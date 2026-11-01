// ── adaptiveDifficulty.js : estimation de maîtrise (theta, sd), calibration en
// 3 réponses, adaptation continue, transfert prudent, sélection (fonctions
// pures). Les tests vérifient des comportements et des invariants. ──────────
import { describe, it, expect } from "vitest";
import {
  initialState,
  updateMastery,
  notionMastery,
  targetDifficulty,
  pickNextExercise,
  workedNotionsByWeakness,
  notionKey,
  CALIBRATION_ANSWERS,
  PRIOR_SD,
  SD_MIN,
  THETA_MIN,
  THETA_MAX,
} from "../adaptiveDifficulty.js";

const T = true;
const F = false;
const LEVELS5 = [1, 2, 3, 4, 5];
let uid = 0;

// Boucle réelle : le moteur propose une difficulté, l'élève répond, l'état est
// recalculé depuis l'historique. `pre` = historique antérieur (autres séries).
function simulate(answers, { levels = LEVELS5, chapter = "C", notion = "N", pre = [], ts0 = 1000 } = {}) {
  const history = [...pre];
  const served = [];
  answers.forEach((ok, i) => {
    const d = targetDifficulty(history, chapter, notion, levels);
    served.push(d);
    history.push({ id: `s${uid++}`, chapter, notion, difficulty: d, correct: ok, ts: ts0 + i });
  });
  return {
    served,
    history,
    next: targetDifficulty(history, chapter, notion, levels),
    mastery: notionMastery(history, chapter, notion),
  };
}
const entries = (notion, list, ts0 = 1, chapter = "C") =>
  list.map(([d, ok], i) => ({ id: `h${uid++}`, chapter, notion, difficulty: d, correct: ok, ts: ts0 + i }));

describe("calibration initiale (3 réponses)", () => {
  it("élève sans historique : première question en Fondamental, incertitude maximale", () => {
    const { next, mastery } = simulate([]);
    expect(next).toBe(1);
    expect(mastery.sd).toBe(PRIOR_SD);
    expect(mastery.calibrated).toBe(false);
  });

  it("3 réussites : Fondamental, Avancé, Défi (niveau réellement posé)", () => {
    const { served, mastery } = simulate([T, T, T]);
    expect(served).toEqual([1, 3, 5]);
    expect(mastery.calibrated).toBe(true);
    expect(mastery.sd).toBeLessThan(PRIOR_SD);
  });

  it("3 erreurs : reste sur des questions accessibles, estimation basse", () => {
    const { served, mastery } = simulate([F, F, F]);
    expect(served).toEqual([1, 1, 1]);
    expect(mastery.theta).toBeLessThan(1);
    expect(mastery.calibrated).toBe(true);
  });

  it("parcours mixte : un échec en Avancé ramène vers un niveau intermédiaire", () => {
    const { served } = simulate([T, F, T]);
    expect(served[0]).toBe(1);
    expect(served[1]).toBe(3);
    expect(served[2]).toBeLessThan(3);
    expect(served[2]).toBeGreaterThanOrEqual(1);
  });

  it("estimation initiale utile dès la 3e réponse : l'incertitude a nettement baissé", () => {
    for (const seq of [
      [T, T, T],
      [F, F, F],
      [T, F, T],
      [F, T, F],
    ]) {
      const { mastery } = simulate(seq);
      expect(mastery.n).toBe(CALIBRATION_ANSWERS);
      expect(mastery.sd).toBeLessThan(PRIOR_SD * 0.5);
    }
  });

  it("une notion déjà travaillée reprend son état depuis l'historique, sans recalibration", () => {
    const pre = entries("N", [
      [1, T],
      [3, T],
      [5, T],
    ]);
    const { served } = simulate([T], { pre });
    expect(served[0]).toBeGreaterThanOrEqual(4); // pas de retour en Fondamental
  });
});

