"""Génération symbolique d'exercices sur les variations de fonctions
(Seconde, Chapitre_8 : sens de variation, comparaison d'images, fonctions de
référence, extremums sur un intervalle).

Mission "audit final et rééquilibrage additif global" (2026-09-02) :
Chapitre_8 (160 exercices, 4 notions) n'avait AUCUN générateur — banque
purement curée. Toute image annoncée pour une fonction affine est calculée
exactement (`fractions.Fraction`) ; les sens de variation des fonctions de
référence (x², 1/x, √x) utilisés sont ceux du programme officiel de Seconde,
jamais approximés.
"""
import random
from dataclasses import dataclass
from fractions import Fraction
from typing import Callable, Optional

CHAPTER_ID = "Chapitre_8"

GENERATED_ID_OFFSET = 550_000

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
    if isinstance(v, Fraction):
        if v.denominator == 1:
            return str(v.numerator)
        sign = "-" if v.numerator < 0 else ""
        return f"{sign}\\dfrac{{{abs(v.numerator)}}}{{{v.denominator}}}"
    return str(v)


# ── 1. Sens de variation d'une fonction affine ──────────────────────────────

def _gen_variation_affine(rng: random.Random) -> Optional[dict]:
    a = _nz(rng, -8, 8)
    b = rng.randint(-9, 9)
    a_txt = "-" if a == -1 else ("" if a == 1 else str(a))
    b_txt = f"+{b}" if b > 0 else (f"-{abs(b)}" if b < 0 else "")
    enonce = f"On considère la fonction affine $f(x) = {a_txt}x{b_txt}$. Déterminer son sens de variation sur $\\mathbb{{R}}$."
    if a > 0:
        sens, raison = "croissante", f"le coefficient directeur $a={a}$ est strictement positif"
    else:
        sens, raison = "décroissante", f"le coefficient directeur $a={a}$ est strictement négatif"
    steps = [
        "Étape 1 — Une fonction affine $f(x)=ax+b$ est croissante si $a>0$, décroissante si $a<0$.",
        f"Étape 2 — Ici {raison}, donc $f$ est {sens} sur $\\mathbb{{R}}$.",
    ]
    answer = f"$f$ est {sens} sur $\\mathbb{{R}}$."
    hint = "Le signe du coefficient directeur a suffit à déterminer tout le sens de variation d'une fonction affine."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint,
            "notion": "Variations des fonctions affines"}


# ── 2. Comparer deux images via le sens de variation (sans calculer) ────────

def _gen_comparer_images(rng: random.Random) -> Optional[dict]:
    sens = rng.choice(["croissante", "décroissante"])
    x1 = rng.randint(-10, 10)
    x2 = x1
    while x2 == x1:
        x2 = rng.randint(-10, 10)
    if x1 > x2:
        x1, x2 = x2, x1
    enonce = (
        f"$f$ est une fonction {sens} sur un intervalle contenant ${x1}$ et ${x2}$. "
        f"Comparer $f({x1})$ et $f({x2})$, sans connaître l'expression de $f$."
    )
    if sens == "croissante":
        comp, mot = "<", "conserve"
    else:
        comp, mot = ">", "inverse"
    steps = [
        f"Étape 1 — ${x1} < {x2}$.",
        f"Étape 2 — Une fonction {sens} {mot} l'ordre : {'' if sens=='croissante' else 'elle '}"
        f"{'préserve' if sens=='croissante' else 'inverse'} l'inégalité entre les antécédents.",
    ]
    answer = f"$f({x1}) {comp} f({x2})$"
    hint = "Une fonction croissante conserve l'ordre (x1<x2 ⟹ f(x1)<f(x2)) ; une fonction décroissante l'inverse."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint,
            "notion": "Variations d'une fonction"}


# ── 3. Sens de variation d'une fonction de référence sur un intervalle ──────

