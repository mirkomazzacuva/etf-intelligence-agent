"""Portable static dashboard: seven real Fineco positions and seven distinct NAV charts."""
from __future__ import annotations

from collections import defaultdict
from datetime import date
from html import escape
import json
from pathlib import Path
from typing import Any

from core.fineco_real_engine import ROOT, OUT_DASH_DATA


def money(number: Any, signed: bool = False) -> str:
    value = float(number or 0)
    mark = '+' if signed and value > 0 else ''
    return mark + f'{value:,.2f}'.replace(',', '#').replace('.', ',').replace('#', '.') + ' &euro;'


def percentage(number: Any, signed: bool = True) -> str:
    value = float(number or 0)
    mark = '+' if signed and value > 0 else ''
    return mark + f'{value:.2f}'.replace('.', ',') + '%'


def text(value: Any) -> str:
    return escape(str(value or ''))


def _chart(series: list[dict[str, str]], height: int = 194) -> str:
    # One point = no slope can be determined. Never fill missing daily NAV values.
    if not series:
        return "<div class='chart-empty'>Nessuna quotazione storica registrata.</div>"
    rows = []
    for s in sorted(series, key=lambda row:row['Data_NAV']):
        try:
            rows.append((date.fromisoformat(s['Data_NAV']), float(s['NAV_EUR']), s.get('Fonte','')))
        except (ValueError, TypeError):
            continue
    if not rows:
        return "<div class='chart-empty'>Storico non utilizzabile.</div>"
    first = rows[0][0]
    end = rows[-1][0]
    vmin = min(v for _,v,_ in rows)
    vmax = max(v for _,v,_ in rows)
    gap = max(0.10, (vmax - vmin) * .20)
    vmin -= gap
    vmax += gap
    width=600; left=44; top=12; bottom=36; right=12
    plotw=width-left-right; ploth=height-top-bottom
    duration=max(1,(end-first).days)
    points=[]; dot_html=[]
    for dt,nav,src in rows:
        x=left+(dt-first).days/duration*plotw
        y=top+(vmax-nav)/(vmax-vmin)*ploth
        points.append(f'{x:.1f},{y:.1f}')
        dot_html.append(f"<circle cx='{x:.1f}' cy='{y:.1f}' r='4.8' class='nav-dot'><title>{text(dt.strftime('%d/%m/%Y'))}: {text(str(nav))} EUR - {text(src)}</title></circle>")
    grid=[]
    for ratio in (0, .5, 1):
        y=top+ratio*ploth
        grid.append(f"<line x1='{left}' x2='{width-right}' y1='{y:.1f}' y2='{y:.1f}' class='gridline'/>")
    class_line='fund-line-dashed' if len(rows)<5 else 'fund-line'
    polyline=f"<polyline points='{' '.join(points)}' class='{class_line}'/>" if len(points)>=2 else ''
    return (
        f"<svg viewBox='0 0 {width} {height}' role='img' aria-label='NAV reale: {len(rows)} osservazioni registrate'>"
        + ''.join(grid)
        + f"<text class='axis' x='0' y='{top+7}'>{text(f'{vmax:.2f}')}</text>"
        + f"<text class='axis' x='0' y='{height-bottom+3}'>{text(f'{vmin:.2f}')}</text>"
        + polyline + ''.join(dot_html)
        + f"<text class='axis' x='{left}' y='{height-7}'>{first.strftime('%d/%m/%y')}</text>"
        + f"<text class='axis' text-anchor='end' x='{width-right}' y='{height-7}'>{end.strftime('%d/%m/%y')}</text>"
        + '</svg>'
    )


