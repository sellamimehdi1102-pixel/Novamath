"""Chapitre 2 de la Première spécifique (manuel « Première ES/L ») — fonctions
racine carrée et cube. Les familles « image et antécédents » et « lecture de
variations » sont celles du module automatismes (rattachées par programme_1es.py).
Créé lors de l'adaptation du 2026-10-26 ; contrat : voir _commun_1es.py.
"""
import math
from fractions import Fraction as F
from typing import Optional

from exercise_generator_premiere_specifique import _commun_1es as c
from exercise_generator_premiere_specifique._commun_1es import Family, dec

CHAPTER_ID = "Chapitre_2"
N_RAC = "Fonction racine carrée"
N_CUBE = "Fonction cube"
GENERATED_ID_OFFSET = 1_210_000
LEVEL_META = c.LEVEL_META


def _non_carre(rng, lo=2, hi=60):
    while True:
        n = rng.randint(lo, hi)
        if math.isqrt(n) ** 2 != n:
            return n


def _gen_comparer_racines(rng):
    a, b = _non_carre(rng), _non_carre(rng)
    if a == b:
        return None
    signe = "<" if a < b else ">"
    return dict(enonce=f"Sans calculatrice, comparer $\\sqrt{{{a}}}$ et $\\sqrt{{{b}}}$.",
                answer=f"$\\sqrt{{{a}}} {signe} \\sqrt{{{b}}}$.",
                hint="La fonction racine carrée est strictement croissante sur $[0 ; +\\infty[$.",
                steps=[f"${a} {signe} {b}$.", f"La racine carrée conserve l'ordre : $\\sqrt{{{a}}} {signe} \\sqrt{{{b}}}$."])


def _gen_equation_racine(rng):
    k = rng.choice([1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12, -2, -3, -5])
    if k < 0:
        return dict(enonce=f"Résoudre dans $[0 ; +\\infty[$ l'équation $\\sqrt{{x}} = {k}$.",
                    answer="L'équation n'a pas de solution.",
                    hint="Une racine carrée est toujours positive ou nulle.",
                    steps=[f"${k} < 0$.", "Une racine carrée est positive ou nulle : aucun réel ne convient."])
    return dict(enonce=f"Résoudre dans $[0 ; +\\infty[$ l'équation $\\sqrt{{x}} = {k}$.",
                answer=f"L'unique solution est $x = {k * k}$.",
                hint="Pour un nombre positif, élève au carré.",
                steps=[f"${k} \\geqslant 0$ : $\\sqrt{{x}} = {k} \\iff x = {k}^2$.", f"$x = {k * k}$."])


def _gen_inequation_racine(rng):
    k = rng.randint(2, 12)
    if rng.random() < 0.5:
        return dict(enonce=f"Résoudre l'inéquation $\\sqrt{{x}} \\leqslant {k}$.",
                    answer=f"$\\mathcal{{S}} = [0 ; {k * k}]$.",
                    hint=f"Écris ${k}$ comme une racine carrée.",
                    steps=["$\\sqrt{x}$ existe pour $x \\geqslant 0$.", f"${k} = \\sqrt{{{k * k}}}$ et la racine carrée est strictement croissante : $x \\leqslant {k * k}$.",
                           f"$\\mathcal{{S}} = [0 ; {k * k}]$."])
    return dict(enonce=f"Résoudre l'inéquation $\\sqrt{{x}} > {k}$.",
                answer=f"$\\mathcal{{S}} = ]{k * k} ; +\\infty[$.",
                hint=f"Écris ${k}$ comme une racine carrée.",
                steps=[f"${k} = \\sqrt{{{k * k}}}$.", f"La racine carrée est strictement croissante : $\\sqrt{{x}} > \\sqrt{{{k * k}}} \\iff x > {k * k}$.",
                       f"$\\mathcal{{S}} = ]{k * k} ; +\\infty[$."])


def _gen_encadrer_racine(rng):
    a, b = sorted(rng.sample(range(1, 16), 2))
    return dict(enonce=f"Sachant que ${a * a} \\leqslant x \\leqslant {b * b}$, encadrer $\\sqrt{{x}}$.",
                answer=f"${a} \\leqslant \\sqrt{{x}} \\leqslant {b}$.",
                hint="Une fonction croissante conserve les inégalités.",
                steps=["La fonction racine carrée est croissante sur $[0 ; +\\infty[$.",
                       f"$\\sqrt{{{a * a}}} \\leqslant \\sqrt{{x}} \\leqslant \\sqrt{{{b * b}}}$, soit ${a} \\leqslant \\sqrt{{x}} \\leqslant {b}$."])


def _cube_de(q) -> str:
    """« (−2)^3 » pour un négatif, « 2^3 » sinon."""
    return f"({dec(q)})^3" if q < 0 else f"{dec(q)}^3"


def _gen_calcul_cube(rng):
    a = F(rng.choice([-5, -4, -3, -2, 2, 3, 4, 5]))
    b = F(rng.choice([-5, -3, -2, -1, 1, 2, 3, 5]), rng.choice([10, 10, 2]))
    return dict(enonce=f"Calculer ${_cube_de(a)}$ et ${_cube_de(b)}$.",
                answer=f"${_cube_de(a)} = {dec(a ** 3)}$ et ${_cube_de(b)} = {dec(b ** 3)}$.",
                hint="Le cube d'un nombre négatif est négatif.",
                steps=[f"${_cube_de(a)} = {dec(a)} \\times {dec(a)} \\times {dec(a)} = {dec(a ** 3)}$." if a > 0
                       else f"${_cube_de(a)} = ({dec(a)}) \\times ({dec(a)}) \\times ({dec(a)}) = {dec(a ** 3)}$.",
                       f"Le cube de ${dec(b)}$ vaut ${dec(b ** 3)}$."])


