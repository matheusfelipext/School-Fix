"""
__init__.py — "Application Factory" do Flask.

create_app(): configura, liga JWT/CORS, conecta ao Firestore, registra os Blueprints
e define handlers de erro para a API responder SEMPRE em JSON.
"""
import logging

from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException

from app import firestore_db
from app.config import Config
from app.extensions import cors, jwt


def create_app(config_object=Config):
    app = Flask(__name__)
    app.config.from_object(config_object)
    app.json.ensure_ascii = False        # acentos legíveis no JSON
    logging.basicConfig(level=logging.INFO)

    # ---- Extensões e banco --------------------------------------------------
    jwt.init_app(app)
    firestore_db.init_app(app)

    origens = app.config["CORS_ORIGINS"]
    if origens != "*":
        origens = [o.strip() for o in origens.split(",") if o.strip()]
    cors.init_app(app, resources={r"/api/*": {"origins": origens}},
                  allow_headers=["Content-Type", "Authorization"],
                  methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])

    # ---- Blueprints (import aqui dentro evita import circular) -------------
    from app.routes import (areas_routes, auth_routes, chamados_routes, chat_routes,
                            configuracoes_routes, notificacoes_routes, usuarios_routes)
    for modulo in (auth_routes, chamados_routes, usuarios_routes, areas_routes,
                   chat_routes, notificacoes_routes, configuracoes_routes):
        app.register_blueprint(modulo.bp)

    # ---- Rotas utilitárias --------------------------------------------------
    @app.get("/")
    def raiz():
        return jsonify({"servico": "SchoolFix API", "banco": firestore_db.modo(), "saude": "/api/health"})

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok", "banco": firestore_db.modo()})

    # ---- Erros sempre em JSON ----------------------------------------------
    @app.errorhandler(HTTPException)
    def erro_http(e):
        padrao = {400: "Requisição inválida (JSON malformado?).", 404: "Recurso não encontrado.",
                  405: "Método não permitido nesta rota.", 413: "Arquivo/imagem muito grande (máx. 2 MB)."}
        descricao_padrao = e.description == type(e).description
        return jsonify({"erro": padrao.get(e.code, e.description) if descricao_padrao else e.description}), e.code

    @app.errorhandler(Exception)
    def erro_inesperado(e):
        app.logger.exception("Erro inesperado: %s", e)
        return jsonify({"erro": "Erro interno do servidor."}), 500

    @jwt.unauthorized_loader
    def jwt_ausente(_):
        return jsonify({"erro": "Token de acesso ausente. Faça login."}), 401

    @jwt.invalid_token_loader
    def jwt_invalido(_):
        return jsonify({"erro": "Token inválido."}), 401

    @jwt.expired_token_loader
    def jwt_expirado(_h, _p):
        return jsonify({"erro": "Sessão expirada. Faça login novamente."}), 401

    return app
