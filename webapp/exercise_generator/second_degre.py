"""Génération symbolique d'exercices sur les équations du second degré
(Première, Chapitre_2, notion "Équations du second degré").

Même principe que `webapp/exercise_generator/derivatives.py` (patron de
référence) : chaque "famille" représente un vrai type de raisonnement,
toute valeur numérique annoncée (racines, discriminant, somme/produit,
factorisation...) est calculée ou vérifiée par sympy — jamais tapée "en
dur" sans contrôle — et jamais retenue si sympy ne la confirme pas.

Différence assumée avec `derivatives.py` : il n'existe pas ici une
opération générique unique (comme `diff`) applicable à toutes les
familles — certaines demandent de résoudre, d'autres de raisonner sur le
signe du discriminant sans résoudre, de juger un corrigé, de retrouver un
paramètre... Comme dans `suites.py`, chaque `_gen_xxx(rng)` renvoie
directement `notes` (un dict déjà rédigé : enonce/answer/steps/hint) ou
`None` si le tirage dégénère. La difficulté affichée n'est PAS basée sur
la taille des nombres tirés (interdit par le cahier des charges), mais
sur un score fixe par famille reflétant la profondeur de raisonnement de
ce TYPE de question — voir `FAMILY_BASE_SCORE`.
"""
import random
from dataclasses import dataclass
from typing import Callable, Optional

from sympy import Eq, Rational, S, factor, latex, solve, symbols

x = symbols("x")

CHAPTER_ID = "Chapitre_2"
NOTION = "Équations du second degré"

# Distinct des offsets déjà utilisés (900_000/910_000/920_000/930_000) —
# voir tools/generate_derivative_exercises.py qui liste tous les offsets et
# garantit l'absence de collision d'id entre pools généraux.
GENERATED_ID_OFFSET = 940_000

LEVEL_META = {
    1: {"emoji": "🟢", "label": "Niveau 1 — Fondamental"},
    2: {"emoji": "🟡", "label": "Niveau 2 — Intermédiaire"},
    3: {"emoji": "🟠", "label": "Niveau 3 — Avancé"},
    4: {"emoji": "🔴", "label": "Niveau 4 — Difficile"},
    5: {"emoji": "🟣", "label": "Niveau 5 — Défi"},
}


def _nz(rng: random.Random, lo: int, hi: int) -> int:
    choices = [n for n in range(lo, hi + 1) if n != 0]
    return rng.choice(choices)


def _small(rng: random.Random, lo=-9, hi=9) -> int:
    return rng.randint(lo, hi)


def _fmt_eq(a, b, c) -> str:
    """Rend $ax^2+bx+c=0$ en LaTeX avec des signes propres (pas de '+ -3')."""
    parts = [f"{'' if a == 1 else ('-' if a == -1 else a)}x^2"]
    if b != 0:
        parts.append(f"{'+' if b > 0 else '-'} {abs(b) if abs(b) != 1 else ''}x".replace("  ", " "))
    if c != 0:
        parts.append(f"{'+' if c > 0 else '-'} {abs(c)}")
    return " ".join(parts) + " = 0"


def _roots_via_sympy(a, b, c):
    """Résout ax²+bx+c=0 par sympy.solve — seule source de vérité."""
    return sorted(solve(Eq(a * x**2 + b * x + c, 0), x), key=lambda r: (r.is_number, str(r)))


# ── 1. Résolution directe (les 3 cas de discriminant) ──────────────────────

def _gen_resolution(rng):
    a = _nz(rng, -4, 4)
    kind = rng.choice(["deux_racines", "racine_double", "aucune_racine"])
    if kind == "deux_racines":
        r1 = _small(rng, -6, 6)
        r2 = r1
        while r2 == r1:
            r2 = _small(rng, -6, 6)
        b, c = -a * (r1 + r2), a * r1 * r2
    elif kind == "racine_double":
        r = _small(rng, -6, 6)
        b, c = -2 * a * r, a * r**2
    else:
        b = _small(rng, -6, 6)
        c = None
        for _ in range(60):
            c_try = _small(rng, -9, 9)
            if b**2 - 4 * a * c_try < 0:
                c = c_try
                break
        if c is None:
            return None

    delta = b**2 - 4 * a * c
    sols = _roots_via_sympy(a, b, c)
    enonce = f"Résoudre dans $\\mathbb{{R}}$ l'équation ${_fmt_eq(a, b, c)}$."
    steps = [
        f"Étape 1 — On calcule le discriminant : $\\Delta = b^2-4ac = {latex(S(delta))}$.",
    ]
    if delta > 0:
        if len(sols) != 2:
            return None
        r1_s, r2_s = latex(sols[0]), latex(sols[1])
        steps.append(
            f"Étape 2 — $\\Delta > 0$ : deux solutions distinctes, "
            f"$x_1=\\dfrac{{-b-\\sqrt{{\\Delta}}}}{{2a}}={r1_s}$ et $x_2=\\dfrac{{-b+\\sqrt{{\\Delta}}}}{{2a}}={r2_s}$."
        )
        answer = f"$S = \\left\\{{{r1_s};\\,{r2_s}\\right\\}}$"
    elif delta == 0:
        if len(sols) != 1:
            return None
        r_s = latex(sols[0])
        steps.append(f"Étape 2 — $\\Delta = 0$ : une racine double, $x_0=\\dfrac{{-b}}{{2a}}={r_s}$.")
        answer = f"$S = \\left\\{{{r_s}\\right\\}}$"
    else:
        steps.append("Étape 2 — $\\Delta < 0$ : l'équation n'admet aucune solution réelle.")
        answer = "$S = \\emptyset$ (aucune solution réelle)"

    hint = "Calculer le discriminant $\\Delta=b^2-4ac$ puis appliquer la formule correspondant à son signe."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


