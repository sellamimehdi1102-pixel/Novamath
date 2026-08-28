// ── exercice.js : QuotaType.EXERCISES_DAILY (Chantier "Limitation des
// exercices par abonnement", 2026-08-26) ────────────────────────────────────
// Couvre : affichage du nombre d'exercices restants (GET /api/quota, jamais
// recalculé côté client), affichage "illimité" pour Ultra, gestion propre
// d'un 429 (POST /api/practice/load) sans casser la série ni afficher une
// erreur technique brute, et absence de double-consommation lors d'une
// reprise de série sans nouvel appel réseau (voir persistProgress/
// resumeSeries dans exercice.js).
import { describe, it, expect, vi, beforeEach } from "vitest";
import { loadPageBody, flushPromises } from "./testUtils.js";

// `store.js` (non mocké) lit/écrit toujours dans localStorage — importer
// dynamiquement ici (plutôt qu'un `import` statique en tête de fichier) évite
// le piège de hoisting de vi.mock (le factory de vi.mock("../api.js", ...)
// référence `mockApi`, déclaré plus bas avec `const` : un import statique de
// store.js forcerait sa résolution AVANT cette déclaration).
async function getGamificationState() {
  const { getState } = await import("../store.js");
  return getState();
}

const mockApi = {
  practiceLoad: vi.fn(),
  practiceResult: vi.fn(),
  getQuota: vi.fn(),
  saveStats: vi.fn().mockResolvedValue({}),
  getStats: vi.fn().mockResolvedValue({}),
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

function exerciseFixture(id = "ex1") {
  return { id, chapter_id: "Chapitre_8", notion: "Dérivées", difficulty: 2, enonce: "Question ?", hint: "", answer: "", solution_steps: [] };
}

function quotaExceededError(limit = 20) {
  const err = new Error("quota dépassé");
  err.status = 429;
  err.isQuotaExceeded = true;
  err.quota = "exercises_daily";
  err.remaining = 0;
  err.limit = limit;
  err.requiredPlan = "premium";
  return err;
}

// `getQuota` n'est PAS réinitialisé/pré-configuré ici (contrairement à
// practiceLoad/practiceResult) : chaque test doit configurer sa propre
// réponse AVANT d'appeler mountExercice(), car init() l'appelle dès l'import
// du module — un reset après coup écraserait silencieusement la config du
// test (utiliser mountExerciceWithDefaultQuota() pour le cas standard).
async function mountExercice(url = "/exercice.html") {
  window.history.pushState({}, "", url);
  document.body.innerHTML = loadPageBody("exercice.html");
  mockApi.practiceLoad.mockReset();
  mockApi.practiceResult.mockReset();
  vi.resetModules();
  await import("../exercice.js");
  await flushPromises();
}

async function mountExerciceWithDefaultQuota(url = "/exercice.html") {
  mockApi.getQuota.mockReset();
  mockApi.getQuota.mockResolvedValue({
    exercises_daily: { used: 3, remaining: 17, limit: 20, unlimited: false },
  });
  await mountExercice(url);
}

describe("exercice.js — indicateur de quota d'exercices", () => {
  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
  });

  it("affiche le nombre d'exercices restants au chargement de la page", async () => {
    await mountExerciceWithDefaultQuota();
    expect(mockApi.getQuota).toHaveBeenCalled();
    expect($("exercises-quota-indicator").hidden).toBe(false);
    expect($("exercises-quota-value").textContent).toBe("17 exercices restants aujourd'hui");
  });

  it("affiche 'Exercices illimités' pour un plan Ultra (unlimited: true)", async () => {
    mockApi.getQuota.mockReset();
    mockApi.getQuota.mockResolvedValue({
      exercises_daily: { used: 12, remaining: null, limit: null, unlimited: true },
    });
    await mountExercice();
    expect($("exercises-quota-value").textContent).toBe("Exercices illimités");
    expect($("exercises-quota-indicator").classList.contains("is-unlimited")).toBe(true);
  });

  it("ne recalcule jamais la limite côté client : affiche exactement ce que renvoie le backend", async () => {
    mockApi.getQuota.mockReset();
    mockApi.getQuota.mockResolvedValue({
      exercises_daily: { used: 58, remaining: 2, limit: 60, unlimited: false },
    });
    await mountExercice();
    expect($("exercises-quota-value").textContent).toBe("2 exercices restants aujourd'hui");
  });
});

