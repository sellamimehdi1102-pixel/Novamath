# NovaMath v1.21

**Date** : 2026-07-13

**Nom de la mise à jour** : Finalisation onglet Cours : rendu KaTeX, figures et banque d'exercices

## Nouveautés
- 5 nouvelles figures géométriques (SVG vectoriel, repère/grille/axes) pour les notions du Chapitre 6 « Droites du plan et systèmes d'équations » qui n'en avaient aucune : vecteur directeur, équation cartésienne, coefficient directeur, comparaison de deux droites (parallèles), résolution d'un système (droites sécantes) — et 1 figure pour la dernière notion sans illustration du Chapitre 5 (colinéarité de points alignés).
- Petite note discrète sous le titre de la page Entraînement (« Le contenu des exercices reste en français quelle que soit la langue de l'interface »), déjà traduite en i18n mais jamais affichée jusqu'ici — câblée dans `exercice.html`.

## Corrections
- **Bug majeur (rendu KaTeX)** : les 119 étapes de calcul (`exemples[].calcul[].expr`) des 12 chapitres de cours n'étaient jamais entourées de `$...$` et s'affichaient donc en LaTeX brut illisible (ex: `\vec{AB}(4-1\,;6-2)`) au lieu d'une vraie notation mathématique. Corrigé au niveau du renderer (`cours.js`), qui encadre désormais systématiquement `c.expr` — corrige d'un coup l'intégralité des exemples résolus du site, sans toucher aux données.
- Icône « livre » résiduelle sur les cartes de l'onglet Exercices (compteur « X notions ») remplacée par l'icône `layers` déjà utilisée ailleurs pour cette notion ; la grande icône de carte utilise désormais `checklist` au lieu d'un SVG « livre » codé en dur.
- Faute de frappe présente depuis plusieurs versions (`Programme AI.json`, héritée jusqu'en v1.12) : titre du Chapitre 8 « Varaitions et extrmums » → « Variations et extremums ». Visible sur la page Cours et dans l'API `/api/chapters`.
- 148 flèches vectorielles unicode combinantes (`u⃗`, `AB⃗`...) dans `exercises_bank.json` / `exercises_bank_reformulations.json` ne s'affichaient pas (caractère non supporté par la police, rendu en carré vide) — remplacées par la notation LaTeX `$\vec{...}$`, correctement rendue par KaTeX.
- Pipeline de naturalisation (`tools/legacy-pipeline/07_naturalize_exercises.py`) : ajout des règles manquantes `\dfrac`, `\vec` sans accolades, `\pm`, `\cdot`, `\%`, `{,}` (virgule décimale protégée) et distinction `+\infty`/`-\infty` (« plus/moins l'infini » au lieu de « +l'infini ») ; `exercises_bank_natural.json` régénéré (2085 exercices) — ~500 exercices avaient au moins un résidu LaTeX non converti.
- Suppression d'une étape de solution hors-sujet (« Note en programmation : ... SymPy ») glissée par erreur dans un exercice, présente identiquement dans les 3 banques.
- Uniformisation de l'astérisque informatique (`2*4`) en notation mathématique (`2×4`) dans 23 étapes de solution de `exercises_bank.json` / `exercises_bank_reformulations.json`.

## Optimisations
- Aucune (corrections de contenu et de rendu, pas de changement de performance).

## Fichiers modifiés
- `webapp/static/js/cours.js` (fix rendu KaTeX des étapes de calcul)
- `webapp/static/js/chapitres.js` (icônes checklist/layers)
- `webapp/static/exercice.html` (notice i18n câblée)
- `webapp/static/data/cours/chapitre_5.json`, `chapitre_6.json` (6 figures ajoutées)
- `Programme AI.json` (typo titre Chapitre 8)
- `exercises_bank.json`, `exercises_bank_reformulations.json`, `exercises_bank_natural.json` (flèches vectorielles, artefacts LaTeX, note hors-sujet, astérisques)
- `tools/legacy-pipeline/07_naturalize_exercises.py` (règles de conversion complétées)
- `tools/legacy-pipeline/08_fix_bank_artifacts.py` (nouveau script, corrections ponctuelles de la banque)

## Bugs connus
- Dans `exercises_bank_natural.json`, la conversion mécanique de `$\vec{u}$` en « le vecteur u » peut produire une légère redondance quand la phrase source contenait déjà le mot « vecteurs » au pluriel (ex : « Les vecteurs le vecteur u = ... »). Lisible et correct mathématiquement, mais pas toujours élégant grammaticalement — limite connue de l'approche déterministe (regex) du pipeline de naturalisation.

## Temps estimé de développement
- Session unique, longue durée : audit complet des 12 chapitres et de la banque de 2085 exercices (via agents dédiés), correction d'un bug de rendu affectant l'ensemble du site, ajout de figures géométriques, corrections de contenu, tests visuels bout en bout (Playwright, mode invité, captures d'écran de chaque figure ajoutée).
