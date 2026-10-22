// Module "IA" (/admin/ia) — panneau d'administration de la CONFIGURATION
// TECHNIQUE des fournisseurs IA configurés dans ai_providers (voir
// admin_ai_service.py) : créer/modifier/activer-désactiver/supprimer un
// fournisseur, réordonner les priorités (boutons monter/descendre — swap
// atomique entre voisins, jamais de collision de priorité possible), tester
// un fournisseur en conditions réelles et lancer un health-check. 3 sections :
// Fournisseurs IA (avec provider_key/modèle et un badge de santé compact en
// sous-ligne), Consommation IA (cumul à vie), Clés API.
// L'assignation fournisseur ⇄ plan d'abonnement (Free/Premium/Ultra) ne vit
// plus ici : elle a été déplacée vers /admin/subscriptions (voir
// admin-subscriptions.js) pour ne plus exister qu'à un seul endroit.
//
// ── Chantier Administrateur "IA" (Phase 2) ──────────────────────────────────
// Avant : une 2e section "État des fournisseurs" affichait, à plat, la quasi
// intégralité des champs déjà présents dans l'onglet "État" de la fiche
// détaillée (voir admin-ai-provider.js) — un doublon sans profondeur propre,
// identifié par l'audit "tri des informations" de /admin/ia. Elle est
// retirée : GET /api/admin/ai/health continue d'être appelée (données
// toujours nécessaires à la fiche détaillée et jamais retirées côté
// backend), mais sert désormais uniquement à peindre un badge de santé
// compact sur chaque carte fournisseur (voir providerHealthState/
// healthBadge ci-dessous), le détail complet restant à un clic sur la fiche.
// Le graphique "Consommation journalière" a été retiré pour la même raison
// (doublon exact de la série `tokens_per_day` d'Analytics, même table
// ai_provider_usage) — remplacé par un simple lien statique dans admin.html,
// aucun rendu JS ni aucune route supplémentaire nécessaires ici.
import { renderApiKeysTable } from "./admin-api-keys.js";

const EMPTY_LABEL = "Aucune donnée disponible";

// Même sémantique et mêmes libellés que system_health_service._provider_state/
// admin-health.js::STATE_LABELS (jamais une seconde définition contradictoire
// de "en bonne santé") — appliquée ici à UN fournisseur, à partir des mêmes
// champs que ceux déjà renvoyés par GET /api/admin/ai/health (jamais un
// nouveau calcul backend, jamais une nouvelle requête) :
//   - aucune ligne ai_provider_health pour ce fournisseur -> "non_teste" ;
//   - dernier échec plus récent que le dernier succès (ou aucun succès du
//     tout) -> "down" ;
//   - taux de succès < 100% -> "degraded" ;
//   - sinon -> "ok".
const HEALTH_STATE_LABELS = {
  ok: "Opérationnel",
  degraded: "Dégradé",
  down: "Indisponible",
  non_teste: "Jamais testé",
};
const HEALTH_STATE_DOT_CLASS = { ok: "ok", degraded: "warning", down: "down", non_teste: "unknown" };

function providerHealthState(healthEntry) {
  if (!healthEntry || !healthEntry.available) return "non_teste";
  const h = healthEntry.value;
  const lastSuccess = h.last_success.available ? h.last_success.value : null;
  const lastFailure = h.last_failure.available ? h.last_failure.value : null;
  if (lastFailure && (!lastSuccess || lastFailure > lastSuccess)) return "down";
  if (h.success_rate.available && h.success_rate.value < 100) return "degraded";
  return "ok";
}

function healthBadge(healthEntry) {
  const state = providerHealthState(healthEntry);
  return el("span", `admin-status-dot admin-status-dot--${HEALTH_STATE_DOT_CLASS[state]}`, HEALTH_STATE_LABELS[state]);
}

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function formatInt(value) {
  return new Intl.NumberFormat("fr-FR").format(value);
}

function formatCost(value) {
  return `${new Intl.NumberFormat("fr-FR", { minimumFractionDigits: 2, maximumFractionDigits: 4 }).format(value)} $`;
}

function emptyState(message) {
  return el("p", "admin-empty", message || EMPTY_LABEL);
}

