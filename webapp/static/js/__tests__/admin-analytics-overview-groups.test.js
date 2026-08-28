// admin-analytics.js : Chantier Administrateur (P2) — overview() n'est plus
// interrogé pour calculer les 5 groupes de KPI systématiquement ; le
// frontend envoie désormais `groups=` dérivé des KPI réellement épinglés
// (voir admin_analytics_service.py::overview(groups=...) et
// test_admin_analytics_overview_groups.py pour la preuve backend).
import { describe, it, expect, vi, afterEach } from "vitest";
import { loadPageBody, flushPromises } from "./testUtils.js";

const mockLoadDashboard = vi.fn().mockResolvedValue(undefined);
vi.mock("../admin-dashboard.js", () => ({ loadDashboard: mockLoadDashboard }));

const NAV_WITH_ANALYTICS = [
  { id: "dashboard", label: "Dashboard", icon: "🏠", path: "/admin", implemented: true },
  { id: "analytics", label: "Analytics", icon: "📊", path: "/admin/analytics", implemented: true },
];

const FILTERS_PAYLOAD = { windows: [{ value: "30j", label: "30 derniers jours" }], default: "30j" };
const NA = { available: false, value: null, reason: "test" };
// Formes réelles (mêmes clés que admin_analytics_service.py::charts()/rankings()),
// toutes indisponibles : suffisant pour exercer le rendu sans planter.
const EMPTY_CHARTS = {
  window: { value: "30j", label: "30 derniers jours", since: "2026-07-26T00:00:00+00:00", until: null },
  users: { daily: NA, monthly: NA, yearly: NA },
  chatbot: {
    conversations_per_day: NA,
    messages_per_day: { user: NA, assistant: NA },
    ai_vs_local_per_day: { ai: NA, local: NA },
  },
  ai: {
    tokens_per_day: NA, cost_per_day: NA, calls_per_day: NA,
    avg_latency_per_day: NA, success_rate_per_day: NA, fallbacks_per_day: NA, errors_per_day: NA,
  },
  support: { tickets_per_day: NA, by_category: NA, by_priority: NA, by_status: NA },
};
const EMPTY_RANKINGS = {
  window: { value: "30j", label: "30 derniers jours", since: "2026-07-26T00:00:00+00:00", until: null },
  users: { top_ai_consumers: NA, top_chatbot_users: NA, top_active_reason: "test" },
  ai: { top_providers: NA, top_models: NA, top_engines: NA, top_cost: NA, top_tokens: NA },
  support: { top_categories: NA, top_priorities: NA, top_admins: NA },
};

function overviewPayload(groups) {
  const base = { window: { value: "30j", label: "30 derniers jours", since: "2026-07-26T00:00:00+00:00", until: null } };
  if (groups.includes("ai")) base.ai = { calls: { available: true, value: 42 }, tokens: { available: true, value: 1000 } };
  return base;
}

let overviewCalls;

function mockFetchWith({ pinned = [] } = {}) {
  overviewCalls = [];
  global.fetch = vi.fn((url) => {
    if (url === "/api/admin/me") {
      return Promise.resolve({ ok: true, json: () => Promise.resolve({ name: "Mehdi", email: "a@b.c", role: "super_admin", avatar: null }) });
    }
    if (url === "/api/admin/nav") {
      return Promise.resolve({ ok: true, json: () => Promise.resolve({ modules: NAV_WITH_ANALYTICS }) });
    }
    if (url === "/api/admin/analytics/filters") {
      return Promise.resolve({ ok: true, json: () => Promise.resolve(FILTERS_PAYLOAD) });
    }
    if (url === "/api/admin/analytics/pinned-kpis") {
      return Promise.resolve({ ok: true, json: () => Promise.resolve({ pinned }) });
    }
    if (url === "/api/admin/analytics/views") {
      return Promise.resolve({ ok: true, json: () => Promise.resolve({ items: [] }) });
    }
    if (url === "/api/admin/analytics/reports") {
      return Promise.resolve({ ok: true, json: () => Promise.resolve({ items: [] }) });
    }
    if (url.startsWith("/api/admin/analytics/overview")) {
      overviewCalls.push(url);
      const groupsParam = new URL(url, "http://x").searchParams.get("groups") || "";
      const groups = groupsParam.split(",").filter(Boolean);
      return Promise.resolve({ ok: true, json: () => Promise.resolve(overviewPayload(groups)) });
    }
    if (url.startsWith("/api/admin/analytics/charts")) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve(EMPTY_CHARTS) });
    }
    if (url.startsWith("/api/admin/analytics/rankings")) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve(EMPTY_RANKINGS) });
    }
    return Promise.resolve({ ok: false, status: 404, json: () => Promise.resolve({ error: "not found" }) });
  });
}

