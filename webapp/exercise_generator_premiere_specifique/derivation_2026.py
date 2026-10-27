"""Génération symbolique d'exercices de dérivation (Première, Chapitre_3) pour
les capacités du programme 2026 peu ou pas couvertes par derivatives.py et
tangente.py : approximation affine, coût marginal, vitesse instantanée,
tangentes de pente imposée, tangentes passant par un point, puissances
d'exposant négatif, règle de l'inverse, produit avec la racine carrée.

Même contrat que second_degre_formes.py (une notion par famille, identifiants
stables par famille). Chaque valeur annoncée est recalculée et contrôlée par
SymPy au moment du tirage : un désaccord rejette le tirage.
"""
import random
from dataclasses import dataclass
from fractions import Fraction as Fr
from typing import Callable, Optional

import sympy as sp

from exercise_generator_premiere_specifique._tex import parse as parse_tex
from exercise_generator_premiere_specifique.second_degre_formes import fr, lead, lin, pw, tri


def _approx_txt(q) -> str:
    """Valeur exacte si c'est un décimal d'au plus 6 décimales, sinon arrondie à 10^-4."""
    q = Fr(q)
    if (q * 10**6).denominator == 1:
        return dec(q)
    return dec(q, 4)


def _tan(m, x0, y0) -> str:
    """m(x - x0) + y0 écrit proprement."""
    if m == 0:
        return fr(y0)
    fac = "x" if x0 == 0 else f"({lin(x0)})"
    return f"{lead(m)}{fac}{_cst(y0)}"


def _cst(c) -> str:
    """Terme constant ajouté : « + 4 », « - 2 », rien si nul."""
    return "" if c == 0 else (f" + {fr(c)}" if c > 0 else f" - {fr(-c)}")

x = sp.symbols("x")

CHAPTER_ID = "Chapitre_3"
NOTION = "Fonction dérivée"
N1 = "Nombre dérivé. Tangente"
N2 = "Approximation affine et dérivabilité"
N3 = "Fonction dérivée"
N4 = "Opérations et dérivation"

GENERATED_ID_OFFSET = 1_120_000

LEVEL_META = {
    1: {"emoji": "🟢", "label": "Niveau 1 — Fondamental"},
    2: {"emoji": "🟡", "label": "Niveau 2 — Intermédiaire"},
    3: {"emoji": "🟠", "label": "Niveau 3 — Avancé"},
    4: {"emoji": "🔴", "label": "Niveau 4 — Difficile"},
}


def dec(q, digits=None) -> str:
    """Décimal à la française ; `digits` : arrondi."""
    v = float(q)
    s = f"{v:.{digits}f}" if digits is not None else f"{v:.10f}".rstrip("0").rstrip(".")
    return s.replace(".", "{,}")


def _S(e):
    q = Fr(e)
    return sp.Rational(q.numerator, q.denominator)


def _eq_line(m, p) -> str:
    """y = mx + p proprement."""
    return tri(0, m, p) if (m or p) else "0"


# ── Notion 1 — tangentes ─────────────────────────────────────────────────────


def _gen_tangente_horizontale(rng):
    a = rng.choice([1, -1, 2, -2, 3])
    x0 = rng.randint(-5, 5)
    b = -2 * a * x0
    c = rng.randint(-8, 8)
    y0 = a * x0 * x0 + b * x0 + c
    f = a * x**2 + b * x + c
    return {"notion": N1,
            "enonce": f"Soit $f(x) = {tri(a, b, c)}$. En quel point la courbe de $f$ admet-elle une tangente horizontale ?",
            "answer": f"Au point $({x0} ; {y0})$.",
            "steps": [f"Étape 1 — $f'(x) = {tri(0, 2 * a, b)}$.", f"Étape 2 — Tangente horizontale : $f'(x) = 0 \\iff x = {x0}$.",
                      f"Étape 3 — $f({x0}) = {y0}$."],
            "hint": "Une tangente horizontale a une pente nulle : résous $f'(x) = 0$.",
            "check": sp.solve(sp.diff(f, x), x) == [x0] and f.subs(x, x0) == y0}


