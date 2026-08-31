from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

from core.config import (
    FINECO_PORTFOLIO_TEMPLATE_FILE,
    SECTOR_COMPASS_OUTPUT_CSV,
    SECTOR_COMPASS_OUTPUT_XLSX,
    SECTOR_UNIVERSE_FILE,
)


def _as_float(value: object, default: float = 0.0) -> float:
    try:
        if pd.isna(value):
            return default
        return float(value)
    except Exception:  # noqa: BLE001
        return default


def _clip(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return float(max(low, min(high, value)))


def load_sector_universe(path: Path = SECTOR_UNIVERSE_FILE) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"File universo settoriale mancante: {path}")
    df = pd.read_csv(path)
    required = {"Settore", "Priorita Strategica", "Ticker ETF/Fondo", "ETF/Fondo candidato", "Target Satellite %", "Max Satellite %"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"Colonne mancanti in {path}: {', '.join(sorted(missing))}")
    return df.fillna("")


def _download_close_prices(tickers: Iterable[str]) -> pd.DataFrame:
    valid = [str(t).strip() for t in tickers if str(t).strip() and str(t).strip().upper() != "NA"]
    if not valid:
        return pd.DataFrame()
    try:
        import yfinance as yf  # type: ignore

        data = yf.download(valid, period="1y", interval="1d", auto_adjust=True, progress=False, threads=False)
        if data.empty:
            return pd.DataFrame()
        if isinstance(data.columns, pd.MultiIndex):
            if "Close" in data.columns.get_level_values(0):
                close = data["Close"].copy()
            elif "Adj Close" in data.columns.get_level_values(0):
                close = data["Adj Close"].copy()
            else:
                close = data.xs(data.columns.get_level_values(0)[0], axis=1, level=0)
        else:
            col = "Close" if "Close" in data.columns else data.columns[0]
            close = data[[col]].copy()
            close.columns = valid[:1]
        if isinstance(close, pd.Series):
            close = close.to_frame(valid[0])
        close = close.dropna(how="all")
        return close
    except Exception:  # noqa: BLE001
        return pd.DataFrame()


def _series_metrics(close: pd.Series) -> dict[str, float | str]:
    close = pd.to_numeric(close, errors="coerce").dropna()
    if len(close) < 40:
        return {
            "Rendimento 3M %": np.nan,
            "Rendimento 6M %": np.nan,
            "Volatilita 1Y %": np.nan,
            "Max Drawdown 1Y %": np.nan,
            "Momentum Score": 50.0,
            "Risk Score": 50.0,
            "Trend": "Dati limitati",
        }
    ret = close.pct_change().dropna()
    last = float(close.iloc[-1])
    r3 = ((last / float(close.iloc[-63])) - 1) * 100 if len(close) > 63 else np.nan
    r6 = ((last / float(close.iloc[-126])) - 1) * 100 if len(close) > 126 else np.nan
    vol = float(ret.std() * np.sqrt(252) * 100) if not ret.empty else np.nan
    peak = close.cummax()
    dd = float(((close / peak) - 1).min() * 100)
    sma50 = float(close.tail(50).mean())
    sma200 = float(close.tail(min(200, len(close))).mean())
    trend = "Sopra media 50/200" if last >= sma50 and last >= sma200 else "Debole o laterale"
    momentum = 50 + (_as_float(r3) * 1.2) + (_as_float(r6) * 0.7)
    if last >= sma50:
        momentum += 8
    if last >= sma200:
        momentum += 8
    risk_score = 100 - max(0, _as_float(vol, 25) - 12) * 1.4 - abs(min(0, dd)) * 0.7
    return {
        "Rendimento 3M %": round(_as_float(r3, np.nan), 2),
        "Rendimento 6M %": round(_as_float(r6, np.nan), 2),
        "Volatilita 1Y %": round(_as_float(vol, np.nan), 2),
        "Max Drawdown 1Y %": round(_as_float(dd, np.nan), 2),
        "Momentum Score": round(_clip(momentum), 1),
        "Risk Score": round(_clip(risk_score), 1),
        "Trend": trend,
    }


