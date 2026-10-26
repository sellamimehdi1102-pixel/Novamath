"""Génération symbolique d'exercices sur le théorème de Pythagore
(Quatrième, Chapitre_8 — chapitre pilote, chantier 2026-10-24).

Huit familles pédagogiquement DISTINCTES (une compétence ou un raisonnement
différent chacune, jamais la même structure avec d'autres nombres), une
par compétence du chapitre :

    ecrire_egalite         N1  repérer l'hypoténuse, écrire / transformer l'égalité
    encadrer_racine        N2  encadrer une racine entre deux entiers, l'arrondir
    calcul_hypotenuse      N3  calculer l'hypoténuse (exacte ou approchée)
    calcul_cote            N3  calculer un côté de l'angle droit (soustraction)
    rectangle_ou_non       N4  réciproque OU contraposée selon le calcul
    diagonale_rectangle    N5  diagonale d'un objet rectangulaire / objet qui « rentre »
    echelle_mur            N5  échelle, câble : hauteur ou longueur
    hauteur_isocele        N5  hauteur puis aire d'un triangle isocèle ou équilatéral

Arithmétique EXACTE (sympy `Rational`, `sqrt`) : une longueur n'est donnée
sous forme décimale approchée qu'après calcul de sa valeur exacte, arrondie
une seule fois à la fin (jamais un arrondi intermédiaire réutilisé). Chaque
générateur vérifie lui-même ses hypothèses (longueurs strictement positives,
hypoténuse strictement plus longue que chaque côté de l'angle droit,
inégalité triangulaire stricte, écart non ambigu dans le cas « non
rectangle ») et renvoie None si un tirage les viole — build_exercise()
retire alors un nouveau tirage.

Programme de 4e : pas de simplification de racine ($a\\sqrt{b}$), pas de
trigonométrie, pas d'identité remarquable.
"""
import random
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, localcontext
from math import isqrt
from typing import Callable, Optional

from sympy import Rational, sqrt

CHAPTER_ID = "Chapitre_8"

GENERATED_ID_OFFSET = 480_000

# Titres EXACTS des notions de cours_quatrieme/chapitre_8.json (vérifié par
# tests/test_quatrieme_pythagore.py) — même convention que les autres classes.
N1 = "Triangle rectangle et égalité de Pythagore"
N2 = "Carrés et racines carrées"
N3 = "Calculer une longueur avec le théorème de Pythagore"
N4 = "Démontrer qu'un triangle est rectangle ou non"
N5 = "Résoudre un problème avec le théorème de Pythagore"

LEVEL_META = {
    1: {"emoji": "🟢", "label": "Niveau 1 — Fondamental"},
    2: {"emoji": "🟡", "label": "Niveau 2 — Intermédiaire"},
    3: {"emoji": "🟠", "label": "Niveau 3 — Avancé"},
    4: {"emoji": "🔴", "label": "Niveau 4 — Difficile"},
}

# Triplets pythagoriciens primitifs (a < b < c, a² + b² = c²).
_TRIPLETS = ((3, 4, 5), (5, 12, 13), (8, 15, 17), (7, 24, 25), (20, 21, 29), (9, 40, 41), (12, 35, 37), (11, 60, 61))

_TRIANGLES = ("ABC", "DEF", "EFG", "GHI", "IJK", "KLM", "LMN", "MNP", "PQR", "RST", "UVW", "XYZ")

# Précision d'arrondi selon l'unité : (formulation, nombre de décimales).
_PRECISIONS = {
    "cm": (("au dixième", 1), ("au centième", 2), ("au millimètre", 1)),
    "m": (("au dixième", 1), ("au centième", 2), ("au centimètre", 2)),
    "mm": (("à l'unité", 0), ("au dixième", 1)),
    "km": (("au dixième", 1), ("au centième", 2)),
}


# ── Outils numériques (exacts) ────────────────────────────────────────────────

def fr(x) -> str:
    """Valeur exacte décimale finie -> écriture LaTeX française (2{,}5)."""
    x = Rational(x)
    q = x.q
    for p in (2, 5):
        while q % p == 0:
            q //= p
    if q != 1:
        raise ValueError(f"{x} n'est pas un nombre décimal")
    if x.q == 1:
        return str(x.p)
    with localcontext() as ctx:
        ctx.prec = 50
        d = (Decimal(x.p) / Decimal(x.q)).normalize()
    return format(d, "f").replace(".", "{,}")


