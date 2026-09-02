"""Génération symbolique d'exercices sur les vecteurs (Seconde, Chapitre_5 :
"Condition de colinéarité", "Milieu et norme", "Base, repère et
coordonnées").

Contrairement à droites.py/signes.py (Chapitre_6/9, déjà les plus fournis de
Seconde), Chapitre_5 était l'un des deux chapitres les plus faibles (121
exercices, aucun générateur) — créé par la mission "équilibrage définitif de
toutes les classes" (2026-09-01).

IMPORTANT — architecture spécifique à Seconde : contrairement à
Première/Troisième, server.py::_class_bank("seconde") NE fusionne PAS de
generated_exercise_bank (chemin historique, voir curriculum_stats.py::
_CLASS_LEVELS_WITHOUT_GENERATED_MERGE). Le pool produit par ce module n'est
donc PAS écrit dans exercises_generated_seconde.json : il est directement
ajouté (par tools/generate_seconde_curated_additions.py) à la fin
d'exercises_bank.json, avec le même schéma que les exercices curés
existants (enonce/answer/hint/solution_steps/chapter_id/notion/difficulty/
id) et des id > 500_000, hors de toute plage déjà utilisée."""
import random
from dataclasses import dataclass
from typing import Callable, Optional

from sympy import Rational, latex, sqrt

CHAPTER_ID = "Chapitre_5"
NOTION_COLINEARITE = "Condition de colinéarité"
NOTION_MILIEU = "Milieu et norme"
NOTION_BASE = "Base, repère et coordonnées"

GENERATED_ID_OFFSET = 500_000

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


def _nz(rng: random.Random, lo: int, hi: int) -> int:
    choices = [n for n in range(lo, hi + 1) if n != 0]
    return rng.choice(choices)


# ── Famille 1 — Coordonnées du vecteur AB ───────────────────────────────────

def _gen_coordonnees_vecteur(rng: random.Random) -> Optional[dict]:
    xa, ya = rng.randint(-8, 8), rng.randint(-8, 8)
    xb, yb = rng.randint(-8, 8), rng.randint(-8, 8)
    if (xa, ya) == (xb, yb):
        return None
    dx, dy = xb - xa, yb - ya
    enonce = f"On donne les points $A({xa} ; {ya})$ et $B({xb} ; {yb})$. Déterminer les coordonnées du vecteur $\\vec{{AB}}$."
    answer = f"$\\vec{{AB}} \\begin{{pmatrix}} {dx} \\\\ {dy} \\end{{pmatrix}}$"
    steps = [
        "Étape 1 — Les coordonnées de $\\vec{AB}$ sont $(x_B - x_A ; y_B - y_A)$.",
        f"Étape 2 — $x_B - x_A = {xb} - ({xa}) = {dx}$ et $y_B - y_A = {yb} - ({ya}) = {dy}$.",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_BASE}


# ── Famille 2 — Milieu d'un segment ─────────────────────────────────────────

def _gen_milieu(rng: random.Random) -> Optional[dict]:
    xa, ya = rng.randint(-9, 9), rng.randint(-9, 9)
    xb, yb = rng.randint(-9, 9), rng.randint(-9, 9)
    xi, yi = Rational(xa + xb, 2), Rational(ya + yb, 2)
    enonce = f"On donne les points $A({xa} ; {ya})$ et $B({xb} ; {yb})$. Déterminer les coordonnées du milieu $I$ du segment $[AB]$."
    answer = f"$I\\left({latex(xi)} ; {latex(yi)}\\right)$"
    steps = [
        "Étape 1 — Les coordonnées du milieu sont $x_I = \\dfrac{x_A + x_B}{2}$ et $y_I = \\dfrac{y_A + y_B}{2}$.",
        f"Étape 2 — $x_I = \\dfrac{{{xa} + {xb}}}{{2}} = {latex(xi)}$ et $y_I = \\dfrac{{{ya} + {yb}}}{{2}} = {latex(yi)}$.",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_MILIEU}


# ── Famille 3 — Norme d'un vecteur ──────────────────────────────────────────

def _gen_norme(rng: random.Random) -> Optional[dict]:
    a, b = _nz(rng, -9, 9), _nz(rng, -9, 9)
    carre = a * a + b * b
    norme = sqrt(carre)
    enonce = f"On donne le vecteur $\\vec{{u}}\\begin{{pmatrix}} {a} \\\\ {b} \\end{{pmatrix}}$. Calculer la norme $\\lVert \\vec{{u}} \\rVert$."
    answer = f"$\\lVert \\vec{{u}} \\rVert = {latex(norme)}$"
    steps = [
        "Étape 1 — La norme d'un vecteur $\\vec{u}(a ; b)$ est $\\lVert \\vec{u} \\rVert = \\sqrt{a^2 + b^2}$.",
        f"Étape 2 — $\\lVert \\vec{{u}} \\rVert = \\sqrt{{({a})^2 + ({b})^2}} = \\sqrt{{{carre}}} = {latex(norme)}$.",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_MILIEU}


