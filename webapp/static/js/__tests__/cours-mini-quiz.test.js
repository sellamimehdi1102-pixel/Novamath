// ── cours.js : chargement robuste du mini-quiz (correction "mini-quiz
// défectueux", 2026-10-24). Avant : Promise.all — un seul exercice absent
// (404) faisait disparaître TOUT le quiz et la leçon était marquée terminée
// automatiquement. Désormais : quiz joué avec les exercices disponibles,
// message explicite si aucun ne l'est, distinction absence / réseau,
// journalisation, et jamais de validation de leçon causée par un échec.
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { loadPageBody, flushPromises } from "./testUtils.js";

const mockApi = {
  me: vi.fn(),
  chapters: vi.fn(),
  getCourseProgress: vi.fn(),
  saveCourseProgress: vi.fn(),
  exercise: vi.fn(),
  getCourseContent: vi.fn(),
  exercisesByNotion: vi.fn(),
};
vi.mock("../api.js", () => ({ api: mockApi }));
vi.mock("../settingsManager.js", () => ({ initSettingsManager: () => Promise.resolve(), onSettingsChange: vi.fn() }));
vi.mock("../settingsPopup.js", () => ({ bindSettingsButton: vi.fn() }));
vi.mock("../i18n.js", () => ({ bindLiveTranslations: vi.fn() }));
vi.mock("../mathrender.js", () => ({
  setMathContent: (el, text) => {
    el.textContent = text;
  },
  setRenderedHtmlContent: (el, text) => {
    el.textContent = text;
  },
}));
vi.mock("../geomSvg.js", () => ({ renderFigure: vi.fn(() => "<svg></svg>") }));
vi.mock("../curriculumSelector.js", () => ({
  getStoredClassLevel: () => "troisieme",
  fetchCurricula: () => Promise.resolve([{ classLevel: "troisieme", hasCourses: true }]),
}));
vi.mock("../animations.js", () => ({ fadeInTransition: vi.fn() }));
vi.mock("../chapterTitleByNotions.js", () => ({ resolveChapterTitle: (title) => title }));
vi.mock("../favorites.js", () => ({
  getFavoriteChapters: () => new Set(),
  toggleFavoriteChapter: vi.fn(),
  getFavoriteNotions: () => new Set(),
  toggleFavoriteNotion: vi.fn(),
  favoriteIconSvg: () => "",
}));
vi.mock("../searchUtils.js", () => ({
  normalizeText: (s) => (s || "").toLowerCase(),
  debounce: (fn) => fn,
}));
vi.mock("../supportTicket.js", () => ({ openReportTicketPopup: vi.fn() }));

const CHAPTER = { id: "Chapitre_1", title: "Nombres entiers", notions_cours: [], n_notions: 1, notions_detail: [] };
const BASE_NOTION = {
  id: "criteres-de-divisibilite",
  title: "Critères de divisibilité",
  schemaVersion: 2,
  intro: "Intro",
  objectif: "Objectif",
  definition: "Définition.",
  reglesImportantes: ["Règle 1"],
  exemples: [{ id: "ex1", titre: "Exemple 1", enonce: "Énoncé.", reponse: "Réponse." }],
  erreursFrequentes: [],
  astuce: "",
  figure: null,
  quizExerciseIds: [67, 68, 81],
};

const EXERCISES = {
  67: { id: 67, enonce: "Énoncé 67", answer: "Réponse 67" },
  68: { id: 68, enonce: "Énoncé 68", answer: "Réponse 68" },
  81: { id: 81, enonce: "Énoncé 81", answer: "Réponse 81" },
};

function apiError(status) {
  const err = new Error(`Erreur API /api/exercise: ${status}`);
  err.status = status;
  return err;
}

