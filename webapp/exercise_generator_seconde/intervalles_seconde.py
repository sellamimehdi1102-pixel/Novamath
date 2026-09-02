"""Génération symbolique d'exercices sur les intervalles, la comparaison de
nombres, la valeur absolue et les inéquations du premier degré (Seconde,
Chapitre_2 : "Intervalles, inégalités, inéquations").

Mission "porter à 300 exercices minimum par chapitre + diversité
mathématique réelle" (2026-09-02) : Chapitre_2 (196 exercices, 4 notions)
n'avait AUCUN générateur. Toute comparaison/résolution est recalculée
exactement (`fractions.Fraction`) — jamais tapée "en dur".
"""
import random
from dataclasses import dataclass
from fractions import Fraction
from typing import Callable, Optional

CHAPTER_ID = "Chapitre_2"

GENERATED_ID_OFFSET = 570_000

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
        sign = "-" if v.numerator < 0 else ""
        return f"{sign}\\dfrac{{{abs(v.numerator)}}}{{{v.denominator}}}"
    return str(v)


def _rand_frac(rng: random.Random, lo=-12, hi=12) -> Fraction:
    num = rng.randint(lo, hi)
    den = rng.choice([1, 1, 1, 2, 3, 4])
    if num == 0:
        num = 1
    return Fraction(num, den)


# ── 1. Valeur absolue ────────────────────────────────────────────────────

def _gen_valeur_absolue(rng: random.Random) -> Optional[dict]:
    mode = rng.choice(["calcul", "distance"])
    if mode == "calcul":
        a = _rand_frac(rng, -15, 15)
        if a == 0:
            return None
        resultat = abs(a)
        enonce = f"Calculer $|{_fmt(a)}|$."
        steps = [
            f"Étape 1 — $|{_fmt(a)}|$ est la distance de ${_fmt(a)}$ à $0$ sur la droite graduée.",
            f"Étape 2 — Comme ${_fmt(a)} {'<' if a < 0 else '>'} 0$, $|{_fmt(a)}| = {_fmt(resultat)}$.",
        ]
        answer = f"$|{_fmt(a)}| = {_fmt(resultat)}$"
        hint = "|a| = a si a ≥ 0, et |a| = -a si a < 0."
        return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint,
                "notion": "Valeur absolue d'un nombre réel"}
    a = rng.randint(-15, 15)
    b = rng.randint(-15, 15)
    if a == b:
        return None
    distance = abs(a - b)
    enonce = (
        f"Écrire la distance entre les nombres ${a}$ et ${b}$ sous la forme d'une valeur absolue, "
        "puis la calculer."
    )
    steps = [
        f"Étape 1 — La distance entre ${a}$ et ${b}$ s'écrit $|{a} - ({b})|$ (ou $|{b} - ({a})|$).",
        f"Étape 2 — $|{a} - ({b})| = |{a - b}| = {distance}$.",
    ]
    answer = f"Distance $= |{a}-({b})| = {distance}$"
    hint = "La distance entre deux nombres a et b est |a - b| = |b - a|."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint,
            "notion": "Valeur absolue d'un nombre réel"}


# ── 2. Comparaison de nombres ────────────────────────────────────────────

def _gen_comparer_nombres(rng: random.Random) -> Optional[dict]:
    a = _rand_frac(rng, -20, 20)
    b = _rand_frac(rng, -20, 20)
    if a == b:
        return None
    diff = a - b
    if diff > 0:
        symbole, mot = ">", "supérieur"
    else:
        symbole, mot = "<", "inférieur"
    enonce = f"Comparer les nombres $A = {_fmt(a)}$ et $B = {_fmt(b)}$."
    steps = [
        f"Étape 1 — On calcule $A - B = {_fmt(a)} - ({_fmt(b)}) = {_fmt(diff)}$.",
        f"Étape 2 — Comme $A - B {'>' if diff > 0 else '<'} 0$, $A$ est {mot} à $B$ : $A {symbole} B$.",
    ]
    answer = f"$A {symbole} B$"
    hint = "Pour comparer A et B, étudier le signe de A - B."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint,
            "notion": "Comparaison"}


# ── 3. Écriture d'un intervalle ──────────────────────────────────────────

