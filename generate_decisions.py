from __future__ import annotations

import pandas as pd

from core.config import ACTION_PLAN_OUTPUT_CSV, ACTION_PLAN_OUTPUT_XLSX, INSIGHTS_OUTPUT_CSV, RANKING_FILE, WATCHLIST_OUTPUT_CSV
from core.decision_engine import build_action_plan


def generate_decisions() -> pd.DataFrame:
    ranking = pd.read_excel(RANKING_FILE) if RANKING_FILE.exists() else pd.DataFrame()
    watchlist = pd.read_csv(WATCHLIST_OUTPUT_CSV) if WATCHLIST_OUTPUT_CSV.exists() else pd.DataFrame()
    insights = pd.read_csv(INSIGHTS_OUTPUT_CSV) if INSIGHTS_OUTPUT_CSV.exists() else pd.DataFrame()
    action_plan = build_action_plan(ranking, watchlist, insights)
    if action_plan.empty:
        raise RuntimeError("Nessuna decisione generabile: ranking/watchlist/insights vuoti")
    action_plan.to_csv(ACTION_PLAN_OUTPUT_CSV, index=False)
    with pd.ExcelWriter(ACTION_PLAN_OUTPUT_XLSX, engine="openpyxl") as writer:
        action_plan.to_excel(writer, sheet_name="Action_Plan", index=False)
    print(f"Action plan generato: {len(action_plan)} strumenti")
    return action_plan


if __name__ == "__main__":
    generate_decisions()
