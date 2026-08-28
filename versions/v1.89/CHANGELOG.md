# NovaMath v1.89

**Date** : 2026-07-25

**Nom de la mise à jour** : Moteur pédagogique v2.1 — interactions, questions éclair, exemples interactifs (notion pilote Pythagore)

## Nouveautés
Perfectionnement du moteur de cours v2 (introduit en v1.88), toujours entièrement rétrocompatible — chaque ajout est gardé par un champ optionnel absent partout ailleurs, donc sans aucun effet sur les autres notions tant qu'il n'est pas explicitement activé.

- **Le graphique raconte l'explication** :
  - `geomSvg.js` : infobulles natives au survol (`<title>`) sur les points, segments, polygones et arcs (`tooltip`, optionnel) — expliquent le rôle de chaque élément sans surcharger la figure.
  - Segments et arcs supportent désormais `variant`/`reveal`, comme les polygones (mise en évidence colorée d'un côté précis, ex. l'hypoténuse, et apparition progressive synchronisée aux étapes).
  - Nouveaux boutons **Précédent / Rejouer l'animation / Suivant** sous les pastilles d'étapes (`figure.steps`) — navigation explicite en plus du clic direct sur une pastille, avec désactivation automatique aux bornes (Précédent grisé à l'étape 1, Suivant grisé à la dernière étape).
  - Survol des points/segments/arcs avec léger agrandissement et halo (`cours-figure-wrap--xl .geom-point:hover`, etc.) — volontairement limité aux figures "mises en avant" (`figure.emphasis`), donc sans effet sur les figures existantes du reste du site.
- **Questions éclair** (`notion.questionsEclair`, nouveau champ) : très courtes questions de réflexion insérées entre les sections du cours (après "Pourquoi apprend-on cela ?", après la figure, après la méthode, après un exemple précis), avec un bouton "Voir une piste" pour révéler un indice au clic — sans jamais donner la réponse directement, pour faire réfléchir en continu plutôt que d'attendre le quiz final.
- **Exemples interactifs** (`exemple.interactif`, nouveau champ) : au lieu d'afficher tout le calcul et la réponse d'un coup, l'élève révèle chaque étape avec un bouton "Voir l'étape suivante", puis la correction complète (réponse + interprétation) au dernier clic.
- **Animations discrètes** (`notion.uxAnimations`, nouveau champ) : légère apparition en fondu + translation de 10px au défilement (IntersectionObserver), jamais de zoom ni de rebond, entièrement désactivée si `prefers-reduced-motion: reduce`.
- **Ton plus humain** sur la notion pilote "Théorème de Pythagore" (Troisième, Chapitre 13) : phrases de transition ("Regardons ensemble...", "Tu remarques que...", "Attention à ce détail...", "C'est ici que beaucoup d'élèves se trompent.", "Retiens simplement cette idée.") dans l'intro, le "pourquoi", l'intuition, la méthode, l'astuce et le résumé — phrases plus courtes, ton de professeur qui parle à l'élève plutôt que manuel qui énonce.

## Corrections
- Aucune (aucun comportement existant modifié pour les 66 autres notions de Troisième ni pour Seconde/Première — tous les ajouts sont gardés par des champs optionnels nouveaux, absents ailleurs).

## Optimisations
- Aucune.

## Fichiers modifiés
- `webapp/static/js/geomSvg.js` : tooltips (points/segments/polygones/arcs), `variant`/`reveal` sur segments et arcs.
- `webapp/static/js/cours.js` : navigation Précédent/Rejouer/Suivant de la figure, questions éclair (`questionsEclairHtml`), exemples interactifs (`buildExempleHtml` étendu), animations d'entrée (`notion.uxAnimations`).
- `webapp/static/css/cours.css` : styles de la navigation figure, du hover figure (scopé à `.cours-figure-wrap--xl`), des questions éclair, des exemples interactifs, des animations d'entrée (+ extension du bloc `prefers-reduced-motion`).
- `webapp/static/data/cours_troisieme/chapitre_13.json` (uniquement la notion `theoreme-de-pythagore`) : tooltips sur la figure, segment hypoténuse mis en évidence, 3 questions éclair, exemples marqués `interactif: true`, ton réécrit. Aucune autre notion du fichier, ni aucun autre chapitre, n'a été touché (vérifié via horodatage des fichiers).
- `webapp/static-dist/` reconstruit (`npm run build`).

## Bugs connus
- Les 4 échecs de tests suivants restent préexistants et sans rapport avec ce chantier (déjà documentés en v1.88) : `test_accesseur_exemple_par_difficulte`, `test_validate_cours_schema`, `test_formules_scaffoldees_depuis_reglesimportantes`, `test_oauth_callback_accessible_avec_headers`.
- Deux tests supplémentaires (`test_retry_fonctionne_meme_quota_epuise`, `test_ultra_chat_messages_illimite`) ont échoué lors d'un run complet de la suite, mais passent tous les deux en isolation : flaky/dépendant de l'ordre d'exécution (quota partagé entre tests), sans rapport avec ce chantier.

## Temps estimé de développement
- Environ 2h (extension geomSvg.js/cours.js/cours.css, rédaction du contenu enrichi de la notion pilote, vérification visuelle via Playwright desktop/mobile — figure interactive, exemples à révélation progressive, questions éclair —, tests de non-régression Python et JS).
