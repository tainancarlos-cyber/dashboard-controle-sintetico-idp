# ============================================================
# LIMITAÇÕES E ANÁLISE DE PRODUTIVIDADE DOS 24 TRTs
# Trajetórias relativas, produtividade, carga e resultado
# ============================================================
#
# OBJETIVO
# Verificar, de forma descritiva, se a trajetória da despesa dos
# Tribunais Regionais do Trabalho pode estar associada a mudanças:
#   1) na escala da força de trabalho;
#   2) no volume da demanda e da produção processual;
#   3) na produtividade de servidores e magistrados;
#   4) na carga de trabalho;
#   5) no atendimento à demanda e no congestionamento.
#
# UNIDADES ANALISADAS
# Apenas TRT1 a TRT24. O TST e todos os demais tribunais são excluídos.
#
# INDICADORES PRINCIPAIS
#   DPJ       - Despesa total
#   FTT       - Força de trabalho total de servidores e magistrados
#   CN1/CN2   - Casos novos no primeiro e no segundo graus
#   TBaix1/2  - Processos baixados no primeiro e no segundo graus
#   CP1/CP2   - Casos pendentes no primeiro e no segundo graus
#   IPSJud    - Produtividade dos servidores da área judiciária
#   IPM       - Produtividade dos magistrados
#   KS        - Carga de trabalho por servidor da área judiciária
#   K         - Carga de trabalho dos magistrados
#   IAD       - Processos baixados por caso novo
#   TCL       - Taxa de congestionamento líquida
#
# ESTRATÉGIA
# - Para variáveis de escala, produtividade e carga, cada TRT é
#   normalizado por seu próprio valor de 2016: índice 2016 = 100.
# - IAD e TCL permanecem em seus percentuais originais.
# - Cada TRT tem o mesmo peso nas médias e medianas agregadas.
# - O script NÃO estabelece causalidade. Ele fornece evidência
#   descritiva complementar ao Controle Sintético.
#
# PRODUTOS GERADOS
# - gráficos em PNG;
# - planilha XLSX com todas as bases e tabelas;
# - arquivos CSV intermediários;
# - um arquivo TXT completo com diagnósticos e resultados.
# ============================================================

rm(list = ls())

# ------------------------------------------------------------
# 1. Pacotes
# ------------------------------------------------------------

pacotes <- c(
  "tidyverse",
  "readxl",
  "readr",
  "janitor",
  "writexl",
  "scales"
)

instalar <- pacotes[!pacotes %in% rownames(installed.packages())]

if (length(instalar) > 0) {
  install.packages(instalar)
}

suppressPackageStartupMessages({
  library(tidyverse)
  library(readxl)
  library(readr)
  library(janitor)
  library(writexl)
  library(scales)
})

options(
  scipen = 999,
  dplyr.summarise.inform = FALSE
)

# ------------------------------------------------------------
# 2. Configurações
# ------------------------------------------------------------

arquivo_entrada <- enc2utf8(
  "C:/Users/tst/OneDrive/Área de Trabalho/Meus Phytons/Arigo IDP/23-jun-2026/JN_23-Jun-2026.csv"
)

if (!file.exists(arquivo_entrada)) {
  arquivo_entrada <- file.choose()
}

aba_excel <- 1

pasta_saida <- enc2utf8(
  "C:/Users/tst/OneDrive/Área de Trabalho/Meus Phytons/Arigo IDP"
)

pasta_produtividade <- file.path(
  pasta_saida,
  "Analise_Produtividade_24_TRTs"
)

dir.create(
  pasta_produtividade,
  recursive = TRUE,
  showWarnings = FALSE
)

ano_inicial <- 2010
ano_final <- 2024
ano_base <- 2016
ano_tratamento <- 2017

anos_desejados <- ano_inicial:ano_final
trts_esperados <- paste0("TRT", 1:24)

# IMPORTANTE:
# Mantenha TRUE somente se a coluna DPJ já estiver expressa em valores reais,
# isto é, deflacionados para preços de um mesmo ano.
dpj_em_valores_reais <- TRUE

# Tolerância usada apenas na interpretação automática.
# Variações entre -5% e +5% são descritas como aproximadamente estáveis.
tolerancia_estabilidade_pct <- 5

# ------------------------------------------------------------
# 3. Funções auxiliares
# ------------------------------------------------------------

ler_base <- function(arquivo, aba = 1) {
  extensao <- tolower(tools::file_ext(arquivo))

  if (extensao %in% c("xlsx", "xls")) {
    return(readxl::read_excel(arquivo, sheet = aba))
  }

  if (extensao == "csv") {
    return(
      readr::read_delim(
        file = arquivo,
        delim = ";",
        locale = readr::locale(
          encoding = "UTF-8",
          decimal_mark = ",",
          grouping_mark = "."
        ),
        col_types = readr::cols(.default = readr::col_character()),
        show_col_types = FALSE,
        trim_ws = TRUE
      )
    )
  }

  stop("Formato não reconhecido. Use arquivo .csv, .xlsx ou .xls.")
}

br_num <- function(x) {
  if (is.numeric(x)) {
    return(as.numeric(x))
  }

  texto <- stringr::str_trim(as.character(x))
  texto[texto %in% c("", "NA", "N/A", "NULL", "null", "-", "...")] <- NA_character_

  readr::parse_number(
    texto,
    locale = readr::locale(
      decimal_mark = ",",
      grouping_mark = "."
    ),
    na = c("", "NA", "N/A", "NULL", "null", "-", "...")
  )
}

padronizar_sigla <- function(x) {
  original <- stringr::str_to_upper(as.character(x))
  limpo <- stringr::str_remove_all(original, "[^A-Z0-9]")

  numero <- stringr::str_match(limpo, "TRT0*([0-9]{1,2})")[, 2]
  numero_int <- suppressWarnings(as.integer(numero))

  dplyr::if_else(
    !is.na(numero_int) & numero_int >= 1 & numero_int <= 24,
    paste0("TRT", numero_int),
    limpo
  )
}

localizar_coluna <- function(base, candidatos, descricao, obrigatoria = TRUE) {
  candidatos_limpos <- janitor::make_clean_names(candidatos)
  encontrada <- candidatos_limpos[candidatos_limpos %in% names(base)]

  if (length(encontrada) > 0) {
    return(encontrada[1])
  }

  if (obrigatoria) {
    stop(
      paste0(
        "Não foi encontrada a coluna de ", descricao, ".\n",
        "Nomes procurados: ", paste(candidatos_limpos, collapse = ", "), ".\n\n",
        "Colunas disponíveis:\n",
        paste(names(base), collapse = ", ")
      )
    )
  }

  NA_character_
}

extrair_numero <- function(base, coluna) {
  if (length(coluna) == 0 || is.na(coluna) || !coluna %in% names(base)) {
    return(rep(NA_real_, nrow(base)))
  }

  br_num(base[[coluna]])
}

somar_componentes_completos <- function(x, y) {
  dplyr::if_else(
    !is.na(x) & !is.na(y),
    x + y,
    NA_real_
  )
}

