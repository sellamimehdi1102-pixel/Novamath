"""Génération symbolique d'exercices sur les variables aléatoires (Première,
Chapitre_10 : "Variables aléatoires réelles", "Espérance – Variance –
Écart-type").

Même patron que webapp/exercise_generator/second_degre.py : familles à score
fixe, toute probabilité/espérance manipulée en fraction exacte
(sympy.Rational). Voir webapp/exercise_generator/trigonometrie.py pour le
contexte de la mission "rééquilibrage additif" (2026-09-01).
"""
import random
from dataclasses import dataclass
from typing import Callable, Optional

from sympy import Rational, latex, sqrt, simplify

CHAPTER_ID = "Chapitre_10"
NOTION_VARIABLES = "Variables aléatoires réelles"
NOTION_ESPERANCE = "Espérance – Variance – Écart-type"

GENERATED_ID_OFFSET = 1_000_000

LEVEL_META = {
    1: {"emoji": "🟢", "label": "Niveau 1 — Fondamental"},
    2: {"emoji": "🟡", "label": "Niveau 2 — Intermédiaire"},
    3: {"emoji": "🟠", "label": "Niveau 3 — Avancé"},
    4: {"emoji": "🔴", "label": "Niveau 4 — Difficile"},
    5: {"emoji": "🟣", "label": "Niveau 5 — Défi"},
}


def _loi_3_valeurs(rng: random.Random):
    """Construit une loi de probabilité à 3 valeurs distinctes (x1<x2<x3),
    probabilités en fractions de dénominateur commun, sommant exactement à 1."""
    den = rng.choice([4, 5, 6, 8, 10])
    parts = []
    remaining = den
    for _ in range(2):
        take = rng.randint(1, remaining - 2) if remaining > 2 else 1
        parts.append(take)
        remaining -= take
    parts.append(remaining)
    rng.shuffle(parts)
    probs = [Rational(p, den) for p in parts]
    values = sorted(rng.sample(range(-6, 9), 3))
    return values, probs


@dataclass(frozen=True)
class Family:
    id: str
    level: int
    label: str
    notion: str
    generate: Callable[[random.Random], Optional[dict]]
    structure_hint: str
    rule_hint: str


def _table_latex(values, probs) -> str:
    header = " & ".join(f"x_{i+1}={v}" for i, v in enumerate(values))
    row = " & ".join(f"{latex(p)}" for p in probs)
    return f"$P(X=x_i)$ : " + ", ".join(f"$P(X={v}) = {latex(p)}$" for v, p in zip(values, probs))


# ── Famille 1 — Calcul de l'espérance ───────────────────────────────────────

def _gen_esperance(rng: random.Random) -> Optional[dict]:
    values, probs = _loi_3_valeurs(rng)
    esperance = sum(v * p for v, p in zip(values, probs))
    table = _table_latex(values, probs)
    enonce = f"Une variable aléatoire $X$ suit la loi de probabilité suivante : {table}. Calculer $E(X)$."
    answer = f"$E(X) = {latex(esperance)}$"
    terms = " + ".join(f"{v} \\times {latex(p)}" for v, p in zip(values, probs))
    steps = [
        "Étape 1 — On utilise la formule $E(X) = \\sum x_i \\times P(X=x_i)$.",
        f"Étape 2 — $E(X) = {terms} = {latex(esperance)}$.",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_ESPERANCE}


# ── Famille 2 — Compléter une loi de probabilité ───────────────────────────

