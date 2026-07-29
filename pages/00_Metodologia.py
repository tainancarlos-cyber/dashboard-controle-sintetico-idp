from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from r_synth_exports import (
    COMPARABILITY_DIR,
    EXPORT_DIR,
    OUTCOME_LABELS,
    comparability_image,
    format_number,
    load_exports,
    model_label,
    model_options,
)


st.markdown(
    """
    <style>
    .block-container {padding-top: 1.4rem; padding-bottom: 2rem;}
    div[data-testid="stMetric"] {
        background: #f8fafc;
        border: 1px solid #d9e2ec;
        border-radius: 8px;
        padding: 14px 16px;
    }
    div[data-testid="stMetricLabel"] p {font-size: 0.9rem;}
    div[data-testid="stMetricValue"] {font-size: 1.55rem;}
    .hero {
        border: 1px solid #d8dee9;
        border-radius: 8px;
        padding: 18px 20px;
        background: linear-gradient(180deg, #ffffff 0%, #f7f9fb 100%);
        margin-bottom: 14px;
    }
    .hero h1 {font-size: 2rem; margin: 0 0 0.35rem 0;}
    .hero p {margin: 0; color: #46515f;}
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data
def get_data() -> dict[str, pd.DataFrame]:
    return load_exports()


def add_model_text(df: pd.DataFrame, model_dict: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["modelo_label"] = out["modelo"].map(lambda model: model_label(model, model_dict))
    return out


def selected_series(series: pd.DataFrame, model: str) -> pd.DataFrame:
    return series[series["modelo"].eq(model)].sort_values("ano")


def trajectory_chart(df: pd.DataFrame, title: str, y_label: str) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["ano"],
            y=df["observado"],
            mode="lines+markers",
            name="Observado",
            line={"width": 3, "color": "#2563eb"},
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df["ano"],
            y=df["sintetico"],
            mode="lines+markers",
            name="Sintetico",
            line={"width": 3, "dash": "dash", "color": "#dc2626"},
        )
    )
    fig.add_vline(x=2017, line_dash="dash", line_color="#334155")
    fig.add_vline(x=2023, line_dash="dot", line_color="#64748b")
    fig.update_layout(
        title=title,
        xaxis_title="Ano",
        yaxis_title=y_label,
        height=470,
        legend_title=None,
        margin={"l": 20, "r": 20, "t": 55, "b": 20},
    )
    return fig


data = get_data()
models = model_options(data["model_dict"])
summary = add_model_text(data["summary"], data["model_dict"])
series = add_model_text(data["series"], data["model_dict"])
unit_weights = add_model_text(data["unit_weights"], data["model_dict"])
pre_means_long = add_model_text(data["pre_means_long"], data["model_dict"])

st.markdown(
    """
    <div class="hero">
      <h1>Controle Sintetico - TRT medio sem TST</h1>
      <p>Resultados gerados no R com Synth/SCtools, apresentados em graficos interativos para a pesquisa IDP.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

top = st.columns([1.1, 1, 1, 1])
top[0].metric("Modelos estimados", len(models))
top[1].metric("Unidade tratada", "TRT_MEDIO")
top[2].metric("Intervencao", "2017")
top[3].metric("Doadores max.", int(summary["n_doadores"].max()))

selected_model = st.selectbox(
    "Escolha um modelo para detalhar",
    models,
    format_func=lambda model: model_label(model, data["model_dict"]),
)

current_summary = summary[summary["modelo"].eq(selected_model)].iloc[0]
current_series = selected_series(series, selected_model)
current_weights = unit_weights[unit_weights["modelo"].eq(selected_model)].sort_values("w_weights", ascending=False)
current_pre = pre_means_long[pre_means_long["modelo"].eq(selected_model)]
outcome_label = OUTCOME_LABELS.get(current_summary["outcome"], current_summary["outcome"])

tabs = st.tabs(
    [
        "Metodo",
        "Comparabilidade",
        "Visao geral",
        "Modelo selecionado",
        "Todos os graficos",
        "Pesos",
        "Ajuste pre",
        "Dados",
    ]
)

with tabs[0]:
    st.subheader("Ajuste metodologico da pesquisa")
    st.markdown(
        """
        Os resultados iniciais com o **TST como unidade tratada** passam a ser tratados como um primeiro
        exercicio exploratorio de aplicacao do Metodo de Controle Sintetico. Essa rodada serviu para testar
        a base Justiça em Numeros, validar a operacionalizacao das variaveis orcamentarias e verificar a
        viabilidade empirica da estrategia.

        A especificacao principal da pesquisa foi reformulada. O **TST foi excluido da unidade tratada**
        porque possui perfil institucional e orcamentario proprio, associado a funcoes de cupula,
        coordenacao administrativa e jurisdicao superior. Sua trajetoria nao representa adequadamente
        a dinamica orcamentaria da Justica do Trabalho como um todo.

        A especificacao com TRTs agregados por soma tambem foi usada como etapa intermediaria, mas
        revelou problema de escala: em especial para despesa total, o metodo tendeu a se aproximar de
        uma comparacao direta com poucos tribunais de grande porte. Por isso, a unidade tratada principal
        agora e o **TRT medio sem TST** (`TRT_MEDIO`), construido pela media anual dos 24 TRTs.
        Essa escolha representa a trajetoria tipica de um tribunal regional e melhora a comparabilidade
        com os Tribunais de Justica estaduais.
        """
    )

    method_cols = st.columns(4)
    method_cols[0].metric("Unidade tratada principal", "TRT_MEDIO")
    method_cols[1].metric("TST na analise final", "Excluido")
    method_cols[2].metric("TJs na base candidata", int(data["base_wide"][data["base_wide"]["sigla"].str.startswith("TJ")]["sigla"].nunique()))
    method_cols[3].metric("Doadores efetivos por modelo", int(summary["n_doadores"].max()))

    st.markdown(
        """
        **Base de doadores**

        Todos os Tribunais de Justica estaduais disponiveis na base foram mantidos como candidatos.
        A partir desse universo amplo, o script R selecionou os TJs mais comparaveis por porte
        orcamentario no periodo pre-intervencao. Essa escolha busca melhorar o ajuste pre-2017,
        reduzir a dependencia de poucos doadores e construir uma unidade sintetica mais adequada.

        **Intervencao**

        A intervencao permanece definida em 2017, primeiro ano de vigencia orcamentaria da EC 95/2016.
        A linha pontilhada em 2023 indica o inicio do novo arcabouco fiscal, usado como marco visual
        complementar nos graficos.

        **Interpretacao**

        O resultado definitivo da pesquisa deve se concentrar no TRT medio sem TST. A rodada inicial
        com TST isolado e a rodada intermediaria com TRTs somados podem ser descritas como testes de
        especificacao e viabilidade metodologica, nao como evidencia final.
        """
    )

    st.subheader("Resultados da reformulacao metodologica")
    st.markdown(
        """
        A primeira rodada da pesquisa funcionou como teste de viabilidade metodologica. Nessa etapa,
        o TST foi utilizado como unidade tratada e TJMG, TJRJ e TJSP compuseram o grupo de doadores.
        A aplicacao permitiu validar a base, as variaveis e a operacionalizacao do metodo, mas tambem
        revelou limitacoes importantes: grupo de doadores restrito, concentracao de peso em poucos
        tribunais e baixa comparabilidade institucional entre o TST e os Tribunais Regionais do Trabalho.

        A especificacao principal da pesquisa passou, portanto, a excluir o TST e a utilizar o TRT medio,
        calculado como a media anual dos 24 Tribunais Regionais do Trabalho. Essa escolha reduz o problema
        de escala observado na agregacao por soma e aproxima a unidade tratada de tribunais estaduais de
        porte comparavel. O grupo de doadores tambem foi ampliado, com a inclusao dos Tribunais de Justica
        estaduais disponiveis na base candidata.

        A reformulacao metodologica fortalece a comparacao contrafactual. A trajetoria observada do TRT
        medio passa a ser comparada a uma trajetoria sintetica formada por tribunais estaduais ponderados,
        permitindo avaliar de modo mais consistente os efeitos da EC 95/2016 sobre despesas totais,
        despesas discricionarias e investimentos no ambito da Justica do Trabalho.
        """
    )

    st.markdown("**TJs candidatos e selecionados por porte**")
    c1, c2 = st.columns(2)
    with c1:
        all_tjs = (
            data["base_wide"][data["base_wide"]["sigla"].str.startswith("TJ")][["sigla"]]
            .drop_duplicates()
            .sort_values("sigla")
        )
        st.dataframe(all_tjs, use_container_width=True, hide_index=True)
    with c2:
        st.dataframe(data["donors"], use_container_width=True, hide_index=True)

with tabs[1]:
    st.subheader("Comparabilidade dos TRTs e justificativa do TRT medio")
    st.write(
        "As series dos TRTs foram indexadas com base 2016 = 100 para remover diferencas de escala. "
        "A analise mostra alta homogeneidade nas despesas estruturais, especialmente DPJ, DPE e DRH. "
        "ODCK e DK sao mais heterogeneas e, por isso, exigem interpretacao mais cautelosa."
    )

    if "comparability_evidence" in data:
        evidence = data["comparability_evidence"]
        cols = st.columns(3)
        for idx, var in enumerate(["dpj", "dpe", "drh"]):
            row = evidence[evidence["variavel"].eq(var)].iloc[0]
            cols[idx].metric(
                f"{var.upper()} dentro de 20% da media no pre",
                f"{row['pct_20_pre']:.1f}%",
            )
        st.dataframe(evidence, use_container_width=True, hide_index=True)

    image_specs = [
        ("01_trajetorias_indexadas_trts_2016_100.png", "Trajetorias indexadas dos TRTs"),
        ("02_faixa_dispersao_trt_medio.png", "Faixa de dispersao em torno do TRT medio"),
        ("03_coeficiente_variacao_trts.png", "Coeficiente de variacao dos TRTs"),
        ("04_percentual_trts_proximos_media.png", "Percentual de TRTs proximos da media"),
        ("05_matriz_correlacao_crescimento_trts.png", "Matriz de correlacao de crescimento"),
    ]
    for file_name, title in image_specs:
        path = comparability_image(file_name)
        if path.exists():
            st.markdown(f"**{title}**")
            st.image(str(path), use_container_width=True)

    if "comparability_period" in data:
        st.markdown("**Resumo de dispersao por periodo**")
        st.dataframe(data["comparability_period"], use_container_width=True, hide_index=True)

    st.info(f"Arquivos de comparabilidade carregados de: {COMPARABILITY_DIR}")

with tabs[2]:
    st.subheader("Resumo grafico dos resultados")
    st.write(
        "A tela abaixo mostra, para todos os modelos, o sinal do gap medio pos-intervencao "
        "e a intensidade da ruptura medida pela razao MSPE pos/pre."
    )

    c1, c2 = st.columns(2)
    with c1:
        fig_gap = px.bar(
            summary,
            x="modelo",
            y="gap_medio_pos",
            color="interpretacao_sinal",
            hover_data=["modelo_label", "outcome", "razao_mspe_pos_pre"],
            title="Gap medio pos-intervencao por modelo",
            labels={"gap_medio_pos": "Gap medio", "modelo": "Modelo"},
            color_discrete_sequence=["#2563eb", "#dc2626", "#64748b"],
        )
        fig_gap.add_hline(y=0, line_dash="dash", line_color="#334155")
        fig_gap.update_layout(height=430, legend_title=None)
        st.plotly_chart(fig_gap, use_container_width=True)

    with c2:
        fig_mspe = px.bar(
            summary,
            x="modelo",
            y="razao_mspe_pos_pre",
            color="qualidade_ruptura_mspe",
            hover_data=["modelo_label", "mspe_pre", "mspe_pos"],
            title="Razao MSPE pos/pre por modelo",
            labels={"razao_mspe_pos_pre": "MSPE pos / MSPE pre", "modelo": "Modelo"},
        )
        fig_mspe.add_hline(y=1, line_dash="dash", line_color="#334155")
        fig_mspe.update_layout(height=430, legend_title=None)
        st.plotly_chart(fig_mspe, use_container_width=True)

    heat = summary.pivot_table(
        index="modelo",
        values=["gap_medio_pos", "gap_acumulado_pos", "razao_mspe_pos_pre"],
        aggfunc="first",
    ).reset_index()
    heat_long = heat.melt(id_vars="modelo", var_name="indicador", value_name="valor")
    fig_heat = px.imshow(
        heat_long.pivot(index="modelo", columns="indicador", values="valor"),
        text_auto=".2f",
        aspect="auto",
        color_continuous_scale="RdBu",
        title="Mapa de calor dos indicadores centrais",
    )
    fig_heat.update_layout(height=430)
    st.plotly_chart(fig_heat, use_container_width=True)

    st.dataframe(
        summary[
            [
                "modelo",
                "modelo_label",
                "outcome",
                "gap_medio_pos",
                "gap_acumulado_pos",
                "razao_mspe_pos_pre",
                "interpretacao_sinal",
                "qualidade_ruptura_mspe",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )

with tabs[3]:
    st.subheader(model_label(selected_model, data["model_dict"]))
    cards = st.columns(5)
    cards[0].metric("MSPE pre", format_number(current_summary["mspe_pre"], 4))
    cards[1].metric("MSPE pos", format_number(current_summary["mspe_pos"], 4))
    cards[2].metric("Razao MSPE", format_number(current_summary["razao_mspe_pos_pre"], 2))
    cards[3].metric("Gap medio pos", format_number(current_summary["gap_medio_pos"], 4))
    cards[4].metric("Gap acumulado", format_number(current_summary["gap_acumulado_pos"], 4))

    st.info(
        f"{current_summary['interpretacao_sinal']}. "
        f"Classificacao: {current_summary['qualidade_ruptura_mspe']}."
    )

    left, right = st.columns([2, 1])
    with left:
        st.plotly_chart(
            trajectory_chart(current_series, "Observado versus sintetico", outcome_label),
            use_container_width=True,
        )
    with right:
        fig_w = px.bar(
            current_weights.sort_values("w_weights"),
            x="w_weights",
            y="unit_names",
            orientation="h",
            title="Pesos dos TJs doadores",
            labels={"w_weights": "Peso", "unit_names": "Doador"},
        )
        fig_w.update_layout(height=470)
        st.plotly_chart(fig_w, use_container_width=True)

    fig_gap_detail = px.bar(
        current_series,
        x="ano",
        y="gap",
        color="periodo",
        title="Gap anual: observado - sintetico",
        labels={"gap": "Gap", "ano": "Ano", "periodo": "Periodo"},
    )
    fig_gap_detail.add_hline(y=0, line_dash="dash", line_color="#334155")
    fig_gap_detail.add_vline(x=2017, line_dash="dash", line_color="#334155")
    fig_gap_detail.add_vline(x=2023, line_dash="dot", line_color="#64748b")
    st.plotly_chart(fig_gap_detail, use_container_width=True)

    st.markdown("**Estrategia empirica do modelo selecionado**")
    st.write(
        "O R/Synth compara a trajetoria observada do TRT medio com uma unidade sintetica composta "
        "por TJs doadores selecionados por porte. O periodo de ajuste e 2010-2016. A linha tracejada marca "
        "2017, inicio do pos-EC 95, e a linha pontilhada marca 2023, novo arcabouco fiscal."
    )

with tabs[4]:
    st.subheader("Trajetorias observado versus sintetico para todos os modelos")
    for model in models:
        model_series = selected_series(series, model)
        label = model_label(model, data["model_dict"])
        y_label = OUTCOME_LABELS.get(model_series["outcome"].iloc[0], model_series["outcome"].iloc[0])
        st.plotly_chart(trajectory_chart(model_series, label, y_label), use_container_width=True)

    st.subheader("Gaps anuais para todos os modelos")
    gap_all = series.copy()
    fig_all_gap = px.line(
        gap_all,
        x="ano",
        y="gap",
        color="modelo",
        facet_col="modelo",
        facet_col_wrap=2,
        markers=True,
        title="Gap anual por modelo",
        labels={"gap": "Observado - sintetico", "ano": "Ano"},
        height=900,
    )
    fig_all_gap.add_hline(y=0, line_dash="dash", line_color="#334155")
    fig_all_gap.update_yaxes(matches=None)
    st.plotly_chart(fig_all_gap, use_container_width=True)

with tabs[5]:
    st.subheader("Pesos das unidades doadoras")
    fig_weight_heat = px.imshow(
        unit_weights.pivot_table(index="unit_names", columns="modelo", values="w_weights", aggfunc="first").fillna(0),
        text_auto=".2f",
        aspect="auto",
        color_continuous_scale="Blues",
        title="Mapa de calor dos w.weights",
    )
    fig_weight_heat.update_layout(height=620)
    st.plotly_chart(fig_weight_heat, use_container_width=True)

    positive_weights = unit_weights[unit_weights["w_weights"] > 0].copy()
    fig_positive = px.bar(
        positive_weights,
        x="modelo",
        y="w_weights",
        color="unit_names",
        title="Doadores com peso positivo por modelo",
        labels={"w_weights": "Peso", "modelo": "Modelo", "unit_names": "Doador"},
    )
    fig_positive.update_layout(height=460, legend_title="Doador")
    st.plotly_chart(fig_positive, use_container_width=True)

    variable_weights = data["variable_weights"]
    if variable_weights["v_weights"].notna().any():
        fig_v = px.imshow(
            variable_weights.pivot_table(index="variavel", columns="modelo", values="v_weights", aggfunc="first").fillna(0),
            text_auto=".2f",
            aspect="auto",
            color_continuous_scale="Greens",
            title="Mapa de calor dos v.weights",
        )
        st.plotly_chart(fig_v, use_container_width=True)
    else:
        st.warning(
            "O export atual trouxe a coluna v_weights vazia. Por isso, o dashboard mostra os preditores usados, "
            "mas nao consegue desenhar os pesos das variaveis. Se o R exportar v.weights numericos, o grafico aparece automaticamente."
        )
        predictor_count = variable_weights.groupby(["modelo", "variavel"]).size().reset_index(name="presente")
        fig_predictors = px.scatter(
            predictor_count,
            x="modelo",
            y="variavel",
            size="presente",
            title="Preditores presentes por modelo",
            labels={"modelo": "Modelo", "variavel": "Preditor"},
        )
        fig_predictors.update_layout(height=560)
        st.plotly_chart(fig_predictors, use_container_width=True)

    st.dataframe(unit_weights, use_container_width=True, hide_index=True)

with tabs[6]:
    st.subheader("Ajuste pre-intervencao")
    st.write(
        "Comparacao entre a unidade tratada, a unidade sintetica e a media simples dos doadores no periodo pre-intervencao."
    )

    fig_pre = px.bar(
        pre_means_long,
        x="variavel",
        y="valor",
        color="tipo_comparacao",
        facet_col="modelo",
        facet_col_wrap=2,
        barmode="group",
        title="Tabela 3 - Medias pre-intervencao por modelo",
        labels={"variavel": "Variavel", "valor": "Valor", "tipo_comparacao": "Comparacao"},
        height=950,
    )
    fig_pre.update_xaxes(tickangle=-35)
    fig_pre.update_yaxes(matches=None)
    st.plotly_chart(fig_pre, use_container_width=True)

    pre_gap = data["pre_means"].copy()
    pre_gap["erro_sintetico_abs"] = (pre_gap["treated"] - pre_gap["synthetic"]).abs()
    pre_gap["erro_media_abs"] = (pre_gap["treated"] - pre_gap["sample_mean"]).abs()
    pre_gap_long = pre_gap.melt(
        id_vars=["modelo", "variavel"],
        value_vars=["erro_sintetico_abs", "erro_media_abs"],
        var_name="tipo_erro",
        value_name="erro_abs",
    )
    fig_pre_error = px.bar(
        pre_gap_long,
        x="variavel",
        y="erro_abs",
        color="tipo_erro",
        facet_col="modelo",
        facet_col_wrap=2,
        barmode="group",
        title="Erro absoluto pre: sintetico versus media simples",
        labels={"erro_abs": "Erro absoluto", "variavel": "Variavel"},
        height=950,
    )
    fig_pre_error.update_xaxes(tickangle=-35)
    fig_pre_error.update_yaxes(matches=None)
    st.plotly_chart(fig_pre_error, use_container_width=True)

with tabs[7]:
    st.subheader("Dados carregados")
    st.info(f"Exports carregados de: {EXPORT_DIR}")
    table_choice = st.selectbox(
        "Tabela",
        [
            "summary",
            "series",
            "unit_weights",
            "variable_weights",
            "pre_means",
            "donors",
            "model_dict",
            "variable_dict",
            "base_wide",
        ],
    )
    st.dataframe(data[table_choice], use_container_width=True, hide_index=True)

    st.download_button(
        "Baixar resumo em CSV",
        data=summary.to_csv(index=False, sep=";").encode("utf-8-sig"),
        file_name="resumo_dashboard_controle_sintetico.csv",
        mime="text/csv",
    )

