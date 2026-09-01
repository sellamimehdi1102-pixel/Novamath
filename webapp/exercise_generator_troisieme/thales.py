"""Génération symbolique d'exercices sur le théorème de Thalès (Troisième,
Chapitre_14 : "Théorème de Thalès : calculer une longueur", "Réciproque du
théorème de Thalès : démontrer un parallélisme", "Théorème des milieux").

Même patron que webapp/exercise_generator_troisieme/equation_premier_degre.py.
Créé par la mission "rééquilibrage global de toutes les classes" (2026-09-01)
— Chapitre_14 était l'un des chapitres les plus faibles de Troisième (100
exercices, aucun générateur).

Configuration géométrique fixe (triangle AOB, points M sur [OA] et N sur
[OB], (MN) // (AB)) — seules les longueurs numériques varient, toujours
construites pour donner des rapports exacts (jamais approximés).
"""
import random
from dataclasses import dataclass
from typing import Callable, Optional

from sympy import Rational, latex

CHAPTER_ID = "Chapitre_14"
NOTION_CALCULER = "Théorème de Thalès : calculer une longueur"
NOTION_RECIPROQUE = "Réciproque du théorème de Thalès : démontrer un parallélisme"
NOTION_MILIEUX = "Théorème des milieux"

GENERATED_ID_OFFSET = 220_000

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


# ── Famille 1 — Calculer une longueur (configuration triangle) ────────────

def _gen_calculer_longueur(rng: random.Random) -> Optional[dict]:
    om = rng.randint(2, 8)
    k = Rational(rng.randint(3, 8), rng.choice([1, 2]))  # facteur OA/OM
    if k <= 1:
        return None
    oa = om * k
    on = rng.randint(2, 8)
    ob = on * k
    ab = rng.randint(5, 20)
    mn = ab / k
    enonce = (
        f"Dans un triangle $OAB$, les points $M \\in [OA]$ et $N \\in [OB]$ sont tels que "
        f"$(MN) \\parallel (AB)$. On donne $OM = {om}$, $OA = {latex(oa)}$, $ON = {on}$, "
        f"$OB = {latex(ob)}$ et $AB = {ab}$. Calculer $MN$."
    )
    answer = f"$MN = {latex(mn)}$"
    steps = [
        f"Étape 1 — $(MN) \\parallel (AB)$ avec $M \\in [OA]$ et $N \\in [OB]$ : le théorème de Thalès "
        f"s'applique dans le triangle $OAB$.",
        f"Étape 2 — $\\dfrac{{OM}}{{OA}} = \\dfrac{{ON}}{{OB}} = \\dfrac{{MN}}{{AB}}$, soit "
        f"$\\dfrac{{{om}}}{{{latex(oa)}}} = \\dfrac{{MN}}{{{ab}}}$.",
        f"Étape 3 — $MN = \\dfrac{{{om} \\times {ab}}}{{{latex(oa)}}} = {latex(mn)}$.",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_CALCULER}


# ── Famille 2 — Réciproque de Thalès (tester le parallélisme) ─────────────

def _gen_reciproque(rng: random.Random) -> Optional[dict]:
    om, oa = rng.randint(2, 6), 0
    oa = om * rng.randint(2, 4)
    force_parallele = rng.random() < 0.5
    on = rng.randint(2, 6)
    if force_parallele:
        ratio = Rational(oa, om)
        ob = on * ratio
    else:
        ob = on * rng.randint(2, 4) + rng.choice([1, -1])
    r1, r2 = Rational(om, oa), Rational(on, ob)
    est_parallele = r1 == r2
    enonce = (
        f"Dans un triangle $OAB$, les points $M \\in [OA]$ et $N \\in [OB]$ vérifient "
        f"$OM = {om}$, $OA = {latex(oa)}$, $ON = {on}$, $OB = {latex(ob)}$, avec $O$, $M$, $A$ alignés "
        "et $O$, $N$, $B$ alignés dans le même ordre. Les droites $(MN)$ et $(AB)$ sont-elles parallèles ? Justifier."
    )
    if est_parallele:
        answer = f"Oui : $\\dfrac{{OM}}{{OA}} = \\dfrac{{ON}}{{OB}} = {latex(r1)}$, donc $(MN) \\parallel (AB)$ (réciproque de Thalès)."
    else:
        answer = f"Non : $\\dfrac{{OM}}{{OA}} = {latex(r1)} \\neq \\dfrac{{ON}}{{OB}} = {latex(r2)}$, donc $(MN)$ et $(AB)$ ne sont pas parallèles."
    steps = [
        f"Étape 1 — On calcule $\\dfrac{{OM}}{{OA}} = \\dfrac{{{om}}}{{{latex(oa)}}} = {latex(r1)}$ et "
        f"$\\dfrac{{ON}}{{OB}} = \\dfrac{{{on}}}{{{latex(ob)}}} = {latex(r2)}$.",
        f"Étape 2 — {answer}",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_RECIPROQUE}


