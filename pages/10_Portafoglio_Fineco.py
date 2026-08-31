from __future__ import annotations

import json
from io import BytesIO

import pandas as pd
import streamlit as st

from core.fineco_portfolio_tracker import (
    analyse_fineco_portfolio,
    default_baseline,
    ensure_template_files,
    load_fineco_portfolio,
    normalize_portfolio,
)

st.set_page_config(page_title="Portafoglio Fineco", page_icon="🏦", layout="wide")
st.title("🏦 Portafoglio Fineco")
st.caption("Tracking privato: carica CSV/XLSX in sessione, senza pubblicarlo su GitHub Pages.")

st.warning(
    "Privacy: se il repository è pubblico, non caricare file con importi personali nel repo. "
    "Usa l'uploader qui sotto per analizzarli solo nella sessione Streamlit, oppure rendi il repo privato."
)

ensure_template_files()

with st.expander("Formato file richiesto", expanded=False):
    st.write("Colonne consigliate:")
    st.code(
        "ISIN, Nome Strumento, Tipo, Ruolo, Settore AlphaForge, Tipo Versamento, Data Inizio, "
        "Importo Iniziale EUR, PAC Mensile EUR, Capitale Versato Manuale EUR, Valore Attuale EUR, "
        "Quote, Prezzo Medio, Costi Annui % Stimati, Benchmark/Confronto, Prima Rata PAC Conteggiata, Note"
    )

sample = default_baseline()
st.download_button(
    "Scarica template CSV",
    data=sample.to_csv(index=False).encode("utf-8"),
    file_name="fineco_portfolio_template_v8.csv",
    mime="text/csv",
)

uploaded = st.file_uploader("Carica CSV/XLSX portafoglio Fineco", type=["csv", "xlsx", "xls"])

if uploaded is not None:
    if uploaded.name.lower().endswith((".xlsx", ".xls")):
        raw = pd.read_excel(uploaded)
    else:
        raw = pd.read_csv(uploaded)
    portfolio = normalize_portfolio(raw)
    source_label = "file caricato"
else:
    portfolio = load_fineco_portfolio()
    source_label = "template/repo"

positions, summary, questions = analyse_fineco_portfolio(portfolio)

st.subheader("Sintesi")
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Fase", str(summary.get("fase", "n/d")))
c2.metric("Una tantum", f"{summary.get('capitale_una_tantum_eur', 0):,.0f} €".replace(",", "."))
c3.metric("PAC mensile", f"{summary.get('pac_mensile_eur', 0):,.0f} €".replace(",", "."))
c4.metric("Versato stimato", f"{summary.get('capitale_versato_stimato_eur', 0):,.0f} €".replace(",", "."))
c5.metric("Rendimento", f"{summary.get('rendimento_pct', 0):.2f}%")

st.info(summary.get("messaggio_principale", ""))

if source_label == "template/repo":
    st.caption("Stai visualizzando il template o il file presente nel repo. Per dati reali usa l'uploader qui sopra.")

st.subheader("Posizioni")
st.dataframe(positions, use_container_width=True, hide_index=True)

st.subheader("Domande da portare al consulente")
st.dataframe(questions, use_container_width=True, hide_index=True)

# Export report sessione
buffer = BytesIO()
with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
    positions.to_excel(writer, sheet_name="Posizioni", index=False)
    pd.DataFrame([summary]).to_excel(writer, sheet_name="Sintesi", index=False)
    questions.to_excel(writer, sheet_name="Domande", index=False)

st.download_button(
    "Scarica report Excel della sessione",
    data=buffer.getvalue(),
    file_name="fineco_portfolio_report.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)

with st.expander("JSON sintesi", expanded=False):
    st.json(summary)
