"""
auth_routes.py — Login, cadastro, perfil e PREFERÊNCIAS do usuário logado.

    POST /api/auth/register           cadastro público (só aluno/professor)
    POST /api/auth/login              → access_token + usuario (com preferencias)
    GET  /api/auth/me
    PUT  /api/auth/me                 {nome}
    PUT  /api/auth/me/senha           {senha_atual, nova_senha}
    GET  /api/auth/me/preferencias
    PUT  /api/auth/me/preferencias    {notificacoes:{...}, idioma, fuso_horario, formato_exportacao, tema}
"""
from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token, get_jwt_identity
from werkzeug.security import check_password_hash, generate_password_hash

from app import repo
from app.auth import login_requerido, usuario_atual
from app.models import (COL_USUARIOS, PREFERENCIAS_PADRAO, preferencias_completas, usuario_para_api,
                        validar_preferencias)

bp = Blueprint("auth", __name__, url_prefix="/api/auth")
PERFIS_AUTO_CADASTRO = ["aluno", "professor"]


def _json():
    return request.get_json(silent=True) or {}


@bp.post("/register")
def register():
    d = _json()
    nome, email = (d.get("nome") or "").strip(), (d.get("email") or "").strip().lower()
    senha, perfil = d.get("senha") or "", d.get("perfil") or "aluno"
    if not nome or not email or not senha:
        return jsonify({"erro": "nome, email e senha são obrigatórios."}), 400
    if len(senha) < 6:
        return jsonify({"erro": "A senha deve ter pelo menos 6 caracteres."}), 400
    if perfil not in PERFIS_AUTO_CADASTRO:
        return jsonify({"erro": f"No auto-cadastro só é permitido: {PERFIS_AUTO_CADASTRO}."}), 400
    if repo.primeiro(COL_USUARIOS, {"email": email}):
        return jsonify({"erro": "Já existe um usuário com esse e-mail."}), 409

    u = repo.criar(COL_USUARIOS, {
        "nome": nome, "email": email, "senha_hash": generate_password_hash(senha), "perfil": perfil,
        "area_id": None, "area_nome": None, "ativo": True,
        "preferencias": PREFERENCIAS_PADRAO, "criado_em": repo.agora(),
    })
    return jsonify(usuario_para_api(u)), 201


@bp.post("/login")
def login():
    d = _json()
    email, senha = (d.get("email") or "").strip().lower(), d.get("senha") or ""
    u = repo.primeiro(COL_USUARIOS, {"email": email})
    if not u or not check_password_hash(u.get("senha_hash", ""), senha):
        return jsonify({"erro": "E-mail ou senha inválidos."}), 401
    if not u.get("ativo", True):
        return jsonify({"erro": "Este usuário está inativo. Fale com a diretoria."}), 403

    token = create_access_token(identity=u["id"], additional_claims={
        "perfil": u["perfil"], "area_id": u.get("area_id"), "nome": u["nome"]})
    return jsonify({"access_token": token, "usuario": usuario_para_api(u)})


@bp.get("/me")
@login_requerido
def me():
    u = usuario_atual()
    return (jsonify(usuario_para_api(u)), 200) if u else (jsonify({"erro": "Usuário não encontrado."}), 404)


@bp.put("/me")
@login_requerido
def atualizar_me():
    nome = (_json().get("nome") or "").strip()
    if len(nome) < 2:
        return jsonify({"erro": "Informe um nome válido."}), 400
    u = repo.atualizar(COL_USUARIOS, get_jwt_identity(), {"nome": nome})
    return jsonify(usuario_para_api(u))


@bp.put("/me/senha")
@login_requerido
def alterar_senha():
    u = usuario_atual()
    d = _json()
    if not check_password_hash(u.get("senha_hash", ""), d.get("senha_atual") or ""):
        return jsonify({"erro": "Senha atual incorreta."}), 400
    nova = d.get("nova_senha") or ""
    if len(nova) < 6:
        return jsonify({"erro": "A nova senha deve ter pelo menos 6 caracteres."}), 400
    repo.atualizar(COL_USUARIOS, u["id"], {"senha_hash": generate_password_hash(nova)})
    return jsonify({"mensagem": "Senha alterada com sucesso."})


@bp.get("/me/preferencias")
@login_requerido
def obter_preferencias():
    return jsonify(preferencias_completas(usuario_atual().get("preferencias")))


@bp.put("/me/preferencias")
@login_requerido
def salvar_preferencias():
    """Recebe só o que mudou; mescla com o que já estava salvo."""
    d = _json()
    erro = validar_preferencias(d)
    if erro:
        return jsonify({"erro": erro}), 400
    u = usuario_atual()
    atuais = preferencias_completas(u.get("preferencias"))
    if "notificacoes" in d:
        atuais["notificacoes"].update({k: bool(v) for k, v in d["notificacoes"].items()})
    for chave in ("idioma", "fuso_horario", "formato_exportacao", "tema"):
        if chave in d:
            atuais[chave] = d[chave]
    repo.atualizar(COL_USUARIOS, u["id"], {"preferencias": atuais})
    return jsonify(atuais)
