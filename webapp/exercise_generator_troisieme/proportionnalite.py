"""Génération symbolique d'exercices sur la proportionnalité (Troisième,
Chapitre_6 : "Calculer une quatrième proportionnelle", "Reconnaître une
situation de proportionnalité", "Utiliser des pourcentages").

Même patron que webapp/exercise_generator_troisieme/equation_premier_degre.py.
Créé par la mission "rééquilibrage global de toutes les classes" (2026-09-01)
— Chapitre_6 était le chapitre le plus faible de Troisième (93 exercices,
aucun générateur).
"""
import random
from dataclasses import dataclass
from typing import Callable, Optional

from sympy import Rational, latex

CHAPTER_ID = "Chapitre_6"
NOTION_QUATRIEME = "Calculer une quatrième proportionnelle"
NOTION_RECONNAITRE = "Reconnaître une situation de proportionnalité"
NOTION_POURCENTAGE = "Utiliser des pourcentages"

GENERATED_ID_OFFSET = 190_000

LEVEL_META = {
    1: {"emoji": "🟢", "label": "Niveau 1 — Fondamental"},
    2: {"emoji": "🟡", "label": "Niveau 2 — Intermédiaire"},
    3: {"emoji": "🟠", "label": "Niveau 3 — Avancé"},
    4: {"emoji": "🔴", "label": "Niveau 4 — Difficile"},
    5: {"emoji": "🟣", "label": "Niveau 5 — Défi"},
}


def _nz(rng: random.Random, lo: int, hi: int) -> int:
    choices = [n for n in range(lo, hi + 1) if n != 0]
    return rng.choice(choices)


@dataclass(frozen=True)
class Family:
    id: str
    level: int
    label: str
    notion: str
    generate: Callable[[random.Random], Optional[dict]]
    structure_hint: str
    rule_hint: str


_CONTEXTES = [
    {"objet": "un gâteau", "unite_a": "personnes", "unite_b": "grammes de farine"},
    {"objet": "un trajet en voiture", "unite_a": "heures", "unite_b": "kilomètres"},
    {"objet": "une recette", "unite_a": "litres", "unite_b": "grammes de sucre"},
    {"objet": "un chantier", "unite_a": "ouvriers", "unite_b": "jours de travail"},
]


# ── Famille 1 — Quatrième proportionnelle (produit en croix) ───────────────

def _gen_quatrieme_proportionnelle(rng: random.Random) -> Optional[dict]:
    ctx = rng.choice(_CONTEXTES)
    a = rng.randint(2, 12)
    b = rng.randint(2, 12) * rng.randint(2, 8)
    c = rng.randint(2, 12)
    if a == c:
        return None
    x = Rational(b * c, a)
    enonce = (
        f"Pour {ctx['objet']}, {a} {ctx['unite_a']} nécessitent {b} {ctx['unite_b']}. "
        f"Combien de {ctx['unite_b']} faut-il pour {c} {ctx['unite_a']} ?"
    )
    answer = f"$x = {latex(x)}$ {ctx['unite_b']}"
    steps = [
        f"Étape 1 — On pose le tableau de proportionnalité : {a} {ctx['unite_a']} ↔ {b} {ctx['unite_b']}, "
        f"{c} {ctx['unite_a']} ↔ $x$.",
        f"Étape 2 — Produit en croix : $x = \\dfrac{{{b} \\times {c}}}{{{a}}} = {latex(x)}$.",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_QUATRIEME}


# ── Famille 2 — Reconnaître une situation de proportionnalité ──────────────

