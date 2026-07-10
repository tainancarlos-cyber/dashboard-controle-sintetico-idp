from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from markov_exports import (
    FIGURES_DIR,
    HYPOTHESIS_SUMMARY,
    RESULTS_DIR,
    consolidated_figure_path,
    evidence_rank,
    figure_path,
    final_summary_path,
    format_model_value,
    format_number,
    format_probability,
    load_markov_exports,
    model_label,
    model_options,
    normalize_period,
    period_rank,
)


st.set_page_config(
    page_title="Markov Switching | TRT medio",
    layout="wide",
)


@st.cache_data
def get_data() -> dict[str, pd.DataFrame]:
    return load_markov_exports()


def add_period_order(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["periodo_limpo"] = out["periodo"].map(normalize_period)
    out["ordem_periodo"] = out["periodo_limpo"].map(period_rank)
    return out.sort_values(["ordem_periodo", "modelo"])


def annual_probability_chart(df: pd.DataFrame, title: str) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["ano"],
            y=df["prob_regime_baixo"],
            mode="lines+markers",
            name="Prob. regime baixo",
            line={"width": 3, "color": "#2563eb"},
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df["ano"],
            y=df["prob_regime_alto"],
            mode="lines+markers",
            name="Prob. regime alto",
            line={"width": 2.5, "dash": "dash", "color": "#dc2626"},
        )
    )
    fig.add_hline(y=0.5, line_dash="dot", line_color="#64748b")
    fig.add_vline(x=2017, line_dash="dash", line_color="#334155", annotation_text="EC 95")
    fig.add_vline(x=2023, line_dash="dot", line_color="#64748b", annotation_text="Novo arcabouco")
    fig.update_layout(
        title=title,
        xaxis_title="Ano",
        yaxis_title="Probabilidade",
        yaxis={"range": [-0.03, 1.03], "tickformat": ".0%"},
        height=480,
        legend_title=None,
        margin={"l": 20, "r": 20, "t": 55, "b": 20},
    )
    return fig


def series_regime_chart(df: pd.DataFrame, model: str, title: str) -> go.Figure:
    colors = {"Regime baixo": "#2563eb", "Regime alto": "#dc2626"}
    fig = px.bar(
        df,
        x="ano",
        y="y",
        color="regime_mais_provavel",
        color_discrete_map=colors,
        title=title,
        labels={"ano": "Ano", "y": "Valor observado", "regime_mais_provavel": "Regime"},
    )
    fig.add_vline(x=2017, line_dash="dash", line_color="#334155")
    fig.add_vline(x=2023, line_dash="dot", line_color="#64748b")
    if "share_" in model:
        fig.update_yaxes(tickformat=".1%")
    fig.update_layout(height=430, legend_title=None)
    return fig


def transition_heatmap(df: pd.DataFrame, title: str) -> go.Figure:
    matrix = df.pivot_table(
        index="regime_origem",
        columns="regime_destino",
        values="prob_transicao",
        aggfunc="first",
    )
    ordered = [col for col in ["Regime baixo", "Regime alto"] if col in matrix.index]
    matrix = matrix.reindex(index=ordered, columns=ordered)
    fig = px.imshow(
        matrix,
        text_auto=".2f",
        aspect="auto",
        color_continuous_scale="Blues",
        zmin=0,
        zmax=1,
        title=title,
        labels={"x": "Destino", "y": "Origem", "color": "Probabilidade"},
    )
    fig.update_layout(height=360)
    return fig


data = get_data()
summary = data["summary"].copy()
interpretive = data["interpretive"].copy()
period = add_period_order(data["period"])
annual = data["annual"].copy()
annual["periodo_limpo"] = annual["periodo"].map(normalize_period)
regimes = data["regimes"].copy()
transition = data["transition"].copy()
models = model_options(summary)

st.title("Markov Switching - TRT medio sem TST")
st.caption(
    "Analise complementar ao Controle Sintetico. O objetivo e verificar se as series passaram a se concentrar "
    "em regimes baixos depois da EC 95/2016, especialmente em despesas discricionarias e despesas de capital."
)

top = st.columns(4)
top[0].metric("Modelos estimados", len(models))
top[1].metric("Periodo analisado", f"{int(summary['ano_inicial'].min())}-{int(summary['ano_final'].max())}")
top[2].metric("Intervencao", "2017")
top[3].metric("Novo arcabouco", "2023")

