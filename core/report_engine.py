from __future__ import annotations

from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any

import pandas as pd


def format_number(value: object, digits: int = 2) -> str:
    try:
        if pd.isna(value):
            return ""
        if isinstance(value, (float, int)):
            return f"{float(value):,.{digits}f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return str(value)
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
        cells = []
        for col in cols:
            value = row.get(col, "")
            txt = format_number(value) if isinstance(value, (float, int)) else str(value)
            css = " class='long'" if col in {"Note AI", "Trigger Monitoraggio", "Azione Suggerita", "Scenario Base"} else ""
            cells.append(f"<td{css}>{escape(txt)}</td>")
        rows.append(f"<tr>{''.join(cells)}</tr>")
    th = "".join(f"<th>{escape(col)}</th>" for col in cols)
    return f"<table><thead><tr>{th}</tr></thead><tbody>{''.join(rows)}</tbody></table>"


def _best_row(df: pd.DataFrame, col: str) -> dict[str, Any]:
    if df is None or df.empty or col not in df.columns:
        return {}
    try:
        return df.sort_values(col, ascending=False, na_position="last").iloc[0].to_dict()
    except Exception:  # noqa: BLE001
        return {}


def build_text_report(
    ranking: pd.DataFrame,
    allocation: pd.DataFrame,
    watchlist: pd.DataFrame | None = None,
    insights: pd.DataFrame | None = None,
) -> str:
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    lines = [
        "AlphaForge Intelligence v3 - Daily Report",
        f"Aggiornato il {now}",
        "",
        "Report informativo. Non costituisce consulenza finanziaria personalizzata.",
        "",
    ]
    if ranking is not None and not ranking.empty:
        best = _best_row(ranking, "Score Finale")
        lines += [
            f"Miglior ETF: {best.get('Ticker', '')} - score {best.get('Score Finale', '')}",
            f"Stato: {best.get('Stato', '')}",
            f"Entry zone: {best.get('Entry Zone', '')}",
            f"Nota: {best.get('Note AI', '')}",
            "",
            "Top ETF:",
        ]
        for _, row in ranking.head(5).iterrows():
            lines.append(f"- {row.get('Ticker', '')}: score {row.get('Score Finale', '')}, priority {row.get('Priority Score', '')}, stato {row.get('Stato', '')}")
    if allocation is not None and not allocation.empty:
        lines += ["", "Allocazione suggerita su 1000 EUR:"]
        for _, row in allocation.head(8).iterrows():
            amount = row.get("Importo su 1000 EUR", row.get("Importo Indicativo EUR", ""))
            lines.append(f"- {row.get('Ticker', '')}: {row.get('Peso Target %', '')}% - {amount} EUR")
    if watchlist is not None and not watchlist.empty:
        lines += ["", "Watchlist azioni/strumenti:"]
        for _, row in watchlist.head(5).iterrows():
            lines.append(f"- {row.get('Ticker', '')}: score {row.get('Score Finale', '')}, action {row.get('Azione Suggerita', row.get('Stato', ''))}")
    if insights is not None and not insights.empty:
        lines += ["", "Priorità AlphaForge:"]
        for _, row in insights.head(5).iterrows():
            lines.append(f"- {row.get('Ticker', '')}: priority {row.get('Priority Score', '')}, azione {row.get('Azione Suggerita', '')}, trigger {row.get('Trigger Monitoraggio', '')}")
    lines += ["", "Usare sempre size, diversificazione, costi, fiscalità, liquidità e profilo personale come filtri finali."]
    return "\n".join(lines)


