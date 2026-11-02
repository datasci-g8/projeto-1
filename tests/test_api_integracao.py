"""Contrato HTTP das rotas missing, outliers e descritiva."""
from __future__ import annotations


def test_missing_summary(client):
    resposta = client.get("/api/missing/summary")
    assert resposta.status_code == 200
    dados = resposta.get_json()
    assert dados["total_ausentes"] == 0
    assert "por_coluna" in dados


def test_missing_tests(client):
    resposta = client.get("/api/missing/tests")
    assert resposta.status_code == 200
    dados = resposta.get_json()
    assert "testes" in dados
    assert "little" in dados["testes"]


def test_outliers_summary(client):
    resposta = client.get("/api/outliers/summary")
    assert resposta.status_code == 200
    dados = resposta.get_json()
    assert "por_coluna" in dados
    assert len(dados["por_coluna"]) > 0


def test_outliers_registros(client):
    resposta = client.get("/api/outliers?method=iqr&modo=coluna")
    assert resposta.status_code == 200


def test_descriptive_summary(client):
    resposta = client.get("/api/descriptive/summary")
    assert resposta.status_code == 200
    dados = resposta.get_json()
    assert "medidas" in dados
    assert "quadro_cv" in dados


def test_descriptive_parametro_invalido(client):
    assert client.get("/api/descriptive/summary?team=Time+Fantasma").status_code == 400


def test_consenso_multivariado_vazio_tem_esquema():
    from dashboards.api.quality import resultado_atual
    from dashboards.web.panel import _consenso_multivariado

    df = resultado_atual()["tratado"]
    vazio = _consenso_multivariado(df, ())
    assert list(vazio.columns) == ["time", "indice", "n_metodos"]
    assert vazio.empty


def test_paginas_html(client):
    for rota in (
        "/",
        "/quality",
        "/outliers",
        "/descriptive",
        "/skewness",
        "/cv",
        "/iqr",
        "/synthesis",
    ):
        assert client.get(rota).status_code == 200
