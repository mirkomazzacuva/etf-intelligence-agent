# AlphaForge v3 Intelligence Patch

Questa patch porta AlphaForge da dashboard ETF/azioni v2 a piattaforma più pratica di intelligence:

- Priority Score per ordinare ETF e azioni da monitorare.
- Entry Zone per capire se il prezzo è costruttivo, esteso o da attendere.
- Risk Flag per segnalare volatilità/drawdown elevati.
- Supporti/resistenze 20D e 60D.
- Scenari base, positivo e negativo per ogni strumento.
- Nuova pagina Streamlit `Priorità Operative`.
- AI Assistant più guidato e prudente.
- Dashboard pubblica GitHub Pages aggiornata ad AlphaForge v3.
- Nuovi output `AlphaForge_Insights.csv` e `AlphaForge_Insights.xlsx`.

## Installazione

Caricare lo zip nella root del repository e lanciare:

```text
Actions -> AlphaForge Patch Installer -> Run workflow
```

Campi consigliati:

```text
patch_zip = alpha_forge_v3_intelligence_patch.zip
run_beta_test = true
run_full_update = true
remove_patch_zip = true
```

## Dopo l'installazione

Controllare:

```text
Actions -> Beta test ETF Intelligence App
Actions -> Auto update ETF Intelligence App
https://mirkomazzacuva.github.io/etf-intelligence-agent/
```

La dashboard pubblica deve mostrare `AlphaForge v3` e la sezione `Priorità operative AlphaForge`.

## Nota

Gli score sono informativi e non costituiscono consulenza finanziaria personalizzata o ordine di acquisto/vendita.
