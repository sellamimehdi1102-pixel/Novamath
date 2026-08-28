"""Génération symbolique d'exercices de dérivation (Première spécialité).

Principe : chaque "famille" décrit une STRUCTURE mathématique (pas un
simple jeu de coefficients). La dérivée est calculée par sympy (`diff`),
donc toujours correcte, jamais approximée. La difficulté affichée est
recalculée depuis la complexité réelle de l'expression produite
(`real_difficulty_score`) et non depuis une étiquette arbitraire — voir
tools/generate_derivative_exercises.py qui vérifie que chaque famille reste
dans la fourchette de difficulté attendue avant d'écrire le pool final.
"""
import random
from dataclasses import dataclass
from typing import Callable, Optional

import sympy
from sympy import (
    Add, Mul, Pow, Rational, S, diff, latex, simplify, sqrt, symbols,
)

x = symbols("x")
t = symbols("t")

CHAPTER_ID = "Chapitre_3"
NOTION = "Fonction dérivée"

# Phase 5 du chantier de diversification (voir prompt) : la notion
# "Composition de fonctions et dérivation" est proche de "Fonction dérivée"
# (même chapitre, même outillage sympy) — on étend donc CE module plutôt que
# d'en créer un nouveau. Les familles "compo_*" ciblent NOTION_COMPOSITION ;
# toutes les autres familles gardent NOTION comme avant (valeur par défaut du
# champ `notion` de Family, voir plus bas — aucune des 16 définitions
# existantes n'a besoin d'être modifiée).
NOTION_COMPOSITION = "Composition de fonctions et dérivation"

# Très au-dessus du plus grand id possible d'une banque curée (~2000
# exercices max par classe aujourd'hui) : voir generate_pool() plus bas —
# la route Flask /api/exercise/<int:exercise_id> attend un id entier.
GENERATED_ID_OFFSET = 900_000


def _nz(rng: random.Random, lo: int, hi: int) -> int:
    """Entier non nul dans [lo, hi] (utilisé pour tout coefficient qui ne
    doit jamais s'annuler, sous peine de dégénérer la structure voulue —
    ex: un coefficient directeur nul transformerait un produit en un simple
    facteur constant)."""
    choices = [n for n in range(lo, hi + 1) if n != 0]
    return rng.choice(choices)


def _small(rng: random.Random, lo=-9, hi=9) -> int:
    return rng.randint(lo, hi)


# ── Générateurs de structure par famille ──────────────────────────────────
# Chaque générateur reçoit un rng seedé et renvoie (expression sympy, notes)
# où `notes` documente en français les paramètres tirés, pour construire
# l'énoncé et les explications sans dupliquer la logique de tirage.

def _gen_constante(rng):
    c = _small(rng, -12, 12)
    return S(c), {"c": c}


def _gen_affine(rng):
    a, b = _nz(rng, -6, 6), _small(rng)
    return a * x + b, {"a": a, "b": b}


def _gen_polynome_simple(rng):
    a, b, c = _nz(rng, -4, 4), _small(rng), _small(rng)
    return a * x**2 + b * x + c, {"a": a, "b": b, "c": c}


def _gen_polynome_sup(rng):
    a, b, c, d = _nz(rng, -3, 3), _small(rng, -4, 4), _small(rng), _small(rng)
    return a * x**3 + b * x**2 + c * x + d, {"a": a, "b": b, "c": c, "d": d}


def _gen_produit_simple(rng):
    a, b = _nz(rng, -4, 4), _small(rng, -5, 5)
    c, d = _nz(rng, -4, 4), _small(rng, -5, 5)
    return (a * x + b) * (c * x + d), {"a": a, "b": b, "c": c, "d": d}


def _gen_fraction_simple(rng):
    a = _nz(rng, -6, 6)
    b = _nz(rng, -5, 5)
    return a / (x + b), {"a": a, "b": b}


def _gen_racine_simple(rng):
    a = _nz(rng, 1, 5)
    b = _small(rng, 0, 8)
    return sqrt(a * x + b), {"a": a, "b": b}


def _gen_coeff_fractionnaire(rng):
    a, b = _nz(rng, 2, 5), _nz(rng, 2, 5)
    c, d = _nz(rng, 2, 5), _nz(rng, 2, 5)
    return Rational(a, b) * x**2 + Rational(c, d) * x, {
        "a": a, "b": b, "c": c, "d": d,
    }


def _gen_fraction_rationnelle(rng):
    a, b = _nz(rng, -4, 4), _small(rng, -5, 5)
    c, d = _nz(rng, -4, 4), _small(rng, -5, 5)
    # évite un dénominateur constant (dégénère en fraction_simple) et une
    # simplification triviale (a/c annule le quotient)
    while c == 0 or a * d == b * c:
        c, d = _nz(rng, -4, 4), _small(rng, -5, 5)
    return (a * x + b) / (c * x + d), {"a": a, "b": b, "c": c, "d": d}


def _gen_produit_complexe(rng):
    a, b, c = _nz(rng, -3, 3), _small(rng, -4, 4), _small(rng, -4, 4)
    d, e = _nz(rng, -3, 3), _small(rng, -5, 5)
    return (a * x**2 + b * x + c) * (d * x + e), {
        "a": a, "b": b, "c": c, "d": d, "e": e,
    }