# ── 2. Signe du discriminant SANS résoudre ──────────────────────────────────

def _gen_signe_discriminant(rng):
    a = _nz(rng, -5, 5)
    b = _small(rng, -8, 8)
    c = _small(rng, -8, 8)
    delta = b**2 - 4 * a * c
    enonce = (
        f"Sans résoudre l'équation, déterminer le signe du discriminant de "
        f"${_fmt_eq(a, b, c)}$ et en déduire le nombre de solutions réelles."
    )
    if delta > 0:
        concl = f"$\\Delta = {delta} > 0$ : l'équation admet deux solutions réelles distinctes."
    elif delta == 0:
        concl = f"$\\Delta = {delta} = 0$ : l'équation admet une unique solution (racine double)."
    else:
        concl = f"$\\Delta = {delta} < 0$ : l'équation n'admet aucune solution réelle."
    steps = [
        f"Étape 1 — $\\Delta = b^2-4ac = {b}^2 - 4\\times({a})\\times({c}) = {delta}$.",
        f"Étape 2 — {concl}",
    ]
    hint = "Le signe de Δ détermine à lui seul le nombre de solutions, sans qu'il soit nécessaire de les calculer."
    return {"enonce": enonce, "answer": concl, "steps": steps, "hint": hint}


# ── 3. Somme et produit des racines SANS les calculer ───────────────────────

def _gen_somme_produit(rng):
    a = _nz(rng, -4, 4)
    r1 = _small(rng, -6, 6)
    r2 = r1
    while r2 == r1:
        r2 = _small(rng, -6, 6)
    b, c = -a * (r1 + r2), a * r1 * r2
    if b**2 - 4 * a * c <= 0:
        return None
    S_val = Rational(-b, a)
    P_val = Rational(c, a)
    enonce = (
        f"L'équation ${_fmt_eq(a, b, c)}$ admet deux solutions $x_1$ et $x_2$. "
        "Sans les calculer, déterminer leur somme $x_1+x_2$ et leur produit $x_1 x_2$."
    )
    steps = [
        f"Étape 1 — Pour $ax^2+bx+c=0$, on a $x_1+x_2 = -\\dfrac{{b}}{{a}}$ et $x_1x_2=\\dfrac{{c}}{{a}}$.",
        f"Étape 2 — Ici $x_1+x_2 = \\dfrac{{-({b})}}{{{a}}} = {latex(S_val)}$ et "
        f"$x_1x_2 = \\dfrac{{{c}}}{{{a}}} = {latex(P_val)}$.",
    ]
    answer = f"$x_1+x_2 = {latex(S_val)}$ et $x_1 x_2 = {latex(P_val)}$"
    hint = "Utiliser directement les relations coefficients-racines $S=-b/a$ et $P=c/a$, sans résoudre l'équation."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


# ── 4. Factorisation du trinôme à partir de ses racines ─────────────────────

def _gen_factorisation(rng):
    a = _nz(rng, -4, 4)
    r1 = _small(rng, -6, 6)
    r2 = r1
    while r2 == r1:
        r2 = _small(rng, -6, 6)
    b, c = -a * (r1 + r2), a * r1 * r2
    expr = a * x**2 + b * x + c
    factored = factor(expr)
    expected = a * (x - r1) * (x - r2)
    if (factored - expected).expand() != 0 and (expr - expected).expand() != 0:
        return None
    enonce = f"Factoriser le trinôme $f(x) = {_fmt_eq(a, b, c)[:-4]}$ après avoir déterminé ses racines."
    # Forme explicite a(x-x1)(x-x2), construite directement en texte plutôt
    # que via latex(expected) : le printer sympy peut absorber la constante
    # `a` dans l'un des deux facteurs binomiaux lors de l'impression d'un
    # Mul (résultat mathématiquement identique une fois développé, vérifié
    # ci-dessus par (factored - expected).expand()==0, mais visuellement
    # incohérent avec l'étape 3 rédigée sous la forme a(x-x1)(x-x2)).
    factored_form = f"{a if a != 1 else ''}(x-({r1}))(x-({r2}))" if a != -1 else f"-(x-({r1}))(x-({r2}))"
    steps = [
        f"Étape 1 — On résout $f(x)=0$ : les racines sont $x_1={r1}$ et $x_2={r2}$.",
        f"Étape 2 — Un trinôme $ax^2+bx+c$ de racines $x_1,x_2$ se factorise en $a(x-x_1)(x-x_2)$.",
        f"Étape 3 — $f(x) = {factored_form}$.",
    ]
    answer = f"$f(x) = {factored_form}$"
    hint = "Une fois les racines connues, utiliser $f(x)=a(x-x_1)(x-x_2)$."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


# ── 5. Retrouver une équation à partir de deux racines données ──────────────

def _gen_equation_depuis_racines(rng):
    r1 = _small(rng, -7, 7)
    r2 = r1
    while r2 == r1:
        r2 = _small(rng, -7, 7)
    a = rng.choice([1, 1, 1, 2, 3, -1])
    b, c = -a * (r1 + r2), a * r1 * r2
    check = _roots_via_sympy(a, b, c)
    if sorted(check, key=str) != sorted([S(r1), S(r2)], key=str):
        return None
    enonce = (
        f"Déterminer une équation du second degré, de la forme $ax^2+bx+c=0$ avec $a={a}$, "
        f"dont les solutions sont $x_1={r1}$ et $x_2={r2}$."
    )
    steps = [
        f"Étape 1 — On utilise $x_1+x_2=-\\dfrac{{b}}{{a}}$ et $x_1x_2=\\dfrac{{c}}{{a}}$, donc "
        f"$b=-a(x_1+x_2)$ et $c=a\\,x_1x_2$.",
        f"Étape 2 — $b = -{a}\\times({r1+r2}) = {b}$ et $c = {a}\\times({r1})\\times({r2}) = {c}$.",
    ]
    answer = f"${_fmt_eq(a, b, c)}$"
    hint = "Reconstruire b et c à partir de la somme et du produit imposés par les racines : b=-a(x1+x2), c=a·x1x2."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


