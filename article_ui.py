from __future__ import annotations

import base64

import pandas as pd
import plotly.express as px
import streamlit as st

from article_data import (ARTICLE_INDICATORS, DATA_DIR, FIGURES, INDICATORS, MARKOV_MODELS, SCM_MODELS,
                          csv_bytes, data_archive, load_data, number, period_means, table3)
from article_charts import (BLUE, OCHRE, SOURCE, interactive, line, scm_spec, serialized)


def setup():
    st.markdown("""<style>
    .block-container {max-width: 1180px; padding-top: 2rem; padding-bottom: 3rem;}
    h1 {letter-spacing: -.035em;} h2 {letter-spacing: -.02em;}
    div[data-testid="stMetricValue"] {font-size: 1.65rem;}
    div[data-testid="stMetric"] {border-bottom: 2px solid #dfe6ed; padding-bottom: .65rem;}
    div[data-testid="stCaptionContainer"] {line-height: 1.55;}
    </style>""", unsafe_allow_html=True)
    with st.sidebar:
        st.caption("MESTRADO PROFISSIONAL · IDP")
        st.markdown("**Regras fiscais e orçamento dos TRTs**")
        st.caption("24 TRTs · 2010–2024\n\nValores reais: IPCA, dez./2024")


def dataset():
    try:
        return load_data()
    except (OSError, ValueError, AssertionError) as exc:
        st.error("Não foi possível carregar o conjunto de dados verificado do artigo.")
        st.exception(exc)
        st.stop()


def model_label(model):
    metadata = SCM_MODELS[model] if model in SCM_MODELS else MARKOV_MODELS[model]
    technical = metadata["outcome"] if model in SCM_MODELS else model
    return f"{metadata['label']} · {technical}"


def model_help(model):
    metadata = SCM_MODELS[model] if model in SCM_MODELS else MARKOV_MODELS[model]
    technical = metadata["outcome"] if model in SCM_MODELS else model
    return (f"{metadata['label']}\n\nModelo: {technical}\n\n"
            f"Identificador da estimação no R: {model}\n\nUnidade: {metadata['unit']}")


def chart(spec, key, model=None):
    st.subheader(spec["title"], help=model_help(model) if model else None)
    if model:
        technical = SCM_MODELS[model]["outcome"] if model in SCM_MODELS else model
        st.caption(f"Modelo: `{technical}`")
    if spec.get("article_figure"):
        # The article embeds these exact PNG files, without regenerating or rescaling them.
        content = (DATA_DIR / "figuras" / f"{spec['filename']}.png").read_bytes()
        st.image("data:image/png;base64," + base64.b64encode(content).decode("ascii"), use_container_width=True)
    else:
        st.plotly_chart(interactive(spec), use_container_width=True, key=f"plot_{key}",
                        config={"displaylogo": False, "modeBarButtonsToRemove": ["toImage"]})
    st.caption("Nota: " + spec["note"] + " Linhas verticais: 2017, início da intervenção; 2023, mudança de regime fiscal.")
    st.caption(SOURCE)