def _gen_racine_complexe(rng):
    a = _nz(rng, 1, 3)
    b = _small(rng, -3, 3)
    c = _small(rng, 4, 12)  # positif pour limiter le risque de domaine vide
    return sqrt(a * x**2 + b * x + c), {"a": a, "b": b, "c": c}


def _gen_composition_puissance(rng):
    a, b = _nz(rng, -3, 3), _small(rng, -4, 4)
    n = rng.choice([3, 4, 5])
    return (a * x + b) ** n, {"a": a, "b": b, "n": n}


def _gen_quotient_complexe(rng):
    a, b, c = _nz(rng, -3, 3), _small(rng, -4, 4), _small(rng, -4, 4)
    d, e = _nz(rng, -3, 3), _small(rng, -5, 5)
    while d == 0:
        d = _nz(rng, -3, 3)
    return (a * x**2 + b * x + c) / (d * x + e), {
        "a": a, "b": b, "c": c, "d": d, "e": e,
    }


def _gen_composition_racine_quotient(rng):
    a, b = _nz(rng, 1, 4), _small(rng, -3, 3)
    c, d = _nz(rng, 1, 4), _small(rng, 1, 5)
    # évite un quotient identiquement constant (a/c == b/d), qui annulerait
    # la dérivée et dégénérerait l'exercice en calcul trivial
    while a * d == b * c:
        c, d = _nz(rng, 1, 4), _small(rng, 1, 5)
    return sqrt((a * x + b) / (c * x + d)), {"a": a, "b": b, "c": c, "d": d}


def _gen_combinee(rng):
    a, b = _nz(rng, 1, 3), _small(rng, -3, 3)
    c, d = _nz(rng, 1, 3), _small(rng, 1, 5)
    e, f = _nz(rng, -2, 2), _small(rng, -3, 3)
    return sqrt(a * x + b) / (c * x + d) + (e * x + f) ** 2, {
        "a": a, "b": b, "c": c, "d": d, "e": e, "f": f,
    }


def _gen_simplification_prealable(rng):
    # (a²x² - b²) / (ax - b) = ax + b après factorisation par différence de
    # carrés — le piège pédagogique voulu est de dériver AVANT de simplifier
    # (calcul long et sujet à erreur) plutôt qu'après (immédiat).
    a = _nz(rng, 2, 5)
    b = _nz(rng, 1, 6)
    expr = (a**2 * x**2 - b**2) / (a * x - b)
    return expr, {"a": a, "b": b}


# ── Familles "Composition de fonctions et dérivation" (Phase 5) ────────────
# Notion distincte de "Fonction dérivée" : il ne s'agit plus seulement de
# calculer une dérivée de fonction composée (déjà couvert par
# composition_puissance/racine_complexe/composition_racine_quotient
# ci-dessus, légitimement conservées), mais de raisonner sur la composition
# ELLE-MÊME — décomposer f=v∘u, domaine d'une composée, évaluation,
# reconnaissance, application nommée de la règle de la chaîne, détection
# d'erreur, synthèse. Comme dans suites.py, `generate` renvoie ici
# directement `notes` (dict déjà rédigé), pas `(expr, params)` : il n'existe
# pas d'opération générique unique applicable à toutes ces familles. Voir la
# branche dédiée dans build_exercise (family.id.startswith("compo_")).

def _gen_compo_decompose(rng):
    """Décomposer f = v∘u : identifier u (fonction interne, affine ou
    quadratique) et v (fonction externe : racine, inverse, puissance)."""
    inner_kind = rng.choice(["affine", "quadratique"])
    if inner_kind == "affine":
        a, b = _nz(rng, -5, 5), _small(rng, -6, 6)
        u_expr = a * x + b
        u_latex = f"u(x) = {latex(u_expr)}"
    else:
        a, b, c = _nz(rng, -3, 3), _small(rng, -4, 4), _small(rng, -4, 4)
        u_expr = a * x**2 + b * x + c
        u_latex = f"u(x) = {latex(u_expr)}"

    outer_kind = rng.choice(["racine", "inverse", "puissance"])
    if outer_kind == "racine":
        v_t = sqrt(t)
        f_expr = sqrt(u_expr)
        v_latex = "v(t) = \\sqrt{t}"
    elif outer_kind == "inverse":
        v_t = 1 / t
        f_expr = 1 / u_expr
        v_latex = "v(t) = \\dfrac{1}{t}"
    else:
        n = rng.choice([2, 3, 4])
        v_t = t**n
        f_expr = u_expr**n
        v_latex = f"v(t) = t^{{{n}}}"

    # Vérification indépendante : v(u(x)) doit bien redonner f(x).
    recompose = simplify(v_t.subs(t, u_expr) - f_expr)
    if recompose != 0:
        return None

    enonce = (
        f"On considère la fonction $f$ définie par $f(x) = {latex(f_expr)}$. "
        "Écrire $f$ comme une composée $f = v \\circ u$ de deux fonctions plus simples, "
        "en précisant les expressions de $u(x)$ et de $v(t)$."
    )
    steps = [
        f"Étape 1 — On repère la fonction \"intérieure\" appliquée en premier à $x$ : ${u_latex}$.",
        f"Étape 2 — On repère la fonction \"extérieure\" appliquée ensuite au résultat : ${v_latex}$.",
        f"Étape 3 — On vérifie : $v(u(x)) = {latex(simplify(v_t.subs(t, u_expr)))} = f(x)$. ✓",
    ]
    answer = f"${u_latex}$ et ${v_latex}$ (avec $f = v \\circ u$)"
    hint = "Repérer la dernière opération effectuée sur x : c'est v. Ce qui reste \"à l'intérieur\" est u."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