def approx_sqrt(x2, decimals: int) -> str:
    """Arrondi au plus proche de √x2 à `decimals` décimales, calculé depuis
    la valeur exacte x2 (un nombre décimal non carré : √x2 est irrationnel,
    donc jamais exactement à mi-chemin — l'arrondi n'est jamais ambigu)."""
    x2 = Rational(x2)
    with localcontext() as ctx:
        ctx.prec = 50
        d = (Decimal(x2.p) / Decimal(x2.q)).sqrt()
        q = d.quantize(Decimal(1).scaleb(-decimals), rounding=ROUND_HALF_UP)
    return format(q, "f").replace(".", "{,}")


def approx(x, decimals: int) -> str:
    """Arrondi d'une valeur exacte (Rational ou expression sympy)."""
    with localcontext() as ctx:
        ctx.prec = 50
        d = Decimal(str(x.evalf(40)))
        q = d.quantize(Decimal(1).scaleb(-decimals), rounding=ROUND_HALF_UP)
    return format(q, "f").replace(".", "{,}")


def exact_sqrt(x2) -> Optional[Rational]:
    root = sqrt(Rational(x2))
    return Rational(root) if root.is_rational else None


def _sq_line(values) -> str:
    """"a^2 + b^2" en écriture française."""
    return " + ".join(f"{fr(v)}^2" for v in values)


def _names(rng: random.Random):
    """(triangle, sommet de l'angle droit, les deux autres sommets)."""
    tri = rng.choice(_TRIANGLES)
    vertex = rng.choice(tri)
    p, q = (c for c in tri if c != vertex)
    return tri, vertex, p, q


def _segment(a: str, b: str) -> str:
    """Nom d'un côté dans l'ordre alphabétique ($XY$, jamais $YX$) — les
    triangles de _TRIANGLES sont tous nommés par des lettres consécutives."""
    return "".join(sorted((a, b)))


# ── 1. Écrire / transformer l'égalité de Pythagore (N1) ────────────────────────

def _gen_ecrire_egalite(rng: random.Random) -> Optional[dict]:
    tri, v, p, q = _names(rng)
    hyp = _segment(p, q)
    leg1, leg2 = _segment(v, p), _segment(v, q)
    if hyp == leg1 or hyp == leg2 or v in hyp:
        return None
    egalite = f"{hyp}^2 = {leg1}^2 + {leg2}^2"
    mode = rng.choice(("nommer", "isoler"))
    steps = [
        f"Le triangle ${tri}$ est rectangle en ${v}$ : l'hypoténuse est le côté opposé à ${v}$, c'est-à-dire $[{hyp}]$.",
        f"Les côtés de l'angle droit sont $[{leg1}]$ et $[{leg2}]$ ; on isole l'hypoténuse : ${egalite}$.",
    ]
    if mode == "nommer":
        enonce = f"Le triangle ${tri}$ est rectangle en ${v}$. Nommer son hypoténuse, puis écrire l'égalité de Pythagore."
        answer = f"Hypoténuse : $[{hyp}]$ ; ${egalite}$."
        hint = "L'hypoténuse est le seul côté dont le nom ne contient pas la lettre du sommet de l'angle droit."
    else:
        cible, autre = (leg1, leg2) if rng.random() < 0.5 else (leg2, leg1)
        enonce = (
            f"Le triangle ${tri}$ est rectangle en ${v}$. Écrire l'égalité de Pythagore, "
            f"puis l'écrire sous la forme qui permet de calculer ${cible}^2$."
        )
        answer = f"${egalite}$, donc ${cible}^2 = {hyp}^2 - {autre}^2$."
        hint = "Pour isoler le carré d'un côté de l'angle droit, on retire l'autre carré aux deux membres."
        steps.append(f"On soustrait ${autre}^2$ aux deux membres : ${cible}^2 = {hyp}^2 - {autre}^2$.")
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint, "notion": N1}


# ── 2. Encadrer et arrondir une racine carrée (N2) ────────────────────────────

def _gen_encadrer_racine(rng: random.Random) -> Optional[dict]:
    n = rng.randint(2, 150)
    k = isqrt(n)
    if k * k == n:
        return None  # carré parfait : racine entière, pas d'encadrement strict
    if not (k * k < n < (k + 1) ** 2):
        return None
    arrondi = approx_sqrt(n, 1)
    enonce = (
        f"Encadrer $\\sqrt{{{n}}}$ entre deux nombres entiers consécutifs, "
        "puis donner sa valeur arrondie au dixième à l'aide de la calculatrice."
    )
    answer = f"${k} < \\sqrt{{{n}}} < {k + 1}$ et $\\sqrt{{{n}}} \\approx {arrondi}$."
    steps = [
        f"On cherche les carrés parfaits qui encadrent ${n}$ : ${k}^2 = {k * k}$ et ${k + 1}^2 = {(k + 1) ** 2}$, avec ${k * k} < {n} < {(k + 1) ** 2}$.",
        f"Les racines carrées sont rangées dans le même ordre que les nombres positifs : ${k} < \\sqrt{{{n}}} < {k + 1}$.",
        f"La calculatrice donne $\\sqrt{{{n}}} \\approx {approx_sqrt(n, 3)}$, soit ${arrondi}$ au dixième.",
    ]
    hint = "Récite les carrés parfaits jusqu'à trouver les deux qui entourent le nombre sous la racine."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint, "notion": N2}