def overview():
    data = dataset()
    st.title("Regras fiscais e orçamento dos TRTs")
    st.markdown("Aplicação estatística da dissertação: **controle sintético**, **Markov Switching** e **produtividade e escala operacional**.")
    st.caption("Unidade tratada: média anual dos 24 TRTs. O TST não integra a amostra. Dados anuais de 2010 a 2024.")
    summary = data["scm_resumo"].set_index("modelo")
    cols = st.columns(4)
    cols[0].metric("H1 · Gap médio da DPJ real", number(summary.loc["H1_lndpj", "gap_medio_pos"], 4), help="Diferença média observado − sintético em unidades logarítmicas, 2017–2024.")
    cols[1].metric("H2 · Participação ODCK", number(summary.loc["H2_share_odck", "gap_medio_pos"] * 100) + " p.p.", help="Gap médio da participação das despesas discricionárias, 2017–2024.")
    cols[2].metric("H3 · Participação DK", number(summary.loc["H3_share_dk", "gap_medio_pos"] * 100) + " p.p.", help="Gap médio da participação das despesas de capital, 2017–2024.")
    cols[3].metric("DPJ real · 2016–2024", number(table3(data).iloc[0]["Variação média"]) + "%", help="Média simples das variações individuais dos 24 TRTs.")
    st.subheader("Como a análise se organiza")
    st.markdown("""
    1. **Controle sintético:** constrói o contrafactual do TRT médio com 12 tribunais de justiça doadores. É a principal análise da trajetória e da composição do gasto, complementada pelos testes de placebo.
    2. **Markov Switching:** identifica regimes nas séries observadas e examina a corroboração temporal dos achados, sobretudo nos indicadores de composição.
    3. **Produtividade e escala:** descreve a evolução da despesa, da atividade e do desempenho dos 24 TRTs, considerando possíveis explicações alternativas.
    """)
    st.subheader("Tabela 1 — Variáveis orçamentárias")
    st.dataframe(pd.DataFrame([
        ["DPJ", "Despesa total do órgão", "Trajetória da despesa total"],
        ["DPE", "Despesa com pessoal", "Componente de maior rigidez"],
        ["DRH", "Despesa com recursos humanos", "Medida ampliada de despesa rígida"],
        ["ODCK", "Outras despesas correntes e de capital", "Despesas discricionárias"],
        ["DK", "Despesa de capital", "Despesas de capital e participação no orçamento"],
    ], columns=["Sigla", "Descrição", "Uso na pesquisa"]), hide_index=True, use_container_width=True)
    st.subheader("Correção monetária e unidade tratada")
    st.latex(r"V^R_{it}=V_{it}\,\frac{IPCA_{\mathrm{dez}/2024}}{IPCA_{\mathrm{dez}/t}}")
    st.markdown("Os níveis da despesa total e das despesas de capital e seus preditores monetários são expressos a preços de dezembro de 2024. O índice utilizado é o IPCA nacional, divulgado pelo IBGE.")
    st.latex(r"\overline{V}_t=\frac{1}{24}\sum_{r=1}^{24}V_{rt}")
    st.caption("O TRT médio representa a média anual dos tribunais regionais; sua interpretação se refere a essa unidade, e não ao orçamento somado do ramo.")
    st.subheader("Tabela 2 — Hipóteses e especificações")
    rows = []
    for model, item in SCM_MODELS.items():
        markov = "MS_H1_g_lndpj" if model == "H1_lndpj" else "MS_H3_g_lndk" if model == "H3_lndk" else "MS_" + model
        rows.append([item["hypothesis"], item["label"].split(" · ")[1], item["outcome"], model, markov])
    st.dataframe(pd.DataFrame(rows, columns=["Hipótese", "Dimensão analisada", "Modelo / variável", "Controle sintético", "Markov Switching"]), hide_index=True, use_container_width=True)
    with st.expander("Dados utilizados e reprodução"):
        st.markdown("O conjunto publicado contém apenas as seis especificações do artigo, os 24 TRTs da análise descritiva, os 12 doadores efetivos e os indicadores de comparabilidade. Os resultados das estimações são os exportados pelo R.")
        st.download_button("Baixar dados do artigo e manifesto de fontes", data_archive(), "dados_artigo_ipca_2024.zip", mime="application/zip")
        st.dataframe(data["ipca_fatores"].rename(columns={"ano": "Ano", "fator_ipca_dez2024": "Fator para dez./2024"}), hide_index=True, use_container_width=True)
        st.markdown("Fontes: Conselho Nacional de Justiça, Justiça em Números; [IBGE, série histórica do IPCA](https://ftp.ibge.gov.br/Precos_Indices_de_Precos_ao_Consumidor/IPCA/Serie_Historica/ipca_SerieHist.zip).")
    st.page_link("pages/03_Resultados_R_Synth.py", label="Ver os Gráficos 1 a 8", icon="↗")


