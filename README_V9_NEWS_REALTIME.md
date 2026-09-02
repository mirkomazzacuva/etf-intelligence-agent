# AlphaForge v9 - News & Performance Radar

Questa patch aggiunge una sezione più utile per il caso reale Fineco:

- portafoglio fondi/PAC pubblicabile nel repo;
- news radar per i settori collegati ai fondi;
- bias prudente di breve periodo: favorevole / neutro / attenzione;
- grafici proxy quasi real-time dove esiste un ticker ETF/mercato disponibile;
- output CSV/XLSX per performance, storico proxy e notizie;
- dashboard pubblica aggiornata a v9;
- pagine Streamlit dedicate a notizie e grafici.

## Limiti importanti

I fondi comuni non sono strumenti intraday: il NAV viene calcolato normalmente una volta al giorno. Per questo AlphaForge usa:

1. il valore ufficiale Fineco/NAV quando caricato manualmente;
2. ETF proxy di mercato per leggere l'andamento quasi real-time;
3. news pubbliche per capire cosa monitorare nei giorni successivi.

Il bias non è una previsione e non è una raccomandazione di acquisto o vendita.

## Output nuovi

- `AlphaForge_Fund_Performance.csv/xlsx`
- `AlphaForge_Fund_Price_History.csv/xlsx`
- `AlphaForge_News_Radar.csv/xlsx`
- `AlphaForge_News_Radar_Summary.json`
- `data/fineco_funds_public.csv`

## Pagine Streamlit nuove

- `Notizie fondi Fineco`
- `Grafici fondi Fineco`
