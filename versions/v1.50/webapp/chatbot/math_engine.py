"""
Moteur de calcul mathématique indépendant du LLM (sympy). Le modèle IA
n'effectue jamais un calcul simple : ce module détecte les demandes de calcul
(simplifier une fraction, résoudre une équation, développer/factoriser une
expression, calculer un pourcentage, simplifier une racine...), calcule le
résultat de façon fiable et déterministe, et renvoie une explication complète
déjà formatée (LaTeX entre $...$, rendu ensuite par KaTeX côté frontend) —
sans jamais appeler le fournisseur IA pour ce type de demande.

Conçu pour être appelé tôt dans la chaîne (voir conversation_manager.py),
juste après le Rule Engine (salutations/identité) et avant le Knowledge
Engine / l'appel LLM : si try_solve() renvoie une chaîne, elle est utilisée
telle quelle comme réponse finale.
"""
import re
import unicodedata

import sympy
from sympy import (
    Eq, Rational, Symbol, expand, factor, latex, nsimplify, simplify, solve, sqrt, sympify,
)
from sympy.parsing.sympy_parser import (
    parse_expr, standard_transformations, implicit_multiplication_application, convert_xor,
)

TRANSFORMATIONS = standard_transformations + (implicit_multiplication_application, convert_xor)

X = Symbol("x")

def _ascii_fold(text):
    """Retire les accents (é -> e, à -> a...) en conservant un texte de même
    longueur pour les lettres accentuées françaises courantes : permet de
    faire correspondre les motifs déclencheurs ci-dessous que l'utilisateur
    ait tapé "résous" ou "resous" (accents omis, très fréquent en saisie
    rapide), tout en réutilisant ensuite les positions (span) trouvées pour
    extraire le contenu depuis le texte ORIGINAL (pas la version aplatie)."""
    return "".join(
        c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c)
    )


# Verbes déclencheurs (français, sans accent : voir _ascii_fold — le texte est
# aplati avant correspondance) associés à chaque type de calcul. Une demande
# qui ne correspond à aucun motif retombe sur le Knowledge Engine / le LLM
# (voir conversation_manager.py).
SOLVE_RE = re.compile(r"\b(resous|resoudre|resolution)\b.*?([^.?!]*=[^.?!]*)", re.IGNORECASE)
SIMPLIFY_FRACTION_RE = re.compile(r"\b(simplifie|simplifier)\b.*?(-?\d+)\s*/\s*(-?\d+)", re.IGNORECASE)
SIMPLIFY_SQRT_RE = re.compile(r"\b(simplifie|simplifier)\b.*?√\s*\{?(\d+)\}?|\\sqrt\{?(\d+)\}?", re.IGNORECASE)
EXPAND_RE = re.compile(r"\b(developpe|developper|developpement)\b\s*(?:de\s*)?([^.?!]+)", re.IGNORECASE)
FACTOR_RE = re.compile(r"\b(factorise|factoriser|factorisation)\b\s*(?:de\s*)?([^.?!]+)", re.IGNORECASE)
PERCENT_OF_RE = re.compile(r"(-?\d+(?:[.,]\d+)?)\s*%\s*de\s*(-?\d+(?:[.,]\d+)?)", re.IGNORECASE)
PERCENT_EVOLUTION_RE = re.compile(
    r"(-?\d+(?:[.,]\d+)?)\s*(?:augmente?e?|majore?e?)\s*de\s*(-?\d+(?:[.,]\d+)?)\s*%", re.IGNORECASE
)
CALCULATE_RE = re.compile(r"\b(calcule|calculer|evalue|evaluer)\b\s*(?:le resultat de\s*)?([^.?!]+)", re.IGNORECASE)


def _fr_number(s):
    return s.replace(",", ".")


_SUP_MAP = {"⁰": "0", "¹": "1", "²": "2", "³": "3", "⁴": "4", "⁵": "5",
            "⁶": "6", "⁷": "7", "⁸": "8", "⁹": "9", "⁻": "-"}
_SUP_CHARS = "".join(_SUP_MAP)


def _normalize_expr_text(text):
    """Convertit une expression écrite en notation mathématique courante
    (×, ÷, ², ³, √, exposants Unicode...) en syntaxe compatible sympy."""
    cleaned = text.strip()
    cleaned = cleaned.replace("×", "*").replace("÷", "/").replace("−", "-")
    cleaned = cleaned.replace("√", "sqrt")

    def _sup_repl(m):
        digits = "".join(_SUP_MAP[c] for c in m.group(2))
        return f"{m.group(1)}^({digits})"

    cleaned = re.sub(rf"([A-Za-z0-9\)])([{re.escape(_SUP_CHARS)}]+)", _sup_repl, cleaned)
    return _fr_number(cleaned)


