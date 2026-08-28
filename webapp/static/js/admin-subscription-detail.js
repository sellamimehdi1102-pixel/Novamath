// Fiche détaillée d'un abonnement (/admin/subscriptions/:plan) — 5 onglets,
// CHACUN chargé par sa propre API au moment où il est ouvert pour la
// première fois (lazy loading réel, cache par onglet) — même architecture
// que admin-ai-provider.js/admin-user-profile.js. L'onglet "IA" a été
// retiré : il n'était qu'un miroir en lecture seule de la section
// "Fournisseurs IA par plan" déjà éditable sur la page Abonnements
// (admin-subscriptions.js) — un seul endroit affiche désormais cette liste,
// avec un lien direct depuis l'onglet Informations.
import { apiCall } from "./admin-subscriptions.js";

const EMPTY_LABEL = "Aucune donnée disponible";

const TABS = [
  { id: "info", label: "Informations" },
  { id: "pricing", label: "Tarification" },
  { id: "features", label: "Fonctionnalités" },
  { id: "users", label: "Utilisateurs" },
  { id: "history", label: "Historique" },
];

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function formatInt(value) {
  return new Intl.NumberFormat("fr-FR").format(value);
}

function formatDateTime(iso) {
  if (!iso) return EMPTY_LABEL;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString("fr-FR", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

function formatPrice(cents, currency) {
  if (cents === 0) return "Gratuit";
  const amount = new Intl.NumberFormat("fr-FR", { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(cents / 100);
  const symbol = (currency || "").toLowerCase() === "eur" ? "€" : (currency || "").toUpperCase();
  return `${amount} ${symbol}`;
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

// ── En-tête ───────────────────────────────────────────────────────────────
function renderHeader(info, plan, { onChanged }) {
  const head = document.getElementById("admin-subscription-detail-head");
  head.innerHTML = "";

  const avatarWrap = el("span", "admin-avatar admin-avatar--lg");
  avatarWrap.textContent = (info.name || "?").trim().charAt(0).toUpperCase();
  head.appendChild(avatarWrap);

  const meta = el("div", "admin-user-profile-meta");
  meta.appendChild(el("h1", "admin-user-profile-name", info.name));
  meta.appendChild(el("p", "admin-user-profile-email", `${formatInt(info.user_count.value)} utilisateur(s)`));
  const badges = el("div", "admin-user-profile-badges");
  badges.appendChild(el("span", `admin-status-dot admin-status-dot--${info.active ? "ok" : "down"}`,
    info.active ? "Actif" : "Inactif"));
  meta.appendChild(badges);
  head.appendChild(meta);

  const actions = el("div", "admin-ai-provider-card-actions");
  const editBtn = el("button", "admin-btn admin-btn--sm", "Modifier");
  editBtn.type = "button";
  editBtn.addEventListener("click", () => openEditModal(plan, onChanged));
  actions.appendChild(editBtn);

  const refreshBtn = el("button", "admin-btn admin-btn--sm", "Actualiser");
  refreshBtn.type = "button";
  refreshBtn.addEventListener("click", onChanged);
  actions.appendChild(refreshBtn);

  head.appendChild(actions);
}

// ── Modale d'édition du catalogue ────────────────────────────────────────
async function openEditModal(plan, onSaved) {
  const [infoRes, pricingRes, featuresRes] = await Promise.all([
    apiCall(`/api/admin/subscriptions/${plan}/info`),
    apiCall(`/api/admin/subscriptions/${plan}/pricing`),
    apiCall(`/api/admin/subscriptions/${plan}/features`),
  ]);
  const info = infoRes.payload;
  const pricing = pricingRes.payload;
  const features = featuresRes.payload;

  const overlay = document.getElementById("admin-ai-provider-modal");
  const title = document.getElementById("admin-ai-provider-modal-title");
  const body = document.getElementById("admin-ai-provider-modal-body");
  const closeBtn = document.getElementById("admin-ai-provider-modal-close");

  title.textContent = `Modifier ${info.name}`;
  body.innerHTML = "";

  const banner = el("div", "admin-form-banner");
  banner.hidden = true;
  body.appendChild(banner);

  const form = document.createElement("form");
  form.className = "admin-form-grid";

  function field(labelText, key, { type = "text", full = false, value = "" } = {}) {
    const wrap = el("div", `admin-form-field${full ? " admin-form-field--full" : ""}`);
    wrap.dataset.field = key;
    wrap.appendChild(el("label", "admin-form-label", labelText));
    const input = document.createElement(type === "textarea" ? "textarea" : "input");
    input.className = type === "textarea" ? "admin-form-textarea" : "admin-form-input";
    input.name = key;
    if (type !== "textarea") input.type = type;
    if (type === "number") input.min = "0";
    input.value = value;
    wrap.appendChild(input);
    form.appendChild(wrap);
    return input;
  }

  const nameInput = field("Nom", "name", { value: info.name });
  const orderInput = field("Ordre d'affichage", "display_order", { type: "number", value: info.display_order });
  const priceInput = field("Prix (centimes)", "price_amount_cents", {
    type: "number", value: pricing.price_amount_cents.available ? pricing.price_amount_cents.value : "",
  });
  const currencyInput = field("Devise", "currency", { value: pricing.currency.available ? pricing.currency.value : "" });
  const durationInput = field("Durée", "duration_label", { value: pricing.duration_label.available ? pricing.duration_label.value : "" });
  const dailyInput = field("Quota quotidien (catalogue)", "quota_daily", {
    type: "number", value: features.quota_daily.available ? features.quota_daily.value : "",
  });
  const chatbotInput = field("Quota chatbot (catalogue)", "quota_chatbot", {
    type: "number", value: features.quota_chatbot.available ? features.quota_chatbot.value : "",
  });

  const descInput = field("Description", "description", { type: "textarea", full: true, value: info.description.available ? info.description.value : "" });
  const advantagesInput = field("Avantages (un par ligne)", "advantages", { type: "textarea", full: true, value: features.advantages.join("\n") });
  const limitsInput = field("Limites (un par ligne)", "limits", { type: "textarea", full: true, value: features.limits.join("\n") });

  const activeWrap = el("div", "admin-form-field admin-form-field--full admin-form-checkbox-row");
  const activeInput = document.createElement("input");
  activeInput.type = "checkbox";
  activeInput.checked = info.active;
  activeWrap.appendChild(activeInput);
  activeWrap.appendChild(el("span", null, "Abonnement actif"));
  form.appendChild(activeWrap);

  const actionsRow = el("div", "admin-form-field--full admin-form-actions");
  const cancelBtn = el("button", "admin-btn", "Annuler");
  cancelBtn.type = "button";
  const saveBtn = el("button", "admin-btn admin-btn--primary", "Sauvegarder");
  saveBtn.type = "submit";
  actionsRow.appendChild(cancelBtn);
  actionsRow.appendChild(saveBtn);
  form.appendChild(actionsRow);

  function closeModal() { overlay.hidden = true; }
  cancelBtn.addEventListener("click", closeModal);
  closeBtn.onclick = closeModal;
  overlay.onclick = (e) => { if (e.target === overlay) closeModal(); };

  const toLines = (text) => text.split("\n").map((l) => l.trim()).filter(Boolean);
  const toIntOrNull = (text) => (text.trim() === "" ? null : Number(text));

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    banner.hidden = true;
    form.querySelectorAll(".admin-form-field--invalid").forEach((n) => n.classList.remove("admin-form-field--invalid"));
    form.querySelectorAll(".admin-form-error").forEach((n) => n.remove());

    const payload = {
      name: nameInput.value,
      description: descInput.value,
      display_order: Number(orderInput.value),
      price_amount_cents: toIntOrNull(priceInput.value),
      currency: currencyInput.value,
      duration_label: durationInput.value,
      quota_daily: toIntOrNull(dailyInput.value),
      quota_chatbot: toIntOrNull(chatbotInput.value),
      advantages: toLines(advantagesInput.value),
      limits: toLines(limitsInput.value),
      active: activeInput.checked,
    };

    saveBtn.disabled = true;
    const { ok, payload: res } = await apiCall(`/api/admin/subscriptions/${plan}`, { method: "PUT", body: payload });
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

// ── 1. Informations ───────────────────────────────────────────────────────
function renderInfoTab(data) {
  const grid = el("div", "admin-fields-grid");
  grid.appendChild(fieldRow("Nom", { available: true, value: data.name }));
  grid.appendChild(fieldRow("Description", data.description));
  grid.appendChild(fieldRow("Actif", { available: true, value: data.active }, (v) => (v ? "Oui" : "Non")));
  grid.appendChild(fieldRow("Ordre d'affichage", { available: true, value: data.display_order }));
  grid.appendChild(fieldRow("Utilisateurs", { available: true, value: data.user_count.value }, formatInt));
  grid.appendChild(fieldRow("Créé le", data.created_at, formatDateTime));
  grid.appendChild(fieldRow("Mis à jour le", data.updated_at, formatDateTime));

  const wrap = el("div");
  wrap.appendChild(grid);
  const aiLink = document.createElement("a");
  aiLink.href = "/admin/subscriptions#admin-subscriptions-ai-title";
  aiLink.className = "admin-btn admin-btn--sm";
  aiLink.textContent = "Fournisseurs IA assignés à ce plan";
  wrap.appendChild(aiLink);
  return wrap;
}

// ── 2. Tarification ─────────────────────────────────────────────────────
function renderPricingTab(data) {
  const wrap = el("div");
  const grid = el("div", "admin-fields-grid");
  const currency = data.currency.available ? data.currency.value : null;
  grid.appendChild(fieldRow("Prix", data.price_amount_cents, (v) => formatPrice(v, currency)));
  grid.appendChild(fieldRow("Devise", data.currency));
  grid.appendChild(fieldRow("Durée", data.duration_label));
  wrap.appendChild(grid);
  wrap.appendChild(el("p", "admin-form-hint", data.note));
  return wrap;
}

// ── 3. Fonctionnalités ────────────────────────────────────────────────────
function bulletList(items) {
  if (!items.length) return el("p", "admin-empty", EMPTY_LABEL);
  const ul = document.createElement("ul");
  ul.className = "admin-bullet-list";
  items.forEach((item) => ul.appendChild(el("li", null, item)));
  return ul;
}

export function renderFeaturesTab(data) {
  const wrap = el("div");

  // Bloc 1 — catalogue cosmétique : texte marketing affiché aux élèves,
  // modifiable ici, mais SANS AUCUN effet sur le comportement réel du
  // produit (voir plan_service.py::FEATURE_MATRIX pour ce qui compte
  // vraiment). Les deux blocs ne doivent jamais être fusionnés visuellement
  // — c'est précisément la confusion que ce chantier corrige.
  const catalogBlock = el("div", "admin-feature-block admin-feature-block--catalog");
  catalogBlock.appendChild(el("h3", "admin-feature-block-title", "📄 Catalogue / présentation (modifiable)"));
  catalogBlock.appendChild(el("p", "admin-form-hint", "Texte commercial affiché aux élèves sur la page d'offres. Le modifier ne change RIEN au comportement réel du produit — voir le bloc ci-dessous pour ce qui est réellement appliqué."));

  catalogBlock.appendChild(el("h4", "admin-section-title", "Avantages affichés"));
  catalogBlock.appendChild(bulletList(data.advantages));

  catalogBlock.appendChild(el("h4", "admin-section-title", "Limites affichées"));
  catalogBlock.appendChild(bulletList(data.limits));

  catalogBlock.appendChild(el("h4", "admin-section-title", "Quotas catalogue"));
  const quotaGrid = el("div", "admin-fields-grid");
  quotaGrid.appendChild(fieldRow("Quota quotidien", data.quota_daily, formatInt));
  quotaGrid.appendChild(fieldRow("Quota chatbot", data.quota_chatbot, formatInt));
  catalogBlock.appendChild(quotaGrid);
  wrap.appendChild(catalogBlock);

  // Bloc 2 — vérité fonctionnelle réelle : dérivé de plan_service.py, jamais
  // éditable depuis cette interface (lecture seule, aucun formulaire).
  const realBlock = el("div", "admin-feature-block admin-feature-block--real");
  realBlock.appendChild(el("h3", "admin-feature-block-title", "✅ Fonctionnalités réellement appliquées (lecture seule)"));
  realBlock.appendChild(el("p", "admin-form-hint", data.real_note));
  const featChips = el("div", "admin-users-filters");
  data.real_features.forEach((f) => featChips.appendChild(el("span", "admin-badge admin-badge--neutral", f.label)));
  realBlock.appendChild(featChips);

  realBlock.appendChild(el("h4", "admin-section-title", "Quotas réellement appliqués aujourd'hui"));
  const realQuotaGrid = el("div", "admin-fields-grid");
  data.real_quotas.forEach((q) => {
    realQuotaGrid.appendChild(fieldRow(q.label, { available: true, value: q.unlimited ? "Illimité" : q.limit }));
  });
  realBlock.appendChild(realQuotaGrid);
  wrap.appendChild(realBlock);

  return wrap;
}

// ── 4. Utilisateurs ────────────────────────────────────────────────────────
function renderUsersTab(data, { onPageChange }) {
  const wrap = el("div");
  if (!data.items.length) {
    wrap.appendChild(emptyState());
    return wrap;
  }
  const table = el("table", "admin-users-table");
  const thead = document.createElement("thead");
  const theadRow = el("tr");
  ["Nom", "Email", "Rôle", "Dernière connexion"].forEach((label) => theadRow.appendChild(el("th", "admin-users-th", label)));
  thead.appendChild(theadRow);
  table.appendChild(thead);
  const tbody = document.createElement("tbody");
  data.items.forEach((user) => {
    const tr = el("tr", "admin-users-row");
    tr.appendChild(el("td", "admin-users-td", user.name));
    tr.appendChild(el("td", "admin-users-td admin-users-td--muted admin-users-td--wrap", user.email));
    tr.appendChild(el("td", "admin-users-td", user.role));
    tr.appendChild(el("td", "admin-users-td", user.last_login_at ? formatDateTime(user.last_login_at) : "Jamais connecté"));
    tbody.appendChild(tr);
  });
  table.appendChild(tbody);
  const tableWrap = el("div", "admin-users-table-wrap");
  tableWrap.appendChild(table);
  wrap.appendChild(tableWrap);

  const pagination = el("nav", "admin-users-pagination");
  pagination.appendChild(el("span", "admin-users-pagination-info",
    `Page ${data.page} / ${data.total_pages} · ${formatInt(data.total)} utilisateur(s)`));
  const prev = el("button", "admin-icon-btn admin-users-page-btn", "‹");
  prev.type = "button";
  prev.disabled = data.page <= 1;
  prev.addEventListener("click", () => onPageChange(data.page - 1));
  pagination.appendChild(prev);
  const next = el("button", "admin-icon-btn admin-users-page-btn", "›");
  next.type = "button";
  next.disabled = data.page >= data.total_pages;
  next.addEventListener("click", () => onPageChange(data.page + 1));
  pagination.appendChild(next);
  wrap.appendChild(pagination);

  return wrap;
}

// ── 5. Historique ──────────────────────────────────────────────────────────
function renderHistoryTab(data, { onPageChange }) {
  const wrap = el("div");
  if (!data.items.length) {
    wrap.appendChild(emptyState());
    return wrap;
  }
  const table = el("table", "admin-users-table");
  const thead = document.createElement("thead");
  const theadRow = el("tr");
  ["Date", "Administrateur", "Action", "Résultat"].forEach((label) => theadRow.appendChild(el("th", "admin-users-th", label)));
  thead.appendChild(theadRow);
  table.appendChild(thead);
  const tbody = document.createElement("tbody");
  data.items.forEach((entry) => {
    const tr = el("tr", "admin-users-row");
    tr.appendChild(el("td", "admin-users-td", formatDateTime(entry.created_at)));
    tr.appendChild(el("td", "admin-users-td", entry.admin.name));
    tr.appendChild(el("td", "admin-users-td", entry.action_label));
    tr.appendChild(el("td", "admin-users-td", entry.result === "success" ? "Succès" : "Échec"));
    tbody.appendChild(tr);
  });
  table.appendChild(tbody);
  const tableWrap = el("div", "admin-users-table-wrap");
  tableWrap.appendChild(table);
  wrap.appendChild(tableWrap);

  const pagination = el("nav", "admin-users-pagination");
  pagination.appendChild(el("span", "admin-users-pagination-info", `Page ${data.page} / ${data.total_pages}`));
  const prev = el("button", "admin-icon-btn admin-users-page-btn", "‹");
  prev.type = "button";
  prev.disabled = data.page <= 1;
  prev.addEventListener("click", () => onPageChange(data.page - 1));
  pagination.appendChild(prev);
  const next = el("button", "admin-icon-btn admin-users-page-btn", "›");
  next.type = "button";
  next.disabled = data.page >= data.total_pages;
  next.addEventListener("click", () => onPageChange(data.page + 1));
  pagination.appendChild(next);
  wrap.appendChild(pagination);

  return wrap;
}

function renderSkeletonPanel(panel) {
  panel.innerHTML = "";
  for (let i = 0; i < 4; i += 1) panel.appendChild(el("div", "admin-skeleton admin-tab-skeleton-row"));
}

export async function loadSubscriptionDetail(plan) {
  const tabsNav = document.getElementById("admin-subscription-detail-tabs");
  const panel = document.getElementById("admin-subscription-detail-panel");
  const cache = new Map();
  let activeTab = "info";
  let usersPage = 1;
  let historyPage = 1;

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

  async function fetchJson(path) {
    const res = await fetch(path, { credentials: "same-origin" });
    const payload = await res.json().catch(() => ({}));
    if (res.status === 404) return { notFound: true };
    if (!res.ok) throw new Error(payload.error || `Erreur API (${res.status})`);
    return { payload };
  }

  async function reloadAll() {
    cache.clear();
    await switchTab(activeTab);
  }

  async function switchTab(tabId) {
    activeTab = tabId;
    renderTabsNav();

    if (!cache.has("info")) {
      try {
        const { payload, notFound } = await fetchJson(`/api/admin/subscriptions/${plan}/info`);
        if (!notFound) { cache.set("info", payload); renderHeader(payload, plan, { onChanged: reloadAll }); }
      } catch { /* en-tête non critique */ }
    } else {
      renderHeader(cache.get("info"), plan, { onChanged: reloadAll });
    }

    const cacheKey = tabId === "users" ? `users-${usersPage}` : tabId === "history" ? `history-${historyPage}` : tabId;
    if (cache.has(cacheKey)) {
      renderTabContent(tabId, cache.get(cacheKey));
      return;
    }

    renderSkeletonPanel(panel);
    try {
      let path = `/api/admin/subscriptions/${plan}/${tabId}`;
      if (tabId === "users") path += `?page=${usersPage}`;
      if (tabId === "history") path += `?page=${historyPage}`;
      const { payload, notFound } = await fetchJson(path);
      if (notFound) {
        panel.innerHTML = "";
        panel.appendChild(emptyState("Cet abonnement est introuvable."));
        return;
      }
      cache.set(cacheKey, payload);
      renderTabContent(tabId, payload);
    } catch {
      panel.innerHTML = "";
      panel.appendChild(el("p", "admin-empty admin-card-error", "Impossible de charger cet onglet. Réessaie dans un instant."));
    }
  }

  function renderTabContent(tabId, data) {
    panel.innerHTML = "";
    if (tabId === "info") panel.appendChild(renderInfoTab(data));
    else if (tabId === "pricing") panel.appendChild(renderPricingTab(data));
    else if (tabId === "features") panel.appendChild(renderFeaturesTab(data));
    else if (tabId === "users") {
      panel.appendChild(renderUsersTab(data, {
        plan, page: usersPage,
        onPageChange: (p) => { usersPage = p; switchTab("users"); },
      }));
    } else if (tabId === "history") {
      panel.appendChild(renderHistoryTab(data, {
        onPageChange: (p) => { historyPage = p; switchTab("history"); },
      }));
    }
  }

  renderTabsNav();
  await switchTab(activeTab);
}
