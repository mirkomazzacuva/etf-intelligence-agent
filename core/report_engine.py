from __future__ import annotations

from datetime import datetime
from html import escape
from pathlib import Path

import pandas as pd


def format_number(value: object, digits: int = 2) -> str:
    try:
        if pd.isna(value):
            return ""
        return f"{float(value):,.{digits}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:  # noqa: BLE001
        return str(value)


def compact_table(df: pd.DataFrame, columns: list[str], limit: int = 10) -> str:
    if df is None or df.empty:
        return "<p class='muted'>Nessun dato disponibile.</p>"
    cols = [col for col in columns if col in df.columns]
    if not cols:
        return "<p class='muted'>Colonne non disponibili.</p>"
    rows = []
    for _, row in df.head(limit).iterrows():
        tds = "".join(f"<td>{escape(format_number(row.get(col)) if isinstance(row.get(col), (float, int)) else str(row.get(col, '')))}</td>" for col in cols)
        rows.append(f"<tr>{tds}</tr>")
    th = "".join(f"<th>{escape(col)}</th>" for col in cols)
    return f"<table><thead><tr>{th}</tr></thead><tbody>{''.join(rows)}</tbody></table>"


def build_text_report(ranking: pd.DataFrame, allocation: pd.DataFrame, watchlist: pd.DataFrame | None = None) -> str:
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    lines = [
        "AlphaForge Intelligence - Daily Report",
        f"Aggiornato il {now}",
        "",
        "Report informativo. Non costituisce consulenza finanziaria personalizzata.",
        "",
    ]
    if ranking is not None and not ranking.empty:
        best = ranking.sort_values("Score Finale", ascending=False, na_position="last").iloc[0]
        lines += [
            f"Miglior ETF: {best.get('Ticker', '')} - score {best.get('Score Finale', '')}",
            f"Stato: {best.get('Stato', '')}",
            f"Nota: {best.get('Note AI', '')}",
            "",
            "Top ETF:",
        ]
        for _, row in ranking.head(5).iterrows():
            lines.append(f"- {row.get('Ticker', '')}: score {row.get('Score Finale', '')}, stato {row.get('Stato', '')}")
    if allocation is not None and not allocation.empty:
        lines += ["", "Allocazione suggerita su 1000 EUR:"]
        for _, row in allocation.head(8).iterrows():
            amount = row.get("Importo su 1000 EUR", row.get("Importo Indicativo EUR", ""))
            lines.append(f"- {row.get('Ticker', '')}: {row.get('Peso Target %', '')}% - {amount} EUR")
    if watchlist is not None and not watchlist.empty:
        lines += ["", "Watchlist azioni/strumenti:"]
        for _, row in watchlist.head(5).iterrows():
            lines.append(f"- {row.get('Ticker', '')}: score {row.get('Score Finale', '')}, stato {row.get('Stato', '')}")
    lines += ["", "Usare sempre size, diversificazione, costi, fiscalità, liquidità e profilo personale come filtri finali."]
    return "\n".join(lines)


