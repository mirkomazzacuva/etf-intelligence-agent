from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from core.config import (
    FINECO_ACTUAL_VALUES_FILE,
    FINECO_DECISION_COCKPIT_CSV,
    FINECO_DECISION_COCKPIT_XLSX,
    FINECO_DECISION_SUMMARY_FILE,
    FINECO_FUND_PERFORMANCE_CSV,
    FINECO_FUND_PRICE_HISTORY_CSV,
    FINECO_FUNDS_PUBLIC_FILE,
    FINECO_NEWS_RADAR_SUMMARY,
    FINECO_PORTFOLIO_OUTPUT_CSV,
)

VERSION = "AlphaForge v10 Decision Cockpit"


def today_rome() -> date:
    try:
        return datetime.now(ZoneInfo("Europe/Rome")).date()
    except Exception:  # noqa: BLE001
        return date.today()


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        if pd.isna(value):
            return default
        if isinstance(value, str):
            text = value.replace("€", "").replace("EUR", "").replace("%", "").replace(" ", "").strip()
            if text == "":
                return default
            if "," in text and "." in text:
                if text.rfind(",") > text.rfind("."):
                    text = text.replace(".", "").replace(",", ".")
                else:
                    text = text.replace(",", "")
            elif "," in text:
                text = text.replace(",", ".")
            value = text
        return float(value)
    except Exception:  # noqa: BLE001
        return default


def _parse_date(value: Any, fallback: date | None = None) -> date:
    fallback = fallback or today_rome()
    try:
        parsed = pd.to_datetime(value, errors="coerce")
        if pd.isna(parsed):
            return fallback
        return parsed.date()
    except Exception:  # noqa: BLE001
        return fallback


