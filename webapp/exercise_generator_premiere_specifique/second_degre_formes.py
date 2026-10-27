"""Génération symbolique d'exercices de second degré pour les notions autres
que « Équations du second degré » (couverte par second_degre.py) — Première
spécialité, programme 2026 (Chapitre_2) :

- « Fonction polynôme de degré 2 » : lire une forme canonique, compléter le
  carré, retrouver une fonction à partir de son sommet, comparer des images ;
- « Propriétés d'un trinôme » : seconde racine par le produit, deux nombres de
  somme et produit donnés, signe des racines, expressions symétriques ;
- « Signe du trinôme et inéquations du second degré » : inéquations sous forme
  factorisée ou développée, à ramener à zéro, position relative, paramètre ;
- « Second degré : modéliser et optimiser » : enclos, recette, projectile,
  zone de rentabilité.

Même contrat que second_degre.py (FAMILIES, generate_one, generate_pool,
GENERATED_ID_OFFSET), avec une notion par famille (Family.notion, voir
registry._notion_of). Chaque valeur annoncée est recalculée en arithmétique
exacte (Fraction) puis CONTRÔLÉE par SymPy : en cas de désaccord, le tirage
est rejeté (None), jamais publié.
"""
import random
from dataclasses import dataclass
from fractions import Fraction as Fr
from typing import Callable, Optional

import sympy as sp

x = sp.symbols("x")

CHAPTER_ID = "Chapitre_2"
NOTION = "Fonction polynôme de degré 2"  # repli (chaque famille porte sa notion)
N1 = "Fonction polynôme de degré 2"
N3 = "Propriétés d'un trinôme"
N4 = "Signe du trinôme et inéquations du second degré"
N5 = "Second degré : modéliser et optimiser"

# Bloc distinct de tous les pools de Première (900 000 à 1 008 071).
GENERATED_ID_OFFSET = 1_100_000

LEVEL_META = {
    1: {"emoji": "🟢", "label": "Niveau 1 — Fondamental"},
    2: {"emoji": "🟡", "label": "Niveau 2 — Intermédiaire"},
    3: {"emoji": "🟠", "label": "Niveau 3 — Avancé"},
    4: {"emoji": "🔴", "label": "Niveau 4 — Difficile"},
}

# ── Écriture ─────────────────────────────────────────────────────────────────


def fr(q) -> str:
    """Rationnel en LaTeX ; entiers d'au moins 4 chiffres avec l'espace des milliers (2\\,000)."""
    q = Fr(q)
    if q.denominator == 1:
        n = q.numerator
        return f"{n:,}".replace(",", "\\,") if abs(n) >= 1000 else str(n)
    return f"{'-' if q < 0 else ''}\\dfrac{{{abs(q.numerator)}}}{{{q.denominator}}}"


def pw(q) -> str:
    q = Fr(q)
    if q.denominator != 1:
        return f"\\left({fr(q)}\\right)"
    return f"({q})" if q < 0 else str(q)


def tri(a, b, c, var="x") -> str:
    out = ""
    for k, mono in ((Fr(a), f"{var}^2"), (Fr(b), var), (Fr(c), "")):
        if k == 0:
            continue
        mag = abs(k)
        body = (fr(mag) if (mag != 1 or not mono) else "") + mono
        out += (("-" if k < 0 else "") + body) if not out else ((" - " if k < 0 else " + ") + body)
    return out or "0"


def lin(r, var="x") -> str:
    r = Fr(r)
    if r == 0:
        return var
    return f"{var} - {fr(r)}" if r > 0 else f"{var} + {fr(-r)}"


def lead(a) -> str:
    a = Fr(a)
    return "" if a == 1 else ("-" if a == -1 else fr(a))


def canon(a, al, be, var="x") -> str:
    al, be = Fr(al), Fr(be)
    sq = f"{var}^2" if al == 0 else (f"({lin(al, var)})^2" if al.denominator == 1 else f"\\left({lin(al, var)}\\right)^2")
    out = lead(a) + sq
    if be:
        out += (" - " if be < 0 else " + ") + fr(abs(be))
    return out


def factored(a, r1, r2, var="x") -> str:
    rs = sorted((Fr(r1), Fr(r2)), key=lambda r: (r != 0, r))
    return lead(a) + "".join(var if r == 0 else f"({lin(r, var)})" for r in rs)


def interval(lo, hi, lo_closed, hi_closed) -> str:
    left = "]-\\infty" if lo is None else ("[" if lo_closed else "]") + fr(lo)
    right = "+\\infty[" if hi is None else fr(hi) + ("]" if hi_closed else "[")
    return f"{left} ; {right}"


def _nz(rng, lo, hi):
    return rng.choice([n for n in range(lo, hi + 1) if n != 0])


def _sym(q):
    q = Fr(q)
    return sp.Rational(q.numerator, q.denominator)


def _poly(a, b, c):
    return _sym(a) * x**2 + _sym(b) * x + _sym(c)