def _gen_completer_loi(rng: random.Random) -> Optional[dict]:
    values, probs = _loi_3_valeurs(rng)
    idx_inconnue = rng.randint(0, 2)
    manquante = probs[idx_inconnue]
    connues = [(v, p) for i, (v, p) in enumerate(zip(values, probs)) if i != idx_inconnue]
    table = ", ".join(f"$P(X={v}) = {latex(p)}$" for v, p in connues)
    enonce = (
        f"Une variable aléatoire $X$ prend les valeurs ${values[0]}$, ${values[1]}$ et ${values[2]}$. "
        f"On donne {table}. Déterminer $P(X={values[idx_inconnue]})$."
    )
    somme_connues = sum(p for _, p in connues)
    answer = f"$P(X={values[idx_inconnue]}) = {latex(manquante)}$"
    steps = [
        "Étape 1 — La somme des probabilités d'une loi vaut $1$.",
        f"Étape 2 — $P(X={values[idx_inconnue]}) = 1 - \\left({' + '.join(latex(p) for _, p in connues)}\\right) = 1 - {latex(somme_connues)}$.",
        f"Étape 3 — {answer}",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_VARIABLES}


# ── Famille 3 — Variance et écart-type ──────────────────────────────────────

def _gen_variance(rng: random.Random) -> Optional[dict]:
    values, probs = _loi_3_valeurs(rng)
    esperance = sum(v * p for v, p in zip(values, probs))
    esperance_carre = sum((v ** 2) * p for v, p in zip(values, probs))
    variance = simplify(esperance_carre - esperance ** 2)
    ecart_type = simplify(sqrt(variance))
    table = _table_latex(values, probs)
    enonce = f"Une variable aléatoire $X$ suit la loi de probabilité suivante : {table}. Calculer $V(X)$ puis $\\sigma(X)$."
    answer = f"$V(X) = {latex(variance)}$, $\\sigma(X) = {latex(ecart_type)}$"
    steps = [
        f"Étape 1 — On calcule d'abord $E(X) = {latex(esperance)}$.",
        f"Étape 2 — On calcule $E(X^2) = \\sum x_i^2 \\times P(X=x_i) = {latex(esperance_carre)}$.",
        f"Étape 3 — $V(X) = E(X^2) - E(X)^2 = {latex(esperance_carre)} - \\left({latex(esperance)}\\right)^2 = {latex(variance)}$.",
        f"Étape 4 — $\\sigma(X) = \\sqrt{{V(X)}} = \\sqrt{{{latex(variance)}}} = {latex(ecart_type)}$.",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_ESPERANCE}


# ── Famille 4 — Transformation affine E(aX+b), V(aX+b) ─────────────────────

def _gen_transformation_affine(rng: random.Random) -> Optional[dict]:
    ex = Rational(rng.randint(-8, 8), rng.choice([1, 2, 3, 4]))
    vx = Rational(rng.randint(1, 12), rng.choice([1, 2, 3, 4]))
    a = rng.choice([n for n in range(-5, 6) if n != 0])
    b = rng.randint(-6, 6)
    e_result = a * ex + b
    v_result = (a ** 2) * vx
    b_suffix = f" + {b}" if b > 0 else (f" - {-b}" if b < 0 else "")
    a_prefix = "-" if a == -1 else ("" if a == 1 else str(a))
    enonce = (
        f"On donne $E(X) = {latex(ex)}$ et $V(X) = {latex(vx)}$. On pose $Y = {a_prefix}X{b_suffix}$. "
        f"Calculer $E(Y)$ et $V(Y)$."
    )
    answer = f"$E(Y) = {latex(e_result)}$, $V(Y) = {latex(v_result)}$"
    steps = [
        f"Étape 1 — Pour $Y=aX+b$, $E(Y) = a\\,E(X) + b = {a} \\times {latex(ex)} + ({b}) = {latex(e_result)}$.",
        f"Étape 2 — $V(Y) = a^2\\,V(X) = {a}^2 \\times {latex(vx)} = {latex(v_result)}$.",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_ESPERANCE}


# ── Famille 5 — Jeu contextualisé : gain espéré, équité ────────────────────

