from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd

try:
    import requests
except Exception:  # noqa: BLE001
    requests = None  # type: ignore[assignment]

try:
    import yfinance as yf
except Exception:  # noqa: BLE001
    yf = None  # type: ignore[assignment]

from core.config import (
    FINECO_FUND_PERFORMANCE_CSV,
    FINECO_FUND_PERFORMANCE_XLSX,
    FINECO_FUND_PRICE_HISTORY_CSV,
    FINECO_FUND_PRICE_HISTORY_XLSX,
    FINECO_FUNDS_PUBLIC_FILE,
)


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        if pd.isna(value):
            return default
        if isinstance(value, str):
            text = value.replace("€", "").replace("EUR", "").replace("%", "").replace(" ", "").strip()
            if text == "":
                return default
            if "," in text and "." in text:
                if text.rfind(",") > text.rfind("."):
                    text = text.replace(".", "").replace(",", ".")
                else:
                    text = text.replace(",", "")
            elif "," in text:
                text = text.replace(",", ".")
            value = text
        return float(value)
    except Exception:  # noqa: BLE001
        return default


def load_fund_universe(path: Path = FINECO_FUNDS_PUBLIC_FILE) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"File universo fondi non trovato: {path}")
    df = pd.read_csv(path)
    text_cols = [
        "ISIN", "Nome Strumento", "Tipo", "Tipo Versamento", "Proxy Ticker", "Proxy Tickers",
        "Proxy Nome", "News Query", "Categoria AlphaForge", "Ruolo", "Nota", "Data Inizio",
    ]
    for col in text_cols:
        if col not in df.columns:
            df[col] = ""
        df[col] = df[col].fillna("").astype(str).str.strip()
    for col in ["Importo Iniziale EUR", "PAC Mensile EUR", "Costo Annuo %", "Bollo Una Tantum EUR"]:
        if col not in df.columns:
            df[col] = 0.0
        df[col] = df[col].apply(_to_float)
    return df


def _ticker_candidates(row: pd.Series) -> list[str]:
    raw = str(row.get("Proxy Tickers", "") or row.get("Proxy Ticker", ""))
    parts = [x.strip() for chunk in raw.split(";") for x in chunk.split(",") if x.strip()]
    primary = str(row.get("Proxy Ticker", "")).strip()
    if primary and primary not in parts:
        parts.insert(0, primary)
    # Keep order, remove duplicates.
    seen: set[str] = set()
    out: list[str] = []
    for item in parts:
        key = item.upper()
        if key not in seen:
            seen.add(key)
            out.append(item)
    return out


def _fetch_yfinance(ticker: str, period: str = "1y") -> pd.DataFrame:
    if not ticker or yf is None:
        return pd.DataFrame()
    try:
        hist = yf.download(ticker, period=period, interval="1d", progress=False, auto_adjust=True, threads=False, timeout=10)
        if hist is None or hist.empty:
            return pd.DataFrame()
        hist = hist.reset_index()
        if isinstance(hist.columns, pd.MultiIndex):
            hist.columns = [c[0] if isinstance(c, tuple) else c for c in hist.columns]
        date_col = "Date" if "Date" in hist.columns else ("Datetime" if "Datetime" in hist.columns else None)
        close_col = "Close" if "Close" in hist.columns else None
        if not date_col or not close_col:
            return pd.DataFrame()
        out = hist[[date_col, close_col]].dropna().copy()
        out.columns = ["Date", "Close"]
        out["Date"] = pd.to_datetime(out["Date"], errors="coerce").dt.date.astype(str)
        out["Close"] = pd.to_numeric(out["Close"], errors="coerce")
        return out.dropna(subset=["Date", "Close"])
    except Exception:  # noqa: BLE001
        return pd.DataFrame()


def _stooq_symbol(ticker: str) -> str:
    t = ticker.strip().lower()
    # Stooq uses qqq.us, eem.us, acwi.us, etc. Use only simple US fallbacks.
    if "." not in t and t.isalnum():
        return f"{t}.us"
    return ""