def _same_poly(p, q) -> bool:
    return sp.expand(p - q) == 0


OPS = {"<": ("<", sp.Lt), ">": (">", sp.Gt), "<=": ("\\leqslant", sp.Le), ">=": ("\\geqslant", sp.Ge)}


def _ineq_set(a, r1, r2, op):
    """Ensemble des solutions de a(x - r1)(x - r2) op 0, r1 < r2 : (texte, intervalles)."""
    strict = op in ("<", ">")
    outside = (op in (">", ">=")) == (a > 0)
    if outside:
        return (f"{interval(None, r1, False, not strict)} \\cup {interval(r2, None, not strict, False)}",
                sp.Union(sp.Interval(-sp.oo, _sym(r1), True, strict), sp.Interval(_sym(r2), sp.oo, strict, True)))
    return interval(r1, r2, not strict, not strict), sp.Interval(_sym(r1), _sym(r2), strict, strict)


def _ineq_ok(expr, op, sym_set) -> bool:
    return sp.solve_univariate_inequality(OPS[op][1](expr, 0), x, relational=False) == sym_set


# ── Notion 1 — Fonction polynôme de degré 2 ─────────────────────────────────


def _gen_canonique_lecture(rng):
    a = rng.choice([1, 2, 3, -1, -2, -3, Fr(1, 2), Fr(-1, 2)])
    al, be = rng.randint(-6, 6), rng.randint(-9, 9)
    expr = canon(a, al, be)
    kind, first, second = ("minimum", "décroissante", "croissante") if a > 0 else ("maximum", "croissante", "décroissante")
    return {
        "notion": N1,
        "enonce": f"Soit $f$ la fonction définie sur $\\mathbb{{R}}$ par $f(x) = {expr}$. Donner les coordonnées du sommet de sa "
                  f"parabole, la nature de l'extremum de $f$ et son tableau de variations.",
        "answer": f"Sommet $S({al} ; {be})$ ; $f$ admet un {kind} égal à ${be}$ en $x = {al}$ ; $f$ est {first} sur "
                  f"$]-\\infty ; {al}]$ et {second} sur $[{al} ; +\\infty[$.",
        "steps": [f"Étape 1 — $f(x) = a(x - \\alpha)^2 + \\beta$ avec $a = {fr(a)}$, $\\alpha = {al}$ et $\\beta = {be}$ : le sommet est $S({al} ; {be})$.",
                  f"Étape 2 — $a {'>' if a > 0 else '<'} 0$ : la parabole est tournée vers le {'haut' if a > 0 else 'bas'}, $\\beta = {be}$ est un {kind}.",
                  f"Étape 3 — $f$ est {first} sur $]-\\infty ; {al}]$ puis {second} sur $[{al} ; +\\infty[$."],
        "hint": "Dans $a(x - \\alpha)^2 + \\beta$, le sommet se lit directement ; le signe de $a$ donne le sens.",
        "check": _same_poly(sp.diff(_sym(a) * (x - al) ** 2 + be, x).subs(x, al), 0),
    }


def _gen_canonique_completion(rng):
    k = _nz(rng, -7, 7)
    c = rng.randint(-12, 12)
    b = 2 * k
    be = c - k * k
    expr = tri(1, b, c)
    res = canon(1, -k, be)
    return {
        "notion": N1,
        "enonce": f"Écrire $f(x) = {expr}$ sous forme canonique par complétion du carré, puis en déduire l'extremum de $f$.",
        "answer": f"$f(x) = {res}$ ; $f$ admet un minimum égal à ${be}$, atteint en $x = {-k}$.",
        "steps": [f"Étape 1 — $x^2 {'+' if b > 0 else '-'} {abs(b)}x$ est le début de $({lin(-k)})^2 = x^2 {'+' if b > 0 else '-'} {abs(b)}x + {k * k}$.",
                  f"Étape 2 — Donc $f(x) = ({lin(-k)})^2 - {k * k}{' + ' + str(c) if c > 0 else (' - ' + str(-c) if c < 0 else '')} = {res}$.",
                  f"Étape 3 — Un carré est positif ou nul : $f(x) \\geqslant {be}$, avec égalité pour $x = {-k}$ (minimum, car $a = 1 > 0$)."],
        "hint": "Utilise $x^2 + 2kx = (x + k)^2 - k^2$.",
        "check": _same_poly((x + k) ** 2 + be, _poly(1, b, c)),
    }


