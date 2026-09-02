"""Génération symbolique d'exercices de trigonométrie (Première, Chapitre_6 :
"Repérage sur le cercle trigonométrique", "Coordonnées d'un point du cercle
trigonométrique", "Fonctions cosinus et sinus").

Même principe que webapp/exercise_generator/second_degre.py (patron simple) :
chaque famille est un vrai type de raisonnement, toute valeur annoncée est
calculée/vérifiée par sympy (jamais tapée "en dur" sans contrôle), et la
difficulté affichée vient d'un score FIXE par famille (profondeur de
raisonnement du type de question, pas taille des nombres tirés).

Mission "rééquilibrage additif" (2026-09-01) : Chapitre_6 à Chapitre_10 de
Première n'avaient aucun générateur symbolique (voir registry.py) — leur
volume était plafonné à la banque curée. Ce module est le premier des 5
générateurs créés pour combler ce vide, en réutilisant exactement le même
contrat que les modules existants (Family/generate_one/generate_pool).
"""
import random
from dataclasses import dataclass
from typing import Callable, Optional

import sympy
from sympy import Rational, cos, latex, pi, sin, sqrt, symbols

CHAPTER_ID = "Chapitre_6"
NOTION_REPERAGE = "Repérage sur le cercle trigonométrique"
NOTION_COORDONNEES = "Coordonnées d'un point du cercle trigonométrique"
NOTION_FONCTIONS = "Fonctions cosinus et sinus"

# Distinct de tous les offsets déjà utilisés par les modules Première
# (900_000/910_000/920_000/930_000/940_000/950_000) — voir
# tools/generate_derivative_exercises.py qui liste tous les offsets et
# garantit l'absence de collision d'id entre pools générés.
GENERATED_ID_OFFSET = 960_000

LEVEL_META = {
    1: {"emoji": "🟢", "label": "Niveau 1 — Fondamental"},
    2: {"emoji": "🟡", "label": "Niveau 2 — Intermédiaire"},
    3: {"emoji": "🟠", "label": "Niveau 3 — Avancé"},
    4: {"emoji": "🔴", "label": "Niveau 4 — Difficile"},
    5: {"emoji": "🟣", "label": "Niveau 5 — Défi"},
}

# Table des angles remarquables du cercle trigonométrique (valeurs exactes,
# jamais approchées) — (angle en LaTeX, valeur sympy, cos exact, sin exact).
_ANGLES = [
    ("0", sympy.Integer(0), sympy.Integer(1), sympy.Integer(0)),
    ("\\dfrac{\\pi}{6}", pi / 6, sqrt(3) / 2, Rational(1, 2)),
    ("\\dfrac{\\pi}{4}", pi / 4, sqrt(2) / 2, sqrt(2) / 2),
    ("\\dfrac{\\pi}{3}", pi / 3, Rational(1, 2), sqrt(3) / 2),
    ("\\dfrac{\\pi}{2}", pi / 2, sympy.Integer(0), sympy.Integer(1)),
    ("\\dfrac{2\\pi}{3}", 2 * pi / 3, Rational(-1, 2), sqrt(3) / 2),
    ("\\dfrac{3\\pi}{4}", 3 * pi / 4, -sqrt(2) / 2, sqrt(2) / 2),
    ("\\dfrac{5\\pi}{6}", 5 * pi / 6, -sqrt(3) / 2, Rational(1, 2)),
]


def _nz(rng: random.Random, lo: int, hi: int) -> int:
    choices = [n for n in range(lo, hi + 1) if n != 0]
    return rng.choice(choices)


@dataclass(frozen=True)
class Family:
    id: str
    level: int
    label: str
    notion: str
    generate: Callable[[random.Random], Optional[dict]]
    structure_hint: str
    rule_hint: str


# ── Famille 1 — Angle associé : cos(π - θ) = -cos(θ) ───────────────────────

