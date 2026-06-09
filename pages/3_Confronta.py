from __future__ import annotations

import pandas as pd
import streamlit as st

from core.compare_engine import compare_tickers, comparison_summary, extract_tickers

st.set_page_config(page_title="Confronta", page_icon="⚖️", layout="wide")
st.title("⚖️ Confronta ETF e azioni")
st.caption("Scrivi tickers separati da virgola. Esempi: VWCE.DE, SWDA.MI, XDEV.MI oppure NVDA, AMD, ASML.AS")

text = st.text_input("Ticker da confrontare", value="NVDA, AMD, ASML.AS")
tickers = extract_tickers(text)
st.caption(f"Riconosciuti: {', '.join(tickers) if tickers else 'nessuno'}")

if st.button("Confronta", type="primary") and tickers:
    with st.spinner("Confronto in corso..."):
        df = compare_tickers(tickers)
    for line in comparison_summary(df):
        st.write(f"- {line}")
    cols = ["Ticker", "Nome", "Nome ETF", "Tipo", "Score Finale", "Stato", "Trend", "Rendimento 3M %", "Rendimento 12M %", "Volatilità %", "Max Drawdown %", "P/E", "Forward P/E", "Note AI"]
    st.dataframe(df[[c for c in cols if c in df.columns]], use_container_width=True, hide_index=True)
