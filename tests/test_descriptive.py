"""Testes da estatística descritiva."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import config
from dashboards.analysis import descriptive


@pytest.fixture
def amostra() -> pd.DataFrame:
    rng = np.random.default_rng(0)
    n = 40
    return pd.DataFrame({
        "time": ["Time A"] * n + ["Time B"] * n,
        "data_jogo": pd.to_datetime(
            ["2025-10-21"] * n + ["2025-10-22"] * n
        ),
        "adversario": ["X"] * n + ["Y"] * n,
        "em_casa": [1] * n + [0] * n,
        "pontos": np.concatenate([rng.normal(110, 8, n), rng.normal(100, 8, n)]),
        "rebotes": np.concatenate([rng.normal(45, 5, n), rng.normal(42, 5, n)]),
        "assistencias": np.concatenate([rng.normal(25, 4, n), rng.normal(22, 4, n)]),
        "roubos": np.concatenate([rng.normal(8, 2, n), rng.normal(7, 2, n)]),
        "tocos": np.concatenate([rng.normal(5, 2, n), rng.normal(4, 2, n)]),
        "faltas": np.concatenate([rng.normal(18, 3, n), rng.normal(19, 3, n)]),
        "tres_pontos_conv": np.concatenate([rng.normal(14, 3, n), rng.normal(12, 3, n)]),
    })


def test_medidas_basicas():
    serie = pd.Series([1, 2, 2, 3, 100], dtype=float)
    m = descriptive.medidas(serie)
    assert m["n"] == 5
    assert m["mediana"] == 2
    assert m["n_outliers"] >= 1
    assert 100 in m["outliers_sup"]


def test_assimetria_direita():
    from scipy import stats

    serie = pd.Series([1, 2, 2, 3, 3, 4, 20], dtype=float)
    g1 = float(stats.skew(serie, bias=False))
    direcao, intensidade = descriptive.classificar_assimetria(g1)
    assert "direita" in direcao
    assert intensidade in {"moderada", "forte"}


def test_classificar_cv():
    assert "baixa" in descriptive.classificar_cv(10)
    assert "média" in descriptive.classificar_cv(20)
    assert "alta" in descriptive.classificar_cv(40)


def test_tabelas_sinteticas(amostra):
    medidas = descriptive.tabela_medidas(amostra)
    assimetria = descriptive.tabela_assimetria(amostra)
    cv = descriptive.tabela_cv(amostra)
    iqr = descriptive.tabela_iqr(amostra)
    esperado = 2 * len(config.VARIAVEIS_ANALISE)
    assert len(medidas) == esperado
    assert len(assimetria) == esperado
    assert len(cv) == esperado
    assert len(iqr) == esperado
    assert (medidas["desvio_padrao"] >= 0).all()
    assert set(assimetria["representante"]).issubset({"média", "mediana"})


def test_iqr_usa_k_do_config():
    serie = pd.Series(range(1, 9), dtype=float)
    _flags, q1, q3, lim_inf, lim_sup = descriptive._iqr_serie(serie)
    iqr = q3 - q1
    assert lim_inf == pytest.approx(q1 - config.K_IQR * iqr)
    assert lim_sup == pytest.approx(q3 + config.K_IQR * iqr)


def test_quadro_resumo(amostra):
    cv = descriptive.tabela_cv(amostra)
    quadro = descriptive.quadro_resumo(cv, "cv_pct")
    assert list(quadro.index) == [descriptive.ROTULOS[v] for v in config.VARIAVEIS_ANALISE]
    assert set(quadro.columns) == {"Time A", "Time B"}


def test_analise_base_real():
    from dashboards.prep.cleaning import calcular_tratamento

    r = descriptive.analisar(calcular_tratamento()["tratado"])
    esperado = len(config.TIMES_GRUPO) * len(config.VARIAVEIS_ANALISE)
    assert len(r["medidas"]) == esperado
    assert len(r["assimetria"]) == esperado
    assert len(r["cv"]) == esperado
    assert len(r["iqr"]) == esperado
    assert set(r["medidas"]["time"]) == set(config.TIMES_GRUPO)
    assert r["parametros"]["k_iqr"] == config.K_IQR
    assert r["parametros"]["ddof"] == config.DDOF
    assert len(r["lista_outliers"]) > 0
    assert set(r["zscore_liga"].index.astype(str)) == set(config.TIMES_GRUPO)


def test_rotas_descriptive(client):
    resumo = client.get("/api/descriptive/summary")
    assert resumo.status_code == 200
    corpo = resumo.get_json()
    assert set(corpo["times"]) == set(config.TIMES_GRUPO)
    assert len(corpo["medidas"]) == len(config.TIMES_GRUPO) * len(config.VARIAVEIS_ANALISE)
    assert "assimetria" in corpo and "cv" in corpo and "iqr" in corpo

    filtrado = client.get(
        "/api/descriptive/summary?team=Orlando Magic&var=pontos"
    ).get_json()
    assert len(filtrado["medidas"]) == 1
    assert filtrado["medidas"][0]["variavel"] == "pontos"

    outliers = client.get("/api/descriptive/outliers?var=pontos").get_json()
    assert outliers["total"] >= 0
    assert "registros" in outliers


@pytest.mark.parametrize(
    "query",
    [
        "team=Boston Celtics",
        "var=xxx",
        "team=Orlando Magic&var=xxx",
    ],
)
def test_rotas_descriptive_parametros_invalidos(client, query):
    assert client.get(f"/api/descriptive/summary?{query}").status_code == 400
    assert client.get(f"/api/descriptive/outliers?{query}").status_code == 400