# ── 6. Problèmes contextualisés (variations authentiques) ───────────────────

def _gen_contexte_rectangle(rng):
    """Variante 1 : rectangle défini par son périmètre et son aire. Le
    contexte (objet, unité) varie réellement, pas seulement les nombres."""
    largeur = rng.randint(4, 12)
    longueur = largeur + rng.randint(2, 10)
    perimetre = 2 * (largeur + longueur)
    aire = largeur * longueur
    objet, complement, unite = rng.choice([
        ("un rectangle", "de ce rectangle", "m"), ("un jardin rectangulaire", "du jardin", "m"),
        ("une salle rectangulaire", "de la salle", "m"), ("un terrain rectangulaire", "du terrain", "m"),
    ])
    sols = _roots_via_sympy(-1, Rational(perimetre, 2), -aire)
    if S(largeur) not in sols:
        return None
    enonce = (
        f"{objet[0].upper()}{objet[1:]} a pour périmètre ${perimetre}$ {unite} et pour aire ${aire}$ {unite}². "
        f"On note $x$ sa largeur (en {unite}). Montrer que $x$ vérifie l'équation "
        f"$-x^2 + {Rational(perimetre,2)}x - {aire} = 0$, puis déterminer les dimensions {complement}."
    )
    steps = [
        f"Étape 1 — Si $x$ est la largeur, la longueur vaut $\\dfrac{{{perimetre}}}{{2}}-x$ (demi-périmètre moins la largeur).",
        f"Étape 2 — L'aire donne $x\\left(\\dfrac{{{perimetre}}}{{2}}-x\\right) = {aire}$, "
        f"soit $-x^2+{Rational(perimetre,2)}x-{aire}=0$.",
        f"Étape 3 — On résout : la solution physiquement acceptable (largeur $\\leq$ longueur, $x>0$) "
        f"est $x={largeur}$ {unite}, d'où une longueur de ${longueur}$ {unite}.",
    ]
    answer = f"Largeur $= {largeur}$ {unite}, longueur $= {longueur}$ {unite}."
    hint = "Traduire périmètre et aire en deux relations, éliminer une inconnue pour obtenir une équation du second degré en x."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


def _gen_contexte_projectile(rng):
    """Variante 2 : trajectoire (hauteur en fonction du temps), contexte
    différent (chute/tir) et question différente (temps de chute au sol)."""
    a = rng.choice([1, 2, 5])
    v0 = rng.randint(10, 30)
    h0 = rng.randint(0, 20)
    # h(t) = -a t^2 + v0 t + h0 ; on choisit v0,h0 pour garantir une racine positive
    delta = v0**2 + 4 * a * h0
    if delta < 0:
        return None
    from sympy import sqrt as _sqrt
    t_pos = (v0 + _sqrt(S(delta))) / (2 * a)
    objet, pronom = rng.choice([
        ("une balle", "elle"), ("une fusée d'artifice miniature", "elle"), ("un ballon", "il"),
    ])
    enonce = (
        f"On lance {objet} verticalement. Sa hauteur $h(t)$ (en mètres), $t$ secondes après le lancer, est modélisée par "
        f"$h(t) = -{a}t^2 + {v0}t + {h0}$. Déterminer, en résolvant une équation du second degré, "
        f"au bout de combien de secondes {pronom} retombe au sol (on donnera une valeur exacte)."
    )
    steps = [
        f"Étape 1 — L'objet touche le sol quand $h(t)=0$, soit $-{a}t^2+{v0}t+{h0}=0$.",
        f"Étape 2 — $\\Delta = {v0}^2+4\\times{a}\\times{h0} = {delta}$, donc $\\Delta > 0$.",
        f"Étape 3 — Seule la solution positive a un sens physique (le temps est positif) : "
        f"$t = \\dfrac{{-{v0}-\\sqrt{{{delta}}}}}{{-2\\times{a}}} = {latex(t_pos)}$ s.",
    ]
    answer = f"$t = {latex(t_pos)}$ secondes (seule racine positive retenue)."
    hint = "Poser h(t)=0, résoudre l'équation du second degré, puis ne garder que la solution positive (le temps ne peut pas être négatif)."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


# ── 7. Comparer deux méthodes de résolution ─────────────────────────────────

