"""Génération symbolique d'exercices de probabilités conditionnelles
(Première, Chapitre_9 : "Probabilité conditionnelle", "Arbres pondérés",
"Notion d'indépendance").

Même patron que webapp/exercise_generator/second_degre.py : familles à score
fixe, toute probabilité manipulée en fraction exacte (sympy.Rational),
jamais en décimal approché. Voir
webapp/exercise_generator/trigonometrie.py pour le contexte de la mission
"rééquilibrage additif" (2026-09-01).
"""
import random
from dataclasses import dataclass
from typing import Callable, Optional

from sympy import Rational, latex

CHAPTER_ID = "Chapitre_9"
NOTION_PROBA_COND = "Probabilité conditionnelle"
NOTION_ARBRES = "Arbres pondérés"
NOTION_INDEPENDANCE = "Notion d'indépendance"

GENERATED_ID_OFFSET = 990_000

LEVEL_META = {
    1: {"emoji": "🟢", "label": "Niveau 1 — Fondamental"},
    2: {"emoji": "🟡", "label": "Niveau 2 — Intermédiaire"},
    3: {"emoji": "🟠", "label": "Niveau 3 — Avancé"},
    4: {"emoji": "🔴", "label": "Niveau 4 — Difficile"},
    5: {"emoji": "🟣", "label": "Niveau 5 — Défi"},
}


def _rat(rng: random.Random, den_choices=(2, 3, 4, 5, 6, 8, 10)) -> Rational:
    den = rng.choice(den_choices)
    num = rng.randint(1, den - 1)
    return Rational(num, den)


@dataclass(frozen=True)
class Family:
    id: str
    level: int
    label: str
    notion: str
    generate: Callable[[random.Random], Optional[dict]]
    structure_hint: str
    rule_hint: str


# ── Famille 1 — Multiplication : P(A∩B) = P(A) × P_A(B) ────────────────────

def _gen_intersection(rng: random.Random) -> Optional[dict]:
    pa = _rat(rng)
    pab = _rat(rng)
    inter = pa * pab
    enonce = (
        f"On donne $P(A) = {latex(pa)}$ et $P_A(B) = {latex(pab)}$. Calculer $P(A \\cap B)$."
    )
    answer = f"$P(A \\cap B) = {latex(inter)}$"
    steps = [
        "Étape 1 — On utilise la formule des probabilités composées $P(A \\cap B) = P(A) \\times P_A(B)$.",
        f"Étape 2 — $P(A \\cap B) = {latex(pa)} \\times {latex(pab)} = {latex(inter)}$.",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_ARBRES}


# ── Famille 2 — Division : P_A(B) = P(A∩B) / P(A) ──────────────────────────

def _gen_proba_conditionnelle(rng: random.Random) -> Optional[dict]:
    pa = _rat(rng)
    pab = pa * _rat(rng, den_choices=(2, 3, 4))
    if pab == 0 or pab > pa:
        return None
    resultat = pab / pa
    enonce = f"On donne $P(A) = {latex(pa)}$ et $P(A \\cap B) = {latex(pab)}$. Calculer $P_A(B)$."
    answer = f"$P_A(B) = {latex(resultat)}$"
    steps = [
        "Étape 1 — On utilise la définition $P_A(B) = \\dfrac{P(A \\cap B)}{P(A)}$.",
        f"Étape 2 — $P_A(B) = \\dfrac{{{latex(pab)}}}{{{latex(pa)}}} = {latex(resultat)}$.",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_PROBA_COND}


# ── Famille 3 — Formule des probabilités totales ───────────────────────────

def _gen_probabilites_totales(rng: random.Random) -> Optional[dict]:
    pa = _rat(rng, den_choices=(2, 3, 4, 5))
    pab = _rat(rng)
    panonb = _rat(rng)
    pb = pa * pab + (1 - pa) * panonb
    enonce = (
        f"Un arbre pondéré donne $P(A) = {latex(pa)}$, $P_A(B) = {latex(pab)}$ et "
        f"$P_{{\\overline{{A}}}}(B) = {latex(panonb)}$. Calculer $P(B)$."
    )
    answer = f"$P(B) = {latex(pb)}$"
    steps = [
        "Étape 1 — On utilise la formule des probabilités totales : "
        "$P(B) = P(A)\\times P_A(B) + P(\\overline{A})\\times P_{\\overline{A}}(B)$.",
        f"Étape 2 — $P(\\overline{{A}}) = 1 - {latex(pa)} = {latex(1-pa)}$.",
        f"Étape 3 — $P(B) = {latex(pa)} \\times {latex(pab)} + {latex(1-pa)} \\times {latex(panonb)} = {latex(pb)}$.",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_ARBRES}


# ── Famille 4 — Test d'indépendance ─────────────────────────────────────────

def _gen_test_independance(rng: random.Random) -> Optional[dict]:
    pa = _rat(rng)
    pb = _rat(rng)
    force_independant = rng.random() < 0.5
    if force_independant:
        pab = pa * pb
    else:
        pab = _rat(rng)
        if pab == pa * pb:
            return None
    produit = pa * pb
    est_indep = pab == produit
    enonce = (
        f"On donne $P(A) = {latex(pa)}$, $P(B) = {latex(pb)}$ et $P(A \\cap B) = {latex(pab)}$. "
        "Les événements $A$ et $B$ sont-ils indépendants ? Justifier."
    )
    if est_indep:
        answer = f"Oui : $P(A) \\times P(B) = {latex(produit)} = P(A \\cap B)$, donc $A$ et $B$ sont indépendants."
    else:
        answer = f"Non : $P(A) \\times P(B) = {latex(produit)} \\neq {latex(pab)} = P(A \\cap B)$, donc $A$ et $B$ ne sont pas indépendants."
    steps = [
        "Étape 1 — $A$ et $B$ sont indépendants si et seulement si $P(A \\cap B) = P(A) \\times P(B)$.",
        f"Étape 2 — $P(A) \\times P(B) = {latex(pa)} \\times {latex(pb)} = {latex(produit)}$.",
        f"Étape 3 — {answer}",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_INDEPENDANCE}


