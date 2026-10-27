"""Chapitre 9 de la Première spécifique (manuel « Première ES/L ») — loi de
Bernoulli, loi binomiale, intervalle de fluctuation et règle de décision.
Créé lors de l'adaptation du 2026-10-26 ; contrat : voir _commun_1es.py.
Probabilités binomiales calculées exactement (math.comb, Fraction) ; bornes
de l'intervalle de fluctuation au sens du manuel : a plus petit entier tel
que P(X ⩽ a) > 0,025, b plus petit entier tel que P(X ⩽ b) ⩾ 0,975.
"""
import math
from fractions import Fraction as F
from typing import Optional

from exercise_generator_premiere_specifique import _commun_1es as c
from exercise_generator_premiere_specifique._commun_1es import Family, dec

CHAPTER_ID = "Chapitre_9"
N_BER = "Expériences indépendantes et loi de Bernoulli"
N_BIN = "Schéma de Bernoulli et loi binomiale"
N_ECH = "Échantillonnage et règle de décision"
GENERATED_ID_OFFSET = 1_240_000
LEVEL_META = c.LEVEL_META


def _pb(n, p, k):
    return math.comb(n, k) * p ** k * (1 - p) ** (n - k)


def _cumul(n, p, k):
    return sum(_pb(n, p, i) for i in range(k + 1))


def bornes(n, p):
    a = next(k for k in range(n + 1) if _cumul(n, p, k) > F(1, 40))
    b = next(k for k in range(n + 1) if _cumul(n, p, k) >= F(39, 40))
    return a, b


def _gen_bernoulli(rng):
    p = F(rng.choice([1, 2, 3, 4, 5, 6, 8, 10, 15, 20, 25, 30, 40, 50, 60, 75]), 100)
    v = p * (1 - p)
    sigma = math.sqrt(v)
    exact = math.isqrt(int(v * 10 ** 8)) ** 2 == v * 10 ** 8
    return dict(enonce=f"Un article est défectueux avec la probabilité ${dec(p)}$. $X$ vaut $1$ si l'article est défectueux et $0$ sinon. Donner la loi de $X$, puis $E(X)$, $V(X)$ et $\\sigma(X)$" + (" (au centième)." if not exact else "."),
                answer=f"$P(X = 1) = {dec(p)}$, $P(X = 0) = {dec(1 - p)}$ ; $E(X) = {dec(p)}$, $V(X) = {dec(v)}$ et $\\sigma(X) " + ("= " + dec(F(math.isqrt(int(v * 10 ** 8)), 10 ** 4)) if exact else "\\approx " + dec(sigma, 2)) + "$.",
                hint="$X$ suit une loi de Bernoulli : $E(X) = p$, $V(X) = p(1 - p)$.",
                steps=[f"$X$ suit la loi de Bernoulli de paramètre $p = {dec(p)}$.", f"$E(X) = {dec(p)}$ ; $V(X) = {dec(p)} \\times {dec(1 - p)} = {dec(v)}$.",
                       f"$\\sigma(X) = \\sqrt{{{dec(v)}}}" + ("= " + dec(F(math.isqrt(int(v * 10 ** 8)), 10 ** 4)) if exact else "\\approx " + dec(sigma, 2)) + "$."])


def _gen_repetition(rng):
    p = F(rng.choice([2, 3, 4, 5, 6, 7, 8, 9]), 10)
    n = rng.randint(2, 5)
    r = p ** n
    return dict(enonce=f"Une pièce truquée donne « face » avec la probabilité ${dec(p)}$. On la lance ${n}$ fois de suite. Quelle est la probabilité d'obtenir ${n}$ fois « face » ?",
                answer=f"La probabilité est ${dec(r)}$.",
                hint="Les lancers sont des expériences indépendantes : on multiplie.",
                steps=[f"Les ${n}$ lancers sont indépendants.", f"$P = {dec(p)}^{n} = {dec(r)}$."])


def _gen_coefficients(rng):
    n = rng.randint(2, 5)
    k = rng.randint(0, n)
    nb = math.comb(n, k)
    mots = ["".join(m) for m in __import__("itertools").product("SE", repeat=n) if m.count("S") == k]
    liste = ", ".join(w.replace("E", "\\overline{S}") for w in mots) if len(mots) <= 10 else ""
    return dict(enonce=f"Dans l'arbre de ${n}$ épreuves de Bernoulli, combien de chemins comportent exactement ${k}$ succès ? En déduire $\\binom{{{n}}}{{{k}}}$.",
                answer=f"${nb}$ chemins : $\\binom{{{n}}}{{{k}}} = {nb}$.",
                hint="Liste les chemins comme des mots de $S$ (succès) et $\\overline{S}$ (échec).",
                steps=[f"Chemins à ${k}$ succès : ${liste}$." if liste else f"On compte les mots de ${n}$ lettres contenant ${k}$ fois $S$.",
                       f"Il y en a ${nb}$, donc $\\binom{{{n}}}{{{k}}} = {nb}$."])


