# NovaMath v1.85

**Date** : 2026-07-25

**Nom de la mise à jour** : Repli automatique de la fiche graphique : colonne de droite reconstruite depuis le contenu réel de la notion (comprendre, observations, astuce, pièges) sur TOUTES les figures du site, plus seulement les 7 pilotes

## Nouveautés
- `cours.js::deriveFigureExplicationFromNotion` : quand une figure n'a pas de `figure.explication` rédigée à la main, la colonne de droite du bloc figure n'affiche plus une seule phrase (`figure.alt`) mais une fiche de plusieurs cartes reconstruite à partir du contenu déjà écrit pour la notion — `explicationSimple`/`intuition` (Ce qu'il faut comprendre), `figure.alt` (Ce que montre ce graphique), `astuce` (Astuce NovaMath), `erreursFrequentes` (À ne pas confondre). Comme ce contenu est présent sur la quasi-totalité des notions déjà en base, cette bascule s'applique immédiatement à TOUTES les figures du site, pas seulement aux 7 notions enrichies à la main en v1.83/v1.84.
- Pour éviter toute duplication visuelle, les sections "Pour bien comprendre", "Astuce NovaMath" et "Erreurs fréquentes" ne sont plus affichées une seconde fois en colonne unique quand leur contenu a été déplacé dans la fiche du graphique (nouveau flag `usesFallbackFigureCards`). La Méthode reste toujours affichée séparément, juste au-dessus des exemples qui s'y réfèrent.

## Corrections
- Colonne de droite du bloc figure quasi vide (une phrase) sur la quasi-totalité des notions du site — seules 7 notions avaient un contenu `figure.explication` rédigé à la main jusqu'ici.

## Optimisations
- (aucune)

## Fichiers modifiés
- `webapp/static/js/cours.js`

## Bugs connus
- Le repli automatique réutilise du texte déjà écrit pour la notion (pas de contenu inédit spécifique au graphique) ; le rendu reste donc moins riche que sur les 7 notions dotées d'une `figure.explication` rédigée à la main. L'enrichissement manuel du reste du contenu (au-delà de Chapitre_1) reste à faire.

## Temps estimé de développement
- (à compléter)
