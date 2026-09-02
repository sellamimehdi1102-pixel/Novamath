"""Génération symbolique d'exercices de calcul littéral (Seconde,
Chapitre_3 : distributivité/identités remarquables, calcul fractionnaire
littéral, équations produit nul et quotient).

Mission "audit final et rééquilibrage additif global" (2026-09-02) :
Chapitre_3 (160 exercices, 4 notions) n'avait AUCUN générateur — banque
purement curée. Tout développement, toute résolution et toute mise au même
dénominateur est vérifiée par sympy (`expand`, `solve`, `together`, `simplify`)
— jamais tapée "en dur".
"""
import random
from dataclasses import dataclass
from typing import Callable, Optional

from sympy import Eq, Rational, expand, latex, solve, symbols, together

x = symbols("x")

CHAPTER_ID = "Chapitre_3"

GENERATED_ID_OFFSET = 530_000

LEVEL_META = {
    1: {"emoji": "🟢", "label": "Niveau 1 — Fondamental"},
    2: {"emoji": "🟡", "label": "Niveau 2 — Intermédiaire"},
    3: {"emoji": "🟠", "label": "Niveau 3 — Avancé"},
    4: {"emoji": "🔴", "label": "Niveau 4 — Difficile"},
}


def _nz(rng: random.Random, lo: int, hi: int) -> int:
    choices = [n for n in range(lo, hi + 1) if n != 0]
    return rng.choice(choices)


def _fmt_linear(a: int, b: int) -> str:
    """Rend ax+b en LaTeX propre : coefficient 1/-1 masqué devant x, terme
    constant omis s'il est nul."""
    a_txt = "-" if a == -1 else ("" if a == 1 else str(a))
    terme = f"{a_txt}x"
    if b > 0:
        terme += f"+{b}"
    elif b < 0:
        terme += f"-{abs(b)}"
    return terme


# ── 1. Distributivité et identités remarquables ─────────────────────────────

def _gen_identite_remarquable(rng: random.Random) -> Optional[dict]:
    a = _nz(rng, -9, 9)
    b = rng.randint(1, 9)
    kind = rng.choice(["carre_somme", "carre_diff", "produit_conjugue"])
    a_txt = "-" if a == -1 else ("" if a == 1 else str(a))
    if kind == "carre_somme":
        expr = (a * x + b) ** 2
        dev = expand(expr)
        enonce = f"Développer $({a_txt}x + {b})^2$."
        formule = "(u+v)^2 = u^2 + 2uv + v^2"
    elif kind == "carre_diff":
        expr = (a * x - b) ** 2
        dev = expand(expr)
        enonce = f"Développer $({a_txt}x - {b})^2$."
        formule = "(u-v)^2 = u^2 - 2uv + v^2"
    else:
        expr = (a * x + b) * (a * x - b)
        dev = expand(expr)
        enonce = f"Développer $({a_txt}x + {b})({a_txt}x - {b})$."
        formule = "(u+v)(u-v) = u^2 - v^2"
    steps = [
        f"Étape 1 — On reconnaît l'identité remarquable ${formule}$.",
        f"Étape 2 — Après développement, on obtient ${latex(dev)}$.",
    ]
    answer = f"${latex(dev)}$"
    hint = "Reconnaître laquelle des trois identités remarquables s'applique avant de développer terme à terme."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint,
            "notion": "Distributivité et identités remarquables"}


# ── 2. Équation produit nul ──────────────────────────────────────────────────

def _gen_equation_produit_nul(rng: random.Random) -> Optional[dict]:
    a = _nz(rng, -5, 5)
    b = rng.randint(-9, 9)
    c = _nz(rng, -5, 5)
    d = rng.randint(-9, 9)
    expr = (a * x + b) * (c * x + d)
    sols = solve(Eq(expr, 0), x)
    if len(sols) != 2:
        return None
    facteur1 = _fmt_linear(a, b)
    facteur2 = _fmt_linear(c, d)
    enonce = f"Résoudre l'équation $({facteur1})({facteur2}) = 0$."
    sols_sorted = sorted(sols, key=str)
    steps = [
        "Étape 1 — Un produit de facteurs est nul si et seulement si l'un au moins des facteurs est nul.",
        f"Étape 2 — ${facteur1} = 0$ donne $x = {latex(sols_sorted[0])}$, "
        f"et ${facteur2} = 0$ donne $x = {latex(sols_sorted[1])}$.",
    ]
    answer = f"$S = \\left\\{{{latex(sols_sorted[0])}\\,;\\,{latex(sols_sorted[1])}\\right\\}}$"
    hint = "Un produit est nul si et seulement si l'un de ses facteurs est nul : annuler chaque facteur séparément."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint,
            "notion": "Résolution d'équation produit nul"}


