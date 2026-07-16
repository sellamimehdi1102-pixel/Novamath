# Changelog — Lumis V2

**Date** : 2026-07-10

## Contexte
Première itération de correction après usage réel de Lumis V1. Introduction de la notion de "série"
(regroupement de questions), refonte des statistiques (temps réel, accuracy/20, graphique dynamique),
correction du bug de progression des chapitres, simplification de la page Entraînement, et mise en place du
système de versionnement (`create_version_snapshot.py`).

## Fonctionnalités ajoutées
- **Séries de 10 questions** pour tous les modes d'entraînement (Révisions, Objectif du jour, Examen blanc,
  Défi chronométré, Erreurs précédentes), avec écran de récapitulatif (score, accuracy, temps, notions
  travaillées) et boutons Recommencer / Retour aux chapitres / Voir le dashboard.
  L'évaluation initiale IA reste à 7 questions (contrainte du modèle `models/level_predictor.pkl`, non
  modifiable sans le ré-entraîner — hors périmètre de cette itération).
- **Lancement ciblé par notion** : chaque notion de `chapitres.html` est cliquable et démarre directement
  une série de 10 questions restreinte à cette notion (avec répétition si la notion contient moins de
  10 exercices).
- **Suivi du temps réel** (`webapp/static/js/timetrack.js`) : chronomètre d'activité qui exclut l'onglet
  masqué et l'inactivité prolongée (>60s sans interaction). Chaque réponse enregistre un `duration_s` réel.
- **Carte "Accuracy /20"** sur le dashboard : `(bonnes réponses / total) × 20`, recalculée à chaque rendu,
  avec badge coloré (vert ≥16, orange 10-15,9, rouge <10).
- **Graphique de progression par série** (au lieu d'un point par jour) : ligne reliant les séries, info-bulle
  au survol (date, chapitre/notion, valeur exacte), contrôle de zoom 20/50/Tout.
- **Historique par série** (`profil.js`) : date, heure, chapitre, notion, score, accuracy, temps, bonnes/
  mauvaises réponses, niveau IA, boutons Revoir (détail question par question) et Recommencer.
- Backend additif (`webapp/server.py`) : `exercise_ids` par notion dans `/api/chapters`, champ `series` dans
  `/api/stats` — aucune route existante modifiée dans son comportement.
- Système de versionnement : `create_version_snapshot.py`, dossiers `versions/Lumis_V1/` et
  `versions/Lumis_V2/`, chacun avec son propre `CHANGELOG.md`.

## Fonctionnalités supprimées
- Mode **Libre** (page Entraînement) : remplacé par le lancement ciblé par notion, plus précis.
- Mode **Notions faibles** : superflu maintenant que chaque notion faible peut être directement sélectionnée
  depuis Chapitres.
- Mode **Favoris** (et les fonctions `getFavorites`/`toggleFavorite` associées dans `store.js`) : retiré à la
  demande, code mort supprimé.

## Corrections de bugs
- **Temps du dashboard totalement faux** (affichait ~3h après 5 min d'usage) : il s'agissait d'une estimation
  fixe (`nb d'exercices × 3 min`), sans lien avec le temps réel. Remplacé par un suivi d'activité réel.
- **Chapitre affiché à 100% alors que jamais travaillé** : deux causes cumulées — (1) une entrée de test
  laissée par erreur dans `data/stats_store.json` pendant le développement (retirée) ; (2) un bug de
  conception plus profond : la "Progression" était calculée comme un taux de réussite (`rate`), donc un seul
  exercice réussi suffisait à afficher 100%. Corrigé : la Progression est désormais une **couverture**
  (exercices distincts tentés / total du chapitre), l'accuracy étant affichée séparément.
- **Graphique cassé** (un seul point visible) : agrégation par jour trop grossière avec peu de données.
  Remplacé par un point par série, avec ligne, tooltip et zoom.

## Améliorations UI
- Nouvelle carte Accuracy avec badge coloré selon le niveau.
- Lignes de notion cliquables avec surbrillance au survol et indication visuelle "Cliquer pour lancer une
  série ciblée".
- Écran de récapitulatif de série avec confettis si accuracy ≥ 70%.

## Améliorations UX
- Page Entraînement simplifiée (5 modes au lieu de 8), plus lisible.
- Statistiques de notion enrichies : progression (couverture), nb d'exercices réalisés, accuracy, dernière
  tentative, temps moyen, difficulté dominante, badge de maîtrise (À renforcer / En progrès / Maîtrisé).
- Historique de profil actionnable : Revoir le détail d'une série, la Recommencer à l'identique, ou retourner
  directement aux chapitres.

## Optimisations
- Aucune dépendance supplémentaire ; toute la logique de séries/temps reste en JS vanilla (pas de librairie
  de graphiques).

## Bugs connus
- Le "temps moyen" par notion (page Chapitres) ne dispose de données réelles que pour les réponses
  enregistrées après cette version (les entrées d'historique antérieures n'ont pas de `duration_s`).
- Pas de navigateur headless disponible dans l'environnement de développement : la vérification visuelle
  (dark/light, responsive, animations) reste à confirmer manuellement par l'utilisateur.
