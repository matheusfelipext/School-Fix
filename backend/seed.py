"""
seed.py — Popula o Firestore com áreas, usuários, canais e chamados de exemplo.

    python seed.py            cria o ESSENCIAL que faltar: contas de teste, áreas, canais,
                              dados da escola (sem chamados/mensagens de exemplo)
    python seed.py --exemplos idem + chamados, respostas, mensagens e conversa de exemplo
    python seed.py --reset    APAGA as coleções do SchoolFix e recria o essencial
                              (combine com --exemplos para recriar também os exemplos)
    python seed.py --limpar   APAGA tudo e NÃO recria (banco vazio). Atenção: run.py/wsgi.py
                              repopulam sozinhos se não houver usuários — para manter vazio,
                              defina SEED_AUTOMATICO=0 no ambiente (local e/ou Render).

Em modo mock (sem credenciais) o seed só faz sentido dentro do próprio processo;
use `python run.py` que já chama o seed automaticamente quando o banco está vazio.

Contas (senha 123456): diretor@, coordenador@, gestor.infra@, gestor.limpeza@,
professor@, aluno@  — todas @schoolfix.com
"""
import sys

from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

load_dotenv()

from app import repo  # noqa: E402
from app.models import (  # noqa: E402
    COL_AREAS, COL_CANAIS, COL_CHAMADOS, COL_CONFIGURACOES, COL_CONVERSAS, COL_NOTIFICACOES, COL_USUARIOS,
    DOC_INSTITUICAO, PREFERENCIAS_PADRAO, sub_mensagens,
)

SENHA = generate_password_hash("123456")


def _obter_ou_criar(colecao, filtro, **valores):
    doc = repo.primeiro(colecao, filtro)
    return doc or repo.criar(colecao, {**filtro, **valores})


def limpar_tudo():
    for col in (COL_CHAMADOS, COL_NOTIFICACOES, COL_AREAS, COL_USUARIOS, COL_CONFIGURACOES):
        for d in repo.listar(col):
            repo.excluir(col, d["id"])
    for col in (COL_CANAIS, COL_CONVERSAS):
        for d in repo.listar(col):
            repo.excluir_subcolecao(sub_mensagens(col, d["id"]))
            repo.excluir(col, d["id"])


