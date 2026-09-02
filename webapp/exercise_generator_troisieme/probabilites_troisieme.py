"""Génération symbolique d'exercices de probabilités (Troisième, Chapitre_10 :
"Construire et utiliser un arbre de probabilités", "Déterminer la probabilité
d'un événement", "Modéliser une expérience aléatoire et équiprobabilité").

Même patron que webapp/exercise_generator_troisieme/equation_premier_degre.py.
Créé par la mission "rééquilibrage global de toutes les classes" (2026-09-01)
— Chapitre_10 était l'un des chapitres les plus faibles de Troisième (98
exercices, aucun générateur).
"""
import random
from dataclasses import dataclass
from typing import Callable, Optional

from sympy import Rational, latex

CHAPTER_ID = "Chapitre_10"
NOTION_PROBA_EVENEMENT = "Déterminer la probabilité d'un événement"
NOTION_ARBRE = "Construire et utiliser un arbre de probabilités"
NOTION_MODELISER = "Modéliser une expérience aléatoire et équiprobabilité"

GENERATED_ID_OFFSET = 210_000

LEVEL_META = {
    1: {"emoji": "🟢", "label": "Niveau 1 — Fondamental"},
    2: {"emoji": "🟡", "label": "Niveau 2 — Intermédiaire"},
    3: {"emoji": "🟠", "label": "Niveau 3 — Avancé"},
    4: {"emoji": "🔴", "label": "Niveau 4 — Difficile"},
    5: {"emoji": "🟣", "label": "Niveau 5 — Défi"},
}

_URNES = [
    {"objet": "boules", "contenant": "un sac"},
    {"objet": "jetons", "contenant": "une urne"},
    {"objet": "cartes", "contenant": "un jeu"},
]


@dataclass(frozen=True)
class Family:
    id: str
    level: int
    label: str
    notion: str
    generate: Callable[[random.Random], Optional[dict]]
    structure_hint: str
    rule_hint: str


# ── Famille 1 — Probabilité d'un événement (tirage équiprobable) ──────────

def _gen_proba_evenement(rng: random.Random) -> Optional[dict]:
    ctx = rng.choice(_URNES)
    couleurs = rng.sample(["rouge", "bleu", "vert", "jaune", "noir"], rng.choice([2, 3]))
    effectifs = [rng.randint(2, 8) for _ in couleurs]
    total = sum(effectifs)
    idx_cible = rng.randrange(len(couleurs))
    proba = Rational(effectifs[idx_cible], total)
    description = ", ".join(f"{n} {ctx['objet']} de couleur {c}" for n, c in zip(effectifs, couleurs))
    enonce = (
        f"{ctx['contenant'].capitalize()} contient {description}, indiscernables au toucher. "
        f"On tire un objet au hasard. Quelle est la probabilité de tirer un objet de couleur {couleurs[idx_cible]} ?"
    )
    answer = f"$P = {latex(proba)}$"
    steps = [
        f"Étape 1 — Il y a {total} {ctx['objet']} au total, tous équiprobables.",
        f"Étape 2 — {effectifs[idx_cible]} {ctx['objet']} sont de couleur {couleurs[idx_cible]} : "
        f"$P = \\dfrac{{{effectifs[idx_cible]}}}{{{total}}} = {latex(proba)}$.",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_PROBA_EVENEMENT}


# ── Famille 2 — Événement contraire ─────────────────────────────────────────

def _gen_evenement_contraire(rng: random.Random) -> Optional[dict]:
    ctx = rng.choice(_URNES)
    total = rng.randint(8, 20)
    favorables = rng.randint(1, total - 1)
    proba = Rational(favorables, total)
    proba_contraire = 1 - proba
    enonce = (
        f"{ctx['contenant'].capitalize()} contient {total} {ctx['objet']}, dont {favorables} "
        "permettent de gagner. On tire un objet au hasard. Quelle est la probabilité qu'il ne permette PAS de gagner ?"
    )
    answer = f"$P(\\text{{non gagnant}}) = {latex(proba_contraire)}$"
    steps = [
        f"Étape 1 — $P(\\text{{gagnant}}) = \\dfrac{{{favorables}}}{{{total}}} = {latex(proba)}$.",
        f"Étape 2 — $P(\\text{{non gagnant}}) = 1 - P(\\text{{gagnant}}) = 1 - {latex(proba)} = {latex(proba_contraire)}$.",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_PROBA_EVENEMENT}


# ── Famille 3 — Modéliser une expérience à deux épreuves (arbre simple) ───

