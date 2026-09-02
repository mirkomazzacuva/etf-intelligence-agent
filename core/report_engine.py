from __future__ import annotations

import json
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any

import pandas as pd

try:
    from core.config import FINECO_FUNDS_PUBLIC_FILE
except Exception:  # noqa: BLE001
    FINECO_FUNDS_PUBLIC_FILE = Path("data/fineco_funds_public.csv")


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


def _read_public_funds() -> pd.DataFrame:
    try:
        return pd.read_csv(FINECO_FUNDS_PUBLIC_FILE) if Path(FINECO_FUNDS_PUBLIC_FILE).exists() else pd.DataFrame()
    except Exception:  # noqa: BLE001
        return pd.DataFrame()


def _portfolio_totals(fineco_portfolio: pd.DataFrame | None, fineco_summary: dict | None) -> dict[str, float]:
    public = _read_public_funds()
    if not public.empty:
        return {
            "one_off": float(public.get("Importo Iniziale EUR", pd.Series(dtype=float)).apply(_as_float).sum()),
            "pac": float(public.get("PAC Mensile EUR", pd.Series(dtype=float)).apply(_as_float).sum()),
            "bollo": float(public.get("Bollo Una Tantum EUR", pd.Series(dtype=float)).apply(_as_float).sum()),
            "tracked": float(len(public)),
        }
    if fineco_portfolio is not None and not fineco_portfolio.empty:
        one_off_col = "Importo Iniziale EUR" if "Importo Iniziale EUR" in fineco_portfolio.columns else None
        pac_col = "PAC Mensile EUR" if "PAC Mensile EUR" in fineco_portfolio.columns else None
        return {
            "one_off": float(fineco_portfolio[one_off_col].apply(_as_float).sum()) if one_off_col else 0.0,
            "pac": float(fineco_portfolio[pac_col].apply(_as_float).sum()) if pac_col else 0.0,
            "bollo": 42.0,
            "tracked": float(len(fineco_portfolio)),
        }
    summary = fineco_summary or {}
    return {
        "one_off": _as_float(summary.get("capitale_una_tantum_eur", 0)),
        "pac": _as_float(summary.get("pac_mensile_eur", 0)),
        "bollo": 42.0,
        "tracked": _as_float(summary.get("numero_strumenti", 0)),
    }


def _badge(value: object) -> str:
    text = str(value or "n/d")
    low = text.lower()
    cls = ""
    if any(x in low for x in ["positivo", "favorevole", "ok", "core", "punto zero", "success"]):
        cls = " good"
    elif any(x in low for x in ["monitor", "laterale", "neutro", "pac", "rimbalzo", "watch"]):
        cls = " watch"
    elif any(x in low for x in ["attenzione", "debole", "rischio", "negative", "pressione", "caro", "elevato"]):
        cls = " danger"
    return f"<span class='pill{cls}'>{escape(text)}</span>"


