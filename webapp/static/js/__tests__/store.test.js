// ── store.js : gamification, mastery/coverage, séries, isolation par compte ─
import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("../api.js", () => ({
  api: { saveStats: vi.fn().mockResolvedValue({}), getStats: vi.fn().mockResolvedValue(null) },
}));

import { api } from "../api.js";
import {
  computeStreak,
  masteryByChapter,
  masteryByNotion,
  coverageByChapter,
  coverageByNotion,
  getChapterStatus,
  levelFromXp,
  recordAnswer,
  getState,
  scopedStats,
  badgeDefs,
  createSeriesDraft,
  addSeriesQuestion,
  finalizeSeries,
  getSeries,
  getSeriesById,
  accuracyOutOf20,
  saveInProgressSeries,
  getInProgressSeries,
  clearInProgressSeries,
  getProfile,
  setProfile,
  resetGuestLocalState,
  hydrateFromServer,
  MASTERY_ACCURACY_THRESHOLD,
  MASTERY_MIN_ATTEMPTS,
} from "../store.js";

function h(overrides = {}) {
  return { id: 1, chapter: "ch1", notion: "n1", correct: true, date: "2026-07-15", ...overrides };
}

describe("store.js — computeStreak", () => {
  it("renvoie 0 pour un historique vide", () => {
    expect(computeStreak([])).toBe(0);
  });

  it("compte 1 jour pour une réponse aujourd'hui", () => {
    const today = new Date().toISOString().slice(0, 10);
    expect(computeStreak([h({ date: today })])).toBe(1);
  });

  it("s'arrête dès qu'un jour est sauté", () => {
    const today = new Date();
    const d0 = today.toISOString().slice(0, 10);
    const d3 = new Date(today.getTime() - 3 * 86400000).toISOString().slice(0, 10);
    expect(computeStreak([h({ date: d0 }), h({ date: d3 })])).toBe(1);
  });

  it("continue sur des jours consécutifs (hier + aujourd'hui)", () => {
    const today = new Date();
    const d0 = today.toISOString().slice(0, 10);
    const d1 = new Date(today.getTime() - 86400000).toISOString().slice(0, 10);
    expect(computeStreak([h({ date: d0 }), h({ date: d1 })])).toBe(2);
  });
});

describe("store.js — masteryByChapter / masteryByNotion", () => {
  it("calcule le taux de réussite par chapitre", () => {
    const history = [h({ correct: true }), h({ correct: false }), h({ correct: true })];
    const m = masteryByChapter(history);
    expect(m.ch1.count).toBe(3);
    expect(m.ch1.rate).toBeCloseTo(2 / 3);
  });

  it("regroupe sous '?' les entrées sans chapitre", () => {
    const m = masteryByChapter([{ correct: true }]);
    expect(m["?"].count).toBe(1);
  });

  it("calcule le taux par (chapitre|notion) et garde le dernier timestamp", () => {
    const history = [h({ ts: 10, correct: true }), h({ ts: 20, correct: false })];
    const m = masteryByNotion(history);
    expect(m["ch1|n1"].count).toBe(2);
    expect(m["ch1|n1"].last).toBe(20);
  });
});

describe("store.js — coverageByChapter / coverageByNotion", () => {
  it("compte les ids distincts réellement tentés par chapitre", () => {
    const history = [h({ id: 1 }), h({ id: 1 }), h({ id: 2 })];
    const cov = coverageByChapter(history);
    expect(cov.ch1.size).toBe(2);
  });

  it("ignore les entrées sans id", () => {
    const cov = coverageByChapter([{ chapter: "ch1" }]);
    expect(cov.ch1).toBeUndefined();
  });

  it("regroupe par chapitre|notion", () => {
    const cov = coverageByNotion([h({ id: 1, notion: "n1" }), h({ id: 2, notion: "n2" })]);
    expect(Object.keys(cov)).toEqual(["ch1|n1", "ch1|n2"]);
  });
});

describe("store.js — getChapterStatus (règle de progression)", () => {
  it("not_started si aucune tentative", () => {
    expect(getChapterStatus("chX", [])).toBe("not_started");
  });

  it("in_progress si le seuil de tentatives n'est pas atteint", () => {
    const history = Array.from({ length: MASTERY_MIN_ATTEMPTS - 1 }, () => h({ correct: true }));
    expect(getChapterStatus("ch1", history)).toBe("in_progress");
  });

  it("in_progress si le taux de réussite est sous le seuil malgré assez de tentatives", () => {
    const history = Array.from({ length: MASTERY_MIN_ATTEMPTS }, (_, i) => h({ correct: i % 2 === 0 }));
    expect(getChapterStatus("ch1", history)).toBe("in_progress");
  });

  it("mastered si accuracy >= seuil ET tentatives >= minimum", () => {
    const history = Array.from({ length: MASTERY_MIN_ATTEMPTS }, () => h({ correct: true }));
    expect(getChapterStatus("ch1", history)).toBe("mastered");
    expect(MASTERY_ACCURACY_THRESHOLD).toBe(0.7);
  });
});

