/* reclamacoes.js — Lista de chamados + painel de detalhes.

   GET  /api/chamados                 (lista; o Flask já filtra pelo perfil)
   GET  /api/chamados/<id>            (detalhe com respostas e imagem)
   PUT  /api/chamados/<id>/status     (gestão)
   POST /api/chamados/<id>/respostas  (gestão)

   Filtro por status e busca são feitos no navegador sobre a lista carregada
   (a lista é pequena; evita uma requisição a cada tecla). */

let lista = [];
let selecionadoId = null;
let filtroStatus = "";
let chartStatus = null;

const PERFIS_GESTAO = ["gestor", "coordenador", "diretor"];

document.addEventListener("DOMContentLoaded", async () => {
  configurarFiltros();
  configurarAcoesDetalhe();
  document.addEventListener("temaAlterado", desenharGrafico);
  await carregarLista();

  // Veio de uma notificação / dashboard com ?id=... → abre direto
  const id = new URLSearchParams(location.search).get("id");
  if (id) abrirDetalhes(id);
});

// ---------------------------------------------------------------------------
async function carregarLista() {
  const tbody = document.getElementById("tabela-reclamacoes");
  try {
    lista = await chamarApi("/api/chamados");
    renderizarTabela();
    desenharGrafico();
  } catch (e) {
    tbody.innerHTML = linhaVazia(7, e.message);
  }
}

function renderizarTabela() {
  const tbody = document.getElementById("tabela-reclamacoes");
  const contagem = document.getElementById("contagem-reclamacoes");
  const termo = (document.getElementById("busca-reclamacoes").value || "").toLowerCase();

  const filtradas = lista.filter((c) => {
    const okStatus = !filtroStatus || c.status === filtroStatus;
    const texto = `${c.titulo} ${c.autor_nome || ""} ${c.protocolo} ${c.categoria}`.toLowerCase();
    return okStatus && texto.includes(termo);
  });

  contagem.textContent = `Exibindo ${filtradas.length} de ${lista.length} ocorrências`;
  if (!filtradas.length) { tbody.innerHTML = linhaVazia(7, "Nenhuma ocorrência encontrada."); return; }

  tbody.innerHTML = filtradas.map((c) => `
    <tr class="${c.id === selecionadoId ? "linha-selecionada" : ""}">
      <td><strong>${escaparHtml(c.titulo)}</strong><br><small class="texto-suave">#${c.protocolo}</small></td>
      <td>${escaparHtml(c.categoria)}</td>
      <td>${etiquetaPrioridade(c.prioridade)}</td>
      <td>${escaparHtml(c.autor_nome || "—")}</td>
      <td>${etiquetaStatus(c.status)}</td>
      <td>${formatarData(c.criado_em)}</td>
      <td style="text-align:center">
        <button type="button" class="botao-tabela botao-tabela-editar" onclick="abrirDetalhes('${c.id}')" title="Ver detalhes">
          <i class="ti ti-eye"></i> Ver
        </button>
      </td>
    </tr>`).join("");
}

function configurarFiltros() {
  document.getElementById("busca-reclamacoes").addEventListener("input", renderizarTabela);
  document.querySelectorAll("#filtros-status .filtro").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll("#filtros-status .filtro").forEach((b) => b.classList.remove("ativo"));
      btn.classList.add("ativo");
      filtroStatus = btn.dataset.status || "";
      renderizarTabela();
    });
  });
}