def render_dashboard_html(
    ranking: pd.DataFrame,
    allocation: pd.DataFrame,
    status: dict,
    watchlist: pd.DataFrame | None,
    output: Path,
) -> None:
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    best = ranking.sort_values("Score Finale", ascending=False, na_position="last").iloc[0] if ranking is not None and not ranking.empty else {}
    best_watch = watchlist.sort_values("Score Finale", ascending=False, na_position="last").iloc[0] if watchlist is not None and not watchlist.empty else {}
    status_text = status.get("status", "unknown") if isinstance(status, dict) else "unknown"
    html = f"""<!doctype html>
<html lang="it">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AlphaForge Intelligence Dashboard</title>
<style>
:root {{ --bg:#0b1020; --panel:#111a33; --card:#162341; --text:#eef3ff; --muted:#9fb0d0; --accent:#70e1c8; --danger:#ff8b8b; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; font-family:Inter,system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif; background:linear-gradient(135deg,#070b16,#101a35 45%,#07101d); color:var(--text); }}
.container {{ max-width:1180px; margin:0 auto; padding:32px 18px 48px; }}
.hero {{ padding:28px; border:1px solid rgba(255,255,255,.12); border-radius:24px; background:rgba(17,26,51,.86); box-shadow:0 18px 60px rgba(0,0,0,.35); }}
h1 {{ margin:0 0 8px; font-size:clamp(30px,5vw,54px); letter-spacing:-.04em; }}
.subtitle {{ color:var(--muted); font-size:17px; max-width:760px; line-height:1.55; }}
.grid {{ display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:14px; margin:22px 0; }}
.card {{ background:rgba(22,35,65,.92); border:1px solid rgba(255,255,255,.10); border-radius:20px; padding:18px; }}
.label {{ color:var(--muted); font-size:12px; text-transform:uppercase; letter-spacing:.08em; }}
.value {{ margin-top:8px; font-size:24px; font-weight:800; }}
section {{ margin-top:26px; }}
h2 {{ margin:0 0 12px; font-size:24px; }}
table {{ width:100%; border-collapse:collapse; overflow:hidden; border-radius:18px; background:rgba(17,26,51,.72); }}
th,td {{ padding:11px 10px; border-bottom:1px solid rgba(255,255,255,.08); text-align:left; vertical-align:top; }}
th {{ color:#cbd7f4; background:rgba(255,255,255,.06); font-size:12px; text-transform:uppercase; letter-spacing:.06em; }}
td {{ color:#f5f7ff; font-size:14px; }}
.muted {{ color:var(--muted); }}
.badge {{ display:inline-block; padding:6px 10px; border-radius:999px; background:rgba(112,225,200,.16); color:var(--accent); font-weight:700; }}
.disclaimer {{ color:var(--muted); line-height:1.6; font-size:13px; }}
@media (max-width:900px) {{ .grid {{ grid-template-columns:repeat(2,minmax(0,1fr)); }} table {{ display:block; overflow-x:auto; }} }}
@media (max-width:560px) {{ .grid {{ grid-template-columns:1fr; }} .hero {{ padding:20px; }} }}
</style>
</head>
<body>
<div class="container">
  <div class="hero">
    <span class="badge">AlphaForge v2</span>
    <h1>ETF & Stock Intelligence Dashboard</h1>
    <p class="subtitle">Ranking ETF, allocazione, watchlist azioni e segnali di rischio in una dashboard pubblica semplice da leggere.</p>
    <div class="grid">
      <div class="card"><div class="label">Aggiornato</div><div class="value">{escape(now)}</div></div>
      <div class="card"><div class="label">Stato update</div><div class="value">{escape(str(status_text))}</div></div>
      <div class="card"><div class="label">Miglior ETF</div><div class="value">{escape(str(best.get('Ticker', 'n/d')))}</div></div>
      <div class="card"><div class="label">Top Watchlist</div><div class="value">{escape(str(best_watch.get('Ticker', 'n/d')))}</div></div>
    </div>
  </div>
  <section><h2>Allocazione suggerita</h2>{compact_table(allocation, ['Ticker','Nome ETF','Categoria','Peso Target %','Importo su 1000 EUR','Score Finale','Stato'], 10)}</section>
  <section><h2>Top ETF Ranking</h2>{compact_table(ranking, ['Ticker','Nome ETF','Categoria','Tema/Area','Score Finale','Stato','Rendimento 12M %','Volatilità %','Max Drawdown %','Sharpe'], 12)}</section>
  <section><h2>Watchlist azioni e strumenti</h2>{compact_table(watchlist if watchlist is not None else pd.DataFrame(), ['Ticker','Nome','Tipo','Score Finale','Stato','Trend','Rendimento 3M %','P/E','Note AI'], 10)}</section>
  <section><h2>Lettura prudente</h2><p class="disclaimer">Gli score sono indicatori informativi e non sono segnali automatici di acquisto o vendita. Prima di qualsiasi operazione verificare costi, spread, fiscalità, liquidità, dimensione posizione, rischio cambio e coerenza con il proprio profilo.</p></section>
</div>
</body>
</html>"""
    output.write_text(html, encoding="utf-8")