def _gen_compo_domaine(rng):
    """Calculer le domaine de définition d'une composée : sqrt(u(x)) (il
    faut u(x)>=0) ou 1/u(x) (il faut u(x)!=0), avec u affine."""
    kind = rng.choice(["racine", "inverse"])
    a = _nz(rng, -5, 5)
    b = _small(rng, -8, 8)
    # Pour |a|>1, un b multiple de a donnerait un zéro entier "trop propre"
    # (peu représentatif) : on ajuste. Pour a=±1, b est TOUJOURS multiple de
    # a (tout entier l'est), donc ce cas ne signale rien à éviter — sans
    # cette distinction, l'ajustement pouvait lui-même retomber sur b=0.
    if kind == "inverse" and abs(a) > 1 and b % a == 0:
        b += 1
    u_expr = a * x + b
    if kind == "racine":
        f_expr = sqrt(u_expr)
        borne = Rational(-b, a)
        if a > 0:
            domaine = f"\\left[{latex(borne)};+\\infty\\right["
            cond = f"x \\geq {latex(borne)}"
        else:
            domaine = f"\\left]-\\infty;{latex(borne)}\\right]"
            cond = f"x \\leq {latex(borne)}"
        enonce = (
            f"Déterminer l'ensemble de définition de la fonction $f$ définie par "
            f"$f(x) = \\sqrt{{{latex(u_expr)}}}$."
        )
        steps = [
            "Étape 1 — Une racine carrée n'est définie que si son contenu est positif ou nul.",
            f"Étape 2 — On résout ${latex(u_expr)} \\geq 0$, ce qui donne ${cond}$.",
        ]
        answer = f"$D_f = {domaine}$"
    else:
        f_expr = 1 / u_expr
        zero = Rational(-b, a)
        enonce = (
            f"Déterminer l'ensemble de définition de la fonction $f$ définie par "
            f"$f(x) = \\dfrac{{1}}{{{latex(u_expr)}}}$."
        )
        steps = [
            "Étape 1 — Un quotient n'est défini que si son dénominateur est non nul.",
            f"Étape 2 — On résout ${latex(u_expr)} = 0$, ce qui donne $x = {latex(zero)}$ : cette valeur est exclue.",
        ]
        answer = f"$D_f = \\mathbb{{R}} \\setminus \\left\\{{{latex(zero)}\\right\\}}$"
    hint = "Identifier la fonction interne u(x) et traduire la contrainte imposée par la fonction externe (racine : u≥0 ; inverse : u≠0)."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


def _gen_compo_evaluer(rng):
    """Évaluer numériquement (f∘g)(a) à partir de deux fonctions simples."""
    af, bf = _nz(rng, -4, 4), _small(rng, -5, 5)
    ag, bg = _nz(rng, -4, 4), _small(rng, -5, 5)
    f_expr = af * x + bf
    g_expr = ag * x + bg
    a_val = _small(rng, -4, 4)
    g_a = g_expr.subs(x, a_val)
    fg_a = f_expr.subs(x, g_a)
    enonce = (
        f"On donne $f(x) = {latex(f_expr)}$ et $g(x) = {latex(g_expr)}$. "
        f"Calculer $(f \\circ g)({a_val})$."
    )
    steps = [
        f"Étape 1 — On calcule d'abord $g({a_val}) = {latex(g_a)}$.",
        f"Étape 2 — On calcule ensuite $f\\big(g({a_val})\\big) = f({latex(g_a)}) = {latex(fg_a)}$.",
    ]
    answer = f"$(f \\circ g)({a_val}) = {latex(fg_a)}$"
    hint = "(f∘g)(a) signifie : d'abord appliquer g à a, puis appliquer f au résultat obtenu — jamais l'inverse."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


def _gen_compo_expression(rng):
    """Calculer l'expression de f∘g à partir de f et g données (l'une des
    deux quadratique pour éviter un exercice trop répétitif)."""
    kind = rng.choice(["f_affine_g_affine", "f_carre_g_affine"])
    ag, bg = _nz(rng, -4, 4), _small(rng, -5, 5)
    g_expr = ag * x + bg
    if kind == "f_affine_g_affine":
        af, bf = _nz(rng, -4, 4), _small(rng, -5, 5)
        f_expr = af * x + bf
    else:
        f_expr = x**2 + _small(rng, -4, 4)
    fg_expr = sympy.expand(f_expr.subs(x, g_expr))
    enonce = (
        f"On donne $f(x) = {latex(f_expr)}$ et $g(x) = {latex(g_expr)}$. "
        "Déterminer l'expression de $(f \\circ g)(x)$, développée et réduite."
    )
    steps = [
        f"Étape 1 — $(f\\circ g)(x) = f\\big(g(x)\\big) = f\\big({latex(g_expr)}\\big)$.",
        f"Étape 2 — On remplace $x$ par ${latex(g_expr)}$ dans l'expression de $f$, puis on développe : "
        f"$(f\\circ g)(x) = {latex(fg_expr)}$.",
    ]
    answer = f"$(f \\circ g)(x) = {latex(fg_expr)}$"
    hint = "Remplacer x par g(x) dans l'expression de f, puis développer et réduire."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


