from __future__ import annotations

import argparse
import importlib
import json
import os
import py_compile
import subprocess
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

APP_TZ = ZoneInfo("Europe/Rome")
ROOT = Path(__file__).resolve().parent
REPORT_FILE = ROOT / "BETA_TEST_REPORT.md"
STATUS_FILE = ROOT / "BETA_TEST_STATUS.json"

REQUIRED_SOURCE_FILES = [
    "streamlit_app.py",
    "auto_update_app.py",
    "update_etf_data_v3.py",
    "allocation_engine.py",
    "generate_dashboard.py",
    "requirements.txt",
    ".github/workflows/etf_agent.yml",
    ".github/workflows/beta_test_app.yml",
]

REQUIRED_DATA_FILES = [
    "ETF_Intelligence_Agent_Master_Populated.xlsx",
]

GENERATED_FILES = [
    "ETF_Intelligence_Agent_UPDATED.xlsx",
    "ETF_Allocation_Model.xlsx",
    "ETF_Daily_Report.txt",
    "index.html",
    "AUTO_UPDATE_STATUS.json",
]

IMPORT_CHECKS = {
    "pandas": "pandas",
    "numpy": "numpy",
    "yfinance": "yfinance",
    "openpyxl": "openpyxl",
    "streamlit": "streamlit",
    "plotly": "plotly",
}

EXPECTED_RANKING_COLUMNS = [
    "Ticker",
    "Nome ETF",
    "Categoria",
    "Tema/Area",
    "Score Finale",
]

EXPECTED_ALLOCATION_COLUMNS = [
    "Ticker",
    "Nome ETF",
    "Categoria",
    "Peso Target %",
    "Importo Indicativo EUR",
]


@dataclass
class CheckResult:
    name: str
    status: str
    message: str
    details: str = ""


def now_iso() -> str:
    return datetime.now(APP_TZ).isoformat(timespec="seconds")


def ok(name: str, message: str, details: str = "") -> CheckResult:
    return CheckResult(name=name, status="OK", message=message, details=details)


def warn(name: str, message: str, details: str = "") -> CheckResult:
    return CheckResult(name=name, status="WARN", message=message, details=details)


def fail(name: str, message: str, details: str = "") -> CheckResult:
    return CheckResult(name=name, status="FAIL", message=message, details=details)


def check_required_files() -> list[CheckResult]:
    results: list[CheckResult] = []
    for rel_path in REQUIRED_SOURCE_FILES:
        path = ROOT / rel_path
        if path.exists():
            results.append(ok(f"File sorgente: {rel_path}", "Presente"))
        else:
            results.append(fail(f"File sorgente: {rel_path}", "Manca un file necessario"))

    for rel_path in REQUIRED_DATA_FILES:
        path = ROOT / rel_path
        if path.exists():
            results.append(ok(f"File dati: {rel_path}", "Presente"))
        else:
            results.append(
                fail(
                    f"File dati: {rel_path}",
                    "Manca il file master necessario per rigenerare ranking e dashboard",
                    "Carica il file Excel master nel repository oppure correggi INPUT_FILE in update_etf_data_v3.py.",
                )
            )

    for rel_path in GENERATED_FILES:
        path = ROOT / rel_path
        if path.exists():
            size_kb = path.stat().st_size / 1024
            results.append(ok(f"Output generato: {rel_path}", f"Presente ({size_kb:.1f} KB)"))
        else:
            results.append(
                warn(
                    f"Output generato: {rel_path}",
                    "Non presente al momento del beta test rapido",
                    "Non e' bloccante se il workflow di aggiornamento deve ancora generarlo.",
                )
            )
    return results


