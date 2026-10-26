"""Génération d'exercices d'automatismes (Première, Chapitre_13, programme
2026 : évolutions et variations ; calcul numérique et algébrique ; fonctions
et représentations ; statistiques et probabilités — entretien des
automatismes de Seconde et de Première, activité mentale privilégiée).

Garantie de correction : tous les calculs sont faits en fractions exactes
(fractions.Fraction) ou par SymPy, puis écrits ; un tirage dont la réponse
ne serait pas exacte au format annoncé est rejeté.

Même contrat que les autres modules du programme 2026 (identifiants stables
par famille : GENERATED_ID_OFFSET + 1000 × rang + k).
"""
import random
from dataclasses import dataclass
from fractions import Fraction as F
from statistics import median
from typing import Callable, Optional

import sympy as sp

CHAPTER_ID = "Chapitre_13"
N1 = "Évolutions et taux"
N2 = "Calcul numérique et algébrique"
N3 = "Fonctions et représentations"
N4 = "Statistiques et probabilités"

GENERATED_ID_OFFSET = 1_180_000

LEVEL_META = {
    1: {"emoji": "🟢", "label": "Niveau 1 — Fondamental"},
    2: {"emoji": "🟡", "label": "Niveau 2 — Intermédiaire"},
    3: {"emoji": "🟠", "label": "Niveau 3 — Avancé"},
    4: {"emoji": "🔴", "label": "Niveau 4 — Difficile"},
}
X = sp.Symbol("x")


def dec(q, nd=None) -> str:
    """Nombre à la française en mode maths (virgule {,}) ; nd : arrondi."""
    q = F(q)
    if nd is None:
        if q.denominator == 1:
            return str(q.numerator)
        v = f"{float(q):.6f}".rstrip("0").rstrip(".")
    else:
        v = f"{float(q):.{nd}f}"
    return v.replace(".", "{,}")


def frac(q) -> str:
    q = F(q)
    if q.denominator == 1:
        return str(q.numerator)
    s = "-" if q < 0 else ""
    return f"{s}\\dfrac{{{abs(q.numerator)}}}{{{q.denominator}}}"


def _decimal_exact(q, max_digits=4) -> bool:
    q = F(q)
    return (q * 10 ** max_digits).denominator == 1


def _moins(a, b) -> str:
    """« a - b » sans « - (-3) » ni « - (1) »."""
    return f"{a} - {b}" if b >= 0 else f"{a} + {-b}"


def _egal(q_brut: str, q) -> str:
    """« = valeur » seulement si l'écriture change."""
    v = frac(q)
    return "" if v == q_brut else f" = {v}"


def _pct(t) -> str:
    return f"{dec(abs(t) * 100)}\\,\\%"


# ── Notion 1 — évolutions ────────────────────────────────────────────────────

def _gen_appliquer_taux(rng):
    v = rng.choice([40, 50, 80, 120, 150, 200, 250, 320, 400, 640, 800, 1200])
    t = F(rng.choice([-30, -25, -20, -15, -10, -5, 5, 10, 12, 15, 20, 25, 40]), 100)
    vf = v * (1 + t)
    if not _decimal_exact(vf, 2):
        return None
    sens = "hausse" if t > 0 else "baisse"
    return dict(enonce=f"Un prix de ${v}$ € subit une {sens} de ${_pct(t)}$. Quel est le nouveau prix ?",
                answer=f"Le nouveau prix est ${dec(vf)}$ €.",
                hint="Multiplie par le coefficient multiplicateur 1 + t.",
                steps=[f"Coefficient multiplicateur : $1 {'+' if t > 0 else '-'} {dec(abs(t))} = {dec(1 + t)}$.", f"${v} \\times {dec(1 + t)} = {dec(vf)}$."])


def _gen_valeur_initiale(rng):
    t = F(rng.choice([-25, -20, -10, 10, 20, 25, 50]), 100)
    v0 = rng.choice([40, 60, 80, 100, 120, 160, 200, 240, 300, 400])
    vf = v0 * (1 + t)
    sens = "augmenté" if t > 0 else "diminué"
    return dict(enonce=f"Après avoir {sens} de ${_pct(t)}$, une quantité vaut ${dec(vf)}$. Quelle était sa valeur initiale ?",
                answer=f"La valeur initiale était ${dec(v0)}$.",
                hint="On divise par le coefficient multiplicateur.",
                steps=[f"Coefficient multiplicateur : ${dec(1 + t)}$.", f"$V_0 = \\dfrac{{{dec(vf)}}}{{{dec(1 + t)}}} = {dec(v0)}$."])


