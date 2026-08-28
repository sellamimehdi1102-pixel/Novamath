"""Génération symbolique d'exercices sur la simplification et la forme
irréductible d'une fraction (Troisième, Chapitre_3, notion
"Simplification et forme irréductible d'une fraction").

30 exercices existants, 100% calcul direct, 80% gabarits, 0 variété de
type — ajoute vrai/faux ("cette fraction est-elle déjà irréductible ?"),
erreur à corriger (simplification partielle) et comparaison. Le PGCD et la
forme irréductible sont calculés par sympy (Rational, gcd), jamais tapés
"en dur".
"""
import random
from dataclasses import dataclass
from typing import Callable, Optional

from sympy import Rational, gcd, latex

CHAPTER_ID = "Chapitre_3"
NOTION = "Simplification et forme irréductible d'une fraction"

GENERATED_ID_OFFSET = 130_000

LEVEL_META = {
    1: {"emoji": "🟢", "label": "Niveau 1 — Fondamental"},
    2: {"emoji": "🟡", "label": "Niveau 2 — Intermédiaire"},
    3: {"emoji": "🟠", "label": "Niveau 3 — Avancé"},
    4: {"emoji": "🔴", "label": "Niveau 4 — Difficile"},
}


def _frac_latex(num, den) -> str:
    return f"\\dfrac{{{num}}}{{{den}}}"


def _rand_simplifiable(rng, min_facteur=2, max_facteur=9):
    """Construit num/den avec un PGCD > 1 garanti (facteur commun tiré)."""
    facteur = rng.randint(min_facteur, max_facteur)
    num_r = rng.randint(1, 9)
    den_r = rng.randint(1, 9)
    while den_r == num_r:
        den_r = rng.randint(1, 9)
    return num_r * facteur, den_r * facteur


# ── 1. Simplification directe ────────────────────────────────────────────────

def _gen_simplification_directe(rng):
    num, den = _rand_simplifiable(rng)
    g = gcd(num, den)
    irr = Rational(num, den)
    enonce = f"Donner la forme irréductible de la fraction ${_frac_latex(num, den)}$."
    steps = [
        f"Étape 1 — Le PGCD de {num} et {den} est {g}.",
        f"Étape 2 — On divise numérateur et dénominateur par {g} : ${_frac_latex(num, den)} = {latex(irr)}$.",
    ]
    answer = f"${latex(irr)}$"
    hint = "Trouver le PGCD du numérateur et du dénominateur, puis diviser les deux par ce PGCD."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


# ── 2. Vrai/faux : déjà irréductible ? ───────────────────────────────────────

