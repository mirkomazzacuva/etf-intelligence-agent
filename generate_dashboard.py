import pandas as pd

INPUT = "ETF_Intelligence_Agent_UPDATED.xlsx"
OUTPUT = "index.html"

df = pd.read_excel(INPUT)

top = df.sort_values("Score Finale", ascending=False).head(20)

rows = ""
for _, r in top.iterrows():
    score = r["Score Finale"]
    stato = r["Stato"]
    note = r.get("Note AI", "")
    rows += f"""
    <tr>
      <td>{r['Ticker']}</td>
      <td>{r['Nome ETF']}</td>
      <td>{r.get('Tema/Area','')}</td>
      <td><strong>{score}</strong></td>
      <td>{stato}</td>
      <td>{r.get('Rendimento 12M %','')}%</td>
      <td>{r.get('Volatilità %','')}%</td>
      <td>{r.get('Max Drawdown %','')}%</td>
      <td>{note}</td>
    </tr>
    """

html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>ETF Intelligence Dashboard</title>
<style>
body {{
  font-family: Arial, sans-serif;
  background: #f4f6f8;
  padding: 24px;
}}
h1 {{
  color: #111827;
}}
.card {{
  background: white;
  padding: 18px;
  border-radius: 14px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
  margin-bottom: 20px;
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
}}
th {{
  background: #111827;
  color: white;
}}
tr:hover {{
  background: #f9fafb;
}}
.badge {{
  display: inline-block;
  padding: 6px 10px;
  border-radius: 999px;
  background: #e0f2fe;
}}
</style>
</head>
<body>

<h1>ETF Intelligence Dashboard</h1>

<div class="card">
  <h2>Miglior ETF oggi</h2>
  <p class="badge">{top.iloc[0]['Ticker']} - {top.iloc[0]['Nome ETF']} | Score {top.iloc[0]['Score Finale']}</p>
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
      <th>Vol</th>
      <th>Drawdown</th>
      <th>Nota AI</th>
    </tr>
    {rows}
  </table>
</div>

</body>
</html>
"""

with open(OUTPUT, "w", encoding="utf-8") as f:
    f.write(html)

print("Dashboard creata:", OUTPUT)
