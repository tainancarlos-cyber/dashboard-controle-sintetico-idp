from __future__ import annotations

import streamlit as st

from r_synth_exports import COMPARABILITY_DIR, comparability_image, load_exports


st.set_page_config(page_title="Metodo | Controle Sintetico", layout="wide")


@st.cache_data
def get_data():
    return load_exports()


data = get_data()

st.title("Metodo de Controle Sintetico")
st.caption("Especificacao principal: TRT medio sem TST")

st.subheader("Da rodada exploratoria ao TRT medio")
st.markdown(
    """
    A primeira aplicacao do Controle Sintetico utilizou o **TST** como unidade tratada e TJMG,
    TJRJ e TJSP como doadores. Essa etapa fica como teste inicial de viabilidade metodologica.

    Em seguida, foi testada uma especificacao com os TRTs agregados por soma. Embora essa abordagem
    representasse o orcamento total dos TRTs, ela gerou problema de escala e reduziu a diversidade da
    unidade sintetica em alguns modelos.

    A especificacao principal passou, portanto, a utilizar o **TRT medio sem TST**, construido pela
    media anual dos 24 Tribunais Regionais do Trabalho. Essa escolha representa a trajetoria tipica de
    um tribunal regional, melhora a comparabilidade com TJs estaduais e preserva a exclusao do TST,
    cuja estrutura institucional e orcamentaria e distinta.
    """
)

cards = st.columns(4)
cards[0].metric("Unidade tratada", "TRT_MEDIO")
cards[1].metric("TST", "Excluido")
cards[2].metric("TJs candidatos", data["base_wide"][data["base_wide"]["sigla"].str.startswith("TJ")]["sigla"].nunique())
cards[3].metric("Doadores efetivos", int(data["summary"]["n_doadores"].max()))

st.subheader("Grupo de doadores")
all_tjs = (
    data["base_wide"][data["base_wide"]["sigla"].str.startswith("TJ")][["sigla"]]
    .drop_duplicates()
    .sort_values("sigla")
)
cols = st.columns(2)
with cols[0]:
    st.markdown("**Todos os TJs estaduais na base candidata**")
    st.dataframe(all_tjs, use_container_width=True, hide_index=True)
with cols[1]:
    st.markdown("**TJs selecionados por porte no script R**")
    st.dataframe(data["donors"], use_container_width=True, hide_index=True)

st.subheader("Comparabilidade dos TRTs")
st.markdown(
    """
    A escolha do TRT medio foi precedida de uma analise de comparabilidade. As series dos TRTs foram
    indexadas com base 2016 = 100 para remover diferencas de escala. Os resultados mostram forte
    homogeneidade para `dpj`, `dpe` e `drh`, enquanto `odck` e `dk` sao mais volateis e devem ser
    interpretadas com cautela.
    """
)

if "comparability_evidence" in data:
    st.dataframe(data["comparability_evidence"], use_container_width=True, hide_index=True)

for file_name, title in [
    ("01_trajetorias_indexadas_trts_2016_100.png", "Trajetorias indexadas dos TRTs"),
    ("02_faixa_dispersao_trt_medio.png", "Faixa de dispersao do TRT medio"),
    ("03_coeficiente_variacao_trts.png", "Coeficiente de variacao"),
    ("04_percentual_trts_proximos_media.png", "Percentual de TRTs proximos da media"),
    ("05_matriz_correlacao_crescimento_trts.png", "Correlacao de crescimento entre TRTs"),
]:
    path = comparability_image(file_name)
    if path.exists():
        st.markdown(f"**{title}**")
        st.image(str(path), use_container_width=True)

st.info(f"Graficos e tabelas de comparabilidade carregados de: {COMPARABILITY_DIR}")

st.subheader("Estrategia empirica")
st.markdown(
    """
    A intervencao e definida em 2017, primeiro ano de vigencia orcamentaria da EC 95/2016.
    O periodo pre-intervencao e 2010-2016, e o periodo pos-intervencao e 2017-2024.

    Para cada modelo, o pacote `Synth` estima uma combinacao ponderada de TJs doadores capaz de
    reproduzir a trajetoria pre-intervencao do `TRT_MEDIO`. O efeito estimado e o gap:

    `gap = observado - sintetico`

    A linha de 2023 nos graficos e mantida como marco complementar associado ao novo arcabouco fiscal.
    """
)
