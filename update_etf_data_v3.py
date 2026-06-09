from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import yfinance as yf

APP_TZ = ZoneInfo("Europe/Rome")
INPUT_FILE = Path("ETF_Intelligence_Agent_Master_Populated.xlsx")
INPUT_SHEET = "ETF_Master"
OUTPUT_FILE = Path("ETF_Intelligence_Agent_UPDATED.xlsx")
REPORT_FILE = Path("ETF_Daily_Report.txt")
RUN_META_FILE = Path("ETF_Update_Metadata.json")
RISK_FREE_RATE = 0.02
MIN_PRICE_DAYS = 30


def now_text() -> str:
    return datetime.now(APP_TZ).strftime("%d/%m/%Y %H:%M")


def normalize_ticker(ticker: object) -> str:
    value = str(ticker).strip().upper()
    if not value or value == "NAN":
        return ""
    return value if "." in value else f"{value}.MI"


def download_prices(ticker: str, attempts: int = 3) -> pd.Series | None:
    if not ticker:
        return None

    last_error = ""
    for attempt in range(1, attempts + 1):
        try:
            data = yf.download(
                ticker,
                period="5y",
                interval="1d",
                auto_adjust=True,
                progress=False,
                threads=False,
            )
            if data is None or data.empty:
                last_error = "download vuoto"
            else:
                if "Close" not in data.columns:
                    last_error = "colonna Close non trovata"
                else:
                    prices = data["Close"]
                    if isinstance(prices, pd.DataFrame):
                        prices = prices.iloc[:, 0]
                    prices = pd.to_numeric(prices, errors="coerce").dropna()
                    if len(prices) >= MIN_PRICE_DAYS:
                        return prices
                    last_error = f"storico insufficiente: {len(prices)} giorni"
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)

        time.sleep(1.5 * attempt)

    print(f"ATTENZIONE: dati non disponibili per {ticker}: {last_error}")
    return None


def period_return(prices: pd.Series | None, days: int) -> float:
    if prices is None or len(prices) <= days:
        return np.nan
    return float((prices.iloc[-1] / prices.iloc[-days] - 1) * 100)


def cagr(prices: pd.Series | None) -> float:
    if prices is None or len(prices) < MIN_PRICE_DAYS:
        return np.nan
    years = len(prices) / 252
    if years <= 0 or prices.iloc[0] <= 0:
        return np.nan
    return float(((prices.iloc[-1] / prices.iloc[0]) ** (1 / years) - 1) * 100)


def volatility(prices: pd.Series | None) -> float:
    if prices is None or len(prices) < MIN_PRICE_DAYS:
        return np.nan
    return float(prices.pct_change().dropna().std() * np.sqrt(252) * 100)


def max_drawdown(prices: pd.Series | None) -> float:
    if prices is None or len(prices) < MIN_PRICE_DAYS:
        return np.nan
    drawdown = (prices / prices.cummax()) - 1
    return float(drawdown.min() * 100)


def sharpe(prices: pd.Series | None) -> float:
    ca = cagr(prices)
    vol = volatility(prices)
    if pd.isna(ca) or pd.isna(vol) or vol == 0:
        return np.nan
    return float(((ca / 100) - RISK_FREE_RATE) / (vol / 100))


def base_score(row: dict) -> float:
    score = 50.0

    r12 = row.get("Rendimento 12M %", np.nan)
    r6 = row.get("Rendimento 6M %", np.nan)
    shrp = row.get("Sharpe", np.nan)
    vol = row.get("Volatilità %", np.nan)
    dd = row.get("Max Drawdown %", np.nan)

    if pd.notna(r12):
        score += min(max(float(r12), -30), 50) * 0.25
    if pd.notna(r6):
        score += min(max(float(r6), -20), 35) * 0.20
    if pd.notna(shrp):
        score += min(max(float(shrp), -1), 2) * 8
    if pd.notna(vol):
        score -= min(max(float(vol) - 12, 0), 30) * 0.35
    if pd.notna(dd):
        score += max(float(dd), -60) * 0.20

    score += 8 if row.get("Trend OK") == "Si" else -8
    return round(max(min(score, 100), 0), 1)


