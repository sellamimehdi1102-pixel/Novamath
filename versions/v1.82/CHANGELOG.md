# NovaMath v1.82

**Date** : 2026-07-25

**Nom de la mise à jour** : Correction du moteur des cours : disposition deux colonnes réservée au seul bloc graphique, reste du cours en une colonne fluide

## Nouveautés
- `buildFigureBlockHtml` (cours.js) : nouveau composant de figure autonome, encapsulant le graphique et sa colonne d'explication dédiée (`figure.details[]` si présent, sinon `figure.alt` en repli).
- Schéma de figure étendu avec un champ optionnel `details` (liste de points qui font directement référence au graphique, ex. "Le point A est ici...") — support pour l'enrichissement de contenu à venir.

## Corrections
- Le lecteur de notion (v1.81) plaçait TOUT le corps du cours (définition, méthode, exemples, erreurs fréquentes...) en deux colonnes dès qu'une figure était présente, cassant la lecture verticale naturelle. Revert vers une seule colonne pour l'ensemble du cours ; seul le bloc contenant la figure (juste après la Définition) devient un mini-layout deux colonnes (graphique ~44% / explication ~56%).
- Suppression du `position: sticky` sur la colonne graphique (inutile hors du contexte pleine largeur, pouvait sembler incohérent si l'explication dépasse largement la hauteur du graphique).

## Optimisations
- Graphique legèrement agrandi (`max-width: 480px` contre 420px).

## Fichiers modifiés
- `webapp/static/js/cours.js`
- `webapp/static/css/cours.css`

## Bugs connus
- (à compléter)

## Temps estimé de développement
- (à compléter)
