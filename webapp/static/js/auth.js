// ── Modales Connexion / Inscription / Mot de passe oublié / légal, validation,
// force du mot de passe, appels API. Injectées dans le DOM au chargement de ce
// module (voir ensureAuthModalsMounted) pour pouvoir être ouvertes depuis
// N'IMPORTE QUELLE page (landing page, mais aussi dashboard/chapitres/profil
// en mode invité) — une seule source de vérité (authModalsTemplate.js) au lieu
// d'une copie du HTML par page. ─────────────────────────────────────────────
import { api } from "./api.js";
import { AUTH_MODALS_HTML } from "./authModalsTemplate.js";
import { resetGuestLocalState } from "./store.js";
import { hasExplicitClassLevel, ALLOWED_NEXT_PAGES } from "./curriculumSelector.js";
import "./cookieConsent.js";

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
  [
    "signup-modal-overlay", "oauth-signup-modal-overlay", "login-modal-overlay", "login-2fa-modal-overlay",
    "forgot-modal-overlay", "legal-modal-overlay", "privacy-modal-overlay",
  ].forEach((id) => { $(id).hidden = true; });
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

// ── Protection des mineurs (RGPD) — seuil légal français : 15 ans (voir
// consent_service.MINOR_CONSENT_AGE_THRESHOLD côté serveur, seule source de
// vérité ; ce calcul client n'est qu'un confort d'affichage immédiat, revalidé
// systématiquement côté serveur à l'inscription). ──────────────────────────
const MINOR_CONSENT_AGE_THRESHOLD = 15;
function computeAge(birthDateStr) {
  const [year, month, day] = birthDateStr.split("-").map(Number);
  if (!year || !month || !day) return null;
  const born = new Date(year, month - 1, day);
  const today = new Date();
  let age = today.getFullYear() - born.getFullYear();
  if (today.getMonth() < born.getMonth() || (today.getMonth() === born.getMonth() && today.getDate() < born.getDate())) {
    age -= 1;
  }
  return age;
}
function isMinorSignup(birthDateFieldId = "signup-birth-date") {
  const birthDate = $(birthDateFieldId).value;
  if (!birthDate) return false;
  const age = computeAge(birthDate);
  return age !== null && age < MINOR_CONSENT_AGE_THRESHOLD;
}
$("signup-birth-date").addEventListener("change", () => {
  $("signup-parent-email-row").hidden = !isMinorSignup();
});
$("oauth-signup-birth-date").addEventListener("change", () => {
  $("oauth-signup-parent-email-row").hidden = !isMinorSignup("oauth-signup-birth-date");
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
  if (e.target.closest("#btn-oauth-signup-cancel")) closeModal($("oauth-signup-modal-overlay"));
  if (e.target.closest("#btn-login-cancel")) closeModal($("login-modal-overlay"));
  if (e.target.closest("#btn-forgot-cancel")) closeModal($("forgot-modal-overlay"));
  if (e.target.closest("#btn-legal-close")) closeModal($("legal-modal-overlay"));
  if (e.target.closest("#btn-privacy-close")) closeModal($("privacy-modal-overlay"));
});

// ── Mode invité ──────────────────────────────────────────────────────────────
// "Commencer gratuitement" sur la landing page ne demande plus de compte : il
// entre directement en mode invité (aucun formulaire, aucune connexion) et
// ouvre directement les chapitres. `currentAccount` distingue 2 cas désormais
// possibles ici (voir webapp/server.py::_serve_landing, point de passage
// UNIQUE de la landing page — `/` et `/index.html` — qui purge
// systématiquement toute session invité avant même de renvoyer ce HTML) :
// anonyme (aucun compte → on crée un invité tout neuf), ou un compte réel (un
// utilisateur connecté qui atteint quand même la landing page — via le logo —
// ne doit JAMAIS être transformé en invité : on le laisse simplement
// continuer avec son vrai compte). Un compte invité ne peut plus jamais être
// observé ici : le serveur l'a déjà détruit avant de servir la page.
let currentAccount = null;
api.me().then(({ user }) => {
  currentAccount = user;
  if (!user.is_guest) checkPolicyReacceptance();
}).catch(() => {
  // 401 : aucune session valide. Purge défensive de tout résidu client d'une
  // éventuelle session invité précédente (localStorage/sessionStorage) — le
  // serveur a déjà détruit ses données, mais on élimine ici toute trace encore
  // visible dans CE navigateur avant que l'utilisateur ne relance quoi que ce
  // soit (voir store.js::resetGuestLocalState).
  if (document.querySelector(".js-start-guest")) resetGuestLocalState();
});