# ── 3. Équation quotient (avec exclusion du domaine) ────────────────────────

def _gen_equation_quotient(rng: random.Random) -> Optional[dict]:
    a = _nz(rng, -6, 6)
    b = rng.randint(-9, 9)
    c = _nz(rng, -4, 4)
    d = rng.randint(-9, 9)
    valeur_interdite = Rational(-d, c)
    numerateur = a * x + b
    sols = solve(Eq(numerateur, 0), x)
    if len(sols) != 1 or sols[0] == valeur_interdite:
        return None
    num_str = _fmt_linear(a, b)
    den_str = _fmt_linear(c, d)
    enonce = f"Résoudre l'équation $\\dfrac{{{num_str}}}{{{den_str}}} = 0$."
    steps = [
        f"Étape 1 — Condition d'existence : le dénominateur ne doit pas s'annuler, donc $x \\neq {latex(valeur_interdite)}$.",
        "Étape 2 — Un quotient est nul si et seulement si son numérateur est nul (le dénominateur restant non nul).",
        f"Étape 3 — ${num_str} = 0$ donne $x = {latex(sols[0])}$, valeur qui respecte bien la condition d'existence.",
    ]
    answer = f"$S = \\left\\{{{latex(sols[0])}\\right\\}}$"
    hint = "Un quotient est nul quand son numérateur est nul ET son dénominateur non nul : vérifier toujours la condition d'existence."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint,
            "notion": "Résolution d'équation quotient"}


# ── 4. Calcul littéral en écriture fractionnaire (réduction au même dénom.) ─

def _gen_calcul_fractionnaire(rng: random.Random) -> Optional[dict]:
    a = _nz(rng, -6, 6)
    b = _nz(rng, 2, 6)
    c = _nz(rng, -6, 6)
    d = _nz(rng, 2, 6)
    if b == d:
        return None
    expr = Rational(a, b) * x + Rational(c, d) * x
    reduit = together(expr)
    enonce = f"Réduire au même dénominateur puis simplifier : $\\dfrac{{{a}}}{{{b}}}x + \\dfrac{{{c}}}{{{d}}}x$."
    denom_commun = b * d
    steps = [
        f"Étape 1 — On réduit au dénominateur commun ${denom_commun}$ : "
        f"$\\dfrac{{{a}}}{{{b}}}x = \\dfrac{{{a*d}}}{{{denom_commun}}}x$ et $\\dfrac{{{c}}}{{{d}}}x = \\dfrac{{{c*b}}}{{{denom_commun}}}x$.",
        f"Étape 2 — En additionnant : $\\dfrac{{{a*d}+{c*b}}}{{{denom_commun}}}x = {latex(reduit)}$.",
    ]
    answer = f"${latex(reduit)}$"
    hint = "Mettre les deux fractions au même dénominateur (produit des deux dénominateurs) avant d'additionner les numérateurs."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint,
            "notion": "Calcul littéral en écriture fractionnaire"}


@dataclass(frozen=True)
class Family:
    id: str
    level: int
    label: str
    generate: Callable[[random.Random], Optional[dict]]
    structure_hint: str
    rule_hint: str


FAMILY_BASE_SCORE: dict[str, float] = {
    "identite_remarquable": 1.4,
    "calcul_fractionnaire": 1.8,
    "equation_produit_nul": 2.2,
    "equation_quotient": 2.8,
}

FAMILIES: tuple[Family, ...] = (
    Family("identite_remarquable", 1, "Développer avec une identité remarquable", _gen_identite_remarquable,
           "une expression de la forme (u±v)² ou (u+v)(u-v)", "appliquer directement la formule correspondante"),
    Family("calcul_fractionnaire", 2, "Calcul littéral fractionnaire", _gen_calcul_fractionnaire,
           "une somme de deux fractions littérales", "réduire au dénominateur commun avant d'additionner"),
    Family("equation_produit_nul", 2, "Équation produit nul", _gen_equation_produit_nul,
           "un produit de deux facteurs égal à zéro", "annuler chaque facteur séparément"),
    Family("equation_quotient", 3, "Équation quotient", _gen_equation_quotient,
           "un quotient égal à zéro", "annuler le numérateur en respectant la condition d'existence"),
)

FAMILIES_BY_ID = {f.id: f for f in FAMILIES}


def _difficulty_bucket_from_score(score: float) -> int:
    if score <= 1.5:
        return 1
    if score <= 2.0:
        return 2
    if score <= 2.5:
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


def generate_pool(per_family: int = 8, seed: int = 940530101) -> list[dict]:
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
