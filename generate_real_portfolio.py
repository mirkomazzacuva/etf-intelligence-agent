"""Generate truthful Fineco NAV-driven summary and history; optional internet update."""
from __future__ import annotations
import os
from core.fineco_real_engine import build_real_portfolio

if __name__ == '__main__':
    funds, history, summary, status = build_real_portfolio(
        allow_network=os.environ.get('ALPHAFORGE_NAV_OFFLINE', '').strip().lower() not in ('1','true','yes'),
        persist=True,
    )
    print('AlphaForge v12 | 7 funds, market EUR %.2f, margin EUR %+.2f, NAV points %d' % (
        summary['market_value_eur'], summary['margin_eur'], len(history)))
    for row in status:
        print('%s | %s | %s' % (row['ISIN'], row['Esito'], row['Messaggio']))
