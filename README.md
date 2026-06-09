# AlphaForge Intelligence

AI-assisted ETF and stock intelligence dashboard.

AlphaForge aggiorna ranking ETF, allocazione, watchlist azioni e dashboard pubblica tramite GitHub Actions.

## Funzioni principali

- Ranking ETF con score qualità, momentum, rischio ed entry.
- Analisi libera di ETF e azioni tramite ticker.
- Confronto tra strumenti.
- Watchlist intelligente.
- Dashboard pubblica generata in `index.html`.
- Beta tester automatico.
- Patch installer permanente per aggiornamenti futuri.

## File principali

```text
streamlit_app.py
update_etf_data_v3.py
allocation_engine.py
generate_watchlist.py
generate_dashboard.py
auto_update_app.py
beta_test_app.py
core/
pages/
data/watchlist.csv
```

## Workflow

- `Auto update ETF Intelligence App`: aggiorna dati e dashboard.
- `Beta test ETF Intelligence App`: controlla che tutto funzioni.
- `AlphaForge Patch Installer`: installa patch ZIP future.

## Disclaimer

Questa applicazione è solo informativa e non costituisce consulenza finanziaria personalizzata.