# ── Tirage de deux côtés de l'angle droit (familles 3 et 4) ──────────────────

def _draw_right_triangle(rng: random.Random):
    """(a, b, unité) : côtés de l'angle droit, entiers ou décimaux à une
    décimale, avec trois régimes — triplet (hypoténuse entière), triplet
    décimal (hypoténuse décimale exacte) et tirage libre (hypoténuse
    irrationnelle, valeur exacte puis arrondi)."""
    kind = rng.choice(("triplet", "decimal", "libre"))
    if kind == "triplet":
        a, b, _ = rng.choice(_TRIPLETS[:6])
        k = rng.randint(1, 3)
        a, b = Rational(a * k), Rational(b * k)
        unit = rng.choice(("cm", "m", "mm"))
    elif kind == "decimal":
        a, b, _ = rng.choice(_TRIPLETS[:4])
        k = rng.randint(1, 9)
        a, b = Rational(a * k, 10), Rational(b * k, 10)
        unit = rng.choice(("cm", "m", "km"))
    else:
        a, b = Rational(rng.randint(2, 15)), Rational(rng.randint(2, 15))
        unit = rng.choice(("cm", "m"))
    if rng.random() < 0.5:
        a, b = b, a
    return a, b, unit


def _length_result(name: str, value2, unit: str, rng: random.Random):
    """Texte de réponse pour une longueur dont on connaît le carré exact :
    valeur exacte si c'est un décimal, sinon √ puis arrondi."""
    exact = exact_sqrt(value2)
    if exact is not None:
        return "", f"${name} = {fr(exact)}$ {unit}", f"${name} = \\sqrt{{{fr(value2)}}} = {fr(exact)}$ {unit}."
    label, decimals = rng.choice(_PRECISIONS[unit])
    rounded = approx_sqrt(value2, decimals)
    demande = f" Donner la valeur exacte, puis la valeur arrondie {label}."
    answer = f"${name} = \\sqrt{{{fr(value2)}}}$ {unit}, soit ${name} \\approx {rounded}$ {unit}"
    last = (
        f"Valeur exacte : ${name} = \\sqrt{{{fr(value2)}}}$ {unit} ; la calculatrice donne "
        f"$\\sqrt{{{fr(value2)}}} \\approx {approx_sqrt(value2, decimals + 2)}$, soit ${name} \\approx {rounded}$ {unit} ({label})."
    )
    return demande, answer, last


# ── 3. Calculer l'hypoténuse (N3) ──────────────────────────────────────────────

def _gen_calcul_hypotenuse(rng: random.Random) -> Optional[dict]:
    a, b, unit = _draw_right_triangle(rng)
    if a <= 0 or b <= 0:
        return None
    tri, v, p, q = _names(rng)
    hyp, leg1, leg2 = _segment(p, q), _segment(v, p), _segment(v, q)
    c2 = a * a + b * b
    demande, answer, last = _length_result(hyp, c2, unit, rng)
    enonce = (
        f"Le triangle ${tri}$ est rectangle en ${v}$, avec ${leg1} = {fr(a)}$ {unit} et ${leg2} = {fr(b)}$ {unit}. "
        f"Calculer ${hyp}$.{demande}"
    )
    steps = [
        f"Le triangle ${tri}$ est rectangle en ${v}$ : son hypoténuse est $[{hyp}]$.",
        f"D'après le théorème de Pythagore : ${hyp}^2 = {leg1}^2 + {leg2}^2 = {_sq_line((a, b))} = {fr(a * a)} + {fr(b * b)} = {fr(c2)}$.",
        last,
    ]
    hint = "On cherche l'hypoténuse : on additionne les carrés des deux autres côtés, puis on prend la racine carrée."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint, "notion": N3}


# ── 4. Calculer un côté de l'angle droit (N3) ─────────────────────────────────

