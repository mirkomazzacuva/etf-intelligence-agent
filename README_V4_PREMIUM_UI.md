# AlphaForge v4 Premium UI Patch

Questa patch migliora l'estetica e la leggibilità di AlphaForge senza cambiare la logica finanziaria principale.

## Novità principali

- Dashboard pubblica GitHub Pages ridisegnata in stile premium dark/glass.
- Badge colorati per stato update, entry zone, risk flag e azione suggerita.
- Barre visive per Score Finale e Priority Score.
- Layout più mobile-friendly e più leggibile su tabelle larghe.
- Streamlit app aggiornata con tema coerente, hero premium, metric card e tabelle più leggibili.
- Pagine Streamlit migliorate: Ranking ETF, Analizza Strumento, Confronta, Watchlist, AI Assistant e Priorità Operative.
- Nuovo modulo `core/ui_theme.py` per centralizzare lo stile.
- Beta tester aggiornato con controllo non bloccante della dashboard v4.

## Installazione

Caricare lo zip nella root del repository e lanciare:

```text
Actions -> AlphaForge Patch Installer -> Run workflow
```

Campi consigliati:

```text
patch_zip = alpha_forge_v4_premium_ui_patch.zip
run_beta_test = true
run_full_update = true
remove_patch_zip = true
```

## Dopo l'installazione

Controllare:

```text
https://mirkomazzacuva.github.io/etf-intelligence-agent/
```

La dashboard deve mostrare:

```text
AlphaForge v4 Premium UI
```

## Nota

Questa patch migliora la user experience. Gli score restano informativi e non costituiscono consulenza finanziaria personalizzata.
