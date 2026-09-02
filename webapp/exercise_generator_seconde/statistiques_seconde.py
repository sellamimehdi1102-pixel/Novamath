"""Génération symbolique d'exercices de statistiques descriptives (Seconde,
Chapitre_11 : moyenne pondérée, linéarité de la moyenne, écart-type,
quartiles et écart interquartile).

Mission "audit final et rééquilibrage additif global" (2026-09-02) :
Chapitre_11 (162 exercices, 4 notions) n'avait AUCUN générateur — banque
purement curée. Toute moyenne/variance/écart-type/quartile annoncé est
recalculé exactement (`fractions.Fraction`, `sympy.sqrt`) à partir de la
série de données — jamais tapé "en dur". Les quartiles utilisent la méthode
des rangs (arrondi à l'entier supérieur) enseignée en Seconde en France.
"""
import math
import random
from dataclasses import dataclass
from fractions import Fraction
from typing import Callable, Optional

from sympy import Rational, latex, sqrt

CHAPTER_ID = "Chapitre_11"

GENERATED_ID_OFFSET = 560_000

LEVEL_META = {
    1: {"emoji": "🟢", "label": "Niveau 1 — Fondamental"},
    2: {"emoji": "🟡", "label": "Niveau 2 — Intermédiaire"},
    3: {"emoji": "🟠", "label": "Niveau 3 — Avancé"},
    4: {"emoji": "🔴", "label": "Niveau 4 — Difficile"},
}


def _fmt(v) -> str:
    if isinstance(v, Fraction):
        if v.denominator == 1:
            return str(v.numerator)
        sign = "-" if v.numerator < 0 else ""
        return f"{sign}\\dfrac{{{abs(v.numerator)}}}{{{v.denominator}}}"
    return str(v)


# ── 1. Moyenne pondérée ───────────────────────────────────────────────────

def _gen_moyenne_ponderee(rng: random.Random) -> Optional[dict]:
    n = rng.choice([3, 4])
    valeurs = rng.sample(range(2, 20), n)
    effectifs = [rng.randint(1, 8) for _ in range(n)]
    total_effectif = sum(effectifs)
    somme = sum(v * e for v, e in zip(valeurs, effectifs))
    moyenne = Fraction(somme, total_effectif)
    lignes = ", ".join(f"${v}$ (effectif ${e}$)" for v, e in zip(valeurs, effectifs))
    enonce = (
        f"Une série statistique a pour valeurs {lignes}. Calculer la moyenne de cette série."
    )
    detail = " + ".join(f"{v}\\times{e}" for v, e in zip(valeurs, effectifs))
    steps = [
        f"Étape 1 — Effectif total : ${' + '.join(map(str, effectifs))} = {total_effectif}$.",
        f"Étape 2 — Moyenne $= \\dfrac{{{detail}}}{{{total_effectif}}} = \\dfrac{{{somme}}}{{{total_effectif}}} = {_fmt(moyenne)}$.",
    ]
    answer = f"Moyenne $= {_fmt(moyenne)}$"
    hint = "La moyenne pondérée est la somme des (valeur × effectif) divisée par l'effectif total."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint,
            "notion": "Moyenne"}


# ── 2. Linéarité de la moyenne (transformation affine des données) ─────────

def _gen_linearite_moyenne(rng: random.Random) -> Optional[dict]:
    moyenne_init = Fraction(rng.randint(20, 400), rng.choice([1, 1, 2, 4]))
    a = rng.choice([2, 3, Fraction(1, 2), -1, 5])
    a = Fraction(a) if not isinstance(a, Fraction) else a
    b = rng.randint(-10, 10)
    nouvelle_moyenne = a * moyenne_init + b
    a_txt = "-" if a == -1 else _fmt(a)
    b_txt = f"+ {b}" if b > 0 else (f"- {abs(b)}" if b < 0 else "")
    enonce = (
        f"Une série statistique a pour moyenne $\\bar{{x}} = {_fmt(moyenne_init)}$. "
        f"On transforme chaque donnée $x_i$ en $y_i = {a_txt}x_i {b_txt}$. Calculer la moyenne $\\bar{{y}}$ de la nouvelle série."
    )
    steps = [
        "Étape 1 — Propriété de linéarité : si $y_i = a x_i + b$ pour toutes les données, alors $\\bar{y} = a\\bar{x} + b$.",
        f"Étape 2 — $\\bar{{y}} = {_fmt(a)} \\times {_fmt(moyenne_init)} {b_txt} = {_fmt(nouvelle_moyenne)}$.",
    ]
    answer = f"$\\bar{{y}} = {_fmt(nouvelle_moyenne)}$"
    hint = "Pas besoin de refaire tous les calculs : la moyenne se transforme comme les données elles-mêmes (ȳ = a×x̄ + b)."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint,
            "notion": "Linéarité de la moyenne"}


# ── 3. Écart-type d'une petite série ─────────────────────────────────────────