def _gen_calcul_cote(rng: random.Random) -> Optional[dict]:
    kind = rng.choice(("triplet", "decimal", "libre"))
    if kind == "triplet":
        legs_c = rng.choice(_TRIPLETS[:6])
        k = rng.randint(1, 3)
        c, known = Rational(legs_c[2] * k), Rational(rng.choice(legs_c[:2]) * k)
        unit = rng.choice(("cm", "m", "mm"))
    elif kind == "decimal":
        legs_c = rng.choice(_TRIPLETS[:4])
        k = rng.randint(1, 9)
        c, known = Rational(legs_c[2] * k, 10), Rational(rng.choice(legs_c[:2]) * k, 10)
        unit = rng.choice(("cm", "m", "km"))
    else:
        c = Rational(rng.randint(6, 20))
        known = Rational(rng.randint(2, int(c) - 1))
        unit = rng.choice(("cm", "m"))
    if not (0 < known < c):
        return None  # l'hypoténuse doit être STRICTEMENT la plus longue
    tri, v, p, q = _names(rng)
    hyp = _segment(p, q)
    known_name, wanted = (_segment(v, p), _segment(v, q)) if rng.random() < 0.5 else (_segment(v, q), _segment(v, p))
    x2 = c * c - known * known
    if x2 <= 0:
        return None
    demande, answer, last = _length_result(wanted, x2, unit, rng)
    enonce = (
        f"Le triangle ${tri}$ est rectangle en ${v}$, avec ${hyp} = {fr(c)}$ {unit} et ${known_name} = {fr(known)}$ {unit}. "
        f"Calculer ${wanted}$.{demande}"
    )
    steps = [
        f"Le triangle ${tri}$ est rectangle en ${v}$ : l'hypoténuse est $[{hyp}]$ et ${hyp}^2 = {known_name}^2 + {wanted}^2$.",
        f"On cherche un côté de l'angle droit, donc on soustrait : ${wanted}^2 = {hyp}^2 - {known_name}^2 = {fr(c)}^2 - {fr(known)}^2 = {fr(c * c)} - {fr(known * known)} = {fr(x2)}$.",
        last,
    ]
    hint = "Repère l'hypoténuse parmi les données : pour un côté de l'angle droit, on soustrait les carrés."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint, "notion": N3}


# ── 5. Réciproque ou contraposée (N4) ─────────────────────────────────────────

def _gen_rectangle_ou_non(rng: random.Random) -> Optional[dict]:
    decimal = rng.random() < 0.4
    a, b, c = rng.choice(_TRIPLETS[:6])
    if decimal:
        k = Rational(rng.randint(2, 9), 10)
    else:
        k = Rational(rng.randint(1, 3))
    sides = [a * k, b * k, c * k]
    right = rng.random() < 0.5
    if not right:
        step = Rational(1, 10) if decimal else Rational(1)
        i = rng.randrange(3)
        sides[i] += rng.choice((-1, 1)) * rng.randint(1, 2) * step
    if any(s <= 0 for s in sides):
        return None
    x, y, z = sorted(sides)
    if not x + y > z:
        return None  # inégalité triangulaire stricte : le triangle doit exister
    is_right = x * x + y * y == z * z
    if is_right != right:
        return None
    if not right and abs(z * z - (x * x + y * y)) < Rational(1, 2):
        return None  # écart trop faible : un élève pourrait le confondre avec un arrondi
    tri = rng.choice(_TRIANGLES)
    segments = [tri[0] + tri[1], tri[1] + tri[2], tri[0] + tri[2]]
    rng.shuffle(sides)
    by_segment = dict(zip(segments, sides))
    longest = max(segments, key=lambda s: by_segment[s])
    others = [s for s in segments if s != longest]
    vertex = next(ch for ch in tri if ch not in longest)
    unit = "cm"
    donnees = ", ".join(f"${s} = {fr(by_segment[s])}$ {unit}" for s in segments[:2]) + f" et ${segments[2]} = {fr(by_segment[segments[2]])}$ {unit}"
    enonce = f"Le triangle ${tri}$ est tel que {donnees}. Ce triangle est-il rectangle ? Justifier."
    big2 = by_segment[longest] ** 2
    sum2 = by_segment[others[0]] ** 2 + by_segment[others[1]] ** 2
    steps = [
        f"Le plus long côté est $[{longest}]$ : ${longest}^2 = {fr(by_segment[longest])}^2 = {fr(big2)}$.",
        f"${others[0]}^2 + {others[1]}^2 = {fr(by_segment[others[0]] ** 2)} + {fr(by_segment[others[1]] ** 2)} = {fr(sum2)}$.",
    ]
    if right:
        steps.append(
            f"On constate que ${longest}^2 = {others[0]}^2 + {others[1]}^2$ : d'après la réciproque du théorème de Pythagore, "
            f"le triangle ${tri}$ est rectangle en ${vertex}$."
        )
        answer = f"Oui, le triangle ${tri}$ est rectangle en ${vertex}$."
    else:
        steps.append(
            f"${fr(big2)} \\neq {fr(sum2)}$ : si le triangle était rectangle, ce serait en ${vertex}$ et on aurait l'égalité. "
            f"D'après le théorème de Pythagore (contraposée), le triangle ${tri}$ n'est pas rectangle."
        )
        answer = f"Non, le triangle ${tri}$ n'est pas rectangle."
    hint = "Compare le carré du plus long côté à la somme des carrés des deux autres, sans arrondir."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint, "notion": N4}


