"""Génération symbolique d'exercices sur la détermination d'une fonction
affine à partir de deux images (Troisième, Chapitre_8, notion
"Déterminer une fonction affine à partir de deux images").

30 exercices existants, 43% de gabarits distincts (redondance
structurelle signalée par tools/check_exercise_diversity.py). Le
coefficient directeur et l'ordonnée à l'origine annoncés sont recalculés
par sympy (Rational), jamais tapés "en dur".
"""
import random
from dataclasses import dataclass
from typing import Callable, Optional

from sympy import Rational, latex

CHAPTER_ID = "Chapitre_8"
NOTION = "Déterminer une fonction affine à partir de deux images"

GENERATED_ID_OFFSET = 140_000

LEVEL_META = {
    1: {"emoji": "🟢", "label": "Niveau 1 — Fondamental"},
    2: {"emoji": "🟡", "label": "Niveau 2 — Intermédiaire"},
    3: {"emoji": "🟠", "label": "Niveau 3 — Avancé"},
    4: {"emoji": "🔴", "label": "Niveau 4 — Difficile"},
}


def _fmt_affine(a, b) -> str:
    a_l = latex(a)
    a_str = "" if a == 1 else ("-" if a == -1 else a_l)
    if b == 0:
        return f"{a_str}x"
    return f"{a_str}x {'+' if b > 0 else '-'} {latex(abs(b))}"


def _compute_affine(x1, y1, x2, y2):
    a = Rational(y2 - y1, x2 - x1)
    b = y1 - a * x1
    return a, b


# ── 1. Calcul direct depuis deux images ──────────────────────────────────────

def _gen_calcul_direct(rng):
    x1 = rng.randint(-6, 5)
    x2 = x1 + rng.randint(1, 8)
    a_target = rng.choice([r for r in range(-6, 7) if r != 0])
    b_target = rng.randint(-8, 8)
    y1 = a_target * x1 + b_target
    y2 = a_target * x2 + b_target
    a, b = _compute_affine(x1, y1, x2, y2)
    enonce = f"Une fonction affine $f$ est telle que $f({x1}) = {y1}$ et $f({x2}) = {y2}$. Déterminer l'expression de $f(x)$."
    steps = [
        f"Étape 1 — Le coefficient directeur est $a = \\dfrac{{f({x2})-f({x1})}}{{{x2}-{x1}}} = \\dfrac{{{y2}-({y1})}}{{{x2}-({x1})}} = {latex(a)}$.",
        f"Étape 2 — On trouve $b$ avec $f({x1}) = a\\times {x1} + b$, soit $b = {y1} - {latex(a)}\\times({x1}) = {latex(b)}$.",
    ]
    answer = f"$f(x) = {_fmt_affine(a, b)}$"
    hint = "Le coefficient directeur est le rapport de la variation des images sur la variation des antécédents ; b se déduit ensuite en substituant un point."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


# ── 2. Vérifier l'appartenance d'un point (vrai/faux) ────────────────────────

def _gen_verifier_appartenance(rng):
    x1 = rng.randint(-6, 5)
    x2 = x1 + rng.randint(1, 8)
    a_target = rng.choice([r for r in range(-6, 7) if r != 0])
    b_target = rng.randint(-8, 8)
    y1 = a_target * x1 + b_target
    y2 = a_target * x2 + b_target
    a, b = _compute_affine(x1, y1, x2, y2)
    x3 = rng.randint(-8, 8)
    while x3 in (x1, x2):
        x3 = rng.randint(-8, 8)
    y3_correct = a * x3 + b
    is_correct = rng.random() < 0.5
    y3_proposed = y3_correct if is_correct else y3_correct + rng.choice([1, -1, 2, -2, 3])
    enonce = (
        f"On sait que $f({x1}) = {y1}$ et $f({x2}) = {y2}$ pour une fonction affine $f$. "
        f"Un élève affirme que $f({x3}) = {latex(y3_proposed)}$. A-t-il raison ? Justifier."
    )
    steps = [
        f"Étape 1 — On détermine $f$ : $a = {latex(a)}$ et $b = {latex(b)}$, donc $f(x) = {_fmt_affine(a, b)}$.",
        f"Étape 2 — On calcule $f({x3}) = {latex(a)}\\times({x3}) {'+' if b >= 0 else '-'} {latex(abs(b))} = {latex(y3_correct)}$.",
    ]
    if is_correct:
        answer = f"Vrai : $f({x3}) = {latex(y3_correct)}$."
    else:
        answer = f"Faux : $f({x3}) = {latex(y3_correct)}$, pas ${latex(y3_proposed)}$."
    hint = "Déterminer d'abord l'expression complète de f, puis calculer réellement l'image annoncée avant de juger."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


# ── 3. Erreur à corriger (coefficient directeur mal calculé) ────────────────