def _gen_canonique_general(rng):
    a = rng.choice([2, 3, -2, -3, 4, -4])
    b = _nz(rng, -12, 12)
    c = rng.randint(-10, 10)
    al = Fr(-b, 2 * a)
    be = a * al * al + b * al + c
    if al.denominator == 1 and be.denominator == 1 and rng.random() < 0.3:
        return None
    half = Fr(b, 2 * a)
    k2 = a * half * half
    inner = tri(1, Fr(b, a), 0)
    res = canon(a, al, be)
    cst = "" if c == 0 else (f" + {c}" if c > 0 else f" - {-c}")
    return {
        "notion": N1,
        "enonce": f"Déterminer la forme canonique de $f(x) = {tri(a, b, c)}$ et les coordonnées du sommet de sa parabole.",
        "answer": f"$f(x) = {res}$ ; sommet $S\\left({fr(al)} ; {fr(be)}\\right)$.",
        "steps": [f"Étape 1 — On factorise $a = {a}$ dans les termes en $x$ : $f(x) = {lead(a)}\\left({inner}\\right){cst}$.",
                  f"Étape 2 — Complétion du carré : ${inner} = {canon(1, al, 0)} - {pw(abs(half))}^2$.",
                  f"Étape 3 — $f(x) = {canon(a, al, 0)} {'-' if k2 > 0 else '+'} {fr(abs(k2))}{cst} = {res}$.",
                  f"Étape 4 — Contrôle : $\\alpha = -\\dfrac{{b}}{{2a}} = {fr(al)}$ et $f(\\alpha) = {fr(be)}$."],
        "hint": "Factorise d'abord $a$ dans les termes en $x$, puis complète le carré dans la parenthèse.",
        "check": _same_poly(_sym(a) * (x - _sym(al)) ** 2 + _sym(be), _poly(a, b, c)),
    }


def _gen_sommet_et_point(rng):
    al, be = rng.randint(-5, 5), rng.randint(-8, 8)
    a = _nz(rng, -3, 3)
    d = _nz(rng, -3, 3)
    x0 = al + d
    y0 = a * d * d + be
    b, c = -2 * a * al, a * al * al + be
    return {
        "notion": N1,
        "enonce": f"La parabole d'une fonction polynôme du second degré $f$ a pour sommet $S({al} ; {be})$ et passe par le point "
                  f"$A({x0} ; {y0})$. Déterminer $f(x)$ sous forme canonique puis développée.",
        "answer": f"$f(x) = {canon(a, al, be)} = {tri(a, b, c)}$.",
        "steps": [f"Étape 1 — Le sommet impose $f(x) = a{canon(1, al, be)}$ avec $a \\neq 0$.",
                  f"Étape 2 — $A$ est sur la parabole : $a \\times {pw(d)}^2{'' if be == 0 else (' + ' if be > 0 else ' - ') + str(abs(be))} = {y0}$, "
                  + (f"donc ${d * d}a = {y0 - be}$ et $a = {a}$." if d * d != 1 else f"donc $a = {a}$."),
                  f"Étape 3 — $f(x) = {canon(a, al, be)} = {tri(a, b, c)}$."],
        "hint": "Écris $f(x) = a(x - \\alpha)^2 + \\beta$ : il ne reste que $a$ à trouver.",
        "check": _same_poly(_sym(a) * (x - al) ** 2 + be, _poly(a, b, c)) and (_sym(a) * (x0 - al) ** 2 + be) == y0,
    }


def _gen_comparer_images(rng):
    a = rng.choice([1, 2, 3, -1, -2, -3])
    al, be = rng.randint(-4, 4), rng.randint(-6, 6)
    du, dv = rng.sample([1, 2, 3, 4, 5], 2)
    u = al - du if rng.random() < 0.5 else al + du
    v = al + dv if u < al else al - dv
    fu, fv = a * (u - al) ** 2 + be, a * (v - al) ** 2 + be
    bigger = "f(u)" if fu > fv else "f(v)"
    rel = f"f({u}) > f({v})" if fu > fv else f"f({u}) < f({v})"
    return {
        "notion": N1,
        "enonce": f"Soit $f(x) = {canon(a, al, be)}$. Sans calculer d'image, comparer $f({u})$ et $f({v})$.",
        "answer": f"${rel}$.",
        "steps": [f"Étape 1 — $f(x)$ ne dépend que de l'écart $|{lin(al)}|$ à l'axe de symétrie ; avec $a = {a}$, "
                  f"$f(x)$ {'augmente' if a > 0 else 'diminue'} quand cet écart augmente.",
                  f"Étape 2 — $|{u} - {pw(al)}| = {abs(u - al)}$ et $|{v} - {pw(al)}| = {abs(v - al)}$.",
                  f"Étape 3 — Conclusion : ${rel}$ (contrôle : $f({u}) = {fu}$ et $f({v}) = {fv}$)."],
        "hint": "Compare les distances des deux nombres à l'abscisse du sommet.",
        "check": bigger is not None and fu != fv,
    }


# ── Notion 3 — Propriétés d'un trinôme ──────────────────────────────────────


