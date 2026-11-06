// ── Moteur adaptatif par notion ──────────────────────────────────────────────
// Fonctions pures (aucun accès au DOM, au stockage ni au réseau), utilisées par
// exercice.js pour choisir l'exercice SUIVANT d'une série après chaque réponse.
//
// Trois responsabilités distinctes :
//   A. estimation de maîtrise  : (theta, sd) par élève et par notion ;
//   B. estimation initiale     : prior d'une notion sans réponse propre ;
//   C. sélection pédagogique   : difficulté visée -> vraie question disponible.
// Le niveau estimé de l'élève (theta) n'est JAMAIS confondu avec la difficulté
// de la question effectivement posée (celle-ci est lue sur la question).
//
// L'état n'est jamais stocké : il est recalculé en rejouant, dans l'ordre, les
// réponses de l'historique (serveur, source de vérité) sur la notion. Il est
// donc identique d'une série, d'un rechargement et d'un navigateur à l'autre.
//
// ── A. Modèle (mise à jour bayésienne gaussienne à lien logistique, 1 pas par
// réponse) ─────────────────────────────────────────────────────────────────
//   theta : maîtrise sur l'échelle des difficultés 1..5 (Fondamental..Défi),
//           bornée à [THETA_MIN, THETA_MAX] (marge hors 1..5 pour que des
//           erreurs au niveau 1 ou des réussites au niveau 5 restent
//           informatives sans jamais saturer définitivement) ;
//   sd    : incertitude (écart-type) dans [SD_MIN, PRIOR_SD].
//   Réponse y (1 = réussie) à la difficulté d, avec un poids w ∈ ]0, 1] :
//     var = sd² + DRIFT_VAR                 (la maîtrise peut évoluer : les
//                                            progrès/baisses restent possibles)
//     p   = 1 / (1 + exp(-(theta - d) / SLOPE))   (modèle d'attente, NON une
//                                            probabilité calibrée)
//     v   = 1 / (1/var + w·p(1-p)/SLOPE²)   (variance a posteriori)
//     theta' = clamp(theta + v·w·(y - p)/SLOPE)
//     sd'    = clamp(sqrt(v))
//   Une réussite à une difficulté élevée (p faible) déplace beaucoup plus
//   theta qu'une réussite à Fondamental ; l'incertitude forte donne un pas
//   large (réaction rapide), l'incertitude faible un pas petit (stabilité) ;
//   DRIFT_VAR empêche l'incertitude de tomber à zéro (reprise possible).
//   Une réponse sans difficulté connue n'apporte aucune information (ignorée).
//
// ── B. Notion sans réponse propre ──────────────────────────────────────────
//   1) relations pédagogiques vérifiées (`relations`, optionnel) : prior tiré
//      des prérequis déjà travaillés, atténué (TRANSFER_PREREQ) ;
//   2) à défaut, faible influence du profil général (autres notions de la
//      classe) si l'historique est assez représentatif ;
//   3) sinon prior neutre (Fondamental, incertitude maximale).
//   Aucune relation « par ressemblance de noms ». Le prior transféré a toujours
//   une incertitude supérieure à celle d'une maîtrise démontrée (TRANSFER_SD),
//   et est calculé uniquement sur les réponses ANTÉRIEURES à la première
//   réponse de la notion : il ne la modifie jamais rétroactivement.
//
// ── C. Sélection ───────────────────────────────────────────────────────────
//   Difficulté visée (continue) :
//     aucune réponse        : theta du prior (Fondamental par défaut) ;
//     calibration (< 3 rép.) et dernière réponse réussie : difficulté de cette
//        réponse + PROBE_STEP (Q1 Fondamental, Q2 Avancé, Q3 Défi pour un
//        élève qui réussit ; niveaux absents : repli sur le plus proche) ; après un échec : cible prudente (ci-dessous) ;
//     ensuite : theta - TARGET_OFFSET + PROGRESS_SD·(sd - SD_MIN) — un peu
//        sous la maîtrise estimée (réussite attendue plutôt élevée, pour
//        consolider), relevée tant que l'incertitude reste forte.
//   Parmi les exercices inédits de la série, coût = |difficulté - visée|, plus
//   REPEAT_PENALTY si l'exercice a déjà été rencontré (variété sans choisir une
//   mauvaise difficulté) ; à égalité, la difficulté la plus basse. Si le niveau
//   visé n'existe pas, repli sur la difficulté disponible la plus proche — ce
//   repli ne modifie jamais la maîtrise.

