from __future__ import annotations

import pandas as pd
import streamlit as st

from core.config import RANKING_FILE
from core.ui_theme import apply_theme, hero, mini_cards, style_priority_dataframe

st.set_page_config(page_title="ETF Ranking", page_icon="📊", layout="wide")
apply_theme()
hero("ETF Ranking", "Vista premium per leggere score, rischio, entry zone e stato operativo degli ETF monitorati.", "AlphaForge v4")

if not RANKING_FILE.exists():
    st.error("File ranking non trovato. Esegui prima l'aggiornamento automatico.")
    st.stop()

ranking = pd.read_excel(RANKING_FILE).sort_values("Score Finale", ascending=False, na_position="last")
score_mean = round(pd.to_numeric(ranking.get("Score Finale", pd.Series()), errors="coerce").mean(), 1)
buy_count = int((ranking.get("Stato", pd.Series()) == "Buy Watchlist").sum()) if "Stato" in ranking.columns else 0
priority_mean = round(pd.to_numeric(ranking.get("Priority Score", pd.Series()), errors="coerce").mean(), 1) if "Priority Score" in ranking.columns else "n/d"
mini_cards([
    ("ETF analizzati", len(ranking), "Universo attuale"),
    ("Score medio", score_mean, "Qualità media"),
    ("Buy Watchlist", buy_count, "Da monitorare"),
    ("Priority media", priority_mean, "Priorità operativa"),
])

c1, c2, c3 = st.columns([1.2, 1, 1])
with c1:
    if "Categoria" in ranking.columns:
        categories = sorted(ranking["Categoria"].dropna().unique())
        selected = st.multiselect("Filtra categorie", categories, default=categories)
        if selected:
            ranking = ranking[ranking["Categoria"].isin(selected)]
with c2:
    min_score = st.slider("Score minimo", 0, 100, 0)
with c3:
    sort_col = st.selectbox("Ordina per", [c for c in ["Score Finale", "Priority Score", "ETF Entry Score", "ETF Risk Score"] if c in ranking.columns], index=0)

if sort_col in ranking.columns:
    ranking = ranking[pd.to_numeric(ranking["Score Finale"], errors="coerce").fillna(0) >= min_score]
    ranking = ranking.sort_values(sort_col, ascending=False, na_position="last")

cols = ["Ticker", "Nome ETF", "Categoria", "Tema/Area", "Score Finale", "Priority Score", "Stato", "ETF Quality Score", "ETF Momentum Score", "ETF Risk Score", "ETF Entry Score", "Trend", "Entry Zone", "Risk Flag", "Rendimento 12M %", "Volatilità %", "Max Drawdown %", "Sharpe", "Note AI"]
st.dataframe(style_priority_dataframe(ranking[[c for c in cols if c in ranking.columns]]), use_container_width=True, hide_index=True)