// ---------------------------------------------------------------------------
async function abrirDetalhes(id) {
  selecionadoId = id;
  renderizarTabela();

  const painel = document.getElementById("painel-detalhes");
  const vazio = document.getElementById("painel-vazio");
  painel.style.display = "block";
  vazio.style.display = "none";

  try {
    const c = await chamarApi(`/api/chamados/${id}`);
    const set = (elId, txt) => (document.getElementById(elId).textContent = txt);

    set("detalhe-protocolo", `Protocolo: #${c.protocolo}`);
    set("detalhe-titulo", c.titulo);
    set("detalhe-resumo", `Por ${c.autor_nome || "—"} • ${c.categoria} • Área: ${c.area || "—"} • ${formatarData(c.criado_em, true)}`);
    set("detalhe-descricao", c.descricao);
    document.getElementById("detalhe-prioridade").innerHTML = etiquetaPrioridade(c.prioridade);
    document.getElementById("detalhe-status").value = c.status;

    const img = document.getElementById("detalhe-imagem");
    img.style.display = c.imagem ? "block" : "none";
    if (c.imagem) img.src = c.imagem;

    renderizarRespostas(c.respostas);

    // Quem não é da gestão só lê
    const podeGerir = PERFIS_GESTAO.includes(obterUsuario()?.perfil);
    document.getElementById("area-gestao").style.display = podeGerir ? "block" : "none";
  } catch (e) {
    aviso(e.message, "erro");
  }
}

function renderizarRespostas(respostas) {
  const box = document.getElementById("lista-respostas");
  if (!respostas?.length) {
    box.innerHTML = '<p class="celula-vazia" style="padding:8px 0">Nenhum feedback enviado ainda.</p>';
    return;
  }
  box.innerHTML = respostas.map((r) => `
    <div class="resposta">
      <div class="resposta-info">
        <strong>${escaparHtml(r.autor_nome)} <span class="texto-suave">(${rotuloPerfil(r.autor_perfil)})</span></strong>
        <span>${formatarData(r.criado_em, true)}</span>
      </div>
      <p>${escaparHtml(r.texto)}</p>
    </div>`).join("");
}

function configurarAcoesDetalhe() {
  document.getElementById("botao-atualizar-status").addEventListener("click", async () => {
    if (!selecionadoId) return;
    const status = document.getElementById("detalhe-status").value;
    try {
      const atualizado = await chamarApi(`/api/chamados/${selecionadoId}/status`, { method: "PUT", body: { status } });
      const idx = lista.findIndex((c) => c.id === atualizado.id);
      if (idx >= 0) lista[idx] = atualizado;
      renderizarTabela();
      desenharGrafico();
      aviso("Status atualizado!", "sucesso");
    } catch (e) { aviso(e.message, "erro"); }
  });

  document.getElementById("botao-enviar-resposta").addEventListener("click", async () => {
    if (!selecionadoId) return;
    const ta = document.getElementById("texto-resposta");
    const texto = ta.value.trim();
    if (!texto) return aviso("Escreva a resposta antes de enviar.", "erro");
    try {
      await chamarApi(`/api/chamados/${selecionadoId}/respostas`, { method: "POST", body: { texto } });
      ta.value = "";
      aviso("Resposta enviada!", "sucesso");
      abrirDetalhes(selecionadoId);   // recarrega o histórico
    } catch (e) { aviso(e.message, "erro"); }
  });
}

// ---------------------------------------------------------------------------
function desenharGrafico() {
  const canvas = document.getElementById("grafico-status");
  if (!canvas || typeof Chart === "undefined") return;
  const cont = (s) => lista.filter((c) => c.status === s).length;
  const css = getComputedStyle(document.documentElement);
  const cor = (v) => css.getPropertyValue(v).trim();

  if (chartStatus) chartStatus.destroy();
  chartStatus = new Chart(canvas, {
    type: "doughnut",
    data: {
      labels: ["Pendente", "Em Análise", "Resolvido"],
      datasets: [{
        data: [cont("pendente"), cont("em_analise"), cont("resolvido")],
        backgroundColor: [cor("--danger"), cor("--warning"), cor("--success")],
        borderColor: cor("--bg-card"),
        borderWidth: 2,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: "65%",
      plugins: { legend: { position: "bottom", labels: { color: cor("--text-secondary"), font: { family: "Inter" } } } },
    },
  });
}

window.abrirDetalhes = abrirDetalhes;