describe("store.js — levelFromXp", () => {
  it("niveau 1 pour 0 xp", () => {
    expect(levelFromXp(0).level).toBe(1);
  });

  it("progresse vers le niveau supérieur en franchissant un seuil", () => {
    expect(levelFromXp(100).level).toBe(2);
    expect(levelFromXp(99).level).toBe(1);
  });

  it("la progression est entre 0 et 1", () => {
    const { progress } = levelFromXp(50);
    expect(progress).toBeGreaterThanOrEqual(0);
    expect(progress).toBeLessThanOrEqual(1);
  });

  it("plafonne au dernier niveau pour un xp très élevé", () => {
    const { level, progress } = levelFromXp(999999);
    expect(level).toBe(11);
    expect(progress).toBe(1);
  });
});

describe("store.js — recordAnswer / getState (persistance localStorage + sync serveur)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("incrémente l'xp et ajoute une entrée à l'historique pour une bonne réponse", () => {
    const { gained, state } = recordAnswer({ id: 1, chapter: "ch1", notion: "n1", difficulty: 1, correct: true });
    expect(gained).toBeGreaterThan(0);
    expect(state.history).toHaveLength(1);
    expect(state.xp).toBe(gained);
  });

  it("ne gagne aucun xp pour une mauvaise réponse", () => {
    const { gained } = recordAnswer({ id: 1, chapter: "ch1", notion: "n1", difficulty: 1, correct: false });
    expect(gained).toBe(0);
  });

  it("applique le multiplicateur de difficulté", () => {
    const { gained: g1 } = recordAnswer({ id: 1, chapter: "c", notion: "n", difficulty: 1, correct: true, usedHint: true });
    const g5 = recordAnswer({ id: 2, chapter: "c", notion: "n", difficulty: 5, correct: true, usedHint: true }).gained - g1;
    expect(g5).toBeGreaterThan(0);
  });

  it("bonifie une bonne réponse sans indice utilisé", () => {
    const withHint = recordAnswer({ id: 1, chapter: "c", notion: "n", difficulty: 1, correct: true, usedHint: true }).gained;
    const noHint = recordAnswer({ id: 2, chapter: "c", notion: "n", difficulty: 1, correct: true, usedHint: false }).gained;
    expect(noHint).toBeGreaterThan(withHint);
  });

  it("persiste l'état côté serveur via api.saveStats (best-effort)", () => {
    recordAnswer({ id: 1, chapter: "c", notion: "n", difficulty: 1, correct: true });
    expect(api.saveStats).toHaveBeenCalled();
  });

  it("débloque le badge ex_10 au 10e exercice", () => {
    let result;
    for (let i = 0; i < 10; i++) {
      result = recordAnswer({ id: i, chapter: "c", notion: "n", difficulty: 1, correct: true });
    }
    expect(result.state.badges).toContain("ex_10");
    expect(result.newlyUnlocked).toContain("ex_10");
  });

  it("getState() reflète les réponses déjà enregistrées", () => {
    recordAnswer({ id: 1, chapter: "c", notion: "n", difficulty: 1, correct: true });
    expect(getState().history).toHaveLength(1);
  });
});

describe("store.js — scopedStats (isolation par classe)", () => {
  it("filtre l'historique et les séries par class_level, traite l'absence comme 'seconde'", () => {
    const state = {
      history: [h({ class_level: "seconde" }), h({ class_level: "premiere" }), { chapter: "c", correct: true }],
      series: [],
    };
    const scoped = scopedStats(state, "seconde");
    expect(scoped.history).toHaveLength(2);
  });

  it("calcule l'xp uniquement sur les entrées du scope", () => {
    const state = { history: [h({ class_level: "seconde", xp: 10 }), h({ class_level: "premiere", xp: 999 })], series: [] };
    expect(scopedStats(state, "seconde").xp).toBe(10);
  });
});

describe("store.js — badgeDefs", () => {
  it("expose au moins un badge avec id + label + test", () => {
    const defs = badgeDefs();
    expect(defs.length).toBeGreaterThan(0);
    defs.forEach((b) => {
      expect(typeof b.id).toBe("string");
      expect(typeof b.label).toBe("string");
      expect(typeof b.test).toBe("function");
    });
  });
});

