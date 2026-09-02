from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any

import pandas as pd

from core.config import (
    FINECO_FUNDS_PUBLIC_FILE,
    FINECO_NEWS_RADAR_CSV,
    FINECO_NEWS_RADAR_SUMMARY,
    FINECO_NEWS_RADAR_XLSX,
)

POSITIVE_WORDS = [
    "rally", "gain", "gains", "up", "surge", "beats", "upgrade", "growth", "cut rates", "rate cut",
    "soft landing", "record high", "bull", "positive", "strong", "rebound", "recover", "outperform",
    "taglio tassi", "rialzo", "crescita", "recupero", "positivo", "utili migliori", "maximi",
]
NEGATIVE_WORDS = [
    "selloff", "sell-off", "down", "drop", "loss", "losses", "downgrade", "recession", "inflation",
    "higher rates", "rate hike", "war", "tariff", "risk", "risks", "weak", "miss", "bear", "default",
    "crollo", "perdita", "perdite", "recessione", "inflazione", "rischio", "tassi alti", "guerra", "dazi", "debole",
]


def _load_funds() -> pd.DataFrame:
    if FINECO_FUNDS_PUBLIC_FILE.exists():
        return pd.read_csv(FINECO_FUNDS_PUBLIC_FILE)
    return pd.DataFrame()


def _clean_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _score_text(text: str) -> int:
    low = text.lower()
    score = 0
    for word in POSITIVE_WORDS:
        if word in low:
            score += 1
    for word in NEGATIVE_WORDS:
        if word in low:
            score -= 1
    return score


def _bias_from_score(score: float, count: int) -> str:
    if count == 0:
        return "Neutro: nessuna notizia rilevante trovata"
    if score >= 1.0:
        return "Potenzialmente favorevole"
    if score <= -1.0:
        return "Attenzione / pressione negativa"
    return "Neutro / da monitorare"


def _fetch_google_news(query: str, limit: int = 5) -> list[dict[str, Any]]:
    if not query:
        return []
    encoded = urllib.parse.quote_plus(query)
    url = f"https://news.google.com/rss/search?q={encoded}&hl=it&gl=IT&ceid=IT:it"
    headers = {"User-Agent": "Mozilla/5.0 AlphaForge News Radar"}
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as response:  # nosec B310 - public RSS feed
            raw = response.read()
        root = ET.fromstring(raw)
        items = []
        for item in root.findall(".//item")[:limit]:
            title = _clean_html(item.findtext("title") or "")
            link = item.findtext("link") or ""
            pub_date = item.findtext("pubDate") or ""
            source = item.findtext("source") or "Google News"
            items.append({"title": title, "link": link, "published": pub_date, "source": source})
        return items
    except Exception as exc:  # noqa: BLE001
        return [{"title": f"News non disponibili: {exc}", "link": "", "published": "", "source": "system"}]


def build_news_radar() -> tuple[pd.DataFrame, dict[str, Any]]:
    funds = _load_funds()
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rows: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []

    if funds.empty:
        empty = pd.DataFrame()
        return empty, {"version": "AlphaForge v9.1 News Radar", "generated_at": generated_at, "message": "Nessun fondo configurato"}

    for _, fund in funds.iterrows():
        query = str(fund.get("News Query", "") or fund.get("Nome Strumento", ""))
        category = str(fund.get("Categoria AlphaForge", ""))
        isin = str(fund.get("ISIN", ""))
        name = str(fund.get("Nome Strumento", ""))
        items = _fetch_google_news(query, limit=5)
        scores = []
        for news in items:
            title = news.get("title", "")
            score = _score_text(title)
            scores.append(score)
            rows.append({
                "ISIN": isin,
                "Nome Strumento": name,
                "Categoria AlphaForge": category,
                "Query": query,
                "Titolo": title,
                "Fonte": news.get("source", ""),
                "Data news": news.get("published", ""),
                "Link": news.get("link", ""),
                "News Score": score,
                "Lettura": _bias_from_score(score, 1),
                "Impatto possibile": _impact_from_category(category, title, score),
                "Aggiornato UTC": generated_at,
            })
        score_sum = sum(scores)
        valid_count = len([s for s in scores if isinstance(s, int)])
        summary_rows.append({
            "ISIN": isin,
            "Nome Strumento": name,
            "Categoria AlphaForge": category,
            "News trovate": len(items),
            "News Score Totale": score_sum,
            "Bias prossimi giorni": _bias_from_score(score_sum, valid_count),
            "Cosa fare": _action_from_bias(score_sum, valid_count),
        })

    radar = pd.DataFrame(rows)
    summary = {
        "version": "AlphaForge v9.1 News Radar",
        "generated_at": generated_at,
        "disclaimer": "Il bias e' una lettura automatica di notizie e momentum, non una previsione o raccomandazione.",
        "funds": summary_rows,
    }
    return radar, summary


def _impact_from_category(category: str, title: str, score: int) -> str:
    cat = category.lower()
    if score < 0:
        if "tecnologia" in cat or "ai" in cat:
            return "Potrebbe pesare su fondi tech/AI nel breve"
        if "emerging" in cat or "emergenti" in cat:
            return "Potrebbe pesare su emergenti, valuta o rischio globale"
        if "europa" in cat:
            return "Potrebbe pesare su azionario europeo"
        return "Potenziale pressione negativa di breve periodo"
    if score > 0:
        if "tecnologia" in cat or "ai" in cat:
            return "Potrebbe supportare fondi tech/AI nel breve"
        if "emerging" in cat or "emergenti" in cat:
            return "Potrebbe supportare emergenti o sentiment globale"
        if "europa" in cat:
            return "Potrebbe supportare azionario europeo"
        return "Potenziale supporto di breve periodo"
    return "Da monitorare: impatto non evidente"


def _action_from_bias(score: int, count: int) -> str:
    if count == 0:
        return "Nessuna azione: attendere nuove notizie o aggiornare manualmente"
    if score >= 2:
        return "Scenario favorevole: non inseguire, usare PAC/ingressi graduali"
    if score <= -2:
        return "Scenario negativo: non aumentare esposizione, monitorare supporti/NAV"
    return "Scenario neutro: continuare monitoraggio e confrontare con andamento fondi"


def save_news_radar() -> tuple[pd.DataFrame, dict[str, Any]]:
    radar, summary = build_news_radar()
    radar.to_csv(FINECO_NEWS_RADAR_CSV, index=False)
    radar.to_excel(FINECO_NEWS_RADAR_XLSX, index=False)
    FINECO_NEWS_RADAR_SUMMARY.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return radar, summary
