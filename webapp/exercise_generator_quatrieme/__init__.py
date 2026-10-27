"""Moteur de génération symbolique d'exercices (sympy) pour le niveau
Quatrième — pendant de `webapp/exercise_generator_troisieme/`.

Même contrat que les autres classes (voir exercise_generator/registry.py) :
`FAMILIES` (dataclass `Family` avec `notion` par famille), `CHAPTER_ID`,
`generate_one(family_id, seed=None)` et `generate_pool(per_family, seed)`.
Toute valeur annoncée dans un énoncé, une réponse ou une correction est
calculée en arithmétique exacte (sympy `Rational`/`sqrt`) ; les valeurs
approchées sont arrondies à partir de la valeur exacte, jamais d'une valeur
intermédiaire déjà arrondie.

Identifiants : 400 000 + 10 000 × numéro de chapitre (Chapitre_8 →
480 000+), plage libre dans toutes les autres banques. Le pool est écrit par
tools/generate_quatrieme_exercises.py dans exercises_generated_quatrieme.json,
consommé uniquement par le profil "quatrieme" du registre des curricula.
"""
