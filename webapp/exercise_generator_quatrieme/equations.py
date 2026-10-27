"""Chapitre 7 — Équations (générateurs).

    tester_solution        N1  v est-il solution de ax + b = cx + d ?
    resoudre_simple        N2  ax + b = c, solution entière
    resoudre_fraction      N2  ax + b = c, solution fractionnaire (irréductible)
    resoudre_deux_membres  N3  ax + b = cx + d
    resoudre_parentheses   N3  k(x + m) = cx + d
    probleme_nombre        N4  « je pense à un nombre… »
    probleme_tarifs        N4  deux tarifs qui coûtent le même prix
    probleme_perimetre     N4  carré et triangle équilatéral de même périmètre
    probleme_ages          N4  dans combien d'années l'âge du père sera k fois celui du fils
"""
import random
from fractions import Fraction
from typing import Optional

from ._commun import Chapter, Family, frac, par

N1 = "Équations : vocabulaire et test d'une solution"
N2 = "Résoudre une équation du type ax + b = c"
N3 = "Équations avec l'inconnue dans les deux membres"
N4 = "Mettre un problème en équation"


def _terme(coef: int, lettre: str, premier: bool) -> str:
    if coef == 0:
        return ""
    signe = "-" if coef < 0 else ("" if premier else "+")
    a = abs(coef)
    corps = (lettre if a == 1 else f"{a}{lettre}") if lettre else str(a)
    return f"{signe}{corps}" if premier else f" {signe} {corps}"


def lin(a: int, b: int) -> str:
    out = _terme(a, "x", True)
    out += _terme(b, "", out == "")
    return out or "0"


def _nz(rng, lo, hi):
    while True:
        v = rng.randint(lo, hi)
        if v != 0:
            return v


def _op(b: int) -> str:
    """Opération qui annule « + b » dans un membre."""
    return f"on soustrait ${b}$" if b > 0 else f"on ajoute ${-b}$"


def _gen_tester(rng: random.Random) -> Optional[dict]:
    a, c = _nz(rng, -6, 8), _nz(rng, -6, 8)
    if a == c:
        return None
    v = _nz(rng, -6, 6)
    b = rng.randint(-15, 15)
    d = a * v + b - c * v if rng.random() < 0.5 else rng.randint(-15, 15)
    g, dr = a * v + b, c * v + d
    vrai = g == dr
    return {
        "enonce": f"Le nombre ${v}$ est-il solution de l'équation ${lin(a, b)} = {lin(c, d)}$ ?",
        "answer": (f"Oui : pour $x = {v}$, les deux membres valent ${g}$." if vrai
                   else f"Non : pour $x = {v}$, le premier membre vaut ${g}$ et le second ${dr}$."),
        "hint": "Calcule séparément chaque membre en remplaçant $x$ par le nombre.",
        "steps": [f"Premier membre : ${lin(a, b).replace('x', f' \\times {par(v)}') if abs(a) != 1 else lin(a, b).replace('x', par(v))} = {g}$.",
                  f"Second membre : ${lin(c, d).replace('x', f' \\times {par(v)}') if abs(c) != 1 else lin(c, d).replace('x', par(v))} = {dr}$.",
                  f"{'Les deux membres sont égaux' if vrai else 'Les deux membres sont différents'} : ${v}$ {'est' if vrai else 'n est pas'} solution.".replace("n est", "n'est")],
        "notion": N1,
    }


def _resoudre(a, b, c, enonce_eq, notion, prefixe=()):
    x = Fraction(c - b, a)
    steps = list(prefixe)
    if b:
        steps.append(f"{_op(b).capitalize()} aux deux membres : ${lin(a, 0)} = {c - b}$.")
    if a != 1:
        steps.append(f"On divise les deux membres par ${par(a)}$ : $x = {frac(x)}$.")
    steps.append(f"Vérification : pour $x = {frac(x)}$, ${lin(a, b)}$ vaut bien ${c}$.")
    return {
        "enonce": f"Résoudre l'équation ${enonce_eq}$.",
        "answer": f"La solution est ${frac(x)}$.",
        "hint": "Isole le terme en $x$, puis divise par son coefficient.",
        "steps": steps,
        "notion": notion,
    }


def _gen_simple(rng: random.Random) -> Optional[dict]:
    a, x = _nz(rng, -9, 9), _nz(rng, -12, 12)
    if a == 1:
        return None
    b = _nz(rng, -20, 20)
    c = a * x + b
    return _resoudre(a, b, c, f"{lin(a, b)} = {c}", N2)


def _gen_fraction(rng: random.Random) -> Optional[dict]:
    a = _nz(rng, -9, 9)
    b, c = rng.randint(-20, 20), rng.randint(-20, 20)
    if abs(a) == 1 or (c - b) % a == 0:
        return None
    return _resoudre(a, b, c, f"{lin(a, b)} = {c}", N2)


