import pandas as pd
from datetime import datetime

RANKING_FILE = "ETF_Intelligence_Agent_UPDATED.xlsx"
ALLOCATION_FILE = "ETF_Allocation_Model.xlsx"
OUTPUT_FILE = "index.html"

ranking = pd.read_excel(RANKING_FILE)
ranking = ranking.sort_values("Score Finale", ascending=False, na_position="last")

allocation = pd.read_excel(ALLOCATION_FILE, sheet_name="Suggested_Allocation")
summary = pd.read_excel(ALLOCATION_FILE, sheet_name="Summary")

top = ranking.head(20)
best = top.iloc[0]

def safe(value):
    if pd.isna(value):
        return ""
    return str(value)

def get_summary_value(key):
    row = summary[summary["Parametro"] == key]
    if len(row) == 0:
        return ""
    return row.iloc[0]["Valore"]

market_regime = get_summary_value("Market Regime")

ranking_rows = ""

for _, r in top.iterrows():
    ranking_rows += f"""
    <tr>
        <td>{safe(r.get("Ticker"))}</td>
        <td>{safe(r.get("Nome ETF"))}</td>
        <td>{safe(r.get("Tema/Area"))}</td>
        <td><strong>{safe(r.get("Score Finale"))}</strong></td>
        <td>{safe(r.get("Stato"))}</td>
        <td>{safe(r.get("Rendimento 12M %"))}%</td>
        <td>{safe(r.get("Volatilità %"))}%</td>
        <td>{safe(r.get("Max Drawdown %"))}%</td>
        <td>{safe(r.get("Note AI"))}</td>
    </tr>
    """

allocation_rows = ""

for _, r in allocation.iterrows():
    allocation_rows += f"""
    <tr>
        <td>{safe(r.get("Ticker"))}</td>
        <td>{safe(r.get("Nome ETF"))}</td>
        <td>{safe(r.get("Categoria"))}</td>
        <td>{safe(r.get("Tema/Area"))}</td>
        <td><strong>{safe(r.get("Peso Target %"))}%</strong></td>
        <td>{safe(r.get("Importo su 1000 EUR"))} €</td>
        <td>{safe(r.get("Score Finale"))}</td>
        <td>{safe(r.get("Note AI"))}</td>
    </tr>
    """

html = f"""
<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ETF Intelligence Dashboard</title>

<style>
body {{
    font-family: Arial, sans-serif;
    background: #f4f6f8;
    padding: 20px;
    color: #111827;
}}

h1 {{
    margin-bottom: 5px;
}}

.subtitle {{
    color: #6b7280;
    margin-bottom: 25px;
}}

.grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
    gap: 16px;
}}

.card {{
    background: white;
    padding: 18px;
    border-radius: 14px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    margin-bottom: 20px;
}}

.badge {{
    display: inline-block;
    padding: 8px 12px;
    border-radius: 999px;
    background: #e0f2fe;
    font-weight: bold;
}}

.badge-green {{
    background: #dcfce7;
}}

.badge-yellow {{
    background: #fef9c3;
}}

.badge-red {{
    background: #fee2e2;
}}

table {{
    width: 100%;
    border-collapse: collapse;
    background: white;
}}

th, td {{
    padding: 10px;
    border-bottom: 1px solid #e5e7eb;
    text-align: left;
    font-size: 14px;
    vertical-align: top;
}}

th {{
    background: #111827;
    color: white;
}}

tr:hover {{
    background: #f9fafb;
}}

.footer {{
    margin-top: 25px;
    color: #6b7280;
    font-size: 13px;
}}

@media screen and (max-width: 768px) {{
    body {{
        padding: 10px;
    }}

    table {{
        display: block;
        overflow-x: auto;
        white-space: nowrap;
    }}
}}
</style>
</head>

<body>

<h1>ETF Intelligence Dashboard</h1>
<div class="subtitle">
Aggiornato il {datetime.now().strftime("%d/%m/%Y %H:%M")}
</div>

<div class="grid">
    <div class="card">
        <h2>Market Regime</h2>
        <p class="badge">{market_regime}</p>
    </div>

    <div class="card">
        <h2>Miglior ETF oggi</h2>
        <p class="badge badge-green">
            {safe(best.get("Ticker"))} - {safe(best.get("Nome ETF"))} | Score {safe(best.get("Score Finale"))}
        </p>
        <p>{safe(best.get("Note AI"))}</p>
    </div>
</div>

<div class="card">
    <h2>Allocazione suggerita per nuovi 1000 €</h2>
    <p>
        Questa non è una raccomandazione automatica di acquisto, ma una proposta di distribuzione basata su score, categoria, rischio e contesto.
    </p>
    <table>
        <tr>
            <th>Ticker</th>
            <th>ETF</th>
            <th>Categoria</th>
            <th>Tema</th>
            <th>Peso</th>
            <th>Importo</th>
            <th>Score</th>
            <th>Nota AI</th>
        </tr>
        {allocation_rows}
    </table>
</div>

<div class="card">
    <h2>Top ETF Ranking</h2>
    <table>
        <tr>
            <th>Ticker</th>
            <th>ETF</th>
            <th>Tema</th>
            <th>Score</th>
            <th>Stato</th>
            <th>12M</th>
            <th>Volatilità</th>
            <th>Drawdown</th>
            <th>Nota AI</th>
        </tr>
        {ranking_rows}
    </table>
</div>

<div class="footer">
    Report informativo. Non costituisce consulenza finanziaria personalizzata.
</div>

</body>
</html>
"""

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    f.write(html)

print("Dashboard creata:", OUTPUT_FILE)
