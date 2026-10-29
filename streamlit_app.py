"""AlphaForge v12 interactive home. Older pages remain accessible in sidebar."""
from __future__ import annotations

from datetime import date
from pathlib import Path
import json

import pandas as pd
import streamlit as st

try:
    import plotly.graph_objects as go
except ImportError:
    go = None

from core.fineco_real_engine import build_real_portfolio, OUT_DASH_DATA, ROOT

st.set_page_config(page_title='AlphaForge | Portafoglio Fineco',page_icon='📈',layout='wide',initial_sidebar_state='collapsed')
st.markdown('''<style>
:root{--brand:#156cd3} .block-container{max-width:1400px;padding-top:2rem}
h1{letter-spacing:-.04em}.af-banner{background:#10233e;border-radius:14px;padding:22px 28px;margin-bottom:20px;color:white}
.af-banner h1{margin:2px 0 8px;color:white}.af-banner p{color:#c7d8ec;margin:0}
.af-note{background:#fff8e6;border-left:4px solid #dca63f;padding:12px 18px;border-radius:5px;color:#553d1d}
</style>''',unsafe_allow_html=True)

@st.cache_data(ttl=900,show_spinner=False)
def real_data():
    return build_real_portfolio(allow_network=True,persist=False)

c1,c2=st.columns([5,1])
with c1:
    st.markdown('<div class="af-banner"><small>AlphaForge v12 / FINECO</small><h1>Il mio portafoglio reale</h1><p>Valore di carico, margini e NAV per ISIN. Senza proxy ETF nel rendimento.</p></div>',unsafe_allow_html=True)
with c2:
    st.write('')
    if st.button('🔄 Verifica nuovi NAV',use_container_width=True):
        st.cache_data.clear()
        st.rerun()
try:
    rows, history, summary, statuses=real_data()
except Exception as exc:
    st.error('Recupero NAV non riuscito: %s. Ultima fotografia salvata disponibile.' % str(exc))
    if OUT_DASH_DATA.exists():
        data=json.loads(OUT_DASH_DATA.read_text(encoding='utf-8'))
        rows,history,summary=data['funds'],data['nav_history'],data['summary']
        statuses=[]
    else:
        st.stop()

m1,m2,m3,m4=st.columns(4)
m1.metric('Controvalore Fineco/NAV',f"{summary['market_value_eur']:,.2f} €".replace(',','X').replace('.',',').replace('X','.'))
m2.metric('Costo di carico',f"{summary['cost_basis_eur']:,.2f} €".replace(',','X').replace('.',',').replace('X','.'))
m3.metric('Margine su carico',f"{summary['margin_eur']:+,.2f} €".replace(',','X').replace('.',',').replace('X','.'),f"{summary['margin_pct']:+.2f}%")
m4.metric('PAC mensili previsti','300 €','150 € + 150 €')

if summary['has_latest_nav_after_snapshot']:
    st.info('Almeno un fondo ha un NAV datato successivo alla rilevazione Fineco del 29/10/2026. Controlla la data specifica per ciascuno.')
else:
    st.warning('Valori dalla fotografia Fineco del 29/10/2026. Nessun NAV pubblico successivo verificato: il prezzo NON viene inventato.')
st.markdown('<div class="af-note">Per i PAC, nuove quote sono incluse solo se registrate in <code>data/fineco_transactions_real.csv</code>. Il margine comprende i costi gia inclusi nel carico/NAV ma non la tassazione futura.</div>',unsafe_allow_html=True)

t1,t2,t3,t4=st.tabs(['💼 Portafoglio','📉 Grafici NAV','🧾 Costi e scenari','📋 Dati e fonti'])
with t1:
    df=pd.DataFrame(rows)
    cols=['Nome','Tipo','Costo_carico_EUR','Controvalore_EUR','Margine_EUR','Rendimento_pct','NAV_attuale_EUR','Data_ultimo_dato','Fonte_ultimo_dato']
    st.dataframe(df[[c for c in cols if c in df]],use_container_width=True,hide_index=True)
    st.caption('Margine = valore corrente - costo di carico Fineco. Data della rilevazione e data effettiva NAV possono essere diverse.')
    if go is not None:
        fig=go.Figure(go.Bar(x=df['Nome'],y=df['Margine_EUR'],marker_color=['#14965a' if m>=0 else '#c93745' for m in df['Margine_EUR']]))
        fig.update_layout(height=340,margin=dict(t=12,b=115,l=22,r=18),yaxis_title='Euro',xaxis_title='',template='plotly_white')
        st.plotly_chart(fig,use_container_width=True)
with t2:
    st.subheader('NAV effettivi dei sette fondi')
    funds={r['Nome']:r['ISIN'] for r in rows}
    fund=st.selectbox('Seleziona un fondo',list(funds))
    h=pd.DataFrame([p for p in history if p['ISIN']==funds[fund]])
    if not h.empty:
        h=h.sort_values('Data_NAV')
        h['NAV_EUR']=pd.to_numeric(h['NAV_EUR'],errors='coerce')
        if go is not None:
            figure=go.Figure(go.Scatter(x=h['Data_NAV'],y=h['NAV_EUR'],mode='markers+lines',name='NAV',line=dict(dash='dot' if len(h)<5 else 'solid'),marker=dict(size=9),hovertemplate='%{x}: %{y:.3f} €<extra></extra>'))
            figure.update_layout(height=440,template='plotly_white',margin=dict(t=12,b=30),xaxis_title='Data valore',yaxis_title='NAV in euro')
            st.plotly_chart(figure,use_container_width=True)
        st.dataframe(h[['Data_NAV','NAV_EUR','Fonte','Qualita']],use_container_width=True,hide_index=True)
        if len(h)<20:
            st.warning('Storico incompleto: sono riportate solo osservazioni NAV effettivamente verificabili. La linea puntinata collega osservazioni distanti nel tempo, non implica prezzi intermedi.')
    else:
        st.info('Nessun NAV storico disponibile.')
with t3:
    c=pd.DataFrame(rows)[['Nome','Costo_annuo_pct','Costo_carico_EUR','Margine_EUR']]
    st.dataframe(c,use_container_width=True,hide_index=True)
    st.info('Le proiezioni a 3 mesi e 1 anno da soli due NAV sarebbero poco attendibili. In questa versione sono sospese, anziche produrre numeri da ETF proxy. Verranno aggiunte quando ci sara una serie storica NAV sufficientemente completa e parametri di rischio verificati.')
with t4:
    st.subheader('Controllo delle fonti')
    if statuses:
        st.dataframe(pd.DataFrame(statuses),use_container_width=True,hide_index=True)
    st.write('Rilevazione Fineco iniziale: 29/10/2026; nella schermata non era riportata una data NAV separata.')
    st.write('File sorgente: `data/fineco_official_positions.csv` ; storici: `data/fineco_nav_history_real.csv`; operazioni: `data/fineco_transactions_real.csv`.')
    st.write('Se acquisti nuove quote, devi registrare le quote eseguite effettivamente. Per il conto, Fineco rimane il dato definitivo.')
st.caption('L app verifica i NAV all apertura, con cache di 15 minuti; GitHub Pages invece usa gli aggiornamenti di GitHub Actions. Investimenti soggetti a rischio; nessuna raccomandazione di acquisto o vendita automatica.')