def _gen_compo_reconnaitre(rng):
    """Reconnaître si une expression correspond à une composition ou à une
    opération classique (produit ou somme de deux fonctions affines)."""
    is_composition = rng.random() < 0.5
    if is_composition:
        a, b = _nz(rng, -4, 4), _small(rng, -5, 5)
        n = rng.choice([2, 3])
        outer = rng.choice(["puissance", "racine"])
        if outer == "puissance":
            u_inner = a * x + b
            expr = u_inner ** n
            expr_latex = latex(expr)
            just = (
                f"C'est une composition : on calcule d'abord $u(x)={latex(u_inner)}$, "
                f"puis on élève le résultat à la puissance ${n}$ — deux opérations appliquées l'une après l'autre "
                "à la même variable, pas deux fonctions combinées terme à terme."
            )
        else:
            b_pos = abs(b) + 1
            expr = sqrt(a * x + b_pos) if a > 0 else sqrt(-a * x + b_pos)
            expr_latex = latex(expr)
            just = (
                "C'est une composition : on calcule d'abord une expression affine, puis on en prend la racine carrée "
                "— la racine s'applique au RÉSULTAT de l'expression affine, pas à $x$ directement."
            )
        answer = f"Composition. {just}"
    else:
        a, b, c, d = _nz(rng, -4, 4), _small(rng, -5, 5), _nz(rng, -4, 4), _small(rng, -5, 5)
        op = rng.choice(["produit", "somme"])
        if op == "produit":
            expr = (a * x + b) * (c * x + d)
            expr_latex = latex(sympy.expand(expr))
            just = (
                "C'est un produit de deux fonctions affines évaluées séparément en $x$ et multipliées entre elles "
                "— aucune fonction n'est appliquée au résultat d'une autre."
            )
        else:
            expr = a * x**2 + b * x + c * x + d
            expr_latex = latex(sympy.expand(expr))
            just = (
                "C'est une somme de termes en $x$, pas une composition : chaque terme dépend directement de $x$, "
                "aucun n'est le résultat d'une autre fonction appliquée en premier."
            )
        answer = f"Pas une composition ({op}). {just}"
    enonce = (
        f"On considère l'expression $h(x) = {expr_latex}$. "
        "S'agit-il d'une composition de deux fonctions, ou d'une opération classique (produit, somme) "
        "entre deux fonctions ? Justifier."
    )
    steps = [
        "Étape 1 — On identifie si une opération s'applique au RÉSULTAT d'une autre (composition), "
        "ou si deux expressions en $x$ sont simplement combinées (produit/somme).",
        f"Étape 2 — {answer}",
    ]
    hint = "Une composition applique une fonction au résultat d'une autre ; un produit/une somme combine deux expressions de x indépendamment."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


def _gen_compo_regle_chaine(rng):
    """Application EXPLICITE et nommée de (v∘u)' = u' × (v'∘u), en
    distinguant u, v, u', v' avant de les combiner — plus conceptuel que le
    calcul direct de dérivée de composée (déjà couvert par ailleurs)."""
    a, b = _nz(rng, -4, 4), _small(rng, -5, 5)
    u_expr = a * x + b
    outer_kind = rng.choice(["racine", "puissance", "inverse"])
    if outer_kind == "racine":
        v_t, vprime_t = sqrt(t), diff(sqrt(t), t)
        v_latex, vprime_latex = "v(t)=\\sqrt{t}", "v'(t)=\\dfrac{1}{2\\sqrt{t}}"
    elif outer_kind == "puissance":
        n = rng.choice([3, 4, 5])
        v_t, vprime_t = t**n, n * t**(n - 1)
        v_latex, vprime_latex = f"v(t)=t^{{{n}}}", f"v'(t)={n}t^{{{n-1}}}"
    else:
        v_t, vprime_t = 1 / t, -1 / t**2
        v_latex, vprime_latex = "v(t)=\\dfrac{1}{t}", "v'(t)=-\\dfrac{1}{t^2}"

    uprime_expr = diff(u_expr, x)
    f_expr = v_t.subs(t, u_expr)
    fprime_via_chain = simplify(uprime_expr * vprime_t.subs(t, u_expr))
    fprime_direct = simplify(diff(f_expr, x))
    if simplify(fprime_via_chain - fprime_direct) != 0:
        return None  # garde-fou : les deux calculs doivent coïncider

    enonce = (
        f"Soit $f(x) = {latex(f_expr)}$. En posant $u(x) = {latex(u_expr)}$ et ${v_latex}$ (de sorte que "
        "$f=v\\circ u$), calculer séparément $u'(x)$ et $v'(t)$, puis en déduire $f'(x)$ à l'aide de la formule "
        "$(v\\circ u)'(x) = u'(x)\\times v'\\big(u(x)\\big)$."
    )
    steps = [
        f"Étape 1 — $u'(x) = {latex(uprime_expr)}$.",
        f"Étape 2 — ${vprime_latex}$, donc $v'\\big(u(x)\\big) = {latex(vprime_t.subs(t, u_expr))}$.",
        f"Étape 3 — $f'(x) = u'(x)\\times v'\\big(u(x)\\big) = {latex(uprime_expr)} \\times "
        f"{latex(vprime_t.subs(t, u_expr))} = {latex(fprime_via_chain)}$.",
    ]
    answer = f"$f'(x) = {latex(fprime_via_chain)}$"
    hint = "Calculer u'(x) et v'(t) séparément, remplacer t par u(x) dans v'(t), puis multiplier par u'(x) — ne jamais dériver directement l'expression composée sans ces étapes."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


