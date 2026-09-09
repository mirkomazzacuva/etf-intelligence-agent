from __future__ import annotations

import json
from datetime import date
from typing import Any

import pandas as pd

from core.config import (
    FINECO_DECISION_COCKPIT_CSV,
    FINECO_DECISION_COCKPIT_XLSX,
    FINECO_DECISION_SUMMARY_FILE,
)
from core.live_value_engine import VERSION, build_live_portfolio_snapshot, save_live_portfolio_snapshot


def today_rome() -> date:
    from core.live_value_engine import today_rome as _today
    return _today()


def build_decision_cockpit(as_of: date | None = None) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Build the decision cockpit from the v11 live value engine.

    This keeps the old public file names used by the dashboard, but the values now come
    from the live/proxy snapshot and include:
    - current estimated countervalue,
    - net margin since subscription,
    - 3 month and 1 year projections,
    - practical hold/switch signal.
    """
    live, _history, summary = build_live_portfolio_snapshot(as_of=as_of)
    summary = dict(summary)
    summary["version"] = VERSION
    summary["latest_proxy_date"] = summary.get("data_analisi", "n/d")
    summary["valore_attuale_eur"] = summary.get("controvalore_attuale_eur", summary.get("valore_attuale_eur", 0))
    return live, summary


def save_decision_cockpit() -> tuple[pd.DataFrame, dict[str, Any]]:
    # Also save the dedicated live files for the Streamlit/public dashboard.
    live, _history, summary = save_live_portfolio_snapshot()
    summary = dict(summary)
    summary["version"] = VERSION
    summary["latest_proxy_date"] = summary.get("data_analisi", "n/d")
    summary["valore_attuale_eur"] = summary.get("controvalore_attuale_eur", summary.get("valore_attuale_eur", 0))
    live.to_csv(FINECO_DECISION_COCKPIT_CSV, index=False)
    FINECO_DECISION_SUMMARY_FILE.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    try:
        with pd.ExcelWriter(FINECO_DECISION_COCKPIT_XLSX) as writer:
            live.to_excel(writer, sheet_name="Decision Cockpit", index=False)
            pd.DataFrame([summary]).to_excel(writer, sheet_name="Sintesi", index=False)
    except Exception:  # noqa: BLE001
        pass
    return live, summary


if __name__ == "__main__":
    save_decision_cockpit()