async function openNotion(notion = BASE_NOTION) {
  document.body.innerHTML = loadPageBody("cours.html");
  mockApi.me.mockResolvedValue({ user: { is_guest: false } });
  mockApi.chapters.mockResolvedValue({ chapters_meta: [CHAPTER] });
  mockApi.getCourseProgress.mockResolvedValue({});
  mockApi.saveCourseProgress.mockResolvedValue({});
  mockApi.getCourseContent.mockResolvedValue({ title: CHAPTER.title, notions: [notion] });
  vi.resetModules();
  await import("../cours.js");
  await flushPromises();
  await flushPromises();
  document.querySelector(".cours-open-btn").click();
  await flushPromises();
  await flushPromises();
  document.querySelector(`.cours-notion-card[data-notion="${notion.id}"] .cours-read-btn`).click();
  await flushPromises();
  await flushPromises();
  await flushPromises();
}

const zone = () => document.getElementById("cours-quiz-zone");
const label = () => zone().querySelector(".cours-quiz-label-text")?.textContent || "";
const doneRow = () => document.getElementById("cours-done-row");
const savedStatuses = () => mockApi.saveCourseProgress.mock.calls.map((c) => c[2].status);

async function answerAll(success = true) {
  while (zone().querySelector("#cours-quiz-reveal")) {
    zone().querySelector("#cours-quiz-reveal").click();
    zone()
      .querySelector(success ? "#cours-quiz-success" : "#cours-quiz-fail")
      .click();
    await flushPromises();
  }
}

