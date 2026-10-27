// ── cours.js : tableau comparatif (notion.tableauComparatif, refonte
// pédagogique Phase 3, 2026-10-23) — synthèse de reconnaissance pour une
// notion à plusieurs règles proches (ex. "Opérations sur les dérivées").
// Ne remplace jamais les exemples détaillés : vient en complément des
// règles importantes, voir buildTableauComparatifHtml dans cours.js.
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
  getStoredClassLevel: () => "premiere",
  fetchCurricula: () => Promise.resolve([{ classLevel: "premiere", hasCourses: true }]),
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

const CHAPTER = { id: "Chapitre_3", title: "Chapitre 3", notions_cours: [], n_notions: 1, notions_detail: [] };

function baseNotion(overrides = {}) {
  return {
    id: "operations-et-derivation",
    title: "Opérations et dérivation",
    schemaVersion: 2,
    intro: "Intro",
    objectif: "Objectif",
    definition: "Définition.",
    reglesImportantes: ["Règle 1"],
    exemples: [{ id: "ex1", titre: "Exemple 1", enonce: "Énoncé.", reponse: "Réponse." }],
    erreursFrequentes: [],
    astuce: "",
    figure: null,
    quizExerciseIds: [1, 2],
    locked_content: { premium: false, premium_extra_examples: 0, premium_extra_formulas: 0, ultra: false },
    tableauComparatif: {
      titre: "Les quatre règles en un coup d'œil",
      colonnes: ["Forme à reconnaître", "Règle", "Exemple simple", "Piège principal"],
      lignes: [
        { forme: "$k \\times u$", regle: "$(ku)'=ku'$", exemple: "$(3x^2)'=6x$", piege: "Ne pas dériver $k$." },
        { forme: "$u+v$", regle: "$(u+v)'=u'+v'$", exemple: "$(x^2+3x)'=2x+3$" },
      ],
    },
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

describe("cours.js — tableau comparatif (notion.tableauComparatif)", () => {
  it("affiche une table avec les en-têtes et une ligne par règle", async () => {
    const readerView = await openNotion(baseNotion());
    const table = readerView.querySelector(".cours-table-comparatif");
    expect(table).not.toBeNull();
    expect(table.querySelectorAll("thead th").length).toBe(4);
    expect(table.querySelectorAll("tbody tr").length).toBe(2);
  });

  it("affiche le titre du tableau et le contenu de chaque cellule", async () => {
    const readerView = await openNotion(baseNotion());
    expect(readerView.textContent).toContain("Les quatre règles en un coup d'œil");
    expect(readerView.textContent).toContain("Ne pas dériver $k$.");
  });

  it("une ligne sans piège affiche un tiret plutôt qu'une cellule vide", async () => {
    const readerView = await openNotion(baseNotion());
    const rows = readerView.querySelectorAll(".cours-table-comparatif tbody tr");
    const lastRowCells = rows[1].querySelectorAll("td");
    expect(lastRowCells[3].textContent).toBe("—");
  });

  it("le tableau est enveloppé dans un conteneur à défilement horizontal", async () => {
    const readerView = await openNotion(baseNotion());
    const wrap = readerView.querySelector(".cours-table-wrap");
    expect(wrap).not.toBeNull();
    expect(wrap.querySelector("table")).not.toBeNull();
  });

  it("sans tableauComparatif, aucune table n'est rendue (non-régression)", async () => {
    const notion = baseNotion({ tableauComparatif: undefined });
    const readerView = await openNotion(notion);
    expect(readerView.querySelector(".cours-table-comparatif")).toBeNull();
  });

  it("avec une liste de lignes vide, aucune table n'est rendue", async () => {
    const notion = baseNotion({ tableauComparatif: { titre: "Vide", colonnes: [], lignes: [] } });
    const readerView = await openNotion(notion);
    expect(readerView.querySelector(".cours-table-comparatif")).toBeNull();
  });
});
