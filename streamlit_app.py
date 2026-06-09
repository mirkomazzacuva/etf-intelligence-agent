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

from core.config import (
    ALLOCATION_FILE,
    INSIGHTS_OUTPUT_CSV,
    RANKING_FILE,
    REPORT_FILE,
    STATUS_FILE,
    WATCHLIST_OUTPUT_CSV,
)
from core.ui_theme import apply_theme, badge, hero, info_panel, mini_cards, style_priority_dataframe

UPDATE_SCRIPT = Path("auto_update_app.py")

st.set_page_config(page_title="AlphaForge Intelligence", page_icon="⚡", layout="wide")
apply_theme()


def file_last_update(path: Path) -> str:
    if not path.exists():
        return "File non trovato"
    timestamp = os.path.getmtime(path)
    return datetime.fromtimestamp(timestamp).strftime("%d/%m/%Y %H:%M")


def load_status() -> dict:
    if not STATUS_FILE.exists():
        return {"status": "unknown", "message": "Nessun aggiornamento registrato", "finished_at": None}
    try:
        return json.loads(STATUS_FILE.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "message": f"Status non leggibile: {exc}", "finished_at": None}


@st.cache_data(show_spinner=False)
def load_outputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    ranking = pd.read_excel(RANKING_FILE) if RANKING_FILE.exists() else pd.DataFrame()
    allocation = pd.read_excel(ALLOCATION_FILE, sheet_name="Suggested_Allocation") if ALLOCATION_FILE.exists() else pd.DataFrame()
    summary = pd.read_excel(ALLOCATION_FILE, sheet_name="Summary") if ALLOCATION_FILE.exists() else pd.DataFrame()
    watchlist = pd.read_csv(WATCHLIST_OUTPUT_CSV) if WATCHLIST_OUTPUT_CSV.exists() else pd.DataFrame()
    insights = pd.read_csv(INSIGHTS_OUTPUT_CSV) if INSIGHTS_OUTPUT_CSV.exists() else pd.DataFrame()
    return ranking, allocation, summary, watchlist, insights


def get_summary_value(summary_df: pd.DataFrame, key: str) -> str:
    if summary_df.empty or "Parametro" not in summary_df.columns:
        return ""
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


def status_badge(status: str) -> str:
    status = str(status).lower()
    if status == "success":
        return "✅ Aggiornato"
    if status == "running":
        return "⏳ In corso"
    if status == "failed":
        return "❌ Errore"
    return "⚪ Non disponibile"


def run_manual_update() -> tuple[bool, str]:
    if not UPDATE_SCRIPT.exists():
        return False, "Script auto_update_app.py non trovato."
    completed = subprocess.run([sys.executable, str(UPDATE_SCRIPT)], text=True, capture_output=True, check=False)
    output = (completed.stdout or "") + "\n" + (completed.stderr or "")
    return completed.returncode == 0, output[-5000:]


status = load_status()
with st.sidebar:
    st.title("⚡ AlphaForge")
    st.caption("ETF, azioni, priority score e watchlist")
    st.markdown(badge(status.get("status", "unknown")), unsafe_allow_html=True)
    st.caption(status.get("message", ""))
    if status.get("finished_at"):
        st.caption(f"Ultimo run: {status.get('finished_at')}")
    if st.button("🔄 Aggiorna ora", type="primary", use_container_width=True):
        with st.spinner("Aggiornamento dati in corso..."):
            ok, output = run_manual_update()
            load_outputs.clear()
            if ok:
                st.success("Aggiornamento completato.")
                st.rerun()
            else:
                st.error("Aggiornamento non completato.")
                with st.expander("Dettagli errore"):
                    st.code(output)
    st.divider()
    amount = st.number_input("Importo simulato (€)", min_value=100, max_value=100000, value=1000, step=100)
    risk_profile = st.selectbox("Profilo rischio", ["Prudente", "Bilanciato", "Aggressivo"], index=1)
    st.caption("Usa le pagine laterali per analisi libera, confronto, watchlist e assistente controllato.")

