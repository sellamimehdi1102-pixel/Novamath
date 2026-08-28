"""Génération symbolique d'exercices sur le nombre dérivé et la tangente
(Première, Chapitre_3, notion "Nombre dérivé. Tangente").

Même principe que `webapp/exercise_generator/second_degre.py` (dont ce
module reprend le patron) : chaque famille couvre un vrai type de
raisonnement, chaque valeur annoncée est calculée par sympy (`diff`,
`limit`, `solve`), et la difficulté affichée vient d'un score FIXE par
famille (profondeur de raisonnement du type de question), jamais de la
taille des nombres tirés.

Module séparé (et non une extension de `derivatives.py`) car il cible une
notion différente ("Nombre dérivé. Tangente" vs "Fonction dérivée") avec un
objet géométrique propre (la tangente) — voir la docstring du chantier pour
la justification de ce choix (mixte : familles mécanisables ici + quelques
exercices de lecture graphique rédigés à la main, trop spécifiques pour être
généralisés symboliquement sans dupliquer une image).
"""
import random
from dataclasses import dataclass
from typing import Callable, Optional

from sympy import Eq, Rational, diff, expand, latex, limit, simplify, solve, sqrt, symbols

x, h, t = symbols("x h t")

CHAPTER_ID = "Chapitre_3"
NOTION = "Nombre dérivé. Tangente"

# Distinct de tous les offsets déjà utilisés (900_000/910_000/920_000/
# 930_000/940_000) — voir tools/generate_derivative_exercises.py qui liste
# tous les offsets et garantit l'absence de collision d'id entre pools.
GENERATED_ID_OFFSET = 950_000

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


def _fmt_poly2(a, b, c, var="x") -> str:
    parts = [f"{'' if a == 1 else ('-' if a == -1 else a)}{var}^2"]
    if b != 0:
        coeff = "" if abs(b) == 1 else abs(b)
        parts.append(f"{'+' if b > 0 else '-'} {coeff}{var}")
    if c != 0:
        parts.append(f"{'+' if c > 0 else '-'} {abs(c)}")
    return " ".join(parts)


def _rand_poly2(rng, lo_a=-4, hi_a=4):
    return _nz(rng, lo_a, hi_a), _small(rng, -6, 6), _small(rng, -6, 6)


def _fmt_poly3(a, b, c, var="x") -> str:
    parts = [f"{'' if a == 1 else ('-' if a == -1 else a)}{var}^3"]
    if b != 0:
        coeff = "" if abs(b) == 1 else abs(b)
        parts.append(f"{'+' if b > 0 else '-'} {coeff}{var}")
    if c != 0:
        parts.append(f"{'+' if c > 0 else '-'} {abs(c)}")
    return " ".join(parts)


def _rand_poly3(rng, lo_a=-2, hi_a=2):
    return _nz(rng, lo_a, hi_a), _small(rng, -4, 4), _small(rng, -6, 6)


def _rand_f_expr(rng):
    """Choisit une fonction polynomiale (degré 2, majoritaire, ou degré 3,
    au programme de Première au même titre que le degré 2 pour le calcul du
    nombre dérivé) — évite que les familles mécaniques ne travaillent
    toujours sur la même mécanique de calcul (chantier « diversification des
    calculs »). Renvoie (expression sympy, texte LaTeX de f(x))."""
    if rng.random() < 0.7:
        a, b, c = _rand_poly2(rng)
        return a * x**2 + b * x + c, _fmt_poly2(a, b, c)
    a, b, c = _rand_poly3(rng)
    return a * x**3 + b * x + c, _fmt_poly3(a, b, c)


# ── 1. Taux de variation → nombre dérivé ────────────────────────────────────

