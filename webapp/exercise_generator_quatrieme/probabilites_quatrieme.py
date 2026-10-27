"""Chapitre 17 — Probabilités (générateurs). Nom distinct de exercise_generator_troisieme.probabilites_troisieme.

    issues_evenement     N1  lister les issues qui réalisent un événement (roue numérotée)
    proba_roue           N2  probabilité d'un événement sur une roue équilibrée numérotée
    proba_urne           N2  probabilité de tirer une couleur dans une urne
    contraire_decimal    N3  probabilité de l'événement contraire (décimale)
    contraire_urne       N3  probabilité de « ne pas tirer » une couleur
    proba_manquante      N4  probabilité manquante (dé truqué, osselet)
    roue_angles          N4  probabilité d'un secteur à partir des angles
    cible_carres         N4  probabilité par les aires (cible carrée)
"""
import random
from fractions import Fraction
from typing import Optional

from ._commun import Chapter, Family, frac, num

N1 = "Expériences aléatoires et vocabulaire"
N2 = "Calculer une probabilité"
N3 = "Événement contraire"
N4 = "Probabilités et aires, issues non équiprobables"

_COULEURS = ("rouges", "bleues", "vertes", "jaunes", "noires")
_SINGULIER = {"rouges": "rouge", "bleues": "bleue", "vertes": "verte", "jaunes": "jaune", "noires": "noire"}


def _evenement(rng, n):
    """(libellé, issues favorables) d'un événement sur les entiers 1..n."""
    sorte = rng.choice(("multiple", "superieur", "inferieur", "diviseur"))
    if sorte == "multiple":
        k = rng.randint(2, 5)
        return f"obtenir un multiple de ${k}$", [x for x in range(1, n + 1) if x % k == 0]
    if sorte == "superieur":
        k = rng.randint(2, n - 2)
        return f"obtenir un nombre strictement supérieur à ${k}$", list(range(k + 1, n + 1))
    if sorte == "inferieur":
        k = rng.randint(2, n - 2)
        return f"obtenir un nombre inférieur ou égal à ${k}$", list(range(1, k + 1))
    m = rng.choice((12, 18, 20, 24, 30, 36))
    return f"obtenir un diviseur de ${m}$", [x for x in range(1, n + 1) if m % x == 0]


def _liste(xs):
    return ", ".join(f"${x}$" for x in xs)


def _gen_issues(rng: random.Random) -> Optional[dict]:
    n = rng.randint(6, 20)
    libelle, fav = _evenement(rng, n)
    if not 0 < len(fav) < n:
        return None
    return {
        "enonce": f"Une roue équilibrée a ${n}$ secteurs identiques numérotés de $1$ à ${n}$. Lister les issues qui réalisent l'événement « {libelle} ».",
        "answer": f"Issues favorables : {_liste(fav)}, soit ${len(fav)}$ issues.",
        "hint": f"Passe en revue les nombres de $1$ à ${n}$.",
        "steps": [f"Les issues possibles sont les entiers de $1$ à ${n}$.",
                  f"Celles qui réalisent l'événement : {_liste(fav)}.",
                  f"Il y en a ${len(fav)}$."],
        "notion": N1,
    }


def _gen_proba_roue(rng: random.Random) -> Optional[dict]:
    n = rng.randint(6, 20)
    libelle, fav = _evenement(rng, n)
    if not 0 < len(fav) < n:
        return None
    p = Fraction(len(fav), n)
    simplif = f" = {frac(p)}" if p.denominator != n else ""
    return {
        "enonce": f"On fait tourner une roue équilibrée à ${n}$ secteurs identiques numérotés de $1$ à ${n}$. Quelle est la probabilité de l'événement « {libelle} » ?",
        "answer": f"$P = {frac(p)}$.",
        "hint": "Probabilité = nombre d'issues favorables ÷ nombre d'issues possibles.",
        "steps": [f"Issues favorables : {_liste(fav)}, soit ${len(fav)}$.",
                  f"Issues possibles : ${n}$, toutes équiprobables.",
                  f"$P = \\dfrac{{{len(fav)}}}{{{n}}}{simplif}$."],
        "notion": N2,
    }


