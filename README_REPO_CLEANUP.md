# Pulizia repository AlphaForge / ETF Intelligence Agent

Questa patch serve ad allineare i file del repository ed evitare conflitti tra workflow, app Streamlit e beta test.

## File aggiunti o sostituiti

- `auto_update_app.py`
- `streamlit_app.py`
- `beta_test_app.py`
- `.github/workflows/etf_agent.yml`
- `.github/workflows/beta_test_app.yml`
- `.gitignore`
- `README_BETA_TEST.md`

## File da eliminare manualmente dal repository

Il file seguente e' un archivio vecchio dentro al repository e puo' creare confusione perche' duplica codice e dati:

```bash
git rm ETF_AI_AGENT_FREE.zip
```

Oppure da GitHub web: apri `ETF_AI_AGENT_FREE.zip`, menu `...`, `Delete file`, poi commit.

## File da tenere

Questi sono file sorgente o file dati usati dall'app:

- `streamlit_app.py`
- `auto_update_app.py`
- `update_etf_data_v3.py`
- `allocation_engine.py`
- `generate_dashboard.py`
- `beta_test_app.py`
- `requirements.txt`
- `ETF_Intelligence_Agent_Master_Populated.xlsx`
- `ETF_Intelligence_Agent_UPDATED.xlsx`
- `ETF_Allocation_Model.xlsx`
- `ETF_Daily_Report.txt`
- `index.html`
- `AUTO_UPDATE_STATUS.json`

## File da non versionare piu'

Questi vengono ignorati dal nuovo `.gitignore`:

- `logs/`
- `BETA_TEST_REPORT.md`
- `BETA_TEST_STATUS.json`
- `streamlit_smoke.log`
- `__pycache__/`

## Dopo l'installazione

1. Fai commit e push.
2. Vai su `Actions`.
3. Lancia manualmente `Beta test ETF Intelligence App` con `run_full_update = false`.
4. Se passa, lancia `Auto update ETF Intelligence App`.
5. Poi rilancia il beta test con `run_full_update = true`.