def _gen_ecart_type(rng: random.Random) -> Optional[dict]:
    valeurs = [rng.randint(1, 15) for _ in range(4)]
    n = len(valeurs)
    moyenne = Rational(sum(valeurs), n)
    variance = sum(Rational((v - moyenne) ** 2) for v in valeurs) / n
    ecart_type = sqrt(variance)
    enonce = (
        f"Une série statistique comporte les 4 valeurs suivantes : ${', '.join(map(str, valeurs))}$ "
        "(chacune avec un effectif de 1). Calculer la moyenne puis l'écart-type de cette série (valeur exacte)."
    )
    ecarts = ", ".join(f"({v}-{latex(moyenne)})^2" for v in valeurs)
    steps = [
        f"Étape 1 — Moyenne $\\bar{{x}} = \\dfrac{{{'+'.join(map(str, valeurs))}}}{{{n}}} = {latex(moyenne)}$.",
        f"Étape 2 — Variance $V = \\dfrac{{{ecarts}}}{{{n}}} = {latex(variance)}$.",
        f"Étape 3 — Écart-type $\\sigma = \\sqrt{{V}} = {latex(ecart_type)}$.",
    ]
    answer = f"Moyenne $= {latex(moyenne)}$, écart-type $\\sigma = {latex(ecart_type)}$"
    hint = "Écart-type = racine carrée de la variance ; variance = moyenne des carrés des écarts à la moyenne."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint,
            "notion": "Ecart-type"}


# ── 4. Quartiles et écart interquartile (méthode des rangs) ─────────────────

def _gen_quartiles(rng: random.Random) -> Optional[dict]:
    n = rng.choice([12, 16, 20])
    donnees = sorted(rng.randint(1, 50) for _ in range(n))
    rang_q1 = math.ceil(n / 4)
    rang_q3 = math.ceil(3 * n / 4)
    q1 = donnees[rang_q1 - 1]
    q3 = donnees[rang_q3 - 1]
    ecart_interquartile = q3 - q1
    enonce = (
        f"Une série de ${n}$ valeurs, rangées dans l'ordre croissant, est : "
        f"${', '.join(map(str, donnees))}$. Déterminer le premier quartile $Q_1$, le troisième quartile $Q_3$ "
        "et l'écart interquartile (méthode des rangs)."
    )
    steps = [
        f"Étape 1 — Rang de $Q_1$ : le plus petit entier $\\geq \\dfrac{{n}}{{4}} = \\dfrac{{{n}}}{{4}} = {n/4}$, "
        f"donc le rang ${rang_q1}$ ; $Q_1 = {q1}$ (valeur au rang {rang_q1}).",
        f"Étape 2 — Rang de $Q_3$ : le plus petit entier $\\geq \\dfrac{{3n}}{{4}} = {3*n/4}$, "
        f"donc le rang ${rang_q3}$ ; $Q_3 = {q3}$ (valeur au rang {rang_q3}).",
        f"Étape 3 — Écart interquartile $= Q_3 - Q_1 = {q3} - {q1} = {ecart_interquartile}$.",
    ]
    answer = f"$Q_1 = {q1}$, $Q_3 = {q3}$, écart interquartile $= {ecart_interquartile}$"
    hint = "Méthode des rangs : Q1 est à la position ⌈n/4⌉, Q3 à la position ⌈3n/4⌉ dans la série triée."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint,
            "notion": "Quartiles et écart interquartile"}


@dataclass(frozen=True)
class Family:
    id: str
    level: int
    label: str
    generate: Callable[[random.Random], Optional[dict]]
    structure_hint: str
    rule_hint: str


FAMILY_BASE_SCORE: dict[str, float] = {
    "moyenne_ponderee": 1.2,
    "linearite_moyenne": 1.8,
    "quartiles": 2.2,
    "ecart_type": 2.8,
}

FAMILIES: tuple[Family, ...] = (
    Family("moyenne_ponderee", 1, "Moyenne pondérée", _gen_moyenne_ponderee,
           "une série de valeurs avec effectifs", "somme des (valeur × effectif) divisée par l'effectif total"),
    Family("linearite_moyenne", 2, "Linéarité de la moyenne", _gen_linearite_moyenne,
           "une transformation affine des données", "ȳ = a×x̄ + b, sans refaire le calcul complet"),
    Family("quartiles", 2, "Quartiles et écart interquartile", _gen_quartiles,
           "une série triée de n valeurs", "méthode des rangs : ⌈n/4⌉ pour Q1, ⌈3n/4⌉ pour Q3"),
    Family("ecart_type", 3, "Écart-type d'une série", _gen_ecart_type,
           "une petite série de valeurs", "variance = moyenne des carrés des écarts, écart-type = racine de la variance"),
)

FAMILIES_BY_ID = {f.id: f for f in FAMILIES}


def _difficulty_bucket_from_score(score: float) -> int:
    if score <= 1.4:
        return 1
    if score <= 2.0:
        return 2
    if score <= 2.5:
        return 3
    return 4


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


def generate_pool(per_family: int = 8, seed: int = 940560101) -> list[dict]:
    rng = random.Random(seed)
    per_family_pool: dict[str, list[dict]] = {}
    for family in FAMILIES:
        seen_signatures = set()
        items = []
        attempts = 0
        while len(items) < per_family and attempts < per_family * 80:
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