def _gen_lire_pente(rng):
    x0 = rng.randint(-4, 4)
    m = rng.choice([-3, -2, -1, 1, 2, 3, Fr(1, 2), Fr(-1, 2)])
    y0 = rng.randint(-4, 4)
    d = rng.choice([2, 4])
    x1, y1 = x0 + d, y0 + m * d
    p = y0 - m * x0
    return {"notion": N1,
            "enonce": f"La tangente à la courbe d'une fonction $f$ au point d'abscisse ${x0}$ passe par les points $({x0} ; {y0})$ et $({x1} ; {fr(y1)})$. "
                      f"Déterminer $f({x0})$, $f'({x0})$ et une équation de cette tangente.",
            "answer": f"$f({x0}) = {y0}$, $f'({x0}) = {fr(m)}$ et la tangente a pour équation $y = {_eq_line(m, p)}$.",
            "steps": [f"Étape 1 — Le point de contact est $({x0} ; {y0})$ : $f({x0}) = {y0}$.",
                      f"Étape 2 — Pente : $\\dfrac{{{fr(y1)} - {pw(y0)}}}{{{x1} - {pw(x0)}}} = {fr(m)}$, donc $f'({x0}) = {fr(m)}$.",
                      f"Étape 3 — $y = {_tan(m, x0, y0)}$, soit $y = {_eq_line(m, p)}$."],
            "hint": "Le nombre dérivé est le coefficient directeur de la tangente.",
            "check": (y1 - y0) / (x1 - x0) == m}


def _gen_tangente_parallele(rng):
    b, c = rng.randint(-6, 6), rng.randint(-6, 6)
    x0 = rng.randint(-4, 4)
    m = 2 * x0 + b
    y0 = x0 * x0 + b * x0 + c
    p = y0 - m * x0
    q = rng.randint(-5, 5)
    if q == p:
        return None
    f = x**2 + b * x + c
    return {"notion": N1,
            "enonce": f"Soit $f(x) = {tri(1, b, c)}$. Déterminer le point de la courbe où la tangente est parallèle à la droite d'équation $y = {_eq_line(m, q)}$, "
                      f"puis une équation de cette tangente.",
            "answer": f"Au point $({x0} ; {y0})$ ; tangente : $y = {_eq_line(m, p)}$.",
            "steps": [f"Étape 1 — Deux droites parallèles ont le même coefficient directeur : on cherche $a$ tel que $f'(a) = {m}$.",
                      f"Étape 2 — $f'(a) = 2a {'+' if b >= 0 else '-'} {abs(b)} = {m}$, donc $a = {x0}$ et $f({x0}) = {y0}$.",
                      f"Étape 3 — $y = {_tan(m, x0, y0)}$, soit $y = {_eq_line(m, p)}$."],
            "hint": "Traduis « parallèle » par « même coefficient directeur ».",
            "check": sp.solve(sp.diff(f, x) - m, x) == [x0] and sp.expand(sp.diff(f, x).subs(x, x0) * (x - x0) + y0) == m * x + p}


def _gen_tangentes_par_un_point(rng):
    r1, r2 = rng.sample(range(-4, 5), 2)
    # tangentes à y = x² en a passant par P : a² - 2·xP·a + yP = 0, de racines r1, r2
    xp = Fr(r1 + r2, 2)
    yp = r1 * r2
    if xp.denominator != 1:
        return None
    xp = int(xp)
    lines = [(2 * r, -r * r) for r in sorted((r1, r2))]
    return {"notion": N1,
            "enonce": f"Déterminer les tangentes à la parabole d'équation $y = x^2$ qui passent par le point $P({xp} ; {yp})$.",
            "answer": "Deux tangentes : " + " et ".join(f"$y = {_eq_line(m, p)}$" for m, p in lines) + ".",
            "steps": ["Étape 1 — Tangente au point d'abscisse $a$ : $y = 2a(x - a) + a^2 = 2ax - a^2$.",
                      f"Étape 2 — Elle passe par $P$ si ${yp} = {2 * xp}a - a^2$, soit ${tri(1, -2 * xp, yp, 'a')} = 0$.",
                      f"Étape 3 — Racines $a = {min(r1, r2)}$ et $a = {max(r1, r2)}$ : " + " ; ".join(f"$y = {_eq_line(m, p)}$" for m, p in lines) + "."],
            "hint": "Écris la tangente en un point d'abscisse inconnue $a$, puis impose qu'elle passe par $P$.",
            "check": all(m * xp + p == yp for m, p in lines) and r1 != r2}