export const CALIBRATION_ANSWERS = 3;
export const PRIOR_MEAN = 1;
export const PRIOR_SD = 3;
export const SLOPE = 0.5;
export const DRIFT_VAR = 0.06;
export const SD_MIN = 0.4;
export const THETA_MIN = 0.5;
export const THETA_MAX = 5.5;
export const REPEAT_WEIGHT = 0.5;
export const PROBE_STEP = 2;
export const TARGET_OFFSET = 0.1;
export const PROGRESS_SD = 0.4;
export const REPEAT_PENALTY = 0.6;
export const TRANSFER_PREREQ = 0.5;
export const TRANSFER_GENERAL = 0.3;
export const TRANSFER_MAX_THETA = 2.5;
export const TRANSFER_SD = 2.2;
export const GENERAL_MIN_ANSWERS = 8;
export const GENERAL_MIN_NOTIONS = 2;
export const PREREQ_MIN_ANSWERS = 3;

export function notionKey(chapter, notion) {
  return `${chapter}|${notion}`;
}

const clamp = (x, lo, hi) => Math.min(hi, Math.max(lo, x));
const byTime = (a, b) => (a.ts || 0) - (b.ts || 0);

/** Attente de réussite d'un élève de maîtrise `theta` à la difficulté `d`. */
export function expectedSuccess(theta, d) {
  return 1 / (1 + Math.exp(-(theta - d) / SLOPE));
}

/** État initial : prior neutre, ou prior transféré {theta, sd}. */
export function initialState(prior = null) {
  return {
    theta: clamp(prior?.theta ?? PRIOR_MEAN, THETA_MIN, THETA_MAX),
    sd: clamp(prior?.sd ?? PRIOR_SD, SD_MIN, PRIOR_SD),
    n: 0,
    lastCorrect: null,
    lastDifficulty: null,
    transferred: Boolean(prior),
  };
}

/** Mise à jour d'une réponse (fonction pure, renvoie un nouvel état). */
export function updateMastery(state, difficulty, correct, weight = 1) {
  if (typeof difficulty !== "number" || !Number.isFinite(difficulty)) return state;
  const w = clamp(weight, 0, 1);
  const variance = state.sd * state.sd + DRIFT_VAR;
  const p = expectedSuccess(state.theta, difficulty);
  const post = 1 / (1 / variance + (w * p * (1 - p)) / (SLOPE * SLOPE));
  const theta = clamp(state.theta + (post * w * ((correct ? 1 : 0) - p)) / SLOPE, THETA_MIN, THETA_MAX);
  return {
    theta,
    sd: clamp(Math.sqrt(post), SD_MIN, PRIOR_SD),
    n: state.n + 1,
    lastCorrect: Boolean(correct),
    lastDifficulty: difficulty,
    transferred: state.transferred,
  };
}

/** Réponses d'une notion, chronologiques, sans doublon de synchronisation
 * (même exercice au même instant) ; chaque entrée porte son poids : une
 * réussite ou erreur sur un exercice déjà rencontré compte moitié moins. */
function weightedAnswers(answers) {
  const seenEntries = new Set();
  const seenIds = new Set();
  const out = [];
  [...answers].sort(byTime).forEach((a) => {
    const entryKey = `${a.id}@${a.ts}`;
    if (a.id != null && a.ts != null) {
      if (seenEntries.has(entryKey)) return;
      seenEntries.add(entryKey);
    }
    const repeat = a.id != null && seenIds.has(a.id);
    if (a.id != null) seenIds.add(a.id);
    out.push({ difficulty: a.difficulty, correct: a.correct, weight: repeat ? REPEAT_WEIGHT : 1 });
  });
  return out;
}

