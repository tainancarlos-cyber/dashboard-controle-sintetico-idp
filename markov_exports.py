from __future__ import annotations

from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
LOCAL_MARKOV_PROJECT_DIR = BASE_DIR / "data" / "Markov_Switching_TRT_Medio_sem_TST"
EXTERNAL_MARKOV_PROJECT_DIR = BASE_DIR.parent / "Markov_Switching_TRT_Medio_sem_TST"
MARKOV_PROJECT_DIR = (
    LOCAL_MARKOV_PROJECT_DIR
    if LOCAL_MARKOV_PROJECT_DIR.exists()
    else EXTERNAL_MARKOV_PROJECT_DIR
)
RESULTS_DIR = MARKOV_PROJECT_DIR / "02_resultados"
FIGURES_DIR = MARKOV_PROJECT_DIR / "03_graficos"
FINAL_DIR = MARKOV_PROJECT_DIR / "04_resumo_final"

MODEL_ORDER = [
    "MS_H1_g_lndpj",
    "MS_H2_share_odck",
    "MS_H2_ln_odck_dpe",
    "MS_H2_ln_odck_drh",
    "MS_H3_share_dk",
    "MS_H3_g_lndk",
]

PERIOD_ORDER = ["Pre-intervencao", "Pos-EC 95", "Novo arcabouco fiscal"]

MODEL_TITLES = {
    "MS_H1_g_lndpj": "H1 - Crescimento da despesa total",
    "MS_H2_share_odck": "H2 - Participacao das despesas discricionarias",
    "MS_H2_ln_odck_dpe": "H2 - ODCK em relacao a DPE",
    "MS_H2_ln_odck_drh": "H2 - ODCK em relacao a DRH",
    "MS_H3_share_dk": "H3 - Participacao das despesas de capital",
    "MS_H3_g_lndk": "H3 - Crescimento das despesas de capital",
}

HYPOTHESIS_SUMMARY = {
    "H1": {
        "titulo": "H1 - Despesa total",
        "evidencia": "Fraca/moderada",
        "leitura": "O crescimento medio cai no periodo 2017-2022, mas os regimes estimados ficam proximos. Use como evidencia complementar ao Controle Sintetico.",
    },
    "H2": {
        "titulo": "H2 - Despesas discricionarias",
        "evidencia": "Forte",
        "leitura": "Os modelos indicam mudanca para regime baixo, com classificacao praticamente integral em regime baixo a partir de 2020.",
    },
    "H3": {
        "titulo": "H3 - Despesas de capital",
        "evidencia": "Moderada/forte",
        "leitura": "A evidencia e mais clara em share_dk; o crescimento anual de dk e volatil e deve entrar como apoio secundario.",
    },
}


def read_result(name: str) -> pd.DataFrame:
    path = RESULTS_DIR / name
    return pd.read_csv(path, sep=";", decimal=",", encoding="utf-8", quotechar='"')


def load_markov_exports() -> dict[str, pd.DataFrame]:
    return {
        "summary": read_result("resumo_modelo.csv"),
        "interpretive": read_result("resumo_interpretativo.csv"),
        "period": read_result("resumo_por_periodo.csv"),
        "annual": read_result("probabilidades_anuais.csv"),
        "regimes": read_result("regimes_estimados.csv"),
        "transition": read_result("probabilidades_transicao.csv"),
    }


def model_options(summary: pd.DataFrame) -> list[str]:
    available = set(summary["modelo"].dropna())
    ordered = [model for model in MODEL_ORDER if model in available]
    return ordered + sorted(available - set(ordered))


def model_label(model: str, summary: pd.DataFrame | None = None) -> str:
    if summary is not None:
        rows = summary[summary["modelo"].eq(model)]
        if not rows.empty:
            row = rows.iloc[0]
            return f"{row['hipotese']} - {row['descricao']}"
    return MODEL_TITLES.get(model, model)


def figure_path(model: str, suffix: str) -> Path:
    return FIGURES_DIR / f"{model}_{suffix}.png"


def consolidated_figure_path() -> Path:
    return FIGURES_DIR / "00_probabilidade_regime_baixo_consolidada.png"


def final_summary_path() -> Path:
    return FINAL_DIR / "resumo_final_markov_switching_trt_medio_sem_tst.txt"


def period_rank(period: str) -> int:
    clean = normalize_period(period)
    try:
        return PERIOD_ORDER.index(clean)
    except ValueError:
        return len(PERIOD_ORDER)


def normalize_period(value: object) -> str:
    text = str(value)
    return (
        text.replace("Pré-intervenção", "Pre-intervencao")
        .replace("Pós-EC 95", "Pos-EC 95")
        .replace("Novo arcabouço fiscal", "Novo arcabouco fiscal")
    )


def format_number(value: object, digits: int = 3) -> str:
    if pd.isna(value):
        return "n/d"
    try:
        return f"{float(value):,.{digits}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return str(value)


def format_probability(value: object) -> str:
    if pd.isna(value):
        return "n/d"
    return f"{float(value) * 100:.1f}%".replace(".", ",")


def format_model_value(model: str, value: object, digits: int = 2) -> str:
    if pd.isna(value):
        return "n/d"
    number = float(value)
    if "share_" in model:
        return f"{number * 100:.2f}%".replace(".", ",")
    return format_number(number, digits)


def evidence_rank(hypothesis: str) -> int:
    return {"H2": 0, "H3": 1, "H1": 2}.get(hypothesis, 9)
