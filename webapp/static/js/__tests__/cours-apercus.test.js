// ── cours.js : encadrés d'aperçu de contenu verrouillé (notion.apercus,
// refonte pédagogique des cours, 2026-10-23) — remplacent, section par
// section, les cartes génériques "Contenu Premium"/"Contenu Ultra" dès
// qu'au moins un aperçu existe pour cette section. `apercus` vient du
// backend déjà filtré par palier (voir course_content_service.py) — ce
// fichier vérifie uniquement le RENDU, jamais le filtrage lui-même (couvert
// par test_course_content_service.py).
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

const CHAPTER = { id: "Chapitre_1", title: "Chapitre 1", notions_cours: [], n_notions: 1, notions_detail: [] };

function baseNotion(overrides = {}) {
  return {
    id: "notion-test",
    title: "Notion test",
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
    locked_content: { premium: true, premium_extra_examples: 2, premium_extra_formulas: 0, ultra: true },
    apercus: [
      {
        id: "ap1",
        section: "exemple",
        niveau: "premium",
        titre: "2 exemples de plus",
        description: "Deux exemples supplémentaires sur les pièges classiques.",
      },
      {
        id: "ap2",
        section: "exemple",
        niveau: "ultra",
        titre: "La démonstration",
        description: "Pourquoi la formule est vraie.",
      },
    ],
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

describe("cours.js — encadrés d'aperçu de contenu verrouillé (notion.apercus)", () => {
  it("affiche un encadré par aperçu, avec son titre, son niveau et sa description", async () => {
    const readerView = await openNotion(baseNotion());
    const locked = readerView.querySelectorAll(".cours-box--locked");
    expect(locked.length).toBe(2);
    expect(readerView.textContent).toContain("2 exemples de plus");
    expect(readerView.textContent).toContain("Deux exemples supplémentaires sur les pièges classiques.");
    expect(readerView.textContent).toContain("La démonstration");
  });

  it("affiche le badge de niveau (Premium / Ultra) et le lien de déblocage", async () => {
    const readerView = await openNotion(baseNotion());
    const niveaux = [...readerView.querySelectorAll(".cours-locked-niveau")].map((el) => el.textContent);
    expect(niveaux).toContain("Premium");
    expect(niveaux).toContain("Ultra");
    const links = readerView.querySelectorAll(".cours-locked-upgrade-link");
    expect(links.length).toBe(2);
    links.forEach((link) => expect(link.getAttribute("href")).toBe("/abonnement.html"));
  });

  it("n'affiche plus les cartes génériques 'Contenu Premium'/'Contenu Ultra' quand des aperçus existent pour cette section", async () => {
    const readerView = await openNotion(baseNotion());
    expect(readerView.textContent).not.toContain("Contenu Premium");
    expect(readerView.textContent).not.toContain("Contenu Ultra");
  });

  it("sans apercus, garde le rendu générique d'avant (non-régression)", async () => {
    const notion = baseNotion({ apercus: [] });
    const readerView = await openNotion(notion);
    expect(readerView.textContent).toContain("Contenu Premium");
    expect(readerView.textContent).toContain("Contenu Ultra");
  });

  it("un aperçu hors de la section 'exemple' n'apparaît pas dans la section Exemple guidé", async () => {
    const notion = baseNotion({
      apercus: [{ id: "ap3", section: "methode", niveau: "premium", titre: "Méthode alternative", description: "..." }],
    });
    const readerView = await openNotion(notion);
    // Aucun aperçu pour "exemple" → repli sur la carte générique Premium.
    expect(readerView.textContent).toContain("Contenu Premium");
    expect(readerView.textContent).not.toContain("Méthode alternative");
  });
});