describe("store.js — Séries (draft, finalisation)", () => {
  it("createSeriesDraft initialise une série vide avec un id unique", () => {
    const draft = createSeriesDraft({ mode: "revisions", chapterId: "ch1", notion: "n1", total: 10 });
    expect(draft.questions).toEqual([]);
    expect(draft.id).toMatch(/^s_\d+$/);
  });

  it("addSeriesQuestion ajoute une question au draft", () => {
    const draft = createSeriesDraft({ mode: "revisions", chapterId: "ch1", total: 1 });
    addSeriesQuestion(draft, { correct: true, duration_s: 5 });
    expect(draft.questions).toHaveLength(1);
  });

  it("finalizeSeries calcule score/accuracy/durée et persiste", () => {
    const draft = createSeriesDraft({ mode: "revisions", chapterId: "ch1", total: 2 });
    addSeriesQuestion(draft, { correct: true, duration_s: 5 });
    addSeriesQuestion(draft, { correct: false, duration_s: 3 });
    const record = finalizeSeries(draft);
    expect(record.score).toBe(1);
    expect(record.total).toBe(2);
    expect(record.accuracy).toBe(50);
    expect(record.durationTotal_s).toBe(8);
    expect(getSeries()).toContainEqual(record);
    expect(getSeriesById(record.id)).toEqual(record);
  });

  it("getSeriesById renvoie null pour un id inconnu", () => {
    expect(getSeriesById("s_inexistant")).toBeNull();
  });
});

describe("store.js — accuracyOutOf20", () => {
  it("renvoie 0 pour un historique vide", () => {
    expect(accuracyOutOf20([])).toBe(0);
  });

  it("convertit le taux de réussite en note sur 20, arrondie au demi-point", () => {
    const history = [h({ correct: true }), h({ correct: true }), h({ correct: false })];
    expect(accuracyOutOf20(history)).toBeCloseTo(13.5);
  });
});

describe("store.js — série en cours (pause/reprise) isolée par classe", () => {
  it("saveInProgressSeries puis getInProgressSeries renvoie le même snapshot pour la classe active", () => {
    localStorage.setItem("novamath:class_level", "seconde");
    saveInProgressSeries({ chapterId: "ch1", answered: 3 });
    const snap = getInProgressSeries();
    expect(snap.chapterId).toBe("ch1");
  });

  it("renvoie null si aucune série n'est en cours", () => {
    expect(getInProgressSeries()).toBeNull();
  });

  it("clearInProgressSeries supprime le snapshot", () => {
    saveInProgressSeries({ chapterId: "ch1" });
    clearInProgressSeries();
    expect(getInProgressSeries()).toBeNull();
  });
});

describe("store.js — profil local historique", () => {
  it("getProfile renvoie un profil par défaut si absent", () => {
    const profile = getProfile();
    expect(profile.name).toBe("Élève");
    expect(profile.joinedAt).toBeTypeOf("number");
  });

  it("setProfile persiste et notifie via CustomEvent novamath:profile-updated", () => {
    const handler = vi.fn();
    window.addEventListener("novamath:profile-updated", handler);
    setProfile({ name: "Sana", pseudo: "sana", avatar: null, joinedAt: 1 });
    expect(handler).toHaveBeenCalledOnce();
    expect(getProfile().name).toBe("Sana");
    window.removeEventListener("novamath:profile-updated", handler);
  });
});

describe("store.js — resetGuestLocalState", () => {
  it("purge tous les caches locaux scopés + la série en cours", () => {
    localStorage.setItem("lumis:stats", "{}");
    localStorage.setItem("novamath:settings", "{}");
    saveInProgressSeries({ chapterId: "ch1" });
    resetGuestLocalState();
    expect(localStorage.getItem("lumis:stats")).toBeNull();
    expect(localStorage.getItem("novamath:settings")).toBeNull();
    expect(getInProgressSeries()).toBeNull();
  });
});

describe("store.js — hydrateFromServer", () => {
  it("adopte l'historique distant s'il est plus long que le local", async () => {
    api.getStats.mockResolvedValueOnce({ xp: 500, history: [h(), h(), h()] });
    const result = await hydrateFromServer();
    expect(result.history).toHaveLength(3);
  });

  it("garde l'état local si le serveur échoue", async () => {
    api.getStats.mockRejectedValueOnce(new Error("réseau"));
    const result = await hydrateFromServer();
    expect(result).toHaveProperty("history");
  });
});
