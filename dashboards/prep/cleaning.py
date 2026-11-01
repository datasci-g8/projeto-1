"""Limpeza e homologação da base.

Separa três coisas que costumam ser misturadas:

* detectar — encontra problemas e registra cada ocorrência com a regra,
  a linha afetada e a decisão adotada;
* remover_duplicatas — única transformação destrutiva, aplicada antes das
  demais verificações;
* executar_tratamento — orquestra leitura, tratamento, limpeza, relatório
  e gravação em data/clean.

Nenhuma inconsistência é corrigida em silêncio: todas viram uma linha em
issues e um flag no relatório. A base atual não tem nenhum problema,
mas o código é genérico e é testado com DataFrames sintéticos.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

import config
from dashboards.prep.loader import carregar_bruto, tratar


# ---------------------------------------------------------------------------
# Metadados das regras
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Regra:
    chave: str
    descricao: str
    decisao: str  # "remover", "corrigir" ou "sinalizar"


REGRAS: dict[str, Regra] = {
    "valor_ausente": Regra(
        "valor_ausente",
        "Célula vazia em uma coluna do contrato.",
        "sinalizar",
    ),
    "valor_negativo": Regra(
        "valor_negativo",
        "Contagem ou percentual negativo (fora do domínio físico).",
        "sinalizar",
    ),
    "fora_dominio": Regra(
        "fora_dominio",
        "Percentual fora de [0, 1] ou binária diferente de 0/1.",
        "sinalizar",
    ),
    "duplicata_exata": Regra(
        "duplicata_exata",
        "Linha idêntica a outra em todas as colunas.",
        "remover",
    ),
    "duplicata_time_jogo": Regra(
        "duplicata_time_jogo",
        "Mesmo time no mesmo jogo aparece mais de uma vez.",
        "remover",
    ),
    "duplicata_time_data": Regra(
        "duplicata_time_data",
        "Mesmo time com dois jogos na mesma data.",
        "sinalizar",
    ),
    "duplicata_confronto_data": Regra(
        "duplicata_confronto_data",
        "Mesmo par de times na mesma data com Game_IDs diferentes.",
        "sinalizar",
    ),
    "time_desconhecido": Regra(
        "time_desconhecido",
        "TEAM_NAME fora da lista oficial dos 30 times.",
        "sinalizar",
    ),
    "time_id_divergente": Regra(
        "time_id_divergente",
        "Um nome de time associado a mais de um Team_ID.",
        "sinalizar",
    ),
    "abreviacao_time": Regra(
        "abreviacao_time",
        "Sigla no MATCHUP diferente da sigla oficial do time.",
        "sinalizar",
    ),
    "adversario_divergente": Regra(
        "adversario_divergente",
        "Sigla do adversário no MATCHUP não coincide com a outra linha do jogo.",
        "sinalizar",
    ),
    "local_inconsistente": Regra(
        "local_inconsistente",
        "Jogo sem exatamente um mandante ('vs.') e um visitante ('@').",
        "sinalizar",
    ),
    "jogo_incompleto": Regra(
        "jogo_incompleto",
        "Game_ID com quantidade de linhas diferente de 2 (uma por time).",
        "sinalizar",
    ),
    "jogo_sem_vencedor": Regra(
        "jogo_sem_vencedor",
        "Soma de WL diferente de 1: nenhum ou mais de um vencedor.",
        "sinalizar",
    ),
    "vencedor_pontos": Regra(
        "vencedor_pontos",
        "Time marcado como vencedor não tem a maior pontuação do jogo.",
        "sinalizar",
    ),
    "data_divergente": Regra(
        "data_divergente",
        "As duas linhas do mesmo Game_ID têm datas diferentes.",
        "sinalizar",
    ),
    "minutos_divergente": Regra(
        "minutos_divergente",
        "As duas linhas do mesmo Game_ID têm durações diferentes.",
        "sinalizar",
    ),
    "pontos_formula": Regra(
        "pontos_formula",
        "PTS diferente de 2*FGM + FG3M + FTM.",
        "sinalizar",
    ),
    "rebotes_formula": Regra(
        "rebotes_formula",
        "REB diferente de OREB + DREB.",
        "sinalizar",
    ),
    "pct_arremessos": Regra(
        "pct_arremessos",
        "FG_PCT diferente de FGM/FGA (tolerância de 0,001).",
        "sinalizar",
    ),
    "pct_tres_pontos": Regra(
        "pct_tres_pontos",
        "FG3_PCT diferente de FG3M/FG3A (tolerância de 0,001).",
        "sinalizar",
    ),
    "pct_lances_livres": Regra(
        "pct_lances_livres",
        "FT_PCT diferente de FTM/FTA (tolerância de 0,001).",
        "sinalizar",
    ),
    "convertidos_maior_tentados": Regra(
        "convertidos_maior_tentados",
        "Arremessos convertidos maiores que os tentados.",
        "sinalizar",
    ),
    "minutos_invalidos": Regra(
        "minutos_invalidos",
        "MIN fora do conjunto {240, 265, 290, 315, 340}.",
        "sinalizar",
    ),
    "pct_vitorias_acumulado": Regra(
        "pct_vitorias_acumulado",
        "W_PCT diferente de W/(W+L).",
        "sinalizar",
    ),
    "acumulado_ordem": Regra(
        "acumulado_ordem",
        "W+L não corresponde ao número do jogo do time na temporada.",
        "sinalizar",
    ),
    "acumulado_incremento": Regra(
        "acumulado_incremento",
        "W/L não crescem exatamente conforme os resultados do time.",
        "sinalizar",
    ),
}

COLUNAS_ISSUES = [
    "id_jogo",
    "id_time",
    "time",
    "data_jogo",
    "regra",
    "detalhe",
    "decisao",
]


def _vazio() -> pd.DataFrame:
    return pd.DataFrame(columns=COLUNAS_ISSUES)


def _int(valor):
    return int(valor) if pd.notna(valor) else None


def _data(valor):
    return valor.date().isoformat() if pd.notna(valor) else None


def _issue(df: pd.DataFrame, indice, regra: str, detalhe: str) -> dict:
    linha = df.loc[indice]
    return {
        "id_jogo": _int(linha["id_jogo"]),
        "id_time": _int(linha["id_time"]),
        "time": str(linha["time"]),
        "data_jogo": _data(linha["data_jogo"]),
        "regra": regra,
        "detalhe": detalhe,
        "decisao": REGRAS[regra].decisao,
    }


def _add(issues: list[dict], df: pd.DataFrame, mascara, regra: str, detalhe: str) -> None:
    mascara = pd.Series(mascara, index=df.index).fillna(False).astype(bool)
    for indice in df.index[mascara]:
        issues.append(_issue(df, indice, regra, detalhe))


def _add_grupo(issues: list[dict], df: pd.DataFrame, id_jogo, regra: str, detalhe: str) -> None:
    for indice in df.index[df["id_jogo"] == id_jogo]:
        issues.append(_issue(df, indice, regra, detalhe))


def _ordenar_issues(issues: pd.DataFrame) -> pd.DataFrame:
    """Padroniza ordem e remove repetições da lista de issues."""
    if issues.empty:
        return _vazio()
    return issues.drop_duplicates().sort_values(["regra", "data_jogo", "id_jogo"]).reset_index(drop=True)


def _issues_duplicatas(duplicatas: dict) -> pd.DataFrame:
    """Converte as linhas removidas em issues, para que /issues não perca o rastro."""
    removidas = duplicatas.get("removidas")
    if removidas is None or len(removidas) == 0:
        return _vazio()

    registros = []
    for _, linha in removidas.iterrows():
        regra = str(linha["_regra_duplicata"])
        registros.append(
            {
                "id_jogo": _int(linha["id_jogo"]),
                "id_time": _int(linha["id_time"]),
                "time": str(linha["time"]),
                "data_jogo": _data(linha["data_jogo"]),
                "regra": regra,
                "detalhe": "linha removida por duplicidade",
                "decisao": REGRAS[regra].decisao,
            }
        )
    return pd.DataFrame(registros, columns=COLUNAS_ISSUES)


# ---------------------------------------------------------------------------
# Regras que dependem de percentuais
# ---------------------------------------------------------------------------
def _mascara_percentual(df: pd.DataFrame, pct: str, feito: str, tentado: str) -> pd.Series:
    """Percentual deveria ser feito/tentado; tolera arredondamento de 3 casas."""
    denominador = df[tentado].replace(0, np.nan)
    calculado = df[feito] / denominador
    divergente = df[pct].notna() & calculado.notna() & ((df[pct] - calculado).abs() > config.TOLERANCIA_PCT)
    sem_tentativa = (df[tentado].fillna(0) == 0) & df[pct].notna() & (df[pct] != 0)
    return divergente | sem_tentativa


# ---------------------------------------------------------------------------
# Detecção
# ---------------------------------------------------------------------------
def coletar_issues(df: pd.DataFrame) -> pd.DataFrame:
    """Retorna uma linha por (registro, regra) violada.

    Espera a base já tratada (nomes em pt-BR e colunas derivadas), mas não
    exige que ela esteja limpa: é justamente o que se quer medir.
    """
    if df.empty:
        return _vazio()

    df = df.reset_index(drop=True)
    issues: list[dict] = []

    # 1) Ausentes
    for coluna in df.columns:
        ausentes = df[coluna].isna()
        for indice in df.index[ausentes]:
            issues.append(_issue(df, indice, "valor_ausente", f"'{coluna}' ausente"))

    # 2) Negativos e domínio
    numericas = list(df.select_dtypes(include="number").columns)
    for coluna in numericas:
        mask = df[coluna] < 0
        if mask.any():
            _add(issues, df, mask, "valor_negativo", f"'{coluna}' negativo")

    for coluna in ("pct_arremessos", "pct_tres_pontos", "pct_lances_livres", "pct_vitorias_acum"):
        mask = df[coluna].notna() & ((df[coluna] < 0) | (df[coluna] > 1))
        if mask.any():
            _add(issues, df, mask, "fora_dominio", f"'{coluna}' fora de [0, 1]")

    mask_binaria = df["vitoria"].notna() & ~df["vitoria"].isin([0, 1])
    if mask_binaria.any():
        _add(issues, df, mask_binaria, "fora_dominio", "'vitoria' diferente de 0/1")

    # 3) Fórmulas aritméticas
    esperado = (
        config.PONTOS_CESTA * df["arremessos_conv"]
        + df["tres_pontos_conv"]
        + df["lances_livres_conv"]
    )
    mask = (df["pontos"] - esperado).abs() > config.TOLERANCIA_PONTOS
    if mask.any():
        _add(issues, df, mask, "pontos_formula", "PTS != 2*FGM + FG3M + FTM")

    mask = (df["rebotes"] - (df["rebotes_ofensivos"] + df["rebotes_defensivos"])).abs() > config.TOLERANCIA_PONTOS
    if mask.any():
        _add(issues, df, mask, "rebotes_formula", "REB != OREB + DREB")

    for pct, feito, tentado in (
        ("pct_arremessos", "arremessos_conv", "arremessos_tent"),
        ("pct_tres_pontos", "tres_pontos_conv", "tres_pontos_tent"),
        ("pct_lances_livres", "lances_livres_conv", "lances_livres_tent"),
    ):
        mask = _mascara_percentual(df, pct, feito, tentado)
        if mask.any():
            _add(issues, df, mask, pct, f"{pct} != {feito}/{tentado}")

    for feito, tentado in (
        ("arremessos_conv", "arremessos_tent"),
        ("tres_pontos_conv", "tres_pontos_tent"),
        ("lances_livres_conv", "lances_livres_tent"),
    ):
        mask = df[feito] > df[tentado]
        if mask.any():
            _add(issues, df, mask, "convertidos_maior_tentados", f"{feito} > {tentado}")

    mask = df["minutos"].notna() & ~df["minutos"].isin(config.MINUTOS_VALIDOS)
    if mask.any():
        _add(issues, df, mask, "minutos_invalidos", "MIN fora de {240, 265, 290, 315, 340}")

    # 4) Acumulados
    denominador = (df["vitorias_acum"] + df["derrotas_acum"]).replace(0, np.nan)
    calculado = df["vitorias_acum"] / denominador
    mask = df["pct_vitorias_acum"].notna() & calculado.notna() & (
        (df["pct_vitorias_acum"] - calculado).abs() > config.TOLERANCIA_PCT
    )
    if mask.any():
        _add(issues, df, mask, "pct_vitorias_acumulado", "W_PCT != W/(W+L)")

    ordenado = df.sort_values(["time", "data_jogo", "id_jogo"])
    ordem = ordenado.groupby("time", observed=True).cumcount() + 1
    mask_ordem = (ordenado["vitorias_acum"] + ordenado["derrotas_acum"]) != ordem
    mask = mask_ordem.reindex(df.index).fillna(False)
    if mask.any():
        _add(issues, df, mask, "acumulado_ordem", "W+L != número do jogo do time")

    mask_incremento = pd.Series(False, index=df.index)
    for _, grupo in ordenado.groupby("time", observed=True):
        vitorias = grupo["vitoria"].fillna(0).cumsum()
        derrotas = (1 - grupo["vitoria"].fillna(0)).cumsum()
        mask_incremento.loc[grupo.index] = (
            (grupo["vitorias_acum"] != vitorias) | (grupo["derrotas_acum"] != derrotas)
        )
    if mask_incremento.any():
        _add(issues, df, mask_incremento, "acumulado_incremento", "W/L não acompanham os resultados")

    # 5) Identidade dos times
    mask = ~df["time"].isin(config.TIME_ABREV)
    if mask.any():
        _add(issues, df, mask, "time_desconhecido", "TEAM_NAME fora da lista oficial")

    for time, grupo in df.groupby("time", observed=True):
        if grupo["id_time"].nunique(dropna=True) > 1:
            _add(
                issues,
                df,
                df["time"] == time,
                "time_id_divergente",
                f"'{time}' tem {grupo['id_time'].nunique(dropna=True)} Team_IDs",
            )

    esperado_sigla = df["time"].map(config.TIME_ABREV)
    mask = esperado_sigla.notna() & (df["sigla"].astype(str) != esperado_sigla.astype(str))
    if mask.any():
        _add(issues, df, mask, "abreviacao_time", "sigla do MATCHUP diferente da oficial")

    # 6) Regras por jogo (as duas linhas)
    for id_jogo, grupo in df.groupby("id_jogo", sort=False, dropna=False):
        if len(grupo) != 2:
            _add_grupo(issues, df, id_jogo, "jogo_incompleto", f"{len(grupo)} linha(s) para o Game_ID")
            continue

        if grupo["vitoria"].sum() != 1:
            _add_grupo(issues, df, id_jogo, "jogo_sem_vencedor", "soma de WL diferente de 1")

        if grupo["data_jogo"].nunique(dropna=False) > 1:
            _add_grupo(issues, df, id_jogo, "data_divergente", "datas diferentes no mesmo jogo")

        if grupo["minutos"].nunique(dropna=False) > 1:
            _add_grupo(issues, df, id_jogo, "minutos_divergente", "durações diferentes no mesmo jogo")

        if grupo["em_casa"].sum() != 1:
            _add_grupo(issues, df, id_jogo, "local_inconsistente", "não há exatamente um mandante")

        primeira, segunda = grupo.iloc[0], grupo.iloc[1]
        if str(primeira["adversario"]) != str(segunda["sigla"]) or str(segunda["adversario"]) != str(primeira["sigla"]):
            _add_grupo(issues, df, id_jogo, "adversario_divergente", "adversário não confere entre as linhas")

        vencedores = grupo[grupo["vitoria"] == 1]
        perdedores = grupo[grupo["vitoria"] == 0]
        if (
            len(vencedores) == 1
            and len(perdedores) == 1
            and vencedores.iloc[0]["pontos"] <= perdedores.iloc[0]["pontos"]
        ):
            _add_grupo(issues, df, id_jogo, "vencedor_pontos", "vencedor não tem a maior pontuação")

    # 7) Duplicatas que não são removidas automaticamente
    for (id_time, data), grupo in df.groupby(["id_time", "data_jogo"], dropna=False):
        if len(grupo) > 1:
            _add(
                issues,
                df,
                df.index.isin(grupo.index),
                "duplicata_time_data",
                f"time {id_time} tem {len(grupo)} jogos em {_data(data)}",
            )

    pares = {}
    for id_jogo, grupo in df.groupby("id_jogo", sort=False, dropna=False):
        ids = tuple(sorted(grupo["id_time"].dropna().unique()))
        data = grupo["data_jogo"].iloc[0] if len(grupo) else None
        pares[id_jogo] = (ids, data)
    contagem = Counter(pares.values())
    for id_jogo, chave in pares.items():
        if contagem[chave] > 1:
            _add_grupo(
                issues,
                df,
                id_jogo,
                "duplicata_confronto_data",
                "mesmo par de times e data com Game_IDs diferentes",
            )

    if not issues:
        return _vazio()

    return _ordenar_issues(pd.DataFrame(issues, columns=COLUNAS_ISSUES))


# ---------------------------------------------------------------------------
# Duplicatas (única transformação destrutiva)
# ---------------------------------------------------------------------------
def remover_duplicatas(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Remove linhas idênticas e pares (id_time, id_jogo) repetidos.

    Mantém a primeira ocorrência. Além das contagens, devolve as próprias
    linhas removidas (com a coluna interna _regra_duplicata) para que o
    relatório e /api/quality/issues não percam o rastro da remoção.

    Duplicatas de confronto/data não são removidas automaticamente: podem ser
    dois jogos distintos com o mesmo Game_ID errado, o que exige decisão humana.
    """
    exatas = df.duplicated(keep="first")
    removidas_exatas = df[exatas].copy()
    sem_exatas = df[~exatas]

    time_jogo = sem_exatas.duplicated(subset=["id_time", "id_jogo"], keep="first")
    removidas_time_jogo = sem_exatas[time_jogo].copy()
    limpo = sem_exatas[~time_jogo].copy().reset_index(drop=True)

    if not removidas_exatas.empty:
        removidas_exatas["_regra_duplicata"] = "duplicata_exata"
    if not removidas_time_jogo.empty:
        removidas_time_jogo["_regra_duplicata"] = "duplicata_time_jogo"

    if removidas_exatas.empty and removidas_time_jogo.empty:
        removidas = pd.DataFrame(columns=list(df.columns) + ["_regra_duplicata"])
    else:
        removidas = pd.concat([removidas_exatas, removidas_time_jogo], ignore_index=True)

    return limpo, {
        "exatas": len(removidas_exatas),
        "time_jogo": len(removidas_time_jogo),
        "total": len(removidas_exatas) + len(removidas_time_jogo),
        "removidas": removidas,
    }


