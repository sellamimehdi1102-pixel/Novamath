// Module "Paramètres" (/admin/settings) — centre de configuration. Toutes
// les données viennent de settings_service.py (voir GET
// /api/admin/settings/overview) : {available:false, reason:"..."} = jamais
// fabriqué, `enforced:false` = persisté mais pas encore réellement appliqué
// par le code (voir sa docstring) — toujours affiché tel quel, jamais caché.
//
// Structure : catégories repliables (.admin-collapse, voir admin-collapse.js)
// + recherche texte. La section "Général" (réglage `language`) a été
// supprimée : audit round 2, aucun code ne lisait jamais cette clé (contrat
// `enforced:true` trompeur) — comme les anciennes sections Comptes/Apparence
// et les 13 réglages jamais consommés ailleurs, déjà supprimés lors du
// premier chantier de simplification (voir settings_service.py pour le
// détail).
//
// Audit admin (2026-10-22), point 1 (Paramètres) : le système de favoris
// (étoile par catégorie + filtre + localStorage) a été entièrement supprimé
// — jugé disproportionné pour seulement 4 catégories, un simple repli
// suffit. La recherche texte reste seule (utile pour retrouver un champ
// précis). Le repli est désormais fixe : "IA & Clés API" ouverte par défaut,
// les 3 autres catégories fermées par défaut, sans persistance d'aucune
// sorte (voir CATEGORIES ci-dessous — seule "ai" porte `open: true`).
import { createCollapseSection, wireCollapsePersistence } from "./admin-collapse.js";
import { confirmDialog, showToast } from "./admin-ui-kit.js";

const EMPTY_LABEL = "Cette fonctionnalité n'est pas encore alimentée.";

const LABELS = {
  ai_temperature_default: "Température par défaut",
  ai_max_response_tokens_default: "Nombre maximal de tokens par réponse",
  ai_fallback_enabled: "Fallback automatique",
};

// Petite phrase affichée sous chaque champ important — jamais de jargon
// technique brut, toujours une explication en une ligne (partie 6 du
// chantier de refonte de la page Paramètres).
const FIELD_DESCRIPTIONS = {
  ai_temperature_default:
    "Contrôle la créativité des réponses IA : une valeur basse privilégie des réponses prévisibles, une valeur haute des réponses plus variées.",
  ai_max_response_tokens_default: "Longueur maximale d'une réponse générée par l'IA.",
  ai_fallback_enabled:
    "Active le basculement automatique vers un autre fournisseur IA si le fournisseur principal échoue.",
};

