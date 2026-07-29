from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from glossario_variaveis import glossary_section, help_text, popover


BASE_DIR = Path(__file__).resolve().parents[1]
PRODUCTIVITY_DIR = BASE_DIR / "data" / "Analise_Produtividade_24_TRTs"


def fix_text(value: object) -> object:
    if not isinstance(value, str) or "Ã" not in value:
        return value
    try:
        return value.encode("latin1").decode("utf-8")
    except UnicodeError:
        return value


@st.cache_data
def read_csv(name: str) -> pd.DataFrame:
    df = pd.read_csv(PRODUCTIVITY_DIR / name, sep=";", decimal=",", encoding="utf-8")
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].map(fix_text)
    return df


def format_pct(value: object, digits: int = 2) -> str:
    if pd.isna(value):
        return "n/d"
    return f"{float(value):,.{digits}f}%".replace(",", "X").replace(".", ",").replace("X", ".")


def format_pp(value: object, digits: int = 2) -> str:
    if pd.isna(value):
        return "n/d"
    return f"{float(value):,.{digits}f} p.p.".replace(",", "X").replace(".", ",").replace("X", ".")


def show_image(file_name: str, title: str, caption: str) -> None:
    path = PRODUCTIVITY_DIR / file_name
    st.markdown(f"**{title}**")
    if path.exists():
        st.image(str(path), caption=caption, use_container_width=True)
    else:
        st.warning(f"Arquivo nao encontrado: {path.name}")


variation = read_csv("resumo_variacao_2016_2024.csv")
annual_indices = read_csv("resumo_anual_indices_2016_100.csv")
iad_tcl = read_csv("resumo_anual_iad_tcl.csv")
correlations = read_csv("correlacoes_variacoes_anuais.csv")

st.title("Produtividade e escala operacional dos 24 TRTs")
st.caption(
    "Analise descritiva complementar, 2010-2024. Indicadores indexados em 2016 = 100, "
    "com IAD e TCL mantidos em valores percentuais."
)

st.markdown(
    """
    Esta seção verifica se a trajetória das despesas dos Tribunais Regionais do Trabalho poderia estar
    associada a mudanças de escala, demanda ou produtividade. O painel cobre os 24 TRTs entre 2010 e
    2024, totalizando 360 observações tribunal-ano. Para evitar que tribunais maiores dominem os
    resultados agregados, os indicadores foram normalizados pelo valor de cada TRT em 2016.
    """
)

cards = st.columns(4)
dpj = variation[variation["indicador"].str.contains("Despesa total", case=False, na=False)].iloc[0]
ftt = variation[variation["indicador"].str.contains("Força de trabalho", case=False, na=False)].iloc[0]
baixados = variation[variation["indicador"].str.contains("Processos baixados", case=False, na=False)].iloc[0]
tcl_2016 = iad_tcl[(iad_tcl["ano"].eq(2016)) & (iad_tcl["indicador_raw"].eq("tcl_pct"))].iloc[0]
tcl_2024 = iad_tcl[(iad_tcl["ano"].eq(2024)) & (iad_tcl["indicador_raw"].eq("tcl_pct"))].iloc[0]

cards[0].metric("Despesa real - DPJ", format_pct(dpj["variacao_media_pct"]), help=help_text("DPJ"))
cards[1].metric("Força de trabalho - FTT", format_pct(ftt["variacao_media_pct"]), help=help_text("FTT"))
cards[2].metric("Processos baixados - TBaix", format_pct(baixados["variacao_media_pct"]), help=help_text("TBaix"))
cards[3].metric("TCL média", f"{format_pct(tcl_2016['media_pct'])} -> {format_pct(tcl_2024['media_pct'])}", help=help_text("TCL"))

st.info(
    "A despesa real cresceu entre 2016 e 2024, mas isso não contradiz o Controle Sintético: "
    "o método compara a trajetória observada com a trajetória contrafactual estimada, não testa "
    "queda absoluta da despesa."
)

