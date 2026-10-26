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


# ── Familles supplémentaires — mission "diversification structurelle"
# (2026-09-02) : les 6 familles ci-dessus reposent chacune sur UN SEUL type
# de tâche (toujours "des fractions données -> appliquer une formule"),
# auditées à 98-99% de quasi-doublon. Nouvelles familles : représentations
# différentes (tableau d'effectifs, tirage sans remise, arbre à 3 branches)
# et tâches différentes (détection d'erreur) — jamais mélangées à
# FAMILIES/generate_pool (baseline figée).

def _gen_intersection_tirage(rng: random.Random) -> Optional[dict]:
    """Contexte de tirage sans remise : P(A) et P_A(B) ne sont pas donnés
    directement, il faut les déduire d'un effectif (structure différente de
    _gen_intersection, où les probabilités sont fournies telles quelles)."""
    n_rouges = rng.randint(3, 10)
    n_total = n_rouges + rng.randint(3, 10)
    pa = Rational(n_rouges, n_total)
    pab = Rational(n_rouges - 1, n_total - 1)
    inter = pa * pab
    enonce = (
        f"Une urne contient ${n_total}$ boules, dont ${n_rouges}$ rouges. On tire successivement et sans "
        f"remise deux boules. On note $A$ : « la première boule tirée est rouge » et $B$ : « la deuxième "
        f"boule tirée est rouge ». Calculer $P(A \\cap B)$."
    )
    answer = f"$P(A \\cap B) = {latex(inter)}$"
    steps = [
        f"Étape 1 — $P(A) = \\dfrac{{{n_rouges}}}{{{n_total}}} = {latex(pa)}$.",
        f"Étape 2 — Sans remise, il reste ${n_rouges - 1}$ boules rouges parmi ${n_total - 1}$ : "
        f"$P_A(B) = \\dfrac{{{n_rouges - 1}}}{{{n_total - 1}}} = {latex(pab)}$.",
        f"Étape 3 — $P(A \\cap B) = P(A) \\times P_A(B) = {latex(pa)} \\times {latex(pab)} = {latex(inter)}$.",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_ARBRES}


def _gen_proba_conditionnelle_tableau(rng: random.Random) -> Optional[dict]:
    """Tableau croisé d'effectifs (pas de fraction donnée à l'avance) —
    structure différente de _gen_proba_conditionnelle."""
    a_et_b = rng.randint(5, 30)
    a_et_nonb = rng.randint(5, 30)
    n_a = a_et_b + a_et_nonb
    resultat = Rational(a_et_b, n_a)
    enonce = (
        f"Dans une classe, on a interrogé les élèves sur leur pratique du sport ($A$) et de la musique ($B$). "
        f"Parmi les ${n_a}$ élèves pratiquant un sport ($A$), ${a_et_b}$ pratiquent aussi la musique. "
        f"Calculer $P_A(B)$."
    )
    answer = f"$P_A(B) = {latex(resultat)}$"
    steps = [
        f"Étape 1 — Parmi les élèves de $A$ (au total ${n_a}$), on compte ceux qui sont aussi dans $B$ (${a_et_b}$).",
        f"Étape 2 — $P_A(B) = \\dfrac{{\\text{{effectif}}(A \\cap B)}}{{\\text{{effectif}}(A)}} = \\dfrac{{{a_et_b}}}{{{n_a}}} = {latex(resultat)}$.",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_PROBA_COND}


def _gen_probabilites_totales_trois_branches(rng: random.Random) -> Optional[dict]:
    """Partition en TROIS événements (pas deux) — la formule des probabilités
    totales comporte trois termes, pas deux."""
    p1 = _rat(rng, den_choices=(6, 8, 10, 12))
    p2 = _rat(rng, den_choices=(6, 8, 10, 12))
    if p1 + p2 >= 1:
        return None
    p3 = 1 - p1 - p2
    pb1, pb2, pb3 = _rat(rng), _rat(rng), _rat(rng)
    pb = p1 * pb1 + p2 * pb2 + p3 * pb3
    enonce = (
        f"Un univers est partagé en trois événements $A_1$, $A_2$, $A_3$ avec $P(A_1)={latex(p1)}$, "
        f"$P(A_2)={latex(p2)}$, $P(A_3)={latex(p3)}$. On donne $P_{{A_1}}(B)={latex(pb1)}$, "
        f"$P_{{A_2}}(B)={latex(pb2)}$, $P_{{A_3}}(B)={latex(pb3)}$. Calculer $P(B)$."
    )
    answer = f"$P(B) = {latex(pb)}$"
    steps = [
        "Étape 1 — Avec une partition en trois événements, "
        "$P(B) = P(A_1)P_{A_1}(B) + P(A_2)P_{A_2}(B) + P(A_3)P_{A_3}(B)$.",
        f"Étape 2 — $P(B) = {latex(p1)} \\times {latex(pb1)} + {latex(p2)} \\times {latex(pb2)} + "
        f"{latex(p3)} \\times {latex(pb3)} = {latex(pb)}$.",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_ARBRES}


