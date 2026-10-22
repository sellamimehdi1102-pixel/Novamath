// Module "Fréquentation" (/admin/frequentation) — Phase 2 Cloudflare,
// finalisé après introspection réelle du schéma GraphQL (2026-10-21).
// Affiche les statistiques de FRÉQUENTATION DU SITE (Cloudflare Web
// Analytics, données externes) — jamais les comptes/l'activité Mathadap
// (voir admin-analytics.js pour cela), jamais mélangées dans une même
// carte. Toutes les données viennent de cloudflare_analytics_service.py
// (voir GET /api/admin/frequentation/{filters,overview,charts,rankings}) :
// {available:false, reason:"...", status:"not_configured"|"api_error"} ou
// {available:true, value:..., status:"ok"} = jamais fabriqué, même
// convention que admin-analytics.js/admin-health.js. "Visites" (sum.visits,
// mesure RUM interne Cloudflare) n'est JAMAIS présentée comme un nombre de
// visiteurs uniques identifiés — voir le "note" renvoyé par le backend,
// toujours affiché tel quel. Le rendu des graphiques reprend le même
// pattern Chart.js que admin-analytics.js/admin-health.js (destroyCharts()),
// jamais réinventé ; les classements réutilisent les mêmes classes CSS que
// les classements du module Analytics (admin-analytics-ranking-*).
//
// ── État vide groupé (Chantier Fréquentation, 2026-10-22) ──────────────────
// En l'absence de donnée réelle, les 3 sections détaillées (vue d'ensemble +
// évolution + classements, ~1300px à vide) sont remplacées par UNE SEULE
// carte compacte (voir computeEmptyState()) — le `status` explicite du
// backend (jamais un string-matching sur `reason`) détermine le message et
// l'action : "not_configured" (lien vers .env.example, pas de bouton), "api_
// error" (raison réelle + bouton Réessayer), "zero_real" (intégration OK,
// vraiment aucun trafic — message rassurant, pas de bouton). Dès qu'une
// seule métrique a une vraie donnée (y compris une métrique à 0 PARMI
// d'autres qui ont du contenu), l'affichage détaillé habituel revient.
import { Chart } from "chart.js/auto";

const EMPTY_LABEL = "Cette fonctionnalité n'est pas encore alimentée.";
const NO_DATA_LABEL = "Aucune donnée pour cette période.";

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

function formatNumber(value) {
  return typeof value === "number" ? value.toLocaleString("fr-FR") : String(value);
}

// ── Graphiques (Chart.js) — même pattern que admin-analytics.js/admin-health.js ──
let _chartInstances = [];

function destroyCharts() {
  _chartInstances.forEach((c) => c.destroy());
  _chartInstances = [];
}

function unavailableMessage(box, reasonOrNoData) {
  box.appendChild(el("p", "admin-empty", reasonOrNoData));
}

// ── Vue d'ensemble : 2 cartes (Visites / Pages vues), valeur courante +
// période précédente + note (définition "visites", jamais une donnée
// fabriquée pour une métrique indisponible) ────────────────────────────────
function overviewCard(label, current, previous) {
  const card = el("article", "admin-card");
  card.appendChild(el("div", "admin-card-label", label));
  if (!current || !current.available) {
    card.appendChild(el("div", "admin-card-value admin-card-value--empty", EMPTY_LABEL));
    if (current && current.reason) card.appendChild(el("div", "admin-card-sub", current.reason));
    return card;
  }
  card.appendChild(el("div", "admin-card-value", formatNumber(current.value)));
  if (previous && previous.available) {
    card.appendChild(el("div", "admin-card-sub", `Période précédente : ${formatNumber(previous.value)}`));
  }
  if (current.note) card.appendChild(el("div", "admin-card-sub", current.note));
  return card;
}

