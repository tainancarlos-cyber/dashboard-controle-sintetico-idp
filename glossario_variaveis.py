from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import streamlit as st


BASE_DIR = Path(__file__).resolve().parent
PDF_SOURCE = BASE_DIR / "data" / "Glossario Justiça em Números.pdf"


@dataclass(frozen=True)
class GlossaryEntry:
    code: str
    name: str
    formula: str
    explanation: str
    components: dict[str, str]
    source_note: str = "Glossario Justiça em Números.pdf"


GLOSSARY: dict[str, GlossaryEntry] = {
    "DPJ": GlossaryEntry(
        "DPJ",
        "Despesa Total da Justiça",
        "DPJ = ODCK + DRH",
        "Mede a despesa total do tribunal no ano-base. Soma as despesas de funcionamento/capital e as despesas de recursos humanos.",
        {
            "ODCK": "Outras despesas correntes e de capital.",
            "DRH": "Despesas com recursos humanos.",
        },
    ),
    "ODCK": GlossaryEntry(
        "ODCK",
        "Outras Despesas Correntes e de Capital",
        "ODCK = ODC + DK",
        "Mede as despesas correntes não classificadas como recursos humanos e as despesas de capital do tribunal.",
        {
            "ODC": "Outras despesas correntes.",
            "DK": "Despesas de capital.",
        },
    ),
    "DRH": GlossaryEntry(
        "DRH",
        "Despesas com Recursos Humanos",
        "DRH = DPE + DBen + DTer + DEst + DIP",
        "Agrega despesas com pessoal, benefícios, terceirizados, estagiários e outras despesas indenizatórias ou indiretas de recursos humanos.",
        {
            "DPE": "Pessoal e encargos do quadro ativo e inativo.",
            "DBen": "Benefícios do pessoal do quadro ativo e inativo.",
            "DTer": "Terceirizados.",
            "DEst": "Estagiários.",
            "DIP": "Despesas indenizatórias e indiretas com pessoal.",
        },
    ),
    "DPE": GlossaryEntry(
        "DPE",
        "Despesas com Pessoal e Encargos do Quadro Ativo e Inativo",
        "DPE = DPEA + DPEI",
        "Mede a despesa com pessoal e encargos do quadro ativo e do quadro inativo.",
        {
            "DPEA": "Pessoal e encargos do quadro ativo.",
            "DPEI": "Pessoal e encargos do quadro inativo.",
        },
    ),
    "DK": GlossaryEntry(
        "DK",
        "Despesas de Capital",
        "DK compõe ODCK; no glossário aparece em ODCK = ODC + DK e em EO2 = DK / OK",
        "Representa despesas de capital liquidadas no ano-base. No dashboard, é usada para medir a trajetória e a participação dos investimentos/capital no orçamento.",
        {
            "ODC": "Outras despesas correntes.",
            "OK": "Orçamento para despesas de capital, usado apenas no indicador de execução orçamentária EO2.",
        },
    ),
    "FTT": GlossaryEntry(
        "FTT",
        "Força de Trabalho Total de Magistrados, Servidores e Auxiliares",
        "FTT = Mag + Serv + TFaux",
        "Indica o total da força de trabalho do tribunal no final do ano-base.",
        {
            "Mag": "Magistrados.",
            "Serv": "Servidores.",
            "TFaux": "Força de trabalho auxiliar.",
        },
    ),
    "TPEfet": GlossaryEntry(
        "TPEfet",
        "Total de Pessoal do Quadro Efetivo",
        "TPEfet = TPEfetJud + TPEfetAdm",
        "Indica o número de servidores do quadro efetivo no final do período-base.",
        {
            "TPEfetJud": "Servidores efetivos da área judiciária.",
            "TPEfetAdm": "Servidores efetivos da área administrativa.",
        },
    ),
    "TBaix": GlossaryEntry(
        "TBaix",
        "Total de Processos Baixados",
        "TBaix = total de processos baixados no período-base",
        "Conta processos originários e recursos que foram baixados pelo tribunal no período-base, como remessas a outros órgãos ou instâncias e arquivamentos definitivos.",
        {
            "Baixa": "Encerramento da tramitação no tribunal segundo os critérios do glossário.",
            "Exclusões": "Não inclui simples remessas internas para cumprimento de diligências.",
        },
    ),
    "Cn": GlossaryEntry(
        "Cn",
        "Casos Novos",
        "Cn = CnO + CnR",
        "Representa os casos novos recebidos no período-base, combinando originários e recursos interpostos no tribunal.",
        {
            "CnO": "Casos novos originários.",
            "CnR": "Casos novos em grau de recurso.",
        },
    ),
    "Cp": GlossaryEntry(
        "Cp",
        "Casos Pendentes",
        "Cp = estoque de processos pendentes ao final do período-base",
        "Saldo de processos que não tiveram baixa até o fim do período-base, incluindo processos que retornaram à tramitação em hipóteses previstas no glossário.",
        {
            "Estoque": "Processos ainda pendentes no fechamento do período.",
            "TBaix": "Critério de baixa usado para separar processos baixados e pendentes.",
        },
    ),
    "K": GlossaryEntry(
        "K",
        "Carga de Trabalho Total dos Magistrados",
        "K = (TBaix + Cp + RIntJ + RIntP) / Mag",
        "Indica a carga média de trabalho dos magistrados no período-base.",
        {
            "TBaix": "Processos baixados.",
            "Cp": "Casos pendentes.",
            "RIntJ": "Recursos internos julgados.",
            "RIntP": "Recursos internos pendentes.",
            "Mag": "Número de magistrados.",
        },
    ),
    "KS": GlossaryEntry(
        "KS",
        "Carga de Trabalho por Servidor",
        "KS = carga processual / servidores da área judiciária",
        "Indicador derivado usado na análise para aproximar a carga por servidor. Funciona como razão entre volume processual e contingente de servidores da área judiciária.",
        {
            "Carga processual": "Combinação de processos baixados, pendentes e recursos internos, conforme a lógica dos indicadores de carga.",
            "Servidores": "Servidores considerados na área judiciária.",
        },
        "Indicador derivado na análise; o PDF extraído traz a formulação original de K para magistrados.",
    ),
    "TCL": GlossaryEntry(
        "TCL",
        "Taxa de Congestionamento Líquida",
        "TCL = (Cp - Sus) / (TBaix + Cp - Sus)",
        "Indica a proporção de processos que permanece congestionada, excluindo processos suspensos, sobrestados ou em arquivo provisório.",
        {
            "Cp": "Casos pendentes.",
            "Sus": "Processos suspensos, sobrestados ou em arquivo provisório.",
            "TBaix": "Processos baixados.",
        },
    ),
    "IPM": GlossaryEntry(
        "IPM",
        "Índice de Produtividade dos Magistrados",
        "IPM = TBaix / Mag",
        "Mede a média de processos baixados por magistrado no período-base.",
        {
            "TBaix": "Processos baixados.",
            "Mag": "Magistrados.",
        },
    ),
    "IPSJud": GlossaryEntry(
        "IPSJud",
        "Índice de Produtividade dos Servidores da Área Judiciária",
        "IPSJud = TBaix / SaJud",
        "Mede a média de processos baixados por servidor da área judiciária no período-base.",
        {
            "TBaix": "Processos baixados.",
            "SaJud": "Servidores da área judiciária.",
        },
    ),
    "IAD": GlossaryEntry(
        "IAD",
        "Índice de Atendimento à Demanda",
        "IAD = TBaix / Cn",
        "Mede a relação entre processos baixados e casos novos. Valores acima de 1, ou 100%, indicam baixa superior à entrada de casos.",
        {
            "TBaix": "Processos baixados.",
            "Cn": "Casos novos.",
        },
    ),
    "share_odck": GlossaryEntry(
        "share_odck",
        "Participação das despesas discricionárias",
        "share_ODCK = ODCK / DPJ",
        "Mede quanto as outras despesas correntes e de capital representam na despesa total.",
        {
            "ODCK": "Outras despesas correntes e de capital.",
            "DPJ": "Despesa total da Justiça.",
        },
        "Indicador construído no dashboard a partir das variáveis do glossário.",
    ),
    "share_dk": GlossaryEntry(
        "share_dk",
        "Participação das despesas de capital",
        "share_DK = DK / DPJ",
        "Mede quanto as despesas de capital representam na despesa total.",
        {
            "DK": "Despesas de capital.",
            "DPJ": "Despesa total da Justiça.",
        },
        "Indicador construído no dashboard a partir das variáveis do glossário.",
    ),
    "ln_odck_dpe": GlossaryEntry(
        "ln_odck_dpe",
        "Razão ODCK/DPE em log",
        "ln(ODCK/DPE) = ln(ODCK) - ln(DPE)",
        "Compara despesas correntes/capital com despesas de pessoal e encargos. A forma em log transforma a razão em diferença logarítmica.",
        {
            "ODCK": "Outras despesas correntes e de capital.",
            "DPE": "Pessoal e encargos do quadro ativo e inativo.",
        },
        "Indicador construído no dashboard a partir das variáveis do glossário.",
    ),
    "ln_odck_drh": GlossaryEntry(
        "ln_odck_drh",
        "Razão ODCK/DRH em log",
        "ln(ODCK/DRH) = ln(ODCK) - ln(DRH)",
        "Compara despesas correntes/capital com o conjunto das despesas de recursos humanos.",
        {
            "ODCK": "Outras despesas correntes e de capital.",
            "DRH": "Despesas com recursos humanos.",
        },
        "Indicador construído no dashboard a partir das variáveis do glossário.",
    ),
}