def _gen_calculer_taux(rng):
    v0 = rng.choice([20, 25, 40, 50, 80, 125, 200, 250, 400, 500])
    t = F(rng.randint(-60, 80), 100)
    if t == 0:
        return None
    v1 = v0 * (1 + t)
    if not _decimal_exact(v1, 2):
        return None
    return dict(enonce=f"Une grandeur passe de ${v0}$ à ${dec(v1)}$. Calculer le taux d'évolution en pourcentage.",
                answer=f"Le taux d'évolution est ${'+' if t > 0 else '-'}{_pct(t)}$.",
                hint="Taux = (valeur finale − valeur initiale) / valeur initiale.",
                steps=[f"$t = \\dfrac{{{dec(v1)} - {v0}}}{{{v0}}} = \\dfrac{{{dec(v1 - v0)}}}{{{v0}}} = {dec(t)}$.", f"Soit ${'+' if t > 0 else '-'}{_pct(t)}$."])


def _gen_evolutions_successives(rng):
    t1 = F(rng.choice([-20, -10, -5, 5, 10, 20, 30, 50]), 100)
    t2 = F(rng.choice([-30, -20, -10, -5, 5, 10, 20, 25]), 100)
    g = (1 + t1) * (1 + t2) - 1
    def mot(t):
        return f"une hausse de ${_pct(t)}$" if t > 0 else f"une baisse de ${_pct(t)}$"
    glob = "aucune évolution" if g == 0 else (f"une hausse de ${_pct(g)}$" if g > 0 else f"une baisse de ${_pct(g)}$")
    return dict(enonce=f"Une quantité subit {mot(t1)}, puis {mot(t2)}. Quel est le taux d'évolution global ?",
                answer=f"Globalement, c'est {glob}.",
                hint="On multiplie les coefficients multiplicateurs (on n'additionne pas les taux).",
                steps=[f"Coefficients : ${dec(1 + t1)}$ et ${dec(1 + t2)}$.", f"Coefficient global : ${dec(1 + t1)} \\times {dec(1 + t2)} = {dec((1 + t1) * (1 + t2))}$.",
                       f"Taux global : ${dec(g)}$, soit {glob}."])


def _gen_taux_reciproque(rng):
    t = F(rng.choice([v for v in range(-60, 155, 5) if v != 0]), 100)
    objet = rng.choice(["Un prix", "Une population", "Une production", "Un chiffre d'affaires"])
    r = 1 / (1 + t) - 1
    exact = _decimal_exact(r * 100, 2)
    val = f"{'+' if r > 0 else '-'}{_pct(r)}" if exact else f"{'+' if r > 0 else '-'}{dec(abs(r) * 100, 2)}\\,\\%"
    approx = "" if exact else " (arrondi au centième)"
    return dict(enonce=f"{objet} a subi une évolution de ${'+' if t > 0 else '-'}{_pct(t)}$. Quelle évolution faut-il lui appliquer pour revenir à sa valeur initiale ?",
                answer=f"Le taux réciproque est ${val}${approx}.",
                hint="Le coefficient réciproque est l'inverse du coefficient multiplicateur.",
                steps=[f"Coefficient : ${dec(1 + t)}$ ; coefficient réciproque : $\\dfrac{{1}}{{{dec(1 + t)}}} = {frac(1 / (1 + t))}$.",
                       f"Taux réciproque : ${frac(1 / (1 + t))} - 1 = {frac(r)}$, soit ${val}${approx}."])


# ── Notion 2 — calcul ────────────────────────────────────────────────────────

def _gen_produit_nul(rng):
    a, b, c, d = rng.randint(1, 5), rng.randint(-9, 9), rng.randint(1, 5), rng.randint(-9, 9)
    e = (a * X + b) * (c * X + d)
    s1, s2 = F(-b, a), F(-d, c)
    if s1 == s2:
        return None
    sols = sorted({s1, s2})
    return dict(enonce=f"Résoudre l'équation $({sp.latex(a * X + b)})({sp.latex(c * X + d)}) = 0$.",
                answer=f"$\\mathcal{{S}} = \\left\\{{{frac(sols[0])} ; {frac(sols[1])}\\right\\}}$.",
                hint="Un produit est nul si et seulement si l'un des facteurs est nul.",
                steps=[f"${sp.latex(a * X + b)} = 0 \\iff x = {frac(s1)}$.", f"${sp.latex(c * X + d)} = 0 \\iff x = {frac(s2)}$."],
                _check=set(sp.solve(e, X)) == {sp.Rational(s.numerator, s.denominator) for s in sols})


