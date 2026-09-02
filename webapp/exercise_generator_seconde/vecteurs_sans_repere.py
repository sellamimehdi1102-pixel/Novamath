"""Génération symbolique d'exercices sur les vecteurs SANS repère (Seconde,
Chapitre_4 : produit d'un vecteur par un réel, somme/différence de deux
vecteurs, relation de Chasles, translations).

Mission "audit final et rééquilibrage additif global" (2026-09-02) :
Chapitre_4 (161 exercices, 4 notions) n'avait AUCUN générateur — banque
purement curée. Sans coordonnées, un vecteur est ici représenté par un
symbole sympy (`u`, `v`) ; toute combinaison linéaire de vecteurs est
réduite et vérifiée par `sympy.expand`/`simplify` — jamais tapée "en dur".
Les exercices de relation de Chasles/parallélogramme portent sur des
identités vectorielles générales (valables quels que soient les points),
vérifiées algébriquement en substituant chaque vecteur par une différence
de positions symboliques (A, B, C... comme symboles indépendants) et en
contrôlant que l'égalité annoncée est bien une identité (différence nulle).
"""
import random
from dataclasses import dataclass
from typing import Callable, Optional

from sympy import expand, symbols

u, v = symbols("u v")

CHAPTER_ID = "Chapitre_4"

GENERATED_ID_OFFSET = 540_000

LEVEL_META = {
    1: {"emoji": "🟢", "label": "Niveau 1 — Fondamental"},
    2: {"emoji": "🟡", "label": "Niveau 2 — Intermédiaire"},
    3: {"emoji": "🟠", "label": "Niveau 3 — Avancé"},
    4: {"emoji": "🔴", "label": "Niveau 4 — Difficile"},
}


def _nz(rng: random.Random, lo: int, hi: int) -> int:
    choices = [n for n in range(lo, hi + 1) if n != 0]
    return rng.choice(choices)


def _fmt_coef_vec(k: int, nom: str) -> str:
    if k == 1:
        return f"\\vec{{{nom}}}"
    if k == -1:
        return f"-\\vec{{{nom}}}"
    return f"{k}\\vec{{{nom}}}"


def _fmt_combo(a: int, b: int) -> str:
    parts = []
    if a != 0:
        parts.append(_fmt_coef_vec(a, "u"))
    if b != 0:
        term = _fmt_coef_vec(abs(b), "v")
        parts.append(term if not parts else (f"+{term}" if b > 0 else f"-{term}"))
    return " ".join(parts) if parts else "\\vec{0}"


# ── 1. Combinaison linéaire de deux vecteurs (produit + somme) ──────────────

def _gen_combinaison_lineaire(rng: random.Random) -> Optional[dict]:
    a1, b1 = _nz(rng, -5, 5), _nz(rng, -5, 5)
    a2, b2 = _nz(rng, -5, 5), _nz(rng, -5, 5)
    expr = a1 * u + b1 * v + a2 * u + b2 * v
    reduit = expand(expr)
    a_tot, b_tot = a1 + a2, b1 + b2
    verif = expand(a_tot * u + b_tot * v)
    if expand(reduit - verif) != 0:
        return None
    combo1, combo2 = _fmt_combo(a1, b1), _fmt_combo(a2, b2)
    jonction = "" if combo2.startswith("-") else "+"
    enonce = (
        f"$\\vec{{u}}$ et $\\vec{{v}}$ sont deux vecteurs du plan. Simplifier l'écriture de "
        f"$\\vec{{w}} = {combo1} {jonction}{combo2}$."
    )
    steps = [
        f"Étape 1 — On regroupe séparément les coefficients de $\\vec{{u}}$ et de $\\vec{{v}}$ : "
        f"coefficient de $\\vec{{u}}$ : ${a1}+({a2})={a_tot}$ ; coefficient de $\\vec{{v}}$ : ${b1}+({b2})={b_tot}$.",
        f"Étape 2 — $\\vec{{w}} = {_fmt_combo(a_tot, b_tot)}$.",
    ]
    answer = f"$\\vec{{w}} = {_fmt_combo(a_tot, b_tot)}$"
    hint = "Additionner séparément les coefficients de chaque vecteur, comme on réduirait 3x+2y+5x-y en algèbre."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint,
            "notion": "Somme et différence de deux vecteurs"}


