# AlphaForge v12 - Fineco Real NAV Portfolio

## Cosa cambia

Questa versione risolve il problema piu serio di AlphaForge: il margine dei fondi comuni non puo essere calcolato usando ETF proxy. La home pubblica usa soltanto i 7 ISIN con i valori reali letti nella schermata Fineco, e solo NAV verificati per gli aggiornamenti futuri.

**Fotografia Fineco comunicata il 29/10/2026** (data del NAV separata non visualizzata):

| Voce | Euro |
|---|---:|
| Controvalore totale | 25.735,13 |
| Costo di carico totale Fineco | 25.646,20 |
| Margine su carico | +88,93 (+0,35%) |
| Versamenti iniziali programmati e confermati dalla schermata | 25.600,00 |
| Differenza fra carico e versamenti, non classificata senza eseguiti | 46,20 |
| PAC futuri programmati | 150 + 150 = 300 al mese |

Il margine e calcolato prima delle eventuali imposte di vendita. I costi di gestione sono gia nel NAV: NON vengono sottratti una seconda volta. Le quote mostrate nella schermata Fineco sono arrotondate; la base utilizza i controvalori e i margini esatti comunicati dalla banca.

## Come installare (senza software sul PC)

1. Scaricare **alpha_forge_v12_fineco_real_patch.zip** da ChatGPT, senza estrarlo.
2. Aprire `https://github.com/mirkomazzacuva/etf-intelligence-agent/upload/main` e caricare lo zip nella directory principale del repository. Fare **Commit changes**.
3. Aprire **Actions > AlphaForge Patch Installer > Run workflow**.
4. In **patch_zip** mettere esattamente `alpha_forge_v12_fineco_real_patch.zip`.
5. Impostare **run_full_update = true**, **run_beta_test = true**, **remove_patch_zip = true**, poi lanciare.
6. Dopo il verde, aprire `https://mirkomazzacuva.github.io/etf-intelligence-agent/?v=12` e forzare il refresh (`Ctrl+F5`). La nuova home deve mostrare **25.735,13 EUR** e **+88,93 EUR** se le fonti non dispongono ancora di NAV piu recenti.
7. Se la fonte ha un NAV datato dopo la rilevazione, i dati possono cambiare automaticamente. **Controllare le date per ciascuno dei sette fondi**.

NON eseguire Clean up prima che il Patch Installer abbia terminato. Nel workflow di pulizia lasciare vuoto il campo patch_zip; la patch non deve essere rimossa prima dell'installazione.

## File nuovi

- `data/fineco_official_positions.csv`: le 7 posizioni Fineco reali, quote, prezzo medio, NAV mostrato, margine, data di rilevazione e PAC.
- `data/fineco_nav_history_real.csv`: storico NAV confermato per ISIN. Comprende osservazioni pubbliche di settembre e la rilevazione Fineco di ottobre, **non** quote inventate nei giorni intermedi.
- `data/fineco_nav_manual_real.csv`: eventuali nuovi NAV verificati inseribili manualmente.
- `data/fineco_transactions_real.csv`: **solo eseguiti successivi al 29/10/2026**, con quote e costo di carico. Lasciarlo con la sola intestazione finche non ci sono nuove operazioni confermate.
- `AlphaForge_Real_Portfolio.csv`, `AlphaForge_Real_NAV_History.csv`, `AlphaForge_Real_Summary.json`, `AlphaForge_Real_Dashboard_Data.json`, `AlphaForge_Real_Source_Status.csv`: dati generati automaticamente e controllo delle fonti.
- `generate_real_portfolio.py`, `core/fineco_real_engine.py`, `core/fineco_nav_sources.py`, `core/fineco_real_ui.py`: motore e interfaccia.
- `legacy_alpha_forge.html`: strumenti storici della dashboard precedente separati dai margini Fineco reali.

## Aggiornamenti NAV

Il workflow `Auto update ETF Intelligence App` legge i NAV dai siti Fineco Asset Management (6 fondi) e Borsa Italiana (Fidelity). L'aggiornamento avviene solo se la pagina offre un **ISIN verificabile, prezzo e data NAV**; una fonte bloccata, non aggiornata o non interpretabile non modifica il valore Fineco.

Le quotazioni dei fondi comuni vengono pubblicate generalmente una volta al giorno. **GitHub Pages e una pagina statica**: aprirla non obbliga i siti dei fondi a fornire un NAV nuovo. Per un refresh su richiesta aprire la versione Streamlit o lanciare l'azione **Auto update ETF Intelligence App**; i prezzi restano fermi finche le fonti non pubblicano NAV piu recenti.

Il controllo delle fonti puo non riuscire per protezioni dei siti o cambiamenti nel loro HTML. In tale caso l'app mostra il dato precedente e la sua data, **mai un NAV sintetico o un ETF proxy chiamato valore reale**.

## PAC: istruzioni dopo la prima fotografia

I due PAC sono di **150 EUR/mese ciascuno**. L'app non aggiunge automaticamente le rate programmate perche potrebbero non essere state eseguite.

Quando Fineco conferma una nuova rata, aggiungere una riga a `data/fineco_transactions_real.csv`:

```
ISIN,Data,Tipo,Quote,Costo_carico_EUR,Note
IE0003YRHWF4,2026-11-05,ACQUISTO,1.031234,156.00,Rata eseguita Fineco; esempio da sostituire
```

L'esempio non e un movimento reale: NON importarlo direttamente. Le nuove quote devono avere la precisione effettiva dell'eseguito, non la quantita arrotondata del riepilogo. Per vendite o rimborsi, creare una nuova fotografia ufficiale delle posizioni con i carichi ricalcolati: la v12 non tenta di ricostruire rimborsi da informazioni incomplete.

## Cosa e rimasto sospeso e perche

- **Previsioni automatiche 3 mesi/1 anno**: due osservazioni per ISIN non permettono di stimare volatilita e distribuzione dei rendimenti in modo affidabile; non viene usato momentum di un ETF come previsione del fondo.
- **Consigli automatici "tieni/vendi"**: senza benchmark e serie NAV sufficienti non vanno presentati come raccomandazioni operative.
- **Grafici**: sono presenti per tutti e sette i fondi, con due osservazioni storiche certe per ciascuno. I nuovi punti si accumulano soltanto dopo acquisizione di NAV datati reali.

## Test e sicurezza

Sono inclusi test automatici che verificano la quadratura dei valori Fineco, l'identificazione degli ISIN e il rifiuto di NAV pubblici piu vecchi della rilevazione. I valori del portafoglio sono in un repository **pubblico**, come autorizzato dall'utente. Nessuna credenziale o dato bancario riservato e incluso nello zip.