def _gen_angle_associe_cos(rng: random.Random) -> Optional[dict]:
    label, theta, c, s = rng.choice(_ANGLES[1:])
    variante = rng.choice(["pi_moins", "pi_plus", "oppose"])
    if variante == "pi_moins":
        expr_latex, target, regle = f"\\pi - {label}", -c, "$\\cos(\\pi-\\theta) = -\\cos(\\theta)$"
    elif variante == "pi_plus":
        expr_latex, target, regle = f"\\pi + {label}", -c, "$\\cos(\\pi+\\theta) = -\\cos(\\theta)$"
    else:
        expr_latex, target, regle = f"-{label}", c, "$\\cos(-\\theta) = \\cos(\\theta)$"
    target = sympy.simplify(target)
    enonce = (
        f"Sachant que $\\cos\\left({label}\\right) = {latex(c)}$, déterminer "
        f"$\\cos\\left({expr_latex}\\right)$ en utilisant les angles associés."
    )
    answer = f"$\\cos\\left({expr_latex}\\right) = {latex(target)}$"
    steps = [
        f"Étape 1 — On reconnaît un angle associé à ${label}$ : ${expr_latex}$.",
        f"Étape 2 — La formule des angles associés donne {regle}.",
        f"Étape 3 — Avec $\\cos\\left({label}\\right) = {latex(c)}$, on obtient {answer}.",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_REPERAGE}


# ── Famille 2 — Angle associé : sin ────────────────────────────────────────

def _gen_angle_associe_sin(rng: random.Random) -> Optional[dict]:
    label, theta, c, s = rng.choice(_ANGLES[1:])
    variante = rng.choice(["pi_moins", "oppose", "pi_plus"])
    if variante == "pi_moins":
        expr_latex, target, regle = f"\\pi - {label}", s, "$\\sin(\\pi-\\theta) = \\sin(\\theta)$"
    elif variante == "pi_plus":
        expr_latex, target, regle = f"\\pi + {label}", -s, "$\\sin(\\pi+\\theta) = -\\sin(\\theta)$"
    else:
        expr_latex, target, regle = f"-{label}", -s, "$\\sin(-\\theta) = -\\sin(\\theta)$"
    target = sympy.simplify(target)
    enonce = (
        f"Sachant que $\\sin\\left({label}\\right) = {latex(s)}$, déterminer "
        f"$\\sin\\left({expr_latex}\\right)$ en utilisant les angles associés."
    )
    answer = f"$\\sin\\left({expr_latex}\\right) = {latex(target)}$"
    steps = [
        f"Étape 1 — On reconnaît un angle associé à ${label}$ : ${expr_latex}$.",
        f"Étape 2 — La formule des angles associés donne {regle}.",
        f"Étape 3 — Avec $\\sin\\left({label}\\right) = {latex(s)}$, on obtient {answer}.",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_REPERAGE}


# ── Famille 3 — Résoudre cos(x) = a sur [-π ; π] ───────────────────────────

def _gen_equation_cos(rng: random.Random) -> Optional[dict]:
    label, theta, c, s = rng.choice(_ANGLES[1:-1])  # exclut 5π/6 pour garder -θ dans ]-π;π]
    solutions = sorted({theta, -theta}, key=lambda t: float(t))
    sol_latex = " \\text{ ou } ".join(f"x = {('-' if t < 0 else '') + label}" for t in solutions)
    enonce = (
        f"Résoudre dans $]-\\pi\\,;\\,\\pi]$ l'équation $\\cos(x) = {latex(c)}$."
    )
    answer = f"$S = \\left\\{{-{label}\\,;\\,{label}\\right\\}}$"
    steps = [
        f"Étape 1 — On reconnaît la valeur remarquable $\\cos\\left({label}\\right) = {latex(c)}$.",
        f"Étape 2 — $\\cos(x) = \\cos\\left({label}\\right)$ équivaut à $x = {label}$ ou $x = -{label}$ "
        "(modulo $2\\pi$), car le cosinus est une fonction paire.",
        f"Étape 3 — Les deux solutions appartiennent à $]-\\pi\\,;\\,\\pi]$, donc {answer}.",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_FONCTIONS}


# ── Famille 4 — Résoudre sin(x) = a sur [-π ; π] ───────────────────────────

