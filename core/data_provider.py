from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

try:
    import yfinance as yf
except Exception:  # pragma: no cover
    yf = None  # type: ignore[assignment]


@dataclass
class InstrumentData:
    ticker: str
    prices: pd.DataFrame
    info: dict[str, Any]
    error: str | None = None


def _flatten_columns(df: pd.DataFrame) -> pd.DataFrame:
    if isinstance(df.columns, pd.MultiIndex):
        # yfinance can return MultiIndex columns even for a single ticker.
        # Prefer first level when it contains OHLCV names; otherwise last level.
        level0 = [str(x) for x in df.columns.get_level_values(0)]
        if {"Open", "High", "Low", "Close", "Adj Close", "Volume"}.intersection(level0):
            df.columns = df.columns.get_level_values(0)
        else:
            df.columns = df.columns.get_level_values(-1)
    return df


def fetch_price_history(ticker: str, period: str = "3y") -> tuple[pd.DataFrame, str | None]:
    ticker = str(ticker).strip()
    if not ticker:
        return pd.DataFrame(), "Ticker vuoto"
    if yf is None:
        return pd.DataFrame(), "yfinance non disponibile"
    try:
        df = yf.download(
            ticker,
            period=period,
            interval="1d",
            auto_adjust=True,
            progress=False,
            threads=False,
        )
        if df is None or df.empty:
            return pd.DataFrame(), "Nessun dato prezzo disponibile"
        df = _flatten_columns(df.copy())
        if "Close" not in df.columns and "Adj Close" in df.columns:
            df["Close"] = df["Adj Close"]
        if "Close" not in df.columns:
            return pd.DataFrame(), "Colonna Close non disponibile"
        columns = [col for col in ["Open", "High", "Low", "Close", "Volume"] if col in df.columns]
        out = df[columns].copy()
        out.index = pd.to_datetime(out.index)
        out = out.dropna(subset=["Close"])
        if out.empty:
            return pd.DataFrame(), "Serie prezzi vuota dopo pulizia"
        return out, None
    except Exception as exc:  # noqa: BLE001
        return pd.DataFrame(), f"Errore download prezzi: {exc}"


def fetch_instrument_info(ticker: str) -> dict[str, Any]:
    if yf is None:
        return {}
    try:
        info = yf.Ticker(str(ticker).strip()).info
        return info if isinstance(info, dict) else {}
    except Exception:  # noqa: BLE001
        return {}


def fetch_instrument(ticker: str, period: str = "3y") -> InstrumentData:
    prices, error = fetch_price_history(ticker, period=period)
    info = fetch_instrument_info(ticker)
    return InstrumentData(ticker=str(ticker).strip(), prices=prices, info=info, error=error)


def infer_instrument_type(ticker: str, info: dict[str, Any] | None = None) -> str:
    info = info or {}
    quote_type = str(info.get("quoteType") or info.get("typeDisp") or "").lower()
    long_name = str(info.get("longName") or info.get("shortName") or "").lower()
    category = str(info.get("category") or "").lower()
    ticker_upper = str(ticker).upper()
    if "etf" in quote_type or "fund" in quote_type or "etf" in long_name or category:
        return "ETF"
    if ticker_upper.endswith((".MI", ".DE", ".AS", ".PA", ".L", ".SW")) and any(x in long_name for x in ["ucits", "etf", "ishares", "xtrackers", "vanguard", "wisdomtree", "invesco"]):
        return "ETF"
    return "Stock"