# ── 6. Diagonale d'un objet rectangulaire (N5) ────────────────────────────────

_DIAGONALE_CONTEXTES = (
    ("Un écran rectangulaire mesure ${L}$ cm de large et ${l}$ cm de haut. Calculer la longueur de sa diagonale", "cm", (20, 80)),
    ("Un jardin rectangulaire mesure ${L}$ m sur ${l}$ m. Calculer la distance parcourue en le traversant en ligne droite d'un coin au coin opposé", "m", (6, 40)),
    ("Un terrain de sport rectangulaire mesure ${L}$ m de long et ${l}$ m de large. Calculer la longueur d'une de ses diagonales", "m", (20, 100)),
    ("Une plaque de verre rectangulaire mesure ${L}$ cm sur ${l}$ cm. Calculer la longueur de sa diagonale", "cm", (15, 90)),
)


def _gen_diagonale_rectangle(rng: random.Random) -> Optional[dict]:
    mode = rng.choice(("calcul", "calcul", "rentre"))
    if mode == "calcul":
        template, unit, (lo, hi) = rng.choice(_DIAGONALE_CONTEXTES)
        L, w = sorted((rng.randint(lo, hi), rng.randint(lo, hi)), reverse=True)
        if L == w:
            return None
        L, w = Rational(L), Rational(w)
        d2 = L * L + w * w
        exact = exact_sqrt(d2)
        if exact is not None:
            demande = ""
            answer = f"La diagonale mesure ${fr(exact)}$ {unit}."
            last = f"Diagonale $= \\sqrt{{{fr(d2)}}} = {fr(exact)}$ {unit}."
        else:
            label, decimals = rng.choice(_PRECISIONS[unit][:2])
            rounded = approx_sqrt(d2, decimals)
            demande = f", arrondie {label}"
            answer = f"La diagonale mesure environ ${rounded}$ {unit}."
            last = f"Diagonale $= \\sqrt{{{fr(d2)}}} \\approx {rounded}$ {unit} ({label})."
        enonce = template.replace("${L}$", f"${fr(L)}$").replace("${l}$", f"${fr(w)}$") + demande + "."
        steps = [
            "Deux côtés consécutifs du rectangle sont perpendiculaires : avec la diagonale, ils forment un triangle rectangle dont la diagonale est l'hypoténuse.",
            f"Diagonale$^2 = {fr(L)}^2 + {fr(w)}^2 = {fr(L * L)} + {fr(w * w)} = {fr(d2)}$.",
            last,
        ]
        hint = "La diagonale partage le rectangle en deux triangles rectangles."
        return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint, "notion": N5}

    L, w = sorted((rng.randint(20, 70), rng.randint(10, 50)), reverse=True)
    if L == w:
        return None
    L, w = Rational(L), Rational(w)
    d2 = L * L + w * w
    baguette = Rational(int(sqrt(d2).evalf()) + rng.choice((-4, -3, -2, 2, 3, 4)))
    if baguette <= L:
        return None  # sinon la question est triviale (la baguette tient le long d'un bord)
    if abs(baguette * baguette - d2) < 1:
        return None
    rentre = baguette * baguette < d2
    exact = exact_sqrt(d2)
    diag_txt = f"= {fr(exact)}" if exact is not None else f"\\approx {approx_sqrt(d2, 1)}"
    enonce = (
        f"Le fond rectangulaire d'une boîte mesure ${fr(L)}$ cm sur ${fr(w)}$ cm. "
        f"Peut-on y poser à plat une baguette rigide de ${fr(baguette)}$ cm ?"
    )
    steps = [
        "La plus grande longueur que w'on peut poser à plat au fond de la boîte est celle de sa diagonale, hypoténuse d'un triangle rectangle.",
        f"Diagonale$^2 = {fr(L)}^2 + {fr(w)}^2 = {fr(L * L)} + {fr(w * w)} = {fr(d2)}$, donc diagonale $= \\sqrt{{{fr(d2)}}} {diag_txt}$ cm.",
    ]
    if rentre:
        steps.append(f"${fr(baguette)}^2 = {fr(baguette * baguette)} < {fr(d2)}$ : la baguette est plus courte que la diagonale, on peut la poser en diagonale.")
        answer = f"Oui : la diagonale du fond (${diag_txt.removeprefix('= ')}$ cm) est plus longue que la baguette ; on la pose en diagonale."
    else:
        steps.append(f"${fr(baguette)}^2 = {fr(baguette * baguette)} > {fr(d2)}$ : la baguette est plus longue que la diagonale, elle ne tient pas à plat.")
        answer = f"Non : la diagonale du fond (${diag_txt.removeprefix('= ')}$ cm) est plus courte que la baguette."
    hint = "Compare la longueur de la baguette à celle de la diagonale du fond."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint, "notion": N5}


