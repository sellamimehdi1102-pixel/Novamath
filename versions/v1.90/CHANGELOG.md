# NovaMath v1.90

**Date** : 2026-07-25

**Nom de la mise à jour** : Vrais intitulés des 15 chapitres de Troisième (chapters_meta corrigé)

## Nouveautés
- 5 des 15 chapitres de Troisième renommés avec un intitulé plus précis et fidèle au contenu réel (analyse des notions et des exercices de chaque chapitre) : `Nombres entiers` → `Arithmétique`, `Représentation et traitement de données` → `Statistiques`, `Construction et transformation de figures` → `Transformations du plan`, `Triangles rectangles : trigonométrie` → `Théorème de Pythagore et trigonométrie`, `Solides de l'espace` → `Géométrie dans l'espace`. Les 10 autres chapitres avaient déjà un intitulé correct et n'ont pas été touchés. Voir le tableau récapitulatif complet livré en fin de tâche.

## Corrections
- **Cause racine du bug "Chapitre 1", "Chapitre 2"... affiché dans l'application** : `/api/chapters` (server.py::`_class_bank`) ne peuplait `chapter_meta` (titres des chapitres) que pour les classes déclarant un `program_file` (Seconde). Pour Première et Troisième (`program_file=None`), `chapter_meta` restait vide et le titre retombait sur `chapter_id.replace("_", " ")` (ex. "Chapitre_13" → "Chapitre 13"), quel que soit le vrai contenu du chapitre. Corrigé en peuplant `chapter_meta` depuis le `title` déjà présent dans `courses_dir/chapitre_N.json` (même source de vérité que le chatbot et que le lecteur de cours) quand aucun `program_file` n'existe — générique, aucune classe codée en dur. Ce correctif propage automatiquement le bon titre à : la grille des chapitres (chapitres.html), le dashboard, la barre de recherche (index construit depuis `chapters_meta`), les favoris, l'historique/séries (profil.js via `getChapterTitles()`), les breadcrumbs du lecteur de cours, et l'API `/api/chapters` elle-même. Le chatbot (`chatbot/knowledge_engine.py::_load_notions`) lisait déjà directement le `title` du cours par classe : il affichait donc déjà les bons intitulés dès que les fichiers `chapitre_N.json` ont été corrigés.
- Aucun ID de chapitre/notion, aucun lien notion↔exercice, aucun favori, aucune progression, aucun moteur adaptatif, aucun JSON d'exercices (`exercises_bank_troisieme.json`) ni aucune route API n'a été modifié — uniquement les intitulés affichés.

## Optimisations
- Aucune.

## Fichiers modifiés
- `webapp/server.py` (`_class_bank`) : repli générique de `chapter_meta` depuis `courses_dir` quand `program_file` est absent.
- `webapp/static/data/cours_troisieme/chapitre_1.json`, `chapitre_9.json`, `chapitre_11.json`, `chapitre_13.json`, `chapitre_15.json` : uniquement le champ racine `title` (aucune notion, aucun exercice, aucun id modifié).
- `webapp/static-dist/` reconstruit (`npm run build`).

## Bugs connus
- Les 4 échecs préexistants déjà documentés en v1.88/v1.89 (sans rapport avec ce chantier) : `test_accesseur_exemple_par_difficulte`, `test_validate_cours_schema`, `test_formules_scaffoldees_depuis_reglesimportantes`, `test_oauth_callback_accessible_avec_headers`.
- Un test de quota chatbot supplémentaire a échoué lors du run complet mais passe en isolation (flaky, quota partagé entre tests, déjà observé en v1.89) : `test_ultra_reste_illimite_apres_grosse_consommation`.
- La classe Première reste inchangée : ses fichiers `courses_dir/chapitre_N.json` contiennent eux-mêmes des titres génériques ("Chapitre 1", etc.) — non demandé dans cette tâche, non régressé (comportement strictement identique à avant).
- Un petit libellé "Chapitre N" (numéro seul) reste affiché sous le vrai titre, dans les cartes et l'en-tête de chapitre (convention "Chapitre 13 — Théorème de Pythagore..." courante dans les manuels scolaires) — jamais utilisé seul comme titre, uniquement en complément du vrai intitulé désormais correct partout.

## Temps estimé de développement
- Environ 1h30 (diagnostic de la cause racine via lecture de server.py/chapitres.js/dashboard.js/seriesview.js/knowledge_engine.py, analyse du contenu réel des 15 chapitres via notions + banque d'exercices, choix des 5 renommages, correctif générique server.py, vérification visuelle Playwright, tests de non-régression).