converter_para_percentual <- function(x) {
  validos <- x[is.finite(x)]

  if (length(validos) == 0) {
    return(x)
  }

  p95 <- as.numeric(stats::quantile(abs(validos), 0.95, na.rm = TRUE))

  # Razões armazenadas como 0,85 ou 1,05 são convertidas para 85% e 105%.
  # Percentuais já armazenados como 85 ou 105 são mantidos.
  if (is.finite(p95) && p95 <= 5) {
    return(100 * x)
  }

  x
}

criar_periodo <- function(ano) {
  dplyr::case_when(
    ano <= 2016 ~ "Pré-EC 95 (2010-2016)",
    ano >= 2017 & ano <= 2022 ~ "Pós-EC 95 (2017-2022)",
    ano >= 2023 ~ "Novo arcabouço (2023-2024)",
    TRUE ~ NA_character_
  )
}

media_na <- function(x) {
  if (all(is.na(x))) return(NA_real_)
  mean(x, na.rm = TRUE)
}

mediana_na <- function(x) {
  if (all(is.na(x))) return(NA_real_)
  median(x, na.rm = TRUE)
}

quantil_na <- function(x, probabilidade) {
  if (all(is.na(x))) return(NA_real_)

  as.numeric(
    quantile(
      x,
      probs = probabilidade,
      na.rm = TRUE,
      names = FALSE
    )
  )
}

minimo_na <- function(x) {
  if (all(is.na(x))) return(NA_real_)
  min(x, na.rm = TRUE)
}

maximo_na <- function(x) {
  if (all(is.na(x))) return(NA_real_)
  max(x, na.rm = TRUE)
}

cor_spearman_segura <- function(x, y) {
  completos <- stats::complete.cases(x, y)
  x2 <- x[completos]
  y2 <- y[completos]

  if (
    length(x2) < 5 ||
    length(unique(x2)) < 2 ||
    length(unique(y2)) < 2
  ) {
    return(NA_real_)
  }

  suppressWarnings(stats::cor(x2, y2, method = "spearman"))
}

n_pares_completos <- function(x, y) {
  sum(stats::complete.cases(x, y))
}

formatar_numero <- function(x, casas = 2) {
  ifelse(
    is.na(x),
    "NA",
    formatC(x, format = "f", digits = casas, decimal.mark = ",", big.mark = ".")
  )
}

classificar_variacao <- function(x, tolerancia = 5) {
  if (is.na(x)) return("não pôde ser calculada")
  if (x > tolerancia) return("aumentou")
  if (x < -tolerancia) return("diminuiu")
  "permaneceu aproximadamente estável"
}

capturar_tabela <- function(titulo, objeto) {
  c(
    "",
    paste0("============================================================"),
    titulo,
    paste0("============================================================"),
    capture.output(print(objeto, n = Inf, width = Inf))
  )
}

# ------------------------------------------------------------
# 4. Importar e limpar a base
# ------------------------------------------------------------

base_raw <- ler_base(arquivo_entrada, aba_excel) |>
  janitor::clean_names()

cat("\n====================================================\n")
cat("COLUNAS ENCONTRADAS NA BASE\n")
cat("====================================================\n")
print(names(base_raw))

# ------------------------------------------------------------
# 5. Localizar as variáveis
# ------------------------------------------------------------

col_ano <- localizar_coluna(base_raw, c("ano"), "ano")
col_sigla <- localizar_coluna(base_raw, c("sigla"), "sigla do tribunal")
col_dpj <- localizar_coluna(base_raw, c("dpj"), "despesa total - DPJ")
col_ftt <- localizar_coluna(base_raw, c("ftt"), "força de trabalho total - FTT")

col_cn1 <- localizar_coluna(base_raw, c("cn1"), "casos novos do primeiro grau - CN1")
col_cn2 <- localizar_coluna(base_raw, c("cn2"), "casos novos do segundo grau - CN2")

col_tbaix <- localizar_coluna(
  base_raw,
  c("tbaix"),
  "total agregado de processos baixados - TBaix",
  obrigatoria = FALSE
)
col_tbaix1 <- localizar_coluna(base_raw, c("tbaix1"), "processos baixados do primeiro grau - TBaix1")
col_tbaix2 <- localizar_coluna(base_raw, c("tbaix2"), "processos baixados do segundo grau - TBaix2")

col_cp1 <- localizar_coluna(
  base_raw,
  c("cp1"),
  "casos pendentes do primeiro grau - CP1",
  obrigatoria = FALSE
)
col_cp2 <- localizar_coluna(
  base_raw,
  c("cp2"),
  "casos pendentes do segundo grau - CP2",
  obrigatoria = FALSE
)

col_ipsjud <- localizar_coluna(base_raw, c("ipsjud"), "produtividade dos servidores - IPSJud")
col_ipm <- localizar_coluna(base_raw, c("ipm"), "produtividade dos magistrados - IPM")
col_ks <- localizar_coluna(base_raw, c("ks"), "carga de trabalho dos servidores - KS")
col_k <- localizar_coluna(
  base_raw,
  c("k"),
  "carga de trabalho dos magistrados - K",
  obrigatoria = FALSE
)
col_iad <- localizar_coluna(base_raw, c("iad"), "índice de atendimento à demanda - IAD")
col_tcl <- localizar_coluna(base_raw, c("tcl"), "taxa de congestionamento líquida - TCL")

colunas_selecionadas <- tibble::tibble(
  variavel = c(
    "Ano", "Sigla", "DPJ", "FTT", "CN1", "CN2",
    "TBaix agregado", "TBaix1", "TBaix2", "CP1", "CP2",
    "IPSJud", "IPM", "KS", "K", "IAD", "TCL"
  ),
  coluna_encontrada = c(
    col_ano, col_sigla, col_dpj, col_ftt, col_cn1, col_cn2,
    col_tbaix, col_tbaix1, col_tbaix2, col_cp1, col_cp2,
    col_ipsjud, col_ipm, col_ks, col_k, col_iad, col_tcl
  )
)

cat("\n====================================================\n")
cat("COLUNAS SELECIONADAS PELO CÓDIGO\n")
cat("====================================================\n")
print(colunas_selecionadas, n = Inf)

# ------------------------------------------------------------
# 6. Construir base mínima
# ------------------------------------------------------------

base_minima <- tibble::tibble(
  ano = as.integer(extrair_numero(base_raw, col_ano)),
  sigla = padronizar_sigla(base_raw[[col_sigla]]),
  dpj = extrair_numero(base_raw, col_dpj),
  ftt = extrair_numero(base_raw, col_ftt),
  cn1 = extrair_numero(base_raw, col_cn1),
  cn2 = extrair_numero(base_raw, col_cn2),
  tbaix_agregado = extrair_numero(base_raw, col_tbaix),
  tbaix1 = extrair_numero(base_raw, col_tbaix1),
  tbaix2 = extrair_numero(base_raw, col_tbaix2),
  cp1 = extrair_numero(base_raw, col_cp1),
  cp2 = extrair_numero(base_raw, col_cp2),
  ipsjud = extrair_numero(base_raw, col_ipsjud),
  ipm = extrair_numero(base_raw, col_ipm),
  ks = extrair_numero(base_raw, col_ks),
  k = extrair_numero(base_raw, col_k),
  iad_informado = extrair_numero(base_raw, col_iad),
  tcl_informado = extrair_numero(base_raw, col_tcl)
) |>
  dplyr::filter(ano %in% anos_desejados)

