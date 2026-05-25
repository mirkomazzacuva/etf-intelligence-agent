import pandas as pd
from datetime import datetime

INPUT_FILE = "ETF_Intelligence_Agent_UPDATED.xlsx"
OUTPUT_FILE = "index.html"

df = pd.read_excel(INPUT_FILE)
df = df.sort_values("Score Finale", ascending=False, na_position="last")

top = df.head(20)
best = top.iloc[0]

def safe(value):
    if pd.isna(value):
        return ""
    return str(value)

rows = ""

for _, r in top.iterrows():
    score = r.get("Score Finale", "")
    rows += f"""
    <tr>
        <td>{safe(r.get("Ticker"))}</td>
        <td>{safe(r.get("Nome ETF"))}</td>
        <td>{safe(r.get("Tema/Area"))}</td>
        <td><strong>{safe(score)}</strong></td>
        <td>{safe(r.get("Stato"))}</td>
        <td>{safe(r.get("Rendimento 12M %"))}%</td>
        <td>{safe(r.get("Volatilità %"))}%</td>
        <td>{safe(r.get("Max Drawdown %"))}%</td>
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

table {{
    width: 100%;
    border-collapse: collapse;
    background: white;
    overflow-x: auto;
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

<div class="card">
    <h2>Miglior ETF oggi</h2>
    <p class="badge">
        {safe(best.get("Ticker"))} - {safe(best.get("Nome ETF"))} | Score {safe(best.get("Score Finale"))}
    </p>
    <p>{safe(best.get("Note AI"))}</p>
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
        {rows}
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
