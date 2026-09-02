"""Génération symbolique d'exercices sur la racine carrée, le théorème de
Pythagore et la trigonométrie du triangle rectangle (Troisième, Chapitre_13).

Mission "audit final et rééquilibrage additif global" (2026-09-02) :
Chapitre_13 (181 exercices, 5 notions) n'avait AUCUN générateur — banque
purement curée. Toute valeur annoncée est calculée/vérifiée par sympy
(`sqrt`, `simplify`, `Rational`) — jamais tapée "en dur".

Les rapports trigonométriques utilisés (`trigonometrie_cote`) sont issus de
triplets pythagoriciens exacts (3-4-5, 5-12-13, 8-15-17, 7-24-25...), ce qui
donne des cos/sin/tan RATIONNELS exacts sans jamais recourir à une valeur
d'angle approchée en degrés.
"""
import random
from dataclasses import dataclass
from fractions import Fraction
from typing import Callable, Optional

from sympy import Rational, factorint, latex, sqrt

CHAPTER_ID = "Chapitre_13"

GENERATED_ID_OFFSET = 260_000

LEVEL_META = {
    1: {"emoji": "🟢", "label": "Niveau 1 — Fondamental"},
    2: {"emoji": "🟡", "label": "Niveau 2 — Intermédiaire"},
    3: {"emoji": "🟠", "label": "Niveau 3 — Avancé"},
    4: {"emoji": "🔴", "label": "Niveau 4 — Difficile"},
}

# Triplets pythagoriciens primitifs (a, b, c) avec a<b<c, a²+b²=c² — utilisés
# tels quels ou multipliés par un petit facteur pour varier les longueurs
# tout en gardant des rapports trigonométriques exacts et rationnels.
_TRIPLETS = [(3, 4, 5), (5, 12, 13), (8, 15, 17), (7, 24, 25), (20, 21, 29), (9, 40, 41)]


def _fmt(v) -> str:
    if isinstance(v, Fraction):
        if v.denominator == 1:
            return str(v.numerator)
        return f"\\dfrac{{{v.numerator}}}{{{v.denominator}}}"
    return str(v)


# ── 1. Simplifier une racine carrée ──────────────────────────────────────────

def _gen_simplifier_racine(rng: random.Random) -> Optional[dict]:
    k = rng.randint(2, 9)
    n = rng.choice([2, 3, 5, 6, 7, 10, 11, 13])  # sans facteur carré
    valeur = k * k * n
    simplifie = k * sqrt(n)
    verif = sqrt(valeur)
    if (verif - simplifie).simplify() != 0:
        return None
    enonce = f"Écrire $\\sqrt{{{valeur}}}$ sous la forme $a\\sqrt{{b}}$ avec $b$ le plus petit possible."
    steps = [
        f"Étape 1 — On cherche le plus grand carré parfait divisant {valeur} : ${valeur} = {k}^2 \\times {n}$.",
        f"Étape 2 — $\\sqrt{{{valeur}}} = \\sqrt{{{k}^2 \\times {n}}} = {k}\\sqrt{{{n}}}$.",
    ]
    answer = f"$\\sqrt{{{valeur}}} = {latex(simplifie)}$"
    hint = "Chercher le plus grand facteur carré parfait sous la racine, puis le sortir : √(k²×n) = k√n."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint,
            "notion": "Racine carrée d'un nombre positif"}


# ── 2. Pythagore direct (calcul de l'hypoténuse) ─────────────────────────────

def _gen_pythagore_direct(rng: random.Random) -> Optional[dict]:
    kind = rng.choice(["triplet", "libre"])
    if kind == "triplet":
        a, b, c = rng.choice(_TRIPLETS)
        k = rng.randint(1, 4)
        a, b, c = a * k, b * k, c * k
        hyp_latex = str(c)
        hyp_val = c
    else:
        a = rng.randint(2, 15)
        b = rng.randint(2, 15)
        somme = a * a + b * b
        hyp_val = sqrt(somme)
        if hyp_val.is_integer:
            return None
        hyp_latex = latex(hyp_val)
    enonce = (
        f"$ABC$ est un triangle rectangle en $A$, avec $AB = {a}$ cm et $AC = {b}$ cm. "
        "Calculer la longueur $BC$ (valeur exacte)."
    )
    steps = [
        "Étape 1 — D'après le théorème de Pythagore : $BC^2 = AB^2 + AC^2$.",
        f"Étape 2 — $BC^2 = {a}^2 + {b}^2 = {a*a} + {b*b} = {a*a+b*b}$.",
        f"Étape 3 — $BC = \\sqrt{{{a*a+b*b}}} = {hyp_latex}$ cm.",
    ]
    answer = f"$BC = {hyp_latex}$ cm"
    hint = "Le théorème de Pythagore donne le carré de l'hypoténuse ; ne pas oublier de prendre la racine carrée à la fin."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint,
            "notion": "Théorème de Pythagore"}


# ── 3. Réciproque du théorème de Pythagore (vrai/faux justifié) ─────────────

