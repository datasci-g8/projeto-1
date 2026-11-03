"""Contrato de cores por time (identidade visual)."""
from __future__ import annotations

import config
from dashboards import theme


def test_team_color_cobre_todos_os_times():
    for nome in config.TIME_ABREV:
        assert theme.team_color(nome).startswith("#")


def test_cores_marca_do_grupo():
    assert theme.team_color("Golden State Warriors") == theme.PRIMARY
    assert theme.team_color("Orlando Magic") == theme.MAGIC
    assert theme.team_color("GSW") == theme.PRIMARY
    assert theme.team_color("ORL") == theme.MAGIC


def test_cor_fixa_nao_depende_da_ordem():
    boston = theme.team_color("Boston Celtics")
    assert theme.team_color("Boston Celtics") == boston
    assert theme.team_color("Golden State Warriors") == theme.PRIMARY
