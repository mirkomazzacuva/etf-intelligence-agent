import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime

INPUT_FILE = "ETF_Intelligence_Agent_Master_Populated.xlsx"
OUTPUT_FILE = "ETF_Intelligence_Agent_UPDATED.xlsx"
REPORT_FILE = "ETF_Daily_Report.txt"
RISK_FREE_RATE = 0.02

def normalize_ticker(ticker):
    ticker = str(ticker).strip()
    return ticker if "." in ticker else ticker + ".MI"

def get_prices(ticker):
    data = yf.download(ticker, period="5y", interval="1d", auto_adjust=True, progress=False)
    if data is None or data.empty:
        return None
    prices = data["Close"] if "Close" in data.columns else None
    if isinstance(prices, pd.DataFrame):
        prices = prices.iloc[:, 0]
    prices = pd.to_numeric(prices, errors="coerce").dropna()
    return prices if len(prices) >= 30 else None

def period_return(p, days):
    return np.nan if p is None or len(p) <= days else (p.iloc[-1] / p.iloc[-days] - 1) * 100

def cagr(p):
    if p is None or len(p) < 30:
        return np.nan
    years = len(p) / 252
    return ((p.iloc[-1] / p.iloc[0]) ** (1 / years) - 1) * 100

def volatility(p):
    if p is None or len(p) < 30:
        return np.nan
    return p.pct_change().dropna().std() * np.sqrt(252) * 100

def max_drawdown(p):
    if p is None or len(p) < 30:
        return np.nan
    return ((p / p.cummax()) - 1).min() * 100

def sharpe(p):
    ca = cagr(p)
    vol = volatility(p)
    if pd.isna(ca) or pd.isna(vol) or vol == 0:
        return np.nan
    return ((ca / 100) - RISK_FREE_RATE) / (vol / 100)

def base_score(r):
    score = 50
    if pd.notna(r["Rendimento 12M %"]):
        score += min(max(r["Rendimento 12M %"], -30), 50) * 0.25
    if pd.notna(r["Rendimento 6M %"]):
        score += min(max(r["Rendimento 6M %"], -20), 35) * 0.20
    if pd.notna(r["Sharpe"]):
        score += min(max(r["Sharpe"], -1), 2) * 8
    if pd.notna(r["Volatilità %"]):
        score -= min(max(r["Volatilità %"] - 12, 0), 30) * 0.35
    if pd.notna(r["Max Drawdown %"]):
        score += max(r["Max Drawdown %"], -60) * 0.20
    score += 8 if r["Trend OK"] == "Sì" else -8
    return round(max(min(score, 100), 0), 1)

def macro_score(row):
    tema = str(row.get("Tema/Area", "")).lower()
    score = 0
    if "gold" in tema: score += 8
    if "defense" in tema: score += 7
    if "quality" in tema: score += 5
    if "global equity" in tema: score += 4
    if "bonds" in tema: score += 3
    if "artificial intelligence" in tema: score += 6
    if "semiconductors" in tema: score += 5
    if "emerging" in tema: score += 2
    return score

def penalty(row):
    tema = str(row.get("Tema/Area", "")).lower()
    vol = row.get("Volatilità %", np.nan)
    dd = row.get("Max Drawdown %", np.nan)
    r12 = row.get("Rendimento 12M %", np.nan)
    p = 0
    if "artificial intelligence" in tema: p -= 5
    if "semiconductors" in tema: p -= 7
    if "nasdaq" in tema: p -= 4
    if pd.notna(vol) and vol > 25: p -= 5
    if pd.notna(dd) and dd < -35: p -= 5
    if pd.notna(r12) and r12 > 70: p -= 6
    return p

def classify(score):
    if pd.isna(score): return "No data"
    if score >= 80: return "Buy Watchlist"
    if score >= 65: return "Accumulate Carefully"
    if score >= 50: return "Hold / Monitor"
    if score >= 35: return "Avoid for Now"
    return "Speculative Only"

