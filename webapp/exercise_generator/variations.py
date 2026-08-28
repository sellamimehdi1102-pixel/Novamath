"""Génération symbolique d'exercices « Variations d'une fonction » et
« Nombre dérivé et extremums locaux » (Première spécialité, Chapitre_4).

Même principe que webapp/exercise_generator/derivatives.py (patron de
référence) : chaque famille décrit une STRUCTURE de raisonnement différente
(pas seulement des coefficients qui changent), tout calcul (dérivée,
résolution de $f'(x)=0$, étude de signe) est fait par sympy — jamais
approximé ni inventé — et la difficulté affichée est recalculée depuis la
complexité réelle de l'expression produite.

Un audit de exercises_bank_premiere.json a montré que le Chapitre_4 était
très redondant sur ces deux notions : « Variations d'une fonction » (95 %
redondant, toujours le même moule "f'(x) = a(x-r1)(x-r2) donné, en déduire
les variations") et « Nombre dérivé et extremums locaux » (81 % redondant,
toujours "f(x) = x^3 - k x, factoriser f', en déduire les extremums"). Ce
module ajoute 8 familles de VRAIS types de raisonnement différents : lecture
directe d'un signe donné, calcul à étapes (degré 2 et 3), problème inversé
(retrouver un coefficient), interprétation contextualisée, vrai/faux
justifié, erreur à corriger, et optimisation contextualisée — plutôt que de
faire varier uniquement les coefficients d'un seul moule.
"""
import random
from dataclasses import dataclass
from typing import Callable, Optional

import sympy
from sympy import Rational, S, diff, latex, oo, simplify, solve, symbols

from exercise_generator import derivatives as deriv_gen

x = symbols("x")

CHAPTER_ID = "Chapitre_4"
NOTION_VARIATIONS = "Variations d'une fonction"
NOTION_EXTREMUMS = "Nombre dérivé et extremums locaux"

# Même logique que derivatives.GENERATED_ID_OFFSET : très au-dessus du plus
# grand id possible d'une banque curée (~2000 exercices max par classe), et
# assez éloigné de GENERATED_ID_OFFSET (900_000, Chapitre_3) pour ne jamais
# entrer en collision entre les deux moteurs de génération.
GENERATED_ID_OFFSET = 930_000

LEVEL_META = deriv_gen.LEVEL_META


# ── Utilitaires communs : signe de f', intervalles, extremums ─────────────

def _nz(rng: random.Random, lo: int, hi: int) -> int:
    choices = [n for n in range(lo, hi + 1) if n != 0]
    return rng.choice(choices)


def _format_bound(v) -> str:
    if v == -oo:
        return "-\\infty"
    if v == oo:
        return "+\\infty"
    return latex(sympy.nsimplify(v))


def _interval_latex(lo, hi) -> str:
    left = "]" if lo == -oo else "["
    right = "[" if hi == oo else "]"
    return f"{left}{_format_bound(lo)} ; {_format_bound(hi)}{right}"


def _test_point(lo, hi):
    if lo == -oo and hi == oo:
        return S(0)
    if lo == -oo:
        return hi - 1
    if hi == oo:
        return lo + 1
    return (lo + hi) / 2


def _sign_segments(fprime_expr, xsym=x):
    """Renvoie (segments, roots) où segments est une liste de (signe, lo,
    hi) triée par x croissant, obtenue en résolvant f'(x)=0 avec sympy et en
    testant le signe de f' en un point de chaque intervalle."""
    solutions = solve(sympy.Eq(fprime_expr, 0), xsym)
    roots = sorted(set(r for r in solutions if r.is_real))
    bounds = [-oo] + roots + [oo]
    segments = []
    for lo, hi in zip(bounds[:-1], bounds[1:]):
        if lo == hi:
            continue
        val = fprime_expr.subs(xsym, _test_point(lo, hi))
        val = simplify(val)
        sign = 1 if val > 0 else (-1 if val < 0 else 0)
        segments.append((sign, lo, hi))
    return segments, roots


def _variation_sentence(segments) -> str:
    words = {1: "croissante", -1: "décroissante", 0: "constante"}
    parts = [f"{words[sign]} sur ${_interval_latex(lo, hi)}$" for sign, lo, hi in segments]
    if len(parts) == 1:
        return parts[0] + "."
    return ", ".join(parts[:-1]) + ", puis " + parts[-1] + "."