const SAVED_LABEL = "✓ Enregistré";

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function readCookie(name) {
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

async function apiCall(path, { method = "GET", body } = {}) {
  const csrfToken = method !== "GET" ? readCookie("nm_csrf") : null;
  const res = await fetch(path, {
    method,
    headers: { "Content-Type": "application/json", ...(csrfToken ? { "X-CSRF-Token": csrfToken } : {}) },
    credentials: "same-origin",
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  const payload = await res.json().catch(() => ({}));
  return { ok: res.ok, status: res.status, payload };
}

function formatDateTime(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString("fr-FR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatBytes(bytes) {
  if (bytes === null || bytes === undefined) return "—";
  if (bytes < 1024) return `${bytes} o`;
  if (bytes < 1024 ** 2) return `${(bytes / 1024).toFixed(1)} Ko`;
  if (bytes < 1024 ** 3) return `${(bytes / 1024 ** 2).toFixed(1)} Mo`;
  return `${(bytes / 1024 ** 3).toFixed(2)} Go`;
}

function metricCard(label, metric, formatter = (v) => v, clamp = false) {
  const card = el("article", "admin-card");
  card.appendChild(el("div", "admin-card-label", label));
  if (!metric || !metric.available) {
    card.appendChild(el("div", "admin-card-value admin-card-value--empty", EMPTY_LABEL));
    if (metric && metric.reason) card.appendChild(el("div", "admin-card-sub", metric.reason));
  } else {
    const text = String(formatter(metric.value));
    const valueEl = el("div", clamp ? "admin-card-value admin-clamp-3" : "admin-card-value", text);
    if (clamp) valueEl.title = text;
    card.appendChild(valueEl);
  }
  return card;
}

// Audit admin (2026-10-22) : l'ancienne liste à plat des fournisseurs IA
// (nom/priorité/badge Actif-Secours) dupliquait, en lecture seule et sans
// aucune action, ce que la page /admin/ia affiche déjà avec en plus la
// gestion complète (créer/modifier/activer/réordonner/tester). Remplacée
// par un simple lien — aucune capacité n'est perdue puisque cette liste
// n'exposait elle-même aucune action.
function providersLink() {
  const card = el("article", "admin-card");
  card.appendChild(el("div", "admin-card-label", "Fournisseurs IA"));
  const link = el("a", "admin-card-value", "Gérer les fournisseurs IA (créer, modifier, priorités, clés API) →");
  link.href = "/admin/ia";
  card.appendChild(link);
  return card;
}

// ── Section éditable "Général" (restreinte à `language`) ────────────────────
function settingField(setting) {
  const field = el(
    "div",
    "admin-form-field" + (setting.type === "str" && setting.max_len > 100 ? " admin-form-field--full" : ""),
  );
  const label = el("label", "admin-form-label", LABELS[setting.key] || setting.key);
  label.htmlFor = `admin-settings-field-${setting.key}`;
  field.appendChild(label);

  let input;
  if (setting.type === "bool") {
    const toggleLabel = el("label", "admin-toggle");
    input = document.createElement("input");
    input.type = "checkbox";
    input.checked = Boolean(setting.value);
    toggleLabel.appendChild(input);
    toggleLabel.appendChild(el("span", "admin-toggle-track"));
    field.appendChild(toggleLabel);
  } else if (setting.type === "enum") {
    input = document.createElement("select");
    input.className = "admin-form-select";
    setting.choices.forEach((choice) => input.appendChild(new Option(choice, choice)));
    input.value = setting.value;
    field.appendChild(input);
  } else if (setting.type === "int") {
    input = document.createElement("input");
    input.type = "number";
    input.className = "admin-form-input";
    input.min = setting.min;
    input.max = setting.max;
    input.value = setting.value;
    field.appendChild(input);
  } else if (setting.type === "float") {
    input = document.createElement("input");
    input.type = "number";
    input.step = "0.05";
    input.className = "admin-form-input";
    input.min = setting.min;
    input.max = setting.max;
    input.value = setting.value;
    field.appendChild(input);
  } else if (setting.type === "color") {
    input = document.createElement("input");
    input.type = "color";
    input.className = "admin-form-input";
    input.value = setting.value;
    field.appendChild(input);
  } else {
    input = document.createElement("input");
    input.type = "text";
    input.className = "admin-form-input";
    input.maxLength = setting.max_len || 300;
    input.value = setting.value || "";
    field.appendChild(input);
  }
  input.id = `admin-settings-field-${setting.key}`;
  input.dataset.key = setting.key;
  input.dataset.type = setting.type;

  const description = FIELD_DESCRIPTIONS[setting.key];
  if (description) field.appendChild(el("p", "admin-form-hint", description));

  if (setting.source === "database" && setting.updated_at) {
    field.appendChild(el("p", "admin-form-hint", `Modifié le ${formatDateTime(setting.updated_at)}`));
  }
  return field;
}

function readFieldValue(input) {
  if (input.dataset.type === "bool") return input.checked;
  if (input.dataset.type === "int" || input.dataset.type === "float") return Number(input.value);
  return input.value;
}

function renderSettingsForm(form, settingsMap, patchPath) {
  form.innerHTML = "";
  Object.values(settingsMap).forEach((setting) => form.appendChild(settingField(setting)));
  const actionsRow = el("div", "admin-section-head-row");
  const submitBtn = el("button", "admin-btn admin-btn--primary", "Enregistrer");
  submitBtn.type = "submit";
  actionsRow.appendChild(submitBtn);
  const savedEl = el("span", "admin-badge admin-badge--ok", SAVED_LABEL);
  savedEl.hidden = true;
  actionsRow.appendChild(savedEl);
  form.appendChild(actionsRow);
  const errorEl = el("p", "admin-form-error");
  errorEl.hidden = true;
  form.appendChild(errorEl);

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    errorEl.hidden = true;
    savedEl.hidden = true;
    const data = {};
    form.querySelectorAll("[data-key]").forEach((input) => {
      data[input.dataset.key] = readFieldValue(input);
    });
    submitBtn.disabled = true;
    const { ok, payload } = await apiCall(patchPath, { method: "PATCH", body: data });
    submitBtn.disabled = false;
    if (!ok) {
      errorEl.hidden = false;
      errorEl.textContent = payload.error
        ? `${payload.error} ${payload.fields ? JSON.stringify(payload.fields) : ""}`
        : "Impossible d'enregistrer.";
      return;
    }
    renderSettingsForm(form, payload, patchPath);
    const refreshedSaved = form.querySelector(".admin-badge--ok");
    if (refreshedSaved) {
      refreshedSaved.hidden = false;
      setTimeout(() => {
        refreshedSaved.hidden = true;
      }, 2500);
    }
  });
}

// ── IA — réglages réellement éditables (température/tokens/fallback, lus par
// llm_fallback_service.py à chaque appel LLM). Retry/cache retirés (chantier
// de simplification) : constantes techniques jamais consultées par un admin,
// jamais des réglages. La gestion des fournisseurs (liste/CRUD/priorités)
// vit uniquement dans /admin/ia (voir providersLink ci-dessus). ───────────
function renderAi(form, infoContainer, ai) {
  const settingsMap = {
    ai_temperature_default: ai.temperature_default,
    ai_max_response_tokens_default: ai.max_response_tokens_default,
    ai_fallback_enabled: ai.fallback_enabled,
  };
  renderSettingsForm(form, settingsMap, "/api/admin/settings/ai");

  infoContainer.innerHTML = "";
  infoContainer.appendChild(providersLink());
}

// ── Clés API ──────────────────────────────────────────────────────────────────
// Finalisation du nettoyage admin (2026-10-22) : la gestion complète des
// clés API (liste, création, renommage/priorité, test, suppression) est
// désormais centralisée dans /admin/ia (voir admin-ai.js, `allowEdit: true`
// activé là-bas — vérifié : aucune des routes /api/admin/ai/keys/* n'exige
// SUPER_ADMIN, toutes sont gardées par le même rôle ADMIN). Cette page ne
// garde plus qu'un lien compact vers /admin/ia (voir CATEGORIES ci-dessous,
// catégorie "ai") — plus aucun formulaire de création ni tableau ici.

// ── Email (SMTP) + Paiements (Stripe) ─────────────────────────────────────────
function metricValue(metric, formatter = (v) => v) {
  return metric && metric.available ? formatter(metric.value) : "—";
}

// Audit admin (2026-10-20) : "mode" distingue désormais explicitement les 4
// états réels (jamais fusionnés) — TEST/PRODUCTION ne sont pas le même
// niveau d'alerte que ÉTAT INCONNU (clé présente mais préfixe non reconnu,
// une anomalie à vérifier) ni que NON CONFIGURÉ (rien à configurer, normal
// en développement). `stripe.configured` (booléen explicite du backend)
// remplace l'ancienne déduction via `stripe.mode.available`, qui confondait
// à tort "non configuré" et "état inconnu".
const STRIPE_MODE_LABELS = {
  test: "TEST",
  production: "PRODUCTION",
  non_configure: "NON CONFIGURÉ",
  etat_inconnu: "ÉTAT INCONNU",
};
const STRIPE_MODE_DOT_STATE = {
  test: "warning",
  production: "ok",
  non_configure: "down",
  etat_inconnu: "warning",
};

// Audit admin (2026-10-22), point 3 (Paramètres) : Stripe (3 lignes, lecture
// seule) fusionné dans LA MÊME carte que SMTP plutôt que 2 sous-sections
// avec leurs propres titres <h3> — les deux conteneurs `#admin-settings-smtp`
// et `#admin-settings-stripe` sont conservés (mêmes ids qu'avant ce
// chantier) comme simples sous-blocs de cette carte unique, pour ne jamais
// casser un repère existant. Les bandeaux d'avertissement critiques (mode
// TEST / état inconnu) restent AUSSI visibles qu'avant — jamais noyés dans
// la fusion, toujours juste après les lignes Stripe.
function renderIntegrations(container, smtp, stripe) {
  container.innerHTML = "";

  const card = el("article", "admin-card");
  card.appendChild(el("div", "admin-card-label", "Email & Paiements (SMTP + Stripe)"));

  const mode = metricValue(stripe.mode);
  const modeLabel = STRIPE_MODE_LABELS[mode] || "—";
  const dotState = STRIPE_MODE_DOT_STATE[mode] || "down";
  const smtpConfigured = smtp.configured;

  const dots = el("div", "admin-integrations-dots");
  dots.appendChild(
    el(
      "span",
      `admin-status-dot admin-status-dot--${smtpConfigured ? "ok" : "down"}`,
      smtpConfigured ? "SMTP configuré" : "SMTP non configuré",
    ),
  );
  dots.appendChild(el("span", `admin-status-dot admin-status-dot--${dotState}`, `Stripe ${modeLabel}`));
  card.appendChild(dots);

  const smtpWrap = el("div", "admin-kv-list");
  smtpWrap.id = "admin-settings-smtp";
  [
    ["Serveur SMTP", metricValue(smtp.host)],
    ["Port SMTP", metricValue(smtp.port)],
    ["Utilisateur SMTP", metricValue(smtp.username)],
    ["Chiffrement SMTP", metricValue(smtp.encryption)],
    ["Expéditeur SMTP", metricValue(smtp.from_address)],
  ].forEach(([k, v]) => {
    const row = el("div", "admin-kv-row");
    row.appendChild(el("span", "admin-kv-label", k));
    row.appendChild(el("span", "admin-kv-value", String(v)));
    smtpWrap.appendChild(row);
  });
  card.appendChild(smtpWrap);
  card.appendChild(el("p", "admin-form-hint", smtp.env_controlled_reason));

  const stripeWrap = el("div", "admin-kv-list");
  stripeWrap.id = "admin-settings-stripe";
  [
    ["Mode Stripe", modeLabel],
    ["Clés Stripe configurées", stripe.configured ? "Oui" : "Non"],
    ["Webhook Stripe", stripe.webhook_configured ? "Configuré" : "Non configuré"],
  ].forEach(([k, v]) => {
    const row = el("div", "admin-kv-row");
    row.appendChild(el("span", "admin-kv-label", k));
    row.appendChild(el("span", "admin-kv-value", String(v)));
    stripeWrap.appendChild(row);
  });
  card.appendChild(stripeWrap);
  if (mode === "test") {
    stripeWrap.appendChild(
      el(
        "p",
        "admin-form-hint admin-form-hint--warning",
        "Mode TEST : aucun paiement réel n'est traité, ne jamais présenter ces données comme des revenus réels.",
      ),
    );
  }
  if (mode === "etat_inconnu") {
    stripeWrap.appendChild(
      el(
        "p",
        "admin-form-hint admin-form-hint--warning",
        "La clé Stripe configurée ne correspond à aucun préfixe Stripe connu (ni sk_test_ ni sk_live_) — à vérifier.",
      ),
    );
  }
  stripeWrap.appendChild(el("p", "admin-form-hint", stripe.env_controlled_reason));
  card.appendChild(stripeWrap);
  container.appendChild(card);

  const testCard = el("article", "admin-card");
  testCard.appendChild(el("div", "admin-card-label", "Dernier test d'envoi SMTP"));
  const lastTestOk = smtp.last_test_ok && smtp.last_test_ok.available ? smtp.last_test_ok.value : null;
  const hasTest = smtp.last_test_at && smtp.last_test_at.available;
  testCard.appendChild(
    el(
      "span",
      `admin-status-dot admin-status-dot--${hasTest ? (lastTestOk ? "ok" : "down") : "unknown"}`,
      hasTest ? (lastTestOk ? "Succès" : "Échec") : "Aucun test",
    ),
  );
  if (hasTest) testCard.appendChild(el("div", "admin-card-sub", formatDateTime(smtp.last_test_at.value)));
  if (!lastTestOk && smtp.last_test_error && smtp.last_test_error.available) {
    testCard.appendChild(el("div", "admin-card-sub", smtp.last_test_error.value));
  }
  container.appendChild(testCard);
}

// ── Sauvegardes ───────────────────────────────────────────────────────────────
// Refonte complète (voir plan) : haut de page réduit à 3 informations de
// décision (dernière sauvegarde/taille totale/espace disque) + un seul
// bouton d'action ; le nom de fichier n'apparaît plus jamais dans une carte
// (uniquement dans le tableau, où l'espace disponible permet un retour à la
// ligne propre, et en tooltip). Recherche/tri/filtre de période/pagination
// sont appliqués côté client (le nombre de sauvegardes est borné par
// backup_service.MAX_BACKUPS = 30, donc sans besoin d'un nouvel endpoint
// paginé côté serveur).
const BACKUPS_PAGE_SIZE = 8;

function renderBackupsStats(container, backups) {
  container.innerHTML = "";

  const lastCard = el("article", "admin-card");
  lastCard.appendChild(el("div", "admin-card-label", "Dernière sauvegarde"));
  const lastBackup = backups.last_backup;
  if (!lastBackup.available) {
    lastCard.appendChild(el("div", "admin-card-value admin-card-value--empty", EMPTY_LABEL));
    lastCard.appendChild(el("div", "admin-card-sub", lastBackup.reason));
  } else {
    const lines = el("div", "admin-backups-stat-lines");
    lines.appendChild(el("div", "admin-card-value", formatDateTime(lastBackup.value.created_at)));
    lines.appendChild(el("div", "admin-card-sub", formatBytes(lastBackup.value.size_bytes)));
    if (backups.last_backup_successful.available) {
      const ok = backups.last_backup_successful.value;
      lines.appendChild(
        el("span", `admin-status-dot admin-status-dot--${ok ? "ok" : "down"}`, ok ? "Réussie" : "Échec depuis"),
      );
    }
    lastCard.appendChild(lines);
  }
  container.appendChild(lastCard);

  container.appendChild(
    metricCard("Taille totale des sauvegardes", { available: true, value: backups.total_size_bytes }, formatBytes),
  );

  // Audit admin (2026-10-22) : la carte "Espace disque utilisé" (pourcentage
  // + barre de progression) a été retirée — elle dépendait de
  // backups.disk_total_bytes, volontairement retiré de
  // system_health_service.storage_info() (voir settings_service.py::
  // ai_config — même principe appliqué ici). `disk_total_bytes.available`
  // étant TOUJOURS false, la branche else ci-dessous n'était jamais
  // atteinte : cette carte n'affichait plus que "Aucune donnée disponible"
  // en permanence. L'équivalent réel (disk_used_bytes seul, sans
  // pourcentage) reste affiché sur la page Santé (voir admin-health.js) —
  // aucune information n'est perdue, jamais recalculée ici.
}

function renderBackupsBanner(container, backups) {
  container.innerHTML = "";
  if (!backups.last_error_at.available) return;
  const banner = el(
    "div",
    "admin-banner admin-banner--error",
    `Dernier échec de sauvegarde le ${formatDateTime(backups.last_error_at.value)}${backups.last_error.available ? ` — ${backups.last_error.value}` : ""}`,
  );
  container.appendChild(banner);
}

const BACKUPS_PERIOD_PREDICATES = {
  all: () => true,
  today: (iso) => new Date(iso).toDateString() === new Date().toDateString(),
  "7d": (iso) => Date.now() - new Date(iso).getTime() <= 7 * 86400000,
  "30d": (iso) => Date.now() - new Date(iso).getTime() <= 30 * 86400000,
};

function filterAndSortBackups(items, { search, period, sortBy, sortDir }) {
  const query = search.trim().toLowerCase();
  const predicate = BACKUPS_PERIOD_PREDICATES[period] || BACKUPS_PERIOD_PREDICATES.all;
  const filtered = items.filter((b) => (!query || b.filename.toLowerCase().includes(query)) && predicate(b.created_at));
  const sorted = [...filtered].sort((a, b) => {
    const av = sortBy === "filename" ? a.filename.toLowerCase() : a[sortBy];
    const bv = sortBy === "filename" ? b.filename.toLowerCase() : b[sortBy];
    if (av < bv) return sortDir === "asc" ? -1 : 1;
    if (av > bv) return sortDir === "asc" ? 1 : -1;
    return 0;
  });
  return sorted;
}

function buildKebabMenu(actions) {
  const wrap = el("div", "admin-kebab");
  const btn = el("button", "admin-kebab-btn", "⋮");
  btn.type = "button";
  btn.setAttribute("aria-label", "Actions");
  const menu = el("div", "admin-kebab-menu");
  menu.hidden = true;
  actions.forEach((action) => {
    if (action.href) {
      const link = document.createElement("a");
      link.href = action.href;
      link.className = "admin-kebab-item";
      link.textContent = action.label;
      link.download = action.download || "";
      menu.appendChild(link);
      return;
    }
    const item = el("button", `admin-kebab-item${action.danger ? " admin-kebab-item--danger" : ""}`, action.label);
    item.type = "button";
    item.addEventListener("click", async () => {
      menu.hidden = true;
      await action.onClick();
    });
    menu.appendChild(item);
  });
  btn.addEventListener("click", (e) => {
    e.stopPropagation();
    document.querySelectorAll(".admin-kebab-menu").forEach((m) => {
      if (m !== menu) m.hidden = true;
    });
    menu.hidden = !menu.hidden;
  });
  document.addEventListener("click", () => {
    menu.hidden = true;
  });
  wrap.appendChild(btn);
  wrap.appendChild(menu);
  return wrap;
}

function buildBackupRow(b, isCurrent, onChanged) {
  const tr = document.createElement("tr");
  const nameTd = el("td", "admin-users-td admin-users-td--wrap", b.filename);
  nameTd.title = b.filename;
  tr.appendChild(nameTd);
  tr.appendChild(el("td", "admin-users-td", formatDateTime(b.created_at)));
  tr.appendChild(el("td", "admin-users-td", formatBytes(b.size_bytes)));

  const statusTd = document.createElement("td");
  statusTd.className = "admin-users-td";
  statusTd.appendChild(
    el(
      "span",
      `admin-badge ${isCurrent ? "admin-badge--ok" : "admin-badge--neutral"}`,
      isCurrent ? "Actuelle" : "Archivée",
    ),
  );
  tr.appendChild(statusTd);

  const actionsTd = document.createElement("td");
  actionsTd.className = "admin-users-td";
  actionsTd.appendChild(
    buildKebabMenu([
      {
        label: "Télécharger",
        href: `/api/admin/settings/backups/${encodeURIComponent(b.filename)}/download`,
        download: b.filename,
      },
      {
        label: "Restaurer",
        danger: true,
        onClick: async () => {
          const confirmed = await confirmDialog({
            title: "Restaurer cette sauvegarde ?",
            text: `La base de données actuelle sera écrasée par « ${b.filename} ». Une copie de sécurité de l'état actuel est prise automatiquement avant l'opération.`,
            confirmLabel: "Restaurer",
          });
          if (!confirmed) return;
          const { ok, payload } = await apiCall(
            `/api/admin/settings/backups/${encodeURIComponent(b.filename)}/restore`,
            { method: "POST" },
          );
          if (!ok) {
            showToast(payload.error || "Restauration impossible.", true);
            return;
          }
          showToast("Restauration effectuée avec succès.");
          onChanged();
        },
      },
      {
        label: "Supprimer",
        danger: true,
        onClick: async () => {
          const confirmed = await confirmDialog({
            title: "Supprimer cette sauvegarde ?",
            text: `« ${b.filename} » sera définitivement supprimée. Cette action est irréversible.`,
            confirmLabel: "Supprimer",
          });
          if (!confirmed) return;
          const { ok, payload } = await apiCall(`/api/admin/settings/backups/${encodeURIComponent(b.filename)}`, {
            method: "DELETE",
          });
          if (!ok) {
            showToast(payload.error || "Suppression impossible.", true);
            return;
          }
          showToast("Sauvegarde supprimée avec succès.");
          onChanged();
        },
      },
    ]),
  );
  tr.appendChild(actionsTd);
  return tr;
}

function renderBackupsPagination(container, page, totalPages, totalCount, onPageChange) {
  container.innerHTML = "";
  if (totalCount === 0) return;
  container.appendChild(
    el("span", "admin-users-pagination-info", `Page ${page} / ${totalPages} · ${totalCount} sauvegarde(s)`),
  );
  const prev = el("button", "admin-icon-btn admin-users-page-btn", "‹");
  prev.type = "button";
  prev.disabled = page <= 1;
  prev.setAttribute("aria-label", "Page précédente");
  prev.addEventListener("click", () => onPageChange(page - 1));
  container.appendChild(prev);
  const next = el("button", "admin-icon-btn admin-users-page-btn", "›");
  next.type = "button";
  next.disabled = page >= totalPages;
  next.setAttribute("aria-label", "Page suivante");
  next.addEventListener("click", () => onPageChange(page + 1));
  container.appendChild(next);
}

function renderBackupsTableHead(theadRow, sortBy, sortDir) {
  theadRow.querySelectorAll("th[data-sort]").forEach((th) => {
    th.classList.remove("is-sorted-asc", "is-sorted-desc");
    if (th.dataset.sort === sortBy) th.classList.add(sortDir === "asc" ? "is-sorted-asc" : "is-sorted-desc");
  });
}

function createBackupsController({ tbody, emptyEl, paginationEl, theadRow, searchInput, periodButtons }) {
  const state = { raw: [], search: "", period: "all", sortBy: "created_at", sortDir: "desc", page: 1 };
  let mostRecentFilename = null;
  let onChanged = () => {};

  function render() {
    renderBackupsTableHead(theadRow, state.sortBy, state.sortDir);
    const filtered = filterAndSortBackups(state.raw, state);
    const totalPages = Math.max(1, Math.ceil(filtered.length / BACKUPS_PAGE_SIZE));
    if (state.page > totalPages) state.page = totalPages;
    const start = (state.page - 1) * BACKUPS_PAGE_SIZE;
    const pageItems = filtered.slice(start, start + BACKUPS_PAGE_SIZE);

    tbody.innerHTML = "";
    pageItems.forEach((b) => tbody.appendChild(buildBackupRow(b, b.filename === mostRecentFilename, onChanged)));

    emptyEl.hidden = filtered.length > 0;
    if (filtered.length === 0) {
      emptyEl.textContent =
        state.raw.length === 0
          ? "Aucune sauvegarde n'existe. Cliquez sur « Créer une sauvegarde » ci-dessus pour en générer une."
          : "Aucune sauvegarde ne correspond à la recherche ou au filtre sélectionné.";
    }
    renderBackupsPagination(paginationEl, state.page, totalPages, filtered.length, (page) => {
      state.page = page;
      render();
    });
  }

  theadRow.querySelectorAll("th[data-sort]").forEach((th) => {
    th.classList.add("is-sortable");
    th.addEventListener("click", () => {
      const key = th.dataset.sort;
      if (state.sortBy === key) {
        state.sortDir = state.sortDir === "asc" ? "desc" : "asc";
      } else {
        state.sortBy = key;
        state.sortDir = "asc";
      }
      state.page = 1;
      render();
    });
  });

  searchInput.addEventListener("input", () => {
    state.search = searchInput.value;
    state.page = 1;
    render();
  });

  periodButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      periodButtons.forEach((b) => b.classList.remove("is-active"));
      btn.classList.add("is-active");
      state.period = btn.dataset.period;
      state.page = 1;
      render();
    });
  });

  return {
    setItems(items, changedCallback) {
      state.raw = items;
      mostRecentFilename = items.length ? items[0].filename : null;
      onChanged = changedCallback;
      render();
    },
  };
}