def _read_csv(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(path) if path.exists() else pd.DataFrame()
    except Exception:  # noqa: BLE001
        return pd.DataFrame()


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except Exception:  # noqa: BLE001
        return {}


def _ensure_actual_values_template(funds: pd.DataFrame) -> None:
    FINECO_ACTUAL_VALUES_FILE.parent.mkdir(parents=True, exist_ok=True)
    if FINECO_ACTUAL_VALUES_FILE.exists() or funds.empty:
        return
    rows = []
    for _, row in funds.iterrows():
        initial = _as_float(row.get("Importo Iniziale EUR"))
        rows.append({
            "ISIN": row.get("ISIN", ""),
            "Nome Strumento": row.get("Nome Strumento", ""),
            "Capitale Versato Fineco EUR": initial,
            "Valore Attuale Fineco EUR": initial,
            "Data Valore Fineco": row.get("Data Inizio", ""),
            "Note": "Inserisci qui il controvalore reale da Fineco per un margine esatto",
        })
    pd.DataFrame(rows).to_csv(FINECO_ACTUAL_VALUES_FILE, index=False)


def _merge_sources() -> pd.DataFrame:
    funds = _read_csv(FINECO_FUNDS_PUBLIC_FILE)
    if funds.empty and FINECO_PORTFOLIO_OUTPUT_CSV.exists():
        pf = _read_csv(FINECO_PORTFOLIO_OUTPUT_CSV)
        if not pf.empty:
            funds = pd.DataFrame({
                "ISIN": pf.get("ISIN", ""),
                "Nome Strumento": pf.get("Nome Strumento", ""),
                "Tipo Versamento": pf.get("Tipo Versamento", ""),
                "Importo Iniziale EUR": pf.get("Importo Iniziale EUR", 0),
                "PAC Mensile EUR": pf.get("PAC Mensile EUR", 0),
                "Data Inizio": pf.get("Data Inizio", ""),
                "Costo Annuo %": pf.get("Costi Annui % Stimati", 0),
                "Bollo Una Tantum EUR": 6,
                "Categoria AlphaForge": pf.get("Settore AlphaForge", ""),
                "Ruolo": pf.get("Ruolo", ""),
                "Proxy Ticker": "",
                "Nota": pf.get("Note", ""),
            })
    if funds.empty:
        return funds

    _ensure_actual_values_template(funds)
    actual = _read_csv(FINECO_ACTUAL_VALUES_FILE)
    if not actual.empty and "ISIN" in actual.columns:
        funds = funds.merge(actual, on="ISIN", how="left", suffixes=("", " Actual"))
        if "Nome Strumento Actual" in funds.columns:
            funds["Nome Strumento"] = funds["Nome Strumento"].fillna(funds["Nome Strumento Actual"])
    return funds


def _history_for(history: pd.DataFrame, name: str) -> pd.DataFrame:
    if history.empty or "Nome Strumento" not in history.columns:
        return pd.DataFrame()
    out = history[history["Nome Strumento"].astype(str) == str(name)].copy()
    if out.empty:
        return out
    out["Date"] = pd.to_datetime(out.get("Date"), errors="coerce")
    out["Close"] = pd.to_numeric(out.get("Close"), errors="coerce")
    out = out.dropna(subset=["Date", "Close"]).sort_values("Date")
    return out


def _proxy_return_since_start(history: pd.DataFrame, name: str, start: date) -> float:
    h = _history_for(history, name)
    if h.empty:
        return 0.0
    after = h[h["Date"].dt.date >= start]
    if after.empty:
        after = h.tail(1)
    first = float(after["Close"].iloc[0])
    last = float(h["Close"].iloc[-1])
    if first == 0:
        return 0.0
    return (last / first - 1) * 100


def _latest_proxy_date(history: pd.DataFrame) -> str:
    if history.empty or "Date" not in history.columns:
        return "n/d"
    try:
        dates = pd.to_datetime(history["Date"], errors="coerce").dropna()
        if dates.empty:
            return "n/d"
        return dates.max().date().isoformat()
    except Exception:  # noqa: BLE001
        return "n/d"


def _estimate_annual_return(perf_row: pd.Series | None) -> float:
    if perf_row is None:
        return 4.0
    values = []
    for col, multiplier in [
        ("Rendimento proxy 1Y %", 1.0),
        ("Rendimento proxy 3M %", 4.0),
        ("Rendimento proxy 1M %", 12.0),
    ]:
        raw = _as_float(perf_row.get(col, np.nan), np.nan)
        if not pd.isna(raw) and abs(raw) < 300:
            values.append(raw * multiplier)
    if not values:
        return 4.0
    # Weighted and capped: projections should be prudent, not mechanical extrapolation.
    annual = values[0] if len(values) == 1 else (values[0] * 0.55 + values[-1] * 0.45)
    return max(-20.0, min(18.0, float(annual)))


def _future_value(current: float, monthly_pac: float, months: int, annual_return_pct: float) -> float:
    monthly_rate = (1 + annual_return_pct / 100) ** (1 / 12) - 1 if annual_return_pct > -99 else 0.0
    value = max(0.0, current)
    for _ in range(months):
        value *= 1 + monthly_rate
        if monthly_pac > 0:
            value += monthly_pac
    return value


def _decision_rule(days: int, role: str, name: str, cost: float, margin_pct: float, net_return_1y: float, news_bias: str) -> tuple[str, str, str]:
    low = f"{role} {name} {news_bias}".lower()
    if days < 30:
        if cost >= 3.0:
            return (
                "Tieni ora, ma sotto esame costi",
                "Troppo presto per chiudere: prima controlla NAV reale e confronto a 3-6 mesi.",
                "Valuta switch se tra 6-12 mesi rende meno del proxy dividend/global dopo costi.",
            )
        return (
            "Tieni / attendi dati reali",
            "Portafoglio appena partito: ora serve verificare esecuzione, quote e primo NAV.",
            "Valuta switch solo se a 6-12 mesi resta sotto benchmark o cambia il ruolo nel portafoglio.",
        )
    if cost >= 3.0 and net_return_1y < 4.0:
        return (
            "Valuta switch con consulente",
            "Costo elevato e proiezione netta non sufficiente: serve alternativa piu' efficiente.",
            "Chiedi confronto con ETF/fondo dividend globale a costo piu' basso.",
        )
    if margin_pct < -6 and "pressione" in low:
        return (
            "Non aumentare, verifica switch",
            "Perdita e news deboli: non incrementare prima di capire se e' correzione o problema strutturale.",
            "Valuta riduzione se resta sotto benchmark per 2-3 mesi consecutivi.",
        )
    if "pac" in low:
        return (
            "Continua PAC, non aumentare peso",
            "Il PAC riduce il rischio timing: mantieni size e controlla che non diventi troppo satellite.",
            "Rivedi se il settore entra in trend negativo prolungato o supera il peso massimo deciso.",
        )
    if net_return_1y >= 5.0 and margin_pct >= -3.0:
        return (
            "Tieni",
            "Dati e proiezione sono coerenti: monitoraggio ordinario vs benchmark.",
            "Switch solo se trovi alternativa piu' economica con stesso ruolo e rischio simile.",
        )
    return (
        "Tieni ma monitora",
        "Non emerge un motivo forte per vendere subito, ma va confrontato con benchmark e costi.",
        "Rivaluta a 3-6 mesi se rendimento netto resta sotto proxy/benchmark.",
    )


def _news_bias_map() -> dict[str, str]:
    summary = _read_json(FINECO_NEWS_RADAR_SUMMARY)
    out: dict[str, str] = {}
    for item in summary.get("funds", []) if isinstance(summary, dict) else []:
        out[str(item.get("ISIN", ""))] = str(item.get("Bias prossimi giorni", ""))
    return out


def build_decision_cockpit(as_of: date | None = None) -> tuple[pd.DataFrame, dict[str, Any]]:
    as_of = as_of or today_rome()
    funds = _merge_sources()
    perf = _read_csv(FINECO_FUND_PERFORMANCE_CSV)
    history = _read_csv(FINECO_FUND_PRICE_HISTORY_CSV)
    news_bias_by_isin = _news_bias_map()

    if funds.empty:
        empty = pd.DataFrame()
        return empty, {"version": VERSION, "data_analisi": as_of.isoformat(), "message": "Nessun fondo configurato"}

    perf_by_name = {}
    if not perf.empty and "Nome Strumento" in perf.columns:
        for _, row in perf.iterrows():
            perf_by_name[str(row.get("Nome Strumento", ""))] = row

    rows: list[dict[str, Any]] = []
    for _, fund in funds.iterrows():
        isin = str(fund.get("ISIN", ""))
        name = str(fund.get("Nome Strumento", ""))
        role = str(fund.get("Ruolo", ""))
        start = _parse_date(fund.get("Data Inizio"), as_of)
        days = max(0, (as_of - start).days)
        initial = _as_float(fund.get("Importo Iniziale EUR"))
        monthly_pac = _as_float(fund.get("PAC Mensile EUR"))
        annual_cost = _as_float(fund.get("Costo Annuo %"))
        stamp = _as_float(fund.get("Bollo Una Tantum EUR"), 6.0)
        actual_capital = _as_float(fund.get("Capitale Versato Fineco EUR"))
        actual_value = _as_float(fund.get("Valore Attuale Fineco EUR"))
        value_date = str(fund.get("Data Valore Fineco", "") or "")

        invested = actual_capital if actual_capital > 0 else initial
        proxy_since_start = _proxy_return_since_start(history, name, start)
        if actual_value > 0:
            current_value = actual_value
            value_source = "Fineco manuale"
        elif invested > 0:
            current_value = invested * (1 + proxy_since_start / 100)
            value_source = "Stimato da proxy"
        else:
            current_value = 0.0
            value_source = "PAC non ancora valorizzato"

        margin_eur = current_value - invested - (stamp if invested > 0 else 0.0)
        margin_pct = (margin_eur / invested * 100) if invested > 0 else 0.0
        accrued_cost_eur = invested * annual_cost / 100 * days / 365 if invested > 0 else 0.0

        perf_row = perf_by_name.get(name)
        annual_proxy = _estimate_annual_return(perf_row)
        # Proxy already has its own fees; subtract the product ongoing cost to keep the reading prudent.
        net_expected_1y = max(-25.0, min(16.0, annual_proxy - annual_cost))
        net_expected_3m = ((1 + net_expected_1y / 100) ** (3 / 12) - 1) * 100 if net_expected_1y > -99 else 0.0

        proj_3m = _future_value(current_value, monthly_pac, 3, net_expected_1y)
        proj_12m = _future_value(current_value, monthly_pac, 12, net_expected_1y)
        proj_3m_low = _future_value(current_value, monthly_pac, 3, net_expected_1y - 18)
        proj_3m_high = _future_value(current_value, monthly_pac, 3, net_expected_1y + 18)
        proj_12m_low = _future_value(current_value, monthly_pac, 12, net_expected_1y - 12)
        proj_12m_high = _future_value(current_value, monthly_pac, 12, net_expected_1y + 12)

        news_bias = news_bias_by_isin.get(isin, "Neutro / da monitorare")
        decision, reason, switch_condition = _decision_rule(days, role, name, annual_cost, margin_pct, net_expected_1y, news_bias)

        rows.append({
            "ISIN": isin,
            "Fondo/PAC": name,
            "Tipo": fund.get("Tipo Versamento", ""),
            "Ruolo": role,
            "Categoria": fund.get("Categoria AlphaForge", ""),
            "Capitale versato EUR": round(invested, 2),
            "Valore attuale EUR": round(current_value, 2),
            "Margine netto EUR": round(margin_eur, 2),
            "Margine netto %": round(margin_pct, 2),
            "Costo annuo %": round(annual_cost, 2),
            "Costo maturato stimato EUR": round(accrued_cost_eur, 2),
            "PAC mensile EUR": round(monthly_pac, 2),
            "Proiezione 3M base EUR": round(proj_3m, 2),
            "Range 3M prudente EUR": f"{proj_3m_low:,.0f} - {proj_3m_high:,.0f}".replace(",", "."),
            "Proiezione 1Y base EUR": round(proj_12m, 2),
            "Range 1Y prudente EUR": f"{proj_12m_low:,.0f} - {proj_12m_high:,.0f}".replace(",", "."),
            "Rendimento atteso netto 3M %": round(net_expected_3m, 2),
            "Rendimento atteso netto 1Y %": round(net_expected_1y, 2),
            "Proxy return da inizio %": round(proxy_since_start, 2),
            "News bias": news_bias,
            "Decisione pratica": decision,
            "Motivo": reason,
            "Quando valutare switch": switch_condition,
            "Fonte valore": value_source,
            "Data valore Fineco": value_date,
            "Giorni da inizio": days,
        })

    cockpit = pd.DataFrame(rows)
    total_invested = float(cockpit["Capitale versato EUR"].sum()) if not cockpit.empty else 0.0
    total_value = float(cockpit["Valore attuale EUR"].sum()) if not cockpit.empty else 0.0
    total_margin = float(cockpit["Margine netto EUR"].sum()) if not cockpit.empty else 0.0
    pac_monthly = float(cockpit["PAC mensile EUR"].sum()) if not cockpit.empty else 0.0
    projected_3m = float(cockpit["Proiezione 3M base EUR"].sum()) if not cockpit.empty else 0.0
    projected_1y = float(cockpit["Proiezione 1Y base EUR"].sum()) if not cockpit.empty else 0.0
    latest_proxy_date = _latest_proxy_date(history)
    summary = {
        "version": VERSION,
        "data_analisi": as_of.isoformat(),
        "latest_proxy_date": latest_proxy_date,
        "capitale_versato_eur": round(total_invested, 2),
        "valore_attuale_eur": round(total_value, 2),
        "margine_netto_eur": round(total_margin, 2),
        "margine_netto_pct": round(total_margin / total_invested * 100, 2) if total_invested > 0 else 0.0,
        "pac_mensile_eur": round(pac_monthly, 2),
        "proiezione_3m_base_eur": round(projected_3m, 2),
        "proiezione_1y_base_eur": round(projected_1y, 2),
        "decisione_sintesi": _summary_decision(cockpit),
        "messaggio": "Per i fondi comuni il NAV ufficiale non e' real-time. Il margine esatto richiede il controvalore Fineco aggiornato in data/fineco_actual_values.csv.",
    }
    return cockpit, summary


def _summary_decision(cockpit: pd.DataFrame) -> str:
    if cockpit.empty:
        return "Nessun dato"
    decisions = " | ".join(cockpit["Decisione pratica"].astype(str).tolist()).lower()
    max_days = int(pd.to_numeric(cockpit["Giorni da inizio"], errors="coerce").fillna(0).max())
    if max_days < 30:
        return "Tieni: portafoglio troppo recente, ora serve solo controllo dati e NAV"
    if "valuta switch" in decisions:
        return "Ci sono fondi da confrontare con alternative: porta la lista al consulente"
    if "non aumentare" in decisions:
        return "Mantieni ma non aumentare le parti deboli"
    return "Tieni e monitora: nessun segnale forte di cambio immediato"


def save_decision_cockpit() -> tuple[pd.DataFrame, dict[str, Any]]:
    cockpit, summary = build_decision_cockpit()
    cockpit.to_csv(FINECO_DECISION_COCKPIT_CSV, index=False)
    FINECO_DECISION_SUMMARY_FILE.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    try:
        with pd.ExcelWriter(FINECO_DECISION_COCKPIT_XLSX) as writer:
            cockpit.to_excel(writer, sheet_name="Decision Cockpit", index=False)
            pd.DataFrame([summary]).to_excel(writer, sheet_name="Sintesi", index=False)
    except Exception:  # noqa: BLE001
        pass
    return cockpit, summary
