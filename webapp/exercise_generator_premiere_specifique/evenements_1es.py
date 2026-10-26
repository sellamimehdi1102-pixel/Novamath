"""Chapitre 8 de la Première spécifique (manuel « Première ES/L ») — rappels de
probabilités sur les événements : contraire, réunion, intersection, lois de
De Morgan. La famille « tableau croisé » du module automatismes est rattachée
à la même notion par programme_1es.py.
Créé lors de l'adaptation du 2026-10-26 ; contrat : voir _commun_1es.py.
"""
from fractions import Fraction as F
from typing import Optional

from exercise_generator_premiere_specifique import _commun_1es as c
from exercise_generator_premiere_specifique._commun_1es import Family, dec, frac

CHAPTER_ID = "Chapitre_8"
N_EVT = "Rappels de probabilités : événements"
GENERATED_ID_OFFSET = 1_230_000
LEVEL_META = c.LEVEL_META


def _p(rng, lo=5, hi=95):
    return F(rng.randrange(lo, hi + 1, 5), 100)


def _gen_contraire(rng):
    p = F(rng.randint(1, 99), 100)
    situation = rng.choice(["qu'un appareil tombe en panne dans l'année", "qu'un train soit en retard", "qu'un candidat réussisse un concours",
                            "qu'il pleuve demain", "qu'une pièce soit défectueuse"])
    return dict(enonce=f"La probabilité {situation} est ${dec(p)}$. Quelle est la probabilité de l'événement contraire ?",
                answer=f"La probabilité de l'événement contraire est ${dec(1 - p)}$.",
                hint="$P(\\overline{A}) = 1 - P(A)$.",
                steps=[f"$P(\\overline{{A}}) = 1 - P(A) = 1 - {dec(p)}$.", f"$P(\\overline{{A}}) = {dec(1 - p)}$."])


def _gen_de_issues(rng):
    k = rng.choice([2, 3])
    m = rng.choice([2, 3, 4, 5])
    au_plus = rng.random() < 0.5
    a = {x for x in range(1, 7) if x % k == 0}
    b = {x for x in range(1, m + 1)} if au_plus else {x for x in range(m, 7)}
    u, i = sorted(a | b), sorted(a & b)
    nom_a = "obtenir un nombre pair" if k == 2 else "obtenir un multiple de $3$"
    nom_b = f"obtenir au plus ${m}$" if au_plus else f"obtenir au moins ${m}$"

    def ens(s):
        return "\\{" + " ; ".join(map(str, s)) + "\\}" if s else "\\varnothing"

    return dict(enonce=f"On lance un dé équilibré à six faces. $A$ : « {nom_a} », $B$ : « {nom_b} ». Décrire $A \\cap B$ et $A \\cup B$, puis calculer $P(A \\cup B)$.",
                answer=f"$A \\cap B = {ens(i)}$, $A \\cup B = {ens(u)}$ et $P(A \\cup B) = {frac(F(len(u), 6))}$.",
                hint="Écris d'abord les issues de $A$ et de $B$.",
                steps=[f"$A = {ens(sorted(a))}$ et $B = {ens(sorted(b))}$.", f"$A \\cap B = {ens(i)}$ et $A \\cup B = {ens(u)}$.",
                       f"$P(A \\cup B) = \\dfrac{{{len(u)}}}{{6}} = {frac(F(len(u), 6))}$."])


def _gen_reunion_formule(rng):
    pa, pb = _p(rng, 10, 70), _p(rng, 10, 70)
    pab = _p(rng, 5, 40)
    if pab > min(pa, pb) or pa + pb - pab > 1:
        return None
    r = pa + pb - pab
    return dict(enonce=f"On donne $P(A) = {dec(pa)}$, $P(B) = {dec(pb)}$ et $P(A \\cap B) = {dec(pab)}$. Calculer $P(A \\cup B)$.",
                answer=f"$P(A \\cup B) = {dec(r)}$.",
                hint="Utilise la formule de la réunion.",
                steps=["$P(A \\cup B) = P(A) + P(B) - P(A \\cap B)$.", f"$P(A \\cup B) = {dec(pa)} + {dec(pb)} - {dec(pab)} = {dec(r)}$."])


