from __future__ import annotations

import pandas as pd
import streamlit as st

from core.config import RANKING_FILE

st.set_page_config(page_title="ETF Ranking", page_icon="📊", layout="wide")
st.title("📊 ETF Ranking")

if not RANKING_FILE.exists():
    st.error("File ranking non trovato. Esegui prima l'aggiornamento automatico.")
    st.stop()

ranking = pd.read_excel(RANKING_FILE).sort_values("Score Finale", ascending=False, na_position="last")

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("ETF analizzati", len(ranking))
with col2:
    st.metric("Score medio", round(pd.to_numeric(ranking["Score Finale"], errors="coerce").mean(), 1))
with col3:
    st.metric("Buy Watchlist", int((ranking["Stato"] == "Buy Watchlist").sum()) if "Stato" in ranking.columns else 0)

if "Categoria" in ranking.columns:
    categories = sorted(ranking["Categoria"].dropna().unique())
    selected = st.multiselect("Filtra categorie", categories, default=categories)
    if selected:
        ranking = ranking[ranking["Categoria"].isin(selected)]

cols = ["Ticker", "Nome ETF", "Categoria", "Tema/Area", "Score Finale", "Stato", "ETF Quality Score", "ETF Momentum Score", "ETF Risk Score", "ETF Entry Score", "Trend", "Rendimento 12M %", "Volatilità %", "Max Drawdown %", "Sharpe", "Note AI"]
st.dataframe(ranking[[c for c in cols if c in ranking.columns]], use_container_width=True, hide_index=True)