// buildSeriesPool() (mode "revisions" par défaut) lit lumis:practice_choices
// pour construire le pool d'ids disponibles — sans lui, la série ne démarre
// jamais (empty-state immédiat, aucun appel réseau). Format accepté par
// pool() : tableau brut de {id}.
function seedPracticeChoices(ids) {
  localStorage.setItem("lumis:practice_choices", JSON.stringify(ids.map((id) => ({ id }))));
}

describe("exercice.js — gestion du HTTP 429 (quota épuisé)", () => {
  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
  });

  it("arrête proprement le chargement, affiche un message clair, ne plante pas", async () => {
    seedPracticeChoices(["ex1", "ex2", "ex3"]);
    mockApi.practiceLoad.mockRejectedValue(quotaExceededError(20));
    document.body.innerHTML = loadPageBody("exercice.html");
    mockApi.getQuota.mockResolvedValue({ exercises_daily: { used: 20, remaining: 0, limit: 20, unlimited: false } });
    vi.resetModules();
    await import("../exercice.js");
    await flushPromises();

    $("btn-next-ex").click();
    await flushPromises();

    expect($("screen-ex").hidden).toBe(true);
    expect($("empty-state").hidden).toBe(false);
    expect($("empty-state").querySelector("p").textContent).toBe(
      "Tu as atteint ta limite de 20 exercices aujourd'hui. Elle sera réinitialisée demain.",
    );
    // Aucune erreur technique brute (message JS, stack, JSON) affichée.
    expect($("empty-state").querySelector("p").textContent).not.toMatch(/error|Error|undefined|\[object/);
  });

  it("une série avec seulement 3 exercices restants charge les 3, puis bloque proprement au 4e", async () => {
    // Pool volontairement plus grand que le quota restant (3) : buildSeriesPool()
    // shuffle l'ordre des ids et répète si besoin pour atteindre SERIES_TOTAL
    // (10 par défaut) — le test ne dépend donc d'aucun id ni d'aucun ordre
    // précis, uniquement du RANG de l'appel (les 3 premiers réussissent, le
    // 4e est refusé), exactement ce que le backend garantit réellement.
    seedPracticeChoices(["ex1", "ex2", "ex3"]);
    document.body.innerHTML = loadPageBody("exercice.html");
    mockApi.getQuota.mockReset();
    mockApi.getQuota.mockResolvedValue({ exercises_daily: { used: 17, remaining: 3, limit: 20, unlimited: false } });
    mockApi.practiceLoad.mockReset();
    let calls = 0;
    mockApi.practiceLoad.mockImplementation(async (id) => {
      calls += 1;
      if (calls > 3) throw quotaExceededError(20);
      return { exercise: exerciseFixture(id) };
    });
    mockApi.practiceResult.mockResolvedValue({
      level: 1, level_icon: "🌱", level_label: "Débutant", level_updated: false, history: [], practice_choices: [],
    });
    vi.resetModules();
    await import("../exercice.js");
    await flushPromises();

    $("btn-next-ex").click();
    await flushPromises();
    expect($("screen-ex").hidden).toBe(false); // exercice 1 chargé

    $("ex-btn-yes").click(); // réponse -> exercice 2
    await flushPromises();
    expect($("screen-ex").hidden).toBe(false);

    $("ex-btn-yes").click(); // réponse -> exercice 3
    await flushPromises();
    expect($("screen-ex").hidden).toBe(false);

    $("ex-btn-yes").click(); // réponse -> tentative exercice 4 : 429
    await flushPromises();

    expect(mockApi.practiceLoad).toHaveBeenCalledTimes(4);
    expect($("screen-ex").hidden).toBe(true);
    expect($("empty-state").hidden).toBe(false);
    expect($("empty-state").querySelector("p").textContent).toContain("limite de 20 exercices");
  });
});

