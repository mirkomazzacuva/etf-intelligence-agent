"""Update v12 truthful Fineco portfolio first, then refresh older auxiliary research."""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

STATUS_FILE = Path('AUTO_UPDATE_STATUS.json')
VERSION = 'AlphaForge v12 - Fineco NAV Reale'
LEGACY_SCRIPTS = [
    'update_etf_data_v3.py',
    'allocation_engine.py',
    'generate_watchlist.py',
    'generate_insights.py',
    'generate_decisions.py',
    'generate_sector_compass.py',
    'generate_fineco_portfolio.py',
    'generate_fund_performance.py',
    'generate_news_radar.py',
    'generate_live_snapshot.py',
    'generate_fund_decisions.py',
]


def stamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def run(script: str) -> dict:
    print('\n=== ' + script + ' ===', flush=True)
    if not Path(script).exists():
        print('Missing optional script ' + script, flush=True)
        return {'script':script,'returncode':-1,'message':'File non presente'}
    process=subprocess.run([sys.executable,script],capture_output=True,text=True,check=False)
    if process.stdout:
        print(process.stdout[-3200:],flush=True)
    if process.stderr:
        print(process.stderr[-3200:],file=sys.stderr,flush=True)
    return {'script':script,'returncode':process.returncode,'stdout_tail':process.stdout[-600:] if process.stdout else '', 'stderr_tail':process.stderr[-600:] if process.stderr else ''}


def save(status: str, message: str, details: list[dict], started_at: str) -> None:
    STATUS_FILE.write_text(json.dumps({
        'status':status,'version':VERSION,'message':message,'started_at':started_at,
        'finished_at':stamp(),'details':details,
    },ensure_ascii=False,indent=2),encoding='utf-8')


def main() -> int:
    started=stamp(); details=[]
    # Mandatory: this source is the only one allowed to compute current P/L.
    actual=run('generate_real_portfolio.py')
    details.append(actual)
    if actual['returncode']:
        save('failed','NAV reale non aggiornato; margini non rigenerati',details,started)
        return 1
    # Legacy market research may occasionally have unavailable ticker/API data.
    # Do not block an accurate Fineco page because a secondary ETF call fails.
    for script in LEGACY_SCRIPTS:
        details.append(run(script))
    page=run('generate_dashboard.py')
    details.append(page)
    if page['returncode']:
        save('failed','Dashboard v12 non rigenerata',details,started)
        return 1
    errors=[d['script'] for d in details if d['returncode'] and d['script'] not in ('generate_real_portfolio.py','generate_dashboard.py')]
    status='success' if not errors else 'partial'
    message=('Portafoglio Fineco v12 aggiornato e dashboard generata.' if not errors
             else 'Portafoglio Fineco v12 aggiornato; moduli secondari con problemi: ' + ', '.join(errors))
    save(status,message,details,started)
    print(message)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
