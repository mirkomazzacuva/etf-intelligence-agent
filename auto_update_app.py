from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from core.config import STATUS_FILE

DATA_SCRIPTS = [
    "update_etf_data_v3.py",
    "allocation_engine.py",
    "generate_watchlist.py",
    "generate_insights.py",
    "generate_decisions.py",
]

DASHBOARD_SCRIPT = "generate_dashboard.py"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def write_status(status: str, message: str, details: list[dict] | None = None, started_at: str | None = None) -> None:
    payload = {
        "status": status,
        "message": message,
        "started_at": started_at,
        "finished_at": now_iso() if status in {"success", "failed"} else None,
        "version": "AlphaForge v6 Action First",
        "details": details or [],
    }
    STATUS_FILE.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def run_script(script: str) -> dict:
    print(f"\n=== Running {script} ===")
    completed = subprocess.run([sys.executable, script], text=True, capture_output=True, check=False)
    print(completed.stdout)
    if completed.stderr:
        print(completed.stderr, file=sys.stderr)
    return {
        "script": script,
        "returncode": completed.returncode,
        "stdout_tail": (completed.stdout or "")[-2000:],
        "stderr_tail": (completed.stderr or "")[-2000:],
    }


def ensure_script_exists(script: str, details: list[dict], started_at: str) -> bool:
    if Path(script).exists():
        return True
    details.append({"script": script, "returncode": 1, "stderr_tail": "File script mancante"})
    write_status("failed", f"Script mancante: {script}", details, started_at=started_at)
    return False


def run_dashboard(details: list[dict], started_at: str) -> int:
    if not ensure_script_exists(DASHBOARD_SCRIPT, details, started_at):
        return 1
    dashboard_result = run_script(DASHBOARD_SCRIPT)
    details.append(dashboard_result)
    if dashboard_result["returncode"] != 0:
        write_status("failed", f"Aggiornamento fallito su {DASHBOARD_SCRIPT}", details, started_at=started_at)
        return int(dashboard_result["returncode"])
    return 0


def main() -> int:
    started_at = now_iso()
    details: list[dict] = []
    write_status("running", "Aggiornamento AlphaForge v6 in corso", details, started_at=started_at)

    for script in DATA_SCRIPTS:
        if not ensure_script_exists(script, details, started_at):
            return 1
        result = run_script(script)
        details.append(result)
        if result["returncode"] != 0:
            write_status("failed", f"Aggiornamento fallito su {script}", details, started_at=started_at)
            return int(result["returncode"])

    write_status("success", "Dati AlphaForge v6 aggiornati; dashboard in generazione", details, started_at=started_at)
    if run_dashboard(details, started_at) != 0:
        return 1

    write_status("success", "Aggiornamento AlphaForge v6 completato", details, started_at=started_at)
    if run_dashboard(details, started_at) != 0:
        return 1

    write_status("success", "Aggiornamento AlphaForge v6 completato", details, started_at=started_at)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
