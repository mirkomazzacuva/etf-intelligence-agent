from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from core.config import ACTION_PLAN_OUTPUT_CSV, INSIGHTS_OUTPUT_CSV
from core.portfolio_engine import analyze_portfolio, portfolio_template
from core.ui_theme import apply_theme, hero, info_panel, mini_cards, style_priority_dataframe

st.set_page_config(page_title="Portafoglio - AlphaForge", page_icon="💼", layout="wide")
apply_theme()
hero(
    "Portafoglio personale",
    "Carica le tue posizioni e capisci se sono coerenti con score, rischio, concentrazione e decisioni AlphaForge.",
    "AlphaForge v5",
)

info_panel(
    "Come usarla",
    "Carica un file CSV/XLSX con colonne tipo <b>Ticker</b>, <b>Quantità</b>, <b>Prezzo Medio</b>, <b>Valore EUR</b>. Il sistema calcola pesi, P/L indicativo, concentrazione e suggerimenti di miglioramento.",
)

template = portfolio_template()
st.download_button("⬇️ Scarica template CSV", template.to_csv(index=False).encode("utf-8"), "portfolio_template.csv", "text/csv")

uploaded = st.file_uploader("Carica portafoglio CSV/XLSX", type=["csv", "xlsx", "xls"])
use_demo = st.checkbox("Usa template demo", value=False)

if uploaded is None and not use_demo:
    st.caption("Carica un file o spunta 'Usa template demo' per provare.")
    st.stop()

try:
    if use_demo and uploaded is None:
        portfolio_df = template
    elif uploaded.name.lower().endswith((".xlsx", ".xls")):
        portfolio_df = pd.read_excel(uploaded)
    else:
        portfolio_df = pd.read_csv(uploaded)
except Exception as exc:  # noqa: BLE001
    st.error(f"File non leggibile: {exc}")
    st.stop()

action_plan = pd.read_csv(ACTION_PLAN_OUTPUT_CSV) if ACTION_PLAN_OUTPUT_CSV.exists() else pd.DataFrame()
insights = pd.read_csv(INSIGHTS_OUTPUT_CSV) if INSIGHTS_OUTPUT_CSV.exists() else pd.DataFrame()

with st.spinner("Analisi portafoglio in corso..."):
    result = analyze_portfolio(portfolio_df, action_plan=action_plan, insights=insights)

summary = result.summary
mini_cards([
    ("Valore totale", f"€ {summary.get('Valore Totale EUR', 0):,.0f}".replace(",", "."), "Stima indicativa"),
    ("Posizioni", summary.get("Numero Posizioni", 0), "Ticker caricati"),
    ("Peso maggiore", f"{summary.get('Peso maggiore %', 0)}%", "Concentrazione"),
    ("High risk", f"{summary.get('Peso High Risk %', 0)}%", "Peso strumenti rischiosi"),
])

st.subheader("Posizioni analizzate")
pos_cols = ["Ticker", "Valore EUR", "Peso %", "P/L %", "Score Finale", "Priority Score", "Decisione chiara", "Risk Flag", "Suggerimento Portafoglio"]
st.dataframe(style_priority_dataframe(result.positions[[c for c in pos_cols if c in result.positions.columns]]), use_container_width=True, hide_index=True)

st.subheader("Come migliorarlo")
st.dataframe(result.improvements, use_container_width=True, hide_index=True)

if "Peso %" in result.positions.columns and not result.positions.empty:
    fig = px.pie(result.positions, names="Ticker", values="Peso %", title="Distribuzione portafoglio")
    fig.update_layout(height=460, margin=dict(l=10, r=10, t=55, b=10))
    st.plotly_chart(fig, use_container_width=True)

st.caption("Nota: analisi informativa. Prima di operare valuta costi, fiscalità, liquidità, profilo rischio, notizie e obiettivi personali.")
