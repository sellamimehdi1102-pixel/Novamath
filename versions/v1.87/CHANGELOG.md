# NovaMath v1.87

**Date** : 2026-07-25

**Nom de la mise à jour** : Personnalisation UX de la classe Troisième : vrais noms de chapitres + correctifs de catégorisation des figures

## Nouveautés
- `generate_cours_from_bank.py` utilise désormais le champ `chapter` (nom réel, ex. "Nombres entiers", "Théorème de Thalès") déjà présent dans `exercises_bank_troisieme.json` pour titrer les chapitres, au lieu du générique `chapter_id.replace("_", " ")` ("Chapitre 1") — comportement inchangé pour Seconde/Première dont la banque n'a pas ce champ.
- Audit complet et vérification bout-en-bout (via API réelle, session invité) de Troisième : structure des 15 chapitres/67 notions (ordre, ids, doublons), 2010 exercices (champs requis, orphelins), recherche (30 requêtes dont Pythagore/Thalès/fonctions/probabilités), dashboard/favoris/historique/progression (isolation confirmée vs Seconde), évaluation initiale (exercices exclusivement Troisième), reconnaissance chatbot des notions.

## Corrections
- `pedagogy_templates.py::_CATEGORY_RULES` : trois faux-positifs de catégorisation lexicale, révélés par le vocabulaire propre à Troisième (absent de Seconde/Première), corrigés sans changer le comportement des deux autres classes :
  - "Somme des angles d'un triangle et inégalité triangulaire" matchait à tort la catégorie `suites` via le motif générique `somme de` (substring de "somme des") → figure de suite numérique affichée sur une notion de géométrie. Motif resserré à `somme des termes|somme des n premiers|calcul de sommes`.
  - La même notion matchait ensuite `intervalles` via `inegalite` (substring de "inégalité triangulaire", y compris dans le slug avec tiret) → figure de droite graduée incohérente. Exclusion ajoutée : `inegalite(?![ -]triangulaire)`.
  - "Représentations graphiques de données" matchait à tort `fonctions_generalites` via le mot `graphique` → figure de courbe/fonction affichée sur une notion de statistiques. Catégorie `statistiques` désormais prioritaire via `representation.*donnees|diagramme`.

## Optimisations
- Aucune.

## Fichiers modifiés
- `webapp/generate_cours_from_bank.py`, `webapp/pedagogy_templates.py`
- Régénéré : `webapp/static/data/cours_troisieme/chapitre_1.json` à `chapitre_15.json` (titres réels + figures corrigées)
- `webapp/static-dist/data/cours_troisieme/` synchronisé manuellement (dossier ciblé uniquement, sans reconstruire tout `static-dist/` afin de ne pas toucher au contenu de Première déjà buildé)

## Bugs connus
- Recherche "échantillonnage" renvoie 0 résultat : ce mot n'apparaît littéralement dans aucun exercice de la banque Troisième (pas une régression de la recherche — comportement identique pour tout mot absent du contenu source).
- Dérive préexistante et sans rapport avec ce chantier, découverte en marge : `webapp/static-dist/data/cours_premiere/` contient un contenu plus riche (templates pédagogiques plus récents) que `webapp/static/data/cours_premiere/` actuellement suivi par git — signalé pour information, non corrigé (hors périmètre "ne pas toucher aux autres classes").

## Temps estimé de développement
- Environ 1h30 (audit structurel + fonctionnel complet, découverte et correction de 2 bugs de regex de catégorisation partagés avec Première, vérification bout-en-bout via API, tests de non-régression Python/JS).