_CONTEXTES_JEU = [
    {"nom": "tirer une boule dans une urne", "gain_mot": "gain algébrique"},
    {"nom": "lancer un dé truqué", "gain_mot": "gain algébrique"},
    {"nom": "jouer à une loterie", "gain_mot": "gain algébrique"},
]


def _gen_jeu_esperance(rng: random.Random) -> Optional[dict]:
    ctx = rng.choice(_CONTEXTES_JEU)
    mise = rng.randint(2, 10)
    gain_grand = rng.randint(mise + 5, mise + 30)
    p_gagner = Rational(1, rng.choice([4, 5, 6, 8, 10]))
    p_perdre = 1 - p_gagner
    values = [gain_grand - mise, -mise]
    probs = [p_gagner, p_perdre]
    esperance = sum(v * p for v, p in zip(values, probs))
    verdict = "favorable au joueur" if esperance > 0 else ("défavorable au joueur" if esperance < 0 else "équitable")
    enonce = (
        f"Pour {ctx['nom']}, la mise est de ${mise}$ € ; le joueur gagne ${gain_grand}$ € avec une probabilité "
        f"de ${latex(p_gagner)}$, et ne gagne rien sinon. Soit $X$ le {ctx['gain_mot']} du joueur (gain moins mise). "
        "Déterminer la loi de $X$, calculer $E(X)$, et dire si le jeu est favorable au joueur, défavorable, ou équitable."
    )
    answer = f"$E(X) = {latex(esperance)}$ : le jeu est {verdict}."
    steps = [
        f"Étape 1 — Si le joueur gagne (probabilité ${latex(p_gagner)}$) : gain algébrique $= {gain_grand} - {mise} = {values[0]}$.",
        f"Étape 2 — Si le joueur perd (probabilité ${latex(p_perdre)}$) : gain algébrique $= -{mise}$.",
        f"Étape 3 — $E(X) = {values[0]} \\times {latex(p_gagner)} + ({values[1]}) \\times {latex(p_perdre)} = {latex(esperance)}$.",
        f"Étape 4 — {answer}",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_VARIABLES}


# ── Familles supplémentaires — mission "diversification structurelle"
# (2026-09-02) : les familles d'origine ci-dessus reposent chacune sur UN
# SEUL type de raisonnement (ex. esperance = toujours "table de loi -> somme
# directe"), audité comme quasi-doublon à 98-99% (les exercices d'une même
# famille ne diffèrent que par leurs coefficients). Ces nouvelles familles
# introduisent un raisonnement RÉELLEMENT différent pour la même notion,
# jamais une simple reformulation textuelle — voir EXTRA_FAMILIES plus bas,
# jamais mélangées à FAMILIES/generate_pool (baseline figée, voir
# tools/generate_derivative_exercises.py).

def _gen_esperance_effectifs(rng: random.Random) -> Optional[dict]:
    """Structure différente de _gen_esperance : la loi n'est pas donnée
    directement en probabilités mais en EFFECTIFS d'une population — il faut
    d'abord convertir (division par l'effectif total) avant d'appliquer la
    formule de l'espérance. Une étape de raisonnement supplémentaire par
    rapport à la famille d'origine."""
    n_groupes = 3
    effectifs = [rng.randint(5, 40) for _ in range(n_groupes)]
    total = sum(effectifs)
    values = sorted(rng.sample(range(-5, 15), n_groupes))
    probs = [Rational(e, total) for e in effectifs]
    esperance = sum(v * p for v, p in zip(values, probs))
    table = ", ".join(f"${v}$ (${e}$ individus)" for v, e in zip(values, effectifs))
    enonce = (
        f"Dans une population de ${total}$ individus, on relève la valeur d'un caractère $X$ : "
        f"{table}. On choisit un individu au hasard dans cette population. Calculer $E(X)$."
    )
    answer = f"$E(X) = {latex(esperance)}$"
    termes = " + ".join(f"{v} \\times \\dfrac{{{e}}}{{{total}}}" for v, e in zip(values, effectifs))
    steps = [
        f"Étape 1 — On convertit chaque effectif en probabilité : $P(X=x_i) = \\dfrac{{\\text{{effectif}}}}{{{total}}}$.",
        f"Étape 2 — On applique $E(X) = \\sum x_i \\times P(X=x_i) = {termes} = {latex(esperance)}$.",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_ESPERANCE}


