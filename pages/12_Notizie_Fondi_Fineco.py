from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

try:
    from core.news_radar_engine import build_news_radar, save_news_radar
except Exception as exc:  # noqa: BLE001
    build_news_radar = None  # type: ignore[assignment]
    save_news_radar = None  # type: ignore[assignment]
    IMPORT_ERROR = exc
else:
    IMPORT_ERROR = None

st.set_page_config(page_title="Notizie fondi Fineco", page_icon="📰", layout="wide")
st.title("📰 Notizie fondi Fineco")
st.caption("Resoconto finanziario collegato ai tuoi fondi/PAC: cosa può aiutare o penalizzare i prossimi giorni.")

st.info("Il bias non è una previsione certa: è una lettura prudente delle notizie per capire se un settore è favorito, neutro o sotto pressione.")

col1, col2, col3 = st.columns([1, 1, 2])
with col1:
    refresh = st.button("🔄 Aggiorna news", use_container_width=True)
with col2:
    st.metric("Fonte", "Google News RSS")
with col3:
    st.write("Le query sono collegate ai fondi: tecnologia/cloud, emergenti, dividend, multi-asset, Europa.")

if IMPORT_ERROR is not None:
    st.error(f"Modulo news non disponibile: {IMPORT_ERROR}")
    st.stop()

if refresh and save_news_radar is not None:
    with st.spinner("Aggiorno news radar..."):
        radar, summary = save_news_radar()
    st.success(f"News aggiornate: {len(radar)} righe")
else:
    radar_path = Path("AlphaForge_News_Radar.csv")
    summary_path = Path("AlphaForge_News_Radar_Summary.json")
    radar = pd.read_csv(radar_path) if radar_path.exists() else pd.DataFrame()
    summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() else {}

funds = pd.DataFrame(summary.get("funds", [])) if isinstance(summary, dict) else pd.DataFrame()

st.subheader("Bias sintetico per fondo")
if funds.empty:
    st.warning("Nessun riepilogo news disponibile. Premi Aggiorna news oppure lancia Auto update.")
else:
    st.dataframe(funds, use_container_width=True, hide_index=True)

st.subheader("Feed notizie rilevanti")
if radar.empty:
    st.warning("Nessuna notizia disponibile.")
else:
    if "News Score" in radar.columns:
        radar = radar.sort_values("News Score", ascending=False, na_position="last")
    cols = ["Nome Strumento", "Categoria AlphaForge", "Titolo", "Fonte", "News Score", "Lettura", "Impatto possibile", "Link"]
    st.dataframe(radar[[c for c in cols if c in radar.columns]], use_container_width=True, hide_index=True)

st.markdown("### Come usarlo")
st.write("Se un fondo ha bias di attenzione non significa vendere: significa non aumentare alla cieca. Se il bias è favorevole non significa comprare subito: meglio usare PAC, ingressi graduali o confronto col consulente.")
