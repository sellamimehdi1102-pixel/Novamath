"""Génération symbolique d'exercices sur les variables aléatoires (Première,
Chapitre_10 : "Variables aléatoires réelles", "Espérance – Variance –
Écart-type").

Même patron que webapp/exercise_generator/second_degre.py : familles à score
fixe, toute probabilité/espérance manipulée en fraction exacte
(sympy.Rational). Voir webapp/exercise_generator/trigonometrie.py pour le
contexte de la mission "rééquilibrage additif" (2026-09-01).
"""
import random
from dataclasses import dataclass
from typing import Callable, Optional

from sympy import Rational, latex, sqrt, simplify

CHAPTER_ID = "Chapitre_10"
NOTION_VARIABLES = "Variables aléatoires réelles"
NOTION_ESPERANCE = "Espérance – Variance – Écart-type"

GENERATED_ID_OFFSET = 1_000_000

LEVEL_META = {
    1: {"emoji": "🟢", "label": "Niveau 1 — Fondamental"},
    2: {"emoji": "🟡", "label": "Niveau 2 — Intermédiaire"},
    3: {"emoji": "🟠", "label": "Niveau 3 — Avancé"},
    4: {"emoji": "🔴", "label": "Niveau 4 — Difficile"},
    5: {"emoji": "🟣", "label": "Niveau 5 — Défi"},
}


def _loi_3_valeurs(rng: random.Random):
    """Construit une loi de probabilité à 3 valeurs distinctes (x1<x2<x3),
    probabilités en fractions de dénominateur commun, sommant exactement à 1."""
    den = rng.choice([4, 5, 6, 8, 10])
    parts = []
    remaining = den
    for _ in range(2):
        take = rng.randint(1, remaining - 2) if remaining > 2 else 1
        parts.append(take)
        remaining -= take
    parts.append(remaining)
    rng.shuffle(parts)
    probs = [Rational(p, den) for p in parts]
    values = sorted(rng.sample(range(-6, 9), 3))
    return values, probs


@dataclass(frozen=True)
class Family:
    id: str
    level: int
    label: str
    notion: str
    generate: Callable[[random.Random], Optional[dict]]
    structure_hint: str
    rule_hint: str


def _table_latex(values, probs) -> str:
    header = " & ".join(f"x_{i+1}={v}" for i, v in enumerate(values))
    row = " & ".join(f"{latex(p)}" for p in probs)
    return f"$P(X=x_i)$ : " + ", ".join(f"$P(X={v}) = {latex(p)}$" for v, p in zip(values, probs))


# ── Famille 1 — Calcul de l'espérance ───────────────────────────────────────

def _gen_esperance(rng: random.Random) -> Optional[dict]:
    values, probs = _loi_3_valeurs(rng)
    esperance = sum(v * p for v, p in zip(values, probs))
    table = _table_latex(values, probs)
    enonce = f"Une variable aléatoire $X$ suit la loi de probabilité suivante : {table}. Calculer $E(X)$."
    answer = f"$E(X) = {latex(esperance)}$"
    terms = " + ".join(f"{v} \\times {latex(p)}" for v, p in zip(values, probs))
    steps = [
        "Étape 1 — On utilise la formule $E(X) = \\sum x_i \\times P(X=x_i)$.",
        f"Étape 2 — $E(X) = {terms} = {latex(esperance)}$.",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_ESPERANCE}


# ── Famille 2 — Compléter une loi de probabilité ───────────────────────────

def _gen_completer_loi(rng: random.Random) -> Optional[dict]:
    values, probs = _loi_3_valeurs(rng)
    idx_inconnue = rng.randint(0, 2)
    manquante = probs[idx_inconnue]
    connues = [(v, p) for i, (v, p) in enumerate(zip(values, probs)) if i != idx_inconnue]
    table = ", ".join(f"$P(X={v}) = {latex(p)}$" for v, p in connues)
    enonce = (
        f"Une variable aléatoire $X$ prend les valeurs ${values[0]}$, ${values[1]}$ et ${values[2]}$. "
        f"On donne {table}. Déterminer $P(X={values[idx_inconnue]})$."
    )
    somme_connues = sum(p for _, p in connues)
    answer = f"$P(X={values[idx_inconnue]}) = {latex(manquante)}$"
    steps = [
        "Étape 1 — La somme des probabilités d'une loi vaut $1$.",
        f"Étape 2 — $P(X={values[idx_inconnue]}) = 1 - \\left({' + '.join(latex(p) for _, p in connues)}\\right) = 1 - {latex(somme_connues)}$.",
        f"Étape 3 — {answer}",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_VARIABLES}


# ── Famille 3 — Variance et écart-type ──────────────────────────────────────

def _gen_variance(rng: random.Random) -> Optional[dict]:
    values, probs = _loi_3_valeurs(rng)
    esperance = sum(v * p for v, p in zip(values, probs))
    esperance_carre = sum((v ** 2) * p for v, p in zip(values, probs))
    variance = simplify(esperance_carre - esperance ** 2)
    ecart_type = simplify(sqrt(variance))
    table = _table_latex(values, probs)
    enonce = f"Une variable aléatoire $X$ suit la loi de probabilité suivante : {table}. Calculer $V(X)$ puis $\\sigma(X)$."
    answer = f"$V(X) = {latex(variance)}$, $\\sigma(X) = {latex(ecart_type)}$"
    steps = [
        f"Étape 1 — On calcule d'abord $E(X) = {latex(esperance)}$.",
        f"Étape 2 — On calcule $E(X^2) = \\sum x_i^2 \\times P(X=x_i) = {latex(esperance_carre)}$.",
        f"Étape 3 — $V(X) = E(X^2) - E(X)^2 = {latex(esperance_carre)} - \\left({latex(esperance)}\\right)^2 = {latex(variance)}$.",
        f"Étape 4 — $\\sigma(X) = \\sqrt{{V(X)}} = \\sqrt{{{latex(variance)}}} = {latex(ecart_type)}$.",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_ESPERANCE}