def _decision(score: float, momentum: float, risk: float, strategic: float, sector_type: str) -> tuple[str, str, str]:
    high_risk = risk < 42
    if score >= 78 and momentum >= 58 and not high_risk:
        return (
            "Da discutere ora",
            "Valuta esposizione graduale con consulente",
            "Settore interessante: usare ETF/fondo come default, azione singola solo per piccola quota satellite.",
        )
    if score >= 68 and high_risk:
        return (
            "Tema forte ma rischioso",
            "Non aumentare size senza piano",
            "Il tema e' interessante ma volatilita/drawdown richiedono ingresso graduale o attesa.",
        )
    if strategic >= 75 and momentum < 52:
        return (
            "Watchlist strategica",
            "Aspetta conferma o PAC piccolo",
            "Trend non ancora forte: utile monitorarlo ma senza inseguire.",
        )
    if score >= 60:
        return (
            "Monitorare",
            "Confronta ETF/fondo e costi",
            "Potrebbe avere senso come satellite, ma non e' una priorita urgente.",
        )
    return (
        "Bassa priorita",
        "Evita o rimanda",
        "Non aggiungere complessita se il portafoglio core e' gia sufficiente.",
    )


def build_sector_compass(universe: pd.DataFrame | None = None) -> pd.DataFrame:
    source = load_sector_universe() if universe is None else universe.copy()
    tickers = source["Ticker ETF/Fondo"].astype(str).tolist()
    prices = _download_close_prices(tickers)
    rows: list[dict] = []
    for _, row in source.iterrows():
        ticker = str(row.get("Ticker ETF/Fondo", "")).strip()
        strategic = _clip(_as_float(row.get("Priorita Strategica", 50), 50))
        metrics = _series_metrics(prices[ticker]) if not prices.empty and ticker in prices.columns else _series_metrics(pd.Series(dtype=float))
        momentum = _as_float(metrics.get("Momentum Score"), 50)
        risk = _as_float(metrics.get("Risk Score"), 50)
        sector_type = str(row.get("Tipo Copertura", "Satellite"))
        # Sector score gives more weight to strategic usefulness than to short term price noise.
        score = round(_clip(strategic * 0.48 + momentum * 0.34 + risk * 0.18), 1)
        bucket, action, reason = _decision(score, momentum, risk, strategic, sector_type)
        target = _as_float(row.get("Target Satellite %"), 0)
        max_target = _as_float(row.get("Max Satellite %"), target)
        suggested_range = "Core" if "Core" in sector_type else f"{max(0, target - 1):.0f}-{max_target:.0f}%"
        rows.append({
            "Settore": row.get("Settore", ""),
            "Bucket": bucket,
            "Cosa fare": action,
            "Perche": reason,
            "Sector Score": score,
            "Priorita Strategica": strategic,
            "Momentum Score": round(momentum, 1),
            "Risk Score": round(risk, 1),
            "Trend": metrics.get("Trend", "Dati limitati"),
            "Rendimento 3M %": metrics.get("Rendimento 3M %", np.nan),
            "Rendimento 6M %": metrics.get("Rendimento 6M %", np.nan),
            "Volatilita 1Y %": metrics.get("Volatilita 1Y %", np.nan),
            "Max Drawdown 1Y %": metrics.get("Max Drawdown 1Y %", np.nan),
            "Strumento preferito": row.get("Strumento Preferito", "ETF/Fondo"),
            "Ticker ETF/Fondo": ticker,
            "ETF/Fondo candidato": row.get("ETF/Fondo candidato", ""),
            "Azioni leader": row.get("Azioni Leader", ""),
            "Target Satellite %": target,
            "Max Satellite %": max_target,
            "Range pratico": suggested_range,
            "Orizzonte": row.get("Orizzonte", ""),
            "Perche guardarlo": row.get("Perche guardarlo", ""),
            "Rischio principale": row.get("Rischio principale", ""),
            "Nota Fineco/Consulente": row.get("Nota Fineco/Consulente", ""),
        })
    output = pd.DataFrame(rows)
    output = output.sort_values(["Sector Score", "Priorita Strategica"], ascending=False, na_position="last")
    output.insert(0, "Priorita", range(1, len(output) + 1))
    return output


