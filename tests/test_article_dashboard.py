import io
from zipfile import ZipFile

import numpy as np
import pandas as pd
import pytest
from PIL import Image, ImageChops
from streamlit.testing.v1 import AppTest

from article_data import DATA_DIR, FIGURES, INDICATORS, MARKOV_MODELS, SCM_MODELS, load_data, period_means, table3
from article_charts import article_archive, export_figure, interactive, scm_spec, serialized


@pytest.fixture(scope="module")
def data():
    return load_data()


def test_results_match_revised_dissertation(data):
    summary = data["scm_resumo"].set_index("modelo")
    assert summary.loc["H1_lndpj", "razao_mspe_pos_pre"] == pytest.approx(4.53903376910068)
    assert summary.loc["H1_lndpj", "gap_medio_pos"] == pytest.approx(-.127508998486534)
    assert summary.loc["H3_lndk", "razao_mspe_pos_pre"] == pytest.approx(7.40715979126077)
    assert summary.loc["H3_lndk", "gap_medio_pos"] == pytest.approx(-.0548215910172134)
    assert summary.loc["H2_share_odck", "gap_medio_pos"] == pytest.approx(-.0337, abs=5e-5)
    assert summary.loc["H3_share_dk", "gap_medio_pos"] == pytest.approx(-.00644164445452725)
    t = table3(data)
    assert np.allclose(t["Variação média"].round(2), [2.19,-.81,5.71,13.51,-15.64,23.43,16.09,1.86,-4.44,6.38,-15.78])


def test_mspe_and_gaps_recomputed_from_annual_series(data):
    for model, rows in data["scm_series"].groupby("modelo"):
        pre = rows[rows.ano.le(2016)].gap.to_numpy()
        post = rows[rows.ano.ge(2017)].gap.to_numpy()
        report = data["scm_resumo"].set_index("modelo").loc[model]
        assert (pre**2).mean() == pytest.approx(report.mspe_pre)
        assert (post**2).mean() == pytest.approx(report.mspe_pos)
        assert (post**2).mean()/(pre**2).mean() == pytest.approx(report.razao_mspe_pos_pre)
        assert post.mean() == pytest.approx(report.gap_medio_pos)


def test_real_amounts_and_markov_growth_use_same_sample(data):
    base = data["scm_base"]
    for variable in ["dpj", "dpe", "drh", "odck", "dk"]:
        assert np.allclose(base[variable] * base.fator_ipca_dez2024, base[variable + "_real_dez2024"], atol=.01)
    treated = base[base.sigla.eq("TRT_MEDIO")].sort_values("ano")
    for model, variable in [("MS_H1_g_lndpj", "dpj"), ("MS_H3_g_lndk", "dk")]:
        actual = data["markov_series"].query("modelo == @model").sort_values("ano")
        expected = np.diff(np.log1p(treated[variable + "_real_dez2024"])) * 100
        assert len(actual) == 14
        assert np.allclose(actual.y, expected, atol=1e-8)
    assert period_means(data, "MS_H1_g_lndpj").iloc[-1, 2] == pytest.approx(27.9429204563133)
    assert period_means(data, "MS_H3_g_lndk").iloc[-1, 2] == pytest.approx(58.5292136)


def test_productivity_mean_of_individual_indices(data):
    base = data["prod_base_24_trts"]
    for key in data["prod_indices"].indicador_raw.unique():
        pivot = base.pivot(index="sigla", columns="ano", values=key)
        indexed = pivot.div(pivot[2016], axis=0) * 100
        report = data["prod_indices"].query("indicador_raw == @key").set_index("ano").sort_index()
        assert np.allclose(indexed.mean(axis=0).sort_index(), report.media_indice, atol=1e-8)
        assert np.allclose(indexed.median(axis=0).sort_index(), report.mediana_indice, atol=1e-8)
    assert set(base.sigla) == {f"TRT{i}" for i in range(1,25)}
    assert "TST" not in set(data["scm_base"].sigla)