# ── 7. Échelle contre un mur, câble d'un poteau (N5) ──────────────────────────

def _gen_echelle_mur(rng: random.Random) -> Optional[dict]:
    objet = rng.choice(("echelle", "cable"))
    mode = rng.choice(("hauteur", "longueur"))
    if mode == "hauteur":
        longueur = Rational(rng.randint(20, 70), 10)
        distance = Rational(rng.randint(4, 25), 10)
        if not distance < longueur - Rational(3, 10):
            return None
        h2 = longueur * longueur - distance * distance
        if h2 <= 0:
            return None
        exact = exact_sqrt(h2)
        if objet == "echelle":
            enonce = (
                f"Une échelle de ${fr(longueur)}$ m est appuyée contre un mur vertical ; son pied est posé sur le sol horizontal, "
                f"à ${fr(distance)}$ m du mur. À quelle hauteur le haut de l'échelle touche-t-il le mur ?"
            )
            hyp_nom = "l'échelle"
        else:
            enonce = (
                f"Un câble tendu de ${fr(longueur)}$ m relie le sommet d'un poteau vertical à un point du sol horizontal "
                f"situé à ${fr(distance)}$ m du pied du poteau. Quelle est la hauteur du poteau ?"
            )
            hyp_nom = "le câble"
        nombre = fr(exact) if exact is not None else approx_sqrt(h2, 2)
        if exact is None:
            enonce += " Arrondir au centimètre."
        relation = "=" if exact is not None else "\\approx"
        environ = "" if exact is not None else "environ "
        steps = [
            f"{'Le mur' if objet == 'echelle' else 'Le poteau'} est perpendiculaire au sol : on obtient un triangle rectangle dont l'hypoténuse est {hyp_nom}.",
            f"Hauteur$^2 = {fr(longueur)}^2 - {fr(distance)}^2 = {fr(longueur ** 2)} - {fr(distance ** 2)} = {fr(h2)}$.",
            f"Hauteur $= \\sqrt{{{fr(h2)}}} {relation} {nombre}$ m.",
        ]
        if objet == "echelle":
            answer = f"Le haut de l'échelle touche le mur à {environ}${nombre}$ m de hauteur."
        else:
            answer = f"Le poteau mesure {environ}${nombre}$ m de haut."
        hint = "On connaît l'hypoténuse : la hauteur est un côté de l'angle droit."
    else:
        hauteur = Rational(rng.randint(15, 60), 10)
        distance = Rational(rng.randint(4, 25), 10)
        l2 = hauteur * hauteur + distance * distance
        exact = exact_sqrt(l2)
        nombre = fr(exact) if exact is not None else approx_sqrt(l2, 2)
        relation = "=" if exact is not None else "\\approx"
        environ = "" if exact is not None else "environ "
        if objet == "echelle":
            enonce = (
                f"On veut appuyer une échelle contre un mur vertical pour atteindre une fenêtre située à ${fr(hauteur)}$ m de hauteur, "
                f"le pied de l'échelle étant à ${fr(distance)}$ m du mur sur un sol horizontal. Quelle doit être la longueur de l'échelle ?"
            )
            hyp_nom = "l'échelle"
            answer = f"L'échelle doit mesurer {environ}${nombre}$ m."
        else:
            enonce = (
                f"Un câble doit relier le sommet d'un poteau vertical de ${fr(hauteur)}$ m à un point du sol horizontal "
                f"situé à ${fr(distance)}$ m du pied du poteau. Quelle doit être la longueur du câble ?"
            )
            hyp_nom = "le câble"
            answer = f"Le câble doit mesurer {environ}${nombre}$ m."
        if exact is None:
            enonce += " Arrondir au centimètre."
        steps = [
            f"{'Le mur' if objet == 'echelle' else 'Le poteau'} est perpendiculaire au sol : on obtient un triangle rectangle dont l'hypoténuse est {hyp_nom}.",
            f"Longueur$^2 = {fr(hauteur)}^2 + {fr(distance)}^2 = {fr(hauteur ** 2)} + {fr(distance ** 2)} = {fr(l2)}$.",
            f"Longueur $= \\sqrt{{{fr(l2)}}} {relation} {nombre}$ m.",
        ]
        hint = "Fais un schéma : le mur et le sol forment un angle droit, et l'objet cherché est en face de cet angle."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint, "notion": N5}