# ------------------------------------------------------------
# 7. Filtrar exclusivamente TRT1 a TRT24
# ------------------------------------------------------------

base_filtrada <- base_minima |>
  dplyr::filter(sigla %in% trts_esperados)

# Não somar silenciosamente linhas duplicadas. Isso poderia duplicar
# servidores, processos ou despesas.
duplicidades <- base_filtrada |>
  dplyr::count(sigla, ano, name = "numero_linhas") |>
  dplyr::filter(numero_linhas > 1)

if (nrow(duplicidades) > 0) {
  print(duplicidades, n = Inf)
  stop(
    paste0(
      "Foram encontradas combinações TRT/ano duplicadas. ",
      "O código foi interrompido para evitar somas indevidas."
    )
  )
}

base_trts <- base_filtrada |>
  tidyr::complete(
    sigla = trts_esperados,
    ano = anos_desejados
  ) |>
  dplyr::arrange(sigla, ano) |>
  dplyr::mutate(
    casos_novos = somar_componentes_completos(cn1, cn2),
    processos_baixados_componentes = somar_componentes_completos(tbaix1, tbaix2),
    processos_baixados = dplyr::coalesce(
      tbaix_agregado,
      processos_baixados_componentes
    ),
    casos_pendentes = somar_componentes_completos(cp1, cp2),

    iad_informado_pct = converter_para_percentual(iad_informado),
    iad_calculado_pct = dplyr::if_else(
      !is.na(casos_novos) & casos_novos > 0 & !is.na(processos_baixados),
      100 * processos_baixados / casos_novos,
      NA_real_
    ),
    iad_pct = dplyr::coalesce(iad_informado_pct, iad_calculado_pct),
    tcl_pct = converter_para_percentual(tcl_informado),

    dpj_por_processo_baixado = dplyr::if_else(
      !is.na(processos_baixados) & processos_baixados > 0,
      dpj / processos_baixados,
      NA_real_
    ),
    dpj_por_forca_trabalho = dplyr::if_else(
      !is.na(ftt) & ftt > 0,
      dpj / ftt,
      NA_real_
    ),
    periodo = criar_periodo(ano)
  )

# ------------------------------------------------------------
# 8. Diagnósticos de qualidade e cobertura
# ------------------------------------------------------------

trts_encontrados <- sort(unique(base_filtrada$sigla))
trts_ausentes_na_base <- setdiff(trts_esperados, trts_encontrados)

painel_esperado <- length(trts_esperados) * length(anos_desejados)
painel_com_linha_original <- nrow(base_filtrada)

comparacao_tbaix <- base_trts |>
  dplyr::filter(
    !is.na(tbaix_agregado),
    !is.na(processos_baixados_componentes),
    processos_baixados_componentes != 0
  ) |>
  dplyr::mutate(
    diferenca_absoluta = tbaix_agregado - processos_baixados_componentes,
    diferenca_pct = 100 * diferenca_absoluta / processos_baixados_componentes
  ) |>
  dplyr::select(
    sigla,
    ano,
    tbaix_agregado,
    processos_baixados_componentes,
    diferenca_absoluta,
    diferenca_pct
  )

variaveis_diagnostico <- c(
  "dpj", "ftt", "cn1", "cn2", "casos_novos",
  "tbaix_agregado", "tbaix1", "tbaix2", "processos_baixados",
  "cp1", "cp2", "casos_pendentes", "ipsjud", "ipm", "ks", "k",
  "iad_pct", "tcl_pct", "dpj_por_processo_baixado", "dpj_por_forca_trabalho"
)

diagnostico_geral <- base_trts |>
  dplyr::select(sigla, ano, dplyr::all_of(variaveis_diagnostico)) |>
  tidyr::pivot_longer(
    cols = -c(sigla, ano),
    names_to = "variavel",
    values_to = "valor"
  ) |>
  dplyr::group_by(variavel) |>
  dplyr::summarise(
    observacoes_esperadas = dplyr::n(),
    observacoes_validas = sum(!is.na(valor)),
    observacoes_ausentes = sum(is.na(valor)),
    cobertura_pct = 100 * observacoes_validas / observacoes_esperadas,
    trts_com_algum_dado = dplyr::n_distinct(sigla[!is.na(valor)]),
    anos_com_algum_dado = dplyr::n_distinct(ano[!is.na(valor)]),
    .groups = "drop"
  ) |>
  dplyr::arrange(variavel)

diagnostico_por_ano <- base_trts |>
  dplyr::select(sigla, ano, dplyr::all_of(variaveis_diagnostico)) |>
  tidyr::pivot_longer(
    cols = -c(sigla, ano),
    names_to = "variavel",
    values_to = "valor"
  ) |>
  dplyr::group_by(ano, variavel) |>
  dplyr::summarise(
    n_trts_validos = sum(!is.na(valor)),
    .groups = "drop"
  ) |>
  dplyr::arrange(variavel, ano)

# ------------------------------------------------------------
# 9. Base longa para índices 2016 = 100
# ------------------------------------------------------------

rotulo_dpj <- ifelse(
  dpj_em_valores_reais,
  "Despesa total real - DPJ",
  "Despesa total nominal - DPJ"
)

mapa_indicadores_indice <- tibble::tribble(
  ~indicador_raw,                  ~indicador,                                      ~dimensao,
  "dpj",                           rotulo_dpj,                                      "Escala e despesa",
  "ftt",                           "Força de trabalho total - FTT",                 "Escala e despesa",
  "casos_novos",                   "Casos novos - primeiro e segundo graus",        "Escala e despesa",
  "processos_baixados",            "Processos baixados - primeiro e segundo graus", "Escala e despesa",
  "casos_pendentes",               "Casos pendentes - primeiro e segundo graus",    "Escala e despesa",
  "ipsjud",                        "Produtividade dos servidores - IPSJud",          "Produtividade e carga",
  "ipm",                           "Produtividade dos magistrados - IPM",            "Produtividade e carga",
  "ks",                            "Carga de trabalho por servidor - KS",            "Produtividade e carga",
  "k",                             "Carga de trabalho dos magistrados - K",          "Produtividade e carga",
  "dpj_por_processo_baixado",      "Despesa por processo baixado",                  "Intensidade de gasto",
  "dpj_por_forca_trabalho",        "Despesa por integrante da força de trabalho",   "Intensidade de gasto"
)