def _gen_equation_sin(rng: random.Random) -> Optional[dict]:
    label, theta, c, s = rng.choice(_ANGLES[1:4])  # angles aigus, pour un π-θ propre dans ]-π;π]
    autre_label = f"\\pi - {label}" if label != "\\dfrac{\\pi}{2}" else label
    autre_val = sympy.simplify(sympy.pi - theta) if label != "\\dfrac{\\pi}{2}" else theta
    if autre_val == theta:
        sol_latex = f"$S = \\left\\{{{label}\\right\\}}$"
        steps_sol = f"Étape 3 — Seule $x = {label}$ convient : {sol_latex}."
    else:
        sol_latex = f"$S = \\left\\{{{label}\\,;\\,{autre_label}\\right\\}}$"
        steps_sol = f"Étape 3 — Les deux solutions appartiennent à $]-\\pi\\,;\\,\\pi]$ : {sol_latex}."
    enonce = f"Résoudre dans $]-\\pi\\,;\\,\\pi]$ l'équation $\\sin(x) = {latex(s)}$."
    steps = [
        f"Étape 1 — On reconnaît la valeur remarquable $\\sin\\left({label}\\right) = {latex(s)}$.",
        f"Étape 2 — $\\sin(x) = \\sin\\left({label}\\right)$ équivaut à $x = {label}$ ou "
        f"$x = \\pi - {label}$ (modulo $2\\pi$).",
        steps_sol,
    ]
    return {"enonce": enonce, "answer": sol_latex, "steps": steps, "notion": NOTION_FONCTIONS}


# ── Famille 5 — Identité cos²+sin²=1, retrouver l'autre valeur ────────────

def _gen_identite_pythagore(rng: random.Random) -> Optional[dict]:
    label, theta, c, s = rng.choice(_ANGLES[1:])
    connu = rng.choice(["cos", "sin"])
    quadrant_positif = rng.random() < 0.5
    if connu == "cos":
        known_sym, known_val = "\\cos", c
        target_sym = "\\sin"
        target_val = s if quadrant_positif else -s
    else:
        known_sym, known_val = "\\sin", s
        target_sym = "\\cos"
        target_val = c if quadrant_positif else -c
    target_val = sympy.simplify(target_val)
    sign_word = "positif" if quadrant_positif else "négatif"
    enonce = (
        f"Soit $\\theta$ un réel tel que ${known_sym}(\\theta) = {latex(known_val)}$ et "
        f"${target_sym}(\\theta)$ est {sign_word}. Déterminer ${target_sym}(\\theta)$."
    )
    answer = f"${target_sym}(\\theta) = {latex(target_val)}$"
    steps = [
        f"Étape 1 — On utilise l'identité fondamentale $\\cos^2(\\theta) + \\sin^2(\\theta) = 1$.",
        f"Étape 2 — ${known_sym}(\\theta) = {latex(known_val)}$ donne "
        f"${target_sym}^2(\\theta) = 1 - \\left({latex(known_val)}\\right)^2 = {latex(sympy.simplify(1 - known_val**2))}$.",
        f"Étape 3 — Donc ${target_sym}(\\theta) = \\pm{latex(sympy.simplify(abs(target_val)))}$ ; "
        f"comme ${target_sym}(\\theta)$ est {sign_word}, {answer}.",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_FONCTIONS}


# ── Famille 6 — Signe de cos/sin selon le quadrant ─────────────────────────

_QUADRANTS = [
    ("\\left]0\\,;\\,\\dfrac{\\pi}{2}\\right[", True, True),
    ("\\left]\\dfrac{\\pi}{2}\\,;\\,\\pi\\right[", False, True),
    ("\\left]-\\pi\\,;\\,-\\dfrac{\\pi}{2}\\right[", False, False),
    ("\\left]-\\dfrac{\\pi}{2}\\,;\\,0\\right[", True, False),
]


def _gen_signe_quadrant(rng: random.Random) -> Optional[dict]:
    quadrant_latex, cos_pos, sin_pos = rng.choice(_QUADRANTS)
    fonction = rng.choice(["cos", "sin"])
    is_pos = cos_pos if fonction == "cos" else sin_pos
    fonction_sym = "\\cos" if fonction == "cos" else "\\sin"
    signe_mot = "positif" if is_pos else "négatif"
    enonce = f"Soit $\\theta \\in {quadrant_latex}$. Quel est le signe de ${fonction_sym}(\\theta)$ ? Justifier."
    answer = f"${fonction_sym}(\\theta)$ est {signe_mot} sur cet intervalle."
    steps = [
        f"Étape 1 — On place l'intervalle ${quadrant_latex}$ sur le cercle trigonométrique.",
        f"Étape 2 — Sur ce quadrant, l'abscisse (cosinus) est "
        f"{'positive' if cos_pos else 'négative'} et l'ordonnée (sinus) est "
        f"{'positive' if sin_pos else 'négative'}.",
        f"Étape 3 — Conclusion : {answer}",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_REPERAGE}


