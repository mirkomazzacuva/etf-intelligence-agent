from __future__ import annotations

import pandas as pd
import streamlit as st

from core.fineco_portfolio_tracker import analyse_fineco_portfolio, normalize_portfolio

st.set_page_config(page_title="Tracker rendimento Fineco", page_icon="📈", layout="wide")
st.title("📈 Tracker rendimento Fineco")
st.caption("Per confrontare capitale versato, valore attuale, rendimento e benchmark nel tempo.")

st.markdown(
    """
Questa pagina serve quando Fineco mostra già **controvalore attuale**, **quote** e **prezzo medio**.
All'inizio, se i fondi sono stati sottoscritti oggi, il rendimento non è ancora significativo.
"""
)

uploaded = st.file_uploader("Carica il file aggiornato Fineco CSV/XLSX", type=["csv", "xlsx", "xls"], key="tracker_upload")

if uploaded is None:
    st.info("Carica un file per calcolare rendimento. Puoi usare il template dalla pagina Portafoglio Fineco.")
    st.stop()

if uploaded.name.lower().endswith((".xlsx", ".xls")):
    raw = pd.read_excel(uploaded)
else:
    raw = pd.read_csv(uploaded)

portfolio = normalize_portfolio(raw)
positions, summary, questions = analyse_fineco_portfolio(portfolio)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Capitale versato", f"{summary.get('capitale_versato_stimato_eur', 0):,.0f} €".replace(",", "."))
c2.metric("Valore attuale", f"{summary.get('valore_attuale_stimato_eur', 0):,.0f} €".replace(",", "."))
c3.metric("Guadagno/Perdita", f"{summary.get('guadagno_perdita_eur', 0):,.0f} €".replace(",", "."))
c4.metric("Rendimento", f"{summary.get('rendimento_pct', 0):.2f}%")

st.subheader("Rendimento per strumento")
cols = [
    "ISIN", "Nome Strumento", "Ruolo", "Capitale versato stimato EUR", "Valore attuale stimato EUR",
    "Guadagno/Perdita EUR", "Rendimento %", "Rendimento annualizzato %", "Peso attuale %", "Stato lettura", "Benchmark/Confronto"
]
st.dataframe(positions[[c for c in cols if c in positions.columns]], use_container_width=True, hide_index=True)

st.subheader("Come leggerlo")
st.write(
    "- Nei primi 30 giorni: controlla solo corretta esecuzione, non performance.\n"
    "- Dopo 3-6 mesi: verifica pesi, sovrapposizioni e costi.\n"
    "- Dopo 12 mesi: confronta ogni fondo con il benchmark corretto."
)
