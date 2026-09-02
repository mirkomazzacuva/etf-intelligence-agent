from __future__ import annotations

from core.fund_market_engine import save_fund_performance


def main() -> None:
    performance, history = save_fund_performance()
    print(f"Performance fondi/proxy generata: {len(performance)} strumenti, {len(history)} punti storici")


if __name__ == "__main__":
    main()
