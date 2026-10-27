"""Chapitre 3 — Fractions : multiplier et diviser (générateurs).

    produit_fractions   N1  produit de deux fractions (signes), irréductible
    fraction_quantite   N1  les a/b d'une quantité entière, en contexte
    inverse_nombre      N2  inverse d'une fraction ou d'un entier relatif
    quotient_fractions  N2  a/b ÷ c/d
    combien_de_fois     N2  combien de récipients de a/b dans une quantité
    priorites_fractions N3  a/b ± c/d × e/f (priorités)
    fraction_du_reste   N3  part p, puis q du reste : fraction restante
    retrouver_tout      N3  tout retrouvé à partir de la part restante
"""
import random
from fractions import Fraction as Fr
from math import gcd
from typing import Optional

from ._commun import Chapter, Family, frac

N1 = "Multiplier des fractions"
N2 = "Inverse et division de fractions"
N3 = "Enchaîner les opérations et résoudre des problèmes"


def _f(rng, max_den=9, signed=True, proper=False):
    d = rng.randint(2, max_den)
    n = rng.randint(1, d - 1 if proper else 2 * d)
    v = Fr(n, d)
    if v.denominator == 1:
        return None
    return -v if signed and rng.random() < 0.35 else v


def _gen_produit_fractions(rng: random.Random) -> Optional[dict]:
    a, b = _f(rng), _f(rng)
    if a is None or b is None:
        return None
    p = a * b
    signe = "positif" if p > 0 else "négatif"
    return {
        "enonce": f"Calculer ${frac(a)} \\times {frac(b) if b > 0 else '(' + frac(b) + ')'}$ et donner le résultat sous forme irréductible.",
        "answer": f"Le produit vaut ${frac(p)}$.",
        "hint": "Multiplie les numérateurs entre eux et les dénominateurs entre eux, en simplifiant avant de calculer.",
        "steps": [f"Signe : le produit est {signe}.",
                  f"$\\dfrac{{{abs(a.numerator)} \\times {abs(b.numerator)}}}{{{a.denominator} \\times {b.denominator}}} = \\dfrac{{{abs(a.numerator * b.numerator)}}}{{{a.denominator * b.denominator}}}$.",
                  f"Forme irréductible : ${frac(p)}$."],
        "notion": N1,
    }


_QUANTITES = (
    ("Un pull coûte {Q} €. Il est vendu aux {p} de son prix pendant les soldes. Quel est son nouveau prix ?", "€", "Le nouveau prix est de"),
    ("Un terrain de {Q} m² est cultivé aux {p}. Quelle surface est cultivée ?", "m²", "La surface cultivée est de"),
    ("Une classe de {Q} élèves compte les {p} de demi-pensionnaires. Combien y a-t-il de demi-pensionnaires ?", "élèves", "Il y a"),
    ("Un réservoir de {Q} L est rempli aux {p}. Combien contient-il de litres ?", "L", "Il contient"),
)


def _gen_fraction_quantite(rng: random.Random) -> Optional[dict]:
    d = rng.randint(2, 9)
    n = rng.randint(1, d - 1)
    if gcd(n, d) != 1:
        return None
    Q = d * rng.randint(2, 30)
    texte, unite, debut = rng.choice(_QUANTITES)
    if unite == "élèves" and Q > 36:
        return None
    res = Fr(n, d) * Q
    return {
        "enonce": texte.format(Q=f"${Q}$", p=f"$\\dfrac{{{n}}}{{{d}}}$"),
        "answer": f"{debut} ${res}$ {unite}.",
        "hint": "Divise la quantité par le dénominateur, puis multiplie par le numérateur.",
        "steps": [f"Les $\\dfrac{{{n}}}{{{d}}}$ de ${Q}$ : $\\dfrac{{{n}}}{{{d}}} \\times {Q}$.",
                  f"${Q} \\div {d} = {Q // d}$, puis ${n} \\times {Q // d} = {res}$."],
        "notion": N1,
    }


