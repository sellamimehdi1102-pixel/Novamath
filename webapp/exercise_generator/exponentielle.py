"""Génération symbolique d'exercices sur la fonction exponentielle (Première,
Chapitre_5).

Contexte du chantier : un audit a montré que Chapitre_5 était le chapitre le
plus redondant de la banque Première (jusqu'à 98% de redondance sur "Lien
avec les suites géométriques"), avec ~59 exercices par notion mais très peu
de gabarits de phrase réellement distincts — le reste n'étant que des
variations numériques d'un même énoncé.

Ce module reproduit le patron de `webapp/exercise_generator/derivatives.py`
(moteur du Chapitre_3, en production) : dataclass `Family`, fonctions
`_gen_xxx(rng)` tirant des paramètres aléatoires, correction garantie par
`sympy` (jamais de calcul « à la main » en Python), `real_difficulty_score()`
recalculée depuis la complexité réelle de l'expression produite, et
`generate_pool()` avec déduplication + alternance round-robin.

Adaptation nécessaire par rapport à `derivatives.py` : là où le Chapitre_3
ne couvre qu'un seul type de tâche (« calculer f'(x) »), le Chapitre_5
couvre six notions et des types de raisonnement très différents (simplifier,
résoudre une équation/inéquation, justifier un vrai/faux, corriger une
erreur, interpréter un contexte de suite géométrique...). Chaque `_gen_xxx`
renvoie donc directement le contenu pédagogique complet (énoncé, réponse,
étapes, indice, score de complexité) plutôt qu'une simple expression que
`build_exercise` mettrait en forme de façon uniforme — mais la garantie
« toute réponse est calculée par sympy, jamais inventée » est strictement
préservée dans chaque générateur.
"""
import random
from dataclasses import dataclass
from typing import Callable, Optional

import sympy
from sympy import (
    Add, And, Eq, Rational, S, diff, exp, latex, limit, oo, simplify, solve,
    symbols,
)

x, n = symbols("x n")

CHAPTER_ID = "Chapitre_5"

# Notions exactes (avec accents) telles que présentes dans
# exercises_bank_premiere.json — vérifiées avant écriture de ce module.
NOTION_PROPRIETES_ALGEBRIQUES = "Propriétés algébriques"
NOTION_NOTATION_E = "Nouvelle notation et nombre e"
NOTION_FONCTION_EXPONENTIELLE = "Fonction exponentielle"
NOTION_COURBE = "Courbe représentative"
NOTION_PROPRIETES_ANALYTIQUES = "Propriétés analytiques"
NOTION_SUITES_GEOMETRIQUES = "Lien avec les suites géométriques"

# Offset choisi au-dessus de celui du Chapitre_3 (900_000) et très au-dessus
# du plus grand id possible d'une banque curée (~2000 exercices max par
# classe aujourd'hui) : voir GENERATED_ID_OFFSET dans derivatives.py pour la
# même contrainte (route Flask /api/exercise/<int:exercise_id> attend un id
# entier, contrat BANK_BY_ID).
GENERATED_ID_OFFSET = 920_000


def _nz(rng: random.Random, lo: int, hi: int) -> int:
    """Entier non nul dans [lo, hi] — évite les coefficients qui
    dégénèrent la structure voulue (ex: un exposant nul rendrait une
    équation triviale)."""
    choices = [k for k in range(lo, hi + 1) if k != 0]
    return rng.choice(choices)


def _small(rng: random.Random, lo=-9, hi=9) -> int:
    return rng.randint(lo, hi)


LEVEL_META = {
    1: {"emoji": "🟢", "label": "Niveau 1 — Fondamental"},
    2: {"emoji": "🟡", "label": "Niveau 2 — Intermédiaire"},
    3: {"emoji": "🟠", "label": "Niveau 3 — Avancé"},
    4: {"emoji": "🔴", "label": "Niveau 4 — Difficile"},
    5: {"emoji": "🟣", "label": "Niveau 5 — Défi"},
}


def real_difficulty_score(exprs, extra: float = 0.0) -> float:
    """Complexité algébrique réelle, dans le même esprit que
    `derivatives.real_difficulty_score` : combine le nombre d'opérations
    sympy (`count_ops`) des expressions impliquées et des bonus explicites
    pour les mécanismes qui alourdissent réellement le raisonnement
    (résolution d'équation/inéquation, contexte à interpréter, comparaison
    à justifier...). `exprs` peut être une unique expression sympy ou une
    liste d'expressions ; `extra` porte les bonus spécifiques à la famille."""
    if not isinstance(exprs, (list, tuple)):
        exprs = [exprs]
    score = 0.0
    for e in exprs:
        try:
            score += float(sympy.sympify(e).count_ops())
        except Exception:
            pass
    return round(score + extra, 2)


def _difficulty_bucket_from_score(score: float) -> int:
    """Mêmes bornes que `derivatives._difficulty_bucket_from_score` —
    cohérence de calibration entre chapitres du même niveau scolaire."""
    if score <= 2:
        return 1
    if score <= 5:
        return 2
    if score <= 8:
        return 3
    if score <= 11:
        return 4
    return 5


def _latex_inf(v) -> str:
    """`sympy.latex` rend `oo` par `\\infty` sans signe : on force le `+`
    conventionnel en français pour une limite tendant vers $+\\infty$."""
    if v == oo:
        return "+\\infty"
    if v == -oo:
        return "-\\infty"
    return latex(v)


def _fmt_interval_from_and(rel) -> str:
    """Formate un `And(bound1 < x, x < bound2)` renvoyé par `sympy.solve`
    sur une inéquation affine en notation d'intervalle français, par ex.
    `]-\\infty ; -1[`. Les bornes infinies utilisent `\\infty`."""
    lo_bound, hi_bound = None, None
    args = rel.args if isinstance(rel, And) else (rel,)
    for r in args:
        left, right = r.lhs, r.rhs
        if right == x:
            lo_bound = left
        elif left == x:
            hi_bound = right
    def _side(v, is_lo):
        if v is None:
            return "-\\infty" if is_lo else "+\\infty"
        return _latex_inf(v)
    return f"]{_side(lo_bound, True)} ; {_side(hi_bound, False)}["


# ═══════════════════════════════════════════════════════════════════════
# Notion 1 — Propriétés algébriques : exp(a+b)=exp(a)exp(b), exp(-a)=1/exp(a),
# (exp(a))^n = exp(na), exp(a)/exp(b) = exp(a-b).
# ═══════════════════════════════════════════════════════════════════════

def _gen_alg_produit(rng: random.Random) -> Optional[dict]:
    a, b = _small(rng, -8, 8), _small(rng, -8, 8)
    while a == 0 or b == 0:
        a, b = _small(rng, -8, 8), _small(rng, -8, 8)
    expr = exp(a) * exp(b)
    result = simplify(expr)
    enonce = f"Simplifier l'expression $A = e^{{{a}}} \\times e^{{{b}}}$."
    steps = [
        f"Étape 1 — On reconnaît un produit de deux exponentielles : $e^{{{a}}} \\times e^{{{b}}}$.",
        f"Étape 2 — On applique la propriété $e^{{p}} \\times e^{{q}} = e^{{p+q}}$ avec $p={a}$ et $q={b}$ : "
        f"$A = e^{{{a}+({b})}} = e^{{{a+b}}}$.",
    ]
    return {
        "enonce": enonce,
        "answer": f"$A = e^{{{a+b}}}$",
        "hint": "Le produit de deux exponentielles se transforme en une exponentielle dont l'exposant est la somme des exposants.",
        "steps": steps,
        "score": real_difficulty_score([expr, result]),
    }


def _gen_alg_quotient(rng: random.Random) -> Optional[dict]:
    a, b = _small(rng, -8, 8), _small(rng, -8, 8)
    while a == 0 or b == 0:
        a, b = _small(rng, -8, 8), _small(rng, -8, 8)
    expr = exp(a) / exp(b)
    result = simplify(expr)
    enonce = f"Simplifier l'expression $B = \\dfrac{{e^{{{a}}}}}{{e^{{{b}}}}}$."
    steps = [
        f"Étape 1 — On reconnaît un quotient de deux exponentielles : $\\dfrac{{e^{{{a}}}}}{{e^{{{b}}}}}$.",
        f"Étape 2 — On applique la propriété $\\dfrac{{e^{{p}}}}{{e^{{q}}}} = e^{{p-q}}$ avec $p={a}$ et $q={b}$ : "
        f"$B = e^{{{a}-({b})}} = e^{{{a - b}}}$.",
    ]
    return {
        "enonce": enonce,
        "answer": f"$B = e^{{{a - b}}}$",
        "hint": "Le quotient de deux exponentielles se transforme en une exponentielle dont l'exposant est la différence des exposants.",
        "steps": steps,
        "score": real_difficulty_score([expr, result]),
    }