def _gen_compo_erreur(rng):
    """Détecter/corriger une erreur classique de dérivation de composée :
    oubli du facteur u'(x) (l'élève dérive v comme si u(x)=x)."""
    a, b = _nz(rng, -4, 4), _small(rng, -5, 5)
    u_expr = a * x + b
    outer_kind = rng.choice(["racine", "puissance"])
    if outer_kind == "racine":
        f_expr = sqrt(u_expr)
        correct = simplify(diff(f_expr, x))
        wrong = 1 / (2 * sqrt(u_expr))  # oubli du facteur u'(x) = a
        wrong_latex = "\\dfrac{1}{2\\sqrt{" + latex(u_expr) + "}}"
    else:
        n = rng.choice([3, 4])
        f_expr = u_expr**n
        correct = simplify(diff(f_expr, x))
        wrong = n * u_expr**(n - 1)  # oubli du facteur u'(x) = a
        wrong_latex = f"{n}\\left({latex(u_expr)}\\right)^{{{n-1}}}"
    if simplify(wrong - correct) == 0:
        return None  # dégénéré si a=1 (le facteur oublié vaudrait 1, l'erreur serait invisible)

    enonce = (
        f"Un élève calcule la dérivée de $f(x) = {latex(f_expr)}$ ainsi : \"$f'(x) = {wrong_latex}$\" "
        "(il applique la règle de dérivation de $v$ mais oublie de multiplier par la dérivée de la fonction "
        "intérieure $u$). Identifier son erreur et donner la dérivée correcte."
    )
    steps = [
        f"Étape 1 — En posant $u(x)={latex(u_expr)}$, l'élève a dérivé $v$ correctement mais a oublié le "
        f"facteur $u'(x) = {a}$ imposé par la règle de composition $(v\\circ u)'=u'\\times v'\\circ u$.",
        f"Étape 2 — La dérivée correcte est $f'(x) = {latex(correct)}$.",
    ]
    answer = f"Facteur $u'(x)={a}$ oublié ; la dérivée correcte est $f'(x) = {latex(correct)}$."
    hint = "Toute dérivée de fonction composée doit comporter le facteur u'(x) — vérifier qu'il n'a pas été \"oublié\" en route."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


def _gen_compo_synthese(rng):
    """Problème de synthèse : composition + dérivée (règle de la chaîne) +
    interprétation du signe de f'(a) en un point donné."""
    a_coef = _nz(rng, -3, 3)
    b_coef = _small(rng, -4, 4)
    u_expr = a_coef * x + b_coef
    n = rng.choice([2, 3])
    f_expr = u_expr**n
    fprime = simplify(diff(f_expr, x))
    point = _small(rng, -4, 4)
    if u_expr.subs(x, point) == 0:
        return None  # dérivée nulle en ce point pour n=2 → signe non tranché, on évite
    slope_at_point = simplify(fprime.subs(x, point))
    if slope_at_point == 0:
        return None
    sens = "croissante" if slope_at_point > 0 else "décroissante"
    enonce = (
        f"Soit $f(x) = {latex(f_expr)}$, composée de $u(x) = {latex(u_expr)}$ et de $v(t)=t^{{{n}}}$. "
        f"Calculer $f'(x)$, puis étudier le signe de $f'({point})$ pour en déduire si $f$ est localement "
        f"croissante ou décroissante au voisinage de $x={point}$."
    )
    steps = [
        f"Étape 1 — $u'(x) = {a_coef}$, et $v'(t) = {n}t^{{{n-1}}}$, donc "
        f"$f'(x) = u'(x)\\times v'\\big(u(x)\\big) = {latex(fprime)}$.",
        f"Étape 2 — $f'({point}) = {latex(slope_at_point)}$.",
        f"Étape 3 — Comme $f'({point})$ est {'positif' if slope_at_point > 0 else 'négatif'}, "
        f"$f$ est localement {sens} au voisinage de $x={point}$.",
    ]
    answer = f"$f'(x) = {latex(fprime)}$ ; $f'({point}) = {latex(slope_at_point)}$, donc $f$ est localement {sens} en $x={point}$."
    hint = "Calculer f' via la règle de la chaîne, puis relier le signe de f'(a) au sens de variation local en a (sans étude supplémentaire)."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


