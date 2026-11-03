"""Aplicação Flask do Projeto 1 (base e qualidade dos dados).

Flask é a sugestão do enunciado e permite reaproveitar o painel já existente.
A camada de dados é independente do framework; a justificativa está em
docs/treatment.md e no README.
"""
from __future__ import annotations

import os

from flask import Flask, jsonify

import config
from dashboards.api.descriptive import bp as descriptive_bp
from dashboards.api.missing import bp as missing_bp
from dashboards.api.outliers import bp as outliers_bp
from dashboards.api.quality import bp as quality_bp
from dashboards.web.panel import register_panel


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
        template_folder=str(config.TEMPLATES_DIR),
    )
    # Desenvolvimento: recarrega templates/CSS sem reiniciar o processo.
    app.config["TEMPLATES_AUTO_RELOAD"] = True
    app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0
    app.register_blueprint(quality_bp, url_prefix="/api/quality")
    app.register_blueprint(missing_bp, url_prefix="/api/missing")
    app.register_blueprint(outliers_bp, url_prefix="/api/outliers")
    app.register_blueprint(descriptive_bp, url_prefix="/api/descriptive")

    register_panel(app)

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
    _debug = os.environ.get("FLASK_DEBUG", "1") == "1"
    if _debug:
        print("Modo desenvolvimento: templates e /static/ sem cache. Reinicie se algo não atualizar.")
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "5000")),
        debug=_debug,
        use_reloader=_debug,
    )