st.subheader("Leitura por hipotese")
hypotheses = sorted(summary["hipotese"].dropna().unique(), key=evidence_rank)
for col, hyp in zip(st.columns(len(hypotheses)), hypotheses):
    info = HYPOTHESIS_SUMMARY.get(hyp, {})
    with col:
        st.metric(info.get("titulo", hyp), info.get("evidencia", "n/d"))
        st.write(info.get("leitura", "Sem leitura cadastrada."))

with st.expander("Texto curto para interpretar o metodo", expanded=True):
    st.markdown(
        """
        O Markov Switching foi usado como analise complementar, nao como novo contrafactual.
        A pergunta central e se, depois da EC 95/2016, as series do TRT medio passaram a apresentar
        maior probabilidade de pertencer a um regime de menor crescimento ou menor participacao relativa.

        A evidencia e mais forte para H2 e H3. Em H2, as despesas discricionarias migram para regime baixo
        com especial clareza a partir de 2020. Em H3, a especificacao mais informativa e `share_dk`, pois
        a taxa de crescimento anual de capital e muito volatil. Em H1, a leitura deve ser cautelosa: ha queda
        do crescimento medio em 2017-2022, mas as medias dos regimes ficam proximas.
        """
    )

selected_model = st.selectbox(
    "Escolha um modelo para detalhar",
    models,
    format_func=lambda model: model_label(model, summary),
)

current_summary = summary[summary["modelo"].eq(selected_model)].iloc[0]
current_interpretive = interpretive[interpretive["modelo"].eq(selected_model)].iloc[0]
current_annual = annual[annual["modelo"].eq(selected_model)].sort_values("ano")
current_period = period[period["modelo"].eq(selected_model)]
current_regimes = regimes[regimes["modelo"].eq(selected_model)].copy()
current_transition = transition[transition["modelo"].eq(selected_model)].copy()

st.subheader(model_label(selected_model, summary))
cards = st.columns(5)
cards[0].metric("Regime baixo", format_model_value(selected_model, current_summary["media_regime_baixo"]))
cards[1].metric("Regime alto", format_model_value(selected_model, current_summary["media_regime_alto"]))
cards[2].metric("Diferenca", format_model_value(selected_model, current_summary["diferenca_media_alto_baixo"]))
cards[3].metric("Prob. baixa no pos", format_probability(current_summary["prob_regime_baixo_pos"]))
cards[4].metric("Observacoes", int(current_summary["n_obs"]))

st.info(
    f"{current_interpretive['leitura_pos_intervencao']}. "
    f"{current_interpretive['interpretacao_hipotese']}"
)

tab_overview, tab_period, tab_all, tab_png, tab_data = st.tabs(
    [
        "Modelo selecionado",
        "Periodos",
        "Comparacao geral",
        "Graficos do R",
        "Dados",
    ]
)