def _gen_alg_puissance(rng: random.Random) -> Optional[dict]:
    a = _small(rng, -5, 5)
    while a == 0:
        a = _small(rng, -5, 5)
    m = rng.choice([2, 3, 4, -2, -3])
    expr = exp(a) ** m
    result = simplify(expr)
    enonce = f"Simplifier l'expression $C = \\left(e^{{{a}}}\\right)^{{{m}}}$."
    steps = [
        f"Étape 1 — On reconnaît une puissance d'une exponentielle : $\\left(e^{{{a}}}\\right)^{{{m}}}$.",
        f"Étape 2 — On applique la propriété $\\left(e^{{p}}\\right)^{{k}} = e^{{kp}}$ avec $p={a}$ et $k={m}$ : "
        f"$C = e^{{{m}\\times {a}}} = e^{{{m * a}}}$.",
    ]
    return {
        "enonce": enonce,
        "answer": f"$C = e^{{{m * a}}}$",
        "hint": "Une puissance d'une exponentielle se transforme en une exponentielle dont l'exposant est multiplié.",
        "steps": steps,
        "score": real_difficulty_score([expr, result]),
    }


def _gen_alg_inverse(rng: random.Random) -> Optional[dict]:
    a = _small(rng, -9, 9)
    while a == 0:
        a = _small(rng, -9, 9)
    expr = 1 / exp(a)
    result = simplify(expr)
    enonce = f"Simplifier l'expression $D = \\dfrac{{1}}{{e^{{{a}}}}}$."
    steps = [
        f"Étape 1 — On reconnaît l'inverse d'une exponentielle : $\\dfrac{{1}}{{e^{{{a}}}}}$.",
        f"Étape 2 — On applique la propriété $\\dfrac{{1}}{{e^{{p}}}} = e^{{-p}}$ avec $p={a}$ : "
        f"$D = e^{{-({a})}} = e^{{{-a}}}$.",
    ]
    return {
        "enonce": enonce,
        "answer": f"$D = e^{{{-a}}}$",
        "hint": "L'inverse d'une exponentielle se transforme en une exponentielle d'exposant opposé.",
        "steps": steps,
        "score": real_difficulty_score([expr, result]),
    }


def _gen_alg_valeur_connue(rng: random.Random) -> Optional[dict]:
    """Choix de méthode : on ne donne pas explicitement $e^a$ et $e^b$
    numériquement, mais on nomme $A=e^a$ et $B=e^b$ ; il faut reconnaître
    quelle propriété algébrique exprime $e^{a+b}$, $e^{a-b}$ ou $e^{2a}$ en
    fonction de $A$ et $B$ sans recalculer les exposants."""
    a, b = _nz(rng, -6, 6), _nz(rng, -6, 6)
    op = rng.choice(["somme", "difference", "double"])
    if op == "somme":
        target_exp = a + b
        exposant_txt = f"{a} + ({b})" if b < 0 else f"{a} + {b}"
        question = f"Exprimer $e^{{{exposant_txt}}}$ en fonction de $A$ et $B$."
        formula = "$e^{a+b} = e^a \\times e^b = A \\times B$"
        answer_txt = "$A \\times B$"
    elif op == "difference":
        target_exp = a - b
        exposant_txt = f"{a} - ({b})" if b < 0 else f"{a} - {b}"
        question = f"Exprimer $e^{{{exposant_txt}}}$ en fonction de $A$ et $B$."
        formula = "$e^{a-b} = \\dfrac{e^a}{e^b} = \\dfrac{A}{B}$"
        answer_txt = "$\\dfrac{A}{B}$"
    else:
        target_exp = 2 * a
        question = f"Exprimer $e^{{{2*a}}}$ en fonction de $A$."
        formula = "$e^{2a} = \\left(e^a\\right)^2 = A^2$"
        answer_txt = "$A^2$"
    check_expr = exp(target_exp)
    enonce = (
        f"On pose $A = e^{{{a}}}$ et $B = e^{{{b}}}$ (on ne connaît pas leurs valeurs numériques). "
        + question
    )
    steps = [
        "Étape 1 — On repère la relation entre l'exposant demandé et les exposants $a$ et $b$ connus.",
        f"Étape 2 — On applique la propriété algébrique correspondante : {formula}.",
    ]
    return {
        "enonce": enonce,
        "answer": answer_txt,
        "hint": "Pas besoin de connaître la valeur numérique de $A$ et $B$ : seule la relation entre les exposants compte.",
        "steps": steps,
        "score": real_difficulty_score(check_expr, extra=2.0),
    }


def _gen_alg_erreur_a_corriger(rng: random.Random) -> Optional[dict]:
    a, b = _nz(rng, -6, 6), _nz(rng, -6, 6)
    faux = f"e^{{{a}}} \\times e^{{{b}}} = e^{{{a}}} + e^{{{b}}}"
    correct_expr = exp(a) * exp(b)
    correct_value = simplify(correct_expr)
    enonce = (
        f"Un élève affirme que $e^{{{a}}} \\times e^{{{b}}} = e^{{{a}}} + e^{{{b}}}$. "
        "Cette affirmation est-elle correcte ? Justifier et donner le bon résultat."
    )
    steps = [
        "Étape 1 — On rappelle que la fonction exponentielle transforme les sommes en produits, "
        "pas les produits en sommes : $e^{p+q} = e^p \\times e^q$, ce qui ne se lit PAS "
        "$e^p \\times e^q = e^p + e^q$.",
        f"Étape 2 — On applique la bonne propriété : $e^{{{a}}} \\times e^{{{b}}} = e^{{{a}+({b})}} = e^{{{a+b}}}$.",
    ]
    return {
        "enonce": enonce,
        "answer": f"Faux. $e^{{{a}}} \\times e^{{{b}}} = e^{{{a + b}}}$ (et non $e^{{{a}}} + e^{{{b}}}$).",
        "hint": "L'erreur classique confond la propriété du produit ($e^{p+q}=e^p e^q$) avec une addition des exponentielles.",
        "steps": steps,
        "score": real_difficulty_score([correct_expr, correct_value], extra=1.5),
    }


def _gen_alg_vrai_faux(rng: random.Random) -> Optional[dict]:
    a, b = _nz(rng, -7, 7), _nz(rng, -7, 7)
    is_true = rng.choice([True, False])
    lhs_exp = a + b
    if is_true:
        rhs_exp = a + b
    else:
        # affirmation fausse construite en perturbant l'exposant annoncé
        delta = _nz(rng, 1, 4)
        rhs_exp = a + b + delta
    statement = f"e^{{{a}}} \\times e^{{{b}}} = e^{{{rhs_exp}}}"
    lhs_val = simplify(exp(a) * exp(b))
    rhs_val = simplify(exp(rhs_exp))
    truth = bool(simplify(lhs_val - rhs_val) == 0)
    enonce = f"Vrai ou faux ? $" + statement + "$. Justifier."
    steps = [
        f"Étape 1 — On calcule le membre de gauche avec la propriété $e^p \\times e^q = e^{{p+q}}$ : "
        f"$e^{{{a}}} \\times e^{{{b}}} = e^{{{lhs_exp}}}$.",
        f"Étape 2 — On compare à l'exposant annoncé à droite ({rhs_exp}) : "
        + ("les deux exposants coïncident, l'affirmation est vraie." if truth
           else f"$e^{{{lhs_exp}}} \\neq e^{{{rhs_exp}}}$ car ${lhs_exp} \\neq {rhs_exp}$, l'affirmation est fausse."),
    ]
    return {
        "enonce": enonce,
        "answer": "Vrai." if truth else f"Faux (le bon résultat est $e^{{{lhs_exp}}}$).",
        "hint": "Calculer le membre de gauche avec les propriétés algébriques, puis comparer les deux exposants.",
        "steps": steps,
        "score": real_difficulty_score([lhs_val, rhs_val], extra=1.0),
    }


