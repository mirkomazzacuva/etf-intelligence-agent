from __future__ import annotations

import pandas as pd
import streamlit as st

from core.config import SECTOR_COMPASS_OUTPUT_CSV

try:
    from core.ui_theme import apply_theme, hero, mini_cards, style_priority_dataframe, info_panel
except Exception:  # noqa: BLE001
    def apply_theme() -> None: return None
    def hero(title: str, subtitle: str, label: str = "") -> None:
        st.title(title); st.caption(label); st.write(subtitle)
    def mini_cards(cards):
        cols = st.columns(len(cards))
        for col, (label, value, hint) in zip(cols, cards):
            col.metric(label, value, help=hint)
    def style_priority_dataframe(df): return df
    def info_panel(title: str, body: str) -> None: st.info(f"**{title}**\n\n{body}")

st.set_page_config(page_title="Bussola Settoriale", page_icon="🧭", layout="wide")
apply_theme()
hero(
    "Bussola Settoriale",
    "La vista piu' importante per il tuo caso: core globale gia' presente, poi pochi settori satellite da discutere con il consulente.",
    "AlphaForge v7",
)

if not SECTOR_COMPASS_OUTPUT_CSV.exists():
    st.error("AlphaForge_Sector_Compass.csv non trovato. Esegui aggiornamento completo.")
    st.stop()

sector = pd.read_csv(SECTOR_COMPASS_OUTPUT_CSV).sort_values("Sector Score", ascending=False, na_position="last")
first = sector.iloc[0]
mini_cards([
    ("Primo settore", first.get("Settore", ""), "Da discutere"),
    ("Azione", first.get("Cosa fare", ""), "Sintesi"),
    ("Score", first.get("Sector Score", ""), "0-100"),
    ("Range", first.get("Range pratico", ""), "Peso satellite"),
])
info_panel("Regola pratica", "Se possiedi gia' All-World o fondi globali, non comprare un tema solo perche' ha score alto: verifica prima esposizione gia' incorporata, costi, KID e peso massimo.")

cols = ["Priorita", "Settore", "Bucket", "Cosa fare", "Sector Score", "Strumento preferito", "Ticker ETF/Fondo", "ETF/Fondo candidato", "Range pratico", "Perche guardarlo", "Rischio principale", "Nota Fineco/Consulente"]
st.dataframe(style_priority_dataframe(sector[[c for c in cols if c in sector.columns]]), use_container_width=True, hide_index=True)
