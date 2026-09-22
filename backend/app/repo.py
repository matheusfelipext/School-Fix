"""
repo.py — Funções genéricas de acesso ao Firestore ("repositório").

Todas as rotas usam SÓ estas funções; nenhuma rota fala com o Firestore diretamente.
Assim, se um dia o banco mudar, muda-se apenas este arquivo.

Conceitos do Firestore usados aqui:
  * coleção  → "pasta" de documentos (ex.: usuarios)
  * documento → um JSON com id (ex.: usuarios/abc-123)
  * subcoleção → coleção dentro de um documento (ex.: canais/{id}/mensagens)

Índices: o Firestore exige "índice composto" para combinar filtro de igualdade com
ordenação em outro campo. Para não depender de criar índices no console, as funções
abaixo aplicam no Firestore apenas filtros de igualdade e UM filtro de faixa, e fazem
a ORDENAÇÃO e o LIMITE em Python (os volumes de uma escola são pequenos).
"""
import uuid
from datetime import datetime, timezone

from app.firestore_db import get_db


# ---------------------------------------------------------------------------
# Utilitários de data/id
# ---------------------------------------------------------------------------
def gerar_id() -> str:
    return str(uuid.uuid4())


def agora() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt):
    """datetime → texto ISO-8601 (ou None). O Firestore devolve datetimes com timezone."""
    if dt is None:
        return None
    if isinstance(dt, str):
        return dt
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def parse_iso(texto):
    try:
        dt = datetime.fromisoformat(texto.replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (ValueError, AttributeError):
        return None


def _com_tz(dt):
    """Garante timezone para comparar/ordenar datetimes vindos do banco."""
    if isinstance(dt, datetime) and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


# ---------------------------------------------------------------------------
# Referências
# ---------------------------------------------------------------------------
def colecao(caminho: str):
    """
    'usuarios'                      → coleção raiz
    'canais/{id}/mensagens'         → subcoleção (caminho com número ímpar de partes)
    """
    partes = caminho.split("/")
    ref = get_db().collection(partes[0])
    for i in range(1, len(partes), 2):           # alterna documento / subcoleção
        ref = ref.document(partes[i]).collection(partes[i + 1])
    return ref


def _doc_para_dict(snapshot):
    dados = snapshot.to_dict() or {}
    dados["id"] = snapshot.id
    return dados


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------
def obter(caminho: str, doc_id: str):
    """Devolve o documento como dict (com 'id') ou None."""
    if not doc_id:
        return None
    snap = colecao(caminho).document(doc_id).get()
    return _doc_para_dict(snap) if snap.exists else None


def criar(caminho: str, dados: dict, doc_id: str | None = None) -> dict:
    """Cria um documento (gera UUID se não vier id) e devolve o dict salvo."""
    doc_id = doc_id or dados.get("id") or gerar_id()
    salvar = {k: v for k, v in dados.items() if k != "id"}
    colecao(caminho).document(doc_id).set(salvar)
    return {**salvar, "id": doc_id}


def atualizar(caminho: str, doc_id: str, campos: dict) -> dict:
    """Atualiza só os campos informados e devolve o documento completo."""
    campos = {k: v for k, v in campos.items() if k != "id"}
    if campos:
        colecao(caminho).document(doc_id).update(campos)
    return obter(caminho, doc_id)


def excluir(caminho: str, doc_id: str):
    colecao(caminho).document(doc_id).delete()


def excluir_subcolecao(caminho: str):
    for snap in colecao(caminho).stream():
        snap.reference.delete()


def contar(caminho: str, igual: dict | None = None) -> int:
    return len(listar(caminho, igual=igual))


# ---------------------------------------------------------------------------
# Consultas
# ---------------------------------------------------------------------------
def listar(caminho: str, igual: dict | None = None, maior_que: tuple | None = None,
           contem: tuple | None = None, ordenar: str | None = None, desc: bool = False,
           limite: int | None = None, filtro=None) -> list[dict]:
    """
    igual      = {"status": "pendente", "area_id": "..."}   (filtros de igualdade — no Firestore)
    maior_que  = ("criado_em", datetime)                      (um filtro de faixa — no Firestore)
    contem     = ("participantes", uid)                       (array_contains — no Firestore)
    ordenar    = "criado_em"  (+ desc=True)                   (feito em Python)
    limite     = 50                                           (feito em Python, após ordenar)
    filtro     = lambda d: ...                                (qualquer regra extra, em Python)
    """
    q = colecao(caminho)
    for campo, valor in (igual or {}).items():
        q = q.where(campo, "==", valor)
    if maior_que:
        q = q.where(maior_que[0], ">", maior_que[1])
    if contem:
        q = q.where(contem[0], "array_contains", contem[1])

    itens = [_doc_para_dict(s) for s in q.stream()]

    if filtro:
        itens = [d for d in itens if filtro(d)]
    if ordenar:
        itens.sort(key=lambda d: (_com_tz(d.get(ordenar)) is None, _com_tz(d.get(ordenar)) or 0), reverse=desc)
        if desc:  # em desc os None iriam para o topo; mandamos para o fim
            itens = [d for d in itens if d.get(ordenar) is not None] + [d for d in itens if d.get(ordenar) is None]
    if limite:
        itens = itens[:limite]
    return itens


def primeiro(caminho: str, igual: dict) -> dict | None:
    itens = listar(caminho, igual=igual, limite=1)
    return itens[0] if itens else None
