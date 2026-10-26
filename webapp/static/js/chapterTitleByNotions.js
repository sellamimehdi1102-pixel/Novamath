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
  "Signe du trinôme et inéquations du second degré": "Polynômes du second degré",
  "Second degré : modéliser et optimiser": "Polynômes du second degré",
  "Approximation affine et dérivabilité": "Dérivation : nombre dérivé et fonction dérivée",
  "Fonctions paires et impaires": "Variations et extremums des fonctions",
  "Inégalités et position relative de courbes": "Variations et extremums des fonctions",
  "Étude d'une fonction et méthode de Newton": "Variations et extremums des fonctions",
  "Croissance et décroissance exponentielles": "Fonction exponentielle",
  "Angles associés et lecture du cercle": "Trigonométrie",
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
  "Formule d'Al-Kashi et calculs dans le triangle": "Produit scalaire",
  "Projeté orthogonal d'un point sur une droite": "Géométrie repérée",
  "Configurations dans un repère": "Géométrie repérée",
  "Épreuves indépendantes et épreuves de Bernoulli": "Probabilités conditionnelles",
  "Simulation et échantillonnage": "Variables aléatoires",
  "Ensembles et notations": "Vocabulaire ensembliste et logique",
  "Propositions, connecteurs et quantificateurs": "Vocabulaire ensembliste et logique",
  "Implication, réciproque et contraposée": "Vocabulaire ensembliste et logique",
  "Types de raisonnement": "Vocabulaire ensembliste et logique",
  "Variables, instructions conditionnelles et boucles": "Algorithmique et programmation : listes",
  "Fonctions et programmation modulaire": "Algorithmique et programmation : listes",
  "Générer une liste": "Algorithmique et programmation : listes",
  "Manipuler et parcourir une liste": "Algorithmique et programmation : listes",
  "Évolutions et taux": "Automatismes",
  "Calcul numérique et algébrique": "Automatismes",
  "Fonctions et représentations": "Automatismes",
  "Statistiques et probabilités": "Automatismes",
  // Première spécifique adaptée au manuel « Première ES/L » (2026-10-26).
  "Proportions et pourcentages": "Pourcentages",
  "Indices base 100": "Pourcentages",
  "Rappels sur les fonctions": "Fonctions numériques",
  "Fonction racine carrée": "Fonctions numériques",
  "Fonction cube": "Fonctions numériques",
  "Racines et factorisation d'un trinôme": "Polynômes du second degré",
  "Notation Σ et indicateurs de tendance centrale": "Statistiques",
  "Quartiles et diagramme en boîte": "Statistiques",
  "Variance, écart-type et dispersion": "Statistiques",
  "Rappels de probabilités : événements": "Variables aléatoires",
  "Loi des grands nombres et simulation": "Variables aléatoires",
  "Expériences indépendantes et loi de Bernoulli": "Loi de Bernoulli et loi binomiale",
  "Schéma de Bernoulli et loi binomiale": "Loi de Bernoulli et loi binomiale",
  "Échantillonnage et règle de décision": "Loi de Bernoulli et loi binomiale",
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
  let best = null,
    bestCount = 0;
  for (const theme in counts) {
    if (counts[theme] > bestCount) {
      best = theme;
      bestCount = counts[theme];
    }
  }
  return best || rawTitle;
}