def _gen_esperance_inverse(rng: random.Random) -> Optional[dict]:
    """Problème INVERSE : l'espérance est donnée, une des deux valeurs de X
    est inconnue — il faut résoudre une équation du premier degré, pas
    seulement appliquer la formule dans le sens direct."""
    p1 = Rational(rng.choice([1, 1, 2, 3]), rng.choice([4, 5, 6, 8]))
    if p1 <= 0 or p1 >= 1:
        return None
    p2 = 1 - p1
    x1 = rng.randint(-8, 8)
    x2 = rng.choice([n for n in range(-8, 9) if n != x1])
    esperance = x1 * p1 + x2 * p2
    enonce = (
        f"Une variable aléatoire $X$ prend deux valeurs : $x_1={x1}$ avec probabilité $P(X=x_1)={latex(p1)}$, "
        f"et $x_2$ (inconnue) avec probabilité $P(X=x_2)={latex(p2)}$. Sachant que $E(X) = {latex(esperance)}$, "
        f"déterminer $x_2$."
    )
    answer = f"$x_2 = {x2}$"
    steps = [
        f"Étape 1 — $E(X) = x_1 \\times P(X=x_1) + x_2 \\times P(X=x_2)$, donc "
        f"${latex(esperance)} = {x1} \\times {latex(p1)} + x_2 \\times {latex(p2)}$.",
        f"Étape 2 — ${latex(esperance)} - {latex(x1 * p1)} = x_2 \\times {latex(p2)}$, soit "
        f"$x_2 = \\dfrac{{{latex(esperance - x1 * p1)}}}{{{latex(p2)}}} = {x2}$.",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_VARIABLES}


def _gen_completer_loi_systeme(rng: random.Random) -> Optional[dict]:
    """Structure différente de _gen_completer_loi : DEUX probabilités sont
    inconnues, liées par une relation (p1 = k×p2) — résoudre un petit
    système, pas une simple soustraction à 1."""
    values = sorted(rng.sample(range(-6, 10), 3))
    k = rng.choice([2, 3, Rational(1, 2)])
    p3 = Rational(rng.choice([1, 1, 2]), rng.choice([4, 5, 6, 8]))
    if p3 <= 0 or p3 >= 1:
        return None
    reste = 1 - p3
    p2 = simplify(reste / (1 + k))
    p1 = simplify(k * p2)
    if p1 <= 0 or p2 <= 0:
        return None
    enonce = (
        f"Une variable aléatoire $X$ prend les valeurs ${values[0]}$, ${values[1]}$ et ${values[2]}$. "
        f"On sait que $P(X={values[2]}) = {latex(p3)}$ et que $P(X={values[0]}) = {latex(k)} \\times P(X={values[1]})$. "
        f"Déterminer $P(X={values[0]})$ et $P(X={values[1]})$."
    )
    answer = f"$P(X={values[0]}) = {latex(p1)}$, $P(X={values[1]}) = {latex(p2)}$"
    steps = [
        f"Étape 1 — La somme des probabilités vaut $1$, donc $P(X={values[0]}) + P(X={values[1]}) = 1 - {latex(p3)} = {latex(reste)}$.",
        f"Étape 2 — En notant $P(X={values[1]}) = p$, on a $P(X={values[0]}) = {latex(k)}p$, donc "
        f"$({latex(k)}+1)p = {latex(reste)}$, soit $p = {latex(p2)}$.",
        f"Étape 3 — $P(X={values[0]}) = {latex(k)} \\times {latex(p2)} = {latex(p1)}$.",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_VARIABLES}


