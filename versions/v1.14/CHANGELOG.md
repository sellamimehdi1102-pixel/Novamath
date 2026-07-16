# NovaMath v1.14

**Date** : 2026-07-13

**Nom de la mise à jour** : Ajout du module Cours

## Nouveautés
- Nouvel onglet **Cours** dans la sidebar (icône livre), premier onglet menant à un véritable espace d'apprentissage : 12 chapitres, 52 notions, ~200 sections de cours rédigées (définitions, propriétés, méthodes, exemples résolus étape par étape, erreurs fréquentes, astuces, résumé, fiche mémo).
- Contenu pédagogique entièrement réécrit (jamais un simple affichage de PDF) à partir des PDF officiels du programme déjà présents dans le dépôt (`Chapitres/*.pdf`, texte pré-extrait dans `texts/*.txt`), stocké en JSON structuré (`webapp/static/data/cours/chapitre_1..12.json`), chargé à la demande (un seul chapitre à la fois, jamais les 12 d'un coup).
- Lecteur de notion avec navigation section par section, rendu mathématique KaTeX réel (aucun texte brut de type `sqrt(x)`), boîtes visuelles typées par nature (définition, propriété, méthode, exemple, attention, astuce, tableau), cohérentes avec le thème/accent/transparence/animations choisis dans Paramètres.
- Mini-quiz de fin de notion réutilisant la banque d'exercices existante (auto-évaluation « J'ai réussi / À revoir », comme le reste du site), score enregistré.
- Progression de lecture sauvegardée et reprise exacte (section courante, statut par notion, score de quiz) via un nouvel espace de stockage par utilisateur (`data/user_course_progress/`) et deux nouveaux endpoints `GET/POST /api/course-progress`.
- Carte "Reprendre mon cours" sur le Dashboard, pointant directement vers la dernière notion en cours de lecture.
- Respect intégral des règles déjà en vigueur : mode invité limité à 2 chapitres (même modale d'incitation que Chapitres), progression non conservée pour les invités (purgée avec le reste du compte), structure d'interface traduite FR/EN (le contenu pédagogique reste en français dans les deux langues, comme les exercices).
- Script d'aide `tools/regenerate_course_content.py` pour réextraire le texte d'un PDF de programme remplacé, en vue d'une mise à jour manuelle du contenu JSON correspondant.

## Corrections
- Aucune (mise à jour additive, aucune fonctionnalité existante modifiée).

## Optimisations
- Chargement paresseux du contenu de cours (un fichier JSON par chapitre, jamais les 12 ensemble) pour un temps de chargement de page inchangé.
- Réutilisation intégrale de l'architecture et des styles de l'onglet Chapitres (grille de cartes, accordéon de notions, tokens CSS) plutôt qu'un système parallèle : aucun composant ne semble ajouté après coup.

## Fichiers modifiés
Nouveaux : `webapp/static/cours.html`, `webapp/static/js/{cours,courseResume}.js`, `webapp/static/css/cours.css`, `webapp/static/data/cours/chapitre_1..12.json` (12 fichiers), `tools/regenerate_course_content.py`.
Modifiés : `webapp/server.py` (route `cours.html` protégée, endpoints `/api/course-progress`), `webapp/auth.py` (stockage progression cours + purge invité), `webapp/static/js/{api,i18n,dashboard}.js`, `webapp/static/dashboard.html` (carte de reprise), sidebar de `dashboard.html`/`chapitres.html`/`exercice.html`/`profil.html` (nouvel onglet Cours).

## Bugs connus
- Comme pour la v1.13 : validation effectuée via tests serveur/API réels (curl, sessions invité réelles, vérification de la purge de progression), pas de test interactif dans un navigateur réel — à confirmer visuellement.
- Les éléments visuels (tableaux, encadrés) sont rendus en HTML/CSS ; les schémas géométriques (repères, vecteurs tracés) ne sont pas encore illustrés graphiquement, seulement décrits — amélioration possible pour une future version.
- Vidéos, synthèse vocale, flashcards et démonstrations animées (évolutions futures envisagées) ne sont pas implémentées dans cette version ; l'architecture en sections JSON typées est conçue pour les accueillir sans réécriture.

## Temps estimé de développement
- Session unique, longue durée, couvrant l'architecture complète du module (backend, frontend, lecteur, quiz, progression), la rédaction pédagogique des 12 chapitres/52 notions, et l'intégration au Dashboard/Paramètres/i18n existants.
