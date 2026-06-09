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


def _as_float(value: object, default: float = 0.0) -> float:
    try:
        if pd.isna(value):
            return default
        return float(value)
    except Exception:  # noqa: BLE001
        return default


def _badge(value: object) -> str:
    text = str(value or "n/d")
    low = text.lower()
    cls = ""
    if any(x in low for x in ["buy", "success", "priorità", "priorita", "costruttiva", "positive"]):
        cls = " good"
    elif any(x in low for x in ["monitor", "graduale", "pullback", "wait", "neutral", "running"]):
        cls = " watch"
    elif any(x in low for x in ["risk", "alto", "high", "avoid", "evitare", "failed", "weak", "negativo"]):
        cls = " danger"
    return f"<span class='pill{cls}'>{escape(text)}</span>"


def _score_bar(value: object) -> str:
    score = max(0.0, min(100.0, _as_float(value)))
    label = format_number(score, 1)
    return f"<div class='scorebar'><span style='width:{score:.0f}%'></span><b>{escape(label)}</b></div>"


def _format_cell(col: str, value: object) -> str:
    if col in {"Score Finale", "Priority Score", "ETF Quality Score", "ETF Momentum Score", "ETF Risk Score", "ETF Entry Score"}:
        return _score_bar(value)
    if col in {"Stato", "Azione Suggerita", "Entry Zone", "Risk Flag", "Trend", "Tipo", "Categoria"}:
        return _badge(value)
    if isinstance(value, (float, int)):
        return escape(format_number(value))
    return escape(str(value if value is not None else ""))


def compact_table(df: pd.DataFrame | None, columns: list[str], limit: int = 10) -> str:
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
            css = " class='long'" if col in {"Note AI", "Trigger Monitoraggio", "Azione Suggerita", "Scenario Base", "Scenario Negativo", "Azione Pratica"} else ""
            cells.append(f"<td{css}>{_format_cell(col, value)}</td>")
        rows.append(f"<tr>{''.join(cells)}</tr>")
    th = "".join(f"<th>{escape(col)}</th>" for col in cols)
    return f"<div class='table-wrap'><table><thead><tr>{th}</tr></thead><tbody>{''.join(rows)}</tbody></table></div>"


def _best_row(df: pd.DataFrame | None, col: str) -> dict[str, Any]:
    if df is None or df.empty or col not in df.columns:
        return {}
    try:
        return df.sort_values(col, ascending=False, na_position="last").iloc[0].to_dict()
    except Exception:  # noqa: BLE001
        return {}


def _safe_count(df: pd.DataFrame | None) -> int:
    return 0 if df is None or df.empty else int(len(df))