def _gen_comparer_cubes(rng):
    a, b = (F(rng.choice(range(-30, 31)), 10) for _ in range(2))
    if a == b:
        return None
    signe = "<" if a < b else ">"
    return dict(enonce=f"Sans calcul, comparer ${_cube_de(a)}$ et ${_cube_de(b)}$.",
                answer=f"${_cube_de(a)} {signe} {_cube_de(b)}$.",
                hint="La fonction cube est strictement croissante sur $\\mathbb{R}$.",
                steps=[f"${dec(a)} {signe} {dec(b)}$.", f"La fonction cube conserve l'ordre : ${_cube_de(a)} {signe} {_cube_de(b)}$."])


def _gen_equation_cube(rng):
    k = rng.choice([-5, -4, -3, -2, -1, 1, 2, 3, 4, 5, 6, 10])
    return dict(enonce=f"Résoudre dans $\\mathbb{{R}}$ l'équation $x^3 = {k ** 3}$.",
                answer=f"$\\mathcal{{S}} = \\{{{k}\\}}$.",
                hint=f"Écris ${k ** 3}$ comme un cube.",
                steps=[f"${k ** 3} = ({k})^3$." if k < 0 else f"${k ** 3} = {k}^3$.",
                       f"La fonction cube est strictement croissante : l'unique solution est $x = {k}$."])


def _gen_inequation_cube(rng):
    a = rng.choice([-4, -3, -2, -1, 1, 2, 3, 4])
    if rng.random() < 0.5:
        s = f"x - {a}" if a > 0 else f"x + {-a}"
        return dict(enonce=f"Résoudre dans $\\mathbb{{R}}$ l'inéquation $({s})^3 \\leqslant 0$.",
                    answer=f"$\\mathcal{{S}} = ]-\\infty ; {a}]$.",
                    hint="Un cube a le même signe que le nombre élevé au cube.",
                    steps=[f"$({s})^3$ a le signe de ${s}$.", f"$({s})^3 \\leqslant 0 \\iff {s} \\leqslant 0 \\iff x \\leqslant {a}$."])
    return dict(enonce=f"Résoudre dans $\\mathbb{{R}}$ l'inéquation $x^3 > {a ** 3}$.",
                answer=f"$\\mathcal{{S}} = ]{a} ; +\\infty[$.",
                hint=f"Écris ${a ** 3}$ comme un cube.",
                steps=[f"${a ** 3} = ({a})^3$." if a < 0 else f"${a ** 3} = {a}^3$.", f"La fonction cube est strictement croissante : $x^3 > {a ** 3} \\iff x > {a}$."])


def _gen_racine_et_cube(rng):
    k = rng.randint(2, 6)
    cube = rng.choice([1, 2, 3])
    if cube ** 3 > k * k:
        return None
    return dict(enonce=f"Déterminer l'ensemble des réels $x$ tels que $\\sqrt{{x}} \\leqslant {k}$ et $x^3 \\geqslant {cube ** 3}$.",
                answer=f"$\\mathcal{{S}} = [{cube} ; {k * k}]$.",
                hint="Résous chaque inéquation séparément, puis prends l'intersection.",
                steps=[f"$\\sqrt{{x}} \\leqslant {k} \\iff 0 \\leqslant x \\leqslant {k * k}$ (racine carrée croissante, $x \\geqslant 0$).",
                       f"$x^3 \\geqslant {cube ** 3} = {cube}^3 \\iff x \\geqslant {cube}$ (cube croissant).",
                       f"Les deux conditions : ${cube} \\leqslant x \\leqslant {k * k}$, soit $\\mathcal{{S}} = [{cube} ; {k * k}]$."])


FAMILIES = [
    Family("comparer_racines", 1, "Comparer deux racines carrées", _gen_comparer_racines, N_RAC, 1.2),
    Family("equation_racine", 1, "Résoudre √x = k", _gen_equation_racine, N_RAC, 1.4),
    Family("inequation_racine", 2, "Résoudre une inéquation avec √x", _gen_inequation_racine, N_RAC, 2.2),
    Family("encadrer_racine", 2, "Encadrer une racine carrée", _gen_encadrer_racine, N_RAC, 2.4),
    Family("calcul_cube", 1, "Calculer des cubes", _gen_calcul_cube, N_CUBE, 1.2),
    Family("comparer_cubes", 1, "Comparer deux cubes", _gen_comparer_cubes, N_CUBE, 1.4),
    Family("equation_cube", 2, "Résoudre x³ = k", _gen_equation_cube, N_CUBE, 2.2),
    Family("inequation_cube", 3, "Résoudre une inéquation avec un cube", _gen_inequation_cube, N_CUBE, 3.0),
    Family("racine_et_cube", 4, "Combiner racine carrée et cube", _gen_racine_et_cube, N_RAC, 4.0),
]
FAMILIES_BY_ID = {f.id: f for f in FAMILIES}


def generate_one(family_id: str, seed: Optional[int] = None) -> dict:
    return c.generate_one(FAMILIES, CHAPTER_ID, family_id, seed)


def generate_pool(per_family: int = 24, seed: int = 20261102) -> list[dict]:
    return c.generate_pool(FAMILIES, CHAPTER_ID, GENERATED_ID_OFFSET, per_family, seed)
