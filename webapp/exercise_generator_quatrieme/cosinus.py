"""Chapitre 10 — Cosinus (générateurs). Cosinus uniquement.

    nommer_cotes         N1  hypoténuse et côté adjacent (lettres variées)
    angle_complementaire N1  l'autre angle aigu
    calculer_cos         N2  cos = adjacent / hypoténuse (fraction irréductible et décimal)
    cos_pythagore        N2  hypoténuse par Pythagore (triplets), puis cosinus
    cote_adjacent        N3  adjacent = hypoténuse × cos (arrondi)
    hypotenuse_cos       N3  hypoténuse = adjacent ÷ cos (arrondi)
    angle_depuis_cotes   N4  angle = cos⁻¹(adjacent / hypoténuse) (arrondi)
    probleme_echelle     N4  angle d'une échelle avec le sol

Les valeurs approchées sont calculées une seule fois en flottants puis
arrondies ; les tirages trop proches d'une demi-unité d'arrondi sont rejetés
(un arrondi ambigu ne doit jamais être proposé).
"""
import math
import random
from fractions import Fraction
from typing import Optional

from ._commun import Chapter, Family, frac, grp

N1 = "Nommer les côtés d'un triangle rectangle"
N2 = "Le cosinus d'un angle aigu"
N3 = "Utiliser le cosinus pour trouver un côté"
N4 = "Calculer un angle avec le cosinus"

_TRIPLETS = ((3, 4, 5), (5, 12, 13), (8, 15, 17), (7, 24, 25), (20, 21, 29), (9, 40, 41), (6, 8, 10), (9, 12, 15), (12, 16, 20))


def _lettres(rng):
    return rng.sample("ABCDEFGHIJKLMNPRSTUVWXYZ", 3)


def _arrondi(x: float, d: int) -> Optional[str]:
    """Arrondi à d décimales en écriture française, ou None si x est trop proche d'une demi-unité."""
    y = x * 10 ** d
    if abs(y - math.floor(y) - 0.5) < 1e-4:
        return None
    return grp(Fraction(round(y), 10 ** d)) if d else grp(round(y))


def _cos(deg):
    return math.cos(math.radians(deg))


def _gen_nommer(rng: random.Random) -> Optional[dict]:
    a, b, c = _lettres(rng)          # triangle abc rectangle en c, angle étudié en a
    return {
        "enonce": f"Le triangle ${a}{b}{c}$ est rectangle en ${c}$. Pour l'angle $\\widehat{{{b}{a}{c}}}$, nommer l'hypoténuse et le côté adjacent.",
        "answer": f"Hypoténuse $[{a}{b}]$ ; côté adjacent $[{a}{c}]$.",
        "hint": "L'hypoténuse est en face de l'angle droit ; le côté adjacent touche l'angle et n'est pas l'hypoténuse.",
        "steps": [f"L'angle droit est en ${c}$ : l'hypoténuse est le côté en face, $[{a}{b}]$.",
                  f"Les côtés de l'angle en ${a}$ sont $[{a}{b}]$ et $[{a}{c}]$ : le côté adjacent est $[{a}{c}]$."],
        "notion": N1,
    }


def _gen_complementaire(rng: random.Random) -> Optional[dict]:
    a, b, c = _lettres(rng)
    ang = Fraction(rng.randint(10, 800), 10)
    if ang >= 85 or ang <= 5:
        return None
    return {
        "enonce": f"Le triangle ${a}{b}{c}$ est rectangle en ${c}$ et $\\widehat{{{b}{a}{c}}} = {grp(ang)}°$. Calculer $\\widehat{{{a}{b}{c}}}$.",
        "answer": f"$\\widehat{{{a}{b}{c}}} = {grp(90 - ang)}°$.",
        "hint": "Les deux angles aigus d'un triangle rectangle sont complémentaires.",
        "steps": ["Les angles aigus totalisent $90°$.", f"$90 - {grp(ang)} = {grp(90 - ang)}$."],
        "notion": N1,
    }


