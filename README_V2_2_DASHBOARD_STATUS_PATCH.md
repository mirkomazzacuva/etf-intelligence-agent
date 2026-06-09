# AlphaForge v2.2 - Dashboard Status Patch

Questa patch corregge in modo robusto la pagina pubblica GitHub Pages:

- ripristina `generate_dashboard.py` alla versione AlphaForge v2;
- ripristina `core/report_engine.py` usato dalla dashboard premium;
- aggiorna `auto_update_app.py` per rigenerare `index.html` anche dopo lo status finale `success`.

Risultato atteso: la pagina pubblica deve mostrare `Stato update: success` e mantenere layout AlphaForge v2 con watchlist azioni.
