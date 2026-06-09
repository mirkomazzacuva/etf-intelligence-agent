# AlphaForge v2.1 - Status dashboard fix

Questa patch corregge un dettaglio della dashboard pubblica: `index.html` poteva mostrare `running` anche dopo un update riuscito, perché la dashboard veniva generata prima della scrittura dello stato finale `success`.

## File aggiornati

- `auto_update_app.py`

## Cosa cambia

- Gli script dati girano prima.
- `AUTO_UPDATE_STATUS.json` viene portato a `success` prima di generare la dashboard pubblica.
- `generate_dashboard.py` genera quindi `index.html` leggendo già lo stato corretto.
- Lo stato finale resta `success` dopo la generazione dashboard.
