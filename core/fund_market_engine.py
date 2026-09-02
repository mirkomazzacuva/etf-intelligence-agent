from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

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
            value = value.replace("€", "").replace("%", "").replace(".", "").replace(",", ".").strip()
            if value == "":
                return default
        return float(value)
    except Exception:  # noqa: BLE001
        return default


def load_fund_universe(path: Path = FINECO_FUNDS_PUBLIC_FILE) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"File universo fondi non trovato: {path}")
    df = pd.read_csv(path)
    for col in ["ISIN", "Nome Strumento", "Proxy Ticker", "News Query", "Categoria AlphaForge", "Ruolo"]:
        if col not in df.columns:
            df[col] = ""
        df[col] = df[col].astype(str).fillna("").str.strip()
    for col in ["Importo Iniziale EUR", "PAC Mensile EUR", "Costo Annuo %", "Bollo Una Tantum EUR"]:
        if col not in df.columns:
            df[col] = 0.0
        df[col] = df[col].apply(_to_float)
    return df


def _fetch_proxy_history(ticker: str, period: str = "1y") -> pd.DataFrame:
    if not ticker or yf is None:
        return pd.DataFrame()
    try:
        hist = yf.download(ticker, period=period, interval="1d", progress=False, auto_adjust=True, threads=False)
        if hist is None or hist.empty:
            return pd.DataFrame()
        hist = hist.reset_index()
        close_col = "Close"
        if isinstance(hist.columns, pd.MultiIndex):
            hist.columns = [c[0] if isinstance(c, tuple) else c for c in hist.columns]
        if close_col not in hist.columns:
            return pd.DataFrame()
        hist = hist[["Date", close_col]].dropna()
        hist["Date"] = pd.to_datetime(hist["Date"]).dt.date.astype(str)
        hist["Close"] = pd.to_numeric(hist[close_col], errors="coerce")
        hist = hist.dropna(subset=["Close"])
        return hist[["Date", "Close"]]
    except Exception:  # noqa: BLE001
        return pd.DataFrame()


def _trend_label(change_1m: float, change_3m: float) -> str:
    if change_1m >= 3 and change_3m >= 5:
        return "Trend positivo"
    if change_1m <= -3 and change_3m <= -5:
        return "Trend debole"
    if change_1m >= 2:
        return "Rimbalzo / momentum breve"
    if change_1m <= -2:
        return "Pressione breve"
    return "Laterale / neutro"


def _watch_action(change_1m: float, change_3m: float, cost: float, role: str) -> str:
    role_l = role.lower()
    if cost >= 3.0:
        return "Monitorare: costo elevato, serve rendimento coerente nel tempo"
    if change_1m < -4:
        return "Non giudicare subito: attendere NAV e capire se e' correzione di mercato"
    if change_1m > 7:
        return "Non inseguire: attendere consolidamento o PAC graduale"
    if "pac" in role_l or "satellite" in role_l:
        return "Tenere in PAC e rivalutare peso tra 3-6 mesi"
    return "Mantenere monitoraggio: confrontare con benchmark/proxy"


def build_fund_performance(period: str = "1y") -> tuple[pd.DataFrame, pd.DataFrame]:
    funds = load_fund_universe()
    rows: list[dict[str, Any]] = []
    history_rows: list[dict[str, Any]] = []
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    for _, fund in funds.iterrows():
        ticker = str(fund.get("Proxy Ticker", "")).strip()
        hist = _fetch_proxy_history(ticker, period=period)
        source = "Proxy ETF Yahoo/yfinance"
        if hist.empty:
            source = "Nessun dato proxy disponibile"
            rows.append({
                "ISIN": fund.get("ISIN", ""),
                "Nome Strumento": fund.get("Nome Strumento", ""),
                "Categoria AlphaForge": fund.get("Categoria AlphaForge", ""),
                "Ruolo": fund.get("Ruolo", ""),
                "Proxy Ticker": ticker,
                "Proxy Nome": fund.get("Proxy Nome", ""),
                "Ultimo prezzo proxy": None,
                "Rendimento proxy 1M %": None,
                "Rendimento proxy 3M %": None,
                "Rendimento proxy 1Y %": None,
                "Trend proxy": "Dato non disponibile",
                "Costo annuo %": fund.get("Costo Annuo %", 0),
                "Azione pratica": "Aggiorna manualmente NAV/controvalore da Fineco",
                "Fonte dato": source,
                "Aggiornato UTC": generated_at,
            })
            continue

        latest = float(hist["Close"].iloc[-1])
        first = float(hist["Close"].iloc[0])
        base = first if first else latest
        hist["Normalized 100"] = hist["Close"] / base * 100

        def perf_from_n(n: int) -> float | None:
            if len(hist) <= n:
                return None
            prev = float(hist["Close"].iloc[-n])
            if prev == 0:
                return None
            return (latest / prev - 1) * 100

        change_1m = perf_from_n(21)
        change_3m = perf_from_n(63)
        change_1y = (latest / first - 1) * 100 if first else None
        c1 = float(change_1m or 0.0)
        c3 = float(change_3m or 0.0)
        cost = _to_float(fund.get("Costo Annuo %", 0))

        rows.append({
            "ISIN": fund.get("ISIN", ""),
            "Nome Strumento": fund.get("Nome Strumento", ""),
            "Categoria AlphaForge": fund.get("Categoria AlphaForge", ""),
            "Ruolo": fund.get("Ruolo", ""),
            "Proxy Ticker": ticker,
            "Proxy Nome": fund.get("Proxy Nome", ""),
            "Ultimo prezzo proxy": round(latest, 4),
            "Rendimento proxy 1M %": round(c1, 2) if change_1m is not None else None,
            "Rendimento proxy 3M %": round(c3, 2) if change_3m is not None else None,
            "Rendimento proxy 1Y %": round(float(change_1y), 2) if change_1y is not None else None,
            "Trend proxy": _trend_label(c1, c3),
            "Costo annuo %": cost,
            "Azione pratica": _watch_action(c1, c3, cost, str(fund.get("Ruolo", ""))),
            "Fonte dato": source,
            "Aggiornato UTC": generated_at,
        })
        for _, h in hist.iterrows():
            history_rows.append({
                "Date": h["Date"],
                "ISIN": fund.get("ISIN", ""),
                "Nome Strumento": fund.get("Nome Strumento", ""),
                "Proxy Ticker": ticker,
                "Proxy Close": round(float(h["Close"]), 6),
                "Normalized 100": round(float(h["Normalized 100"]), 4),
            })

    performance = pd.DataFrame(rows)
    history = pd.DataFrame(history_rows)
    return performance, history


def save_fund_performance() -> tuple[pd.DataFrame, pd.DataFrame]:
    performance, history = build_fund_performance()
    performance.to_csv(FINECO_FUND_PERFORMANCE_CSV, index=False)
    performance.to_excel(FINECO_FUND_PERFORMANCE_XLSX, index=False)
    history.to_csv(FINECO_FUND_PRICE_HISTORY_CSV, index=False)
    history.to_excel(FINECO_FUND_PRICE_HISTORY_XLSX, index=False)
    return performance, history