// ── Sécurité & Logs (lecture seule) ───────────────────────────────────────────
// Audit admin (2026-10-22), point 2 (Paramètres) : les 5 cartes Sécurité +
// les 2 champs Logs (7 informations au total, toutes en LECTURE SEULE —
// aucune route d'écriture n'existe pour elles côté backend, voir
// security_info()/logs_info() dans settings_service.py, jamais modifié par
// ce chantier) sont fusionnées en UNE SEULE carte compacte "Sécurité & Logs"
// avec 7 lignes clé/valeur, sans sous-titres séparés.
function renderSecurity(container, security, logs) {
  container.innerHTML = "";
  const card = el("article", "admin-card");
  card.appendChild(el("div", "admin-card-label", "Sécurité & Logs"));
  const kv = el("div", "admin-kv-list");
  const twoFa = metricValue(security.two_factor_admins);
  const csp = metricValue(security.csp);
  const sessions = metricValue(security.session_durations);
  const attempts = metricValue(security.login_attempts);
  [
    ["2FA administrateurs", twoFa !== "—" ? `${twoFa.enabled} / ${twoFa.total}` : "—"],
    [
      "CSP",
      csp !== "—" ? `${csp.enabled ? "Activée" : "Désactivée"}${csp.report_only ? " (mode rapport seul)" : ""}` : "—",
    ],
    [
      "Durée des sessions",
      sessions !== "—"
        ? `Par défaut ${sessions.default_days} j · Se souvenir : ${sessions.remember_me_days} j · Invité : ${sessions.guest_days} j`
        : "—",
    ],
    [
      "Tentatives de connexion",
      attempts !== "—" ? `${attempts.max_attempts} max · verrouillage ${attempts.lockout_minutes} min` : "—",
    ],
    ["HSTS", metricValue(security.hsts_enabled, (v) => (v ? "Activé" : "Désactivé"))],
    ["Niveau de log", metricValue(logs.level)],
    ["Sentry", metricValue(logs.sentry_enabled, (v) => (v ? "Activé" : "Désactivé"))],
  ].forEach(([k, v]) => {
    const row = el("div", "admin-kv-row");
    row.appendChild(el("span", "admin-kv-label", k));
    row.appendChild(el("span", "admin-kv-value", String(v)));
    kv.appendChild(row);
  });
  card.appendChild(kv);
  card.appendChild(el("p", "admin-form-hint", logs.level_env_controlled_reason));
  container.appendChild(card);
}

