from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

try:
    import plotly.express as px
except Exception:  # noqa: BLE001
    px = None  # type: ignore[assignment]

from core.config import (
    FINECO_DECISION_COCKPIT_CSV,
    FINECO_DECISION_SUMMARY_FILE,
    FINECO_FUND_PRICE_HISTORY_CSV,
    FINECO_ACTUAL_VALUES_FILE,
)

st.set_page_config(page_title="Decision Cockpit", page_icon="📌", layout="wide")
st.title("📌 Decision Cockpit Fineco")
st.caption("Margine netto, proiezioni e decisione pratica per ogni fondo/PAC.")


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


def euro(value: object) -> str:
    try:
        return f"{float(value):,.0f} €".replace(",", ".")
    except Exception:  # noqa: BLE001
        return "n/d"


def pct(value: object) -> str:
    try:
        return f"{float(value):+.2f}%".replace(".", ",")
    except Exception:  # noqa: BLE001
        return "n/d"


summary = read_json(FINECO_DECISION_SUMMARY_FILE)
decision = read_csv(FINECO_DECISION_COCKPIT_CSV)
history = read_csv(FINECO_FUND_PRICE_HISTORY_CSV)
actual = read_csv(FINECO_ACTUAL_VALUES_FILE)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Capitale versato", euro(summary.get("capitale_versato_eur", 0)))
c2.metric("Valore attuale", euro(summary.get("valore_attuale_eur", 0)))
c3.metric("Margine netto", euro(summary.get("margine_netto_eur", 0)), pct(summary.get("margine_netto_pct", 0)))
c4.metric("PAC mensile", euro(summary.get("pac_mensile_eur", 0)))

st.info(summary.get("decisione_sintesi", "Tieni e monitora"))

if decision.empty:
    st.warning("Decision Cockpit non ancora generato. Lancia Auto update completo.")
else:
    cols = [
        "Fondo/PAC", "Tipo", "Capitale versato EUR", "Valore attuale EUR", "Margine netto EUR", "Margine netto %",
        "Costo annuo %", "Proiezione 3M base EUR", "Range 3M prudente EUR", "Proiezione 1Y base EUR",
        "Range 1Y prudente EUR", "Decisione pratica", "Motivo", "Quando valutare switch", "Fonte valore",
    ]
    st.dataframe(decision[[c for c in cols if c in decision.columns]], use_container_width=True, hide_index=True)

    left, right = st.columns([1.1, .9])
    with left:
        st.subheader("Margine netto")
        if px is not None:
            fig = px.bar(decision, x="Fondo/PAC", y="Margine netto EUR", hover_data=["Decisione pratica", "Costo annuo %"])
            fig.update_layout(height=430, xaxis_title="", yaxis_title="EUR", margin=dict(l=20, r=20, t=20, b=80))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.bar_chart(decision.set_index("Fondo/PAC")["Margine netto EUR"])
    with right:
        st.subheader("Proiezioni 1 anno")
        if px is not None:
            fig = px.bar(decision, x="Fondo/PAC", y="Proiezione 1Y base EUR", hover_data=["Range 1Y prudente EUR", "Decisione pratica"])
            fig.update_layout(height=430, xaxis_title="", yaxis_title="EUR", margin=dict(l=20, r=20, t=20, b=80))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.bar_chart(decision.set_index("Fondo/PAC")["Proiezione 1Y base EUR"])

st.subheader("Grafico proxy base 100")
if history.empty:
    st.warning("Storico proxy non disponibile.")
else:
    names = sorted(history["Nome Strumento"].dropna().unique().tolist())
    selected = st.multiselect("Fondi da confrontare", names, default=names[:7])
    view = history[history["Nome Strumento"].isin(selected)].copy()
    if px is not None and not view.empty:
        fig = px.line(view, x="Date", y="Normalized 100", color="Nome Strumento")
        fig.update_layout(height=520, yaxis_title="Base 100", xaxis_title="Data")
        st.plotly_chart(fig, use_container_width=True)

st.subheader("Valori Fineco da aggiornare")
st.caption("Per un margine reale devi aggiornare questo file nel repo con il controvalore Fineco effettivo.")
if not actual.empty:
    st.dataframe(actual, use_container_width=True, hide_index=True)