hero(
    "AlphaForge Intelligence",
    "Dashboard premium per leggere ETF, azioni, ranking, allocazione, watchlist, priority score, entry zone e scenari pratici senza complessità inutile.",
    "AlphaForge v4 Premium UI",
)

ranking, allocation, summary, watchlist, insights = load_outputs()
if ranking.empty or allocation.empty:
    st.error("Mancano i file principali. Esegui Auto update ETF Intelligence App da GitHub Actions.")
    st.stop()

ranking = ranking.sort_values("Score Finale", ascending=False, na_position="last")
if not insights.empty and "Priority Score" in insights.columns:
    insights = insights.sort_values("Priority Score", ascending=False, na_position="last")
market_regime = get_summary_value(summary, "Market Regime") or "Neutral"
best = ranking.iloc[0]
last_update = file_last_update(RANKING_FILE)
top_priority = insights.iloc[0].get("Ticker", "n/d") if not insights.empty else "n/d"
top_watch = watchlist.sort_values("Score Finale", ascending=False, na_position="last").iloc[0].get("Ticker", "n/d") if not watchlist.empty and "Score Finale" in watchlist.columns else "n/d"

mini_cards([
    ("Market Regime", market_regime, "Scenario sintetico"),
    ("Miglior ETF", best.get("Ticker", ""), f"Score {safe_number(best.get('Score Finale', ''), 1)}"),
    ("Priorità", top_priority, "Strumento da monitorare prima"),
    ("Top Watchlist", top_watch, "Miglior score azioni/strumenti"),
])

st.info(f"Ultimo aggiornamento dati: **{last_update}** · Profilo selezionato: **{risk_profile}** · Importo simulato: **{amount:,.0f} €**".replace(",", "."))

tab_dash, tab_prior, tab_alloc, tab_rank, tab_watch, tab_report = st.tabs(["Quadro", "Priorità", "Allocazione", "Ranking ETF", "Watchlist", "Report"])

with tab_dash:
    c1, c2 = st.columns([1.12, 0.88])
    with c1:
        st.subheader("Mappa score/rischio")
        required = {"Volatilità %", "Score Finale", "Categoria", "Rendimento 12M %", "Ticker"}
        if required.issubset(ranking.columns):
            fig = px.scatter(
                ranking,
                x="Volatilità %",
                y="Score Finale",
                color="Categoria",
                size="Rendimento 12M %",
                hover_name="Ticker",
                title="ETF: qualità, momentum e rischio",
            )
            fig.update_layout(height=460, margin=dict(l=10, r=10, t=55, b=10), legend_title_text="Categoria")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Grafico non disponibile: colonne mancanti.")
    with c2:
        info_panel(
            "Lettura operativa",
            "<b>Priority Score</b> ordina cosa guardare prima. <b>Entry Zone</b> evita di inseguire prezzi estesi. <b>Risk Flag</b> segnala quando usare size più prudente. Gli output sono informativi, non ordini automatici.",
        )
        st.markdown("<div class='af-divider'></div>", unsafe_allow_html=True)
        if not insights.empty:
            top_cols = ["Ticker", "Priority Score", "Azione Suggerita", "Entry Zone", "Risk Flag"]
            st.dataframe(insights[[c for c in top_cols if c in insights.columns]].head(5), use_container_width=True, hide_index=True)

