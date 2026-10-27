"""Socle commun des générateurs créés pour l'adaptation de la Première spécifique
au manuel « Première ES/L » (2026-10-26) : pourcentages_1es, fonctions_reference_1es,
statistiques_1es, evenements_1es, loi_binomiale_1es.

Même contrat que les autres modules (Family, CHAPTER_ID, generate_one,
generate_pool ; identifiants GENERATED_ID_OFFSET + 1000 × rang + k). Tous les
calculs sont faits en fractions exactes ; une famille renvoie None pour un
tirage qu'elle ne sait pas écrire exactement, et le tirage est recommencé.
"""
import random
from dataclasses import dataclass
from fractions import Fraction as F
from typing import Callable, Optional

LEVEL_META = {
    1: {"emoji": "🟢", "label": "Niveau 1 — Fondamental"},
    2: {"emoji": "🟡", "label": "Niveau 2 — Intermédiaire"},
    3: {"emoji": "🟠", "label": "Niveau 3 — Avancé"},
    4: {"emoji": "🔴", "label": "Niveau 4 — Difficile"},
}


@dataclass(frozen=True)
class Family:
    id: str
    level: int
    label: str
    generate: Callable
    notion: str
    score: float


def level_from_score(score: float) -> int:
    return 1 if score <= 1.5 else 2 if score <= 2.7 else 3 if score <= 3.8 else 4


def decimal_exact(q, max_digits=6) -> bool:
    return (F(q) * 10 ** max_digits).denominator == 1


def dec(q, nd=None) -> str:
    """Nombre à la française en mode maths : virgule {,} ; nd = arrondi."""
    q = F(q)
    if nd is None:
        assert decimal_exact(q, 12), q
        if q.denominator == 1:
            return str(q.numerator)
        s = f"{float(q):.12f}".rstrip("0").rstrip(".")
    else:
        s = f"{float(q):.{nd}f}"
    neg = s.startswith("-")
    entier, _, frac = s.lstrip("-").partition(".")
    if len(entier) > 3:
        groupes = []
        while entier:
            groupes.insert(0, entier[-3:])
            entier = entier[:-3]
        entier = "\\,".join(groupes)
    return ("-" if neg else "") + entier + ("{,}" + frac if frac else "")


def frac(q) -> str:
    q = F(q)
    if q.denominator == 1:
        return str(q.numerator)
    s = "-" if q < 0 else ""
    return f"{s}\\dfrac{{{abs(q.numerator)}}}{{{q.denominator}}}"


def pct(q) -> str:
    """Proportion -> pourcentage en mode maths (« 12{,}5\\,\\% »)."""
    return f"{dec(F(q) * 100)}\\,\\%"


def par(q) -> str:
    """Facteur entre parenthèses s'il est négatif."""
    s = dec(q)
    return f"({s})" if F(q) < 0 else s


def build_exercise(family: Family, rng: random.Random, chapter_id: str) -> Optional[dict]:
    notes = family.generate(rng)
    if notes is None:
        return None
    level = level_from_score(family.score)
    assert level == family.level, family.id
    steps = [f"Étape {k} — {s}" for k, s in enumerate(notes["steps"], 1)]
    return {"enonce": notes["enonce"], "answer": notes["answer"], "hint": notes["hint"], "solution_steps": steps,
            "chapter_id": chapter_id, "notion": family.notion, "difficulty": level,
            "difficulty_label": LEVEL_META[level]["label"], "difficulty_emoji": LEVEL_META[level]["emoji"],
            "family": family.id, "family_label": family.label, "declared_level": family.level,
            "complexity_score": family.score, "source": "generated"}


def generate_one(families, chapter_id, family_id, seed=None, max_attempts=200) -> dict:
    rng = random.Random(seed)
    fam = {f.id: f for f in families}[family_id]
    for _ in range(max_attempts):
        ex = build_exercise(fam, rng, chapter_id)
        if ex is not None:
            return ex
    raise RuntimeError(f"Impossible de générer un exercice valide pour la famille {family_id!r}")


def generate_pool(families, chapter_id, offset, per_family, seed) -> list[dict]:
    pool = []
    for rank, family in enumerate(families):
        rng = random.Random(seed * 100 + rank)
        seen, items, attempts = set(), [], 0
        while len(items) < per_family and attempts < per_family * 200:
            attempts += 1
            ex = build_exercise(family, rng, chapter_id)
            if ex is None or ex["enonce"] in seen:
                continue
            seen.add(ex["enonce"])
            items.append(ex)
        for k, ex in enumerate(items):
            ex["id"] = offset + 1000 * rank + k
        pool.extend(items)
    return pool