def synthetic_method():
    data = dataset()
    st.title("Controle sintético · aplicação")
    st.markdown("**Pergunta:** como teria evoluído o TRT médio na ausência da intervenção, tomando uma combinação de tribunais estaduais como referência?")
    st.markdown("""
    1. **Unidade tratada:** média anual dos 24 TRTs, com exclusão do TST.
    2. **Período de ajuste:** 2010–2016. **Período pós-intervenção:** 2017–2024.
    3. **Grupo de controle:** 12 TJs selecionados por porte orçamentário no período pré-intervenção.
    4. **Estimação:** pesos não negativos, com soma igual a um, definidos a partir das características anteriores à intervenção.
    """)
    st.latex(r"\widehat{Y}_{1t}^{N}=\sum_j w_jY_{jt},\qquad w_j\geq0,\quad\sum_jw_j=1")
    st.markdown("O contrafactual é uma média ponderada dos doadores. Os pesos são estimados separadamente para cada variável de resultado.")
    model = st.selectbox("Especificação para examinar os pesos e o ajuste", list(SCM_MODELS), format_func=model_label, help="O nome técnico aparece após a especificação. Ele identifica a variável de resultado; o identificador completo do R aparece abaixo.", key="method_model")
    st.caption(f"Modelo: `{SCM_MODELS[model]['outcome']}` · Identificador no R: `{model}`")
    weights = data["scm_pesos"].query("modelo == @model").sort_values("w_weights", ascending=False)
    left, right = st.columns([1, 1.4])
    with left:
        st.markdown("**Pesos dos doadores**")
        st.dataframe(weights[["unit_names", "w_weights"]].rename(columns={"unit_names": "Tribunal", "w_weights": "Peso"}), hide_index=True, use_container_width=True)
        st.caption("Pesos apresentados com três casas decimais.")
    with right:
        fig = px.bar(weights.sort_values("w_weights"), x="w_weights", y="unit_names", orientation="h", labels={"w_weights": "Peso", "unit_names": "Tribunal"}, color_discrete_sequence=[BLUE])
        fig.update_layout(template="plotly_white", height=390, margin={"t": 15, "b": 30}, showlegend=False)
        st.plotly_chart(fig, use_container_width=True, key="weights_chart")
    with st.expander("Preditores e equilíbrio pré-intervenção"):
        st.markdown("São utilizados valores anteriores à intervenção da variável de resultado, despesas com pessoal e recursos humanos e indicadores de composição. A despesa total também integra os preditores quando não é a variável de resultado. Nos modelos de níveis reais, os preditores monetários também são reais.")
        balance = data["scm_ajuste_pre"].query("modelo == @model")
        st.dataframe(balance.drop(columns="modelo").rename(columns={"variavel": "Preditor", "treated": "TRT médio", "synthetic": "Sintético", "sample_mean": "Média dos doadores"}), hide_index=True, use_container_width=True)
    st.subheader("Como interpretar o resultado")
    st.latex(r"gap_t=Y_{1t}-\widehat{Y}_{1t}^{N}")
    st.markdown("Um gap negativo indica valor observado inferior ao sintético. Em participações, a diferença é apresentada em **pontos percentuais**; nos modelos de logaritmos, em **unidades logarítmicas**.")
    st.latex(r"MSPE=\frac{1}{T}\sum_t\left(Y_{1t}-\widehat{Y}_{1t}^{N}\right)^2,\qquad R=\frac{MSPE_{\mathrm{pós}}}{MSPE_{\mathrm{pré}}}")
    st.markdown("A razão MSPE compara o erro quadrático médio de predição posterior com o anterior à intervenção. Valores superiores a um indicam maior afastamento quadrático médio no pós-intervenção. A razão, isoladamente, não determina significância estatística.")
    st.subheader("Comparabilidade dos 24 TRTs")
    st.markdown("As cinco rubricas monetárias foram corrigidas pelo IPCA e indexadas em 2016 = 100 por tribunal. O coeficiente de variação e a proximidade da média descrevem a dispersão das trajetórias relativas.")
    comp = data["comparabilidade"][["variavel", "cv_medio_pre", "pct_20_pre", "cv_medio_pos_ec95", "pct_20_pos_ec95"]].copy()
    comp.columns = ["Variável", "CV médio: 2010–2016", "Dentro de ±20% da média: pré (%)", "CV médio: 2017–2022", "Dentro de ±20% da média: 2017–2022 (%)"]
    st.dataframe(comp, hide_index=True, use_container_width=True)
    st.caption("O indicador de proximidade corresponde à média anual do percentual de TRTs dentro da faixa.")
    st.info("A interpretação depende do ajuste anterior à intervenção e da comparabilidade institucional entre TRTs e TJs. Na H1, o afastamento de 2016 exige atenção. O marco de 2023 contextualiza a mudança de regime fiscal e não constitui uma segunda intervenção estimada separadamente.")
    with st.expander("Validação por placebos"):
        st.markdown("Os seis modelos foram avaliados por placebos no espaço: cada TJ é tratado ficticiamente em 2017 e comparado com os outros 11 doadores. Nenhum apresentou p-valor inferior a 0,05, com ou sem o filtro de ajuste pré-intervenção.")
        st.page_link("pages/05_Placebos.py", label="Examinar os testes de placebo e seus gráficos")