def _gen_arbre_deux_epreuves(rng: random.Random) -> Optional[dict]:
    p1 = Rational(rng.randint(1, 4), rng.choice([4, 5, 6]))
    p2 = Rational(rng.randint(1, 4), rng.choice([4, 5, 6]))
    if p1 >= 1 or p2 >= 1:
        return None
    proba_deux = p1 * p2
    enonce = (
        f"Une expérience aléatoire comporte deux épreuves indépendantes. La probabilité de succès à la "
        f"première épreuve est ${latex(p1)}$, et à la seconde ${latex(p2)}$. "
        "Quelle est la probabilité de réussir les deux épreuves ?"
    )
    answer = f"$P = {latex(proba_deux)}$"
    steps = [
        "Étape 1 — Les deux épreuves étant indépendantes, on multiplie les probabilités le long des branches de l'arbre.",
        f"Étape 2 — $P(\\text{{succès}},\\text{{succès}}) = {latex(p1)} \\times {latex(p2)} = {latex(proba_deux)}$.",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_ARBRE}


# ── Famille 4 — Dénombrer les issues d'une expérience à deux épreuves ─────

def _gen_denombrement(rng: random.Random) -> Optional[dict]:
    n1 = rng.randint(2, 6)
    n2 = rng.randint(2, 6)
    total = n1 * n2
    enonce = (
        f"On lance successivement deux objets : le premier peut donner {n1} résultats différents, "
        f"le second {n2} résultats différents. Combien l'expérience complète (les deux lancers) "
        "compte-t-elle d'issues possibles au total ?"
    )
    answer = f"${total}$ issues possibles"
    steps = [
        "Étape 1 — On utilise le principe multiplicatif : le nombre total d'issues est le produit des "
        "nombres de résultats possibles à chaque épreuve.",
        f"Étape 2 — ${n1} \\times {n2} = {total}$.",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_MODELISER}


# ── Famille 5 — Équiprobabilité, retrouver un effectif ─────────────────────

def _gen_retrouver_effectif(rng: random.Random) -> Optional[dict]:
    total = rng.randint(10, 40)
    proba = Rational(rng.randint(1, 4), rng.choice([2, 4, 5]))
    if proba >= 1:
        return None
    effectif = proba * total
    if effectif != int(effectif):
        return None
    effectif = int(effectif)
    enonce = (
        f"Un sac contient {total} jetons indiscernables au toucher. La probabilité de tirer un jeton "
        f"rouge est ${latex(proba)}$. Combien de jetons rouges le sac contient-il ?"
    )
    answer = f"${effectif}$ jetons rouges"
    steps = [
        f"Étape 1 — $P(\\text{{rouge}}) = \\dfrac{{\\text{{effectif rouge}}}}{{{total}}} = {latex(proba)}$.",
        f"Étape 2 — Effectif rouge $= {latex(proba)} \\times {total} = {effectif}$.",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_MODELISER}


# ── Familles supplémentaires — mission "diversification structurelle"
# (2026-09-02) : arbre_deux_epreuves (96%), retrouver_effectif (96%) et
# denombrement (95%) reposaient chacune sur UNE SEULE structure. Nouvelles
# familles : probabilité d'EXACTEMENT UN succès (somme de deux chemins),
# effectif TOTAL inconnu (au lieu de l'effectif favorable), et dénombrement
# SANS répétition — jamais mélangées à FAMILIES/generate_pool (baseline
# figée).

def _gen_arbre_exactement_un_succes(rng: random.Random) -> Optional[dict]:
    """Probabilité d'obtenir EXACTEMENT UN succès sur deux épreuves : il faut
    additionner DEUX chemins de l'arbre (succès-échec et échec-succès), pas
    un seul produit — structure différente de _gen_arbre_deux_epreuves."""
    p1 = Rational(rng.randint(1, 4), rng.choice([4, 5, 6]))
    p2 = Rational(rng.randint(1, 4), rng.choice([4, 5, 6]))
    if p1 >= 1 or p2 >= 1:
        return None
    chemin1 = p1 * (1 - p2)
    chemin2 = (1 - p1) * p2
    proba = chemin1 + chemin2
    enonce = (
        f"Une expérience aléatoire comporte deux épreuves indépendantes. La probabilité de succès à la "
        f"première épreuve est ${latex(p1)}$, et à la seconde ${latex(p2)}$. "
        "Quelle est la probabilité d'obtenir EXACTEMENT un succès sur les deux épreuves ?"
    )
    answer = f"$P = {latex(proba)}$"
    steps = [
        "Étape 1 — « Exactement un succès » correspond à deux chemins de l'arbre : "
        "(succès, échec) ou (échec, succès).",
        f"Étape 2 — $P(\\text{{succès,échec}}) = {latex(p1)} \\times {latex(1-p2)} = {latex(chemin1)}$ et "
        f"$P(\\text{{échec,succès}}) = {latex(1-p1)} \\times {latex(p2)} = {latex(chemin2)}$.",
        f"Étape 3 — $P = {latex(chemin1)} + {latex(chemin2)} = {latex(proba)}$.",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_ARBRE}


