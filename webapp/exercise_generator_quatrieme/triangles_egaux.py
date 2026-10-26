"""Chapitre 12 — Triangles égaux (générateurs).

    cotes_homologues   N1  côté homologue selon une correspondance de sommets
    reporter_angle     N1  angle homologue (éventuellement le troisième angle)
    perimetre_egal     N1  troisième côté grâce au périmètre commun
    reconnaitre_cas    N2  CCC, CAC, ACA, ou impossibilité de conclure
    milieu_commun      N3  diagonales qui se coupent en leur milieu : AB = CD
    mediatrice_calcul  N3  point de la médiatrice : MA = MB, puis Pythagore
"""
import random
from typing import Optional

from ._commun import Chapter, Family

N1 = "Triangles égaux : définition et éléments homologues"
N2 = "Les trois cas d'égalité des triangles"
N3 = "Démontrer avec des triangles égaux"

_ALPHABET = "ABCDEFGHIJKLMNPRSTUVWXYZ"
_TRIPLETS = ((3, 4, 5), (5, 12, 13), (6, 8, 10), (8, 15, 17), (7, 24, 25), (9, 12, 15), (12, 16, 20), (20, 21, 29))


def _deux_triangles(rng):
    lettres = rng.sample(_ALPHABET, 6)
    t1, t2 = lettres[:3], lettres[3:]
    perm = list(range(3))
    rng.shuffle(perm)
    corr = {t1[i]: t2[perm[i]] for i in range(3)}
    return t1, t2, corr


def _corr_txt(t1, corr):
    return ", ".join(f"${a} \\to {corr[a]}$" for a in t1)


def _gen_cotes_homologues(rng: random.Random) -> Optional[dict]:
    t1, t2, corr = _deux_triangles(rng)
    i, j = rng.sample(range(3), 2)
    a, b = t1[i], t1[j]
    return {
        "enonce": (f"Les triangles ${''.join(t1)}$ et ${''.join(t2)}$ sont égaux, avec {_corr_txt(t1, corr)}. "
                   f"Quel côté du triangle ${''.join(t2)}$ a la même longueur que $[{a}{b}]$ ?"),
        "answer": f"Le côté $[{corr[a]}{corr[b]}]$ : ${a}{b} = {corr[a]}{corr[b]}$.",
        "hint": "Remplace chaque sommet par son homologue.",
        "steps": [f"${a} \\to {corr[a]}$ et ${b} \\to {corr[b]}$.",
                  f"L'homologue de $[{a}{b}]$ est $[{corr[a]}{corr[b]}]$."],
        "notion": N1,
    }


def _gen_reporter_angle(rng: random.Random) -> Optional[dict]:
    t1, t2, corr = _deux_triangles(rng)
    a1, a2 = rng.randint(20, 110), rng.randint(15, 100)
    if a1 + a2 >= 170:
        return None
    a3 = 180 - a1 - a2
    angles = dict(zip(t1, (a1, a2, a3)))
    cible = rng.choice(t1)                 # sommet de t1 dont on cherche l'homologue
    connus = [s for s in t1 if s != cible] if rng.random() < 0.5 else [s for s in t1 if s != t1[2]]
    donnees = " et ".join(f"$\\widehat{{{s}}} = {angles[s]}°$" for s in connus)
    steps = []
    if cible not in connus:
        steps.append(f"Dans ${''.join(t1)}$ : $\\widehat{{{cible}}} = 180 - {angles[connus[0]]} - {angles[connus[1]]} = {angles[cible]}°$.")
    steps.append(f"$\\widehat{{{corr[cible]}}}$ est l'angle homologue de $\\widehat{{{cible}}}$ : il mesure ${angles[cible]}°$.")
    return {
        "enonce": (f"Les triangles ${''.join(t1)}$ et ${''.join(t2)}$ sont égaux, avec {_corr_txt(t1, corr)}. "
                   f"On sait que {donnees}. Calculer $\\widehat{{{corr[cible]}}}$."),
        "answer": f"$\\widehat{{{corr[cible]}}} = {angles[cible]}°$.",
        "hint": "Trouve l'angle homologue dans le premier triangle (somme des angles $180°$ si besoin).",
        "steps": steps,
        "notion": N1,
    }


