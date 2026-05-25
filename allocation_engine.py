import pandas as pd
import numpy as np

INPUT_FILE = "ETF_Intelligence_Agent_UPDATED.xlsx"
OUTPUT_FILE = "ETF_Allocation_Model.xlsx"
CASH_AMOUNT = 1000

df = pd.read_excel(INPUT_FILE)
df = df.sort_values("Score Finale", ascending=False, na_position="last")

def clean_text(x):
    return str(x).lower() if pd.notna(x) else ""

def market_regime(df):
    core = df[df["Categoria"].astype(str).str.lower() == "core"]
    thematic = df[df["Categoria"].astype(str).str.lower() == "thematic"]
    defensive = df[df["Categoria"].astype(str).str.lower() == "defensive"]

    avg_core_score = core["Score Finale"].mean()
    avg_thematic_vol = thematic["Volatilità %"].mean()
    avg_defensive_score = defensive["Score Finale"].mean()

    if avg_core_score >= 65 and avg_thematic_vol < 24:
        return "Risk-On"
    elif avg_defensive_score >= 65 or avg_thematic_vol > 28:
        return "Defensive"
    else:
        return "Neutral"

def allocation_targets(regime):
    if regime == "Risk-On":
        return {
            "Core": 60,
            "Factor": 15,
            "Thematic": 20,
            "Defensive": 5,
            "Satellite": 0
        }
    elif regime == "Defensive":
        return {
            "Core": 70,
            "Factor": 10,
            "Thematic": 5,
            "Defensive": 15,
            "Satellite": 0
        }
    else:
        return {
            "Core": 65,
            "Factor": 15,
            "Thematic": 10,
            "Defensive": 10,
            "Satellite": 0
        }

def pick_best_by_category(df, category, max_items):
    subset = df[df["Categoria"].astype(str).str.lower() == category.lower()].copy()
    subset = subset[pd.notna(subset["Score Finale"])]
    subset = subset.sort_values("Score Finale", ascending=False)

    if category.lower() == "thematic":
        # Evita eccessiva concentrazione su tematici troppo rischiosi
        subset = subset[subset["Volatilità %"] <= 30]

    return subset.head(max_items)

def build_allocation(df, cash_amount=1000):
    regime = market_regime(df)
    targets = allocation_targets(regime)

    selected = []

    category_rules = {
        "Core": 2,
        "Factor": 2,
        "Thematic": 2,
        "Defensive": 2,
        "Satellite": 1
    }

    for category, target_weight in targets.items():
        if target_weight <= 0:
            continue

        picks = pick_best_by_category(df, category, category_rules.get(category, 1))

        if len(picks) == 0:
            continue

        weight_each = target_weight / len(picks)

        for _, row in picks.iterrows():
            selected.append({
                "Ticker": row["Ticker"],
                "Nome ETF": row["Nome ETF"],
                "Categoria": row["Categoria"],
                "Tema/Area": row.get("Tema/Area", ""),
                "Score Finale": row["Score Finale"],
                "Stato": row["Stato"],
                "Peso Target %": round(weight_each, 2),
                "Importo su 1000 EUR": round(cash_amount * weight_each / 100, 2),
                "Note AI": row.get("Note AI", "")
            })

    allocation = pd.DataFrame(selected)

    # Normalizzazione se per qualche categoria mancano ETF
    total_weight = allocation["Peso Target %"].sum()

    if total_weight > 0:
        allocation["Peso Target %"] = allocation["Peso Target %"] / total_weight * 100
        allocation["Peso Target %"] = allocation["Peso Target %"].round(2)
        allocation["Importo su 1000 EUR"] = (cash_amount * allocation["Peso Target %"] / 100).round(2)

    allocation = allocation.sort_values("Peso Target %", ascending=False)

    return regime, allocation

regime, allocation = build_allocation(df, CASH_AMOUNT)

summary = pd.DataFrame([
    {"Parametro": "Market Regime", "Valore": regime},
    {"Parametro": "Importo simulato", "Valore": f"{CASH_AMOUNT} EUR"},
    {"Parametro": "Nota", "Valore": "Allocazione indicativa, non consulenza finanziaria personalizzata"}
])

with pd.ExcelWriter(OUTPUT_FILE, engine="openpyxl") as writer:
    allocation.to_excel(writer, sheet_name="Suggested_Allocation", index=False)
    summary.to_excel(writer, sheet_name="Summary", index=False)

print("Market regime:", regime)
print("")
print("Allocazione suggerita:")
print(allocation.to_string(index=False))
print("")
print("File creato:", OUTPUT_FILE)
