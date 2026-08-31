# AlphaForge v8.1 Fineco Template Fix

Questa mini-patch corregge il beta tester v8.

## Cosa corregge

Il beta test v8 richiedeva ancora le colonne legacy:

- `Ticker`
- `Valore EUR`

mentre il nuovo tracker Fineco usa correttamente anche:

- `ISIN`
- `Valore Attuale EUR`

La patch rende il controllo compatibile con entrambi gli schemi e aggiorna i template Fineco aggiungendo colonne alias per compatibilita.

## File aggiornati

- `beta_test_app.py`
- `data/fineco_portfolio_template.csv`
- `data/fineco_portfolio_template_v8.csv`

## Installazione

Usa AlphaForge Patch Installer con:

`alpha_forge_v8_1_fineco_template_fix_patch.zip`

Consigliato:

- `run_beta_test = true`
- `run_full_update = false` per un controllo rapido
- `remove_patch_zip = true`

Dopo il verde puoi lanciare il beta test completo se vuoi.
