from __future__ import annotations

import calendar
import json
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from core.config import (
    FINECO_ACTUAL_VALUES_FILE,
    FINECO_FUNDS_PUBLIC_FILE,
    FINECO_LIVE_PORTFOLIO_CSV,
    FINECO_LIVE_PRICE_HISTORY_CSV,
    FINECO_LIVE_SUMMARY_FILE,
)
from core.fund_market_engine import _fetch_proxy_history, _ticker_candidates, load_fund_universe

VERSION = "AlphaForge v11 Live Value Cockpit"
ROME_TZ = ZoneInfo("Europe/Rome")


@dataclass
class Cashflow:
    cashflow_date: date
    amount: float
    kind: str


def today_rome() -> date:
    try:
        return datetime.now(ROME_TZ).date()
    except Exception:  # noqa: BLE001
        return date.today()


def now_rome_iso() -> str:
    try:
        return datetime.now(ROME_TZ).isoformat(timespec="seconds")
    except Exception:  # noqa: BLE001
        return datetime.now(timezone.utc).isoformat(timespec="seconds")


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


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _last_day(year: int, month: int) -> int:
    return calendar.monthrange(year, month)[1]


def _add_months(start: date, months: int) -> date:
    month_index = start.month - 1 + months
    year = start.year + month_index // 12
    month = month_index % 12 + 1
    day = min(start.day, _last_day(year, month))
    return date(year, month, day)


def _pac_installment_count(start: date, as_of: date) -> int:
    if as_of < start:
        return 0
    months = (as_of.year - start.year) * 12 + (as_of.month - start.month)
    scheduled_this_month = _add_months(start, months)
    if as_of >= scheduled_this_month:
        return months + 1
    return max(1, months)


def _build_cashflows(initial: float, pac_monthly: float, start: date, as_of: date) -> list[Cashflow]:
    flows: list[Cashflow] = []
    if initial > 0 and as_of >= start:
        flows.append(Cashflow(start, initial, "Una tantum"))
    if pac_monthly > 0:
        count = _pac_installment_count(start, as_of)
        for i in range(count):
            flow_date = _add_months(start, i)
            if flow_date <= as_of:
                flows.append(Cashflow(flow_date, pac_monthly, "PAC"))
    return flows


def _history_prepare(hist: pd.DataFrame) -> pd.DataFrame:
    if hist.empty:
        return pd.DataFrame()
    out = hist.copy()
    out["Date"] = pd.to_datetime(out.get("Date"), errors="coerce")
    out["Close"] = pd.to_numeric(out.get("Close"), errors="coerce")
    out = out.dropna(subset=["Date", "Close"]).sort_values("Date")
    return out


def _close_on_or_after(hist: pd.DataFrame, flow_date: date) -> float | None:
    if hist.empty:
        return None
    dates = hist[hist["Date"].dt.date >= flow_date]
    if dates.empty:
        dates = hist.tail(1)
    try:
        value = float(dates["Close"].iloc[0])
        return value if value > 0 else None
    except Exception:  # noqa: BLE001
        return None


def _cashflows_value_from_proxy(hist: pd.DataFrame, flows: list[Cashflow]) -> float:
    if hist.empty or not flows:
        return sum(x.amount for x in flows)
    latest = float(hist["Close"].iloc[-1])
    total = 0.0
    for flow in flows:
        entry = _close_on_or_after(hist, flow.cashflow_date)
        if not entry:
            total += flow.amount
        else:
            total += flow.amount * latest / entry
    return total


def _cashflows_accrued_cost(flows: list[Cashflow], annual_cost_pct: float, as_of: date) -> float:
    total = 0.0
    for flow in flows:
        days = max(0, (as_of - flow.cashflow_date).days)
        total += flow.amount * annual_cost_pct / 100 * days / 365
    return total


