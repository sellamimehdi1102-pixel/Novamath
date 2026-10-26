"""Construction des cours de Première au schéma v2.

Réutilise le constructeur de la Quatrième (quatrieme.cours_commun : mêmes
champs, mêmes invariants vérifiés par assertion) et ajoute ce dont l'analyse
a besoin : courbes échantillonnées et tableaux de signes / de variations dont
le contenu est CONTRÔLÉ numériquement à partir de la fonction représentée
(une figure ne peut donc pas annoncer un signe ou un sens de variation faux).
"""
from fractions import Fraction

from quatrieme.cours_commun import (  # noqa: F401  (réexportés pour les modules de chapitre)
    P, arc, calc, chapter, demonstration, dist, ex, explication, figure_geom, formule, mid, poly, pt, right_marker,
    seg, step, text, view_box,
)
from quatrieme.cours_commun import notion as _notion


def notion(**kw):
    """Notion de lycée : une seule définition (`definitions.lycee`)."""
    n = _notion(definition_college=kw["definition"], **kw)
    n["definitions"] = {"lycee": n["definition"]}
    return n


# ── Courbes ──────────────────────────────────────────────────────────────────


def curve(f, x0, x1, view, n=120, variant=None, reveal=None, dashed=False, tooltip=None):
    """Courbe de `f` sur [x0 ; x1], coupée là où elle sort du cadre `view`
    ([xmin, ymin, largeur, hauteur]) : renvoie une LISTE de courbes."""
    ymin, ymax = view[1], view[1] + view[3]
    parts, cur = [], []
    for i in range(n + 1):
        x = x0 + (x1 - x0) * i / n
        try:
            y = f(x)
        except (ZeroDivisionError, ValueError):
            y = None
        if y is None or not (ymin - 0.05 <= y <= ymax + 0.05):
            if len(cur) > 1:
                parts.append(cur)
            cur = []
            continue
        cur.append([round(x, 3), round(y, 3)])
    if len(cur) > 1:
        parts.append(cur)
    out = []
    for pts in parts:
        c = {"points": pts}
        for key, value in (("variant", variant), ("reveal", reveal), ("dashed", dashed), ("tooltip", tooltip)):
            if value:
                c[key] = value
        out.append(c)
    assert out, "courbe entièrement hors du cadre"
    return out


def on_curve(f, x, label, **kw):
    """Point de la courbe (ordonnée calculée, jamais saisie)."""
    return pt(x, f(x), label, **kw)


# ── Tableaux de signes et de variations ─────────────────────────────────────


def _between(a, b):
    """Point test strictement entre a et b (bornes infinies comprises)."""
    if a is None and b is None:
        return 0.0
    if a is None:
        return b - 1.0
    if b is None:
        return a + 1.0
    return (a + b) / 2


def signe(label, f, xs, marks):
    """Ligne de signes de `f` : les signes sont CALCULÉS (f en un point de
    chaque intervalle) ; `marks` (« 0 », « || », « ») est vérifié : « 0 »
    exige f = 0 ; « || » une valeur interdite. `xs` : abscisses numériques,
    None pour ±∞."""
    signs = []
    for a, b in zip(xs, xs[1:]):
        v = f(_between(a, b))
        assert v != 0, f"{label} : f s'annule dans un intervalle"
        signs.append("+" if v > 0 else "-")
    for x, m in zip(xs, marks):
        if m == "0":
            assert abs(f(x)) < 1e-9, f"{label} : f({x}) ≠ 0"
        if m == "||":
            try:
                f(x)
                raise AssertionError(f"{label} : {x} n'est pas une valeur interdite")
            except ZeroDivisionError:
                pass
    return {"type": "signe", "label": label, "signs": signs, "marks": list(marks)}