def _gen_perimetre(rng: random.Random) -> Optional[dict]:
    t1, t2, corr = _deux_triangles(rng)
    a, b, c = (rng.randint(3, 25) for _ in range(3))
    if not (a + b > c and a + c > b and b + c > a):
        return None
    cotes = {(t1[0], t1[1]): a, (t1[1], t1[2]): b, (t1[0], t1[2]): c}
    p = a + b + c
    (x1, y1), (x2, y2), (x3, y3) = cotes
    return {
        "enonce": (f"Les triangles ${''.join(t1)}$ et ${''.join(t2)}$ sont égaux, avec {_corr_txt(t1, corr)}. "
                   f"${x1}{y1} = {a}$ cm, ${x2}{y2} = {b}$ cm et le périmètre de ${''.join(t2)}$ vaut ${p}$ cm. Calculer ${corr[x3]}{corr[y3]}$."),
        "answer": f"${corr[x3]}{corr[y3]} = {c}$ cm.",
        "hint": "Deux triangles égaux ont le même périmètre.",
        "steps": [f"Périmètre de ${''.join(t1)}$ : ${p}$ cm aussi.",
                  f"${x3}{y3} = {p} - {a} - {b} = {c}$ cm.",
                  f"$[{corr[x3]}{corr[y3]}]$ est homologue de $[{x3}{y3}]$ : ${corr[x3]}{corr[y3]} = {c}$ cm."],
        "notion": N1,
    }


_CAS = {"CCC": "côté – côté – côté", "CAC": "côté – angle – côté", "ACA": "angle – côté – angle"}


def _gen_reconnaitre(rng: random.Random) -> Optional[dict]:
    l = rng.sample(_ALPHABET, 6)
    A, B, C, D, E, F = l
    t1, t2 = A + B + C, D + E + F            # correspondance dans l'ordre : A→D, B→E, C→F
    scenario = rng.choice(("CCC", "CAC", "ACA", "ACA_calcul", "AAA", "non_compris", "CCC_diff"))
    a, b, c = rng.randint(3, 12), rng.randint(3, 12), rng.randint(3, 12)
    if not (a + b > c and a + c > b and b + c > a):
        return None
    angA, angB = rng.randint(25, 85), rng.randint(25, 85)
    angC = 180 - angA - angB
    if scenario == "CCC":
        d1 = f"${A}{B} = {a}$, ${B}{C} = {b}$, ${A}{C} = {c}$"
        d2 = f"${D}{E} = {a}$, ${E}{F} = {b}$, ${D}{F} = {c}$"
        answer, why = f"Oui, d'après le cas {_CAS['CCC']}.", "Les trois côtés sont égaux deux à deux."
    elif scenario == "CCC_diff":
        d1 = f"${A}{B} = {a}$, ${B}{C} = {b}$, ${A}{C} = {c}$"
        c2 = c + rng.choice((-1, 1)) if c > 3 else c + 1
        if not (a + b > c2 and a + c2 > b and b + c2 > a):
            return None
        d2 = f"${D}{E} = {a}$, ${E}{F} = {b}$, ${D}{F} = {c2}$"
        answer, why = f"Non : ${A}{C} \\neq {D}{F}$, les triangles ne sont pas égaux.", "Deux triangles égaux auraient leurs trois côtés égaux."
    elif scenario == "CAC":
        d1 = f"${A}{B} = {a}$, ${A}{C} = {c}$, $\\widehat{{{A}}} = {angA}°$"
        d2 = f"${D}{E} = {a}$, ${D}{F} = {c}$, $\\widehat{{{D}}} = {angA}°$"
        answer, why = f"Oui, d'après le cas {_CAS['CAC']}.", f"L'angle en ${A}$ (et en ${D}$) est compris entre les deux côtés égaux."
    elif scenario == "non_compris":
        d1 = f"${A}{B} = {a}$, ${A}{C} = {c}$, $\\widehat{{{B}}} = {angB}°$"
        d2 = f"${D}{E} = {a}$, ${D}{F} = {c}$, $\\widehat{{{E}}} = {angB}°$"
        answer, why = "On ne peut pas conclure : l'angle donné n'est pas compris entre les deux côtés égaux.", "Aucun cas d'égalité ne s'applique."
    elif scenario == "ACA":
        d1 = f"${B}{C} = {b}$, $\\widehat{{{B}}} = {angB}°$, $\\widehat{{{C}}} = {angC}°$"
        d2 = f"${E}{F} = {b}$, $\\widehat{{{E}}} = {angB}°$, $\\widehat{{{F}}} = {angC}°$"
        answer, why = f"Oui, d'après le cas {_CAS['ACA']}.", "Les angles donnés sont aux extrémités du côté égal."
    elif scenario == "ACA_calcul":
        d1 = f"${B}{C} = {b}$, $\\widehat{{{B}}} = {angB}°$, $\\widehat{{{C}}} = {angC}°$"
        d2 = f"${E}{F} = {b}$, $\\widehat{{{E}}} = {angB}°$, $\\widehat{{{D}}} = {angA}°$"
        answer = f"Oui : $\\widehat{{{F}}} = 180 - {angB} - {angA} = {angC}°$, puis cas {_CAS['ACA']}."
        why = f"Le troisième angle de ${t2}$ est égal à $\\widehat{{{C}}}$."
    else:  # AAA
        d1 = f"$\\widehat{{{A}}} = {angA}°$, $\\widehat{{{B}}} = {angB}°$, $\\widehat{{{C}}} = {angC}°$"
        d2 = f"$\\widehat{{{D}}} = {angA}°$, $\\widehat{{{E}}} = {angB}°$, $\\widehat{{{F}}} = {angC}°$"
        answer, why = "On ne peut pas conclure : trois angles égaux ne suffisent pas.", "Les triangles ont la même forme mais pas forcément la même taille."
    return {
        "enonce": f"Dans le triangle ${t1}$ : {d1}. Dans le triangle ${t2}$ : {d2}. Les triangles ${t1}$ et ${t2}$ sont-ils égaux ?",
        "answer": answer,
        "hint": "Repère les côtés et angles égaux, et la position des angles par rapport aux côtés.",
        "steps": [f"Éléments égaux : comparer ${t1}$ et ${t2}$ avec ${A} \\to {D}$, ${B} \\to {E}$, ${C} \\to {F}$.", why, answer],
        "notion": N2,
    }