def _gen_signe_affine(rng):
    a, b = rng.choice([-5, -4, -3, -2, -1, 1, 2, 3, 4, 5]), rng.randint(-12, 12)
    r = F(-b, a)
    pos = f"x > {frac(r)}" if a > 0 else f"x < {frac(r)}"
    neg = f"x < {frac(r)}" if a > 0 else f"x > {frac(r)}"
    return dict(enonce=f"Étudier le signe de ${sp.latex(a * X + b)}$ selon les valeurs de $x$.",
                answer=f"${sp.latex(a * X + b)}$ s'annule en ${frac(r)}$, est positif pour ${pos}$ et négatif pour ${neg}$.",
                hint="Une fonction affine ax + b a le signe de a à droite de sa racine.",
                steps=[f"Racine : ${sp.latex(a * X + b)} = 0 \\iff x = {frac(r)}$.", f"Coefficient directeur ${a}$ {'positif' if a > 0 else 'négatif'} : signe de $a$ à droite de la racine.",
                       f"Positif pour ${pos}$, négatif pour ${neg}$."])


def _gen_developper(rng):
    a, b, c, d = rng.randint(1, 5), rng.randint(-7, 7), rng.randint(-4, 5), rng.randint(-7, 7)
    if c == 0 or b == 0 or d == 0:
        return None
    g = (a * X + b) * (c * X + d)
    return dict(enonce=f"Développer et réduire $({sp.latex(a * X + b)})({sp.latex(c * X + d)})$.",
                answer=f"$({sp.latex(a * X + b)})({sp.latex(c * X + d)}) = {sp.latex(sp.expand(g))}$.",
                hint="Double distributivité : chaque terme du premier facteur multiplie chaque terme du second.",
                steps=[f"$= {_par(a * X)} \\times {_par(c * X)} + {_par(a * X)} \\times {_par(d)} + {_par(b)} \\times {_par(c * X)} + {_par(b)} \\times {_par(d)}$.",
                       f"$= {sp.latex(sp.expand(g))}$."])


def _par(e) -> str:
    """Facteur d'un produit : entre parenthèses s'il commence par « - »."""
    s = sp.latex(e)
    return f"({s})" if s.startswith("-") else s


def _gen_factoriser(rng):
    a = rng.randint(1, 9)
    kind = rng.choice(["diff", "carre_plus", "carre_moins", "facteur"])
    if kind == "diff":
        e, f = X ** 2 - a * a, f"(x - {a})(x + {a})"
        how = "identité $a^2 - b^2 = (a - b)(a + b)$"
    elif kind == "carre_plus":
        e, f = X ** 2 + 2 * a * X + a * a, f"(x + {a})^2"
        how = "identité $a^2 + 2ab + b^2 = (a + b)^2$"
    elif kind == "carre_moins":
        e, f = X ** 2 - 2 * a * X + a * a, f"(x - {a})^2"
        how = "identité $a^2 - 2ab + b^2 = (a - b)^2$"
    else:
        k = rng.randint(2, 7)
        e, f = k * X ** 2 + k * a * X, f"{k}x(x + {a})"
        how = f"facteur commun ${k}x$"
    assert sp.expand(sp.sympify(f.replace("^", "**").replace(")(", ")*(").replace("x(", "x*(").replace(f"{f[0]}x", f"{f[0]}*x") if kind == "facteur" else f.replace("^", "**").replace(")(", ")*(")) - e) == 0
    return dict(enonce=f"Factoriser ${sp.latex(e)}$.",
                answer=f"${sp.latex(e)} = {f}$.",
                hint="Cherche un facteur commun ou une identité remarquable.",
                steps=[f"On reconnaît : {how}.", f"${sp.latex(e)} = {f}$."])


# ── Notion 3 — fonctions ─────────────────────────────────────────────────────

def _gen_droite(rng):
    x1, y1 = rng.randint(-5, 5), rng.randint(-6, 6)
    x2 = x1 + rng.choice([-4, -3, -2, -1, 1, 2, 3, 4])
    y2 = rng.randint(-6, 6)
    m = F(y2 - y1, x2 - x1)
    p = y1 - m * x1
    eq = sp.latex(sp.Rational(m.numerator, m.denominator) * X + sp.Rational(p.numerator, p.denominator))
    return dict(enonce=f"Déterminer l'équation réduite de la droite passant par $A({x1} ; {y1})$ et $B({x2} ; {y2})$.",
                answer=f"$y = {eq.replace('frac', 'dfrac')}$.",
                hint="Coefficient directeur m = (yB − yA)/(xB − xA), puis p avec un point.",
                steps=[f"$m = \\dfrac{{{_moins(y2, y1)}}}{{{_moins(x2, x1)}}} = {frac(m)}$.", f"$p = y_A - m x_A = {frac(p)}$.", f"$y = {eq.replace('frac', 'dfrac')}$."])


