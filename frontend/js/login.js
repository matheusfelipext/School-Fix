/* login.js — Tela de entrada.
   POST /api/auth/login → guarda token + usuário → vai para index.html */
document.addEventListener("DOMContentLoaded", () => {
  // Já logado? Pula o login.
  if (obterToken() && obterUsuario()) { window.location.replace("index.html"); return; }

  // Mostra a API em uso (para diagnosticar "está falando com o servidor errado?")
  const apiEl = document.getElementById("login-api");
  if (apiEl) apiEl.textContent = `API: ${API_BASE_URL}`;

  const form = document.getElementById("formulario-login");
  const erroEl = document.getElementById("login-erro");
  const btn = form.querySelector("button[type=submit]");

  const mostrarErro = (msg) => { erroEl.textContent = msg; erroEl.style.display = "block"; };

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    erroEl.style.display = "none";

    const email = document.getElementById("email").value.trim();
    const senha = document.getElementById("senha").value;
    if (!email || !senha) return mostrarErro("Preencha e-mail e senha.");

    btn.disabled = true;
    btn.textContent = "Entrando...";
    try {
      const dados = await chamarApi("/api/auth/login", { method: "POST", body: { email, senha } });
      salvarToken(dados.access_token);
      salvarUsuario(dados.usuario);
      if (dados.usuario.preferencias?.tema && window.alternarTema) window.alternarTema(dados.usuario.preferencias.tema === "escuro");
      window.location.href = "index.html";
    } catch (err) {
      mostrarErro(err.message);
    } finally {
      btn.disabled = false;
      btn.textContent = "Entrar";
    }
  });
});