def _urne(rng):
    k = rng.randint(2, 3)
    couleurs = rng.sample(_COULEURS, k)
    effectifs = [rng.randint(1, 12) for _ in couleurs]
    texte = ", ".join(f"${e}$ boules {c}" for e, c in zip(effectifs[:-1], couleurs[:-1]))
    texte += f" et ${effectifs[-1]}$ boules {couleurs[-1]}"
    return couleurs, effectifs, texte


def _gen_proba_urne(rng: random.Random) -> Optional[dict]:
    couleurs, effectifs, texte = _urne(rng)
    i = rng.randrange(len(couleurs))
    total = sum(effectifs)
    p = Fraction(effectifs[i], total)
    simplif = f" = {frac(p)}" if p.denominator != total else ""
    return {
        "enonce": f"Une urne contient {texte}, indiscernables au toucher. On tire une boule au hasard. Quelle est la probabilité de tirer une boule {_SINGULIER[couleurs[i]]} ?",
        "answer": f"$P = {frac(p)}$.",
        "hint": "Compte d'abord le nombre total de boules.",
        "steps": [f"Nombre total de boules : ${' + '.join(map(str, effectifs))} = {total}$.",
                  f"Boules {couleurs[i]} : ${effectifs[i]}$.",
                  f"$P = \\dfrac{{{effectifs[i]}}}{{{total}}}{simplif}$."],
        "notion": N2,
    }


_CONTEXTES = ("qu'il pleuve demain", "qu'un joueur marque son penalty", "qu'une ampoule tombe en panne avant un an",
              "qu'un train arrive à l'heure", "qu'un élève choisi au hasard soit externe", "qu'une graine germe")


def _gen_contraire_decimal(rng: random.Random) -> Optional[dict]:
    p = Fraction(rng.randint(1, 99), 100)
    contexte = rng.choice(_CONTEXTES)
    return {
        "enonce": f"La probabilité {contexte} est ${num(p)}$. Quelle est la probabilité de l'événement contraire ?",
        "answer": f"La probabilité de l'événement contraire est ${num(1 - p)}$.",
        "hint": "$P(\\text{non } A) = 1 - P(A)$.",
        "steps": [f"$1 - {num(p)} = {num(1 - p)}$."],
        "notion": N3,
    }


def _gen_contraire_urne(rng: random.Random) -> Optional[dict]:
    couleurs, effectifs, texte = _urne(rng)
    i = rng.randrange(len(couleurs))
    total = sum(effectifs)
    p = Fraction(effectifs[i], total)
    return {
        "enonce": f"Une urne contient {texte}. On tire une boule au hasard. Quelle est la probabilité de ne pas tirer une boule {_SINGULIER[couleurs[i]]} ?",
        "answer": f"$P = {frac(1 - p)}$.",
        "hint": "Calcule la probabilité de tirer cette couleur, puis utilise l'événement contraire.",
        "steps": [f"$P(\\text{{{_SINGULIER[couleurs[i]]}}}) = \\dfrac{{{effectifs[i]}}}{{{total}}}$.",
                  f"$P(\\text{{non {_SINGULIER[couleurs[i]]}}}) = 1 - \\dfrac{{{effectifs[i]}}}{{{total}}} = {frac(1 - p)}$."],
        "notion": N3,
    }


def _gen_proba_manquante(rng: random.Random) -> Optional[dict]:
    objet, faces = rng.choice((("un osselet", 4), ("un dé truqué à six faces", 6)))
    probas = [Fraction(rng.randint(5, 30), 100) for _ in range(faces - 1)]
    reste = 1 - sum(probas)
    if reste <= 0:
        return None
    donnees = " ; ".join(f"$P({k}) = {num(q)}$" for k, q in enumerate(probas, 1))
    return {
        "enonce": f"On lance {objet} dont les faces sont numérotées de $1$ à ${faces}$. On connaît : {donnees}. Calculer $P({faces})$.",
        "answer": f"$P({faces}) = {num(reste)}$.",
        "hint": "La somme des probabilités de toutes les issues vaut $1$.",
        "steps": [f"Somme des probabilités connues : ${' + '.join(num(q) for q in probas)} = {num(sum(probas))}$.",
                  f"$P({faces}) = 1 - {num(sum(probas))} = {num(reste)}$."],
        "notion": N4,
    }


