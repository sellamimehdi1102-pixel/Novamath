"""Génération symbolique d'exercices sur les pourcentages et évolutions
(Seconde, Chapitre_10 : "Evolutions d'une quantité", "Evolutions successives
et évolutions réciproques", "Proportion de proportion").

Chapitre_10 était, à égalité avec Chapitre_5, le chapitre le plus faible de
Seconde (121 exercices, aucun générateur) — créé par la mission
"équilibrage définitif de toutes les classes" (2026-09-01). Voir la
docstring de vecteurs_seconde.py pour l'architecture de distribution
(ajout direct dans exercises_bank.json, pas de fusion generated_exercise_bank
pour Seconde)."""
import random
from dataclasses import dataclass
from typing import Callable, Optional

from sympy import Rational, latex

CHAPTER_ID = "Chapitre_10"
NOTION_EVOLUTION = "Evolutions d'une quantité"
NOTION_SUCCESSIVES = "Evolutions successives et évolutions réciproques"
NOTION_PROPORTION = "Proportion de proportion"

GENERATED_ID_OFFSET = 510_000

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


# ── Famille 1 — Évolution simple (hausse ou baisse) ─────────────────────────

def _gen_evolution_simple(rng: random.Random) -> Optional[dict]:
    valeur_initiale = rng.randint(20, 400)
    taux = rng.choice([5, 10, 15, 20, 25, 30, 40, 50])
    hausse = rng.choice([True, False])
    coeff = Rational(100 + taux, 100) if hausse else Rational(100 - taux, 100)
    valeur_finale = valeur_initiale * coeff
    sens = "augmentée" if hausse else "diminuée"
    enonce = (
        f"Une quantité vaut initialement ${valeur_initiale}$. Elle est {sens} de ${taux}\\%$. "
        f"Calculer sa nouvelle valeur."
    )
    answer = f"Nouvelle valeur $= {latex(valeur_finale)}$"
    steps = [
        f"Étape 1 — Le coefficient multiplicateur d'une {'hausse' if hausse else 'baisse'} de ${taux}\\%$ est "
        f"${latex(coeff)}$.",
        f"Étape 2 — Nouvelle valeur $= {valeur_initiale} \\times {latex(coeff)} = {latex(valeur_finale)}$.",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_EVOLUTION}


# ── Famille 2 — Coefficient multiplicateur associé à une évolution ────────

def _gen_coefficient_multiplicateur(rng: random.Random) -> Optional[dict]:
    taux = rng.choice([2, 4, 5, 8, 10, 12, 15, 18, 20, 25, 30, 35, 40, 50, 60, 75])
    hausse = rng.choice([True, False])
    coeff = Rational(100 + taux, 100) if hausse else Rational(100 - taux, 100)
    sens = "hausse" if hausse else "baisse"
    enonce = f"Déterminer le coefficient multiplicateur associé à une {sens} de ${taux}\\%$."
    answer = f"Coefficient multiplicateur $= {latex(coeff)}$"
    steps = [
        f"Étape 1 — Une {sens} de $t\\%$ correspond au coefficient multiplicateur "
        f"${'1 + t/100' if hausse else '1 - t/100'}$.",
        f"Étape 2 — $CM = {'1 + ' if hausse else '1 - '}\\dfrac{{{taux}}}{{100}} = {latex(coeff)}$.",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_EVOLUTION}


# ── Famille 3 — Évolutions successives ──────────────────────────────────────

def _gen_evolutions_successives(rng: random.Random) -> Optional[dict]:
    valeur_initiale = rng.randint(50, 500)
    t1 = rng.choice([5, 10, 15, 20, 25, 30])
    t2 = rng.choice([5, 10, 15, 20, 25, 30])
    h1, h2 = rng.choice([True, False]), rng.choice([True, False])
    coeff1 = Rational(100 + t1, 100) if h1 else Rational(100 - t1, 100)
    coeff2 = Rational(100 + t2, 100) if h2 else Rational(100 - t2, 100)
    coeff_global = coeff1 * coeff2
    valeur_finale = valeur_initiale * coeff_global
    taux_global = (coeff_global - 1) * 100
    sens1 = "hausse" if h1 else "baisse"
    sens2 = "hausse" if h2 else "baisse"
    enonce = (
        f"Une quantité vaut initialement ${valeur_initiale}$. Elle subit une {sens1} de ${t1}\\%$ "
        f"puis une {sens2} de ${t2}\\%$. Calculer sa valeur finale, puis le taux d'évolution global."
    )
    answer = (
        f"Valeur finale $= {latex(valeur_finale)}$, taux d'évolution global $= {latex(taux_global)}\\%$"
    )
    steps = [
        f"Étape 1 — Les coefficients multiplicateurs successifs sont ${latex(coeff1)}$ puis ${latex(coeff2)}$.",
        f"Étape 2 — Le coefficient multiplicateur global est leur produit : "
        f"${latex(coeff1)} \\times {latex(coeff2)} = {latex(coeff_global)}$.",
        f"Étape 3 — Valeur finale $= {valeur_initiale} \\times {latex(coeff_global)} = {latex(valeur_finale)}$ ; "
        f"taux global $= ({latex(coeff_global)} - 1) \\times 100 = {latex(taux_global)}\\%$.",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_SUCCESSIVES}