def executar(silencioso=False, exemplos=False):
    """
    Cria os dados. Chamado por run.py (banco vazio) e pela linha de comando.
    exemplos=False → só o essencial para conseguir entrar e testar do zero.
    """
    areas = {}
    for nome in ["Infraestrutura", "Limpeza", "Alimentação", "Coordenação", "Segurança", "TI", "Geral"]:
        areas[nome] = _obter_ou_criar(COL_AREAS, {"nome": nome}, gestor_id=None, gestor_nome=None)

    def usuario(email, nome, perfil, area=None):
        return _obter_ou_criar(COL_USUARIOS, {"email": email}, nome=nome, perfil=perfil, senha_hash=SENHA,
                               area_id=area["id"] if area else None, area_nome=area["nome"] if area else None,
                               ativo=True, preferencias=PREFERENCIAS_PADRAO, criado_em=repo.agora())

    diretor = usuario("diretor@schoolfix.com", "Matheus Felipe", "diretor")
    usuario("coordenador@schoolfix.com", "Marcos Souza", "coordenador")
    g_infra = usuario("gestor.infra@schoolfix.com", "Carlos Lima", "gestor", areas["Infraestrutura"])
    g_limp = usuario("gestor.limpeza@schoolfix.com", "Ana Paula Ribeiro", "gestor", areas["Limpeza"])
    professor = usuario("professor@schoolfix.com", "Alberto Silva", "professor")
    aluno = usuario("aluno@schoolfix.com", "Lucas Andrade", "aluno")

    repo.atualizar(COL_AREAS, areas["Infraestrutura"]["id"], {"gestor_id": g_infra["id"], "gestor_nome": g_infra["nome"]})
    repo.atualizar(COL_AREAS, areas["Limpeza"]["id"], {"gestor_id": g_limp["id"], "gestor_nome": g_limp["nome"]})

    geral = _obter_ou_criar(COL_CANAIS, {"nome": "geral"}, descricao="Avisos e discussões gerais", privado=False, perfis_permitidos=[])
    _obter_ou_criar(COL_CANAIS, {"nome": "infraestrutura"}, descricao="Manutenção e instalações", privado=False, perfis_permitidos=[])
    _obter_ou_criar(COL_CANAIS, {"nome": "pedagogico"}, descricao="Assuntos acadêmicos", privado=False, perfis_permitidos=[])
    _obter_ou_criar(COL_CANAIS, {"nome": "gestao"}, descricao="Exclusivo da administração", privado=True,
                    perfis_permitidos=["diretor", "coordenador", "gestor"])

    if not repo.obter(COL_CONFIGURACOES, DOC_INSTITUICAO):
        repo.criar(COL_CONFIGURACOES, {
            "nome_escola": "Centro Universitário Salesiano de São Paulo",
            "endereco": "Rua Baronesa Geraldo de Resende, 330 — Campinas/SP",
            "telefone": "(19) 3744-6000", "email_contato": "contato@schoolfix.com",
        }, doc_id=DOC_INSTITUICAO)

    if exemplos and repo.contar(COL_CHAMADOS) == 0:
        agora = repo.agora()

        def chamado(titulo, descricao, categoria, area, status, prioridade, autor, **extra):
            return repo.criar(COL_CHAMADOS, {
                "titulo": titulo, "descricao": descricao, "categoria": categoria,
                "area_id": area["id"], "area_nome": area["nome"], "status": status, "prioridade": prioridade,
                "anonimo": extra.get("anonimo", False), "autor_id": autor["id"], "autor_nome": autor["nome"],
                "autor_perfil": autor["perfil"], "imagem": None,
                "canal_prioridade_pedagogica": extra.get("pedagogico", False),
                "respostas": extra.get("respostas", []), "criado_em": agora, "atualizado_em": agora})

        def resposta(autor, texto):
            return {"id": repo.gerar_id(), "autor_id": autor["id"], "autor_nome": autor["nome"],
                    "autor_perfil": autor["perfil"], "texto": texto, "criado_em": agora}

        chamado("Infiltração no teto do Laboratório de Química",
                "Durante as chuvas de ontem formou-se uma goteira acima da bancada principal.",
                "Infraestrutura", areas["Infraestrutura"], "pendente", "urgente", professor)
        chamado("Ar-condicionado sujo na Sala 04",
                "O filtro do ar-condicionado está com mofo e cheiro forte há duas semanas.",
                "Limpeza", areas["Limpeza"], "resolvido", "media", aluno,
                respostas=[resposta(g_limp, "Filtro higienizado e substituído em 17/09. Chamado encerrado.")])
        chamado("Monitor danificado no laboratório de informática",
                "O monitor da bancada 7 está com a tela trincada e não liga.",
                "Infraestrutura", areas["Infraestrutura"], "em_analise", "alta", aluno,
                respostas=[resposta(g_infra, "Orçamento de reposição solicitado ao fornecedor; prazo de 10 dias.")])
        chamado("Conflito recorrente no intervalo",
                "Alunos do 2º ano relatam provocações constantes no pátio durante o intervalo.",
                "Convivência", areas["Coordenação"], "pendente", "alta", aluno, anonimo=True)
        chamado("Cardápio repetido na cantina",
                "O mesmo lanche foi servido cinco dias seguidos; pedimos mais variedade.",
                "Alimentação", areas["Alimentação"], "pendente", "baixa", aluno)
        chamado("Material didático desatualizado",
                "A apostila de História ainda usa a edição de 2015; solicitamos atualização.",
                "Pedagógico", areas["Coordenação"], "em_analise", "media", professor, pedagogico=True)

        repo.criar(sub_mensagens(COL_CANAIS, geral["id"]), {
            "canal_id": geral["id"], "autor_id": diretor["id"], "autor_nome": diretor["nome"],
            "autor_perfil": "diretor", "texto": "Bem-vindos ao chat do SchoolFix! Use este canal para avisos gerais.",
            "criado_em": agora})

        texto = "Diretor, o técnico já terminou a vistoria do teto do laboratório."
        conv = repo.criar(COL_CONVERSAS, {
            "participantes": [diretor["id"], g_infra["id"]],
            "nomes": {diretor["id"]: diretor["nome"], g_infra["id"]: g_infra["nome"]},
            "perfis": {diretor["id"]: "diretor", g_infra["id"]: "gestor"},
            "ultima_mensagem": texto, "ultima_mensagem_em": agora, "criado_em": agora})
        repo.criar(sub_mensagens(COL_CONVERSAS, conv["id"]), {
            "conversa_id": conv["id"], "autor_id": g_infra["id"], "autor_nome": g_infra["nome"],
            "texto": texto, "lida": False, "criado_em": agora})

    if not silencioso:
        print("\n" + "=" * 52 + "\n  SEED EXECUTADO COM SUCESSO!\n" + "=" * 52)
        print("Dados de exemplo (chamados, mensagens):", "criados" if exemplos else "não criados (use --exemplos)")
        print("Contas para teste (senha: 123456):")
        for u in repo.listar(COL_USUARIOS, ordenar="perfil"):
            print(f" - {u['perfil']:<12} {u['email']}")
        print("=" * 52 + "\n")


if __name__ == "__main__":
    from app import create_app, firestore_db
    app = create_app()
    if firestore_db.modo() == "mock":
        print("AVISO: sem credenciais do Firebase → modo em memória. Os dados só existem enquanto o "
              "processo roda; execute `python run.py` (ele popula sozinho).")
        sys.exit(0)
    with app.app_context():
        if "--limpar" in sys.argv:
            print("Apagando TODAS as coleções do SchoolFix (sem recriar)...")
            limpar_tudo()
            print("Banco vazio. Lembre-se de SEED_AUTOMATICO=0 para o servidor não repopular.")
            sys.exit(0)
        if "--reset" in sys.argv:
            print("Apagando coleções do SchoolFix...")
            limpar_tudo()
        executar(exemplos="--exemplos" in sys.argv)