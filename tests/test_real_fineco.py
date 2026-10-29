import json
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from core import fineco_real_engine as engine
from core.fineco_nav_sources import NAVReading, parse_borsa_fidelity, parse_fam_page
from core.fineco_real_ui import render_real_dashboard

class RealPortfolioTests(unittest.TestCase):
    def test_exact_reconciliation(self):
        rows,history,summary,status=engine.build_real_portfolio(allow_network=False,persist=False)
        self.assertEqual(len(rows),7)
        self.assertEqual(len(history),14)
        self.assertEqual(round(summary['market_value_eur'],2),25735.13)
        self.assertEqual(round(summary['cost_basis_eur'],2),25646.20)
        self.assertEqual(round(summary['margin_eur'],2),88.93)
        self.assertEqual(summary['pac_monthly_eur'],300)
        self.assertEqual(summary['positive_count'],4)
        self.assertEqual(summary['negative_count'],3)
        self.assertEqual(sum(r['Margine_EUR'] for r in rows),88.93)
        self.assertTrue(all(r['Fonte_ultimo_dato']=='Schermata Fineco' for r in rows))

    def test_fam_parser_with_isin_and_date(self):
        text='<html><body>ISIN IE000DWG3DP6 NAV Price 163.889 1 Day % 0.0666 YTD % 14.8 NAV Date 2026-10-07 NAV Currency EUR</body></html>'
        nav=parse_fam_page('IE000DWG3DP6',text,'https://sample.test')
        self.assertIsNotNone(nav)
        self.assertEqual(nav.nav_date,date(2026,10,7))
        self.assertEqual(nav.nav_eur,163.889)
        self.assertIsNone(parse_fam_page('IE000KTYLDC4',text,'https://sample.test'))

    def test_borsa_parser(self):
        html='<html><body>Fidelity Euro 50 Index A Cap Eur 28,67 +0,30% Valuta: EUR Data: 28/10/26 Andamento Ultima Precedente Valuta Data Variazione Isin LU0261952682</body></html>'
        result=parse_borsa_fidelity('LU0261952682',html,'https://borsa.test')
        self.assertIsNotNone(result)
        self.assertEqual(result.nav_eur,28.67)
        self.assertEqual(result.nav_date,date(2026,10,28))

    def test_old_public_nav_not_allowed_to_override_fineco(self):
        quote=NAVReading('IE000DWG3DP6',date(2026,9,9),159.289,'Issuer','https://issuer.test')
        with patch.object(engine,'fetch_verified_nav',return_value=(quote,'OK')):
            rows, history,summary,_=engine.build_real_portfolio(allow_network=True,persist=False)
        fund=next(r for r in rows if r['ISIN']=='IE000DWG3DP6')
        self.assertEqual(fund['Controvalore_EUR'],5099.32)
        self.assertEqual(fund['Margine_EUR'],93.32)

    def test_future_nav_replaces_only_specific_fund(self):
        q=NAVReading('IE000DWG3DP6',date(2026,10,30),162.0,'Issuer','https://issuer.test')
        def fake_fetch(isin):
            return (q,'OK') if isin=='IE000DWG3DP6' else (None,'offline')
        with patch.object(engine,'fetch_verified_nav',side_effect=fake_fetch):
            rows,history,summary,_=engine.build_real_portfolio(allow_network=True,persist=False)
        changed=next(r for r in rows if r['ISIN']=='IE000DWG3DP6')
        unchanged=next(r for r in rows if r['ISIN']=='IE000KTYLDC4')
        self.assertAlmostEqual(changed['Controvalore_EUR'], round(5099.32*162/161.837,2),places=2)
        self.assertEqual(changed['Fonte_ultimo_dato'],'Issuer')
        self.assertEqual(unchanged['Controvalore_EUR'],5017.0)
        self.assertEqual(len([h for h in history if h['ISIN']=='IE000DWG3DP6']),3)

    def test_public_dashboard_has_visible_true_figures(self):
        with TemporaryDirectory() as td:
            output=Path(td)/'test.html'
            render_real_dashboard(output)
            html=output.read_text(encoding='utf-8')
            for value in ['25.735,13','25.646,20','88,93','AlphaForge v12','Fineco']:
                self.assertIn(value,html)
            self.assertNotIn('26.214',html)
            self.assertEqual(html.count("<article class='fund-card'"),7)

if __name__=='__main__':
    unittest.main()