# ── Notion 2 — approximation affine ─────────────────────────────────────────

_FUNCS = (
    ("x^2", lambda a: a * a, lambda a: 2 * a, (1, 2, 3, 5, 10)),
    ("x^3", lambda a: a ** 3, lambda a: 3 * a * a, (1, 2, 3)),
    ("\\sqrt{x}", lambda a: int(a ** 0.5), lambda a: Fr(1, 2 * int(a ** 0.5)), (1, 4, 9, 16, 25)),
    ("\\dfrac{1}{x}", lambda a: Fr(1, a), lambda a: Fr(-1, a * a), (1, 2, 4, 5, 10)),
)


def _gen_approx_affine(rng):
    name, f, df, points = rng.choice(_FUNCS)
    a = rng.choice(points)
    h = rng.choice([Fr(1, 100), Fr(2, 100), Fr(5, 100), Fr(-1, 100), Fr(1, 10)])
    fa, dfa = Fr(f(a)), Fr(df(a))
    approx = fa + dfa * h
    exact = {"x^2": lambda t: t * t, "x^3": lambda t: t ** 3, "\\sqrt{x}": lambda t: t ** 0.5, "\\dfrac{1}{x}": lambda t: 1 / t}[name](float(a + h))
    if abs(float(approx) - exact) > 0.05 * abs(exact):
        return None
    xv = dec(a + h)
    return {"notion": N2,
            "enonce": f"Soit $f(x) = {name.replace('x', 'x')}$. À l'aide de l'approximation affine de $f$ en $a = {a}$, donner une valeur approchée de $f({xv})$.",
            "answer": f"$f({xv}) \\approx {_approx_txt(approx)}$ (calculatrice : ${dec(exact, 5)}$).",
            "steps": [f"Étape 1 — $f({a}) = {fr(fa)}$ et $f'({a}) = {fr(dfa)}$.",
                      f"Étape 2 — $f(a + h) \\approx f(a) + f'(a)h$ avec $h = {dec(h)}$.",
                      f"Étape 3 — $f({xv}) \\approx {fr(fa)} + {pw(dfa)} \\times {('(' + dec(h) + ')') if h < 0 else dec(h)} \\approx {_approx_txt(approx)}$."],
            "hint": "Approximation affine : $f(a + h) \\approx f(a) + f'(a)h$ pour $h$ proche de $0$.",
            "check": abs(float(approx) - exact) < 0.05 * abs(exact)}


def _gen_cout_marginal(rng):
    k = rng.choice([Fr(1, 10), Fr(1, 5), Fr(1, 2), Fr(1, 4)])
    b = rng.randint(2, 20)
    c = rng.choice([50, 100, 200, 500])
    q = rng.choice([10, 20, 30, 40, 50, 60])
    cm = 2 * k * q + b
    real = k * ((q + 1) ** 2 - q * q) + b
    return {"notion": N2,
            "enonce": f"Le coût de fabrication de $q$ objets est $C(q) = {tri(k, b, c, 'q')}$ euros. Calculer le coût marginal $C'({q})$ et le comparer "
                      f"au coût réel du ${q + 1}$e objet, $C({q + 1}) - C({q})$.",
            "answer": f"$C'({q}) = {dec(cm)}$ € et $C({q + 1}) - C({q}) = {dec(real)}$ € : le coût marginal en est une bonne approximation.",
            "steps": [f"Étape 1 — $C'(q) = {tri(0, 2 * k, b, 'q')}$, donc $C'({q}) = {dec(cm)}$.",
                      f"Étape 2 — $C({q + 1}) - C({q}) = {fr(k)} \\times ({(q + 1) ** 2} - {q * q}) + {b} = {dec(real)}$.",
                      "Étape 3 — C'est l'approximation affine avec $h = 1$ : $C(q + 1) - C(q) \\approx C'(q)$."],
            "hint": "Le coût marginal est le nombre dérivé du coût.",
            "check": abs(real - cm) == k}


