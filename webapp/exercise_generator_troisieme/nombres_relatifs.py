"""Génération symbolique d'exercices sur les nombres relatifs (Troisième,
Chapitre_2 : "Addition et soustraction de nombres relatifs", "Multiplication
et division de nombres relatifs", "Puissances d'un nombre relatif",
"Puissances de 10 et écriture scientifique").

Même patron que webapp/exercise_generator_troisieme/equation_premier_degre.py
(patron de référence Troisième) : familles à score fixe, tout résultat
calculé/vérifié par sympy. Créé par la mission "rééquilibrage global de
toutes les classes" (2026-09-01) — Chapitre_2 était sous-représenté (120
exercices, aucun générateur) alors que d'autres chapitres dépassaient 240.
"""
import random
from dataclasses import dataclass
from typing import Callable, Optional

from sympy import Rational, latex

CHAPTER_ID = "Chapitre_2"
NOTION_ADDITION = "Addition et soustraction de nombres relatifs"
NOTION_MULT_DIV = "Multiplication et division de nombres relatifs"
NOTION_PUISSANCE = "Puissances d'un nombre relatif"
NOTION_SCIENTIFIQUE = "Puissances de 10 et écriture scientifique"

GENERATED_ID_OFFSET = 180_000

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


@dataclass(frozen=True)
class Family:
    id: str
    level: int
    label: str
    notion: str
    generate: Callable[[random.Random], Optional[dict]]
    structure_hint: str
    rule_hint: str


# ── Famille 1 — Addition/soustraction de deux relatifs ─────────────────────

def _gen_addition(rng: random.Random) -> Optional[dict]:
    a, b = _nz(rng, -20, 20), _nz(rng, -20, 20)
    operation = rng.choice(["+", "-"])
    resultat = a + b if operation == "+" else a - b
    b_latex = f"({b})" if b < 0 else str(b)
    enonce = f"Calculer $A = {a} {operation} {b_latex}$."
    answer = f"$A = {resultat}$"
    steps = [
        f"Étape 1 — On applique les règles d'addition/soustraction des relatifs à ${a} {operation} {b_latex}$.",
        f"Étape 2 — $A = {resultat}$.",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_ADDITION}


# ── Famille 2 — Multiplication/division de deux relatifs ───────────────────

def _gen_mult_div(rng: random.Random) -> Optional[dict]:
    operation = rng.choice(["\\times", "\\div"])
    if operation == "\\times":
        a, b = _nz(rng, -12, 12), _nz(rng, -12, 12)
        resultat = a * b
    else:
        b = _nz(rng, -10, 10)
        resultat = _nz(rng, -10, 10)
        a = b * resultat
    b_latex = f"({b})" if b < 0 else str(b)
    enonce = f"Calculer $A = {a} {operation} {b_latex}$."
    signe = "positif" if resultat > 0 else "négatif"
    signes_op = "de même signe" if (a > 0) == (b > 0) else "de signes contraires"
    answer = f"$A = {resultat}$"
    steps = [
        f"Étape 1 — ${a}$ et ${b}$ sont {signes_op}, donc le résultat est {signe}.",
        f"Étape 2 — $A = {resultat}$.",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_MULT_DIV}


# ── Famille 3 — Puissance d'un nombre relatif ───────────────────────────────

def _gen_puissance(rng: random.Random) -> Optional[dict]:
    base = _nz(rng, -6, 6)
    exposant = rng.randint(2, 4)
    resultat = base ** exposant
    signe_mot = "positif" if resultat > 0 else "négatif"
    parite = "pair" if exposant % 2 == 0 else "impair"
    enonce = f"Calculer $A = ({base})^{exposant}$."
    answer = f"$A = {resultat}$"
    steps = [
        f"Étape 1 — $({base})^{exposant} = " + " \\times ".join([f"({base})"] * exposant) + "$.",
        f"Étape 2 — L'exposant {exposant} est {parite}, donc le résultat est {signe_mot} (base négative)." if base < 0
        else f"Étape 2 — La base est positive, le résultat est donc positif.",
        f"Étape 3 — $A = {resultat}$.",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_PUISSANCE}


# ── Famille 4 — Écriture scientifique ───────────────────────────────────────
# Décimaux gérés en arithmétique entière exacte (jamais via Rational, qui
# simplifierait 6.4 en 32/5 — faux registre pour une "écriture décimale").