def _gen_autre_racine(rng):
    a = rng.choice([1, 1, 2, 3, -1, -2])
    r1, r2 = rng.sample([n for n in range(-7, 8) if n != 0], 2)
    b, c = -a * (r1 + r2), a * r1 * r2
    return {
        "notion": N3,
        "enonce": f"Vérifier que ${r1}$ est racine de $f(x) = {tri(a, b, c)}$, puis déterminer l'autre racine sans calculer de "
                  f"discriminant et factoriser $f(x)$.",
        "answer": f"L'autre racine est ${r2}$ et $f(x) = {factored(a, r1, r2)}$.",
        "steps": [f"Étape 1 — $f({r1}) = {a * r1 * r1} {'+' if b * r1 >= 0 else '-'} {abs(b * r1)} {'+' if c >= 0 else '-'} {abs(c)} = 0$.",
                  f"Étape 2 — Produit des racines : $\\dfrac{{c}}{{a}} = {fr(Fr(c, a))}$, donc l'autre racine vaut ${fr(Fr(c, a))} \\div {pw(r1)} = {r2}$.",
                  f"Étape 3 — $f(x) = a(x - x_1)(x - x_2) = {factored(a, r1, r2)}$."],
        "hint": "Le produit des racines vaut $\\dfrac{c}{a}$.",
        "check": sp.factor(_poly(a, b, c)) == sp.factor(a * (x - r1) * (x - r2)) and _poly(a, b, c).subs(x, r1) == 0,
    }


def _gen_deux_nombres(rng):
    u, v = rng.sample(range(-9, 13), 2)
    s, p = u + v, u * v
    lo, hi = min(u, v), max(u, v)
    return {
        "notion": N3,
        "enonce": f"Déterminer deux réels dont la somme vaut ${s}$ et le produit ${p}$.",
        "answer": f"Les deux réels sont ${lo}$ et ${hi}$.",
        "steps": [f"Étape 1 — Deux réels de somme $s$ et de produit $p$ sont les racines de $x^2 - sx + p$ : ici ${tri(1, -s, p)} = 0$.",
                  f"Étape 2 — $\\Delta = {pw(s)}^2 - 4 \\times {pw(p)} = {s * s - 4 * p} = {abs(u - v)}^2$, donc $x = \\dfrac{{{s} \\pm {abs(u - v)}}}{{2}}$.",
                  f"Étape 3 — On trouve ${lo}$ et ${hi}$ (contrôle : ${lo} + {pw(hi)} = {s}$ et ${lo} \\times {pw(hi)} = {p}$)."],
        "hint": "Ce sont les racines de $x^2 - sx + p$.",
        "check": sorted(sp.solve(x**2 - s * x + p, x)) == [lo, hi],
    }


def _gen_signe_racines(rng):
    a = rng.choice([1, 2, 3, -1, -2, 4])
    r1, r2 = rng.sample([n for n in range(-6, 7) if n != 0], 2)
    if rng.random() < 0.5:
        r2 = Fr(r2, rng.choice([2, 3]))
    b, c = -a * (r1 + r2), a * r1 * r2
    if Fr(b).denominator != 1 or Fr(c).denominator != 1:
        return None
    b, c = int(b), int(c)
    s, p = Fr(-b, a), Fr(c, a)
    if p < 0:
        concl = "elles sont de signes contraires"
    elif s > 0:
        concl = "elles sont toutes les deux positives"
    else:
        concl = "elles sont toutes les deux négatives"
    d = b * b - 4 * a * c
    return {
        "notion": N3,
        "enonce": f"Sans calculer les racines de $f(x) = {tri(a, b, c)}$, justifier qu'elles existent et déterminer leur signe.",
        "answer": f"$f$ a deux racines distinctes et {concl}.",
        "steps": [f"Étape 1 — $\\Delta = {pw(b)}^2 - 4 \\times {pw(a)} \\times {pw(c)} = {d} > 0$ : deux racines distinctes.",
                  f"Étape 2 — Produit $P = \\dfrac{{c}}{{a}} = {fr(p)}$ et somme $S = -\\dfrac{{b}}{{a}} = {fr(s)}$.",
                  f"Étape 3 — {'$P < 0$ : ' + concl if p < 0 else '$P > 0$ : les racines sont de même signe, celui de $S$ ; ' + concl}."],
        "hint": "Le signe du produit dit si les racines sont de même signe, celui de la somme lequel.",
        "check": d > 0 and p != 0 and (sorted([float(r1), float(r2)]) == sorted(float(r) for r in sp.solve(_poly(a, b, c), x))),
    }


