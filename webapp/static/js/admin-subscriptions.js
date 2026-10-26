// Module "Abonnements" (/admin/subscriptions) — panneau d'administration
// complet des 3 plans Mathadap (Free/Premium/Ultra) : catalogue (nom/
// description/prix/durée/avantages/limites/quotas), nombre réel
// d'utilisateurs par plan, activation/désactivation, ET assignation des
// fournisseurs IA par plan (section repliable "Fournisseurs IA par plan" —
// seul endroit de l'admin où cette information est éditable ; la page IA
// n'affiche plus que la configuration technique des fournisseurs, voir
// admin-ai.js). IMPORTANT : ce module ne modifie JAMAIS les droits/quotas
// réellement appliqués au chatbot (voir admin_subscriptions_service.py) ni
// la facturation Stripe réelle — le prix édité ici est un champ catalogue.
//
// Audit admin (2026-10-22) : les cartes "Nouveaux abonnements (30j)"/
// "Résiliations (30j)" ont été retirées d'ici — ces compteurs agrégés
// dupliquaient exactement ceux du module Finance (admin-finance.js),
// devenu la seule référence pour les indicateurs d'abonnement agrégés (voir
// admin_subscriptions_service.py::get_overview pour le détail).
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
  const amount = new Intl.NumberFormat("fr-FR", { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(
    cents / 100,
  );
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

// ── Réconciliation Stripe (lecture seule, audit admin 2026-10-20) ─────────
const STRIPE_RECONCILE_MODE_LABELS = { test: "mode TEST", production: "mode PRODUCTION", etat_inconnu: "état inconnu" };

// Garde-fou Stripe production (2026-10-20) : la vraie protection est côté
// serveur (voir stripe_reconciliation_service.py, qui refuse 403/409 même
// sur un appel direct à l'API) — ce bandeau ne fait qu'expliquer pourquoi le
// bouton est grisé ou va demander une confirmation, jamais la protection
// elle-même.
function renderStripeEnvironment(container, env) {
  container.innerHTML = "";
  if (!env) return;
  const modeLabel = STRIPE_RECONCILE_MODE_LABELS[env.mode] || env.mode;
  const envLabel = env.app_environment === "production" ? "production" : "développement";
  container.appendChild(
    el("p", "admin-form-hint", `Stripe ciblé : ${modeLabel} — serveur en environnement de ${envLabel}.`),
  );
  if (env.reconciliation_blocked) {
    container.appendChild(
      el(
        "p",
        "admin-form-hint admin-form-hint--warning",
        "Réconciliation bloquée : Stripe est en mode PRODUCTION mais ce serveur tourne en développement. " +
          "Aucun appel réel vers Stripe production n'est autorisé depuis ce poste.",
      ),
    );
  } else if (env.reconciliation_requires_confirmation) {
    container.appendChild(
      el(
        "p",
        "admin-form-hint admin-form-hint--warning",
        "Attention : une confirmation explicite sera demandée avant d'interroger de vrais abonnements Stripe.",
      ),
    );
  }
}

function renderReconcileResult(container, report) {
  container.innerHTML = "";
  const modeLabel = STRIPE_RECONCILE_MODE_LABELS[report.mode] || report.mode;
  container.appendChild(
    el("p", "admin-form-hint", `${report.checked} compte(s) vérifié(s) sur ${report.total} (${modeLabel}).`),
  );
  if (report.divergences.length === 0 && report.errors.length === 0) {
    container.appendChild(emptyState("Aucune divergence détectée sur ce lot."));
  }
  if (report.divergences.length > 0) {
    const table = el("table", "admin-table");
    const thead = el("thead");
    const headRow = el("tr");
    ["Utilisateur", "Abonnement Stripe", "Statut local", "Statut Stripe réel"].forEach((label) =>
      headRow.appendChild(el("th", null, label)),
    );
    thead.appendChild(headRow);
    table.appendChild(thead);
    const tbody = el("tbody");
    report.divergences.forEach((d) => {
      const row = el("tr");
      row.appendChild(el("td", null, d.email));
      row.appendChild(el("td", null, d.stripe_subscription_id));
      row.appendChild(el("td", null, d.local_status || "—"));
      row.appendChild(el("td", null, d.stripe_status || "—"));
      tbody.appendChild(row);
    });
    table.appendChild(tbody);
    container.appendChild(table);
  }
  if (report.errors.length > 0) {
    container.appendChild(
      el(
        "p",
        "admin-form-error",
        `${report.errors.length} compte(s) n'ont pas pu être vérifiés (erreur réseau/Stripe) — réessaie plus tard.`,
      ),
    );
  }
  if (report.has_more) {
    container.appendChild(
      el("p", "admin-form-hint", "D'autres comptes restent à vérifier (lot suivant non lancé automatiquement)."),
    );
  }
}

async function runReconcile(resultEl, { confirmed = false } = {}) {
  return apiCall("/api/admin/subscriptions/reconcile-stripe", {
    method: "POST",
    body: { confirmed },
  });
}

function wireReconcileButton(env) {
  const btn = document.getElementById("admin-subscriptions-reconcile-btn");
  const resultEl = document.getElementById("admin-subscriptions-reconcile-result");
  if (!btn || !resultEl) return;

  // Blocage DUR déjà appliqué côté serveur (403, non contournable) — le
  // bouton est aussi désactivé ici pour ne pas laisser l'admin cliquer dans
  // le vide, mais ce n'est qu'un confort d'interface : voir
  // stripe_reconciliation_service.py pour la vraie protection.
  if (env && env.reconciliation_blocked) {
    btn.disabled = true;
    btn.textContent = "Réconciliation bloquée (Stripe production depuis un poste de développement)";
    return;
  }

  btn.disabled = false;
  const baseLabel = "Lancer une réconciliation (lecture seule)";
  btn.textContent = baseLabel;

  btn.onclick = async () => {
    // Confirmation explicite obligatoire côté serveur (409) quand Stripe ET
    // ce serveur sont tous deux en PRODUCTION — demandée AVANT tout appel
    // réseau pour ne jamais déclencher un premier lot d'appels Stripe réels
    // sans consentement explicite de l'admin.
    let confirmed = false;
    if (env && env.reconciliation_requires_confirmation) {
      confirmed = window.confirm(
        "Cette réconciliation va interroger de VRAIS abonnements Stripe en PRODUCTION " +
          "(lecture seule, aucune modification). Confirmer le lancement ?",
      );
      if (!confirmed) return;
    }

    btn.disabled = true;
    const originalLabel = btn.textContent;
    btn.textContent = "Réconciliation en cours...";
    resultEl.innerHTML = "";
    try {
      const { ok, status, payload } = await runReconcile(resultEl, { confirmed });
      if (!ok) {
        resultEl.innerHTML = "";
        let message = "La réconciliation a échoué. Réessaie dans un instant.";
        if (status === 501) {
          message = payload.error || "Stripe n'est pas configuré sur ce serveur.";
        } else if (status === 403) {
          message =
            payload.error || "Réconciliation bloquée (Stripe production depuis un environnement non-production).";
        } else if (status === 409) {
          message = payload.error || "Confirmation requise avant de lancer cette réconciliation.";
        }
        resultEl.appendChild(el("p", "admin-form-error", message));
        return;
      }
      renderReconcileResult(resultEl, payload);
    } catch {
      resultEl.innerHTML = "";
      resultEl.appendChild(
        el("p", "admin-form-error", "La réconciliation a échoué (réseau). Réessaie dans un instant."),
      );
    } finally {
      btn.disabled = false;
      btn.textContent = originalLabel;
    }
  };
}

// ── Cartes de plans ───────────────────────────────────────────────────────
function renderPlanCard(plan, { onPlanClick, onChanged }) {
  const card = el("article", "admin-card admin-ai-provider-card");
  card.tabIndex = 0;
  card.setAttribute("role", "button");
  card.addEventListener("click", () => onPlanClick(plan.plan));
  card.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      onPlanClick(plan.plan);
    }
  });

  const head = el("div", "admin-ai-provider-card-head");
  head.appendChild(el("span", "admin-ai-provider-card-name", plan.name));
  head.appendChild(
    el("span", `admin-status-dot admin-status-dot--${plan.active ? "ok" : "down"}`, plan.active ? "Actif" : "Inactif"),
  );
  card.appendChild(head);

  card.appendChild(el("div", "admin-card-sub", fieldValue(plan.description)));
  const currency = plan.currency.available ? plan.currency.value : null;
  card.appendChild(
    el(
      "div",
      "admin-card-sub",
      `${fieldValue(plan.price_amount_cents, (v) => formatPrice(v, currency))} / ${fieldValue(plan.duration_label)}`,
    ),
  );
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
      method: "PATCH",
      body: { active: toggleInput.checked },
    });
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
        method: "PUT",
        body: { provider_ids: providerIds },
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

  const providersPayload =
    providersRes.status === "fulfilled" && providersRes.value.ok
      ? await providersRes.value.json().catch(() => null)
      : null;
  const subscriptionsPayload =
    subscriptionsRes.status === "fulfilled" && subscriptionsRes.value.ok
      ? await subscriptionsRes.value.json().catch(() => null)
      : null;

  if (providersPayload === null || subscriptionsPayload === null) {
    editorEl.appendChild(
      el("p", "admin-empty admin-card-error", "Impossible de charger les fournisseurs IA. Réessaie dans un instant."),
    );
    return;
  }

  const allProviders = providersPayload.providers ? providersPayload.providers : [];
  renderAiAssignmentEditor(editorEl, subscriptionsPayload, allProviders, onChanged);
}

// ── Point d'entrée ────────────────────────────────────────────────────────
export async function loadSubscriptionsOverview(onPlanClick) {
  const plansEl = document.getElementById("admin-subscriptions-plans");
  const aiAssignmentEl = document.getElementById("admin-subscriptions-ai-assignment");
  const errorEl = document.getElementById("admin-global-error");

  renderPlansSkeleton(plansEl);
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
    plansEl.appendChild(
      el("p", "admin-empty admin-card-error", "Impossible de charger les abonnements. Réessaie dans un instant."),
    );
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
  const stripeEnvEl = document.getElementById("admin-subscriptions-stripe-environment");
  if (stripeEnvEl) renderStripeEnvironment(stripeEnvEl, res.stripe_environment);
  wireReconcileButton(res.stripe_environment);

  if (aiAssignmentEl) {
    await loadAiAssignment(aiAssignmentEl, refresh);
  }
}
