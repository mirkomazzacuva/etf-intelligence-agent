from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from core.config import (
    ACTION_PLAN_OUTPUT_CSV,
    FINECO_PORTFOLIO_OUTPUT_CSV,
    FINECO_PORTFOLIO_SUMMARY_FILE,
    FINECO_FUND_PERFORMANCE_CSV,
    FINECO_NEWS_RADAR_CSV,
    SECTOR_COMPASS_OUTPUT_CSV,
    STATUS_FILE,
)

st.set_page_config(page_title="AlphaForge v9", page_icon="⚒️", layout="wide")


def read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except Exception:  # noqa: BLE001
        return {}


def read_csv(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(path) if path.exists() else pd.DataFrame()
    except Exception:  # noqa: BLE001
        return pd.DataFrame()

status = read_json(STATUS_FILE)
summary = read_json(FINECO_PORTFOLIO_SUMMARY_FILE)
sectors = read_csv(SECTOR_COMPASS_OUTPUT_CSV)
actions = read_csv(ACTION_PLAN_OUTPUT_CSV)
fineco = read_csv(FINECO_PORTFOLIO_OUTPUT_CSV)
fund_perf = read_csv(FINECO_FUND_PERFORMANCE_CSV)
news = read_csv(FINECO_NEWS_RADAR_CSV)

st.title("⚒️ AlphaForge v9 - News & Performance Radar")
st.caption("Portafoglio Fineco, notizie finanziarie e grafici proxy per capire cosa monitorare.")

with st.sidebar:
    st.subheader("Aggiornamento")
    st.write(status.get("status", "unknown"))
    st.caption(status.get("message", ""))
    st.divider()
    st.info("Non pubblicare dati personali nel repository pubblico. Usa il caricamento file nelle pagine Portafoglio/Tracker.")

st.info(
    "Se fondi e PAC sono stati sottoscritti oggi, la performance non è ancora da giudicare. "
    "Ora l'obiettivo è creare il punto zero: importi, date, quote, prezzi medi, costi e benchmark."
)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Fase", summary.get("fase", "n/d"))
c2.metric("Una tantum", f"{summary.get('capitale_una_tantum_eur', 0):,.0f} €".replace(",", "."))
c3.metric("PAC mensile", f"{summary.get('pac_mensile_eur', 0):,.0f} €".replace(",", "."))
c4.metric("Fondi tracciati", len(fineco) if not fineco.empty else "n/d")

st.subheader("Cosa fare adesso")
steps = pd.DataFrame([
    {"Quando": "Oggi", "Azione": "Verifica esecuzione", "Cosa controllare": "Data valuta, quote, prezzo medio, eventuale prima rata PAC."},
    {"Quando": "1 mese", "Azione": "Controllo PAC", "Cosa controllare": "Che le rate siano partite e il valore sia allineato al capitale versato."},
    {"Quando": "3-6 mesi", "Azione": "Controllo struttura", "Cosa controllare": "Core vs satelliti, sovrapposizioni, costi e pesi."},
    {"Quando": "12 mesi", "Azione": "Prima valutazione rendimento", "Cosa controllare": "Performance vs benchmark e alternative ETF/fondi."},
])
st.dataframe(steps, use_container_width=True, hide_index=True)

left, right = st.columns(2)
with left:
    st.subheader("Bussola settoriale")
    cols = ["Priorita", "Settore", "Bucket", "Cosa fare", "Sector Score", "ETF/Fondo candidato"]
    st.dataframe(sectors[[c for c in cols if c in sectors.columns]].head(8), use_container_width=True, hide_index=True)
with right:
    st.subheader("Priorità operative")
    cols = ["Ticker", "Decisione chiara", "Cosa fare adesso", "Bucket operativo"]
    st.dataframe(actions[[c for c in cols if c in actions.columns]].head(8), use_container_width=True, hide_index=True)


st.subheader("News e andamento proxy")
col_news, col_perf = st.columns(2)
with col_news:
    st.write("Ultime notizie rilevate")
    if not news.empty:
        ncols = [c for c in ["Nome Strumento", "Titolo", "Lettura", "Impatto possibile"] if c in news.columns]
        st.dataframe(news[ncols].head(8), use_container_width=True, hide_index=True)
    else:
        st.info("Esegui Auto update o apri la pagina Notizie fondi Fineco.")
with col_perf:
    st.write("Riepilogo performance proxy")
    if not fund_perf.empty:
        pcols = [c for c in ["Nome Strumento", "Proxy Ticker", "Rendimento proxy 1M %", "Rendimento proxy 3M %", "Trend proxy", "Azione pratica"] if c in fund_perf.columns]
        st.dataframe(fund_perf[pcols].head(8), use_container_width=True, hide_index=True)
    else:
        st.info("Esegui Auto update o apri la pagina Grafici fondi Fineco.")

st.subheader("Tracker Fineco pubblico")
if not fineco.empty:
    public_cols = ["ISIN", "Nome Strumento", "Ruolo", "Tipo Versamento", "Capitale versato stimato EUR", "Rendimento %", "Stato lettura"]
    st.dataframe(fineco[[c for c in public_cols if c in fineco.columns]], use_container_width=True, hide_index=True)
else:
    st.write("Nessun output Fineco generato. Esegui aggiornamento completo.")

st.warning("Questa app non è consulenza finanziaria. Prima di agire verifica KID, costi, fiscalità, liquidità, adeguatezza e benchmark con il consulente.")
