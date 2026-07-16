# NovaMath v1.20

**Date** : 2026-07-13

**Nom de la mise à jour** : Refonte Exercices (ex-Chapitres) : filtres, favoris, multi-selection + Profil en lecture seule

## Nouveautés
- **Onglet "Chapitres" renommé en "Exercices"** partout sur le site (sidebar des 5 pages, titre d'onglet, `<h1>`, i18n FR/EN, textes d'aide, liens du footer landing, message de reprise de session) avec une nouvelle icône checklist (Lucide-style, cohérente avec le reste du système) distincte de l'icône "Cours".
- **Barre de filtres** sur la page Exercices : Tout / En cours / Maîtrisé / Non maîtrisé / Enregistrés, pastilles animées, réutilisant exactement la fonction `masteryLabel()` déjà utilisée pour les notions (aucune logique de maîtrise parallèle créée). "En cours" détecte automatiquement la série en pause ; chaque filtre affiche un message dédié quand il est vide (ex. « Aucune série en cours. »).
- **Favoris ("Enregistrés")** : étoile discrète sur chaque carte de chapitre, état persistant (nouveau champ `favorites` dans les préférences existantes, `/api/settings` — aucun nouveau point d'API), survit à la fermeture du navigateur, mise à jour immédiate de l'icône et du filtre "Enregistrés" au clic.
- **Multi-sélection des notions** : cliquer sur une notion ne démarre plus une série immédiatement — elle devient une case à cocher premium (style NovaMath). Un bouton "Commencer la série" apparaît sous la liste, désactivé tant qu'aucune notion n'est sélectionnée, puis lance une série couvrant l'union des exercices des notions choisies. Tous les paramètres d'entraînement existants (nombre d'exercices, chronomètre, niveau, mode naturel, ordre aléatoire) s'appliquent sans changement, via la même logique `exercice.js`/Paramètres → Entraînement. La reprise d'une série multi-notions déjà en cours reste détectée automatiquement (chaque notion concernée affiche "Reprendre").
- **Page Profil simplifiée** : devient une page de consultation pure (avatar, pseudo, niveau, progression, statistiques, badges, historique, calendrier d'activité). Toute modification (pseudo, avatar, informations personnelles) a été retirée — désormais centralisée exclusivement dans Paramètres → Compte, qui gérait déjà ces mêmes actions (suppression du doublon de fonctionnalité). "Se déconnecter" et "Supprimer mon compte" restent accessibles depuis le Profil.

## Corrections
- Aucune (fonctionnalités nouvelles/renommage, pas de bug préexistant corrigé).

## Optimisations
- Aucune régression de performance : filtres et favoris sont calculés/appliqués côté client sur des données déjà chargées (`api.chapters()`), sans appel réseau supplémentaire ; les favoris réutilisent le mécanisme de sauvegarde optimiste déjà en place dans `settingsManager.js`.

## Fichiers modifiés
- `webapp/static/js/chapitres.js` (réécrit : filtres, favoris, multi-sélection, bouton de démarrage)
- `webapp/static/css/chapitres.css` (barre de filtres, étoile favoris, checkboxes de notion)
- `webapp/static/js/icons.js` (icône `checklist`)
- `webapp/auth.py` (`favorites: []` dans `DEFAULT_SETTINGS`)
- `webapp/static/{dashboard,chapitres,cours,exercice,profil}.html` (icône + libellé "Exercices" dans la sidebar)
- `webapp/static/js/i18n.js` (clé `nav.exercices`)
- `webapp/static/{index.html,js/auth.js,js/settings.js,js/exercice.js,js/cours.js}` (textes utilisateur mentionnant l'onglet)
- `webapp/static/profil.html`, `webapp/static/js/profil.js` (suppression de toute UI de modification)

## Bugs connus
- Aucun identifié après tests (Playwright headless : filtres, favoris + persistance après rechargement, multi-sélection + démarrage de série, reprise de série multi-notions, Profil en lecture seule vérifié à la fois en mode invité et sur un compte réel, édition du pseudo toujours fonctionnelle depuis Paramètres, clair/sombre, sidebar réduite, mobile, 0 erreur JS fatale sur les 6 pages).

## Temps estimé de développement
- Session unique, longue durée : refonte de la page Exercices (filtres, favoris, multi-sélection), simplification du Profil, renommage complet de l'onglet, tests automatisés bout en bout.
