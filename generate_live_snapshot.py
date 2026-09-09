from __future__ import annotations

from core.live_value_engine import save_live_portfolio_snapshot


if __name__ == "__main__":
    live, history, summary = save_live_portfolio_snapshot()
    print(f"Live snapshot generato: {len(live)} strumenti, {len(history)} punti grafico")
    print(summary)