def _gen_deux_membres(rng: random.Random) -> Optional[dict]:
    a, c = _nz(rng, -9, 9), _nz(rng, -9, 9)
    if a == c:
        return None
    x = _nz(rng, -10, 10)
    b = rng.randint(-20, 20)
    d = (a - c) * x + b
    if d == b:
        return None
    eq = f"{lin(a, b)} = {lin(c, d)}"
    pre = [f"On {'soustrait' if c > 0 else 'ajoute'} ${lin(abs(c), 0)}$ aux deux membres : ${lin(a - c, b)} = {d}$."]
    out = _resoudre(a - c, b, d, eq, N3, pre)
    out["steps"][-1] = f"Vérification : pour $x = {frac(Fraction(d - b, a - c))}$, les deux membres valent ${a * x + b}$."
    return out


def _gen_parentheses(rng: random.Random) -> Optional[dict]:
    k = _nz(rng, -6, 7)
    if abs(k) == 1:
        return None
    m, c = _nz(rng, -9, 9), _nz(rng, -6, 8)
    if c == k:
        return None
    x = _nz(rng, -8, 8)
    d = k * (x + m) - c * x
    fk = f"-{abs(k)}" if k < 0 else str(k)
    eq = f"{fk}({lin(1, m)}) = {lin(c, d)}"
    pre = [f"On développe le premier membre : ${lin(k, k * m)} = {lin(c, d)}$.",
           f"On {'soustrait' if c > 0 else 'ajoute'} ${lin(abs(c), 0)}$ aux deux membres : ${lin(k - c, k * m)} = {d}$."]
    out = _resoudre(k - c, k * m, d, eq, N3, pre)
    out["steps"][-1] = f"Vérification : pour $x = {x}$, les deux membres valent ${c * x + d}$."
    return out


def _gen_nombre(rng: random.Random) -> Optional[dict]:
    a, x = rng.randint(2, 9), _nz(rng, -15, 25)
    b = _nz(rng, -30, 30)
    c = a * x + b
    action = f"j'ajoute ${b}$" if b > 0 else f"je retire ${-b}$"
    return {
        "enonce": f"Je pense à un nombre. Je le multiplie par ${a}$, puis {action} : j'obtiens ${c}$. Quel est ce nombre ?",
        "answer": f"Le nombre est ${x}$.",
        "hint": "Appelle $x$ le nombre pensé et écris l'équation.",
        "steps": [f"Soit $x$ le nombre pensé : ${lin(a, b)} = {c}$.",
                  f"${a}x = {c - b}$, donc $x = {x}$.",
                  f"Vérification : ${a} \\times {par(x)} {'+' if b > 0 else '-'} {abs(b)} = {c}$."],
        "notion": N4,
    }


def _gen_tarifs(rng: random.Random) -> Optional[dict]:
    p = rng.randint(8, 20)
    q = rng.randint(3, p - 2)
    n = rng.randint(4, 20)
    f = (p - q) * n
    activite = rng.choice(("une piscine", "un cinéma", "une salle d'escalade", "un club de tennis", "une patinoire"))
    return {
        "enonce": (f"Pour {activite}, le tarif A coûte ${p}$ € par entrée ; le tarif B coûte ${f}$ € d'abonnement annuel "
                   f"puis ${q}$ € par entrée. Pour combien d'entrées les deux tarifs coûtent-ils le même prix ?"),
        "answer": f"Pour ${n}$ entrées (prix commun : ${p * n}$ €).",
        "hint": "Soit $x$ le nombre d'entrées : écris le prix de chaque tarif en fonction de $x$.",
        "steps": [f"Tarif A : ${p}x$ ; tarif B : ${q}x + {f}$.",
                  f"Équation : ${p}x = {q}x + {f}$, soit ${p - q}x = {f}$.",
                  f"$x = {n}$ ; vérification : ${p} \\times {n} = {p * n}$ et ${q} \\times {n} + {f} = {p * n}$."],
        "notion": N4,
    }


