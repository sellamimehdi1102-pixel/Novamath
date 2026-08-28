"""Génération symbolique d'exercices sur les inéquations et le signe d'un
produit/quotient (Seconde, Chapitre_9), notions "Inéquations" et "Signe d'un
produit ou d'un quotient" — mêmes principes que `droites.py` (voir sa
docstring et celle du package) : gabarit déjà élevé pour ces notions, seul un
manque de VARIÉTÉ DE TYPE est corrigé ici (vrai/faux, erreur à corriger,
inversé, contexte, résolution multi-étapes via tableau de signes).
"""
import random
from dataclasses import dataclass
from typing import Callable, Optional

from sympy import Eq, Rational, solve, symbols

x_sym, k_sym = symbols("x k")

CHAPTER_ID = "Chapitre_9"
NOTION_INEQ = "Inéquations"
NOTION_SIGNE = "Signe d'un produit ou d'un quotient"

# Distinct de droites.py (800_000) et de exercises_generated_premiere.json
# (900_000+) — voir tools/generate_seconde_exercises.py.
GENERATED_ID_OFFSET = 810_000

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


def _small(rng: random.Random, lo=-9, hi=9) -> int:
    return rng.randint(lo, hi)


def _fmt_num(r) -> str:
    r = Rational(r)
    if r.q == 1:
        return str(r.p)
    return f"{r.p}/{r.q}"


def _disp(n) -> str:
    s = _fmt_num(n) if hasattr(n, "q") else str(n)
    return f"({s})" if s.startswith("-") else s


def _fmt_interval(op: str, bound) -> str:
    b = _fmt_num(bound)
    if op == ">":
        return f"]{b} ; +∞["
    if op == "≥":
        return f"[{b} ; +∞["
    if op == "<":
        return f"]-∞ ; {b}["
    return f"]-∞ ; {b}]"


_FLIP = {">": "<", "≥": "≤", "<": ">", "≤": "≥"}


# ═════════════════════ Notion : Inéquations ═════════════════════════════════

def _gen_ineq_vf(rng):
    a = _nz(rng, -8, 8)
    b = _small(rng, -10, 10)
    c = _small(rng, -12, 12)
    op = rng.choice([">", "≥", "<", "≤"])
    x0 = _small(rng, -10, 10)
    lhs = a * x0 + b
    ops_py = {">": lhs > c, "≥": lhs >= c, "<": lhs < c, "≤": lhs <= c}
    is_solution = ops_py[op]
    enonce = (
        f"Vrai ou faux : x = {x0} est solution de l'inéquation "
        f"{a}x {'+' if b >= 0 else '-'} {abs(b)} {op} {c}. Justifier."
    )
    steps = [
        f"On remplace x par {x0} : {a}×{_disp(x0)} {'+' if b >= 0 else '-'} {abs(b)} = {lhs}.",
        f"On compare : {lhs} {op} {c} est {'vraie' if is_solution else 'fausse'}.",
    ]
    est_ou_pas = "est" if is_solution else "n'est pas"
    answer = f"{'Vrai' if is_solution else 'Faux'} : x = {x0} {est_ou_pas} solution."
    hint = "Remplacer x par la valeur proposée et vérifier si l'inégalité numérique obtenue est vraie."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


