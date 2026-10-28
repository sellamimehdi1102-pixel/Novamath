// ── adaptiveDifficulty.js : règles de niveau par notion et choix de l'exercice
// suivant (fonctions pures). ───────────────────────────────────────────────
import { describe, it, expect } from "vitest";
import {
  levelIndexFromAnswers,
  targetDifficulty,
  pickNextExercise,
  workedNotionsByWeakness,
  notionKey,
} from "../adaptiveDifficulty.js";

const T = true;
const F = false;

describe("levelIndexFromAnswers — paliers de 5 réponses", () => {
  it("démarre au niveau le plus bas", () => {
    expect(levelIndexFromAnswers([], 3)).toBe(0);
  });

  it("un bloc incomplet ne change rien", () => {
    expect(levelIndexFromAnswers([T, T, T, T], 3)).toBe(0);
  });

  it("4 ou 5 réussites sur 5 : niveau supérieur", () => {
    expect(levelIndexFromAnswers([T, T, T, T, F], 3)).toBe(1);
    expect(levelIndexFromAnswers([T, T, T, T, T], 3)).toBe(1);
  });

  it("3 réussites sur 5 : même niveau", () => {
    expect(levelIndexFromAnswers([T, T, T, T, T, T, T, T, F, F], 3)).toBe(1);
  });

  it("2 réussites ou moins sur 5 : niveau inférieur", () => {
    expect(levelIndexFromAnswers([T, T, T, T, T, T, T, F, F, F], 3)).toBe(0);
  });

  it("une réponse isolée ne déclenche pas de nouveau changement (paliers, pas fenêtre glissante)", () => {
    expect(levelIndexFromAnswers([T, T, T, T, T, T], 3)).toBe(1);
  });

  it("ne dépasse jamais les bornes", () => {
    const allRight = Array(30).fill(T);
    expect(levelIndexFromAnswers(allRight, 3)).toBe(2);
    expect(levelIndexFromAnswers(Array(30).fill(F), 3)).toBe(0);
    expect(levelIndexFromAnswers(allRight, 1)).toBe(0);
  });
});

describe("targetDifficulty — niveaux réellement disponibles pour la notion", () => {
  const h = (correct, ts, notion = "N") => ({ chapter: "C", notion, correct, ts });

  it("utilise l'échelle propre à la notion (ex. 1, 2, 4)", () => {
    expect(targetDifficulty([], "C", "N", [4, 1, 2, 2])).toBe(1);
    const fiveRight = [1, 2, 3, 4, 5].map((ts) => h(T, ts));
    expect(targetDifficulty(fiveRight, "C", "N", [1, 2, 4])).toBe(2);
  });

  it("ignore les réponses des autres notions et respecte l'ordre chronologique", () => {
    const history = [h(T, 5), h(T, 4), h(T, 3), h(T, 2), h(T, 1), h(F, 6, "Autre")];
    expect(targetDifficulty(history, "C", "N", [1, 2])).toBe(2);
    expect(targetDifficulty(history, "C", "Autre", [1, 2])).toBe(1);
  });
});

describe("pickNextExercise", () => {
  const ex = (id, difficulty, notion = "N") => ({ id, chapter: "C", notion, difficulty });
  const first = () => 0;

  it("choisit un exercice au niveau visé", () => {
    const candidates = [ex(1, 1), ex(2, 2), ex(3, 3)];
    expect(pickNextExercise({ candidates, history: [], usedIds: [], rng: first }).id).toBe(1);
  });

  it("à défaut d'exercice inédit au niveau visé, prend la difficulté la plus proche (la plus basse à égalité)", () => {
    const candidates = [ex(1, 1), ex(2, 3), ex(3, 4)];
    const history = [1, 2, 3, 4, 5].map((ts) => ({ chapter: "C", notion: "N", correct: T, ts }));
    // Niveaux disponibles 1, 3, 4 : 5/5 → niveau 3.
    expect(pickNextExercise({ candidates, history, usedIds: [2], rng: first }).id).toBe(3);
    expect(pickNextExercise({ candidates: [ex(1, 1), ex(3, 3), ex(5, 5)], history, usedIds: [3], rng: first }).id).toBe(
      1,
    );
  });

  it("ne ressert jamais un exercice déjà utilisé dans la série et renvoie null quand tout est épuisé", () => {
    const candidates = [ex(1, 1), ex(2, 1)];
    expect(pickNextExercise({ candidates, history: [], usedIds: [1], rng: first }).id).toBe(2);
    expect(pickNextExercise({ candidates, history: [], usedIds: [1, 2], rng: first })).toBeNull();
  });

  it("préfère un exercice jamais fait à un exercice déjà rencontré", () => {
    const candidates = [ex(1, 1), ex(2, 1)];
    const history = [{ id: 1, chapter: "C", notion: "N", correct: T, ts: 1 }];
    expect(pickNextExercise({ candidates, history, usedIds: [], rng: first }).id).toBe(2);
  });

  it("répartit la série entre les notions, dans l'ordre de priorité fourni", () => {
    const candidates = [ex(1, 1, "A"), ex(2, 1, "A"), ex(3, 1, "B")];
    const order = [notionKey("C", "B"), notionKey("C", "A")];
    expect(pickNextExercise({ candidates, history: [], usedIds: [], notionOrder: order, rng: first }).id).toBe(3);
    // B déjà servie une fois : c'est le tour de A.
    expect(pickNextExercise({ candidates, history: [], usedIds: [3], notionOrder: order, rng: first }).notion).toBe(
      "A",
    );
  });

  it("chaque notion garde son propre niveau", () => {
    const candidates = [ex(1, 1, "A"), ex(2, 2, "A"), ex(3, 1, "B"), ex(4, 2, "B")];
    const history = [1, 2, 3, 4, 5].map((ts) => ({ chapter: "C", notion: "A", correct: T, ts }));
    const order = [notionKey("C", "A"), notionKey("C", "B")];
    expect(pickNextExercise({ candidates, history, usedIds: [], notionOrder: order, rng: first }).id).toBe(2);
    expect(pickNextExercise({ candidates, history, usedIds: [2], notionOrder: order, rng: first }).id).toBe(3);
  });
});

describe("workedNotionsByWeakness", () => {
  it("classe les notions travaillées de la plus fragile à la plus solide", () => {
    const history = [
      { chapter: "C", notion: "Solide", correct: T, ts: 1 },
      { chapter: "C", notion: "Fragile", correct: F, ts: 2 },
      { chapter: "C", notion: "Fragile", correct: T, ts: 3 },
      { chapter: "C", notion: "Ratee", correct: F, ts: 4 },
    ];
    expect(workedNotionsByWeakness(history).map((w) => w.notion)).toEqual(["Ratee", "Fragile", "Solide"]);
  });
});
