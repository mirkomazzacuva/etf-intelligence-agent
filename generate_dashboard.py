from __future__ import annotations

import json

import pandas as pd

from core.config import (
    ALLOCATION_FILE,
    DASHBOARD_FILE,
    INSIGHTS_OUTPUT_CSV,
    RANKING_FILE,
    REPORT_FILE,
    STATUS_FILE,
    WATCHLIST_OUTPUT_CSV,
)
from core.report_engine import build_text_report, render_dashboard_html


def read_status() -> dict:
    if STATUS_FILE.exists():
        try:
            return json.loads(STATUS_FILE.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            return {"status": "unknown"}
    return {"status": "unknown"}


def generate_dashboard() -> None:
    if not RANKING_FILE.exists() or not ALLOCATION_FILE.exists():
        raise FileNotFoundError("Mancano ranking o allocazione")
    ranking = pd.read_excel(RANKING_FILE)
    allocation = pd.read_excel(ALLOCATION_FILE, sheet_name="Suggested_Allocation")
    watchlist = pd.read_csv(WATCHLIST_OUTPUT_CSV) if WATCHLIST_OUTPUT_CSV.exists() else pd.DataFrame()
    insights = pd.read_csv(INSIGHTS_OUTPUT_CSV) if INSIGHTS_OUTPUT_CSV.exists() else pd.DataFrame()
    status = read_status()
    REPORT_FILE.write_text(build_text_report(ranking, allocation, watchlist, insights), encoding="utf-8")
    render_dashboard_html(ranking, allocation, status, watchlist, DASHBOARD_FILE, insights)
    print(f"Dashboard generata: {DASHBOARD_FILE}")


if __name__ == "__main__":
    generate_dashboard()
