"""Chapitre 4 de la Première spécifique (manuel « Première ES/L ») — statistiques :
notation Σ, moyenne et médiane, quartiles, dispersion. La famille
« statistiques » du module automatismes (moyenne, médiane, étendue) est
rattachée à la première notion par programme_1es.py.
Créé lors de l'adaptation du 2026-10-26 ; contrat : voir _commun_1es.py.
Quartiles au sens du manuel : x_i avec i le plus petit entier ⩾ N/4 (ou 3N/4).
"""
import math
from fractions import Fraction as F
from typing import Optional

from exercise_generator_premiere_specifique import _commun_1es as c
from exercise_generator_premiere_specifique._commun_1es import Family, dec, frac

CHAPTER_ID = "Chapitre_4"
N_TC = "Notation Σ et indicateurs de tendance centrale"
N_Q = "Quartiles et diagramme en boîte"
N_D = "Variance, écart-type et dispersion"
GENERATED_ID_OFFSET = 1_220_000
LEVEL_META = c.LEVEL_META


def _liste(xs):
    return " ; ".join(f"${dec(x)}$" for x in xs)


def _quartile(data, num, den):
    s = sorted(data)
    return s[math.ceil(F(num * len(s), den)) - 1]


def _mediane(data):
    s, n = sorted(data), len(data)
    return F(s[n // 2]) if n % 2 else F(s[n // 2 - 1] + s[n // 2], 2)


def _tableau(valeurs, effectifs):
    return " ; ".join(f"${v}$ ({n})" for v, n in zip(valeurs, effectifs))


def _gen_somme_sigma(rng):
    n = rng.randint(3, 6)
    a, b = rng.randint(1, 5), rng.randint(-3, 6)
    if b == 0:
        terme, somme = (f"{a}i" if a > 1 else "i"), sum(a * i for i in range(1, n + 1))
        detail = " + ".join(str(a * i) for i in range(1, n + 1))
    else:
        terme = (f"{a}i" if a > 1 else "i") + (f" + {b}" if b > 0 else f" - {-b}")
        somme = sum(a * i + b for i in range(1, n + 1))
        detail = " + ".join(f"({a * i + b})" if a * i + b < 0 else str(a * i + b) for i in range(1, n + 1))
    return dict(enonce=f"Calculer $\\sum_{{i=1}}^{{{n}}} ({terme})$.",
                answer=f"$\\sum_{{i=1}}^{{{n}}} ({terme}) = {somme}$.",
                hint="Remplace $i$ par $1$, $2$, …, puis additionne.",
                steps=[f"Termes : ${detail}$.", f"Somme : ${somme}$."])


def _gen_mediane_serie(rng):
    n = rng.choice([7, 8, 9, 10])
    data = [rng.randint(2, 20) for _ in range(n)]
    s, me = sorted(data), _mediane(data)
    regle = (f"$N = {n}$ est impair : valeur de rang $\\dfrac{{{n} + 1}}{{2}} = {(n + 1) // 2}$." if n % 2
             else f"$N = {n}$ est pair : moyenne des valeurs de rangs ${n // 2}$ et ${n // 2 + 1}$.")
    return dict(enonce=f"Déterminer la médiane de la série : {_liste(data)}.",
                answer=f"La médiane vaut ${dec(me)}$.",
                hint="Range d'abord la série dans l'ordre croissant.",
                steps=[f"Série rangée : {_liste(s)}.", regle, f"$Me = {dec(me)}$."])


def _gen_moyenne_effectifs(rng):
    valeurs = sorted(rng.sample(range(5, 21), 5))
    effectifs = [rng.randint(1, 8) for _ in valeurs]
    n = sum(effectifs)
    if n not in (10, 16, 20, 25, 40) and (F(1, n) * 100).denominator != 1:
        return None
    s = sum(v * k for v, k in zip(valeurs, effectifs))
    m = F(s, n)
    if not c.decimal_exact(m, 2):
        return None
    mode = valeurs[effectifs.index(max(effectifs))]
    if effectifs.count(max(effectifs)) > 1:
        return None
    return dict(enonce=f"Une série a pour valeurs (effectifs) : {_tableau(valeurs, effectifs)}. Calculer l'effectif total, la moyenne et donner le mode.",
                answer=f"$N = {n}$, $\\overline{{x}} = {dec(m)}$ et le mode est ${mode}$.",
                hint="Multiplie chaque valeur par son effectif, additionne, divise par l'effectif total.",
                steps=[f"$N = {' + '.join(map(str, effectifs))} = {n}$.",
                       f"$\\sum n_i x_i = {' + '.join(f'{k} \\times {v}' for v, k in zip(valeurs, effectifs))} = {s}$.",
                       f"$\\overline{{x}} = \\dfrac{{{s}}}{{{n}}} = {dec(m)}$ ; le mode est la valeur de plus grand effectif, ${mode}$."])


def _gen_quartiles_serie(rng):
    n = rng.randint(8, 15)
    data = [rng.randint(1, 30) for _ in range(n)]
    s = sorted(data)
    r1, r3 = math.ceil(F(n, 4)), math.ceil(F(3 * n, 4))
    q1, q3 = s[r1 - 1], s[r3 - 1]
    return dict(enonce=f"Déterminer le premier et le troisième quartile de la série : {_liste(data)}.",
                answer=f"$Q_1 = {q1}$ et $Q_3 = {q3}$.",
                hint="Range la série, puis calcule $\\dfrac{N}{4}$ et $\\dfrac{3N}{4}$.",
                steps=[f"Série rangée ($N = {n}$) : {_liste(s)}.",
                       f"$\\dfrac{{{n}}}{{4}} = {dec(F(n, 4))}$ : rang ${r1}$, donc $Q_1 = {q1}$.",
                       f"$\\dfrac{{3 \\times {n}}}{{4}} = {dec(F(3 * n, 4))}$ : rang ${r3}$, donc $Q_3 = {q3}$."])


def _gen_ecart_interquartile(rng):
    mn = rng.randint(0, 8)
    q1 = mn + rng.randint(1, 5)
    me = q1 + rng.randint(1, 4)
    q3 = me + rng.randint(1, 5)
    mx = q3 + rng.randint(1, 8)
    return dict(enonce=f"Un diagramme en boîte a pour valeurs extrêmes ${mn}$ et ${mx}$, une boîte allant de ${q1}$ à ${q3}$ et une médiane égale à ${me}$. Calculer l'écart interquartile et l'étendue.",
                answer=f"Écart interquartile ${q3 - q1}$ ; étendue ${mx - mn}$.",
                hint="La boîte va de $Q_1$ à $Q_3$ ; les moustaches jusqu'aux valeurs extrêmes.",
                steps=[f"$E_i = Q_3 - Q_1 = {q3} - {q1} = {q3 - q1}$.", f"Étendue : ${mx} - {mn} = {mx - mn}$."])


def _gen_quartiles_effectifs(rng):
    valeurs = sorted(rng.sample(range(1, 21), 6))
    effectifs = [rng.randint(1, 7) for _ in valeurs]
    n = sum(effectifs)
    data = [v for v, k in zip(valeurs, effectifs) for _ in range(k)]
    cumul, tot = [], 0
    for k in effectifs:
        tot += k
        cumul.append(tot)
    r1, r3 = math.ceil(F(n, 4)), math.ceil(F(3 * n, 4))
    q1, q3, me = data[r1 - 1], data[r3 - 1], _mediane(data)
    return dict(enonce=f"Une série a pour valeurs (effectifs) : {_tableau(valeurs, effectifs)}. Déterminer $Q_1$, la médiane et $Q_3$.",
                answer=f"$Q_1 = {q1}$, $Me = {dec(me)}$ et $Q_3 = {q3}$.",
                hint="Utilise les effectifs cumulés croissants.",
                steps=[f"Effectifs cumulés : {' ; '.join(map(str, cumul))} ; $N = {n}$.",
                       f"Rang de $Q_1$ : ${r1}$ ($\\dfrac{{{n}}}{{4}} = {dec(F(n, 4))}$), donc $Q_1 = {q1}$ ; rang de $Q_3$ : ${r3}$, donc $Q_3 = {q3}$.",
                       f"Médiane : $Me = {dec(me)}$."])


def _gen_variance_serie(rng):
    n = rng.choice([3, 4, 5])
    data = [rng.randint(0, 12) for _ in range(n)]
    m = F(sum(data), n)
    if m.denominator != 1 or len(set(data)) == 1:
        return None
    v = sum((F(x) - m) ** 2 for x in data) / n
    sigma = math.sqrt(v)
    ecarts = " + ".join(f"({dec(x - m)})^2" if x - m < 0 else f"{dec(x - m)}^2" for x in data)
    return dict(enonce=f"Calculer la variance et l'écart-type de la série : {_liste(data)}.",
                answer=f"$V = {frac(v)}$ et $\\sigma \\approx {dec(sigma, 2)}$." if v.denominator != 1 or math.isqrt(int(v)) ** 2 != v
                else f"$V = {frac(v)}$ et $\\sigma = {math.isqrt(int(v))}$.",
                hint="Calcule la moyenne, puis la moyenne des carrés des écarts.",
                steps=[f"$\\overline{{x}} = \\dfrac{{{sum(data)}}}{{{n}}} = {dec(m)}$.", f"$V = \\dfrac{{{ecarts}}}{{{n}}} = {frac(v)}$.",
                       f"$\\sigma = \\sqrt{{V}} \\approx {dec(sigma, 2)}$."])


def _gen_variance_formule(rng):
    n = rng.choice([10, 20, 25, 40, 50])
    m = F(rng.randint(80, 160), 10)
    v = F(rng.randint(5, 80), 4)
    sx = n * m
    sx2 = n * (v + m * m)
    if not (c.decimal_exact(sx, 2) and c.decimal_exact(sx2, 4)):
        return None
    sigma = math.sqrt(v)
    return dict(enonce=f"Pour une série d'effectif total $N = {n}$, on donne $\\sum n_i x_i = {dec(sx)}$ et $\\sum n_i x_i^2 = {dec(sx2)}$. Calculer la moyenne, la variance et l'écart-type (au centième).",
                answer=f"$\\overline{{x}} = {dec(m)}$, $V = {dec(v)}$ et $\\sigma \\approx {dec(sigma, 2)}$.",
                hint="$V = \\dfrac{\\sum n_i x_i^2}{N} - \\overline{x}^2$.",
                steps=[f"$\\overline{{x}} = \\dfrac{{{dec(sx)}}}{{{n}}} = {dec(m)}$.",
                       f"$\\dfrac{{{dec(sx2)}}}{{{n}}} = {dec(sx2 / n)}$ et $\\overline{{x}}^2 = {dec(m * m)}$, donc $V = {dec(sx2 / n)} - {dec(m * m)} = {dec(v)}$.",
                       f"$\\sigma = \\sqrt{{{dec(v)}}} \\approx {dec(sigma, 2)}$."])


def _gen_comparer_dispersion(rng):
    m = rng.randint(8, 14)
    d1, d2 = sorted(rng.sample(range(1, 7), 2))
    a, b = [m - d1, m, m + d1], [m - d2, m, m + d2]
    va, vb = F(2 * d1 * d1, 3), F(2 * d2 * d2, 3)
    return dict(enonce=f"Série A : {_liste(a)}. Série B : {_liste(b)}. Calculer les moyennes et les variances, puis comparer les dispersions.",
                answer=f"Les deux moyennes valent ${m}$ ; $V_A = {frac(va)}$ et $V_B = {frac(vb)}$ : la série B est plus dispersée.",
                hint="Même moyenne ne veut pas dire même dispersion.",
                steps=[f"Moyennes : $\\dfrac{{{3 * m}}}{{3}} = {m}$ dans les deux cas.",
                       f"$V_A = \\dfrac{{{d1}^2 + 0 + {d1}^2}}{{3}} = {frac(va)}$ et $V_B = \\dfrac{{{d2}^2 + 0 + {d2}^2}}{{3}} = {frac(vb)}$.",
                       "$V_B > V_A$ : la série B est plus dispersée autour de la moyenne."])


def _gen_resume_serie(rng):
    data = sorted(rng.randint(1, 20) for _ in range(8))
    m = F(sum(data), 8)
    if not c.decimal_exact(m, 3):
        return None
    me = _mediane(data)
    q1, q3 = _quartile(data, 1, 4), _quartile(data, 3, 4)
    v = sum((F(x) - m) ** 2 for x in data) / 8
    return dict(enonce=f"Pour la série {_liste(data)}, calculer la moyenne, la médiane, les quartiles, l'écart interquartile et l'écart-type (au centième).",
                answer=f"$\\overline{{x}} = {dec(m)}$, $Me = {dec(me)}$, $Q_1 = {q1}$, $Q_3 = {q3}$, $E_i = {q3 - q1}$ et $\\sigma \\approx {dec(math.sqrt(v), 2)}$.",
                hint="La série est rangée ; $N = 8$.",
                steps=[f"$\\overline{{x}} = \\dfrac{{{sum(data)}}}{{8}} = {dec(m)}$ ; $Me = \\dfrac{{{data[3]} + {data[4]}}}{{2}} = {dec(me)}$.",
                       f"$\\dfrac{{8}}{{4}} = 2$ : $Q_1 = x_2 = {q1}$ ; $\\dfrac{{3 \\times 8}}{{4}} = 6$ : $Q_3 = x_6 = {q3}$ ; $E_i = {q3 - q1}$.",
                       f"$V = \\dfrac{{\\sum (x_i - \\overline{{x}})^2}}{{8}} = {frac(v)}$, donc $\\sigma \\approx {dec(math.sqrt(v), 2)}$."])


FAMILIES = [
    Family("somme_sigma", 1, "Calculer une somme Σ", _gen_somme_sigma, N_TC, 1.3),
    Family("mediane_serie", 1, "Médiane d'une série", _gen_mediane_serie, N_TC, 1.5),
    Family("moyenne_effectifs", 2, "Moyenne et mode d'une série avec effectifs", _gen_moyenne_effectifs, N_TC, 2.0),
    Family("quartiles_serie", 2, "Quartiles d'une série", _gen_quartiles_serie, N_Q, 2.0),
    Family("ecart_interquartile", 1, "Lire un diagramme en boîte", _gen_ecart_interquartile, N_Q, 1.2),
    Family("quartiles_effectifs", 3, "Quartiles et médiane avec effectifs", _gen_quartiles_effectifs, N_Q, 3.0),
    Family("variance_serie", 2, "Variance et écart-type d'une petite série", _gen_variance_serie, N_D, 2.4),
    Family("variance_formule", 3, "Variance par la seconde formule", _gen_variance_formule, N_D, 3.2),
    Family("comparer_dispersion", 3, "Comparer deux dispersions", _gen_comparer_dispersion, N_D, 3.0),
    Family("resume_serie", 4, "Résumer une série par ses indicateurs", _gen_resume_serie, N_D, 4.0),
]
FAMILIES_BY_ID = {f.id: f for f in FAMILIES}


def generate_one(family_id: str, seed: Optional[int] = None) -> dict:
    return c.generate_one(FAMILIES, CHAPTER_ID, family_id, seed)


def generate_pool(per_family: int = 24, seed: int = 20261103) -> list[dict]:
    return c.generate_pool(FAMILIES, CHAPTER_ID, GENERATED_ID_OFFSET, per_family, seed)
