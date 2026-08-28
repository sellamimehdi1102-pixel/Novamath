"""Génération symbolique d'exercices pour la classe de Seconde
(`exercises_bank.json`).

Créé pendant le chantier de diversification ciblée sur 6 notions du cluster
"droites / inéquations en analytique" (Chapitre_6 et Chapitre_9) — ces
notions avaient déjà un gabarit textuel élevé (peu de doublons) mais
manquaient de variété de TYPE de raisonnement (trop de calcul direct, pas
assez de vrai/faux, erreur à corriger, exercice inversé...). Voir
tools/audit_exercise_taxonomy.py pour le diagnostic et
tools/generate_seconde_exercises.py pour la régénération du pool.

Même patron que webapp/exercise_generator/ (Première) : dataclass `Family`,
`_gen_xxx(rng)` avec sympy pour garantir la justesse mathématique,
`build_exercise()`, `generate_pool()`. Différence : ici un seul module peut
couvrir PLUSIEURS notions d'un même chapitre (`Family.chapter_id`/`.notion`
portés par la famille plutôt que par le module), car les 4 notions de
Chapitre_6 partagent le même objet géométrique (droites du plan) et les
mêmes outils sympy.
"""
