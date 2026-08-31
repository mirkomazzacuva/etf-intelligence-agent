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
    if any(x in low for x in ["success", "discutere", "graduale", "core", "alta priorita", "priorità", "da fare", "buy"]):
        cls = " good"
    elif any(x in low for x in ["monitor", "pullback", "attendi", "watch", "strategica", "laterale"]):
        cls = " watch"
    elif any(x in low for x in ["risk", "rischio", "alto", "avoid", "evita", "riduci", "bassa"]):
        cls = " danger"
    return f"<span class='pill{cls}'>{escape(text)}</span>"


def _score_bar(value: object) -> str:
    score = max(0.0, min(100.0, _as_float(value)))
    label = format_number(score, 1)
    return f"<div class='scorebar'><span style='width:{score:.0f}%'></span><b>{escape(label)}</b></div>"


def _format_cell(col: str, value: object) -> str:
    if col in {"Score Finale", "Priority Score", "Sector Score", "Momentum Score", "Risk Score", "Priorita Strategica", "Portfolio Health Score"}:
        return _score_bar(value)
    if col in {"Stato", "Azione Suggerita", "Entry Zone", "Risk Flag", "Trend", "Tipo", "Categoria", "Decisione", "Bucket", "Cosa fare", "AF Bucket", "Priorita", "Priorità", "Tipo Copertura", "Strumento preferito"}:
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
    long_cols = {
        "Note AI",
        "Trigger Monitoraggio",
        "Azione Suggerita",
        "Scenario Base",
        "Scenario Negativo",
        "Azione Pratica",
        "Cosa fare adesso",
        "Cosa fare in pratica",
        "Perché",
        "Perche",
        "Perche guardarlo",
        "Rischio principale",
        "Nota Fineco/Consulente",
        "ETF/Fondo candidato",
        "Cosa fare",
    }
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


def _count_bucket(df: pd.DataFrame | None, col: str, value: str) -> int:
    if df is None or df.empty or col not in df.columns:
        return 0
    return int(df[col].astype(str).eq(value).sum())


def build_text_report(
    ranking: pd.DataFrame,
    allocation: pd.DataFrame,
    watchlist: pd.DataFrame | None = None,
    insights: pd.DataFrame | None = None,
    action_plan: pd.DataFrame | None = None,
    sector_compass: pd.DataFrame | None = None,
) -> str:
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    brief = build_action_brief(action_plan, insights)
    lines = [
        "AlphaForge Intelligence v7 - Sector Compass Report",
        f"Aggiornato il {now}",
        "",
        "Report informativo. Non costituisce consulenza finanziaria personalizzata.",
        "Obiettivo: aiutare la conversazione con consulente Fineco su core, satelliti settoriali e strumenti candidati.",
        "",
        "Bussola settoriale:",
    ]
    if sector_compass is not None and not sector_compass.empty:
        for _, row in sector_compass.head(6).iterrows():
            lines.append(
                f"- {row.get('Settore','')}: {row.get('Bucket','')} | {row.get('Cosa fare','')} | candidato: {row.get('ETF/Fondo candidato','')} ({row.get('Ticker ETF/Fondo','')})"
            )
    else:
        lines.append("- Bussola settoriale non disponibile.")
    lines += ["", "Cosa fare adesso:"]
    for line in brief.narrative[:6]:
        lines.append(f"- {line}")
    if allocation is not None and not allocation.empty:
        lines += ["", "Allocazione modello su 1000 EUR:"]
        for _, row in allocation.head(6).iterrows():
            amount = row.get("Importo su 1000 EUR", row.get("Importo Indicativo EUR", ""))
            lines.append(f"- {row.get('Ticker', '')}: {row.get('Peso Target %', '')}% - {amount} EUR")
    lines += [
        "",
        "Portafoglio personale: usa la pagina Streamlit 'Portafoglio Fineco' per caricare il CSV/XLSX, verificare peso core/satellite e classificare fondi/ETF per settore.",
        "Prima di investire controllare sempre: KID, TER/costi, fiscalita, liquidita, valuta, dimensione fondo, sovrapposizione con All-World e adeguatezza con il consulente.",
    ]
    return "\n".join(lines)


