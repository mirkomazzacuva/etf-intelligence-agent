# AlphaForge v6 Action First & Portfolio

Questa patch rende AlphaForge piu pratico per l'utente finale.

## Novita principali

- Sezione iniziale **Cosa fare adesso**.
- Bucket operativi: azione controllata, attendi pullback, controllo rischio, monitoraggio.
- Dashboard pubblica v6 piu guidata e meno tabellare.
- Portafoglio utente migliorato con Health Score, gap target e suggerimenti per posizione.
- Nuova pagina Streamlit `8_Cosa_Fare_Adesso.py`.
- Nuovo motore `core/action_guide_engine.py`.

## File aggiornati

- `core/action_guide_engine.py`
- `core/portfolio_engine.py`
- `core/report_engine.py`
- `streamlit_app.py`
- `pages/7_Portafoglio.py`
- `pages/8_Cosa_Fare_Adesso.py`
- `auto_update_app.py`
- `generate_dashboard.py`
- `beta_test_app.py`
- `data/portfolio_template.csv`

## Dopo installazione

Eseguire Patch Installer con:

- `run_beta_test = true`
- `run_full_update = true`
- `remove_patch_zip = true`

Poi controllare GitHub Pages: deve apparire **AlphaForge v6 Action First**.
