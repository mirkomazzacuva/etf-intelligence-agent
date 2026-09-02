# AlphaForge v9.1 - Investing-style Fineco Radar

Patch di miglioramento grafico e correzione importi.

## Correzioni principali

- Una tantum corretta: 5 fondi x 5.000 EUR = 25.000 EUR.
- PAC corretti: 2 PAC x 150 EUR/mese = 300 EUR/mese.
- Bollo una tantum: 7 prodotti x 6 EUR = 42 EUR.
- Baseline pubblica aggiunta in `data/fineco_portfolio_baseline.csv`.
- Universo pubblico aggiornato in `data/fineco_funds_public.csv`.

## Grafica

- Home Streamlit rifatta con stile più simile a una dashboard finanziaria/watchlist.
- Dashboard pubblica `index.html` rifatta in stile Investing-like: KPI, watchlist, tabelle, news e grafici.
- Pagina `Grafici fondi Fineco` migliorata con Plotly e grafici singoli.
- Pagina `Notizie fondi Fineco` resa più leggibile.

## Dati e grafici

I fondi comuni non sono strumenti intraday. AlphaForge usa proxy ETF/mercato per grafici quasi real-time e mantiene il NAV/controvalore Fineco come dato ufficiale.

Ogni fondo può avere più ticker proxy alternativi. Il sistema prova il ticker principale e poi i fallback.

## Workflow

Aggiornato `.github/workflows/etf_agent.yml` a:

- `actions/checkout@v7`
- `actions/setup-python@v7`

per ridurre i warning legati a Node.js 20.
