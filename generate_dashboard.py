from __future__ import annotations

import json

import pandas as pd

from core.config import (
    ACTION_PLAN_OUTPUT_CSV,
    ALLOCATION_FILE,
    DASHBOARD_FILE,
    INSIGHTS_OUTPUT_CSV,
    RANKING_FILE,
    REPORT_FILE,
    SECTOR_COMPASS_OUTPUT_CSV,
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


def _read_csv(path) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def generate_dashboard() -> None:
    if not RANKING_FILE.exists() or not ALLOCATION_FILE.exists():
        raise FileNotFoundError("Mancano ranking o allocazione")
    ranking = pd.read_excel(RANKING_FILE)
    allocation = pd.read_excel(ALLOCATION_FILE, sheet_name="Suggested_Allocation")
    watchlist = _read_csv(WATCHLIST_OUTPUT_CSV)
    insights = _read_csv(INSIGHTS_OUTPUT_CSV)
    action_plan = _read_csv(ACTION_PLAN_OUTPUT_CSV)
    sector_compass = _read_csv(SECTOR_COMPASS_OUTPUT_CSV)
    status = read_status()
    REPORT_FILE.write_text(
        build_text_report(ranking, allocation, watchlist, insights, action_plan, sector_compass),
        encoding="utf-8",
    )
    render_dashboard_html(ranking, allocation, status, watchlist, DASHBOARD_FILE, insights, action_plan, sector_compass)
    print(f"Dashboard v7 generata: {DASHBOARD_FILE}")


if __name__ == "__main__":
    generate_dashboard()
