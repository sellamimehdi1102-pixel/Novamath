// ── Parcours réel (vraie banque Seconde) : sélection -> affichage -> réponse ->
// enregistrement -> sélection suivante, via exercice.js et le DOM de
// exercice.html. Complète exercice-adaptive.test.js (banque synthétique). ────
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
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

const $ = (id) => document.getElementById(id);

// Vraie banque : mêmes regroupements chapitre/notion que /api/chapters.
const BANK_FILE = [
  resolve(process.cwd(), "exercises_bank.json"),
  resolve(process.cwd(), "..", "exercises_bank.json"),
].find((f) => existsSync(f));
const RAW = JSON.parse(readFileSync(BANK_FILE, "utf8"));
const BANK = {};
const GROUPS = new Map();
RAW.forEach((e, i) => {
  const ex = { ...e, id: e.id ?? i };
  BANK[ex.id] = ex;
  if (!GROUPS.has(ex.chapter_id)) GROUPS.set(ex.chapter_id, new Map());
  const notions = GROUPS.get(ex.chapter_id);
  if (!notions.has(ex.notion)) notions.set(ex.notion, []);
  notions.get(ex.notion).push(ex.id);
});
const CHAPTERS_META = [...GROUPS].map(([id, notions]) => ({
  id,
  title: id,
  notions_detail: [...notions].map(([notion, ids]) => ({
    notion,
    exercise_ids: ids,
    exercise_difficulties: ids.map((x) => BANK[x].difficulty),
  })),
}));
const CHAPTER = CHAPTERS_META.find(
  (c) => c.notions_detail.length >= 3 && c.notions_detail.every((n) => n.exercise_ids.length >= 12),
);
const NOTIONS = CHAPTER.notions_detail;
const levelsOf = (n) => [...new Set(n.exercise_difficulties)].sort();

async function mountExercice(pending) {
  if (pending) localStorage.setItem("lumis:pending_series", JSON.stringify(pending));
  window.history.pushState({}, "", "/exercice.html");
  document.body.innerHTML = loadPageBody("exercice.html");
  mockApi.practiceLoad.mockReset();
  mockApi.practiceLoad.mockImplementation((id) => Promise.resolve({ exercise: BANK[id] }));
  mockApi.chapters.mockReset();
  mockApi.chapters.mockResolvedValue({ chapters_meta: CHAPTERS_META });
  vi.resetModules();
  await import("../exercice.js");
  await flushPromises();
}
const shown = () =>
  mockApi.practiceLoad.mock.calls.map((c) => ({ notion: BANK[c[0]].notion, d: BANK[c[0]].difficulty }));
const seriesFor = (notions) => ({
  mode: "notion",
  chapterId: CHAPTER.id,
  notion: notions.map((n) => n.notion).join(" + "),
  notions: notions.map((n) => n.notion),
  exerciseIds: notions.flatMap((n) => n.exercise_ids.slice(0, 3)),
});
async function answer(correct) {
  $(correct ? "ex-btn-yes" : "ex-btn-no").click();
  await flushPromises();
}
beforeEach(() => {
  localStorage.clear();
  sessionStorage.clear();
});
afterEach(() => mockApi.getStats.mockReset().mockResolvedValue({}));

const ids = () => mockApi.practiceLoad.mock.calls.map((c) => c[0]);
// Série complète : la dernière réponse termine la série (écran récap).
async function runSeries(pending, outcomes) {
  await mountExercice(pending);
  for (const ok of outcomes) await answer(ok);
  return shown();
}
const T10 = Array(10).fill(true);
const rec = (n, list, ts0) =>
  list.map(([k, ok], j) => ({
    id: n.exercise_ids.filter((x) => BANK[x].difficulty === k)[j % 8],
    ts: ts0 + j,
    date: "2026-10-01",
    chapter: CHAPTER.id,
    notion: n.notion,
    difficulty: k,
    correct: ok,
    class_level: "seconde",
  }));

