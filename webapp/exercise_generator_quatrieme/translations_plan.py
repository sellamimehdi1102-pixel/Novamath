"""Chapitre 11 — Translations (générateurs). Coordonnées entières, repère du plan.

    image_point          N1  image d'un point par un déplacement décrit en mots
    image_par_couple     N1  translation définie par M → N ; image d'un point A
    antecedent           N1  retrouver le point de départ à partir de l'image
    quatrieme_sommet     N1  D image de C par la translation A → B : parallélogramme ABDC
    conservation_mesure  N2  mesure conservée (longueur, angle, aire, périmètre)
    longueur_image       N2  longueur d'un côté image (Pythagore, triplets)
    frise_position       N3  début du n-ième motif d'une frise
    frise_rang           N3  rang d'un motif à partir de sa position
"""
import random
from fractions import Fraction
from typing import Optional

from ._commun import Chapter, Family, grp, par

N1 = "Image d'une figure par une translation"
N2 = "Propriétés de la translation"
N3 = "Translations dans les frises et les pavages"

_ALPHABET = "ABCDEFGHIJKLMNPRSTUVWXYZ"
_TRIPLETS = ((3, 4, 5), (5, 12, 13), (6, 8, 10), (8, 15, 17), (9, 12, 15), (7, 24, 25))


def _pt(p):
    return f"({p[0]} ; {p[1]})"


def _mots(dx, dy):
    parts = []
    if dx:
        parts.append(f"${abs(dx)}$ unité{'s' if abs(dx) > 1 else ''} vers la {'droite' if dx > 0 else 'gauche'}")
    if dy:
        parts.append(f"${abs(dy)}$ unité{'s' if abs(dy) > 1 else ''} vers le {'haut' if dy > 0 else 'bas'}")
    return " et ".join(parts)


def _nz(rng, lo, hi):
    while True:
        v = rng.randint(lo, hi)
        if v:
            return v


def _gen_image_point(rng: random.Random) -> Optional[dict]:
    a = rng.choice(_ALPHABET)
    p = (rng.randint(-8, 8), rng.randint(-8, 8))
    d = (_nz(rng, -9, 9), rng.randint(-9, 9))
    q = (p[0] + d[0], p[1] + d[1])
    return {
        "enonce": f"Dans un repère, une translation déplace chaque point de {_mots(*d)}. Quelle est l'image du point ${a}{_pt(p)}$ ?",
        "answer": f"${a}'{_pt(q)}$",
        "hint": "Ajoute le déplacement horizontal à l'abscisse et le déplacement vertical à l'ordonnée.",
        "steps": [f"Abscisse : ${p[0]} {'+' if d[0] >= 0 else '-'} {abs(d[0])} = {q[0]}$.",
                  f"Ordonnée : ${p[1]} {'+' if d[1] >= 0 else '-'} {abs(d[1])} = {q[1]}$.",
                  f"${a}'{_pt(q)}$."],
        "notion": N1,
    }


def _gen_image_couple(rng: random.Random) -> Optional[dict]:
    m, n, a = rng.sample(_ALPHABET, 3)
    pm = (rng.randint(-6, 6), rng.randint(-6, 6))
    d = (rng.randint(-7, 7), rng.randint(-7, 7))
    if d == (0, 0):
        return None
    pn = (pm[0] + d[0], pm[1] + d[1])
    pa = (rng.randint(-6, 6), rng.randint(-6, 6))
    if pa == pm:
        return None
    pa2 = (pa[0] + d[0], pa[1] + d[1])
    return {
        "enonce": f"La translation qui transforme ${m}{_pt(pm)}$ en ${n}{_pt(pn)}$ transforme ${a}{_pt(pa)}$ en ${a}'$. Donner les coordonnées de ${a}'$.",
        "answer": f"${a}'{_pt(pa2)}$",
        "hint": f"Calcule d'abord le déplacement de ${m}$ à ${n}$.",
        "steps": [f"Déplacement : ${pn[0]} - {par(pm[0])} = {d[0]}$ horizontalement et ${pn[1]} - {par(pm[1])} = {d[1]}$ verticalement.",
                  f"${a}'({pa[0]} + {par(d[0])} ; {pa[1]} + {par(d[1])}) = {_pt(pa2)}$."],
        "notion": N1,
    }


