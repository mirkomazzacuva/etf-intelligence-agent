"""Fineco positions valued using actual fund NAVs, never proxy ETFs.

Fineco screenshot snapshot is an immutable anchor. Public NAV feeds are optional and
only replace the NAV when their own dated reading is strictly later. For PACs,
additional units are counted only when a confirmed trade is recorded.
"""
from __future__ import annotations

import csv
from datetime import date, datetime
import json
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from core.fineco_nav_sources import NAVReading, fetch_verified_nav

ROOT = Path(__file__).resolve().parent.parent
POSITIONS = ROOT / 'data/fineco_official_positions.csv'
HISTORY = ROOT / 'data/fineco_nav_history_real.csv'
MANUAL_NAV = ROOT / 'data/fineco_nav_manual_real.csv'
TRADES = ROOT / 'data/fineco_transactions_real.csv'
OUT_PORTFOLIO = ROOT / 'AlphaForge_Real_Portfolio.csv'
OUT_HISTORY = ROOT / 'AlphaForge_Real_NAV_History.csv'
OUT_STATUS = ROOT / 'AlphaForge_Real_Source_Status.csv'
OUT_SUMMARY = ROOT / 'AlphaForge_Real_Summary.json'
OUT_DASH_DATA = ROOT / 'AlphaForge_Real_Dashboard_Data.json'
VERSION = 'AlphaForge v12 - Fineco NAV Reale'

HIST_COLS = ['ISIN','Data_NAV','NAV_EUR','Fonte','URL','Qualita']
PORT_COLS = [
    'ISIN','Nome','Tipo','Quote_rilevate','Quote_attuali','Prezzo_medio_carico_EUR',
    'Costo_carico_EUR','Controvalore_EUR','Margine_EUR','Rendimento_pct',
    'NAV_attuale_EUR','Data_ultimo_dato','Fonte_ultimo_dato','Qualita_ultimo_dato',
    'Aggiornamento','Costo_annuo_pct','PAC_mensile_EUR','Versamenti_post_snapshot_EUR',
    'Nuove_quote_registrate','Numero_punti_NAV','Fonte_URL',
]


