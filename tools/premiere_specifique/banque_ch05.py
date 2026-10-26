"""Chapitre 5 (ancien chapitre 3) — Dérivation : banque curée.

Exercices historiques (identifiants conservés, banque_ch03_historiques.py) :
- « Calculer la dérivée » : relu par une famille générique qui identifie la
  structure (polynôme, fonction usuelle, somme, produit, quotient, inverse,
  puissance d'une expression affine), rédige la correction règle par règle et
  recalcule la dérivée avec SymPy ;
- notion « Composition de fonctions et dérivation » retirée du programme 2026
  (seule la dérivée de t ↦ e^{at} reste au programme, voir Ch. 5) : ses 20
  exercices sont rattachés à « Opérations et dérivation » et traités avec les
  outils du programme : (ax + b)ⁿ par produit ou développement, 1/(ax + b) par
  la règle de l'inverse ; √(ax + b) (non dérivable avec ces outils) devient
  (ax + b)√x, dérivée par la règle du produit ;
- taux de variation et tangentes : textes réécrits, valeurs recalculées.

Nouveaux exercices : bloc 63 000.
"""
import re

import sympy as sp

from premiere_specifique.banque_ch05_historiques import HISTORIQUES
from premiere_specifique.banque_commun import E, S, code, fr, lin, par, poly_tex

CHAPTER_NUMBER = 5  # ancien chapitre 3 (adaptation au manuel « Première ES/L », 2026-10-26)
N1 = "Nombre dérivé. Tangente"
N2 = "Approximation affine et dérivabilité"
N3 = "Fonction dérivée"
N4 = "Opérations et dérivation"
NOTIONS = (N1, N2, N3, N4)
NOTION_IDS = (
    "nombre-derive.-tangente",
    "approximation-affine-et-derivabilite",
    "fonction-derivee",
    "operations-et-derivation",
)

x, h = sp.symbols("x h")
R = "\\mathbb{R}"
POS = "]0 ; +\\infty["


# ── LaTeX ↔ SymPy ───────────────────────────────────────────────────────────


def _group(s, i):
    """Contenu du groupe {…} qui commence en s[i] == '{' ; renvoie (contenu, fin)."""
    assert s[i] == "{"
    depth = 0
    for j in range(i, len(s)):
        if s[j] == "{":
            depth += 1
        elif s[j] == "}":
            depth -= 1
            if depth == 0:
                return s[i + 1:j], j + 1
    raise ValueError(s)


def tex2py(s):
    s = s.replace("\\left", "").replace("\\right", "").replace(" ", "")
    out, i = "", 0
    while i < len(s):
        if s.startswith("\\dfrac", i) or s.startswith("\\frac", i):
            i += 6 if s.startswith("\\dfrac", i) else 5
            a, i = _group(s, i)
            b, i = _group(s, i)
            out += f" (({tex2py(a)})/({tex2py(b)})) "
        elif s.startswith("\\sqrt", i):
            a, i = _group(s, i + 5)
            out += f" sqrt({tex2py(a)}) "
        elif s[i] == "^":
            if s[i + 1] == "{":
                a, i = _group(s, i + 1)
            else:
                a, i = s[i + 1], i + 2
            out += f"**({tex2py(a)})"
        else:
            out += s[i]
            i += 1
    return out


_TR = sp.parsing.sympy_parser.standard_transformations + (sp.parsing.sympy_parser.implicit_multiplication_application,)


def parse(s):
    return sp.parsing.sympy_parser.parse_expr(tex2py(s), local_dict={"x": x, "h": h, "sqrt": sp.sqrt}, transformations=_TR)


def ptex(expr):
    """Polynôme en x écrit proprement (coefficients rationnels)."""
    p = sp.Poly(sp.expand(expr), x)
    return poly_tex([sp.Rational(c) for c in p.all_coeffs()])


def stex(expr):
    s = sp.latex(expr)
    return s.replace("\\frac", "\\dfrac")


def _same(a, b):
    return sp.simplify(a - b) == 0


def _split_top(s, sep):
    """Découpe s au niveau de profondeur 0 (parenthèses et accolades)."""
    parts, depth, cur, i = [], 0, "", 0
    while i < len(s):
        c = s[i]
        if c in "({":
            depth += 1
        elif c in ")}":
            depth -= 1
        if depth == 0 and s.startswith(sep, i):
            parts.append(cur)
            cur = ""
            i += len(sep)
            continue
        cur += c
        i += 1
    parts.append(cur)
    return parts


def _is_linear(e):
    return sp.Poly(e, x).degree() == 1 if e.is_polynomial(x) else False


# ── Famille générique « calculer la dérivée » ───────────────────────────────


