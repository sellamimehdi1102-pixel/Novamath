// ── Centre de personnalisation Mathadap ─────────────────────────────────────
// Deux colonnes (catégories à gauche, contenu à droite), tout est mis à jour
// sans recharger la page. Chaque catégorie a une fonction render() qui
// retourne du HTML et une fonction bind() qui attache les événements après
// insertion dans le DOM — évite les handlers dupliqués à chaque changement
// d'onglet.
import { api } from "./api.js";
import { currentTheme } from "./theme.js";
import { getSettings, setSetting, onSettingsChange } from "./settingsManager.js";
import { icon } from "./icons.js";
import { t } from "./i18n.js";
import { initClassBadge } from "./curriculumSelector.js";
import { openPopup } from "./popup.js";
import { openReportTicketPopup, openSupportHubPopup } from "./supportTicket.js";

const $ = (id) => document.getElementById(id);
let panel, menu;

let user = null;
let settings = null;
let cookieConsentState = null;

function CATEGORIES() {
  return [
    { id: "account", label: t("settings.cat.account"), icon: "user" },
    { id: "appearance", label: t("settings.cat.appearance"), icon: "palette" },
    { id: "training", label: t("settings.cat.training"), icon: "sliders" },
    { id: "learning", label: t("settings.cat.learning"), icon: "target" },
    { id: "chatbot", label: t("settings.cat.chatbot"), icon: "messageSquare" },
    { id: "security", label: t("settings.cat.security"), icon: "lock" },
    { id: "language", label: t("settings.cat.language"), icon: "globe" },
    { id: "help", label: t("settings.cat.help"), icon: "helpCircle" },
  ];
}

let activeCategory = localStorage.getItem("novamath:settings_tab") || "account";
if (!CATEGORIES().some((c) => c.id === activeCategory)) activeCategory = "account";

// ── Toast ────────────────────────────────────────────────────────────────────
let toastTimer = null;
function showToast(message, isError = false) {
  const el = $("settings-toast");
  clearTimeout(toastTimer);
  el.className = `toast${isError ? " toast--error" : ""}`;
  el.innerHTML = `${icon(isError ? "x" : "check")}<span>${message}</span>`;
  el.hidden = false;
  toastTimer = setTimeout(() => {
    el.classList.add("is-leaving");
    el.addEventListener("animationend", () => { el.hidden = true; }, { once: true });
  }, 2600);
}

// ── Modale de confirmation générique (aussi utilisée comme "prompt" léger) ──
function openModal({ title, text, confirmLabel = "Confirmer", danger = true, fields = [], onConfirm }) {
  const overlay = $("confirm-modal-overlay");
  $("confirm-modal-title").textContent = title;
  $("confirm-modal-text").textContent = text || "";
  $("confirm-modal-error").hidden = true;
  $("confirm-modal-error").textContent = "";

  const extra = $("confirm-modal-extra");
  extra.innerHTML = fields.map((f) => `
    <div class="form-field">
      <label for="modal-field-${f.name}">${f.label}</label>
      <input type="${f.type || "text"}" id="modal-field-${f.name}" placeholder="${f.placeholder || ""}" autocomplete="${f.autocomplete || "off"}">
    </div>
  `).join("");

  const confirmBtn = $("confirm-modal-confirm");
  confirmBtn.textContent = confirmLabel;
  confirmBtn.className = `btn ${danger ? "btn-danger-outline" : "btn-primary"}`;

  const close = () => { overlay.hidden = true; cleanup(); };
  const onConfirmClick = async () => {
    const values = {};
    for (const f of fields) values[f.name] = $(`modal-field-${f.name}`)?.value ?? "";
    confirmBtn.disabled = true;
    try {
      await onConfirm(values);
      close();
    } catch (err) {
      $("confirm-modal-error").textContent = err.message || "Une erreur est survenue.";
      $("confirm-modal-error").hidden = false;
    } finally {
      confirmBtn.disabled = false;
    }
  };
  const onCancelClick = () => close();
  const onOverlayClick = (e) => { if (e.target === overlay) close(); };

  function cleanup() {
    confirmBtn.removeEventListener("click", onConfirmClick);
    $("confirm-modal-cancel").removeEventListener("click", onCancelClick);
    overlay.removeEventListener("click", onOverlayClick);
  }

  confirmBtn.addEventListener("click", onConfirmClick);
  $("confirm-modal-cancel").addEventListener("click", onCancelClick);
  overlay.addEventListener("click", onOverlayClick);
  overlay.hidden = false;
  if (fields.length) setTimeout(() => $(`modal-field-${fields[0].name}`)?.focus(), 50);
}

// ── Sauvegarde des préférences ───────────────────────────────────────────────
// Délègue entièrement au SettingsManager global (js/settingsManager.js) :
// application immédiate (mémoire+cache+DOM+événement novamath:settings-changed
// pour que le reste du site réagisse en direct) puis persistance serveur en
// arrière-plan avec debounce — plus de logique de sauvegarde dupliquée ici.
function updateSetting(category, key, value) {
  settings = setSetting(category, key, value);
}

function updateFlatSetting(category, value) {
  settings = setSetting(category, null, value);
}

