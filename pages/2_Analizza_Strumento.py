from __future__ import annotations

import pandas as pd
import streamlit as st

from core.compare_engine import analyze_instrument

st.set_page_config(page_title="Analizza strumento", page_icon="🔎", layout="wide")
st.title("🔎 Analizza ETF o azione")
st.caption("Inserisci un ticker libero, per esempio: VWCE.DE, SWDA.MI, NVDA, STM.MI, ASML.AS")

ticker = st.text_input("Ticker", value="NVDA").strip().upper()
forced_type = st.selectbox("Tipo", ["Auto", "ETF", "Stock"], index=0)

if st.button("Analizza", type="primary") and ticker:
    with st.spinner(f"Analisi di {ticker} in corso..."):
        result = analyze_instrument(ticker, None if forced_type == "Auto" else forced_type)
    if result.get("Errore"):
        st.warning(result.get("Errore"))
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Ticker", result.get("Ticker", ticker))
    with col2:
        st.metric("Tipo", result.get("Tipo", ""))
    with col3:
        st.metric("Score", result.get("Score Finale", ""))
    with col4:
        st.metric("Stato", result.get("Stato", ""))
    st.subheader(result.get("Nome") or result.get("Nome ETF") or ticker)
    st.info(result.get("Note AI", "Nessuna nota disponibile."))
    df = pd.DataFrame([result])
    preferred = ["Current Price", "Trend", "Rendimento 1M %", "Rendimento 3M %", "Rendimento 6M %", "Rendimento 12M %", "Volatilità %", "Max Drawdown %", "Sharpe", "P/E", "Forward P/E", "Profit Margin %", "Revenue Growth %", "Debt/Equity"]
    st.dataframe(df[[c for c in preferred if c in df.columns]], use_container_width=True, hide_index=True)
    with st.expander("Mostra tutti i dati calcolati"):
        st.dataframe(df, use_container_width=True, hide_index=True)