def _to_sympy_expr(text, evaluate=True):
    """Renvoie l'expression sympy correspondante, ou None si le texte ne
    ressemble pas à une expression exploitable."""
    if not text:
        return None
    cleaned = _normalize_expr_text(text)
    try:
        return parse_expr(cleaned, transformations=TRANSFORMATIONS, local_dict={"x": X}, evaluate=evaluate)
    except (SyntaxError, TypeError, ValueError, sympy.SympifyError):
        return None


def _fmt(expr):
    """Représentation LaTeX inline, prête à insérer dans un message ($...$)."""
    return f"${latex(expr)}$"


def _solve_equation(equation_text):
    if "=" not in equation_text:
        return None
    left, right = equation_text.split("=", 1)
    left_expr, right_expr = _to_sympy_expr(left), _to_sympy_expr(right)
    if left_expr is None or right_expr is None:
        return None
    eq = Eq(left_expr, right_expr)
    free_symbols = eq.free_symbols
    if not free_symbols:
        return None
    symbol = sorted(free_symbols, key=str)[0]
    try:
        solutions = solve(eq, symbol)
    except (NotImplementedError, sympy.SympifyError):
        return None
    if not solutions:
        return (
            f"**Résolution de** {_fmt(eq)} :\n\n"
            f"Cette équation n'a pas de solution réelle."
        )
    sol_str = ", ".join(_fmt(Eq(symbol, s)) for s in solutions)
    degree = sympy.degree(sympy.Poly(left_expr - right_expr, symbol)) if left_expr.is_polynomial(symbol) else None
    method = {
        1: "C'est une équation du premier degré : on isole l'inconnue en faisant les mêmes opérations des deux côtés.",
        2: "C'est une équation du second degré : on la résout avec le discriminant (ou une factorisation si possible).",
    }.get(degree, "On isole l'inconnue étape par étape.")
    return (
        f"**Résolution de** {_fmt(eq)} :\n\n"
        f"{method}\n\n"
        f"**Solution{'s' if len(solutions) > 1 else ''} :** {sol_str}"
    )


def _simplify_fraction(num, den):
    try:
        num_i, den_i = int(num), int(den)
    except ValueError:
        return None
    if den_i == 0:
        return "Division par zéro impossible : le dénominateur ne peut pas être 0."
    frac_simplified = Rational(num_i, den_i)
    if frac_simplified.q == 1:
        return f"**Simplification de** ${num}/{den}$ :\n\n${num}/{den} = {frac_simplified.p}$ (c'est un nombre entier)."
    return (
        f"**Simplification de** ${num}/{den}$ :\n\n"
        f"On divise le numérateur et le dénominateur par leur PGCD.\n\n"
        f"**Résultat :** ${frac_simplified.p}/{frac_simplified.q}$"
    )


def _simplify_sqrt(n):
    try:
        n = int(n)
    except ValueError:
        return None
    if n < 0:
        return f"√{n} n'existe pas dans les nombres réels (racine d'un nombre négatif)."
    result = sqrt(n)
    simplified = sympy.simplify(result)
    if simplified.is_Integer:
        return f"**Simplification de** $\\sqrt{{{n}}}$ :\n\n$\\sqrt{{{n}}} = {simplified}$ (c'est un carré parfait)."
    # Extraction du plus grand carré parfait
    for k in range(int(n**0.5), 1, -1):
        if n % (k * k) == 0:
            rest = n // (k * k)
            return (
                f"**Simplification de** $\\sqrt{{{n}}}$ :\n\n"
                f"On cherche le plus grand carré parfait qui divise {n} : ${k}^2 = {k*k}$, et ${n}/{k*k} = {rest}$.\n\n"
                f"**Résultat :** $\\sqrt{{{n}}} = {k}\\sqrt{{{rest}}}$"
            )
    return f"**Résultat :** $\\sqrt{{{n}}}$ ne se simplifie pas (aucun carré parfait ne le divise)."


def _expand_expr(text):
    expr = _to_sympy_expr(text)
    if expr is None:
        return None
    result = expand(expr)
    return f"**Développement de** {_fmt(expr)} :\n\n**Résultat :** {_fmt(result)}"


def _factor_expr(text):
    expr = _to_sympy_expr(text)
    if expr is None:
        return None
    result = factor(expr)
    if result == expr:
        return f"**Factorisation de** {_fmt(expr)} :\n\nCette expression ne se factorise pas davantage avec des coefficients simples."
    return f"**Factorisation de** {_fmt(expr)} :\n\n**Résultat :** {_fmt(result)}"