def _gen_vitesse(rng):
    k = rng.choice([2, 3, 4, 5, Fr(49, 10)])
    t0 = rng.randint(1, 6)
    v = 2 * k * t0
    return {"notion": N1,
            "enonce": f"Un mobile parcourt $d(t) = {fr(k) if Fr(k).denominator == 1 else dec(k)}t^2$ mètres en $t$ secondes. Calculer sa vitesse moyenne entre $t = {t0}$ "
                      f"et $t = {t0} + h$ ($h \\neq 0$), puis sa vitesse instantanée à $t = {t0}$.",
            "answer": f"Vitesse moyenne : ${dec(2 * k * t0)} + {dec(k)}h$ m/s ; vitesse instantanée : ${dec(v)}$ m/s.",
            "steps": [f"Étape 1 — $d({t0} + h) - d({t0}) = {dec(k)}(({t0} + h)^2 - {t0 * t0}) = {dec(2 * k * t0)}h + {dec(k)}h^2$.",
                      f"Étape 2 — Vitesse moyenne : $\\dfrac{{d({t0} + h) - d({t0})}}{{h}} = {dec(2 * k * t0)} + {dec(k)}h$.",
                      f"Étape 3 — Quand $h$ tend vers $0$ : $d'({t0}) = {dec(v)}$ m/s."],
            "hint": "Vitesse moyenne = taux de variation ; vitesse instantanée = nombre dérivé.",
            "check": sp.diff(_S(k) * x**2, x).subs(x, t0) == _S(v)}


# ── Notion 3 — puissances d'exposant négatif ────────────────────────────────


def _gen_puissance_negative(rng):
    k = rng.choice([1, 2, 3, 4, 5, -1, -2, -3])
    n = rng.choice([1, 2, 3])
    a, b = rng.randint(-5, 5), rng.randint(1, 4)
    f = k / x**n + a * x**b
    df = sp.diff(f, x)
    kn = -k * n
    num_t = f"{'-' if kn < 0 else ''}\\dfrac{{{abs(kn)}}}{{x^{{{n + 1}}}}}"
    first = f"\\dfrac{{{abs(k)}}}{{x{'^' + str(n) if n > 1 else ''}}}"
    expr = f"{'-' if k < 0 else ''}{first}" + ("" if a == 0 else f" {'+' if a > 0 else '-'} {'' if abs(a) == 1 else abs(a)}x{'^' + str(b) if b > 1 else ''}")
    dpoly = "" if a == 0 else (f" {'+' if a * b > 0 else '-'} {abs(a * b) if not (abs(a * b) == 1 and b > 1) else ''}{'x' if b > 1 else ''}{'^' + str(b - 1) if b > 2 else ''}")
    if a != 0 and b == 1:
        dpoly = f" {'+' if a > 0 else '-'} {abs(a)}"
    ans = num_t + dpoly
    return {"notion": N3,
            "enonce": f"Calculer la dérivée de $f(x) = {expr}$ sur $]0 ; +\\infty[$.",
            "answer": f"$f'(x) = {ans}$.",
            "steps": [f"Étape 1 — On écrit ${first} = {'' if abs(k) == 1 else abs(k)}x^{{-{n}}}$ et on utilise $(x^n)' = nx^{{n-1}}$, valable pour $n$ entier relatif.",
                      f"Étape 2 — $({lead(k)}x^{{-{n}}})' = {lead(kn)}x^{{-{n + 1}}} = {num_t}$.",
                      f"Étape 3 — $f'(x) = {ans}$."],
            "hint": "Réécris $\\dfrac{1}{x^n}$ sous la forme $x^{-n}$.",
            "check": True, "_expr": f, "_d": df, "_ans": ans}


# ── Notion 4 — inverse et produit ───────────────────────────────────────────


def _gen_inverse(rng):
    a = rng.choice([1, 2, 3, -1])
    c = rng.choice([1, 2, 3, 4, 5])
    if a < 0:
        c = -c
    v = a * x**2 + c
    if sp.solveset(v, x, sp.S.Reals) != sp.S.EmptySet:
        return None
    vt = tri(a, 0, c)
    num = 2 * a
    ans = f"{'-' if num > 0 else ''}\\dfrac{{{abs(num) if abs(num) != 1 else ''}x}}{{({vt})^2}}"
    return {"notion": N4,
            "enonce": f"Calculer la dérivée de $f(x) = \\dfrac{{1}}{{{vt}}}$ sur $\\mathbb{{R}}$.",
            "answer": f"$f'(x) = {ans}$.",
            "steps": [f"Étape 1 — $v(x) = {vt}$ ne s'annule jamais ; $v'(x) = {fr(2 * a)}x$.",
                      "Étape 2 — Règle de l'inverse : $\\left(\\dfrac{1}{v}\\right)' = -\\dfrac{v'}{v^2}$.",
                      f"Étape 3 — $f'(x) = {ans}$."],
            "hint": "Repère $v$ et vérifie qu'il ne s'annule pas.",
            "check": True, "_expr": 1 / v, "_d": sp.diff(1 / v, x), "_ans": ans}


