// ── exercice.js : progression réelle d'une série lancée via
// lumis:pending_series (mode "notion") ──────────────────────────────────────
// Chantier "routage réel" (2026-10-19, bug "les 10 questions sont
// identiques", persistant malgré deux correctifs précédents côté backend
// uniquement) : la cause racine réelle était double —
//   1. chatbot.js::resultToCard (suggestions live pendant la frappe, chemin
//      SÉPARÉ de action_cards_service.py/build_cards — jamais couvert par
//      les tests backend précédents) codait en dur `exercise_ids: [r.exercise_id]`,
//      un pool à 1 seul élément, quel que soit le nombre réel d'exercices de
//      la notion.
//   2. exercice.js::buildSeriesPool (ce fichier, voir ci-dessous) répétait
//      alors silencieusement cet unique id pour remplir SERIES_TOTAL
//      questions — chaque "question suivante" réaffichait donc le même
//      énoncé du début à la fin, sans que rien ne le signale (compteur et
//      historique progressaient normalement).
// Corrections : chatbot.js enrichit désormais le pool via
// /api/search/exercises-by-notion avant de poser lumis:pending_series quand
// il ne reçoit qu'un seul id (voir chatbot.test.js) ; buildSeriesPool()
// ci-dessous ne fabrique plus jamais de fausse diversité — un pool trop
// restreint raccourcit la série au lieu de répéter le même exercice.
//
// Round 2 (même jour) : persistance en conditions réelles malgré ce premier
// correctif — cause réelle TROUVÉE ET PROUVÉE : webapp/static-dist/ (bundle
// Vite figé, servi en PRIORITÉ sur webapp/static/ par server.py dès qu'il
// existe, voir _STATIC_FOLDER) datait d'avant ces correctifs. Le navigateur
// exécutait donc un exercice.js/chatbot.js obsolète quel que soit l'état des
// sources — aucun test unitaire ne peut détecter ce genre de problème de
// build/déploiement ; la preuve a été apportée en inspectant directement les
// fichiers servis par le serveur réel (voir le rapport). Le dossier a été
// désactivé (renommé) pour que le serveur de dev serve les sources réelles.
// Profitant du symptôme signalé ("3 questions distinctes puis répétition"),
// cette passe a aussi détecté et corrigé une VRAIE limite de taille de pool
// (action_cards_service.py/chatbot.js plafonnaient à 5 exercices, alors que
// exercice.js attend 10 questions par défaut) et ajouté une gestion
// explicite des identifiants introuvables (404) dans loadCurrent().
import { describe, it, expect, vi } from "vitest";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import { loadPageBody, flushPromises } from "./testUtils.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
// webapp/static/js/__tests__ -> ... -> racine du projet (exercises_bank.json)
const PROJECT_ROOT = resolve(__dirname, "..", "..", "..", "..");
const REAL_BANK = JSON.parse(readFileSync(resolve(PROJECT_ROOT, "exercises_bank.json"), "utf-8"));
const REAL_BANK_BY_ID = new Map(REAL_BANK.map((e) => [e.id, e]));

const mockApi = {
  practiceLoad: vi.fn(),
  practiceResult: vi.fn().mockResolvedValue({}),
  getQuota: vi.fn().mockResolvedValue({ exercises_daily: { used: 0, remaining: 20, limit: 20, unlimited: false } }),
  saveStats: vi.fn().mockResolvedValue({}),
  getStats: vi.fn().mockResolvedValue({}),
};
vi.mock("../api.js", () => ({ api: mockApi }));
vi.mock("../settingsManager.js", () => ({
  initSettingsManager: () => Promise.resolve(),
  getSettings: () => ({ training: { questionsPerSeries: 10 } }),
  onSettingsChange: vi.fn(),
}));
vi.mock("../settingsPopup.js", () => ({ bindSettingsButton: vi.fn() }));
vi.mock("../i18n.js", () => ({ bindLiveTranslations: vi.fn() }));
vi.mock("../mathrender.js", () => ({
  setMathContent: (el, text) => {
    el.textContent = text;
  },
}));
vi.mock("../animations.js", () => ({ fireConfetti: vi.fn(), shakeElement: vi.fn(), fadeInTransition: vi.fn() }));
vi.mock("../supportTicket.js", () => ({ openReportTicketPopup: vi.fn() }));

const $ = (id) => document.getElementById(id);

