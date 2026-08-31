# AlphaForge v7 Sector Compass

Questa versione semplifica la lettura dell'app per un uso reale con portafoglio Fineco e consulente.

## Nuovo obiettivo

Non partire piu' da decine di score o ticker. La lettura diventa:

1. Core globale gia' presente: All-World, MSCI World, fondi globali.
2. Settori satellite da discutere.
3. Per ogni settore: ETF/fondo candidato, azioni leader solo come alternativa rischiosa.
4. Portafoglio reale: carica CSV/XLSX e verifica peso core, satellite e concentrazione.

## Nuovi file

- `data/sector_universe.csv`
- `data/fineco_portfolio_template.csv`
- `generate_sector_compass.py`
- `AlphaForge_Sector_Compass.csv`
- `AlphaForge_Sector_Compass.xlsx`
- `core/sector_compass_engine.py`
- `pages/9_Bussola_Settoriale.py`
- `pages/10_Portafoglio_Fineco.py`

## Come usarla

La dashboard pubblica mostra la bussola settoriale. L'app Streamlit permette anche di caricare il portafoglio personale.

## Nota importante

Gli ETF/fondi indicati sono candidati da verificare. Prima di investire controllare disponibilita' su Fineco, KID, costi, liquidita', fiscalita', rischio valuta e adeguatezza con il consulente.
