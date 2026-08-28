"""Génération symbolique d'exercices sur l'addition/soustraction de
fractions (Troisième, Chapitre_3, notion
"Addition et soustraction de fractions").

30 exercices existants, 97% calcul direct, 67% gabarits. Tout résultat
annoncé est calculé par sympy (Rational), jamais tapé "en dur".
"""
import random
from dataclasses import dataclass
from typing import Callable, Optional

from sympy import Rational, latex

CHAPTER_ID = "Chapitre_3"
NOTION = "Addition et soustraction de fractions"

GENERATED_ID_OFFSET = 120_000

LEVEL_META = {
    1: {"emoji": "🟢", "label": "Niveau 1 — Fondamental"},
    2: {"emoji": "🟡", "label": "Niveau 2 — Intermédiaire"},
    3: {"emoji": "🟠", "label": "Niveau 3 — Avancé"},
    4: {"emoji": "🔴", "label": "Niveau 4 — Difficile"},
}


def _frac_latex(num, den) -> str:
    return f"\\dfrac{{{num}}}{{{den}}}"


def _rng_frac(rng, den_choices=(2, 3, 4, 5, 6, 7, 8, 9, 10, 12)):
    den = rng.choice(den_choices)
    num = rng.randint(1, den * 2)
    while num == 0:
        num = rng.randint(1, den * 2)
    return num, den


# ── 1. Même dénominateur ─────────────────────────────────────────────────────

def _gen_meme_denominateur(rng):
    den = rng.choice([2, 3, 4, 5, 6, 7, 8, 9, 10, 12])
    n1 = rng.randint(1, den - 1) if den > 1 else 1
    n2 = rng.randint(1, den - 1) if den > 1 else 1
    op = rng.choice(["+", "-"])
    result = Rational(n1, den) + Rational(n2, den) if op == "+" else Rational(n1, den) - Rational(n2, den)
    enonce = f"Calculer ${_frac_latex(n1, den)} {op} {_frac_latex(n2, den)}$, puis simplifier si possible."
    steps = [
        f"Étape 1 — Les dénominateurs sont identiques ($ {den} $) : on {'additionne' if op=='+' else 'soustrait'} les numérateurs.",
        f"Étape 2 — ${_frac_latex(n1, den)} {op} {_frac_latex(n2, den)} = {_frac_latex(n1 + n2 if op=='+' else n1 - n2, den)} = {latex(result)}$.",
    ]
    answer = f"${latex(result)}$"
    hint = "Avec le même dénominateur, on additionne ou soustrait directement les numérateurs."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


# ── 2. Dénominateurs différents ─────────────────────────────────────────────

