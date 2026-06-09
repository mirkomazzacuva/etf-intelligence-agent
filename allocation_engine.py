from __future__ import annotations

import pandas as pd

from core.config import ALLOCATION_FILE, RANKING_FILE

TARGET_BY_CATEGORY = {
    "Core": 55.0,
    "Defensive": 20.0,
    "Factor": 15.0,
    "Thematic": 10.0,
    "Custom": 0.0,
}


def build_allocation(amount: float = 1000.0) -> tuple[pd.DataFrame, pd.DataFrame]:
    if not RANKING_FILE.exists():
        raise FileNotFoundError(f"File ranking non trovato: {RANKING_FILE}")
    ranking = pd.read_excel(RANKING_FILE)
    if ranking.empty:
        raise RuntimeError("Ranking vuoto")
    if "Categoria" not in ranking.columns:
        ranking["Categoria"] = "Core"
    ranking = ranking.sort_values("Score Finale", ascending=False, na_position="last")

    selected_rows = []
    for category, target in TARGET_BY_CATEGORY.items():
        if target <= 0:
            continue
        subset = ranking[ranking["Categoria"].astype(str).str.lower() == category.lower()].head(3)
        if subset.empty:
            continue
        weight_each = target / len(subset)
        for _, row in subset.iterrows():
            out = row.to_dict()
            out["Peso Target %"] = round(weight_each, 2)
            selected_rows.append(out)

    if not selected_rows:
        selected_rows = ranking.head(8).to_dict("records")
        for row in selected_rows:
            row["Peso Target %"] = round(100 / len(selected_rows), 2)

    alloc = pd.DataFrame(selected_rows)
    alloc = alloc.drop_duplicates(subset=["Ticker"]).copy()
    alloc["Peso Target %"] = pd.to_numeric(alloc["Peso Target %"], errors="coerce").fillna(0)
    total = alloc["Peso Target %"].sum()
    if total <= 0:
        alloc["Peso Target %"] = 100 / len(alloc)
    else:
        alloc["Peso Target %"] = alloc["Peso Target %"] / total * 100
    alloc["Peso Target %"] = alloc["Peso Target %"].round(2)
    alloc["Importo su 1000 EUR"] = (amount * alloc["Peso Target %"] / 100).round(2)

    cols = [
        "Ticker", "Nome ETF", "Categoria", "Tema/Area", "Peso Target %", "Importo su 1000 EUR",
        "Score Finale", "Stato", "Volatilità %", "Max Drawdown %", "Note AI",
    ]
    alloc = alloc[[col for col in cols if col in alloc.columns]]

    market_regime = "Neutral"
    avg_score = pd.to_numeric(ranking.get("Score Finale"), errors="coerce").mean()
    avg_mom = pd.to_numeric(ranking.get("ETF Momentum Score"), errors="coerce").mean()
    if avg_score >= 72 and avg_mom >= 60:
        market_regime = "Risk On"
    elif avg_score < 55 or avg_mom < 45:
        market_regime = "Risk Off"

    summary = pd.DataFrame(
        [
            {"Parametro": "Market Regime", "Valore": market_regime},
            {"Parametro": "ETF analizzati", "Valore": len(ranking)},
            {"Parametro": "ETF in allocazione", "Valore": len(alloc)},
            {"Parametro": "Score medio", "Valore": round(float(avg_score), 2) if pd.notna(avg_score) else ""},
            {"Parametro": "Nota", "Valore": "Allocazione informativa su 1000 EUR, non consulenza personalizzata."},
        ]
    )
    with pd.ExcelWriter(ALLOCATION_FILE, engine="openpyxl") as writer:
        alloc.to_excel(writer, sheet_name="Suggested_Allocation", index=False)
        summary.to_excel(writer, sheet_name="Summary", index=False)
    print(f"Creato {ALLOCATION_FILE} con {len(alloc)} righe")
    return alloc, summary


if __name__ == "__main__":
    build_allocation()
