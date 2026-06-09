from __future__ import annotations

from pathlib import Path

RANKING_FILE = Path("ETF_Intelligence_Agent_UPDATED.xlsx")
MASTER_FILE = Path("ETF_Intelligence_Agent_Master_Populated.xlsx")
ALLOCATION_FILE = Path("ETF_Allocation_Model.xlsx")
REPORT_FILE = Path("ETF_Daily_Report.txt")
STATUS_FILE = Path("AUTO_UPDATE_STATUS.json")
DASHBOARD_FILE = Path("index.html")
WATCHLIST_FILE = Path("data/watchlist.csv")
WATCHLIST_OUTPUT_XLSX = Path("AlphaForge_Watchlist.xlsx")
WATCHLIST_OUTPUT_CSV = Path("AlphaForge_Watchlist.csv")
INSIGHTS_OUTPUT_XLSX = Path("AlphaForge_Insights.xlsx")
INSIGHTS_OUTPUT_CSV = Path("AlphaForge_Insights.csv")
ACTION_PLAN_OUTPUT_XLSX = Path("AlphaForge_Action_Plan.xlsx")
ACTION_PLAN_OUTPUT_CSV = Path("AlphaForge_Action_Plan.csv")
PORTFOLIO_TEMPLATE_FILE = Path("data/portfolio_template.csv")

DEFAULT_ETF_UNIVERSE = [
    {"Ticker": "SWDA.MI", "Nome ETF": "iShares Core MSCI World", "Categoria": "Core", "Tema/Area": "Azionario globale sviluppato"},
    {"Ticker": "VWCE.DE", "Nome ETF": "Vanguard FTSE All-World", "Categoria": "Core", "Tema/Area": "Azionario globale"},
    {"Ticker": "EIMI.MI", "Nome ETF": "iShares Core MSCI EM IMI", "Categoria": "Core", "Tema/Area": "Mercati emergenti"},
    {"Ticker": "SXR8.DE", "Nome ETF": "iShares Core S&P 500", "Categoria": "Core", "Tema/Area": "USA large cap"},
    {"Ticker": "XDEV.MI", "Nome ETF": "Xtrackers MSCI World Value", "Categoria": "Factor", "Tema/Area": "Value globale"},
    {"Ticker": "IWQU.MI", "Nome ETF": "iShares Edge MSCI World Quality", "Categoria": "Factor", "Tema/Area": "Quality globale"},
    {"Ticker": "MVOL.MI", "Nome ETF": "iShares Edge MSCI World Minimum Volatility", "Categoria": "Defensive", "Tema/Area": "Min volatility"},
    {"Ticker": "EUNA.MI", "Nome ETF": "iShares Core Global Aggregate Bond", "Categoria": "Defensive", "Tema/Area": "Obbligazionario globale"},
    {"Ticker": "SGLD.MI", "Nome ETF": "Invesco Physical Gold", "Categoria": "Defensive", "Tema/Area": "Oro"},
    {"Ticker": "EXSA.DE", "Nome ETF": "iShares STOXX Europe 600", "Categoria": "Core", "Tema/Area": "Europa"},
    {"Ticker": "RBOT.MI", "Nome ETF": "iShares Automation & Robotics", "Categoria": "Thematic", "Tema/Area": "Robotica e automazione"},
    {"Ticker": "WCLD.MI", "Nome ETF": "WisdomTree Cloud Computing", "Categoria": "Thematic", "Tema/Area": "Cloud"},
    {"Ticker": "SMH", "Nome ETF": "VanEck Semiconductor", "Categoria": "Thematic", "Tema/Area": "Semiconduttori"},
    {"Ticker": "INRG.MI", "Nome ETF": "iShares Global Clean Energy", "Categoria": "Thematic", "Tema/Area": "Energia pulita"},
]

DEFAULT_MODEL_BASKETS = {
    "AI & Semiconductors": ["NVDA", "AMD", "ASML.AS", "SMH", "STM.MI"],
    "Core ETF": ["SWDA.MI", "VWCE.DE", "SXR8.DE", "EIMI.MI"],
    "Defensive": ["EUNA.MI", "SGLD.MI", "MVOL.MI"],
    "Big Tech": ["AAPL", "MSFT", "GOOGL", "AMZN", "META"],
}

DEFAULT_STOCK_WATCHLIST = [
    {"Ticker": "AAPL", "Nome": "Apple", "Tipo": "Stock", "Area": "USA / Technology"},
    {"Ticker": "MSFT", "Nome": "Microsoft", "Tipo": "Stock", "Area": "USA / Technology"},
    {"Ticker": "NVDA", "Nome": "NVIDIA", "Tipo": "Stock", "Area": "USA / Semiconductors"},
    {"Ticker": "ASML.AS", "Nome": "ASML", "Tipo": "Stock", "Area": "Europe / Semiconductors"},
    {"Ticker": "STM.MI", "Nome": "STMicroelectronics", "Tipo": "Stock", "Area": "Italy / Semiconductors"},
    {"Ticker": "GOOGL", "Nome": "Alphabet", "Tipo": "Stock", "Area": "USA / Internet"},
    {"Ticker": "AMZN", "Nome": "Amazon", "Tipo": "Stock", "Area": "USA / Consumer & Cloud"},
    {"Ticker": "META", "Nome": "Meta Platforms", "Tipo": "Stock", "Area": "USA / Social & AI"},
    {"Ticker": "TSLA", "Nome": "Tesla", "Tipo": "Stock", "Area": "USA / EV"},
]
