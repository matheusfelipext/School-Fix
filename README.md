# SchoolFix

Sistema de gestão de ocorrências e reclamações escolares.

- **Front-end**: `frontend/` — HTML, CSS e JavaScript puros (publicado no Netlify).
- **Back-end**: `backend/` — API Flask + JWT, banco Cloud Firestore (publicado no Render).

📘 **[Documentação técnica completa](DOCUMENTACAO.md)** — arquitetura, como rodar, API, permissões e histórico de correções.

## Rodar localmente

```bash
# API
cd backend
python -m venv venv && venv\Scripts\activate      # Linux/Mac: source venv/bin/activate
pip install -r requirements.txt
copy .env.example .env                              # ajuste FIREBASE_CREDENTIALS / FIRESTORE_DATABASE
python run.py                                       # http://127.0.0.1:5000

# Site: abra a pasta frontend com o Live Server (VS Code) → login.html
```

Contas de teste (senha `123456`): `diretor@schoolfix.com`, `coordenador@schoolfix.com`,
`gestor.infra@schoolfix.com`, `professor@schoolfix.com`, `aluno@schoolfix.com`.
