"""Génération symbolique d'exercices sur les probabilités et
l'échantillonnage (Seconde, Chapitre_12).

Mission "porter à 300 exercices minimum par chapitre + diversité
mathématique réelle" (2026-09-02) : Chapitre_12 (211 exercices, 5 notions)
n'avait AUCUN générateur. Toute probabilité annoncée est recalculée
exactement (`fractions.Fraction`) — jamais tapée "en dur".
"""
import random
from dataclasses import dataclass
from fractions import Fraction
from typing import Callable, Optional

CHAPTER_ID = "Chapitre_12"

GENERATED_ID_OFFSET = 590_000

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


# ── 1. Événement contraire ────────────────────────────────────────────────

def _gen_evenement_contraire(rng: random.Random) -> Optional[dict]:
    num = rng.randint(1, 19)
    den = rng.choice([20, 25, 10, 8, 5, 4])
    if num >= den:
        num = rng.randint(1, den - 1)
    p = Fraction(num, den)
    contraire = 1 - p
    enonce = (
        f"Un événement $A$ a pour probabilité $P(A) = {_fmt(p)}$. "
        "Calculer la probabilité de l'événement contraire $\\overline{A}$."
    )
    steps = [
        "Étape 1 — Propriété : $P(\\overline{A}) = 1 - P(A)$.",
        f"Étape 2 — $P(\\overline{{A}}) = 1 - {_fmt(p)} = {_fmt(contraire)}$.",
    ]
    answer = f"$P(\\overline{{A}}) = {_fmt(contraire)}$"
    hint = "La somme des probabilités d'un événement et de son contraire vaut toujours 1."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint,
            # "évènement" (accent grave) : orthographe exacte utilisée par
            # webapp/static/data/topic_crosswalk.json pour ce chapitre —
            # jamais "événement" (accent aigu), qui échoue la validation.
            "notion": "Notion d'évènement"}


# ── 2. Union / intersection d'événements ─────────────────────────────────

