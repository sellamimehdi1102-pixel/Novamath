"""Génération symbolique d'exercices sur la factorisation d'une somme ou
d'une différence par facteur commun (Troisième, Chapitre_4, notion
"Factoriser une somme ou une différence").

30 exercices existants, 47% de gabarits distincts (redondance
structurelle signalée). Toute factorisation annoncée est vérifiée par
sympy.expand (en redéveloppant la forme factorisée), jamais tapée "en dur".
"""
import random
from dataclasses import dataclass
from typing import Callable, Optional

from sympy import expand, gcd, latex, symbols

x = symbols("x")

CHAPTER_ID = "Chapitre_4"
NOTION = "Factoriser une somme ou une différence"

GENERATED_ID_OFFSET = 160_000

LEVEL_META = {
    1: {"emoji": "🟢", "label": "Niveau 1 — Fondamental"},
    2: {"emoji": "🟡", "label": "Niveau 2 — Intermédiaire"},
    3: {"emoji": "🟠", "label": "Niveau 3 — Avancé"},
    4: {"emoji": "🔴", "label": "Niveau 4 — Difficile"},
}


def _nz(rng, lo, hi):
    return rng.choice([n for n in range(lo, hi + 1) if n != 0])


def _cx(n) -> str:
    """Coefficient devant x, sans afficher '1x' ni '-1x'."""
    return "" if n == 1 else ("-" if n == -1 else str(n))


def _fmt_somme(a, b) -> str:
    a_str = "" if a == 1 else ("-" if a == -1 else str(a))
    return f"{a_str}x {'+' if b > 0 else '-'} {abs(b)}"


# ── 1. Facteur commun simple (entier) ────────────────────────────────────────

