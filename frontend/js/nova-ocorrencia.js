/* nova-ocorrencia.js — Formulário de cadastro de chamado.
   POST /api/chamados com título, descrição, categoria, prioridade,
   anônimo e (opcional) imagem em base64. */

const TAMANHO_MAX_IMAGEM = 2 * 1024 * 1024; // 2 MB

document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("formulario-nova-ocorrencia");
  const inputImg = document.getElementById("ocorrencia-imagem");

  inputImg.addEventListener("change", previewImagem);
  form.addEventListener("submit", salvarOcorrencia);

  // Professor pode marcar "prioridade pedagógica"; para os demais o campo some
  const boxPedagogico = document.getElementById("campo-pedagogico");
  if (boxPedagogico && obterUsuario()?.perfil !== "professor") boxPedagogico.style.display = "none";
});

function previewImagem(e) {
  const file = e.target.files[0];
  const label = document.getElementById("arquivo-rotulo");
  const preview = document.getElementById("imagem-previa");
  const container = document.getElementById("previa-area");

  if (!file) { container.style.display = "none"; return; }
  if (file.size > TAMANHO_MAX_IMAGEM) {
    aviso("Imagem muito grande (máx. 2 MB).", "erro");
    e.target.value = "";
    return;
  }
  label.innerHTML = `<strong>Arquivo selecionado:</strong> ${escaparHtml(file.name)}`;
  const reader = new FileReader();
  reader.onload = () => { preview.src = reader.result; container.style.display = "block"; };
  reader.readAsDataURL(file);
}

function lerImagemBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

async function salvarOcorrencia(e) {
  e.preventDefault();
  const btn = e.target.querySelector("button[type=submit]");
  const file = document.getElementById("ocorrencia-imagem").files[0];

  const dados = {
    titulo: document.getElementById("ocorrencia-titulo").value.trim(),
    descricao: document.getElementById("ocorrencia-descricao").value.trim(),
    categoria: document.getElementById("categoria").value,
    prioridade: document.getElementById("prioridade").value,     // já em minúsculo (baixa/media/alta/urgente)
    anonimo: document.getElementById("ocorrencia-anonimo").checked,
    canal_prioridade_pedagogica: document.getElementById("ocorrencia-pedagogico")?.checked || false,
    imagem: file ? await lerImagemBase64(file) : null,
  };

  if (dados.titulo.length < 3) return aviso("Informe um título com pelo menos 3 caracteres.", "erro");
  if (dados.descricao.length < 10) return aviso("Descreva o problema com pelo menos 10 caracteres.", "erro");

  btn.disabled = true;
  try {
    const criado = await chamarApi("/api/chamados", { method: "POST", body: dados });
    aviso(`Ocorrência registrada! Protocolo #${criado.protocolo}`, "sucesso");
    setTimeout(() => (window.location.href = `reclamacoes.html?id=${criado.id}`), 900);
  } catch (err) {
    aviso(err.message, "erro");
    btn.disabled = false;
  }
}
