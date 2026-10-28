// ── Difficulté adaptative par notion ────────────────────────────────────────
// Fonctions pures (aucun accès au DOM, au stockage ni au réseau), utilisées par
// exercice.js pour choisir l'exercice SUIVANT d'une série pendant qu'elle se
// déroule, au lieu de tirer toute la série au hasard au départ.
//
// Règle (validée produit) : chaque notion a son propre niveau, recalculé à
// partir de l'historique de l'élève dans la classe active.
//   - Notion jamais travaillée : niveau le plus bas disponible pour elle.
//   - Le niveau n'est réévalué qu'à chaque BLOC COMPLET de 5 réponses sur la
//     notion (paliers, pas une fenêtre glissante) :
//       4 ou 5 réussies → niveau supérieur ;
//       3 réussies      → même niveau ;
//       0 à 2 réussies  → niveau inférieur.
//   - Les niveaux sont ceux réellement disponibles pour la notion (ex. 1, 2, 4
//     si la banque n'a pas d'exercice de difficulté 3 pour elle).
//   - Si aucun exercice inédit (dans la série) n'existe au niveau visé, on
//     prend la difficulté disponible la plus proche (la plus basse en cas
//     d'égalité).

export const BLOCK_SIZE = 5;
export const PROMOTE_AT = 4;
export const DEMOTE_AT = 2;

export function notionKey(chapter, notion) {
  return `${chapter}|${notion}`;
}

/** Index de niveau (0 = plus bas) après rejeu de `answers` (booléens dans
 * l'ordre chronologique) sur `nLevels` niveaux disponibles. */
export function levelIndexFromAnswers(answers, nLevels) {
  if (nLevels <= 1) return 0;
  let idx = 0;
  const completeBlocks = Math.floor(answers.length / BLOCK_SIZE);
  for (let b = 0; b < completeBlocks; b++) {
    const block = answers.slice(b * BLOCK_SIZE, (b + 1) * BLOCK_SIZE);
    const correct = block.filter(Boolean).length;
    if (correct >= PROMOTE_AT) idx = Math.min(idx + 1, nLevels - 1);
    else if (correct <= DEMOTE_AT) idx = Math.max(idx - 1, 0);
  }
  return idx;
}

/** Difficulté visée pour une notion : `history` = historique de la classe
 * active (entrées {chapter, notion, correct, ts}), `levels` = difficultés
 * disponibles pour la notion. */
export function targetDifficulty(history, chapter, notion, levels) {
  const sorted = [...new Set(levels)].filter((d) => d != null).sort((a, b) => a - b);
  if (!sorted.length) return null;
  const answers = history
    .filter((h) => h.chapter === chapter && h.notion === notion)
    .sort((a, b) => (a.ts || 0) - (b.ts || 0))
    .map((h) => Boolean(h.correct));
  return sorted[levelIndexFromAnswers(answers, sorted.length)];
}

/** Choisit le prochain exercice d'une série adaptative, ou `null` s'il n'en
 * reste aucun d'inédit.
 *   candidates  : [{id, chapter, notion, difficulty}]
 *   history     : historique de la classe active
 *   usedIds     : ids déjà servis (ou écartés) dans CETTE série
 *   notionOrder : clés notionKey par priorité (départage à égalité)
 *   rng         : générateur [0, 1) (injectable pour les tests) */
export function pickNextExercise({ candidates, history, usedIds, notionOrder = [], rng = Math.random }) {
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

  // Notion la moins servie dans la série (répartition équilibrée), puis
  // l'ordre de priorité fourni.
  const servedIn = (g) => g.all.length - g.fresh.length;
  const rank = (key) => {
    const i = notionOrder.indexOf(key);
    return i === -1 ? Number.MAX_SAFE_INTEGER : i;
  };
  available.sort(([ka, a], [kb, b]) => servedIn(a) - servedIn(b) || rank(ka) - rank(kb));
  const [, group] = available[0];

  const target = targetDifficulty(
    history,
    group.chapter,
    group.notion,
    group.all.map((c) => c.difficulty),
  );
  const distance = (c) => (target == null || c.difficulty == null ? 0 : Math.abs(c.difficulty - target));
  const best = Math.min(...group.fresh.map(distance));
  let pool = group.fresh.filter((c) => distance(c) === best);
  // Égalité de distance (au-dessus et au-dessous) : la difficulté la plus basse.
  const lowest = Math.min(...pool.map((c) => c.difficulty ?? 0));
  pool = pool.filter((c) => (c.difficulty ?? 0) === lowest);
  // Préférence pour un exercice jamais fait, sinon un déjà rencontré.
  const seen = new Set(history.map((h) => h.id));
  const neverDone = pool.filter((c) => !seen.has(c.id));
  if (neverDone.length) pool = neverDone;
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