def _fetch_stooq(ticker: str, period: str = "1y") -> pd.DataFrame:
    symbol = _stooq_symbol(ticker)
    if not symbol:
        return pd.DataFrame()
    try:
        days = 400 if period == "1y" else 210 if period == "6mo" else 110
        end = datetime.now(timezone.utc).date()
        start = end - timedelta(days=days)
        url = f"https://stooq.com/q/d/l/?s={symbol}&d1={start:%Y%m%d}&d2={end:%Y%m%d}&i=d"
        if requests is None:
            return pd.DataFrame()
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        from io import StringIO
        df = pd.read_csv(StringIO(response.text))
        if df.empty or "Close" not in df.columns or "Date" not in df.columns:
            return pd.DataFrame()
        df = df[["Date", "Close"]].dropna()
        df["Close"] = pd.to_numeric(df["Close"], errors="coerce")
        return df.dropna(subset=["Close"])
    except Exception:  # noqa: BLE001
        return pd.DataFrame()


def _fetch_proxy_history(candidates: list[str], period: str = "1y") -> tuple[pd.DataFrame, str, str]:
    tried: list[str] = []
    for ticker in candidates:
        tried.append(ticker)
        hist = _fetch_yfinance(ticker, period=period)
        if not hist.empty:
            return hist, ticker, "Yahoo/yfinance"
    # fallback for US ETFs when Yahoo blocks a specific request
    for ticker in candidates:
        tried.append(f"stooq:{ticker}")
        hist = _fetch_stooq(ticker, period=period)
        if not hist.empty:
            return hist, ticker, "Stooq daily CSV fallback"
    return pd.DataFrame(), "", "Nessun dato proxy disponibile. Provati: " + ", ".join(tried[:8])


def _trend_label(change_1m: float, change_3m: float) -> str:
    if change_1m >= 3 and change_3m >= 5:
        return "Positivo"
    if change_1m <= -3 and change_3m <= -5:
        return "Debole"
    if change_1m >= 2:
        return "Rimbalzo breve"
    if change_1m <= -2:
        return "Pressione breve"
    return "Laterale"


def _watch_action(change_1m: float, change_3m: float, cost: float, role: str) -> str:
    role_l = role.lower()
    if cost >= 3.0:
        return "Monitorare costo elevato: deve battere alternative piu' economiche"
    if change_1m < -4:
        return "Attendere NAV e capire se e' correzione normale del mercato"
    if change_1m > 7:
        return "Non inseguire: meglio PAC/ingressi graduali"
    if "satellite" in role_l or "pac" in role_l:
        return "Tenere monitorato come satellite; rivalutare peso tra 3-6 mesi"
    return "Monitoraggio ordinario vs benchmark/proxy"


def _perf_from_n(hist: pd.DataFrame, latest: float, n: int) -> float | None:
    if len(hist) <= n:
        return None
    prev = float(hist["Close"].iloc[-n])
    if prev == 0:
        return None
    return (latest / prev - 1) * 100


