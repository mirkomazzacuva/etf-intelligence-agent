from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from core.config import (
    FINECO_ADVISOR_QUESTIONS_CSV,
    FINECO_ADVISOR_QUESTIONS_XLSX,
    FINECO_BASELINE_FILE,
    FINECO_PORTFOLIO_OUTPUT_CSV,
    FINECO_PORTFOLIO_OUTPUT_XLSX,
    FINECO_PORTFOLIO_SUMMARY_FILE,
    FINECO_TEMPLATE_V8_FILE,
)

REQUIRED_COLUMNS = [
    "ISIN",
    "Nome Strumento",
    "Tipo",
    "Ruolo",
    "Settore AlphaForge",
    "Tipo Versamento",
    "Data Inizio",
    "Importo Iniziale EUR",
    "PAC Mensile EUR",
    "Capitale Versato Manuale EUR",
    "Valore Attuale EUR",
    "Quote",
    "Prezzo Medio",
    "Costi Annui % Stimati",
    "Benchmark/Confronto",
    "Prima Rata PAC Conteggiata",
    "Note",
]

FALLBACK_ROWS = [
    {
        "ISIN": "ESEMPIO_CORE",
        "Nome Strumento": "Esempio fondo/ETF core globale",
        "Tipo": "ETF/Fondo",
        "Ruolo": "Core globale",
        "Settore AlphaForge": "Core Globale",
        "Tipo Versamento": "Una tantum",
        "Data Inizio": "2026-08-31",
        "Importo Iniziale EUR": 5000,
        "PAC Mensile EUR": 0,
        "Capitale Versato Manuale EUR": 0,
        "Valore Attuale EUR": 5000,
        "Quote": "",
        "Prezzo Medio": "",
        "Costi Annui % Stimati": "",
        "Benchmark/Confronto": "FTSE All-World / MSCI ACWI",
        "Prima Rata PAC Conteggiata": "No",
        "Note": "Riga di esempio. Sostituire con dati reali solo in app o in repo privato.",
    },
    {
        "ISIN": "ESEMPIO_PAC",
        "Nome Strumento": "Esempio PAC settoriale",
        "Tipo": "Fondo/PAC",
        "Ruolo": "Satellite",
        "Settore AlphaForge": "Tecnologia e AI",
        "Tipo Versamento": "PAC",
        "Data Inizio": "2026-08-31",
        "Importo Iniziale EUR": 0,
        "PAC Mensile EUR": 150,
        "Capitale Versato Manuale EUR": 0,
        "Valore Attuale EUR": 0,
        "Quote": "",
        "Prezzo Medio": "",
        "Costi Annui % Stimati": "",
        "Benchmark/Confronto": "ETF/fondo settoriale coerente",
        "Prima Rata PAC Conteggiata": "No",
        "Note": "Riga di esempio per PAC. Non pubblicare dati personali in repo pubblico.",
    },
]


def today_rome() -> date:
    try:
        return datetime.now(ZoneInfo("Europe/Rome")).date()
    except Exception:  # noqa: BLE001
        return date.today()


def _as_float(value: object, default: float = 0.0) -> float:
    """Convert common Italian/European money strings and numeric values to float.

    Handles values such as 5000, 5000.0, 5.000,00, 5,000.00,
    "5.000 EUR", empty cells and NaN.
    """
    try:
        if pd.isna(value):
            return default
        if isinstance(value, str):
            text = (
                value.replace("€", "")
                .replace("EUR", "")
                .replace("%", "")
                .replace(" ", "")
                .strip()
            )
            if text == "":
                return default
            if "," in text and "." in text:
                # If comma is the decimal separator, dots are thousands separators.
                if text.rfind(",") > text.rfind("."):
                    text = text.replace(".", "").replace(",", ".")
                else:
                    text = text.replace(",", "")
            elif "," in text:
                text = text.replace(",", ".")
            # If only dot is present, keep it as decimal separator.
            value = text
        return float(value)
    except Exception:  # noqa: BLE001
        return default

def _parse_date(value: object, fallback: date | None = None) -> date:
    fallback = fallback or today_rome()
    try:
        parsed = pd.to_datetime(value, dayfirst=False, errors="coerce")
        if pd.isna(parsed):
            return fallback
        return parsed.date()
    except Exception:  # noqa: BLE001
        return fallback


def _months_between(start: date, end: date) -> int:
    if end < start:
        return 0
    months = (end.year - start.year) * 12 + (end.month - start.month)
    if end.day < start.day:
        months -= 1
    return max(0, months)