def _gen_test_independance_tableau(rng: random.Random) -> Optional[dict]:
    """Tableau croisé d'effectifs bruts — il faut calculer P(A), P(B) et
    P(A∩B) à partir des comptages avant de tester l'indépendance (structure
    différente de _gen_test_independance, où les probabilités sont déjà
    fournies)."""
    a_et_b = rng.randint(5, 25)
    a_et_nonb = rng.randint(5, 25)
    nona_et_b = rng.randint(5, 25)
    nona_et_nonb = rng.randint(5, 25)
    n = a_et_b + a_et_nonb + nona_et_b + nona_et_nonb
    n_a = a_et_b + a_et_nonb
    n_b = a_et_b + nona_et_b
    pa = Rational(n_a, n)
    pb = Rational(n_b, n)
    pab = Rational(a_et_b, n)
    produit = pa * pb
    est_indep = pab == produit
    enonce = (
        f"Une enquête auprès de ${n}$ personnes donne : ${a_et_b}$ vérifient à la fois $A$ et $B$, "
        f"${a_et_nonb}$ vérifient $A$ sans $B$, ${nona_et_b}$ vérifient $B$ sans $A$, et ${nona_et_nonb}$ "
        f"ne vérifient ni $A$ ni $B$. Les événements $A$ et $B$ sont-ils indépendants ?"
    )
    if est_indep:
        answer = f"Oui : $P(A) \\times P(B) = {latex(produit)} = P(A \\cap B)$, donc $A$ et $B$ sont indépendants."
    else:
        answer = f"Non : $P(A) \\times P(B) = {latex(produit)} \\neq {latex(pab)} = P(A \\cap B)$, donc $A$ et $B$ ne sont pas indépendants."
    steps = [
        f"Étape 1 — $P(A) = \\dfrac{{{n_a}}}{{{n}}} = {latex(pa)}$, $P(B) = \\dfrac{{{n_b}}}{{{n}}} = {latex(pb)}$, "
        f"$P(A \\cap B) = \\dfrac{{{a_et_b}}}{{{n}}} = {latex(pab)}$.",
        f"Étape 2 — $P(A) \\times P(B) = {latex(produit)}$.",
        f"Étape 3 — {answer}",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_INDEPENDANCE}


def _gen_bayes_trois_branches(rng: random.Random) -> Optional[dict]:
    """Bayes avec une partition à TROIS événements : le dénominateur de la
    formule de Bayes comporte trois termes au lieu de deux (structure
    réellement plus complexe que _gen_bayes_simple)."""
    p1 = _rat(rng, den_choices=(6, 8, 10))
    p2 = _rat(rng, den_choices=(6, 8, 10))
    if p1 + p2 >= 1:
        return None
    p3 = 1 - p1 - p2
    pb1, pb2, pb3 = _rat(rng, (2, 3, 4)), _rat(rng, (2, 3, 4)), _rat(rng, (2, 3, 4))
    inter1, inter2, inter3 = p1 * pb1, p2 * pb2, p3 * pb3
    pb = inter1 + inter2 + inter3
    if pb == 0:
        return None
    p_a1_sachant_b = inter1 / pb
    enonce = (
        f"Un univers est partagé en trois événements $A_1$, $A_2$, $A_3$ avec $P(A_1)={latex(p1)}$, "
        f"$P(A_2)={latex(p2)}$, $P(A_3)={latex(p3)}$, et $P_{{A_1}}(B)={latex(pb1)}$, $P_{{A_2}}(B)={latex(pb2)}$, "
        f"$P_{{A_3}}(B)={latex(pb3)}$. Calculer $P_B(A_1)$."
    )
    answer = f"$P_B(A_1) = {latex(p_a1_sachant_b)}$"
    steps = [
        f"Étape 1 — $P(A_1 \\cap B) = {latex(p1)} \\times {latex(pb1)} = {latex(inter1)}$ "
        f"(de même $P(A_2 \\cap B) = {latex(inter2)}$, $P(A_3 \\cap B) = {latex(inter3)}$).",
        f"Étape 2 — $P(B) = {latex(inter1)} + {latex(inter2)} + {latex(inter3)} = {latex(pb)}$.",
        f"Étape 3 — $P_B(A_1) = \\dfrac{{P(A_1 \\cap B)}}{{P(B)}} = \\dfrac{{{latex(inter1)}}}{{{latex(pb)}}} = {latex(p_a1_sachant_b)}$.",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_PROBA_COND}


