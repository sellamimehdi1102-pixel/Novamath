// Module "Santé du système" (/admin/health) — centre de supervision. Toutes
// les données proviennent de system_health_service.py (voir
// GET /api/admin/system-health/{overview,incidents}) : chaque champ
// non calculable renvoie {available:false, reason:"..."}, jamais une valeur
// fabriquée — voir EMPTY_LABEL ci-dessous, même convention que
// admin-support.js/admin-ai.js.
//
// Structure de la page (simplifiée, ordre imposé) : Résumé → Services → IA →
// Base de données → Serveur → Alertes, chaque bloc étant une section
// repliable .admin-collapse (voir admin-collapse.js — composant transverse
// réutilisé ici, pas de nouveau composant). Le détail "Fournisseurs IA"/
// "Clés API" et les 6 graphiques IA ont été retirés de cette page : ils
// duplicaient intégralement /admin/ia (mêmes routes, même bouton "Tester la
// connexion") et /admin/analytics (mêmes séries journalières) — seul un lien
// "Voir les détails IA" subsiste ici. L'explorateur de logs (placeholder
// 100% codé en dur, aucun appel API) a également été retiré.
import { createCollapseSection, wireCollapsePersistence } from "./admin-collapse.js";

const EMPTY_LABEL = "Cette fonctionnalité n'est pas encore alimentée.";
const REFRESH_INTERVAL_MS = 30000;

const STATE_LABELS = {
  ok: "Opérationnel", degraded: "Dégradé", down: "Indisponible", non_teste: "Jamais testé",
};
const STATE_DOT_CLASS = {
  ok: "admin-status-dot--ok", degraded: "admin-status-dot--warning", down: "admin-status-dot--down",
  non_teste: "admin-status-dot--unknown",
};
const ALERT_LEVEL_CLASS = { critical: "admin-badge--error", warning: "admin-badge--neutral", info: "admin-badge--muted" };
const INCIDENT_LEVEL_CLASS = { error: "admin-badge--error", warning: "admin-badge--neutral" };

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

async function fetchJson(path) {
  const res = await fetch(path, { credentials: "same-origin" });
  if (!res.ok) return null;
  return res.json();
}

