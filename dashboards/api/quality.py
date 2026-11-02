"""Rotas JSON de qualidade dos dados.

Endpoints:
    GET /api/quality/summary  — relatório antes/depois e contagem por regra.
    GET /api/quality/issues   — registros afetados; filtros opcionais.
    GET /api/quality/regras   — catálogo de regras e decisões.

A leitura é cacheada pela assinatura do CSV (caminho, mtime e tamanho) e não
grava a base limpa: GET não deve ter efeito colateral. A gravação continua
disponível em dashboards.prep.cleaning.executar_tratamento(), usada pelo CLI.
"""
from __future__ import annotations

from functools import lru_cache

from flask import Blueprint, jsonify, request

import config
from dashboards.prep.cleaning import REGRAS, calcular_tratamento

bp = Blueprint("quality", __name__)


@lru_cache(maxsize=4)
def _calcular(caminho: str, mtime_ns: int, tamanho: int, caminho_limpo: str) -> dict:
    """Cache invalidado quando o CSV muda (mtime/tamanho) ou o destino muda."""
    return calcular_tratamento(caminho_bruto=caminho, caminho_limpo=caminho_limpo)


def limpar_cache() -> None:
    """Limpa o cache de leitura (usado pelos testes)."""
    _calcular.cache_clear()


def _resultado() -> dict:
    assinatura = config.RAW_CSV.stat()
    return _calcular(
        str(config.RAW_CSV),
        assinatura.st_mtime_ns,
        assinatura.st_size,
        str(config.CLEAN_CSV),
    )


def resultado_atual() -> dict:
    """Resultado cacheado do tratamento, reutilizado pelas rotas de outliers."""
    return _resultado()


@bp.get("/summary")
def summary():
    return jsonify(_resultado()["resumo"])


@bp.get("/issues")
def issues():
    regra = request.args.get("regra")
    time = request.args.get("time")

    if regra and regra not in REGRAS:
        return jsonify({"erro": "Regra inexistente.", "regra": regra, "regras_validas": sorted(REGRAS)}), 400
    if time and time not in config.TIME_ABREV:
        return jsonify({"erro": "Time inexistente.", "time": time, "times_validos": sorted(config.TIME_ABREV)}), 400

    tabela = _resultado()["issues"]
    if regra:
        tabela = tabela[tabela["regra"] == regra]
    if time:
        tabela = tabela[tabela["time"] == time]

    return jsonify(
        {
            "total": len(tabela),
            "filtros": {"regra": regra, "time": time},
            "issues": tabela.to_dict(orient="records"),
        }
    )


@bp.get("/regras")
def regras():
    return jsonify(
        [
            {"regra": chave, "descricao": valor.descricao, "decisao": valor.decisao}
            for chave, valor in REGRAS.items()
        ]
    )