# ═══════════════════════════════════════════════════════════════════════
# Notion 2 — Nouvelle notation et nombre e : notation $e^x$, $e^0=1$,
# résolution d'équations $e^{u}=e^{v}$ (injectivité de exp).
# ═══════════════════════════════════════════════════════════════════════

def _gen_not_simplifier(rng: random.Random) -> Optional[dict]:
    a, b = _small(rng, -8, 8), _small(rng, -8, 8)
    while a == 0 or b == 0:
        a, b = _small(rng, -8, 8), _small(rng, -8, 8)
    op = rng.choice(["mult", "div"])
    if op == "mult":
        expr = exp(a) * exp(b)
        target = a + b
        statement = f"e^{{{a}}} \\times e^{{{b}}}"
    else:
        expr = exp(a) / exp(b)
        target = a - b
        statement = f"\\dfrac{{e^{{{a}}}}}{{e^{{{b}}}}}"
    result = simplify(expr)
    enonce = f"En utilisant la notation $e^x$, simplifier l'expression ${statement}$."
    steps = [
        f"Étape 1 — On écrit l'expression avec la notation $e^x$ : ${statement}$.",
        f"Étape 2 — On applique la règle des exposants correspondante pour obtenir $e^{{{target}}}$.",
    ]
    return {
        "enonce": enonce,
        "answer": f"$e^{{{target}}}$",
        "hint": "La notation $e^x$ suit les mêmes règles de calcul sur les exposants que les puissances usuelles.",
        "steps": steps,
        "score": real_difficulty_score([expr, result]),
    }


def _gen_not_equation_simple(rng: random.Random) -> Optional[dict]:
    a, b, c = _nz(rng, -6, 6), _small(rng, -8, 8), _small(rng, -12, 12)
    lhs = a * x + b
    eq = Eq(lhs, c)
    sol = solve(eq, x)
    if not sol:
        return None
    xs = sol[0]
    enonce = f"Résoudre dans $\\mathbb{{R}}$ l'équation $e^{{{latex(lhs)}}} = e^{{{c}}}$."
    steps = [
        "Étape 1 — La fonction exponentielle étant strictement croissante sur $\\mathbb{R}$, elle est "
        "injective : $e^u = e^v \\iff u = v$.",
        f"Étape 2 — On résout l'équation affine équivalente $ {latex(lhs)} = {c}$, ce qui donne $x = {latex(xs)}$.",
    ]
    return {
        "enonce": enonce,
        "answer": f"$\\mathcal{{S}} = \\{{{latex(xs)}\\}}$",
        "hint": "Deux exponentielles sont égales si et seulement si leurs exposants sont égaux.",
        "steps": steps,
        "score": real_difficulty_score([lhs, S(c)], extra=1.5),
    }


def _gen_not_equation_double(rng: random.Random) -> Optional[dict]:
    a, b = _nz(rng, -5, 5), _small(rng, -8, 8)
    c, d = _nz(rng, -5, 5), _small(rng, -8, 8)
    while a == c:  # sinon l'équation dégénère en une identité ou une contradiction
        c = _nz(rng, -5, 5)
    lhs, rhs = a * x + b, c * x + d
    sol = solve(Eq(lhs, rhs), x)
    if not sol:
        return None
    xs = sol[0]
    enonce = f"Résoudre dans $\\mathbb{{R}}$ l'équation $e^{{{latex(lhs)}}} = e^{{{latex(rhs)}}}$."
    steps = [
        "Étape 1 — Par injectivité de la fonction exponentielle sur $\\mathbb{R}$, l'équation équivaut à "
        f"${latex(lhs)} = {latex(rhs)}$.",
        f"Étape 2 — On isole $x$ : $x = {latex(xs)}$.",
    ]
    return {
        "enonce": enonce,
        "answer": f"$\\mathcal{{S}} = \\{{{latex(xs)}\\}}$",
        "hint": "Ramener l'équation exponentielle à une équation affine en identifiant les exposants.",
        "steps": steps,
        "score": real_difficulty_score([lhs, rhs], extra=2.0),
    }


def _gen_not_valeur_particuliere(rng: random.Random) -> Optional[dict]:
    kind = rng.choice(["e0", "e1_produit"])
    if kind == "e0":
        k = _nz(rng, 2, 9)
        expr = k * exp(0)
        result = simplify(expr)
        enonce = f"Sans calculatrice, donner la valeur exacte de $k \\times e^{{0}}$ pour $k = {k}$."
        steps = [
            "Étape 1 — On rappelle que $e^0 = 1$ (valeur particulière de la fonction exponentielle en 0).",
            f"Étape 2 — On en déduit $k \\times e^0 = {k} \\times 1 = {result}$.",
        ]
        answer = f"${result}$"
    else:
        p = _small(rng, -5, 5)
        while p == 0:
            p = _small(rng, -5, 5)
        expr = exp(p) * exp(-p)
        result = simplify(expr)
        enonce = f"Sans calculer $e^{{{p}}}$, donner la valeur exacte de $e^{{{p}}} \\times e^{{{-p}}}$."
        steps = [
            f"Étape 1 — On applique la propriété $e^p \\times e^{{-p}} = e^{{p-p}} = e^0$.",
            "Étape 2 — Or $e^0 = 1$, donc le produit vaut $1$.",
        ]
        answer = f"${result}$"
    return {
        "enonce": enonce,
        "answer": answer,
        "hint": "$e^0 = 1$ est la valeur de référence de la fonction exponentielle.",
        "steps": steps,
        "score": real_difficulty_score([expr, result]),
    }


def _gen_not_comparer(rng: random.Random) -> Optional[dict]:
    a, b = _small(rng, -9, 9), _small(rng, -9, 9)
    while a == b:
        b = _small(rng, -9, 9)
    symbole = "<" if a < b else ">"
    enonce = f"Comparer $e^{{{a}}}$ et $e^{{{b}}}$ sans calculer leurs valeurs."
    steps = [
        "Étape 1 — La fonction exponentielle est strictement croissante sur $\\mathbb{R}$.",
        f"Étape 2 — Comme ${a} {symbole} {b}$, on en déduit $e^{{{a}}} {symbole} e^{{{b}}}$.",
    ]
    return {
        "enonce": enonce,
        "answer": f"$e^{{{a}}} {symbole} e^{{{b}}}$",
        "hint": "Comparer directement les exposants : $u < v \\iff e^u < e^v$.",
        "steps": steps,
        "score": real_difficulty_score([S(a), S(b)], extra=1.0),
    }


def _gen_not_erreur(rng: random.Random) -> Optional[dict]:
    a, b = _nz(rng, -6, 6), _nz(rng, -6, 6)
    correct = simplify(exp(a) * exp(b))
    enonce = (
        f"Un élève écrit : « $e^{{{a}}} \\times e^{{{b}}} = e^{{{a}\\times{b}}}$ ». "
        "Corriger cette erreur en donnant le bon résultat."
    )
    steps = [
        "Étape 1 — La propriété correcte transforme un PRODUIT d'exponentielles en une exponentielle dont "
        "l'exposant est la SOMME des exposants, pas leur produit : $e^p \\times e^q = e^{p+q}$.",
        f"Étape 2 — On applique la bonne règle : $e^{{{a}}} \\times e^{{{b}}} = e^{{{a + b}}}$ (et non "
        f"$e^{{{a * b}}}$).",
    ]
    return {
        "enonce": enonce,
        "answer": f"$e^{{{a + b}}}$",
        "hint": "L'exposant d'un produit d'exponentielles est une somme, pas un produit d'exposants.",
        "steps": steps,
        "score": real_difficulty_score(correct, extra=1.5),
    }


# ═══════════════════════════════════════════════════════════════════════
# Notion 3 — Fonction exponentielle : définition ($\\exp' = \\exp$,
# $\\exp(0)=1$), dérivée de $k\\exp(x)$ et de $\\exp(u(x))$, signe.
# ═══════════════════════════════════════════════════════════════════════

