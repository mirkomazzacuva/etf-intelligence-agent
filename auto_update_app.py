from __future__ import annotations

import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

APP_TZ = ZoneInfo("Europe/Rome")
ROOT = Path(__file__).resolve().parent
LOG_DIR = ROOT / "logs"
STATUS_FILE = ROOT / "AUTO_UPDATE_STATUS.json"
LOG_FILE = LOG_DIR / "update_log.jsonl"

COMMANDS = [
    [sys.executable, "update_etf_data_v3.py"],
    [sys.executable, "allocation_engine.py"],
    [sys.executable, "generate_dashboard.py"],
]

OUTPUT_FILES = [
    "ETF_Intelligence_Agent_UPDATED.xlsx",
    "ETF_Allocation_Model.xlsx",
    "ETF_Daily_Report.txt",
    "index.html",
    "AUTO_UPDATE_STATUS.json",
]


def now_iso() -> str:
    return datetime.now(APP_TZ).isoformat(timespec="seconds")


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def append_log(payload: dict) -> None:
    LOG_DIR.mkdir(exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def run_command(command: list[str]) -> dict:
    started = time.time()
    completed = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    return {
        "command": " ".join(command),
        "return_code": completed.returncode,
        "duration_seconds": round(time.time() - started, 2),
        "stdout_tail": completed.stdout[-4000:],
        "stderr_tail": completed.stderr[-4000:],
        "ok": completed.returncode == 0,
    }


def main() -> int:
    LOG_DIR.mkdir(exist_ok=True)
    started_at = now_iso()
    status = {
        "status": "running",
        "started_at": started_at,
        "finished_at": None,
        "duration_seconds": None,
        "message": "Aggiornamento in corso",
        "steps": [],
        "output_files": OUTPUT_FILES,
    }
    write_json(STATUS_FILE, status)

    start_time = time.time()
    ok = True

    for command in COMMANDS:
        step = run_command(command)
        status["steps"].append(step)
        append_log({"timestamp": now_iso(), "step": step})
        write_json(STATUS_FILE, status)
        if not step["ok"]:
            ok = False
            break

    status["status"] = "success" if ok else "failed"
    status["finished_at"] = now_iso()
    status["duration_seconds"] = round(time.time() - start_time, 2)
    status["message"] = (
        "Aggiornamento completato correttamente"
        if ok
        else "Aggiornamento non completato: controllare il log"
    )
    write_json(STATUS_FILE, status)
    append_log({"timestamp": now_iso(), "summary": status})
    print(json.dumps(status, indent=2, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
