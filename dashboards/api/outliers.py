"""Rotas /api/outliers: resumo por coluna × método e registros marcados."""
from __future__ import annotations

from functools import lru_cache

from flask import Blueprint, jsonify, request

import config
from dashboards.analysis import outliers
from dashboards.api.quality import resultado_atual

bp = Blueprint("outliers", __name__)

MODOS = ("coluna", "multivariado")


def _base():
    return resultado_atual()["tratado"]


@lru_cache(maxsize=2)
def _analise(chave: int) -> dict:
    return outliers.analisar(_base())


def limpar_cache() -> None:
    _analise.cache_clear()


def _resultado() -> dict:
    return _analise(id(resultado_atual()))


@bp.get("/summary")
def summary():
    r = _resultado()
    return jsonify({
        "times": list(config.TIMES_GRUPO),
        "variaveis": list(config.VARIAVEIS_ANALISE),
        "metodos": {"univariados": list(outliers.UNIVARIADOS),
                    "multivariados": list(outliers.MULTIVARIADOS)},
        "por_coluna": r["por_coluna"].to_dict(orient="records"),
        "multivariado": r["multivariado"].to_dict(orient="records"),
        "univariado_liga": r["univariado_liga"].to_dict(orient="records"),
        "normalidade": r["normalidade"].to_dict(orient="records"),
        "sensibilidade": r["sensibilidade"].to_dict(orient="records"),
        "dbscan": r["dbscan"],
        "parametros": r["parametros"],
        "inconsistencias_total": len(resultado_atual()["issues"]),
        "nota": ("Contagens em 'por_coluna' são por coluna; em 'multivariado' são por "
                 "jogo. Inconsistências (erros) vêm de /api/quality; outliers são "
                 "valores extremos plausíveis e não são removidos."),
    })


@bp.get("")
def marcados():
    metodo = request.args.get("method")
    time = request.args.get("team")
    modo = request.args.get("modo", "coluna")

    if modo not in MODOS:
        return jsonify({"erro": "Modo inexistente.", "modos_validos": list(MODOS)}), 400
    validos = outliers.MULTIVARIADOS if modo == "multivariado" else tuple(outliers.METODOS)
    if metodo not in validos:
        return jsonify({"erro": "Método inexistente para o modo.", "method": metodo,
                        "metodos_validos": list(validos)}), 400
    if time and time not in config.TIMES_GRUPO:
        return jsonify({"erro": "Time fora do recorte do grupo.", "team": time,
                        "times_validos": list(config.TIMES_GRUPO)}), 400

    times = (time,) if time else config.TIMES_GRUPO
    base = _base()
    marcar = outliers.marcar_por_coluna if modo == "coluna" else outliers.marcar_multivariado
    tabela = marcar(base, metodo, times)

    contexto = base.loc[tabela["indice"], ["id_jogo", "data_jogo", "adversario", *config.VARIAVEIS_ANALISE]]
    contexto = contexto.assign(data_jogo=contexto["data_jogo"].dt.strftime("%Y-%m-%d"),
                               adversario=contexto["adversario"].astype(str))
    registros = [
        {**{k: v for k, v in linha.items() if k != "indice"}, **ctx}
        for linha, ctx in zip(tabela.to_dict(orient="records"), contexto.to_dict(orient="records"))
    ]
    return jsonify({"total": len(registros),
                    "filtros": {"method": metodo, "team": time, "modo": modo},
                    "registros": registros})