def _manual_actual_is_active(row: pd.Series, start: date, invested_auto: float) -> bool:
    actual_value = _as_float(row.get("Valore Attuale Fineco EUR"), 0.0)
    actual_capital = _as_float(row.get("Capitale Versato Fineco EUR"), 0.0)
    if actual_value <= 0:
        return False
    explicit = str(row.get("Usa Valore Fineco", "")).strip().lower()
    if explicit in {"si", "sì", "yes", "true", "1", "x"}:
        return True
    note = str(row.get("Note", "")).lower()
    if any(token in note for token in ["sostituisci", "placeholder", "quando parte", "inserisci qui"]):
        return False
    value_date = _parse_date(row.get("Data Valore Fineco"), start)
    if value_date > start:
        return True
    if actual_capital > 0 and abs(actual_value - actual_capital) > 0.01:
        return True
    if invested_auto > 0 and abs(actual_value - invested_auto) > 0.01:
        return True
    return False


def _merge_manual_values(funds: pd.DataFrame) -> pd.DataFrame:
    actual = _read_csv(FINECO_ACTUAL_VALUES_FILE)
    if actual.empty or "ISIN" not in actual.columns:
        return funds
    actual = actual.copy()
    actual["ISIN"] = actual["ISIN"].fillna("").astype(str).str.strip()
    funds = funds.merge(actual, on="ISIN", how="left", suffixes=("", " Manuale"))
    return funds


def _return_from_hist(hist: pd.DataFrame, n: int) -> float | None:
    if hist.empty or len(hist) <= n:
        return None
    latest = float(hist["Close"].iloc[-1])
    prev = float(hist["Close"].iloc[-n])
    if prev == 0:
        return None
    return (latest / prev - 1) * 100


def _annual_expectation(hist: pd.DataFrame, annual_cost_pct: float) -> tuple[float, float, float, str]:
    if hist.empty:
        gross = 4.0
        trend = "Dato proxy non disponibile"
    else:
        r1m = _return_from_hist(hist, 21)
        r3m = _return_from_hist(hist, 63)
        r1y = None
        if len(hist) > 2:
            first = float(hist["Close"].iloc[0])
            latest = float(hist["Close"].iloc[-1])
            r1y = (latest / first - 1) * 100 if first else None
        estimates = []
        if r1y is not None:
            estimates.append((r1y, 0.50))
        if r3m is not None:
            estimates.append((r3m * 4, 0.30))
        if r1m is not None:
            estimates.append((r1m * 12, 0.20))
        if estimates:
            weighted = sum(v * w for v, w in estimates) / sum(w for _, w in estimates)
            gross = max(-25.0, min(22.0, weighted))
        else:
            gross = 4.0
        r1m_value = float(r1m or 0.0)
        r3m_value = float(r3m or 0.0)
        if r1m_value > 3 and r3m_value > 5:
            trend = "Positivo"
        elif r1m_value < -3 and r3m_value < -5:
            trend = "Debole"
        elif r1m_value > 2:
            trend = "Rimbalzo breve"
        elif r1m_value < -2:
            trend = "Pressione breve"
        else:
            trend = "Laterale"
    net = max(-30.0, min(18.0, gross - annual_cost_pct))
    net_3m = ((1 + net / 100) ** (3 / 12) - 1) * 100 if net > -99 else 0.0
    return gross, net, net_3m, trend


def _future_value(current: float, monthly_pac: float, months: int, annual_return_pct: float) -> float:
    monthly_rate = (1 + annual_return_pct / 100) ** (1 / 12) - 1 if annual_return_pct > -99 else 0.0
    value = max(0.0, current)
    for _ in range(months):
        value *= 1 + monthly_rate
        if monthly_pac > 0:
            value += monthly_pac
    return value


