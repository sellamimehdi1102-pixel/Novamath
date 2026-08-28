// Charte unique de difficulté (1-5), partagée entre exercice.js et
// chapitres.js — même échelle et mêmes libellés que
// webapp/exercise_generator/derivatives.py::LEVEL_META côté serveur, pour
// que l'élève voie le même niveau désigné de la même façon partout
// (Phase 1 du chantier pédagogique : "l'élève doit comprendre immédiatement
// le niveau de l'exercice").
export const DIFF_EMOJI = { 1: "🟢", 2: "🟡", 3: "🟠", 4: "🔴", 5: "🟣" };
export const DIFF_LABEL = {
  1: "Niveau 1 — Fondamental",
  2: "Niveau 2 — Intermédiaire",
  3: "Niveau 3 — Avancé",
  4: "Niveau 4 — Difficile",
  5: "Niveau 5 — Défi",
};
export const DIFF_LABEL_SHORT = { 1: "Fondamental", 2: "Intermédiaire", 3: "Avancé", 4: "Difficile", 5: "Défi" };
export const DIFF_BADGE = {
  1: "badge--success", 2: "badge--success", 3: "badge--warning", 4: "badge--danger", 5: "badge--danger",
};