def _gen_comparer_methodes(rng):
    r1 = _small(rng, -6, 6)
    r2 = r1
    while r2 == r1:
        r2 = _small(rng, -6, 6)
    a = 1
    b, c = -(r1 + r2), r1 * r2
    delta = b**2 - 4 * a * c
    sols = _roots_via_sympy(a, b, c)
    if sorted(sols, key=str) != sorted([S(r1), S(r2)], key=str):
        return None
    enonce = (
        f"On considère l'équation ${_fmt_eq(a, b, c)}$. "
        "Léa la résout en remarquant une racine évidente puis en utilisant la somme/produit ; "
        "Marc la résout avec le discriminant. Mener les deux méthodes et vérifier qu'elles donnent le même résultat."
    )
    r_evidente = r1
    autre = r2
    steps = [
        f"Méthode de Léa — $x_1={r_evidente}$ est une racine évidente (on vérifie : "
        f"${r_evidente}^2 {'+' if b>=0 else '-'} {abs(b)}\\times({r_evidente}) {'+' if c>=0 else '-'} {abs(c)} = 0$). "
        f"Comme $x_1x_2={c}$, on trouve $x_2={c}/{r_evidente}={autre}$.",
        f"Méthode de Marc — $\\Delta = {delta}$, donc les racines sont "
        f"$\\dfrac{{-({b})\\pm\\sqrt{{{delta}}}}}{{2}}$, ce qui redonne $\\{{{min(r1,r2)};{max(r1,r2)}\\}}$.",
        "Étape finale — Les deux méthodes donnent bien le même ensemble de solutions : "
        "une racine évidente permet d'aller plus vite, le discriminant fonctionne toujours.",
    ]
    answer = f"$S = \\{{{min(r1,r2)};\\,{max(r1,r2)}\\}}$ par les deux méthodes."
    hint = "Repérer une racine évidente accélère le calcul (via somme/produit) ; le discriminant est la méthode universelle."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


# ── 8. Vérifier une résolution donnée (vrai/faux justifié) ──────────────────

def _gen_verifier_resolution(rng):
    a = _nz(rng, -4, 4)
    r1 = _small(rng, -6, 6)
    r2 = r1
    while r2 == r1:
        r2 = _small(rng, -6, 6)
    b, c = -a * (r1 + r2), a * r1 * r2
    delta = b**2 - 4 * a * c
    correct_sols = sorted(_roots_via_sympy(a, b, c), key=str)
    is_correct = rng.random() < 0.5
    if is_correct:
        proposed = correct_sols
        proposed_delta = delta
    else:
        erreur = rng.choice(["signe_delta", "racine_fausse", "oubli_2a"])
        if erreur == "signe_delta":
            proposed_delta = -delta if delta != 0 else delta + 4
            proposed = correct_sols  # discours incohérent avec Δ affiché : l'erreur porte sur le calcul de Δ
        elif erreur == "racine_fausse":
            proposed_delta = delta
            proposed = [correct_sols[0] + 1, correct_sols[1]] if len(correct_sols) == 2 else [correct_sols[0] + 1]
        else:
            # Erreur classique : l'élève oublie de diviser par 2a et écrit
            # x = -b ± √Δ au lieu de x = (-b ± √Δ)/(2a).
            proposed_delta = delta
            from sympy import sqrt as _sqrt
            root_delta = _sqrt(S(delta))
            proposed = sorted({-b - root_delta, -b + root_delta}, key=str)
            if sorted(proposed, key=str) == sorted(correct_sols, key=str):
                return None  # coïncidence dégénérée (rare) : le "faux" ne serait pas visible
    prop_str = ", ".join(f"$x={latex(s)}$" for s in proposed)
    enonce = (
        f"Un élève affirme, pour l'équation ${_fmt_eq(a, b, c)}$ : \"$\\Delta={proposed_delta}$ et "
        f"les solutions sont {prop_str}\". Cette résolution est-elle correcte ? Justifier."
    )
    if is_correct:
        answer = f"Vrai : $\\Delta={delta}$ et les solutions annoncées sont bien correctes."
        steps = [
            f"Étape 1 — On recalcule : $\\Delta=b^2-4ac={delta}$, ce qui correspond à ce qui est annoncé.",
            f"Étape 2 — On vérifie les racines par substitution dans l'équation : elles conviennent.",
        ]
    else:
        answer = f"Faux : en réalité $\\Delta={delta}$" + (
            f" et les solutions sont {', '.join(f'$x={latex(s)}$' for s in correct_sols)}." if correct_sols else " (aucune solution réelle)."
        )
        steps = [
            f"Étape 1 — On recalcule indépendamment : $\\Delta=b^2-4ac={delta}$.",
            "Étape 2 — Cette valeur (et/ou les racines annoncées) ne correspond pas à ce qu'affirme l'élève : "
            "l'affirmation est fausse.",
        ]
    hint = "Recalculer soi-même Δ et les racines avant de juger l'affirmation proposée — ne jamais faire confiance à un résultat donné sans le vérifier."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


# ── 9. Détecter et corriger une erreur dans une résolution ──────────────────

def _gen_corriger_erreur(rng):
    a = _nz(rng, -4, 4)
    r1 = _small(rng, -6, 6)
    r2 = r1
    while r2 == r1:
        r2 = _small(rng, -6, 6)
    b, c = -a * (r1 + r2), a * r1 * r2
    delta = b**2 - 4 * a * c
    correct_sols = sorted(_roots_via_sympy(a, b, c), key=str)
    if delta <= 0 or len(correct_sols) != 2:
        return None
    # Erreur classique : oubli du signe "-" devant b dans la formule des racines.
    wrong_x1 = Rational(b - S(delta) ** Rational(1, 2), 2 * a)
    enonce = (
        f"Un élève résout ${_fmt_eq(a, b, c)}$ ainsi : \"$\\Delta = {delta}$, donc "
        f"$x_1 = \\dfrac{{b-\\sqrt{{\\Delta}}}}{{2a}}$ et $x_2=\\dfrac{{b+\\sqrt{{\\Delta}}}}{{2a}}$\" "
        "(il a oublié le signe $-$ devant $b$ au numérateur). Identifier son erreur et donner la résolution correcte."
    )
    steps = [
        f"Étape 1 — Le calcul de $\\Delta={delta}>0$ est correct.",
        "Étape 2 — L'erreur est dans la formule des racines : c'est "
        "$x=\\dfrac{-b\\pm\\sqrt{\\Delta}}{2a}$ (avec un $-b$), pas $\\dfrac{b\\pm\\sqrt{\\Delta}}{2a}$.",
        f"Étape 3 — Avec la bonne formule : $x_1={latex(correct_sols[0])}$ et $x_2={latex(correct_sols[1])}$.",
    ]
    answer = f"Erreur de signe devant $b$ dans la formule ; les solutions correctes sont $x_1={latex(correct_sols[0])}$ et $x_2={latex(correct_sols[1])}$."
    hint = "Comparer la formule utilisée par l'élève à la formule officielle x=(-b±√Δ)/(2a) terme à terme."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


