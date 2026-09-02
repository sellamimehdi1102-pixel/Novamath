"""Génération symbolique d'exercices sur les généralités sur les fonctions et
les fonctions de référence (Seconde, Chapitre_7).

Mission "porter à 300 exercices minimum par chapitre + diversité
mathématique réelle" (2026-09-02) : Chapitre_7 (204 exercices, 5 notions)
n'avait AUCUN générateur. Toute image/parité/résolution est recalculée
exactement (`fractions.Fraction`) à partir de la fonction donnée — jamais
tapée "en dur".
"""
import random
from dataclasses import dataclass
from fractions import Fraction
from typing import Callable, Optional

CHAPTER_ID = "Chapitre_7"

GENERATED_ID_OFFSET = 580_000

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


def _fmt_affine(a: Fraction, b: int) -> str:
    a_txt = "-" if a == -1 else ("" if a == 1 else _fmt(a))
    b_txt = f"+ {b}" if b > 0 else (f"- {abs(b)}" if b < 0 else "")
    return f"{a_txt}x {b_txt}".strip()


# ── 1. Image / antécédent par une fonction affine ────────────────────────

def _gen_image_antecedent(rng: random.Random) -> Optional[dict]:
    a = rng.choice([2, 3, -2, -3, Fraction(1, 2), Fraction(-1, 2)])
    a = Fraction(a)
    b = rng.randint(-8, 8)
    mode = rng.choice(["image", "antecedent"])
    expr = _fmt_affine(a, b)
    if mode == "image":
        x0 = rng.randint(-6, 6)
        y0 = a * x0 + b
        enonce = f"Soit $f(x) = {expr}$. Calculer l'image de ${x0}$ par $f$, c'est-à-dire $f({x0})$."
        steps = [
            f"Étape 1 — On remplace $x$ par ${x0}$ dans l'expression de $f$.",
            f"Étape 2 — $f({x0}) = {_fmt(a)} \\times {x0} {'+' if b >= 0 else '-'} {abs(b)} = {_fmt(y0)}$.",
        ]
        answer = f"$f({x0}) = {_fmt(y0)}$"
        hint = "L'image de x0 par f est f(x0) : on remplace x par x0 dans l'expression."
        return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint,
                "notion": "Notion de fonction"}
    y0 = rng.randint(-10, 10)
    x0 = Fraction(y0 - b, a)
    enonce = f"Soit $f(x) = {expr}$. Déterminer le ou les antécédent(s) de ${y0}$ par $f$."
    steps = [
        f"Étape 1 — On résout l'équation $f(x) = {y0}$, soit ${expr} = {y0}$.",
        f"Étape 2 — ${_fmt(a)}x = {y0} - ({b}) = {y0 - b}$, donc $x = {_fmt(x0)}$.",
    ]
    answer = f"L'antécédent de ${y0}$ est $x = {_fmt(x0)}$"
    hint = "Chercher l'antécédent de y0 revient à résoudre f(x) = y0."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint,
            "notion": "Notion de fonction"}


# ── 2. Parité d'une fonction ─────────────────────────────────────────────

def _gen_parite(rng: random.Random) -> Optional[dict]:
    kind = rng.choice(["paire", "impaire", "aucune"])
    if kind == "paire":
        a = rng.choice([1, 2, 3, -1, -2])
        a_txt = "-" if a == -1 else ("" if a == 1 else str(a))
        c_val = rng.randint(1, 9)
        enonce = f"Soit $f(x) = {a_txt}x^2 + {c_val}$, définie sur $\\mathbb{{R}}$. Étudier la parité de $f$."
        steps = [
            "Étape 1 — $\\mathbb{R}$ est symétrique par rapport à $0$ : on peut étudier $f(-x)$.",
            f"Étape 2 — $f(-x) = {a_txt}(-x)^2 + {c_val} = {a_txt}x^2 + {c_val} = f(x)$.",
            "Étape 3 — Comme $f(-x) = f(x)$ pour tout $x$, $f$ est paire.",
        ]
        answer = "$f$ est paire"
        hint = "f est paire si f(-x) = f(x) pour tout x du domaine."
        return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint,
                "notion": "Parité"}
    if kind == "impaire":
        a = rng.choice([1, 2, 3, -1, -2, -3])
        a_txt = "-" if a == -1 else ("" if a == 1 else str(a))
        neg_a = -a
        neg_a_txt = "-" if neg_a == -1 else ("" if neg_a == 1 else str(neg_a))
        enonce = f"Soit $f(x) = {a_txt}x^3$, définie sur $\\mathbb{{R}}$. Étudier la parité de $f$."
        steps = [
            "Étape 1 — $\\mathbb{R}$ est symétrique par rapport à $0$ : on peut étudier $f(-x)$.",
            f"Étape 2 — $f(-x) = {a_txt}(-x)^3 = {neg_a_txt}x^3 = -f(x)$.",
            "Étape 3 — Comme $f(-x) = -f(x)$ pour tout $x$, $f$ est impaire.",
        ]
        answer = "$f$ est impaire"
        hint = "f est impaire si f(-x) = -f(x) pour tout x du domaine."
        return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint,
                "notion": "Parité"}
    a = rng.choice([1, 2, -1, -2])
    b = rng.choice([2, 3, -2, -3, 4])
    if b == 0:
        return None
    a_txt = "-" if a == -1 else ("" if a == 1 else str(a))
    b_txt = f"+ {b}" if b > 0 else f"- {abs(b)}"
    b_txt_oppose = f"- {b}" if b > 0 else f"+ {abs(b)}"
    enonce = f"Soit $f(x) = {a_txt}x^2 {b_txt}x$, définie sur $\\mathbb{{R}}$. Étudier la parité de $f$."
    steps = [
        "Étape 1 — $\\mathbb{R}$ est symétrique par rapport à $0$ : on peut étudier $f(-x)$.",
        f"Étape 2 — $f(-x) = {a_txt}x^2 {b_txt_oppose}x$, qui n'est égal ni à $f(x)$ ni à $-f(x)$ (le terme en $x$ change de signe, pas celui en $x^2$).",
        "Étape 3 — $f$ n'est ni paire ni impaire.",
    ]
    answer = "$f$ n'est ni paire ni impaire"
    hint = "Si f(-x) n'est ni égal à f(x) ni à -f(x), la fonction n'a pas de parité."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint,
            "notion": "Parité"}


