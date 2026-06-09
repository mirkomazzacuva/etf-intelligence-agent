from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd


ACTION_ORDER = {
    "Da fare ora": 1,
    "Da guardare oggi": 2,
    "Ingresso graduale": 3,
    "Attendi pullback": 4,
    "Monitora": 5,
    "Rischio da ridurre": 6,
    "Evita per ora": 7,
    "Portafoglio": 8,
}


@dataclass
class ActionBrief:
    cards: list[tuple[str, Any, str]]
    focus: pd.DataFrame
    narrative: list[str]


def _num(value: object, default: float = 0.0) -> float:
    try:
        if pd.isna(value):
            return default
        if isinstance(value, str):
            value = value.replace("%", "").replace("€", "").replace(".", "").replace(",", ".").strip()
        return float(value)
    except Exception:  # noqa: BLE001
        return default


def _text(row: pd.Series, *cols: str) -> str:
    for col in cols:
        if col in row.index and str(row.get(col, "")).strip():
            return str(row.get(col, "")).strip()
    return ""


def _bucket(row: pd.Series) -> str:
    decision = _text(row, "Decisione chiara", "Azione Suggerita", "Stato").lower()
    entry = _text(row, "Entry Zone").lower()
    risk = _text(row, "Risk Flag").lower()
    priority = _num(row.get("Priority Score", row.get("Score Finale", 0)))
    score = _num(row.get("Score Finale", 0))

    if "riduci" in decision or "high" in risk or "alto" in risk:
        return "Rischio da ridurre"
    if "evita" in decision or "avoid" in decision:
        return "Evita per ora"
    if "pullback" in decision or "pullback" in entry or "attendi" in decision:
        return "Attendi pullback"
    if "valuta ingresso" in decision and priority >= 72:
        return "Da fare ora"
    if "valuta ingresso" in decision or "graduale" in decision:
        return "Ingresso graduale"
    if priority >= 72 and score >= 68:
        return "Da guardare oggi"
    return "Monitora"


def _plain_action(row: pd.Series) -> str:
    bucket = str(row.get("AF Bucket", _bucket(row)))
    ticker = _text(row, "Ticker")
    entry = _text(row, "Entry Zone")
    risk = _text(row, "Risk Flag")
    trigger = _text(row, "Trigger Monitoraggio", "Cosa monitorare prima")
    base = _text(row, "Cosa fare adesso", "Azione Pratica", "Azione Suggerita")

    if bucket == "Da fare ora":
        return f"{ticker}: valuta ingresso solo graduale. Prima controlla {trigger or 'supporto/resistenza e news recenti'}."
    if bucket == "Ingresso graduale":
        return f"{ticker}: costruisci solo a piccoli step; non usare tutto il capitale in un unico ingresso."
    if bucket == "Attendi pullback":
        return f"{ticker}: non inseguire. Metti alert su pullback o ritorno in zona tecnica migliore."
    if bucket == "Rischio da ridurre":
        return f"{ticker}: non aumentare. Controlla size, stop mentale e peso nel portafoglio."
    if bucket == "Evita per ora":
        return f"{ticker}: lascia fuori dalla lista operativa finche' score, trend o rischio non migliorano."
    if bucket == "Da guardare oggi":
        return f"{ticker}: priorita' alta, ma attendi conferma prezzo/volume prima di agire."
    if base:
        return f"{ticker}: {base}"
    return f"{ticker}: monitora senza azioni immediate. Entry: {entry or 'n/d'}; rischio: {risk or 'n/d'}."


