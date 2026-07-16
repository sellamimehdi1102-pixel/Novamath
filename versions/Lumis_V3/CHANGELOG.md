# Changelog — Lumis V3

**Date** : 2026-07-10

## Contexte
Deuxième itération de correction/enrichissement après usage réel de Lumis V2. Corrige le bug d'accordéon
des chapitres, ajoute la possibilité de mettre en pause et reprendre une série d'exercices, enrichit
l'historique et les bulles de progression du dashboard, et uniformise tous les boutons du site avec des
icônes SVG (style Lucide) à la place des emojis.

## Fonctionnalités ajoutées
- **Quitter / Reprendre une série** (`webapp/static/js/store.js`, `js/exercice.js`) : bouton "Quitter" pendant
  une série, qui renvoie au dashboard sans rien supprimer. La progression (question actuelle, réponses
  données, temps) est sauvegardée automatiquement après chaque réponse (`saveInProgressSeries`). Une carte
  "Série en cours" apparaît désormais sur `dashboard.html` et `chapitres.html` (nouveau module
  `js/resume.js`, partagé entre les deux pages) avec un bouton "Reprendre la série" qui restaure exactement
  la question, les réponses et le temps déjà enregistrés.
- **Bulles "Chapitres maîtrisés / à revoir" enrichies** (`dashboard.js`) : affichent désormais le numéro et
  le nom complet du chapitre, la progression (couverture), l'accuracy, et un bouton "Aller au chapitre" qui
  ouvre directement l'accordéon du bon chapitre sur `chapitres.html` (et, pour les chapitres à revoir,
  pré-sélectionne la notion la plus faible).
- **Historique enrichi et unifié** (nouveau module `js/seriesview.js`, partagé entre `dashboard.js` et
  `profil.js`) : date au format JJ/MM/AAAA, heure, chapitre complet ("Chapitre 3 · Calcul littéral"), notion,
  score, accuracy, temps, bonnes/mauvaises réponses, niveau IA, et bouton "Revoir" (détail question par
  question) désormais disponible aussi sur le dashboard, pas seulement sur le profil.
- **Icônes SVG uniformisées** (nouveau module `js/icons.js`) : tous les boutons du site (Réussi/Échoué,
  Indice/Méthode/Solution, Démarrer/Recommencer/Quitter, Revoir, navigation profil, CTA d'accueil...)
  utilisent désormais des icônes vectorielles au trait (style Lucide), cohérentes avec la sidebar et le
  bouton de thème déjà existants — remplace les emojis (🚀📚🎯🏆✅❌💡🧭👁🔄← →) précédemment utilisés.

## Fonctionnalités supprimées
- Aucune fonctionnalité supprimée dans cette version.

## Corrections de bugs
- **Accordéon des chapitres cassé** : cliquer sur "Voir les notions" faisait visuellement se déplier toute la
  ligne de cartes (CSS Grid étirait les cartes voisines à la hauteur de la carte ouverte). Corrigé avec
  `align-items: start` sur `.chapters-grid`. Le comportement est aussi devenu un vrai accordéon : ouvrir un
  chapitre referme automatiquement les autres (un seul ouvert à la fois), avec chevron animé et transition de
  350ms (au lieu de 450ms).

## Améliorations UI
- Transition d'ouverture/fermeture des notions plus fluide (max-height + opacity, 300-350ms).
- Boutons visuellement homogènes (taille, coins arrondis, ombre, animation au survol) grâce aux icônes SVG
  partagées.

## Améliorations UX
- Reprise de série fiable même après fermeture du navigateur (persistée en localStorage, restaurée à l'octet
  près : question, réponses, temps).
- Accès direct à un chapitre/notion depuis le dashboard, sans avoir à le rechercher dans la liste.
- Historique du dashboard aussi actionnable (Revoir) que celui du profil, réduisant les allers-retours entre
  pages.

## Optimisations
- Mutualisation du rendu de l'historique des séries (`seriesview.js`) et de la couverture par chapitre
  (`coverageByChapter`/`coverageByNotion` déplacées dans `store.js`) : élimine la duplication de code entre
  `dashboard.js`, `chapitres.js` et `profil.js`.

## Bugs connus
- Le format de date JJ/MM/AAAA est local à `seriesview.js` ; toute nouvelle page affichant des dates de série
  doit réutiliser `formatDateFR` plutôt que d'implémenter son propre format.
- Toujours pas de navigateur headless disponible dans l'environnement de développement : la vérification
  visuelle (animations de l'accordéon, responsive des nouvelles cartes) reste à confirmer manuellement.