def _gen_ineq_erreur(rng):
    a = -_nz(rng, 1, 8)  # a strictement négatif : diviser par a doit inverser le sens
    b = _small(rng, -10, 10)
    c = _small(rng, -12, 12)
    op = rng.choice([">", "≥"])
    bound = Rational(c - b, a)
    correct_op = _FLIP[op]
    wrong_op = op
    enonce = (
        f"Un élève résout l'inéquation {a}x {'+' if b >= 0 else '-'} {abs(b)} {op} {c} et écrit : "
        f"\"{a}x {op} {c - b}, donc x {wrong_op} {_fmt_num(bound)}\" (il n'a pas changé le sens de "
        "l'inégalité). Identifier son erreur et donner l'ensemble solution correct."
    )
    steps = [
        f"Après avoir isolé le terme en x, on a bien {a}x {op} {c - b}.",
        f"Mais {a} est NÉGATIF : en divisant les deux membres par {a}, il faut inverser le sens de "
        f"l'inégalité, donc x {correct_op} {_fmt_num(bound)} (et non x {wrong_op} {_fmt_num(bound)}).",
        f"Ensemble solution correct : {_fmt_interval(correct_op, bound)}.",
    ]
    answer = f"Erreur : diviser par un nombre négatif inverse le sens. Solution correcte : x {correct_op} {_fmt_num(bound)}, soit {_fmt_interval(correct_op, bound)}."
    hint = "Diviser (ou multiplier) les deux membres d'une inéquation par un nombre NÉGATIF inverse le sens de l'inégalité."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


def _gen_ineq_inverse(rng):
    m = _nz(rng, 1, 9)  # m strictement positif, choisi d'abord pour garantir la cohérence
    b = _small(rng, -8, 8)
    c = _small(rng, -8, 8)
    s = Rational(c - b, m)
    enonce = (
        f"On considère l'inéquation d'inconnue x : kx {'+' if b >= 0 else '-'} {abs(b)} > {c}, où k est "
        f"un réel strictement positif. Sachant que son ensemble solution est ]{_fmt_num(s)} ; +∞[, "
        "déterminer la valeur de k."
    )
    steps = [
        f"Comme k > 0, résoudre kx {'+' if b >= 0 else '-'} {abs(b)} > {c} donne x > ({c}-({b}))/k = "
        f"({c - b})/k.",
        f"On sait que cette solution est x > {_fmt_num(s)}, donc ({c - b})/k = {_fmt_num(s)}.",
        f"On résout : k = ({c - b})/({_fmt_num(s)}) = {m}.",
    ]
    answer = f"k = {m}"
    hint = "Résoudre l'inéquation en fonction de k (en supposant k>0, donc sans changer le sens), puis identifier avec la solution donnée."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


def _gen_ineq_contexte(rng):
    budget = _nz(rng, 20, 200)
    prix = _nz(rng, 2, 15)
    frais = _small(rng, 0, 10)
    n_max = (budget - frais) // prix if prix else 0
    enonce = (
        f"Un client dispose d'un budget de {budget} euros pour acheter des articles à {prix} euros "
        f"pièce, sachant que des frais de livraison fixes de {frais} euros s'ajoutent à la commande. "
        "Combien d'articles peut-il acheter au maximum ?"
    )
    steps = [
        f"Si n désigne le nombre d'articles achetés, le coût total est {prix}n + {frais} euros.",
        f"On doit avoir {prix}n + {frais} ≤ {budget}, soit n ≤ ({budget}-{frais})/{prix} = "
        f"{Rational(budget - frais, prix)}.",
        f"Comme n est un entier, le client peut acheter au maximum {n_max} article(s).",
    ]
    answer = f"Au maximum {n_max} article(s)."
    hint = "Traduire l'énoncé par une inéquation prix×n + frais ≤ budget, puis résoudre en n'oubliant pas que n est un entier."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


# ═════════════════════ Notion : Signe d'un produit ou d'un quotient ════════

