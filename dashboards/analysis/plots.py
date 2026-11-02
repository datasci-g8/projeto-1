"""Gráficos Plotly: boxplot anotado, barras comparativas e histograma + KDE."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy import stats

import config
from dashboards.analysis import descriptive

CORES = [
    "#1D428A", "#0077C0", "#C8102E", "#FDB927", "#007A33",
    "#5D76A9", "#E56020", "#00788C",
]
LAYOUT = dict(
    template="plotly_white",
    font=dict(family="Inter, Arial", size=13),
    margin=dict(l=60, r=30, t=70, b=60),
)


def _html(fig):
    return fig.to_html(full_html=False, include_plotlyjs=False, config={"responsive": True})


def boxplot(df: pd.DataFrame, variavel: str) -> str:
    fig = go.Figure()
    if hasattr(df["time"], "cat"):
        times = list(df["time"].cat.categories)
    else:
        times = sorted(df["time"].astype(str).unique())
    for i, time in enumerate(times):
        serie = df.loc[df["time"] == time, variavel]
        m = descriptive.medidas(serie)
        cor = CORES[i % len(CORES)]
        fig.add_trace(go.Box(
            y=serie, name=str(time), boxpoints="outliers", marker_color=cor,
            boxmean=True, quartilemethod="linear", line_width=1.5, legendgroup=str(time),
        ))
        modas = [float(x) for x in str(m["moda"]).split(" (")[0].split(", ")]
        sigla = config.TIME_ABREV.get(str(time), str(time))
        fig.add_trace(go.Scatter(
            x=[time] * len(modas), y=modas, mode="markers",
            name=f"Moda — {sigla}",
            marker=dict(symbol="diamond", size=11, color="black"),
            legendgroup=str(time),
        ))
        anot = [
            ("Lim. sup.", m["limite_sup"]), ("Q3", m["q3"]), ("Mediana", m["mediana"]),
            ("Média", m["media"]), ("Q1", m["q1"]), ("Lim. inf.", m["limite_inf"]),
        ]
        txt = "<br>".join(f"{k}: {v:.2f}" for k, v in anot)
        txt += f"<br>Outliers sup.: {len(m['outliers_sup'])} · inf.: {len(m['outliers_inf'])}"
        fig.add_annotation(
            x=i, y=m["limite_sup"], text=txt, showarrow=False, xshift=95, yshift=-10,
            align="left", font=dict(size=10), bgcolor="rgba(255,255,255,.85)", bordercolor=cor,
        )
        for _nome, y in (("Lim. sup.", m["limite_sup"]), ("Lim. inf.", m["limite_inf"])):
            fig.add_shape(
                type="line", x0=i - 0.4, x1=i + 0.4, y0=y, y1=y,
                line=dict(color=cor, dash="dot", width=1),
            )
    rotulo = descriptive.ROTULOS[variavel]
    fig.update_layout(
        title=(
            f"Boxplot de {rotulo} ({descriptive.UNIDADE}) por time<br>"
            "<sup>Caixa = Q1–Q3; linha = mediana; tracejado interno = média; "
            "losango = moda; pontilhado = limites 1,5×IQR; pontos = outliers</sup>"
        ),
        yaxis_title=f"{rotulo} ({descriptive.UNIDADE})",
        xaxis_title="Time",
        legend_title="Legenda",
        **LAYOUT,
    )
    return _html(fig)


def barras_comparativas(
    df: pd.DataFrame, variaveis: tuple[str, ...], zscores: pd.DataFrame
) -> str:
    if hasattr(df["time"], "cat"):
        times = list(df["time"].cat.categories)
    else:
        times = sorted(df["time"].astype(str).unique())
    med = df.groupby("time", observed=True)[list(variaveis)].mean()
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=(
            "Média por jogo (escala original)",
            "Z-score da média do time em relação aos 30 times da liga",
        ),
    )
    for i, time in enumerate(times):
        cor = CORES[i % len(CORES)]
        fig.add_trace(go.Bar(
            x=[descriptive.ROTULOS[v] for v in variaveis],
            y=med.loc[time, list(variaveis)],
            name=str(time), marker_color=cor,
            text=[f"{x:.1f}" for x in med.loc[time, list(variaveis)]],
            textposition="outside",
        ), row=1, col=1)
        fig.add_trace(go.Bar(
            x=[descriptive.ROTULOS[v] for v in variaveis],
            y=zscores.loc[time, list(variaveis)],
            name=str(time), marker_color=cor, showlegend=False,
            text=[f"{x:+.2f}" for x in zscores.loc[time, list(variaveis)]],
            textposition="outside",
        ), row=1, col=2)
    fig.update_layout(
        title="Comparação entre times: médias brutas e padronizadas (z-score)",
        barmode="group", legend_title="Time", height=480, **LAYOUT,
    )
    fig.update_yaxes(title_text=f"Média ({descriptive.UNIDADE})", row=1, col=1)
    fig.update_yaxes(title_text="Z-score (desvios padrão)", row=1, col=2, zeroline=True)
    fig.update_xaxes(title_text="Variável", row=1, col=1)
    fig.update_xaxes(title_text="Variável", row=1, col=2)
    return _html(fig)


def histograma_kde(df: pd.DataFrame, variavel: str) -> str:
    if hasattr(df["time"], "cat"):
        times = list(df["time"].cat.categories)
    else:
        times = sorted(df["time"].astype(str).unique())
    fig = make_subplots(rows=1, cols=len(times), subplot_titles=times, shared_yaxes=True)
    for i, time in enumerate(times):
        serie = df.loc[df["time"] == time, variavel]
        cor = CORES[i % len(CORES)]
        sigla = config.TIME_ABREV.get(str(time), str(time))
        fig.add_trace(go.Histogram(
            x=serie, histnorm="probability density",
            name=f"Histograma — {sigla}",
            marker_color=cor, opacity=0.55,
            xbins=dict(size=1 if serie.max() - serie.min() < 30 else None),
        ), row=1, col=i + 1)
        if serie.std() > 0:
            xs = np.linspace(serie.min() - 1, serie.max() + 1, 200)
            fig.add_trace(go.Scatter(
                x=xs, y=stats.gaussian_kde(serie)(xs),
                name=f"KDE — {sigla}",
                line=dict(color=cor, width=2),
            ), row=1, col=i + 1)
        for nome, x, dash in (("média", serie.mean(), "dash"), ("mediana", serie.median(), "dot")):
            fig.add_vline(
                x=x, line=dict(color="black", dash=dash, width=1), row=1, col=i + 1,
                annotation_text=f"{nome} {x:.1f}", annotation_position="top",
                annotation_font_size=10,
            )
        rotulo = descriptive.ROTULOS[variavel]
        fig.update_xaxes(title_text=f"{rotulo} ({descriptive.UNIDADE})", row=1, col=i + 1)
    fig.update_yaxes(title_text="Densidade", row=1, col=1)
    fig.update_layout(
        title=(
            f"Histograma com curva de densidade (KDE) — {descriptive.ROTULOS[variavel]}<br>"
            "<sup>Linha tracejada = média; pontilhada = mediana</sup>"
        ),
        legend_title="Legenda", height=430, **LAYOUT,
    )
    return _html(fig)


def serie_temporal(df: pd.DataFrame, variavel: str) -> str:
    if hasattr(df["time"], "cat"):
        times = list(df["time"].cat.categories)
    else:
        times = sorted(df["time"].astype(str).unique())
    fig = go.Figure()
    for i, time in enumerate(times):
        grupo = df[df["time"] == time]
        fig.add_trace(go.Scatter(
            x=grupo["data_jogo"], y=grupo[variavel],
            mode="lines+markers", name=str(time),
            line=dict(color=CORES[i % len(CORES)], width=1.2), marker_size=5,
        ))
    rotulo = descriptive.ROTULOS[variavel]
    fig.update_layout(
        title=f"{rotulo} ao longo da temporada",
        xaxis_title="Data do jogo",
        yaxis_title=f"{rotulo} ({descriptive.UNIDADE})",
        legend_title="Time", height=380, **LAYOUT,
    )
    return _html(fig)