def _extrema_from_segments(segments, f_expr=None, xsym=x):
    """Détecte les changements de signe entre segments consécutifs (= les
    racines intérieures de f') et classe chaque extremum (maximum si le
    signe passe de + à -, minimum si de - à +). Si `f_expr` est fourni, la
    valeur de l'extremum est calculée par substitution directe (donc exacte,
    jamais approximée)."""
    extrema = []
    for (sign_before, _, r), (sign_after, _, __) in zip(segments, segments[1:]):
        if sign_before == sign_after or sign_before == 0 or sign_after == 0:
            continue
        kind = "maximum local" if sign_before > 0 > sign_after else "minimum local"
        value = simplify(f_expr.subs(xsym, r)) if f_expr is not None else None
        extrema.append((kind, r, value))
    return extrema


@dataclass(frozen=True)
class Family:
    id: str
    level: int
    label: str
    notion: str
    build: Callable[[random.Random], Optional[dict]]
    structure_hint: str
    rule_hint: str


def _score(base_expr, bonus: float = 0.0) -> float:
    return round(deriv_gen.real_difficulty_score(base_expr) + bonus, 2)


def _bucket(score: float) -> int:
    return deriv_gen._difficulty_bucket_from_score(score)


def _make_result(*, enonce, answer, hint, steps, notion, family: "Family", score: float) -> dict:
    real_level = _bucket(score)
    return {
        "enonce": enonce,
        "answer": answer,
        "hint": hint,
        "solution_steps": steps,
        "chapter_id": CHAPTER_ID,
        "notion": notion,
        "difficulty": real_level,
        "difficulty_label": LEVEL_META[real_level]["label"],
        "difficulty_emoji": LEVEL_META[real_level]["emoji"],
        "family": family.id,
        "family_label": family.label,
        "declared_level": family.level,
        "complexity_score": score,
        "source": "generated",
    }


# ── Famille 1 — Application directe : signe de f' déjà connu ──────────────
# Reproduit fidèlement le moule le plus fréquent de la banque
# ("f'(x) = a(x-r1)(x-r2), en déduire les variations") mais avec de vraies
# racines et un vrai calcul de signe par sympy, jamais un texte recopié.

def _build_signe_connu(rng: random.Random) -> Optional[dict]:
    a = _nz(rng, -4, 4)
    r1 = rng.randint(-8, 8)
    r2 = rng.randint(-8, 8)
    if r1 == r2:
        return None
    r1, r2 = sorted((r1, r2))
    fprime = a * (x - r1) * (x - r2)
    segments, roots = _sign_segments(fprime)
    if len(roots) != 2:
        return None

    fam = FAMILIES_BY_ID["signe_connu"]
    fprime_latex = latex(fprime)
    enonce = (
        f"Soit $f$ une fonction dérivable sur $\\mathbb{{R}}$ telle que, pour tout réel $x$, "
        f"$f'(x) = {fprime_latex}$. Étudier le signe de $f'(x)$ puis en déduire les variations de $f$."
    )
    answer = "$f$ est " + _variation_sentence(segments)
    steps = [
        f"Étape 1 — $f'(x) = {fprime_latex}$ s'annule en $x={latex(roots[0])}$ et $x={latex(roots[1])}$ : "
        "ce sont les deux seules valeurs où $f'$ peut changer de signe.",
        "Étape 2 — On teste le signe de $f'$ sur chacun des trois intervalles délimités par ces racines "
        f"(en substituant une valeur test dans $f'(x) = {fprime_latex}$).",
        f"Étape 3 — On en déduit le tableau de variations : {answer}",
    ]
    return _make_result(
        enonce=enonce, answer=answer, hint=fam.rule_hint, steps=steps,
        notion=NOTION_VARIATIONS, family=fam, score=_score(fprime),
    )


# ── Famille 2 — Calcul à étapes, degré 2 ───────────────────────────────────

def _build_calcul_deg2(rng: random.Random) -> Optional[dict]:
    f_expr, _ = deriv_gen._gen_polynome_simple(rng)
    fprime = simplify(diff(f_expr, x))
    segments, roots = _sign_segments(fprime)
    if len(roots) != 1:
        return None

    fam = FAMILIES_BY_ID["calcul_deg2"]
    f_latex = latex(f_expr)
    fprime_latex = latex(fprime)
    answer = "$f$ est " + _variation_sentence(segments)
    steps = [
        f"Étape 1 — On calcule $f'(x)$ pour $f(x) = {f_latex}$ : $f'(x) = {fprime_latex}$.",
        f"Étape 2 — $f'(x) = 0$ pour $x = {latex(roots[0])}$ ($f'$ est affine, elle change de signe une seule fois).",
        "Étape 3 — On étudie le signe de $f'$ de part et d'autre de cette valeur, puis on en déduit "
        f"les variations : {answer}",
    ]
    return _make_result(
        enonce=f"Soit $f$ la fonction définie sur $\\mathbb{{R}}$ par $f(x) = {f_latex}$. "
                "1) Calculer $f'(x)$. 2) Étudier le signe de $f'(x)$. 3) En déduire les variations de $f$.",
        answer=answer, hint=fam.rule_hint, steps=steps,
        notion=NOTION_VARIATIONS, family=fam, score=_score(f_expr),
    )