def _percent_of(pct, base):
    try:
        pct_v, base_v = float(_fr_number(pct)), float(_fr_number(base))
    except ValueError:
        return None
    result = pct_v * base_v / 100
    result_str = f"{result:g}"
    return (
        f"**Calcul de {pct_v:g}% de {base_v:g}** :\n\n"
        f"${pct_v:g}\\% \\times {base_v:g} = \\dfrac{{{pct_v:g}}}{{100}} \\times {base_v:g} = {result_str}$"
    )


def _percent_evolution(base, pct):
    try:
        base_v, pct_v = float(_fr_number(base)), float(_fr_number(pct))
    except ValueError:
        return None
    result = base_v * (1 + pct_v / 100)
    return (
        f"**{base_v:g} augmenté de {pct_v:g}%** :\n\n"
        f"On multiplie par le coefficient multiplicateur $1 + \\dfrac{{{pct_v:g}}}{{100}} = {1 + pct_v/100:g}$.\n\n"
        f"**Résultat :** ${base_v:g} \\times {1 + pct_v/100:g} = {result:g}$"
    )


def _calculate(text):
    expr = _to_sympy_expr(text)
    if expr is None or expr.free_symbols:
        return None
    # Affichage : le texte d'origine tel quel (KaTeX affiche très bien ×, ÷,
    # √ comme caractères littéraux en mode math) — plus fiable qu'un
    # aller-retour par sympy, dont l'évaluation "eager" des exposants
    # négatifs littéraux peut déformer l'expression même avec evaluate=False.
    display_text = text.strip()
    display_text = re.sub(r"\^(-?\d+)", r"^{\1}", display_text)  # LaTeX exige des accolades autour d'un exposant signé
    display_text = display_text.replace("*", " \\times ")
    try:
        result = sympy.nsimplify(expr)
        exact = sympy.simplify(result)
    except (sympy.SympifyError, TypeError):
        return None
    numeric = sympy.N(exact, 10)
    if exact == numeric or exact.is_Integer or exact.is_Rational:
        return f"**Calcul de** ${display_text}$ :\n\n**Résultat :** {_fmt(exact)}"
    return f"**Calcul de** ${display_text}$ :\n\n**Résultat exact :** {_fmt(exact)} ≈ {round(float(numeric), 4)}"


def try_solve(user_message):
    """Point d'entrée unique. Renvoie une réponse Markdown/LaTeX déjà
    formatée si la demande est un calcul reconnu, sinon None (le pipeline
    continue vers le Knowledge Engine puis, en dernier recours, le LLM)."""
    text = (user_message or "").strip()
    if not text:
        return None
    # Recherche sur le texte sans accents (voir _ascii_fold), mais extraction
    # du contenu (équation, expression...) depuis le texte ORIGINAL via les
    # positions (span) du match — préserve les accents éventuels du contenu
    # mathématique lui-même tout en tolérant "resous"/"résous" indifféremment.
    folded = _ascii_fold(text)

    def _group_from_original(match, idx):
        start, end = match.span(idx)
        return text[start:end]

    m = PERCENT_OF_RE.search(folded)
    if m:
        result = _percent_of(_group_from_original(m, 1), _group_from_original(m, 2))
        if result:
            return result

    m = PERCENT_EVOLUTION_RE.search(folded)
    if m:
        result = _percent_evolution(_group_from_original(m, 1), _group_from_original(m, 2))
        if result:
            return result

    m = SIMPLIFY_FRACTION_RE.search(folded)
    if m:
        result = _simplify_fraction(_group_from_original(m, 2), _group_from_original(m, 3))
        if result:
            return result

    m = SIMPLIFY_SQRT_RE.search(folded)
    if m:
        n = _group_from_original(m, 2) if m.group(2) else _group_from_original(m, 3)
        result = _simplify_sqrt(n)
        if result:
            return result

    m = SOLVE_RE.search(folded)
    if m:
        result = _solve_equation(_group_from_original(m, 2))
        if result:
            return result

    m = EXPAND_RE.search(folded)
    if m:
        result = _expand_expr(_group_from_original(m, 2))
        if result:
            return result

    m = FACTOR_RE.search(folded)
    if m:
        result = _factor_expr(_group_from_original(m, 2))
        if result:
            return result

    m = CALCULATE_RE.search(folded)
    if m:
        result = _calculate(_group_from_original(m, 2))
        if result:
            return result

    return None
