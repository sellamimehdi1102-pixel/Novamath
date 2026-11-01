// ── exercice.js : séries adaptatives (séries par notion, Révisions, Objectif
// du jour) — l'exercice suivant est choisi après chaque réponse selon le
// niveau de l'élève sur la notion (voir adaptiveDifficulty.js). ────────────
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
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

// Banque synthétique : chaque notion a ses exercices par niveau de difficulté.
const BANK = {};
function addExercises(notion, difficulty, firstId, count = 6) {
  const ids = [];
  for (let i = 0; i < count; i++) {
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
// « Dérivées » : niveaux 1 à 5. « Tangente » : niveau 1 seulement.
// « Trou » : niveaux 1 et 4 (niveaux manquants). « Primitives » et « Intégrales »
// : niveaux 1 à 3 (estimation du départ d'une notion nouvelle).
const D = [1, 2, 3, 4, 5].map((d, i) => addExercises("Dérivées", d, 100 + i * 10));
const DERIVEES = D.flat();
const T1 = addExercises("Tangente", 1, 400);
const TROU = [...addExercises("Trou", 1, 500, 3), ...addExercises("Trou", 4, 510, 3)];
const PRIM = [1, 2, 3].flatMap((d, i) => addExercises("Primitives", d, 600 + i * 10, 3));
const INTEG = [1, 2, 3].flatMap((d, i) => addExercises("Intégrales", d, 700 + i * 10, 3));

const detail = (notion, ids) => ({
  notion,
  exercise_ids: ids,
  exercise_difficulties: ids.map((id) => BANK[id].difficulty),
});
const CHAPTERS_META = [
  {
    id: "Chapitre_8",
    title: "Dérivation",
    notions_detail: [
      detail("Dérivées", DERIVEES),
      detail("Tangente", T1),
      detail("Trou", TROU),
      detail("Primitives", PRIM),
      detail("Intégrales", INTEG),
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

const served = () => mockApi.practiceLoad.mock.calls.map((c) => BANK[c[0]].difficulty);
const seriesFor = (notion, ids) => ({
  mode: "notion",
  chapterId: "Chapitre_8",
  notion,
  notions: [notion],
  exerciseIds: ids,
});

async function answer(correct) {
  $(correct ? "ex-btn-yes" : "ex-btn-no").click();
  await flushPromises();
}
async function answers(list) {
  for (const ok of list) await answer(ok);
}

beforeEach(() => {
  localStorage.clear();
  sessionStorage.clear();
});
afterEach(() => mockApi.getStats.mockReset().mockResolvedValue({}));

describe("série par notion : calibration rapide puis adaptation continue", () => {
  it("élève performant : Fondamental, Avancé, Défi dès la 3e question, puis niveaux élevés", async () => {
    await mountExercice(seriesFor("Dérivées", DERIVEES));
    await answers([true, true, true, true, true]);
    expect(served().slice(0, 3)).toEqual([1, 3, 5]);
    expect(Math.min(...served().slice(2))).toBeGreaterThanOrEqual(4);
  });

  it("élève en difficulté : reste sur des questions accessibles", async () => {
    await mountExercice(seriesFor("Dérivées", DERIVEES));
    await answers([false, false, false, false]);
    expect(Math.max(...served())).toBeLessThanOrEqual(1);
  });

  it("la difficulté affichée est celle de la vraie question proposée", async () => {
    await mountExercice(seriesFor("Dérivées", DERIVEES));
    expect($("ex-difficulty-badge").textContent).toContain("Fondamental");
    await answer(true);
    expect(BANK[mockApi.practiceLoad.mock.calls[1][0]].difficulty).toBe(3);
    expect($("ex-difficulty-badge").textContent).toContain("Avancé");
    expect($("level-line").textContent).toContain("Avancé");
  });

  it("descente effective après des erreurs répétées", async () => {
    await mountExercice(seriesFor("Dérivées", DERIVEES));
    await answers([true, true, true, false, false, false]);
    const s = served();
    expect(s[s.length - 1]).toBeLessThan(Math.max(...s));
  });

  it("une erreur isolée ne fait pas descendre un élève confirmé", async () => {
    await mountExercice(seriesFor("Dérivées", DERIVEES));
    await answers([true, true, true, true, false]);
    expect(Math.min(...served().slice(-2))).toBeGreaterThanOrEqual(4);
  });

  it("adaptation après chaque réponse, sans attendre un groupe de 5", async () => {
    await mountExercice(seriesFor("Dérivées", DERIVEES));
    await answer(true);
    expect(served()).toEqual([1, 3]);
  });
});

describe("séries : taille, niveaux manquants, notion à un seul niveau", () => {
  it("le pool complet d'une notion ne rallonge pas la série (10 questions)", async () => {
    await mountExercice(seriesFor("Dérivées", DERIVEES.slice(0, 3)));
    expect($("series-count").textContent).toBe("Question 1/10");
    await answers(Array(10).fill(true));
    expect(mockApi.practiceLoad).toHaveBeenCalledTimes(10);
    expect($("screen-recap").hidden).toBe(false);
  });

  it("notion à niveaux manquants (1 et 4) : seules les difficultés existantes sont servies", async () => {
    await mountExercice(seriesFor("Trou", TROU));
    await answers([true, true, true]);
    expect(new Set(served())).toEqual(new Set([1, 4]));
    expect(served()[0]).toBe(1);
  });

  it("notion à un seul niveau : série raccourcie au nombre d'exercices réels, sans en inventer", async () => {
    await mountExercice(seriesFor("Tangente", T1));
    expect($("series-count").textContent).toBe("Question 1/6");
    await answers(Array(6).fill(true));
    expect(served()).toEqual([1, 1, 1, 1, 1, 1]);
    expect($("screen-recap").hidden).toBe(false);
  });

  it("niveau le plus haut épuisé : repli sur la difficulté la plus proche, sans répéter une question", async () => {
    await mountExercice(seriesFor("Dérivées", DERIVEES));
    await answers(Array(9).fill(true));
    const ids = mockApi.practiceLoad.mock.calls.map((c) => c[0]);
    expect(new Set(ids).size).toBe(ids.length);
    // Une fois les six questions de niveau 5 servies, repli sur le niveau le plus proche.
    expect(served()).toHaveLength(10);
    expect(served().filter((d) => d === 5)).toHaveLength(6);
    expect(served().slice(-2)).toEqual([4, 4]);
  });
});

describe("persistance, indépendance des notions et estimation", () => {
  const entry = (notion, difficulty, correct, ts) => ({
    id: ts,
    ts,
    date: "2026-10-01",
    chapter: "Chapitre_8",
    notion,
    difficulty,
    correct,
    class_level: "seconde",
  });
  const mastered = (notion, offset = 0) => [1, 2, 3, 3].map((d, i) => entry(notion, d, true, offset + i + 1));

  it("nouveau navigateur (historique local vide) : le niveau enregistré est retrouvé depuis le serveur", async () => {
    mockApi.getStats.mockResolvedValue({
      history: [1, 2, 3, 4].map((d, i) => entry("Dérivées", d, true, i + 1)),
    });
    await mountExercice(seriesFor("Dérivées", DERIVEES));
    expect(served()[0]).toBeGreaterThanOrEqual(4);
  });

  it("anciennes réponses sans difficulté : difficulté retrouvée par l'id de l'exercice (sans rien inventer)", async () => {
    const old = [D[0][0], D[2][0], D[4][0]].map((id, i) => ({
      id,
      ts: i + 1,
      date: "2026-10-01",
      chapter: "Chapitre_8",
      notion: "Dérivées",
      correct: true,
      class_level: "seconde",
    }));
    mockApi.getStats.mockResolvedValue({ history: old });
    await mountExercice(seriesFor("Dérivées", DERIVEES));
    expect(served()[0]).toBeGreaterThanOrEqual(4);
    // Entrées sans difficulté ni exercice connu : ignorées, jamais comptées.
    localStorage.clear();
    mockApi.getStats.mockResolvedValue({ history: old.map((h) => ({ ...h, id: 99999 + h.ts })) });
    await mountExercice(seriesFor("Dérivées", DERIVEES));
    expect(served()[0]).toBe(1);
  });

  it("exercice reclassé (5 -> 1) : l'ancienne réussite reste enregistrée mais ne prouve plus un niveau Défi", async () => {
    // Réponses enregistrées au niveau 5 sur des exercices aujourd'hui classés 1 (même id, chapitre, notion).
    const reclasses = D[0].slice(0, 3).map((id, i) => ({ ...entry("Dérivées", 5, true, i + 1), id }));
    mockApi.getStats.mockResolvedValue({ history: reclasses });
    await mountExercice(seriesFor("Dérivées", DERIVEES));
    const apresReclassement = served()[0];
    // Les réussites restent enregistrées telles quelles (difficulté d'origine).
    const { getState } = await import("../store.js");
    const stored = getState().history.filter((h) => reclasses.some((r) => r.id === h.id));
    expect(stored).toHaveLength(3);
    stored.forEach((h) => expect(h.difficulty).toBe(5));
    // Référence : les mêmes réussites enregistrées directement au niveau 1.
    localStorage.clear();
    mockApi.getStats.mockResolvedValue({ history: reclasses.map((h) => ({ ...h, difficulty: 1 })) });
    await mountExercice(seriesFor("Dérivées", DERIVEES));
    expect(apresReclassement).toBe(served()[0]);
    expect(apresReclassement).toBeLessThan(5);
    // Sans le reclassement, ces réussites Défi enverraient l'élève en Difficile ou Défi.
    localStorage.clear();
    mockApi.getStats.mockResolvedValue({ history: reclasses.map((h, i) => ({ ...h, id: 90000 + i })) });
    await mountExercice(seriesFor("Dérivées", DERIVEES));
    expect(served()[0]).toBeGreaterThanOrEqual(4);
  });

  it("identification incertaine (exercice d'une autre notion) : la difficulté enregistrée est conservée", async () => {
    // Ids d'exercices « Primitives » de niveau 1, enregistrés sous « Dérivées » au niveau 5 : pas de réinterprétation.
    const incertains = PRIM.slice(0, 3).map((id, i) => ({ ...entry("Dérivées", 5, true, i + 1), id }));
    mockApi.getStats.mockResolvedValue({ history: incertains });
    await mountExercice(seriesFor("Dérivées", DERIVEES));
    expect(served()[0]).toBeGreaterThanOrEqual(4);
  });

  it("la descente enregistrée est elle aussi retrouvée (pas de nouvelle calibration)", async () => {
    mockApi.getStats.mockResolvedValue({
      history: [
        ...[1, 2, 3, 4].map((d, i) => entry("Dérivées", d, true, i + 1)),
        entry("Dérivées", 4, false, 5),
        entry("Dérivées", 4, false, 6),
        entry("Dérivées", 4, false, 7),
      ],
    });
    await mountExercice(seriesFor("Dérivées", DERIVEES));
    const afterErrors = served()[0];
    localStorage.clear();
    sessionStorage.clear();
    mockApi.getStats.mockResolvedValue({ history: [1, 2, 3, 4].map((d, i) => entry("Dérivées", d, true, i + 1)) });
    await mountExercice(seriesFor("Dérivées", DERIVEES));
    expect(afterErrors).toBeLessThan(served()[0]);
  });

  it("le niveau d'une notion ne dépend pas des autres une fois travaillée", async () => {
    mockApi.getStats.mockResolvedValue({ history: mastered("Primitives") });
    await mountExercice(seriesFor("Tangente", T1));
    expect(served()[0]).toBe(1);
  });

  it("notion nouvelle : départ prudent (faible profil général) depuis des résultats solides sur d'autres notions", async () => {
    mockApi.getStats.mockResolvedValue({ history: [...mastered("Primitives"), ...mastered("Dérivées", 10)] });
    await mountExercice(seriesFor("Intégrales", INTEG));
    expect(served()[0]).toBeGreaterThan(1);
    expect(served()[0]).toBeLessThanOrEqual(3);
  });

  it("notion nouvelle, une seule notion maîtrisée : données insuffisantes, départ en Fondamental", async () => {
    mockApi.getStats.mockResolvedValue({ history: mastered("Primitives") });
    await mountExercice(seriesFor("Intégrales", INTEG));
    expect(served()[0]).toBe(1);
  });

  it("série lancée depuis un cours ou l'assistant (3 exercices transmis) : tous les niveaux restent atteignables", async () => {
    await mountExercice(seriesFor("Dérivées", D[0].slice(0, 3)));
    await answers([true, true, true]);
    expect(served().slice(0, 3)).toEqual([1, 3, 5]);
  });
});

describe("Révisions et Objectif du jour", () => {
  it("Révisions : construit la série à partir des notions déjà travaillées uniquement, au niveau enregistré", async () => {
    await mountExercice(seriesFor("Tangente", T1));
    await answer(false);
    document.querySelector('.mode-pill[data-mode="revisions"]').click();
    await flushPromises();
    const lastId = mockApi.practiceLoad.mock.calls.at(-1)[0];
    expect(BANK[lastId].notion).toBe("Tangente");
    expect($("screen-ex").hidden).toBe(false);
  });

  it("Révisions sans aucune notion travaillée : message d'accompagnement", async () => {
    await mountExercice(null);
    document.querySelector('.mode-pill[data-mode="revisions"]').click();
    await flushPromises();
    expect($("empty-state").hidden).toBe(false);
    expect($("empty-state").textContent).toContain("Commence par une notion");
  });

  it("Objectif du jour : la série couvre les exercices restants pour atteindre l'objectif quotidien", async () => {
    await mountExercice(seriesFor("Tangente", T1));
    await answer(true);
    document.querySelector('.mode-pill[data-mode="objectif"]').click();
    await flushPromises();
    expect($("series-count").textContent).toBe("Question 1/3");
  });
});

describe("modes non adaptatifs inchangés", () => {
  it("« Recommencer » une série passée (sans liste de notions) rejoue exactement ses exercices", async () => {
    await mountExercice({ mode: "notion", chapterId: "Chapitre_8", notion: "Dérivées", exerciseIds: [D[2][0]] });
    expect(mockApi.practiceLoad.mock.calls[0][0]).toBe(D[2][0]);
  });
});
