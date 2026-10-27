"""Socle commun des générateurs de Quatrième (chapitres autres que le pilote
Pythagore, dont le module historique reste autonome).

Même contrat que pythagore.py, attendu par exercise_generator/registry.py :
`FAMILIES` (Family.notion porte la notion), `generate_one(family_id, seed)`
et `generate_pool(per_family, seed)` (pool déterministe, dédupliqué par
énoncé, familles entrelacées, identifiants GENERATED_ID_BASE + 10 000 ×
chapitre + rang).

Un générateur de famille reçoit un `random.Random` et renvoie
{"enonce", "answer", "hint", "steps", "notion"} ou None si le tirage viole
une hypothèse (build_exercise retire alors un nouveau tirage).
"""
import random
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from fractions import Fraction
from typing import Callable, Optional

# 4 000 000 + 10 000 × chapitre : plage libre dans toutes les banques (la
# règle du pilote, 400 000 + 10 000 × chapitre, chevaucherait les
# identifiants 500 000 – 599 999 de la Seconde à partir du chapitre 10).
GENERATED_ID_BASE = 4_000_000

LEVEL_META = {
    1: {"emoji": "🟢", "label": "Niveau 1 — Fondamental"},
    2: {"emoji": "🟡", "label": "Niveau 2 — Intermédiaire"},
    3: {"emoji": "🟠", "label": "Niveau 3 — Avancé"},
    4: {"emoji": "🔴", "label": "Niveau 4 — Difficile"},
}

# Score de complexité « médian » de chaque niveau, même échelle que
# pythagore._difficulty_bucket_from_score (≤ 1,3 / ≤ 1,9 / ≤ 2,5 / au-delà).
_SCORE_BY_LEVEL = {1: 1.0, 2: 1.6, 3: 2.2, 4: 3.0}


@dataclass(frozen=True)
class Family:
    id: str
    level: int
    label: str
    notion: str
    generate: Callable[[random.Random], Optional[dict]]
    structure_hint: str
    rule_hint: str


class Chapter:
    """Regroupe les familles d'un chapitre et expose le contrat du registre."""

    def __init__(self, number: int, families):
        self.number = number
        self.chapter_id = f"Chapitre_{number}"
        self.families = tuple(families)
        self.by_id = {f.id: f for f in self.families}
        assert len(self.by_id) == len(self.families), "identifiants de famille dupliqués"
        self.id_offset = GENERATED_ID_BASE + 10_000 * number

    def build_exercise(self, family: Family, rng: random.Random) -> Optional[dict]:
        notes = family.generate(rng)
        if notes is None:
            return None
        level = family.level
        return {
            "enonce": notes["enonce"],
            "answer": notes["answer"],
            "hint": notes["hint"],
            "solution_steps": [f"Étape {i} — {s}" for i, s in enumerate(notes["steps"], 1)],
            "chapter_id": self.chapter_id,
            "notion": notes.get("notion", family.notion),
            "difficulty": level,
            "difficulty_label": LEVEL_META[level]["label"],
            "difficulty_emoji": LEVEL_META[level]["emoji"],
            "family": family.id,
            "family_label": family.label,
            "declared_level": level,
            "complexity_score": _SCORE_BY_LEVEL[level],
            "source": "generated",
        }

    def generate_one(self, family_id: str, seed: Optional[int] = None, max_attempts: int = 80) -> dict:
        rng = random.Random(seed)
        fam = self.by_id[family_id]
        for _ in range(max_attempts):
            ex = self.build_exercise(fam, rng)
            if ex is not None:
                return ex
        raise RuntimeError(f"Impossible de générer un exercice valide pour la famille {family_id!r}")

    def generate_pool(self, per_family: int = 25, seed: int = 0) -> list[dict]:
        rng = random.Random(seed)
        buckets: dict[str, list[dict]] = {}
        for family in self.families:
            seen, items, attempts = set(), [], 0
            while len(items) < per_family and attempts < per_family * 80:
                attempts += 1
                ex = self.build_exercise(family, rng)
                if ex is None or ex["enonce"] in seen:
                    continue
                seen.add(ex["enonce"])
                items.append(ex)
            buckets[family.id] = items
        pool, idx = [], 0
        while any(buckets.values()):
            bucket = buckets[self.families[idx % len(self.families)].id]
            if bucket:
                pool.append(bucket.pop(0))
            idx += 1
        for i, ex in enumerate(pool):
            ex["id"] = self.id_offset + i
        return pool


# ── Écriture française des nombres ──────────────────────────────────────────


def num(x) -> str:
    """Nombre décimal exact (int, Fraction décimale, Decimal) -> « -2{,}5 »."""
    if isinstance(x, Fraction):
        q = x.denominator
        for p in (2, 5):
            while q % p == 0:
                q //= p
        if q != 1:
            raise ValueError(f"{x} n'est pas décimal")
        x = Decimal(x.numerator) / Decimal(x.denominator)
    d = Decimal(str(x)) if not isinstance(x, Decimal) else x
    s = format(d.normalize(), "f")
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    if s in ("-0", ""):
        s = "0"
    return s.replace(".", "{,}")


def rnd(x, decimals: int) -> str:
    if isinstance(x, Fraction):
        x = Decimal(x.numerator) / Decimal(x.denominator)
    d = Decimal(str(x)) if not isinstance(x, Decimal) else x
    return num(d.quantize(Decimal(1).scaleb(-decimals), rounding=ROUND_HALF_UP))


def par(x) -> str:
    s = num(x)
    return f"({s})" if s.startswith("-") else s


def frac(f) -> str:
    f = Fraction(f)
    if f.denominator == 1:
        return str(f.numerator)
    sign = "-" if f < 0 else ""
    return f"{sign}\\dfrac{{{abs(f.numerator)}}}{{{f.denominator}}}"


def is_decimal(f: Fraction) -> bool:
    q = Fraction(f).denominator
    for p in (2, 5):
        while q % p == 0:
            q //= p
    return q == 1


def grp(x) -> str:
    """Comme num(), avec des espaces fines entre les tranches de trois chiffres : « 12\\,500{,}25 »."""
    s = num(x)
    signe = "-" if s.startswith("-") else ""
    ent, _, dec = s.lstrip("-").partition("{,}")
    ent = "\\,".join(ent[max(0, i - 3):i] for i in range(len(ent), 0, -3)[::-1])
    return signe + ent + ("{,}" + dec if dec else "")
