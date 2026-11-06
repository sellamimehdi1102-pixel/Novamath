// ── Moteur adaptatif sur les VRAIES banques servies des cinq classes ────────
// Les métadonnées (ids et difficultés par notion) sont la réponse réelle de
// /api/chapters, instantané produit par webapp/tests/dump_served_chapters.py --write
// (client de test Flask, lecture seule, sans compte ni quota). Le vrai exercice.js,
// adaptiveDifficulty.js et le vrai fichier de prérequis sont utilisés ; seuls le
// réseau et la page sont simulés. Aucune question n'est ajoutée aux banques.
import { describe, it, expect, vi, beforeAll, beforeEach, afterEach } from "vitest";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { loadPageBody, flushPromises } from "./testUtils.js";
import { DIFF_LABEL_SHORT } from "../difficultyLevels.js";

const mockApi = {
  practiceLoad: vi.fn(),
  practiceResult: vi.fn().mockResolvedValue({}),
  getQuota: vi.fn().mockResolvedValue({ exercises_daily: { used: 0, remaining: 50, limit: 50, unlimited: false } }),
  saveStats: vi.fn().mockResolvedValue({}),
  getStats: vi.fn().mockResolvedValue({}),
  chapters: vi.fn(),
};
vi.mock("../api.js", () => ({ api: mockApi }));
vi.mock("../settingsManager.js", () => ({
  initSettingsManager: () => Promise.resolve(),
  getSettings: () => ({ training: { questionsPerSeries: 10 }, learning: { dailyGoalExercises: 4 } }),
  onSettingsChange: vi.fn(),
}));
vi.mock("../settingsPopup.js", () => ({ bindSettingsButton: vi.fn() }));
vi.mock("../i18n.js", () => ({ bindLiveTranslations: vi.fn() }));
vi.mock("../mathrender.js", () => ({
  setMathContent: (el, text) => {
    el.textContent = text;
  },
  formatStepLabels: (s) => s,
}));
vi.mock("../animations.js", () => ({ fireConfetti: vi.fn(), shakeElement: vi.fn(), fadeInTransition: vi.fn() }));
vi.mock("../supportTicket.js", () => ({ openReportTicketPopup: vi.fn() }));

const HERE = dirname(fileURLToPath(import.meta.url));
const WEBAPP = resolve(HERE, "..", "..", "..");
const PREREQS = JSON.parse(readFileSync(resolve(WEBAPP, "static", "data", "notion_prerequisites.json"), "utf8"));
const CLASSES = ["quatrieme", "troisieme", "seconde", "premiere", "premiere_specifique"];
const $ = (id) => document.getElementById(id);

let META = {};
let INDEX = {}; // classe -> id -> {id, chapter, notion, difficulty}

beforeAll(() => {
  // Instantané versionné de la réponse réelle (le job frontend de la CI n'a pas
  // Python) ; webapp/tests/test_served_chapters_fixture.py garantit qu'il est
  // identique aux banques servies.
  META = JSON.parse(readFileSync(resolve(HERE, "fixtures", "served_chapters.json"), "utf8"));
  CLASSES.forEach((cl) => {
    INDEX[cl] = {};
    META[cl].forEach((ch) =>
      ch.notions_detail.forEach((n) =>
        n.exercise_ids.forEach((id, i) => {
          INDEX[cl][id] = { id, chapter: ch.id, notion: n.notion, difficulty: n.exercise_difficulties[i] };
        }),
      ),
    );
  });
}, 180_000);

let currentClass = "seconde";
let fetchMode = "ok";

async function mount(classLevel, pending, url = "/exercice.html") {
  currentClass = classLevel;
  localStorage.setItem("novamath:class_level", classLevel);
  if (pending) localStorage.setItem("lumis:pending_series", JSON.stringify(pending));
  window.history.pushState({}, "", url);
  document.body.innerHTML = loadPageBody("exercice.html");
  mockApi.practiceLoad.mockReset();
  mockApi.practiceLoad.mockImplementation((id) => {
    const e = INDEX[currentClass][id];
    return Promise.resolve({
      exercise: {
        id,
        chapter_id: e.chapter,
        notion: e.notion,
        difficulty: e.difficulty,
        enonce: `#${id}`,
        hint: "",
        answer: "",
        solution_steps: [],
      },
    });
  });
  mockApi.chapters.mockReset();
  mockApi.chapters.mockResolvedValue({ chapters_meta: META[classLevel] });
  vi.resetModules();
  await import("../exercice.js");
  await flushPromises();
}

