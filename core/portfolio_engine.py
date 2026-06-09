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
    "Note": ["note", "commento", "commenti"],
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
            value = value.replace("€", "").replace("%", "").replace(" ", "").strip()
            if "," in value and "." in value:
                value = value.replace(".", "").replace(",", ".")
            elif "," in value:
                value = value.replace(",", ".")
        return float(value)
    except Exception:  # noqa: BLE001
        return default


def _safe_series(df: pd.DataFrame, col: str, default: object = "") -> pd.Series:
    if col in df.columns:
        return df[col]
    return pd.Series([default] * len(df), index=df.index)


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


def _estimate_category(ticker: str, user_category: object = "") -> str:
    if str(user_category or "").strip():
        return str(user_category).strip()
    t = str(ticker).upper()
    if t.endswith((".MI", ".DE", ".AS", ".PA")) and any(x in t for x in ["SWDA", "VWCE", "EIMI", "SXR8", "EUNA", "SGLD", "MVOL", "EXSA", "IWQU", "XDEV"]):
        return "ETF"
    if t in {"NVDA", "AMD", "ASML.AS", "STM.MI", "SMH"}:
        return "Semiconduttori / AI"
    if t in {"AAPL", "MSFT", "GOOGL", "AMZN", "META"}:
        return "Big Tech"
    if t in {"TSLA"}:
        return "Growth ad alta volatilità"
    return "Altro"


def _portfolio_decision(row: pd.Series) -> str:
    weight = _to_float(row.get("Peso %"))
    gap = _to_float(row.get("Gap vs Target %"), 0)
    risk = str(row.get("Risk Flag", "")).lower()
    decision = str(row.get("Decisione chiara", row.get("Azione Suggerita", ""))).lower()
    gain = _to_float(row.get("P/L %"), 0)
    priority = _to_float(row.get("Priority Score"), 0)
    if weight >= 35:
        return "Priorità: riduci concentrazione o blocca nuovi ingressi su questa posizione."
    if weight >= 25 and ("high" in risk or "alto" in risk):
        return "Priorità: rischio alto e peso elevato. Valuta alleggerimento graduale."
    if gap > 8:
        return "Sovrappeso rispetto al target: non aumentare, valuta ribilanciamento."
    if gap < -8 and priority >= 70 and "high" not in risk:
        return "Sottopeso e qualità buona: valuta accumulo graduale solo se coerente col profilo."
    if "pullback" in decision:
        return "Mantieni/monitora: evita nuovi acquisti finché non torna in zona migliore."
    if "riduci" in decision or "high" in risk or "alto" in risk:
        return "Non aumentare: controlla size, volatilità e scenario negativo."
    if gain > 50 and priority < 65:
        return "Guadagno elevato ma priorità non forte: valuta presa profitto parziale o trailing stop."
    if priority >= 75 and weight < 15:
        return "Posizione interessante: eventuale incremento solo a piccoli step e con alert."
    return "Mantieni in osservazione: nessuna azione urgente."


