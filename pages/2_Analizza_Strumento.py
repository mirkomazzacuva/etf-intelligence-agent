from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core.compare_engine import analyze_instrument
from core.data_provider import fetch_price_history
from core.insight_engine import assistant_answer_for_row

st.set_page_config(page_title="Analizza strumento", page_icon="🔎", layout="wide")
st.title("🔎 Analizza ETF o azione")
st.caption("Inserisci un ticker libero, per esempio: VWCE.DE, SWDA.MI, NVDA, STM.MI, ASML.AS")

col_in, col_type, col_period = st.columns([2, 1, 1])
with col_in:
    ticker = st.text_input("Ticker", value="NVDA").strip().upper()
with col_type:
    forced_type = st.selectbox("Tipo", ["Auto", "ETF", "Stock"], index=0)
with col_period:
    chart_period = st.selectbox("Grafico", ["1y", "2y", "3y", "5y"], index=2)

if st.button("Analizza", type="primary") and ticker:
    with st.spinner(f"Analisi di {ticker} in corso..."):
        result = analyze_instrument(ticker, None if forced_type == "Auto" else forced_type)
        prices, price_error = fetch_price_history(ticker, period=chart_period)
    if result.get("Errore"):
        st.warning(result.get("Errore"))
    if price_error:
        st.caption(price_error)

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Ticker", result.get("Ticker", ticker))
    col2.metric("Tipo", result.get("Tipo", ""))
    col3.metric("Score", result.get("Score Finale", ""))
    col4.metric("Priority", result.get("Priority Score", ""))
    col5.metric("Stato", result.get("Stato", ""))

    st.subheader(result.get("Nome") or result.get("Nome ETF") or ticker)
    st.info(result.get("Note AI", "Nessuna nota disponibile."))

    s1, s2, s3 = st.columns(3)
    s1.metric("Entry Zone", result.get("Entry Zone", "n/d"))
    s2.metric("Risk Flag", result.get("Risk Flag", "n/d"))
    s3.metric("Azione", result.get("Azione Suggerita", "n/d"))
    st.write("**Trigger monitoraggio:**", result.get("Trigger Monitoraggio", "n/d"))

    if not prices.empty and "Close" in prices.columns:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=prices.index, y=prices["Close"], mode="lines", name="Close"))
        if "MA50" in result and pd.notna(result.get("MA50")):
            fig.add_hline(y=float(result["MA50"]), line_dash="dash", annotation_text="MA50")
        if "MA200" in result and pd.notna(result.get("MA200")):
            fig.add_hline(y=float(result["MA200"]), line_dash="dot", annotation_text="MA200")
        for level, label in [(result.get("Supporto 60D"), "Supporto 60D"), (result.get("Resistenza 60D"), "Resistenza 60D")]:
            try:
                if pd.notna(level):
                    fig.add_hline(y=float(level), line_dash="dash", annotation_text=label)
            except Exception:  # noqa: BLE001
                pass
        fig.update_layout(title=f"Prezzo {ticker}", height=430, margin=dict(l=10, r=10, t=45, b=10))
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("### Scenari pratici")
    st.markdown(assistant_answer_for_row(result))

    df = pd.DataFrame([result])
    preferred = [
        "Current Price", "Trend", "Entry Zone", "Risk Flag", "Distanza MA50 %", "Distanza MA200 %",
        "Supporto 60D", "Resistenza 60D", "Rendimento 1M %", "Rendimento 3M %", "Rendimento 6M %",
        "Rendimento 12M %", "Volatilità %", "Max Drawdown %", "Sharpe", "P/E", "Forward P/E",
        "Profit Margin %", "Revenue Growth %", "Debt/Equity", "Trigger Monitoraggio",
    ]
    st.dataframe(df[[c for c in preferred if c in df.columns]], use_container_width=True, hide_index=True)
    with st.expander("Mostra tutti i dati calcolati"):
        st.dataframe(df, use_container_width=True, hide_index=True)
