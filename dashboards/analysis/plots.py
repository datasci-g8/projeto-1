"""Gráficos Plotly: boxplot anotado, barras comparativas e histograma + KDE."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy import stats

import config
from dashboards.analysis import descriptive
from dashboards import theme

_TRACOS_LINHA = ("solid", "dash", "dot", "dashdot", "longdash", "longdashdot")
LAYOUT_BASE = dict(
    template="plotly_white",
    font=dict(family="Inter, Arial", size=12, color=theme.INK),
    colorway=[theme.PRIMARY, theme.MAGIC, *theme.NEUTRAL_TEAMS],
    paper_bgcolor="#fff",
    plot_bgcolor="#fff",
)


def _html(fig, slot: str = "default"):
    inner = fig.to_html(
        full_html=False, include_plotlyjs=False, config={"responsive": True},
    )
    return f'<div class="chart-block chart-block--{slot}">{inner}</div>'


def _titulos_subplot(fig, yshift: int = 14) -> None:
    """Afasta títulos de subplot do título principal (só anotações de coluna)."""
    for ann in fig.layout.annotations:
        if (
            ann.yref == "paper"
            and ann.y is not None
            and ann.y > 0.9
            and not ann.showarrow
            and ann.xref == "paper"
        ):
            ann.update(yshift=yshift)


def _layout_titulo(texto: str, *, centro: bool = False) -> dict:
    if centro:
        return dict(text=texto, x=0.5, xanchor="center", y=1.0, yanchor="top", pad=dict(t=8))
    return dict(text=texto, x=0, xanchor="left", y=1.0, yanchor="top", pad=dict(t=8))


def _sigla_time(time: str) -> str:
    return config.TIME_ABREV.get(str(time), str(time))


def _eixo_x(fig, *, rows: int = 1, cols: int = 1, angulo: int | None = None) -> None:
    kwargs = dict(automargin=True, title_standoff=14, **theme.PLOTLY_AXIS_X)
    if angulo is not None:
        kwargs["tickangle"] = angulo
    for row in range(1, rows + 1):
        for col in range(1, cols + 1):
            if rows == 1 and cols == 1:
                fig.update_xaxes(**kwargs)
                fig.update_yaxes(**theme.PLOTLY_AXIS_Y)
            else:
                fig.update_xaxes(**kwargs, row=row, col=col)
                fig.update_yaxes(**theme.PLOTLY_AXIS_Y, row=row, col=col)


def _rotulo_direto_serie(fig, x, y, texto: str, cor: str) -> None:
    """Rótulo no fim da linha (legenda integrada, estilo Tufte)."""
    fig.add_annotation(
        x=x,
        y=y,
        text=texto,
        showarrow=False,
        xanchor="left",
        xshift=6,
        font=dict(size=12, color=cor),
    )


def _times_com_dados(df: pd.DataFrame) -> list[str]:
    """Somente times presentes no recorte (não todas as categorias do CSV)."""
    return sorted(df["time"].astype(str).unique())


def _fillcolor(hex_color: str, alpha: float | None = None) -> str:
    if alpha is None:
        alpha = 0.62 if hex_color in (theme.PRIMARY, theme.MAGIC) else 0.4
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def _cor_time(time: str) -> str:
    return theme.team_color(str(time))


def _indice_time(time: str) -> int:
    nome = str(time)
    if nome in config.TIME_ABREV:
        return sorted(config.TIME_ABREV).index(nome)
    return 0


def _estilo_linha(time: str) -> dict:
    nome = str(time).strip()
    cor = _cor_time(nome)
    if nome in config.TIMES_GRUPO:
        return dict(color=cor, width=2.5, dash="solid")
    idx = _indice_time(time)
    return dict(
        color=cor,
        width=1.2,
        dash=_TRACOS_LINHA[idx % len(_TRACOS_LINHA)],
    )


def boxplot(df: pd.DataFrame, variavel: str) -> str:
    fig = go.Figure()
    times = _times_com_dados(df)
    for i, time in enumerate(times):
        serie = df.loc[df["time"].astype(str) == time, variavel]
        m = descriptive.medidas(serie)
        cor = _cor_time(time)
        fig.add_trace(go.Box(
            y=serie,
            name=_sigla_time(time),
            boxpoints="outliers",
            boxmean=True,
            quartilemethod="linear",
            marker=dict(color=cor, outliercolor=cor),
            line=dict(color=cor, width=1.5),
            fillcolor=_fillcolor(cor),
        ))
        modas = [float(x) for x in str(m["moda"]).split(" (")[0].split(", ")]
        sigla = config.TIME_ABREV.get(str(time), str(time))
        fig.add_trace(go.Scatter(
            x=[_sigla_time(time)] * len(modas), y=modas, mode="markers",
            name=f"Moda ({sigla})",
            marker=dict(symbol="diamond", size=11, color="black"),
            showlegend=False,
        ))
        anot = [
            ("Lim. sup.", m["limite_sup"]), ("Q3", m["q3"]), ("Mediana", m["mediana"]),
            ("Média", m["media"]), ("Q1", m["q1"]), ("Lim. inf.", m["limite_inf"]),
        ]
        txt = "<br>".join(f"{k}: {v:.2f}" for k, v in anot)
        txt += f"<br>Outliers sup.: {len(m['outliers_sup'])}; inf.: {len(m['outliers_inf'])}"
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
        **LAYOUT_BASE,
        title=_layout_titulo(f"Boxplot de {rotulo} ({descriptive.UNIDADE}) por time"),
        yaxis_title=f"{rotulo} ({descriptive.UNIDADE})",
        xaxis_title="Time (sigla)",
        showlegend=False,
        height=theme.CHART_HEIGHT_BOX,
        margin=theme.chart_margin(wide_right=True),
    )
    _eixo_x(fig)
    fig.update_layout(title_font=dict(size=14, color=theme.PRIMARY))
    return _html(fig, "box")


def barras_comparativas(
    df: pd.DataFrame, variaveis: tuple[str, ...], zscores: pd.DataFrame
) -> str:
    times = _times_com_dados(df)
    med = df.groupby(df["time"].astype(str), observed=True)[list(variaveis)].mean()
    fig = make_subplots(
        rows=1,
        cols=2,
        column_widths=[0.5, 0.5],
        horizontal_spacing=theme.CHART_SUBPLOT_SPACING,
        subplot_titles=(
            "Média por jogo (escala original)",
            "Z-score da média do time em relação aos 30 times da liga",
        ),
    )
    for time in times:
        cor = _cor_time(time)
        rotulo_time = _sigla_time(time)
        marcador = dict(color=cor, line=dict(color=cor, width=1))
        fig.add_trace(go.Bar(
            x=[descriptive.ROTULOS[v] for v in variaveis],
            y=med.loc[time, list(variaveis)],
            name=rotulo_time,
            marker=marcador,
            text=[f"{x:.1f}" for x in med.loc[time, list(variaveis)]],
            textposition="outside",
        ), row=1, col=1)
        fig.add_trace(go.Bar(
            x=[descriptive.ROTULOS[v] for v in variaveis],
            y=zscores.loc[time, list(variaveis)],
            name=rotulo_time,
            marker=marcador,
            showlegend=False,
            text=[f"{x:+.2f}" for x in zscores.loc[time, list(variaveis)]],
            textposition="outside",
        ), row=1, col=2)
    fig.update_layout(
        **LAYOUT_BASE,
        title=_layout_titulo(
            "Comparação entre times: médias brutas e padronizadas (z-score)",
            centro=True,
        ),
        barmode="group",
        legend=theme.chart_legend_top(),
        height=theme.CHART_HEIGHT_BAR,
        margin=theme.chart_margin(subplot=True, legend_top=True),
    )
    _titulos_subplot(fig, yshift=22)
    fig.update_yaxes(title_text=f"Média ({descriptive.UNIDADE})", row=1, col=1)
    fig.update_yaxes(title_text="Z-score (desvios padrão)", row=1, col=2, zeroline=True)
    fig.update_xaxes(tickangle=-35, title_text="Variável", row=1, col=1)
    fig.update_xaxes(tickangle=-35, title_text="Variável", row=1, col=2)
    _eixo_x(fig, rows=1, cols=2, angulo=-35)
    fig.update_layout(title_font=dict(size=14, color=theme.PRIMARY))
    return _html(fig, "bar")


def histograma_kde(df: pd.DataFrame, variavel: str) -> str:
    times = _times_com_dados(df)
    titulos = [_sigla_time(t) for t in times]
    fig = make_subplots(
        rows=1,
        cols=len(times),
        subplot_titles=titulos,
        shared_yaxes=True,
        horizontal_spacing=theme.CHART_SUBPLOT_SPACING,
    )
    for i, time in enumerate(times):
        serie = df.loc[df["time"].astype(str) == time, variavel]
        cor = _cor_time(time)
        opac = 0.72 if cor in (theme.PRIMARY, theme.MAGIC) else 0.55
        fig.add_trace(go.Histogram(
            x=serie, histnorm="probability density",
            name=str(time),
            marker=dict(color=cor, line=dict(color=cor, width=0.5)),
            opacity=opac,
            showlegend=False,
            xbins=dict(size=1 if serie.max() - serie.min() < 30 else None),
        ), row=1, col=i + 1)
        if serie.std() > 0:
            xs = np.linspace(serie.min() - 1, serie.max() + 1, 200)
            fig.add_trace(go.Scatter(
                x=xs, y=stats.gaussian_kde(serie)(xs),
                name=str(time),
                line=dict(color=cor, width=2),
                showlegend=False,
            ), row=1, col=i + 1)
        for _nome, x, dash in (("média", serie.mean(), "dash"), ("mediana", serie.median(), "dot")):
            fig.add_vline(
                x=x,
                line=dict(color="black", dash=dash, width=1),
                row=1,
                col=i + 1,
            )
        rotulo = descriptive.ROTULOS[variavel]
        fig.update_xaxes(
            title_text=f"{rotulo} ({descriptive.UNIDADE})",
            row=1,
            col=i + 1,
        )
    fig.update_yaxes(title_text="Densidade", row=1, col=1)
    altura = theme.CHART_HEIGHT_HIST + 36 * max(0, len(times) - 1)
    fig.update_layout(
        **LAYOUT_BASE,
        title=_layout_titulo(
            f"Histograma com curva de densidade (KDE), {descriptive.ROTULOS[variavel]}"
        ),
        showlegend=False,
        height=altura,
        margin=theme.chart_margin(subplot=True),
    )
    _titulos_subplot(fig, yshift=18)
    _eixo_x(fig, rows=1, cols=len(times))
    fig.update_layout(title_font=dict(size=14, color=theme.PRIMARY))
    return _html(fig, "hist")


def serie_temporal(df: pd.DataFrame, variavel: str) -> str:
    times = _times_com_dados(df)
    fig = go.Figure()
    for time in times:
        grupo = df[df["time"].astype(str) == time]
        estilo = _estilo_linha(str(time))
        sigla = _sigla_time(time)
        fig.add_trace(go.Scatter(
            x=grupo["data_jogo"], y=grupo[variavel],
            mode="lines+markers", name=sigla,
            line=dict(width=estilo["width"], color=estilo["color"], dash=estilo["dash"]),
            marker=dict(size=4, color=estilo["color"]),
            showlegend=False,
        ))
        ult = grupo.iloc[-1]
        _rotulo_direto_serie(
            fig, ult["data_jogo"], ult[variavel], sigla, estilo["color"],
        )
    rotulo = descriptive.ROTULOS[variavel]
    fig.update_layout(
        **LAYOUT_BASE,
        title=_layout_titulo(f"{rotulo} ao longo da temporada"),
        xaxis_title="Data do jogo",
        yaxis_title=f"{rotulo} ({descriptive.UNIDADE})",
        showlegend=False,
        height=theme.CHART_HEIGHT_SERIES,
        margin=theme.chart_margin(),
        title_font=dict(size=14, color=theme.PRIMARY),
    )
    _eixo_x(fig)
    return _html(fig, "series")
