"""Génération symbolique d'exercices sur les critères de divisibilité
(Troisième, Chapitre_1, notion "Critères de divisibilité").

30 exercices existants, 87% calcul direct, 70% gabarits — se prête très
naturellement au vrai/faux justifié, à l'erreur à corriger et à la
comparaison. Toute divisibilité annoncée est vérifiée par calcul entier
direct (`n % d == 0`), jamais tapée "en dur" sans contrôle.
"""
import random
from dataclasses import dataclass
from typing import Callable, Optional

CHAPTER_ID = "Chapitre_1"
NOTION = "Critères de divisibilité"

GENERATED_ID_OFFSET = 110_000

LEVEL_META = {
    1: {"emoji": "🟢", "label": "Niveau 1 — Fondamental"},
    2: {"emoji": "🟡", "label": "Niveau 2 — Intermédiaire"},
    3: {"emoji": "🟠", "label": "Niveau 3 — Avancé"},
    4: {"emoji": "🔴", "label": "Niveau 4 — Difficile"},
}

CRITERES = {
    2: "un nombre est divisible par 2 si son chiffre des unités est 0, 2, 4, 6 ou 8",
    3: "un nombre est divisible par 3 si la somme de ses chiffres est divisible par 3",
    4: "un nombre est divisible par 4 si le nombre formé par ses deux derniers chiffres est divisible par 4",
    5: "un nombre est divisible par 5 si son chiffre des unités est 0 ou 5",
    9: "un nombre est divisible par 9 si la somme de ses chiffres est divisible par 9",
    10: "un nombre est divisible par 10 si son chiffre des unités est 0",
}


def _digit_sum(n: int) -> int:
    return sum(int(c) for c in str(abs(n)))


def _est(cond: bool) -> str:
    """Évite d'imbriquer des guillemets simples ('n'est pas') dans une
    f-string délimitée par des guillemets doubles — source d'erreurs de
    syntaxe difficiles à repérer visuellement."""
    return "est" if cond else "n'est pas"


def _justif(n: int, d: int) -> str:
    if d in (2, 5, 10):
        u = abs(n) % 10
        return f"le chiffre des unités de ${n}$ est ${u}$"
    if d == 4:
        last2 = abs(n) % 100
        return f"les deux derniers chiffres de ${n}$ forment ${last2:02d}$, {'divisible' if last2 % 4 == 0 else 'non divisible'} par 4"
    # 3 ou 9
    s = _digit_sum(n)
    return f"la somme des chiffres de ${n}$ vaut ${s}$"


# ── 1. Test de divisibilité direct ───────────────────────────────────────────

def _gen_test_direct(rng):
    d = rng.choice(list(CRITERES))
    n = rng.randint(20, 999)
    is_div = n % d == 0
    enonce = f"Le nombre ${n}$ est-il divisible par ${d}$ ? Justifier à l'aide du critère de divisibilité."
    answer = f"{'Oui' if is_div else 'Non'}, ${n}$ {_est(is_div)} divisible par ${d}$."
    steps = [
        f"Étape 1 — Critère : {CRITERES[d]}.",
        f"Étape 2 — Ici, {_justif(n, d)}, donc {n} {_est(is_div)} divisible par {d}.",
    ]
    hint = f"Appliquer directement le critère de divisibilité par {d} sans effectuer la division."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


# ── 2. Divisibilité composée (vrai/faux, ex. divisible par 6 = par 2 ET 3) ──

def _gen_vrai_faux_compose(rng):
    n = rng.randint(30, 999)
    is_div6 = n % 6 == 0
    div2 = n % 2 == 0
    div3 = n % 3 == 0
    enonce = f"Un nombre est divisible par $6$ si et seulement s'il est divisible par $2$ ET par $3$. ${n}$ est-il divisible par $6$ ? Justifier."
    answer = f"{'Vrai' if is_div6 else 'Faux'} : ${n}$ {_est(div2)} divisible par 2 et {_est(div3)} divisible par 3, donc il {_est(is_div6)} divisible par 6."
    steps = [
        f"Étape 1 — Divisibilité par 2 : {_justif(n, 2)}, donc {n} {_est(div2)} divisible par 2.",
        f"Étape 2 — Divisibilité par 3 : {_justif(n, 3)}, donc {n} {_est(div3)} divisible par 3.",
        f"Étape 3 — Il faut les DEUX conditions à la fois : {n} {_est(is_div6)} divisible par 6.",
    ]
    hint = "La divisibilité par 6 combine deux critères indépendants (par 2 et par 3) : il faut vérifier les deux, pas un seul."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


# ── 3. Erreur à corriger ─────────────────────────────────────────────────────