/** Rejoue des réponses ([{id, ts, difficulty, correct}]) depuis `prior`. */
export function replayMastery(answers, prior = null) {
  return weightedAnswers(answers).reduce(
    (st, a) => updateMastery(st, a.difficulty, a.correct, a.weight),
    initialState(prior),
  );
}

function answersOf(history, chapter, notion) {
  return history.filter((h) => h.chapter === chapter && h.notion === notion);
}

/** Prior d'une notion sans réponse propre (B). Seules les réponses antérieures
 * à `beforeTs` sont utilisées. `relations` : Map notionKey -> [notionKey de
 * prérequis vérifiés] (optionnel ; aucune relation n'est supposée). */
export function transferPrior(history, chapter, notion, { beforeTs = Infinity, relations = null } = {}) {
  const past = history.filter((h) => (h.ts || 0) < beforeTs && !(h.chapter === chapter && h.notion === notion));
  const stateOf = (c, n) => replayMastery(answersOf(past, c, n));

  const prereqs = relations?.get(notionKey(chapter, notion)) || [];
  const known = prereqs
    .map((key) => {
      const [c, ...rest] = key.split("|");
      return stateOf(c, rest.join("|"));
    })
    .filter((s) => s.n >= PREREQ_MIN_ANSWERS);
  if (known.length) {
    const mean = known.reduce((s, k) => s + k.theta, 0) / known.length;
    return {
      theta: clamp(PRIOR_MEAN + TRANSFER_PREREQ * (mean - PRIOR_MEAN), PRIOR_MEAN, TRANSFER_MAX_THETA),
      sd: TRANSFER_SD,
    };
  }

  // Profil général : assez de réponses sur au moins deux autres notions.
  const keys = new Map();
  past.forEach((h) => {
    if (h.chapter && h.notion) keys.set(notionKey(h.chapter, h.notion), [h.chapter, h.notion]);
  });
  const states = [...keys.values()].map(([c, n]) => stateOf(c, n)).filter((s) => s.n > 0);
  const total = states.reduce((s, k) => s + k.n, 0);
  if (states.length < GENERAL_MIN_NOTIONS || total < GENERAL_MIN_ANSWERS) return null;
  const mean = states.reduce((s, k) => s + k.theta * k.n, 0) / total;
  return {
    theta: clamp(PRIOR_MEAN + TRANSFER_GENERAL * (mean - PRIOR_MEAN), PRIOR_MEAN, TRANSFER_MAX_THETA),
    sd: TRANSFER_SD,
  };
}

/** État de maîtrise d'une notion pour cet élève : réponses propres rejouées
 * depuis le prior (neutre ou transféré). */
export function notionMastery(history, chapter, notion, opts = {}) {
  const answers = answersOf(history, chapter, notion).sort(byTime);
  const prior = transferPrior(history, chapter, notion, {
    beforeTs: answers[0]?.ts ?? Infinity,
    relations: opts.relations,
  });
  const state = replayMastery(answers, prior);
  return { ...state, calibrated: state.n >= CALIBRATION_ANSWERS };
}

/** Difficulté visée (continue) pour la prochaine question. */
export function targetValue(state) {
  if (state.n === 0) return state.theta;
  // Politique diagnostique (indépendante du calcul de theta) : pendant la
  // calibration, une réussite fait sonder PROBE_STEP niveaux plus haut que la
  // question réussie (1 -> 3 -> 5) ; le niveau réellement disponible le plus
  // proche est ensuite retenu. Après un échec, c'est la maîtrise estimée qui décide.
  if (state.n < CALIBRATION_ANSWERS && state.lastCorrect && state.lastDifficulty != null) {
    return state.lastDifficulty + PROBE_STEP;
  }
  const target = state.theta - TARGET_OFFSET + PROGRESS_SD * (state.sd - SD_MIN);
  // Juste après une réussite, jamais en dessous de la difficulté réussie : sans
  // ce plancher, la fin du sondage (cible revenue sous la difficulté sondée)
  // faisait reculer l'élève après une bonne réponse (ex. 1 -> 3 -> 2). Ce
  // plancher ne fait pas monter la difficulté ; une erreur le lève aussitôt.
  if (state.lastCorrect && state.lastDifficulty != null) return Math.max(target, state.lastDifficulty);
  return target;
}

