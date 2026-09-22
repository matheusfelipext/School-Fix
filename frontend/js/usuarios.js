/* usuarios.js — CRUD de usuários (exclusivo do diretor).
   GET/POST /api/usuarios, PUT/DELETE /api/usuarios/<id>, GET /api/areas */

let usuarios = [];
let areas = [];

document.addEventListener("DOMContentLoaded", async () => {
  if (obterUsuario()?.perfil !== "diretor") {
    aviso("Área exclusiva da diretoria.", "erro");
    setTimeout(() => (location.href = "index.html"), 1200);
    return;
  }
  configurarFormulario();
  document.getElementById("busca-usuarios").addEventListener("input", renderizar);
  document.getElementById("usuario-perfil").addEventListener("change", alternarCampoArea);
  await carregarAreas();
  await carregarUsuarios();
});

async function carregarAreas() {
  try {
    areas = await chamarApi("/api/areas");
    document.getElementById("usuario-area").innerHTML =
      '<option value="">Selecione a área...</option>' +
      areas.map((a) => `<option value="${a.id}">${escaparHtml(a.nome)}</option>`).join("");
  } catch (e) { aviso(e.message, "erro"); }
}

async function carregarUsuarios() {
  const tbody = document.getElementById("tabela-usuarios");
  try {
    usuarios = await chamarApi("/api/usuarios");
    renderizar();
  } catch (e) { tbody.innerHTML = linhaVazia(6, e.message); }
}

function renderizar() {
  const tbody = document.getElementById("tabela-usuarios");
  const termo = document.getElementById("busca-usuarios").value.toLowerCase();
  const lista = usuarios.filter((u) =>
    `${u.nome} ${u.email} ${rotuloPerfil(u.perfil)} ${u.ativo ? "ativo" : "inativo"}`.toLowerCase().includes(termo));

  if (!lista.length) { tbody.innerHTML = linhaVazia(6, "Nenhum usuário encontrado."); return; }
  tbody.innerHTML = lista.map((u) => `
    <tr class="${u.ativo ? "" : "linha-inativa"}">
      <td><div class="avatar avatar-tabela">${escaparHtml(u.nome.charAt(0).toUpperCase())}</div></td>
      <td><strong>${escaparHtml(u.nome)}</strong>${u.area_nome ? `<br><small class="texto-suave">${escaparHtml(u.area_nome)}</small>` : ""}</td>
      <td>${escaparHtml(u.email)}</td>
      <td><span class="cargo-etiqueta cargo-${u.perfil === "diretor" ? "diretoria" : u.perfil}">${rotuloPerfil(u.perfil)}</span></td>
      <td><span class="etiqueta ${u.ativo ? "etiqueta-ativo" : "etiqueta-inativo"}">${u.ativo ? "Ativo" : "Inativo"}</span></td>
      <td style="text-align:center">
        <div class="acoes-tabela">
          <button type="button" class="botao-tabela botao-tabela-editar" onclick="editarUsuario('${u.id}')"><i class="ti ti-pencil"></i> Editar</button>
          ${u.ativo ? `<button type="button" class="botao-tabela botao-tabela-excluir" onclick="desativarUsuario('${u.id}')"><i class="ti ti-user-off"></i> Desativar</button>` : ""}
        </div>
      </td>
    </tr>`).join("");
}

function alternarCampoArea() {
  const gestor = document.getElementById("usuario-perfil").value === "gestor";
  document.getElementById("campo-area").style.display = gestor ? "block" : "none";
}

function configurarFormulario() {
  const form = document.getElementById("formulario-usuario");
  document.getElementById("botao-novo-usuario").onclick = () => {
    limparFormulario();
    document.getElementById("formulario-usuario-titulo").textContent = "Novo Usuário";
    document.getElementById("dica-senha").textContent = "Obrigatória (mín. 6 caracteres)";
    form.style.display = "block";
    document.getElementById("usuario-nome").focus();
  };
  document.getElementById("botao-cancelar-usuario").onclick = () => { form.style.display = "none"; limparFormulario(); };
  document.getElementById("botao-salvar-usuario").onclick = salvarUsuario;
}

async function salvarUsuario() {
  const id = document.getElementById("usuario-id").value;
  const dados = {
    nome: document.getElementById("usuario-nome").value.trim(),
    email: document.getElementById("usuario-email").value.trim(),
    perfil: document.getElementById("usuario-perfil").value,
    ativo: document.getElementById("usuario-status").value === "true",
    area_id: document.getElementById("usuario-area").value || null,
  };
  const senha = document.getElementById("usuario-senha").value;
  if (senha) dados.senha = senha;

  if (!dados.nome || !dados.email) return aviso("Preencha nome e e-mail.", "erro");
  if (!id && !senha) return aviso("Informe uma senha para o novo usuário.", "erro");

  try {
    if (id) {
      await chamarApi(`/api/usuarios/${id}`, { method: "PUT", body: dados });
      aviso("Usuário atualizado!", "sucesso");
    } else {
      await chamarApi("/api/usuarios", { method: "POST", body: dados });
      aviso("Usuário cadastrado!", "sucesso");
    }
    document.getElementById("formulario-usuario").style.display = "none";
    limparFormulario();
    carregarUsuarios();
  } catch (e) { aviso(e.message, "erro"); }
}

function limparFormulario() {
  ["usuario-id", "usuario-nome", "usuario-email", "usuario-senha"].forEach((id) => (document.getElementById(id).value = ""));
  document.getElementById("usuario-perfil").value = "aluno";
  document.getElementById("usuario-status").value = "true";
  document.getElementById("usuario-area").value = "";
  alternarCampoArea();
}

window.editarUsuario = (id) => {
  const u = usuarios.find((x) => x.id === id);
  if (!u) return;
  document.getElementById("usuario-id").value = u.id;
  document.getElementById("usuario-nome").value = u.nome;
  document.getElementById("usuario-email").value = u.email;
  document.getElementById("usuario-perfil").value = u.perfil;
  document.getElementById("usuario-status").value = String(u.ativo);
  document.getElementById("usuario-area").value = u.area_id || "";
  document.getElementById("usuario-senha").value = "";
  document.getElementById("dica-senha").textContent = "Deixe em branco para não alterar";
  document.getElementById("formulario-usuario-titulo").textContent = "Editar Usuário";
  alternarCampoArea();
  document.getElementById("formulario-usuario").style.display = "block";
  window.scrollTo({ top: 0, behavior: "smooth" });
};

window.desativarUsuario = async (id) => {
  if (!confirm("Desativar este usuário? Ele não conseguirá mais entrar, mas o histórico é mantido.")) return;
  try {
    await chamarApi(`/api/usuarios/${id}`, { method: "DELETE" });
    aviso("Usuário desativado.", "sucesso");
    carregarUsuarios();
  } catch (e) { aviso(e.message, "erro"); }
};
