"""Génération symbolique d'exercices sur les ensembles de nombres, la
divisibilité, les puissances entières et la racine carrée (Seconde,
Chapitre_1).

Mission "audit final et rééquilibrage additif global" (2026-09-02) :
Chapitre_1 (164 exercices, 4 notions) n'avait AUCUN générateur — banque
purement curée. L'appartenance à un ensemble de nombres (N/Z/D/Q/R), le
caractère premier d'un entier, une puissance à exposant négatif et un
encadrement de racine carrée sont tous vérifiés par calcul exact (jamais
tapés "en dur") — via `fractions.Fraction` pour la décimalité exacte
(dénominateur réduit ne contenant que les facteurs 2 et 5).
"""
import math
import random
from dataclasses import dataclass
from fractions import Fraction
from typing import Callable, Optional

CHAPTER_ID = "Chapitre_1"

GENERATED_ID_OFFSET = 520_000

LEVEL_META = {
    1: {"emoji": "🟢", "label": "Niveau 1 — Fondamental"},
    2: {"emoji": "🟡", "label": "Niveau 2 — Intermédiaire"},
    3: {"emoji": "🟠", "label": "Niveau 3 — Avancé"},
    4: {"emoji": "🔴", "label": "Niveau 4 — Difficile"},
}


def _fmt_frac(f: Fraction) -> str:
    if f.denominator == 1:
        return str(f.numerator)
    sign = "-" if f.numerator < 0 else ""
    return f"{sign}\\dfrac{{{abs(f.numerator)}}}{{{f.denominator}}}"


def _is_decimal(f: Fraction) -> bool:
    d = f.denominator
    while d % 2 == 0:
        d //= 2
    while d % 5 == 0:
        d //= 5
    return d == 1


# ── 1. Appartenance aux ensembles de nombres N, Z, D, Q, R ──────────────────

def _gen_classer_nombre(rng: random.Random) -> Optional[dict]:
    kind = rng.choice(["entier_naturel", "entier_negatif", "decimal", "fraction_non_decimale", "irrationnel"])
    if kind == "entier_naturel":
        n = rng.randint(0, 50)
        label, valeur = str(n), Fraction(n)
        ensembles = ["N", "Z", "D", "Q", "R"]
        raison = f"c'est un entier positif ou nul (${n} \\geq 0$), donc il appartient aussi à N"
    elif kind == "entier_negatif":
        n = -rng.randint(1, 50)
        label, valeur = str(n), Fraction(n)
        ensembles = ["Z", "D", "Q", "R"]
        raison = f"c'est un entier négatif (${n} < 0$), donc il n'appartient PAS à N, mais à Z"
    elif kind == "decimal":
        num = rng.randint(1, 99)
        den = rng.choice([2, 4, 5, 8, 10, 20, 25])
        valeur = Fraction(num, den)
        if valeur.denominator == 1:
            return None
        label = _fmt_frac(valeur)
        ensembles = ["D", "Q", "R"]
        raison = f"son dénominateur réduit ({valeur.denominator}) ne contient que des facteurs 2 et/ou 5, donc c'est un nombre décimal"
    elif kind == "fraction_non_decimale":
        num = rng.randint(1, 20)
        den = rng.choice([3, 6, 7, 9, 11, 12])
        valeur = Fraction(num, den)
        if _is_decimal(valeur) or valeur.denominator == 1:
            return None
        label = _fmt_frac(valeur)
        ensembles = ["Q", "R"]
        raison = f"son dénominateur réduit ({valeur.denominator}) contient un facteur premier autre que 2 ou 5 : ce n'est PAS un nombre décimal"
    else:
        n = rng.choice([2, 3, 5, 6, 7, 10, 11])
        label, valeur = f"\\sqrt{{{n}}}", None
        ensembles = ["R"]
        raison = f"$\\sqrt{{{n}}}$ n'est pas un nombre rationnel (racine d'un entier qui n'est pas un carré parfait) : il appartient seulement à R"
    tous = ["N", "Z", "D", "Q", "R"]
    enonce = f"Dans quels ensembles parmi $\\mathbb{{N}}$, $\\mathbb{{Z}}$, $\\mathbb{{D}}$, $\\mathbb{{Q}}$, $\\mathbb{{R}}$ le nombre ${label}$ se trouve-t-il ? Justifier."
    steps = [
        f"Étape 1 — On examine la nature du nombre ${label}$.",
        f"Étape 2 — {raison}.",
        f"Étape 3 — Rappel des inclusions : $\\mathbb{{N}} \\subset \\mathbb{{Z}} \\subset \\mathbb{{D}} \\subset \\mathbb{{Q}} \\subset \\mathbb{{R}}$ "
        "(appartenir à un ensemble plus petit implique appartenir à tous les plus grands).",
    ]
    answer = "$" + ", ".join(f"\\mathbb{{{e}}}" for e in ensembles) + "$"
    hint = "Utiliser l'inclusion N ⊂ Z ⊂ D ⊂ Q ⊂ R : identifier le plus petit ensemble contenant le nombre suffit à connaître tous les autres."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint,
            "notion": "Ensembles de nombres"}


# ── 2. Nombre premier ou composé (décomposition) ────────────────────────────