def _gen_milieu(rng: random.Random) -> Optional[dict]:
    A, B, C, D, O = rng.sample(_ALPHABET, 5)
    x = rng.randint(20, 150) / 10
    xs = f"{x:g}".replace(".", "{,}")
    return {
        "enonce": (f"Les segments $[{A}{C}]$ et $[{B}{D}]$ se coupent en leur milieu ${O}$, et ${A}{B} = {xs}$ cm. "
                   f"Démontrer que les triangles ${A}{O}{B}$ et ${C}{O}{D}$ sont égaux, puis donner ${C}{D}$."),
        "answer": f"Les triangles sont égaux (cas côté – angle – côté), donc ${C}{D} = {A}{B} = {xs}$ cm.",
        "hint": "Pense au milieu et aux angles opposés par le sommet.",
        "steps": [f"${O}{A} = {O}{C}$ et ${O}{B} = {O}{D}$ (${O}$ milieu des deux segments).",
                  f"$\\widehat{{{A}{O}{B}}} = \\widehat{{{C}{O}{D}}}$ (angles opposés par le sommet).",
                  f"Cas côté – angle – côté : les triangles sont égaux, donc ${C}{D} = {A}{B} = {xs}$ cm."],
        "notion": N3,
    }


def _gen_mediatrice(rng: random.Random) -> Optional[dict]:
    A, B, H, M = rng.sample(_ALPHABET, 4)
    p, q, r = rng.choice(_TRIPLETS)
    if rng.random() < 0.5:
        p, q = q, p
    return {
        "enonce": (f"${H}$ est le milieu de $[{A}{B}]$ et ${M}$ est un point de la perpendiculaire à $({A}{B})$ passant par ${H}$. "
                   f"On donne ${A}{H} = {p}$ cm et ${H}{M} = {q}$ cm. Démontrer que ${M}{A} = {M}{B}$, puis calculer ${M}{B}$."),
        "answer": f"Les triangles ${A}{H}{M}$ et ${B}{H}{M}$ sont égaux (cas côté – angle – côté), donc ${M}{A} = {M}{B}$ ; ${M}{B} = {r}$ cm.",
        "hint": "Triangles égaux, puis théorème de Pythagore dans le triangle rectangle en $" + H + "$.",
        "steps": [f"${A}{H} = {B}{H}$ (milieu), $\\widehat{{{A}{H}{M}}} = \\widehat{{{B}{H}{M}}} = 90°$, $[{H}{M}]$ commun : cas côté – angle – côté.",
                  f"Donc ${M}{A} = {M}{B}$.",
                  f"Pythagore : ${M}{A}^2 = {p}^2 + {q}^2 = {p * p + q * q}$, donc ${M}{A} = {M}{B} = {r}$ cm."],
        "notion": N3,
    }


FAMILIES_LIST = (
    Family("cotes_homologues", 1, "Côtés homologues", N1, _gen_cotes_homologues,
           "une correspondance de sommets", "remplacer chaque sommet"),
    Family("reporter_angle", 2, "Angles homologues", N1, _gen_reporter_angle,
           "deux angles connus", "somme des angles et report"),
    Family("perimetre_egal", 2, "Périmètre de triangles égaux", N1, _gen_perimetre,
           "deux côtés et un périmètre", "même périmètre"),
    Family("reconnaitre_cas", 2, "Reconnaître un cas d'égalité", N2, _gen_reconnaitre,
           "des côtés et des angles", "CCC, CAC, ACA"),
    Family("milieu_commun", 2, "Segments de même milieu", N3, _gen_milieu,
           "une configuration en X", "angles opposés par le sommet"),
    Family("mediatrice_calcul", 3, "Médiatrice et Pythagore", N3, _gen_mediatrice,
           "un point de la médiatrice", "CAC puis Pythagore"),
)

CHAPTER = Chapter(12, FAMILIES_LIST)
CHAPTER_ID = CHAPTER.chapter_id
FAMILIES = CHAPTER.families
GENERATED_ID_OFFSET = CHAPTER.id_offset
generate_one = CHAPTER.generate_one
generate_pool = CHAPTER.generate_pool
