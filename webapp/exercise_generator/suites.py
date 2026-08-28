"""Génération symbolique d'exercices sur les suites (Première, Chapitre_1).

Même principe que `webapp/exercise_generator/derivatives.py` (le patron de
référence de ce package) : chaque "famille" représente un vrai type de
raisonnement (pas une simple variation numérique), tous les calculs
(termes, sommes, limites, résolutions d'équations) sont faits par sympy —
jamais à la main en Python — et la difficulté affichée est recalculée
depuis la complexité réelle de la structure produite plutôt que depuis une
étiquette arbitraire.

Différence assumée avec `derivatives.py` : ce module couvre LES SIX
notions du Chapitre_1 (pas une seule notion), et les familles ne partagent
pas toutes la même opération (dérivée) — certaines calculent un terme,
d'autres une somme, une limite, ou demandent une démonstration ou une
justification vrai/faux. En conséquence :
  * la dataclass `Family` gagne un champ `notion` (en plus de
    id/level/label/generate/structure_hint/rule_hint imposés par le
    patron) pour savoir à quelle notion du Chapitre_1 rattacher l'exercice ;
  * `generate(rng)` renvoie toujours `(structure_sympy, notes)` comme dans
    derivatives.py, mais `notes` porte ici le texte déjà rédigé (énoncé,
    réponse, étapes) car il n'existe pas d'opération générique unique
    (contrairement à `diff`) applicable à toutes les familles — le rendu
    reste néanmoins entièrement dérivé de valeurs calculées par sympy,
    jamais tapées "en dur".

Un exercice est écarté (retiré, nouvelle graine) quand `generate` renvoie
`None`, exactement comme `build_exercise` le fait dans derivatives.py pour
une dérivée dégénérée.
"""
import random
from dataclasses import dataclass
from typing import Callable, Optional

import sympy
from sympy import (
    Eq, Integer, Pow, Rational, S, Sum, latex, limit, oo, simplify,
    solve, summation, symbols,
)

from .derivatives import _nz, _small

n = symbols("n", integer=True, nonnegative=True)
k = symbols("k", integer=True, nonnegative=True)

CHAPTER_ID = "Chapitre_1"

NOTION_GENERALITES = "Généralités sur les suites"
NOTION_ARITHMETIQUE = "Suite arithmétique"
NOTION_GEOMETRIQUE = "Suite géométrique"
NOTION_VARIATION = "Sens de variation d'une suite"
NOTION_SOMMES = "Calcul de sommes"
NOTION_LIMITE = "Notion de limite d'une suite"

# Distinct de GENERATED_ID_OFFSET = 900_000 dans derivatives.py, pour ne
# jamais entrer en collision si les deux pools généraux sont fusionnés dans
# la même banque.
GENERATED_ID_OFFSET = 910_000


def _lin_rule_latex(a, b, var_latex: str = "u_n") -> str:
    """Rend en LaTeX une relation affine  a·var + b , utilisée pour décrire
    une relation de récurrence u_{n+1} = a u_n + b sans dupliquer le calcul
    (les valeurs a, b sont toujours tirées par les générateurs, jamais
    tapées en dur dans les énoncés)."""
    if a == 1:
        term = var_latex
    elif a == -1:
        term = f"-{var_latex}"
    else:
        term = f"{a}{var_latex}"
    if b > 0:
        return f"{term} + {b}"
    if b < 0:
        return f"{term} - {abs(b)}"
    return term


LEVEL_META = {
    1: {"emoji": "🟢", "label": "Niveau 1 — Fondamental"},
    2: {"emoji": "🟡", "label": "Niveau 2 — Intermédiaire"},
    3: {"emoji": "🟠", "label": "Niveau 3 — Avancé"},
    4: {"emoji": "🔴", "label": "Niveau 4 — Difficile"},
    5: {"emoji": "🟣", "label": "Niveau 5 — Défi"},
}


# ── Complexité réelle ──────────────────────────────────────────────────────

def real_difficulty_score(expr) -> float:
    """Complexité algébrique réelle d'une structure produite par une
    famille, utilisée pour vérifier que la difficulté affichée correspond
    au contenu réel — même principe que dans derivatives.py, adapté au fait
    qu'ici `expr` peut être un `Sum` (somme), une `Eq` (équation/preuve) ou
    une expression classique (terme, limite)."""
    if isinstance(expr, Eq):
        # Une équation à résoudre/démontrer : complexité des deux membres
        # + bonus fixe pour la mise en équation elle-même.
        score = float(expr.lhs.count_ops()) + float(expr.rhs.count_ops()) + 1.5
    elif isinstance(expr, Sum):
        # Une somme non développée : complexité du terme général + bonus
        # pour la manipulation d'indices (bornes de sommation).
        body, (idx, lo, hi) = expr.function, expr.limits[0]
        score = float(body.count_ops()) + 2.5
        if lo != 0:
            score += 1.0  # décalage d'indices : pas une somme "de base"
    else:
        score = float(expr.count_ops())

    atoms_source = expr.atoms(Pow) if hasattr(expr, "atoms") else []
    for p in atoms_source:
        if not p.exp.is_number:
            continue
        if p.exp == Rational(1, 2):
            score += 2.0
        elif p.exp.is_Integer and p.exp < 0:
            score += 2.0  # quotient
        elif not p.exp.is_Integer:
            score += 1.5
        elif p.exp not in (0, 1):
            score += 0.5

    if hasattr(expr, "has") and expr.has(oo):
        score += 1.0

    free = expr.free_symbols if hasattr(expr, "free_symbols") else set()
    abstract_symbols = free - {n, k}
    if abstract_symbols:
        # Un paramètre littéral (a, q, u0…) resté symbolique signale un
        # raisonnement général/une démonstration, plus abstrait qu'un
        # calcul purement numérique.
        score += 1.5 * len(abstract_symbols)

    return round(score, 2)


def _difficulty_bucket_from_score(score: float) -> int:
    """Convertit le score de complexité réelle en palier 1-5. Bornes
    calibrées par observation empirique sur un grand pool généré (voir le
    test `TestDifficulteReelle` qui vérifie l'absence d'inversion nette
    entre niveaux déclarés croissants)."""
    if score <= 2:
        return 1
    if score <= 4.5:
        return 2
    if score <= 7:
        return 3
    if score <= 10:
        return 4
    return 5


# ── Généralités sur les suites ─────────────────────────────────────────────