const servedIds = () => mockApi.practiceLoad.mock.calls.map((c) => c[0]);
const served = () => servedIds().map((id) => INDEX[currentClass][id].difficulty);
const badge = () => $("ex-difficulty-badge").textContent;
async function answer(ok) {
  // La difficulté affichée est celle de la question réellement posée.
  const id = servedIds().at(-1);
  expect(badge()).toContain(DIFF_LABEL_SHORT[INDEX[currentClass][id].difficulty]);
  $(ok ? "ex-btn-yes" : "ex-btn-no").click();
  await flushPromises();
}
async function answers(list) {
  for (const ok of list) await answer(ok);
}
const local = () => JSON.parse(localStorage.getItem("lumis:stats") || "{}").history || [];

function notionsOf(classLevel) {
  return META[classLevel].flatMap((ch) =>
    ch.notions_detail.map((n) => ({
      chapter: ch.id,
      notion: n.notion,
      key: `${ch.id}|${n.notion}`,
      ids: n.exercise_ids,
      levels: [...new Set(n.exercise_difficulties)].sort(),
    })),
  );
}
const maxLevel = (cl) => (cl === "quatrieme" || cl === "premiere_specifique" ? 4 : 5);
/** Notion couvrant toute l'échelle de la classe (et rien au-delà). */
function fullNotion(cl, skip = []) {
  const top = maxLevel(cl);
  return notionsOf(cl).find(
    (n) => !skip.includes(n.key) && n.levels.join() === [...Array(top)].map((_, i) => i + 1).join(),
  );
}
/** Toutes les questions de `level` de la notion ont-elles été servies avant la position `i` ? */
const exhaustedBefore = (n, level, i) =>
  n.ids
    .filter((id) => INDEX[currentClass][id].difficulty === level)
    .every((id) => servedIds().slice(0, i).includes(id));
const nearest = (levels, v) => levels.reduce((b, d) => (Math.abs(d - v) < Math.abs(b - v) ? d : b), levels[0]);
const seriesFor = (n) => ({
  mode: "notion",
  chapterId: n.chapter,
  notion: n.notion,
  notions: [n.notion],
  exerciseIds: n.ids.slice(0, 3),
});
/** Relation de prérequis : de préférence entre deux chapitres différents. */
function relationOf(cl) {
  const rel = Object.entries(PREREQS[cl] || {});
  const keys = new Set(notionsOf(cl).map((n) => n.key));
  const ok = rel.filter(([k, ps]) => keys.has(k) && keys.has(ps[0]));
  const pick = ok.find(([k, ps]) => k.split("|")[0] !== ps[0].split("|")[0]) || ok[0];
  if (!pick) return null;
  const find = (key) => notionsOf(cl).find((n) => n.key === key);
  return { dependent: find(pick[0]), prereq: find(pick[1][0]) };
}

beforeEach(() => {
  localStorage.clear();
  sessionStorage.clear();
  mockApi.saveStats.mockClear();
  fetchMode = "ok";
  vi.stubGlobal(
    "fetch",
    vi.fn((url) =>
      fetchMode === "ok" && String(url).endsWith("/data/notion_prerequisites.json")
        ? Promise.resolve({ ok: true, json: () => Promise.resolve(PREREQS) })
        : Promise.reject(new Error("réseau indisponible")),
    ),
  );
});
afterEach(() => {
  vi.unstubAllGlobals();
  mockApi.getStats.mockReset().mockResolvedValue({});
});