def _gen_signe_vf(rng):
    a = _small(rng, -8, 8)
    b = _small(rng, -8, 8)
    if a == b:
        return None
    x0 = _small(rng, -10, 10)
    is_product = rng.random() < 0.5
    fa = x0 - a
    fb = x0 - b
    if is_product:
        val = fa * fb
        expr_txt = f"(x - ({a}))(x - ({b}))" if (a < 0 or b < 0) else f"(x-{a})(x-{b})"
    else:
        if fb == 0:
            return None
        val = Rational(fa, fb)
        expr_txt = f"(x - ({a}))/(x - ({b}))" if (a < 0 or b < 0) else f"(x-{a})/(x-{b})"
    if val == 0:
        return None  # ni positif ni négatif : hors du champ de cette famille (racine exacte)
    is_positive = val > 0
    proposed_sign = rng.choice(["positive", "négative"])
    is_true = (proposed_sign == "positive") == is_positive
    enonce = (
        f"Vrai ou faux : pour x = {x0}, l'expression {expr_txt} est {proposed_sign}."
    )
    steps = [
        f"x - {_disp(a)} = {fa} et x - {_disp(b)} = {fb} pour x = {x0}.",
        f"{'Produit' if is_product else 'Quotient'} : {fa} {'×' if is_product else '/'} {fb} = {_fmt_num(val)}, "
        f"qui est {'positif' if is_positive else 'négatif'}.",
    ]
    answer = f"{'Vrai' if is_true else 'Faux'} : l'expression est {'positive' if is_positive else 'négative'} en x = {x0}."
    hint = "Calculer le signe de chaque facteur séparément (ou du numérateur/dénominateur), puis appliquer la règle des signes."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


def _gen_signe_erreur(rng):
    a = _nz(rng, 1, 9)
    b = _nz(rng, 1, 9)
    is_product = rng.random() < 0.5
    if is_product:
        val = (-a) * (-b)
        wrong_claim = "négatif (produit de deux négatifs)"
        correct_claim = f"positif : (-{a})×(-{b}) = {val} > 0 (le produit de deux nombres négatifs est positif, pas négatif)"
        enonce = (
            f"Un élève affirme : \"(-{a}) × (-{b}) est négatif, car il y a deux signes moins\". "
            "A-t-il raison ? Justifier."
        )
    else:
        val = Rational(-a, -b)
        wrong_claim = "négatif (quotient de deux négatifs)"
        correct_claim = f"positif : (-{a})/(-{b}) = {_fmt_num(val)} > 0 (le quotient de deux nombres négatifs est positif, pas négatif)"
        enonce = (
            f"Un élève affirme : \"(-{a}) / (-{b}) est négatif, car le numérateur et le dénominateur "
            "sont tous les deux négatifs\". A-t-il raison ? Justifier."
        )
    steps = [
        f"Règle des signes : le {'produit' if is_product else 'quotient'} de deux nombres de MÊME signe "
        "est toujours positif (pas seulement quand ils sont positifs tous les deux).",
        f"Ici {correct_claim}.",
    ]
    answer = f"Faux : le résultat est {correct_claim}."
    hint = "Le produit/quotient de deux nombres négatifs est toujours positif — 'même signe' inclut le cas où les deux sont négatifs."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


def _gen_signe_inverse(rng):
    a = _small(rng, -8, 8)
    b = _small(rng, -8, 8)
    while b == a:
        b = _small(rng, -8, 8)
    expr_txt = f"(x-{_disp(a)})(x-{_disp(b)})"
    enonce = f"Pour quelles valeurs de x le produit {expr_txt} est-il nul ?"
    steps = [
        "Un produit de facteurs est nul si et seulement si l'un au moins des facteurs est nul.",
        f"x - {_disp(a)} = 0 donne x = {a} ; x - {_disp(b)} = 0 donne x = {b}.",
    ]
    answer = f"x = {a} ou x = {b}."
    hint = "Un produit est nul si et seulement si l'un de ses facteurs est nul (annulation de chaque facteur séparément)."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


