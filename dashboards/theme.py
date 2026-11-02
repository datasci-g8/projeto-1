"""Cores do painel web e dos gráficos Plotly."""
from __future__ import annotations

import config

PRIMARY = "#1D428A"  # Golden State Warriors (UI e gráficos)
MAGIC = "#F58426"  # Orlando Magic
NEUTRAL_TEAMS = ("#6B7280", "#9CA3AF", "#4B5563", "#B0B7C3", "#374151", "#8A93A0")
INK = "#5c6370"  # alinhado a --color-text-muted (eixos)

# Eixos inspirados em Tufte: grid horizontal leve, sem grid vertical, linha de base no X.
PLOTLY_AXIS_X = dict(
    showgrid=False,
    showline=True,
    linewidth=1,
    linecolor="#cbd5e1",
    ticks="outside",
    tickcolor="#cbd5e1",
)
PLOTLY_AXIS_Y = dict(
    showgrid=True,
    gridcolor="#eef1f6",
    gridwidth=1,
    zeroline=False,
    showline=False,
)

# Alturas e margens dos gráficos (Plotly)
CHART_HEIGHT_BAR = 480
CHART_HEIGHT_BOX = 520
CHART_HEIGHT_SERIES = 380
CHART_HEIGHT_HIST = 430
CHART_SUBPLOT_SPACING = 0.1
CHART_LEGEND_KW = dict(
    orientation="h",
    x=0.5,
    xanchor="center",
    yanchor="top",
    bgcolor="rgba(255,255,255,0.95)",
    bordercolor="#dde3ee",
    borderwidth=1,
)


def chart_legend_top() -> dict:
    """Legenda horizontal abaixo do título (coord. paper), longe do eixo X."""
    return {
        **CHART_LEGEND_KW,
        "orientation": "h",
        "yanchor": "top",
        "y": 0.90,
        "x": 0.5,
        "xanchor": "center",
    }


def chart_margin(
    *,
    subplot: bool = False,
    wide_right: bool = False,
    legend_top: bool = False,
) -> dict:
    """Margens por tipo de figura."""
    return dict(
        l=60,
        r=130 if wide_right else 40,
        t=118 if legend_top else (92 if subplot else 78),
        b=110 if subplot else 72,
    )

_OTHER_TEAMS = sorted(n for n in config.TIME_ABREV if n not in config.TIMES_GRUPO)


def team_color(team: str) -> str:
    """Cor fixa por nome do time (não depende da ordem na seleção do filtro)."""
    nome = str(team).strip()
    if nome in (config.TIMES_GRUPO[0], config.TIME_ABREV[config.TIMES_GRUPO[0]]):
        return PRIMARY
    if nome in (config.TIMES_GRUPO[1], config.TIME_ABREV[config.TIMES_GRUPO[1]]):
        return MAGIC
    if team in _OTHER_TEAMS:
        return NEUTRAL_TEAMS[_OTHER_TEAMS.index(team) % len(NEUTRAL_TEAMS)]
    return NEUTRAL_TEAMS[0]