def synthetic_results():
    data = dataset()
    st.title("Controle sintético · resultados e gráficos do artigo")
    hypothesis = st.radio("Hipótese", ["H1", "H2", "H3"], horizontal=True, key="results_hypothesis")
    models = [m for m, item in SCM_MODELS.items() if item["hypothesis"] == hypothesis]
    summary = data["scm_resumo"].set_index("modelo")
    rows = []
    for model in models:
        item, source = SCM_MODELS[model], summary.loc[model]
        share = item["scale"] == 100
        rows.append({"Especificação": item["label"], "Modelo": item["outcome"], "MSPE pré": number(source.mspe_pre, 6), "MSPE pós": number(source.mspe_pos, 6),
                     "Razão MSPE pós/pré": number(source.razao_mspe_pos_pre), "Gap médio 2017–2024": number(source.gap_medio_pos * item["scale"], 2 if share else 4) + (" p.p." if share else " un. log.")})
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    if hypothesis == "H1":
        st.markdown("A despesa total real ficou abaixo da trajetória sintética em todos os anos de 2017–2024. Os maiores afastamentos negativos ocorreram em 2023 e 2024. O desvio anterior à intervenção, em 2016, integra a avaliação do ajuste.")
    elif hypothesis == "H2":
        st.markdown("As três especificações indicam menor posição relativa das despesas discricionárias em relação ao contrafactual. Os afastamentos negativos tornam-se, em geral, mais pronunciados a partir de 2020.")
    else:
        st.markdown("Os níveis reais das despesas de capital apresentam gaps positivos em 2017–2020 e negativos em 2021–2024. A participação na despesa total ficou, em média, abaixo da sintética no período pós-intervenção.")
    st.caption("Os testes de placebo não apresentaram significância a 5%. A comparação dos gaps deve ser interpretada em conjunto com essa evidência e com a qualidade do ajuste pré-intervenção.")
    st.page_link("pages/05_Placebos.py", label="Ver os placebos e a comparação das razões MSPE")
    for definition in FIGURES:
        if SCM_MODELS[definition["model"]]["hypothesis"] == hypothesis:
            chart(scm_spec(data, definition), f"article_{definition['number']}", model=definition["model"])
    numbered_gaps = {definition["model"] for definition in FIGURES if definition["kind"] == "gap"}
    missing_gaps = [model for model in models if model not in numbered_gaps]
    if missing_gaps:
        st.subheader("GAPs complementares por modelo")
        for model in missing_gaps:
            definition = {"model": model, "kind": "gap", "title": "Figura de apoio — GAP anual do modelo " + SCM_MODELS[model]["outcome"]}
            chart(scm_spec(data, definition), "support_gap_" + model, model=model)
    if hypothesis == "H2":
        with st.expander("Trajetória complementar · ln_odck_drh — ODCK / DRH"):
            definition = {"model": "H2_ln_odck_drh", "kind": "trajectory", "title": "Figura de apoio — Despesas discricionárias / recursos humanos"}
            chart(scm_spec(data, definition), "support_odck_drh", model="H2_ln_odck_drh")
    with st.expander("Dados anuais dos modelos apresentados"):
        selected = data["scm_series"][data["scm_series"].modelo.isin(models)]
        st.dataframe(selected, hide_index=True, use_container_width=True)
        st.download_button("Baixar séries anuais", csv_bytes(selected), f"series_controle_sintetico_{hypothesis}.csv", mime="text/csv", key="scm_csv")