/** Difficulté disponible la plus proche de `value` (la plus basse à égalité). */
export function nearestLevel(levels, value) {
  let best = null;
  for (const d of [...levels].sort((a, b) => a - b)) {
    if (best == null || Math.abs(d - value) < Math.abs(best - value)) best = d;
  }
  return best;
}

/** Difficulté visée pour une notion, parmi les `levels` réellement disponibles. */
export function targetDifficulty(history, chapter, notion, levels, opts = {}) {
  const sorted = [...new Set(levels)].filter((d) => d != null);
  if (!sorted.length) return null;
  return nearestLevel(sorted, targetValue(notionMastery(history, chapter, notion, opts)));
}

/** Nombre de questions consécutives d'une notion NOUVELLE au début de sa
 * calibration (ordonnancement uniquement, voir calibrationBlockGroup). */
export const CALIBRATION_BLOCK = 2;

/** Groupe (notion) à reservir immédiatement pour compléter le bloc de
 * calibration de la dernière notion servie, ou null. Conditions, toutes
 * déduites de la file de la série et de l'historique (aucun état stocké :
 * identique après rechargement ou reprise) :
 *   - la dernière question de la série appartient à cette notion et a déjà
 *     reçu sa réponse (la suivante est donc choisie APRÈS cette réponse) ;
 *   - la notion était nouvelle au début de la série : sa seule réponse est
 *     celle-ci (une notion déjà travaillée garde l'alternance) ;
 *   - elle a été servie moins de CALIBRATION_BLOCK fois dans la série et il
 *     lui reste une question inédite ;
 *   - le regroupement laisse encore au moins une question à chaque notion pas
 *     encore servie (séries courtes avec beaucoup de notions). */
function calibrationBlockGroup(groups, history, seriesIds, remaining) {
  if (!seriesIds?.length) return null;
  const lastId = seriesIds[seriesIds.length - 1];
  const inSeries = new Set(seriesIds);
  const group = [...groups.values()].find((g) => g.all.some((c) => c.id === lastId));
  if (!group || !group.fresh.length) return null;
  if (group.all.filter((c) => inSeries.has(c.id)).length >= CALIBRATION_BLOCK) return null;
  // Une seule réponse dans tout l'historique, celle de la question qui vient
  // d'être servie : la notion était donc nouvelle au début de la série.
  // (doublons de synchronisation — même exercice, même instant — comptés une fois)
  const answers = [
    ...new Map(answersOf(history, group.chapter, group.notion).map((a) => [`${a.id}@${a.ts}`, a])).values(),
  ];
  if (answers.length !== 1 || answers[0].id !== lastId) return null;
  if (remaining != null) {
    const unserved = [...groups.values()].filter(
      (g) => g !== group && g.fresh.length && !g.all.some((c) => inSeries.has(c.id)),
    ).length;
    if (remaining - 1 < unserved) return null;
  }
  return group;
}

