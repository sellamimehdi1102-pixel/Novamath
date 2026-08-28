import { api } from "./api.js";

const $ = (id) => document.getElementById(id);

document.querySelectorAll(".password-toggle").forEach((btn) => {
  btn.addEventListener("click", () => {
    const input = $(btn.dataset.target);
    const showing = input.type === "text";
    input.type = showing ? "password" : "text";
    btn.classList.toggle("is-visible", !showing);
  });
});

function evaluatePassword(password) {
  return {
    len: password.length >= 8,
    lower: /[a-z]/.test(password),
    upper: /[A-Z]/.test(password),
    digit: /[0-9]/.test(password),
    special: /[^a-zA-Z0-9]/.test(password),
  };
}

$("reset-password").addEventListener("input", () => {
  const rules = evaluatePassword($("reset-password").value);
  document.querySelectorAll("#reset-password-rules li").forEach((li) => {
    li.classList.toggle("is-valid", !!rules[li.dataset.rule]);
  });
});

const params = new URLSearchParams(window.location.search);
const token = params.get("token");

if (!token) {
  $("reset-form-wrap").hidden = true;
  $("reset-invalid").hidden = false;
}

$("reset-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const errorEl = $("reset-error");
  errorEl.hidden = true;

  const password = $("reset-password").value;
  const confirm = $("reset-password-confirm").value;
  const rules = evaluatePassword(password);
  if (!Object.values(rules).every(Boolean)) {
    errorEl.textContent = "Le mot de passe ne respecte pas toutes les conditions ci-dessus.";
    errorEl.hidden = false;
    return;
  }
  if (password !== confirm) {
    errorEl.textContent = "Les deux mots de passe ne correspondent pas.";
    errorEl.hidden = false;
    return;
  }

  try {
    await api.resetPassword({ token, password, confirm_password: confirm });
    $("reset-form-wrap").hidden = true;
    $("reset-success").hidden = false;
  } catch (err) {
    if (err.status === 400 && /invalide|expir/i.test(err.message || "")) {
      $("reset-form-wrap").hidden = true;
      $("reset-invalid").hidden = false;
    } else {
      errorEl.textContent = err.message || "Une erreur est survenue.";
      errorEl.hidden = false;
    }
  }
});
