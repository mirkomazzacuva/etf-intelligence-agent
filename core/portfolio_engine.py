from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from core.data_provider import fetch_price_history

ALIASES = {
    "Ticker": ["ticker", "simbolo", "strumento", "isin/ticker"],
    "Quantità": ["quantita", "quantità", "qty", "quote", "numero quote", "azioni"],
    "Prezzo Medio": ["prezzo medio", "pmc", "prezzo carico", "prezzo acquisto", "avg price", "average price"],
    "Prezzo Attuale": ["prezzo attuale", "current price", "last price", "prezzo"],
    "Valore EUR": ["valore", "valore eur", "controvalore", "market value", "importo"],
    "Target %": ["target %", "peso target", "peso target %", "target"],
    "Categoria Utente": ["categoria", "asset class", "tipo", "bucket"],
}


@dataclass
class PortfolioResult:
    positions: pd.DataFrame
    summary: dict[str, object]
    improvements: pd.DataFrame


def _clean_name(value: object) -> str:
    return str(value or "").strip().lower().replace("_", " ")


def _to_float(value: object, default: float = 0.0) -> float:
    try:
        if pd.isna(value):
            return default
        if isinstance(value, str):
            value = value.replace("€", "").replace("%", "").replace(".", "").replace(",", ".").strip()
        return float(value)
    except Exception:  # noqa: BLE001
        return default


def normalize_portfolio_columns(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=["Ticker", "Quantità", "Prezzo Medio", "Valore EUR"])
    out = df.copy()
    mapping: dict[str, str] = {}
    cols_clean = {_clean_name(col): col for col in out.columns}
    for canonical, aliases in ALIASES.items():
        if canonical in out.columns:
            continue
        for alias in aliases:
            if alias in cols_clean:
                mapping[cols_clean[alias]] = canonical
                break
    out = out.rename(columns=mapping)
    if "Ticker" not in out.columns:
        return pd.DataFrame(columns=["Ticker", "Quantità", "Prezzo Medio", "Valore EUR", "Errore"])
    out["Ticker"] = out["Ticker"].astype(str).str.upper().str.strip()
    out = out[out["Ticker"] != ""].copy()
    for col in ["Quantità", "Prezzo Medio", "Prezzo Attuale", "Valore EUR", "Target %"]:
        if col in out.columns:
            out[col] = out[col].map(_to_float)
    return out


def _latest_price(ticker: str) -> float | None:
    prices, error = fetch_price_history(ticker, period="6mo")
    if error or prices.empty or "Close" not in prices.columns:
        return None
    try:
        return float(pd.to_numeric(prices["Close"], errors="coerce").dropna().iloc[-1])
    except Exception:  # noqa: BLE001
        return None


def _decision_for_position(row: pd.Series) -> str:
    weight = _to_float(row.get("Peso %"))
    risk = str(row.get("Risk Flag", "")).lower()
    decision = str(row.get("Decisione chiara", row.get("Azione Suggerita", ""))).lower()
    gain = _to_float(row.get("P/L %"), 0)
    priority = _to_float(row.get("Priority Score"), 0)
    if weight >= 30:
        return "Controlla concentrazione: posizione molto pesante."
    if "high" in risk or "riduci" in decision:
        return "Non aumentare: valuta riduzione size o protezione del rischio."
    if gain > 45 and priority < 65:
        return "Valuta presa profitto parziale o trailing stop: guadagno alto ma priorità non elevata."
    if "pullback" in decision:
        return "Mantieni/monitora: evita nuovi acquisti finché non rientra in zona migliore."
    if priority >= 75 and weight < 15:
        return "Buona posizione da monitorare: eventuale incremento solo graduale e coerente col rischio."
    return "Mantieni in monitoraggio: rivaluta dopo prossimo aggiornamento dati."


