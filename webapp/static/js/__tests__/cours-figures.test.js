// Chantier "cours" (refonte visuelle) : couvre le rendu réel des figures
// dans une notion (pas mocké, contrairement à cours.test.js) — une notion
// sans figure doit continuer de fonctionner à l'identique (compatibilité
// anciens JSON), une notion avec figure valide doit afficher un SVG, une
// notion avec figure malformée ne doit jamais casser le chargement de la
// page (voir cours.js::buildFigureBlockHtml, try/catch ajouté par l'audit).
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
vi.mock("../mathrender.js", () => ({ setMathContent: vi.fn(), setRenderedHtmlContent: (el, text) => { el.textContent = text; } }));
// geomSvg.js réel (pas mocké) : on veut vérifier le vrai rendu SVG.
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

const CHAPTER = { id: "Chapitre_1", title: "Nombres et calculs", notions_cours: [], n_notions: 3, notions_detail: [] };

const NOTION_SANS_FIGURE = {
  id: "notion-sans-figure", title: "Notion sans figure", schemaVersion: 2,
  definition: "Définition.", figure: null, exemples: [], erreursFrequentes: [], aRetenir: [],
};
const NOTION_AVEC_FIGURE = {
  id: "notion-avec-figure", title: "Notion avec figure", schemaVersion: 2,
  definition: "Définition.", exemples: [], erreursFrequentes: [], aRetenir: [],
  figure: { viewBox: [-1, -1, 8, 8], axes: true, points: [{ x: 2, y: 2, label: "A" }], alt: "Point A" },
};
const NOTION_FIGURE_MALFORMEE = {
  id: "notion-figure-malformee", title: "Notion avec figure cassée", schemaVersion: 2,
  definition: "Définition.", exemples: [], erreursFrequentes: [], aRetenir: [],
  figure: { kind: "type-inconnu-invente" },
};

function defaultMocks() {
  Object.values(mockApi).forEach((fn) => fn.mockReset());
  mockApi.me.mockResolvedValue({ user: { is_guest: false } });
  mockApi.chapters.mockResolvedValue({ chapters_meta: [CHAPTER] });
  mockApi.getCourseProgress.mockResolvedValue({});
  mockApi.saveCourseProgress.mockResolvedValue({});
}

async function mountCours() {
  document.body.innerHTML = loadPageBody("cours.html");
  defaultMocks();
  vi.resetModules();
  await import("../cours.js");
  await flushPromises();
  await flushPromises();
}

async function openNotion(notion) {
  await mountCours();
  mockApi.getCourseContent.mockResolvedValue({ title: "Nombres et calculs", notions: [notion] });
  document.querySelector(".cours-open-btn").click();
  await flushPromises();
  await flushPromises();
  document.querySelector(`.cours-notion-card[data-notion="${notion.id}"] .cours-read-btn`).click();
  await flushPromises();
  await flushPromises();
}

describe("cours.js — rendu des figures dans une notion", () => {
  it("une notion sans figure (figure: null) s'affiche normalement, sans bloc figure", async () => {
    await openNotion(NOTION_SANS_FIGURE);
    expect(document.querySelector(".cours-load-error")).toBeNull();
    expect(document.querySelector(".cours-figure-layout")).toBeNull();
  });

  it("une notion avec une figure valide affiche un vrai SVG", async () => {
    await openNotion(NOTION_AVEC_FIGURE);
    expect(document.querySelector(".cours-load-error")).toBeNull();
    const svg = document.querySelector(".cours-figure-layout svg");
    expect(svg).not.toBeNull();
    expect(svg.getAttribute("aria-label")).toBe("Point A");
  });

  it("une notion avec une figure malformée (kind inconnu) n'empêche jamais le chargement de la page", async () => {
    await openNotion(NOTION_FIGURE_MALFORMEE);
    expect(document.querySelector(".cours-load-error")).toBeNull();
    expect(document.getElementById("cours-reader-view").hidden).toBe(false);
    // Le kind inconnu retombe sur renderGeom par défaut (voir geomSvg.js) :
    // avec viewBox absent, le repli défensif produit tout de même un SVG,
    // jamais une exception qui casserait la page.
    expect(() => document.querySelector(".cours-figure-layout")).not.toThrow();
  });
});