def _gen_roue_angles(rng: random.Random) -> Optional[dict]:
    pas = rng.choice((10, 15, 20, 30))
    a, b = rng.randint(1, 360 // pas - 2) * pas, rng.randint(1, 360 // pas - 2) * pas
    if a + b >= 360:
        return None
    c = 360 - a - b
    cible = rng.choice(("rouge", "bleu", "vert"))
    angle = {"rouge": a, "bleu": b, "vert": c}[cible]
    p = Fraction(angle, 360)
    calc_vert = [f"Angle du secteur vert : $360° - {a}° - {b}° = {c}°$."] if cible == "vert" else []
    return {
        "enonce": f"Une roue est partagée en trois secteurs : rouge (${a}°$), bleu (${b}°$) et vert (le reste). Quelle est la probabilité que l'aiguille s'arrête sur le {cible} ?",
        "answer": f"$P = {frac(p)}$.",
        "hint": "La probabilité est proportionnelle à l'angle du secteur.",
        "steps": calc_vert + [f"$P = \\dfrac{{{angle}}}{{360}} = {frac(p)}$."],
        "notion": N4,
    }


def _gen_cible_carres(rng: random.Random) -> Optional[dict]:
    a = rng.randint(4, 20)
    b = rng.randint(1, a - 1)
    zone = rng.choice(("centre", "bord"))
    p = Fraction(b * b, a * a) if zone == "centre" else 1 - Fraction(b * b, a * a)
    question = "le carré central" if zone == "centre" else "la zone située hors du carré central"
    favorable = f"{b * b}" if zone == "centre" else f"{a * a} - {b * b} = {a * a - b * b}"
    return {
        "enonce": (f"Une cible carrée de côté ${a}$ cm contient en son centre un carré de côté ${b}$ cm. "
                   f"Une fléchette atteint la cible en un point au hasard. Quelle est la probabilité qu'elle atteigne {question} ?"),
        "answer": f"$P = {frac(p)}$.",
        "hint": "La probabilité est le quotient de l'aire de la zone par l'aire de la cible.",
        "steps": [f"Aire de la cible : ${a}^2 = {a * a}$ cm², aire du carré central : ${b}^2 = {b * b}$ cm².",
                  f"Aire de la zone : ${favorable}$ cm².",
                  f"$P = {frac(p)}$."],
        "notion": N4,
    }


FAMILIES_LIST = (
    Family("issues_evenement", 1, "Issues réalisant un événement", N1, _gen_issues,
           "une roue numérotée et un événement", "lister les issues"),
    Family("proba_roue", 1, "Probabilité sur une roue numérotée", N2, _gen_proba_roue,
           "une roue équilibrée", "favorables / possibles"),
    Family("proba_urne", 1, "Probabilité dans une urne", N2, _gen_proba_urne,
           "une urne de boules colorées", "favorables / possibles"),
    Family("contraire_decimal", 1, "Événement contraire", N3, _gen_contraire_decimal,
           "une probabilité décimale", "1 − P(A)"),
    Family("contraire_urne", 2, "Ne pas tirer une couleur", N3, _gen_contraire_urne,
           "une urne", "événement contraire"),
    Family("proba_manquante", 2, "Probabilité manquante", N4, _gen_proba_manquante,
           "des issues non équiprobables", "somme des probabilités = 1"),
    Family("roue_angles", 2, "Roue à secteurs inégaux", N4, _gen_roue_angles,
           "des angles de secteurs", "angle / 360"),
    Family("cible_carres", 3, "Cible et aires", N4, _gen_cible_carres,
           "deux carrés emboîtés", "quotient d'aires"),
)

CHAPTER = Chapter(17, FAMILIES_LIST)
CHAPTER_ID = CHAPTER.chapter_id
FAMILIES = CHAPTER.families
GENERATED_ID_OFFSET = CHAPTER.id_offset
generate_one = CHAPTER.generate_one
generate_pool = CHAPTER.generate_pool
