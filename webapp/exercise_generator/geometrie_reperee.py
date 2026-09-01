"""Génération symbolique d'exercices de géométrie repérée (Première,
Chapitre_8 : "Étude d'un ensemble de points", "Vecteur normal à une droite",
"Équation d'un cercle").

Même patron que webapp/exercise_generator/second_degre.py : familles à score
fixe, tout résultat vérifié par sympy. Voir
webapp/exercise_generator/trigonometrie.py pour le contexte de la mission
"rééquilibrage additif" (2026-09-01).
"""
import random
from dataclasses import dataclass
from typing import Callable, Optional

import sympy
from sympy import Rational, expand, latex, sqrt, symbols

x, y = symbols("x y")

CHAPTER_ID = "Chapitre_8"
NOTION_ENSEMBLE_POINTS = "Étude d'un ensemble de points"
NOTION_VECTEUR_NORMAL = "Vecteur normal à une droite"
NOTION_EQUATION_CERCLE = "Équation d'un cercle"

GENERATED_ID_OFFSET = 980_000

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


def _fmt_signed(v, var) -> str:
    if v == 0:
        return ""
    sign = "+" if v > 0 else "-"
    coeff = abs(v)
    coeff_txt = "" if coeff == 1 else str(coeff)
    return f" {sign} {coeff_txt}{var}"


@dataclass(frozen=True)
class Family:
    id: str
    level: int
    label: str
    notion: str
    generate: Callable[[random.Random], Optional[dict]]
    structure_hint: str
    rule_hint: str


# ── Famille 1 — Équation d'un cercle depuis centre + rayon ─────────────────

def _gen_equation_cercle(rng: random.Random) -> Optional[dict]:
    a, b = _nz(rng, -8, 8), _nz(rng, -8, 8)
    r = rng.randint(2, 9)
    r2 = r * r
    enonce = f"Donner l'équation cartésienne du cercle de centre $\\Omega({a}\\,;\\,{b})$ et de rayon $r = {r}$."
    xa = "x" if a == 0 else f"(x{_fmt_signed(-a, '')})" if False else f"(x - {a})" if a > 0 else f"(x + {-a})"
    yb = f"(y - {b})" if b > 0 else f"(y + {-b})"
    answer = f"${xa}^2 + {yb}^2 = {r2}$"
    steps = [
        "Étape 1 — Un cercle de centre $\\Omega(a\\,;\\,b)$ et de rayon $r$ a pour équation "
        "$(x-a)^2 + (y-b)^2 = r^2$.",
        f"Étape 2 — Avec $a = {a}$, $b = {b}$ et $r = {r}$, on obtient {answer}.",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_EQUATION_CERCLE}


# ── Famille 2 — Centre/rayon depuis l'équation réduite ─────────────────────

def _gen_centre_rayon_reduite(rng: random.Random) -> Optional[dict]:
    a, b = _nz(rng, -8, 8), _nz(rng, -8, 8)
    r = rng.randint(2, 9)
    r2 = r * r
    xa = f"(x - {a})" if a > 0 else f"(x + {-a})"
    yb = f"(y - {b})" if b > 0 else f"(y + {-b})"
    enonce = f"Le cercle $\\mathcal{{C}}$ a pour équation ${xa}^2 + {yb}^2 = {r2}$. Donner son centre et son rayon."
    answer = f"Centre $\\Omega({a}\\,;\\,{b})$, rayon $r = {r}$."
    steps = [
        "Étape 1 — L'équation est déjà sous forme réduite $(x-a)^2+(y-b)^2=r^2$.",
        f"Étape 2 — Par identification, $a = {a}$, $b = {b}$ et $r^2 = {r2}$, donc {answer}",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_EQUATION_CERCLE}


# ── Famille 3 — Centre/rayon depuis l'équation développée ──────────────────

