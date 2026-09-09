from __future__ import annotations

import pandas as pd
import streamlit as st

try:
    import plotly.express as px
except Exception:  # noqa: BLE001
    px = None  # type: ignore[assignment]

from core.live_value_engine import build_live_portfolio_snapshot

st.set_page_config(page_title="Decision Cockpit", page_icon="📌", layout="wide")
st.title("📌 Fineco Live Decision Cockpit")
st.caption("Controvalore stimato/live, margine netto dalla sottoscrizione, proiezioni e segnale pratico.")

@st.cache_data(ttl=180, show_spinner="Aggiorno valori live/proxy...")
def load_data() -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    return build_live_portfolio_snapshot(period="1y")

if st.button("🔄 Aggiorna ora"):
    st.cache_data.clear()
    st.rerun()

live, history, summary = load_data()


def euro(value: object) -> str:
    try:
        return f"{float(value):,.0f} €".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:  # noqa: BLE001
        return "n/d"


def pct(value: object) -> str:
    try:
        return f"{float(value):+.2f}%".replace(".", ",")
    except Exception:  # noqa: BLE001
        return "n/d"

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Versato ad oggi", euro(summary.get("capitale_versato_eur", 0)))
c2.metric("Controvalore", euro(summary.get("controvalore_attuale_eur", 0)))
c3.metric("Margine netto", euro(summary.get("margine_netto_eur", 0)), pct(summary.get("margine_netto_pct", 0)))
c4.metric("Proiezione 3M", euro(summary.get("proiezione_3m_base_eur", 0)))
c5.metric("Proiezione 1Y", euro(summary.get("proiezione_1y_base_eur", 0)))

st.info(summary.get("decisione_sintesi", "Tieni e monitora"))
st.caption(f"Aggiornato: {summary.get('generated_at_rome', 'n/d')} · Fonte prevalente: {summary.get('fonte_prevalente', 'proxy/Fineco')}")

if live.empty:
    st.warning("Nessun dato disponibile.")
    st.stop()

cols = [
    "Fondo/PAC", "Capitale versato EUR", "Controvalore attuale EUR", "Margine netto EUR", "Margine netto %",
    "Costo annuo %", "Costo maturato stimato EUR", "Proiezione 3M base EUR", "Guadagno stimato 3M EUR",
    "Proiezione 1Y base EUR", "Guadagno stimato 1Y EUR", "Fonte valore", "Decisione pratica", "Quando valutare switch",
]
st.dataframe(live[[c for c in cols if c in live.columns]], use_container_width=True, hide_index=True)

left, right = st.columns([0.55, 0.45])
with left:
    st.subheader("Margine netto")
    if px is not None:
        fig = px.bar(live, x="Fondo/PAC", y="Margine netto EUR", hover_data=["Fonte valore", "Decisione pratica"])
        fig.update_layout(height=430, xaxis_title="", yaxis_title="EUR", margin=dict(l=20, r=20, t=20, b=90))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.bar_chart(live.set_index("Fondo/PAC")["Margine netto EUR"])
with right:
    st.subheader("Proiezione guadagno")
    if px is not None and {"Guadagno stimato 3M EUR", "Guadagno stimato 1Y EUR"}.issubset(live.columns):
        long = live[["Fondo/PAC", "Guadagno stimato 3M EUR", "Guadagno stimato 1Y EUR"]].melt("Fondo/PAC", var_name="Scenario", value_name="Guadagno stimato EUR")
        fig = px.bar(long, x="Fondo/PAC", y="Guadagno stimato EUR", color="Scenario", barmode="group")
        fig.update_layout(height=430, xaxis_title="", yaxis_title="EUR", margin=dict(l=20, r=20, t=20, b=90))
        st.plotly_chart(fig, use_container_width=True)

st.subheader("Grafico proxy")
if history.empty:
    st.warning("Storico proxy non disponibile.")
else:
    names = sorted(history["Nome Strumento"].dropna().unique().tolist())
    selected = st.multiselect("Fondi", names, default=names[:7])
    view = history[history["Nome Strumento"].isin(selected)].copy() if selected else history.copy()
    if px is not None and not view.empty:
        fig = px.line(view, x="Date", y="Normalized 100", color="Nome Strumento", hover_data=["Proxy usato", "Close"])
        fig.update_layout(height=520, xaxis_title="", yaxis_title="Base 100", margin=dict(l=20, r=20, t=20, b=20))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.dataframe(view, use_container_width=True, hide_index=True)

st.warning("Decisioni e proiezioni sono solo strumenti di monitoraggio. Per un vero switch valuta costi, fiscalità e confronto col consulente.")