def _gen_variance_comparaison(rng: random.Random) -> Optional[dict]:
    """Structure différente de _gen_variance : DEUX lois sont données, il
    faut calculer les deux variances et COMPARER (raisonnement de
    comparaison, pas seulement une application de formule isolée)."""
    valuesX, probsX = _loi_3_valeurs(rng)
    valuesY, probsY = _loi_3_valeurs(rng)
    ex = sum(v * p for v, p in zip(valuesX, probsX))
    vx = simplify(sum((v ** 2) * p for v, p in zip(valuesX, probsX)) - ex ** 2)
    ey = sum(v * p for v, p in zip(valuesY, probsY))
    vy = simplify(sum((v ** 2) * p for v, p in zip(valuesY, probsY)) - ey ** 2)
    if vx == vy:
        return None
    plus_dispersee = "X" if vx > vy else "Y"
    enonce = (
        f"Deux variables aléatoires suivent les lois : {_table_latex(valuesX, probsX)} pour $X$, et "
        f"{_table_latex(valuesY, probsY)} pour $Y$. Calculer $V(X)$ et $V(Y)$, puis dire laquelle des deux "
        f"variables est la plus dispersée."
    )
    answer = f"$V(X) = {latex(vx)}$, $V(Y) = {latex(vy)}$ : ${plus_dispersee}$ est la plus dispersée."
    steps = [
        f"Étape 1 — $V(X) = E(X^2) - E(X)^2 = {latex(vx)}$ (avec $E(X) = {latex(ex)}$).",
        f"Étape 2 — $V(Y) = E(Y^2) - E(Y)^2 = {latex(vy)}$ (avec $E(Y) = {latex(ey)}$).",
        f"Étape 3 — La variable ayant la plus grande variance est la plus dispersée : c'est ${plus_dispersee}$.",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_ESPERANCE}


_CONTEXTES_JEU_3 = [
    {"nom": "tirer une carte dans un jeu", "issue3": "carte neutre"},
    {"nom": "lancer une roue de loterie", "issue3": "case neutre"},
]


def _gen_jeu_trois_issues(rng: random.Random) -> Optional[dict]:
    """Structure différente de _gen_jeu_esperance : TROIS issues (gain,
    perte, nul) au lieu de deux — la somme de l'espérance comporte trois
    termes, pas deux."""
    ctx = rng.choice(_CONTEXTES_JEU_3)
    mise = rng.randint(2, 10)
    gain_grand = rng.randint(mise + 10, mise + 40)
    den = rng.choice([6, 8, 10, 12])
    p_gagner = Rational(rng.choice([1, 2]), den)
    p_neutre = Rational(rng.choice([1, 2, 3]), den)
    if p_gagner + p_neutre >= 1:
        return None
    p_perdre = 1 - p_gagner - p_neutre
    values = [gain_grand - mise, 0, -mise]
    probs = [p_gagner, p_neutre, p_perdre]
    esperance = sum(v * p for v, p in zip(values, probs))
    verdict = "favorable au joueur" if esperance > 0 else ("défavorable au joueur" if esperance < 0 else "équitable")
    enonce = (
        f"Pour {ctx['nom']}, la mise est de ${mise}$ €. Le joueur gagne ${gain_grand}$ € avec probabilité "
        f"${latex(p_gagner)}$, ne gagne ni ne perd rien ({ctx['issue3']}) avec probabilité ${latex(p_neutre)}$, "
        f"et perd sa mise sinon. Soit $X$ le gain algébrique. Déterminer la loi de $X$, calculer $E(X)$, "
        "et dire si le jeu est favorable, défavorable, ou équitable."
    )
    answer = f"$E(X) = {latex(esperance)}$ : le jeu est {verdict}."
    steps = [
        f"Étape 1 — Les trois issues possibles pour $X$ sont ${values[0]}$ (probabilité ${latex(p_gagner)}$), "
        f"${values[1]}$ (probabilité ${latex(p_neutre)}$) et ${values[2]}$ (probabilité ${latex(p_perdre)}$).",
        f"Étape 2 — $E(X) = {values[0]} \\times {latex(p_gagner)} + {values[1]} \\times {latex(p_neutre)} "
        f"+ ({values[2]}) \\times {latex(p_perdre)} = {latex(esperance)}$.",
        f"Étape 3 — {answer}",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_VARIABLES}


