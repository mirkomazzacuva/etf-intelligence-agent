from __future__ import annotations

import argparse
import importlib
import json
import py_compile
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd

REQUIRED_FILES = [
    "streamlit_app.py",
    "auto_update_app.py",
    "update_etf_data_v3.py",
    "allocation_engine.py",
    "generate_dashboard.py",
    "generate_watchlist.py",
    "generate_insights.py",
    "generate_decisions.py",
    "requirements.txt",
    ".github/workflows/etf_agent.yml",
    ".github/workflows/beta_test_app.yml",
    ".github/workflows/alpha_forge_patch_installer.yml",
    "data/portfolio_template.csv",
    "data/sector_universe.csv",
    "data/fineco_portfolio_template.csv",
    "data/fineco_portfolio_template_v8.csv",
    "generate_fineco_portfolio.py",
    "generate_fund_performance.py",
    "generate_news_radar.py",
    "data/fineco_funds_public.csv",
]

OUTPUT_FILES = [
    "ETF_Intelligence_Agent_UPDATED.xlsx",
    "ETF_Allocation_Model.xlsx",
    "ETF_Daily_Report.txt",
    "index.html",
    "AUTO_UPDATE_STATUS.json",
    "AlphaForge_Watchlist.csv",
    "AlphaForge_Watchlist.xlsx",
    "AlphaForge_Insights.csv",
    "AlphaForge_Insights.xlsx",
    "AlphaForge_Action_Plan.csv",
    "AlphaForge_Action_Plan.xlsx",
    "AlphaForge_Sector_Compass.csv",
    "AlphaForge_Sector_Compass.xlsx",
    "AlphaForge_Fineco_Portfolio.csv",
    "AlphaForge_Fineco_Portfolio.xlsx",
    "AlphaForge_Fineco_Portfolio_Summary.json",
    "AlphaForge_Fineco_Advisor_Questions.csv",
    "AlphaForge_Fineco_Advisor_Questions.xlsx",
    "AlphaForge_Fund_Performance.csv",
    "AlphaForge_Fund_Performance.xlsx",
    "AlphaForge_Fund_Price_History.csv",
    "AlphaForge_Fund_Price_History.xlsx",
    "AlphaForge_News_Radar.csv",
    "AlphaForge_News_Radar.xlsx",
    "AlphaForge_News_Radar_Summary.json",
]

CORE_MODULES = [
    "core.config",
    "core.data_provider",
    "core.metrics",
    "core.etf_scoring",
    "core.stock_scoring",
    "core.compare_engine",
    "core.watchlist_engine",
    "core.signal_engine",
    "core.insight_engine",
    "core.decision_engine",
    "core.portfolio_engine",
    "core.action_guide_engine",
    "core.report_engine",
    "core.ui_theme",
    "core.sector_compass_engine",
    "core.fineco_portfolio_tracker",
    "core.fund_market_engine",
    "core.news_radar_engine",
]


@dataclass
class Check:
    name: str
    status: str
    detail: str = ""


