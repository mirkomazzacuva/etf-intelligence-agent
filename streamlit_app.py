from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

RANKING_FILE = Path("ETF_Intelligence_Agent_UPDATED.xlsx")
ALLOCATION_FILE = Path("ETF_Allocation_Model.xlsx")
REPORT_FILE = Path("ETF_Daily_Report.txt")
STATUS_FILE = Path("AUTO_UPDATE_STATUS.json")
UPDATE_SCRIPT = Path("auto_update_app.py")

st.set_page_config(page_title="ETF Intelligence App", page_icon="📊", layout="wide")


def file_last_update(path: Path) -> str:
    if not path.exists():
        return "File non trovato"
    timestamp = os.path.getmtime(path)
    return datetime.fromtimestamp(timestamp).strftime("%d/%m/%Y %H:%M")


def load_status() -> dict:
    if not STATUS_FILE.exists():
        return {
            "status": "unknown",
            "message": "Nessun aggiornamento automatico registrato",
            "finished_at": None,
        }
    try:
        return json.loads(STATUS_FILE.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "message": f"Status non leggibile: {exc}", "finished_at": None}


@st.cache_data(show_spinner=False)
def load_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    ranking = pd.read_excel(RANKING_FILE)
    allocation = pd.read_excel(ALLOCATION_FILE, sheet_name="Suggested_Allocation")
    summary = pd.read_excel(ALLOCATION_FILE, sheet_name="Summary")
    return ranking, allocation, summary


def get_summary_value(summary_df: pd.DataFrame, key: str) -> str:
    row = summary_df[summary_df["Parametro"] == key]
    if len(row) == 0:
        return ""
    return str(row.iloc[0]["Valore"])


def safe_number(value: object, decimals: int = 2) -> object:
    if pd.isna(value):
        return ""
    try:
        return round(float(value), decimals)
    except Exception:  # noqa: BLE001
        return value


def run_manual_update() -> tuple[bool, str]:
    if not UPDATE_SCRIPT.exists():
        return False, "Script auto_update_app.py non trovato."
    completed = subprocess.run(
        [sys.executable, str(UPDATE_SCRIPT)],
        text=True,
        capture_output=True,
        check=False,
    )
    output = (completed.stdout or "") + "\n" + (completed.stderr or "")
    return completed.returncode == 0, output[-5000:]


def status_badge(status: str) -> str:
    status = str(status).lower()
    if status == "success":
        return "✅ Aggiornato"
    if status == "running":
        return "⏳ In corso"
    if status == "failed":
        return "❌ Errore"
    return "⚪ Non disponibile"


st.title("📊 ETF Intelligence App")
st.caption("Ranking ETF, allocazione Fineco e analisi rischio. Report informativo, non consulenza finanziaria personalizzata.")

status = load_status()

with st.sidebar:
    st.header("Aggiornamenti")
    st.write(status_badge(status.get("status", "unknown")))
    st.caption(status.get("message", ""))
    if status.get("finished_at"):
        st.caption(f"Ultimo run: {status.get('finished_at')}")

    if st.button("🔄 Aggiorna ora", type="primary", use_container_width=True):
        with st.spinner("Aggiornamento dati in corso..."):
            ok, output = run_manual_update()
        load_data.clear()
        if ok:
            st.success("Aggiornamento completato.")
            st.rerun()
        else:
            st.error("Aggiornamento non completato.")
            with st.expander("Mostra dettagli errore"):
                st.code(output)

    st.divider()
    amount = st.number_input("Importo da investire (€)", min_value=100, max_value=100000, value=1000, step=100)
    risk_profile = st.selectbox("Profilo rischio", ["Prudente", "Bilanciato", "Aggressivo"], index=1)

required_files = [RANKING_FILE, ALLOCATION_FILE]
missing_files = [str(path) for path in required_files if not path.exists()]
if missing_files:
    st.error("Mancano file necessari per avviare la dashboard.")
    st.write("File mancanti:", ", ".join(missing_files))
    st.info("Esegui prima l'aggiornamento automatico da GitHub Actions o premi 'Aggiorna ora' se stai usando l'app in locale.")
    st.stop()

ranking, allocation, summary = load_data()
ranking = ranking.sort_values("Score Finale", ascending=False, na_position="last")

category_options = sorted(ranking["Categoria"].dropna().unique()) if "Categoria" in ranking.columns else []
with st.sidebar:
    category_filter = st.multiselect("Categorie da mostrare", options=category_options, default=category_options)
    st.divider()
    if st.toggle("Mostra log aggiornamento", value=False):
        st.json(status)

