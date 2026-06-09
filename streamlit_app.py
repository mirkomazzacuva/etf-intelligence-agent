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
    ACTION_PLAN_OUTPUT_CSV,
    ALLOCATION_FILE,
    INSIGHTS_OUTPUT_CSV,
    PORTFOLIO_TEMPLATE_FILE,
    RANKING_FILE,
    REPORT_FILE,
    STATUS_FILE,
    WATCHLIST_OUTPUT_CSV,
)
from core.portfolio_engine import analyze_portfolio, portfolio_template
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
def load_outputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    ranking = pd.read_excel(RANKING_FILE) if RANKING_FILE.exists() else pd.DataFrame()
    allocation = pd.read_excel(ALLOCATION_FILE, sheet_name="Suggested_Allocation") if ALLOCATION_FILE.exists() else pd.DataFrame()
    summary = pd.read_excel(ALLOCATION_FILE, sheet_name="Summary") if ALLOCATION_FILE.exists() else pd.DataFrame()
    watchlist = pd.read_csv(WATCHLIST_OUTPUT_CSV) if WATCHLIST_OUTPUT_CSV.exists() else pd.DataFrame()
    insights = pd.read_csv(INSIGHTS_OUTPUT_CSV) if INSIGHTS_OUTPUT_CSV.exists() else pd.DataFrame()
    action_plan = pd.read_csv(ACTION_PLAN_OUTPUT_CSV) if ACTION_PLAN_OUTPUT_CSV.exists() else pd.DataFrame()
    return ranking, allocation, summary, watchlist, insights, action_plan


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


def run_manual_update() -> tuple[bool, str]:
    if not UPDATE_SCRIPT.exists():
        return False, "Script auto_update_app.py non trovato."
    completed = subprocess.run([sys.executable, str(UPDATE_SCRIPT)], text=True, capture_output=True, check=False)
    output = (completed.stdout or "") + "\n" + (completed.stderr or "")
    return completed.returncode == 0, output[-5000:]


def read_uploaded_portfolio(uploaded_file) -> pd.DataFrame:
    if uploaded_file is None:
        return pd.DataFrame()
    name = uploaded_file.name.lower()
    if name.endswith(".xlsx") or name.endswith(".xls"):
        return pd.read_excel(uploaded_file)
    return pd.read_csv(uploaded_file)


status = load_status()
with st.sidebar:
    st.title("⚡ AlphaForge")
    st.caption("ETF, azioni, decisioni chiare e portafoglio")
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
    st.caption("La vista chiave ora è 'Cosa fare': decisioni chiare, non solo score.")

hero(
    "AlphaForge Intelligence",
    "Dashboard operativa per capire cosa guardare oggi, cosa attendere, cosa non aumentare e come migliorare un portafoglio già esistente.",
    "AlphaForge v5 Decision & Portfolio",
)

ranking, allocation, summary, watchlist, insights, action_plan = load_outputs()
if ranking.empty or allocation.empty:
    st.error("Mancano i file principali. Esegui Auto update ETF Intelligence App da GitHub Actions.")
    st.stop()

ranking = ranking.sort_values("Score Finale", ascending=False, na_position="last")
if not insights.empty and "Priority Score" in insights.columns:
    insights = insights.sort_values("Priority Score", ascending=False, na_position="last")
if not action_plan.empty and "Priority Score" in action_plan.columns:
    action_plan = action_plan.sort_values("Priority Score", ascending=False, na_position="last")

market_regime = get_summary_value(summary, "Market Regime") or "Neutral"
best = ranking.iloc[0]
last_update = file_last_update(RANKING_FILE)
watch_today = int(action_plan.get("Decisione chiara", pd.Series(dtype=str)).astype(str).str.contains("Valuta ingresso", case=False, na=False).sum()) if not action_plan.empty else 0
risk_control = int(action_plan.get("Decisione chiara", pd.Series(dtype=str)).astype(str).str.contains("Riduci|size piccola", case=False, regex=True, na=False).sum()) if not action_plan.empty else 0
pullback_wait = int(action_plan.get("Decisione chiara", pd.Series(dtype=str)).astype(str).str.contains("pullback", case=False, na=False).sum()) if not action_plan.empty else 0

mini_cards([
    ("Market Regime", market_regime, "Scenario sintetico"),
    ("Da guardare oggi", watch_today, "Possibili ingressi graduali"),
    ("Rischio da controllare", risk_control, "Non aumentare / size prudente"),
    ("Da attendere", pullback_wait, "Interessanti ma estesi"),
])

st.info(f"Ultimo aggiornamento dati: **{last_update}** · Profilo: **{risk_profile}** · Importo simulato: **{amount:,.0f} €**".replace(",", "."))

tab_action, tab_portfolio, tab_dash, tab_alloc, tab_rank, tab_watch, tab_report = st.tabs([
    "Cosa fare", "Portafoglio", "Quadro", "Allocazione", "Ranking ETF", "Watchlist", "Report"
])

