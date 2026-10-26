"""Chapitre 1 de la Première spécifique (manuel « Première ES/L ») — proportions
et indices base 100. Les familles d'évolutions (taux, coefficient
multiplicateur, évolutions successives, taux réciproque) sont celles du module
automatismes, rattachées au chapitre 1 par programme_1es.py.
Créé lors de l'adaptation du 2026-10-26 ; contrat : voir _commun_1es.py.
"""
from fractions import Fraction as F
from typing import Optional

from exercise_generator_premiere_specifique import _commun_1es as c
from exercise_generator_premiere_specifique._commun_1es import Family, dec, pct

CHAPTER_ID = "Chapitre_1"
N_PROP = "Proportions et pourcentages"
N_IND = "Indices base 100"
GENERATED_ID_OFFSET = 1_200_000
LEVEL_META = c.LEVEL_META

_GROUPES = [("adhérents d'un club", "sont des femmes"), ("élèves d'un lycée", "sont demi-pensionnaires"),
            ("salariés d'une entreprise", "travaillent à temps partiel"), ("clients d'un magasin", "ont payé par carte"),
            ("habitants d'un village", "ont plus de 60 ans")]


def _gen_proportion(rng):
    n = rng.choice([200, 250, 400, 480, 500, 640, 800, 1000, 1200])
    p = F(rng.choice([5, 10, 12, 15, 20, 25, 30, 35, 40, 45, 55, 60, 75, 85]), 100)
    a = n * p
    if a.denominator != 1:
        return None
    qui, quoi = rng.choice(_GROUPES)
    return dict(enonce=f"Sur ${dec(n)}$ {qui}, ${dec(a)}$ {quoi}. Quelle proportion cela représente-t-il, en pourcentage ?",
                answer=f"La proportion est ${dec(p)}$, soit ${pct(p)}$.",
                hint="Divise l'effectif de la partie par l'effectif total.",
                steps=[f"$p = \\dfrac{{{dec(a)}}}{{{dec(n)}}} = {dec(p)}$.", f"En pourcentage : ${pct(p)}$."])


def _gen_pourcentage_de(rng):
    p = rng.choice([5, 12, 15, 20, 25, 30, 35, 40, 65, 75, 120])
    q = rng.choice([40, 60, 80, 120, 150, 240, 320, 450, 600, 840])
    r = F(q * p, 100)
    if not c.decimal_exact(r, 2):
        return None
    return dict(enonce=f"Calculer ${p}\\,\\%$ de ${q}$ €.",
                answer=f"${p}\\,\\%$ de ${q}$ € font ${dec(r)}$ €.",
                hint=f"Multiplie par $\\dfrac{{{p}}}{{100}}$.",
                steps=[f"${q} \\times \\dfrac{{{p}}}{{100}} = {q} \\times {dec(F(p, 100))}$.", f"$= {dec(r)}$."])


def _gen_effectif_total(rng):
    p = rng.choice([4, 5, 8, 10, 12, 15, 20, 24, 25, 30, 40, 60, 75])
    n = rng.choice([25, 40, 50, 60, 75, 80, 120, 150, 200, 250, 300])
    a = F(n * p, 100)
    if a.denominator != 1:
        return None
    return dict(enonce=f"Dans une association, ${dec(a)}$ membres représentent ${p}\\,\\%$ de l'effectif. Combien l'association compte-t-elle de membres ?",
                answer=f"L'association compte ${n}$ membres.",
                hint="L'effectif total multiplié par la proportion donne l'effectif de la partie.",
                steps=[f"$n \\times {dec(F(p, 100))} = {dec(a)}$.", f"$n = \\dfrac{{{dec(a)}}}{{{dec(F(p, 100))}}} = {n}$."])


def _gen_proportion_de_proportion(rng):
    p1 = F(rng.choice([20, 25, 30, 40, 45, 50, 60, 70, 80]), 100)
    p2 = F(rng.choice([10, 15, 20, 25, 30, 40, 50, 75]), 100)
    r = p1 * p2
    return dict(enonce=f"Dans un lycée, ${pct(p1)}$ des élèves sont internes, et ${pct(p2)}$ des internes pratiquent un sport en club. Quelle proportion de l'ensemble des élèves est interne et pratique un sport en club ?",
                answer=f"${pct(r)}$ des élèves.",
                hint="Une proportion d'une proportion se calcule par un produit.",
                steps=[f"On multiplie les proportions : ${dec(p1)} \\times {dec(p2)} = {dec(r)}$.", f"Soit ${pct(r)}$ de l'ensemble des élèves."])


