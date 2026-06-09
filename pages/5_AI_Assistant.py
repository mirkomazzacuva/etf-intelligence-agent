from __future__ import annotations

import pandas as pd
import streamlit as st

from core.compare_engine import analyze_instrument, compare_tickers, comparison_summary, extract_tickers
from core.insight_engine import assistant_answer_for_row
from core.ui_theme import apply_theme, hero, info_panel, style_priority_dataframe

st.set_page_config(page_title="AI Assistant", page_icon="🤖", layout="wide")
apply_theme()
hero("AlphaForge AI Assistant", "Assistente controllato: risponde usando dati, score, entry zone, risk flag e scenari. Non promette guadagni o acquisti sicuri.", "AlphaForge v4")

quick = st.radio("Prompt rapidi", ["Analizza NVDA", "Confronta NVDA, AMD, ASML.AS", "Analizza SWDA.MI", "Custom"], horizontal=True)

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Scrivimi una richiesta tipo: 'analizza NVDA' oppure 'confronta VWCE.DE, SWDA.MI e XDEV.MI'."}
    ]

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

placeholder = "Chiedi una valutazione su ETF o azioni"
default_prompt = "" if quick == "Custom" else quick
prompt = st.chat_input(placeholder)
if default_prompt and st.button("Esegui prompt rapido", type="primary", use_container_width=True):
    prompt = default_prompt

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
            answer = assistant_answer_for_row(r)
            st.markdown(answer)
            cols = ["Ticker", "Tipo", "Score Finale", "Priority Score", "Azione Suggerita", "Stato", "Trend", "Entry Zone", "Risk Flag", "Rendimento 3M %", "Rendimento 12M %", "Volatilità %", "Max Drawdown %", "P/E", "Forward P/E"]
            st.dataframe(pd.DataFrame([{k: v for k, v in r.items() if k in cols}]), use_container_width=True, hide_index=True)
        else:
            with st.spinner("Confronto strumenti..."):
                df = compare_tickers(tickers)
            lines = comparison_summary(df)
            answer = "\n".join(f"- {line}" for line in lines)
            info_panel("Sintesi", "<br>".join(f"• {line}" for line in lines))
            cols = ["Ticker", "Nome", "Nome ETF", "Tipo", "Score Finale", "Priority Score", "Azione Suggerita", "Stato", "Trend", "Entry Zone", "Risk Flag", "Rendimento 3M %", "Rendimento 12M %", "Trigger Monitoraggio"]
            st.dataframe(style_priority_dataframe(df[[c for c in cols if c in df.columns]]), use_container_width=True, hide_index=True)
    st.session_state.messages.append({"role": "assistant", "content": answer})
