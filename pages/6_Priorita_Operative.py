from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from core.config import INSIGHTS_OUTPUT_CSV
from core.ui_theme import apply_theme, hero, mini_cards, style_priority_dataframe

st.set_page_config(page_title="Priorità Operative", page_icon="🎯", layout="wide")
apply_theme()
hero("Priorità operative", "Vista pratica per ordinare ETF e azioni per monitoraggio, ingresso graduale o semplice osservazione.", "AlphaForge v4")

if not INSIGHTS_OUTPUT_CSV.exists():
    st.warning("File insights non disponibile. Esegui aggiornamento completo dati.")
    st.stop()

insights = pd.read_csv(INSIGHTS_OUTPUT_CSV)
if insights.empty:
    st.warning("Insights vuoti.")
    st.stop()

top = insights.sort_values("Priority Score", ascending=False, na_position="last").iloc[0] if "Priority Score" in insights.columns else insights.iloc[0]
mini_cards([
    ("Strumenti", len(insights), "ETF + watchlist"),
    ("Top priorità", top.get("Ticker", "n/d"), top.get("Azione Suggerita", "")),
    ("Priority media", round(pd.to_numeric(insights.get("Priority Score", pd.Series()), errors="coerce").mean(), 1), "Media monitoraggio"),
    ("Risk high", int(insights.get("Risk Flag", pd.Series(dtype=str)).astype(str).str.lower().str.contains("high|alto|risk").sum()) if "Risk Flag" in insights.columns else 0, "Size prudente"),
])

c1, c2, c3 = st.columns(3)
status_options = sorted([str(x) for x in insights.get("Azione Suggerita", pd.Series()).dropna().unique()])
type_options = sorted([str(x) for x in insights.get("Tipo", pd.Series()).dropna().unique()])
with c1:
    selected_actions = st.multiselect("Azioni suggerite", status_options, default=status_options)
with c2:
    selected_types = st.multiselect("Tipo", type_options, default=type_options)
with c3:
    min_priority = st.slider("Priority score minimo", 0, 100, 50)

filtered = insights.copy()
if selected_actions and "Azione Suggerita" in filtered.columns:
    filtered = filtered[filtered["Azione Suggerita"].isin(selected_actions)]
if selected_types and "Tipo" in filtered.columns:
    filtered = filtered[filtered["Tipo"].isin(selected_types)]
if "Priority Score" in filtered.columns:
    filtered = filtered[pd.to_numeric(filtered["Priority Score"], errors="coerce").fillna(0) >= min_priority]

if {"Priority Score", "Score Finale", "Ticker"}.issubset(filtered.columns):
    fig = px.bar(filtered.head(15), x="Ticker", y="Priority Score", hover_data=[c for c in ["Score Finale", "Azione Suggerita", "Entry Zone", "Risk Flag"] if c in filtered.columns], title="Top priorità")
    fig.update_layout(height=460, margin=dict(l=10, r=10, t=55, b=10))
    st.plotly_chart(fig, use_container_width=True)

cols = ["Ticker", "Tipo", "Score Finale", "Priority Score", "Azione Suggerita", "Stato", "Trend", "Entry Zone", "Risk Flag", "Trigger Monitoraggio", "Scenario Base", "Scenario Negativo"]
st.dataframe(style_priority_dataframe(filtered[[c for c in cols if c in filtered.columns]]), use_container_width=True, hide_index=True)
