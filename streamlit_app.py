from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from core.config import (
    ACTION_PLAN_OUTPUT_CSV,
    ALLOCATION_FILE,
    FINECO_PORTFOLIO_TEMPLATE_FILE,
    INSIGHTS_OUTPUT_CSV,
    RANKING_FILE,
    REPORT_FILE,
    SECTOR_COMPASS_OUTPUT_CSV,
    STATUS_FILE,
    WATCHLIST_OUTPUT_CSV,
)
from core.sector_compass_engine import analyze_sector_portfolio, fineco_portfolio_template

try:
    from core.ui_theme import apply_theme, hero, mini_cards, info_panel, style_priority_dataframe
except Exception:  # noqa: BLE001
    def apply_theme() -> None: return None
    def hero(title: str, subtitle: str, label: str = "") -> None:
        st.title(title); st.caption(label); st.write(subtitle)
    def mini_cards(cards):
        cols = st.columns(len(cards))
        for col, (label, value, hint) in zip(cols, cards):
            col.metric(label, value, help=hint)
    def info_panel(title: str, body: str) -> None:
        st.info(f"**{title}**\n\n{body}")
    def style_priority_dataframe(df): return df

st.set_page_config(page_title="AlphaForge v7 Sector Compass", page_icon="🧭", layout="wide")
apply_theme()

UPDATE_SCRIPT = Path("auto_update_app.py")


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
def load_outputs() -> dict[str, pd.DataFrame]:
    out: dict[str, pd.DataFrame] = {}
    out["ranking"] = pd.read_excel(RANKING_FILE) if RANKING_FILE.exists() else pd.DataFrame()
    if ALLOCATION_FILE.exists():
        out["allocation"] = pd.read_excel(ALLOCATION_FILE, sheet_name="Suggested_Allocation")
        out["summary"] = pd.read_excel(ALLOCATION_FILE, sheet_name="Summary")
    else:
        out["allocation"] = pd.DataFrame(); out["summary"] = pd.DataFrame()
    out["watchlist"] = pd.read_csv(WATCHLIST_OUTPUT_CSV) if WATCHLIST_OUTPUT_CSV.exists() else pd.DataFrame()
    out["insights"] = pd.read_csv(INSIGHTS_OUTPUT_CSV) if INSIGHTS_OUTPUT_CSV.exists() else pd.DataFrame()
    out["action_plan"] = pd.read_csv(ACTION_PLAN_OUTPUT_CSV) if ACTION_PLAN_OUTPUT_CSV.exists() else pd.DataFrame()
    out["sector_compass"] = pd.read_csv(SECTOR_COMPASS_OUTPUT_CSV) if SECTOR_COMPASS_OUTPUT_CSV.exists() else pd.DataFrame()
    return out


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
    st.title("🧭 AlphaForge")
    st.caption("Sector Compass per Fineco + consulente")
    st.write(f"**Stato:** {status.get('status', 'unknown')}")
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
            st.error("Aggiornamento non completato.")
            with st.expander("Dettagli errore"):
                st.code(output)
    st.divider()
    st.markdown("### Metodo")
    st.caption("1) Capisci il core gia' presente. 2) Scegli pochi settori satellite. 3) Per ogni settore confronta ETF/fondo e solo dopo eventuale azione singola.")

hero(
    "AlphaForge v7 Sector Compass",
    "Meno tabelle, piu' decisioni: la app parte dal tuo caso reale, cioe' un portafoglio gestito con core globale e consulente Fineco. Prima individua i settori da discutere, poi propone ETF/fondi candidati e alternative azionarie solo come satellite.",
    "Core + settori + consulente",
)

outputs = load_outputs()
sector = outputs["sector_compass"].copy()
ranking = outputs["ranking"].copy()
allocation = outputs["allocation"].copy()
action_plan = outputs["action_plan"].copy()

if sector.empty:
    st.error("Manca AlphaForge_Sector_Compass.csv. Esegui Auto update ETF Intelligence App o il Patch Installer con run_full_update=true.")
    st.stop()

