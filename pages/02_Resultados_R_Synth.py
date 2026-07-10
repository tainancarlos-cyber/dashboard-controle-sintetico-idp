from __future__ import annotations

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from r_synth_exports import (
    EXPORT_DIR,
    OUTCOME_LABELS,
    format_number,
    image_path,
    load_exports,
    model_label,
    model_options,
)



@st.cache_data
def get_data():
    return load_exports()


data = get_data()

st.title("Controle Sintetico - Resultados gerados no R/Synth")
st.caption(
    "Unidade tratada: TRT medio sem TST. Base candidata: todos os TJs estaduais disponiveis. "
    "Doadores efetivos: TJs selecionados automaticamente por porte. "
    "Fonte dos resultados: pasta 04_exports_dashboard gerada pelo script R."
)

models = model_options(data["model_dict"])

with st.sidebar:
    st.header("Filtros")
    selected_model = st.selectbox(
        "Modelo",
        models,
        format_func=lambda model: model_label(model, data["model_dict"]),
    )
    show_r_png = st.toggle("Mostrar PNGs originais do R", value=False)

summary = data["summary"][data["summary"]["modelo"].eq(selected_model)].iloc[0]
series = data["series"][data["series"]["modelo"].eq(selected_model)].sort_values("ano")
unit_weights = data["unit_weights"][data["unit_weights"]["modelo"].eq(selected_model)].copy()
variable_weights = data["variable_weights"][data["variable_weights"]["modelo"].eq(selected_model)].copy()
pre_means = data["pre_means"][data["pre_means"]["modelo"].eq(selected_model)].copy()
pre_means_long = data["pre_means_long"][data["pre_means_long"]["modelo"].eq(selected_model)].copy()

outcome = summary["outcome"]
outcome_label = OUTCOME_LABELS.get(outcome, outcome)

st.subheader(model_label(selected_model, data["model_dict"]))

cards = st.columns(5)
cards[0].metric("Doadores usados", int(summary["n_doadores"]))
cards[1].metric("MSPE pre", format_number(summary["mspe_pre"], 4))
cards[2].metric("MSPE pos", format_number(summary["mspe_pos"], 4))
cards[3].metric("Razao pos/pre", format_number(summary["razao_mspe_pos_pre"], 2))
cards[4].metric("Gap medio pos", format_number(summary["gap_medio_pos"], 4))

st.info(
    f"{summary['interpretacao_sinal']}. Classificacao pela razao MSPE: "
    f"{summary['qualidade_ruptura_mspe']}."
)

with st.expander("Estrategia empirica aplicada neste modelo", expanded=True):
    st.markdown(
        f"""
        O script R aplicou o pacote `Synth` para construir uma unidade sintética do **TRT medio sem TST**.
        A intervenção foi fixada em **2017**, primeiro ano de vigência orçamentária da EC 95/2016.

        Para o modelo selecionado, a variável de resultado é **{outcome_label}** (`{outcome}`).
        Todos os TJs estaduais disponiveis foram mantidos como base candidata. A partir desse universo,
        o conjunto efetivo de doadores foi selecionado por porte orcamentario no periodo pre-intervencao,
        tomando como referencia a media de `dpj` entre 2010 e 2016. O codigo permitiu de 5 a 12 doadores
        e selecionou os TJs mais proximos da unidade tratada segundo distancia logaritmica de porte.

        A função `dataprep()` montou a base do controle sintético com:

        - unidade tratada: `TRT_MEDIO`;
        - controles: `{summary['doadores_utilizados']}`;
        - período de otimização: 2010-2016;
        - período de plotagem: 2010-2024;
        - intervenção: 2017;
        - preditores médios definidos no script R;
        - `special.predictors`: anos selecionados da própria variável de resultado no pré-tratamento.

        Em seguida, `synth()` estimou os pesos das unidades doadoras (`w.weights`) e os pesos das variáveis
        preditoras (`v.weights`). O resultado central é o gap anual:

        `gap = observado - sintetico`
        """
    )

left, right = st.columns([2.2, 1])

with left:
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=series["ano"],
            y=series["observado"],
            mode="lines+markers",
            name="TRT medio observado",
            line={"width": 3, "color": "#1f77b4"},
        )
    )
    fig.add_trace(
        go.Scatter(
            x=series["ano"],
            y=series["sintetico"],
            mode="lines+markers",
            name="TRT medio sintetico",
            line={"width": 3, "dash": "dash", "color": "#d62728"},
        )
    )
    fig.add_vline(x=2017, line_dash="dash", line_color="#333", annotation_text="EC 95")
    fig.add_vline(x=2023, line_dash="dot", line_color="#666", annotation_text="Novo arcabouco")
    fig.update_layout(
        title="Observado versus sintetico",
        xaxis_title="Ano",
        yaxis_title=outcome_label,
        height=520,
        legend_title=None,
    )
    st.plotly_chart(fig, use_container_width=True)

