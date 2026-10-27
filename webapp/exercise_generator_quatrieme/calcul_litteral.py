"""Chapitre 6 — Calcul littéral (générateurs). Distributivité simple uniquement.

    substituer           N1  calculer ax² + bx + c pour une valeur (éventuellement négative)
    traduire_programme   N1  programme de calcul en deux étapes -> expression
    reduire_somme        N2  ax + b + cx + d -> forme réduite
    reduire_parentheses  N2  ax + b ± (cx + d) -> forme réduite
    developper           N3  k(ax + b) -> kax + kb
    developper_reduire   N3  k(ax + b) + m(cx + d) -> forme réduite
    factoriser           N3  somme à facteur commun -> produit (plus grand facteur)
    tester_egalite       N4  ax + b = cx + d pour une valeur donnée ?
    programme_constant   N4  programme qui donne toujours le même nombre : le prouver
"""
import random
from math import gcd
from typing import Optional

from ._commun import Chapter, Family, par

N1 = "Expressions littérales : écrire, lire et calculer"
N2 = "Réduire une expression littérale"
N3 = "Développer et factoriser avec la distributivité simple"
N4 = "Prouver avec le calcul littéral"


def _terme(coef: int, lettre: str, premier: bool) -> str:
    """Un terme « coef·lettre » avec son signe ; lettre = '' pour un nombre seul."""
    if coef == 0:
        return ""
    signe = "-" if coef < 0 else ("" if premier else "+")
    a = abs(coef)
    corps = (lettre if a == 1 else f"{a}{lettre}") if lettre else str(a)
    return f"{signe}{corps}" if premier else f" {signe} {corps}"


def poly(*coefs) -> str:
    """poly(a, b) -> « ax + b » ; poly(a, b, c) -> « ax^2 + bx + c »."""
    lettres = ("x^2", "x", "")[-len(coefs):]
    out = ""
    for c, l in zip(coefs, lettres):
        out += _terme(c, l, premier=(out == ""))
    return out or "0"


def _par_terme(t: str) -> str:
    return f"({t})" if t.startswith("-") else t


def _nz(rng, lo, hi):
    while True:
        v = rng.randint(lo, hi)
        if v != 0:
            return v


def _gen_substituer(rng: random.Random) -> Optional[dict]:
    a, b, c = _nz(rng, -3, 4), _nz(rng, -7, 7), rng.randint(-9, 9)
    v = _nz(rng, -5, 5)
    r = a * v * v + b * v + c
    expr = poly(a, b, c)
    X = "\\times"
    detail = f"{par(a)} {X} {par(v)}^2 + {par(b)} {X} {par(v)} + {par(c)}"
    return {
        "enonce": f"Calculer $A = {expr}$ pour $x = {v}$.",
        "answer": f"$A = {r}$",
        "hint": "Remplace $x$ par sa valeur (entre parenthèses si elle est négative) et respecte les priorités.",
        "steps": [f"On remplace $x$ par ${par(v)}$ : $A = {detail}$.",
                  f"${par(v)}^2 = {v * v}$, donc $A = {a * v * v} + {par(b * v)} + {par(c)}$.",
                  f"$A = {r}$."],
        "notion": N1,
    }


def _gen_traduire(rng: random.Random) -> Optional[dict]:
    a, k = rng.randint(2, 12), rng.randint(2, 9)
    ordre = rng.choice(("add_puis_mult", "mult_puis_add", "sub_puis_mult", "mult_puis_sub"))
    if ordre == "add_puis_mult":
        texte = f"choisir un nombre $x$, lui ajouter ${a}$, puis multiplier le résultat par ${k}$"
        expr, val = f"{k}(x + {a})", k * (1 + a)
    elif ordre == "sub_puis_mult":
        texte = f"choisir un nombre $x$, lui soustraire ${a}$, puis multiplier le résultat par ${k}$"
        expr, val = f"{k}(x - {a})", k * (1 - a)
    elif ordre == "mult_puis_add":
        texte = f"choisir un nombre $x$, le multiplier par ${k}$, puis ajouter ${a}$ au résultat"
        expr, val = f"{k}x + {a}", k + a
    else:
        texte = f"choisir un nombre $x$, le multiplier par ${k}$, puis soustraire ${a}$ au résultat"
        expr, val = f"{k}x - {a}", k - a
    paren = "(" in expr
    return {
        "enonce": f"Écrire une expression en $x$ qui traduit le programme : « {texte} ». Contrôler avec $x = 1$.",
        "answer": f"${expr}$ (pour $x = 1$, on obtient ${val}$)",
        "hint": "Si l'on multiplie « le résultat », l'opération précédente se met entre parenthèses.",
        "steps": [("La première opération porte sur $x$, puis on multiplie le résultat entier : il faut des parenthèses."
                   if paren else "On multiplie d'abord $x$, puis on ajoute ou soustrait : pas de parenthèses."),
                  f"Expression : ${expr}$.",
                  f"Contrôle pour $x = 1$ : ${val}$."],
        "notion": N1,
    }


