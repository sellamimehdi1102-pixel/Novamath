"""Moteur de génération symbolique d'exercices (sympy).

Contrairement aux banques `exercises_bank*.json` (contenu figé, écrit une
fois hors-ligne — voir tools/legacy-pipeline/README.md), ce package génère
des exercices dont la STRUCTURE mathématique varie réellement (pas
seulement les coefficients), avec une difficulté calculée à partir de la
complexité algébrique réelle de l'expression produite, et une correction
garantie par calcul formel (sympy), jamais par un LLM.

Un seul module de familles existe pour l'instant : `derivatives` (dérivées,
Première spécialité — voir tools/generate_derivative_exercises.py pour
régénérer le pool consommé par server.py). D'autres notions peuvent être
ajoutées en suivant le même schéma (voir `derivatives.FAMILIES` comme
référence de structure).
"""
