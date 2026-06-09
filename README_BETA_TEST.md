# Beta tester automatico ETF Intelligence App

Questa patch aggiunge un workflow GitHub Actions separato dall'aggiornamento automatico dei dati.

File aggiunti:

- `beta_test_app.py`
- `.github/workflows/beta_test_app.yml`
- `README_BETA_TEST.md`

## Cosa controlla

Il beta tester verifica:

1. presenza dei file sorgente principali;
2. presenza del file master Excel necessario all'aggiornamento;
3. sintassi di tutti i file Python;
4. import delle dipendenze principali;
5. leggibilita' degli Excel generati, quando presenti;
6. stato dell'ultimo aggiornamento automatico, quando presente;
7. avvio minimo della app Streamlit tramite health check.

## Quando parte

Parte automaticamente:

- a ogni push su `main`;
- a ogni pull request verso `main`;
- ogni giorno feriale alle 06:15 UTC;
- manualmente da GitHub Actions.

## Come lanciarlo manualmente

Da GitHub:

1. vai su `Actions`;
2. apri `Beta test ETF Intelligence App`;
3. clicca `Run workflow`;
4. lascia `run_full_update = false` per il test rapido;
5. scegli `run_full_update = true` solo se vuoi provare anche tutto il ciclo di aggiornamento dati.

## Differenza tra test rapido e test completo

Il test rapido non modifica i dati e serve a controllare che la app sia integra.

Il test completo esegue anche:

```bash
python auto_update_app.py
```

Quindi scarica dati, rigenera Excel, report e dashboard. Usalo manualmente quando vuoi validare davvero tutta la catena.

## Dove leggere il risultato

Al termine del workflow, GitHub Actions salva un artifact chiamato:

```text
beta-test-report
```

Dentro trovi:

- `BETA_TEST_REPORT.md`
- `BETA_TEST_STATUS.json`
- `streamlit_smoke.log`



## Aggiornamento v2

Questa versione rende il controllo dell'Excel di allocazione piu' robusto: accetta sia `Importo Indicativo EUR` sia `Importo su 1000 EUR`, perche' alcune versioni dell'allocation engine usano il secondo nome.

Il workflow inoltre esegue una sola modalita' per volta: test rapido oppure test completo, evitando il doppio run quando scegli `run_full_update = true`.