def _gen_erreur_a_corriger(rng):
    x1 = rng.randint(-6, 4)
    x2 = x1 + rng.randint(2, 8)
    a_target = rng.choice([r for r in range(-6, 7) if r not in (0, 1, -1)])
    b_target = rng.randint(-8, 8)
    y1 = a_target * x1 + b_target
    y2 = a_target * x2 + b_target
    a, b = _compute_affine(x1, y1, x2, y2)
    # Erreur classique : l'élève inverse numérateur et dénominateur.
    wrong_a = Rational(x2 - x1, y2 - y1)
    if wrong_a == a:
        return None
    enonce = (
        f"Un élève calcule le coefficient directeur de la fonction affine $f$ telle que $f({x1}) = {y1}$ et "
        f"$f({x2}) = {y2}$ ainsi : \"$a = \\dfrac{{{x2}-({x1})}}{{{y2}-({y1})}} = {latex(wrong_a)}$\" "
        "(il a inversé numérateur et dénominateur). Identifier son erreur et donner l'expression correcte de $f$."
    )
    steps = [
        "Étape 1 — La formule est $a = \\dfrac{\\text{variation des images}}{\\text{variation des antécédents}}$, "
        "pas l'inverse.",
        f"Étape 2 — Le bon calcul est $a = \\dfrac{{{y2}-({y1})}}{{{x2}-({x1})}} = {latex(a)}$.",
        f"Étape 3 — On en déduit $b = {y1} - {latex(a)}\\times({x1}) = {latex(b)}$, donc $f(x) = {_fmt_affine(a, b)}$.",
    ]
    answer = f"Erreur : numérateur et dénominateur inversés ; la fonction correcte est $f(x) = {_fmt_affine(a, b)}$."
    hint = "Le coefficient directeur est toujours (variation des images) divisée par (variation des antécédents), jamais l'inverse."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


# ── 4. Contexte réel (tarif linéaire) ────────────────────────────────────────

def _gen_contexte(rng):
    grandeur, unite = rng.choice([
        ("le prix d'une location de vélo", "€"), ("le coût d'un trajet en taxi", "€"),
        ("la masse d'eau dans une cuve", "L"), ("la distance parcourue par un coureur", "km"),
    ])
    var, de_var, var_unite = rng.choice([
        ("la durée", "de la durée", "min"), ("le temps", "du temps", "h"),
        ("le nombre de kilomètres", "du nombre de kilomètres", "km"),
    ])
    x1 = rng.randint(0, 4)
    x2 = x1 + rng.randint(2, 10)
    a_target = rng.choice([r for r in range(1, 7)])
    b_target = rng.randint(0, 15)
    y1 = a_target * x1 + b_target
    y2 = a_target * x2 + b_target
    a, b = _compute_affine(x1, y1, x2, y2)
    enonce = (
        f"On modélise {grandeur} (en {unite}) en fonction {de_var} (en {var_unite}) par une fonction affine $f$. "
        f"On sait que $f({x1}) = {y1}$ et $f({x2}) = {y2}$. Déterminer l'expression de $f(x)$ et interpréter le "
        "coefficient directeur dans ce contexte."
    )
    steps = [
        f"Étape 1 — $a = \\dfrac{{{y2}-({y1})}}{{{x2}-({x1})}} = {latex(a)}$ et $b = {y1} - {latex(a)}\\times({x1}) = {latex(b)}$.",
        f"Étape 2 — $f(x) = {_fmt_affine(a, b)}$.",
        f"Étape 3 — Le coefficient directeur ${latex(a)}$ représente l'augmentation de {grandeur} par unité de {var} "
        f"(en {unite} par {var_unite}) ; $b={latex(b)}$ est la valeur initiale (à {var}$=0$).",
    ]
    answer = f"$f(x) = {_fmt_affine(a, b)}$ ; le coefficient ${latex(a)}$ {unite}/{var_unite} est le taux d'augmentation, ${latex(b)}$ {unite} est la valeur de départ."
    hint = "Une fois a et b calculés, interpréter a comme un taux (unité de f par unité de x) et b comme la valeur initiale."
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
    "calcul_direct": 1.0,
    "verifier_appartenance": 2.0,
    "contexte": 2.8,
    "erreur_a_corriger": 3.6,
}

FAMILIES: tuple[Family, ...] = (
    Family("calcul_direct", 1, "Calcul direct depuis deux images", _gen_calcul_direct,
           "deux couples (antécédent, image)", "a = variation des images / variation des antécédents, puis b par substitution"),
    Family("verifier_appartenance", 2, "Vérifier une image annoncée (vrai/faux)", _gen_verifier_appartenance,
           "une troisième image annoncée par un élève", "reconstruire f entièrement avant de juger"),
    Family("contexte", 3, "Problème contextualisé (tarif linéaire)", _gen_contexte,
           "une situation concrète modélisée par une fonction affine", "interpréter a comme un taux et b comme une valeur initiale"),
    Family("erreur_a_corriger", 4, "Détecter et corriger une erreur", _gen_erreur_a_corriger,
           "un calcul de coefficient directeur inversé", "a = Δimages/Δantécédents, jamais l'inverse"),
)

FAMILIES_BY_ID = {f.id: f for f in FAMILIES}


def _difficulty_bucket_from_score(score: float) -> int:
    if score <= 1.5:
        return 1
    if score <= 2.3:
        return 2
    if score <= 3.2:
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


def generate_pool(per_family: int = 7, seed: int = 30260105) -> list[dict]:
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
