// ── Quatrième, chapitre pilote « Théorème de Pythagore » (2026-10-24) —
// rendu RÉEL du contenu livré (course_content/cours_quatrieme/chapitre_8.json
// et exercises_bank_quatrieme.json, lus sur disque) dans le lecteur de cours
// existant : mêmes composants que les autres classes, aucun style dédié.
// geomSvg.js n'est pas mocké : les figures sont réellement dessinées.
import { describe, it, expect, vi, beforeEach } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { loadPageBody, flushPromises } from "./testUtils.js";
import { renderFigure } from "../geomSvg.js";

const ROOT = resolve(__dirname, "..", "..", "..", "..");
const CHAPTER = JSON.parse(
  readFileSync(resolve(ROOT, "webapp", "course_content", "cours_quatrieme", "chapitre_8.json"), "utf-8"),
);
const BANK = Object.fromEntries(
  JSON.parse(readFileSync(resolve(ROOT, "exercises_bank_quatrieme.json"), "utf-8")).map((e) => [e.id, e]),
);

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
vi.mock("../curriculumSelector.js", () => ({
  getStoredClassLevel: () => "quatrieme",
  fetchCurricula: () => Promise.resolve([{ classLevel: "quatrieme", hasCourses: true }]),
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

// Même filtrage que course_content_service.filter_notion pour un compte Free
// (le filtrage serveur lui-même est verrouillé par tests/test_quatrieme_pythagore.py).
const PREMIUM_FIELDS = ["explicationSimple", "intuition", "exemplesConcrets", "erreursFrequentesDetail", "aRetenir"];
function asFree(notion) {
  const free = { ...notion, exemples: notion.exemples.filter((e) => e.niveauAcces === "free") };
  PREMIUM_FIELDS.forEach((f) => delete free[f]);
  delete free.demonstration;
  free.formules = notion.formules.slice(0, 1);
  free.locked_content = { premium: true, premium_extra_examples: 2, premium_extra_formulas: 1, ultra: true };
  return free;
}
function asUltra(notion) {
  const ultra = {
    ...notion,
    locked_content: { premium: false, premium_extra_examples: 0, premium_extra_formulas: 0, ultra: false },
  };
  delete ultra.apercus;
  return ultra;
}

const META = { id: "Chapitre_8", title: CHAPTER.title, notions_cours: [], n_notions: 5, notions_detail: [] };

async function openNotion(notion, progress = {}) {
  document.body.innerHTML = loadPageBody("cours.html");
  mockApi.me.mockResolvedValue({ user: { is_guest: false } });
  mockApi.chapters.mockResolvedValue({ chapters_meta: [META] });
  mockApi.getCourseProgress.mockResolvedValue(progress);
  mockApi.saveCourseProgress.mockResolvedValue({});
  mockApi.getCourseContent.mockResolvedValue({ ...CHAPTER, notions: [notion] });
  mockApi.exercise.mockImplementation((id) => Promise.resolve({ exercise: BANK[id] }));
  vi.resetModules();
  await import("../cours.js");
  await flushPromises();
  await flushPromises();
  document.querySelector(".cours-open-btn").click();
  await flushPromises();
  await flushPromises();
  document.querySelector(`.cours-notion-card[data-notion="${notion.id}"] .cours-read-btn`).click();
  for (let i = 0; i < 4; i++) await flushPromises();
}

describe("Quatrième — figures du chapitre Pythagore (geomSvg réel)", () => {
  CHAPTER.notions.forEach((notion) => {
    it(`${notion.id} : figure dessinée, angle droit codé, étapes révélées, couleurs par variables CSS`, () => {
      const svg = renderFigure(notion.figure);
      expect(svg).toContain('class="geom-figure geom-figure--geom"');
      expect(svg).toMatch(/viewBox="0 0 [\d.]+ [\d.]+"/);
      expect(svg).not.toMatch(/\swidth="\d/); // largeur pilotée par le CSS (width: 100%) : responsive
      expect(svg.match(/geom-polygon--marker/g)).toHaveLength(1);
      expect(svg).toContain("reveal-2");
      expect(svg).toContain("reveal-3");
      // Compatibilité thème clair/sombre : aucune couleur écrite en dur dans
      // le SVG, tout passe par les classes CSS (variables du thème).
      expect(svg).not.toMatch(/(fill|stroke)="#/);
      expect(svg).not.toMatch(/style="[^"]*(color|fill|stroke)/);
    });
  });
});

describe("Quatrième — lecteur de cours", () => {
  beforeEach(() => {
    Object.values(mockApi).forEach((fn) => fn.mockReset());
  });

  it("Free : le cours essentiel est complet (règles, méthode, 2 exemples, figure expliquée, quiz) et le reste est annoncé", async () => {
    const source = CHAPTER.notions[0];
    await openNotion(asFree(source));
    const reader = document.body;
    expect(reader.querySelectorAll(".cours-regle-card")).toHaveLength(source.reglesImportantes.length);
    expect(reader.querySelectorAll(".cours-step").length).toBeGreaterThanOrEqual(source.methode.etapes.length);
    expect(reader.querySelectorAll(".cours-exemple-card")).toHaveLength(2);
    expect(reader.querySelector(".cours-figure-layout svg.geom-figure")).not.toBeNull();
    expect(reader.querySelectorAll(".cours-figure-step-btn")).toHaveLength(3);
    expect(reader.querySelector(".cours-figure-cards")).not.toBeNull(); // figure.explication rédigée
    expect(reader.querySelectorAll(".cours-box--locked").length).toBeGreaterThanOrEqual(2); // aperçus Premium + Ultra
    expect(reader.textContent).not.toContain("Démonstration — pourquoi");
    expect(document.getElementById("cours-quiz-zone").textContent).toContain("question 1/3");
    expect(mockApi.exercise.mock.calls).toEqual(source.quizExerciseIds.map((id) => [id, "quatrieme"]));
  });

  it("Ultra : tous les exemples et la démonstration sont affichés, aucun verrou", async () => {
    const source = CHAPTER.notions[0];
    await openNotion(asUltra(source));
    expect(document.querySelectorAll(".cours-exemple-card")).toHaveLength(source.exemples.length);
    expect(document.body.textContent).toContain("Démonstration — pourquoi l'égalité est-elle toujours vraie ?");
    expect(document.querySelectorAll(".cours-box--locked")).toHaveLength(0);
  });

  it("réciproque / contraposée : le tableau de synthèse est affiché en Free", async () => {
    await openNotion(asFree(CHAPTER.notions.find((n) => n.id === "triangle-rectangle-ou-non")));
    const rows = document.querySelectorAll(".cours-table-comparatif tbody tr");
    expect(rows).toHaveLength(3);
  });

  it("mini-quiz complet : validation de la leçon seulement après les 3 réponses", async () => {
    const source = CHAPTER.notions.find((n) => n.id === "problemes-avec-pythagore");
    await openNotion(asFree(source));
    const zone = document.getElementById("cours-quiz-zone");
    expect(zone.textContent).toContain(BANK[source.quizExerciseIds[0]].enonce);
    const statuses = () => mockApi.saveCourseProgress.mock.calls.map((c) => c[2].status);
    expect(statuses()).not.toContain("done");
    while (zone.querySelector("#cours-quiz-reveal")) {
      zone.querySelector("#cours-quiz-reveal").click();
      zone.querySelector("#cours-quiz-success").click();
      await flushPromises();
    }
    expect(mockApi.saveCourseProgress).toHaveBeenLastCalledWith(
      "Chapitre_8",
      "problemes-avec-pythagore",
      { status: "done", quizScore: 3, quizTotal: 3 },
      "quatrieme",
    );
  });

  it("le retour au chapitre affiche aussitôt la notion terminée, sans rechargement", async () => {
    const source = CHAPTER.notions.find((n) => n.id === "carres-et-racines-carrees");
    await openNotion(asFree(source));
    const zone = document.getElementById("cours-quiz-zone");
    while (zone.querySelector("#cours-quiz-reveal")) {
      zone.querySelector("#cours-quiz-reveal").click();
      zone.querySelector("#cours-quiz-success").click();
      await flushPromises();
    }
    document.getElementById("cours-back-to-chapter").click();
    await flushPromises();
    const card = document.querySelector(`.cours-notion-card[data-notion="${source.id}"]`);
    expect(card.textContent).toContain("Terminée");
  });

  it("rouvrir une notion déjà terminée ne la rétrograde jamais en « En cours »", async () => {
    const source = CHAPTER.notions[0];
    const progress = { Chapitre_8: { [source.id]: { status: "done", quizScore: 3, quizTotal: 3 } } };
    await openNotion(asFree(source), progress);
    expect(mockApi.saveCourseProgress.mock.calls.map((c) => c[2].status)).not.toContain("in_progress");
    expect(document.querySelector(".cours-progress-badge").textContent).toContain("Terminée");
  });
});