// ── Catégories repliables (admin-collapse.js) ────────────────────────────────
// Chaque catégorie = un <details class="admin-collapse"> (voir
// buildCategories, plus bas — plus aucune étoile de favori injectée dans le
// titre, voir point 1 de l'audit 2026-10-22). "IA & Clés API" est ouverte
// par défaut, les 3 autres repliées par défaut, sans persistance de favoris.
const CATEGORIES = [
  {
    id: "ai",
    title: "IA & Clés API",
    open: true,
    bodyHtml: `
      <form class="admin-settings-rows" id="admin-settings-ai-form"></form>
      <div class="admin-settings-grid" id="admin-settings-ai-info"></div>
      <h3 class="admin-settings-subtitle">Clés API</h3>
      <p class="admin-form-hint">
        La gestion complète des clés API (création, modification, priorité, activation, test, suppression) est
        centralisée dans <a href="/admin/ia">IA → Clés API (haute disponibilité)</a>.
      </p>
    `,
  },
  {
    id: "smtp",
    title: "Intégrations",
    bodyHtml: `
      <div class="admin-section-head-row">
        <button type="button" class="admin-btn admin-btn--sm" id="admin-settings-smtp-test-btn">Tester l'envoi</button>
      </div>
      <p class="admin-form-hint">Envoie un vrai email de test à l'administrateur connecté pour vérifier la configuration SMTP.</p>
      <div class="admin-settings-grid" id="admin-settings-integrations"></div>
    `,
  },
  {
    id: "backups",
    title: "Sauvegardes",
    bodyHtml: `
      <div class="admin-backups-top">
        <div class="admin-settings-grid" id="admin-settings-backups-stats"></div>
        <button type="button" class="admin-btn admin-btn--primary" id="admin-settings-backup-create-btn">Créer une sauvegarde</button>
      </div>
      <div id="admin-settings-backups-banner"></div>
      <div class="admin-backups-toolbar">
        <div class="admin-users-search">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/></svg>
          <input type="search" id="admin-settings-backups-search" placeholder="Rechercher un fichier…" aria-label="Rechercher une sauvegarde">
        </div>
        <div class="admin-segmented" id="admin-settings-backups-period" role="group" aria-label="Filtrer par période">
          <button type="button" class="admin-segmented-btn is-active" data-period="all">Toutes</button>
          <button type="button" class="admin-segmented-btn" data-period="today">Aujourd'hui</button>
          <button type="button" class="admin-segmented-btn" data-period="7d">7 jours</button>
          <button type="button" class="admin-segmented-btn" data-period="30d">30 jours</button>
        </div>
      </div>
      <div class="admin-users-table-wrap">
        <table class="admin-users-table" id="admin-settings-backups-table">
          <thead><tr id="admin-settings-backups-thead-row">
            <th class="admin-users-th" data-sort="filename">Nom</th>
            <th class="admin-users-th" data-sort="created_at">Date</th>
            <th class="admin-users-th" data-sort="size_bytes">Taille</th>
            <th class="admin-users-th">Statut</th>
            <th class="admin-users-th">Actions</th>
          </tr></thead>
          <tbody id="admin-settings-backups-tbody"></tbody>
        </table>
      </div>
      <p class="admin-empty" id="admin-settings-backups-empty" hidden></p>
      <nav class="admin-users-pagination" id="admin-settings-backups-pagination" aria-label="Pagination des sauvegardes"></nav>
    `,
  },
  {
    id: "security",
    title: "Sécurité / Logs",
    bodyHtml: `
      <div class="admin-settings-grid" id="admin-settings-security"></div>
    `,
  },
];