// ── Répartition des questions entre les notions d'une série ─────────────────
// Ordonnancement uniquement : la difficulté de chaque question reste choisie
// par le moteur (targetValue), et la maîtrise (theta, sd) est celle calculée
// ci-dessus — aucun second système d'estimation.
//   besoin  = écart entre la maîtrise estimée et le plus haut niveau que la
//             notion propose réellement (0 = maîtrisée, 1 = tout à travailler),
//             + UNCERTAINTY_WEIGHT × incertitude normalisée (peu de preuves ->
//             à vérifier), borné à [0, 1]. Mesuré par rapport à la notion
//             elle-même : une notion aux questions plus difficiles n'est pas
//             pénalisée. Lissé par le modèle bayésien : une erreur isolée ne
//             déplace theta que modérément (jamais un pourcentage brut).
//   poids   = 1 + NEED_WEIGHT × besoin, donc dans [1, 1 + NEED_WEIGHT] : une
//             notion maîtrisée garde toujours une part (vérification des
//             acquis) et une notion faible ne peut pas recevoir plus de
//             (1 + NEED_WEIGHT) fois la part d'une notion maîtrisée
//             (protection contre la monopolisation).
//   choix   = la notion de plus grand poids / (questions déjà servies + 1) :
//             répartition proportionnelle au besoin, recalculée après chaque
//             réponse (aucun quota fixé au départ).
//   répétition : la notion qui vient d'être servie n'est reservie aussitôt que
//             si sa part dépasse d'au moins REPEAT_MARGIN celle de la suivante
//             (priorité pédagogique nettement supérieure).
export const NEED_WEIGHT = 2;
export const UNCERTAINTY_WEIGHT = 0.5;
export const REPEAT_MARGIN = 1.25;

/** Besoin de travail d'une notion, dans [0, 1], à partir de son état de
 * maîtrise et des niveaux qu'elle propose réellement. */
export function notionNeed(state, levels) {
  const valid = levels.filter((d) => typeof d === "number");
  const top = valid.length ? Math.max(...valid) : THETA_MAX;
  const low = valid.length ? Math.min(...valid) : 1;
  const gap = top > low ? clamp((top - state.theta) / (top - low), 0, 1) : state.theta >= top ? 0 : 1;
  const uncertainty = clamp((state.sd - SD_MIN) / (PRIOR_SD - SD_MIN), 0, 1);
  return clamp(gap + UNCERTAINTY_WEIGHT * uncertainty, 0, 1);
}

/** Poids de répartition d'une notion dans [1, 1 + NEED_WEIGHT]. */
export function notionWeight(state, levels) {
  return 1 + NEED_WEIGHT * notionNeed(state, levels);
}

/** Choisit le prochain exercice d'une série adaptative, ou `null` s'il n'en
 * reste aucun d'inédit.
 *   candidates  : [{id, chapter, notion, difficulty}]
 *   history     : historique de la classe active
 *   usedIds     : ids déjà servis (ou écartés) dans CETTE série
 *   notionOrder : clés notionKey par priorité (départage à égalité)
 *   relations   : prérequis vérifiés (optionnel, voir transferPrior)
 *   seriesIds   : ids servis dans CETTE série, dans l'ordre (optionnel) —
 *                 active le bloc de calibration des notions nouvelles
 *   remaining   : questions restant à servir, celle-ci comprise (optionnel)
 *   rng         : générateur [0, 1) (injectable pour les tests) */