base_longa_indice <- base_trts |>
  dplyr::select(
    sigla,
    ano,
    periodo,
    dplyr::all_of(mapa_indicadores_indice$indicador_raw)
  ) |>
  tidyr::pivot_longer(
    cols = -c(sigla, ano, periodo),
    names_to = "indicador_raw",
    values_to = "valor"
  ) |>
  dplyr::left_join(mapa_indicadores_indice, by = "indicador_raw")

base_2016 <- base_longa_indice |>
  dplyr::filter(ano == ano_base) |>
  dplyr::select(
    sigla,
    indicador_raw,
    valor_base_2016 = valor
  )

base_indices <- base_longa_indice |>
  dplyr::left_join(
    base_2016,
    by = c("sigla", "indicador_raw")
  ) |>
  dplyr::mutate(
    indice_2016 = dplyr::if_else(
      !is.na(valor_base_2016) & valor_base_2016 != 0,
      100 * valor / valor_base_2016,
      NA_real_
    ),
    variacao_pct_desde_2016 = indice_2016 - 100
  ) |>
  dplyr::arrange(indicador_raw, sigla, ano)

checagem_base_2016 <- base_indices |>
  dplyr::filter(is.na(valor_base_2016) | valor_base_2016 == 0) |>
  dplyr::distinct(sigla, indicador_raw, indicador, valor_base_2016) |>
  dplyr::arrange(indicador, sigla)

# ------------------------------------------------------------
# 10. Resumo anual dos índices
# ------------------------------------------------------------

resumo_anual_indices <- base_indices |>
  dplyr::group_by(
    ano,
    periodo,
    dimensao,
    indicador_raw,
    indicador
  ) |>
  dplyr::summarise(
    n_trts = sum(!is.na(indice_2016)),
    media_indice = media_na(indice_2016),
    mediana_indice = mediana_na(indice_2016),
    p25_indice = quantil_na(indice_2016, 0.25),
    p75_indice = quantil_na(indice_2016, 0.75),
    minimo_indice = minimo_na(indice_2016),
    maximo_indice = maximo_na(indice_2016),
    .groups = "drop"
  ) |>
  dplyr::arrange(dimensao, indicador, ano)

# ------------------------------------------------------------
# 11. Variação de 2016 a 2024
# ------------------------------------------------------------

variacao_2016_2024_individual <- base_indices |>
  dplyr::filter(ano == ano_final) |>
  dplyr::select(
    sigla,
    dimensao,
    indicador_raw,
    indicador,
    valor_base_2016,
    valor_2024 = valor,
    indice_2024 = indice_2016,
    variacao_pct_2016_2024 = variacao_pct_desde_2016
  ) |>
  dplyr::arrange(dimensao, indicador, sigla)

resumo_variacao_2016_2024 <- variacao_2016_2024_individual |>
  dplyr::group_by(dimensao, indicador_raw, indicador) |>
  dplyr::summarise(
    n_trts = sum(!is.na(variacao_pct_2016_2024)),
    variacao_media_pct = media_na(variacao_pct_2016_2024),
    variacao_mediana_pct = mediana_na(variacao_pct_2016_2024),
    p25_variacao_pct = quantil_na(variacao_pct_2016_2024, 0.25),
    p75_variacao_pct = quantil_na(variacao_pct_2016_2024, 0.75),
    minimo_variacao_pct = minimo_na(variacao_pct_2016_2024),
    maximo_variacao_pct = maximo_na(variacao_pct_2016_2024),
    .groups = "drop"
  ) |>
  dplyr::arrange(dimensao, indicador)

# ------------------------------------------------------------
# 12. Resumo por período dos índices
# Primeiro calcula a média de cada TRT no período; depois agrega
# os TRTs com o mesmo peso.
# ------------------------------------------------------------

media_trt_periodo_indices <- base_indices |>
  dplyr::filter(!is.na(periodo)) |>
  dplyr::group_by(
    sigla,
    periodo,
    dimensao,
    indicador_raw,
    indicador
  ) |>
  dplyr::summarise(
    indice_medio_trt_periodo = media_na(indice_2016),
    anos_validos = sum(!is.na(indice_2016)),
    .groups = "drop"
  )

resumo_periodo_indices <- media_trt_periodo_indices |>
  dplyr::group_by(periodo, dimensao, indicador_raw, indicador) |>
  dplyr::summarise(
    n_trts = sum(!is.na(indice_medio_trt_periodo)),
    indice_medio = media_na(indice_medio_trt_periodo),
    indice_mediano = mediana_na(indice_medio_trt_periodo),
    p25_indice = quantil_na(indice_medio_trt_periodo, 0.25),
    p75_indice = quantil_na(indice_medio_trt_periodo, 0.75),
    .groups = "drop"
  ) |>
  dplyr::arrange(dimensao, indicador, periodo)

# ------------------------------------------------------------
# 13. IAD e TCL em níveis percentuais
# ------------------------------------------------------------

mapa_taxas <- tibble::tribble(
  ~indicador_raw, ~indicador,
  "iad_pct",      "Índice de atendimento à demanda - IAD (%)",
  "tcl_pct",      "Taxa de congestionamento líquida - TCL (%)"
)

base_taxas <- base_trts |>
  dplyr::select(sigla, ano, periodo, iad_pct, tcl_pct) |>
  tidyr::pivot_longer(
    cols = c(iad_pct, tcl_pct),
    names_to = "indicador_raw",
    values_to = "valor_percentual"
  ) |>
  dplyr::left_join(mapa_taxas, by = "indicador_raw")

resumo_anual_taxas <- base_taxas |>
  dplyr::group_by(ano, periodo, indicador_raw, indicador) |>
  dplyr::summarise(
    n_trts = sum(!is.na(valor_percentual)),
    media_pct = media_na(valor_percentual),
    mediana_pct = mediana_na(valor_percentual),
    p25_pct = quantil_na(valor_percentual, 0.25),
    p75_pct = quantil_na(valor_percentual, 0.75),
    minimo_pct = minimo_na(valor_percentual),
    maximo_pct = maximo_na(valor_percentual),
    .groups = "drop"
  ) |>
  dplyr::arrange(indicador, ano)

variacao_taxas_2016_2024_individual <- base_taxas |>
  dplyr::filter(ano %in% c(ano_base, ano_final)) |>
  dplyr::select(sigla, indicador_raw, indicador, ano, valor_percentual) |>
  tidyr::pivot_wider(
    names_from = ano,
    values_from = valor_percentual,
    names_prefix = "ano_"
  ) |>
  dplyr::mutate(
    variacao_pontos_percentuais = .data[[paste0("ano_", ano_final)]] -
      .data[[paste0("ano_", ano_base)]]
  ) |>
  dplyr::arrange(indicador, sigla)

