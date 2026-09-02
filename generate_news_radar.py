from __future__ import annotations

from core.news_radar_engine import save_news_radar


def main() -> None:
    radar, summary = save_news_radar()
    print(f"News radar generato: {len(radar)} notizie, {len(summary.get('funds', []))} strumenti")


if __name__ == "__main__":
    main()