describe("calibration : politique diagnostique robuste", () => {
  it("niveaux manquants : 3 réussites suivent les niveaux réellement disponibles", () => {
    expect(simulate([T, T, T], { levels: [1, 4, 5] }).served).toEqual([1, 4, 5]);
    expect(simulate([T, T, T], { levels: [1, 2] }).served).toEqual([1, 2, 2]);
    expect(simulate([T, T, T], { levels: [2, 3] }).served).toEqual([2, 3, 3]);
  });

  it("un échec en calibration arrête le sondage vers le haut", () => {
    const { served } = simulate([T, F, F]);
    expect(served[1]).toBe(3);
    expect(served[2]).toBeLessThan(3);
    expect(simulate([F, T, T]).served[2]).toBeLessThan(5);
  });

  it("la calibration ne recommence pas dans une nouvelle série", () => {
    const first = simulate([T, T, T]);
    const second = simulate([T], { pre: first.history, ts0: 9000 });
    expect(second.served[0]).toBeGreaterThanOrEqual(4);
  });
});

describe("aucun recul juste après une réussite", () => {
  it("fin de calibration après un sondage réussi : pas de retour sous le niveau réussi (1F -> 1 -> 3 -> pas 2)", () => {
    const pre = entries("N", [[1, F]]);
    const { served, next } = simulate([T, T], { pre, ts0: 100 });
    expect(served).toEqual([1, 3]);
    expect(next).toBeGreaterThanOrEqual(3);
    const pre2 = entries("N", [
      [1, T],
      [2, T],
    ]);
    const r2 = simulate([T], { pre: pre2, ts0: 100 });
    expect(r2.served).toEqual([4]);
    expect(r2.next).toBeGreaterThanOrEqual(4);
  });

  it("quel que soit l'historique, une bonne réponse n'est jamais suivie d'une question plus facile", () => {
    let seed = 7;
    const rnd = () => (seed = (seed * 1664525 + 1013904223) % 4294967296) / 4294967296;
    for (let t = 0; t < 300; t++) {
      const pre = entries(
        "N",
        Array.from({ length: Math.floor(rnd() * 7) }, () => [1 + Math.floor(rnd() * 5), rnd() < 0.6]),
      );
      const { served, next } = simulate(Array(6).fill(T), { pre, ts0: 100 });
      [...served, next].forEach((d, i, all) => i && expect(d).toBeGreaterThanOrEqual(all[i - 1]));
    }
  });

  it("une erreur lève le plancher : la descente reste possible", () => {
    const pre = entries("N", [
      [1, T],
      [3, T],
      [5, T],
    ]);
    const { served } = simulate([F, F, F, F, F, F], { pre, ts0: 100 });
    expect(served[served.length - 1]).toBeLessThan(served[0]);
  });
});

