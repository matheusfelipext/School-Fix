"""
notificacoes.py — Criação de notificações respeitando as preferências do usuário.

Toda notificação do sistema passa por notificar(). Antes de gravar, olhamos
usuario.preferencias.notificacoes[<chave>] (ver PREFERENCIA_POR_TIPO em models.py).
Se o usuário desligou aquele tipo na tela Configurações, nada é criado.
"""
from app import repo
from app.models import COL_NOTIFICACOES, COL_USUARIOS, PREFERENCIA_POR_TIPO, preferencias_completas


def usuario_aceita(usuario: dict | None, tipo: str) -> bool:
    if not usuario or not usuario.get("ativo", True):
        return False
    chave = PREFERENCIA_POR_TIPO.get(tipo)
    if chave is None:
        return True
    return preferencias_completas(usuario.get("preferencias"))["notificacoes"].get(chave, True)


def notificar(usuario_id: str, tipo: str, titulo: str, chamado_id: str | None = None, usuario: dict | None = None):
    """
    tipo pode ser "novo_chamado_urgente" para checar a preferência certa;
    no documento gravamos o tipo "oficial" (novo_chamado).
    """
    usuario = usuario or repo.obter(COL_USUARIOS, usuario_id)
    if not usuario_aceita(usuario, tipo):
        return None
    tipo_gravado = "novo_chamado" if tipo == "novo_chamado_urgente" else tipo
    return repo.criar(COL_NOTIFICACOES, {
        "usuario_id": usuario_id, "tipo": tipo_gravado, "titulo": titulo,
        "chamado_id": chamado_id, "lida": False, "criado_em": repo.agora(),
    })