def _gen_indice_calcul(rng):
    y1 = F(rng.choice([80, 120, 150, 200, 250, 400, 500, 800, 1200]))
    i2 = F(rng.choice([85, 90, 92, 95, 104, 105, 108, 110, 112, 115, 120, 125, 130, 150]))
    y2 = y1 * i2 / 100
    if not c.decimal_exact(y2, 2):
        return None
    an1, an2 = rng.choice([(2015, 2020), (2018, 2023), (2010, 2020), (2019, 2024)])
    sens = "hausse" if i2 > 100 else "baisse"
    return dict(enonce=f"Une grandeur vaut ${dec(y1)}$ en {an1} et ${dec(y2)}$ en {an2}. Calculer son indice en {an2}, base $100$ en {an1}, puis interpréter.",
                answer=f"L'indice vaut ${dec(i2)}$ : {sens} de ${dec(abs(i2 - 100))}\\,\\%$ entre {an1} et {an2}.",
                hint="Indice $= 100 \\times \\dfrac{\\text{nouvelle valeur}}{\\text{valeur de référence}}$.",
                steps=[f"$I = 100 \\times \\dfrac{{{dec(y2)}}}{{{dec(y1)}}} = {dec(i2)}$.", f"Écart à $100$ : ${dec(i2 - 100)}$, soit une {sens} de ${dec(abs(i2 - 100))}\\,\\%$."])


def _gen_indice_taux(rng):
    i = F(rng.choice([72, 85, 87, 91, 96, 98, 103, 107, 112, 118, 124, 135, 146])) + F(rng.choice([0, 0, 5]), 10)
    sens = "augmenté" if i > 100 else "diminué"
    return dict(enonce=f"L'indice d'un prix vaut ${dec(i)}$ en 2024 (base $100$ en 2020). Interpréter cet indice.",
                answer=f"Le prix a {sens} de ${dec(abs(i - 100))}\\,\\%$ entre 2020 et 2024.",
                hint="Compare l'indice à $100$.",
                steps=[f"$t = \\dfrac{{{dec(i)} - 100}}{{100}} = {dec((i - 100) / 100)}$.", f"Le prix a {sens} de ${dec(abs(i - 100))}\\,\\%$."])


def _gen_indice_valeur(rng):
    y1 = rng.choice([1200, 1500, 2000, 2400, 3000, 4500, 6000, 8000])
    i2 = F(rng.choice([92, 96, 104, 105, 108, 112, 115, 118, 125])) + F(rng.choice([0, 5]), 10)
    y2 = y1 * i2 / 100
    if y2.denominator != 1:
        return None
    return dict(enonce=f"Une commune comptait ${dec(y1)}$ habitants en 2015 (indice $100$). En 2025, l'indice vaut ${dec(i2)}$. Combien compte-t-elle d'habitants en 2025 ?",
                answer=f"La commune compte ${dec(y2)}$ habitants en 2025.",
                hint="Valeur $=$ valeur de référence $\\times \\dfrac{I}{100}$.",
                steps=[f"$y = {dec(y1)} \\times \\dfrac{{{dec(i2)}}}{{100}} = {dec(y1)} \\times {dec(i2 / 100)}$.", f"$y = {dec(y2)}$."])


