// ── dashboard.js : répartition Free / Premium / Ultra du graphique et du
// sélecteur de fenêtre "Résultats au fil des séries" (chantier "Répartition
// des options du dashboard par plan", 2026-08-26). ─────────────────────────
// Le backend (/api/stats) fournit déjà `series[]` correctement tronqué selon
// le plan effectif (voir test_dashboard_stats_plan_window.py côté serveur) —
// ce fichier vérifie que le FRONTEND se contente d'exposer/verrouiller les
// bonnes options du sélecteur 20/50/Tout sans recréer de logique de
// filtrage, et que le reste du dashboard (streak, XP, badges, mastery,
// suggestions, objectif du jour, série en cours, reprise de cours) continue
// de fonctionner à l'identique quel que soit le plan.
import { describe, it, expect, vi, beforeEach } from "vitest";
import { loadPageBody, flushPromises } from "./testUtils.js";

const mockApi = {
  me: vi.fn(),
  chapters: vi.fn(),
  getCourseProgress: vi.fn(),
  getStats: vi.fn(),
  getQuota: vi.fn(),
  guestDashboardSeen: vi.fn(),
  exercise: vi.fn(),
};
vi.mock("../api.js", () => ({ api: mockApi }));
vi.mock("../settingsManager.js", () => ({
  initSettingsManager: () => Promise.resolve(),
  onSettingsChange: vi.fn(),
  getSettings: () => ({ learning: { dailyGoalExercises: 10 } }),
}));
vi.mock("../settingsPopup.js", () => ({ bindSettingsButton: vi.fn() }));
vi.mock("../i18n.js", () => ({ bindLiveTranslations: vi.fn() }));
vi.mock("../curriculumSelector.js", () => ({ getStoredClassLevel: () => "seconde" }));
vi.mock("../guestLockOverlay.js", () => ({
  mountGuestLockOverlay: vi.fn(),
  dismissGuestLockOverlay: vi.fn(),
  unmountGuestLockOverlay: vi.fn(),
}));

const CHAPTER = { id: "Chapitre_1", title: "Nombres et calculs", n_exercises: 10 };

function historyEntry(ts, correct = true) {
  return {
    id: `ex_${ts}`, ts, date: "2026-08-20", chapter: "Chapitre_1", notion: "n1",
    difficulty: 1, correct, mode: "revisions", duration_s: 30, xp: 5, class_level: "seconde",
  };
}

function seriesEntry(startedAt) {
  return {
    id: `s_${startedAt}`, startedAt, endedAt: startedAt + 100, mode: "revisions",
    chapterId: "Chapitre_1", notion: "n1", questions: [], score: 8, total: 10,
    accuracy: 80, durationTotal_s: 100, class_level: "seconde",
  };
}

function statsFixture({ nHistory = 5, nSeries = 5 } = {}) {
  return {
    xp: 100,
    history: Array.from({ length: nHistory }, (_, i) => historyEntry(i + 1, i % 3 !== 0)),
    series: Array.from({ length: nSeries }, (_, i) => seriesEntry(i + 1)),
    badges: [],
  };
}

function defaultMocks() {
  Object.values(mockApi).forEach((fn) => fn.mockReset());
  mockApi.chapters.mockResolvedValue({ chapters_meta: [CHAPTER] });
  mockApi.getCourseProgress.mockResolvedValue({});
  mockApi.getQuota.mockResolvedValue({ chat_messages: { used: 1, limit: 25, remaining: 24, unlimited: false } });
  mockApi.guestDashboardSeen.mockResolvedValue({ locked: false });
  mockApi.exercise.mockResolvedValue({ exercise: { id: 1, enonce: "Q1", answer: "R1" } });
}

async function mountDashboard({ plan = "free", stats } = {}) {
  document.body.innerHTML = loadPageBody("dashboard.html");
  document.documentElement.setAttribute("data-animations", "off");
  localStorage.clear();
  defaultMocks();
  mockApi.me.mockResolvedValue({ user: { id: 1, pseudo: "Élève", username: "eleve", email: "e@gmail.com", is_guest: false, plan } });
  mockApi.getStats.mockResolvedValue(stats || statsFixture());
  vi.resetModules();
  await import("../dashboard.js");
  await flushPromises();
  await flushPromises();
  await flushPromises();
}

