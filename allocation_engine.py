from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

APP_TZ = ZoneInfo("Europe/Rome")
INPUT_FILE = Path("ETF_Intelligence_Agent_UPDATED.xlsx")
OUTPUT_FILE = Path("ETF_Allocation_Model.xlsx")
CASH_AMOUNT = 1000


def now_text() -> str:
    return datetime.now(APP_TZ).strftime("%d/%m/%Y %H:%M")


def market_regime(df: pd.DataFrame) -> str:
    category = df["Categoria"].astype(str).str.lower() if "Categoria" in df.columns else pd.Series(dtype=str)
    core = df[category == "core"]
    thematic = df[category == "thematic"]
    defensive = df[category == "defensive"]

    avg_core_score = core["Score Finale"].mean() if len(core) else np.nan
    avg_thematic_vol = thematic["Volatilità %"].mean() if len(thematic) else np.nan
    avg_defensive_score = defensive["Score Finale"].mean() if len(defensive) else np.nan

    if pd.notna(avg_core_score) and pd.notna(avg_thematic_vol):
        if avg_core_score >= 65 and avg_thematic_vol < 24:
            return "Risk-On"
    if (pd.notna(avg_defensive_score) and avg_defensive_score >= 65) or (
        pd.notna(avg_thematic_vol) and avg_thematic_vol > 28
    ):
        return "Defensive"
    return "Neutral"


def allocation_targets(regime: str) -> dict[str, float]:
    if regime == "Risk-On":
        return {"Core": 60, "Factor": 15, "Thematic": 20, "Defensive": 5, "Satellite": 0}
    if regime == "Defensive":
        return {"Core": 70, "Factor": 10, "Thematic": 5, "Defensive": 15, "Satellite": 0}
    return {"Core": 65, "Factor": 15, "Thematic": 10, "Defensive": 10, "Satellite": 0}


def pick_best_by_category(df: pd.DataFrame, category: str, max_items: int) -> pd.DataFrame:
    if "Categoria" not in df.columns:
        return pd.DataFrame()
    subset = df[df["Categoria"].astype(str).str.lower() == category.lower()].copy()
    subset = subset[pd.notna(subset.get("Score Finale"))]
    subset = subset.sort_values("Score Finale", ascending=False)

    if category.lower() == "thematic" and "Volatilità %" in subset.columns:
        subset = subset[(subset["Volatilità %"].isna()) | (subset["Volatilità %"] <= 30)]

    return subset.head(max_items)


def build_allocation(df: pd.DataFrame, cash_amount: float = 1000) -> tuple[str, pd.DataFrame]:
    regime = market_regime(df)
    targets = allocation_targets(regime)
    selected: list[dict] = []
    category_rules = {"Core": 2, "Factor": 2, "Thematic": 2, "Defensive": 2, "Satellite": 1}

    for category, target_weight in targets.items():
        if target_weight <= 0:
            continue
        picks = pick_best_by_category(df, category, category_rules.get(category, 1))
        if picks.empty:
            continue
        weight_each = target_weight / len(picks)
        for _, row in picks.iterrows():
            selected.append(
                {
                    "Ticker": row.get("Ticker", ""),
                    "Nome ETF": row.get("Nome ETF", ""),
                    "Categoria": row.get("Categoria", ""),
                    "Tema/Area": row.get("Tema/Area", ""),
                    "Score Finale": row.get("Score Finale", np.nan),
                    "Stato": row.get("Stato", ""),
                    "Peso Target %": round(weight_each, 2),
                    "Importo su 1000 EUR": round(cash_amount * weight_each / 100, 2),
                    "Note AI": row.get("Note AI", ""),
                }
            )

    allocation = pd.DataFrame(selected)
    if allocation.empty:
        return regime, allocation

    total_weight = allocation["Peso Target %"].sum()
    if total_weight > 0:
        allocation["Peso Target %"] = allocation["Peso Target %"] / total_weight * 100
        allocation["Peso Target %"] = allocation["Peso Target %"].round(2)
        allocation["Importo su 1000 EUR"] = (cash_amount * allocation["Peso Target %"] / 100).round(2)

    allocation = allocation.sort_values(["Peso Target %", "Score Finale"], ascending=[False, False])
    return regime, allocation


def main() -> None:
    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"File ranking non trovato: {INPUT_FILE}")

    df = pd.read_excel(INPUT_FILE)
    df = df.sort_values("Score Finale", ascending=False, na_position="last")
    regime, allocation = build_allocation(df, CASH_AMOUNT)

    summary = pd.DataFrame(
        [
            {"Parametro": "Market Regime", "Valore": regime},
            {"Parametro": "Importo simulato", "Valore": f"{CASH_AMOUNT} EUR"},
            {"Parametro": "Ultimo aggiornamento", "Valore": now_text()},
            {
                "Parametro": "Nota",
                "Valore": "Allocazione indicativa, non consulenza finanziaria personalizzata",
            },
        ]
    )

    with pd.ExcelWriter(OUTPUT_FILE, engine="openpyxl") as writer:
        allocation.to_excel(writer, sheet_name="Suggested_Allocation", index=False)
        summary.to_excel(writer, sheet_name="Summary", index=False)

    print("Market regime:", regime)
    print("")
    print("Allocazione suggerita:")
    print(allocation.to_string(index=False) if not allocation.empty else "Nessuna allocazione disponibile")
    print("")
    print("File creato:", OUTPUT_FILE)


if __name__ == "__main__":
    main()
