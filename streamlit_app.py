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
    FINECO_FUND_PERFORMANCE_CSV,
    FINECO_FUND_PRICE_HISTORY_CSV,
    FINECO_FUNDS_PUBLIC_FILE,
    FINECO_NEWS_RADAR_CSV,
    FINECO_NEWS_RADAR_SUMMARY,
    FINECO_PORTFOLIO_OUTPUT_CSV,
    FINECO_PORTFOLIO_SUMMARY_FILE,
    SECTOR_COMPASS_OUTPUT_CSV,
    STATUS_FILE,
)

st.set_page_config(page_title="AlphaForge v9.1", page_icon="📊", layout="wide")


CSS = """
<style>
:root { --af-bg:#f5f7fb; --af-card:#ffffff; --af-border:#e2e8f0; --af-text:#111827; --af-muted:#64748b; --af-green:#0f9f6e; --af-red:#dc2626; --af-blue:#2563eb; --af-amber:#d97706; }
.stApp { background: var(--af-bg); }
.block-container { padding-top: 1.4rem; padding-bottom: 2.5rem; max-width: 1400px; }
.af-hero { background: linear-gradient(135deg,#0f172a 0%,#172554 55%,#064e3b 100%); padding: 24px 26px; border-radius: 22px; color: white; margin-bottom: 18px; box-shadow: 0 18px 45px rgba(15,23,42,.18); }
.af-hero h1 { margin: 0; font-size: 42px; letter-spacing: -0.04em; }
.af-hero p { color: #dbeafe; margin: 8px 0 0; font-size: 16px; }
.af-kpi { background: var(--af-card); border: 1px solid var(--af-border); border-radius: 18px; padding: 16px 18px; box-shadow: 0 10px 28px rgba(15,23,42,.06); min-height: 105px; }
.af-kpi .label { color: var(--af-muted); font-size: 13px; font-weight: 700; text-transform: uppercase; letter-spacing: .05em; }
.af-kpi .value { color: var(--af-text); font-size: 30px; font-weight: 900; margin-top: 4px; }
.af-kpi .hint { color: var(--af-muted); font-size: 12px; margin-top: 4px; }
.af-panel { background: var(--af-card); border: 1px solid var(--af-border); border-radius: 18px; padding: 18px; box-shadow: 0 10px 28px rgba(15,23,42,.05); }
.af-chip { display:inline-block; padding: 4px 9px; border-radius:999px; background:#e0f2fe; color:#075985; font-size:12px; font-weight:800; margin-right:5px; }
.af-chip.green { background:#dcfce7; color:#166534; }
.af-chip.red { background:#fee2e2; color:#991b1b; }
.af-chip.amber { background:#fef3c7; color:#92400e; }
div[data-testid="stMetric"] { background: var(--af-card); border:1px solid var(--af-border); padding:14px; border-radius:16px; box-shadow:0 8px 22px rgba(15,23,42,.05); }
[data-testid="stDataFrame"] { border-radius: 14px; overflow: hidden; }
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


def euro(value: float | int | str | None) -> str:
    try:
        return f"{float(value):,.0f} €".replace(",", ".")
    except Exception:  # noqa: BLE001
        return "n/d"


def pct(value: float | int | str | None) -> str:
    try:
        return f"{float(value):+.2f}%".replace(".", ",")
    except Exception:  # noqa: BLE001
        return "n/d"


def portfolio_totals(funds: pd.DataFrame, summary: dict) -> dict[str, float]:
    if not funds.empty:
        one_off = pd.to_numeric(funds.get("Importo Iniziale EUR", 0), errors="coerce").fillna(0).sum()
        pac = pd.to_numeric(funds.get("PAC Mensile EUR", 0), errors="coerce").fillna(0).sum()
        bollo = pd.to_numeric(funds.get("Bollo Una Tantum EUR", 0), errors="coerce").fillna(0).sum()
        tracked = len(funds)
        return {"one_off": float(one_off), "pac": float(pac), "bollo": float(bollo), "tracked": float(tracked)}
    return {
        "one_off": float(summary.get("capitale_una_tantum_eur", 0) or 0),
        "pac": float(summary.get("pac_mensile_eur", 0) or 0),
        "bollo": 42.0,
        "tracked": float(summary.get("numero_strumenti", 0) or 0),
    }


status = read_json(STATUS_FILE)
summary = read_json(FINECO_PORTFOLIO_SUMMARY_FILE)
news_summary = read_json(FINECO_NEWS_RADAR_SUMMARY)
funds = read_csv(FINECO_FUNDS_PUBLIC_FILE)
fineco = read_csv(FINECO_PORTFOLIO_OUTPUT_CSV)
fund_perf = read_csv(FINECO_FUND_PERFORMANCE_CSV)
fund_history = read_csv(FINECO_FUND_PRICE_HISTORY_CSV)
news = read_csv(FINECO_NEWS_RADAR_CSV)
sectors = read_csv(SECTOR_COMPASS_OUTPUT_CSV)
actions = read_csv(ACTION_PLAN_OUTPUT_CSV)
tot = portfolio_totals(funds, summary)

st.markdown(
    """
