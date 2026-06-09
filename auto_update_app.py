from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from core.config import STATUS_FILE

SCRIPTS = [
    "update_etf_data_v3.py",
    "allocation_engine.py",
    "generate_watchlist.py",
    "generate_dashboard.py",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def write_status(status: str, message: str, details: list[dict] | None = None) -> None:
    payload = {
        "status": status,
        "message": message,
        "finished_at": now_iso() if status in {"success", "failed"} else None,
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


def main() -> int:
    write_status("running", "Aggiornamento AlphaForge in corso")
    details: list[dict] = []
    for script in SCRIPTS:
        if not Path(script).exists():
            details.append({"script": script, "returncode": 1, "stderr_tail": "File script mancante"})
            write_status("failed", f"Script mancante: {script}", details)
            return 1
        result = run_script(script)
        details.append(result)
        if result["returncode"] != 0:
            write_status("failed", f"Aggiornamento fallito su {script}", details)
            return int(result["returncode"])
    write_status("success", "Aggiornamento AlphaForge completato", details)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