// ── Rendu : menu de gauche ───────────────────────────────────────────────────
function renderMenu() {
  menu.innerHTML = CATEGORIES().map((c) => `
    <button type="button" class="settings-menu-item${c.id === activeCategory ? " active" : ""}" data-cat="${c.id}">
      ${icon(c.icon)}<span>${c.label}</span>
    </button>
  `).join("");
  menu.querySelectorAll(".settings-menu-item").forEach((btn) => {
    btn.addEventListener("click", () => {
      activeCategory = btn.dataset.cat;
      localStorage.setItem("novamath:settings_tab", activeCategory);
      renderMenu();
      renderPanel();
    });
  });
}

// ── Helpers de rendu de contrôles ───────────────────────────────────────────
function toggleHtml(id, checked, disabled = false) {
  return `<label class="toggle-switch"><input type="checkbox" id="${id}" ${checked ? "checked" : ""} ${disabled ? "disabled" : ""}><span class="track"></span></label>`;
}

function settingRow(label, desc, controlHtml) {
  return `
    <div class="setting-row">
      <div class="setting-row-text"><span class="label">${label}</span>${desc ? `<span class="desc">${desc}</span>` : ""}</div>
      <div class="setting-row-control">${controlHtml}</div>
    </div>`;
}

function pillGroupHtml(name, options, activeValue) {
  return `<div class="choice-group" data-group="${name}">${options.map((o) => `
    <button type="button" class="choice-pill${String(o.value) === String(activeValue) ? " active" : ""}" data-value="${o.value}">${o.label}</button>
  `).join("")}</div>`;
}

function bindPillGroup(root, name, onSelect) {
  root.querySelectorAll(`[data-group="${name}"] .choice-pill`).forEach((btn) => {
    btn.addEventListener("click", () => {
      root.querySelectorAll(`[data-group="${name}"] .choice-pill`).forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      onSelect(btn.dataset.value);
    });
  });
}

function initials(name) {
  const parts = String(name || "").trim().split(/\s+/).slice(0, 2);
  return parts.map((p) => p[0]?.toUpperCase() || "").join("") || "?";
}

function guestNotice(action = "cette action") {
  return `<p class="settings-empty">Le mode invité ne permet pas ${action}. <a href="profil.html" style="color:var(--brand-indigo);">Crée un compte</a> pour en profiter.</p>`;
}

// ── 1. Compte ────────────────────────────────────────────────────────────────
function renderAccount() {
  if (user.is_guest) {
    return `
      <h2>${icon("user")} Compte</h2>
      <p class="settings-panel-desc">Tu es en mode invité : ta progression n'est pas sauvegardée durablement.</p>
      ${guestNotice("la gestion de compte")}
      <div class="settings-actions-grid">
        <a href="profil.html" class="btn btn-primary">Créer un compte</a>
      </div>

      <div class="settings-section">
        <div class="settings-section-title">Cursus</div>
        <div class="settings-actions-grid">
          <button class="btn btn-secondary" id="btn-change-class" type="button">
            <span class="class-badge-label" id="settings-class-badge-label">Seconde</span> — Changer de classe
          </button>
        </div>
      </div>
    `;
  }

  return `
    <h2>${icon("user")} Compte</h2>
    <p class="settings-panel-desc">Gère ton identité et la sécurité de ton compte Mathadap.</p>

    <div class="account-summary">
      <div class="account-summary-avatar" id="acc-avatar">${user.avatar ? `<img src="${user.avatar}" alt="">` : initials(user.pseudo)}</div>
      <div class="account-summary-meta">
        <div class="name">${user.pseudo}</div>
        <div class="sub">@${user.username}</div>
      </div>
    </div>

    <div class="account-info-grid">
      <div class="account-info-item"><div class="label">Adresse email</div><div class="value">${user.email}</div></div>
    </div>

    <div class="settings-section">
      <div class="settings-section-title">Identité</div>
      <div class="settings-actions-grid">
        <button class="btn btn-secondary" id="btn-edit-pseudo">Modifier le pseudo</button>
        <button class="btn btn-secondary" id="btn-edit-email">Modifier l'adresse Gmail</button>
        <button class="btn btn-secondary" id="btn-edit-password">Modifier le mot de passe</button>
        <button class="btn btn-secondary" id="btn-change-photo">Changer la photo</button>
      </div>
    </div>

    <div class="settings-section">
      <div class="settings-section-title">Cursus</div>
      <div class="settings-actions-grid">
        <button class="btn btn-secondary" id="btn-change-class" type="button">
          <span class="class-badge-label" id="settings-class-badge-label">Seconde</span> — Changer de classe
        </button>
      </div>
    </div>

    <input type="file" id="avatar-file-input" accept="image/png,image/jpeg,image/webp" hidden>
  `;
}

function readFileAsResizedDataUrl(file, maxSize = 480) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error("Impossible de lire ce fichier."));
    reader.onload = () => {
      const img = new Image();
      img.onerror = () => reject(new Error("Fichier image invalide."));
      img.onload = () => {
        const scale = Math.min(1, maxSize / Math.max(img.width, img.height));
        const canvas = document.createElement("canvas");
        canvas.width = Math.round(img.width * scale);
        canvas.height = Math.round(img.height * scale);
        const ctx = canvas.getContext("2d");
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
        resolve(canvas.toDataURL("image/jpeg", 0.85));
      };
      img.src = reader.result;
    };
    reader.readAsDataURL(file);
  });
}