# ── 3. Fonctions de référence : sens de variation en un point ────────────

_REFS = {
    "carre": ("x^2", lambda x: x * x),
    "inverse": ("1/x", lambda x: Fraction(1, x)),
    "racine": ("\\sqrt{x}", None),
}


def _gen_fonction_reference_valeurs(rng: random.Random) -> Optional[dict]:
    ref = rng.choice(["carre", "inverse"])
    label, f = _REFS[ref]
    x1 = rng.choice([i for i in range(-8, 9) if i != 0])
    x2 = rng.choice([i for i in range(-8, 9) if i != 0 and i != x1])
    y1, y2 = f(x1), f(x2)
    if ref == "carre":
        croissante_pos = x1 > 0 and x2 > 0
        croissante_neg = x1 < 0 and x2 < 0
        if croissante_pos:
            comp = "<" if x1 < x2 else ">"
            expected = "<" if x1 < x2 else ">"
        elif croissante_neg:
            expected = ">" if x1 < x2 else "<"
        else:
            expected = None
        if expected is None:
            return None
        vraie_comp = "<" if y1 < y2 else (">" if y1 > y2 else "=")
        enonce = (
            f"La fonction carré $f(x) = x^2$ est décroissante sur $]-\\infty\\,;\\,0]$ et croissante sur "
            f"$[0\\,;\\,+\\infty[$. Sans calculer $f({x1})$ ni $f({x2})$, comparer $f({x1})$ et $f({x2})$."
        )
        steps = [
            f"Étape 1 — ${x1}$ et ${x2}$ sont {'tous deux positifs' if croissante_pos else 'tous deux négatifs'} : "
            f"on est sur un intervalle où $f$ est {'croissante' if croissante_pos else 'décroissante'}.",
            f"Étape 2 — Comme ${x1} {'<' if x1 < x2 else '>'} {x2}$, on en déduit $f({x1}) {expected} f({x2})$.",
            f"Étape 3 — Vérification : $f({x1}) = {y1}$ et $f({x2}) = {y2}$, donc $f({x1}) {vraie_comp} f({x2})$.",
        ]
        answer = f"$f({x1}) {expected} f({x2})$"
    else:
        meme_signe = (x1 > 0) == (x2 > 0)
        if not meme_signe:
            return None
        expected = "<" if x1 < x2 else (">" if x1 > x2 else "=")
        expected = ">" if x1 < x2 else "<"
        vraie_comp = "<" if y1 < y2 else (">" if y1 > y2 else "=")
        enonce = (
            f"La fonction inverse $f(x) = \\dfrac{{1}}{{x}}$ est décroissante sur $]-\\infty\\,;\\,0[$ et sur "
            f"$]0\\,;\\,+\\infty[$. Sans calculer $f({x1})$ ni $f({x2})$, comparer $f({x1})$ et $f({x2})$."
        )
        steps = [
            f"Étape 1 — ${x1}$ et ${x2}$ ont le même signe : on est sur un seul intervalle de monotonie, où $f$ est décroissante.",
            f"Étape 2 — Comme ${x1} {'<' if x1 < x2 else '>'} {x2}$, on en déduit $f({x1}) {expected} f({x2})$.",
            f"Étape 3 — Vérification : $f({x1}) = {_fmt(y1)}$ et $f({x2}) = {_fmt(y2)}$, donc $f({x1}) {vraie_comp} f({x2})$.",
        ]
        answer = f"$f({x1}) {expected} f({x2})$"
    hint = "Utiliser le sens de variation connu de la fonction de référence sur l'intervalle concerné, sans calculer."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint,
            "notion": "Exemples de fonctions de référence"}


