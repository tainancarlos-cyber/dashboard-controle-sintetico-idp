from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from article_charts import BLUE, GRAY, SOURCE
from article_data import SCM_MODELS, number
from article_ui import dataset, model_help, model_label


def selected_placebos(data, model, filtered=False):
    units = data["scm_placebo_mspe"].query("modelo == @model").copy()
    if filtered:
        units = units[units.incluido_filtro_20]
    series = data["scm_placebo_series"].query("modelo == @model")
    return units, series[series.unidade.isin(units.unidade)].copy()


def gap_figure(data, model, filtered=False):
    _, series = selected_placebos(data, model, filtered)
    scale = SCM_MODELS[model]["scale"]
    x, y, tribunals = [], [], []
    for unit, rows in series[~series.tratado].groupby("unidade", sort=True):
        rows = rows.sort_values("ano")
        x.extend(rows.ano.astype(int).tolist() + [None])
        y.extend((rows.gap * scale).tolist() + [None])
        tribunals.extend([unit] * len(rows) + [None])
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x, y=y, customdata=tribunals, name="Placebos (TJs)",
                             mode="lines", connectgaps=False, line={"color": "#AAB2BB", "width": 1.4},
                             hovertemplate="Tribunal: %{customdata}<br>Ano: %{x}<br>Gap: %{y:.4f}<extra></extra>"))
    treated = series[series.tratado].sort_values("ano")
    fig.add_trace(go.Scatter(x=treated.ano.astype(int).tolist(), y=(treated.gap * scale).tolist(),
                             name="TRT médio", mode="lines+markers", line={"color": BLUE, "width": 3},
                             marker={"size": 5}, hovertemplate="TRT médio<br>Ano: %{x}<br>Gap: %{y:.4f}<extra></extra>"))
    fig.add_hline(y=0, line_color=GRAY, line_width=1)
    fig.add_vline(x=2017, line_color=GRAY, line_dash="dash", line_width=1)
    fig.add_annotation(x=2017, y=1.04, yref="paper", text="2017", showarrow=False)
    fig.update_layout(template="plotly_white", height=450, separators=",.", hovermode="closest",
                      margin={"l": 55, "r": 15, "t": 65, "b": 50},
                      legend={"orientation": "h", "y": 1.16, "x": 0},
                      font={"family": "Arial, sans-serif", "size": 13, "color": "#263445"})
    fig.update_xaxes(title="Ano", dtick=2, tickformat="d", showgrid=False)
    fig.update_yaxes(title="Gap (pontos percentuais)" if scale == 100 else "Gap (unidades logarítmicas)",
                      gridcolor="#E7EBEF", automargin=True)
    return fig


def mspe_figure(data, model, filtered=False):
    units, _ = selected_placebos(data, model, filtered)
    units = units.sort_values("razao_mspe_pos_pre")
    labels = ["TRT médio" if row.tratado else row.unidade for row in units.itertuples()]
    fig = go.Figure(go.Bar(x=units.razao_mspe_pos_pre.tolist(), y=labels, orientation="h",
                           marker_color=[BLUE if value else "#AAB2BB" for value in units.tratado],
                           customdata=units[["mspe_pre", "mspe_pos"]].to_numpy().tolist(),
                           hovertemplate="%{y}<br>Razão MSPE pós/pré: %{x:.3f}<br>MSPE pré: %{customdata[0]:.6f}<br>MSPE pós: %{customdata[1]:.6f}<extra></extra>"))
    fig.update_layout(template="plotly_white", height=max(340, len(units) * 29 + 90), separators=",.",
                      margin={"l": 15, "r": 20, "t": 15, "b": 50}, showlegend=False,
                      font={"family": "Arial, sans-serif", "size": 13, "color": "#263445"})
    fig.update_xaxes(title="Razão MSPE pós/pré", rangemode="tozero", gridcolor="#E7EBEF")
    fig.update_yaxes(title=None, automargin=True)
    return fig