def _gen_antecedent(rng: random.Random) -> Optional[dict]:
    r = rng.choice(_ALPHABET)
    d = (_nz(rng, -9, 9), _nz(rng, -9, 9))
    pr = (rng.randint(-8, 8), rng.randint(-8, 8))
    pr2 = (pr[0] + d[0], pr[1] + d[1])
    return {
        "enonce": f"Par la translation qui déplace de {_mots(*d)}, le point ${r}$ a pour image ${r}'{_pt(pr2)}$. Quelles sont les coordonnées de ${r}$ ?",
        "answer": f"${r}{_pt(pr)}$",
        "hint": "Fais le déplacement inverse.",
        "steps": [f"On retire le déplacement : ${pr2[0]} - {par(d[0])} = {pr[0]}$ et ${pr2[1]} - {par(d[1])} = {pr[1]}$.",
                  f"${r}{_pt(pr)}$ ; vérification : ${pr[0]} + {par(d[0])} = {pr2[0]}$ et ${pr[1]} + {par(d[1])} = {pr2[1]}$."],
        "notion": N1,
    }


def _gen_quatrieme_sommet(rng: random.Random) -> Optional[dict]:
    a, b, c, d = rng.sample(_ALPHABET, 4)
    pa, pb, pc = ((rng.randint(-6, 6), rng.randint(-6, 6)) for _ in range(3))
    # trois points non alignés
    if (pb[0] - pa[0]) * (pc[1] - pa[1]) - (pb[1] - pa[1]) * (pc[0] - pa[0]) == 0:
        return None
    u = (pb[0] - pa[0], pb[1] - pa[1])
    pd = (pc[0] + u[0], pc[1] + u[1])
    return {
        "enonce": (f"On donne ${a}{_pt(pa)}$, ${b}{_pt(pb)}$ et ${c}{_pt(pc)}$. Le point ${d}$ est l'image de ${c}$ par la translation qui transforme "
                   f"${a}$ en ${b}$. Calculer les coordonnées de ${d}$ et donner la nature du quadrilatère ${a}{b}{d}{c}$."),
        "answer": f"${d}{_pt(pd)}$ ; ${a}{b}{d}{c}$ est un parallélogramme.",
        "hint": f"Calcule le déplacement de ${a}$ à ${b}$ et applique-le à ${c}$.",
        "steps": [f"Déplacement de ${a}$ à ${b}$ : ${u[0]}$ horizontalement et ${u[1]}$ verticalement.",
                  f"${d}({pc[0]} + {par(u[0])} ; {pc[1]} + {par(u[1])}) = {_pt(pd)}$.",
                  f"La translation qui transforme ${a}$ en ${b}$ transforme ${c}$ en ${d}$ : ${a}{b}{d}{c}$ est un parallélogramme."],
        "notion": N1,
    }


_MESURES = (
    ("le côté $[{a}{b}]$ mesure ${v}$ cm", "$[{a}'{b}']$ mesure ${v}$ cm", "les longueurs", "cm"),
    ("l'angle $\\widehat{{{a}{b}{c}}}$ mesure ${v}°$", "$\\widehat{{{a}'{b}'{c}'}}$ mesure ${v}°$", "les angles", "°"),
    ("l'aire du triangle ${a}{b}{c}$ vaut ${v}$ cm²", "l'aire de ${a}'{b}'{c}'$ vaut ${v}$ cm²", "les aires", "cm²"),
    ("le périmètre du triangle ${a}{b}{c}$ vaut ${v}$ cm", "le périmètre de ${a}'{b}'{c}'$ vaut ${v}$ cm", "les longueurs (donc les périmètres)", "cm"),
)


def _gen_conservation(rng: random.Random) -> Optional[dict]:
    a, b, c = rng.sample(_ALPHABET, 3)
    i = rng.randrange(len(_MESURES))
    donnee, image, prop, unite = _MESURES[i]
    v = rng.randint(20, 170) if unite == "°" else Fraction(rng.randint(10, 400), 10)
    vs = grp(v)
    return {
        "enonce": (f"Le triangle ${a}'{b}'{c}'$ est l'image du triangle ${a}{b}{c}$ par une translation, et "
                   f"{donnee.format(a=a, b=b, c=c, v=vs)}. Que peut-on dire de l'élément correspondant du triangle ${a}'{b}'{c}'$ ?"),
        "answer": f"Une translation conserve {prop} : {image.format(a=a, b=b, c=c, v=vs)}.",
        "hint": "Une translation fait glisser la figure sans la déformer.",
        "steps": [f"La translation conserve {prop}.", f"Donc {image.format(a=a, b=b, c=c, v=vs)}."],
        "notion": N2,
    }


