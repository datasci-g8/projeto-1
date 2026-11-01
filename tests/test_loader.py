"""Testes do contrato de leitura e tratamento da base."""
import pandas as pd
import pytest

import config
from dashboards.prep import loader


def test_tratar_renomeia_e_deriva(base):
    df = loader.tratar(base)
    assert "data_jogo" in df.columns and "confronto" not in df.columns
    assert pd.api.types.is_datetime64_any_dtype(df["data_jogo"])
    assert {"em_casa", "prorrogacao", "adversario", "sigla", "mes", "dia_semana"}.issubset(df.columns)
    assert df["em_casa"].isin([0, 1]).all()
    assert df["prorrogacao"].isin([0, 1]).all()
    assert df.loc[df["em_casa"] == 1, "sigla"].astype(str).isin(["GSW", "ORL"]).all()


def test_coluna_ausente_falha(base):
    with pytest.raises(loader.ErroBaseDados):
        loader.tratar(base.drop(columns=["PTS"]))


def test_coluna_extra_falha(base):
    with pytest.raises(loader.ErroBaseDados):
        loader.tratar(base.assign(EXTRA=1))


def test_dicionario_tem_todas_as_colunas():
    tabela = loader.tabela_dicionario()
    assert len(tabela) == 34
    assert {"coluna_original", "coluna_nova", "tipo", "descricao", "situacao"}.issubset(tabela.columns)


def test_colunas_modelagem_remove_vazamento(base):
    df = loader.tratar(base)
    modelo = loader.colunas_modelagem(df)
    for coluna in config.COLUNAS_EXCLUIDAS_MODELAGEM:
        assert coluna not in modelo.columns
    assert "pontos" in modelo.columns


def test_hash_arquivo_detecta_mudanca(tmp_path, base):
    caminho = tmp_path / "base.csv"
    base.to_csv(caminho, index=False)
    antes = loader.hash_arquivo(caminho)
    base.to_csv(caminho, index=False)
    assert loader.hash_arquivo(caminho) == antes
    base.loc[0, "PTS"] += 1
    base.to_csv(caminho, index=False)
    assert loader.hash_arquivo(caminho) != antes

def test_tratar_rejeita_tipo_invalido(base):
    ruim = base.copy()
    ruim["TEAM_NAME"] = 123
    with pytest.raises(loader.ErroBaseDados):
        loader.tratar(ruim)


def test_data_invalida_falha(base):
    ruim = base.copy()
    ruim.loc[ruim.index[0], "GAME_DATE"] = "2025-13-01"
    with pytest.raises(loader.ErroBaseDados):
        loader.tratar(ruim)


def test_base_vazia_falha(base, tmp_path):
    caminho = tmp_path / "vazia.csv"
    base.iloc[0:0].to_csv(caminho, index=False)
    with pytest.raises(loader.ErroBaseDados):
        loader.ler_bruto(caminho)


def test_arquivo_ausente(tmp_path):
    with pytest.raises(FileNotFoundError):
        loader.ler_bruto(tmp_path / "nao_existe.csv")


def test_carregar_tratado(base, tmp_path):
    caminho = tmp_path / "base.csv"
    base.to_csv(caminho, index=False)
    df = loader.carregar_tratado(caminho)
    assert len(df) == len(base)
    assert "data_jogo" in df.columns

def test_numerico_invalido_falha(base):
    ruim = base.copy()
    ruim["PTS"] = "x"
    with pytest.raises(loader.ErroBaseDados):
        loader.tratar(ruim)