with right:
    top_weights = unit_weights.sort_values("w_weights", ascending=False)
    st.markdown("**Pesos das unidades doadoras**")
    st.dataframe(
        top_weights[["unit_names", "w_weights"]].rename(
            columns={"unit_names": "TJ doador", "w_weights": "peso"}
        ),
        use_container_width=True,
        hide_index=True,
    )
    positive = top_weights[top_weights["w_weights"] > 0]
    if not positive.empty:
        donors_text = ", ".join(
            f"{row.unit_names} ({row.w_weights:.3f})" for row in positive.itertuples(index=False)
        )
        st.write(f"Doadores efetivamente ponderados: {donors_text}.")
    else:
        st.write("Nenhum peso positivo identificado no arquivo exportado.")

gap_fig = px.bar(
    series,
    x="ano",
    y="gap",
    color="periodo",
    title="Gap anual: observado menos sintetico",
    labels={"gap": "Gap", "ano": "Ano", "periodo": "Periodo"},
)
gap_fig.add_hline(y=0, line_dash="dash", line_color="#444")
gap_fig.add_vline(x=2017, line_dash="dash", line_color="#333")
gap_fig.add_vline(x=2023, line_dash="dot", line_color="#666")
st.plotly_chart(gap_fig, use_container_width=True)

st.subheader("Pesos, ajuste pre-intervencao e interpretacao")

col1, col2 = st.columns(2)
with col1:
    weights_plot = unit_weights.sort_values("w_weights", ascending=True)
    fig_w = px.bar(
        weights_plot,
        x="w_weights",
        y="unit_names",
        orientation="h",
        title="Tabela 2 - Pesos das unidades doadoras",
        labels={"w_weights": "Peso", "unit_names": "Unidade doadora"},
    )
    st.plotly_chart(fig_w, use_container_width=True)

with col2:
    vw = variable_weights.dropna(subset=["v_weights"]).sort_values("v_weights", ascending=True)
    if vw.empty:
        st.warning(
            "O arquivo de pesos das variaveis nao trouxe valores numericos de v.weights para este modelo. "
            "A tabela bruta continua disponivel abaixo."
        )
    else:
        fig_v = px.bar(
            vw,
            x="v_weights",
            y="variavel",
            orientation="h",
            title="Tabela 1 - Pesos das variaveis preditoras",
            labels={"v_weights": "Peso", "variavel": "Preditor"},
        )
        st.plotly_chart(fig_v, use_container_width=True)

st.markdown(
    """
    **Como ler os pesos**

    Os `w.weights` indicam a composicao da unidade sintética. Um TJ com peso elevado foi mais útil para
    reproduzir a trajetória pré-intervenção do TRT medio. Peso zero não significa irrelevância institucional;
    significa apenas que, dadas as restrições do método e os demais doadores disponíveis, aquele TJ não melhorou
    o ajuste pré-intervenção.

    Os `v.weights`, quando disponíveis no export, indicam quais preditores tiveram maior importância na distância
    minimizada pelo `Synth`.
    """
)

means_fig = px.bar(
    pre_means_long,
    x="variavel",
    y="valor",
    color="tipo_comparacao",
    barmode="group",
    title="Tabela 3 - Medias pre-intervencao: tratado, sintetico e media dos doadores",
    labels={"variavel": "Variavel", "valor": "Valor", "tipo_comparacao": "Comparacao"},
)
means_fig.update_layout(xaxis_tickangle=-35)
st.plotly_chart(means_fig, use_container_width=True)

tabs = st.tabs(["Resumo", "Series", "Pesos", "Medias pre", "Base e dicionarios", "PNGs do R"])

with tabs[0]:
    st.dataframe(data["summary"], use_container_width=True, hide_index=True)

with tabs[1]:
    st.dataframe(series, use_container_width=True, hide_index=True)

with tabs[2]:
    c1, c2 = st.columns(2)
    c1.dataframe(unit_weights, use_container_width=True, hide_index=True)
    c2.dataframe(variable_weights, use_container_width=True, hide_index=True)

with tabs[3]:
    st.dataframe(pre_means, use_container_width=True, hide_index=True)

with tabs[4]:
    st.markdown(f"Exports carregados de: `{EXPORT_DIR}`")
    st.markdown("**Dicionario dos modelos**")
    st.dataframe(data["model_dict"], use_container_width=True, hide_index=True)
    st.markdown("**Dicionario das variaveis**")
    st.dataframe(data["variable_dict"], use_container_width=True, hide_index=True)
    st.markdown("**Doadores selecionados por porte**")
    st.dataframe(data["donors"], use_container_width=True, hide_index=True)

with tabs[5]:
    if show_r_png:
        for suffix, label in [
            ("01_observado_sintetico", "Observado versus sintetico"),
            ("02_gap", "Gap"),
            ("03_placebos", "Placebos"),
            ("04_rmspe", "RMSPE"),
        ]:
            path = image_path(selected_model, suffix)
            st.markdown(f"**{label}**")
            if path.exists() and path.stat().st_size > 1000:
                st.image(str(path), use_container_width=True)
            elif path.exists():
                st.warning(f"Arquivo encontrado, mas parece vazio/incompleto: {path.name}")
            else:
                st.warning(f"Arquivo nao encontrado: {path.name}")
    else:
        st.write("Ative a opcao na lateral para exibir os PNGs originais gerados pelo R.")
