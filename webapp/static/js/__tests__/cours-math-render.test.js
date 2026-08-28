// ── Non-régression : rendu mathématique sur TOUTES les pages de cours ──────
// Cause du bug corrigé : certains champs de notion (intro, objectif, la
// description de carte de la liste du chapitre, les titres de méthode/
// démonstration/exemple) étaient interpolés directement dans le HTML sans
// jamais passer par le pipeline data-text → renderMathAttrs → setMathContent
// → KaTeX (voir mathrender.js). Résultat : le LaTeX ($...$, \frac, \sqrt...)
// s'affichait littéralement au lieu d'être rendu.
//
// Ce test ne mocke PAS mathrender.js (contrairement à cours-figures.test.js) :
// on veut vérifier le VRAI pipeline. window.renderMathInElement est simulé
// pour se comporter comme le fait réellement KaTeX auto-render — il consomme
// les délimiteurs `$...$` des éléments qu'on lui passe. Si un champ ne passe
// jamais par ce pipeline (régression du bug corrigé), son texte brut reste
// visible dans le DOM et le test le détecte via findRawLatexInDom.
import { describe, it, expect, vi, afterEach } from "vitest";
import { loadPageBody, flushPromises } from "./testUtils.js";
import { findRawLatexInDom } from "./helpers/detectRawLatex.js";

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
// geomSvg.js et mathrender.js réels (pas mockés) : on veut le vrai pipeline.
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

const CHAPTER = { id: "Chapitre_1", title: "Dérivation", notions_cours: [], n_notions: 1, notions_detail: [] };

// Une notion contenant du LaTeX dans CHAQUE champ texte connu du template,
// y compris les 4 points corrigés (intro, objectif, méthode.titre,
// démonstration.titre) et les champs qui passaient déjà par data-text.
const NOTION_AVEC_LATEX = {
  id: "nombre-derive", title: "Nombre dérivé", schemaVersion: 2,
  intro: "Le taux de variation $\\frac{f(x_0+h)-f(x_0)}{h}$ est étudié ici.",
  objectif: "Tu sauras calculer $f'(x_0)$ en faisant tendre $h \\to 0$.",
  definition: "Le nombre dérivé $f'(x_0)$ est la limite $\\lim_{h\\to0}\\frac{f(x_0+h)-f(x_0)}{h}$.",
  explicationSimple: "On calcule $\\sqrt{x}$ puis $x^2$.",
  pourquoi: "Pour étudier les variations avec $\\Delta y / \\Delta x$.",
  methode: { titre: "Calculer $f'(x_0)$", etapes: [{ texte: "On développe $(x+h)^2$." }] },
  exemples: [{ id: "ex1", titre: "Exemple $f(x)=x^2$", enonce: "Calculer $f'(2)$.", reponse: "$4$" }],
  demonstration: {
    titre: "Pourquoi $(x^2)' = 2x$ ? — démonstration",
    etapes: [{ titre: "Étape 1", texte: "On développe $(x+h)^2$." }],
    conclusion: "On obtient $2x$.",
  },
  erreursFrequentes: ["Confondre $f(x_0+h)$ et $f(x_0)+h$."],
  aRetenir: ["$f'(x_0) = \\lim_{h\\to0}\\frac{f(x_0+h)-f(x_0)}{h}$"],
  figure: null,
};

function defaultMocks() {
  Object.values(mockApi).forEach((fn) => fn.mockReset());
  mockApi.me.mockResolvedValue({ user: { is_guest: false } });
  mockApi.chapters.mockResolvedValue({ chapters_meta: [CHAPTER] });
  mockApi.getCourseProgress.mockResolvedValue({});
  mockApi.saveCourseProgress.mockResolvedValue({});
}

/** Simule le comportement réel de KaTeX auto-render : consomme les segments
 * $...$/$$...$$ des éléments qu'on lui passe (jamais du texte hors de ces
 * éléments — c'est justement ce qui permet au test de détecter un champ qui
 * ne serait jamais passé au moteur). */
function installFakeKatex() {
  window.renderMathInElement = (el) => {
    const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
    const nodes = [];
    let n;
    while ((n = walker.nextNode())) nodes.push(n);
    nodes.forEach((textNode) => {
      if (!textNode.textContent.includes("$")) return;
      textNode.textContent = textNode.textContent.replace(/\$\$?([^$]+)\$\$?/g, "‹math›");
    });
  };
}

async function mountCours() {
  document.body.innerHTML = loadPageBody("cours.html");
  defaultMocks();
  installFakeKatex();
  vi.resetModules();
  await import("../cours.js");
  await flushPromises();
  await flushPromises();
}

describe("cours.js — rendu mathématique (non-régression architecturale)", () => {
  afterEach(() => {
    delete window.renderMathInElement;
  });

  it("la carte de notion dans la liste du chapitre ne montre aucun LaTeX brut (objectif)", async () => {
    await mountCours();
    mockApi.getCourseContent.mockResolvedValue({ title: "Dérivation", notions: [NOTION_AVEC_LATEX] });
    document.querySelector(".cours-open-btn").click();
    await flushPromises();
    await flushPromises();

    const card = document.querySelector('.cours-notion-card[data-notion="nombre-derive"]');
    expect(card).not.toBeNull();
    const raw = findRawLatexInDom(card);
    expect(raw).toEqual([]);
  });

  it("la page détail d'une notion ne montre aucun LaTeX brut, sur tous les champs (intro, objectif, définition, méthode, exemples, démonstration, erreurs, à retenir)", async () => {
    await mountCours();
    mockApi.getCourseContent.mockResolvedValue({ title: "Dérivation", notions: [NOTION_AVEC_LATEX] });
    document.querySelector(".cours-open-btn").click();
    await flushPromises();
    await flushPromises();
    document.querySelector('.cours-notion-card[data-notion="nombre-derive"] .cours-read-btn').click();
    await flushPromises();
    await flushPromises();

    const readerView = document.getElementById("cours-reader-view");
    expect(readerView.hidden).toBe(false);

    // Vérifie explicitement que le pipeline a bien été appelé sur chaque
    // champ ciblé (aucun `data-text` restant = tout a été consommé).
    expect(readerView.querySelectorAll("[data-text]").length).toBe(0);

    const raw = findRawLatexInDom(readerView);
    expect(raw).toEqual([]);

    // Les marqueurs simulés doivent bien apparaître (preuve que le moteur
    // a réellement été invoqué sur intro/objectif/méthode.titre/
    // démonstration.titre, pas juste que le texte a disparu par hasard).
    expect(readerView.textContent).toContain("‹math›");
    expect(readerView.querySelector(".cours-intro-text").textContent).toContain("‹math›");
    expect(readerView.querySelector(".cours-objectif-card p").textContent).toContain("‹math›");
  });
});