def _gen_indice_changement_base(rng):
    ia = F(rng.choice([104, 105, 108, 110, 120, 125]))
    t = F(rng.choice([5, 8, 10, 12, 20, -4, -5, -10]), 100)
    ib = ia * (1 + t)
    if not c.decimal_exact(ib, 2):
        return None
    nb = 100 * ib / ia
    sens = "hausse" if t > 0 else "baisse"
    return dict(enonce=f"Base $100$ en 2018, un indice vaut ${dec(ia)}$ en 2020 et ${dec(ib)}$ en 2023. Calculer l'indice de 2023 en prenant 2020 comme référence, puis l'évolution entre 2020 et 2023.",
                answer=f"Indice ${dec(nb)}$ : {sens} de ${dec(abs(nb - 100))}\\,\\%$ entre 2020 et 2023.",
                hint="Les indices sont proportionnels aux valeurs.",
                steps=[f"$I = 100 \\times \\dfrac{{{dec(ib)}}}{{{dec(ia)}}} = {dec(nb)}$.", f"Entre 2020 et 2023 : {sens} de ${dec(abs(nb - 100))}\\,\\%$ (et non de ${dec(abs(ib - ia))}\\,\\%$)."])


def _gen_indice_evolutions(rng):
    t1 = F(rng.choice([10, 20, 25, 30, 40, 50]), 100)
    t2 = F(rng.choice([-10, -20, -25, -40, 10, 20]), 100)
    i1 = 100 * (1 + t1)
    i2 = i1 * (1 + t2)
    if not c.decimal_exact(i2, 2):
        return None
    recip = 100 / i2
    s1 = "augmente" if t1 > 0 else "baisse"
    s2 = "augmente" if t2 > 0 else "baisse"
    glob = "hausse" if i2 > 100 else "baisse"
    return dict(enonce=f"Base $100$ en 2022, une grandeur {s1} de ${pct(abs(t1))}$ en 2023, puis {s2} de ${pct(abs(t2))}$ en 2024. Calculer ses indices en 2023 et en 2024, l'évolution globale, puis le taux qui la ramènerait à son niveau de 2022 (arrondi à $0{{,}}1\\,\\%$).",
                answer=f"Indices ${dec(i1)}$ puis ${dec(i2)}$ : {glob} globale de ${dec(abs(i2 - 100))}\\,\\%$ ; taux réciproque environ ${dec((recip - 1) * 100, 1)}\\,\\%$.",
                hint="Applique les coefficients multiplicateurs aux indices ; le coefficient réciproque est l'inverse.",
                steps=[f"2023 : $100 \\times {dec(1 + t1)} = {dec(i1)}$ ; 2024 : ${dec(i1)} \\times {dec(1 + t2)} = {dec(i2)}$.",
                       f"Évolution globale : ${dec(i2)} - 100 = {dec(i2 - 100)}$, soit une {glob} de ${dec(abs(i2 - 100))}\\,\\%$.",
                       f"Coefficient réciproque : $\\dfrac{{100}}{{{dec(i2)}}} \\approx {dec(recip, 4)}$, soit un taux d'environ ${dec((recip - 1) * 100, 1)}\\,\\%$."])


FAMILIES = [
    Family("proportion", 1, "Calculer une proportion", _gen_proportion, N_PROP, 1.2),
    Family("pourcentage_de", 1, "Calculer p % d'une quantité", _gen_pourcentage_de, N_PROP, 1.2),
    Family("effectif_total", 2, "Retrouver un effectif total", _gen_effectif_total, N_PROP, 2.0),
    Family("proportion_de_proportion", 2, "Proportion d'une proportion", _gen_proportion_de_proportion, N_PROP, 2.3),
    Family("indice_calcul", 1, "Calculer un indice base 100", _gen_indice_calcul, N_IND, 1.4),
    Family("indice_taux", 1, "Interpréter un indice", _gen_indice_taux, N_IND, 1.2),
    Family("indice_valeur", 2, "Retrouver une valeur à partir de son indice", _gen_indice_valeur, N_IND, 2.0),
    Family("indice_changement_base", 3, "Changer d'année de référence", _gen_indice_changement_base, N_IND, 3.0),
    Family("indice_evolutions", 4, "Indices, évolutions successives et taux réciproque", _gen_indice_evolutions, N_IND, 4.0),
]
FAMILIES_BY_ID = {f.id: f for f in FAMILIES}


def generate_one(family_id: str, seed: Optional[int] = None) -> dict:
    return c.generate_one(FAMILIES, CHAPTER_ID, family_id, seed)


def generate_pool(per_family: int = 24, seed: int = 20261101) -> list[dict]:
    return c.generate_pool(FAMILIES, CHAPTER_ID, GENERATED_ID_OFFSET, per_family, seed)
