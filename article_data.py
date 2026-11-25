from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).resolve().parent / "data" / "artigo_ipca_2024"
SCM_MODELS = {
    "H1_lndpj": {"hypothesis": "H1", "label": "H1 · Despesa total real", "outcome": "ln_dpj_real", "unit": "ln(1 + DPJ real)", "scale": 1},
    "H2_share_odck": {"hypothesis": "H2", "label": "H2 · Participação das despesas discricionárias", "outcome": "share_odck", "unit": "Participação na despesa total (%)", "scale": 100},
    "H2_ln_odck_dpe": {"hypothesis": "H2", "label": "H2 · Despesas discricionárias / pessoal", "outcome": "ln_odck_dpe", "unit": "ln(1 + ODCK) − ln(1 + DPE)", "scale": 1},
    "H2_ln_odck_drh": {"hypothesis": "H2", "label": "H2 · Despesas discricionárias / recursos humanos", "outcome": "ln_odck_drh", "unit": "ln(1 + ODCK) − ln(1 + DRH)", "scale": 1},
    "H3_lndk": {"hypothesis": "H3", "label": "H3 · Despesas de capital reais", "outcome": "ln_dk_real", "unit": "ln(1 + DK real)", "scale": 1},
    "H3_share_dk": {"hypothesis": "H3", "label": "H3 · Participação das despesas de capital", "outcome": "share_dk", "unit": "Participação na despesa total (%)", "scale": 100},
}
MARKOV_MODELS = {
    "MS_H1_g_lndpj": {"label": "H1 · Crescimento real da despesa total", "scale": 1, "unit": "Variação logarítmica × 100", "formula": r"100\,\Delta\ln(1+\overline{DPJ}^{R}_t)"},
    "MS_H2_share_odck": {"label": "H2 · Participação das despesas discricionárias", "scale": 100, "unit": "Participação (%)", "formula": r"ODCK_t/DPJ_t"},
    "MS_H2_ln_odck_dpe": {"label": "H2 · Discricionárias / pessoal", "scale": 1, "unit": "Razão logarítmica", "formula": r"\ln(1+ODCK_t)-\ln(1+DPE_t)"},
    "MS_H2_ln_odck_drh": {"label": "H2 · Discricionárias / recursos humanos", "scale": 1, "unit": "Razão logarítmica", "formula": r"\ln(1+ODCK_t)-\ln(1+DRH_t)"},
    "MS_H3_g_lndk": {"label": "H3 · Crescimento real das despesas de capital", "scale": 1, "unit": "Variação logarítmica × 100", "formula": r"100\,\Delta\ln(1+\overline{DK}^{R}_t)"},
    "MS_H3_share_dk": {"label": "H3 · Participação das despesas de capital", "scale": 100, "unit": "Participação (%)", "formula": r"DK_t/DPJ_t"},
}
FIGURES = [
    {"number": 1, "model": "H1_lndpj", "kind": "trajectory", "title": "Despesa total real do TRT médio e de seu controle sintético"},
    {"number": 2, "model": "H1_lndpj", "kind": "gap", "title": "Gap anual da despesa total real"},
    {"number": 3, "model": "H2_share_odck", "kind": "trajectory", "title": "Participação das despesas discricionárias na despesa total"},
    {"number": 4, "model": "H2_ln_odck_dpe", "kind": "trajectory", "title": "Despesas discricionárias em relação às despesas com pessoal"},
    {"number": 5, "model": "H2_share_odck", "kind": "gap", "title": "Gap anual da participação das despesas discricionárias"},
    {"number": 6, "model": "H3_lndk", "kind": "trajectory", "title": "Despesas de capital reais do TRT médio e de seu controle sintético"},
    {"number": 7, "model": "H3_lndk", "kind": "gap", "title": "Gap anual das despesas de capital reais"},
    {"number": 8, "model": "H3_share_dk", "kind": "gap", "title": "Gap anual da participação das despesas de capital"},
]
INDICATORS = {
    "dpj_real_dez2024": "Despesa total real — DPJ",
    "ftt": "Força de trabalho total — FTT",
    "casos_novos": "Casos novos",
    "processos_baixados": "Processos baixados",
    "casos_pendentes": "Casos pendentes",
    "ipsjud": "Produtividade dos servidores — IPSJud",
    "ipm": "Produtividade dos magistrados — IPM",
    "ks": "Carga de trabalho por servidor — KS",
    "k": "Carga de trabalho dos magistrados — K",
    "iad_pct": "Índice de Atendimento à Demanda — IAD",
    "tcl_pct": "Taxa de Congestionamento Líquida — TCL",
    "dpj_por_processo_baixado": "Despesa nominal por processo baixado",
    "dpj_por_forca_trabalho": "Despesa nominal por integrante da força de trabalho",
}
ARTICLE_INDICATORS = list(INDICATORS)[:11]


def number(value: float, digits: int = 2) -> str:
    return f"{value:,.{digits}f}".replace(",", "@ ").replace(".", ",").replace("@ ", ".")


