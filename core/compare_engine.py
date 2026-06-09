from __future__ import annotations

import re
from typing import Any

import pandas as pd

from core.data_provider import fetch_instrument, infer_instrument_type
from core.etf_scoring import score_etf
from core.metrics import calculate_price_metrics
from core.stock_scoring import score_stock

TICKER_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9.\-]{0,12}")


def extract_tickers(text: str) -> list[str]:
    raw = TICKER_RE.findall(text.replace(",", " ").replace(";", " "))
    stopwords = {"analizza", "confronta", "vs", "and", "or", "etf", "azione", "azioni", "stock", "mi", "de", "as"}
    tickers: list[str] = []
    for item in raw:
        token = item.strip().upper()
        if token.lower() in stopwords or len(token) < 2:
            continue
        if token not in tickers:
            tickers.append(token)
    return tickers[:8]


def analyze_instrument(ticker: str, preferred_type: str | None = None) -> dict[str, Any]:
    ticker = ticker.strip().upper()
    data = fetch_instrument(ticker)
    instrument_type = preferred_type or infer_instrument_type(ticker, data.info)
    if instrument_type == "ETF":
        metrics = calculate_price_metrics(data.prices)
        base = {
            "Ticker": ticker,
            "Nome ETF": data.info.get("longName") or data.info.get("shortName") or ticker,
            "Categoria": "Custom",
            "Tema/Area": data.info.get("category") or data.info.get("fundFamily") or "Analisi libera",
        }
        score = score_etf(base, metrics)
        out = {**base, "Tipo": "ETF", **metrics, **score, "Errore": data.error or ""}
        return out
    return score_stock(ticker)


def compare_tickers(tickers: list[str]) -> pd.DataFrame:
    rows = [analyze_instrument(ticker) for ticker in tickers]
    df = pd.DataFrame(rows)
    if not df.empty and "Score Finale" in df.columns:
        df = df.sort_values("Score Finale", ascending=False, na_position="last")
    return df


def comparison_summary(df: pd.DataFrame) -> list[str]:
    if df.empty:
        return ["Nessuno strumento analizzabile."]
    lines: list[str] = []
    if "Score Finale" in df.columns:
        best = df.sort_values("Score Finale", ascending=False).iloc[0]
        lines.append(f"Miglior score complessivo: {best.get('Ticker', '')} ({best.get('Score Finale', '')}).")
    if "Risk Score" in df.columns:
        defensive = df.sort_values("Risk Score", ascending=False).iloc[0]
        lines.append(f"Profilo più difensivo: {defensive.get('Ticker', '')}.")
    elif "Stock Risk Score" in df.columns:
        defensive = df.sort_values("Stock Risk Score", ascending=False).iloc[0]
        lines.append(f"Profilo più difensivo: {defensive.get('Ticker', '')}.")
    if "Momentum Score" in df.columns:
        mom = df.sort_values("Momentum Score", ascending=False).iloc[0]
        lines.append(f"Momentum migliore: {mom.get('Ticker', '')}.")
    elif "Stock Momentum Score" in df.columns:
        mom = df.sort_values("Stock Momentum Score", ascending=False).iloc[0]
        lines.append(f"Momentum migliore: {mom.get('Ticker', '')}.")
    lines.append("Interpretazione informativa: non è consulenza finanziaria personalizzata.")
    return lines