def _gen_taux_variation(rng):
    f, f_txt = _rand_f_expr(rng)
    x0 = _small(rng, -6, 6)
    taux_expr = expand((f.subs(x, x0 + h) - f.subs(x, x0)) / h)
    fprime_x0 = limit(taux_expr, h, 0)
    enonce = (
        f"Soit $f$ la fonction définie sur $\\mathbb{{R}}$ par $f(x) = {f_txt}$. "
        f"Exprimer le taux de variation $\\dfrac{{f({x0}+h)-f({x0})}}{{h}}$ en fonction de $h$ "
        f"(pour $h \\neq 0$), puis en déduire le nombre dérivé $f'({x0})$."
    )
    steps = [
        f"Étape 1 — $f({x0}+h) = {latex(expand(f.subs(x, x0 + h)))}$, à développer et simplifier.",
        f"Étape 2 — Après simplification, $\\dfrac{{f({x0}+h)-f({x0})}}{{h}} = {latex(taux_expr)}$.",
        f"Étape 3 — Quand $h$ tend vers $0$, ce taux de variation tend vers ${latex(fprime_x0)}$, "
        f"donc $f'({x0}) = {latex(fprime_x0)}$.",
    ]
    answer = f"$f'({x0}) = {latex(fprime_x0)}$"
    hint = "Développer f(x0+h)-f(x0), factoriser par h, puis faire tendre h vers 0."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


# ── 2. Nombre dérivé via l'expression EXPLICITE de la limite ────────────────

def _gen_limite_derivee_explicite(rng):
    f, f_txt = _rand_f_expr(rng)
    x0 = _small(rng, -5, 5)
    taux_expr = expand((f.subs(x, x0 + h) - f.subs(x, x0)) / h)
    fprime_x0 = limit(taux_expr, h, 0)
    enonce = (
        f"Soit $f$ la fonction définie sur $\\mathbb{{R}}$ par $f(x) = {f_txt}$. "
        f"Écrire, sans la calculer d'abord, l'expression de la limite dont la valeur donne le nombre "
        f"dérivé $f'({x0})$, puis calculer cette limite."
    )
    steps = [
        f"Étape 1 — Par définition, $f'({x0}) = \\displaystyle\\lim_{{h\\to0}} "
        f"\\dfrac{{f({x0}+h)-f({x0})}}{{h}}$.",
        f"Étape 2 — On développe : $\\dfrac{{f({x0}+h)-f({x0})}}{{h}} = {latex(taux_expr)}$.",
        f"Étape 3 — $\\displaystyle\\lim_{{h\\to0}} \\left({latex(taux_expr)}\\right) = {latex(fprime_x0)}$, "
        f"donc $f'({x0}) = {latex(fprime_x0)}$.",
    ]
    answer = (
        f"$f'({x0}) = \\displaystyle\\lim_{{h\\to0}}\\dfrac{{f({x0}+h)-f({x0})}}{{h}} = {latex(fprime_x0)}$"
    )
    hint = "Écrire d'abord la limite elle-même (définition du nombre dérivé), avant de la calculer — ce n'est pas juste appliquer une formule de dérivation toute faite."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


# ── 3. Équation de la tangente ──────────────────────────────────────────────
# Cette famille utilise `diff`+`simplify` (contrairement à taux_variation et
# limite_derivee_explicite, qui explicitent le calcul de la limite en h et
# restent donc volontairement limitées aux polynômes) : elle se prête sans
# adaptation à toute forme dérivable, donc à une vraie diversification des
# objets mathématiques (audit calcul-diversité Première : cette notion était
# 100% polynomiale alors que "Fonction dérivée", notion voisine du même
# chapitre, maîtrise déjà racine et quotient — rien ne justifie de l'en priver
# ici).