with st.container():
    pcols = st.columns(6)
    with pcols[0]:
        popover("DPJ")
    with pcols[1]:
        popover("FTT")
    with pcols[2]:
        popover("TBaix")
    with pcols[3]:
        popover("IPM")
    with pcols[4]:
        popover("IPSJud")
    with pcols[5]:
        popover("TCL")

tab_summary, tab_figures, tab_tables, tab_limits = st.tabs(
    ["Leitura sintética", "Gráficos", "Tabelas", "Limites"]
)

with tab_summary:
    st.subheader("Achados centrais")
    st.markdown(
        """
        Entre 2016 e 2024, a despesa total real média dos TRTs aumentou 51,93%, enquanto a força de
        trabalho total ficou praticamente estável, com variação média de -0,81%. No mesmo período, os
        processos baixados cresceram 13,51%, os casos pendentes recuaram 15,64% e os indicadores de
        produtividade também avançaram: 23,43% para servidores da área judiciária e 16,09% para
        magistrados.

        A leitura conjunta é que a trajetória orçamentária estimada nos modelos anteriores não parece
        decorrer de queda generalizada de atividade jurisdicional, redução da força de trabalho ou
        deterioração de produtividade. Os TRTs mantiveram ou ampliaram sua capacidade de entrega mesmo
        com trajetória de despesa inferior ao contrafactual estimado pelo Controle Sintético.
        """
    )

    st.subheader("Desempenho operacional")
    st.markdown(
        """
        O Índice de Atendimento à Demanda aumentou 6,38 pontos percentuais entre 2016 e 2024, e a Taxa
        de Congestionamento Líquida caiu 15,78 pontos percentuais. A queda da TCL ocorreu nos 24 TRTs,
        sugerindo melhora disseminada do estoque relativo de processos. Houve ruptura temporária em
        2020 e 2021, mas a recuperação de 2023 e 2024 ocorreu sem expansão correspondente da força de
        trabalho.
        """
    )

    st.subheader("Intensidade de gasto")
    st.markdown(
        """
        Os indicadores de gasto por unidade cresceram de forma expressiva: a despesa por processo baixado
        subiu 38,27% e a despesa por integrante da força de trabalho aumentou 53,62%. Esse resultado não
        deve ser lido automaticamente como perda de eficiência, pois a despesa do Judiciário contém
        componentes rígidos e não varia proporcionalmente ao volume anual de processos baixados.
        """
    )

with tab_figures:
    st.markdown("**Fórmulas dos indicadores exibidos nos gráficos**")
    fcols = st.columns(5)
    with fcols[0]:
        popover("IAD")
    with fcols[1]:
        popover("TCL")
    with fcols[2]:
        popover("KS")
    with fcols[3]:
        popover("K")
    with fcols[4]:
        popover("IPM")

    show_image(
        "01_escala_despesa_atividade.png",
        "Escala, despesa e atividade jurisdicional",
        "Média dos índices dos 24 TRTs, com 2016 = 100.",
    )
    show_image(
        "02_produtividade_carga.png",
        "Produtividade e carga de trabalho",
        "IPSMJud, IPM, KS e K em trajetórias indexadas.",
    )
    show_image(
        "03_iad_tcl_percentuais.png",
        "IAD e TCL em valores percentuais",
        "Indicadores mantidos em percentuais, sem indexação.",
    )
    show_image(
        "04_intensidade_gasto.png",
        "Intensidade de gasto",
        "Despesa por processo baixado e por integrante da força de trabalho.",
    )
    show_image(
        "05_trajetorias_individuais.png",
        "Trajetórias individuais dos 24 TRTs",
        "Distribuição das trajetórias por tribunal para os principais indicadores.",
    )