with tab_action:
    st.subheader("Cosa fare adesso")
    info_panel(
        "Come leggere questa pagina",
        "Parti sempre da qui: <b>Decisione chiara</b> traduce score, rischio ed entry zone in un'azione pratica. Non è un ordine di acquisto/vendita: serve per decidere cosa monitorare prima e cosa evitare di inseguire.",
    )
    if action_plan.empty:
        st.warning("Action plan non ancora generato. Esegui aggiornamento completo.")
    else:
        c1, c2, c3 = st.columns(3)
        with c1:
            buckets = sorted([str(x) for x in action_plan.get("Bucket operativo", pd.Series()).dropna().unique()])
            selected_buckets = st.multiselect("Bucket", buckets, default=buckets)
        with c2:
            decisions = sorted([str(x) for x in action_plan.get("Decisione chiara", pd.Series()).dropna().unique()])
            selected_decisions = st.multiselect("Decisione", decisions, default=decisions)
        with c3:
            min_priority = st.slider("Priority minima", 0, 100, 45)
        view = action_plan.copy()
        if selected_buckets and "Bucket operativo" in view.columns:
            view = view[view["Bucket operativo"].isin(selected_buckets)]
        if selected_decisions and "Decisione chiara" in view.columns:
            view = view[view["Decisione chiara"].isin(selected_decisions)]
        if "Priority Score" in view.columns:
            view = view[pd.to_numeric(view["Priority Score"], errors="coerce").fillna(0) >= min_priority]
        cols = ["Bucket operativo", "Ticker", "Score Finale", "Priority Score", "Decisione chiara", "Cosa fare adesso", "Entry Zone", "Risk Flag", "Trigger Monitoraggio"]
        st.dataframe(style_priority_dataframe(view[[c for c in cols if c in view.columns]].head(50)), use_container_width=True, hide_index=True)

with tab_portfolio:
    st.subheader("Analizza il tuo portafoglio")
    info_panel(
        "A cosa serve",
        "Carica un CSV/XLSX con le tue posizioni. AlphaForge calcola pesi, concentrazione, P/L indicativo e collega ogni ticker a score, risk flag e decisione chiara. I dati restano nella sessione Streamlit: non vengono salvati nel repository.",
    )
    template_df = portfolio_template()
    csv_template = template_df.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Scarica template CSV", csv_template, "portfolio_template.csv", "text/csv")
    uploaded = st.file_uploader("Carica portafoglio CSV/XLSX", type=["csv", "xlsx", "xls"])
    use_demo = st.checkbox("Usa template demo per provare", value=False)
    try:
        portfolio_df = template_df if use_demo and uploaded is None else read_uploaded_portfolio(uploaded)
    except Exception as exc:  # noqa: BLE001
        st.error(f"File non leggibile: {exc}")
        portfolio_df = pd.DataFrame()
    if portfolio_df.empty:
        st.caption("Colonne accettate: Ticker, Quantità, Prezzo Medio, Valore EUR, Target %, Categoria Utente. Puoi anche usare varianti tipo qty, pmc, valore.")
    else:
        with st.spinner("Analisi portafoglio in corso..."):
            result = analyze_portfolio(portfolio_df, action_plan=action_plan, insights=insights)
        s = result.summary
        mini_cards([
            ("Valore totale", f"€ {s.get('Valore Totale EUR', 0):,.0f}".replace(",", "."), "Stima dal file o dai prezzi"),
            ("Posizioni", s.get("Numero Posizioni", 0), "Ticker caricati"),
            ("Peso maggiore", f"{s.get('Peso maggiore %', 0)}%", "Rischio concentrazione"),
            ("High risk", f"{s.get('Peso High Risk %', 0)}%", "Peso strumenti rischiosi"),
        ])
        st.markdown("#### Posizioni analizzate")
        pos_cols = ["Ticker", "Valore EUR", "Peso %", "P/L %", "Score Finale", "Priority Score", "Decisione chiara", "Risk Flag", "Suggerimento Portafoglio"]
        st.dataframe(style_priority_dataframe(result.positions[[c for c in pos_cols if c in result.positions.columns]]), use_container_width=True, hide_index=True)
        st.markdown("#### Come migliorarlo")
        st.dataframe(result.improvements, use_container_width=True, hide_index=True)
        if "Peso %" in result.positions.columns:
            fig_port = px.pie(result.positions, names="Ticker", values="Peso %", title="Peso posizioni")
            fig_port.update_layout(height=430, margin=dict(l=10, r=10, t=55, b=10))
            st.plotly_chart(fig_port, use_container_width=True)

with tab_dash:
    c1, c2 = st.columns([1.12, 0.88])
    with c1:
        st.subheader("Mappa score/rischio")
        required = {"Volatilità %", "Score Finale", "Categoria", "Rendimento 12M %", "Ticker"}
        if required.issubset(ranking.columns):
            fig = px.scatter(ranking, x="Volatilità %", y="Score Finale", color="Categoria", size="Rendimento 12M %", hover_name="Ticker", title="ETF: qualità, momentum e rischio")
            fig.update_layout(height=460, margin=dict(l=10, r=10, t=55, b=10), legend_title_text="Categoria")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Grafico non disponibile: colonne mancanti.")
    with c2:
        info_panel("Lettura operativa", "<b>Cosa fare</b> è la vista principale. <b>Portafoglio</b> ti dice se quello che possiedi è troppo concentrato, troppo rischioso o fuori watchlist.")
        if not action_plan.empty:
            top_cols = ["Ticker", "Priority Score", "Decisione chiara", "Entry Zone", "Risk Flag"]
            st.dataframe(action_plan[[c for c in top_cols if c in action_plan.columns]].head(5), use_container_width=True, hide_index=True)

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
    cols = ["Ticker", "Nome ETF", "Categoria", "Tema/Area", "Score Finale", "Stato", "ETF Quality Score", "ETF Momentum Score", "ETF Risk Score", "ETF Entry Score", "Priority Score", "Trend", "Entry Zone", "Risk Flag", "Rendimento 12M %", "Volatilità %", "Max Drawdown %", "Sharpe", "Note AI"]
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