def _gen_denominateurs_differents(rng):
    d1 = rng.choice([2, 3, 4, 5, 6])
    d2 = rng.choice([3, 4, 5, 6, 7])
    while d2 == d1:
        d2 = rng.choice([3, 4, 5, 6, 7])
    n1 = rng.randint(1, d1 * 2)
    n2 = rng.randint(1, d2 * 2)
    op = rng.choice(["+", "-"])
    result = Rational(n1, d1) + Rational(n2, d2) if op == "+" else Rational(n1, d1) - Rational(n2, d2)
    from sympy import lcm
    d_commun = lcm(d1, d2)
    n1c = n1 * (d_commun // d1)
    n2c = n2 * (d_commun // d2)
    enonce = f"Calculer ${_frac_latex(n1, d1)} {op} {_frac_latex(n2, d2)}$."
    steps = [
        f"Étape 1 — On réduit au même dénominateur : le PPCM de {d1} et {d2} est {d_commun}.",
        f"Étape 2 — ${_frac_latex(n1, d1)} = {_frac_latex(n1c, d_commun)}$ et ${_frac_latex(n2, d2)} = {_frac_latex(n2c, d_commun)}$.",
        f"Étape 3 — ${_frac_latex(n1c, d_commun)} {op} {_frac_latex(n2c, d_commun)} = {latex(result)}$.",
    ]
    answer = f"${latex(result)}$"
    hint = "Réduire les deux fractions au même dénominateur (PPCM des deux dénominateurs) avant de combiner les numérateurs."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


# ── 3. Trois fractions (multi-étapes) ────────────────────────────────────────

def _gen_trois_fractions(rng):
    dens = rng.sample([2, 3, 4, 5, 6], 3)
    nums = [rng.randint(1, d - 1) if d > 1 else 1 for d in dens]
    ops = [rng.choice(["+", "-"]) for _ in range(2)]
    val = Rational(nums[0], dens[0])
    val = val + Rational(nums[1], dens[1]) if ops[0] == "+" else val - Rational(nums[1], dens[1])
    val = val + Rational(nums[2], dens[2]) if ops[1] == "+" else val - Rational(nums[2], dens[2])
    expr = f"{_frac_latex(nums[0], dens[0])} {ops[0]} {_frac_latex(nums[1], dens[1])} {ops[1]} {_frac_latex(nums[2], dens[2])}"
    enonce = f"Calculer ${expr}$ (on combinera les fractions deux par deux)."
    from sympy import lcm
    d_commun = lcm(lcm(dens[0], dens[1]), dens[2])
    steps = [
        f"Étape 1 — On met les trois fractions au même dénominateur (PPCM de {dens[0]}, {dens[1]} et {dens[2]} = {d_commun}).",
        "Étape 2 — On combine ensuite les numérateurs dans l'ordre des opérations.",
        f"Étape 3 — Le résultat final est ${latex(val)}$.",
    ]
    answer = f"${latex(val)}$"
    hint = "Réduire toutes les fractions au même dénominateur avant de combiner les numérateurs, étape par étape."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


# ── 4. Contexte réel ─────────────────────────────────────────────────────────

def _gen_contexte(rng):
    nom, de_nom, den1, den2 = rng.choice([
        ("un réservoir", "d'un réservoir", 3, 4), ("un gâteau", "d'un gâteau", 2, 3),
        ("un budget familial", "d'un budget familial", 4, 5), ("un trajet", "d'un trajet", 3, 5),
    ])
    n1 = rng.randint(1, den1 - 1) if den1 > 1 else 1
    n2 = rng.randint(1, den2 - 1) if den2 > 1 else 1
    total = Rational(n1, den1) + Rational(n2, den2)
    reste = 1 - total
    if reste <= 0:
        return None
    from sympy import lcm
    d_commun = lcm(den1, den2)
    enonce = (
        f"Le premier jour, on remplit ${_frac_latex(n1, den1)}$ {de_nom}. Le deuxième jour, on ajoute encore "
        f"${_frac_latex(n2, den2)}$ {de_nom}. Quelle fraction {de_nom} reste-t-il à remplir ?"
    )
    steps = [
        f"Étape 1 — La part déjà remplie est ${_frac_latex(n1, den1)} + {_frac_latex(n2, den2)} = {latex(total)}$ (dénominateur commun {d_commun}).",
        f"Étape 2 — La part restante est $1 - {latex(total)} = {latex(reste)}$.",
    ]
    answer = f"${latex(reste)}$ {de_nom} reste à remplir."
    hint = "Additionner d'abord les fractions déjà remplies, puis soustraire ce total à l'unité entière (1)."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


# ── 5. Erreur à corriger ─────────────────────────────────────────────────────

def _gen_erreur_a_corriger(rng):
    d1 = rng.choice([2, 3, 4])
    d2 = rng.choice([3, 4, 5])
    while d2 == d1:
        d2 = rng.choice([3, 4, 5])
    n1 = rng.randint(1, d1 - 1) if d1 > 1 else 1
    n2 = rng.randint(1, d2 - 1) if d2 > 1 else 1
    correct = Rational(n1, d1) + Rational(n2, d2)
    # Erreur classique : additionner numérateurs ENTRE EUX et dénominateurs ENTRE EUX.
    wrong = Rational(n1 + n2, d1 + d2)
    if wrong == correct:
        return None
    enonce = (
        f"Un élève calcule ${_frac_latex(n1, d1)} + {_frac_latex(n2, d2)}$ ainsi : "
        f"\"on additionne les numérateurs entre eux et les dénominateurs entre eux, donc "
        f"${_frac_latex(n1 + n2, d1 + d2)}$\". Cette méthode est-elle correcte ? Donner le bon calcul."
    )
    from sympy import lcm
    d_commun = lcm(d1, d2)
    steps = [
        "Étape 1 — On n'additionne JAMAIS directement les dénominateurs entre eux : il faut d'abord réduire au même dénominateur.",
        f"Étape 2 — Le dénominateur commun de {d1} et {d2} est {d_commun}, pas {d1 + d2}.",
        f"Étape 3 — Le calcul correct donne ${_frac_latex(n1, d1)} + {_frac_latex(n2, d2)} = {latex(correct)}$.",
    ]
    answer = f"Méthode incorrecte ; le résultat correct est ${latex(correct)}$ (pas ${latex(wrong)}$)."
    hint = "On ne peut jamais additionner des fractions en additionnant séparément numérateurs et dénominateurs — il faut le même dénominateur."
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
    "meme_denominateur": 1.0,
    "denominateurs_differents": 2.0,
    "contexte": 2.6,
    "trois_fractions": 3.2,
    "erreur_a_corriger": 3.8,
}

FAMILIES: tuple[Family, ...] = (
    Family("meme_denominateur", 1, "Même dénominateur", _gen_meme_denominateur,
           "deux fractions de même dénominateur", "combiner directement les numérateurs"),
    Family("denominateurs_differents", 2, "Dénominateurs différents", _gen_denominateurs_differents,
           "deux fractions de dénominateurs distincts", "réduire au même dénominateur (PPCM) avant de combiner"),
    Family("contexte", 3, "Problème contextualisé", _gen_contexte,
           "une situation concrète en fractions", "additionner les parts connues puis soustraire à 1"),
    Family("trois_fractions", 3, "Trois fractions successives", _gen_trois_fractions,
           "un calcul à plusieurs fractions et dénominateurs", "réduire toutes les fractions au même dénominateur"),
    Family("erreur_a_corriger", 4, "Détecter et corriger une erreur", _gen_erreur_a_corriger,
           "un calcul qui additionne dénominateurs entre eux", "toujours réduire au même dénominateur avant de combiner"),
)

FAMILIES_BY_ID = {f.id: f for f in FAMILIES}


def _difficulty_bucket_from_score(score: float) -> int:
    if score <= 1.5:
        return 1
    if score <= 2.8:
        return 2
    if score <= 3.4:
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


def generate_pool(per_family: int = 6, seed: int = 30260103) -> list[dict]:
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