def _rand_f_expr_diverse(rng):
    """f(x) diversifié : polynôme degré 2/3 (majoritaire), racine d'une
    expression affine, ou quotient affine/affine. Renvoie (expr, texte latex,
    info) où `info` décrit la contrainte de domaine à respecter pour x0
    (voir _draw_domain_safe_x0)."""
    kind = rng.choices(["poly2", "poly3", "racine", "quotient"], weights=[45, 20, 20, 15])[0]
    if kind == "poly2":
        a, b, c = _rand_poly2(rng)
        return a * x**2 + b * x + c, _fmt_poly2(a, b, c), ("poly", None, None)
    if kind == "poly3":
        a, b, c = _rand_poly3(rng)
        return a * x**3 + b * x + c, _fmt_poly3(a, b, c), ("poly", None, None)
    if kind == "racine":
        a = _nz(rng, 1, 4)
        b = _small(rng, -6, 6)
        return sqrt(a * x + b), f"\\sqrt{{{latex(a * x + b)}}}", ("racine", a, b)
    a = _nz(rng, -6, 6)
    b = _nz(rng, -5, 5)
    return a / (x + b), f"\\dfrac{{{a}}}{{{latex(x + b)}}}", ("quotient", a, b)


def _draw_domain_safe_x0(rng, info, lo=-5, hi=5, max_tries=50):
    """Tire x0 dans [lo, hi] compatible avec le domaine de f (racine : sous
    la racine strictement positif, pour que f soit dérivable en x0 ; quotient
    : dénominateur non nul). Renvoie None si aucun tirage valide (dégénéré,
    l'appelant retire une nouvelle graine)."""
    kind, p1, p2 = info
    for _ in range(max_tries):
        x0 = _small(rng, lo, hi)
        if kind == "racine":
            if p1 * x0 + p2 > 0:
                return x0
        elif kind == "quotient":
            if x0 != -p2:
                return x0
        else:
            return x0
    return None


def _gen_tangente(rng):
    f, f_txt, info = _rand_f_expr_diverse(rng)
    x0 = _draw_domain_safe_x0(rng, info)
    if x0 is None:
        return None
    fprime = simplify(diff(f, x))
    m = simplify(fprime.subs(x, x0))
    p = simplify(f.subs(x, x0))
    tangente = expand(m * (x - x0) + p)
    enonce = (
        f"Soit $f$ la fonction définie sur $\\mathbb{{R}}$ par $f(x) = {f_txt}$. "
        f"Déterminer une équation de la tangente à la courbe représentative de $f$ au point d'abscisse $x_0 = {x0}$."
    )
    steps = [
        f"Étape 1 — $f'(x) = {latex(fprime)}$, donc $f'({x0}) = {latex(m)}$.",
        f"Étape 2 — $f({x0}) = {latex(p)}$.",
        f"Étape 3 — La tangente a pour équation $y = f'({x0})(x-{x0}) + f({x0})$, soit $y = {latex(tangente)}$.",
    ]
    answer = f"$y = {latex(tangente)}$"
    hint = "Utiliser $y = f'(x_0)(x-x_0)+f(x_0)$."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


# ── 4. Interprétation du signe de f'(a) ──────────────────────────────────────

def _gen_signe_interpretation(rng):
    a, b, c = _rand_poly2(rng)
    x0 = _small(rng, -5, 5)
    f = a * x**2 + b * x + c
    fprime = diff(f, x)
    val = fprime.subs(x, x0)
    if val == 0:
        return None
    sens = "croissante" if val > 0 else "décroissante"
    enonce = (
        f"Soit $f$ une fonction dérivable en $x_0={x0}$, avec $f'({x0}) = {latex(val)}$. "
        "Sans calcul supplémentaire, que peut-on dire du sens de variation de $f$ au voisinage de $x_0$ ?"
    )
    steps = [
        f"Étape 1 — Le signe de $f'({x0})$ est {'positif' if val > 0 else 'négatif'}.",
        f"Étape 2 — Or le signe du nombre dérivé en un point donne directement le sens de variation local : "
        f"$f$ est {sens} au voisinage de $x_0={x0}$.",
    ]
    answer = f"$f$ est localement {sens} au voisinage de $x_0={x0}$ (car $f'({x0})$ est {'positif' if val>0 else 'négatif'})."
    hint = "Le signe de f'(x0) donne directement le sens de variation local : positif → croissante, négatif → décroissante."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