# ── Famille 4 — Évolution réciproque ────────────────────────────────────────

def _gen_evolution_reciproque(rng: random.Random) -> Optional[dict]:
    taux = rng.choice([10, 20, 25, 40, 50])
    hausse = rng.choice([True, False])
    coeff = Rational(100 + taux, 100) if hausse else Rational(100 - taux, 100)
    coeff_reciproque = 1 / coeff
    taux_reciproque = (1 - coeff_reciproque) * 100 if coeff_reciproque < 1 else (coeff_reciproque - 1) * 100
    sens = "hausse" if hausse else "baisse"
    sens_recip = "baisse" if hausse else "hausse"
    enonce = (
        f"Une quantité subit une {sens} de ${taux}\\%$. Quel doit être le taux de {sens_recip} (évolution "
        f"réciproque) permettant de revenir exactement à la valeur initiale ?"
    )
    answer = f"Taux de {sens_recip} $= {latex(taux_reciproque)}\\%$"
    steps = [
        f"Étape 1 — Le coefficient multiplicateur de l'évolution est ${latex(coeff)}$.",
        f"Étape 2 — Le coefficient réciproque est l'inverse : $\\dfrac{{1}}{{{latex(coeff)}}} = {latex(coeff_reciproque)}$.",
        f"Étape 3 — Le taux de {sens_recip} associé est $\\left|{latex(coeff_reciproque)} - 1\\right| \\times 100 = {latex(taux_reciproque)}\\%$.",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_SUCCESSIVES}


# ── Famille 5 — Proportion de proportion ────────────────────────────────────

def _gen_proportion_de_proportion(rng: random.Random) -> Optional[dict]:
    total = rng.choice([80, 120, 160, 200, 240, 300, 400, 500])
    p1 = rng.choice([10, 20, 25, 30, 40, 50, 60, 75])
    p2 = rng.choice([10, 20, 25, 30, 40, 50, 60, 75])
    etape1 = Rational(total * p1, 100)
    resultat = Rational(etape1 * p2, 100)
    enonce = (
        f"Dans un groupe de ${total}$ personnes, ${p1}\\%$ pratiquent un sport. "
        f"Parmi elles, ${p2}\\%$ pratiquent la natation. "
        f"Quel pourcentage du groupe total pratique la natation ? Donner aussi l'effectif correspondant."
    )
    pourcentage_global = Rational(p1 * p2, 100)
    answer = f"${latex(pourcentage_global)}\\%$ du groupe, soit ${latex(resultat)}$ personnes"
    steps = [
        f"Étape 1 — Nombre de personnes pratiquant un sport : ${p1}\\%$ de ${total}$ $= {latex(etape1)}$.",
        f"Étape 2 — Parmi elles, ${p2}\\%$ pratiquent la natation : ${latex(etape1)} \\times \\dfrac{{{p2}}}{{100}} = {latex(resultat)}$ personnes.",
        f"Étape 3 — Le pourcentage global équivalent est $\\dfrac{{{p1} \\times {p2}}}{{100}} = {latex(pourcentage_global)}\\%$ du groupe total.",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_PROPORTION}


FAMILY_BASE_SCORE: dict[str, float] = {
    "coefficient_multiplicateur": 1.0,
    "evolution_simple": 1.4,
    "proportion_de_proportion": 2.2,
    "evolutions_successives": 3.0,
    "evolution_reciproque": 3.6,
}

FAMILIES: tuple[Family, ...] = (
    Family("coefficient_multiplicateur", 1, "Coefficient multiplicateur", NOTION_EVOLUTION, _gen_coefficient_multiplicateur,
           "une évolution exprimée en pourcentage", "hausse de t% → coefficient 1 + t/100, baisse → 1 - t/100"),
    Family("evolution_simple", 1, "Évolution simple", NOTION_EVOLUTION, _gen_evolution_simple,
           "une valeur initiale soumise à une hausse ou une baisse en pourcentage", "multiplier par le coefficient multiplicateur associé"),
    Family("proportion_de_proportion", 2, "Proportion de proportion", NOTION_PROPORTION, _gen_proportion_de_proportion,
           "un pourcentage appliqué à un sous-groupe lui-même défini par un pourcentage", "multiplier les deux taux et diviser par 100"),
    Family("evolutions_successives", 3, "Évolutions successives", NOTION_SUCCESSIVES, _gen_evolutions_successives,
           "deux évolutions appliquées l'une après l'autre", "le coefficient global est le produit des coefficients successifs"),
    Family("evolution_reciproque", 4, "Évolution réciproque", NOTION_SUCCESSIVES, _gen_evolution_reciproque,
           "une évolution dont on cherche celle qui ramène à la valeur de départ", "le coefficient réciproque est l'inverse du coefficient initial"),
)

FAMILIES_BY_ID: dict[str, Family] = {f.id: f for f in FAMILIES}


def _difficulty_bucket_from_score(score: float) -> int:
    if score <= 1.2:
        return 1
    if score <= 2.0:
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


def generate_pool(per_family: int = 12, seed: int = 20260911) -> list[dict]:
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
