"""Génération symbolique d'exercices sur le développement d'un produit avec
la simple distributivité (Troisième, Chapitre_4, notion
"Développer un produit avec la simple distributivité").

30 exercices existants, 47% de gabarits distincts (redondance
structurelle signalée). Tout développement annoncé est calculé par
sympy.expand, jamais tapé "en dur".
"""
import random
from dataclasses import dataclass
from typing import Callable, Optional

from sympy import Rational, expand, latex, symbols

x = symbols("x")

CHAPTER_ID = "Chapitre_4"
NOTION = "Développer un produit avec la simple distributivité"

GENERATED_ID_OFFSET = 150_000

LEVEL_META = {
    1: {"emoji": "🟢", "label": "Niveau 1 — Fondamental"},
    2: {"emoji": "🟡", "label": "Niveau 2 — Intermédiaire"},
    3: {"emoji": "🟠", "label": "Niveau 3 — Avancé"},
    4: {"emoji": "🔴", "label": "Niveau 4 — Difficile"},
}


def _nz(rng, lo, hi):
    return rng.choice([n for n in range(lo, hi + 1) if n != 0])


def _fmt_parenthese(b, c) -> str:
    b_str = "" if b == 1 else ("-" if b == -1 else str(b))
    inner = f"{b_str}x"
    if c != 0:
        inner += f" {'+' if c > 0 else '-'} {abs(c)}"
    return f"({inner})"


# ── 1. Calcul direct k(bx+c) ─────────────────────────────────────────────────

def _gen_calcul_direct(rng):
    k = _nz(rng, 2, 9)
    b = _nz(rng, 1, 9)
    c = rng.randint(-9, 9)
    expr = k * (b * x + c)
    dev = expand(expr)
    enonce = f"Développer l'expression ${k}{_fmt_parenthese(b, c)}$."
    steps = [
        f"Étape 1 — On distribue ${k}$ sur chaque terme : ${k}\\times {b}x = {k * b}x$ et ${k}\\times({c}) = {k * c}$.",
        f"Étape 2 — On obtient ${latex(dev)}$.",
    ]
    answer = f"${latex(dev)}$"
    hint = "Multiplier le facteur devant la parenthèse par CHAQUE terme à l'intérieur, séparément."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


# ── 2. Facteur négatif devant la parenthèse ──────────────────────────────────

def _gen_facteur_negatif(rng):
    k = -_nz(rng, 2, 9)
    b = _nz(rng, 1, 9)
    c = rng.randint(-9, 9)
    expr = k * (b * x + c)
    dev = expand(expr)
    enonce = f"Développer l'expression ${k}{_fmt_parenthese(b, c)}$."
    steps = [
        f"Étape 1 — Le facteur ${k}$ est négatif : il change le signe de CHAQUE terme distribué.",
        f"Étape 2 — ${k}\\times {b}x = {k * b}x$ et ${k}\\times({c}) = {k * c}$, donc le résultat est ${latex(dev)}$.",
    ]
    answer = f"${latex(dev)}$"
    hint = "Un facteur négatif devant la parenthèse change le signe de tous les termes développés — erreur fréquente à surveiller."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


# ── 3. Expression avec un terme supplémentaire (multi-étapes) ───────────────

def _gen_avec_terme_supplementaire(rng):
    k = _nz(rng, 2, 8)
    b = _nz(rng, 1, 8)
    c = rng.randint(-8, 8)
    d = _nz(rng, -12, 12)
    expr = k * (b * x + c) + d * x
    dev = expand(expr)
    d_abs_str = "" if abs(d) == 1 else str(abs(d))
    enonce = f"Développer puis réduire l'expression ${k}{_fmt_parenthese(b, c)} {'+' if d > 0 else '-'} {d_abs_str}x$."
    steps = [
        f"Étape 1 — On distribue ${k}$ : ${k}{_fmt_parenthese(b, c)} = {latex(expand(k * (b * x + c)))}$.",
        f"Étape 2 — On ajoute le terme restant en $x$ et on réduit : ${latex(dev)}$.",
    ]
    answer = f"${latex(dev)}$"
    hint = "Développer d'abord la parenthèse, puis regrouper tous les termes en x entre eux."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


# ── 4. Vérifier un développement proposé (vrai/faux) ─────────────────────────

def _gen_verifier(rng):
    k = _nz(rng, 2, 9)
    b = _nz(rng, 1, 9)
    c = _nz(rng, -9, 9)
    correct = expand(k * (b * x + c))
    is_correct = rng.random() < 0.5
    if is_correct:
        proposed = correct
    else:
        erreur = rng.choice(["oubli_second_terme", "erreur_signe"])
        if erreur == "oubli_second_terme":
            proposed = k * b * x  # l'élève n'a distribué que sur le premier terme
        else:
            proposed = k * b * x - k * c  # signe du second terme inversé
        if expand(proposed) == correct:
            return None
    enonce = (
        f"Un élève affirme que ${k}{_fmt_parenthese(b, c)} = {latex(expand(proposed))}$. "
        "A-t-il raison ? Justifier."
    )
    steps = [
        f"Étape 1 — On développe soi-même : ${k}{_fmt_parenthese(b, c)} = {latex(correct)}$.",
        "Étape 2 — On compare ce résultat à celui annoncé par l'élève.",
    ]
    answer = f"Vrai : le développement annoncé est correct (${latex(correct)}$)." if is_correct else \
        f"Faux : le développement correct est ${latex(correct)}$."
    hint = "Développer soi-même l'expression, terme par terme, avant de juger la proposition."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


# ── 5. Erreur à corriger (facteur mal distribué sur un seul terme) ──────────