def _gen_retrouver_effectif_total(rng: random.Random) -> Optional[dict]:
    """L'effectif TOTAL est inconnu (l'effectif favorable est donné) —
    position de l'inconnue différente de _gen_retrouver_effectif (qui donne
    le total et cherche le favorable)."""
    effectif_favorable = rng.randint(3, 20)
    proba = Rational(rng.randint(1, 4), rng.choice([2, 5, 8, 10]))
    if proba >= 1:
        return None
    total = effectif_favorable / proba
    if total != int(total):
        return None
    total = int(total)
    enonce = (
        f"Un sac contient un certain nombre de jetons indiscernables au toucher, dont {effectif_favorable} "
        f"sont rouges. La probabilité de tirer un jeton rouge est ${latex(proba)}$. "
        "Combien de jetons le sac contient-il au total ?"
    )
    answer = f"${total}$ jetons au total"
    steps = [
        f"Étape 1 — $P(\\text{{rouge}}) = \\dfrac{{{effectif_favorable}}}{{\\text{{effectif total}}}} = {latex(proba)}$.",
        f"Étape 2 — Effectif total $= \\dfrac{{{effectif_favorable}}}{{{latex(proba)}}} = {total}$.",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_MODELISER}


def _gen_denombrement_sans_repetition(rng: random.Random) -> Optional[dict]:
    """Dénombrement SANS répétition (le second résultat ne peut pas être
    identique au premier) : $n \\times (n-1)$ au lieu de $n \\times n$ —
    structure différente de _gen_denombrement (issues indépendantes)."""
    n = rng.randint(3, 8)
    total = n * (n - 1)
    enonce = (
        f"On tire successivement, sans remise, deux jetons numérotés parmi {n} jetons distincts. "
        "Combien y a-t-il de tirages possibles (en tenant compte de l'ordre) ?"
    )
    answer = f"${total}$ tirages possibles"
    steps = [
        f"Étape 1 — Pour le premier jeton, il y a ${n}$ possibilités.",
        f"Étape 2 — Sans remise, il ne reste plus que ${n-1}$ possibilités pour le second jeton (le premier "
        "ne peut pas être retiré une seconde fois).",
        f"Étape 3 — Nombre total de tirages $= {n} \\times {n-1} = {total}$.",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_MODELISER}


EXTRA_FAMILY_BASE_SCORE: dict[str, float] = {
    "denombrement_sans_repetition": 1.6,
    "retrouver_effectif_total": 3.2,
    "arbre_exactement_un_succes": 4.0,
}

EXTRA_FAMILIES: tuple[Family, ...] = (
    Family("denombrement_sans_repetition", 2, "Dénombrer sans répétition", NOTION_MODELISER,
           _gen_denombrement_sans_repetition, "un tirage successif sans remise",
           "n possibilités puis (n-1), sans répétition du même élément"),
    Family("retrouver_effectif_total", 3, "Retrouver l'effectif total", NOTION_MODELISER,
           _gen_retrouver_effectif_total, "un effectif favorable et une probabilité connus, le total inconnu",
           "effectif total = effectif favorable / probabilité"),
    Family("arbre_exactement_un_succes", 4, "Exactement un succès sur deux épreuves", NOTION_ARBRE,
           _gen_arbre_exactement_un_succes, "deux épreuves indépendantes, un seul succès exigé",
           "additionner les deux chemins (succès,échec) et (échec,succès)"),
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


def generate_extra_pool(per_family: int = 12, seed: int = 30260450) -> list[dict]:
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
    "denombrement": 1.0,
    "proba_evenement": 1.6,
    "evenement_contraire": 2.2,
    "retrouver_effectif": 3.0,
    "arbre_deux_epreuves": 3.6,
}

FAMILIES: tuple[Family, ...] = (
    Family("denombrement", 1, "Dénombrer les issues (principe multiplicatif)", NOTION_MODELISER,
           _gen_denombrement, "deux épreuves successives", "multiplier le nombre de résultats possibles à chaque épreuve"),
    Family("proba_evenement", 2, "Probabilité d'un événement", NOTION_PROBA_EVENEMENT, _gen_proba_evenement,
           "un tirage équiprobable dans un ensemble d'objets", "P = effectif favorable / effectif total"),
    Family("evenement_contraire", 2, "Événement contraire", NOTION_PROBA_EVENEMENT, _gen_evenement_contraire,
           "un événement et son contraire", "P(non A) = 1 - P(A)"),
    Family("retrouver_effectif", 3, "Retrouver un effectif à partir d'une probabilité", NOTION_MODELISER,
           _gen_retrouver_effectif, "une probabilité et un effectif total connus", "effectif favorable = P × effectif total"),
    Family("arbre_deux_epreuves", 4, "Arbre à deux épreuves indépendantes", NOTION_ARBRE,
           _gen_arbre_deux_epreuves, "deux épreuves indépendantes successives", "multiplier les probabilités le long d'un chemin de l'arbre"),
)

FAMILIES_BY_ID: dict[str, Family] = {f.id: f for f in FAMILIES}


def _difficulty_bucket_from_score(score: float) -> int:
    if score <= 1.3:
        return 1
    if score <= 1.9:
        return 2
    if score <= 2.6:
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


def generate_pool(per_family: int = 12, seed: int = 30260204) -> list[dict]:
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