resumo_variacao_taxas_2016_2024 <- variacao_taxas_2016_2024_individual |>
  dplyr::group_by(indicador_raw, indicador) |>
  dplyr::summarise(
    n_trts = sum(!is.na(variacao_pontos_percentuais)),
    variacao_media_pp = media_na(variacao_pontos_percentuais),
    variacao_mediana_pp = mediana_na(variacao_pontos_percentuais),
    p25_variacao_pp = quantil_na(variacao_pontos_percentuais, 0.25),
    p75_variacao_pp = quantil_na(variacao_pontos_percentuais, 0.75),
    minimo_variacao_pp = minimo_na(variacao_pontos_percentuais),
    maximo_variacao_pp = maximo_na(variacao_pontos_percentuais),
    .groups = "drop"
  ) |>
  dplyr::arrange(indicador)

media_trt_periodo_taxas <- base_taxas |>
  dplyr::group_by(sigla, periodo, indicador_raw, indicador) |>
  dplyr::summarise(
    media_pct_trt_periodo = media_na(valor_percentual),
    anos_validos = sum(!is.na(valor_percentual)),
    .groups = "drop"
  )

resumo_periodo_taxas <- media_trt_periodo_taxas |>
  dplyr::group_by(periodo, indicador_raw, indicador) |>
  dplyr::summarise(
    n_trts = sum(!is.na(media_pct_trt_periodo)),
    media_pct = media_na(media_pct_trt_periodo),
    mediana_pct = mediana_na(media_pct_trt_periodo),
    p25_pct = quantil_na(media_pct_trt_periodo, 0.25),
    p75_pct = quantil_na(media_pct_trt_periodo, 0.75),
    .groups = "drop"
  ) |>
  dplyr::arrange(indicador, periodo)

# ------------------------------------------------------------
# 14. Correlações descritivas das variações anuais
# Não são testes de causalidade.
# ------------------------------------------------------------

base_variacoes_anuais <- base_trts |>
  dplyr::group_by(sigla) |>
  dplyr::arrange(ano, .by_group = TRUE) |>
  dplyr::mutate(
    var_dpj_pct = 100 * (dpj / dplyr::lag(dpj) - 1),
    var_ftt_pct = 100 * (ftt / dplyr::lag(ftt) - 1),
    var_casos_novos_pct = 100 * (casos_novos / dplyr::lag(casos_novos) - 1),
    var_processos_baixados_pct = 100 * (processos_baixados / dplyr::lag(processos_baixados) - 1),
    var_ipsjud_pct = 100 * (ipsjud / dplyr::lag(ipsjud) - 1),
    var_ipm_pct = 100 * (ipm / dplyr::lag(ipm) - 1),
    var_ks_pct = 100 * (ks / dplyr::lag(ks) - 1),
    var_k_pct = 100 * (k / dplyr::lag(k) - 1),
    var_iad_pp = iad_pct - dplyr::lag(iad_pct),
    var_tcl_pp = tcl_pct - dplyr::lag(tcl_pct)
  ) |>
  dplyr::ungroup()

variaveis_correlacao <- tibble::tribble(
  ~variavel_raw,                     ~variavel,
  "var_ftt_pct",                     "Variação anual da força de trabalho - FTT",
  "var_casos_novos_pct",             "Variação anual dos casos novos",
  "var_processos_baixados_pct",      "Variação anual dos processos baixados",
  "var_ipsjud_pct",                  "Variação anual da produtividade dos servidores - IPSJud",
  "var_ipm_pct",                     "Variação anual da produtividade dos magistrados - IPM",
  "var_ks_pct",                      "Variação anual da carga por servidor - KS",
  "var_k_pct",                       "Variação anual da carga dos magistrados - K",
  "var_iad_pp",                      "Variação anual do IAD em pontos percentuais",
  "var_tcl_pp",                      "Variação anual da TCL em pontos percentuais"
)

correlacoes_variacoes_anuais <- purrr::map_dfr(
  seq_len(nrow(variaveis_correlacao)),
  function(i) {
    nome_raw <- variaveis_correlacao$variavel_raw[i]
    nome_rotulo <- variaveis_correlacao$variavel[i]

    tibble::tibble(
      variavel = nome_rotulo,
      n_pares = n_pares_completos(
        base_variacoes_anuais$var_dpj_pct,
        base_variacoes_anuais[[nome_raw]]
      ),
      correlacao_spearman = cor_spearman_segura(
        base_variacoes_anuais$var_dpj_pct,
        base_variacoes_anuais[[nome_raw]]
      )
    )
  }
) |>
  dplyr::arrange(dplyr::desc(abs(correlacao_spearman)))

# ------------------------------------------------------------
# 15. Tabelas prontas para interpretação
# ------------------------------------------------------------

tabela_principal_2016_2024 <- resumo_variacao_2016_2024 |>
  dplyr::select(
    dimensao,
    indicador,
    n_trts,
    variacao_media_pct,
    variacao_mediana_pct,
    p25_variacao_pct,
    p75_variacao_pct,
    minimo_variacao_pct,
    maximo_variacao_pct
  ) |>
  dplyr::mutate(
    dplyr::across(
      where(is.numeric) & !matches("n_trts"),
      ~ round(.x, 2)
    )
  )

tabela_taxas_2016_2024 <- resumo_variacao_taxas_2016_2024 |>
  dplyr::mutate(
    dplyr::across(
      where(is.numeric) & !matches("n_trts"),
      ~ round(.x, 2)
    )
  )

tabela_correlacoes <- correlacoes_variacoes_anuais |>
  dplyr::mutate(
    correlacao_spearman = round(correlacao_spearman, 3)
  )

# ------------------------------------------------------------
# 16. Gráficos
# ------------------------------------------------------------

indicadores_escala_principais <- c(
  rotulo_dpj,
  "Força de trabalho total - FTT",
  "Casos novos - primeiro e segundo graus",
  "Processos baixados - primeiro e segundo graus"
)

indicadores_produtividade_carga <- c(
  "Produtividade dos servidores - IPSJud",
  "Produtividade dos magistrados - IPM",
  "Carga de trabalho por servidor - KS",
  "Carga de trabalho dos magistrados - K"
)

indicadores_intensidade <- c(
  "Despesa por processo baixado",
  "Despesa por integrante da força de trabalho"
)

# 16.1 Escala e despesa: média dos índices
g1_escala <- resumo_anual_indices |>
  dplyr::filter(indicador %in% indicadores_escala_principais) |>
  ggplot2::ggplot(
    ggplot2::aes(
      x = ano,
      y = media_indice,
      linetype = indicador
    )
  ) +
  ggplot2::geom_line(linewidth = 1.05, na.rm = TRUE) +
  ggplot2::geom_hline(yintercept = 100, linetype = "dotted") +
  ggplot2::geom_vline(xintercept = ano_tratamento, linetype = "dashed") +
  ggplot2::scale_x_continuous(breaks = anos_desejados) +
  ggplot2::labs(
    title = "Despesa, força de trabalho e atividade processual dos 24 TRTs",
    subtitle = "Média dos índices relativos; cada TRT foi normalizado por seu valor em 2016",
    x = "Ano",
    y = "Índice médio dos TRTs — 2016 = 100",
    linetype = "Indicador"
  ) +
  ggplot2::theme_minimal(base_size = 12) +
  ggplot2::theme(axis.text.x = ggplot2::element_text(angle = 45, hjust = 1))

