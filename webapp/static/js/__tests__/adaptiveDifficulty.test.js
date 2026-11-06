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
  notionNeed,
  NEED_WEIGHT,
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

// ── Bloc de calibration des notions nouvelles (ordonnancement uniquement) ────
// Boucle réelle de série : le moteur choisit, l'élève répond, l'historique est
// complété, puis la question suivante est choisie APRÈS cette réponse — même
// enchaînement que exercice.js::queueNextAdaptive.
function runSeries({
  notions,
  outcomes,
  total = outcomes.length,
  pre = [],
  levels = LEVELS5,
  perLevel = 4,
  ts0 = 5000,
}) {
  const candidates = [];
  let id = 0;
  notions.forEach((notion) =>
    levels.forEach((d) => {
      for (let k = 0; k < perLevel; k++)
        candidates.push({ id: `${notion}-${id++}`, chapter: "C", notion, difficulty: d });
    }),
  );
  const order = notions.map((n) => notionKey("C", n));
  const history = [...pre];
  const seriesIds = [];
  const served = [];
  for (let i = 0; i < total; i++) {
    const next = pickNextExercise({
      candidates,
      history,
      usedIds: seriesIds,
      notionOrder: order,
      seriesIds,
      remaining: total - seriesIds.length,
      rng: () => 0,
    });
    if (!next) break;
    seriesIds.push(next.id);
    served.push({ notion: next.notion, d: next.difficulty });
    if (i < outcomes.length) {
      history.push({
        id: next.id,
        chapter: "C",
        notion: next.notion,
        difficulty: next.difficulty,
        correct: outcomes[i],
        ts: ts0 + i,
      });
    }
  }
  return {
    served,
    notionsSeq: served.map((s) => s.notion).join(""),
    levels: served.map((s) => s.d),
    history,
    seriesIds,
    candidates,
    order,
  };
}
const ALL_RIGHT = (n) => Array(n).fill(T);
const known = (notion, ts0) =>
  entries(
    notion,
    [
      [1, T],
      [3, T],
      [5, T],
      [5, T],
    ],
    ts0,
  );