ALIASES = {
    "Dpj": "DPJ",
    "dpj": "DPJ",
    "odck": "ODCK",
    "drh": "DRH",
    "dpe": "DPE",
    "dk": "DK",
    "ftt": "FTT",
    "tpefet": "TPEfet",
    "tbaix": "TBaix",
    "casos_novos": "Cn",
    "casos_pendentes": "Cp",
    "iad_pct": "IAD",
    "tcl_pct": "TCL",
    "ipm": "IPM",
    "ipsjud": "IPSJud",
    "ks": "KS",
    "k": "K",
    "ln_dpj": "DPJ",
    "ln_dk": "DK",
}


def normalize_code(code: str) -> str:
    return ALIASES.get(code, code)


def entry(code: str) -> GlossaryEntry | None:
    return GLOSSARY.get(normalize_code(code))


def help_text(code: str) -> str | None:
    item = entry(code)
    if item is None:
        return None
    return f"{item.name}. Fórmula: {item.formula}. {item.explanation}"


def popover(code: str, label: str | None = None) -> None:
    item = entry(code)
    if item is None:
        return
    with st.popover(label or f"{item.code} - fórmula", help=help_text(item.code)):
        st.markdown(f"**{item.code} - {item.name}**")
        st.code(item.formula, language=None)
        st.write(item.explanation)
        st.markdown("**Componentes**")
        st.dataframe(
            pd.DataFrame(
                [{"Componente": key, "Como entra na fórmula": value} for key, value in item.components.items()]
            ),
            use_container_width=True,
            hide_index=True,
        )
        st.caption(f"Fonte: {item.source_note}")


