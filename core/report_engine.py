from __future__ import annotations

from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any

import pandas as pd

try:
    from core.action_guide_engine import build_action_brief, build_focus_board
except Exception:  # noqa: BLE001
    class _Brief:
        narrative = ["Dati operativi non disponibili: esegui l'aggiornamento completo."]

    def build_action_brief(action_plan=None, insights=None):  # type: ignore[no-redef]
        return _Brief()

    def build_focus_board(action_plan=None, insights=None, limit: int = 12):  # type: ignore[no-redef]
        return pd.DataFrame()


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
    if any(x in low for x in ["success", "core", "graduale", "da discutere", "punto zero", "ok", "alta"]):
        cls = " good"
    elif any(x in low for x in ["monitor", "pullback", "attendi", "watch", "verifica", "pac"]):
        cls = " watch"
    elif any(x in low for x in ["risk", "rischio", "alto", "avoid", "evita", "riduci", "bassa"]):
        cls = " danger"
    return f"<span class='pill{cls}'>{escape(text)}</span>"


def _score_bar(value: object) -> str:
    score = max(0.0, min(100.0, _as_float(value)))
    label = format_number(score, 1)
    return f"<div class='scorebar'><span style='width:{score:.0f}%'></span><b>{escape(label)}</b></div>"


def _format_cell(col: str, value: object) -> str:
    score_cols = {"Score Finale", "Priority Score", "Sector Score", "Momentum Score", "Risk Score", "Priorita Strategica", "Portfolio Health Score"}
    badge_cols = {"Stato", "Azione Suggerita", "Entry Zone", "Risk Flag", "Trend", "Tipo", "Categoria", "Decisione", "Bucket", "Cosa fare", "AF Bucket", "Priorita", "Priorità", "Tipo Copertura", "Strumento preferito", "Fase", "Stato lettura", "Ruolo"}
    if col in score_cols:
        return _score_bar(value)
    if col in badge_cols:
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
        "Note AI", "Trigger Monitoraggio", "Azione Suggerita", "Scenario Base", "Scenario Negativo",
        "Azione Pratica", "Cosa fare adesso", "Cosa fare in pratica", "Perché", "Perche", "Perche guardarlo",
        "Rischio principale", "Nota Fineco/Consulente", "ETF/Fondo candidato", "Cosa fare", "Domanda", "Perche",
        "Domanda consulente", "Stato lettura", "Note"
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


def _count_bucket(df: pd.DataFrame | None, col: str, value: str) -> int:
    if df is None or df.empty or col not in df.columns:
        return 0
    return int(df[col].astype(str).eq(value).sum())


def _portfolio_is_example(fineco_portfolio: pd.DataFrame | None) -> bool:
    if fineco_portfolio is None or fineco_portfolio.empty or "ISIN" not in fineco_portfolio.columns:
        return True
    return bool(fineco_portfolio["ISIN"].astype(str).str.startswith("ESEMPIO").all())


