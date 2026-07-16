// ── Modales Connexion / Inscription / Mot de passe oublié / légal, validation,
// force du mot de passe, appels API. Injectées dans le DOM au chargement de ce
// module (voir ensureAuthModalsMounted) pour pouvoir être ouvertes depuis
// N'IMPORTE QUELLE page (landing page, mais aussi dashboard/chapitres/profil
// en mode invité) — une seule source de vérité (authModalsTemplate.js) au lieu
// d'une copie du HTML par page. ─────────────────────────────────────────────
import { api } from "./api.js";
import { AUTH_MODALS_HTML } from "./authModalsTemplate.js";
import { resetGuestLocalState } from "./store.js";

const $ = (id) => document.getElementById(id);
const EMAIL_RE = /^[a-zA-Z0-9](?:[a-zA-Z0-9._+-]*[a-zA-Z0-9])?@gmail\.com$/;
const USERNAME_RE = /^[a-zA-Z0-9_-]{3,25}$/;

function ensureAuthModalsMounted() {
  if ($("signup-modal-overlay")) return;
  document.body.insertAdjacentHTML("beforeend", AUTH_MODALS_HTML);
}
ensureAuthModalsMounted();

function openModal(overlay) {
  overlay.hidden = false;
}
function closeModal(overlay) {
  overlay.hidden = true;
}
function closeAllAuthModals() {
  ["signup-modal-overlay", "login-modal-overlay", "forgot-modal-overlay", "legal-modal-overlay", "privacy-modal-overlay"].forEach(
    (id) => { $(id).hidden = true; }
  );
}

// ── Ouverture / fermeture génériques ────────────────────────────────────────
// Délégation d'événements sur `document` (plutôt que d'attacher un listener à
// chaque bouton trouvé au chargement) : indispensable pour que des boutons
// ajoutés dynamiquement APRÈS ce module (carte premium du mode invité, panneau
// flottant) ouvrent eux aussi les modales sans re-câblage explicite.
function wireOpeners(selector, overlayId, before) {
  document.addEventListener("click", (e) => {
    const trigger = e.target.closest(selector);
    if (!trigger) return;
    closeAllAuthModals();
    if (before) before();
    openModal($(overlayId));
  });
}

let transferGuestChoice = true;
function setTransferGuestChoice(value) {
  transferGuestChoice = value;
  $("btn-transfer-guest-yes").classList.toggle("btn-primary", value);
  $("btn-transfer-guest-yes").classList.toggle("btn-secondary", !value);
  $("btn-transfer-guest-yes").setAttribute("aria-pressed", String(value));
  $("btn-transfer-guest-no").classList.toggle("btn-primary", !value);
  $("btn-transfer-guest-no").classList.toggle("btn-secondary", value);
  $("btn-transfer-guest-no").setAttribute("aria-pressed", String(!value));
}
document.addEventListener("click", (e) => {
  if (e.target.closest("#btn-transfer-guest-yes")) setTransferGuestChoice(true);
  if (e.target.closest("#btn-transfer-guest-no")) setTransferGuestChoice(false);
});

wireOpeners(".js-open-signup", "signup-modal-overlay", () => {
  $("signup-transfer-guest-row").hidden = !currentAccount?.is_guest;
  setTransferGuestChoice(true);
});
wireOpeners(".js-open-login", "login-modal-overlay");
wireOpeners(".js-open-legal", "legal-modal-overlay");
wireOpeners(".js-open-privacy", "privacy-modal-overlay");
wireOpeners(".js-open-forgot", "forgot-modal-overlay", () => {
  $("forgot-email").value = $("login-email").value || "";
  $("forgot-result").hidden = true;
  $("forgot-error").hidden = true;
});
wireOpeners(".js-switch-to-login", "login-modal-overlay");
wireOpeners(".js-switch-to-signup", "signup-modal-overlay");

document.addEventListener("click", (e) => {
  if (e.target.classList?.contains("modal-overlay")) closeModal(e.target);
});
document.addEventListener("click", (e) => {
  if (e.target.closest("#btn-signup-cancel")) closeModal($("signup-modal-overlay"));
  if (e.target.closest("#btn-login-cancel")) closeModal($("login-modal-overlay"));
  if (e.target.closest("#btn-forgot-cancel")) closeModal($("forgot-modal-overlay"));
  if (e.target.closest("#btn-legal-close")) closeModal($("legal-modal-overlay"));
  if (e.target.closest("#btn-privacy-close")) closeModal($("privacy-modal-overlay"));
});