def _gen_fn_derivee_simple(rng: random.Random) -> Optional[dict]:
    k = _nz(rng, -9, 9)
    expr = k * exp(x)
    deriv = diff(expr, x)
    enonce = f"Soit $f$ la fonction définie sur $\\mathbb{{R}}$ par $f(x) = {latex(expr)}$. Calculer $f'(x)$."
    steps = [
        "Étape 1 — On utilise la propriété fondamentale de la fonction exponentielle : elle est égale à sa "
        "propre dérivée, $\\left(e^x\\right)' = e^x$.",
        f"Étape 2 — Comme $f = {k} \\times \\exp$, on dérive terme constant fois fonction : "
        f"$f'(x) = {latex(deriv)}$.",
    ]
    return {
        "enonce": enonce,
        "answer": f"$f'(x) = {latex(deriv)}$",
        "hint": "La dérivée de $k\\,e^x$ est $k\\,e^x$ : la fonction exponentielle est sa propre dérivée.",
        "steps": steps,
        "score": real_difficulty_score([expr, deriv]),
    }


def _gen_fn_derivee_composee(rng: random.Random) -> Optional[dict]:
    a, b = _nz(rng, -4, 4), _small(rng, -6, 6)
    u = a * x + b
    expr = exp(u)
    deriv_raw = diff(expr, x)
    deriv = simplify(deriv_raw)
    enonce = f"Soit $f$ la fonction définie sur $\\mathbb{{R}}$ par $f(x) = e^{{{latex(u)}}}$. Calculer $f'(x)$."
    steps = [
        f"Étape 1 — On identifie une composée $e^{{u(x)}}$ avec $u(x) = {latex(u)}$, donc $u'(x) = {a}$.",
        "Étape 2 — On applique la règle de dérivation $\\left(e^{u}\\right)' = u' \\, e^{u}$ : "
        f"$f'(x) = {latex(deriv_raw)}$.",
    ]
    return {
        "enonce": enonce,
        "answer": f"$f'(x) = {latex(deriv)}$",
        "hint": "$\\left(e^{u}\\right)' = u'\\,e^{u}$ : ne pas oublier de multiplier par la dérivée de l'exposant.",
        "steps": steps,
        "score": real_difficulty_score([expr, deriv], extra=2.0),
    }


def _gen_fn_derivee_polynome_expo(rng: random.Random) -> Optional[dict]:
    a, b = _nz(rng, -3, 3), _small(rng, -5, 5)
    u = a * x**2 + b * x
    expr = exp(u)
    deriv_raw = diff(expr, x)
    deriv = simplify(deriv_raw)
    enonce = f"Soit $f$ la fonction définie sur $\\mathbb{{R}}$ par $f(x) = e^{{{latex(u)}}}$. Calculer $f'(x)$."
    steps = [
        f"Étape 1 — On pose $u(x) = {latex(u)}$, donc $u'(x) = {latex(diff(u, x))}$.",
        f"Étape 2 — On applique $\\left(e^u\\right)' = u'\\,e^u$ : $f'(x) = {latex(deriv_raw)}$.",
    ]
    return {
        "enonce": enonce,
        "answer": f"$f'(x) = {latex(deriv)}$",
        "hint": "L'exposant est un polynôme du second degré : on dérive d'abord $u$, puis on applique la règle de composition.",
        "steps": steps,
        "score": real_difficulty_score([expr, deriv], extra=2.0),
    }


def _gen_fn_valeur_en_0(rng: random.Random) -> Optional[dict]:
    k, c = _nz(rng, -8, 8), _small(rng, -9, 9)
    expr = k * exp(x) + c
    value_at_0 = expr.subs(x, 0)
    enonce = f"Soit $f$ la fonction définie sur $\\mathbb{{R}}$ par $f(x) = {latex(expr)}$. Calculer $f(0)$."
    steps = [
        "Étape 1 — On rappelle la valeur particulière $e^0 = 1$.",
        f"Étape 2 — On substitue $x=0$ : $f(0) = {k} \\times 1 + ({c}) = {value_at_0}$.",
    ]
    return {
        "enonce": enonce,
        "answer": f"$f(0) = {value_at_0}$",
        "hint": "$\\exp(0) = 1$ est la valeur de référence à connaître par cœur.",
        "steps": steps,
        "score": real_difficulty_score([expr, S(value_at_0)]),
    }


def _gen_fn_signe(rng: random.Random) -> Optional[dict]:
    k = _nz(rng, -6, 6)
    expr = k * exp(x)
    signe = "strictement positive" if k > 0 else "strictement négative"
    symbole = ">" if k > 0 else "<"
    enonce = (
        f"Soit $f$ la fonction définie sur $\\mathbb{{R}}$ par $f(x) = {latex(expr)}$. "
        "Justifier le signe de $f(x)$ pour tout réel $x$."
    )
    steps = [
        "Étape 1 — On rappelle que $e^x > 0$ pour tout réel $x$ (la fonction exponentielle ne s'annule jamais "
        "et reste strictement positive).",
        f"Étape 2 — Comme le coefficient {k} est {'positif' if k>0 else 'négatif'}, $f(x) = {k}\\,e^x$ est "
        f"{signe} sur $\\mathbb{{R}}$ : $f(x) {symbole} 0$.",
    ]
    return {
        "enonce": enonce,
        "answer": f"$f(x) {symbole} 0$ pour tout réel $x$ (fonction {signe}).",
        "hint": "$e^x$ est toujours strictement positif ; le signe de $k\\,e^x$ est donc celui de $k$.",
        "steps": steps,
        "score": real_difficulty_score(expr, extra=1.0),
    }


def _gen_fn_equation_differentielle(rng: random.Random) -> Optional[dict]:
    k = _nz(rng, 2, 7)
    expr = k * exp(x)
    deriv = diff(expr, x)
    is_equal = bool(simplify(expr - deriv) == 0)
    enonce = (
        f"Vérifier que la fonction $f(x) = {latex(expr)}$ vérifie l'équation différentielle $f' = f$."
    )
    steps = [
        f"Étape 1 — On calcule $f'(x)$ : $f'(x) = {latex(deriv)}$ (la dérivée de $e^x$ est $e^x$).",
        f"Étape 2 — On compare à $f(x) = {latex(expr)}$ : " + (
            "les deux expressions sont identiques, donc $f' = f$." if is_equal
            else "les deux expressions diffèrent."
        ),
    ]
    return {
        "enonce": enonce,
        "answer": "Oui, $f' = f$." if is_equal else "Non, $f' \\neq f$.",
        "hint": "La fonction $x \\mapsto k\\,e^x$ est, à une constante multiplicative près, la seule fonction égale à sa propre dérivée.",
        "steps": steps,
        "score": real_difficulty_score([expr, deriv], extra=1.0),
    }


# ═══════════════════════════════════════════════════════════════════════
# Notion 4 — Courbe représentative : positivité, point $(0;1)$, tangente,
# monotonie, position par rapport à une droite horizontale.
# ═══════════════════════════════════════════════════════════════════════

def _gen_courbe_appartenance(rng: random.Random) -> Optional[dict]:
    a = _small(rng, -6, 6)
    y_correct = exp(a)
    is_true = rng.choice([True, False])
    if is_true:
        proposed_exp = a
        y_proposed_latex = f"e^{{{a}}}"
        truth = True
    else:
        delta = _nz(rng, 1, 3)
        proposed_exp = a + delta
        y_proposed_latex = f"e^{{{proposed_exp}}}"
        truth = False
    enonce = (
        f"La courbe représentative de la fonction exponentielle passe-t-elle par le point de coordonnées "
        f"$({a} ; {y_proposed_latex})$ ? Justifier."
    )
    steps = [
        f"Étape 1 — Un point $(a ; y)$ appartient à la courbe de $\\exp$ si et seulement si $y = e^{{a}}$, ici "
        f"$a = {a}$, donc il faut $y = e^{{{a}}}$.",
        "Étape 2 — On compare à l'ordonnée proposée : " + (
            f"$e^{{{a}}} = e^{{{a}}}$, le point appartient bien à la courbe." if truth
            else f"l'ordonnée proposée est $e^{{{proposed_exp}}}$, qui diffère de $e^{{{a}}}$ car "
                 f"${proposed_exp} \\neq {a}$, donc le point n'appartient pas à la courbe."
        ),
    ]
    return {
        "enonce": enonce,
        "answer": "Oui, ce point appartient à la courbe représentative de la fonction exponentielle." if truth
                  else f"Non, ce point n'appartient pas à la courbe (il faudrait $y = e^{{{a}}}$).",
        "hint": "Un point appartient à la courbe de $\\exp$ si et seulement si son ordonnée vaut $e$ élevé à son abscisse.",
        "steps": steps,
        "score": real_difficulty_score(y_correct, extra=1.0),
    }


