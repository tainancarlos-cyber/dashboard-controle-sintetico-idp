# Dissertação IDP — Orçamento dos TRTs

Dashboard da aplicação estatística utilizada no artigo, com os resultados revistos em valores reais pelo IPCA a preços de dezembro de 2024.

## Conteúdo

- Média anual dos 24 TRTs; TST excluído; 12 TJs doadores efetivos.
- Seis especificações de controle sintético, seus placebos no espaço e seis modelos de Markov Switching.
- Produtividade e escala: 24 TRTs, 360 observações tribunal-ano, 2010–2024.
- Gráficos 1 a 8 conforme a ordem do artigo, com as mesmas imagens de alta resolução inseridas no documento. Os gráficos de GAP são de barras, sem controles de download na interface.
- Figuras de apoio de Markov e produtividade, sem atribuição de novos números aos gráficos do artigo.

A aplicação carrega exclusivamente `data/artigo_ipca_2024`. Não há fallback para dados antigos nem dependência das pastas locais da pesquisa. `manifesto.json` registra fontes, hashes e recortes. As séries estimadas são as exportadas pelo R; o site não reestima os modelos.

## Execução

```sh
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## Validação

```sh
python -m pip install pytest
python -m pytest tests/test_article_dashboard.py
```

Os testes conferem MSPE, gaps, deflação, amostras, crescimento real, média dos índices por TRT, unidades das figuras, arquivos exportados e navegação pelos modelos.

## Interpretação

Participações são mostradas em % e seus gaps em pontos percentuais. Os níveis reais usam ln(1 + despesa real). Crescimento real usa 100 vezes a diferença anual desse logaritmo. A corroboração por Markov concentra-se nos indicadores de composição; os modelos de crescimento real não mostram aumento da probabilidade média do regime baixo em 2017–2024.

A aba Placebos apresenta 72 estimações nos seis modelos: cada um dos 12 TJs é pseudotratado em 2017 e comparado com os outros 11 TJs. As trajetórias principais do TRT médio são preservadas. Os gráficos e testes incluem versões com todos os placebos e com filtro de MSPE pré inferior a 20 vezes o do tratado. O p-valor inclui o TRT médio na contagem; nenhum dos seis modelos apresentou p < 0,05. A qualidade do ajuste pré-intervenção e as diferenças institucionais entre os tribunais devem ser consideradas.