with tab_overview:
    left, right = st.columns([2, 1])
    with left:
        st.plotly_chart(
            annual_probability_chart(current_annual, "Probabilidades anuais dos regimes"),
            use_container_width=True,
        )
    with right:
        st.markdown("**Regimes estimados**")
        show_regimes = current_regimes[["regime_nome", "media_regime", "desvio_padrao_regime"]].copy()
        show_regimes["media_regime"] = show_regimes["media_regime"].map(
            lambda value: format_model_value(selected_model, value)
        )
        show_regimes["desvio_padrao_regime"] = show_regimes["desvio_padrao_regime"].map(
            lambda value: format_model_value(selected_model, value)
        )
        st.dataframe(
            show_regimes.rename(
                columns={
                    "regime_nome": "Regime",
                    "media_regime": "Media",
                    "desvio_padrao_regime": "Desvio padrao",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )
        st.plotly_chart(
            transition_heatmap(current_transition, "Probabilidades de transicao"),
            use_container_width=True,
        )

    st.plotly_chart(
        series_regime_chart(current_annual, selected_model, "Serie observada classificada pelo regime mais provavel"),
        use_container_width=True,
    )

with tab_period:
    display_period = current_period[
        [
            "periodo_limpo",
            "n_anos",
            "media_y",
            "prob_media_regime_baixo",
            "prob_media_regime_alto",
            "anos_regime_baixo",
            "anos_regime_alto",
        ]
    ].copy()
    display_period["media_y"] = display_period["media_y"].map(
        lambda value: format_model_value(selected_model, value)
    )
    for col in ["prob_media_regime_baixo", "prob_media_regime_alto"]:
        display_period[col] = display_period[col].map(format_probability)
    st.dataframe(
        display_period.rename(
            columns={
                "periodo_limpo": "Periodo",
                "n_anos": "Anos",
                "media_y": "Media da serie",
                "prob_media_regime_baixo": "Prob. media regime baixo",
                "prob_media_regime_alto": "Prob. media regime alto",
                "anos_regime_baixo": "Anos em regime baixo",
                "anos_regime_alto": "Anos em regime alto",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )

    period_plot = current_period.copy()
    period_plot["periodo_limpo"] = pd.Categorical(
        period_plot["periodo_limpo"],
        categories=["Pre-intervencao", "Pos-EC 95", "Novo arcabouco fiscal"],
        ordered=True,
    )
    fig_period = px.bar(
        period_plot,
        x="periodo_limpo",
        y="prob_media_regime_baixo",
        text="anos_regime_baixo",
        title="Probabilidade media de regime baixo por periodo",
        labels={
            "periodo_limpo": "Periodo",
            "prob_media_regime_baixo": "Probabilidade media",
            "anos_regime_baixo": "Anos em regime baixo",
        },
        color="periodo_limpo",
        color_discrete_sequence=["#64748b", "#2563eb", "#0f766e"],
    )
    fig_period.update_yaxes(range=[0, 1.05], tickformat=".0%")
    fig_period.update_layout(height=430, showlegend=False)
    st.plotly_chart(fig_period, use_container_width=True)

with tab_all:
    all_probs = annual.copy()
    fig_all = px.line(
        all_probs,
        x="ano",
        y="prob_regime_baixo",
        color="modelo",
        facet_col="hipotese",
        markers=True,
        title="Probabilidade de regime baixo em todos os modelos",
        labels={"ano": "Ano", "prob_regime_baixo": "Probabilidade", "modelo": "Modelo"},
        height=560,
    )
    fig_all.add_hline(y=0.5, line_dash="dot", line_color="#64748b")
    fig_all.add_vline(x=2017, line_dash="dash", line_color="#334155")
    fig_all.update_yaxes(range=[0, 1.05], tickformat=".0%")
    st.plotly_chart(fig_all, use_container_width=True)

    heat = summary.pivot_table(
        index="modelo",
        values=["media_regime_baixo", "media_regime_alto", "prob_regime_baixo_pos"],
        aggfunc="first",
    )
    fig_heat = px.imshow(
        heat,
        text_auto=".2f",
        aspect="auto",
        color_continuous_scale="RdBu",
        title="Mapa de calor dos indicadores centrais",
    )
    fig_heat.update_layout(height=430)
    st.plotly_chart(fig_heat, use_container_width=True)

    st.dataframe(
        interpretive[
            [
                "modelo",
                "hipotese",
                "descricao",
                "media_regime_baixo",
                "media_regime_alto",
                "prob_regime_baixo_pos",
                "interpretacao_hipotese",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )

with tab_png:
    consolidated = consolidated_figure_path()
    if consolidated.exists():
        st.markdown("**Probabilidade de regime baixo - consolidado**")
        st.image(str(consolidated), use_container_width=True)

    for suffix, label in [
        ("01_serie_regime", "Serie e regime mais provavel"),
        ("02_prob_regime_baixo", "Probabilidade do regime baixo"),
        ("03_probabilidades_regimes", "Probabilidades dos dois regimes"),
    ]:
        path = figure_path(selected_model, suffix)
        st.markdown(f"**{label}**")
        if path.exists():
            st.image(str(path), use_container_width=True)
        else:
            st.warning(f"Arquivo nao encontrado: {path.name}")

    st.info(f"Graficos carregados de: {FIGURES_DIR}")

with tab_data:
    st.markdown(f"Resultados carregados de: `{RESULTS_DIR}`")
    table_choice = st.selectbox(
        "Tabela",
        ["summary", "interpretive", "period", "annual", "regimes", "transition"],
    )
    st.dataframe(data[table_choice], use_container_width=True, hide_index=True)

    final_path = final_summary_path()
    if final_path.exists():
        st.download_button(
            "Baixar resumo final do Markov",
            data=final_path.read_bytes(),
            file_name=final_path.name,
            mime="text/plain",
        )

    st.download_button(
        "Baixar probabilidades anuais em CSV",
        data=annual.to_csv(index=False, sep=";").encode("utf-8-sig"),
        file_name="probabilidades_anuais_markov.csv",
        mime="text/csv",
    )