def build_focus_board(action_plan: pd.DataFrame | None, insights: pd.DataFrame | None = None, limit: int = 14) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    if action_plan is not None and not action_plan.empty:
        frames.append(action_plan.copy())
    if insights is not None and not insights.empty:
        frames.append(insights.copy())
    if not frames:
        return pd.DataFrame(columns=["Priorita", "Ticker", "AF Bucket", "Decisione", "Cosa fare in pratica", "Perche", "Priority Score", "Score Finale", "Entry Zone", "Risk Flag"])

    df = pd.concat(frames, ignore_index=True, sort=False)
    if "Ticker" not in df.columns:
        return pd.DataFrame()
    df["Ticker"] = df["Ticker"].astype(str).str.upper().str.strip()
    df = df[df["Ticker"] != ""].drop_duplicates(subset=["Ticker"], keep="first").copy()
    df["AF Bucket"] = df.apply(_bucket, axis=1)
    df["AF Ordine"] = df["AF Bucket"].map(ACTION_ORDER).fillna(99).astype(int)
    df["Priority Score"] = pd.to_numeric(df.get("Priority Score", df.get("Score Finale", 0)), errors="coerce").fillna(0).round(1)
    df["Score Finale"] = pd.to_numeric(df.get("Score Finale", 0), errors="coerce").fillna(0).round(1)
    df["Decisione"] = df.apply(lambda r: _text(r, "Decisione chiara", "Azione Suggerita", "Stato"), axis=1)
    df["Cosa fare in pratica"] = df.apply(_plain_action, axis=1)
    df["Perche"] = df.apply(lambda r: _text(r, "Perché", "Perche", "Note AI", "Scenario Base"), axis=1)
    df["Priorita"] = df["AF Bucket"].map({
        "Da fare ora": "1 - Azione controllata",
        "Da guardare oggi": "2 - Watchlist alta",
        "Ingresso graduale": "3 - Entrata a step",
        "Attendi pullback": "4 - Aspetta prezzo migliore",
        "Monitora": "5 - Monitoraggio",
        "Rischio da ridurre": "6 - Controllo rischio",
        "Evita per ora": "7 - Fuori lista",
    }).fillna("5 - Monitoraggio")
    df = df.sort_values(["AF Ordine", "Priority Score", "Score Finale"], ascending=[True, False, False], na_position="last")
    cols = ["Priorita", "Ticker", "AF Bucket", "Decisione", "Cosa fare in pratica", "Perche", "Priority Score", "Score Finale", "Entry Zone", "Risk Flag", "Trigger Monitoraggio"]
    return df[[c for c in cols if c in df.columns]].head(limit).reset_index(drop=True)


def action_cards(action_plan: pd.DataFrame | None, insights: pd.DataFrame | None = None) -> list[tuple[str, Any, str]]:
    focus = build_focus_board(action_plan, insights, limit=999)
    if focus.empty:
        return [
            ("Azione controllata", 0, "Nessun dato"),
            ("Aspetta pullback", 0, "Nessun dato"),
            ("Controllo rischio", 0, "Nessun dato"),
            ("Monitoraggio", 0, "Nessun dato"),
        ]
    buckets = focus.get("AF Bucket", pd.Series(dtype=str)).astype(str)
    top = str(focus.iloc[0].get("Ticker", "n/d"))
    return [
        ("Da fare ora", int((buckets == "Da fare ora").sum()), f"Prima priorita': {top}"),
        ("Aspetta pullback", int((buckets == "Attendi pullback").sum()), "Non inseguire prezzi estesi"),
        ("Controllo rischio", int((buckets == "Rischio da ridurre").sum()), "Size e stop mentale"),
        ("Monitoraggio", int((buckets == "Monitora").sum()), "Nessuna urgenza operativa"),
    ]


def narrative(action_plan: pd.DataFrame | None, insights: pd.DataFrame | None = None) -> list[str]:
    focus = build_focus_board(action_plan, insights, limit=5)
    if focus.empty:
        return ["Non ci sono dati sufficienti per generare un piano operativo."]
    lines = []
    for _, row in focus.iterrows():
        lines.append(str(row.get("Cosa fare in pratica", "")))
    return [line for line in lines if line]


def build_action_brief(action_plan: pd.DataFrame | None, insights: pd.DataFrame | None = None) -> ActionBrief:
    focus = build_focus_board(action_plan, insights)
    return ActionBrief(cards=action_cards(action_plan, insights), focus=focus, narrative=narrative(action_plan, insights))