def _gen_nombre_premier(rng: random.Random) -> Optional[dict]:
    n = rng.randint(20, 150)
    is_prime = all(n % d != 0 for d in range(2, int(math.isqrt(n)) + 1))
    if is_prime:
        enonce = f"Le nombre ${n}$ est-il premier ? Justifier."
        divs_testes = [d for d in range(2, int(math.isqrt(n)) + 1)]
        steps = [
            f"Étape 1 — On teste la divisibilité de {n} par tous les entiers de 2 à $\\sqrt{{{n}}} \\approx {math.isqrt(n)}$.",
            f"Étape 2 — Aucun de ces entiers ({', '.join(map(str, divs_testes))}) ne divise {n}.",
        ]
        answer = f"Oui, ${n}$ est premier (aucun diviseur autre que 1 et lui-même)."
    else:
        facteurs = []
        m = n
        d = 2
        while d * d <= m:
            while m % d == 0:
                facteurs.append(d)
                m //= d
            d += 1
        if m > 1:
            facteurs.append(m)
        enonce = f"Le nombre ${n}$ est-il premier ? Si non, donner sa décomposition en facteurs premiers."
        decomposition = " \\times ".join(str(f) for f in facteurs)
        steps = [
            f"Étape 1 — On cherche un diviseur de {n} autre que 1 et lui-même : {facteurs[0]} convient.",
            f"Étape 2 — En poursuivant la décomposition : ${n} = {decomposition}$.",
        ]
        answer = f"Non, ${n} = {decomposition}$."
    hint = "Tester les diviseurs premiers successifs (2, 3, 5, 7...) jusqu'à la racine carrée du nombre."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint,
            "notion": "Multiples, diviseurs et nombres premiers"}


# ── 3. Puissance entière relative (exposant négatif) ────────────────────────

def _gen_puissance_relative(rng: random.Random) -> Optional[dict]:
    base = rng.choice([2, 3, 4, 5, 10, -2, -3])
    exposant = rng.choice([-1, -2, -3, -4])
    valeur = Fraction(1, base ** (-exposant))
    enonce = f"Calculer ${base}^{{{exposant}}}$ et donner le résultat sous forme de fraction irréductible."
    steps = [
        f"Étape 1 — Pour un exposant négatif, $a^{{-n}} = \\dfrac{{1}}{{a^n}}$ (avec $a \\neq 0$).",
        f"Étape 2 — ${base}^{{{exposant}}} = \\dfrac{{1}}{{{base}^{{{-exposant}}}}} = {_fmt_frac(valeur)}$.",
    ]
    answer = f"${base}^{{{exposant}}} = {_fmt_frac(valeur)}$"
    hint = "Un exposant négatif transforme la puissance en inverse : a^(-n) = 1/(a^n)."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint,
            "notion": "Puissances entières relatives"}


# ── 4. Encadrement d'une racine carrée entre deux entiers consécutifs ───────

def _gen_encadrement_racine(rng: random.Random) -> Optional[dict]:
    a = rng.randint(2, 200)
    n = math.isqrt(a)
    if n * n == a:
        return None
    enonce = f"Entre quels deux entiers consécutifs se situe $\\sqrt{{{a}}}$ ? Justifier."
    steps = [
        f"Étape 1 — On cherche l'entier $n$ tel que $n^2 \\leq {a} < (n+1)^2$.",
        f"Étape 2 — ${n}^2 = {n*n}$ et ${n+1}^2 = {(n+1)**2}$, et ${n*n} \\leq {a} < {(n+1)**2}$.",
        f"Étape 3 — Donc ${n} < \\sqrt{{{a}}} < {n+1}$ (racine carrée croissante).",
    ]
    answer = f"${n} < \\sqrt{{{a}}} < {n+1}$"
    hint = "Chercher les deux carrés parfaits consécutifs qui encadrent le nombre sous la racine."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint,
            "notion": "Racine carrée"}


@dataclass(frozen=True)
class Family:
    id: str
    level: int
    label: str
    generate: Callable[[random.Random], Optional[dict]]
    structure_hint: str
    rule_hint: str


FAMILY_BASE_SCORE: dict[str, float] = {
    "classer_nombre": 1.4,
    "nombre_premier": 1.8,
    "puissance_relative": 2.2,
    "encadrement_racine": 1.6,
}

FAMILIES: tuple[Family, ...] = (
    Family("classer_nombre", 1, "Ensembles de nombres", _gen_classer_nombre,
           "un nombre à classer parmi N/Z/D/Q/R", "utiliser les inclusions N ⊂ Z ⊂ D ⊂ Q ⊂ R"),
    Family("nombre_premier", 2, "Nombre premier ou décomposition", _gen_nombre_premier,
           "un entier à tester", "tester les diviseurs premiers jusqu'à la racine carrée du nombre"),
    Family("puissance_relative", 2, "Puissance entière relative", _gen_puissance_relative,
           "une puissance à exposant négatif", "a^(-n) = 1/a^n"),
    Family("encadrement_racine", 1, "Encadrement d'une racine carrée", _gen_encadrement_racine,
           "un nombre non carré parfait sous une racine", "trouver les deux carrés parfaits consécutifs qui l'encadrent"),
)

FAMILIES_BY_ID = {f.id: f for f in FAMILIES}


def _difficulty_bucket_from_score(score: float) -> int:
    if score <= 1.5:
        return 1
    if score <= 1.9:
        return 2
    if score <= 2.4:
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


def generate_pool(per_family: int = 8, seed: int = 940520101, id_offset: int = None) -> list[dict]:
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
        base_offset = GENERATED_ID_OFFSET if id_offset is None else id_offset
        ex["id"] = base_offset + i
    return pool
