# AlphaForge Intelligence

AlphaForge Intelligence è una dashboard Python/Streamlit per analisi informativa di ETF e azioni.

## Funzioni principali

- Ranking ETF automatico.
- Allocazione informativa su capitale simulato.
- Watchlist azioni e strumenti.
- Analisi libera di ticker ETF/azioni.
- Confronto tra strumenti.
- Priority Score, Entry Zone, Risk Flag e scenari pratici.
- AI Assistant controllato su dati e score calcolati.
- Dashboard pubblica tramite GitHub Pages.
- Aggiornamento automatico tramite GitHub Actions.
- Beta tester automatico.

## Output principali

```text
ETF_Intelligence_Agent_UPDATED.xlsx
ETF_Allocation_Model.xlsx
AlphaForge_Watchlist.csv
AlphaForge_Watchlist.xlsx
AlphaForge_Insights.csv
AlphaForge_Insights.xlsx
ETF_Daily_Report.txt
AUTO_UPDATE_STATUS.json
index.html
```

## Avvio locale

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Aggiornamento dati

```bash
python auto_update_app.py
```

## Disclaimer

Il progetto è solo informativo e non costituisce consulenza finanziaria personalizzata, sollecitazione al risparmio o raccomandazione di acquisto/vendita.