with tab_tables:
    st.subheader("Variação média dos indicadores entre 2016 e 2024")
    display_variation = variation.copy()
    display_variation["variacao_media"] = display_variation["variacao_media_pct"].map(format_pct)
    display_variation["mediana"] = display_variation["variacao_mediana_pct"].map(format_pct)
    display_variation["intervalo_interquartil"] = display_variation.apply(
        lambda row: f"{format_pct(row['p25_variacao_pct'])} a {format_pct(row['p75_variacao_pct'])}",
        axis=1,
    )
    st.dataframe(
        display_variation[
            ["dimensao", "indicador", "n_trts", "variacao_media", "mediana", "intervalo_interquartil"]
        ],
        use_container_width=True,
        hide_index=True,
        column_config={
            "indicador": st.column_config.TextColumn(
                "Indicador",
                help="Passe o mouse sobre os botões de glossário acima ou consulte o glossário ao final para ver fórmulas e decomposição.",
            ),
            "n_trts": st.column_config.NumberColumn("TRTs", help="Número de tribunais regionais considerados."),
        },
    )

    st.subheader("Trajetórias anuais indexadas")
    selected_dimension = st.selectbox(
        "Dimensão",
        annual_indices["dimensao"].drop_duplicates().tolist(),
    )
    selected = annual_indices[annual_indices["dimensao"].eq(selected_dimension)].copy()
    fig = px.line(
        selected,
        x="ano",
        y="media_indice",
        color="indicador",
        markers=True,
        labels={"ano": "Ano", "media_indice": "Índice médio, 2016 = 100", "indicador": "Indicador"},
    )
    fig.add_hline(y=100, line_dash="dot", line_color="#64748b")
    fig.add_vline(x=2017, line_dash="dash", line_color="#334155")
    fig.add_vline(x=2023, line_dash="dot", line_color="#64748b")
    fig.update_layout(height=520, legend_title=None)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Correlação de Spearman com a variação anual da despesa")
    corr_plot = correlations.sort_values("correlacao_spearman")
    fig_corr = px.bar(
        corr_plot,
        x="correlacao_spearman",
        y="variavel",
        orientation="h",
        labels={"correlacao_spearman": "Correlação de Spearman", "variavel": "Indicador"},
    )
    fig_corr.add_vline(x=0, line_dash="dash", line_color="#334155")
    fig_corr.update_layout(height=430)
    st.plotly_chart(fig_corr, use_container_width=True)
    st.dataframe(correlations, use_container_width=True, hide_index=True)

    st.download_button(
        "Baixar variações 2016-2024",
        data=variation.to_csv(index=False, sep=";").encode("utf-8-sig"),
        file_name="resumo_variacao_produtividade_24_trts.csv",
        mime="text/csv",
    )

with tab_limits:
    st.subheader("Como interpretar")
    st.markdown(
        """
        A análise é complementar e descritiva. Ela não estabelece relação causal entre produtividade e
        despesa, e as correlações anuais não controlam fatores institucionais, tecnológicos ou
        macroeconômicos. A normalização em 2016 reduz diferenças de porte, mas torna os resultados
        sensíveis às condições específicas daquele exercício.

        Também é preciso cautela com 2020 e 2021, quando a pandemia produziu ruptura relevante nas
        séries de atividade jurisdicional. Ainda assim, a consistência entre crescimento dos processos
        baixados, aumento do IAD, queda da TCL e avanço dos índices de produtividade reduz a plausibilidade
        de que os resultados orçamentários observados tenham sido determinados por queda generalizada da
        produtividade dos TRTs.
        """
    )
    st.info(f"Arquivos carregados de: {PRODUCTIVITY_DIR}")

glossary_section(
    ["DPJ", "ODCK", "DRH", "DPE", "DK", "FTT", "TPEfet", "TBaix", "Cn", "Cp", "IAD", "TCL", "IPM", "IPSJud", "KS", "K"],
    "Glossário e fórmulas dos indicadores de produtividade",
)