def _gen_erreur_a_corriger(rng):
    d = rng.choice([3, 9])
    n = rng.randint(100, 999)
    s = _digit_sum(n)
    is_div = n % d == 0
    # Erreur classique : l'élève regarde le chiffre des unités au lieu de la somme des chiffres.
    unite = n % 10
    wrong_verdict = unite % d == 0
    pas_mot = "" if wrong_verdict else "pas "
    unite_verdict = "est" if wrong_verdict else _est(False)
    enonce = (
        f"Un élève affirme : \"${n}$ n'est {pas_mot}divisible par ${d}$ car son chiffre des "
        f"unités, ${unite}$, {unite_verdict} un multiple de ${d}$\". "
        "Son raisonnement est-il correct ? Justifier et donner la bonne conclusion."
    )
    steps = [
        f"Étape 1 — Le critère de divisibilité par {d} porte sur la SOMME des chiffres, pas sur le chiffre des unités.",
        f"Étape 2 — La somme des chiffres de {n} vaut {s}.",
        f"Étape 3 — {s} {_est(is_div)} divisible par {d}, donc {n} {_est(is_div)} divisible par {d}.",
    ]
    answer = f"Raisonnement incorrect (il utilise le mauvais critère) ; en réalité {n} {_est(is_div)} divisible par {d} (somme des chiffres = {s})."
    hint = "Le critère de 3 et de 9 porte sur la somme des chiffres, pas sur le seul chiffre des unités (contrairement aux critères de 2, 5 et 10)."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


# ── 4. Retrouver un chiffre manquant (exercice inversé) ─────────────────────

def _gen_chiffre_manquant(rng):
    d = rng.choice([2, 3, 5, 9])
    base = rng.randint(10, 99)
    valid_digits = [c for c in range(10) if (base * 10 + c) % d == 0]
    if not valid_digits:
        return None
    chosen = rng.choice(valid_digits)
    enonce = (
        f"Trouver tous les chiffres $c$ tels que le nombre $\\overline{{{base}c}}$ "
        f"(c'est-à-dire {base}0 + c) soit divisible par ${d}$."
    )
    steps = [
        f"Étape 1 — Critère : {CRITERES[d]}.",
        "Étape 2 — On teste chaque chiffre $c$ de 0 à 9 avec ce critère.",
        f"Étape 3 — Les chiffres qui conviennent sont : {', '.join(str(c) for c in valid_digits)}.",
    ]
    answer = "$c \\in \\{" + ";\\,".join(str(c) for c in valid_digits) + "\\}$"
    hint = "Tester chaque chiffre de 0 à 9 avec le critère de divisibilité, plutôt que deviner."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


# ── 5. Comparer deux nombres ─────────────────────────────────────────────────

def _gen_comparer_deux_nombres(rng):
    d = rng.choice(list(CRITERES))
    n1 = rng.randint(20, 999)
    n2 = rng.randint(20, 999)
    while n2 == n1:
        n2 = rng.randint(20, 999)
    div1 = n1 % d == 0
    div2 = n2 % d == 0
    if div1 == div2:
        return None  # on veut un contraste réel entre les deux nombres
    enonce = f"Parmi ${n1}$ et ${n2}$, lequel est divisible par ${d}$ ? Justifier pour les deux nombres."
    winner = n1 if div1 else n2
    answer = f"${winner}$ est divisible par ${d}$ (pas l'autre)."
    steps = [
        f"Étape 1 — Pour {n1} : {_justif(n1, d)}, donc {n1} {_est(div1)} divisible par {d}.",
        f"Étape 2 — Pour {n2} : {_justif(n2, d)}, donc {n2} {_est(div2)} divisible par {d}.",
        f"Étape 3 — Seul {winner} convient.",
    ]
    hint = f"Appliquer le même critère de divisibilité par {d} successivement aux deux nombres."
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
    "test_direct": 1.0,
    "comparer_deux_nombres": 2.0,
    "vrai_faux_compose": 2.3,
    "chiffre_manquant": 3.0,
    "erreur_a_corriger": 3.6,
}

FAMILIES: tuple[Family, ...] = (
    Family("test_direct", 1, "Test de divisibilité direct", _gen_test_direct,
           "un nombre à tester", "appliquer le critère du diviseur demandé"),
    Family("comparer_deux_nombres", 2, "Comparer deux nombres", _gen_comparer_deux_nombres,
           "deux nombres à comparer", "appliquer le même critère aux deux nombres"),
    Family("vrai_faux_compose", 2, "Divisibilité composée (vrai/faux)", _gen_vrai_faux_compose,
           "un diviseur composé (6 = 2×3)", "vérifier les deux critères simples séparément"),
    Family("chiffre_manquant", 3, "Retrouver un chiffre manquant", _gen_chiffre_manquant,
           "un chiffre inconnu à déterminer", "tester chaque chiffre possible avec le critère"),
    Family("erreur_a_corriger", 4, "Détecter et corriger une erreur", _gen_erreur_a_corriger,
           "un raisonnement utilisant le mauvais critère", "comparer au bon critère (somme des chiffres vs chiffre des unités)"),
)

FAMILIES_BY_ID = {f.id: f for f in FAMILIES}


def _difficulty_bucket_from_score(score: float) -> int:
    if score <= 1.5:
        return 1
    if score <= 2.6:
        return 2
    if score <= 3.3:
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


def generate_pool(per_family: int = 6, seed: int = 30260102) -> list[dict]:
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