def _gen_proba_binomiale(rng):
    n = rng.randint(3, 6)
    p = F(rng.choice([1, 2, 3, 4, 5]), 10)
    k = rng.randint(1, n - 1)
    r = _pb(n, p, k)
    return dict(enonce=f"$X$ suit la loi binomiale $\\mathcal{{B}}({n} ; {dec(p)})$. Calculer $P(X = {k})$.",
                answer=f"$P(X = {k}) = {dec(r)}$.",
                hint="$P(X = k) = \\binom{n}{k} p^k (1 - p)^{n - k}$.",
                steps=[f"$\\binom{{{n}}}{{{k}}} = {math.comb(n, k)}$.",
                       f"$P(X = {k}) = {math.comb(n, k)} \\times {dec(p)}^{{{k}}} \\times {dec(1 - p)}^{{{n - k}}} = {dec(r)}$."])


def _gen_esperance_binomiale(rng):
    n = rng.choice([10, 12, 20, 25, 30, 40, 50, 100])
    p = F(rng.choice([1, 2, 3, 4, 5]), 10)
    e, v = n * p, n * p * (1 - p)
    return dict(enonce=f"$X$ suit la loi binomiale $\\mathcal{{B}}({n} ; {dec(p)})$. Calculer $E(X)$ et $V(X)$, puis donner $\\sigma(X)$ au centième.",
                answer=f"$E(X) = {dec(e)}$, $V(X) = {dec(v)}$ et $\\sigma(X) \\approx {dec(math.sqrt(v), 2)}$.",
                hint="$E(X) = np$ et $V(X) = np(1 - p)$.",
                steps=[f"$E(X) = {n} \\times {dec(p)} = {dec(e)}$.", f"$V(X) = {n} \\times {dec(p)} \\times {dec(1 - p)} = {dec(v)}$.",
                       f"$\\sigma(X) = \\sqrt{{{dec(v)}}} \\approx {dec(math.sqrt(v), 2)}$."])


def _gen_au_moins_un(rng):
    n = rng.randint(2, 6)
    p = F(rng.choice([1, 2, 3, 4, 5]), 10)
    r = 1 - (1 - p) ** n
    return dict(enonce=f"$X$ suit la loi binomiale $\\mathcal{{B}}({n} ; {dec(p)})$. Calculer $P(X \\geqslant 1)$.",
                answer=f"$P(X \\geqslant 1) = {dec(r)}$.",
                hint="Passe par l'événement contraire $X = 0$.",
                steps=[f"$P(X = 0) = {dec(1 - p)}^{n} = {dec((1 - p) ** n)}$.", f"$P(X \\geqslant 1) = 1 - {dec((1 - p) ** n)} = {dec(r)}$."])


def _gen_cumul(rng):
    n = rng.randint(8, 12)
    p = F(rng.choice([1, 2, 3]), 10)
    r = _cumul(n, p, 1)
    return dict(enonce=f"Un lot contient ${n}$ pièces ; chacune est défectueuse avec la probabilité ${dec(p)}$, indépendamment des autres. Calculer la probabilité qu'il y ait au plus une pièce défectueuse (à $0{{,}}001$ près).",
                answer=f"$P(X \\leqslant 1) \\approx {dec(r, 3)}$.",
                hint=f"$X \\sim \\mathcal{{B}}({n} ; {dec(p)})$ ; additionne $P(X = 0)$ et $P(X = 1)$.",
                steps=[f"Le nombre $X$ de pièces défectueuses suit $\\mathcal{{B}}({n} ; {dec(p)})$.",
                       f"$P(X = 0) = {dec(1 - p)}^{{{n}}} \\approx {dec(_pb(n, p, 0), 4)}$ et $P(X = 1) = {n} \\times {dec(p)} \\times {dec(1 - p)}^{{{n - 1}}} \\approx {dec(_pb(n, p, 1), 4)}$.",
                       f"$P(X \\leqslant 1) \\approx {dec(r, 3)}$."])