def _decision(days: int, name: str, role: str, annual_cost: float, margin_pct: float, net_1y: float, trend: str) -> tuple[str, str, str]:
    low = f"{name} {role} {trend}".lower()
    if days < 45:
        if annual_cost >= 3.0:
            return (
                "Tieni ora, sotto esame costi",
                "Portafoglio appena partito: troppo presto per chiudere, ma il costo alto va verificato.",
                "Valuta switch se tra 6-12 mesi resta sotto un'alternativa dividend/global meno costosa.",
            )
        return (
            "Tieni / monitora",
            "Appena sottoscritto: ora la priorita' e' leggere correttamente controvalore, costi e primo andamento.",
            "Rivaluta solo dopo 3-6 mesi di dati reali, meglio 12 mesi.",
        )
    if annual_cost >= 3.0 and net_1y < 4.0:
        return (
            "Valuta alternativa col consulente",
            "Costo elevato e proiezione netta debole: serve confronto con fondo/ETF simile piu' efficiente.",
            "Chiedi simulazione di switch e impatto fiscale/costi prima di muoverti.",
        )
    if margin_pct < -6 and ("debole" in low or "pressione" in low):
        return (
            "Non aumentare",
            "Perdita e trend debole: meglio non incrementare finche' non si stabilizza.",
            "Valuta switch se resta sotto benchmark per 2-3 mesi consecutivi.",
        )
    if "pac" in low or "satellite" in low:
        return (
            "Tieni PAC, non aumentare peso",
            "Il PAC riduce il rischio timing: mantieni la rata e controlla il peso nel portafoglio.",
            "Rivedi se il settore entra in trend negativo prolungato o diventa troppo pesante.",
        )
    if net_1y >= 5.0 and margin_pct >= -3.0:
        return (
            "Tieni",
            "Andamento e proiezione sono coerenti con il ruolo del fondo.",
            "Switch solo se trovi alternativa piu' economica con stesso ruolo/rischio.",
        )
    return (
        "Tieni ma confronta",
        "Non c'e' un segnale forte per vendere subito, ma va confrontato con benchmark e costi.",
        "Rivaluta tra 3-6 mesi se rende meno del proxy dopo costi.",
    )