def _gen_vrai_faux_irreductible(rng):
    if rng.random() < 0.5:
        num, den = _rand_simplifiable(rng)
        already = False
    else:
        # Construire une fraction déjà irréductible : deux nombres premiers entre eux.
        candidates = [(a, b) for a in range(2, 13) for b in range(2, 13) if a != b and gcd(a, b) == 1]
        num, den = rng.choice(candidates)
        already = True
    g = gcd(num, den)
    enonce = f"Vrai ou faux : la fraction ${_frac_latex(num, den)}$ est déjà sous forme irréductible. Justifier."
    if already:
        answer = f"Oui : le PGCD de {num} et {den} est {g}, ils n'ont aucun facteur commun autre que 1."
    else:
        irr = Rational(num, den)
        answer = f"Non : le PGCD de {num} et {den} est {g} $> 1$ ; la forme irréductible est ${latex(irr)}$."
    steps = [
        f"Étape 1 — On calcule le PGCD de {num} et {den} : il vaut {g}.",
        f"Étape 2 — {'Comme le PGCD vaut 1, la fraction est déjà irréductible.' if already else f'Le PGCD étant {g} > 1, la fraction peut encore être simplifiée.'}",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": "Calculer le PGCD du numérateur et du dénominateur : la fraction est irréductible si et seulement si ce PGCD vaut 1."}


# ── 3. Erreur à corriger : simplification partielle ──────────────────────────

def _gen_erreur_a_corriger(rng):
    facteur1 = rng.randint(2, 5)
    facteur2 = rng.randint(2, 5)
    while facteur2 == 1:
        facteur2 = rng.randint(2, 5)
    base_num = rng.randint(1, 6)
    base_den = rng.randint(1, 6)
    while base_den == base_num:
        base_den = rng.randint(1, 6)
    num = base_num * facteur1 * facteur2
    den = base_den * facteur1 * facteur2
    partial_num, partial_den = num // facteur1, den // facteur1
    if gcd(partial_num, partial_den) == 1:
        return None  # la division par facteur1 suffisait déjà : ce ne serait pas une vraie erreur
    full = Rational(num, den)
    enonce = (
        f"Un élève affirme avoir simplifié ${_frac_latex(num, den)}$ en divisant seulement par ${facteur1}$, et propose "
        f"${_frac_latex(num // facteur1, den // facteur1)}$. A-t-il obtenu la forme irréductible ? Sinon, terminer la simplification."
    )
    g_total = gcd(num, den)
    steps = [
        f"Étape 1 — Le PGCD de {num} et {den} est {g_total}, pas seulement {facteur1} : l'élève n'a pas tout simplifié.",
        f"Étape 2 — En divisant par {g_total} directement (ou en continuant à simplifier ${_frac_latex(num // facteur1, den // facteur1)}$), "
        f"on obtient ${latex(full)}$.",
    ]
    answer = f"Non, ${_frac_latex(num // facteur1, den // facteur1)}$ n'est pas encore irréductible ; la forme irréductible est ${latex(full)}$."
    hint = "Une fraction n'est irréductible que lorsque son PGCD vaut 1 — vérifier qu'aucune simplification supplémentaire n'est possible."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


# ── 4. Comparaison : laquelle est équivalente ? ──────────────────────────────

def _gen_comparaison(rng):
    num, den = _rand_simplifiable(rng, 2, 6)
    irr = Rational(num, den)
    # Une fraction "leurre" avec le même dénominateur simplifié mais un numérateur légèrement différent.
    leurre_num = irr.p + rng.choice([1, -1, 2, -2])
    while leurre_num == 0 or Rational(leurre_num, irr.q) == irr:
        leurre_num = irr.p + rng.choice([1, -1, 2, -2, 3])
    a, b = (num, irr.p) if rng.random() < 0.5 else (irr.p, num)
    enonce = (
        f"Comparer les deux fractions ${_frac_latex(irr.p, irr.q)}$ et ${_frac_latex(leurre_num, irr.q)}$ : "
        f"laquelle est égale à ${_frac_latex(num, den)}$ une fois simplifiée ?"
    )
    steps = [
        f"Étape 1 — On simplifie ${_frac_latex(num, den)}$ : le PGCD de {num} et {den} est {gcd(num, den)}, "
        f"ce qui donne ${latex(irr)}$.",
        f"Étape 2 — Seule ${_frac_latex(irr.p, irr.q)}$ correspond à cette forme irréductible.",
    ]
    answer = f"${_frac_latex(irr.p, irr.q)}$ (l'autre, ${_frac_latex(leurre_num, irr.q)}$, n'est pas égale à ${_frac_latex(num, den)}$)."
    hint = "Simplifier la fraction de référence sous forme irréductible, puis comparer terme à terme avec chaque proposition."
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
    "simplification_directe": 1.0,
    "vrai_faux_irreductible": 2.0,
    "comparaison": 2.8,
    "erreur_a_corriger": 3.6,
}

FAMILIES: tuple[Family, ...] = (
    Family("simplification_directe", 1, "Simplification directe", _gen_simplification_directe,
           "une fraction à simplifier", "diviser par le PGCD du numérateur et du dénominateur"),
    Family("vrai_faux_irreductible", 2, "Déjà irréductible ? (vrai/faux)", _gen_vrai_faux_irreductible,
           "une fraction dont on demande le caractère irréductible", "le PGCD vaut 1 si et seulement si la fraction est irréductible"),
    Family("comparaison", 3, "Comparer deux fractions candidates", _gen_comparaison,
           "deux fractions candidates à la forme irréductible", "simplifier la fraction de référence puis comparer"),
    Family("erreur_a_corriger", 4, "Détecter une simplification partielle", _gen_erreur_a_corriger,
           "une simplification incomplète", "vérifier que le PGCD restant vaut bien 1"),
)

FAMILIES_BY_ID = {f.id: f for f in FAMILIES}


def _difficulty_bucket_from_score(score: float) -> int:
    if score <= 1.5:
        return 1
    if score <= 3.0:
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


def generate_pool(per_family: int = 7, seed: int = 30260104) -> list[dict]:
    rng = random.Random(seed)
    per_family_pool: dict[str, list[dict]] = {}
    for family in FAMILIES:
        seen_signatures = set()
        items = []
        attempts = 0
        while len(items) < per_family and attempts < per_family * 100:
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
