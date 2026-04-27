lucide.createIcons();

document.getElementById("loginForm").addEventListener("submit", async (e) => {
  e.preventDefault();

  const loginId = document.getElementById("loginId").value.trim();
  const senha = document.getElementById("senha").value;
  const btn = document.getElementById("btnSubmit");
  const errorBox = document.getElementById("errorBox");

  btn.disabled = true;

  btn.innerHTML =
    '<i data-lucide="loader-2" class="w-5 h-5 animate-spin"></i> Entrando...';

  lucide.createIcons();

  errorBox.classList.add("hidden");

  try {
    const response = await fetch(`${window.MATCHHELP_API}/api/v1/auth/login`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        login_id: loginId,
        senha: senha,
      }),
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || "Falha na autenticação");
    }

    localStorage.setItem("mh_token", data.token);
    localStorage.setItem("mh_voluntario_id", data.voluntario_id);
    localStorage.setItem("mh_nome", data.nome);

    if (data.precisa_trocar_senha) {
      window.location.href = "trocar-senha.html";
    } else {
      window.location.href = "painel-voluntario.html";
    }
  } catch (err) {
    errorBox.textContent = err.message;
    errorBox.classList.remove("hidden");
  } finally {
    btn.disabled = false;

    btn.innerHTML = 'Entrar <i data-lucide="arrow-right" class="w-5 h-5"></i>';

    lucide.createIcons();
  }
});
