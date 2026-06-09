from __future__ import annotations

from datetime import datetime
from html import escape
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

APP_TZ = ZoneInfo("Europe/Rome")
RANKING_FILE = Path("ETF_Intelligence_Agent_UPDATED.xlsx")
ALLOCATION_FILE = Path("ETF_Allocation_Model.xlsx")
OUTPUT_FILE = Path("index.html")


def safe(value: object) -> str:
    if pd.isna(value):
        return ""
    return escape(str(value))


def get_summary_value(summary: pd.DataFrame, key: str) -> str:
    row = summary[summary["Parametro"] == key]
    if len(row) == 0:
        return ""
    return safe(row.iloc[0]["Valore"])


def badge(status: object) -> str:
    text = safe(status)
    return f'<span class="badge">{text}</span>'


def table_rows(df: pd.DataFrame, columns: list[str]) -> str:
    rows: list[str] = []
    for _, row in df.iterrows():
        cells = "".join(f"<td>{safe(row.get(col, ''))}</td>" for col in columns)
        rows.append(f"<tr>{cells}</tr>")
    return "\n".join(rows)


def main() -> None:
    ranking = pd.read_excel(RANKING_FILE).sort_values("Score Finale", ascending=False, na_position="last")
    allocation = pd.read_excel(ALLOCATION_FILE, sheet_name="Suggested_Allocation")
    summary = pd.read_excel(ALLOCATION_FILE, sheet_name="Summary")

    top = ranking.head(20)
    best = top.iloc[0] if not top.empty else {}
    market_regime = get_summary_value(summary, "Market Regime")
    updated_at = datetime.now(APP_TZ).strftime("%d/%m/%Y %H:%M")

    allocation_cols = ["Ticker", "Nome ETF", "Categoria", "Tema/Area", "Peso Target %", "Importo su 1000 EUR", "Score Finale", "Note AI"]
    ranking_cols = ["Ticker", "Nome ETF", "Tema/Area", "Score Finale", "Stato", "Rendimento 12M %", "Volatilità %", "Max Drawdown %", "Note AI"]

    html = f"""
<!doctype html>
<html lang="it">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>ETF Intelligence Dashboard</title>
  <style>
    body {{ font-family: Inter, Arial, sans-serif; margin: 0; background: #0f172a; color: #e5e7eb; }}
    main {{ max-width: 1180px; margin: 0 auto; padding: 32px 18px 60px; }}
    .hero {{ background: linear-gradient(135deg, #111827, #1e293b); border: 1px solid #334155; border-radius: 24px; padding: 28px; margin-bottom: 22px; }}
    h1 {{ margin: 0 0 8px; font-size: 34px; }}
    h2 {{ margin-top: 34px; }}
    .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 14px; margin-top: 18px; }}
    .card {{ background: #111827; border: 1px solid #334155; border-radius: 18px; padding: 18px; }}
    .label {{ color: #94a3b8; font-size: 13px; margin-bottom: 8px; }}
    .value {{ font-size: 22px; font-weight: 750; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 12px; background: #111827; border-radius: 16px; overflow: hidden; }}
    th, td {{ border-bottom: 1px solid #263449; padding: 11px 10px; text-align: left; vertical-align: top; }}
    th {{ color: #cbd5e1; background: #1e293b; font-size: 13px; }}
    td {{ color: #e5e7eb; font-size: 13px; }}
    .muted {{ color: #94a3b8; }}
    .badge {{ display: inline-block; padding: 5px 9px; border-radius: 999px; background: #1d4ed8; color: white; font-size: 12px; }}
    .disclaimer {{ margin-top: 28px; padding: 16px; border-radius: 14px; background: #1e293b; color: #cbd5e1; }}
  </style>
</head>
<body>
<main>
  <section class="hero">
    <div class="muted">Aggiornato il {safe(updated_at)}</div>
    <h1>ETF Intelligence Dashboard</h1>
    <p class="muted">Ranking ETF, allocazione indicativa e lettura prudente del rischio.</p>
    <div class="cards">
      <div class="card"><div class="label">Market Regime</div><div class="value">{market_regime}</div></div>
      <div class="card"><div class="label">Miglior ETF</div><div class="value">{safe(best.get('Ticker', ''))}</div></div>
      <div class="card"><div class="label">Score migliore</div><div class="value">{safe(best.get('Score Finale', ''))}</div></div>
      <div class="card"><div class="label">Stato</div><div class="value">{badge(best.get('Stato', ''))}</div></div>
    </div>
  </section>

  <h2>Allocazione suggerita per nuovi 1000 EUR</h2>
  <p class="muted">Non è una raccomandazione automatica di acquisto: serve per capire distribuzione, rischio e ruolo degli ETF.</p>
  <table>
    <thead><tr>{''.join(f'<th>{safe(col)}</th>' for col in allocation_cols)}</tr></thead>
    <tbody>{table_rows(allocation, allocation_cols)}</tbody>
  </table>

  <h2>Top ETF Ranking</h2>
  <table>
    <thead><tr>{''.join(f'<th>{safe(col)}</th>' for col in ranking_cols)}</tr></thead>
    <tbody>{table_rows(top, ranking_cols)}</tbody>
  </table>

  <div class="disclaimer">Report informativo. Non costituisce consulenza finanziaria personalizzata.</div>
</main>
</body>
</html>
"""
    OUTPUT_FILE.write_text(html, encoding="utf-8")
    print("Dashboard creata:", OUTPUT_FILE)


if __name__ == "__main__":
    main()
