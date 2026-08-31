# AlphaForge v8.3 - Fineco Normalize Fix

Corregge il crash del tracker Fineco quando il template contiene sia `ISIN` sia `Ticker` oppure sia `Valore Attuale EUR` sia `Valore EUR`.

## Fix principali

- `core/fineco_portfolio_tracker.py` ora coalesca colonne duplicate create dagli alias legacy.
- Il parser numerico gestisce valori in formato italiano/europeo e anglosassone.
- Il tracker Fineco continua a supportare template nuovi e vecchi.

## Installazione

Usare AlphaForge Patch Installer con:

```text
patch_zip = alpha_forge_v8_3_fineco_normalize_fix_patch.zip
run_beta_test = true
run_full_update = true
remove_patch_zip = true
```