# ── Famille 4 — Transformation affine E(aX+b), V(aX+b) ─────────────────────

def _gen_transformation_affine(rng: random.Random) -> Optional[dict]:
    ex = Rational(rng.randint(-8, 8), rng.choice([1, 2, 3, 4]))
    vx = Rational(rng.randint(1, 12), rng.choice([1, 2, 3, 4]))
    a = rng.choice([n for n in range(-5, 6) if n != 0])
    b = rng.randint(-6, 6)
    e_result = a * ex + b
    v_result = (a ** 2) * vx
    b_suffix = f" + {b}" if b > 0 else (f" - {-b}" if b < 0 else "")
    a_prefix = "-" if a == -1 else ("" if a == 1 else str(a))
    enonce = (
        f"On donne $E(X) = {latex(ex)}$ et $V(X) = {latex(vx)}$. On pose $Y = {a_prefix}X{b_suffix}$. "
        f"Calculer $E(Y)$ et $V(Y)$."
    )
    answer = f"$E(Y) = {latex(e_result)}$, $V(Y) = {latex(v_result)}$"
    steps = [
        f"Étape 1 — Pour $Y=aX+b$, $E(Y) = a\\,E(X) + b = {a} \\times {latex(ex)} + ({b}) = {latex(e_result)}$.",
        f"Étape 2 — $V(Y) = a^2\\,V(X) = {a}^2 \\times {latex(vx)} = {latex(v_result)}$.",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_ESPERANCE}


# ── Famille 5 — Jeu contextualisé : gain espéré, équité ────────────────────

_CONTEXTES_JEU = [
    {"nom": "tirer une boule dans une urne", "gain_mot": "gain algébrique"},
    {"nom": "lancer un dé truqué", "gain_mot": "gain algébrique"},
    {"nom": "jouer à une loterie", "gain_mot": "gain algébrique"},
]


def _gen_jeu_esperance(rng: random.Random) -> Optional[dict]:
    ctx = rng.choice(_CONTEXTES_JEU)
    mise = rng.randint(2, 10)
    gain_grand = rng.randint(mise + 5, mise + 30)
    p_gagner = Rational(1, rng.choice([4, 5, 6, 8, 10]))
    p_perdre = 1 - p_gagner
    values = [gain_grand - mise, -mise]
    probs = [p_gagner, p_perdre]
    esperance = sum(v * p for v, p in zip(values, probs))
    verdict = "favorable au joueur" if esperance > 0 else ("défavorable au joueur" if esperance < 0 else "équitable")
    enonce = (
        f"Pour {ctx['nom']}, la mise est de ${mise}$ € ; le joueur gagne ${gain_grand}$ € avec une probabilité "
        f"de ${latex(p_gagner)}$, et ne gagne rien sinon. Soit $X$ le {ctx['gain_mot']} du joueur (gain moins mise). "
        "Déterminer la loi de $X$, calculer $E(X)$, et dire si le jeu est favorable au joueur, défavorable, ou équitable."
    )
    answer = f"$E(X) = {latex(esperance)}$ : le jeu est {verdict}."
    steps = [
        f"Étape 1 — Si le joueur gagne (probabilité ${latex(p_gagner)}$) : gain algébrique $= {gain_grand} - {mise} = {values[0]}$.",
        f"Étape 2 — Si le joueur perd (probabilité ${latex(p_perdre)}$) : gain algébrique $= -{mise}$.",
        f"Étape 3 — $E(X) = {values[0]} \\times {latex(p_gagner)} + ({values[1]}) \\times {latex(p_perdre)} = {latex(esperance)}$.",
        f"Étape 4 — {answer}",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_VARIABLES}


FAMILY_BASE_SCORE: dict[str, float] = {
    "completer_loi": 1.0,
    "esperance": 1.6,
    "transformation_affine": 2.4,
    "jeu_esperance": 3.2,
    "variance": 4.0,
}

FAMILIES: tuple[Family, ...] = (
    Family("completer_loi", 1, "Compléter une loi de probabilité", NOTION_VARIABLES, _gen_completer_loi,
           "une loi de probabilité avec une valeur manquante", "la somme des probabilités vaut 1"),
    Family("esperance", 2, "Calcul de l'espérance", NOTION_ESPERANCE, _gen_esperance,
           "une loi de probabilité complète", "E(X) = Σ x_i × P(X=x_i)"),
    Family("transformation_affine", 2, "Transformation affine E(aX+b), V(aX+b)", NOTION_ESPERANCE,
           _gen_transformation_affine, "E(X) et V(X) connues, Y=aX+b",
           "E(aX+b)=aE(X)+b et V(aX+b)=a²V(X)"),
    Family("jeu_esperance", 3, "Jeu contextualisé : gain espéré", NOTION_VARIABLES, _gen_jeu_esperance,
           "un jeu avec mise et gain conditionnel", "calculer E(X) puis comparer son signe à 0"),
    Family("variance", 4, "Variance et écart-type", NOTION_ESPERANCE, _gen_variance,
           "une loi de probabilité complète", "V(X)=E(X²)-E(X)², puis σ(X)=√V(X)"),
)

FAMILIES_BY_ID: dict[str, Family] = {f.id: f for f in FAMILIES}


def _difficulty_bucket_from_score(score: float) -> int:
    if score <= 1.3:
        return 1
    if score <= 2.0:
        return 2
    if score <= 2.8:
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


def generate_pool(per_family: int = 12, seed: int = 20260905) -> list[dict]:
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
