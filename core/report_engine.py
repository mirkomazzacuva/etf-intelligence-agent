from __future__ import annotations

from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any

import pandas as pd


def _as_float(value: object, default: float = 0.0) -> float:
    try:
        if pd.isna(value):
            return default
        if isinstance(value, str):
            text = value.replace("€", "").replace("EUR", "").replace("%", "").replace(" ", "").strip()
            if text == "":
                return default
            if "," in text and "." in text:
                if text.rfind(",") > text.rfind("."):
                    text = text.replace(".", "").replace(",", ".")
                else:
                    text = text.replace(",", "")
            elif "," in text:
                text = text.replace(",", ".")
            value = text
        return float(value)
    except Exception:  # noqa: BLE001
        return default


def format_number(value: object, digits: int = 2) -> str:
    try:
        if pd.isna(value):
            return ""
        return f"{float(value):,.{digits}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:  # noqa: BLE001
        return str(value if value is not None else "")


def euro(value: object, digits: int = 0) -> str:
    return f"{format_number(value, digits)} €"


def pct(value: object, digits: int = 2) -> str:
    try:
        return f"{float(value):+,.{digits}f}%".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:  # noqa: BLE001
        return "n/d"


def _badge(value: object) -> str:
    text = str(value or "n/d")
    low = text.lower()
    cls = ""
    if any(x in low for x in ["tieni", "success", "positivo", "favorevole", "continua"]):
        cls = " good"
    elif any(x in low for x in ["monitor", "attendi", "neutro", "sotto esame", "watch"]):
        cls = " watch"
    elif any(x in low for x in ["switch", "attenzione", "debole", "negativa", "non aumentare"]):
        cls = " danger"
    return f"<span class='pill{cls}'>{escape(text)}</span>"


def _format_cell(col: str, value: object) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    badge_cols = {"Decisione pratica", "Quando valutare switch", "News bias", "Fonte valore", "Ruolo", "Tipo", "Categoria", "Trend proxy", "Cosa fare", "Bias prossimi giorni"}
    pct_cols = {"Margine netto %", "Costo annuo %", "Rendimento atteso netto 3M %", "Rendimento atteso netto 1Y %", "Proxy return da inizio %", "Rendimento proxy 1D %", "Rendimento proxy 1M %", "Rendimento proxy 3M %", "Rendimento proxy 1Y %", "Rendimento atteso netto 3M %", "Rendimento atteso netto 1Y %"}
    eur_cols = {"Capitale versato EUR", "Valore attuale EUR", "Margine netto EUR", "Costo maturato stimato EUR", "PAC mensile EUR", "Proiezione 3M base EUR", "Proiezione 1Y base EUR", "Importo Iniziale EUR", "PAC Mensile EUR", "Controvalore attuale EUR", "Margine lordo EUR", "Guadagno stimato 3M EUR", "Guadagno stimato 1Y EUR", "Bollo sottratto EUR"}
    if col in badge_cols:
        return _badge(value)
    if col in pct_cols:
        return f"<span class='num'>{escape(pct(value))}</span>"
    if col in eur_cols:
        return f"<span class='num'>{escape(euro(value, 0))}</span>"
    if isinstance(value, (float, int)):
        return f"<span class='num'>{escape(format_number(value, 2))}</span>"
    text = str(value)
    if text.startswith("http"):
        return f"<a href='{escape(text)}' target='_blank'>link</a>"
    return escape(text)


def compact_table(df: pd.DataFrame | None, columns: list[str], limit: int = 10) -> str:
    if df is None or df.empty:
        return "<p class='muted'>Nessun dato disponibile.</p>"
    cols = [c for c in columns if c in df.columns]
    if not cols:
        return "<p class='muted'>Colonne non disponibili.</p>"
    rows: list[str] = []
    for _, row in df.head(limit).iterrows():
        cells = []
        for col in cols:
            css = " class='long'" if col in {"Fondo/PAC", "Nome Strumento", "Motivo", "Quando valutare switch", "Titolo", "Cosa fare"} else ""
            cells.append(f"<td{css}>{_format_cell(col, row.get(col, ''))}</td>")
        rows.append(f"<tr>{''.join(cells)}</tr>")
    th = "".join(f"<th>{escape(c)}</th>" for c in cols)
    return f"<div class='table-wrap'><table><thead><tr>{th}</tr></thead><tbody>{''.join(rows)}</tbody></table></div>"