def _gen_courbe_signe_positif(rng: random.Random) -> Optional[dict]:
    a = _small(rng, -9, 9)
    enonce = (
        f"Justifier que le point de la courbe représentative de la fonction exponentielle d'abscisse $x={a}$ "
        "est situé strictement au-dessus de l'axe des abscisses."
    )
    steps = [
        "Étape 1 — On rappelle la propriété analytique fondamentale : $e^x > 0$ pour tout réel $x$.",
        f"Étape 2 — En particulier pour $x = {a}$, l'ordonnée $e^{{{a}}}$ est strictement positive : le point "
        "est bien au-dessus de l'axe des abscisses.",
    ]
    return {
        "enonce": enonce,
        "answer": f"$e^{{{a}}} > 0$, donc le point est strictement au-dessus de l'axe des abscisses.",
        "hint": "La courbe de la fonction exponentielle ne touche jamais l'axe des abscisses : elle reste toujours strictement au-dessus.",
        "steps": steps,
        "score": real_difficulty_score(exp(a), extra=1.0),
    }


def _gen_courbe_comparaison(rng: random.Random) -> Optional[dict]:
    a, b = _small(rng, -8, 8), _small(rng, -8, 8)
    while a == b:
        b = _small(rng, -8, 8)
    symbole = "<" if a < b else ">"
    enonce = (
        f"Sans calculer $e^{{{a}}}$ ni $e^{{{b}}}$, comparer les points de la courbe représentative de la "
        f"fonction exponentielle d'abscisses $x={a}$ et $x={b}$."
    )
    steps = [
        "Étape 1 — La fonction exponentielle est strictement croissante sur $\\mathbb{R}$ : la courbe monte "
        "de gauche à droite.",
        f"Étape 2 — Comme ${a} {symbole} {b}$, l'ordonnée du point d'abscisse ${a}$ est {'inférieure' if symbole=='<' else 'supérieure'} "
        f"à celle du point d'abscisse ${b}$ : $e^{{{a}}} {symbole} e^{{{b}}}$.",
    ]
    return {
        "enonce": enonce,
        "answer": f"$e^{{{a}}} {symbole} e^{{{b}}}$",
        "hint": "La croissance stricte de la fonction exponentielle permet de comparer deux ordonnées sans les calculer.",
        "steps": steps,
        "score": real_difficulty_score([S(a), S(b)], extra=1.0),
    }


def _gen_courbe_tangente(rng: random.Random) -> Optional[dict]:
    a = _small(rng, -3, 3)
    f = exp(x)
    fp = diff(f, x)
    tangent = sympy.expand(f.subs(x, a) + fp.subs(x, a) * (x - a))
    enonce = (
        f"Déterminer une équation de la tangente à la courbe représentative de la fonction exponentielle "
        f"au point d'abscisse $x = {a}$."
    )
    steps = [
        f"Étape 1 — On calcule $f({a}) = e^{{{a}}}$ et $f'({a}) = e^{{{a}}}$ (la dérivée de $\\exp$ est "
        "$\\exp$ elle-même).",
        f"Étape 2 — L'équation de la tangente au point d'abscisse $a$ est $y = f(a) + f'(a)(x-a)$, soit ici "
        f"$y = {latex(tangent)}$.",
    ]
    return {
        "enonce": enonce,
        "answer": f"$y = {latex(tangent)}$",
        "hint": "L'équation de la tangente en $a$ est $y = f(a) + f'(a)(x-a)$, avec $f(a)=f'(a)=e^a$ pour l'exponentielle.",
        "steps": steps,
        "score": real_difficulty_score(tangent, extra=2.0),
    }


def _gen_courbe_position_asymptote(rng: random.Random) -> Optional[dict]:
    a = _small(rng, -9, -1)
    enonce = (
        "Justifier que la courbe représentative de la fonction exponentielle se rapproche de l'axe des "
        f"abscisses (droite d'équation $y=0$) lorsque $x$ tend vers $-\\infty$, en observant la valeur en "
        f"$x = {a}$."
    )
    value = exp(a)
    steps = [
        "Étape 1 — On rappelle que $\\lim\\limits_{x \\to -\\infty} e^x = 0$ : l'axe des abscisses est "
        "asymptote horizontale à la courbe en $-\\infty$.",
        f"Étape 2 — Par exemple, pour $x = {a}$ (négatif), $e^{{{a}}}$ est déjà une valeur très proche de $0$, "
        "ce qui illustre ce comportement.",
    ]
    return {
        "enonce": enonce,
        "answer": "L'axe des abscisses ($y=0$) est asymptote horizontale à la courbe en $-\\infty$.",
        "hint": "$\\lim\\limits_{x\\to-\\infty} e^x = 0$ : la courbe s'approche indéfiniment de l'axe des abscisses sans jamais le toucher.",
        "steps": steps,
        "score": real_difficulty_score(value, extra=1.5),
    }


# ═══════════════════════════════════════════════════════════════════════
# Notion 5 — Propriétés analytiques : limites en $\\pm\\infty$, variations,
# signe, résolution d'inéquations $e^u < e^v$.
# ═══════════════════════════════════════════════════════════════════════

def _gen_ana_limite_infini(rng: random.Random) -> Optional[dict]:
    sens = rng.choice(["plus", "moins"])
    if sens == "plus":
        lim_val = limit(exp(x), x, oo)
        enonce = "Donner $\\lim\\limits_{x \\to +\\infty} e^x$ et justifier à l'aide des propriétés analytiques de l'exponentielle."
        justification = "La fonction exponentielle est strictement croissante et non majorée sur $\\mathbb{R}$."
        answer_latex = "+\\infty"
    else:
        lim_val = limit(exp(x), x, -oo)
        enonce = "Donner $\\lim\\limits_{x \\to -\\infty} e^x$ et justifier à l'aide des propriétés analytiques de l'exponentielle."
        justification = "La fonction exponentielle est strictement positive et tend vers $0$ sans jamais s'annuler."
        answer_latex = "0"
    steps = [
        f"Étape 1 — {justification}",
        f"Étape 2 — On en déduit $\\lim\\limits_{{x \\to {'+' if sens=='plus' else '-'}\\infty}} e^x = {_latex_inf(lim_val)}$.",
    ]
    return {
        "enonce": enonce,
        "answer": f"$\\lim\\limits_{{x \\to {'+' if sens=='plus' else '-'}\\infty}} e^x = {answer_latex}$",
        "hint": "Retenir les deux limites de référence : $e^x \\to +\\infty$ en $+\\infty$ et $e^x \\to 0$ en $-\\infty$.",
        "steps": steps,
        "score": real_difficulty_score(S(0), extra=1.5),
    }


def _gen_ana_limite_composee(rng: random.Random) -> Optional[dict]:
    a = _nz(rng, -5, 5)
    u = a * x
    lim_val = limit(exp(u), x, oo)
    sens_desc = "diminue vers $-\\infty$" if a > 0 else "augmente vers $+\\infty$"
    enonce = f"Déterminer $\\lim\\limits_{{x \\to +\\infty}} e^{{{latex(u)}}}$."
    steps = [
        f"Étape 1 — On étudie le comportement de l'exposant $u(x) = {latex(u)}$ quand $x \\to +\\infty$ : "
        f"comme le coefficient {a} est {'positif' if a>0 else 'négatif'}, $u(x)$ tend vers "
        f"{'$+\\infty$' if a>0 else '$-\\infty$'}.",
        f"Étape 2 — Par composition avec les limites de référence de l'exponentielle, "
        f"$\\lim\\limits_{{x\\to+\\infty}} e^{{{latex(u)}}} = {_latex_inf(lim_val)}$.",
    ]
    return {
        "enonce": enonce,
        "answer": f"$\\lim\\limits_{{x \\to +\\infty}} e^{{{latex(u)}}} = {_latex_inf(lim_val)}$",
        "hint": "Étudier d'abord la limite de l'exposant, puis composer avec les limites de référence de $\\exp$.",
        "steps": steps,
        "score": real_difficulty_score(u, extra=2.0),
    }


