"""Génération symbolique d'exercices de géométrie plane sur les triangles et
parallélogrammes (Troisième, Chapitre_12).

Mission "audit final et rééquilibrage additif global" (2026-09-02) :
Chapitre_12 (210 exercices, 7 notions) n'avait AUCUN générateur — banque
purement curée. Toute conclusion annoncée (angle manquant, existence d'un
triangle, angle correspondant) est recalculée directement à partir des
propriétés géométriques (somme des angles = 180°, inégalité triangulaire,
angles alternes-internes/correspondants), jamais tapée "en dur".

Notions "Triangles égaux"/"Reconnaître un parallélogramme"/"Parallélogrammes
particuliers" restent portées par la banque curée existante (identification
de figures/propriétés à partir d'une figure donnée — se prête mal à un
énoncé textuel généré sans figure) ; les 4 familles ci-dessous couvrent les
notions numériques/calculables du chapitre.
"""
import random
from dataclasses import dataclass
from fractions import Fraction
from typing import Callable, Optional

CHAPTER_ID = "Chapitre_12"

GENERATED_ID_OFFSET = 250_000

LEVEL_META = {
    1: {"emoji": "🟢", "label": "Niveau 1 — Fondamental"},
    2: {"emoji": "🟡", "label": "Niveau 2 — Intermédiaire"},
    3: {"emoji": "🟠", "label": "Niveau 3 — Avancé"},
    4: {"emoji": "🔴", "label": "Niveau 4 — Difficile"},
}


def _fmt(v) -> str:
    if isinstance(v, Fraction):
        if v.denominator == 1:
            return str(v.numerator)
        return f"\\dfrac{{{v.numerator}}}{{{v.denominator}}}"
    return str(v)


# ── 1. Somme des angles d'un triangle (angle manquant) ──────────────────────

def _gen_angle_triangle(rng: random.Random) -> Optional[dict]:
    kind = rng.choice(["quelconque", "isocele"])
    if kind == "quelconque":
        a = rng.randint(20, 130)
        b = rng.randint(20, 150 - a) if a < 140 else 20
        b = max(10, min(b, 150 - a))
        c = 180 - a - b
        if c <= 0 or c >= 160:
            return None
        enonce = (
            f"Dans un triangle $ABC$, on donne $\\widehat{{A}} = {a}°$ et $\\widehat{{B}} = {b}°$. "
            "Déterminer la mesure de l'angle $\\widehat{C}$."
        )
        steps = [
            "Étape 1 — La somme des angles d'un triangle vaut toujours $180°$.",
            f"Étape 2 — $\\widehat{{C}} = 180° - \\widehat{{A}} - \\widehat{{B}} = 180° - {a}° - {b}° = {c}°$.",
        ]
        answer = f"$\\widehat{{C}} = {c}°$"
        hint = "La somme des trois angles d'un triangle vaut 180° : soustraire les deux angles connus de 180°."
    else:
        base = rng.randint(20, 85)
        sommet = 180 - 2 * base
        if sommet <= 0 or sommet >= 180:
            return None
        enonce = (
            f"$ABC$ est un triangle isocèle en $A$, avec $\\widehat{{B}} = {base}°$. "
            "Déterminer les mesures de $\\widehat{C}$ et de $\\widehat{A}$."
        )
        steps = [
            "Étape 1 — Un triangle isocèle en $A$ a deux angles à la base égaux : $\\widehat{B} = \\widehat{C}$.",
            f"Étape 2 — $\\widehat{{C}} = \\widehat{{B}} = {base}°$.",
            f"Étape 3 — $\\widehat{{A}} = 180° - 2\\times{base}° = {sommet}°$.",
        ]
        answer = f"$\\widehat{{C}} = {base}°$ et $\\widehat{{A}} = {sommet}°$"
        hint = "Dans un triangle isocèle, les deux angles à la base (opposés aux côtés égaux) sont égaux."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint,
            "notion": "Somme des angles d'un triangle et inégalité triangulaire" if kind == "quelconque"
            else "Triangle isocèle et triangle équilatéral"}


# ── 2. Inégalité triangulaire (existence d'un triangle) ─────────────────────

def _gen_inegalite_triangulaire(rng: random.Random) -> Optional[dict]:
    a = rng.randint(2, 20)
    b = rng.randint(2, 20)
    make_valid = rng.random() < 0.5
    if make_valid:
        c = rng.randint(abs(a - b) + 1, a + b - 1) if a + b - 1 > abs(a - b) else None
        if c is None:
            return None
    else:
        c = rng.choice([a + b, a + b + rng.randint(1, 5)])
    valid = (a + b > c) and (a + c > b) and (b + c > a)
    enonce = (
        f"Peut-on construire un triangle dont les côtés mesurent ${a}$ cm, ${b}$ cm et ${c}$ cm ? Justifier."
    )
    max_side = max(a, b, c)
    others_sum = a + b + c - max_side
    comparateur = "<" if valid else "\\geq"
    conclusion = "existe" if valid else "n'existe pas"
    steps = [
        "Étape 1 — Un triangle existe si et seulement si la plus grande longueur est INFÉRIEURE à la somme des deux autres (inégalité triangulaire).",
        f"Étape 2 — La plus grande longueur est ${max_side}$ cm ; la somme des deux autres vaut ${others_sum}$ cm.",
        f"Étape 3 — ${max_side} {comparateur} {others_sum}$, donc le triangle {conclusion}.",
    ]
    answer = f"{'Oui' if valid else 'Non'}, ce triangle {'peut' if valid else 'ne peut pas'} être construit."
    hint = "Comparer la plus grande longueur à la somme des deux autres : elle doit être strictement inférieure."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint,
            "notion": "Somme des angles d'un triangle et inégalité triangulaire"}