@dataclass(frozen=True)
class Family:
    id: str
    level: int  # 1 (facile) .. 5 (défi) — étiquette de départ, revalidée par real_difficulty_score
    label: str
    generate: Callable[[random.Random], tuple]
    structure_hint: str  # explique la structure pour la consigne pédagogique
    rule_hint: str  # règle de dérivation principale à mobiliser
    notion: str = NOTION  # notion exacte (Chapitre_3) — voir NOTION_COMPOSITION pour les familles compo_*


FAMILIES: tuple[Family, ...] = (
    Family("constante", 1, "Fonction constante", _gen_constante,
           "une fonction constante", "la dérivée d'une constante est nulle"),
    Family("affine", 1, "Fonction affine", _gen_affine,
           "une fonction affine", "la dérivée de $ax+b$ est $a$"),
    Family("polynome_simple", 1, "Polynôme du second degré", _gen_polynome_simple,
           "un polynôme du second degré", "la dérivée terme à terme d'un polynôme"),
    Family("polynome_sup", 2, "Polynôme de degré supérieur", _gen_polynome_sup,
           "un polynôme de degré 3", "la dérivée terme à terme d'un polynôme"),
    Family("produit_simple", 2, "Produit de deux fonctions affines", _gen_produit_simple,
           "un produit de deux facteurs affines", "la règle du produit $(uv)'=u'v+uv'$"),
    Family("fraction_simple", 2, "Fraction simple", _gen_fraction_simple,
           "une fraction avec un dénominateur affine", "la règle du quotient (cas $u$ constant)"),
    Family("racine_simple", 2, "Racine d'une expression affine", _gen_racine_simple,
           "une racine carrée d'une expression affine", "la dérivée de $\\sqrt{u}$ est $\\frac{u'}{2\\sqrt{u}}$"),
    Family("coeff_fractionnaire", 2, "Polynôme à coefficients fractionnaires", _gen_coeff_fractionnaire,
           "un polynôme dont les coefficients sont des fractions", "la dérivée terme à terme, calcul fractionnaire"),
    Family("fraction_rationnelle", 3, "Fonction rationnelle (quotient affine/affine)", _gen_fraction_rationnelle,
           "un quotient de deux fonctions affines", "la règle du quotient $(u/v)'=\\frac{u'v-uv'}{v^2}$"),
    Family("produit_complexe", 3, "Produit polynôme × affine", _gen_produit_complexe,
           "un produit d'un polynôme du second degré et d'une fonction affine", "la règle du produit"),
    Family("racine_complexe", 3, "Racine d'un polynôme du second degré", _gen_racine_complexe,
           "une racine carrée d'un polynôme du second degré", "la composition avec $\\sqrt{u}$"),
    Family("composition_puissance", 3, "Puissance d'une expression affine", _gen_composition_puissance,
           "une puissance $n$-ième d'une expression affine", "la règle de composition $(u^n)'=nu'u^{n-1}$"),
    Family("quotient_complexe", 4, "Quotient polynôme/affine", _gen_quotient_complexe,
           "un quotient d'un polynôme du second degré par une fonction affine", "la règle du quotient"),
    Family("composition_racine_quotient", 4, "Racine d'un quotient", _gen_composition_racine_quotient,
           "une racine carrée d'un quotient de deux fonctions affines", "composition de $\\sqrt{u}$ et du quotient"),
    Family("combinee", 5, "Somme combinant plusieurs règles", _gen_combinee,
           "une somme d'un quotient sous racine et d'une puissance", "plusieurs règles combinées : somme, quotient, racine, puissance"),
    Family("simplification_prealable", 5, "Expression nécessitant une simplification", _gen_simplification_prealable,
           "un quotient qui se simplifie par une identité remarquable", "reconnaître une différence de carrés avant de dériver"),

    # Composition de fonctions et dérivation (Phase 5)
    Family("compo_evaluer", 1, "Évaluation numérique de f∘g", _gen_compo_evaluer,
           "deux fonctions affines simples", "calculer g(a) d'abord, puis f de ce résultat",
           NOTION_COMPOSITION),
    Family("compo_decompose", 2, "Décomposer f en v∘u", _gen_compo_decompose,
           "une fonction composée", "identifier la fonction interne u et la fonction externe v",
           NOTION_COMPOSITION),
    Family("compo_expression", 2, "Expression de f∘g", _gen_compo_expression,
           "deux fonctions données par leur expression", "remplacer x par g(x) dans f puis développer",
           NOTION_COMPOSITION),
    Family("compo_reconnaitre", 2, "Composition ou opération classique ?", _gen_compo_reconnaitre,
           "une expression à classifier", "une composition applique une fonction au résultat d'une autre",
           NOTION_COMPOSITION),
    Family("compo_domaine", 3, "Domaine de définition d'une composée", _gen_compo_domaine,
           "une racine ou un inverse d'une fonction affine", "traduire la contrainte imposée par la fonction externe",
           NOTION_COMPOSITION),
    Family("compo_regle_chaine", 3, "Application nommée de la règle de la chaîne", _gen_compo_regle_chaine,
           "une composée f=v∘u", "(v∘u)'=u'×(v'∘u), en calculant u' et v' séparément",
           NOTION_COMPOSITION),
    Family("compo_erreur", 4, "Erreur de dérivation de composée à corriger", _gen_compo_erreur,
           "une dérivée de composée où le facteur u' a été oublié", "comparer à la règle (v∘u)'=u'×(v'∘u)",
           NOTION_COMPOSITION),
    Family("compo_synthese", 5, "Synthèse : composition, dérivée et signe", _gen_compo_synthese,
           "une composée dont on étudie le signe de la dérivée en un point", "règle de la chaîne puis interprétation du signe",
           NOTION_COMPOSITION),
)