def variation(label, f, xs, values):
    """Ligne de variations de `f` : les niveaux haut/bas sont DÉDUITS de la
    monotonie mesurée sur chaque intervalle (f strictement monotone exigée) ;
    chaque valeur affichée doit être f(x) (comparée à `values_num`)."""
    pts = []
    for a, b in zip(xs, xs[1:]):
        lo, hi = (a if a is not None else (b - 3.0)), (b if b is not None else (a + 3.0))
        grid = [lo + (hi - lo) * k / 40 for k in range(41)]
        ys = [f(x) for x in grid]
        inc = all(y2 > y1 for y1, y2 in zip(ys, ys[1:]))
        dec = all(y2 < y1 for y1, y2 in zip(ys, ys[1:]))
        assert inc or dec, f"{label} : f non strictement monotone sur [{a} ; {b}]"
        pts.append("inc" if inc else "dec")
    levels = []
    for i in range(len(xs)):
        left = pts[i - 1] if i > 0 else None
        right = pts[i] if i < len(pts) else None
        if right == "inc" or left == "dec":
            levels.append("bas")
        else:
            levels.append("haut")
    for i, (x, (shown, num)) in enumerate(zip(xs, values)):
        if num is not None:
            assert x is not None and abs(f(x) - num) < 1e-9, f"{label} : valeur {shown} ≠ f({x})"
    return {"type": "variation", "label": label, "values": [v[0] for v in values], "levels": levels}


def tableau(xs_tex, rows, *, steps, relation, alt, explication):
    assert len(steps) == 3
    for r in rows:
        if r["type"] == "signe":
            assert len(r["signs"]) == len(xs_tex) - 1 and len(r["marks"]) == len(xs_tex)
        else:
            assert len(r["values"]) == len(xs_tex) == len(r["levels"])
    for r in rows:
        assert len(r["label"]) <= 12, f"libellé trop long pour la colonne : {r['label']!r} (mettre l'expression dans la relation)"
    # emphasis : colonne graphique élargie (comme les figures geom), le tableau
    # restant lisible à sa taille d'affichage.
    return {"kind": "tableau", "xs": list(xs_tex), "rows": list(rows), "emphasis": True, "steps": list(steps),
            "relation": relation, "alt": alt, "explication": explication}


# ── Écriture des nombres et des polynômes (LaTeX) ───────────────────────────


def fr(q, display=True):
    """Rationnel en LaTeX : entier, ou fraction irréductible signée."""
    q = Fraction(q)
    if q.denominator == 1:
        return str(q.numerator)
    cmd = "\\dfrac" if display else "\\frac"
    return f"{'-' if q < 0 else ''}{cmd}{{{abs(q.numerator)}}}{{{q.denominator}}}"


def trinome(a, b, c, var="x"):
    """ax² + bx + c en LaTeX, sans « + - », « 1x », « + 0 »."""
    terms = []
    for coef, mono in ((a, f"{var}^2"), (b, var), (c, "")):
        coef = Fraction(coef)
        if coef == 0:
            continue
        sign = "-" if coef < 0 else "+"
        mag = abs(coef)
        body = fr(mag) if (mono == "" or mag != 1) else ""
        terms.append((sign, body + mono))
    if not terms:
        return "0"
    first_sign, first = terms[0]
    out = ("-" if first_sign == "-" else "") + first
    for s, t in terms[1:]:
        out += f" {s} {t}"
    return out


from premiere_specifique.banque_commun import code  # noqa: E402,F401  (code Python dans les cours)


def points(values, label_every=None, start=0, **kw):
    """Points (n ; u_n) d'une suite, étiquetés « u₀ », « u₁ »… (indices en
    caractères Unicode, convertis par geomSvg.js)."""
    subs = "₀₁₂₃₄₅₆₇₈₉"
    out = []
    for k, v in enumerate(values, start):
        lab = "u" + "".join(subs[int(d)] for d in str(k)) if (label_every and (k - start) % label_every == 0) else ""
        out.append(pt(k, v, lab, **kw))
    return out


def calc(texte, expr=""):
    """Étape de calcul : `texte` (phrase, formules entre $…$) et `expr`
    (formule seule, sans $). Refuse une commande LaTeX hors délimiteurs dans
    `texte` : elle s'afficherait brute à l'élève."""
    import re as _re
    # Formule seule (sans $) : commande LaTeX, virgule décimale {,} ou
    # exposant ^ — sinon « 129{,}45 » ou « x^2 » s'afficheraient bruts.
    if "$" not in texte and not expr and _re.search(r"\\|\{,\}|\^", texte):
        return {"expr": texte, "texte": ""}  # formule seule : rendue comme telle
    outside = _re.sub(r"\$[^$]*\$", "", texte)
    assert "\\" not in outside, f"commande LaTeX hors formule dans le texte : {texte[:80]!r}"
    return {"expr": expr, "texte": texte}
