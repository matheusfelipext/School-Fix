/* tema.js — Modo claro/escuro.
   Carregado no <head> (antes do CSS renderizar) para não "piscar" branco.
   O CSS aplica as variáveis do tema escuro quando <html> tem a classe tema-escuro. */
(function aplicarTemaSalvo() {
  if (localStorage.getItem("schoolfix_theme") === "dark") {
    document.documentElement.classList.add("tema-escuro");
  }
})();

window.alternarTema = function (ativarEscuro) {
  const escuro = ativarEscuro ?? !document.documentElement.classList.contains("tema-escuro");
  document.documentElement.classList.toggle("tema-escuro", escuro);
  localStorage.setItem("schoolfix_theme", escuro ? "dark" : "light");
  // Avisa quem desenha gráficos (Chart.js) para trocar as cores
  document.dispatchEvent(new CustomEvent("temaAlterado", { detail: { escuro } }));
};

window.temaEscuro = () => document.documentElement.classList.contains("tema-escuro");
