"""Génération symbolique d'exercices sur les transformations du plan
(Troisième, Chapitre_11 : symétrie axiale/centrale, translation, rotation,
homothétie).

Mission "audit final et rééquilibrage additif global" (2026-09-02) :
Chapitre_11 (180 exercices, 6 notions) n'avait AUCUN générateur — banque
purement curée. Toutes les transformations étudiées ici sont des
transformations affines EXACTES du plan repéré par des coordonnées
rationnelles : chaque image est calculée et vérifiée par calcul direct
(jamais tapée "en dur"), jamais approchée.

Notion "Frises, pavages et rosaces" (reconnaissance visuelle de motifs) est
volontairement laissée à la banque curée : la nature de cette notion
(identifier un motif dans une image) ne se prête pas à un énoncé textuel
généré sans figure, et forcer un générateur ici produirait un exercice
artificiel plutôt qu'une vraie question de reconnaissance de motif.
"""
import random
from dataclasses import dataclass
from fractions import Fraction
from typing import Callable, Optional

CHAPTER_ID = "Chapitre_11"

GENERATED_ID_OFFSET = 240_000

LEVEL_META = {
    1: {"emoji": "🟢", "label": "Niveau 1 — Fondamental"},
    2: {"emoji": "🟡", "label": "Niveau 2 — Intermédiaire"},
    3: {"emoji": "🟠", "label": "Niveau 3 — Avancé"},
    4: {"emoji": "🔴", "label": "Niveau 4 — Difficile"},
}


def _nz(rng: random.Random, lo: int, hi: int) -> int:
    choices = [n for n in range(lo, hi + 1) if n != 0]
    return rng.choice(choices)


def _fmt(v) -> str:
    """Rend un entier ou une Fraction en LaTeX propre (pas de '3/1')."""
    if isinstance(v, Fraction):
        if v.denominator == 1:
            return str(v.numerator)
        sign = "-" if v.numerator < 0 else ""
        return f"{sign}\\dfrac{{{abs(v.numerator)}}}{{{v.denominator}}}"
    return str(v)


def _point(x, y) -> str:
    return f"({_fmt(x)}\\,;\\,{_fmt(y)})"


# ── 1. Symétrie centrale (image d'un point par symétrie de centre O) ────────

def _gen_symetrie_centrale(rng: random.Random) -> Optional[dict]:
    xa, ya = _nz(rng, -8, 8), _nz(rng, -8, 8)
    xo, yo = rng.randint(-6, 6), rng.randint(-6, 6)
    xa2, ya2 = 2 * xo - xa, 2 * yo - ya
    enonce = (
        f"$A{_point(xa, ya)}$ et $O{_point(xo, yo)}$ sont deux points du plan. "
        f"Déterminer les coordonnées du point $A'$, symétrique de $A$ par rapport à $O$."
    )
    steps = [
        "Étape 1 — Si $A'$ est le symétrique de $A$ par rapport à $O$, alors $O$ est le milieu de $[AA']$.",
        f"Étape 2 — $x_{{A'}} = 2x_O - x_A = 2\\times({xo}) - ({xa}) = {xa2}$ et "
        f"$y_{{A'}} = 2y_O - y_A = 2\\times({yo}) - ({ya}) = {ya2}$.",
    ]
    answer = f"$A'{_point(xa2, ya2)}$"
    hint = "Le centre de symétrie est le milieu du segment reliant un point et son image : utiliser x_A' = 2x_O - x_A."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint,
            "notion": "Symétrie axiale et symétrie centrale"}


# ── 2. Symétrie axiale (par rapport à un axe parallèle aux axes) ────────────

def _gen_symetrie_axiale(rng: random.Random) -> Optional[dict]:
    xa, ya = _nz(rng, -8, 8), _nz(rng, -8, 8)
    axe = rng.choice(["horizontal", "vertical"])
    k = rng.randint(-5, 5)
    if axe == "horizontal":
        xa2, ya2 = xa, 2 * k - ya
        droite = f"la droite d'équation $y={k}$"
    else:
        xa2, ya2 = 2 * k - xa, ya
        droite = f"la droite d'équation $x={k}$"
    enonce = (
        f"$A{_point(xa, ya)}$ est un point du plan. Déterminer les coordonnées du point $A'$, "
        f"symétrique de $A$ par rapport à {droite}."
    )
    if axe == "horizontal":
        steps = [
            f"Étape 1 — Par symétrie par rapport à une droite horizontale $y={k}$, l'abscisse ne change pas : $x_{{A'}}=x_A={xa}$.",
            f"Étape 2 — L'ordonnée est symétrique par rapport à {k} : $y_{{A'}} = 2\\times{k} - {ya} = {ya2}$.",
        ]
    else:
        steps = [
            f"Étape 1 — Par symétrie par rapport à une droite verticale $x={k}$, l'ordonnée ne change pas : $y_{{A'}}=y_A={ya}$.",
            f"Étape 2 — L'abscisse est symétrique par rapport à {k} : $x_{{A'}} = 2\\times{k} - {xa} = {xa2}$.",
        ]
    answer = f"$A'{_point(xa2, ya2)}$"
    hint = "Sur un axe vertical x=k, seule l'abscisse change (symétrique de x_A par rapport à k) ; sur un axe horizontal y=k, seule l'ordonnée change."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint,
            "notion": "Symétrie axiale et symétrie centrale"}


