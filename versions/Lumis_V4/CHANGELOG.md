# Changelog — Lumis V4

**Date** : 2026-07-10

## Contexte
Complète la gestion des séries en cours introduite en V3 : celle-ci manquait la confirmation avant de
quitter, un intitulé de bouton conforme au design demandé, et un moyen de reprendre une série directement
depuis la page Chapitres (pas seulement depuis le Dashboard).

## Fonctionnalités ajoutées
- **Fenêtre de confirmation "Quitter la série ?"** (`exercice.html`, `js/exercice.js`) : cliquer sur
  "Quitter la série" n'interrompt plus directement l'entraînement — une modale (nouveau style `.modal-overlay`
  / `.modal-card` dans `base.css`, réutilisable ailleurs) demande confirmation avec deux actions :
  "Continuer la série" (ferme la modale, rien ne change) et "Quitter et sauvegarder" (sauvegarde explicite
  de la série en cours puis retour au dashboard).
- **Bouton Commencer / Reprendre par notion** (`chapitres.js`) : chaque ligne de notion affiche désormais un
  bouton explicite — "Commencer" normalement, ou "▶ Reprendre" (avec surbrillance de la ligne) si une série
  est déjà en cours sur cette notion précise. Cliquer sur "Reprendre" renvoie directement à `exercice.html`,
  qui détecte la série en cours et restaure exactement la question, les réponses et le temps déjà enregistrés
  — sans jamais relancer une nouvelle série par erreur.
- Carte "Série en cours" du dashboard/chapitres alignée sur le format demandé : titre "📖 Série en cours",
  puis Chapitre / Notion / Question X sur 10 / Temps écoulé affichés comme champs distincts (au lieu d'un
  résumé combiné), bouton "▶ Reprendre la série".

## Fonctionnalités supprimées
- Aucune.

## Corrections de bugs
- Le bouton "Quitter" précédent (V3) quittait immédiatement sans confirmation — corrigé avec la modale.
- Cliquer sur une notion pour laquelle une série était déjà en cours relançait par erreur une série neuve
  (et effaçait la série en pause) au lieu de la reprendre — corrigé : le clic détecte maintenant la
  correspondance exacte chapitre+notion avec la série en cours et navigue simplement vers `exercice.html`
  pour la reprise automatique, sans écraser la sauvegarde.

## Améliorations UI
- Icône ArrowLeft (au lieu d'une croix) pour "Quitter la série", plus cohérente avec l'action "retour".
- Modale avec fond flouté, animation d'apparition douce (200-220ms), cohérente avec le reste du design
  (cartes, ombres, coins arrondis).

## Améliorations UX
- Impossible de quitter une série par erreur (clic accidentel) sans confirmation explicite.
- Reprise d'une série directement depuis l'endroit où elle a été commencée (page Chapitres), en plus du
  Dashboard.

## Optimisations
- Aucune.

## Bugs connus
- Toujours pas de navigateur headless disponible pour vérifier visuellement l'animation de la modale et la
  surbrillance de la ligne de notion "Reprendre" — vérification manuelle recommandée.
