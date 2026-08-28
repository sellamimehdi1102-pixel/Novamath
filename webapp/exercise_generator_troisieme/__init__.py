"""Moteur de génération symbolique d'exercices (sympy) pour le niveau
Troisième — pendant de `webapp/exercise_generator/` (Première).

Chaque module couvre UNE notion de `exercises_bank_troisieme.json` et expose
le même contrat que `webapp/exercise_generator/second_degre.py` : une
dataclass `Family` (id, level, label, generate, structure_hint, rule_hint),
des fonctions `_gen_xxx(rng)` qui renvoient un dict rédigé ou `None` si le
tirage dégénère, `build_exercise(family, rng)`, `generate_one(...)` et
`generate_pool(per_family=..., seed=...)`.

Toute valeur numérique annoncée dans un énoncé/réponse est calculée ou
vérifiée par sympy (jamais tapée "en dur" sans contrôle). Chaque module
déclare son propre `GENERATED_ID_OFFSET`, distinct des offsets utilisés par
`webapp/exercise_generator/` (900_000+, Première) pour éviter toute
confusion, même si les deux pools ne sont jamais fusionnés dans le même
fichier (voir `tools/generate_troisieme_exercises.py` ->
`exercises_generated_troisieme.json`, consommé uniquement par le profil
"troisieme" du registre des curricula).
"""
