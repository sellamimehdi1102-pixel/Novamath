"""Chapitre 2 — Fractions : comparer, additionner, soustraire (générateurs).

    simplifier          N1  fraction (éventuellement négative) -> irréductible
    completer_egalite   N1  a/b = ?/d ou a/b = c/?
    comparer_deux       N2  comparer deux fractions (signes, dénominateurs)
    encadrer            N2  encadrer une fraction entre deux entiers consécutifs
    ranger_trois        N2  ranger trois nombres dans l'ordre croissant
    somme_multiple      N3  a/b ± c/d, d multiple de b
    somme_quelconque    N3  a/b ± c/d quelconques, relatifs
    part_restante       N4  1 − (somme de parts d'un tout), en contexte
"""
import random
from fractions import Fraction as Fr
from math import gcd
from typing import Optional

from ._commun import Chapter, Family, frac

N1 = "Quotients égaux et simplification"
N2 = "Comparer et ranger des nombres en écriture fractionnaire"
N3 = "Additionner et soustraire des fractions"
N4 = "Résoudre des problèmes avec des sommes de fractions"


def _lcm(a, b):
    return a * b // gcd(a, b)


def _sym(x, y):
    return "<" if x < y else (">" if x > y else "=")


def _gen_simplifier(rng: random.Random) -> Optional[dict]:
    n, d = rng.randint(1, 12), rng.randint(2, 15)
    if gcd(n, d) != 1 or n == d:
        return None
    k = rng.randint(2, 12)
    sn, sd = rng.choice(((1, 1), (-1, 1), (1, -1), (-1, -1)))
    top, bottom = sn * n * k, sd * d * k
    value = Fr(top, bottom)
    signe = "positif" if value > 0 else "négatif"
    return {
        "enonce": f"Simplifier $\\dfrac{{{top}}}{{{bottom}}}$ et donner le résultat sous forme irréductible.",
        "answer": f"$\\dfrac{{{top}}}{{{bottom}}} = {frac(value)}$",
        "hint": "Règle d'abord le signe, puis divise le numérateur et le dénominateur par leur plus grand diviseur commun.",
        "steps": [f"Signe : le quotient est {signe}.",
                  f"${abs(top)}$ et ${abs(bottom)}$ sont divisibles par ${k}$ : $\\dfrac{{{abs(top)}}}{{{abs(bottom)}}} = \\dfrac{{{n}}}{{{d}}}$.",
                  f"${n}$ et ${d}$ n'ont pas d'autre diviseur commun que $1$ : ${frac(value)}$ est irréductible."],
        "notion": N1,
    }


def _gen_completer_egalite(rng: random.Random) -> Optional[dict]:
    n, d = rng.randint(1, 11), rng.randint(2, 13)
    if gcd(n, d) != 1:
        return None
    k = rng.randint(2, 9)
    if rng.random() < 0.6:
        enonce = f"Compléter : $\\dfrac{{{n}}}{{{d}}} = \\dfrac{{\\ldots}}{{{d * k}}}$."
        steps = [f"$ {d} \\times {k} = {d * k}$ : le dénominateur a été multiplié par ${k}$.",
                 f"On multiplie aussi le numérateur par ${k}$ : ${n} \\times {k} = {n * k}$."]
    else:
        enonce = f"Compléter : $\\dfrac{{{n}}}{{{d}}} = \\dfrac{{{n * k}}}{{\\ldots}}$."
        steps = [f"${n} \\times {k} = {n * k}$ : le numérateur a été multiplié par ${k}$.",
                 f"On multiplie aussi le dénominateur par ${k}$ : ${d} \\times {k} = {d * k}$."]
    return {
        "enonce": enonce,
        "answer": f"$\\dfrac{{{n}}}{{{d}}} = \\dfrac{{{n * k}}}{{{d * k}}}$",
        "hint": "Cherche par quel nombre on a multiplié le terme connu, puis multiplie l'autre terme par le même nombre.",
        "steps": steps + [f"$\\dfrac{{{n}}}{{{d}}} = \\dfrac{{{n * k}}}{{{d * k}}}$."],
        "notion": N1,
    }