# Score fixe par famille "compo_*" (mêmes bornes de bucket que
# real_difficulty_score/_difficulty_bucket_from_score ci-dessus) : reflète la
# profondeur de raisonnement du TYPE de question, pas la taille des nombres
# tirés (interdit par le cahier des charges) — ces familles ne calculent pas
# toutes une unique expression sympy à noter, contrairement aux familles de
# calcul de dérivée pure.
FAMILY_BASE_SCORE_COMPO: dict[str, float] = {
    "compo_evaluer": 1.5,
    "compo_decompose": 3.5,
    "compo_expression": 4.0,
    "compo_reconnaitre": 4.5,
    "compo_domaine": 6.0,
    "compo_regle_chaine": 7.0,
    "compo_erreur": 9.0,
    "compo_synthese": 12.0,
}

FAMILIES_BY_LEVEL: dict[int, tuple[Family, ...]] = {
    level: tuple(f for f in FAMILIES if f.level == level) for level in range(1, 6)
}

LEVEL_META = {
    1: {"emoji": "🟢", "label": "Niveau 1 — Fondamental"},
    2: {"emoji": "🟡", "label": "Niveau 2 — Intermédiaire"},
    3: {"emoji": "🟠", "label": "Niveau 3 — Avancé"},
    4: {"emoji": "🔴", "label": "Niveau 4 — Difficile"},
    5: {"emoji": "🟣", "label": "Niveau 5 — Défi"},
}


def real_difficulty_score(expr) -> float:
    """Complexité algébrique réelle d'une expression, utilisée pour
    vérifier que la difficulté affichée correspond au contenu réel (Phase 1
    du chantier pédagogique : "un exercice affiché Difficile ne doit pas
    être un simple calcul de dérivée de x²").

    Combine : nombre d'opérations (sympy count_ops), présence d'une
    division (règle du quotient), présence d'une racine (composition),
    présence d'une puissance non entière ou d'une composition profonde, et
    le nombre de facteurs distincts au niveau supérieur (produit)."""
    score = float(expr.count_ops())
    if expr.has(sympy.Pow):
        for p in expr.atoms(Pow):
            if p.exp == Rational(1, 2):
                score += 2.5  # racine : règle de composition
            elif not p.exp.is_Integer:
                score += 2
            elif p.exp.is_Integer and p.exp not in (1, 2, -1):
                score += 1.5
    if any(a.exp.is_negative for a in expr.atoms(Pow) if a.exp.is_Integer):
        score += 2.0  # division déguisée en Pow(-1) → règle du quotient
    top = expr
    if isinstance(top, Add):
        score += 0.5 * (len(top.args) - 1)
    if isinstance(top, Mul):
        non_trivial_factors = [a for a in top.args if not a.is_number]
        if len(non_trivial_factors) >= 2:
            score += 2.0  # règle du produit
    return round(score, 2)


def _difficulty_bucket_from_score(score: float) -> int:
    """Convertit le score de complexité réelle en palier 1-5, avec les
    mêmes bornes que celles observées sur un grand échantillon généré (voir
    tools/generate_derivative_exercises.py::_check_family_calibration)."""
    if score <= 2:
        return 1
    if score <= 5:
        return 2
    if score <= 8:
        return 3
    if score <= 11:
        return 4
    return 5


def _describe_structure(expr) -> str:
    """Phrase pédagogique expliquant POURQUOI telle règle s'applique,
    plutôt qu'un simple résultat — répond à l'exigence "l'élève doit
    comprendre pourquoi on fait quelque chose"."""
    if not expr.free_symbols:
        return ("Il s'agit d'un nombre constant, qui ne dépend pas de $x$ : sa dérivée "
                "est nulle en tout point, quelle que soit la valeur de $x$.")
    has_div = any(a.exp.is_Integer and a.exp < 0 for a in expr.atoms(Pow))
    has_sqrt = any(a.exp == Rational(1, 2) for a in expr.atoms(Pow))
    if isinstance(expr, Add) and len(expr.args) > 1 and not expr.is_polynomial(x):
        return ("Il s'agit d'une somme de plusieurs termes de nature différente : "
                "on dérive chaque terme séparément, en appliquant à chacun la règle "
                "qui lui correspond, avant de tout additionner.")
    if has_div and has_sqrt:
        return ("Cette expression combine une racine carrée et un quotient : on "
                "commence par identifier la fonction interne du quotient, puis on "
                "applique la règle de dérivation de $\\sqrt{u}$.")
    if has_div:
        return ("Il s'agit d'un quotient de deux fonctions : on ne peut pas dériver "
                "numérateur et dénominateur séparément, il faut appliquer la règle "
                "$(u/v)' = \\frac{u'v - uv'}{v^2}$.")
    if has_sqrt:
        return ("Il s'agit d'une racine carrée d'une expression : c'est une "
                "composition de fonctions, on applique $(\\sqrt{u})' = \\frac{u'}{2\\sqrt{u}}$.")
    if isinstance(expr, Mul) and len([a for a in expr.args if not a.is_number]) >= 2:
        return ("Il s'agit d'un produit de deux fonctions : on ne peut pas dériver "
                "chaque facteur indépendamment, il faut appliquer la règle "
                "$(uv)' = u'v + uv'$.")
    if isinstance(expr, Pow) and expr.exp.is_Integer and expr.exp not in (1,):
        return ("Il s'agit d'une puissance d'une expression : c'est une composition, "
                "on applique $(u^n)' = n\\,u' \\,u^{n-1}$.")
    if expr.is_polynomial(x):
        return "Il s'agit d'un polynôme : on dérive chaque terme séparément, terme à terme."
    return "On identifie la forme de l'expression avant de choisir la règle de dérivation adaptée."