// Banque synthétique de 3 exercices réellement distincts — pour les tests qui
// n'ont besoin que de vérifier le MÉCANISME de progression (pas la richesse
// des données réelles).
const BANK = {
  101: { id: 101, chapter_id: "Chapitre_8", notion: "Dérivées", difficulty: 2, enonce: "Question A", hint: "", answer: "", solution_steps: [] },
  102: { id: 102, chapter_id: "Chapitre_8", notion: "Dérivées", difficulty: 2, enonce: "Question B", hint: "", answer: "", solution_steps: [] },
  103: { id: 103, chapter_id: "Chapitre_8", notion: "Dérivées", difficulty: 2, enonce: "Question C", hint: "", answer: "", solution_steps: [] },
};

async function mountExerciceWithPendingSeries(exerciseIds, { chapterId = "Chapitre_8", notion = "Dérivées", bank = BANK } = {}) {
  localStorage.setItem(
    "lumis:pending_series",
    JSON.stringify({ mode: "notion", chapterId, notion, notions: [notion], exerciseIds }),
  );
  window.history.pushState({}, "", "/exercice.html");
  document.body.innerHTML = loadPageBody("exercice.html");
  mockApi.practiceLoad.mockReset();
  mockApi.practiceLoad.mockImplementation((id) => Promise.resolve({ exercise: bank[id] }));
  mockApi.practiceResult.mockClear();
  vi.resetModules();
  await import("../exercice.js");
  await flushPromises();
}

async function answerCurrentQuestion() {
  $("ex-btn-yes").click();
  await flushPromises();
}