# ---------------------------------------------------------------------------
# Relatório e persistência
# ---------------------------------------------------------------------------
def _contagem_por_regra(issues: pd.DataFrame) -> dict[str, int]:
    contagem = issues["regra"].value_counts().to_dict() if not issues.empty else {}
    return {chave: int(contagem.get(chave, 0)) for chave in REGRAS}


def _relativo(caminho: Path | str) -> str:
    """Caminho relativo à raiz do projeto, para não expor caminho absoluto na API."""
    caminho = Path(caminho)
    try:
        return str(caminho.resolve().relative_to(config.BASE_DIR))
    except ValueError:
        return str(caminho)


def resumo_qualidade(
    bruto: pd.DataFrame,
    tratado: pd.DataFrame,
    issues: pd.DataFrame,
    duplicatas: dict,
    caminho_limpo: Path | str,
    caminho_bruto: Path | str | None = None,
) -> dict:
    """Relatório antes/depois, pronto para JSON."""
    linhas_com_flag = 0
    if not issues.empty:
        linhas_com_flag = int(
            issues[["id_jogo", "id_time", "data_jogo"]].drop_duplicates().shape[0]
        )

    contagem = _contagem_por_regra(issues)
    return {
        "base": {
            "arquivo_bruto": _relativo(caminho_bruto or config.RAW_CSV),
            "arquivo_limpo": _relativo(caminho_limpo),
            "times": int(tratado["time"].nunique()),
            "jogos": int(tratado["id_jogo"].nunique()),
            "periodo": [
                tratado["data_jogo"].min().date().isoformat(),
                tratado["data_jogo"].max().date().isoformat(),
            ],
        },
        "antes": {
            "linhas": len(bruto),
            "colunas": int(bruto.shape[1]),
            "ausentes": int(bruto.isna().sum().sum()),
            "duplicatas_exatas": int(bruto.duplicated().sum()),
            "duplicatas_time_jogo": int(bruto.duplicated(["Team_ID", "Game_ID"]).sum()),
        },
        "depois": {
            "linhas": len(tratado),
            "colunas": int(tratado.shape[1]),
            "ausentes": int(tratado.isna().sum().sum()),
            "linhas_com_flag": linhas_com_flag,
            "issues": len(issues),
        },
        "duplicatas_removidas": {
            chave: int(duplicatas[chave]) for chave in ("exatas", "time_jogo", "total")
        },
        "por_regra": contagem,
        "regras": [
            {
                "regra": chave,
                "descricao": regra.descricao,
                "decisao": regra.decisao,
                "violacoes": contagem[chave],
            }
            for chave, regra in REGRAS.items()
        ],
        "colunas_excluidas_modelagem": dict(config.COLUNAS_EXCLUIDAS_MODELAGEM),
    }