def build_fund_performance(period: str = "1y") -> tuple[pd.DataFrame, pd.DataFrame]:
    funds = load_fund_universe()
    rows: list[dict[str, Any]] = []
    history_rows: list[dict[str, Any]] = []
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    for _, fund in funds.iterrows():
        candidates = _ticker_candidates(fund)
        hist, used_ticker, source = _fetch_proxy_history(candidates, period=period)
        initial = _to_float(fund.get("Importo Iniziale EUR", 0))
        pac = _to_float(fund.get("PAC Mensile EUR", 0))
        annual_cost = _to_float(fund.get("Costo Annuo %", 0))
        one_off_stamp = _to_float(fund.get("Bollo Una Tantum EUR", 0))

        if hist.empty:
            rows.append({
                "ISIN": fund.get("ISIN", ""),
                "Nome Strumento": fund.get("Nome Strumento", ""),
                "Categoria AlphaForge": fund.get("Categoria AlphaForge", ""),
                "Ruolo": fund.get("Ruolo", ""),
                "Tipo Versamento": fund.get("Tipo Versamento", ""),
                "Importo iniziale EUR": initial,
                "PAC mensile EUR": pac,
                "Proxy Ticker": str(fund.get("Proxy Ticker", "")),
                "Proxy usato": "n/d",
                "Proxy Nome": fund.get("Proxy Nome", ""),
                "Ultimo prezzo proxy": None,
                "Rendimento proxy 1D %": None,
                "Rendimento proxy 1M %": None,
                "Rendimento proxy 3M %": None,
                "Rendimento proxy 1Y %": None,
                "Trend proxy": "Dato non disponibile",
                "Costo annuo %": annual_cost,
                "Bollo una tantum EUR": one_off_stamp,
                "Azione pratica": "Proxy non scaricato: controlla ticker/proxy o aggiorna manualmente NAV Fineco",
                "Fonte dato": source,
                "Aggiornato UTC": generated_at,
            })
            continue

        hist = hist.dropna().copy()
        hist["Date"] = pd.to_datetime(hist["Date"], errors="coerce")
        hist = hist.dropna(subset=["Date", "Close"]).sort_values("Date")
        hist["Date"] = hist["Date"].dt.date.astype(str)
        latest = float(hist["Close"].iloc[-1])
        first = float(hist["Close"].iloc[0])
        base = first if first else latest
        hist["Normalized 100"] = hist["Close"] / base * 100
        ch_1d = _perf_from_n(hist, latest, 1)
        ch_1m = _perf_from_n(hist, latest, 21)
        ch_3m = _perf_from_n(hist, latest, 63)
        ch_1y = (latest / first - 1) * 100 if first else None
        c1 = float(ch_1m or 0.0)
        c3 = float(ch_3m or 0.0)

        rows.append({
            "ISIN": fund.get("ISIN", ""),
            "Nome Strumento": fund.get("Nome Strumento", ""),
            "Categoria AlphaForge": fund.get("Categoria AlphaForge", ""),
            "Ruolo": fund.get("Ruolo", ""),
            "Tipo Versamento": fund.get("Tipo Versamento", ""),
            "Importo iniziale EUR": initial,
            "PAC mensile EUR": pac,
            "Proxy Ticker": str(fund.get("Proxy Ticker", "")),
            "Proxy usato": used_ticker,
            "Proxy Nome": fund.get("Proxy Nome", ""),
            "Ultimo prezzo proxy": round(latest, 4),
            "Rendimento proxy 1D %": round(float(ch_1d), 2) if ch_1d is not None else None,
            "Rendimento proxy 1M %": round(c1, 2) if ch_1m is not None else None,
            "Rendimento proxy 3M %": round(c3, 2) if ch_3m is not None else None,
            "Rendimento proxy 1Y %": round(float(ch_1y), 2) if ch_1y is not None else None,
            "Trend proxy": _trend_label(c1, c3),
            "Costo annuo %": annual_cost,
            "Bollo una tantum EUR": one_off_stamp,
            "Azione pratica": _watch_action(c1, c3, annual_cost, str(fund.get("Ruolo", ""))),
            "Fonte dato": source,
            "Aggiornato UTC": generated_at,
        })
        for _, h in hist.iterrows():
            history_rows.append({
                "Date": h["Date"],
                "ISIN": fund.get("ISIN", ""),
                "Nome Strumento": fund.get("Nome Strumento", ""),
                "Categoria AlphaForge": fund.get("Categoria AlphaForge", ""),
                "Proxy Ticker": str(fund.get("Proxy Ticker", "")),
                "Proxy usato": used_ticker,
                "Proxy Close": round(float(h["Close"]), 6),
                "Normalized 100": round(float(h["Normalized 100"]), 4),
            })

    performance = pd.DataFrame(rows)
    history = pd.DataFrame(history_rows)
    return performance, history


def save_fund_performance() -> tuple[pd.DataFrame, pd.DataFrame]:
    performance, history = build_fund_performance()
    performance.to_csv(FINECO_FUND_PERFORMANCE_CSV, index=False)
    history.to_csv(FINECO_FUND_PRICE_HISTORY_CSV, index=False)
    try:
        performance.to_excel(FINECO_FUND_PERFORMANCE_XLSX, index=False)
        history.to_excel(FINECO_FUND_PRICE_HISTORY_XLSX, index=False)
    except Exception:  # noqa: BLE001
        pass
    return performance, history
