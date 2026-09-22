# SchoolFix — Front-end

Site estático (HTML + CSS + JS puro) que consome a API Flask.
Documentação completa em [`../DOCUMENTACAO.md`](../DOCUMENTACAO.md).

## Rodar

1. Suba o back-end (`python run.py` na pasta `backend`).
2. Abra esta pasta no VS Code → **Live Server** → `login.html`.

A URL da API é detectada em `js/api.js`: `localhost/127.0.0.1` → `http://127.0.0.1:5000`;
publicado → Render. Para forçar outra: `localStorage.setItem("schoolfix_api", "http://...")`.

## Arquivos

```
js/api.js              núcleo: URL, token, chamarApi, preferências (idioma/fuso/tema), cabeçalho, menu, notificações
js/tema.js             modo escuro
js/<pagina>.js         lógica de cada tela (inicio, reclamacoes, nova-ocorrencia, chat,
                       mensagens, relatorios, usuarios, configuracoes, login)
style.css              design tokens + tema escuro + componentes
*.html                 páginas (layout comum de sidebar/header)
```

Ordem dos scripts em cada página: `tema.js` (head) → `api.js` → script da página.
