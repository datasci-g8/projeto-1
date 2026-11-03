"""Testes da detecção de outliers."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import config
from dashboards.analysis import outliers


@pytest.fixture
def normal():
    rng = np.random.default_rng(0)
    return pd.DataFrame({"x": rng.normal(100, 10, 200)})


@pytest.fixture
def com_outlier(normal):
    df = normal.copy()
    df.loc[0, "x"] = 300
    return df


@pytest.mark.parametrize("nome", list(outliers.METODOS))
def test_interface_comum(normal, nome):
    mascara = outliers.METODOS[nome](normal)
    assert isinstance(mascara, pd.Series)
    assert mascara.dtype == bool
    assert mascara.index.equals(normal.index)


@pytest.mark.parametrize("nome", list(outliers.METODOS))
def test_outlier_injetado_e_detectado(com_outlier, nome):
    assert outliers.METODOS[nome](com_outlier).loc[0]


@pytest.mark.parametrize("nome", ["zscore", "iqr", "grubbs", "lof"])
def test_serie_normal_sem_falsos_positivos_em_excesso(normal, nome):
    assert outliers.METODOS[nome](normal).mean() <= 0.05


def _combinacao_rara() -> pd.DataFrame:
    rng = np.random.default_rng(1)
    x = rng.normal(0, 1, 300)
    df = pd.DataFrame({"x": x, "y": x + rng.normal(0, 0.1, 300)})
    df.loc[0] = [2.0, -2.0]
    return df


@pytest.mark.parametrize("nome", ["knn", "lof", "dbscan"])
def test_vizinhanca_detecta_combinacao_rara(nome):
    assert outliers.METODOS[nome](_combinacao_rara()).loc[0]


def test_ecod_nao_ve_correlacao():
    assert not outliers.ecod(_combinacao_rara()).loc[0]


def test_grubbs_valor_critico_tabelado():
    assert outliers.grubbs_critico(10, 0.05) == pytest.approx(2.290, abs=1e-3)
    assert outliers.grubbs_critico(30, 0.05) == pytest.approx(2.908, abs=1e-3)


def test_grubbs_exemplo_conhecido():
    serie = pd.Series([10, 11, 12, 11, 10, 12, 11, 10, 11, 40], dtype=float)
    assert outliers.grubbs_serie(serie).tolist() == [False] * 9 + [True]


def test_consenso_conta_metodos(com_outlier):
    votos = outliers.consenso(com_outlier)
    assert votos.loc[0] == len(outliers.MULTIVARIADOS)
    assert votos.between(0, len(outliers.MULTIVARIADOS)).all()


def test_iqr_usa_k_do_config():
    serie = pd.Series(range(1, 9), dtype=float)
    inf, sup = outliers.limites_iqr(serie)
    assert (inf, sup) == pytest.approx((2.75 - config.K_IQR * 3.5, 6.25 + config.K_IQR * 3.5))


def test_analise_base_real():
    from dashboards.prep.cleaning import calcular_tratamento
    r = outliers.analisar(calcular_tratamento()["tratado"])
    esperado = len(config.TIMES_GRUPO) * len(config.VARIAVEIS_ANALISE)
    assert len(r["por_coluna"]) == esperado
    assert set(outliers.METODOS).issubset(r["por_coluna"].columns)
    assert set(r["multivariado"]["time"]) == set(config.TIMES_GRUPO)
    assert len(r["sensibilidade"]) == esperado * len(config.SENSIBILIDADE)
    assert "consenso_2+" in r["multivariado"].columns
    liga = r["univariado_liga"]
    assert liga["time"].nunique() == 30
    assert len(liga) == 30 * len(config.VARIAVEIS_ANALISE)
    grupo = liga[liga["time"].isin(config.TIMES_GRUPO)].set_index(["time", "coluna"])
    por_coluna = r["por_coluna"].set_index(["time", "coluna"])
    for m in outliers.UNIVARIADOS:
        assert (grupo[m] == por_coluna[m]).all()


def test_rotas_outliers(client):
    resumo = client.get("/api/outliers/summary")
    assert resumo.status_code == 200
    assert resumo.get_json()["inconsistencias_total"] == 0

    marcados = client.get("/api/outliers?method=iqr&team=Orlando Magic").get_json()
    assert marcados["total"] > 0
    assert {"id_jogo", "data_jogo", "coluna", "valor"}.issubset(marcados["registros"][0])

    multi = client.get("/api/outliers?method=knn&modo=multivariado").get_json()
    assert "coluna" not in multi["registros"][0]
    assert all(1 <= r["n_metodos"] <= 4 for r in multi["registros"])


@pytest.mark.parametrize("query", ["method=xxx", "method=zscore&modo=multivariado",
                                   "method=iqr&team=Boston Celtics", "method=iqr&modo=xxx"])
def test_rotas_outliers_parametros_invalidos(client, query):
    assert client.get(f"/api/outliers?{query}").status_code == 400
