// Configuração compartilhada da URL base da API.
// Ordem de resolução (do mais específico para o mais genérico):
//   1. localStorage["matchhelp_api"]   → override manual via DevTools
//   2. <meta name="matchhelp-api">     → injetado pelo backend ou build
//   3. window.location.origin          → mesma origem da página (ideal: serve o HTML pelo FastAPI)
//   4. Fallback hardcoded para a VPS   → garantia de demo mesmo abrindo o HTML local
(function () {
  const FALLBACK_API = "http://192.241.151.209:8000";

  function resolveBase() {
    try {
      const stored = localStorage.getItem("matchhelp_api");
      if (stored && stored.trim()) return stored.trim().replace(/\/+$/, "");
    } catch (_) {
      /* localStorage indisponível (file://) — segue o fluxo */
    }

    const meta = document.querySelector('meta[name="matchhelp-api"]');
    if (meta && meta.content && meta.content.trim()) {
      return meta.content.trim().replace(/\/+$/, "");
    }

    if (window.location && window.location.origin && window.location.origin.startsWith("http")) {
      return window.location.origin.replace(/\/+$/, "");
    }

    return FALLBACK_API;
  }

  window.MATCHHELP_API = resolveBase();

  window.matchhelpFetch = async function (path, options = {}) {
    const url = `${window.MATCHHELP_API}${path}`;
    const opts = {
      method: options.method || "GET",
      mode: "cors",
      headers: {
        Accept: "application/json",
        ...(options.body ? { "Content-Type": "application/json" } : {}),
        ...(options.headers || {}),
      },
      ...(options.body ? { body: JSON.stringify(options.body) } : {}),
    };
    const res = await fetch(url, opts);
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new Error(`HTTP ${res.status} — ${text || res.statusText}`);
    }
    return res.status === 204 ? null : res.json();
  };
})();