def _gen_jeu_equite(rng: random.Random) -> Optional[dict]:
    """Problème INVERSE : on impose l'équité (E(X)=0) et on demande de
    retrouver la mise — algèbre, pas un simple calcul d'espérance."""
    gain_grand = rng.randint(20, 100)
    den = rng.choice([4, 5, 8, 10])
    p_gagner = Rational(rng.choice([1, 2]), den)
    p_perdre = 1 - p_gagner
    # E(X) = (gain_grand - mise)*p_gagner - mise*p_perdre = 0  =>  mise = gain_grand * p_gagner
    mise = simplify(gain_grand * p_gagner)
    enonce = (
        f"Dans un jeu, le joueur gagne ${gain_grand}$ € avec probabilité ${latex(p_gagner)}$, et perd sa mise $m$ "
        f"sinon. Déterminer la valeur de la mise $m$ pour que le jeu soit équitable (c'est-à-dire $E(X)=0$)."
    )
    answer = f"$m = {latex(mise)}$ €"
    steps = [
        f"Étape 1 — Le gain algébrique vaut ${gain_grand}-m$ avec probabilité ${latex(p_gagner)}$, et $-m$ avec probabilité ${latex(p_perdre)}$.",
        f"Étape 2 — L'équité impose $E(X) = ({gain_grand}-m) \\times {latex(p_gagner)} + (-m) \\times {latex(p_perdre)} = 0$.",
        f"Étape 3 — En développant : ${gain_grand} \\times {latex(p_gagner)} - m = 0$, donc $m = {gain_grand} \\times {latex(p_gagner)} = {latex(mise)}$ €.",
    ]
    return {"enonce": enonce, "answer": answer, "steps": steps, "notion": NOTION_VARIABLES}


EXTRA_FAMILY_BASE_SCORE: dict[str, float] = {
    "completer_loi_systeme": 2.2,
    "esperance_effectifs": 1.8,
    "esperance_inverse": 2.6,
    "jeu_trois_issues": 3.4,
    "jeu_equite": 3.8,
    "variance_comparaison": 4.4,
}

EXTRA_FAMILIES: tuple[Family, ...] = (
    Family("esperance_effectifs", 2, "Espérance à partir d'effectifs", NOTION_ESPERANCE, _gen_esperance_effectifs,
           "une population décrite par effectifs plutôt que par probabilités",
           "convertir chaque effectif en probabilité avant d'appliquer E(X)=Σ x_i×P(X=x_i)"),
    Family("completer_loi_systeme", 3, "Compléter une loi via un système", NOTION_VARIABLES, _gen_completer_loi_systeme,
           "deux probabilités inconnues liées par une relation", "poser un système à partir de la somme=1 et de la relation donnée"),
    Family("esperance_inverse", 3, "Retrouver une valeur connaissant E(X)", NOTION_ESPERANCE, _gen_esperance_inverse,
           "une valeur de X inconnue et l'espérance donnée", "résoudre l'équation E(X)=x1p1+x2p2 d'inconnue x2"),
    Family("jeu_trois_issues", 4, "Jeu à trois issues", NOTION_VARIABLES, _gen_jeu_trois_issues,
           "un jeu à trois issues (gain, nul, perte)", "sommer les trois termes x_i×P(X=x_i)"),
    Family("jeu_equite", 4, "Retrouver la mise d'un jeu équitable", NOTION_VARIABLES, _gen_jeu_equite,
           "un jeu dont on impose l'équité E(X)=0", "poser E(X)=0 et résoudre en la mise m"),
    Family("variance_comparaison", 5, "Comparer la dispersion de deux lois", NOTION_ESPERANCE, _gen_variance_comparaison,
           "deux lois de probabilité à comparer", "calculer les deux variances puis comparer leurs valeurs"),
)

