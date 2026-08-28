// ── Titre de secours déterministe, dérivé des notions réellement présentes
// dans le chapitre (pas de l'ordre/l'id du chapitre) — utilisé uniquement
// quand aucun titre officiel n'est fourni par les données.
const NOTION_THEME = {
  "Calcul de sommes": "Suites numériques",
  "Généralités sur les suites": "Suites numériques",
  "Notion de limite d'une suite": "Suites numériques",
  "Sens de variation d'une suite": "Suites numériques",
  "Suite arithmétique": "Suites numériques",
  "Suite géométrique": "Suites numériques",
  "Fonction polynôme de degré 2": "Polynômes du second degré",
  "Propriétés d'un trinôme": "Polynômes du second degré",
  "Équations du second degré": "Polynômes du second degré",
  "Composition de fonctions et dérivation": "Dérivation : nombre dérivé et fonction dérivée",
  "Fonction dérivée": "Dérivation : nombre dérivé et fonction dérivée",
  "Nombre dérivé. Tangente": "Dérivation : nombre dérivé et fonction dérivée",
  "Opérations et dérivation": "Dérivation : nombre dérivé et fonction dérivée",
  "Nombre dérivé et extremums locaux": "Variations et extremums des fonctions",
  "Variations d'une fonction": "Variations et extremums des fonctions",
  "Courbe représentative": "Fonction exponentielle",
  "Fonction exponentielle": "Fonction exponentielle",
  "Lien avec les suites géométriques": "Fonction exponentielle",
  "Nouvelle notation et nombre e": "Fonction exponentielle",
  "Propriétés algébriques": "Fonction exponentielle",
  "Propriétés analytiques": "Fonction exponentielle",
  "Coordonnées d'un point du cercle trigonométrique": "Trigonométrie",
  "Fonctions cosinus et sinus": "Trigonométrie",
  "Repérage sur le cercle trigonométrique": "Trigonométrie",
  "Autres définitions et propriétés": "Produit scalaire",
  "Produit scalaire, colinéarité et orthogonalité de vecteurs": "Produit scalaire",
  "Étude d'un ensemble de points": "Produit scalaire",
  "Vecteur normal à une droite": "Géométrie repérée",
  "Équation d'un cercle": "Géométrie repérée",
  "Arbres pondérés": "Probabilités conditionnelles",
  "Notion d'indépendance": "Probabilités conditionnelles",
  "Probabilité conditionnelle": "Probabilités conditionnelles",
  "Espérance – Variance – Écart-type": "Variables aléatoires",
  "Variables aléatoires réelles": "Variables aléatoires",
};

const GENERIC_TITLE_RE = /^chapitre\s+\d+$/i;

/** Garde le titre officiel s'il existe déjà ; sinon déduit un titre stable à
 * partir du thème le plus fréquent parmi les notions du chapitre. */
export function resolveChapterTitle(rawTitle, notionLabels) {
  if (rawTitle && !GENERIC_TITLE_RE.test(rawTitle)) return rawTitle;
  const counts = {};
  for (const label of notionLabels || []) {
    const theme = NOTION_THEME[label];
    if (theme) counts[theme] = (counts[theme] || 0) + 1;
  }
  let best = null, bestCount = 0;
  for (const theme in counts) {
    if (counts[theme] > bestCount) { best = theme; bestCount = counts[theme]; }
  }
  return best || rawTitle;
}