function bindAccount() {
  // Même mécanisme que le badge de classe de la page d'accueil (voir
  // curriculumSelector.js::initClassBadge) — aucune logique de changement de
  // classe réécrite ici.
  initClassBadge($("btn-change-class"));
  if (user.is_guest) return;

  $("btn-edit-pseudo").addEventListener("click", () => {
    openModal({
      title: "Modifier le pseudo",
      confirmLabel: "Enregistrer",
      danger: false,
      fields: [{ name: "pseudo", label: "Pseudo", placeholder: user.pseudo }],
      onConfirm: async ({ pseudo }) => {
        if (!pseudo.trim()) throw new Error("Le pseudo est obligatoire.");
        const { user: updated } = await api.updateMe({ pseudo: pseudo.trim() });
        user = updated;
        window.dispatchEvent(new CustomEvent("novamath:account-updated", { detail: user }));
        renderPanel();
        showToast("Pseudo mis à jour");
      },
    });
  });

  $("btn-edit-email").addEventListener("click", () => {
    openModal({
      title: "Modifier l'adresse Gmail",
      confirmLabel: "Enregistrer",
      danger: false,
      fields: [
        { name: "email", label: "Nouvelle adresse Gmail", placeholder: "nom@gmail.com" },
        { name: "current_password", label: "Mot de passe actuel", type: "password" },
      ],
      onConfirm: async ({ email, current_password }) => {
        const { user: updated } = await api.updateMe({ email, current_password });
        user = updated;
        renderPanel();
        showToast("Adresse email mise à jour");
      },
    });
  });

  $("btn-edit-password").addEventListener("click", () => {
    openModal({
      title: "Modifier le mot de passe",
      confirmLabel: "Enregistrer",
      danger: false,
      fields: [
        { name: "current_password", label: "Mot de passe actuel", type: "password" },
        { name: "new_password", label: "Nouveau mot de passe", type: "password" },
        { name: "confirm_password", label: "Confirmer le nouveau mot de passe", type: "password" },
      ],
      onConfirm: async ({ current_password, new_password, confirm_password }) => {
        await api.changePassword({ current_password, new_password, confirm_password });
        showToast("Mot de passe mis à jour");
      },
    });
  });

  $("btn-change-photo").addEventListener("click", () => $("avatar-file-input").click());
  $("avatar-file-input").addEventListener("change", async (e) => {
    const file = e.target.files[0];
    e.target.value = "";
    if (!file) return;
    try {
      const dataUrl = await readFileAsResizedDataUrl(file);
      const { user: updated } = await api.updateMe({ avatar: dataUrl });
      user = updated;
      window.dispatchEvent(new CustomEvent("novamath:account-updated", { detail: user }));
      renderPanel();
      showToast("Photo de profil mise à jour");
    } catch (err) {
      showToast(err.message || "Échec de l'envoi de la photo.", true);
    }
  });
}

// ── 2. Apparence ─────────────────────────────────────────────────────────────
const ACCENTS = [
  { value: "purple", label: "Nova Purple" },
  { value: "blue", label: "Bleu" },
  { value: "green", label: "Vert" },
  { value: "red", label: "Rose" },
  { value: "orange", label: "Orange" },
];

function renderAppearance() {
  const a = settings.appearance;
  return `
    <h2>${icon("palette")} Apparence</h2>
    <p class="settings-panel-desc">Personnalise l'apparence de Mathadap — tout s'applique immédiatement.</p>

    <div class="settings-section">
      <div class="settings-section-title">Thème</div>
      ${pillGroupHtml("theme", [{ value: "dark", label: "Mode sombre" }, { value: "light", label: "Mode clair" }], currentTheme())}
    </div>

    <div class="settings-section">
      <div class="settings-section-title">Couleur principale</div>
      <p class="settings-panel-desc" style="margin-bottom:10px;">Violet par défaut. Change la couleur d'accent dans toute l'interface (boutons, badges, liens, états actifs, graphiques...) — les fonds et le thème clair/sombre ne changent pas.</p>
      <div class="color-swatch-group">
        ${ACCENTS.map((c) => `<button type="button" class="color-swatch swatch-${c.value}${a.accent === c.value ? " active" : ""}" data-accent="${c.value}" title="${c.label}" aria-label="${c.label}"></button>`).join("")}
      </div>
    </div>

    <div class="settings-section">
      <div class="settings-section-title">Taille du texte</div>
      ${pillGroupHtml("fontSize", [{ value: "normal", label: "Normal" }, { value: "large", label: "Grand" }], a.fontSize)}
    </div>

    <div class="settings-section">
      ${settingRow("Animations", "Transitions et animations dans toute l'interface.", toggleHtml("toggle-animations", a.animations))}
    </div>
  `;
}

function bindAppearance() {
  bindPillGroup(panel, "theme", (value) => updateSetting("appearance", "theme", value));
  bindPillGroup(panel, "fontSize", (value) => updateSetting("appearance", "fontSize", value));

  panel.querySelectorAll(".color-swatch").forEach((btn) => {
    btn.addEventListener("click", () => {
      panel.querySelectorAll(".color-swatch").forEach((s) => s.classList.remove("active"));
      btn.classList.add("active");
      updateSetting("appearance", "accent", btn.dataset.accent);
    });
  });

  $("toggle-animations").addEventListener("change", (e) => updateSetting("appearance", "animations", e.target.checked));
}

