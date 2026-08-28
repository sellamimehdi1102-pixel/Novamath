# NovaMath v1.88

**Date** : 2026-07-25

**Nom de la mise à jour** : Nouveau moteur pédagogique v2 — notion pilote Théorème de Pythagore (Troisième)

## Nouveautés
- Nouveau moteur de rendu de cours, entièrement rétrocompatible (activé uniquement quand les nouveaux champs sont présents — aucun autre cours n'est affecté) :
  - Section **« Pourquoi apprend-on cela ? »** (`notion.pourquoi`) et section de fermeture **« Résumé de la leçon »** (`notion.resume`, carte dédiée `.cours-resume-card`).
  - Figures **agrandies et interactives** (`figure.emphasis`, colonne graphique 56/44 au lieu de 44/56) avec **révélation progressive par étapes** (`figure.steps` + pastilles cliquables, `reveal: 2/3` sur les éléments SVG via `geomSvg.js`) et **formule de synthèse** révélée en dernier (`figure.relation`, rendue en KaTeX).
  - `geomSvg.js` : support additif de `variant` (couleur par polygone) et `reveal` sur polygones/textes, `anchor`/`weight` sur les textes — aucune figure existante n'est affectée (champs optionnels).
  - Exemples **entièrement guidés** : `exemple.analyse` (lecture de l'énoncé), `exemple.choixMethode` (pourquoi cette méthode), `exemple.interpretation` (sens du résultat), en plus du calcul détaillé déjà existant.
  - `generate_cours_from_bank.py` : les chapitres reprennent désormais le vrai nom déclaré dans la banque (champ `chapter`) au lieu d'un titre générique "Chapitre N" — sans impact sur Seconde/Première qui n'ont pas ce champ (déjà livré en v1.87, documenté ici pour mémoire).
- **Notion pilote** : "Théorème de Pythagore" (Troisième, Chapitre 13) entièrement réécrite avec ce nouveau moteur — introduction, pourquoi, intuition, définition, figure interactive (triangle 3-4-5 avec démonstration par les aires des 3 carrés), 3 exemples guidés, pièges détaillés, astuce, à retenir, résumé, mini-quiz. Aucune autre notion (des 67 de Troisième, ni de Seconde/Première) n'a été touchée.

## Corrections
- Aucune (aucun comportement existant modifié pour les 66 autres notions de Troisième ni pour Seconde/Première).

## Optimisations
- Aucune.

## Fichiers modifiés
- `webapp/static/js/cours.js`, `webapp/static/js/geomSvg.js`, `webapp/static/css/cours.css`
- `webapp/static/data/cours_troisieme/chapitre_13.json` (uniquement la notion `theoreme-de-pythagore`)
- `webapp/tests/test_server_api_site_stats.py` (test `test_liste_les_deux_programmes_actuels` mis à jour pour inclure "troisieme", oublié lors de l'intégration de la classe en v1.86)
- `webapp/static-dist/` reconstruit (`npm run build`), en préservant explicitement le contenu déjà présent de `cours_premiere` dans le build (non régénéré depuis la source, voir "Bugs connus" v1.87)

## Bugs connus
- Les 4 échecs de tests suivants sont préexistants et sans rapport avec ce chantier (confirmés via `git stash`, contenu de `Chapitre_1` de Seconde modifié hors de toute session de travail) : `test_accesseur_exemple_par_difficulte`, `test_validate_cours_schema`, `test_formules_scaffoldees_depuis_reglesimportantes`, `test_oauth_callback_accessible_avec_headers`.

## Temps estimé de développement
- Environ 2h30 (cartographie du rendu existant, conception du schéma additif rétrocompatible, extension geomSvg.js/cours.js/cours.css, rédaction du contenu pilote, vérification visuelle via Playwright headless desktop/mobile, correction d'un chevauchement de labels, tests de non-régression).