# ── Famille 3 — Vrai/Faux justifié ─────────────────────────────────────────

def _build_vrai_faux(rng: random.Random) -> Optional[dict]:
    a = _nz(rng, -3, 3)
    r1 = rng.randint(-7, 7)
    r2 = rng.randint(-7, 7)
    if r1 == r2:
        return None
    r1, r2 = sorted((r1, r2))
    fprime = a * (x - r1) * (x - r2)
    segments, roots = _sign_segments(fprime)
    if len(roots) != 2:
        return None

    fam = FAMILIES_BY_ID["vrai_faux"]
    sign, lo, hi = rng.choice(segments)
    is_true = rng.random() < 0.5
    claimed_word = ("croissante" if sign > 0 else "décroissante") if is_true \
        else ("décroissante" if sign > 0 else "croissante")
    actual_word = "croissante" if sign > 0 else "décroissante"
    interval_latex = _interval_latex(lo, hi)
    fprime_latex = latex(fprime)

    enonce = (
        f"Soit $f$ une fonction dérivable sur $\\mathbb{{R}}$ telle que, pour tout réel $x$, "
        f"$f'(x) = {fprime_latex}$. Affirmation : « $f$ est {claimed_word} sur l'intervalle "
        f"${interval_latex}$ ». Cette affirmation est-elle vraie ou fausse ? Justifier."
    )
    if is_true:
        answer = f"Vrai : $f$ est bien {actual_word} sur ${interval_latex}$."
    else:
        answer = f"Faux : sur ${interval_latex}$, $f$ est en réalité {actual_word} (pas {claimed_word})."
    steps = [
        f"Étape 1 — On étudie le signe de $f'(x) = {fprime_latex}$ sur l'intervalle ${interval_latex}$ "
        "en testant une valeur de cet intervalle.",
        f"Étape 2 — Le signe obtenu est {'positif' if sign > 0 else 'négatif'}, donc $f$ y est {actual_word}.",
        f"Étape 3 — Conclusion : {answer}",
    ]
    return _make_result(
        enonce=enonce, answer=answer, hint=fam.rule_hint, steps=steps,
        notion=NOTION_VARIATIONS, family=fam, score=_score(fprime, bonus=1.0),
    )


# ── Famille 4 — Erreur à corriger ──────────────────────────────────────────