# ── 4. Résolution graphique via une fonction affine (f(x)=k, f(x)>k) ─────

def _gen_resolution_graphique(rng: random.Random) -> Optional[dict]:
    a = rng.choice([1, 2, 3, -1, -2, -3])
    b = rng.randint(-8, 8)
    k = rng.randint(-10, 10)
    mode = rng.choice(["equation", "inequation"])
    expr = _fmt_affine(Fraction(a), b)
    if mode == "equation":
        x0 = Fraction(k - b, a)
        enonce = (
            f"On considère la fonction $f(x) = {expr}$ et sa courbe représentative $\\mathcal{{C}}_f$. "
            f"Résoudre graphiquement (par le calcul, en interprétant l'équation) $f(x) = {k}$."
        )
        steps = [
            f"Étape 1 — Résoudre $f(x) = {k}$ revient à trouver l'abscisse du point de $\\mathcal{{C}}_f$ d'ordonnée ${k}$.",
            f"Étape 2 — ${a}x {'+' if b>=0 else '-'} {abs(b)} = {k}$, donc $x = {_fmt(x0)}$.",
        ]
        answer = f"$S = \\{{{_fmt(x0)}\\}}$"
    else:
        x0 = Fraction(k - b, a)
        symb = rng.choice([">", "<"])
        enonce = (
            f"On considère la fonction $f(x) = {expr}$. Résoudre l'inéquation $f(x) {symb} {k}$, "
            "en précisant le sens de variation de f."
        )
        if symb == ">":
            sens_final = ">" if a > 0 else "<"
        else:
            sens_final = "<" if a > 0 else ">"
        steps = [
            f"Étape 1 — $f$ est {'croissante' if a > 0 else 'décroissante'} car $a = {a}$ est {'positif' if a>0 else 'négatif'}.",
            f"Étape 2 — $f(x) {symb} {k} \\iff {a}x {'+' if b>=0 else '-'} {abs(b)} {symb} {k} \\iff x {sens_final} {_fmt(x0)}$"
            + (" (le sens s'inverse car $a<0$)." if a < 0 else " (le sens est conservé car $a>0$)."),
        ]
        if sens_final == ">":
            answer = f"$S = \\left]{_fmt(x0)}\\,;\\,+\\infty\\right[$"
        else:
            answer = f"$S = \\left]-\\infty\\,;\\,{_fmt(x0)}\\right[$"
    hint = "Résoudre f(x) = k ou f(x) ⋛ k algébriquement donne directement la lecture graphique attendue."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint,
            "notion": "Résolutions graphiques d'équations et d'inéquations à l'aide d'une fonction"}


@dataclass(frozen=True)
class Family:
    id: str
    level: int
    label: str
    generate: Callable[[random.Random], Optional[dict]]
    structure_hint: str
    rule_hint: str


FAMILY_BASE_SCORE: dict[str, float] = {
    "image_antecedent": 1.4,
    "parite": 2.0,
    "fonction_reference_valeurs": 2.4,
    "resolution_graphique": 2.8,
}

FAMILIES: tuple[Family, ...] = (
    Family("image_antecedent", 1, "Image et antécédent", _gen_image_antecedent,
           "une fonction affine et une valeur", "f(x0) pour une image, résoudre f(x)=y0 pour un antécédent"),
    Family("parite", 2, "Parité d'une fonction", _gen_parite,
           "une fonction définie sur un ensemble symétrique", "comparer f(-x) à f(x) et à -f(x)"),
    Family("fonction_reference_valeurs", 2, "Comparaison via une fonction de référence", _gen_fonction_reference_valeurs,
           "deux réels sur un même intervalle de monotonie", "utiliser le sens de variation connu, sans calculer"),
    Family("resolution_graphique", 3, "Résolution graphique", _gen_resolution_graphique,
           "une équation ou inéquation f(x) ⋛ k", "traduire la lecture graphique par un calcul algébrique"),
)

FAMILIES_BY_ID = {f.id: f for f in FAMILIES}


def _difficulty_bucket_from_score(score: float) -> int:
    if score <= 1.6:
        return 1
    if score <= 2.2:
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


def generate_pool(per_family: int = 8, seed: int = 950580101, id_offset: int = None) -> list[dict]:
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
