// ── exercice.js : régression Chantier 6 ("Entraînement" ouvre parfois un
// ancien chapitre) — un clic générique sur "Entraînement" (sidebar, URL
// exercice.html sans paramètre) ne doit plus reprendre silencieusement une
// série ancienne restée en pause en localStorage ; seuls un F5 dans le même
// onglet pendant une série active (sessionStorage, voir TAB_ACTIVE_KEY dans
// exercice.js) ou un clic explicite sur "Reprendre la série" (?resume=1, voir
// resume.js) doivent la reprendre automatiquement.
import { describe, it, expect, vi, beforeEach } from "vitest";
import { loadPageBody, withMockedLocation, flushPromises } from "./testUtils.js";

const mockApi = {
  practiceLoad: vi.fn(),
  practiceResult: vi.fn(),
  getQuota: vi.fn().mockResolvedValue({ exercises_daily: { used: 0, remaining: 20, limit: 20, unlimited: false } }),
};
vi.mock("../api.js", () => ({ api: mockApi }));
vi.mock("../settingsManager.js", () => ({
  initSettingsManager: () => Promise.resolve(),
  getSettings: () => ({ training: {} }),
  onSettingsChange: vi.fn(),
}));
vi.mock("../settingsPopup.js", () => ({ bindSettingsButton: vi.fn() }));
vi.mock("../i18n.js", () => ({ bindLiveTranslations: vi.fn() }));
vi.mock("../mathrender.js", () => ({ setMathContent: vi.fn() }));
vi.mock("../animations.js", () => ({ fireConfetti: vi.fn(), shakeElement: vi.fn(), fadeInTransition: vi.fn() }));
vi.mock("../supportTicket.js", () => ({ openReportTicketPopup: vi.fn() }));

const $ = (id) => document.getElementById(id);
const IN_PROGRESS_KEY = "lumis:series_in_progress";
const TAB_ACTIVE_KEY = "lumis:exercice_tab_active";

// Snapshot minimal mais réaliste d'une série en pause sur "Chapitre_8" —
// exactement la forme écrite par store.js::saveInProgressSeries (voir
// exercice.js::persistProgress).
function seedStaleSeries(chapterId = "Chapitre_8") {
  localStorage.setItem(IN_PROGRESS_KEY, JSON.stringify({
    mode: "revisions",
    seriesConfig: { chapterId, notion: null },
    seriesQueue: ["ex1", "ex2", "ex3"],
    seriesIndex: 1,
    draftId: "draft-1",
    draftStartedAt: Date.now() - 60_000,
    startDate: new Date().toISOString().slice(0, 10),
    draftQuestions: [{ exercise_id: "ex1", chapter: chapterId, correct: true }],
    total: 3,
    score: 1,
    wrong: 0,
    progressPct: 33,
    class_level: "seconde",
    savedAt: Date.now() - 60_000,
  }));
}

async function mountExercice(url = "/exercice.html") {
  window.history.pushState({}, "", url);
  document.body.innerHTML = loadPageBody("exercice.html");
  mockApi.practiceLoad.mockReset();
  mockApi.practiceResult.mockReset();
  mockApi.practiceLoad.mockResolvedValue({
    exercise: { id: "ex2", chapter_id: "Chapitre_8", notion: "Dérivées", difficulty: 2, enonce: "Question ?", hint: "", answer: "", solution_steps: [] },
  });
  vi.resetModules();
  await import("../exercice.js");
  await flushPromises();
}

