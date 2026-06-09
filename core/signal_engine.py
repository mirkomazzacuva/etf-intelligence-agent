from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

from core.metrics import clamp, safe_float


def _fmt_pct(value: float | int | None) -> str:
    try:
        if value is None or pd.isna(value):
            return "n/d"
        return f"{float(value):.1f}%"
    except Exception:  # noqa: BLE001
        return "n/d"


def _fmt_price(value: float | int | None) -> str:
    try:
        if value is None or pd.isna(value):
            return "n/d"
        return f"{float(value):.2f}"
    except Exception:  # noqa: BLE001
        return "n/d"


def calculate_signal_levels(price_df: pd.DataFrame, metrics: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build simple support/resistance and entry-quality levels from recent prices.

    This is intentionally conservative: it does not produce a buy/sell order,
    but a practical map for monitoring price behaviour.
    """
    metrics = metrics or {}
    if price_df is None or price_df.empty or "Close" not in price_df.columns:
        return {
            "Supporto 20D": np.nan,
            "Supporto 60D": np.nan,
            "Resistenza 20D": np.nan,
            "Resistenza 60D": np.nan,
            "Distanza MA50 %": np.nan,
            "Distanza MA200 %": np.nan,
            "Entry Zone": "No Data",
            "Risk Flag": "No Data",
            "Trigger Monitoraggio": "Dati prezzo insufficienti.",
        }

    close = pd.to_numeric(price_df["Close"], errors="coerce").dropna()
    if close.empty:
        return calculate_signal_levels(pd.DataFrame(), metrics)
    current = float(close.iloc[-1])
    support_20 = float(close.tail(min(20, len(close))).min())
    support_60 = float(close.tail(min(60, len(close))).min())
    resistance_20 = float(close.tail(min(20, len(close))).max())
    resistance_60 = float(close.tail(min(60, len(close))).max())

    ma50 = safe_float(metrics.get("MA50"), float("nan"))
    ma200 = safe_float(metrics.get("MA200"), float("nan"))
    dist_ma50 = (current / ma50 - 1.0) * 100 if ma50 and not math.isnan(ma50) else np.nan
    dist_ma200 = (current / ma200 - 1.0) * 100 if ma200 and not math.isnan(ma200) else np.nan

    trend = str(metrics.get("Trend", "")).lower()
    risk_score = safe_float(metrics.get("Risk Score"), safe_float(metrics.get("Stock Risk Score"), 45))
    entry_score = safe_float(metrics.get("Entry Score"), safe_float(metrics.get("Stock Entry Score"), 45))
    drawdown = safe_float(metrics.get("Max Drawdown %"), 0)
    vol = safe_float(metrics.get("Volatilità %"), 0)

    if "weak" in trend:
        entry_zone = "Wait for trend repair"
    elif entry_score >= 70 and risk_score >= 45:
        entry_zone = "Constructive entry zone"
    elif entry_score >= 55:
        entry_zone = "Monitor / partial entry only"
    elif not pd.isna(dist_ma50) and dist_ma50 > 8:
        entry_zone = "Extended - wait pullback"
    else:
        entry_zone = "Neutral / wait confirmation"

    if risk_score < 35 or drawdown < -35 or vol > 38:
        risk_flag = "High risk"
    elif risk_score < 50 or drawdown < -25:
        risk_flag = "Medium-high risk"
    else:
        risk_flag = "Normal risk"

    triggers = []
    if not pd.isna(dist_ma50):
        if dist_ma50 > 8:
            triggers.append(f"prezzo {dist_ma50:.1f}% sopra MA50: evitare inseguimento")
        elif dist_ma50 < -4:
            triggers.append(f"prezzo {abs(dist_ma50):.1f}% sotto MA50: attendere recupero")
        else:
            triggers.append("prezzo vicino a MA50: monitorare conferma")
    if resistance_20 and current >= resistance_20 * 0.99:
        triggers.append("vicino a resistenza 20D: attenzione a falso breakout")
    if support_60 and current <= support_60 * 1.05:
        triggers.append("vicino a supporto 60D: controllare tenuta e volumi")
    if not triggers:
        triggers.append("monitorare trend, supporti, trimestrali/news e volatilità")

    return {
        "Supporto 20D": round(support_20, 4),
        "Supporto 60D": round(support_60, 4),
        "Resistenza 20D": round(resistance_20, 4),
        "Resistenza 60D": round(resistance_60, 4),
        "Distanza MA50 %": round(float(dist_ma50), 2) if not pd.isna(dist_ma50) else np.nan,
        "Distanza MA200 %": round(float(dist_ma200), 2) if not pd.isna(dist_ma200) else np.nan,
        "Entry Zone": entry_zone,
        "Risk Flag": risk_flag,
        "Trigger Monitoraggio": "; ".join(triggers),
    }


def build_scenarios(row: dict[str, Any]) -> dict[str, str]:
    ticker = str(row.get("Ticker", "strumento"))
    trend = str(row.get("Trend", "n/d"))
    status = str(row.get("Stato", "n/d"))
    score = row.get("Score Finale", "n/d")
    support = _fmt_price(row.get("Supporto 60D"))
    resistance = _fmt_price(row.get("Resistenza 60D"))
    risk_flag = str(row.get("Risk Flag", "n/d"))
    entry_zone = str(row.get("Entry Zone", "n/d"))
    dist = _fmt_pct(row.get("Distanza MA50 %"))

    base = (
        f"{ticker}: scenario base {status}, score {score}, trend {trend}. "
        f"Entry zone: {entry_zone}. Distanza da MA50: {dist}."
    )
    positive = (
        f"Scenario positivo: conferma sopra area {resistance} con momentum stabile; "
        "valutare solo se rischio e size restano coerenti."
    )
    negative = (
        f"Scenario negativo: perdita area {support} o peggioramento trend; "
        f"rischio attuale: {risk_flag}."
    )
    action = (
        "Azione pratica: non trasformare lo score in ordine automatico; usa watchlist, alert prezzo, "
        "controllo news/trimestrali e dimensione posizione."
    )
    return {
        "Scenario Base": base,
        "Scenario Positivo": positive,
        "Scenario Negativo": negative,
        "Azione Pratica": action,
    }