describe("exercice.js — absence de double-consommation lors d'une reprise", () => {
  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
  });

  function seedInProgressWithCachedExercise() {
    localStorage.setItem(IN_PROGRESS_KEY, JSON.stringify({
      mode: "revisions",
      seriesConfig: { chapterId: "Chapitre_8", notion: null },
      seriesQueue: ["ex1", "ex2", "ex3"],
      seriesIndex: 0,
      draftId: "draft-1",
      draftStartedAt: Date.now() - 60_000,
      startDate: new Date().toISOString().slice(0, 10),
      draftQuestions: [],
      total: 3,
      score: 0,
      wrong: 0,
      progressPct: 0,
      currentExercise: exerciseFixture("ex1"),
      class_level: "seconde",
      savedAt: Date.now() - 60_000,
    }));
  }

  it("F5 en cours de série (exercice déjà chargé et persisté) : ne rappelle PAS /api/practice/load", async () => {
    seedInProgressWithCachedExercise();
    sessionStorage.setItem(TAB_ACTIVE_KEY, "1"); // F5 dans le même onglet
    document.body.innerHTML = loadPageBody("exercice.html");
    mockApi.getQuota.mockResolvedValue({ exercises_daily: { used: 1, remaining: 19, limit: 20, unlimited: false } });
    mockApi.practiceLoad.mockReset();
    vi.resetModules();
    await import("../exercice.js");
    await flushPromises();

    expect(mockApi.practiceLoad).not.toHaveBeenCalled();
    expect($("screen-ex").hidden).toBe(false);
    expect($("ex-chapter-badge").textContent).toBe("Chapitre_8");
  });

  it("reprise avec un exercice persisté qui ne correspond plus à seriesQueue[seriesIndex] : retombe sur un vrai appel réseau", async () => {
    localStorage.setItem(IN_PROGRESS_KEY, JSON.stringify({
      mode: "revisions",
      seriesConfig: { chapterId: "Chapitre_8", notion: null },
      seriesQueue: ["ex1", "ex2", "ex3"],
      seriesIndex: 1, // pointe sur ex2, mais currentExercise ci-dessous est ex1 (désynchronisé)
      draftId: "draft-1",
      draftStartedAt: Date.now() - 60_000,
      startDate: new Date().toISOString().slice(0, 10),
      draftQuestions: [{ exercise_id: "ex1", chapter: "Chapitre_8", correct: true }],
      total: 3,
      score: 1,
      wrong: 0,
      progressPct: 33,
      currentExercise: exerciseFixture("ex1"),
      class_level: "seconde",
      savedAt: Date.now() - 60_000,
    }));
    sessionStorage.setItem(TAB_ACTIVE_KEY, "1");
    document.body.innerHTML = loadPageBody("exercice.html");
    mockApi.getQuota.mockResolvedValue({ exercises_daily: { used: 1, remaining: 19, limit: 20, unlimited: false } });
    mockApi.practiceLoad.mockReset();
    mockApi.practiceLoad.mockResolvedValue({ exercise: exerciseFixture("ex2") });
    vi.resetModules();
    await import("../exercice.js");
    await flushPromises();

    expect(mockApi.practiceLoad).toHaveBeenCalledTimes(1);
    expect($("ex-chapter-badge").textContent).toBe("Chapitre_8");
  });
});