def _derivee(i, name, dom, expr_tex, notion_code):
    t = expr_tex.strip()
    f = parse(t)
    level, notion = 1, (N3 if notion_code == "Fon" else N4)
    dom_txt = dom
    t = re.sub(r"^1(?=\\sqrt)", "", t)  # « 1\sqrt{x} » historique -> « \sqrt{x} »
    new_tex = t
    m_frac = re.fullmatch(r"\\dfrac\{(.+)\}\{(.+)\}", t)
    m_pow = re.fullmatch(r"\((.+)\)\^\{(\d+)\}", t)
    m_sqrt = re.fullmatch(r"(-?\d*)\\sqrt\{(.+)\}", t)
    if m_sqrt and m_sqrt.group(2) != "x":
        # √(ax + b) : réécrit en (ax + b)√x (règle du produit, programme 2026)
        inner = parse(m_sqrt.group(2))
        a_, b_ = sp.Poly(inner, x).all_coeffs() if sp.Poly(inner, x).degree() == 1 else (inner.coeff(x), 0)
        lin = ptex(inner)
        new_tex = (f"({lin})\\sqrt{{x}}" if sp.Poly(inner, x).length() > 1 else f"{'-' if lin.startswith('-') else ''}x\\sqrt{{x}}")
        f = inner * sp.sqrt(x)
        d = sp.diff(f, x)
        num = sp.expand(sp.simplify(d * 2 * sp.sqrt(x)))
        coeffs = sp.Poly(num, x).all_coeffs()
        ans = (f"\\dfrac{{{ptex(num / 2)}}}{{\\sqrt{{x}}}}" if all(sp.Integer(c) % 2 == 0 for c in coeffs)
               else f"\\dfrac{{{ptex(num)}}}{{2\\sqrt{{x}}}}")
        steps = (f"$f = u \\times v$ avec $u(x) = {lin}$ et $v(x) = \\sqrt{{x}}$ : $u'(x) = {stex(a_)}$ et $v'(x) = \\dfrac{{1}}{{2\\sqrt{{x}}}}$ (sur $]0 ; +\\infty[$).",
                 f"$f'(x) = u'v + uv' = {'' if a_ == 1 else ('-' if a_ == -1 else stex(a_))}\\sqrt{{x}} + \\dfrac{{{lin}}}{{2\\sqrt{{x}}}}$.",
                 f"On réduit au même dénominateur $2\\sqrt{{x}}$, sachant que $\\sqrt{{x}} = \\dfrac{{x}}{{\\sqrt{{x}}}} = \\dfrac{{2x}}{{2\\sqrt{{x}}}}$ : $f'(x) = {ans}$.")
        level, notion, dom_txt = 3, N4, POS
        assert _same(parse(ans), d)
    elif m_pow and _is_linear(parse(m_pow.group(1))):
        u = parse(m_pow.group(1))
        n = int(m_pow.group(2))
        a_ = sp.Poly(u, x).coeff_monomial(x)
        d = sp.diff(f, x)
        monome = sp.Poly(u, x).length() == 1
        ans = ptex(d) if monome else f"{stex(n * a_)}({m_pow.group(1)})" + (f"^{{{n - 1}}}" if n > 2 else "")
        if n == 2:
            steps = (f"On écrit $f = u \\times u$ avec $u(x) = {m_pow.group(1)}$ et $u'(x) = {stex(a_)}$.",
                     f"Règle du produit : $f'(x) = u'u + uu' = 2u'u = 2 \\times {par(a_)} \\times ({m_pow.group(1)})$.",
                     f"$f'(x) = {ans}$ (contrôle en développant : $f(x) = {ptex(f)}$ et $f'(x) = {ptex(d)}$).")
            level = 2
        else:
            steps = (f"On développe : $f(x) = {ptex(f)}$.",
                     f"On dérive terme à terme : $f'(x) = {ptex(d)}$.",
                     (f"Ici $({m_pow.group(1)})^{{{n}}} = {ptex(f)}$, donc $f'(x) = {ans}$." if monome else
                      f"Ce résultat se factorise : $f'(x) = {ans}$ (on le vérifie en développant ${ans}$)."))
            level = 3
        notion = N4
        assert _same(parse(ans), d)
    elif m_frac and parse(m_frac.group(1)).is_number:
        k = parse(m_frac.group(1))
        v = parse(m_frac.group(2))
        if v.is_polynomial(x) and sp.Poly(v, x).length() == 1:
            # k/(c x) : fonction inverse
            c = sp.Poly(v, x).coeff_monomial(x)
            kk = k / c
            d = sp.diff(f, x)
            c_ = abs(sp.Rational(kk))
            ans = f"{'-' if kk > 0 else ''}\\dfrac{{{c_.p}}}{{{'' if c_.q == 1 else c_.q}x^2}}"
            steps = (f"$f(x) = {fr(kk)} \\times \\dfrac{{1}}{{x}}$ sur ${R} \\setminus \\{{0\\}}$.",
                     "$\\left(\\dfrac{1}{x}\\right)' = -\\dfrac{1}{x^2}$ et la constante multiplicative se conserve.",
                     f"$f'(x) = {fr(kk)} \\times \\left(-\\dfrac{{1}}{{x^2}}\\right) = {ans}$.")
            if not dom_txt:
                dom_txt = f"{R} \\setminus \\left\\{{0\\right\\}}"
        else:
            vt = m_frac.group(2)
            vp = sp.diff(v, x)
            d = sp.diff(f, x)
            numer = sp.simplify(-k * vp)
            ans = f"{'-' if numer < 0 else ''}\\dfrac{{{stex(abs(numer))}}}{{({vt})^2}}"
            root = sp.solve(v, x)[0]
            dom_txt = f"{R} \\setminus \\left\\{{{stex(root)}\\right\\}}"
            kt = "" if k == 1 else stex(k) + " \\times "
            steps = (f"$f = {kt}\\dfrac{{1}}{{v}}$ avec $v(x) = {vt}$, qui ne s'annule pas sur $D = {dom_txt}$ ; $v'(x) = {stex(vp)}$.",
                     "Règle de l'inverse : $\\left(\\dfrac{1}{v}\\right)' = -\\dfrac{v'}{v^2}$.",
                     f"$f'(x) = {kt}\\left(-\\dfrac{{{stex(vp)}}}{{({vt})^2}}\\right) = {ans}$.")
            level, notion = 2, N4
        assert _same(parse(ans), d)
    elif m_frac:
        ut, vt = m_frac.group(1), m_frac.group(2)
        u, v = parse(ut), parse(vt)
        up, vp = sp.diff(u, x), sp.diff(v, x)
        numer = sp.expand(up * v - u * vp)
        d = sp.diff(f, x)
        ans = f"\\dfrac{{{ptex(numer)}}}{{({vt})^2}}"
        steps = (f"$f = \\dfrac{{u}}{{v}}$ avec $u(x) = {ut}$, $v(x) = {vt}$ ; $u'(x) = {ptex(up)}$ et $v'(x) = {ptex(vp)}$.",
                 "Règle du quotient : $\\left(\\dfrac{u}{v}\\right)' = \\dfrac{u'v - uv'}{v^2}$, valable là où $v$ ne s'annule pas.",
                 f"Numérateur : ${mulf(up, vt)} - ({ut}) \\times {par_tex(vp)} = {ptex(numer)}$.",
                 f"$f'(x) = {ans}$.")
        level = 3
        assert _same(parse(ans), d)
    elif m_sqrt:
        g = m_sqrt.group(1)
        k = int(g) if g not in ("", "-") else (1 if g == "" else -1)
        d = sp.diff(f, x)
        kk = sp.Rational(k, 2)
        sign = "-" if kk < 0 else ""
        ans = (f"{sign}\\dfrac{{{abs(k)}}}{{2\\sqrt{{x}}}}" if kk.q == 2 else f"{sign}\\dfrac{{{abs(kk)}}}{{\\sqrt{{x}}}}")
        steps = (f"La fonction racine carrée est dérivable sur $]0 ; +\\infty[$ (mais pas en $0$), avec $(\\sqrt{{x}})' = \\dfrac{{1}}{{2\\sqrt{{x}}}}$.",
                 f"$f'(x) = {stex(k)} \\times \\dfrac{{1}}{{2\\sqrt{{x}}}} = {ans}$.")
        assert _same(parse(ans), d)
    else:
        m_prod = re.fullmatch(r"\(([^()]+)\)\(([^()]+)\)", t)
        plus = re.split(r" \+ (?=\()", t) if t.startswith("(") else [t]
        d = sp.diff(f, x)
        if m_prod:
            ut, vt = m_prod.group(1), m_prod.group(2)
            u, v = parse(ut), parse(vt)
            up, vp = sp.diff(u, x), sp.diff(v, x)
            ans = ptex(d)
            steps = (f"$f = u \\times v$ avec $u(x) = {ut}$ et $v(x) = {vt}$ ; $u'(x) = {ptex(up)}$, $v'(x) = {ptex(vp)}$.",
                     "Règle du produit : $(uv)' = u'v + uv'$.",
                     f"$f'(x) = {mulf(up, vt)} + ({ut}) \\times {par_tex(vp)} = {ans}$.")
            level = 2
        elif len(plus) >= 2 and t.startswith("("):
            ans = ptex(d)
            if len(plus) == 2 and all(")(" not in p for p in plus):
                ut, vt = plus[0][1:-1], plus[1][1:-1]
                steps = (f"$f = u + v$ avec $u(x) = {ut}$ et $v(x) = {vt}$ : la dérivée d'une somme est la somme des dérivées.",
                         f"$u'(x) = {ptex(sp.diff(parse(ut), x))}$ et $v'(x) = {ptex(sp.diff(parse(vt), x))}$.",
                         f"$f'(x) = u'(x) + v'(x) = {ans}$.")
            else:
                steps = ("La dérivée d'une somme est la somme des dérivées : on dérive chaque bloc.",
                         " ; ".join(f"$\\left[{p}\\right]' = {ptex(sp.diff(parse(p), x))}$"
                                    + (" (règle du produit)" if ")(" in p else "") for p in plus) + ".",
                         f"$f'(x) = {ans}$.")
            level = 1 if all(")(" not in p for p in plus) else 2
        else:
            ans = ptex(d)
            deg = sp.Poly(f, x).degree()
            steps = ("On dérive terme à terme avec $(x^n)' = nx^{n-1}$, $(ax)' = a$ et $(c)' = 0$ (une constante disparaît).",
                     f"$f'(x) = {ans}$.")
            level = 1 if deg <= 3 else 2
        assert _same(parse(ans), d)
    dom_phrase = f" définie sur ${dom_txt}$" if dom_txt else ""
    return E(i, notion, level,
             f"Calculer la dérivée de la fonction ${name}$ définie{(' sur $' + dom_txt + '$') if dom_txt else ''} par ${name}(x) = {new_tex}$."
             .replace(f"définie définie", "définie") if dom_txt else
             f"Calculer la dérivée de la fonction ${name}$ définie par ${name}(x) = {new_tex}$ (là où elle est dérivable).",
             f"${name}'(x) = {ans}$.",
             "Repère d'abord la structure (somme, produit, quotient, fonction usuelle) avant d'appliquer une règle.",
             S(*steps),
             checks=(ans,))