function renderOverview(container, overview) {
  container.innerHTML = "";
  container.appendChild(overviewCard("Visites", overview.visits, overview.visits_previous_period));
  container.appendChild(overviewCard("Pages vues", overview.pageviews, overview.pageviews_previous_period));
}

// ── Évolution quotidienne : UN SEUL graphique à 2 séries (visites + pages
// vues), jamais deux graphiques distincts pour la même période (redondant) ──
function renderEvolutionChart(box, daily) {
  box.innerHTML = "";
  box.classList.remove("admin-health-chart-box--compact");
  box.appendChild(el("h3", "admin-health-chart-title", "Visites et pages vues par jour"));
  if (!daily || !daily.available) {
    box.classList.add("admin-health-chart-box--compact");
    unavailableMessage(box, (daily && daily.reason) || EMPTY_LABEL);
    return;
  }
  if (!daily.value.length) {
    box.classList.add("admin-health-chart-box--compact");
    unavailableMessage(box, daily.note || NO_DATA_LABEL);
    return;
  }
  const canvas = document.createElement("canvas");
  box.appendChild(canvas);
  const chart = new Chart(canvas, {
    type: "line",
    data: {
      labels: daily.value.map((p) => p.date),
      datasets: [
        {
          label: "Visites",
          data: daily.value.map((p) => p.visits),
          borderColor: "#7c5cff",
          backgroundColor: "#7c5cff33",
          fill: true,
          tension: 0.25,
          borderWidth: 2,
          pointRadius: 2,
        },
        {
          label: "Pages vues",
          data: daily.value.map((p) => p.pageviews),
          borderColor: "#3B82F6",
          backgroundColor: "#3B82F633",
          fill: true,
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
  _chartInstances.push(chart);
}

// ── Classements : pages/sources de trafic en liste (même pattern que les
// classements du module Analytics, admin-analytics-ranking-*), pays/
// navigateurs/appareils en camembert (répartition, Chart.js) — jamais deux
// représentations pour la même donnée. ──────────────────────────────────────
function rankingListBox(title, metric) {
  const box = el("div", "admin-analytics-ranking-box");
  box.appendChild(el("h4", "admin-analytics-ranking-title", title));
  if (!metric || !metric.available) {
    box.appendChild(el("p", "admin-empty", (metric && metric.reason) || EMPTY_LABEL));
    return box;
  }
  if (!metric.value.length) {
    box.appendChild(el("p", "admin-empty", metric.note || NO_DATA_LABEL));
    return box;
  }
  metric.value.forEach((row) => {
    const rowEl = el("div", "admin-analytics-ranking-row");
    rowEl.appendChild(el("span", "admin-analytics-ranking-name", row.label));
    rowEl.appendChild(el("span", "admin-analytics-ranking-value", `${formatNumber(row.pageviews)} pages vues`));
    box.appendChild(rowEl);
  });
  return box;
}

function renderPieRanking(container, title, metric) {
  const box = el("div", "admin-health-chart-box");
  box.appendChild(el("h3", "admin-health-chart-title", title));
  if (!metric || !metric.available) {
    box.classList.add("admin-health-chart-box--compact");
    unavailableMessage(box, (metric && metric.reason) || EMPTY_LABEL);
    container.appendChild(box);
    return;
  }
  if (!metric.value.length) {
    box.classList.add("admin-health-chart-box--compact");
    unavailableMessage(box, metric.note || NO_DATA_LABEL);
    container.appendChild(box);
    return;
  }
  const palette = [
    "#7c5cff",
    "#3B82F6",
    "#22C55E",
    "#D97757",
    "#dc8f2e",
    "#dd4b56",
    "#06b6d4",
    "#a855f7",
    "#ec4899",
    "#64748b",
  ];
  const canvas = document.createElement("canvas");
  box.appendChild(canvas);
  const chart = new Chart(canvas, {
    type: "pie",
    data: {
      labels: metric.value.map((row) => row.label),
      datasets: [
        {
          data: metric.value.map((row) => row.pageviews),
          backgroundColor: metric.value.map((_row, i) => palette[i % palette.length]),
        },
      ],
    },
    options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: "bottom" } } },
  });
  _chartInstances.push(chart);
  container.appendChild(box);
}

function renderRankings(container, rankings) {
  container.innerHTML = "";

  const listsRow = el("div", "admin-cards");
  listsRow.appendChild(rankingListBox("Top 10 des pages consultées", rankings.top_pages));
  listsRow.appendChild(rankingListBox("Sources de trafic", rankings.top_referrers));
  container.appendChild(listsRow);

  const chartsRow = el("div", "admin-cards");
  renderPieRanking(chartsRow, "Répartition des pays", rankings.top_countries);
  renderPieRanking(chartsRow, "Répartition des navigateurs", rankings.top_browsers);
  renderPieRanking(chartsRow, "Répartition des types d'appareils", rankings.top_devices);
  container.appendChild(chartsRow);
}

// ── État vide groupé ─────────────────────────────────────────────────────
// `hasRealData` : true uniquement pour une métrique disponible ET non vide
// (valeur > 0, ou liste non vide) — une métrique à 0/[] confirmée compte
// comme "réelle" dès qu'au MOINS UNE AUTRE métrique a du contenu (voir
// computeEmptyState, qui regarde l'ensemble des métriques, jamais une
// seule isolément).
function hasRealData(metric) {
  if (!metric || !metric.available) return false;
  if (Array.isArray(metric.value)) return metric.value.length > 0;
  return typeof metric.value === "number" ? metric.value > 0 : Boolean(metric.value);
}

function allMetrics(overview, charts, rankings) {
  return [
    overview.pageviews,
    overview.visits,
    overview.pageviews_previous_period,
    overview.visits_previous_period,
    charts.daily,
    rankings.top_pages,
    rankings.top_countries,
    rankings.top_referrers,
    rankings.top_browsers,
    rankings.top_devices,
  ];
}

// Renvoie null si au moins une métrique a une vraie donnée (affichage
// détaillé habituel), sinon le statut à afficher dans la carte compacte :
// "not_configured" / "api_error" (prioritaire : une erreur réelle doit
// toujours être visible, jamais masquée derrière "non configuré") / "zero_
// real" (toutes les métriques sont disponibles mais confirment zéro trafic).
function computeEmptyState(overview, charts, rankings) {
  const metrics = allMetrics(overview, charts, rankings);
  if (metrics.some(hasRealData)) return null;

  const statuses = metrics.filter((m) => m && !m.available).map((m) => m.status);
  const reason = (metrics.find((m) => m && !m.available && m.status === "api_error") || {}).reason;
  if (statuses.includes("api_error")) return { status: "api_error", reason };
  if (statuses.includes("not_configured")) return { status: "not_configured" };
  return { status: "zero_real" };
}

function renderEmptyState(emptyStateEl, titleEl, messageEl, retryBtn, { status, reason }, onRetry) {
  retryBtn.hidden = true;
  retryBtn.onclick = null;
  if (status === "not_configured") {
    titleEl.textContent = "Fréquentation — intégration non configurée";
    messageEl.textContent =
      "L'intégration Cloudflare Web Analytics n'est pas configurée sur cet environnement " +
      "(variables CLOUDFLARE_API_TOKEN/CLOUDFLARE_ACCOUNT_TAG/CLOUDFLARE_SITE_TAG) — voir .env.example.";
  } else if (status === "api_error") {
    titleEl.textContent = "Fréquentation — service indisponible";
    messageEl.textContent = reason || "L'API Cloudflare n'a pas répondu correctement.";
    retryBtn.hidden = false;
    retryBtn.onclick = onRetry;
  } else {
    titleEl.textContent = "Fréquentation";
    messageEl.textContent = "Aucune visite enregistrée sur cette période — l'intégration fonctionne normalement.";
  }
  emptyStateEl.hidden = false;
}

// ── Skeleton (état de chargement) — même pattern que admin-dashboard.js::
// renderSkeletons (un bloc qui pulse à la place de la valeur, jamais un
// vide silencieux confondu avec une vraie absence de donnée). ─────────────
function renderOverviewSkeletons(container) {
  container.innerHTML = "";
  ["Visites", "Pages vues"].forEach((label) => {
    const card = el("article", "admin-card");
    card.appendChild(el("div", "admin-card-label", label));
    card.appendChild(el("div", "admin-card-value admin-skeleton", " "));
    container.appendChild(card);
  });
}

export async function loadFrequentation() {
  const windowSelect = document.getElementById("admin-frequentation-window-select");
  const samplingNoteEl = document.getElementById("admin-frequentation-sampling-note");
  const errorEl = document.getElementById("admin-frequentation-error");
  const overviewCards = document.getElementById("admin-frequentation-overview-cards");
  const evolutionChartBox = document.getElementById("admin-frequentation-evolution-chart");
  const rankingsEl = document.getElementById("admin-frequentation-rankings");
  const detailEl = document.getElementById("admin-frequentation-detail");
  const emptyStateEl = document.getElementById("admin-frequentation-empty-state");
  const emptyStateTitleEl = document.getElementById("admin-frequentation-empty-state-title");
  const emptyStateMessageEl = document.getElementById("admin-frequentation-empty-state-message");
  const emptyStateRetryBtn = document.getElementById("admin-frequentation-empty-state-retry");

  async function refresh() {
    errorEl.hidden = true;
    samplingNoteEl.hidden = true;
    emptyStateEl.hidden = true;
    destroyCharts();
    detailEl.hidden = false;
    renderOverviewSkeletons(overviewCards);

    const window_ = windowSelect.value;

    const [overviewRes, chartsRes, rankingsRes] = await Promise.all([
      fetchJson(`/api/admin/frequentation/overview?window=${encodeURIComponent(window_)}`),
      fetchJson(`/api/admin/frequentation/charts?window=${encodeURIComponent(window_)}`),
      fetchJson(`/api/admin/frequentation/rankings?window=${encodeURIComponent(window_)}`),
    ]);

    if (!overviewRes.ok || !chartsRes.ok || !rankingsRes.ok) {
      errorEl.textContent =
        (overviewRes.payload && overviewRes.payload.error) ||
        (chartsRes.payload && chartsRes.payload.error) ||
        (rankingsRes.payload && rankingsRes.payload.error) ||
        "Impossible de charger les statistiques de fréquentation.";
      errorEl.hidden = false;
      detailEl.hidden = true;
      return;
    }

    const emptyState = computeEmptyState(overviewRes.payload, chartsRes.payload, rankingsRes.payload);
    if (emptyState) {
      detailEl.hidden = true;
      renderEmptyState(emptyStateEl, emptyStateTitleEl, emptyStateMessageEl, emptyStateRetryBtn, emptyState, refresh);
      return;
    }

    const samplingNote = overviewRes.payload.sampling_note || chartsRes.payload.sampling_note;
    if (samplingNote) {
      samplingNoteEl.textContent = samplingNote;
      samplingNoteEl.hidden = false;
    }

    renderOverview(overviewCards, overviewRes.payload);
    renderEvolutionChart(evolutionChartBox, chartsRes.payload.daily);
    renderRankings(rankingsEl, rankingsRes.payload);
  }

  const { ok: filtersOk, payload: filters } = await fetchJson("/api/admin/frequentation/filters");
  if (filtersOk) {
    windowSelect.innerHTML = "";
    filters.windows.forEach((w) => windowSelect.appendChild(new Option(w.label, w.value)));
    windowSelect.value = filters.default;
  }

  windowSelect.addEventListener("change", refresh);
  await refresh();
}
