"""Chapitre 13 — Espace : repérage, pyramides, cônes, volumes (générateurs).

    coordonnees_sommet  N1  coordonnées d'un sommet d'un pavé (origine A)
    diagonale_pave      N1  grande diagonale d'un pavé (Pythagore deux fois, valeur exacte)
    elements_pyramide   N2  faces, arêtes, sommets d'une pyramide à base à n côtés
    generatrice_cone    N2  génératrice d'un cône (triplets pythagoriciens)
    volume_pyramide     N3  B × h ÷ 3 (base carrée, rectangulaire ou triangle rectangle)
    volume_cone         N3  π r² h ÷ 3 : valeur exacte en π puis arrondi au dixième
    hauteur_pyramide    N3  hauteur à partir du volume et de la base carrée
    volume_k3           N4  volume après agrandissement ou réduction de rapport k
"""
import math
import random
from fractions import Fraction
from typing import Optional

from ._commun import Chapter, Family, frac, grp

N1 = "Se repérer dans un pavé droit"
N2 = "Pyramides et cônes : perspective et patrons"
N3 = "Volume d'une pyramide et d'un cône"
N4 = "Agrandissement et réduction : longueurs, aires, volumes"

# Sommets du pavé ABCDEFGH repéré depuis A : (facteur abscisse, ordonnée, altitude)
_SOMMETS = {"A": (0, 0, 0), "B": (1, 0, 0), "C": (1, 1, 0), "D": (0, 1, 0),
            "E": (0, 0, 1), "F": (1, 0, 1), "G": (1, 1, 1), "H": (0, 1, 1)}
_POLYGONES = ((3, "triangulaire"), (4, "carrée"), (4, "rectangulaire"), (5, "pentagonale"), (6, "hexagonale"),
              (7, "heptagonale"), (8, "octogonale"), (9, "ennéagonale"), (10, "décagonale"), (12, "dodécagonale"))
_TRIPLETS = ((3, 4, 5), (6, 8, 10), (5, 12, 13), (8, 15, 17), (9, 12, 15), (7, 24, 25), (12, 16, 20))


def _racine(n: int) -> str:
    r = math.isqrt(n)
    return str(r) if r * r == n else f"\\sqrt{{{n}}}"


def _gen_coordonnees(rng: random.Random) -> Optional[dict]:
    L, l, h = rng.randint(2, 12), rng.randint(2, 12), rng.randint(2, 12)
    s = rng.choice("BCDEFGH")
    fx, fy, fz = _SOMMETS[s]
    c = (fx * L, fy * l, fz * h)
    return {
        "enonce": (f"Le pavé droit $ABCDEFGH$ a pour dimensions $AB = {L}$, $AD = {l}$ et $AE = {h}$ (la face $EFGH$ est au-dessus de $ABCD$, "
                   f"$E$ au-dessus de $A$). Dans le repère d'origine $A$, quelles sont les coordonnées de ${s}$ ?"),
        "answer": f"${s}({c[0]} ; {c[1]} ; {c[2]})$",
        "hint": "Abscisse le long de $[AB]$, ordonnée le long de $[AD]$, altitude le long de $[AE]$.",
        "steps": [f"Pour aller de $A$ à ${s}$ : on avance de ${c[0]}$, on se décale de ${c[1]}$, on monte de ${c[2]}$.",
                  f"${s}({c[0]} ; {c[1]} ; {c[2]})$."],
        "notion": N1,
    }


def _gen_diagonale(rng: random.Random) -> Optional[dict]:
    L, l, h = rng.randint(2, 12), rng.randint(2, 12), rng.randint(2, 12)
    ac2, ag2 = L * L + l * l, L * L + l * l + h * h
    return {
        "enonce": f"Un pavé droit $ABCDEFGH$ a pour dimensions $AB = {L}$ cm, $BC = {l}$ cm et $CG = {h}$ cm. Calculer la valeur exacte de la grande diagonale $AG$.",
        "answer": f"$AG = {_racine(ag2)}$ cm.",
        "hint": "Pythagore dans le triangle $ABC$, puis dans le triangle $ACG$ rectangle en $C$.",
        "steps": [f"Dans $ABC$ rectangle en $B$ : $AC^2 = {L}^2 + {l}^2 = {ac2}$.",
                  f"Dans $ACG$ rectangle en $C$ : $AG^2 = AC^2 + CG^2 = {ac2} + {h * h} = {ag2}$.",
                  f"$AG = {_racine(ag2)}$ cm."],
        "notion": N1,
    }