def mulf(k, factor_tex):
    """k × (facteur) sans coefficient 1 écrit."""
    if k == 1:
        return f"({factor_tex})"
    if k == -1:
        return f"-({factor_tex})"
    return f"{par_tex(k)}({factor_tex})"


def par_tex(e):
    s = ptex(e) if e.is_polynomial(x) else stex(e)
    return f"({s})" if (s.startswith("-") or " " in s.strip()) else s


def _taux(i, expr_tex, a):
    f = parse(expr_tex)
    diff = sp.expand(f.subs(x, a + h) - f.subs(x, a))
    rate = sp.expand(diff / h)
    lim = rate.subs(h, 0)
    fa = f.subs(x, a)
    return E(i, N1, 2,
             f"Soit $f$ la fonction définie sur ${R}$ par $f(x) = {expr_tex}$. Pour $h \\neq 0$, exprimer le taux de variation "
             f"$\\dfrac{{f({a} + h) - f({a})}}{{h}}$ en fonction de $h$, puis en déduire $f'({a})$.",
             f"$\\dfrac{{f({a} + h) - f({a})}}{{h}} = {stex(rate)}$ et $f'({a}) = {lim}$.".replace("+ -", "- "),
             "Développe $f(a + h)$, soustrais $f(a)$ : tous les termes restants contiennent $h$.",
             S(f"$f({a}) = {fa}$.",
               f"$f({a} + h) - f({a}) = {stex(diff)}$ (le terme constant disparaît).",
               f"On divise par $h \\neq 0$ : le taux vaut ${stex(rate)}$.",
               f"Quand $h$ se rapproche de $0$, le taux se rapproche de ${lim}$ : $f'({a}) = {lim}$."),
             checks=(f"f'({a}) = {lim}",))


def _tangente(i, expr_tex, a):
    f = parse(expr_tex)
    fa, dfa = f.subs(x, a), sp.diff(f, x).subs(x, a)
    tan = sp.expand(dfa * (x - a) + fa)
    eq = ptex(tan) if tan != 0 else "0"
    return E(i, N1, 1,
             f"Soit $f$ la fonction définie sur ${R}$ par $f(x) = {expr_tex}$. Déterminer une équation de la tangente à sa courbe "
             f"au point d'abscisse ${a}$.",
             f"$y = {eq}$.",
             "Équation de la tangente en $a$ : $y = f'(a)(x - a) + f(a)$.",
             S(f"$f({a}) = {fa}$.", f"$f'(x) = {ptex(sp.diff(f, x))}$, donc $f'({a}) = {dfa}$.",
               f"$y = {'' if dfa == 1 else ('-' if dfa == -1 else dfa)}({lin(a)}){'' if fa == 0 else (' + ' if fa > 0 else ' - ') + str(abs(fa))}$, soit $y = {eq}$."),
             checks=(f"y = {eq}",))


