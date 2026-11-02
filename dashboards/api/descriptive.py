"""Rotas /api/descriptive: resumo descritivo e lista de outliers IQR."""
from __future__ import annotations

from functools import lru_cache

import pandas as pd
from flask import Blueprint, jsonify, request

import config
from dashboards.analysis import descriptive
from dashboards.api.quality import resultado_atual

bp = Blueprint("descriptive", __name__)


def _base() -> pd.DataFrame:
    return resultado_atual()["tratado"]


@lru_cache(maxsize=2)
def _analise(chave: int) -> dict:
    return descriptive.analisar(_base())


def limpar_cache() -> None:
    _analise.cache_clear()


def _resultado() -> dict:
    return _analise(id(resultado_atual()))


def _serializar(df: pd.DataFrame) -> list[dict]:
    return df.where(pd.notna(df), None).to_dict(orient="records")


def _filtrar(df: pd.DataFrame, time: str | None, variavel: str | None) -> pd.DataFrame:
    saida = df
    if time:
        saida = saida[saida["time"] == time]
    if variavel and "variavel" in saida.columns:
        saida = saida[saida["variavel"] == variavel]
    return saida


def _validar_filtros(time: str | None, variavel: str | None):
    if time and time not in config.TIMES_GRUPO:
        return jsonify({
            "erro": "Time fora do recorte do grupo.",
            "team": time,
            "times_validos": list(config.TIMES_GRUPO),
        }), 400
    if variavel and variavel not in config.VARIAVEIS_ANALISE:
        return jsonify({
            "erro": "Variável inexistente.",
            "var": variavel,
            "variaveis_validas": list(config.VARIAVEIS_ANALISE),
        }), 400
    return None


@bp.get("/summary")
def summary():
    time = request.args.get("team")
    variavel = request.args.get("var")
    erro = _validar_filtros(time, variavel)
    if erro:
        return erro

    r = _resultado()
    zscore = r["zscore_liga"].reset_index(names="time")
    if time:
        zscore = zscore[zscore["time"] == time]

    return jsonify({
        "times": list(config.TIMES_GRUPO),
        "variaveis": list(config.VARIAVEIS_ANALISE),
        "rotulos": r["rotulos"],
        "parametros": r["parametros"],
        "filtros": {"team": time, "var": variavel},
        "medidas": _serializar(_filtrar(r["medidas"], time, variavel)),
        "assimetria": _serializar(_filtrar(r["assimetria"], time, variavel)),
        "cv": _serializar(_filtrar(r["cv"], time, variavel)),
        "iqr": _serializar(_filtrar(r["iqr"], time, variavel)),
        "quadro_assimetria": r["quadro_assimetria"].where(
            pd.notna(r["quadro_assimetria"]), None
        ).to_dict(orient="index"),
        "quadro_cv": r["quadro_cv"].where(pd.notna(r["quadro_cv"]), None).to_dict(
            orient="index"
        ),
        "quadro_iqr": r["quadro_iqr"].where(pd.notna(r["quadro_iqr"]), None).to_dict(
            orient="index"
        ),
        "zscore_liga": _serializar(zscore),
    })


@bp.get("/outliers")
def outliers_iqr():
    time = request.args.get("team")
    variavel = request.args.get("var")
    erro = _validar_filtros(time, variavel)
    if erro:
        return erro

    tabela = _filtrar(_resultado()["lista_outliers"], time, variavel)
    return jsonify({
        "total": len(tabela),
        "filtros": {"team": time, "var": variavel},
        "registros": _serializar(tabela),
        "nota": (
            "Outliers da estatística descritiva pela regra 1,5×IQR. "
            "Não são removidos; a detecção multi-método está em /api/outliers."
        ),
    })