def _coalesce_duplicate_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Coalesce duplicate columns created by legacy aliases.

    Example: a user template may contain both ISIN and Ticker. Since legacy
    code maps Ticker -> ISIN, pandas would create duplicate ISIN columns; then
    df["ISIN"] returns a DataFrame and .str operations fail. This function
    keeps one column per name, taking the first non-empty value row by row.
    """
    if not df.columns.duplicated().any():
        return df

    result = pd.DataFrame(index=df.index)
    for col in dict.fromkeys(df.columns):
        subset = df.loc[:, df.columns == col]
        if isinstance(subset, pd.Series):
            result[col] = subset
            continue
        if subset.shape[1] == 1:
            result[col] = subset.iloc[:, 0]
            continue

        clean = subset.copy()
        clean = clean.replace(r"^\s*$", pd.NA, regex=True)
        result[col] = clean.bfill(axis=1).iloc[:, 0]
    return result

def normalize_portfolio(df: pd.DataFrame) -> pd.DataFrame:
    mapping = {
        "isin": "ISIN",
        "ticker": "ISIN",
        "nome": "Nome Strumento",
        "strumento": "Nome Strumento",
        "nome strumento": "Nome Strumento",
        "tipo": "Tipo",
        "ruolo": "Ruolo",
        "categoria": "Ruolo",
        "settore": "Settore AlphaForge",
        "settore alphaforge": "Settore AlphaForge",
        "tipo versamento": "Tipo Versamento",
        "data inizio": "Data Inizio",
        "data acquisto": "Data Inizio",
        "importo iniziale": "Importo Iniziale EUR",
        "importo iniziale eur": "Importo Iniziale EUR",
        "capitale iniziale": "Importo Iniziale EUR",
        "pac mensile": "PAC Mensile EUR",
        "pac mensile eur": "PAC Mensile EUR",
        "capitale versato manuale": "Capitale Versato Manuale EUR",
        "capitale versato manuale eur": "Capitale Versato Manuale EUR",
        "valore attuale": "Valore Attuale EUR",
        "valore attuale eur": "Valore Attuale EUR",
        "valore eur": "Valore Attuale EUR",
        "valore": "Valore Attuale EUR",
        "controvalore": "Valore Attuale EUR",
        "quote": "Quote",
        "quantita": "Quote",
        "quantità": "Quote",
        "prezzo medio": "Prezzo Medio",
        "pmc": "Prezzo Medio",
        "costi annui": "Costi Annui % Stimati",
        "costi annui % stimati": "Costi Annui % Stimati",
        "benchmark": "Benchmark/Confronto",
        "benchmark/confronto": "Benchmark/Confronto",
        "prima rata pac conteggiata": "Prima Rata PAC Conteggiata",
        "note": "Note",
    }
    out = df.copy()
    out = out.rename(columns={col: mapping.get(str(col).lower().strip(), col) for col in out.columns})
    out = _coalesce_duplicate_columns(out)
    for col in REQUIRED_COLUMNS:
        if col not in out.columns:
            out[col] = ""
    numeric_cols = [
        "Importo Iniziale EUR",
        "PAC Mensile EUR",
        "Capitale Versato Manuale EUR",
        "Valore Attuale EUR",
        "Quote",
        "Prezzo Medio",
        "Costi Annui % Stimati",
    ]
    for col in numeric_cols:
        out[col] = out[col].apply(_as_float)
    for col in ["ISIN", "Nome Strumento", "Tipo", "Ruolo", "Settore AlphaForge", "Tipo Versamento", "Data Inizio", "Benchmark/Confronto", "Prima Rata PAC Conteggiata", "Note"]:
        out[col] = out[col].fillna("").astype(str).str.strip()
    return out[REQUIRED_COLUMNS]


def default_baseline() -> pd.DataFrame:
    return normalize_portfolio(pd.DataFrame(FALLBACK_ROWS))


def load_fineco_portfolio(path: Path | None = None) -> pd.DataFrame:
    source = path or FINECO_BASELINE_FILE
    if source.exists():
        if source.suffix.lower() in {".xlsx", ".xls"}:
            return normalize_portfolio(pd.read_excel(source))
        return normalize_portfolio(pd.read_csv(source))
    if FINECO_TEMPLATE_V8_FILE.exists():
        return normalize_portfolio(pd.read_csv(FINECO_TEMPLATE_V8_FILE))
    return default_baseline()


def analyse_fineco_portfolio(portfolio: pd.DataFrame, as_of: date | None = None) -> tuple[pd.DataFrame, dict[str, Any], pd.DataFrame]:
    as_of = as_of or today_rome()
    df = normalize_portfolio(portfolio)
    rows: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        start = _parse_date(row.get("Data Inizio"), as_of)
        pac = _as_float(row.get("PAC Mensile EUR"))
        initial = _as_float(row.get("Importo Iniziale EUR"))
        manual = _as_float(row.get("Capitale Versato Manuale EUR"))
        first_pac = str(row.get("Prima Rata PAC Conteggiata", "")).lower() in {"si", "sì", "yes", "true", "1"}
        months = _months_between(start, as_of)
        pac_installments = months + (1 if first_pac and pac > 0 else 0)
        pac_paid = pac * pac_installments
        invested = initial + manual + pac_paid
        current_value = _as_float(row.get("Valore Attuale EUR"))
        if current_value <= 0 and invested > 0:
            current_value = invested
        pl_eur = current_value - invested
        pl_pct = (pl_eur / invested * 100) if invested > 0 else 0.0
        days = max(0, (as_of - start).days)
        if invested > 0 and days >= 30 and current_value > 0:
            annualized = ((current_value / invested) ** (365 / max(days, 1)) - 1) * 100
        else:
            annualized = np.nan
        status = _status_comment(days, invested, pl_pct, row)
        rows.append({
            **row.to_dict(),
            "Data Analisi": as_of.isoformat(),
            "Giorni da inizio": days,
            "Rate PAC conteggiate": int(pac_installments),
            "PAC versato stimato EUR": round(pac_paid, 2),
            "Capitale versato stimato EUR": round(invested, 2),
            "Valore attuale stimato EUR": round(current_value, 2),
            "Guadagno/Perdita EUR": round(pl_eur, 2),
            "Rendimento %": round(pl_pct, 2),
            "Rendimento annualizzato %": round(float(annualized), 2) if not pd.isna(annualized) else "n/d",
            "Stato lettura": status,
            "Domanda consulente": _advisor_question(row),
        })
    out = pd.DataFrame(rows)
    total_invested = float(out["Capitale versato stimato EUR"].sum()) if not out.empty else 0.0
    total_value = float(out["Valore attuale stimato EUR"].sum()) if not out.empty else 0.0
    out["Peso attuale %"] = np.where(total_value > 0, out["Valore attuale stimato EUR"] / total_value * 100, 0)
    total_pl = total_value - total_invested
    total_pct = (total_pl / total_invested * 100) if total_invested > 0 else 0.0
    monthly_pac = float(out["PAC Mensile EUR"].sum()) if not out.empty else 0.0
    one_off = float(out["Importo Iniziale EUR"].sum()) if not out.empty else 0.0
    core_weight = float(out.loc[out["Ruolo"].astype(str).str.contains("core", case=False, na=False), "Peso attuale %"].sum()) if not out.empty else 0.0
    satellite_weight = max(0.0, 100.0 - core_weight) if total_value > 0 else 0.0
    stage = "Punto zero" if out["Giorni da inizio"].max() < 30 else ("Prima verifica" if out["Giorni da inizio"].max() < 180 else "Monitoraggio")
    health = _portfolio_health_score(out, core_weight, satellite_weight, total_value)
    summary = {
        "version": "AlphaForge v8 Fineco Portfolio Tracker",
        "data_analisi": as_of.isoformat(),
        "fase": stage,
        "numero_strumenti": int(len(out)),
        "capitale_una_tantum_eur": round(one_off, 2),
        "pac_mensile_eur": round(monthly_pac, 2),
        "capitale_versato_stimato_eur": round(total_invested, 2),
        "valore_attuale_stimato_eur": round(total_value, 2),
        "guadagno_perdita_eur": round(total_pl, 2),
        "rendimento_pct": round(total_pct, 2),
        "peso_core_pct": round(core_weight, 2),
        "peso_satellite_pct": round(satellite_weight, 2),
        "portfolio_health_score": round(health, 1),
        "messaggio_principale": _main_message(stage, total_invested, monthly_pac),
    }
    questions = build_advisor_questions(out, summary)
    return out, summary, questions


def _status_comment(days: int, invested: float, pl_pct: float, row: pd.Series) -> str:
    if invested <= 0 and _as_float(row.get("PAC Mensile EUR")) > 0:
        return "PAC impostato: attendere prima rata o confermare se gia' addebitata."
    if days < 30:
        return "Punto zero: non valutare ancora il rendimento, verifica solo corretta esecuzione."
    if abs(pl_pct) < 2:
        return "Movimento contenuto: monitoraggio ordinario."
    if pl_pct > 2:
        return "In guadagno: confrontare con benchmark e non aumentare solo per performance recente."
    return "In perdita: verificare se e' normale volatilita' o problema di strumento/costi."


def _advisor_question(row: pd.Series) -> str:
    isin = str(row.get("ISIN", "")).strip()
    role = str(row.get("Ruolo", "")).lower()
    if "passive underlyings" in str(row.get("Nome Strumento", "")).lower():
        return f"Per {isin}: quali sottostanti, costi totali e sovrapposizione con All-World/MSCI World?"
    if "pac" in str(row.get("Tipo Versamento", "")).lower():
        return f"Per {isin}: quando parte la prima rata PAC e quale benchmark useriamo per valutarlo?"
    if "satellite" in role:
        return f"Per {isin}: quale peso massimo satellite e cosa deve succedere per aumentare/ridurre?"
    return f"Per {isin}: qual e' il ruolo nel portafoglio e con quale ETF/fondo lo confrontiamo?"


def _portfolio_health_score(out: pd.DataFrame, core_weight: float, satellite_weight: float, total_value: float) -> float:
    if out.empty or total_value <= 0:
        return 50.0
    score = 75.0
    if core_weight < 45:
        score -= 12
    if satellite_weight > 45:
        score -= 10
    max_weight = float(out["Peso attuale %"].max()) if "Peso attuale %" in out.columns else 0
    if max_weight > 35:
        score -= 10
    unclassified = out["Settore AlphaForge"].astype(str).str.contains("classificare", case=False, regex=True, na=False).sum()
    if unclassified > 0:
        score -= min(10, int(unclassified) * 2)
    # At inception a neutral score is more honest than pretending precision.
    if out["Giorni da inizio"].max() < 30:
        score = min(score, 72.0)
    return max(0.0, min(100.0, score))


def _main_message(stage: str, total_invested: float, monthly_pac: float) -> str:
    if stage == "Punto zero":
        return f"Portafoglio appena avviato: registra baseline, verifica costi/KID e non valutare ancora la performance. PAC programmato: {monthly_pac:.0f} EUR/mese."
    return "Confronta rendimento, pesi e benchmark; porta al consulente solo le anomalie importanti."


def build_advisor_questions(out: pd.DataFrame, summary: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    rows.append({"Priorita": 1, "Tema": "Punto zero", "Domanda": "Confermi che tutti gli ordini/PAC sono effettivamente eseguiti e da quale data decorrono?", "Perche": "Serve per calcolare correttamente rendimento e capitale versato."})
    rows.append({"Priorita": 2, "Tema": "Costi totali", "Domanda": "Qual e' il costo annuo totale dei fondi, inclusi eventuali costi dei sottostanti?", "Perche": "I costi incidono sul rendimento netto nel lungo periodo."})
    rows.append({"Priorita": 3, "Tema": "Sovrapposizione", "Domanda": "Quanto questi fondi duplicano Vanguard All-World, MSCI World, S&P 500 o tecnologia USA?", "Perche": "Evita di aggiungere strumenti che sembrano diversi ma contengono gli stessi mercati."})
    rows.append({"Priorita": 4, "Tema": "Ruolo", "Domanda": "Qual e' il ruolo di ogni fondo: core, difensivo, satellite geografico o satellite tematico?", "Perche": "Ogni posizione deve avere un motivo chiaro."})
    rows.append({"Priorita": 5, "Tema": "Benchmark", "Domanda": "Quale benchmark useriamo per giudicare ciascun prodotto tra 6/12 mesi?", "Perche": "Il rendimento va confrontato con alternative coerenti."})
    if summary.get("pac_mensile_eur", 0) > 0:
        rows.append({"Priorita": 6, "Tema": "PAC", "Domanda": "I due PAC sono sui settori giusti o aumentano troppo emergenti/tecnologia?", "Perche": "Il PAC crea esposizione crescente mese dopo mese."})
    if not out.empty:
        for _, row in out.head(10).iterrows():
            rows.append({"Priorita": len(rows) + 1, "Tema": str(row.get("ISIN", "")), "Domanda": str(row.get("Domanda consulente", "")), "Perche": "Domanda specifica sul singolo strumento."})
    return pd.DataFrame(rows)


def save_fineco_outputs(positions: pd.DataFrame, summary: dict[str, Any], questions: pd.DataFrame) -> None:
    positions.to_csv(FINECO_PORTFOLIO_OUTPUT_CSV, index=False)
    questions.to_csv(FINECO_ADVISOR_QUESTIONS_CSV, index=False)
    FINECO_PORTFOLIO_SUMMARY_FILE.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    try:
        with pd.ExcelWriter(FINECO_PORTFOLIO_OUTPUT_XLSX) as writer:
            positions.to_excel(writer, sheet_name="Posizioni", index=False)
            pd.DataFrame([summary]).to_excel(writer, sheet_name="Sintesi", index=False)
            questions.to_excel(writer, sheet_name="Domande Consulente", index=False)
        questions.to_excel(FINECO_ADVISOR_QUESTIONS_XLSX, index=False)
    except Exception:  # noqa: BLE001
        pass


def ensure_template_files() -> None:
    FINECO_TEMPLATE_V8_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not FINECO_TEMPLATE_V8_FILE.exists():
        default_baseline().to_csv(FINECO_TEMPLATE_V8_FILE, index=False)