def build_text_report(
    ranking: pd.DataFrame,
    allocation: pd.DataFrame,
    watchlist: pd.DataFrame | None = None,
    insights: pd.DataFrame | None = None,
) -> str:
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    lines = [
        "AlphaForge Intelligence v4 - Daily Report",
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
    best_watch = _best_row(watchlist, "Score Finale")
    best_priority = _best_row(insights, "Priority Score")
    status_text = status.get("status", "unknown") if isinstance(status, dict) else "unknown"
    status_class = "good" if status_text == "success" else "watch" if status_text == "running" else "danger" if status_text == "failed" else ""
    avg_priority = "n/d"
    if insights is not None and not insights.empty and "Priority Score" in insights.columns:
        avg_priority = format_number(pd.to_numeric(insights["Priority Score"], errors="coerce").mean(), 1)

    html = f"""<!doctype html>
<html lang="it">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AlphaForge v4 Premium Dashboard</title>
<style>
:root {{
  --bg:#050814; --bg2:#090f21; --panel:rgba(17,26,52,.82); --panel2:rgba(24,37,73,.92);
  --border:rgba(255,255,255,.11); --text:#f4f7ff; --muted:#a7b6d8; --soft:#dbe6ff;
  --green:#6ee7c8; --blue:#91b8ff; --gold:#ffd37a; --red:#ff8f98; --purple:#bda2ff;
}}
* {{ box-sizing:border-box; }}
html {{ scroll-behavior:smooth; }}
body {{ margin:0; font-family:Inter, ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; color:var(--text); background:
  radial-gradient(circle at 6% -4%, rgba(85,119,255,.30), transparent 31%),
  radial-gradient(circle at 92% 2%, rgba(110,231,200,.18), transparent 26%),
  linear-gradient(180deg, var(--bg), var(--bg2) 48%, #050711); }}
body:before {{ content:""; position:fixed; inset:0; pointer-events:none; opacity:.32; background-image:linear-gradient(rgba(255,255,255,.035) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.035) 1px, transparent 1px); background-size:42px 42px; mask-image:linear-gradient(to bottom, black, transparent 78%); }}
.container {{ width:min(1280px, calc(100% - 32px)); margin:0 auto; padding:30px 0 58px; }}
.nav {{ display:flex; align-items:center; justify-content:space-between; gap:16px; margin-bottom:16px; color:var(--muted); font-size:13px; }}
.nav b {{ color:var(--text); letter-spacing:-.02em; }}
.hero {{ position:relative; overflow:hidden; border:1px solid var(--border); border-radius:34px; padding:34px; background:linear-gradient(135deg, rgba(30,45,90,.94), rgba(10,16,33,.88)); box-shadow:0 28px 100px rgba(0,0,0,.42); }}
.hero:after {{ content:""; position:absolute; right:-130px; bottom:-190px; width:440px; height:440px; background:radial-gradient(circle, rgba(145,184,255,.25), transparent 62%); }}
.pill {{ display:inline-flex; align-items:center; gap:7px; padding:6px 11px; border-radius:999px; border:1px solid rgba(255,255,255,.14); background:rgba(255,255,255,.07); color:#dfe8ff; font-weight:850; font-size:12px; white-space:nowrap; }}
.pill.good {{ color:var(--green); background:rgba(110,231,200,.13); border-color:rgba(110,231,200,.25); }}
.pill.watch {{ color:var(--gold); background:rgba(255,211,122,.13); border-color:rgba(255,211,122,.26); }}
.pill.danger {{ color:var(--red); background:rgba(255,143,152,.13); border-color:rgba(255,143,152,.26); }}
h1 {{ position:relative; z-index:1; margin:14px 0 10px; font-size:clamp(40px, 7vw, 74px); line-height:.92; letter-spacing:-.065em; max-width:900px; }}
.subtitle {{ position:relative; z-index:1; max-width:860px; color:var(--muted); font-size:18px; line-height:1.62; margin:0; }}
.grid {{ position:relative; z-index:1; display:grid; grid-template-columns:repeat(6,minmax(0,1fr)); gap:14px; margin-top:26px; }}
.card {{ min-height:112px; padding:17px; border-radius:22px; background:linear-gradient(145deg, rgba(255,255,255,.078), rgba(255,255,255,.035)); border:1px solid rgba(255,255,255,.105); }}
.card.wide {{ grid-column: span 2; }}
.label {{ color:var(--muted); font-size:12px; letter-spacing:.08em; text-transform:uppercase; }}
.value {{ margin-top:8px; color:var(--text); font-size:24px; font-weight:900; letter-spacing:-.03em; }}
.hint {{ margin-top:5px; color:var(--muted); font-size:12px; line-height:1.35; }}
section {{ margin-top:30px; }}
.section-head {{ display:flex; align-items:end; justify-content:space-between; gap:14px; margin-bottom:13px; }}
h2 {{ margin:0; font-size:26px; letter-spacing:-.035em; }}
.section-sub {{ color:var(--muted); font-size:13px; }}
.table-wrap {{ border:1px solid var(--border); border-radius:24px; overflow:auto; background:rgba(8,13,28,.58); box-shadow:0 20px 60px rgba(0,0,0,.20); }}
table {{ width:100%; border-collapse:separate; border-spacing:0; min-width:850px; }}
th,td {{ padding:12px 12px; border-bottom:1px solid rgba(255,255,255,.08); text-align:left; vertical-align:middle; }}
th {{ position:sticky; top:0; z-index:2; color:#cbd8f8; background:rgba(17,26,52,.96); font-size:11px; text-transform:uppercase; letter-spacing:.075em; }}
td {{ color:#f3f6ff; font-size:14px; }}
td.long {{ min-width:300px; color:#dce6ff; line-height:1.45; }}
tr:hover td {{ background:rgba(255,255,255,.035); }}
.scorebar {{ position:relative; min-width:112px; height:28px; border-radius:999px; overflow:hidden; background:rgba(255,255,255,.07); border:1px solid rgba(255,255,255,.08); }}
.scorebar span {{ display:block; height:100%; background:linear-gradient(90deg, rgba(145,184,255,.55), rgba(110,231,200,.72)); }}
.scorebar b {{ position:absolute; inset:0; display:grid; place-items:center; font-size:12px; color:var(--text); text-shadow:0 1px 8px rgba(0,0,0,.55); }}
.notegrid {{ display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:14px; }}
.note {{ border:1px solid var(--border); border-radius:22px; padding:18px; background:rgba(255,255,255,.055); color:#dce7ff; line-height:1.55; }}
.note b {{ color:var(--text); }}
.disclaimer {{ color:var(--muted); line-height:1.62; font-size:13px; margin-top:14px; }}
.footer {{ margin-top:36px; padding:18px; color:var(--muted); border-top:1px solid rgba(255,255,255,.12); font-size:13px; }}
@media (max-width:1050px) {{ .grid {{ grid-template-columns:repeat(2,minmax(0,1fr)); }} .card.wide {{ grid-column:span 1; }} .notegrid {{ grid-template-columns:1fr 1fr; }} }}
@media (max-width:640px) {{ .container {{ width:min(100% - 22px, 1280px); padding-top:14px; }} .hero {{ padding:24px; border-radius:26px; }} .grid {{ grid-template-columns:1fr; }} .notegrid {{ grid-template-columns:1fr; }} h1 {{ font-size:42px; }} }}
</style>
</head>
<body>
<div class="container">
  <div class="nav"><b>AlphaForge Trader</b><span>Dashboard pubblica • dati informativi • aggiornamento automatico</span></div>
  <div class="hero">
    <span class="pill good">✦ AlphaForge v4 Premium UI</span>
    <h1>ETF & Stock Intelligence Dashboard</h1>
    <p class="subtitle">Ranking ETF, allocazione, watchlist azioni, priority score, entry zone, risk flag e scenari pratici in una dashboard più leggibile e premium.</p>
    <div class="grid">
      <div class="card wide"><div class="label">Aggiornato</div><div class="value">{escape(now)}</div><div class="hint">Orario generazione dashboard</div></div>
      <div class="card"><div class="label">Stato update</div><div class="value">{_badge(status_text)}</div><div class="hint">Pipeline dati</div></div>
      <div class="card"><div class="label">Miglior ETF</div><div class="value">{escape(str(best.get('Ticker', 'n/d')))}</div><div class="hint">Score: {escape(format_number(best.get('Score Finale', ''), 1))}</div></div>
      <div class="card"><div class="label">Top Watchlist</div><div class="value">{escape(str(best_watch.get('Ticker', 'n/d')))}</div><div class="hint">Score: {escape(format_number(best_watch.get('Score Finale', ''), 1))}</div></div>
      <div class="card"><div class="label">Priorità</div><div class="value">{escape(str(best_priority.get('Ticker', 'n/d')))}</div><div class="hint">Media priority: {escape(str(avg_priority))}</div></div>
      <div class="card"><div class="label">Copertura</div><div class="value">{_safe_count(ranking)+_safe_count(watchlist)}</div><div class="hint">Strumenti monitorati</div></div>
    </div>
  </div>

  <section>
    <div class="section-head"><div><h2>Priorità operative AlphaForge</h2><div class="section-sub">Cosa monitorare prima, con azione pratica e rischio visibile.</div></div></div>
    {compact_table(insights if insights is not None else pd.DataFrame(), ['Ticker','Tipo','Score Finale','Priority Score','Azione Suggerita','Entry Zone','Risk Flag','Trigger Monitoraggio'], 12)}
  </section>

  <section>
    <div class="section-head"><div><h2>Allocazione suggerita</h2><div class="section-sub">Modello indicativo su nuovi 1000 EUR, non ordine operativo.</div></div></div>
    {compact_table(allocation, ['Ticker','Nome ETF','Categoria','Peso Target %','Importo su 1000 EUR','Score Finale','Stato'], 10)}
  </section>

  <section>
    <div class="section-head"><div><h2>Top ETF Ranking</h2><div class="section-sub">Score finale, priorità, entry zone e rischio in una vista compatta.</div></div></div>
    {compact_table(ranking, ['Ticker','Nome ETF','Categoria','Tema/Area','Score Finale','Priority Score','Stato','Entry Zone','Rendimento 12M %','Volatilità %','Max Drawdown %','Sharpe'], 12)}
  </section>

  <section>
    <div class="section-head"><div><h2>Watchlist azioni e strumenti</h2><div class="section-sub">Titoli e strumenti da seguire con score, azione suggerita e note sintetiche.</div></div></div>
    {compact_table(watchlist if watchlist is not None else pd.DataFrame(), ['Ticker','Nome','Tipo','Score Finale','Priority Score','Azione Suggerita','Trend','Entry Zone','P/E','Note AI'], 10)}
  </section>

  <section>
    <div class="section-head"><div><h2>Lettura prudente</h2><div class="section-sub">Come interpretare gli indicatori senza trasformarli in segnali automatici.</div></div></div>
    <div class="notegrid">
      <div class="note"><b>Priority Score</b><br>Ordina gli strumenti da monitorare combinando score, rischio, momentum ed entry quality.</div>
      <div class="note"><b>Entry Zone</b><br>Aiuta a distinguere prezzo costruttivo, esteso o da attendere su pullback.</div>
      <div class="note"><b>Risk Flag</b><br>Rende visibile quando volatilità e drawdown richiedono size più prudente.</div>
      <div class="note"><b>Azione suggerita</b><br>È una lettura pratica per watchlist, non un ordine di acquisto o vendita.</div>
    </div>
    <p class="disclaimer">Gli score sono indicatori informativi. Prima di qualsiasi operazione verificare costi, spread, fiscalità, liquidità, rischio cambio, dimensione posizione, notizie, trimestrali e coerenza con il proprio profilo.</p>
  </section>
  <div class="footer">AlphaForge v4 Premium UI • Dashboard statica generata automaticamente da GitHub Actions.</div>
</div>
</body>
</html>"""
    output.write_text(html, encoding="utf-8")
