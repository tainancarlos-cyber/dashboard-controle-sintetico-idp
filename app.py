from __future__ import annotations

import streamlit as st


st.set_page_config(
    page_title="Pesquisa IDP | Dashboard",
    layout="wide",
    initial_sidebar_state="expanded",
)

pages = [
    st.Page("pages/00_Metodologia.py", title="Metodologia"),
    st.Page("pages/01_Metodo_Controle_Sintetico.py", title="Metodo de Controle Sintetico"),
    st.Page("pages/02_Resultados_R_Synth.py", title="Resultados Controle Sintetico"),
    st.Page("pages/03_Markov_Switching.py", title="Markov Switching"),
]

navigation = st.navigation(pages)
navigation.run()
