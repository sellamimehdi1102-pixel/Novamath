# Changelog — Lumis V1

**Date** : 2026-07-10

## Contexte
Première version de la plateforme **Lumis** (remplace l'ancien prototype "AdaptiveMath" à base de
Gradio/HTML minimal). Refonte complète du frontend en HTML/CSS/JS vanilla, en conservant intégralement la
logique métier existante (sélection d'exercices, prédiction de niveau par IA, banque d'exercices).

## Fonctionnalités ajoutées
- Landing page complète (hero, fonctionnement, fonctionnalités, avis, FAQ, footer).
- Page Chapitres : grille de 12 cartes avec accordéon des notions.
- Page Évaluation initiale (7 questions, pilotée par `models/level_predictor.pkl`).
- Page Entraînement avec 8 modes : Libre, Révisions, Objectif du jour, Examen blanc, Défi chronométré,
  Erreurs précédentes, Notions faibles, Favoris.
- Dashboard : XP, niveau, streak, temps passé (estimé), objectif hebdomadaire, graphique de progression,
  suggestions IA, badges, historique récent.
- Page Profil : avatar, radar de compétences, heatmap d'activité, historique paginé.
- Gamification : XP, niveaux, streak, badges, confettis.
- Dark mode par défaut, light mode via bascule persistée.
- Convertisseur déterministe `07_naturalize_exercises.py` : transforme les notations LaTeX/code
  (`\frac`, `\sqrt`, `*`, `^`...) en français rédigé naturellement, sans jamais modifier
  `exercises_bank.json` (fichier source, lecture seule) — produit `exercises_bank_natural.json`.
- Backend additif dans `webapp/server.py` : `/api/exercise/<id>`, `/api/stats` (persistance JSON locale),
  enrichissement de `/api/chapters` (titres, notions, métadonnées). Aucune route existante modifiée dans
  son comportement, aucune logique de sélection/prédiction touchée.

## Fonctionnalités supprimées
- Ancienne interface Gradio (`06_quiz_app.py`) : conservée telle quelle en référence, non branchée au nouveau
  frontend. Ancien frontend HTML minimal (`webapp/static/style.css` / `script.js`) : supprimé, remplacé
  intégralement.

## Corrections de bugs
- N/A (première version du nouveau frontend).

## Améliorations UI
- Design system complet (tokens.css) : palette indigo/violet, glassmorphism léger, coins arrondis,
  ombres douces, typographie Inter/Lexend.

## Améliorations UX
- Parcours guidé (landing → chapitres → évaluation → entraînement → dashboard/profil).
- Rendu mathématique naturel (plus de notation "code" visible pour l'élève).

## Optimisations
- Aucune dépendance JS lourde (KaTeX en CDN uniquement pour le rendu des formules restantes ; pas de
  framework).

## Bugs connus (identifiés après usage, corrigés en V2)
- Le temps affiché au dashboard est une estimation grossière (nb d'exercices × 3 min), pas un temps réel.
- La progression d'un chapitre est calculée comme un taux de réussite et non une couverture : un seul
  exercice réussi peut afficher 100% sur un chapitre jamais réellement travaillé.
- Le graphique de progression n'agrège qu'un point par jour (peu lisible avec peu de données).
- Aucune notion de "série" : pas de regroupement en session de 10 questions, pas de récapitulatif.