def _gen_centre_rayon_developpee(rng: random.Random) -> Optional[dict]:
    a, b = _nz(rng, -6, 6), _nz(rng, -6, 6)
    r = rng.randint(2, 8)
    r2 = r * r
    expr = expand((x - a) ** 2 + (y - b) ** 2 - r2)
    d = expr.coeff(x, 1)
    e = expr.coeff(y, 1)
    f_const = expr.subs({x: 0, y: 0})
    dev_latex = f"x^2 + y^2{_fmt_signed(d, 'x')}{_fmt_signed(e, 'y')}{_fmt_signed(f_const, '')} = 0"
    enonce = f"Le cercle $\\mathcal{{C}}$ a pour équation ${dev_latex}$. Déterminer son centre et son rayon."
    answer = f"Centre $\\Omega({a}\\,;\\,{b})$, rayon $r = {r}$."
    steps = [
        f"Étape 1 — On regroupe : $x^2{_fmt_signed(d,'x')} + y^2{_fmt_signed(e,'y')} = {-f_const}$.",
        f"Étape 2 — On complète le carré : $(x - {a})^2 - {a*a} + (y - {b})^2 - {b*b} = {-f_const}$.",
        f"Étape 3 — $(x - {a})^2 + (y - {b})^2 = {-f_const} + {a*a} + {b*b} = {r2}$, donc {answer}",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_EQUATION_CERCLE}


# ── Famille 4 — Un point appartient-il au cercle ? ─────────────────────────

def _gen_point_appartient_cercle(rng: random.Random) -> Optional[dict]:
    a, b = _nz(rng, -7, 7), _nz(rng, -7, 7)
    r = rng.randint(2, 8)
    r2 = r * r
    force_sur = rng.random() < 0.5
    if force_sur:
        # Point exact sur le cercle : (a + r, b)
        mx, my = a + r, b
    else:
        mx, my = _nz(rng, -10, 10), _nz(rng, -10, 10)
    dist2 = (mx - a) ** 2 + (my - b) ** 2
    est_sur = dist2 == r2
    xa = f"(x - {a})" if a > 0 else f"(x + {-a})"
    yb = f"(y - {b})" if b > 0 else f"(y + {-b})"
    enonce = (
        f"Le cercle $\\mathcal{{C}}$ a pour équation ${xa}^2 + {yb}^2 = {r2}$. "
        f"Le point $M({mx}\\,;\\,{my})$ appartient-il à $\\mathcal{{C}}$ ? Justifier."
    )
    if est_sur:
        answer = f"Oui, $M \\in \\mathcal{{C}}$ car $({mx-a})^2 + ({my-b})^2 = {dist2} = r^2$."
    else:
        answer = f"Non, $M \\notin \\mathcal{{C}}$ car $({mx-a})^2 + ({my-b})^2 = {dist2} \\neq {r2}$."
    steps = [
        "Étape 1 — $M$ appartient au cercle si et seulement si ses coordonnées vérifient l'équation.",
        f"Étape 2 — $({mx}-({a}))^2 + ({my}-({b}))^2 = {dist2}$.",
        f"Étape 3 — {answer}",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_EQUATION_CERCLE}


# ── Famille 5 — Vecteur normal à une droite ────────────────────────────────

def _gen_vecteur_normal(rng: random.Random) -> Optional[dict]:
    a, b = _nz(rng, -9, 9), _nz(rng, -9, 9)
    c = rng.randint(-10, 10)
    droite_latex = f"{a}x{_fmt_signed(b, 'y')}{_fmt_signed(c, '')} = 0"
    enonce = f"La droite $\\mathcal{{D}}$ a pour équation cartésienne ${droite_latex}$. Donner un vecteur normal à $\\mathcal{{D}}$."
    answer = f"$\\vec{{n}}\\begin{{pmatrix}} {a} \\\\ {b} \\end{{pmatrix}}$"
    steps = [
        "Étape 1 — Une droite d'équation $ax+by+c=0$ admet pour vecteur normal $\\vec{n}(a\\,;\\,b)$.",
        f"Étape 2 — Ici $a = {a}$ et $b = {b}$, donc {answer}.",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_VECTEUR_NORMAL}


# ── Famille 6 — Équation d'une droite depuis point + vecteur normal ────────

def _gen_equation_depuis_normal(rng: random.Random) -> Optional[dict]:
    a, b = _nz(rng, -8, 8), _nz(rng, -8, 8)
    px, py = _nz(rng, -7, 7), _nz(rng, -7, 7)
    c = -(a * px + b * py)
    droite_latex = f"{a}x{_fmt_signed(b, 'y')}{_fmt_signed(c, '')} = 0"
    enonce = (
        f"Déterminer une équation cartésienne de la droite $\\mathcal{{D}}$ passant par le point "
        f"$A({px}\\,;\\,{py})$ et de vecteur normal $\\vec{{n}}\\begin{{pmatrix}} {a} \\\\ {b} \\end{{pmatrix}}$."
    )
    answer = f"$\\mathcal{{D}} : {droite_latex}$"
    steps = [
        "Étape 1 — $\\mathcal{D}$ admet une équation de la forme $ax+by+c=0$ avec $(a,b)$ les coordonnées de $\\vec{n}$.",
        f"Étape 2 — $A \\in \\mathcal{{D}}$ donne ${a} \\times {px} + {b} \\times {py} + c = 0$, "
        f"donc $c = {c}$.",
        f"Étape 3 — {answer}",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_VECTEUR_NORMAL}