def _gen_expression_symetrique(rng):
    s, p = _nz(rng, -9, 9), _nz(rng, -12, 12)
    if s * s - 4 * p <= 0:
        return None
    q2 = s * s - 2 * p
    inv = Fr(s, p)
    return {
        "notion": N3,
        "enonce": f"On note $x_1$ et $x_2$ les racines de ${tri(1, -s, p)}$. Sans les calculer, "
                  f"déterminer $x_1^2 + x_2^2$ et $\\dfrac{{1}}{{x_1}} + \\dfrac{{1}}{{x_2}}$.",
        "answer": f"$x_1^2 + x_2^2 = {q2}$ et $\\dfrac{{1}}{{x_1}} + \\dfrac{{1}}{{x_2}} = {fr(inv)}$.",
        "steps": [f"Étape 1 — $\\Delta = {s * s} {'-' if p > 0 else '+'} {abs(4 * p)} = {s * s - 4 * p} > 0$ ; $S = x_1 + x_2 = {s}$ et $P = x_1 x_2 = {p}$.",
                  f"Étape 2 — $x_1^2 + x_2^2 = (x_1 + x_2)^2 - 2x_1x_2 = {pw(s)}^2 - 2 \\times {pw(p)} = {q2}$.",
                  f"Étape 3 — $\\dfrac{{1}}{{x_1}} + \\dfrac{{1}}{{x_2}} = \\dfrac{{x_1 + x_2}}{{x_1 x_2}} = \\dfrac{{{s}}}{{{p}}} = {fr(inv)}$."],
        "hint": "Exprime chaque quantité avec $S = x_1 + x_2$ et $P = x_1 x_2$.",
        "check": (lambda rs: sp.simplify(rs[0] ** 2 + rs[1] ** 2 - q2) == 0 and sp.simplify(1 / rs[0] + 1 / rs[1] - _sym(inv)) == 0)(
            sp.solve(x**2 - s * x + p, x)),
    }


# ── Notion 4 — Signe et inéquations ─────────────────────────────────────────


def _roots_pair(rng, frac_ok=False):
    r1, r2 = sorted(rng.sample(range(-7, 8), 2))
    if frac_ok and rng.random() < 0.4:
        r2 = Fr(2 * r2 + 1, 2) if Fr(2 * r2 + 1, 2) > r1 else None
        if r2 is None:
            return None
    return Fr(r1), Fr(r2)


def _gen_inequation_factorisee(rng):
    a = _nz(rng, -4, 4)
    pair = _roots_pair(rng)
    r1, r2 = pair
    op = rng.choice(list(OPS))
    text, sset = _ineq_set(a, r1, r2, op)
    return {
        "notion": N4,
        "enonce": f"Résoudre dans $\\mathbb{{R}}$ l'inéquation ${factored(a, r1, r2)} {OPS[op][0]} 0$.",
        "answer": f"$\\mathcal{{S}} = {text}$",
        "steps": [f"Étape 1 — Racines : ${fr(r1)}$ et ${fr(r2)}$ ; coefficient $a = {a}$.",
                  f"Étape 2 — Le trinôme est du signe de $a$ ({'positif' if a > 0 else 'négatif'}) à l'extérieur des racines, du signe contraire entre.",
                  f"Étape 3 — {'Inégalité stricte : crochets ouverts aux racines' if op in ('<', '>') else 'Inégalité large : crochets fermés aux racines'} : $\\mathcal{{S}} = {text}$."],
        "hint": "Lis les racines sur la forme factorisée, puis applique la règle du signe.",
        "check": _ineq_ok(a * (x - _sym(r1)) * (x - _sym(r2)), op, sset),
    }


def _gen_inequation_developpee(rng):
    a = rng.choice([1, 2, -1, -2, 3, -3])
    pair = _roots_pair(rng, frac_ok=True)
    if pair is None:
        return None
    r1, r2 = pair
    b, c = -a * (r1 + r2), a * r1 * r2
    if b.denominator != 1 or c.denominator != 1:
        return None
    op = rng.choice(list(OPS))
    text, sset = _ineq_set(a, r1, r2, op)
    d = b * b - 4 * a * c
    return {
        "notion": N4,
        "enonce": f"Résoudre dans $\\mathbb{{R}}$ l'inéquation ${tri(a, b, c)} {OPS[op][0]} 0$.",
        "answer": f"$\\mathcal{{S}} = {text}$",
        "steps": [f"Étape 1 — $\\Delta = {pw(b)}^2 - 4 \\times {pw(a)} \\times {pw(c)} = {d}$ : racines ${fr(r1)}$ et ${fr(r2)}$.",
                  f"Étape 2 — $a = {a}$ : signe de $a$ à l'extérieur des racines, signe contraire entre.",
                  f"Étape 3 — $\\mathcal{{S}} = {text}$."],
        "hint": "Cherche les racines, puis applique la règle du signe d'un trinôme.",
        "check": _ineq_ok(_poly(a, b, c), op, sset),
    }