<div class="af-hero">
  <div><span class="af-chip green">AlphaForge v9.1</span><span class="af-chip">Investing-style dashboard</span></div>
  <h1>Il tuo portafoglio Fineco sotto controllo</h1>
  <p>Vista rapida tipo watchlist: importi corretti, PAC, costi, news radar e grafici proxy quasi real-time.</p>
</div>
""",
    unsafe_allow_html=True,
)

k1, k2, k3, k4, k5 = st.columns(5)
k1.markdown(f"<div class='af-kpi'><div class='label'>Investito una tantum</div><div class='value'>{euro(tot['one_off'])}</div><div class='hint'>5 fondi x 5.000 €</div></div>", unsafe_allow_html=True)
k2.markdown(f"<div class='af-kpi'><div class='label'>PAC mensile</div><div class='value'>{euro(tot['pac'])}</div><div class='hint'>2 PAC x 150 €/mese</div></div>", unsafe_allow_html=True)
k3.markdown(f"<div class='af-kpi'><div class='label'>Bollo una tantum</div><div class='value'>{euro(tot['bollo'])}</div><div class='hint'>6 € per prodotto</div></div>", unsafe_allow_html=True)
k4.markdown(f"<div class='af-kpi'><div class='label'>Fondi/PAC</div><div class='value'>{int(tot['tracked'])}</div><div class='hint'>Strumenti caricati</div></div>", unsafe_allow_html=True)
k5.markdown(f"<div class='af-kpi'><div class='label'>Stato</div><div class='value'>{summary.get('fase', 'Punto zero')}</div><div class='hint'>{status.get('version', 'v9.1')}</div></div>", unsafe_allow_html=True)

st.info("Nota: per i fondi comuni il valore ufficiale resta il NAV Fineco, di norma giornaliero. I grafici usano proxy ETF/mercato per leggere il contesto prima dell'aggiornamento del NAV.")

tab1, tab2, tab3, tab4 = st.tabs(["📌 Panoramica", "📈 Grafici", "📰 Notizie", "🧭 Cosa controllare"])

with tab1:
    left, right = st.columns([1.35, 1])
    with left:
        st.subheader("Watchlist fondi/PAC")
        if funds.empty:
            st.warning("File data/fineco_funds_public.csv non trovato.")
        else:
            view = funds.copy()
            view["Capitale/PAC"] = view.apply(lambda r: euro(r.get("Importo Iniziale EUR", 0)) if float(r.get("Importo Iniziale EUR", 0) or 0) > 0 else euro(r.get("PAC Mensile EUR", 0)) + "/mese", axis=1)
            cols = ["ISIN", "Nome Strumento", "Tipo Versamento", "Capitale/PAC", "Costo Annuo %", "Ruolo", "Categoria AlphaForge", "Proxy Ticker"]
            st.dataframe(view[[c for c in cols if c in view.columns]], use_container_width=True, hide_index=True)
    with right:
        st.subheader("Peso iniziale una tantum")
        if not funds.empty:
            alloc = funds[pd.to_numeric(funds["Importo Iniziale EUR"], errors="coerce").fillna(0) > 0].copy()
            if px is not None and not alloc.empty:
                fig = px.pie(alloc, names="Nome Strumento", values="Importo Iniziale EUR", hole=0.55)
                fig.update_layout(height=380, margin=dict(l=10, r=10, t=10, b=10), legend=dict(orientation="h"))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.dataframe(alloc[["Nome Strumento", "Importo Iniziale EUR"]], use_container_width=True, hide_index=True)

    st.subheader("Performance proxy")
    if fund_perf.empty:
        st.warning("Nessuna performance proxy disponibile. Lancia Auto update oppure apri la pagina Grafici e premi Aggiorna.")
    else:
        cols = ["Nome Strumento", "Proxy usato", "Rendimento proxy 1D %", "Rendimento proxy 1M %", "Rendimento proxy 3M %", "Rendimento proxy 1Y %", "Trend proxy", "Azione pratica"]
        st.dataframe(fund_perf[[c for c in cols if c in fund_perf.columns]], use_container_width=True, hide_index=True)

with tab2:
    st.subheader("Grafico normalizzato a 100")
    if fund_history.empty:
        st.warning("Storico proxy non disponibile. Il prossimo Auto update dovrebbe crearlo. Se resta vuoto, bisogna cambiare ticker proxy.")
        if not funds.empty:
            st.dataframe(funds[["Nome Strumento", "Proxy Ticker", "Proxy Tickers", "Proxy Nome"]], use_container_width=True, hide_index=True)
    else:
        names = sorted(fund_history["Nome Strumento"].dropna().unique().tolist())
        default = names[:7]
        selected = st.multiselect("Fondi da confrontare", names, default=default)
        view = fund_history[fund_history["Nome Strumento"].isin(selected)].copy()
        if px is not None and not view.empty:
            fig = px.line(view, x="Date", y="Normalized 100", color="Nome Strumento", hover_data=["Proxy usato"] if "Proxy usato" in view.columns else None)
            fig.update_layout(height=560, yaxis_title="Base 100", xaxis_title="Data", legend_title="Fondo/proxy", margin=dict(l=20, r=20, t=20, b=20))
            st.plotly_chart(fig, use_container_width=True)
        elif not view.empty:
            chart = view.pivot_table(index="Date", columns="Nome Strumento", values="Normalized 100", aggfunc="last")
            st.line_chart(chart, use_container_width=True)

with tab3:
    st.subheader("News radar")
    funds_summary = pd.DataFrame(news_summary.get("funds", [])) if isinstance(news_summary, dict) else pd.DataFrame()
    if not funds_summary.empty:
        st.dataframe(funds_summary, use_container_width=True, hide_index=True)
    if not news.empty:
        cols = ["Nome Strumento", "Categoria AlphaForge", "Titolo", "Fonte", "News Score", "Lettura", "Impatto possibile", "Link"]
        st.dataframe(news[[c for c in cols if c in news.columns]].head(30), use_container_width=True, hide_index=True)
    if news.empty and funds_summary.empty:
        st.warning("Nessuna news disponibile. Lancia Auto update o apri la pagina Notizie e premi Aggiorna.")

with tab4:
    st.subheader("Cosa controllare adesso")
    checklist = pd.DataFrame([
        {"Quando": "Subito", "Controllo": "Importi", "Dettaglio": "Una tantum corretta: 25.000 €. PAC: 300 €/mese."},
        {"Quando": "Subito", "Controllo": "Esecuzione", "Dettaglio": "Data valuta, quote assegnate, prezzo medio, NAV Fineco."},
        {"Quando": "1 mese", "Controllo": "PAC", "Dettaglio": "Verifica partenza dei due PAC da 150 €/mese."},
        {"Quando": "3-6 mesi", "Controllo": "Pesi", "Dettaglio": "Controlla se tecnologia/emergenti stanno diventando troppo pesanti."},
        {"Quando": "12 mesi", "Controllo": "Performance", "Dettaglio": "Confronta ogni fondo col suo proxy/benchmark e col costo annuo."},
    ])
    st.dataframe(checklist, use_container_width=True, hide_index=True)
    if not sectors.empty:
        st.subheader("Bussola settoriale")
        cols = ["Priorita", "Settore", "Bucket", "Cosa fare", "Sector Score", "ETF/Fondo candidato"]
        st.dataframe(sectors[[c for c in cols if c in sectors.columns]].head(10), use_container_width=True, hide_index=True)
    if not actions.empty:
        st.subheader("Priorità operative")
        cols = ["Ticker", "Decisione chiara", "Cosa fare adesso", "Bucket operativo"]
        st.dataframe(actions[[c for c in cols if c in actions.columns]].head(10), use_container_width=True, hide_index=True)

st.warning("App informativa per monitoraggio personale. Non costituisce consulenza finanziaria o garanzia di rendimento.")