# ── Famille 7 — Ensemble de points à distance donnée (cercle défini par la distance) ─

def _gen_ensemble_points_distance(rng: random.Random) -> Optional[dict]:
    ax, ay = _nz(rng, -6, 6), _nz(rng, -6, 6)
    r = rng.randint(2, 8)
    r2 = r * r
    enonce = (
        f"Déterminer l'ensemble des points $M(x\\,;\\,y)$ du plan tels que $AM = {r}$, "
        f"où $A({ax}\\,;\\,{ay})$."
    )
    xa = f"(x - {ax})" if ax > 0 else f"(x + {-ax})"
    ya = f"(y - {ay})" if ay > 0 else f"(y + {-ay})"
    answer = f"C'est le cercle de centre $A({ax}\\,;\\,{ay})$ et de rayon ${r}$, d'équation ${xa}^2 + {ya}^2 = {r2}$."
    steps = [
        f"Étape 1 — $AM = {r} \\iff AM^2 = {r2}$.",
        f"Étape 2 — $AM^2 = {xa}^2 + {ya}^2$, donc la condition s'écrit ${xa}^2 + {ya}^2 = {r2}$.",
        f"Étape 3 — {answer}",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_ENSEMBLE_POINTS}


FAMILY_BASE_SCORE: dict[str, float] = {
    "equation_cercle": 1.0,
    "centre_rayon_reduite": 1.2,
    "vecteur_normal": 1.6,
    "point_appartient_cercle": 2.2,
    "ensemble_points_distance": 2.6,
    "equation_depuis_normal": 3.2,
    "centre_rayon_developpee": 4.0,
}

FAMILIES: tuple[Family, ...] = (
    Family("equation_cercle", 1, "Équation d'un cercle depuis centre et rayon", NOTION_EQUATION_CERCLE,
           _gen_equation_cercle, "un centre et un rayon donnés", "(x-a)²+(y-b)²=r²"),
    Family("centre_rayon_reduite", 1, "Centre/rayon depuis l'équation réduite", NOTION_EQUATION_CERCLE,
           _gen_centre_rayon_reduite, "une équation déjà sous forme réduite", "identifier a, b, r² par comparaison directe"),
    Family("vecteur_normal", 2, "Vecteur normal à une droite", NOTION_VECTEUR_NORMAL, _gen_vecteur_normal,
           "une droite donnée par son équation cartésienne", "ax+by+c=0 admet n(a;b) comme vecteur normal"),
    Family("point_appartient_cercle", 2, "Un point appartient-il au cercle ?", NOTION_EQUATION_CERCLE,
           _gen_point_appartient_cercle, "un point et un cercle donnés", "vérifier si les coordonnées vérifient l'équation"),
    Family("ensemble_points_distance", 3, "Ensemble de points à distance fixée", NOTION_ENSEMBLE_POINTS,
           _gen_ensemble_points_distance, "une condition de distance AM=r", "traduire AM=r en AM²=r² puis développer"),
    Family("equation_depuis_normal", 3, "Équation d'une droite (point + normal)", NOTION_VECTEUR_NORMAL,
           _gen_equation_depuis_normal, "un point et un vecteur normal donnés", "poser ax+by+c=0 puis utiliser A∈D pour trouver c"),
    Family("centre_rayon_developpee", 4, "Centre/rayon depuis l'équation développée", NOTION_EQUATION_CERCLE,
           _gen_centre_rayon_developpee, "une équation développée x²+y²+dx+ey+f=0", "compléter le carré en x et en y"),
)

FAMILIES_BY_ID: dict[str, Family] = {f.id: f for f in FAMILIES}


def _difficulty_bucket_from_score(score: float) -> int:
    if score <= 1.3:
        return 1
    if score <= 2.0:
        return 2
    if score <= 3.0:
        return 3
    if score <= 3.6:
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


def generate_pool(per_family: int = 12, seed: int = 20260903) -> list[dict]:
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