// ── Mode invité ──────────────────────────────────────────────────────────────
// "Démarrer l'évaluation" sur la landing page ne demande plus de compte : il
// entre directement en mode invité (aucun formulaire, aucune connexion) et
// lance l'évaluation. `currentAccount` distingue 2 cas désormais possibles ici
// (voir webapp/server.py::_serve_landing, point de passage UNIQUE de la
// landing page — `/` et `/index.html` — qui purge systématiquement toute
// session invité avant même de renvoyer ce HTML) : anonyme (aucun compte → on
// crée un invité tout neuf), ou un compte réel (un utilisateur connecté qui
// atteint quand même la landing page — via le logo — ne doit JAMAIS être
// transformé en invité : on le laisse simplement continuer avec son vrai
// compte). Un compte invité ne peut plus jamais être observé ici : le serveur
// l'a déjà détruit avant de servir la page.
let currentAccount = null;
api.me().then(({ user }) => { currentAccount = user; }).catch(() => {
  // 401 : aucune session valide. Purge défensive de tout résidu client d'une
  // éventuelle session invité précédente (localStorage/sessionStorage) — le
  // serveur a déjà détruit ses données, mais on élimine ici toute trace encore
  // visible dans CE navigateur avant que l'utilisateur ne relance quoi que ce
  // soit (voir store.js::resetGuestLocalState).
  if (document.querySelector(".js-start-guest-eval")) resetGuestLocalState();
});

document.addEventListener("click", async (e) => {
  const trigger = e.target.closest(".js-start-guest-eval");
  if (!trigger) return;
  trigger.disabled = true;
  try {
    if (!currentAccount) await api.enterGuest();
    window.location.href = "/evaluation.html";
  } catch {
    trigger.disabled = false;
  }
});

// ── Afficher / masquer le mot de passe ──────────────────────────────────────
document.querySelectorAll(".password-toggle").forEach((btn) => {
  btn.addEventListener("click", () => {
    const input = $(btn.dataset.target);
    const showing = input.type === "text";
    input.type = showing ? "password" : "text";
    btn.classList.toggle("is-visible", !showing);
    btn.setAttribute("aria-label", showing ? "Afficher le mot de passe" : "Masquer le mot de passe");
  });
});

// ── Indicateur de force du mot de passe ─────────────────────────────────────
function evaluatePassword(password) {
  const rules = {
    len: password.length >= 8,
    lower: /[a-z]/.test(password),
    upper: /[A-Z]/.test(password),
    digit: /[0-9]/.test(password),
    special: /[^a-zA-Z0-9]/.test(password),
  };
  let score = Object.values(rules).filter(Boolean).length;
  if (password.length < 8) score = Math.min(score, 1);
  const labels = ["Faible", "Faible", "Faible", "Moyen", "Fort", "Très fort"];
  const levels = [1, 1, 1, 2, 3, 4];
  return { rules, score, label: labels[score], level: levels[score] };
}

$("signup-password").addEventListener("input", () => {
  const password = $("signup-password").value;
  const { rules, label, level } = evaluatePassword(password);
  const strengthEl = $("signup-strength");
  strengthEl.hidden = password.length === 0;
  $("signup-strength-fill").style.width = `${level * 25}%`;
  $("signup-strength-fill").dataset.level = String(level);
  $("signup-strength-label").textContent = label;
  document.querySelectorAll("#signup-password-rules li").forEach((li) => {
    li.classList.toggle("is-valid", !!rules[li.dataset.rule]);
  });
});

// ── Validation (miroir de webapp/auth.py côté client, pour un retour immédiat) ─
function setFieldError(prefix, field, message) {
  const el = $(`${prefix}-error-${field}`);
  if (!el) return;
  el.textContent = message || el.textContent;
  el.hidden = !message;
}
function clearErrors(prefix, fields) {
  fields.forEach((f) => setFieldError(prefix, f, ""));
}

function validateSignupClientSide() {
  clearErrors("signup", ["email", "username", "pseudo", "password", "confirm", "terms", "privacy", "global"]);
  let ok = true;

  const email = $("signup-email").value.trim();
  if (!email) { setFieldError("signup", "email", "L'adresse email est obligatoire."); ok = false; }
  else if (!EMAIL_RE.test(email)) { setFieldError("signup", "email", "Utilise une adresse Gmail valide (nom@gmail.com)."); ok = false; }

  const username = $("signup-username").value.trim();
  if (!username) { setFieldError("signup", "username", "Le nom d'utilisateur est obligatoire."); ok = false; }
  else if (!USERNAME_RE.test(username)) { setFieldError("signup", "username", "3 à 25 caractères : lettres, chiffres, - ou _ uniquement."); ok = false; }

  const pseudo = $("signup-pseudo").value.trim();
  if (!pseudo) { setFieldError("signup", "pseudo", "Le pseudo est obligatoire."); ok = false; }

  const password = $("signup-password").value;
  const { rules } = evaluatePassword(password);
  if (!password) { setFieldError("signup", "password", "Le mot de passe est obligatoire."); ok = false; }
  else if (!Object.values(rules).every(Boolean)) { setFieldError("signup", "password", "Le mot de passe ne respecte pas toutes les conditions ci-dessus."); ok = false; }

  const confirm = $("signup-password-confirm").value;
  if (password !== confirm) { setFieldError("signup", "confirm", "Les deux mots de passe ne correspondent pas."); ok = false; }

  if (!$("signup-accept-terms").checked) { setFieldError("signup", "terms", "Tu dois accepter les conditions d'utilisation."); ok = false; }
  if (!$("signup-accept-privacy").checked) { setFieldError("signup", "privacy", "Tu dois accepter la politique de confidentialité."); ok = false; }

  return ok;
}