describe("bloc de calibration : 2 premières questions consécutives pour une notion nouvelle", () => {
  it("trois notions nouvelles : A, A, B, B, C, C puis alternance habituelle", () => {
    const r = runSeries({ notions: ["A", "B", "C"], outcomes: ALL_RIGHT(10) });
    expect(r.notionsSeq).toBe("AABBCCABCA");
    // La 2e question est choisie après la 1re réponse : réussite au Fondamental -> sondage plus haut.
    expect(r.levels.slice(0, 6)).toEqual([1, 3, 1, 3, 1, 3]);
  });

  it("une seule notion : fonctionnement inchangé (même séquence qu'avant)", () => {
    const withBlock = runSeries({ notions: ["A"], outcomes: ALL_RIGHT(10) }).levels;
    const before = [];
    const history = [];
    const cands = runSeries({ notions: ["A"], outcomes: [], total: 0 }).candidates;
    const used = [];
    for (let i = 0; i < 10; i++) {
      const next = pickNextExercise({ candidates: cands, history, usedIds: used, rng: () => 0 });
      used.push(next.id);
      before.push(next.difficulty);
      history.push({ id: next.id, chapter: "C", notion: "A", difficulty: next.difficulty, correct: T, ts: 5000 + i });
    }
    expect(withBlock).toEqual(before);
  });

  it("trois notions déjà connues : alternance habituelle, aucune recalibration", () => {
    const pre = [...known("A", 1), ...known("B", 10), ...known("C", 20)];
    const r = runSeries({ notions: ["A", "B", "C"], outcomes: ALL_RIGHT(6), pre });
    expect(r.notionsSeq).toBe("ABCABC");
    // Maîtrise reprise : jamais de retour au Fondamental.
    expect(Math.min(...r.levels)).toBeGreaterThanOrEqual(4);
  });

  it("mélange : seule la notion nouvelle est regroupée, les notions connues gardent leur niveau", () => {
    const pre = [...known("A", 1), ...known("C", 20)];
    const r = runSeries({ notions: ["A", "B", "C"], outcomes: ALL_RIGHT(8), pre });
    // Après A, B, B, C : les notions les moins servies d'abord (A puis C), puis
    // à égalité la moins récemment servie (B) — jamais deux fois de suite hors bloc.
    expect(r.notionsSeq).toBe("ABBCACBA");
    expect(r.notionsSeq.slice(3)).not.toMatch(/(.)\1/);
    r.served.filter((s) => s.notion !== "B").forEach((s) => expect(s.d).toBeGreaterThanOrEqual(4));
    // B part du prior transféré existant (profil général, A et C déjà travaillées),
    // puis sa 2e question, choisie après la réussite, est plus difficile.
    const [b1, b2] = r.served.filter((s) => s.notion === "B").map((s) => s.d);
    expect(b1).toBe(targetDifficulty(pre, "C", "B", LEVELS5));
    expect(b2).toBeGreaterThan(b1);
  });

  it("notion connue en tête puis deux nouvelles : A, B, B, C, C, puis répartition sans répétition injustifiée", () => {
    const r = runSeries({ notions: ["A", "B", "C"], outcomes: ALL_RIGHT(10), pre: known("A", 1) });
    expect(r.notionsSeq.slice(0, 5)).toBe("ABBCC");
    // Après les blocs : jamais deux fois de suite la même notion (parts proches).
    expect(r.notionsSeq.slice(4)).not.toMatch(/(.)\1/);
    // A (déjà maîtrisée) ne reçoit pas plus de questions que les notions nouvelles.
    const n = (x) => [...r.notionsSeq].filter((c) => c === x).length;
    expect(n("A")).toBeLessThanOrEqual(Math.min(n("B"), n("C")));
  });

  it("réussite puis échec : la difficulté suivante reste celle du moteur (repli prudent)", () => {
    const r = runSeries({ notions: ["A", "B"], outcomes: [T, F, T, T, T, T] });
    expect(r.notionsSeq.slice(0, 4)).toBe("AABB");
    const nextA = r.served.findIndex((s, i) => i > 1 && s.notion === "A");
    // Après 1 (réussi) puis 3 (échoué), le moteur redescend : jamais plus haut que 3.
    expect(r.levels[nextA]).toBeLessThanOrEqual(2);
  });

  it("plus de cinq notions dans une série de dix : chaque notion reçoit au moins une question", () => {
    const notions = ["A", "B", "C", "D", "E", "F"];
    const r = runSeries({ notions, outcomes: ALL_RIGHT(10) });
    expect(r.notionsSeq).toBe("AABBCCDDEF");
    expect(new Set(r.notionsSeq).size).toBe(6);
    const seven = runSeries({ notions: [...notions, "G"], outcomes: ALL_RIGHT(10) });
    expect(new Set(seven.notionsSeq).size).toBe(7);
  });

  it("aucune question dupliquée et pool épuisé : la série continue sans bloquer", () => {
    // Une seule question par niveau et par notion (2 niveaux) : 2 questions par notion.
    const r = runSeries({ notions: ["A", "B"], outcomes: ALL_RIGHT(6), levels: [1, 2], perLevel: 1 });
    expect(new Set(r.seriesIds).size).toBe(r.seriesIds.length);
    expect(r.notionsSeq).toBe("AABB");
    // Notion avec une seule question : pas de second exemplaire, notion suivante.
    const single = runSeries({ notions: ["A", "B"], outcomes: ALL_RIGHT(3), levels: [1], perLevel: 1 });
    expect(single.notionsSeq).toBe("AB");
  });

  it("dernière question pas encore répondue (série interrompue) : aucun regroupement anticipé", () => {
    const r = runSeries({ notions: ["A", "B"], outcomes: [], total: 1 });
    const next = pickNextExercise({
      candidates: r.candidates,
      history: r.history,
      usedIds: r.seriesIds,
      notionOrder: r.order,
      seriesIds: r.seriesIds,
      remaining: 9,
      rng: () => 0,
    });
    expect(next.notion).toBe("B");
  });

  it("reprise : le bloc est recalculé depuis la file et l'historique (aucun état caché)", () => {
    const full = runSeries({ notions: ["A", "B", "C"], outcomes: ALL_RIGHT(10) });
    // Reprise après la 1re question de B (index 2) : même choix que sans interruption.
    const seriesIds = full.seriesIds.slice(0, 3);
    const history = full.history.slice(0, 3);
    const next = pickNextExercise({
      candidates: full.candidates,
      history,
      usedIds: seriesIds,
      notionOrder: full.order,
      seriesIds,
      remaining: 7,
      rng: () => 0,
    });
    expect(next.id).toBe(full.seriesIds[3]);
  });

  it("nouvelle série sur les mêmes notions : plus de regroupement (notions déjà travaillées)", () => {
    const first = runSeries({ notions: ["A", "B", "C"], outcomes: ALL_RIGHT(10) });
    const second = runSeries({ notions: ["A", "B", "C"], outcomes: ALL_RIGHT(6), pre: first.history, ts0: 9000 });
    // Premier passage dans l'ordre, sans bloc de deux (aucune recalibration),
    // puis répartition selon le besoin, sans répétition immédiate.
    expect(second.notionsSeq.slice(0, 3)).toBe("ABC");
    expect(second.notionsSeq).not.toMatch(/(.)\1/);
    expect(Math.min(...second.levels)).toBeGreaterThanOrEqual(3);
  });

  it("doublon de synchronisation (même réponse deux fois) : le bloc s'applique quand même", () => {
    const r = runSeries({ notions: ["A", "B"], outcomes: [], total: 1 });
    const answer = { id: r.seriesIds[0], chapter: "C", notion: "A", difficulty: 1, correct: T, ts: 42 };
    const next = pickNextExercise({
      candidates: r.candidates,
      history: [answer, { ...answer }],
      usedIds: r.seriesIds,
      notionOrder: r.order,
      seriesIds: r.seriesIds,
      remaining: 9,
      rng: () => 0,
    });
    expect(next.notion).toBe("A");
    expect(next.difficulty).toBe(3);
  });

  it("classe à 4 niveaux : même ordonnancement, difficultés dans 1..4", () => {
    const r = runSeries({ notions: ["A", "B", "C"], outcomes: ALL_RIGHT(10), levels: [1, 2, 3, 4] });
    expect(r.notionsSeq).toBe("AABBCCABCA");
    expect(r.levels.slice(0, 6)).toEqual([1, 3, 1, 3, 1, 3]);
    expect(Math.max(...r.levels)).toBeLessThanOrEqual(4);
  });

  it("sans file de série transmise : comportement historique strictement inchangé", () => {
    const r = runSeries({ notions: ["A", "B", "C"], outcomes: [], total: 0 });
    const history = [{ id: r.candidates[0].id, chapter: "C", notion: "A", difficulty: 1, correct: T, ts: 1 }];
    const next = pickNextExercise({
      candidates: r.candidates,
      history,
      usedIds: [r.candidates[0].id],
      notionOrder: r.order,
      rng: () => 0,
    });
    expect(next.notion).toBe("B");
  });
});