def glossary_dataframe(codes: list[str] | None = None) -> pd.DataFrame:
    selected = [normalize_code(code) for code in codes] if codes else list(GLOSSARY)
    rows = []
    seen = set()
    for code in selected:
        item = GLOSSARY.get(code)
        if item is None or item.code in seen:
            continue
        seen.add(item.code)
        rows.append(
            {
                "variavel": item.code,
                "nome": item.name,
                "formula": item.formula,
                "explicacao": item.explanation,
                "componentes": "; ".join(f"{key}: {value}" for key, value in item.components.items()),
                "fonte": item.source_note,
            }
        )
    return pd.DataFrame(rows)


def glossary_section(codes: list[str] | None = None, title: str = "Glossário das variáveis") -> None:
    st.subheader(title)
    st.write(
        "As fórmulas abaixo seguem o Glossário Justiça em Números quando a variável existe no documento. "
        "Indicadores derivados do dashboard são identificados na coluna de fonte."
    )
    df = glossary_dataframe(codes)
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "variavel": st.column_config.TextColumn("Variável", help="Sigla usada no dashboard."),
            "nome": st.column_config.TextColumn("Nome", help="Denominação do indicador/variável."),
            "formula": st.column_config.TextColumn("Fórmula original ou derivada", help="Como o indicador é calculado."),
            "explicacao": st.column_config.TextColumn("Explicação", help="Como interpretar o indicador."),
            "componentes": st.column_config.TextColumn("Decomposição dos componentes"),
            "fonte": st.column_config.TextColumn("Fonte"),
        },
    )
    if PDF_SOURCE.exists():
        st.download_button(
            "Baixar glossário Justiça em Números em PDF",
            data=PDF_SOURCE.read_bytes(),
            file_name=PDF_SOURCE.name,
            mime="application/pdf",
        )