describe("adaptation continue", () => {
  it("montée : un élève qui réussit reste durablement aux niveaux élevés", () => {
    const { served } = simulate(Array(10).fill(T));
    expect(Math.min(...served.slice(2))).toBeGreaterThanOrEqual(4);
  });

  it("descente effective après des erreurs répétées", () => {
    const strong = simulate(Array(8).fill(T));
    const { served } = simulate(Array(6).fill(F), { pre: strong.history, ts0: 5000 });
    expect(served[served.length - 1]).toBeLessThan(served[0]);
    // Les erreurs se poursuivant, la descente continue jusqu'à un niveau accessible.
    const longer = simulate(Array(12).fill(F), { pre: strong.history, ts0: 5000 });
    expect(longer.served[longer.served.length - 1]).toBeLessThanOrEqual(3);
  });

  it("une erreur isolée n'annule pas une maîtrise solide", () => {
    const strong = simulate(Array(10).fill(T));
    const { served } = simulate([F, T], { pre: strong.history, ts0: 5000 });
    expect(served[1]).toBeGreaterThanOrEqual(4);
  });

  it("réévaluation après chaque réponse (pas de palier fixe)", () => {
    const h = [];
    const levelsSeen = [targetDifficulty(h, "C", "N", LEVELS5)];
    [T, T].forEach((ok, i) => {
      h.push({ id: `r${i}`, chapter: "C", notion: "N", difficulty: levelsSeen[i], correct: ok, ts: i + 1 });
      levelsSeen.push(targetDifficulty(h, "C", "N", LEVELS5));
    });
    expect(levelsSeen[1]).toBeGreaterThan(levelsSeen[0]);
    expect(levelsSeen[2]).toBeGreaterThan(levelsSeen[1]);
  });

  it("élève oscillant : difficulté stable, sans va-et-vient systématique", () => {
    const { served } = simulate([T, F, T, F, T, F, T, F, T, F, T, F]);
    const tail = served.slice(4);
    const changes = tail.slice(1).filter((d, i) => d !== tail[i]).length;
    expect(changes).toBeLessThanOrEqual(1);
    expect(Math.max(...tail) - Math.min(...tail)).toBeLessThanOrEqual(1);
  });

  it("la progression reprend après une longue période de stabilité", () => {
    const plateau = simulate(Array.from({ length: 24 }, (_, i) => i % 3 !== 0));
    const level = plateau.next;
    const later = simulate(Array(14).fill(T), { pre: plateau.history, ts0: 9000 });
    expect(later.next).toBeGreaterThan(level);
  });

  it("les progrès restent possibles même après une très longue série d'échecs", () => {
    const low = simulate(Array(40).fill(F));
    expect(low.mastery.sd).toBeGreaterThanOrEqual(SD_MIN);
    const later = simulate(Array(12).fill(T), { pre: low.history, ts0: 9000 });
    expect(later.mastery.theta).toBeGreaterThan(low.mastery.theta + 1);
    expect(later.next).toBeGreaterThan(low.next);
  });

  it("élève bien connu : incertitude plus faible qu'un élève nouvellement évalué, mais jamais nulle", () => {
    const fresh = simulate([T, T, T]).mastery;
    const known = simulate(Array(20).fill(T)).mastery;
    expect(known.sd).toBeLessThan(fresh.sd);
    expect(known.sd).toBeGreaterThanOrEqual(SD_MIN);
  });

  it("estimation bornée quelles que soient les réponses", () => {
    const { mastery: hi } = simulate(Array(80).fill(T));
    const { mastery: lo } = simulate(Array(80).fill(F));
    expect(hi.theta).toBeLessThanOrEqual(THETA_MAX);
    expect(lo.theta).toBeGreaterThanOrEqual(THETA_MIN);
    expect(hi.sd).toBeGreaterThanOrEqual(SD_MIN);
  });

  it("réussir un Défi apporte plus d'information que réussir un Fondamental", () => {
    const base = initialState();
    const easy = updateMastery(base, 1, true);
    const hard = updateMastery(base, 5, true);
    expect(hard.theta).toBeGreaterThan(easy.theta);
  });

  it("l'absence de niveaux élevés ne fait jamais baisser la maîtrise", () => {
    const { mastery } = simulate(Array(8).fill(T), { levels: [1, 2] });
    expect(mastery.theta).toBeGreaterThanOrEqual(2);
    expect(targetDifficulty(simulate(Array(8).fill(T), { levels: [1, 2] }).history, "C", "N", [1, 2])).toBe(2);
  });

  it("notions à 1, 2 ou 3 niveaux : toujours un niveau réellement disponible", () => {
    for (const levels of [[3], [1, 4], [2, 3, 5]]) {
      const { served } = simulate([T, T, F, T, F, F, T, T], { levels });
      served.forEach((d) => expect(levels).toContain(d));
    }
    expect(targetDifficulty([], "C", "N", [])).toBeNull();
  });
});

describe("intégrité de l'historique", () => {
  it("une entrée dupliquée (même exercice au même instant, synchronisation) ne compte qu'une fois", () => {
    const base = entries("N", [
      [1, T],
      [3, T],
    ]);
    const dup = [...base, { ...base[1] }, { ...base[0] }];
    expect(notionMastery(dup, "C", "N")).toEqual(notionMastery(base, "C", "N"));
  });

  it("un résultat sur une question répétée pèse moins qu'un résultat sur une question inédite", () => {
    const first = entries("N", [[2, T]], 1);
    const repeated = [...first, { ...first[0], ts: 2, correct: F }];
    const fresh = [...first, { ...first[0], id: "autre", ts: 2, correct: F }];
    const rep = notionMastery(repeated, "C", "N").theta;
    const inedit = notionMastery(fresh, "C", "N").theta;
    expect(rep).toBeGreaterThan(inedit);
    expect(rep).toBeLessThan(notionMastery(first, "C", "N").theta);
  });

  it("l'ordre des entrées de l'historique n'a pas d'importance (rejeu chronologique)", () => {
    const h = entries("N", [
      [1, T],
      [3, T],
      [5, F],
      [3, T],
      [4, F],
    ]);
    expect(notionMastery([...h].reverse(), "C", "N")).toEqual(notionMastery(h, "C", "N"));
  });

  it("une réponse sans difficulté connue n'apporte aucune information", () => {
    const h = entries("N", [
      [1, T],
      [null, F],
      [undefined, F],
    ]);
    const ref = entries("N", [[1, T]]);
    expect(notionMastery(h, "C", "N").theta).toBeCloseTo(notionMastery(ref, "C", "N").theta, 10);
  });

  it("un ancien historique (sans id ni ts) reste exploitable", () => {
    const old = [
      { chapter: "C", notion: "N", difficulty: 1, correct: T },
      { chapter: "C", notion: "N", difficulty: 2, correct: T },
    ];
    expect(notionMastery(old, "C", "N").n).toBe(2);
  });

  it("deux élèves (historiques distincts) et deux notions sont indépendants", () => {
    const a = entries("A", [
      [1, T],
      [3, T],
      [5, T],
    ]);
    const b = entries("A", [
      [1, F],
      [1, F],
      [1, F],
    ]);
    expect(targetDifficulty(a, "C", "A", LEVELS5)).toBeGreaterThan(targetDifficulty(b, "C", "A", LEVELS5));
    // L'historique de A ne modifie pas la lecture de B quand B a ses propres réponses.
    const own = entries(
      "B",
      [
        [1, F],
        [1, F],
      ],
      10,
    );
    expect(notionMastery([...a, ...own], "C", "B")).toEqual(notionMastery(own, "C", "B"));
  });
});

