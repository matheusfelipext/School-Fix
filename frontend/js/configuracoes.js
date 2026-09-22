/* configuracoes.js — Tela Configurações (tudo persistido na API/Firestore).

   Dados da instituição   GET/PUT /api/configuracoes           (só diretor edita)
   Meu perfil             PUT /api/auth/me                     (nome)
   Preferências e tema    PUT /api/auth/me/preferencias        (idioma, fuso, exportação, tema)
   Notificações           PUT /api/auth/me/preferencias        (notificacoes.{...})
   Alterar senha          PUT /api/auth/me/senha

   Cada interruptor/select salva no ato da mudança (sem botão "salvar"), com aviso de confirmação. */

const PERFIS_GESTAO = ["gestor", "coordenador", "diretor"];

document.addEventListener("DOMContentLoaded", async () => {
  const u = obterUsuario();
  const ehDiretor = u?.perfil === "diretor";

  // ---- Meu perfil ----------------------------------------------------------
  document.getElementById("perfil-nome").value = u?.nome || "";
  document.getElementById("perfil-email").value = u?.email || "";
  document.getElementById("perfil-cargo").value = rotuloPerfil(u?.perfil);

  document.getElementById("botao-salvar-perfil").onclick = async () => {
    const nome = document.getElementById("perfil-nome").value.trim();
    try {
      const atualizado = await chamarApi("/api/auth/me", { method: "PUT", body: { nome } });
      salvarUsuario(atualizado);
      document.getElementById("cabecalho-nome").textContent = atualizado.nome;
      document.getElementById("cabecalho-avatar").textContent = atualizado.nome.charAt(0).toUpperCase();
      aviso("Perfil atualizado!", "sucesso");
    } catch (e) { aviso(e.message, "erro"); }
  };

  // ---- Dados da instituição ------------------------------------------------
  const campos = { "instituicao-nome": "nome_escola", "instituicao-endereco": "endereco",
                   "instituicao-telefone": "telefone", "instituicao-email": "email_contato" };
  try {
    const cfg = await chamarApi("/api/configuracoes");
    for (const [id, chave] of Object.entries(campos)) {
      const el = document.getElementById(id);
      el.value = cfg[chave] || "";
      el.disabled = !ehDiretor;
    }
  } catch (e) { aviso(e.message, "erro"); }
  const btnInst = document.getElementById("botao-salvar-instituicao");
  btnInst.style.display = ehDiretor ? "" : "none";
  btnInst.onclick = async () => {
    const body = {};
    for (const [id, chave] of Object.entries(campos)) body[chave] = document.getElementById(id).value.trim();
    try {
      await chamarApi("/api/configuracoes", { method: "PUT", body });
      aviso("Dados da instituição salvos!", "sucesso");
      const h = document.getElementById("cabecalho-escola");
      if (h && body.nome_escola) h.textContent = body.nome_escola;
    } catch (e) { aviso(e.message, "erro"); }
  };

  // ---- Preferências e tema -------------------------------------------------
  const prefs = obterPreferencias();
  document.querySelectorAll("select[data-pref]").forEach((sel) => {
    sel.value = prefs[sel.dataset.pref];
    sel.addEventListener("change", async () => {
      try {
        await salvarPreferencias({ [sel.dataset.pref]: sel.value });
        aviso("Preferência salva.", "sucesso", 1600);
      } catch (e) { aviso(e.message, "erro"); sel.value = obterPreferencias()[sel.dataset.pref]; }
    });
  });

  const chkTema = document.getElementById("alternador-tema");
  chkTema.checked = prefs.tema === "escuro";
  chkTema.addEventListener("change", async () => {
    window.alternarTema(chkTema.checked);                       // aplica na hora
    try { await salvarPreferencias({ tema: chkTema.checked ? "escuro" : "claro" }); }
    catch (e) { aviso(e.message, "erro"); }
  });

  // ---- Notificações --------------------------------------------------------
  // "Reclamações urgentes" só faz sentido para quem recebe esse alerta (gestão)
  document.querySelectorAll("[data-somente-gestao]").forEach((el) => {
    if (!PERFIS_GESTAO.includes(u?.perfil)) el.style.display = "none";
  });
  document.querySelectorAll("input[data-notif]").forEach((chk) => {
    chk.checked = prefs.notificacoes[chk.dataset.notif] !== false;
    chk.addEventListener("change", async () => {
      try {
        await salvarPreferencias({ notificacoes: { [chk.dataset.notif]: chk.checked } });
        aviso(chk.checked ? "Notificação ativada." : "Notificação desativada.", "sucesso", 1600);
      } catch (e) { aviso(e.message, "erro"); chk.checked = !chk.checked; }
    });
  });

  // ---- Alterar senha -------------------------------------------------------
  document.getElementById("formulario-senha").addEventListener("submit", async (e) => {
    e.preventDefault();
    const senha_atual = document.getElementById("senha-atual").value;
    const nova_senha = document.getElementById("senha-nova").value;
    if (nova_senha !== document.getElementById("senha-confirma").value) return aviso("A confirmação não confere com a nova senha.", "erro");
    try {
      await chamarApi("/api/auth/me/senha", { method: "PUT", body: { senha_atual, nova_senha } });
      e.target.reset();
      aviso("Senha alterada com sucesso!", "sucesso");
    } catch (err) { aviso(err.message, "erro"); }
  });
});