describe.each(CLASSES)("classe %s — banque réellement servie", (cl) => {
  it("nouvel élève : calibration rapide (Fondamental, Avancé, plus haut niveau), puis montée sans retour en arrière", async () => {
    const n = fullNotion(cl);
    expect(n, "notion couvrant toute l'échelle").toBeTruthy();
    await mount(cl, seriesFor(n));
    await answers(Array(6).fill(true));
    const s = served();
    expect(s.slice(0, 3)).toEqual([1, 3, nearest(n.levels, 5)]);
    // Jamais de recul après une réussite, sauf si le niveau atteint est épuisé dans
    // la série (banque réelle : parfois 4 questions seulement au niveau le plus haut).
    s.forEach((d, i) => {
      if (i > 0 && d < s[i - 1]) expect(exhaustedBefore(n, s[i - 1], i)).toBe(true);
    });
    expect(new Set(servedIds()).size).toBe(servedIds().length);
  });

  it("élève en difficulté : reste sur des questions accessibles ; descente effective après des erreurs", async () => {
    const n = fullNotion(cl);
    await mount(cl, seriesFor(n));
    await answers([false, false, false, false]);
    // Toujours Fondamental tant qu'il reste une question Fondamental inédite dans la série.
    served().forEach((d, i) => {
      if (d > 1) expect(exhaustedBefore(n, 1, i)).toBe(true);
    });
    localStorage.clear();
    await mount(cl, seriesFor(n));
    await answers([true, true, true, false, false, false, false]);
    const s = served();
    expect(s.at(-1)).toBeLessThan(Math.max(...s));
  });

  it("élève confirmé : une erreur isolée ne le fait pas redescendre", async () => {
    const n = fullNotion(cl);
    await mount(cl, seriesFor(n));
    await answers([true, true, true, true, true, false]);
    expect(served().at(-1)).toBeGreaterThanOrEqual(maxLevel(cl) - 1);
  });

  it("série suivante, rechargement et second navigateur : acquis conservés, aucune recalibration, aucun doublon synchronisé", async () => {
    const n = fullNotion(cl);
    await mount(cl, seriesFor(n));
    await answers(Array(5).fill(true));
    const reached = served().at(-1);
    // Rechargement (F5) : même question, sans nouvelle consommation.
    await mount(cl, null, "/exercice.html?resume=1");
    expect(mockApi.practiceLoad).not.toHaveBeenCalled();
    // Nouvelle série sur la même notion : repart du niveau acquis.
    localStorage.removeItem("lumis:series_in_progress");
    await mount(cl, seriesFor(n));
    const firstNext = served()[0];
    expect(firstNext).toBeGreaterThanOrEqual(reached - 1);
    // Second navigateur : historique du serveur, même état, même difficulté.
    const synced = mockApi.saveStats.mock.calls.at(-1)[0].history;
    const keys = synced.map((h) => `${h.id}@${h.ts}`);
    expect(new Set(keys).size).toBe(keys.length);
    expect(synced.filter((h) => h.notion === n.notion)).toHaveLength(5);
    localStorage.clear();
    mockApi.getStats.mockResolvedValue({ history: synced });
    await mount(cl, seriesFor(n));
    expect(served()[0]).toBe(firstNext);
  });

  it("série sur deux notions : chaque notion se calibre indépendamment", async () => {
    const a = fullNotion(cl);
    const b = fullNotion(cl, [a.key]);
    expect(b).toBeTruthy();
    await mount(cl, {
      mode: "notion",
      chapterId: a.chapter,
      notion: a.notion,
      notions: [a.notion, b.notion],
      exerciseIds: [...a.ids.slice(0, 2), ...b.ids.slice(0, 2)],
    });
    await answers(Array(6).fill(true));
    const byNotion = (key) =>
      servedIds()
        .map((id) => INDEX[cl][id])
        .filter((e) => `${e.chapter}|${e.notion}` === key)
        .map((e) => e.difficulty);
    expect(byNotion(a.key).slice(0, 3)).toEqual([1, 3, nearest(a.levels, 5)]);
    expect(byNotion(b.key).slice(0, 3)).toEqual([1, 3, nearest(b.levels, 5)]);
  });

  it("niveau épuisé : repli sur le niveau disponible le plus proche, sans répéter une question", async () => {
    const n = fullNotion(cl);
    const top = n.ids.filter((id) => INDEX[cl][id].difficulty === nearest(n.levels, 5)).length;
    await mount(cl, seriesFor(n));
    await answers(Array(9).fill(true));
    expect(new Set(servedIds()).size).toBe(10);
    const atTop = served().filter((d) => d === nearest(n.levels, 5)).length;
    expect(atTop).toBeLessThanOrEqual(top);
    expect(served().every((d) => n.levels.includes(d))).toBe(true);
  });

  it("changement de notion / de chapitre : prérequis maîtrisé -> départ prudent au-dessus de Fondamental ; sans relation -> Fondamental", async () => {
    const rel = relationOf(cl);
    if (cl === "quatrieme" || cl === "troisieme") {
      // Aucune relation renseignée : aucune n'est inventée.
      expect(rel).toBeNull();
      const a = fullNotion(cl);
      const b = notionsOf(cl).find((x) => x.chapter !== a.chapter && x.levels.includes(1));
      await mount(cl, seriesFor(a));
      await answers(Array(5).fill(true));
      localStorage.removeItem("lumis:series_in_progress");
      await mount(cl, seriesFor(b));
      expect(served()[0]).toBe(1); // une seule notion travaillée : pas de profil général
      return;
    }
    expect(rel).toBeTruthy();
    await mount(cl, seriesFor(rel.prereq));
    await answers(Array(5).fill(true));
    localStorage.removeItem("lumis:series_in_progress");
    await mount(cl, seriesFor(rel.dependent));
    const start = served()[0];
    expect(start).toBeGreaterThan(1);
    expect(start).toBeLessThanOrEqual(3); // estimation initiale prudente
    // Les réponses propres prennent vite le dessus : deux erreurs suffisent à redescendre.
    await answers([false, false]);
    expect(served().at(-1)).toBeLessThanOrEqual(start - 1);

    // Sans fichier de prérequis (réseau indisponible) : repli actuel, Fondamental.
    const history = local();
    localStorage.clear();
    fetchMode = "fail";
    mockApi.getStats.mockResolvedValue({
      history: history.filter((h) => h.notion === rel.prereq.notion && h.chapter === rel.prereq.chapter),
    });
    await mount(cl, seriesFor(rel.dependent));
    expect(served()[0]).toBe(1);
  });

  it("notion déjà travaillée : son historique personnel l'emporte sur un prérequis maîtrisé", async () => {
    const rel = relationOf(cl);
    if (!rel) return;
    const t0 = 1_000;
    const mk = (n, d, ok, i) => ({
      id: n.ids[i],
      ts: t0 + i,
      date: "2026-10-30",
      chapter: n.chapter,
      notion: n.notion,
      difficulty: d,
      correct: ok,
      class_level: cl,
    });
    const prereqIds = rel.prereq.ids.filter((id) => INDEX[cl][id].difficulty >= 3);
    const strong = prereqIds
      .slice(0, 5)
      .map((id, i) => ({ ...mk(rel.prereq, INDEX[cl][id].difficulty, true, 0), id, ts: t0 + 10 + i }));
    const depLow = rel.dependent.ids.filter((id) => INDEX[cl][id].difficulty === 1);
    const weak = depLow.slice(0, 3).map((id, i) => ({ ...mk(rel.dependent, 1, false, 0), id, ts: t0 + 100 + i }));
    mockApi.getStats.mockResolvedValue({ history: [...strong, ...weak] });
    await mount(cl, seriesFor(rel.dependent));
    expect(served()[0]).toBe(1);
  });
});