def _gen_intersection(rng):
    pa, pb = _p(rng, 20, 70), _p(rng, 20, 70)
    pab = _p(rng, 5, 40)
    u = pa + pb - pab
    if pab > min(pa, pb) or u > 1:
        return None
    return dict(enonce=f"On donne $P(A) = {dec(pa)}$, $P(B) = {dec(pb)}$ et $P(A \\cup B) = {dec(u)}$. Calculer $P(A \\cap B)$. Les événements $A$ et $B$ sont-ils incompatibles ?",
                answer=f"$P(A \\cap B) = {dec(pab)}$ : $A$ et $B$ ne sont pas incompatibles.",
                hint="Isole $P(A \\cap B)$ dans la formule de la réunion.",
                steps=[f"$P(A \\cap B) = P(A) + P(B) - P(A \\cup B) = {dec(pa)} + {dec(pb)} - {dec(u)} = {dec(pab)}$.",
                       "$P(A \\cap B) \\neq 0$ : $A$ et $B$ ne sont pas incompatibles."])


def _gen_de_morgan(rng):
    pa, pb = _p(rng, 20, 60), _p(rng, 20, 60)
    pab = _p(rng, 5, 30)
    u = pa + pb - pab
    if pab > min(pa, pb) or u >= 1:
        return None
    return dict(enonce=f"On donne $P(A) = {dec(pa)}$, $P(B) = {dec(pb)}$ et $P(A \\cap B) = {dec(pab)}$. Calculer la probabilité qu'aucun des deux événements ne soit réalisé.",
                answer=f"$P(\\overline{{A}} \\cap \\overline{{B}}) = {dec(1 - u)}$.",
                hint="« Aucun des deux » : $\\overline{A} \\cap \\overline{B} = \\overline{A \\cup B}$.",
                steps=[f"$P(A \\cup B) = {dec(pa)} + {dec(pb)} - {dec(pab)} = {dec(u)}$.",
                       "Lois de De Morgan : $\\overline{A} \\cap \\overline{B} = \\overline{A \\cup B}$.",
                       f"$P(\\overline{{A}} \\cap \\overline{{B}}) = 1 - {dec(u)} = {dec(1 - u)}$."])


def _gen_tableau_reunion(rng):
    f_e, f_i, g_e, g_i = (rng.randint(8, 60) for _ in range(4))
    n = f_e + f_i + g_e + g_i
    pf, pe, pfe = F(f_e + f_i, n), F(f_e + g_e, n), F(f_e, n)
    u = pf + pe - pfe
    return dict(enonce=f"Dans un lycée : {f_e} filles externes, {f_i} filles internes, {g_e} garçons externes et {g_i} garçons internes. On choisit un élève au hasard ; $F$ : « c'est une fille », $E$ : « il est externe ». Calculer $P(F \\cup E)$ et $P(\\overline{{F}} \\cap \\overline{{E}})$.",
                answer=f"$P(F \\cup E) = {frac(u)}$ et $P(\\overline{{F}} \\cap \\overline{{E}}) = {frac(1 - u)}$.",
                hint="Calcule $P(F)$, $P(E)$ et $P(F \\cap E)$ avec l'effectif total.",
                steps=[f"Effectif total : ${n}$ ; $P(F) = \\dfrac{{{f_e + f_i}}}{{{n}}}$, $P(E) = \\dfrac{{{f_e + g_e}}}{{{n}}}$, $P(F \\cap E) = \\dfrac{{{f_e}}}{{{n}}}$.",
                       f"$P(F \\cup E) = \\dfrac{{{f_e + f_i} + {f_e + g_e} - {f_e}}}{{{n}}} = {frac(u)}$.",
                       f"$\\overline{{F}} \\cap \\overline{{E}}$ : garçons internes ; $P = 1 - P(F \\cup E) = \\dfrac{{{g_i}}}{{{n}}} = {frac(1 - u)}$."])


FAMILIES = [
    Family("contraire", 1, "Événement contraire", _gen_contraire, N_EVT, 1.2),
    Family("de_issues", 1, "Intersection et réunion par les issues", _gen_de_issues, N_EVT, 1.5),
    Family("reunion_formule", 2, "Probabilité d'une réunion", _gen_reunion_formule, N_EVT, 2.0),
    Family("intersection", 2, "Probabilité d'une intersection", _gen_intersection, N_EVT, 2.4),
    Family("de_morgan", 3, "Ni l'un ni l'autre (De Morgan)", _gen_de_morgan, N_EVT, 3.0),
    Family("tableau_reunion", 4, "Tableau croisé : réunion et contraire", _gen_tableau_reunion, N_EVT, 4.0),
]
FAMILIES_BY_ID = {f.id: f for f in FAMILIES}


def generate_one(family_id: str, seed: Optional[int] = None) -> dict:
    return c.generate_one(FAMILIES, CHAPTER_ID, family_id, seed)


def generate_pool(per_family: int = 24, seed: int = 20261104) -> list[dict]:
    return c.generate_pool(FAMILIES, CHAPTER_ID, GENERATED_ID_OFFSET, per_family, seed)