def _build_erreur_a_corriger(rng: random.Random) -> Optional[dict]:
    f_expr, _ = deriv_gen._gen_polynome_sup(rng)
    fprime = simplify(diff(f_expr, x))
    segments, roots = _sign_segments(fprime)
    if len(roots) != 2 or not all(r.is_rational for r in roots):
        return None  # racines non rationnelles : pas exploitable pédagogiquement à ce niveau
    extrema = _extrema_from_segments(segments, f_expr)
    if len(extrema) != 2:
        return None

    fam = FAMILIES_BY_ID["erreur_a_corriger"]
    f_latex = latex(f_expr)
    fprime_latex = latex(fprime)
    error_type = rng.choice(["signe_f_vs_fprime", "extremum_local_vs_global"])

    if error_type == "signe_f_vs_fprime":
        r0 = roots[0]
        val_f_at_r0 = simplify(f_expr.subs(x, r0))
        wrong_conclusion = "croissante" if val_f_at_r0 >= 0 else "décroissante"
        enonce = (
            f"Léa étudie $f(x) = {f_latex}$. Elle écrit : « $f({latex(r0)}) = {latex(val_f_at_r0)}$, "
            f"qui est {'positif' if val_f_at_r0 >= 0 else 'négatif'}, donc $f$ est {wrong_conclusion} "
            f"autour de $x={latex(r0)}$. » Le raisonnement de Léa est-il correct ? Identifier l'erreur et "
            "donner le raisonnement correct."
        )
        answer = (
            "Faux : Léa confond le signe de $f$ avec le signe de $f'$. Pour étudier les variations de $f$, "
            f"il faut étudier le signe de $f'(x) = {fprime_latex}$, pas la valeur de $f$ elle-même."
        )
        steps = [
            f"Étape 1 — Léa utilise le signe de $f({latex(r0)})$ pour conclure sur les variations : "
            "c'est l'erreur — le signe de $f$ ne donne aucune information sur le sens de variation de $f$.",
            f"Étape 2 — Le raisonnement correct calcule $f'(x) = {fprime_latex}$ puis étudie SON signe.",
            f"Étape 3 — {answer}",
        ]
    else:
        kind, r, val = extrema[0]
        other_kind = extrema[1][0]
        enonce = (
            f"Léa étudie $f(x) = {f_latex}$ et trouve un {kind} en $x={latex(r)}$, de valeur ${latex(val)}$. "
            f"Elle en conclut : « C'est donc le {kind.replace('local', 'global')} de $f$ sur $\\mathbb{{R}}$. » "
            "Le raisonnement de Léa est-il correct ? Justifier."
        )
        answer = (
            f"Faux : Léa confond extremum LOCAL et extremum GLOBAL. $f$ est un polynôme de degré 3, donc "
            f"$f$ n'est bornée ni vers $-\\infty$ ni vers $+\\infty$ (elle admet aussi un {other_kind}) : "
            "il n'existe pas de maximum ou de minimum global sur $\\mathbb{R}$ pour une telle fonction."
        )
        steps = [
            f"Étape 1 — On identifie bien un {kind} en $x={latex(r)}$ (changement de signe de $f'$) : "
            "ça, c'est correct.",
            "Étape 2 — Mais un extremum LOCAL n'est valable que sur un voisinage, pas sur $\\mathbb{R}$ tout "
            "entier : c'est l'erreur de Léa.",
            f"Étape 3 — {answer}",
        ]
    return _make_result(
        enonce=enonce, answer=answer, hint=fam.rule_hint, steps=steps,
        notion=NOTION_VARIATIONS, family=fam, score=_score(f_expr, bonus=1.5),
    )


# ── Famille 5 — Calcul à étapes, degré 3, avec extremums (abscisses/valeurs)

def _build_calcul_deg3(rng: random.Random) -> Optional[dict]:
    f_expr, _ = deriv_gen._gen_polynome_sup(rng)
    fprime = simplify(diff(f_expr, x))
    segments, roots = _sign_segments(fprime)
    if len(roots) != 2 or not all(r.is_rational for r in roots):
        return None  # racines non rationnelles : pas exploitable pédagogiquement à ce niveau
    extrema = _extrema_from_segments(segments, f_expr)
    if len(extrema) != 2:
        return None

    fam = FAMILIES_BY_ID["calcul_deg3"]
    f_latex = latex(f_expr)
    fprime_latex = latex(fprime)
    fprime_factored = sympy.factor(fprime)
    extrema_text = " ; ".join(
        f"{kind} ${latex(val)}$ en $x={latex(r)}$" for kind, r, val in extrema
    )
    steps = [
        f"Étape 1 — On calcule $f'(x)$ pour $f(x) = {f_latex}$ : $f'(x) = {fprime_latex} = {latex(fprime_factored)}$.",
        f"Étape 2 — On résout $f'(x) = 0$ : $x = {latex(roots[0])}$ ou $x = {latex(roots[1])}$.",
        "Étape 3 — On étudie le signe de $f'$ sur les trois intervalles délimités par ces deux racines.",
        f"Étape 4 — On en déduit les extremums locaux : {extrema_text}.",
    ]
    return _make_result(
        enonce=f"Soit $f$ la fonction définie sur $\\mathbb{{R}}$ par $f(x) = {f_latex}$. "
                "1) Calculer $f'(x)$ et la factoriser. 2) Étudier le signe de $f'(x)$ et en déduire les "
                "extremums locaux de $f$ (abscisses et valeurs).",
        answer=extrema_text, hint=fam.rule_hint, steps=steps,
        notion=NOTION_EXTREMUMS, family=fam, score=_score(f_expr),
    )


# ── Famille 6 — Problème inversé : retrouver un coefficient ───────────────