def _gen_perimetre(rng: random.Random) -> Optional[dict]:
    a = rng.randint(1, 15)
    genre = rng.random()
    if genre < 0.34:
        b = rng.randint(2, 20)
        x = a + b          # 4x = 2((x + a) + b) <=> 2x = 2a + 2b
        enonce = (f"Un carré a pour côté $x$ cm et un rectangle a pour dimensions $x + {a}$ cm et ${b}$ cm. "
                  "Pour quelle valeur de $x$ ont-ils le même périmètre ?")
        steps = [f"Périmètre du carré : $4x$ ; du rectangle : $2(x + {a} + {b}) = 2x + {2 * (a + b)}$.",
                 f"Équation : $4x = 2x + {2 * (a + b)}$, soit $2x = {2 * (a + b)}$, donc $x = {x}$.",
                 f"Vérification : $4 \\times {x} = {4 * x}$ et $2 \\times ({x + a} + {b}) = {4 * x}$."]
        per = 4 * x
    elif genre < 0.67:
        x = 3 * a          # 4x = 3(x + a)
        enonce = (f"Un carré a pour côté $x$ cm et un triangle équilatéral a pour côté $x + {a}$ cm. "
                  "Pour quelle valeur de $x$ ont-ils le même périmètre ?")
        steps = [f"Périmètre du carré : $4x$ ; du triangle : $3(x + {a}) = 3x + {3 * a}$.",
                 f"Équation : $4x = 3x + {3 * a}$, donc $x = {x}$.",
                 f"Vérification : $4 \\times {x} = {4 * x}$ et $3 \\times {x + a} = {4 * x}$."]
        per = 4 * x
    else:
        x = 4 * a          # 3x = 4(x - a) ; carré de côté x - a
        if x - a <= 0:
            return None
        enonce = (f"Un triangle équilatéral a pour côté $x$ cm et un carré a pour côté $x - {a}$ cm. "
                  "Pour quelle valeur de $x$ ont-ils le même périmètre ?")
        steps = [f"Périmètre du triangle : $3x$ ; du carré : $4(x - {a}) = 4x - {4 * a}$.",
                 f"Équation : $3x = 4x - {4 * a}$, donc $x = {x}$.",
                 f"Vérification : $3 \\times {x} = {3 * x}$ et $4 \\times {x - a} = {3 * x}$."]
        per = 3 * x
    return {
        "enonce": enonce,
        "answer": f"Pour $x = {x}$ cm (périmètre commun : ${per}$ cm).",
        "hint": "Exprime les deux périmètres en fonction de $x$, puis écris qu'ils sont égaux.",
        "steps": steps,
        "notion": N4,
    }


def _gen_ages(rng: random.Random) -> Optional[dict]:
    k = rng.choice((2, 3, 4))
    fils = rng.randint(2, 15)
    n = rng.randint(1, 20)
    pere = k * (fils + n) - n
    if not 22 + fils <= pere <= 60:
        return None
    return {
        "enonce": (f"Un père a ${pere}$ ans et son fils ${fils}$ ans. Dans combien d'années l'âge du père sera-t-il "
                   f"{ {2: 'le double', 3: 'le triple', 4: 'le quadruple'}[k] } de celui du fils ?"),
        "answer": f"Dans ${n}$ ans (le père aura ${pere + n}$ ans et le fils ${fils + n}$ ans).",
        "hint": "Dans $x$ ans, le père aura ($" + str(pere) + " + x$) ans et le fils ($" + str(fils) + " + x$) ans.",
        "steps": [f"Équation : ${pere} + x = {k}({fils} + x)$, soit ${pere} + x = {k * fils} + {k}x$.",
                  f"On soustrait $x$ et ${k * fils}$ aux deux membres : ${pere - k * fils} = {lin(k - 1, 0)}$, donc $x = {n}$.",
                  f"Vérification : ${pere + n} = {k} \\times {fils + n}$."],
        "notion": N4,
    }


FAMILIES_LIST = (
    Family("tester_solution", 1, "Tester si un nombre est solution", N1, _gen_tester,
           "une équation du premier degré", "calculer chaque membre"),
    Family("resoudre_simple", 1, "Résoudre ax + b = c", N2, _gen_simple,
           "une équation à solution entière", "isoler x"),
    Family("resoudre_fraction", 2, "Résoudre avec une solution fractionnaire", N2, _gen_fraction,
           "une équation à solution non entière", "fraction irréductible"),
    Family("resoudre_deux_membres", 2, "Inconnue dans les deux membres", N3, _gen_deux_membres,
           "x des deux côtés", "regrouper les x"),
    Family("resoudre_parentheses", 3, "Équation avec parenthèses", N3, _gen_parentheses,
           "un produit à développer", "développer puis résoudre"),
    Family("probleme_nombre", 1, "Nombre pensé", N4, _gen_nombre,
           "un programme inversé", "mettre en équation"),
    Family("probleme_tarifs", 2, "Comparer deux tarifs", N4, _gen_tarifs,
           "deux tarifs", "égalité des prix"),
    Family("probleme_perimetre", 2, "Périmètres égaux", N4, _gen_perimetre,
           "un carré et un triangle équilatéral", "égalité des périmètres"),
    Family("probleme_ages", 3, "Problème d'âges", N4, _gen_ages,
           "deux âges", "même durée pour les deux"),
)

CHAPTER = Chapter(7, FAMILIES_LIST)
CHAPTER_ID = CHAPTER.chapter_id
FAMILIES = CHAPTER.families
GENERATED_ID_OFFSET = CHAPTER.id_offset
generate_one = CHAPTER.generate_one
generate_pool = CHAPTER.generate_pool