def note(row):
    tema = str(row.get("Tema/Area", ""))
    notes = []
    if "Artificial Intelligence" in tema:
        notes.append("Tema strutturale forte, ma rischio euforia/concentrazione elevato.")
    if "Semiconductors" in tema:
        notes.append("Tema molto forte, ma ciclico e volatile.")
    if "Gold" in tema:
        notes.append("Utile come protezione macro/geopolitica.")
    if "Global Equity" in tema:
        notes.append("Buona base core di lungo periodo.")
    if "Bonds" in tema:
        notes.append("Componente difensiva, utile per bilanciare rischio equity.")
    if "Defense" in tema:
        notes.append("Tema sostenuto da contesto geopolitico, ma da usare come satellite.")
    if pd.notna(row.get("Volatilità %")) and row["Volatilità %"] > 25:
        notes.append("Volatilità elevata.")
    if pd.notna(row.get("Max Drawdown %")) and row["Max Drawdown %"] < -35:
        notes.append("Drawdown storico importante.")
    return " ".join(notes) if notes else "Monitorare secondo score e trend."

df = pd.read_excel(INPUT_FILE, sheet_name="ETF_Master")
results = []

for _, row in df.iterrows():
    out = row.to_dict()
    ticker = normalize_ticker(out["Ticker"])
    out["Ticker"] = ticker
    print("Aggiorno:", ticker)

    prices = get_prices(ticker)

    if prices is None:
        out["Fonte dati"] = "No data"
        out["Score Finale"] = np.nan
        out["Stato"] = "No data"
        results.append(out)
        continue

    out["Prezzo"] = round(float(prices.iloc[-1]), 4)
    out["MA50"] = round(float(prices.tail(50).mean()), 4)
    out["MA200"] = round(float(prices.tail(200).mean()), 4) if len(prices) >= 200 else np.nan
    out["Trend OK"] = "Sì" if pd.notna(out["MA200"]) and out["Prezzo"] > out["MA200"] else "No"
    out["Rendimento 1M %"] = round(period_return(prices, 21), 2)
    out["Rendimento 3M %"] = round(period_return(prices, 63), 2)
    out["Rendimento 6M %"] = round(period_return(prices, 126), 2)
    out["Rendimento 12M %"] = round(period_return(prices, 252), 2)
    out["CAGR storico %"] = round(cagr(prices), 2)
    out["Volatilità %"] = round(volatility(prices), 2)
    out["Max Drawdown %"] = round(max_drawdown(prices), 2)
    out["Sharpe"] = round(sharpe(prices), 2)
    out["Anni storico"] = round(len(prices) / 252, 2)
    out["Fonte dati"] = "Yahoo Finance"

    out["Score Finale Base"] = base_score(out)
    out["Macro Score"] = macro_score(out)
    out["Penalità"] = penalty(out)
    out["Score Finale"] = round(max(min(out["Score Finale Base"] + out["Macro Score"] + out["Penalità"], 100), 0), 1)
    out["Stato"] = classify(out["Score Finale"])
    out["Note AI"] = note(out)

    results.append(out)

result = pd.DataFrame(results).sort_values("Score Finale", ascending=False, na_position="last")
result.to_excel(OUTPUT_FILE, index=False)

top = result.head(10)
lines = []
lines.append("ETF INTELLIGENCE REPORT")
lines.append(f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
lines.append("")
lines.append(f"Miglior ETF del giorno: {top.iloc[0]['Nome ETF']} ({top.iloc[0]['Ticker']}) - Score {top.iloc[0]['Score Finale']}")
lines.append("")
lines.append("TOP 10 ETF:")
for _, r in top.iterrows():
    lines.append(f"- {r['Ticker']} | {r['Nome ETF']} | Score {r['Score Finale']} | {r['Stato']} | Nota: {r.get('Note AI', '')}")

lines.append("")
lines.append("Lettura prudente:")
lines.append("- Non sono segnali automatici di acquisto.")
lines.append("- Gli ETF tematici vanno trattati come satellite.")
lines.append("- Gli ETF core globali sono più adatti come base.")
lines.append("- Oro/difensivi aiutano a bilanciare rischio macro.")
lines.append("")
lines.append("Disclaimer: report informativo, non consulenza finanziaria personalizzata.")

with open(REPORT_FILE, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print("\n".join(lines))
print("Creati:", OUTPUT_FILE, REPORT_FILE)
