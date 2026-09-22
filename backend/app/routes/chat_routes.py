"""
chat_routes.py — Chat geral (canais) e mensagens diretas (conversas 1:1).

    GET  /api/canais                          canais que meu perfil pode ver
    GET  /api/canais/<id>/mensagens?depois=   mensagens (só as novas, se `depois`)
    POST /api/canais/<id>/mensagens
    GET  /api/conversas                       minhas conversas + não lidas
    POST /api/conversas  {destinatario_id}    abre ou reaproveita
    GET  /api/conversas/<id>/mensagens        lê e marca como lidas as recebidas
    POST /api/conversas/<id>/mensagens        envia + notifica (se o outro permitir)

Mensagens ficam em SUBCOLEÇÕES: canais/{id}/mensagens e conversas/{id}/mensagens.
"""
from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt, get_jwt_identity

from app import repo
from app.auth import login_requerido
from app.models import (COL_CANAIS, COL_CONVERSAS, COL_USUARIOS, canal_para_api, canal_permite, conversa_para_api,
                        mensagem_para_api, sub_mensagens)
from app.notificacoes import notificar

bp = Blueprint("chat", __name__, url_prefix="/api")


def _json():
    return request.get_json(silent=True) or {}


def _texto():
    t = (_json().get("texto") or "").strip()
    if not t:
        return None, (jsonify({"erro": "texto é obrigatório."}), 400)
    if len(t) > 2000:
        return None, (jsonify({"erro": "Mensagem muito longa (máx. 2000 caracteres)."}), 400)
    return t, None


def _depois():
    return repo.parse_iso(request.args["depois"]) if request.args.get("depois") else None


def _mensagens(caminho):
    dt = _depois()
    return repo.listar(caminho, maior_que=("criado_em", dt) if dt else None, ordenar="criado_em", limite=200)


# ---------- Canais ----------
def _canal_autorizado(canal_id):
    canal = repo.obter(COL_CANAIS, canal_id)
    if not canal:
        return None, (jsonify({"erro": "Canal não encontrado."}), 404)
    if not canal_permite(canal, get_jwt().get("perfil")):
        return None, (jsonify({"erro": "Você não tem acesso a este canal."}), 403)
    return canal, None


@bp.get("/canais")
@login_requerido
def listar_canais():
    perfil = get_jwt().get("perfil")
    return jsonify([canal_para_api(c) for c in repo.listar(COL_CANAIS, ordenar="nome") if canal_permite(c, perfil)])


@bp.get("/canais/<canal_id>/mensagens")
@login_requerido
def listar_mensagens_canal(canal_id):
    canal, erro = _canal_autorizado(canal_id)
    if erro:
        return erro
    return jsonify([mensagem_para_api(m) for m in _mensagens(sub_mensagens(COL_CANAIS, canal["id"]))])


@bp.post("/canais/<canal_id>/mensagens")
@login_requerido
def enviar_mensagem_canal(canal_id):
    canal, erro = _canal_autorizado(canal_id)
    if erro:
        return erro
    texto, erro = _texto()
    if erro:
        return erro
    claims = get_jwt()
    m = repo.criar(sub_mensagens(COL_CANAIS, canal["id"]), {
        "canal_id": canal["id"], "autor_id": get_jwt_identity(), "autor_nome": claims.get("nome"),
        "autor_perfil": claims.get("perfil"), "texto": texto, "criado_em": repo.agora()})
    return jsonify(mensagem_para_api(m)), 201


# ---------- Conversas ----------
def _conversa_do_usuario(conversa_id, uid):
    c = repo.obter(COL_CONVERSAS, conversa_id)
    if not c:
        return None, (jsonify({"erro": "Conversa não encontrada."}), 404)
    if uid not in c.get("participantes", []):
        return None, (jsonify({"erro": "Você não participa desta conversa."}), 403)
    return c, None


@bp.get("/conversas")
@login_requerido
def listar_conversas():
    uid = get_jwt_identity()
    conversas = repo.listar(COL_CONVERSAS, contem=("participantes", uid), ordenar="ultima_mensagem_em", desc=True)
    saida = []
    for c in conversas:
        nao_lidas = len(repo.listar(sub_mensagens(COL_CONVERSAS, c["id"]), igual={"lida": False},
                                    filtro=lambda m: m.get("autor_id") != uid))
        saida.append(conversa_para_api(c, uid, nao_lidas))
    return jsonify(saida)


@bp.post("/conversas")
@login_requerido
def iniciar_conversa():
    uid, claims = get_jwt_identity(), get_jwt()
    dest_id = _json().get("destinatario_id")
    if not dest_id or dest_id == uid:
        return jsonify({"erro": "Informe um destinatário válido (diferente de você)."}), 400
    dest = repo.obter(COL_USUARIOS, dest_id)
    if not dest or not dest.get("ativo", True):
        return jsonify({"erro": "Destinatário não encontrado."}), 404

    existente = repo.listar(COL_CONVERSAS, contem=("participantes", uid),
                            filtro=lambda c: dest_id in c.get("participantes", []), limite=1)
    if existente:
        return jsonify(conversa_para_api(existente[0], uid))

    c = repo.criar(COL_CONVERSAS, {
        "participantes": [uid, dest_id],
        "nomes": {uid: claims.get("nome"), dest_id: dest["nome"]},
        "perfis": {uid: claims.get("perfil"), dest_id: dest["perfil"]},
        "ultima_mensagem": None, "ultima_mensagem_em": None, "criado_em": repo.agora()})
    return jsonify(conversa_para_api(c, uid)), 201


@bp.get("/conversas/<conversa_id>/mensagens")
@login_requerido
def listar_mensagens_diretas(conversa_id):
    uid = get_jwt_identity()
    c, erro = _conversa_do_usuario(conversa_id, uid)
    if erro:
        return erro
    caminho = sub_mensagens(COL_CONVERSAS, c["id"])
    msgs = _mensagens(caminho)
    for m in msgs:                                    # o que o OUTRO mandou vira "lida"
        if m.get("autor_id") != uid and not m.get("lida"):
            repo.atualizar(caminho, m["id"], {"lida": True})
            m["lida"] = True
    return jsonify([mensagem_para_api(m) for m in msgs])


@bp.post("/conversas/<conversa_id>/mensagens")
@login_requerido
def enviar_mensagem_direta(conversa_id):
    uid, claims = get_jwt_identity(), get_jwt()
    c, erro = _conversa_do_usuario(conversa_id, uid)
    if erro:
        return erro
    texto, erro = _texto()
    if erro:
        return erro
    agora = repo.agora()
    m = repo.criar(sub_mensagens(COL_CONVERSAS, c["id"]), {
        "conversa_id": c["id"], "autor_id": uid, "autor_nome": claims.get("nome"),
        "texto": texto, "lida": False, "criado_em": agora})
    repo.atualizar(COL_CONVERSAS, c["id"], {"ultima_mensagem": texto[:255], "ultima_mensagem_em": agora})
    destinatario = [p for p in c["participantes"] if p != uid][0]
    notificar(destinatario, "nova_mensagem", f"Nova mensagem de {claims.get('nome') or 'alguém'}")
    return jsonify(mensagem_para_api(m)), 201