@pytest.mark.parametrize("definition", FIGURES)
def test_numbered_figures_preserve_data_units_and_export(definition, data):
    spec = scm_spec(data, definition)
    assert spec["title"].startswith(f"Gráfico {definition['number']} — ")
    source = data["scm_series"][data["scm_series"].modelo.eq(definition["model"])].sort_values("ano")
    column = "gap" if definition["kind"] == "gap" else "observado"
    scale = SCM_MODELS[definition["model"]]["scale"]
    plot = interactive(spec)
    assert np.allclose(plot.data[0].y, source[column] * scale)
    assert plot.data[0].type == ("bar" if definition["kind"] == "gap" else "scatter")
    exports = export_figure(serialized(spec))
    image = Image.open(io.BytesIO(exports["png"]))
    assert image.size == (4560,2910)
    assert image.info["dpi"][0] == pytest.approx(600, abs=.02)
    assert ImageChops.difference(image.convert("RGB"), Image.new("RGB",image.size,"white")).getbbox() is not None
    assert b"<svg" in exports["svg"]
    assert exports["pdf"].startswith(b"%PDF-")


def test_article_package_has_exact_figure_numbers(data):
    with ZipFile(io.BytesIO(article_archive(data))) as archive:
        for n in range(1,9):
            for ext in ["png","svg","pdf"]:assert f"grafico_{n:02d}.{ext}" in archive.namelist()
        assert len(archive.namelist()) == 33
        assert "legendas_dos_graficos.txt" in archive.namelist()


def assert_no_errors(app):
    assert not app.exception, [e.message for e in app.exception]


def test_navigation_and_all_model_filters():
    root = DATA_DIR.parents[1]
    app = AppTest.from_file(str(root/"app.py"), default_timeout=90).run()
    assert_no_errors(app)
    for page in ["pages/01_Metodo_Controle_Sintetico.py", "pages/03_Resultados_R_Synth.py", "pages/04_Markov_Switching.py", "pages/02_Analise_Produtividade_Escala.py"]:
        app.switch_page(page).run()
        assert_no_errors(app)
        if "01_" in page:
            for model in SCM_MODELS:
                app.selectbox(key="method_model").set_value(model).run()
                assert_no_errors(app)
        elif "03_" in page:
            for hypothesis in ["H1", "H2", "H3"]:
                app.radio(key="results_hypothesis").set_value(hypothesis).run()
                assert_no_errors(app)
                assert not app.button
                assert len(app.get("imgs")) == sum(SCM_MODELS[d["model"]]["hypothesis"] == hypothesis for d in FIGURES)
                assert all(e.proto.label == "Baixar séries anuais" for e in app.get("download_button"))
        elif "04_" in page:
            for model in MARKOV_MODELS:
                app.selectbox(key="markov_model").set_value(model).run()
                assert_no_errors(app)
        else:
            for indicator in INDICATORS:
                app.selectbox(key="productivity_indicator").set_value(indicator).run()
                assert_no_errors(app)
            app.radio(key="productivity_statistic").set_value("Mediana").run()
            assert_no_errors(app)


def test_dataset_integrity_across_windows_and_linux_newlines(tmp_path, monkeypatch):
    import article_data
    for source in DATA_DIR.iterdir():
        if source.is_file():
            (tmp_path / source.name).write_bytes(source.read_bytes().replace(b"\r\n", b"\n"))
    monkeypatch.setattr(article_data, "DATA_DIR", tmp_path)
    linux = article_data.load_data()
    for path in tmp_path.glob("*.csv"):
        path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
    windows = article_data.load_data()
    for name in linux:
        pd.testing.assert_frame_equal(linux[name], windows[name])
    path = tmp_path / "scm_resumo.csv"
    path.write_bytes(path.read_bytes().replace(b"H1_lndpj", b"H9_lndpj", 1))
    with pytest.raises(ValueError, match="scm_resumo.csv"):
        article_data.load_data()


def test_published_figure_assets_match_verified_specs(data):
    import hashlib,json
    folder = DATA_DIR / "figuras"
    manifest = json.loads((folder / "manifesto_figuras.json").read_text(encoding="utf-8"))
    for definition in FIGURES:
        spec = scm_spec(data, definition)
        info = manifest[spec["filename"]]
        assert info["spec_sha256"] == hashlib.sha256(serialized(spec).encode("utf-8")).hexdigest()
        content = (folder / (spec["filename"] + ".png")).read_bytes()
        assert info["png_sha256"] == hashlib.sha256(content).hexdigest()
        assert Image.open(io.BytesIO(content)).size == (4560,2910)
