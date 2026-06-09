from __future__ import annotations

import pandas as pd
import streamlit as st

from core.config import WATCHLIST_FILE, WATCHLIST_OUTPUT_CSV
from core.ui_theme import apply_theme, hero, mini_cards, style_priority_dataframe
from core.watchlist_engine import analyze_watchlist, ensure_watchlist_file, save_watchlist_outputs

st.set_page_config(page_title="Watchlist", page_icon="👀", layout="wide")
apply_theme()
hero("Watchlist intelligente", "Monitoraggio azioni e strumenti con score, entry zone, risk flag e azione pratica.", "AlphaForge v4")

ensure_watchlist_file(WATCHLIST_FILE)
source = pd.read_csv(WATCHLIST_FILE)
mini_cards([
    ("Ticker sorgente", len(source), "data/watchlist.csv"),
    ("Output", "presente" if WATCHLIST_OUTPUT_CSV.exists() else "mancante", "AlphaForge_Watchlist.csv"),
    ("Modifica", "GitHub", "Aggiungi ticker nel CSV"),
    ("Uso", "monitoraggio", "Non segnali automatici"),
])

with st.expander("Ticker monitorati dalla sorgente"):
    st.dataframe(source, use_container_width=True, hide_index=True)

if st.button("Aggiorna watchlist ora", type="primary", use_container_width=True):
    with st.spinner("Analisi watchlist in corso..."):
        out = analyze_watchlist(WATCHLIST_FILE)
        save_watchlist_outputs(out)
    st.success("Watchlist aggiornata.")

if WATCHLIST_OUTPUT_CSV.exists():
    out = pd.read_csv(WATCHLIST_OUTPUT_CSV)
    sort_col = "Priority Score" if "Priority Score" in out.columns else "Score Finale"
    out = out.sort_values(sort_col, ascending=False, na_position="last")
    st.subheader("Risultati")
    cols = ["Ticker", "Nome", "Tipo", "Score Finale", "Priority Score", "Azione Suggerita", "Stato", "Trend", "Entry Zone", "Risk Flag", "Rendimento 3M %", "Rendimento 12M %", "P/E", "Forward P/E", "Trigger Monitoraggio", "Note AI"]
    st.dataframe(style_priority_dataframe(out[[c for c in cols if c in out.columns]]), use_container_width=True, hide_index=True)
else:
    st.info("Output watchlist non ancora generato.")
