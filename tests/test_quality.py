"""Testes das regras de qualidade, duplicatas e relatório."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import config
from dashboards.prep import cleaning
from dashboards.prep.loader import hash_arquivo, tratar


# ---------------------------------------------------------------------------
# Cada mutação deve disparar exatamente a regra indicada (podendo disparar
# outras também; o alvo precisa aparecer).
# ---------------------------------------------------------------------------
def _mutar(df, indice, coluna, valor):
    df.loc[df.index[indice], coluna] = valor
    return df


def mut_pontos(df):
    return _mutar(df, 0, "PTS", df.loc[df.index[0], "PTS"] + 1)


def mut_rebotes(df):
    return _mutar(df, 0, "REB", df.loc[df.index[0], "REB"] + 1)


def mut_pct_arremessos(df):
    return _mutar(df, 0, "FG_PCT", df.loc[df.index[0], "FG_PCT"] + 0.01)


def mut_pct_tres(df):
    return _mutar(df, 0, "FG3_PCT", df.loc[df.index[0], "FG3_PCT"] + 0.01)


def mut_pct_lances(df):
    return _mutar(df, 0, "FT_PCT", df.loc[df.index[0], "FT_PCT"] + 0.01)


def mut_convertidos(df):
    return _mutar(df, 0, "FGM", df.loc[df.index[0], "FGA"] + 1)


def mut_minutos_invalidos(df):
    return _mutar(df, 0, "MIN", 200)


def mut_pct_vitorias(df):
    return _mutar(df, 0, "W_PCT", 0.95)


def mut_acumulado_ordem(df):
    return _mutar(df, 0, "W", df.loc[df.index[0], "W"] + 1)


def mut_acumulado_incremento(df):
    return _mutar(df, 2, "W", df.loc[df.index[2], "W"] + 1)


def mut_negativo(df):
    return _mutar(df, 0, "STL", -1)


def mut_fora_dominio(df):
    return _mutar(df, 0, "FG_PCT", 1.2)


def mut_ausente(df):
    return _mutar(df, 0, "STL", np.nan)


def mut_time_desconhecido(df):
    return _mutar(df, 0, "TEAM_NAME", "Time Fantasma")


def mut_time_id(df):
    return _mutar(df, 0, "Team_ID", config.ID_TIME["Orlando Magic"])


def mut_abreviacao(df):
    return _mutar(df, 0, "MATCHUP", "XXX vs. ORL")


def mut_adversario(df):
    return _mutar(df, 0, "MATCHUP", "GSW vs. XXX")


def mut_local(df):
    return _mutar(df, 0, "MATCHUP", "GSW @ ORL")


def mut_jogo_incompleto(df):
    return df.drop(df.index[0])


def mut_sem_vencedor(df):
    df.loc[df["Game_ID"] == 1, "WL"] = 0
    return df


def mut_vencedor_pontos(df):
    return _mutar(df, 0, "PTS", 90)


def mut_data_divergente(df):
    return _mutar(df, 0, "GAME_DATE", "2025-10-22")


def mut_minutos_divergente(df):
    return _mutar(df, 0, "MIN", 265)


def mut_duplicata_time_data(df):
    df.loc[df["Game_ID"] == 1, "GAME_DATE"] = "2025-10-23"
    return df


def mut_contagem_nao_inteira(df):
    return _mutar(df.astype({"AST": float}), 0, "AST", 25.5)


def mut_tres_convertidos(df):
    # FG3M > FGM, mantendo FG3M <= FG3A para isolar a regra.
    df = _mutar(df, 0, "FG3A", 60)
    return _mutar(df, 0, "FG3M", df.loc[df.index[0], "FGM"] + 1)


def mut_tres_tentados(df):
    return _mutar(df, 0, "FG3A", df.loc[df.index[0], "FGA"] + 1)


def mut_limite_temporada(df):
    return _mutar(df, 0, "L", config.JOGOS_TEMPORADA_REGULAR)


def mut_duplicata_confronto_data(df):
    copia = df[df["Game_ID"] == 1].copy()
    copia["Game_ID"] = 99
    return pd.concat([df, copia], ignore_index=True)


CASOS = [
    ("pontos_formula", mut_pontos, "pontos_formula"),
    ("rebotes_formula", mut_rebotes, "rebotes_formula"),
    ("pct_arremessos", mut_pct_arremessos, "pct_arremessos"),
    ("pct_tres_pontos", mut_pct_tres, "pct_tres_pontos"),
    ("pct_lances_livres", mut_pct_lances, "pct_lances_livres"),
    ("convertidos_maior_tentados", mut_convertidos, "convertidos_maior_tentados"),
    ("minutos_invalidos", mut_minutos_invalidos, "minutos_invalidos"),
    ("pct_vitorias_acumulado", mut_pct_vitorias, "pct_vitorias_acumulado"),
    ("acumulado_ordem", mut_acumulado_ordem, "acumulado_ordem"),
    ("acumulado_incremento", mut_acumulado_incremento, "acumulado_incremento"),
    ("valor_negativo", mut_negativo, "valor_negativo"),
    ("fora_dominio", mut_fora_dominio, "fora_dominio"),
    ("valor_ausente", mut_ausente, "valor_ausente"),
    ("time_desconhecido", mut_time_desconhecido, "time_desconhecido"),
    ("time_id_divergente", mut_time_id, "time_id_divergente"),
    ("abreviacao_time", mut_abreviacao, "abreviacao_time"),
    ("adversario_divergente", mut_adversario, "adversario_divergente"),
    ("local_inconsistente", mut_local, "local_inconsistente"),
    ("jogo_incompleto", mut_jogo_incompleto, "jogo_incompleto"),
    ("jogo_sem_vencedor", mut_sem_vencedor, "jogo_sem_vencedor"),
    ("vencedor_pontos", mut_vencedor_pontos, "vencedor_pontos"),
    ("data_divergente", mut_data_divergente, "data_divergente"),
    ("minutos_divergente", mut_minutos_divergente, "minutos_divergente"),
    ("duplicata_time_data", mut_duplicata_time_data, "duplicata_time_data"),
    ("duplicata_confronto_data", mut_duplicata_confronto_data, "duplicata_confronto_data"),
    ("contagem_nao_inteira", mut_contagem_nao_inteira, "contagem_nao_inteira"),
    ("tres_convertidos", mut_tres_convertidos, "tres_maior_arremessos"),
    ("tres_tentados", mut_tres_tentados, "tres_maior_arremessos"),
    ("limite_temporada", mut_limite_temporada, "limite_temporada"),
]


def test_base_sintetica_e_valida(base):
    issues = cleaning.coletar_issues(tratar(base))
    assert issues.empty, issues.to_string()


@pytest.mark.parametrize("nome,mutacao,regra", CASOS, ids=[c[0] for c in CASOS])
def test_regra_detectada(base, nome, mutacao, regra):
    bruto = base.copy()
    issues = cleaning.coletar_issues(tratar(mutacao(bruto)))
    assert regra in set(issues["regra"]), f"{nome}: regras encontradas = {sorted(set(issues['regra']))}"


def test_remover_duplicata_exata(base):
    bruto = pd.concat([base, base.iloc[[0]]], ignore_index=True)
    tratado = tratar(bruto)
    limpo, relatorio = cleaning.remover_duplicatas(tratado)
    assert relatorio["exatas"] == 1
    assert len(limpo) == len(tratado) - 1


def test_remover_duplicata_time_jogo(base):
    bruto = base.copy()
    bruto.loc[bruto.index[0], "PTS"] += 1
    tratado = tratar(pd.concat([base, bruto.iloc[[0]]], ignore_index=True))
    limpo, relatorio = cleaning.remover_duplicatas(tratado)
    assert relatorio["exatas"] == 0
    assert relatorio["time_jogo"] == 1
    assert len(limpo) == len(tratado) - 1


def test_resumo_tem_antes_e_depois(base, tmp_path):
    bruto = tmp_path / "raw.csv"
    base.to_csv(bruto, index=False)
    resultado = cleaning.executar_tratamento(caminho_bruto=bruto, caminho_limpo=tmp_path / "clean.csv")
    resumo = resultado["resumo"]
    assert resumo["antes"]["linhas"] == len(base)
    assert resumo["depois"]["linhas"] == len(base)
    assert resumo["depois"]["issues"] == 0
    assert resumo["base"]["arquivo_bruto"] == str(bruto)
    assert resumo["depois"]["linhas_com_flag"] == 0
    assert set(resumo["por_regra"]).issuperset({"pontos_formula", "jogo_incompleto"})
    assert (tmp_path / "clean.csv").exists()


def test_calcular_nao_grava(base, tmp_path):
    bruto = tmp_path / "raw.csv"
    base.to_csv(bruto, index=False)
    limpo = tmp_path / "clean.csv"
    resultado = cleaning.calcular_tratamento(caminho_bruto=bruto, caminho_limpo=limpo)
    assert resultado["tratado"].shape[0] == len(base)
    assert not limpo.exists()


def test_duplicata_removida_aparece_nas_issues(base, tmp_path):
    bruto = tmp_path / "dup.csv"
    pd.concat([base, base.iloc[[0]]], ignore_index=True).to_csv(bruto, index=False)
    resultado = cleaning.executar_tratamento(caminho_bruto=bruto, caminho_limpo=tmp_path / "clean.csv")
    assert resultado["duplicatas"]["total"] == 1
    assert set(resultado["issues"]["regra"]) == {"duplicata_exata"}
    assert resultado["resumo"]["por_regra"]["duplicata_exata"] == 1
    assert resultado["resumo"]["depois"]["linhas_com_flag"] == 1


def test_dataframe_vazio_nao_quebra():
    assert cleaning.coletar_issues(pd.DataFrame()).empty


def test_vitoria_fora_de_0_1(base):
    bruto = base.copy()
    bruto.loc[bruto.index[0], "WL"] = 2
    issues = cleaning.coletar_issues(tratar(bruto))
    assert "fora_dominio" in set(issues["regra"])


def test_base_real_sem_issues(tmp_path):
    resultado = cleaning.executar_tratamento(caminho_limpo=tmp_path / "clean.csv")
    assert len(resultado["tratado"]) == 2238
    assert resultado["issues"].empty
    assert resultado["resumo"]["antes"]["ausentes"] == 0
    assert resultado["resumo"]["antes"]["duplicatas_exatas"] == 0
    assert resultado["resumo"]["duplicatas_removidas"]["total"] == 0


def test_arquivo_original_nao_e_alterado(tmp_path):
    antes = hash_arquivo(config.RAW_CSV)
    cleaning.executar_tratamento(caminho_limpo=tmp_path / "clean.csv")
    assert hash_arquivo(config.RAW_CSV) == antes


def test_tratamento_idempotente(tmp_path):
    p1, p2 = tmp_path / "a.csv", tmp_path / "b.csv"
    cleaning.executar_tratamento(caminho_limpo=p1)
    cleaning.executar_tratamento(caminho_limpo=p2)
    assert p1.read_bytes() == p2.read_bytes()


def test_limite_temporada_por_numero_de_linhas(base):
    """Mais de 82 linhas para um time viola a regra, mesmo sem olhar W/L."""
    gsw = base[base["TEAM_NAME"] == "Golden State Warriors"]
    extra = pd.concat([gsw] * 21, ignore_index=True)  # 84 linhas
    extra["Game_ID"] = range(1000, 1000 + len(extra))
    issues = cleaning.coletar_issues(tratar(pd.concat([base, extra], ignore_index=True)))
    detalhes = set(issues.loc[issues["regra"] == "limite_temporada", "detalhe"])
    assert any("jogos na base" in d for d in detalhes)


def test_zero_nao_e_sinalizado(base):
    """Zero é valor legítimo (ex.: jogo sem tocos/roubos) e não gera issue."""
    bruto = base.copy()
    bruto.loc[bruto.index[0], ["BLK", "STL"]] = 0
    assert cleaning.coletar_issues(tratar(bruto)).empty


def test_base_modelagem_gravada_sem_colunas_excluidas(base, tmp_path):
    bruto = tmp_path / "raw.csv"
    base.to_csv(bruto, index=False)
    modelagem = tmp_path / "modelo.csv"
    resultado = cleaning.executar_tratamento(
        caminho_bruto=bruto, caminho_limpo=tmp_path / "clean.csv", caminho_modelagem=modelagem
    )
    gravada = pd.read_csv(modelagem)
    assert len(gravada) == len(base)
    assert not set(config.COLUNAS_EXCLUIDAS_MODELAGEM) & set(gravada.columns)
    assert {"pontos", "vitoria", "em_casa"}.issubset(gravada.columns)
    # a base limpa continua completa, para auditoria
    assert set(config.COLUNAS_EXCLUIDAS_MODELAGEM).issubset(pd.read_csv(tmp_path / "clean.csv").columns)
    resumo = resultado["resumo"]["modelagem"]
    assert resumo["colunas"] == gravada.shape[1]
    assert resumo["colunas_mantidas"] == list(gravada.columns)


def test_base_modelagem_padrao_fica_ao_lado_da_limpa(base, tmp_path):
    bruto = tmp_path / "raw.csv"
    base.to_csv(bruto, index=False)
    resultado = cleaning.executar_tratamento(caminho_bruto=bruto, caminho_limpo=tmp_path / "clean.csv")
    assert Path(resultado["caminho_modelagem"]) == tmp_path / config.MODEL_CSV.name
    assert (tmp_path / config.MODEL_CSV.name).exists()


def test_calcular_nao_grava_modelagem(base, tmp_path):
    bruto = tmp_path / "raw.csv"
    base.to_csv(bruto, index=False)
    cleaning.calcular_tratamento(caminho_bruto=bruto, caminho_limpo=tmp_path / "clean.csv")
    assert not (tmp_path / config.MODEL_CSV.name).exists()