def _gen_elements(rng: random.Random) -> Optional[dict]:
    n, nom = rng.choice(_POLYGONES)
    objet = rng.choice(("Une pyramide", "Un toit en forme de pyramide", "Une bougie en forme de pyramide", "Un presse-papier en forme de pyramide",
                        "Une lampe en forme de pyramide", "Une tente en forme de pyramide"))
    return {
        "enonce": f"{objet} a une base {nom} (${n}$ côtés). Combien a-t-elle de faces, d'arêtes et de sommets ?",
        "answer": f"${n + 1}$ faces, ${2 * n}$ arêtes et ${n + 1}$ sommets.",
        "hint": "Une face latérale par côté de la base, plus la base.",
        "steps": [f"Faces : ${n}$ faces latérales + la base $= {n + 1}$.",
                  f"Arêtes : ${n}$ de la base + ${n}$ latérales $= {2 * n}$.",
                  f"Sommets : ${n}$ sommets de la base + le sommet $= {n + 1}$."],
        "notion": N2,
    }


def _gen_generatrice(rng: random.Random) -> Optional[dict]:
    a, b, c = rng.choice(_TRIPLETS)
    k = rng.choice((1, 1, 2, 3, Fraction(1, 2), Fraction(3, 2)))
    a, b, c = a * k, b * k, c * k
    r, h = (a, b) if rng.random() < 0.5 else (b, a)
    if rng.random() < 0.4:
        return {
            "enonce": f"Un cône de révolution a une génératrice de ${grp(c)}$ cm et une base de rayon ${grp(r)}$ cm. Calculer sa hauteur.",
            "answer": f"La hauteur mesure ${grp(h)}$ cm.",
            "hint": "La hauteur, un rayon et une génératrice forment un triangle rectangle dont la génératrice est l'hypoténuse.",
            "steps": [f"Hauteur$^2 = {grp(c)}^2 - {grp(r)}^2 = {grp(c * c - r * r)}$.", f"Hauteur $= {grp(h)}$ cm."],
            "notion": N2,
        }
    return {
        "enonce": f"Un cône de révolution a une hauteur de ${grp(h)}$ cm et une base de rayon ${grp(r)}$ cm. Calculer la longueur d'une génératrice.",
        "answer": f"La génératrice mesure ${grp(c)}$ cm.",
        "hint": "La hauteur, un rayon et une génératrice forment un triangle rectangle.",
        "steps": ["La hauteur est perpendiculaire au rayon : triangle rectangle.",
                  f"Génératrice$^2 = {grp(h)}^2 + {grp(r)}^2 = {grp(h * h + r * r)}$.",
                  f"Génératrice $= {grp(c)}$ cm."],
        "notion": N2,
    }


def _gen_volume_pyramide(rng: random.Random) -> Optional[dict]:
    genre = rng.choice(("carrée", "rectangulaire", "triangle"))
    h = rng.randint(2, 30)
    if genre == "carrée":
        c = rng.randint(2, 15)
        base, desc, calc = Fraction(c * c), f"une base carrée de côté ${c}$ cm", f"${c} \\times {c} = {c * c}$ cm²"
    elif genre == "rectangulaire":
        a, b = rng.randint(2, 15), rng.randint(2, 15)
        if a == b:
            return None
        base, desc, calc = Fraction(a * b), f"une base rectangulaire de ${a}$ cm sur ${b}$ cm", f"${a} \\times {b} = {a * b}$ cm²"
    else:
        a, b = rng.randint(2, 15), rng.randint(2, 15)
        base = Fraction(a * b, 2)
        desc = f"pour base un triangle rectangle dont les côtés de l'angle droit mesurent ${a}$ cm et ${b}$ cm"
        calc = f"$\\dfrac{{{a} \\times {b}}}{{2}} = {grp(base)}$ cm²"
    v = base * h / 3
    if v.denominator not in (1, 2):
        return None
    a_ou_pour = "a " if not desc.startswith("pour") else "a "
    return {
        "enonce": f"Une pyramide {a_ou_pour}{desc} et une hauteur de ${h}$ cm. Calculer son volume.",
        "answer": f"$V = {grp(v)}$ cm³.",
        "hint": "Volume = aire de la base × hauteur ÷ 3.",
        "steps": [f"Aire de la base : {calc}.", f"$V = \\dfrac{{{grp(base)} \\times {h}}}{{3}} = {grp(v)}$ cm³."],
        "notion": N3,
    }


