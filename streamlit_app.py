import pandas as pd
import streamlit as st
import plotly.express as px

RANKING_FILE = "ETF_Intelligence_Agent_UPDATED.xlsx"
ALLOCATION_FILE = "ETF_Allocation_Model.xlsx"

st.set_page_config(
    page_title="ETF Intelligence App",
    page_icon="📈",
    layout="wide"
)

st.title("📈 ETF Intelligence App")
st.caption("Ranking ETF, allocazione Fineco e analisi rischio. Report informativo, non consulenza finanziaria personalizzata.")

@st.cache_data
def load_data():
    ranking = pd.read_excel(RANKING_FILE)
    allocation = pd.read_excel(ALLOCATION_FILE, sheet_name="Suggested_Allocation")
    summary = pd.read_excel(ALLOCATION_FILE, sheet_name="Summary")
    return ranking, allocation, summary

ranking, allocation, summary = load_data()

ranking = ranking.sort_values("Score Finale", ascending=False, na_position="last")

def get_summary_value(key):
    row = summary[summary["Parametro"] == key]
    if len(row) == 0:
        return ""
    return row.iloc[0]["Valore"]

market_regime = get_summary_value("Market Regime")

st.sidebar.header("Impostazioni")

amount = st.sidebar.number_input(
    "Importo da investire (€)",
    min_value=100,
    max_value=100000,
    value=1000,
    step=100
)

risk_profile = st.sidebar.selectbox(
    "Profilo rischio",
    ["Prudente", "Bilanciato", "Aggressivo"],
    index=1
)

category_filter = st.sidebar.multiselect(
    "Categorie da mostrare",
    options=sorted(ranking["Categoria"].dropna().unique()),
    default=sorted(ranking["Categoria"].dropna().unique())
)

filtered = ranking[ranking["Categoria"].isin(category_filter)]

best = ranking.iloc[0]

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Market Regime", market_regime)

with col2:
    st.metric("Miglior ETF", best["Ticker"])

with col3:
    st.metric("Score migliore", best["Score Finale"])

st.divider()

st.subheader("💼 Allocazione suggerita")

alloc = allocation.copy()

if risk_profile == "Prudente":
    defensive_boost = 1.25
    thematic_cut = 0.60
elif risk_profile == "Aggressivo":
    defensive_boost = 0.60
    thematic_cut = 1.40
else:
    defensive_boost = 1.00
    thematic_cut = 1.00

def adjust_weight(row):
    category = str(row["Categoria"]).lower()
    weight = row["Peso Target %"]

    if category == "defensive":
        return weight * defensive_boost
    if category == "thematic":
        return weight * thematic_cut
    return weight

alloc["Peso App %"] = alloc.apply(adjust_weight, axis=1)
alloc["Peso App %"] = alloc["Peso App %"] / alloc["Peso App %"].sum() * 100
alloc["Peso App %"] = alloc["Peso App %"].round(2)
alloc["Importo €"] = (amount * alloc["Peso App %"] / 100).round(2)

st.write(
    f"Profilo selezionato: **{risk_profile}** — importo simulato: **{amount:,.0f} €**"
    .replace(",", ".")
)

st.dataframe(
    alloc[[
        "Ticker",
        "Nome ETF",
        "Categoria",
        "Tema/Area",
        "Peso App %",
        "Importo €",
        "Score Finale",
        "Note AI"
    ]],
    use_container_width=True,
    hide_index=True
)

fig_alloc = px.pie(
    alloc,
    names="Ticker",
    values="Peso App %",
    title="Distribuzione allocazione suggerita"
)

st.plotly_chart(fig_alloc, use_container_width=True)

st.divider()

st.subheader("🏆 Ranking ETF")

st.dataframe(
    filtered[[
        "Ticker",
        "Nome ETF",
        "Categoria",
        "Tema/Area",
        "Score Finale",
        "Stato",
        "Rendimento 12M %",
        "Volatilità %",
        "Max Drawdown %",
        "Sharpe",
        "Note AI"
    ]],
    use_container_width=True,
    hide_index=True
)

st.divider()

st.subheader("📊 Score vs Volatilità")

fig = px.scatter(
    filtered,
    x="Volatilità %",
    y="Score Finale",
    color="Categoria",
    size="Rendimento 12M %",
    hover_name="Ticker",
    hover_data=["Nome ETF", "Tema/Area", "Max Drawdown %"],
    title="Score finale rispetto alla volatilità"
)

st.plotly_chart(fig, use_container_width=True)

st.divider()

st.subheader("🧠 Lettura prudente")

st.markdown("""
- Gli ETF con score alto non sono acquisti automatici.
- Gli ETF core globali sono più adatti come base di lungo periodo.
- Gli ETF tematici vanno usati come satellite.
- Oro e difensivi aiutano a bilanciare rischio macro/geopolitico.
- Prima di investire su Fineco, verifica sempre costi, disponibilità, spread e coerenza con il tuo profilo di rischio.
""")
