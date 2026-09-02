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
st.title("📰 Notizie e segnali sui fondi Fineco")
st.caption("News radar prudente: non predice il futuro, ma aiuta a capire cosa monitorare nei prossimi giorni.")

st.info(
    "Per i fondi comuni il NAV non è real-time: le notizie servono per leggere il contesto. "
    "Il bias 'favorevole/attenzione/neutro' non è un consiglio di acquisto o vendita."
)

col1, col2 = st.columns([1, 1])
with col1:
    refresh = st.button("🔄 Aggiorna news ora", use_container_width=True)
with col2:
    st.write("Fonte: Google News RSS pubblico + lettura keyword AlphaForge")

if IMPORT_ERROR is not None:
    st.error(f"Modulo news non disponibile: {IMPORT_ERROR}")
    st.stop()

if refresh and save_news_radar is not None:
    with st.spinner("Aggiornamento news in corso..."):
        radar, summary = save_news_radar()
    st.success(f"News aggiornate: {len(radar)} righe")
else:
    radar_path = Path("AlphaForge_News_Radar.csv")
    summary_path = Path("AlphaForge_News_Radar_Summary.json")
    radar = pd.read_csv(radar_path) if radar_path.exists() else pd.DataFrame()
    summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() else {}

funds = pd.DataFrame(summary.get("funds", [])) if isinstance(summary, dict) else pd.DataFrame()

st.subheader("Bias per fondo")
if funds.empty:
    st.warning("Nessun riepilogo news disponibile. Premi 'Aggiorna news ora' oppure lancia l'Auto update.")
else:
    st.dataframe(funds, use_container_width=True, hide_index=True)

st.subheader("Ultime notizie rilevate")
if radar.empty:
    st.warning("Nessuna notizia disponibile.")
else:
    cols = [c for c in ["Nome Strumento", "Categoria AlphaForge", "Titolo", "Fonte", "News Score", "Lettura", "Impatto possibile", "Link"] if c in radar.columns]
    st.dataframe(radar[cols], use_container_width=True, hide_index=True)

st.markdown("### Come usarlo")
st.write(
    "Se vedi molte notizie negative su un settore, non significa vendere subito: significa evitare di aumentare l'esposizione "
    "senza aver capito se il rischio è temporaneo o strutturale. Se vedi notizie positive, non inseguire il prezzo: usa PAC, ingressi graduali o alert."
)
