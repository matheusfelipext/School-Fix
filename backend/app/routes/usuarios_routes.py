"""
usuarios_routes.py — Gestão de usuários (diretor) + lista de contatos (todos).

    GET    /api/usuarios            diretor
    GET    /api/usuarios/contatos   logado — [{id,nome,perfil}] ativos, menos eu
    POST   /api/usuarios            diretor — senha obrigatória
    PUT    /api/usuarios/<id>       diretor — nome/email/perfil/ativo/area_id/senha
    DELETE /api/usuarios/<id>       diretor — desativa (soft delete)
"""
from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity
from werkzeug.security import generate_password_hash

from app import repo
from app.auth import login_requerido, perfil_requerido
from app.models import COL_AREAS, COL_USUARIOS, PERFIS, PREFERENCIAS_PADRAO, usuario_para_api

bp = Blueprint("usuarios", __name__, url_prefix="/api/usuarios")


def _json():
    return request.get_json(silent=True) or {}


def _resolver_area(perfil, area_id):
    """Só gestor tem área. Devolve (area_dict|None, erro|None)."""
    if perfil != "gestor":
        return None, None
    if not area_id:
        return None, "Gestor precisa de uma area_id."
    area = repo.obter(COL_AREAS, area_id)
    return (area, None) if area else (None, "Área não encontrada.")


@bp.get("")
@perfil_requerido("diretor")
def listar_usuarios():
    return jsonify([usuario_para_api(u) for u in repo.listar(COL_USUARIOS, ordenar="nome")])


@bp.get("/contatos")
@login_requerido
def listar_contatos():
    uid = get_jwt_identity()
    ativos = repo.listar(COL_USUARIOS, igual={"ativo": True}, ordenar="nome", filtro=lambda u: u["id"] != uid)
    return jsonify([{"id": u["id"], "nome": u["nome"], "perfil": u["perfil"]} for u in ativos])


@bp.post("")
@perfil_requerido("diretor")
def criar_usuario():
    d = _json()
    nome, email = (d.get("nome") or "").strip(), (d.get("email") or "").strip().lower()
    senha, perfil = d.get("senha") or "", d.get("perfil")
    if not nome or not email:
        return jsonify({"erro": "nome e email são obrigatórios."}), 400
    if perfil not in PERFIS:
        return jsonify({"erro": f"perfil inválido. Use um de: {PERFIS}"}), 400
    if len(senha) < 6:
        return jsonify({"erro": "Informe uma senha com pelo menos 6 caracteres."}), 400
    if repo.primeiro(COL_USUARIOS, {"email": email}):
        return jsonify({"erro": "Já existe um usuário com esse e-mail."}), 409
    area, erro = _resolver_area(perfil, d.get("area_id"))
    if erro:
        return jsonify({"erro": erro}), 400

    u = repo.criar(COL_USUARIOS, {
        "nome": nome, "email": email, "perfil": perfil, "senha_hash": generate_password_hash(senha),
        "area_id": area["id"] if area else None, "area_nome": area["nome"] if area else None,
        "ativo": bool(d.get("ativo", True)), "preferencias": PREFERENCIAS_PADRAO, "criado_em": repo.agora(),
    })
    return jsonify(usuario_para_api(u)), 201


@bp.put("/<usuario_id>")
@perfil_requerido("diretor")
def atualizar_usuario(usuario_id):
    u = repo.obter(COL_USUARIOS, usuario_id)
    if not u:
        return jsonify({"erro": "Usuário não encontrado."}), 404
    d, campos = _json(), {}

    if "nome" in d:
        if len((d["nome"] or "").strip()) < 2:
            return jsonify({"erro": "Nome inválido."}), 400
        campos["nome"] = d["nome"].strip()
    if "email" in d:
        email = (d["email"] or "").strip().lower()
        outro = repo.primeiro(COL_USUARIOS, {"email": email})
        if outro and outro["id"] != u["id"]:
            return jsonify({"erro": "Já existe outro usuário com esse e-mail."}), 409
        campos["email"] = email
    if "perfil" in d:
        if d["perfil"] not in PERFIS:
            return jsonify({"erro": f"perfil inválido. Use um de: {PERFIS}"}), 400
        campos["perfil"] = d["perfil"]
    if "ativo" in d:
        if u["id"] == get_jwt_identity() and not d["ativo"]:
            return jsonify({"erro": "Você não pode desativar a própria conta."}), 400
        campos["ativo"] = bool(d["ativo"])
    if "perfil" in d or "area_id" in d:
        perfil = campos.get("perfil", u["perfil"])
        area, erro = _resolver_area(perfil, d.get("area_id", u.get("area_id")))
        if erro:
            return jsonify({"erro": erro}), 400
        campos["area_id"], campos["area_nome"] = (area["id"], area["nome"]) if area else (None, None)
    if d.get("senha"):
        if len(d["senha"]) < 6:
            return jsonify({"erro": "A senha deve ter pelo menos 6 caracteres."}), 400
        campos["senha_hash"] = generate_password_hash(d["senha"])

    u = repo.atualizar(COL_USUARIOS, u["id"], campos)
    return jsonify(usuario_para_api(u))


@bp.delete("/<usuario_id>")
@perfil_requerido("diretor")
def remover_usuario(usuario_id):
    """Soft delete: mantém o histórico (chamados, mensagens) e só bloqueia o login."""
    u = repo.obter(COL_USUARIOS, usuario_id)
    if not u:
        return jsonify({"erro": "Usuário não encontrado."}), 404
    if u["id"] == get_jwt_identity():
        return jsonify({"erro": "Você não pode remover a própria conta."}), 400
    repo.atualizar(COL_USUARIOS, u["id"], {"ativo": False})
    return "", 204
