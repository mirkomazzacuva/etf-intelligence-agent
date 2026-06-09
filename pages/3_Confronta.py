from __future__ import annotations

import plotly.express as px
import streamlit as st

from core.compare_engine import compare_tickers, comparison_summary, extract_tickers
from core.config import DEFAULT_MODEL_BASKETS
from core.ui_theme import apply_theme, hero, info_panel, style_priority_dataframe

st.set_page_config(page_title="Confronta", page_icon="⚖️", layout="wide")
apply_theme()
hero("Confronta strumenti", "Confronto pratico tra ETF e azioni con score, priority, entry zone e rischio.", "AlphaForge v4")

basket = st.selectbox("Basket rapido", ["Custom"] + list(DEFAULT_MODEL_BASKETS.keys()))
default_text = "NVDA, AMD, ASML.AS" if basket == "Custom" else ", ".join(DEFAULT_MODEL_BASKETS[basket])
text = st.text_input("Ticker da confrontare", value=default_text)
tickers = extract_tickers(text)
st.caption(f"Riconosciuti: {', '.join(tickers) if tickers else 'nessuno'}")

if st.button("Confronta", type="primary", use_container_width=True) and tickers:
    with st.spinner("Confronto in corso..."):
        df = compare_tickers(tickers)
    info_panel("Sintesi confronto", "<br>".join(f"• {line}" for line in comparison_summary(df)))

    if not df.empty and {"Score Finale", "Priority Score", "Ticker"}.issubset(df.columns):
        fig = px.scatter(df, x="Score Finale", y="Priority Score", hover_name="Ticker", size="Rendimento 3M %" if "Rendimento 3M %" in df.columns else None, title="Score finale vs priorità operativa")
        fig.update_layout(height=460, margin=dict(l=10, r=10, t=55, b=10))
        st.plotly_chart(fig, use_container_width=True)

    cols = ["Ticker", "Nome", "Nome ETF", "Tipo", "Score Finale", "Priority Score", "Azione Suggerita", "Stato", "Trend", "Entry Zone", "Risk Flag", "Rendimento 3M %", "Rendimento 12M %", "Volatilità %", "Max Drawdown %", "P/E", "Forward P/E", "Trigger Monitoraggio", "Note AI"]
    st.dataframe(style_priority_dataframe(df[[c for c in cols if c in df.columns]]), use_container_width=True, hide_index=True)
