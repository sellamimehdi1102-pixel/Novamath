// ── cours.js : CTA "Commencer les exercices" (refonte pédagogique des cours,
// 2026-10-23, point 7) — ce bouton doit désormais ouvrir une VRAIE série
// d'entraînement sur la notion précise dans l'onglet Entraînement (même
// mécanisme que chatbot.js::navigateToCard, type "notion_series" : pool
// d'exercices via api.exercisesByNotion, écriture de "lumis:pending_series",
// navigation vers exercice.html), au lieu de se contenter de faire défiler
// jusqu'au mini-quiz embarqué plus haut sur la page.
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { loadPageBody, flushPromises, withMockedLocation } from "./testUtils.js";

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
const NOTION = {
  id: "composition-de-fonctions-et-derivation",
  title: "Composition de fonctions et dérivation",
  schemaVersion: 2,
  intro: "Intro",
  objectif: "Objectif",
  definition: "Définition.",
  reglesImportantes: ["Règle 1"],
  exemples: [{ id: "ex1", titre: "Exemple 1", enonce: "Énoncé.", reponse: "Réponse." }],
  erreursFrequentes: [],
  astuce: "",
  figure: null,
  quizExerciseIds: [709, 710, 711],
};

function defaultMocks() {
  Object.values(mockApi).forEach((fn) => fn.mockReset());
  mockApi.me.mockResolvedValue({ user: { is_guest: false } });
  mockApi.chapters.mockResolvedValue({ chapters_meta: [CHAPTER] });
  mockApi.getCourseProgress.mockResolvedValue({});
  mockApi.saveCourseProgress.mockResolvedValue({});
  mockApi.getCourseContent.mockResolvedValue({ title: CHAPTER.title, notions: [NOTION] });
}

async function openNotionAndGetCta() {
  document.body.innerHTML = loadPageBody("cours.html");
  defaultMocks();
  vi.resetModules();
  await import("../cours.js");
  await flushPromises();
  await flushPromises();
  document.querySelector(".cours-open-btn").click();
  await flushPromises();
  await flushPromises();
  document.querySelector(`.cours-notion-card[data-notion="${NOTION.id}"] .cours-read-btn`).click();
  await flushPromises();
  await flushPromises();
  return document.getElementById("cours-cta-pratique-btn");
}

describe("cours.js — CTA 'Commencer les exercices' ouvre une vraie série dans Entraînement", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.spyOn(window, "alert").mockImplementation(() => {});
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("appelle api.exercisesByNotion avec le chapitre, le titre exact de la notion et la classe courante", async () => {
    await withMockedLocation(async () => {
      const btn = await openNotionAndGetCta();
      mockApi.exercisesByNotion.mockResolvedValue({ results: [{ exercise_id: 709 }, { exercise_id: 710 }] });
      btn.click();
      await flushPromises();
      expect(mockApi.exercisesByNotion).toHaveBeenCalledWith(
        "Chapitre_3",
        "Composition de fonctions et dérivation",
        10,
        "premiere",
      );
    });
  });

  it("écrit lumis:pending_series (mode notion) puis navigue vers exercice.html", async () => {
    await withMockedLocation(async () => {
      const btn = await openNotionAndGetCta();
      mockApi.exercisesByNotion.mockResolvedValue({
        results: [{ exercise_id: 709 }, { exercise_id: 710 }, { exercise_id: 711 }],
      });
      btn.click();
      await flushPromises();
      const pending = JSON.parse(localStorage.getItem("lumis:pending_series"));
      expect(pending).toEqual({
        mode: "notion",
        chapterId: "Chapitre_3",
        notion: "Composition de fonctions et dérivation",
        notions: ["Composition de fonctions et dérivation"],
        exerciseIds: [709, 710, 711],
      });
      expect(window.location.href).toBe("exercice.html");
    });
  });

  it("si aucun exercice n'est trouvé pour cette notion précise, affiche un message explicite et ne navigue jamais", async () => {
    await withMockedLocation(async () => {
      const btn = await openNotionAndGetCta();
      mockApi.exercisesByNotion.mockResolvedValue({ results: [] });
      btn.click();
      await flushPromises();
      expect(window.alert).toHaveBeenCalled();
      expect(localStorage.getItem("lumis:pending_series")).toBeNull();
      expect(window.location.href).toBe("");
    });
  });

  it("si l'appel échoue, affiche un message d'erreur et réactive le bouton", async () => {
    const btn = await openNotionAndGetCta();
    mockApi.exercisesByNotion.mockRejectedValue(new Error("réseau"));
    btn.click();
    await flushPromises();
    expect(window.alert).toHaveBeenCalled();
    expect(btn.disabled).toBe(false);
  });

  // ── Vérification Cours → Entraînement, point 8 : "ne jamais remplacer
  // silencieusement une série en cours" — même si exercice.js::init()
  // remplace déjà silencieusement une série en pause pour un lancement
  // explicite (comportement accepté pour le chatbot), ce point d'entrée
  // doit demander confirmation AVANT d'écrire quoi que ce soit dès qu'une
  // série est en pause (store.js::getInProgressSeries, clé réelle
  // "lumis:series_in_progress", non mockée dans ce fichier). ──────────────
  function setInProgressSeries() {
    localStorage.setItem(
      "lumis:series_in_progress",
      JSON.stringify({ class_level: "premiere", savedAt: Date.now(), chapterId: "Chapitre_1" }),
    );
  }

  it("une série en pause + confirmation acceptée : démarre normalement la nouvelle série", async () => {
    await withMockedLocation(async () => {
      const btn = await openNotionAndGetCta();
      setInProgressSeries();
      vi.spyOn(window, "confirm").mockReturnValue(true);
      mockApi.exercisesByNotion.mockResolvedValue({ results: [{ exercise_id: 709 }] });
      btn.click();
      await flushPromises();
      expect(window.confirm).toHaveBeenCalled();
      expect(mockApi.exercisesByNotion).toHaveBeenCalled();
      expect(JSON.parse(localStorage.getItem("lumis:pending_series")).notion).toBe(
        "Composition de fonctions et dérivation",
      );
      expect(window.location.href).toBe("exercice.html");
    });
  });

  it("une série en pause + confirmation refusée : n'appelle pas l'API, n'écrit rien et ne navigue pas", async () => {
    await withMockedLocation(async () => {
      const btn = await openNotionAndGetCta();
      setInProgressSeries();
      vi.spyOn(window, "confirm").mockReturnValue(false);
      btn.click();
      await flushPromises();
      expect(window.confirm).toHaveBeenCalled();
      expect(mockApi.exercisesByNotion).not.toHaveBeenCalled();
      expect(localStorage.getItem("lumis:pending_series")).toBeNull();
      expect(window.location.href).toBe("");
    });
  });

  it("aucune série en pause : ne demande aucune confirmation", async () => {
    await withMockedLocation(async () => {
      const btn = await openNotionAndGetCta();
      vi.spyOn(window, "confirm");
      mockApi.exercisesByNotion.mockResolvedValue({ results: [{ exercise_id: 709 }] });
      btn.click();
      await flushPromises();
      expect(window.confirm).not.toHaveBeenCalled();
    });
  });
});
