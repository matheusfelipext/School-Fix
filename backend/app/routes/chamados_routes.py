"""
chamados_routes.py — Reclamações / ocorrências.

    GET    /api/chamados                 lista (filtrada pelo perfil)
    GET    /api/chamados/estatisticas    números para dashboard/relatórios
    GET    /api/chamados/<id>            detalhe + respostas + imagem
    POST   /api/chamados                 cria e ROTEIA (notifica gestor da área)
    PUT    /api/chamados/<id>/status     gestão
    POST   /api/chamados/<id>/respostas  gestão → notifica autor
    DELETE /api/chamados/<id>            diretor

Visibilidade: aluno/professor → próprios; gestor → sua área; coordenador/diretor → todos.
No Firestore as respostas ficam DENTRO do documento do chamado (lista `respostas`).
"""
from collections import Counter

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt, get_jwt_identity

from app import repo
from app.auth import login_requerido, perfil_requerido, usuario_atual
from app.models import (COL_AREAS, COL_CHAMADOS, COL_NOTIFICACOES, COL_USUARIOS, PERFIS_GESTAO, PRIORIDADES,
                        STATUS_CHAMADO, chamado_para_api, resposta_para_api)
from app.notificacoes import notificar

bp = Blueprint("chamados", __name__, url_prefix="/api/chamados")

# Categoria do formulário → nome da Área que atende (fallback: área com o mesmo nome, depois "Geral")
CATEGORIA_PARA_AREA = {
    "Infraestrutura": "Infraestrutura", "Limpeza": "Limpeza", "Convivência": "Coordenação",
    "Pedagógico": "Coordenação", "Alimentação": "Alimentação", "Segurança": "Segurança",
    "TI": "TI", "Outros": "Geral",
}
_NORM_PRIO = {"média": "media", "medium": "media"}
_NORM_STATUS = {"em análise": "em_analise", "em analise": "em_analise", "em-analise": "em_analise"}
ROTULO_STATUS = {"pendente": "Pendente", "em_analise": "Em análise", "resolvido": "Resolvido"}


def _json():
    return request.get_json(silent=True) or {}


def normalizar_prioridade(v):
    v = (v or "media").strip().lower()
    return _NORM_PRIO.get(v, v)


def normalizar_status(v):
    v = (v or "").strip().lower()
    return _NORM_STATUS.get(v, v)


def resolver_area(categoria, area_nome=None):
    for nome in (area_nome, CATEGORIA_PARA_AREA.get(categoria), categoria, "Geral"):
        if nome:
            area = repo.primeiro(COL_AREAS, {"nome": nome})
            if area:
                return area
    return None


def pode_gerenciar(chamado, claims):
    perfil = claims.get("perfil")
    if perfil in ("diretor", "coordenador"):
        return True
    return perfil == "gestor" and chamado.get("area_id") and chamado["area_id"] == claims.get("area_id")


def pode_ver(chamado, claims, uid):
    return pode_gerenciar(chamado, claims) or chamado.get("autor_id") == uid


def listar_visiveis(claims, uid, igual=None):
    """Aplica a regra de visibilidade como filtro de igualdade no Firestore."""
    igual = dict(igual or {})
    perfil = claims.get("perfil")
    if perfil == "gestor":
        igual["area_id"] = claims.get("area_id")
    elif perfil not in ("diretor", "coordenador"):
        igual["autor_id"] = uid
    return repo.listar(COL_CHAMADOS, igual=igual, ordenar="criado_em", desc=True)


def rotear_chamado(chamado, area):
    """Notifica o gestor da área; se urgente, também diretoria/coordenação (conforme preferência)."""
    if area and area.get("gestor_id"):
        notificar(area["gestor_id"], "novo_chamado",
                  f"Novo chamado ({chamado['prioridade']}) em {area['nome']}: {chamado['titulo']}", chamado["id"])
    if chamado["prioridade"] == "urgente":
        gestao = [u for p in ("diretor", "coordenador") for u in repo.listar(COL_USUARIOS, igual={"perfil": p, "ativo": True})]
        for u in gestao:
            if area and u["id"] == area.get("gestor_id"):
                continue
            notificar(u["id"], "novo_chamado_urgente",
                      f"URGENTE em {area['nome'] if area else chamado['categoria']}: {chamado['titulo']}",
                      chamado["id"], usuario=u)


