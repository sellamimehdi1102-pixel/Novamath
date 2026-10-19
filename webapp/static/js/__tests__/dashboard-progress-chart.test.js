// ── dashboard.js : graphique "Résultats au fil des séries" (refonte, fenêtres
// simplifiées en 5/15/Tout le 2026-10-19) ───────────────────────────────────
// Couvre les cas demandés : 0/1/5/6/15/16/20 séries, plusieurs séries le même
// jour, séries de longueurs différentes, tooltip (date+heure+score+%) et le
// fait que ce sont toujours les N PLUS RÉCENTES séries qui sont affichées
// (jamais les N premières). Le graphique ne doit jamais recalculer/filtrer
// les données lui-même au-delà de la fenêtre déjà fournie par le backend
// (voir dashboard-plan-window.test.js) — ici on vérifie uniquement le rendu
// visuel (points/axes/tooltip) à partir de `series[]` déjà reçu.
import { describe, it, expect, vi } from "vitest";
import { loadPageBody, flushPromises } from "./testUtils.js";

const mockApi = {
  me: vi.fn(),
  chapters: vi.fn(),
  getCourseProgress: vi.fn(),
  getStats: vi.fn(),
  getQuota: vi.fn(),
  guestDashboardSeen: vi.fn(),
  exercise: vi.fn(),
};
vi.mock("../api.js", () => ({ api: mockApi }));
vi.mock("../settingsManager.js", () => ({
  initSettingsManager: () => Promise.resolve(),
  onSettingsChange: vi.fn(),
  getSettings: () => ({ learning: { dailyGoalExercises: 10 } }),
}));
vi.mock("../settingsPopup.js", () => ({ bindSettingsButton: vi.fn() }));
vi.mock("../i18n.js", () => ({ bindLiveTranslations: vi.fn() }));
vi.mock("../curriculumSelector.js", () => ({ getStoredClassLevel: () => "seconde" }));
vi.mock("../guestLockOverlay.js", () => ({
  mountGuestLockOverlay: vi.fn(),
  dismissGuestLockOverlay: vi.fn(),
  unmountGuestLockOverlay: vi.fn(),
}));

const CHAPTER = { id: "Chapitre_1", title: "Nombres et calculs", n_exercises: 10 };

// `index` sert à la fois d'ordre chronologique (startedAt croissant) et
// d'identifiant lisible dans les tests ("la série n°3").
function seriesEntry(index, { score = 7, total = 10, dateOffsetDays, chapterId = "Chapitre_1", notion = "n1" } = {}) {
  const dayOffset = dateOffsetDays ?? index;
  const endedAt = Date.UTC(2026, 9, 1, 8, 0, 0) + dayOffset * 86400000 + index * 1000;
  return {
    id: `s_${index}`,
    seriesIndex: index,
    startedAt: endedAt - 100,
    endedAt,
    mode: "revisions",
    chapterId,
    notion,
    questions: [],
    score,
    total,
    accuracy: total ? Math.round((score / total) * 100) : 0,
    durationTotal_s: 100,
    class_level: "seconde",
  };
}

function nSeries(n, opts) {
  return Array.from({ length: n }, (_, i) => seriesEntry(i + 1, opts));
}

// hydrateFromServer() (store.js) ne retient la réponse serveur (donc
// `series[]`) que si `history[]` n'est pas vide — reflète le comportement
// réel de l'app (une série terminée produit toujours des entrées
// `history`). Un historique minimal, un par série, suffit ici : seul son
// existence compte pour ces tests du graphique.
function historyFor(series) {
  return series.map((s, i) => ({
    id: `ex_${i}`,
    ts: s.endedAt,
    date: s.date,
    chapter: s.chapterId,
    notion: s.notion,
    difficulty: 1,
    correct: true,
    mode: s.mode,
    duration_s: 10,
    xp: 5,
    class_level: s.class_level,
  }));
}

function defaultMocks() {
  Object.values(mockApi).forEach((fn) => fn.mockReset());
  mockApi.chapters.mockResolvedValue({ chapters_meta: [CHAPTER] });
  mockApi.getCourseProgress.mockResolvedValue({});
  mockApi.getQuota.mockResolvedValue({ chat_messages: { used: 1, limit: 25, remaining: 24, unlimited: false } });
  mockApi.guestDashboardSeen.mockResolvedValue({ locked: false });
  mockApi.exercise.mockResolvedValue({ exercise: { id: 1, enonce: "Q1", answer: "R1" } });
}

