/* mensagens.js — Mensagens diretas (1:1).

   GET  /api/conversas                          minhas conversas
   POST /api/conversas {destinatario_id}        abre/reaproveita
   GET  /api/conversas/<id>/mensagens?depois=   novas (marca como lidas)
   POST /api/conversas/<id>/mensagens
   GET  /api/usuarios/contatos                  pessoas para iniciar conversa */

let conversaAtivaId = null;
let ultimaEm = null;
let timerMsgs = null;
let timerConversas = null;

document.addEventListener("DOMContentLoaded", () => {
  carregarConversas();
  configurarNovaConversa();
  configurarEnvio();
  timerConversas = setInterval(carregarConversas, 10000);
});

async function carregarConversas() {
  const box = document.getElementById("lista-conversas");
  try {
    const conversas = await chamarApi("/api/conversas");
    if (!conversas.length) { box.innerHTML = '<div class="notificacoes-vazio">Nenhuma conversa. Clique em + para iniciar.</div>'; return; }
    box.innerHTML = conversas.map((c) => `
      <div class="conversa ${c.id === conversaAtivaId ? "active" : ""}" data-id="${c.id}" data-nome="${escaparHtml(c.outro_nome)}" data-perfil="${c.outro_perfil}">
        <div class="conversa-topo">
          <strong>${escaparHtml(c.outro_nome)}</strong>
          ${c.nao_lidas ? `<span class="conversa-contador">${c.nao_lidas}</span>` : ""}
        </div>
        <p>${escaparHtml(c.ultima_mensagem || "Conversa iniciada")}</p>
      </div>`).join("");
    box.querySelectorAll(".conversa").forEach((el) =>
      el.addEventListener("click", () => abrirConversa(el.dataset.id, el.dataset.nome, el.dataset.perfil)));
  } catch (e) {
    box.innerHTML = `<div class="notificacoes-vazio">${escaparHtml(e.message)}</div>`;
  }
}

function abrirConversa(id, nome, perfil) {
  conversaAtivaId = id;
  ultimaEm = null;
  document.querySelectorAll(".conversa").forEach((el) => {
    el.classList.toggle("ativo", el.dataset.id === id);
    if (el.dataset.id === id) el.querySelector(".conversa-contador")?.remove();
  });
  document.getElementById("conversa-cabecalho").innerHTML =
    `<h3>${escaparHtml(nome)}</h3><p>${rotuloPerfil(perfil)} · Mensagem direta</p>`;
  document.getElementById("conversa-entrada-texto").disabled = false;
  document.getElementById("conversa-enviar").disabled = false;
  document.getElementById("conversa-mensagens").innerHTML = '<p class="celula-vazia">Carregando...</p>';

  clearInterval(timerMsgs);
  buscarMensagens(true);
  timerMsgs = setInterval(() => buscarMensagens(false), 4000);
}

async function buscarMensagens(inicial) {
  if (!conversaAtivaId) return;
  const box = document.getElementById("conversa-mensagens");
  const idNaHora = conversaAtivaId;
  try {
    const q = ultimaEm ? `?depois=${encodeURIComponent(ultimaEm)}` : "";
    const msgs = await chamarApi(`/api/conversas/${idNaHora}/mensagens${q}`);
    if (idNaHora !== conversaAtivaId) return;

    if (inicial) box.innerHTML = msgs.length ? "" : '<p class="celula-vazia">Inicie a conversa enviando uma mensagem.</p>';
    if (msgs.length) {
      if (box.querySelector(".celula-vazia")) box.innerHTML = "";
      const meuId = obterUsuario()?.id;
      box.insertAdjacentHTML("beforeend", msgs.map((m) => `
        <div class="mensagem ${m.autor_id === meuId ? "mensagem-minha" : ""}">
          <div class="mensagem-topo"><strong>${escaparHtml(m.autor_nome)}</strong><span>${formatarHora(m.criado_em)}</span></div>
          <p>${escaparHtml(m.texto)}</p>
        </div>`).join(""));
      ultimaEm = msgs[msgs.length - 1].criado_em;
      box.scrollTop = box.scrollHeight;
    }
  } catch (e) {
    if (inicial) box.innerHTML = `<p class="celula-vazia">${escaparHtml(e.message)}</p>`;
  }
}

function configurarEnvio() {
  const input = document.getElementById("conversa-entrada-texto");
  const btn = document.getElementById("conversa-enviar");
  const enviar = async () => {
    const texto = input.value.trim();
    if (!texto || !conversaAtivaId) return;
    input.value = "";
    try {
      await chamarApi(`/api/conversas/${conversaAtivaId}/mensagens`, { method: "POST", body: { texto } });
      buscarMensagens(false);
      carregarConversas();
    } catch (e) { aviso(e.message, "erro"); input.value = texto; }
  };
  btn.addEventListener("click", enviar);
  input.addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); enviar(); } });
}

function configurarNovaConversa() {
  const btnNova = document.getElementById("botao-nova-conversa");
  const painel = document.getElementById("painel-nova-conversa");
  const select = document.getElementById("seletor-novo-contato");
  const btnOk = document.getElementById("botao-confirmar-nova-conversa");

  btnNova.addEventListener("click", async () => {
    const abrir = painel.style.display === "none";
    painel.style.display = abrir ? "block" : "none";
    if (!abrir) return;
    select.innerHTML = "<option>Carregando...</option>";
    try {
      const contatos = await chamarApi("/api/usuarios/contatos");
      select.innerHTML = contatos.map((u) =>
        `<option value="${u.id}">${escaparHtml(u.nome)} (${rotuloPerfil(u.perfil)})</option>`).join("");
    } catch (e) { select.innerHTML = `<option>${escaparHtml(e.message)}</option>`; }
  });

  btnOk.addEventListener("click", async () => {
    const destinatario_id = select.value;
    if (!destinatario_id) return;
    try {
      const conv = await chamarApi("/api/conversas", { method: "POST", body: { destinatario_id } });
      painel.style.display = "none";
      await carregarConversas();
      abrirConversa(conv.id, conv.outro_nome, conv.outro_perfil);
    } catch (e) { aviso(e.message, "erro"); }
  });
}
