"""Génération symbolique d'exercices de géométrie dans l'espace (Troisième,
Chapitre_15 : "Calculer le volume d'un solide", "Effet d'un agrandissement
ou d'une réduction sur les volumes", "Sections planes de solides").

Même patron que webapp/exercise_generator_troisieme/statistiques.py.
Créé par la mission "équilibrage définitif de toutes les classes"
(2026-09-01) — Chapitre_15 était le chapitre le plus faible de Troisième
(150 exercices, aucun générateur avant cette mission).
"""
import random
from dataclasses import dataclass
from typing import Callable, Optional

from sympy import Rational, latex, pi

CHAPTER_ID = "Chapitre_15"
NOTION_VOLUME = "Calculer le volume d'un solide"
NOTION_AGRANDISSEMENT = "Effet d'un agrandissement ou d'une réduction sur les volumes"

GENERATED_ID_OFFSET = 230_000

LEVEL_META = {
    1: {"emoji": "🟢", "label": "Niveau 1 — Fondamental"},
    2: {"emoji": "🟡", "label": "Niveau 2 — Intermédiaire"},
    3: {"emoji": "🟠", "label": "Niveau 3 — Avancé"},
    4: {"emoji": "🔴", "label": "Niveau 4 — Difficile"},
    5: {"emoji": "🟣", "label": "Niveau 5 — Défi"},
}


@dataclass(frozen=True)
class Family:
    id: str
    level: int
    label: str
    notion: str
    generate: Callable[[random.Random], Optional[dict]]
    structure_hint: str
    rule_hint: str


# ── Famille 1 — Volume d'un pavé droit ──────────────────────────────────────

def _gen_volume_pave(rng: random.Random) -> Optional[dict]:
    L, l, h = rng.randint(3, 15), rng.randint(2, 12), rng.randint(2, 10)
    volume = L * l * h
    enonce = (
        f"Un pavé droit a pour dimensions $L = {L}$ cm, $l = {l}$ cm et $h = {h}$ cm. "
        f"Calculer son volume."
    )
    answer = f"$V = {volume}$ cm$^3$"
    steps = [
        f"Étape 1 — Le volume d'un pavé droit est $V = L \\times l \\times h$.",
        f"Étape 2 — $V = {L} \\times {l} \\times {h} = {volume}$ cm$^3$.",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_VOLUME}


# ── Famille 2 — Volume d'un cylindre ────────────────────────────────────────

def _gen_volume_cylindre(rng: random.Random) -> Optional[dict]:
    r, h = rng.randint(2, 8), rng.randint(3, 15)
    volume_exact = r * r * h * pi
    volume_approx = round(float(volume_exact), 2)
    enonce = (
        f"Un cylindre a pour rayon de base $r = {r}$ cm et pour hauteur $h = {h}$ cm. "
        f"Calculer son volume (valeur exacte en fonction de $\\pi$, puis arrondi au centième)."
    )
    answer = f"$V = {r}^2 \\times {h} \\times \\pi = {latex(volume_exact)}$ cm$^3 \\approx {volume_approx}$ cm$^3$"
    steps = [
        f"Étape 1 — Le volume d'un cylindre est $V = \\pi r^2 h$.",
        f"Étape 2 — $V = \\pi \\times {r}^2 \\times {h} = {latex(volume_exact)}$ cm$^3 \\approx {volume_approx}$ cm$^3$.",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_VOLUME}


# ── Famille 3 — Volume d'un prisme droit à base triangulaire ───────────────

def _gen_volume_prisme(rng: random.Random) -> Optional[dict]:
    base, hauteur_triangle = rng.randint(4, 12), rng.randint(3, 10)
    hauteur_prisme = rng.randint(3, 12)
    aire_base = Rational(base * hauteur_triangle, 2)
    volume = aire_base * hauteur_prisme
    enonce = (
        f"Un prisme droit a pour base un triangle de base ${base}$ cm et de hauteur "
        f"${hauteur_triangle}$ cm. La hauteur du prisme vaut ${hauteur_prisme}$ cm. "
        f"Calculer le volume de ce prisme."
    )
    answer = f"$V = {latex(volume)}$ cm$^3$"
    steps = [
        f"Étape 1 — L'aire de la base triangulaire est $\\dfrac{{{base} \\times {hauteur_triangle}}}{{2}} = {latex(aire_base)}$ cm$^2$.",
        f"Étape 2 — Le volume du prisme est $V = \\text{{aire de la base}} \\times \\text{{hauteur}} = {latex(aire_base)} \\times {hauteur_prisme} = {latex(volume)}$ cm$^3$.",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_VOLUME}