def _gen_calculer_cos(rng: random.Random) -> Optional[dict]:
    a, b, c = _lettres(rng)
    hyp = rng.randint(4, 40)
    adj = rng.randint(1, hyp - 1)
    q = Fraction(adj, hyp)
    dec = q.denominator in (1, 2, 4, 5, 8, 10, 16, 20, 25, 40)
    val = f"{frac(q)} = {grp(q)}" if dec else frac(q)
    return {
        "enonce": (f"Le triangle ${a}{b}{c}$ est rectangle en ${c}$, avec ${a}{c} = {adj}$ cm et ${a}{b} = {hyp}$ cm. "
                   f"Calculer $\\cos \\widehat{{{b}{a}{c}}}$ (fraction irréductible{', puis écriture décimale' if dec else ''})."),
        "answer": f"$\\cos \\widehat{{{b}{a}{c}}} = {val}$",
        "hint": "Côté adjacent sur hypoténuse.",
        "steps": [f"Hypoténuse $[{a}{b}]$ ; côté adjacent à l'angle en ${a}$ : $[{a}{c}]$.",
                  f"$\\cos \\widehat{{{b}{a}{c}}} = \\dfrac{{{a}{c}}}{{{a}{b}}} = "
                  + (f"{val}$." if q.denominator == hyp else f"\\dfrac{{{adj}}}{{{hyp}}} = {val}$.")],
        "notion": N2,
    }


def _gen_cos_pythagore(rng: random.Random) -> Optional[dict]:
    a, b, c = _lettres(rng)
    p, q, r = rng.choice(_TRIPLETS)
    if rng.random() < 0.5:
        p, q = q, p
    # angle en a ; ac = p (adjacent), bc = q, ab = r (hypoténuse)
    return {
        "enonce": (f"Le triangle ${a}{b}{c}$ est rectangle en ${c}$, avec ${a}{c} = {p}$ cm et ${b}{c} = {q}$ cm. "
                   f"Calculer ${a}{b}$, puis $\\cos \\widehat{{{b}{a}{c}}}$ sous forme de fraction irréductible."),
        "answer": f"${a}{b} = {r}$ cm et $\\cos \\widehat{{{b}{a}{c}}} = {frac(Fraction(p, r))}$.",
        "hint": "Théorème de Pythagore pour l'hypoténuse, puis côté adjacent sur hypoténuse.",
        "steps": [f"${a}{b}^2 = {p}^2 + {q}^2 = {p * p + q * q}$, donc ${a}{b} = {r}$ cm.",
                  f"$\\cos \\widehat{{{b}{a}{c}}} = \\dfrac{{{a}{c}}}{{{a}{b}}} = \\dfrac{{{p}}}{{{r}}}"
                  + (f" = {frac(Fraction(p, r))}$." if Fraction(p, r).denominator != r else "$.")],
        "notion": N2,
    }


def _gen_adjacent(rng: random.Random) -> Optional[dict]:
    a, b, c = _lettres(rng)
    hyp = Fraction(rng.randint(20, 300), 10)
    ang = rng.randint(10, 80)
    res = _arrondi(float(hyp) * _cos(ang), 1)
    if res is None:
        return None
    return {
        "enonce": (f"Le triangle ${a}{b}{c}$ est rectangle en ${c}$, ${a}{b} = {grp(hyp)}$ cm et $\\widehat{{{b}{a}{c}}} = {ang}°$. "
                   f"Calculer ${a}{c}$, arrondi au dixième."),
        "answer": f"${a}{c} \\approx {res}$ cm.",
        "hint": "Côté adjacent = hypoténuse × cosinus.",
        "steps": [f"$\\cos {ang}° = \\dfrac{{{a}{c}}}{{{grp(hyp)}}}$.",
                  f"${a}{c} = {grp(hyp)} \\times \\cos {ang}° \\approx {res}$ cm."],
        "notion": N3,
    }


def _gen_hypotenuse(rng: random.Random) -> Optional[dict]:
    a, b, c = _lettres(rng)
    adj = Fraction(rng.randint(20, 200), 10)
    ang = rng.randint(10, 75)
    res = _arrondi(float(adj) / _cos(ang), 1)
    if res is None:
        return None
    return {
        "enonce": (f"Le triangle ${a}{b}{c}$ est rectangle en ${c}$, ${a}{c} = {grp(adj)}$ cm et $\\widehat{{{b}{a}{c}}} = {ang}°$. "
                   f"Calculer ${a}{b}$, arrondi au dixième."),
        "answer": f"${a}{b} \\approx {res}$ cm.",
        "hint": "Hypoténuse = côté adjacent ÷ cosinus.",
        "steps": [f"$\\cos {ang}° = \\dfrac{{{grp(adj)}}}{{{a}{b}}}$.",
                  f"${a}{b} = \\dfrac{{{grp(adj)}}}{{\\cos {ang}°}} \\approx {res}$ cm."],
        "notion": N3,
    }