# ── 3. Translation (image d'un point par un vecteur) ────────────────────────

def _gen_translation(rng: random.Random) -> Optional[dict]:
    xa, ya = _nz(rng, -8, 8), _nz(rng, -8, 8)
    a, b = _nz(rng, -6, 6), _nz(rng, -6, 6)
    xa2, ya2 = xa + a, ya + b
    enonce = (
        f"$A{_point(xa, ya)}$ est un point du plan et $\\vec{{u}}{_point(a, b)}$ un vecteur. "
        f"Déterminer les coordonnées du point $A'$, image de $A$ par la translation de vecteur $\\vec{{u}}$."
    )
    steps = [
        f"Étape 1 — La translation de vecteur $\\vec{{u}}(a\\,;\\,b)$ transforme $A(x_A\\,;\\,y_A)$ en "
        f"$A'(x_A+a\\,;\\,y_A+b)$.",
        f"Étape 2 — $x_{{A'}} = {xa} + ({a}) = {xa2}$ et $y_{{A'}} = {ya} + ({b}) = {ya2}$.",
    ]
    answer = f"$A'{_point(xa2, ya2)}$"
    hint = "Ajouter simplement les coordonnées du vecteur à celles du point de départ."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint,
            "notion": "Translation"}


# ── 4. Rotation (quart/demi-tour autour de l'origine) ───────────────────────

def _gen_rotation(rng: random.Random) -> Optional[dict]:
    xa, ya = _nz(rng, -8, 8), _nz(rng, -8, 8)
    angle = rng.choice([90, -90, 180])
    if angle == 90:
        xa2, ya2 = -ya, xa
        desc = "d'un quart de tour dans le sens direct ($90°$)"
    elif angle == -90:
        xa2, ya2 = ya, -xa
        desc = "d'un quart de tour dans le sens indirect ($-90°$)"
    else:
        xa2, ya2 = -xa, -ya
        desc = "d'un demi-tour ($180°$)"
    enonce = (
        f"$A{_point(xa, ya)}$ est un point du plan et $O(0\\,;\\,0)$ l'origine du repère. "
        f"Déterminer les coordonnées du point $A'$, image de $A$ par la rotation de centre $O$ et d'angle {desc}."
    )
    if angle == 180:
        steps = [
            "Étape 1 — Une rotation de centre $O$ et d'angle $180°$ est la symétrie centrale de centre $O$ : $(x\\,;\\,y) \\mapsto (-x\\,;\\,-y)$.",
            f"Étape 2 — $x_{{A'}} = -({xa}) = {xa2}$ et $y_{{A'}} = -({ya}) = {ya2}$.",
        ]
    elif angle == 90:
        steps = [
            "Étape 1 — Une rotation de centre $O$ et d'angle $90°$ (sens direct) transforme $(x\\,;\\,y)$ en $(-y\\,;\\,x)$.",
            f"Étape 2 — $x_{{A'}} = -({ya}) = {xa2}$ et $y_{{A'}} = {xa} = {ya2}$.",
        ]
    else:
        steps = [
            "Étape 1 — Une rotation de centre $O$ et d'angle $-90°$ (sens indirect) transforme $(x\\,;\\,y)$ en $(y\\,;\\,-x)$.",
            f"Étape 2 — $x_{{A'}} = {ya} = {xa2}$ et $y_{{A'}} = -({xa}) = {ya2}$.",
        ]
    answer = f"$A'{_point(xa2, ya2)}$"
    hint = "Une rotation de centre O d'angle 90°, -90° ou 180° a une formule directe sur les coordonnées — pas besoin de trigonométrie ici."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint,
            "notion": "Rotation"}


# ── 5. Homothétie (image d'un point par une homothétie de centre/rapport) ──