def _gen_ana_variation(rng: random.Random) -> Optional[dict]:
    k = _nz(rng, -6, 6)
    expr = k * exp(x)
    deriv = diff(expr, x)
    sens = "croissante" if k > 0 else "décroissante"
    enonce = (
        f"Étudier les variations de la fonction $f$ définie sur $\\mathbb{{R}}$ par $f(x) = {latex(expr)}$."
    )
    steps = [
        f"Étape 1 — On calcule $f'(x) = {latex(deriv)}$.",
        f"Étape 2 — Comme $e^x > 0$ pour tout $x$ et que {k} est {'positif' if k>0 else 'négatif'}, $f'(x)$ est "
        f"du signe de {k}, donc $f$ est strictement {sens} sur $\\mathbb{{R}}$.",
    ]
    return {
        "enonce": enonce,
        "answer": f"$f$ est strictement {sens} sur $\\mathbb{{R}}$.",
        "hint": "Le signe de $f'(x) = k\\,e^x$ est celui de $k$, car $e^x$ est toujours strictement positif.",
        "steps": steps,
        "score": real_difficulty_score([expr, deriv], extra=1.0),
    }


def _gen_ana_inequation(rng: random.Random) -> Optional[dict]:
    a, b = _nz(rng, -5, 5), _small(rng, -8, 8)
    c = _small(rng, -10, 10)
    lhs = a * x + b
    rel = solve(lhs < c, x)
    if not isinstance(rel, (And,)) and not hasattr(rel, "lhs"):
        return None
    try:
        interval = _fmt_interval_from_and(rel)
    except Exception:
        return None
    enonce = f"Résoudre dans $\\mathbb{{R}}$ l'inéquation $e^{{{latex(lhs)}}} < e^{{{c}}}$."
    steps = [
        "Étape 1 — La fonction exponentielle étant strictement croissante sur $\\mathbb{R}$, l'inégalité "
        f"$e^u < e^v$ équivaut à $u < v$ : ici $ {latex(lhs)} < {c}$.",
        f"Étape 2 — On résout cette inéquation affine, ce qui donne $\\mathcal{{S}} = {interval}$.",
    ]
    return {
        "enonce": enonce,
        "answer": f"$\\mathcal{{S}} = {interval}$",
        "hint": "La croissance stricte de l'exponentielle permet de remplacer $e^u < e^v$ par $u < v$.",
        "steps": steps,
        "score": real_difficulty_score([lhs, S(c)], extra=2.0),
    }


def _gen_ana_signe_expression(rng: random.Random) -> Optional[dict]:
    c = _nz(rng, -8, 8)
    # e^x - e^c s'annule en x=c et change de signe : positif ssi x>c
    enonce = (
        f"Déterminer le signe de $g(x) = e^x - e^{{{c}}}$ selon les valeurs de $x$."
    )
    steps = [
        f"Étape 1 — $g(x) = 0 \\iff e^x = e^{{{c}}} \\iff x = {c}$ par injectivité de l'exponentielle.",
        f"Étape 2 — La fonction exponentielle étant strictement croissante, $e^x > e^{{{c}}}$ pour $x > {c}$ "
        f"et $e^x < e^{{{c}}}$ pour $x < {c}$ : $g(x)$ est du signe de $(x-{c})$.",
    ]
    return {
        "enonce": enonce,
        "answer": f"$g(x) < 0$ sur $]-\\infty ; {c}[$, $g({c})=0$, et $g(x) > 0$ sur $]{c} ; +\\infty[$.",
        "hint": "Étudier le signe d'une différence d'exponentielles revient à comparer directement les exposants.",
        "steps": steps,
        "score": real_difficulty_score(exp(x) - exp(c), extra=2.0),
    }


# ═══════════════════════════════════════════════════════════════════════
# Notion 6 — Lien avec les suites géométriques : $u_n = A\\,e^{rn}$ est
# géométrique de raison $e^r$ ; contextes de croissance/décroissance
# continue (population, désintégration, capitalisation).
# ═══════════════════════════════════════════════════════════════════════

def _gen_suite_identifier(rng: random.Random) -> Optional[dict]:
    A = _nz(rng, 1, 9)
    r = _nz(rng, -3, 3)
    k = rng.randint(2, 6)
    u_n = A * exp(r * n)
    ratio = simplify(u_n.subs(n, n + 1) / u_n)
    u_k = simplify(u_n.subs(n, k))
    enonce = (
        f"On considère la suite $(u_n)$ définie pour tout entier naturel $n$ par $u_n = {A} \\times e^{{{r}n}}$. "
        f"Montrer que $(u_n)$ est géométrique et préciser sa raison, puis calculer $u_{{{k}}}$ en fonction de "
        f"$e^{{{r}}}$."
    )
    steps = [
        f"Étape 1 — On calcule le rapport $\\dfrac{{u_{{n+1}}}}{{u_n}} = \\dfrac{{{A}\\,e^{{{r}(n+1)}}}}{{{A}\\,e^{{{r}n}}}} = e^{{{r}}}$, "
        "constant : la suite est donc géométrique de raison $q = e^{" + str(r) + "}$.",
        f"Étape 2 — On en déduit $u_{{{k}}} = {A} \\times e^{{{r*k}}}$.",
    ]
    return {
        "enonce": enonce,
        "answer": f"$(u_n)$ est géométrique de raison $e^{{{r}}}$ et $u_{{{k}}} = {A} \\times e^{{{r*k}}}$",
        "hint": "Une suite $u_n = A\\,e^{rn}$ est géométrique de raison $e^r$, obtenue en factorisant $u_{n+1}$ par $u_n$.",
        "steps": steps,
        "score": real_difficulty_score([ratio, u_k], extra=1.5),
    }


def _gen_suite_contexte_population(rng: random.Random) -> Optional[dict]:
    N0 = rng.choice([500, 800, 1000, 1200, 2000, 5000])
    r = _nz(rng, 1, 4) * Rational(1, 20)  # taux de croissance continue plausible (5%, 10%...)
    k = rng.randint(2, 6)
    N_t = N0 * exp(r * t) if (t := symbols("t")) is not None else None
    N_k = simplify(N_t.subs(t, k))
    taux_pct = int(r * 100)
    enonce = (
        f"Une population de bactéries évolue selon $N(t) = {N0} \\times e^{{{latex(r)}t}}$, où $t$ est le temps "
        f"en heures et $N(t)$ le nombre de bactéries. Cette évolution correspond à un taux de croissance "
        f"continu de {taux_pct}\\,\\% par heure. Montrer que la suite $(N(k))_{{k \\in \\mathbb{{N}}}}$ des "
        f"effectifs aux instants entiers est géométrique, puis calculer $N({k})$ en fonction de "
        f"$e^{{{latex(r)}}}$."
    )
    steps = [
        f"Étape 1 — Pour $k$ entier, $N(k) = {N0}\\,e^{{{latex(r)}k}}$ : le rapport $\\dfrac{{N(k+1)}}{{N(k)}} = "
        f"e^{{{latex(r)}}}$ est constant, donc $(N(k))$ est géométrique de raison $e^{{{latex(r)}}}$.",
        f"Étape 2 — On calcule $N({k}) = {N0} \\times e^{{{latex(r*k)}}}$.",
    ]
    return {
        "enonce": enonce,
        "answer": f"$(N(k))$ est géométrique de raison $e^{{{latex(r)}}}$ et $N({k}) = {N0} \\times e^{{{latex(r*k)}}}$",
        "hint": "Une croissance continue à taux constant se modélise par $N(t) = N_0\\,e^{rt}$, géométrique aux instants entiers.",
        "steps": steps,
        "score": real_difficulty_score(N_k, extra=2.5),
    }


def _gen_suite_contexte_radioactif(rng: random.Random) -> Optional[dict]:
    N0 = rng.choice([100, 250, 400, 600, 1000])
    lam = _nz(rng, 1, 4) * Rational(1, 20)
    k = rng.randint(2, 6)
    tt = symbols("t")
    N_t = N0 * exp(-lam * tt)
    N_k = simplify(N_t.subs(tt, k))
    enonce = (
        f"La masse d'une substance radioactive suit la loi $N(t) = {N0} \\times e^{{-{latex(lam)}t}}$, où $t$ "
        f"est le temps en années. Montrer que la suite des masses aux instants entiers $(N(k))_{{k\\in\\mathbb{{N}}}}$ "
        f"est géométrique, préciser si elle est croissante ou décroissante, puis calculer $N({k})$."
    )
    steps = [
        f"Étape 1 — $\\dfrac{{N(k+1)}}{{N(k)}} = e^{{-{latex(lam)}}}$, constant : la suite est géométrique de "
        f"raison $e^{{-{latex(lam)}}}$.",
        f"Étape 2 — Comme l'exposant $-{latex(lam)}$ est négatif, $0 < e^{{-{latex(lam)}}} < 1$ : la suite est "
        f"décroissante (désintégration). On calcule $N({k}) = {N0} \\times e^{{-{latex(lam*k)}}}$.",
    ]
    return {
        "enonce": enonce,
        "answer": f"$(N(k))$ est géométrique de raison $e^{{-{latex(lam)}}}$ (décroissante) et "
                  f"$N({k}) = {N0} \\times e^{{-{latex(lam*k)}}}$",
        "hint": "Un exposant négatif donne une raison $e^{-\\lambda}$ comprise entre $0$ et $1$ : la suite décroît.",
        "steps": steps,
        "score": real_difficulty_score(N_k, extra=2.5),
    }