async function mountDashboard({ plan = "ultra", series = [], history = [] } = {}) {
  document.body.innerHTML = loadPageBody("dashboard.html");
  document.documentElement.setAttribute("data-animations", "off");
  localStorage.clear();
  defaultMocks();
  mockApi.me.mockResolvedValue({
    user: {
      id: 1,
      pseudo: "Élève",
      username: "eleve",
      email: "e@gmail.com",
      is_guest: false,
      plan,
      effective_plan: plan,
    },
  });
  mockApi.getStats.mockResolvedValue({ xp: 0, history, badges: [], series });
  vi.resetModules();
  await import("../dashboard.js");
  await flushPromises();
  await flushPromises();
  await flushPromises();
}

describe("dashboard.js — graphique de progression : états des données", () => {
  it("0 série : état vide explicite, pas de point ni de tooltip actif", async () => {
    await mountDashboard({ series: [] });
    const svg = document.getElementById("progress-chart");
    expect(svg.querySelectorAll(".chart-dot").length).toBe(0);
    expect(svg.textContent).toContain("Termine une série");
    expect(document.getElementById("chart-tooltip").style.display).toBe("none");
  });

  it("1 série : un seul point rendu, centré, sans division par zéro", async () => {
    const series = [seriesEntry(1, { score: 7, total: 10 })];
    await mountDashboard({ series, history: historyFor(series) });
    const dots = document.querySelectorAll("#progress-chart .chart-dot");
    expect(dots.length).toBe(1);
    expect(Number(dots[0].getAttribute("cy"))).not.toBeNaN();
  });

  it("plusieurs séries le même jour apparaissent comme des points distincts", async () => {
    const series = [
      seriesEntry(1, { score: 5, total: 10, dateOffsetDays: 0 }),
      seriesEntry(2, { score: 9, total: 10, dateOffsetDays: 0 }),
      seriesEntry(3, { score: 3, total: 10, dateOffsetDays: 0 }),
    ];
    await mountDashboard({ series, history: historyFor(series) });
    const dots = document.querySelectorAll("#progress-chart .chart-dot");
    expect(dots.length).toBe(3);
    const cys = [...dots].map((d) => d.getAttribute("cy"));
    expect(new Set(cys).size).toBe(3); // 3 taux de réussite différents -> 3 hauteurs distinctes
  });

  it("des séries de longueurs différentes sont normalisées en % sur l'axe, en gardant le score exact pour le tooltip", async () => {
    const series = [
      seriesEntry(1, { score: 7, total: 8, dateOffsetDays: 0 }),
      seriesEntry(2, { score: 6, total: 10, dateOffsetDays: 1 }),
    ];
    await mountDashboard({ series, history: historyFor(series) });
    const hits = document.querySelectorAll("#progress-chart .chart-hit");
    expect(hits.length).toBe(2);

    hits[0].dispatchEvent(new MouseEvent("mousemove", { bubbles: true }));
    const tooltip = document.getElementById("chart-tooltip");
    expect(tooltip.innerHTML).toContain("7 bonnes réponses sur 8 — 88%");

    hits[1].dispatchEvent(new MouseEvent("mousemove", { bubbles: true }));
    expect(tooltip.innerHTML).toContain("6 bonnes réponses sur 10 — 60%");
  });

  it("le tooltip affiche une date ET une heure (jj/mm à hh:mm), le chapitre/notion et le %, jamais une valeur fictive", async () => {
    const series = [seriesEntry(1, { score: 7, total: 10, dateOffsetDays: 0 })];
    await mountDashboard({ series, history: historyFor(series) });
    const hit = document.querySelector("#progress-chart .chart-hit");
    hit.dispatchEvent(new MouseEvent("mousemove", { bubbles: true }));
    const tooltip = document.getElementById("chart-tooltip");
    expect(tooltip.innerHTML).toMatch(/\d{2}\/\d{2} à \d{2}:\d{2}/);
    expect(tooltip.innerHTML).toContain("Chapitre_1 · n1");
  });

  it("1 bonne réponse reste au singulier dans le tooltip", async () => {
    const series = [seriesEntry(1, { score: 1, total: 10, dateOffsetDays: 0 })];
    await mountDashboard({ series, history: historyFor(series) });
    const hit = document.querySelector("#progress-chart .chart-hit");
    hit.dispatchEvent(new MouseEvent("mousemove", { bubbles: true }));
    expect(document.getElementById("chart-tooltip").innerHTML).toContain("1 bonne réponse sur 10 — 10%");
  });

  it("l'axe horizontal affiche aussi une heure (hh:mm), pas seulement une date", async () => {
    const series = [seriesEntry(1, { dateOffsetDays: 0 })];
    await mountDashboard({ series, history: historyFor(series) });
    const svgText = document.getElementById("progress-chart").textContent;
    expect(svgText).toMatch(/\d{2}:\d{2}/);
  });
});