def _health_score(top1: float, top3: float, high_risk_weight: float, no_score: int, avg_gap: float) -> float:
    score = 100.0
    score -= max(top1 - 25, 0) * 1.1
    score -= max(top3 - 60, 0) * 0.8
    score -= max(high_risk_weight - 20, 0) * 1.0
    score -= no_score * 5
    score -= max(avg_gap - 8, 0) * 1.2
    return round(max(0.0, min(100.0, score)), 1)


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
    if "Target %" in pos.columns:
        pos["Gap vs Target %"] = (pd.to_numeric(pos["Peso %"], errors="coerce").fillna(0) - pd.to_numeric(pos["Target %"], errors="coerce").fillna(0)).round(2)
    else:
        pos["Target %"] = pd.NA
        pos["Gap vs Target %"] = pd.NA
    if "Prezzo Medio" in pos.columns:
        avg = pd.to_numeric(pos["Prezzo Medio"], errors="coerce").fillna(0)
        cur = pd.to_numeric(pos["Prezzo Attuale"], errors="coerce").fillna(0)
        pos["P/L %"] = ((cur / avg - 1) * 100).where(avg > 0).round(2)
    else:
        pos["P/L %"] = pd.NA
    pos["Categoria Stimata"] = pos.apply(lambda r: _estimate_category(str(r.get("Ticker", "")), r.get("Categoria Utente", "")), axis=1)

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
            "Trigger Monitoraggio", "Cosa fare adesso", "Perché", "Stato", "Trend", "Scenario Negativo",
        ]
        pos = pos.merge(enrich[[c for c in keep if c in enrich.columns]], on="Ticker", how="left")

    pos["Suggerimento Portafoglio"] = pos.apply(_portfolio_decision, axis=1)
    pos = pos.sort_values("Peso %", ascending=False, na_position="last")

    top1 = float(pd.to_numeric(pos["Peso %"], errors="coerce").fillna(0).max()) if not pos.empty else 0.0
    top3 = float(pd.to_numeric(pos["Peso %"], errors="coerce").fillna(0).head(3).sum()) if not pos.empty else 0.0
    high_risk_weight = float(pos.loc[_safe_series(pos, "Risk Flag").astype(str).str.contains("high|alto", case=False, regex=True, na=False), "Peso %"].sum()) if "Risk Flag" in pos.columns else 0.0
    no_score = int(_safe_series(pos, "Score Finale", pd.NA).isna().sum()) if not pos.empty else 0
    avg_gap = float(pd.to_numeric(pos["Gap vs Target %"], errors="coerce").abs().dropna().mean()) if "Gap vs Target %" in pos.columns else 0.0
    health = _health_score(top1, top3, high_risk_weight, no_score, avg_gap)
    review_count = int(pos["Suggerimento Portafoglio"].astype(str).str.contains("Priorità|Non aumentare|Sovrappeso|alleggerimento|ribilanciamento", case=False, regex=True, na=False).sum())

    summary = {
        "Valore Totale EUR": round(total, 2),
        "Numero Posizioni": int(len(pos)),
        "Peso maggiore %": round(top1, 2),
        "Peso Top 3 %": round(top3, 2),
        "Peso High Risk %": round(high_risk_weight, 2),
        "Posizioni senza score": no_score,
        "Gap medio target %": round(avg_gap, 2),
        "Portfolio Health Score": health,
        "Posizioni da rivedere": review_count,
    }

    rows: list[dict[str, object]] = []
    if top1 > 30:
        rows.append({"Priorità": "Alta", "Area": "Concentrazione", "Miglioramento": "La posizione più grande supera il 30%. Prima di comprare altro, valuta ribilanciamento."})
    if top3 > 65:
        rows.append({"Priorità": "Media", "Area": "Diversificazione", "Miglioramento": "Le prime 3 posizioni pesano molto. Aggiungi decorrelazione prima di aumentare rischio."})
    if high_risk_weight > 25:
        rows.append({"Priorità": "Alta", "Area": "Rischio", "Miglioramento": "Peso high-risk elevato: evita nuovi incrementi sulle posizioni più volatili."})
    if avg_gap > 10:
        rows.append({"Priorità": "Media", "Area": "Target", "Miglioramento": "Il portafoglio è distante dai target inseriti. Ordina le posizioni per Gap vs Target %."})
    if no_score > 0:
        rows.append({"Priorità": "Media", "Area": "Copertura dati", "Miglioramento": "Alcuni ticker non hanno score AlphaForge: analizzali nella pagina Analizza Strumento."})
    if not rows:
        rows.append({"Priorità": "OK", "Area": "Struttura", "Miglioramento": "Nessun problema evidente: continua monitoraggio e ribilanciamento periodico."})
    return PortfolioResult(pos, summary, pd.DataFrame(rows))


def portfolio_template() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"Ticker": "SWDA.MI", "Quantità": 10, "Prezzo Medio": 95.0, "Prezzo Attuale": "", "Valore EUR": 1000, "Target %": 40, "Categoria Utente": "Core ETF", "Note": "Core globale"},
            {"Ticker": "NVDA", "Quantità": 2, "Prezzo Medio": 120.0, "Prezzo Attuale": "", "Valore EUR": 240, "Target %": 10, "Categoria Utente": "AI/Semiconduttori", "Note": "Satellite"},
            {"Ticker": "SGLD.MI", "Quantità": 5, "Prezzo Medio": 220.0, "Prezzo Attuale": "", "Valore EUR": 1100, "Target %": 10, "Categoria Utente": "Difensivo", "Note": "Decorrelazione"},
        ]
    )