def _gen_angle(rng: random.Random) -> Optional[dict]:
    a, b, c = _lettres(rng)
    hyp = rng.randint(3, 30)
    adj = Fraction(rng.randint(5, hyp * 10 - 1), 10)
    d = rng.choice((0, 1))
    res = _arrondi(math.degrees(math.acos(float(adj) / hyp)), d)
    if res is None:
        return None
    precision = "au degré près" if d == 0 else "au dixième de degré"
    return {
        "enonce": (f"Le triangle ${a}{b}{c}$ est rectangle en ${c}$, ${a}{c} = {grp(adj)}$ cm et ${a}{b} = {hyp}$ cm. "
                   f"Calculer $\\widehat{{{b}{a}{c}}}$ {precision}."),
        "answer": f"$\\widehat{{{b}{a}{c}}} \\approx {res}°$.",
        "hint": "Calcule le cosinus, puis utilise la touche cos⁻¹.",
        "steps": [f"$\\cos \\widehat{{{b}{a}{c}}} = \\dfrac{{{grp(adj)}}}{{{hyp}}}$.",
                  f"Avec cos⁻¹ : $\\widehat{{{b}{a}{c}}} \\approx {res}°$."],
        "notion": N4,
    }


def _gen_echelle(rng: random.Random) -> Optional[dict]:
    longueur = Fraction(rng.randint(20, 80), 10)
    pied = Fraction(rng.randint(5, int(longueur * 10 * 0.6)), 10)
    res = _arrondi(math.degrees(math.acos(float(pied / longueur))), 0)
    if res is None:
        return None
    angle = math.degrees(math.acos(float(pied / longueur)))
    conforme = 65 <= angle <= 75
    return {
        "enonce": (f"Une échelle de ${grp(longueur)}$ m est appuyée contre un mur vertical ; son pied est posé sur le sol horizontal à "
                   f"${grp(pied)}$ m du mur. Quel angle fait-elle avec le sol, au degré près ? (On conseille un angle compris entre $65°$ et $75°$.)"),
        "answer": f"Environ ${res}°$ : " + ("l'angle est dans la plage conseillée." if conforme
                                            else "l'angle n'est pas dans la plage conseillée."),
        "hint": "L'échelle est l'hypoténuse ; la distance au mur est le côté adjacent à l'angle au sol.",
        "steps": [f"$\\cos \\alpha = \\dfrac{{{grp(pied)}}}{{{grp(longueur)}}}$.",
                  f"Avec cos⁻¹ : $\\alpha \\approx {res}°$.",
                  "L'angle est entre $65°$ et $75°$." if conforme else "L'angle n'est pas entre $65°$ et $75°$."],
        "notion": N4,
    }


FAMILIES_LIST = (
    Family("nommer_cotes", 1, "Nommer les côtés", N1, _gen_nommer,
           "un triangle rectangle", "hypoténuse en face de l'angle droit"),
    Family("angle_complementaire", 1, "Angles complémentaires", N1, _gen_complementaire,
           "un angle aigu", "somme 90°"),
    Family("calculer_cos", 1, "Calculer un cosinus", N2, _gen_calculer_cos,
           "deux longueurs", "adjacent / hypoténuse"),
    Family("cos_pythagore", 2, "Pythagore puis cosinus", N2, _gen_cos_pythagore,
           "deux côtés de l'angle droit", "triplets pythagoriciens"),
    Family("cote_adjacent", 2, "Calculer le côté adjacent", N3, _gen_adjacent,
           "hypoténuse et angle", "adjacent = hypoténuse × cos"),
    Family("hypotenuse_cos", 2, "Calculer l'hypoténuse", N3, _gen_hypotenuse,
           "côté adjacent et angle", "hypoténuse = adjacent ÷ cos"),
    Family("angle_depuis_cotes", 2, "Calculer un angle", N4, _gen_angle,
           "côté adjacent et hypoténuse", "touche cos⁻¹"),
    Family("probleme_echelle", 3, "Angle d'une échelle", N4, _gen_echelle,
           "une échelle contre un mur", "cos⁻¹ et interprétation"),
)

CHAPTER = Chapter(10, FAMILIES_LIST)
CHAPTER_ID = CHAPTER.chapter_id
FAMILIES = CHAPTER.families
GENERATED_ID_OFFSET = CHAPTER.id_offset
generate_one = CHAPTER.generate_one
generate_pool = CHAPTER.generate_pool