def _gen_volume_cone(rng: random.Random) -> Optional[dict]:
    r, h = rng.randint(1, 12), rng.randint(2, 30)
    k = Fraction(r * r * h, 3)
    if k.denominator != 1:
        return None
    if abs(float(k) * math.pi * 10 - math.floor(float(k) * math.pi * 10) - 0.5) < 1e-4:
        return None
    exact = f"{k}\\pi"
    return {
        "enonce": f"Calculer le volume d'un cône de révolution de rayon ${r}$ cm et de hauteur ${h}$ cm : valeur exacte, puis valeur arrondie au dixième.",
        "answer": f"$V = {exact} \\approx {grp(Fraction(round(float(k) * math.pi * 10), 10))}$ cm³.",
        "hint": "$V = \\dfrac{\\pi r^2 h}{3}$.",
        "steps": [f"Aire de la base : $\\pi \\times {r}^2 = {r * r}\\pi$ cm².",
                  f"$V = \\dfrac{{{r * r}\\pi \\times {h}}}{{3}} = {exact}$ cm³.",
                  f"$V \\approx {grp(Fraction(round(float(k) * math.pi * 10), 10))}$ cm³."],
        "notion": N3,
    }


def _gen_hauteur(rng: random.Random) -> Optional[dict]:
    c, h = rng.randint(2, 12), rng.randint(2, 24)
    v = Fraction(c * c * h, 3)
    if v.denominator != 1:
        return None
    return {
        "enonce": f"Une pyramide à base carrée de côté ${c}$ cm a un volume de ${v}$ cm³. Calculer sa hauteur.",
        "answer": f"La hauteur est ${h}$ cm.",
        "hint": "$V = \\dfrac{\\mathcal{B} \\times h}{3}$, donc $h = \\dfrac{3V}{\\mathcal{B}}$.",
        "steps": [f"Aire de la base : ${c * c}$ cm².", f"$h = \\dfrac{{3 \\times {v}}}{{{c * c}}} = {h}$ cm."],
        "notion": N3,
    }


def _gen_volume_k3(rng: random.Random) -> Optional[dict]:
    k = rng.choice((Fraction(2), Fraction(3), Fraction(1, 2), Fraction(1, 3), Fraction(3, 2), Fraction(4), Fraction(1, 4), Fraction(5)))
    v = Fraction(rng.randint(2, 400))
    v2 = v * k ** 3
    if v2.denominator not in (1, 2, 4, 8):
        return None
    solide = rng.choice(("Un cône", "Une pyramide", "Un pavé droit", "Un cylindre", "Une maquette de bâtiment"))
    nature = "agrandi" if k > 1 else "réduit"
    if solide.startswith("Une"):
        nature = nature + "e"
    kt = grp(k) if k.denominator in (1, 2, 4) else frac(k)
    k3 = grp(k ** 3) if (k ** 3).denominator in (1, 2, 4, 8, 16, 64) else frac(k ** 3)
    kp = f"\\left({kt}\\right)" if "dfrac" in kt else kt
    return {
        "enonce": f"{solide} de volume ${grp(v)}$ cm³ est {nature} avec le rapport ${kt}$. Quel est le nouveau volume ?",
        "answer": f"Le nouveau volume est ${grp(v2)}$ cm³.",
        "hint": "Les volumes sont multipliés par $k^3$.",
        "steps": [f"$k^3 = {kp}^3 = {k3}$.", f"${grp(v)} \\times {k3} = {grp(v2)}$ cm³."],
        "notion": N4,
    }


FAMILIES_LIST = (
    Family("coordonnees_sommet", 1, "Coordonnées d'un sommet", N1, _gen_coordonnees,
           "un pavé droit", "abscisse, ordonnée, altitude"),
    Family("diagonale_pave", 3, "Grande diagonale d'un pavé", N1, _gen_diagonale,
           "trois dimensions", "Pythagore deux fois"),
    Family("elements_pyramide", 1, "Faces, arêtes, sommets", N2, _gen_elements,
           "une base à n côtés", "n + 1, 2n, n + 1"),
    Family("generatrice_cone", 2, "Génératrice d'un cône", N2, _gen_generatrice,
           "hauteur et rayon", "Pythagore"),
    Family("volume_pyramide", 1, "Volume d'une pyramide", N3, _gen_volume_pyramide,
           "une base et une hauteur", "B × h ÷ 3"),
    Family("volume_cone", 2, "Volume d'un cône", N3, _gen_volume_cone,
           "rayon et hauteur", "π r² h ÷ 3"),
    Family("hauteur_pyramide", 3, "Hauteur à partir du volume", N3, _gen_hauteur,
           "un volume et une base", "h = 3V ÷ B"),
    Family("volume_k3", 2, "Volume et rapport k", N4, _gen_volume_k3,
           "un volume et un rapport", "volumes × k³"),
)

CHAPTER = Chapter(13, FAMILIES_LIST)
CHAPTER_ID = CHAPTER.chapter_id
FAMILIES = CHAPTER.families
GENERATED_ID_OFFSET = CHAPTER.id_offset
generate_one = CHAPTER.generate_one
generate_pool = CHAPTER.generate_pool
