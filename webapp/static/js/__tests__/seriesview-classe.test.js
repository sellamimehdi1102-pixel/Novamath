// ── Historique des séries (Dashboard + Profil) : titres et détail « Revoir »
// lus dans la classe concernée (2026-10-24). Sans `class_level`,
// /api/chapters et /api/exercise répondent pour la Seconde : une série de
// Quatrième s'affichait « Chapitre 8 · Variations et extremums » et son
// détail « Revoir » restait « (exercice indisponible) ».
import { describe, it, expect, vi, beforeEach } from "vitest";
import { flushPromises } from "./testUtils.js";

const mockApi = { chapters: vi.fn(), exercise: vi.fn() };
vi.mock("../api.js", () => ({ api: mockApi }));
vi.mock("../curriculumSelector.js", () => ({ getStoredClassLevel: () => "quatrieme" }));
vi.mock("../mathrender.js", () => ({
  setMathContent: (el, text) => {
    el.textContent = text;
  },
}));

async function freshModule() {
  vi.resetModules();
  return import("../seriesview.js");
}

describe("seriesview.js — classe des séries", () => {
  beforeEach(() => {
    Object.values(mockApi).forEach((fn) => fn.mockReset());
  });

  it("charge les titres de chapitres de la classe active", async () => {
    mockApi.chapters.mockResolvedValue({ chapters_meta: [{ id: "Chapitre_8", title: "Théorème de Pythagore" }] });
    const { getChaptersMeta, chapterLabel, getChapterTitles } = await freshModule();
    await getChaptersMeta();
    expect(mockApi.chapters).toHaveBeenCalledWith("quatrieme");
    expect(chapterLabel("Chapitre_8", await getChapterTitles())).toBe("Chapitre 8 · Théorème de Pythagore");
  });

  it("« Revoir » lit chaque exercice dans la banque de la classe de la série", async () => {
    mockApi.exercise.mockImplementation((id, classLevel) =>
      Promise.resolve({ exercise: { enonce: `énoncé ${id} (${classLevel})` } }),
    );
    const { buildSeriesRow } = await freshModule();
    const series = {
      date: "2026-10-24",
      endedAt: Date.now(),
      chapterId: "Chapitre_8",
      notion: "Carrés et racines carrées",
      score: 1,
      total: 2,
      accuracy: 50,
      class_level: "quatrieme",
      questions: [
        { exercise_id: 48201, correct: true },
        { exercise_id: 480030, correct: false },
      ],
    };
    const table = document.createElement("table");
    const row = buildSeriesRow(series, {});
    table.appendChild(row);
    row.querySelector(".btn-review").click();
    await flushPromises();
    await flushPromises();
    expect(mockApi.exercise.mock.calls).toEqual([
      [48201, "quatrieme"],
      [480030, "quatrieme"],
    ]);
    expect(table.textContent).toContain("énoncé 48201 (quatrieme)");
    expect(table.textContent).not.toContain("exercice indisponible");
  });

  it("une série ancienne sans class_level reste lue dans la banque de Seconde", async () => {
    mockApi.exercise.mockResolvedValue({ exercise: { enonce: "énoncé" } });
    const { buildSeriesRow } = await freshModule();
    const row = buildSeriesRow(
      { date: "2026-01-01", score: 1, total: 1, accuracy: 100, questions: [{ exercise_id: 12, correct: true }] },
      {},
    );
    document.createElement("table").appendChild(row);
    row.querySelector(".btn-review").click();
    await flushPromises();
    expect(mockApi.exercise).toHaveBeenCalledWith(12, "seconde");
  });
});