def _gen_inverse_nombre(rng: random.Random) -> Optional[dict]:
    if rng.random() < 0.3:
        v = Fr(rng.choice((-1, 1)) * rng.randint(2, 15))
    else:
        v = _f(rng, 12)
        if v is None:
            return None
    inv = 1 / v
    return {
        "enonce": f"Donner l'inverse de ${frac(v)}$.",
        "answer": f"L'inverse de ${frac(v)}$ est ${frac(inv)}$.",
        "hint": "Un nombre et son inverse ont pour produit $1$ ; ils ont le même signe.",
        "steps": [f"On cherche le nombre qui, multiplié par ${frac(v)}$, donne $1$.",
                  f"${frac(v)} \\times {frac(inv) if inv > 0 else '(' + frac(inv) + ')'} = 1$ : l'inverse est ${frac(inv)}$."],
        "notion": N2,
    }


def _gen_quotient_fractions(rng: random.Random) -> Optional[dict]:
    a, b = _f(rng), _f(rng)
    if a is None or b is None:
        return None
    q = a / b
    inv = 1 / b
    eb = frac(b) if b > 0 else "(" + frac(b) + ")"
    ei = frac(inv) if inv > 0 else "(" + frac(inv) + ")"
    return {
        "enonce": f"Calculer ${frac(a)} \\div {eb}$.",
        "answer": f"${frac(a)} \\div {eb} = {frac(q)}$",
        "hint": "Diviser par une fraction, c'est multiplier par son inverse.",
        "steps": [f"L'inverse de ${frac(b)}$ est ${frac(inv)}$.",
                  f"${frac(a)} \\div {eb} = {frac(a)} \\times {ei}$.",
                  f"Résultat irréductible : ${frac(q)}$."],
        "notion": N2,
    }


_RECIPIENTS = (
    ("Combien de bouteilles de {p} L peut-on remplir avec {Q} L de jus ?", "bouteilles"),
    ("Une ficelle de {Q} m est coupée en morceaux de {p} m. Combien obtient-on de morceaux ?", "morceaux"),
    ("Combien de parts de {p} kg peut-on faire avec {Q} kg de pâte ?", "parts"),
)


def _gen_combien_de_fois(rng: random.Random) -> Optional[dict]:
    d = rng.randint(2, 8)
    n = rng.randint(1, d + 2)
    p = Fr(n, d)
    if p.denominator == 1:
        return None
    k = rng.randint(4, 40)
    Q = p * k
    if Q.denominator != 1:
        return None
    texte, objet = rng.choice(_RECIPIENTS)
    return {
        "enonce": texte.format(p=f"${frac(p)}$", Q=f"${Q.numerator}$"),
        "answer": f"On obtient ${k}$ {objet}.",
        "hint": "« Combien de fois … dans … ? » se traduit par une division.",
        "steps": [f"${Q.numerator} \\div {frac(p)} = {Q.numerator} \\times {frac(1 / p)}$.",
                  f"${Q.numerator} \\times {frac(1 / p)} = {k}$."],
        "notion": N2,
    }


def _gen_priorites_fractions(rng: random.Random) -> Optional[dict]:
    a, b, c = _f(rng, 8, proper=True), _f(rng, 8, signed=False), _f(rng, 8, signed=False)
    if a is None or b is None or c is None:
        return None
    op = rng.choice(("+", "-"))
    pr = b * c
    res = a + pr if op == "+" else a - pr
    return {
        "enonce": f"Calculer $A = {frac(a)} {op} {frac(b)} \\times {frac(c)}$.",
        "answer": f"$A = {frac(res)}$",
        "hint": "La multiplication est prioritaire sur l'addition et la soustraction.",
        "steps": [f"Multiplication : ${frac(b)} \\times {frac(c)} = {frac(pr)}$.",
                  f"$A = {frac(a)} {op} {frac(pr)} = {frac(res)}$."],
        "notion": N3,
    }