describe("transfert prudent vers une notion nouvelle", () => {
  const strongProfile = [
    ...entries(
      "A",
      [
        [1, T],
        [3, T],
        [5, T],
        [4, T],
      ],
      1,
    ),
    ...entries(
      "B",
      [
        [1, T],
        [3, T],
        [4, T],
        [5, T],
      ],
      10,
    ),
  ];

  it("profil général solide : départ un peu plus haut que Fondamental, jamais au maximum", () => {
    const m = notionMastery(strongProfile, "C", "Nouvelle");
    expect(m.theta).toBeGreaterThan(1);
    expect(targetDifficulty(strongProfile, "C", "Nouvelle", LEVELS5)).toBeLessThan(5);
  });

  it("le profil général ne dépasse jamais Intermédiaire au départ, même pour un profil parfait", () => {
    const perfect = [...entries("A", Array(10).fill([5, T])), ...entries("B", Array(10).fill([5, T]), 50)];
    expect(targetDifficulty(perfect, "C", "Nouvelle", LEVELS5)).toBeLessThanOrEqual(2);
    expect(notionMastery(perfect, "C", "Nouvelle").theta).toBeLessThanOrEqual(2.5);
  });

  it("un profil faible ne descend jamais sous Fondamental", () => {
    const weak = [...entries("A", Array(10).fill([1, F])), ...entries("B", Array(10).fill([1, F]), 50)];
    expect(targetDifficulty(weak, "C", "Nouvelle", LEVELS5)).toBe(1);
  });

  it("estimation transférée toujours moins certaine qu'une maîtrise démontrée", () => {
    const transferred = notionMastery(strongProfile, "C", "Nouvelle");
    const direct = notionMastery(strongProfile, "C", "A");
    expect(transferred.transferred).toBe(true);
    expect(transferred.sd).toBeGreaterThan(direct.sd);
  });

  it("historique trop court ou trop étroit : aucun transfert", () => {
    const few = entries("A", [
      [1, T],
      [3, T],
      [5, T],
    ]);
    expect(notionMastery(few, "C", "Nouvelle").theta).toBe(initialState().theta);
    expect(notionMastery(few, "C", "Nouvelle").sd).toBe(PRIOR_SD);
    const oneNotion = entries("A", Array(12).fill([5, T]));
    expect(notionMastery(oneNotion, "C", "Nouvelle").transferred).toBe(false);
  });

  it("aucun transfert déduit d'une ressemblance de noms", () => {
    const h = [...entries("Dérivées", Array(6).fill([4, T])), ...entries("Dérivées partielles", [[1, F]], 50)];
    const m = notionMastery(h, "C", "Dérivées secondes");
    expect(m.transferred).toBe(false);
    expect(m.theta).toBe(initialState().theta);
  });

  it("n'écrase jamais les observations de la notion : ses réponses l'emportent", () => {
    const own = entries(
      "Nouvelle",
      [
        [1, F],
        [1, F],
        [1, F],
        [1, F],
      ],
      100,
    );
    const withProfile = notionMastery([...strongProfile, ...own], "C", "Nouvelle");
    const alone = notionMastery(own, "C", "Nouvelle");
    expect(withProfile.theta).toBeLessThan(2);
    expect(Math.abs(withProfile.theta - alone.theta)).toBeLessThan(1);
  });

  it("le prior n'est pas modifié rétroactivement par des réponses ultérieures sur d'autres notions", () => {
    const own = entries(
      "Nouvelle",
      [
        [1, T],
        [2, T],
      ],
      100,
    );
    const later = entries("A", Array(10).fill([1, F]), 500);
    expect(notionMastery([...strongProfile, ...own, ...later], "C", "Nouvelle")).toEqual(
      notionMastery([...strongProfile, ...own], "C", "Nouvelle"),
    );
  });

  it("relations pédagogiques vérifiées : les prérequis travaillés servent de prior atténué", () => {
    const relations = new Map([[notionKey("C", "Nouvelle"), [notionKey("C", "A")]]]);
    const withRel = notionMastery(strongProfile.slice(0, 4), "C", "Nouvelle", { relations });
    expect(withRel.transferred).toBe(true);
    expect(withRel.theta).toBeGreaterThan(1);
    expect(withRel.sd).toBeGreaterThan(notionMastery(strongProfile, "C", "A").sd);
  });
});