def macro_score(row: dict) -> float:
    tema = str(row.get("Tema/Area", "")).lower()
    score = 0.0
    keyword_scores = {
        "gold": 8,
        "oro": 8,
        "defense": 7,
        "difesa": 7,
        "quality": 5,
        "global equity": 4,
        "world": 4,
        "bonds": 3,
        "bond": 3,
        "artificial intelligence": 6,
        "ai": 4,
        "semiconductors": 5,
        "semiconduttori": 5,
        "emerging": 2,
    }
    for keyword, points in keyword_scores.items():
        if keyword in tema:
            score += points
    return score


def penalty(row: dict) -> float:
    tema = str(row.get("Tema/Area", "")).lower()
    vol = row.get("Volatilità %", np.nan)
    dd = row.get("Max Drawdown %", np.nan)
    r12 = row.get("Rendimento 12M %", np.nan)
    p = 0.0

    if "artificial intelligence" in tema or " ai" in f" {tema} ":
        p -= 5
    if "semiconductor" in tema or "semiconduttori" in tema:
        p -= 7
    if "nasdaq" in tema:
        p -= 4
    if pd.notna(vol) and float(vol) > 25:
        p -= 5
    if pd.notna(dd) and float(dd) < -35:
        p -= 5
    if pd.notna(r12) and float(r12) > 70:
        p -= 6

    return p


def classify(score: float) -> str:
    if pd.isna(score):
        return "No data"
    if score >= 80:
        return "Buy Watchlist"
    if score >= 65:
        return "Accumulate Carefully"
    if score >= 50:
        return "Hold / Monitor"
    if score >= 35:
        return "Avoid for Now"
    return "Speculative Only"


def note(row: dict) -> str:
    tema = str(row.get("Tema/Area", ""))
    tema_lower = tema.lower()
    notes: list[str] = []

    if "artificial intelligence" in tema_lower or " ai" in f" {tema_lower} ":
        notes.append("Tema strutturale forte, ma con rischio euforia e concentrazione.")
    if "semiconductor" in tema_lower or "semiconduttori" in tema_lower:
        notes.append("Tema molto forte, ma ciclico e volatile.")
    if "gold" in tema_lower or "oro" in tema_lower:
        notes.append("Utile come protezione macro/geopolitica.")
    if "global equity" in tema_lower or "world" in tema_lower:
        notes.append("Buona base core di lungo periodo.")
    if "bond" in tema_lower:
        notes.append("Componente difensiva utile per bilanciare il rischio equity.")
    if "defense" in tema_lower or "difesa" in tema_lower:
        notes.append("Tema sostenuto dal contesto geopolitico, da usare come satellite.")

    vol = row.get("Volatilità %", np.nan)
    dd = row.get("Max Drawdown %", np.nan)
    trend = row.get("Trend OK")

    if pd.notna(vol) and float(vol) > 25:
        notes.append("Volatilità elevata: ingresso da valutare con prudenza.")
    if pd.notna(dd) and float(dd) < -35:
        notes.append("Drawdown storico importante.")
    if trend == "No":
        notes.append("Prezzo sotto media 200: trend non ancora convincente.")

    return " ".join(notes) if notes else "Monitorare secondo score, trend e rischio."


def load_master() -> pd.DataFrame:
    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"File input non trovato: {INPUT_FILE}")
    try:
        return pd.read_excel(INPUT_FILE, sheet_name=INPUT_SHEET)
    except ValueError:
        return pd.read_excel(INPUT_FILE)


