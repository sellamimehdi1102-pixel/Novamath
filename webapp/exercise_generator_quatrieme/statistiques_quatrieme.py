"""Chapitre 16 — Statistiques (générateurs). Nom distinct de exercise_generator_troisieme.statistiques.

    angles_diagramme       N1  angles d'un diagramme circulaire à partir des effectifs
    effectif_depuis_angle  N1  effectif d'une catégorie à partir de son angle
    frequence_pourcentage  N1  fréquence d'une catégorie en pourcentage
    mediane_liste          N2  médiane d'une liste (effectif pair ou impair, ≤ 15)
    mediane_tableau        N2  médiane à partir d'un tableau d'effectifs (total ≤ 30)
    moyenne_tableau        N3  moyenne à partir d'un tableau d'effectifs
    comparer_frequences    N3  comparer deux groupes d'effectifs différents
"""
import random
from fractions import Fraction
from typing import Optional

from ._commun import Chapter, Family, grp

N1 = "Diagrammes circulaires"
N2 = "Médiane d'une série statistique"
N3 = "Comparer et interpréter des séries"

_DIVISEURS_360 = (12, 15, 18, 20, 24, 30, 36, 40, 45, 60, 72, 90, 120)
_CATEGORIES = (("à pied", "en bus", "à vélo", "en voiture", "en train"),
               ("football", "basket", "natation", "tennis", "danse"),
               ("pomme", "poire", "banane", "orange", "kiwi"),
               ("rouge", "bleu", "vert", "jaune", "noir"))


def _decomposer(rng, total, k):
    """k effectifs strictement positifs de somme total."""
    if total < k:
        return None
    coupes = sorted(rng.sample(range(1, total), k - 1))
    parts = [b - a for a, b in zip([0] + coupes, coupes + [total])]
    return parts


def _gen_angles(rng: random.Random) -> Optional[dict]:
    total = rng.choice(_DIVISEURS_360)
    k = rng.randint(3, 5)
    eff = _decomposer(rng, total, k)
    if eff is None:
        return None
    cats = rng.choice(_CATEGORIES)[:k]
    unite = 360 // total
    angles = [e * unite for e in eff]
    donnees = ", ".join(f"{c} : ${e}$" for c, e in zip(cats, eff))
    return {
        "enonce": f"Une enquête auprès de ${total}$ personnes donne les effectifs suivants : {donnees}. Calculer l'angle de chaque secteur du diagramme circulaire.",
        "answer": "Angles : " + ", ".join(f"{c} ${a}°$" for c, a in zip(cats, angles)) + ".",
        "hint": "Un individu correspond à $360° \\div$ effectif total.",
        "steps": [f"$360 \\div {total} = {unite}°$ par personne.",
                  " ; ".join(f"${e} \\times {unite} = {a}°$" for e, a in zip(eff, angles)) + ".",
                  f"Vérification : la somme des angles vaut ${sum(angles)}°$."],
        "notion": N1,
    }


def _gen_effectif(rng: random.Random) -> Optional[dict]:
    total = rng.choice((40, 60, 72, 80, 90, 120, 180, 240, 360, 600, 720))
    angle = rng.randint(1, 35) * 10
    eff = Fraction(angle * total, 360)
    if eff.denominator != 1 or angle >= 360:
        return None
    return {
        "enonce": f"Dans un diagramme circulaire représentant ${total}$ personnes, un secteur mesure ${angle}°$. Combien de personnes représente-t-il ?",
        "answer": f"Il représente ${eff}$ personnes.",
        "hint": "L'effectif est proportionnel à l'angle.",
        "steps": [f"$\\dfrac{{{angle}}}{{360}} \\times {total} = {eff}$."],
        "notion": N1,
    }


def _gen_frequence(rng: random.Random) -> Optional[dict]:
    total = rng.choice((20, 25, 40, 50, 80, 125, 200, 250, 400, 500))
    e = rng.randint(1, total - 1)
    f = Fraction(100 * e, total)
    if f.denominator not in (1, 2, 4, 5, 10):
        return None
    sujet = rng.choice(("élèves", "spectateurs", "clients", "joueurs", "votants"))
    return {
        "enonce": f"Parmi ${total}$ {sujet}, ${e}$ ont répondu « oui ». Quelle est la fréquence de la réponse « oui », en pourcentage ?",
        "answer": f"La fréquence est ${grp(f)}\\,\\%$.",
        "hint": "Fréquence = effectif ÷ effectif total.",
        "steps": [f"$\\dfrac{{{e}}}{{{total}}} = {grp(Fraction(e, total))}$.", f"Soit ${grp(f)}\\,\\%$."],
        "notion": N1,
    }


