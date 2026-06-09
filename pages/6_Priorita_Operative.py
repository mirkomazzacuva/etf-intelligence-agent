from __future__ import annotations

import pandas as pd
import streamlit as st

from core.config import ACTION_PLAN_OUTPUT_CSV, INSIGHTS_OUTPUT_CSV
from core.ui_theme import apply_theme, hero, info_panel, style_priority_dataframe

st.set_page_config(page_title="Cosa fare - AlphaForge", page_icon="✅", layout="wide")
apply_theme()
hero(
    "Cosa fare adesso",
    "La pagina più pratica: traduce score, rischio ed entry zone in una decisione chiara e in un'azione da monitorare.",
    "AlphaForge v5",
)

if not ACTION_PLAN_OUTPUT_CSV.exists():
    st.error("Action plan non trovato. Esegui Auto update ETF Intelligence App.")
    st.stop()

action_plan = pd.read_csv(ACTION_PLAN_OUTPUT_CSV)
insights = pd.read_csv(INSIGHTS_OUTPUT_CSV) if INSIGHTS_OUTPUT_CSV.exists() else pd.DataFrame()

info_panel(
    "Regola semplice",
    "Prima guarda <b>Decisione chiara</b>. Poi leggi <b>Cosa fare adesso</b>. Solo alla fine controlla score e dettagli tecnici. Questo evita di trasformare un numero in un acquisto impulsivo.",
)

c1, c2, c3, c4 = st.columns(4)
decisions = action_plan.get("Decisione chiara", pd.Series(dtype=str)).astype(str)
c1.metric("Da guardare oggi", int(decisions.str.contains("Valuta ingresso", case=False, na=False).sum()))
c2.metric("Rischio", int(decisions.str.contains("Riduci|size piccola", case=False, regex=True, na=False).sum()))
c3.metric("Attendi pullback", int(decisions.str.contains("pullback", case=False, na=False).sum()))
c4.metric("Strumenti", len(action_plan))

buckets = sorted([str(x) for x in action_plan.get("Bucket operativo", pd.Series()).dropna().unique()])
selected_buckets = st.multiselect("Bucket operativo", buckets, default=buckets)
view = action_plan.copy()
if selected_buckets and "Bucket operativo" in view.columns:
    view = view[view["Bucket operativo"].isin(selected_buckets)]

cols = ["Bucket operativo", "Ticker", "Score Finale", "Priority Score", "Decisione chiara", "Cosa fare adesso", "Perché", "Entry Zone", "Risk Flag", "Trigger Monitoraggio"]
st.dataframe(style_priority_dataframe(view[[c for c in cols if c in view.columns]].head(80)), use_container_width=True, hide_index=True)

with st.expander("Scenari e dettagli"):
    detail_cols = ["Ticker", "Scenario Base", "Scenario Positivo", "Scenario Negativo", "Azione Pratica"]
    source = insights if not insights.empty else action_plan
    st.dataframe(source[[c for c in detail_cols if c in source.columns]].head(40), use_container_width=True, hide_index=True)
