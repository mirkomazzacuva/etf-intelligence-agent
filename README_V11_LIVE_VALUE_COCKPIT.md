# AlphaForge v11 - Live Value Cockpit

Questa patch trasforma il tracker Fineco in una vista più pratica:

- aggiornamento live/proxy all'apertura della versione Streamlit;
- controvalore attuale stimato per ogni fondo/PAC;
- margine/guadagno netto dalla sottoscrizione;
- costo maturato stimato;
- proiezione a 3 mesi e 1 anno;
- segnale pratico: tieni, monitora, valuta alternativa con consulente;
- grafici aggiornati dei proxy per ogni fondo.

## Limite importante

I fondi comuni hanno NAV ufficiale giornaliero e l'app non può leggere il conto Fineco senza export o inserimento manuale. Per questo:

- se `data/fineco_actual_values.csv` contiene valori Fineco reali e `Usa Valore Fineco = si`, il margine usa quelli;
- altrimenti l'app usa proxy di mercato scaricati live con yfinance/Stooq.

GitHub Pages resta una dashboard statica: si aggiorna quando gira GitHub Actions. L'aggiornamento all'apertura funziona nella versione Streamlit.

## File principali

- `core/live_value_engine.py`
- `generate_live_snapshot.py`
- `streamlit_app.py`
- `pages/14_Decision_Cockpit.py`
- `core/fund_decision_engine.py`
- `.github/workflows/etf_agent.yml`

## File output nuovi

- `AlphaForge_Live_Portfolio.csv`
- `AlphaForge_Live_Price_History.csv`
- `AlphaForge_Live_Summary.json`