def _gen_union_intersection(rng: random.Random) -> Optional[dict]:
    den = rng.choice([20, 25, 30, 10])
    pa = Fraction(rng.randint(2, den // 2), den)
    pb = Fraction(rng.randint(2, den // 2), den)
    incompatibles = rng.choice([True, False])
    if incompatibles:
        p_inter = Fraction(0)
        p_union = pa + pb
        enonce = (
            f"Deux événements incompatibles $A$ et $B$ vérifient $P(A) = {_fmt(pa)}$ et $P(B) = {_fmt(pb)}$. "
            "Calculer $P(A \\cup B)$."
        )
        steps = [
            "Étape 1 — $A$ et $B$ étant incompatibles, $P(A \\cap B) = 0$.",
            f"Étape 2 — $P(A \\cup B) = P(A) + P(B) - P(A \\cap B) = {_fmt(pa)} + {_fmt(pb)} - 0 = {_fmt(p_union)}$.",
        ]
        answer = f"$P(A \\cup B) = {_fmt(p_union)}$"
    else:
        p_inter = Fraction(rng.randint(1, min(pa, pb).numerator if min(pa, pb).numerator > 0 else 1), den)
        if p_inter > pa or p_inter > pb:
            p_inter = Fraction(1, den)
        p_union = pa + pb - p_inter
        enonce = (
            f"Deux événements $A$ et $B$ vérifient $P(A) = {_fmt(pa)}$, $P(B) = {_fmt(pb)}$ et "
            f"$P(A \\cap B) = {_fmt(p_inter)}$. Calculer $P(A \\cup B)$."
        )
        steps = [
            "Étape 1 — Formule générale : $P(A \\cup B) = P(A) + P(B) - P(A \\cap B)$.",
            f"Étape 2 — $P(A \\cup B) = {_fmt(pa)} + {_fmt(pb)} - {_fmt(p_inter)} = {_fmt(p_union)}$.",
        ]
        answer = f"$P(A \\cup B) = {_fmt(p_union)}$"
    hint = "P(A∪B) = P(A) + P(B) - P(A∩B) ; si A et B sont incompatibles, P(A∩B) = 0."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint,
            "notion": "Opérations sur les évènements"}


# ── 3. Loi de probabilité (probabilité manquante) ────────────────────────

def _gen_loi_probabilite(rng: random.Random) -> Optional[dict]:
    n = rng.choice([3, 4])
    den = rng.choice([10, 20, 12, 24])
    probas = []
    reste = den
    for i in range(n - 1):
        maxv = max(1, reste - (n - 1 - i))
        v = rng.randint(1, min(maxv, reste - 1)) if reste > 1 else 0
        probas.append(v)
        reste -= v
    probas.append(reste)
    if any(p <= 0 for p in probas):
        return None
    manquant_idx = rng.randrange(n)
    fracs = [Fraction(p, den) for p in probas]
    noms = [f"x_{i+1}" for i in range(n)]
    lignes = " ; ".join(
        f"$P({noms[i]}) = {_fmt(fracs[i])}$" if i != manquant_idx else f"$P({noms[i]}) = ?$"
        for i in range(n)
    )
    somme_connues = sum(fracs[i] for i in range(n) if i != manquant_idx)
    manquant = 1 - somme_connues
    enonce = (
        f"Une expérience aléatoire a ${n}$ issues possibles ${', '.join(noms)}$. "
        f"On donne la loi de probabilité partielle : {lignes}. Déterminer la probabilité manquante."
    )
    steps = [
        "Étape 1 — La somme des probabilités d'une loi de probabilité vaut toujours $1$.",
        f"Étape 2 — $P({noms[manquant_idx]}) = 1 - ({' + '.join(_fmt(fracs[i]) for i in range(n) if i != manquant_idx)}) = {_fmt(manquant)}$.",
    ]
    answer = f"$P({noms[manquant_idx]}) = {_fmt(manquant)}$"
    hint = "La somme de toutes les probabilités d'une loi de probabilité est égale à 1."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint,
            "notion": "Loi de probabilité"}


# ── 4. Échantillonnage : intervalle de fluctuation (méthode Seconde) ─────

def _gen_echantillonnage(rng: random.Random) -> Optional[dict]:
    p_pct = rng.choice([10, 20, 25, 30, 40, 50, 60, 70])
    p = Fraction(p_pct, 100)
    n = rng.choice([100, 400, 900, 1600, 2500])
    import math
    racine_n = math.isqrt(n)
    if racine_n * racine_n != n:
        return None
    demi_largeur = Fraction(1, racine_n)
    borne_inf = p - demi_largeur
    borne_sup = p + demi_largeur
    freq_num = rng.randint(int(borne_inf * 100) - 3, int(borne_sup * 100) + 3)
    freq = Fraction(freq_num, 100)
    dans_intervalle = borne_inf <= freq <= borne_sup
    enonce = (
        f"Dans une population, on admet que la proportion d'un caractère est $p = {p_pct}\\%$. "
        f"On prélève un échantillon de taille $n = {n}$. "
        f"Sachant que $\\sqrt{{n}} = {racine_n}$, déterminer l'intervalle de fluctuation "
        f"$\\left[p - \\dfrac{{1}}{{\\sqrt{{n}}}}\\,;\\,p + \\dfrac{{1}}{{\\sqrt{{n}}}}\\right]$, "
        f"puis dire si une fréquence observée de ${freq_num}\\%$ est compatible avec $p$."
    )
    steps = [
        f"Étape 1 — $\\dfrac{{1}}{{\\sqrt{{n}}}} = \\dfrac{{1}}{{{racine_n}}} = {_fmt(demi_largeur)}$.",
        f"Étape 2 — Intervalle de fluctuation $= \\left[{_fmt(borne_inf)}\\,;\\,{_fmt(borne_sup)}\\right]$.",
        f"Étape 3 — La fréquence observée ${_fmt(freq)}$ "
        + ("appartient" if dans_intervalle else "n'appartient pas")
        + " à cet intervalle : le résultat observé est donc "
        + ("compatible" if dans_intervalle else "incompatible")
        + " avec $p$ au seuil de 95%.",
    ]
    answer = (
        f"Intervalle $= \\left[{_fmt(borne_inf)}\\,;\\,{_fmt(borne_sup)}\\right]$ — "
        + ("compatible" if dans_intervalle else "incompatible")
    )
    hint = "Intervalle de fluctuation en Seconde : [p - 1/√n ; p + 1/√n]. Une fréquence hors de cet intervalle remet en cause p."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint,
            "notion": "Fluctuation et estimation" if rng.random() < 0.5 else "Echantillon et simulation"}


@dataclass(frozen=True)
class Family:
    id: str
    level: int
    label: str
    generate: Callable[[random.Random], Optional[dict]]
    structure_hint: str
    rule_hint: str


FAMILY_BASE_SCORE: dict[str, float] = {
    "evenement_contraire": 1.2,
    "union_intersection": 2.0,
    "loi_probabilite": 2.4,
    "echantillonnage": 2.9,
}

FAMILIES: tuple[Family, ...] = (
    Family("evenement_contraire", 1, "Événement contraire", _gen_evenement_contraire,
           "une probabilité P(A) donnée", "P(contraire de A) = 1 - P(A)"),
    Family("union_intersection", 2, "Union et intersection", _gen_union_intersection,
           "deux événements A et B", "P(A∪B) = P(A) + P(B) - P(A∩B)"),
    Family("loi_probabilite", 2, "Loi de probabilité", _gen_loi_probabilite,
           "une loi de probabilité partiellement donnée", "la somme de toutes les probabilités vaut 1"),
    Family("echantillonnage", 3, "Intervalle de fluctuation", _gen_echantillonnage,
           "une proportion p et une taille d'échantillon n", "intervalle [p - 1/√n ; p + 1/√n]"),
)

FAMILIES_BY_ID = {f.id: f for f in FAMILIES}


def _difficulty_bucket_from_score(score: float) -> int:
    if score <= 1.4:
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


def generate_pool(per_family: int = 8, seed: int = 950590101, id_offset: int = None) -> list[dict]:
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