EXTRA_FAMILIES_BY_ID: dict[str, Family] = {f.id: f for f in EXTRA_FAMILIES}


def generate_extra_pool(per_family: int = 12, seed: int = 20260950) -> list[dict]:
    """Pool de diversification structurelle (mission 2026-09-02) — jamais
    mélangé à generate_pool()/FAMILIES (qui restent figés à l'identique pour
    préserver bit pour bit le pool historique). IDs à partir de
    GENERATED_ID_OFFSET + 8000, bloc dédié et jamais utilisé par la baseline
    ni par une extension quantitative antérieure."""
    rng = random.Random(seed)
    per_family_pool: dict[str, list[dict]] = {}
    for family in EXTRA_FAMILIES:
        seen_signatures = set()
        items = []
        attempts = 0
        while len(items) < per_family and attempts < per_family * 60:
            attempts += 1
            ex = _build_extra_exercise(family, rng)
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
        family = EXTRA_FAMILIES[idx % len(EXTRA_FAMILIES)]
        bucket = per_family_pool.get(family.id) or []
        if bucket:
            pool.append(bucket.pop(0))
        idx += 1
        if idx > 200000:
            break
    offset = GENERATED_ID_OFFSET + 8000
    for i, ex in enumerate(pool):
        ex["id"] = offset + i
    return pool


def _build_extra_exercise(family: Family, rng: random.Random) -> Optional[dict]:
    notes = family.generate(rng)
    if notes is None:
        return None
    score = EXTRA_FAMILY_BASE_SCORE[family.id]
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


FAMILY_BASE_SCORE: dict[str, float] = {
    "completer_loi": 1.0,
    "esperance": 1.6,
    "transformation_affine": 2.4,
    "jeu_esperance": 3.2,
    "variance": 4.0,
}

FAMILIES: tuple[Family, ...] = (
    Family("completer_loi", 1, "Compléter une loi de probabilité", NOTION_VARIABLES, _gen_completer_loi,
           "une loi de probabilité avec une valeur manquante", "la somme des probabilités vaut 1"),
    Family("esperance", 2, "Calcul de l'espérance", NOTION_ESPERANCE, _gen_esperance,
           "une loi de probabilité complète", "E(X) = Σ x_i × P(X=x_i)"),
    Family("transformation_affine", 2, "Transformation affine E(aX+b), V(aX+b)", NOTION_ESPERANCE,
           _gen_transformation_affine, "E(X) et V(X) connues, Y=aX+b",
           "E(aX+b)=aE(X)+b et V(aX+b)=a²V(X)"),
    Family("jeu_esperance", 3, "Jeu contextualisé : gain espéré", NOTION_VARIABLES, _gen_jeu_esperance,
           "un jeu avec mise et gain conditionnel", "calculer E(X) puis comparer son signe à 0"),
    Family("variance", 4, "Variance et écart-type", NOTION_ESPERANCE, _gen_variance,
           "une loi de probabilité complète", "V(X)=E(X²)-E(X)², puis σ(X)=√V(X)"),
)

FAMILIES_BY_ID: dict[str, Family] = {f.id: f for f in FAMILIES}


def _difficulty_bucket_from_score(score: float) -> int:
    if score <= 1.3:
        return 1
    if score <= 2.0:
        return 2
    if score <= 2.8:
        return 3
    if score <= 3.6:
        return 4
    return 5


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


def generate_pool(per_family: int = 12, seed: int = 20260905) -> list[dict]:
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
