// Module "Analytics" (/admin/analytics) — pur outil de TENDANCES/
// COMPARAISONS : graphiques d'évolution temporelle (Chart.js), classements
// ("Top X") et recherche globale, tous filtrables par période. Les cartes
// KPI de comptage brut (utilisateurs/chatbot/IA/abonnements/support), le
// camembert "Répartition des abonnements" et le bloc "Pédagogie" (jamais
// alimenté) ont été retirés (chantier de simplification du panneau admin) :
// ces chiffres vivent déjà sur le Dashboard ou dans les pages dédiées
// IA/Santé/Support — /api/admin/analytics/overview reste interrogé
// uniquement pour le tableau de bord personnalisé ("cartes KPI épinglées")
// et l'étiquette de période. L'ancien groupe "Système" (doublon exact du
// taux de succès IA + erreurs/fallbacks IA mal étiquetés) a été fusionné
// dans le groupe "ai" — plus de section "Système" séparée. La planification
// automatique de rapports a été supprimée (aucun scheduler ne l'exécutait
// jamais) ; la génération manuelle de rapport reste. Toutes les données
// viennent de admin_analytics_service.py (voir GET /api/admin/analytics/
// {overview,filters,charts,rankings,search}) : {available:false,
// reason:"..."} = jamais fabriqué, même convention que admin-health.js/
// admin-settings.js. Le rendu Chart.js reprend le même pattern que
// admin-health.js (CHART_SPECS déclaratif + destroyCharts()), jamais
// réinventé.
//
// ── Chantier de densité visuelle (2026-10-22) ────────────────────────────
// Graphiques "Utilisateurs" (quotidien/mensuel/annuel — même métrique
// d'inscriptions) fusionnés en UN SEUL graphique + un sélecteur de
// granularité (voir renderUsersChart) — toutes les données restent
// accessibles. Graphiques "IA" (7 → 4, voir renderAiCharts) :
// calls_per_day/fallbacks_per_day/errors_per_day (tous dérivés de
// ai_provider_usage) fusionnés en un seul "Appels & incidents IA"
// multi-séries ; latence/succès fusionnés en un graphique à 2 axes
// (unités différentes, jamais mélangées sur le même axe). "Top
// fournisseurs"/"Top coûts" (mêmes lignes provider_rows, juste un tri
// différent) fusionnés en un seul tableau (voir renderProviderTable).
// "Tickets par statut" (camembert à 2-3 valeurs) remplacé par une
// statistique compacte (voir renderStatusCompact) — plus de 240px
// réservés pour 2-3 chiffres. Export + Rapports fusionnés en une seule UI
// (voir le handler du formulaire exportForm plus bas) ; "Imprimer" retiré
// (doublon de l'export PDF serveur, qui fait mieux).
import { Chart } from "chart.js/auto";
import { debounce } from "./searchUtils.js";

const EMPTY_LABEL = "Cette fonctionnalité n'est pas encore alimentée.";
const REFRESH_INTERVAL_MS = 30000;
const SEARCH_DEBOUNCE_MS = 300;

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