def render_real_dashboard(output: Path | None = None) -> Path:
    output=output or (ROOT/'index.html')
    if not OUT_DASH_DATA.exists():
        raise FileNotFoundError('Manca AlphaForge_Real_Dashboard_Data.json: eseguire generate_real_portfolio.py')
    data=json.loads(OUT_DASH_DATA.read_text(encoding='utf-8'))
    summary=data['summary']; funds=data['funds']; hist=data['nav_history']
    groups=defaultdict(list)
    for h in hist:
        groups[h['ISIN']].append(h)
    badge=('var(--success)' if summary['margin_eur'] >= 0 else 'var(--danger)')
    all_snapshot=not summary['has_latest_nav_after_snapshot']
    status_label=('Rilevazione Fineco - 29/10/2026' if all_snapshot else 'NAV aggiornati per alcuni fondi')

    def fund_row(f: dict[str, Any]) -> str:
        signed_cls='green' if f['Margine_EUR']>=0 else 'red'
        source='Fineco rilevazione' if f['Fonte_ultimo_dato']=='Schermata Fineco' else f['Fonte_ultimo_dato']
        return (
            '<tr data-filter="'+text(f['Nome']+' '+f['ISIN'])+'">'
            f"<td class='fundname'><a href='#fund-{text(f['ISIN'])}'>{text(f['Nome'])}</a><small>{text(f['ISIN'])} &middot; {text(f['Tipo'])}</small></td>"
            f"<td class='right number'>{money(f['Costo_carico_EUR'])}</td>"
            f"<td class='right number strong'>{money(f['Controvalore_EUR'])}</td>"
            f"<td class='right number {signed_cls}'>{money(f['Margine_EUR'], signed=True)}</td>"
            f"<td class='right number {signed_cls}'>{percentage(f['Rendimento_pct'])}</td>"
            f"<td class='price'><b>{text(f['NAV_attuale_EUR'])} &euro;</b><small>{text(f['Data_ultimo_dato'])} &middot; {text(source)}</small></td>"
            '</tr>'
        )

    def fund_card(f: dict[str,Any]) -> str:
        serie=groups[f['ISIN']]
        mcls='green' if f['Margine_EUR']>=0 else 'red'
        per=percentage(f['Rendimento_pct'])
        label=("Snapshot Fineco - NAV non verificato dopo il 29/10" if f['Fonte_ultimo_dato']=='Schermata Fineco'
               else f"NAV {f['Data_ultimo_dato']} - {f['Fonte_ultimo_dato']}")
        chart=_chart(serie)
        point_note=('Due osservazioni storiche reali: i giorni mancanti NON sono interpolati come quotazioni.' if len(serie)==2
                    else f'{len(serie)} NAV storici distinti registrati.')
        return f"""
        <article class='fund-card' id='fund-{text(f['ISIN'])}'>
          <div class='fund-top'><div><span class='eyebrow'>{text(f['Tipo'])} &bull; {text(f['ISIN'])}</span><h3>{text(f['Nome'])}</h3></div>
          <div class='fund-gain {mcls}'>{money(f['Margine_EUR'],signed=True)}<small>{per}</small></div></div>
          <div class='fund-metrics'><div><label>Controvalore</label><strong>{money(f['Controvalore_EUR'])}</strong></div><div><label>Costo carico</label><strong>{money(f['Costo_carico_EUR'])}</strong></div><div><label>Ultimo NAV</label><strong>{text(f['NAV_attuale_EUR'])} &euro;</strong></div><div><label>Costo annuo nel NAV</label><strong>{percentage(f['Costo_annuo_pct'],signed=False)}</strong></div></div>
          <div class='fund-chart'>{chart}</div>
          <div class='fineprint'>{text(point_note)}<br>{text(label)}. {text(f['Qualita_ultimo_dato'])}</div>
        </article>"""

    notes=(
        'Tutti i sette controvalori sono quelli di Fineco al 29/10/2026; il NAV non e stato mostrato con una data distinta.' if all_snapshot
        else 'Alcuni strumenti utilizzano NAV datati verificati successivi al 29/10/2026; gli altri restano alla rilevazione Fineco.'
    )
    html=f"""<!doctype html><html lang='it'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>AlphaForge v12 | Portafoglio Fineco reale</title>
<style>
:root{{--ink:#182337;--ink2:#2b3851;--accent:#1475d4;--sky:#e7f2ff;--success:#17864c;--danger:#c52f40;--bg:#f4f6fa;--line:#e0e6ee;--muted:#657388;--white:#fff;}}
*{{box-sizing:border-box}}html{{scroll-behavior:smooth}}body{{margin:0;background:var(--bg);color:var(--ink);font:14px/1.5 system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;}}a{{color:var(--accent);text-decoration:none}}a:hover{{text-decoration:underline}}
.wrap{{max-width:1360px;margin:auto;padding:0 22px 44px}}.topbar{{background:#0f1b2f;color:#fff}}.top-inner{{max-width:1360px;margin:auto;display:flex;align-items:center;justify-content:space-between;gap:12px;padding:14px 22px;}}.brand{{font-weight:850;font-size:19px;letter-spacing:-.5px}}.brand em{{color:#5eb1ff;font-style:normal}}.toplinks{{display:flex;gap:16px;flex-wrap:wrap}}.toplinks a{{color:#c5d1e0;font-size:13px}}
.hero{{display:flex;align-items:flex-end;justify-content:space-between;gap:18px;margin:28px 0 18px}}.eyebrow{{color:var(--muted);text-transform:uppercase;font-size:11px;font-weight:800;letter-spacing:1px}}h1{{font-size:36px;line-height:1.1;letter-spacing:-1px;margin:7px 0 7px}}.sub{{color:var(--muted);margin:0;font-size:14px}}.snapshot{{font-weight:700;font-size:12px;color:#1e5f9b;background:var(--sky);border:1px solid #c5e0ff;padding:8px 12px;border-radius:999px;white-space:nowrap}}
.kpis{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}}.kpi{{background:#fff;border:1px solid var(--line);border-radius:14px;padding:18px 19px;box-shadow:0 5px 16px #23344f08}}.kpi-label{{font-size:12px;font-weight:750;color:var(--muted)}}.kpi-value{{font-size:29px;line-height:1.1;font-weight:850;letter-spacing:-1px;margin:9px 0 6px;font-variant-numeric:tabular-nums}}.kpi-hint{{font-size:12px;color:var(--muted)}}.green{{color:var(--success)!important}}.red{{color:var(--danger)!important}}
.callout{{display:flex;gap:12px;background:#fff9eb;border-left:4px solid #e4a328;padding:13px 17px;border-radius:8px;margin:16px 0 18px;line-height:1.55}}.callout b{{color:#996312}}.section{{border:1px solid var(--line);background:var(--white);border-radius:15px;padding:22px;margin-top:17px;box-shadow:0 5px 18px #23344f08}}.section-head{{display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;margin-bottom:14px}}.section h2{{font-size:20px;margin:0;letter-spacing:-.5px}}.section-sub{{font-size:12px;color:var(--muted);margin:6px 0 0}}.search{{background:#f6f8fc;border:1px solid var(--line);border-radius:9px;padding:10px 12px;min-width:260px;max-width:100%;outline-color:var(--accent)}}
.tablewrap{{overflow-x:auto;border:1px solid var(--line);border-radius:10px}}table{{border-collapse:collapse;width:100%;min-width:950px}}th{{padding:12px 13px;color:var(--muted);background:#f8fafd;font-size:11px;text-align:left;text-transform:uppercase;letter-spacing:.5px;white-space:nowrap}}td{{padding:13px;border-top:1px solid #edf0f4;vertical-align:middle}}tr:hover td{{background:#fafcff}}.fundname a{{font-weight:800;color:var(--ink)}}.fundname small,.price small{{display:block;color:var(--muted);font-size:11px;margin-top:3px}}.price b{{color:var(--ink2)}}.right{{text-align:right}}.number{{white-space:nowrap;font-variant-numeric:tabular-nums;font-weight:700}}.strong{{font-weight:850}}
.nav-cards{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:15px}}.fund-card{{border:1px solid var(--line);border-radius:14px;padding:17px;scroll-margin-top:22px;min-width:0;background:#fff}}.fund-top{{display:flex;justify-content:space-between;gap:10px;align-items:flex-start}}.fund-top h3{{font-size:18px;line-height:1.2;letter-spacing:-.3px;margin:4px 0 12px}}.fund-gain{{font-weight:850;font-size:20px;text-align:right;white-space:nowrap}}.fund-gain small{{display:block;font-size:12px}}.fund-metrics{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;padding:12px 0;border-top:1px solid #edf0f4}}.fund-metrics label{{display:block;font-size:11px;color:var(--muted)}}.fund-metrics strong{{display:block;font-size:13px;margin-top:3px;white-space:nowrap}}.fund-chart svg{{display:block;width:100%;height:auto;overflow:visible}}.gridline{{stroke:#e4e9ef;stroke-width:1}}.fund-line{{fill:none;stroke:#1583d6;stroke-width:3;stroke-linecap:round;stroke-linejoin:round}}.fund-line-dashed{{fill:none;stroke:#1583d6;stroke-width:2.5;stroke-dasharray:6 5;stroke-linecap:round}}.nav-dot{{fill:#1475d4;stroke:#fff;stroke-width:2}}.axis{{font-size:12px;fill:#7b8899}}.fineprint{{color:var(--muted);font-size:11px;line-height:1.55;border-top:1px solid #edf0f4;padding-top:9px}}.explain{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}.box{{background:#f7f9fd;border:1px solid var(--line);padding:16px;border-radius:12px}}.box h3{{margin:0 0 6px;font-size:15px}}.box p{{font-size:13px;line-height:1.6;color:var(--ink2);margin:0}}.footer{{color:var(--muted);font-size:12px;line-height:1.55;padding:18px 2px}}
@media(max-width:1080px){{.kpis{{grid-template-columns:repeat(2,1fr)}}.nav-cards{{grid-template-columns:1fr}}}}@media(max-width:640px){{.wrap{{padding:0 12px 24px}}.top-inner{{padding:13px 12px;align-items:flex-start;flex-direction:column}}.hero{{align-items:flex-start;flex-direction:column;margin-top:20px}}h1{{font-size:29px}}.kpis{{grid-template-columns:1fr 1fr;gap:8px}}.kpi{{padding:14px}}.kpi-value{{font-size:23px}}.section{{padding:13px}}.fund-metrics{{grid-template-columns:repeat(2,1fr)}}.explain{{grid-template-columns:1fr}}}}
</style></head><body><header class='topbar'><div class='top-inner'><div class='brand'>Alpha<em>Forge</em> <span style='font-size:12px;font-weight:500;color:#a6b4c5'>/ FINECO</span></div><nav class='toplinks'><a href='#portafoglio'>Portafoglio</a><a href='#grafici'>Grafici NAV</a><a href='#metodo'>Come leggere</a><a href='legacy_alpha_forge.html'>Altri strumenti &#8599;</a></nav></div></header>
<main class='wrap'><div class='hero'><div><div class='eyebrow'>AlphaForge v12 &middot; dati verificabili</div><h1>Il mio portafoglio</h1><p class='sub'>Valori Fineco reali e NAV per ISIN. Niente rendimenti ricavati da ETF proxy.</p></div><div class='snapshot'>{text(status_label)}</div></div>
<div class='kpis'>
<div class='kpi'><div class='kpi-label'>Controvalore complessivo</div><div class='kpi-value'>{money(summary['market_value_eur'])}</div><div class='kpi-hint'>Ultimo valore verificato per ogni strumento</div></div>
<div class='kpi'><div class='kpi-label'>Costo di carico Fineco</div><div class='kpi-value'>{money(summary['cost_basis_eur'])}</div><div class='kpi-hint'>Include costi entrati nel prezzo di carico</div></div>
<div class='kpi'><div class='kpi-label'>Guadagno / perdita su carico</div><div class='kpi-value' style='color:{badge}'>{money(summary['margin_eur'], signed=True)}</div><div class='kpi-hint'><b style='color:{badge}'>{percentage(summary['margin_pct'])}</b> &middot; prima di eventuali imposte</div></div>
<div class='kpi'><div class='kpi-label'>PAC programmati</div><div class='kpi-value'>{money(summary['pac_monthly_eur'], signed=False)}<span style='font-size:13px;color:#69788d'>/mese</span></div><div class='kpi-hint'>150 &euro; tecnologia + 150 &euro; emergenti</div></div></div>
<div class='callout'><div>&#9432;</div><div><b>Qualita dei dati.</b> {text(notes)} I grafici contengono solo NAV pubblicati o rilevati: non ci sono prezzi giornalieri inventati. <b>Nuove rate PAC:</b> inserire le operazioni effettivamente eseguite, non quelle soltanto programmate.</div></div>
<section class='section' id='portafoglio'><div class='section-head'><div><h2>Le mie posizioni</h2><p class='section-sub'>4 positive, 3 negative alla rilevazione originale Fineco &middot; clicca il nome per il grafico</p></div><input class='search' id='filter' placeholder='Cerca fondo o ISIN...' aria-label='Cerca fondo o ISIN'></div><div class='tablewrap'><table><thead><tr><th>Fondo</th><th style='text-align:right'>Costo di carico</th><th style='text-align:right'>Controvalore</th><th style='text-align:right'>Margine</th><th style='text-align:right'>%</th><th>Ultimo valore e fonte</th></tr></thead><tbody>{''.join(fund_row(f) for f in funds)}</tbody></table></div><p class='section-sub'>Importi in euro. Il margine coincide con Fineco al 29/10/2026. Un NAV aggiornato varia il risultato solo se la fonte e piu recente del riferimento.</p></section>
<section class='section' id='grafici'><div class='section-head'><div><h2>Andamento NAV per singolo fondo</h2><p class='section-sub'>7 grafici distinti e ISIN corretti. I punti storici crescono con ogni quotazione realmente disponibile.</p></div></div><div class='nav-cards'>{''.join(fund_card(f) for f in funds)}</div></section>
<section class='section' id='metodo'><div class='section-head'><h2>Come leggere questi numeri</h2></div><div class='explain'><div class='box'><h3>Guadagno reale, non simulazione</h3><p>Controvalore meno costo di carico. Il prezzo di carico e il valore forniti da Fineco incorporano gia la struttura effettiva dei costi; il costo di gestione del fondo e gia riflesso nel NAV e NON viene sottratto una seconda volta. Le eventuali tasse future non sono incluse.</p></div><div class='box'><h3>Quanto sono aggiornati i prezzi?</h3><p>La data del controllo delle fonti e distinta dalla data NAV. Quando una fonte pubblica non rende disponibile un NAV verificabile piu recente, rimane la fotografia Fineco. Le quotazioni dei fondi non sono intraday.</p></div><div class='box'><h3>PAC e nuovi versamenti</h3><p>Partenza confermata: 25.000 &euro; nei 5 fondi e 300 &euro; versati su ciascuno dei due PAC. I 300 &euro; mensili futuri NON sono considerati automaticamente gia versati. Aggiungi quote e costi degli eseguiti effettivi nel file movimenti.</p></div><div class='box'><h3>Previsioni e cambi fondo</h3><p>Le proiezioni automatiche precedenti erano basate su ETF sostitutivi e potevano fuorviare. Le proiezioni a 3 mesi / 1 anno saranno riattivate con serie NAV sufficienti, benchmark e ipotesi dichiarate. Un costo elevato, da solo, non equivale a un ordine di vendita.</p></div></div></section>
<div class='footer'><b>{text(summary['version'])}</b> &middot; Verifica fonti: {text(summary['updated_at_rome'])} &middot; Rilevazione Fineco 29/10/2026. <a href='legacy_alpha_forge.html'>Apri la precedente dashboard analitica (dati proxy, non margini reali)</a>.<br>Dashboard informativa; il conto Fineco rimane la fonte definitiva per quantita, eseguiti e controvalori. I contenuti pubblicati in GitHub Pages sono visibili a chi ha il link.</div>
</main><script>document.getElementById('filter').addEventListener('input',function(){{const q=this.value.toLowerCase();document.querySelectorAll('tr[data-filter]').forEach(r=>r.hidden=!r.dataset.filter.toLowerCase().includes(q));}});</script></body></html>"""
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(html,encoding='utf-8')
    return output
