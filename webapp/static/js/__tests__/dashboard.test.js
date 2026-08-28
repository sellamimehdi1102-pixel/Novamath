// ── dashboard.js : plafond de suggestions différencié par plan ─────────────
// Chantier "Différenciation des abonnements — suggestions du Dashboard"
// (2026-08-27) : GET /api/stats expose désormais `suggestions_limit`
// (Free=3/Premium=5/Ultra=8, voir server.py::_SUGGESTIONS_LIMIT_BY_PLAN) ;
// dashboard.js doit s'en servir tel quel pour plafonner l'affichage des
// suggestions déjà calculées à partir de history[] (jamais recalculées ni
// dupliquées ici). Modules périphériques (settings/resume/seriesview/icons/
// badges/guestLock/animations) mockés en no-op : hors sujet de ce test, seul
// store.js (real) + dashboard.js (real) sont exercés, comme
// api.js réel se doit d'être mocké au niveau réseau uniquement.
import { describe, it, expect, vi } from "vitest";
import { loadPageBody, flushPromises } from "./testUtils.js";

vi.mock("../settingsManager.js", () => ({
  initSettingsManager: vi.fn().mockResolvedValue(undefined),
  onSettingsChange: vi.fn(),
  getSettings: vi.fn().mockReturnValue({}),
}));
vi.mock("../settingsPopup.js", () => ({ bindSettingsButton: vi.fn() }));
vi.mock("../theme.js", () => ({ getAccentColor: () => "#000", getAccentColorSecondary: () => "#111" }));
vi.mock("../i18n.js", () => ({ bindLiveTranslations: vi.fn() }));
vi.mock("../resume.js", () => ({ renderResumeCard: vi.fn() }));
vi.mock("../courseResume.js", () => ({ renderCourseResumeCard: vi.fn() }));
vi.mock("../seriesview.js", () => ({
  getChaptersMeta: vi.fn().mockResolvedValue([]),
  buildSeriesRow: vi.fn().mockReturnValue(""),
}));
vi.mock("../icons.js", () => ({ icon: () => "" }));
vi.mock("../badgeIcons.js", () => ({ badgeIconSvg: () => "" }));
vi.mock("../animations.js", () => ({ animateCount: (el, { to, formatter }) => { el.textContent = formatter ? formatter(to) : String(to); } }));
vi.mock("../guestLockOverlay.js", () => ({
  mountGuestLockOverlay: vi.fn(),
  dismissGuestLockOverlay: vi.fn(),
  unmountGuestLockOverlay: vi.fn(),
}));

const mockApi = {
  me: vi.fn(),
  getStats: vi.fn(),
  saveStats: vi.fn().mockResolvedValue({}),
  getQuota: vi.fn().mockRejectedValue(new Error("hors sujet")),
  guestDashboardSeen: vi.fn().mockResolvedValue({ locked: false }),
  chapters: vi.fn().mockResolvedValue({ chapters_meta: [] }),
};
vi.mock("../api.js", () => ({ api: mockApi }));

function user(overrides = {}) {
  return { id: 1, pseudo: "Léa", username: "lea", email: "lea@x.com", avatar: null, plan: "free", is_guest: false, ...overrides };
}

// 5 notions distinctes, chacune avec un taux de réussite < 60% (2 bonnes /
// 5 tentatives = 40%), pour produire davantage de candidats de suggestion
// que le plus haut plafond testé (8) n'en nécessite jamais réellement mais
// suffisamment pour vérifier un plafonnement à 3/5.
function weakHistory(n) {
  const entries = [];
  for (let i = 0; i < n; i++) {
    for (let j = 0; j < 5; j++) {
      entries.push({
        chapter: `Chapitre ${i}`, notion: `Notion ${i}`, correct: j < 2,
        date: "2026-08-01", class_level: "seconde",
      });
    }
  }
  return entries;
}

async function mount({
  suggestionsLimit, historyCount = 8, planUser = {},
  notionBreakdownEnabled = false, history,
} = {}) {
  document.body.innerHTML = loadPageBody("dashboard.html");
  document.cookie = "nm_csrf=test-csrf-token";
  mockApi.me.mockReset().mockResolvedValue({ user: user(planUser) });
  mockApi.getStats.mockReset().mockResolvedValue({
    xp: 0, history: history || weakHistory(historyCount), series: [], badges: [],
    suggestions_limit: suggestionsLimit,
    notion_breakdown_enabled: notionBreakdownEnabled,
  });
  vi.resetModules();
  await import("../dashboard.js");
  await flushPromises();
  await flushPromises();
}

function suggestionCards() {
  return document.querySelectorAll("#suggestions .suggestion-card");
}

function notionBreakdownRows() {
  return document.querySelectorAll("#notion-breakdown .notion-breakdown-table tbody tr");
}

function notionBreakdownLocked() {
  return document.querySelector("#notion-breakdown .dashboard-locked-card");
}