def _gen_reconnaitre(rng: random.Random) -> Optional[dict]:
    is_prop = rng.random() < 0.5
    a1, a2, a3 = sorted(rng.sample(range(1, 10), 3))
    if is_prop:
        k = Rational(rng.randint(2, 9), rng.choice([1, 2, 3]))
        b1, b2, b3 = k * a1, k * a2, k * a3
    else:
        k = Rational(rng.randint(2, 9), rng.choice([1, 2]))
        b1, b2, b3 = k * a1, k * a2 + rng.randint(1, 5), k * a3
    enonce = (
        f"Le tableau suivant est-il un tableau de proportionnalité ? "
        f"$x$ : {a1} ; {a2} ; {a3}  —  $y$ : {latex(b1)} ; {latex(b2)} ; {latex(b3)}. Justifier."
    )
    r1, r2, r3 = Rational(b1, a1), Rational(b2, a2), Rational(b3, a3)
    est_prop = r1 == r2 == r3
    if est_prop:
        answer = f"Oui : tous les rapports $y/x$ valent {latex(r1)}."
        steps = [
            f"Étape 1 — On calcule les rapports : $\\frac{{{latex(b1)}}}{{{a1}}} = {latex(r1)}$, "
            f"$\\frac{{{latex(b2)}}}{{{a2}}} = {latex(r2)}$, $\\frac{{{latex(b3)}}}{{{a3}}} = {latex(r3)}$.",
            f"Étape 2 — Les trois rapports sont égaux : {answer}",
        ]
    else:
        answer = f"Non : $\\frac{{{latex(b1)}}}{{{a1}}} = {latex(r1)}$ mais $\\frac{{{latex(b2)}}}{{{a2}}} = {latex(r2)}$, les rapports diffèrent."
        steps = [
            f"Étape 1 — On calcule les rapports : $\\frac{{{latex(b1)}}}{{{a1}}} = {latex(r1)}$, "
            f"$\\frac{{{latex(b2)}}}{{{a2}}} = {latex(r2)}$, $\\frac{{{latex(b3)}}}{{{a3}}} = {latex(r3)}$.",
            f"Étape 2 — Les rapports ne sont pas tous égaux : {answer}",
        ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_RECONNAITRE}


# ── Famille 3 — Pourcentage d'augmentation/diminution ──────────────────────
# valeur_initiale × (100±taux) est toujours un entier (deux entiers) : on
# l'affiche donc en décimal (centimes), jamais en fraction vulgaire — un prix
# ne se présente pas "en 1034/5 €".

def _fmt_centimes(numerateur_sur_100: int) -> str:
    entiers, centimes = divmod(numerateur_sur_100, 100)
    return f"{entiers}" if centimes == 0 else f"{entiers}.{centimes:02d}".rstrip("0").rstrip(".")


def _gen_pourcentage(rng: random.Random) -> Optional[dict]:
    valeur_initiale = rng.randint(20, 300)
    taux = rng.choice([5, 10, 15, 20, 25, 30, 40, 50])
    sens = rng.choice(["augmentation", "diminution"])
    if sens == "augmentation":
        numerateur = valeur_initiale * (100 + taux)
        valeur_finale_latex = _fmt_centimes(numerateur)
        coefficient_latex = _fmt_centimes(100 + taux)
        enonce = f"Un article coûte {valeur_initiale} €. Son prix augmente de {taux} %. Calculer le nouveau prix."
        answer = f"Nouveau prix $= {valeur_finale_latex}$ €"
        steps = [
            f"Étape 1 — Une augmentation de {taux} % correspond à un coefficient multiplicateur de "
            f"$1 + \\dfrac{{{taux}}}{{100}} = {coefficient_latex}$.",
            f"Étape 2 — Nouveau prix $= {valeur_initiale} \\times {coefficient_latex} = {valeur_finale_latex}$ €.",
        ]
    else:
        numerateur = valeur_initiale * (100 - taux)
        valeur_finale_latex = _fmt_centimes(numerateur)
        coefficient_latex = _fmt_centimes(100 - taux)
        enonce = f"Un article coûte {valeur_initiale} €. Son prix diminue de {taux} %. Calculer le nouveau prix."
        answer = f"Nouveau prix $= {valeur_finale_latex}$ €"
        steps = [
            f"Étape 1 — Une diminution de {taux} % correspond à un coefficient multiplicateur de "
            f"$1 - \\dfrac{{{taux}}}{{100}} = {coefficient_latex}$.",
            f"Étape 2 — Nouveau prix $= {valeur_initiale} \\times {coefficient_latex} = {valeur_finale_latex}$ €.",
        ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_POURCENTAGE}


