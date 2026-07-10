from __future__ import annotations

from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
LOCAL_DATA_PROJECT_DIR = BASE_DIR / "data" / "Controle_Sintetico_TRT_Medio_sem_TST"
EXTERNAL_PROJECT_DIR = BASE_DIR.parent / "Controle_Sintetico_TRT_Medio_sem_TST"
R_PROJECT_DIR = LOCAL_DATA_PROJECT_DIR if LOCAL_DATA_PROJECT_DIR.exists() else EXTERNAL_PROJECT_DIR
EXPORT_DIR = R_PROJECT_DIR / "04_exports_dashboard"
FIGURES_DIR = R_PROJECT_DIR / "02_resultados_scm"
COMPARABILITY_DIR = R_PROJECT_DIR / "06_comparabilidade_trts"
FINAL_SUMMARY_DIR = R_PROJECT_DIR / "05_resumo_final"
JN_DATA_FILE = BASE_DIR.parent / "23-jun-2026" / "JN_23-Jun-2026.csv"
PRODUCTIVITY_FILE = BASE_DIR / "data" / "produtividade_trt_medio.csv"

MODEL_ORDER = [
    "H1_lndpj",
    "H2_share_odck",
    "H2_ln_odck_dpe",
    "H2_ln_odck_drh",
    "H3_share_dk",
    "H3_lndk",
]

MODEL_TITLES = {
    "H1_lndpj": "H1 - Despesa total",
    "H2_share_odck": "H2 - Participacao das despesas discricionarias",
    "H2_ln_odck_dpe": "H2 - Razao ODCK/DPE",
    "H2_ln_odck_drh": "H2 - Razao ODCK/DRH",
    "H3_share_dk": "H3 - Participacao das despesas de capital",
    "H3_lndk": "H3 - Despesas de capital",
}

OUTCOME_LABELS = {
    "ln_dpj": "Log da despesa total - DPJ",
    "share_odck": "ODCK / DPJ",
    "ln_odck_dpe": "Log(ODCK) - Log(DPE)",
    "ln_odck_drh": "Log(ODCK) - Log(DRH)",
    "share_dk": "DK / DPJ",
    "ln_dk": "Log das despesas de capital - DK",
}


def fix_text(value: object) -> object:
    if not isinstance(value, str):
        return value
    if "Ã" not in value and "Â" not in value:
        return value
    try:
        return value.encode("latin1").decode("utf-8")
    except UnicodeError:
        return value


def read_export(name: str) -> pd.DataFrame:
    path = EXPORT_DIR / name
    df = pd.read_csv(path, sep=";", decimal=",", encoding="utf-8", quotechar='"')
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].map(fix_text)
    return df


def parse_br_number(value: object) -> float:
    if pd.isna(value):
        return float("nan")
    text = str(value).strip()
    if not text or text.lower() in {"nd", "n/a", "na", "nan"}:
        return float("nan")
    return float(text.replace(".", "").replace(",", "."))


