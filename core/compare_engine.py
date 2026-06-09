from __future__ import annotations

import re
from typing import Any

import pandas as pd

from core.data_provider import fetch_instrument, infer_instrument_type
from core.etf_scoring import score_etf
from core.insight_engine import action_label, priority_score
from core.metrics import calculate_price_metrics
from core.signal_engine import build_scenarios, calculate_signal_levels
from core.stock_scoring import score_stock

TICKER_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9.\-]{0,12}")


def extract_tickers(text: str) -> list[str]:
    raw = TICKER_RE.findall(text.replace(",", " ").replace(";", " "))
    stopwords = {
        "analizza", "confronta", "valuta", "vs", "and", "or", "etf", "azione", "azioni", "stock", "titolo", "titoli",
        "meglio", "compra", "vendere", "mi", "de", "as", "pa", "monitor", "watchlist",
    }
    tickers: list[str] = []
    for item in raw:
        token = item.strip().upper()
        if token.lower() in stopwords or len(token) < 2:
            continue
        if token not in tickers:
            tickers.append(token)
    return tickers[:10]


def _enrich_common(out: dict[str, Any], prices: pd.DataFrame, metrics: dict[str, Any]) -> dict[str, Any]:
    signal = calculate_signal_levels(prices, metrics)
    out.update(signal)
    out["Priority Score"] = priority_score(out)
    out["Azione Suggerita"] = action_label(out)
    out.update(build_scenarios(out))
    return out


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
        return _enrich_common(out, data.prices, metrics)
    out = score_stock(ticker)
    # score_stock already fetches data; fetch again is avoided there in future refactors, but kept safe here.
    data2 = fetch_instrument(ticker)
    metrics = calculate_price_metrics(data2.prices)
    return _enrich_common(out, data2.prices, metrics)


def compare_tickers(tickers: list[str]) -> pd.DataFrame:
    rows = [analyze_instrument(ticker) for ticker in tickers]
    df = pd.DataFrame(rows)
    if not df.empty and "Score Finale" in df.columns:
        df = df.sort_values(["Priority Score", "Score Finale"], ascending=False, na_position="last")
    return df


def comparison_summary(df: pd.DataFrame) -> list[str]:
    if df.empty:
        return ["Nessuno strumento analizzabile."]
    lines: list[str] = []
    if "Priority Score" in df.columns:
        best = df.sort_values("Priority Score", ascending=False).iloc[0]
        lines.append(f"Priorità operativa watchlist: {best.get('Ticker', '')} ({best.get('Priority Score', '')}).")
    if "Score Finale" in df.columns:
        best_score = df.sort_values("Score Finale", ascending=False).iloc[0]
        lines.append(f"Miglior score complessivo: {best_score.get('Ticker', '')} ({best_score.get('Score Finale', '')}).")
    risk_col = "Risk Score" if "Risk Score" in df.columns else "Stock Risk Score" if "Stock Risk Score" in df.columns else None
    if risk_col:
        defensive = df.sort_values(risk_col, ascending=False).iloc[0]
        lines.append(f"Profilo più difensivo: {defensive.get('Ticker', '')}.")
    mom_col = "Momentum Score" if "Momentum Score" in df.columns else "Stock Momentum Score" if "Stock Momentum Score" in df.columns else None
    if mom_col:
        mom = df.sort_values(mom_col, ascending=False).iloc[0]
        lines.append(f"Momentum migliore: {mom.get('Ticker', '')}.")
    if "Azione Suggerita" in df.columns:
        actions = df[["Ticker", "Azione Suggerita"]].head(3).to_dict("records")
        lines.append("Prime azioni pratiche: " + "; ".join(f"{x['Ticker']}: {x['Azione Suggerita']}" for x in actions) + ".")
    lines.append("Interpretazione informativa: non è consulenza finanziaria personalizzata.")
    return lines