# ── Famille 4 — Retrouver le taux à partir de deux valeurs ─────────────────

def _gen_retrouver_taux(rng: random.Random) -> Optional[dict]:
    valeur_initiale = rng.randint(20, 40) * 5
    taux = rng.choice([5, 10, 20, 25, 50])
    sens = rng.choice(["augmentation", "diminution"])
    if sens == "augmentation":
        valeur_finale = valeur_initiale + valeur_initiale * taux // 100
    else:
        valeur_finale = valeur_initiale - valeur_initiale * taux // 100
    if valeur_initiale * taux % 100 != 0:
        return None
    enonce = (
        f"Un prix passe de {valeur_initiale} € à {valeur_finale} €. "
        "Quel est le taux d'évolution en pourcentage ? Préciser s'il s'agit d'une augmentation ou d'une diminution."
    )
    variation = valeur_finale - valeur_initiale
    taux_calcule = Rational(abs(variation) * 100, valeur_initiale)
    mot = "augmentation" if variation > 0 else "diminution"
    answer = f"{mot.capitalize()} de {latex(taux_calcule)} %"
    steps = [
        f"Étape 1 — La variation est de ${variation}$ € (soit une {mot}).",
        f"Étape 2 — Le taux est $\\dfrac{{|{variation}|}}{{{valeur_initiale}}} \\times 100 = {latex(taux_calcule)}$ %.",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_POURCENTAGE}


# ── Familles supplémentaires — mission "diversification structurelle"
# (2026-09-02) : pourcentage (94%) et retrouver_taux (97%) reposaient sur UN
# SEUL scénario chacune (prix qui évolue une fois ; deux prix dont on
# déduit le taux). Nouvelles familles : problème INVERSE (retrouver le prix
# initial) et comparaison de deux évolutions — jamais mélangées à
# FAMILIES/generate_pool (baseline figée).

def _gen_pourcentage_prix_initial(rng: random.Random) -> Optional[dict]:
    """Problème INVERSE : le prix FINAL est donné, il faut retrouver le prix
    initial (division par le coefficient, pas multiplication) — structure
    différente de _gen_pourcentage."""
    prix_initial = rng.randint(20, 300)
    taux = rng.choice([5, 10, 20, 25, 50])
    sens = rng.choice(["augmentation", "diminution"])
    if sens == "augmentation":
        numerateur = prix_initial * (100 + taux)
    else:
        numerateur = prix_initial * (100 - taux)
    if numerateur % 100 != 0:
        return None
    prix_final = numerateur // 100
    coefficient_latex = _fmt_centimes(100 + taux) if sens == "augmentation" else _fmt_centimes(100 - taux)
    enonce = (
        f"Après une {sens} de {taux} %, un article coûte {prix_final} €. Quel était son prix initial ?"
    )
    answer = f"Prix initial $= {prix_initial}$ €"
    steps = [
        f"Étape 1 — Le coefficient multiplicateur de cette {sens} est ${coefficient_latex}$.",
        f"Étape 2 — Le prix initial vérifie $\\text{{prix initial}} \\times {coefficient_latex} = {prix_final}$, "
        f"donc $\\text{{prix initial}} = \\dfrac{{{prix_final}}}{{{coefficient_latex}}} = {prix_initial}$ €.",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_POURCENTAGE}


