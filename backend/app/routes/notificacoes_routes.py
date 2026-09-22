"""
notificacoes_routes.py — Sininho.
    GET /api/notificacoes · GET /nao-lidas · PUT /<id>/lida · PUT /ler-todas
"""
from flask import Blueprint, jsonify
from flask_jwt_extended import get_jwt_identity

from app import repo
from app.auth import login_requerido
from app.models import COL_NOTIFICACOES, notificacao_para_api

bp = Blueprint("notificacoes", __name__, url_prefix="/api/notificacoes")


@bp.get("")
@login_requerido
def listar():
    itens = repo.listar(COL_NOTIFICACOES, igual={"usuario_id": get_jwt_identity()}, ordenar="criado_em", desc=True, limite=50)
    return jsonify([notificacao_para_api(n) for n in itens])


@bp.get("/nao-lidas")
@login_requerido
def contar_nao_lidas():
    return jsonify({"total": repo.contar(COL_NOTIFICACOES, {"usuario_id": get_jwt_identity(), "lida": False})})


@bp.put("/<notificacao_id>/lida")
@login_requerido
def marcar_lida(notificacao_id):
    n = repo.obter(COL_NOTIFICACOES, notificacao_id)
    if not n:
        return jsonify({"erro": "Notificação não encontrada."}), 404
    if n.get("usuario_id") != get_jwt_identity():
        return jsonify({"erro": "Esta notificação não é sua."}), 403
    return jsonify(notificacao_para_api(repo.atualizar(COL_NOTIFICACOES, n["id"], {"lida": True})))


@bp.put("/ler-todas")
@login_requerido
def marcar_todas():
    for n in repo.listar(COL_NOTIFICACOES, igual={"usuario_id": get_jwt_identity(), "lida": False}):
        repo.atualizar(COL_NOTIFICACOES, n["id"], {"lida": True})
    return jsonify({"mensagem": "Todas as notificações foram marcadas como lidas."})