def _decale_virgule(mantisse_num: int, decalage: int) -> str:
    """mantisse_num est un entier à 2 chiffres représentant m.d (ex. 64 -> 6.4).
    Renvoie la représentation décimale de m.d × 10^decalage, décalage ∈ [-9;9]."""
    chiffres = f"{mantisse_num:02d}"  # "64" pour 6.4
    entier, decimal = chiffres[0], chiffres[1]
    tous_chiffres = entier + decimal
    point = 1 + decalage  # position du point dans tous_chiffres, avant décalage
    if point <= 0:
        return "0." + "0" * (-point) + tous_chiffres.rstrip("0").ljust(1, "0") if tous_chiffres.rstrip("0") else "0"
    if point >= len(tous_chiffres):
        return tous_chiffres + "0" * (point - len(tous_chiffres))
    partie_entiere = tous_chiffres[:point] or "0"
    partie_decimale = tous_chiffres[point:].rstrip("0")
    return partie_entiere if not partie_decimale else f"{partie_entiere}.{partie_decimale}"


def _gen_ecriture_scientifique(rng: random.Random) -> Optional[dict]:
    mantisse_num = rng.randint(11, 99)  # représente m.d, ex. 64 -> "6.4"
    mantisse_latex = _decale_virgule(mantisse_num, 0)
    exposant = rng.randint(-5, 6)
    sens = rng.choice(["vers_scientifique", "vers_decimal"])
    if sens == "vers_scientifique":
        decalage = rng.randint(1, 3)
        nombre_brut_latex = _decale_virgule(mantisse_num, decalage)
        # nombre_brut = mantisse × 10^decalage (construction), donc
        # nombre_brut × 10^exposant = mantisse × 10^(decalage+exposant).
        exposant_correct = exposant + decalage
        enonce = f"Écrire le nombre $A = {nombre_brut_latex} \\times 10^{{{exposant}}}$ en écriture scientifique (mantisse entre 1 et 10)."
        answer = f"$A = {mantisse_latex} \\times 10^{{{exposant_correct}}}$"
        steps = [
            f"Étape 1 — La mantisse ${nombre_brut_latex}$ n'est pas comprise entre 1 et 10 : on la réécrit "
            f"${nombre_brut_latex} = {mantisse_latex} \\times 10^{{{decalage}}}$.",
            f"Étape 2 — $A = {mantisse_latex} \\times 10^{{{decalage}}} \\times 10^{{{exposant}}} = "
            f"{mantisse_latex} \\times 10^{{{exposant_correct}}}$.",
        ]
    else:
        valeur_latex = _decale_virgule(mantisse_num, exposant)
        enonce = f"Donner l'écriture décimale du nombre $A = {mantisse_latex} \\times 10^{{{exposant}}}$."
        answer = f"$A = {valeur_latex}$"
        steps = [
            f"Étape 1 — On multiplie ${mantisse_latex}$ par $10^{{{exposant}}}$, ce qui décale la virgule "
            f"de {abs(exposant)} rang(s) vers la {'droite' if exposant > 0 else 'gauche'}.",
            f"Étape 2 — $A = {valeur_latex}$.",
        ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_SCIENTIFIQUE}


FAMILY_BASE_SCORE: dict[str, float] = {
    "addition": 1.0,
    "mult_div": 1.6,
    "puissance": 2.4,
    "ecriture_scientifique": 3.2,
}

FAMILIES: tuple[Family, ...] = (
    Family("addition", 1, "Addition/soustraction de relatifs", NOTION_ADDITION, _gen_addition,
           "une somme ou différence de deux nombres relatifs", "règles de signes de l'addition/soustraction"),
    Family("mult_div", 2, "Multiplication/division de relatifs", NOTION_MULT_DIV, _gen_mult_div,
           "un produit ou quotient de deux nombres relatifs", "règle des signes : mêmes signes → positif, signes contraires → négatif"),
    Family("puissance", 3, "Puissance d'un nombre relatif", NOTION_PUISSANCE, _gen_puissance,
           "une puissance d'un nombre relatif", "le signe du résultat dépend de la parité de l'exposant si la base est négative"),
    Family("ecriture_scientifique", 3, "Écriture scientifique", NOTION_SCIENTIFIQUE, _gen_ecriture_scientifique,
           "une conversion entre écriture scientifique et décimale", "la mantisse doit être comprise entre 1 et 10"),
)

FAMILIES_BY_ID: dict[str, Family] = {f.id: f for f in FAMILIES}


def _difficulty_bucket_from_score(score: float) -> int:
    if score <= 1.3:
        return 1
    if score <= 2.0:
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


def generate_pool(per_family: int = 12, seed: int = 30260201) -> list[dict]:
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