def check_python_syntax() -> list[CheckResult]:
    results: list[CheckResult] = []
    py_files = [
        path
        for path in ROOT.rglob("*.py")
        if ".git" not in path.parts and "venv" not in path.parts and ".venv" not in path.parts
    ]
    if not py_files:
        return [fail("Sintassi Python", "Nessun file Python trovato")]

    for path in sorted(py_files):
        rel_path = path.relative_to(ROOT).as_posix()
        try:
            py_compile.compile(str(path), doraise=True)
            results.append(ok(f"Sintassi Python: {rel_path}", "Compilazione riuscita"))
        except py_compile.PyCompileError as exc:
            results.append(fail(f"Sintassi Python: {rel_path}", "Errore di sintassi", str(exc)))
    return results


def check_imports() -> list[CheckResult]:
    results: list[CheckResult] = []
    for label, module_name in IMPORT_CHECKS.items():
        try:
            module = importlib.import_module(module_name)
            version = getattr(module, "__version__", "versione non disponibile")
            results.append(ok(f"Dipendenza: {label}", f"Import OK ({version})"))
        except Exception as exc:  # noqa: BLE001
            results.append(fail(f"Dipendenza: {label}", "Import fallito", str(exc)))
    return results


def check_excel_outputs() -> list[CheckResult]:
    results: list[CheckResult] = []
    try:
        import pandas as pd
    except Exception as exc:  # noqa: BLE001
        return [fail("Controllo Excel", "Pandas non disponibile", str(exc))]

    ranking_path = ROOT / "ETF_Intelligence_Agent_UPDATED.xlsx"
    allocation_path = ROOT / "ETF_Allocation_Model.xlsx"

    if ranking_path.exists():
        try:
            ranking = pd.read_excel(ranking_path)
            missing = [col for col in EXPECTED_RANKING_COLUMNS if col not in ranking.columns]
            if missing:
                results.append(
                    fail(
                        "Excel ranking",
                        "File leggibile ma mancano colonne attese",
                        ", ".join(missing),
                    )
                )
            elif ranking.empty:
                results.append(fail("Excel ranking", "File leggibile ma tabella vuota"))
            else:
                results.append(ok("Excel ranking", f"Leggibile, {len(ranking)} righe"))
        except Exception as exc:  # noqa: BLE001
            results.append(fail("Excel ranking", "File non leggibile", str(exc)))
    else:
        results.append(warn("Excel ranking", "Non ancora presente"))

    if allocation_path.exists():
        try:
            allocation = pd.read_excel(allocation_path, sheet_name="Suggested_Allocation")
            summary = pd.read_excel(allocation_path, sheet_name="Summary")
            missing = [col for col in EXPECTED_ALLOCATION_COLUMNS if col not in allocation.columns]
            if missing:
                results.append(
                    fail(
                        "Excel allocazione",
                        "File leggibile ma mancano colonne attese",
                        ", ".join(missing),
                    )
                )
            elif allocation.empty:
                results.append(fail("Excel allocazione", "Sheet Suggested_Allocation vuoto"))
            elif summary.empty:
                results.append(fail("Excel allocazione", "Sheet Summary vuoto"))
            else:
                results.append(ok("Excel allocazione", f"Leggibile, {len(allocation)} righe"))
        except Exception as exc:  # noqa: BLE001
            results.append(fail("Excel allocazione", "File non leggibile", str(exc)))
    else:
        results.append(warn("Excel allocazione", "Non ancora presente"))

    return results


def check_status_file() -> list[CheckResult]:
    path = ROOT / "AUTO_UPDATE_STATUS.json"
    if not path.exists():
        return [warn("Stato aggiornamento", "AUTO_UPDATE_STATUS.json non ancora presente")]
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return [fail("Stato aggiornamento", "JSON non leggibile", str(exc))]

    status = payload.get("status")
    message = payload.get("message", "")
    if status == "success":
        return [ok("Stato aggiornamento", f"Successo: {message}")]
    if status in {"failed", "error"}:
        return [fail("Stato aggiornamento", f"Ultimo aggiornamento in errore: {message}")]
    return [warn("Stato aggiornamento", f"Stato non conclusivo: {status} - {message}")]