def _gen_inequation_ramener(rng):
    a = rng.choice([1, 2, -1, 3])
    r1, r2 = (Fr(v) for v in sorted(rng.sample(range(-6, 7), 2)))
    b, c = -a * (r1 + r2), a * r1 * r2
    d1, e1 = rng.randint(-5, 5), rng.randint(-9, 9)
    # Inéquation a x² + (b + d1) x + (c + e1) op d1 x + e1 : se ramène à a(x - r1)(x - r2) op 0
    op = rng.choice(list(OPS))
    text, sset = _ineq_set(a, r1, r2, op)
    left = tri(a, b + d1, c + e1)
    right = tri(0, d1, e1)
    if right == "0" or b + d1 == 0:
        return None
    return {
        "notion": N4,
        "enonce": f"Résoudre dans $\\mathbb{{R}}$ l'inéquation ${left} {OPS[op][0]} {right}$.",
        "answer": f"$\\mathcal{{S}} = {text}$",
        "steps": [f"Étape 1 — On ramène tout dans le premier membre : ${tri(a, b, c)} {OPS[op][0]} 0$.",
                  f"Étape 2 — Racines ${fr(r1)}$ et ${fr(r2)}$ ; $a = {a}$.",
                  f"Étape 3 — Règle du signe : $\\mathcal{{S}} = {text}$."],
        "hint": "Ne compare jamais deux expressions directement : étudie le signe de leur différence.",
        "check": _ineq_ok(_poly(a, b + d1, c + e1) - _poly(0, d1, e1), op, sset),
    }


def _gen_position_relative(rng):
    r1, r2 = (Fr(v) for v in sorted(rng.sample(range(-5, 6), 2)))
    m, p = rng.randint(-4, 4), rng.randint(-6, 6)
    # f(x) - g(x) = (x - r1)(x - r2) avec g(x) = mx + p
    b, c = -(r1 + r2) + m, r1 * r2 + p
    y1, y2 = m * r1 + p, m * r2 + p
    g = tri(0, m, p)
    if g == "0":
        return None
    return {
        "notion": N4,
        "enonce": f"Étudier la position relative de la parabole $\\mathcal{{P}}$ d'équation $y = {tri(1, b, c)}$ et de la droite "
                  f"$\\mathcal{{D}}$ d'équation $y = {g}$.",
        "answer": f"$\\mathcal{{P}}$ est au-dessus de $\\mathcal{{D}}$ sur ${interval(None, r1, False, False)} \\cup {interval(r2, None, False, False)}$, "
                  f"en dessous sur ${interval(r1, r2, False, False)}$ ; elles se coupent en $({fr(r1)} ; {fr(y1)})$ et $({fr(r2)} ; {fr(y2)})$.",
        "steps": [f"Étape 1 — Différence : $d(x) = {tri(1, b, c)} - ({g}) = {tri(1, -(r1 + r2), r1 * r2)} = {factored(1, r1, r2)}$.",
                  f"Étape 2 — $d(x) > 0$ à l'extérieur de ${fr(r1)}$ et ${fr(r2)}$ ($a = 1 > 0$), $d(x) < 0$ entre.",
                  f"Étape 3 — Points communs : abscisses ${fr(r1)}$ et ${fr(r2)}$, d'ordonnées ${fr(y1)}$ et ${fr(y2)}$."],
        "hint": "Étudie le signe de la différence des deux expressions.",
        "check": _same_poly(_poly(1, b, c) - _poly(0, m, p), (x - _sym(r1)) * (x - _sym(r2))),
    }


def _gen_inequation_parametre(rng):
    k = rng.choice([1, 4, 9, 16, 25])
    rt = int(k ** 0.5)
    return {
        "notion": N4,
        "enonce": f"Déterminer les réels $m$ pour lesquels $x^2 + mx + {k} > 0$ pour tout réel $x$.",
        "answer": f"$m \\in ]-{2 * rt} ; {2 * rt}[$",
        "steps": ["Étape 1 — $a = 1 > 0$ : le trinôme est strictement positif sur $\\mathbb{R}$ si et seulement s'il n'a pas de racine, c'est-à-dire $\\Delta < 0$.",
                  f"Étape 2 — $\\Delta = m^2 - {4 * k}$.",
                  f"Étape 3 — $m^2 - {4 * k} < 0 \\iff (m - {2 * rt})(m + {2 * rt}) < 0 \\iff -{2 * rt} < m < {2 * rt}$."],
        "hint": "Un trinôme avec $a > 0$ est toujours positif exactement quand son discriminant est négatif.",
        "check": sp.solve_univariate_inequality(sp.Symbol("m") ** 2 - 4 * k < 0, sp.Symbol("m"), relational=False)
        == sp.Interval.open(-2 * rt, 2 * rt),
    }


# ── Notion 5 — Modéliser et optimiser ───────────────────────────────────────


def _gen_enclos(rng):
    L = rng.choice([24, 32, 40, 48, 60, 64, 80, 100, 120])
    xm = Fr(L, 4)
    am = xm * (L - 2 * xm)
    return {
        "notion": N5,
        "enonce": f"Avec ${L}$ m de grillage, on clôture un enclos rectangulaire adossé à un mur (le côté le long du mur n'est pas "
                  f"grillagé). On note $x$ la longueur des côtés perpendiculaires au mur. Quelles dimensions donnent la plus grande aire ?",
        "answer": f"Côtés perpendiculaires au mur : ${fr(xm)}$ m, côté parallèle : ${fr(L - 2 * xm)}$ m ; aire maximale ${fr(am)}$ m².",
        "steps": [f"Étape 1 — Le côté parallèle au mur mesure ${L} - 2x$, avec $0 < x < {fr(Fr(L, 2))}$.",
                  f"Étape 2 — $A(x) = x({L} - 2x) = -2x^2 + {L}x$, avec $a = -2 < 0$ : $A$ admet un maximum.",
                  f"Étape 3 — $\\alpha = -\\dfrac{{{L}}}{{2 \\times (-2)}} = {fr(xm)}$ (dans le domaine) et $A({fr(xm)}) = {fr(am)}$."],
        "hint": "Exprime l'aire en fonction de $x$, puis cherche le sommet.",
        "check": sp.solve(sp.diff(x * (L - 2 * x), x), x) == [_sym(xm)],
    }


