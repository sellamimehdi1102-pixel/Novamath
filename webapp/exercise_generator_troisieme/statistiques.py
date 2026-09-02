"""Génération symbolique d'exercices de statistiques (Troisième, Chapitre_9 :
"Moyenne (simple et pondérée)", "Médiane et étendue d'une série statistique").

Même patron que webapp/exercise_generator_troisieme/equation_premier_degre.py.
Créé par la mission "rééquilibrage global de toutes les classes" (2026-09-01)
— Chapitre_9 était l'un des chapitres les plus faibles de Troisième (90
exercices, aucun générateur).
"""
import random
from dataclasses import dataclass
from typing import Callable, Optional

from sympy import Rational, latex

CHAPTER_ID = "Chapitre_9"
NOTION_MOYENNE = "Moyenne (simple et pondérée)"
NOTION_MEDIANE = "Médiane et étendue d'une série statistique"

GENERATED_ID_OFFSET = 200_000

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


# ── Famille 1 — Moyenne simple ──────────────────────────────────────────────

def _gen_moyenne_simple(rng: random.Random) -> Optional[dict]:
    n = rng.randint(5, 8)
    valeurs = [rng.randint(0, 20) for _ in range(n)]
    total = sum(valeurs)
    moyenne = Rational(total, n)
    valeurs_txt = " ; ".join(str(v) for v in valeurs)
    enonce = f"Une série statistique a pour valeurs : {valeurs_txt}. Calculer la moyenne de cette série."
    answer = f"$\\bar{{x}} = {latex(moyenne)}$"
    steps = [
        f"Étape 1 — On additionne toutes les valeurs : ${' + '.join(str(v) for v in valeurs)} = {total}$.",
        f"Étape 2 — On divise par le nombre de valeurs ($n={n}$) : $\\bar{{x}} = \\dfrac{{{total}}}{{{n}}} = {latex(moyenne)}$.",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_MOYENNE}


# ── Famille 2 — Moyenne pondérée ────────────────────────────────────────────

def _gen_moyenne_ponderee(rng: random.Random) -> Optional[dict]:
    n = rng.randint(3, 4)
    valeurs = [rng.randint(4, 20) for _ in range(n)]
    poids = [rng.randint(1, 5) for _ in range(n)]
    total = sum(v * p for v, p in zip(valeurs, poids))
    total_poids = sum(poids)
    moyenne = Rational(total, total_poids)
    table = ", ".join(f"{v} (coefficient {p})" for v, p in zip(valeurs, poids))
    enonce = f"Calculer la moyenne pondérée des notes suivantes : {table}."
    termes = " + ".join(f"{v} \\times {p}" for v, p in zip(valeurs, poids))
    answer = f"$\\bar{{x}} = {latex(moyenne)}$"
    steps = [
        f"Étape 1 — On multiplie chaque valeur par son coefficient puis on additionne : ${termes} = {total}$.",
        f"Étape 2 — On divise par la somme des coefficients (${' + '.join(map(str, poids))} = {total_poids}$) : "
        f"$\\bar{{x}} = \\dfrac{{{total}}}{{{total_poids}}} = {latex(moyenne)}$.",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_MOYENNE}


# ── Famille 3 — Médiane d'une série (effectif impair) ──────────────────────