def build_report(result: pd.DataFrame, failed: list[str]) -> str:
    lines: list[str] = []
    lines.append("ETF INTELLIGENCE REPORT")
    lines.append(f"Data aggiornamento: {now_text()}")
    lines.append("")

    valid = result[pd.notna(result["Score Finale"])].copy()
    if valid.empty:
        lines.append("Nessun ETF aggiornato con dati sufficienti.")
    else:
        top = valid.head(10)
        best = top.iloc[0]
        lines.append(
            f"Miglior ETF del giorno: {best.get('Nome ETF', '')} "
            f"({best.get('Ticker', '')}) - Score {best.get('Score Finale', '')}"
        )
        lines.append("")
        lines.append("TOP 10 ETF:")
        for _, row in top.iterrows():
            lines.append(
                f"- {row.get('Ticker', '')} | {row.get('Nome ETF', '')} | "
                f"Score {row.get('Score Finale', '')} | {row.get('Stato', '')} | "
                f"Nota: {row.get('Note AI', '')}"
            )

    if failed:
        lines.append("")
        lines.append("Ticker non aggiornati:")
        for ticker in failed:
            lines.append(f"- {ticker}")

    lines.append("")
    lines.append("Lettura prudente:")
    lines.append("- Non sono segnali automatici di acquisto.")
    lines.append("- Gli ETF tematici vanno trattati come satellite.")
    lines.append("- Gli ETF core globali sono piu adatti come base.")
    lines.append("- Oro/difensivi aiutano a bilanciare rischio macro.")
    lines.append("")
    lines.append("Disclaimer: report informativo, non consulenza finanziaria personalizzata.")
    return "\n".join(lines)


def main() -> None:
    started = time.time()
    df = load_master()

    if "Ticker" not in df.columns:
        raise ValueError("Nel file master manca la colonna obbligatoria 'Ticker'.")

    results: list[dict] = []
    failed: list[str] = []

    for _, source_row in df.iterrows():
        out = source_row.to_dict()
        ticker = normalize_ticker(out.get("Ticker", ""))
        out["Ticker"] = ticker
        out["Ultimo aggiornamento"] = now_text()
        print(f"Aggiorno: {ticker}")

        prices = download_prices(ticker)
        if prices is None:
            failed.append(ticker)
            out["Fonte dati"] = "No data"
            out["Score Finale"] = np.nan
            out["Stato"] = "No data"
            out["Note AI"] = "Dati prezzo non disponibili o insufficienti."
            results.append(out)
            continue

        out["Prezzo"] = round(float(prices.iloc[-1]), 4)
        out["MA50"] = round(float(prices.tail(50).mean()), 4)
        out["MA200"] = round(float(prices.tail(200).mean()), 4) if len(prices) >= 200 else np.nan
        out["Trend OK"] = "Si" if pd.notna(out["MA200"]) and out["Prezzo"] > out["MA200"] else "No"
        out["Rendimento 1M %"] = round(period_return(prices, 21), 2)
        out["Rendimento 3M %"] = round(period_return(prices, 63), 2)
        out["Rendimento 6M %"] = round(period_return(prices, 126), 2)
        out["Rendimento 12M %"] = round(period_return(prices, 252), 2)
        out["CAGR storico %"] = round(cagr(prices), 2)
        out["Volatilità %"] = round(volatility(prices), 2)
        out["Max Drawdown %"] = round(max_drawdown(prices), 2)
        out["Sharpe"] = round(sharpe(prices), 2)
        out["Anni storico"] = round(len(prices) / 252, 2)
        out["Fonte dati"] = "Yahoo Finance via yfinance"
        out["Score Finale Base"] = base_score(out)
        out["Macro Score"] = macro_score(out)
        out["Penalità"] = penalty(out)
        out["Score Finale"] = round(
            max(min(out["Score Finale Base"] + out["Macro Score"] + out["Penalità"], 100), 0),
            1,
        )
        out["Stato"] = classify(out["Score Finale"])
        out["Note AI"] = note(out)
        results.append(out)

    result = pd.DataFrame(results).sort_values("Score Finale", ascending=False, na_position="last")
    result.to_excel(OUTPUT_FILE, index=False)

    report = build_report(result, failed)
    REPORT_FILE.write_text(report, encoding="utf-8")

    metadata = {
        "status": "success",
        "updated_at": now_text(),
        "tickers_total": int(len(result)),
        "tickers_failed": failed,
        "duration_seconds": round(time.time() - started, 2),
        "output_file": str(OUTPUT_FILE),
        "report_file": str(REPORT_FILE),
    }
    RUN_META_FILE.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")

    print(report)
    print(f"Creati: {OUTPUT_FILE}, {REPORT_FILE}, {RUN_META_FILE}")


if __name__ == "__main__":
    main()