class BetaTester:
    def __init__(self, full_update: bool = False) -> None:
        self.full_update = full_update
        self.checks: list[Check] = []

    def add(self, name: str, status: str, detail: str = "") -> None:
        self.checks.append(Check(name, status, detail))
        print(f"{status:4} | {name} | {detail}")

    def ok(self, name: str, detail: str = "") -> None:
        self.add(name, "OK", detail)

    def warn(self, name: str, detail: str = "") -> None:
        self.add(name, "WARN", detail)

    def fail(self, name: str, detail: str = "") -> None:
        self.add(name, "FAIL", detail)

    def check_required_files(self) -> None:
        for item in REQUIRED_FILES:
            if Path(item).exists():
                self.ok("File presente", item)
            else:
                self.fail("File mancante", item)

    def check_python_syntax(self) -> None:
        for path in sorted(Path(".").glob("**/*.py")):
            if any(part.startswith(".") for part in path.parts) or "__pycache__" in path.parts:
                continue
            try:
                py_compile.compile(str(path), doraise=True)
                self.ok("Sintassi Python", str(path))
            except Exception as exc:  # noqa: BLE001
                self.fail("Sintassi Python", f"{path}: {exc}")

    def check_imports(self) -> None:
        for module in CORE_MODULES:
            try:
                importlib.import_module(module)
                self.ok("Import modulo core", module)
            except Exception as exc:  # noqa: BLE001
                self.fail("Import modulo core", f"{module}: {exc}")
        for module in ["pandas", "numpy", "yfinance", "openpyxl", "streamlit", "plotly"]:
            try:
                importlib.import_module(module)
                self.ok("Dipendenza", module)
            except Exception as exc:  # noqa: BLE001
                self.fail("Dipendenza", f"{module}: {exc}")

    def run_full_update_if_requested(self) -> None:
        if not self.full_update:
            self.ok("Test completo aggiornamento dati", "no")
            return
        start = time.time()
        completed = subprocess.run([sys.executable, "auto_update_app.py"], text=True, capture_output=True, check=False)
        Path("BETA_FULL_UPDATE.log").write_text((completed.stdout or "") + "\n" + (completed.stderr or ""), encoding="utf-8")
        if completed.returncode == 0:
            self.ok("Test completo aggiornamento", f"Completato in {time.time() - start:.2f} secondi")
        else:
            self.fail("Test completo aggiornamento", f"Exit {completed.returncode}. Vedi BETA_FULL_UPDATE.log")

    def check_outputs(self) -> None:
        for item in OUTPUT_FILES:
            if Path(item).exists():
                self.ok("Output presente", item)
            else:
                self.fail("Output mancante", item)

        if Path("ETF_Intelligence_Agent_UPDATED.xlsx").exists():
            try:
                df = pd.read_excel("ETF_Intelligence_Agent_UPDATED.xlsx")
                missing = [col for col in ["Ticker", "Score Finale", "Stato", "Note AI"] if col not in df.columns]
                if missing:
                    self.fail("Excel ranking", f"Mancano colonne: {', '.join(missing)}")
                else:
                    self.ok("Excel ranking", f"OK, {len(df)} righe")
            except Exception as exc:  # noqa: BLE001
                self.fail("Excel ranking", str(exc))

        if Path("ETF_Allocation_Model.xlsx").exists():
            try:
                alloc = pd.read_excel("ETF_Allocation_Model.xlsx", sheet_name="Suggested_Allocation")
                amount_cols = ["Importo su 1000 EUR", "Importo Indicativo EUR"]
                missing = [col for col in ["Ticker", "Peso Target %"] if col not in alloc.columns]
                if not any(col in alloc.columns for col in amount_cols):
                    missing.append("Importo su 1000 EUR")
                if missing:
                    self.fail("Excel allocazione", f"Mancano colonne: {', '.join(missing)}")
                else:
                    amount_col = next(col for col in amount_cols if col in alloc.columns)
                    self.ok("Excel allocazione", f"OK, {len(alloc)} righe. Colonna importo: {amount_col}")
            except Exception as exc:  # noqa: BLE001
                self.fail("Excel allocazione", str(exc))

        if Path("AlphaForge_Insights.csv").exists():
            try:
                insights = pd.read_csv("AlphaForge_Insights.csv")
                missing = [col for col in ["Ticker", "Priority Score", "Azione Suggerita", "Entry Zone", "Risk Flag"] if col not in insights.columns]
                if missing:
                    self.fail("Insights", f"Mancano colonne: {', '.join(missing)}")
                else:
                    self.ok("Insights", f"OK, {len(insights)} righe")
            except Exception as exc:  # noqa: BLE001
                self.fail("Insights", str(exc))

        if Path("AlphaForge_Action_Plan.csv").exists():
            try:
                actions = pd.read_csv("AlphaForge_Action_Plan.csv")
                missing = [col for col in ["Ticker", "Decisione chiara", "Cosa fare adesso", "Bucket operativo"] if col not in actions.columns]
                if missing:
                    self.fail("Action plan", f"Mancano colonne: {', '.join(missing)}")
                else:
                    self.ok("Action plan", f"OK, {len(actions)} righe")
            except Exception as exc:  # noqa: BLE001
                self.fail("Action plan", str(exc))

        if Path("data/portfolio_template.csv").exists():
            try:
                template = pd.read_csv("data/portfolio_template.csv")
                missing = [col for col in ["Ticker", "Quantità", "Prezzo Medio"] if col not in template.columns]
                if missing:
                    self.fail("Template portafoglio", f"Mancano colonne: {', '.join(missing)}")
                else:
                    self.ok("Template portafoglio", f"OK, {len(template)} righe")
            except Exception as exc:  # noqa: BLE001
                self.fail("Template portafoglio", str(exc))



        if Path("AlphaForge_Sector_Compass.csv").exists():
            try:
                sectors = pd.read_csv("AlphaForge_Sector_Compass.csv")
                missing = [col for col in ["Settore", "Bucket", "Cosa fare", "Sector Score", "ETF/Fondo candidato"] if col not in sectors.columns]
                if missing:
                    self.fail("Sector Compass", f"Mancano colonne: {', '.join(missing)}")
                else:
                    self.ok("Sector Compass", f"OK, {len(sectors)} settori")
            except Exception as exc:  # noqa: BLE001
                self.fail("Sector Compass", str(exc))

        if Path("data/fineco_portfolio_template.csv").exists():
            try:
                template = pd.read_csv("data/fineco_portfolio_template.csv")
                missing: list[str] = []
                if not any(col in template.columns for col in ["Ticker", "ISIN"]):
                    missing.append("Ticker o ISIN")
                for col in ["Nome Strumento", "Settore AlphaForge"]:
                    if col not in template.columns:
                        missing.append(col)
                if not any(col in template.columns for col in ["Valore EUR", "Valore Attuale EUR"]):
                    missing.append("Valore EUR o Valore Attuale EUR")
                if missing:
                    self.fail("Template Fineco", f"Mancano colonne: {', '.join(missing)}")
                else:
                    value_col = "Valore EUR" if "Valore EUR" in template.columns else "Valore Attuale EUR"
                    id_col = "Ticker" if "Ticker" in template.columns else "ISIN"
                    self.ok("Template Fineco", f"OK, {len(template)} righe. ID: {id_col}. Valore: {value_col}")
            except Exception as exc:  # noqa: BLE001
                self.fail("Template Fineco", str(exc))



        if Path("AlphaForge_Fineco_Portfolio.csv").exists():
            try:
                fineco = pd.read_csv("AlphaForge_Fineco_Portfolio.csv")
                missing = [col for col in ["ISIN", "Capitale versato stimato EUR", "Rendimento %", "Stato lettura"] if col not in fineco.columns]
                if missing:
                    self.fail("Fineco tracker", f"Mancano colonne: {', '.join(missing)}")
                else:
                    self.ok("Fineco tracker", f"OK, {len(fineco)} righe")
            except Exception as exc:  # noqa: BLE001
                self.fail("Fineco tracker", str(exc))

        if Path("AlphaForge_Fineco_Portfolio_Summary.json").exists():
            try:
                summary = json.loads(Path("AlphaForge_Fineco_Portfolio_Summary.json").read_text(encoding="utf-8"))
                if summary.get("version") == "AlphaForge v8 Fineco Portfolio Tracker":
                    self.ok("Fineco summary", str(summary.get("fase", "n/d")))
                else:
                    self.warn("Fineco summary", str(summary.get("version", "versione mancante")))
            except Exception as exc:  # noqa: BLE001
                self.fail("Fineco summary", str(exc))

        if Path("AlphaForge_Fund_Performance.csv").exists():
            try:
                perf = pd.read_csv("AlphaForge_Fund_Performance.csv")
                missing = [col for col in ["ISIN", "Nome Strumento", "Proxy Ticker", "Trend proxy", "Azione pratica"] if col not in perf.columns]
                if missing:
                    self.fail("Performance fondi", f"Mancano colonne: {', '.join(missing)}")
                else:
                    self.ok("Performance fondi", f"OK, {len(perf)} strumenti")
            except Exception as exc:  # noqa: BLE001
                self.fail("Performance fondi", str(exc))

        if Path("AlphaForge_News_Radar.csv").exists():
            try:
                news = pd.read_csv("AlphaForge_News_Radar.csv")
                missing = [col for col in ["ISIN", "Nome Strumento", "Titolo", "News Score", "Lettura"] if col not in news.columns]
                if missing:
                    self.fail("News radar", f"Mancano colonne: {', '.join(missing)}")
                else:
                    self.ok("News radar", f"OK, {len(news)} righe")
            except Exception as exc:  # noqa: BLE001
                self.fail("News radar", str(exc))

        if Path("AlphaForge_News_Radar_Summary.json").exists():
            try:
                news_summary = json.loads(Path("AlphaForge_News_Radar_Summary.json").read_text(encoding="utf-8"))
                if news_summary.get("version") == "AlphaForge v9 News Radar":
                    self.ok("News summary", "AlphaForge v9 News Radar")
                else:
                    self.warn("News summary", str(news_summary.get("version", "versione mancante")))
            except Exception as exc:  # noqa: BLE001
                self.fail("News summary", str(exc))

        if Path("AUTO_UPDATE_STATUS.json").exists():
            try:
                status = json.loads(Path("AUTO_UPDATE_STATUS.json").read_text(encoding="utf-8"))
                if status.get("status") == "success":
                    self.ok("Stato aggiornamento", "Successo")
                else:
                    self.warn("Stato aggiornamento", str(status.get("status")))
            except Exception as exc:  # noqa: BLE001
                self.fail("Stato aggiornamento", str(exc))

        if Path("index.html").exists():
            try:
                html = Path("index.html").read_text(encoding="utf-8", errors="ignore")
                if "AlphaForge v9" in html and "News & Performance Radar" in html:
                    self.ok("Dashboard pubblica v9", "AlphaForge v9 News & Performance Radar presente")
                elif "AlphaForge v8" in html or "AlphaForge v7" in html or "AlphaForge v6" in html or "AlphaForge v5" in html or "AlphaForge v4" in html:
                    self.warn("Dashboard pubblica v9", "index.html non ancora v9: esegui full update")
                else:
                    self.warn("Dashboard pubblica v9", "Marker v9 non trovato")
            except Exception as exc:  # noqa: BLE001
                self.fail("Dashboard pubblica", str(exc))

    def streamlit_smoke_test(self) -> None:
        if not Path("streamlit_app.py").exists():
            self.fail("Streamlit smoke test", "streamlit_app.py mancante")
            return
        cmd = [sys.executable, "-m", "streamlit", "run", "streamlit_app.py", "--server.headless", "true", "--server.port", "8501"]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        log_lines: list[str] = []
        try:
            time.sleep(8)
            if proc.poll() is None:
                self.ok("Streamlit smoke test", "Server avviato")
            else:
                self.fail("Streamlit smoke test", f"Exit {proc.returncode}")
        finally:
            proc.terminate()
            try:
                out, _ = proc.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                out, _ = proc.communicate()
            if out:
                log_lines.append(out)
            Path("streamlit_smoke.log").write_text("\n".join(log_lines), encoding="utf-8")

    def write_report(self) -> int:
        ok = sum(1 for c in self.checks if c.status == "OK")
        warn = sum(1 for c in self.checks if c.status == "WARN")
        fail = sum(1 for c in self.checks if c.status == "FAIL")
        lines = [
            "# AlphaForge v9 Beta Test Report",
            "",
            f"Check totali: {len(self.checks)}",
            f"OK: {ok}",
            f"Warning: {warn}",
            f"Errori bloccanti: {fail}",
            f"Test completo aggiornamento dati: {'sì' if self.full_update else 'no'}",
            "",
            "| Stato | Controllo | Dettaglio |",
            "|---|---|---|",
        ]
        for check in self.checks:
            lines.append(f"| {check.status} | {check.name} | {str(check.detail).replace('|', '/')} |")
        Path("BETA_TEST_REPORT.md").write_text("\n".join(lines), encoding="utf-8")
        Path("BETA_TEST_STATUS.json").write_text(json.dumps([asdict(c) for c in self.checks], indent=2, ensure_ascii=False), encoding="utf-8")
        print("\n".join(lines[:8]))
        return 1 if fail else 0

    def run(self) -> int:
        self.check_required_files()
        self.check_python_syntax()
        self.check_imports()
        self.run_full_update_if_requested()
        self.check_outputs()
        self.streamlit_smoke_test()
        return self.write_report()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--full-update", action="store_true")
    args = parser.parse_args()
    return BetaTester(full_update=args.full_update).run()


if __name__ == "__main__":
    raise SystemExit(main())
