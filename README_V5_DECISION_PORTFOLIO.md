# AlphaForge v5 - Decision & Portfolio

Questa patch rende AlphaForge più pratico per l'utente finale.

## Novità principali

- **Cosa fare adesso**: nuova vista operativa che traduce score, rischio ed entry zone in una decisione chiara.
- **Action Plan**: generazione automatica di `AlphaForge_Action_Plan.csv` e `AlphaForge_Action_Plan.xlsx`.
- **Portafoglio utente**: pagina Streamlit per caricare CSV/XLSX con posizioni già possedute.
- **Analisi portafoglio**: peso reale, concentrazione, P/L indicativo, high risk, posizioni senza score e suggerimenti di miglioramento.
- **Dashboard pubblica v5**: sezione iniziale orientata a cosa fare, non solo a leggere score.

## File nuovi

- `core/decision_engine.py`
- `generate_decisions.py`
- `pages/7_Portafoglio.py`
- `data/portfolio_template.csv`
- `AlphaForge_Action_Plan.csv/xlsx` generati dall'aggiornamento completo

## Come usare il portafoglio

Aprire l'app Streamlit e andare nella pagina **Portafoglio**.
Caricare un CSV/XLSX con colonne tipo:

- `Ticker`
- `Quantità`
- `Prezzo Medio`
- `Valore EUR`
- `Target %`
- `Categoria Utente`

Il sistema accetta anche varianti come `qty`, `pmc`, `valore`, `peso target`.

## Nota

AlphaForge è uno strumento informativo. Le decisioni chiare non sono ordini di acquisto/vendita e non sostituiscono consulenza finanziaria personalizzata.