function redirectAfterAuth() {
  const params = new URLSearchParams(window.location.search);
  const next = params.get("next");
  const allowed = ["dashboard.html", "chapitres.html", "exercice.html", "evaluation.html", "profil.html"];
  window.location.href = next && allowed.includes(next) ? `/${next}` : "/dashboard.html";
}

$("signup-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  if (!validateSignupClientSide()) return;

  const submitBtn = $("btn-signup-submit");
  submitBtn.disabled = true;
  try {
    await api.register({
      email: $("signup-email").value.trim(),
      username: $("signup-username").value.trim(),
      pseudo: $("signup-pseudo").value.trim(),
      password: $("signup-password").value,
      confirm_password: $("signup-password-confirm").value,
      accept_terms: $("signup-accept-terms").checked,
      accept_privacy: $("signup-accept-privacy").checked,
      transfer_guest: !!currentAccount?.is_guest && transferGuestChoice,
    });
    redirectAfterAuth();
  } catch (err) {
    if (err.field) setFieldError("signup", err.field, err.message);
    else setFieldError("signup", "global", err.message || "Une erreur est survenue.");
  } finally {
    submitBtn.disabled = false;
  }
});

$("login-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  setFieldError("login", "global", "");
  const email = $("login-email").value.trim();
  const password = $("login-password").value;
  if (!email || !password) {
    setFieldError("login", "global", "Adresse email et mot de passe requis.");
    return;
  }

  const submitBtn = $("btn-login-submit");
  submitBtn.disabled = true;
  try {
    await api.login({ email, password, remember: $("login-remember").checked });
    redirectAfterAuth();
  } catch (err) {
    setFieldError("login", "global", err.message || "Connexion impossible.");
  } finally {
    submitBtn.disabled = false;
  }
});

$("btn-forgot-submit").addEventListener("click", async () => {
  $("forgot-error").hidden = true;
  $("forgot-result").hidden = true;
  const email = $("forgot-email").value.trim();
  if (!email || !EMAIL_RE.test(email)) {
    $("forgot-error").textContent = "Utilise une adresse Gmail valide.";
    $("forgot-error").hidden = false;
    return;
  }
  const btn = $("btn-forgot-submit");
  btn.disabled = true;
  try {
    const res = await api.forgotPassword(email);
    $("forgot-result").innerHTML = res.dev_reset_link
      ? `${res.message}<br><a href="${res.dev_reset_link}">Lien de réinitialisation (mode développement, aucun service d'email configuré)</a>`
      : res.message;
    $("forgot-result").hidden = false;
  } catch (err) {
    $("forgot-error").textContent = err.message || "Une erreur est survenue.";
    $("forgot-error").hidden = false;
  } finally {
    btn.disabled = false;
  }
});

// ── Connexion Google : détecte si l'OAuth est configuré avant de rediriger,
// pour ne jamais faire semblant de fonctionner si aucune clé n'est en place. ─
async function handleGoogleClick() {
  try {
    const res = await fetch("/api/auth/google/start", { redirect: "manual" });
    if (res.type === "opaqueredirect" || res.status === 0) {
      window.location.href = "/api/auth/google/start";
      return;
    }
    const data = await res.json().catch(() => ({}));
    setFieldError("signup", "global", data.error || "Connexion Google indisponible pour le moment.");
    setFieldError("login", "global", data.error || "Connexion Google indisponible pour le moment.");
  } catch {
    setFieldError("signup", "global", "Connexion Google indisponible pour le moment.");
    setFieldError("login", "global", "Connexion Google indisponible pour le moment.");
  }
}
$("btn-google-signup").addEventListener("click", handleGoogleClick);
$("btn-google-login").addEventListener("click", handleGoogleClick);

// ── Si redirigé depuis une page protégée (?next=...), pré-ouvre la connexion ─
(function initFromQuery() {
  const params = new URLSearchParams(window.location.search);
  const next = params.get("next");
  if (!next) return;
  const labels = {
    "dashboard.html": "ton dashboard", "chapitres.html": "les chapitres",
    "exercice.html": "l'entraînement", "evaluation.html": "l'évaluation", "profil.html": "ton profil",
  };
  $("login-next-hint").textContent = `Connecte-toi pour accéder à ${labels[next] || "cette page"}.`;
  $("login-next-hint").hidden = false;
  openModal($("login-modal-overlay"));
})();
