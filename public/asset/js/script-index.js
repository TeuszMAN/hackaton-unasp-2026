// URL base resolvida em api-config.js (window.MATCHHELP_API).
// Ordem: localStorage → <meta> → window.location.origin → fallback VPS.
const API_BASE_URL =
  (typeof window !== "undefined" && window.MATCHHELP_API) ||
  "http://192.241.151.209:8000";
document.getElementById("api-url-text").innerText = API_BASE_URL;

async function fetchDados() {
  const tableBody = document.getElementById("tabela-voluntarios");
  const icon = document.getElementById("refresh-icon");
  const banner = document.getElementById("error-banner");
  const debugText = document.getElementById("error-debug");
  const debugOrigin = document.getElementById("debug-origin");
  const badgeApi = document.getElementById("badge-api");
  const sDot = document.getElementById("status-dot");
  const sTxt = document.getElementById("status-text");

  icon.classList.add("animate-spin-fast");
  banner.classList.add("hidden");
  debugOrigin.innerText = window.location.origin;

  try {
    // Configuração comum para os fetches
    const fetchOptions = {
      method: "GET",
      mode: "cors",
      headers: {
        Accept: "application/json",
      },
    };

    // 1. Buscar Estatísticas (/api/v1/estatisticas)
    console.log("Buscando estatísticas...");
    const statsRes = await fetch(
      `${API_BASE_URL}/api/v1/estatisticas`,
      fetchOptions,
    );

    if (statsRes.ok) {
      const stats = await statsRes.json();
      document.getElementById("stat-total-voluntarios").innerText =
        stats.total_voluntarios || 0;
      document.getElementById("stat-necessidades-abertas").innerText =
        stats.necessidades_abertas || 0;
      document.getElementById("stat-vinculos-concluidos").innerText =
        stats.vinculos_concluidos || 0;
    }

    // 2. Buscar Voluntários (/api/v1/voluntarios)
    console.log("Buscando lista de voluntários...");
    const volRes = await fetch(
      `${API_BASE_URL}/api/v1/voluntarios`,
      fetchOptions,
    );

    if (volRes.ok) {
      const lista = await volRes.json();

      if (!lista || lista.length === 0) {
        tableBody.innerHTML = `<tr><td colspan="4" class="px-6 py-12 text-center text-slate-400 italic">Nenhum voluntário cadastrado na base de dados.</td></tr>`;
      } else {
        tableBody.innerHTML = lista
          .map((vol) => {
            // Garantir que habilidades seja um array
            const habs = Array.isArray(vol.habilidades) ? vol.habilidades : [];

            return `
                                <tr class="hover:bg-slate-50/80 transition-colors group">
                                    <td class="px-6 py-4 font-bold text-slate-700 font-medium">${vol.nome}</td>
                                    <td class="px-6 py-4">
                                        <div class="flex flex-wrap gap-1">
                                            ${habs
                                              .map(
                                                (h) => `
                                                <span class="bg-blue-50 text-blue-600 px-2 py-0.5 rounded text-[9px] font-bold uppercase border border-blue-100">
                                                    ${h}
                                                </span>
                                            `,
                                              )
                                              .join("")}
                                            ${habs.length === 0 ? '<span class="text-slate-300 text-[10px]">Sem habilidades</span>' : ""}
                                        </div>
                                    </td>
                                    <td class="px-6 py-4">
                                        <span class="text-[10px] font-bold ${vol.disponibilidade === "disponivel" ? "text-green-600" : "text-orange-500"} uppercase">
                                            ${vol.disponibilidade || "---"}
                                        </span>
                                    </td>
                                    <td class="px-6 py-4 text-right">
                                        <button class="p-2 text-blue-600 hover:bg-blue-50 rounded-lg shadow-sm border border-transparent hover:border-blue-100 transition-all">
                                            <i data-lucide="phone" class="w-4 h-4"></i>
                                        </button>
                                    </td>
                                </tr>
                            `;
          })
          .join("");
      }

      // Sucesso na UI
      badgeApi.innerText = "ONLINE";
      badgeApi.className =
        "text-green-600 font-bold bg-green-50 px-2.5 py-1 rounded-md border border-green-100 text-[9px]";
      sDot.className = "w-2 h-2 rounded-full bg-green-500 animate-pulse";
      sTxt.innerText = "Sincronizado";
      sTxt.className = "text-[10px] font-bold text-green-700 uppercase";
    } else {
      throw new Error(`Erro HTTP ${volRes.status} ao acessar voluntários.`);
    }
  } catch (err) {
    console.error("Erro Crítico de Fetch:", err);
    banner.classList.remove("hidden");
    debugText.innerText = err.message;

    badgeApi.innerText = "OFFLINE";
    badgeApi.className =
      "text-red-600 font-bold bg-red-50 px-2.5 py-1 rounded-md border border-red-100 text-[9px]";
    sDot.className = "w-2 h-2 rounded-full bg-red-500";
    sTxt.innerText = "Erro API";
  } finally {
    icon.classList.remove("animate-spin-fast");
    lucide.createIcons();
  }
}

// Carregamento inicial
window.onload = fetchDados;
window.wxOConfiguration = {
  orchestrationID:
    "3d7ed1c2090b4b5e9bcdead3a89d1f60_6f41ae2b-4456-4224-96b4-69de8e405c58",
  hostURL: "https://au-syd.watson-orchestrate.cloud.ibm.com",
  rootElementID: "root",
  deploymentPlatform: "ibmcloud",
  crn: "crn:v1:bluemix:public:watsonx-orchestrate:au-syd:a/3d7ed1c2090b4b5e9bcdead3a89d1f60:6f41ae2b-4456-4224-96b4-69de8e405c58::",
  chatOptions: {
    agentId: "625d0c9e-1e0a-4097-a075-5e76e087dafe",
    agentEnvironmentId: "8a47ed4b-83da-4e5a-bdbd-67245d5a62d1",
  },
};
setTimeout(function () {
  const script = document.createElement("script");
  script.src = `${window.wxOConfiguration.hostURL}/wxochat/wxoLoader.js?embed=true`;
  script.addEventListener("load", function () {
    wxoLoader.init();
  });
  document.head.appendChild(script);
}, 0);