sector = sector.sort_values("Sector Score", ascending=False, na_position="last")
last_update = file_last_update(SECTOR_COMPASS_OUTPUT_CSV)
first = sector.iloc[0].to_dict() if not sector.empty else {}

mini_cards([
    ("Settore da discutere", first.get("Settore", "n/d"), "Non e' un ordine: e' il primo tema da valutare"),
    ("Cosa fare", first.get("Cosa fare", "n/d"), "Sintesi operativa"),
    ("Strumento base", first.get("Strumento preferito", "ETF/Fondo"), "Default: diversificato"),
    ("Aggiornato", last_update, "Sector Compass"),
])

st.markdown("## Leggi prima questo")
st.success(
    "Se hai gia' All-World/fondi globali, non partire dalla singola azione. Parti da: **quali settori mi mancano davvero?** Poi verifica con il consulente Fineco quale ETF/fondo UCITS e' piu' adatto, costi inclusi."
)

tabs = st.tabs(["Bussola settoriale", "Strumenti per settore", "Portafoglio Fineco", "Domande consulente", "Avanzato"])

with tabs[0]:
    st.subheader("Bussola settoriale")
    info_panel(
        "Come usarla",
        "Questa pagina serve a scegliere i temi da discutere, non a fare trading. Per ogni settore vedi: priorita', strumento preferito, peso massimo indicativo e rischio principale.",
    )
    c1, c2, c3 = st.columns(3)
    with c1:
        buckets = sorted(sector["Bucket"].dropna().astype(str).unique().tolist()) if "Bucket" in sector.columns else []
        selected = st.multiselect("Filtro", buckets, default=buckets)
    with c2:
        min_score = st.slider("Sector Score minimo", 0, 100, 55)
    with c3:
        hide_core = st.checkbox("Nascondi core globale", value=False)
    view = sector.copy()
    if selected and "Bucket" in view.columns:
        view = view[view["Bucket"].isin(selected)]
    if "Sector Score" in view.columns:
        view = view[pd.to_numeric(view["Sector Score"], errors="coerce").fillna(0) >= min_score]
    if hide_core and "Settore" in view.columns:
        view = view[~view["Settore"].astype(str).str.contains("Core", case=False, na=False)]
    st.dataframe(
        style_priority_dataframe(safe_cols(view, ["Priorita", "Settore", "Bucket", "Cosa fare", "Sector Score", "Strumento preferito", "Ticker ETF/Fondo", "ETF/Fondo candidato", "Range pratico", "Perche guardarlo", "Rischio principale"])),
        use_container_width=True,
        hide_index=True,
    )

with tabs[1]:
    st.subheader("ETF/Fondo o azione singola?")
    st.caption("Default prudente: ETF/fondo. Azione singola solo se vuoi una quota piccola, consapevole e non sovrapposta al core.")
    selected_sector = st.selectbox("Scegli settore", sector["Settore"].astype(str).tolist())
    row = sector[sector["Settore"].astype(str) == selected_sector].iloc[0]
    mini_cards([
        ("Settore", row.get("Settore", ""), "Tema"),
        ("Preferenza", row.get("Strumento preferito", ""), "Strumento base"),
        ("Range", row.get("Range pratico", ""), "Peso massimo indicativo"),
        ("Rischio", row.get("Rischio principale", ""), "Da discutere"),
    ])
    st.markdown("### Candidato principale")
    st.write(f"**{row.get('ETF/Fondo candidato', '')}**")
    st.write(f"Ticker indicativo da verificare: **{row.get('Ticker ETF/Fondo', '')}**")
    st.markdown("### Alternative azionarie")
    leaders = str(row.get("Azioni leader", "")).replace("|", ", ")
    st.write(leaders or "Non prioritario: meglio ETF/fondo diversificato.")
    st.warning("Prima di investire: verifica KID, TER, valuta, liquidita', fiscalita', disponibilita' su Fineco e adeguatezza con il consulente.")

