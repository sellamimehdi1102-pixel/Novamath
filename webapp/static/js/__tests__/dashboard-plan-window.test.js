// ── dashboard.js : répartition Free / Premium / Ultra du graphique et du
// sélecteur de fenêtre "Résultats au fil des séries" (chantier "Répartition
// des options du dashboard par plan", 2026-08-26 ; fenêtres simplifiées en
// 5/15/Tout le 2026-10-19). ─────────────────────────────────────────────────
// Le backend (/api/stats) fournit déjà `series[]` correctement tronqué selon
// le plan effectif (voir test_dashboard_stats_plan_window.py côté serveur) —
// ce fichier vérifie que le FRONTEND se contente d'exposer/verrouiller les
// bonnes options du sélecteur 5/15/Tout sans recréer de logique de
// filtrage, et que le reste du dashboard (streak, XP, badges, mastery,
// suggestions, objectif du jour, série en cours, reprise de cours) continue
// de fonctionner à l'identique quel que soit le plan.
import { describe, it, expect, vi } from "vitest";
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
    id: `ex_${ts}`,
    ts,
    date: "2026-08-20",
    chapter: "Chapitre_1",
    notion: "n1",
    difficulty: 1,
    correct,
    mode: "revisions",
    duration_s: 30,
    xp: 5,
    class_level: "seconde",
  };
}

