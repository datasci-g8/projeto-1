"""Aplicação Flask do Projeto 1 (base e qualidade dos dados).

Flask é a sugestão do enunciado e permite reaproveitar o painel já existente.
A camada de dados é independente do framework; a justificativa está em
docs/tratamento.md e no README.
"""
from __future__ import annotations

import os

from flask import Flask, jsonify, send_from_directory

import config
from dashboards.api.quality import bp as quality_bp


def _caminho_bruto_relativo() -> str:
    """Evita expor caminho absoluto na API."""
    try:
        return str(config.RAW_CSV.relative_to(config.BASE_DIR))
    except ValueError:
        return config.RAW_CSV.name


def create_app() -> Flask:
    app = Flask(
        __name__,
        static_folder=str(config.STATIC_DIR),
        static_url_path="/static",
    )
    app.register_blueprint(quality_bp, url_prefix="/api/quality")

    @app.get("/")
    def index():
        return send_from_directory(app.static_folder, "index.html")

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok", "base": _caminho_bruto_relativo()})

    @app.errorhandler(404)
    def nao_encontrado(_erro):
        return jsonify({"erro": "Recurso não encontrado."}), 404

    @app.errorhandler(500)
    def erro_interno(_erro):
        app.logger.exception("Erro interno ao processar a base")
        return jsonify({"erro": "Erro interno ao processar a base."}), 500

    return app


app = create_app()


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "5000")),
        debug=os.environ.get("FLASK_DEBUG") == "1",
    )
