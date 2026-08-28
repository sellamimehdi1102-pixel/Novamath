# NovaMath v1.81

**Date** : 2026-07-24

**Nom de la mise à jour** : Refonte du moteur d'affichage des cours : graphiques SVG agrandis (axes fléchés, graduations, grille, points annotés) et disposition deux colonnes graphique/explications

## Nouveautés
- Nouveau moteur de figures SVG (`geomSvg.js`) : canevas dimensionné dynamiquement (fini le carré forcé), axes fléchés, graduations chiffrées sur x/y, repère de l'origine "O", grille légère activée par défaut dès qu'un repère est affiché, coordonnées optionnelles sous les points remarquables (`showCoords`).
- Toutes les figures non-"geom" (arbre de probabilités, Venn, ensembles emboîtés, droite graduée, bâtons, camembert, boîte à moustaches, solides) mises à l'échelle ×1.6 pour rester au même niveau visuel que les repères mathématiques.
- Lecteur de notion (`cours.js`/`cours.css`) : disposition en deux colonnes dès qu'une notion a une figure — graphique à gauche (~45%, collant au scroll), explications à droite (~55% : définition, méthode, exemples, erreurs fréquentes, astuces...). Empilement graphique puis texte en dessous de 900px.

## Corrections
- (aucune — chantier purement additif sur le moteur d'affichage)

## Optimisations
- (à compléter)

## Fichiers modifiés
- `webapp/static/js/geomSvg.js`
- `webapp/static/js/cours.js`
- `webapp/static/css/cours.css`

## Bugs connus
- (à compléter)

## Temps estimé de développement
- (à compléter)