def _build_extremum_inverse(rng: random.Random) -> Optional[dict]:
    x0 = rng.choice([n for n in range(-6, 7) if n != 0])
    q = rng.randint(-5, 5)
    p = symbols("p")
    f_expr = x**3 + p * x + q
    fprime = diff(f_expr, x)
    solutions = solve(sympy.Eq(fprime.subs(x, x0), 0), p)
    if not solutions:
        return None
    p_value = solutions[0]
    if p_value == 0:
        return None
    f_final = f_expr.subs(p, p_value)
    fprime_final = simplify(diff(f_final, x))

    fam = FAMILIES_BY_ID["extremum_inverse"]
    f_latex = latex(x**3 + p * x + q)
    enonce = (
        f"Soit $f$ la fonction définie sur $\\mathbb{{R}}$ par $f(x) = {f_latex}$, où $p$ est un réel "
        f"inconnu. Sachant que $f$ admet un extremum local en $x = {x0}$, déterminer la valeur de $p$."
    )
    answer = f"$p = {latex(p_value)}$"
    steps = [
        f"Étape 1 — On calcule $f'(x) = {latex(fprime)}$ (en fonction du paramètre $p$).",
        f"Étape 2 — Un extremum local en $x={x0}$ impose $f'({x0}) = 0$ (condition nécessaire).",
        f"Étape 3 — On résout $f'({x0}) = 0$ en $p$ : {answer}.",
        f"Étape 4 — Vérification : avec cette valeur, $f'(x) = {latex(fprime_final)}$, qui change bien de "
        f"signe en $x={x0}$, donc il s'agit bien d'un extremum local.",
    ]
    return _make_result(
        enonce=enonce, answer=answer, hint=fam.rule_hint, steps=steps,
        notion=NOTION_EXTREMUMS, family=fam, score=_score(f_final, bonus=4.5),
    )


# ── Famille 7 — Interprétation contextualisée d'un extremum ───────────────

_CONTEXTS = [
    {"nom": "coût de production", "symbole": "C", "unite": "en milliers d'euros",
     "variable": "la quantité produite, en centaines d'unités", "sens_min": True,
     "phrase": "le coût de production est minimal"},
    {"nom": "bénéfice réalisé", "symbole": "B", "unite": "en milliers d'euros",
     "variable": "la quantité vendue, en centaines d'unités", "sens_min": False,
     "phrase": "le bénéfice réalisé est maximal"},
    {"nom": "aire d'un enclos rectangulaire de périmètre fixé", "symbole": "A", "unite": "en m²",
     "variable": "la longueur d'un côté de l'enclos, en mètres", "sens_min": False,
     "phrase": "l'aire de l'enclos est maximale"},
]


def _build_interpretation(rng: random.Random) -> Optional[dict]:
    ctx = rng.choice(_CONTEXTS)
    a = _nz(rng, 1, 5)
    if not ctx["sens_min"]:
        a = -a  # concave (bénéfice/aire max) vs convexe (coût min)
    b = rng.randint(-20, 20)
    c = rng.randint(0, 30)
    f_expr = a * x**2 + b * x + c
    fprime = simplify(diff(f_expr, x))
    segments, roots = _sign_segments(fprime)
    if len(roots) != 1:
        return None
    x0 = roots[0]
    if x0 <= 0:
        return None
    value = simplify(f_expr.subs(x, x0))

    fam = FAMILIES_BY_ID["interpretation"]
    f_latex = latex(f_expr)
    answer = (
        f"${ctx['symbole']}$ atteint un extremum ({'minimum' if ctx['sens_min'] else 'maximum'}) en "
        f"$x = {latex(x0)}$, de valeur ${latex(value)}$ {ctx['unite']} : concrètement, {ctx['phrase']} "
        f"lorsque {ctx['variable']} vaut ${latex(x0)}$."
    )
    steps = [
        f"Étape 1 — On calcule ${ctx['symbole']}'(x) = {latex(fprime)}$.",
        f"Étape 2 — $f'$ s'annule et change de signe en $x = {latex(x0)}$ : c'est là que se situe l'extremum.",
        f"Étape 3 — On calcule la valeur associée : ${ctx['symbole']}({latex(x0)}) = {latex(value)}$.",
        f"Étape 4 — Interprétation dans le contexte : {answer}",
    ]
    return _make_result(
        enonce=(
            f"Un responsable modélise {ctx['nom']} par ${ctx['symbole']}(x) = {f_latex}$ {ctx['unite']}, où "
            f"$x$ désigne {ctx['variable']}. 1) Étudier les variations de ${ctx['symbole']}$. "
            f"2) Interpréter concrètement le résultat obtenu en $x = {latex(x0)}$."
        ),
        answer=answer, hint=fam.rule_hint, steps=steps,
        notion=NOTION_EXTREMUMS, family=fam, score=_score(f_expr, bonus=1.0),
    )


# ── Famille 8 — Optimisation contextualisée (degré 3) ──────────────────────