def _gen_intervalle_ecriture(rng: random.Random) -> Optional[dict]:
    a = rng.randint(-10, 5)
    b = a + rng.randint(2, 12)
    ferme_a = rng.choice([True, False])
    ferme_b = rng.choice([True, False])
    sens = "<=" if ferme_a else "<"
    sens2 = "<=" if ferme_b else "<"
    crochet_a = "[" if ferme_a else "]"
    crochet_b = "]" if ferme_b else "["
    enonce = (
        f"Traduire par un intervalle l'ensemble des réels $x$ tels que "
        f"${a} {'\\leq' if ferme_a else '<'} x {'\\leq' if ferme_b else '<'} {b}$."
    )
    steps = [
        f"Étape 1 — La borne ${a}$ est {'incluse' if ferme_a else 'exclue'} : "
        f"crochet {'fermé' if ferme_a else 'ouvert'} du côté de ${a}$.",
        f"Étape 2 — La borne ${b}$ est {'incluse' if ferme_b else 'exclue'} : "
        f"crochet {'fermé' if ferme_b else 'ouvert'} du côté de ${b}$.",
        f"Étape 3 — L'intervalle est ${crochet_a}{a}\\,;\\,{b}{crochet_b}$.",
    ]
    answer = f"${crochet_a}{a}\\,;\\,{b}{crochet_b}$"
    hint = "Un crochet fermé [ ] inclut la borne, un crochet ouvert ] [ l'exclut."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint,
            "notion": "Intervalles"}


# ── 4. Inéquation du premier degré ───────────────────────────────────────

def _gen_inequation(rng: random.Random) -> Optional[dict]:
    a = rng.choice([2, 3, 4, 5, -2, -3, -4, -5])
    b = rng.randint(-15, 15)
    c = rng.randint(-15, 15)
    sens_depart = rng.choice(["<=", ">="])
    # a x + b <= c  ou  >=
    diff = c - b
    borne = Fraction(diff, a)
    if a > 0:
        sens_final = sens_depart
    else:
        sens_final = "<=" if sens_depart == ">=" else ">="
    symb_depart = "\\leq" if sens_depart == "<=" else "\\geq"
    symb_final = "\\leq" if sens_final == "<=" else "\\geq"
    b_txt = f"+ {b}" if b > 0 else (f"- {abs(b)}" if b < 0 else "")
    enonce = f"Résoudre l'inéquation ${a}x {b_txt} {symb_depart} {c}$."
    steps = [
        f"Étape 1 — On isole le terme en $x$ : ${a}x {symb_depart} {c} - ({b}) = {diff}$.",
        f"Étape 2 — On divise par ${a}$ "
        + ("(nombre positif, le sens de l'inégalité est conservé)." if a > 0
           else "(nombre négatif, le sens de l'inégalité s'inverse)."),
        f"Étape 3 — $x {symb_final} {_fmt(borne)}$.",
    ]
    if sens_final == "<=":
        sol_txt = f"\\left]-\\infty\\,;\\,{_fmt(borne)}\\right]"
    else:
        sol_txt = f"\\left[{_fmt(borne)}\\,;\\,+\\infty\\right["
    answer = f"$S = {sol_txt}$"
    hint = "Diviser ou multiplier une inégalité par un nombre négatif inverse son sens."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint,
            "notion": "Inégalités et inéquations"}


@dataclass(frozen=True)
class Family:
    id: str
    level: int
    label: str
    generate: Callable[[random.Random], Optional[dict]]
    structure_hint: str
    rule_hint: str


FAMILY_BASE_SCORE: dict[str, float] = {
    "valeur_absolue": 1.2,
    "comparer_nombres": 1.6,
    "intervalle_ecriture": 2.0,
    "inequation": 2.6,
}

FAMILIES: tuple[Family, ...] = (
    Family("valeur_absolue", 1, "Valeur absolue", _gen_valeur_absolue,
           "un nombre réel ou une distance entre deux nombres", "|a| = distance de a à 0"),
    Family("comparer_nombres", 1, "Comparaison de nombres", _gen_comparer_nombres,
           "deux nombres à comparer", "étudier le signe de la différence A - B"),
    Family("intervalle_ecriture", 2, "Écriture d'un intervalle", _gen_intervalle_ecriture,
           "un encadrement double", "crochet fermé = borne incluse, crochet ouvert = borne exclue"),
    Family("inequation", 3, "Inéquation du premier degré", _gen_inequation,
           "une inéquation ax + b ⋛ c", "diviser par un nombre négatif inverse le sens"),
)

FAMILIES_BY_ID = {f.id: f for f in FAMILIES}


def _difficulty_bucket_from_score(score: float) -> int:
    if score <= 1.4:
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


def generate_pool(per_family: int = 8, seed: int = 950570101, id_offset: int = None) -> list[dict]:
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