def render_dashboard_html(
    ranking: pd.DataFrame,
    allocation: pd.DataFrame,
    status: dict,
    watchlist: pd.DataFrame | None,
    output: Path,
    insights: pd.DataFrame | None = None,
    action_plan: pd.DataFrame | None = None,
    sector_compass: pd.DataFrame | None = None,
) -> None:
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    best = _best_row(ranking, "Score Finale")
    best_sector = _best_row(sector_compass, "Sector Score")
    best_priority = _best_row(insights, "Priority Score")
    status_text = status.get("status", "unknown") if isinstance(status, dict) else "unknown"
    focus = build_focus_board(action_plan, insights, limit=12)

    if sector_compass is not None and not sector_compass.empty:
        sector_compass = sector_compass.sort_values("Sector Score", ascending=False, na_position="last")
    core_count = _count_bucket(sector_compass, "Bucket", "Da discutere ora")
    strategic_watch = _count_bucket(sector_compass, "Bucket", "Watchlist strategica")
    risky_count = _count_bucket(sector_compass, "Bucket", "Tema forte ma rischioso")
    low_count = _count_bucket(sector_compass, "Bucket", "Bassa priorita")
    first_sector = best_sector.get("Settore", "n/d")
    first_action = best_sector.get("Cosa fare", "Classifica prima il portafoglio e discuti eventuali satelliti con il consulente.")

    css = """
    <style>
    :root { --bg:#040711; --bg2:#081126; --panel:rgba(17,26,52,.88); --border:rgba(255,255,255,.13); --text:#f5f8ff; --muted:#a8b8dd; --green:#69e6c2; --blue:#8eb5ff; --gold:#ffd37a; --red:#ff8f98; --purple:#c4a7ff; }
    * { box-sizing:border-box; } html { scroll-behavior:smooth; } body { margin:0; font-family:Inter,ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif; color:var(--text); background:radial-gradient(circle at 10% -6%, rgba(105,230,194,.22), transparent 27%), radial-gradient(circle at 90% 0%, rgba(142,181,255,.25), transparent 30%), linear-gradient(180deg,var(--bg),var(--bg2) 48%,#050711); }
    body:before { content:""; position:fixed; inset:0; pointer-events:none; opacity:.22; background-image:linear-gradient(rgba(255,255,255,.035) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.035) 1px, transparent 1px); background-size:42px 42px; mask-image:linear-gradient(to bottom, black, transparent 78%); }
    .container { width:min(1280px, calc(100% - 32px)); margin:0 auto; padding:30px 0 58px; } .nav { display:flex; align-items:center; justify-content:space-between; gap:16px; margin-bottom:16px; color:var(--muted); font-size:13px; } .nav b { color:var(--text); letter-spacing:-.02em; }
    .hero { position:relative; overflow:hidden; border:1px solid var(--border); border-radius:34px; padding:34px; background:linear-gradient(135deg, rgba(22,43,74,.96), rgba(9,15,32,.90)); box-shadow:0 28px 100px rgba(0,0,0,.44); } .hero:after { content:""; position:absolute; right:-130px; bottom:-190px; width:460px; height:460px; background:radial-gradient(circle, rgba(105,230,194,.24), transparent 62%); }
    .pill { display:inline-flex; align-items:center; gap:7px; padding:6px 11px; border-radius:999px; border:1px solid rgba(255,255,255,.14); background:rgba(255,255,255,.07); color:#dfe8ff; font-weight:850; font-size:12px; white-space:nowrap; } .pill.good { color:var(--green); background:rgba(105,230,194,.13); border-color:rgba(105,230,194,.25); } .pill.watch { color:var(--gold); background:rgba(255,211,122,.13); border-color:rgba(255,211,122,.26); } .pill.danger { color:var(--red); background:rgba(255,143,152,.13); border-color:rgba(255,143,152,.26); }
    h1 { position:relative; z-index:1; margin:14px 0 10px; font-size:clamp(38px, 7vw, 72px); line-height:.94; letter-spacing:-.065em; max-width:1080px; } .subtitle { position:relative; z-index:1; max-width:980px; color:var(--muted); font-size:18px; line-height:1.62; margin:0; }
    .grid { position:relative; z-index:1; display:grid; grid-template-columns:repeat(6,minmax(0,1fr)); gap:14px; margin-top:26px; } .card { min-height:112px; padding:17px; border-radius:22px; background:linear-gradient(145deg, rgba(255,255,255,.082), rgba(255,255,255,.035)); border:1px solid rgba(255,255,255,.12); } .card .label { color:var(--muted); font-size:12px; text-transform:uppercase; letter-spacing:.08em; } .card .value { margin-top:7px; font-size:24px; font-weight:900; } .card .hint { margin-top:4px; color:var(--muted); font-size:12px; line-height:1.35; } .span2 { grid-column:span 2; } .span3 { grid-column:span 3; }
    section { margin-top:22px; padding:24px; border-radius:30px; background:var(--panel); border:1px solid var(--border); box-shadow:0 18px 60px rgba(0,0,0,.25); } h2 { margin:0 0 8px; font-size:28px; letter-spacing:-.035em; } .muted { color:var(--muted); line-height:1.55; } .big-action { margin-top:18px; padding:20px; border-radius:24px; border:1px solid rgba(105,230,194,.25); background:linear-gradient(135deg, rgba(105,230,194,.13), rgba(142,181,255,.08)); font-size:18px; line-height:1.55; font-weight:820; }
    .decision-grid { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:14px; margin-top:16px; } .decision { padding:16px; border-radius:20px; background:rgba(255,255,255,.055); border:1px solid rgba(255,255,255,.10); } .decision b { display:block; font-size:22px; margin-top:6px; }
    .advisor { border-color:rgba(255,211,122,.25); background:linear-gradient(135deg, rgba(255,211,122,.10), rgba(255,255,255,.04)); }
    .table-wrap { overflow:auto; border-radius:18px; border:1px solid rgba(255,255,255,.09); margin-top:14px; } table { width:100%; border-collapse:collapse; min-width:920px; } th,td { padding:12px 13px; border-bottom:1px solid rgba(255,255,255,.075); text-align:left; vertical-align:top; font-size:13px; } th { position:sticky; top:0; background:rgba(9,15,32,.96); color:#d9e4ff; font-size:12px; text-transform:uppercase; letter-spacing:.06em; } td.long { min-width:270px; color:#dbe6ff; line-height:1.42; } tr:hover td { background:rgba(255,255,255,.035); }
    .scorebar { min-width:112px; height:24px; border-radius:999px; background:rgba(255,255,255,.08); overflow:hidden; position:relative; border:1px solid rgba(255,255,255,.08); } .scorebar span { display:block; height:100%; background:linear-gradient(90deg, var(--green), var(--blue)); } .scorebar b { position:absolute; inset:0; display:flex; align-items:center; justify-content:center; font-size:12px; }
    .two { display:grid; grid-template-columns:1fr 1fr; gap:18px; } .footer { margin-top:24px; color:var(--muted); font-size:13px; line-height:1.5; } a { color:var(--green); }
    @media (max-width:980px){ .grid,.decision-grid,.two{grid-template-columns:1fr 1fr}.span2,.span3{grid-column:span 1} } @media (max-width:640px){ .container{width:min(100% - 18px,1280px)} .hero,section{border-radius:22px;padding:20px}.grid,.decision-grid,.two{grid-template-columns:1fr} h1{font-size:40px} }
    </style>
    """

    html = f"""<!doctype html>
<html lang='it'>
<head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'><title>AlphaForge v7 Sector Compass</title>{css}</head>
<body><div class='container'>
  <div class='nav'><b>AlphaForge Trader</b><span>{_badge('Stato update: ' + str(status_text))}</span></div>
  <div class='hero'>
    <span class='pill good'>✦ AlphaForge v7 Sector Compass</span>
    <h1>Prima i settori, poi lo strumento.</h1>
    <p class='subtitle'>Pensato per chi ha gia' un core globale e un consulente: la dashboard non dice "compra questo", ma prepara una lista chiara di settori da discutere, ETF/fondi candidati da verificare su Fineco e alternative azionarie solo per quote satellite.</p>
    <div class='grid'>
      <div class='card span2'><div class='label'>Prima discussione con consulente</div><div class='value'>{escape(str(first_sector))}</div><div class='hint'>{escape(str(first_action))}</div></div>
      <div class='card'><div class='label'>Settori da discutere</div><div class='value'>{core_count}</div><div class='hint'>Priorita' alta</div></div>
      <div class='card'><div class='label'>Watchlist strategica</div><div class='value'>{strategic_watch}</div><div class='hint'>Attendere conferma</div></div>
      <div class='card'><div class='label'>Temi rischiosi</div><div class='value'>{risky_count}</div><div class='hint'>Size piccola</div></div>
      <div class='card'><div class='label'>Bassa priorita'</div><div class='value'>{low_count}</div><div class='hint'>Evita rumore</div></div>
    </div>
  </div>

  <section>
    <h2>1. Bussola settoriale</h2>
    <p class='muted'>Questa e' la nuova vista principale. Se hai gia' Vanguard All-World o fondi globali, qui non si cerca di sostituire il core: si decide se aggiungere piccoli satelliti settoriali e con quale strumento preferito.</p>
    <div class='big-action'>Regola semplice: core globale prima, satelliti settoriali piccoli dopo, azioni singole solo come eccezione consapevole.</div>
    {compact_table(sector_compass, ['Priorita','Settore','Bucket','Cosa fare','Sector Score','Strumento preferito','Ticker ETF/Fondo','ETF/Fondo candidato','Range pratico','Perche guardarlo','Rischio principale','Nota Fineco/Consulente'], 12)}
  </section>

  <section class='advisor'>
    <h2>2. Cosa portare al consulente Fineco</h2>
    <p class='muted'>Usa questa pagina come traccia di discussione, non come ordine operativo.</p>
    <div class='decision-grid'>
      <div class='decision'><span class='muted'>Domanda 1</span><b>Quanto ho gia' nel core globale?</b><small class='muted'>All-World, MSCI World, fondi globali.</small></div>
      <div class='decision'><span class='muted'>Domanda 2</span><b>Quali settori mancano davvero?</b><small class='muted'>Evita doppioni nascosti.</small></div>
      <div class='decision'><span class='muted'>Domanda 3</span><b>ETF/Fondo o azione singola?</b><small class='muted'>Default: ETF/fondo UCITS.</small></div>
      <div class='decision'><span class='muted'>Domanda 4</span><b>Che peso massimo?</b><small class='muted'>Satellite piccolo e controllato.</small></div>
    </div>
  </section>

  <div class='two'>
    <section><h2>3. Priorita' operative</h2><p class='muted'>Rimane utile, ma ora viene dopo la bussola settoriale.</p>{compact_table(focus, ['Priorita','Ticker','AF Bucket','Decisione','Cosa fare in pratica','Priority Score','Entry Zone','Risk Flag'], 8)}</section>
    <section><h2>4. Strumenti candidati</h2><p class='muted'>ETF/fondi come default; azioni leader solo se vuoi un satellite piu' rischioso.</p>{compact_table(sector_compass, ['Settore','Strumento preferito','Ticker ETF/Fondo','ETF/Fondo candidato','Azioni leader','Range pratico'], 10)}</section>
  </div>

  <section>
    <h2>5. Portafoglio utente</h2>
    <p class='muted'>Per sapere come sta andando il portafoglio reale apri l'app Streamlit, pagina <b>Portafoglio Fineco</b>, carica CSV/XLSX e classifica ogni fondo/ETF in un settore AlphaForge. La dashboard pubblica non carica dati personali.</p>
    <div class='decision-grid'>
      <div class='decision'><span class='muted'>Core</span><b>All-World / fondi globali</b></div>
      <div class='decision'><span class='muted'>Satelliti</span><b>Settori scelti</b></div>
      <div class='decision'><span class='muted'>Rischio</span><b>Peso massimo per tema</b></div>
      <div class='decision'><span class='muted'>Azione</span><b>Ribilancia prima di aggiungere</b></div>
    </div>
  </section>

  <section>
    <h2>6. Allocazione modello</h2>
    <p class='muted'>Esempio informativo su 1000 EUR. Non considera il tuo patrimonio totale, fiscalita', vincoli personali o fondi gia' posseduti.</p>
    {compact_table(allocation, ['Ticker','Nome ETF','Categoria','Peso Target %','Importo su 1000 EUR','Razionale'], 8)}
  </section>

  <section>
    <h2>7. Dati avanzati</h2>
    <p class='muted'>Ranking e watchlist restano disponibili, ma non sono piu' la prima schermata da leggere.</p>
    {compact_table(ranking, ['Ticker','Nome ETF','Categoria','Score Finale','Stato','Trend','Entry Zone','Risk Flag','Note AI'], 10)}
  </section>

  <section>
    <h2>8. Lettura prudente</h2>
    <p class='muted'>Aggiornato il {escape(now)}. Miglior ETF quantitativo: <b>{escape(str(best.get('Ticker', 'n/d')))}</b>. Migliore priorita' strumento: <b>{escape(str(best_priority.get('Ticker', 'n/d')))}</b>. Settore da discutere per primo: <b>{escape(str(first_sector))}</b>.</p>
    <p class='muted'>Informazioni a scopo educativo e di monitoraggio. Non costituiscono consulenza finanziaria personalizzata, sollecitazione all'investimento o garanzia di rendimento. Verificare sempre KID, costi, liquidita', fiscalita', adeguatezza e disponibilita' su Fineco.</p>
  </section>
  <div class='footer'>AlphaForge v7 Sector Compass · Core + satelliti settoriali · File pubblici generati automaticamente da GitHub Actions.</div>
</div></body></html>"""
    output.write_text(html, encoding="utf-8")