def _build_optimisation(rng: random.Random) -> Optional[dict]:
    L = rng.randint(6, 40)
    V_expr = x * (L - 2 * x) ** 2
    Vprime = sympy.factor(simplify(diff(V_expr, x)))
    domain_lo, domain_hi = S(0), Rational(L, 2)
    solutions = [r for r in solve(sympy.Eq(Vprime, 0), x) if r.is_real and domain_lo < r < domain_hi]
    if len(solutions) != 1:
        return None
    x0 = solutions[0]
    v_max = simplify(V_expr.subs(x, x0))

    fam = FAMILIES_BY_ID["optimisation"]
    v_latex = latex(V_expr)
    interval_latex = _interval_latex(domain_lo, domain_hi)
    answer = f"Le volume est maximal pour $x = {latex(x0)}$ cm, et vaut alors $V({latex(x0)}) = {latex(v_max)}$ cm³."
    steps = [
        f"Étape 1 — On modélise le volume : $V(x) = {v_latex}$ pour $x \\in {interval_latex}$.",
        f"Étape 2 — On calcule $V'(x) = {latex(Vprime)}$ (forme factorisée).",
        f"Étape 3 — Sur ${interval_latex}$, $V'(x) = 0$ pour $x = {latex(x0)}$ (l'autre racine "
        f"$x = {latex(Rational(L, 2))}$ est exclue du domaine).",
        f"Étape 4 — Étude du signe de $V'$ : $V$ est croissante puis décroissante, donc $V$ admet un maximum "
        f"en $x = {latex(x0)}$. Conclusion : {answer}",
    ]
    return _make_result(
        enonce=(
            f"On souhaite fabriquer une boîte sans couvercle à partir d'une feuille de carton carrée de "
            f"côté {L} cm, en découpant un carré de côté $x$ dans chaque coin puis en repliant les bords. "
            f"Le volume de la boîte obtenue est $V(x) = {v_latex}$ pour $x \\in {interval_latex}$. Étudier "
            "les variations de $V$ et déterminer la valeur de $x$ qui maximise le volume, ainsi que ce "
            "volume maximal."
        ),
        answer=answer, hint=fam.rule_hint, steps=steps,
        notion=NOTION_EXTREMUMS, family=fam, score=_score(V_expr, bonus=5.0),
    )


# ── Famille 9 — Variations d'une fonction homographique ────────────────────
# Audit calcul-diversité Première : "Variations d'une fonction" était
# exclusivement polynomiale (signe_connu/calcul_deg2/vrai_faux/erreur), alors
# que le programme de Première introduit aussi les fonctions homographiques
# (ax+b)/(cx+d), dont l'étude des variations est structurellement différente
# (domaine à trous, signe de f' CONSTANT sur chaque intervalle car le
# dénominateur est un carré — pas de racine à résoudre).

def _build_variations_homographique(rng: random.Random) -> Optional[dict]:
    c = _nz(rng, -4, 4)
    d = rng.randint(-6, 6)
    a = _nz(rng, -4, 4)
    b = rng.randint(-6, 6)
    delta = a * d - b * c
    if delta == 0:
        return None
    f_expr = (a * x + b) / (c * x + d)
    fprime = simplify(diff(f_expr, x))
    pole = sympy.nsimplify(Rational(-d, c))
    sens = "croissante" if delta > 0 else "décroissante"

    fam = FAMILIES_BY_ID["variations_homographique"]
    f_latex = f"\\dfrac{{{latex(a * x + b)}}}{{{latex(c * x + d)}}}"
    domaine_latex = f"\\mathbb{{R}} \\setminus \\left\\{{{latex(pole)}\\right\\}}"
    answer = (
        f"$f$ est {sens} sur chacun des deux intervalles $]-\\infty;{latex(pole)}[$ et "
        f"$]{latex(pole)};+\\infty[$ qui composent son domaine (mais $f$ n'est pas monotone "
        "sur $D_f$ tout entier, puisqu'elle n'y est pas définie en un point)."
    )
    steps = [
        f"Étape 1 — Le dénominateur s'annule en $x={latex(pole)}$, donc $D_f = {domaine_latex}$.",
        f"Étape 2 — Par la règle du quotient, $f'(x) = {latex(fprime)}$ : le numérateur "
        f"(${latex(delta)}$) est une constante non nulle, et le dénominateur est un carré, "
        "donc toujours strictement positif sur $D_f$.",
        f"Étape 3 — Le signe de $f'$ est donc constant sur $D_f$ : {answer}",
    ]
    return _make_result(
        enonce=(
            f"Soit $f$ la fonction homographique définie par $f(x) = {f_latex}$ sur son "
            "ensemble de définition. Déterminer $D_f$, calculer $f'(x)$, puis en déduire "
            "les variations de $f$."
        ),
        answer=answer, hint=fam.rule_hint, steps=steps,
        notion=NOTION_VARIATIONS, family=fam, score=_score(f_expr, bonus=2.0),
    )


