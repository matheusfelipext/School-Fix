"""
models.py — "Modelos" do SchoolFix no Firestore.

O Firestore não tem tabelas nem joins. Cada coleção guarda documentos JSON e nós
DENORMALIZAMOS o que precisa aparecer junto (ex.: o chamado já carrega
`autor_nome` e `area_nome`, para a listagem não precisar buscar o usuário e a área).

Coleções:
    usuarios/{id}                 nome, email, senha_hash, perfil, area_id, area_nome, ativo,
                                  preferencias{...}, criado_em
    areas/{id}                    nome, gestor_id, gestor_nome
    chamados/{id}                 titulo, descricao, categoria, area_id, area_nome, status,
                                  prioridade, anonimo, autor_id, autor_nome, autor_perfil, imagem,
                                  canal_prioridade_pedagogica, respostas[ {...} ], criado_em, atualizado_em
    canais/{id}                   nome, descricao, privado, perfis_permitidos[]
    canais/{id}/mensagens/{id}    autor_id, autor_nome, autor_perfil, texto, criado_em
    conversas/{id}                participantes[a,b], nomes{uid:nome}, perfis{uid:perfil},
                                  ultima_mensagem, ultima_mensagem_em
    conversas/{id}/mensagens/{id} autor_id, autor_nome, texto, lida, criado_em
    notificacoes/{id}             usuario_id, tipo, chamado_id, titulo, lida, criado_em
    configuracoes/instituicao     nome_escola, endereco, telefone, email_contato

As funções `*_para_api()` são o equivalente ao antigo `to_dict()`: definem a "cara"
de cada recurso no JSON da API (escondem senha, autor anônimo, etc.).
"""
import copy

from app.repo import iso

# ---------------------------------------------------------------------------
# Valores válidos
# ---------------------------------------------------------------------------
PERFIS = ["aluno", "professor", "gestor", "coordenador", "diretor"]
PERFIS_GESTAO = ["gestor", "coordenador", "diretor"]
STATUS_CHAMADO = ["pendente", "em_analise", "resolvido"]
PRIORIDADES = ["baixa", "media", "alta", "urgente"]
TIPOS_NOTIFICACAO = ["novo_chamado", "status_atualizado", "nova_resposta", "nova_mensagem"]

IDIOMAS = ["pt-BR", "en-US"]
FUSOS = ["America/Sao_Paulo", "America/Manaus", "America/Rio_Branco", "America/Noronha"]
FORMATOS_EXPORTACAO = ["csv", "pdf"]
TEMAS = ["claro", "escuro"]

# Preferências de cada usuário (tela Configurações). Tudo aqui é aplicado de verdade:
#  - notificacoes.*  → a API só cria a notificação se a chave estiver True
#  - idioma / fuso   → o front formata datas com eles
#  - formato_exportacao → botão "Exportar" em Relatórios
#  - tema            → aplicado ao entrar
PREFERENCIAS_PADRAO = {
    "notificacoes": {
        "chamados_urgentes": True,   # gestão: aviso quando abre chamado urgente
        "status_chamados": True,     # autor: quando o status do meu chamado muda
        "respostas": True,           # autor: quando recebo resposta oficial
        "mensagens_diretas": True,   # todos: nova mensagem direta
    },
    "idioma": "pt-BR",
    "fuso_horario": "America/Sao_Paulo",
    "formato_exportacao": "csv",
    "tema": "claro",
}

# tipo de notificação → chave de preferência que a controla (None = sempre envia)
PREFERENCIA_POR_TIPO = {
    "novo_chamado": None,               # gestor da área sempre recebe (é o trabalho dele)
    "novo_chamado_urgente": "chamados_urgentes",
    "status_atualizado": "status_chamados",
    "nova_resposta": "respostas",
    "nova_mensagem": "mensagens_diretas",
}

COL_USUARIOS = "usuarios"
COL_AREAS = "areas"
COL_CHAMADOS = "chamados"
COL_CANAIS = "canais"
COL_CONVERSAS = "conversas"
COL_NOTIFICACOES = "notificacoes"
COL_CONFIGURACOES = "configuracoes"
DOC_INSTITUICAO = "instituicao"


def sub_mensagens(colecao_pai: str, doc_id: str) -> str:
    return f"{colecao_pai}/{doc_id}/mensagens"


# ---------------------------------------------------------------------------
# Preferências
# ---------------------------------------------------------------------------
def preferencias_completas(salvas: dict | None) -> dict:
    """Mescla o que o usuário salvou com o padrão (chaves novas ganham valor padrão)."""
    prefs = copy.deepcopy(PREFERENCIAS_PADRAO)
    salvas = salvas or {}
    prefs["notificacoes"].update({k: bool(v) for k, v in (salvas.get("notificacoes") or {}).items()
                                  if k in prefs["notificacoes"]})
    for chave in ("idioma", "fuso_horario", "formato_exportacao", "tema"):
        if chave in salvas:
            prefs[chave] = salvas[chave]
    return prefs


