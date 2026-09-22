/* ============================================================================
   api.js — Núcleo compartilhado do front-end SchoolFix.

   Inclua este arquivo em TODAS as páginas, ANTES dos scripts da página.
   Ele substitui os antigos api-config.js, auth.js, auth-header.js e script.js
   (que se sobrepunham e usavam chaves/URLs diferentes entre si).

   O que ele faz:
     1. Descobre a URL da API (local ou Render).
     2. Guarda/recupera token e usuário no localStorage (UMA chave para cada).
     3. chamarApi(): centraliza todas as chamadas HTTP (token, JSON, erros, 401).
     4. Helpers de interface: escaparHtml, datas, etiquetas, avisos.
     5. Ao carregar a página: exige login, preenche header, marca menu ativo,
        esconde itens que o perfil não pode ver e carrega o sininho.
   ========================================================================== */

// ---------------------------------------------------------------------------
// 1. URL da API
// ---------------------------------------------------------------------------
// Abrindo o site localmente (Live Server, file://) → Flask local.
// Publicado (Netlify, GitHub Pages...) → API_PRODUCAO abaixo.
// ►► Depois de criar o serviço no Render, cole aqui a URL dele (sem barra no final).
const API_PRODUCAO = "https://schoolfix-api.onrender.com";
// Para forçar outra URL sem editar o código: localStorage.setItem("schoolfix_api", "http://...")
const API_BASE_URL = (() => {
  const forcada = localStorage.getItem("schoolfix_api");
  if (forcada) return forcada.replace(/\/$/, "");
  const h = window.location.hostname;
  const local = h === "localhost" || h === "127.0.0.1" || h === "" || h.startsWith("192.168.");
  return local ? "http://127.0.0.1:5000" : API_PRODUCAO;
})();

// ---------------------------------------------------------------------------
// 2. Sessão (token + usuário)
// ---------------------------------------------------------------------------
const CHAVE_TOKEN = "schoolfix_token";
const CHAVE_USUARIO = "schoolfix_usuario";

function obterToken() { return localStorage.getItem(CHAVE_TOKEN); }
function salvarToken(t) { localStorage.setItem(CHAVE_TOKEN, t); }
function obterUsuario() {
  try { return JSON.parse(localStorage.getItem(CHAVE_USUARIO) || "null"); }
  catch { return null; }
}
function salvarUsuario(u) { localStorage.setItem(CHAVE_USUARIO, JSON.stringify(u)); }

function logout(perguntar = true) {
  if (perguntar && !confirm("Deseja realmente sair da sua conta?")) return;
  localStorage.removeItem(CHAVE_TOKEN);
  localStorage.removeItem(CHAVE_USUARIO);
  window.location.href = "login.html";
}

/** Redireciona para o login se não houver sessão. Retorna true se está logado. */
function exigirLogin() {
  if (!obterToken() || !obterUsuario()) {
    window.location.replace("login.html");
    return false;
  }
  return true;
}

// ---------------------------------------------------------------------------
// 3. Cliente HTTP
// ---------------------------------------------------------------------------
/**
 * chamarApi("/api/chamados")                         → GET
 * chamarApi("/api/chamados", { method: "POST", body: {...} })  (body pode ser objeto)
 *
 * - Adiciona Authorization: Bearer <token> automaticamente.
 * - 401 (token expirado/inválido) → faz logout.
 * - Erro HTTP → lança Error com a mensagem `erro` que o Flask devolveu.
 * - 204 → retorna null.
 */
