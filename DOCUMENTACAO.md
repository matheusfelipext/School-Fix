# SchoolFix — Documentação Técnica

Sistema de gestão de ocorrências/reclamações escolares. Front-end em HTML/CSS/JS puro,
back-end em **Flask** com autenticação **JWT** e banco de dados **Cloud Firestore (Firebase)**.

> Esta documentação explica **o que cada arquivo faz e o que acontece por baixo dos panos**,
> do clique no botão até a linha gravada no banco. Ao final há a lista de problemas
> encontrados na versão anterior e como cada um foi corrigido.

---

## Índice

1. [Visão geral da arquitetura](#1-visão-geral-da-arquitetura)
2. [Como rodar](#2-como-rodar)
3. [O caminho de uma requisição (do clique ao banco)](#3-o-caminho-de-uma-requisição)
4. [Back-end (Flask) — arquivo por arquivo](#4-back-end-flask--arquivo-por-arquivo)
5. [Banco de dados — coleções do Firestore](#5-banco-de-dados-firestore)
6. [Referência da API](#6-referência-da-api)
7. [Permissões por perfil](#7-permissões-por-perfil)
8. [Front-end — arquivo por arquivo](#8-front-end--arquivo-por-arquivo)
9. [CSS — sistema de design e tema escuro](#9-css--sistema-de-design)
10. [Deploy (Render + Netlify/GitHub Pages)](#10-deploy)
11. [Problemas encontrados e correções](#11-problemas-encontrados-e-correções)
12. [Próximos passos sugeridos](#12-próximos-passos-sugeridos)

---

## 1. Visão geral da arquitetura

```
┌──────────────────────────┐   HTTP + JSON    ┌──────────────────────────┐  firebase-admin  ┌──────────────────┐
│ FRONT-END (navegador)    │ ───────────────▶ │ BACK-END (Flask)         │ ───────────────▶ │ Cloud Firestore  │
│ HTML + CSS + JS puro     │  Bearer <JWT>    │ routes/ → repo.py        │                  │ (Firebase)       │
│ Live Server / Netlify    │ ◀─────────────── │ regras, permissões, JWT  │ ◀─────────────── │ coleções JSON    │
└──────────────────────────┘                  └──────────────────────────┘                  └──────────────────┘
```

* **Front e back são projetos separados**, em origens diferentes; conversam só por HTTP/JSON,
  por isso o Flask tem **CORS**.
* **O site nunca fala com o Firebase diretamente.** Só o Flask acessa o Firestore, com a
  *conta de serviço* (chave privada). Assim as regras de quem pode ver/alterar o quê ficam em
  **um lugar só** (Python), e a chave do Firebase nunca vai para o navegador.
* **Autenticação por JWT**: o login devolve um token; o front o envia em todas as requisições.
* **Sem WebSocket.** Chat e sininho usam *polling* (consulta periódica).
* **Modo em memória**: sem credenciais do Firebase, a API sobe com um Firestore *mock* — mesma
  API, dados temporários. Serve para desenvolver/testar sem configurar nada.

Pastas entregues:

```
schoolfix/
├── DOCUMENTACAO.md          ← este arquivo
├── backend/                 ← Flask
│   ├── run.py               ← python run.py (popula o banco se estiver vazio)
│   ├── wsgi.py / Procfile   ← entrada do gunicorn (Render)
│   ├── seed.py              ← dados de exemplo (python seed.py [--reset])
│   ├── requirements.txt
│   ├── .env.example         ← modelo de variáveis de ambiente (credenciais do Firebase)
│   └── app/
│       ├── __init__.py      ← create_app() – monta a aplicação
│       ├── config.py        ← lê variáveis de ambiente
│       ├── extensions.py    ← jwt, cors
│       ├── firestore_db.py  ← conexão com o Firestore (real ou mock)
│       ├── repo.py          ← funções genéricas de acesso ao banco (CRUD/consultas)
│       ├── models.py        ← coleções, valores válidos, preferências e serializadores
│       ├── notificacoes.py  ← cria notificações respeitando as preferências do usuário
│       ├── auth.py          ← decorators @login_requerido / @perfil_requerido
│       └── routes/          ← um arquivo (Blueprint) por assunto
└── frontend/                ← site estático
    ├── login.html, index.html, reclamacoes.html, nova-ocorrencia.html,
    │   chat.html, mensagens.html, relatorios.html, usuarios.html, configuracoes.html
    ├── style.css
    └── js/
        ├── api.js           ← núcleo: URL da API, token, chamarApi, preferências, cabeçalho, menu, sininho
        ├── tema.js          ← modo escuro
        └── <uma página>.js  ← lógica de cada tela
```

---

## 2. Como rodar

### 2.1 Criar o projeto no Firebase (uma vez)

1. Acesse <https://console.firebase.google.com> → **Adicionar projeto** (ex.: `schoolfix`).
2. Menu **Build → Firestore Database → Criar banco de dados** → modo *produção* → região
   `southamerica-east1` (São Paulo).
3. **Regras** do Firestore: como só o Flask (conta de serviço) acessa o banco, deixe tudo
   negado para clientes:
   ```
   rules_version = '2';
   service cloud.firestore {
     match /databases/{database}/documents {
       match /{document=**} { allow read, write: if false; }
     }
   }
   ```
   A conta de serviço **ignora** essas regras — é exatamente o que queremos.
4. **Engrenagem → Configurações do projeto → Contas de serviço → Gerar nova chave privada**.
   Baixa um JSON. Salve como `backend/firebase-credenciais.json` (já está no `.gitignore` —
   **nunca** faça commit dele).

### 2.2 Back-end

```bash
cd backend
python -m venv venv
venv\Scripts\activate           # Linux/Mac: source venv/bin/activate
pip install -r requirements.txt
copy .env.example .env          # Linux/Mac: cp .env.example .env
#  → no .env confira: FIREBASE_CREDENTIALS=firebase-credenciais.json
python run.py                   # API em http://127.0.0.1:5000  (popula o banco na 1ª vez)
```

Sem credenciais? Coloque `FIRESTORE_MOCK=1` no `.env`: a API sobe com banco em memória,
já populado. Bom para o grupo desenvolver o front sem depender do Firebase.

Teste rápido: `http://127.0.0.1:5000/api/health` → `{"status":"ok","banco":"firestore"}`
(ou `"mock"`).

Para recriar os dados de exemplo no Firestore real: `python seed.py --reset`.

### 2.3 Front-end

Abra a pasta `frontend` no VS Code e use o **Live Server** (ou qualquer servidor estático).
Acesse `login.html`. O `api.js` detecta `localhost/127.0.0.1` e usa `http://127.0.0.1:5000`;
publicado, usa a URL do Render. Para forçar outra URL sem editar código, no console:
```js
localStorage.setItem("schoolfix_api", "http://192.168.0.10:5000")
```

### Contas de teste (senha `123456`)

| Perfil      | E-mail                       |
|-------------|------------------------------|
| diretor     | diretor@schoolfix.com        |
| coordenador | coordenador@schoolfix.com    |
| gestor      | gestor.infra@schoolfix.com   |
| gestor      | gestor.limpeza@schoolfix.com |
| professor   | professor@schoolfix.com      |
| aluno       | aluno@schoolfix.com          |

---

## 3. O caminho de uma requisição

Exemplo: o aluno clica em **"Enviar Ocorrência"**.

1. **`nova-ocorrencia.html`** — o `<form id="form-nova-ocorrencia">` dispara o evento `submit`.
2. **`js/nova-ocorrencia.js`** — `salvarOcorrencia()` lê os campos, valida (título ≥ 3,
   descrição ≥ 10), converte a imagem para base64 e chama
   `chamarApi("/api/chamados", { method: "POST", body: {...} })`.
3. **`js/api.js`** — `chamarApi()` monta a URL (`API_BASE_URL + path`), serializa o body em
   JSON, adiciona `Authorization: Bearer <token>` e faz `fetch()`.
4. **Navegador** — como a origem é diferente (5500 → 5000), ele manda antes um `OPTIONS`
   (*preflight*). O **Flask-CORS** responde "pode", e aí o `POST` real é enviado.
5. **`app/__init__.py`** — o Flask recebe e encaminha para o Blueprint `chamados`
   (`url_prefix="/api/chamados"`).
6. **`app/auth.py`** — `@login_requerido` chama `verify_jwt_in_request()`: confere a
   assinatura e a validade do token. Sem token → 401 em JSON.
7. **`app/routes/chamados_routes.py`** — `criar_chamado()`:
   * lê o JSON, normaliza `prioridade` ("Média" → `media`), valida;
   * `resolver_area()` descobre a **Área** responsável a partir da categoria
     (`repo.primeiro("areas", {"nome": ...})`);
   * `repo.criar("chamados", {...})` grava o documento no Firestore com um UUID; o chamado já
     leva `autor_nome`, `autor_perfil` e `area_nome` copiados (denormalização — Firestore não faz JOIN);
   * `rotear_chamado()` chama `notificar()` para o gestor da área (e para diretoria/coordenação
     se urgente). `notificar()` só grava se a **preferência** daquele usuário permitir;
   * devolve `chamado_para_api(chamado)` com status **201**.
8. **`app/repo.py`** — `criar()` faz `db.collection("chamados").document(id).set(dados)`;
   **`app/models.py`** — `chamado_para_api()` define o JSON devolvido (esconde autor anônimo, etc.).
9. **De volta no front** — `chamarApi()` lê o JSON, `salvarOcorrencia()` mostra um aviso
   com o protocolo e redireciona para `reclamacoes.html?id=<id>`.
10. **`reclamacoes.js`** vê o `?id=` na URL e abre o painel de detalhes daquele chamado.

Se algo dá errado no meio (ex.: prioridade inválida), o Flask devolve
`{"erro": "..."}` com status 4xx; `chamarApi()` lança um `Error` com essa mensagem e a tela
mostra o aviso vermelho.

---

## 4. Back-end (Flask) — arquivo por arquivo

### `run.py` / `wsgi.py` / `Procfile`
`run.py` carrega o `.env`, chama `create_app()`, **popula o banco se não houver usuários**
(`seed.executar()`) e sobe o servidor de desenvolvimento. `wsgi.py` só reexporta `app` para o
gunicorn; `Procfile` tem o comando do Render.

### `app/config.py`
Classe `Config` lida de variáveis de ambiente: `SECRET_KEY`, `JWT_SECRET_KEY`, `JWT_HORAS`,
`CORS_ORIGINS`, `MAX_CONTENT_LENGTH` (2 MB — um documento do Firestore aceita até 1 MB, então a
imagem em base64 é limitada a ~650 KB) e as três formas de conectar ao Firebase:
`FIREBASE_CREDENTIALS` (caminho do JSON), `FIREBASE_CREDENTIALS_JSON` (conteúdo, para o Render)
ou `FIRESTORE_MOCK=1` (memória).

### `app/firestore_db.py` — conexão
`init_app(app)` decide o modo: com credenciais, `firebase_admin.initialize_app(Certificate(...))`
e `firestore.client()`; sem, `mockfirestore.MockFirestore()` (mesma interface). `get_db()` devolve
o cliente para o `repo.py`; `modo()` devolve `"firestore"` ou `"mock"` (aparece em `/api/health`).

### `app/repo.py` — repositório genérico
**Nenhuma rota fala com o Firestore diretamente**; todas usam estas funções:

| Função | O que faz |
|---|---|
| `obter(colecao, id)` | documento como dict (com `id`) ou `None` |
| `criar(colecao, dados, id=None)` | `set()` com UUID gerado; devolve o dict salvo |
| `atualizar(colecao, id, campos)` | `update()` parcial; devolve o documento completo |
| `excluir(colecao, id)` / `excluir_subcolecao(caminho)` | apaga |
| `listar(colecao, igual=, maior_que=, contem=, ordenar=, desc=, limite=, filtro=)` | consulta |
| `primeiro(colecao, igual)` | primeiro resultado ou `None` |
| `contar(colecao, igual)` | quantidade |
| `agora()`, `iso()`, `parse_iso()`, `gerar_id()` | utilitários |

Caminhos com barra viram **subcoleções**: `"canais/{id}/mensagens"`.

**Por que ordenar em Python?** O Firestore exige *índice composto* para combinar filtro de
igualdade com `order_by` em outro campo (ex.: `area_id == X` ordenado por `criado_em`). Para o
projeto não depender de criar índices no console, `listar()` aplica no Firestore só filtros de
igualdade, um `array_contains` e um filtro de faixa, e faz ordenação/limite em Python. Os volumes
de uma escola são pequenos; se crescer, crie os índices e mova a ordenação para a query.

### `app/models.py` — coleções, valores válidos e serializadores
Documenta o **formato de cada coleção** (seção 5), as listas de valores válidos (`PERFIS`,
`STATUS_CHAMADO`, `PRIORIDADES`, `IDIOMAS`, `FUSOS`...), as **preferências padrão** do usuário e
qual preferência controla cada tipo de notificação (`PREFERENCIA_POR_TIPO`). As funções
`*_para_api()` são a "cara" de cada recurso no JSON (equivalente ao antigo `to_dict()`):
escondem `senha_hash`, ocultam autor de chamado anônimo, só incluem a imagem no detalhe, etc.

### `app/notificacoes.py`
`notificar(usuario_id, tipo, titulo, chamado_id)` é o **único** ponto que cria notificações.
Antes de gravar, lê `usuarios/{id}.preferencias.notificacoes` e verifica a chave associada ao
tipo (`status_atualizado → status_chamados`, `nova_resposta → respostas`, `nova_mensagem →
mensagens_diretas`, `novo_chamado_urgente → chamados_urgentes`). O aviso ao gestor da área
(`novo_chamado`) não pode ser desligado — é o trabalho dele.

### `app/auth.py`
`@login_requerido`, `@perfil_requerido("diretor", ...)` e `usuario_atual()` (busca o documento do
usuário do token). Como o JWT funciona: no login colocamos `perfil`, `area_id` e `nome` dentro do
token (`additional_claims`); nas rotas, `get_jwt()` lê isso sem consultar o banco.

### `app/__init__.py` — *Application Factory*
`create_app()`: configura, `jwt.init_app`, `firestore_db.init_app`, CORS em `/api/*`, registra os
7 Blueprints e define **handlers de erro** para responder sempre JSON (400/404/405/413, 500 e os
três casos de JWT em português).

### `app/routes/*.py` — um Blueprint por assunto
| Arquivo | Responsabilidade |
|---|---|
| `auth_routes.py` | register, login, `/me`, nome, senha e **`/me/preferencias`** |
| `chamados_routes.py` | CRUD de chamados, roteamento por área, status, respostas (embutidas no documento), estatísticas |
| `usuarios_routes.py` | CRUD do diretor + `/contatos`; *soft delete* |
| `areas_routes.py` | áreas e vínculo com gestor (mantém `area.gestor_*` e `usuario.area_*` coerentes) |
| `chat_routes.py` | canais (regra de privacidade) e conversas 1:1 (regra de participação); mensagens em subcoleções |
| `notificacoes_routes.py` | listar, contar não lidas, marcar lida(s) — só as próprias |
| `configuracoes_routes.py` | dados da instituição (documento único `configuracoes/instituicao`) |

### `seed.py`
Idempotente: `_obter_ou_criar()` só insere o que falta. `--reset` apaga as coleções do SchoolFix
e recria. É chamado automaticamente por `run.py` quando não há usuários.

---

## 5. Banco de dados (Firestore)

O Firestore é um banco de **documentos JSON** organizados em coleções — não há tabelas, chaves
estrangeiras nem JOIN. Por isso alguns dados são **copiados** (denormalizados) para onde são
lidos: o chamado guarda `autor_nome` e `area_nome`; a conversa guarda `nomes` e `perfis` dos dois
participantes. Quando um nome muda, a lista antiga continua com o nome da época (aceitável
para um histórico de ocorrências).

| Coleção / documento | Campos |
|---|---|
| `usuarios/{id}` | nome, email, senha_hash, perfil, area_id, area_nome, ativo, **preferencias{}**, criado_em |
| `areas/{id}` | nome, gestor_id, gestor_nome |
| `chamados/{id}` | titulo, descricao, categoria, area_id, area_nome, status, prioridade, anonimo, autor_id, autor_nome, autor_perfil, imagem (base64), canal_prioridade_pedagogica, **respostas[ ]**, criado_em, atualizado_em |
| `canais/{id}` | nome, descricao, privado, perfis_permitidos[ ] |
| `canais/{id}/mensagens/{id}` | autor_id, autor_nome, autor_perfil, texto, criado_em |
| `conversas/{id}` | participantes[a, b], nomes{}, perfis{}, ultima_mensagem, ultima_mensagem_em |
| `conversas/{id}/mensagens/{id}` | autor_id, autor_nome, texto, lida, criado_em |
| `notificacoes/{id}` | usuario_id, tipo, chamado_id, titulo, lida, criado_em |
| `configuracoes/instituicao` | nome_escola, endereco, telefone, email_contato |

**Preferências** (`usuarios/{id}.preferencias`):
```json
{
  "notificacoes": { "chamados_urgentes": true, "status_chamados": true, "respostas": true, "mensagens_diretas": true },
  "idioma": "pt-BR",              // pt-BR | en-US   → formato de datas/números no front
  "fuso_horario": "America/Sao_Paulo",  // → horários exibidos no front
  "formato_exportacao": "csv",    // csv | pdf      → botão Exportar em Relatórios
  "tema": "claro"                 // claro | escuro → aplicado ao entrar
}
```

Valores válidos (em `models.py`): `PERFIS = aluno, professor, gestor, coordenador, diretor` ·
`STATUS_CHAMADO = pendente, em_analise, resolvido` · `PRIORIDADES = baixa, media, alta, urgente`.

**Senhas** nunca são gravadas em texto: `generate_password_hash` (scrypt) / `check_password_hash`.

**Limites do Firestore que importam aqui:** documento ≤ 1 MB (por isso a imagem é limitada a
~650 KB em base64); consultas com igualdade + ordenação em campos diferentes pedem índice
composto (evitado ordenando em Python — ver `repo.py`).

---

## 6. Referência da API

Todas as rotas (exceto login/register/health) exigem `Authorization: Bearer <token>`.
Erros vêm como `{"erro": "mensagem"}`.

### Autenticação — `/api/auth`
| Método | Rota | Quem | Corpo / Retorno |
|---|---|---|---|
| POST | `/register` | público | `{nome,email,senha,perfil?}` (perfil só aluno/professor) → usuário 201 |
| POST | `/login` | público | `{email,senha}` → `{access_token, usuario}` |
| GET | `/me` | logado | usuário atual (inclui `preferencias`) |
| PUT | `/me` | logado | `{nome}` |
| PUT | `/me/senha` | logado | `{senha_atual, nova_senha}` |
| GET | `/me/preferencias` | logado | preferências completas |
| PUT | `/me/preferencias` | logado | envia só o que mudou, ex.: `{"notificacoes":{"respostas":false}}` ou `{"tema":"escuro"}` |

### Chamados — `/api/chamados`
| Método | Rota | Quem | Observações |
|---|---|---|---|
| GET | `` | logado | filtros: `?status=&categoria=&prioridade=&busca=&limite=`; visibilidade por perfil |
| GET | `/estatisticas` | logado | `{total, por_status, por_prioridade, por_categoria, taxa_resolucao, urgentes_abertos, categoria_mais_frequente}` |
| GET | `/<id>` | autor ou gestão | inclui `respostas[]` e `imagem` |
| POST | `` | logado | `{titulo, descricao, categoria, prioridade?, anonimo?, imagem?, canal_prioridade_pedagogica?}` → 201 |
| PUT | `/<id>/status` | gestor da área / coord. / diretor | `{status}`; notifica o autor |
| POST | `/<id>/respostas` | idem | `{texto}`; resposta fica embutida no documento; notifica o autor |
| DELETE | `/<id>` | diretor | 204 |

### Usuários — `/api/usuarios`
| Método | Rota | Quem |
|---|---|---|
| GET | `` | diretor |
| GET | `/contatos` | logado — `[{id,nome,perfil}]` dos ativos, menos você |
| POST | `` | diretor — `{nome,email,senha,perfil,area_id?,ativo?}` |
| PUT | `/<id>` | diretor — qualquer subconjunto de `nome,email,perfil,ativo,area_id,senha` |
| DELETE | `/<id>` | diretor — **desativa** (soft delete) |

### Áreas — `/api/areas`: `GET` (logado), `POST`, `PUT /<id>` (diretor).

### Chat — `/api`
| Método | Rota | Observações |
|---|---|---|
| GET | `/canais` | só os que o perfil pode ver |
| GET | `/canais/<id>/mensagens?depois=<ISO>` | `depois` traz só as novas (polling) |
| POST | `/canais/<id>/mensagens` | `{texto}` |
| GET | `/conversas` | com `nao_lidas` por conversa |
| POST | `/conversas` | `{destinatario_id}` → reaproveita se já existir (200) ou cria (201) |
| GET | `/conversas/<id>/mensagens?depois=` | marca como lidas as recebidas |
| POST | `/conversas/<id>/mensagens` | `{texto}`; notifica o outro |

### Notificações — `/api/notificacoes`: `GET ``, `GET /nao-lidas`, `PUT /<id>/lida`, `PUT /ler-todas`.

### Configurações — `/api/configuracoes`: `GET` (logado), `PUT` (diretor) com as chaves
`nome_escola, endereco, telefone, email_contato`.

---

## 7. Permissões por perfil

| Ação | aluno | professor | gestor | coordenador | diretor |
|---|:-:|:-:|:-:|:-:|:-:|
| Criar chamado | ✔ | ✔ | ✔ | ✔ | ✔ |
| Ver chamados | próprios | próprios | da sua área | todos | todos |
| Mudar status / responder | – | – | da sua área | ✔ | ✔ |
| Excluir chamado | – | – | – | – | ✔ |
| Marcar "prioridade pedagógica" | – | ✔ | – | – | – |
| Relatórios (menu) | – | – | ✔ | ✔ | ✔ |
| Gerir usuários / áreas | – | – | – | – | ✔ |
| Editar dados da instituição | – | – | – | – | ✔ |
| Canal privado `gestao` | – | – | ✔ | ✔ | ✔ |
| Preferência "reclamações urgentes" (visível) | – | – | ✔ | ✔ | ✔ |

A regra é aplicada **no Flask** (fonte da verdade) e espelhada no front apenas para
esconder botões/menus — esconder no front não é segurança.

---

## 8. Front-end — arquivo por arquivo

### Layout comum (todas as páginas logadas)
Sidebar + header são idênticos em todas as páginas. O header tem: nome da escola
(`#cabecalho-escola`, vindo de `/api/configuracoes`), **sininho** (`#notificacoes-botao` com contador e
dropdown), avatar/nome/perfil (`#cabecalho-avatar`, `#cabecalho-nome`, `#cabecalho-cargo`) e botão sair.
Ordem dos scripts: `tema.js` no `<head>` (evita "piscar" branco no modo escuro), depois
`api.js` e por último o script da página.

### `js/api.js` — o núcleo
Substitui `api-config.js`, `auth.js`, `auth-header.js` e `script.js` da versão antiga.
* **`API_BASE_URL`**: local → `http://127.0.0.1:5000`; publicado → Render; override via
  `localStorage.schoolfix_api`.
* **Sessão**: `obterToken/salvarToken/obterUsuario/salvarUsuario/logout/exigirLogin`, com **uma**
  chave para cada coisa (`schoolfix_token`, `schoolfix_usuario`).
* **`chamarApi(path, options)`**: aceita `body` como objeto (vira JSON), injeta o token,
  trata 401 (logout), 204 (null) e erros (`throw new Error(erro)`).
* **Helpers**: `escaparHtml` (anti-XSS — obrigatório antes de qualquer `innerHTML` com dado
  do usuário), `formatarData/Hora` (usam **idioma e fuso das preferências**), `etiquetaStatus`,
  `etiquetaPrioridade`, `rotuloPerfil`, `aviso` (substitui `alert`), `linhaVazia`.
* **Preferências**: `obterPreferencias()` (do usuário salvo) e `salvarPreferencias(parcial)`
  (PUT na API, atualiza o localStorage e aplica o tema). `aplicarTemaDasPreferencias()` roda ao
  carregar e ao revalidar `/me`, então o tema escolhido acompanha o usuário em qualquer dispositivo.
* **Inicialização** (`DOMContentLoaded`): se a página não é pública (`<body data-publica>`),
  exige login, preenche o header, marca o menu ativo pela URL, **esconde itens do menu por
  perfil** (`PAGINAS_POR_PERFIL`), carrega o sininho (e atualiza a cada 30 s) e revalida o
  token em `/api/auth/me`.

### `js/tema.js`
Aplica `tema-escuro` no `<html>` imediatamente se salvo. `alternarTema()` grava a escolha e
dispara o evento `temaAlterado`, que `reclamacoes.js` e `relatorios.js` escutam para
redesenhar os gráficos com as cores do novo tema.

### Scripts de página
| Arquivo | O que faz | Endpoints |
|---|---|---|
| `login.js` | valida, chama login, guarda sessão, redireciona; mostra erro no `#login-erro` (sem `alert`) | `POST /api/auth/login` |
| `inicio.js` | KPIs, tabela de 5 recentes (clicável), barras de categoria **dinâmicas** | `/estatisticas`, `/chamados?limite=5` |
| `reclamacoes.js` | tabela com busca/filtro local, painel de detalhes (abre via `?id=`), atualizar status, responder, donut de status; esconde a área de gestão para aluno/professor | `/chamados`, `/chamados/<id>`, `PUT status`, `POST respostas` |
| `nova-ocorrencia.js` | preview e limite de 2 MB da imagem, anônimo, prioridade pedagógica só para professor, redireciona para o detalhe criado | `POST /chamados` |
| `chat.js` | lista canais, seleciona, **polling incremental** a cada 4 s com `?depois=`, destaca minhas mensagens | `/canais`, `/canais/<id>/mensagens` |
| `mensagens.js` | conversas com contador de não lidas (atualiza a cada 10 s), abrir, enviar, iniciar conversa a partir de `/contatos` | `/conversas`, `/usuarios/contatos` |
| `relatorios.js` | cards + donut de prioridade + barras por categoria, cores lidas das variáveis CSS; **Exportar** (CSV baixa arquivo; PDF abre impressão com CSS `@media print`) conforme a preferência | `/estatisticas`, `/chamados` |
| `usuarios.js` | bloqueia não-diretor, CRUD, campo "área" só para gestor, senha obrigatória ao criar / opcional ao editar, desativar | `/usuarios`, `/areas` |
| `configuracoes.js` | dados da instituição (só diretor edita), meu nome, trocar senha; **preferências e notificações salvam no ato** da mudança (selects `data-pref`, interruptores `data-notif`, tema); "reclamações urgentes" só aparece para a gestão | `/configuracoes`, `/auth/me`, `/auth/me/senha`, `/auth/me/preferencias` |

### HTML — pontos de atenção
* `nova-ocorrencia.html`: os `value` dos selects estão **em minúsculo, iguais à API**
  (`baixa/media/alta/urgente`). O antigo campo "Status inicial" foi removido — status
  inicial é sempre `pendente` e só a gestão altera.
* `login.html`: `<body data-publica="true">` diz ao `api.js` para não exigir login.
* `reclamacoes.html`: `#area-gestao` agrupa status + resposta para poder ser ocultado.
* **Nomenclatura**: todas as classes e ids são em **português semântico** (ver glossário na seção 9). Ícones do Tabler (`ti ti-*`) são a única exceção, por serem de biblioteca externa.
* Nenhuma página carrega Firebase nem tem `onclick` para funções inexistentes.

---

## 9. CSS — sistema de design

`style.css` é baseado em **variáveis CSS (design tokens)** definidas em `:root`
(`--primary`, `--bg-card`, `--text-primary`, `--danger`...). O bloco
`html.tema-escuro { ... }` **redefine as mesmas variáveis** com valores escuros — por isso o
modo escuro funciona sem duplicar regras: os componentes só usam `var(--x)`.

Os gráficos (Chart.js) não leem CSS; por isso `relatorios.js`/`reclamacoes.js` fazem
`getComputedStyle(document.documentElement).getPropertyValue("--danger")` na hora de
desenhar e redesenham quando o tema muda.

Seções principais do arquivo: tokens → reset → sidebar/header → cards/KPIs → tabelas e
badges (`.etiqueta-*`, `.prioridade-*`, `.cargo-etiqueta`) → formulários → chat → configurações →
responsividade (`@media`) → **Complementos** (adicionado nesta versão: sininho, toast,
painel de detalhes, formulário, mensagens simplificadas, switch, login — que antes estava
inline em `login.html`).


### Glossário de classes (inglês antigo → português atual)

Todas as classes/ids foram padronizadas em português para o grupo ler o CSS sem traduzir.
Regra adotada: **substantivo do componente + qualificador**, separados por hífen
(`cartao-titulo`, `indicador-valor`, `etiqueta-pendente`).

| Área | Antes | Agora |
|---|---|---|
| Estrutura | `app`, `sidebar`, `main`, `content-area`, `footer`, `view` | `aplicacao`, `barra-lateral`, `principal`, `conteudo`, `rodape`, `tela` |
| Menu | `nav-items`, `nav-item`, `active` | `menu`, `menu-item`, `ativo` |
| Cabeçalho | `header`, `header-school`, `header-right`, `user-profile`, `user-meta`, `.name`, `.role`, `icon-btn` | `cabecalho`, `cabecalho-escola`, `cabecalho-direita`, `usuario-perfil`, `usuario-info`, `.nome`, `.cargo`, `botao-icone` |
| Notificações | `notif-wrap`, `notif-badge`, `notif-painel`, `notif-item`, `notif-vazio` | `notificacoes`, `notificacoes-contador`, `notificacoes-painel`, `notificacao`, `notificacoes-vazio` |
| Cartões/KPIs | `card`, `card-title`, `card-title-row`, `kpi-row`, `kpi-card`, `kpi-value`, `dashboard-grid` | `cartao`, `cartao-titulo`, `cartao-titulo-linha`, `indicadores`, `indicador`, `indicador-valor`, `painel-grade` |
| Barras/legenda | `bar-row`, `bar-track`, `bar-fill`, `count`, `legend-row` | `barra-linha`, `barra-trilho`, `barra-preenchimento`, `contagem`, `legenda` |
| Tabelas | `td-vazio`, `btn-tbl`, `btn-tbl-edit`, `btn-tbl-delete` | `celula-vazia`, `botao-tabela`, `botao-tabela-editar`, `botao-tabela-excluir` |
| Etiquetas | `badge`, `badge-pendente/analise/resolvido/ativo/inativo` | `etiqueta`, `etiqueta-pendente/analise/resolvido/ativo/inativo` |
| Prioridade | `badge-prio`, `badge-baixa/media/alta/urgente` | `prioridade`, `prioridade-baixa/media/alta/urgente` |
| Cargo | `role-badge`, `role-diretoria`, `role-gestor`… | `cargo-etiqueta`, `cargo-diretoria`, `cargo-gestor`… |
| Botões | `btn`, `btn-primary`, `btn-outline`, `btn-submit`, `send-btn` | `botao`, `botao-primario`, `botao-contorno`, `botao-enviar`, `botao-enviar-mensagem` |
| Formulário | `field`, `form-group`, `form-label`, `form-control`, `form-check`, `file-upload-box` | `campo`, `campo-grupo`, `campo-rotulo`, `campo-controle`, `campo-marcacao`, `area-upload` |
| Busca/filtros | `search-bar`, `filter-tabs`, `filter-tab`, `two-col` | `busca`, `filtros`, `filtro`, `duas-colunas` |
| Detalhes | `details-panel`, `.meta`, `.desc`, `section-label`, `divider`, `resposta-item` | `detalhes`, `.resumo`, `.descricao`, `secao-rotulo`, `divisor`, `resposta` |
| Chat | `chat-layout`, `chat-col`, `chat-messages`, `chat-input-bar`, `channel-item`, `conv-item`, `msg`, `msg-minha` | `chat-grade`, `chat-coluna`, `mensagens-lista`, `chat-entrada`, `canal`, `conversa`, `mensagem`, `mensagem-minha` |
| Gráficos | `chart-container`, `chart-card`, `donut-center-text`, `stats-row`, `stat-card`, `stat-value` | `grafico-area`, `grafico-cartao`, `grafico-centro`, `estatisticas`, `estatistica`, `estatistica-valor` |
| Configurações | `settings-section`, `toggle-row`, `switch`, `switch.on` | `configuracoes-secao`, `alternador-linha`, `interruptor`, `interruptor.ligado` |
| Avisos | `toast`, `toast-sucesso/erro`, `show` | `aviso`, `aviso-sucesso/erro`, `visivel` |
| Tema | `dark-theme` | `tema-escuro` |
| Login | `login-page`, `login-card`, `login-hint` | `login-pagina`, `login-cartao`, `login-dica` |

Ids seguem a mesma lógica: `kpi-total` → `indicador-total`, `chartCategoria` → `grafico-categoria`,
`oc-titulo` → `ocorrencia-titulo`, `inst-nome` → `instituicao-nome`, `btn-salvar-usuario` →
`botao-salvar-usuario`, `chk-tema` → `alternador-tema`, `user-nome` → `cabecalho-nome`.

Funções JS utilitárias também: `getToken/setToken` → `obterToken/salvarToken`,
`getUsuario/setUsuario` → `obterUsuario/salvarUsuario`, `apiFetch` → `chamarApi`,
`escapeHtml` → `escaparHtml`, `toast` → `aviso`, `badgeStatus/badgePrioridade` →
`etiquetaStatus/etiquetaPrioridade`.

---

## 10. Deploy

**Back-end no Render**
1. Repositório com a pasta `backend` (ou *root directory* = `backend`).
2. Build: `pip install -r requirements.txt` · Start: `gunicorn wsgi:app --bind 0.0.0.0:$PORT`
   (já está no `Procfile`).
3. Variáveis de ambiente no painel: `SECRET_KEY`, `JWT_SECRET_KEY` (aleatórias e longas),
   **`FIREBASE_CREDENTIALS_JSON`** = conteúdo inteiro do JSON da conta de serviço (o Render não
   guarda arquivos), `CORS_ORIGINS=https://SEU-SITE.netlify.app`, `FLASK_DEBUG=0`.
4. Na primeira subida o `wsgi.py` popula o Firestore sozinho se não houver usuários.

**Front-end no Netlify / GitHub Pages**: publique a pasta `frontend`. Confira a URL do
Render em `js/api.js` (constante `API_PRODUCAO`).

> Plano gratuito do Render "dorme" após inatividade: a primeira requisição pode levar ~30 s.
> O `chamarApi` mostra a mensagem "Não foi possível conectar" se estourar — basta tentar de novo.

---

## 11. Problemas encontrados e correções

### Críticos (impediam o funcionamento)
| # | Problema | Onde | Correção |
|---|---|---|---|
| 1 | Front misturava **Firestore e Flask**: login no Flask, mas dashboard, reclamações, chat, usuários e relatórios liam do Firebase (por isso apareciam dados de teste que não estavam no SQLite) | 7 scripts + todos os HTML | Firebase removido por completo; tudo via `chamarApi` |
| 2 | **Duas chaves de sessão** (`token` vs `schoolfix_token`) — `chamarApi` nunca achava o token e deslogava | `api-config.js`, `login.js`, `index.js` | Uma chave só, centralizada em `api.js` |
| 3 | **Três URLs de API diferentes** (`127.0.0.1:5000`, `127.0.0.1:5000/api`, Render) | 5 arquivos | `API_BASE_URL` único com detecção automática |
| 4 | `criar_chamado` exigia campo `area` que o formulário não enviava → **todo POST dava 400** | `chamados_routes.py` | `resolver_area()` mapeia categoria → área, com fallback "Geral" |
| 5 | Front enviava `"Média"`, `"Em Análise"`; API só aceitava `media`, `em_analise` | HTML + rotas | Selects em minúsculo **e** normalização tolerante no Flask |
| 6 | `configuracoes_routes.py` (`config_bp`) **nunca registrado**, sem auth, dados falsos | `__init__.py` | Reescrito com tabela `Configuracao`; registrado |
| 7 | `reclamacoes.js` tinha código morto no fim referenciando `doc` → `ReferenceError` a cada carga | `reclamacoes.js` | Removido |
| 8 | `index.html` carregava `inicio.js` (Firestore) **e** `index.js` (Flask), ambos escrevendo na mesma tabela | `index.html` | Um só `inicio.js` |

### Segurança
| # | Problema | Correção |
|---|---|---|
| 9 | `/register` público permitia criar **diretor** | Só `aluno`/`professor`; demais via diretor |
| 10 | Chamado anônimo vazava `autor_perfil`; `to_dict` quebrava se autor fosse `None` | Oculta id/nome/perfil quando anônimo; `None`-safe |
| 11 | Qualquer aluno podia **responder qualquer chamado** e ver qualquer chamado pelo id | `pode_ver` / `pode_gerenciar` por perfil e área |
| 12 | Canal privado sem verificação; conversa lida por quem não participava | `perfil_pode_acessar`, `envolve` |
| 13 | Marcar notificação **alheia** como lida | Checagem de `usuario_id` |
| 14 | `criar_usuario` com senha padrão `mudar123`; `atualizar_usuario` fazia `setattr` sem validar; e-mail duplicado não checado no PUT | Senha obrigatória (≥ 6), validação campo a campo, e-mail único |
| 15 | `innerHTML` com dados do usuário **sem escape** (XSS) em todas as tabelas/chats | `escaparHtml()` em tudo |
| 16 | Chave do Firebase exposta no repositório | Arquivo removido |
| 17 | `DELETE /usuarios` apagava de verdade → violava FK (500) e perdia histórico | *Soft delete* (`ativo=False`); diretor não pode se desativar |

### Qualidade / manutenção
| # | Problema | Correção |
|---|---|---|
| 18 | CORS configurado **3 vezes** (extensão + `before_request` + `after_request`) | Só `Flask-CORS`, em `/api/*`, origens configuráveis |
| 19 | Erros 500 e do JWT em HTML/inglês | Handlers globais → sempre JSON em português |
| 20 | `datetime.utcnow()` deprecado; `Query.get()` legado | `datetime.now(timezone.utc)`; `db.session.get` / `db.get_or_404` |
| 21 | `flask-cors` duplicado no `requirements.txt`; sem gunicorn | Limpo, `gunicorn` + `Procfile` |
| 22 | `seed.py` sempre fazia `drop_all()` | Idempotente; `--reset` opcional |
| 23 | Áreas do seed (Elétrica, Segurança, TI) não batiam com as categorias do formulário | Áreas alinhadas ao mapeamento |
| 24 | `window.logout` redefinido em 5 arquivos (com e sem `confirm`) | Um só |
| 25 | Menu "Início" fixo como `active` em todas as páginas; `onclick="mostrarView()"` para função inexistente | Ativo pela URL; atributo removido |
| 26 | Sininho com ícone **e** emoji 🔔; texto "Sair" dentro de `<i>`; avatar sem `id` em algumas páginas | Header único gerado de um template |
| 27 | Dica do login `diretora@` (conta é `diretor@`); erro via `alert` em vez do `#login-erro` | Corrigido |
| 28 | Gráficos com cores fixas de tema escuro (borda preta no claro) | Cores lidas das variáveis CSS; redesenho no `temaAlterado` |
| 29 | Barras do dashboard com categorias/percentuais fixos no HTML; legenda de status em gráfico de categoria | Dinâmicas a partir de `/estatisticas` |
| 30 | `configuracoes.js` com dois `DOMContentLoaded`, nome fixo "Maria Oliveira", gravava só no localStorage | Reescrito contra a API |
| 31 | Formulário de ocorrência deixava o usuário escolher "Status inicial: Resolvido" | Campo removido; status só pela gestão |
| 32 | `alert()` em toda ação | `aviso()` |
| 33 | Datas: front esperava `c.data` (inexistente) | `formatarData(c.criado_em)` |
| 34 | Chat usava `canalAtualId = "geral"` fixo; nomes de usuário digitados no cliente | Ids reais; autor vem do token no servidor |

### Funcionalidades novas
* `/api/chamados/estatisticas`, `/api/usuarios/contatos`, `/api/notificacoes/nao-lidas`,
  `ler-todas`, `PUT /api/auth/me`, `PUT /api/auth/me/senha`, `/api/configuracoes`.
* Sininho funcional com painel e clique → abre o chamado.
* Filtros na API (`status`, `categoria`, `prioridade`, `busca`, `limite`).
* Imagem anexa persistida e exibida no detalhe.
* Contador de não lidas nas conversas; polling incremental (`?depois=`).
* Menu e botões escondidos por perfil; página de usuários bloqueia não-diretor.
* Notificação ao autor quando recebe resposta.

### Versão 3 — Firestore + Configurações funcionais
| O que | Como |
|---|---|
| Banco trocado de SQLite/SQLAlchemy para **Cloud Firestore** | `firestore_db.py` + `repo.py`; rotas reescritas sobre o repositório; respostas e mensagens reorganizadas (embutidas / subcoleções) |
| Modo em memória para desenvolver sem credenciais | `FIRESTORE_MOCK=1` (ou automático sem credenciais) |
| Preferências por usuário salvas no banco | `usuarios.preferencias`; `GET/PUT /api/auth/me/preferencias` |
| Notificações **realmente** ligadas/desligadas | `notificacoes.py` consulta a preferência antes de gravar |
| Idioma e fuso horário aplicados | `formatarData/formatarHora` usam `toLocaleString(idioma, {timeZone})` |
| Tema persistido na conta | aplicado ao logar e ao revalidar `/me` |
| Formato de exportação | botão **Exportar** em Relatórios (CSV com BOM/`;` para o Excel em português, ou impressão/PDF) |
| Removidos da tela | "Autenticação em duas etapas" e "Tempo de sessão inativa" (não tinham back-end); "Resumo diário por e-mail" trocado por notificações que existem no sistema |

### Como foi validado
* Back-end: ~45 cenários via `curl` (login, permissões por perfil, roteamento/notificações,
  chat, DMs, CRUD de usuários, configurações, erros 400/401/403/404/405/409).
* Front-end: teste automatizado (jsdom) abrindo **todas as páginas** contra a API real (Firestore
  em memória) como diretor e como aluno — 75 verificações (render, filtros, criação de chamado
  pela UI, envio de mensagem, criação de usuário, ocultação por perfil, redirecionamentos,
  preferências persistidas, fuso aplicado nas horas, tema, exportação CSV).

---

## 12. Próximos passos sugeridos

1. **Índices do Firestore**: se o volume crescer, crie índices compostos (área + data, autor +
   data) e mova a ordenação de `repo.listar()` para a própria query.
2. **Imagens**: base64 no documento funciona para o TCC (limite ~650 KB); o ideal é o
   **Firebase Storage** guardando o arquivo e o documento só com a URL.
3. **Paginação** em `/api/chamados` (cursor do Firestore) quando passar de algumas centenas.
4. **Testes no repositório** (`pytest` + `app.test_client()` com `FIRESTORE_MOCK=1`).
5. **Refresh token** para não deslogar a cada 8 h.
6. **E-mail** (SMTP ou Firebase Extensions) para reativar "resumo diário" e uma futura 2FA.
