// ── Moteur adaptatif sur les VRAIES banques servies des cinq classes ────────
// Les métadonnées (ids et difficultés par notion) sont la réponse réelle de
// /api/chapters, obtenue par webapp/tests/dump_served_chapters.py (client de test
// Flask, lecture seule, sans compte ni quota). Le vrai exercice.js,
// adaptiveDifficulty.js et le vrai fichier de prérequis sont utilisés ; seuls le
// réseau et la page sont simulés. Aucune question n'est ajoutée aux banques.
import { describe, it, expect, vi, beforeAll, beforeEach, afterEach } from "vitest";
import { execFileSync } from "node:child_process";
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
  META = JSON.parse(
    execFileSync("python", [resolve(WEBAPP, "tests", "dump_served_chapters.py")], {
      cwd: WEBAPP,
      maxBuffer: 256 * 1024 * 1024,
      stdio: ["ignore", "pipe", "ignore"],
    }).toString("utf8"),
  );
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
      exercise: { id, chapter_id: e.chapter, notion: e.notion, difficulty: e.difficulty, enonce: `#${id}`, hint: "", answer: "", solution_steps: [] },
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
  return notionsOf(cl).find((n) => !skip.includes(n.key) && n.levels.join() === [...Array(top)].map((_, i) => i + 1).join());
}
/** Toutes les questions de `level` de la notion ont-elles été servies avant la position `i` ? */
const exhaustedBefore = (n, level, i) =>
  n.ids.filter((id) => INDEX[currentClass][id].difficulty === level).every((id) => servedIds().slice(0, i).includes(id));
const nearest = (levels, v) => levels.reduce((b, d) => (Math.abs(d - v) < Math.abs(b - v) ? d : b), levels[0]);
const seriesFor = (n) => ({ mode: "notion", chapterId: n.chapter, notion: n.notion, notions: [n.notion], exerciseIds: n.ids.slice(0, 3) });
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
    const byNotion = (key) => servedIds().map((id) => INDEX[cl][id]).filter((e) => `${e.chapter}|${e.notion}` === key).map((e) => e.difficulty);
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
    mockApi.getStats.mockResolvedValue({ history: history.filter((h) => h.notion === rel.prereq.notion && h.chapter === rel.prereq.chapter) });
    await mount(cl, seriesFor(rel.dependent));
    expect(served()[0]).toBe(1);
  });

  it("notion déjà travaillée : son historique personnel l'emporte sur un prérequis maîtrisé", async () => {
    const rel = relationOf(cl);
    if (!rel) return;
    const t0 = 1_000;
    const mk = (n, d, ok, i) => ({ id: n.ids[i], ts: t0 + i, date: "2026-10-30", chapter: n.chapter, notion: n.notion, difficulty: d, correct: ok, class_level: cl });
    const prereqIds = rel.prereq.ids.filter((id) => INDEX[cl][id].difficulty >= 3);
    const strong = prereqIds.slice(0, 5).map((id, i) => ({ ...mk(rel.prereq, INDEX[cl][id].difficulty, true, 0), id, ts: t0 + 10 + i }));
    const depLow = rel.dependent.ids.filter((id) => INDEX[cl][id].difficulty === 1);
    const weak = depLow.slice(0, 3).map((id, i) => ({ ...mk(rel.dependent, 1, false, 0), id, ts: t0 + 100 + i }));
    mockApi.getStats.mockResolvedValue({ history: [...strong, ...weak] });
    await mount(cl, seriesFor(rel.dependent));
    expect(served()[0]).toBe(1);
  });
});
