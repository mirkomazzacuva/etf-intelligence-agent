from __future__ import annotations

from typing import Any

import pandas as pd

from core.signal_engine import build_scenarios


def _num(row: pd.Series | dict[str, Any], key: str, default: float = 0.0) -> float:
    try:
        value = row.get(key, default) if isinstance(row, dict) else row.get(key, default)
        if pd.isna(value):
            return default
        return float(value)
    except Exception:  # noqa: BLE001
        return default


def priority_score(row: pd.Series | dict[str, Any]) -> float:
    score = _num(row, "Score Finale")
    entry = _num(row, "Entry Score", _num(row, "Stock Entry Score", 50))
    risk = _num(row, "Risk Score", _num(row, "Stock Risk Score", 50))
    momentum = _num(row, "Momentum Score", _num(row, "Stock Momentum Score", 50))
    extended_penalty = max(_num(row, "Distanza MA50 %") - 7, 0) * 1.8
    high_risk_penalty = 12 if str((row.get("Risk Flag", "") if isinstance(row, dict) else row.get("Risk Flag", ""))).lower().startswith("high") else 0
    return round(max(0.0, min(100.0, score * 0.45 + entry * 0.25 + risk * 0.15 + momentum * 0.15 - extended_penalty - high_risk_penalty)), 1)


def action_label(row: pd.Series | dict[str, Any]) -> str:
    p = priority_score(row)
    state = str(row.get("Stato", "") if isinstance(row, dict) else row.get("Stato", "")).lower()
    entry_zone = str(row.get("Entry Zone", "") if isinstance(row, dict) else row.get("Entry Zone", "")).lower()
    risk_flag = str(row.get("Risk Flag", "") if isinstance(row, dict) else row.get("Risk Flag", "")).lower()
    if "high" in risk_flag:
        return "Ridurre size / solo monitoraggio"
    if p >= 75 and "extended" not in entry_zone:
        return "Priorità watchlist"
    if p >= 62:
        return "Monitorare ingresso graduale"
    if "avoid" in state or "weak" in state:
        return "Evitare per ora"
    return "Osservare"


def build_insights_table(frames: list[pd.DataFrame]) -> pd.DataFrame:
    available = [df for df in frames if df is not None and not df.empty]
    if not available:
        return pd.DataFrame()
    merged = pd.concat(available, ignore_index=True, sort=False)
    if "Ticker" not in merged.columns:
        return pd.DataFrame()
    merged = merged.drop_duplicates(subset=["Ticker"], keep="first").copy()
    merged["Priority Score"] = merged.apply(priority_score, axis=1)
    merged["Azione Suggerita"] = merged.apply(action_label, axis=1)
    for key in ["Scenario Base", "Scenario Positivo", "Scenario Negativo", "Azione Pratica"]:
        merged[key] = merged.apply(lambda r, k=key: build_scenarios(r.to_dict()).get(k, ""), axis=1)
    merged = merged.sort_values(["Priority Score", "Score Finale"], ascending=False, na_position="last")
    preferred = [
        "Ticker", "Nome", "Nome ETF", "Tipo", "Categoria", "Score Finale", "Priority Score", "Azione Suggerita", "Stato",
        "Trend", "Entry Zone", "Risk Flag", "Trigger Monitoraggio", "Rendimento 3M %", "Rendimento 12M %",
        "Volatilità %", "Max Drawdown %", "P/E", "Forward P/E", "Scenario Base", "Scenario Positivo", "Scenario Negativo", "Azione Pratica", "Note AI",
    ]
    cols = [c for c in preferred if c in merged.columns] + [c for c in merged.columns if c not in preferred]
    return merged[cols]


def assistant_answer_for_row(row: dict[str, Any]) -> str:
    scenarios = build_scenarios(row)
    name = row.get("Nome") or row.get("Nome ETF") or row.get("Ticker", "strumento")
    return (
        f"**{row.get('Ticker', '')} — {name}**\n\n"
        f"Score finale: **{row.get('Score Finale', 'n/d')}**. Priority score: **{row.get('Priority Score', priority_score(row))}**. "
        f"Stato: **{row.get('Stato', 'n/d')}**. Trend: **{row.get('Trend', 'n/d')}**.\n\n"
        f"**Scenario base:** {scenarios['Scenario Base']}\n\n"
        f"**Scenario positivo:** {scenarios['Scenario Positivo']}\n\n"
        f"**Scenario negativo:** {scenarios['Scenario Negativo']}\n\n"
        f"**Azione pratica:** {scenarios['Azione Pratica']}\n\n"
        "Nota: analisi informativa basata su dati disponibili, non consulenza finanziaria personalizzata."
    )