# ── Famille 10 — Variations d'une fonction racine carrée ───────────────────

def _build_variations_racine(rng: random.Random) -> Optional[dict]:
    a = _nz(rng, -4, 4)
    b = rng.randint(-6, 6)
    f_expr = sympy.sqrt(a * x + b)
    fprime = simplify(diff(f_expr, x))
    pole = sympy.nsimplify(Rational(-b, a))
    if a > 0:
        domaine_latex = f"\\left[{latex(pole)};+\\infty\\right["
        sens = "croissante"
    else:
        domaine_latex = f"\\left]-\\infty;{latex(pole)}\\right]"
        sens = "décroissante"

    fam = FAMILIES_BY_ID["variations_racine"]
    f_latex = f"\\sqrt{{{latex(a * x + b)}}}"
    answer = f"$f$ est {sens} sur $D_f = {domaine_latex}$."
    steps = [
        f"Étape 1 — Une racine carrée n'est définie que si son contenu est positif ou nul : "
        f"$D_f = {domaine_latex}$.",
        f"Étape 2 — $f'(x) = {latex(fprime)}$, qui garde un signe constant sur $D_f$ (le "
        f"numérateur ${a}$ ne change pas de signe, et le dénominateur $2\\sqrt{{{latex(a * x + b)}}}$ "
        "est toujours positif sur ce domaine).",
        f"Étape 3 — Donc {answer}",
    ]
    return _make_result(
        enonce=(
            f"Soit $f$ la fonction définie par $f(x) = {f_latex}$ sur son ensemble de "
            "définition. Déterminer $D_f$, calculer $f'(x)$, puis en déduire les variations de $f$."
        ),
        answer=answer, hint=fam.rule_hint, steps=steps,
        notion=NOTION_VARIATIONS, family=fam, score=_score(f_expr, bonus=1.5),
    )


# ── Famille 11 — Optimisation à quotient (coût moyen a·x + b/x) ────────────
# Audit calcul-diversité Première : "Nombre dérivé et extremums locaux" ne
# proposait qu'une optimisation polynomiale (boîte sans couvercle). Le coût
# moyen a·x + b/x est l'archétype du problème d'optimisation à quotient du
# programme de Première (dérivée a - b/x², minimum en x=√(b/a)) — on choisit
# b = a·k² pour garantir une solution entière propre (k), exploitable par un
# élève sans calculatrice.

def _build_optimisation_quotient(rng: random.Random) -> Optional[dict]:
    a = _nz(rng, 1, 4)
    k = rng.randint(2, 6)
    b = a * k * k
    C_expr = a * x + Rational(b, 1) / x
    Cprime = simplify(diff(C_expr, x))
    c_min = simplify(C_expr.subs(x, k))

    fam = FAMILIES_BY_ID["optimisation_quotient"]
    c_latex = latex(C_expr)
    answer = f"Le coût moyen est minimal pour $x = {k}$, et vaut alors $C({k}) = {latex(c_min)}$."
    steps = [
        f"Étape 1 — On modélise le coût moyen par unité : $C(x) = {c_latex}$ pour $x>0$.",
        f"Étape 2 — $C'(x) = {latex(Cprime)}$ (dérivée d'une somme d'un terme affine et d'un "
        "terme en $1/x$).",
        f"Étape 3 — $C'(x)=0$ pour $x={k}$ (seule solution positive) ; $C'$ est négative avant, "
        "positive après, donc $C$ admet un minimum en ce point.",
        f"Étape 4 — Conclusion : {answer}",
    ]
    return _make_result(
        enonce=(
            f"Le coût moyen de production d'un objet, en fonction de la quantité $x>0$ produite "
            f"(en centaines d'unités), est modélisé par $C(x) = {c_latex}$ (en euros). Étudier "
            "les variations de $C$ sur $]0;+\\infty[$ et déterminer la quantité $x$ qui minimise "
            "le coût moyen, ainsi que ce coût minimal."
        ),
        answer=answer, hint=fam.rule_hint, steps=steps,
        notion=NOTION_EXTREMUMS, family=fam, score=_score(C_expr, bonus=7.5),
    )


