from functools import lru_cache

from flask import Blueprint, jsonify

import config
from dashboards.analysis.missing import analisar
from dashboards.prep.loader import carregar_bruto

bp = Blueprint("missing", __name__)


@lru_cache(maxsize=2)
def _calcular(caminho: str, mtime_ns: int, tamanho: int) -> dict:
    return analisar(carregar_bruto(caminho))


def limpar_cache() -> None:
    _calcular.cache_clear()


def _resultado() -> dict:
    assinatura = config.RAW_CSV.stat()
    return _calcular(str(config.RAW_CSV), assinatura.st_mtime_ns, assinatura.st_size)


@bp.get("/summary")
def summary():
    r = _resultado()
    return jsonify({
        "base": r["base"],
        "total_ausentes": int(r["por_coluna"]["ausentes"].sum()),
        "por_coluna": r["por_coluna"].to_dict(orient="records"),
        "por_time": r["por_time"].to_dict(orient="records"),
        "padroes": r["padroes"].to_dict(orient="records"),
    })


@bp.get("/tests")
def tests():
    r = _resultado()
    return jsonify({
        "alpha": config.ALPHA_TESTES,
        "hipotese_nula": "os dados são MCAR",
        "base": r["base"],
        "variaveis_testadas": r["variaveis_testadas"],
        "testes": r["testes"],
        "conclusao": r["conclusao"],
    })