def _gen_erreur_a_corriger(rng):
    k = _nz(rng, 2, 9)
    b = _nz(rng, 1, 9)
    c = rng.randint(-9, 9)
    if c == 0:
        return None
    correct = expand(k * (b * x + c))
    wrong = k * b * x + c  # l'élève oublie de multiplier le second terme par k
    if expand(wrong) == correct:
        return None
    enonce = (
        f"Un élève développe ${k}{_fmt_parenthese(b, c)}$ ainsi : \"${k}\\times {b}x {'+' if c > 0 else '-'} {abs(c)} = "
        f"{latex(expand(wrong))}$\" (il n'a multiplié ${k}$ que par le premier terme). Identifier son erreur et donner "
        "le développement correct."
    )
    steps = [
        f"Étape 1 — Le facteur ${k}$ doit multiplier CHAQUE terme de la parenthèse, pas seulement le premier.",
        f"Étape 2 — Le second terme devient ${k}\\times({c}) = {k * c}$, pas ${c}$.",
        f"Étape 3 — Le développement correct est ${latex(correct)}$.",
    ]
    answer = f"Erreur : le second terme n'a pas été multiplié par {k} ; le développement correct est ${latex(correct)}$."
    hint = "La distributivité s'applique à TOUS les termes de la parenthèse, sans exception."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


@dataclass(frozen=True)
class Family:
    id: str
    level: int
    label: str
    generate: Callable[[random.Random], Optional[dict]]
    structure_hint: str
    rule_hint: str


FAMILY_BASE_SCORE: dict[str, float] = {
    "calcul_direct": 1.0,
    "facteur_negatif": 2.0,
    "verifier": 2.3,
    "avec_terme_supplementaire": 3.0,
    "erreur_a_corriger": 3.8,
}

FAMILIES: tuple[Family, ...] = (
    Family("calcul_direct", 1, "Calcul direct k(bx+c)", _gen_calcul_direct,
           "un produit d'un facteur par une somme", "distribuer le facteur sur chaque terme"),
    Family("facteur_negatif", 2, "Facteur négatif devant la parenthèse", _gen_facteur_negatif,
           "un facteur négatif à distribuer", "changer le signe de chaque terme distribué"),
    Family("verifier", 2, "Vérifier un développement proposé", _gen_verifier,
           "un développement annoncé, correct ou non", "redévelopper soi-même avant de juger"),
    Family("avec_terme_supplementaire", 3, "Développer puis réduire", _gen_avec_terme_supplementaire,
           "une expression avec un terme supplémentaire en x", "développer puis regrouper les termes semblables"),
    Family("erreur_a_corriger", 4, "Détecter et corriger une erreur", _gen_erreur_a_corriger,
           "une distribution incomplète (un seul terme multiplié)", "vérifier que TOUS les termes ont été multipliés"),
)

FAMILIES_BY_ID = {f.id: f for f in FAMILIES}


# ── Famille supplémentaire — mission "chantier final : diversification
# numérique maximale" (2026-09-02) : vérification par lecture du code —
# k, b, c sont TOUJOURS des entiers (`_nz`/`randint`) dans les 5 familles de
# ce module (99 exercices servis pour cette notion, 0% de fraction dans
# l'audit). Nouvelle famille dédiée : facteur devant la parenthèse
# FRACTIONNAIRE (ex. 1/2), vérifiée par sympy.expand avec Rational — jamais
# mélangée à FAMILIES/generate_pool (baseline figée, déjà servie).

def _gen_calcul_direct_fractionnaire(rng):
    denom = rng.choice([2, 3, 4, 5])
    k = Rational(_nz(rng, 1, 6), denom)
    if k.q == 1:
        return None  # simplifié en entier (ex. 4/2=2) : ne démontre plus un facteur fractionnaire
    b = _nz(rng, 1, 9)
    c = rng.randint(-9, 9)
    expr = k * (b * x + c)
    dev = expand(expr)
    check = k * b * x + k * c
    if expand(check) != dev:
        return None
    enonce = f"Développer l'expression ${latex(k)}{_fmt_parenthese(b, c)}$."
    steps = [
        f"Étape 1 — On distribue ${latex(k)}$ (une fraction, pas un entier) sur chaque terme : "
        f"${latex(k)}\\times {b}x = {latex(k * b)}x$ et ${latex(k)}\\times({c}) = {latex(k * c)}$.",
        f"Étape 2 — On obtient ${latex(dev)}$.",
    ]
    answer = f"${latex(dev)}$"
    hint = "Le facteur devant la parenthèse peut être une fraction : on distribue exactement comme avec un entier."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


EXTRA_FAMILY_BASE_SCORE: dict[str, float] = {
    "calcul_direct_fractionnaire": 2.4,
}

EXTRA_FAMILIES: tuple[Family, ...] = (
    Family("calcul_direct_fractionnaire", 3, "Facteur fractionnaire devant la parenthèse",
           _gen_calcul_direct_fractionnaire, "un produit d'une fraction par une somme",
           "distribuer la fraction sur chaque terme comme on le ferait avec un entier"),
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


def generate_extra_pool(per_family: int = 12, seed: int = 30260450) -> list[dict]:
    """Pool de diversification NUMÉRIQUE (mission 2026-09-02) — jamais
    mélangé à generate_pool()/FAMILIES (baseline figée, déjà servie). IDs à
    partir de GENERATED_ID_OFFSET + 8000."""
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


def _difficulty_bucket_from_score(score: float) -> int:
    if score <= 1.5:
        return 1
    if score <= 2.6:
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


def generate_pool(per_family: int = 6, seed: int = 30260106) -> list[dict]:
    rng = random.Random(seed)
    per_family_pool: dict[str, list[dict]] = {}
    for family in FAMILIES:
        seen_signatures = set()
        items = []
        attempts = 0
        while len(items) < per_family and attempts < per_family * 80:
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
