/* chat.js — Chat geral por canais.

   GET  /api/canais                               canais que meu perfil vê
   GET  /api/canais/<id>/mensagens?depois=<ISO>   novas desde a última consulta
   POST /api/canais/<id>/mensagens

   Não há WebSocket: usamos "polling" — a cada 4 s pedimos só as mensagens
   novas (parâmetro `depois`) e as acrescentamos no fim da conversa. */

let canalAtualId = null;
let ultimaMensagemEm = null;
let timerPolling = null;

document.addEventListener("DOMContentLoaded", () => {
  carregarCanais();
  configurarEnvio();
});

async function carregarCanais() {
  const box = document.getElementById("lista-canais");
  try {
    const canais = await chamarApi("/api/canais");
    if (!canais.length) { box.innerHTML = '<div class="notificacoes-vazio">Nenhum canal disponível.</div>'; return; }
    box.innerHTML = canais.map((c) => `
      <div class="canal" data-id="${c.id}" data-nome="${escaparHtml(c.nome)}" data-desc="${escaparHtml(c.descricao || "")}">
        <strong># ${escaparHtml(c.nome)} ${c.privado ? '<i class="ti ti-lock" title="Privado"></i>' : ""}</strong>
        <p>${escaparHtml(c.descricao || "")}</p>
      </div>`).join("");
    box.querySelectorAll(".canal").forEach((el) =>
      el.addEventListener("click", () => selecionarCanal(el.dataset.id, el.dataset.nome, el.dataset.desc)));
    selecionarCanal(canais[0].id, canais[0].nome, canais[0].descricao);
  } catch (e) {
    box.innerHTML = `<div class="notificacoes-vazio">${escaparHtml(e.message)}</div>`;
  }
}

function selecionarCanal(id, nome, descricao) {
  canalAtualId = id;
  ultimaMensagemEm = null;
  document.querySelectorAll(".canal").forEach((el) => el.classList.toggle("ativo", el.dataset.id === id));
  document.getElementById("canal-nome-atual").textContent = `# ${nome}`;
  document.getElementById("canal-descricao-atual").textContent = descricao || "";
  document.getElementById("chat-entrada-texto").disabled = false;
  document.getElementById("chat-enviar").disabled = false;
  document.getElementById("chat-mensagens").innerHTML = '<p class="celula-vazia">Carregando...</p>';

  clearInterval(timerPolling);
  buscarMensagens(true);
  timerPolling = setInterval(() => buscarMensagens(false), 4000);
}

async function buscarMensagens(inicial) {
  if (!canalAtualId) return;
  const box = document.getElementById("chat-mensagens");
  const canalNaHora = canalAtualId;
  try {
    const q = ultimaMensagemEm ? `?depois=${encodeURIComponent(ultimaMensagemEm)}` : "";
    const msgs = await chamarApi(`/api/canais/${canalNaHora}/mensagens${q}`);
    if (canalNaHora !== canalAtualId) return;   // usuário trocou de canal no meio

    if (inicial) box.innerHTML = msgs.length ? "" : '<p class="celula-vazia">Nenhuma mensagem neste canal ainda.</p>';
    if (msgs.length) {
      if (box.querySelector(".celula-vazia")) box.innerHTML = "";
      box.insertAdjacentHTML("beforeend", msgs.map(renderMensagem).join(""));
      ultimaMensagemEm = msgs[msgs.length - 1].criado_em;
      box.scrollTop = box.scrollHeight;
    }
  } catch (e) {
    if (inicial) box.innerHTML = `<p class="celula-vazia">${escaparHtml(e.message)}</p>`;
  }
}

function renderMensagem(m) {
  const minha = m.autor_id === obterUsuario()?.id;
  return `
    <div class="mensagem ${minha ? "mensagem-minha" : ""}">
      <div class="mensagem-topo">
        <strong>${escaparHtml(m.autor_nome)} <span class="texto-suave">· ${rotuloPerfil(m.autor_perfil)}</span></strong>
        <span>${formatarHora(m.criado_em)}</span>
      </div>
      <p>${escaparHtml(m.texto)}</p>
    </div>`;
}

function configurarEnvio() {
  const input = document.getElementById("chat-entrada-texto");
  const btn = document.getElementById("chat-enviar");

  const enviar = async () => {
    const texto = input.value.trim();
    if (!texto || !canalAtualId) return;
    input.value = "";
    try {
      await chamarApi(`/api/canais/${canalAtualId}/mensagens`, { method: "POST", body: { texto } });
      buscarMensagens(false);
    } catch (e) { aviso(e.message, "erro"); input.value = texto; }
  };

  btn.addEventListener("click", enviar);
  input.addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); enviar(); } });
}
