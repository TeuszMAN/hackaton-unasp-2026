lucide.createIcons();

let chatInstance = null;
let watchInterval = null;

/**
 * Ativa o efeito de escurecer a tela e dar foco no chat.
 * Inicia uma verificação periódica para garantir o fechamento.
 */
function activateSpotlight() {
  const overlay = document.getElementById("spotlight-overlay");
  if (overlay) {
    overlay.classList.remove("invisible", "pointer-events-none");
    overlay.classList.add("opacity-100", "pointer-events-auto");
    document.body.classList.add("spotlight-active");

    // VIGILÂNCIA ATIVA: Verifica a cada 300ms se o chat abriu
    if (watchInterval) clearInterval(watchInterval);
    watchInterval = setInterval(() => {
      // Verifica se a instância da IBM reporta que está aberta
      if (chatInstance && typeof chatInstance.getState === "function") {
        const state = chatInstance.getState();
        if (state && state.mainWindow && state.mainWindow.visible) {
          console.log(
            "[Crise-Sync] Detectado chat aberto via State. Fechando Spotlight.",
          );
          closeSpotlight();
        }
      }

      // Fallback visual: Verifica se existe algum iframe de chat visível que não seja apenas a bolha
      // Isso ajuda se a API do Watson estiver lenta para responder
      const launcherOpen =
        document.querySelector(".WxoMain-container") ||
        document.querySelector(".ea-chat-container") ||
        document.querySelector('[role="dialog"]');

      if (launcherOpen && launcherOpen.offsetHeight > 100) {
        closeSpotlight();
      }
    }, 300);
  }
}

/**
 * Remove o efeito de foco (spotlight).
 */
function closeSpotlight() {
  const overlay = document.getElementById("spotlight-overlay");
  if (overlay && overlay.classList.contains("opacity-100")) {
    overlay.classList.add("opacity-0", "pointer-events-none");
    overlay.classList.remove("opacity-100", "pointer-events-auto");

    if (watchInterval) {
      clearInterval(watchInterval);
      watchInterval = null;
    }

    setTimeout(() => {
      overlay.classList.add("invisible");
      document.body.classList.remove("spotlight-active");
    }, 400);
  }
}

// Captura global de cliques no container do chat para garantir o fechamento imediato
document.addEventListener(
  "mousedown",
  function (e) {
    const chatContainer = document.getElementById("ibm-chat-portal");
    if (chatContainer && chatContainer.contains(e.target)) {
      closeSpotlight();
    }
  },
  true,
);

// Configuração do Chat
window.wxOConfiguration = {
  orchestrationID:
    "3d7ed1c2090b4b5e9bcdead3a89d1f60_6f41ae2b-4456-4224-96b4-69de8e405c58",
  hostURL: "https://au-syd.watson-orchestrate.cloud.ibm.com",
  deploymentPlatform: "ibmcloud",
  crn: "crn:v1:bluemix:public:watsonx-orchestrate:au-syd:a/3d7ed1c2090b4b5e9bcdead3a89d1f60:6f41ae2b-4456-4224-96b4-69de8e405c58::",
  chatOptions: {
    agentId: "8efb193d-a518-41dc-b248-6cf1fc73b783",
    agentEnvironmentId: "c8ee69af-31f9-4d5c-904e-f3b08fee9a40",
    showLauncher: true,
    onLoad: function (instance) {
      chatInstance = instance;
      instance.render();

      // Eventos oficiais da IBM
      instance.on({
        type: "view:change",
        handler: (event) => {
          if (event.newViewState.isOpen) closeSpotlight();
        },
      });

      instance.on({
        type: "window:open",
        handler: () => {
          closeSpotlight();
        },
      });
    },
  },
  defaultLocale: "pt-BR",
};

(function () {
  const chatDiv = document.createElement("div");
  chatDiv.id = "ibm-chat-portal";
  document.body.appendChild(chatDiv);

  setTimeout(function () {
    const s = document.createElement("script");
    s.src = `${window.wxOConfiguration.hostURL}/wxochat/wxoLoader.js`;
    s.onload = function () {
      if (window.wxoLoader) {
        window.wxoLoader.init();
      }
    };
    document.head.appendChild(s);
  }, 300);
})();