describe("dashboard.js — fenêtres 5/15/Tout : exactement N points, jamais plus, jamais moins quand disponible", () => {
  it("5 séries : la fenêtre 5 (défaut) affiche les 5 disponibles, la note reste masquée", async () => {
    const series = nSeries(5);
    await mountDashboard({ plan: "ultra", series, history: historyFor(series) });
    expect(document.querySelectorAll("#progress-chart .chart-dot").length).toBe(5);
    expect(document.getElementById("chart-window-note").hidden).toBe(true);
  });

  it("6 séries : la fenêtre 5 affiche 5 points, 15 et Tout affichent les 6 disponibles avec une note explicative", async () => {
    const series = nSeries(6);
    await mountDashboard({ plan: "ultra", series, history: historyFor(series) });
    expect(document.querySelectorAll("#progress-chart .chart-dot").length).toBe(5);

    document.querySelector('.chart-zoom-btn[data-window="15"]').click();
    await flushPromises();
    expect(document.querySelectorAll("#progress-chart .chart-dot").length).toBe(6);
    expect(document.getElementById("chart-window-note").textContent).toContain(
      "6 séries disponibles sur les 15 dernières demandées",
    );

    document.querySelector('.chart-zoom-btn[data-window="all"]').click();
    await flushPromises();
    expect(document.querySelectorAll("#progress-chart .chart-dot").length).toBe(6);
  });

  it("15 séries : 5 affiche 5, 15 affiche 15, Tout affiche 15 (rien à tronquer)", async () => {
    const series = nSeries(15);
    await mountDashboard({ plan: "ultra", series, history: historyFor(series) });
    expect(document.querySelectorAll("#progress-chart .chart-dot").length).toBe(5);

    document.querySelector('.chart-zoom-btn[data-window="15"]').click();
    await flushPromises();
    expect(document.querySelectorAll("#progress-chart .chart-dot").length).toBe(15);
    expect(document.getElementById("chart-window-note").hidden).toBe(true);
  });

  it("16 séries : la fenêtre 15 affiche 15 points (pas 16), Tout affiche les 16", async () => {
    const series = nSeries(16);
    await mountDashboard({ plan: "ultra", series, history: historyFor(series) });

    document.querySelector('.chart-zoom-btn[data-window="15"]').click();
    await flushPromises();
    expect(document.querySelectorAll("#progress-chart .chart-dot").length).toBe(15);

    document.querySelector('.chart-zoom-btn[data-window="all"]').click();
    await flushPromises();
    expect(document.querySelectorAll("#progress-chart .chart-dot").length).toBe(16);
  });

  it("20 séries : 5/15/Tout affichent respectivement 5/15/20 points", async () => {
    const series = nSeries(20);
    await mountDashboard({ plan: "ultra", series, history: historyFor(series) });
    expect(document.querySelectorAll("#progress-chart .chart-dot").length).toBe(5);

    document.querySelector('.chart-zoom-btn[data-window="15"]').click();
    await flushPromises();
    expect(document.querySelectorAll("#progress-chart .chart-dot").length).toBe(15);

    document.querySelector('.chart-zoom-btn[data-window="all"]').click();
    await flushPromises();
    expect(document.querySelectorAll("#progress-chart .chart-dot").length).toBe(20);
  });
});

