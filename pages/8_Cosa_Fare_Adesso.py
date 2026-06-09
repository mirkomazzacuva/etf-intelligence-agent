from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from core.action_guide_engine import build_action_brief
from core.config import ACTION_PLAN_OUTPUT_CSV, INSIGHTS_OUTPUT_CSV
from core.ui_theme import apply_theme, hero, info_panel, mini_cards, style_priority_dataframe

st.set_page_config(page_title="Cosa fare adesso", page_icon="🎯", layout="wide")
apply_theme()
hero(
    "Cosa fare adesso",
    "La pagina più operativa: trasforma score e rischio in priorità comprensibili.",
    "AlphaForge v6 Action First",
)


def load_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


action_plan = load_csv(ACTION_PLAN_OUTPUT_CSV)
insights = load_csv(INSIGHTS_OUTPUT_CSV)
brief = build_action_brief(action_plan, insights)
mini_cards(brief.cards)

info_panel(
    "Regola pratica",
    "Non partire dal ticker che ti piace: parti dal bucket. <b>Azione controllata</b> significa ingresso solo graduale; <b>Attendi pullback</b> significa non inseguire; <b>Rischio da ridurre</b> significa non aumentare size.",
)

focus = brief.focus
if focus.empty:
    st.warning("Nessun action plan disponibile. Esegui aggiornamento completo.")
    st.stop()

buckets = sorted([str(x) for x in focus.get("AF Bucket", pd.Series()).dropna().unique()])
selected = st.multiselect("Bucket operativo", buckets, default=buckets)
view = focus[focus["AF Bucket"].isin(selected)] if selected and "AF Bucket" in focus.columns else focus
cols = ["Priorita", "Ticker", "AF Bucket", "Decisione", "Cosa fare in pratica", "Perche", "Priority Score", "Score Finale", "Entry Zone", "Risk Flag"]
st.dataframe(style_priority_dataframe(view[[c for c in cols if c in view.columns]]), use_container_width=True, hide_index=True)