def markov():
    data = dataset()
    st.title("Markov Switching · análise complementar")
    st.markdown("O modelo identifica dois regimes nas séries observadas do TRT médio. Sua função é examinar a dinâmica temporal e a corroboração dos achados do controle sintético.")
    with st.expander("Como o modelo foi aplicado", expanded=True):
        st.latex(r"Y_t=\mu_{s_t}+\varepsilon_t,\quad\varepsilon_t\sim N(0,\sigma_{s_t}^2),\quad P(s_t=k\mid s_{t-1}=l)=p_{lk}")
        st.markdown("Cada regime possui média e dispersão próprias. O regime de menor média estimada é denominado **baixo**. As probabilidades suavizadas utilizam a série observada completa para estimar a probabilidade de cada regime em cada ano.")
        st.caption("Para crescimento real, regime baixo significa menor média das variações logarítmicas; para participações e razões, significa menor posição relativa da rubrica.")
    model = st.selectbox("Modelo de Markov", list(MARKOV_MODELS), format_func=model_label, help="O identificador técnico do modelo aparece após a especificação e também acompanha os gráficos.", key="markov_model")
    metadata = MARKOV_MODELS[model]
    st.latex(metadata["formula"])
    selected = data["markov_series"].query("modelo == @model").sort_values("ano")
    periods = period_means(data, model)
    before, after = periods.iloc[0], periods.iloc[-1]
    cols = st.columns(2)
    probcol = "Probabilidade média do regime baixo (%)"
    cols[0].metric("Regime baixo · pré-intervenção", number(before[probcol]) + "%")
    cols[1].metric("Regime baixo · 2017–2024", number(after[probcol]) + "%")
    if model in {"MS_H1_g_lndpj", "MS_H3_g_lndk"}:
        st.markdown("A probabilidade média do regime baixo em 2017–2024 é inferior à do período pré-intervenção. Essa especificação descreve a dinâmica do crescimento real e não corrobora uma mudança persistente para o regime de menor crescimento após 2017.")
        st.caption("Unidade: diferença anual de ln(1 + despesa real média), multiplicada por 100. Não corresponde a uma variação percentual exata.")
    elif model == "MS_H3_share_dk":
        st.markdown("A participação das despesas de capital apresenta maior concentração no regime baixo nos anos mais recentes. A corroboração da H3 concentra-se nessa dimensão relativa da rubrica.")
    else:
        st.markdown("A maior presença do regime baixo nos anos mais recentes corrobora a compressão relativa das despesas discricionárias identificada pelo controle sintético.")
    spec = {"title": "Figura de apoio — Probabilidades suavizadas dos regimes", "ylabel": "Probabilidade (%)",
            "lines": [line("Regime baixo", selected.ano, selected.prob_regime_baixo * 100), line("Regime alto", selected.ano, selected.prob_regime_alto * 100, OCHRE, "dash")],
            "range": [0, 100], "reference": 50, "zero": False, "filename": "apoio_" + model + "_probabilidades",
            "note": "Regimes ordenados pela média estimada; linha horizontal de referência em 50%."}
    chart(spec, "markov_prob", model=model)
    spec_y = {"title": "Figura de apoio — " + metadata["label"], "ylabel": metadata["unit"],
              "lines": [line("Série observada do TRT médio", selected.ano, selected.y * metadata["scale"])],
              "range": None, "zero": model in {"MS_H1_g_lndpj", "MS_H3_g_lndk"}, "filename": "apoio_" + model + "_serie",
              "note": "Crescimento real em diferenças logarítmicas × 100; participações em %; razões em unidades logarítmicas."}
    with st.expander("Série observada e parâmetros dos regimes"):
        chart(spec_y, "markov_series", model=model)
        regimes = data["markov_regimes"].query("modelo == @model").copy()
        regimes["media_regime"] *= metadata["scale"]
        regimes["desvio_padrao_regime"] *= metadata["scale"]
        st.dataframe(regimes[["regime_nome", "media_regime", "desvio_padrao_regime"]].rename(columns={"regime_nome": "Regime", "media_regime": "Média", "desvio_padrao_regime": "Desvio-padrão"}), hide_index=True, use_container_width=True)
        st.caption("Médias e desvios-padrão apresentados na unidade indicada no eixo da série observada.")
    periods["Média da variável"] *= metadata["scale"]
    st.markdown("**Comparação por períodos**")
    st.dataframe(periods, hide_index=True, use_container_width=True)
    with st.expander("Matriz de transição e dados anuais"):
        transitions = data["markov_transicoes"].query("modelo == @model")
        matrix = transitions.pivot(index="regime_origem", columns="regime_destino", values="prob_transicao") * 100
        st.dataframe(matrix, use_container_width=True)
        st.caption("Linhas: regime de origem. Colunas: regime de destino. Probabilidades em %.")
        st.download_button("Baixar dados anuais do modelo", csv_bytes(selected), f"{model}_dados.csv", mime="text/csv")
    st.caption("As figuras de apoio não recebem os números 1 a 8, reservados aos gráficos já presentes no artigo. O Markov descreve regimes e não constrói um contrafactual causal.")


