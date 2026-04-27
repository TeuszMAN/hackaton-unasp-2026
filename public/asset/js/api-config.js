// Configuração compartilhada da URL base da API.
// Pode ser sobrescrita em runtime via localStorage.setItem('matchhelp_api', 'https://...').
(function () {
  const DEFAULT_API = "https://coveting-economy-tingling.ngrok-free.dev";
  const stored = localStorage.getItem("matchhelp_api");
  window.MATCHHELP_API = (stored && stored.trim()) || DEFAULT_API;

  window.matchhelpFetch = async function (path, options = {}) {
    const url = `${window.MATCHHELP_API}${path}`;
    const opts = {
      method: options.method || "GET",
      mode: "cors",
      headers: {
        "ngrok-skip-browser-warning": "true",
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