filtered = ranking[ranking["Categoria"].isin(category_filter)] if category_filter and "Categoria" in ranking.columns else ranking
market_regime = get_summary_value(summary, "Market Regime")
best = ranking.iloc[0]
last_update = file_last_update(RANKING_FILE)

st.info(f"Ultimo aggiornamento dati: **{last_update}**")

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Market Regime", market_regime)
with col2:
    st.metric("Miglior ETF", best.get("Ticker", ""))
with col3:
    st.metric("Score migliore", safe_number(best.get("Score Finale", ""), 1))
with col4:
    st.metric("Profilo rischio", risk_profile)

st.divider()
st.subheader("Allocazione suggerita per Fineco")

alloc = allocation.copy()
if not alloc.empty and "Categoria" in alloc.columns and "Peso Target %" in alloc.columns:
    if risk_profile == "Prudente":
        defensive_boost = 1.30
        thematic_cut = 0.60
        factor_boost = 1.05
    elif risk_profile == "Aggressivo":
        defensive_boost = 0.60
        thematic_cut = 1.45
        factor_boost = 1.10
    else:
        defensive_boost = 1.00
        thematic_cut = 1.00
        factor_boost = 1.00

    def adjust_weight(row: pd.Series) -> float:
        category = str(row["Categoria"]).lower()
        weight = float(row["Peso Target %"])
        if category == "defensive":
            return weight * defensive_boost
        if category == "thematic":
            return weight * thematic_cut
        if category == "factor":
            return weight * factor_boost
        return weight

    alloc["Peso App %"] = alloc.apply(adjust_weight, axis=1)
    alloc["Peso App %"] = alloc["Peso App %"] / alloc["Peso App %"].sum() * 100
    alloc["Peso App %"] = alloc["Peso App %"].round(2)
    alloc["Importo €"] = (amount * alloc["Peso App %"] / 100).round(2)

st.write(f"Profilo selezionato: **{risk_profile}** — importo simulato: **{amount:,.0f} €**".replace(",", "."))

alloc_columns = [
    "Ticker",
    "Nome ETF",
    "Categoria",
    "Tema/Area",
    "Peso App %",
    "Importo €",
    "Score Finale",
    "Note AI",
]
alloc_columns = [col for col in alloc_columns if col in alloc.columns]
st.dataframe(alloc[alloc_columns], use_container_width=True, hide_index=True)

if not alloc.empty and "Peso App %" in alloc.columns:
    fig_alloc = px.pie(alloc, names="Ticker", values="Peso App %", title="Distribuzione allocazione suggerita")
    st.plotly_chart(fig_alloc, use_container_width=True)

st.divider()
st.subheader("Ranking ETF")
ranking_columns = [
    "Ticker",
    "Nome ETF",
    "Categoria",
    "Tema/Area",
    "Score Finale",
    "Stato",
    "Rendimento 12M %",
    "Volatilità %",
    "Max Drawdown %",
    "Sharpe",
    "Note AI",
]
ranking_columns = [col for col in ranking_columns if col in filtered.columns]
st.dataframe(filtered[ranking_columns], use_container_width=True, hide_index=True)

st.divider()
st.subheader("Score vs Volatilità")
if {"Volatilità %", "Score Finale", "Categoria", "Rendimento 12M %", "Ticker"}.issubset(filtered.columns):
    fig = px.scatter(
        filtered,
        x="Volatilità %",
        y="Score Finale",
        color="Categoria",
        size="Rendimento 12M %",
        hover_name="Ticker",
        hover_data=[col for col in ["Nome ETF", "Tema/Area", "Max Drawdown %", "Rendimento 12M %", "Sharpe"] if col in filtered.columns],
        title="Score finale rispetto alla volatilità",
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("Grafico non disponibile: mancano alcune colonne nel file ranking.")

st.divider()
st.subheader("Lettura prudente")
st.markdown(
    """
- Gli ETF con score alto **non sono acquisti automatici**.
- Gli ETF core globali sono più adatti come base di lungo periodo.
- Gli ETF tematici vanno usati come satellite, non come parte principale.
- Oro e strumenti difensivi aiutano a bilanciare rischio macro/geopolitico.
- Prima di investire su Fineco, verifica costi, disponibilità, spread, valuta e coerenza con il tuo profilo di rischio.
"""
)

if REPORT_FILE.exists():
    with st.expander("Leggi report testuale completo"):
        st.text(REPORT_FILE.read_text(encoding="utf-8"))

st.divider()
st.caption("Disclaimer: questa applicazione è solo informativa e non costituisce consulenza finanziaria personalizzata.")
