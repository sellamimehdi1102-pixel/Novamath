// ── exercice.js : séries adaptatives (séries par notion, Révisions, Objectif
// du jour) — l'exercice suivant est choisi après chaque réponse selon le
// niveau de l'élève sur la notion (voir adaptiveDifficulty.js). ────────────
import { describe, it, expect, vi, beforeEach } from "vitest";
import { loadPageBody, flushPromises } from "./testUtils.js";

const mockApi = {
  practiceLoad: vi.fn(),
  practiceResult: vi.fn().mockResolvedValue({}),
  getQuota: vi.fn().mockResolvedValue({ exercises_daily: { used: 0, remaining: 50, limit: 50, unlimited: false } }),
  saveStats: vi.fn().mockResolvedValue({}),
  getStats: vi.fn().mockResolvedValue({}),
  chapters: vi.fn(),
};
vi.mock("../api.js", () => ({ api: mockApi }));
vi.mock("../settingsManager.js", () => ({
  initSettingsManager: () => Promise.resolve(),
  getSettings: () => ({ training: { questionsPerSeries: 10 }, learning: { dailyGoalExercises: 4 } }),
  onSettingsChange: vi.fn(),
}));
vi.mock("../settingsPopup.js", () => ({ bindSettingsButton: vi.fn() }));
vi.mock("../i18n.js", () => ({ bindLiveTranslations: vi.fn() }));
vi.mock("../mathrender.js", () => ({
  setMathContent: (el, text) => {
    el.textContent = text;
  },
  formatStepLabels: (s) => s,
}));
vi.mock("../animations.js", () => ({ fireConfetti: vi.fn(), shakeElement: vi.fn(), fadeInTransition: vi.fn() }));
vi.mock("../supportTicket.js", () => ({ openReportTicketPopup: vi.fn() }));

const $ = (id) => document.getElementById(id);

// Notion « Dérivées » : 6 exercices par niveau de difficulté 1, 2 et 3.
// Notion « Tangente » : 6 exercices de difficulté 1.
const BANK = {};
function addExercises(notion, difficulty, firstId) {
  const ids = [];
  for (let i = 0; i < 6; i++) {
    const id = firstId + i;
    BANK[id] = {
      id,
      chapter_id: "Chapitre_8",
      notion,
      difficulty,
      enonce: `${notion} d${difficulty} #${id}`,
      hint: "",
      answer: "",
      solution_steps: [],
    };
    ids.push(id);
  }
  return ids;
}
const D1 = addExercises("Dérivées", 1, 100);
const D2 = addExercises("Dérivées", 2, 200);
const D3 = addExercises("Dérivées", 3, 300);
const T1 = addExercises("Tangente", 1, 400);
const DERIVEES = [...D1, ...D2, ...D3];

const CHAPTERS_META = [
  {
    id: "Chapitre_8",
    title: "Dérivation",
    notions_detail: [
      { notion: "Dérivées", exercise_ids: DERIVEES, exercise_difficulties: DERIVEES.map((id) => BANK[id].difficulty) },
      { notion: "Tangente", exercise_ids: T1, exercise_difficulties: T1.map(() => 1) },
    ],
  },
];

async function mountExercice(pending) {
  if (pending) localStorage.setItem("lumis:pending_series", JSON.stringify(pending));
  window.history.pushState({}, "", "/exercice.html");
  document.body.innerHTML = loadPageBody("exercice.html");
  mockApi.practiceLoad.mockReset();
  mockApi.practiceLoad.mockImplementation((id) => Promise.resolve({ exercise: BANK[id] }));
  mockApi.chapters.mockReset();
  mockApi.chapters.mockResolvedValue({ chapters_meta: CHAPTERS_META });
  vi.resetModules();
  await import("../exercice.js");
  await flushPromises();
}

const loadedDifficulty = (call) => BANK[mockApi.practiceLoad.mock.calls[call][0]].difficulty;

async function answer(correct) {
  $(correct ? "ex-btn-yes" : "ex-btn-no").click();
  await flushPromises();
}

beforeEach(() => {
  localStorage.clear();
  sessionStorage.clear();
});

