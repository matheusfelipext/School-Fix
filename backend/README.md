# SchoolFix — Back-end (Flask + Cloud Firestore)

API REST do SchoolFix. Documentação completa (arquitetura, Firebase, endpoints, permissões,
correções) em [`../DOCUMENTACAO.md`](../DOCUMENTACAO.md).

## Rodar em desenvolvimento

```bash
python -m venv venv
venv\Scripts\activate            # Linux/Mac: source venv/bin/activate
pip install -r requirements.txt
copy .env.example .env           # Linux/Mac: cp .env.example .env
```

**Com Firebase:** baixe a chave da conta de serviço (Console → Configurações do projeto →
Contas de serviço → Gerar nova chave privada), salve como `firebase-credenciais.json` nesta
pasta e confira `FIREBASE_CREDENTIALS=firebase-credenciais.json` no `.env`.

**Sem Firebase (teste):** coloque `FIRESTORE_MOCK=1` no `.env` — banco em memória.

```bash
python run.py                    # http://127.0.0.1:5000 — popula o banco se estiver vazio
```

Teste: `curl http://127.0.0.1:5000/api/health` → `{"status":"ok","banco":"firestore"}`

Login de teste: `diretor@schoolfix.com` / `123456`

## Estrutura

```
app/__init__.py       create_app(): JWT, CORS, Firestore, blueprints, erros em JSON
app/config.py         variáveis de ambiente
app/firestore_db.py   conexão (real ou mock)
app/repo.py           acesso genérico ao banco (obter/criar/atualizar/listar...)
app/models.py         coleções, valores válidos, preferências, serializadores *_para_api
app/notificacoes.py   cria notificações respeitando as preferências do usuário
app/auth.py           @login_requerido, @perfil_requerido
app/routes/           auth, chamados, usuarios, areas, chat, notificacoes, configuracoes
seed.py               dados de exemplo (python seed.py --reset)
run.py / wsgi.py      dev / gunicorn
```

## Produção (Render)

Start: `gunicorn wsgi:app --bind 0.0.0.0:$PORT` (Procfile).
Variáveis: `SECRET_KEY`, `JWT_SECRET_KEY`, `FIREBASE_CREDENTIALS_JSON` (conteúdo do JSON),
`CORS_ORIGINS`, `FLASK_DEBUG=0`.
