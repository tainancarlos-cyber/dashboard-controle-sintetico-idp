import streamlit as st
from article_ui import setup

st.set_page_config(page_title="Dissertação IDP | Orçamento dos TRTs", layout="wide")
setup()
navigation = st.navigation([
    st.Page("pages/00_Metodologia.py", title="Pesquisa e dados"),
    st.Page("pages/01_Metodo_Controle_Sintetico.py", title="Controle sintético · aplicação"),
    st.Page("pages/03_Resultados_R_Synth.py", title="Resultados · Gráficos 1 a 8"),
    st.Page("pages/05_Placebos.py", title="Placebos · Controle sintético"),
    st.Page("pages/04_Markov_Switching.py", title="Markov Switching"),
    st.Page("pages/02_Analise_Produtividade_Escala.py", title="Produtividade e escala"),
])
navigation.run()