describe("parcours réel (vraie banque Seconde) : sélection -> affichage -> réponse -> sélection suivante", () => {
  it("10 bonnes réponses, notion à 5 niveaux : Fondamental, Avancé, Défi puis niveaux élevés, sans retour en arrière", async () => {
    expect(levelsOf(NOTIONS[0])).toEqual([1, 2, 3, 4, 5]);
    await mountExercice(seriesFor([NOTIONS[0]]));
    const badges = [$("ex-difficulty-badge").textContent];
    for (let i = 0; i < 9; i++) {
      await answer(true);
      badges.push($("ex-difficulty-badge")?.textContent ?? "");
    }
    const d = shown().map((x) => x.d);
    expect(d.slice(0, 3)).toEqual([1, 3, 5]);
    expect(Math.min(...d.slice(2, 8))).toBeGreaterThanOrEqual(4);
    // Niveau affiché = difficulté de la vraie question posée.
    d.forEach((level, i) => expect(badges[i]).toContain(DIFF_LABEL_SHORT[level]));
    // Aucune question répétée dans la série.
    expect(new Set(ids()).size).toBe(ids().length);
  });

  it("série suivante : acquis conservés (pas de recalibration), pool épuisé -> repli sans perte de maîtrise", async () => {
    await runSeries(seriesFor([NOTIONS[0]]), T10);
    localStorage.removeItem("lumis:in_progress_series");
    const second = (await runSeries(seriesFor([NOTIONS[0]]), T10)).map((x) => x.d);
    expect(Math.min(...second.slice(0, 8))).toBeGreaterThanOrEqual(4);
    expect(new Set(ids()).size).toBe(ids().length);
    // Les 8 questions de niveau 5 sont déjà servies/épuisées : repli sur 4, jamais sur Fondamental.
    expect(Math.min(...second)).toBeGreaterThanOrEqual(4);
    const third = (await runSeries(seriesFor([NOTIONS[0]]), [true, true])).map((x) => x.d);
    expect(third[0]).toBeGreaterThanOrEqual(4);
  });

  it("erreurs répétées après une bonne série : descente cohérente, jamais de saut au hasard", async () => {
    const d = (await runSeries(seriesFor([NOTIONS[0]]), [...Array(3).fill(true), ...Array(7).fill(false)])).map(
      (x) => x.d,
    );
    expect(d[d.length - 1]).toBeLessThan(d[2]);
    d.slice(3).forEach((level, i, tail) => i && expect(level).toBeLessThanOrEqual(tail[i - 1]));
  });

  it("série mélangeant plusieurs notions : chaque notion garde sa propre calibration indépendante", async () => {
    const shownList = await runSeries(seriesFor(NOTIONS.slice(0, 3)), T10);
    const by = new Map();
    shownList.forEach((x) => by.set(x.notion, [...(by.get(x.notion) || []), x.d]));
    expect(by.size).toBe(3);
    by.forEach((levels) => {
      expect(levels[0]).toBe(1);
      expect(levels[1]).toBe(3);
      levels.slice(1).forEach((level, i) => expect(level).toBeGreaterThanOrEqual(levels[i]));
    });
  });

  it("Révisions : chaque notion travaillée reprend SON niveau (pas de réinitialisation, pas de niveau global)", async () => {
    const hist = [
      ...rec(
        NOTIONS[0],
        [
          [1, false],
          [1, false],
          [1, false],
          [1, true],
        ],
        1,
      ),
      ...rec(
        NOTIONS[1],
        [
          [1, true],
          [3, true],
          [5, true],
          [5, true],
        ],
        10,
      ),
      ...rec(
        NOTIONS[2],
        [
          [1, true],
          [3, true],
          [3, false],
          [2, true],
        ],
        20,
      ),
    ];
    mockApi.getStats.mockResolvedValue({ history: hist });
    await mountExercice(null);
    document.querySelector('[data-mode="revisions"]').click();
    await flushPromises();
    for (let i = 0; i < 8; i++) await answer(true);
    const by = new Map();
    shown().forEach((x) => by.set(x.notion, [...(by.get(x.notion) || []), x.d]));
    const strong = by.get(NOTIONS[1].notion);
    const weak = by.get(NOTIONS[0].notion);
    expect(Math.min(...strong)).toBeGreaterThanOrEqual(4); // notion solide : jamais ramenée à Fondamental
    expect(weak[0]).toBeLessThanOrEqual(2); // notion fragile : niveaux accessibles
    by.forEach((levels) => levels.slice(1).forEach((level, i) => expect(level).toBeGreaterThanOrEqual(levels[i] - 1)));
    expect(new Set(ids()).size).toBe(ids().length);
  });

  it("chapitre entier depuis l'onglet Questions, historique hétérogène : aucune notion ne recule après une réussite", async () => {
    // Historique varié (notions déjà travaillées, partiellement ou en échec) :
    // les niveaux affichés alternent selon les notions, mais chaque notion
    // progresse ou se maintient après chaque bonne réponse.
    const hist = [
      ...rec(
        NOTIONS[0],
        [
          [1, true],
          [2, true],
          [3, true],
          [4, true],
          [5, true],
        ],
        1,
      ),
      ...rec(
        NOTIONS[1],
        [
          [1, true],
          [2, true],
        ],
        10,
      ),
      ...rec(NOTIONS[2], [[1, false]], 20),
    ];
    mockApi.getStats.mockResolvedValue({ history: hist });
    const all = { ...seriesFor(NOTIONS), exerciseIds: NOTIONS.flatMap((n) => n.exercise_ids) };
    const list = await runSeries(all, T10);
    const by = new Map();
    list.forEach((x) => by.set(x.notion, [...(by.get(x.notion) || []), x.d]));
    by.forEach((levels) => levels.slice(1).forEach((level, i) => expect(level).toBeGreaterThanOrEqual(levels[i])));
    expect(by.get(NOTIONS[1].notion)[0]).toBe(4); // sondage après 2 réussites (1, 2)
    expect(by.get(NOTIONS[1].notion)[1]).toBeGreaterThanOrEqual(4); // plus de retour en 3
  });

  it("un niveau indisponible (pool restreint) ne fait pas perdre de maîtrise : la série suivante ne repart pas plus bas", async () => {
    // Pool d'une notion réduit à ses niveaux 1 à 3 : repli sur 3, puis la banque complète redonne 4-5.
    const low = { ...NOTIONS[0], exercise_ids: NOTIONS[0].exercise_ids.filter((x) => BANK[x].difficulty <= 3) };
    CHAPTERS_META[CHAPTERS_META.indexOf(CHAPTER)].notions_detail[0] = {
      ...NOTIONS[0],
      exercise_ids: low.exercise_ids,
      exercise_difficulties: low.exercise_ids.map((x) => BANK[x].difficulty),
    };
    try {
      const d = (await runSeries(seriesFor([low]), T10)).map((x) => x.d);
      expect(Math.max(...d)).toBe(3);
      expect(d.slice(2, 6).every((x) => x === 3)).toBe(true);
    } finally {
      CHAPTERS_META[CHAPTERS_META.indexOf(CHAPTER)].notions_detail[0] = NOTIONS[0];
    }
    localStorage.removeItem("lumis:in_progress_series");
    expect((await runSeries(seriesFor([NOTIONS[0]]), [true])).map((x) => x.d)[0]).toBeGreaterThanOrEqual(3);
  });
});