def _format_cell(col: str, value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and pd.isna(value):
        return ""
    badge_cols = {"Trend proxy", "Azione pratica", "Ruolo", "Tipo Versamento", "Categoria AlphaForge", "Bias prossimi giorni", "Cosa fare", "Lettura", "Impatto possibile", "Fase", "Stato lettura"}
    pct_cols = {"Rendimento proxy 1D %", "Rendimento proxy 1M %", "Rendimento proxy 3M %", "Rendimento proxy 1Y %", "Rendimento %", "Costo annuo %", "Peso attuale %"}
    eur_cols = {"Importo iniziale EUR", "PAC mensile EUR", "Importo Iniziale EUR", "PAC Mensile EUR", "Capitale versato stimato EUR", "Valore attuale stimato EUR", "Guadagno/Perdita EUR", "Bollo una tantum EUR"}
    if col in badge_cols:
        return _badge(value)
    if col in pct_cols:
        return f"<span class='num'>{escape(format_number(value, 2))}%</span>"
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
            css = " class='long'" if col in {"Nome Strumento", "Azione pratica", "Titolo", "Domanda", "Perche", "Nota", "Note"} else ""
            cells.append(f"<td{css}>{_format_cell(col, row.get(col, ''))}</td>")
        rows.append(f"<tr>{''.join(cells)}</tr>")
    th = "".join(f"<th>{escape(c)}</th>" for c in cols)
    return f"<div class='table-wrap'><table><thead><tr>{th}</tr></thead><tbody>{''.join(rows)}</tbody></table></div>"


def _line_chart_svg(history: pd.DataFrame, fund_name: str, width: int = 520, height: int = 210) -> str:
    if history is None or history.empty:
        return ""
    if "Nome Strumento" not in history.columns or "Normalized 100" not in history.columns or "Date" not in history.columns:
        return ""
    df = history[history["Nome Strumento"].astype(str) == str(fund_name)].copy()
    if df.empty:
        return ""
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Normalized 100"] = pd.to_numeric(df["Normalized 100"], errors="coerce")
    df = df.dropna(subset=["Date", "Normalized 100"]).sort_values("Date")
    if len(df) < 2:
        return ""
    if len(df) > 140:
        step = max(1, len(df) // 140)
        df = df.iloc[::step].copy()
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
    latest = vals[-1]
    first = vals[0]
    change = latest - first
    cls = "pos" if change >= 0 else "neg"
    start_date = df["Date"].iloc[0].strftime("%d/%m")
    end_date = df["Date"].iloc[-1].strftime("%d/%m")
    label = f"{latest:.1f}".replace(".", ",")
    change_label = f"{change:+.1f}".replace(".", ",")
    # simple horizontal grid lines
    grid = []
    for ratio in [0, .5, 1]:
        y = top + ratio * plot_h
        grid.append(f"<line x1='{left}' y1='{y:.1f}' x2='{width-right}' y2='{y:.1f}' class='gridline'/>")
    return f"""
    <div class='mini-chart'>
      <div class='chart-head'><b>{escape(fund_name)}</b><span class='{cls}'>{escape(change_label)} pt</span></div>
      <svg viewBox='0 0 {width} {height}' role='img' aria-label='Grafico {escape(fund_name)}'>
        {''.join(grid)}
        <text x='0' y='{top+4}' class='axis'>{escape(format_number(max_v,1))}</text>
        <text x='0' y='{top+plot_h:.0f}' class='axis'>{escape(format_number(min_v,1))}</text>
        <polyline points='{' '.join(pts)}' class='spark {cls}' fill='none'/>
        <circle cx='{pts[-1].split(',')[0]}' cy='{pts[-1].split(',')[1]}' r='4' class='dot {cls}'/>
        <text x='{left}' y='{height-8}' class='axis'>{escape(start_date)}</text>
        <text x='{width-right-54}' y='{height-8}' class='axis'>{escape(end_date)}</text>
        <text x='{width-right-65}' y='{top+16}' class='last {cls}'>{escape(label)}</text>
      </svg>
    </div>"""


def _charts_grid(history: pd.DataFrame | None, performance: pd.DataFrame | None) -> str:
    if history is None or history.empty or "Nome Strumento" not in history.columns:
        return "<p class='muted'>Grafici non ancora disponibili. Lancia l'Auto update o apri la pagina Grafici e premi Aggiorna.</p>"
    names = history["Nome Strumento"].dropna().astype(str).drop_duplicates().tolist()[:7]
    cards = [_line_chart_svg(history, name) for name in names]
    cards = [c for c in cards if c]
    if not cards:
        return "<p class='muted'>Storico presente ma non sufficiente per disegnare i grafici.</p>"
    return f"<div class='charts-grid'>{''.join(cards)}</div>"


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
) -> str:
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    totals = _portfolio_totals(fineco_portfolio, fineco_summary)
    lines = [
        "AlphaForge v9.1 - Investing-style Fineco Radar",
        f"Aggiornato il {now}",
        "",
        f"Una tantum corretta: {totals['one_off']:.0f} EUR",
        f"PAC mensile corretto: {totals['pac']:.0f} EUR/mese",
        f"Bollo una tantum stimato: {totals['bollo']:.0f} EUR",
        "",
        "Cosa guardare: NAV Fineco ufficiale, performance proxy, news radar, costi annui e benchmark coerenti.",
        "Nota: report informativo, non consulenza finanziaria.",
    ]
    if fund_performance is not None and not fund_performance.empty:
        lines += ["", "Performance proxy:"]
        for _, row in fund_performance.head(7).iterrows():
            lines.append(f"- {row.get('Nome Strumento','')}: 1M {row.get('Rendimento proxy 1M %','n/d')}%, 3M {row.get('Rendimento proxy 3M %','n/d')}%, trend {row.get('Trend proxy','n/d')}")
    if news_summary and isinstance(news_summary, dict):
        lines += ["", "News radar:"]
        for item in news_summary.get("funds", [])[:7]:
            lines.append(f"- {item.get('Nome Strumento','')}: {item.get('Bias prossimi giorni','n/d')} | {item.get('Cosa fare','n/d')}")
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
) -> None:
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    totals = _portfolio_totals(fineco_portfolio, fineco_summary)
    status_text = str(status.get("status", "unknown") if isinstance(status, dict) else "unknown")
    status_version = str(status.get("version", "AlphaForge v9.1") if isinstance(status, dict) else "AlphaForge v9.1")
    phase = str((fineco_summary or {}).get("fase", "Punto zero"))
    message = str((fineco_summary or {}).get("messaggio_principale", "Portafoglio appena avviato: controlla quote, NAV e PAC."))

    public = _read_public_funds()
    funds_for_table = public if not public.empty else fineco_portfolio
    if funds_for_table is not None and not funds_for_table.empty:
        funds_for_table = funds_for_table.copy()
        if "Importo Iniziale EUR" in funds_for_table.columns and "PAC Mensile EUR" in funds_for_table.columns:
            funds_for_table["Capitale/PAC"] = funds_for_table.apply(lambda r: euro(r.get("Importo Iniziale EUR", 0), 0) if _as_float(r.get("Importo Iniziale EUR", 0)) > 0 else euro(r.get("PAC Mensile EUR", 0), 0) + "/mese", axis=1)

    news_funds = pd.DataFrame((news_summary or {}).get("funds", [])) if isinstance(news_summary, dict) else pd.DataFrame()
    css = """
    <style>
    :root{--bg:#f4f6fb;--panel:#fff;--text:#111827;--muted:#64748b;--line:#e2e8f0;--green:#0f9f6e;--red:#dc2626;--blue:#2563eb;--amber:#d97706;--dark:#0f172a;}
    *{box-sizing:border-box} body{margin:0;background:var(--bg);color:var(--text);font-family:Inter,ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif}.wrap{width:min(100% - 28px,1420px);margin:0 auto;padding:20px 0 34px}.topbar{display:flex;justify-content:space-between;align-items:center;background:var(--panel);border:1px solid var(--line);border-radius:18px;padding:12px 16px;box-shadow:0 8px 22px rgba(15,23,42,.05);position:sticky;top:8px;z-index:10}.brand{font-weight:900;letter-spacing:-.02em}.hero{margin-top:16px;border-radius:24px;padding:28px;background:linear-gradient(135deg,#0f172a 0%,#172554 56%,#064e3b 100%);color:white;box-shadow:0 22px 55px rgba(15,23,42,.22)}h1{font-size:46px;line-height:1;margin:12px 0 10px;letter-spacing:-.05em}.subtitle{color:#dbeafe;font-size:17px;max-width:900px;line-height:1.5}.pill{display:inline-flex;align-items:center;gap:6px;border-radius:999px;padding:5px 10px;background:#e0f2fe;color:#075985;font-size:12px;font-weight:850;white-space:nowrap}.pill.good{background:#dcfce7;color:#166534}.pill.watch{background:#fef3c7;color:#92400e}.pill.danger{background:#fee2e2;color:#991b1b}.grid{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:14px;margin-top:18px}.card{background:var(--panel);border:1px solid var(--line);border-radius:18px;padding:16px;box-shadow:0 10px 28px rgba(15,23,42,.06)}.hero .card{background:rgba(255,255,255,.10);border-color:rgba(255,255,255,.18);backdrop-filter:blur(8px)}.label{font-size:12px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);font-weight:900}.hero .label{color:#bfdbfe}.value{font-size:30px;font-weight:950;letter-spacing:-.04em;margin-top:4px}.hint{color:var(--muted);font-size:12px;margin-top:5px;line-height:1.35}.hero .hint{color:#dbeafe}section{margin-top:18px;background:var(--panel);border:1px solid var(--line);border-radius:22px;padding:20px;box-shadow:0 10px 28px rgba(15,23,42,.05)}h2{font-size:24px;margin:0 0 8px;letter-spacing:-.035em}.muted{color:var(--muted);line-height:1.55}.two{display:grid;grid-template-columns:1.05fr .95fr;gap:18px}.three{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}.callout{padding:16px;border:1px solid #bfdbfe;background:#eff6ff;border-radius:16px;font-weight:750;line-height:1.45}.table-wrap{overflow:auto;border:1px solid var(--line);border-radius:15px;margin-top:12px}table{border-collapse:collapse;width:100%;min-width:960px}th,td{padding:11px 12px;border-bottom:1px solid var(--line);font-size:13px;text-align:left;vertical-align:top}th{background:#f8fafc;text-transform:uppercase;font-size:11px;letter-spacing:.06em;color:#475569;position:sticky;top:0}td.long{min-width:260px}.num{font-variant-numeric:tabular-nums;font-weight:750}.charts-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px;margin-top:14px}.mini-chart{background:#fff;border:1px solid var(--line);border-radius:18px;padding:13px;box-shadow:0 8px 20px rgba(15,23,42,.04)}.chart-head{display:flex;justify-content:space-between;gap:12px;align-items:center;margin-bottom:6px;font-size:13px}.pos{color:var(--green)}.neg{color:var(--red)}svg{width:100%;height:auto}.gridline{stroke:#e5e7eb;stroke-width:1}.spark{stroke-width:2.5}.spark.pos{stroke:var(--green)}.spark.neg{stroke:var(--red)}.dot.pos{fill:var(--green)}.dot.neg{fill:var(--red)}.axis{font-size:11px;fill:#64748b}.last{font-size:13px;font-weight:900}.footer{margin-top:18px;color:var(--muted);font-size:13px;line-height:1.5}@media(max-width:980px){.grid{grid-template-columns:repeat(2,1fr)}.two,.three,.charts-grid{grid-template-columns:1fr}h1{font-size:38px}}@media(max-width:620px){.wrap{width:min(100% - 16px,1420px)}.grid{grid-template-columns:1fr}.hero,section{border-radius:18px;padding:18px}h1{font-size:32px}}
    </style>
    """
    html = f"""<!doctype html>
<html lang='it'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'><title>AlphaForge v9.1 Fineco Radar</title>{css}</head>
<body><div class='wrap'>
  <div class='topbar'><div class='brand'>📊 AlphaForge Trader</div><div>{_badge('Update: ' + status_text)} {_badge(status_version)}</div></div>
  <div class='hero'>
    <span class='pill good'>AlphaForge v9.1</span> <span class='pill'>Investing-style Fineco Radar</span>
    <h1>Portafoglio Fineco, grafici e notizie in una vista sola.</h1>
    <p class='subtitle'>Dashboard rapida tipo watchlist: importi corretti, PAC, costi, news finanziarie rilevanti e andamento dei proxy per capire cosa monitorare nei prossimi giorni.</p>
    <div class='grid'>
      <div class='card'><div class='label'>Investito una tantum</div><div class='value'>{escape(euro(totals['one_off'],0))}</div><div class='hint'>Corretto: 5 fondi x 5.000 €</div></div>
      <div class='card'><div class='label'>PAC mensile</div><div class='value'>{escape(euro(totals['pac'],0))}</div><div class='hint'>Corretto: 2 PAC x 150 €/mese</div></div>
      <div class='card'><div class='label'>Bollo una tantum</div><div class='value'>{escape(euro(totals['bollo'],0))}</div><div class='hint'>6 € per prodotto</div></div>
      <div class='card'><div class='label'>Fondi/PAC caricati</div><div class='value'>{int(totals['tracked'])}</div><div class='hint'>Universo Fineco pubblico</div></div>
      <div class='card'><div class='label'>Fase</div><div class='value'>{escape(phase)}</div><div class='hint'>Non giudicare ancora il rendimento</div></div>
    </div>
  </div>

  <section><h2>Vista rapida</h2><div class='callout'>{escape(message)}</div></section>

  <div class='two'>
    <section><h2>Watchlist fondi/PAC</h2><p class='muted'>Importi caricati correttamente: 25.000 € una tantum + 300 €/mese di PAC.</p>{compact_table(funds_for_table, ['ISIN','Nome Strumento','Tipo Versamento','Capitale/PAC','Costo Annuo %','Ruolo','Categoria AlphaForge','Proxy Ticker'], 12)}</section>
    <section><h2>Performance proxy</h2><p class='muted'>Non è il NAV ufficiale Fineco: serve a leggere il mercato sottostante quasi in tempo reale.</p>{compact_table(fund_performance, ['Nome Strumento','Proxy usato','Rendimento proxy 1D %','Rendimento proxy 1M %','Rendimento proxy 3M %','Rendimento proxy 1Y %','Trend proxy'], 12)}</section>
  </div>

  <section><h2>Grafici fondi/proxy</h2><p class='muted'>Grafici normalizzati a base 100. Se non compaiono, l'Auto update non ha ancora scaricato lo storico proxy o serve cambiare ticker proxy.</p>{_charts_grid(fund_history, fund_performance)}</section>

  <section><h2>News radar</h2><p class='muted'>Lettura prudente delle notizie finanziarie collegate ai settori dei fondi. Non e' una previsione certa.</p>{compact_table(news_funds, ['Nome Strumento','Categoria AlphaForge','News trovate','News Score Totale','Bias prossimi giorni','Cosa fare'], 8)}{compact_table(news_radar, ['Nome Strumento','Titolo','Fonte','News Score','Lettura','Impatto possibile','Link'], 12)}</section>

  <div class='two'>
    <section><h2>Tracker Fineco</h2><p class='muted'>Valore reale da aggiornare con NAV/controvalore Fineco.</p>{compact_table(fineco_portfolio, ['ISIN','Nome Strumento','Tipo Versamento','Capitale versato stimato EUR','Valore attuale stimato EUR','Rendimento %','Peso attuale %','Stato lettura'], 12)}</section>
    <section><h2>Cosa controllare</h2><div class='three'><div class='card'><div class='label'>Subito</div><div class='value'>Quote</div><div class='hint'>Data valuta, NAV, prezzo medio.</div></div><div class='card'><div class='label'>1 mese</div><div class='value'>PAC</div><div class='hint'>Verifica i due addebiti da 150 €.</div></div><div class='card'><div class='label'>12 mesi</div><div class='value'>Benchmark</div><div class='hint'>Confronta rendimento e costi.</div></div></div>{compact_table(fineco_questions, ['Priorita','Tema','Domanda','Perche'], 8)}</section>
  </div>

  <section><h2>Bussola settoriale</h2>{compact_table(sector_compass, ['Priorita','Settore','Bucket','Cosa fare','Sector Score','ETF/Fondo candidato','Rischio principale'], 10)}</section>

  <section><h2>Avvertenza</h2><p class='muted'>Aggiornato il {escape(now)}. Informazioni a scopo educativo e di monitoraggio. Non costituiscono consulenza finanziaria personalizzata, sollecitazione all'investimento o garanzia di rendimento. Per i fondi comuni il valore ufficiale resta il NAV/controvalore Fineco.</p></section>
  <div class='footer'>AlphaForge v9.1 Investing-style Fineco Radar · File generati automaticamente da GitHub Actions.</div>
</div></body></html>"""
    output.write_text(html, encoding="utf-8")