# ── Famille 7 — Conversion degrés ↔ radians ────────────────────────────────

_DEGRE_VERS_FRACTION_PI = [
    (30, Rational(1, 6)), (45, Rational(1, 4)), (60, Rational(1, 3)), (90, Rational(1, 2)),
    (120, Rational(2, 3)), (135, Rational(3, 4)), (150, Rational(5, 6)), (180, sympy.Integer(1)),
]


def _gen_conversion(rng: random.Random) -> Optional[dict]:
    degres, frac = rng.choice(_DEGRE_VERS_FRACTION_PI)
    sens = rng.choice(["deg_vers_rad", "rad_vers_deg"])
    if sens == "deg_vers_rad":
        rad_latex = f"{latex(frac)}\\pi" if frac != 1 else "\\pi"
        enonce = f"Convertir un angle de ${degres}\\degree$ en radians."
        answer = f"${degres}\\degree = {rad_latex}$ rad"
        steps = [
            f"Étape 1 — On utilise la proportionnalité $180\\degree \\leftrightarrow \\pi$ rad.",
            f"Étape 2 — ${degres}\\degree = \\dfrac{{{degres}}}{{180}}\\pi = {rad_latex}$ rad.",
        ]
    else:
        rad_latex = f"{latex(frac)}\\pi" if frac != 1 else "\\pi"
        enonce = f"Convertir un angle de ${rad_latex}$ rad en degrés."
        answer = f"${rad_latex}$ rad $= {degres}\\degree$"
        steps = [
            f"Étape 1 — On utilise la proportionnalité $\\pi$ rad $\\leftrightarrow 180\\degree$.",
            f"Étape 2 — ${rad_latex}$ rad $= {latex(frac)} \\times 180\\degree = {degres}\\degree$.",
        ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_REPERAGE}


# ── Famille 8 — Combinaison linéaire a·cos(θ)+b·sin(θ) pour un angle connu ─
# Espace combinatoire large (8 angles × ~8×8 couples (a,b)) — contrairement
# aux familles 1-7, purement discrètes (angle + variante fixe), nécessaire
# pour produire un volume réellement diversifié sans jamais répéter le même
# énoncé (voir mission "rééquilibrage additif").

def _gen_combinaison_lineaire(rng: random.Random) -> Optional[dict]:
    label, theta, c, s = rng.choice(_ANGLES[1:])
    a = _nz(rng, -4, 4)
    b = _nz(rng, -4, 4)
    valeur = sympy.simplify(a * c + b * s)
    a_txt = f"{a}" if a != 1 else ""
    a_txt = f"-{-a}" if a == -1 else a_txt if a != 1 else "1"
    b_txt = str(abs(b))
    signe_b = "+" if b > 0 else "-"
    expr_latex = f"{a}\\cos\\left({label}\\right) {signe_b} {b_txt}\\sin\\left({label}\\right)"
    enonce = f"Calculer $A = {expr_latex}$ (valeur exacte)."
    answer = f"$A = {latex(valeur)}$"
    steps = [
        f"Étape 1 — On utilise les valeurs exactes $\\cos\\left({label}\\right) = {latex(c)}$ et "
        f"$\\sin\\left({label}\\right) = {latex(s)}$.",
        f"Étape 2 — $A = {a} \\times {latex(c)} {signe_b} {b_txt} \\times {latex(s)}$.",
        f"Étape 3 — Après simplification, {answer}.",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_FONCTIONS}


FAMILY_BASE_SCORE: dict[str, float] = {
    "conversion": 1.0,
    "signe_quadrant": 1.4,
    "angle_associe_cos": 2.0,
    "angle_associe_sin": 2.2,
    "combinaison_lineaire": 2.6,
    "identite_pythagore": 3.0,
    "equation_cos": 3.4,
    "equation_sin": 3.8,
}