def _gen_image_antecedent(rng):
    c, k = rng.randint(1, 9), rng.randint(-5, 5)
    t = rng.randint(1, 6)
    val = t * t - c
    return dict(enonce=f"Soit $f(x) = x^2 - {c}$. Calculer l'image de ${k}$, puis déterminer les antécédents de ${val}$.",
                answer=f"$f({k}) = {k * k - c}$ ; les antécédents de ${val}$ sont ${-t}$ et ${t}$.",
                hint="Image : on remplace x ; antécédents : on résout f(x) = valeur.",
                steps=[f"$f({k}) = ({k})^2 - {c} = {k * k - c}$.", f"$x^2 - {c} = {val} \\iff x^2 = {t * t} \\iff x = {t}$ ou $x = {-t}$."])


def _gen_lecture_variations(rng):
    a = rng.randint(-5, -1)
    b = a + rng.randint(2, 4)
    c = b + rng.randint(2, 4)
    m1, M, m2 = rng.randint(-6, -1), rng.randint(2, 8), rng.randint(-4, 1)
    k = rng.randint(m1 + 1, M - 1)
    n = (1 if m1 <= k <= M else 0) + (1 if m2 <= k < M else 0)
    if k == M:
        return None
    return dict(enonce=f"Une fonction $f$ est croissante sur $[{a} ; {b}]$, de $f({a}) = {m1}$ à $f({b}) = {M}$, puis décroissante sur $[{b} ; {c}]$ jusqu'à $f({c}) = {m2}$. Combien l'équation $f(x) = {k}$ a-t-elle de solutions sur $[{a} ; {c}]$ ?",
                answer=f"Elle a ${n}$ solution{'s' if n > 1 else ''}.",
                hint="Sur chaque intervalle de monotonie, f prend une fois exactement chaque valeur comprise entre ses valeurs extrêmes.",
                steps=[f"Sur $[{a} ; {b}]$, $f$ prend toutes les valeurs de ${m1}$ à ${M}$ : ${k}$ {'est' if m1 <= k <= M else 'n’est pas'} atteint, une fois au plus.",
                       f"Sur $[{b} ; {c}]$, $f$ prend les valeurs de ${M}$ à ${m2}$ (sans compter ${M}$, déjà atteint en ${b}$) : ${k}$ {'est' if m2 <= k < M else 'n’est pas'} atteint.",
                       f"Total : ${n}$ solution{'s' if n > 1 else ''}."])


# ── Notion 4 — statistiques et probabilités ──────────────────────────────────

def _gen_statistiques(rng):
    n = rng.choice([5, 6, 7, 8])
    L = sorted(rng.randint(2, 20) for _ in range(n))
    moy = F(sum(L), n)
    med = F(median(L)).limit_denominator(2)
    return dict(enonce=f"On considère la série : ${' ; '.join(map(str, L))}$. Calculer la moyenne, la médiane et l'étendue.",
                answer=f"Moyenne $\\overline{{x}} = {frac(moy) if not _decimal_exact(moy, 2) else dec(moy)}$, médiane ${dec(med)}$, étendue ${L[-1] - L[0]}$.",
                hint="La série est déjà rangée par ordre croissant.",
                steps=[f"Somme : ${sum(L)}$ ; effectif ${n}$ : $\\overline{{x}} = \\dfrac{{{sum(L)}}}{{{n}}}$.",
                       f"Médiane : {'valeur centrale' if n % 2 else 'moyenne des deux valeurs centrales'}, ${dec(med)}$.", f"Étendue : ${L[-1]} - {L[0]} = {L[-1] - L[0]}$."])