def _gen_reduire_somme(rng: random.Random) -> Optional[dict]:
    a, c = _nz(rng, -9, 12), _nz(rng, -9, 9)
    b, d = _nz(rng, -15, 15), _nz(rng, -15, 15)
    depart = f"{poly(a, b)}{_terme(c, 'x', False)}{_terme(d, '', False)}"
    return {
        "enonce": f"Réduire $B = {depart}$.",
        "answer": f"$B = {poly(a + c, b + d)}$",
        "hint": "Regroupe les termes en $x$, puis les nombres.",
        "steps": [f"Termes en $x$ : ${poly(a, 0)}{_terme(c, 'x', False)} = {poly(a + c, 0)}$.",
                  f"Nombres : ${b}{_terme(d, '', False)} = {b + d}$.",
                  f"$B = {poly(a + c, b + d)}$."],
        "notion": N2,
    }


def _gen_reduire_parentheses(rng: random.Random) -> Optional[dict]:
    a, b, c, d = _nz(rng, -8, 9), _nz(rng, -12, 12), _nz(rng, -8, 8), _nz(rng, -12, 12)
    s = rng.choice((1, -1, -1))
    depart = f"{poly(a, b)} {'+' if s > 0 else '-'} ({poly(c, d)})"
    sans = f"{poly(a, b)}{_terme(s * c, 'x', False)}{_terme(s * d, '', False)}"
    return {
        "enonce": f"Supprimer les parenthèses puis réduire $C = {depart}$.",
        "answer": f"$C = {poly(a + s * c, b + s * d)}$",
        "hint": "Un signe $-$ devant une parenthèse change le signe de chacun de ses termes.",
        "steps": [("Parenthèse précédée de $-$ : on change le signe de chaque terme." if s < 0
                   else "Parenthèse précédée de $+$ : on la supprime sans rien changer."),
                  f"$C = {sans}$.",
                  f"$C = {poly(a + s * c, b + s * d)}$."],
        "notion": N2,
    }


def _gen_developper(rng: random.Random) -> Optional[dict]:
    k, a, b = _nz(rng, -9, 9), _nz(rng, -6, 7), _nz(rng, -12, 12)
    if k in (1, -1):
        return None
    fk = f"-{abs(k)}" if k < 0 else str(k)
    return {
        "enonce": f"Développer $D = {fk}({poly(a, b)})$.",
        "answer": f"$D = {poly(k * a, k * b)}$",
        "hint": "Le facteur multiplie chaque terme de la parenthèse ; applique la règle des signes.",
        "steps": [f"$D = {par(k)} \\times {_par_terme(poly(a, 0))} + {par(k)} \\times {par(b)}$.",
                  f"$D = {poly(k * a, k * b)}$."],
        "notion": N3,
    }


def _gen_developper_reduire(rng: random.Random) -> Optional[dict]:
    k, m = rng.randint(2, 7), _nz(rng, -6, 6)
    a, b, c, d = _nz(rng, 1, 5), _nz(rng, -9, 9), _nz(rng, 1, 5), _nz(rng, -9, 9)
    if m == 1:
        return None
    signe = "-" if m < 0 else "+"
    depart = f"{k}({poly(a, b)}) {signe} {abs(m)}({poly(c, d)})"
    p1, p2 = poly(k * a, k * b), poly(m * c, m * d)
    res = poly(k * a + m * c, k * b + m * d)
    return {
        "enonce": f"Développer et réduire $E = {depart}$.",
        "answer": f"$E = {res}$",
        "hint": "Développe chaque produit (avec son signe), puis regroupe les termes semblables.",
        "steps": [f"${k}({poly(a, b)}) = {p1}$.",
                  f"${'-' if m < 0 else ''}{abs(m)}({poly(c, d)}) = {p2}$.",
                  f"$E = {p1} {'- ' + p2[1:] if p2.startswith('-') else '+ ' + p2}$ puis on réduit : $E = {res}$."],
        "notion": N3,
    }