def _rand_frac(rng, max_den=12, allow_neg=True):
    d = rng.randint(2, max_den)
    n = rng.randint(1, 2 * d)
    f = Fr(n, d)
    if allow_neg and rng.random() < 0.4:
        f = -f
    return f


def _gen_comparer_deux(rng: random.Random) -> Optional[dict]:
    a, b = _rand_frac(rng), _rand_frac(rng)
    if a.denominator == 1 or b.denominator == 1:
        return None  # « comparer deux fractions » : jamais un entier déguisé
    if a == b or a.denominator == b.denominator or (a > 0) != (b > 0) and rng.random() < 0.7:
        return None
    m = _lcm(a.denominator, b.denominator)
    if m > 120:
        return None
    na, nb = a.numerator * (m // a.denominator), b.numerator * (m // b.denominator)
    s = _sym(a, b)
    return {
        "enonce": f"Comparer ${frac(a)}$ et ${frac(b)}$.",
        "answer": f"${frac(a)} {s} {frac(b)}$",
        "hint": "Écris les deux nombres avec un même dénominateur positif, puis compare les numérateurs.",
        "steps": [f"Dénominateur commun : ${m}$.",
                  f"${frac(a)} = \\dfrac{{{na}}}{{{m}}}$ et ${frac(b)} = \\dfrac{{{nb}}}{{{m}}}$.",
                  f"${na} {s} {nb}$, donc ${frac(a)} {s} {frac(b)}$."],
        "notion": N2,
    }


def _gen_encadrer(rng: random.Random) -> Optional[dict]:
    d = rng.randint(2, 12)
    n = rng.randint(d + 1, 12 * d)
    if n % d == 0:
        return None
    q, r = divmod(n, d)
    if rng.random() < 0.5:
        return {
            "enonce": f"Encadrer $\\dfrac{{{n}}}{{{d}}}$ entre deux entiers consécutifs.",
            "answer": f"${q} < \\dfrac{{{n}}}{{{d}}} < {q + 1}$",
            "hint": "Effectue la division euclidienne du numérateur par le dénominateur.",
            "steps": [f"${n} = {d} \\times {q} + {r}$, donc $\\dfrac{{{n}}}{{{d}}} = {q} + \\dfrac{{{r}}}{{{d}}}$.",
                      f"$0 < \\dfrac{{{r}}}{{{d}}} < 1$, donc ${q} < \\dfrac{{{n}}}{{{d}}} < {q + 1}$."],
            "notion": N2,
        }
    return {
        "enonce": f"Encadrer $-\\dfrac{{{n}}}{{{d}}}$ entre deux entiers consécutifs.",
        "answer": f"${-(q + 1)} < -\\dfrac{{{n}}}{{{d}}} < {-q}$",
        "hint": "Encadre d'abord la distance à zéro, puis prends les opposés en inversant l'ordre.",
        "steps": [f"${n} = {d} \\times {q} + {r}$, donc ${q} < \\dfrac{{{n}}}{{{d}}} < {q + 1}$.",
                  f"En prenant les opposés, l'ordre s'inverse : ${-(q + 1)} < -\\dfrac{{{n}}}{{{d}}} < {-q}$."],
        "notion": N2,
    }


def _gen_ranger_trois(rng: random.Random) -> Optional[dict]:
    m = rng.choice((6, 8, 10, 12, 15, 18, 20, 24))
    dens = [d for d in range(2, m + 1) if m % d == 0]
    vals = []
    for _ in range(3):
        d = rng.choice(dens)
        n = rng.randint(-2 * d, 2 * d)
        if n == 0:
            return None
        vals.append(Fr(n, d))
    if any(v.denominator == 1 for v in vals) or len(set(vals)) < 3 or len({v.denominator for v in vals}) < 2:
        return None
    ordre = sorted(vals)
    ecrit = " ; ".join(f"${frac(v)}$" for v in vals)
    converti = " ; ".join(f"${frac(v)}$" if v.denominator == m else f"${frac(v)} = \\dfrac{{{v.numerator * (m // v.denominator)}}}{{{m}}}$"
                          for v in vals)
    negatifs = " (les négatifs d'abord)" if any(v < 0 for v in vals) else ""
    return {
        "enonce": f"Ranger dans l'ordre croissant : {ecrit}.",
        "answer": "$" + " < ".join(frac(v) for v in ordre) + "$",
        "hint": f"Écris les trois nombres avec le dénominateur ${m}$.",
        "steps": [f"Dénominateur commun ${m}$ : {converti}.",
                  f"On range les numérateurs dans l'ordre croissant{negatifs}.",
                  "Ordre : $" + " < ".join(frac(v) for v in ordre) + "$."],
        "notion": N2,
    }


def _gen_somme_multiple(rng: random.Random) -> Optional[dict]:
    b = rng.randint(2, 9)
    k = rng.randint(2, 5)
    d = b * k
    a = rng.randint(1, 2 * b)
    c = rng.randint(1, 2 * d)
    op = rng.choice(("+", "-"))
    if gcd(a, b) != 1 or gcd(c, d) != 1:
        return None
    res = Fr(a, b) + Fr(c, d) if op == "+" else Fr(a, b) - Fr(c, d)
    num_res = a * k + c if op == "+" else a * k - c
    return {
        "enonce": f"Calculer $\\dfrac{{{a}}}{{{b}}} {op} \\dfrac{{{c}}}{{{d}}}$.",
        "answer": f"$\\dfrac{{{a}}}{{{b}}} {op} \\dfrac{{{c}}}{{{d}}} = {frac(res)}$",
        "hint": f"${d}$ est un multiple de ${b}$ : écris la première fraction avec le dénominateur ${d}$.",
        "steps": [f"$\\dfrac{{{a}}}{{{b}}} = \\dfrac{{{a * k}}}{{{d}}}$.",
                  f"$\\dfrac{{{a * k}}}{{{d}}} {op} \\dfrac{{{c}}}{{{d}}} = \\dfrac{{{num_res}}}{{{d}}}$.",
                  f"Forme irréductible : ${frac(res)}$."],
        "notion": N3,
    }


def _gen_somme_quelconque(rng: random.Random) -> Optional[dict]:
    b, d = rng.randint(2, 9), rng.randint(2, 9)
    if b == d or b % d == 0 or d % b == 0:
        return None
    a = rng.randint(-2 * b, 2 * b)
    c = rng.randint(1, 2 * d)
    if a == 0 or gcd(abs(a), b) != 1 or gcd(c, d) != 1:
        return None
    op = rng.choice(("+", "-"))
    m = _lcm(b, d)
    na, nc = a * (m // b), c * (m // d)
    res = Fr(a, b) + Fr(c, d) if op == "+" else Fr(a, b) - Fr(c, d)
    first = frac(Fr(a, b))
    return {
        "enonce": f"Calculer ${first} {op} \\dfrac{{{c}}}{{{d}}}$.",
        "answer": f"${first} {op} \\dfrac{{{c}}}{{{d}}} = {frac(res)}$",
        "hint": f"Cherche un multiple commun de ${b}$ et de ${d}$.",
        "steps": [f"Dénominateur commun : ${m}$.",
                  f"${first} = \\dfrac{{{na}}}{{{m}}}$ et $\\dfrac{{{c}}}{{{d}}} = \\dfrac{{{nc}}}{{{m}}}$.",
                  f"$\\dfrac{{{na} {op} {nc}}}{{{m}}} = {frac(res)}$."],
        "notion": N3,
    }


_CONTEXTES = (
    ("Dans un club, {p} des adhérents font du tennis et {q} de la natation ; les autres font de l'escalade.",
     "Quelle fraction des adhérents fait de l'escalade ?", "des adhérents fait de l'escalade"),
    ("Un terrain est planté : {p} en légumes, {q} en fleurs, et le reste en gazon.",
     "Quelle fraction du terrain est en gazon ?", "du terrain est en gazon"),
    ("Sur son salaire, Lou consacre {p} au loyer et {q} aux courses.",
     "Quelle fraction de son salaire lui reste-t-il ?", "du salaire reste"),
    ("Un sac de billes contient {p} de billes rouges et {q} de billes bleues ; les autres sont vertes.",
     "Quelle fraction des billes est verte ?", "des billes est verte"),
)


def _gen_part_restante(rng: random.Random) -> Optional[dict]:
    p, q = Fr(rng.randint(1, 5), rng.randint(2, 8)), Fr(rng.randint(1, 5), rng.randint(2, 8))
    if p.denominator == q.denominator or p + q >= 1 or p.numerator >= p.denominator or q.numerator >= q.denominator:
        return None
    m = _lcm(p.denominator, q.denominator)
    reste = 1 - p - q
    debut, question, fin = rng.choice(_CONTEXTES)
    np_, nq = p.numerator * (m // p.denominator), q.numerator * (m // q.denominator)
    return {
        "enonce": debut.format(p=f"${frac(p)}$", q=f"${frac(q)}$") + " " + question,
        "answer": f"${frac(reste)}$ {fin}.",
        "hint": "Le tout correspond à $1$ : retire à $1$ la somme des parts connues.",
        "steps": [f"Parts connues : ${frac(p)} + {frac(q)} = \\dfrac{{{np_}}}{{{m}}} + \\dfrac{{{nq}}}{{{m}}} = \\dfrac{{{np_ + nq}}}{{{m}}}$.",
                  f"Part restante : $1 - \\dfrac{{{np_ + nq}}}{{{m}}} = \\dfrac{{{m - np_ - nq}}}{{{m}}}$.",
                  f"Forme irréductible : ${frac(reste)}$."],
        "notion": N4,
    }


FAMILIES_LIST = (
    Family("simplifier", 1, "Simplifier une fraction", N1, _gen_simplifier,
           "une fraction à simplifier", "diviser par le plus grand diviseur commun"),
    Family("completer_egalite", 1, "Compléter une égalité de fractions", N1, _gen_completer_egalite,
           "deux fractions égales à compléter", "même facteur en haut et en bas"),
    Family("comparer_deux", 2, "Comparer deux fractions", N2, _gen_comparer_deux,
           "deux fractions de dénominateurs différents", "mettre au même dénominateur"),
    Family("encadrer", 2, "Encadrer une fraction", N2, _gen_encadrer,
           "une fraction supérieure à 1", "division euclidienne"),
    Family("ranger_trois", 3, "Ranger trois fractions", N2, _gen_ranger_trois,
           "trois nombres positifs ou négatifs", "dénominateur commun"),
    Family("somme_multiple", 2, "Somme : dénominateurs multiples", N3, _gen_somme_multiple,
           "un dénominateur multiple de l'autre", "convertir la première fraction"),
    Family("somme_quelconque", 3, "Somme : dénominateurs quelconques", N3, _gen_somme_quelconque,
           "deux dénominateurs quelconques", "multiple commun"),
    Family("part_restante", 3, "Part restante d'un tout", N4, _gen_part_restante,
           "deux parts d'un tout", "le tout vaut 1"),
)

CHAPTER = Chapter(2, FAMILIES_LIST)
CHAPTER_ID = CHAPTER.chapter_id
FAMILIES = CHAPTER.families
GENERATED_ID_OFFSET = CHAPTER.id_offset
generate_one = CHAPTER.generate_one
generate_pool = CHAPTER.generate_pool