ggplot2::ggsave(
  filename = file.path(pasta_produtividade, "01_escala_despesa_atividade.png"),
  plot = g1_escala,
  width = 14,
  height = 8,
  dpi = 300
)

# 16.2 Produtividade e carga: mediana e intervalo interquartil
g2_produtividade <- resumo_anual_indices |>
  dplyr::filter(indicador %in% indicadores_produtividade_carga) |>
  ggplot2::ggplot(ggplot2::aes(x = ano, y = mediana_indice)) +
  ggplot2::geom_ribbon(
    ggplot2::aes(ymin = p25_indice, ymax = p75_indice),
    alpha = 0.20,
    na.rm = TRUE
  ) +
  ggplot2::geom_line(linewidth = 1.05, na.rm = TRUE) +
  ggplot2::geom_hline(yintercept = 100, linetype = "dotted") +
  ggplot2::geom_vline(xintercept = ano_tratamento, linetype = "dashed") +
  ggplot2::facet_wrap(~ indicador, scales = "free_y", ncol = 2) +
  ggplot2::scale_x_continuous(breaks = anos_desejados) +
  ggplot2::labs(
    title = "Produtividade e carga de trabalho dos 24 TRTs",
    subtitle = "Linha: mediana; faixa: intervalo interquartil; índice 2016 = 100",
    x = "Ano",
    y = "Índice 2016 = 100"
  ) +
  ggplot2::theme_minimal(base_size = 12) +
  ggplot2::theme(axis.text.x = ggplot2::element_text(angle = 45, hjust = 1))

ggplot2::ggsave(
  filename = file.path(pasta_produtividade, "02_produtividade_carga.png"),
  plot = g2_produtividade,
  width = 14,
  height = 9,
  dpi = 300
)

# 16.3 IAD e TCL em percentuais
referencias_taxas <- tibble::tibble(
  indicador = "Índice de atendimento à demanda - IAD (%)",
  referencia = 100
)

g3_taxas <- resumo_anual_taxas |>
  ggplot2::ggplot(ggplot2::aes(x = ano, y = mediana_pct)) +
  ggplot2::geom_ribbon(
    ggplot2::aes(ymin = p25_pct, ymax = p75_pct),
    alpha = 0.20,
    na.rm = TRUE
  ) +
  ggplot2::geom_line(linewidth = 1.05, na.rm = TRUE) +
  ggplot2::geom_hline(
    data = referencias_taxas,
    ggplot2::aes(yintercept = referencia),
    linetype = "dotted",
    inherit.aes = FALSE
  ) +
  ggplot2::geom_vline(xintercept = ano_tratamento, linetype = "dashed") +
  ggplot2::facet_wrap(~ indicador, scales = "free_y", ncol = 1) +
  ggplot2::scale_x_continuous(breaks = anos_desejados) +
  ggplot2::labs(
    title = "Atendimento à demanda e congestionamento dos 24 TRTs",
    subtitle = "Linha: mediana; faixa: intervalo interquartil; valores em percentual",
    x = "Ano",
    y = "Percentual"
  ) +
  ggplot2::theme_minimal(base_size = 12) +
  ggplot2::theme(axis.text.x = ggplot2::element_text(angle = 45, hjust = 1))

ggplot2::ggsave(
  filename = file.path(pasta_produtividade, "03_iad_tcl_percentuais.png"),
  plot = g3_taxas,
  width = 13,
  height = 9,
  dpi = 300
)

# 16.4 Intensidade de gasto
g4_intensidade <- resumo_anual_indices |>
  dplyr::filter(indicador %in% indicadores_intensidade) |>
  ggplot2::ggplot(
    ggplot2::aes(
      x = ano,
      y = media_indice,
      linetype = indicador
    )
  ) +
  ggplot2::geom_line(linewidth = 1.05, na.rm = TRUE) +
  ggplot2::geom_hline(yintercept = 100, linetype = "dotted") +
  ggplot2::geom_vline(xintercept = ano_tratamento, linetype = "dashed") +
  ggplot2::scale_x_continuous(breaks = anos_desejados) +
  ggplot2::labs(
    title = "Intensidade relativa de gasto dos 24 TRTs",
    subtitle = "Despesa por processo baixado e por integrante da força de trabalho; 2016 = 100",
    x = "Ano",
    y = "Índice médio dos TRTs — 2016 = 100",
    linetype = "Indicador"
  ) +
  ggplot2::theme_minimal(base_size = 12) +
  ggplot2::theme(axis.text.x = ggplot2::element_text(angle = 45, hjust = 1))

ggplot2::ggsave(
  filename = file.path(pasta_produtividade, "04_intensidade_gasto.png"),
  plot = g4_intensidade,
  width = 13,
  height = 8,
  dpi = 300
)

# 16.5 Trajetórias individuais dos TRTs
g5_individuais <- base_indices |>
  dplyr::filter(indicador %in% c(
    rotulo_dpj,
    "Força de trabalho total - FTT",
    "Processos baixados - primeiro e segundo graus",
    "Produtividade dos servidores - IPSJud"
  )) |>
  ggplot2::ggplot(
    ggplot2::aes(
      x = ano,
      y = indice_2016,
      group = sigla
    )
  ) +
  ggplot2::geom_line(alpha = 0.40, linewidth = 0.65, na.rm = TRUE) +
  ggplot2::geom_hline(yintercept = 100, linetype = "dotted") +
  ggplot2::geom_vline(xintercept = ano_tratamento, linetype = "dashed") +
  ggplot2::facet_wrap(~ indicador, scales = "free_y", ncol = 2) +
  ggplot2::scale_x_continuous(breaks = anos_desejados) +
  ggplot2::labs(
    title = "Trajetórias individuais relativas dos 24 TRTs",
    subtitle = "Cada linha representa um TRT; índice base 2016 = 100",
    x = "Ano",
    y = "Índice 2016 = 100"
  ) +
  ggplot2::theme_minimal(base_size = 12) +
  ggplot2::theme(axis.text.x = ggplot2::element_text(angle = 45, hjust = 1))

ggplot2::ggsave(
  filename = file.path(pasta_produtividade, "05_trajetorias_individuais.png"),
  plot = g5_individuais,
  width = 14,
  height = 10,
  dpi = 300
)

# ------------------------------------------------------------
# 17. Funções para extrair resultados da tabela principal
# ------------------------------------------------------------

pegar_variacao_media <- function(nome_raw) {
  valor <- resumo_variacao_2016_2024 |>
    dplyr::filter(indicador_raw == nome_raw) |>
    dplyr::pull(variacao_media_pct)

  if (length(valor) == 0) return(NA_real_)
  valor[1]
}

pegar_variacao_mediana <- function(nome_raw) {
  valor <- resumo_variacao_2016_2024 |>
    dplyr::filter(indicador_raw == nome_raw) |>
    dplyr::pull(variacao_mediana_pct)

  if (length(valor) == 0) return(NA_real_)
  valor[1]
}