# ── 8. Hauteur et aire d'un triangle isocèle ou équilatéral (N5) ─────────────

def _gen_hauteur_isocele(rng: random.Random) -> Optional[dict]:
    equilateral = rng.random() < 0.3
    base = Rational(rng.randint(4, 20))
    cote = base if equilateral else Rational(rng.randint(3, 20))
    demi = base / 2
    if not cote > demi:
        return None  # sinon le triangle n'existe pas (inégalité triangulaire)
    h2 = cote * cote - demi * demi
    if h2 <= 0:
        return None
    h_exact = exact_sqrt(h2)
    if equilateral:
        enonce = (
            f"Le triangle $ABC$ est équilatéral de côté ${fr(base)}$ cm. On note $H$ le milieu de $[BC]$ ; "
            "la droite $(AH)$ est perpendiculaire à $(BC)$. Calculer la hauteur $AH$, puis l'aire du triangle $ABC$"
        )
    else:
        enonce = (
            f"Le triangle $ABC$ est isocèle en $A$, avec $AB = AC = {fr(cote)}$ cm et $BC = {fr(base)}$ cm. On note $H$ le milieu de $[BC]$ ; "
            "dans ce triangle isocèle, la droite $(AH)$ est perpendiculaire à $(BC)$. Calculer la hauteur $AH$, puis l'aire du triangle $ABC$"
        )
    if h_exact is not None:
        enonce += "."
        aire = base * h_exact / 2
        h_txt, aire_txt = f"= {fr(h_exact)}", f"= {fr(aire)}"
        answer = f"$AH = {fr(h_exact)}$ cm et l'aire du triangle $ABC$ est ${fr(aire)}$ cm$^2$."
    else:
        enonce += ", en arrondissant les résultats au dixième."
        aire_exacte = base * sqrt(h2) / 2
        h_txt, aire_txt = f"\\approx {approx_sqrt(h2, 1)}", f"\\approx {approx(aire_exacte, 1)}"
        answer = (
            f"$AH = \\sqrt{{{fr(h2)}}}$ cm, soit $AH \\approx {approx_sqrt(h2, 1)}$ cm ; "
            f"l'aire du triangle $ABC$ est d'environ ${approx(aire_exacte, 1)}$ cm$^2$."
        )
    steps = [
        f"$H$ est le milieu de $[BC]$, donc $BH = {fr(base)} \\div 2 = {fr(demi)}$ cm, et le triangle $ABH$ est rectangle en $H$, d'hypoténuse $[AB]$.",
        f"$AH^2 = AB^2 - BH^2 = {fr(cote)}^2 - {fr(demi)}^2 = {fr(cote * cote)} - {fr(demi * demi)} = {fr(h2)}$, donc $AH = \\sqrt{{{fr(h2)}}} {h_txt}$ cm.",
        f"$[AH]$ est la hauteur relative à $[BC]$ : aire $= \\dfrac{{BC \\times AH}}{{2}} {aire_txt}$ cm$^2$"
        + (" (calculée avec la valeur exacte de $AH$, arrondie seulement à la fin)." if h_exact is None else "."),
    ]
    hint = "Commence par le triangle rectangle $ABH$ : la moitié de la base est un de ses côtés."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint, "notion": N5}


@dataclass(frozen=True)
class Family:
    id: str
    level: int
    label: str
    notion: str
    generate: Callable[[random.Random], Optional[dict]]
    structure_hint: str
    rule_hint: str


