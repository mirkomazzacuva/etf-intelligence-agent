from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from core.action_guide_engine import build_action_brief, build_focus_board
from core.compare_engine import analyze_instrument, compare_tickers, extract_tickers
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

st.set_page_config(page_title="AlphaForge v6", page_icon="⚡", layout="wide")
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
    if name.endswith((".xlsx", ".xls")):
        return pd.read_excel(uploaded_file)
    return pd.read_csv(uploaded_file)


def safe_cols(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    return df[[c for c in cols if c in df.columns]].copy() if not df.empty else df


status = load_status()
with st.sidebar:
    st.title("⚡ AlphaForge")
    st.caption("Action-first dashboard")
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
    st.markdown("### Lettura rapida")
    st.caption("Prima guarda 'Cosa fare adesso'. Poi controlla portafoglio e solo dopo ranking/score.")
    amount = st.number_input("Importo simulato (€)", min_value=100, max_value=100000, value=1000, step=100)
    risk_profile = st.selectbox("Profilo rischio", ["Prudente", "Bilanciato", "Aggressivo"], index=1)


hero(
    "AlphaForge v6 Action First",
    "Una vista più pratica: prima dice cosa fare, cosa aspettare e cosa non aumentare. Poi ti aiuta a leggere il portafoglio già posseduto.",
    "AlphaForge v6 Decision & Portfolio",
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

brief = build_action_brief(action_plan, insights)
focus = brief.focus
market_regime = get_summary_value(summary, "Market Regime") or "Neutral"
last_update = file_last_update(RANKING_FILE)

cards = [("Market Regime", market_regime, "Scenario sintetico")] + brief.cards[:3]
mini_cards(cards)
st.info(f"Ultimo aggiornamento: **{last_update}** · Profilo: **{risk_profile}** · Importo simulato: **{amount:,.0f} €**".replace(",", "."))

if brief.narrative:
    st.markdown("### Cosa devi guardare per primo")
    for idx, line in enumerate(brief.narrative[:4], start=1):
        st.markdown(f"**{idx}.** {line}")

tabs = st.tabs(["Cosa fare adesso", "Portafoglio", "Analizza", "Confronta", "Allocazione", "Ranking ETF", "Watchlist", "Report"])

with tabs[0]:
    st.subheader("Cosa fare adesso")
    info_panel(
        "Metodo di lettura",
        "Qui lo score viene tradotto in istruzioni operative. <b>Non è un ordine di acquisto/vendita</b>: è una lista di priorità per capire cosa guardare, cosa attendere e dove non aumentare rischio.",
    )
    if focus.empty:
        st.warning("Action plan non disponibile. Esegui aggiornamento completo.")
    else:
        c1, c2, c3 = st.columns(3)
        with c1:
            buckets = sorted([str(x) for x in focus.get("AF Bucket", pd.Series()).dropna().unique()])
            selected_buckets = st.multiselect("Filtro operativo", buckets, default=buckets)
        with c2:
            min_priority = st.slider("Priority minima", 0, 100, 40)
        with c3:
            max_rows = st.slider("Numero righe", 5, 40, 16)
        view = focus.copy()
        if selected_buckets and "AF Bucket" in view.columns:
            view = view[view["AF Bucket"].isin(selected_buckets)]
        if "Priority Score" in view.columns:
            view = view[pd.to_numeric(view["Priority Score"], errors="coerce").fillna(0) >= min_priority]
        cols = ["Priorita", "Ticker", "AF Bucket", "Decisione", "Cosa fare in pratica", "Perche", "Priority Score", "Score Finale", "Entry Zone", "Risk Flag"]
        st.dataframe(style_priority_dataframe(safe_cols(view, cols).head(max_rows)), use_container_width=True, hide_index=True)
        st.caption("Regola pratica: se è in pullback-wait non inseguire; se è high-risk non aumentare size; se è azione controllata usa solo ingresso graduale.")

with tabs[1]:
    st.subheader("Portafoglio utente")
    info_panel(
        "Come funziona",
        "Carica un CSV/XLSX con le tue posizioni. AlphaForge calcola peso, P/L indicativo, gap rispetto al target e collega ogni ticker a score, entry zone e rischio. Il file resta nella sessione Streamlit e non viene salvato nel repository.",
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
        st.caption("Colonne accettate: Ticker, Quantità, Prezzo Medio, Prezzo Attuale, Valore EUR, Target %, Categoria Utente, Note. Puoi usare anche varianti come qty, pmc, valore.")
    else:
        with st.spinner("Analisi portafoglio in corso..."):
            result = analyze_portfolio(portfolio_df, action_plan=action_plan, insights=insights)
        s = result.summary
        mini_cards([
            ("Health Score", s.get("Portfolio Health Score", 0), "0 debole · 100 ordinato"),
            ("Valore totale", f"€ {s.get('Valore Totale EUR', 0):,.0f}".replace(",", "."), "Dai valori indicati/calcolati"),
            ("Peso maggiore", f"{s.get('Peso maggiore %', 0)}%", "Concentrazione"),
            ("Da rivedere", s.get("Posizioni da rivedere", 0), "Priorità portafoglio"),
        ])
        st.markdown("### Prima cosa da fare sul portafoglio")
        if not result.improvements.empty:
            st.dataframe(result.improvements, use_container_width=True, hide_index=True)
        cols = ["Ticker", "Categoria Stimata", "Valore EUR", "Peso %", "Target %", "Gap vs Target %", "P/L %", "Score Finale", "Priority Score", "Risk Flag", "Suggerimento Portafoglio"]
        st.markdown("### Posizioni")
        st.dataframe(style_priority_dataframe(safe_cols(result.positions, cols)), use_container_width=True, hide_index=True)

with tabs[2]:
    st.subheader("Analizza uno strumento")
    ticker = st.text_input("Ticker ETF o azione", value="NVDA")
    if st.button("Analizza", use_container_width=True):
        with st.spinner(f"Analisi {ticker}..."):
            try:
                data = analyze_instrument(ticker)
                df = pd.DataFrame([data])
                show = ["Ticker", "Nome", "Nome ETF", "Tipo", "Score Finale", "Stato", "Entry Zone", "Risk Flag", "Trend", "Note AI", "Errore"]
                st.dataframe(style_priority_dataframe(safe_cols(df, show)), use_container_width=True, hide_index=True)
                st.json({k: v for k, v in data.items() if k in ["Scenario Base", "Scenario Positivo", "Scenario Negativo", "Trigger Monitoraggio", "Azione Suggerita"]})
            except Exception as exc:  # noqa: BLE001
                st.error(f"Analisi non riuscita: {exc}")

with tabs[3]:
    st.subheader("Confronta strumenti")
    text = st.text_input("Ticker separati da virgola", value="SWDA.MI, VWCE.DE, NVDA, ASML.AS")
    if st.button("Confronta", use_container_width=True):
        tickers = extract_tickers(text)
        if not tickers:
            st.warning("Inserisci almeno un ticker.")
        else:
            with st.spinner("Confronto in corso..."):
                df = compare_tickers(tickers)
            cols = ["Ticker", "Tipo", "Score Finale", "Stato", "Entry Zone", "Risk Flag", "Trend", "Note AI"]
            st.dataframe(style_priority_dataframe(safe_cols(df, cols)), use_container_width=True, hide_index=True)

with tabs[4]:
    st.subheader("Allocazione suggerita")
    st.caption("Esempio informativo, non personalizzato.")
    cols = ["Ticker", "Nome ETF", "Categoria", "Peso Target %", "Importo su 1000 EUR", "Razionale"]
    st.dataframe(style_priority_dataframe(safe_cols(allocation, cols)), use_container_width=True, hide_index=True)

with tabs[5]:
    st.subheader("Ranking ETF")
    cols = ["Ticker", "Nome ETF", "Categoria", "Score Finale", "Stato", "Trend", "Entry Zone", "Risk Flag", "Note AI"]
    st.dataframe(style_priority_dataframe(safe_cols(ranking, cols)), use_container_width=True, hide_index=True)

with tabs[6]:
    st.subheader("Watchlist")
    if watchlist.empty:
        st.warning("Watchlist non disponibile.")
    else:
        cols = ["Ticker", "Tipo", "Score Finale", "Azione Suggerita", "Entry Zone", "Risk Flag", "Trigger Monitoraggio", "Note AI"]
        st.dataframe(style_priority_dataframe(safe_cols(watchlist, cols)), use_container_width=True, hide_index=True)

with tabs[7]:
    st.subheader("Report")
    if REPORT_FILE.exists():
        st.text(REPORT_FILE.read_text(encoding="utf-8"))
    else:
        st.warning("Report non disponibile.")
