from __future__ import annotations

from typing import Any

from core.metrics import clamp, safe_float


def classify_status(final_score: float, risk_score: float, entry_score: float, trend: str) -> str:
    trend_l = str(trend).lower()
    if final_score >= 78 and risk_score >= 45 and entry_score >= 55:
        return "Buy Watchlist"
    if final_score >= 68 and "weak" not in trend_l:
        return "Accumulate Carefully"
    if final_score >= 55:
        return "Hold / Monitor"
    if risk_score < 35:
        return "High Risk"
    return "Avoid for Now"


def etf_note(final_score: float, risk_score: float, entry_score: float, trend: str, category: str) -> str:
    if final_score >= 78 and entry_score >= 60:
        return "ETF forte e in trend favorevole; valutare solo con coerenza di portafoglio."
    if final_score >= 70 and entry_score < 55:
        return "ETF interessante ma ingresso non ideale: meglio attendere pullback o conferma."
    if risk_score < 40:
        return "Rischio elevato: usare solo come quota satellite e con size ridotta."
    if str(category).lower() == "defensive":
        return "Strumento utile per bilanciare volatilità e rischio macro."
    if "weak" in str(trend).lower():
        return "Trend debole: monitorare prima di aumentare esposizione."
    return "Da monitorare: non è un segnale automatico di acquisto."


def score_etf(base_row: dict[str, Any], metrics: dict[str, Any]) -> dict[str, Any]:
    category = str(base_row.get("Categoria", "Core"))
    trend = str(metrics.get("Trend", "No Data"))
    momentum = safe_float(metrics.get("Momentum Score"), 45)
    risk = safe_float(metrics.get("Risk Score"), 45)
    entry = safe_float(metrics.get("Entry Score"), 45)
    sharpe = safe_float(metrics.get("Sharpe"), 0)
    dd = safe_float(metrics.get("Max Drawdown %"), -30)
    vol = safe_float(metrics.get("Volatilità %"), 25)
    trend_score = safe_float(metrics.get("Trend Score"), 45)

    quality = clamp(50 + sharpe * 18 + min(max(-dd, 0), 45) * -0.45 + max(20 - vol, -20) * 0.45)
    if category.lower() == "core":
        quality = clamp(quality + 5)
    elif category.lower() == "thematic":
        risk = clamp(risk - 5)

    final = clamp(quality * 0.25 + momentum * 0.25 + risk * 0.20 + entry * 0.15 + trend_score * 0.15)
    status = classify_status(final, risk, entry, trend)

    return {
        "ETF Quality Score": round(quality, 1),
        "ETF Momentum Score": round(momentum, 1),
        "ETF Risk Score": round(risk, 1),
        "ETF Entry Score": round(entry, 1),
        "Score Finale": round(final, 1),
        "Stato": status,
        "Note AI": etf_note(final, risk, entry, trend, category),
    }
