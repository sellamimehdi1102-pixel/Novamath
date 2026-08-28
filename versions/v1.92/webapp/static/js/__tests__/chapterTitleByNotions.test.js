// ── chapterTitleByNotions.js : titre de secours déduit des notions ─────────
import { describe, it, expect } from "vitest";
import { resolveChapterTitle } from "../chapterTitleByNotions.js";

describe("chapterTitleByNotions.js — resolveChapterTitle", () => {
  it("garde le titre officiel s'il n'est pas générique", () => {
    expect(resolveChapterTitle("Les suites numériques", ["Suite arithmétique"])).toBe("Les suites numériques");
  });

  it("déduit un titre depuis les notions si le titre est générique ('Chapitre N')", () => {
    expect(resolveChapterTitle("Chapitre 3", ["Suite arithmétique", "Suite géométrique"])).toBe("Suites numériques");
  });

  it("la détection de titre générique est insensible à la casse", () => {
    expect(resolveChapterTitle("chapitre 7", ["Fonction exponentielle"])).toBe("Fonction exponentielle");
  });

  it("choisit le thème le plus fréquent parmi plusieurs notions", () => {
    const notions = ["Suite arithmétique", "Suite géométrique", "Équations du second degré"];
    expect(resolveChapterTitle("Chapitre 1", notions)).toBe("Suites numériques");
  });

  it("renvoie le titre générique tel quel si aucune notion connue ne correspond", () => {
    expect(resolveChapterTitle("Chapitre 9", ["Notion inconnue"])).toBe("Chapitre 9");
  });

  it("gère une absence de notions sans planter", () => {
    expect(resolveChapterTitle("Chapitre 2", undefined)).toBe("Chapitre 2");
    expect(resolveChapterTitle("Chapitre 2", [])).toBe("Chapitre 2");
  });

  it("gère un titre absent (falsy) en tentant une déduction", () => {
    expect(resolveChapterTitle("", ["Fonction dérivée"])).toBe("Dérivation : nombre dérivé et fonction dérivée");
  });
});
