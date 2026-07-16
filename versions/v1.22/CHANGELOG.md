# NovaMath v1.22

**Date** : 2026-07-13

**Nom de la mise à jour** : Rose moderne + notation mathématique réelle (quiz, exercices, cours)

## Nouveautés
- Aucune (finalisation esthétique et de contenu, pas de fonctionnalité nouvelle).

## Corrections
- **Couleur d'accent « Rouge »** (Paramètres → Apparence) remplacée par un rose moderne et élégant (`#db2777` → `#f472b6`), appliquée automatiquement partout où l'accent est utilisé (boutons, switches, badges, bordures, focus, progression...) via les variables CSS existantes. La clé interne `red` et le nom de fichier n'ont pas changé (aucune migration nécessaire pour les préférences déjà enregistrées) ; seul le label visible passe de « Rouge » à « Rose ».
- **Refonte complète du moteur de notation mathématique** (`tools/legacy-pipeline/07_naturalize_exercises.py`) : l'ancienne approche « tout épeler en mots français » (`7 puissance 5 fois 7 puissance (-2) sur 7 puissance 4`) est remplacée par une vraie écriture mathématique (`(7⁵ × 7⁻²)/7⁴`), comme dans un manuel scolaire. Le moteur traite chaque fragment mathématique du texte : conversion directe en symboles Unicode (×, ÷, ±, ≥, ≤, ≠, ∈, ∉, ℕ/ℤ/ℚ/ℝ/ℂ, ∞, √, exposants réels ⁰¹²³...ⁿ, fractions simples « a/b »...) quand c'est fiable, et repli propre sur du LaTeX rendu par KaTeX (déjà utilisé sur le site) pour les constructions trop complexes en texte brut (vecteurs, moyennes/écarts-types avec barre, angles avec accent circonflexe, sommes, systèmes d'équations, coordonnées indexées comme x_A) — jamais de conversion partielle ou cassée.
- `exercises_bank_natural.json` (2085 exercices, effectivement la version servie par défaut aux élèves) régénéré avec ce nouveau moteur ; `exercises_bank_reformulations.json` (champs enonce/hint/answer/solution_steps + `natural_variants`) nettoyé de la même façon (nouveau script `09_naturalize_reformulations.py`).
- Élimination de tous les résidus LaTeX non convertis identifiés en cours de route : `\vec`/`\sqrt` sans espace avant un argument non accolé (`\vec0`, `\sqrt2`), fractions LaTeX sans accolades (`\frac12`) ou à accolades mixtes (`\frac1{12}`), `\sigma_x`/`\sigma^2` (mal découpés par l'ancien attrapeur d'indices générique), `\approx`, `\mathbb{D}`, `\mathcal{}`, `\to`, `\max`/`\min` sans parenthèses, et surtout les exposants composés (`a^{n+m}`) qui n'étaient auparavant ni convertis ni protégés (donc affichés cassés) — désormais toujours confiés à KaTeX si non simplifiables.

## Optimisations
- Aucune.

## Fichiers modifiés
- `webapp/static/css/tokens.css`, `webapp/static/css/settings.css` (couleur d'accent rose)
- `webapp/static/js/settings.js` (libellé « Rose »)
- `tools/legacy-pipeline/07_naturalize_exercises.py` (réécrit)
- `tools/legacy-pipeline/09_naturalize_reformulations.py` (nouveau)
- `exercises_bank_natural.json`, `exercises_bank_reformulations.json` (régénérés)

## Bugs connus
- Aucun identifié après vérification visuelle (mode invité, captures d'écran de chaque cas : puissances/fractions, vecteurs/colinéarité, systèmes d'équations, palette de couleurs).

## Temps estimé de développement
- Session unique, longue durée : conception et implémentation d'un moteur de conversion LaTeX → notation Unicode/KaTeX hybride, itérations de débogage sur l'ensemble du corpus (2085 exercices × 3 fichiers), tests visuels bout en bout.