def _gen_fraction_du_reste(rng: random.Random) -> Optional[dict]:
    p = _f(rng, 8, signed=False, proper=True)
    q = _f(rng, 8, signed=False, proper=True)
    if p is None or q is None:
        return None
    reste1 = 1 - p
    part2 = q * reste1
    final = reste1 - part2
    return {
        "enonce": (f"Lou dépense ${frac(p)}$ de son argent de poche pour un livre, puis ${frac(q)}$ de ce qui lui reste "
                   "pour une place de cinéma. Quelle fraction de son argent de poche lui reste-t-il ?"),
        "answer": f"Il lui reste ${frac(final)}$ de son argent de poche.",
        "hint": "La seconde fraction porte sur ce qui reste, pas sur la somme de départ.",
        "steps": [f"Après le livre, il reste $1 - {frac(p)} = {frac(reste1)}$.",
                  f"Cinéma : ${frac(q)} \\times {frac(reste1)} = {frac(part2)}$ de l'argent de départ.",
                  f"Reste final : ${frac(reste1)} - {frac(part2)} = {frac(final)}$."],
        "notion": N3,
    }


def _gen_retrouver_tout(rng: random.Random) -> Optional[dict]:
    p = _f(rng, 6, signed=False, proper=True)
    q = _f(rng, 6, signed=False, proper=True)
    if p is None or q is None:
        return None
    final = (1 - p) * (1 - q)
    total = rng.randint(2, 40) * final.denominator
    reste = final * total
    if reste.denominator != 1 or total > 600:
        return None
    return {
        "enonce": (f"Un randonneur parcourt ${frac(p)}$ d'un trajet le matin, puis ${frac(q)}$ du reste l'après-midi. "
                   f"Il lui reste alors ${reste.numerator}$ km à parcourir. Quelle est la longueur du trajet ?"),
        "answer": f"Le trajet mesure ${total}$ km.",
        "hint": "Calcule la fraction du trajet qui reste, puis divise la distance restante par cette fraction.",
        "steps": [f"Après le matin, il reste $1 - {frac(p)} = {frac(1 - p)}$ du trajet.",
                  f"L'après-midi, il en parcourt ${frac(q)}$ : il reste ${frac(1 - q)} \\times {frac(1 - p)} = {frac(final)}$ du trajet.",
                  f"Longueur : ${reste.numerator} \\div {frac(final)} = {total}$ km."],
        "notion": N3,
    }


FAMILIES_LIST = (
    Family("produit_fractions", 1, "Produit de deux fractions", N1, _gen_produit_fractions,
           "deux fractions, éventuellement négatives", "haut fois haut, bas fois bas"),
    Family("fraction_quantite", 2, "Fraction d'une quantité", N1, _gen_fraction_quantite,
           "une quantité en contexte", "diviser par le dénominateur puis multiplier"),
    Family("inverse_nombre", 1, "Inverse d'un nombre", N2, _gen_inverse_nombre,
           "une fraction ou un entier relatif", "retourner la fraction, même signe"),
    Family("quotient_fractions", 2, "Quotient de deux fractions", N2, _gen_quotient_fractions,
           "deux fractions", "multiplier par l'inverse"),
    Family("combien_de_fois", 3, "Combien de fois une fraction dans une quantité", N2, _gen_combien_de_fois,
           "des récipients ou des morceaux", "division par une fraction"),
    Family("priorites_fractions", 3, "Priorités avec des fractions", N3, _gen_priorites_fractions,
           "une somme et un produit", "multiplication d'abord"),
    Family("fraction_du_reste", 3, "Fraction du reste", N3, _gen_fraction_du_reste,
           "deux dépenses successives", "la seconde porte sur le reste"),
    Family("retrouver_tout", 4, "Retrouver le tout", N3, _gen_retrouver_tout,
           "une distance restante connue", "diviser par la fraction restante"),
)

CHAPTER = Chapter(3, FAMILIES_LIST)
CHAPTER_ID = CHAPTER.chapter_id
FAMILIES = CHAPTER.families
GENERATED_ID_OFFSET = CHAPTER.id_offset
generate_one = CHAPTER.generate_one
generate_pool = CHAPTER.generate_pool