// ── Appels API (mêmes conventions que static/js/api.js : cookie nm_csrf en
// double-submit sur toute requête mutante — dupliqué ici volontairement, ce
// module n'importe pas api.js, précédent déjà établi dans ce projet, voir
// admin-ai.js::buildSparklinePath). ──────────────────────────────────────
function readCookie(name) {
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

export async function apiCall(path, { method = "GET", body } = {}) {
  const csrfToken = method !== "GET" ? readCookie("nm_csrf") : null;
  const res = await fetch(path, {
    method,
    headers: {
      ...(body ? { "Content-Type": "application/json" } : {}),
      ...(csrfToken ? { "X-CSRF-Token": csrfToken } : {}),
    },
    credentials: "same-origin",
    body: body ? JSON.stringify(body) : undefined,
  });
  const payload = await res.json().catch(() => ({}));
  return { ok: res.ok, status: res.status, payload };
}

// ── Bloc générique champ label/valeur, honore le contrat {available,value,reason} ──
function fieldRow(label, metric, formatter = (v) => v, title) {
  const row = el("div", "admin-field");
  const labelEl = el("span", "admin-field-label", label);
  // `title` (optionnel) : infobulle native au survol — utilisé uniquement
  // pour "Tokens total" ci-dessous (préciser que ce chiffre peut dépasser
  // input+output à cause des tokens de réflexion Gemini, voir renderUsageItem),
  // aucun autre champ n'en a besoin, aucun nouveau composant introduit.
  if (title) labelEl.title = title;
  row.appendChild(labelEl);
  if (!metric || !metric.available) {
    row.appendChild(el("span", "admin-field-value admin-field-value--empty", EMPTY_LABEL));
    if (metric && metric.reason) row.appendChild(el("span", "admin-field-reason", metric.reason));
  } else {
    row.appendChild(el("span", "admin-field-value", formatter(metric.value)));
  }
  return row;
}

function colorDot(colorMetric) {
  const dot = el("span", "admin-ai-color-dot");
  if (colorMetric.available) dot.style.background = colorMetric.value;
  return dot;
}

export function testResultBox(result) {
  const box = el("div", `admin-test-result admin-test-result--${result.ok ? "ok" : "fail"}`);
  if ("tokens" in result) {
    // "Tester la connexion" : test + health-check en une seule action, voir
    // admin_ai_service.test_connection — seul résultat qui expose de vrais
    // tokens (prompt/completion réels renvoyés par le fournisseur).
    box.appendChild(
      el(
        "span",
        null,
        result.ok
          ? `✓ Connexion OK — ${result.latency_ms} ms — modèle : ${result.model}` +
              (result.tokens
                ? ` — tokens : ${result.tokens.prompt_tokens ?? "?"} entrée / ${result.tokens.completion_tokens ?? "?"} sortie`
                : "")
          : `✗ Connexion en échec — ${result.detail}`,
      ),
    );
  } else {
    box.appendChild(
      el(
        "span",
        null,
        result.ok ? `✓ Health-check OK — ${result.latency_ms} ms` : `✗ Health-check en échec — ${result.detail}`,
      ),
    );
  }
  return box;
}

// Audit admin (2026-10-22), point 2 : regroupe les actions secondaires
// (priorité ↑/↓) dans un menu "⋮" — même composant/mêmes classes CSS que le
// menu kebab déjà utilisé par admin-settings.js (actions de sauvegarde),
// pour une cohérence visuelle, sans importer ce module entre pages (chacune
// garde son périmètre). Toujours 1 clic pour ouvrir + 1 clic pour l'action
// (jamais une navigation à plusieurs niveaux) — aucune perte d'accessibilité
// réelle par rapport aux deux boutons visibles séparément.
// Audit admin (2026-10-22), point 3 : Health-check (gratuit) et "Tester la
// connexion" (coûte de vrais tokens) sont RÉELLEMENT différents — confirmé
// dans admin_ai_service.py (run_health_check() = instance.health(), aucun
// token ; test_connection() = vrai prompt). Jamais fusionnés. Le `title`
// (infobulle au survol) ne suffit pas seul : invisible au tactile/mobile —
// ce libellé COURT est donc affiché en permanence sous le bouton, ici comme
// dans la fiche détaillée (voir admin-ai-provider.js::renderHeader).
export function buttonWithCostCaption(button, captionText) {
  const wrap = el("div", "admin-btn-with-caption");
  wrap.appendChild(button);
  wrap.appendChild(el("span", "admin-btn-caption", captionText));
  return wrap;
}

function buildKebabMenu(actions) {
  const wrap = el("div", "admin-kebab");
  const btn = el("button", "admin-kebab-btn", "⋮");
  btn.type = "button";
  btn.setAttribute("aria-label", "Actions de priorité");
  const menu = el("div", "admin-kebab-menu");
  menu.hidden = true;
  actions.forEach((action) => {
    const item = el("button", "admin-kebab-item", action.label);
    item.type = "button";
    item.title = action.title || "";
    item.disabled = Boolean(action.disabled);
    item.addEventListener("click", async (e) => {
      e.stopPropagation();
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

// ── Carte 1 : Fournisseurs IA ────────────────────────────────────────────
function renderProviderCard(provider, { onProviderClick, onChanged, providersCount, healthEntry }) {
  const card = el("article", "admin-card admin-ai-provider-card");
  card.tabIndex = 0;
  card.setAttribute("role", "button");
  card.addEventListener("click", () => onProviderClick(provider.id));
  card.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      onProviderClick(provider.id);
    }
  });

  const head = el("div", "admin-ai-provider-card-head");
  head.appendChild(colorDot(provider.color));
  head.appendChild(el("span", "admin-ai-provider-card-name", provider.name));
  if (provider.badge.available) head.appendChild(el("span", "admin-badge admin-badge--neutral", provider.badge.value));
  head.appendChild(
    el(
      "span",
      `admin-status-dot admin-status-dot--${provider.enabled ? "ok" : "down"}`,
      provider.enabled ? "Activé" : "Désactivé",
    ),
  );
  card.appendChild(head);

  // Badge de santé compact (ex-carte "État des fournisseurs", voir en-tête du
  // fichier) — permet de repérer un problème sans quitter cette carte ; le
  // détail complet (latence, erreurs, code HTTP...) reste dans la fiche.
  card.appendChild(healthBadge(healthEntry));

  card.appendChild(el("div", "admin-card-sub", `Modèle : ${provider.provider_key} · ${provider.model_name}`));
  card.appendChild(el("div", "admin-card-sub", `Priorité ${provider.priority}`));

  // Audit admin (2026-10-22), point 1 : la carte ne garde plus que
  // l'essentiel (nom/badge/statut/santé/modèle/priorité/secours) — icône,
  // description et dates de création/mise à jour sont déplacées vers
  // l'onglet "Informations" de la fiche détaillée (voir admin-ai-provider.js
  // ::renderInfoTab, qui les affiche déjà), AUCUNE information perdue.
  const fields = el("div", "admin-fields-grid admin-ai-provider-card-fields");
  fields.appendChild(fieldRow("Fournisseur de secours", provider.fallback_provider, (v) => v.name));
  card.appendChild(fields);

  // ── Actions — chaque bouton stoppe la propagation pour ne jamais déclencher
  // la navigation vers la fiche détaillée portée par la carte elle-même.
  const actions = el("div", "admin-ai-provider-card-actions");
  const stop = (fn) => (e) => {
    e.stopPropagation();
    fn(e);
  };

  const toggleLabel = el("label", "admin-toggle");
  toggleLabel.title = provider.enabled ? "Désactiver" : "Activer";
  const toggleInput = document.createElement("input");
  toggleInput.type = "checkbox";
  toggleInput.checked = provider.enabled;
  toggleInput.addEventListener("click", (e) => e.stopPropagation());
  toggleInput.addEventListener("change", async () => {
    if (
      !toggleInput.checked &&
      !confirm(`Désactiver le fournisseur « ${provider.name} » ? Le chatbot ne l'utilisera plus.`)
    ) {
      toggleInput.checked = true;
      return;
    }
    toggleInput.disabled = true;
    const { ok, payload } = await apiCall(`/api/admin/ai/providers/${provider.id}/enabled`, {
      method: "PATCH",
      body: { enabled: toggleInput.checked },
    });
    toggleInput.disabled = false;
    if (!ok) {
      window.alert(payload.error || "Action impossible.");
      toggleInput.checked = !toggleInput.checked;
      return;
    }
    onChanged();
  });
  toggleLabel.appendChild(toggleInput);
  toggleLabel.appendChild(el("span", "admin-toggle-track"));
  actions.appendChild(toggleLabel);

  const editBtn = el("button", "admin-btn admin-btn--sm", "Modifier");
  editBtn.type = "button";
  editBtn.addEventListener(
    "click",
    stop(() => openProviderModal({ mode: "edit", provider, onSaved: onChanged })),
  );
  actions.appendChild(editBtn);

  if (providersCount > 1) {
    const priorityMenu = buildKebabMenu([
      {
        label: "↑ Monter la priorité",
        title: "Monter la priorité",
        onClick: async () => {
          const { ok, payload } = await apiCall(`/api/admin/ai/providers/${provider.id}/move-up`, { method: "POST" });
          if (!ok) {
            window.alert(payload.error || "Action impossible.");
            return;
          }
          onChanged();
        },
      },
      {
        label: "↓ Descendre la priorité",
        title: "Descendre la priorité",
        onClick: async () => {
          const { ok, payload } = await apiCall(`/api/admin/ai/providers/${provider.id}/move-down`, {
            method: "POST",
          });
          if (!ok) {
            window.alert(payload.error || "Action impossible.");
            return;
          }
          onChanged();
        },
      },
    ]);
    actions.appendChild(priorityMenu);
  }

  const resultSlot = el("div", "admin-ai-provider-card-result");

  const healthBtn = el("button", "admin-btn admin-btn--sm", "Health-check");
  healthBtn.type = "button";
  // Audit admin (2026-10-22) : vérifié dans admin_ai_service.py que ce
  // bouton et "Tester la connexion" ci-dessous ne font PAS la même chose —
  // run_health_check() appelle instance.health() (diagnostic, aucun token
  // consommé, aucun contenu généré) alors que test_connection() envoie un
  // vrai prompt (tokens réels, voir testResultBox). Conservés séparés à
  // dessein ; le titre explicite leur coût réel plutôt que de les fusionner.
  healthBtn.title = "Vérification de disponibilité : gratuite, aucun token consommé, aucun contenu généré.";
  healthBtn.addEventListener(
    "click",
    stop(async () => {
      healthBtn.disabled = true;
      resultSlot.innerHTML = "";
      resultSlot.appendChild(el("p", "admin-test-result admin-test-result--pending", "Health-check en cours…"));
      const { ok, payload } = await apiCall(`/api/admin/ai/providers/${provider.id}/health-check`, { method: "POST" });
      healthBtn.disabled = false;
      resultSlot.innerHTML = "";
      resultSlot.appendChild(
        ok
          ? testResultBox(payload)
          : el("p", "admin-test-result admin-test-result--fail", payload.error || "Erreur inattendue."),
      );
    }),
  );
  actions.appendChild(buttonWithCostCaption(healthBtn, "Gratuit"));

  const testConnectionBtn = el("button", "admin-btn admin-btn--sm admin-btn--primary", "Tester la connexion");
  testConnectionBtn.type = "button";
  testConnectionBtn.title = "Appel réel au fournisseur : consomme de vrais tokens (prompt + réponse).";
  testConnectionBtn.addEventListener(
    "click",
    stop(async () => {
      testConnectionBtn.disabled = true;
      resultSlot.innerHTML = "";
      resultSlot.appendChild(el("p", "admin-test-result admin-test-result--pending", "Test de connexion en cours…"));
      const { ok, payload } = await apiCall(`/api/admin/ai/providers/${provider.id}/test-connection`, {
        method: "POST",
      });
      testConnectionBtn.disabled = false;
      resultSlot.innerHTML = "";
      resultSlot.appendChild(
        ok
          ? testResultBox(payload)
          : el("p", "admin-test-result admin-test-result--fail", payload.error || "Erreur inattendue."),
      );
    }),
  );
  actions.appendChild(buttonWithCostCaption(testConnectionBtn, "Coûte des tokens"));

  const deleteBtn = el("button", "admin-btn admin-btn--sm admin-btn--danger", "Supprimer");
  deleteBtn.type = "button";
  deleteBtn.addEventListener(
    "click",
    stop(async () => {
      if (!window.confirm(`Supprimer définitivement "${provider.name}" ?`)) return;
      deleteBtn.disabled = true;
      const { ok, payload } = await apiCall(`/api/admin/ai/providers/${provider.id}`, { method: "DELETE" });
      deleteBtn.disabled = false;
      if (!ok) {
        window.alert(payload.error || "Suppression impossible.");
        return;
      }
      onChanged();
    }),
  );
  actions.appendChild(deleteBtn);

  card.appendChild(actions);
  card.appendChild(resultSlot);

  return card;
}

function renderProvidersCard(container, data, ctx) {
  container.innerHTML = "";
  if (!data.providers) {
    container.appendChild(emptyState(data.reason));
    return;
  }
  const healthByProvider = ctx.healthByProvider || {};
  data.providers.forEach((provider) =>
    container.appendChild(
      renderProviderCard(provider, {
        ...ctx,
        providersCount: data.providers.length,
        // Absent (fetch en échec, ou fournisseur créé après le chargement de la
        // santé) -> traité comme "jamais testé", jamais un état fabriqué.
        healthEntry: healthByProvider[provider.id],
      }),
    ),
  );
}

function renderProvidersSkeleton(container) {
  container.innerHTML = "";
  for (let i = 0; i < 3; i += 1) {
    const card = el("article", "admin-card");
    const bar = el("div", "admin-skeleton");
    bar.style.height = "120px";
    card.appendChild(bar);
    container.appendChild(card);
  }
}

// ── Modale de création/modification d'un fournisseur ────────────────────
const PROVIDER_KEY_OPTIONS = ["gemini", "anthropic", "ollama", "fake"];

export function openProviderModal({ mode, provider, allProviders, onSaved }) {
  const overlay = document.getElementById("admin-ai-provider-modal");
  const title = document.getElementById("admin-ai-provider-modal-title");
  const body = document.getElementById("admin-ai-provider-modal-body");
  const closeBtn = document.getElementById("admin-ai-provider-modal-close");

  title.textContent = mode === "edit" ? `Modifier ${provider.name}` : "Nouveau fournisseur";
  body.innerHTML = "";

  const banner = el("div", "admin-form-banner");
  banner.hidden = true;
  body.appendChild(banner);

  const form = document.createElement("form");
  form.className = "admin-form-grid";

  function field(target, labelText, key, { type = "text", full = false, value = "" } = {}) {
    const wrap = el("div", `admin-form-field${full ? " admin-form-field--full" : ""}`);
    wrap.dataset.field = key;
    wrap.appendChild(el("label", "admin-form-label", labelText));
    const input = document.createElement(type === "select" ? "select" : "input");
    input.className = type === "select" ? "admin-form-select" : "admin-form-input";
    input.name = key;
    if (type !== "select") input.type = type;
    if (type === "number") input.min = "0";
    input.value = value;
    wrap.appendChild(input);
    target.appendChild(wrap);
    return input;
  }

  // Le nom reste seul, hors des deux blocs (identité du fournisseur, visible
  // d'emblée, ni "configuration" ni "présentation" au sens de l'audit).
  const nameInput = field(form, "Nom", "name", { value: provider?.name || "" });

  // Audit admin (2026-10-22), point 6 : les 10 champs à plat de l'ancienne
  // modale sont regroupés en 2 blocs visuels — "Configuration" (impacte le
  // comportement réel du chatbot : provider_key/modèle/priorité/secours/
  // activé) et "Présentation" (purement cosmétique, jamais lu par le
  // chatbot : code/badge/icône/couleur/description), ce second bloc replié
  // par défaut sous un <details>. AUCUN champ supprimé, AUCUNE validation
  // changée — seule la présentation visuelle évolue.
  const configSection = el("div", "admin-form-grid admin-form-field--full");
  configSection.appendChild(el("h3", "admin-settings-subtitle", "Configuration"));
  form.appendChild(configSection);

  const keySelect = field(configSection, "provider_key", "provider_key", { type: "select" });
  PROVIDER_KEY_OPTIONS.forEach((key) => {
    const opt = document.createElement("option");
    opt.value = key;
    opt.textContent = key;
    keySelect.appendChild(opt);
  });
  keySelect.value = provider?.provider_key || PROVIDER_KEY_OPTIONS[0];
  const modelInput = field(configSection, "Modèle", "model_name", { value: provider?.model_name || "" });
  const priorityInput = field(configSection, "Priorité", "priority", {
    type: "number",
    value: provider?.priority ?? 0,
  });

  const fallbackSelect = field(configSection, "Fournisseur de secours", "fallback_provider_id", { type: "select" });
  const noneOpt = document.createElement("option");
  noneOpt.value = "";
  noneOpt.textContent = "Aucun";
  fallbackSelect.appendChild(noneOpt);
  (allProviders || []).forEach((p) => {
    if (mode === "edit" && p.id === provider.id) return;
    const opt = document.createElement("option");
    opt.value = String(p.id);
    opt.textContent = p.name;
    fallbackSelect.appendChild(opt);
  });
  if (provider?.fallback_provider?.available) fallbackSelect.value = String(provider.fallback_provider.value.id);

  const enabledWrap = el("div", "admin-form-field admin-form-field--full admin-form-checkbox-row");
  const enabledInput = document.createElement("input");
  enabledInput.type = "checkbox";
  enabledInput.checked = provider ? provider.enabled : true;
  enabledWrap.appendChild(enabledInput);
  enabledWrap.appendChild(el("span", null, "Fournisseur activé"));
  configSection.appendChild(enabledWrap);

  const presentationDetails = document.createElement("details");
  presentationDetails.className = "admin-form-field--full admin-ai-provider-presentation";
  const presentationSummary = document.createElement("summary");
  presentationSummary.className = "admin-settings-subtitle";
  presentationSummary.textContent = "Présentation (cosmétique — jamais lu par le chatbot)";
  presentationDetails.appendChild(presentationSummary);
  const presentationGrid = el("div", "admin-form-grid");
  presentationDetails.appendChild(presentationGrid);
  form.appendChild(presentationDetails);

  const codeInput = field(presentationGrid, "Code", "code", {
    value: provider?.code?.available ? provider.code.value : provider?.code || "",
  });
  const badgeInput = field(presentationGrid, "Badge", "badge", {
    value: provider?.badge?.available ? provider.badge.value : "",
  });
  const iconInput = field(presentationGrid, "Icône", "icon", {
    value: provider?.icon?.available ? provider.icon.value : "",
  });
  const colorInput = field(presentationGrid, "Couleur", "color", {
    value: provider?.color?.available ? provider.color.value : "#3B82F6",
  });
  colorInput.type = "color";

  const descWrap = el("div", "admin-form-field admin-form-field--full");
  descWrap.dataset.field = "description";
  descWrap.appendChild(el("label", "admin-form-label", "Description"));
  const descInput = document.createElement("textarea");
  descInput.className = "admin-form-textarea";
  descInput.rows = 2;
  descInput.value = provider?.description?.available ? provider.description.value : "";
  descWrap.appendChild(descInput);
  presentationGrid.appendChild(descWrap);

  const actions = el("div", "admin-form-field--full admin-form-actions");
  const cancelBtn = el("button", "admin-btn", "Annuler");
  cancelBtn.type = "button";
  const saveBtn = el("button", "admin-btn admin-btn--primary", "Sauvegarder");
  saveBtn.type = "submit";
  actions.appendChild(cancelBtn);
  actions.appendChild(saveBtn);
  form.appendChild(actions);

  function closeModal() {
    overlay.hidden = true;
  }
  cancelBtn.addEventListener("click", closeModal);
  closeBtn.onclick = closeModal;
  overlay.onclick = (e) => {
    if (e.target === overlay) closeModal();
  };

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    banner.hidden = true;
    form.querySelectorAll(".admin-form-field--invalid").forEach((n) => n.classList.remove("admin-form-field--invalid"));
    form.querySelectorAll(".admin-form-error").forEach((n) => n.remove());

    const payload = {
      name: nameInput.value,
      provider_key: keySelect.value,
      model_name: modelInput.value,
      priority: Number(priorityInput.value),
      code: codeInput.value,
      badge: badgeInput.value,
      icon: iconInput.value,
      color: colorInput.value,
      description: descInput.value,
      fallback_provider_id: fallbackSelect.value ? Number(fallbackSelect.value) : null,
      enabled: enabledInput.checked,
    };

    saveBtn.disabled = true;
    const path = mode === "edit" ? `/api/admin/ai/providers/${provider.id}` : "/api/admin/ai/providers";
    const { ok, payload: res } = await apiCall(path, { method: mode === "edit" ? "PUT" : "POST", body: payload });
    saveBtn.disabled = false;

    if (!ok) {
      const fields = res.fields || {};
      if (Object.keys(fields).length) {
        Object.entries(fields).forEach(([key, message]) => {
          const wrap = form.querySelector(`[data-field="${key}"]`);
          if (wrap) {
            wrap.classList.add("admin-form-field--invalid");
            wrap.appendChild(el("span", "admin-form-error", message));
          } else {
            banner.hidden = false;
            banner.textContent = message;
          }
        });
      } else {
        banner.hidden = false;
        banner.textContent = res.error || "Une erreur est survenue.";
      }
      return;
    }

    closeModal();
    onSaved();
  });

  body.appendChild(form);
  overlay.hidden = false;
  nameInput.focus();
}

// La carte 2 "État des fournisseurs" (champ pour champ identique à l'onglet
// "État" de la fiche détaillée) a été retirée — voir le commentaire en tête
// de fichier. Les mêmes données (GET /api/admin/ai/health) alimentent
// désormais uniquement le badge compact de la carte Fournisseurs
// (providerHealthState/healthBadge, plus haut).

// ── Consommation IA (cumul à vie) ───────────────────────────────────────────
function renderUsageItem(item) {
  const card = el("article", "admin-card");
  card.appendChild(el("div", "admin-card-label", item.name));
  if (!item.usage.available) {
    card.appendChild(el("div", "admin-card-value--empty", EMPTY_LABEL));
    card.appendChild(el("div", "admin-card-sub", item.usage.reason));
    return card;
  }
  const u = item.usage.value;
  const fields = el("div", "admin-fields-grid");
  fields.appendChild(fieldRow("Input tokens", { available: true, value: u.input_tokens }, formatInt));
  fields.appendChild(fieldRow("Output tokens", { available: true, value: u.output_tokens }, formatInt));
  // Chantier "fiabilité des données d'analytics IA" (audit 2026-08-27) :
  // total_tokens (déjà stocké en base, désormais exposé par admin_ai_service)
  // peut dépasser input+output — les tokens de réflexion Gemini sont
  // comptés à part par l'API (voir estimate_llm_cost() côté backend, jamais
  // recalculé ici) mais déjà inclus dans le coût affiché ci-dessous. Sans ce
  // champ, un admin qui recalcule "input×prix + output×prix" obtient un
  // montant inférieur au coût réel, sans explication visible.
  fields.appendChild(
    fieldRow(
      "Tokens total",
      { available: true, value: u.total_tokens },
      formatInt,
      "Total des tokens comptabilisés par le fournisseur, incluant les tokens de réflexion (thinking) lorsqu'ils sont fournis — peut dépasser input + output. Déjà inclus dans le coût estimé ci-dessous.",
    ),
  );
  fields.appendChild(fieldRow("Requêtes", { available: true, value: u.requests }, formatInt));
  fields.appendChild(fieldRow("Coût estimé", { available: true, value: u.estimated_cost }, formatCost));
  card.appendChild(fields);
  return card;
}

// Audit admin (2026-10-22), point 5 : si TOUS les fournisseurs sont à
// "aucune donnée" en même temps, le même message ("Aucun appel réel n'a
// encore été comptabilisé...") apparaissait répété sur chaque carte —
// remplacé par UN SEUL message global au-dessus de la liste, jamais répété.
// Dès qu'AU MOINS un fournisseur a une donnée réelle, chaque carte retrouve
// son propre état (vide ou rempli), pour ne jamais masquer une absence
// ponctuelle sur un fournisseur précis parmi d'autres qui ont des données.
function renderUsage(container, data) {
  container.innerHTML = "";
  if (!data.items) {
    container.appendChild(emptyState(data.reason));
    return;
  }
  const allEmpty = data.items.length > 0 && data.items.every((item) => !item.usage.available);
  if (allEmpty) {
    container.appendChild(
      emptyState(
        `${EMPTY_LABEL} : aucun appel réel n'a encore été comptabilisé pour aucun fournisseur (ai_provider_usage n'est pas encore alimentée par le chatbot).`,
      ),
    );
    return;
  }
  data.items.forEach((item) => container.appendChild(renderUsageItem(item)));
}

// ── Carte 4 : Clés API (haute disponibilité, rotation automatique) ─────────
// Finalisation du nettoyage admin (2026-10-22) : /admin/ia devient l'UNIQUE
// emplacement de gestion des clés API (Paramètres ne garde qu'un lien, voir
// admin-settings.js). `allowEdit: true` active ici le renommage/changement
// de priorité — auparavant réservé à /admin/settings (SUPER_ADMIN), jamais
// à /admin/ia (ADMIN). Vérifié avant d'activer : AUCUNE des routes
// /api/admin/ai/keys/* (GET/POST/PATCH/DELETE/test, server.py) n'exige
// SUPER_ADMIN — toutes sont gardées par le même rôle minimum ADMIN
// (_AI_MODULE_ROLE), y compris le PATCH de renommage/priorité ; la
// frontière "SUPER_ADMIN uniquement" n'existait qu'au niveau de la PAGE
// /admin/settings, jamais au niveau de l'autorisation réelle de l'opération.
// Activer `allowEdit` ici n'élargit donc aucune permission : un ADMIN
// pouvait déjà techniquement appeler ce PATCH via l'API, il peut
// maintenant aussi le faire depuis l'interface qu'il utilise déjà pour
// tout le reste de la gestion des clés.

export function openApiKeyModal({ onSaved }) {
  const overlay = document.getElementById("admin-ai-key-modal");
  const body = document.getElementById("admin-ai-key-modal-body");
  const closeBtn = document.getElementById("admin-ai-key-modal-close");
  body.innerHTML = "";

  const banner = el("div", "admin-form-banner");
  banner.hidden = true;
  body.appendChild(banner);

  const form = document.createElement("form");
  form.className = "admin-form-grid";

  function field(labelText, key, { type = "text", full = false } = {}) {
    const wrap = el("div", `admin-form-field${full ? " admin-form-field--full" : ""}`);
    const input = document.createElement(type === "select" ? "select" : "input");
    input.className = type === "select" ? "admin-form-select" : "admin-form-input";
    input.name = key;
    if (type !== "select") input.type = type;
    wrap.appendChild(el("label", "admin-form-label", labelText));
    wrap.appendChild(input);
    form.appendChild(wrap);
    return input;
  }

  const providerSelect = field("Fournisseur", "provider_key", { type: "select" });
  PROVIDER_KEY_OPTIONS.filter((k) => k !== "fake" && k !== "ollama").forEach((k) => {
    const opt = document.createElement("option");
    opt.value = k;
    opt.textContent = k;
    providerSelect.appendChild(opt);
  });
  const labelInput = field("Libellé", "label", { full: true });
  const apiKeyInput = field("Clé API", "api_key", { type: "password", full: true });
  const priorityInput = field("Priorité (0 = essayée en premier)", "priority", { type: "number" });
  priorityInput.value = "0";

  const submitBtn = el("button", "admin-btn admin-btn--primary", "Ajouter la clé");
  submitBtn.type = "submit";
  form.appendChild(submitBtn);

  form.onsubmit = async (event) => {
    event.preventDefault();
    banner.hidden = true;
    const { ok, payload } = await apiCall("/api/admin/ai/keys", {
      method: "POST",
      body: {
        provider_key: providerSelect.value,
        label: labelInput.value,
        api_key: apiKeyInput.value,
        priority: Number(priorityInput.value) || 0,
      },
    });
    if (!ok) {
      banner.hidden = false;
      banner.textContent = payload.error || "Impossible d'ajouter cette clé.";
      return;
    }
    overlay.hidden = true;
    onSaved();
  };

  body.appendChild(form);
  overlay.hidden = false;
  closeBtn.onclick = () => {
    overlay.hidden = true;
  };
}

// ── Point d'entrée ────────────────────────────────────────────────────────
export async function loadAiOverview(onProviderClick) {
  const providersEl = document.getElementById("admin-ai-providers");
  const usageEl = document.getElementById("admin-ai-usage");
  const keysEl = document.getElementById("admin-ai-keys");
  const errorEl = document.getElementById("admin-global-error");
  const newProviderBtn = document.getElementById("admin-ai-new-provider-btn");
  const newKeyBtn = document.getElementById("admin-ai-new-key-btn");

  renderProvidersSkeleton(providersEl);
  usageEl.innerHTML = "";
  if (keysEl) keysEl.innerHTML = "";
  errorEl.hidden = true;

  const refresh = () => loadAiOverview(onProviderClick);

  const [providersRes, healthRes, usageRes] = await Promise.allSettled([
    fetch("/api/admin/ai/providers", { credentials: "same-origin" }),
    fetch("/api/admin/ai/health", { credentials: "same-origin" }),
    fetch("/api/admin/ai/usage", { credentials: "same-origin" }),
  ]);

  let anyError = false;

  async function renderOrError(settled, renderer, container) {
    if (settled.status !== "fulfilled" || !settled.value.ok) {
      container.innerHTML = "";
      container.appendChild(
        el("p", "admin-empty admin-card-error", "Impossible de charger cette section. Réessaie dans un instant."),
      );
      anyError = true;
      return null;
    }
    const payload = await settled.value.json().catch(() => null);
    if (payload === null) {
      container.innerHTML = "";
      container.appendChild(
        el("p", "admin-empty admin-card-error", "Impossible de charger cette section. Réessaie dans un instant."),
      );
      anyError = true;
      return null;
    }
    renderer(payload);
    return payload;
  }

  // Les données de santé n'ont plus de conteneur/carte dédié (voir en-tête du
  // fichier) : un échec de leur récupération ne bloque jamais l'affichage des
  // fournisseurs, il se traduit uniquement par des badges "Jamais testé"
  // (voir healthByProvider ci-dessous, toujours un objet défini, jamais
  // `undefined`) + le bandeau d'erreur global déjà utilisé par les autres
  // sections — jamais un état de santé fabriqué pour compenser.
  const healthByProvider = {};
  if (healthRes.status === "fulfilled" && healthRes.value.ok) {
    const healthPayload = await healthRes.value.json().catch(() => null);
    if (healthPayload && healthPayload.items) {
      healthPayload.items.forEach((item) => {
        healthByProvider[item.provider_id] = item.health;
      });
    } else {
      anyError = true;
    }
  } else {
    anyError = true;
  }

  const providersPayload = await renderOrError(
    providersRes,
    (data) => renderProvidersCard(providersEl, data, { onProviderClick, onChanged: refresh, healthByProvider }),
    providersEl,
  );
  const allProviders = providersPayload && providersPayload.providers ? providersPayload.providers : [];

  await renderOrError(usageRes, (data) => renderUsage(usageEl, data), usageEl);

  if (keysEl) {
    try {
      const keysResp = await fetch("/api/admin/ai/keys", { credentials: "same-origin" });
      // Audit admin (2026-10-20), point 4 : une réponse HTTP en échec ne
      // doit jamais être traitée comme "aucune clé" (un [] en cas d'erreur
      // s'affichait exactement comme un [] légitime, via emptyMessage
      // ci-dessous, qui affirme à tort qu'aucune clé n'est configurée).
      if (!keysResp.ok) throw new Error(`HTTP ${keysResp.status}`);
      const keys = await keysResp.json();
      renderApiKeysTable(keysEl, keys, {
        onChanged: refresh,
        allowEdit: true,
        emptyMessage:
          "Aucune clé API configurée — le fournisseur utilise la variable d'environnement historique (une seule clé, sans rotation).",
      });
    } catch {
      keysEl.innerHTML = "";
      keysEl.appendChild(
        el("p", "admin-empty admin-card-error", "Impossible de charger les clés API. Réessaie dans un instant."),
      );
    }
  }

  if (newProviderBtn) {
    newProviderBtn.onclick = () => openProviderModal({ mode: "create", allProviders, onSaved: refresh });
  }
  if (newKeyBtn) {
    newKeyBtn.onclick = () => openApiKeyModal({ onSaved: refresh });
  }

  errorEl.hidden = !anyError;
  if (anyError)
    errorEl.textContent = "Certaines sections du module IA n'ont pas pu être chargées. Réessaie dans un instant.";
}
