from __future__ import annotations

import io
import json
import textwrap
import threading
from functools import lru_cache
from zipfile import ZIP_DEFLATED, ZipFile

import matplotlib
matplotlib.use("Agg")
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter, MaxNLocator
import plotly.graph_objects as go

from article_data import FIGURES, SCM_MODELS

BLUE = "#173F5F"
OCHRE = "#B06427"
GRAY = "#75808B"
PLOT_LOCK = threading.RLock()
SOURCE = "Fonte: elaboração própria, com dados do CNJ e resultados das estimações em R."


def line(name, x, y, color=BLUE, dash="solid", lower=None, upper=None):
    return {"name": name, "x": list(map(int, x)), "y": list(map(float, y)), "color": color, "dash": dash,
            "lower": None if lower is None else list(map(float, lower)),
            "upper": None if upper is None else list(map(float, upper))}


def scm_spec(data, definition):
    model = definition["model"]
    metadata = SCM_MODELS[model]
    selected = data["scm_series"].query("modelo == @model").sort_values("ano")
    gap = definition["kind"] == "gap"
    share = metadata["scale"] == 100
    ylabel = ("Gap (pontos percentuais)" if share else "Gap (unidades logarítmicas)") if gap else metadata["unit"]
    if gap:
        lines = [line("Observado − sintético", selected.ano, selected.gap * metadata["scale"])]
    else:
        lines = [line("TRT médio observado", selected.ano, selected.observado * metadata["scale"]),
                 line("Controle sintético", selected.ano, selected.sintetico * metadata["scale"], OCHRE, "dash")]
    real = model in {"H1_lndpj", "H3_lndk"}
    note = "Despesas corrigidas pelo IPCA a preços de dezembro de 2024; transformação ln(1 + despesa real)." if real else ("Participações em %; diferenças entre participações expressas em pontos percentuais." if share else "Diferença entre logaritmos de despesas acrescidas de uma unidade.")
    number = definition.get("number")
    title = f"Gráfico {number} — {definition['title']}" if number else definition["title"]
    return {"title": title, "ylabel": ylabel, "lines": lines, "zero": gap, "note": note,
            "kind": "bar" if gap else "line", "article_figure": number is not None,
            "filename": f"grafico_{number:02d}" if number else f"apoio_{model}", "range": None}


def interactive(spec):
    fig = go.Figure()
    for item in spec["lines"]:
        if item.get("lower") is not None:
            fig.add_trace(go.Scatter(x=item["x"], y=item["lower"], mode="lines", line={"width": 0}, showlegend=False, hoverinfo="skip"))
            fig.add_trace(go.Scatter(x=item["x"], y=item["upper"], mode="lines", line={"width": 0}, fill="tonexty", fillcolor="rgba(23,63,95,0.12)", name="Intervalo interquartil", hoverinfo="skip"))
        if spec.get("kind") == "bar":
            fig.add_trace(go.Bar(x=item["x"], y=item["y"], name=item["name"], marker_color=item["color"], width=.7,
                                 hovertemplate="Ano: %{x}<br>Gap: %{y:.4f}<extra>%{fullData.name}</extra>"))
        else:
            fig.add_trace(go.Scatter(x=item["x"], y=item["y"], mode="lines+markers", name=item["name"],
                                     line={"color": item["color"], "width": 2.6, "dash": item["dash"]}, marker={"size": 4.5},
                                     hovertemplate="Ano: %{x}<br>Valor: %{y:.4f}<extra>%{fullData.name}</extra>"))
    if spec.get("zero"):
        fig.add_hline(y=0, line_width=1, line_color="#5D6670")
    if spec.get("reference") is not None:
        fig.add_hline(y=spec["reference"], line_width=1, line_dash="dot", line_color=GRAY)
    for year, dash in [(2017, "dash"), (2023, "dot")]:
        fig.add_vline(x=year, line_width=1, line_dash=dash, line_color=GRAY)
        fig.add_annotation(x=year, y=1.03, yref="paper", text=str(year), showarrow=False, font={"size": 10, "color": "#59636F"})
    fig.update_layout(template="plotly_white", height=440, margin={"l": 65, "r": 20, "t": 65, "b": 50},
                      font={"family": "Arial, sans-serif", "size": 13, "color": "#263445"}, separators=",.",
                      legend={"orientation": "h", "yanchor": "bottom", "y": 1.12, "x": 0, "title": None},
                      hovermode="x unified", paper_bgcolor="white", plot_bgcolor="white")
    fig.update_xaxes(title="Ano", dtick=2, tickformat="d", showgrid=False, fixedrange=False)
    fig.update_yaxes(title=spec["ylabel"], gridcolor="#E7EBEF", zeroline=False, automargin=True)
    if spec.get("range") is not None:fig.update_yaxes(range=spec["range"])
    return fig