describe("exercice.js — progression d'une série « notion » (chatbot ET onglet Exercices)", () => {
  it("un pool de plusieurs exercices distincts : la question change à chaque étape, jamais de répétition", async () => {
    await mountExerciceWithPendingSeries([101, 102, 103]);

    const firstEnonce = $("ex-enonce").textContent;
    expect(["Question A", "Question B", "Question C"]).toContain(firstEnonce);
    const firstCallId = mockApi.practiceLoad.mock.calls[0][0];

    await answerCurrentQuestion();
    const secondEnonce = $("ex-enonce").textContent;
    const secondCallId = mockApi.practiceLoad.mock.calls[1][0];

    expect(secondCallId).not.toBe(firstCallId);
    expect(secondEnonce).not.toBe(firstEnonce);
  });

  it("conserve le chapitre et la notion transmis par la carte tout au long de la série", async () => {
    await mountExerciceWithPendingSeries([101, 102]);
    expect($("ex-chapter-badge").textContent).toBe("Chapitre_8");
    expect($("ex-notion-badge").textContent).toBe("Dérivées");

    await answerCurrentQuestion();
    expect($("ex-chapter-badge").textContent).toBe("Chapitre_8");
    expect($("ex-notion-badge").textContent).toBe("Dérivées");
  });

  it("practiceResult n'est appelé qu'une seule fois par question répondue (pas de double consommation)", async () => {
    await mountExerciceWithPendingSeries([101, 102, 103]);
    await answerCurrentQuestion();
    expect(mockApi.practiceResult).toHaveBeenCalledTimes(1);
  });

  it("RÉGRESSION CRITIQUE — un pool à UN SEUL exercice ne doit JAMAIS être répété pour remplir la série : la série est raccourcie à 1 question", async () => {
    // Reproduit exactement l'état transmis par chatbot.js::resultToCard
    // AVANT correction (un seul exercise_id) : exercice.js ne reçoit ici
    // qu'un pool d'1 id — à lui de ne pas fabriquer de fausse diversité.
    await mountExerciceWithPendingSeries([101]);

    expect($("ex-enonce").textContent).toBe("Question A");
    expect($("series-count").textContent).toBe("Question 1/1");

    await answerCurrentQuestion();

    // Avec l'ancien comportement (répétition jusqu'à SERIES_TOTAL=10), on
    // serait ici en "Question 2/10" avec le même énoncé "Question A" affiché
    // une seconde fois. Le comportement attendu : la série (réellement
    // longue d'un seul exercice distinct) se termine directement, sans
    // jamais recharger une deuxième fois le même exercice.
    expect(mockApi.practiceLoad).toHaveBeenCalledTimes(1);
    expect($("screen-recap").hidden).toBe(false);
    expect($("screen-ex").hidden).toBe(true);
    expect($("recap-score").textContent).toBe("1/1");
  });

  it("DONNÉES RÉELLES — série de 10 questions sur « Distributivité et identités remarquables » (Chapitre_3) : 10 énoncés distincts, jamais de répétition", async () => {
    // Pool réel construit exactement comme search_service.exercises_by_notion
    // le ferait côté backend (voir test_routage_reel_chatbot.py) : tous les
    // exercices de cette notion dans la vraie banque exercises_bank.json.
    const realPool = REAL_BANK.filter((e) => e.chapter_id === "Chapitre_3" && e.notion === "Distributivité et identités remarquables");
    expect(realPool.length).toBeGreaterThanOrEqual(10);
    const tenIds = realPool.slice(0, 10).map((e) => e.id);

    await mountExerciceWithPendingSeries(tenIds, {
      chapterId: "Chapitre_3",
      notion: "Distributivité et identités remarquables",
      bank: Object.fromEntries(REAL_BANK.map((e) => [e.id, { ...e, solution_steps: e.solution_steps || [] }])),
    });

    const seenEnonces = new Set();
    for (let i = 0; i < 10; i++) {
      const enonce = $("ex-enonce").textContent;
      expect(seenEnonces.has(enonce)).toBe(false);
      seenEnonces.add(enonce);
      if (i < 9) await answerCurrentQuestion();
    }
    await answerCurrentQuestion(); // 10e réponse -> fin de série
    expect(seenEnonces.size).toBe(10);
    expect(mockApi.practiceLoad).toHaveBeenCalledTimes(10);
    expect($("screen-recap").hidden).toBe(false);
    expect($("recap-score").textContent).toBe("10/10");
  });

  it("RÉGRESSION — un pool de DOUBLONS (mêmes ids répétés, comme une carte mal construite) ne produit jamais deux fois la même question", async () => {
    // [101, 102, 101, 103, 102] : 3 ids distincts seulement, transmis avec
    // des doublons (ex: fusion de deux pools qui se chevauchent).
    await mountExerciceWithPendingSeries([101, 102, 101, 103, 102]);

    const seen = new Set();
    for (let i = 0; i < 3; i++) {
      const enonce = $("ex-enonce").textContent;
      expect(seen.has(enonce)).toBe(false);
      seen.add(enonce);
      if (i < 2) await answerCurrentQuestion();
    }
    await answerCurrentQuestion(); // 3e réponse -> fin de série (3 ids distincts seulement)
    expect($("screen-recap").hidden).toBe(false);
    expect($("recap-score").textContent).toBe("3/3");
  });

  it("RÉGRESSION — un identifiant introuvable (404) au milieu du pool est retiré explicitement, sans planter la série ni répéter la question précédente", async () => {
    await mountExerciceWithPendingSeries([101, 102, 103]);
    const firstEnonce = $("ex-enonce").textContent;

    // buildSeriesPool() mélange l'ordre : l'exercice qui "disparaît" (404,
    // ex: supprimé de la banque depuis la construction du pool) est celui
    // qui serait chargé en 2e position, quel que soit son id réel — le test
    // ne doit dépendre d'aucun ordre précis de mélange, seulement du RANG
    // de l'appel.
    let loadCount = 0;
    mockApi.practiceLoad.mockImplementation((id) => {
      loadCount += 1;
      if (loadCount === 1) {
        const err = new Error("exercice inconnu");
        err.status = 404;
        return Promise.reject(err);
      }
      return Promise.resolve({ exercise: BANK[id] });
    });

    await answerCurrentQuestion(); // tente le 2e id (404, retiré), enchaîne automatiquement sur le 3e
    const secondEnonce = $("ex-enonce").textContent;
    expect(secondEnonce).not.toBe(firstEnonce);
    expect($("series-count").textContent).toBe("Question 2/2"); // série raccourcie à 2 ids distincts

    await answerCurrentQuestion();
    expect($("screen-recap").hidden).toBe(false);
    expect($("recap-score").textContent).toBe("2/2");
  });

  it("RÉGRESSION — carte sous une réponse du chatbot (build_cards) ET suggestion live transmettent toutes deux un pool exploitable jusqu'à 10 questions", async () => {
    // Reproduit les deux formes RÉELLES de payload lumis:pending_series,
    // telles qu'écrites par chatbot.js::navigateToCard pour les deux
    // origines possibles (voir chatbot.test.js pour la construction côté
    // frontend) : une fois le pool déjà posé en localStorage, exercice.js ne
    // fait plus aucune différence entre les deux — ce test vérifie que
    // cette garantie tient réellement pour une série de 10.
    const tenIds = [101, 102, 103, 104, 105, 106, 107, 108, 109, 110];
    const bigBank = Object.fromEntries(
      tenIds.map((id) => [id, { id, chapter_id: "Chapitre_3", notion: "Distributivité et identités remarquables", difficulty: 2, enonce: `Question ${id}`, hint: "", answer: "", solution_steps: [] }]),
    );
    await mountExerciceWithPendingSeries(tenIds, { chapterId: "Chapitre_3", notion: "Distributivité et identités remarquables", bank: bigBank });

    const seen = new Set();
    for (let i = 0; i < 10; i++) {
      seen.add($("ex-enonce").textContent);
      if (i < 9) await answerCurrentQuestion();
    }
    expect(seen.size).toBe(10);
    expect($("series-count").textContent).toBe("Question 10/10");
  });
});
