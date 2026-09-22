/* relatorios.js — Gráficos e KPIs (Chart.js) a partir de /api/chamados/estatisticas.
   As cores são lidas das variáveis CSS para funcionar no tema claro e escuro. */

let chartPrioridade = null;
let chartCategoria = null;
let statsCache = null;

document.addEventListener("DOMContentLoaded", () => {
  carregarRelatorios();
  document.getElementById("botao-exportar")?.addEventListener("click", exportarRelatorio);
});
document.addEventListener("temaAlterado", () => statsCache && desenharGraficos(statsCache));

async function carregarRelatorios() {
  try {
    statsCache = await chamarApi("/api/chamados/estatisticas");
    preencherCards(statsCache);
    desenharGraficos(statsCache);
  } catch (e) {
    aviso(e.message, "erro");
  }
}

function preencherCards(s) {
  const set = (id, v) => { const el = document.getElementById(id); if (el) el.textContent = v; };
  set("grafico-total", s.total);
  set("estatistica-total", s.total);
  set("estatistica-taxa", `${s.taxa_resolucao}%`);
  set("estatistica-taxa-nota", `${s.por_status.resolvido} de ${s.total} resolvidos`);
  set("estatistica-categoria", s.categoria_mais_frequente || "—");
  const qtdCat = s.categoria_mais_frequente ? s.por_categoria[s.categoria_mais_frequente] : 0;
  set("estatistica-categoria-nota", qtdCat ? `${qtdCat} ocorrências nesta categoria` : "");
  set("estatistica-urgentes", s.urgentes_abertos);
}

function coresTema() {
  const css = getComputedStyle(document.documentElement);
  const v = (n) => css.getPropertyValue(n).trim();
  return {
    texto: v("--text-secondary"), grade: v("--border"), fundo: v("--bg-card"),
    paleta: [v("--success"), v("--warning"), v("--danger"), "#8b5cf6", v("--info"), v("--primary"), "#ec4899", "#06b6d4"],
  };
}

function desenharGraficos(s) {
  if (typeof Chart === "undefined") return;
  const cor = coresTema();
  const fonte = { family: "Inter", size: 12 };

  // --- Donut de prioridades ---
  const cvP = document.getElementById("grafico-prioridade");
  if (chartPrioridade) chartPrioridade.destroy();
  chartPrioridade = new Chart(cvP, {
    type: "doughnut",
    data: {
      labels: ["Baixa", "Média", "Alta", "Urgente"],
      datasets: [{
        data: [s.por_prioridade.baixa, s.por_prioridade.media, s.por_prioridade.alta, s.por_prioridade.urgente],
        backgroundColor: [cor.paleta[0], cor.paleta[1], cor.paleta[2], cor.paleta[3]],
        borderColor: cor.fundo, borderWidth: 2,
      }],
    },
    options: {
      responsive: true, maintainAspectRatio: false, cutout: "72%",
      plugins: { legend: { position: "bottom", labels: { color: cor.texto, padding: 14, font: fonte } } },
    },
  });

  // --- Barras por categoria ---
  const cvC = document.getElementById("grafico-categoria");
  if (chartCategoria) chartCategoria.destroy();
  const labels = Object.keys(s.por_categoria);
  chartCategoria = new Chart(cvC, {
    type: "bar",
    data: {
      labels: labels.length ? labels : ["Sem dados"],
      datasets: [{
        label: "Quantidade",
        data: labels.length ? Object.values(s.por_categoria) : [0],
        backgroundColor: labels.map((_, i) => cor.paleta[(i + 4) % cor.paleta.length]),
        borderRadius: 6, maxBarThickness: 38,
      }],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { display: false }, ticks: { color: cor.texto, font: fonte } },
        y: { beginAtZero: true, ticks: { stepSize: 1, color: cor.texto, font: fonte }, grid: { color: cor.grade } },
      },
    },
  });
}

// ---------------------------------------------------------------------------
// Exportação — usa a preferência "formato_exportacao" (Configurações)
//   csv → baixa um arquivo com todos os chamados visíveis
//   pdf → abre a impressão da página (o CSS @media print esconde menu/cabeçalho)
// ---------------------------------------------------------------------------
async function exportarRelatorio() {
  const formato = obterPreferencias().formato_exportacao;
  if (formato === "pdf") { window.print(); return; }
  try {
    const chamados = await chamarApi("/api/chamados");
    const colunas = ["protocolo", "titulo", "categoria", "area", "prioridade", "status", "autor_nome", "criado_em"];
    const escapar = (v) => `"${String(v ?? "").replace(/"/g, '""')}"`;
    const linhas = [colunas.join(";"), ...chamados.map((c) => colunas.map((k) =>
      escapar(k === "criado_em" ? formatarData(c[k], true) : k === "status" ? ROTULO_STATUS[c[k]] : k === "prioridade" ? ROTULO_PRIORIDADE[c[k]] : c[k])).join(";"))];
    const blob = new Blob(["\ufeff" + linhas.join("\r\n")], { type: "text/csv;charset=utf-8" });
    const a = Object.assign(document.createElement("a"), { href: URL.createObjectURL(blob), download: `schoolfix-chamados-${new Date().toISOString().slice(0, 10)}.csv` });
    document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(a.href);
    aviso(`${chamados.length} chamados exportados em CSV.`, "sucesso");
  } catch (e) { aviso(e.message, "erro"); }
}
