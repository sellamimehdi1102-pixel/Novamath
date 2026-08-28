// Rendu du Dashboard Administrateur (/admin) — lecture seule, aucune action
// destructive, aucune donnée inventée côté client : ce module se contente
// d'afficher ce que /api/admin/dashboard renvoie (voir
// webapp/admin_dashboard_service.py). Un backend qui renvoie available=false
// est TOUJOURS rendu comme "Aucune donnée disponible", jamais comme 0/vide
// silencieux — ce module ne doit jamais fabriquer une valeur par défaut.
//
// Refonte UX (audit round 2) : 4 cartes, chacune réellement décisionnelle
// (Santé, Support, IA, Utilisateurs actifs) + une liste d'alertes métier
// déplacée depuis /admin/analytics (seul endroit où elle existe désormais).
// Sorties : total d'utilisateurs (vanity), nouveaux inscrits 24h (déjà
// couvert par l'alerte "forte création de comptes"), répartition par plan
// (déjà sur /admin/subscriptions) et le flux d'activité brute (aucune
// décision). Le détail complet de chaque domaine reste exclusivement dans sa
// page dédiée (IA, Santé, Support, Analytics).
const EMPTY_LABEL = "Aucune donnée disponible";

function formatInt(value) {
  return new Intl.NumberFormat("fr-FR").format(value);
}

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function cardShell(label, tooltip) {
  const card = el("article", "admin-card");
  const labelEl = el("div", "admin-card-label", label);
  if (tooltip) labelEl.title = tooltip;
  card.appendChild(labelEl);
  return card;
}

function emptyCardBody(card, metric) {
  card.appendChild(el("div", "admin-card-value admin-card-value--empty", EMPTY_LABEL));
  if (metric.reason) card.appendChild(el("div", "admin-card-sub", metric.reason));
}

// Carte "Utilisateurs actifs" — seul indicateur de croissance conservé sur
// le Dashboard : répond à "le produit est-il utilisé aujourd'hui ?". Delta
// simple vs hier (jamais un pourcentage — voir admin_dashboard_service.py::
// _card_active_users_today), toujours affichable même si hier=0.
function formatDelta(delta) {
  if (delta > 0) return `+${formatInt(delta)} vs hier`;
  if (delta < 0) return `−${formatInt(Math.abs(delta))} vs hier`;
  return "0 vs hier";
}

function activeUsersCard(cards) {
  const card = cardShell("Utilisateurs actifs", "Comptes ayant eu une activité depuis minuit (heure serveur), comparés à la même fenêtre hier.");
  const metric = cards.active_users_today;
  if (!metric || !metric.available) {
    emptyCardBody(card, metric || {});
    return card;
  }
  card.appendChild(el("div", "admin-card-value", formatInt(metric.value.today)));
  card.appendChild(el("div", "admin-card-sub", formatDelta(metric.value.delta)));
  return card;
}

// Carte "IA" — un seul badge agrégé (jamais le détail par fournisseur, qui
// vit uniquement dans /admin/ia) + lien "Voir les détails".
function aiBadge(metric) {
  if (!metric || !metric.available) return { cls: "unknown", label: EMPTY_LABEL };
  const providers = metric.value;
  if (!providers.length) return { cls: "unknown", label: EMPTY_LABEL };
  const enabled = providers.filter((p) => p.enabled);
  if (!enabled.length) return { cls: "disabled", label: "Aucun fournisseur actif" };
  const down = enabled.filter((p) => p.last_failure && (!p.last_success || p.last_failure > p.last_success));
  if (down.length) return { cls: "down", label: `${down.length}/${enabled.length} en échec` };
  return { cls: "ok", label: `${enabled.length}/${enabled.length} opérationnels` };
}

// Carte "Santé système" — statut agrégé réel (system_health_service.overview,
// même source que la page Santé), plus une carte de navigation vide.
function healthBadge(metric) {
  if (!metric || !metric.available) return { cls: "unknown", label: EMPTY_LABEL };
  const h = metric.value;
  if (h.total_services === 0) return { cls: "unknown", label: "Aucun service supervisé" };
  if (h.global_status === "down") return { cls: "down", label: `${h.down_count} service(s) en panne` };
  if (h.global_status === "degraded") return { cls: "warning", label: `${h.degraded_count} service(s) dégradé(s)` };
  return { cls: "ok", label: `${h.ok_count}/${h.total_services} opérationnels` };
}

// Carte "Support" — nombre réel de tickets ouverts (support_service.overview_stats,
// même source que la page Analytics), plus une carte de navigation vide.
function supportBadge(metric) {
  if (!metric || !metric.available) return { cls: "unknown", label: EMPTY_LABEL };
  const s = metric.value;
  if (!s.open_count) return { cls: "ok", label: "Aucun ticket ouvert" };
  return { cls: s.open_count > 5 ? "down" : "warning", label: `${formatInt(s.open_count)} ticket(s) ouvert(s)` };
}

