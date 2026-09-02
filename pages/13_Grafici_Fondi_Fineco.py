from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

try:
    import plotly.express as px
except Exception:  # noqa: BLE001
    px = None  # type: ignore[assignment]

try:
    from core.fund_market_engine import build_fund_performance, save_fund_performance
except Exception as exc:  # noqa: BLE001
    build_fund_performance = None  # type: ignore[assignment]
    save_fund_performance = None  # type: ignore[assignment]
    IMPORT_ERROR = exc
else:
    IMPORT_ERROR = None

st.set_page_config(page_title="Grafici fondi Fineco", page_icon="📈", layout="wide")
st.title("📈 Grafici fondi Fineco")
st.caption("Vista tipo Investing: watchlist, performance proxy e grafici normalizzati. Per i fondi comuni il NAV ufficiale resta quello Fineco.")

st.info("I fondi comuni non sono davvero intraday: AlphaForge usa proxy ETF/mercato per capire il contesto quasi real-time. Se un proxy non scarica dati, prova automaticamente ticker alternativi.")

col1, col2, col3 = st.columns([1, 1, 2])
with col1:
    refresh = st.button("🔄 Aggiorna ora", use_container_width=True)
with col2:
    period = st.selectbox("Periodo", ["1y", "6mo", "3mo"], index=0)
with col3:
    st.write("Suggerimento: dopo l'aggiornamento, torna alla home per vedere il grafico anche nella dashboard pubblica.")

if IMPORT_ERROR is not None:
    st.error(f"Modulo performance non disponibile: {IMPORT_ERROR}")
    st.stop()

if refresh and build_fund_performance is not None:
    with st.spinner("Scarico dati proxy e costruisco grafici..."):
        performance, history = build_fund_performance(period=period)
        performance.to_csv("AlphaForge_Fund_Performance.csv", index=False)
        history.to_csv("AlphaForge_Fund_Price_History.csv", index=False)
    st.success(f"Aggiornati {len(performance)} strumenti e {len(history)} punti storici.")
else:
    perf_path = Path("AlphaForge_Fund_Performance.csv")
    hist_path = Path("AlphaForge_Fund_Price_History.csv")
    performance = pd.read_csv(perf_path) if perf_path.exists() else pd.DataFrame()
    history = pd.read_csv(hist_path) if hist_path.exists() else pd.DataFrame()

st.subheader("Watchlist performance")
if performance.empty:
    st.warning("Nessun dato disponibile. Premi Aggiorna ora o lancia Auto update.")
else:
    cols = [
        "Nome Strumento", "Tipo Versamento", "Importo iniziale EUR", "PAC mensile EUR", "Proxy usato",
        "Rendimento proxy 1D %", "Rendimento proxy 1M %", "Rendimento proxy 3M %", "Rendimento proxy 1Y %",
        "Trend proxy", "Costo annuo %", "Azione pratica", "Fonte dato",
    ]
    st.dataframe(performance[[c for c in cols if c in performance.columns]], use_container_width=True, hide_index=True)

st.subheader("Grafico confronto")
if history.empty:
    st.warning("Storico proxy non disponibile. Possibili cause: ticker non supportato, yfinance momentaneamente bloccato, o dipendenze non installate.")
else:
    options = sorted(history["Nome Strumento"].dropna().unique().tolist())
    selected = st.multiselect("Fondi/proxy da mostrare", options, default=options[:7])
    view = history[history["Nome Strumento"].isin(selected)].copy()
    if view.empty:
        st.info("Seleziona almeno un fondo.")
    elif px is not None:
        fig = px.line(view, x="Date", y="Normalized 100", color="Nome Strumento", hover_data=["Proxy usato"] if "Proxy usato" in view.columns else None)
        fig.update_layout(height=620, yaxis_title="Base 100", xaxis_title="Data", legend_title="Fondo/proxy", margin=dict(l=20, r=20, t=30, b=20))
        st.plotly_chart(fig, use_container_width=True)
    else:
        chart = view.pivot_table(index="Date", columns="Nome Strumento", values="Normalized 100", aggfunc="last")
        st.line_chart(chart, use_container_width=True)

st.subheader("Grafici singoli")
if not history.empty:
    for name in sorted(history["Nome Strumento"].dropna().unique().tolist()):
        single = history[history["Nome Strumento"] == name].copy()
        if single.empty:
            continue
        with st.expander(name, expanded=False):
            if px is not None:
                fig = px.line(single, x="Date", y="Normalized 100")
                fig.update_layout(height=330, yaxis_title="Base 100", xaxis_title="Data", margin=dict(l=20, r=20, t=10, b=20))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.line_chart(single.set_index("Date")[["Normalized 100"]], use_container_width=True)

st.markdown("### Lettura corretta")
st.write("Un proxy non è il fondo ufficiale: serve per capire se il mercato sottostante sta salendo o scendendo. La performance reale si valuta con NAV/controvalore Fineco e benchmark coerente.")