describe("exercice.js — reprise automatique d'une série (Chantier 6)", () => {
  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
  });

  it("clic générique 'Entraînement' (pas de ?resume, onglet neuf) : n'ouvre PAS silencieusement une série ancienne", async () => {
    seedStaleSeries("Chapitre_8");
    await mountExercice("/exercice.html");

    // Pas de reprise silencieuse : écran vide affiché, pas l'exercice de la
    // série ancienne.
    expect($("empty-state").hidden).toBe(false);
    expect($("screen-ex").hidden).toBe(true);
    expect(mockApi.practiceLoad).not.toHaveBeenCalled();
  });

  it("clic explicite 'Reprendre la série' (?resume=1) : reprend bien la série en pause", async () => {
    seedStaleSeries("Chapitre_8");
    await mountExercice("/exercice.html?resume=1");

    expect(mockApi.practiceLoad).toHaveBeenCalled();
    expect($("screen-ex").hidden).toBe(false);
    expect($("empty-state").hidden).toBe(true);
    expect($("ex-chapter-badge").textContent).toBe("Chapitre_8");
    // Le paramètre ?resume=1 est nettoyé de l'URL après usage.
    expect(window.location.search).toBe("");
  });

  it("F5 pendant une série active dans le même onglet : reprend automatiquement (sessionStorage)", async () => {
    seedStaleSeries("Chapitre_8");
    sessionStorage.setItem(TAB_ACTIVE_KEY, "1"); // posé par startSeries()/resumeSeries() avant ce rechargement
    await mountExercice("/exercice.html");

    expect(mockApi.practiceLoad).toHaveBeenCalled();
    expect($("screen-ex").hidden).toBe(false);
    expect($("ex-chapter-badge").textContent).toBe("Chapitre_8");
  });

  it("aucune série en pause : écran vide dans tous les cas (comportement inchangé)", async () => {
    await mountExercice("/exercice.html");
    expect($("empty-state").hidden).toBe(false);
    expect($("screen-ex").hidden).toBe(true);
  });

  it("Chantier 9 — navigation fraîche depuis une autre page (ex: sidebar, sans quitter la série) : ne reprend PAS malgré le marqueur sessionStorage resté collé", async () => {
    // Reproduit le bug remonté : l'élève quitte exercice.html en pleine
    // série via un lien de la sidebar (jamais le bouton "Quitter", seul
    // endroit qui nettoie TAB_ACTIVE_KEY) — le marqueur sessionStorage reste
    // à "1" indéfiniment dans cet onglet. performance.getEntriesByType
    // renvoie "navigate" pour cette arrivée fraîche sur exercice.html (pas
    // un F5 de cette page) : ne doit plus reprendre silencieusement une
    // autre série que celle attendue par l'élève.
    seedStaleSeries("Chapitre_8");
    sessionStorage.setItem(TAB_ACTIVE_KEY, "1"); // marqueur resté collé (jamais nettoyé, série jamais quittée proprement)
    const navSpy = vi.spyOn(performance, "getEntriesByType").mockReturnValue([{ type: "navigate" }]);
    try {
      await mountExercice("/exercice.html");
    } finally {
      navSpy.mockRestore();
    }

    expect($("empty-state").hidden).toBe(false);
    expect($("screen-ex").hidden).toBe(true);
    expect(mockApi.practiceLoad).not.toHaveBeenCalled();
  });

  it("Chantier 9 — retour d'historique (back_forward) vers exercice.html : reprend automatiquement, comme un F5", async () => {
    seedStaleSeries("Chapitre_8");
    sessionStorage.setItem(TAB_ACTIVE_KEY, "1");
    const navSpy = vi.spyOn(performance, "getEntriesByType").mockReturnValue([{ type: "back_forward" }]);
    try {
      await mountExercice("/exercice.html");
    } finally {
      navSpy.mockRestore();
    }

    expect(mockApi.practiceLoad).toHaveBeenCalled();
    expect($("screen-ex").hidden).toBe(false);
    expect($("ex-chapter-badge").textContent).toBe("Chapitre_8");
  });

  it("Chantier 9 — un vrai F5 (type reload) reprend toujours automatiquement, même avec l'API Navigation Timing active", async () => {
    seedStaleSeries("Chapitre_8");
    sessionStorage.setItem(TAB_ACTIVE_KEY, "1");
    const navSpy = vi.spyOn(performance, "getEntriesByType").mockReturnValue([{ type: "reload" }]);
    try {
      await mountExercice("/exercice.html");
    } finally {
      navSpy.mockRestore();
    }

    expect(mockApi.practiceLoad).toHaveBeenCalled();
    expect($("screen-ex").hidden).toBe(false);
    expect($("ex-chapter-badge").textContent).toBe("Chapitre_8");
  });

  it("quitter une série (bouton Quitter) empêche la reprise silencieuse au prochain clic générique, même onglet", async () => {
    seedStaleSeries("Chapitre_8");
    sessionStorage.setItem(TAB_ACTIVE_KEY, "1");
    await mountExercice("/exercice.html");
    // Ce montage a repris automatiquement (F5-like) : confirme le point de départ.
    expect($("screen-ex").hidden).toBe(false);

    await withMockedLocation(async () => {
      $("btn-quit-series").click(); // confirmBeforeLeave par défaut true : ouvre d'abord la modale de confirmation
      $("btn-quit-confirm").click();
      await flushPromises();
    });

    // Un nouveau montage (clic générique "Entraînement" depuis le dashboard,
    // même onglet donc même sessionStorage) ne doit plus reprendre : le
    // marqueur a été nettoyé par quitSeries().
    expect(sessionStorage.getItem(TAB_ACTIVE_KEY)).toBe(null);
    mockApi.practiceLoad.mockClear();
    await mountExercice("/exercice.html");
    expect($("empty-state").hidden).toBe(false);
    expect($("screen-ex").hidden).toBe(true);
    expect(mockApi.practiceLoad).not.toHaveBeenCalled();
  });
});
