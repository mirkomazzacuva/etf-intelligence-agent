from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from core.config import ACTION_PLAN_OUTPUT_CSV, INSIGHTS_OUTPUT_CSV
from core.portfolio_engine import analyze_portfolio, portfolio_template
from core.ui_theme import apply_theme, hero, info_panel, mini_cards, style_priority_dataframe

st.set_page_config(page_title="Portafoglio AlphaForge", page_icon="📊", layout="wide")
apply_theme()
hero(
    "Portafoglio utente",
    "Carica le posizioni reali e guarda subito concentrazione, rischio, gap target e suggerimenti pratici per migliorarlo.",
    "AlphaForge v6 Portfolio",
)


def load_csv(path: str) -> pd.DataFrame:
    p = Path(path)
    return pd.read_csv(p) if p.exists() else pd.DataFrame()


def read_uploaded(uploaded_file) -> pd.DataFrame:
    if uploaded_file is None:
        return pd.DataFrame()
    name = uploaded_file.name.lower()
    if name.endswith((".xlsx", ".xls")):
        return pd.read_excel(uploaded_file)
    return pd.read_csv(uploaded_file)


def safe_cols(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    return df[[c for c in cols if c in df.columns]].copy() if not df.empty else df


action_plan = load_csv(str(ACTION_PLAN_OUTPUT_CSV))
insights = load_csv(str(INSIGHTS_OUTPUT_CSV))

template = portfolio_template()
st.download_button("⬇️ Scarica template CSV", template.to_csv(index=False).encode("utf-8"), "portfolio_template.csv", "text/csv")

uploaded = st.file_uploader("Carica CSV/XLSX portafoglio", type=["csv", "xlsx", "xls"])
use_demo = st.checkbox("Usa demo", value=False)

if not uploaded and not use_demo:
    info_panel(
        "Formato consigliato",
        "Usa colonne: <b>Ticker, Quantità, Prezzo Medio, Prezzo Attuale, Valore EUR, Target %, Categoria Utente</b>. Se non inserisci Prezzo Attuale, AlphaForge prova a scaricarlo automaticamente.",
    )
    st.dataframe(template, use_container_width=True, hide_index=True)
    st.stop()

try:
    portfolio = template if use_demo and uploaded is None else read_uploaded(uploaded)
except Exception as exc:  # noqa: BLE001
    st.error(f"File non leggibile: {exc}")
    st.stop()

with st.spinner("Analisi portafoglio..."):
    result = analyze_portfolio(portfolio, action_plan=action_plan, insights=insights)

s = result.summary
mini_cards([
    ("Health Score", s.get("Portfolio Health Score", 0), "Più alto = più ordinato"),
    ("Valore totale", f"€ {s.get('Valore Totale EUR', 0):,.0f}".replace(",", "."), "Indicativo"),
    ("Peso maggiore", f"{s.get('Peso maggiore %', 0)}%", "Concentrazione"),
    ("Da rivedere", s.get("Posizioni da rivedere", 0), "Priorità pratiche"),
])

st.subheader("Cosa migliorare prima")
st.dataframe(result.improvements, use_container_width=True, hide_index=True)

st.subheader("Posizioni con suggerimento")
cols = ["Ticker", "Categoria Stimata", "Valore EUR", "Peso %", "Target %", "Gap vs Target %", "P/L %", "Score Finale", "Priority Score", "Risk Flag", "Suggerimento Portafoglio"]
st.dataframe(style_priority_dataframe(safe_cols(result.positions, cols)), use_container_width=True, hide_index=True)

st.caption("Uso informativo: i risultati dipendono dai dati disponibili, dalla correttezza del file caricato e non costituiscono consulenza finanziaria personalizzata.")