def load_data() -> dict[str, pd.DataFrame]:
    manifest = json.loads((DATA_DIR / "manifesto.json").read_text(encoding="utf-8"))
    result = {}
    for filename, metadata in manifest["arquivos"].items():
        path = DATA_DIR / filename
        if hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest() != metadata["sha256"]:
            raise ValueError(f"O arquivo {filename} não corresponde ao conjunto de dados verificado.")
        result[path.stem] = pd.read_csv(path, sep=";", decimal=",", encoding="utf-8")
    validate_data(result)
    return result


def validate_data(data: dict[str, pd.DataFrame]) -> None:
    assert set(data["scm_resumo"].modelo) == set(SCM_MODELS)
    assert set(data["markov_resumo"].modelo) == set(MARKOV_MODELS)
    assert set(data["scm_series"].outcome) == {v["outcome"] for v in SCM_MODELS.values()}
    assert len(data["scm_doadores"]) == 12
    allowed = set(data["scm_doadores"].sigla) | {"TRT_MEDIO"}
    assert set(data["scm_base"].sigla) == allowed
    assert set(data["prod_base_24_trts"].sigla) == {f"TRT{i}" for i in range(1, 25)}
    assert len(data["prod_base_24_trts"]) == 360
    assert data["prod_indices"].n_trts.eq(24).all()
    series = data["scm_series"]
    assert np.allclose(series.observado - series.sintetico, series.gap, atol=1e-12)
    assert series.groupby("modelo").size().eq(15).all()
    placebo_summary = data["scm_placebo_resumo"]
    assert set(placebo_summary.modelo) == set(SCM_MODELS)
    assert placebo_summary.status.eq("ok").all()
    assert placebo_summary.n_placebos.eq(12).all()
    assert placebo_summary[["p_valor_todos", "p_valor_filtrado"]].gt(0).all().all()
    assert placebo_summary[["p_valor_todos", "p_valor_filtrado"]].le(1).all().all()
    placebo_units = data["scm_placebo_mspe"]
    assert set(placebo_units.unidade) == allowed
    assert placebo_units.groupby("modelo").size().eq(13).all()
    assert placebo_units.groupby("modelo").tratado.sum().eq(1).all()
    placebo_series = data["scm_placebo_series"]
    assert placebo_series.groupby(["modelo", "unidade"]).size().eq(15).all()
    assert set(placebo_series.modelo) == set(SCM_MODELS)
    assert np.allclose(placebo_series.observado - placebo_series.sintetico, placebo_series.gap, atol=1e-12)
    annual = data["markov_series"]
    assert annual[["prob_regime_baixo", "prob_regime_alto"]].ge(-1e-10).all().all()
    assert annual[["prob_regime_baixo", "prob_regime_alto"]].le(1 + 1e-10).all().all()
    assert np.allclose(annual.prob_regime_baixo + annual.prob_regime_alto, 1)


def csv_bytes(frame: pd.DataFrame) -> bytes:
    return frame.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig")


def data_archive() -> bytes:
    buffer = io.BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        for path in sorted(DATA_DIR.iterdir()):
            archive.write(path, path.name)
    return buffer.getvalue()


def table3(data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    indices = data["prod_indices"][["indicador_raw", "indicador"]].drop_duplicates()
    lookup = dict(zip(indices.indicador_raw, indices.indicador))
    variations = data["prod_variacao"].set_index("indicador")
    base = data["prod_base_24_trts"]
    rows = []
    for key in ARTICLE_INDICATORS:
        if key in {"iad_pct", "tcl_pct"}:
            pivot = base.pivot(index="sigla", columns="ano", values=key)
            delta = pivot[2024] - pivot[2016]
            row = {"Indicador": INDICATORS[key], "Variação média": delta.mean(), "Mediana": delta.median(), "Q1": delta.quantile(.25), "Q3": delta.quantile(.75), "Unidade": "p.p."}
        else:
            source = variations.loc[lookup[key]]
            row = {"Indicador": INDICATORS[key], "Variação média": source.variacao_media_pct, "Mediana": source.variacao_mediana_pct, "Q1": source.p25_variacao_pct, "Q3": source.p75_variacao_pct, "Unidade": "%"}
        rows.append(row)
    return pd.DataFrame(rows)


def period_means(data: dict[str, pd.DataFrame], model: str) -> pd.DataFrame:
    annual = data["markov_series"].query("modelo == @model")
    rows = []
    for label, lower, upper in [("Pré-intervenção", 2010, 2016), ("2017–2022", 2017, 2022), ("2023–2024", 2023, 2024), ("Pós-intervenção: 2017–2024", 2017, 2024)]:
        selected = annual[annual.ano.between(lower, upper)]
        rows.append({"Período": label, "Média da variável": selected.y.mean(), "Probabilidade média do regime baixo (%)": selected.prob_regime_baixo.mean() * 100})
    return pd.DataFrame(rows)