def _gen_recette(rng):
    n = rng.choice([200, 300, 400, 600, 800, 1000])
    k = rng.choice([5, 10, 20, 25])
    pm = Fr(n, 2 * k)
    if pm.denominator != 1 or pm > 100:
        return None
    rm = pm * (n - k * pm)
    return {
        "notion": N5,
        "enonce": f"Une salle de concert vend $({n} - {k}p)$ billets lorsque le prix d'un billet est $p$ euros "
                  f"($0 \\leqslant p \\leqslant {fr(Fr(n, k))}$). Quel prix maximise la recette ? Quelle est alors la recette ?",
        "answer": f"Un prix de ${fr(pm)}$ euros, pour une recette de ${fr(rm)}$ euros.",
        "steps": [f"Étape 1 — Recette : $R(p) = p({n} - {k}p) = -{k}p^2 + {n}p$.",
                  f"Étape 2 — $a = -{k} < 0$ : maximum en $p = -\\dfrac{{{n}}}{{2 \\times (-{k})}} = {fr(pm)}$.",
                  f"Étape 3 — $R({fr(pm)}) = {fr(pm)} \\times {fr(n - k * pm)} = {fr(rm)}$ euros."],
        "hint": "Recette = prix × nombre de billets vendus.",
        "check": sp.solve(sp.diff(x * (n - k * x), x), x) == [_sym(pm)],
    }


def _gen_projectile(rng):
    t2 = rng.randint(2, 6)
    t1 = -rng.randint(1, min(3, t2 - 1))  # t1 + t2 > 0 : la balle monte d'abord
    # h(t) = -5(t - t1)(t - t2)
    b, c = 5 * (t1 + t2), -5 * t1 * t2
    tm = Fr(t1 + t2, 2)
    hm = -5 * (tm - t1) * (tm - t2)
    return {
        "notion": N5,
        "enonce": f"La hauteur (en m) d'une balle lancée vers le haut est $h(t) = {tri(-5, b, c, 't')}$, où $t$ est le temps en "
                  f"secondes ($t \\geqslant 0$). Au bout de combien de temps touche-t-elle le sol ? Quelle hauteur maximale atteint-elle ?",
        "answer": f"Elle touche le sol au bout de ${t2}$ s ; sa hauteur maximale est ${fr(hm)}$ m, atteinte à $t = {fr(tm)}$ s.",
        "steps": [f"Étape 1 — $h(t) = -5\\left({tri(1, -(t1 + t2), t1 * t2, 't')}\\right) = -5{factored(1, t1, t2, 't')}$.",
                  f"Étape 2 — $h(t) = 0$ pour $t = {t1}$ (exclu car $t \\geqslant 0$) ou $t = {t2}$.",
                  f"Étape 3 — Maximum au sommet : $t = \\dfrac{{{t1} + {t2}}}{{2}} = {fr(tm)}$, et $h({fr(tm)}) = {fr(hm)}$."],
        "hint": "Factorise $h(t)$ en mettant $-5$ en facteur.",
        "check": _same_poly(_poly(-5, b, c), -5 * (x - t1) * (x - t2)),
    }


def _gen_rentabilite(rng):
    q1, q2 = sorted(rng.sample(range(10, 120, 10), 2))
    k = rng.choice([1, 2])
    # B(q) = -k(q - q1)(q - q2)
    b, c = k * (q1 + q2), -k * q1 * q2
    qm = Fr(q1 + q2, 2)
    bm = -k * (qm - q1) * (qm - q2)
    return {
        "notion": N5,
        "enonce": f"Le bénéfice (en euros) réalisé en vendant $q$ objets est $B(q) = {tri(-k, b, c, 'q')}$. Pour quelles quantités "
                  f"l'entreprise ne perd-elle pas d'argent ? Quel est le bénéfice maximal ?",
        "answer": f"Pour $q \\in [{q1} ; {q2}]$ ; le bénéfice maximal est ${fr(bm)}$ euros, pour $q = {fr(qm)}$.",
        "steps": [f"Étape 1 — $B(q) = {lead(-k)}\\left({tri(1, -(q1 + q2), q1 * q2, 'q')}\\right) = {factored(-k, q1, q2, 'q')}$.",
                  f"Étape 2 — $a < 0$ : $B(q) \\geqslant 0$ entre les racines, soit pour ${q1} \\leqslant q \\leqslant {q2}$.",
                  f"Étape 3 — Maximum au milieu des racines : $q = {fr(qm)}$, $B({fr(qm)}) = {fr(bm)}$."],
        "hint": "Factorise : les racines bornent la zone de rentabilité, le sommet donne le maximum.",
        "check": _same_poly(_poly(-k, b, c), -k * (x - q1) * (x - q2)) and bm > 0,
    }


