from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

TRADING_DAYS = 252


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or (isinstance(value, float) and math.isnan(value)):
            return default
        return float(value)
    except Exception:  # noqa: BLE001
        return default


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, float(value)))


def pct_return(close: pd.Series, days: int) -> float:
    close = close.dropna()
    if len(close) <= days:
        return float("nan")
    start = float(close.iloc[-days - 1])
    end = float(close.iloc[-1])
    if start == 0:
        return float("nan")
    return (end / start - 1.0) * 100.0


def max_drawdown_pct(close: pd.Series) -> float:
    close = close.dropna()
    if len(close) < 2:
        return float("nan")
    running_max = close.cummax()
    drawdown = close / running_max - 1.0
    return float(drawdown.min() * 100.0)


def cagr_pct(close: pd.Series) -> float:
    close = close.dropna()
    if len(close) < 30:
        return float("nan")
    years = len(close) / TRADING_DAYS
    if years <= 0 or close.iloc[0] <= 0:
        return float("nan")
    return float(((close.iloc[-1] / close.iloc[0]) ** (1 / years) - 1) * 100)


def calculate_price_metrics(price_df: pd.DataFrame) -> dict[str, Any]:
    if price_df is None or price_df.empty or "Close" not in price_df.columns:
        return {
            "Current Price": np.nan,
            "Rendimento 1M %": np.nan,
            "Rendimento 3M %": np.nan,
            "Rendimento 6M %": np.nan,
            "Rendimento 12M %": np.nan,
            "CAGR %": np.nan,
            "Volatilità %": np.nan,
            "Max Drawdown %": np.nan,
            "Sharpe": np.nan,
            "MA50": np.nan,
            "MA200": np.nan,
            "Trend": "No Data",
            "Trend Score": 0.0,
            "Momentum Score": 0.0,
            "Risk Score": 100.0,
            "Entry Score": 0.0,
            "Data Points": 0,
        }
    close = pd.to_numeric(price_df["Close"], errors="coerce").dropna()
    if close.empty:
        return calculate_price_metrics(pd.DataFrame())

    daily = close.pct_change().dropna()
    vol = float(daily.std() * math.sqrt(TRADING_DAYS) * 100) if len(daily) > 5 else float("nan")
    cagr = cagr_pct(close)
    drawdown = max_drawdown_pct(close)
    sharpe = float(cagr / vol) if vol and not math.isnan(vol) and vol > 0 and not math.isnan(cagr) else float("nan")
    ma50 = float(close.rolling(50).mean().iloc[-1]) if len(close) >= 50 else float("nan")
    ma200 = float(close.rolling(200).mean().iloc[-1]) if len(close) >= 200 else float("nan")
    current = float(close.iloc[-1])

    above_ma50 = not math.isnan(ma50) and current >= ma50
    above_ma200 = not math.isnan(ma200) and current >= ma200
    if above_ma50 and above_ma200:
        trend = "Bullish"
        trend_score = 85.0
    elif above_ma200:
        trend = "Constructive"
        trend_score = 65.0
    elif above_ma50:
        trend = "Recovery"
        trend_score = 55.0
    elif not math.isnan(ma200):
        trend = "Weak"
        trend_score = 35.0
    else:
        trend = "Insufficient History"
        trend_score = 45.0

    r1 = pct_return(close, 21)
    r3 = pct_return(close, 63)
    r6 = pct_return(close, 126)
    r12 = pct_return(close, 252)
    momentum_score = clamp(50 + safe_float(r3) * 1.4 + safe_float(r6) * 0.6 + safe_float(r12) * 0.25)
    risk_score = clamp(100 - safe_float(vol, 35) * 1.2 + safe_float(drawdown, -35) * 0.8)
    distance_ma50 = (current / ma50 - 1) * 100 if ma50 and not math.isnan(ma50) and ma50 > 0 else 0
    entry_score = clamp(70 + trend_score * 0.15 - max(distance_ma50 - 4, 0) * 4 + min(distance_ma50, 0) * 1.5)

    return {
        "Current Price": round(current, 4),
        "Rendimento 1M %": round(r1, 2) if not math.isnan(r1) else np.nan,
        "Rendimento 3M %": round(r3, 2) if not math.isnan(r3) else np.nan,
        "Rendimento 6M %": round(r6, 2) if not math.isnan(r6) else np.nan,
        "Rendimento 12M %": round(r12, 2) if not math.isnan(r12) else np.nan,
        "CAGR %": round(cagr, 2) if not math.isnan(cagr) else np.nan,
        "Volatilità %": round(vol, 2) if not math.isnan(vol) else np.nan,
        "Max Drawdown %": round(drawdown, 2) if not math.isnan(drawdown) else np.nan,
        "Sharpe": round(sharpe, 2) if not math.isnan(sharpe) else np.nan,
        "MA50": round(ma50, 4) if not math.isnan(ma50) else np.nan,
        "MA200": round(ma200, 4) if not math.isnan(ma200) else np.nan,
        "Trend": trend,
        "Trend Score": round(trend_score, 1),
        "Momentum Score": round(momentum_score, 1),
        "Risk Score": round(risk_score, 1),
        "Entry Score": round(entry_score, 1),
        "Data Points": int(len(close)),
    }
