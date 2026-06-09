from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from core.config import INSIGHTS_OUTPUT_CSV

st.set_page_config(page_title="Priorità Operative", page_icon="🎯", layout="wide")
st.title("🎯 Priorità operative AlphaForge")
st.caption("Vista pratica per ordinare ETF e azioni per priorità di monitoraggio, non per acquisto automatico.")

if not INSIGHTS_OUTPUT_CSV.exists():
    st.warning("File insights non disponibile. Esegui aggiornamento completo dati.")
    st.stop()

insights = pd.read_csv(INSIGHTS_OUTPUT_CSV)
if insights.empty:
    st.warning("Insights vuoti.")
    st.stop()

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

st.metric("Strumenti filtrati", len(filtered))
if {"Priority Score", "Score Finale", "Ticker"}.issubset(filtered.columns):
    fig = px.bar(filtered.head(15), x="Ticker", y="Priority Score", hover_data=[c for c in ["Score Finale", "Azione Suggerita", "Entry Zone", "Risk Flag"] if c in filtered.columns], title="Top priorità")
    st.plotly_chart(fig, use_container_width=True)

cols = ["Ticker", "Tipo", "Score Finale", "Priority Score", "Azione Suggerita", "Stato", "Trend", "Entry Zone", "Risk Flag", "Trigger Monitoraggio", "Scenario Base", "Scenario Negativo"]
st.dataframe(filtered[[c for c in cols if c in filtered.columns]], use_container_width=True, hide_index=True)