// ── Verrou anti double-clic (chantier "Correction du risque de double-
// consommation des exercices") ──────────────────────────────────────────────
describe("exercice.js — verrou anti double-clic (exerciseActionInFlight)", () => {
  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
  });

  // TEST 1 — double-clic sur "Démarrer la série"
  it("double-clic sur 'Démarrer la série' : un seul practiceLoad, une seule série créée", async () => {
    seedPracticeChoices(["ex1", "ex2", "ex3"]);
    document.body.innerHTML = loadPageBody("exercice.html");
    mockApi.getQuota.mockResolvedValue({ exercises_daily: { used: 0, remaining: 20, limit: 20, unlimited: false } });
    mockApi.practiceLoad.mockReset();
    mockApi.practiceLoad.mockResolvedValue({ exercise: exerciseFixture("ex1") });
    vi.resetModules();
    await import("../exercice.js");
    await flushPromises();

    // Deux clics synchrones, avant toute résolution réseau — reproduit
    // exactement le scénario de l'audit (deux invocations de startSeries()
    // avant le premier `await`).
    $("btn-next-ex").click();
    $("btn-next-ex").click();
    await flushPromises();

    expect(mockApi.practiceLoad).toHaveBeenCalledTimes(1);
    expect($("screen-ex").hidden).toBe(false);
    expect($("ex-chapter-badge").textContent).toBe("Chapitre_8");
    // Le verrou est bien libéré une fois le flux terminé.
    expect($("btn-next-ex").disabled).toBe(false);
  });

  it("double-clic rapide sur deux mode-pills différents : un seul practiceLoad (même verrou que 'Démarrer la série')", async () => {
    seedPracticeChoices(["ex1", "ex2", "ex3"]);
    document.body.innerHTML = loadPageBody("exercice.html");
    mockApi.getQuota.mockResolvedValue({ exercises_daily: { used: 0, remaining: 20, limit: 20, unlimited: false } });
    mockApi.practiceLoad.mockReset();
    mockApi.practiceLoad.mockResolvedValue({ exercise: exerciseFixture("ex1") });
    vi.resetModules();
    await import("../exercice.js");
    await flushPromises();

    const pills = document.querySelectorAll(".mode-pill");
    pills[0].click();
    pills[1].click();
    await flushPromises();

    expect(mockApi.practiceLoad).toHaveBeenCalledTimes(1);
  });

  // TEST 2 — double-clic sur "Réussi" (et "Échoué", même handleVerdict())
  it("double-clic sur 'Réussi' : une seule soumission, un seul passage à l'exercice suivant, aucune duplication d'historique/XP", async () => {
    seedPracticeChoices(["ex1", "ex2", "ex3"]);
    document.body.innerHTML = loadPageBody("exercice.html");
    mockApi.getQuota.mockResolvedValue({ exercises_daily: { used: 0, remaining: 20, limit: 20, unlimited: false } });
    mockApi.practiceLoad.mockReset();
    mockApi.practiceLoad
      .mockResolvedValueOnce({ exercise: exerciseFixture("ex1") })
      .mockResolvedValue({ exercise: exerciseFixture("ex2") });
    mockApi.practiceResult.mockReset();
    mockApi.practiceResult.mockResolvedValue({
      level: 1, level_icon: "🌱", level_label: "Débutant", level_updated: false, history: [], practice_choices: [],
    });
    vi.resetModules();
    await import("../exercice.js");
    await flushPromises();

    $("btn-next-ex").click();
    await flushPromises();
    expect($("screen-ex").hidden).toBe(false);

    const before = await getGamificationState();
    const historyBefore = before.history.length;
    const xpBefore = before.xp;

    // Double-clic synchrone sur "Réussi", avant que practiceResult n'ait résolu.
    $("ex-btn-yes").click();
    $("ex-btn-yes").click();
    await flushPromises();

    // 1 seule soumission de résultat, 1 seul chargement de l'exercice suivant
    // (2 appels practiceLoad au total : le chargement initial + celui-ci).
    expect(mockApi.practiceResult).toHaveBeenCalledTimes(1);
    expect(mockApi.practiceLoad).toHaveBeenCalledTimes(2);
    // Un seul point d'historique / une seule augmentation d'XP ajoutés, jamais deux.
    const after = await getGamificationState();
    expect(after.history.length).toBe(historyBefore + 1);
    expect(after.xp).toBeGreaterThan(xpBefore);
    // Le verrou est libéré à la fin du flux.
    expect($("ex-btn-yes").disabled).toBe(false);
  });

  // "Échoué" utilise exactement le même handleVerdict() qu'"Réussi" (seul le
  // booléen isCorrect diffère, voir exercice.js) — même verrou, même garantie,
  // revérifié explicitement par prudence plutôt que supposé identique.
  it("double-clic sur 'Échoué' : même garantie (un seul practiceResult, une seule avancée)", async () => {
    seedPracticeChoices(["ex1", "ex2", "ex3"]);
    document.body.innerHTML = loadPageBody("exercice.html");
    mockApi.getQuota.mockResolvedValue({ exercises_daily: { used: 0, remaining: 20, limit: 20, unlimited: false } });
    mockApi.practiceLoad.mockReset();
    mockApi.practiceLoad
      .mockResolvedValueOnce({ exercise: exerciseFixture("ex1") })
      .mockResolvedValue({ exercise: exerciseFixture("ex2") });
    mockApi.practiceResult.mockReset();
    mockApi.practiceResult.mockResolvedValue({
      level: 1, level_icon: "🌱", level_label: "Débutant", level_updated: false, history: [], practice_choices: [],
    });
    vi.resetModules();
    await import("../exercice.js");
    await flushPromises();

    $("btn-next-ex").click();
    await flushPromises();

    const historyBefore = (await getGamificationState()).history.length;

    $("ex-btn-no").click();
    $("ex-btn-no").click();
    await flushPromises();

    expect(mockApi.practiceResult).toHaveBeenCalledTimes(1);
    expect(mockApi.practiceLoad).toHaveBeenCalledTimes(2);
    expect((await getGamificationState()).history.length).toBe(historyBefore + 1);
  });

  // TEST 3 — erreur réseau : le verrou ne doit jamais rester bloqué
  it("erreur réseau sur practiceLoad : le verrou est libéré, aucun bouton ne reste disabled, un nouvel essai fonctionne", async () => {
    seedPracticeChoices(["ex1", "ex2", "ex3"]);
    document.body.innerHTML = loadPageBody("exercice.html");
    mockApi.getQuota.mockResolvedValue({ exercises_daily: { used: 0, remaining: 20, limit: 20, unlimited: false } });
    mockApi.practiceLoad.mockReset();
    mockApi.practiceLoad.mockRejectedValueOnce(new Error("network fail"));
    vi.resetModules();
    await import("../exercice.js");
    await flushPromises();

    // L'échec réseau remonte comme un rejet non intercepté par le handler de
    // clic (comportement pré-existant, hors périmètre de ce chantier) — on
    // l'avale ici pour ne tester QUE l'état du verrou/des boutons après coup.
    const swallow = () => {};
    process.on("unhandledRejection", swallow);
    try {
      $("btn-next-ex").click();
      await flushPromises();
    } finally {
      process.off("unhandledRejection", swallow);
    }

    // Le verrou a bien été libéré (finally) malgré l'échec.
    expect($("btn-next-ex").disabled).toBe(false);
    document.querySelectorAll(".mode-pill").forEach((b) => expect(b.disabled).toBe(false));

    // Un nouvel essai (l'utilisateur retente) fonctionne normalement.
    mockApi.practiceLoad.mockResolvedValueOnce({ exercise: exerciseFixture("ex1") });
    $("btn-next-ex").click();
    await flushPromises();

    expect(mockApi.practiceLoad).toHaveBeenCalledTimes(2);
    expect($("screen-ex").hidden).toBe(false);
  });

  // TEST 4 — 429 quota : le verrou doit être libéré comme n'importe quel autre échec
  it("429 quota : le verrou est libéré, le message quota existant est conservé, la série s'arrête proprement", async () => {
    seedPracticeChoices(["ex1"]);
    document.body.innerHTML = loadPageBody("exercice.html");
    mockApi.getQuota.mockResolvedValue({ exercises_daily: { used: 20, remaining: 0, limit: 20, unlimited: false } });
    mockApi.practiceLoad.mockReset();
    const quotaErr = new Error("quota dépassé");
    quotaErr.isQuotaExceeded = true;
    quotaErr.quota = "exercises_daily";
    quotaErr.limit = 20;
    mockApi.practiceLoad.mockRejectedValue(quotaErr);
    vi.resetModules();
    await import("../exercice.js");
    await flushPromises();

    $("btn-next-ex").click();
    await flushPromises();

    expect($("empty-state").querySelector("p").textContent).toBe(
      "Tu as atteint ta limite de 20 exercices aujourd'hui. Elle sera réinitialisée demain.",
    );
    // Verrou libéré : les boutons ne restent pas bloqués après un 429.
    expect($("btn-next-ex").disabled).toBe(false);
    // Un nouveau clic (l'élève retente) déclenche bien une nouvelle tentative
    // — preuve supplémentaire que le verrou n'est pas resté figé à true.
    mockApi.practiceLoad.mockReset();
    mockApi.practiceLoad.mockResolvedValueOnce({ exercise: exerciseFixture("ex1") });
    $("btn-next-ex").click();
    await flushPromises();
    expect(mockApi.practiceLoad).toHaveBeenCalledTimes(1);
  });

  // TEST 5 — la reprise (F5/back-forward/?resume=1) continue de fonctionner
  // avec le verrou en place : déjà couvert intégralement par le describe
  // "absence de double-consommation lors d'une reprise" ci-dessus (F5 avec
  // cache valide → 0 appel réseau ; cache désynchronisé → exactement 1 appel)
  // et par exercice-resume.test.js (F5/back_forward/navigate/?resume=1) —
  // aucun de ces tests n'a été modifié par l'ajout du verrou et tous
  // continuent de passer (voir résultats joints au rapport), ce qui prouve
  // que resumeSeries() reste fonctionnelle sous le même verrou partagé.
});