pegar_variacao_taxa_media <- function(nome_raw) {
  valor <- resumo_variacao_taxas_2016_2024 |>
    dplyr::filter(indicador_raw == nome_raw) |>
    dplyr::pull(variacao_media_pp)

  if (length(valor) == 0) return(NA_real_)
  valor[1]
}

var_dpj <- pegar_variacao_media("dpj")
var_ftt <- pegar_variacao_media("ftt")
var_cn <- pegar_variacao_media("casos_novos")
var_tbaix <- pegar_variacao_media("processos_baixados")
var_cp <- pegar_variacao_media("casos_pendentes")
var_ipsjud <- pegar_variacao_media("ipsjud")
var_ipm <- pegar_variacao_media("ipm")
var_ks <- pegar_variacao_media("ks")
var_k <- pegar_variacao_media("k")
var_dpj_tbaix <- pegar_variacao_media("dpj_por_processo_baixado")
var_dpj_ftt <- pegar_variacao_media("dpj_por_forca_trabalho")
var_iad_pp <- pegar_variacao_taxa_media("iad_pct")
var_tcl_pp <- pegar_variacao_taxa_media("tcl_pct")

# ------------------------------------------------------------
# 18. Interpretação automática preliminar
# ------------------------------------------------------------

atividade_manteve_ou_cresceu <- !is.na(var_tbaix) && var_tbaix >= -tolerancia_estabilidade_pct
produtividade_servidores_manteve_ou_cresceu <- !is.na(var_ipsjud) && var_ipsjud >= -tolerancia_estabilidade_pct
produtividade_magistrados_manteve_ou_cresceu <- !is.na(var_ipm) && var_ipm >= -tolerancia_estabilidade_pct
forca_nao_expandiu_fortemente <- !is.na(var_ftt) && var_ftt <= tolerancia_estabilidade_pct

conclusao_automatica <- dplyr::case_when(
  atividade_manteve_ou_cresceu &
    produtividade_servidores_manteve_ou_cresceu &
    produtividade_magistrados_manteve_ou_cresceu ~
    paste0(
      "A evidência descritiva preliminar não é compatível com a explicação de que ",
      "a trajetória da despesa decorreu simplesmente de queda generalizada da atividade ",
      "ou da produtividade. Processos baixados e índices de produtividade permaneceram ",
      "estáveis ou aumentaram dentro da tolerância adotada."
    ),

  !atividade_manteve_ou_cresceu &
    (!produtividade_servidores_manteve_ou_cresceu ||
       !produtividade_magistrados_manteve_ou_cresceu) ~
    paste0(
      "A evidência descritiva mostra redução relevante da produção processual e de pelo ",
      "menos um indicador de produtividade. Assim, mudanças na escala ou no desempenho ",
      "podem ter contribuído para a trajetória da despesa e devem ser tratadas como limitação."
    ),

  TRUE ~
    paste0(
      "Os indicadores apresentam comportamento misto. Não é possível atribuir a trajetória ",
      "da despesa exclusivamente à produtividade, mas também não é possível descartar por ",
      "completo a influência de mudanças na escala ou no desempenho operacional."
    )
)

texto_interpretacao <- c(
  "INTERPRETAÇÃO AUTOMÁTICA PRELIMINAR",
  "",
  paste0(
    "Entre 2016 e 2024, a despesa total ",
    classificar_variacao(var_dpj, tolerancia_estabilidade_pct),
    " em média ", formatar_numero(var_dpj), "% entre os 24 TRTs."
  ),
  paste0(
    "A força de trabalho total ",
    classificar_variacao(var_ftt, tolerancia_estabilidade_pct),
    " em média ", formatar_numero(var_ftt), "%."
  ),
  paste0(
    "Os casos novos ",
    classificar_variacao(var_cn, tolerancia_estabilidade_pct),
    " em média ", formatar_numero(var_cn), "%."
  ),
  paste0(
    "Os processos baixados ",
    classificar_variacao(var_tbaix, tolerancia_estabilidade_pct),
    " em média ", formatar_numero(var_tbaix), "%."
  ),
  paste0(
    "Os casos pendentes ",
    classificar_variacao(var_cp, tolerancia_estabilidade_pct),
    " em média ", formatar_numero(var_cp), "%."
  ),
  "",
  paste0(
    "A produtividade dos servidores, medida pelo IPSJud, ",
    classificar_variacao(var_ipsjud, tolerancia_estabilidade_pct),
    " em média ", formatar_numero(var_ipsjud), "%."
  ),
  paste0(
    "A produtividade dos magistrados, medida pelo IPM, ",
    classificar_variacao(var_ipm, tolerancia_estabilidade_pct),
    " em média ", formatar_numero(var_ipm), "%."
  ),
  paste0(
    "A carga de trabalho por servidor, medida pelo KS, ",
    classificar_variacao(var_ks, tolerancia_estabilidade_pct),
    " em média ", formatar_numero(var_ks), "%."
  ),
  paste0(
    "A carga de trabalho dos magistrados, medida por K, ",
    classificar_variacao(var_k, tolerancia_estabilidade_pct),
    " em média ", formatar_numero(var_k), "%."
  ),
  "",
  paste0(
    "O IAD variou, em média, ", formatar_numero(var_iad_pp),
    " pontos percentuais entre 2016 e 2024."
  ),
  paste0(
    "A TCL variou, em média, ", formatar_numero(var_tcl_pp),
    " pontos percentuais entre 2016 e 2024."
  ),
  "",
  paste0(
    "A despesa por processo baixado variou, em média, ",
    formatar_numero(var_dpj_tbaix), "%."
  ),
  paste0(
    "A despesa por integrante da força de trabalho variou, em média, ",
    formatar_numero(var_dpj_ftt), "%."
  ),
  "",
  conclusao_automatica,
  "",
  paste0(
    "A força de trabalho não apresentou expansão superior a ",
    tolerancia_estabilidade_pct,
    "%? ", ifelse(forca_nao_expandiu_fortemente, "SIM", "NÃO ou dado ausente"), "."
  ),
  "",
  "RESSALVAS METODOLÓGICAS",
  "1. A análise é descritiva e não estabelece causalidade.",
  "2. Correlação entre variações anuais não demonstra influência causal.",
  "3. A interpretação depende da cobertura dos indicadores em todos os TRTs e anos.",
  "4. O índice 2016 = 100 mede evolução relativa e elimina diferenças de porte, mas não elimina outros fatores institucionais.",
  "5. IAD e TCL são mantidos em percentual e não são normalizados em 2016.",
  paste0(
    "6. A DPJ foi tratada como ",
    ifelse(dpj_em_valores_reais, "despesa real", "despesa nominal"),
    "."
  ),
  "7. Se DPJ estiver nominal, os resultados de crescimento da despesa não devem ser interpretados como crescimento real."
)

# ------------------------------------------------------------
# 19. Montar o arquivo TXT com TODOS os resultados
# ------------------------------------------------------------

