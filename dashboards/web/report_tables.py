"""HTML de tabelas do relatório web (cabeçalhos em português)."""
from __future__ import annotations

import pandas as pd

from dashboards.analysis import descriptive

ROTULOS_METODOS = {
    "zscore": "Z-score",
    "iqr": "IQR (1,5×)",
    "grubbs": "Grubbs",
    "ecod": "ECOD",
    "knn": "K-NN",
    "lof": "LOF",
    "dbscan": "DBSCAN",
    "consenso_2+": "Consenso (≥ 2)",
}

ROTULOS_COLUNAS = {
    "time": "Time",
    "variavel": "Variável",
    "coluna": "Variável",
    "coluna_original": "Coluna (NBA)",
    "coluna_nova": "Nome no projeto",
    "tipo": "Tipo",
    "descricao": "Descrição",
    "situacao": "Situação",
    "jogos": "Jogos",
    "ausentes": "Ausentes",
    "percentual": "% ausentes",
    "n": "n",
    "media": "Média",
    "mediana": "Mediana",
    "moda": "Moda",
    "minimo": "Mínimo",
    "maximo": "Máximo",
    "amplitude": "Amplitude",
    "desvio_padrao": "Desvio padrão",
    "variancia": "Variância",
    "q1": "Q1",
    "q3": "Q3",
    "iqr": "IQR",
    "limite_inf": "Limite inferior",
    "limite_sup": "Limite superior",
    "n_outliers": "Outliers (n)",
    "g1_fisher_pearson": "G1 (Fisher–Pearson)",
    "pearson_2": "Pearson (2)",
    "bowley": "Bowley",
    "direcao": "Direção",
    "intensidade": "Intensidade",
    "representante": "Representante",
    "cv_pct": "CV (%)",
    "cv_robusto_pct": "CV robusto (%)",
    "classificacao": "Classificação",
    "media_pequena": "Média pequena",
    "valido": "Válido para CV",
    "razao_amp_iqr": "Amplitude / IQR",
    "razao_dp_iqr": "DP / IQR",
    "data_jogo": "Data do jogo",
    "adversario": "Adversário",
    "em_casa": "Mando",
    "valor": "Valor",
    "lado": "Lado",
    "limite": "Limite (1,5×IQR)",
    "id_jogo": "ID do jogo",
    "id_time": "ID do time",
    "regra": "Regra",
    "detalhe": "Detalhe",
    "decisao": "Decisão",
    "indice": "Índice (linha)",
    "n_metodos": "Métodos (n)",
    "vitoria": "Resultado",
    "shapiro_w": "Shapiro–Wilk (W)",
    "p_valor": "p-valor",
    "normal": "Normal (α=0,05)",
}

COLUNAS_AMOSTRA = (
    "time",
    "data_jogo",
    "adversario",
    "em_casa",
    "vitoria",
    "pontos",
    "rebotes",
    "assistencias",
)

_ALIASES = {**ROTULOS_COLUNAS, **descriptive.ROTULOS, **ROTULOS_METODOS}


def tab(
    df: pd.DataFrame,
    index: bool = False,
    dec: int = 2,
    *,
    classes: str = "tabela",
) -> str:
    return df.to_html(
        classes=classes,
        index=index,
        float_format=lambda x: f"{x:.{dec}f}",
        border=0,
        na_rep="n/d",
    )


def _rotular_colunas(df: pd.DataFrame) -> pd.DataFrame:
    return df.rename(columns={c: _ALIASES[c] for c in df.columns if c in _ALIASES})


def preparar(
    df: pd.DataFrame,
    *,
    omit_var: bool = False,
    omit_cols: tuple[str, ...] = (),
) -> pd.DataFrame:
    t = df.copy()
    for col in omit_cols:
        if col in t.columns:
            t = t.drop(columns=[col])
    if omit_var and "variavel" in t.columns:
        t = t.drop(columns=["variavel"])
    for col in ("variavel", "coluna"):
        if col in t.columns:
            t[col] = t[col].map(descriptive.ROTULOS).fillna(t[col])
    for col in ("valido", "media_pequena", "normal"):
        if col in t.columns:
            t[col] = t[col].map({True: "Sim", False: "Não"}).fillna(t[col])
    return _rotular_colunas(t)


def tab_relatorio(
    df: pd.DataFrame,
    *,
    dec: int = 2,
    index: bool = False,
    classes: str = "tabela",
    omit_var: bool = False,
    omit_cols: tuple[str, ...] = (),
) -> str:
    return tab(
        preparar(df, omit_var=omit_var, omit_cols=omit_cols),
        dec=dec,
        index=index,
        classes=classes,
    )


def tab_lista_outliers(df: pd.DataFrame, *, omit_var: bool = False) -> str:
    return tab_relatorio(df, omit_var=omit_var)


def tab_quadro(df: pd.DataFrame, *, dec: int = 2) -> str:
    t = df.copy()
    t.index.name = "Variável"
    return tab(t, index=True, dec=dec)


def tab_amostra(df: pd.DataFrame) -> str:
    cols = [c for c in COLUNAS_AMOSTRA if c in df.columns]
    t = df[cols].copy()
    if "data_jogo" in t.columns:
        t["data_jogo"] = pd.to_datetime(t["data_jogo"]).dt.strftime("%Y-%m-%d")
    if "em_casa" in t.columns:
        t["em_casa"] = t["em_casa"].map({1: "casa", 0: "fora", True: "casa", False: "fora"})
    if "vitoria" in t.columns:
        t["vitoria"] = t["vitoria"].map({1: "V", 0: "D", True: "V", False: "D"})
    return tab_relatorio(t, dec=2)