FAMILIES: tuple[Family, ...] = (
    Family("conversion", 1, "Conversion degrés / radians", NOTION_REPERAGE, _gen_conversion,
           "un angle à convertir", "utiliser la proportionnalité 180° ↔ π rad"),
    Family("signe_quadrant", 1, "Signe de cos/sin selon le quadrant", NOTION_REPERAGE, _gen_signe_quadrant,
           "un intervalle du cercle trigonométrique", "lire le signe de l'abscisse (cos) et de l'ordonnée (sin)"),
    Family("angle_associe_cos", 2, "Angles associés — cosinus", NOTION_REPERAGE, _gen_angle_associe_cos,
           "un angle associé à un angle remarquable", "cos(π−θ)=−cos(θ), cos(π+θ)=−cos(θ), cos(−θ)=cos(θ)"),
    Family("angle_associe_sin", 2, "Angles associés — sinus", NOTION_REPERAGE, _gen_angle_associe_sin,
           "un angle associé à un angle remarquable", "sin(π−θ)=sin(θ), sin(π+θ)=−sin(θ), sin(−θ)=−sin(θ)"),
    Family("combinaison_lineaire", 3, "Combinaison linéaire de cos/sin", NOTION_FONCTIONS, _gen_combinaison_lineaire,
           "une expression a·cos(θ)+b·sin(θ) pour un angle remarquable", "remplacer cos(θ) et sin(θ) par leurs valeurs exactes puis calculer"),
    Family("identite_pythagore", 3, "Identité cos²+sin²=1", NOTION_FONCTIONS, _gen_identite_pythagore,
           "une valeur de cos ou sin connue, l'autre à retrouver", "cos²(θ)+sin²(θ)=1, puis choisir le signe selon le quadrant"),
    Family("equation_cos", 3, "Résoudre cos(x)=a", NOTION_FONCTIONS, _gen_equation_cos,
           "une équation en cosinus sur un intervalle", "cos(x)=cos(θ) ⟺ x=θ ou x=−θ (mod 2π)"),
    Family("equation_sin", 4, "Résoudre sin(x)=a", NOTION_FONCTIONS, _gen_equation_sin,
           "une équation en sinus sur un intervalle", "sin(x)=sin(θ) ⟺ x=θ ou x=π−θ (mod 2π)"),
)

FAMILIES_BY_ID: dict[str, Family] = {f.id: f for f in FAMILIES}


def _difficulty_bucket_from_score(score: float) -> int:
    if score <= 1.2:
        return 1
    if score <= 2.1:
        return 2
    if score <= 3.2:
        return 3
    if score <= 3.6:
        return 4
    return 5