// ── Bloc de calibration (ordonnancement des séries multi-notions) ───────────
// Vrai exercice.js + vraie banque de chaque classe : une notion NOUVELLE reçoit
// ses deux premières questions à la suite (la 2e choisie après la 1re réponse),
// puis l'alternance habituelle reprend. Les difficultés restent celles du moteur.
describe.each(CLASSES)("classe %s — bloc de calibration des notions nouvelles", (cl) => {
  /** Trois notions d'un même chapitre proposant au moins Fondamental et Avancé. */
  function threeNotions() {
    const byChapter = new Map();
    notionsOf(cl)
      .filter((n) => n.levels.includes(1) && n.levels.includes(3) && n.ids.length >= 8)
      .forEach((n) => byChapter.set(n.chapter, [...(byChapter.get(n.chapter) || []), n]));
    return [...byChapter.values()].find((list) => list.length >= 3).slice(0, 3);
  }
  const multi = (list) => ({
    mode: "notion",
    chapterId: list[0].chapter,
    notion: list.map((n) => n.notion).join(" + "),
    notions: list.map((n) => n.notion),
    exerciseIds: list.flatMap((n) => n.ids.slice(0, 2)),
  });
  const letters = (list) =>
    servedIds()
      .map((id) => INDEX[cl][id])
      .map((e) => "ABC"[list.findIndex((n) => n.key === `${e.chapter}|${e.notion}`)])
      .join("");

  it("trois notions nouvelles, dix réussites : A, A, B, B, C, C puis alternance ; montée dès la 2e question", async () => {
    const list = threeNotions();
    await mount(cl, multi(list));
    await answers(Array(10).fill(true));
    expect(letters(list)).toBe("AABBCCABCA");
    expect(served().slice(0, 6)).toEqual([1, 3, 1, 3, 1, 3]);
    expect(new Set(servedIds()).size).toBe(10);
    expect(Math.max(...served())).toBeLessThanOrEqual(maxLevel(cl));
  });

  it("réussite puis échec dans le bloc : le moteur redescend normalement", async () => {
    const list = threeNotions();
    await mount(cl, multi(list));
    await answers([true, false, true, true, true, true, true]);
    expect(letters(list).slice(0, 6)).toBe("AABBCC");
    // 3e question de A (après 1 réussi puis 3 échoué) : jamais au-dessus de 2.
    expect(served()[6]).toBeLessThanOrEqual(2);
  });

  it("rechargement après la 1re question d'un bloc, puis nouvelle série : bloc conservé, puis plus de regroupement", async () => {
    const list = threeNotions();
    await mount(cl, multi(list));
    await answers([true, true, true]); // A, A, B : la 2e question de B est affichée
    const before = servedIds().slice();
    await mount(cl, null, "/exercice.html?resume=1");
    expect(mockApi.practiceLoad).not.toHaveBeenCalled(); // même question, aucune consommation
    // Question réaffichée depuis la sauvegarde (2e de B) : on y répond directement.
    expect(badge()).toContain(DIFF_LABEL_SHORT[INDEX[cl][before.at(-1)].difficulty]);
    $("ex-btn-yes").click();
    await flushPromises();
    await answers(Array(6).fill(true));
    const all = [...before, ...servedIds()];
    expect(new Set(all).size).toBe(all.length);
    const seq = all
      .map((id) => INDEX[cl][id])
      .map((e) => "ABC"[list.findIndex((n) => n.key === `${e.chapter}|${e.notion}`)])
      .join("");
    expect(seq).toBe("AABBCCABCA");
    // Nouvelle série sur les mêmes notions : notions connues, aucun bloc de deux
    // (pas de recalibration), répartition selon le besoin, acquis conservés.
    localStorage.removeItem("lumis:series_in_progress");
    await mount(cl, multi(list));
    await answers(Array(5).fill(true));
    expect(letters(list).slice(0, 3)).toBe("ABC");
    expect(letters(list)).not.toMatch(/(.)\1/);
    expect(Math.min(...served())).toBeGreaterThanOrEqual(3);
  });
});