function formatDateTime(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString("fr-FR", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

function formatBytes(bytes) {
  if (bytes === null || bytes === undefined) return "—";
  if (bytes < 1024) return `${bytes} o`;
  if (bytes < 1024 ** 2) return `${(bytes / 1024).toFixed(1)} Ko`;
  if (bytes < 1024 ** 3) return `${(bytes / 1024 ** 2).toFixed(1)} Mo`;
  return `${(bytes / 1024 ** 3).toFixed(2)} Go`;
}

function formatMs(ms) {
  if (ms === null || ms === undefined) return "—";
  return ms < 1000 ? `${Math.round(ms)} ms` : `${(ms / 1000).toFixed(2)} s`;
}

function metricCard(label, metric, formatter = (v) => v, tooltip) {
  const card = el("article", "admin-card");
  const labelEl = el("div", "admin-card-label", label);
  if (tooltip) labelEl.title = tooltip;
  card.appendChild(labelEl);
  if (!metric || !metric.available) {
    card.appendChild(el("div", "admin-card-value admin-card-value--empty", EMPTY_LABEL));
    if (metric && metric.reason) card.appendChild(el("div", "admin-card-sub", metric.reason));
  } else {
    card.appendChild(el("div", "admin-card-value", String(formatter(metric.value))));
  }
  return card;
}

function simpleCard(label, value, sub, tooltip) {
  const card = el("article", "admin-card");
  const labelEl = el("div", "admin-card-label", label);
  if (tooltip) labelEl.title = tooltip;
  card.appendChild(labelEl);
  card.appendChild(el("div", "admin-card-value", String(value)));
  if (sub) card.appendChild(el("div", "admin-card-sub", sub));
  return card;
}

function statusDot(state) {
  const span = el("span", `admin-status-dot ${STATE_DOT_CLASS[state] || "admin-status-dot--unknown"}`);
  span.textContent = STATE_LABELS[state] || state || "Inconnu";
  return span;
}

// ── Résumé (fusion Vue d'ensemble + Disponibilité) ──────────────────────────
// "Services supervisés"/"Opérationnels" (contexte redondant avec le badge),
// "Disponibilité globale"/"Temps moyen de réponse" (moyennes mélangeant
// SQLite/Stripe/SMTP/IA, non actionnables) ont été retirés — chantier de
// simplification de la page Santé. degraded_count/down_count restent pour
// jauger la sévérité à côté du badge ; le détail précis vit dans Services.
function renderOverview(container, overview) {
  container.innerHTML = "";
  const statusLabel = { ok: "Opérationnel", degraded: "Dégradé", down: "Indisponible" }[overview.global_status] || overview.global_status;
  container.appendChild(simpleCard("Santé globale", statusLabel, null, "Statut agrégé de tous les services supervisés : Opérationnel si tous fonctionnent, Dégradé si au moins un est en échec sans que tout soit indisponible, Indisponible si un service critique est en panne."));
  container.appendChild(simpleCard("Dégradés", overview.degraded_count));
  container.appendChild(simpleCard("Indisponibles", overview.down_count));
  container.appendChild(simpleCard("Dernière vérification", formatDateTime(overview.checked_at)));
}

function renderAvailability(container, availability) {
  container.innerHTML = "";
  container.appendChild(metricCard("24 heures", availability["24h"], (v) => `${v}%`));
  container.appendChild(metricCard("7 jours", availability["7j"], (v) => `${v}%`));
  container.appendChild(metricCard("30 jours", availability["30j"], (v) => `${v}%`));
}

// ── Services (SQLite/Stripe/SMTP/fournisseurs IA enregistrés) ───────────────
// Stripe et SMTP n'ont jamais de vrai health-check (juste une vérification de
// configuration, voir health_service.check_stripe_configured/
// check_smtp_configured) : un badge "configuré/non configuré" remplace donc
// ici les fausses cartes de latence/dernier succès/dernier échec toujours
// vides pour ces deux services uniquement.
const CONFIG_ONLY_SERVICE_IDS = new Set(["stripe", "smtp"]);

function renderServices(container, services) {
  container.innerHTML = "";
  services.forEach((s) => {
    const card = el("article", "admin-card");
    const head = el("div", "admin-provider-row");
    head.appendChild(el("span", "admin-provider-name", s.name));
    if (CONFIG_ONLY_SERVICE_IDS.has(s.id)) {
      const configured = s.state === "ok";
      head.appendChild(el("span", `admin-badge ${configured ? "admin-badge--ok" : "admin-badge--neutral"}`, configured ? "Configuré" : "Non configuré"));
      card.appendChild(head);
      container.appendChild(card);
      return;
    }
    head.appendChild(statusDot(s.state));
    card.appendChild(head);
    card.appendChild(metricCard("Latence", s.latency_ms, formatMs));
    card.appendChild(metricCard("Dernier succès", s.last_success, formatDateTime));
    card.appendChild(metricCard("Dernier échec", s.last_failure, formatDateTime));
    card.appendChild(metricCard("Version", s.version));
    container.appendChild(card);
  });
}

// ── IA (résumé + renvoi vers /admin/ia) ─────────────────────────────────────
// Le détail par fournisseur (santé, usage du jour, clés API) est un doublon
// intégral des mêmes routes que /admin/ia (admin_ai_service/
// ai_provider_service) et n'est plus rendu ici. `services` provient du même
// appel réseau déjà effectué pour la section Services (aucun appel dédié).
function renderAiSummary(container, services, navigateTo) {
  container.innerHTML = "";
  const aiServices = services.filter((s) => s.id && s.id.startsWith("ai_"));
  if (aiServices.length) {
    const down = aiServices.filter((s) => s.state === "down").length;
    const degraded = aiServices.filter((s) => s.state === "degraded").length;
    let state = "ok";
    if (down) state = "down";
    else if (degraded) state = "degraded";
    container.appendChild(statusDot(state));
    container.appendChild(el("span", "admin-card-sub", `${aiServices.length - down} / ${aiServices.length} opérationnel(s)`));
  } else {
    container.appendChild(el("p", "admin-empty", "Aucun fournisseur IA enregistré."));
  }
  const btn = el("button", "admin-btn admin-btn--sm", "Voir les détails IA →");
  btn.type = "button";
  btn.addEventListener("click", () => navigateTo("/admin/ia", { pushState: true }));
  container.appendChild(btn);
}

// ── Base de données (fusion Base SQLite + volet DB/disque de Stockage) ──────
// "Nombre de tables"/"Nombre de lignes"/"Version SQLite" (aucune décision
// admin n'en dépend) et "Taille du fichier" (doublon exact de "Taille en
// base", même DB_PATH.stat().st_size) ont été retirés — chantier de
// simplification de la page Santé. Seule "Intégrité" reste (corruption =
// action : restaurer une sauvegarde).
function renderDatabase(container, database, storage) {
  container.innerHTML = "";
  container.appendChild(simpleCard("État", database.state.available ? database.state.value : "—"));
  if (database.introspection.available) {
    container.appendChild(simpleCard("Intégrité", database.introspection.value.integrity));
  } else {
    container.appendChild(metricCard("Introspection SQLite", database.introspection));
  }
  container.appendChild(metricCard("Dernière sauvegarde", database.last_backup, (b) => `${b.filename} — ${formatDateTime(b.created_at)}`));
  container.appendChild(metricCard("Taille en base", storage.database_bytes, formatBytes));
  container.appendChild(metricCard("Espace disque libre", storage.disk_free_bytes, formatBytes));
  container.appendChild(metricCard("Espace disque utilisé", storage.disk_used_bytes, formatBytes));
}

// ── Serveur (fusion Serveur + volet uploads de Stockage) ────────────────────
function formatUptime(seconds) {
  const s = Math.round(seconds);
  const days = Math.floor(s / 86400);
  const hours = Math.floor((s % 86400) / 3600);
  const minutes = Math.floor((s % 3600) / 60);
  if (days > 0) return `${days} j ${hours} h`;
  if (hours > 0) return `${hours} h ${minutes} min`;
  return `${minutes} min`;
}

// "Mémoire disponible" (redondant avec RAM%), "Charge (load average)"
// (n'existe pas sous Windows, toujours indisponible sur ce déploiement) et
// "Nombre de processus" (process OS entier, non spécifique à NovaMath, non
// actionnable) ont été retirés — chantier de simplification de la page Santé.
function renderServer(container, server, storage) {
  container.innerHTML = "";
  container.appendChild(metricCard("CPU", server.cpu_percent, (v) => `${v}%`));
  container.appendChild(metricCard("RAM", server.ram_percent, (v) => `${v}%`));
  container.appendChild(simpleCard("Uptime", formatUptime(server.uptime_seconds), `Démarré le ${formatDateTime(server.process_started_at)}`));
  container.appendChild(metricCard("Temps moyen API", server.avg_api_response_time_ms, formatMs));
  container.appendChild(metricCard("Uploads (pièces jointes)", storage.uploads_bytes, formatBytes));
}

// ── Alertes ──────────────────────────────────────────────────────────────────
function renderAlerts(container, emptyEl, alerts) {
  container.innerHTML = "";
  emptyEl.hidden = alerts.length > 0;
  alerts.forEach((a) => {
    const li = el("li", "admin-unavailable-item");
    li.appendChild(el("span", `admin-badge ${ALERT_LEVEL_CLASS[a.level] || "admin-badge--neutral"}`, a.level));
    li.appendChild(document.createTextNode(` ${a.message}`));
    container.appendChild(li);
  });
}

// ── Historique des incidents (sous-bloc de Services) ────────────────────────
function renderIncidents(container, emptyEl, items) {
  container.innerHTML = "";
  emptyEl.hidden = items.length > 0;
  items.forEach((ev) => {
    const li = el("li", "admin-unavailable-item");
    li.appendChild(el("span", `admin-badge ${INCIDENT_LEVEL_CLASS[ev.level] || "admin-badge--neutral"}`, ev.level));
    li.appendChild(document.createTextNode(` ${formatDateTime(ev.created_at)} — ${ev.service} — ${ev.message} `));
    li.appendChild(el("em", null, ev.resolution + (ev.duration_ms !== null && ev.duration_ms !== undefined ? ` (${formatMs(ev.duration_ms)})` : "")));
    container.appendChild(li);
  });
}

// ── Structure des 6 sections repliables (ordre imposé) ──────────────────────
const SECTIONS = [
  {
    id: "health-summary", title: "Résumé", open: true,
    bodyHtml: `
      <div class="admin-cards" id="admin-health-overview"></div>
      <h3 class="admin-analytics-subtitle">Disponibilité</h3>
      <div class="admin-cards" id="admin-health-availability"></div>
    `,
  },
  {
    id: "health-services", title: "Services", open: false,
    bodyHtml: `
      <div class="admin-ai-health-list" id="admin-health-services"></div>
      <div class="admin-section-head-row">
        <h3 class="admin-analytics-subtitle" style="margin:0">Historique des incidents</h3>
        <select class="admin-form-select" id="admin-health-incidents-window" aria-label="Fenêtre de temps">
          <option value="24h">24 heures</option>
          <option value="7j" selected>7 jours</option>
          <option value="30j">30 jours</option>
          <option value="tous">Tout</option>
        </select>
      </div>
      <ul class="admin-unavailable-list" id="admin-health-incidents"></ul>
      <p class="admin-empty" id="admin-health-incidents-empty" hidden>Aucun incident sur cette période.</p>
    `,
  },
  {
    id: "health-ai", title: "IA", open: false,
    bodyHtml: `<div class="admin-provider-row" id="admin-health-ai-summary"></div>`,
  },
  {
    id: "health-database", title: "Base de données", open: false,
    bodyHtml: `<div class="admin-cards" id="admin-health-database"></div>`,
  },
  {
    id: "health-server", title: "Serveur", open: false,
    bodyHtml: `<div class="admin-cards" id="admin-health-server"></div>`,
  },
  {
    id: "health-alerts", title: "Alertes", open: false,
    bodyHtml: `
      <ul class="admin-unavailable-list" id="admin-health-alerts"></ul>
      <p class="admin-empty" id="admin-health-alerts-empty" hidden>Aucune alerte active.</p>
    `,
  },
];

// ── Chargement complet + actualisation automatique ───────────────────────────
export async function loadHealth(navigateTo) {
  const sectionsEl = document.getElementById("admin-health-sections");
  sectionsEl.innerHTML = SECTIONS.map(createCollapseSection).join("");
  wireCollapsePersistence(sectionsEl);

  const overviewEl = document.getElementById("admin-health-overview");
  const availabilityEl = document.getElementById("admin-health-availability");
  const servicesEl = document.getElementById("admin-health-services");
  const incidentsEl = document.getElementById("admin-health-incidents");
  const incidentsEmptyEl = document.getElementById("admin-health-incidents-empty");
  const incidentsWindowSelect = document.getElementById("admin-health-incidents-window");
  const aiSummaryEl = document.getElementById("admin-health-ai-summary");
  const databaseEl = document.getElementById("admin-health-database");
  const serverEl = document.getElementById("admin-health-server");
  const alertsEl = document.getElementById("admin-health-alerts");
  const alertsEmptyEl = document.getElementById("admin-health-alerts-empty");
  const refreshBtn = document.getElementById("admin-health-refresh-btn");
  const errorEl = document.getElementById("admin-global-error");

  async function refreshOverview() {
    const data = await fetchJson("/api/admin/system-health/overview");
    if (!data) {
      if (errorEl) { errorEl.hidden = false; errorEl.textContent = "Impossible de charger la santé du système."; }
      return;
    }
    if (errorEl) errorEl.hidden = true;
    renderOverview(overviewEl, data.overview);
    renderAvailability(availabilityEl, data.availability);
    renderServices(servicesEl, data.services);
    renderAiSummary(aiSummaryEl, data.services, navigateTo);
    renderDatabase(databaseEl, data.database, data.storage);
    renderServer(serverEl, data.server, data.storage);
    renderAlerts(alertsEl, alertsEmptyEl, data.alerts);
  }

  async function refreshIncidents() {
    const data = await fetchJson(`/api/admin/system-health/incidents?window=${incidentsWindowSelect.value}`);
    if (data) renderIncidents(incidentsEl, incidentsEmptyEl, data.items);
  }

  async function refreshAll() {
    await Promise.all([refreshOverview(), refreshIncidents()]);
  }
  loadHealth.refresh = refreshAll;

  incidentsWindowSelect.addEventListener("change", refreshIncidents);
  refreshBtn.addEventListener("click", refreshAll);

  await refreshAll();

  const intervalId = setInterval(refreshOverview, REFRESH_INTERVAL_MS);
  const contentBody = document.getElementById("admin-content-body");
  const observer = new MutationObserver(() => {
    if (!document.body.contains(sectionsEl)) {
      clearInterval(intervalId);
      observer.disconnect();
    }
  });
  if (contentBody) observer.observe(contentBody, { childList: true });
}