def _gen_mediane_impair(rng: random.Random) -> Optional[dict]:
    n = rng.choice([5, 7, 9])
    valeurs = sorted(rng.sample(range(0, 30), n))
    mediane = valeurs[n // 2]
    valeurs_txt = " ; ".join(str(v) for v in valeurs)
    enonce = f"Voici une série statistique triée par ordre croissant : {valeurs_txt}. Déterminer sa médiane."
    answer = f"Médiane $= {mediane}$"
    steps = [
        f"Étape 1 — La série contient {n} valeurs (nombre impair), déjà triées.",
        f"Étape 2 — La médiane est la valeur centrale, en position {n // 2 + 1} : elle vaut {mediane}.",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_MEDIANE}


# ── Famille 4 — Médiane d'une série (effectif pair) ────────────────────────

def _gen_mediane_pair(rng: random.Random) -> Optional[dict]:
    n = rng.choice([6, 8])
    valeurs = sorted(rng.sample(range(0, 30), n))
    v1, v2 = valeurs[n // 2 - 1], valeurs[n // 2]
    mediane = Rational(v1 + v2, 2)
    valeurs_txt = " ; ".join(str(v) for v in valeurs)
    enonce = f"Voici une série statistique triée par ordre croissant : {valeurs_txt}. Déterminer sa médiane."
    answer = f"Médiane $= {latex(mediane)}$"
    steps = [
        f"Étape 1 — La série contient {n} valeurs (nombre pair), déjà triées.",
        f"Étape 2 — La médiane est la moyenne des deux valeurs centrales (positions {n // 2} et {n // 2 + 1}) : "
        f"$\\dfrac{{{v1} + {v2}}}{{2}} = {latex(mediane)}$.",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_MEDIANE}


# ── Famille 5 — Étendue d'une série ─────────────────────────────────────────

def _gen_etendue(rng: random.Random) -> Optional[dict]:
    n = rng.randint(6, 9)
    valeurs = [rng.randint(0, 40) for _ in range(n)]
    etendue = max(valeurs) - min(valeurs)
    valeurs_txt = " ; ".join(str(v) for v in valeurs)
    enonce = f"Une série statistique a pour valeurs : {valeurs_txt}. Calculer son étendue."
    answer = f"Étendue $= {etendue}$"
    steps = [
        f"Étape 1 — On identifie le maximum (${max(valeurs)}$) et le minimum (${min(valeurs)}$) de la série.",
        f"Étape 2 — L'étendue est leur différence : ${max(valeurs)} - {min(valeurs)} = {etendue}$.",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_MEDIANE}


# ── Familles supplémentaires — mission "diversification structurelle"
# (2026-09-02) : mediane_pair (93%) et moyenne_ponderee (93%) reposaient
# chacune sur UNE SEULE structure (liste de valeurs triées ; moyenne
# directe). Nouvelles familles : tableau d'EFFECTIFS (pas une simple liste)
# et problème INVERSE (retrouver une note manquante) — jamais mélangées à
# FAMILIES/generate_pool (baseline figée).

def _gen_mediane_tableau_effectifs(rng: random.Random) -> Optional[dict]:
    """Médiane à partir d'un TABLEAU D'EFFECTIFS (valeur → nombre
    d'occurrences), pas d'une simple liste déjà énumérée — il faut d'abord
    reconstituer l'effectif total et la position centrale, structure
    différente de _gen_mediane_pair/_gen_mediane_impair."""
    n_valeurs = rng.choice([3, 4])
    valeurs = sorted(rng.sample(range(0, 20), n_valeurs))
    effectifs = [rng.randint(2, 8) for _ in range(n_valeurs)]
    total = sum(effectifs)
    serie = []
    for v, e in zip(valeurs, effectifs):
        serie.extend([v] * e)
    serie.sort()
    if total % 2 == 0:
        mediane = Rational(serie[total // 2 - 1] + serie[total // 2], 2)
    else:
        mediane = serie[total // 2]
    table = ", ".join(f"{v} (effectif {e})" for v, e in zip(valeurs, effectifs))
    enonce = (
        f"Une série statistique est donnée par le tableau d'effectifs suivant : {table}. "
        f"Déterminer la médiane de cette série."
    )
    answer = f"Médiane $= {latex(mediane)}$"
    steps = [
        f"Étape 1 — L'effectif total est ${total}$ (somme des effectifs).",
        "Étape 2 — On reconstitue la série triée à partir des effectifs, puis on repère la ou les valeurs centrales.",
        f"Étape 3 — Médiane $= {latex(mediane)}$.",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_MEDIANE}


def _gen_moyenne_ponderee_inverse(rng: random.Random) -> Optional[dict]:
    """Problème INVERSE : la moyenne pondérée finale est donnée, une note
    est inconnue — il faut résoudre une équation, pas seulement appliquer la
    formule (structure différente de _gen_moyenne_ponderee)."""
    n = rng.randint(3, 4)
    valeurs_connues = [rng.randint(4, 18) for _ in range(n - 1)]
    poids = [rng.randint(1, 4) for _ in range(n)]
    note_inconnue = rng.randint(4, 18)
    total_poids = sum(poids)
    somme_ponderee = sum(v * p for v, p in zip(valeurs_connues, poids[:-1])) + note_inconnue * poids[-1]
    moyenne = Rational(somme_ponderee, total_poids)
    table = ", ".join(f"{v} (coefficient {p})" for v, p in zip(valeurs_connues, poids[:-1]))
    enonce = (
        f"Un élève a obtenu les notes suivantes : {table}, et une dernière note $x$ inconnue "
        f"(coefficient {poids[-1]}). Sachant que sa moyenne pondérée générale est ${latex(moyenne)}$, "
        f"déterminer $x$."
    )
    answer = f"$x = {note_inconnue}$"
    connu_latex = " + ".join(f"{v} \\times {p}" for v, p in zip(valeurs_connues, poids[:-1]))
    steps = [
        f"Étape 1 — La moyenne pondérée s'écrit $\\dfrac{{{connu_latex} + x \\times {poids[-1]}}}{{{total_poids}}} = {latex(moyenne)}$.",
        f"Étape 2 — En multipliant par ${total_poids}$ : ${sum(v*p for v,p in zip(valeurs_connues, poids[:-1]))} + {poids[-1]}x = {somme_ponderee}$.",
        f"Étape 3 — $x = \\dfrac{{{somme_ponderee} - {sum(v*p for v,p in zip(valeurs_connues, poids[:-1]))}}}{{{poids[-1]}}} = {note_inconnue}$.",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_MOYENNE}


EXTRA_FAMILY_BASE_SCORE: dict[str, float] = {
    "mediane_tableau_effectifs": 2.0,
    "moyenne_ponderee_inverse": 3.6,
}

EXTRA_FAMILIES: tuple[Family, ...] = (
    Family("mediane_tableau_effectifs", 2, "Médiane à partir d'un tableau d'effectifs", NOTION_MEDIANE,
           _gen_mediane_tableau_effectifs, "un tableau d'effectifs (valeur, effectif) à reconstituer",
           "reconstituer la série triée à partir des effectifs avant de repérer le centre"),
    Family("moyenne_ponderee_inverse", 4, "Retrouver une note connaissant la moyenne", NOTION_MOYENNE,
           _gen_moyenne_ponderee_inverse, "une moyenne pondérée finale connue, une note inconnue",
           "poser l'équation de la moyenne pondérée et résoudre en la note inconnue"),
)

EXTRA_FAMILIES_BY_ID: dict[str, Family] = {f.id: f for f in EXTRA_FAMILIES}


def _build_extra_exercise(family: Family, rng: random.Random) -> Optional[dict]:
    notes = family.generate(rng)
    if notes is None:
        return None
    score = EXTRA_FAMILY_BASE_SCORE[family.id]
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


def generate_extra_pool(per_family: int = 12, seed: int = 30260250) -> list[dict]:
    """Pool de diversification structurelle (mission 2026-09-02) — jamais
    mélangé à generate_pool()/FAMILIES (baseline figée). IDs à partir de
    GENERATED_ID_OFFSET + 8000."""
    rng = random.Random(seed)
    per_family_pool: dict[str, list[dict]] = {}
    for family in EXTRA_FAMILIES:
        seen_signatures = set()
        items = []
        attempts = 0
        while len(items) < per_family and attempts < per_family * 60:
            attempts += 1
            ex = _build_extra_exercise(family, rng)
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
        family = EXTRA_FAMILIES[idx % len(EXTRA_FAMILIES)]
        bucket = per_family_pool.get(family.id) or []
        if bucket:
            pool.append(bucket.pop(0))
        idx += 1
        if idx > 200000:
            break
    offset = GENERATED_ID_OFFSET + 8000
    for i, ex in enumerate(pool):
        ex["id"] = offset + i
    return pool


FAMILY_BASE_SCORE: dict[str, float] = {
    "etendue": 1.0,
    "moyenne_simple": 1.4,
    "mediane_impair": 1.8,
    "mediane_pair": 2.4,
    "moyenne_ponderee": 3.2,
}

FAMILIES: tuple[Family, ...] = (
    Family("etendue", 1, "Étendue d'une série", NOTION_MEDIANE, _gen_etendue,
           "une série de valeurs", "étendue = maximum - minimum"),
    Family("moyenne_simple", 1, "Moyenne simple", NOTION_MOYENNE, _gen_moyenne_simple,
           "une série de valeurs à moyenner", "somme des valeurs divisée par leur nombre"),
    Family("mediane_impair", 2, "Médiane (effectif impair)", NOTION_MEDIANE, _gen_mediane_impair,
           "une série triée de taille impaire", "la médiane est la valeur centrale"),
    Family("mediane_pair", 3, "Médiane (effectif pair)", NOTION_MEDIANE, _gen_mediane_pair,
           "une série triée de taille paire", "la médiane est la moyenne des deux valeurs centrales"),
    Family("moyenne_ponderee", 4, "Moyenne pondérée", NOTION_MOYENNE, _gen_moyenne_ponderee,
           "des valeurs affectées de coefficients différents", "somme des (valeur × coefficient) divisée par la somme des coefficients"),
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


def generate_pool(per_family: int = 12, seed: int = 30260203) -> list[dict]:
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