# ── Famille 5 — Bayes simple : retrouver P_B(A) à partir de l'arbre ────────

def _gen_bayes_simple(rng: random.Random) -> Optional[dict]:
    pa = _rat(rng, den_choices=(2, 3, 4, 5))
    pab = _rat(rng, den_choices=(2, 3, 4))
    panonb = _rat(rng, den_choices=(2, 3, 4))
    p_inter = pa * pab
    p_nona_inter = (1 - pa) * panonb
    pb = p_inter + p_nona_inter
    if pb == 0:
        return None
    p_a_sachant_b = p_inter / pb
    enonce = (
        f"Un arbre pondéré donne $P(A) = {latex(pa)}$, $P_A(B) = {latex(pab)}$ et "
        f"$P_{{\\overline{{A}}}}(B) = {latex(panonb)}$. Calculer $P_B(A)$."
    )
    answer = f"$P_B(A) = {latex(p_a_sachant_b)}$"
    steps = [
        f"Étape 1 — On calcule $P(A \\cap B) = P(A) \\times P_A(B) = {latex(pa)} \\times {latex(pab)} = {latex(p_inter)}$.",
        f"Étape 2 — On calcule $P(B) = P(A \\cap B) + P(\\overline{{A}} \\cap B) = {latex(p_inter)} + "
        f"{latex(1-pa)} \\times {latex(panonb)} = {latex(pb)}$.",
        f"Étape 3 — $P_B(A) = \\dfrac{{P(A \\cap B)}}{{P(B)}} = \\dfrac{{{latex(p_inter)}}}{{{latex(pb)}}} = {latex(p_a_sachant_b)}$.",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_PROBA_COND}


# ── Famille 6 — Compléter une probabilité manquante dans un arbre ─────────

def _gen_completer_arbre(rng: random.Random) -> Optional[dict]:
    pab = _rat(rng, den_choices=(3, 4, 5, 6))
    complement = 1 - pab
    branche = rng.choice(["B", "\\overline{B}"])
    donnee, cherchee = (pab, complement) if branche == "B" else (complement, pab)
    branche_cherchee = "\\overline{B}" if branche == "B" else "B"
    enonce = (
        f"Dans un arbre pondéré, sachant $A$ réalisé, on a $P_A({branche}) = {latex(donnee)}$. "
        f"Calculer $P_A({branche_cherchee})$."
    )
    answer = f"$P_A({branche_cherchee}) = {latex(cherchee)}$"
    steps = [
        f"Étape 1 — Sur les branches issues de $A$, les probabilités s'ajoutent à 1 : "
        f"$P_A(B) + P_A(\\overline{{B}}) = 1$.",
        f"Étape 2 — $P_A({branche_cherchee}) = 1 - {latex(donnee)} = {latex(cherchee)}$.",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_ARBRES}


FAMILY_BASE_SCORE: dict[str, float] = {
    "completer_arbre": 1.0,
    "intersection": 1.4,
    "proba_conditionnelle": 2.0,
    "test_independance": 2.6,
    "probabilites_totales": 3.2,
    "bayes_simple": 4.2,
}

FAMILIES: tuple[Family, ...] = (
    Family("completer_arbre", 1, "Compléter une probabilité manquante", NOTION_ARBRES, _gen_completer_arbre,
           "deux branches complémentaires issues d'un même nœud", "les probabilités des branches d'un même nœud somment à 1"),
    Family("intersection", 1, "Probabilité d'une intersection", NOTION_ARBRES, _gen_intersection,
           "une probabilité et une probabilité conditionnelle données", "P(A∩B) = P(A) × P_A(B)"),
    Family("proba_conditionnelle", 2, "Calcul d'une probabilité conditionnelle", NOTION_PROBA_COND,
           _gen_proba_conditionnelle, "une intersection et une probabilité données",
           "P_A(B) = P(A∩B) / P(A)"),
    Family("test_independance", 3, "Test d'indépendance de deux événements", NOTION_INDEPENDANCE,
           _gen_test_independance, "deux événements dont on teste l'indépendance",
           "A et B indépendants ⟺ P(A∩B) = P(A)×P(B)"),
    Family("probabilites_totales", 3, "Formule des probabilités totales", NOTION_ARBRES,
           _gen_probabilites_totales, "un arbre à deux branches principales",
           "P(B) = P(A)P_A(B) + P(non A)P_(non A)(B)"),
    Family("bayes_simple", 4, "Probabilité conditionnelle inverse (Bayes)", NOTION_PROBA_COND,
           _gen_bayes_simple, "un arbre complet dont on veut inverser le conditionnement",
           "calculer P(A∩B) et P(B), puis diviser"),
)

FAMILIES_BY_ID: dict[str, Family] = {f.id: f for f in FAMILIES}


def _difficulty_bucket_from_score(score: float) -> int:
    if score <= 1.2:
        return 1
    if score <= 2.2:
        return 2
    if score <= 2.9:
        return 3
    if score <= 3.7:
        return 4
    return 5


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


def generate_pool(per_family: int = 12, seed: int = 20260904) -> list[dict]:
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