def save_sector_compass(df: pd.DataFrame) -> None:
    df.to_csv(SECTOR_COMPASS_OUTPUT_CSV, index=False)
    try:
        df.to_excel(SECTOR_COMPASS_OUTPUT_XLSX, index=False)
    except Exception:  # noqa: BLE001
        pass


def fineco_portfolio_template() -> pd.DataFrame:
    if FINECO_PORTFOLIO_TEMPLATE_FILE.exists():
        return pd.read_csv(FINECO_PORTFOLIO_TEMPLATE_FILE)
    return pd.DataFrame(columns=["Ticker", "Nome Strumento", "Tipo", "Settore AlphaForge", "Valore EUR", "PMC", "Prezzo Attuale", "Target %", "Note"])


def normalize_portfolio_columns(df: pd.DataFrame) -> pd.DataFrame:
    mapping = {
        "ticker": "Ticker",
        "isin/ticker": "Ticker",
        "nome": "Nome Strumento",
        "strumento": "Nome Strumento",
        "tipo": "Tipo",
        "settore": "Settore AlphaForge",
        "settore alphaforge": "Settore AlphaForge",
        "valore": "Valore EUR",
        "valore eur": "Valore EUR",
        "controvalore": "Valore EUR",
        "target": "Target %",
        "target %": "Target %",
    }
    out = df.copy()
    rename = {col: mapping.get(str(col).lower().strip(), col) for col in out.columns}
    out = out.rename(columns=rename)
    for col in ["Ticker", "Nome Strumento", "Tipo", "Settore AlphaForge", "Valore EUR", "Target %", "Note"]:
        if col not in out.columns:
            out[col] = "" if col not in {"Valore EUR", "Target %"} else 0
    out["Valore EUR"] = pd.to_numeric(out["Valore EUR"], errors="coerce").fillna(0.0)
    out["Target %"] = pd.to_numeric(out["Target %"], errors="coerce").fillna(0.0)
    return out


@dataclass
class SectorPortfolioResult:
    summary: dict[str, object]
    positions: pd.DataFrame
    sector_view: pd.DataFrame
    suggestions: pd.DataFrame


def analyze_sector_portfolio(portfolio: pd.DataFrame, sector_compass: pd.DataFrame) -> SectorPortfolioResult:
    pf = normalize_portfolio_columns(portfolio)
    total = float(pd.to_numeric(pf["Valore EUR"], errors="coerce").fillna(0).sum())
    pf["Peso %"] = np.where(total > 0, pf["Valore EUR"] / total * 100, 0)
    compass_cols = ["Settore", "Bucket", "Cosa fare", "Sector Score", "Range pratico", "Rischio principale", "Nota Fineco/Consulente"]
    merged = pf.merge(sector_compass[compass_cols], how="left", left_on="Settore AlphaForge", right_on="Settore") if not sector_compass.empty else pf.copy()
    merged["Lettura portafoglio"] = merged.apply(_portfolio_position_comment, axis=1)
    sector_view = (
        merged.groupby("Settore AlphaForge", dropna=False)
        .agg({"Valore EUR": "sum", "Peso %": "sum", "Target %": "sum"})
        .reset_index()
        .sort_values("Peso %", ascending=False)
    )
    sector_view["Gap vs Target %"] = sector_view["Target %"] - sector_view["Peso %"]
    suggestions = _portfolio_suggestions(merged, sector_view, sector_compass, total)
    summary = {
        "Valore Totale EUR": round(total, 2),
        "Numero posizioni": int(len(pf)),
        "Peso core %": round(float(sector_view.loc[sector_view["Settore AlphaForge"].astype(str).str.contains("Core", case=False, na=False), "Peso %"].sum()), 2),
        "Peso satellite %": round(float(100 - sector_view.loc[sector_view["Settore AlphaForge"].astype(str).str.contains("Core", case=False, na=False), "Peso %"].sum()), 2) if total > 0 else 0,
        "Peso maggiore %": round(float(pf["Peso %"].max()) if len(pf) else 0, 2),
        "Settori coperti": int(sector_view["Settore AlphaForge"].replace("", np.nan).dropna().nunique()),
    }
    return SectorPortfolioResult(summary=summary, positions=merged, sector_view=sector_view, suggestions=suggestions)