// ── Répartition du nombre de questions selon le besoin de chaque notion ─────
// Vraie boucle de série (choix -> réponse -> choix suivant APRÈS la réponse),
// avec des résultats fixés PAR NOTION : `answerOf(notion, k)` donne la k-ième
// réponse de l'élève sur cette notion dans la série.
function runByNotion({
  notions,
  answerOf,
  total = 10,
  pre = [],
  levels = LEVELS5,
  perLevel = 6,
  sizes = {},
  ts0 = 20000,
}) {
  const candidates = [];
  let id = 0;
  notions.forEach((n) =>
    levels.forEach((d) => {
      const k = sizes[n] ? (d === levels[0] ? sizes[n] : 0) : perLevel;
      for (let j = 0; j < k; j++) candidates.push({ id: `${n}#${id++}`, chapter: "C", notion: n, difficulty: d });
    }),
  );
  const order = notions.map((n) => notionKey("C", n));
  const history = [...pre];
  const seriesIds = [];
  const served = [];
  const count = Object.fromEntries(notions.map((n) => [n, 0]));
  for (let i = 0; i < total; i++) {
    const next = pickNextExercise({
      candidates,
      history,
      usedIds: seriesIds,
      notionOrder: order,
      seriesIds,
      remaining: total - seriesIds.length,
      rng: () => 0,
    });
    if (!next) break;
    const ok = answerOf(next.notion, count[next.notion]++);
    seriesIds.push(next.id);
    served.push({ notion: next.notion, d: next.difficulty, ok });
    history.push({
      id: next.id,
      chapter: "C",
      notion: next.notion,
      difficulty: next.difficulty,
      correct: ok,
      ts: ts0 + i,
    });
  }
  return { served, count, seq: served.map((s) => s.notion).join(""), history, seriesIds, candidates, order };
}
const RIGHT = () => T;
const WRONG = () => F;
const MIXED = (k) => k % 2 === 0;
const by = (a, b, c) => (n, k) => ({ A: a, B: b, C: c })[n](k);
const strongA = (ts0 = 1) =>
  entries(
    "A",
    [
      [3, T],
      [4, T],
      [5, T],
      [5, T],
    ],
    ts0,
  );
