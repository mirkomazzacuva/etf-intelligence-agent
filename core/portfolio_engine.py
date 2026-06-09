from __future__ import annotations

import pandas as pd


def normalize_weights(df: pd.DataFrame, weight_col: str = "Peso Target %") -> pd.DataFrame:
    out = df.copy()
    if out.empty or weight_col not in out.columns:
        return out
    weights = pd.to_numeric(out[weight_col], errors="coerce").fillna(0)
    total = float(weights.sum())
    if total > 0:
        out[weight_col] = (weights / total * 100).round(2)
    return out


def portfolio_risk_summary(allocation: pd.DataFrame) -> dict[str, object]:
    if allocation is None or allocation.empty:
        return {"Profilo": "n/d", "Nota": "Allocazione non disponibile."}
    weights = pd.to_numeric(allocation.get("Peso Target %"), errors="coerce").fillna(0)
    vol = pd.to_numeric(allocation.get("Volatilità %"), errors="coerce").fillna(0)
    dd = pd.to_numeric(allocation.get("Max Drawdown %"), errors="coerce").fillna(0)
    weighted_vol = float((weights * vol).sum() / max(weights.sum(), 1))
    weighted_dd = float((weights * dd).sum() / max(weights.sum(), 1))
    if weighted_vol <= 14:
        profile = "Prudente/Bilanciato"
    elif weighted_vol <= 22:
        profile = "Bilanciato"
    else:
        profile = "Aggressivo"
    return {
        "Profilo": profile,
        "Volatilità ponderata stimata %": round(weighted_vol, 2),
        "Drawdown ponderato storico %": round(weighted_dd, 2),
        "Nota": "Stima semplificata basata su volatilità/drawdown storici degli strumenti in allocazione.",
    }