def validar_preferencias(dados: dict) -> str | None:
    """Devolve mensagem de erro ou None se estiver tudo válido."""
    if "notificacoes" in dados:
        if not isinstance(dados["notificacoes"], dict):
            return "notificacoes deve ser um objeto."
        desconhecidas = set(dados["notificacoes"]) - set(PREFERENCIAS_PADRAO["notificacoes"])
        if desconhecidas:
            return f"Preferências de notificação desconhecidas: {sorted(desconhecidas)}"
    regras = {"idioma": IDIOMAS, "fuso_horario": FUSOS, "formato_exportacao": FORMATOS_EXPORTACAO, "tema": TEMAS}
    for chave, validos in regras.items():
        if chave in dados and dados[chave] not in validos:
            return f"{chave} inválido. Use um de: {validos}"
    extras = set(dados) - set(PREFERENCIAS_PADRAO)
    if extras:
        return f"Chaves não permitidas: {sorted(extras)}"
    return None


# ---------------------------------------------------------------------------
# Serializadores (documento → JSON da API)
# ---------------------------------------------------------------------------
def usuario_para_api(u: dict) -> dict:
    return {
        "id": u["id"],
        "nome": u.get("nome"),
        "email": u.get("email"),
        "perfil": u.get("perfil"),
        "area_id": u.get("area_id"),
        "area_nome": u.get("area_nome"),
        "ativo": bool(u.get("ativo", True)),
        "preferencias": preferencias_completas(u.get("preferencias")),
        "criado_em": iso(u.get("criado_em")),
    }


def area_para_api(a: dict) -> dict:
    return {"id": a["id"], "nome": a.get("nome"), "gestor_id": a.get("gestor_id"), "gestor_nome": a.get("gestor_nome")}


def resposta_para_api(r: dict) -> dict:
    return {**r, "criado_em": iso(r.get("criado_em"))}


def chamado_para_api(c: dict, incluir_imagem=False, incluir_respostas=False) -> dict:
    anonimo = bool(c.get("anonimo"))
    dados = {
        "id": c["id"],
        "protocolo": c["id"][:8].upper(),
        "titulo": c.get("titulo"),
        "descricao": c.get("descricao"),
        "categoria": c.get("categoria"),
        "area": c.get("area_nome"),
        "area_id": c.get("area_id"),
        "status": c.get("status", "pendente"),
        "prioridade": c.get("prioridade", "media"),
        "anonimo": anonimo,
        # Anônimo: escondemos id, nome e perfil do autor
        "autor_id": None if anonimo else c.get("autor_id"),
        "autor_nome": "Anônimo" if anonimo else c.get("autor_nome"),
        "autor_perfil": None if anonimo else c.get("autor_perfil"),
        "tem_imagem": bool(c.get("imagem")),
        "total_respostas": len(c.get("respostas") or []),
        "canal_prioridade_pedagogica": bool(c.get("canal_prioridade_pedagogica")),
        "criado_em": iso(c.get("criado_em")),
        "atualizado_em": iso(c.get("atualizado_em")),
    }
    if incluir_imagem:
        dados["imagem"] = c.get("imagem")
    if incluir_respostas:
        dados["respostas"] = [resposta_para_api(r) for r in (c.get("respostas") or [])]
    return dados


def canal_para_api(c: dict) -> dict:
    return {
        "id": c["id"], "nome": c.get("nome"), "descricao": c.get("descricao"),
        "privado": bool(c.get("privado")), "perfis_permitidos": c.get("perfis_permitidos") or [],
    }


def canal_permite(canal: dict, perfil: str) -> bool:
    return not canal.get("privado") or perfil in (canal.get("perfis_permitidos") or [])


def mensagem_para_api(m: dict) -> dict:
    return {**m, "lida": bool(m.get("lida", False)), "criado_em": iso(m.get("criado_em"))}


def conversa_para_api(c: dict, uid_atual: str, nao_lidas: int = 0) -> dict:
    outros = [p for p in c.get("participantes", []) if p != uid_atual]
    outro = outros[0] if outros else None
    return {
        "id": c["id"],
        "participantes": c.get("participantes", []),
        "outro_id": outro,
        "outro_nome": (c.get("nomes") or {}).get(outro),
        "outro_perfil": (c.get("perfis") or {}).get(outro),
        "ultima_mensagem": c.get("ultima_mensagem"),
        "ultima_mensagem_em": iso(c.get("ultima_mensagem_em")),
        "nao_lidas": nao_lidas,
    }


def notificacao_para_api(n: dict) -> dict:
    return {**n, "lida": bool(n.get("lida", False)), "criado_em": iso(n.get("criado_em"))}