describe("dashboard.js — plafond de suggestions par plan (suggestions_limit backend)", () => {
  it("Free : suggestions_limit=3 -> au maximum 3 cartes, malgré 8 candidats faibles", async () => {
    await mount({ suggestionsLimit: 3, historyCount: 8 });
    expect(suggestionCards().length).toBe(3);
  });

  it("Premium : suggestions_limit=5 -> au maximum 5 cartes", async () => {
    await mount({ suggestionsLimit: 5, historyCount: 8 });
    expect(suggestionCards().length).toBe(5);
  });

  it("Ultra : suggestions_limit=8 -> au maximum 8 cartes", async () => {
    await mount({ suggestionsLimit: 8, historyCount: 8 });
    expect(suggestionCards().length).toBe(8);
  });

  it("moins de suggestions disponibles que le plafond : jamais de carte fabriquée", async () => {
    await mount({ suggestionsLimit: 8, historyCount: 2 });
    expect(suggestionCards().length).toBe(2);
  });

  it("suggestions_limit absent (repli sur le comportement historique = 3)", async () => {
    await mount({ suggestionsLimit: undefined, historyCount: 8 });
    expect(suggestionCards().length).toBe(3);
  });

  it("aucun impact sur l'historique rendu (streak/accuracy dépendent de history[], jamais tronqué)", async () => {
    await mount({ suggestionsLimit: 3, historyCount: 8 });
    // 8 notions x 5 réponses = 40 entrées d'historique réellement utilisées
    // par le calcul (compteur "aujourd'hui" non pertinent ici) — on vérifie
    // simplement que le plafonnement des suggestions n'a pas fait disparaître
    // le reste du Dashboard (aucune exception, sections toujours rendues).
    expect(document.getElementById("history-body")).not.toBeNull();
    expect(document.getElementById("xp-value").textContent).not.toBe("");
  });
});

// ── Bilan de progression par notion (Premium+, notion_breakdown_enabled) ────
// Le flag vient TOUJOURS de GET /api/stats (server.py, réutilise Feature.
// ADVANCED_EXPLANATIONS via has_feature/effective_plan) — jamais déduit de
// user.plan côté client ici. Un scénario "Owner en test Premium/Ultra" est
// donc, du point de vue de dashboard.js, strictement indistinguable d'un
// compte Premium/Ultra normal : le flag reçu vaut déjà true dans les deux
// cas (la résolution effective_plan est vérifiée côté backend, voir
// tests/test_dashboard_stats_plan_window.py::TestNotionBreakdownEnabledOwnerTestPlan).
function notionHistory({ n = 3, correct = 2, durations = [10, 20, 30] } = {}) {
  const entries = [];
  for (let i = 0; i < n; i++) {
    entries.push({
      chapter: "Chapitre 1", notion: "Fonctions", ts: i + 1, date: "2026-08-01",
      correct: i < correct, duration_s: durations[i] ?? 0, class_level: "seconde",
    });
  }
  return entries;
}

describe("dashboard.js — bilan de progression par notion (notion_breakdown_enabled)", () => {
  it("Free : le bilan reste verrouillé, aucune ligne rendue", async () => {
    await mount({ notionBreakdownEnabled: false, history: notionHistory() });
    expect(notionBreakdownLocked()).not.toBeNull();
    expect(notionBreakdownRows().length).toBe(0);
  });

  it("Premium : le bilan est visible (équivalent Owner en test Premium côté frontend)", async () => {
    await mount({ notionBreakdownEnabled: true, planUser: { plan: "premium" }, history: notionHistory() });
    expect(notionBreakdownLocked()).toBeNull();
    expect(notionBreakdownRows().length).toBe(1);
  });

  it("Ultra : le bilan est également visible (équivalent Owner en test Ultra côté frontend)", async () => {
    await mount({ notionBreakdownEnabled: true, planUser: { plan: "ultra" }, history: notionHistory() });
    expect(notionBreakdownLocked()).toBeNull();
    expect(notionBreakdownRows().length).toBe(1);
  });

  it("calcule correctement le taux de réussite affiché (2/3 -> 67%)", async () => {
    await mount({ notionBreakdownEnabled: true, history: notionHistory({ n: 3, correct: 2 }) });
    const row = notionBreakdownRows()[0];
    expect(row.textContent).toContain("67%");
  });

  it("calcule correctement le nombre d'exercices (tentatives) affiché", async () => {
    await mount({ notionBreakdownEnabled: true, history: notionHistory({ n: 3, correct: 2 }) });
    const row = notionBreakdownRows()[0];
    expect(row.children[1].textContent.trim()).toBe("3");
  });

  it("calcule correctement le temps moyen affiché ((10+20+30)/3 = 20 s)", async () => {
    await mount({ notionBreakdownEnabled: true, history: notionHistory({ n: 3, durations: [10, 20, 30] }) });
    const row = notionBreakdownRows()[0];
    expect(row.children[3].textContent.trim()).toBe("20 s");
  });

  it("historique vide : message d'invitation, aucune ligne, aucune exception", async () => {
    // hydrateFromServer() n'adopte jamais un remote dont history[] est vide
    // (voir store.js — le gate `remote.history.length` protège contre un
    // écrasement par une réponse serveur vide) : pour exercer la branche
    // "historique vide" de renderNotionBreakdown avec le flag déjà à true,
    // on seed directement l'état LOCAL avant le premier rendu — scénario
    // réaliste (un compte Premium déjà hydraté une fois, revenant sans
    // avoir fait d'exercice depuis).
    localStorage.setItem("lumis:stats", JSON.stringify({
      xp: 0, history: [], badges: [], series: [], notion_breakdown_enabled: true,
    }));
    await mount({ notionBreakdownEnabled: false, history: [] });
    expect(notionBreakdownRows().length).toBe(0);
    expect(document.getElementById("notion-breakdown").textContent).toMatch(/première évaluation/);
  });

  it("données insuffisantes pour une tendance (< 4 tentatives) : jamais une tendance inventée", async () => {
    await mount({ notionBreakdownEnabled: true, history: notionHistory({ n: 3, correct: 2 }) });
    const row = notionBreakdownRows()[0];
    expect(row.children[4].textContent.trim()).toBe("—");
  });

  it("n'altère jamais history[] reçu (aucune mutation par le calcul du bilan)", async () => {
    const history = notionHistory({ n: 3, correct: 2 });
    const snapshot = JSON.parse(JSON.stringify(history));
    await mount({ notionBreakdownEnabled: true, history });
    expect(history).toEqual(snapshot);
  });
});