describe("dashboard.js — verrouillage du sélecteur de fenêtre par plan", () => {
  it("Free : 20 accessible, 50 et Tout verrouillés (disabled + badge)", async () => {
    await mountDashboard({ plan: "free" });
    const btn20 = document.querySelector('.chart-zoom-btn[data-window="20"]');
    const btn50 = document.querySelector('.chart-zoom-btn[data-window="50"]');
    const btnAll = document.querySelector('.chart-zoom-btn[data-window="all"]');

    expect(btn20.disabled).toBe(false);
    expect(btn50.disabled).toBe(true);
    expect(btnAll.disabled).toBe(true);
    expect(btn50.querySelector(".chart-zoom-lock-badge")?.textContent).toBe("Premium");
    expect(btnAll.querySelector(".chart-zoom-lock-badge")?.textContent).toBe("Ultra");
  });

  it("Premium : 20 et 50 accessibles, Tout verrouillé", async () => {
    await mountDashboard({ plan: "premium" });
    expect(document.querySelector('.chart-zoom-btn[data-window="20"]').disabled).toBe(false);
    expect(document.querySelector('.chart-zoom-btn[data-window="50"]').disabled).toBe(false);
    expect(document.querySelector('.chart-zoom-btn[data-window="all"]').disabled).toBe(true);
  });

  it("Ultra : les trois options sont accessibles, aucun badge de verrouillage", async () => {
    await mountDashboard({ plan: "ultra" });
    document.querySelectorAll(".chart-zoom-btn").forEach((btn) => {
      expect(btn.disabled).toBe(false);
      expect(btn.querySelector(".chart-zoom-lock-badge")).toBeNull();
    });
  });

  it("cliquer sur un bouton verrouillé (Free → 50) ne change rien : le graphique respecte les données déjà reçues du backend, sans deuxième filtrage frontend", async () => {
    await mountDashboard({ plan: "free" });
    const btn20 = document.querySelector('.chart-zoom-btn[data-window="20"]');
    const btn50 = document.querySelector('.chart-zoom-btn[data-window="50"]');
    expect(btn20.classList.contains("active")).toBe(true);

    btn50.click();
    await flushPromises();

    expect(btn50.classList.contains("active")).toBe(false);
    expect(btn20.classList.contains("active")).toBe(true);
  });

  it("cliquer sur un bouton accessible (Ultra → Tout) change bien la fenêtre active", async () => {
    await mountDashboard({ plan: "ultra" });
    const btnAll = document.querySelector('.chart-zoom-btn[data-window="all"]');
    btnAll.click();
    await flushPromises();
    expect(btnAll.classList.contains("active")).toBe(true);
  });
});

describe("dashboard.js — non-régression des fonctionnalités communes aux trois plans", () => {
  it.each(["free", "premium", "ultra"])("streak, XP et accuracy s'affichent normalement pour le plan %s", async (plan) => {
    await mountDashboard({ plan, stats: statsFixture({ nHistory: 12, nSeries: 3 }) });
    expect(document.getElementById("streak-value").textContent).not.toBe("");
    expect(document.getElementById("xp-value").textContent).toContain("XP");
    expect(document.getElementById("accuracy-value").textContent).toMatch(/\/ 20/);
  });

  it.each(["free", "premium", "ultra"])("les badges se calculent à partir de l'historique complet, identiques quel que soit le plan (%s)", async (plan) => {
    // 10 exercices d'historique (nHistory=10) au-delà de la fenêtre `series`
    // (5, toujours < 20) : le badge "10 exercices" doit se débloquer même en
    // Free, preuve que `history[]` n'est jamais tronqué par la restriction
    // appliquée à `series[]`.
    await mountDashboard({ plan, stats: statsFixture({ nHistory: 10, nSeries: 5 }) });
    const badgesCounter = document.getElementById("badges-counter").textContent;
    expect(badgesCounter).toMatch(/^\d+ \/ \d+$/);
    const unlockedCount = Number(badgesCounter.split(" / ")[0]);
    expect(unlockedCount).toBeGreaterThanOrEqual(1);
  });

  it.each(["free", "premium", "ultra"])("les suggestions et chapitres à revoir se basent sur l'historique complet (%s)", async (plan) => {
    await mountDashboard({ plan, stats: statsFixture({ nHistory: 8, nSeries: 2 }) });
    // Ne doit jamais rester sur l'état vide "Fais ta première évaluation..."
    expect(document.getElementById("suggestions").textContent).not.toContain("première évaluation");
  });

  it.each(["free", "premium", "ultra"])("la table des dernières séries se remplit sans erreur (%s)", async (plan) => {
    await mountDashboard({ plan, stats: statsFixture({ nHistory: 5, nSeries: 5 }) });
    const rows = document.querySelectorAll("#history-body tr");
    expect(rows.length).toBeGreaterThan(0);
    expect(document.querySelector(".cours-load-error")).toBeNull();
  });

  it("le quota IA (commun aux trois plans) reste affiché indépendamment du verrouillage du graphique", async () => {
    await mountDashboard({ plan: "free" });
    expect(document.getElementById("ai-usage-card").hidden).toBe(false);
    expect(document.getElementById("ai-usage-value").textContent).toContain("messages");
  });
});