_FAMILIES = {"derivee": _derivee, "taux": _taux, "tangente": _tangente}
def _build(i, fam, p):
    try:
        return _FAMILIES[fam](i, *p)
    except AssertionError as exc:
        raise AssertionError(f"exercice {i} : {p}") from exc


HIST = [_build(i, fam, p) for i, fam, p in HISTORIQUES]

MANUELS = [
    E(2246, N1, 1,
      "La tangente à la courbe d'une fonction $f$ au point $A$ d'abscisse $2$ passe par les points $(0 ; 1)$ et $(2 ; 5)$. Déterminer $f'(2)$.",
      "$f'(2) = 2$.",
      "Le nombre dérivé est le coefficient directeur de la tangente.",
      S("$f'(2)$ est la pente de la tangente en $A$.", "$f'(2) = \\dfrac{5 - 1}{2 - 0} = 2$."),
      checks=("f'(2) = 2",)),
    E(2247, N1, 2,
      "La courbe d'une fonction $g$, dérivable sur $[-3 ; 4]$, monte sur $[-3 ; 0]$, admet une tangente horizontale au point d'abscisse $0$, "
      "puis descend sur $[0 ; 4]$. Que peut-on dire du signe de $g'(-2)$, de $g'(0)$ et de $g'(3)$ ?",
      "$g'(-2) > 0$ (ou nul), $g'(0) = 0$ et $g'(3) < 0$ (ou nul) ; pour une courbe qui monte franchement, $g'(-2) > 0$.",
      "Le signe du nombre dérivé est celui de la pente de la tangente.",
      S("En $-2$, la courbe monte : la tangente a une pente positive.", "En $0$, la tangente est horizontale : pente nulle, $g'(0) = 0$.",
        "En $3$, la courbe descend : pente négative."),
      checks=("g'(0) = 0",)),
    E(2248, N1, 2,
      "On a tracé la tangente à la courbe d'une fonction $h$ au point $B$ d'abscisse $-1$ ; elle passe par $(-1 ; 3)$ et $(1 ; -1)$. "
      "Déterminer une équation de cette tangente, puis $h'(-1)$ et $h(-1)$.",
      "La tangente a pour équation $y = -2x + 1$ ; $h'(-1) = -2$ et $h(-1) = 3$.",
      "Le point de contact appartient à la fois à la courbe et à la tangente.",
      S("Pente : $\\dfrac{-1 - 3}{1 - (-1)} = -2$.", "$y = -2x + p$ passe par $(-1 ; 3)$ : $3 = 2 + p$, $p = 1$.",
        "$h'(-1) = -2$ (pente) et $h(-1) = 3$ (ordonnée du point de contact)."),
      checks=("y = -2x + 1",)),
    E(2249, N1, 1,
      "Au point d'abscisse $1$, la courbe d'une fonction $k$ est presque plate (tangente de faible pente positive) ; au point d'abscisse $3$, "
      "elle monte très raide. Un élève affirme que $k'(1) > k'(3)$. A-t-il raison ?",
      "Non : $k'(1) < k'(3)$.",
      "Compare les pentes des deux tangentes.",
      S("$k'(1)$ et $k'(3)$ sont les pentes des tangentes.", "Une tangente presque horizontale a une pente faible ; une tangente raide, une pente forte.",
        "Donc $k'(1) < k'(3)$ : l'élève a tort."),
      checks=("k'(1) < k'(3)",)),
]

LEGACY_IDS = tuple(e.id for e in HIST + MANUELS)


def _chk(expr, ans):
    return lambda: None if _same(parse(expr), parse(ans)) else "valeur fausse"


