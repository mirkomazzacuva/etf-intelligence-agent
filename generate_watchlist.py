from __future__ import annotations

from core.watchlist_engine import analyze_watchlist, save_watchlist_outputs


if __name__ == "__main__":
    watchlist = analyze_watchlist()
    save_watchlist_outputs(watchlist)
    print(f"Watchlist aggiornata: {len(watchlist)} strumenti")