def _gen_signe_tableau(rng):
    a = _small(rng, -6, 6)
    b = _small(rng, -6, 6)
    while b == a:
        b = _small(rng, -6, 6)
    lo, hi = min(a, b), max(a, b)
    want_positive = rng.random() < 0.5
    op = ">" if want_positive else "<"
    expr_txt = f"(x-({a}))(x-({b}))" if (a < 0 or b < 0) else f"(x-{a})(x-{b})"
    enonce = f"Résoudre l'inéquation {expr_txt} {op} 0 à l'aide d'un tableau de signes."
    steps = [
        f"Les racines des facteurs sont x = {a} et x = {b}, qui partagent la droite réelle en trois "
        f"intervalles : ]-∞ ; {lo}[, ]{lo} ; {hi}[ et ]{hi} ; +∞[.",
        "Un produit de deux facteurs affines change de signe à chaque racine et est du signe du produit "
        "des coefficients dominants à l'extérieur des racines (ici +1×+1 = +1, donc positif à l'extérieur).",
        f"Tableau de signes : positif sur ]-∞ ; {lo}[, négatif sur ]{lo} ; {hi}[, positif sur ]{hi} ; +∞[ "
        f"(nul en x={lo} et x={hi}).",
        f"L'ensemble solution de {expr_txt} {op} 0 est donc "
        + (f"]-∞ ; {lo}[ ∪ ]{hi} ; +∞[" if want_positive else f"]{lo} ; {hi}[")
        + ".",
    ]
    answer = (f"]-∞ ; {lo}[ ∪ ]{hi} ; +∞[" if want_positive else f"]{lo} ; {hi}[")
    hint = "Placer les racines des facteurs dans un tableau de signes, puis en déduire le signe du produit sur chaque intervalle."
    return {"enonce": enonce, "answer": answer, "steps": steps, "hint": hint}


@dataclass(frozen=True)
class Family:
    id: str
    level: int
    notion: str
    label: str
    generate: Callable[[random.Random], Optional[dict]]
    structure_hint: str
    rule_hint: str


FAMILY_BASE_SCORE: dict[str, float] = {
    "ineq_vf": 1.3,
    "ineq_erreur": 3.5,
    "ineq_inverse": 3.8,
    "ineq_contexte": 3.0,
    "signe_vf": 1.8,
    "signe_erreur": 3.3,
    "signe_inverse": 2.0,
    "signe_tableau": 4.3,
}

FAMILIES: tuple[Family, ...] = (
    Family("ineq_vf", 1, NOTION_INEQ, "Vrai/faux : une valeur est-elle solution ?", _gen_ineq_vf,
           "une valeur numérique à tester dans une inéquation", "substituer et comparer"),
    Family("ineq_erreur", 4, NOTION_INEQ, "Erreur à corriger : division par un négatif", _gen_ineq_erreur,
           "un sens d'inégalité non inversé lors d'une division par un négatif",
           "diviser par un nombre négatif inverse le sens"),
    Family("ineq_inverse", 4, NOTION_INEQ, "Exercice inversé : retrouver un coefficient",
           _gen_ineq_inverse, "un coefficient inconnu k et une solution donnée",
           "identifier la borne obtenue à la solution donnée"),
    Family("ineq_contexte", 3, NOTION_INEQ, "Problème contextualisé (budget)", _gen_ineq_contexte,
           "un budget maximal à respecter", "traduire par une inéquation puis résoudre en nombre entier"),
    Family("signe_vf", 2, NOTION_SIGNE, "Vrai/faux : signe en une valeur donnée", _gen_signe_vf,
           "une affirmation sur le signe d'un produit/quotient en un point", "calculer chaque facteur puis appliquer la règle des signes"),
    Family("signe_erreur", 4, NOTION_SIGNE, "Erreur à corriger : règle des signes", _gen_signe_erreur,
           "une règle des signes mal appliquée", "produit/quotient de deux négatifs est positif"),
    Family("signe_inverse", 2, NOTION_SIGNE, "Exercice inversé : valeurs d'annulation", _gen_signe_inverse,
           "un produit à annuler", "un produit est nul ssi un facteur est nul"),
    Family("signe_tableau", 5, NOTION_SIGNE, "Résolution via tableau de signes", _gen_signe_tableau,
           "une inéquation produit à résoudre entièrement", "tableau de signes puis lecture de l'ensemble solution"),
)

FAMILIES_BY_ID = {f.id: f for f in FAMILIES}


def _difficulty_bucket_from_score(score: float) -> int:
    if score <= 1.6:
        return 1
    if score <= 2.6:
        return 2
    if score <= 3.4:
        return 3
    if score <= 4.1:
        return 4
    return 5


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
        "notion": family.notion,
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


def generate_pool(per_family: int = 9, seed: int = 20260831) -> list[dict]:
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