# ── Famille 4 — Test de colinéarité de deux vecteurs ───────────────────────

def _gen_colinearite_test(rng: random.Random) -> Optional[dict]:
    a, b = _nz(rng, -6, 6), _nz(rng, -6, 6)
    if rng.random() < 0.5:
        k = Rational(rng.choice([-3, -2, 2, 3]), rng.choice([1, 1, 1, 2]))
        c, d = k * a, k * b
        colineaires = True
    else:
        c, d = _nz(rng, -6, 6), _nz(rng, -6, 6)
        colineaires = (a * d - b * c) == 0
    det = a * d - b * c
    enonce = (
        f"On donne les vecteurs $\\vec{{u}}\\begin{{pmatrix}} {a} \\\\ {b} \\end{{pmatrix}}$ et "
        f"$\\vec{{v}}\\begin{{pmatrix}} {latex(c)} \\\\ {latex(d)} \\end{{pmatrix}}$. "
        f"Les vecteurs $\\vec{{u}}$ et $\\vec{{v}}$ sont-ils colinéaires ?"
    )
    answer = f"{'Oui, ils sont colinéaires' if colineaires else 'Non, ils ne sont pas colinéaires'} (déterminant $= {latex(det)}$)"
    steps = [
        "Étape 1 — $\\vec{u}(a ; b)$ et $\\vec{v}(c ; d)$ sont colinéaires si et seulement si $ad - bc = 0$.",
        f"Étape 2 — $ad - bc = {a} \\times ({latex(d)}) - {b} \\times ({latex(c)}) = {latex(det)}$, donc "
        f"{'ils sont colinéaires.' if colineaires else 'ils ne sont pas colinéaires.'}",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_COLINEARITE}


# ── Famille 5 — Déterminer un paramètre pour rendre deux vecteurs colinéaires

def _gen_determiner_parametre(rng: random.Random) -> Optional[dict]:
    a, b = _nz(rng, -6, 6), _nz(rng, -6, 6)
    c = _nz(rng, -6, 6)
    if a == 0:
        return None
    m = Rational(b * c, a)
    enonce = (
        f"On donne les vecteurs $\\vec{{u}}\\begin{{pmatrix}} {a} \\\\ {b} \\end{{pmatrix}}$ et "
        f"$\\vec{{v}}\\begin{{pmatrix}} {c} \\\\ m \\end{{pmatrix}}$. "
        f"Déterminer la valeur de $m$ pour laquelle $\\vec{{u}}$ et $\\vec{{v}}$ sont colinéaires."
    )
    answer = f"$m = {latex(m)}$"
    steps = [
        "Étape 1 — $\\vec{u}(a ; b)$ et $\\vec{v}(c ; m)$ sont colinéaires si et seulement si $a \\times m - b \\times c = 0$.",
        f"Étape 2 — ${a} \\times m - {b} \\times {c} = 0 \\Longrightarrow m = \\dfrac{{{b} \\times {c}}}{{{a}}} = {latex(m)}$.",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_COLINEARITE}


FAMILY_BASE_SCORE: dict[str, float] = {
    "coordonnees_vecteur": 1.0,
    "milieu": 1.4,
    "norme": 2.0,
    "colinearite_test": 2.6,
    "determiner_parametre": 3.4,
}

FAMILIES: tuple[Family, ...] = (
    Family("coordonnees_vecteur", 1, "Coordonnées d'un vecteur", NOTION_BASE, _gen_coordonnees_vecteur,
           "deux points A et B dont on connaît les coordonnées", "les coordonnées de AB s'obtiennent par (xB - xA ; yB - yA)"),
    Family("milieu", 1, "Milieu d'un segment", NOTION_MILIEU, _gen_milieu,
           "deux points A et B", "le milieu a pour coordonnées la demi-somme des coordonnées de A et B"),
    Family("norme", 2, "Norme d'un vecteur", NOTION_MILIEU, _gen_norme,
           "un vecteur donné par ses coordonnées", "la norme est la racine carrée de la somme des carrés des coordonnées"),
    Family("colinearite_test", 3, "Tester la colinéarité de deux vecteurs", NOTION_COLINEARITE, _gen_colinearite_test,
           "deux vecteurs donnés par leurs coordonnées", "ils sont colinéaires si et seulement si ad - bc = 0"),
    Family("determiner_parametre", 4, "Déterminer un paramètre de colinéarité", NOTION_COLINEARITE, _gen_determiner_parametre,
           "deux vecteurs dont l'un contient un paramètre inconnu", "annuler le déterminant ad - bc pour trouver le paramètre"),
)

FAMILIES_BY_ID: dict[str, Family] = {f.id: f for f in FAMILIES}


def _difficulty_bucket_from_score(score: float) -> int:
    if score <= 1.2:
        return 1
    if score <= 1.8:
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


def generate_pool(per_family: int = 12, seed: int = 20260910) -> list[dict]:
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
