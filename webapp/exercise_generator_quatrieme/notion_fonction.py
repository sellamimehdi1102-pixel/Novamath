"""Chapitre 15 — Notion de fonction (générateurs).

    calculer_valeur      N1  valeur d'une grandeur donnée par une formule
    traduire_situation   N1  part fixe + part variable : formule et valeur
    tableau_valeurs      N1  tableau de valeurs d'une formule y = ax + b
    point_sur_graphique  N2  le point (x ; y) est-il sur le graphique de y = ax + b ?
    graduation           N2  pas de graduation pour faire tenir une valeur maximale
    lecture_points       N3  lecture directe ou inverse sur un graphique donné par ses points
    lecture_segment      N3  lecture sur un graphique formé d'un segment (évolution régulière)
"""
import random
import re
from fractions import Fraction
from typing import Optional

from ._commun import Chapter, Family, frac, grp

N1 = "Exprimer une grandeur en fonction d'une autre"
N2 = "Représenter une dépendance par un graphique"
N3 = "Lire et interpréter un graphique"

_CONTEXTES = (
    ("Une salle de sport demande ${f}$ € d'inscription puis ${u}$ € par séance.", "du nombre $n$ de séances", "P", "n", "séances", "€"),
    ("Un taxi facture ${f}$ € de prise en charge puis ${u}$ € par kilomètre.", "de la distance $n$ parcourue (en km)", "P", "n", "km", "€"),
    ("Une location de vélo coûte ${f}$ € de caution non remboursée puis ${u}$ € par heure.", "de la durée $n$ (en heures)", "P", "n", "heures", "€"),
    ("Un réservoir contient ${f}$ L et reçoit ${u}$ L par minute.", "du temps $n$ (en minutes)", "V", "n", "minutes", "L"),
    ("Une plante mesure ${f}$ cm et pousse de ${u}$ cm par semaine.", "du nombre $n$ de semaines", "h", "n", "semaines", "cm"),
)


def _nz(rng, lo, hi):
    while True:
        v = rng.randint(lo, hi)
        if v:
            return v


def _lin(a, b, var="x"):
    out = (f"{a}{var}" if abs(a) != 1 else ("-" if a < 0 else "") + var)
    if b:
        out += f" {'+' if b > 0 else '-'} {abs(b)}"
    return out


def _gen_calculer(rng: random.Random) -> Optional[dict]:
    genre = rng.choice(("affine", "carre", "produit"))
    x = rng.randint(-5, 8)
    if genre == "affine":
        a, b = _nz(rng, -9, 9), rng.randint(-15, 15)
        formule, y = f"y = {_lin(a, b)}", a * x + b
    elif genre == "carre":
        a, c = _nz(rng, -4, 5), rng.randint(-20, 20)
        formule = f"y = {a if abs(a) != 1 else ('-' if a < 0 else '')}x^2" + (f" {'+' if c > 0 else '-'} {abs(c)}" if c else "")
        y = a * x * x + c
    else:
        k = rng.randint(4, 12)
        formule, y = f"y = x({k} - x)", x * (k - x)
    xs = f"({x})" if x < 0 else str(x)
    # Membre de droite avec x remplacé, signes × rétablis (« 4x^2 » → « 4 \times (-2)^2 »).
    rhs = formule.split("=", 1)[1].strip().replace("x", "§")
    rhs = re.sub(r"(\d)§", r"\1 \\times §", rhs).replace("§(", "§ \\times (").replace("§", xs)
    return {
        "enonce": f"La grandeur $y$ est donnée en fonction de $x$ par la formule ${formule}$. Calculer $y$ pour $x = {x}$.",
        "answer": f"Pour $x = {x}$, $y = {y}$.",
        "hint": "Remplace $x$ par sa valeur, entre parenthèses si elle est négative, et respecte les priorités.",
        "steps": [f"On remplace $x$ par ${xs}$ dans ${formule}$ : $y = {rhs}$.",
                  f"On respecte les priorités (puissances, puis multiplications, puis additions) : $y = {y}$."],
        "notion": N1,
    }


def _gen_traduire(rng: random.Random) -> Optional[dict]:
    txt, var_desc, nom, n, unite_n, unite = rng.choice(_CONTEXTES)
    f = rng.randint(2, 60)
    u = Fraction(rng.randint(2, 40), 2)
    k = rng.randint(2, 20)
    val = f + u * k
    return {
        "enonce": (txt.format(f=f, u=grp(u)) + f" Exprimer ${nom}$ en fonction {var_desc}, puis calculer ${nom}$ pour ${n} = {k}$."),
        "answer": f"${nom} = {grp(u)}{n} + {f}$ ; pour ${n} = {k}$, ${nom} = {grp(val)}$ {unite}.",
        "hint": "Part variable (proportionnelle) + part fixe.",
        "steps": [f"Part variable : ${grp(u)} \\times {n}$ ; part fixe : ${f}$.",
                  f"${nom} = {grp(u)}{n} + {f}$.",
                  f"Pour ${n} = {k}$ : ${grp(u)} \\times {k} + {f} = {grp(val)}$ {unite}."],
        "notion": N1,
    }


