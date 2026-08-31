from __future__ import annotations

import pandas as pd
import streamlit as st

from core.config import SECTOR_COMPASS_OUTPUT_CSV
from core.sector_compass_engine import analyze_sector_portfolio, fineco_portfolio_template

try:
    from core.ui_theme import apply_theme, hero, mini_cards, info_panel
except Exception:  # noqa: BLE001
    def apply_theme() -> None: return None
    def hero(title: str, subtitle: str, label: str = "") -> None:
        st.title(title); st.caption(label); st.write(subtitle)
    def mini_cards(cards):
        cols = st.columns(len(cards))
        for col, (label, value, hint) in zip(cols, cards):
            col.metric(label, value, help=hint)
    def info_panel(title: str, body: str) -> None: st.info(f"**{title}**\n\n{body}")

st.set_page_config(page_title="Portafoglio Fineco", page_icon="🏦", layout="wide")
apply_theme()
hero(
    "Portafoglio Fineco",
    "Carica le posizioni principali e classificale per settore. La app ti aiuta a capire se hai troppo core, troppo satellite o settori mancanti.",
    "AlphaForge v7",
)

if not SECTOR_COMPASS_OUTPUT_CSV.exists():
    st.error("AlphaForge_Sector_Compass.csv non trovato. Esegui aggiornamento completo.")
    st.stop()
sector = pd.read_csv(SECTOR_COMPASS_OUTPUT_CSV)

def read_file(uploaded):
    if uploaded is None:
        return pd.DataFrame()
    name = uploaded.name.lower()
    if name.endswith((".xlsx", ".xls")):
        return pd.read_excel(uploaded)
    return pd.read_csv(uploaded)

template = fineco_portfolio_template()
st.download_button("Scarica template CSV", template.to_csv(index=False).encode("utf-8"), "fineco_portfolio_template.csv", "text/csv")
info_panel("Come compilare", "Inserisci almeno Ticker/Nome, Valore EUR e Settore AlphaForge. Per i fondi Fineco che non hanno ticker, usa il nome e classificali manualmente nel settore piu' vicino.")

uploaded = st.file_uploader("Carica CSV/XLSX", type=["csv", "xlsx", "xls"])
use_demo = st.checkbox("Usa esempio demo", value=False)
try:
    portfolio = template if use_demo and uploaded is None else read_file(uploaded)
except Exception as exc:  # noqa: BLE001
    st.error(f"File non leggibile: {exc}")
    portfolio = pd.DataFrame()

if portfolio.empty:
    st.caption("Nessun file caricato. Scarica il template, compila e ricarica.")
    st.stop()

result = analyze_sector_portfolio(portfolio, sector)
s = result.summary
mini_cards([
    ("Valore totale", f"€ {s.get('Valore Totale EUR', 0):,.0f}".replace(",", "."), "Portafoglio caricato"),
    ("Peso core", f"{s.get('Peso core %', 0)}%", "Base globale"),
    ("Peso satellite", f"{s.get('Peso satellite %', 0)}%", "Temi/settori"),
    ("Peso maggiore", f"{s.get('Peso maggiore %', 0)}%", "Concentrazione"),
])
st.subheader("Cosa migliorare")
st.dataframe(result.suggestions, use_container_width=True, hide_index=True)
st.subheader("Esposizione per settore")
st.dataframe(result.sector_view, use_container_width=True, hide_index=True)
st.subheader("Posizioni")
st.dataframe(result.positions, use_container_width=True, hide_index=True)
