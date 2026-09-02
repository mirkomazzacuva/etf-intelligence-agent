from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

try:
    from core.fund_market_engine import build_fund_performance, save_fund_performance
except Exception as exc:  # noqa: BLE001
    build_fund_performance = None  # type: ignore[assignment]
    save_fund_performance = None  # type: ignore[assignment]
    IMPORT_ERROR = exc
else:
    IMPORT_ERROR = None

st.set_page_config(page_title="Grafici fondi Fineco", page_icon="📈", layout="wide")
st.title("📈 Andamento fondi Fineco")
st.caption("Grafici proxy quasi real-time per ETF/mercati collegati ai fondi. Per i fondi comuni il NAV è giornaliero, non intraday.")

st.warning(
    "I grafici usano proxy di mercato quando il NAV del fondo non è disponibile via ticker pubblico. "
    "Il valore ufficiale resta quello mostrato da Fineco."
)

col1, col2 = st.columns([1, 1])
with col1:
    refresh = st.button("🔄 Aggiorna grafici ora", use_container_width=True)
with col2:
    period = st.selectbox("Periodo", ["1y", "6mo", "3mo"], index=0)

if IMPORT_ERROR is not None:
    st.error(f"Modulo performance non disponibile: {IMPORT_ERROR}")
    st.stop()

if refresh and save_fund_performance is not None:
    with st.spinner("Scarico dati proxy..."):
        performance, history = build_fund_performance(period=period)
else:
    perf_path = Path("AlphaForge_Fund_Performance.csv")
    hist_path = Path("AlphaForge_Fund_Price_History.csv")
    performance = pd.read_csv(perf_path) if perf_path.exists() else pd.DataFrame()
    history = pd.read_csv(hist_path) if hist_path.exists() else pd.DataFrame()

st.subheader("Riepilogo andamento")
if performance.empty:
    st.warning("Nessun dato disponibile. Premi aggiorna o lancia Auto update.")
else:
    st.dataframe(performance, use_container_width=True, hide_index=True)

st.subheader("Grafico normalizzato")
if history.empty:
    st.warning("Storico proxy non disponibile.")
else:
    options = sorted(history["Nome Strumento"].dropna().unique().tolist())
    selected = st.multiselect("Fondi da mostrare", options, default=options[:5])
    view = history[history["Nome Strumento"].isin(selected)].copy()
    if view.empty:
        st.info("Seleziona almeno un fondo.")
    else:
        chart = view.pivot_table(index="Date", columns="Nome Strumento", values="Normalized 100", aggfunc="last")
        st.line_chart(chart, use_container_width=True)

st.markdown("### Lettura corretta")
st.write(
    "Un fondo comune non si muove minuto per minuto come un'azione. La valorizzazione ufficiale viene aggiornata a NAV, di norma giornalmente. "
    "Il grafico proxy serve a capire se il mercato sottostante sta migliorando o peggiorando prima del prossimo NAV."
)