def _gen_tableau(rng: random.Random) -> Optional[dict]:
    a, b = _nz(rng, -6, 7), rng.randint(-10, 10)
    xs = sorted(rng.sample(range(-4, 7), 4))
    ys = [a * x + b for x in xs]
    return {
        "enonce": f"Compléter le tableau de valeurs de $y = {_lin(a, b)}$ pour $x = {' ; '.join(map(str, xs))}$.",
        "answer": f"$y = {' ; '.join(map(str, ys))}$.",
        "hint": "Calcule la formule pour chaque valeur de $x$.",
        "steps": [f"$x = {x}$ : $y = {y}$." for x, y in zip(xs, ys)],
        "notion": N1,
    }


def _gen_point(rng: random.Random) -> Optional[dict]:
    a, b = _nz(rng, -6, 7), rng.randint(-10, 10)
    x = rng.randint(-5, 6)
    y = a * x + b
    if rng.random() < 0.5:
        y += rng.choice((-2, -1, 1, 2))
    ok = y == a * x + b
    return {
        "enonce": f"Le point $({x} ; {y})$ appartient-il au graphique représentant $y = {_lin(a, b)}$ ?",
        "answer": (f"Oui : pour $x = {x}$, $y = {a * x + b}$." if ok
                   else f"Non : pour $x = {x}$, $y = {a * x + b}$ et non ${y}$."),
        "hint": "Calcule $y$ pour l'abscisse du point et compare avec son ordonnée.",
        "steps": [f"Pour $x = {x}$ : $y = {a * x + b}$.",
                  "C'est l'ordonnée du point : il appartient au graphique." if ok else f"${a * x + b} \\neq {y}$ : le point n'appartient pas au graphique."],
        "notion": N2,
    }


def _gen_graduation(rng: random.Random) -> Optional[dict]:
    pas = rng.choice((2, 5, 10, 20, 25, 50, 100))
    carreaux = rng.randint(5, 15)
    maxi = pas * carreaux - rng.randint(0, pas - 1) if pas > 1 else pas * carreaux
    grandeur = rng.choice(("des températures", "des distances", "des prix", "des masses", "des hauteurs"))
    # le plus petit pas « rond » qui convient
    ronds = (1, 2, 5, 10, 20, 25, 50, 100, 200)
    p = next(r for r in ronds if r * carreaux >= maxi)
    return {
        "enonce": (f"On veut représenter {grandeur} allant de $0$ à ${maxi}$ sur un axe de ${carreaux}$ carreaux. "
                   f"Parmi les pas $1$, $2$, $5$, $10$, $20$, $25$, $50$, $100$, $200$, quel est le plus petit pas qui convient ?"),
        "answer": f"Le pas de ${p}$ par carreau.",
        "hint": "Le pas multiplié par le nombre de carreaux doit atteindre la valeur maximale.",
        "steps": [f"Le pas doit vérifier : pas $\\times {carreaux} \\geq {maxi}$, soit pas $\\geq {grp(Fraction(maxi, carreaux))}$." if Fraction(maxi, carreaux).denominator in (1, 2, 4, 5, 10, 20, 25, 50) else f"Le pas doit vérifier : pas $\\times {carreaux} \\geq {maxi}$.",
                  f"Le plus petit pas de la liste qui convient est ${p}$ (car ${p} \\times {carreaux} = {p * carreaux}$)."],
        "notion": N2,
    }