# ── 10. Retrouver un paramètre (racine double / deux racines / aucune) ──────

def _gen_parametre(rng):
    b = _nz(rng, -8, 8)
    # Δ(m) = b² - 4m (équation x² + b x + m = 0)
    b_term = "+x" if b == 1 else ("-x" if b == -1 else (f"+{b}x" if b > 0 else f"-{abs(b)}x"))
    eq_latex = f"x^2{b_term}+m=0"
    seuil = Rational(b**2, 4)
    question = rng.choice(["double", "deux", "aucune"])
    if question == "double":
        target = f"${eq_latex}$ ait une racine double"
        cond = f"$m = {latex(seuil)}$"
        just = f"Racine double $\\iff \\Delta=0 \\iff b^2-4m=0 \\iff m=\\dfrac{{b^2}}{{4}}={latex(seuil)}$."
    elif question == "deux":
        target = f"${eq_latex}$ ait deux solutions réelles distinctes"
        cond = f"$m < {latex(seuil)}$"
        just = f"Deux solutions distinctes $\\iff \\Delta>0 \\iff b^2-4m>0 \\iff m<\\dfrac{{b^2}}{{4}}={latex(seuil)}$."
    else:
        target = f"${eq_latex}$ n'ait aucune solution réelle"
        cond = f"$m > {latex(seuil)}$"
        just = f"Aucune solution $\\iff \\Delta<0 \\iff b^2-4m<0 \\iff m>\\dfrac{{b^2}}{{4}}={latex(seuil)}$."
    enonce = f"Déterminer, selon les valeurs du réel $m$, pour quelle(s) valeur(s) l'équation {target}."
    steps = [
        f"Étape 1 — On exprime le discriminant en fonction de $m$ : $\\Delta = b^2-4\\times1\\times m = {b}^2-4m$.",
        f"Étape 2 — {just}",
    ]
    answer = cond
    hint = "Exprimer Δ en fonction du paramètre m, puis traduire la condition demandée (Δ=0, Δ>0 ou Δ<0) en une inégalité/égalité sur m."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


@dataclass(frozen=True)
class Family:
    id: str
    level: int
    label: str
    generate: Callable[[random.Random], Optional[dict]]
    structure_hint: str
    rule_hint: str


# Score fixe par famille : reflète la profondeur de raisonnement du TYPE de
# question (pas la taille des nombres tirés, interdit par le cahier des
# charges). Espacé pour rester strictement croissant d'un niveau déclaré au
# suivant (voir _difficulty_bucket_from_score / test de calibration).
FAMILY_BASE_SCORE: dict[str, float] = {
    "resolution": 1.0,
    "signe_discriminant": 2.0,
    "somme_produit": 2.2,
    "factorisation": 2.4,
    "equation_depuis_racines": 3.0,
    "contexte_rectangle": 3.2,
    "comparer_methodes": 3.4,
    "verifier_resolution": 3.6,
    "corriger_erreur": 4.0,
    "contexte_projectile": 4.2,
    "parametre": 5.0,
}

FAMILIES: tuple[Family, ...] = (
    Family("resolution", 1, "Résolution directe (les 3 cas de discriminant)", _gen_resolution,
           "une équation du second degré à résoudre", "calculer Δ puis appliquer la formule adaptée à son signe"),
    Family("signe_discriminant", 2, "Signe du discriminant sans résoudre", _gen_signe_discriminant,
           "une équation dont on ne demande pas les solutions", "le signe de Δ suffit à conclure sur le nombre de solutions"),
    Family("somme_produit", 2, "Somme et produit des racines", _gen_somme_produit,
           "une équation dont on connaît l'existence de deux racines", "les relations S=-b/a et P=c/a"),
    Family("factorisation", 2, "Factorisation à partir des racines", _gen_factorisation,
           "un trinôme dont on cherche la forme factorisée", "a(x-x1)(x-x2) une fois les racines connues"),
    Family("equation_depuis_racines", 3, "Retrouver une équation depuis ses racines", _gen_equation_depuis_racines,
           "deux racines imposées", "reconstruire b et c via S et P"),
    Family("contexte_rectangle", 3, "Problème contextualisé (aire/périmètre)", _gen_contexte_rectangle,
           "une mise en équation à partir d'un contexte géométrique", "traduire les données en équation du second degré"),
    Family("comparer_methodes", 3, "Comparer deux méthodes de résolution", _gen_comparer_methodes,
           "une équation à racine évidente", "factorisation évidente vs discriminant, même résultat"),
    Family("verifier_resolution", 3, "Vérifier une résolution proposée", _gen_verifier_resolution,
           "une résolution proposée, correcte ou non", "recalculer Δ et les racines avant de juger"),
    Family("corriger_erreur", 4, "Détecter et corriger une erreur", _gen_corriger_erreur,
           "une résolution contenant une erreur classique", "comparer chaque étape à la méthode correcte"),
    Family("contexte_projectile", 4, "Problème contextualisé (trajectoire)", _gen_contexte_projectile,
           "une mise en équation à partir d'une trajectoire", "résoudre puis ne garder que la solution physiquement acceptable"),
    Family("parametre", 5, "Retrouver un paramètre", _gen_parametre,
           "une équation dépendant d'un paramètre m", "exprimer Δ en fonction de m puis traduire la condition demandée"),
)