def salvar_tratado(df: pd.DataFrame, caminho: Path | str | None = None) -> Path:
    """Grava a base tratada em data/clean (diretório criado se necessário)."""
    caminho = Path(caminho) if caminho is not None else config.CLEAN_CSV
    caminho.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(caminho, index=False, date_format="%Y-%m-%d")
    return caminho


def calcular_tratamento(
    caminho_bruto: Path | str | None = None,
    caminho_limpo: Path | str | None = None,
) -> dict:
    """Executa o pipeline e devolve o resultado, sem gravar arquivo.

    É a função usada pela API: leitura/diagnóstico não devem ter efeito
    colateral. A gravação fica em executar_tratamento.
    """
    bruto = carregar_bruto(caminho_bruto)
    tratado = tratar(bruto)
    tratado, duplicatas = remover_duplicatas(tratado)
    issues = _ordenar_issues(
        pd.concat([coletar_issues(tratado), _issues_duplicatas(duplicatas)], ignore_index=True)
    )
    caminho_limpo = Path(caminho_limpo) if caminho_limpo is not None else config.CLEAN_CSV
    resumo = resumo_qualidade(
        bruto, tratado, issues, duplicatas, caminho_limpo, caminho_bruto
    )
    return {
        "bruto": bruto,
        "tratado": tratado,
        "issues": issues,
        "duplicatas": duplicatas,
        "resumo": resumo,
        "caminho_limpo": str(caminho_limpo),
    }


def executar_tratamento(
    caminho_bruto: Path | str | None = None,
    caminho_limpo: Path | str | None = None,
) -> dict:
    """Pipeline completo, incluindo a gravação da base limpa.

    A leitura sempre parte do CSV bruto; por isso rodar duas vezes produz
    exatamente o mesmo arquivo limpo (idempotência do fluxo).
    """
    resultado = calcular_tratamento(caminho_bruto, caminho_limpo)
    caminho_limpo = salvar_tratado(resultado["tratado"], resultado["caminho_limpo"])
    resultado["caminho_limpo"] = str(caminho_limpo)
    resultado["resumo"]["base"]["arquivo_limpo"] = _relativo(caminho_limpo)
    return resultado


if __name__ == "__main__":
    resultado = executar_tratamento()
    print(f"Base limpa: {resultado['caminho_limpo']}")
    print(f"Linhas: {resultado['resumo']['antes']['linhas']} -> {resultado['resumo']['depois']['linhas']}")
    print(f"Issues: {resultado['resumo']['depois']['issues']}")
    print(resultado["issues"].to_string(index=False) if not resultado["issues"].empty else "Nenhuma inconsistência encontrada.")