def _portfolio_position_comment(row: pd.Series) -> str:
    peso = _as_float(row.get("Peso %"), 0)
    settore = str(row.get("Settore AlphaForge", "")).strip()
    bucket = str(row.get("Bucket", "")).strip()
    if not settore or settore.lower() == "da classificare":
        return "Prima classifica questo strumento in un settore AlphaForge."
    if peso > 30:
        return "Peso molto alto: prima discutere concentrazione/ribilanciamento con consulente."
    if bucket in {"Tema forte ma rischioso", "Bassa priorita"} and peso > 8:
        return "Satellite rischioso: non aumentare e verifica se il peso e' coerente."
    if "Core" in settore and peso < 40:
        return "Core potenzialmente basso: verifica se la base globale e' sufficiente."
    return "Mantieni monitoraggio: controlla peso, costi, KID e coerenza con obiettivo."


def _portfolio_suggestions(positions: pd.DataFrame, sector_view: pd.DataFrame, sector_compass: pd.DataFrame, total: float) -> pd.DataFrame:
    rows: list[dict] = []
    if total <= 0:
        rows.append({"Priorita": 1, "Tema": "Dati portafoglio", "Suggerimento": "Inserisci Valore EUR per ogni posizione per calcolare pesi e gap."})
        return pd.DataFrame(rows)
    top_weight = float(positions["Peso %"].max()) if not positions.empty else 0
    if top_weight > 30:
        top = positions.sort_values("Peso %", ascending=False).iloc[0]
        rows.append({"Priorita": 1, "Tema": "Concentrazione", "Suggerimento": f"{top.get('Ticker','')} pesa {top_weight:.1f}%. Prima di comprare nuovi settori valuta il ribilanciamento."})
    unclassified = positions[positions["Settore AlphaForge"].astype(str).str.strip().isin(["", "Da classificare"])]
    if not unclassified.empty:
        rows.append({"Priorita": len(rows) + 1, "Tema": "Classificazione", "Suggerimento": f"{len(unclassified)} strumenti non sono classificati. Classificarli prima di decidere nuovi settori."})
    core_weight = float(sector_view.loc[sector_view["Settore AlphaForge"].astype(str).str.contains("Core", case=False, na=False), "Peso %"].sum())
    if core_weight < 45:
        rows.append({"Priorita": len(rows) + 1, "Tema": "Core globale", "Suggerimento": "Il core globale sembra sotto il 45%. Discuti con il consulente se aumentare base diversificata prima dei satelliti."})
    if not sector_compass.empty:
        high_priority = sector_compass[sector_compass["Bucket"].isin(["Da discutere ora", "Watchlist strategica"])].head(3)
        covered = set(sector_view["Settore AlphaForge"].astype(str))
        missing = high_priority[~high_priority["Settore"].astype(str).isin(covered)]
        for _, row in missing.head(3).iterrows():
            rows.append({"Priorita": len(rows) + 1, "Tema": str(row.get("Settore", "")), "Suggerimento": f"Settore in priorita ma non presente: valuta {row.get('ETF/Fondo candidato','ETF/fondo')} con il consulente, range {row.get('Range pratico','n/d')}."})
    if not rows:
        rows.append({"Priorita": 1, "Tema": "Portafoglio", "Suggerimento": "Portafoglio leggibile: usa la bussola settoriale per decidere solo eventuali satelliti piccoli."})
    return pd.DataFrame(rows)