def _gen_completer_arbre_erreur(rng: random.Random) -> Optional[dict]:
    """Détection d'erreur : un arbre erroné est présenté (les deux branches
    issues de A ne somment pas à 1), il faut identifier et corriger l'erreur
    — tâche différente de _gen_completer_arbre (qui ne fait que compléter)."""
    pab = _rat(rng, den_choices=(3, 4, 5, 6))
    correct = 1 - pab
    # Erreur volontaire : valeur incorrecte pour l'autre branche.
    fausse = _rat(rng, den_choices=(3, 4, 5, 6))
    if fausse == correct:
        return None
    enonce = (
        f"Un élève affirme que, dans un arbre pondéré, sachant $A$ réalisé : "
        f"$P_A(B) = {latex(pab)}$ et $P_A(\\overline{{B}}) = {latex(fausse)}$. Cette affirmation est-elle "
        f"correcte ? Si non, corriger la valeur de $P_A(\\overline{{B}})$."
    )
    answer = f"Incorrect : $P_A(\\overline{{B}}) = {latex(correct)}$ (et non ${latex(fausse)}$)."
    steps = [
        "Étape 1 — Sur les branches issues d'un même nœud, les probabilités doivent sommer à $1$ : "
        "$P_A(B) + P_A(\\overline{B}) = 1$.",
        f"Étape 2 — Ici $P_A(B) + P_A(\\overline{{B}}) = {latex(pab)} + {latex(fausse)} = {latex(pab + fausse)} \\neq 1$ : l'affirmation est fausse.",
        f"Étape 3 — La valeur correcte est $P_A(\\overline{{B}}) = 1 - {latex(pab)} = {latex(correct)}$.",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_ARBRES}


EXTRA_FAMILY_BASE_SCORE: dict[str, float] = {
    "completer_arbre_erreur": 1.6,
    "intersection_tirage": 2.0,
    "proba_conditionnelle_tableau": 2.2,
    "test_independance_tableau": 3.0,
    "probabilites_totales_trois_branches": 3.8,
    "bayes_trois_branches": 4.6,
}

EXTRA_FAMILIES: tuple[Family, ...] = (
    Family("proba_conditionnelle_tableau", 2, "Probabilité conditionnelle à partir d'un tableau", NOTION_PROBA_COND,
           _gen_proba_conditionnelle_tableau, "un tableau croisé d'effectifs", "P_A(B) = effectif(A∩B) / effectif(A)"),
    Family("intersection_tirage", 2, "Intersection via un tirage sans remise", NOTION_ARBRES,
           _gen_intersection_tirage, "un tirage successif sans remise dans une urne",
           "déduire P(A) et P_A(B) des effectifs avant de les multiplier"),
    Family("completer_arbre_erreur", 2, "Détecter une erreur dans un arbre", NOTION_ARBRES,
           _gen_completer_arbre_erreur, "un arbre dont les branches d'un même nœud ne somment pas à 1",
           "vérifier que P_A(B)+P_A(non B)=1 puis corriger"),
    Family("test_independance_tableau", 3, "Indépendance à partir d'un tableau croisé", NOTION_INDEPENDANCE,
           _gen_test_independance_tableau, "un tableau croisé d'effectifs à quatre cases",
           "calculer P(A), P(B), P(A∩B) depuis les effectifs puis comparer"),
    Family("probabilites_totales_trois_branches", 4, "Probabilités totales à trois branches", NOTION_ARBRES,
           _gen_probabilites_totales_trois_branches, "une partition de l'univers en trois événements",
           "sommer les trois termes P(Ai)×P_Ai(B)"),
    Family("bayes_trois_branches", 5, "Bayes avec une partition à trois branches", NOTION_PROBA_COND,
           _gen_bayes_trois_branches, "un arbre à trois branches principales dont on inverse le conditionnement",
           "calculer les trois intersections, leur somme, puis diviser"),
)

EXTRA_FAMILIES_BY_ID: dict[str, Family] = {f.id: f for f in EXTRA_FAMILIES}


def generate_extra_pool(per_family: int = 12, seed: int = 20260949) -> list[dict]:
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