// ── 3. Entraînement ──────────────────────────────────────────────────────────
function renderTraining() {
  const t = settings.training;
  return `
    <h2>${icon("sliders")} Entraînement</h2>
    <p class="settings-panel-desc">Ajuste le déroulement de tes séries d'exercices.</p>

    <div class="settings-section">
      <div class="settings-section-title">Nombre de questions par série</div>
      ${pillGroupHtml("questionsPerSeries", [5, 10, 15, 20].map((n) => ({ value: n, label: String(n) })), t.questionsPerSeries)}
    </div>

    <div class="settings-section">
      <div class="settings-section-title">Mode de correction</div>
      ${pillGroupHtml("correctionDisplay", [{ value: "chaque_question", label: "Après chaque question" }, { value: "fin", label: "À la fin de la série" }], t.correctionDisplay)}
    </div>

    <div class="settings-section">
      ${settingRow("Chronomètre", "Limite de temps par question en mode Défi chronométré.", toggleHtml("toggle-chrono", t.chrono))}
      ${settingRow("Effets sonores", "Petits sons de confirmation en cas de bonne/mauvaise réponse.", toggleHtml("toggle-sound", t.soundEffects))}
    </div>
  `;
}

function bindTraining() {
  bindPillGroup(panel, "questionsPerSeries", (value) => updateSetting("training", "questionsPerSeries", Number(value)));
  bindPillGroup(panel, "correctionDisplay", (value) => updateSetting("training", "correctionDisplay", value));
  $("toggle-chrono").addEventListener("change", (e) => updateSetting("training", "chrono", e.target.checked));
  $("toggle-sound").addEventListener("change", (e) => updateSetting("training", "soundEffects", e.target.checked));
}

// ── 4. Apprentissage ─────────────────────────────────────────────────────────
function renderLearning() {
  const l = settings.learning;
  return `
    <h2>${icon("target")} Apprentissage</h2>
    <p class="settings-panel-desc">Rends Mathadap plus intelligent en précisant tes objectifs.</p>

    <div class="settings-section">
      <div class="settings-section-title">Objectif quotidien</div>
      <div class="setting-row">
        <div class="setting-row-text"><span class="label">Nombre d'exercices souhaités</span></div>
        <div class="setting-row-control"><input type="number" min="1" max="100" id="input-daily-exercises" value="${l.dailyGoalExercises}" style="width:80px;" class="learning-input"></div>
      </div>
      <div class="setting-row">
        <div class="setting-row-text"><span class="label">Temps quotidien (minutes)</span></div>
        <div class="setting-row-control"><input type="number" min="1" max="240" id="input-daily-time" value="${l.dailyGoalTimeMin}" style="width:80px;" class="learning-input"></div>
      </div>
    </div>

    <div class="settings-section">
      ${settingRow("Révision espacée", "Refait réapparaître les exercices déjà vus au bon moment pour mémoriser durablement.", toggleHtml("toggle-spaced", l.spacedRepetition))}
    </div>
  `;
}

function bindLearning() {
  $("input-daily-exercises").addEventListener("change", (e) => updateSetting("learning", "dailyGoalExercises", Math.max(1, Number(e.target.value) || 1)));
  $("input-daily-time").addEventListener("change", (e) => updateSetting("learning", "dailyGoalTimeMin", Math.max(1, Number(e.target.value) || 1)));
  $("toggle-spaced").addEventListener("change", (e) => updateSetting("learning", "spacedRepetition", e.target.checked));
}

// ── 5. Chatbot ───────────────────────────────────────────────────────────────
// Le fournisseur IA et le modèle sont une décision interne à Mathadap (voir
// webapp/chatbot/provider_manager.py) — jamais un réglage utilisateur, donc
// aucune trace ici : seuls les réglages de comportement restent exposés.
function renderChatbot() {
  const c = settings.chatbot || {};
  return `
    <h2>${icon("messageSquare")} Chatbot</h2>
    <p class="settings-panel-desc">Personnalise l'assistant pédagogique Mathadap — tout s'applique dès le prochain message.</p>

    <div class="settings-section">
      <div class="settings-section-title">Niveau d'explication</div>
      ${pillGroupHtml("chatbotExplanationLevel", [{ value: "auto", label: "Automatique" }, { value: "college", label: "Collège" }, { value: "lycee", label: "Lycée" }], c.explanationLevel)}
    </div>

    <div class="settings-section">
      <div class="settings-section-title">Mode</div>
      <p class="settings-panel-desc" style="margin-bottom:10px;">Change la façon dont le chatbot construit ses réponses.</p>
      ${pillGroupHtml("chatbotMode", [{ value: "professeur", label: "Professeur" }, { value: "pas_a_pas", label: "Pas-à-pas" }, { value: "rapide", label: "Rapide" }], c.mode)}
    </div>

    <div class="settings-section">
      <div class="settings-section-title">Longueur des réponses</div>
      ${pillGroupHtml("chatbotResponseLength", [{ value: "court", label: "Courtes" }, { value: "normal", label: "Normales" }, { value: "detaille", label: "Détaillées" }], c.responseLength)}
    </div>

    <div class="settings-section">
      ${settingRow("Mémoire", "Le chatbot retient tes préférences et ta progression d'une conversation à l'autre.", toggleHtml("toggle-chatbot-memory", c.memoryEnabled !== false))}
      ${settingRow("Historique", "Le chatbot relit les messages précédents de la conversation en cours.", toggleHtml("toggle-chatbot-history", c.historyEnabled !== false))}
      ${settingRow("Affichage progressif", "Les réponses s'affichent au fur et à mesure plutôt que d'un coup.", toggleHtml("toggle-chatbot-streaming", c.streaming !== false))}
    </div>
  `;
}