# ── Famille 4 — Effet d'un agrandissement/réduction sur une aire ──────────

def _gen_effet_aire(rng: random.Random) -> Optional[dict]:
    aire_initiale = rng.randint(5, 40)
    k = rng.choice([Rational(2, 1), Rational(3, 1), Rational(4, 1), Rational(1, 2), Rational(1, 3)])
    aire_finale = aire_initiale * k * k
    sens = "agrandissement" if k > 1 else "réduction"
    enonce = (
        f"Une figure a une aire de ${aire_initiale}$ cm$^2$. On applique un {sens} de rapport $k = {latex(k)}$. "
        f"Calculer l'aire de la figure obtenue."
    )
    answer = f"Aire finale $= {latex(aire_finale)}$ cm$^2$"
    steps = [
        f"Étape 1 — Lors d'un {sens} de rapport $k$, une aire est multipliée par $k^2$.",
        f"Étape 2 — Aire finale $= {aire_initiale} \\times {latex(k)}^2 = {latex(aire_finale)}$ cm$^2$.",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_AGRANDISSEMENT}


# ── Famille 5 — Effet d'un agrandissement/réduction sur un volume ─────────

def _gen_effet_volume(rng: random.Random) -> Optional[dict]:
    volume_initial = rng.randint(10, 200)
    k = rng.choice([2, 3, 4])
    reduction = rng.choice([True, False])
    if reduction:
        volume_final = Rational(volume_initial, k ** 3)
        sens, rapport = "réduction", Rational(1, k)
    else:
        volume_final = volume_initial * k ** 3
        sens, rapport = "agrandissement", Rational(k, 1)
    enonce = (
        f"Un solide a un volume de ${volume_initial}$ cm$^3$. On applique un {sens} de rapport $k = {latex(rapport)}$. "
        f"Calculer le volume du solide obtenu."
    )
    answer = f"Volume final $= {latex(volume_final)}$ cm$^3$"
    steps = [
        f"Étape 1 — Lors d'un {sens} de rapport $k$, un volume est multiplié par $k^3$.",
        f"Étape 2 — Volume final $= {volume_initial} \\times {latex(rapport)}^3 = {latex(volume_final)}$ cm$^3$.",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_AGRANDISSEMENT}


FAMILY_BASE_SCORE: dict[str, float] = {
    "volume_pave": 1.0,
    "volume_prisme": 1.8,
    "volume_cylindre": 2.4,
    "effet_aire": 2.8,
    "effet_volume": 3.4,
}

FAMILIES: tuple[Family, ...] = (
    Family("volume_pave", 1, "Volume d'un pavé droit", NOTION_VOLUME, _gen_volume_pave,
           "un pavé droit dont on connaît les trois dimensions", "V = L × l × h"),
    Family("volume_prisme", 2, "Volume d'un prisme droit", NOTION_VOLUME, _gen_volume_prisme,
           "un prisme droit à base triangulaire", "V = aire de la base × hauteur du prisme"),
    Family("volume_cylindre", 3, "Volume d'un cylindre", NOTION_VOLUME, _gen_volume_cylindre,
           "un cylindre dont on connaît le rayon et la hauteur", "V = π × r² × h"),
    Family("effet_aire", 3, "Effet d'un agrandissement sur une aire", NOTION_AGRANDISSEMENT, _gen_effet_aire,
           "un agrandissement ou une réduction de rapport k appliqué à une figure plane", "l'aire est multipliée par k²"),
    Family("effet_volume", 4, "Effet d'un agrandissement sur un volume", NOTION_AGRANDISSEMENT, _gen_effet_volume,
           "un agrandissement ou une réduction de rapport k appliqué à un solide", "le volume est multiplié par k³"),
)

FAMILIES_BY_ID: dict[str, Family] = {f.id: f for f in FAMILIES}


def _difficulty_bucket_from_score(score: float) -> int:
    if score <= 1.2:
        return 1
    if score <= 2.0:
        return 2
    if score <= 2.8:
        return 3
    return 4


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


def generate_pool(per_family: int = 12, seed: int = 30260306) -> list[dict]:
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