NOUVEAUX = [
    # N1 — taux de variation, nombre dérivé, tangente
    E(63101, N1, 1,
      "Soit $f(x) = x^2$. Calculer le taux de variation de $f$ entre $1$ et $3$ et interpréter graphiquement.",
      "Le taux vaut $4$ : c'est le coefficient directeur de la sécante passant par $(1 ; 1)$ et $(3 ; 9)$.",
      "Taux de variation entre $a$ et $b$ : $\\dfrac{f(b) - f(a)}{b - a}$.",
      S("$\\dfrac{f(3) - f(1)}{3 - 1} = \\dfrac{9 - 1}{2} = 4$.", "C'est la pente de la droite qui joint les points d'abscisses $1$ et $3$ de la courbe."),
      checks=("$4$",)),
    E(63102, N1, 2,
      "Une bille lâchée parcourt $d(t) = 5t^2$ mètres en $t$ secondes. Calculer sa vitesse moyenne entre $t = 2$ et $t = 2 + h$, "
      "puis sa vitesse instantanée à $t = 2$.",
      "Vitesse moyenne : $20 + 5h$ m/s ; vitesse instantanée : $d'(2) = 20$ m/s.",
      "La vitesse moyenne est un taux de variation ; la vitesse instantanée est sa limite.",
      S("$d(2 + h) - d(2) = 5(4 + 4h + h^2) - 20 = 20h + 5h^2$.", "Vitesse moyenne : $\\dfrac{20h + 5h^2}{h} = 20 + 5h$.",
        "Quand $h$ se rapproche de $0$ : $20$ m/s."),
      checks=("20 + 5h", "20$ m/s")),
    E(63103, N1, 3,
      "Soit $f(x) = \\dfrac{1}{x}$ sur $]0 ; +\\infty[$. Montrer que $\\dfrac{f(2 + h) - f(2)}{h} = -\\dfrac{1}{2(2 + h)}$, puis en déduire $f'(2)$.",
      "$f'(2) = -\\dfrac{1}{4}$.",
      "Réduis $\\dfrac{1}{2 + h} - \\dfrac{1}{2}$ au même dénominateur.",
      S("$\\dfrac{1}{2 + h} - \\dfrac{1}{2} = \\dfrac{2 - (2 + h)}{2(2 + h)} = \\dfrac{-h}{2(2 + h)}$.",
        "En divisant par $h$ : $-\\dfrac{1}{2(2 + h)}$.", "Quand $h$ tend vers $0$ : $-\\dfrac{1}{4}$."),
      checks=("-\\dfrac{1}{4}",), verify=_chk("-1/4", "-\\dfrac{1}{4}")),
    E(63104, N1, 3,
      "Soit $f(x) = x^2 - x$. En quel point la tangente à la courbe est-elle parallèle à la droite d'équation $y = 3x + 1$ ? Donner l'équation de cette tangente.",
      "Au point $(2 ; 2)$ ; la tangente a pour équation $y = 3x - 4$.",
      "Deux droites parallèles ont le même coefficient directeur.",
      S("$f'(a) = 2a - 1 = 3 \\iff a = 2$.", "$f(2) = 2$.", "$y = 3(x - 2) + 2 = 3x - 4$."),
      checks=("y = 3x - 4",)),
    E(63105, N1, 2,
      "Soit $f(x) = x^2 - 6x + 5$. En quel point la courbe a-t-elle une tangente horizontale ?",
      "Au point $(3 ; -4)$.",
      "Une tangente horizontale a un coefficient directeur nul.",
      S("$f'(x) = 2x - 6$.", "$f'(a) = 0 \\iff a = 3$.", "$f(3) = 9 - 18 + 5 = -4$ : c'est le sommet de la parabole."),
      checks=("(3 ; -4)",)),
    E(63106, N1, 4,
      "Soit $f(x) = x^2 + 1$. Déterminer les tangentes à la courbe de $f$ qui passent par l'origine du repère.",
      "Les tangentes aux points d'abscisses $1$ et $-1$ : $y = 2x$ et $y = -2x$.",
      "Écris l'équation de la tangente en un point d'abscisse $a$ quelconque, puis impose qu'elle passe par $(0 ; 0)$.",
      S("Tangente en $a$ : $y = 2a(x - a) + a^2 + 1 = 2ax - a^2 + 1$.", "Elle passe par $O$ si $0 = -a^2 + 1$, soit $a = 1$ ou $a = -1$.",
        "On obtient $y = 2x$ et $y = -2x$."),
      checks=("y = 2x", "y = -2x")),
    E(63107, N1, 1,
      "La courbe d'une fonction $f$ passe par $A(1 ; 3)$ et $f'(1) = -2$. Donner un second point de la tangente en $A$ pour pouvoir la tracer.",
      "Par exemple $(2 ; 1)$ : on avance de $1$ et on descend de $2$.",
      "La pente $-2$ signifie : quand $x$ augmente de $1$, $y$ diminue de $2$.",
      S("Équation : $y = -2(x - 1) + 3 = -2x + 5$.", "Pour $x = 2$ : $y = 1$."),
      checks=("(2 ; 1)",)),
    E(63108, N1, 4,
      "Soit $f(x) = \\sqrt{x}$. Montrer que pour $h > 0$, $\\dfrac{f(4 + h) - f(4)}{h} = \\dfrac{1}{\\sqrt{4 + h} + 2}$, puis en déduire $f'(4)$.",
      "$f'(4) = \\dfrac{1}{4}$.",
      "Multiplie numérateur et dénominateur par la quantité conjuguée $\\sqrt{4 + h} + 2$.",
      S("$\\dfrac{\\sqrt{4 + h} - 2}{h} = \\dfrac{(\\sqrt{4 + h} - 2)(\\sqrt{4 + h} + 2)}{h(\\sqrt{4 + h} + 2)} = \\dfrac{h}{h(\\sqrt{4 + h} + 2)}$.",
        "Après simplification par $h$ : $\\dfrac{1}{\\sqrt{4 + h} + 2}$.", "Quand $h$ tend vers $0$ : $\\dfrac{1}{2 + 2} = \\dfrac{1}{4}$."),
      checks=("\\dfrac{1}{4}",)),

    # N2 — approximation affine, dérivabilité
    E(63201, N2, 1,
      "Soit $f(x) = x^2$. Écrire l'approximation affine de $f(1 + h)$ pour $h$ proche de $0$, puis en déduire une valeur approchée de $1{,}01^2$.",
      "$f(1 + h) \\approx 1 + 2h$ ; $1{,}01^2 \\approx 1{,}02$ (valeur exacte $1{,}0201$).",
      "$f(a + h) \\approx f(a) + f'(a)h$.",
      S("$f(1) = 1$ et $f'(1) = 2$.", "$f(1 + h) \\approx 1 + 2h$.", "Avec $h = 0{,}01$ : $1{,}02$ ; l'erreur, $h^2 = 0{,}0001$, est très petite."),
      checks=("1 + 2h", "1{,}02")),
    E(63202, N2, 2,
      "Donner l'approximation affine de $\\sqrt{1 + h}$ pour $h$ proche de $0$, puis une valeur approchée de $\\sqrt{1{,}02}$.",
      "$\\sqrt{1 + h} \\approx 1 + \\dfrac{h}{2}$ ; $\\sqrt{1{,}02} \\approx 1{,}01$ (calculatrice : $1{,}00995$).",
      "Utilise $(\\sqrt{x})' = \\dfrac{1}{2\\sqrt{x}}$ en $a = 1$.",
      S("$f(1) = 1$ et $f'(1) = \\dfrac{1}{2}$.", "$\\sqrt{1 + h} \\approx 1 + \\dfrac{1}{2}h$.", "Pour $h = 0{,}02$ : $1{,}01$."),
      checks=("1{,}01",)),
    E(63203, N2, 2,
      "Donner l'approximation affine de $\\dfrac{1}{1 + h}$ pour $h$ proche de $0$, puis une valeur approchée de $\\dfrac{1}{1{,}05}$.",
      "$\\dfrac{1}{1 + h} \\approx 1 - h$ ; $\\dfrac{1}{1{,}05} \\approx 0{,}95$ (valeur exacte $0{,}952\\ldots$).",
      "Utilise $\\left(\\dfrac{1}{x}\\right)' = -\\dfrac{1}{x^2}$ en $a = 1$.",
      S("$f(1) = 1$ et $f'(1) = -1$.", "$\\dfrac{1}{1 + h} \\approx 1 - h$.", "Pour $h = 0{,}05$ : $0{,}95$."),
      checks=("1 - h", "0{,}95")),
    E(63204, N2, 2,
      "Le coût de production de $q$ objets est $C(q) = 0{,}1q^2 + 5q + 100$ euros. Calculer le coût marginal $C'(50)$ et comparer avec le coût "
      "réel de fabrication du $51$e objet, $C(51) - C(50)$.",
      "$C'(50) = 15$ € ; $C(51) - C(50) = 15{,}10$ € : le coût marginal en est une très bonne approximation.",
      "Le coût marginal est le nombre dérivé du coût.",
      S("$C'(q) = 0{,}2q + 5$, donc $C'(50) = 15$.", "$C(51) = 615{,}10$ et $C(50) = 600$ : différence $15{,}10$.",
        "$C(51) - C(50) \\approx C'(50) \\times 1$ : c'est l'approximation affine avec $h = 1$."),
      checks=("15{,}10",), verify=lambda: None if abs((0.1 * 51 ** 2 + 255 + 100) - (0.1 * 2500 + 250 + 100) - 15.1) < 1e-9 else "faux"),
    E(63205, N2, 3,
      "Étudier la dérivabilité en $0$ de la fonction valeur absolue $f(x) = |x|$, à l'aide du taux de variation $\\dfrac{f(h) - f(0)}{h}$.",
      "Le taux vaut $1$ si $h > 0$ et $-1$ si $h < 0$ : il ne se rapproche d'aucun nombre unique, $f$ n'est pas dérivable en $0$.",
      "Distingue $h > 0$ et $h < 0$.",
      S("$\\dfrac{|h| - 0}{h} = \\dfrac{|h|}{h}$.", "Pour $h > 0$ : $1$ ; pour $h < 0$ : $-1$.",
        "Les deux valeurs ne se rejoignent pas : la courbe a un « point anguleux » en $0$, pas de tangente."),
      checks=()),
    E(63206, N2, 3,
      "Montrer que la fonction racine carrée n'est pas dérivable en $0$ en étudiant $\\dfrac{\\sqrt{h} - \\sqrt{0}}{h}$ pour $h > 0$.",
      "Le taux vaut $\\dfrac{1}{\\sqrt{h}}$, qui devient aussi grand que l'on veut quand $h$ se rapproche de $0$ : pas de nombre dérivé en $0$.",
      "Simplifie $\\dfrac{\\sqrt{h}}{h}$.",
      S("$\\dfrac{\\sqrt{h}}{h} = \\dfrac{1}{\\sqrt{h}}$.", "Pour $h = 10^{-4}$ : $100$ ; pour $h = 10^{-8}$ : $10\\,000$.",
        "Le taux ne se rapproche d'aucun réel : la tangente en $0$ est verticale, $\\sqrt{\\,}$ n'est pas dérivable en $0$."),
      checks=()),
    E(63207, N2, 2,
      "Le programme Python suivant affiche la liste des pentes des sécantes à la courbe de $f(x) = x^2$ entre $1$ et $1 + h$ : "
      + code("def f(x): return x**2") + " puis " + code("print([(f(1 + h) - f(1)) / h for h in [0.1, 0.01, 0.001]])")
      + ". Quelle liste obtient-on (aux arrondis près) ? Que conjecturer ?",
      "Environ $[2{,}1 ; 2{,}01 ; 2{,}001]$ : on conjecture que $f'(1) = 2$.",
      "Calcule $\\dfrac{(1 + h)^2 - 1}{h}$.",
      S("$\\dfrac{(1 + h)^2 - 1}{h} = 2 + h$.", "Pour $h = 0{,}1$, $0{,}01$, $0{,}001$ : $2{,}1$, $2{,}01$, $2{,}001$.",
        "Les pentes des sécantes se rapprochent de $2$, pente de la tangente."),
      checks=("2{,}01",)),
    E(63208, N2, 2,
      "Soit $f(x) = x^3$. Donner une valeur approchée de $2{,}01^3$ grâce à l'approximation affine en $2$, et la comparer à la valeur exacte.",
      "$2{,}01^3 \\approx 8{,}12$ ; valeur exacte $8{,}120601$.",
      "$f(2 + h) \\approx f(2) + f'(2)h$ avec $f'(x) = 3x^2$.",
      S("$f(2) = 8$ et $f'(2) = 12$.", "$f(2{,}01) \\approx 8 + 12 \\times 0{,}01 = 8{,}12$.", "Écart avec la valeur exacte : environ $0{,}0006$."),
      checks=("8{,}12",)),
    E(63209, N2, 4,
      "On approche $f(a + h)$ par $f(a) + f'(a)h$. Pour $f(x) = x^2$, exprimer l'erreur commise en fonction de $h$ et expliquer pourquoi "
      "l'approximation est « d'autant meilleure que $h$ est petit ».",
      "L'erreur vaut exactement $h^2$ : elle est négligeable devant $h$ quand $h$ est proche de $0$ (pour $h = 0{,}01$, $0{,}0001$).",
      "Développe $(a + h)^2$.",
      S("$(a + h)^2 = a^2 + 2ah + h^2$ et $f(a) + f'(a)h = a^2 + 2ah$.", "L'erreur est $h^2$.",
        "$\\dfrac{h^2}{h} = h$ se rapproche de $0$ : l'erreur devient négligeable par rapport à $h$."),
      checks=("h^2",)),

    # N3 — fonctions dérivées usuelles
    E(63301, N3, 1,
      "Calculer les dérivées de $x \\mapsto x^5$, de $x \\mapsto \\dfrac{1}{x^2}$ et de $x \\mapsto \\dfrac{1}{x^3}$ (sur $]0 ; +\\infty[$).",
      "$5x^4$ ; $-\\dfrac{2}{x^3}$ ; $-\\dfrac{3}{x^4}$.",
      "Écris $\\dfrac{1}{x^2} = x^{-2}$ et utilise $(x^n)' = nx^{n-1}$, valable pour $n$ entier relatif.",
      S("$(x^5)' = 5x^4$.", "$(x^{-2})' = -2x^{-3} = -\\dfrac{2}{x^3}$.", "$(x^{-3})' = -3x^{-4} = -\\dfrac{3}{x^4}$."),
      checks=("-\\dfrac{2}{x^3}",), verify=_chk("diff(x**-2, x)", "-\\dfrac{2}{x^3}")),
    E(63302, N3, 2,
      "Calculer la dérivée de $f(x) = \\dfrac{3}{x^2} - x^4$ sur $]0 ; +\\infty[$.",
      "$f'(x) = -\\dfrac{6}{x^3} - 4x^3$.",
      "$\\dfrac{3}{x^2} = 3x^{-2}$.",
      S("$(3x^{-2})' = -6x^{-3} = -\\dfrac{6}{x^3}$.", "$(x^4)' = 4x^3$.", "$f'(x) = -\\dfrac{6}{x^3} - 4x^3$."),
      checks=("-\\dfrac{6}{x^3} - 4x^3",), verify=_chk("diff(3/x**2 - x**4, x)", "-\\dfrac{6}{x^3} - 4x^3")),
    E(63303, N3, 3,
      "Vrai ou faux : pour tout $x > 0$, $(\\sqrt{x})' = \\dfrac{\\sqrt{x}}{2x}$.",
      "Vrai : $\\dfrac{1}{2\\sqrt{x}} = \\dfrac{\\sqrt{x}}{2\\sqrt{x}\\sqrt{x}} = \\dfrac{\\sqrt{x}}{2x}$.",
      "Multiplie numérateur et dénominateur de $\\dfrac{1}{2\\sqrt{x}}$ par $\\sqrt{x}$.",
      S("$(\\sqrt{x})' = \\dfrac{1}{2\\sqrt{x}}$.", "$\\dfrac{1}{2\\sqrt{x}} \\times \\dfrac{\\sqrt{x}}{\\sqrt{x}} = \\dfrac{\\sqrt{x}}{2x}$ car $\\sqrt{x}^2 = x$."),
      checks=()),
    E(63304, N3, 3,
      "Trouver une fonction polynôme $f$ telle que $f'(x) = 6x^2 - 4$ et $f(0) = 1$.",
      "$f(x) = 2x^3 - 4x + 1$.",
      "Cherche quel monôme a pour dérivée $6x^2$.",
      S("$(2x^3)' = 6x^2$ et $(-4x)' = -4$.", "Les fonctions $2x^3 - 4x + c$ conviennent ($c$ constante).", "$f(0) = c = 1$."),
      checks=("2x^3 - 4x + 1",)),
    E(63305, N3, 2,
      "Simplifier $f(x) = \\dfrac{x^2 + 1}{x}$ pour $x \\neq 0$, puis calculer $f'(x)$ sans règle du quotient.",
      "$f(x) = x + \\dfrac{1}{x}$ et $f'(x) = 1 - \\dfrac{1}{x^2}$.",
      "Sépare la fraction en deux.",
      S("$\\dfrac{x^2 + 1}{x} = \\dfrac{x^2}{x} + \\dfrac{1}{x} = x + \\dfrac{1}{x}$.", "$f'(x) = 1 - \\dfrac{1}{x^2}$."),
      checks=("1 - \\dfrac{1}{x^2}",), verify=_chk("diff((x**2 + 1)/x, x)", "1 - \\dfrac{1}{x^2}")),
    E(63306, N3, 3,
      "Déterminer les réels $a$ et $b$ tels que $f(x) = ax^2 + bx$ vérifie $f(1) = 1$ et $f'(1) = 4$.",
      "$a = 3$ et $b = -2$.",
      "Traduis les deux conditions par un système.",
      S("$f(1) = a + b = 1$ et $f'(x) = 2ax + b$, donc $f'(1) = 2a + b = 4$.", "En soustrayant : $a = 3$, puis $b = -2$."),
      checks=("a = 3", "b = -2")),
    E(63307, N3, 1,
      "Calculer la dérivée de $f(x) = 4\\sqrt{x} + \\dfrac{2}{x} - 7$ sur $]0 ; +\\infty[$.",
      "$f'(x) = \\dfrac{2}{\\sqrt{x}} - \\dfrac{2}{x^2}$.",
      "Applique les dérivées usuelles terme à terme.",
      S("$(4\\sqrt{x})' = \\dfrac{4}{2\\sqrt{x}} = \\dfrac{2}{\\sqrt{x}}$.", "$\\left(\\dfrac{2}{x}\\right)' = -\\dfrac{2}{x^2}$ et $(-7)' = 0$."),
      checks=("\\dfrac{2}{\\sqrt{x}} - \\dfrac{2}{x^2}",), verify=_chk("diff(4*sqrt(x) + 2/x - 7, x)", "\\dfrac{2}{\\sqrt{x}} - \\dfrac{2}{x^2}")),
    E(63308, N3, 4,
      "Démontrer, à l'aide du taux de variation, que la dérivée de $x \\mapsto x^3$ est $x \\mapsto 3x^2$.",
      "$\\dfrac{(a + h)^3 - a^3}{h} = 3a^2 + 3ah + h^2$, qui se rapproche de $3a^2$ quand $h$ tend vers $0$.",
      "$(a + h)^3 = a^3 + 3a^2h + 3ah^2 + h^3$.",
      S("$(a + h)^3 - a^3 = 3a^2h + 3ah^2 + h^3$.", "En divisant par $h$ : $3a^2 + 3ah + h^2$.", "Quand $h$ tend vers $0$ : $3a^2$. Donc $(x^3)' = 3x^2$."),
      checks=("3a^2 + 3ah + h^2",)),

    # N4 — opérations
    E(63401, N4, 3,
      "Calculer la dérivée de $f(x) = x^2\\sqrt{x}$ sur $]0 ; +\\infty[$ et l'écrire sous la forme $k\\,x\\sqrt{x}$.",
      "$f'(x) = \\dfrac{5}{2}x\\sqrt{x}$.",
      "Règle du produit avec $u(x) = x^2$ et $v(x) = \\sqrt{x}$.",
      S("$f'(x) = 2x\\sqrt{x} + x^2 \\times \\dfrac{1}{2\\sqrt{x}}$.", "$\\dfrac{x^2}{2\\sqrt{x}} = \\dfrac{x\\sqrt{x}}{2}$ (car $x = \\sqrt{x}^2$).",
        "$f'(x) = 2x\\sqrt{x} + \\dfrac{1}{2}x\\sqrt{x} = \\dfrac{5}{2}x\\sqrt{x}$."),
      checks=("\\dfrac{5}{2}x\\sqrt{x}",), verify=_chk("diff(x**2*sqrt(x), x)", "\\dfrac{5}{2}x\\sqrt{x}")),
    E(63402, N4, 2,
      "Calculer la dérivée de $f(x) = \\dfrac{1}{x^2 + 1}$ sur $\\mathbb{R}$.",
      "$f'(x) = -\\dfrac{2x}{(x^2 + 1)^2}$.",
      "Règle de l'inverse : $\\left(\\dfrac{1}{v}\\right)' = -\\dfrac{v'}{v^2}$.",
      S("$v(x) = x^2 + 1$ ne s'annule jamais ; $v'(x) = 2x$.", "$f'(x) = -\\dfrac{2x}{(x^2 + 1)^2}$."),
      checks=("-\\dfrac{2x}{(x^2 + 1)^2}",), verify=_chk("diff(1/(x**2 + 1), x)", "-\\dfrac{2x}{(x^2 + 1)^2}")),
    E(63403, N4, 2,
      "Calculer la dérivée de $f(x) = \\dfrac{x^2}{x + 1}$ sur $]-1 ; +\\infty[$.",
      "$f'(x) = \\dfrac{x^2 + 2x}{(x + 1)^2}$.",
      "Règle du quotient avec $u = x^2$ et $v = x + 1$.",
      S("$u' = 2x$, $v' = 1$.", "$f'(x) = \\dfrac{2x(x + 1) - x^2}{(x + 1)^2} = \\dfrac{x^2 + 2x}{(x + 1)^2}$."),
      checks=("\\dfrac{x^2 + 2x}{(x + 1)^2}",), verify=_chk("diff(x**2/(x + 1), x)", "\\dfrac{x^2 + 2x}{(x + 1)^2}")),
    E(63404, N4, 3,
      "Retrouver la règle de l'inverse $\\left(\\dfrac{1}{v}\\right)' = -\\dfrac{v'}{v^2}$ à partir de la règle du quotient.",
      "Avec $u = 1$ (donc $u' = 0$) : $\\left(\\dfrac{1}{v}\\right)' = \\dfrac{0 \\times v - 1 \\times v'}{v^2} = -\\dfrac{v'}{v^2}$.",
      "Applique la règle du quotient avec un numérateur constant.",
      S("$\\left(\\dfrac{u}{v}\\right)' = \\dfrac{u'v - uv'}{v^2}$.", "Avec $u = 1$ : $u' = 0$.", "On obtient $-\\dfrac{v'}{v^2}$."),
      checks=()),
    E(63405, N4, 2,
      "Un élève écrit : « $(uv)' = u'v'$ ». Montrer qu'il se trompe avec $u(x) = v(x) = x$.",
      "$(x \\times x)' = (x^2)' = 2x$, alors que $u'v' = 1 \\times 1 = 1$ : la formule est fausse.",
      "Compare avec une dérivée que tu connais.",
      S("$uv = x^2$, de dérivée $2x$.", "$u'v' = 1$.", "La bonne règle est $(uv)' = u'v + uv' = x + x = 2x$."),
      checks=()),
    E(63406, N4, 3,
      "Calculer la dérivée de $f(x) = \\dfrac{2x + 1}{x - 3}$ sur $]3 ; +\\infty[$ et en déduire son signe.",
      "$f'(x) = \\dfrac{-7}{(x - 3)^2} < 0$ sur $]3 ; +\\infty[$.",
      "Règle du quotient ; un carré non nul est strictement positif.",
      S("$u' = 2$, $v' = 1$.", "$f'(x) = \\dfrac{2(x - 3) - (2x + 1)}{(x - 3)^2} = \\dfrac{-7}{(x - 3)^2}$.", "Numérateur négatif, dénominateur positif : $f'(x) < 0$."),
      checks=("\\dfrac{-7}{(x - 3)^2}",), verify=_chk("diff((2*x + 1)/(x - 3), x)", "\\dfrac{-7}{(x - 3)^2}")),
    E(63407, N4, 3,
      "La puissance d'un appareil est $P(t) = \\dfrac{100t}{t^2 + 1}$ (en watts, $t \\geqslant 0$ en secondes). Calculer $P'(t)$ et $P'(1)$.",
      "$P'(t) = \\dfrac{100(1 - t^2)}{(t^2 + 1)^2}$ et $P'(1) = 0$.",
      "Règle du quotient avec $u = 100t$ et $v = t^2 + 1$.",
      S("$u' = 100$, $v' = 2t$.", "$P'(t) = \\dfrac{100(t^2 + 1) - 100t \\times 2t}{(t^2 + 1)^2} = \\dfrac{100 - 100t^2}{(t^2 + 1)^2}$.",
        "$P'(1) = 0$ : la tangente est horizontale à $t = 1$."),
      checks=("P'(1) = 0",)),
    E(63408, N4, 2,
      "Calculer la dérivée de $f(x) = (x^2 - 1)(x + 2)$ de deux façons : par la règle du produit et en développant d'abord.",
      "$f'(x) = 3x^2 + 4x - 1$ dans les deux cas.",
      "Les deux méthodes doivent donner le même résultat.",
      S("Produit : $f'(x) = 2x(x + 2) + (x^2 - 1) \\times 1 = 3x^2 + 4x - 1$.", "Développement : $f(x) = x^3 + 2x^2 - x - 2$, donc $f'(x) = 3x^2 + 4x - 1$."),
      checks=("3x^2 + 4x - 1",), verify=_chk("diff((x**2 - 1)*(x + 2), x)", "3x^2 + 4x - 1")),
]