function seriesEntry(startedAt) {
  return {
    id: `s_${startedAt}`,
    startedAt,
    endedAt: startedAt + 100,
    mode: "revisions",
    chapterId: "Chapitre_1",
    notion: "n1",
    questions: [],
    score: 8,
    total: 10,
    accuracy: 80,
    durationTotal_s: 100,
    class_level: "seconde",
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

async function mountDashboard({ plan = "free", effectivePlan = plan, stats } = {}) {
  document.body.innerHTML = loadPageBody("dashboard.html");
  document.documentElement.setAttribute("data-animations", "off");
  localStorage.clear();
  defaultMocks();
  mockApi.me.mockResolvedValue({
    user: {
      id: 1,
      pseudo: "Élève",
      username: "eleve",
      email: "e@gmail.com",
      is_guest: false,
      plan,
      effective_plan: effectivePlan,
    },
  });
  mockApi.getStats.mockResolvedValue(stats || statsFixture());
  vi.resetModules();
  await import("../dashboard.js");
  await flushPromises();
  await flushPromises();
  await flushPromises();
}

describe("dashboard.js — verrouillage du sélecteur de fenêtre par plan", () => {
  it("Free : 5 accessible, 15 et Tout verrouillés (disabled + badge)", async () => {
    await mountDashboard({ plan: "free" });
    const btn5 = document.querySelector('.chart-zoom-btn[data-window="5"]');
    const btn15 = document.querySelector('.chart-zoom-btn[data-window="15"]');
    const btnAll = document.querySelector('.chart-zoom-btn[data-window="all"]');

    expect(btn5.disabled).toBe(false);
    expect(btn15.disabled).toBe(true);
    expect(btnAll.disabled).toBe(true);
    expect(btn5.querySelector(".chart-zoom-lock-badge")).toBeNull();
    expect(btn15.querySelector(".chart-zoom-lock-badge")?.textContent).toBe("Premium");
    expect(btnAll.querySelector(".chart-zoom-lock-badge")?.textContent).toBe("Ultra");
  });

  it("5 est la fenêtre active par défaut à l'ouverture du dashboard, quel que soit le plan", async () => {
    for (const plan of ["free", "premium", "ultra"]) {
      await mountDashboard({ plan });
      const btn5 = document.querySelector('.chart-zoom-btn[data-window="5"]');
      expect(btn5.classList.contains("active")).toBe(true);
    }
  });

  it("Premium : 5/15 accessibles, Tout verrouillé", async () => {
    await mountDashboard({ plan: "premium" });
    expect(document.querySelector('.chart-zoom-btn[data-window="5"]').disabled).toBe(false);
    expect(document.querySelector('.chart-zoom-btn[data-window="15"]').disabled).toBe(false);
    expect(document.querySelector('.chart-zoom-btn[data-window="all"]').disabled).toBe(true);
  });

  it("Ultra : les trois options sont accessibles, aucun badge de verrouillage", async () => {
    await mountDashboard({ plan: "ultra" });
    document.querySelectorAll(".chart-zoom-btn").forEach((btn) => {
      expect(btn.disabled).toBe(false);
      expect(btn.querySelector(".chart-zoom-lock-badge")).toBeNull();
    });
  });

  it("cliquer sur un bouton verrouillé (Free → 15) ne change rien : le graphique respecte les données déjà reçues du backend, sans deuxième filtrage frontend", async () => {
    await mountDashboard({ plan: "free" });
    const btn5 = document.querySelector('.chart-zoom-btn[data-window="5"]');
    const btn15 = document.querySelector('.chart-zoom-btn[data-window="15"]');
    expect(btn5.classList.contains("active")).toBe(true);

    btn15.click();
    await flushPromises();

    expect(btn15.classList.contains("active")).toBe(false);
    expect(btn5.classList.contains("active")).toBe(true);
  });

  it("cliquer sur un bouton accessible (Ultra → Tout) change bien la fenêtre active", async () => {
    await mountDashboard({ plan: "ultra" });
    const btnAll = document.querySelector('.chart-zoom-btn[data-window="all"]');
    btnAll.click();
    await flushPromises();
    expect(btnAll.classList.contains("active")).toBe(true);
  });
});

describe("dashboard.js — les verrous suivent effective_plan, jamais le plan réel facturé (régression bug badges figés)", () => {
  it("un compte Owner en test Premium (plan réel free, effective_plan premium) débloque bien 15", async () => {
    await mountDashboard({ plan: "free", effectivePlan: "premium" });
    const btn15 = document.querySelector('.chart-zoom-btn[data-window="15"]');
    expect(btn15.disabled).toBe(false);
    expect(btn15.querySelector(".chart-zoom-lock-badge")).toBeNull();
  });

  it("un changement de plan de test via novamath:account-updated met à jour les verrous sans rechargement", async () => {
    await mountDashboard({ plan: "free", effectivePlan: "free" });
    const btnAll = document.querySelector('.chart-zoom-btn[data-window="all"]');
    expect(btnAll.disabled).toBe(true);

    window.dispatchEvent(
      new CustomEvent("novamath:account-updated", {
        detail: { pseudo: "Élève", username: "eleve", email: "e@gmail.com", plan: "free", effective_plan: "ultra" },
      }),
    );
    await flushPromises();

    expect(btnAll.disabled).toBe(false);
    expect(btnAll.querySelector(".chart-zoom-lock-badge")).toBeNull();
  });
});

describe("dashboard.js — réaction du GRAPHIQUE lui-même à un changement de plan (régression : verrous corrects mais graphique figé)", () => {
  it("rétrogradation Ultra → Free alors que 'Tout' est sélectionné : retombe automatiquement sur la fenêtre 5, et le bouton 'Tout' perd sa classe active", async () => {
    await mountDashboard({ plan: "ultra", effectivePlan: "ultra", stats: statsFixture({ nHistory: 20, nSeries: 20 }) });
    const btn5 = document.querySelector('.chart-zoom-btn[data-window="5"]');
    const btnAll = document.querySelector('.chart-zoom-btn[data-window="all"]');

    btnAll.click();
    await flushPromises();
    expect(document.querySelectorAll("#progress-chart .chart-dot").length).toBe(20);
    expect(btnAll.classList.contains("active")).toBe(true);

    // Le serveur, lui, ne renverrait plus que 5 séries pour un compte Free
    // (voir server.py::_STATS_SERIES_WINDOW) — le second appel GET /api/stats
    // déclenché par le changement de plan doit refléter cette troncature.
    mockApi.getStats.mockResolvedValue(statsFixture({ nHistory: 20, nSeries: 5 }));
    window.dispatchEvent(
      new CustomEvent("novamath:account-updated", {
        detail: { pseudo: "Élève", username: "eleve", email: "e@gmail.com", plan: "free", effective_plan: "free" },
      }),
    );
    await flushPromises();

    expect(btnAll.disabled).toBe(true);
    expect(btnAll.classList.contains("active")).toBe(false);
    expect(btn5.classList.contains("active")).toBe(true);
    expect(document.querySelectorAll("#progress-chart .chart-dot").length).toBe(5);
  });

  it("upgrade Free → Premium : un nouvel appel API ramène réellement plus de séries, pas seulement un re-découpage de l'historique déjà en mémoire", async () => {
    // Sous Free, le backend n'aurait jamais envoyé plus de 5 séries : c'est
    // tout ce que le frontend a en mémoire avant l'upgrade.
    await mountDashboard({ plan: "free", effectivePlan: "free", stats: statsFixture({ nHistory: 5, nSeries: 5 }) });
    expect(document.querySelectorAll("#progress-chart .chart-dot").length).toBe(5);

    const btn15 = document.querySelector('.chart-zoom-btn[data-window="15"]');
    expect(btn15.disabled).toBe(true);

    // Après l'upgrade, le serveur enverrait désormais jusqu'à 15 séries
    // (Premium) — le fetch déclenché par account-updated doit les récupérer.
    mockApi.getStats.mockResolvedValue(statsFixture({ nHistory: 15, nSeries: 15 }));
    window.dispatchEvent(
      new CustomEvent("novamath:account-updated", {
        detail: { pseudo: "Élève", username: "eleve", email: "e@gmail.com", plan: "premium", effective_plan: "premium" },
      }),
    );
    await flushPromises();
    await flushPromises();
    await flushPromises();

    expect(btn15.disabled).toBe(false);
    // La fenêtre sélectionnée (5) reste inchangée par un upgrade (seule une
    // fenêtre devenue INTERDITE force un repli) : toujours 5 points...
    expect(document.querySelectorAll("#progress-chart .chart-dot").length).toBe(5);

    // ...mais cliquer sur 15 (désormais accessible) doit afficher les 15
    // séries fraîchement récupérées, pas seulement les 5 déjà en mémoire.
    btn15.click();
    await flushPromises();
    expect(document.querySelectorAll("#progress-chart .chart-dot").length).toBe(15);
  });

  it("passage à Ultra débloque 'Tout' et l'affiche avec l'historique complet fraîchement récupéré", async () => {
    await mountDashboard({ plan: "premium", effectivePlan: "premium", stats: statsFixture({ nHistory: 15, nSeries: 15 }) });
    const btnAll = document.querySelector('.chart-zoom-btn[data-window="all"]');
    expect(btnAll.disabled).toBe(true);

    mockApi.getStats.mockResolvedValue(statsFixture({ nHistory: 40, nSeries: 40 }));
    window.dispatchEvent(
      new CustomEvent("novamath:account-updated", {
        detail: { pseudo: "Élève", username: "eleve", email: "e@gmail.com", plan: "ultra", effective_plan: "ultra" },
      }),
    );
    await flushPromises();
    await flushPromises();
    await flushPromises();

    expect(btnAll.disabled).toBe(false);
    btnAll.click();
    await flushPromises();
    expect(document.querySelectorAll("#progress-chart .chart-dot").length).toBe(40);
  });

  it("un clic sur une fenêtre après un changement de plan réutilise les données fraîches, jamais l'ancien historique du store local", async () => {
    await mountDashboard({ plan: "free", effectivePlan: "free", stats: statsFixture({ nHistory: 5, nSeries: 5 }) });

    mockApi.getStats.mockResolvedValue(statsFixture({ nHistory: 15, nSeries: 15 }));
    window.dispatchEvent(
      new CustomEvent("novamath:account-updated", {
        detail: { pseudo: "Élève", username: "eleve", email: "e@gmail.com", plan: "premium", effective_plan: "premium" },
      }),
    );
    await flushPromises();
    await flushPromises();
    await flushPromises();

    const btn15 = document.querySelector('.chart-zoom-btn[data-window="15"]');
    const btn5 = document.querySelector('.chart-zoom-btn[data-window="5"]');
    btn15.click();
    await flushPromises();
    expect(document.querySelectorAll("#progress-chart .chart-dot").length).toBe(15);

    btn5.click();
    await flushPromises();
    expect(document.querySelectorAll("#progress-chart .chart-dot").length).toBe(5);
  });
});

describe("dashboard.js — non-régression des fonctionnalités communes aux trois plans", () => {
  it.each(["free", "premium", "ultra"])(
    "streak, XP et accuracy s'affichent normalement pour le plan %s",
    async (plan) => {
      await mountDashboard({ plan, stats: statsFixture({ nHistory: 12, nSeries: 3 }) });
      expect(document.getElementById("streak-value").textContent).not.toBe("");
      expect(document.getElementById("xp-value").textContent).toContain("XP");
      expect(document.getElementById("accuracy-value").textContent).toMatch(/\/ 20/);
    },
  );

  it.each(["free", "premium", "ultra"])(
    "les badges se calculent à partir de l'historique complet, identiques quel que soit le plan (%s)",
    async (plan) => {
      // 10 exercices d'historique (nHistory=10), indépendant de la fenêtre
      // `series` (5 ici) : le badge "10 exercices" doit se débloquer même en
      // Free, preuve que `history[]` n'est jamais tronqué par la restriction
      // appliquée à `series[]`.
      await mountDashboard({ plan, stats: statsFixture({ nHistory: 10, nSeries: 5 }) });
      const badgesCounter = document.getElementById("badges-counter").textContent;
      expect(badgesCounter).toMatch(/^\d+ \/ \d+$/);
      const unlockedCount = Number(badgesCounter.split(" / ")[0]);
      expect(unlockedCount).toBeGreaterThanOrEqual(1);
    },
  );

  it.each(["free", "premium", "ultra"])(
    "les suggestions et chapitres à revoir se basent sur l'historique complet (%s)",
    async (plan) => {
      await mountDashboard({ plan, stats: statsFixture({ nHistory: 8, nSeries: 2 }) });
      // Ne doit jamais rester sur l'état vide "Fais ta première évaluation..."
      expect(document.getElementById("suggestions").textContent).not.toContain("première évaluation");
    },
  );

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
