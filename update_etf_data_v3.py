from __future__ import annotations

from pathlib import Path

import pandas as pd

from core.config import DEFAULT_ETF_UNIVERSE, MASTER_FILE, RANKING_FILE, REPORT_FILE
from core.data_provider import fetch_instrument
from core.etf_scoring import score_etf
from core.metrics import calculate_price_metrics
from core.report_engine import build_text_report


def load_etf_universe() -> pd.DataFrame:
    if MASTER_FILE.exists():
        try:
            df = pd.read_excel(MASTER_FILE)
            if "Ticker" in df.columns and not df.empty:
                # Normalize common column names while preserving existing information.
                if "Nome ETF" not in df.columns:
                    for candidate in ["Nome", "Name", "ETF", "Descrizione"]:
                        if candidate in df.columns:
                            df["Nome ETF"] = df[candidate]
                            break
                if "Nome ETF" not in df.columns:
                    df["Nome ETF"] = df["Ticker"]
                if "Categoria" not in df.columns:
                    df["Categoria"] = "Core"
                if "Tema/Area" not in df.columns:
                    df["Tema/Area"] = df.get("Tema", "")
                return df[[col for col in df.columns if col]].copy()
        except Exception as exc:  # noqa: BLE001
            print(f"Master non leggibile, uso universo default: {exc}")
    return pd.DataFrame(DEFAULT_ETF_UNIVERSE)


def update_etf_ranking() -> pd.DataFrame:
    universe = load_etf_universe().dropna(subset=["Ticker"]).drop_duplicates(subset=["Ticker"])
    rows: list[dict] = []
    for _, base in universe.iterrows():
        ticker = str(base.get("Ticker", "")).strip()
        if not ticker:
            continue
        print(f"Analisi ETF: {ticker}")
        data = fetch_instrument(ticker, period="3y")
        metrics = calculate_price_metrics(data.prices)
        base_dict = base.to_dict()
        scored = score_etf(base_dict, metrics)
        long_name = data.info.get("longName") or data.info.get("shortName") or base_dict.get("Nome ETF") or ticker
        row = {
            **base_dict,
            "Ticker": ticker.upper(),
            "Nome ETF": long_name,
            **metrics,
            **scored,
            "Errore Dati": data.error or "",
        }
        rows.append(row)
    ranking = pd.DataFrame(rows)
    if ranking.empty:
        raise RuntimeError("Nessun ETF analizzato: controllare tickers/master file")
    ranking = ranking.sort_values("Score Finale", ascending=False, na_position="last")
    preferred = [
        "Ticker", "Nome ETF", "Categoria", "Tema/Area", "Current Price", "Score Finale", "Stato",
        "ETF Quality Score", "ETF Momentum Score", "ETF Risk Score", "ETF Entry Score",
        "Trend", "Rendimento 1M %", "Rendimento 3M %", "Rendimento 6M %", "Rendimento 12M %",
        "CAGR %", "Volatilità %", "Max Drawdown %", "Sharpe", "MA50", "MA200", "Note AI", "Errore Dati",
    ]
    ordered = [col for col in preferred if col in ranking.columns] + [col for col in ranking.columns if col not in preferred]
    ranking = ranking[ordered]
    ranking.to_excel(RANKING_FILE, index=False)
    REPORT_FILE.write_text(build_text_report(ranking, pd.DataFrame()), encoding="utf-8")
    print(f"Creato {RANKING_FILE} con {len(ranking)} righe")
    return ranking


if __name__ == "__main__":
    update_etf_ranking()
