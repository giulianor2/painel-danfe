// Tema claro/escuro. A preferência fica salva no navegador; sem preferência, segue o sistema.
(function () {
  function temaAtual() {
    try {
      var salvo = localStorage.getItem("tema");
      if (salvo === "claro" || salvo === "escuro") return salvo;
    } catch (e) {}
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "escuro" : "claro";
  }
  function aplicar(tema) {
    document.documentElement.classList.toggle("dark", tema === "escuro");
    document.dispatchEvent(new CustomEvent("tema", { detail: tema }));
  }
  aplicar(temaAtual());
  window.alternarTema = function () {
    var novo = document.documentElement.classList.contains("dark") ? "claro" : "escuro";
    try { localStorage.setItem("tema", novo); } catch (e) {}
    aplicar(novo);
  };
})();