def serialized(spec):
    return json.dumps(spec, ensure_ascii=False, allow_nan=False, sort_keys=True)


@lru_cache(maxsize=48)
def export_figure(spec_json):
    spec = json.loads(spec_json)
    output = {}
    with PLOT_LOCK, matplotlib.rc_context({"font.family": "serif", "font.serif": ["DejaVu Serif"], "font.size": 11,
                                          "pdf.fonttype": 42, "axes.unicode_minus": False, "svg.hashsalt": "idp-artigo"}):
        fig = Figure(figsize=(7.6, 4.85), facecolor="white")
        ax = fig.add_axes([.15, .15, .82, .70] if spec.get("article_figure") else [.13, .23, .83, .55])
        for item in spec["lines"]:
            if spec.get("kind") == "bar":
                ax.bar(item["x"], item["y"], label=item["name"], color=item["color"], width=.7, zorder=2)
            else:
                ax.plot(item["x"], item["y"], label=item["name"], color=item["color"], linewidth=1.7,
                        linestyle="--" if item["dash"] == "dash" else "-", marker="o", markersize=2.5)
            if item.get("lower") is not None:ax.fill_between(item["x"], item["lower"], item["upper"], color=item["color"], alpha=.12, label="Intervalo interquartil")
        if spec.get("zero"):ax.axhline(0, color="#5D6670", linewidth=1, zorder=3)
        if spec.get("reference") is not None:ax.axhline(spec["reference"], color=GRAY, linewidth=.7, linestyle=":")
        for year, style in [(2017, "--"), (2023, ":")]:
            ax.axvline(year, color=GRAY, linestyle=style, linewidth=.8, zorder=0)
            ax.text(year, 1.025, str(year), transform=ax.get_xaxis_transform(), ha="center", fontsize=7.5, color="#59636F")
        ax.set_xlabel("Ano", labelpad=8)
        ax.set_ylabel(textwrap.fill(spec["ylabel"], 38), labelpad=10)
        ax.grid(axis="y", color="#E7EBEF", linewidth=.6)
        ax.set_axisbelow(True)
        ax.spines[["top", "right"]].set_visible(False)
        ax.spines[["left", "bottom"]].set_color("#ADB5BD")
        ax.tick_params(length=3, color="#ADB5BD")
        ax.set_xticks(spec["lines"][0]["x"])
        ax.tick_params(axis="x", labelsize=9)
        ax.yaxis.set_major_formatter(FuncFormatter(lambda value, pos: f"{value:g}".replace(".", ",")))
        if spec.get("range") is not None:ax.set_ylim(spec["range"])
        ax.legend(loc="lower left", bbox_to_anchor=(0, 1.11), frameon=False, ncol=2, fontsize=10 if spec.get("article_figure") else 8, borderaxespad=0)
        if not spec.get("article_figure"):
            fig.text(.13, .98, textwrap.fill(spec["title"], 83), ha="left", va="top", fontsize=10.2, fontweight="bold")
            footer = textwrap.fill(spec["note"], 118) + "\n" + SOURCE
            fig.text(.13, .07, footer, ha="left", va="bottom", fontsize=7, linespacing=1.5, color="#354150")
        for extension in ["png", "svg", "pdf"]:
            buffer = io.BytesIO()
            fig.savefig(buffer, format=extension, dpi=600, facecolor="white")
            output[extension] = buffer.getvalue()
        fig.clear()
    return output


def article_archive(data):
    buffer = io.BytesIO()
    captions = []
    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        for definition in FIGURES:
            spec = scm_spec(data, definition)
            exports = export_figure(serialized(spec))
            for extension, content in exports.items():archive.writestr(f"{spec['filename']}.{extension}", content)
            frame = data["scm_series"][data["scm_series"].modelo.eq(definition["model"])]
            archive.writestr(f"{spec['filename']}_dados.csv", frame.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"))
            captions.append(spec["title"] + "\nNota: " + spec["note"] + "\n" + SOURCE)
        archive.writestr("legendas_dos_graficos.txt", "\n\n".join(captions).encode("utf-8-sig"))
    return buffer.getvalue()
