from __future__ import annotations

from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any

import pandas as pd

from core.action_guide_engine import build_action_brief, build_focus_board


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
    if any(x in low for x in ["success", "valuta", "graduale", "azione controllata", "da fare", "buy", "priorita", "priorità"]):
        cls = " good"
    elif any(x in low for x in ["monitor", "pullback", "attendi", "wait", "neutral", "watch", "osservazione"]):
        cls = " watch"
    elif any(x in low for x in ["risk", "alto", "high", "avoid", "evita", "riduci", "failed", "rischio"]):
        cls = " danger"
    return f"<span class='pill{cls}'>{escape(text)}</span>"


def _score_bar(value: object) -> str:
    score = max(0.0, min(100.0, _as_float(value)))
    label = format_number(score, 1)
    return f"<div class='scorebar'><span style='width:{score:.0f}%'></span><b>{escape(label)}</b></div>"


def _format_cell(col: str, value: object) -> str:
    if col in {"Score Finale", "Priority Score", "Portfolio Health Score", "ETF Quality Score", "ETF Momentum Score", "ETF Risk Score", "ETF Entry Score"}:
        return _score_bar(value)
    if col in {"Stato", "Azione Suggerita", "Entry Zone", "Risk Flag", "Trend", "Tipo", "Categoria", "Decisione chiara", "Bucket operativo", "AF Bucket", "Priorita", "Priorità"}:
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
    long_cols = {"Note AI", "Trigger Monitoraggio", "Azione Suggerita", "Scenario Base", "Scenario Negativo", "Azione Pratica", "Cosa fare adesso", "Cosa fare in pratica", "Perché", "Perche", "Decisione chiara", "Perche"}
    rows: list[str] = []
    for _, row in df.head(limit).iterrows():
        cells = []
        for col in cols:
            css = " class='long'" if col in long_cols else ""
            cells.append(f"<td{css}>{_format_cell(col, row.get(col, ''))}</td>")
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


def _count_bucket(focus: pd.DataFrame, bucket: str) -> int:
    if focus is None or focus.empty or "AF Bucket" not in focus.columns:
        return 0
    return int(focus["AF Bucket"].astype(str).eq(bucket).sum())


def build_text_report(
    ranking: pd.DataFrame,
    allocation: pd.DataFrame,
    watchlist: pd.DataFrame | None = None,
    insights: pd.DataFrame | None = None,
    action_plan: pd.DataFrame | None = None,
) -> str:
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    brief = build_action_brief(action_plan, insights)
    lines = [
        "AlphaForge Intelligence v6 - Action First Report",
        f"Aggiornato il {now}",
        "",
        "Report informativo. Non costituisce consulenza finanziaria personalizzata.",
        "",
        "Cosa fare adesso:",
    ]
    for line in brief.narrative[:8]:
        lines.append(f"- {line}")
    if ranking is not None and not ranking.empty:
        best = _best_row(ranking, "Score Finale")
        lines += ["", f"Miglior ETF: {best.get('Ticker', '')} - score {best.get('Score Finale', '')}", f"Stato: {best.get('Stato', '')}"]
    if allocation is not None and not allocation.empty:
        lines += ["", "Allocazione suggerita su 1000 EUR:"]
        for _, row in allocation.head(8).iterrows():
            amount = row.get("Importo su 1000 EUR", row.get("Importo Indicativo EUR", ""))
            lines.append(f"- {row.get('Ticker', '')}: {row.get('Peso Target %', '')}% - {amount} EUR")
    lines += ["", "Portafoglio personale: usa la pagina Streamlit 'Portafoglio' per caricare CSV/XLSX, controllare concentrazione, rischio e gap target."]
    lines += ["", "Usare sempre size, diversificazione, costi, fiscalità, liquidità e profilo personale come filtri finali."]
    return "\n".join(lines)