EXERCISES = HIST + MANUELS + NOUVEAUX

QUIZ = {
    "nombre-derive.-tangente": (2246, 63101, 63105),
    "approximation-affine-et-derivabilite": (63201, 63202, 63207),
    "fonction-derivee": (590, 595, 63301),
    "operations-et-derivation": (661, 673, 63402),
}

# ── Adaptation au manuel « Première ES/L » (2026-10-26) ─────────────────────
# Voir PREMIERE_SPECIFIQUE_SUIVI.md. Hors manuel, retirés de la banque servie
# (conservés ici) : la notion « Approximation affine et dérivabilité » et les
# dérivées de (ax + b)^n (dérivée d'une fonction composée).
_IDS_HORS_PERIMETRE = {708, 722, 728}
EXERCICES_HORS_PERIMETRE = [e for e in EXERCISES if e.notion == N2 or e.id in _IDS_HORS_PERIMETRE]
_hors = {e.id for e in EXERCICES_HORS_PERIMETRE}
EXERCISES = [e for e in EXERCISES if e.id not in _hors]
NOTIONS = (N1, N3, N4)
NOTION_IDS = ("nombre-derive.-tangente", "fonction-derivee", "operations-et-derivation")
QUIZ = {k: v for k, v in QUIZ.items() if k in NOTION_IDS}
