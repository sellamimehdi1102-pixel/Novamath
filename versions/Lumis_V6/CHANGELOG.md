# Changelog — Lumis V6

**Date** : 2026-07-11

## Contexte
L'utilisateur a signalé que le comportement de gestion des séries en cours (demandé et censé être livré en
V4/V5) ne semblait toujours pas fonctionner. Après relecture exhaustive du code, toute la logique
(bouton visible pendant les 10 questions, confirmation, sauvegarde, carte de reprise, restauration exacte,
suppression en fin de série) était déjà correcte et présente depuis V4/V5. La cause la plus probable des
rapports répétés "ça ne marche toujours pas" : le serveur Flask ne renvoyait aucun en-tête anti-cache, donc
le navigateur pouvait continuer à servir une version mise en cache d'un ancien `exercice.js`/`base.css`
après chaque correction. Cette version corrige ce point structurel et aligne le texte du bouton/de la modale
sur le libellé exact demandé ("Retour au menu").

## Fonctionnalités ajoutées
- Sauvegarde de série en cours étendue (`js/exercice.js`, `persistProgress`) : ajout explicite de `score`
  (bonnes réponses), `wrong` (mauvaises réponses), `progressPct` et `startDate` dans l'objet persisté, en
  plus des champs déjà présents (mode, chapitre, notion, index de question, réponses détaillées, id et date
  de début de série) — couvre explicitement chaque champ demandé, même ceux déjà dérivables.

## Fonctionnalités supprimées
- Aucune.

## Corrections de bugs
- **Cache navigateur non maîtrisé** (`webapp/server.py`) : aucun en-tête de cache n'était envoyé par Flask,
  ce qui pouvait laisser un navigateur servir une version obsolète de `js/exercice.js` ou `css/base.css`
  après une correction déployée côté serveur — expliquant que des correctifs déjà livrés (V4, V5) semblaient
  "ne pas s'appliquer". Ajout d'un hook `after_request` qui force
  `Cache-Control: no-store, no-cache, must-revalidate` sur toutes les réponses (adapté à un projet en
  développement actif ; à retirer/ajuster avant une mise en production où le cache redevient souhaitable).
- Libellés alignés sur la demande exacte : bouton renommé "Quitter la série" → **"Retour au menu"**, bouton
  de confirmation "Quitter et sauvegarder" → **"Retour au menu et sauvegarder"**, texte de la modale
  précisé ("...exactement là où vous l'avez laissée").

## Améliorations UI
- Aucune (hors renommage de libellés).

## Améliorations UX
- Le bouton et la modale utilisent maintenant la terminologie "Retour au menu" demandée, cohérente avec le
  fait que la confirmation renvoie bien vers le Dashboard (le "menu" de l'application).

## Optimisations
- Aucune.

## Bugs connus
- Le `Cache-Control: no-store` global s'applique à toutes les routes, y compris l'API — acceptable en
  développement (aucune route n'a besoin d'être mise en cache ici) mais à revoir si des réponses API
  volumineuses doivent un jour être mises en cache côté client.
- Toujours pas de navigateur headless disponible pour confirmer visuellement — recommandé de forcer un
  rechargement complet (Ctrl+Maj+R / vider le cache) au moins une fois après cette mise à jour, le temps que
  le nouvel en-tête no-cache prenne effet pour les requêtes déjà en cache avant ce déploiement.
