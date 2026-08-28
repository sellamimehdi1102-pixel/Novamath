// Module "Abonnements" (/admin/subscriptions) — panneau d'administration
// complet des 3 plans NovaMath (Free/Premium/Ultra) : catalogue (nom/
// description/prix/durée/avantages/limites/quotas), statistiques réelles
// (nombre d'utilisateurs, nouveaux abonnés, résiliations), activation/
// désactivation, ET assignation des fournisseurs IA par plan (section
// repliable "Fournisseurs IA par plan" — seul endroit de l'admin où cette
// information est éditable ; la page IA n'affiche plus que la configuration
// technique des fournisseurs, voir admin-ai.js). IMPORTANT : ce module ne
// modifie JAMAIS les droits/quotas réellement appliqués au chatbot (voir
// admin_subscriptions_service.py) ni la facturation Stripe réelle — le prix
// édité ici est un champ catalogue.
import { createCollapseSection, wireCollapsePersistence } from "./admin-collapse.js";

const EMPTY_LABEL = "Aucune donnée disponible";

const SUBSCRIPTION_LABELS = { free: "Free", premium: "Premium", ultra: "Ultra" };
const SUBSCRIPTION_ORDER = ["free", "premium", "ultra"];

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function formatInt(value) {
  return new Intl.NumberFormat("fr-FR").format(value);
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

function fieldValue(metric, formatter = (v) => v) {
  if (!metric || !metric.available) return EMPTY_LABEL;
  return formatter(metric.value);
}

// ── Cartes de statistiques globales ─────────────────────────────────────
function statCard(label, metric, formatter = formatInt) {
  const card = el("article", "admin-card");
  card.appendChild(el("div", "admin-card-label", label));
  if (!metric.available) {
    card.appendChild(el("div", "admin-card-value admin-card-value--empty", EMPTY_LABEL));
    card.appendChild(el("div", "admin-card-sub", metric.reason));
  } else {
    card.appendChild(el("div", "admin-card-value", formatter(metric.value)));
  }
  return card;
}

function renderStats(container, stats) {
  container.innerHTML = "";
  container.appendChild(statCard(`Nouveaux abonnés (${stats.window_days}j)`, stats.new_subscribers));
  container.appendChild(statCard(`Résiliations (${stats.window_days}j)`, stats.cancellations));
}

// ── Cartes de plans ───────────────────────────────────────────────────────
function renderPlanCard(plan, { onPlanClick, onChanged }) {
  const card = el("article", "admin-card admin-ai-provider-card");
  card.tabIndex = 0;
  card.setAttribute("role", "button");
  card.addEventListener("click", () => onPlanClick(plan.plan));
  card.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onPlanClick(plan.plan); }
  });

  const head = el("div", "admin-ai-provider-card-head");
  head.appendChild(el("span", "admin-ai-provider-card-name", plan.name));
  head.appendChild(el("span", `admin-status-dot admin-status-dot--${plan.active ? "ok" : "down"}`,
    plan.active ? "Actif" : "Inactif"));
  card.appendChild(head);

  card.appendChild(el("div", "admin-card-sub", fieldValue(plan.description)));
  const currency = plan.currency.available ? plan.currency.value : null;
  card.appendChild(el("div", "admin-card-sub",
    `${fieldValue(plan.price_amount_cents, (v) => formatPrice(v, currency))} / ${fieldValue(plan.duration_label)}`));
  card.appendChild(el("div", "admin-card-value", `${formatInt(plan.user_count.value)} utilisateur(s)`));

  const actions = el("div", "admin-ai-provider-card-actions");
  const toggleLabel = el("label", "admin-toggle");
  toggleLabel.title = plan.active ? "Désactiver" : "Activer";
  const toggleInput = document.createElement("input");
  toggleInput.type = "checkbox";
  toggleInput.checked = plan.active;
  toggleInput.addEventListener("click", (e) => e.stopPropagation());
  toggleInput.addEventListener("change", async () => {
    const { ok, payload } = await apiCall(`/api/admin/subscriptions/${plan.plan}/active`, {
      method: "PATCH", body: { active: toggleInput.checked },
    });
    if (!ok) { window.alert(payload.error || "Action impossible."); toggleInput.checked = !toggleInput.checked; return; }
    onChanged();
  });
  toggleLabel.appendChild(toggleInput);
  toggleLabel.appendChild(el("span", "admin-toggle-track"));
  actions.appendChild(toggleLabel);
  card.appendChild(actions);

  return card;
}

function renderPlansSkeleton(container) {
  container.innerHTML = "";
  for (let i = 0; i < 3; i += 1) {
    const card = el("article", "admin-card");
    const bar = el("div", "admin-skeleton");
    bar.style.height = "140px";
    card.appendChild(bar);
    container.appendChild(card);
  }
}