def _line_chart_svg(history: pd.DataFrame, fund_name: str, width: int = 520, height: int = 210) -> str:
    if history is None or history.empty:
        return ""
    required = {"Nome Strumento", "Normalized 100", "Date"}
    if not required.issubset(set(history.columns)):
        return ""
    df = history[history["Nome Strumento"].astype(str) == str(fund_name)].copy()
    if df.empty:
        return ""
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Normalized 100"] = pd.to_numeric(df["Normalized 100"], errors="coerce")
    df = df.dropna(subset=["Date", "Normalized 100"]).sort_values("Date")
    if len(df) < 2:
        return ""
    if len(df) > 150:
        df = df.iloc[:: max(1, len(df) // 150)].copy()
    vals = df["Normalized 100"].tolist()
    min_v, max_v = min(vals), max(vals)
    if min_v == max_v:
        min_v -= 1
        max_v += 1
    pad = (max_v - min_v) * 0.12
    min_v -= pad
    max_v += pad
    left, right, top, bottom = 42, 12, 18, 34
    plot_w = width - left - right
    plot_h = height - top - bottom
    pts: list[str] = []
    for i, value in enumerate(vals):
        x = left + (i / max(1, len(vals) - 1)) * plot_w
        y = top + (max_v - value) / (max_v - min_v) * plot_h
        pts.append(f"{x:.1f},{y:.1f}")
    change = vals[-1] - vals[0]
    cls = "pos" if change >= 0 else "neg"
    start_date = df["Date"].iloc[0].strftime("%d/%m")
    end_date = df["Date"].iloc[-1].strftime("%d/%m")
    label = format_number(vals[-1], 1)
    change_label = f"{change:+.1f}".replace(".", ",")
    grid = []
    for ratio in [0, .5, 1]:
        y = top + ratio * plot_h
        grid.append(f"<line x1='{left}' y1='{y:.1f}' x2='{width-right}' y2='{y:.1f}' class='gridline'/>")
    last_x, last_y = pts[-1].split(",")
    return f"""
    <div class='mini-chart'>
      <div class='chart-head'><b>{escape(fund_name)}</b><span class='{cls}'>{escape(change_label)} pt</span></div>
      <svg viewBox='0 0 {width} {height}' role='img' aria-label='Grafico {escape(fund_name)}'>
        {''.join(grid)}
        <text x='0' y='{top+4}' class='axis'>{escape(format_number(max_v,1))}</text>
        <text x='0' y='{top+plot_h:.0f}' class='axis'>{escape(format_number(min_v,1))}</text>
        <polyline points='{' '.join(pts)}' class='spark {cls}' fill='none'/>
        <circle cx='{last_x}' cy='{last_y}' r='4' class='dot {cls}'/>
        <text x='{left}' y='{height-8}' class='axis'>{escape(start_date)}</text>
        <text x='{width-right-54}' y='{height-8}' class='axis'>{escape(end_date)}</text>
        <text x='{width-right-65}' y='{top+16}' class='last {cls}'>{escape(label)}</text>
      </svg>
    </div>"""


def _charts_grid(history: pd.DataFrame | None) -> str:
    if history is None or history.empty or "Nome Strumento" not in history.columns:
        return "<p class='muted'>Grafici non disponibili: esegui l'Auto update completo o controlla i proxy ticker.</p>"
    names = history["Nome Strumento"].dropna().astype(str).drop_duplicates().tolist()[:7]
    cards = [_line_chart_svg(history, name) for name in names]
    cards = [c for c in cards if c]
    if not cards:
        return "<p class='muted'>Storico presente ma non sufficiente per disegnare i grafici.</p>"
    return f"<div class='charts-grid'>{''.join(cards)}</div>"


def _margin_cards(decision: pd.DataFrame | None) -> str:
    if decision is None or decision.empty or "Margine netto EUR" not in decision.columns:
        return "<p class='muted'>Margini non disponibili.</p>"
    vals = decision.copy()
    vals["Margine netto EUR"] = pd.to_numeric(vals["Margine netto EUR"], errors="coerce").fillna(0)
    max_abs = max(1.0, float(vals["Margine netto EUR"].abs().max()))
    cards = []
    for _, r in vals.iterrows():
        margin = float(r["Margine netto EUR"])
        cls = "pos" if margin >= 0 else "neg"
        width = min(100, abs(margin) / max_abs * 100)
        cards.append(
            f"<div class='margin-row'><div><b>{escape(str(r.get('Fondo/PAC','')))}</b><span>{escape(str(r.get('Decisione pratica','')))}</span></div>"
            f"<div class='margin-num {cls}'>{escape(euro(margin,0))}</div><div class='bar'><i class='{cls}' style='width:{width:.1f}%'></i></div></div>"
        )
    return f"<div class='margin-list'>{''.join(cards)}</div>"


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
    fund_performance: pd.DataFrame | None = None,
    news_radar: pd.DataFrame | None = None,
    news_summary: dict | None = None,
    decision_cockpit: pd.DataFrame | None = None,
    decision_summary: dict | None = None,
) -> str:
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    ds = decision_summary or {}
    lines = [
        "AlphaForge v11 Live Value Cockpit",
        f"Aggiornato il {now}",
        "",
        f"Capitale versato: {ds.get('capitale_versato_eur', 'n/d')} EUR",
        f"Valore attuale: {ds.get('valore_attuale_eur', 'n/d')} EUR",
        f"Margine netto: {ds.get('margine_netto_eur', 'n/d')} EUR",
        f"Proiezione 3M base: {ds.get('proiezione_3m_base_eur', 'n/d')} EUR",
        f"Proiezione 1Y base: {ds.get('proiezione_1y_base_eur', 'n/d')} EUR",
        f"Decisione sintesi: {ds.get('decisione_sintesi', 'n/d')}",
        "",
        "Nota: il margine esatto richiede il controvalore Fineco reale. Le proiezioni sono scenari, non previsioni garantite.",
    ]
    if decision_cockpit is not None and not decision_cockpit.empty:
        lines += ["", "Decisioni per fondo:"]
        for _, row in decision_cockpit.iterrows():
            lines.append(f"- {row.get('Fondo/PAC','')}: margine {row.get('Margine netto EUR','n/d')} EUR, 1Y {row.get('Proiezione 1Y base EUR','n/d')} EUR, {row.get('Decisione pratica','n/d')}")
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
    fund_performance: pd.DataFrame | None = None,
    fund_history: pd.DataFrame | None = None,
    news_radar: pd.DataFrame | None = None,
    news_summary: dict | None = None,
    decision_cockpit: pd.DataFrame | None = None,
    decision_summary: dict | None = None,
) -> None:
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    ds = decision_summary or {}
    status_text = str(status.get("status", "unknown") if isinstance(status, dict) else "unknown")
    status_version = str(status.get("version", "AlphaForge v11") if isinstance(status, dict) else "AlphaForge v11")
    decision_text = str(ds.get("decisione_sintesi", "Tieni e monitora"))
    latest_proxy = str(ds.get("latest_proxy_date", "n/d"))
    news_funds = pd.DataFrame((news_summary or {}).get("funds", [])) if isinstance(news_summary, dict) else pd.DataFrame()

    css = """
    <style>
    :root{--bg:#f3f5f8;--panel:#fff;--text:#111827;--muted:#667085;--line:#d9dee7;--green:#068647;--red:#d92d20;--blue:#175cd3;--amber:#b54708;--dark:#111827;--soft:#f8fafc}
    *{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font-family:Inter,ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif}.wrap{width:min(100% - 24px,1440px);margin:0 auto;padding:16px 0 30px}.topbar{display:flex;justify-content:space-between;align-items:center;background:#0b1220;color:#fff;border-radius:14px;padding:12px 16px;position:sticky;top:8px;z-index:10;box-shadow:0 12px 32px rgba(15,23,42,.22)}.brand{font-weight:950;letter-spacing:-.02em}.hero{margin-top:14px;border:1px solid var(--line);border-radius:18px;background:var(--panel);padding:22px;box-shadow:0 10px 24px rgba(15,23,42,.06)}h1{font-size:38px;line-height:1;margin:10px 0;letter-spacing:-.045em}.subtitle{color:var(--muted);font-size:16px;line-height:1.55;max-width:980px}.pill{display:inline-flex;align-items:center;border-radius:999px;padding:5px 10px;background:#e0f2fe;color:#075985;font-size:12px;font-weight:900;white-space:nowrap}.pill.good{background:#dcfce7;color:#166534}.pill.watch{background:#fef3c7;color:#92400e}.pill.danger{background:#fee2e2;color:#991b1b}.kpis{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:12px;margin-top:16px}.kpi{background:var(--soft);border:1px solid var(--line);border-radius:16px;padding:14px}.label{font-size:11px;text-transform:uppercase;letter-spacing:.07em;color:var(--muted);font-weight:950}.value{font-size:27px;font-weight:950;letter-spacing:-.04em;margin-top:4px}.hint{font-size:12px;color:var(--muted);line-height:1.35;margin-top:4px}section{margin-top:14px;background:var(--panel);border:1px solid var(--line);border-radius:18px;padding:18px;box-shadow:0 8px 20px rgba(15,23,42,.04)}h2{font-size:22px;margin:0 0 8px;letter-spacing:-.035em}.muted{color:var(--muted);line-height:1.55}.two{display:grid;grid-template-columns:1.15fr .85fr;gap:14px}.three{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}.callout{padding:14px;border:1px solid #bfdbfe;background:#eff6ff;border-radius:14px;line-height:1.45;font-weight:800}.table-wrap{overflow:auto;border:1px solid var(--line);border-radius:14px;margin-top:10px}table{border-collapse:collapse;width:100%;min-width:1060px}th,td{padding:10px 11px;border-bottom:1px solid var(--line);font-size:13px;text-align:left;vertical-align:top}th{background:#f8fafc;text-transform:uppercase;font-size:10px;letter-spacing:.06em;color:#475467;position:sticky;top:0}td.long{min-width:250px}.num{font-variant-numeric:tabular-nums;font-weight:800}.pos{color:var(--green)}.neg{color:var(--red)}.charts-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin-top:12px}.mini-chart{background:#fff;border:1px solid var(--line);border-radius:16px;padding:12px}.chart-head{display:flex;justify-content:space-between;gap:12px;align-items:center;margin-bottom:6px;font-size:13px}.gridline{stroke:#e5e7eb;stroke-width:1}.spark{stroke-width:2.5}.spark.pos{stroke:var(--green)}.spark.neg{stroke:var(--red)}.dot.pos{fill:var(--green)}.dot.neg{fill:var(--red)}.axis{font-size:11px;fill:#667085}.last{font-size:13px;font-weight:950}.margin-list{display:grid;gap:10px;margin-top:10px}.margin-row{border:1px solid var(--line);border-radius:14px;padding:12px;background:#fff}.margin-row>div:first-child{display:flex;justify-content:space-between;gap:10px}.margin-row span{color:var(--muted);font-size:12px}.margin-num{font-size:20px;font-weight:950;margin:6px 0}.bar{height:8px;background:#edf1f7;border-radius:999px;overflow:hidden}.bar i{display:block;height:100%;border-radius:999px}.bar i.pos{background:var(--green)}.bar i.neg{background:var(--red)}.footer{margin-top:14px;color:var(--muted);font-size:13px;line-height:1.5}@media(max-width:1100px){.kpis{grid-template-columns:repeat(3,1fr)}.two,.three,.charts-grid{grid-template-columns:1fr}}@media(max-width:680px){.kpis{grid-template-columns:1fr}h1{font-size:31px}.wrap{width:min(100% - 14px,1440px)}}
    </style>
    """

    html = f"""<!doctype html>
<html lang='it'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'><title>AlphaForge v11 Live Value Cockpit</title>{css}</head>
<body><div class='wrap'>
  <div class='topbar'><div class='brand'>📈 AlphaForge Fineco Cockpit</div><div>{_badge('Update: ' + status_text)} {_badge(status_version)}</div></div>
  <div class='hero'>
    <span class='pill good'>AlphaForge v11</span> <span class='pill'>Live Value Cockpit</span>
    <h1>Controvalore aggiornato, margine netto e proiezioni per ogni fondo.</h1>
    <p class='subtitle'>Vista piu' semplice: prima il guadagno/perdita netto, poi le proiezioni a 3 mesi e 1 anno, infine una lettura pratica: tenere, monitorare o valutare switch con il consulente.</p>
    <div class='kpis'>
      <div class='kpi'><div class='label'>Capitale versato</div><div class='value'>{escape(euro(ds.get('capitale_versato_eur',0),0))}</div><div class='hint'>Una tantum + PAC gia' valorizzati</div></div>
      <div class='kpi'><div class='label'>Valore attuale</div><div class='value'>{escape(euro(ds.get('valore_attuale_eur',0),0))}</div><div class='hint'>Da Fineco manuale o proxy</div></div>
      <div class='kpi'><div class='label'>Margine netto</div><div class='value'>{escape(euro(ds.get('margine_netto_eur',0),0))}</div><div class='hint'>Netto bollo una tantum</div></div>
      <div class='kpi'><div class='label'>Proiezione 3 mesi</div><div class='value'>{escape(euro(ds.get('proiezione_3m_base_eur',0),0))}</div><div class='hint'>Scenario base, non garanzia</div></div>
      <div class='kpi'><div class='label'>Proiezione 1 anno</div><div class='value'>{escape(euro(ds.get('proiezione_1y_base_eur',0),0))}</div><div class='hint'>Include PAC futuri</div></div>
      <div class='kpi'><div class='label'>Sintesi</div><div class='value' style='font-size:19px'>{escape(decision_text)}</div><div class='hint'>Ultimo proxy: {escape(latest_proxy)}</div></div>
    </div>
  </div>

  <section><h2>Lettura rapida</h2><div class='callout'>{escape(str(ds.get('messaggio','Il margine esatto richiede il controvalore Fineco aggiornato.')))}</div><p class='muted'>Aggiornato il {escape(now)}. Se oggi e' mattina, sui fondi comuni puo' essere normale vedere ancora il NAV dell'ultimo giorno lavorativo precedente.</p></section>

  <section><h2>Decisione per fondo</h2><p class='muted'>Questa e' la tabella principale: qui vedi subito margine netto, costo, proiezioni e cosa fare.</p>{compact_table(decision_cockpit, ['Fondo/PAC','Tipo','Capitale versato EUR','Valore attuale EUR','Margine netto EUR','Margine netto %','Costo annuo %','Proiezione 3M base EUR','Proiezione 1Y base EUR','Decisione pratica','Quando valutare switch'], 12)}</section>

  <div class='two'>
    <section><h2>Margine netto per fondo</h2><p class='muted'>Se non hai ancora inserito i valori reali Fineco, i fondi una tantum partono da 5.000 € e il margine resta quasi a zero.</p>{_margin_cards(decision_cockpit)}</section>
    <section><h2>News e bias</h2><p class='muted'>Serve solo per capire se il contesto puo' aiutare o pesare nei prossimi giorni.</p>{compact_table(news_funds, ['Nome Strumento','Bias prossimi giorni','Cosa fare'], 8)}</section>
  </div>

  <section><h2>Grafici fondi/proxy</h2><p class='muted'>Grafici normalizzati a base 100 sui proxy di mercato. Il NAV ufficiale resta Fineco.</p>{_charts_grid(fund_history)}</section>

  <div class='two'>
    <section><h2>Performance proxy</h2>{compact_table(fund_performance, ['Nome Strumento','Proxy usato','Rendimento proxy 1D %','Rendimento proxy 1M %','Rendimento proxy 3M %','Rendimento proxy 1Y %','Trend proxy'], 10)}</section>
    <section><h2>Tracker Fineco dettagliato</h2>{compact_table(fineco_portfolio, ['ISIN','Nome Strumento','Capitale versato stimato EUR','Valore attuale stimato EUR','Guadagno/Perdita EUR','Rendimento %','Stato lettura'], 10)}</section>
  </div>

  <section><h2>Notizie finanziarie collegate</h2>{compact_table(news_radar, ['Nome Strumento','Titolo','Fonte','News Score','Lettura','Impatto possibile','Link'], 12)}</section>

  <section><h2>Regola pratica</h2><div class='three'><div class='callout'>Non vendere solo per pochi giorni negativi: i fondi sono appena partiti.</div><div class='callout'>Core Dividend va controllato di piu' perche' costa molto: deve giustificare il 3,40%.</div><div class='callout'>Per decidere uno switch servono almeno 3-6 mesi di confronto col benchmark, meglio 12 mesi.</div></div></section>

  <section><h2>Avvertenza</h2><p class='muted'>Dashboard informativa. Le proiezioni sono scenari basati su proxy, momentum e costi stimati, non sono previsioni garantite ne' consulenza finanziaria personalizzata.</p></section>
  <div class='footer'>AlphaForge v11 Live Value Cockpit · File statici generati da GitHub Actions. La versione Streamlit aggiorna i proxy all'apertura.</div>
</div></body></html>"""
    output.write_text(html, encoding="utf-8")