def _gen_fonction_reference(rng: random.Random) -> Optional[dict]:
    fonction = rng.choice(["carre", "inverse", "racine"])
    if fonction == "carre":
        cote = rng.choice(["negatif", "positif"])
        if cote == "negatif":
            enonce = "Déterminer le sens de variation de la fonction $f(x)=x^2$ sur $]-\\infty\\,;\\,0]$."
            sens = "décroissante"
            raison = "sur les négatifs, plus x augmente (se rapproche de 0), plus x² diminue"
        else:
            enonce = "Déterminer le sens de variation de la fonction $f(x)=x^2$ sur $[0\\,;\\,+\\infty[$."
            sens = "croissante"
            raison = "sur les positifs, plus x augmente, plus x² augmente"
    elif fonction == "inverse":
        cote = rng.choice(["negatif", "positif"])
        if cote == "negatif":
            enonce = "Déterminer le sens de variation de la fonction $f(x)=\\dfrac{1}{x}$ sur $]-\\infty\\,;\\,0[$."
        else:
            enonce = "Déterminer le sens de variation de la fonction $f(x)=\\dfrac{1}{x}$ sur $]0\\,;\\,+\\infty[$."
        sens = "décroissante"
        raison = "la fonction inverse est décroissante sur chacun des deux intervalles ]-∞;0[ et ]0;+∞[ (mais pas sur leur réunion)"
    else:
        enonce = "Déterminer le sens de variation de la fonction $f(x)=\\sqrt{x}$ sur $[0\\,;\\,+\\infty[$."
        sens = "croissante"
        raison = "la fonction racine carrée est croissante sur tout son ensemble de définition"
    steps = [
        "Étape 1 — Le sens de variation d'une fonction de référence sur un intervalle donné fait partie des résultats à connaître.",
        f"Étape 2 — Ici, {raison}.",
    ]
    answer = f"$f$ est {sens} sur cet intervalle."
    hint = "Connaître par cœur le tableau de variations des trois fonctions de référence : carré, inverse, racine carrée."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint,
            "notion": "Variations des fonctions de référence"}


# ── 4. Extremum d'une fonction affine sur un intervalle fermé ───────────────

def _gen_extremum_affine(rng: random.Random) -> Optional[dict]:
    a = _nz(rng, -6, 6)
    b = rng.randint(-9, 9)
    p = rng.randint(-8, 5)
    q = p
    while q <= p:
        q = rng.randint(-8, 8)
    fp = Fraction(a * p + b)
    fq = Fraction(a * q + b)
    a_txt = "-" if a == -1 else ("" if a == 1 else str(a))
    b_txt = f"+{b}" if b > 0 else (f"-{abs(b)}" if b < 0 else "")
    enonce = (
        f"On considère $f(x) = {a_txt}x{b_txt}$ sur l'intervalle $[{p}\\,;\\,{q}]$. "
        "Déterminer le minimum et le maximum de $f$ sur cet intervalle."
    )
    if a > 0:
        mini, maxi = fp, fq
        raison = f"$f$ est croissante ($a={a}>0$) : le minimum est atteint en $x={p}$ (borne gauche) et le maximum en $x={q}$ (borne droite)"
    else:
        mini, maxi = fq, fp
        raison = f"$f$ est décroissante ($a={a}<0$) : le minimum est atteint en $x={q}$ (borne droite) et le maximum en $x={p}$ (borne gauche)"
    steps = [
        f"Étape 1 — {raison}.",
        f"Étape 2 — $f({p}) = {_fmt(fp)}$ et $f({q}) = {_fmt(fq)}$.",
    ]
    answer = f"Minimum $= {_fmt(mini)}$, maximum $= {_fmt(maxi)}$"
    hint = "Sur un intervalle fermé, une fonction affine atteint ses extremums aux bornes — lesquelles dépend du signe de a."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint,
            "notion": "Maximum et minimum d'une fonction"}


@dataclass(frozen=True)
class Family:
    id: str
    level: int
    label: str
    generate: Callable[[random.Random], Optional[dict]]
    structure_hint: str
    rule_hint: str


FAMILY_BASE_SCORE: dict[str, float] = {
    "variation_affine": 1.0,
    "fonction_reference": 1.4,
    "comparer_images": 2.0,
    "extremum_affine": 2.6,
}

FAMILIES: tuple[Family, ...] = (
    Family("variation_affine", 1, "Sens de variation d'une fonction affine", _gen_variation_affine,
           "une fonction affine ax+b", "le signe de a détermine tout le sens de variation"),
    Family("fonction_reference", 1, "Variations d'une fonction de référence", _gen_fonction_reference,
           "une fonction de référence (carré/inverse/racine) sur un intervalle", "connaître le tableau de variations de chaque fonction de référence"),
    Family("comparer_images", 2, "Comparer deux images via le sens de variation", _gen_comparer_images,
           "deux antécédents et un sens de variation donné", "croissante conserve l'ordre, décroissante l'inverse"),
    Family("extremum_affine", 3, "Extremum d'une fonction affine sur un intervalle", _gen_extremum_affine,
           "une fonction affine sur un intervalle fermé [p;q]", "les extremums sont toujours aux bornes de l'intervalle"),
)

FAMILIES_BY_ID = {f.id: f for f in FAMILIES}


def _difficulty_bucket_from_score(score: float) -> int:
    if score <= 1.2:
        return 1
    if score <= 1.7:
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


def generate_pool(per_family: int = 8, seed: int = 940550101, id_offset: int = None) -> list[dict]:
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