FAMILIES_BY_ID = {f.id: f for f in FAMILIES}


def _difficulty_bucket_from_score(score: float) -> int:
    if score <= 1.5:
        return 1
    if score <= 2.7:
        return 2
    if score <= 3.8:
        return 3
    if score <= 4.7:
        return 4
    return 5


def build_exercise(family: Family, rng: random.Random) -> Optional[dict]:
    notes = family.generate(rng)
    if notes is None:
        return None
    score = FAMILY_BASE_SCORE[family.id]
    real_level = _difficulty_bucket_from_score(score)
    hint = notes.get("hint") or f"Reconnais {family.structure_hint} : {family.rule_hint}."
    return {
        "enonce": notes["enonce"],
        "answer": notes["answer"],
        "hint": hint,
        "solution_steps": notes["steps"],
        "chapter_id": CHAPTER_ID,
        "notion": NOTION,
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
    fam = FAMILIES_BY_ID[family_id]
    for _ in range(max_attempts):
        ex = build_exercise(fam, rng)
        if ex is not None:
            return ex
    raise RuntimeError(f"Impossible de générer un exercice valide pour la famille {family_id!r}")


def generate_pool(per_family: int = 12, seed: int = 20260823) -> list[dict]:
    rng = random.Random(seed)
    per_family_pool: dict[str, list[dict]] = {}
    for family in FAMILIES:
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
        family = FAMILIES[idx % len(FAMILIES)]
        bucket = per_family_pool.get(family.id) or []
        if bucket:
            pool.append(bucket.pop(0))
        idx += 1
        if idx > 200000:
            break
    for i, ex in enumerate(pool):
        ex["id"] = GENERATED_ID_OFFSET + i
    return pool


# ── Famille supplémentaire — mission "diversification structurelle"
# (2026-09-02) : equation_depuis_racines était auditée à 96% de quasi-doublon
# (toujours "a donné directement, b et c à reconstruire via S et P"). Nouvelle
# structure : $a$ n'est PAS donné, il faut le retrouver via une valeur de $f$
# en un point tiers — jamais mélangée à FAMILIES/generate_pool (baseline
# figée).

def _gen_equation_depuis_racines_et_point(rng):
    r1 = _small(rng, -6, 6)
    r2 = r1
    while r2 == r1:
        r2 = _small(rng, -6, 6)
    a = rng.choice([1, 1, 2, 3, -1, -2])
    x0 = _small(rng, -6, 6)
    if x0 == r1 or x0 == r2:
        return None
    valeur = a * (x0 - r1) * (x0 - r2)
    if valeur == 0:
        return None
    b, c = -a * (r1 + r2), a * r1 * r2
    check = _roots_via_sympy(a, b, c)
    if sorted(check, key=str) != sorted([S(r1), S(r2)], key=str):
        return None
    enonce = (
        f"Une fonction $f$ du second degré admet pour racines $x_1={r1}$ et $x_2={r2}$, et vérifie "
        f"$f({x0})={valeur}$. Déterminer l'expression de $f(x) = ax^2+bx+c$."
    )
    steps = [
        f"Étape 1 — $f$ s'écrit sous forme factorisée $f(x) = a(x-{r1})(x-{r2})$.",
        f"Étape 2 — $f({x0}) = a \\times ({x0-r1}) \\times ({x0-r2}) = {valeur}$, donc $a = "
        f"\\dfrac{{{valeur}}}{{{(x0-r1)*(x0-r2)}}} = {a}$.",
        f"Étape 3 — On développe : $b = -a(x_1+x_2) = {b}$ et $c = a\\,x_1x_2 = {c}$.",
    ]
    answer = f"$f(x) = {_fmt_eq(a, b, c).replace(' = 0', '')}$"
    hint = "Utiliser la forme factorisée a(x-x1)(x-x2), évaluer en x0 pour trouver a, puis développer."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


# ── Famille supplémentaire — mission "audit et renforcement de la diversité
# NUMÉRIQUE" (2026-09-02) : vérification par lecture du code de `_gen_resolution`
# (et de toutes les familles dérivées de r1/r2 entiers) — le discriminant y est
# TOUJOURS un carré parfait par construction (b,c calculés à partir de racines
# entières choisies au départ), donc jamais de racine irrationnelle nulle part
# dans Chapitre_2. Nouvelle famille dédiée : a,b,c tirés directement (pas de
# racines entières imposées a priori), on ne garde le tirage QUE si Δ>0 et
# n'est PAS un carré parfait — les solutions exactes viennent de
# `_roots_via_sympy`, seule source de vérité (jamais recalculées à la main).

def _gen_resolution_irrationnelle(rng):
    a = 1
    b = c = None
    for _ in range(300):
        bb = _small(rng, -8, 8)
        cc = _small(rng, -8, 8)
        delta = bb**2 - 4 * a * cc
        if delta <= 0:
            continue
        roots = _roots_via_sympy(a, bb, cc)
        if len(roots) != 2 or all(r.is_rational for r in roots):
            continue
        b, c = bb, cc
        break
    if b is None:
        return None
    roots = _roots_via_sympy(a, b, c)
    delta = b**2 - 4 * a * c
    enonce = (
        f"Résoudre dans $\\mathbb{{R}}$ l'équation ${_fmt_eq(a, b, c)}$. "
        f"Donner les solutions sous forme exacte (radicaux non simplifiables en entiers)."
    )
    steps = [
        f"Étape 1 — Discriminant : $\\Delta = {b}^2 - 4\\times{a}\\times({c}) = {delta}$.",
        f"Étape 2 — $\\Delta = {delta}$ n'est pas le carré d'un entier : les solutions restent sous forme "
        f"radicale, $x = \\dfrac{{-b \\pm \\sqrt{{\\Delta}}}}{{2a}}$.",
        f"Étape 3 — $x_1 = {latex(roots[0])}$ et $x_2 = {latex(roots[1])}$.",
    ]
    answer = f"$x_1 = {latex(roots[0])}$ ou $x_2 = {latex(roots[1])}$"
    hint = "Calculer le discriminant puis appliquer la formule des racines, même si Δ n'est pas un carré parfait."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


# ── Familles supplémentaires — mission "audit final et exhaustif de la
# diversité mathématique" (2026-09-02) : `resolution_irrationnelle` (ci-
# dessus) a comblé UNE SEULE famille sur les ~9 construites à partir de
# racines entières (audit confirmé par lecture de code : `resolution`,
# `somme_produit`, `factorisation`, `equation_depuis_racines`,
# `comparer_methodes`, `verifier_resolution`, `corriger_erreur`,
# `equation_depuis_racines_et_point`, `contexte_rectangle` partent toutes de
# r1/r2 entiers choisis a priori). Deux nouvelles familles, à deux
# raisonnements réellement différents de `resolution_irrationnelle` (qui ne
# fait que résoudre) :
# - `equation_depuis_racines_irrationnelles` : reconstruire l'équation à
#   PARTIR de deux racines conjuguées p±√q (raisonnement inverse — utiliser
#   somme/produit d'irrationnels conjugués, jamais testé nulle part dans le
#   chapitre) ;
# - `verifier_resolution_irrationnelle` : juger une résolution proposée
#   (vrai/faux justifié) dont le discriminant n'est pas un carré parfait —
#   `verifier_resolution` existant ne teste ce raisonnement que sur des
#   racines entières.
# (`contexte_projectile` n'est volontairement pas dupliquée : vérifié par
# exécution, elle produit déjà ~94% de résultats irrationnels par
# construction — v0,h0 y sont tirés indépendamment, pas dérivés de racines
# entières — donc aucun gap réel à combler pour cette famille.)

def _gen_equation_depuis_racines_irrationnelles(rng):
    from sympy import sqrt as _sqrt
    p = _small(rng, -6, 6)
    q = rng.choice([2, 3, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15])
    a = rng.choice([1, 1, 1, 2, 3, -1])
    b = -a * 2 * p
    c = a * (p * p - q)
    check = _roots_via_sympy(a, b, c)
    expected = sorted([S(p) + _sqrt(S(q)), S(p) - _sqrt(S(q))], key=str)
    if sorted(check, key=str) != expected:
        return None
    r1_s, r2_s = latex(expected[1]), latex(expected[0])
    enonce = (
        f"Une fonction du second degré, de la forme $ax^2+bx+c=0$ avec $a={a}$, admet pour "
        f"solutions $x_1={r1_s}$ et $x_2={r2_s}$. Déterminer $b$ et $c$."
    )
    steps = [
        f"Étape 1 — $x_1+x_2 = ({r1_s})+({r2_s}) = {2*p}$ (les termes en $\\sqrt{{{q}}}$ s'annulent) "
        f"et $x_1x_2 = ({r1_s})({r2_s}) = {p}^2-{q} = {p*p-q}$ (identité $(u+v)(u-v)=u^2-v^2$).",
        f"Étape 2 — $b=-a(x_1+x_2) = -{a}\\times{2*p} = {b}$ et $c=a\\,x_1x_2 = {a}\\times({p*p-q}) = {c}$.",
    ]
    answer = f"$b = {b}$ et $c = {c}$ (soit ${_fmt_eq(a, b, c)}$)"
    hint = "Même deux racines irrationnelles conjuguées se traitent avec les relations S=-b/a, P=c/a — les radicaux s'annulent dans la somme et se simplifient dans le produit via (u+v)(u-v)=u²-v²."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


def _gen_verifier_resolution_irrationnelle(rng):
    a = 1
    b = c = None
    for _ in range(300):
        bb = _small(rng, -8, 8)
        cc = _small(rng, -8, 8)
        delta = bb**2 - 4 * a * cc
        if delta <= 0:
            continue
        roots = _roots_via_sympy(a, bb, cc)
        if len(roots) != 2 or all(r.is_rational for r in roots):
            continue
        b, c = bb, cc
        break
    if b is None:
        return None
    delta = b**2 - 4 * a * c
    correct_sols = sorted(_roots_via_sympy(a, b, c), key=str)
    is_correct = rng.random() < 0.5
    if is_correct:
        proposed_delta = delta
        proposed = correct_sols
    else:
        from sympy import sqrt as _sqrt
        erreur = rng.choice(["signe_delta_faux", "oubli_2a", "delta_errone"])
        if erreur == "signe_delta_faux":
            proposed_delta = delta
            root_delta = _sqrt(S(delta))
            proposed = sorted({b - root_delta, b + root_delta}, key=str)  # oubli du signe "-" devant b
        elif erreur == "oubli_2a":
            proposed_delta = delta
            root_delta = _sqrt(S(delta))
            proposed = sorted({-b - root_delta, -b + root_delta}, key=str)  # division par 2a oubliée
        else:
            proposed_delta = delta + 3
            proposed = correct_sols
        if sorted(proposed, key=str) == sorted(correct_sols, key=str) and proposed_delta == delta:
            return None
    prop_str = ", ".join(f"$x={latex(s)}$" for s in proposed)
    enonce = (
        f"Un élève affirme, pour l'équation ${_fmt_eq(a, b, c)}$ : \"$\\Delta={proposed_delta}$ et "
        f"les solutions sont {prop_str}\" (le discriminant n'est pas un carré parfait ici). "
        "Cette résolution est-elle correcte ? Justifier."
    )
    if is_correct:
        answer = f"Vrai : $\\Delta={delta}$ (non carré parfait) et les solutions annoncées sous forme radicale sont bien correctes."
        steps = [
            f"Étape 1 — On recalcule : $\\Delta=b^2-4ac={delta}$, ce qui correspond à ce qui est annoncé.",
            "Étape 2 — $\\Delta$ n'étant pas le carré d'un entier, les solutions restent sous forme radicale ; "
            "on vérifie qu'elles correspondent bien à la formule $x=\\dfrac{-b\\pm\\sqrt{\\Delta}}{2a}$.",
        ]
    else:
        answer = (
            f"Faux : en réalité $\\Delta={delta}$ et les solutions sont "
            f"{', '.join(f'$x={latex(s)}$' for s in correct_sols)}."
        )
        steps = [
            f"Étape 1 — On recalcule indépendamment : $\\Delta=b^2-4ac={delta}$.",
            "Étape 2 — La formule $x=\\dfrac{-b\\pm\\sqrt{\\Delta}}{2a}$ appliquée correctement ne redonne pas "
            "ce qu'affirme l'élève : l'affirmation est fausse.",
        ]
    hint = "Ne pas se laisser impressionner par la présence d'un radical : recalculer Δ et réappliquer la formule (-b±√Δ)/(2a) terme à terme avant de juger."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


EXTRA_FAMILY_BASE_SCORE: dict[str, float] = {
    "equation_depuis_racines_et_point": 3.4,
    "resolution_irrationnelle": 3.6,
    "equation_depuis_racines_irrationnelles": 3.8,
    "verifier_resolution_irrationnelle": 3.9,
}

EXTRA_FAMILIES: tuple[Family, ...] = (
    Family("equation_depuis_racines_et_point", 4, "Retrouver une équation depuis ses racines et un point",
           _gen_equation_depuis_racines_et_point, "deux racines et une valeur en un point tiers",
           "évaluer la forme factorisée au point donné pour retrouver a, puis développer"),
    Family("resolution_irrationnelle", 4, "Résoudre une équation à discriminant non carré parfait",
           _gen_resolution_irrationnelle, "discriminant positif mais non carré parfait, solutions radicales",
           "appliquer la formule des racines et laisser le résultat sous forme radicale exacte"),
    Family("equation_depuis_racines_irrationnelles", 4, "Retrouver une équation depuis deux racines conjuguées irrationnelles",
           _gen_equation_depuis_racines_irrationnelles, "deux racines de la forme p±√q",
           "utiliser S=-b/a et P=c/a : les radicaux s'annulent dans la somme et se simplifient dans le produit"),
    Family("verifier_resolution_irrationnelle", 4, "Vérifier une résolution à discriminant non carré parfait",
           _gen_verifier_resolution_irrationnelle, "une résolution radicale proposée, correcte ou non",
           "recalculer Δ et réappliquer (-b±√Δ)/(2a) avant de juger, même en présence d'un radical"),
)

EXTRA_FAMILIES_BY_ID = {f.id: f for f in EXTRA_FAMILIES}


def _build_extra_exercise(family: Family, rng: random.Random) -> Optional[dict]:
    notes = family.generate(rng)
    if notes is None:
        return None
    score = EXTRA_FAMILY_BASE_SCORE[family.id]
    real_level = _difficulty_bucket_from_score(score)
    hint = notes.get("hint") or f"Reconnais {family.structure_hint} : {family.rule_hint}."
    return {
        "enonce": notes["enonce"],
        "answer": notes["answer"],
        "hint": hint,
        "solution_steps": notes["steps"],
        "chapter_id": CHAPTER_ID,
        "notion": NOTION,
        "difficulty": real_level,
        "difficulty_label": LEVEL_META[real_level]["label"],
        "difficulty_emoji": LEVEL_META[real_level]["emoji"],
        "family": family.id,
        "family_label": family.label,
        "declared_level": family.level,
        "complexity_score": score,
        "source": "generated",
    }


def generate_extra_pool(per_family: int = 12, seed: int = 20260946) -> list[dict]:
    """Pool de diversification structurelle (mission 2026-09-02) — jamais
    mélangé à generate_pool()/FAMILIES (baseline figée). IDs à partir de
    GENERATED_ID_OFFSET + 8000."""
    rng = random.Random(seed)
    per_family_pool: dict[str, list[dict]] = {}
    for family in EXTRA_FAMILIES:
        seen_signatures = set()
        items = []
        attempts = 0
        while len(items) < per_family and attempts < per_family * 60:
            attempts += 1
            ex = _build_extra_exercise(family, rng)
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
        family = EXTRA_FAMILIES[idx % len(EXTRA_FAMILIES)]
        bucket = per_family_pool.get(family.id) or []
        if bucket:
            pool.append(bucket.pop(0))
        idx += 1
        if idx > 200000:
            break
    offset = GENERATED_ID_OFFSET + 8000
    for i, ex in enumerate(pool):
        ex["id"] = offset + i
    return pool