def render_dashboard_html(
    ranking: pd.DataFrame,
    allocation: pd.DataFrame,
    status: dict,
    watchlist: pd.DataFrame | None,
    output: Path,
    insights: pd.DataFrame | None = None,
    action_plan: pd.DataFrame | None = None,
) -> None:
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    best = _best_row(ranking, "Score Finale")
    best_watch = _best_row(watchlist, "Score Finale")
    best_priority = _best_row(insights, "Priority Score")
    status_text = status.get("status", "unknown") if isinstance(status, dict) else "unknown"
    focus = build_focus_board(action_plan, insights, limit=16)
    first_action = focus.iloc[0].get("Cosa fare in pratica", "Nessuna azione generata") if not focus.empty else "Nessuna azione generata"
    do_now = _count_bucket(focus, "Da fare ora")
    wait_pullback = _count_bucket(focus, "Attendi pullback")
    risk_control = _count_bucket(focus, "Rischio da ridurre")
    monitor = _count_bucket(focus, "Monitora")
    avg_priority = "n/d"
    if insights is not None and not insights.empty and "Priority Score" in insights.columns:
        avg_priority = format_number(pd.to_numeric(insights["Priority Score"], errors="coerce").mean(), 1)

    css = """
    <style>
    :root { --bg:#040711; --bg2:#081126; --panel:rgba(17,26,52,.86); --border:rgba(255,255,255,.12); --text:#f4f7ff; --muted:#a7b6d8; --green:#6ee7c8; --blue:#91b8ff; --gold:#ffd37a; --red:#ff8f98; --purple:#bda2ff; }
    * { box-sizing:border-box; } html { scroll-behavior:smooth; } body { margin:0; font-family:Inter,ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif; color:var(--text); background:radial-gradient(circle at 6% -4%, rgba(85,119,255,.30), transparent 31%), radial-gradient(circle at 92% 2%, rgba(110,231,200,.18), transparent 26%), linear-gradient(180deg,var(--bg),var(--bg2) 48%,#050711); }
    body:before { content:""; position:fixed; inset:0; pointer-events:none; opacity:.24; background-image:linear-gradient(rgba(255,255,255,.035) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.035) 1px, transparent 1px); background-size:42px 42px; mask-image:linear-gradient(to bottom, black, transparent 78%); }
    .container { width:min(1280px, calc(100% - 32px)); margin:0 auto; padding:30px 0 58px; } .nav { display:flex; align-items:center; justify-content:space-between; gap:16px; margin-bottom:16px; color:var(--muted); font-size:13px; } .nav b { color:var(--text); letter-spacing:-.02em; }
    .hero { position:relative; overflow:hidden; border:1px solid var(--border); border-radius:34px; padding:34px; background:linear-gradient(135deg, rgba(30,45,90,.94), rgba(10,16,33,.88)); box-shadow:0 28px 100px rgba(0,0,0,.42); } .hero:after { content:""; position:absolute; right:-130px; bottom:-190px; width:440px; height:440px; background:radial-gradient(circle, rgba(145,184,255,.25), transparent 62%); }
    .pill { display:inline-flex; align-items:center; gap:7px; padding:6px 11px; border-radius:999px; border:1px solid rgba(255,255,255,.14); background:rgba(255,255,255,.07); color:#dfe8ff; font-weight:850; font-size:12px; white-space:nowrap; } .pill.good { color:var(--green); background:rgba(110,231,200,.13); border-color:rgba(110,231,200,.25); } .pill.watch { color:var(--gold); background:rgba(255,211,122,.13); border-color:rgba(255,211,122,.26); } .pill.danger { color:var(--red); background:rgba(255,143,152,.13); border-color:rgba(255,143,152,.26); }
    h1 { position:relative; z-index:1; margin:14px 0 10px; font-size:clamp(40px, 7vw, 74px); line-height:.92; letter-spacing:-.065em; max-width:980px; } .subtitle { position:relative; z-index:1; max-width:930px; color:var(--muted); font-size:18px; line-height:1.62; margin:0; }
    .grid { position:relative; z-index:1; display:grid; grid-template-columns:repeat(6,minmax(0,1fr)); gap:14px; margin-top:26px; } .card { min-height:112px; padding:17px; border-radius:22px; background:linear-gradient(145deg, rgba(255,255,255,.078), rgba(255,255,255,.035)); border:1px solid rgba(255,255,255,.12); } .card .label { color:var(--muted); font-size:12px; text-transform:uppercase; letter-spacing:.08em; } .card .value { margin-top:7px; font-size:24px; font-weight:900; } .card .hint { margin-top:4px; color:var(--muted); font-size:12px; line-height:1.35; } .span2 { grid-column:span 2; } .span3 { grid-column:span 3; }
    section { margin-top:22px; padding:24px; border-radius:30px; background:var(--panel); border:1px solid var(--border); box-shadow:0 18px 60px rgba(0,0,0,.25); } h2 { margin:0 0 8px; font-size:28px; letter-spacing:-.035em; } .muted { color:var(--muted); line-height:1.55; } .big-action { margin-top:18px; padding:20px; border-radius:24px; border:1px solid rgba(110,231,200,.25); background:linear-gradient(135deg, rgba(110,231,200,.12), rgba(145,184,255,.08)); font-size:18px; line-height:1.55; font-weight:820; }
    .decision-grid { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:14px; margin-top:16px; } .decision { padding:16px; border-radius:20px; background:rgba(255,255,255,.055); border:1px solid rgba(255,255,255,.10); } .decision b { display:block; font-size:24px; margin-top:6px; }
    .table-wrap { overflow:auto; border-radius:18px; border:1px solid rgba(255,255,255,.09); margin-top:14px; } table { width:100%; border-collapse:collapse; min-width:860px; } th,td { padding:12px 13px; border-bottom:1px solid rgba(255,255,255,.075); text-align:left; vertical-align:top; font-size:13px; } th { position:sticky; top:0; background:rgba(9,15,32,.96); color:#d9e4ff; font-size:12px; text-transform:uppercase; letter-spacing:.06em; } td.long { min-width:260px; color:#dbe6ff; line-height:1.42; } tr:hover td { background:rgba(255,255,255,.035); }
    .scorebar { min-width:112px; height:24px; border-radius:999px; background:rgba(255,255,255,.08); overflow:hidden; position:relative; border:1px solid rgba(255,255,255,.08); } .scorebar span { display:block; height:100%; background:linear-gradient(90deg, var(--green), var(--blue)); } .scorebar b { position:absolute; inset:0; display:flex; align-items:center; justify-content:center; font-size:12px; }
    .two { display:grid; grid-template-columns:1.05fr .95fr; gap:18px; } .footer { margin-top:24px; color:var(--muted); font-size:13px; line-height:1.5; } a { color:var(--green); }
    @media (max-width:980px){ .grid,.decision-grid,.two{grid-template-columns:1fr 1fr}.span2,.span3{grid-column:span 1} } @media (max-width:640px){ .container{width:min(100% - 18px,1280px)} .hero,section{border-radius:22px;padding:20px}.grid,.decision-grid,.two{grid-template-columns:1fr} h1{font-size:42px} }
    </style>
    """

    html = f"""<!doctype html>
<html lang='it'>
<head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'><title>AlphaForge v6 Action First Dashboard</title>{css}</head>
<body><div class='container'>
  <div class='nav'><b>AlphaForge Trader</b><span>{_badge('Stato update: ' + str(status_text))}</span></div>
  <div class='hero'>
    <span class='pill good'>✦ AlphaForge v6 Action First</span>
    <h1>Cosa fare adesso, prima degli score.</h1>
    <p class='subtitle'>La dashboard traduce ranking, entry zone e rischio in priorità operative semplici: cosa guardare, cosa attendere, cosa non aumentare e come leggere il portafoglio.</p>
    <div class='grid'>
      <div class='card span2'><div class='label'>Prima azione pratica</div><div class='value'>Action First</div><div class='hint'>{escape(str(first_action))}</div></div>
      <div class='card'><div class='label'>Da fare ora</div><div class='value'>{do_now}</div><div class='hint'>Solo ingressi controllati</div></div>
      <div class='card'><div class='label'>Aspetta pullback</div><div class='value'>{wait_pullback}</div><div class='hint'>Non inseguire</div></div>
      <div class='card'><div class='label'>Controllo rischio</div><div class='value'>{risk_control}</div><div class='hint'>Size / protezione</div></div>
      <div class='card'><div class='label'>Priority media</div><div class='value'>{escape(str(avg_priority))}</div><div class='hint'>Copertura { _safe_count(insights) } strumenti</div></div>
    </div>
  </div>

  <section>
    <h2>1. Cosa fare adesso</h2>
    <p class='muted'>Questa è la sezione da leggere per prima. Non sostituisce una scelta personale, ma riduce il rumore: ti dice quali strumenti meritano attenzione, quali vanno aspettati e dove controllare il rischio.</p>
    <div class='big-action'>{escape(str(first_action))}</div>
    <div class='decision-grid'>
      <div class='decision'><span class='muted'>Azione controllata</span><b>{do_now}</b><small class='muted'>Possibili ingressi solo graduali</small></div>
      <div class='decision'><span class='muted'>Non inseguire</span><b>{wait_pullback}</b><small class='muted'>Attendi prezzo migliore</small></div>
      <div class='decision'><span class='muted'>Rischio</span><b>{risk_control}</b><small class='muted'>Non aumentare esposizione</small></div>
      <div class='decision'><span class='muted'>Monitoraggio</span><b>{monitor}</b><small class='muted'>Nessuna urgenza</small></div>
    </div>
    {compact_table(focus, ['Priorita','Ticker','AF Bucket','Decisione','Cosa fare in pratica','Perche','Priority Score','Score Finale','Entry Zone','Risk Flag'], 14)}
  </section>

  <section>
    <h2>2. Portafoglio utente</h2>
    <p class='muted'>La dashboard pubblica non carica file personali. Per valutare un portafoglio reale apri l'app Streamlit, pagina <b>Portafoglio</b>, carica il CSV/XLSX e controlla: peso maggiore, top 3, high-risk, gap target e suggerimento per posizione.</p>
    <div class='decision-grid'>
      <div class='decision'><span class='muted'>Prima domanda</span><b>Quanto pesa la posizione più grande?</b></div>
      <div class='decision'><span class='muted'>Seconda domanda</span><b>Quanto pesa il rischio alto?</b></div>
      <div class='decision'><span class='muted'>Terza domanda</span><b>Sei sopra o sotto target?</b></div>
      <div class='decision'><span class='muted'>Azione</span><b>Ribilancia prima di comprare altro.</b></div>
    </div>
  </section>

  <div class='two'>
    <section><h2>3. Top priorità</h2><p class='muted'>Strumenti ordinati per priority score e filtro operativo.</p>{compact_table(insights, ['Ticker','Tipo','Score Finale','Priority Score','Azione Suggerita','Entry Zone','Risk Flag','Trigger Monitoraggio'], 10)}</section>
    <section><h2>4. Watchlist azioni e strumenti</h2><p class='muted'>Non tutti gli strumenti sono da comprare: controlla entry zone e risk flag.</p>{compact_table(watchlist, ['Ticker','Tipo','Score Finale','Azione Suggerita','Entry Zone','Risk Flag','Note AI'], 10)}</section>
  </div>

  <section>
    <h2>5. Allocazione suggerita</h2>
    <p class='muted'>Esempio informativo su 1000 EUR. Non considera il tuo patrimonio totale, fiscalità o vincoli personali.</p>
    {compact_table(allocation, ['Ticker','Nome ETF','Categoria','Peso Target %','Importo su 1000 EUR','Razionale'], 10)}
  </section>

  <section>
    <h2>6. Top ETF Ranking</h2>
    <p class='muted'>Ranking quantitativo: utile come filtro, non come comando automatico.</p>
    {compact_table(ranking, ['Ticker','Nome ETF','Categoria','Score Finale','Stato','Trend','Entry Zone','Risk Flag','Note AI'], 12)}
  </section>

  <section>
    <h2>7. Lettura prudente</h2>
    <p class='muted'>Aggiornato il {escape(now)}. Miglior ETF: <b>{escape(str(best.get('Ticker', 'n/d')))}</b>. Migliore priorità: <b>{escape(str(best_priority.get('Ticker', 'n/d')))}</b>. Migliore watchlist: <b>{escape(str(best_watch.get('Ticker', 'n/d')))}</b>.</p>
    <p class='muted'>Informazioni a scopo educativo e di monitoraggio. Non costituiscono consulenza finanziaria personalizzata, sollecitazione all'investimento o garanzia di rendimento.</p>
  </section>
  <div class='footer'>AlphaForge v6 Action First · File pubblici generati automaticamente da GitHub Actions.</div>
</div></body></html>"""
    output.write_text(html, encoding="utf-8")