def _gen_factoriser(rng: random.Random) -> Optional[dict]:
    k = rng.randint(2, 9)
    a, b = _nz(rng, 1, 7), _nz(rng, -9, 9)
    if gcd(a, abs(b)) != 1:
        return None
    lettre = rng.random() < 0.3
    if lettre:
        # k·a·x² + k·b·x = kx(ax + b)
        somme, prod = poly(k * a, k * b, 0), f"{k}x({poly(a, b)})"
        facteur = f"{k}x"
    else:
        somme, prod = poly(k * a, k * b), f"{k}({poly(a, b)})"
        facteur = str(k)
    return {
        "enonce": f"Factoriser $F = {somme}$ en mettant en facteur le plus grand facteur commun possible.",
        "answer": f"$F = {prod}$",
        "hint": "Cherche le plus grand diviseur commun des coefficients" + (" et la lettre commune." if lettre else "."),
        "steps": [f"Chaque terme est un multiple de ${facteur}$.",
                  f"$F = {prod}$ ; contrôle en redéveloppant : ${somme}$."],
        "notion": N3,
    }


def _gen_tester(rng: random.Random) -> Optional[dict]:
    a, c = _nz(rng, -6, 7), _nz(rng, -6, 7)
    if a == c:
        return None
    v = _nz(rng, -5, 6)
    b = rng.randint(-12, 12)
    if rng.random() < 0.5:
        d = a * v + b - c * v          # égalité vraie pour v
    else:
        d = rng.randint(-12, 12)
    g, dr = a * v + b, c * v + d
    vrai = g == dr
    return {
        "enonce": f"L'égalité ${poly(a, b)} = {poly(c, d)}$ est-elle vraie pour $x = {v}$ ?",
        "answer": (f"Oui : les deux membres valent ${g}$." if vrai
                   else f"Non : le membre de gauche vaut ${g}$ et celui de droite ${dr}$."),
        "hint": "Calcule séparément chaque membre pour la valeur donnée.",
        "steps": [f"Membre de gauche : ${g}$.", f"Membre de droite : ${dr}$.",
                  "Les deux membres sont égaux : l'égalité est vraie." if vrai else "Les deux membres sont différents : l'égalité est fausse."],
        "notion": N4,
    }


def _gen_programme_constant(rng: random.Random) -> Optional[dict]:
    k, a = rng.randint(2, 9), rng.randint(2, 12)
    return {
        "enonce": (f"Programme : « choisir un nombre, le multiplier par ${k}$, ajouter ${k * a}$, diviser le résultat par ${k}$, "
                   "puis soustraire le nombre choisi ». Démontrer que ce programme donne toujours le même résultat, et donner ce résultat."),
        "answer": f"Le résultat est toujours ${a}$.",
        "hint": f"Applique le programme à $x$ et factorise par ${k}$ avant de diviser.",
        "steps": [f"Avec $x$ : ${k}x + {k * a} = {k}(x + {a})$.",
                  f"Division par ${k}$ : $x + {a}$.",
                  f"On soustrait $x$ : $x + {a} - x = {a}$, quel que soit $x$."],
        "notion": N4,
    }


FAMILIES_LIST = (
    Family("substituer", 1, "Calculer une expression pour une valeur", N1, _gen_substituer,
           "une expression du second degré", "remplacer et respecter les priorités"),
    Family("traduire_programme", 2, "Traduire un programme de calcul", N1, _gen_traduire,
           "un programme en deux étapes", "parenthèses pour « le résultat »"),
    Family("reduire_somme", 1, "Réduire une somme", N2, _gen_reduire_somme,
           "quatre termes", "regrouper les termes semblables"),
    Family("reduire_parentheses", 2, "Supprimer des parenthèses et réduire", N2, _gen_reduire_parentheses,
           "une parenthèse précédée de + ou de -", "changer les signes"),
    Family("developper", 1, "Développer un produit", N3, _gen_developper,
           "un produit k(ax + b)", "distributivité simple"),
    Family("developper_reduire", 2, "Développer et réduire", N3, _gen_developper_reduire,
           "deux produits", "développer puis regrouper"),
    Family("factoriser", 2, "Factoriser", N3, _gen_factoriser,
           "une somme à facteur commun", "plus grand facteur commun"),
    Family("tester_egalite", 1, "Tester une égalité", N4, _gen_tester,
           "une égalité du premier degré", "calculer chaque membre"),
    Family("programme_constant", 3, "Prouver un programme de calcul", N4, _gen_programme_constant,
           "un programme de calcul", "factoriser avant de diviser"),
)

CHAPTER = Chapter(6, FAMILIES_LIST)
CHAPTER_ID = CHAPTER.chapter_id
FAMILIES = CHAPTER.families
GENERATED_ID_OFFSET = CHAPTER.id_offset
generate_one = CHAPTER.generate_one
generate_pool = CHAPTER.generate_pool