def _gen_tableau_croise(rng):
    a, b, c, d = (rng.randint(5, 60) for _ in range(4))
    tot = a + b + c + d
    pB = F(a + c, tot)
    pAB = F(a, a + c)
    return dict(enonce=(f"Dans un club, ${a}$ adhérents sont des filles qui font du tennis, ${b}$ des filles qui n'en font pas, "
                        f"${c}$ des garçons qui font du tennis et ${d}$ des garçons qui n'en font pas. On choisit un adhérent au hasard. "
                        "Calculer la probabilité qu'il fasse du tennis, puis la proportion de filles parmi les joueurs de tennis."),
                answer=f"$P(T) = {frac(pB)}$ ; parmi les joueurs de tennis, la proportion de filles est ${frac(pAB)}$.",
                hint="Dresse le tableau croisé avec les totaux.",
                steps=[f"Effectif total : ${tot}$ ; joueurs de tennis : ${a} + {c} = {a + c}$.", f"$P(T) = \\dfrac{{{a + c}}}{{{tot}}}{_egal(f'\\dfrac{{{a + c}}}{{{tot}}}', pB)}$.",
                       f"Parmi les ${a + c}$ joueurs : $\\dfrac{{{a}}}{{{a + c}}}{_egal(f'\\dfrac{{{a}}}{{{a + c}}}', pAB)}$."])


@dataclass(frozen=True)
class Family:
    id: str
    level: int
    label: str
    generate: Callable[[random.Random], Optional[dict]]
    notion: str
    score: float


FAMILIES: tuple[Family, ...] = (
    Family("appliquer_taux", 1, "Appliquer un taux d'évolution", _gen_appliquer_taux, N1, 1.2),
    Family("valeur_initiale", 2, "Retrouver une valeur initiale", _gen_valeur_initiale, N1, 2.0),
    Family("calculer_taux", 1, "Calculer un taux d'évolution", _gen_calculer_taux, N1, 1.5),
    Family("evolutions_successives", 2, "Évolutions successives", _gen_evolutions_successives, N1, 2.4),
    Family("taux_reciproque", 3, "Taux réciproque", _gen_taux_reciproque, N1, 3.0),
    Family("produit_nul", 1, "Équation produit nul", _gen_produit_nul, N2, 1.4),
    Family("signe_affine", 2, "Signe d'une expression du premier degré", _gen_signe_affine, N2, 2.1),
    Family("developper", 2, "Développer et réduire", _gen_developper, N2, 2.2),
    Family("factoriser", 2, "Factoriser", _gen_factoriser, N2, 2.6),
    Family("droite", 2, "Équation réduite d'une droite", _gen_droite, N3, 2.5),
    Family("image_antecedent", 1, "Image et antécédents", _gen_image_antecedent, N3, 1.3),
    Family("lecture_variations", 3, "Nombre de solutions d'après les variations", _gen_lecture_variations, N3, 3.3),
    Family("statistiques", 1, "Moyenne, médiane, étendue", _gen_statistiques, N4, 1.4),
    Family("tableau_croise", 2, "Tableau croisé et probabilités", _gen_tableau_croise, N4, 2.3),
)
FAMILIES_BY_ID = {f.id: f for f in FAMILIES}


def _level_from_score(score: float) -> int:
    return 1 if score <= 1.5 else 2 if score <= 2.7 else 3 if score <= 3.8 else 4


def build_exercise(family: Family, rng: random.Random) -> Optional[dict]:
    notes = family.generate(rng)
    if notes is None or not notes.pop("_check", True):
        return None
    level = _level_from_score(family.score)
    assert level == family.level, family.id
    steps = [f"Étape {k} — {s}" for k, s in enumerate(notes["steps"], 1)]
    return {"enonce": notes["enonce"], "answer": notes["answer"], "hint": notes["hint"], "solution_steps": steps,
            "chapter_id": CHAPTER_ID, "notion": family.notion, "difficulty": level,
            "difficulty_label": LEVEL_META[level]["label"], "difficulty_emoji": LEVEL_META[level]["emoji"],
            "family": family.id, "family_label": family.label, "declared_level": family.level,
            "complexity_score": family.score, "source": "generated"}


def generate_one(family_id: str, seed: Optional[int] = None, max_attempts: int = 80) -> dict:
    rng = random.Random(seed)
    fam = FAMILIES_BY_ID[family_id]
    for _ in range(max_attempts):
        ex = build_exercise(fam, rng)
        if ex is not None:
            return ex
    raise RuntimeError(f"Impossible de générer un exercice valide pour la famille {family_id!r}")


def generate_pool(per_family: int = 32, seed: int = 20261029) -> list[dict]:
    pool: list[dict] = []
    for rank, family in enumerate(FAMILIES):
        rng = random.Random(seed * 100 + rank)
        seen, items, attempts = set(), [], 0
        while len(items) < per_family and attempts < per_family * 100:
            attempts += 1
            ex = build_exercise(family, rng)
            if ex is None or ex["enonce"] in seen:
                continue
            seen.add(ex["enonce"])
            items.append(ex)
        for k, ex in enumerate(items):
            ex["id"] = GENERATED_ID_OFFSET + 1000 * rank + k
        pool.extend(items)
    return pool