async function chamarApi(path, options = {}) {
  const headers = { Accept: "application/json", ...(options.headers || {}) };
  let body = options.body;
  if (body && typeof body === "object" && !(body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(body);
  }
  const token = obterToken();
  if (token) headers.Authorization = "Bearer " + token;

  let res;
  try {
    res = await fetch(API_BASE_URL + path, { ...options, headers, body });
  } catch {
    throw new Error("Não foi possível conectar ao servidor. Verifique se o back-end está rodando.");
  }

  if (res.status === 401) {
    if (!path.startsWith("/api/auth/login")) logout(false);
    const e = await res.json().catch(() => ({}));
    throw new Error(e.erro || "Sessão expirada.");
  }
  if (res.status === 204) return null;

  const dados = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(dados.erro || `Erro ${res.status} na requisição.`);
  return dados;
}

// ---------------------------------------------------------------------------
// 4. Helpers de interface
// ---------------------------------------------------------------------------
/** Evita XSS: todo texto vindo do usuário passa por aqui antes do innerHTML. */
function escaparHtml(valor) {
  return String(valor ?? "")
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}

// --- Preferências do usuário (salvas no Firestore em usuarios/{id}.preferencias) ---
// idioma e fuso_horario são usados por formatarData/formatarHora; tema é aplicado ao entrar;
// formato_exportacao alimenta o botão "Exportar" em Relatórios.
const PREFERENCIAS_PADRAO = {
  notificacoes: { chamados_urgentes: true, status_chamados: true, respostas: true, mensagens_diretas: true },
  idioma: "pt-BR", fuso_horario: "America/Sao_Paulo", formato_exportacao: "csv", tema: "claro",
};

function obterPreferencias() {
  const p = obterUsuario()?.preferencias || {};
  return { ...PREFERENCIAS_PADRAO, ...p, notificacoes: { ...PREFERENCIAS_PADRAO.notificacoes, ...(p.notificacoes || {}) } };
}

/** Envia só o que mudou; a API mescla e devolve as preferências completas. */
async function salvarPreferencias(parcial) {
  const prefs = await chamarApi("/api/auth/me/preferencias", { method: "PUT", body: parcial });
  const u = obterUsuario();
  if (u) salvarUsuario({ ...u, preferencias: prefs });
  aplicarTemaDasPreferencias(prefs);
  return prefs;
}

function aplicarTemaDasPreferencias(prefs) {
  if (typeof window.alternarTema === "function" && prefs?.tema) window.alternarTema(prefs.tema === "escuro");
}

function formatarData(iso, comHora = false) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (isNaN(d)) return "—";
  const { idioma, fuso_horario } = obterPreferencias();
  const opcoes = { day: "2-digit", month: "2-digit", year: "numeric", timeZone: fuso_horario };
  if (comHora) Object.assign(opcoes, { hour: "2-digit", minute: "2-digit" });
  try { return d.toLocaleString(idioma, opcoes); } catch { return d.toLocaleString("pt-BR", opcoes); }
}

function formatarHora(iso) {
  const d = new Date(iso);
  if (isNaN(d)) return "";
  const { idioma, fuso_horario } = obterPreferencias();
  return d.toLocaleTimeString(idioma, { hour: "2-digit", minute: "2-digit", timeZone: fuso_horario });
}

const ROTULO_STATUS = { pendente: "Pendente", em_analise: "Em Análise", resolvido: "Resolvido" };
const ROTULO_PRIORIDADE = { baixa: "Baixa", media: "Média", alta: "Alta", urgente: "Urgente" };
const ROTULO_PERFIL = { aluno: "Aluno", professor: "Professor", gestor: "Gestor", coordenador: "Coordenador", diretor: "Diretor" };

function etiquetaStatus(status) {
  const s = status || "pendente";
  const classe = { pendente: "etiqueta-pendente", em_analise: "etiqueta-analise", resolvido: "etiqueta-resolvido" }[s] || "etiqueta-pendente";
  return `<span class="etiqueta ${classe}">${ROTULO_STATUS[s] || escaparHtml(s)}</span>`;
}

function etiquetaPrioridade(p) {
  const prio = p || "media";
  return `<span class="prioridade prioridade-${prio}">${ROTULO_PRIORIDADE[prio] || escaparHtml(prio)}</span>`;
}

function rotuloPerfil(p) { return ROTULO_PERFIL[p] || (p ? p.charAt(0).toUpperCase() + p.slice(1) : "—"); }

/** Aviso flutuante no canto (substitui os alert()). tipo: sucesso | erro | info */
function aviso(mensagem, tipo = "info", ms = 3200) {
  let area = document.getElementById("avisos-area");
  if (!area) {
    area = document.createElement("div");
    area.id = "avisos-area";
    document.body.appendChild(area);
  }
  const el = document.createElement("div");
  el.className = `aviso aviso-${tipo}`;
  el.textContent = mensagem;
  area.appendChild(el);
  setTimeout(() => el.classList.add("visivel"), 10);
  setTimeout(() => { el.classList.remove("visivel"); setTimeout(() => el.remove(), 300); }, ms);
}

/** Estado de carregamento/vazio dentro de um <tbody>. */
function linhaVazia(colunas, texto) {
  return `<tr><td colspan="${colunas}" class="celula-vazia">${escaparHtml(texto)}</td></tr>`;
}

// ---------------------------------------------------------------------------
// 5. Layout comum (header, sidebar, notificações)
// ---------------------------------------------------------------------------
const PAGINAS_POR_PERFIL = {
  // Página → perfis que podem vê-la no menu (ausente = todos)
  "usuarios.html": ["diretor"],
  "relatorios.html": ["diretor", "coordenador", "gestor"],
};

function preencherHeader() {
  const u = obterUsuario();
  if (!u) return;
  const nome = u.nome || u.email || "Usuário";
  const set = (id, txt) => { const el = document.getElementById(id); if (el) el.textContent = txt; };
  set("cabecalho-nome", nome);
  set("cabecalho-cargo", rotuloPerfil(u.perfil));
  set("cabecalho-avatar", nome.charAt(0).toUpperCase());
  set("saudacao", `Olá, ${nome.split(" ")[0]}!`);
}

