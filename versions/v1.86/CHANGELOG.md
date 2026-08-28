# NovaMath v1.86

**Date** : 2026-07-25

**Nom de la mise à jour** : Intégration de la classe Troisième dans toute l'architecture

## Nouveautés
- La classe **Troisième** est désormais un programme natif de NovaMath, au même titre que Seconde et Première : nouvelle entrée `CurriculumProfile(id="troisieme", ...)` dans `curriculum_registry.py`, seule source de vérité déjà consommée par tous les endpoints (`server.py`), le moteur de connaissances/chatbot (`canonical_ids.py`, `curriculum_stats.py`, `chatbot/*`) et le frontend (dashboard, cours, exercices, recherche, favoris, progression, évaluation initiale, moteur adaptatif) — aucune branche spécifique ajoutée ailleurs, tout est piloté par `class_level`.
- `static/data/cours_troisieme/` généré automatiquement par `generate_cours_from_bank.py` depuis les banques déjà fournies `exercises_bank_troisieme.json` / `exercises_bank_troisieme_natural.json` : 15 chapitres, 67 notions, 2010 exercices.
- "Troisième" ajoutée au formulaire d'avis utilisateurs (`server.py::CLASSE_CHOICES`, `static/index.html`) et à la meta description de `choisir-classe.html`.

## Corrections
- Aucune (étape d'intégration pure, aucun comportement existant modifié pour Seconde/Première).

## Optimisations
- Aucune.

## Fichiers modifiés
- `webapp/curriculum_registry.py`, `webapp/server.py`, `webapp/static/index.html`, `webapp/static/choisir-classe.html`, `webapp/tests/test_curriculum_registry.py`
- Créé : `webapp/static/data/cours_troisieme/chapitre_1.json` à `chapitre_15.json`
- `webapp/static-dist/` reconstruit via `npm run build` (Vite)

## Bugs connus
- Aucun. Note sans rapport avec ce chantier : `test_non_regression.py` a 2 échecs préexistants (contenu `chapitre_1.json` de Seconde modifié hors de ce chantier, mismatch `erreursFrequentesDetail`/`erreursFrequentes` et scaffolding des formules) — confirmés antérieurs à cette mise à jour via `git stash`.

## Temps estimé de développement
- Environ 1h (exploration de l'architecture existante via le patron "Première", ajout du registre, génération des cours, tests de non-régression, vérification bout-en-bout via API).