FAMILY_BASE_SCORE: dict[str, float] = {
    "ecrire_egalite": 1.0,
    "encadrer_racine": 1.2,
    "calcul_hypotenuse": 1.6,
    "calcul_cote": 1.8,
    "rectangle_ou_non": 2.2,
    "diagonale_rectangle": 2.3,
    "echelle_mur": 2.4,
    "hauteur_isocele": 3.0,
}

FAMILIES: tuple[Family, ...] = (
    Family("ecrire_egalite", 1, "Écrire l'égalité de Pythagore", N1, _gen_ecrire_egalite,
           "un triangle rectangle nommé", "repérer l'hypoténuse puis l'isoler"),
    Family("encadrer_racine", 1, "Encadrer et arrondir une racine carrée", N2, _gen_encadrer_racine,
           "une racine carrée non entière", "encadrer par deux carrés parfaits"),
    Family("calcul_hypotenuse", 2, "Calculer l'hypoténuse", N3, _gen_calcul_hypotenuse,
           "deux côtés de l'angle droit connus", "additionner les carrés puis prendre la racine"),
    Family("calcul_cote", 2, "Calculer un côté de l'angle droit", N3, _gen_calcul_cote,
           "l'hypoténuse et un côté de l'angle droit connus", "soustraire les carrés puis prendre la racine"),
    Family("rectangle_ou_non", 3, "Réciproque ou contraposée", N4, _gen_rectangle_ou_non,
           "trois longueurs d'un triangle", "comparer le carré du plus long côté à la somme des deux autres"),
    Family("diagonale_rectangle", 3, "Diagonale d'un objet rectangulaire", N5, _gen_diagonale_rectangle,
           "un objet rectangulaire", "la diagonale est l'hypoténuse"),
    Family("echelle_mur", 3, "Échelle, mur et câble", N5, _gen_echelle_mur,
           "un objet appuyé contre une verticale", "le mur et le sol forment un angle droit"),
    Family("hauteur_isocele", 4, "Hauteur et aire d'un triangle isocèle", N5, _gen_hauteur_isocele,
           "un triangle isocèle ou équilatéral", "travailler dans le demi-triangle rectangle"),
)

FAMILIES_BY_ID = {f.id: f for f in FAMILIES}


def _difficulty_bucket_from_score(score: float) -> int:
    if score <= 1.3:
        return 1
    if score <= 1.9:
        return 2
    if score <= 2.5:
        return 3
    return 4


def build_exercise(family: Family, rng: random.Random) -> Optional[dict]:
    notes = family.generate(rng)
    if notes is None:
        return None
    score = FAMILY_BASE_SCORE[family.id]
    real_level = _difficulty_bucket_from_score(score)
    return {
        "enonce": notes["enonce"],
        "answer": notes["answer"],
        "hint": notes["hint"],
        "solution_steps": [f"Étape {i} — {s}" for i, s in enumerate(notes["steps"], 1)],
        "chapter_id": CHAPTER_ID,
        "notion": notes["notion"],
        "difficulty": real_level,
        "difficulty_label": LEVEL_META[real_level]["label"],
        "difficulty_emoji": LEVEL_META[real_level]["emoji"],
        "family": family.id,
        "family_label": family.label,
        "declared_level": family.level,
        "complexity_score": score,
        "source": "generated",
    }


def generate_one(family_id: str, seed: Optional[int] = None, max_attempts: int = 60) -> dict:
    rng = random.Random(seed)
    fam = FAMILIES_BY_ID[family_id]
    for _ in range(max_attempts):
        ex = build_exercise(fam, rng)
        if ex is not None:
            return ex
    raise RuntimeError(f"Impossible de générer un exercice valide pour la famille {family_id!r}")


def generate_pool(per_family: int = 25, seed: int = 40080001) -> list[dict]:
    """Pool déterministe (même seed -> même pool, mêmes identifiants),
    dédupliqué par énoncé au sein de chaque famille, familles entrelacées."""
    rng = random.Random(seed)
    per_family_pool: dict[str, list[dict]] = {}
    for family in FAMILIES:
        seen = set()
        items = []
        attempts = 0
        while len(items) < per_family and attempts < per_family * 80:
            attempts += 1
            ex = build_exercise(family, rng)
            if ex is None or ex["enonce"] in seen:
                continue
            seen.add(ex["enonce"])
            items.append(ex)
        per_family_pool[family.id] = items

    pool: list[dict] = []
    idx = 0
    while any(per_family_pool.values()):
        bucket = per_family_pool[FAMILIES[idx % len(FAMILIES)].id]
        if bucket:
            pool.append(bucket.pop(0))
        idx += 1
    for i, ex in enumerate(pool):
        ex["id"] = GENERATED_ID_OFFSET + i
    return pool
