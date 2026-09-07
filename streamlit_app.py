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
    ACTION_PLAN_OUTPUT_CSV,
    FINECO_ACTUAL_VALUES_FILE,
    FINECO_DECISION_COCKPIT_CSV,
    FINECO_DECISION_SUMMARY_FILE,
    FINECO_FUND_PERFORMANCE_CSV,
    FINECO_FUND_PRICE_HISTORY_CSV,
    FINECO_NEWS_RADAR_CSV,
    FINECO_NEWS_RADAR_SUMMARY,
    FINECO_PORTFOLIO_OUTPUT_CSV,
    SECTOR_COMPASS_OUTPUT_CSV,
    STATUS_FILE,
)

st.set_page_config(page_title="AlphaForge v10", page_icon="📈", layout="wide")

CSS = """
<style>
:root { --af-bg:#f3f5f8; --af-card:#ffffff; --af-border:#d9dee7; --af-text:#111827; --af-muted:#667085; --af-green:#068647; --af-red:#d92d20; --af-blue:#175cd3; --af-amber:#b54708; }
.stApp { background: var(--af-bg); }
.block-container { padding-top: 1.1rem; padding-bottom: 2.5rem; max-width: 1450px; }
.af-hero { background: #0b1220; padding: 22px 24px; border-radius: 18px; color: white; margin-bottom: 16px; box-shadow: 0 18px 38px rgba(15,23,42,.22); }
.af-hero h1 { font-size: 42px; line-height: 1; margin: 10px 0 8px; letter-spacing: -.05em; }
.af-hero p { color: #d0d5dd; font-size: 16px; margin: 0; }
.af-chip { display:inline-block; padding: 4px 10px; border-radius:999px; background:#e0f2fe; color:#075985; font-size:12px; font-weight:900; margin-right:6px; }
.af-chip.green { background:#dcfce7; color:#166534; }
div[data-testid="stMetric"] { background: var(--af-card); border:1px solid var(--af-border); padding:14px; border-radius:15px; box-shadow:0 8px 20px rgba(15,23,42,.05); }
[data-testid="stDataFrame"] { border-radius: 14px; overflow: hidden; }
.af-note { background:#eff6ff; border:1px solid #bfdbfe; border-radius:14px; padding:14px; font-weight:700; color:#1e3a8a; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


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


def euro(value: object, digits: int = 0) -> str:
    try:
        return f"{float(value):,.{digits}f} €".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:  # noqa: BLE001
        return "n/d"


def pct(value: object) -> str:
    try:
        return f"{float(value):+.2f}%".replace(".", ",")
    except Exception:  # noqa: BLE001
        return "n/d"


status = read_json(STATUS_FILE)
decision_summary = read_json(FINECO_DECISION_SUMMARY_FILE)
news_summary = read_json(FINECO_NEWS_RADAR_SUMMARY)
decision = read_csv(FINECO_DECISION_COCKPIT_CSV)
fineco = read_csv(FINECO_PORTFOLIO_OUTPUT_CSV)
fund_perf = read_csv(FINECO_FUND_PERFORMANCE_CSV)
fund_history = read_csv(FINECO_FUND_PRICE_HISTORY_CSV)
news = read_csv(FINECO_NEWS_RADAR_CSV)
actual_values = read_csv(FINECO_ACTUAL_VALUES_FILE)
sectors = read_csv(SECTOR_COMPASS_OUTPUT_CSV)
actions = read_csv(ACTION_PLAN_OUTPUT_CSV)

st.markdown(
    """
<div class="af-hero">
  <div><span class="af-chip green">AlphaForge v10</span><span class="af-chip">Decision Cockpit</span></div>
  <h1>Margine, proiezioni e decisione pratica</h1>
  <p>Vista semplice: quanto stai guadagnando/perdendo, dove potresti essere tra 3 mesi e 1 anno, e cosa monitorare prima di pensare a uno switch.</p>
