// Fiche détaillée d'un fournisseur IA (/admin/ia/:id) — 3 onglets, CHACUN
// chargé par sa propre API au moment où il est ouvert pour la première fois
// (lazy loading réel, cache par onglet) — même architecture que
// admin-user-profile.js. L'onglet Informations reste un AFFICHAGE en lecture
// seule des champs bruts (fusion des anciens onglets "Informations générales"
// et "Configuration", strictement les mêmes champs) : la modification passe
// par le bouton "Modifier" de l'en-tête (modale partagée avec admin-ai.js),
// jamais par une édition inline de cet onglet — un seul formulaire de
// fournisseur dans toute l'application, jamais deux implémentations
// divergentes.
import { openProviderModal, apiCall, testResultBox } from "./admin-ai.js";

const EMPTY_LABEL = "Aucune donnée disponible";

const TABS = [
  { id: "info", label: "Informations" },
  { id: "health", label: "État" },
  { id: "usage", label: "Consommation" },
];

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function formatDateTime(iso) {
  if (!iso) return null;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString("fr-FR", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
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

function fieldRow(label, metric, formatter = (v) => v) {
  const row = el("div", "admin-field");
  row.appendChild(el("span", "admin-field-label", label));
  if (!metric || !metric.available) {
    row.appendChild(el("span", "admin-field-value admin-field-value--empty", EMPTY_LABEL));
    if (metric && metric.reason) row.appendChild(el("span", "admin-field-reason", metric.reason));
  } else {
    row.appendChild(el("span", "admin-field-value", formatter(metric.value)));
  }
  return row;
}

// ── En-tête de la fiche + actions (Modifier/Health-check/Tester la connexion/Actualiser) ─
function renderHeader(info, providerId, { onChanged, onRefresh }) {
  const head = document.getElementById("admin-ai-provider-head");
  head.innerHTML = "";

  const avatarWrap = el("span", "admin-avatar admin-avatar--lg");
  if (info.color.available) avatarWrap.style.background = info.color.value;
  avatarWrap.textContent = (info.name || "?").trim().charAt(0).toUpperCase();
  head.appendChild(avatarWrap);

  const meta = el("div", "admin-user-profile-meta");
  meta.appendChild(el("h1", "admin-user-profile-name", info.name));
  meta.appendChild(el("p", "admin-user-profile-email", `${info.provider_key} · ${info.model_name}`));
  const badges = el("div", "admin-user-profile-badges");
  if (info.badge.available) badges.appendChild(el("span", "admin-badge admin-badge--neutral", info.badge.value));
  badges.appendChild(el("span", `admin-status-dot admin-status-dot--${info.enabled ? "ok" : "down"}`,
    info.enabled ? "Activé" : "Désactivé"));
  meta.appendChild(badges);
  head.appendChild(meta);

  const actions = el("div", "admin-ai-provider-card-actions");

  const editBtn = el("button", "admin-btn admin-btn--sm", "Modifier");
  editBtn.type = "button";
  editBtn.addEventListener("click", async () => {
    const { ok, payload: providersPayload } = await apiCall("/api/admin/ai/providers");
    const allProviders = ok && providersPayload.providers ? providersPayload.providers : [];
    const provider = {
      id: providerId,
      name: info.name,
      provider_key: info.provider_key,
      model_name: info.model_name,
      priority: info.priority,
      enabled: info.enabled,
      fallback_provider: info.fallback_provider,
      badge: info.badge,
      icon: info.icon,
      color: info.color,
      description: info.description,
      code: allProviders.find((p) => p.id === providerId)?.code || { available: false, value: null },
    };
    openProviderModal({ mode: "edit", provider, allProviders, onSaved: onChanged });
  });
  actions.appendChild(editBtn);

  const refreshBtn = el("button", "admin-btn admin-btn--sm", "Actualiser");
  refreshBtn.type = "button";
  refreshBtn.addEventListener("click", onRefresh);
  actions.appendChild(refreshBtn);

  const resultSlot = el("div", "admin-ai-provider-card-result");

  const healthBtn = el("button", "admin-btn admin-btn--sm", "Lancer un health-check");
  healthBtn.type = "button";
  healthBtn.addEventListener("click", async () => {
    healthBtn.disabled = true;
    resultSlot.innerHTML = "";
    resultSlot.appendChild(el("p", "admin-test-result admin-test-result--pending", "Health-check en cours…"));
    const { ok, payload } = await apiCall(`/api/admin/ai/providers/${providerId}/health-check`, { method: "POST" });
    healthBtn.disabled = false;
    resultSlot.innerHTML = "";
    resultSlot.appendChild(ok ? testResultBox(payload) : el("p", "admin-test-result admin-test-result--fail", payload.error || "Erreur inattendue."));
  });
  actions.appendChild(healthBtn);

  const testConnectionBtn = el("button", "admin-btn admin-btn--sm admin-btn--primary", "Tester la connexion");
  testConnectionBtn.type = "button";
  testConnectionBtn.addEventListener("click", async () => {
    testConnectionBtn.disabled = true;
    resultSlot.innerHTML = "";
    resultSlot.appendChild(el("p", "admin-test-result admin-test-result--pending", "Test de connexion en cours…"));
    const { ok, payload } = await apiCall(`/api/admin/ai/providers/${providerId}/test-connection`, { method: "POST" });
    testConnectionBtn.disabled = false;
    resultSlot.innerHTML = "";
    resultSlot.appendChild(ok ? testResultBox(payload) : el("p", "admin-test-result admin-test-result--fail", payload.error || "Erreur inattendue."));
  });
  actions.appendChild(testConnectionBtn);

  head.appendChild(actions);
  head.appendChild(resultSlot);
}

// ── 1. Informations (fusion Informations générales + Configuration) ────────
function renderInfoTab(data) {
  const grid = el("div", "admin-fields-grid");
  grid.appendChild(fieldRow("Nom", { available: true, value: data.name }));
  grid.appendChild(fieldRow("Provider key", { available: true, value: data.provider_key }));
  grid.appendChild(fieldRow("Modèle", { available: true, value: data.model_name }));
  grid.appendChild(fieldRow("Priorité", { available: true, value: data.priority }));
  grid.appendChild(fieldRow("Activé", { available: true, value: data.enabled }, (v) => (v ? "Oui" : "Non")));
  grid.appendChild(fieldRow("Fournisseur de secours", data.fallback_provider, (v) => v.name));
  grid.appendChild(fieldRow("Code", data.code));
  grid.appendChild(fieldRow("Badge", data.badge));
  grid.appendChild(fieldRow("Icône", data.icon));
  grid.appendChild(fieldRow("Couleur", data.color));
  grid.appendChild(fieldRow("Description", data.description));
  grid.appendChild(fieldRow("Créé le", data.created_at, formatDateTime));
  grid.appendChild(fieldRow("Dernière mise à jour", data.updated_at, formatDateTime));
  return grid;
}

// ── 2. État ───────────────────────────────────────────────────────────────
function renderHealthTab(data) {
  if (!data.available) return emptyState(data.reason);
  const h = data.value;
  const grid = el("div", "admin-fields-grid");
  grid.appendChild(fieldRow("Dernier succès", h.last_success, formatDateTime));
  grid.appendChild(fieldRow("Dernier échec", h.last_failure, formatDateTime));
  grid.appendChild(fieldRow("Latence", h.latency_ms, (v) => `${v} ms`));
  grid.appendChild(fieldRow("Latence moyenne", h.average_latency, (v) => `${Math.round(v)} ms`));
  grid.appendChild(fieldRow("Nombre de requêtes", { available: true, value: h.total_requests.value }, formatInt));
  grid.appendChild(fieldRow("Nombre d'erreurs", { available: true, value: h.total_errors.value }, formatInt));
  grid.appendChild(fieldRow("Taux de succès", h.success_rate, (v) => `${v}%`));
  grid.appendChild(fieldRow("Dernier code HTTP", h.http_code));
  grid.appendChild(fieldRow("Dernier message d'erreur", h.last_error));
  grid.appendChild(fieldRow("Dernière vérification", { available: true, value: h.updated_at.value }, formatDateTime));
  return grid;
}

// ── 3. Consommation ───────────────────────────────────────────────────────
function renderUsageTab(data) {
  const wrap = el("div", "admin-ai-usage-tab");
  if (!data.available) {
    wrap.appendChild(emptyState(data.reason));
    return wrap;
  }
  const u = data.value;
  const cards = el("div", "admin-cards");
  [
    ["Input tokens", formatInt(u.input_tokens)],
    ["Output tokens", formatInt(u.output_tokens)],
    ["Requêtes", formatInt(u.requests)],
    ["Coût estimé", formatCost(u.estimated_cost)],
  ].forEach(([label, value]) => {
    const card = el("article", "admin-card");
    card.appendChild(el("div", "admin-card-label", label));
    card.appendChild(el("div", "admin-card-value", value));
    cards.appendChild(card);
  });
  wrap.appendChild(cards);

  if (u.daily.length) {
    const table = el("table", "admin-users-table");
    const thead = document.createElement("thead");
    const theadRow = el("tr");
    ["Date", "Input", "Output", "Requêtes", "Coût"].forEach((label) => theadRow.appendChild(el("th", "admin-users-th", label)));
    thead.appendChild(theadRow);
    table.appendChild(thead);
    const tbody = document.createElement("tbody");
    u.daily.forEach((row) => {
      const tr = el("tr", "admin-users-row");
      tr.appendChild(el("td", "admin-users-td", row.date));
      tr.appendChild(el("td", "admin-users-td", formatInt(row.input_tokens)));
      tr.appendChild(el("td", "admin-users-td", formatInt(row.output_tokens)));
      tr.appendChild(el("td", "admin-users-td", formatInt(row.requests)));
      tr.appendChild(el("td", "admin-users-td", formatCost(row.estimated_cost)));
      tbody.appendChild(tr);
    });
    table.appendChild(tbody);
    const wrapTable = el("div", "admin-users-table-wrap");
    wrapTable.appendChild(table);
    wrap.appendChild(wrapTable);
  }
  return wrap;
}

const TAB_RENDERERS = {
  info: renderInfoTab,
  health: renderHealthTab,
  usage: renderUsageTab,
};

function renderSkeletonPanel(panel) {
  panel.innerHTML = "";
  for (let i = 0; i < 4; i += 1) {
    panel.appendChild(el("div", "admin-skeleton admin-tab-skeleton-row"));
  }
}

export async function loadAiProviderDetail(providerId) {
  const tabsNav = document.getElementById("admin-ai-provider-tabs");
  const panel = document.getElementById("admin-ai-provider-panel");
  const cache = new Map();
  let activeTab = "info";

  function renderTabsNav() {
    tabsNav.innerHTML = "";
    TABS.forEach((tab) => {
      const btn = el("button", "admin-tab-btn", tab.label);
      btn.type = "button";
      btn.dataset.tab = tab.id;
      if (tab.id === activeTab) btn.classList.add("is-active");
      btn.addEventListener("click", () => switchTab(tab.id));
      tabsNav.appendChild(btn);
    });
  }

  async function fetchTab(tabId) {
    const res = await fetch(`/api/admin/ai/providers/${providerId}/${tabId}`, { credentials: "same-origin" });
    const payload = await res.json().catch(() => ({}));
    if (res.status === 404) return { notFound: true };
    if (!res.ok) throw new Error(payload.error || `Erreur API (${res.status})`);
    return { payload };
  }

  // Rechargement complet après une modification enregistrée (modale de
  // fournisseur) ou un clic sur "Actualiser" — vide le cache par onglet pour
  // que le prochain switchTab() refasse un appel réseau réel, jamais un
  // affichage périmé après écriture.
  async function reloadAll() {
    cache.clear();
    await switchTab(activeTab);
  }

  async function switchTab(tabId) {
    activeTab = tabId;
    renderTabsNav();

    // L'en-tête (nom/badge/statut + actions) a besoin des champs de l'onglet
    // "info", quel que soit l'onglet actif — un seul appel réseau partagé
    // avec le rendu de l'onglet "info" lui-même (voir plus bas : si tabId
    // vaut "info", le cache est déjà rempli à ce stade, donc AUCUN second
    // appel n'est déclenché).
    let providerNotFound = false;
    if (!cache.has("info")) {
      try {
        const { payload, notFound } = await fetchTab("info");
        if (notFound) {
          providerNotFound = true;
        } else {
          cache.set("info", payload);
          renderHeader(payload, providerId, { onChanged: reloadAll, onRefresh: reloadAll });
        }
      } catch {
        // En-tête non critique pour l'affichage de l'onglet demandé — une
        // panne ici n'empêche jamais de tenter le chargement de l'onglet.
      }
    } else {
      renderHeader(cache.get("info"), providerId, { onChanged: reloadAll, onRefresh: reloadAll });
    }

    if (providerNotFound) {
      panel.innerHTML = "";
      panel.appendChild(emptyState("Ce fournisseur est introuvable."));
      return;
    }

    // L'onglet "Informations" fusionne les anciens onglets Informations
    // générales + Configuration : sa version affichée (avec "code" en plus)
    // est mise en cache sous une clé distincte ("infoTab") de celle de
    // l'en-tête ("info"), pour ne jamais mélanger les deux formes du payload.
    const contentCacheKey = tabId === "info" ? "infoTab" : tabId;

    if (cache.has(contentCacheKey)) {
      renderTabContent(tabId, cache.get(contentCacheKey));
      return;
    }

    renderSkeletonPanel(panel);
    try {
      const { payload, notFound } = tabId === "info" ? { payload: cache.get("info"), notFound: false } : await fetchTab(tabId);
      if (notFound) {
        panel.innerHTML = "";
        panel.appendChild(emptyState("Ce fournisseur est introuvable."));
        return;
      }
      if (tabId === "info") {
        try {
          const { payload: configPayload } = await fetchTab("config");
          payload.code = configPayload.code;
        } catch {
          payload.code = { available: false, reason: "Indisponible" };
        }
      }
      cache.set(contentCacheKey, payload);
      renderTabContent(tabId, payload);
    } catch {
      panel.innerHTML = "";
      panel.appendChild(el("p", "admin-empty admin-card-error", "Impossible de charger cet onglet. Réessaie dans un instant."));
    }
  }

  function renderTabContent(tabId, data) {
    panel.innerHTML = "";
    panel.appendChild(TAB_RENDERERS[tabId](data));
  }

  renderTabsNav();
  await switchTab(activeTab);
}
