# Pesquisa IDP - Controle Sintetico

Dashboard para apresentar os resultados do Controle Sintetico gerados no R com `Synth` e `SCtools`.

## Especificacao atual

- Unidade tratada: `TRT_MEDIO`, formada pela media anual dos 24 TRTs, excluindo-se o TST.
- TST: excluido da analise principal.
- Rodadas anteriores: TST isolado e TRTs agregados por soma ficam como testes de especificacao.
- Base candidata de doadores: todos os TJs estaduais disponiveis.
- Doadores efetivos: TJs selecionados por porte orcamentario no script R.
- Periodo pre-intervencao: 2010 a 2016.
- Intervencao: 2017, primeiro ano de vigencia orcamentaria da EC 95/2016.
- Periodo pos-intervencao: 2017 a 2024.
- Marco visual complementar: 2023, novo arcabouco fiscal.

## Exports usados

```text
../Controle_Sintetico_TRT_Medio_sem_TST/04_exports_dashboard
```

Arquivos adicionais de comparabilidade:

```text
../Controle_Sintetico_TRT_Medio_sem_TST/06_comparabilidade_trts
```

## Como abrir o dashboard

```powershell
python -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501
```

Ou execute:

```text
iniciar_dashboard.bat
```

## Observacao metodologica

A especificacao com TRT medio reduz o problema de escala observado na agregacao por soma e permite comparacao mais plausivel com TJs estaduais de porte semelhante. Os resultados devem ser lidos como efeito sobre a trajetoria tipica de um TRT, nao como soma total do orcamento dos TRTs.