with tabs[2]:
    st.subheader("Portafoglio Fineco")
    info_panel(
        "Obiettivo",
        "Qui non serve importare automaticamente Fineco. Scarichi il template, inserisci le posizioni principali e assegni un settore AlphaForge. La app ti dice se sei troppo concentrato, se il core e' sufficiente e quali settori mancano.",
    )
    template_df = fineco_portfolio_template()
    st.download_button("⬇️ Scarica template Fineco CSV", template_df.to_csv(index=False).encode("utf-8"), "fineco_portfolio_template.csv", "text/csv")
    uploaded = st.file_uploader("Carica portafoglio CSV/XLSX", type=["csv", "xlsx", "xls"])
    use_demo = st.checkbox("Usa esempio demo", value=False)
    try:
        portfolio = template_df if use_demo and uploaded is None else read_uploaded_portfolio(uploaded)
    except Exception as exc:  # noqa: BLE001
        st.error(f"File non leggibile: {exc}")
        portfolio = pd.DataFrame()
    if portfolio.empty:
        st.caption("Colonne consigliate: Ticker, Nome Strumento, Tipo, Settore AlphaForge, Valore EUR, Target %, Note.")
    else:
        result = analyze_sector_portfolio(portfolio, sector)
        summary = result.summary
        mini_cards([
            ("Valore totale", f"€ {summary.get('Valore Totale EUR', 0):,.0f}".replace(",", "."), "Dati caricati"),
            ("Peso core", f"{summary.get('Peso core %', 0)}%", "Core globale"),
            ("Peso satellite", f"{summary.get('Peso satellite %', 0)}%", "Settori/temi"),
            ("Peso maggiore", f"{summary.get('Peso maggiore %', 0)}%", "Concentrazione"),
        ])
        st.markdown("### Suggerimenti principali")
        st.dataframe(result.suggestions, use_container_width=True, hide_index=True)
        st.markdown("### Vista per settore")
        st.dataframe(result.sector_view, use_container_width=True, hide_index=True)
        st.markdown("### Posizioni")
        cols = ["Ticker", "Nome Strumento", "Tipo", "Settore AlphaForge", "Valore EUR", "Peso %", "Target %", "Bucket", "Sector Score", "Lettura portafoglio"]
        st.dataframe(safe_cols(result.positions, cols), use_container_width=True, hide_index=True)

with tabs[3]:
    st.subheader("Domande da portare al consulente")
    st.markdown(
        """
        1. Il mio core globale e' gia' abbastanza diversificato o sto duplicando gli stessi indici?
        2. Quali settori ha senso aggiungere come satellite e con quale peso massimo?
        3. Per ogni settore: meglio ETF UCITS, fondo attivo o nessuna aggiunta?
        4. Quali strumenti sono disponibili su Fineco, con KID, TER e liquidita' adeguati?
        5. Che impatto hanno fiscalita', valuta, orizzonte temporale e rischio complessivo?
        6. Se scelgo azioni singole, qual e' la quota massima accettabile rispetto al patrimonio?
        """
    )
    if not sector.empty:
        st.markdown("### Prime 5 discussioni suggerite")
        st.dataframe(safe_cols(sector.head(5), ["Settore", "Cosa fare", "ETF/Fondo candidato", "Range pratico", "Rischio principale", "Nota Fineco/Consulente"]), use_container_width=True, hide_index=True)

with tabs[4]:
    st.subheader("Dati avanzati")
    st.caption("Qui trovi le vecchie viste quantitative. Sono utili come supporto, non come schermata principale.")
    sub = st.tabs(["Action Plan", "Ranking ETF", "Allocazione", "Report"])
    with sub[0]:
        st.dataframe(action_plan, use_container_width=True, hide_index=True)
    with sub[1]:
        st.dataframe(ranking, use_container_width=True, hide_index=True)
    with sub[2]:
        st.dataframe(allocation, use_container_width=True, hide_index=True)
    with sub[3]:
        if REPORT_FILE.exists():
            st.text(REPORT_FILE.read_text(encoding="utf-8"))
        else:
            st.caption("Report non disponibile.")

st.caption("Informazioni educative e di monitoraggio. Non costituiscono consulenza finanziaria personalizzata o sollecitazione all'investimento.")