def show_placebos():
    data = dataset()
    st.title("Placebos do controle sintético")
    st.markdown("O teste compara o afastamento do **TRT médio** com os afastamentos obtidos ao atribuir ficticiamente a intervenção de 2017 a cada tribunal doador.")
    with st.expander("Como o teste foi aplicado"):
        st.markdown("Cada um dos **12 TJs** é tratado como se tivesse recebido a intervenção. Seu controle sintético é estimado com os **outros 11 TJs**, usando a mesma especificação e os mesmos períodos do modelo correspondente. O TRT médio e o TST não entram como doadores dos placebos.")
        st.caption("Ajuste pré-intervenção: 2010–2016. Avaliação pós-intervenção: 2017–2024. As trajetórias principais do TRT médio são as mesmas apresentadas nos resultados do artigo.")
        st.latex(r"R_i=\frac{MSPE_{i,\mathrm{pós}}}{MSPE_{i,\mathrm{pré}}},\qquad p=\frac{1+\sum_{j=1}^{J}\mathbf{1}(R_j\geq R_{\mathrm{TRT}})}{J+1}")
        st.markdown("O p-valor corresponde à proporção de unidades, **incluindo o TRT médio**, com razão MSPE igual ou superior à dele. Quanto menor o valor, mais excepcional é a posição do TRT médio no conjunto comparado.")
        st.markdown("O filtro mantém placebos com MSPE pré-intervenção **inferior a 20 vezes** o do TRT médio. Ele considera apenas o ajuste anterior à intervenção. Os resultados com todos os placebos e com o filtro são apresentados lado a lado.")
    st.subheader("Resultados dos seis modelos")
    summary = data["scm_placebo_resumo"].set_index("modelo")
    table = pd.DataFrame([{
        "Especificação": meta["label"], "Modelo": meta["outcome"],
        "Razão MSPE do TRT médio": number(summary.loc[model, "razao_mspe_tratado"]),
        "p · todos": number(summary.loc[model, "p_valor_todos"], 3),
        "p · com filtro": number(summary.loc[model, "p_valor_filtrado"], 3),
        "Placebos após filtro": int(summary.loc[model, "n_placebos_filtrados"]),
    } for model, meta in SCM_MODELS.items()])
    st.dataframe(table, hide_index=True, use_container_width=True)
    st.info("Nenhum dos seis modelos apresentou p-valor inferior a 0,05, com ou sem o filtro. Os gaps observados permanecem, mas os placebos não fornecem suporte estatístico adicional para atribuí-los à intervenção. Isso não demonstra ausência de efeito.")
    model = st.selectbox("Modelo para examinar os placebos", list(SCM_MODELS), format_func=model_label,
                          help="O nome técnico identifica a especificação. O identificador do R aparece abaixo e na ajuda dos gráficos.", key="placebo_model")
    st.caption(f"Modelo: `{SCM_MODELS[model]['outcome']}` · Identificador no R: `{model}`")
    comparison = st.radio("Conjunto de comparação", ["Todos os 12 placebos", "Filtro de ajuste pré-intervenção"],
                           horizontal=True, key="placebo_comparison")
    filtered = comparison == "Filtro de ajuste pré-intervenção"
    row = summary.loc[model]
    count = int(row.n_placebos_filtrados if filtered else row.n_placebos)
    probability = row.p_valor_filtrado if filtered else row.p_valor_todos
    columns = st.columns(4)
    columns[0].metric("Razão MSPE do TRT médio", number(row.razao_mspe_tratado))
    columns[1].metric("p-valor", number(probability, 3), help="Inclui o TRT médio na contagem das unidades comparadas.")
    columns[2].metric("Placebos comparados", str(count))
    columns[3].metric("Menor p-valor possível", number(1 / (count + 1), 3))
    st.caption("Com 12 placebos, o menor p-valor possível é 1/13 ≈ 0,077. Quando exclui doadores, o filtro reduz o número de comparações e eleva esse mínimo.")
    units, _ = selected_placebos(data, model, filtered)
    config = {"displaylogo": False, "modeBarButtonsToRemove": ["toImage"]}
    st.subheader("Figura de apoio — Gaps do TRT médio e dos placebos", help=model_help(model))
    st.plotly_chart(gap_figure(data, model, filtered), use_container_width=True, key="placebo_gaps", config=config)
    st.caption("Linhas cinzas: TJs tratados ficticiamente. Linha azul: TRT médio. Passe o cursor sobre as curvas para identificar o tribunal e o ano. Linha vertical: intervenção em 2017.")
    st.caption(SOURCE)
    st.subheader("Figura de apoio — Comparação das razões MSPE pós/pré", help=model_help(model))
    st.plotly_chart(mspe_figure(data, model, filtered), use_container_width=True, key="placebo_mspe", config=config)
    st.caption("Azul: TRT médio. Cinza: placebos do conjunto selecionado. A razão é adimensional e mede o afastamento quadrático relativo, sem indicar o sinal do gap.")
    st.caption(SOURCE)
    with st.expander("MSPEs e aplicação do filtro por tribunal"):
        details = data["scm_placebo_mspe"].query("modelo == @model").copy()
        details["Papel"] = details.tratado.map({True: "TRT médio", False: "Placebo"})
        details["No filtro"] = details.incluido_filtro_20.map({True: "Incluído", False: "Excluído"})
        details = details[["unidade", "Papel", "mspe_pre", "mspe_pos", "razao_mspe_pos_pre", "No filtro"]]
        details.columns = ["Tribunal", "Papel", "MSPE pré", "MSPE pós", "Razão MSPE pós/pré", "No filtro"]
        st.dataframe(details, hide_index=True, use_container_width=True)
        st.caption(f"Excluídos pelo filtro neste modelo: {int(row.n_descartados)} de {int(row.n_placebos)} TJs. O TRT médio permanece como referência nas duas comparações.")
    st.caption("Figuras de apoio aos testes de robustez, sem alteração da numeração dos Gráficos 1 a 8 do artigo. A interpretação também depende do ajuste pré-intervenção e da comparabilidade institucional entre TRTs e TJs.")
