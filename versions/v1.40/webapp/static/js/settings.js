// ── Centre de personnalisation NovaMath ─────────────────────────────────────
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
import { NOVAMATH_VERSION } from "./version.js";

const $ = (id) => document.getElementById(id);
let panel, menu;

let user = null;
let settings = null;
let dataSummary = null;
let sessions = null;

function CATEGORIES() {
  return [
    { id: "account", label: t("settings.cat.account"), icon: "user" },
    { id: "appearance", label: t("settings.cat.appearance"), icon: "palette" },
    { id: "training", label: t("settings.cat.training"), icon: "sliders" },
    { id: "learning", label: t("settings.cat.learning"), icon: "target" },
    { id: "data", label: t("settings.cat.data"), icon: "database" },
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
  toastTimer = setTimeout(() => { el.hidden = true; }, 2600);
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

function formatDate(iso) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString("fr-FR", { day: "numeric", month: "long", year: "numeric" });
  } catch {
    return iso;
  }
}

function formatDuration(seconds) {
  const s = seconds || 0;
  if (s < 60) return `${s} s`;
  const h = Math.floor(s / 3600);
  const m = Math.round((s % 3600) / 60);
  return h ? `${h} h ${m} min` : `${m} min`;
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
    `;
  }

  return `
    <h2>${icon("user")} Compte</h2>
    <p class="settings-panel-desc">Gère ton identité et la sécurité de ton compte NovaMath.</p>

    <div class="account-summary">
      <div class="account-summary-avatar" id="acc-avatar">${user.avatar ? `<img src="${user.avatar}" alt="">` : initials(user.pseudo)}</div>
      <div class="account-summary-meta">
        <div class="name">${user.pseudo}</div>
        <div class="sub">@${user.username}</div>
      </div>
    </div>

    <div class="account-info-grid">
      <div class="account-info-item"><div class="label">Adresse email</div><div class="value">${user.email}</div></div>
      <div class="account-info-item"><div class="label">Compte vérifié</div><div class="value">${user.email_verified ? icon("check") + " Vérifié" : "Non vérifié"}</div></div>
      <div class="account-info-item"><div class="label">Date de création</div><div class="value">${formatDate(user.created_at)}</div></div>
      <div class="account-info-item"><div class="label">Identifiant utilisateur</div><div class="value">#${user.id}</div></div>
    </div>

    <div class="settings-section">
      <div class="settings-section-title">Identité</div>
      <div class="settings-actions-grid">
        <button class="btn btn-secondary" id="btn-edit-pseudo">Modifier le pseudo</button>
        <button class="btn btn-secondary" id="btn-edit-email">Modifier l'adresse Gmail</button>
        <button class="btn btn-secondary" id="btn-edit-password">Modifier le mot de passe</button>
        <button class="btn btn-secondary" id="btn-change-photo">Changer la photo</button>
        <button class="btn btn-secondary" id="btn-remove-photo" ${user.avatar ? "" : "disabled"}>Supprimer la photo</button>
      </div>
    </div>

    <div class="settings-section danger-zone">
      <div class="settings-section-title">Zone sensible</div>
      <div class="settings-actions-grid">
        <button class="btn btn-danger-outline" id="btn-logout">Déconnexion</button>
        <button class="btn btn-danger-outline" id="btn-delete-account">Supprimer définitivement le compte</button>
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

  $("btn-remove-photo").addEventListener("click", () => {
    openModal({
      title: "Supprimer la photo de profil",
      text: "Ta photo sera remplacée par tes initiales. Cette action est réversible en ajoutant une nouvelle photo.",
      confirmLabel: "Supprimer",
      onConfirm: async () => {
        const { user: updated } = await api.updateMe({ avatar: null });
        user = updated;
        window.dispatchEvent(new CustomEvent("novamath:account-updated", { detail: user }));
        renderPanel();
        showToast("Photo supprimée");
      },
    });
  });

  $("btn-logout").addEventListener("click", () => {
    openModal({
      title: "Se déconnecter",
      text: "Tu devras te reconnecter pour retrouver ta progression sur cet appareil.",
      confirmLabel: "Déconnexion",
      danger: false,
      onConfirm: async () => {
        await api.logout();
        window.location.href = "/";
      },
    });
  });

  $("btn-delete-account").addEventListener("click", () => {
    openModal({
      title: "Supprimer définitivement le compte",
      text: "Cette action est irréversible : toute ta progression, tes statistiques et tes préférences seront supprimées.",
      confirmLabel: "Supprimer mon compte",
      fields: [{ name: "password", label: "Mot de passe", type: "password" }],
      onConfirm: async ({ password }) => {
        await api.deleteMe({ password, confirm: true });
        window.location.href = "/";
      },
    });
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
    <p class="settings-panel-desc">Personnalise l'apparence de NovaMath — tout s'applique immédiatement.</p>

    <div class="settings-section">
      <div class="settings-section-title">Thème</div>
      ${pillGroupHtml("theme", [{ value: "dark", label: "Mode sombre" }, { value: "light", label: "Mode clair" }], currentTheme())}
    </div>

    <div class="settings-section">
      <div class="settings-section-title">Couleur principale</div>
      <div class="color-swatch-group">
        ${ACCENTS.map((c) => `<button type="button" class="color-swatch swatch-${c.value}${a.accent === c.value ? " active" : ""}" data-accent="${c.value}" title="${c.label}" aria-label="${c.label}"></button>`).join("")}
      </div>
    </div>

    <div class="settings-section">
      <div class="settings-section-title">Taille du texte</div>
      ${pillGroupHtml("fontSize", [{ value: "small", label: "Petit" }, { value: "normal", label: "Normal" }, { value: "large", label: "Grand" }], a.fontSize)}
    </div>

    <div class="settings-section">
      <div class="settings-section-title">Coins des cartes</div>
      ${pillGroupHtml("radius", [{ value: "normal", label: "Normaux" }, { value: "rounded", label: "Très arrondis" }], a.radius)}
    </div>

    <div class="settings-section">
      ${settingRow("Animations", "Transitions et animations dans toute l'interface.", toggleHtml("toggle-animations", a.animations))}
      ${settingRow("Effet de transparence", "Surfaces vitrées (cartes, fenêtres) légèrement transparentes.", toggleHtml("toggle-transparency", a.transparency))}
    </div>
  `;
}

function bindAppearance() {
  bindPillGroup(panel, "theme", (value) => updateSetting("appearance", "theme", value));
  bindPillGroup(panel, "fontSize", (value) => updateSetting("appearance", "fontSize", value));
  bindPillGroup(panel, "radius", (value) => updateSetting("appearance", "radius", value));

  panel.querySelectorAll(".color-swatch").forEach((btn) => {
    btn.addEventListener("click", () => {
      panel.querySelectorAll(".color-swatch").forEach((s) => s.classList.remove("active"));
      btn.classList.add("active");
      updateSetting("appearance", "accent", btn.dataset.accent);
    });
  });

  $("toggle-animations").addEventListener("change", (e) => updateSetting("appearance", "animations", e.target.checked));
  $("toggle-transparency").addEventListener("change", (e) => updateSetting("appearance", "transparency", e.target.checked));
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
      ${settingRow("Chronomètre", "Limite de temps par question en mode Défi chronométré.", toggleHtml("toggle-chrono", t.chrono))}
      ${settingRow("Confirmation avant de quitter une série", "Une fenêtre te demande confirmation si tu quittes en cours de série.", toggleHtml("toggle-confirm-leave", t.confirmBeforeLeave))}
      ${settingRow("Reprendre automatiquement une série interrompue", "Sinon, NovaMath te demande avant de reprendre.", toggleHtml("toggle-auto-resume", t.autoResume))}
      ${settingRow("Afficher automatiquement la correction", "La méthode s'affiche juste après chaque réponse, sans clic.", toggleHtml("toggle-auto-correction", t.autoShowCorrection))}
      ${settingRow("Effets sonores", "Petits sons de confirmation en cas de bonne/mauvaise réponse.", toggleHtml("toggle-sound", t.soundEffects))}
    </div>
  `;
}

function bindTraining() {
  bindPillGroup(panel, "questionsPerSeries", (value) => updateSetting("training", "questionsPerSeries", Number(value)));
  $("toggle-chrono").addEventListener("change", (e) => updateSetting("training", "chrono", e.target.checked));
  $("toggle-confirm-leave").addEventListener("change", (e) => updateSetting("training", "confirmBeforeLeave", e.target.checked));
  $("toggle-auto-resume").addEventListener("change", (e) => updateSetting("training", "autoResume", e.target.checked));
  $("toggle-auto-correction").addEventListener("change", (e) => updateSetting("training", "autoShowCorrection", e.target.checked));
  $("toggle-sound").addEventListener("change", (e) => updateSetting("training", "soundEffects", e.target.checked));
}

// ── 4. Apprentissage ─────────────────────────────────────────────────────────
function renderLearning() {
  const l = settings.learning;
  return `
    <h2>${icon("target")} Apprentissage</h2>
    <p class="settings-panel-desc">Rends NovaMath plus intelligent en précisant tes objectifs.</p>

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
      <div class="setting-row">
        <div class="setting-row-text"><span class="label">Accuracy cible</span><span class="desc">Sur 20, comme au dashboard (ex. 18/20)</span></div>
        <div class="setting-row-control"><input type="number" min="0" max="20" step="0.5" id="input-target-accuracy" value="${l.targetAccuracyOn20}" style="width:80px;" class="learning-input"></div>
      </div>
    </div>

    <div class="settings-section">
      ${settingRow("Prioriser les notions faibles", "Les exercices proposés favorisent tes notions les moins maîtrisées.", toggleHtml("toggle-prioritize-weak", l.prioritizeWeakNotions))}
      ${settingRow("Prioriser les chapitres non maîtrisés", "", toggleHtml("toggle-prioritize-chapters", l.prioritizeUnmasteredChapters))}
      ${settingRow("Révision espacée", "Refait réapparaître les exercices déjà vus au bon moment pour mémoriser durablement.", toggleHtml("toggle-spaced", l.spacedRepetition))}
    </div>

    <div class="settings-section">
      <div class="settings-section-title">Afficher des indices pendant les exercices</div>
      ${pillGroupHtml("hints", [{ value: "jamais", label: "Jamais" }, { value: "parfois", label: "Parfois" }, { value: "toujours", label: "Toujours" }], l.hints)}
    </div>

    <div class="settings-section">
      <div class="settings-section-title">Afficher la correction</div>
      ${pillGroupHtml("correctionDisplay", [{ value: "fin", label: "Uniquement à la fin" }, { value: "chaque_question", label: "Après chaque question" }], l.correctionDisplay)}
    </div>
  `;
}

function bindLearning() {
  $("input-daily-exercises").addEventListener("change", (e) => updateSetting("learning", "dailyGoalExercises", Math.max(1, Number(e.target.value) || 1)));
  $("input-daily-time").addEventListener("change", (e) => updateSetting("learning", "dailyGoalTimeMin", Math.max(1, Number(e.target.value) || 1)));
  $("input-target-accuracy").addEventListener("change", (e) => updateSetting("learning", "targetAccuracyOn20", Math.min(20, Math.max(0, Number(e.target.value) || 0))));
  $("toggle-prioritize-weak").addEventListener("change", (e) => updateSetting("learning", "prioritizeWeakNotions", e.target.checked));
  $("toggle-prioritize-chapters").addEventListener("change", (e) => updateSetting("learning", "prioritizeUnmasteredChapters", e.target.checked));
  $("toggle-spaced").addEventListener("change", (e) => updateSetting("learning", "spacedRepetition", e.target.checked));
  bindPillGroup(panel, "hints", (value) => updateSetting("learning", "hints", value));
  bindPillGroup(panel, "correctionDisplay", (value) => updateSetting("learning", "correctionDisplay", value));
}

// ── 5. Données ───────────────────────────────────────────────────────────────
function renderData() {
  if (user.is_guest) return `<h2>${icon("database")} Données</h2>${guestNotice("la gestion des données")}`;
  const d = dataSummary || {};
  return `
    <h2>${icon("database")} Données</h2>
    <p class="settings-panel-desc">Ta progression, en chiffres.</p>

    <div class="data-stats-grid">
      <div class="data-stat-card"><div class="value">${d.totalExercises ?? "—"}</div><div class="label">Exercices réalisés</div></div>
      <div class="data-stat-card"><div class="value">${d.accuracy ?? 0}%</div><div class="label">Accuracy</div></div>
      <div class="data-stat-card"><div class="value">${formatDuration(d.totalTimeS)}</div><div class="label">Temps d'entraînement</div></div>
      <div class="data-stat-card"><div class="value">${d.seriesCount ?? 0}</div><div class="label">Séries</div></div>
      <div class="data-stat-card"><div class="value" style="font-size:1rem;">${formatDate(d.memberSince)}</div><div class="label">Première connexion</div></div>
    </div>

    <div class="settings-section">
      <div class="settings-section-title">Exporter</div>
      <div class="settings-actions-grid">
        <button class="btn btn-secondary" id="btn-export-pdf">${icon("fileText")} Exporter mon rapport (PDF)</button>
      </div>
    </div>

    <div class="settings-section danger-zone">
      <div class="settings-section-title">Zone sensible</div>
      <div class="settings-actions-grid">
        <button class="btn btn-danger-outline" id="btn-reset-stats">Réinitialiser les statistiques</button>
        <button class="btn btn-danger-outline" id="btn-reset-progress">Réinitialiser entièrement ma progression</button>
      </div>
    </div>
  `;
}

function bindData() {
  if (user.is_guest) return;
  $("btn-export-pdf").addEventListener("click", async () => {
    const btn = $("btn-export-pdf");
    btn.disabled = true;
    const original = btn.textContent;
    btn.textContent = "Génération du PDF…";
    try {
      const { exportProgressPdf } = await import("./pdfExport.js");
      await exportProgressPdf();
      showToast("Rapport PDF téléchargé");
    } catch {
      showToast("Échec de l'export PDF.", true);
    } finally {
      btn.disabled = false;
      btn.innerHTML = `${icon("fileText")} Exporter mon rapport (PDF)`;
    }
  });

  const doReset = (label) => openModal({
    title: label,
    text: "Cette action est irréversible : XP, historique, séries et badges seront remis à zéro.",
    confirmLabel: "Réinitialiser",
    onConfirm: async () => {
      await api.resetProgress();
      dataSummary = await api.getDataSummary().catch(() => dataSummary);
      renderPanel();
      showToast("Progression réinitialisée");
    },
  });
  $("btn-reset-stats").addEventListener("click", () => doReset("Réinitialiser les statistiques"));
  $("btn-reset-progress").addEventListener("click", () => doReset("Réinitialiser entièrement ma progression"));
}

// ── 6. Chatbot ───────────────────────────────────────────────────────────────
const CHATBOT_PROVIDERS = [
  { value: "ollama", label: "Ollama (local, par défaut)" },
  { value: "anthropic", label: "Claude (Anthropic)" },
  { value: "openai", label: "OpenAI (bientôt disponible)", disabled: true },
  { value: "gemini", label: "Gemini (bientôt disponible)", disabled: true },
];
// Catalogue de secours (utilisé tant que /api/chatbot/models n'a pas encore
// répondu, ou si le fournisseur actif est indisponible) — la vraie liste des
// modèles est détectée dynamiquement (voir loadChatbotModels ci-dessous).
const CHATBOT_MODELS_FALLBACK = {
  ollama: [{ value: "mistral", label: "Mistral (par défaut)" }],
  anthropic: [
    { value: "claude-sonnet-5", label: "Claude Sonnet 5 (équilibré)" },
    { value: "claude-opus-4-8", label: "Claude Opus 4.8 (le plus capable)" },
    { value: "claude-haiku-4-5-20251001", label: "Claude Haiku 4.5 (le plus rapide)" },
  ],
};
let chatbotModelsInfo = null; // { provider, models: {id: label} } — voir loadChatbotModels()

function loadChatbotModels() {
  api.chatbotModels().then((info) => {
    chatbotModelsInfo = info;
    if (activeCategory === "chatbot") renderPanel();
  }).catch(() => {});
}

function chatbotModelsForProvider(provider) {
  if (chatbotModelsInfo && chatbotModelsInfo.provider === provider) {
    const entries = Object.entries(chatbotModelsInfo.models || {});
    if (entries.length) return entries.map(([value, label]) => ({ value, label }));
  }
  return CHATBOT_MODELS_FALLBACK[provider] || [];
}

function renderChatbot() {
  const c = settings.chatbot || {};
  const provider = c.provider || "ollama";
  const models = chatbotModelsForProvider(provider);
  return `
    <h2>${icon("messageSquare")} Chatbot</h2>
    <p class="settings-panel-desc">Personnalise l'assistant pédagogique NovaMath — tout s'applique dès le prochain message.</p>

    <div class="settings-section">
      <div class="settings-section-title">Fournisseur IA</div>
      <p class="settings-panel-desc" style="margin-bottom:10px;">Ollama (modèle local Mistral) est le fournisseur par défaut : aucune donnée n'est envoyée à une API cloud. Architecture prête pour en accueillir d'autres (OpenAI, Gemini…) sans changement du reste du site.</p>
      <div class="choice-group" data-group="chatbotProvider">
        ${CHATBOT_PROVIDERS.map((p) => `<button type="button" class="choice-pill${p.value === provider ? " active" : ""}" data-value="${p.value}" ${p.disabled ? "disabled" : ""}>${p.label}</button>`).join("")}
      </div>
      <div class="settings-section-title" style="margin-top:18px;">Modèle</div>
      <div class="choice-group" data-group="chatbotModel">
        ${models.map((m) => `<button type="button" class="choice-pill${m.value === c.model ? " active" : ""}" data-value="${m.value}">${m.label}</button>`).join("")}
      </div>
      ${provider === "ollama" ? `<p class="settings-panel-desc" style="margin-top:8px;">Modèles détectés automatiquement dans Ollama (<code>ollama list</code>). Installe-en d'autres avec <code>ollama pull &lt;modèle&gt;</code>, puis rouvre ce panneau.</p>` : ""}
    </div>

    <div class="settings-section">
      <div class="settings-section-title">Créativité</div>
      <div class="setting-row">
        <div class="setting-row-text"><span class="label">Température (${c.temperature ?? 0.6})</span><span class="desc">Plus basse = réponses plus factuelles, plus haute = plus créatives.</span></div>
        <div class="setting-row-control"><input type="range" min="0" max="1" step="0.1" id="range-chatbot-temperature" value="${c.temperature ?? 0.6}"></div>
      </div>
    </div>

    <div class="settings-section">
      <div class="settings-section-title">Longueur des réponses</div>
      ${pillGroupHtml("chatbotResponseLength", [{ value: "court", label: "Court" }, { value: "normal", label: "Normal" }, { value: "detaille", label: "Détaillé" }], c.responseLength)}
    </div>

    <div class="settings-section">
      <div class="settings-section-title">Niveau d'explication</div>
      ${pillGroupHtml("chatbotExplanationLevel", [{ value: "auto", label: "Automatique" }, { value: "college", label: "Collège" }, { value: "lycee", label: "Lycée" }, { value: "expert", label: "Expert" }], c.explanationLevel)}
    </div>

    <div class="settings-section">
      ${settingRow("Streaming", "Affiche la réponse au fur et à mesure qu'elle est générée.", toggleHtml("toggle-chatbot-streaming", c.streaming))}
      ${settingRow("Historique", "Le chatbot garde le fil de la conversation en cours.", toggleHtml("toggle-chatbot-history", c.historyEnabled))}
      ${settingRow("Mémoire", "Le chatbot tient compte de ta progression NovaMath (niveau, notions faibles, chapitres en cours).", toggleHtml("toggle-chatbot-memory", c.memoryEnabled))}
    </div>
  `;
}

function bindChatbot() {
  bindPillGroup(panel, "chatbotProvider", (value) => {
    updateSetting("chatbot", "provider", value);
    updateSetting("chatbot", "model", chatbotModelsForProvider(value)[0]?.value || "");
    loadChatbotModels();
    renderPanel();
  });
  bindPillGroup(panel, "chatbotModel", (value) => updateSetting("chatbot", "model", value));
  $("range-chatbot-temperature").addEventListener("input", (e) => updateSetting("chatbot", "temperature", Number(e.target.value)));
  $("range-chatbot-temperature").addEventListener("change", () => renderPanel());
  bindPillGroup(panel, "chatbotResponseLength", (value) => updateSetting("chatbot", "responseLength", value));
  bindPillGroup(panel, "chatbotExplanationLevel", (value) => updateSetting("chatbot", "explanationLevel", value));
  $("toggle-chatbot-streaming").addEventListener("change", (e) => updateSetting("chatbot", "streaming", e.target.checked));
  $("toggle-chatbot-history").addEventListener("change", (e) => updateSetting("chatbot", "historyEnabled", e.target.checked));
  $("toggle-chatbot-memory").addEventListener("change", (e) => updateSetting("chatbot", "memoryEnabled", e.target.checked));
}

// ── 7. Confidentialité & Sécurité ────────────────────────────────────────────
function deviceLabel(ua) {
  if (/mobile/i.test(ua)) return "Mobile";
  if (/tablet|ipad/i.test(ua)) return "Tablette";
  return "Ordinateur";
}

function renderSecurity() {
  if (user.is_guest) return `<h2>${icon("lock")} Confidentialité & Sécurité</h2>${guestNotice("la gestion de la sécurité")}`;
  const list = sessions || [];
  return `
    <h2>${icon("lock")} Confidentialité & Sécurité</h2>
    <p class="settings-panel-desc">Garde le contrôle de l'accès à ton compte.</p>

    <div class="settings-section">
      ${settingRow("Authentification à deux facteurs", "Sécurité renforcée par code à usage unique.", `<span class="settings-badge-soon">Bientôt disponible</span>`)}
    </div>

    <div class="settings-section">
      <div class="settings-section-title">Appareils connectés</div>
      <div class="device-list">
        ${list.map((s) => `
          <div class="device-item">
            <span class="device-icon">${icon("monitor")}</span>
            <div class="device-item-text">
              <div class="ua">${deviceLabel(s.user_agent)}${s.current ? " · Cet appareil" : ""}</div>
              <div class="meta">Connecté depuis le ${formatDate(s.created_at)}</div>
            </div>
          </div>
        `).join("") || `<p class="settings-empty">Aucun appareil actif.</p>`}
      </div>
      <div class="settings-actions-grid">
        <button class="btn btn-secondary" id="btn-logout-others">Déconnecter tous les autres appareils</button>
      </div>
    </div>

    <div class="settings-section">
      <div class="settings-section-title">Dernière connexion</div>
      <div class="account-info-grid">
        <div class="account-info-item"><div class="label">Date</div><div class="value">${formatDate(user.last_login_at)}</div></div>
      </div>
    </div>

    <div class="settings-section">
      <div class="settings-actions-grid">
        <button class="btn btn-danger-outline" id="btn-delete-account-sec">Supprimer définitivement mon compte</button>
      </div>
    </div>
  `;
}

function bindSecurity() {
  if (user.is_guest) return;

  $("btn-logout-others").addEventListener("click", () => {
    openModal({
      title: "Déconnecter tous les autres appareils",
      text: "Toutes les sessions actives, sauf celle-ci, seront immédiatement fermées.",
      confirmLabel: "Déconnecter",
      onConfirm: async () => {
        await api.logoutOtherSessions();
        sessions = await api.getSessions().then((r) => r.sessions).catch(() => sessions);
        renderPanel();
        showToast("Autres appareils déconnectés");
      },
    });
  });

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
    <p class="settings-panel-desc">Choisis la langue de NovaMath.</p>
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
  presentation: {
    title: "Présentation de NovaMath",
    body: `
      <p>NovaMath est une plateforme française d'entraînement aux mathématiques, conçue pour accompagner les élèves du secondaire dans la maîtrise progressive du programme, chapitre par chapitre et notion par notion.</p>
      <p>La plateforme s'appuie sur une base de plus de 2000 exercices répartis sur 12 chapitres et 51 notions, avec 5 niveaux de difficulté, pour proposer un entraînement réellement adapté au niveau de chaque élève plutôt qu'un contenu générique.</p>
      <p>Chaque série d'exercices est suivie d'une correction détaillée, d'indices contextuels et d'un suivi de progression (précision, temps, régularité) afin de transformer l'entraînement en une boucle de progrès mesurable.</p>`,
  },
  mission: {
    title: "Notre mission",
    body: `
      <p>Rendre l'entraînement aux mathématiques aussi efficace que possible, en combinant trois principes : <strong>la répétition ciblée</strong> (travailler en priorité ce qui n'est pas encore maîtrisé), <strong>la mesure honnête</strong> (des statistiques de progression fidèles, jamais gonflées) et <strong>l'autonomie</strong> (un élève doit pouvoir comprendre pourquoi il se trompe, pas seulement le savoir).</p>
      <p>NovaMath n'a pas vocation à remplacer un enseignant : c'est un outil d'entraînement complémentaire, pensé pour le travail personnel entre les cours.</p>`,
  },
  fonctionnement: {
    title: "Comment fonctionne NovaMath",
    body: `
      <p><strong>1. Évaluation initiale.</strong> Un court test de positionnement estime ton niveau de départ.</p>
      <p><strong>2. Entraînement ciblé.</strong> Depuis Exercices ou Entraînement, tu lances des séries d'exercices dont le nombre, le chronomètre et le comportement suivent tes préférences définies dans Paramètres → Entraînement — quel que soit l'endroit d'où tu les lances.</p>
      <p><strong>3. Correction et indices.</strong> Chaque exercice propose un indice, une méthode détaillée et une solution, pour comprendre plutôt que deviner.</p>
      <p><strong>4. Suivi de progression.</strong> Le Dashboard centralise ton niveau, ton XP, ta précision, ton objectif quotidien et ton historique récent.</p>`,
  },
  faq: {
    title: "FAQ — Questions fréquentes",
    body: `
      <p><strong>Le contenu des exercices est-il disponible en anglais ?</strong><br>Non : l'interface (menus, boutons, paramètres) est traduite en anglais, mais les énoncés d'exercices restent en français.</p>
      <p><strong>Pourquoi mes préférences ne sont-elles pas sauvegardées en mode invité ?</strong><br>Un compte invité est temporaire par conception : ses données sont automatiquement supprimées à la fin de la session. Crée un compte pour conserver ta progression durablement.</p>
      <p><strong>Comment changer le nombre d'exercices par série ?</strong><br>Paramètres → Entraînement → « Nombre de questions par série ». Le changement s'applique immédiatement à toutes les prochaines séries, depuis n'importe quelle page.</p>
      <p><strong>Le chronomètre reste actif alors que je l'ai désactivé, que faire ?</strong><br>Ce comportement a été corrigé : la désactivation est désormais appliquée en direct, y compris pendant une série déjà en cours d'affichage.</p>
      <p><strong>Comment supprimer mon compte ?</strong><br>Paramètres → Compte → Zone sensible → « Supprimer définitivement le compte ». Cette action est irréversible.</p>`,
  },
  guide: {
    title: "Guide utilisateur",
    body: `
      <p><strong>Démarrer une série</strong> — depuis Entraînement, choisis un mode (Révisions, Objectif du jour, Examen blanc, Défi chronométré, Erreurs précédentes) puis lance-la. Depuis Exercices, ouvre un chapitre, sélectionne une ou plusieurs notions puis clique sur « Commencer la série ».</p>
      <p><strong>Reprendre une série interrompue</strong> — le Dashboard affiche une carte « Continuer » tant qu'une série n'est pas terminée.</p>
      <p><strong>Personnaliser l'apparence</strong> — Paramètres → Apparence permet de changer le thème clair/sombre, la couleur d'accent, la taille du texte, la transparence et les animations ; chaque changement s'applique instantanément à tout le site.</p>
      <p><strong>Suivre ses objectifs</strong> — Paramètres → Apprentissage définit l'objectif quotidien (nombre d'exercices, temps), visible en temps réel sur le Dashboard.</p>
      <p><strong>Exporter ses données</strong> — Paramètres → Données → « Exporter mon rapport (PDF) » génère un rapport complet et imprimable de ta progression.</p>`,
  },
  contact: {
    title: "Nous contacter",
    body: `
      <p>Le moyen le plus rapide de nous joindre est la section Avis de la page d'accueil, consultée en priorité par l'équipe.</p>
      <p>Pour un bug ou une suggestion, décris précisément le contexte (page, action effectuée, comportement attendu) : cela accélère beaucoup la résolution.</p>`,
  },
  privacy: {
    title: "Politique de confidentialité",
    body: `
      <p>NovaMath collecte uniquement les données nécessaires au fonctionnement du service : identifiant de compte, pseudo, adresse email, préférences, et historique d'entraînement (exercices réalisés, résultats, durée).</p>
      <p>Ces données ne sont jamais vendues ni partagées avec des tiers à des fins commerciales. Elles servent exclusivement à faire fonctionner le suivi de progression et la personnalisation de l'entraînement.</p>
      <p>Un compte invité est entièrement temporaire : ses données sont supprimées automatiquement à la fin de la session, sans action nécessaire de ta part.</p>
      <p>Tu peux à tout moment consulter, exporter (Paramètres → Données) ou supprimer définitivement (Paramètres → Compte) tes données.</p>`,
  },
  terms: {
    title: "Conditions générales d'utilisation",
    body: `
      <p>L'utilisation de NovaMath implique l'acceptation des présentes conditions. Le service est fourni « en l'état », à des fins d'entraînement pédagogique, sans garantie d'exhaustivité du programme scolaire.</p>
      <p>Chaque utilisateur est responsable de la confidentialité de son mot de passe. Toute utilisation frauduleuse ou automatisée (scripts, bots) du service est interdite et peut entraîner la suspension du compte.</p>
      <p>NovaMath se réserve le droit de faire évoluer les fonctionnalités du service ; les préférences et la progression des utilisateurs sont préservées lors de ces évolutions dans la mesure du possible.</p>`,
  },
  legal: {
    title: "Mentions légales",
    body: `
      <p>NovaMath est un service édité à des fins pédagogiques. Les contenus mathématiques (énoncés, corrections) sont produits ou vérifiés par l'équipe éditoriale de NovaMath.</p>
      <p>Le nom « NovaMath » et le logo associé sont la propriété de l'éditeur du service. Toute reproduction non autorisée est interdite.</p>`,
  },
  cookies: {
    title: "Gestion des cookies",
    body: `
      <p>NovaMath utilise un cookie de session strictement nécessaire à l'authentification (maintien de la connexion) ainsi qu'un cookie technique anti-CSRF, indispensables au fonctionnement du service — ils ne peuvent pas être désactivés sans empêcher la connexion.</p>
      <p>Aucun cookie publicitaire ou de traçage tiers n'est utilisé. Les préférences d'interface (thème, couleur, langue…) sont stockées localement dans ton navigateur (localStorage), jamais partagées.</p>`,
  },
  roadmap: {
    title: "Roadmap",
    body: `
      <p><strong>Récemment livré :</strong> centre de paramètres unifié en popup, thème et couleur d'accent propagés à tout le site, export PDF du rapport de progression, interface bilingue français/anglais.</p>
      <p><strong>À venir :</strong> traduction complète de la base d'exercices, authentification à deux facteurs, rapport enseignant, certificats de progression.</p>
      <p>Cette roadmap est indicative et peut évoluer selon les retours des utilisateurs (section Avis).</p>`,
  },
  credits: {
    title: "Crédits, technologies & licences",
    body: `
      <p><strong>Technologies utilisées :</strong> Flask (backend Python), JavaScript vanilla en modules ES (frontend, sans framework), SQLite pour le stockage.</p>
      <p><strong>Bibliothèques tierces :</strong></p>
      <p>— <strong>KaTeX</strong> (rendu des formules mathématiques) — licence MIT.<br>— <strong>jsPDF</strong> (génération de l'export PDF) — licence MIT.</p>
      <p>NovaMath n'utilise aucune dépendance propriétaire : l'ensemble des bibliothèques tierces est open source.</p>`,
  },
  security: {
    title: "Sécurité",
    body: `
      <p>Les mots de passe sont stockés sous forme hachée (Argon2), jamais en clair. Les sessions sont protégées par cookies sécurisés et une protection CSRF par double-soumission de jeton.</p>
      <p>Aucune donnée de paiement n'est collectée par NovaMath.</p>`,
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
    <p class="settings-panel-desc">Tout savoir sur NovaMath, comment l'utiliser, et comment nous contacter.</p>

    <div class="settings-section">
      <div class="settings-section-title">NovaMath</div>
      <div class="help-links">
        <button class="help-link" data-help="presentation">Présentation NovaMath ${icon("arrowRight")}</button>
        <button class="help-link" data-help="mission">Notre mission ${icon("arrowRight")}</button>
        <button class="help-link" data-help="fonctionnement">Comment ça fonctionne ${icon("arrowRight")}</button>
        <button class="help-link" data-help="roadmap">Roadmap ${icon("arrowRight")}</button>
        <button class="help-link" data-help="credits">Crédits & technologies ${icon("arrowRight")}</button>
      </div>
    </div>

    <div class="settings-section">
      <div class="settings-section-title">Aide</div>
      <div class="help-links">
        <button class="help-link" data-help="guide">Guide utilisateur ${icon("arrowRight")}</button>
        <button class="help-link" data-help="faq">FAQ ${icon("arrowRight")}</button>
        <button class="help-link" id="help-support-link">Support & nous contacter ${icon("arrowRight")}</button>
      </div>
    </div>

    <div class="settings-section">
      <div class="settings-section-title">Légal</div>
      <div class="help-links">
        <button class="help-link" data-help="terms">Conditions générales d'utilisation ${icon("arrowRight")}</button>
        <button class="help-link" data-help="privacy">Politique de confidentialité ${icon("arrowRight")}</button>
        <button class="help-link" data-help="cookies">Gestion des cookies ${icon("arrowRight")}</button>
        <button class="help-link" data-help="legal">Mentions légales ${icon("arrowRight")}</button>
        <button class="help-link" data-help="security">Sécurité ${icon("arrowRight")}</button>
      </div>
    </div>

    <div class="settings-section" style="margin-top:8px;">
      <div class="account-info-grid">
        <div class="account-info-item"><div class="label">Version actuelle</div><div class="value">NovaMath v${NOVAMATH_VERSION}</div></div>
      </div>
      <div class="settings-actions-grid" style="margin-top:14px;">
        <button class="btn btn-secondary" id="btn-check-updates">${icon("refreshCcw")} Vérifier les mises à jour</button>
      </div>
    </div>
  `;
}

function bindHelp() {
  panel.querySelectorAll("[data-help]").forEach((btn) => {
    btn.addEventListener("click", () => openHelpPage(btn.dataset.help));
  });
  $("help-support-link").addEventListener("click", () => openHelpPage("contact"));
  $("btn-check-updates").addEventListener("click", () => showToast(`Tu utilises déjà la dernière version (NovaMath v${NOVAMATH_VERSION}).`));
}

// ── Dispatch ─────────────────────────────────────────────────────────────────
const RENDERERS = {
  account: [renderAccount, bindAccount],
  appearance: [renderAppearance, bindAppearance],
  training: [renderTraining, bindTraining],
  learning: [renderLearning, bindLearning],
  data: [renderData, bindData],
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
    api.getDataSummary().then((d) => { dataSummary = d; if (activeCategory === "data") renderPanel(); }).catch(() => {});
    api.getSessions().then((r) => { sessions = r.sessions; if (activeCategory === "security") renderPanel(); }).catch(() => {});
  }
  loadChatbotModels();
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