const weakB = (ts0 = 20) =>
  entries(
    "B",
    [
      [1, F],
      [1, T],
      [2, F],
      [1, F],
    ],
    ts0,
  );
const midC = (ts0 = 40) =>
  entries(
    "C",
    [
      [2, T],
      [3, F],
      [2, T],
      [3, T],
    ],
    ts0,
  );

describe("répartition des questions selon le besoin de chaque notion", () => {
  it("test comparatif : B en difficulté reçoit plus que A ; résultats inversés -> répartition inversée", () => {
    const scenarioA = runByNotion({ notions: ["A", "B", "C"], answerOf: by(RIGHT, WRONG, MIXED), total: 15 });
    const scenarioB = runByNotion({ notions: ["A", "B", "C"], answerOf: by(WRONG, RIGHT, MIXED), total: 15 });
    expect(scenarioA.count.B).toBeGreaterThan(scenarioA.count.A);
    expect(scenarioB.count.A).toBeGreaterThan(scenarioB.count.B);
    // Toutes choses égales par ailleurs : inversion exacte des parts de A et B.
    expect(scenarioB.count.A).toBe(scenarioA.count.B);
    expect(scenarioB.count.B).toBe(scenarioA.count.A);
    expect(scenarioB.count.C).toBe(scenarioA.count.C);
  });

  it("notions déjà connues (A forte, B faible, C moyenne) : B > C > A sur dix questions, total inchangé", () => {
    const r = runByNotion({
      notions: ["A", "B", "C"],
      answerOf: by(RIGHT, WRONG, MIXED),
      pre: [...strongA(), ...weakB(), ...midC()],
    });
    expect(r.served).toHaveLength(10);
    expect(r.count.B).toBeGreaterThan(r.count.C);
    expect(r.count.C).toBeGreaterThan(r.count.A);
    expect(r.count.A).toBeGreaterThanOrEqual(1); // la notion maîtrisée est encore vérifiée
  });

  it("deux notions, une maîtrisée et une faible : la faible reçoit davantage, sans monopoliser la série", () => {
    const r = runByNotion({ notions: ["A", "B"], answerOf: by(RIGHT, WRONG, RIGHT), pre: [...strongA(), ...weakB()] });
    expect(r.count.B).toBeGreaterThan(r.count.A);
    // Protection : la part de la notion faible reste bornée (poids au plus 1 + NEED_WEIGHT).
    expect(r.count.A).toBeGreaterThanOrEqual(Math.floor(10 / (2 + NEED_WEIGHT)));
  });

  it("plusieurs échecs sur une notion : elle est davantage travaillée, mais les autres ne disparaissent pas", () => {
    const r = runByNotion({ notions: ["A", "B", "C"], answerOf: by(RIGHT, WRONG, RIGHT), total: 15 });
    expect(r.count.B).toBe(Math.max(...Object.values(r.count)));
    expect(Math.min(r.count.A, r.count.C)).toBeGreaterThanOrEqual(3);
  });

  it("réussites puis échecs sur une même notion : sa part augmente (par rapport à des réussites)", () => {
    const thenFail = runByNotion({ notions: ["A", "B", "C"], answerOf: by(RIGHT, (k) => k < 2, RIGHT), total: 15 });
    const allRight = runByNotion({ notions: ["A", "B", "C"], answerOf: by(RIGHT, RIGHT, RIGHT), total: 15 });
    expect(thenFail.count.B).toBeGreaterThan(allRight.count.B);
  });

  it("échecs puis réussites : la priorité baisse progressivement (moins qu'en échec continu)", () => {
    const recover = runByNotion({ notions: ["A", "B", "C"], answerOf: by(RIGHT, (k) => k >= 3, RIGHT), total: 15 });
    const keepFailing = runByNotion({ notions: ["A", "B", "C"], answerOf: by(RIGHT, WRONG, RIGHT), total: 15 });
    expect(recover.count.B).toBeLessThanOrEqual(keepFailing.count.B);
    // Le besoin de B diminue bien après ses réussites.
    const needAt = (r, upto) => notionNeed(notionMastery(r.history.slice(0, upto), "C", "B"), LEVELS5);
    expect(needAt(recover, recover.history.length)).toBeLessThan(needAt(keepFailing, keepFailing.history.length));
  });

  it("la difficulté évolue indépendamment dans chaque notion (A monte, B reste au Fondamental)", () => {
    const r = runByNotion({ notions: ["A", "B", "C"], answerOf: by(RIGHT, WRONG, MIXED), total: 15 });
    const levelsOf = (n) => r.served.filter((s) => s.notion === n).map((s) => s.d);
    expect(levelsOf("A").slice(0, 3)).toEqual([1, 3, 5]);
    expect(Math.max(...levelsOf("B"))).toBe(1);
    // Chaque difficulté servie est exactement celle visée par le moteur à cet instant.
    r.served.forEach((s, i) => {
      const before = r.history.slice(0, i);
      const levels = r.candidates.filter((c) => c.notion === s.notion).map((c) => c.difficulty);
      expect(s.d).toBe(targetDifficulty(before, "C", s.notion, levels));
    });
  });

  it("plus de notions que de questions : une question par notion, aucun bloc de deux", () => {
    const notions = "ABCDEFGHIJKL".split("");
    const r = runByNotion({ notions, answerOf: () => T });
    expect(new Set(r.seq).size).toBe(10);
  });

  it("pool épuisé pour une notion faible : places redistribuées, série complète, aucune question répétée", () => {
    const r = runByNotion({ notions: ["A", "B", "C"], answerOf: by(RIGHT, WRONG, MIXED), sizes: { B: 2 } });
    expect(r.count.B).toBe(2);
    expect(r.served).toHaveLength(10);
    expect(new Set(r.seriesIds).size).toBe(10);
  });

  it("reprise / rechargement : chaque choix ne dépend que de la file et de l'historique (déterministe)", () => {
    const full = runByNotion({ notions: ["A", "B", "C"], answerOf: by(RIGHT, WRONG, MIXED), total: 12 });
    for (let k = 1; k < 12; k++) {
      const next = pickNextExercise({
        candidates: full.candidates,
        history: full.history.slice(0, k),
        usedIds: full.seriesIds.slice(0, k),
        notionOrder: full.order,
        seriesIds: full.seriesIds.slice(0, k),
        remaining: 12 - k,
        rng: () => 0,
      });
      expect(next.id).toBe(full.seriesIds[k]);
    }
  });

  it("historique ancien : maîtrise basse -> plus de questions qu'une maîtrise élevée, à résultats égaux", () => {
    const r = runByNotion({ notions: ["A", "B"], answerOf: () => MIXED(0), pre: [...strongA(), ...weakB()] });
    expect(r.count.B).toBeGreaterThan(r.count.A);
  });

  it("4 ou 5 niveaux : une notion au sommet de SON échelle n'est pas pénalisée", () => {
    expect(notionNeed({ theta: 4, sd: SD_MIN }, [1, 2, 3, 4])).toBe(0);
    expect(notionNeed({ theta: 5, sd: SD_MIN }, LEVELS5)).toBe(0);
    expect(notionNeed({ theta: 1, sd: SD_MIN }, [1, 2, 3, 4])).toBe(1);
    const four = runByNotion({
      notions: ["A", "B", "C"],
      answerOf: by(RIGHT, WRONG, MIXED),
      total: 15,
      levels: [1, 2, 3, 4],
    });
    expect(four.count.B).toBeGreaterThan(four.count.A);
    expect(Math.max(...four.served.map((s) => s.d))).toBeLessThanOrEqual(4);
  });

  it("une erreur isolée ne bouleverse pas la répartition", () => {
    const oneSlip = runByNotion({
      notions: ["A", "B"],
      answerOf: by((k) => k !== 1, RIGHT, RIGHT),
      pre: [
        ...strongA(),
        ...entries(
          "B",
          [
            [3, T],
            [4, T],
            [5, T],
            [5, T],
          ],
          20,
        ),
      ],
    });
    expect(Math.abs(oneSlip.count.A - oneSlip.count.B)).toBeLessThanOrEqual(2);
  });

  it("une seule notion : répartition sans effet (toutes les questions sur cette notion)", () => {
    const r = runByNotion({ notions: ["A"], answerOf: MIXED });
    expect(r.count.A).toBe(10);
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