def _gen_generalites_explicite(rng):
    """Application directe : calculer un terme depuis une formule explicite
    (pas forcément affine — pour bien montrer qu'une suite n'est pas
    toujours arithmétique/géométrique)."""
    a = _nz(rng, -3, 3)
    b = _small(rng, -5, 5)
    c = _small(rng, -8, 8)
    expr = a * n**2 + b * n + c
    p_val = rng.randint(3, 9)
    u_p = expr.subs(n, p_val)
    enonce = (
        f"On considère la suite $(u_n)$ définie pour tout entier $n \\geq 0$ par "
        f"$u_n = {latex(expr)}$. Calculer $u_{{{p_val}}}$."
    )
    steps = [
        f"Étape 1 — On remplace $n$ par ${p_val}$ dans l'expression de $u_n$.",
        f"Étape 2 — $u_{{{p_val}}} = {latex(u_p)}$ après calcul.",
    ]
    answer = f"$u_{{{p_val}}} = {latex(u_p)}$"
    hint = "Substituer directement la valeur de l'indice dans la formule explicite."
    return expr, {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


def _gen_generalites_recurrence(rng):
    """Calcul à étapes : dérouler une relation de récurrence affine terme à
    terme, sans passer par une formule explicite."""
    a = _nz(rng, -3, 3)
    if a == 1:
        a = 2  # a=1 dégénérerait en suite arithmétique, notion déjà dédiée
    b = _small(rng, -6, 6)
    u0 = _small(rng, -6, 6)
    steps_count = rng.choice([2, 3])
    values = [Integer(u0)]
    for _ in range(steps_count):
        values.append(sympy.expand(a * values[-1] + b))
    rel = _lin_rule_latex(a, b)
    indices = ", ".join(f"$u_{{{i}}}$" for i in range(1, steps_count))
    enonce = (
        f"On considère la suite $(u_n)$ définie par $u_0 = {u0}$ et, pour tout entier "
        f"$n \\geq 0$, $u_{{n+1}} = {rel}$. Calculer "
        + (f"{indices} et $u_{{{steps_count}}}$" if steps_count > 1 else f"$u_{{{steps_count}}}$")
        + "."
    )
    steps = [
        f"Étape {i} — $u_{{{i}}} = {a} \\times {latex(values[i-1])} {'+' if b >= 0 else '-'} {abs(b)} = {latex(values[i])}$."
        for i in range(1, steps_count + 1)
    ]
    answer = ", ".join(f"$u_{{{i}}} = {latex(values[i])}$" for i in range(1, steps_count + 1))
    hint = "Calculer les termes un par un en appliquant la relation de récurrence à chaque étape, sans raccourci."
    sym_u0 = symbols("u0")
    core = sym_u0
    for _ in range(steps_count):
        core = a * core + b
    return sympy.expand(core), {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


def _gen_generalites_inverse(rng):
    """Inversé : retrouver u0 à partir de u1 et de la relation de
    récurrence (résolution d'équation par sympy, pas de calcul mental)."""
    a = _nz(rng, -3, 3)
    if a == 1:
        a = 2
    b = _small(rng, -6, 6)
    u0 = _small(rng, -6, 6)
    u1 = sympy.expand(a * u0 + b)
    rel = _lin_rule_latex(a, b)
    u0_sym = symbols("u0")
    eq = Eq(a * u0_sym + b, u1)
    sol = solve(eq, u0_sym)
    if not sol or sol[0] != u0:
        return None
    found = sol[0]
    enonce = (
        f"Une suite $(u_n)$ vérifie, pour tout entier $n \\geq 0$, $u_{{n+1}} = {rel}$. "
        f"On sait que $u_1 = {latex(u1)}$. Déterminer $u_0$."
    )
    steps = [
        f"Étape 1 — On pose l'équation vérifiée par $u_0$ : ${latex(eq)}$.",
        f"Étape 2 — On résout cette équation : $u_0 = {latex(found)}$.",
    ]
    answer = f"$u_0 = {latex(found)}$"
    hint = "Remplacer u_n par u_0 dans la relation de récurrence puis résoudre l'équation d'inconnue u_0."
    return eq, {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


def _gen_generalites_interpretation(rng):
    """Interprétation contextualisée d'une suite définie par un modèle
    simple (évolution linéaire d'un effectif)."""
    c = _nz(rng, -50, 80)
    u0 = rng.randint(200, 2000)
    label, unite = rng.choice([
        ("le nombre d'adhérents d'une association", "adhérents"),
        ("le nombre d'abonnés d'une chaîne en ligne", "abonnés"),
        ("la population d'une ville, en centaines d'habitants", "centaines d'habitants"),
    ])
    p_val = rng.randint(2, 5)
    expr = u0 + c * n
    u_p = expr.subs(n, p_val)
    sens = "augmente" if c > 0 else "diminue"
    enonce = (
        f"On modélise {label} par une suite $(u_n)$ où $u_n$ représente cette quantité l'année $n$. "
        f"On a $u_0 = {u0}$ et, chaque année, elle {sens} de {abs(c)} {unite}. "
        f"Calculer $u_{{{p_val}}}$ et interpréter le résultat dans le contexte."
    )
    steps = [
        f"Étape 1 — Chaque année, on ajoute {c} à la valeur précédente : $u_n = {latex(expr)}$.",
        f"Étape 2 — $u_{{{p_val}}} = {latex(u_p)}$.",
    ]
    answer = f"$u_{{{p_val}}} = {latex(u_p)}$ : après {p_val} ans, la valeur modélisée est {latex(u_p)}."
    hint = "Traduire l'énoncé par une formule explicite u_n = u_0 + c×n, puis interpréter le résultat numérique."
    return expr, {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


def _gen_generalites_vrai_faux(rng):
    """Vrai/Faux justifié : un élève propose une valeur pour u_p, correcte
    ou non — il faut recalculer par sympy pour trancher."""
    a = _nz(rng, -3, 3)
    b = _small(rng, -6, 6)
    c = _small(rng, -6, 6)
    expr = a * n**2 + b * n + c
    p_val = rng.randint(2, 7)
    correct = expr.subs(n, p_val)
    is_true = rng.random() < 0.5
    proposed = correct if is_true else correct + rng.choice([1, -1, 2, -2, 3])
    enonce = (
        f"La suite $(u_n)$ est définie pour tout $n \\geq 0$ par $u_n = {latex(expr)}$. "
        f"Un élève affirme que $u_{{{p_val}}} = {latex(proposed)}$. "
        "Cette affirmation est-elle vraie ou fausse ? Justifier."
    )
    if is_true:
        answer = "Vrai."
        steps = [f"Étape 1 — On calcule $u_{{{p_val}}} = {latex(correct)}$, ce qui correspond à l'affirmation."]
    else:
        answer = f"Faux : la valeur correcte est $u_{{{p_val}}} = {latex(correct)}$."
        steps = [
            f"Étape 1 — On calcule $u_{{{p_val}}} = {latex(correct)}$.",
            f"Étape 2 — Cette valeur diffère de celle proposée (${latex(proposed)}$) : l'affirmation est fausse.",
        ]
    hint = "Recalculer soi-même la valeur exacte avant de comparer à l'affirmation proposée."
    return expr, {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


# ── Suite arithmétique ──────────────────────────────────────────────────────

def _gen_arith_terme_general(rng):
    """Application directe : u_n = u0 + r·n puis évaluation en un rang."""
    u0 = _small(rng, -20, 20)
    r = _nz(rng, -9, 9)
    p_val = rng.randint(3, 12)
    expr = u0 + r * n
    u_p = expr.subs(n, p_val)
    enonce = (
        f"Soit $(u_n)$ une suite arithmétique de premier terme $u_0 = {u0}$ et de raison $r = {r}$. "
        f"Donner l'expression de $u_n$ en fonction de $n$, puis calculer $u_{{{p_val}}}$."
    )
    steps = [
        "Étape 1 — Pour une suite arithmétique, $u_n = u_0 + r \\times n$.",
        f"Étape 2 — Ici, $u_n = {latex(expr)}$.",
        f"Étape 3 — $u_{{{p_val}}} = {latex(u_p)}$.",
    ]
    answer = f"$u_n = {latex(expr)}$ et $u_{{{p_val}}} = {latex(u_p)}$"
    hint = "Utiliser la formule $u_n = u_0 + r \\times n$."
    return expr, {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


def _gen_arith_somme(rng):
    """Calcul à étapes : somme des N premiers termes, calculée par sympy
    (Sum().doit()), pas par une formule recopiée sans vérification."""
    u0 = _small(rng, -15, 15)
    r = _nz(rng, -7, 7)
    p_val = rng.randint(5, 15)
    term = u0 + r * k
    sum_expr = Sum(term, (k, 0, p_val))
    total = simplify(sum_expr.doit())
    u_last = term.subs(k, p_val)
    nb_termes = p_val + 1
    enonce = (
        f"Soit $(u_n)$ la suite arithmétique de premier terme $u_0={u0}$ et de raison $r={r}$. "
        f"Calculer la somme $S = u_0 + u_1 + \\dots + u_{{{p_val}}}$."
    )
    steps = [
        f"Étape 1 — $u_{{{p_val}}} = {latex(u_last)}$.",
        f"Étape 2 — Il y a {nb_termes} termes, donc $S = {nb_termes} \\times \\dfrac{{u_0 + u_{{{p_val}}}}}{{2}}$.",
        f"Étape 3 — $S = {latex(total)}$.",
    ]
    answer = f"$S = {latex(total)}$"
    hint = "Utiliser $S = (\\text{nombre de termes}) \\times \\dfrac{\\text{premier terme}+\\text{dernier terme}}{2}$."
    return sum_expr, {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


def _gen_arith_retrouver_raison(rng):
    """Inversé : retrouver r et u0 à partir de deux termes connus (système
    linéaire résolu par sympy.solve)."""
    u0 = _small(rng, -15, 15)
    r = _nz(rng, -8, 8)
    p_idx = rng.randint(2, 6)
    q_idx = p_idx + rng.randint(2, 6)
    up = u0 + r * p_idx
    uq = u0 + r * q_idx
    r_sym, u0_sym = symbols("r u0")
    sol = solve([Eq(u0_sym + r_sym * p_idx, up), Eq(u0_sym + r_sym * q_idx, uq)], [u0_sym, r_sym])
    if not sol:
        return None
    r_found, u0_found = sol[r_sym], sol[u0_sym]
    diff_n = q_idx - p_idx
    enonce = (
        f"Une suite arithmétique $(u_n)$ est telle que $u_{{{p_idx}}} = {up}$ et $u_{{{q_idx}}} = {uq}$. "
        "Déterminer la raison $r$ et le premier terme $u_0$."
    )
    steps = [
        f"Étape 1 — $u_{{{q_idx}}} - u_{{{p_idx}}} = {diff_n} \\times r$, donc "
        f"$r = \\dfrac{{{uq - up}}}{{{diff_n}}} = {latex(r_found)}$.",
        f"Étape 2 — $u_0 = u_{{{p_idx}}} - {p_idx} \\times r = {latex(u0_found)}$.",
    ]
    answer = f"$r = {latex(r_found)}$ et $u_0 = {latex(u0_found)}$"
    hint = "Utiliser $u_q - u_p = (q-p)\\times r$ pour isoler la raison, puis revenir à u_0."
    core = Eq(diff_n * r_sym, uq - up)
    return core, {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


def _gen_arith_probleme(rng):
    """Problème contextualisé : remboursement à taux fixe (suite
    arithmétique de raison négative)."""
    remb = rng.randint(20, 80)
    total_months = rng.randint(24, 60)
    capital = remb * total_months
    n_val = rng.randint(6, total_months - 2)
    expr = capital - remb * n
    reste = expr.subs(n, n_val)
    enonce = (
        f"Une personne emprunte {capital} € et rembourse chaque mois {remb} € (sans intérêt). "
        f"On note $u_n$ le capital restant dû après $n$ mois, avec $u_0 = {capital}$. "
        f"Exprimer $u_n$ en fonction de $n$, puis calculer le capital restant après {n_val} mois."
    )
    steps = [
        f"Étape 1 — Chaque mois, le capital restant diminue de {remb} € : $(u_n)$ est arithmétique de raison $r = -{remb}$.",
        f"Étape 2 — $u_n = {latex(expr)}$.",
        f"Étape 3 — $u_{{{n_val}}} = {latex(reste)}$.",
    ]
    answer = f"$u_n = {latex(expr)}$ ; après {n_val} mois, il reste {latex(reste)} € à rembourser."
    hint = "Modéliser par une suite arithmétique de raison négative égale à l'opposé du remboursement mensuel."
    return expr, {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


def _gen_arith_demonstration(rng):
    """Démonstration : établir, à partir d'une formule explicite, que la
    suite est arithmétique en calculant u_{n+1}-u_n de façon symbolique."""
    a = _nz(rng, -6, 6)
    b = _small(rng, -8, 8)
    expr = a * n + b
    # evaluate=False : sympy annule automatiquement a*(n+1)-a*n en une
    # constante dès la construction si on laisse l'évaluation par défaut,
    # ce qui masquerait la complexité réelle de la démonstration (mise en
    # facteur, développement) dans le score de difficulté.
    unsimplified = sympy.Add(expr.subs(n, n + 1), -expr, evaluate=False)
    diff_expr = simplify(unsimplified)
    enonce = (
        f"On considère la suite $(u_n)$ définie pour tout entier $n \\geq 0$ par $u_n = {latex(expr)}$. "
        "Démontrer que $(u_n)$ est une suite arithmétique et préciser sa raison."
    )
    steps = [
        f"Étape 1 — On calcule $u_{{n+1}} - u_n = {latex(expr.subs(n, n+1))} - ({latex(expr)})$.",
        f"Étape 2 — Après simplification, $u_{{n+1}} - u_n = {latex(diff_expr)}$, une constante indépendante de $n$.",
        f"Étape 3 — Donc $(u_n)$ est arithmétique de raison $r = {latex(diff_expr)}$.",
    ]
    answer = f"$(u_n)$ est arithmétique de raison $r = {latex(diff_expr)}$."
    hint = "Calculer u_{n+1} - u_n en fonction de n et vérifier que le résultat ne dépend pas de n."
    return unsimplified, {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


# ── Suite géométrique ───────────────────────────────────────────────────────

_Q_CHOICES = (Integer(2), Integer(3), Integer(-2), Rational(1, 2), Rational(3, 2),
              Rational(-1, 2), Rational(2, 3))


def _gen_geo_terme_general(rng):
    """Application directe : u_n = u0·q^n puis évaluation en un rang."""
    u0 = _nz(rng, -12, 12)
    q = rng.choice(_Q_CHOICES)
    p_val = rng.randint(2, 6)
    expr = u0 * q**n
    u_p = simplify(expr.subs(n, p_val))
    enonce = (
        f"Soit $(u_n)$ une suite géométrique de premier terme $u_0 = {u0}$ et de raison $q = {latex(q)}$. "
        f"Donner l'expression de $u_n$ en fonction de $n$, puis calculer $u_{{{p_val}}}$."
    )
    steps = [
        "Étape 1 — Pour une suite géométrique, $u_n = u_0 \\times q^n$.",
        f"Étape 2 — Ici, $u_n = {latex(expr)}$.",
        f"Étape 3 — $u_{{{p_val}}} = {latex(u_p)}$.",
    ]
    answer = f"$u_n = {latex(expr)}$ et $u_{{{p_val}}} = {latex(u_p)}$"
    hint = "Utiliser la formule $u_n = u_0 \\times q^n$."
    return expr, {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


def _gen_geo_somme(rng):
    """Calcul à étapes : somme géométrique calculée par sympy
    (Sum().doit()), formule $S=u_0\\frac{1-q^{N}}{1-q}$ vérifiée par calcul."""
    u0 = _nz(rng, -10, 10)
    q = rng.choice(_Q_CHOICES[:-2])  # évite les petites raisons trop proches de 1 en valeur absolue pour ce calcul
    p_val = rng.randint(4, 10)
    term = u0 * q**k
    sum_expr = Sum(term, (k, 0, p_val))
    total = simplify(sum_expr.doit())
    nb_termes = p_val + 1
    enonce = (
        f"Soit $(u_n)$ la suite géométrique de premier terme $u_0={u0}$ et de raison $q={latex(q)}$. "
        f"Calculer $S = u_0+u_1+\\dots+u_{{{p_val}}}$."
    )
    steps = [
        f"Étape 1 — $S$ comporte {nb_termes} termes et $q \\neq 1$, donc "
        f"$S = u_0 \\times \\dfrac{{1-q^{{{nb_termes}}}}}{{1-q}}$.",
        f"Étape 2 — $S = {latex(total)}$.",
    ]
    answer = f"$S = {latex(total)}$"
    hint = "Utiliser $S = u_0 \\times \\dfrac{1-q^{n+1}}{1-q}$ (valable car $q\\neq 1$)."
    return sum_expr, {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


def _gen_geo_retrouver_raison(rng):
    """Inversé : retrouver q puis u0 à partir de deux termes consécutifs
    connus (rapport constant d'une suite géométrique)."""
    u0 = _nz(rng, 1, 9) * rng.choice([1, -1])
    q = rng.choice(_Q_CHOICES)
    p_idx = rng.randint(1, 5)
    up = simplify(u0 * q**p_idx)
    u_next = simplify(u0 * q**(p_idx + 1))
    q_found = simplify(u_next / up)
    u0_found = simplify(up / q_found**p_idx)
    enonce = (
        f"Une suite géométrique $(u_n)$ est telle que $u_{{{p_idx}}} = {latex(up)}$ et "
        f"$u_{{{p_idx+1}}} = {latex(u_next)}$. Déterminer la raison $q$, puis $u_0$."
    )
    steps = [
        f"Étape 1 — $q = \\dfrac{{u_{{{p_idx+1}}}}}{{u_{{{p_idx}}}}} = {latex(q_found)}$.",
        f"Étape 2 — $u_0 = \\dfrac{{u_{{{p_idx}}}}}{{q^{{{p_idx}}}}} = {latex(u0_found)}$.",
    ]
    answer = f"$q = {latex(q_found)}$ et $u_0 = {latex(u0_found)}$"
    hint = "Le rapport de deux termes consécutifs d'une suite géométrique est constant et égal à q."
    core = Eq(q_found**p_idx * symbols("u0"), up)
    return core, {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


def _gen_geo_probleme(rng):
    """Problème contextualisé : intérêts composés (suite géométrique de
    raison $1+\\text{taux}$)."""
    capital = rng.choice([1000, 1500, 2000, 2500, 3000, 5000])
    taux = rng.choice([1, 2, 3, 4, 5])
    q = 1 + Rational(taux, 100)
    n_val = rng.randint(3, 10)
    expr = capital * q**n
    montant = simplify(expr.subs(n, n_val))
    montant_float = round(float(montant), 2)
    enonce = (
        f"Un capital de {capital} € est placé à intérêts composés au taux annuel de {taux}\\%. "
        f"On note $u_n$ le capital après $n$ années, avec $u_0 = {capital}$. "
        f"Exprimer $u_n$ en fonction de $n$, puis calculer $u_{{{n_val}}}$ (arrondi au centime)."
    )
    steps = [
        f"Étape 1 — Chaque année, le capital est multiplié par $q = 1 + \\dfrac{{{taux}}}{{100}} = {latex(q)}$ : "
        "$(u_n)$ est géométrique.",
        f"Étape 2 — $u_n = {latex(expr)}$.",
        f"Étape 3 — $u_{{{n_val}}} \\approx {montant_float}$ €.",
    ]
    answer = f"$u_n = {latex(expr)}$ ; $u_{{{n_val}}} \\approx {montant_float}$ €."
    hint = "Un taux d'intérêt composé se traduit par une suite géométrique de raison 1 + taux."
    return expr, {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


def _gen_geo_demonstration(rng):
    """Démonstration : établir, à partir d'une formule explicite, que la
    suite est géométrique en calculant le quotient u_{n+1}/u_n."""
    u0 = _nz(rng, 1, 6)
    q = rng.choice(_Q_CHOICES)
    expr = u0 * q**n
    # evaluate=False : sinon sympy simplifie q**(n+1)/q**n en q dès la
    # construction (mêmes bases), ce qui masquerait la complexité réelle du
    # calcul demandé dans le score de difficulté.
    unsimplified = sympy.Mul(expr.subs(n, n + 1), sympy.Pow(expr, -1, evaluate=False), evaluate=False)
    quotient_expr = simplify(unsimplified)
    enonce = (
        f"On considère la suite $(u_n)$ définie pour tout entier $n \\geq 0$ par $u_n = {latex(expr)}$. "
        "Démontrer que $(u_n)$ est une suite géométrique et préciser sa raison."
    )
    steps = [
        f"Étape 1 — Pour $u_n \\neq 0$, on calcule $\\dfrac{{u_{{n+1}}}}{{u_n}} = "
        f"\\dfrac{{{latex(expr.subs(n, n+1))}}}{{{latex(expr)}}}$.",
        f"Étape 2 — Après simplification, $\\dfrac{{u_{{n+1}}}}{{u_n}} = {latex(quotient_expr)}$, "
        "une constante indépendante de $n$.",
        f"Étape 3 — Donc $(u_n)$ est géométrique de raison $q = {latex(quotient_expr)}$.",
    ]
    answer = f"$(u_n)$ est géométrique de raison $q = {latex(quotient_expr)}$."
    hint = "Calculer le quotient u_{n+1}/u_n en fonction de n et vérifier qu'il ne dépend pas de n."
    return unsimplified, {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


# ── Sens de variation d'une suite ──────────────────────────────────────────

def _gen_variation_difference(rng):
    """Application directe : étudier le signe de u_{n+1}-u_n pour une
    suite affine en n (méthode de la différence)."""
    a = _nz(rng, -5, 5)
    b = _small(rng, -6, 6)
    expr = a * n + b
    diff_expr = simplify(expr.subs(n, n + 1) - expr)
    sens = "croissante" if diff_expr > 0 else ("décroissante" if diff_expr < 0 else "constante")
    signe = "positif" if diff_expr > 0 else ("négatif" if diff_expr < 0 else "nul")
    enonce = (
        f"On considère la suite $(u_n)$ définie pour tout $n\\geq0$ par $u_n = {latex(expr)}$. "
        "Étudier le sens de variation de cette suite."
    )
    steps = [
        f"Étape 1 — On calcule $u_{{n+1}}-u_n = {latex(expr.subs(n, n+1))} - ({latex(expr)}) = {latex(diff_expr)}$.",
        f"Étape 2 — Ce signe est {signe} pour tout $n$, donc la suite est {sens}.",
    ]
    answer = f"La suite $(u_n)$ est {sens} (car $u_{{n+1}}-u_n = {latex(diff_expr)}$)."
    hint = "Étudier le signe de u_{n+1} - u_n (méthode de la différence)."
    core = sympy.Add(expr.subs(n, n + 1), -expr, evaluate=False)
    return core, {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


def _gen_variation_quotient(rng):
    """Calcul à étapes : comparer u_{n+1}/u_n à 1 (méthode du quotient,
    valable ici car u_n garde un signe constant)."""
    u0 = _nz(rng, 1, 9)
    q = rng.choice([Rational(2), Rational(3), Rational(1, 2), Rational(1, 3), Rational(3, 2)])
    expr = u0 * q**n
    sens = "croissante" if q > 1 else ("décroissante" if q < 1 else "constante")
    comparaison = ">" if q > 1 else "<"
    enonce = (
        f"Soit $(u_n)$ la suite définie pour tout $n \\geq 0$ par $u_n = {latex(expr)}$ (avec $u_n>0$). "
        "Étudier le sens de variation de cette suite en comparant $\\dfrac{u_{n+1}}{u_n}$ à 1."
    )
    steps = [
        f"Étape 1 — $\\dfrac{{u_{{n+1}}}}{{u_n}} = {latex(q)}$ pour tout $n$.",
        f"Étape 2 — Comme $u_n>0$ et $\\dfrac{{u_{{n+1}}}}{{u_n}} {comparaison} 1$, la suite est {sens}.",
    ]
    answer = f"La suite est {sens} (quotient constant égal à ${latex(q)}$)."
    hint = "Comparer le quotient u_{n+1}/u_n à 1 (méthode valable car u_n garde un signe constant)."
    return expr, {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


def _gen_variation_parametre(rng):
    """Inversé : déterminer pour quelles valeurs d'un paramètre symbolique
    la suite est croissante (raisonnement sur le signe, pas un calcul
    numérique)."""
    b = _small(rng, -6, 6)
    a_sym = symbols("a")
    expr = a_sym * n + b
    unsimplified = expr.subs(n, n + 1) - expr
    diff_expr = simplify(unsimplified)
    b_terme = f" + {b}" if b > 0 else (f" - {abs(b)}" if b < 0 else "")
    enonce = (
        f"On considère la suite $(u_n)$ définie par $u_n = a\\,n{b_terme}$ où $a$ est un réel. "
        "Pour quelles valeurs de $a$ la suite $(u_n)$ est-elle croissante ?"
    )
    steps = [
        f"Étape 1 — $u_{{n+1}}-u_n = {latex(diff_expr)}$, une expression qui ne dépend pas de $n$.",
        "Étape 2 — La suite est croissante si et seulement si cette différence est positive ou nulle.",
        "Étape 3 — On obtient la condition $a \\geq 0$.",
    ]
    answer = "$(u_n)$ est croissante si et seulement si $a \\geq 0$."
    hint = "La suite est arithmétique de raison a : son sens de variation dépend uniquement du signe de a."
    return unsimplified, {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


def _gen_variation_interpretation(rng):
    """Interprétation contextualisée du sens de variation (signe de la
    raison d'une suite arithmétique appliqué à un modèle concret)."""
    u0 = rng.randint(50, 300)
    r = _nz(rng, -20, 20)
    expr = u0 + r * n
    sens = "augmente" if r > 0 else "diminue"
    contexte = rng.choice([
        "le nombre de visiteurs d'un site web chaque mois",
        "le stock d'un entrepôt chaque semaine",
        "la température d'un four chaque minute (modèle simplifié, en °C)",
    ])
    enonce = (
        f"On modélise {contexte} par une suite $(u_n)$ arithmétique, avec $u_0={u0}$ et $u_n = {latex(expr)}$. "
        "Que peut-on dire du sens de variation de cette suite ? Interpréter dans le contexte."
    )
    steps = [
        f"Étape 1 — La raison de la suite est $r={r}$.",
        f"Étape 2 — Comme $r {'>' if r > 0 else '<'} 0$, la suite est {'croissante' if r > 0 else 'décroissante'}.",
        f"Étape 3 — Dans le contexte, cela signifie que la quantité modélisée {sens} régulièrement.",
    ]
    answer = f"La suite est {'croissante' if r > 0 else 'décroissante'} : la quantité modélisée {sens} au cours du temps."
    hint = "Le signe de la raison détermine directement le sens de variation, à interpréter ensuite dans le contexte."
    return expr, {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


def _gen_variation_vrai_faux(rng):
    """Vrai/Faux justifié : peut-on généraliser le sens de variation
    observé sur deux termes seulement ? Vrai pour une suite arithmétique
    (raison constante), faux en général pour une suite quadratique en n."""
    p_val = rng.randint(1, 4)
    if rng.random() < 0.5:
        a = _nz(rng, -5, 5)
        b = _small(rng, -6, 6)
        expr = a * n + b
        d1 = simplify(expr.subs(n, p_val + 1) - expr.subs(n, p_val))
        claim_croissante = d1 > 0
        answer = (
            f"Vrai : $(u_n)$ est arithmétique de raison ${latex(d1)}$, donc "
            f"{'croissante' if d1 > 0 else 'décroissante'} pour tout $n$, pas seulement localement."
        )
        steps = [
            f"Étape 1 — $u_{{n+1}}-u_n = {latex(expr.subs(n, n+1) - expr)} = {latex(d1)}$ : différence constante.",
            "Étape 2 — Comme elle ne dépend pas de $n$, le comportement observé se généralise à tout $n$.",
        ]
    else:
        a = _nz(rng, -4, 4)
        b = _small(rng, -5, 5)
        c = _small(rng, -5, 5)
        expr = a * n**2 + b * n + c
        d1 = simplify(expr.subs(n, p_val + 1) - expr.subs(n, p_val))
        claim_croissante = d1 > 0
        answer = (
            "Faux : cette suite n'est pas arithmétique (elle est définie par un polynôme du second degré "
            "en $n$), donc $u_{n+1}-u_n$ dépend de $n$ ; on ne peut pas généraliser le comportement observé "
            "sur un seul couple de termes à toute la suite."
        )
        steps = [
            f"Étape 1 — $u_{{n+1}}-u_n = {latex(expr.subs(n, n+1) - expr)}$, une expression qui dépend de $n$.",
            "Étape 2 — Le signe de cette différence peut donc changer selon $n$ : on ne peut rien conclure "
            "pour tout $n$ à partir de deux termes.",
        ]
    enonce = (
        f"La suite $(u_n)$ est définie par $u_n = {latex(expr)}$. Un élève affirme, en observant "
        f"seulement $u_{{{p_val}}}$ et $u_{{{p_val+1}}}$, que la suite est "
        f"{'croissante' if claim_croissante else 'décroissante'} pour tout $n$. "
        "Cette généralisation est-elle valide ? Justifier."
    )
    hint = "Vérifier si la différence u_{n+1}-u_n est constante (suite arithmétique) ou dépend de n avant de généraliser."
    return expr.subs(n, n + 1) - expr, {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


# ── Calcul de sommes ─────────────────────────────────────────────────────

def _gen_sommes_arith(rng):
    """Application directe : somme des N premiers termes d'une suite
    arithmétique, calculée par sympy."""
    u0 = _small(rng, -12, 12)
    r = _nz(rng, -8, 8)
    p_val = rng.randint(6, 20)
    term = u0 + r * k
    sum_expr = Sum(term, (k, 0, p_val))
    total = simplify(sum_expr.doit())
    enonce = (
        f"On considère la suite arithmétique $(u_n)$ de premier terme $u_0={u0}$ et de raison $r={r}$. "
        f"Calculer $S = \\sum_{{k=0}}^{{{p_val}}} u_k$."
    )
    steps = [
        f"Étape 1 — $S$ contient {p_val + 1} termes, de $u_0$ à $u_{{{p_val}}}$.",
        f"Étape 2 — $S = (\\text{{nb termes}}) \\times \\dfrac{{u_0+u_{{{p_val}}}}}{{2}} = {latex(total)}$.",
    ]
    answer = f"$S = {latex(total)}$"
    hint = "Utiliser la formule de la somme des termes d'une suite arithmétique."
    return sum_expr, {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


def _gen_sommes_geo(rng):
    """Application directe/calcul à étapes : somme des N premiers termes
    d'une suite géométrique, calculée par sympy."""
    u0 = _nz(rng, -8, 8)
    q = rng.choice([Rational(2), Rational(3), Rational(-2), Rational(1, 2), Rational(3, 2)])
    p_val = rng.randint(4, 10)
    term = u0 * q**k
    sum_expr = Sum(term, (k, 0, p_val))
    total = simplify(sum_expr.doit())
    enonce = (
        f"On considère la suite géométrique $(u_n)$ de premier terme $u_0={u0}$ et de raison $q={latex(q)}$. "
        f"Calculer $S = \\sum_{{k=0}}^{{{p_val}}} u_k$."
    )
    steps = [
        f"Étape 1 — $S$ contient {p_val + 1} termes et $q \\neq 1$ : $S = u_0 \\times \\dfrac{{1-q^{{{p_val+1}}}}}{{1-q}}$.",
        f"Étape 2 — $S = {latex(total)}$.",
    ]
    answer = f"$S = {latex(total)}$"
    hint = "Utiliser la formule de la somme des termes d'une suite géométrique."
    return sum_expr, {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


def _gen_sommes_consecutifs(rng):
    """Calcul à étapes : somme de termes consécutifs qui ne commence pas à
    l'indice 0 — piège pédagogique du nombre de termes/du décalage."""
    kind = rng.choice(["arith", "geo"])
    p_val = rng.randint(3, 8)
    q_val = p_val + rng.randint(3, 10)
    if kind == "arith":
        u0 = _small(rng, -10, 10)
        r = _nz(rng, -6, 6)
        term = u0 + r * k
        nom = "arithmétique"
    else:
        u0 = _nz(rng, -6, 6)
        q = rng.choice([Rational(2), Rational(1, 2), Rational(3), Rational(-2)])
        term = u0 * q**k
        nom = "géométrique"
    sum_expr = Sum(term, (k, p_val, q_val))
    total = simplify(sum_expr.doit())
    nb = q_val - p_val + 1
    enonce = (
        f"Soit $(u_n)$ la suite {nom} définie par $u_n = {latex(term.subs(k, n))}$. "
        f"Calculer $S = u_{{{p_val}}}+u_{{{p_val+1}}}+\\dots+u_{{{q_val}}}$."
    )
    steps = [
        f"Étape 1 — La somme comporte {nb} termes, de $u_{{{p_val}}}$ à $u_{{{q_val}}}$ (et non {q_val} termes).",
        f"Étape 2 — $S = {latex(total)}$.",
    ]
    answer = f"$S = {latex(total)}$"
    hint = "Attention, la somme ne commence pas à l'indice 0 : recompter précisément le nombre de termes."
    return sum_expr, {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


def _gen_sommes_inverse(rng):
    """Inversé : connaissant la valeur de la somme des N premiers termes,
    retrouver N (résolution d'équation par sympy)."""
    u0 = _small(rng, 1, 10)
    r = _nz(rng, 1, 6)
    term = u0 + r * k
    N_sym = symbols("N", positive=True, integer=True)
    sum_formula = simplify(Sum(term, (k, 0, N_sym - 1)).doit())
    target_N = rng.randint(8, 20)
    target_S = sum_formula.subs(N_sym, target_N)
    eq = Eq(sum_formula, target_S)
    sols = solve(eq, N_sym)
    if not any(s == target_N for s in sols):
        return None
    enonce = (
        f"Soit $(u_n)$ la suite arithmétique de premier terme $u_0={u0}$ et de raison $r={r}$. "
        f"On note $S_N = u_0+u_1+\\dots+u_{{N-1}}$ la somme des $N$ premiers termes. "
        f"Sachant que $S_N = {latex(target_S)}$, déterminer $N$."
    )
    steps = [
        f"Étape 1 — $S_N = {latex(sum_formula)}$ (formule de la somme des $N$ premiers termes).",
        f"Étape 2 — On résout $S_N = {latex(target_S)}$, ce qui donne $N = {target_N}$.",
    ]
    answer = f"$N = {target_N}$"
    hint = "Exprimer S_N en fonction de N grâce à la formule de la somme arithmétique, puis résoudre l'équation."
    return eq, {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


def _gen_sommes_erreur(rng):
    """Erreur à corriger : oubli classique du dernier terme dans le
    comptage (erreur de type 'off-by-one')."""
    u0 = _small(rng, -10, 10)
    r = _nz(rng, -6, 6)
    p_val = rng.randint(5, 15)
    term = u0 + r * k
    if term.subs(k, p_val) == 0:
        return None
    sum_expr = Sum(term, (k, 0, p_val))
    correct_sum = simplify(sum_expr.doit())
    wrong_sum = simplify(correct_sum - term.subs(k, p_val))
    if wrong_sum == correct_sum:
        return None
    enonce = (
        f"Un élève calcule la somme $S = u_0+u_1+\\dots+u_{{{p_val}}}$ d'une suite arithmétique de "
        f"premier terme $u_0={u0}$ et de raison $r={r}$. Il trouve $S = {latex(wrong_sum)}$ en comptant "
        f"{p_val} termes au lieu de {p_val + 1}. Identifier son erreur et donner la valeur correcte de $S$."
    )
    steps = [
        f"Étape 1 — La somme va de $u_0$ à $u_{{{p_val}}}$, ce qui fait {p_val + 1} termes (et non {p_val}) : "
        "l'élève a oublié de compter le dernier terme.",
        f"Étape 2 — La valeur correcte est $S = {latex(correct_sum)}$.",
    ]
    answer = f"Erreur de comptage des termes ; la valeur correcte est $S = {latex(correct_sum)}$."
    hint = "Vérifier le nombre exact de termes entre les deux indices donnés (erreur classique de type 'off-by-one')."
    return sum_expr, {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


# ── Notion de limite d'une suite ───────────────────────────────────────────

def _gen_limite_polynomiale(rng):
    """Application directe : limite d'une suite polynomiale simple en $n$
    (le terme dominant impose la limite), calculée par sympy.limit."""
    a = _nz(rng, -5, 5)
    b = _small(rng, -6, 6)
    deg = rng.choice([1, 2])
    expr = a * n**deg + b * n if deg == 2 else a * n + b
    lim = limit(expr, n, oo)
    terme_dominant = a * n**deg
    enonce = f"Déterminer la limite de la suite $(u_n)$ définie par $u_n = {latex(expr)}$ lorsque $n$ tend vers $+\\infty$."
    steps = [
        f"Étape 1 — Le terme dominant est ${latex(terme_dominant)}$.",
        f"Étape 2 — $\\lim_{{n\\to+\\infty}} u_n = {latex(lim)}$.",
    ]
    answer = f"$\\lim_{{n\\to+\\infty}} u_n = {latex(lim)}$"
    hint = "La limite d'une somme de termes en n est déterminée par le terme de plus haut degré."
    return expr, {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


def _gen_limite_quotient(rng):
    """Calcul à étapes : limite d'une suite rationnelle (quotient
    affine/affine), calculée par sympy.limit."""
    a = _nz(rng, -5, 5)
    b = _small(rng, -6, 6)
    c = _nz(rng, -5, 5)
    d = _small(rng, -6, 6)
    expr = (a * n + b) / (c * n + d)
    # évite le cas b=d=0 (ou tout autre cas où sympy annule directement le
    # facteur n commun) : la fraction dégénère alors en une constante
    # indépendante de n, ce qui viderait l'exercice de son enjeu (aucun
    # quotient à étudier). Vérifié par calcul (dérivée nulle), pas deviné.
    if sympy.diff(expr, n) == 0:
        return None
    lim = limit(expr, n, oo)
    enonce = (
        f"Déterminer $\\lim_{{n\\to+\\infty}} u_n$ où $u_n = {latex(expr)}$ "
        "(pour $n$ assez grand pour que l'expression soit définie)."
    )
    steps = [
        "Étape 1 — On met en évidence le terme de plus haut degré au numérateur et au dénominateur.",
        f"Étape 2 — $\\lim_{{n\\to+\\infty}} u_n = \\dfrac{{{a}}}{{{c}}} = {latex(lim)}$.",
    ]
    answer = f"$\\lim_{{n\\to+\\infty}} u_n = {latex(lim)}$"
    hint = "Diviser numérateur et dénominateur par la plus haute puissance de n présente."
    return expr, {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


def _gen_limite_geometrique(rng):
    """Vrai/Faux justifié par étude de cas : classer la convergence d'une
    suite géométrique selon la position de $q$ par rapport à $-1$ et $1$."""
    u0 = _nz(rng, -8, 8)
    q = rng.choice([Rational(2), Rational(3), Rational(-3), Rational(1, 2),
                     Rational(-1, 2), Rational(2, 3), Integer(1), Integer(-2)])
    expr = u0 * q**n
    enonce = (
        f"Soit $(u_n)$ la suite géométrique définie par $u_n = {latex(expr)}$ (raison $q={latex(q)}$). "
        "Déterminer, en justifiant selon la valeur de $q$, si cette suite converge ou diverge, "
        "et préciser sa limite le cas échéant."
    )
    if q > 1:
        just = f"Comme $q={latex(q)} > 1$, la suite géométrique diverge (vers $+\\infty$ ou $-\\infty$ selon le signe de $u_0$)."
        lim = limit(expr, n, oo)
        answer_lim = f"${latex(lim)}$"
    elif q == 1:
        just = "Comme $q=1$, la suite est constante, égale à $u_0$."
        lim = limit(expr, n, oo)
        answer_lim = f"${latex(lim)}$"
    elif q >= 0:
        # 0 <= q < 1 : base positive, sympy.limit gère directement ce cas.
        just = f"Comme $0\\leq q={latex(q)}<1$, la suite géométrique converge vers 0."
        lim = limit(expr, n, oo)
        answer_lim = f"${latex(lim)}$"
    elif q > -1:
        # -1 < q < 0 : base négative, sympy.limit échoue sur l'oscillation
        # de signe de q^n (branche complexe de gruntz). On calcule à la
        # place la limite de la valeur absolue (toujours par sympy) : comme
        # |u_n| -> 0, on conclut u_n -> 0 par encadrement (suite bornée par
        # une suite qui tend vers 0).
        just = (f"Comme $-1<q={latex(q)}<0$, on a $|u_n| = |u_0|\\,|q|^n \\to 0$ (car $0\\leq|q|<1$), "
                "donc $u_n \\to 0$ par encadrement.")
        lim = limit(sympy.Abs(expr), n, oo)
        answer_lim = f"${latex(lim)}$"
    else:
        just = f"Comme $q={latex(q)} \\leq -1$, la suite géométrique n'a pas de limite (elle oscille en divergeant)."
        answer_lim = "n'existe pas (la suite diverge sans limite)"
    steps = [
        "Étape 1 — On identifie la position de $q$ par rapport à $-1$ et $1$.",
        f"Étape 2 — {just}",
    ]
    answer = f"La limite est {answer_lim}. {just}"
    hint = "Comparer |q| à 1 (et distinguer le cas q ≤ -1) pour conclure sur la convergence d'une suite géométrique."
    # La vraie complexité de cet exercice est la classification par cas, pas
    # l'expression u0*q^n elle-même (très simple isolément) : on la reflète
    # en renvoyant, pour le score de difficulté, le Piecewise à 4 branches
    # qui représente authentiquement le raisonnement demandé (un Piecewise
    # EST l'objet mathématique correspondant à une étude de cas).
    q_sym = symbols("q")
    core = sympy.Piecewise(
        (oo, q_sym > 1),
        (u0, sympy.Eq(q_sym, 1)),
        (0, q_sym > -1),
        (S.NaN, True),
    )
    return core, {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


def _gen_limite_interpretation(rng):
    """Interprétation contextualisée : un modèle de stabilisation/
    saturation $u_n = L - A q^n$ avec $0<q<1$."""
    L = rng.randint(100, 500)
    A = rng.randint(10, 80)
    q = rng.choice([Rational(1, 2), Rational(2, 3), Rational(3, 4), Rational(4, 5)])
    expr = L - A * q**n
    lim = limit(expr, n, oo)
    contexte = rng.choice([
        "le nombre d'utilisateurs actifs d'une application (en milliers)",
        "la quantité de médicament présente dans le sang (en mg)",
        "la température d'un objet qui refroidit vers la température ambiante (en °C)",
    ])
    enonce = (
        f"On modélise {contexte} par $u_n = {latex(expr)}$ où $n$ est le temps écoulé. "
        "Déterminer la limite de $(u_n)$ quand $n \\to +\\infty$ et interpréter ce résultat dans le contexte."
    )
    steps = [
        f"Étape 1 — Comme $0<q={latex(q)}<1$, on a $\\lim_{{n\\to+\\infty}} q^n = 0$.",
        f"Étape 2 — Donc $\\lim_{{n\\to+\\infty}} u_n = {latex(lim)}$.",
    ]
    answer = f"$\\lim_{{n\\to+\\infty}} u_n = {latex(lim)}$ : la quantité modélisée se stabilise autour de {latex(lim)}."
    hint = "Une suite du type L - A×q^n avec 0<q<1 tend vers L : c'est un modèle de stabilisation/saturation."
    return expr, {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


def _gen_limite_erreur(rng):
    """Erreur à corriger : confusion entre forme indéterminée (∞/∞) et
    absence de limite — l'indétermination se lève, elle ne prouve rien
    seule."""
    a = _nz(rng, -5, 5)
    b = _small(rng, -6, 6)
    c = _nz(rng, -5, 5)
    d = _small(rng, -6, 6)
    expr = (a * n + b) / (c * n + d)
    # même garde que _gen_limite_quotient (vérifiée par calcul, pas devinée) :
    # éviter une fraction qui dégénère en constante, ce qui viderait
    # l'exercice de son enjeu (lever une indétermination).
    if sympy.diff(expr, n) == 0:
        return None
    lim_correct = limit(expr, n, oo)
    enonce = (
        f"Un élève doit calculer $\\lim_{{n\\to+\\infty}} u_n$ où $u_n = {latex(expr)}$. Il affirme que "
        "\"comme le numérateur et le dénominateur tendent tous les deux vers l'infini, la limite n'existe pas\". "
        "Cette affirmation est-elle correcte ? Justifier et donner la bonne valeur si besoin."
    )
    steps = [
        "Étape 1 — Une forme $\\infty/\\infty$ est indéterminée, ce qui NE SIGNIFIE PAS que la limite n'existe pas : "
        "il faut lever l'indétermination.",
        "Étape 2 — On met en facteur le terme de plus haut degré au numérateur et au dénominateur pour simplifier.",
        f"Étape 3 — On obtient $\\lim_{{n\\to+\\infty}} u_n = {latex(lim_correct)}$ : la limite existe bien.",
    ]
    answer = f"Faux : l'affirmation confond forme indéterminée et absence de limite. La limite existe et vaut ${latex(lim_correct)}$."
    hint = "Une forme indéterminée ∞/∞ nécessite de lever l'indétermination (factorisation) ; elle ne signifie pas que la limite n'existe pas."
    return expr, {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


@dataclass(frozen=True)
class Family:
    id: str
    level: int  # 1 (facile) .. 5 (défi) — étiquette de départ, revalidée par real_difficulty_score
    label: str
    generate: Callable[[random.Random], Optional[tuple]]
    structure_hint: str  # explique la structure pour la consigne pédagogique (fallback du hint)
    rule_hint: str  # règle/méthode principale à mobiliser (fallback du hint)
    notion: str  # notion exacte du Chapitre_1 (voir exercises_bank_premiere.json)


FAMILIES: tuple[Family, ...] = (
    # Généralités sur les suites
    Family("generalites_explicite", 2, "Terme d'une suite définie explicitement", _gen_generalites_explicite,
           "une suite définie par une formule explicite non affine", "substituer directement la valeur de n",
           NOTION_GENERALITES),
    Family("generalites_recurrence", 2, "Termes d'une suite définie par récurrence", _gen_generalites_recurrence,
           "une suite définie par une relation de récurrence affine", "dérouler la relation terme à terme",
           NOTION_GENERALITES),
    Family("generalites_inverse", 3, "Retrouver le premier terme", _gen_generalites_inverse,
           "une relation de récurrence dont on connaît un terme", "résoudre une équation d'inconnue u_0",
           NOTION_GENERALITES),
    Family("generalites_interpretation", 2, "Interprétation d'un modèle par suite", _gen_generalites_interpretation,
           "une suite modélisant une évolution concrète", "traduire l'énoncé en formule puis interpréter",
           NOTION_GENERALITES),
    Family("generalites_vrai_faux", 2, "Vrai/Faux sur un terme de suite", _gen_generalites_vrai_faux,
           "une valeur de terme proposée à vérifier", "recalculer la valeur exacte avant de juger",
           NOTION_GENERALITES),

    # Suite arithmétique
    Family("arith_terme_general", 1, "Terme général d'une suite arithmétique", _gen_arith_terme_general,
           "une suite arithmétique", "la formule u_n = u_0 + r×n",
           NOTION_ARITHMETIQUE),
    Family("arith_somme", 2, "Somme de termes d'une suite arithmétique", _gen_arith_somme,
           "une somme de termes consécutifs d'une suite arithmétique",
           "S = (nombre de termes) × (premier+dernier)/2", NOTION_ARITHMETIQUE),
    Family("arith_retrouver_raison", 3, "Retrouver la raison d'une suite arithmétique", _gen_arith_retrouver_raison,
           "deux termes connus d'une suite arithmétique", "résoudre le système linéaire associé",
           NOTION_ARITHMETIQUE),
    Family("arith_probleme_contextualise", 3, "Problème contextualisé (remboursement)", _gen_arith_probleme,
           "un remboursement à taux fixe", "modéliser par une suite arithmétique de raison négative",
           NOTION_ARITHMETIQUE),
    Family("arith_demonstration", 5, "Démonstration : suite arithmétique", _gen_arith_demonstration,
           "une suite définie par une formule explicite affine", "calculer u_{n+1}-u_n symboliquement",
           NOTION_ARITHMETIQUE),

    # Suite géométrique
    Family("geo_terme_general", 2, "Terme général d'une suite géométrique", _gen_geo_terme_general,
           "une suite géométrique", "la formule u_n = u_0 × q^n", NOTION_GEOMETRIQUE),
    Family("geo_somme", 3, "Somme de termes d'une suite géométrique", _gen_geo_somme,
           "une somme de termes consécutifs d'une suite géométrique",
           "S = u_0 × (1-q^N)/(1-q)", NOTION_GEOMETRIQUE),
    Family("geo_retrouver_raison", 3, "Retrouver la raison d'une suite géométrique", _gen_geo_retrouver_raison,
           "deux termes consécutifs connus d'une suite géométrique", "diviser deux termes consécutifs",
           NOTION_GEOMETRIQUE),
    Family("geo_probleme_contextualise", 3, "Problème contextualisé (intérêts composés)", _gen_geo_probleme,
           "un placement à intérêts composés", "modéliser par une suite géométrique de raison 1+taux",
           NOTION_GEOMETRIQUE),
    Family("geo_demonstration", 5, "Démonstration : suite géométrique", _gen_geo_demonstration,
           "une suite définie par une formule explicite exponentielle en n", "calculer u_{n+1}/u_n symboliquement",
           NOTION_GEOMETRIQUE),

    # Sens de variation d'une suite
    Family("variation_difference", 2, "Signe de u_{n+1}-u_n", _gen_variation_difference,
           "une suite affine en n", "étudier le signe de la différence de deux termes consécutifs",
           NOTION_VARIATION),
    Family("variation_quotient", 2, "Comparaison du quotient à 1", _gen_variation_quotient,
           "une suite géométrique à termes positifs", "comparer u_{n+1}/u_n à 1", NOTION_VARIATION),
    Family("variation_parametre", 4, "Condition sur un paramètre", _gen_variation_parametre,
           "une suite dépendant d'un paramètre symbolique", "étudier le signe symbolique de la différence",
           NOTION_VARIATION),
    Family("variation_interpretation", 2, "Interprétation du sens de variation", _gen_variation_interpretation,
           "un modèle concret croissant ou décroissant", "relier le signe de la raison au contexte",
           NOTION_VARIATION),
    Family("variation_vrai_faux", 3, "Généralisation valide ou non ?", _gen_variation_vrai_faux,
           "une généralisation proposée à partir de deux termes", "vérifier si la différence est constante",
           NOTION_VARIATION),

    # Calcul de sommes
    Family("sommes_arith", 2, "Somme des N premiers termes (arithmétique)", _gen_sommes_arith,
           "une somme de termes d'une suite arithmétique", "la formule de somme arithmétique",
           NOTION_SOMMES),
    Family("sommes_geo", 3, "Somme des N premiers termes (géométrique)", _gen_sommes_geo,
           "une somme de termes d'une suite géométrique", "la formule de somme géométrique",
           NOTION_SOMMES),
    Family("sommes_consecutifs", 3, "Somme de termes non consécutifs à 0", _gen_sommes_consecutifs,
           "une somme de termes qui ne commence pas à l'indice 0", "recompter précisément le nombre de termes",
           NOTION_SOMMES),
    Family("sommes_inverse", 4, "Retrouver le nombre de termes", _gen_sommes_inverse,
           "une somme connue dont on cherche le nombre de termes", "résoudre l'équation S_N = valeur connue",
           NOTION_SOMMES),
    Family("sommes_erreur", 3, "Erreur de comptage à corriger", _gen_sommes_erreur,
           "une résolution erronée par oubli d'un terme", "recompter les termes entre les deux indices",
           NOTION_SOMMES),

    # Notion de limite d'une suite
    Family("limite_polynomiale", 2, "Limite d'une suite polynomiale", _gen_limite_polynomiale,
           "une suite polynomiale simple en n", "le terme dominant impose la limite", NOTION_LIMITE),
    Family("limite_quotient", 3, "Limite d'une suite rationnelle", _gen_limite_quotient,
           "un quotient de deux expressions affines en n", "diviser par la puissance dominante",
           NOTION_LIMITE),
    Family("limite_geometrique", 4, "Classification de la limite géométrique", _gen_limite_geometrique,
           "une suite géométrique de raison quelconque", "comparer |q| à 1 selon les cas", NOTION_LIMITE),
    Family("limite_interpretation", 2, "Interprétation d'une limite (saturation)", _gen_limite_interpretation,
           "un modèle de stabilisation L - A×q^n", "la limite de q^n quand 0<q<1", NOTION_LIMITE),
    Family("limite_erreur", 3, "Erreur : forme indéterminée mal interprétée", _gen_limite_erreur,
           "une forme indéterminée ∞/∞ mal interprétée", "lever l'indétermination avant de conclure",
           NOTION_LIMITE),
)

FAMILIES_BY_NOTION: dict[str, tuple[Family, ...]] = {}
for _fam in FAMILIES:
    FAMILIES_BY_NOTION.setdefault(_fam.notion, []).append(_fam)
FAMILIES_BY_NOTION = {notion: tuple(fams) for notion, fams in FAMILIES_BY_NOTION.items()}


def build_exercise(family: Family, rng: random.Random) -> Optional[dict]:
    """Construit un exercice complet à partir d'une famille. Renvoie None
    si la structure tirée dégénère (voir chaque _gen_xxx) — dans ce cas
    l'appelant retire simplement une nouvelle graine."""
    result = family.generate(rng)
    if result is None:
        return None
    core_expr, notes = result
    if core_expr is None:
        return None

    score = real_difficulty_score(core_expr)
    real_level = _difficulty_bucket_from_score(score)
    hint = notes.get("hint") or f"Reconnais {family.structure_hint} : {family.rule_hint}."

    return {
        "enonce": notes["enonce"],
        "answer": notes["answer"],
        "hint": hint,
        "solution_steps": notes["steps"],
        "chapter_id": CHAPTER_ID,
        "notion": family.notion,
        "difficulty": real_level,
        "difficulty_label": LEVEL_META[real_level]["label"],
        "difficulty_emoji": LEVEL_META[real_level]["emoji"],
        "family": family.id,
        "family_label": family.label,
        "declared_level": family.level,
        "complexity_score": score,
        "source": "generated",
    }


def generate_one(family_id: str, seed: Optional[int] = None, max_attempts: int = 25) -> dict:
    rng = random.Random(seed)
    fam = next(f for f in FAMILIES if f.id == family_id)
    for _ in range(max_attempts):
        ex = build_exercise(fam, rng)
        if ex is not None:
            return ex
    raise RuntimeError(f"Impossible de générer un exercice valide pour la famille {family_id!r}")


def generate_pool(per_family: int = 12, seed: int = 20260818, notion: Optional[str] = None) -> list[dict]:
    """Génère un pool diversifié : `per_family` exercices distincts par
    famille, avec déduplication par signature d'énoncé (aucun couple
    d'exercices identiques) et alternance round-robin des familles dans
    l'ordre de sortie (jamais deux exercices consécutifs de la même
    famille). Si `notion` est fourni, seules les familles de cette notion
    sont utilisées (utile pour produire un pool par notion)."""
    families = FAMILIES_BY_NOTION[notion] if notion is not None else FAMILIES
    rng = random.Random(seed)
    per_family_pool: dict[str, list[dict]] = {}
    for family in families:
        seen_signatures = set()
        items = []
        attempts = 0
        while len(items) < per_family and attempts < per_family * 50:
            attempts += 1
            ex = build_exercise(family, rng)
            if ex is None:
                continue
            signature = (ex["family"], ex["enonce"])
            if signature in seen_signatures:
                continue
            seen_signatures.add(signature)
            items.append(ex)
        per_family_pool[family.id] = items

    pool: list[dict] = []
    idx = 0
    while any(per_family_pool.values()):
        family = families[idx % len(families)]
        bucket = per_family_pool.get(family.id) or []
        if bucket:
            pool.append(bucket.pop(0))
        idx += 1
        if idx > 200000:
            break
    # IDs entiers, offset distinct de derivatives.GENERATED_ID_OFFSET
    # (900_000) pour ne jamais entrer en collision si les pools sont
    # fusionnés dans la même banque — voir server.py::api_exercise qui
    # attend un id entier sur la route /api/exercise/<int:exercise_id>.
    for i, ex in enumerate(pool):
        ex["id"] = GENERATED_ID_OFFSET + i
    return pool