export function pickNextExercise({
  candidates,
  history,
  usedIds,
  notionOrder = [],
  relations = null,
  seriesIds = null,
  remaining = null,
  rng = Math.random,
}) {
  const used = new Set(usedIds);
  const groups = new Map();
  for (const c of candidates) {
    const key = notionKey(c.chapter, c.notion);
    if (!groups.has(key)) groups.set(key, { chapter: c.chapter, notion: c.notion, all: [], fresh: [] });
    const g = groups.get(key);
    g.all.push(c);
    if (!used.has(c.id)) g.fresh.push(c);
  }
  const available = [...groups.entries()].filter(([, g]) => g.fresh.length);
  if (!available.length) return null;

  // Notion la moins servie dans la série (répartition équilibrée), puis la
  // moins récemment servie (sans file transmise, ou en alternance simple, cela
  // revient exactement à l'ordre de priorité), puis l'ordre de priorité fourni.
  // Le départage par récence évite qu'une notion repasse juste après elle-même
  // à la fin des blocs de calibration (A, A, B, B, C, C, puis A, B, C…).
  const servedIn = (g) => g.all.length - g.fresh.length;
  const rank = (key) => {
    const i = notionOrder.indexOf(key);
    return i === -1 ? Number.MAX_SAFE_INTEGER : i;
  };
  const position = new Map((seriesIds || []).map((id, i) => [id, i]));
  const lastServed = (g) => Math.max(-1, ...g.all.map((c) => position.get(c.id) ?? -1));
  const byBalance = ([ka, a], [kb, b]) =>
    servedIn(a) - servedIn(b) || lastServed(a) - lastServed(b) || rank(ka) - rank(kb);
  if (seriesIds) {
    // Série adaptative (file transmise par exercice.js) : chaque notion encore
    // jamais servie d'abord (couverture de toutes les notions), puis
    // répartition proportionnelle au besoin (voir notionWeight). Égalité :
    // départage historique ci-dessus.
    const share = new Map(
      available.map(([key, g]) => {
        const state = notionMastery(history, g.chapter, g.notion, { relations });
        const levels = g.all.map((c) => c.difficulty);
        return [key, notionWeight(state, levels) / (servedIn(g) + 1)];
      }),
    );
    // Premier passage dans l'ordre habituel (ordre de sélection conservé) ;
    // la part de chaque notion ne départage que les notions déjà servies.
    const unservedFirst = ([, a], [, b]) => (servedIn(a) === 0 ? 0 : 1) - (servedIn(b) === 0 ? 0 : 1);
    const byShare = (x, y) => {
      if (servedIn(x[1]) === 0 && servedIn(y[1]) === 0) return 0;
      const d = share.get(y[0]) - share.get(x[0]);
      return Math.abs(d) > 1e-9 ? d : 0;
    };
    available.sort((x, y) => unservedFirst(x, y) || byShare(x, y) || byBalance(x, y));
    // Pas de répétition immédiate d'une notion (hors bloc de calibration, géré
    // plus bas) sauf si sa part dépasse nettement celle de la suivante.
    const lastId = seriesIds[seriesIds.length - 1];
    if (available.length > 1 && available[0][1].all.some((c) => c.id === lastId)) {
      const [first, second] = available;
      if (servedIn(second[1]) === 0 || share.get(first[0]) < REPEAT_MARGIN * share.get(second[0])) {
        available[0] = second;
        available[1] = first;
      }
    }
  } else {
    available.sort(byBalance);
  }
  // Notion nouvelle : sa 2e question suit immédiatement la 1re (A, A, B, B…),
  // puis la répartition ci-dessus reprend. La difficulté reste choisie plus bas,
  // par le moteur, sur l'état mis à jour après la 1re réponse.
  const group = calibrationBlockGroup(groups, history, seriesIds, remaining) || available[0][1];

  const target = targetValue(notionMastery(history, group.chapter, group.notion, { relations }));
  const seen = new Set(history.map((h) => h.id));
  const cost = (c) =>
    (c.difficulty == null ? 0 : Math.abs(c.difficulty - target)) + (seen.has(c.id) ? REPEAT_PENALTY : 0);
  const best = Math.min(...group.fresh.map(cost));
  let pool = group.fresh.filter((c) => cost(c) - best < 1e-9);
  // Égalité de coût (au-dessus et au-dessous) : la difficulté la plus basse.
  const lowest = Math.min(...pool.map((c) => c.difficulty ?? 0));
  pool = pool.filter((c) => (c.difficulty ?? 0) === lowest);
  return pool[Math.floor(rng() * pool.length)];
}

/** Notions déjà travaillées dans la classe active, de la plus fragile à la
 * plus solide (taux de réussite croissant, puis la moins récemment
 * travaillée). Renvoie [{key, chapter, notion, rate, count}]. */
export function workedNotionsByWeakness(history) {
  const byKey = new Map();
  for (const h of history) {
    if (!h.chapter || !h.notion) continue;
    const key = notionKey(h.chapter, h.notion);
    const s = byKey.get(key) || { key, chapter: h.chapter, notion: h.notion, correct: 0, count: 0, last: 0 };
    s.count += 1;
    if (h.correct) s.correct += 1;
    s.last = Math.max(s.last, h.ts || 0);
    byKey.set(key, s);
  }
  return [...byKey.values()]
    .map((s) => ({ ...s, rate: s.correct / s.count }))
    .sort((a, b) => a.rate - b.rate || a.last - b.last);
}