function bindChatbot() {
  bindPillGroup(panel, "chatbotExplanationLevel", (value) => updateSetting("chatbot", "explanationLevel", value));
  bindPillGroup(panel, "chatbotMode", (value) => updateSetting("chatbot", "mode", value));
  bindPillGroup(panel, "chatbotResponseLength", (value) => updateSetting("chatbot", "responseLength", value));
  $("toggle-chatbot-memory").addEventListener("change", (e) => updateSetting("chatbot", "memoryEnabled", e.target.checked));
  $("toggle-chatbot-history").addEventListener("change", (e) => updateSetting("chatbot", "historyEnabled", e.target.checked));
  $("toggle-chatbot-streaming").addEventListener("change", (e) => updateSetting("chatbot", "streaming", e.target.checked));
}

// ── 7. Confidentialité & Sécurité ────────────────────────────────────────────
function renderSecurity() {
  if (user.is_guest) return `<h2>${icon("lock")} Confidentialité & Sécurité</h2>${guestNotice("la gestion de la sécurité")}`;
  return `
    <h2>${icon("lock")} Confidentialité & Sécurité</h2>
    <p class="settings-panel-desc">Garde le contrôle de l'accès à ton compte.</p>

    <div class="settings-section">
      ${settingRow(
        "Authentification à deux facteurs",
        user.two_factor_enabled
          ? "Activée — un code à usage unique est demandé à chaque connexion."
          : "Protège ton compte avec un code généré par Google Authenticator, Microsoft Authenticator, Authy, 1Password ou Bitwarden.",
        user.two_factor_enabled
          ? `<button type="button" class="btn btn-danger-outline btn-sm" id="btn-2fa-disable">Désactiver</button>`
          : `<button type="button" class="btn btn-primary btn-sm" id="btn-2fa-enable">Activer</button>`
      )}
    </div>

    <div class="settings-section">
      <div class="settings-section-title">Appareils</div>
      <div class="settings-actions-grid">
        <button class="btn btn-secondary" id="btn-logout-others">Déconnecter tous les autres appareils</button>
      </div>
    </div>

    ${cookieConsentState === null ? "" : `
    <div class="settings-section">
      <div class="settings-section-title">Cookies</div>
      ${settingRow("Cookies statistiques", "Mesure d'audience anonyme pour améliorer Mathadap.", toggleHtml("toggle-cookie-statistics", cookieConsentState.statistics))}
      ${settingRow("Cookies marketing", "Personnalisation des communications Mathadap.", toggleHtml("toggle-cookie-marketing", cookieConsentState.marketing))}
    </div>`}

    <div class="settings-section">
      <div class="settings-actions-grid">
        <button class="btn btn-danger-outline" id="btn-delete-account-sec">Supprimer définitivement mon compte</button>
      </div>
    </div>
  `;
}

// ── 2FA (TOTP) — écran de configuration puis affichage unique des recovery
// codes, réutilisant uniquement js/popup.js (openPopup) et les classes déjà
// définies dans base.css/settings.css (.form-field, .btn, .verdict-row,
// .twofa-*). Jamais de nouvelle bibliothèque UI, jamais de CSS dupliqué. ────
async function open2FASetupFlow() {
  let setup;
  try {
    setup = await api.setup2FA();
  } catch (err) {
    showToast(err.message || "Impossible de démarrer la configuration.", true);
    return;
  }

  const bodyEl = document.createElement("div");
  bodyEl.innerHTML = `
    <p class="settings-panel-desc">Scanne ce QR code avec ton application d'authentification (Google Authenticator, Microsoft Authenticator, Authy, 1Password, Bitwarden...).</p>
    <div class="twofa-qr-wrap"><img src="${setup.qr_code}" alt="QR code d'activation de la double authentification" width="200" height="200"></div>
    <div class="form-field">
      <label for="twofa-secret-text">Impossible de scanner ? Saisis cette clé manuellement</label>
      <div class="twofa-secret-row">
        <code id="twofa-secret-text">${setup.secret}</code>
        <button type="button" class="btn btn-ghost btn-sm" id="btn-2fa-copy-secret" aria-label="Copier la clé">${icon("copy")}</button>
      </div>
    </div>
    <div class="form-field">
      <label for="twofa-setup-code">Code à 6 chiffres généré par l'application</label>
      <input type="text" id="twofa-setup-code" inputmode="numeric" pattern="[0-9]*" maxlength="6" autocomplete="one-time-code" placeholder="123456">
      <span class="form-error" id="twofa-setup-error" hidden></span>
    </div>
    <div class="verdict-row">
      <button type="button" class="btn btn-ghost" data-action="cancel">Annuler</button>
      <button type="button" class="btn btn-primary" data-action="confirm">Activer</button>
    </div>
  `;

  const popup = openPopup({ title: "Activer la double authentification", bodyEl, size: "sm" });
  const codeInput = bodyEl.querySelector("#twofa-setup-code");
  const errorEl = bodyEl.querySelector("#twofa-setup-error");

  bodyEl.querySelector("#btn-2fa-copy-secret").addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(setup.secret);
      showToast("Clé copiée");
    } catch {
      showToast("Copie impossible sur ce navigateur.", true);
    }
  });

  bodyEl.querySelector('[data-action="cancel"]').addEventListener("click", () => popup.close());

  async function confirmSetup() {
    errorEl.hidden = true;
    const code = codeInput.value.trim();
    if (!/^\d{6}$/.test(code)) {
      errorEl.textContent = "Saisis les 6 chiffres affichés par ton application.";
      errorEl.hidden = false;
      return;
    }
    const confirmBtn = bodyEl.querySelector('[data-action="confirm"]');
    confirmBtn.disabled = true;
    try {
      const { recovery_codes } = await api.enable2FA(code);
      user.two_factor_enabled = true;
      popup.close();
      renderPanel();
      showToast("Authentification à deux facteurs activée");
      showRecoveryCodesPopup(recovery_codes);
    } catch (err) {
      errorEl.textContent = err.message || "Code invalide.";
      errorEl.hidden = false;
    } finally {
      confirmBtn.disabled = false;
    }
  }
  bodyEl.querySelector('[data-action="confirm"]').addEventListener("click", confirmSetup);
  codeInput.addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); confirmSetup(); } });

  requestAnimationFrame(() => codeInput.focus());
}