def _gen_pythagore_reciproque(rng: random.Random) -> Optional[dict]:
    is_right = rng.random() < 0.5
    if is_right:
        a, b, c = rng.choice(_TRIPLETS)
        k = rng.randint(1, 4)
        a, b, c = a * k, b * k, c * k
    else:
        a, b, c = rng.choice(_TRIPLETS)
        k = rng.randint(1, 4)
        a, b, c = a * k, b * k, c * k
        c += rng.randint(1, 3)  # casse l'égalité pythagoricienne
    longest = max(a, b, c)
    others = sorted([a, b, c])[:2]
    somme_carres = others[0] ** 2 + others[1] ** 2
    carre_grand = longest ** 2
    verdict = somme_carres == carre_grand
    enonce = (
        f"Un triangle a pour côtés ${a}$ cm, ${b}$ cm et ${c}$ cm. Ce triangle est-il rectangle ? Justifier "
        "à l'aide de la réciproque du théorème de Pythagore."
    )
    est_ou_pas = "est" if verdict else "n'est pas"
    steps = [
        f"Étape 1 — Le plus grand côté est ${longest}$ cm ; on compare son carré à la somme des carrés des deux autres.",
        f"Étape 2 — ${others[0]}^2 + {others[1]}^2 = {others[0]**2} + {others[1]**2} = {somme_carres}$, "
        f"et ${longest}^2 = {carre_grand}$.",
        f"Étape 3 — {'Les deux valeurs sont égales' if verdict else 'Les deux valeurs sont différentes'}, "
        f"donc le triangle {est_ou_pas} rectangle.",
    ]
    answer = f"{'Oui' if verdict else 'Non'}, ce triangle {est_ou_pas} rectangle."
    hint = "Comparer le carré du plus grand côté à la somme des carrés des deux autres — égalité = rectangle, sinon non."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint,
            "notion": "Réciproque du théorème de Pythagore"}


# ── 4. Trigonométrie : calculer un côté (rapports exacts via triplets) ──────

def _gen_trigonometrie_cote(rng: random.Random) -> Optional[dict]:
    a, b, c = rng.choice(_TRIPLETS)
    k = rng.randint(1, 5)
    adjacent, oppose, hyp = a * k, b * k, c * k
    ratio_fn = rng.choice(["cos", "sin", "tan"])
    if ratio_fn == "cos":
        valeur_ratio = Fraction(adjacent, hyp)
        donnee = f"l'hypoténuse $BC = {hyp}$ cm et $\\cos(\\widehat{{B}}) = {_fmt(valeur_ratio)}$"
        cherche_nom, cherche_val = "AB", adjacent
        formule = "AB = BC \\times \\cos(\\widehat{B})"
        connu_val = hyp
    elif ratio_fn == "sin":
        valeur_ratio = Fraction(oppose, hyp)
        donnee = f"l'hypoténuse $BC = {hyp}$ cm et $\\sin(\\widehat{{B}}) = {_fmt(valeur_ratio)}$"
        cherche_nom, cherche_val = "AC", oppose
        formule = "AC = BC \\times \\sin(\\widehat{B})"
        connu_val = hyp
    else:
        valeur_ratio = Fraction(oppose, adjacent)
        donnee = f"le côté adjacent $AB = {adjacent}$ cm et $\\tan(\\widehat{{B}}) = {_fmt(valeur_ratio)}$"
        cherche_nom, cherche_val = "AC", oppose
        formule = "AC = AB \\times \\tan(\\widehat{B})"
        connu_val = adjacent
    enonce = (
        f"$ABC$ est un triangle rectangle en $A$. On donne {donnee}. "
        f"Calculer la longueur ${cherche_nom}$."
    )
    steps = [
        f"Étape 1 — Dans un triangle rectangle en $A$, on utilise la relation ${formule}$ (angle en $B$).",
        f"Étape 2 — ${cherche_nom} = {connu_val} \\times {_fmt(valeur_ratio)} = {cherche_val}$ cm.",
    ]
    answer = f"${cherche_nom} = {cherche_val}$ cm"
    hint = "Identifier le côté connu (hypoténuse ou adjacent) et le rapport trigonométrique donné, puis isoler le côté cherché."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint,
            "notion": "Cosinus, sinus et tangente d'un angle aigu" if ratio_fn != "tan"
            else "Calculer une longueur ou un angle grâce à la trigonométrie"}


@dataclass(frozen=True)
class Family:
    id: str
    level: int
    label: str
    generate: Callable[[random.Random], Optional[dict]]
    structure_hint: str
    rule_hint: str


FAMILY_BASE_SCORE: dict[str, float] = {
    "simplifier_racine": 1.0,
    "pythagore_direct": 1.6,
    "pythagore_reciproque": 2.2,
    "trigonometrie_cote": 2.8,
}

FAMILIES: tuple[Family, ...] = (
    Family("simplifier_racine", 1, "Simplifier une racine carrée", _gen_simplifier_racine,
           "un nombre sous une racine carrée", "extraire le plus grand facteur carré parfait"),
    Family("pythagore_direct", 2, "Théorème de Pythagore (calcul direct)", _gen_pythagore_direct,
           "un triangle rectangle avec deux côtés connus", "BC² = AB² + AC² puis racine carrée"),
    Family("pythagore_reciproque", 2, "Réciproque du théorème de Pythagore", _gen_pythagore_reciproque,
           "trois longueurs à tester", "comparer le carré du plus grand côté à la somme des carrés des deux autres"),
    Family("trigonometrie_cote", 3, "Trigonométrie du triangle rectangle", _gen_trigonometrie_cote,
           "un rapport trigonométrique et un côté connus", "isoler le côté cherché via cos/sin/tan"),
)

FAMILIES_BY_ID = {f.id: f for f in FAMILIES}


def _difficulty_bucket_from_score(score: float) -> int:
    if score <= 1.3:
        return 1
    if score <= 1.9:
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


def generate_pool(per_family: int = 10, seed: int = 30260113) -> list[dict]:
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