# ---------------------------------------------------------------------------
@bp.post("")
@login_requerido
def criar_chamado():
    d, claims = _json(), get_jwt()
    autor = usuario_atual()
    titulo = (d.get("titulo") or "").strip()
    descricao = (d.get("descricao") or d.get("mensagem") or "").strip()
    categoria = (d.get("categoria") or "Outros").strip()
    prioridade = normalizar_prioridade(d.get("prioridade"))

    if len(titulo) < 3:
        return jsonify({"erro": "Informe um título com pelo menos 3 caracteres."}), 400
    if len(descricao) < 10:
        return jsonify({"erro": "Descreva o problema com pelo menos 10 caracteres."}), 400
    if prioridade not in PRIORIDADES:
        return jsonify({"erro": f"prioridade inválida. Use um de: {PRIORIDADES}"}), 400
    imagem = d.get("imagem")
    if imagem and not str(imagem).startswith("data:image/"):
        return jsonify({"erro": "Imagem inválida. Envie no formato data:image/...;base64,..."}), 400
    if imagem and len(imagem) > 900_000:   # documento do Firestore tem limite de 1 MB
        return jsonify({"erro": "Imagem muito grande para o banco (máx. ~650 KB). Reduza a resolução."}), 400

    area = resolver_area(categoria, d.get("area"))
    agora = repo.agora()
    chamado = repo.criar(COL_CHAMADOS, {
        "titulo": titulo, "descricao": descricao, "categoria": categoria,
        "area_id": area["id"] if area else None, "area_nome": area["nome"] if area else None,
        "status": "pendente", "prioridade": prioridade, "anonimo": bool(d.get("anonimo", False)),
        "autor_id": autor["id"], "autor_nome": autor["nome"], "autor_perfil": autor["perfil"],
        "imagem": imagem or None,
        "canal_prioridade_pedagogica": bool(d.get("canal_prioridade_pedagogica")) and claims.get("perfil") == "professor",
        "respostas": [], "criado_em": agora, "atualizado_em": agora,
    })
    rotear_chamado(chamado, area)
    return jsonify(chamado_para_api(chamado)), 201


@bp.get("")
@login_requerido
def listar_chamados():
    claims, uid = get_jwt(), get_jwt_identity()
    igual = {}
    status = normalizar_status(request.args.get("status"))
    if status:
        igual["status"] = status
    if request.args.get("categoria"):
        igual["categoria"] = request.args["categoria"]
    if request.args.get("prioridade"):
        igual["prioridade"] = normalizar_prioridade(request.args["prioridade"])

    itens = listar_visiveis(claims, uid, igual)
    busca = (request.args.get("busca") or "").strip().lower()
    if busca:
        itens = [c for c in itens if busca in (c.get("titulo") or "").lower()
                 or busca in (c.get("descricao") or "").lower() or busca in c["id"].lower()]
    limite = request.args.get("limite", type=int)
    if limite:
        itens = itens[:limite]
    return jsonify([chamado_para_api(c) for c in itens])