describe("pickNextExercise", () => {
  const ex = (id, difficulty, notion = "N") => ({ id, chapter: "C", notion, difficulty });
  const first = () => 0;
  const rightAt = (notion, difficulty, ts) => ({ id: `p${ts}`, chapter: "C", notion, difficulty, correct: T, ts });

  it("choisit un exercice à la difficulté visée (difficulté réelle de la question)", () => {
    const candidates = [ex(1, 1), ex(2, 2), ex(3, 3), ex(4, 4), ex(5, 5)];
    expect(pickNextExercise({ candidates, history: [], usedIds: [], rng: first }).difficulty).toBe(1);
    const history = [rightAt("N", 1, 1)];
    expect(pickNextExercise({ candidates, history, usedIds: [], rng: first }).difficulty).toBe(3);
  });

  it("niveau visé indisponible : repli sur la difficulté disponible la plus proche", () => {
    const candidates = [ex(1, 1), ex(2, 2)];
    const history = [rightAt("N", 1, 1), rightAt("N", 2, 2)];
    expect(pickNextExercise({ candidates, history, usedIds: [], rng: first }).difficulty).toBe(2);
    expect(pickNextExercise({ candidates, history, usedIds: [2], rng: first }).id).toBe(1);
  });

  it("ne ressert jamais un exercice déjà utilisé dans la série et renvoie null quand tout est épuisé", () => {
    const candidates = [ex(1, 1), ex(2, 1)];
    expect(pickNextExercise({ candidates, history: [], usedIds: [1], rng: first }).id).toBe(2);
    expect(pickNextExercise({ candidates, history: [], usedIds: [1, 2], rng: first })).toBeNull();
  });

  it("préfère un exercice jamais fait, sans choisir une difficulté éloignée pour autant", () => {
    const history = [{ id: 1, chapter: "C", notion: "N", correct: F, ts: 1, difficulty: 1 }];
    expect(pickNextExercise({ candidates: [ex(1, 1), ex(2, 1)], history, usedIds: [], rng: first }).id).toBe(2);
    // Un exercice inédit trop éloigné ne l'emporte pas sur une répétition à la bonne difficulté.
    const far = pickNextExercise({ candidates: [ex(1, 1), ex(2, 5)], history, usedIds: [], rng: first });
    expect(far.id).toBe(1);
  });

  it("répartit la série entre les notions, dans l'ordre de priorité fourni", () => {
    const candidates = [ex(1, 1, "A"), ex(2, 1, "A"), ex(3, 1, "B")];
    const order = [notionKey("C", "B"), notionKey("C", "A")];
    expect(pickNextExercise({ candidates, history: [], usedIds: [], notionOrder: order, rng: first }).id).toBe(3);
    expect(pickNextExercise({ candidates, history: [], usedIds: [3], notionOrder: order, rng: first }).notion).toBe(
      "A",
    );
  });

  it("chaque notion garde son propre niveau", () => {
    const candidates = [ex(1, 1, "A"), ex(2, 3, "A"), ex(3, 1, "B"), ex(4, 3, "B")];
    const history = [rightAt("A", 1, 1)];
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
