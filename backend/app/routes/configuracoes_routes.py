"""
configuracoes_routes.py — Dados da instituição (documento único configuracoes/instituicao).
    GET /api/configuracoes (logado) · PUT /api/configuracoes (diretor)
Preferências PESSOAIS ficam em /api/auth/me/preferencias.
"""
from flask import Blueprint, jsonify, request

from app import repo
from app.auth import login_requerido, perfil_requerido
from app.models import COL_CONFIGURACOES, DOC_INSTITUICAO

bp = Blueprint("configuracoes", __name__, url_prefix="/api/configuracoes")
CHAVES_PERMITIDAS = {"nome_escola", "endereco", "telefone", "email_contato"}


def _atual():
    doc = repo.obter(COL_CONFIGURACOES, DOC_INSTITUICAO) or {}
    return {k: doc.get(k, "") for k in CHAVES_PERMITIDAS}


@bp.get("")
@login_requerido
def obter():
    return jsonify(_atual())


@bp.put("")
@perfil_requerido("diretor")
def salvar():
    d = request.get_json(silent=True) or {}
    invalidas = set(d) - CHAVES_PERMITIDAS
    if invalidas:
        return jsonify({"erro": f"Chaves não permitidas: {sorted(invalidas)}"}), 400
    novo = {**_atual(), **{k: (str(v) if v is not None else "").strip() for k, v in d.items()}}
    repo.criar(COL_CONFIGURACOES, novo, doc_id=DOC_INSTITUICAO)
    return jsonify(_atual())
