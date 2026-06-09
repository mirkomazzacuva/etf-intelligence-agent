# Aggiornamenti automatici ETF Intelligence App

Questa patch rende l'app piu pratica per l'utente finale:

- aggiornamento automatico ogni giorno feriale dopo la chiusura dei mercati europei;
- aggiornamento manuale da GitHub Actions con pulsante `Run workflow`;
- aggiornamento manuale dall'app Streamlit con pulsante `Aggiorna ora`, utile in locale;
- file `AUTO_UPDATE_STATUS.json` con esito leggibile dell'ultimo aggiornamento;
- log tecnico in `logs/update_log.jsonl`;
- dashboard Streamlit piu chiara, con stato aggiornamento visibile nella sidebar.

## File da copiare nel repository

Copia questi file nella root del repository, sostituendo quelli esistenti quando richiesto:

```text
streamlit_app.py
update_etf_data_v3.py
allocation_engine.py
generate_dashboard.py
requirements.txt
auto_update_app.py
.github/workflows/etf_agent.yml
README_AUTO_UPDATE.md
```

## Come funziona

Il workflow `.github/workflows/etf_agent.yml` esegue:

```bash
python auto_update_app.py
```

A sua volta `auto_update_app.py` lancia in ordine:

```bash
python update_etf_data_v3.py
python allocation_engine.py
python generate_dashboard.py
```

Se tutto va bene, GitHub Actions salva nel repository i file aggiornati:

```text
ETF_Intelligence_Agent_UPDATED.xlsx
ETF_Allocation_Model.xlsx
ETF_Daily_Report.txt
index.html
AUTO_UPDATE_STATUS.json
logs/update_log.jsonl
```

## Orario aggiornamento automatico

Il cron e:

```yaml
- cron: "30 18 * * 1-5"
```

GitHub Actions usa UTC. Quindi equivale circa a:

- 20:30 in Italia con ora legale;
- 19:30 in Italia con ora solare.

## Come lanciare aggiornamento manuale da GitHub

1. Apri il repository su GitHub.
2. Vai su `Actions`.
3. Seleziona `Auto update ETF Intelligence App`.
4. Premi `Run workflow`.
5. Aspetta la fine del workflow.
6. Riapri l'app Streamlit: vedrai ultimo aggiornamento e stato.

## Come usarlo in locale

```bash
pip install -r requirements.txt
python auto_update_app.py
streamlit run streamlit_app.py
```

## Nota importante

Il pulsante `Aggiorna ora` dentro Streamlit aggiorna i file nell'ambiente in cui gira l'app. Se l'app gira su Streamlit Cloud, l'aggiornamento piu solido resta quello tramite GitHub Actions, perche committa i file nel repository.

## Disclaimer

Il sistema produce analisi informative e non costituisce consulenza finanziaria personalizzata.