def _build_compo_exercise(family: Family, rng: random.Random) -> Optional[dict]:
    """Construit un exercice pour une famille compo_* : `generate` renvoie
    directement `notes` (dict déjà rédigé), pas `(expr, params)`, car ces
    familles n'ont pas d'opération générique unique (contrairement à `diff`
    pour les autres familles) — même principe que build_exercise dans
    suites.py. La difficulté vient de FAMILY_BASE_SCORE_COMPO (score fixe
    par famille, pas de la taille des nombres tirés)."""
    notes = family.generate(rng)
    if notes is None:
        return None
    score = FAMILY_BASE_SCORE_COMPO[family.id]
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


def build_exercise(family: Family, rng: random.Random) -> Optional[dict]:
    """Construit un exercice complet à partir d'une famille. Renvoie None
    si l'expression tirée dégénère (dérivée nulle, domaine vide...) — dans
    ce cas l'appelant retire simplement et retire une nouvelle graine."""
    if family.id.startswith("compo_"):
        return _build_compo_exercise(family, rng)
    expr, params = family.generate(rng)
    expr = sympy.together(expr) if family.id in ("simplification_prealable",) else expr
    try:
        derivative_raw = diff(expr, x)
        derivative = simplify(derivative_raw)
    except Exception:
        return None
    if derivative == 0 and family.id != "constante":
        return None  # dégénéré (ex: coefficients qui s'annulent) → retirer

    score = real_difficulty_score(expr)
    real_level = _difficulty_bucket_from_score(score)

    f_latex = sympy.latex(expr)
    fprime_raw_latex = sympy.latex(derivative_raw)
    fprime_latex = sympy.latex(derivative)

    steps = [
        f"Étape 1 — On identifie la structure de $f(x) = {f_latex}$ : {_describe_structure(expr)}",
        f"Étape 2 — On applique la règle ({family.rule_hint}) et on dérive : "
        f"$f'(x) = {fprime_raw_latex}$.",
    ]
    if sympy.simplify(derivative_raw - derivative) != 0 or str(derivative_raw) != str(derivative):
        steps.append(f"Étape 3 — On simplifie l'expression obtenue : $f'(x) = {fprime_latex}$.")
    else:
        steps[-1] = steps[-1][:-1] + f" (déjà sous forme simplifiée)."

    enonce = (
        f"Calculer la dérivée de la fonction $f$ définie par $f(x) = {f_latex}$."
        + (" (Indication : une simplification est possible avant de dériver.)"
           if family.id == "simplification_prealable" else "")
    )
    hint = f"Reconnais {family.structure_hint} : {family.rule_hint}."

    return {
        "enonce": enonce,
        "answer": f"$f'(x) = {fprime_latex}$",
        "hint": hint,
        "solution_steps": steps,
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


def generate_pool(per_family: int = 12, seed: int = 20260818) -> list[dict]:
    """Génère un pool diversifié : `per_family` exercices distincts par
    famille (16 familles), avec déduplication par signature d'énoncé pour
    qu'aucun couple d'exercices ne soit identique (Phase 1 : diversité
    contrôlée). L'ordre de sortie alterne les familles (round-robin) plutôt
    que de grouper une famille à la suite, pour qu'un pool consommé dans
    l'ordre n'enchaîne jamais deux exercices de la même famille."""
    rng = random.Random(seed)
    per_family_pool: dict[str, list[dict]] = {}
    for family in FAMILIES:
        seen_signatures = set()
        items = []
        attempts = 0
        while len(items) < per_family and attempts < per_family * 40:
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
        if idx > 100000:
            break
    # IDs entiers (pas de préfixe string) : la route Flask
    # /api/exercise/<int:exercise_id> et le contrat BANK_BY_ID existants
    # attendent un id entier — voir server.py::api_exercise. L'offset
    # GENERATED_ID_OFFSET est très au-dessus du plus grand id possible
    # d'une banque curée (~2000 exercices max par classe aujourd'hui) pour
    # ne jamais entrer en collision.
    for i, ex in enumerate(pool):
        ex["id"] = GENERATED_ID_OFFSET + i
    return pool