# ── 3. Angles formés par deux droites parallèles et une sécante ─────────────

def _gen_angles_paralleles(rng: random.Random) -> Optional[dict]:
    angle = rng.randint(20, 160)
    relation = rng.choice(["correspondants", "alternes_internes", "cointerieurs"])
    if relation == "correspondants":
        autre = angle
        regle = "des angles correspondants formés par deux droites parallèles coupées par une sécante sont égaux"
    elif relation == "alternes_internes":
        autre = angle
        regle = "des angles alternes-internes formés par deux droites parallèles coupées par une sécante sont égaux"
    else:
        autre = 180 - angle
        regle = "des angles co-intérieurs (du même côté de la sécante) formés par deux droites parallèles sont supplémentaires (leur somme vaut 180°)"
    label = {"correspondants": "correspondant", "alternes_internes": "alterne-interne", "cointerieurs": "co-intérieur"}[relation]
    enonce = (
        f"Deux droites parallèles $(d_1)$ et $(d_2)$ sont coupées par une sécante $(s)$. "
        f"Un des angles formés mesure ${angle}°$. Déterminer la mesure de son angle {label}."
    )
    steps = [
        f"Étape 1 — Propriété utilisée : {regle}.",
        f"Étape 2 — L'angle {label} mesure donc "
        + (f"${autre}°$ (égal à l'angle donné)." if relation != "cointerieurs"
           else f"$180° - {angle}° = {autre}°$ (supplémentaire de l'angle donné)."),
    ]
    answer = f"${autre}°$"
    hint = "Identifier le type de position (correspondants/alternes-internes : égaux ; co-intérieurs : supplémentaires) avant de conclure."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint,
            "notion": "Angles formés par deux droites parallèles et une sécante"}


# ── 4. Triangles semblables (rapport de longueurs) ──────────────────────────

def _gen_triangles_semblables(rng: random.Random) -> Optional[dict]:
    k = Fraction(rng.choice([2, 3, 4, 5]), rng.choice([1, 1, 2, 3]))
    if k == 1:
        return None
    cote_petit = Fraction(rng.randint(2, 15))
    cote_grand = k * cote_petit
    enonce = (
        f"Les triangles $ABC$ et $A'B'C'$ sont semblables, dans un rapport de similitude $k={_fmt(k)}$ "
        f"(les longueurs de $A'B'C'$ sont obtenues en multipliant celles de $ABC$ par $k$). "
        f"Sachant que $AB = {_fmt(cote_petit)}$ cm, déterminer $A'B'$."
    )
    steps = [
        "Étape 1 — Dans deux triangles semblables de rapport $k$, chaque longueur du second est le produit de la longueur correspondante du premier par $k$.",
        f"Étape 2 — $A'B' = k \\times AB = {_fmt(k)} \\times {_fmt(cote_petit)} = {_fmt(cote_grand)}$ cm.",
    ]
    answer = f"$A'B' = {_fmt(cote_grand)}$ cm"
    hint = "Multiplier directement la longueur connue par le rapport de similitude k."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint,
            "notion": "Triangles semblables"}


@dataclass(frozen=True)
class Family:
    id: str
    level: int
    label: str
    generate: Callable[[random.Random], Optional[dict]]
    structure_hint: str
    rule_hint: str


FAMILY_BASE_SCORE: dict[str, float] = {
    "angle_triangle": 1.0,
    "inegalite_triangulaire": 1.6,
    "angles_paralleles": 2.0,
    "triangles_semblables": 2.6,
}

FAMILIES: tuple[Family, ...] = (
    Family("angle_triangle", 1, "Somme des angles d'un triangle", _gen_angle_triangle,
           "deux angles connus (ou un triangle isocèle)", "la somme des angles d'un triangle vaut 180°"),
    Family("inegalite_triangulaire", 2, "Inégalité triangulaire", _gen_inegalite_triangulaire,
           "trois longueurs proposées", "comparer la plus grande longueur à la somme des deux autres"),
    Family("angles_paralleles", 2, "Angles formés par des parallèles et une sécante", _gen_angles_paralleles,
           "deux droites parallèles coupées par une sécante", "égalité (correspondants/alternes-internes) ou supplémentarité (co-intérieurs)"),
    Family("triangles_semblables", 3, "Triangles semblables", _gen_triangles_semblables,
           "deux triangles semblables et un rapport k", "multiplier la longueur connue par k"),
)

FAMILIES_BY_ID = {f.id: f for f in FAMILIES}


def _difficulty_bucket_from_score(score: float) -> int:
    if score <= 1.3:
        return 1
    if score <= 1.9:
        return 2
    if score <= 2.3:
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


def generate_pool(per_family: int = 8, seed: int = 30260112) -> list[dict]:
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