def _gen_decision(rng):
    n = rng.choice([20, 25, 40, 50, 100])
    p = F(rng.choice([1, 2, 3, 4, 5]), 10)
    a, b = bornes(n, p)
    k = rng.choice([rng.randint(max(0, a - 6), a - 1) if a > 0 else b + 2, rng.randint(a, b), rng.randint(a, b), rng.randint(b + 1, min(n, b + 6))])
    f = F(k, n)
    dedans = a <= k <= b
    return dict(enonce=f"Sous l'hypothèse « la proportion vaut ${dec(p)}$ », pour un échantillon de taille ${n}$, l'intervalle de fluctuation à $95\\,\\%$ est $\\left[{dec(F(a, n))} ; {dec(F(b, n))}\\right]$. On observe ${k}$ succès sur ${n}$. Que décider ?",
                answer=f"$f = {dec(f)}$ " + ("appartient à l'intervalle : on accepte l'hypothèse." if dedans else "n'appartient pas à l'intervalle : on rejette l'hypothèse."),
                hint="Calcule la fréquence observée et compare-la à l'intervalle.",
                steps=[f"$f = \\dfrac{{{k}}}{{{n}}} = {dec(f)}$.",
                       (f"${dec(f)} \\in \\left[{dec(F(a, n))} ; {dec(F(b, n))}\\right]$ : l'hypothèse n'est pas remise en question." if dedans
                        else f"${dec(f)} \\notin \\left[{dec(F(a, n))} ; {dec(F(b, n))}\\right]$ : on rejette l'hypothèse, avec un risque d'environ $5\\,\\%$.")])


def _gen_bornes(rng):
    n = rng.choice([20, 25, 40, 50])
    p = F(rng.choice([1, 2, 3, 4, 5]), 10)
    a, b = bornes(n, p)
    if a == 0:
        return None
    vals = {k: _cumul(n, p, k) for k in (a - 1, a, b - 1, b)}
    table = " ; ".join(f"$P(X \\leqslant {k}) \\approx {dec(v, 4)}$" for k, v in vals.items())
    return dict(enonce=f"$X \\sim \\mathcal{{B}}({n} ; {dec(p)})$. On donne : {table}. Déterminer l'intervalle de fluctuation à $95\\,\\%$ de la fréquence.",
                answer=f"$a = {a}$, $b = {b}$ : l'intervalle est $\\left[{dec(F(a, n))} ; {dec(F(b, n))}\\right]$.",
                hint="$a$ : premier entier avec $P(X \\leqslant a) > 0{,}025$ ; $b$ : premier entier avec $P(X \\leqslant b) \\geqslant 0{,}975$.",
                steps=[f"$P(X \\leqslant {a - 1}) \\leqslant 0{{,}}025 < P(X \\leqslant {a})$ : $a = {a}$.",
                       f"$P(X \\leqslant {b - 1}) < 0{{,}}975 \\leqslant P(X \\leqslant {b})$ : $b = {b}$.",
                       f"Intervalle : $\\left[\\dfrac{{{a}}}{{{n}}} ; \\dfrac{{{b}}}{{{n}}}\\right] = \\left[{dec(F(a, n))} ; {dec(F(b, n))}\\right]$."])


FAMILIES = [
    Family("bernoulli", 1, "Loi de Bernoulli : espérance et variance", _gen_bernoulli, N_BER, 1.4),
    Family("repetition", 2, "Répétition d'expériences indépendantes", _gen_repetition, N_BER, 2.0),
    Family("coefficients", 1, "Compter les chemins : coefficient binomial", _gen_coefficients, N_BIN, 1.3),
    Family("proba_binomiale", 2, "Calculer P(X = k)", _gen_proba_binomiale, N_BIN, 2.5),
    Family("esperance_binomiale", 1, "Espérance et variance d'une loi binomiale", _gen_esperance_binomiale, N_BIN, 1.5),
    Family("au_moins_un", 3, "Au moins un succès", _gen_au_moins_un, N_BIN, 3.0),
    Family("cumul", 4, "Probabilité cumulée", _gen_cumul, N_BIN, 4.0),
    Family("decision", 2, "Appliquer la règle de décision", _gen_decision, N_ECH, 2.0),
    Family("bornes", 3, "Déterminer l'intervalle de fluctuation", _gen_bornes, N_ECH, 3.5),
]
FAMILIES_BY_ID = {f.id: f for f in FAMILIES}


def generate_one(family_id: str, seed: Optional[int] = None) -> dict:
    return c.generate_one(FAMILIES, CHAPTER_ID, family_id, seed)


def generate_pool(per_family: int = 24, seed: int = 20261105) -> list[dict]:
    return c.generate_pool(FAMILIES, CHAPTER_ID, GENERATED_ID_OFFSET, per_family, seed)