@bp.get("/estatisticas")
@login_requerido
def estatisticas():
    chamados = listar_visiveis(get_jwt(), get_jwt_identity())
    por_status = Counter(c.get("status") for c in chamados)
    por_prio = Counter(c.get("prioridade") for c in chamados)
    por_cat = Counter(c.get("categoria") for c in chamados)
    total, resolvidos = len(chamados), por_status.get("resolvido", 0)
    return jsonify({
        "total": total,
        "por_status": {s: por_status.get(s, 0) for s in STATUS_CHAMADO},
        "por_prioridade": {p: por_prio.get(p, 0) for p in PRIORIDADES},
        "por_categoria": dict(por_cat.most_common()),
        "taxa_resolucao": round(resolvidos / total * 100, 1) if total else 0,
        "urgentes_abertos": sum(1 for c in chamados if c.get("prioridade") == "urgente" and c.get("status") != "resolvido"),
        "categoria_mais_frequente": por_cat.most_common(1)[0][0] if por_cat else None,
    })


@bp.get("/<chamado_id>")
@login_requerido
def obter_chamado(chamado_id):
    c = repo.obter(COL_CHAMADOS, chamado_id)
    if not c:
        return jsonify({"erro": "Chamado não encontrado."}), 404
    if not pode_ver(c, get_jwt(), get_jwt_identity()):
        return jsonify({"erro": "Você não tem acesso a este chamado."}), 403
    return jsonify(chamado_para_api(c, incluir_imagem=True, incluir_respostas=True))


@bp.put("/<chamado_id>/status")
@login_requerido
def atualizar_status(chamado_id):
    c, claims = repo.obter(COL_CHAMADOS, chamado_id), get_jwt()
    if not c:
        return jsonify({"erro": "Chamado não encontrado."}), 404
    if claims.get("perfil") not in PERFIS_GESTAO:
        return jsonify({"erro": "Sem permissão para atualizar status."}), 403
    if not pode_gerenciar(c, claims):
        return jsonify({"erro": "Você só pode atualizar chamados da sua área."}), 403
    novo = normalizar_status(_json().get("status"))
    if novo not in STATUS_CHAMADO:
        return jsonify({"erro": f"status inválido. Use um de: {STATUS_CHAMADO}"}), 400
    if novo != c.get("status"):
        c = repo.atualizar(COL_CHAMADOS, c["id"], {"status": novo, "atualizado_em": repo.agora()})
        notificar(c["autor_id"], "status_atualizado",
                  f'Seu chamado "{c["titulo"]}" mudou para: {ROTULO_STATUS[novo]}', c["id"])
    return jsonify(chamado_para_api(c))


@bp.post("/<chamado_id>/respostas")
@login_requerido
def responder_chamado(chamado_id):
    c, claims = repo.obter(COL_CHAMADOS, chamado_id), get_jwt()
    if not c:
        return jsonify({"erro": "Chamado não encontrado."}), 404
    if claims.get("perfil") not in PERFIS_GESTAO or not pode_gerenciar(c, claims):
        return jsonify({"erro": "Apenas a gestão responsável pode responder este chamado."}), 403
    texto = (_json().get("texto") or "").strip()
    if not texto:
        return jsonify({"erro": "texto é obrigatório."}), 400

    resposta = {"id": repo.gerar_id(), "chamado_id": c["id"], "autor_id": get_jwt_identity(),
                "autor_nome": claims.get("nome"), "autor_perfil": claims.get("perfil"),
                "texto": texto, "criado_em": repo.agora()}
    repo.atualizar(COL_CHAMADOS, c["id"], {"respostas": (c.get("respostas") or []) + [resposta],
                                           "atualizado_em": repo.agora()})
    notificar(c["autor_id"], "nova_resposta", f'Seu chamado "{c["titulo"]}" recebeu uma resposta oficial.', c["id"])
    return jsonify(resposta_para_api(resposta)), 201


@bp.delete("/<chamado_id>")
@perfil_requerido("diretor")
def excluir_chamado(chamado_id):
    if not repo.obter(COL_CHAMADOS, chamado_id):
        return jsonify({"erro": "Chamado não encontrado."}), 404
    for n in repo.listar(COL_NOTIFICACOES, igual={"chamado_id": chamado_id}):
        repo.excluir(COL_NOTIFICACOES, n["id"])
    repo.excluir(COL_CHAMADOS, chamado_id)
    return "", 204
