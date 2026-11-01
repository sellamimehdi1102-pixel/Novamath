// ── Non-régression : séquence observée sur le serveur local (Première,
// Chapitre 3 — « Fonction dérivée », une seule notion) puis reprise, avec le
// vrai exercice.js, adaptiveDifficulty.js et la vraie banque. ───────────────
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { loadPageBody, flushPromises } from "./testUtils.js";
import { notionMastery } from "../adaptiveDifficulty.js";

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

// Banque Première telle que servie par le serveur : banque principale + exercices générés.
const readBank = (name) =>
  JSON.parse(
    readFileSync(
      [resolve(process.cwd(), name), resolve(process.cwd(), "..", name)].find((f) => existsSync(f)),
      "utf8",
    ),
  );
const BANK = {};
[...readBank("exercises_bank_premiere.json"), ...readBank("exercises_generated_premiere.json")].forEach((e) => {
  BANK[e.id] = e;
});
const CH = "Chapitre_3";
const NOTION = "Fonction dérivée";
const CHAPTERS_META = [
  {
    id: CH,
    title: "Chapitre 3",
    notions_detail: [
      ...new Set(
        Object.values(BANK)
          .filter((e) => e.chapter_id === CH)
          .map((e) => e.notion),
      ),
    ].map((notion) => {
      const ids = Object.values(BANK)
        .filter((e) => e.chapter_id === CH && e.notion === notion)
        .map((e) => e.id);
      return { notion, exercise_ids: ids, exercise_difficulties: ids.map((x) => BANK[x].difficulty) };
    }),
  },
];
const ND = CHAPTERS_META[0].notions_detail.find((n) => n.notion === NOTION);
const SERIES = {
  mode: "notion",
  chapterId: CH,
  notion: NOTION,
  notions: [NOTION],
  exerciseIds: ND.exercise_ids.slice(0, 3),
};

async function mount(pending, url = "/exercice.html") {
  if (pending) localStorage.setItem("lumis:pending_series", JSON.stringify(pending));
  localStorage.setItem("novamath:class_level", "premiere");
  window.history.pushState({}, "", url);
  document.body.innerHTML = loadPageBody("exercice.html");
  mockApi.practiceLoad.mockReset();
  mockApi.practiceLoad.mockImplementation((id) => Promise.resolve({ exercise: BANK[id] }));
  mockApi.chapters.mockReset();
  mockApi.chapters.mockResolvedValue({ chapters_meta: CHAPTERS_META });
  vi.resetModules();
  await import("../exercice.js");
  await flushPromises();
}
const posed = () => mockApi.practiceLoad.mock.calls.map((c) => BANK[c[0]].difficulty);
const badge = () => $("ex-difficulty-badge").textContent;
async function answer(ok) {
  $(ok ? "ex-btn-yes" : "ex-btn-no").click();
  await flushPromises();
}
const local = () => JSON.parse(localStorage.getItem("lumis:stats")).history;
const mastery = (h) =>
  notionMastery(
    h.filter((e) => e.class_level === "premiere"),
    CH,
    NOTION,
  );
// Historique antérieur réel de la notion (1 ✓, 3 ✓, 5 ✓) : c'est lui qui fait démarrer en Défi.
const PRIOR = [1, 3, 5].map((d, i) => ({
  id: ND.exercise_ids.find((x) => BANK[x].difficulty === d),
  ts: 1000 + i,
  date: "2026-10-30",
  chapter: CH,
  notion: NOTION,
  difficulty: d,
  correct: true,
  mode: "notion",
  class_level: "premiere",
}));

beforeEach(() => {
  localStorage.clear();
  sessionStorage.clear();
  mockApi.saveStats.mockClear();
});
afterEach(() => mockApi.getStats.mockReset().mockResolvedValue({}));

describe("Fonction dérivée : séquence des captures, reprise et série suivante", () => {
  it("Défi ✓, puis 8 erreurs : descente Défi -> Difficile -> Avancé, état identique après rechargement, nouvelle série et second navigateur", async () => {
    mockApi.getStats.mockResolvedValue({ history: PRIOR });
    await mount(SERIES);
    await answer(true);
    for (let i = 0; i < 8; i++) await answer(false);
    // Banque réelle (recalibrée au chantier 2) : la notion ne compte que 4 questions
    // Défi, dont une déjà vue dans l'historique. Après les 3 Défi inédites, le moteur
    // se replie sur le niveau disponible le plus proche (Difficile), sans répéter de
    // question ; la descente reste monotone jusqu'à Avancé.
    const unseenDefi = ND.exercise_ids.filter((x) => BANK[x].difficulty === 5 && !PRIOR.some((h) => h.id === x)).length;
    expect(unseenDefi).toBe(3);
    expect(posed()).toEqual([5, 5, 5, 4, 4, 4, 4, 3, 3, 3]);
    const servedIds = mockApi.practiceLoad.mock.calls.map((c) => c[0]);
    expect(new Set(servedIds).size).toBe(servedIds.length);
    expect(posed().every((d, i, s) => i === 0 || d <= s[i - 1])).toBe(true);
    expect(badge()).toContain("Avancé");
    const endOfSeries = mastery(local());
    expect(endOfSeries.n).toBe(12);

    // Rechargement (F5) : même question, même état, aucune nouvelle consommation.
    await mount(null, "/exercice.html?resume=1");
    expect(mockApi.practiceLoad).not.toHaveBeenCalled();
    expect(badge()).toContain("Avancé");
    expect(mastery(local())).toEqual(endOfSeries);

    // Q10 échouée : fin de série, puis nouvelle série sur la même notion.
    await answer(false);
    expect($("screen-recap").hidden).toBe(false);
    const afterQ10 = mastery(local());
    expect(afterQ10.theta).toBeLessThan(endOfSeries.theta);
    await mount(SERIES);
    expect(mastery(local())).toEqual(afterQ10);
    expect(posed()[0]).toBeLessThanOrEqual(3); // jamais de retour en Défi ni en Difficile
    expect(badge()).not.toMatch(/Défi|Difficile/);

    // Second navigateur (stockage vide) : historique repris du serveur -> même état, même difficulté.
    const synced = mockApi.saveStats.mock.calls.at(-1)[0].history;
    const firstNew = posed()[0];
    localStorage.clear();
    sessionStorage.clear();
    mockApi.getStats.mockResolvedValue({ history: synced });
    await mount(SERIES);
    expect(mastery(local())).toEqual(afterQ10);
    expect(posed()[0]).toBe(firstNew);
  });
});