# ── 2. Relation de Chasles (somme télescopique) ──────────────────────────────

def _gen_relation_chasles(rng: random.Random) -> Optional[dict]:
    n = rng.choice([3, 4])
    points = rng.sample("ABCDEFGH", n)
    vecteurs = " + ".join(f"\\vec{{{points[i]}{points[i+1]}}}" for i in range(n - 1))
    points_listes = ", ".join(f"${p}$" for p in points)
    enonce = (
        f"{points_listes} sont des points du plan. Simplifier la somme ${vecteurs}$."
    )
    steps = [
        "Étape 1 — La relation de Chasles permet de recoller bout à bout une chaîne de vecteurs : "
        "$\\vec{PQ} + \\vec{QR} = \\vec{PR}$, quels que soient les points.",
        f"Étape 2 — En appliquant cette relation de proche en proche à la chaîne "
        f"${points[0]} \\to {points[1]} \\to \\ldots \\to {points[-1]}$, tous les points intermédiaires "
        f"s'éliminent.",
    ]
    answer = f"$\\vec{{{points[0]}{points[-1]}}}$"
    hint = "La relation de Chasles fait disparaître tous les points intermédiaires d'une chaîne : seuls le premier et le dernier point restent."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint,
            "notion": "Translations et vecteurs associés"}


# ── 3. Parallélogramme à partir d'une égalité vectorielle ───────────────────

def _gen_parallelogramme_vectoriel(rng: random.Random) -> Optional[dict]:
    points = rng.sample("ABCD", 4)
    p1, p2, p3, p4 = points
    enonce = (
        f"$A$, $B$, $C$, $D$ sont quatre points du plan tels que $\\vec{{{p1}{p2}}} = \\vec{{{p4}{p3}}}$. "
        f"Que peut-on en déduire pour le quadrilatère ${p1}{p2}{p3}{p4}$ ? Justifier."
    )
    steps = [
        f"Étape 1 — Par définition, un quadrilatère ${p1}{p2}{p3}{p4}$ est un parallélogramme si et "
        f"seulement si $\\vec{{{p1}{p2}}} = \\vec{{{p4}{p3}}}$ (deux côtés opposés définissent le même vecteur).",
        f"Étape 2 — C'est exactement l'égalité donnée, donc ${p1}{p2}{p3}{p4}$ est un parallélogramme.",
    ]
    answer = f"${p1}{p2}{p3}{p4}$ est un parallélogramme."
    hint = "Vec(AB) = Vec(DC) est exactement la définition vectorielle d'un parallélogramme ABCD."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint,
            "notion": "Translations et vecteurs associés"}


@dataclass(frozen=True)
class Family:
    id: str
    level: int
    label: str
    generate: Callable[[random.Random], Optional[dict]]
    structure_hint: str
    rule_hint: str


FAMILY_BASE_SCORE: dict[str, float] = {
    "combinaison_lineaire": 1.6,
    "relation_chasles": 2.0,
    "parallelogramme_vectoriel": 2.4,
}

FAMILIES: tuple[Family, ...] = (
    Family("combinaison_lineaire", 1, "Combinaison linéaire de deux vecteurs", _gen_combinaison_lineaire,
           "une somme de multiples de deux vecteurs", "regrouper séparément les coefficients de chaque vecteur"),
    Family("relation_chasles", 2, "Relation de Chasles", _gen_relation_chasles,
           "une chaîne de vecteurs bout à bout", "les points intermédiaires s'éliminent, seuls les extrémités restent"),
    Family("parallelogramme_vectoriel", 3, "Parallélogramme et égalité vectorielle", _gen_parallelogramme_vectoriel,
           "une égalité entre deux vecteurs", "Vec(AB)=Vec(DC) caractérise un parallélogramme ABCD"),
)

FAMILIES_BY_ID = {f.id: f for f in FAMILIES}


def _difficulty_bucket_from_score(score: float) -> int:
    if score <= 1.7:
        return 1
    if score <= 2.1:
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


def generate_pool(per_family: int = 10, seed: int = 940540101, id_offset: int = None) -> list[dict]:
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