</div>
""",
    unsafe_allow_html=True,
)

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Capitale versato", euro(decision_summary.get("capitale_versato_eur", 0)))
k2.metric("Valore attuale", euro(decision_summary.get("valore_attuale_eur", 0)))
k3.metric("Margine netto", euro(decision_summary.get("margine_netto_eur", 0)), pct(decision_summary.get("margine_netto_pct", 0)))
k4.metric("Proiezione 3 mesi", euro(decision_summary.get("proiezione_3m_base_eur", 0)))
k5.metric("Proiezione 1 anno", euro(decision_summary.get("proiezione_1y_base_eur", 0)))

st.markdown(f"<div class='af-note'>{decision_summary.get('decisione_sintesi', 'Tieni e monitora')}</div>", unsafe_allow_html=True)
st.caption("Per i fondi comuni il NAV ufficiale non è real-time. Se vuoi il margine esatto, aggiorna data/fineco_actual_values.csv con il controvalore Fineco reale.")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["📌 Decisione", "📈 Grafici", "📰 News", "✍️ Valori Fineco", "🧭 Dettagli"])

with tab1:
    st.subheader("Decisione per fondo")
    if decision.empty:
        st.warning("Decision cockpit non ancora disponibile. Lancia Auto update completo.")
    else:
        cols = [
            "Fondo/PAC", "Tipo", "Capitale versato EUR", "Valore attuale EUR", "Margine netto EUR", "Margine netto %",
            "Costo annuo %", "Proiezione 3M base EUR", "Proiezione 1Y base EUR", "Decisione pratica", "Quando valutare switch",
        ]
        st.dataframe(decision[[c for c in cols if c in decision.columns]], use_container_width=True, hide_index=True)

        st.subheader("Margine netto per fondo")
        if px is not None:
            fig = px.bar(decision, x="Fondo/PAC", y="Margine netto EUR", hover_data=["Decisione pratica", "Costo annuo %"])
            fig.update_layout(height=430, xaxis_title="", yaxis_title="Margine netto EUR", margin=dict(l=20, r=20, t=20, b=80))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.bar_chart(decision.set_index("Fondo/PAC")["Margine netto EUR"], use_container_width=True)

with tab2:
    st.subheader("Andamento fondi/proxy")
    if fund_history.empty:
        st.warning("Grafici non disponibili. Il prossimo Auto update dovrebbe scaricare lo storico proxy.")
    else:
        names = sorted(fund_history["Nome Strumento"].dropna().unique().tolist())
        selected = st.multiselect("Fondi da confrontare", names, default=names[:7])
        view = fund_history[fund_history["Nome Strumento"].isin(selected)].copy()
        if px is not None and not view.empty:
            fig = px.line(view, x="Date", y="Normalized 100", color="Nome Strumento", hover_data=["Proxy usato"] if "Proxy usato" in view.columns else None)
            fig.update_layout(height=560, yaxis_title="Base 100", xaxis_title="Data", legend_title="Fondo/proxy", margin=dict(l=20, r=20, t=20, b=20))
            st.plotly_chart(fig, use_container_width=True)
        elif not view.empty:
            chart = view.pivot_table(index="Date", columns="Nome Strumento", values="Normalized 100", aggfunc="last")
            st.line_chart(chart, use_container_width=True)

    st.subheader("Performance proxy")
    if not fund_perf.empty:
        cols = ["Nome Strumento", "Proxy usato", "Rendimento proxy 1D %", "Rendimento proxy 1M %", "Rendimento proxy 3M %", "Rendimento proxy 1Y %", "Trend proxy", "Azione pratica"]
        st.dataframe(fund_perf[[c for c in cols if c in fund_perf.columns]], use_container_width=True, hide_index=True)

with tab3:
    st.subheader("News radar")
    funds_summary = pd.DataFrame(news_summary.get("funds", [])) if isinstance(news_summary, dict) else pd.DataFrame()
    if not funds_summary.empty:
        st.dataframe(funds_summary, use_container_width=True, hide_index=True)
    if not news.empty:
        cols = ["Nome Strumento", "Categoria AlphaForge", "Titolo", "Fonte", "News Score", "Lettura", "Impatto possibile", "Link"]
        st.dataframe(news[[c for c in cols if c in news.columns]].head(40), use_container_width=True, hide_index=True)

with tab4:
    st.subheader("Valori Fineco manuali")
    st.write("Per vedere il margine reale, copia da Fineco il controvalore attuale e il capitale versato per ogni fondo in `data/fineco_actual_values.csv`.")
    if actual_values.empty:
        st.warning("Template data/fineco_actual_values.csv non trovato.")
    else:
        st.dataframe(actual_values, use_container_width=True, hide_index=True)

with tab5:
    st.subheader("Tracker Fineco originale")
    if not fineco.empty:
        st.dataframe(fineco, use_container_width=True, hide_index=True)
    if not sectors.empty:
        st.subheader("Bussola settoriale")
        st.dataframe(sectors.head(12), use_container_width=True, hide_index=True)
    if not actions.empty:
        st.subheader("Priorità operative ETF/stock")
        st.dataframe(actions.head(12), use_container_width=True, hide_index=True)

st.warning("Informazioni per monitoraggio personale. Non costituiscono consulenza finanziaria, sollecitazione all'investimento o garanzia di rendimento.")