def _gen_suite_contexte_capitalisation(rng: random.Random) -> Optional[dict]:
    C0 = rng.choice([1000, 2000, 5000, 10000])
    r = _nz(rng, 1, 5) * Rational(1, 100)
    k = rng.randint(2, 8)
    tt = symbols("t")
    C_t = C0 * exp(r * tt)
    C_k = simplify(C_t.subs(tt, k))
    taux_pct = float(r * 100)
    enonce = (
        f"Un capital est placé à intérêts composés en continu selon $C(t) = {C0} \\times e^{{{latex(r)}t}}$, "
        f"où $t$ est le temps en années et $C(t)$ le capital en euros (taux annuel continu {taux_pct:g}\\,\\%). "
        f"Montrer que la suite $(C(k))_{{k\\in\\mathbb{{N}}}}$ est géométrique et calculer $C({k})$ en fonction "
        f"de $e^{{{latex(r)}}}$."
    )
    steps = [
        f"Étape 1 — $\\dfrac{{C(k+1)}}{{C(k)}} = e^{{{latex(r)}}}$, constant : $(C(k))$ est géométrique de "
        f"raison $e^{{{latex(r)}}} > 1$, donc croissante (capitalisation).",
        f"Étape 2 — $C({k}) = {C0} \\times e^{{{latex(r*k)}}}$.",
    ]
    return {
        "enonce": enonce,
        "answer": f"$(C(k))$ est géométrique de raison $e^{{{latex(r)}}}$ et $C({k}) = {C0} \\times e^{{{latex(r*k)}}}$",
        "hint": "La capitalisation continue à taux constant se modélise par $C(t) = C_0\\,e^{rt}$, géométrique aux instants entiers.",
        "steps": steps,
        "score": real_difficulty_score(C_k, extra=2.5),
    }


def _gen_suite_sens_variation(rng: random.Random) -> Optional[dict]:
    r = _nz(rng, -5, 5) * Rational(1, 10)
    A = _nz(rng, 1, 9)
    q = simplify(exp(r))
    sens = "croissante" if r > 0 else "décroissante"
    comparaison = ">" if r > 0 else "<"
    enonce = (
        f"On considère la suite géométrique $u_n = {A} \\times e^{{{latex(r)}n}}$. Sans calculer sa valeur "
        f"numérique, déterminer si la raison $q = e^{{{latex(r)}}}$ est supérieure ou inférieure à $1$, et en "
        "déduire le sens de variation de la suite."
    )
    steps = [
        f"Étape 1 — La fonction exponentielle est strictement croissante et $e^0=1$ ; comme l'exposant "
        f"${latex(r)}$ est {'positif' if r>0 else 'négatif'}, on a $e^{{{latex(r)}}} {comparaison} 1$.",
        f"Étape 2 — Une suite géométrique à termes positifs de raison $q {comparaison} 1$ est {sens} : "
        f"$(u_n)$ est donc {sens}.",
    ]
    return {
        "enonce": enonce,
        "answer": f"$q = e^{{{latex(r)}}} {comparaison} 1$, donc $(u_n)$ est {sens}.",
        "hint": "Comparer l'exposant $r$ à $0$ suffit à savoir si $e^r$ est supérieur ou inférieur à $1$, sans calcul numérique.",
        "steps": steps,
        "score": real_difficulty_score(q, extra=2.0),
    }


@dataclass(frozen=True)
class Family:
    id: str
    level: int  # 1 (facile) .. 5 (défi) — étiquette de départ, revalidée par real_difficulty_score
    label: str
    notion: str
    generate: Callable[[random.Random], Optional[dict]]
    structure_hint: str
    rule_hint: str