def build_text_report(
    ranking: pd.DataFrame,
    allocation: pd.DataFrame,
    watchlist: pd.DataFrame | None = None,
    insights: pd.DataFrame | None = None,
    action_plan: pd.DataFrame | None = None,
    sector_compass: pd.DataFrame | None = None,
    fineco_portfolio: pd.DataFrame | None = None,
    fineco_summary: dict | None = None,
    fineco_questions: pd.DataFrame | None = None,
) -> str:
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    brief = build_action_brief(action_plan, insights)
    summary = fineco_summary or {}
    lines = [
        "AlphaForge Intelligence v8 - Fineco Portfolio Tracker",
        f"Aggiornato il {now}",
        "",
        "Report informativo. Non costituisce consulenza finanziaria personalizzata.",
        "Obiettivo: separare core gia' gestito, satelliti settoriali e controllo rendimento del portafoglio Fineco.",
        "",
        "Portafoglio Fineco:",
        f"- Fase: {summary.get('fase', 'Non configurato')}",
        f"- Capitale una tantum: {summary.get('capitale_una_tantum_eur', 'n/d')} EUR",
        f"- PAC mensile: {summary.get('pac_mensile_eur', 'n/d')} EUR",
        f"- Capitale versato stimato: {summary.get('capitale_versato_stimato_eur', 'n/d')} EUR",
        f"- Rendimento stimato: {summary.get('rendimento_pct', 'n/d')}%",
        "",
        "Cosa fare adesso:",
        "- Se hai sottoscritto oggi, non giudicare ancora la performance: crea il punto zero.",
        "- Verifica su Fineco data valuta, prima rata PAC, quote assegnate e prezzo medio.",
        "- Chiedi al consulente costi totali, sottostanti e benchmark di confronto.",
        "",
        "Bussola settoriale:",
    ]
    if sector_compass is not None and not sector_compass.empty:
        for _, row in sector_compass.head(6).iterrows():
            lines.append(f"- {row.get('Settore','')}: {row.get('Bucket','')} | {row.get('Cosa fare','')} | candidato: {row.get('ETF/Fondo candidato','')} ({row.get('Ticker ETF/Fondo','')})")
    else:
        lines.append("- Bussola settoriale non disponibile.")
    lines += ["", "Priorita' operative:"]
    for line in getattr(brief, "narrative", [])[:6]:
        lines.append(f"- {line}")
    if fineco_questions is not None and not fineco_questions.empty:
        lines += ["", "Domande per il consulente:"]
        for _, row in fineco_questions.head(6).iterrows():
            lines.append(f"- {row.get('Tema','')}: {row.get('Domanda','')}")
    lines += ["", "Prima di investire controllare sempre: KID, costi, fiscalita', liquidita', valuta, dimensione fondo, sovrapposizione con All-World e adeguatezza con il consulente."]
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
    fineco_portfolio: pd.DataFrame | None = None,
    fineco_summary: dict | None = None,
    fineco_questions: pd.DataFrame | None = None,
) -> None:
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    best = _best_row(ranking, "Score Finale")
    best_sector = _best_row(sector_compass, "Sector Score")
    best_priority = _best_row(insights, "Priority Score")
    status_text = status.get("status", "unknown") if isinstance(status, dict) else "unknown"
    focus = build_focus_board(action_plan, insights, limit=12)
    summary = fineco_summary or {}
    is_example = _portfolio_is_example(fineco_portfolio)

    if sector_compass is not None and not sector_compass.empty:
        sector_compass = sector_compass.sort_values("Sector Score", ascending=False, na_position="last")
    core_count = _count_bucket(sector_compass, "Bucket", "Da discutere ora")
    strategic_watch = _count_bucket(sector_compass, "Bucket", "Watchlist strategica")
    risky_count = _count_bucket(sector_compass, "Bucket", "Tema forte ma rischioso")
    first_sector = best_sector.get("Settore", "n/d")
    first_action = best_sector.get("Cosa fare", "Classifica prima il portafoglio e discuti eventuali satelliti con il consulente.")

    phase = summary.get("fase", "Non configurato")
    one_off = summary.get("capitale_una_tantum_eur", 0)
    pac_monthly = summary.get("pac_mensile_eur", 0)
    invested = summary.get("capitale_versato_stimato_eur", 0)
    perf = summary.get("rendimento_pct", 0)
    health = summary.get("portfolio_health_score", 0)
    portfolio_message = summary.get("messaggio_principale", "Carica il portafoglio Fineco nella pagina Streamlit per il tracking privato.")

    privacy_note = "Dashboard pubblica in modalita' privacy: non pubblica dati personali. Carica il CSV reale solo nell'app Streamlit o usa repo privato." if is_example else "Portafoglio configurato nel repo: ricordati che questa pagina e' pubblica se il repository e' pubblico."

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
    .advisor { border-color:rgba(255,211,122,.25); background:linear-gradient(135deg, rgba(255,211,122,.10), rgba(255,255,255,.04)); } .privacy { border-color:rgba(142,181,255,.25); background:linear-gradient(135deg, rgba(142,181,255,.10), rgba(255,255,255,.04)); }
    .table-wrap { overflow:auto; border-radius:18px; border:1px solid rgba(255,255,255,.09); margin-top:14px; } table { width:100%; border-collapse:collapse; min-width:920px; } th,td { padding:12px 13px; border-bottom:1px solid rgba(255,255,255,.075); text-align:left; vertical-align:top; font-size:13px; } th { position:sticky; top:0; background:rgba(9,15,32,.96); color:#d9e4ff; font-size:12px; text-transform:uppercase; letter-spacing:.06em; } td.long { min-width:270px; color:#dbe6ff; line-height:1.42; } tr:hover td { background:rgba(255,255,255,.035); }
    .scorebar { min-width:112px; height:24px; border-radius:999px; background:rgba(255,255,255,.08); overflow:hidden; position:relative; border:1px solid rgba(255,255,255,.08); } .scorebar span { display:block; height:100%; background:linear-gradient(90deg, var(--green), var(--blue)); } .scorebar b { position:absolute; inset:0; display:flex; align-items:center; justify-content:center; font-size:12px; }
    .two { display:grid; grid-template-columns:1fr 1fr; gap:18px; } .footer { margin-top:24px; color:var(--muted); font-size:13px; line-height:1.5; } a { color:var(--green); }
    @media (max-width:980px){ .grid,.decision-grid,.two{grid-template-columns:1fr 1fr}.span2,.span3{grid-column:span 1} } @media (max-width:640px){ .container{width:min(100% - 18px,1280px)} .hero,section{border-radius:22px;padding:20px}.grid,.decision-grid,.two{grid-template-columns:1fr} h1{font-size:40px} }
    </style>
    """

    html = f"""<!doctype html>
<html lang='it'>
<head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'><title>AlphaForge v8 Fineco Portfolio Tracker</title>{css}</head>
<body><div class='container'>
  <div class='nav'><b>AlphaForge Trader</b><span>{_badge('Stato update: ' + str(status_text))}</span></div>
  <div class='hero'>
    <span class='pill good'>✦ AlphaForge v8 Fineco Portfolio Tracker</span>
    <h1>Prima il portafoglio, poi i settori.</h1>
    <p class='subtitle'>Pensato per un uso realistico con Fineco e consulente: crea il punto zero dei fondi/PAC, misura rendimento e pesi nel tempo, poi valuta solo eventuali satelliti settoriali.</p>
    <div class='grid'>
      <div class='card span2'><div class='label'>Fase portafoglio</div><div class='value'>{escape(str(phase))}</div><div class='hint'>{escape(str(portfolio_message))}</div></div>
      <div class='card'><div class='label'>Una tantum</div><div class='value'>{escape(format_number(one_off,0))} €</div><div class='hint'>Capitale iniziale</div></div>
      <div class='card'><div class='label'>PAC mensile</div><div class='value'>{escape(format_number(pac_monthly,0))} €</div><div class='hint'>Versamenti programmati</div></div>
      <div class='card'><div class='label'>Versato stimato</div><div class='value'>{escape(format_number(invested,0))} €</div><div class='hint'>Da baseline</div></div>
      <div class='card'><div class='label'>Health score</div><div class='value'>{escape(format_number(health,1))}</div><div class='hint'>Qualità struttura, non rendimento</div></div>
    </div>
  </div>

  <section class='privacy'>
    <h2>1. Cosa fare adesso</h2>
    <p class='muted'>{escape(str(privacy_note))}</p>
    <div class='big-action'>Se i fondi/PAC sono stati sottoscritti oggi, non giudicare il rendimento: verifica data valuta, quote assegnate, prezzo medio, prima rata PAC, costi e benchmark. Il primo controllo utile e' tra 1 mese; la prima valutazione seria tra 6-12 mesi.</div>
    <div class='decision-grid'>
      <div class='decision'><span class='muted'>Oggi</span><b>Punto zero</b><small class='muted'>Registra importi, quote, date.</small></div>
      <div class='decision'><span class='muted'>1 mese</span><b>Controllo esecuzione</b><small class='muted'>PAC e NAV valorizzati.</small></div>
      <div class='decision'><span class='muted'>3-6 mesi</span><b>Pesi e sovrapposizioni</b><small class='muted'>Core, Europa, emergenti, tech.</small></div>
      <div class='decision'><span class='muted'>12 mesi</span><b>Rendimento vs benchmark</b><small class='muted'>Valutazione più sensata.</small></div>
    </div>
  </section>

  <section>
    <h2>2. Tracker Fineco</h2>
    <p class='muted'>Questa tabella e' utile soprattutto nell'app Streamlit, dove puoi caricare il CSV reale senza pubblicarlo nella dashboard.</p>
    {compact_table(fineco_portfolio, ['ISIN','Nome Strumento','Ruolo','Tipo Versamento','Data Inizio','Capitale versato stimato EUR','Valore attuale stimato EUR','Guadagno/Perdita EUR','Rendimento %','Peso attuale %','Stato lettura'], 12)}
  </section>

  <section class='advisor'>
    <h2>3. Domande da portare al consulente Fineco</h2>
    <p class='muted'>Queste sono le domande piu' utili prima di aggiungere nuovi settori o strumenti.</p>
    {compact_table(fineco_questions, ['Priorita','Tema','Domanda','Perche'], 12)}
  </section>

  <section>
    <h2>4. Bussola settoriale</h2>
    <p class='muted'>Dopo aver capito il portafoglio esistente, scegli pochi settori satellite da discutere. ETF/fondo come default; azione singola solo per quota piccola e consapevole.</p>
    {compact_table(sector_compass, ['Priorita','Settore','Bucket','Cosa fare','Sector Score','Strumento preferito','Ticker ETF/Fondo','ETF/Fondo candidato','Range pratico','Perche guardarlo','Rischio principale','Nota Fineco/Consulente'], 12)}
  </section>

  <div class='two'>
    <section><h2>5. Priorita' operative</h2><p class='muted'>Da leggere dopo il portafoglio e la bussola settoriale.</p>{compact_table(focus, ['Priorita','Ticker','AF Bucket','Decisione','Cosa fare in pratica','Priority Score','Entry Zone','Risk Flag'], 8)}</section>
    <section><h2>6. Strumenti candidati</h2><p class='muted'>Lista candidati da verificare su Fineco: costi, KID, disponibilita' e adeguatezza.</p>{compact_table(sector_compass, ['Settore','Strumento preferito','Ticker ETF/Fondo','ETF/Fondo candidato','Azioni leader','Range pratico'], 10)}</section>
  </div>

  <section>
    <h2>7. Allocazione modello</h2>
    <p class='muted'>Esempio informativo su 1000 EUR. Non sostituisce la consulenza e non considera il tuo patrimonio totale.</p>
    {compact_table(allocation, ['Ticker','Nome ETF','Categoria','Peso Target %','Importo su 1000 EUR','Razionale'], 8)}
  </section>

  <section>
    <h2>8. Lettura prudente</h2>
    <p class='muted'>Aggiornato il {escape(now)}. Miglior ETF quantitativo: <b>{escape(str(best.get('Ticker', 'n/d')))}</b>. Migliore priorita' strumento: <b>{escape(str(best_priority.get('Ticker', 'n/d')))}</b>. Settore da discutere per primo: <b>{escape(str(first_sector))}</b> ({escape(str(first_action))}).</p>
    <p class='muted'>Informazioni a scopo educativo e di monitoraggio. Non costituiscono consulenza finanziaria personalizzata, sollecitazione all'investimento o garanzia di rendimento. Verificare sempre KID, costi, liquidita', fiscalita', adeguatezza e disponibilita' su Fineco.</p>
  </section>
  <div class='footer'>AlphaForge v8 Fineco Portfolio Tracker · Punto zero portafoglio + bussola settoriale · File generati automaticamente da GitHub Actions.</div>
</div></body></html>"""
    output.write_text(html, encoding="utf-8")