cabecalho_txt <- c(
  "ANÁLISE DE PRODUTIVIDADE E TRAJETÓRIA DA DESPESA DOS 24 TRTs",
  paste0("Arquivo de entrada: ", arquivo_entrada),
  paste0("Pasta de saída: ", pasta_produtividade),
  paste0("Período: ", ano_inicial, " a ", ano_final),
  paste0("Ano-base dos índices: ", ano_base, " = 100"),
  paste0("Unidades esperadas: TRT1 a TRT24"),
  paste0("Número esperado de observações TRT-ano: ", painel_esperado),
  paste0("Número de linhas TRT-ano encontradas antes de completar o painel: ", painel_com_linha_original),
  paste0(
    "TRTs ausentes integralmente na base: ",
    ifelse(length(trts_ausentes_na_base) == 0, "nenhum", paste(trts_ausentes_na_base, collapse = ", "))
  ),
  paste0(
    "DPJ tratada como: ",
    ifelse(dpj_em_valores_reais, "despesa real/deflacionada", "despesa nominal")
  ),
  "",
  "Este arquivo contém diagnósticos, tabelas anuais, variações de 2016 a 2024,",
  "resumos por período, correlações descritivas e interpretação automática preliminar."
)

linhas_txt <- c(
  cabecalho_txt,
  capturar_tabela("1. COLUNAS SELECIONADAS", colunas_selecionadas),
  capturar_tabela("2. DIAGNÓSTICO GERAL DE COBERTURA", diagnostico_geral),
  capturar_tabela("3. COBERTURA POR ANO E VARIÁVEL", diagnostico_por_ano),
  capturar_tabela("4. BASES DE 2016 AUSENTES OU IGUAIS A ZERO", checagem_base_2016),
  capturar_tabela("5. COMPARAÇÃO ENTRE TBAIX AGREGADO E TBAIX1 + TBAIX2", comparacao_tbaix),
  capturar_tabela("6. RESUMO ANUAL DOS ÍNDICES 2016 = 100", resumo_anual_indices),
  capturar_tabela("7. VARIAÇÃO INDIVIDUAL DE 2016 A 2024", variacao_2016_2024_individual),
  capturar_tabela("8. RESUMO DA VARIAÇÃO DE 2016 A 2024", tabela_principal_2016_2024),
  capturar_tabela("9. RESUMO DOS ÍNDICES POR PERÍODO", resumo_periodo_indices),
  capturar_tabela("10. RESUMO ANUAL DO IAD E DA TCL", resumo_anual_taxas),
  capturar_tabela("11. VARIAÇÃO INDIVIDUAL DO IAD E DA TCL — 2016 A 2024", variacao_taxas_2016_2024_individual),
  capturar_tabela("12. RESUMO DA VARIAÇÃO DO IAD E DA TCL — PONTOS PERCENTUAIS", tabela_taxas_2016_2024),
  capturar_tabela("13. RESUMO DO IAD E DA TCL POR PERÍODO", resumo_periodo_taxas),
  capturar_tabela("14. CORRELAÇÕES DESCRITIVAS ENTRE VARIAÇÕES ANUAIS", tabela_correlacoes),
  "",
  "============================================================",
  "15. INTERPRETAÇÃO AUTOMÁTICA PRELIMINAR",
  "============================================================",
  texto_interpretacao,
  "",
  "============================================================",
  "16. ARQUIVOS GRÁFICOS GERADOS",
  "============================================================",
  "01_escala_despesa_atividade.png",
  "02_produtividade_carga.png",
  "03_iad_tcl_percentuais.png",
  "04_intensidade_gasto.png",
  "05_trajetorias_individuais.png"
)

arquivo_txt <- file.path(
  pasta_produtividade,
  "RESULTADOS_COMPLETOS_PRODUTIVIDADE_24_TRTs.txt"
)

writeLines(
  enc2utf8(linhas_txt),
  con = arquivo_txt,
  useBytes = TRUE
)

# ------------------------------------------------------------
# 20. Exportar planilha e CSVs
# ------------------------------------------------------------

arquivo_xlsx <- file.path(
  pasta_produtividade,
  "analise_produtividade_24_trts.xlsx"
)

writexl::write_xlsx(
  list(
    colunas_selecionadas = colunas_selecionadas,
    base_24_trts = base_trts,
    diagnostico_geral = diagnostico_geral,
    diagnostico_por_ano = diagnostico_por_ano,
    checagem_base_2016 = checagem_base_2016,
    comparacao_tbaix = comparacao_tbaix,
    base_indices = base_indices,
    resumo_anual_indices = resumo_anual_indices,
    variacao_2016_2024_ind = variacao_2016_2024_individual,
    resumo_variacao_2016_2024 = tabela_principal_2016_2024,
    resumo_periodo_indices = resumo_periodo_indices,
    base_taxas = base_taxas,
    resumo_anual_taxas = resumo_anual_taxas,
    variacao_taxas_ind = variacao_taxas_2016_2024_individual,
    resumo_variacao_taxas = tabela_taxas_2016_2024,
    resumo_periodo_taxas = resumo_periodo_taxas,
    variacoes_anuais = base_variacoes_anuais,
    correlacoes = tabela_correlacoes
  ),
  path = arquivo_xlsx
)

readr::write_csv2(
  resumo_anual_indices,
  file.path(pasta_produtividade, "resumo_anual_indices_2016_100.csv")
)

readr::write_csv2(
  tabela_principal_2016_2024,
  file.path(pasta_produtividade, "resumo_variacao_2016_2024.csv")
)

readr::write_csv2(
  resumo_anual_taxas,
  file.path(pasta_produtividade, "resumo_anual_iad_tcl.csv")
)

readr::write_csv2(
  tabela_correlacoes,
  file.path(pasta_produtividade, "correlacoes_variacoes_anuais.csv")
)

# ------------------------------------------------------------
# 21. Prints finais
# ------------------------------------------------------------

cat("\n====================================================\n")
cat("ANÁLISE CONCLUÍDA\n")
cat("====================================================\n")
cat("\nApenas TRT1 a TRT24 foram mantidos.\n")
cat("\nPasta de saída:\n")
cat(pasta_produtividade, "\n")

cat("\nArquivo TXT principal para enviar ao ChatGPT:\n")
cat(arquivo_txt, "\n")

cat("\nPlanilha completa:\n")
cat(arquivo_xlsx, "\n")

cat("\nResumo da variação média entre 2016 e 2024:\n")
print(tabela_principal_2016_2024, n = Inf, width = Inf)

cat("\nVariação média do IAD e da TCL em pontos percentuais:\n")
print(tabela_taxas_2016_2024, n = Inf, width = Inf)

cat("\nInterpretação automática preliminar:\n")
cat(paste(texto_interpretacao, collapse = "\n"), "\n")

cat("\nATENÇÃO:\n")
cat("Antes de interpretar os resultados, confira no TXT a seção de cobertura.\n")
cat("Indicadores com poucos TRTs ou muitos anos ausentes devem ser tratados com cautela.\n")