def _history_rows(hist: pd.DataFrame, fund: pd.Series, used_ticker: str, source: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if hist.empty:
        return out
    first = float(hist["Close"].iloc[0]) or 1.0
    for _, point in hist.iterrows():
        close = float(point["Close"])
        out.append({
            "ISIN": fund.get("ISIN", ""),
            "Nome Strumento": fund.get("Nome Strumento", ""),
            "Date": point["Date"].date().isoformat() if hasattr(point["Date"], "date") else str(point["Date"]),
            "Close": round(close, 6),
            "Normalized 100": round(close / first * 100, 4),
            "Proxy usato": used_ticker,
            "Fonte dato": source,
        })
    return out


def _safe_funds() -> pd.DataFrame:
    try:
        return load_fund_universe(FINECO_FUNDS_PUBLIC_FILE)
    except Exception:  # noqa: BLE001
        if FINECO_FUNDS_PUBLIC_FILE.exists():
            return pd.read_csv(FINECO_FUNDS_PUBLIC_FILE)
        return pd.DataFrame()


def build_live_portfolio_snapshot(period: str = "1y", as_of: date | None = None) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    as_of = as_of or today_rome()
    funds = _safe_funds()
    if funds.empty:
        summary = {
            "version": VERSION,
            "generated_at_rome": now_rome_iso(),
            "data_analisi": as_of.isoformat(),
            "message": "Nessun fondo configurato",
        }
        return pd.DataFrame(), pd.DataFrame(), summary

    funds = _merge_manual_values(funds)
    rows: list[dict[str, Any]] = []
    history_rows: list[dict[str, Any]] = []
    generated_at = now_rome_iso()

    for _, fund in funds.iterrows():
        isin = str(fund.get("ISIN", "")).strip()
        name = str(fund.get("Nome Strumento", "")).strip()
        start = _parse_date(fund.get("Data Inizio"), as_of)
        days = max(0, (as_of - start).days)
        initial = _as_float(fund.get("Importo Iniziale EUR"))
        monthly_pac = _as_float(fund.get("PAC Mensile EUR"))
        annual_cost = _as_float(fund.get("Costo Annuo %"))
        stamp = _as_float(fund.get("Bollo Una Tantum EUR"), 6.0)
        flows = _build_cashflows(initial, monthly_pac, start, as_of)
        invested_auto = round(sum(flow.amount for flow in flows), 2)
        stamp_applied = stamp if invested_auto > 0 else 0.0

        candidates_all = _ticker_candidates(fund)
        primary = str(fund.get("Proxy Ticker", "")).strip()
        quick_candidates: list[str] = []
        if primary:
            quick_candidates.append(primary)
        # Add one liquid non-European fallback if configured.
        for candidate in candidates_all:
            if candidate not in quick_candidates and "." not in candidate:
                quick_candidates.append(candidate)
                break
        if not quick_candidates:
            quick_candidates = candidates_all[:2]
        raw_hist, used_ticker, source = _fetch_proxy_history(quick_candidates, period=period)
        hist = _history_prepare(raw_hist)
        history_rows.extend(_history_rows(hist, fund, used_ticker, source))

        proxy_value_before_costs = _cashflows_value_from_proxy(hist, flows)
        accrued_cost = _cashflows_accrued_cost(flows, annual_cost, as_of)
        manual_active = _manual_actual_is_active(fund, start, invested_auto)
        actual_value = _as_float(fund.get("Valore Attuale Fineco EUR"), 0.0)
        actual_capital = _as_float(fund.get("Capitale Versato Fineco EUR"), 0.0)

        if manual_active:
            invested = actual_capital if actual_capital > 0 else invested_auto
            current_value = actual_value
            value_source = "Fineco manuale/reale"
            cost_note = "Costi gestione gia' incorporati nel NAV Fineco; bollo sottratto nel margine netto."
            margin_gross = current_value - invested
            margin_net = current_value - invested - stamp_applied
        else:
            invested = invested_auto
            current_value = max(0.0, proxy_value_before_costs - accrued_cost)
            value_source = "Proxy live automatico"
            cost_note = "Proxy di mercato: sottratto costo annuo maturato stimato + bollo una tantum."
            margin_gross = proxy_value_before_costs - invested
            margin_net = current_value - invested - stamp_applied

        margin_pct = margin_net / invested * 100 if invested > 0 else 0.0
        gross_expected_1y, net_expected_1y, net_expected_3m, trend = _annual_expectation(hist, annual_cost)
        projection_3m = _future_value(current_value, monthly_pac, 3, net_expected_1y)
        projection_1y = _future_value(current_value, monthly_pac, 12, net_expected_1y)
        future_invested_3m = invested + monthly_pac * 3
        future_invested_1y = invested + monthly_pac * 12
        projection_gain_3m = projection_3m - future_invested_3m - stamp_applied
        projection_gain_1y = projection_1y - future_invested_1y - stamp_applied
        decision, reason, switch = _decision(days, name, str(fund.get("Ruolo", "")), annual_cost, margin_pct, net_expected_1y, trend)

        rows.append({
            "ISIN": isin,
            "Fondo/PAC": name,
            "Nome Strumento": name,
            "Tipo": fund.get("Tipo Versamento", fund.get("Tipo", "")),
            "Ruolo": fund.get("Ruolo", ""),
            "Categoria": fund.get("Categoria AlphaForge", ""),
            "Data sottoscrizione": start.isoformat(),
            "Giorni da inizio": days,
            "Importo iniziale EUR": round(initial, 2),
            "PAC mensile EUR": round(monthly_pac, 2),
            "Rate PAC stimate versate": sum(1 for flow in flows if flow.kind == "PAC"),
            "Capitale versato EUR": round(invested, 2),
            "Controvalore attuale EUR": round(current_value, 2),
            "Valore attuale EUR": round(current_value, 2),
            "Margine lordo EUR": round(margin_gross, 2),
            "Costo maturato stimato EUR": round(accrued_cost, 2),
            "Bollo sottratto EUR": round(stamp_applied, 2),
            "Margine netto EUR": round(margin_net, 2),
            "Margine netto %": round(margin_pct, 2),
            "Costo annuo %": round(annual_cost, 2),
            "Rendimento atteso netto 3M %": round(net_expected_3m, 2),
            "Rendimento atteso netto 1Y %": round(net_expected_1y, 2),
            "Proiezione 3M base EUR": round(projection_3m, 2),
            "Guadagno stimato 3M EUR": round(projection_gain_3m, 2),
            "Proiezione 1Y base EUR": round(projection_1y, 2),
            "Guadagno stimato 1Y EUR": round(projection_gain_1y, 2),
            "Trend proxy": trend,
            "Proxy usato": used_ticker or "n/d",
            "Fonte valore": value_source,
            "Fonte dato proxy": source,
            "Decisione pratica": decision,
            "Motivo": reason,
            "Quando valutare switch": switch,
            "Nota costi": cost_note,
            "Aggiornato Roma": generated_at,
        })

    live = pd.DataFrame(rows)
    history = pd.DataFrame(history_rows)
    total_initial = float(live["Importo iniziale EUR"].sum()) if not live.empty else 0.0
    total_pac = float(live["PAC mensile EUR"].sum()) if not live.empty else 0.0
    invested = float(live["Capitale versato EUR"].sum()) if not live.empty else 0.0
    current = float(live["Controvalore attuale EUR"].sum()) if not live.empty else 0.0
    margin = float(live["Margine netto EUR"].sum()) if not live.empty else 0.0
    proj_3m = float(live["Proiezione 3M base EUR"].sum()) if not live.empty else 0.0
    proj_1y = float(live["Proiezione 1Y base EUR"].sum()) if not live.empty else 0.0
    latest_proxy_date = "n/d"
    if not history.empty and "Date" in history.columns:
        try:
            latest_proxy_date = str(pd.to_datetime(history["Date"], errors="coerce").dropna().max().date())
        except Exception:  # noqa: BLE001
            latest_proxy_date = "n/d"
    summary = {
        "version": VERSION,
        "generated_at_rome": generated_at,
        "data_analisi": as_of.isoformat(),
        "latest_proxy_date": latest_proxy_date,
        "investito_iniziale_eur": round(total_initial, 2),
        "pac_mensile_eur": round(total_pac, 2),
        "capitale_versato_eur": round(invested, 2),
        "controvalore_attuale_eur": round(current, 2),
        "valore_attuale_eur": round(current, 2),
        "margine_netto_eur": round(margin, 2),
        "margine_netto_pct": round(margin / invested * 100, 2) if invested > 0 else 0.0,
        "proiezione_3m_base_eur": round(proj_3m, 2),
        "proiezione_1y_base_eur": round(proj_1y, 2),
        "fonte_prevalente": "Fineco manuale se compilato; altrimenti proxy live automatico",
        "decisione_sintesi": _summary_decision(live),
        "messaggio": "Streamlit aggiorna dati/proxy all'apertura. Il controvalore Fineco esatto richiede export o inserimento dei valori reali; il proxy live e' una stima di mercato.",
    }
    return live, history, summary


def _summary_decision(live: pd.DataFrame) -> str:
    if live.empty:
        return "Nessun dato"
    decisions = " | ".join(live["Decisione pratica"].astype(str).tolist()).lower()
    if "valuta alternativa" in decisions:
        return "Tieni ora, ma porta al consulente i fondi da confrontare"
    if "non aumentare" in decisions:
        return "Mantieni ma non aumentare le parti deboli"
    if "sotto esame costi" in decisions:
        return "Tieni: controlla soprattutto i costi elevati"
    return "Tieni e monitora: nessun segnale forte di switch immediato"


def save_live_portfolio_snapshot(period: str = "1y") -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    live, history, summary = build_live_portfolio_snapshot(period=period)
    live.to_csv(FINECO_LIVE_PORTFOLIO_CSV, index=False)
    history.to_csv(FINECO_LIVE_PRICE_HISTORY_CSV, index=False)
    _write_json(FINECO_LIVE_SUMMARY_FILE, summary)
    return live, history, summary


if __name__ == "__main__":
    save_live_portfolio_snapshot()