function showRecoveryCodesPopup(codes) {
  const bodyEl = document.createElement("div");
  bodyEl.innerHTML = `
    <p class="settings-panel-desc">Conserve ces codes de récupération en lieu sûr : chacun permet de te connecter <strong>une seule fois</strong> si tu perds l'accès à ton application d'authentification. Ils ne seront plus jamais affichés.</p>
    <ul class="twofa-recovery-list">${codes.map((c) => `<li><code>${c}</code></li>`).join("")}</ul>
    <div class="verdict-row">
      <button type="button" class="btn btn-secondary" id="btn-2fa-copy-codes">${icon("copy")} Copier</button>
      <button type="button" class="btn btn-primary" id="btn-2fa-download-codes">${icon("download")} Télécharger</button>
    </div>
  `;
  // Fermeture volontairement au clic/Échap quand même autorisée (les codes
  // restent consultables ensuite via une nouvelle désactivation/activation
  // si perdus) — pas de blocage forcé qui piégerait l'utilisateur.
  const popup = openPopup({ title: "Codes de récupération", bodyEl, size: "sm" });

  bodyEl.querySelector("#btn-2fa-copy-codes").addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(codes.join("\n"));
      showToast("Codes copiés");
    } catch {
      showToast("Copie impossible sur ce navigateur.", true);
    }
  });
  bodyEl.querySelector("#btn-2fa-download-codes").addEventListener("click", () => {
    const blob = new Blob([codes.join("\n") + "\n"], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "mathadap-recovery-codes.txt";
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  });

  return popup;
}

function bindSecurity() {
  if (user.is_guest) return;

  $("btn-2fa-enable")?.addEventListener("click", () => open2FASetupFlow());
  $("btn-2fa-disable")?.addEventListener("click", () => {
    openModal({
      title: "Désactiver la double authentification",
      text: "Ton compte ne sera plus protégé par un code à usage unique. Confirme avec ton mot de passe et un code de ton application d'authentification.",
      confirmLabel: "Désactiver",
      fields: [
        { name: "password", label: "Mot de passe actuel", type: "password" },
        { name: "code", label: "Code à 6 chiffres", placeholder: "123456" },
      ],
      onConfirm: async ({ password, code }) => {
        await api.disable2FA(password, code);
        user.two_factor_enabled = false;
        renderPanel();
        showToast("Authentification à deux facteurs désactivée");
      },
    });
  });

  $("btn-logout-others").addEventListener("click", () => {
    openModal({
      title: "Déconnecter tous les autres appareils",
      text: "Toutes les sessions actives, sauf celle-ci, seront immédiatement fermées.",
      confirmLabel: "Déconnecter",
      onConfirm: async () => {
        await api.logoutOtherSessions();
        showToast("Autres appareils déconnectés");
      },
    });
  });

  if (cookieConsentState !== null) {
    $("toggle-cookie-statistics").addEventListener("change", (e) => {
      cookieConsentState = { ...cookieConsentState, statistics: e.target.checked };
      api.setCookieConsent(cookieConsentState.statistics, cookieConsentState.marketing).catch(() => {});
    });
    $("toggle-cookie-marketing").addEventListener("change", (e) => {
      cookieConsentState = { ...cookieConsentState, marketing: e.target.checked };
      api.setCookieConsent(cookieConsentState.statistics, cookieConsentState.marketing).catch(() => {});
    });
  }

  $("btn-delete-account-sec").addEventListener("click", () => {
    openModal({
      title: "Supprimer définitivement le compte",
      text: "Cette action est irréversible.",
      confirmLabel: "Supprimer mon compte",
      fields: [{ name: "password", label: "Mot de passe", type: "password" }],
      onConfirm: async ({ password }) => {
        await api.deleteMe({ password, confirm: true });
        window.location.href = "/";
      },
    });
  });
}