def _gen_comparer_taux(rng: random.Random) -> Optional[dict]:
    """Comparaison de DEUX évolutions distinctes — tâche de comparaison, pas
    seulement un calcul isolé (structure différente de _gen_retrouver_taux)."""
    v1_init = rng.randint(20, 40) * 5
    v1_final = v1_init + rng.choice([-1, 1]) * rng.randint(1, 8) * (v1_init // 20)
    v2_init = rng.randint(20, 40) * 5
    v2_final = v2_init + rng.choice([-1, 1]) * rng.randint(1, 8) * (v2_init // 20)
    t1 = Rational((v1_final - v1_init) * 100, v1_init)
    t2 = Rational((v2_final - v2_init) * 100, v2_init)
    if t1 == t2:
        return None
    plus_forte = "A" if abs(t1) > abs(t2) else "B"
    enonce = (
        f"Le prix d'un article A passe de {v1_init} € à {v1_final} €, et le prix d'un article B passe de "
        f"{v2_init} € à {v2_final} €. Quel article a subi l'évolution la plus importante en valeur relative ?"
    )
    answer = f"L'article {plus_forte} (taux de ${latex(t1)}\\%$ pour A contre ${latex(t2)}\\%$ pour B)."
    steps = [
        f"Étape 1 — Taux d'évolution de A : $\\dfrac{{{v1_final}-{v1_init}}}{{{v1_init}}} \\times 100 = {latex(t1)}\\%$.",
        f"Étape 2 — Taux d'évolution de B : $\\dfrac{{{v2_final}-{v2_init}}}{{{v2_init}}} \\times 100 = {latex(t2)}\\%$.",
        f"Étape 3 — On compare les valeurs ABSOLUES des deux taux : {answer}",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_POURCENTAGE}


EXTRA_FAMILY_BASE_SCORE: dict[str, float] = {
    "pourcentage_prix_initial": 2.6,
    "comparer_taux": 3.8,
}

EXTRA_FAMILIES: tuple[Family, ...] = (
    Family("pourcentage_prix_initial", 3, "Retrouver le prix initial", NOTION_POURCENTAGE,
           _gen_pourcentage_prix_initial, "un prix final et un taux d'évolution donnés",
           "diviser le prix final par le coefficient multiplicateur"),
    Family("comparer_taux", 4, "Comparer deux évolutions de pourcentage", NOTION_POURCENTAGE,
           _gen_comparer_taux, "deux évolutions de prix distinctes à comparer",
           "calculer les deux taux puis comparer leurs valeurs absolues"),
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
    "quatrieme_proportionnelle": 1.0,
    "reconnaitre": 1.6,
    "pourcentage": 2.2,
    "retrouver_taux": 3.4,
}

FAMILIES: tuple[Family, ...] = (
    Family("quatrieme_proportionnelle", 1, "Quatrième proportionnelle", NOTION_QUATRIEME,
           _gen_quatrieme_proportionnelle, "un tableau de proportionnalité à trois valeurs connues",
           "produit en croix"),
    Family("reconnaitre", 2, "Reconnaître une situation de proportionnalité", NOTION_RECONNAITRE,
           _gen_reconnaitre, "un tableau de valeurs à tester", "comparer les rapports y/x un par un"),
    Family("pourcentage", 2, "Appliquer un pourcentage", NOTION_POURCENTAGE, _gen_pourcentage,
           "une augmentation ou diminution en pourcentage", "utiliser le coefficient multiplicateur 1±t/100"),
    Family("retrouver_taux", 4, "Retrouver un taux d'évolution", NOTION_POURCENTAGE, _gen_retrouver_taux,
           "deux valeurs dont on cherche le taux d'évolution", "taux = variation/valeur initiale × 100"),
)

FAMILIES_BY_ID: dict[str, Family] = {f.id: f for f in FAMILIES}


def _difficulty_bucket_from_score(score: float) -> int:
    if score <= 1.3:
        return 1
    if score <= 1.9:
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


def generate_pool(per_family: int = 12, seed: int = 30260202) -> list[dict]:
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
