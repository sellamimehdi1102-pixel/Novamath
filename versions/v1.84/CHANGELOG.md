# NovaMath v1.84

**Date** : 2026-07-25

**Nom de la mise à jour** : Refonte du contenu pédagogique (Chapitre 1 pilote, mini-cours complets) et des cartes de notion (badges niveau/temps/exemples/graphiques, description, progression) ; correction du badge À lire sur une ligne

## Nouveautés
- Chapitre_1 (Nombres et calculs, Seconde) intégralement réécrit : les 4 notions (puissances, racine carrée, multiples/diviseurs/nombres premiers, ensembles de nombres) passent de textes d'une ou deux phrases à de vrais mini-cours — intro étoffée, nouveau champ `remarques[]`, méthode enrichie (étapes par niveau complétées), passage à 3-4 exemples par notion avec une explication rédigée spécifiquement pour chaque exemple (suppression du texte générique répété "Lisons d'abord attentivement l'énoncé..."), `erreursFrequentesDetail` entièrement rempli (pourquoi/comment détecter/comment éviter), astuce et résumé étoffés.
- Figure ajoutée pour "Les puissances" (diagramme en bâtons illustrant $2^1$ à $2^5$, absente jusqu'ici) et `figure.explication` complète ajoutée pour "Multiples, diviseurs, nombres premiers" et "Les ensembles de nombres" (déjà fait pour "La racine carrée" en v1.83) — les 4 notions du chapitre ont maintenant un graphique avec sa fiche pédagogique complète.
- Nouvelle section "Remarques" dans le lecteur de notion (`cours.js`, `.cours-box--remarque`), rendue quand `notion.remarques[]` est présent.
- Refonte des cartes de notion (grille de chapitre) : icône adaptée au sujet (heuristique par mots-clés), badge de niveau (Facile/Moyen/Difficile), temps de lecture estimé (comptage de mots réel, ≈180 mots/min), nombre d'exemples, nombre de graphiques, description (2 lignes, clamp CSS), barre de progression affichée uniquement si la notion est "en cours".
- En-tête "Astuce" renommé "Astuce NovaMath" ; "À retenir" renommé "Résumé — à retenir".

## Corrections
- Badge de statut ("À lire"/"En cours"/"Terminée") et badges en général : ajout de `white-space: nowrap` + `flex-shrink: 0` (`base.css` `.badge`) pour qu'ils ne se coupent plus jamais sur deux lignes, quelle que soit la largeur de la carte ou la longueur du titre voisin.

## Optimisations
- (aucune)

## Fichiers modifiés
- `webapp/static/js/cours.js`
- `webapp/static/css/cours.css`
- `webapp/static/css/base.css`
- `webapp/static/data/cours/chapitre_1.json`

## Bugs connus
- Seul Chapitre_1 (Seconde) a le contenu entièrement réécrit ; tous les autres chapitres/classes gardent l'ancien contenu (plus court) en attendant la suite du volet contenu.

## Temps estimé de développement
- (à compléter)
