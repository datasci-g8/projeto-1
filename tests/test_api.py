"""Testes do contrato HTTP das rotas de qualidade."""
from __future__ import annotations

import config
from dashboards.api import quality


def test_summary(client):
    resposta = client.get("/api/quality/summary")
    assert resposta.status_code == 200
    dados = resposta.get_json()
    assert dados["antes"]["linhas"] == 2238
    assert dados["depois"]["issues"] == 0
    assert dados["antes"]["ausentes"] == 0
    assert dados["base"]["times"] == 30


def test_issues_sem_filtro(client):
    resposta = client.get("/api/quality/issues")
    assert resposta.status_code == 200
    dados = resposta.get_json()
    assert dados["total"] == 0
    assert dados["issues"] == []


def test_issues_filtro_regra_valida(client):
    resposta = client.get("/api/quality/issues?regra=valor_ausente")
    assert resposta.status_code == 200
    assert resposta.get_json()["total"] == 0


def test_issues_regra_invalida(client):
    resposta = client.get("/api/quality/issues?regra=nao_existe")
    assert resposta.status_code == 400
    assert "erro" in resposta.get_json()


def test_issues_time_invalido(client):
    resposta = client.get("/api/quality/issues?time=Time+Fantasma")
    assert resposta.status_code == 400
    assert "erro" in resposta.get_json()


def test_regras(client):
    resposta = client.get("/api/quality/regras")
    assert resposta.status_code == 200
    dados = resposta.get_json()
    assert len(dados) >= 20
    assert {"regra", "descricao", "decisao"} == set(dados[0])


def test_index_e_health(client):
    assert client.get("/").status_code == 200
    saude = client.get("/api/health")
    assert saude.status_code == 200
    dados = saude.get_json()
    assert dados["status"] == "ok"
    assert not dados["base"].startswith("/")


def test_issues_filtro_time_valido(client):
    resposta = client.get("/api/quality/issues?time=Golden+State+Warriors")
    assert resposta.status_code == 200
    assert resposta.get_json()["total"] == 0


def test_summary_nao_grava_base(client, monkeypatch, tmp_path):
    quality.limpar_cache()
    monkeypatch.setattr(config, "CLEAN_CSV", tmp_path / "clean.csv")
    resposta = client.get("/api/quality/summary")
    assert resposta.status_code == 200
    assert not (tmp_path / "clean.csv").exists()
    quality.limpar_cache()


def test_erro_de_base_vira_json(client, monkeypatch, tmp_path):
    quality.limpar_cache()
    monkeypatch.setattr(config, "RAW_CSV", tmp_path / "nao_existe.csv")
    client.application.config["PROPAGATE_EXCEPTIONS"] = False
    resposta = client.get("/api/quality/summary")
    assert resposta.status_code == 500
    assert resposta.is_json
    assert "erro" in resposta.get_json()
    quality.limpar_cache()


def test_404_vira_json(client):
    resposta = client.get("/nao-existe")
    assert resposta.status_code == 404
    assert resposta.is_json
    assert "erro" in resposta.get_json()