def _gen_produit_racine(rng):
    a = rng.choice([1, 2, 3, -1, -2, 4])
    b = rng.choice([-6, -4, -2, 2, 4, 6, 1, 3])
    f = (a * x + b) * sp.sqrt(x)
    num = sp.expand(sp.simplify(sp.diff(f, x) * 2 * sp.sqrt(x)))  # 3a x + b
    lin_t = tri(0, a, b)
    num_t = tri(0, 3 * a, b)
    ans = f"\\dfrac{{{num_t}}}{{2\\sqrt{{x}}}}"
    return {"notion": N4,
            "enonce": f"Calculer la dérivée de $f(x) = ({lin_t})\\sqrt{{x}}$ sur $]0 ; +\\infty[$.",
            "answer": f"$f'(x) = {ans}$.",
            "steps": [f"Étape 1 — $u(x) = {lin_t}$, $u'(x) = {a}$ ; $v(x) = \\sqrt{{x}}$, $v'(x) = \\dfrac{{1}}{{2\\sqrt{{x}}}}$.",
                      f"Étape 2 — $f'(x) = {lead(a)}\\sqrt{{x}} + \\dfrac{{{lin_t}}}{{2\\sqrt{{x}}}}$.",
                      f"Étape 3 — Au même dénominateur $2\\sqrt{{x}}$ : $f'(x) = {ans}$."],
            "hint": "Règle du produit, puis réduction au même dénominateur.",
            "check": sp.expand(num - (3 * a * x + b)) == 0, "_expr": f, "_d": sp.diff(f, x), "_ans": ans}


@dataclass(frozen=True)
class Family:
    id: str
    level: int
    label: str
    generate: Callable[[random.Random], Optional[dict]]
    notion: str
    score: float


FAMILIES: tuple[Family, ...] = (
    Family("tangente_horizontale", 1, "Point à tangente horizontale", _gen_tangente_horizontale, N1, 1.2),
    Family("lire_pente_tangente", 1, "Tangente donnée par deux points", _gen_lire_pente, N1, 1.4),
    Family("vitesse_instantanee", 2, "Vitesse moyenne et instantanée", _gen_vitesse, N1, 2.2),
    Family("tangente_parallele", 3, "Tangente parallèle à une droite", _gen_tangente_parallele, N1, 3.0),
    Family("tangentes_par_un_point", 4, "Tangentes passant par un point", _gen_tangentes_par_un_point, N1, 4.2),
    Family("approximation_affine", 2, "Approximation affine", _gen_approx_affine, N2, 2.0),
    Family("cout_marginal", 2, "Coût marginal", _gen_cout_marginal, N2, 2.4),
    Family("puissance_negative", 2, "Puissances d'exposant négatif", _gen_puissance_negative, N3, 2.1),
    Family("regle_inverse", 2, "Règle de l'inverse", _gen_inverse, N4, 2.5),
    Family("produit_racine", 3, "Produit avec la racine carrée", _gen_produit_racine, N4, 3.2),
)
FAMILIES_BY_ID = {f.id: f for f in FAMILIES}


def _level_from_score(score: float) -> int:
    return 1 if score <= 1.5 else 2 if score <= 2.7 else 3 if score <= 3.8 else 4


def build_exercise(family: Family, rng: random.Random) -> Optional[dict]:
    notes = family.generate(rng)
    if notes is None or not notes.pop("check"):
        return None
    if "_expr" in notes:
        expr, d, ans = notes.pop("_expr"), notes.pop("_d"), notes.pop("_ans")
        try:
            got = parse_tex(ans)
        except Exception:
            return None  # réponse illisible : jamais publiée
        if sp.simplify(got - d) != 0:
            return None
    level = _level_from_score(family.score)
    assert level == family.level, family.id
    return {"enonce": notes["enonce"], "answer": notes["answer"], "hint": notes["hint"], "solution_steps": notes["steps"],
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


def generate_pool(per_family: int = 12, seed: int = 20261026) -> list[dict]:
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