// ── Fournisseurs IA par plan (assignation, déplacée depuis admin-ai.js) ──
// Section repliable (voir admin-collapse.js) : liste tous les fournisseurs
// IA existants (module IA, /api/admin/ai/providers) et permet de choisir,
// pour chaque plan Free/Premium/Ultra, lesquels lui sont assignés
// (/api/admin/ai/subscriptions/<plan>, PUT). Seul endroit de l'admin où
// cette assignation se modifie désormais.
function renderAiAssignmentEditor(container, subscriptionsData, allProviders, onChanged) {
  container.innerHTML = "";
  if (!allProviders.length) {
    container.appendChild(emptyState("Aucun fournisseur IA n'est configuré."));
    return;
  }
  const currentByPlan = subscriptionsData.available ? subscriptionsData.value : {};

  const grid = el("div", "admin-ai-subscription-editor");
  SUBSCRIPTION_ORDER.forEach((planKey) => {
    const assigned = new Set((currentByPlan[planKey] || []).map((p) => p.provider_id));
    const card = el("div", "admin-ai-subscription-edit-card");
    card.appendChild(el("div", "admin-ai-subscription-edit-title", SUBSCRIPTION_LABELS[planKey]));

    const checklist = el("div", "admin-ai-subscription-checklist");
    const checkboxes = [];
    allProviders.forEach((provider) => {
      const row = el("label", "admin-form-checkbox-row");
      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.value = String(provider.id);
      checkbox.checked = assigned.has(provider.id);
      checkboxes.push(checkbox);
      row.appendChild(checkbox);
      row.appendChild(el("span", null, `${provider.name} (priorité ${provider.priority})`));
      checklist.appendChild(row);
    });
    card.appendChild(checklist);

    const banner = el("div", "admin-form-error");
    banner.hidden = true;
    card.appendChild(banner);

    const saveBtn = el("button", "admin-btn admin-btn--primary admin-btn--sm", "Enregistrer");
    saveBtn.type = "button";
    saveBtn.addEventListener("click", async () => {
      banner.hidden = true;
      const providerIds = checkboxes.filter((c) => c.checked).map((c) => Number(c.value));
      saveBtn.disabled = true;
      const { ok, payload } = await apiCall(`/api/admin/ai/subscriptions/${planKey}`, {
        method: "PUT", body: { provider_ids: providerIds },
      });
      saveBtn.disabled = false;
      if (!ok) {
        banner.hidden = false;
        banner.textContent = payload.error || "Une erreur est survenue.";
        return;
      }
      onChanged();
    });
    card.appendChild(saveBtn);

    grid.appendChild(card);
  });
  container.appendChild(grid);
}

async function loadAiAssignment(container, onChanged) {
  const [providersRes, subscriptionsRes] = await Promise.allSettled([
    fetch("/api/admin/ai/providers", { credentials: "same-origin" }),
    fetch("/api/admin/ai/subscriptions", { credentials: "same-origin" }),
  ]);

  container.innerHTML = createCollapseSection({
    id: "subscriptions-ai-assignment",
    title: "Fournisseurs IA assignés",
    hint: "Quels fournisseurs sont utilisés par chaque plan",
    open: true,
    bodyHtml: '<div id="admin-subscriptions-ai-editor"></div>',
  });
  wireCollapsePersistence(container);
  const editorEl = container.querySelector("#admin-subscriptions-ai-editor");

  const providersPayload = providersRes.status === "fulfilled" && providersRes.value.ok
    ? await providersRes.value.json().catch(() => null) : null;
  const subscriptionsPayload = subscriptionsRes.status === "fulfilled" && subscriptionsRes.value.ok
    ? await subscriptionsRes.value.json().catch(() => null) : null;

  if (providersPayload === null || subscriptionsPayload === null) {
    editorEl.appendChild(el("p", "admin-empty admin-card-error", "Impossible de charger les fournisseurs IA. Réessaie dans un instant."));
    return;
  }

  const allProviders = providersPayload.providers ? providersPayload.providers : [];
  renderAiAssignmentEditor(editorEl, subscriptionsPayload, allProviders, onChanged);
}

// ── Point d'entrée ────────────────────────────────────────────────────────
export async function loadSubscriptionsOverview(onPlanClick) {
  const plansEl = document.getElementById("admin-subscriptions-plans");
  const statsEl = document.getElementById("admin-subscriptions-stats");
  const aiAssignmentEl = document.getElementById("admin-subscriptions-ai-assignment");
  const errorEl = document.getElementById("admin-global-error");

  renderPlansSkeleton(plansEl);
  statsEl.innerHTML = "";
  if (aiAssignmentEl) aiAssignmentEl.innerHTML = "";
  errorEl.hidden = true;

  const refresh = () => loadSubscriptionsOverview(onPlanClick);

  let res;
  try {
    const r = await fetch("/api/admin/subscriptions", { credentials: "same-origin" });
    const payload = await r.json().catch(() => null);
    if (!r.ok || payload === null) throw new Error(payload && payload.error);
    res = payload;
  } catch {
    plansEl.innerHTML = "";
    plansEl.appendChild(el("p", "admin-empty admin-card-error", "Impossible de charger les abonnements. Réessaie dans un instant."));
    errorEl.hidden = false;
    errorEl.textContent = "Le module Abonnements n'a pas pu être chargé. Réessaie dans un instant.";
    return;
  }

  plansEl.innerHTML = "";
  if (!res.plans) {
    plansEl.appendChild(emptyState(res.reason));
  } else {
    res.plans.forEach((plan) => plansEl.appendChild(renderPlanCard(plan, { onPlanClick, onChanged: refresh })));
  }
  renderStats(statsEl, res.stats);

  if (aiAssignmentEl) {
    await loadAiAssignment(aiAssignmentEl, refresh);
  }
}