// ── Ré-acceptation forcée des CGU/politique de confidentialité (RGPD) ──────
// Vérifiée à chaque chargement de page pour un compte connecté (non invité) :
// si consent_service.py signale une nouvelle version publiée depuis la
// dernière acceptation de ce compte, une modale bloquante (fermeture
// impossible sans accepter) est affichée avant de laisser continuer.
async function checkPolicyReacceptance() {
  try {
    const status = await api.getPolicyStatus();
    if (!status.needs_reacceptance) return;
  } catch {
    return;
  }
  $("policy-update-modal-overlay").hidden = false;
}

$("btn-policy-update-accept").addEventListener("click", async () => {
  const errorEl = $("policy-update-error");
  errorEl.hidden = true;
  if (!$("policy-update-accept-terms").checked || !$("policy-update-accept-privacy").checked) {
    errorEl.textContent = "Tu dois accepter les deux documents pour continuer.";
    errorEl.hidden = false;
    return;
  }
  try {
    await api.acceptPolicy();
    $("policy-update-modal-overlay").hidden = true;
  } catch (err) {
    errorEl.textContent = err.message || "Une erreur est survenue.";
    errorEl.hidden = false;
  }
});

document.addEventListener("click", async (e) => {
  const trigger = e.target.closest(".js-start-guest");
  if (!trigger) return;
  trigger.disabled = true;
  try {
    if (!currentAccount) await api.enterGuest();
    window.location.href = "/chapitres.html";
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
  clearErrors("signup", ["email", "username", "pseudo", "birth_date", "parent_email", "password", "confirm", "terms", "privacy", "global"]);
  let ok = true;

  const email = $("signup-email").value.trim();
  if (!email) { setFieldError("signup", "email", "L'adresse email est obligatoire."); ok = false; }
  else if (!EMAIL_RE.test(email)) { setFieldError("signup", "email", "Utilise une adresse Gmail valide (nom@gmail.com)."); ok = false; }

  const username = $("signup-username").value.trim();
  if (!username) { setFieldError("signup", "username", "Le nom d'utilisateur est obligatoire."); ok = false; }
  else if (!USERNAME_RE.test(username)) { setFieldError("signup", "username", "3 à 25 caractères : lettres, chiffres, - ou _ uniquement."); ok = false; }

  const pseudo = $("signup-pseudo").value.trim();
  if (!pseudo) { setFieldError("signup", "pseudo", "Le pseudo est obligatoire."); ok = false; }

  const birthDate = $("signup-birth-date").value;
  if (!birthDate) { setFieldError("signup", "birth_date", "La date de naissance est obligatoire."); ok = false; }
  else if (new Date(birthDate) > new Date()) { setFieldError("signup", "birth_date", "La date de naissance ne peut pas être dans le futur."); ok = false; }
  else if (isMinorSignup() && !$("signup-parent-email").value.trim()) {
    setFieldError("signup", "parent_email", "L'email d'un parent est obligatoire pour ton âge."); ok = false;
  }

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

function resolveAuthDestination() {
  const params = new URLSearchParams(window.location.search);
  const next = params.get("next");
  return next && ALLOWED_NEXT_PAGES.includes(next) ? next : "dashboard.html";
}

function redirectAfterAuth() {
  window.location.href = `/${resolveAuthDestination()}`;
}

// ── Phase 5 (onboarding) — uniquement pour une INSCRIPTION (jamais une
// connexion à un compte existant, voir les appels ci-dessous) : si aucune
// classe n'a encore été choisie explicitement dans ce navigateur
// (curriculumSelector.js::hasExplicitClassLevel — jamais le simple défaut
// silencieux "seconde"), on détoure une seule fois par /choisir-classe.html
// avant de continuer vers la destination habituelle (next ou dashboard),
// jamais perdue en route (?next= repropagé). Un compte déjà existant qui se
// connecte pour la première fois sur un navigateur sans classe choisie n'est
// PAS concerné : seule la création de compte déclenche ce détour, pour rester
// strictement dans le périmètre de cette phase. Aucune donnée de compte,
// aucune règle métier : `class_level` reste une préférence 100% client,
// exactement comme avant.
function redirectAfterSignup() {
  const destination = resolveAuthDestination();
  if (!hasExplicitClassLevel()) {
    window.location.href = `/choisir-classe.html?next=${encodeURIComponent(destination)}`;
    return;
  }
  window.location.href = `/${destination}`;
}

$("signup-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  if (!validateSignupClientSide()) return;

  const submitBtn = $("btn-signup-submit");
  submitBtn.disabled = true;
  try {
    const isMinor = isMinorSignup();
    const result = await api.register({
      email: $("signup-email").value.trim(),
      username: $("signup-username").value.trim(),
      pseudo: $("signup-pseudo").value.trim(),
      birth_date: $("signup-birth-date").value,
      parent_email: isMinor ? $("signup-parent-email").value.trim() : undefined,
      password: $("signup-password").value,
      confirm_password: $("signup-password-confirm").value,
      accept_terms: $("signup-accept-terms").checked,
      accept_privacy: $("signup-accept-privacy").checked,
      transfer_guest: !!currentAccount?.is_guest && transferGuestChoice,
    });
    if (result.account_status === "pending_parental_consent") {
      // Aucune session n'a été créée côté serveur — le compte doit attendre
      // l'autorisation du parent (voir consent_service.py) avant tout accès.
      setFieldError("signup", "global", result.message);
      $("signup-error-global").classList.add("form-error--info");
      return;
    }
    redirectAfterSignup();
  } catch (err) {
    if (err.field) setFieldError("signup", err.field, err.message);
    else setFieldError("signup", "global", err.message || "Une erreur est survenue.");
  } finally {
    submitBtn.disabled = false;
  }
});

// ── Finalise une inscription Google amorcée par oauth_callback (voir
// initFromQuery ci-dessous) : email déjà vérifié par Google, il ne manque que
// nom d'utilisateur/pseudo/date de naissance/CGU (auth.py::oauth_complete_signup). ─
let pendingOAuthProvider = null;
function validateOAuthSignupClientSide() {
  clearErrors("oauth-signup", ["username", "pseudo", "birth_date", "parent_email", "accept_terms", "accept_privacy", "global"]);
  let ok = true;

  const username = $("oauth-signup-username").value.trim();
  if (!username) { setFieldError("oauth-signup", "username", "Le nom d'utilisateur est obligatoire."); ok = false; }
  else if (!USERNAME_RE.test(username)) { setFieldError("oauth-signup", "username", "3 à 25 caractères : lettres, chiffres, - ou _ uniquement."); ok = false; }

  const pseudo = $("oauth-signup-pseudo").value.trim();
  if (!pseudo) { setFieldError("oauth-signup", "pseudo", "Le pseudo est obligatoire."); ok = false; }

  const birthDate = $("oauth-signup-birth-date").value;
  if (!birthDate) { setFieldError("oauth-signup", "birth_date", "La date de naissance est obligatoire."); ok = false; }
  else if (new Date(birthDate) > new Date()) { setFieldError("oauth-signup", "birth_date", "La date de naissance ne peut pas être dans le futur."); ok = false; }
  else if (isMinorSignup("oauth-signup-birth-date") && !$("oauth-signup-parent-email").value.trim()) {
    setFieldError("oauth-signup", "parent_email", "L'email d'un parent est obligatoire pour ton âge."); ok = false;
  }

  if (!$("oauth-signup-accept-terms").checked) { setFieldError("oauth-signup", "accept_terms", "Tu dois accepter les conditions d'utilisation."); ok = false; }
  if (!$("oauth-signup-accept-privacy").checked) { setFieldError("oauth-signup", "accept_privacy", "Tu dois accepter la politique de confidentialité."); ok = false; }

  return ok;
}

function openOAuthCompleteSignup(provider) {
  pendingOAuthProvider = provider;
  closeAllAuthModals();
  clearErrors("oauth-signup", ["username", "pseudo", "birth_date", "parent_email", "accept_terms", "accept_privacy", "global"]);
  $("oauth-signup-form").reset();
  $("oauth-signup-parent-email-row").hidden = true;
  openModal($("oauth-signup-modal-overlay"));
}

$("oauth-signup-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  if (!validateOAuthSignupClientSide()) return;

  const submitBtn = $("btn-oauth-signup-submit");
  submitBtn.disabled = true;
  try {
    const isMinor = isMinorSignup("oauth-signup-birth-date");
    const result = await api.oauthCompleteSignup(pendingOAuthProvider, {
      username: $("oauth-signup-username").value.trim(),
      pseudo: $("oauth-signup-pseudo").value.trim(),
      birth_date: $("oauth-signup-birth-date").value,
      parent_email: isMinor ? $("oauth-signup-parent-email").value.trim() : undefined,
      accept_terms: $("oauth-signup-accept-terms").checked,
      accept_privacy: $("oauth-signup-accept-privacy").checked,
    });
    if (result.account_status === "pending_parental_consent") {
      // Aucune session n'a été créée côté serveur — le compte doit attendre
      // l'autorisation du parent (voir consent_service.py) avant tout accès.
      setFieldError("oauth-signup", "global", result.message);
      $("oauth-signup-error-global").classList.add("form-error--info");
      return;
    }
    redirectAfterSignup();
  } catch (err) {
    if (err.field) setFieldError("oauth-signup", err.field, err.message);
    else setFieldError("oauth-signup", "global", err.message || "Une erreur est survenue.");
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
    const result = await api.login({ email, password, remember: $("login-remember").checked });
    if (result.two_factor_required) {
      closeModal($("login-modal-overlay"));
      open2FAChallenge(result.challenge_token);
    } else {
      redirectAfterAuth();
    }
  } catch (err) {
    setFieldError("login", "global", err.message || "Connexion impossible.");
  } finally {
    submitBtn.disabled = false;
  }
});

// ── Étape 2 de connexion : code TOTP ou recovery code (voir login() ci-dessus,
// qui renvoie two_factor_required + challenge_token au lieu d'une session
// quand le compte a activé la 2FA — webapp/two_factor_service.py). ──────────
let recoveryMode = false;
function setRecoveryMode(value) {
  recoveryMode = value;
  $("login-2fa-code-row").hidden = value;
  $("login-2fa-recovery-row").hidden = !value;
  $("login-2fa-intro").textContent = value
    ? "Saisis l'un de tes recovery codes (généré lors de l'activation de la double authentification)."
    : "Saisis le code à 6 chiffres généré par ton application d'authentification.";
  $("btn-2fa-toggle-recovery").textContent = value
    ? "Utiliser le code de mon application"
    : "Utiliser un recovery code";
  $("login-2fa-error-global").hidden = true;
  const input = value ? $("login-2fa-recovery-code") : $("login-2fa-code");
  setTimeout(() => input.focus(), 50);
}

function open2FAChallenge(challengeToken) {
  $("login-2fa-form").dataset.challengeToken = challengeToken;
  $("login-2fa-code").value = "";
  $("login-2fa-recovery-code").value = "";
  setRecoveryMode(false);
  openModal($("login-2fa-modal-overlay"));
}

$("btn-2fa-toggle-recovery").addEventListener("click", () => setRecoveryMode(!recoveryMode));
$("btn-login-2fa-cancel").addEventListener("click", () => closeModal($("login-2fa-modal-overlay")));

$("login-2fa-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  $("login-2fa-error-global").hidden = true;
  const challengeToken = e.currentTarget.dataset.challengeToken;
  const submitBtn = $("btn-login-2fa-submit");
  submitBtn.disabled = true;
  try {
    if (recoveryMode) {
      await api.recover2FA(challengeToken, $("login-2fa-recovery-code").value.trim());
    } else {
      await api.verify2FA(challengeToken, $("login-2fa-code").value.trim());
    }
    redirectAfterAuth();
  } catch (err) {
    $("login-2fa-error-global").textContent = err.message || "Code invalide.";
    $("login-2fa-error-global").hidden = false;
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

// ── Si redirigé depuis une page protégée (?next=...), pré-ouvre la connexion ;
// si redirigé depuis oauth_callback (webapp/auth.py), termine le flux Google :
// erreur, second facteur requis, ou inscription à finaliser (nouveau compte). ─
function stripQueryParams(names) {
  const url = new URL(window.location.href);
  names.forEach((n) => url.searchParams.delete(n));
  window.history.replaceState({}, "", url.pathname + url.search + url.hash);
}

(function initFromQuery() {
  const params = new URLSearchParams(window.location.search);

  const oauthError = params.get("oauth_error");
  if (oauthError) {
    stripQueryParams(["oauth_error"]);
    setFieldError("login", "global", oauthError);
    openModal($("login-modal-overlay"));
    return;
  }

  const challengeToken = params.get("oauth_two_factor_required");
  if (challengeToken) {
    stripQueryParams(["oauth_two_factor_required"]);
    open2FAChallenge(challengeToken);
    return;
  }

  const oauthProvider = params.get("oauth_complete_signup");
  if (oauthProvider) {
    stripQueryParams(["oauth_complete_signup"]);
    openOAuthCompleteSignup(oauthProvider);
    return;
  }

  const next = params.get("next");
  if (!next) return;
  const labels = {
    "dashboard.html": "ton dashboard", "chapitres.html": "les exercices",
    "exercice.html": "l'entraînement", "profil.html": "ton profil",
  };
  $("login-next-hint").textContent = `Connecte-toi pour accéder à ${labels[next] || "cette page"}.`;
  $("login-next-hint").hidden = false;
  openModal($("login-modal-overlay"));
})();