# ── 5. Vérifier si une droite donnée est tangente à Cf ───────────────────────

def _gen_verifier_tangente(rng):
    a, b, c = _rand_poly2(rng)
    x0 = _small(rng, -5, 5)
    f = a * x**2 + b * x + c
    fprime = diff(f, x)
    m_true = fprime.subs(x, x0)
    p_true = f.subs(x, x0)
    true_line = expand(m_true * (x - x0) + p_true)
    is_correct = rng.random() < 0.5
    if is_correct:
        proposed = true_line
    else:
        erreur = rng.choice(["mauvaise_pente", "ne_passe_pas_par_le_point"])
        if erreur == "mauvaise_pente":
            wrong_m = m_true + rng.choice([2, -2, 3, -3])
            proposed = expand(wrong_m * (x - x0) + p_true)
        else:
            proposed = expand(true_line + rng.choice([1, -1, 2, -2]))
    enonce = (
        f"Soit $f$ la fonction définie sur $\\mathbb{{R}}$ par $f(x) = {_fmt_poly2(a, b, c)}$. "
        f"La droite d'équation $y = {latex(proposed)}$ est-elle tangente à la courbe représentative de $f$ "
        f"au point d'abscisse $x_0={x0}$ ? Justifier."
    )
    steps = [
        f"Étape 1 — On calcule la VRAIE tangente en $x_0={x0}$ : $f'({x0})={latex(m_true)}$, $f({x0})={latex(p_true)}$, "
        f"donc $y={latex(true_line)}$.",
        "Étape 2 — On compare cette équation à celle proposée.",
    ]
    if is_correct:
        answer = f"Vrai : la droite $y={latex(proposed)}$ est bien la tangente en $x_0={x0}$."
    else:
        answer = f"Faux : la vraie tangente en $x_0={x0}$ est $y={latex(true_line)}$, différente de celle proposée."
    hint = "Calculer soi-même f'(x0) et f(x0) pour retrouver la vraie équation de la tangente, puis comparer terme à terme (coefficient directeur ET ordonnée à l'origine)."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


# ── 6. Problème contextualisé (vitesse instantanée) ──────────────────────────

def _gen_contexte_vitesse(rng):
    a = _nz(rng, -5, 5)
    b = _small(rng, -8, 8)
    c = _small(rng, 0, 20)
    t0 = rng.randint(1, 8)
    s = a * t**2 + b * t + c
    sprime = diff(s, t)
    v_t0 = sprime.subs(t, t0)
    contexte = rng.choice([
        ("un mobile se déplaçant sur un axe", "s(t)", "sa position (en mètres)", "sa vitesse instantanée"),
        ("une voiture sur une route rectiligne", "s(t)", "la distance parcourue (en mètres)", "sa vitesse instantanée"),
    ])
    objet, s_name, quoi, vitesse_mot = contexte
    enonce = (
        f"On étudie {objet}. On note $s(t) = {latex(s)}$ {quoi} à l'instant $t$ (en secondes). "
        f"Déterminer {vitesse_mot} à l'instant $t={t0}$ s, c'est-à-dire $s'({t0})$."
    )
    steps = [
        f"Étape 1 — La vitesse instantanée est donnée par la dérivée de la position : $s'(t) = {latex(sprime)}$.",
        f"Étape 2 — $s'({t0}) = {latex(v_t0)}$ m/s.",
    ]
    answer = f"$s'({t0}) = {latex(v_t0)}$ m/s."
    hint = "La vitesse instantanée à l'instant t0 est le nombre dérivé s'(t0) de la fonction position."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


# ── 7. Retrouver un paramètre de f à partir de sa tangente ───────────────────