def productivity():
    data = dataset()
    st.title("Produtividade e escala operacional")
    st.markdown("Análise descritiva dos **24 TRTs**, com painel de 360 observações tribunal-ano entre 2010 e 2024. A comparação de 2016 a 2024 atribui o mesmo peso a cada tribunal.")
    table = table3(data)
    st.subheader("Tabela 3 — Evolução média dos indicadores, 2016–2024")
    display = table.copy()
    for column in ["Variação média", "Mediana", "Q1", "Q3"]:
        display[column] = [number(value) + " " + unit for value, unit in zip(table[column], table.Unidade)]
    st.dataframe(display.drop(columns="Unidade"), hide_index=True, use_container_width=True)
    st.caption("Variações calculadas por TRT e agregadas por média simples. IAD e TCL em pontos percentuais; demais indicadores em %. DPJ a preços de dezembro de 2024.")
    st.markdown("A DPJ apresentou crescimento real médio de **2,19%**, com força de trabalho praticamente estável (**−0,81%**). Os processos baixados cresceram **13,51%**, acompanhados de melhora dos indicadores de produtividade e da taxa de congestionamento.")
    st.subheader("Como os indicadores foram construídos")
    st.latex(r"I_{r,t}=100\,\frac{X_{r,t}}{X_{r,2016}},\qquad\overline{I}_t=\frac{1}{24}\sum_{r=1}^{24}I_{r,t}")
    st.caption("Primeiro se calcula o índice de cada TRT; depois se obtém a média entre tribunais. IAD e TCL são apresentados em seus percentuais originais.")
    key = st.selectbox("Indicador para visualizar", list(INDICATORS), format_func=INDICATORS.get, key="productivity_indicator")
    statistic = st.radio("Linha do gráfico", ["Média", "Mediana"], horizontal=True, key="productivity_statistic")
    percentage = key in {"iad_pct", "tcl_pct"}
    frame = data["prod_percentuais" if percentage else "prod_indices"]
    frame = frame[frame.indicador_raw.eq(key)].sort_values("ano")
    suffix = "pct" if percentage else "indice"
    center = ("media_" if statistic == "Média" else "mediana_") + suffix
    spec = {"title": "Figura de apoio — " + INDICATORS[key], "ylabel": "Percentual (%)" if percentage else "Índice (2016 = 100)",
            "lines": [line(statistic + " dos 24 TRTs", frame.ano, frame[center], lower=frame["p25_" + suffix], upper=frame["p75_" + suffix])],
            "range": None, "zero": False, "reference": None if percentage else 100, "filename": "apoio_produtividade_" + key + ("_media" if statistic == "Média" else "_mediana"),
            "note": "Faixa: percentis 25 e 75 entre tribunais; descreve dispersão, não intervalo de confiança."}
    if key == "dpj_real_dez2024":spec["note"] += " DPJ corrigida pelo IPCA, dez./2024."
    chart(spec, "prod_chart")
    if key.startswith("dpj_por_"):
        st.info("Este indicador utiliza despesa nominal. Sua evolução incorpora a variação dos preços e não mede, isoladamente, aumento real de custo ou perda de eficiência.")
    with st.expander("Indicadores de intensidade do gasto"):
        nominal = data["prod_variacao"].query("dimensao == 'Intensidade de gasto'")
        st.dataframe(nominal[["indicador", "variacao_media_pct", "variacao_mediana_pct"]].rename(columns={"indicador": "Indicador nominal", "variacao_media_pct": "Variação média (%)", "variacao_mediana_pct": "Mediana (%)"}), hide_index=True, use_container_width=True)
    st.download_button("Baixar a Tabela 3", csv_bytes(table), "tabela_3_produtividade_2016_2024.csv", mime="text/csv")
    st.caption("A análise é descritiva. Os indicadores operacionais ajudam a examinar explicações alternativas, mas não identificam efeitos causais da restrição fiscal sobre a produtividade.")