def _read(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open('r', encoding='utf-8-sig', newline='') as handle:
        return [{key.strip(): (value or '').strip() for key, value in row.items() if key is not None} for row in csv.DictReader(handle)]


def _write_csv(path: Path, keys: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=keys, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)


def _money(value: Any) -> float:
    if isinstance(value, str):
        v = value.replace(' ', '').replace('EUR','').replace('€','')
        if ',' in v and '.' in v:
            v = v.replace('.','').replace(',','.') if v.rfind(',') > v.rfind('.') else v.replace(',','')
        else:
            v = v.replace(',','.')
        return float(v or 0)
    return float(value or 0)


def _day(value: str) -> date:
    return date.fromisoformat(str(value).strip()[:10])


def _stamp() -> str:
    return datetime.now(ZoneInfo('Europe/Rome')).isoformat(timespec='seconds')


def load_positions() -> list[dict[str, str]]:
    rows = _read(POSITIONS)
    expected = {'ISIN','Nome','Tipo','Quote_rilevate','NAV_rilevato_EUR','Controvalore_Fineco_EUR','Margine_Fineco_EUR','Data_rilevazione'}
    if not rows or not expected.issubset(rows[0]):
        raise ValueError('Snapshot Fineco reale assente o colonne incomplete')
    if len(rows) != 7 or len({r['ISIN'] for r in rows}) != 7:
        raise ValueError('Attesi esattamente 7 ISIN Fineco, senza duplicati')
    for r in rows:
        if _money(r['NAV_rilevato_EUR']) <= 0 or _money(r['Quote_rilevate']) <= 0:
            raise ValueError('Quote o NAV non validi: ' + r['ISIN'])
    return rows


def load_nav_history() -> list[dict[str, str]]:
    history = _read(HISTORY)
    seen = set()
    cleaned: list[dict[str, str]] = []
    for row in history:
        try:
            isin = row['ISIN']
            day = _day(row['Data_NAV'])
            nav = _money(row['NAV_EUR'])
            if not 0.01 < nav < 100000 or day > date.today():
                continue
            key = (isin, day.isoformat())
            if key in seen:
                continue
            seen.add(key)
            cleaned.append({key: row.get(key, '') for key in HIST_COLS})
        except (ValueError, KeyError):
            continue
    return sorted(cleaned, key=lambda r: (r['ISIN'],r['Data_NAV']))


def _manual_quotes() -> list[NAVReading]:
    out = []
    for row in _read(MANUAL_NAV):
        try:
            day = _day(row['Data_NAV'])
            nav = _money(row['NAV_EUR'])
            isin = row['ISIN'].strip()
            if not 0.01 < nav < 100000 or day > date.today() or not isin:
                continue
            out.append(NAVReading(isin, day, nav, row.get('Fonte') or 'NAV inserito manualmente', row.get('URL') or ''))
        except (ValueError, KeyError):
            continue
    return out


def update_history(positions: list[dict[str, str]], history: list[dict[str, str]], allow_network: bool = True) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    by_key = {(r['ISIN'], r['Data_NAV']) for r in history}
    newest = {p['ISIN']: max((h['Data_NAV'] for h in history if h['ISIN'] == p['ISIN']), default=p['Data_rilevazione']) for p in positions}
    manual = _manual_quotes()
    state = []
    valid_isins = set(newest)
    for p in positions:
        isin = p['ISIN']
        readings = [q for q in manual if q.isin == isin]
        message = 'Aggiornamento automatico non richiesto (offline).'
        if allow_network:
            quote, message = fetch_verified_nav(isin)
            if quote is not None:
                readings.append(quote)
        added = False
        for quote in sorted(readings, key=lambda item:item.nav_date):
            # Never replace the Fineco screenshot with an older/same-date public NAV.
            if quote.nav_date <= _day(newest[isin]) or quote.nav_date <= _day(p['Data_rilevazione']):
                continue
            if (isin, quote.nav_date.isoformat()) in by_key:
                continue
            if _money(p['NAV_rilevato_EUR']) > 0:
                ratio = quote.nav_eur / _money(p['NAV_rilevato_EUR'])
                if not 0.4 < ratio < 2.5:
                    message = 'Valore NAV anomalo, escluso per sicurezza'
                    continue
            history.append({
                'ISIN': isin, 'Data_NAV': quote.nav_date.isoformat(), 'NAV_EUR': f'{quote.nav_eur:.6f}',
                'Fonte': quote.source, 'URL': quote.url,
                'Qualita': 'NAV datato per ISIN; fonte pubblica' if quote.url else 'NAV manuale (verificare fonte)',
            })
            by_key.add((isin, quote.nav_date.isoformat()))
            newest[isin] = quote.nav_date.isoformat()
            added = True
        if not added and allow_network:
            message = ('Nessuna quotazione pubblica piu recente dello screenshot. ' + message).strip()
        state.append({'ISIN': isin, 'Esito': 'NAV NUOVO' if added else 'NESSUNA NOVITA', 'Messaggio': message, 'Ultimo_NAV_utilizzato': newest[isin], 'Controllato_il': _stamp()})
    return sorted(history, key=lambda r:(r['ISIN'],r['Data_NAV'])), state


def _confirmed_purchases(positions: list[dict[str, str]]) -> dict[str, dict[str, float]]:
    purchases: dict[str, dict[str,float]] = {}
    anchor_dates = {p['ISIN']: _day(p['Data_rilevazione']) for p in positions}
    for t in _read(TRADES):
        if not t.get('ISIN'):
            continue
        kind = t.get('Tipo','').strip().lower()
        if kind not in {'buy','acquisto','sottoscrizione','pac'}:
            raise ValueError('Operazione ' + str(t.get('Tipo','')) + ' non gestita. Dopo un rimborso aggiornare lo snapshot Fineco.')
        isin = t['ISIN']
        if isin not in anchor_dates or _day(t['Data']) <= anchor_dates[isin]:
            raise ValueError('Operazione senza ISIN valido o precedente alla relativa data di rilevazione Fineco: ' + isin)
        qty = _money(t['Quote'])
        cost = _money(t['Costo_carico_EUR'])
        if qty <= 0 or cost <= 0:
            raise ValueError('Quote e costo devono essere positivi: ' + isin)
        record = purchases.setdefault(isin, {'qty': 0.0, 'cost': 0.0,'count':0})
        record['qty'] += qty
        record['cost'] += cost
        record['count'] += 1
    return purchases


def build_real_portfolio(allow_network: bool = True, persist: bool = False) -> tuple[list[dict[str, Any]], list[dict[str, str]], dict[str, Any], list[dict[str,str]]]:
    positions = load_positions()
    history, status = update_history(positions, load_nav_history(), allow_network=allow_network)
    buys = _confirmed_purchases(positions)
    unmatched = set(buys) - {p['ISIN'] for p in positions}
    if unmatched:
        raise ValueError('Movimenti con ISIN non presente nel portafoglio: ' + ', '.join(sorted(unmatched)))

    result: list[dict[str, Any]] = []
    all_snapshot = True
    for p in positions:
        isin = p['ISIN']
        record = sorted((h for h in history if h['ISIN'] == isin), key=lambda r:r['Data_NAV'])
        snapshot_date = p['Data_rilevazione']
        later = [h for h in record if h['Data_NAV'] > snapshot_date]
        latest = later[-1] if later else None
        snapshot_nav = _money(p['NAV_rilevato_EUR'])
        snapshot_value = _money(p['Controvalore_Fineco_EUR'])
        snapshot_margin = _money(p['Margine_Fineco_EUR'])
        snapshot_basis = round(snapshot_value - snapshot_margin, 2)
        qty = _money(p['Quote_rilevate'])
        bought = buys.get(isin, {'qty':0.0,'cost':0.0,'count':0})
        new_qty = bought['qty']
        new_cost = bought['cost']
        nav_now = _money(latest['NAV_EUR']) if latest is not None else snapshot_nav
        if latest:
            all_snapshot = False
            # Exactly preserve screenshot market value as benchmark; holdings are rounded on the screen.
            current_value = round(snapshot_value * nav_now / snapshot_nav + new_qty * nav_now, 2)
            source = latest['Fonte']
            quote_date = latest['Data_NAV']
            quality = latest.get('Qualita','NAV pubblico verificato')
            update = 'NAV pubblico/registrato, nuove quote solo se dichiarate'
        else:
            current_value = round(snapshot_value + new_qty * snapshot_nav, 2)
            source = 'Schermata Fineco'
            quote_date = snapshot_date
            quality = 'Rilevazione Fineco: data effettiva NAV non visibile'
            update = 'Snapshot Fineco, valore invariato (nessun NAV piu recente verificato)'
        basis = round(snapshot_basis + new_cost, 2)
        gain = round(current_value - basis, 2)
        yield_pct = round(gain/basis*100, 2) if basis else 0.0
        result.append({
            'ISIN': isin, 'Nome': p['Nome'], 'Tipo':p['Tipo'],
            'Quote_rilevate': qty, 'Quote_attuali': round(qty+new_qty, 6),
            'Prezzo_medio_carico_EUR': _money(p.get('Prezzo_medio_carico_EUR',0)),
            'Costo_carico_EUR': basis, 'Controvalore_EUR': current_value,
            'Margine_EUR': gain, 'Rendimento_pct': yield_pct,
            'NAV_attuale_EUR': nav_now, 'Data_ultimo_dato': quote_date,
            'Fonte_ultimo_dato': source, 'Qualita_ultimo_dato': quality,
            'Aggiornamento': update,
            'Costo_annuo_pct': _money(p.get('Costo_annuo_pct',0)),
            'PAC_mensile_EUR': _money(p.get('PAC_programmato_mensile_EUR',0)),
            'Versamenti_post_snapshot_EUR': round(new_cost, 2),
            'Nuove_quote_registrate': round(new_qty,6),
            'Numero_punti_NAV':len(record),
            'Fonte_URL': latest.get('URL','') if latest else '',
        })
    market = round(sum(r['Controvalore_EUR'] for r in result),2)
    basis = round(sum(r['Costo_carico_EUR'] for r in result),2)
    gain = round(market-basis,2)
    summary: dict[str,Any] = {
        'version': VERSION,
        'updated_at_rome': _stamp(),
        'snapshot_date': max(p['Data_rilevazione'] for p in positions),
        'market_value_eur': market,
        'cost_basis_eur': basis,
        'margin_eur': gain,
        'margin_pct':round(gain/basis*100,2) if basis else 0.0,
        'initial_oneoff_eur': 25000.0,
        'pac_monthly_eur': round(sum(r['PAC_mensile_EUR'] for r in result),2),
        'confirmed_initial_pac_principal_eur': 600.0,
        'original_paid_cash_eur': 25600.0,
        'snapshot_cost_basis_extra_vs_cash_eur': 46.2,
        'transactions_after_snapshot_count':int(sum(v['count'] for v in buys.values())),
        'has_latest_nav_after_snapshot':not all_snapshot,
        'funds_count':len(result),
        'positive_count':sum(r['Margine_EUR'] > 0 for r in result),
        'negative_count':sum(r['Margine_EUR'] < 0 for r in result),
        'status': 'NAV pubblico + snapshot Fineco' if not all_snapshot else 'Snapshot Fineco: NAV nuovo non verificato',
        'warning':'Quote PAC successive al 29/10/2026 NON stimate automaticamente: registrare ogni eseguito nel file movimenti. Nessun valore ETF proxy entra nel margine.',
        'cost_note':'Margini gia al netto dei costi incorporati nel NAV e dei costi di carico Fineco; prima di eventuali imposte di vendita. Nessuna ulteriore detrazione del TER.',
    }
    if all_snapshot and not buys and all(p['Data_rilevazione'] == '2026-10-29' for p in positions):
        if (abs(market-25735.13)>0.01 or abs(basis-25646.20)>0.01 or abs(gain-88.93)>0.01):
            raise AssertionError('Snapshot Fineco non riconciliato: valori attesi 25735.13, 25646.20, 88.93')
    if persist:
        _write_csv(HISTORY, HIST_COLS, history)
        _write_csv(OUT_HISTORY, HIST_COLS, history)
        _write_csv(OUT_STATUS, ['ISIN','Esito','Messaggio','Ultimo_NAV_utilizzato','Controllato_il'], status)
        _write_csv(OUT_PORTFOLIO, PORT_COLS, result)
        OUT_SUMMARY.write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
        OUT_DASH_DATA.write_text(json.dumps({'summary':summary,'funds':result,'nav_history':history},ensure_ascii=False,indent=2), encoding='utf-8')
    return result, history, summary, status