def render_dashboard_html(
    ranking: pd.DataFrame,
    allocation: pd.DataFrame,
    status: dict,
    watchlist: pd.DataFrame | None,
    output: Path,
    insights: pd.DataFrame | None = None,
) -> None:
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    best = _best_row(ranking, "Score Finale")
    best_watch = _best_row(watchlist if watchlist is not None else pd.DataFrame(), "Score Finale")
    best_priority = _best_row(insights if insights is not None else pd.DataFrame(), "Priority Score")
    status_text = status.get("status", "unknown") if isinstance(status, dict) else "unknown"
    status_class = "ok" if status_text == "success" else "warn" if status_text == "running" else "bad" if status_text == "failed" else ""
    html = f"""<!doctype html>
<html lang="it">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AlphaForge Intelligence Dashboard</title>
<style>
:root {{ --bg:#07101f; --panel:#101a33; --card:#152340; --text:#eef3ff; --muted:#9fb0d0; --accent:#70e1c8; --accent2:#8fb7ff; --danger:#ff8b8b; --warning:#ffd37a; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; font-family:Inter,system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif; background:radial-gradient(circle at top left,#17284f,#07101f 45%,#050813); color:var(--text); }}
.container {{ max-width:1240px; margin:0 auto; padding:32px 18px 56px; }}
.hero {{ padding:30px; border:1px solid rgba(255,255,255,.12); border-radius:28px; background:linear-gradient(135deg,rgba(18,30,58,.92),rgba(12,18,35,.88)); box-shadow:0 20px 70px rgba(0,0,0,.38); }}
h1 {{ margin:0 0 8px; font-size:clamp(32px,5vw,58px); letter-spacing:-.045em; }}
.subtitle {{ color:var(--muted); font-size:17px; max-width:820px; line-height:1.55; }}
.grid {{ display:grid; grid-template-columns:repeat(5,minmax(0,1fr)); gap:14px; margin:24px 0 6px; }}
.card {{ background:rgba(21,35,64,.94); border:1px solid rgba(255,255,255,.10); border-radius:20px; padding:18px; }}
.label {{ color:var(--muted); font-size:12px; text-transform:uppercase; letter-spacing:.08em; }}
.value {{ margin-top:8px; font-size:23px; font-weight:850; }}
.ok {{ color:var(--accent); }} .warn {{ color:var(--warning); }} .bad {{ color:var(--danger); }}
section {{ margin-top:28px; }}
h2 {{ margin:0 0 12px; font-size:24px; }}
table {{ width:100%; border-collapse:collapse; overflow:hidden; border-radius:18px; background:rgba(17,26,51,.72); }}
th,td {{ padding:11px 10px; border-bottom:1px solid rgba(255,255,255,.08); text-align:left; vertical-align:top; }}
th {{ color:#cbd7f4; background:rgba(255,255,255,.06); font-size:12px; text-transform:uppercase; letter-spacing:.06em; }}
td {{ color:#f5f7ff; font-size:14px; }}
td.long {{ min-width:260px; color:#dfe7ff; }}
.muted {{ color:var(--muted); }}
.badge {{ display:inline-block; padding:6px 10px; border-radius:999px; background:rgba(112,225,200,.16); color:var(--accent); font-weight:800; }}
.notegrid {{ display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:14px; }}
.note {{ background:rgba(255,255,255,.055); border:1px solid rgba(255,255,255,.08); border-radius:18px; padding:16px; color:#dce7ff; line-height:1.55; }}
.disclaimer {{ color:var(--muted); line-height:1.6; font-size:13px; }}
@media (max-width:980px) {{ .grid {{ grid-template-columns:repeat(2,minmax(0,1fr)); }} .notegrid {{ grid-template-columns:1fr; }} table {{ display:block; overflow-x:auto; }} }}
@media (max-width:560px) {{ .grid {{ grid-template-columns:1fr; }} .hero {{ padding:20px; }} }}
</style>
</head>
<body>
<div class="container">
  <div class="hero">
    <span class="badge">AlphaForge v3</span>
    <h1>ETF & Stock Intelligence Dashboard</h1>
    <p class="subtitle">Ranking ETF, allocazione, watchlist azioni, priority score, entry zone e scenari pratici in una dashboard pubblica semplice da leggere.</p>
    <div class="grid">
      <div class="card"><div class="label">Aggiornato</div><div class="value">{escape(now)}</div></div>
      <div class="card"><div class="label">Stato update</div><div class="value {status_class}">{escape(str(status_text))}</div></div>
      <div class="card"><div class="label">Miglior ETF</div><div class="value">{escape(str(best.get('Ticker', 'n/d')))}</div></div>
      <div class="card"><div class="label">Top Watchlist</div><div class="value">{escape(str(best_watch.get('Ticker', 'n/d')))}</div></div>
      <div class="card"><div class="label">Priorità</div><div class="value">{escape(str(best_priority.get('Ticker', 'n/d')))}</div></div>
    </div>
  </div>
  <section><h2>Priorità operative AlphaForge</h2>{compact_table(insights if insights is not None else pd.DataFrame(), ['Ticker','Tipo','Score Finale','Priority Score','Azione Suggerita','Entry Zone','Risk Flag','Trigger Monitoraggio'], 12)}</section>
  <section><h2>Allocazione suggerita</h2>{compact_table(allocation, ['Ticker','Nome ETF','Categoria','Peso Target %','Importo su 1000 EUR','Score Finale','Stato'], 10)}</section>
  <section><h2>Top ETF Ranking</h2>{compact_table(ranking, ['Ticker','Nome ETF','Categoria','Tema/Area','Score Finale','Priority Score','Stato','Entry Zone','Rendimento 12M %','Volatilità %','Max Drawdown %','Sharpe'], 12)}</section>
  <section><h2>Watchlist azioni e strumenti</h2>{compact_table(watchlist if watchlist is not None else pd.DataFrame(), ['Ticker','Nome','Tipo','Score Finale','Priority Score','Azione Suggerita','Trend','Entry Zone','P/E','Note AI'], 10)}</section>
  <section><h2>Lettura prudente</h2><div class="notegrid"><div class="note"><b>Priority Score</b><br>Combina score, entry quality, rischio e momentum. Serve per ordinare la watchlist, non per comprare automaticamente.</div><div class="note"><b>Entry Zone</b><br>Aiuta a capire se il prezzo è costruttivo, esteso o da attendere. Va sempre confermata con news e mercato.</div><div class="note"><b>Risk Flag</b><br>Segnala volatilità/drawdown elevati e suggerisce size più prudente.</div></div><p class="disclaimer">Gli score sono indicatori informativi e non sono segnali automatici di acquisto o vendita. Prima di qualsiasi operazione verificare costi, spread, fiscalità, liquidità, dimensione posizione, rischio cambio e coerenza con il proprio profilo.</p></section>
</div>
</body>
</html>"""
    output.write_text(html, encoding="utf-8")
