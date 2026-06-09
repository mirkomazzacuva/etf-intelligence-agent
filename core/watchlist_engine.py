from __future__ import annotations

from pathlib import Path

import pandas as pd

from core.compare_engine import analyze_instrument
from core.config import DEFAULT_STOCK_WATCHLIST, WATCHLIST_FILE, WATCHLIST_OUTPUT_CSV, WATCHLIST_OUTPUT_XLSX


def ensure_watchlist_file(path: Path = WATCHLIST_FILE) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        pd.DataFrame(DEFAULT_STOCK_WATCHLIST).to_csv(path, index=False)
    return path


def load_watchlist(path: Path = WATCHLIST_FILE) -> pd.DataFrame:
    ensure_watchlist_file(path)
    try:
        df = pd.read_csv(path)
    except Exception:  # noqa: BLE001
        df = pd.DataFrame(DEFAULT_STOCK_WATCHLIST)
    if "Ticker" not in df.columns:
        df = pd.DataFrame(DEFAULT_STOCK_WATCHLIST)
    return df.dropna(subset=["Ticker"]).drop_duplicates(subset=["Ticker"])


def analyze_watchlist(path: Path = WATCHLIST_FILE) -> pd.DataFrame:
    source = load_watchlist(path)
    rows = []
    for _, row in source.iterrows():
        ticker = str(row.get("Ticker", "")).strip().upper()
        if not ticker:
            continue
        result = analyze_instrument(ticker, preferred_type=str(row.get("Tipo", "") or "Stock"))
        for col in ["Nome", "Area", "Tipo"]:
            if col in row and row.get(col):
                result.setdefault(col, row.get(col))
        rows.append(result)
    out = pd.DataFrame(rows)
    if not out.empty and "Score Finale" in out.columns:
        out = out.sort_values("Score Finale", ascending=False, na_position="last")
    return out


def save_watchlist_outputs(df: pd.DataFrame) -> None:
    if df.empty:
        return
    df.to_csv(WATCHLIST_OUTPUT_CSV, index=False)
    with pd.ExcelWriter(WATCHLIST_OUTPUT_XLSX, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Watchlist", index=False)