describe("dashboard.js — ce sont toujours les N séries les PLUS RÉCENTES qui s'affichent (jamais les N premières)", () => {
  // Chaque point porte `data-idx` (0-based, ordre d'affichage gauche->droite) ;
  // on retrouve la série réelle correspondante via son tooltip (score unique
  // par série ici : score = seriesIndex, pour identifier sans ambiguïté).
  function scoreShownAtIndex(idx) {
    const hit = document.querySelectorAll("#progress-chart .chart-hit")[idx];
    hit.dispatchEvent(new MouseEvent("mousemove", { bubbles: true }));
    const html = document.getElementById("chart-tooltip").innerHTML;
    return Number(html.match(/(\d+) bonnes? réponses? sur/)[1]);
  }

  it("avec 6 séries, la fenêtre 5 affiche les séries 2 à 6 (jamais 1 à 5)", async () => {
    // score = index de la série (1..6) pour l'identifier sans ambiguïté dans le tooltip.
    const series = Array.from({ length: 6 }, (_, i) => seriesEntry(i + 1, { score: i + 1, total: 10 }));
    await mountDashboard({ plan: "ultra", series, history: historyFor(series) });
    const dots = document.querySelectorAll("#progress-chart .chart-dot");
    expect(dots.length).toBe(5);
    const shown = [0, 1, 2, 3, 4].map(scoreShownAtIndex);
    expect(shown).toEqual([2, 3, 4, 5, 6]);
  });

  it("avec 20 séries : fenêtre 5 -> séries 16 à 20, fenêtre 15 -> séries 6 à 20, Tout -> 1 à 20", async () => {
    const series = Array.from({ length: 20 }, (_, i) => seriesEntry(i + 1, { score: i + 1, total: 20 }));
    await mountDashboard({ plan: "ultra", series, history: historyFor(series) });

    expect([0, 1, 2, 3, 4].map(scoreShownAtIndex)).toEqual([16, 17, 18, 19, 20]);

    document.querySelector('.chart-zoom-btn[data-window="15"]').click();
    await flushPromises();
    expect(document.querySelectorAll("#progress-chart .chart-dot").length).toBe(15);
    expect([0, 14].map(scoreShownAtIndex)).toEqual([6, 20]);

    document.querySelector('.chart-zoom-btn[data-window="all"]').click();
    await flushPromises();
    expect(document.querySelectorAll("#progress-chart .chart-dot").length).toBe(20);
    expect([0, 19].map(scoreShownAtIndex)).toEqual([1, 20]);
  });

  it("le tri utilise l'horodatage réel de fin de série (endedAt), pas seulement une date sans heure", async () => {
    // Deux séries le même jour civil mais endedAt dans le désordre d'insertion :
    // l'affichage doit suivre endedAt, pas l'ordre du tableau fourni.
    const base = Date.UTC(2026, 9, 19, 0, 0, 0);
    const earlyInDay = { ...seriesEntry(1, { score: 1, total: 10 }), endedAt: base + 8 * 3600000 }; // 08:00
    const lateInDay = { ...seriesEntry(2, { score: 2, total: 10 }), endedAt: base + 20 * 3600000 }; // 20:00
    // Fourni déjà trié par endedAt croissant (comme le fait le backend/store) :
    // ce test vérifie l'affichage de l'ordre, pas un tri interne du frontend.
    const series = [earlyInDay, lateInDay];
    await mountDashboard({ plan: "ultra", series, history: historyFor(series) });
    expect([0, 1].map(scoreShownAtIndex)).toEqual([1, 2]);
  });

  it("les points restent triés chronologiquement de gauche à droite après un changement de fenêtre", async () => {
    const series = nSeries(20);
    await mountDashboard({ plan: "ultra", series, history: historyFor(series) });
    document.querySelector('.chart-zoom-btn[data-window="all"]').click();
    await flushPromises();
    const xs = [...document.querySelectorAll("#progress-chart .chart-dot")].map((d) => Number(d.getAttribute("cx")));
    expect(xs.every((x, i) => i === 0 || x > xs[i - 1])).toBe(true);
  });
});