def build_exercise(family: Family, rng: random.Random) -> Optional[dict]:
    notes = family.generate(rng)
    if notes is None:
        return None
    score = FAMILY_BASE_SCORE[family.id]
    real_level = _difficulty_bucket_from_score(score)
    return {
        "enonce": notes["enonce"],
        "answer": notes["answer"],
        "hint": f"Reconnais {family.structure_hint} : {family.rule_hint}.",
        "solution_steps": notes["steps"],
        "chapter_id": CHAPTER_ID,
        "notion": notes["notion"],
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


def generate_pool(per_family: int = 12, seed: int = 20260901) -> list[dict]:
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
    for i, ex in enumerate(pool):
        ex["id"] = GENERATED_ID_OFFSET + i
    return pool


# ── Familles supplémentaires — mission "diversification structurelle"
# (2026-09-02) : combinaison_lineaire représentait à elle seule 47% du
# chapitre (205/438) avec une seule structure ("A = a·cos(θ)+b·sin(θ) pour
# UN angle", 98% de quasi-doublon). Nouvelles familles : deux angles
# distincts combinés (recall de deux valeurs différentes) et une expression
# quadratique liée à l'identité de Pythagore — jamais mélangées à
# FAMILIES/generate_pool (baseline figée).

def _gen_combinaison_deux_angles(rng: random.Random) -> Optional[dict]:
    """A = a·cos(θ1) + b·cos(θ2) pour DEUX angles remarquables DIFFÉRENTS —
    structure différente de _gen_combinaison_lineaire (un seul angle, cos et
    sin du MÊME angle)."""
    (label1, theta1, c1, s1), (label2, theta2, c2, s2) = rng.sample(_ANGLES[1:], 2)
    a = _nz(rng, -4, 4)
    b = _nz(rng, -4, 4)
    valeur = sympy.simplify(a * c1 + b * s2)
    a_txt = "-" if a == -1 else ("" if a == 1 else str(a))
    b_txt = str(abs(b)) if abs(b) != 1 else ""
    signe_b = "+" if b > 0 else "-"
    expr_latex = f"{a_txt}\\cos\\left({label1}\\right) {signe_b} {b_txt}\\sin\\left({label2}\\right)"
    enonce = f"Calculer $A = {expr_latex}$ (valeur exacte)."
    answer = f"$A = {latex(valeur)}$"
    steps = [
        f"Étape 1 — On utilise $\\cos\\left({label1}\\right) = {latex(c1)}$ et $\\sin\\left({label2}\\right) = {latex(s2)}$ "
        "(deux angles différents, donc deux valeurs à retenir séparément).",
        f"Étape 2 — $A = {a} \\times {latex(c1)} {signe_b} {abs(b)} \\times {latex(s2)}$.",
        f"Étape 3 — Après réduction au même dénominateur si besoin, {answer}.",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_FONCTIONS}


def _gen_expression_carre(rng: random.Random) -> Optional[dict]:
    """Expression quadratique $\\cos^2(\\theta) - \\sin^2(\\theta)$ — utilise
    une identité (liée à $\\cos(2\\theta)$), structure différente de
    _gen_combinaison_lineaire (linéaire, pas de carré)."""
    label, theta, c, s = rng.choice(_ANGLES[1:])
    valeur = sympy.simplify(c ** 2 - s ** 2)
    enonce = f"Calculer $B = \\cos^2\\left({label}\\right) - \\sin^2\\left({label}\\right)$ (valeur exacte)."
    answer = f"$B = {latex(valeur)}$"
    steps = [
        f"Étape 1 — On utilise $\\cos\\left({label}\\right) = {latex(c)}$ et $\\sin\\left({label}\\right) = {latex(s)}$.",
        f"Étape 2 — $B = \\left({latex(c)}\\right)^2 - \\left({latex(s)}\\right)^2$.",
        f"Étape 3 — Après simplification, {answer} (cette quantité est égale à $\\cos(2\\times{label})$).",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_FONCTIONS}


EXTRA_FAMILY_BASE_SCORE: dict[str, float] = {
    "combinaison_deux_angles": 2.8,
    "expression_carre": 3.2,
}

EXTRA_FAMILIES: tuple[Family, ...] = (
    Family("combinaison_deux_angles", 3, "Combinaison de deux angles différents", NOTION_FONCTIONS,
           _gen_combinaison_deux_angles, "deux angles remarquables distincts dans la même expression",
           "remplacer chaque cos/sin par la valeur exacte de SON angle avant de combiner"),
    Family("expression_carre", 3, "Expression quadratique cos²−sin²", NOTION_FONCTIONS, _gen_expression_carre,
           "une différence de carrés de cosinus et sinus du même angle",
           "élever au carré chaque valeur exacte puis soustraire"),
)

EXTRA_FAMILIES_BY_ID: dict[str, Family] = {f.id: f for f in EXTRA_FAMILIES}


def _build_extra_exercise(family: Family, rng: random.Random) -> Optional[dict]:
    notes = family.generate(rng)
    if notes is None:
        return None
    score = EXTRA_FAMILY_BASE_SCORE[family.id]
    real_level = _difficulty_bucket_from_score(score)
    return {
        "enonce": notes["enonce"],
        "answer": notes["answer"],
        "hint": f"Reconnais {family.structure_hint} : {family.rule_hint}.",
        "solution_steps": notes["steps"],
        "chapter_id": CHAPTER_ID,
        "notion": notes["notion"],
        "difficulty": real_level,
        "difficulty_label": LEVEL_META[real_level]["label"],
        "difficulty_emoji": LEVEL_META[real_level]["emoji"],
        "family": family.id,
        "family_label": family.label,
        "declared_level": family.level,
        "complexity_score": score,
        "source": "generated",
    }


def generate_extra_pool(per_family: int = 12, seed: int = 20260945) -> list[dict]:
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