def analyze_portfolio(portfolio: pd.DataFrame, action_plan: pd.DataFrame | None = None, insights: pd.DataFrame | None = None) -> PortfolioResult:
    pos = normalize_portfolio_columns(portfolio)
    if pos.empty:
        return PortfolioResult(pos, {"Valore Totale EUR": 0, "Nota": "Portafoglio vuoto o colonne non riconosciute."}, pd.DataFrame())

    if "Prezzo Attuale" not in pos.columns:
        pos["Prezzo Attuale"] = 0.0
    for idx, row in pos.iterrows():
        if _to_float(row.get("Prezzo Attuale"), 0) <= 0:
            latest = _latest_price(str(row.get("Ticker", "")))
            if latest is not None:
                pos.at[idx, "Prezzo Attuale"] = latest

    if "Valore EUR" not in pos.columns:
        pos["Valore EUR"] = 0.0
    for idx, row in pos.iterrows():
        value = _to_float(row.get("Valore EUR"), 0)
        qty = _to_float(row.get("Quantità"), 0)
        current = _to_float(row.get("Prezzo Attuale"), 0)
        if value <= 0 and qty > 0 and current > 0:
            pos.at[idx, "Valore EUR"] = round(qty * current, 2)

    total = float(pd.to_numeric(pos["Valore EUR"], errors="coerce").fillna(0).sum())
    pos["Peso %"] = (pd.to_numeric(pos["Valore EUR"], errors="coerce").fillna(0) / total * 100).round(2) if total > 0 else 0
    if "Prezzo Medio" in pos.columns:
        avg = pd.to_numeric(pos["Prezzo Medio"], errors="coerce").fillna(0)
        cur = pd.to_numeric(pos["Prezzo Attuale"], errors="coerce").fillna(0)
        pos["P/L %"] = ((cur / avg - 1) * 100).where(avg > 0).round(2)
    else:
        pos["P/L %"] = pd.NA

    enrich_frames: list[pd.DataFrame] = []
    if action_plan is not None and not action_plan.empty:
        enrich_frames.append(action_plan.copy())
    if insights is not None and not insights.empty:
        enrich_frames.append(insights.copy())
    if enrich_frames:
        enrich = pd.concat(enrich_frames, ignore_index=True, sort=False)
        enrich["Ticker"] = enrich["Ticker"].astype(str).str.upper().str.strip()
        enrich = enrich.drop_duplicates(subset=["Ticker"], keep="first")
        keep = [
            "Ticker", "Score Finale", "Priority Score", "Decisione chiara", "Azione Suggerita", "Entry Zone", "Risk Flag",
            "Trigger Monitoraggio", "Cosa fare adesso", "Perché", "Stato", "Trend",
        ]
        pos = pos.merge(enrich[[c for c in keep if c in enrich.columns]], on="Ticker", how="left")

    pos["Suggerimento Portafoglio"] = pos.apply(_decision_for_position, axis=1)
    pos = pos.sort_values("Peso %", ascending=False, na_position="last")

    top1 = float(pos["Peso %"].max()) if not pos.empty else 0.0
    top3 = float(pos["Peso %"].head(3).sum()) if not pos.empty else 0.0
    high_risk_weight = float(pos.loc[pos.get("Risk Flag", pd.Series(dtype=str)).astype(str).str.contains("high|alto", case=False, regex=True, na=False), "Peso %"].sum()) if "Risk Flag" in pos.columns else 0.0
    no_score = int(pos.get("Score Finale", pd.Series([pd.NA] * len(pos))).isna().sum()) if not pos.empty else 0
    summary = {
        "Valore Totale EUR": round(total, 2),
        "Numero Posizioni": int(len(pos)),
        "Peso maggiore %": round(top1, 2),
        "Peso Top 3 %": round(top3, 2),
        "Peso High Risk %": round(high_risk_weight, 2),
        "Posizioni senza score": no_score,
    }

    rows: list[dict[str, object]] = []
    if top1 > 30:
        rows.append({"Priorità": "Alta", "Area": "Concentrazione", "Miglioramento": "La posizione più grande supera il 30%. Valuta riduzione o bilanciamento."})
    if top3 > 65:
        rows.append({"Priorità": "Media", "Area": "Diversificazione", "Miglioramento": "Le prime 3 posizioni pesano molto. Aggiungere decorrelazione può ridurre volatilità."})
    if high_risk_weight > 25:
        rows.append({"Priorità": "Alta", "Area": "Rischio", "Miglioramento": "Peso high-risk elevato: evitare nuovi incrementi sulle posizioni più volatili."})
    if no_score > 0:
        rows.append({"Priorità": "Media", "Area": "Copertura dati", "Miglioramento": "Alcuni ticker non sono nella watchlist AlphaForge: analizzali nella pagina Analizza Strumento."})
    if not rows:
        rows.append({"Priorità": "OK", "Area": "Struttura", "Miglioramento": "Nessun problema evidente: continua il monitoraggio periodico."})
    return PortfolioResult(pos, summary, pd.DataFrame(rows))


def portfolio_template() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"Ticker": "SWDA.MI", "Quantità": 10, "Prezzo Medio": 95.0, "Valore EUR": 1000, "Target %": 40, "Categoria Utente": "Core ETF"},
            {"Ticker": "NVDA", "Quantità": 2, "Prezzo Medio": 120.0, "Valore EUR": 240, "Target %": 10, "Categoria Utente": "AI/Semiconduttori"},
            {"Ticker": "SGLD.MI", "Quantità": 5, "Prezzo Medio": 220.0, "Valore EUR": 1100, "Target %": 10, "Categoria Utente": "Difensivo"},
        ]
    )