def _gen_lecture_points(rng: random.Random) -> Optional[dict]:
    k = rng.randint(4, 8)
    xs = list(range(0, k + 1))
    ys = [x * (k - x) for x in xs]
    pts = " ; ".join(f"$({x} ; {y})$" for x, y in zip(xs, ys))
    if rng.random() < 0.5:
        x = rng.choice(xs)
        return {
            "enonce": f"Un graphique passe par les points {pts}. Lire la valeur de $y$ pour $x = {x}$.",
            "answer": f"Pour $x = {x}$, $y = {ys[x]}$.",
            "hint": "Cherche le point d'abscisse donnée et lis son ordonnée.",
            "steps": [f"Point d'abscisse ${x}$ : $({x} ; {ys[x]})$.", f"$y = {ys[x]}$."],
            "notion": N3,
        }
    y = rng.choice(sorted(set(ys)))
    sol = [x for x in xs if ys[x] == y]
    sol_txt = " et ".join(f"$x = {s}$" for s in sol)
    return {
        "enonce": f"Un graphique passe par les points {pts}. Pour quelles valeurs de $x$ (parmi celles du graphique) a-t-on $y = {y}$ ?",
        "answer": f"Pour {sol_txt}.",
        "hint": "Cherche tous les points d'ordonnée donnée.",
        "steps": [f"Points d'ordonnée ${y}$ : " + ", ".join(f"$({s} ; {y})$" for s in sol) + ".", f"Solutions : {sol_txt}."],
        "notion": N3,
    }


def _gen_lecture_segment(rng: random.Random) -> Optional[dict]:
    T = rng.choice((4, 5, 8, 10, 12, 20))
    y0, y1 = rng.randint(0, 50) * 2, rng.randint(0, 50) * 2
    if y0 == y1:
        return None
    pente = Fraction(y1 - y0, T)
    if rng.random() < 0.5:
        t = rng.randint(1, T - 1)
        v = y0 + pente * t
        if v.denominator not in (1, 2, 4, 5, 10):
            return None
        ps = grp(pente) if pente.denominator in (1, 2, 4, 5, 10) else frac(pente)
        return {
            "enonce": f"Un graphique est formé d'un segment allant du point $(0 ; {y0})$ au point $({T} ; {y1})$. Quelle est la valeur de $y$ pour $x = {t}$ ?",
            "answer": f"Pour $x = {t}$, $y = {grp(v)}$.",
            "hint": "Sur un segment, $y$ varie régulièrement : calcule la variation de $y$ pour une unité de $x$.",
            "steps": [f"Variation de $y$ par unité de $x$ : $\\dfrac{{{y1} - {y0}}}{{{T}}} = {grp(pente) if pente.denominator in (1, 2, 4, 5, 10) else frac(pente)}$.",
                      f"$y = {y0} + {t} \\times {f'({ps})' if pente < 0 else ps} = {grp(v)}$."],
            "notion": N3,
        }
    v = rng.randint(min(y0, y1) + 1, max(y0, y1) - 1) if abs(y1 - y0) > 2 else None
    if v is None:
        return None
    t = (v - y0) / pente
    if t.denominator not in (1, 2, 4, 5, 10):
        return None
    return {
        "enonce": f"Un graphique est formé d'un segment allant du point $(0 ; {y0})$ au point $({T} ; {y1})$. Pour quelle valeur de $x$ a-t-on $y = {v}$ ?",
        "answer": f"Pour $x = {grp(t)}$.",
        "hint": "Calcule de combien $y$ doit varier, puis combien d'unités de $x$ cela représente.",
        "steps": [f"$y$ doit varier de ${v - y0}$, à raison de $\\dfrac{{{y1 - y0}}}{{{T}}}$ par unité de $x$.",
                  f"$x = {v - y0} \\times \\dfrac{{{T}}}{{{y1 - y0}}} = {grp(t)}$."],
        "notion": N3,
    }


FAMILIES_LIST = (
    Family("calculer_valeur", 1, "Calculer une valeur", N1, _gen_calculer,
           "une formule", "remplacer et calculer"),
    Family("traduire_situation", 2, "Formule d'une situation", N1, _gen_traduire,
           "part fixe et part variable", "écrire la formule"),
    Family("tableau_valeurs", 1, "Tableau de valeurs", N1, _gen_tableau,
           "une formule et quatre valeurs", "calculer chaque colonne"),
    Family("point_sur_graphique", 1, "Point d'un graphique", N2, _gen_point,
           "un point et une formule", "comparer les ordonnées"),
    Family("graduation", 2, "Choisir une graduation", N2, _gen_graduation,
           "une valeur maximale et un axe", "pas × carreaux ≥ maximum"),
    Family("lecture_points", 1, "Lire un graphique", N3, _gen_lecture_points,
           "un graphique donné par ses points", "sens direct ou inverse"),
    Family("lecture_segment", 2, "Lire une évolution régulière", N3, _gen_lecture_segment,
           "un graphique en segment", "variation par unité"),
)

CHAPTER = Chapter(15, FAMILIES_LIST)
CHAPTER_ID = CHAPTER.chapter_id
FAMILIES = CHAPTER.families
GENERATED_ID_OFFSET = CHAPTER.id_offset
generate_one = CHAPTER.generate_one
generate_pool = CHAPTER.generate_pool
