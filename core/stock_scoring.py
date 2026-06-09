from __future__ import annotations

from typing import Any

from core.data_provider import fetch_instrument
from core.metrics import calculate_price_metrics, clamp, safe_float


def _ratio_to_score(value: float, low_good: float, high_bad: float, inverse: bool = True) -> float:
    if value <= 0:
        return 50.0
    if inverse:
        return clamp(100 - (value - low_good) / max(high_bad - low_good, 1) * 100)
    return clamp((value - low_good) / max(high_bad - low_good, 1) * 100)


def stock_note(final_score: float, valuation: float, risk: float, trend: str) -> str:
    if final_score >= 78 and valuation >= 45:
        return "Titolo forte; resta necessario controllare prezzo, trimestrali e size."
    if final_score >= 72 and valuation < 45:
        return "Business/momentum interessanti ma valutazione tirata: non inseguire senza pullback."
    if risk < 35:
        return "Rischio elevato: volatilità/drawdown richiedono prudenza."
    if "weak" in str(trend).lower():
        return "Trend debole: meglio aspettare stabilizzazione tecnica."
    return "Da monitorare con scenario positivo, base e negativo."


def score_stock(ticker: str, period: str = "3y") -> dict[str, Any]:
    data = fetch_instrument(ticker, period=period)
    metrics = calculate_price_metrics(data.prices)
    info = data.info or {}

    pe = safe_float(info.get("trailingPE"), 0)
    fpe = safe_float(info.get("forwardPE"), 0)
    margin = safe_float(info.get("profitMargins"), 0) * 100
    roe = safe_float(info.get("returnOnEquity"), 0) * 100
    revenue_growth = safe_float(info.get("revenueGrowth"), 0) * 100
    debt_equity = safe_float(info.get("debtToEquity"), 0)
    dividend_yield = safe_float(info.get("dividendYield"), 0) * 100
    market_cap = safe_float(info.get("marketCap"), 0)

    momentum = safe_float(metrics.get("Momentum Score"), 45)
    trend_score = safe_float(metrics.get("Trend Score"), 45)
    risk_score = safe_float(metrics.get("Risk Score"), 45)
    entry = safe_float(metrics.get("Entry Score"), 45)

    valuation_parts = []
    if pe > 0:
        valuation_parts.append(_ratio_to_score(pe, 12, 55, inverse=True))
    if fpe > 0:
        valuation_parts.append(_ratio_to_score(fpe, 10, 45, inverse=True))
    valuation = sum(valuation_parts) / len(valuation_parts) if valuation_parts else 50.0

    quality = clamp(50 + margin * 0.8 + roe * 0.35 + revenue_growth * 0.6 - max(debt_equity - 120, 0) * 0.06)
    final = clamp(quality * 0.25 + momentum * 0.25 + valuation * 0.18 + risk_score * 0.17 + entry * 0.10 + trend_score * 0.05)

    if final >= 78 and risk_score >= 40:
        status = "Buy Watchlist"
    elif final >= 68:
        status = "Accumulate Carefully"
    elif final >= 55:
        status = "Hold / Monitor"
    elif risk_score < 35:
        status = "High Risk"
    else:
        status = "Avoid for Now"

    out = {
        "Ticker": ticker.upper(),
        "Nome": info.get("longName") or info.get("shortName") or ticker.upper(),
        "Tipo": "Stock",
        "Settore": info.get("sector") or "",
        "Industry": info.get("industry") or "",
        "Market Cap": round(market_cap, 0) if market_cap else 0,
        "P/E": round(pe, 2) if pe else "",
        "Forward P/E": round(fpe, 2) if fpe else "",
        "Profit Margin %": round(margin, 2) if margin else "",
        "ROE %": round(roe, 2) if roe else "",
        "Revenue Growth %": round(revenue_growth, 2) if revenue_growth else "",
        "Debt/Equity": round(debt_equity, 2) if debt_equity else "",
        "Dividend Yield %": round(dividend_yield, 2) if dividend_yield else "",
        "Stock Quality Score": round(quality, 1),
        "Stock Momentum Score": round(momentum, 1),
        "Stock Valuation Score": round(valuation, 1),
        "Stock Risk Score": round(risk_score, 1),
        "Stock Entry Score": round(entry, 1),
        "Score Finale": round(final, 1),
        "Stato": status,
        "Note AI": stock_note(final, valuation, risk_score, str(metrics.get("Trend"))),
        "Errore": data.error or "",
    }
    out.update(metrics)
    return out