// Audit admin (2026-10-22), point 1 (Paramètres) : système de favoris
// (readFavorites/writeFavorites/starGlyph/wireFavorites + filtre dédié)
// entièrement supprimé — disproportionné pour seulement 4 catégories.
// buildCategories() ne construit plus que le titre brut de chaque catégorie
// (jamais une étoile injectée), et wireFilters() ne gère plus que la
// recherche texte, conservée seule.
function buildCategories(root) {
  root.innerHTML = CATEGORIES.map((cat) =>
    createCollapseSection({
      id: `settings-${cat.id}`,
      title: cat.title,
      open: Boolean(cat.open),
      bodyHtml: cat.bodyHtml,
    }),
  ).join("");
  wireCollapsePersistence(root);
}

// ── Recherche texte ───────────────────────────────────────────────────────────
function wireFilters(root, searchInput) {
  function apply() {
    const query = searchInput.value.trim().toLowerCase();
    root.querySelectorAll(".admin-collapse[data-collapse-id]").forEach((section) => {
      section.hidden = Boolean(query) && !section.textContent.toLowerCase().includes(query);
    });
  }
  searchInput.addEventListener("input", apply);
}

// ── Chargement complet ────────────────────────────────────────────────────────
export async function loadSettings() {
  const errorEl = document.getElementById("admin-global-error");
  const categoriesRoot = document.getElementById("admin-settings-categories");
  buildCategories(categoriesRoot);

  const aiForm = document.getElementById("admin-settings-ai-form");
  const aiInfoEl = document.getElementById("admin-settings-ai-info");
  const integrationsEl = document.getElementById("admin-settings-integrations");
  const backupsStatsEl = document.getElementById("admin-settings-backups-stats");
  const backupsBannerEl = document.getElementById("admin-settings-backups-banner");
  const backupsTbody = document.getElementById("admin-settings-backups-tbody");
  const backupsEmptyEl = document.getElementById("admin-settings-backups-empty");
  const backupsPaginationEl = document.getElementById("admin-settings-backups-pagination");
  const backupsTheadRow = document.getElementById("admin-settings-backups-thead-row");
  const backupsSearchInput = document.getElementById("admin-settings-backups-search");
  const backupsPeriodButtons = Array.from(
    document.querySelectorAll("#admin-settings-backups-period .admin-segmented-btn"),
  );
  const backupsController = createBackupsController({
    tbody: backupsTbody,
    emptyEl: backupsEmptyEl,
    paginationEl: backupsPaginationEl,
    theadRow: backupsTheadRow,
    searchInput: backupsSearchInput,
    periodButtons: backupsPeriodButtons,
  });
  const securityEl = document.getElementById("admin-settings-security");
  const searchInput = document.getElementById("admin-settings-search-input");
  const smtpTestBtn = document.getElementById("admin-settings-smtp-test-btn");
  const backupCreateBtn = document.getElementById("admin-settings-backup-create-btn");

  async function refresh() {
    const res = await fetch("/api/admin/settings/overview", { credentials: "same-origin" });
    if (!res.ok) {
      errorEl.hidden = false;
      errorEl.textContent = "Impossible de charger les paramètres.";
      return;
    }
    errorEl.hidden = true;
    const data = await res.json();

    renderAi(aiForm, aiInfoEl, data.ai);
    renderIntegrations(integrationsEl, data.smtp, data.stripe);
    renderBackupsStats(backupsStatsEl, data.backups);
    renderBackupsBanner(backupsBannerEl, data.backups);
    backupsController.setItems(data.backups.items, refresh);
    renderSecurity(securityEl, data.security, data.logs);
  }

  smtpTestBtn.addEventListener("click", async () => {
    smtpTestBtn.disabled = true;
    smtpTestBtn.textContent = "Envoi en cours…";
    const { ok, payload } = await apiCall("/api/admin/settings/smtp/test", { method: "POST", body: {} });
    smtpTestBtn.disabled = false;
    smtpTestBtn.textContent = "Tester l'envoi";
    if (!ok || !payload.sent) {
      alert(`Échec de l'envoi : ${payload.error || "raison inconnue"}`);
    } else {
      alert("Email de test envoyé avec succès.");
    }
    await refresh();
  });

  backupCreateBtn.addEventListener("click", async () => {
    backupCreateBtn.disabled = true;
    const originalLabel = backupCreateBtn.textContent;
    backupCreateBtn.textContent = "Création en cours…";
    const { ok, payload } = await apiCall("/api/admin/settings/backups", { method: "POST", body: {} });
    backupCreateBtn.disabled = false;
    backupCreateBtn.textContent = originalLabel;
    if (!ok) {
      showToast(payload.error || "Création impossible.", true);
      return;
    }
    showToast("Sauvegarde créée avec succès.");
    await refresh();
  });

  wireFilters(categoriesRoot, searchInput);
  await refresh();
}