async function fetchJson(path) {
  const res = await fetch(path, { credentials: "same-origin" });
  if (!res.ok) return { ok: false, status: res.status, payload: await res.json().catch(() => ({})) };
  return { ok: true, payload: await res.json() };
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

function formatDuration(seconds) {
  if (seconds === null || seconds === undefined) return "—";
  const s = Math.round(seconds);
  if (s < 60) return `${s} s`;
  const minutes = Math.floor(s / 60);
  if (minutes < 60) return `${minutes} min`;
  return `${Math.floor(minutes / 60)} h ${minutes % 60} min`;
}

// État des cartes KPI épinglées ("KPI épinglés" — renommé depuis "Mon
// tableau de bord" au Chantier Administrateur Phase 2, pour ne plus créer
// d'ambiguïté avec le vrai Dashboard de /admin) — peuplé au
// chargement, lu par metricCard() pour afficher l'étoile dans le bon état,
// jamais une seconde source de vérité côté client (toujours re-synchronisé
// depuis /api/admin/analytics/pinned-kpis).
let _pinnedKpis = new Set();
let _onPinToggle = null;

function metricCard(label, metric, formatter = (v) => v, kpiKey = null, tooltip = null) {
  const card = el("article", "admin-card");
  if (kpiKey) card.classList.add("admin-analytics-card--pinnable");
  const head = el("div", "admin-card-label-row");
  const labelEl = el("div", "admin-card-label", label);
  if (tooltip) labelEl.title = tooltip;
  head.appendChild(labelEl);
  if (kpiKey && _onPinToggle) {
    const pinned = _pinnedKpis.has(kpiKey);
    const pinBtn = el(
      "button",
      `admin-analytics-pin-btn${pinned ? " admin-analytics-pin-btn--active" : ""}`,
      pinned ? "★" : "☆",
    );
    pinBtn.type = "button";
    pinBtn.title = pinned ? "Retirer du tableau de bord" : "Épingler au tableau de bord";
    pinBtn.addEventListener("click", () => _onPinToggle(kpiKey, !pinned));
    head.appendChild(pinBtn);
  }
  card.appendChild(head);
  if (!metric || !metric.available) {
    card.appendChild(el("div", "admin-card-value admin-card-value--empty", EMPTY_LABEL));
    if (metric && metric.reason) card.appendChild(el("div", "admin-card-sub", metric.reason));
  } else {
    card.appendChild(el("div", "admin-card-value", String(formatter(metric.value))));
    if (metric.note) card.appendChild(el("div", "admin-card-sub", metric.note));
  }
  return card;
}

// ── Tableau de bord personnalisé (cartes épinglées) ──────────────────────────
const KPI_LOOKUP = {
  "users.total_registered": ["Utilisateurs inscrits", (u) => u.users.total_registered],
  "users.guest_accounts": ["Comptes invités", (u) => u.users.guest_accounts],
  "users.new_users": ["Nouveaux utilisateurs", (u) => u.users.new_users],
  "users.active_users": ["Utilisateurs actifs", (u) => u.users.active_users],
  "users.logins": ["Connexions", (u) => u.users.logins],
  "chatbot.conversations": ["Conversations", (u) => u.chatbot.conversations],
  "chatbot.user_messages": ["Messages utilisateur", (u) => u.chatbot.user_messages],
  "chatbot.assistant_messages": ["Réponses assistant", (u) => u.chatbot.assistant_messages],
  "ai.calls": ["Appels IA", (u) => u.ai.calls],
  "ai.tokens": ["Tokens", (u) => u.ai.tokens],
  "ai.cost_usd": [
    "Coût estimé ($)",
    (u) => u.ai.cost_usd,
    "Estimation calculée à partir d'une grille tarifaire figée côté serveur (Gemini/Claude), jamais une facture réelle du fournisseur.",
  ],
  "ai.avg_latency_ms": [
    "Latence moyenne",
    (u) => u.ai.avg_latency_ms,
    "Temps de réponse moyen des fournisseurs IA sur la période, en millisecondes.",
  ],
  "ai.success_rate_pct": [
    "Taux de succès",
    (u) => u.ai.success_rate_pct,
    "Proportion d'appels IA ayant abouti sans erreur ni bascule de secours.",
  ],
  "ai.errors": ["Erreurs IA", (u) => u.ai.errors],
  "ai.fallbacks": [
    "Fallbacks IA",
    (u) => u.ai.fallbacks,
    "Nombre de bascules automatiques vers un fournisseur IA de secours suite à un échec du fournisseur principal.",
  ],
  "support.tickets_created": ["Tickets créés", (u) => u.support.tickets_created],
  "support.open": ["Tickets ouverts", (u) => u.support.open],
  "support.closed": ["Tickets fermés", (u) => u.support.closed],
  "subscriptions.free": ["Free", (u) => u.subscriptions.free],
  "subscriptions.premium": ["Premium", (u) => u.subscriptions.premium],
  "subscriptions.ultra": ["Ultra", (u) => u.subscriptions.ultra],
};

function renderPinned(container, section, overview) {
  container.innerHTML = "";
  const keys = [..._pinnedKpis];
  section.hidden = keys.length === 0;
  keys.forEach((key) => {
    const entry = KPI_LOOKUP[key];
    if (!entry) return;
    const [label, getter, tooltip] = entry;
    container.appendChild(metricCard(label, getter(overview), undefined, key, tooltip));
  });
}

// ── Graphiques (Chart.js) — même pattern que admin-health.js ────────────────
let _chartInstances = [];

function destroyCharts() {
  _chartInstances.forEach((c) => c.destroy());
  _chartInstances = [];
  if (_usersChartInstance) {
    _usersChartInstance.destroy();
    _usersChartInstance = null;
  }
}

function renderChart(box, spec, series) {
  box.appendChild(el("h3", "admin-health-chart-title", spec.label));
  if (!series || !series.available) {
    box.appendChild(el("p", "admin-empty", (series && series.reason) || EMPTY_LABEL));
    return;
  }
  const canvas = document.createElement("canvas");
  box.appendChild(canvas);
  const chart = new Chart(canvas, {
    type: spec.type,
    data: {
      labels: series.value.map((p) => p.date),
      datasets: [
        {
          label: spec.label,
          data: series.value.map((p) => p.value),
          borderColor: spec.color,
          backgroundColor: spec.type === "bar" ? spec.color : `${spec.color}33`,
          fill: spec.type === "line" || spec.type === "area",
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
      plugins: { legend: { display: false } },
    },
  });
  _chartInstances.push(chart);
}

function renderMultiSeriesChart(box, label, type, seriesByName, colors) {
  box.appendChild(el("h3", "admin-health-chart-title", label));
  const names = Object.keys(seriesByName).filter((name) => seriesByName[name] && seriesByName[name].available);
  if (!names.length) {
    box.appendChild(el("p", "admin-empty", EMPTY_LABEL));
    return;
  }
  const allDates = new Set();
  names.forEach((name) => seriesByName[name].value.forEach((p) => allDates.add(p.date)));
  const labels = [...allDates].sort();
  const canvas = document.createElement("canvas");
  box.appendChild(canvas);
  const chart = new Chart(canvas, {
    type,
    data: {
      labels,
      datasets: names.map((name, i) => {
        const byDate = new Map(seriesByName[name].value.map((p) => [p.date, p.value]));
        return {
          label: name,
          data: labels.map((d) => (byDate.has(d) ? byDate.get(d) : null)),
          borderColor: colors[i % colors.length],
          backgroundColor: type === "bar" ? colors[i % colors.length] : `${colors[i % colors.length]}33`,
          fill: type === "line",
          tension: 0.25,
          borderWidth: 2,
          pointRadius: 2,
        };
      }),
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: { y: { beginAtZero: true } },
      plugins: { legend: { display: true, position: "bottom" } },
    },
  });
  _chartInstances.push(chart);
}

function renderPieChart(box, label, valueMap) {
  box.appendChild(el("h3", "admin-health-chart-title", label));
  const entries = Object.entries(valueMap || {});
  if (!entries.length) {
    box.appendChild(el("p", "admin-empty", EMPTY_LABEL));
    return;
  }
  const palette = ["#3B82F6", "#22C55E", "#D97757", "#7c5cff", "#dc8f2e", "#dd4b56"];
  const canvas = document.createElement("canvas");
  box.appendChild(canvas);
  const chart = new Chart(canvas, {
    type: "pie",
    data: {
      labels: entries.map(([k]) => k),
      datasets: [
        { data: entries.map(([, v]) => v), backgroundColor: entries.map((_, i) => palette[i % palette.length]) },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: true, position: "bottom" } },
    },
  });
  _chartInstances.push(chart);
}

function chartBox() {
  return el("div", "admin-health-chart-box");
}

// Les 3 graphiques "Croissance quotidienne/mensuelle/annuelle" (même
// métrique d'inscriptions — users.daily/monthly/yearly — seule la
// granularité change) ont été fusionnés en UN SEUL graphique + un
// sélecteur de granularité (Chantier Analytics, 2026-10-22) — toutes les
// données restent accessibles, juste via le sélecteur plutôt que 3 blocs
// simultanés. Instance Chart.js dédiée (jamais mêlée à _chartInstances/
// destroyCharts()) : changer la granularité ne doit PAS détruire/reconstruire
// les graphiques Chatbot/IA/Support affichés à côté.
const USERS_GRANULARITY_SPECS = {
  daily: { label: "Croissance quotidienne", type: "bar", color: "#3B82F6" },
  monthly: { label: "Croissance mensuelle", type: "bar", color: "#22C55E" },
  yearly: { label: "Croissance annuelle", type: "bar", color: "#D97757" },
};
let _usersChartInstance = null;

function renderUsersChart(container, users, granularity) {
  container.innerHTML = "";
  if (_usersChartInstance) {
    _usersChartInstance.destroy();
    _usersChartInstance = null;
  }
  const spec = USERS_GRANULARITY_SPECS[granularity] || USERS_GRANULARITY_SPECS.daily;
  const series = (users && users[granularity]) || null;
  const box = chartBox();
  box.appendChild(el("h3", "admin-health-chart-title", spec.label));
  if (!series || !series.available) {
    box.appendChild(el("p", "admin-empty", (series && series.reason) || EMPTY_LABEL));
    container.appendChild(box);
    return;
  }
  const canvas = document.createElement("canvas");
  box.appendChild(canvas);
  _usersChartInstance = new Chart(canvas, {
    type: spec.type,
    data: {
      labels: series.value.map((p) => p.date),
      datasets: [
        {
          label: spec.label,
          data: series.value.map((p) => p.value),
          borderColor: spec.color,
          backgroundColor: spec.color,
          borderWidth: 2,
          pointRadius: 2,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: { y: { beginAtZero: true } },
      plugins: { legend: { display: false } },
    },
  });
  container.appendChild(box);
}

function renderChatbotCharts(container, chatbot) {
  container.innerHTML = "";
  const conv = chartBox();
  renderChart(conv, { label: "Conversations par jour", type: "bar", color: "#3B82F6" }, chatbot.conversations_per_day);
  container.appendChild(conv);
  const msg = chartBox();
  renderMultiSeriesChart(
    msg,
    "Messages par jour",
    "line",
    { Utilisateur: chatbot.messages_per_day.user, Assistant: chatbot.messages_per_day.assistant },
    ["#3B82F6", "#22C55E"],
  );
  container.appendChild(msg);
  const aiVsLocal = chartBox();
  renderMultiSeriesChart(
    aiVsLocal,
    "Réponses IA vs réponses locales",
    "line",
    { "IA (réel)": chatbot.ai_vs_local_per_day.ai, "Locale (estimé)": chatbot.ai_vs_local_per_day.local },
    ["#7c5cff", "#dc8f2e"],
  );
  container.appendChild(aiVsLocal);
}

// Fusion des 7 graphiques IA en 4 (Chantier Analytics, 2026-10-22), analyses
// réellement distinctes conservées :
//   1. Consommation de tokens  2. Coût
//   3. Performance (latence + taux de succès, 2 axes — unités différentes)
//   4. "Appels & incidents IA" : calls_per_day/fallbacks_per_day/
//      errors_per_day, tous les 3 dérivés de la même table
//      ai_provider_usage — regroupés en UN graphique multi-séries plutôt
//      que 3 graphiques séparés (consigne explicite).
function renderDualAxisChart(box, label, seriesSpecs) {
  box.appendChild(el("h3", "admin-health-chart-title", label));
  const available = seriesSpecs.filter((s) => s.series && s.series.available);
  if (!available.length) {
    box.appendChild(el("p", "admin-empty", EMPTY_LABEL));
    return;
  }
  const allDates = new Set();
  available.forEach((s) => s.series.value.forEach((p) => allDates.add(p.date)));
  const labels = [...allDates].sort();
  const canvas = document.createElement("canvas");
  box.appendChild(canvas);
  const chart = new Chart(canvas, {
    type: "line",
    data: {
      labels,
      datasets: available.map((s) => {
        const byDate = new Map(s.series.value.map((p) => [p.date, p.value]));
        return {
          label: s.name,
          data: labels.map((d) => (byDate.has(d) ? byDate.get(d) : null)),
          borderColor: s.color,
          backgroundColor: `${s.color}33`,
          yAxisID: s.axis,
          tension: 0.25,
          borderWidth: 2,
          pointRadius: 2,
          fill: false,
        };
      }),
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: { type: "linear", position: "left", beginAtZero: true },
        y1: { type: "linear", position: "right", beginAtZero: true, grid: { drawOnChartArea: false } },
      },
      plugins: { legend: { display: true, position: "bottom" } },
    },
  });
  _chartInstances.push(chart);
}

function renderAiCharts(container, ai) {
  container.innerHTML = "";

  const tokens = chartBox();
  renderChart(tokens, { label: "Consommation de tokens", type: "line", color: "#22C55E" }, ai.tokens_per_day);
  container.appendChild(tokens);

  const cost = chartBox();
  renderChart(cost, { label: "Coût", type: "line", color: "#D97757" }, ai.cost_per_day);
  container.appendChild(cost);

  const performance = chartBox();
  renderDualAxisChart(performance, "Performance (latence & taux de succès)", [
    { name: "Latence moyenne (ms)", series: ai.avg_latency_per_day, color: "#7c5cff", axis: "y" },
    { name: "Taux de succès (%)", series: ai.success_rate_per_day, color: "#22C55E", axis: "y1" },
  ]);
  container.appendChild(performance);

  const incidents = chartBox();
  renderMultiSeriesChart(
    incidents,
    "Appels & incidents IA",
    "bar",
    { Appels: ai.calls_per_day, Fallbacks: ai.fallbacks_per_day, Erreurs: ai.errors_per_day },
    ["#3B82F6", "#dc8f2e", "#dd4b56"],
  );
  container.appendChild(incidents);
}

// "Tickets par statut" (2-3 valeurs seulement : open/in_progress/closed) est
// remplacé par une statistique compacte — un simple camembert pour 2-3
// valeurs n'apportait rien de plus qu'une ligne de chiffres, et réservait
// 240px (.admin-health-chart-box) pour ça (Chantier Analytics, 2026-10-22).
const SUPPORT_STATUS_LABELS = { open: "Ouverts", in_progress: "En cours", closed: "Fermés" };

function renderStatusCompact(container, byStatus) {
  const box = el("article", "admin-card admin-analytics-status-compact");
  box.appendChild(el("div", "admin-card-label", "Tickets par statut"));
  if (!byStatus || !byStatus.available) {
    box.appendChild(el("p", "admin-empty", (byStatus && byStatus.reason) || EMPTY_LABEL));
    container.appendChild(box);
    return;
  }
  const row = el("div", "admin-analytics-status-compact-row");
  Object.entries(byStatus.value).forEach(([key, count]) => {
    row.appendChild(
      el("span", "admin-analytics-status-compact-item", `${SUPPORT_STATUS_LABELS[key] || key} : ${count}`),
    );
  });
  box.appendChild(row);
  if (byStatus.note) box.appendChild(el("div", "admin-card-sub", byStatus.note));
  container.appendChild(box);
}

function renderSupportCharts(container, support) {
  container.innerHTML = "";
  const perDay = chartBox();
  renderChart(perDay, { label: "Tickets par jour", type: "bar", color: "#3B82F6" }, support.tickets_per_day);
  container.appendChild(perDay);
  const byCategory = chartBox();
  renderPieChart(byCategory, "Tickets par catégorie", support.by_category.available ? support.by_category.value : null);
  container.appendChild(byCategory);
  renderStatusCompact(container, support.by_status);
}

// ── Classements ("Top X") ─────────────────────────────────────────────────────
function rankingBox(title) {
  const box = el("div", "admin-analytics-ranking-box");
  box.appendChild(el("h4", "admin-analytics-ranking-title", title));
  return box;
}

async function toggleUserDetail(row, userId) {
  const existing = row.nextElementSibling;
  if (existing && existing.classList.contains("admin-analytics-ranking-detail")) {
    existing.remove();
    return;
  }
  const detail = el("div", "admin-analytics-ranking-detail", "Chargement…");
  row.after(detail);
  const { ok, payload } = await fetchJson(`/api/admin/users/${userId}/chatbot`);
  if (!ok) {
    detail.textContent = "Impossible de charger le détail.";
    return;
  }
  detail.innerHTML = "";
  const lines = [
    ["Conversations", payload.conversations_count],
    ["Messages", payload.messages_count],
    [
      "Tokens IA",
      payload.ai_tokens_total && payload.ai_tokens_total.available ? payload.ai_tokens_total.value : undefined,
    ],
    ["Coût IA estimé", payload.ai_cost && payload.ai_cost.available ? `${payload.ai_cost.value} $` : undefined],
    [
      "Progression (temps passé)",
      payload.time_spent_s && payload.time_spent_s.available ? formatDuration(payload.time_spent_s.value) : undefined,
    ],
  ];
  lines.forEach(([label, value]) => {
    if (value === undefined || value === null) return;
    detail.appendChild(el("div", null, `${label} : ${value}`));
  });
  if (!detail.childNodes.length) detail.textContent = EMPTY_LABEL;
}

function renderUserRankingBox(container, title, rows, valueKey, valueLabel) {
  const box = rankingBox(title);
  if (!rows || !rows.length) {
    box.appendChild(el("p", "admin-empty", EMPTY_LABEL));
    container.appendChild(box);
    return;
  }
  rows.forEach((row) => {
    const rowEl = el("div", "admin-analytics-ranking-row admin-analytics-ranking-row--clickable");
    rowEl.appendChild(el("span", "admin-analytics-ranking-name", row.pseudo));
    rowEl.appendChild(el("span", "admin-analytics-ranking-value", `${row[valueKey]} ${valueLabel}`));
    rowEl.addEventListener("click", () => toggleUserDetail(rowEl, row.user_id));
    box.appendChild(rowEl);
  });
  container.appendChild(box);
}

function renderSimpleRankingBox(container, title, rows, nameKey, valueKey, valueLabel, formatter = (v) => v) {
  const box = rankingBox(title);
  if (!rows || !rows.length) {
    box.appendChild(el("p", "admin-empty", EMPTY_LABEL));
    container.appendChild(box);
    return;
  }
  rows.forEach((row) => {
    const rowEl = el("div", "admin-analytics-ranking-row");
    rowEl.appendChild(el("span", "admin-analytics-ranking-name", String(row[nameKey])));
    rowEl.appendChild(el("span", "admin-analytics-ranking-value", `${formatter(row[valueKey])} ${valueLabel}`));
    box.appendChild(rowEl);
  });
  container.appendChild(box);
}

function renderChatbotRankings(container, rankings) {
  container.innerHTML = "";
  renderUserRankingBox(
    container,
    "Top utilisateurs du chatbot",
    rankings.users.top_chatbot_users.available ? rankings.users.top_chatbot_users.value : null,
    "message_count",
    "messages",
  );
  const note = el("p", "admin-form-hint", rankings.users.top_active_reason);
  container.appendChild(note);
}

// "Top fournisseurs" et "Top coûts" renvoyaient les MÊMES lignes
// (provider_rows), juste triées différemment (par tokens vs par coût) — un
// doublon confirmé par l'audit. Fusionnés en UN SEUL tableau (nom/tokens/
// coût sur la même ligne), trié par tokens comme l'ancien "Top fournisseurs"
// (Chantier Analytics, 2026-10-22) : `top_cost` reste calculé côté backend
// (jamais supprimé, pourrait servir ailleurs) mais n'est plus lu ici.
function renderProviderTable(container, title, rows) {
  const box = rankingBox(title);
  if (!rows || !rows.length) {
    box.appendChild(el("p", "admin-empty", EMPTY_LABEL));
    container.appendChild(box);
    return;
  }
  const table = el("table", "admin-users-table");
  const thead = document.createElement("thead");
  const headRow = document.createElement("tr");
  ["Fournisseur", "Tokens", "Coût estimé ($)"].forEach((h) => headRow.appendChild(el("th", null, h)));
  thead.appendChild(headRow);
  table.appendChild(thead);
  const tbody = document.createElement("tbody");
  rows.forEach((row) => {
    const tr = document.createElement("tr");
    tr.appendChild(el("td", null, row.provider_key));
    tr.appendChild(el("td", null, String(row.total_tokens)));
    tr.appendChild(el("td", null, Number(row.estimated_cost || 0).toFixed(4)));
    tbody.appendChild(tr);
  });
  table.appendChild(tbody);
  box.appendChild(table);
  container.appendChild(box);
}

function renderAiRankings(container, rankings) {
  container.innerHTML = "";
  renderUserRankingBox(
    container,
    "Top consommateurs IA",
    rankings.users.top_ai_consumers.available ? rankings.users.top_ai_consumers.value : null,
    "total_tokens",
    "tokens",
  );
  renderProviderTable(
    container,
    "Fournisseurs (tokens & coût)",
    rankings.ai.top_providers.available ? rankings.ai.top_providers.value : null,
  );
  renderSimpleRankingBox(
    container,
    "Top modèles",
    rankings.ai.top_models.available ? rankings.ai.top_models.value : null,
    "name",
    "total_tokens",
    "tokens",
  );
  renderSimpleRankingBox(
    container,
    "Top moteurs",
    rankings.ai.top_engines.available ? rankings.ai.top_engines.value : null,
    "engine",
    "requests",
    "appels",
  );
}

// "Top catégories"/"Top priorités" ont été retirés : ils répétaient les pie
// charts "Tickets par catégorie"/"Tickets par statut" déjà affichés juste
// au-dessus (renderSupportCharts) — seul "Top administrateurs" apporte une
// information réellement nouvelle (absente des graphiques).
// `avg_resolution_seconds` (temps moyen de résolution PAR administrateur)
// était calculé par db.support_tickets_by_assigned_admin_since mais jamais
// affiché (chantier de simplification du panneau admin) — repris ici en
// sous-ligne, seule façon de distinguer "beaucoup de tickets" de "tickets
// résolus vite".
function renderSupportRankings(container, rankings) {
  container.innerHTML = "";
  const box = rankingBox("Top administrateurs");
  const rows = rankings.support.top_admins.available ? rankings.support.top_admins.value : null;
  if (!rows || !rows.length) {
    box.appendChild(el("p", "admin-empty", EMPTY_LABEL));
    container.appendChild(box);
    return;
  }
  rows.forEach((row) => {
    const rowEl = el("div", "admin-analytics-ranking-row");
    rowEl.appendChild(el("span", "admin-analytics-ranking-name", row.admin_name));
    const valueWrap = el("span", "admin-analytics-ranking-value", `${row.ticket_count} tickets`);
    if (row.avg_resolution_seconds !== null && row.avg_resolution_seconds !== undefined) {
      valueWrap.appendChild(
        el("span", "admin-card-sub", ` · résolution moy. ${formatDuration(row.avg_resolution_seconds)}`),
      );
    }
    rowEl.appendChild(valueWrap);
    box.appendChild(rowEl);
  });
  container.appendChild(box);
}

// ── Recherche globale ─────────────────────────────────────────────────────────
function searchResultGroup(title, items, renderItem) {
  const group = el("div", "admin-analytics-search-result-group");
  group.appendChild(el("h3", null, title));
  if (!items.length) {
    group.appendChild(el("p", "admin-empty", "Aucun résultat."));
    return group;
  }
  items.forEach((item) => group.appendChild(renderItem(item)));
  return group;
}

function renderSearchResults(container, resultsSection, results) {
  container.innerHTML = "";
  resultsSection.hidden = false;
  container.appendChild(
    searchResultGroup("Utilisateurs", results.users, (u) => {
      const a = el("a", "admin-analytics-search-result-item", `${u.pseudo} — ${u.email}`);
      a.href = `/admin/users/${u.id}`;
      return a;
    }),
  );
  container.appendChild(
    searchResultGroup("Conversations", results.conversations, (c) => {
      const a = el(
        "a",
        "admin-analytics-search-result-item",
        `${c.title} — ${c.pseudo} (${formatDateTime(c.created_at)})`,
      );
      a.href = `/admin/users/${c.user_id}`;
      return a;
    }),
  );
  container.appendChild(
    searchResultGroup("Tickets", results.tickets, (t) => {
      const a = el("a", "admin-analytics-search-result-item", `#${t.id} — ${t.subject}`);
      a.href = `/admin/support/${t.id}`;
      return a;
    }),
  );
  container.appendChild(
    searchResultGroup("Fournisseurs / modèles IA", results.ai_providers, (p) => {
      const a = el("a", "admin-analytics-search-result-item", `${p.name} (${p.provider_key} — ${p.model_name})`);
      a.href = `/admin/ia/${p.id}`;
      return a;
    }),
  );
  container.appendChild(
    searchResultGroup("Messages", results.messages, (m) => {
      const a = el(
        "a",
        "admin-analytics-search-result-item",
        `${m.pseudo} — « ${m.excerpt} » (${formatDateTime(m.created_at)})`,
      );
      a.href = `/admin/users/${m.user_id}`;
      return a;
    }),
  );
  container.appendChild(
    searchResultGroup("Sauvegardes", results.backups, (b) => {
      const span = el("span", "admin-analytics-search-result-item", `${b.filename} (${formatDateTime(b.created_at)})`);
      return span;
    }),
  );
  container.appendChild(
    searchResultGroup("Événements de sécurité", results.security_events, (e) => {
      const span = el(
        "span",
        "admin-analytics-search-result-item",
        `${e.event_type} — ${e.ip || "IP inconnue"} (${formatDateTime(e.created_at)})`,
      );
      return span;
    }),
  );
}

// ── Rapports ──────────────────────────────────────────────────────────────────
function renderReports(tbody, emptyEl, items) {
  tbody.innerHTML = "";
  emptyEl.hidden = items.length > 0;
  items.forEach((entry) => {
    const meta = entry.new_values || {};
    const tr = document.createElement("tr");
    tr.appendChild(el("td", null, formatDateTime(entry.created_at)));
    tr.appendChild(el("td", null, entry.admin ? entry.admin.name : "—"));
    tr.appendChild(el("td", null, meta.report_type || entry.action_label));
    tr.appendChild(el("td", null, (meta.format || "").toUpperCase()));
    tr.appendChild(el("td", null, meta.size_bytes ? `${(meta.size_bytes / 1024).toFixed(1)} Ko` : "—"));
    tr.appendChild(el("td", null, meta.duration_ms ? `${meta.duration_ms} ms` : "—"));
    tr.appendChild(
      el("td", `admin-badge ${entry.result === "success" ? "admin-badge--ok" : "admin-badge--error"}`, entry.result),
    );
    const actionsTd = document.createElement("td");
    if (entry.action === "analytics_report" && meta.filename && entry.result === "success") {
      const link = document.createElement("a");
      link.href = `/api/admin/analytics/reports/${encodeURIComponent(meta.filename)}/download`;
      link.className = "admin-btn admin-btn--sm";
      link.textContent = "Télécharger";
      actionsTd.appendChild(link);
    }
    tr.appendChild(actionsTd);
    tbody.appendChild(tr);
  });
}

// ── Chargement complet ────────────────────────────────────────────────────────
export async function loadAnalytics() {
  const windowSelect = document.getElementById("admin-analytics-window-select");
  const dateFromInput = document.getElementById("admin-analytics-date-from");
  const dateToInput = document.getElementById("admin-analytics-date-to");
  const windowLabelEl = document.getElementById("admin-analytics-window-label");
  const errorEl = document.getElementById("admin-analytics-error");
  const searchInput = document.getElementById("admin-analytics-search-input");
  const searchResultsSection = document.getElementById("admin-analytics-search-results");
  const searchResultsBody = document.getElementById("admin-analytics-search-body");

  const savedViewsSelect = document.getElementById("admin-analytics-saved-views-select");
  const saveViewBtn = document.getElementById("admin-analytics-save-view-btn");

  const pinnedSection = document.getElementById("admin-analytics-pinned-section");
  const pinnedEl = document.getElementById("admin-analytics-pinned");

  // Export + Rapports fusionnés en une seule UI (voir le commentaire du
  // template admin.html) : la case "conserver dans l'historique" bascule
  // entre export ponctuel (période actuellement affichée) et rapport
  // persisté (période dédiée, téléchargeable plus tard) — même tableau
  // d'historique pour les deux, jamais deux UI distinctes.
  const exportForm = document.getElementById("admin-analytics-export-form");
  const exportFormatSelect = document.getElementById("admin-analytics-export-format");
  const exportKeepCheckbox = document.getElementById("admin-analytics-export-keep-checkbox");
  const exportReportTypeField = document.getElementById("admin-analytics-export-report-type-field");
  const exportReportTypeSelect = document.getElementById("admin-analytics-export-report-type");
  const exportSubmitBtn = document.getElementById("admin-analytics-export-submit-btn");
  const reportsTbody = document.getElementById("admin-analytics-reports-tbody");
  const reportsEmptyEl = document.getElementById("admin-analytics-reports-empty");

  const usersGranularitySelect = document.getElementById("admin-analytics-users-granularity-select");
  const usersChartsEl = document.getElementById("admin-analytics-users-charts");
  const chatbotChartsEl = document.getElementById("admin-analytics-chatbot-charts");
  const aiChartsEl = document.getElementById("admin-analytics-ai-charts");
  const supportChartsEl = document.getElementById("admin-analytics-support-charts");

  const chatbotRankingsEl = document.getElementById("admin-analytics-chatbot-rankings");
  const aiRankingsEl = document.getElementById("admin-analytics-ai-rankings");
  const supportRankingsEl = document.getElementById("admin-analytics-support-rankings");

  let lastOverview = null;

  const { ok: filtersOk, payload: filters } = await fetchJson("/api/admin/analytics/filters");
  if (filtersOk) {
    windowSelect.innerHTML = "";
    filters.windows.forEach((w) => windowSelect.appendChild(new Option(w.label, w.value)));
    windowSelect.value = filters.default;
  }

  const { ok: pinsOk, payload: pins } = await fetchJson("/api/admin/analytics/pinned-kpis");
  if (pinsOk) _pinnedKpis = new Set(pins.pinned);
  _onPinToggle = async (kpiKey, pinned) => {
    const csrfToken = document.cookie.match(/(?:^|; )nm_csrf=([^;]*)/);
    await fetch("/api/admin/analytics/pinned-kpis", {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        ...(csrfToken ? { "X-CSRF-Token": decodeURIComponent(csrfToken[1]) } : {}),
      },
      credentials: "same-origin",
      body: JSON.stringify({ kpi_key: kpiKey, pinned }),
    });
    if (pinned) _pinnedKpis.add(kpiKey);
    else _pinnedKpis.delete(kpiKey);
    // Épingler une clé d'un groupe jamais encore chargé (overview() ne
    // calcule désormais que les groupes réellement épinglés, voir refresh())
    // : lastOverview peut ne pas le contenir — un unique refetch ciblé
    // comble ce trou, jamais un recalcul complet des 5 groupes.
    const neededGroups = [...new Set([..._pinnedKpis].map((key) => key.split(".")[0]))];
    const missingGroups = neededGroups.filter((g) => !lastOverview || !(g in lastOverview));
    if (missingGroups.length) {
      const { ok, payload } = await fetchJson(
        `/api/admin/analytics/overview?${buildQuery()}&groups=${neededGroups.join(",")}`,
      );
      if (ok) lastOverview = payload;
    }
    if (lastOverview) renderPinned(pinnedEl, pinnedSection, lastOverview);
  };

  async function refreshSavedViews() {
    const { ok, payload } = await fetchJson("/api/admin/analytics/views");
    if (!ok) return;
    savedViewsSelect.innerHTML = "";
    savedViewsSelect.appendChild(new Option("Favoris…", ""));
    payload.items.forEach((view) => savedViewsSelect.appendChild(new Option(view.name, String(view.id))));
    savedViewsSelect.dataset.views = JSON.stringify(payload.items);
  }
  await refreshSavedViews();

  function updateCustomInputsVisibility() {
    const isCustom = windowSelect.value === "personnalise";
    dateFromInput.hidden = !isCustom;
    dateToInput.hidden = !isCustom;
  }

  function buildQuery() {
    const params = new URLSearchParams({ window: windowSelect.value });
    if (windowSelect.value === "personnalise") {
      if (dateFromInput.value) params.set("date_from", dateFromInput.value);
      if (dateToInput.value) params.set("date_to", dateToInput.value);
    }
    return params.toString();
  }

  async function refreshReports() {
    const { ok, payload } = await fetchJson("/api/admin/analytics/reports");
    if (ok) renderReports(reportsTbody, reportsEmptyEl, payload.items);
  }

  let lastCharts = null;

  async function refresh() {
    errorEl.hidden = true;
    const query = buildQuery();

    // `groups` restreint les agrégations réellement calculées par
    // overview() à celles dont un KPI est épinglé (voir PINNABLE_KPIS côté
    // backend, clés "groupe.champ") — vide si aucun pin, jamais omis
    // (l'absence du paramètre garde l'ancien comportement "tout calculer",
    // réservé aux autres appelants éventuels de la fonction Python).
    const pinnedGroups = [...new Set([..._pinnedKpis].map((key) => key.split(".")[0]))];
    const overviewQuery = `${query}&groups=${pinnedGroups.join(",")}`;

    const [overviewRes, chartsRes, rankingsRes] = await Promise.all([
      fetchJson(`/api/admin/analytics/overview?${overviewQuery}`),
      fetchJson(`/api/admin/analytics/charts?${query}`),
      fetchJson(`/api/admin/analytics/rankings?${query}&limit=10`),
    ]);

    if (!overviewRes.ok) {
      errorEl.hidden = false;
      errorEl.textContent = overviewRes.payload.error || "Impossible de charger les statistiques.";
      return;
    }
    const payload = overviewRes.payload;
    lastOverview = payload;

    windowLabelEl.textContent = payload.window.until
      ? `Période : ${formatDateTime(payload.window.since)} → ${formatDateTime(payload.window.until)}`
      : `Depuis : ${formatDateTime(payload.window.since)}`;

    renderPinned(pinnedEl, pinnedSection, payload);

    destroyCharts();
    if (chartsRes.ok) {
      const charts = chartsRes.payload;
      lastCharts = charts;
      renderUsersChart(usersChartsEl, charts.users, usersGranularitySelect.value);
      renderChatbotCharts(chatbotChartsEl, charts.chatbot);
      renderAiCharts(aiChartsEl, charts.ai);
      renderSupportCharts(supportChartsEl, charts.support);
    }

    if (rankingsRes.ok) {
      const rankings = rankingsRes.payload;
      renderChatbotRankings(chatbotRankingsEl, rankings);
      renderAiRankings(aiRankingsEl, rankings);
      renderSupportRankings(supportRankingsEl, rankings);
    }
  }

  const runSearch = debounce(async () => {
    const q = searchInput.value.trim();
    if (q.length < 2) {
      searchResultsSection.hidden = true;
      return;
    }
    const { ok, payload } = await fetchJson(`/api/admin/analytics/search?q=${encodeURIComponent(q)}`);
    if (ok) renderSearchResults(searchResultsBody, searchResultsSection, payload);
  }, SEARCH_DEBOUNCE_MS);
  searchInput.addEventListener("input", runSearch);

  updateCustomInputsVisibility();
  windowSelect.addEventListener("change", () => {
    updateCustomInputsVisibility();
    refresh();
  });
  dateFromInput.addEventListener("change", () => refresh());
  dateToInput.addEventListener("change", () => refresh());

  // Changer la granularité ne relance AUCUN appel réseau : toutes les
  // séries (jour/mois/année) sont déjà dans la réponse charts() courante
  // (lastCharts), seul le graphique Utilisateurs est redessiné.
  usersGranularitySelect.addEventListener("change", () => {
    if (lastCharts) renderUsersChart(usersChartsEl, lastCharts.users, usersGranularitySelect.value);
  });

  savedViewsSelect.addEventListener("change", () => {
    if (!savedViewsSelect.value) return;
    const views = JSON.parse(savedViewsSelect.dataset.views || "[]");
    const view = views.find((v) => String(v.id) === savedViewsSelect.value);
    if (!view) return;
    windowSelect.value = view.params.window;
    updateCustomInputsVisibility();
    if (view.params.window === "personnalise") {
      dateFromInput.value = view.params.date_from || "";
      dateToInput.value = view.params.date_to || "";
    }
    refresh();
  });

  saveViewBtn.addEventListener("click", async () => {
    const name = window.prompt("Nom de cette vue favorite :");
    if (!name) return;
    const csrfToken = document.cookie.match(/(?:^|; )nm_csrf=([^;]*)/);
    const res = await fetch("/api/admin/analytics/views", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(csrfToken ? { "X-CSRF-Token": decodeURIComponent(csrfToken[1]) } : {}),
      },
      credentials: "same-origin",
      body: JSON.stringify({
        name,
        window: windowSelect.value,
        date_from: dateFromInput.value || null,
        date_to: dateToInput.value || null,
      }),
    });
    const payload = await res.json().catch(() => ({}));
    if (!res.ok) {
      alert(payload.error || "Impossible d'enregistrer cette vue.");
      return;
    }
    await refreshSavedViews();
  });

  // "Imprimer" a été retiré (doublon fonctionnel confirmé avec l'export PDF
  // serveur — mise en page dédiée + graphiques vectoriels réels, jamais une
  // simple capture de la page web).

  // Export + Rapports fusionnés (voir le commentaire de la section dans
  // admin.html) : la case "conserver dans l'historique" est le SEUL
  // discriminant — décochée = export ponctuel de la période actuellement
  // affichée (ancien comportement des 3 boutons "Exporter CSV/Excel/PDF"),
  // cochée = rapport persisté sur disque, avec sa propre période dédiée
  // (ancien comportement de la section "Rapports"). Les deux apparaissent
  // dans le même tableau d'historique ci-dessous.
  const EXPORT_FORMAT_TO_ENDPOINT = { csv: "csv", xlsx: "excel", pdf: "pdf" };

  function updateExportKeepUi() {
    const keep = exportKeepCheckbox.checked;
    exportReportTypeField.hidden = !keep;
    exportSubmitBtn.textContent = keep ? "Générer le rapport" : "Exporter";
  }
  exportKeepCheckbox.addEventListener("change", updateExportKeepUi);
  updateExportKeepUi();

  exportForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const format = exportFormatSelect.value;

    if (!exportKeepCheckbox.checked) {
      // Export ponctuel : jamais écrit sur disque, journalisé côté serveur
      // (export_logged()) — même mécanisme que les anciens liens <a href>.
      const url = `/api/admin/analytics/export/${EXPORT_FORMAT_TO_ENDPOINT[format]}?${buildQuery()}`;
      const link = document.createElement("a");
      link.href = url;
      document.body.appendChild(link);
      link.click();
      link.remove();
      setTimeout(refreshReports, 1000);
      return;
    }

    const originalLabel = exportSubmitBtn.textContent;
    exportSubmitBtn.disabled = true;
    exportSubmitBtn.textContent = "Génération en cours…";
    const csrfToken = document.cookie.match(/(?:^|; )nm_csrf=([^;]*)/);
    const res = await fetch("/api/admin/analytics/reports", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(csrfToken ? { "X-CSRF-Token": decodeURIComponent(csrfToken[1]) } : {}),
      },
      credentials: "same-origin",
      body: JSON.stringify({ report_type: exportReportTypeSelect.value, format }),
    });
    const payload = await res.json().catch(() => ({}));
    exportSubmitBtn.disabled = false;
    exportSubmitBtn.textContent = originalLabel;
    if (!res.ok) {
      alert(payload.error || "Génération impossible.");
      return;
    }
    await refreshReports();
  });

  await Promise.all([refresh(), refreshReports()]);

  // Rafraîchissement automatique — ne recharge que les données (jamais toute
  // la page), stoppé dès que ce module quitte le DOM (voir admin-health.js
  // pour le même mécanisme d'observation de #admin-content-body).
  const intervalId = setInterval(() => refresh(), REFRESH_INTERVAL_MS);
  const contentBody = document.getElementById("admin-content-body");
  const observer = new MutationObserver(() => {
    if (!document.body.contains(usersChartsEl)) {
      clearInterval(intervalId);
      destroyCharts();
      observer.disconnect();
    }
  });
  if (contentBody) observer.observe(contentBody, { childList: true });
}