def _gen_homothetie(rng: random.Random) -> Optional[dict]:
    xa, ya = _nz(rng, -6, 6), _nz(rng, -6, 6)
    xo, yo = rng.randint(-4, 4), rng.randint(-4, 4)
    k = rng.choice([Fraction(n) for n in (2, 3, -2, -3)] + [Fraction(1, 2), Fraction(-1, 2), Fraction(3, 2)])
    xa2 = Fraction(xo) + k * (xa - xo)
    ya2 = Fraction(yo) + k * (ya - yo)
    enonce = (
        f"$A{_point(xa, ya)}$ est un point du plan, $O{_point(xo, yo)}$ un point et $k={_fmt(k)}$ un réel. "
        f"Déterminer les coordonnées du point $A'$, image de $A$ par l'homothétie de centre $O$ et de rapport $k$."
    )
    steps = [
        "Étape 1 — L'homothétie de centre $O$ et de rapport $k$ transforme $A$ en $A'$ tel que "
        "$\\vec{OA'} = k\\,\\vec{OA}$, soit $x_{A'} = x_O + k(x_A-x_O)$ et $y_{A'} = y_O + k(y_A-y_O)$.",
        f"Étape 2 — $x_{{A'}} = {xo} + {_fmt(k)}\\times({xa}-({xo})) = {_fmt(xa2)}$ et "
        f"$y_{{A'}} = {yo} + {_fmt(k)}\\times({ya}-({yo})) = {_fmt(ya2)}$.",
    ]
    answer = f"$A'{_point(xa2, ya2)}$"
    hint = "Utiliser la relation vectorielle OA' = k·OA, composante par composante, en partant du centre O."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint,
            "notion": "Homothétie"}


# ── 6. Effet d'une homothétie sur une longueur et sur une aire ──────────────

def _gen_effet_homothetie(rng: random.Random) -> Optional[dict]:
    k = rng.choice([Fraction(n) for n in (2, 3, 4, -2, -3)] + [Fraction(1, 2), Fraction(1, 3), Fraction(-1, 2)])
    longueur = Fraction(rng.randint(2, 20))
    aire = Fraction(rng.randint(3, 40))
    longueur_image = abs(k) * longueur
    aire_image = k * k * aire
    enonce = (
        f"Une figure a un côté de longueur ${_fmt(longueur)}$ cm et une aire de ${_fmt(aire)}$ cm². "
        f"On lui applique une homothétie de rapport $k={_fmt(k)}$. "
        "Déterminer la longueur du côté correspondant et l'aire de l'image."
    )
    steps = [
        f"Étape 1 — Une homothétie de rapport $k$ multiplie toutes les LONGUEURS par $|k|$ : "
        f"$|{_fmt(k)}| \\times {_fmt(longueur)} = {_fmt(longueur_image)}$ cm.",
        f"Étape 2 — Une homothétie de rapport $k$ multiplie les AIRES par $k^2$ : "
        f"${_fmt(k)}^2 \\times {_fmt(aire)} = {_fmt(aire_image)}$ cm².",
    ]
    answer = f"Longueur image $= {_fmt(longueur_image)}$ cm ; aire image $= {_fmt(aire_image)}$ cm²"
    hint = "Longueurs : facteur |k|. Aires : facteur k² (jamais k pour l'aire, même si k est négatif)."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint,
            "notion": "Effets d'une homothétie sur les longueurs et les aires"}


@dataclass(frozen=True)
class Family:
    id: str
    level: int
    label: str
    generate: Callable[[random.Random], Optional[dict]]
    structure_hint: str
    rule_hint: str


FAMILY_BASE_SCORE: dict[str, float] = {
    "symetrie_centrale": 1.0,
    "translation": 1.2,
    "symetrie_axiale": 1.4,
    "rotation": 2.2,
    "homothetie": 2.8,
    "effet_homothetie": 2.4,
}

FAMILIES: tuple[Family, ...] = (
    Family("symetrie_centrale", 1, "Image par symétrie centrale", _gen_symetrie_centrale,
           "un point et un centre de symétrie", "le centre est le milieu du point et de son image"),
    Family("translation", 1, "Image par translation", _gen_translation,
           "un point et un vecteur de translation", "ajouter les coordonnées du vecteur au point"),
    Family("symetrie_axiale", 1, "Image par symétrie axiale", _gen_symetrie_axiale,
           "un point et un axe parallèle à un axe du repère", "seule la coordonnée perpendiculaire à l'axe change"),
    Family("rotation", 2, "Image par rotation (centre O)", _gen_rotation,
           "un point et un angle de rotation remarquable", "utiliser la formule directe sur les coordonnées pour 90°/-90°/180°"),
    Family("homothetie", 3, "Image par homothétie", _gen_homothetie,
           "un point, un centre et un rapport d'homothétie", "vecteur OA' = k·OA, composante par composante"),
    Family("effet_homothetie", 2, "Effet d'une homothétie sur longueur/aire", _gen_effet_homothetie,
           "une longueur et une aire soumises à une homothétie de rapport k", "longueur ×|k|, aire ×k²"),
)

FAMILIES_BY_ID = {f.id: f for f in FAMILIES}


def _difficulty_bucket_from_score(score: float) -> int:
    if score <= 1.3:
        return 1
    if score <= 2.0:
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


def generate_pool(per_family: int = 10, seed: int = 30260111) -> list[dict]:
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
