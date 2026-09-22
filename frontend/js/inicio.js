/* inicio.js — Dashboard (index.html).
   Usa /api/chamados/estatisticas para os cards e barras e
   /api/chamados?limite=5 para a tabela de recentes. */

const CORES_CATEGORIA = ["--danger", "--info", "--warning", "--success", "--primary", "--navy"];

document.addEventListener("DOMContentLoaded", carregarDashboard);

async function carregarDashboard() {
  try {
    const [stats, recentes] = await Promise.all([
      chamarApi("/api/chamados/estatisticas"),
      chamarApi("/api/chamados?limite=5"),
    ]);
    renderizarKpis(stats);
    renderizarRecentes(recentes);
    renderizarCategorias(stats.por_categoria, stats.total);
  } catch (e) {
    aviso(e.message, "erro");
    document.getElementById("tabela-recentes").innerHTML = linhaVazia(4, "Erro ao carregar dados.");
  }
}

function renderizarKpis(s) {
  const set = (id, v) => { const el = document.getElementById(id); if (el) el.textContent = v; };
  set("indicador-total", s.total);
  set("indicador-pendentes", s.por_status.pendente);
  set("indicador-analise", s.por_status.em_analise);
  set("indicador-resolvidas", s.por_status.resolvido);
}

function renderizarRecentes(lista) {
  const tbody = document.getElementById("tabela-recentes");
  if (!lista.length) { tbody.innerHTML = linhaVazia(4, "Nenhuma ocorrência registrada ainda."); return; }
  tbody.innerHTML = lista.map((c) => `
    <tr class="linha-clicavel" onclick="location.href='reclamacoes.html?id=${c.id}'">
      <td><strong>${escaparHtml(c.titulo)}</strong></td>
      <td>${escaparHtml(c.categoria)}</td>
      <td>${etiquetaStatus(c.status)}</td>
      <td>${formatarData(c.criado_em)}</td>
    </tr>`).join("");
}

function renderizarCategorias(porCategoria, total) {
  const box = document.getElementById("mapa-categorias");
  if (!box) return;
  const entradas = Object.entries(porCategoria || {});
  if (!entradas.length) { box.innerHTML = '<p class="celula-vazia">Sem dados.</p>'; return; }

  box.innerHTML = entradas.map(([cat, qtd], i) => {
    const pct = total ? Math.round((qtd / total) * 100) : 0;
    const cor = `var(${CORES_CATEGORIA[i % CORES_CATEGORIA.length]})`;
    return `
      <div class="barra-linha">
        <div class="barra-rotulo">
          <span>${escaparHtml(cat)}</span>
          <span class="contagem">${qtd} ${qtd === 1 ? "ocorrência" : "ocorrências"} (${pct}%)</span>
        </div>
        <div class="barra-trilho"><div class="barra-preenchimento" style="width:${pct}%;background:${cor}"></div></div>
      </div>`;
  }).join("");
}
