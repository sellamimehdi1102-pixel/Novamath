// Module "Finance" (/admin/finance) — Phase 2A de l'audit admin
// (2026-10-21). Deux familles de données, JAMAIS mélangées visuellement :
// - Abonnements/MRR : chargés automatiquement (local, aucun appel Stripe,
//   toujours instantané) — voir GET /api/admin/finance/overview.
// - Revenus/paiements : chargés UNIQUEMENT sur clic explicite admin (jamais
//   au chargement de la page), car chaque clic déclenche un vrai appel
//   réseau à Stripe — même philosophie que le bouton de réconciliation du
//   module Abonnements (admin-subscriptions.js). Protégé par le même
//   garde-fou backend (403 bloqué / 409 confirmation requise), jamais
//   supposé acquis côté frontend : un échec API affiche un message
//   explicite, jamais un montant à 0 €.
import { Chart } from "chart.js/auto";

const EMPTY_LABEL = "Aucune donnée disponible";

const STRIPE_MODE_LABELS = {
  test: "mode TEST",
  production: "mode PRODUCTION",
  etat_inconnu: "état inconnu",
  non_configure: "non configuré",
};

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function formatInt(value) {
  return new Intl.NumberFormat("fr-FR").format(value);
}

function formatCents(cents, currency) {
  const amount = new Intl.NumberFormat("fr-FR", { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(
    (cents || 0) / 100,
  );
  const symbol = (currency || "").toLowerCase() === "eur" ? "€" : (currency || "").toUpperCase();
  return `${amount} ${symbol}`;
}

function formatDateTime(tsSeconds) {
  if (tsSeconds === null || tsSeconds === undefined) return "—";
  const d = new Date(tsSeconds * 1000);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleString("fr-FR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

async function apiGet(path) {
  const res = await fetch(path, { credentials: "same-origin" });
  const payload = await res.json().catch(() => ({}));
  return { ok: res.ok, status: res.status, payload };
}

function emptyState(message) {
  return el("p", "admin-empty", message || EMPTY_LABEL);
}

function statCard(label, metric, formatter = formatInt) {
  const card = el("article", "admin-card");
  card.appendChild(el("div", "admin-card-label", label));
  if (!metric || !metric.available) {
    card.appendChild(el("div", "admin-card-value admin-card-value--empty", EMPTY_LABEL));
    if (metric && metric.reason) card.appendChild(el("div", "admin-card-sub", metric.reason));
  } else {
    card.appendChild(el("div", "admin-card-value", formatter(metric.value)));
    if (metric.note) card.appendChild(el("div", "admin-card-sub", metric.note));
  }
  return card;
}

// ── Disponibilité Stripe pour les sections Revenus/Paiements ────────────────
// Audit admin (2026-10-22), bug confirmé : le cas "Stripe non configuré du
// tout" (mode "non_configure", clé absente/placeholder — cas réel d'un poste
// de dev local) ou "état inconnu" (clé présente mais préfixe non reconnu)
// n'étaient PAS traités comme bloqués au chargement, contrairement au cas
// "production bloquée" (reconciliation_blocked) qui l'était déjà. Résultat
// avant correctif : sélecteur de période + bouton actifs dès le chargement,
// menant à un 501 après clic, pendant qu'un graphique vide de 240px restait
// affiché en permanence. Les 3 cas sont désormais traités de façon unifiée
// ici : AUCUN des 3 n'est transitoire (contrairement à une erreur réseau),
// donc jamais de bouton "Réessayer" proposé pour l'un d'eux — seul un
// nouveau chargement de page (Stripe reconfiguré) peut changer l'état.
function isFinanceUnavailable(env) {
  return !!env && (env.reconciliation_blocked || env.mode === "non_configure" || env.mode === "etat_inconnu");
}

function unavailableMessage(env) {
  if (env.mode === "non_configure") {
    return (
      "Stripe n'est pas configuré sur ce serveur (STRIPE_SECRET_KEY absente ou valeur placeholder) — aucune donnée " +
      "de revenus/paiements n'est disponible. Les chiffres Abonnements/MRR ci-dessus restent disponibles (calculés " +
      "localement, sans appel Stripe)."
    );
  }
  if (env.mode === "etat_inconnu") {
    return (
      "La clé Stripe configurée ne correspond à aucun préfixe reconnu (ni sk_test_, ni sk_live_) — lecture des " +
      "revenus/paiements désactivée par précaution jusqu'à vérification de la configuration, plutôt que de deviner " +
      "un mode. Les chiffres Abonnements/MRR ci-dessus restent disponibles (calculés localement)."
    );
  }
  // reconciliation_blocked
  return (
    "Lecture des revenus/paiements bloquée : Stripe est en mode PRODUCTION mais ce serveur tourne en " +
    "développement. Aucun appel réel vers Stripe production n'est autorisé depuis ce poste."
  );
}

// ── Bannière d'environnement Stripe — même garde-fou que le module
// Abonnements (Phase 1), recalculé indépendamment côté backend. ─────────────
function renderStripeEnvironment(container, env) {
  container.innerHTML = "";
  if (!env) return;
  const modeLabel = STRIPE_MODE_LABELS[env.mode] || env.mode;
  const envLabel = env.app_environment === "production" ? "production" : "développement";
  container.appendChild(
    el("p", "admin-form-hint", `Source des données : Stripe ${modeLabel} — serveur en environnement de ${envLabel}.`),
  );
  if (env.mode === "non_configure" || env.mode === "etat_inconnu") {
    // 3ᵉ état de bannière (audit 2026-10-22) : jusqu'ici, ce cas n'affichait
    // qu'une phrase neutre ci-dessus, sans alerter que Revenus/Paiements
    // seraient inutilisables (contrairement à reconciliation_blocked, déjà
    // signalé explicitement ci-dessous).
    container.appendChild(el("p", "admin-form-hint admin-form-hint--warning", unavailableMessage(env)));
  } else if (env.reconciliation_blocked) {
    container.appendChild(el("p", "admin-form-hint admin-form-hint--warning", unavailableMessage(env)));
  } else if (env.reconciliation_requires_confirmation) {
    container.appendChild(
      el(
        "p",
        "admin-form-hint admin-form-hint--warning",
        "Attention : une confirmation explicite sera demandée avant d'interroger de vraies données Stripe.",
      ),
    );
  }
}

// ── Abonnements / MRR (local, chargé automatiquement) ───────────────────────
// Audit admin (2026-10-22) : ces chiffres mesurent les abonnements Stripe
// RÉELLEMENT actifs (dernier statut webhook connu 'active'/'trialing' —
// voir la note de chaque carte ci-dessous), une mesure différente et
// légitimement non identique au nombre d'utilisateurs par plan affiché dans
// le module Abonnements (champ users.plan, pas nécessairement synchronisé
// en temps réel) — ce n'est jamais un doublon à fusionner, voir la
// réconciliation Stripe du module Abonnements en cas d'écart suspect.
function renderSubscriptionsOverview(container, subs) {
  container.innerHTML = "";
  const byPlan = subs.active_subscriptions_by_plan;
  const activePremium = byPlan.available ? byPlan.value.premium || 0 : null;
  const activeUltra = byPlan.available ? byPlan.value.ultra || 0 : null;

  container.appendChild(
    statCard(
      "Abonnements actifs — Premium",
      byPlan.available ? { available: true, value: activePremium, note: byPlan.note } : byPlan,
    ),
  );
  container.appendChild(
    statCard(
      "Abonnements actifs — Ultra",
      byPlan.available ? { available: true, value: activeUltra, note: byPlan.note } : byPlan,
    ),
  );
  container.appendChild(statCard("En retard de paiement", subs.past_due_or_unpaid));
  container.appendChild(statCard("Résiliés (état courant)", subs.canceled));
  container.appendChild(statCard(`Nouveaux abonnements (${subs.window_days}j)`, subs.new_subscriptions));
  container.appendChild(statCard(`Résiliations (${subs.window_days}j)`, subs.cancellations));
  // Audit admin (2026-10-22) : le caractère "estimation" doit être visible
  // dans le TITRE de la carte elle-même, pas seulement dans sa note
  // secondaire (voir subs.mrr_cents.note, qui détaille déjà l'hypothèse
  // exacte posée — remises/coupons/changements de prix Stripe ne sont pas
  // détectables sans appel réseau réel, volontairement exclu ici).
  container.appendChild(
    statCard("MRR estimé — hors remises et ajustements Stripe", subs.mrr_cents, (v) => formatCents(v, "eur")),
  );
}

// ── Revenus (Stripe, déclenchement manuel) ──────────────────────────────────
let _revenueChart = null;

function destroyRevenueChart() {
  if (_revenueChart) {
    _revenueChart.destroy();
    _revenueChart = null;
  }
}

function renderRevenueReport(container, report) {
  container.innerHTML = "";
  const cards = el("div", "admin-cards");
  const currencies = Object.keys(report.gross_revenue_cents_by_currency);
  if (!currencies.length) {
    cards.appendChild(emptyState("Aucune facture payée sur cette période."));
  }
  currencies.forEach((currency) => {
    cards.appendChild(
      statCard(
        `Revenu brut (${currency.toUpperCase()})`,
        { available: true, value: report.gross_revenue_cents_by_currency[currency] },
        (v) => formatCents(v, currency),
      ),
    );
    cards.appendChild(
      statCard(
        `Remboursé (${currency.toUpperCase()})`,
        { available: true, value: report.refunded_cents_by_currency[currency] || 0 },
        (v) => formatCents(v, currency),
      ),
    );
    cards.appendChild(
      statCard(
        `Net de remboursements (${currency.toUpperCase()})`,
        {
          available: true,
          value: report.net_of_refunds_cents_by_currency[currency] || 0,
          note: "Brut moins remboursements uniquement — jamais net des frais Stripe (non calculé, voir rapport final).",
        },
        (v) => formatCents(v, currency),
      ),
    );
  });
  container.appendChild(cards);

  const breakdown = el("div", "admin-finance-breakdown");
  breakdown.appendChild(el("h3", "admin-health-chart-title", "Ventilation par plan (meilleur effort)"));
  const planEntries = Object.entries(report.gross_revenue_cents_by_plan || {});
  if (!planEntries.length) {
    breakdown.appendChild(emptyState());
  } else {
    const list = el("ul", "admin-finance-plan-list");
    planEntries.forEach(([plan, cents]) => {
      list.appendChild(el("li", null, `${plan} : ${formatCents(cents, currencies[0] || "eur")}`));
    });
    breakdown.appendChild(list);
  }
  container.appendChild(breakdown);

  if (report.capped) {
    container.appendChild(
      el(
        "p",
        "admin-form-error",
        "Rapport incomplet : la limite de pagination a été atteinte, ce total ne couvre pas toute la période.",
      ),
    );
  }
  container.appendChild(
    el(
      "p",
      "admin-form-hint",
      `${report.invoices_checked} facture(s) payée(s) et ${report.refunds_checked} remboursement(s) vérifiés — période de ${report.window_days} jour(s).`,
    ),
  );
}

function renderRevenueSeries(box, series) {
  // La classe qui réserve 240px (.admin-health-chart-box, partagée avec les
  // autres modules à graphique) n'est ajoutée qu'ICI, au moment où une vraie
  // série est rendue — jamais présente statiquement dans admin.html (voir
  // wireFinanceButtons) pour ne pas réserver cet espace tant qu'aucune
  // donnée n'est disponible (audit admin 2026-10-22).
  box.classList.add("admin-health-chart-box");
  box.innerHTML = "";
  box.appendChild(el("h3", "admin-health-chart-title", "Évolution des revenus"));
  if (!series.series.length) {
    box.appendChild(emptyState("Aucune facture payée sur cette période."));
    return;
  }
  destroyRevenueChart();
  const canvas = document.createElement("canvas");
  box.appendChild(canvas);
  _revenueChart = new Chart(canvas, {
    type: "line",
    data: {
      labels: series.series.map((p) => p.month),
      datasets: [
        {
          label: "Revenu brut",
          data: series.series.map((p) => p.gross_revenue_cents / 100),
          borderColor: "#7c5cff",
          backgroundColor: "#7c5cff33",
          fill: true,
          tension: 0.25,
          borderWidth: 2,
          pointRadius: 2,
        },
        {
          label: "Net de remboursements",
          data: series.series.map((p) => p.net_of_refunds_cents / 100),
          borderColor: "#22C55E",
          backgroundColor: "#22C55E33",
          fill: false,
          tension: 0.25,
          borderWidth: 2,
          pointRadius: 2,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: { y: { beginAtZero: true } },
      plugins: { legend: { display: true, position: "bottom" } },
    },
  });
  if (series.capped) {
    box.appendChild(el("p", "admin-form-error", "Série incomplète : limite de pagination atteinte."));
  }
}

// ── Paiements (Stripe, déclenchement manuel) ────────────────────────────────
function renderPaymentsReport(container, report) {
  container.innerHTML = "";
  container.appendChild(
    el(
      "p",
      "admin-form-hint",
      `${report.succeeded_count} paiement(s) réussi(s), ${report.failed_count} échec(s) sur ce lot.`,
    ),
  );
  if (!report.payments.length) {
    container.appendChild(emptyState("Aucun paiement sur cette période."));
    return;
  }
  const table = el("table", "admin-table");
  const thead = el("thead");
  const headRow = el("tr");
  ["Date", "Montant", "Devise", "Statut"].forEach((label) => headRow.appendChild(el("th", null, label)));
  thead.appendChild(headRow);
  table.appendChild(thead);
  const tbody = el("tbody");
  report.payments.forEach((p) => {
    const row = el("tr");
    row.appendChild(el("td", null, formatDateTime(p.created)));
    row.appendChild(el("td", null, formatCents(p.amount, p.currency)));
    row.appendChild(el("td", null, (p.currency || "").toUpperCase()));
    row.appendChild(el("td", null, p.status));
    tbody.appendChild(row);
  });
  table.appendChild(tbody);
  container.appendChild(table);
  if (report.has_more) {
    container.appendChild(
      el("p", "admin-form-hint", "D'autres paiements existent au-delà de ce lot (non chargés automatiquement)."),
    );
  }
}

// ── Déclenchement manuel protégé (confirmation Stripe production) ──────────
async function withStripeConfirmation(env, path, resultEl, onSuccess) {
  let confirmed = false;
  if (env && env.reconciliation_requires_confirmation) {
    confirmed = window.confirm(
      "Cette action va interroger de VRAIES données Stripe en PRODUCTION (lecture seule). Confirmer ?",
    );
    if (!confirmed) return;
  }
  const url = `${path}${path.includes("?") ? "&" : "?"}confirmed=${confirmed}`;
  const { ok, status, payload } = await apiGet(url);
  if (!ok) {
    resultEl.innerHTML = "";
    let message = "Le chargement a échoué. Réessaie dans un instant.";
    if (status === 501) message = payload.error || "Stripe n'est pas configuré sur ce serveur.";
    else if (status === 403)
      message = payload.error || "Lecture bloquée (Stripe production depuis un environnement non-production).";
    else if (status === 409) message = payload.error || "Confirmation requise avant de lancer cette lecture.";
    resultEl.appendChild(el("p", "admin-form-error", message));
    return;
  }
  onSuccess(payload);
}

function wireFinanceButtons(env) {
  const revenueBtn = document.getElementById("admin-finance-revenue-btn");
  const revenueResult = document.getElementById("admin-finance-revenue-result");
  const revenueChartBox = document.getElementById("admin-finance-revenue-chart");
  const periodSelect = document.getElementById("admin-finance-period");
  const periodLabel = document.getElementById("admin-finance-period-label");
  const paymentsBtn = document.getElementById("admin-finance-payments-btn");
  const paymentsResult = document.getElementById("admin-finance-payments-result");
  const controlsEl = document.getElementById("admin-finance-revenue-controls");
  const unavailableEl = document.getElementById("admin-finance-revenue-unavailable");

  // Audit admin (2026-10-22) : non_configure/etat_inconnu traités désormais
  // comme reconciliation_blocked — désactivation DÈS LE CHARGEMENT, avant
  // tout clic (jamais après une tentative échouée). Dès que Stripe redevient
  // accessible (mode test/production confirmée), ces mêmes blocs
  // réapparaissent naturellement : aucune nouvelle logique, uniquement cette
  // condition en plus de reconciliation_blocked (point 5 du chantier).
  const unavailable = isFinanceUnavailable(env);

  if (unavailableEl) {
    unavailableEl.innerHTML = "";
    unavailableEl.hidden = !unavailable;
    if (unavailable) {
      unavailableEl.appendChild(el("p", "admin-form-error", unavailableMessage(env)));
    }
  }
  // Remplace toute la zone Revenus (hint + période + bouton + résultat +
  // graphique) par le bloc compact ci-dessus — jamais les deux affichés en
  // même temps, et plus aucune réservation de 240px tant qu'aucune donnée
  // n'est disponible (le graphique est à l'intérieur de ce bloc masqué).
  if (controlsEl) controlsEl.hidden = unavailable;
  if (periodSelect) periodSelect.disabled = !!unavailable;
  if (periodLabel) periodLabel.hidden = !!unavailable;

  [revenueBtn, paymentsBtn].forEach((btn) => {
    if (!btn) return;
    btn.disabled = !!unavailable;
    if (unavailable) btn.textContent = "Lecture bloquée (voir Source des données ci-dessus)";
  });
  if (unavailable) return;

  if (revenueBtn) {
    revenueBtn.onclick = async () => {
      revenueBtn.disabled = true;
      const original = revenueBtn.textContent;
      revenueBtn.textContent = "Chargement…";
      revenueResult.innerHTML = "";
      revenueChartBox.innerHTML = "";
      const days = periodSelect ? periodSelect.value : "30";
      try {
        await withStripeConfirmation(env, `/api/admin/finance/revenue?days=${days}`, revenueResult, (payload) => {
          renderRevenueReport(revenueResult, payload);
        });
        await withStripeConfirmation(
          env,
          `/api/admin/finance/revenue/series?months=${Math.max(1, Math.round(days / 30))}`,
          revenueChartBox,
          (payload) => renderRevenueSeries(revenueChartBox, payload),
        );
      } finally {
        revenueBtn.disabled = false;
        revenueBtn.textContent = original;
      }
    };
  }

  if (paymentsBtn) {
    paymentsBtn.onclick = async () => {
      paymentsBtn.disabled = true;
      const original = paymentsBtn.textContent;
      paymentsBtn.textContent = "Chargement…";
      paymentsResult.innerHTML = "";
      try {
        await withStripeConfirmation(env, "/api/admin/finance/payments?limit=20", paymentsResult, (payload) => {
          renderPaymentsReport(paymentsResult, payload);
        });
      } finally {
        paymentsBtn.disabled = false;
        paymentsBtn.textContent = original;
      }
    };
  }
}

// ── Point d'entrée ───────────────────────────────────────────────────────
export async function loadFinanceOverview() {
  const envEl = document.getElementById("admin-finance-stripe-environment");
  const subsEl = document.getElementById("admin-finance-subscriptions");
  const errorEl = document.getElementById("admin-global-error");
  const retryBtn = document.getElementById("admin-finance-retry-btn");

  if (subsEl) subsEl.innerHTML = "";
  errorEl.hidden = true;
  if (retryBtn) retryBtn.hidden = true;

  const { ok, payload } = await apiGet("/api/admin/finance/overview");
  if (!ok) {
    errorEl.hidden = false;
    errorEl.textContent = "Le module Finance n'a pas pu être chargé. Réessaie dans un instant.";
    if (retryBtn) {
      retryBtn.hidden = false;
      retryBtn.onclick = () => loadFinanceOverview();
    }
    return;
  }

  renderStripeEnvironment(envEl, payload.stripe_environment);
  renderSubscriptionsOverview(subsEl, payload.subscriptions);
  wireFinanceButtons(payload.stripe_environment);

  const lastRefreshEl = document.getElementById("admin-finance-last-refresh");
  if (lastRefreshEl) {
    lastRefreshEl.textContent = `Dernière actualisation : ${new Date().toLocaleString("fr-FR")}`;
  }
}