// ── 7. Langue ────────────────────────────────────────────────────────────────
// L'interface (menus, boutons, dashboard, paramètres, popups, messages) est
// intégralement traduite via js/i18n.js. Les énoncés des exercices restent en
// français dans tous les cas (base de contenu non traduite) — voir mention
// affichée ci-dessous en mode English.
const LANGUAGES = [
  { code: "fr", name: "Français", native: "Français" },
  { code: "en", name: "English", native: "English" },
];
// Langues prévues sur la roadmap mais pas encore traduites : affichées à
// titre indicatif, grisées et non cliquables (point 12 du cahier des
// charges), plutôt que simplement absentes.
const LANGUAGES_SOON = [
  { name: "العربية", native: "Arabe" },
  { name: "Español", native: "Espagnol" },
  { name: "Deutsch", native: "Allemand" },
];

function renderLanguage() {
  return `
    <h2>${icon("globe")} Langue</h2>
    <p class="settings-panel-desc">Choisis la langue de Mathadap.</p>
    <div class="language-grid">
      ${LANGUAGES.map((l) => `
        <button type="button" class="language-card${settings.language === l.code ? " active" : ""}" data-lang="${l.code}">
          <div class="lang-name">${l.name}</div>
          <div class="lang-native">${l.native}</div>
        </button>
      `).join("")}
      ${LANGUAGES_SOON.map((l) => `
        <button type="button" class="language-card is-disabled" disabled title="Bientôt disponible">
          <div class="lang-name">${l.name}</div>
          <div class="lang-native">${l.native} · Bientôt disponible</div>
        </button>
      `).join("")}
    </div>
    <p class="settings-panel-desc" style="margin-top:18px;">${settings.language === "en" ? "Exercise content stays in French regardless of the interface language — only the interface itself is translated." : "Le contenu des exercices reste en français quelle que soit la langue de l'interface — seule l'interface elle-même est traduite."}</p>
  `;
}

function bindLanguage() {
  panel.querySelectorAll(".language-card").forEach((btn) => {
    btn.addEventListener("click", () => {
      updateFlatSetting("language", btn.dataset.lang);
      renderPanel();
    });
  });
}

// ── 9. Aide & À propos ───────────────────────────────────────────────────────
// Contenu réel de chaque sous-page (pas de placeholder) : ouvert dans un popup
// générique (js/popup.js), donc cohérent visuellement avec le reste du site.
const HELP_PAGES = {
  faq: {
    title: "FAQ — Questions fréquentes",
    body: `
      <p><strong>Le contenu des exercices est-il disponible en anglais ?</strong><br>Non : l'interface (menus, boutons, paramètres) est traduite en anglais, mais les énoncés d'exercices restent en français.</p>
      <p><strong>Pourquoi mes préférences ne sont-elles pas sauvegardées en mode invité ?</strong><br>Un compte invité est temporaire par conception : ses données sont automatiquement supprimées à la fin de la session. Crée un compte pour conserver ta progression durablement.</p>
      <p><strong>Comment changer le nombre d'exercices par série ?</strong><br>Paramètres → Entraînement → « Nombre de questions par série ». Le changement s'applique immédiatement à toutes les prochaines séries, depuis n'importe quelle page.</p>
      <p><strong>Le chronomètre reste actif alors que je l'ai désactivé, que faire ?</strong><br>Ce comportement a été corrigé : la désactivation est désormais appliquée en direct, y compris pendant une série déjà en cours d'affichage.</p>
      <p><strong>Comment supprimer mon compte ?</strong><br>Page Profil → « Supprimer définitivement le compte ». Cette action est irréversible.</p>`,
  },
  guide: {
    title: "Guide utilisateur",
    body: `
      <p><strong>Démarrer une série</strong> — depuis Entraînement, choisis un mode (Révisions, Objectif du jour, Examen blanc, Défi chronométré, Erreurs précédentes) puis lance-la. Depuis Exercices, ouvre un chapitre, sélectionne une ou plusieurs notions puis clique sur « Commencer la série ».</p>
      <p><strong>Reprendre une série interrompue</strong> — le Dashboard affiche une carte « Continuer » tant qu'une série n'est pas terminée.</p>
      <p><strong>Personnaliser l'apparence</strong> — Paramètres → Apparence permet de changer le thème clair/sombre, la couleur d'accent, la taille du texte et les animations ; chaque changement s'applique instantanément à tout le site.</p>
      <p><strong>Suivre ses objectifs</strong> — Paramètres → Apprentissage définit l'objectif quotidien (nombre d'exercices, temps), visible en temps réel sur le Dashboard.</p>`,
  },
  privacy: {
    title: "Politique de confidentialité",
    body: `
      <p>Mathadap collecte uniquement les données nécessaires au fonctionnement du service : identifiant de compte, pseudo, adresse email, préférences, et historique d'entraînement (exercices réalisés, résultats, durée).</p>
      <p>Ces données ne sont jamais vendues ni partagées avec des tiers à des fins commerciales. Elles servent exclusivement à faire fonctionner le suivi de progression et la personnalisation de l'entraînement.</p>
      <p>Un compte invité est entièrement temporaire : ses données sont supprimées automatiquement à la fin de la session, sans action nécessaire de ta part.</p>
      <p>Tu peux à tout moment demander une copie de tes données ou la suppression définitive de ton compte (Paramètres → Compte) via la page Nous contacter.</p>`,
  },
  terms: {
    title: "Conditions générales d'utilisation",
    body: `
      <p>L'utilisation de Mathadap implique l'acceptation des présentes conditions. Le service est fourni « en l'état », à des fins d'entraînement pédagogique, sans garantie d'exhaustivité du programme scolaire.</p>
      <p>Chaque utilisateur est responsable de la confidentialité de son mot de passe. Toute utilisation frauduleuse ou automatisée (scripts, bots) du service est interdite et peut entraîner la suspension du compte.</p>
      <p>Mathadap se réserve le droit de faire évoluer les fonctionnalités du service ; les préférences et la progression des utilisateurs sont préservées lors de ces évolutions dans la mesure du possible.</p>`,
  },
};

