// ── cours.js : page "Cours" — ce fichier couvre spécifiquement la régression
// "troisieme" (curriculum_registry.py) : un fetch de contenu de chapitre qui
// échoue (404/réseau) ne doit JAMAIS laisser le squelette de chargement
// bloqué indéfiniment (Promise rejetée non gérée, invisible pour
// l'utilisateur) — voir cours.js::openChapter/renderChapterLoadError.
//
// Chantier "Répartition du contenu des cours par plan" (2026-08-26) :
// loadChapterContent() appelle désormais api.getCourseContent() (route
// GET /api/course-content/<classe>/<chapitre>, filtrée par plan côté
// serveur) plutôt qu'un fetch statique direct — ce fichier mock donc
// api.getCourseContent au lieu de global.fetch.
import { describe, it, expect, vi, beforeEach } from "vitest";
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
vi.mock("../geomSvg.js", () => ({ renderFigure: vi.fn(() => "") }));
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

const CHAPTER = { id: "Chapitre_1", title: "Nombres et calculs", notions_cours: [], n_notions: 2, notions_detail: [] };

function defaultMocks() {
  Object.values(mockApi).forEach((fn) => fn.mockReset());
  mockApi.me.mockResolvedValue({ user: { is_guest: false } });
  mockApi.chapters.mockResolvedValue({ chapters_meta: [CHAPTER] });
  mockApi.getCourseProgress.mockResolvedValue({});
  // Comportement par défaut neutre — chaque describe ci-dessous reconfigure
  // explicitement getCourseContent APRÈS mountCours() (donc après ce reset),
  // juste avant le clic qui le déclenche réellement.
  mockApi.getCourseContent.mockResolvedValue({ title: CHAPTER.title, notions: [] });
}

async function mountCours() {
  document.body.innerHTML = loadPageBody("cours.html");
  defaultMocks();
  vi.resetModules();
  await import("../cours.js");
  await flushPromises();
  await flushPromises();
}

describe("cours.js — échec de chargement du contenu d'un chapitre", () => {
  beforeEach(async () => {
    await mountCours();
    mockApi.getCourseContent.mockRejectedValue(new Error("Contenu introuvable pour Chapitre_1"));
  });

  it("n'affiche jamais indéfiniment le squelette de chargement après un échec", async () => {
    document.querySelector(".cours-open-btn").click();
    await flushPromises();
    await flushPromises();

    expect(document.querySelectorAll(".cours-skeleton-card").length).toBe(0);
  });

  it("affiche un vrai message d'erreur avec Réessayer et Retour", async () => {
    document.querySelector(".cours-open-btn").click();
    await flushPromises();
    await flushPromises();

    const errorCard = document.querySelector(".cours-load-error");
    expect(errorCard).not.toBeNull();
    expect(errorCard.textContent).toContain("Le contenu de ce chapitre est momentanément indisponible.");
    expect(document.getElementById("cours-error-retry")).not.toBeNull();
    expect(document.getElementById("cours-error-back")).not.toBeNull();
  });

  it("le bouton Retour ramène à la grille des chapitres", async () => {
    document.querySelector(".cours-open-btn").click();
    await flushPromises();
    await flushPromises();

    document.getElementById("cours-error-back").click();

    expect(document.getElementById("cours-list-view").hidden).toBe(false);
    expect(document.getElementById("cours-reader-view").hidden).toBe(true);
  });

  it("le bouton Réessayer relance l'appel et affiche le contenu si celui-ci réussit ensuite", async () => {
    document.querySelector(".cours-open-btn").click();
    await flushPromises();
    await flushPromises();

    mockApi.getCourseContent.mockResolvedValue({ title: "Nombres et calculs", notions: [] });
    document.getElementById("cours-error-retry").click();
    await flushPromises();
    await flushPromises();

    expect(document.querySelector(".cours-load-error")).toBeNull();
  });

  it("ne laisse aucune Promise rejetée non gérée s'échapper du clic", async () => {
    const unhandled = vi.fn();
    process.on("unhandledRejection", unhandled);

    document.querySelector(".cours-open-btn").click();
    await flushPromises();
    await flushPromises();

    process.off("unhandledRejection", unhandled);
    expect(unhandled).not.toHaveBeenCalled();
  });
});

describe("cours.js — chargement réussi (non-régression)", () => {
  beforeEach(async () => {
    await mountCours();
    mockApi.getCourseContent.mockResolvedValue({ title: "Nombres et calculs", notions: [] });
  });

  it("ouvre normalement le chapitre quand le contenu existe", async () => {
    document.querySelector(".cours-open-btn").click();
    await flushPromises();
    await flushPromises();

    expect(document.querySelector(".cours-load-error")).toBeNull();
    expect(document.getElementById("cours-reader-view").hidden).toBe(false);
  });
});