def load_productivity() -> pd.DataFrame:
    if PRODUCTIVITY_FILE.exists():
        df = pd.read_csv(PRODUCTIVITY_FILE, sep=";", decimal=",", encoding="utf-8")
        for col in df.select_dtypes(include="object").columns:
            df[col] = df[col].map(fix_text)
        return df

    cols = ["ano", "sigla", "justica", "dsc_tribunal", "dpj", "tpefet", "tbaix"]
    df = pd.read_csv(
        JN_DATA_FILE,
        sep=";",
        dtype=str,
        encoding="latin1",
        usecols=lambda col: col in cols,
    )
    df["ano"] = df["ano"].astype(int)
    for col in ["dpj", "tpefet", "tbaix"]:
        df[col] = df[col].map(parse_br_number)

    trts = [f"TRT{i}" for i in range(1, 25)]
    base = df[df["sigla"].isin(trts) & df["ano"].between(2010, 2024)].copy()

    annual = (
        base.groupby("ano", as_index=False)
        .agg(
            dpj_medio=("dpj", "mean"),
            tpefet_medio=("tpefet", "mean"),
            tbaix_medio=("tbaix", "mean"),
            dpj_total=("dpj", "sum"),
            tpefet_total=("tpefet", "sum"),
            tbaix_total=("tbaix", "sum"),
            n_trts=("sigla", "nunique"),
        )
        .sort_values("ano")
    )
    annual["processos_por_servidor"] = annual["tbaix_medio"] / annual["tpefet_medio"]
    annual["despesa_por_processo"] = annual["dpj_medio"] / annual["tbaix_medio"]
    annual["despesa_por_servidor"] = annual["dpj_medio"] / annual["tpefet_medio"]
    annual["periodo"] = annual["ano"].map(
        lambda year: "Pre-intervencao" if year < 2017 else ("Pos-EC 95" if year < 2023 else "Novo arcabouco fiscal")
    )

    index_cols = [
        "dpj_medio",
        "tpefet_medio",
        "tbaix_medio",
        "processos_por_servidor",
        "despesa_por_processo",
        "despesa_por_servidor",
    ]
    base_2016 = annual.loc[annual["ano"].eq(2016), index_cols].iloc[0]
    for col in index_cols:
        annual[f"{col}_indice_2016"] = 100 * annual[col] / base_2016[col]

    return annual


def load_exports() -> dict[str, pd.DataFrame]:
    exports = {
        "series": read_export("serie_observado_sintetico.csv"),
        "series_long": read_export("serie_observado_sintetico_long.csv"),
        "summary": read_export("resumo_efeitos.csv"),
        "unit_weights": read_export("tabela_2_pesos_unidades.csv"),
        "variable_weights": read_export("tabela_1_pesos_variaveis.csv"),
        "pre_means": read_export("tabela_3_medias_pre.csv"),
        "pre_means_long": read_export("tabela_3_medias_pre_long.csv"),
        "donors": read_export("doadores_por_porte.csv"),
        "variable_dict": read_export("dicionario_variaveis.csv"),
        "model_dict": read_export("dicionario_modelos.csv"),
        "base_wide": read_export("base_variaveis_wide.csv"),
        "base_long": read_export("base_variaveis_long.csv"),
        "productivity": load_productivity(),
    }
    comparability_files = {
        "comparability_period": COMPARABILITY_DIR / "resumo_comparabilidade_periodo.csv",
        "comparability_evidence": COMPARABILITY_DIR / "evidencias_comparabilidade_trts.csv",
        "comparability_dispersion": COMPARABILITY_DIR / "estatisticas_anuais_dispersao_trts.csv",
        "comparability_correlations": COMPARABILITY_DIR / "resumo_correlacoes_trts.csv",
    }
    for key, path in comparability_files.items():
        if path.exists():
            df = pd.read_csv(path, sep=";", decimal=",", encoding="utf-8", quotechar='"')
            for col in df.select_dtypes(include="object").columns:
                df[col] = df[col].map(fix_text)
            exports[key] = df
    return exports


def model_options(model_dict: pd.DataFrame) -> list[str]:
    available = set(model_dict["modelo"].dropna())
    ordered = [model for model in MODEL_ORDER if model in available]
    rest = sorted(available - set(ordered))
    return ordered + rest


def model_label(model: str, model_dict: pd.DataFrame) -> str:
    rows = model_dict[model_dict["modelo"].eq(model)]
    if rows.empty:
        return MODEL_TITLES.get(model, model)
    row = rows.iloc[0]
    return f"{row['hipotese']} - {row['descricao']}"


def format_number(value: object, digits: int = 3) -> str:
    if pd.isna(value):
        return "n/d"
    try:
        return f"{float(value):,.{digits}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return str(value)


def image_path(model: str, suffix: str) -> Path:
    return FIGURES_DIR / f"TRT_MEDIO_{model}_{suffix}.png"


def comparability_image(name: str) -> Path:
    return COMPARABILITY_DIR / name