def _gen_parametre_retrouver(rng):
    a = _nz(rng, -4, 4)
    c = _small(rng, -6, 6)
    b_true = _small(rng, -6, 6)
    x0 = _small(rng, -5, 5)
    b_sym = symbols("b")
    f_sym = a * x**2 + b_sym * x + c
    fprime_sym = diff(f_sym, x)
    m_true = fprime_sym.subs(x, x0).subs(b_sym, b_true)
    eq = Eq(fprime_sym.subs(x, x0), m_true)
    sol = solve(eq, b_sym)
    if not sol or sol[0] != b_true:
        return None
    c_term = f"+ {c}" if c >= 0 else f"- {abs(c)}"
    enonce = (
        f"Soit $f$ la fonction définie sur $\\mathbb{{R}}$ par $f(x) = {latex(a*x**2)} + bx\\ {c_term}$ où $b$ est un "
        f"réel inconnu. On sait que la tangente à la courbe de $f$ au point d'abscisse $x_0={x0}$ a pour "
        f"coefficient directeur ${latex(m_true)}$. Déterminer la valeur de $b$."
    )
    steps = [
        f"Étape 1 — $f'(x) = {latex(fprime_sym)}$, donc $f'({x0}) = {latex(fprime_sym.subs(x, x0))}$.",
        f"Étape 2 — On résout $f'({x0}) = {latex(m_true)}$, soit ${latex(eq)}$.",
        f"Étape 3 — $b = {latex(sol[0])}$.",
    ]
    answer = f"$b = {latex(sol[0])}$"
    hint = "Exprimer f'(x0) en fonction du paramètre inconnu, puis résoudre l'équation f'(x0) = coefficient directeur donné."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


# ── 8. Détecter/corriger une erreur ──────────────────────────────────────────

def _gen_erreur_calcul(rng):
    a, b, c = _rand_poly2(rng)
    x0 = _small(rng, -5, 5)
    f = a * x**2 + b * x + c
    fprime = diff(f, x)
    m_true = fprime.subs(x, x0)
    p_true = f.subs(x, x0)
    true_line = expand(m_true * (x - x0) + p_true)
    # Erreur classique : utiliser f'(x0) comme ordonnée à l'origine au lieu
    # de calculer f(x0) séparément (confusion entre les deux quantités).
    wrong_line = expand(m_true * (x - x0) + m_true)
    if wrong_line == true_line:
        return None
    enonce = (
        f"Soit $f$ la fonction définie sur $\\mathbb{{R}}$ par $f(x) = {_fmt_poly2(a, b, c)}$. "
        f"Un élève détermine la tangente en $x_0={x0}$ ainsi : \"$f'({x0})={latex(m_true)}$, donc "
        f"$y = {latex(m_true)}(x-{x0}) + {latex(m_true)}$\" (il a utilisé $f'({x0})$ à la place de $f({x0})$ "
        "pour l'ordonnée à l'origine du calcul). Identifier son erreur et donner l'équation correcte."
    )
    steps = [
        f"Étape 1 — Le calcul de $f'({x0})={latex(m_true)}$ est correct.",
        f"Étape 2 — L'erreur est d'avoir réutilisé $f'({x0})$ à la place de $f({x0})$ : ici $f({x0})={latex(p_true)}$.",
        f"Étape 3 — L'équation correcte est $y = f'({x0})(x-{x0})+f({x0}) = {latex(true_line)}$.",
    ]
    answer = f"Confusion entre $f'({x0})$ et $f({x0})$ ; l'équation correcte est $y = {latex(true_line)}$."
    hint = "Vérifier que l'ordonnée à l'origine du calcul utilise bien f(x0), pas f'(x0) — ce sont deux quantités différentes."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


# ── 9. Défi : tangente parallèle à une droite donnée ─────────────────────────

