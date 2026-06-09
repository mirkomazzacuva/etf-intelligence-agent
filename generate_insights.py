from __future__ import annotations

import pandas as pd

from core.config import INSIGHTS_OUTPUT_CSV, INSIGHTS_OUTPUT_XLSX, RANKING_FILE, WATCHLIST_OUTPUT_CSV
from core.insight_engine import build_insights_table


def generate_insights() -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    if RANKING_FILE.exists():
        frames.append(pd.read_excel(RANKING_FILE))
    if WATCHLIST_OUTPUT_CSV.exists():
        frames.append(pd.read_csv(WATCHLIST_OUTPUT_CSV))
    insights = build_insights_table(frames)
    if insights.empty:
        raise RuntimeError("Nessun insight generabile: ranking/watchlist vuoti")
    insights.to_csv(INSIGHTS_OUTPUT_CSV, index=False)
    with pd.ExcelWriter(INSIGHTS_OUTPUT_XLSX, engine="openpyxl") as writer:
        insights.to_excel(writer, sheet_name="Insights", index=False)
    print(f"Insights generati: {len(insights)} strumenti")
    return insights


if __name__ == "__main__":
    generate_insights()