// ── Répartition du nombre de questions selon le besoin (vrai exercice.js) ───
// La réponse dépend de la notion de la question RÉELLEMENT affichée : le
// nombre de questions par notion résulte des résultats, pas d'un ordre fixé.
describe.each(CLASSES)("classe %s — répartition des questions selon le besoin", (cl) => {
  function threeNotions() {
    const byChapter = new Map();
    notionsOf(cl)
      .filter((n) => n.levels.includes(1) && n.levels.includes(3) && n.ids.length >= 12)
      .forEach((n) => byChapter.set(n.chapter, [...(byChapter.get(n.chapter) || []), n]));
    return [...byChapter.values()].find((list) => list.length >= 3).slice(0, 3);
  }
  async function playSeries(list, outcomeOf) {
    await mount(cl, {
      mode: "notion",
      chapterId: list[0].chapter,
      notion: list.map((n) => n.notion).join(" + "),
      notions: list.map((n) => n.notion),
      exerciseIds: list.flatMap((n) => n.ids.slice(0, 2)),
    });
    const seen = { A: 0, B: 0, C: 0 };
    for (let i = 0; i < 10; i++) {
      const e = INDEX[cl][servedIds().at(-1)];
      const letter = "ABC"[list.findIndex((n) => n.key === `${e.chapter}|${e.notion}`)];
      await answer(outcomeOf(letter, seen[letter]++));
    }
    return seen;
  }
  const scenario = (a, b) => (l, k) => ({ A: a, B: b, C: (j) => j % 2 === 0 })[l](k);

  it("A réussit, B échoue : B reçoit plus de questions que A ; résultats inversés -> répartition inversée", async () => {
    const list = threeNotions();
    const first = await playSeries(
      list,
      scenario(
        () => true,
        () => false,
      ),
    );
    localStorage.clear();
    const second = await playSeries(
      list,
      scenario(
        () => false,
        () => true,
      ),
    );
    expect(first.B).toBeGreaterThan(first.A);
    expect(second.A).toBeGreaterThan(second.B);
    expect([second.A, second.B, second.C]).toEqual([first.B, first.A, first.C]);
    expect(first.A + first.B + first.C).toBe(10);
  });
});