def _gen_defi_tangente_parallele(rng):
    a = _nz(rng, -3, 3)
    b = _small(rng, -4, 4)
    cc = _small(rng, -3, 3)
    d = _small(rng, -6, 6)
    f = a * x**3 + b * x**2 + cc * x + d
    fprime = diff(f, x)
    m = _small(rng, -12, 12)
    sols = solve(Eq(fprime, m), x)
    real_sols = [s for s in sols if s.is_real]
    if not real_sols:
        return None
    sols_latex = ", ".join(f"$x = {latex(s)}$" for s in real_sols)
    enonce = (
        f"Soit $f$ la fonction définie sur $\\mathbb{{R}}$ par $f(x) = {latex(f)}$ et $D$ la droite d'équation "
        f"$y = {m}x + 7$. Déterminer, s'il en existe, le ou les points de la courbe de $f$ où la tangente est "
        f"parallèle à $D$."
    )
    steps = [
        f"Étape 1 — Deux droites sont parallèles si et seulement si elles ont le même coefficient directeur : "
        f"il faut $f'(x) = {m}$.",
        f"Étape 2 — $f'(x) = {latex(fprime)}$, donc on résout ${latex(fprime)} = {m}$.",
        f"Étape 3 — Cette équation admet {'pour solution' if len(real_sols)==1 else 'pour solutions'} "
        f"{sols_latex}.",
    ]
    answer = f"La tangente est parallèle à $D$ aux points d'abscisse {sols_latex}."
    hint = "Deux droites sont parallèles ssi leurs coefficients directeurs sont égaux : résoudre f'(x) = coefficient directeur de D."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


@dataclass(frozen=True)
class Family:
    id: str
    level: int
    label: str
    generate: Callable[[random.Random], Optional[dict]]
    structure_hint: str
    rule_hint: str


FAMILY_BASE_SCORE: dict[str, float] = {
    "taux_variation": 1.0,
    "tangente": 1.2,
    "limite_derivee_explicite": 2.0,
    "signe_interpretation": 2.3,
    "verifier_tangente": 3.0,
    "contexte_vitesse": 3.3,
    "parametre_retrouver": 4.0,
    "erreur_calcul": 4.3,
    "defi_tangente_parallele": 5.0,
}

FAMILIES: tuple[Family, ...] = (
    Family("taux_variation", 1, "Taux de variation → nombre dérivé", _gen_taux_variation,
           "un taux de variation à exprimer en fonction de h", "développer, factoriser par h, faire tendre h vers 0"),
    Family("tangente", 1, "Équation de la tangente", _gen_tangente,
           "une tangente à déterminer en un point donné", "y = f'(x0)(x-x0) + f(x0)"),
    Family("limite_derivee_explicite", 2, "Nombre dérivé via l'expression de la limite", _gen_limite_derivee_explicite,
           "une limite à écrire puis calculer", "f'(a) = lim_{h→0} (f(a+h)-f(a))/h"),
    Family("signe_interpretation", 2, "Interprétation du signe de f'(a)", _gen_signe_interpretation,
           "le signe d'un nombre dérivé déjà connu", "signe positif → croissante, négatif → décroissante"),
    Family("verifier_tangente", 3, "Vérifier si une droite est tangente", _gen_verifier_tangente,
           "une droite proposée comme tangente", "recalculer f'(x0) et f(x0) puis comparer"),
    Family("contexte_vitesse", 3, "Problème contextualisé (vitesse instantanée)", _gen_contexte_vitesse,
           "une position en fonction du temps", "la vitesse instantanée est la dérivée de la position"),
    Family("parametre_retrouver", 4, "Retrouver un paramètre depuis la tangente", _gen_parametre_retrouver,
           "un coefficient inconnu de f et un coefficient directeur donné", "résoudre f'(x0) = coefficient directeur donné"),
    Family("erreur_calcul", 4, "Détecter/corriger une erreur", _gen_erreur_calcul,
           "une confusion entre f(x0) et f'(x0)", "comparer chaque étape à la méthode correcte"),
    Family("defi_tangente_parallele", 5, "Défi : tangente parallèle à une droite", _gen_defi_tangente_parallele,
           "une fonction cubique et une droite de référence", "résoudre f'(x) = coefficient directeur de la droite"),
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


def generate_pool(per_family: int = 12, seed: int = 20260824) -> list[dict]:
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
