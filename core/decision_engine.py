from __future__ import annotations

from typing import Any

import pandas as pd


def _num(value: Any, default: float = 0.0) -> float:
    try:
        if pd.isna(value):
            return default
        return float(value)
    except Exception:  # noqa: BLE001
        return default


def _txt(value: Any) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:  # noqa: BLE001
        pass
    return str(value)


def _first(row: pd.Series, keys: list[str], default: str = "") -> str:
    for key in keys:
        if key in row and _txt(row.get(key)):
            return _txt(row.get(key))
    return default


def _status_family(row: pd.Series) -> tuple[str, int]:
    priority = _num(row.get("Priority Score"), _num(row.get("Score Finale"), 0))
    score = _num(row.get("Score Finale"), 0)
    entry = _txt(row.get("Entry Zone")).lower()
    risk = _txt(row.get("Risk Flag")).lower()
    state = _txt(row.get("Stato")).lower()
    action = _txt(row.get("Azione Suggerita")).lower()
    trend = _txt(row.get("Trend")).lower()

    high_risk = any(x in risk for x in ["high", "alto", "medium-high"]) or "ridurre" in action
    extended = any(x in entry for x in ["extended", "pullback", "wait"])
    weak = any(x in state + trend for x in ["weak", "avoid", "evitare", "negative", "negativo"])

    if high_risk and score < 70:
        return "🟥 Riduci rischio / non aumentare", 1
    if weak:
        return "⚪ Evita per ora", 5
    if priority >= 78 and not extended and not high_risk:
        return "🟢 Valuta ingresso graduale", 2
    if extended and score >= 62:
        return "🟠 Attendi pullback", 3
    if priority >= 62:
        return "🟡 Metti alert / monitora", 4
    if high_risk:
        return "🟥 Solo size piccola", 4
    return "⚪ Osserva", 6


def _bucket(decision: str) -> str:
    if "Valuta" in decision:
        return "1. Da guardare oggi"
    if "Riduci" in decision or "size piccola" in decision:
        return "2. Rischio da controllare"
    if "pullback" in decision:
        return "3. Interessanti ma da attendere"
    if "alert" in decision or "monitora" in decision:
        return "4. Alert / monitoraggio"
    return "5. Solo osservazione"


def _why(row: pd.Series) -> str:
    parts: list[str] = []
    score = _num(row.get("Score Finale"), -1)
    priority = _num(row.get("Priority Score"), -1)
    if score >= 0:
        parts.append(f"score {score:.1f}")
    if priority >= 0:
        parts.append(f"priority {priority:.1f}")
    for col in ["Trend", "Entry Zone", "Risk Flag"]:
        val = _txt(row.get(col))
        if val:
            parts.append(f"{col.lower()}: {val}")
    return "; ".join(parts) if parts else "Dati insufficienti: controllare manualmente."


def _next_step(row: pd.Series, decision: str) -> str:
    trigger = _txt(row.get("Trigger Monitoraggio"))
    support = _txt(row.get("Supporto 60D"))
    resistance = _txt(row.get("Resistenza 60D"))
    if "Valuta ingresso" in decision:
        return "Non entrare a mercato alla cieca: valuta ingresso graduale, size piccola e conferma su trend/supporti."
    if "pullback" in decision:
        return f"Non inseguire il prezzo: imposta alert su pullback o tenuta supporto. Supporto 60D: {support or 'n/d'}."
    if "Riduci" in decision:
        return "Non aumentare esposizione: controlla peso in portafoglio, stop mentale e correlazione con posizioni simili."
    if "alert" in decision or "monitora" in decision:
        return f"Imposta alert prezzo/news. Resistenza 60D: {resistance or 'n/d'}. Trigger: {trigger or 'trend e volatilità'}."
    if "Evita" in decision:
        return "Lascia fuori dalla lista operativa finché trend, score o rischio non migliorano."
    return "Tieni in osservazione senza azione immediata; rivaluta dopo aggiornamento dati o news rilevanti."


def build_action_plan(ranking: pd.DataFrame | None, watchlist: pd.DataFrame | None, insights: pd.DataFrame | None) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    if insights is not None and not insights.empty:
        frames.append(insights.copy())
    else:
        if ranking is not None and not ranking.empty:
            frames.append(ranking.copy())
        if watchlist is not None and not watchlist.empty:
            frames.append(watchlist.copy())
    if not frames:
        return pd.DataFrame()

    df = pd.concat(frames, ignore_index=True, sort=False)
    if "Ticker" not in df.columns:
        return pd.DataFrame()
    df["Ticker"] = df["Ticker"].astype(str).str.upper().str.strip()
    df = df[df["Ticker"] != ""].drop_duplicates(subset=["Ticker"], keep="first").copy()
    if "Priority Score" not in df.columns:
        df["Priority Score"] = pd.to_numeric(df.get("Score Finale", 0), errors="coerce").fillna(0)

    decisions: list[str] = []
    ranks: list[int] = []
    for _, row in df.iterrows():
        decision, rank = _status_family(row)
        decisions.append(decision)
        ranks.append(rank)
    df["Decisione chiara"] = decisions
    df["Bucket operativo"] = df["Decisione chiara"].map(_bucket)
    df["Perché"] = df.apply(_why, axis=1)
    df["Cosa fare adesso"] = df.apply(lambda row: _next_step(row, str(row.get("Decisione chiara", ""))), axis=1)
    df["Ordine Bucket"] = ranks
    df["Nome Strumento"] = df.apply(lambda r: _first(r, ["Nome", "Nome ETF"], r.get("Ticker", "")), axis=1)
    df["Tipo"] = df.get("Tipo", df.get("Categoria", "Strumento"))

    preferred = [
        "Bucket operativo", "Ticker", "Nome Strumento", "Tipo", "Score Finale", "Priority Score", "Decisione chiara",
        "Cosa fare adesso", "Perché", "Entry Zone", "Risk Flag", "Trigger Monitoraggio", "Scenario Base",
        "Scenario Positivo", "Scenario Negativo", "Azione Pratica", "Stato", "Trend", "Supporto 60D", "Resistenza 60D",
    ]
    cols = [c for c in preferred if c in df.columns] + [c for c in df.columns if c not in preferred and c != "Ordine Bucket"]
    df = df.sort_values(["Ordine Bucket", "Priority Score", "Score Finale"], ascending=[True, False, False], na_position="last")
    return df[cols]


def action_summary(action_plan: pd.DataFrame | None) -> dict[str, object]:
    if action_plan is None or action_plan.empty:
        return {
            "Da guardare oggi": 0,
            "Rischio da controllare": 0,
            "Da attendere": 0,
            "Prima decisione": "Nessun dato",
        }
    decisions = action_plan.get("Decisione chiara", pd.Series(dtype=str)).astype(str)
    return {
        "Da guardare oggi": int(decisions.str.contains("Valuta ingresso", case=False, na=False).sum()),
        "Rischio da controllare": int(decisions.str.contains("Riduci|size piccola", case=False, regex=True, na=False).sum()),
        "Da attendere": int(decisions.str.contains("pullback", case=False, na=False).sum()),
        "Prima decisione": str(action_plan.iloc[0].get("Decisione chiara", "n/d")),
    }