describe("cours.js — mini-quiz", () => {
  let warn;
  beforeEach(() => {
    Object.values(mockApi).forEach((fn) => fn.mockReset());
    warn = vi.spyOn(console, "warn").mockImplementation(() => {});
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("Indice et Point méthode : affichés seulement si l'aide existe, sans changer le score", async () => {
    const aides = {
      67: { ...EXERCISES[67], hint: "Indice 67", solution_steps: ["Étape 1 — a", "Étape 2 — b"] },
      68: { ...EXERCISES[68], hint: "", solution_steps: [] },
      81: { ...EXERCISES[81], hint: "Indice 81", solution_steps: [] },
    };
    mockApi.exercise.mockImplementation((id) => Promise.resolve({ exercise: aides[id] }));
    await openNotion();
    const q = (sel) => zone().querySelector(sel);
    expect(q("#cours-quiz-hint-box").hidden).toBe(true);
    q("#cours-quiz-hint").click();
    expect(q("#cours-quiz-hint-box").hidden).toBe(false);
    expect(q("#cours-quiz-hint-box").textContent).toBe("Indice 67");
    q("#cours-quiz-method").click();
    expect(q("#cours-quiz-method-box").querySelectorAll("li").length).toBe(2);
    expect(q("#cours-quiz-method").classList.contains("is-revealed")).toBe(true);
    q("#cours-quiz-reveal").click();
    q("#cours-quiz-success").click();
    await flushPromises();
    expect(label()).toContain("question 2/3");
    expect(q("#cours-quiz-hint")).toBeNull();
    expect(q("#cours-quiz-method")).toBeNull();
    expect(q(".cours-quiz-aides")).toBeNull();
    q("#cours-quiz-reveal").click();
    q("#cours-quiz-fail").click();
    await flushPromises();
    expect(q("#cours-quiz-hint")).not.toBeNull();
    expect(q("#cours-quiz-method")).toBeNull();
    q("#cours-quiz-reveal").click();
    q("#cours-quiz-success").click();
    await flushPromises();
    expect(zone().textContent).toContain("2/3");
  });

  it("mini-quiz complet : 3 questions, classe courante transmise, validation à la fin seulement", async () => {
    mockApi.exercise.mockImplementation((id) => Promise.resolve({ exercise: EXERCISES[id] }));
    await openNotion();
    expect(mockApi.exercise.mock.calls).toEqual([
      [67, "troisieme"],
      [68, "troisieme"],
      [81, "troisieme"],
    ]);
    expect(label()).toContain("question 1/3");
    expect(zone().textContent).toContain("Énoncé 67");
    expect(savedStatuses()).not.toContain("done");
    expect(doneRow().hidden).toBe(true);
    await answerAll(true);
    expect(zone().textContent).toContain("3/3");
    expect(mockApi.saveCourseProgress).toHaveBeenLastCalledWith(
      "Chapitre_1",
      "criteres-de-divisibilite",
      { status: "done", quizScore: 3, quizTotal: 3 },
      "troisieme",
    );
    expect(warn).not.toHaveBeenCalled();
  });

  it("un exercice absent (404) : le quiz reste jouable avec les autres et l'absence est journalisée", async () => {
    mockApi.exercise.mockImplementation((id) =>
      id === 68 ? Promise.reject(apiError(404)) : Promise.resolve({ exercise: EXERCISES[id] }),
    );
    await openNotion();
    expect(label()).toContain("question 1/2");
    expect(savedStatuses()).not.toContain("done");
    expect(warn).toHaveBeenCalledWith(
      "[mini-quiz] exercice(s) non chargé(s)",
      expect.objectContaining({
        notionId: "criteres-de-divisibilite",
        classLevel: "troisieme",
        charges: 2,
        total: 3,
        failures: [expect.objectContaining({ id: 68, kind: "absent", status: 404 })],
      }),
    );
    await answerAll(false);
    expect(mockApi.saveCourseProgress).toHaveBeenLastCalledWith(
      "Chapitre_1",
      "criteres-de-divisibilite",
      { status: "done", quizScore: 0, quizTotal: 2 },
      "troisieme",
    );
  });

  it("tous les exercices absents : message explicite, aucune validation automatique, fin de leçon manuelle possible", async () => {
    mockApi.exercise.mockRejectedValue(apiError(404));
    await openNotion();
    expect(zone().textContent).toContain("Le mini-quiz de cette notion est momentanément indisponible.");
    expect(zone().querySelector("#cours-quiz-retry")).toBeNull();
    expect(savedStatuses()).not.toContain("done");
    expect(doneRow().hidden).toBe(false);
    document.getElementById("cours-mark-done-btn").click();
    expect(savedStatuses().filter((s) => s === "done")).toHaveLength(1);
  });

  it("erreur réseau : message distinct, bouton Réessayer, et un nouvel essai réussi relance le quiz", async () => {
    mockApi.exercise.mockRejectedValue(new TypeError("Failed to fetch"));
    await openNotion();
    expect(zone().textContent).toContain("problème de connexion");
    expect(savedStatuses()).not.toContain("done");
    expect(warn.mock.calls[0][1].failures.every((f) => f.kind === "reseau")).toBe(true);
    expect(doneRow().hidden).toBe(false);

    mockApi.exercise.mockImplementation((id) => Promise.resolve({ exercise: EXERCISES[id] }));
    zone().querySelector("#cours-quiz-retry").click();
    await flushPromises();
    await flushPromises();
    expect(label()).toContain("question 1/3");
    expect(doneRow().hidden).toBe(true);
    expect(savedStatuses()).not.toContain("done");
  });

  it("erreur serveur (500) classée comme réseau, plusieurs échecs n'attachent jamais deux fois le bouton manuel", async () => {
    mockApi.exercise.mockRejectedValue(apiError(500));
    await openNotion();
    expect(zone().querySelector("#cours-quiz-retry")).not.toBeNull();
    zone().querySelector("#cours-quiz-retry").click();
    await flushPromises();
    await flushPromises();
    document.getElementById("cours-mark-done-btn").click();
    expect(savedStatuses().filter((s) => s === "done")).toHaveLength(1);
  });

  it("non-régression : une notion sans mini-quiz garde son bouton manuel visible et n'appelle jamais l'API exercice", async () => {
    await openNotion({ ...BASE_NOTION, quizExerciseIds: [] });
    expect(mockApi.exercise).not.toHaveBeenCalled();
    expect(doneRow().hidden).toBe(false);
    expect(savedStatuses()).toEqual(["in_progress"]);
    document.getElementById("cours-mark-done-btn").click();
    expect(savedStatuses()).toEqual(["in_progress", "done"]);
  });
});
