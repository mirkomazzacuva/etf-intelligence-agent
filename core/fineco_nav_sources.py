"""Best-effort NAV sources; only dates and ISIN-verified official fund quotes.

No market ETF proxy is ever substituted for a fund NAV. Network errors are nonfatal.
The screen snapshot is the trusted fallback when feeds are unavailable or stale.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from html.parser import HTMLParser
import re
from typing import Optional

import requests

ISSUER_PAGES = {
    'IE0003YRHWF4': 'https://finecoassetmanagement.com/it/archives/products/sustainable-future-connectivity-fam-fund-5',
    'IE00BD2PJG29': 'https://finecoassetmanagement.com/it/archives/products/fam-msci-emerging-markets-index-fund',
    'LU0981915779': 'https://finecoassetmanagement.com/it/archives/products/core-dividend-4',
    'IE000DWG3DP6': 'https://finecoassetmanagement.com/it/archives/products/fineco-am-passive-underlyings-8',
    'IE0005TOUMC7': 'https://finecoassetmanagement.com/it/archives/products/fineco-am-passive-underlyings-7',
    'IE000KTYLDC4': 'https://finecoassetmanagement.com/it/archives/products/fineco-am-passive-underlyings-6',
    'LU0261952682': 'https://www.borsaitaliana.it/borsa/fondi/dettaglio/2FIDES50.html?lang=it',
}


@dataclass(frozen=True)
class NAVReading:
    isin: str
    nav_date: date
    nav_eur: float
    source: str
    url: str


class _VisibleText(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.fragments: list[str] = []
        self.invisible = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in ('script', 'style', 'svg', 'noscript'):
            self.invisible += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in ('script', 'style', 'svg', 'noscript'):
            self.invisible = max(0, self.invisible - 1)

    def handle_data(self, data: str) -> None:
        if not self.invisible and data.strip():
            self.fragments.append(data.strip())


def _text(html: str) -> str:
    parser = _VisibleText()
    parser.feed(html)
    return re.sub(r'\s+', ' ', ' '.join(parser.fragments)).strip()


def _number(raw: str) -> float:
    s = raw.strip().replace(' ', '')
    if ',' in s and '.' in s:
        s = s.replace('.', '').replace(',', '.') if s.rfind(',') > s.rfind('.') else s.replace(',', '')
    elif ',' in s:
        s = s.replace(',', '.')
    return float(s)


def parse_fam_page(isin: str, html: str, url: str) -> Optional[NAVReading]:
    text = _text(html)
    if isin not in text:
        return None
    price = re.search(r'\bNAV\s+Price\s+([0-9][0-9.,]*)\b', text, re.I)
    dated = re.search(r'\bNAV\s+Date\s+(20[0-9]{2}-[0-9]{2}-[0-9]{2})\b', text, re.I)
    if not price or not dated:
        return None
    try:
        nav = _number(price.group(1))
        day = date.fromisoformat(dated.group(1))
    except (ValueError, TypeError):
        return None
    if not 0.01 < nav < 100000 or day > date.today():
        return None
    return NAVReading(isin, day, nav, 'Fineco Asset Management', url)


def parse_borsa_fidelity(isin: str, html: str, url: str) -> Optional[NAVReading]:
    text = _text(html)
    if isin not in text:
        return None
    # Example: Fidelity Euro 50 Index ... 29,33 +0,93% Valuta: EUR Data: 11/09/26
    head = text[: max(0, text.find('Andamento'))] if 'Andamento' in text else text[:1800]
    match = re.search(
        r'([0-9]{1,4}[.,][0-9]{1,5})\s*[+-]\s*[0-9]+[.,][0-9]+\s*%\s*Valuta\s*:\s*EUR\s*Data\s*:\s*(\d{2}/\d{2}/\d{2,4})',
        head, re.I,
    )
    # Some pages put the NAV in the "Andamento" first data row rather than the header.
    if not match:
        match = re.search(
            r'\bUltima\s+Precedente\s+Valuta\s+Data\s+Variazione\s+([0-9]{1,4}[.,][0-9]{1,5})\s+[0-9]{1,4}[.,][0-9]{1,5}\s+EUR\s+(\d{2}/\d{2}/\d{2,4})',
            text, re.I,
        )
    if not match:
        return None
    try:
        nav = _number(match.group(1))
        day = datetime.strptime(match.group(2), '%d/%m/%y' if len(match.group(2)) == 8 else '%d/%m/%Y').date()
    except (ValueError, TypeError):
        return None
    if not 0.01 < nav < 100000 or day > date.today():
        return None
    return NAVReading(isin, day, nav, 'Borsa Italiana', url)


def fetch_verified_nav(isin: str, timeout: float = 12.0) -> tuple[Optional[NAVReading], str]:
    url = ISSUER_PAGES.get(isin)
    if not url:
        return None, 'ISIN senza fonte di NAV configurata'
    try:
        response = requests.get(
            url,
            timeout=timeout,
            headers={'User-Agent': 'Mozilla/5.0 (compatible; AlphaForge-Portfolio/12.0; personal financial dashboard)', 'Accept': 'text/html'},
        )
        response.raise_for_status()
        reading = parse_borsa_fidelity(isin, response.text, url) if isin == 'LU0261952682' else parse_fam_page(isin, response.text, url)
        if reading is None:
            return None, 'Pagina raggiunta, ma NAV/data o ISIN non verificabili'
        return reading, 'OK'
    except requests.RequestException as exc:
        return None, f'Fonte non raggiungibile: {exc.__class__.__name__}'