function ajustarSidebar() {
  const atual = window.location.pathname.split("/").pop() || "index.html";
  const perfil = obterUsuario()?.perfil;
  document.querySelectorAll(".barra-lateral .menu-item").forEach((link) => {
    const href = (link.getAttribute("href") || "").split("/").pop();
    link.classList.toggle("ativo", href === atual);
    const permitidos = PAGINAS_POR_PERFIL[href];
    if (permitidos && !permitidos.includes(perfil)) link.style.display = "none";
  });
}

/** Mostra o nome da escola (vindo das configurações) no header. */
async function carregarNomeEscola() {
  const el = document.getElementById("cabecalho-escola");
  if (!el) return;
  try {
    const cfg = await chamarApi("/api/configuracoes");
    if (cfg.nome_escola) el.textContent = cfg.nome_escola;
  } catch { /* mantém o texto padrão do HTML */ }
}

// --- Sininho -------------------------------------------------------------
async function atualizarBadgeNotificacoes() {
  const contador = document.getElementById("notificacoes-contador");
  if (!contador) return;
  try {
    const { total } = await chamarApi("/api/notificacoes/nao-lidas");
    contador.textContent = total > 99 ? "99+" : total;
    contador.style.display = total > 0 ? "inline-flex" : "none";
  } catch { /* silencioso */ }
}

async function abrirNotificacoes() {
  const painel = document.getElementById("notificacoes-painel");
  if (!painel) return;
  const aberto = painel.style.display === "block";
  painel.style.display = aberto ? "none" : "block";
  if (aberto) return;

  painel.innerHTML = '<div class="notificacoes-vazio">Carregando...</div>';
  try {
    const lista = await chamarApi("/api/notificacoes");
    if (!lista.length) {
      painel.innerHTML = '<div class="notificacoes-vazio">Nenhuma notificação.</div>';
      return;
    }
    painel.innerHTML = `
      <div class="notificacoes-topo">
        <strong>Notificações</strong>
        <button type="button" class="link-acao" id="notificacoes-ler-todas">Marcar todas como lidas</button>
      </div>
      ${lista.map((n) => `
        <div class="notificacao ${n.lida ? "" : "nao-lida"}" data-id="${n.id}" data-chamado="${n.chamado_id || ""}">
          <span class="notificacao-titulo">${escaparHtml(n.titulo)}</span>
          <span class="notificacao-data">${formatarData(n.criado_em, true)}</span>
        </div>`).join("")}`;

    painel.querySelector("#notificacoes-ler-todas").onclick = async () => {
      await chamarApi("/api/notificacoes/ler-todas", { method: "PUT" });
      painel.querySelectorAll(".nao-lida").forEach((el) => el.classList.remove("nao-lida"));
      atualizarBadgeNotificacoes();
    };
    painel.querySelectorAll(".notificacao").forEach((item) => {
      item.onclick = async () => {
        if (item.classList.contains("nao-lida")) {
          await chamarApi(`/api/notificacoes/${item.dataset.id}/lida`, { method: "PUT" }).catch(() => {});
          item.classList.remove("nao-lida");
          atualizarBadgeNotificacoes();
        }
        if (item.dataset.chamado) window.location.href = `reclamacoes.html?id=${item.dataset.chamado}`;
      };
    });
  } catch (e) {
    painel.innerHTML = `<div class="notificacoes-vazio">${escaparHtml(e.message)}</div>`;
  }
}

function configurarNotificacoes() {
  const btn = document.getElementById("notificacoes-botao");
  if (!btn) return;
  btn.addEventListener("click", (e) => { e.stopPropagation(); abrirNotificacoes(); });
  document.addEventListener("click", (e) => {
    const painel = document.getElementById("notificacoes-painel");
    if (painel && !painel.contains(e.target)) painel.style.display = "none";
  });
  atualizarBadgeNotificacoes();
  setInterval(atualizarBadgeNotificacoes, 30000);
}

// --- Inicialização comum ---------------------------------------------------
document.addEventListener("DOMContentLoaded", () => {
  // Páginas públicas (login) marcam <body data-publica="true">
  if (document.body.dataset.publica === "true") return;
  if (!exigirLogin()) return;

  preencherHeader();
  ajustarSidebar();
  configurarNotificacoes();
  carregarNomeEscola();
  aplicarTemaDasPreferencias(obterPreferencias());

  // Revalida o token em segundo plano e atualiza dados/preferências do usuário
  chamarApi("/api/auth/me").then((u) => {
    salvarUsuario(u);
    preencherHeader();
    aplicarTemaDasPreferencias(u.preferencias);
  }).catch(() => {});
});

// Expõe no window para os atributos onclick="" do HTML
Object.assign(window, {
  API_BASE_URL, obterToken, salvarToken, obterUsuario, salvarUsuario, logout, exigirLogin, chamarApi,
  escaparHtml, formatarData, formatarHora, etiquetaStatus, etiquetaPrioridade, rotuloPerfil, aviso, linhaVazia,
  obterPreferencias, salvarPreferencias, PREFERENCIAS_PADRAO,
  ROTULO_STATUS, ROTULO_PRIORIDADE, ROTULO_PERFIL,
});
