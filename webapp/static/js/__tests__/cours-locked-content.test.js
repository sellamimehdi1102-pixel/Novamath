// ── cours.js : indicateurs de contenu verrouillé (Chantier "Répartition du
// contenu des cours par plan", 2026-08-26) ──────────────────────────────────
// `notion.locked_content` vient du backend (course_content_service.py) — ce
// fichier vérifie que cours.js se contente de l'AFFICHER (jamais recalculé
// côté client), affiche un indicateur discret uniquement quand du contenu a
// réellement été retiré, et que le reste (mini-quiz, navigation, contenu
// Free normal) continue de fonctionner à l'identique.
import { describe, it, expect, vi } from "vitest";
import { loadPageBody, flushPromises } from "./testUtils.js";

const mockApi = {
  me: vi.fn(),
  chapters: vi.fn(),
  getCourseProgress: vi.fn(),
  saveCourseProgress: vi.fn(),
  exercise: vi.fn(),
  getCourseContent: vi.fn(),
};
vi.mock("../api.js", () => ({ api: mockApi }));
vi.mock("../settingsManager.js", () => ({ initSettingsManager: () => Promise.resolve(), onSettingsChange: vi.fn() }));
vi.mock("../settingsPopup.js", () => ({ bindSettingsButton: vi.fn() }));
vi.mock("../i18n.js", () => ({ bindLiveTranslations: vi.fn() }));
vi.mock("../mathrender.js", () => ({ setMathContent: (el, text) => { el.textContent = text; }, setRenderedHtmlContent: (el, text) => { el.textContent = text; } }));
vi.mock("../geomSvg.js", () => ({ renderFigure: vi.fn(() => "<svg></svg>") }));
vi.mock("../curriculumSelector.js", () => ({
  getStoredClassLevel: () => "seconde",
  fetchCurricula: () => Promise.resolve([{ classLevel: "seconde", hasCourses: true }]),
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

const CHAPTER = { id: "Chapitre_1", title: "Nombres et calculs", notions_cours: [], n_notions: 1, notions_detail: [] };

function baseNotion(overrides = {}) {
  return {
    id: "notion-test", title: "Notion test", schemaVersion: 2,
    intro: "Intro", objectif: "Objectif", definition: "Définition.",
    reglesImportantes: ["Règle 1"], exemples: [{ id: "ex1", titre: "Exemple 1", enonce: "Énoncé.", reponse: "Réponse." }],
    erreursFrequentes: [], astuce: "", figure: null, quizExerciseIds: [1, 2],
    locked_content: { premium: false, premium_extra_examples: 0, premium_extra_formulas: 0, ultra: false },
    ...overrides,
  };
}

function defaultMocks() {
  Object.values(mockApi).forEach((fn) => fn.mockReset());
  mockApi.me.mockResolvedValue({ user: { is_guest: false } });
  mockApi.chapters.mockResolvedValue({ chapters_meta: [CHAPTER] });
  mockApi.getCourseProgress.mockResolvedValue({});
  mockApi.saveCourseProgress.mockResolvedValue({});
  mockApi.exercise.mockResolvedValue({ exercise: { id: 1, enonce: "Q1", answer: "R1" } });
}

async function openNotion(notion) {
  document.body.innerHTML = loadPageBody("cours.html");
  defaultMocks();
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
  return document.getElementById("cours-reader-view");
}

describe("cours.js — indicateurs de contenu verrouillé", () => {
  it("une notion Free sans contenu verrouillé n'affiche aucun indicateur", async () => {
    const readerView = await openNotion(baseNotion());
    expect(readerView.querySelector(".cours-box--locked")).toBeNull();
  });

  it("affiche l'indicateur Premium quand locked_content.premium est vrai", async () => {
    const readerView = await openNotion(baseNotion({
      locked_content: { premium: true, premium_extra_examples: 2, premium_extra_formulas: 0, ultra: false },
    }));
    const card = readerView.querySelector(".cours-box--locked-premium");
    expect(card).not.toBeNull();
    expect(card.textContent).toContain("Contenu Premium");
    expect(card.textContent).toContain("2 exemples supplémentaires");
  });

  it("affiche l'indicateur Ultra quand locked_content.ultra est vrai", async () => {
    const readerView = await openNotion(baseNotion({
      locked_content: { premium: false, premium_extra_examples: 0, premium_extra_formulas: 0, ultra: true },
    }));
    const card = readerView.querySelector(".cours-box--locked-ultra");
    expect(card).not.toBeNull();
    expect(card.textContent).toContain("Contenu Ultra");
  });

  it("affiche les deux indicateurs si premium ET ultra sont tous les deux verrouillés", async () => {
    const readerView = await openNotion(baseNotion({
      locked_content: { premium: true, premium_extra_examples: 1, premium_extra_formulas: 0, ultra: true },
    }));
    expect(readerView.querySelectorAll(".cours-box--locked").length).toBe(2);
  });

  it("n'affiche jamais d'indicateur pour une notion sans locked_content (compatibilité)", async () => {
    const notion = baseNotion();
    delete notion.locked_content;
    const readerView = await openNotion(notion);
    expect(readerView.querySelector(".cours-box--locked")).toBeNull();
  });

  it("le contenu Free normal (définition, règles, premier exemple) reste affiché même avec du contenu verrouillé", async () => {
    const readerView = await openNotion(baseNotion({
      locked_content: { premium: true, premium_extra_examples: 1, premium_extra_formulas: 0, ultra: true },
    }));
    expect(readerView.textContent).toContain("Définition.");
    expect(readerView.textContent).toContain("Règle 1");
    expect(readerView.textContent).toContain("Énoncé.");
  });

  it("le mini-quiz continue de fonctionner sur une notion avec du contenu verrouillé", async () => {
    const readerView = await openNotion(baseNotion({
      locked_content: { premium: true, premium_extra_examples: 1, premium_extra_formulas: 0, ultra: false },
    }));
    await flushPromises();
    expect(mockApi.exercise).toHaveBeenCalled();
  });

  it("la navigation notion précédente/suivante continue de fonctionner", async () => {
    document.body.innerHTML = loadPageBody("cours.html");
    defaultMocks();
    const n1 = baseNotion({ id: "n1", title: "Notion 1" });
    const n2 = baseNotion({ id: "n2", title: "Notion 2" });
    mockApi.getCourseContent.mockResolvedValue({ title: CHAPTER.title, notions: [n1, n2] });
    vi.resetModules();
    await import("../cours.js");
    await flushPromises();
    await flushPromises();
    document.querySelector(".cours-open-btn").click();
    await flushPromises();
    await flushPromises();
    document.querySelector('.cours-notion-card[data-notion="n1"] .cours-read-btn').click();
    await flushPromises();
    await flushPromises();

    const nextBtn = document.querySelector(".cours-notion-nav-btn--next");
    expect(nextBtn).not.toBeNull();
    nextBtn.click();
    await flushPromises();
    await flushPromises();

    expect(document.getElementById("cours-reader-view").textContent).toContain("Notion 2");
  });
});
