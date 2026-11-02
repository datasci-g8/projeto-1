"""Fixtures compartilhadas dos testes.

A base sintética tem 2 times, 4 jogos e 8 linhas — pequena, mas passa em
todas as regras da #1. Cada teste de regra muta uma cópia dessa base.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import config
from main import create_app


def _linha(
    id_jogo: int,
    data: str,
    time: str,
    adversario: str,
    em_casa: bool,
    pontos: int,
    vitorias: int,
    derrotas: int,
    vitoria: int,
) -> dict:
    fgm, fga, fg3m, fg3a = 40, 85, 10, 30
    ftm = pontos - 2 * fgm - fg3m
    fta = ftm + 2
    return {
        "Team_ID": config.ID_TIME[time],
        "Game_ID": id_jogo,
        "GAME_DATE": data,
        "MATCHUP": f"{config.TIME_ABREV[time]} {'vs.' if em_casa else '@'} {config.TIME_ABREV[adversario]}",
        "WL": vitoria,
        "W": vitorias,
        "L": derrotas,
        "W_PCT": round(vitorias / (vitorias + derrotas), 3),
        "MIN": 240,
        "FGM": fgm,
        "FGA": fga,
        "FG_PCT": round(fgm / fga, 3),
        "FG3M": fg3m,
        "FG3A": fg3a,
        "FG3_PCT": round(fg3m / fg3a, 3),
        "FTM": ftm,
        "FTA": fta,
        "FT_PCT": round(ftm / fta, 3),
        "OREB": 10,
        "DREB": 30,
        "REB": 40,
        "AST": 25,
        "STL": 8,
        "BLK": 5,
        "TOV": 12,
        "PF": 18,
        "PTS": 2 * fgm + fg3m + ftm,
        "TEAM_NAME": time,
    }


def base_bruta() -> pd.DataFrame:
    """Quatro jogos entre GSW e ORL, com acumulados e MATCHUP corretos."""
    jogos = [
        (1, "2025-10-21", "Golden State Warriors", "Orlando Magic", 110, 100),
        (2, "2025-10-23", "Orlando Magic", "Golden State Warriors", 105, 101),
        (3, "2025-10-25", "Golden State Warriors", "Orlando Magic", 120, 115),
        (4, "2025-10-27", "Orlando Magic", "Golden State Warriors", 98, 99),
    ]
    registro = {"Golden State Warriors": [0, 0], "Orlando Magic": [0, 0]}
    linhas = []
    for id_jogo, data, casa, fora, pontos_casa, pontos_fora in jogos:
        venceu_casa = pontos_casa > pontos_fora
        for time, adversario, em_casa, pontos, venceu in (
            (casa, fora, True, pontos_casa, venceu_casa),
            (fora, casa, False, pontos_fora, not venceu_casa),
        ):
            registro[time][0] += int(venceu)
            registro[time][1] += int(not venceu)
            linhas.append(
                _linha(
                    id_jogo,
                    data,
                    time,
                    adversario,
                    em_casa,
                    pontos,
                    registro[time][0],
                    registro[time][1],
                    int(venceu),
                )
            )
    return pd.DataFrame(linhas, columns=config.COLUNAS_ESPERADAS)


@pytest.fixture
def base() -> pd.DataFrame:
    return base_bruta()


@pytest.fixture
def client():
    app = create_app()
    app.config.update(TESTING=True)
    return app.test_client()