FAMILIES: tuple[Family, ...] = (
    Family("signe_connu", 2, "Signe de f' déjà connu (application directe)", NOTION_VARIATIONS,
           _build_signe_connu, "un signe de dérivée déjà factorisé",
           "lire le signe de chaque facteur, puis appliquer la règle des signes"),
    Family("calcul_deg2", 2, "Calcul à étapes — polynôme de degré 2", NOTION_VARIATIONS,
           _build_calcul_deg2, "un polynôme du second degré dont il faut calculer la dérivée",
           "dériver, résoudre $f'(x)=0$, puis étudier le signe de $f'$"),
    Family("vrai_faux", 2, "Vrai/Faux justifié", NOTION_VARIATIONS,
           _build_vrai_faux, "une affirmation sur le sens de variation à vérifier",
           "étudier le signe de $f'$ sur l'intervalle donné avant de conclure"),
    Family("erreur_a_corriger", 3, "Erreur à corriger", NOTION_VARIATIONS,
           _build_erreur_a_corriger, "un raisonnement fautif à identifier",
           "ne jamais confondre le signe de $f$ avec le signe de $f'$, ni un extremum local et global"),
    Family("calcul_deg3", 3, "Calcul à étapes — polynôme de degré 3, extremums", NOTION_EXTREMUMS,
           _build_calcul_deg3, "un polynôme de degré 3 dont il faut calculer la dérivée et les extremums",
           "dériver, factoriser, résoudre $f'(x)=0$, puis étudier le changement de signe"),
    Family("extremum_inverse", 4, "Problème inversé — retrouver un coefficient", NOTION_EXTREMUMS,
           _build_extremum_inverse, "un coefficient inconnu à retrouver à partir d'un extremum donné",
           "poser $f'(x_0)=0$ (condition nécessaire d'extremum) puis résoudre en l'inconnue"),
    Family("interpretation", 3, "Interprétation contextualisée", NOTION_EXTREMUMS,
           _build_interpretation, "un extremum à interpréter dans un contexte concret",
           "relier l'extremum mathématique (abscisse et valeur) à sa signification dans le contexte"),
    Family("optimisation", 5, "Problème d'optimisation contextualisé", NOTION_EXTREMUMS,
           _build_optimisation, "un problème d'optimisation sous contrainte de domaine",
           "modéliser, dériver, résoudre $f'(x)=0$ sur le domaine pertinent, puis conclure"),
    Family("variations_homographique", 3, "Variations d'une fonction homographique", NOTION_VARIATIONS,
           _build_variations_homographique, "une fonction (ax+b)/(cx+d) à étudier",
           "déterminer le domaine (dénominateur non nul), puis dériver par la règle du quotient : le signe de f' est constant sur chaque intervalle"),
    Family("variations_racine", 2, "Variations d'une fonction racine carrée", NOTION_VARIATIONS,
           _build_variations_racine, "une racine carrée d'une expression affine à étudier",
           "déterminer le domaine (contenu de la racine positif ou nul), puis dériver : le signe de f' est constant sur ce domaine"),
    Family("optimisation_quotient", 5, "Optimisation à quotient (coût moyen)", NOTION_EXTREMUMS,
           _build_optimisation_quotient, "un coût moyen modélisé par a·x + b/x",
           "dériver une somme affine + 1/x, résoudre f'(x)=0 sur x>0, puis conclure sur le minimum"),
)

FAMILIES_BY_ID: dict[str, Family] = {f.id: f for f in FAMILIES}
FAMILIES_BY_LEVEL: dict[int, tuple[Family, ...]] = {
    level: tuple(f for f in FAMILIES if f.level == level) for level in range(1, 6)
}


def build_exercise(family: Family, rng: random.Random) -> Optional[dict]:
    """Construit un exercice complet à partir d'une famille. Renvoie None si
    le tirage dégénère (racines confondues, extremum hors domaine...) —
    l'appelant retire alors simplement une nouvelle graine."""
    return family.build(rng)


def generate_one(family_id: str, seed: Optional[int] = None, max_attempts: int = 40) -> dict:
    rng = random.Random(seed)
    fam = FAMILIES_BY_ID[family_id]
    for _ in range(max_attempts):
        ex = build_exercise(fam, rng)
        if ex is not None:
            return ex
    raise RuntimeError(f"Impossible de générer un exercice valide pour la famille {family_id!r}")


def generate_pool(per_family: int = 12, seed: int = 20260819) -> list[dict]:
    """Génère un pool diversifié : `per_family` exercices distincts par
    famille (8 familles), dédupliqués par signature d'énoncé, en alternant
    les familles (round-robin) pour qu'un pool consommé dans l'ordre
    n'enchaîne jamais deux exercices de la même famille."""
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
        if idx > 100000:
            break
    for i, ex in enumerate(pool):
        ex["id"] = GENERATED_ID_OFFSET + i
    return pool
