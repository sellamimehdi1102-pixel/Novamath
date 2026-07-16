# Changelog — Lumis V5

**Date** : 2026-07-10

## Contexte
Correction d'un bug signalé après usage réel de V4 : le bouton "Quitter la série" semblait n'apparaître
qu'à la fin de la série au lieu d'être visible en permanence pendant les 10 questions. La cause n'était pas
un problème de placement (le bouton était bien dans le bon composant depuis V4) mais un bug CSS transverse
qui rendait l'attribut `hidden` inopérant sur plusieurs éléments du site.

## Fonctionnalités ajoutées
- Aucune (correction de bug pure, aucune logique métier ni fonctionnalité modifiée).

## Fonctionnalités supprimées
- Aucune.

## Corrections de bugs
- **Bug CSS racine : `[hidden]` ignoré** (`css/base.css`) — plusieurs composants (`.eval-topbar`,
  `.badge`, `.modal-overlay`) fixaient `display` sans exception pour l'état masqué. Or une règle d'auteur
  qui fixe `display` l'emporte toujours sur le `[hidden] { display:none }` du navigateur, même à
  spécificité égale (l'origine de la règle prime sur la spécificité). Conséquence concrète : le JS
  togglait correctement `element.hidden = true/false` (logique déjà correcte depuis V3/V4), mais la barre
  contenant le bouton "Quitter la série" restait affichée en permanence au lieu de suivre l'état réel de la
  série — d'où l'impression que le bouton "n'apparaissait qu'à la fin".
  Corrigé avec une règle globale `[hidden] { display: none !important; }` dans `css/base.css`, garantissant
  que l'attribut `hidden` masque toujours l'élément quel que soit le composant, sur toutes les pages du site
  (corrige aussi, par la même occasion, le même défaut latent sur `.badge` et `.modal-overlay`).
- Aucune logique JS n'a été modifiée : `js/exercice.js` togglait déjà correctement le bouton au bon moment
  (visible dès la question 1/10, masqué uniquement à l'écran de récapitulatif) — seul le rendu visuel était
  en cause.

## Améliorations UI
- Aucune (hors correction de bug).

## Améliorations UX
- Le bouton "Quitter la série" est désormais fiablement visible sur les 10 questions, sans jamais disparaître
  pendant la série, conformément à la demande.

## Optimisations
- Aucune.

## Bugs connus
- Toujours pas de navigateur headless disponible pour confirmer visuellement le correctif — vérification
  manuelle recommandée (recharger `exercice.html`, démarrer une série, confirmer que le bouton reste visible
  de la question 1/10 à 10/10 puis disparaît à l'écran de récapitulatif).