# ── Famille 3 — Théorème des milieux (segment parallèle et longueur) ──────

def _gen_theoreme_milieux(rng: random.Random) -> Optional[dict]:
    bc = rng.randint(4, 15) * 2  # pair, pour un IJ entier
    ij = Rational(bc, 2)
    enonce = (
        f"Dans un triangle $ABC$, $I$ est le milieu de $[AB]$ et $J$ est le milieu de $[AC]$. "
        f"On donne $BC = {bc}$. Calculer $IJ$ et préciser la position relative de $(IJ)$ et $(BC)$."
    )
    answer = f"$IJ = {latex(ij)}$ et $(IJ) \\parallel (BC)$"
    steps = [
        "Étape 1 — $I$ et $J$ sont les milieux respectifs de $[AB]$ et $[AC]$ : le théorème des milieux s'applique.",
        f"Étape 2 — $(IJ) \\parallel (BC)$ et $IJ = \\dfrac{{BC}}{{2}} = \\dfrac{{{bc}}}{{2}} = {latex(ij)}$.",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_MILIEUX}


# ── Famille 4 — Théorème des milieux, sens réciproque (retrouver BC) ──────

def _gen_milieux_retrouver_bc(rng: random.Random) -> Optional[dict]:
    ij = rng.randint(3, 15)
    bc = ij * 2
    enonce = (
        f"Dans un triangle $ABC$, $I$ est le milieu de $[AB]$ et $J$ est le milieu de $[AC]$. "
        f"On donne $IJ = {ij}$. Calculer $BC$."
    )
    answer = f"$BC = {bc}$"
    steps = [
        "Étape 1 — D'après le théorème des milieux, $IJ = \\dfrac{BC}{2}$.",
        f"Étape 2 — Donc $BC = 2 \\times IJ = 2 \\times {ij} = {bc}$.",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_MILIEUX}


FAMILY_BASE_SCORE: dict[str, float] = {
    "theoreme_milieux": 1.0,
    "milieux_retrouver_bc": 1.4,
    "calculer_longueur": 2.4,
    "reciproque": 3.2,
}

FAMILIES: tuple[Family, ...] = (
    Family("theoreme_milieux", 1, "Théorème des milieux (calculer IJ)", NOTION_MILIEUX, _gen_theoreme_milieux,
           "deux milieux de côtés d'un triangle", "IJ = BC/2 et (IJ) // (BC)"),
    Family("milieux_retrouver_bc", 2, "Théorème des milieux (retrouver BC)", NOTION_MILIEUX,
           _gen_milieux_retrouver_bc, "IJ connu, BC à retrouver", "BC = 2 × IJ"),
    Family("calculer_longueur", 3, "Calculer une longueur (Thalès)", NOTION_CALCULER, _gen_calculer_longueur,
           "une configuration de Thalès avec une longueur inconnue", "égalité des rapports OM/OA = ON/OB = MN/AB"),
    Family("reciproque", 4, "Réciproque de Thalès", NOTION_RECIPROQUE, _gen_reciproque,
           "deux rapports à comparer pour conclure sur le parallélisme", "comparer OM/OA et ON/OB"),
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


def generate_pool(per_family: int = 12, seed: int = 30260205) -> list[dict]:
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