function openHelpPage(key) {
  const page = HELP_PAGES[key];
  if (!page) return;
  import("./popup.js").then(({ openPopup }) => {
    openPopup({ title: page.title, bodyHtml: `<div class="help-page-content">${page.body}</div>`, size: "md" });
  });
}

function renderHelp() {
  return `
    <h2>${icon("helpCircle")} Aide & À propos</h2>
    <p class="settings-panel-desc">Tout savoir sur Mathadap, comment l'utiliser, et comment nous contacter.</p>

    <div class="settings-section">
      <div class="settings-section-title">Aide</div>
      <div class="help-links">
        <button class="help-link" data-help="guide">Guide utilisateur ${icon("arrowRight")}</button>
        <button class="help-link" data-help="faq">FAQ ${icon("arrowRight")}</button>
        <button class="help-link" id="help-support-link">Nous contacter ${icon("arrowRight")}</button>
      </div>
    </div>

    <div class="settings-section">
      <div class="settings-section-title">Support</div>
      <div class="help-links">
        <button class="help-link" id="help-support-my-tickets">Mes tickets ${icon("arrowRight")}</button>
        <button class="help-link" id="help-support-new-ticket">Créer un ticket ${icon("arrowRight")}</button>
      </div>
    </div>

    <div class="settings-section">
      <div class="settings-section-title">Légal</div>
      <div class="help-links">
        <button class="help-link" data-help="terms">Conditions générales d'utilisation ${icon("arrowRight")}</button>
        <button class="help-link" data-help="privacy">Politique de confidentialité ${icon("arrowRight")}</button>
      </div>
    </div>
  `;
}

function bindHelp() {
  panel.querySelectorAll("[data-help]").forEach((btn) => {
    btn.addEventListener("click", () => openHelpPage(btn.dataset.help));
  });
  $("help-support-link").addEventListener("click", () => openReportTicketPopup({ sourceLabel: "Paramètres" }));
  $("help-support-my-tickets").addEventListener("click", () => openSupportHubPopup());
  $("help-support-new-ticket").addEventListener("click", () => openReportTicketPopup({ sourceLabel: "Paramètres" }));
}

// ── Dispatch ─────────────────────────────────────────────────────────────────
const RENDERERS = {
  account: [renderAccount, bindAccount],
  appearance: [renderAppearance, bindAppearance],
  training: [renderTraining, bindTraining],
  learning: [renderLearning, bindLearning],
  chatbot: [renderChatbot, bindChatbot],
  security: [renderSecurity, bindSecurity],
  language: [renderLanguage, bindLanguage],
  help: [renderHelp, bindHelp],
};

function renderPanel() {
  const [render, bind] = RENDERERS[activeCategory] || RENDERERS.account;
  panel.innerHTML = render();
  bind();
}

/** Monte le panneau Paramètres à l'intérieur du popup ouvert par
 * js/settingsPopup.js. `container` doit déjà contenir le markup attendu
 * (settings-menu, settings-panel, confirm-modal-overlay, settings-toast) —
 * voir settingsPopup.js pour ce gabarit. Le SettingsManager global (chargé en
 * tête de chaque page) a déjà résolu les préférences avant l'ouverture du
 * popup : on les lit ici en synchrone, pas de nouvel appel réseau. */
export async function mountSettingsPanel(container) {
  panel = container.querySelector("#settings-panel");
  menu = container.querySelector("#settings-menu");
  settings = getSettings();

  try {
    const { user: u } = await api.me();
    user = u;
  } catch {
    window.location.href = "/";
    return;
  }

  renderMenu();
  renderPanel();

  if (!user.is_guest) {
    api.getCookieConsent().then((c) => { cookieConsentState = c; if (activeCategory === "security") renderPanel(); }).catch(() => {});
  }
}

// Changement de langue en direct (Paramètres → Langue) : le menu et le
// panneau du popup lui-même doivent aussi se retraduire immédiatement. Monté
// une seule fois au chargement du module (pas à chaque mountSettingsPanel)
// pour ne jamais accumuler de listeners au fil des ouvertures/fermetures du
// popup — panel/menu sont lus à l'exécution, donc toujours à jour tant que le
// popup est ouvert ; un no-op sans effet visible s'il est fermé (renderPanel
// écrirait dans un DOM détaché, sans conséquence).
onSettingsChange((e) => {
  if (e.detail.category !== "language" && e.detail.category !== "*") return;
  if (!panel || !menu) return;
  settings = getSettings();
  renderMenu();
  renderPanel();
});