FAMILIES: tuple[Family, ...] = (
    # ── Propriétés algébriques ──────────────────────────────────────────
    Family("alg_produit", 1, "Produit de deux exponentielles", NOTION_PROPRIETES_ALGEBRIQUES,
           _gen_alg_produit, "un produit de deux exponentielles à exposants numériques",
           "$e^p \\times e^q = e^{p+q}$"),
    Family("alg_quotient", 1, "Quotient de deux exponentielles", NOTION_PROPRIETES_ALGEBRIQUES,
           _gen_alg_quotient, "un quotient de deux exponentielles à exposants numériques",
           "$e^p / e^q = e^{p-q}$"),
    Family("alg_puissance", 2, "Puissance d'une exponentielle", NOTION_PROPRIETES_ALGEBRIQUES,
           _gen_alg_puissance, "une puissance entière d'une exponentielle",
           "$(e^p)^k = e^{kp}$"),
    Family("alg_inverse", 1, "Inverse d'une exponentielle", NOTION_PROPRIETES_ALGEBRIQUES,
           _gen_alg_inverse, "l'inverse d'une exponentielle", "$1/e^p = e^{-p}$"),
    Family("alg_valeur_connue", 3, "Choix de méthode sans valeur numérique", NOTION_PROPRIETES_ALGEBRIQUES,
           _gen_alg_valeur_connue, "une expression à exprimer en fonction de $A=e^a$ et $B=e^b$ non calculés",
           "reconnaître quelle propriété algébrique relie l'exposant demandé aux exposants connus"),
    Family("alg_erreur", 2, "Erreur classique à corriger", NOTION_PROPRIETES_ALGEBRIQUES,
           _gen_alg_erreur_a_corriger, "une confusion entre $e^{p+q}=e^pe^q$ et une addition d'exponentielles",
           "identifier et corriger l'erreur de propriété algébrique"),
    Family("alg_vrai_faux", 2, "Vrai/Faux justifié", NOTION_PROPRIETES_ALGEBRIQUES,
           _gen_alg_vrai_faux, "une égalité impliquant des exponentielles à valider ou réfuter",
           "calculer un membre avec les propriétés algébriques puis comparer les exposants"),

    # ── Nouvelle notation et nombre e ───────────────────────────────────
    Family("not_simplifier", 1, "Simplification avec la notation $e^x$", NOTION_NOTATION_E,
           _gen_not_simplifier, "une expression à simplifier avec la notation $e^x$",
           "les règles usuelles des exposants s'appliquent à $e^x$"),
    Family("not_equation_simple", 2, "Équation $e^{u}=e^{c}$", NOTION_NOTATION_E,
           _gen_not_equation_simple, "une équation avec un exposant affine égal à une constante",
           "injectivité de $\\exp$ : $e^u=e^v \\iff u=v$"),
    Family("not_equation_double", 3, "Équation $e^{u}=e^{v}$ à deux membres affines", NOTION_NOTATION_E,
           _gen_not_equation_double, "une équation avec deux exposants affines distincts",
           "injectivité de $\\exp$ : $e^u=e^v \\iff u=v$"),
    Family("not_valeur_particuliere", 1, "Valeur particulière $e^0=1$", NOTION_NOTATION_E,
           _gen_not_valeur_particuliere, "une expression utilisant la valeur $e^0=1$",
           "$e^0 = 1$"),
    Family("not_comparer", 2, "Comparaison sans calcul", NOTION_NOTATION_E,
           _gen_not_comparer, "deux exponentielles à comparer sans les calculer",
           "croissance stricte de $\\exp$ : $u<v \\iff e^u<e^v$"),
    Family("not_erreur", 2, "Erreur classique à corriger", NOTION_NOTATION_E,
           _gen_not_erreur, "une confusion entre $e^{p+q}$ et $e^{p\\times q}$",
           "identifier et corriger l'erreur de propriété"),

    # ── Fonction exponentielle ──────────────────────────────────────────
    Family("fn_derivee_simple", 1, "Dérivée de $k\\,e^x$", NOTION_FONCTION_EXPONENTIELLE,
           _gen_fn_derivee_simple, "une fonction $k$ fois l'exponentielle", "$(e^x)' = e^x$"),
    Family("fn_derivee_composee", 3, "Dérivée de $e^{u(x)}$ affine", NOTION_FONCTION_EXPONENTIELLE,
           _gen_fn_derivee_composee, "une composée exponentielle d'exposant affine",
           "$(e^u)' = u'\\,e^u$"),
    Family("fn_derivee_polynome_expo", 4, "Dérivée de $e^{u(x)}$ quadratique", NOTION_FONCTION_EXPONENTIELLE,
           _gen_fn_derivee_polynome_expo, "une composée exponentielle d'exposant du second degré",
           "$(e^u)' = u'\\,e^u$"),
    Family("fn_valeur_en_0", 1, "Valeur en $0$", NOTION_FONCTION_EXPONENTIELLE,
           _gen_fn_valeur_en_0, "une fonction affine en $\\exp(x)$ évaluée en $0$", "$\\exp(0) = 1$"),
    Family("fn_signe", 2, "Signe de $k\\,e^x$", NOTION_FONCTION_EXPONENTIELLE,
           _gen_fn_signe, "le signe d'une fonction proportionnelle à l'exponentielle",
           "$e^x > 0$ pour tout $x$"),
    Family("fn_equation_differentielle", 2, "Équation différentielle $f'=f$", NOTION_FONCTION_EXPONENTIELLE,
           _gen_fn_equation_differentielle, "une vérification de l'équation $f'=f$",
           "la fonction exponentielle est sa propre dérivée"),

    # ── Courbe représentative ───────────────────────────────────────────
    Family("courbe_appartenance", 1, "Appartenance à la courbe", NOTION_COURBE,
           _gen_courbe_appartenance, "un point dont il faut vérifier l'appartenance à la courbe de $\\exp$",
           "un point $(a;y)$ appartient à la courbe ssi $y=e^a$"),
    Family("courbe_signe_positif", 1, "Positivité de la courbe", NOTION_COURBE,
           _gen_courbe_signe_positif, "un point de la courbe dont il faut justifier la position",
           "$e^x > 0$ pour tout $x$"),
    Family("courbe_comparaison", 2, "Comparaison de deux points de la courbe", NOTION_COURBE,
           _gen_courbe_comparaison, "deux points de la courbe à comparer sans calcul",
           "croissance stricte de la courbe"),
    Family("courbe_tangente", 4, "Tangente à la courbe", NOTION_COURBE,
           _gen_courbe_tangente, "la tangente à la courbe en un point donné",
           "$y = f(a) + f'(a)(x-a)$ avec $f=f'=\\exp$"),
    Family("courbe_position_asymptote", 3, "Asymptote horizontale", NOTION_COURBE,
           _gen_courbe_position_asymptote, "le comportement de la courbe en $-\\infty$",
           "$\\lim_{x\\to-\\infty} e^x = 0$"),

    # ── Propriétés analytiques ──────────────────────────────────────────
    Family("ana_limite_infini", 1, "Limites de référence", NOTION_PROPRIETES_ANALYTIQUES,
           _gen_ana_limite_infini, "une limite de référence de la fonction exponentielle",
           "$e^x \\to +\\infty$ en $+\\infty$, $e^x \\to 0$ en $-\\infty$"),
    Family("ana_limite_composee", 3, "Limite d'une exponentielle composée", NOTION_PROPRIETES_ANALYTIQUES,
           _gen_ana_limite_composee, "une limite d'exponentielle à exposant affine",
           "composition des limites de référence"),
    Family("ana_variation", 2, "Variations de $k\\,e^x$", NOTION_PROPRIETES_ANALYTIQUES,
           _gen_ana_variation, "l'étude des variations d'une fonction proportionnelle à $\\exp$",
           "signe de $f'(x)=k\\,e^x$"),
    Family("ana_inequation", 3, "Inéquation $e^u < e^c$", NOTION_PROPRIETES_ANALYTIQUES,
           _gen_ana_inequation, "une inéquation exponentielle à exposant affine",
           "croissance stricte : $e^u<e^v \\iff u<v$"),
    Family("ana_signe_expression", 3, "Signe d'une différence d'exponentielles", NOTION_PROPRIETES_ANALYTIQUES,
           _gen_ana_signe_expression, "le signe de $e^x - e^c$ selon $x$",
           "comparaison des exposants via la croissance stricte"),

    # ── Lien avec les suites géométriques ───────────────────────────────
    Family("suite_identifier", 2, "Identifier une suite géométrique", NOTION_SUITES_GEOMETRIQUES,
           _gen_suite_identifier, "une suite $u_n=A e^{rn}$ dont il faut prouver la nature géométrique",
           "$u_{n+1}/u_n = e^r$ constant"),
    Family("suite_contexte_population", 4, "Contexte : croissance d'une population", NOTION_SUITES_GEOMETRIQUES,
           _gen_suite_contexte_population, "une modélisation de croissance continue $N(t)=N_0 e^{rt}$",
           "reconnaître la suite géométrique associée aux instants entiers"),
    Family("suite_contexte_radioactif", 4, "Contexte : désintégration radioactive", NOTION_SUITES_GEOMETRIQUES,
           _gen_suite_contexte_radioactif, "une modélisation de décroissance continue $N(t)=N_0 e^{-\\lambda t}$",
           "reconnaître une suite géométrique de raison $0<q<1$"),
    Family("suite_contexte_capitalisation", 4, "Contexte : capitalisation continue", NOTION_SUITES_GEOMETRIQUES,
           _gen_suite_contexte_capitalisation, "une modélisation d'intérêts composés continus $C(t)=C_0 e^{rt}$",
           "reconnaître une suite géométrique de raison $q>1$"),
    Family("suite_sens_variation", 3, "Sens de variation sans calcul numérique", NOTION_SUITES_GEOMETRIQUES,
           _gen_suite_sens_variation, "une suite géométrique de raison $e^r$ dont le sens de variation est à justifier",
           "comparer l'exposant $r$ à $0$ pour situer $e^r$ par rapport à $1$"),
)

FAMILIES_BY_NOTION: dict[str, tuple[Family, ...]] = {}
for _f in FAMILIES:
    FAMILIES_BY_NOTION.setdefault(_f.notion, [])
    FAMILIES_BY_NOTION[_f.notion].append(_f)
FAMILIES_BY_NOTION = {k: tuple(v) for k, v in FAMILIES_BY_NOTION.items()}


def build_exercise(family: Family, rng: random.Random) -> Optional[dict]:
    """Construit un exercice complet à partir d'une famille. Renvoie None si
    le générateur juge le tirage dégénéré (ex: équation sans solution
    exploitable) — l'appelant retire alors une nouvelle graine, exactement
    comme dans `derivatives.build_exercise`."""
    try:
        payload = family.generate(rng)
    except Exception:
        return None
    if payload is None:
        return None

    score = payload["score"]
    real_level = _difficulty_bucket_from_score(score)

    return {
        "enonce": payload["enonce"],
        "answer": payload["answer"],
        "hint": payload["hint"],
        "solution_steps": payload["steps"],
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


def generate_pool(per_family: int = 10, seed: int = 20260819) -> list[dict]:
    """Génère un pool diversifié : `per_family` exercices distincts par
    famille (30 familles couvrant les 6 notions du Chapitre_5), dédupliqués
    par signature d'énoncé, avec alternance round-robin des familles —
    même contrat que `derivatives.generate_pool`."""
    rng = random.Random(seed)
    per_family_pool: dict[str, list[dict]] = {}
    for family in FAMILIES:
        seen_signatures = set()
        items = []
        attempts = 0
        while len(items) < per_family and attempts < per_family * 60:
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
        family = FAMILIES[idx % len(FAMILIES)]
        bucket = per_family_pool.get(family.id) or []
        if bucket:
            pool.append(bucket.pop(0))
        idx += 1
        if idx > 200000:
            break
    # IDs entiers : mêmes contraintes que derivatives.GENERATED_ID_OFFSET
    # (route Flask /api/exercise/<int:exercise_id>, contrat BANK_BY_ID).
    for i, ex in enumerate(pool):
        ex["id"] = GENERATED_ID_OFFSET + i
    return pool
