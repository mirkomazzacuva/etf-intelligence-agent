# AlphaForge v10 - Decision Cockpit Fineco

Questa patch rende la dashboard piu' semplice e focalizzata sulle domande pratiche:

- quanto sto guadagnando/perdendo su ogni fondo;
- margine netto stimato al netto del bollo una tantum;
- costi annui visibili per ogni prodotto;
- proiezione a 3 mesi e 1 anno;
- decisione pratica: tieni, tieni ma monitora, valuta switch;
- grafici proxy normalizzati a 100;
- avviso se il valore esatto richiede controvalore Fineco manuale.

## File principali aggiunti

- `core/fund_decision_engine.py`
- `generate_fund_decisions.py`
- `pages/14_Decision_Cockpit.py`
- `data/fineco_actual_values.csv`
- `AlphaForge_Fineco_Decision_Cockpit.csv`
- `AlphaForge_Fineco_Decision_Cockpit.xlsx`
- `AlphaForge_Fineco_Decision_Summary.json`

## Come aggiornare i valori reali Fineco

Per avere margini reali, aggiornare `data/fineco_actual_values.csv` con:

- capitale versato Fineco EUR;
- valore attuale Fineco EUR;
- data valore Fineco.

Se non viene aggiornato, l'app usa:

- 5.000 EUR per ciascun fondo una tantum;
- 0 EUR per i PAC fino alla prima rata;
- proxy ETF/mercato per stimare il contesto.

## Auto update

Il workflow viene eseguito piu' volte al giorno nei giorni lavorativi:

- mattina;
- pomeriggio;
- sera.

Nota: per i fondi comuni il NAV ufficiale non e' real-time e puo' restare fermo all'ultimo giorno lavorativo disponibile.

## Disclaimer

La dashboard e' informativa. Le proiezioni sono scenari automatici, non previsioni garantite e non sono consulenza finanziaria personalizzata.