// Indicateur secondaire de la carte "Santé système" — PAS une nouvelle
// carte, juste un badge discret (étiquette + valeur) sous le statut
// principal. metrics_service.in_memory_snapshot() est process-local (remis
// à zéro à chaque redémarrage) : jamais présenté comme une fenêtre glissante
// de 24h (aucune donnée réelle ne le permettrait), libellé honnête "depuis
// le dernier redémarrage" conservé tel quel (Chantier Administrateur,
// Phase 2 — avant : une phrase libre en sous-texte mélangeant deux
// dimensions, voir admin-dashboard.test.js pour la non-régression).
function serverErrorsIndicator(metric) {
  if (!metric || !metric.available) return null;
  const { total_errors, total_requests } = metric.value;
  if (!total_requests) {
    return { value: "Aucune requête enregistrée depuis le dernier redémarrage.", warn: false };
  }
  return total_errors
    ? { value: `${formatInt(total_errors)} depuis le dernier redémarrage (${formatInt(total_requests)} requêtes)`, warn: true }
    : { value: `Aucune depuis le dernier redémarrage (${formatInt(total_requests)} requêtes)`, warn: false };
}

function badgeCard(label, badge, navigateTo, path, tooltip, indicator) {
  const card = cardShell(label, tooltip);
  card.appendChild(el("span", `admin-status-dot admin-status-dot--${badge.cls}`, badge.label));
  if (indicator) {
    const row = el("div", "admin-card-sub admin-provider-row");
    row.appendChild(el("span", null, "Erreurs serveur"));
    row.appendChild(el("span", `admin-badge ${indicator.warn ? "admin-badge--error" : "admin-badge--muted"}`, indicator.value));
    card.appendChild(row);
  }
  const link = el("button", "admin-card-link-btn", "Voir les détails →");
  link.type = "button";
  link.addEventListener("click", () => navigateTo(path, { pushState: true }));
  card.appendChild(link);
  return card;
}

// ── Alertes (déplacées depuis /admin/analytics — audit round 2) ───────────
const ALERT_LEVEL_CLASS = { critical: "admin-badge--error", warning: "admin-badge--neutral", info: "admin-badge--muted" };

// `a.link` optionnel ({path, label}) — seules les 2 alertes ponctuelles du
// Dashboard (paiements en échec / consentements parentaux en attente) en
// portent un aujourd'hui (Chantier Administrateur, Phase 2) ; les 5 alertes
// de tendance existantes (admin_analytics_service.list_alerts) n'en ont
// jamais eu et continuent de s'afficher sans bouton, comportement inchangé.
function renderAlerts(container, alerts, navigateTo) {
  container.replaceChildren();
  if (!alerts.available) {
    container.appendChild(el("p", "admin-empty", alerts.reason || EMPTY_LABEL));
    return;
  }
  if (!alerts.value.length) {
    container.appendChild(el("p", "admin-empty", "Aucune alerte aujourd'hui."));
    return;
  }
  const list = el("ul", "admin-activity-list");
  alerts.value.forEach((a) => {
    const row = el("li", "admin-activity-row");
    row.appendChild(el("span", `admin-badge ${ALERT_LEVEL_CLASS[a.level] || "admin-badge--neutral"}`, a.level));
    row.appendChild(el("span", "admin-activity-meta", a.message));
    if (a.link) {
      const link = el("button", "admin-card-link-btn", `${a.link.label} →`);
      link.type = "button";
      link.addEventListener("click", () => navigateTo(a.link.path, { pushState: true }));
      row.appendChild(link);
    }
    list.appendChild(row);
  });
  container.appendChild(list);
}

// ── Skeletons (état de chargement) ──────────────────────────────────────
const CARD_LABELS_FOR_SKELETON = ["Santé système", "Support", "IA", "Utilisateurs actifs"];

function renderSkeletons(cardsContainer) {
  cardsContainer.replaceChildren();
  CARD_LABELS_FOR_SKELETON.forEach((label) => {
    const card = cardShell(label);
    card.appendChild(el("div", "admin-card-value admin-skeleton", " "));
    cardsContainer.appendChild(card);
  });
}

// ── Point d'entrée ───────────────────────────────────────────────────────
export async function loadDashboard(navigateTo) {
  const cardsEl = document.getElementById("admin-cards");
  const activityEl = document.getElementById("admin-activity-body");
  const errorEl = document.getElementById("admin-global-error");

  renderSkeletons(cardsEl);

  let snapshot;
  try {
    const res = await fetch("/api/admin/dashboard", { credentials: "same-origin" });
    const payload = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(payload.error || `Erreur API (${res.status})`);
    snapshot = payload;
  } catch {
    errorEl.textContent = "Impossible de charger le dashboard administrateur. Réessaie dans un instant.";
    errorEl.hidden = false;
    cardsEl.replaceChildren();
    renderAlerts(activityEl, { available: false, reason: EMPTY_LABEL }, navigateTo);
    return;
  }

  errorEl.hidden = true;
  const cards = snapshot.cards || {};
  cardsEl.replaceChildren();
  cardsEl.appendChild(badgeCard("Santé système", healthBadge(cards.health_status), navigateTo, "/admin/health", "Statut agrégé des services, de la base de données et du serveur.", serverErrorsIndicator(cards.server_errors)));
  cardsEl.appendChild(badgeCard("Support", supportBadge(cards.support_status), navigateTo, "/admin/support", "Nombre de tickets actuellement ouverts."));
  cardsEl.appendChild(badgeCard("IA", aiBadge(cards.ai_providers_status), navigateTo, "/admin/ia", "État agrégé des fournisseurs IA actifs (opérationnel / en échec)."));
  cardsEl.appendChild(activeUsersCard(cards));

  renderAlerts(activityEl, snapshot.alerts || { available: false }, navigateTo);
}
