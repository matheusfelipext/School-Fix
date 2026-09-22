"""
areas_routes.py — Áreas/setores que atendem chamados.
    GET /api/areas (logado) · POST /api/areas · PUT /api/areas/<id> (diretor)
"""
from flask import Blueprint, jsonify, request

from app import repo
from app.auth import login_requerido, perfil_requerido
from app.models import COL_AREAS, COL_USUARIOS, area_para_api

bp = Blueprint("areas", __name__, url_prefix="/api/areas")


def _json():
    return request.get_json(silent=True) or {}


def _validar_gestor(gestor_id):
    if not gestor_id:
        return None, None
    g = repo.obter(COL_USUARIOS, gestor_id)
    if not g or g.get("perfil") != "gestor":
        return None, "gestor_id precisa apontar para um usuário com perfil 'gestor'."
    return g, None


def _vincular(area, gestor):
    """Mantém os dois lados coerentes: area.gestor_* e usuario.area_*."""
    repo.atualizar(COL_AREAS, area["id"], {"gestor_id": gestor["id"] if gestor else None,
                                           "gestor_nome": gestor["nome"] if gestor else None})
    if gestor:
        repo.atualizar(COL_USUARIOS, gestor["id"], {"area_id": area["id"], "area_nome": area["nome"]})


@bp.get("")
@login_requerido
def listar_areas():
    return jsonify([area_para_api(a) for a in repo.listar(COL_AREAS, ordenar="nome")])


@bp.post("")
@perfil_requerido("diretor")
def criar_area():
    d = _json()
    nome = (d.get("nome") or "").strip()
    if not nome:
        return jsonify({"erro": "nome é obrigatório."}), 400
    if repo.primeiro(COL_AREAS, {"nome": nome}):
        return jsonify({"erro": "Já existe uma área com esse nome."}), 409
    gestor, erro = _validar_gestor(d.get("gestor_id"))
    if erro:
        return jsonify({"erro": erro}), 400
    area = repo.criar(COL_AREAS, {"nome": nome, "gestor_id": None, "gestor_nome": None})
    _vincular(area, gestor)
    return jsonify(area_para_api(repo.obter(COL_AREAS, area["id"]))), 201


@bp.put("/<area_id>")
@perfil_requerido("diretor")
def atualizar_area(area_id):
    area = repo.obter(COL_AREAS, area_id)
    if not area:
        return jsonify({"erro": "Área não encontrada."}), 404
    d = _json()
    if d.get("nome", "").strip():
        area = repo.atualizar(COL_AREAS, area_id, {"nome": d["nome"].strip()})
    if "gestor_id" in d:
        gestor, erro = _validar_gestor(d["gestor_id"])
        if erro:
            return jsonify({"erro": erro}), 400
        _vincular(area, gestor)
    return jsonify(area_para_api(repo.obter(COL_AREAS, area_id)))