describe("série par notion adaptative", () => {
  const pending = {
    mode: "notion",
    chapterId: "Chapitre_8",
    notion: "Dérivées",
    notions: ["Dérivées"],
    exerciseIds: DERIVEES,
  };

  it("commence au niveau le plus bas, puis monte après 4 ou 5 réussites sur 5", async () => {
    await mountExercice(pending);
    expect(loadedDifficulty(0)).toBe(1);
    for (let i = 0; i < 5; i++) await answer(true);
    expect([0, 1, 2, 3, 4].map(loadedDifficulty)).toEqual([1, 1, 1, 1, 1]);
    expect(loadedDifficulty(5)).toBe(2);
    // La ligne de niveau décrit l'exercice affiché (difficulté 2 = Intermédiaire).
    expect($("level-line").textContent).toContain("Dérivées");
    expect($("level-line").textContent).toContain("Intermédiaire");
  });

  it("reste au même niveau avec 3 réussites sur 5", async () => {
    await mountExercice(pending);
    for (const ok of [true, true, true, false, false]) await answer(ok);
    expect(loadedDifficulty(5)).toBe(1);
  });

  it("redescend après 2 réussites ou moins sur 5", async () => {
    await mountExercice(pending);
    for (let i = 0; i < 5; i++) await answer(true);
    for (const ok of [true, false, false, true, false]) await answer(ok);
    expect(loadedDifficulty(5)).toBe(2);
    expect(loadedDifficulty(9)).toBe(2);
    // 10 questions répondues : la série (10 questions) est terminée.
    expect($("screen-recap").hidden).toBe(false);
    // Nouvelle série sur la même notion : le niveau tient compte de tout
    // l'historique (5/5 puis 2/5) et repart donc du niveau 1.
    await mountExercice(pending);
    expect(loadedDifficulty(0)).toBe(1);
  });

  it("ne sert jamais deux fois le même exercice dans la série", async () => {
    await mountExercice(pending);
    for (let i = 0; i < 9; i++) await answer(i % 2 === 0);
    const ids = mockApi.practiceLoad.mock.calls.map((c) => c[0]);
    expect(new Set(ids).size).toBe(ids.length);
  });
});

describe("Révisions et Objectif du jour", () => {
  it("Révisions : construit la série à partir des notions déjà travaillées uniquement", async () => {
    await mountExercice({
      mode: "notion",
      chapterId: "Chapitre_8",
      notion: "Tangente",
      notions: ["Tangente"],
      exerciseIds: T1,
    });
    await answer(false);
    document.querySelector('.mode-pill[data-mode="revisions"]').click();
    await flushPromises();
    const lastId = mockApi.practiceLoad.mock.calls.at(-1)[0];
    expect(BANK[lastId].notion).toBe("Tangente");
    expect($("screen-ex").hidden).toBe(false);
  });

  it("Révisions sans aucune notion travaillée : message d'accompagnement (plus d'« évaluation initiale »)", async () => {
    await mountExercice(null);
    document.querySelector('.mode-pill[data-mode="revisions"]').click();
    await flushPromises();
    expect($("empty-state").hidden).toBe(false);
    expect($("empty-state").textContent).toContain("Commence par une notion");
    expect($("empty-state").textContent).not.toContain("évaluation initiale");
  });

  it("Objectif du jour : la série couvre les exercices restants pour atteindre l'objectif quotidien", async () => {
    await mountExercice({
      mode: "notion",
      chapterId: "Chapitre_8",
      notion: "Tangente",
      notions: ["Tangente"],
      exerciseIds: T1,
    });
    await answer(true);
    document.querySelector('.mode-pill[data-mode="objectif"]').click();
    await flushPromises();
    // Objectif quotidien : 4 exercices, 1 déjà fait aujourd'hui.
    expect($("series-count").textContent).toBe("Question 1/3");
  });
});

describe("modes non adaptatifs inchangés", () => {
  it("« Recommencer » une série passée (sans liste de notions) rejoue exactement ses exercices", async () => {
    await mountExercice({ mode: "notion", chapterId: "Chapitre_8", notion: "Dérivées", exerciseIds: [D3[0]] });
    expect(mockApi.practiceLoad.mock.calls[0][0]).toBe(D3[0]);
  });
});