def _gen_longueur_image(rng: random.Random) -> Optional[dict]:
    a, b, c = rng.sample(_ALPHABET, 3)
    p, q, r = rng.choice(_TRIPLETS)
    k = rng.choice((1, 1, 2, Fraction(1, 2)))
    p, q, r = p * k, q * k, r * k
    if rng.random() < 0.5:
        p, q = q, p
    return {
        "enonce": (f"Le triangle ${a}{b}{c}$ est rectangle en ${a}$, avec ${a}{b} = {grp(p)}$ cm et ${a}{c} = {grp(q)}$ cm. "
                   f"Ses sommets ont pour images ${a}'$, ${b}'$, ${c}'$ par une translation. Calculer ${b}'{c}'$."),
        "answer": f"${b}'{c}' = {grp(r)}$ cm.",
        "hint": "Calcule l'hypoténuse, puis utilise la conservation des longueurs.",
        "steps": [f"Pythagore : ${b}{c}^2 = {grp(p)}^2 + {grp(q)}^2 = {grp(p * p + q * q)}$, donc ${b}{c} = {grp(r)}$ cm.",
                  f"La translation conserve les longueurs : ${b}'{c}' = {b}{c} = {grp(r)}$ cm."],
        "notion": N2,
    }


def _gen_frise_position(rng: random.Random) -> Optional[dict]:
    x0 = Fraction(rng.randint(0, 20), 2)
    pas = Fraction(rng.randint(3, 30), 2)
    n = rng.randint(3, 25)
    pos = x0 + (n - 1) * pas
    return {
        "enonce": (f"Dans une frise, le premier motif commence en $x = {grp(x0)}$ cm et chaque motif est l'image du précédent par une translation "
                   f"de ${grp(pas)}$ cm vers la droite. Où commence le motif numéro ${n}$ ?"),
        "answer": f"En $x = {grp(pos)}$ cm.",
        "hint": "Le motif numéro $n$ est décalé de $n - 1$ pas.",
        "steps": [f"Décalage : $({n} - 1) \\times {grp(pas)} = {grp((n - 1) * pas)}$ cm.",
                  f"Position : ${grp(x0)} + {grp((n - 1) * pas)} = {grp(pos)}$ cm."],
        "notion": N3,
    }


def _gen_frise_rang(rng: random.Random) -> Optional[dict]:
    x0 = Fraction(rng.randint(0, 20), 2)
    pas = Fraction(rng.randint(3, 30), 2)
    n = rng.randint(3, 30)
    pos = x0 + (n - 1) * pas
    return {
        "enonce": (f"Les motifs d'une frise commencent en $x = {grp(x0)}$ cm, puis tous les ${grp(pas)}$ cm. "
                   f"Un motif commence en $x = {grp(pos)}$ cm. Quel est son numéro ?"),
        "answer": f"C'est le motif numéro ${n}$.",
        "hint": "Résous $x_0 + (n - 1) \\times \\text{pas} = x$.",
        "steps": [f"$(n - 1) \\times {grp(pas)} = {grp(pos)} - {grp(x0)} = {grp(pos - x0)}$.",
                  f"$n - 1 = {grp(pos - x0)} \\div {grp(pas)} = {n - 1}$, donc $n = {n}$."],
        "notion": N3,
    }


FAMILIES_LIST = (
    Family("image_point", 1, "Image d'un point", N1, _gen_image_point,
           "un déplacement décrit en mots", "ajouter le déplacement"),
    Family("image_par_couple", 2, "Translation définie par deux points", N1, _gen_image_couple,
           "un point et son image", "même déplacement"),
    Family("antecedent", 2, "Retrouver un point de départ", N1, _gen_antecedent,
           "une image et un déplacement", "déplacement inverse"),
    Family("quatrieme_sommet", 3, "Parallélogramme et translation", N1, _gen_quatrieme_sommet,
           "trois points", "parallélogramme ABDC"),
    Family("conservation_mesure", 1, "Mesure conservée", N2, _gen_conservation,
           "une mesure du triangle de départ", "conservation"),
    Family("longueur_image", 2, "Longueur d'un côté image", N2, _gen_longueur_image,
           "un triangle rectangle", "Pythagore et conservation"),
    Family("frise_position", 1, "Position d'un motif", N3, _gen_frise_position,
           "une frise", "n - 1 pas"),
    Family("frise_rang", 2, "Rang d'un motif", N3, _gen_frise_rang,
           "une position dans une frise", "équation simple"),
)

CHAPTER = Chapter(11, FAMILIES_LIST)
CHAPTER_ID = CHAPTER.chapter_id
FAMILIES = CHAPTER.families
GENERATED_ID_OFFSET = CHAPTER.id_offset
generate_one = CHAPTER.generate_one
generate_pool = CHAPTER.generate_pool