def run_command(command: list[str], timeout_seconds: int) -> tuple[int, float, str]:
    started = time.time()
    completed = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=timeout_seconds,
    )
    duration = round(time.time() - started, 2)
    output = ((completed.stdout or "") + "\n" + (completed.stderr or "")).strip()
    return completed.returncode, duration, output[-8000:]


def run_full_update_check() -> list[CheckResult]:
    results: list[CheckResult] = []
    script = ROOT / "auto_update_app.py"
    if not script.exists():
        return [fail("Test completo aggiornamento", "auto_update_app.py non trovato")]

    try:
        return_code, duration, output = run_command([sys.executable, str(script)], timeout_seconds=1200)
    except subprocess.TimeoutExpired as exc:
        return [fail("Test completo aggiornamento", "Timeout durante aggiornamento", str(exc))]

    if return_code == 0:
        results.append(ok("Test completo aggiornamento", f"Completato in {duration} secondi"))
    else:
        results.append(
            fail(
                "Test completo aggiornamento",
                f"Fallito con codice {return_code} dopo {duration} secondi",
                output,
            )
        )
    results.extend(check_required_files())
    results.extend(check_excel_outputs())
    results.extend(check_status_file())
    return results


def write_reports(results: list[CheckResult], full_update: bool) -> None:
    failures = [item for item in results if item.status == "FAIL"]
    warnings = [item for item in results if item.status == "WARN"]
    payload = {
        "generated_at": now_iso(),
        "full_update": full_update,
        "summary": {
            "total": len(results),
            "ok": len([item for item in results if item.status == "OK"]),
            "warnings": len(warnings),
            "failures": len(failures),
        },
        "results": [asdict(item) for item in results],
    }
    STATUS_FILE.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        "# Beta test ETF Intelligence App",
        "",
        f"Generato: {payload['generated_at']}",
        f"Test completo aggiornamento dati: {'si' if full_update else 'no'}",
        "",
        "## Sintesi",
        "",
        f"- Check totali: {payload['summary']['total']}",
        f"- OK: {payload['summary']['ok']}",
        f"- Warning: {payload['summary']['warnings']}",
        f"- Errori bloccanti: {payload['summary']['failures']}",
        "",
        "## Dettaglio controlli",
        "",
        "| Stato | Controllo | Messaggio | Dettagli |",
        "|---|---|---|---|",
    ]
    for item in results:
        details = item.details.replace("\n", "<br>").replace("|", "\\|") if item.details else ""
        lines.append(f"| {item.status} | {item.name} | {item.message} | {details} |")
    REPORT_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def print_summary(results: list[CheckResult]) -> None:
    failures = [item for item in results if item.status == "FAIL"]
    warnings = [item for item in results if item.status == "WARN"]
    print("\n=== BETA TEST ETF INTELLIGENCE APP ===")
    print(f"OK: {len([item for item in results if item.status == 'OK'])}")
    print(f"WARN: {len(warnings)}")
    print(f"FAIL: {len(failures)}")
    print(f"Report: {REPORT_FILE.name}")
    print(f"Status: {STATUS_FILE.name}")
    if failures:
        print("\nErrori bloccanti:")
        for item in failures:
            print(f"- {item.name}: {item.message}")
    if warnings:
        print("\nWarning:")
        for item in warnings[:10]:
            print(f"- {item.name}: {item.message}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Beta tester automatico per ETF Intelligence App")
    parser.add_argument(
        "--full-update",
        action="store_true",
        help="Esegue anche auto_update_app.py e controlla gli output generati.",
    )
    args = parser.parse_args()

    results: list[CheckResult] = []
    results.extend(check_required_files())
    results.extend(check_python_syntax())
    results.extend(check_imports())
    results.extend(check_excel_outputs())
    results.extend(check_status_file())

    if args.full_update:
        results.extend(run_full_update_check())

    write_reports(results, full_update=args.full_update)
    print_summary(results)
    return 1 if any(item.status == "FAIL" for item in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