async function mount(options) {
  window.history.pushState({}, "", "/admin/analytics");
  document.body.innerHTML = loadPageBody("admin.html");
  document.cookie = "nm_csrf=test-csrf-token";
  mockFetchWith(options);
  vi.resetModules();
  const { initAdminShell } = await import("../admin-shell.js");
  await initAdminShell();
  await flushPromises();
}

afterEach(() => {
  vi.restoreAllMocks();
  document.cookie = "nm_csrf=; expires=Thu, 01 Jan 1970 00:00:00 UTC";
});

describe("admin-analytics.js — overview() n'est calculé que pour les KPI épinglés", () => {
  it("aucun KPI épinglé : groups= est vide, aucun groupe inutilement calculé", async () => {
    await mount({ pinned: [] });
    expect(overviewCalls.length).toBe(1);
    const url = new URL(overviewCalls[0], "http://x");
    expect(url.searchParams.get("groups")).toBe("");
  });

  it("un KPI déjà épinglé au chargement : son groupe est demandé dès le premier appel", async () => {
    await mount({ pinned: ["ai.calls"] });
    const url = new URL(overviewCalls[0], "http://x");
    expect(url.searchParams.get("groups")).toBe("ai");
    expect(document.getElementById("admin-analytics-pinned-section").hidden).toBe(false);
    expect(document.getElementById("admin-analytics-pinned").textContent).toContain("Appels IA");
  });

  // Chantier Administrateur "Tri des informations" (Phase 2) : "Mon tableau
  // de bord" créait une ambiguïté avec le vrai Dashboard de /admin — titre
  // seul renommé, aucun KPI retiré, aucune logique de pinning modifiée (voir
  // les tests ci-dessus, toujours verts à l'identique).
  it("le titre de la section KPI épinglés ne crée plus d'ambiguïté avec /admin", async () => {
    await mount({ pinned: ["ai.calls"] });
    const title = document.getElementById("admin-analytics-pinned-title");
    expect(title.textContent).toBe("KPI épinglés");
    expect(title.textContent).not.toContain("tableau de bord");
  });

  it("désépingler le dernier KPI d'un groupe masque la section, sans appel overview() superflu", async () => {
    // Note : l'UI actuelle n'expose une étoile que sur une carte DÉJÀ
    // épinglée (retirer, jamais ajouter — aucun sélecteur de nouveaux KPI
    // n'existe côté page). Ce test couvre donc le chemin réellement
    // atteignable ; le refetch ciblé pour un groupe manquant (voir
    // _onPinToggle dans admin-analytics.js) protège le cas où un futur
    // sélecteur d'ajout serait branché sur ce même toggle.
    await mount({ pinned: ["ai.calls"] });
    expect(overviewCalls.length).toBe(1);
    expect(document.getElementById("admin-analytics-pinned-section").hidden).toBe(false);

    const unpinBtn = [...document.querySelectorAll(".admin-analytics-pin-btn")].find((b) => b.title.includes("Retirer"));
    expect(unpinBtn).toBeDefined();
    unpinBtn.click();
    await flushPromises();

    // Le groupe "ai" était déjà chargé (lastOverview le contient encore) :
    // aucun refetch n'est nécessaire pour un simple retrait.
    expect(overviewCalls.length).toBe(1);
    expect(document.getElementById("admin-analytics-pinned-section").hidden).toBe(true);
  });
});
