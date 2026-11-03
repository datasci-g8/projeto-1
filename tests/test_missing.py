"""Testes da análise de ausentes (#2)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import config
from dashboards.analysis import missing


@pytest.fixture(scope="module")
def variaveis():
    from dashboards.prep.loader import carregar_tratado
    return carregar_tratado()[list(config.VARIAVEIS_ANALISE)]


def test_contagem_com_ausentes_conhecidos():
    df = pd.DataFrame({"a": [1, np.nan, 3, np.nan], "b": [1, 2, 3, 4], "c": [np.nan] * 4})
    tabela = missing.contar_ausentes(df).set_index("coluna")
    assert tabela.loc["a", "ausentes"] == 2
    assert tabela.loc["b", "ausentes"] == 0
    assert tabela.loc["c", "percentual"] == 100.0


def test_contagem_por_time():
    df = pd.DataFrame({"time": ["X", "X", "Y"], "v": [np.nan, 1, np.nan]})
    tabela = missing.contar_por_time(df).set_index("time")
    assert tabela.loc["X", "ausentes"] == 1
    assert tabela.loc["Y", "colunas_com_ausentes"] == {"v": 1}


def test_padroes_ausencia():
    df = pd.DataFrame({"a": [np.nan, np.nan, 1], "b": [np.nan, 2, 3]})
    padroes = {tuple(p): n for p, n in missing.padroes_ausencia(df).itertuples(index=False)}
    assert padroes == {("a", "b"): 1, ("a",): 1, (): 1}


@pytest.mark.parametrize("mecanismo", missing.MECANISMOS)
def test_simulacao_apaga_so_a_coluna_alvo(variaveis, mecanismo):
    simulado = missing.simular_ausencia(variaveis, mecanismo)
    ausentes = simulado.isna().sum()
    assert ausentes[config.COLUNA_ALVO_AUSENCIA] > 0
    assert ausentes.drop(config.COLUNA_ALVO_AUSENCIA).sum() == 0
    assert variaveis.isna().sum().sum() == 0


def test_em_sem_ausentes_e_a_estimativa_de_maxima_verossimilhanca(variaveis):
    X = variaveis.to_numpy(float)
    mu, sigma = missing.estimar_em(X)
    assert np.allclose(mu, X.mean(axis=0))
    assert np.allclose(sigma, np.cov(X, rowvar=False, ddof=0))


def test_em_recupera_parametros_com_ausencia_mcar():
    rng = np.random.default_rng(0)
    cov = np.array([[1.0, 0.8], [0.8, 1.0]])
    X = rng.multivariate_normal([10, 20], cov, 4000)
    X[rng.random(4000) < 0.3, 1] = np.nan
    mu, sigma = missing.estimar_em(X)
    assert mu == pytest.approx([10, 20], abs=0.1)
    assert sigma == pytest.approx(cov, abs=0.1)


def test_little_mcar_em_varias_colunas(variaveis):
    rng = np.random.default_rng(config.SEMENTE)
    simulado = variaveis.mask(rng.random(variaveis.shape) < 0.05)
    resultado = missing.teste_little(simulado)
    assert resultado["padroes"] > 2
    assert resultado["conclusao"] == "não rejeita MCAR"


def test_base_sem_ausentes_nao_aplica_testes(variaveis):
    for resultado in missing.executar_testes(variaveis).values():
        assert resultado["p_valor"] is None
        assert resultado["conclusao"].startswith("não aplicável")


@pytest.mark.parametrize("teste", missing.TESTES)
def test_mcar_nao_rejeitado_e_mar_rejeitado(variaveis, teste):
    funcao = getattr(missing, f"teste_{teste}")
    mcar = funcao(missing.simular_ausencia(variaveis, "MCAR"))
    mar = funcao(missing.simular_ausencia(variaveis, "MAR"))
    assert mcar["conclusao"] == "não rejeita MCAR", mcar["p_valor"]
    assert mar["conclusao"] == "rejeita MCAR", mar["p_valor"]


def test_fairclough_aponta_a_variavel_causadora(variaveis):
    resultado = missing.teste_fairclough(missing.simular_ausencia(variaveis, "MAR"))
    coefs = resultado["por_coluna"][0]["coeficientes"]
    assert max(coefs, key=lambda c: abs(c["z"]))["variavel"] == config.COLUNA_CAUSA_MAR


def test_analise_usa_base_original():
    from dashboards.prep.loader import carregar_bruto
    r = missing.analisar(carregar_bruto())
    assert r["base"] == {"arquivo": config.RAW_CSV.name, "linhas": 2238, "colunas": 28}
    assert list(r["por_coluna"]["coluna"]) == config.COLUNAS_ESPERADAS
    assert r["variaveis_testadas"] == ["PTS", "REB", "AST", "STL", "BLK", "PF", "FG3M"]
    assert all(t["p_valor"] is None for t in r["testes"].values())


def test_rotas_missing(client):
    resumo = client.get("/api/missing/summary").get_json()
    assert resumo["total_ausentes"] == 0
    assert resumo["base"]["colunas"] == 28
    assert len(resumo["por_time"]) == 30
    testes = client.get("/api/missing/tests").get_json()
    assert set(testes["testes"]) == set(missing.TESTES)