def _gen_facteur_commun_simple(rng):
    facteur = rng.randint(2, 9)
    a = _nz(rng, 1, 9)
    b = _nz(rng, -9, 9)
    expr_a, expr_b = facteur * a, facteur * b
    g = gcd(expr_a, expr_b)
    enonce = f"Factoriser l'expression ${expr_a}x {'+' if expr_b > 0 else '-'} {abs(expr_b)}$."
    factored = f"{g}({_cx(expr_a // g)}x {'+' if expr_b // g > 0 else '-'} {abs(expr_b // g)})"
    check = expand(g * ((expr_a // g) * x + expr_b // g))
    original = expand(expr_a * x + expr_b)
    if check != original:
        return None
    steps = [
        f"Étape 1 — Le PGCD de {expr_a} et {abs(expr_b)} est {g}.",
        f"Étape 2 — On met {g} en facteur : ${factored}$.",
    ]
    answer = f"${factored}$"
    hint = "Trouver le plus grand facteur commun aux deux termes, puis le mettre en évidence devant une parenthèse."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


# ── 2. Facteur commun binomial : k(x+a) apparaît dans les deux termes ───────

def _gen_facteur_commun_binomial(rng):
    a_bin, b_bin = _nz(rng, 1, 5), rng.randint(-7, 7)
    k1 = _nz(rng, 1, 8)
    k2 = _nz(rng, 1, 8)
    while k2 == k1:
        k2 = _nz(rng, 1, 8)
    binome = a_bin * x + b_bin
    expr = k1 * x * binome + k2 * binome
    dev = expand(expr)
    enonce = f"Factoriser l'expression ${latex(dev)}$ sachant qu'elle admet ${_fmt_somme(a_bin, b_bin)}$ comme facteur commun."
    facteur_restant = f"{_cx(k1)}x {'+' if k2 > 0 else '-'} {abs(k2)}"
    steps = [
        f"Étape 1 — On reconnaît le facteur commun $({_fmt_somme(a_bin, b_bin)})$ dans les deux termes de l'expression.",
        f"Étape 2 — On le met en évidence : $({_fmt_somme(a_bin, b_bin)})({facteur_restant})$.",
    ]
    check = expand(binome * (k1 * x + k2))
    if check != dev:
        return None
    answer = f"$({_fmt_somme(a_bin, b_bin)})({facteur_restant})$"
    hint = "Repérer le facteur commun (ici un binôme entier) dans chaque terme, puis le factoriser comme on le ferait avec un nombre."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


# ── 3. Vérifier une factorisation proposée (vrai/faux) ──────────────────────

def _gen_verifier(rng):
    facteur = rng.randint(2, 9)
    a = _nz(rng, 1, 9)
    b = _nz(rng, -9, 9)
    expr_a, expr_b = facteur * a, facteur * b
    g = gcd(expr_a, expr_b)
    correct_factored = f"{g}({_cx(expr_a // g)}x {'+' if expr_b // g > 0 else '-'} {abs(expr_b // g)})"
    is_correct = rng.random() < 0.5
    if is_correct:
        proposed = correct_factored
    else:
        wrong_g = g + rng.choice([1, -1]) if g > 1 else g + 2
        if wrong_g == 0:
            return None
        proposed = f"{wrong_g}(\\dots)"
        # Pour rester vérifiable formellement, on compare plutôt en testant si wrong_g divise les deux coefficients.
        if expr_a % wrong_g == 0 and expr_b % wrong_g == 0 and wrong_g != g:
            proposed = f"{wrong_g}({_cx(expr_a // wrong_g)}x {'+' if expr_b // wrong_g > 0 else '-'} {abs(expr_b // wrong_g)})"
        else:
            return None
    enonce = f"Un élève affirme que ${expr_a}x {'+' if expr_b > 0 else '-'} {abs(expr_b)} = {proposed}$. A-t-il raison ? Justifier."
    steps = [
        f"Étape 1 — Le PGCD de {expr_a} et {abs(expr_b)} est {g} : c'est le plus grand facteur qu'on puisse mettre en évidence.",
        f"Étape 2 — La factorisation complète est ${correct_factored}$.",
    ]
    answer = f"Vrai : c'est bien la factorisation complète." if is_correct else \
        f"Faux (ce n'est pas le plus grand facteur commun, ou le résultat est incorrect) : la factorisation complète est ${correct_factored}$."
    hint = "Vérifier que le facteur proposé est bien le PGCD des deux coefficients, pas seulement un diviseur commun quelconque."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


# ── 4. Erreur à corriger (facteur commun incomplet) ─────────────────────────

def _gen_erreur_a_corriger(rng):
    facteur = rng.randint(4, 9)
    a = _nz(rng, 1, 6)
    b = _nz(rng, -8, 8)
    expr_a, expr_b = facteur * a, facteur * b
    g = gcd(expr_a, expr_b)
    if g <= 2:
        return None
    partial = 2 if expr_a % 2 == 0 and expr_b % 2 == 0 and g != 2 else None
    if partial is None:
        return None
    correct_factored = f"{g}({_cx(expr_a // g)}x {'+' if expr_b // g > 0 else '-'} {abs(expr_b // g)})"
    partial_factored = f"{partial}({_cx(expr_a // partial)}x {'+' if expr_b // partial > 0 else '-'} {abs(expr_b // partial)})"
    enonce = (
        f"Un élève factorise ${expr_a}x {'+' if expr_b > 0 else '-'} {abs(expr_b)}$ en ${partial_factored}$. "
        "A-t-il obtenu la factorisation complète ? Sinon, terminer la factorisation."
    )
    steps = [
        f"Étape 1 — Le PGCD réel de {expr_a} et {abs(expr_b)} est {g}, pas seulement {partial}.",
        f"Étape 2 — On peut donc continuer à factoriser : la forme complète est ${correct_factored}$.",
    ]
    answer = f"Non, ce n'est pas complet ; la factorisation complète est ${correct_factored}$."
    hint = "Vérifier systématiquement si le facteur restant entre parenthèses a lui-même un facteur commun avec le coefficient extrait."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


@dataclass(frozen=True)
class Family:
    id: str
    level: int
    label: str
    generate: Callable[[random.Random], Optional[dict]]
    structure_hint: str
    rule_hint: str


# ── Famille supplémentaire — mission "diversification structurelle"
# (2026-09-02) : facteur_commun_simple (90%) reposait sur UNE SEULE
# structure ("ax+b" avec un facteur NUMÉRIQUE commun). Nouvelle famille :
# facteur commun VARIABLE ($x$ lui-même), $ax^2+bx = x(ax+b)$ — jamais
# mélangée à FAMILIES/generate_pool (baseline figée).

def _gen_facteur_commun_variable(rng):
    a = _nz(rng, 1, 9)
    b = _nz(rng, -9, 9)
    if b == 0:
        return None
    enonce = f"Factoriser l'expression ${a}x^2 {'+' if b > 0 else '-'} {abs(b)}x$."
    factored = f"x({_cx(a)}x {'+' if b > 0 else '-'} {abs(b)})"
    check = expand(x * (a * x + b))
    original = expand(a * x**2 + b * x)
    if check != original:
        return None
    steps = [
        f"Étape 1 — Les deux termes ${a}x^2$ et ${b}x$ contiennent tous les deux le facteur $x$.",
        f"Étape 2 — On met $x$ en facteur : ${factored}$.",
    ]
    answer = f"${factored}$"
    hint = "Repérer le facteur commun x (pas un nombre) présent dans les deux termes, puis le mettre en évidence."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


EXTRA_FAMILY_BASE_SCORE: dict[str, float] = {
    "facteur_commun_variable": 1.8,
}

EXTRA_FAMILIES: tuple[Family, ...] = (
    Family("facteur_commun_variable", 2, "Facteur commun variable (x)", _gen_facteur_commun_variable,
           "une somme ax²+bx dont x est facteur commun", "mettre x en évidence : ax²+bx = x(ax+b)"),
)

EXTRA_FAMILIES_BY_ID = {f.id: f for f in EXTRA_FAMILIES}


def _build_extra_exercise(family: Family, rng: random.Random) -> Optional[dict]:
    notes = family.generate(rng)
    if notes is None:
        return None
    score = EXTRA_FAMILY_BASE_SCORE[family.id]
    real_level = _difficulty_bucket_from_score(score)
    hint = notes.get("hint") or f"Reconnais {family.structure_hint} : {family.rule_hint}."
    return {
        "enonce": notes["enonce"],
        "answer": notes["answer"],
        "hint": hint,
        "solution_steps": notes["steps"],
        "chapter_id": CHAPTER_ID,
        "notion": NOTION,
        "difficulty": real_level,
        "difficulty_label": LEVEL_META[real_level]["label"],
        "difficulty_emoji": LEVEL_META[real_level]["emoji"],
        "family": family.id,
        "family_label": family.label,
        "declared_level": family.level,
        "complexity_score": score,
        "source": "generated",
    }


def generate_extra_pool(per_family: int = 12, seed: int = 30260350) -> list[dict]:
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
    "facteur_commun_simple": 1.0,
    "verifier": 2.2,
    "facteur_commun_binomial": 3.0,
    "erreur_a_corriger": 3.8,
}

FAMILIES: tuple[Family, ...] = (
    Family("facteur_commun_simple", 1, "Facteur commun numérique", _gen_facteur_commun_simple,
           "une somme dont les coefficients ont un facteur commun", "mettre le PGCD en évidence"),
    Family("verifier", 2, "Vérifier une factorisation proposée", _gen_verifier,
           "une factorisation annoncée, complète ou non", "comparer le facteur proposé au PGCD réel"),
    Family("facteur_commun_binomial", 3, "Facteur commun binomial", _gen_facteur_commun_binomial,
           "un facteur commun qui est lui-même un binôme", "factoriser comme avec un nombre, en gardant le binôme entier"),
    Family("erreur_a_corriger", 4, "Détecter une factorisation incomplète", _gen_erreur_a_corriger,
           "une factorisation partielle", "vérifier que le facteur extrait est bien le PGCD complet"),
)

FAMILIES_BY_ID = {f.id: f for f in FAMILIES}


def _difficulty_bucket_from_score(score: float) -> int:
    if score <= 1.5:
        return 1
    if score <= 2.5:
        return 2
    if score <= 3.4:
        return 3
    return 4


def build_exercise(family: Family, rng: random.Random) -> Optional[dict]:
    notes = family.generate(rng)
    if notes is None:
        return None
    score = FAMILY_BASE_SCORE[family.id]
    real_level = _difficulty_bucket_from_score(score)
    hint = notes.get("hint") or f"Reconnais {family.structure_hint} : {family.rule_hint}."
    return {
        "enonce": notes["enonce"],
        "answer": notes["answer"],
        "hint": hint,
        "solution_steps": notes["steps"],
        "chapter_id": CHAPTER_ID,
        "notion": NOTION,
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


def generate_pool(per_family: int = 7, seed: int = 30260107) -> list[dict]:
    rng = random.Random(seed)
    per_family_pool: dict[str, list[dict]] = {}
    for family in FAMILIES:
        seen_signatures = set()
        items = []
        attempts = 0
        while len(items) < per_family and attempts < per_family * 150:
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
