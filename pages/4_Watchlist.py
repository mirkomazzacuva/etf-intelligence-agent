from __future__ import annotations

import pandas as pd
import streamlit as st

from core.config import WATCHLIST_FILE, WATCHLIST_OUTPUT_CSV
from core.watchlist_engine import analyze_watchlist, ensure_watchlist_file, save_watchlist_outputs

st.set_page_config(page_title="Watchlist", page_icon="👀", layout="wide")
st.title("👀 Watchlist intelligente")
st.caption("La lista sorgente è data/watchlist.csv. Puoi modificarla dal repository aggiungendo ticker.")

ensure_watchlist_file(WATCHLIST_FILE)
source = pd.read_csv(WATCHLIST_FILE)
st.subheader("Ticker monitorati")
st.dataframe(source, use_container_width=True, hide_index=True)

if st.button("Aggiorna watchlist ora", type="primary"):
    with st.spinner("Analisi watchlist in corso..."):
        out = analyze_watchlist(WATCHLIST_FILE)
        save_watchlist_outputs(out)
    st.success("Watchlist aggiornata.")

if WATCHLIST_OUTPUT_CSV.exists():
    out = pd.read_csv(WATCHLIST_OUTPUT_CSV).sort_values("Score Finale", ascending=False, na_position="last")
    st.subheader("Risultati")
    cols = ["Ticker", "Nome", "Tipo", "Score Finale", "Stato", "Trend", "Rendimento 3M %", "Rendimento 12M %", "P/E", "Forward P/E", "Note AI"]
    st.dataframe(out[[c for c in cols if c in out.columns]], use_container_width=True, hide_index=True)
else:
    st.info("Output watchlist non ancora generato.")
