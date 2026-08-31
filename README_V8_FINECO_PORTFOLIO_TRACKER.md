# AlphaForge v8 - Fineco Portfolio Tracker

Questa patch sposta la logica da dashboard operativa/trading a controllo portafoglio reale:

1. crea il punto zero dei fondi/PAC Fineco;
2. misura capitale versato, valore attuale e rendimento;
3. distingue core, satelliti, PAC e fondi contenitore;
4. genera domande pratiche da portare al consulente;
5. mantiene la bussola settoriale come secondo livello, non come prima decisione.

## Privacy

Il repository e GitHub Pages possono essere pubblici. Per questo la patch non richiede di pubblicare il portafoglio reale.

Usare la pagina Streamlit `Portafoglio Fineco` per caricare CSV/XLSX in sessione. Pubblicare un file `data/fineco_portfolio_baseline.csv` solo se il repository e' privato o se si accetta che quei dati siano visibili.

## Nuovi file

- `core/fineco_portfolio_tracker.py`
- `generate_fineco_portfolio.py`
- `pages/10_Portafoglio_Fineco.py`
- `pages/11_Tracker_Portafoglio_Fineco.py`
- `data/fineco_portfolio_template_v8.csv`
- `AlphaForge_Fineco_Portfolio.csv`
- `AlphaForge_Fineco_Portfolio.xlsx`
- `AlphaForge_Fineco_Portfolio_Summary.json`
- `AlphaForge_Fineco_Advisor_Questions.csv`

## Campi principali del CSV portafoglio

```text
ISIN
Nome Strumento
Tipo
Ruolo
Settore AlphaForge
Tipo Versamento
Data Inizio
Importo Iniziale EUR
PAC Mensile EUR
Capitale Versato Manuale EUR
Valore Attuale EUR
Quote
Prezzo Medio
Costi Annui % Stimati
Benchmark/Confronto
Prima Rata PAC Conteggiata
Note
```

## Lettura consigliata

Se fondi e PAC sono stati sottoscritti oggi, la performance non va ancora giudicata. Prima serve verificare:

- data valuta;
- quote assegnate;
- prezzo medio;
- prima rata PAC;
- costi totali;
- benchmark di confronto;
- sovrapposizione con All-World/MSCI World/S&P 500.

Primo controllo utile: dopo 1 mese. Prima valutazione seria del rendimento: 6-12 mesi.
