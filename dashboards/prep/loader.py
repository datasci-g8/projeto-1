"""Leitura, validação, tipagem e renomeação da base bruta da NBA.

Responsabilidade única: transformar o CSV bruto em um DataFrame com contrato
conhecido (nomes em pt-BR, data convertida, colunas derivadas), sem decidir
nada sobre qualidade/limpeza — isso fica em cleaning.py.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd

import config
from config import (
    COLUNAS_ESPERADAS,
    COLUNAS_EXCLUIDAS_MODELAGEM,
    COLUNAS_NUMERICAS,
    RENOMEAR,
)


class ErroBaseDados(ValueError):
    """Erro de contrato da base (coluna faltando, tipo inválido etc.)."""


# ---------------------------------------------------------------------------
# Leitura e validação
# ---------------------------------------------------------------------------
def hash_arquivo(caminho: Path | str) -> str:
    """SHA-256 de um arquivo — usado para provar que o bruto não foi alterado."""
    caminho = Path(caminho)
    digest = hashlib.sha256()
    with caminho.open("rb") as f:
        for bloco in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(bloco)
    return digest.hexdigest()


def validar_colunas(df: pd.DataFrame) -> None:
    """Garante que a base tem exatamente as 28 colunas do contrato."""
    faltando = [c for c in COLUNAS_ESPERADAS if c not in df.columns]
    extras = [c for c in df.columns if c not in COLUNAS_ESPERADAS]
    if faltando:
        raise ErroBaseDados(f"Colunas obrigatórias ausentes: {faltando}")
    if extras:
        raise ErroBaseDados(f"Colunas inesperadas: {extras}")
    if len(df) == 0:
        raise ErroBaseDados("A base está vazia.")


def validar_tipos(df: pd.DataFrame) -> None:
    """Valida (sem silenciar) os tipos das colunas do contrato bruto."""
    for coluna in ("TEAM_NAME", "MATCHUP"):
        if not (pd.api.types.is_string_dtype(df[coluna]) or pd.api.types.is_object_dtype(df[coluna])):
            raise ErroBaseDados(f"'{coluna}' deveria ser texto.")
    try:
        pd.to_datetime(df["GAME_DATE"], format="%Y-%m-%d", errors="raise")
    except (ValueError, TypeError) as exc:
        raise ErroBaseDados(f"'GAME_DATE' tem data inválida: {exc}") from exc
    for coluna in [c for c in COLUNAS_ESPERADAS if c not in ("TEAM_NAME", "MATCHUP", "GAME_DATE")]:
        if not pd.api.types.is_numeric_dtype(df[coluna]):
            raise ErroBaseDados(f"'{coluna}' deveria ser numérica.")


def ler_bruto(caminho: Path | str | None = None) -> pd.DataFrame:
    """Lê o CSV original sem alterar o arquivo e valida o contrato."""
    caminho = Path(caminho) if caminho is not None else config.RAW_CSV
    if not caminho.exists():
        raise FileNotFoundError(f"Base bruta não encontrada: {caminho}")
    df = pd.read_csv(caminho)
    validar_colunas(df)
    validar_tipos(df)
    return df


def carregar_bruto(caminho: Path | str | None = None) -> pd.DataFrame:
    """Alias público usado pelos demais módulos."""
    return ler_bruto(caminho)


# ---------------------------------------------------------------------------
# Tratamento
# ---------------------------------------------------------------------------
def tratar(df_bruto: pd.DataFrame) -> pd.DataFrame:
    """Renomeia, tipa, converte a data e cria as colunas derivadas.

    Não remove linhas e não corrige valores: isso é responsabilidade de
    cleaning.py, que registra cada decisão no relatório.
    """
    validar_colunas(df_bruto)
    validar_tipos(df_bruto)
    df = df_bruto.copy()

    df = df.rename(columns=RENOMEAR)

    # Data: string ISO -> datetime64; derivadas temporais.
    df["data_jogo"] = pd.to_datetime(df["data_jogo"], format="%Y-%m-%d", errors="raise")
    df["mes"] = df["data_jogo"].dt.month
    df["dia_semana"] = df["data_jogo"].dt.day_of_week  # 0 = segunda-feira

    # Contrato numérico: falha alto em vez de virar NaN silencioso.
    for coluna in COLUNAS_NUMERICAS:
        df[coluna] = pd.to_numeric(df[coluna], errors="raise")

    # Binárias e derivadas de MATCHUP/MIN.
    df["em_casa"] = df["confronto"].str.contains(" vs. ", regex=False).fillna(False).astype(int)
    df["prorrogacao"] = (df["minutos"] > config.MINUTOS_REGULAMENTARES).astype(int)
    df["adversario"] = df["confronto"].str.split(" ").str[-1]
    df["sigla"] = df["confronto"].str.split(" ").str[0]

    # MATCHUP era texto composto: depois de derivado, não é mais necessário.
    df = df.drop(columns=["confronto"])

    df["time"] = df["time"].astype("category")
    df["adversario"] = df["adversario"].astype("category")
    df["sigla"] = df["sigla"].astype("category")

    ordem = [
        "id_time", "id_jogo", "data_jogo", "time", "vitoria", "vitorias_acum",
        "derrotas_acum", "pct_vitorias_acum", "minutos",
        "arremessos_conv", "arremessos_tent", "pct_arremessos",
        "tres_pontos_conv", "tres_pontos_tent", "pct_tres_pontos",
        "lances_livres_conv", "lances_livres_tent", "pct_lances_livres",
        "rebotes_ofensivos", "rebotes_defensivos", "rebotes",
        "assistencias", "roubos", "tocos", "erros", "faltas", "pontos",
        "mes", "dia_semana", "em_casa", "prorrogacao", "adversario", "sigla",
    ]
    df = df[ordem].sort_values(["time", "data_jogo", "id_jogo"]).reset_index(drop=True)
    return df


def carregar_tratado(caminho: Path | str | None = None) -> pd.DataFrame:
    """Lê o bruto e devolve a base tratada (sem limpeza de registros)."""
    return tratar(ler_bruto(caminho))


def colunas_modelagem(df: pd.DataFrame) -> pd.DataFrame:
    """Remove identificadores e colunas com vazamento de informação."""
    return df.drop(columns=[c for c in COLUNAS_EXCLUIDAS_MODELAGEM if c in df.columns])


# ---------------------------------------------------------------------------
# Dicionário de dados
# ---------------------------------------------------------------------------
DICIONARIO = {
    "Team_ID": ("id_time", "identificador", "ID numérico do time na API da NBA."),
    "Game_ID": ("id_jogo", "identificador", "ID numérico do jogo; aparece em duas linhas (um time cada)."),
    "GAME_DATE": ("data_jogo", "data", "Data do jogo (AAAA-MM-DD), convertida para datetime."),
    "MATCHUP": ("confronto", "texto", "Confronto no formato 'SIGLA vs. ADV' (casa) ou 'SIGLA @ ADV' (fora)."),
    "WL": ("vitoria", "binária", "1 = vitória do time naquele jogo; 0 = derrota."),
    "W": ("vitorias_acum", "numérica", "Vitórias acumuladas do time na temporada até o jogo (inclui este jogo)."),
    "L": ("derrotas_acum", "numérica", "Derrotas acumuladas do time na temporada até o jogo."),
    "W_PCT": ("pct_vitorias_acum", "numérica", "Percentual de vitórias acumulado: W/(W+L), em fração."),
    "MIN": ("minutos", "numérica", "Duração do jogo em minutos: 240 regulamentar; +25 por prorrogação."),
    "FGM": ("arremessos_conv", "numérica", "Arremessos de quadra convertidos."),
    "FGA": ("arremessos_tent", "numérica", "Arremessos de quadra tentados."),
    "FG_PCT": ("pct_arremessos", "numérica", "Aproveitamento de quadra: FGM/FGA."),
    "FG3M": ("tres_pontos_conv", "numérica", "Arremessos de 3 pontos convertidos."),
    "FG3A": ("tres_pontos_tent", "numérica", "Arremessos de 3 pontos tentados."),
    "FG3_PCT": ("pct_tres_pontos", "numérica", "Aproveitamento de 3 pontos: FG3M/FG3A."),
    "FTM": ("lances_livres_conv", "numérica", "Lances livres convertidos."),
    "FTA": ("lances_livres_tent", "numérica", "Lances livres tentados."),
    "FT_PCT": ("pct_lances_livres", "numérica", "Aproveitamento de lances livres: FTM/FTA."),
    "OREB": ("rebotes_ofensivos", "numérica", "Rebotes ofensivos."),
    "DREB": ("rebotes_defensivos", "numérica", "Rebotes defensivos."),
    "REB": ("rebotes", "numérica", "Rebotes totais: OREB + DREB."),
    "AST": ("assistencias", "numérica", "Assistências."),
    "STL": ("roubos", "numérica", "Roubos de bola (steals)."),
    "BLK": ("tocos", "numérica", "Tocos/bloqueios (blocks)."),
    "TOV": ("erros", "numérica", "Perdas de bola (turnovers)."),
    "PF": ("faltas", "numérica", "Faltas pessoais cometidas."),
    "PTS": ("pontos", "numérica", "Pontos marcados: 2*FGM + FG3M + FTM."),
    "TEAM_NAME": ("time", "categórica", "Nome oficial do time."),
}

DERIVADAS_DICIONARIO = [
    ("—", "mes", "numérica", "Mês do jogo (1–12), derivado de data_jogo."),
    ("—", "dia_semana", "numérica", "Dia da semana (0 = segunda), derivado de data_jogo."),
    ("—", "em_casa", "binária", "1 = jogo em casa ('vs.' no MATCHUP); 0 = fora ('@')."),
    ("—", "prorrogacao", "binária", "1 = jogo com prorrogação (minutos > 240)."),
    ("—", "adversario", "categórica", "Sigla do adversário, derivada do MATCHUP."),
    ("—", "sigla", "categórica", "Sigla do próprio time, derivada do MATCHUP."),
]


def tabela_dicionario() -> pd.DataFrame:
    """Dicionário de dados em formato tabular para a interface e os docs."""
    linhas = []
    for original, (novo, tipo, descricao) in DICIONARIO.items():
        if novo == "confronto":
            situacao = "substituída por em_casa, adversario e sigla"
        elif novo in COLUNAS_EXCLUIDAS_MODELAGEM:
            situacao = "mantida na análise; excluída da modelagem"
        else:
            situacao = "mantida"
        linhas.append((original, novo, tipo, descricao, situacao))
    for original, novo, tipo, descricao in DERIVADAS_DICIONARIO:
        linhas.append((original, novo, tipo, descricao, "derivada"))
    return pd.DataFrame(
        linhas,
        columns=["coluna_original", "coluna_nova", "tipo", "descricao", "situacao"],
    )


if __name__ == "__main__":
    base = carregar_tratado()
    print(f"{config.RAW_CSV.name}: {base.shape[0]} linhas x {base.shape[1]} colunas")
    print(base.dtypes.to_string())
    print()
    print(tabela_dicionario().to_string(index=False))
