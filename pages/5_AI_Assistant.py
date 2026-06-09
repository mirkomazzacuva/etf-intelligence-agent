from __future__ import annotations

import streamlit as st

from core.compare_engine import analyze_instrument, compare_tickers, comparison_summary, extract_tickers

st.set_page_config(page_title="AI Assistant", page_icon="🤖", layout="wide")
st.title("🤖 AlphaForge AI Assistant")
st.caption("Assistente controllato: risponde usando dati scaricati e score calcolati, senza promettere acquisti/vendite sicuri.")

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Scrivimi una richiesta tipo: 'analizza NVDA' oppure 'confronta VWCE.DE, SWDA.MI e XDEV.MI'."}
    ]

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

prompt = st.chat_input("Chiedi una valutazione su ETF o azioni")
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)
    tickers = extract_tickers(prompt)
    with st.chat_message("assistant"):
        if not tickers:
            answer = "Non ho riconosciuto ticker. Scrivi per esempio: 'analizza NVDA' o 'confronta SWDA.MI, VWCE.DE, XDEV.MI'."
            st.write(answer)
        elif len(tickers) == 1:
            with st.spinner(f"Analizzo {tickers[0]}..."):
                r = analyze_instrument(tickers[0])
            answer = (
                f"**{r.get('Ticker')} — {r.get('Nome') or r.get('Nome ETF', '')}**\n\n"
                f"Score finale: **{r.get('Score Finale')}**. Stato: **{r.get('Stato')}**. Trend: **{r.get('Trend')}**.\n\n"
                f"Nota pratica: {r.get('Note AI', '')}\n\n"
                "Questa è una valutazione informativa basata su dati e score, non un ordine di acquisto o vendita."
            )
            st.markdown(answer)
            st.dataframe({k: [v] for k, v in r.items() if k in ["Ticker", "Tipo", "Score Finale", "Stato", "Trend", "Rendimento 3M %", "Rendimento 12M %", "Volatilità %", "Max Drawdown %", "P/E", "Forward P/E"]}, use_container_width=True)
        else:
            with st.spinner("Confronto strumenti..."):
                df = compare_tickers(tickers)
            lines = comparison_summary(df)
            answer = "\n".join(f"- {line}" for line in lines)
            st.markdown(answer)
            cols = ["Ticker", "Nome", "Nome ETF", "Tipo", "Score Finale", "Stato", "Trend", "Rendimento 3M %", "Rendimento 12M %", "Note AI"]
            st.dataframe(df[[c for c in cols if c in df.columns]], use_container_width=True, hide_index=True)
    st.session_state.messages.append({"role": "assistant", "content": answer})