# ── Familles ─────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Family:
    id: str
    level: int
    label: str
    generate: Callable[[random.Random], Optional[dict]]
    notion: str
    score: float


FAMILIES: tuple[Family, ...] = (
    Family("canonique_lecture", 1, "Lire sommet et variations sur une forme canonique", _gen_canonique_lecture, N1, 1.0),
    Family("canonique_completion", 2, "Forme canonique par complétion du carré (a = 1)", _gen_canonique_completion, N1, 2.0),
    Family("canonique_general", 3, "Forme canonique avec a ≠ 1", _gen_canonique_general, N1, 3.0),
    Family("sommet_et_point", 3, "Retrouver une fonction à partir du sommet et d'un point", _gen_sommet_et_point, N1, 3.2),
    Family("comparer_images", 4, "Comparer des images grâce à la symétrie", _gen_comparer_images, N1, 4.0),
    Family("autre_racine", 2, "Seconde racine par le produit, factorisation", _gen_autre_racine, N3, 2.2),
    Family("deux_nombres", 2, "Deux nombres de somme et produit donnés", _gen_deux_nombres, N3, 2.4),
    Family("signe_racines", 3, "Signe des racines sans les calculer", _gen_signe_racines, N3, 3.4),
    Family("expression_symetrique", 4, "Expressions symétriques des racines", _gen_expression_symetrique, N3, 4.2),
    Family("inequation_factorisee", 1, "Inéquation sous forme factorisée", _gen_inequation_factorisee, N4, 1.2),
    Family("inequation_developpee", 2, "Inéquation du second degré", _gen_inequation_developpee, N4, 2.6),
    Family("inequation_ramener", 3, "Inéquation à ramener à zéro", _gen_inequation_ramener, N4, 3.0),
    Family("position_relative", 3, "Position relative d'une parabole et d'une droite", _gen_position_relative, N4, 3.6),
    Family("inequation_parametre", 4, "Trinôme toujours positif (paramètre)", _gen_inequation_parametre, N4, 4.4),
    Family("enclos", 2, "Optimisation : aire d'un enclos", _gen_enclos, N5, 2.5),
    Family("recette", 3, "Optimisation : recette maximale", _gen_recette, N5, 3.1),
    Family("projectile", 3, "Modélisation : trajectoire d'une balle", _gen_projectile, N5, 3.5),
    Family("rentabilite", 4, "Zone de rentabilité et bénéfice maximal", _gen_rentabilite, N5, 4.1),
)
FAMILIES_BY_ID = {f.id: f for f in FAMILIES}


def _level_from_score(score: float) -> int:
    if score <= 1.5:
        return 1
    if score <= 2.7:
        return 2
    if score <= 3.8:
        return 3
    return 4


def build_exercise(family: Family, rng: random.Random) -> Optional[dict]:
    notes = family.generate(rng)
    if notes is None or not notes.pop("check"):
        return None
    level = _level_from_score(family.score)
    assert level == family.level, family.id
    return {
        "enonce": notes["enonce"],
        "answer": notes["answer"],
        "hint": notes["hint"],
        "solution_steps": notes["steps"],
        "chapter_id": CHAPTER_ID,
        "notion": family.notion,
        "difficulty": level,
        "difficulty_label": LEVEL_META[level]["label"],
        "difficulty_emoji": LEVEL_META[level]["emoji"],
        "family": family.id,
        "family_label": family.label,
        "declared_level": family.level,
        "complexity_score": family.score,
        "source": "generated",
    }


def generate_one(family_id: str, seed: Optional[int] = None, max_attempts: int = 60) -> dict:
    rng = random.Random(seed)
    fam = FAMILIES_BY_ID[family_id]
    for _ in range(max_attempts):
        ex = build_exercise(fam, rng)
        if ex is not None:
            return ex
    raise RuntimeError(f"Impossible de générer un exercice valide pour la famille {family_id!r}")


def generate_pool(per_family: int = 12, seed: int = 20261025) -> list[dict]:
    """Pool déterministe : même seed → même fichier, mêmes identifiants.
    Chaque famille a son propre générateur aléatoire (seed + rang) et son bloc
    d'identifiants (OFFSET + 1 000 × rang + k) : augmenter `per_family` plus
    tard AJOUTE des exercices en fin de bloc sans modifier ceux déjà servis."""
    pool: list[dict] = []
    for rank, family in enumerate(FAMILIES):
        rng = random.Random(seed * 100 + rank)
        seen, items, attempts = set(), [], 0
        while len(items) < per_family and attempts < per_family * 80:
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