def _mediane(v):
    v = sorted(v)
    n = len(v)
    return Fraction(v[n // 2]) if n % 2 else Fraction(v[n // 2 - 1] + v[n // 2], 2)


def _gen_mediane_liste(rng: random.Random) -> Optional[dict]:
    n = rng.randint(5, 15)
    vals = [rng.randint(0, 20) for _ in range(n)]
    m = _mediane(vals)
    rangees = sorted(vals)
    rang = f"la ${(n + 1) // 2}^e$ valeur" if n % 2 else f"la moyenne des ${n // 2}^e$ et ${n // 2 + 1}^e$ valeurs"
    contexte = rng.choice(("Notes", "Temps (en min)", "Scores", "Âges", "Pointages"))
    return {
        "enonce": f"{contexte} de ${n}$ personnes : {' ; '.join(f'${v}$' for v in vals)}. Déterminer la médiane.",
        "answer": f"La médiane est ${grp(m)}$.",
        "hint": "Range les valeurs, puis cherche la (ou les) valeur(s) du milieu.",
        "steps": [f"Série rangée : {' ; '.join(f'${v}$' for v in rangees)}.",
                  f"Effectif ${n}$ ({'impair' if n % 2 else 'pair'}) : médiane $=$ {rang}.",
                  f"Médiane : ${grp(m)}$."],
        "notion": N2,
    }


def _gen_mediane_tableau(rng: random.Random) -> Optional[dict]:
    k = rng.randint(4, 6)
    valeurs = sorted(rng.sample(range(0, 20), k))
    eff = [rng.randint(1, 7) for _ in range(k)]
    n = sum(eff)
    if n > 30:
        return None
    serie = [v for v, e in zip(valeurs, eff) for _ in range(e)]
    m = _mediane(serie)
    cumul, c = [], 0
    for e in eff:
        c += e
        cumul.append(c)
    tableau = " ; ".join(f"${v}$ ({e})" for v, e in zip(valeurs, eff))
    return {
        "enonce": f"Une série est donnée par ses valeurs et leurs effectifs (entre parenthèses) : {tableau}. Déterminer la médiane.",
        "answer": f"La médiane est ${grp(m)}$.",
        "hint": "Calcule l'effectif total et les effectifs cumulés.",
        "steps": [f"Effectif total : ${n}$.",
                  "Effectifs cumulés : " + " ; ".join(f"${v} \\to {c}$" for v, c in zip(valeurs, cumul)) + ".",
                  f"Médiane : ${grp(m)}$."],
        "notion": N2,
    }


def _gen_moyenne_tableau(rng: random.Random) -> Optional[dict]:
    k = rng.randint(3, 5)
    valeurs = sorted(rng.sample(range(0, 20), k))
    eff = [rng.randint(1, 8) for _ in range(k)]
    n = sum(eff)
    s = sum(v * e for v, e in zip(valeurs, eff))
    m = Fraction(s, n)
    if m.denominator not in (1, 2, 4, 5, 10, 20, 25):
        return None
    tableau = " ; ".join(f"${v}$ ({e})" for v, e in zip(valeurs, eff))
    return {
        "enonce": f"Une série est donnée par ses valeurs et leurs effectifs (entre parenthèses) : {tableau}. Calculer la moyenne.",
        "answer": f"La moyenne est ${grp(m)}$.",
        "hint": "Multiplie chaque valeur par son effectif, additionne, puis divise par l'effectif total.",
        "steps": ["Somme : " + " + ".join(f"{v} \\times {e}" for v, e in zip(valeurs, eff)).join(("$", "$")) + f" $= {s}$.",
                  f"Effectif total : ${n}$.", f"Moyenne : $\\dfrac{{{s}}}{{{n}}} = {grp(m)}$."],
        "notion": N3,
    }


def _gen_comparer(rng: random.Random) -> Optional[dict]:
    n1, n2 = rng.choice((20, 25, 40, 50, 80)), rng.choice((20, 25, 40, 50, 80))
    if n1 == n2:
        return None
    e1, e2 = rng.randint(1, n1 - 1), rng.randint(1, n2 - 1)
    f1, f2 = Fraction(100 * e1, n1), Fraction(100 * e2, n2)
    if f1 == f2 or f1.denominator > 10 or f2.denominator > 10:
        return None
    grand = "A" if f1 > f2 else "B"
    return {
        "enonce": (f"Dans le groupe A, ${e1}$ personnes sur ${n1}$ pratiquent un instrument ; dans le groupe B, ${e2}$ sur ${n2}$. "
                   "Dans quel groupe la proportion de musiciens est-elle la plus grande ?"),
        "answer": f"Dans le groupe {grand} : A ${grp(f1)}\\,\\%$ et B ${grp(f2)}\\,\\%$.",
        "hint": "Compare des pourcentages, pas des effectifs.",
        "steps": [f"A : $\\dfrac{{{e1}}}{{{n1}}} = {grp(f1)}\\,\\%$.", f"B : $\\dfrac{{{e2}}}{{{n2}}} = {grp(f2)}\\,\\%$.",
                  f"La proportion est plus grande dans le groupe {grand}."],
        "notion": N3,
    }


FAMILIES_LIST = (
    Family("angles_diagramme", 1, "Angles d'un diagramme circulaire", N1, _gen_angles,
           "des effectifs", "angle = effectif × 360 / total"),
    Family("effectif_depuis_angle", 2, "Effectif à partir d'un angle", N1, _gen_effectif,
           "un angle et un total", "proportionnalité"),
    Family("frequence_pourcentage", 1, "Fréquence en pourcentage", N1, _gen_frequence,
           "un effectif et un total", "effectif / total"),
    Family("mediane_liste", 1, "Médiane d'une liste", N2, _gen_mediane_liste,
           "une liste de valeurs", "ranger puis milieu"),
    Family("mediane_tableau", 2, "Médiane d'un tableau", N2, _gen_mediane_tableau,
           "valeurs et effectifs", "effectifs cumulés"),
    Family("moyenne_tableau", 2, "Moyenne d'un tableau", N3, _gen_moyenne_tableau,
           "valeurs et effectifs", "somme des produits / total"),
    Family("comparer_frequences", 2, "Comparer deux groupes", N3, _gen_comparer,
           "deux groupes de tailles différentes", "pourcentages"),
)

CHAPTER = Chapter(16, FAMILIES_LIST)
CHAPTER_ID = CHAPTER.chapter_id
FAMILIES = CHAPTER.families
GENERATED_ID_OFFSET = CHAPTER.id_offset
generate_one = CHAPTER.generate_one
generate_pool = CHAPTER.generate_pool