with tab_prior:
    if insights.empty:
        st.warning("Insights non ancora generati. Esegui aggiornamento completo.")
    else:
        st.subheader("Priorità operative")
        a1, a2, a3 = st.columns(3)
        with a1:
            min_priority = st.slider("Priority minima", 0, 100, 50)
        with a2:
            action_options = sorted([str(x) for x in insights.get("Azione Suggerita", pd.Series()).dropna().unique()])
            selected_actions = st.multiselect("Azione", action_options, default=action_options)
        with a3:
            type_options = sorted([str(x) for x in insights.get("Tipo", pd.Series()).dropna().unique()])
            selected_types = st.multiselect("Tipo", type_options, default=type_options)
        filtered_insights = insights.copy()
        if "Priority Score" in filtered_insights.columns:
            filtered_insights = filtered_insights[pd.to_numeric(filtered_insights["Priority Score"], errors="coerce").fillna(0) >= min_priority]
        if selected_actions and "Azione Suggerita" in filtered_insights.columns:
            filtered_insights = filtered_insights[filtered_insights["Azione Suggerita"].isin(selected_actions)]
        if selected_types and "Tipo" in filtered_insights.columns:
            filtered_insights = filtered_insights[filtered_insights["Tipo"].isin(selected_types)]
        cols = ["Ticker", "Tipo", "Score Finale", "Priority Score", "Azione Suggerita", "Stato", "Trend", "Entry Zone", "Risk Flag", "Trigger Monitoraggio"]
        st.dataframe(style_priority_dataframe(filtered_insights[[c for c in cols if c in filtered_insights.columns]].head(30)), use_container_width=True, hide_index=True)

with tab_alloc:
    alloc = allocation.copy()
    if not alloc.empty and "Peso Target %" in alloc.columns:
        if risk_profile == "Prudente":
            defensive_boost, thematic_cut, factor_boost = 1.30, 0.65, 1.0
        elif risk_profile == "Aggressivo":
            defensive_boost, thematic_cut, factor_boost = 0.65, 1.45, 1.10
        else:
            defensive_boost, thematic_cut, factor_boost = 1.0, 1.0, 1.0

        def adjust_weight(row: pd.Series) -> float:
            category = str(row.get("Categoria", "")).lower()
            weight = float(row.get("Peso Target %", 0))
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
    st.dataframe(alloc, use_container_width=True, hide_index=True)
    if "Peso App %" in alloc.columns:
        fig_alloc = px.pie(alloc, names="Ticker", values="Peso App %", title="Distribuzione allocazione simulata")
        fig_alloc.update_layout(height=430, margin=dict(l=10, r=10, t=55, b=10))
        st.plotly_chart(fig_alloc, use_container_width=True)

with tab_rank:
    categories = sorted(ranking["Categoria"].dropna().unique()) if "Categoria" in ranking.columns else []
    selected = st.multiselect("Categorie", options=categories, default=categories)
    filtered = ranking[ranking["Categoria"].isin(selected)] if selected and "Categoria" in ranking.columns else ranking
    cols = [
        "Ticker", "Nome ETF", "Categoria", "Tema/Area", "Score Finale", "Stato", "ETF Quality Score",
        "ETF Momentum Score", "ETF Risk Score", "ETF Entry Score", "Priority Score", "Trend", "Entry Zone", "Risk Flag", "Rendimento 12M %",
        "Volatilità %", "Max Drawdown %", "Sharpe", "Note AI",
    ]
    st.dataframe(style_priority_dataframe(filtered[[c for c in cols if c in filtered.columns]]), use_container_width=True, hide_index=True)

with tab_watch:
    if watchlist.empty:
        st.warning("Watchlist non ancora generata. Esegui l'aggiornamento completo.")
    else:
        watchlist_view = watchlist.sort_values("Priority Score" if "Priority Score" in watchlist.columns else "Score Finale", ascending=False, na_position="last")
        cols = ["Ticker", "Nome", "Tipo", "Score Finale", "Priority Score", "Azione Suggerita", "Stato", "Trend", "Entry Zone", "Risk Flag", "Rendimento 3M %", "P/E", "Forward P/E", "Note AI"]
        st.dataframe(style_priority_dataframe(watchlist_view[[c for c in cols if c in watchlist_view.columns]]), use_container_width=True, hide_index=True)

with tab_report:
    if REPORT_FILE.exists():
        st.text(REPORT_FILE.read_text(encoding="utf-8"))
    else:
        st.info("Report testuale non disponibile.")

st.divider()
st.caption("Disclaimer: AlphaForge è uno strumento informativo e non sostituisce consulenza finanziaria personalizzata.")
