# NovaMath v1.83

**Date** : 2026-07-25

**Nom de la mise à jour** : Fiche pédagogique riche pour les graphiques : la colonne d'explication devient une suite de cartes typées (comprendre, lire le graphique, observations, calcul étape par étape, astuce, pièges, à retenir)

## Nouveautés
- Nouveau schéma `figure.explication` (optionnel) : `resume`, `comprendre`, `lecture[]`, `observations[]`, `etapes[{titre,texte}]`, `astuce`, `pieges[]`, `aRetenir[]` — remplace l'ancien champ `figure.details` (jamais utilisé en contenu réel) par une structure permettant de rendre la colonne du bloc figure comme une vraie fiche pédagogique multi-cartes plutôt qu'une légende d'une phrase.
- `cours.js::buildFigureExplicationHtml` : génère une carte typée par section présente (icône + titre coloré, cohérent avec la palette `.cours-box--*` déjà utilisée ailleurs dans le cours), avec repli sur `figure.alt` si `explication` est absent.
- Nouvelles variantes de carte `.cours-box--lecture` (bleu info), `.cours-box--observations` (vert succès), `.cours-box--etapes` (indigo, liste numérotée dédiée `.cours-figure-etapes`), `.cours-box--aretenir` (or).
- Contenu pilote : 4 figures enrichies avec `explication` complète pour valider visuellement le rendu — `racine-carree` (Chapitre_1), `courbe-representative-dune-fonction` (Chapitre_7), `somme-et-difference-de-deux-vecteurs` (Chapitre_4), `loi-de-probabilite` (Chapitre_12).

## Corrections
- (aucune)

## Optimisations
- (à compléter)

## Fichiers modifiés
- `webapp/static/js/cours.js`
- `webapp/static/css/cours.css`
- `webapp/static/data/cours/chapitre_1.json`, `chapitre_4.json`, `chapitre_7.json`, `chapitre_12.json`

## Bugs connus
- Seules 4 figures sur l'ensemble des chapitres ont le nouveau champ `explication` ; les autres retombent sur `figure.alt` (légende courte) en attendant l'enrichissement complet du contenu (volet B).

## Temps estimé de développement
- (à compléter)
