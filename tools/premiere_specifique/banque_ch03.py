"""Chapitre 3 — Polynômes du second degré (ancien chapitre 2) : banque curée.

Exercices historiques (identifiants conservés, voir banque_ch02_historiques.py) :
textes réécrits sans écritures fautives (« x - (-3) », « -1(x…) », « + 0 »,
solutions non simplifiées), correction rédigée, niveau fixé par le
raisonnement demandé (et non plus par la taille des nombres). Chaque valeur
annoncée est recalculée (Fraction) et contrôlée par SymPy.

Nouveaux exercices : bloc 62 000 (voir banque_commun.ID_BASE).
"""
from fractions import Fraction as Fr

import sympy as sp

from premiere_specifique.banque_ch03_historiques import HISTORIQUES
from premiere_specifique.banque_commun import E, S, canonical, factored, fr, lin, par, pw, ratio, roots_tex, sq, sqrt_parts, tri

CHAPTER_NUMBER = 3  # ancien chapitre 2 (adaptation au manuel « Première ES/L », 2026-10-26)
N1 = "Fonction polynôme de degré 2"
N2 = "Équations du second degré"
N3 = "Racines et factorisation d'un trinôme"
N4 = "Signe du trinôme et inéquations du second degré"
N5 = "Second degré : modéliser et optimiser"
NOTIONS = (N1, N2, N3, N4, N5)
NOTION_IDS = (
    "fonction-polynome-de-degre-2",
    "equations-du-second-degre",
    "proprietes-d-un-trinome",
    "signe-du-trinome-et-inequations",
    "second-degre-modeliser-et-optimiser",
)

X = sp.symbols("x")
R = "\\mathbb{R}"


def _sp_roots(a, b, c):
    return sorted(float(r) for r in sp.solve(sp.Rational(a) * X**2 + sp.Rational(b) * X + sp.Rational(c), X)
                  if r.is_real)


def _same(vals, ref, tol=1e-9):
    return len(vals) == len(ref) and all(abs(u - v) < tol for u, v in zip(vals, ref))


def _sum_tex(nums):
    """Somme de nombres écrite proprement : « 4 + 14 - 2 »."""
    nums = [Fr(n) for n in nums if Fr(n) != 0] or [Fr(0)]
    out = fr(nums[0])
    for n in nums[1:]:
        out += (" - " if n < 0 else " + ") + fr(abs(n))
    return out


def _subst(a, b, c, x0, name="f"):
    """« f(x0) = a × (x0)² + b × (x0) + c = … = v »."""
    a, b, c, x0 = Fr(a), Fr(b), Fr(c), Fr(x0)
    parts = []
    for k, mono in ((a, f"{pw(x0)}^2"), (b, par(x0)), (c, None)):
        if k == 0:
            continue
        mag = abs(k)
        body = fr(mag) if mono is None else (mono if mag == 1 else f"{fr(mag)} \\times {mono}")
        if not parts:
            parts.append(("-" if k < 0 else "") + body)
        else:
            parts.append((" - " if k < 0 else " + ") + body)
    v = a * x0 * x0 + b * x0 + c
    return f"{name}({fr(x0)}) = {''.join(parts)} = {_sum_tex([a * x0 * x0, b * x0, c])} = {fr(v)}", v


def _delta_tex(a, b, c):
    d = b * b - 4 * a * c
    four_ac = 4 * a * c
    middle = f"{b * b} {'-' if four_ac >= 0 else '+'} {abs(four_ac)}"
    return f"\\Delta = b^2 - 4ac = {par(b)}^2 - 4 \\times {par(a)} \\times {par(c)} = {middle} = {d}", d


def _vertex(a, b, c):
    a, b, c = Fr(a), Fr(b), Fr(c)
    alpha = -b / (2 * a)
    return alpha, a * alpha * alpha + b * alpha + c


def _interval(lo, hi, lo_closed, hi_closed):
    left = "]-\\infty" if lo is None else (("[" if lo_closed else "]") + lo)
    right = "+\\infty[" if hi is None else (hi + ("]" if hi_closed else "["))
    return f"{left} ; {right}"


def _ineq_solution(a, b, c, op):
    """Ensemble des solutions de ax² + bx + c op 0 (op : <, >, <=, >=) :
    (texte LaTeX, prédicat d'appartenance construit par la MÊME règle)."""
    texts, vals = roots_tex(a, b, c)
    want_pos = op in (">", ">=")
    strict = op in ("<", ">")
    eps = 1e-12
    if len(set(vals)) == 2:
        x1, x2 = texts
        v1, v2 = vals
        if want_pos == (a > 0):  # signe voulu = signe de a : à l'extérieur des racines
            text = f"{_interval(None, x1, False, not strict)} \\cup {_interval(x2, None, not strict, False)}"
            pred = ((lambda t: t < v1 - eps or t > v2 + eps) if strict
                    else (lambda t: t <= v1 + eps or t >= v2 - eps))
        else:
            text = _interval(x1, x2, not strict, not strict)
            pred = ((lambda t: v1 + eps < t < v2 - eps) if strict
                    else (lambda t: v1 - eps <= t <= v2 + eps))
        return text, pred
    if len(vals) == 2:  # racine double
        x0, v0 = texts[0], vals[0]
        if want_pos == (a > 0):
            if strict:
                return f"{R} \\setminus \\left\\{{{x0}\\right\\}}", (lambda t: abs(t - v0) > eps)
            return R, (lambda t: True)
        if strict:
            return "\\varnothing", (lambda t: False)
        return f"\\left\\{{{x0}\\right\\}}", (lambda t: abs(t - v0) <= eps)
    if want_pos == (a > 0):
        return R, (lambda t: True)
    return "\\varnothing", (lambda t: False)


def _ineq_check(a, b, c, op, pred):
    """Contrôle indépendant : SymPy résout l'inéquation ; on compare l'ensemble
    annoncé en 400 points et en chaque racine exacte (bornes ouvertes ou fermées)."""
    rel = {"<": sp.Lt, ">": sp.Gt, "<=": sp.Le, ">=": sp.Ge}[op]
    poly = sp.Integer(a) * X**2 + sp.Integer(b) * X + sp.Integer(c)
    sym = sp.solve_univariate_inequality(rel(poly, 0), X, relational=False)
    for k in range(-200, 201):
        t = k / 17 + 0.013
        if bool(pred(t)) != bool(sym.contains(sp.Rational(t))):
            return f"ensemble annoncé faux en x = {t}"
    for r in sp.solve(poly, X):
        if r.is_real and bool(pred(float(r))) != bool(sym.contains(r)):
            return f"borne mal fermée ou ouverte en x = {r}"
    return None


def _ineq_numeric_ok(a, b, c, op, _sol_text):
    """Inéquations rédigées à la main : même contrôle, ensemble déduit de la règle."""
    return _ineq_check(a, b, c, op, _ineq_solution(a, b, c, op)[1])


OPS_TEX = {"<": "<", ">": ">", "<=": "\\leqslant", ">=": "\\geqslant"}

# ── Familles historiques ─────────────────────────────────────────────────────


def _coef_image(i, a, b, c, x0):
    line, v = _subst(a, b, c, x0)
    missing = []
    if b == 0:
        missing.append("il n'y a pas de terme en $x$, donc $b = 0$")
    if c == 0:
        missing.append("il n'y a pas de terme constant, donc $c = 0$")
    note = (" ; " + " et ".join(missing)) if missing else ""
    return E(i, N1, 1,
             f"On considère la fonction polynôme du second degré $f$ définie sur ${R}$ par $f(x) = {tri(a, b, c)}$. "
             f"Donner les coefficients $a$, $b$ et $c$, puis calculer $f({x0})$.",
             f"$a = {a}$, $b = {b}$, $c = {c}$ et $f({x0}) = {fr(v)}$.",
             "Les coefficients se lisent devant $x^2$, devant $x$, puis dans le terme constant ; remplace $x$ en gardant les parenthèses.",
             S(f"On écrit $f(x)$ sous la forme $ax^2 + bx + c$ : $a = {a}$, $b = {b}$, $c = {c}${note}.",
               f"On remplace $x$ par ${par(x0)}$ : ${line}$."),
             checks=(f"f({x0}) = {fr(v)}",))


def _variations(i, a, b, c):
    alpha, beta = _vertex(a, b, c)
    vline, _ = _subst(a, b, c, alpha)
    extr = "minimum" if a > 0 else "maximum"
    first, second = ("décroissante", "croissante") if a > 0 else ("croissante", "décroissante")
    al = fr(alpha)
    ans = (f"$f$ est {first} sur $]-\\infty ; {al}]$ et {second} sur $[{al} ; +\\infty[$ ; "
           f"son {extr} vaut ${fr(beta)}$, atteint en $x = {al}$.")
    return E(i, N1, 2,
             f"Soit $f$ la fonction définie sur ${R}$ par $f(x) = {tri(a, b, c)}$. Dresser le tableau de variations de $f$ "
             f"et préciser son extremum.",
             ans,
             "Le signe de $a$ donne l'allure de la parabole ; le sommet a pour abscisse $-\\dfrac{b}{2a}$.",
             S(f"$a = {a}$ est {'positif' if a > 0 else 'négatif'} : la parabole est tournée vers le "
               f"{'haut' if a > 0 else 'bas'}, $f$ admet un {extr}.",
               f"Abscisse du sommet : $\\alpha = \\dfrac{{-b}}{{2a}} = {ratio(-b, 2 * a)}$.",
               f"Ordonnée du sommet : $\\beta = {vline}$.",
               f"Tableau : $f$ est {first} jusqu'à $x = {al}$, puis {second} ; {extr} ${fr(beta)}$ en $x = {al}$."),
             checks=(al, fr(beta)),
             verify=lambda: None if sp.diff(a * X**2 + b * X + c, X).subs(X, sp.Rational(alpha.numerator, alpha.denominator)) == 0 else "sommet faux")


def _canonique(i, a, b, c):
    a, b, c = Fr(a), Fr(b), Fr(c)
    alpha, beta = _vertex(a, b, c)
    half = b / (2 * a)
    result = canonical(a, alpha, beta)
    if a == 1:
        steps = S(f"On reconnaît le début d'un carré : $x^2 + 2kx = (x + k)^2 - k^2$ avec $2k = {fr(b)}$, donc $k = {fr(half)}$.",
                  f"$f(x) = ({lin(-half)})^2 - {sq(half)}{'' if c == 0 else (' + ' if c > 0 else ' - ') + fr(abs(c))} = {result}$.",
                  f"Vérification : le sommet a pour abscisse $-\\dfrac{{b}}{{2a}} = {fr(alpha)}$ et $f({fr(alpha)}) = {fr(beta)}$.")
        level = 1 if b.denominator == 1 and b.numerator % 2 == 0 else 2
    else:
        inner = tri(1, b / a, 0)
        lead = "-" if a == -1 else fr(a)
        k2 = a * half * half
        cst = "" if c == 0 else f" {'+' if c > 0 else '-'} {fr(abs(c))}"
        steps = S(f"On factorise $a = {fr(a)}$ dans les termes en $x$ : $f(x) = {lead}\\left({inner}\\right){cst}$.",
                  f"Complétion du carré : ${inner} = ({lin(-half)})^2 - {sq(half)}$.",
                  f"$f(x) = {lead}({lin(-half)})^2 {'-' if k2 > 0 else '+'} {fr(abs(k2))}{cst} = {result}$.",
                  f"Vérification : $\\alpha = -\\dfrac{{b}}{{2a}} = {fr(alpha)}$ et $\\beta = f(\\alpha) = {fr(beta)}$.")
        level = 3
    expanded = sp.expand(sp.Rational(a.numerator, a.denominator) * (X - sp.Rational(alpha.numerator, alpha.denominator))**2
                         + sp.Rational(beta.numerator, beta.denominator))
    target = sp.Rational(a.numerator, a.denominator) * X**2 + sp.Rational(b.numerator, b.denominator) * X + sp.Rational(c.numerator, c.denominator)
    return E(i, N1, level,
             f"Déterminer la forme canonique de la fonction $f$ définie sur ${R}$ par $f(x) = {tri(a, b, c)}$.",
             f"$f(x) = {result}$.",
             "Fais apparaître le début d'un carré : $x^2 + 2kx = (x + k)^2 - k^2$.",
             steps, checks=(result,),
             verify=lambda: None if sp.simplify(expanded - target) == 0 else "forme canonique fausse")


def _resolution(i, a, b, c):
    dline, d = _delta_tex(a, b, c)
    texts, vals = roots_tex(a, b, c)
    eq = f"{tri(a, b, c)} = 0"
    if d < 0:
        ans, level = "$\\mathcal{S} = \\varnothing$", 1
        concl = f"$\\Delta = {d} < 0$ : l'équation n'a aucune solution réelle."
    elif d == 0:
        ans, level = f"$\\mathcal{{S}} = \\left\\{{{texts[0]}\\right\\}}$", 2
        concl = f"$\\Delta = 0$ : une seule solution, $x_0 = -\\dfrac{{b}}{{2a}} = {texts[0]}$."
    else:
        ans = f"$\\mathcal{{S}} = \\left\\{{{texts[0]} ; {texts[1]}\\right\\}}$"
        k, m = sqrt_parts(d)
        level = 2 if m == 1 else 3
        root_note = (f" (ici $\\sqrt{{\\Delta}} = {k}$)" if m == 1 else
                     f" (ici $\\sqrt{{{d}}} = {k}\\sqrt{{{m}}}$, puis on simplifie)" if k > 1 else "")
        concl = (f"$\\Delta = {d} > 0$ : deux solutions $x = \\dfrac{{-b \\pm \\sqrt{{\\Delta}}}}{{2a}} = "
                 f"\\dfrac{{{-b} \\pm \\sqrt{{{d}}}}}{{{2 * a}}}${root_note}, soit ${texts[0]}$ et ${texts[1]}$.")
    return E(i, N2, level,
             f"Résoudre dans ${R}$ l'équation ${eq}$.",
             ans,
             "Commence par calculer le discriminant ; son signe donne le nombre de solutions.",
             S(f"On identifie $a = {a}$, $b = {b}$, $c = {c}$.", f"${dline}$.", concl),
             verify=lambda: None if _same(vals, _sp_roots(a, b, c)) else "racines fausses")


def _somme_produit(i, a, b, c):
    _, d = _delta_tex(a, b, c)
    assert d > 0, i
    s, p = Fr(-b, a), Fr(c, a)
    level = 1 if (s.denominator == 1 and p.denominator == 1) else 2
    vals = _sp_roots(a, b, c)
    return E(i, N3, level,
             f"Soit $f$ la fonction définie sur ${R}$ par $f(x) = {tri(a, b, c)}$. Justifier que $f$ admet deux racines distinctes "
             f"$x_1$ et $x_2$, puis calculer $x_1 + x_2$ et $x_1 x_2$ sans les déterminer.",
             f"$x_1 + x_2 = {fr(s)}$ et $x_1 x_2 = {fr(p)}$.",
             "Si $\\Delta > 0$, la somme des racines vaut $-\\dfrac{b}{a}$ et leur produit $\\dfrac{c}{a}$.",
             S(f"$\\Delta = {b * b} {'-' if 4 * a * c >= 0 else '+'} {abs(4 * a * c)} = {d} > 0$ : deux racines distinctes.",
               f"Somme : $x_1 + x_2 = -\\dfrac{{b}}{{a}} = {fr(s)}$.",
               f"Produit : $x_1 x_2 = \\dfrac{{c}}{{a}} = {fr(p)}$."),
             checks=(fr(s), fr(p)),
             verify=lambda: None if abs(sum(vals) - float(s)) < 1e-9 and abs(vals[0] * vals[1] - float(p)) < 1e-9 else "somme ou produit faux")


def _inequation(i, a, b, c, op):
    sol, pred = _ineq_solution(a, b, c, op)
    texts, vals = roots_tex(a, b, c)
    _, d = _delta_tex(a, b, c)
    sa = "positif" if a > 0 else "négatif"
    if d > 0:
        roots_step = f"$\\Delta = {d} > 0$ : racines $x_1 = {texts[0]}$ et $x_2 = {texts[1]}$."
        rule = f"Le trinôme est du signe de $a$ ({sa}) à l'extérieur des racines et du signe contraire entre elles."
        level = 2
    elif d == 0:
        roots_step = f"$\\Delta = 0$ : racine double $x_0 = {texts[0]}$."
        rule = f"Le trinôme est du signe de $a$ ({sa}) pour tout $x \\neq {texts[0]}$ et s'annule en ${texts[0]}$."
        level = 3
    else:
        roots_step = f"$\\Delta = {d} < 0$ : aucune racine."
        rule = f"Le trinôme garde le signe de $a$ ({sa}) sur ${R}$."
        level = 3
    return E(i, N4, level,
             f"Résoudre dans ${R}$ l'inéquation ${tri(a, b, c)} {OPS_TEX[op]} 0$.",
             f"$\\mathcal{{S}} = {sol}$",
             "Cherche les racines, puis applique la règle du signe d'un trinôme.",
             S(roots_step, rule, f"On garde les $x$ pour lesquels le trinôme est {'positif' if op in ('>', '>=') else 'négatif'}"
               f"{'' if op in ('<', '>') else ' ou nul'} : $\\mathcal{{S}} = {sol}$."),
             verify=lambda: _ineq_check(a, b, c, op, pred))


def _autre_racine(i, a, b, c, r):
    assert a * r * r + b * r + c == 0, i
    r2 = Fr(c, a) / r if r != 0 else Fr(-b, a) - r
    line, _ = _subst(a, b, c, r)
    if c == 0:
        how = (f"Le terme constant est nul : le produit des racines vaut $0$, l'une d'elles est donc $0$ ; "
               f"la somme $-\\dfrac{{b}}{{a}} = {fr(Fr(-b, a))}$ confirme que l'autre racine est ${fr(r2)}$.")
    elif r != 0:
        how = (f"Le produit des racines vaut $\\dfrac{{c}}{{a}} = {fr(Fr(c, a))}$, donc l'autre racine est "
               f"${fr(Fr(c, a))} \\div {par(r)} = {fr(r2)}$.")
    else:
        how = f"Le produit vaut $0$ ; on utilise la somme $-\\dfrac{{b}}{{a}} = {fr(Fr(-b, a))}$ : l'autre racine est ${fr(r2)}$."
    form = factored(a, sorted([Fr(r), r2]))
    return E(i, N3, 2,
             f"On donne la fonction $f$ définie sur ${R}$ par $f(x) = {tri(a, b, c)}$. 1) Vérifier que ${r}$ est racine de $f$. "
             f"2) À l'aide de la somme ou du produit des racines, déterminer l'autre racine. 3) En déduire une forme factorisée de $f$.",
             f"L'autre racine est ${fr(r2)}$ et $f(x) = {form}$.",
             "Quand une racine est connue, le produit $\\dfrac{c}{a}$ (ou la somme $-\\dfrac{b}{a}$) donne l'autre sans calculer $\\Delta$.",
             S(f"${line}$ : ${r}$ est bien racine.", how, f"Avec $a = {a}$ : $f(x) = a(x - x_1)(x - x_2) = {form}$."),
             checks=(fr(r2),),
             verify=lambda: None if _same(sorted([float(r), float(r2)]), _sp_roots(a, b, c)) else "autre racine fausse")


_FAMILIES = {"coef_image": _coef_image, "variations": _variations, "canonique": _canonique, "resolution": _resolution,
             "somme_produit": _somme_produit, "inequation": _inequation, "autre_racine": _autre_racine}

HIST = [_FAMILIES[fam](i, *params) for i, fam, params in HISTORIQUES]


# ── Exercices historiques saisis à la main ───────────────────────────────────


def _sommet_vf(i, name, a, b, c, claimed):
    alpha, beta = _vertex(a, b, c)
    vrai = (Fr(claimed[0]), Fr(claimed[1])) == (alpha, beta)
    vline, _ = _subst(a, b, c, alpha, name)
    verdict = (f"Vrai : le sommet est bien $\\left({fr(alpha)} ; {fr(beta)}\\right)$." if vrai else
               f"Faux : le sommet est $\\left({fr(alpha)} ; {fr(beta)}\\right)$.")
    return E(i, N1, 2,
             f"Soit ${name}$ la fonction définie sur ${R}$ par ${name}(x) = {tri(a, b, c)}$. Un élève affirme que le sommet de sa "
             f"parabole a pour coordonnées $\\left({fr(claimed[0])} ; {fr(claimed[1])}\\right)$. A-t-il raison ? Justifier.",
             verdict,
             "Recalcule l'abscisse du sommet avec $-\\dfrac{b}{2a}$ avant de comparer.",
             S(f"$\\alpha = \\dfrac{{-b}}{{2a}} = {ratio(-b, 2 * a)}$.", f"$\\beta = {vline}$.",
               "On compare avec les coordonnées annoncées." + ("" if vrai else " L'erreur la plus fréquente est d'oublier le signe moins de $-\\dfrac{b}{2a}$.")),
             checks=(fr(alpha), fr(beta)))


def _canonique_erreur(i, name, a, b, c):
    alpha, beta = _vertex(a, b, c)
    wrong = canonical(a, -alpha, beta)
    good = canonical(a, alpha, beta)
    return E(i, N1, 3,
             f"Un élève écrit la forme canonique de ${name}(x) = {tri(a, b, c)}$ ainsi : ${name}(x) = {wrong}$. "
             f"Identifier son erreur et donner la forme correcte.",
             f"Le signe de l'abscisse du sommet est faux : ${name}(x) = {good}$.",
             "Dans $a(x - \\alpha)^2 + \\beta$, le signe écrit dans la parenthèse est l'opposé de $\\alpha$.",
             S(f"$\\alpha = -\\dfrac{{b}}{{2a}} = {fr(alpha)}$, donc la parenthèse est $({lin(alpha)})$.",
               f"$\\beta = {name}(\\alpha) = {fr(beta)}$ (l'élève avait juste sur ce point).",
               f"Forme correcte : ${name}(x) = {good}$."),
             checks=(good,))


def _resserree(i, p, q):
    (a1, b1, c1), (a2, b2, c2) = p, q
    plus = "f" if abs(a1) > abs(a2) else "g"
    big, small = max(abs(a1), abs(a2)), min(abs(a1), abs(a2))
    return E(i, N1, 1,
             f"On donne $f(x) = {tri(a1, b1, c1)}$ et $g(x) = {tri(a2, b2, c2)}$. Sans tracer les courbes, déterminer laquelle "
             f"des deux paraboles est la plus « resserrée » autour de son axe de symétrie.",
             f"La parabole de ${plus}$ est la plus resserrée, car $|a|$ y est le plus grand (${big}$ contre ${small}$).",
             "Compare les valeurs absolues des coefficients de $x^2$.",
             S("Plus $|a|$ est grand, plus la parabole s'écarte vite de son sommet : elle est plus resserrée.",
               f"Pour $f$ : $|a| = {abs(a1)}$ ; pour $g$ : $|a| = {abs(a2)}$.",
               f"Conclusion : la parabole de ${plus}$ est la plus resserrée (les coefficients $b$ et $c$ ne changent que la position)."))


def _parametre_b(i, name, a, c, alpha):
    b = -2 * a * alpha
    return E(i, N1, 2,
             f"Soit ${name}$ la fonction définie sur ${R}$ par ${name}(x) = {a}x^2 + bx {'+' if c > 0 else '-'} {abs(c)}$, où $b$ est un réel. "
             f"Sachant que le sommet de la parabole a pour abscisse ${alpha}$, déterminer $b$.",
             f"$b = {b}$.",
             "Écris l'égalité $-\\dfrac{b}{2a} = \\alpha$ et isole $b$.",
             S(f"L'abscisse du sommet vaut $-\\dfrac{{b}}{{2a}} = -\\dfrac{{b}}{{{2 * a}}}$.",
               f"On résout $-\\dfrac{{b}}{{{2 * a}}} = {alpha}$ : $b = -{par(2 * a)} \\times {par(alpha)} = {b}$.",
               f"Vérification : $-\\dfrac{{{b}}}{{{2 * a}}} = {alpha}$."),
             checks=(f"b = {b}",))


def _signe_valeur(i, name, a, b, c, x0, claim):
    line, v = _subst(a, b, c, x0, name)
    ok = (v > 0) == (claim == "positive")
    real = "positive" if v > 0 else "négative"
    return E(i, N4, 1,
             f"Soit ${name}(x) = {tri(a, b, c)}$. Un élève affirme que ${name}({x0})$ est {claim}. A-t-il raison ? Justifier.",
             (f"Vrai : ${name}({x0}) = {fr(v)}$, qui est bien {real}." if ok else
              f"Faux : ${name}({x0}) = {fr(v)}$, qui est {real}."),
             "Calcule l'image en remplaçant $x$ entre parenthèses.",
             S(f"${line}$.", f"${fr(v)}$ est {real}."),
             checks=(fr(v),))


def _factorisation_erreur(i, name, a, b, c, r, wrong):
    r2 = Fr(c, a) / r
    good = factored(a, sorted([Fr(r), r2]))
    bad = factored(a, sorted([Fr(r), Fr(wrong)]))
    return E(i, N3, 3,
             f"On donne ${name}(x) = {tri(a, b, c)}$, dont ${r}$ est une racine. Un élève propose la factorisation "
             f"${name}(x) = {bad}$. Identifier son erreur et donner la factorisation correcte.",
             f"La seconde racine est fausse : elle vaut ${fr(r2)}$, et ${name}(x) = {good}$.",
             "Contrôle avec le produit des racines $\\dfrac{c}{a}$.",
             S(f"Produit des racines : $\\dfrac{{c}}{{a}} = {fr(Fr(c, a))}$ ; avec ${r}$, l'autre racine vaut ${fr(Fr(c, a))} \\div {par(r)} = {fr(r2)}$ (et non ${wrong}$).",
               f"Contrôle : en développant la proposition de l'élève, on n'obtient pas ${tri(a, b, c)}$.",
               f"Factorisation correcte : ${name}(x) = {good}$."),
             checks=(fr(r2),),
             verify=lambda: None if sp.expand(sp.Rational(a) * (X - r) * (X - sp.Rational(r2.numerator, r2.denominator))
                                             - (a * X**2 + b * X + c)) == 0 else "factorisation fausse")


MANUELS = [
    E(437, N5, 3,
      "Un rectangle a pour périmètre $40$ m et pour aire $91$ m². On note $x$ sa largeur (en m). Montrer que $x$ vérifie une "
      "équation du second degré, puis déterminer les dimensions du rectangle (la largeur est inférieure à la longueur).",
      "La largeur vaut $7$ m et la longueur $13$ m.",
      "Le demi-périmètre donne la longueur en fonction de $x$.",
      S("Le demi-périmètre vaut $20$ : la longueur est $20 - x$.",
        "Aire : $x(20 - x) = 91$, soit $x^2 - 20x + 91 = 0$.",
        "$\\Delta = 400 - 364 = 36$ : $x = \\dfrac{20 - 6}{2} = 7$ ou $x = \\dfrac{20 + 6}{2} = 13$.",
        "La largeur est la plus petite dimension : $7$ m ; la longueur vaut $20 - 7 = 13$ m (vérification : $7 \\times 13 = 91$)."),
      checks=("$7$", "$13$")),
    _sommet_vf(2250, "f", 4, 1, 6, (Fr(1, 8), Fr(99, 16))),
    _sommet_vf(2251, "g", -2, 1, 5, (Fr(-1, 4), Fr(37, 8))),
    _sommet_vf(2252, "f", -3, 8, 3, (Fr(4, 3), Fr(25, 3))),
    _sommet_vf(2253, "g", 2, -4, 6, (-1, 12)),
    _canonique_erreur(2254, "f", 1, -5, 5),
    _canonique_erreur(2255, "h", -3, 5, -6),
    _canonique_erreur(2256, "g", -3, -1, 4),
    _resserree(2257, (-6, -3, -2), (-4, -1, 3)),
    _resserree(2258, (-5, 3, -3), (-6, 5, 1)),
    _resserree(2259, (3, 1, 5), (-6, 1, 2)),
    _parametre_b(2260, "g", -4, 1, -5),
    _parametre_b(2261, "h", -4, -5, 3),
    _parametre_b(2262, "g", -3, 8, 1),
    _signe_valeur(2263, "h", 2, -3, -3, -1, "positive"),
    _signe_valeur(2264, "h", 3, 2, 5, -4, "positive"),
    _signe_valeur(2265, "g", 4, 6, 6, -2, "positive"),
    _signe_valeur(2266, "h", 2, 6, -2, 4, "négative"),
    _factorisation_erreur(2267, "h", 1, -1, -6, -2, -3),
    _factorisation_erreur(2268, "g", 2, 18, 40, -4, 5),
    _factorisation_erreur(2269, "f", 1, 1, -6, 2, 3),
]

LEGACY_IDS = tuple(e.id for e in HIST + MANUELS)


def _poly_eq(expr_a, expr_b):
    return sp.simplify(sp.sympify(expr_a) - sp.sympify(expr_b)) == 0


# ── Nouveaux exercices ──────────────────────────────────────────────────────

NOUVEAUX = [
    # N1 — fonction polynôme de degré 2 : formes, sommet, variations, allure
    E(62101, N1, 2,
      "Parmi les fonctions suivantes, définies sur $\\mathbb{R}$, lesquelles sont des fonctions polynômes du second degré ? "
      "Donner alors $a$, $b$ et $c$. $f(x) = (x - 1)(2x + 3)$ ; $g(x) = x^2 - (x + 1)^2$ ; $h(x) = 3 - x^2$ ; $k(x) = (x + 1)^3 - x^3$.",
      "$f$ ($a = 2$, $b = 1$, $c = -3$), $h$ ($a = -1$, $b = 0$, $c = 3$) et $k$ ($a = 3$, $b = 3$, $c = 1$) ; $g$ n'en est pas une : $g(x) = -2x - 1$.",
      "Développe et réduis chaque expression avant de conclure : seul le terme de plus haut degré compte.",
      S("$f(x) = 2x^2 + 3x - 2x - 3 = 2x^2 + x - 3$ : second degré.",
        "$g(x) = x^2 - (x^2 + 2x + 1) = -2x - 1$ : les termes en $x^2$ s'annulent, $g$ est affine.",
        "$h(x) = -x^2 + 3$ : second degré, avec $b = 0$.",
        "$k(x) = x^3 + 3x^2 + 3x + 1 - x^3 = 3x^2 + 3x + 1$ : second degré, malgré l'écriture avec des cubes."),
      verify=lambda: None if _poly_eq("(x-1)*(2*x+3)", "2*x**2+x-3") and _poly_eq("x**2-(x+1)**2", "-2*x-1")
      and _poly_eq("(x+1)**3-x**3", "3*x**2+3*x+1") else "développement faux"),
    E(62102, N1, 3,
      "La parabole représentant une fonction polynôme du second degré $f$ a pour sommet $S(-2 ; 3)$ et coupe l'axe des ordonnées au "
      "point d'ordonnée $11$. Déterminer $f(x)$ sous forme canonique, puis sous forme développée.",
      "$f(x) = 2(x + 2)^2 + 3 = 2x^2 + 8x + 11$.",
      "Le sommet fixe $\\alpha$ et $\\beta$ ; le point d'abscisse $0$ permet de trouver $a$.",
      S("Avec le sommet : $f(x) = a(x + 2)^2 + 3$, $a \\neq 0$.",
        "$f(0) = 11$ : $4a + 3 = 11$, donc $a = 2$.",
        "$f(x) = 2(x + 2)^2 + 3 = 2(x^2 + 4x + 4) + 3 = 2x^2 + 8x + 11$."),
      checks=("2(x + 2)^2 + 3", "2x^2 + 8x + 11"),
      verify=lambda: None if _poly_eq("2*(x+2)**2+3", "2*x**2+8*x+11") else "développement faux"),
    E(62103, N1, 2,
      "Soit $f(x) = x^2 - 4x + 7$. On a $f(-1) = 12$. Sans résoudre d'équation, trouver un autre réel qui a pour image $12$.",
      "$5$ a aussi pour image $12$.",
      "La parabole est symétrique par rapport à la droite d'équation $x = \\alpha$.",
      S("Abscisse du sommet : $\\alpha = \\dfrac{4}{2} = 2$ ; l'axe de symétrie est la droite d'équation $x = 2$.",
        "Le symétrique de $-1$ par rapport à $2$ est $2 + (2 - (-1)) = 5$.",
        "Vérification : $f(5) = 25 - 20 + 7 = 12$."),
      checks=("$5$",)),
    E(62104, N1, 3,
      "Soit $f(x) = -3(x - 1)^2 + 4$. Sans calculer d'image, comparer $f(-2)$ et $f(3)$.",
      "$f(3) > f(-2)$.",
      "Pour $a < 0$, plus $x$ est loin de l'abscisse du sommet, plus $f(x)$ est petit.",
      S("$a = -3 < 0$ : $f(x) = 4 - 3(x - 1)^2$ diminue quand l'écart $|x - 1|$ augmente.",
        "$|-2 - 1| = 3$ et $|3 - 1| = 2$ : $3$ est plus proche de $1$ que $-2$.",
        "Donc $f(3) > f(-2)$ (contrôle : $f(3) = -8$ et $f(-2) = -23$)."),
      verify=lambda: None if -3 * 4 + 4 > -3 * 9 + 4 else "comparaison fausse"),
    E(62105, N1, 1,
      "Compléter : $x^2 + 10x + 21 = (x + \\ldots)^2 - \\ldots$, puis donner les coordonnées du sommet de la parabole.",
      "$x^2 + 10x + 21 = (x + 5)^2 - 4$ ; sommet $S(-5 ; -4)$.",
      "$x^2 + 10x$ est le début du développement de $(x + 5)^2$.",
      S("$(x + 5)^2 = x^2 + 10x + 25$, donc $x^2 + 10x = (x + 5)^2 - 25$.",
        "$x^2 + 10x + 21 = (x + 5)^2 - 25 + 21 = (x + 5)^2 - 4$.",
        "Sous la forme $a(x - \\alpha)^2 + \\beta$ : $\\alpha = -5$ et $\\beta = -4$."),
      checks=("(x + 5)^2 - 4", "S(-5 ; -4)"),
      verify=lambda: None if _poly_eq("(x+5)**2-4", "x**2+10*x+21") else "complétion fausse"),
    E(62106, N1, 1,
      "On note $\\mathcal{P}$ la parabole d'équation $y = x^2$ et $\\mathcal{C}$ celle de $h(x) = (x - 3)^2 + 2$. "
      "Par quelle transformation passe-t-on de $\\mathcal{P}$ à $\\mathcal{C}$ ? Donner le sommet de $\\mathcal{C}$.",
      "Par la translation de $3$ unités vers la droite et $2$ unités vers le haut ; le sommet de $\\mathcal{C}$ est $(3 ; 2)$.",
      "Remplacer $x$ par $x - 3$ décale la courbe horizontalement ; ajouter $2$ la décale verticalement.",
      S("La courbe de $x \\mapsto (x - 3)^2$ est celle de $x \\mapsto x^2$ décalée de $3$ vers la droite (et non vers la gauche).",
        "Ajouter $2$ décale de $2$ vers le haut.",
        "Le sommet $(0 ; 0)$ de $\\mathcal{P}$ devient $(3 ; 2)$."),
      checks=("(3 ; 2)",)),
    E(62107, N1, 2,
      "Soit $f(x) = (x - 1)^2 - 9$. Déterminer les antécédents de $0$, de $-9$ et de $-10$ par $f$.",
      "$0$ a deux antécédents, $-2$ et $4$ ; $-9$ en a un seul, $1$ ; $-10$ n'en a aucun.",
      "La forme canonique permet de résoudre $f(x) = k$ en isolant le carré.",
      S("$f(x) = 0 \\iff (x - 1)^2 = 9 \\iff x - 1 = 3$ ou $x - 1 = -3$, soit $x = 4$ ou $x = -2$.",
        "$f(x) = -9 \\iff (x - 1)^2 = 0 \\iff x = 1$.",
        "$f(x) = -10 \\iff (x - 1)^2 = -1$ : impossible, un carré est positif ou nul. Le minimum de $f$ est $-9$."),
      checks=("$-2$", "$4$", "$1$")),
    E(62108, N1, 2,
      "Le coût de fabrication de $x$ centaines d'objets est $C(x) = 0{,}5x^2 - 6x + 40$ (en milliers d'euros), pour $x \\in [0 ; 15]$. "
      "Pour quelle production le coût est-il minimal ? Que vaut-il ?",
      "Le coût est minimal pour $600$ objets ($x = 6$) ; il vaut $22$ milliers d'euros.",
      "C'est l'ordonnée du sommet de la parabole ; regarde le signe de $a$.",
      S("$a = 0{,}5 > 0$ : la parabole est tournée vers le haut, $C$ admet un minimum.",
        "$\\alpha = -\\dfrac{-6}{2 \\times 0{,}5} = 6$, qui appartient bien à $[0 ; 15]$.",
        "$C(6) = 0{,}5 \\times 36 - 36 + 40 = 22$."),
      checks=("$22$",), verify=lambda: None if 0.5 * 36 - 36 + 40 == 22 else "minimum faux"),
    E(62109, N1, 1,
      "Un élève affirme : « la parabole de $f(x) = -(x + 2)^2 + 5$ a pour sommet $(2 ; 5)$ ». A-t-il raison ?",
      "Non : le sommet est $(-2 ; 5)$.",
      "Écris $(x + 2)$ sous la forme $(x - \\alpha)$.",
      S("$(x + 2) = (x - (-2))$, donc $\\alpha = -2$.", "$\\beta = 5$.", "Le sommet est $(-2 ; 5)$ : l'élève s'est trompé de signe."),
      checks=("(-2 ; 5)",)),
    E(62110, N1, 3,
      "Déterminer les réels $b$ et $c$ tels que la parabole de $f(x) = x^2 + bx + c$ ait pour sommet $S(3 ; -1)$.",
      "$b = -6$ et $c = 8$.",
      "Avec $a = 1$, la forme canonique est imposée par le sommet.",
      S("Le sommet impose $f(x) = (x - 3)^2 - 1$.", "On développe : $f(x) = x^2 - 6x + 9 - 1 = x^2 - 6x + 8$.",
        "Par identification : $b = -6$ et $c = 8$."),
      checks=("b = -6", "c = 8"), verify=lambda: None if _poly_eq("(x-3)**2-1", "x**2-6*x+8") else "faux"),
    E(62111, N1, 4,
      "Soit $f(x) = a(x - \\alpha)^2 + \\beta$ avec $a \\neq 0$. Démontrer que pour tout réel $h$, $f(\\alpha + h) = f(\\alpha - h)$. "
      "Interpréter graphiquement.",
      "$f(\\alpha + h) = ah^2 + \\beta = f(\\alpha - h)$ : la droite d'équation $x = \\alpha$ est un axe de symétrie de la parabole.",
      "Calcule séparément les deux images.",
      S("$f(\\alpha + h) = a(\\alpha + h - \\alpha)^2 + \\beta = ah^2 + \\beta$.",
        "$f(\\alpha - h) = a(-h)^2 + \\beta = ah^2 + \\beta$.",
        "Les points d'abscisses $\\alpha + h$ et $\\alpha - h$, symétriques par rapport à $\\alpha$, ont la même ordonnée : la parabole est symétrique par rapport à la droite d'équation $x = \\alpha$."),
      verify=lambda: None if sp.expand(sp.Symbol("a") * (sp.Symbol("h"))**2 - sp.Symbol("a") * (-sp.Symbol("h"))**2) == 0 else "faux"),
    E(62112, N1, 3,
      "Démontrer que pour tout réel $x$, $2x^2 - 12x + 23 > 0$, et préciser la plus petite valeur prise par cette expression.",
      "$2x^2 - 12x + 23 = 2(x - 3)^2 + 5 \\geqslant 5 > 0$ ; la plus petite valeur est $5$, atteinte en $x = 3$.",
      "Écris l'expression sous forme canonique.",
      S("$2x^2 - 12x + 23 = 2(x^2 - 6x) + 23 = 2\\left((x - 3)^2 - 9\\right) + 23 = 2(x - 3)^2 + 5$.",
        "Un carré est positif ou nul : $2(x - 3)^2 \\geqslant 0$, donc l'expression est supérieure ou égale à $5$.",
        "Elle vaut $5$ pour $x = 3$ : c'est le minimum, strictement positif."),
      checks=("$5$",), verify=lambda: None if _poly_eq("2*(x-3)**2+5", "2*x**2-12*x+23") else "faux"),
    E(62113, N1, 4,
      "Pour tout réel $m$, on note $f_m(x) = x^2 - 2mx + 3m$. Déterminer les coordonnées du sommet $S_m$ de la parabole de $f_m$, "
      "puis montrer que tous les points $S_m$ sont sur une même parabole dont on donnera une équation.",
      "$S_m(m ; -m^2 + 3m)$ ; tous les sommets sont sur la parabole d'équation $y = -x^2 + 3x$.",
      "Exprime l'ordonnée du sommet en fonction de son abscisse.",
      S("$\\alpha = -\\dfrac{-2m}{2} = m$.", "$\\beta = f_m(m) = m^2 - 2m^2 + 3m = -m^2 + 3m$.",
        "L'abscisse de $S_m$ est $x = m$ et son ordonnée vaut $y = -x^2 + 3x$ : $S_m$ appartient à cette parabole pour tout $m$."),
      checks=("y = -x^2 + 3x",)),

    # N2 — équations du second degré
    E(62201, N2, 1,
      "Sans les résoudre, donner le nombre de solutions de chaque équation : a) $4x^2 - 12x + 9 = 0$ ; b) $-2x^2 + x - 5 = 0$ ; c) $x^2 + x - 1 = 0$.",
      "a) une solution ($\\Delta = 0$) ; b) aucune ($\\Delta = -39$) ; c) deux ($\\Delta = 5$).",
      "Seul le signe du discriminant compte ici.",
      S("a) $\\Delta = 144 - 144 = 0$.", "b) $\\Delta = 1 - 40 = -39 < 0$.", "c) $\\Delta = 1 + 4 = 5 > 0$."),
      checks=("-39", "5")),
    E(62202, N2, 2,
      "Résoudre dans $\\mathbb{R}$ l'équation $3x^2 - 2x - 8 = 0$.",
      "$\\mathcal{S} = \\left\\{-\\dfrac{4}{3} ; 2\\right\\}$",
      "Calcule $\\Delta$, puis applique les formules.",
      S("$\\Delta = (-2)^2 - 4 \\times 3 \\times (-8) = 4 + 96 = 100 = 10^2$.",
        "$x_1 = \\dfrac{2 - 10}{6} = -\\dfrac{4}{3}$ et $x_2 = \\dfrac{2 + 10}{6} = 2$.",
        "Vérification : $3 \\times 4 - 4 - 8 = 0$."),
      verify=lambda: None if _same(_sp_roots(3, -2, -8), [-4 / 3, 2]) else "faux"),
    E(62203, N2, 2,
      "Résoudre dans $\\mathbb{R}$ l'équation $x^2 - 6x + 4 = 0$. Donner les solutions sous forme exacte simplifiée.",
      "$\\mathcal{S} = \\left\\{3 - \\sqrt{5} ; 3 + \\sqrt{5}\\right\\}$",
      "Simplifie $\\sqrt{\\Delta}$ : $\\sqrt{20} = 2\\sqrt{5}$.",
      S("$\\Delta = 36 - 16 = 20 > 0$ et $\\sqrt{20} = 2\\sqrt{5}$.",
        "$x = \\dfrac{6 \\pm 2\\sqrt{5}}{2} = 3 \\pm \\sqrt{5}$.",
        "Valeurs approchées : $0{,}76$ et $5{,}24$."),
      verify=lambda: None if _same(_sp_roots(1, -6, 4), [3 - 5 ** 0.5, 3 + 5 ** 0.5]) else "faux"),
    E(62204, N2, 3,
      "Résoudre dans $\\mathbb{R}$ l'équation $(2x - 1)^2 = x + 2$.",
      "$\\mathcal{S} = \\left\\{\\dfrac{5 - \\sqrt{41}}{8} ; \\dfrac{5 + \\sqrt{41}}{8}\\right\\}$",
      "Développe et ramène tout dans un seul membre.",
      S("$(2x - 1)^2 = x + 2 \\iff 4x^2 - 4x + 1 - x - 2 = 0 \\iff 4x^2 - 5x - 1 = 0$.",
        "$\\Delta = 25 + 16 = 41 > 0$.",
        "$x = \\dfrac{5 \\pm \\sqrt{41}}{8}$."),
      verify=lambda: None if _same(_sp_roots(4, -5, -1), [(5 - 41 ** 0.5) / 8, (5 + 41 ** 0.5) / 8]) else "faux"),
    E(62205, N2, 2,
      "Résoudre sans calculer de discriminant : a) $x^2 - 5x = 0$ ; b) $4x^2 - 25 = 0$ ; c) $(x - 2)^2 = 9$.",
      "a) $\\{0 ; 5\\}$ ; b) $\\left\\{-\\dfrac{5}{2} ; \\dfrac{5}{2}\\right\\}$ ; c) $\\{-1 ; 5\\}$.",
      "Facteur commun, différence de deux carrés, racine carrée : choisis la voie la plus courte.",
      S("a) $x(x - 5) = 0$ : $x = 0$ ou $x = 5$.",
        "b) $(2x - 5)(2x + 5) = 0$ : $x = \\dfrac{5}{2}$ ou $x = -\\dfrac{5}{2}$.",
        "c) $x - 2 = 3$ ou $x - 2 = -3$ : $x = 5$ ou $x = -1$."),
      checks=("\\{0 ; 5\\}", "\\{-1 ; 5\\}")),
    E(62206, N2, 3,
      "Soit $m$ un réel non nul. Pour quelles valeurs de $m$ l'équation $mx^2 + 4x + 1 = 0$ n'a-t-elle aucune solution réelle ?",
      "Pour $m > 4$.",
      "C'est bien une équation du second degré car $m \\neq 0$ : étudie le signe de $\\Delta$ en fonction de $m$.",
      S("$\\Delta = 16 - 4m$.", "Aucune solution $\\iff \\Delta < 0 \\iff 16 - 4m < 0 \\iff m > 4$.",
        "Remarque : pour $m = 0$, l'équation $4x + 1 = 0$ a une solution, ce qui justifie l'hypothèse $m \\neq 0$."),
      checks=("m > 4",)),
    E(62207, N2, 4,
      "Résoudre dans $\\mathbb{R}$ l'équation $x^4 - 5x^2 + 4 = 0$ en posant $X = x^2$.",
      "$\\mathcal{S} = \\{-2 ; -1 ; 1 ; 2\\}$",
      "Résous d'abord l'équation en $X$, puis reviens à $x$ en tenant compte du signe de $X$.",
      S("Avec $X = x^2$ : $X^2 - 5X + 4 = 0$, $\\Delta = 25 - 16 = 9$, donc $X = 1$ ou $X = 4$.",
        "$x^2 = 1 \\iff x = \\pm 1$ et $x^2 = 4 \\iff x = \\pm 2$.",
        "Les deux valeurs de $X$ sont positives : l'équation a quatre solutions."),
      verify=lambda: None if sorted(float(r) for r in sp.solve(X**4 - 5 * X**2 + 4, X)) == [-2, -1, 1, 2] else "faux"),
    E(62208, N2, 2,
      "Un élève résout $-x^2 + 3x + 4 = 0$ et écrit : « $\\Delta = 3^2 - 4 \\times 1 \\times 4 = -7 < 0$, donc pas de solution ». "
      "Corriger.",
      "Ici $a = -1$ : $\\Delta = 9 + 16 = 25$ ; les solutions sont $-1$ et $4$.",
      "Repère bien le signe de $a$.",
      S("L'élève a pris $a = 1$ au lieu de $a = -1$.",
        "$\\Delta = 3^2 - 4 \\times (-1) \\times 4 = 9 + 16 = 25$.",
        "$x = \\dfrac{-3 \\pm 5}{-2}$ : $x = -1$ ou $x = 4$ (vérification : $-16 + 12 + 4 = 0$)."),
      verify=lambda: None if _same(_sp_roots(-1, 3, 4), [-1, 4]) else "faux"),
    E(62209, N2, 2,
      "Trouver deux entiers consécutifs dont le produit vaut $132$.",
      "$11$ et $12$, ou $-12$ et $-11$.",
      "Appelle $n$ le plus petit des deux entiers.",
      S("$n(n + 1) = 132 \\iff n^2 + n - 132 = 0$.", "$\\Delta = 1 + 528 = 529 = 23^2$, donc $n = \\dfrac{-1 \\pm 23}{2}$ : $n = 11$ ou $n = -12$.",
        "Deux couples conviennent : $(11 ; 12)$ et $(-12 ; -11)$."),
      verify=lambda: None if _same(_sp_roots(1, 1, -132), [-12, 11]) else "faux"),
    E(62210, N2, 4,
      "Démontrer que pour tout réel $m$, l'équation $x^2 + mx - 1 = 0$ admet deux solutions distinctes, et que ces solutions sont "
      "de signes contraires.",
      "$\\Delta = m^2 + 4 > 0$ et le produit des solutions vaut $-1 < 0$ : elles sont distinctes et de signes contraires.",
      "Le produit des racines vaut $\\dfrac{c}{a}$.",
      S("$\\Delta = m^2 - 4 \\times 1 \\times (-1) = m^2 + 4$, et $m^2 + 4 \\geqslant 4 > 0$ : deux solutions distinctes.",
        "Leur produit vaut $\\dfrac{c}{a} = -1$.",
        "Un produit strictement négatif impose deux facteurs de signes contraires."),
      checks=("m^2 + 4",)),
    E(62211, N2, 2,
      "Résoudre dans $\\mathbb{R}$ l'équation $x^2 + 2x = 2x^2 - 3$.",
      "$\\mathcal{S} = \\{-1 ; 3\\}$",
      "Regroupe tout dans un membre avant de calculer quoi que ce soit.",
      S("$x^2 + 2x - 2x^2 + 3 = 0 \\iff -x^2 + 2x + 3 = 0 \\iff x^2 - 2x - 3 = 0$.",
        "$\\Delta = 4 + 12 = 16$ : $x = \\dfrac{2 \\pm 4}{2}$.", "$x = -1$ ou $x = 3$."),
      verify=lambda: None if _same(_sp_roots(1, -2, -3), [-1, 3]) else "faux"),
    E(62212, N2, 4,
      "Résoudre dans $\\mathbb{R}$ l'équation $\\dfrac{1}{x} + \\dfrac{1}{x + 1} = 1$.",
      "$\\mathcal{S} = \\left\\{\\dfrac{1 - \\sqrt{5}}{2} ; \\dfrac{1 + \\sqrt{5}}{2}\\right\\}$",
      "Précise d'abord les valeurs interdites, puis multiplie par $x(x + 1)$.",
      S("Valeurs interdites : $0$ et $-1$.",
        "Pour $x \\notin \\{-1 ; 0\\}$ : $(x + 1) + x = x(x + 1) \\iff x^2 - x - 1 = 0$.",
        "$\\Delta = 5$ : $x = \\dfrac{1 \\pm \\sqrt{5}}{2}$, qui ne sont pas des valeurs interdites."),
      verify=lambda: None if _same(sorted(float(r) for r in sp.solve(1 / X + 1 / (X + 1) - 1, X)),
                                   [(1 - 5 ** 0.5) / 2, (1 + 5 ** 0.5) / 2]) else "faux"),

    # N3 — propriétés : racines, forme factorisée, somme et produit, factorisation
    E(62301, N3, 1,
      "Soit $f(x) = -2(x + 5)\\left(x - \\dfrac{1}{2}\\right)$. Donner les racines de $f$, puis calculer $f(0)$.",
      "Les racines sont $-5$ et $\\dfrac{1}{2}$ ; $f(0) = 5$.",
      "Un produit est nul si et seulement si l'un de ses facteurs est nul.",
      S("$f(x) = 0 \\iff x + 5 = 0$ ou $x - \\dfrac{1}{2} = 0$.", "Racines : $-5$ et $\\dfrac{1}{2}$.",
        "$f(0) = -2 \\times 5 \\times \\left(-\\dfrac{1}{2}\\right) = 5$."),
      checks=("f(0) = 5",)),
    E(62302, N3, 2,
      "Déterminer toutes les fonctions polynômes du second degré qui s'annulent en $2$ et en $-3$, puis celle qui vérifie $f(1) = 8$.",
      "Ce sont les fonctions $x \\mapsto a(x - 2)(x + 3)$ avec $a \\neq 0$ ; celle qui vérifie $f(1) = 8$ est $f(x) = -2(x - 2)(x + 3)$.",
      "Une fonction du second degré de racines $x_1$ et $x_2$ s'écrit $a(x - x_1)(x - x_2)$.",
      S("Les fonctions cherchées sont $f(x) = a(x - 2)(x + 3)$, $a$ réel non nul.",
        "$f(1) = a \\times (-1) \\times 4 = -4a$.", "$-4a = 8 \\iff a = -2$ : $f(x) = -2(x - 2)(x + 3) = -2x^2 - 2x + 12$."),
      checks=("-2(x - 2)(x + 3)",)),
    E(62303, N3, 2,
      "Vérifier que $1$ est racine évidente de $2x^2 - 3x + 1$, puis factoriser ce trinôme.",
      "$2x^2 - 3x + 1 = 2(x - 1)\\left(x - \\dfrac{1}{2}\\right) = (x - 1)(2x - 1)$.",
      "Une racine connue et le produit $\\dfrac{c}{a}$ suffisent.",
      S("$2 - 3 + 1 = 0$ : $1$ est racine.", "Produit des racines : $\\dfrac{1}{2}$, donc l'autre racine est $\\dfrac{1}{2}$.",
        "$2x^2 - 3x + 1 = 2(x - 1)\\left(x - \\dfrac{1}{2}\\right) = (x - 1)(2x - 1)$."),
      verify=lambda: None if _poly_eq("(x-1)*(2*x-1)", "2*x**2-3*x+1") else "faux"),
    E(62304, N3, 1,
      "Trouver mentalement les racines de $x^2 + x - 12$ à l'aide de leur somme et de leur produit, puis factoriser.",
      "Les racines sont $3$ et $-4$ : $x^2 + x - 12 = (x - 3)(x + 4)$.",
      "Cherche deux nombres de somme $-1$ et de produit $-12$.",
      S("Somme : $-\\dfrac{b}{a} = -1$ ; produit : $\\dfrac{c}{a} = -12$.", "$3 + (-4) = -1$ et $3 \\times (-4) = -12$.",
        "$x^2 + x - 12 = (x - 3)(x + 4)$."),
      verify=lambda: None if _poly_eq("(x-3)*(x+4)", "x**2+x-12") else "faux"),
    E(62305, N3, 2,
      "Factoriser en choisissant la méthode la plus adaptée : a) $9x^2 - 6x + 1$ ; b) $x^2 - 3x$ ; c) $x^2 - 16$ ; d) $x^2 - 4x + 2$.",
      "a) $(3x - 1)^2$ ; b) $x(x - 3)$ ; c) $(x - 4)(x + 4)$ ; d) $(x - 2 + \\sqrt{2})(x - 2 - \\sqrt{2})$.",
      "Identités remarquables et facteur commun d'abord ; les formules seulement si rien n'est visible.",
      S("a) Identité remarquable $a^2 - 2ab + b^2$ avec $a = 3x$, $b = 1$.", "b) Facteur commun $x$.", "c) Différence de deux carrés.",
        "d) Rien d'évident : $\\Delta = 8$, racines $2 \\pm \\sqrt{2}$, donc $(x - (2 - \\sqrt{2}))(x - (2 + \\sqrt{2}))$."),
      verify=lambda: None if _poly_eq("(x-2+sqrt(2))*(x-2-sqrt(2))", "x**2-4*x+2") and _poly_eq("(3*x-1)**2", "9*x**2-6*x+1") else "faux"),
    E(62306, N3, 3,
      "Déterminer un trinôme de coefficient $a = 1$ dont les racines sont $1 - \\sqrt{3}$ et $1 + \\sqrt{3}$.",
      "$x^2 - 2x - 2$.",
      "Calcule la somme et le produit des racines.",
      S("Somme : $(1 - \\sqrt{3}) + (1 + \\sqrt{3}) = 2$.", "Produit : $1^2 - (\\sqrt{3})^2 = 1 - 3 = -2$.",
        "Avec $a = 1$ : $x^2 - (\\text{somme})x + \\text{produit} = x^2 - 2x - 2$."),
      verify=lambda: None if _poly_eq("(x-1+sqrt(3))*(x-1-sqrt(3))", "x**2-2*x-2") else "faux"),
    E(62307, N3, 4,
      "On note $x_1$ et $x_2$ les racines de $x^2 - 7x + 3$. Sans les calculer, déterminer $x_1^2 + x_2^2$ et $\\dfrac{1}{x_1} + \\dfrac{1}{x_2}$.",
      "$x_1^2 + x_2^2 = 43$ et $\\dfrac{1}{x_1} + \\dfrac{1}{x_2} = \\dfrac{7}{3}$.",
      "Exprime chaque quantité à l'aide de $S = x_1 + x_2$ et $P = x_1 x_2$.",
      S("$\\Delta = 49 - 12 = 37 > 0$ : deux racines réelles, $S = 7$ et $P = 3$.",
        "$x_1^2 + x_2^2 = (x_1 + x_2)^2 - 2x_1x_2 = 49 - 6 = 43$.",
        "$\\dfrac{1}{x_1} + \\dfrac{1}{x_2} = \\dfrac{x_1 + x_2}{x_1 x_2} = \\dfrac{7}{3}$."),
      verify=lambda: None if abs(sum(r * r for r in _sp_roots(1, -7, 3)) - 43) < 1e-9 else "faux"),
    E(62308, N3, 2,
      "Trouver deux réels dont la somme vaut $5$ et le produit $-14$.",
      "Les deux réels sont $7$ et $-2$.",
      "Ce sont les racines de $x^2 - sx + p$.",
      S("Ils sont racines de $x^2 - 5x - 14 = 0$.", "$\\Delta = 25 + 56 = 81$ : $x = \\dfrac{5 \\pm 9}{2}$, soit $7$ et $-2$.",
        "Vérification : $7 + (-2) = 5$ et $7 \\times (-2) = -14$."),
      verify=lambda: None if _same(_sp_roots(1, -5, -14), [-2, 7]) else "faux"),
    E(62309, N3, 1,
      "Un élève écrit $3x^2 - 3x - 6 = (x + 1)(x - 2)$ car $-1$ et $2$ sont les racines. Corriger.",
      "Il manque le coefficient $a = 3$ : $3x^2 - 3x - 6 = 3(x + 1)(x - 2)$.",
      "Développe le produit proposé.",
      S("$(x + 1)(x - 2) = x^2 - x - 2$ : le coefficient de $x^2$ vaut $1$, pas $3$.", "La forme factorisée est $a(x - x_1)(x - x_2)$ avec $a = 3$.",
        "$3x^2 - 3x - 6 = 3(x + 1)(x - 2)$."),
      verify=lambda: None if _poly_eq("3*(x+1)*(x-2)", "3*x**2-3*x-6") else "faux"),
    E(62310, N3, 3,
      "Sans calculer les racines, déterminer le signe des racines de $2x^2 + 7x + 3$.",
      "Les deux racines sont strictement négatives.",
      "Le produit indique si les racines sont de même signe, la somme lequel.",
      S("$\\Delta = 49 - 24 = 25 > 0$ : deux racines.", "Produit $\\dfrac{3}{2} > 0$ : elles sont de même signe.",
        "Somme $-\\dfrac{7}{2} < 0$ : elles sont toutes deux négatives (ce sont $-3$ et $-\\dfrac{1}{2}$)."),
      verify=lambda: None if all(r < 0 for r in _sp_roots(2, 7, 3)) else "faux"),
    E(62311, N3, 4,
      "Déterminer les réels $m$ pour lesquels l'une des racines de $x^2 - mx + 12$ est le triple de l'autre.",
      "$m = 8$ (racines $2$ et $6$) ou $m = -8$ (racines $-2$ et $-6$).",
      "Appelle les racines $r$ et $3r$, puis écris le produit et la somme.",
      S("Produit : $r \\times 3r = 12$, donc $r^2 = 4$ et $r = 2$ ou $r = -2$.", "Somme : $r + 3r = 4r = m$.",
        "$r = 2$ donne $m = 8$ ; $r = -2$ donne $m = -8$ (vérification : $x^2 - 8x + 12 = (x - 2)(x - 6)$)."),
      verify=lambda: None if _poly_eq("(x-2)*(x-6)", "x**2-8*x+12") else "faux"),
    E(62312, N3, 4,
      "Soit $P(x) = x^3 - 2x^2 - 5x + 6$. Vérifier que $1$ est racine de $P$, déterminer les réels $b$ et $c$ tels que "
      "$P(x) = (x - 1)(x^2 + bx + c)$, puis résoudre $P(x) = 0$.",
      "$P(x) = (x - 1)(x^2 - x - 6) = (x - 1)(x - 3)(x + 2)$ ; $\\mathcal{S} = \\{-2 ; 1 ; 3\\}$.",
      "Développe $(x - 1)(x^2 + bx + c)$ et identifie les coefficients.",
      S("$P(1) = 1 - 2 - 5 + 6 = 0$.", "$(x - 1)(x^2 + bx + c) = x^3 + (b - 1)x^2 + (c - b)x - c$ : $b - 1 = -2$, $c - b = -5$, $-c = 6$, donc $b = -1$, $c = -6$.",
        "$x^2 - x - 6 = (x - 3)(x + 2)$ : les solutions sont $-2$, $1$ et $3$."),
      verify=lambda: None if _poly_eq("(x-1)*(x-3)*(x+2)", "x**3-2*x**2-5*x+6") else "faux"),

    # N4 — signe et inéquations
    E(62401, N4, 1,
      "Étudier le signe de $f(x) = -3(x - 2)(x + 1)$ sur $\\mathbb{R}$.",
      "$f(x) > 0$ sur $]-1 ; 2[$, $f(x) < 0$ sur $]-\\infty ; -1[ \\cup ]2 ; +\\infty[$, et $f$ s'annule en $-1$ et $2$.",
      "Le trinôme a le signe de $a$ à l'extérieur des racines.",
      S("Racines : $-1$ et $2$ ; $a = -3 < 0$.", "À l'extérieur des racines, $f$ est du signe de $a$ : négative.", "Entre les racines : positive."),
      verify=lambda: _ineq_numeric_ok(-3, 3, 6, ">", "")),
    E(62402, N4, 2,
      "Dresser le tableau de signes de $g(x) = (2x - 1)(3 - x)$, puis résoudre $g(x) > 0$.",
      "$g(x) > 0 \\iff x \\in \\left]\\dfrac{1}{2} ; 3\\right[$.",
      "Étudie le signe de chaque facteur, ou développe pour trouver $a$.",
      S("$2x - 1 > 0 \\iff x > \\dfrac{1}{2}$ et $3 - x > 0 \\iff x < 3$.", "Le produit est positif quand les deux facteurs ont le même signe : entre $\\dfrac{1}{2}$ et $3$.",
        "Contrôle : $g(x) = -2x^2 + 7x - 3$ a pour coefficient $a = -2 < 0$, positif entre les racines."),
      verify=lambda: _ineq_numeric_ok(-2, 7, -3, ">", "")),
    E(62403, N4, 2,
      "Résoudre dans $\\mathbb{R}$ l'inéquation $x^2 \\geqslant 4x$.",
      "$\\mathcal{S} = ]-\\infty ; 0] \\cup [4 ; +\\infty[$",
      "Ne divise surtout pas par $x$ : son signe est inconnu.",
      S("$x^2 \\geqslant 4x \\iff x^2 - 4x \\geqslant 0 \\iff x(x - 4) \\geqslant 0$.", "Racines $0$ et $4$, $a = 1 > 0$ : positif à l'extérieur.",
        "Diviser par $x$ aurait fait perdre les solutions négatives et $0$."),
      verify=lambda: _ineq_numeric_ok(1, -4, 0, ">=", "")),
    E(62404, N4, 1,
      "Résoudre dans $\\mathbb{R}$ : a) $2x^2 + 3 > 0$ ; b) $x^2 + 2x + 5 < 0$.",
      "a) $\\mathcal{S} = \\mathbb{R}$ ; b) $\\mathcal{S} = \\varnothing$.",
      "Regarde le signe du discriminant et celui de $a$.",
      S("a) $2x^2 \\geqslant 0$ donc $2x^2 + 3 \\geqslant 3 > 0$ pour tout $x$.",
        "b) $\\Delta = 4 - 20 = -16 < 0$ : le trinôme garde le signe de $a = 1$, il est toujours strictement positif.",
        "b) n'a donc aucune solution."),
      verify=lambda: _ineq_numeric_ok(1, 2, 5, "<", "")),
    E(62405, N4, 3,
      "Étudier la position relative de la parabole $\\mathcal{C}$ d'équation $y = x^2 + x - 2$ et de la droite $\\mathcal{D}$ d'équation $y = 2x + 4$.",
      "$\\mathcal{C}$ est au-dessus de $\\mathcal{D}$ sur $]-\\infty ; -2[ \\cup ]3 ; +\\infty[$, en dessous sur $]-2 ; 3[$ ; elles se coupent en $(-2 ; 0)$ et $(3 ; 10)$.",
      "Étudie le signe de la différence $(x^2 + x - 2) - (2x + 4)$.",
      S("$d(x) = x^2 + x - 2 - 2x - 4 = x^2 - x - 6 = (x - 3)(x + 2)$.", "$d(x) > 0$ à l'extérieur de $-2$ et $3$ ($a = 1 > 0$), $d(x) < 0$ entre.",
        "Points communs : $x = -2$ ($y = 0$) et $x = 3$ ($y = 10$)."),
      verify=lambda: _ineq_numeric_ok(1, -1, -6, ">", "")),
    E(62406, N4, 3,
      "Déterminer l'ensemble des réels $x$ pour lesquels $\\sqrt{6 + x - x^2}$ existe.",
      "$[-2 ; 3]$.",
      "Une racine carrée n'existe que si ce qui est sous la racine est positif ou nul.",
      S("Il faut $-x^2 + x + 6 \\geqslant 0$.", "Racines : $-2$ et $3$ ; $a = -1 < 0$ : positif entre les racines.", "Ensemble cherché : $[-2 ; 3]$."),
      verify=lambda: _ineq_numeric_ok(-1, 1, 6, ">=", "")),
    E(62407, N4, 4,
      "Résoudre dans $\\mathbb{R}$ l'inéquation $(x^2 - 1)(x + 3) < 0$.",
      "$\\mathcal{S} = ]-\\infty ; -3[ \\cup ]-1 ; 1[$",
      "Dresse un tableau de signes avec les facteurs $x^2 - 1$ et $x + 3$.",
      S("$x^2 - 1$ : positif à l'extérieur de $-1$ et $1$ ; $x + 3$ : positif pour $x > -3$.",
        "Signes du produit : $-$ sur $]-\\infty ; -3[$, $+$ sur $]-3 ; -1[$, $-$ sur $]-1 ; 1[$, $+$ sur $]1 ; +\\infty[$.",
        "Solutions : $]-\\infty ; -3[ \\cup ]-1 ; 1[$."),
      verify=lambda: None if all(((t * t - 1) * (t + 3) < 0) == (t < -3 or -1 < t < 1) for t in [k / 7 + 0.01 for k in range(-40, 40)]) else "faux"),
    E(62408, N4, 2,
      "Le bénéfice d'un artisan qui vend $x$ objets est $B(x) = -2x^2 + 28x - 80$ (en euros). Pour quelles quantités ne perd-il pas d'argent ?",
      "Pour $x \\in [4 ; 10]$, soit entre $4$ et $10$ objets.",
      "Ne pas perdre d'argent, c'est $B(x) \\geqslant 0$.",
      S("$B(x) \\geqslant 0 \\iff -2(x^2 - 14x + 40) \\geqslant 0 \\iff x^2 - 14x + 40 \\leqslant 0$.",
        "$x^2 - 14x + 40 = (x - 4)(x - 10)$, négatif entre $4$ et $10$.", "L'artisan ne perd pas d'argent pour $4 \\leqslant x \\leqslant 10$."),
      verify=lambda: _ineq_numeric_ok(-2, 28, -80, ">=", "")),
    E(62409, N4, 2,
      "Un élève écrit : « $-x^2 + 9 > 0 \\iff x^2 < 9 \\iff x < 3$ ». Corriger.",
      "$\\mathcal{S} = ]-3 ; 3[$ : l'élève a oublié les valeurs négatives.",
      "Pense au cas $x = -5$.",
      S("$x^2 < 9$ ne donne pas seulement $x < 3$ : par exemple $(-5)^2 = 25 > 9$.", "$-x^2 + 9 = (3 - x)(3 + x)$, de racines $-3$ et $3$ ; $a = -1$.",
        "Positif entre les racines : $\\mathcal{S} = ]-3 ; 3[$."),
      verify=lambda: _ineq_numeric_ok(-1, 0, 9, ">", "")),
    E(62410, N4, 4,
      "Déterminer les réels $m$ non nuls tels que $mx^2 + 2x + m < 0$ pour tout réel $x$.",
      "$m < -1$.",
      "Un trinôme est strictement négatif sur $\\mathbb{R}$ si et seulement si $a < 0$ et $\\Delta < 0$.",
      S("Il faut $m < 0$ et $\\Delta = 4 - 4m^2 < 0$.", "$4 - 4m^2 < 0 \\iff m^2 > 1 \\iff m < -1$ ou $m > 1$.",
        "Avec $m < 0$ : $m < -1$."),
      checks=("m < -1",)),
    E(62411, N4, 3,
      "Résoudre dans $\\mathbb{R}$ l'inéquation $4x^2 - 4x + 1 \\leqslant 0$.",
      "$\\mathcal{S} = \\left\\{\\dfrac{1}{2}\\right\\}$",
      "Reconnais une identité remarquable.",
      S("$4x^2 - 4x + 1 = (2x - 1)^2$.", "Un carré est positif ou nul : il est négatif ou nul seulement quand il vaut $0$.",
        "$(2x - 1)^2 = 0 \\iff x = \\dfrac{1}{2}$."),
      verify=lambda: None if _poly_eq("(2*x-1)**2", "4*x**2-4*x+1") else "faux"),

    # N5 — choisir une forme, problèmes
    E(62501, N5, 2,
      "On admet que $f(x) = -(x - 2)^2 + 9 = -(x + 1)(x - 5) = -x^2 + 4x + 5$. En choisissant chaque fois la forme la plus adaptée : "
      "a) calculer $f(0)$ ; b) résoudre $f(x) = 0$ ; c) donner le maximum de $f$ ; d) résoudre $f(x) = 5$.",
      "a) $5$ ; b) $\\{-1 ; 5\\}$ ; c) $9$, atteint en $2$ ; d) $\\{0 ; 4\\}$.",
      "Développée pour les images, factorisée pour $f(x) = 0$, canonique pour l'extremum.",
      S("a) Forme développée : $f(0) = 5$.", "b) Forme factorisée : $x = -1$ ou $x = 5$.", "c) Forme canonique : maximum $9$ en $x = 2$ ($a = -1 < 0$).",
        "d) $-x^2 + 4x + 5 = 5 \\iff -x(x - 4) = 0 \\iff x = 0$ ou $x = 4$."),
      verify=lambda: None if _poly_eq("-(x-2)**2+9", "-(x+1)*(x-5)") and _poly_eq("-(x+1)*(x-5)", "-x**2+4*x+5") else "faux"),
    E(62502, N5, 2,
      "Parmi les rectangles de périmètre $24$ cm, lequel a la plus grande aire ?",
      "Le carré de côté $6$ cm, d'aire $36$ cm².",
      "Exprime l'aire en fonction de la largeur $x$.",
      S("Si la largeur vaut $x$, la longueur vaut $12 - x$, avec $0 < x < 12$.", "$A(x) = x(12 - x) = -x^2 + 12x$, maximale pour $x = \\dfrac{12}{2} = 6$.",
        "$A(6) = 36$ : c'est un carré de côté $6$ cm."),
      checks=("$36$",)),
    E(62503, N5, 2,
      "Avec $60$ m de grillage, on clôture un enclos rectangulaire adossé à un mur (le côté le long du mur n'est pas grillagé). "
      "Quelles dimensions donnent la plus grande aire ?",
      "Les deux côtés perpendiculaires au mur mesurent $15$ m, le côté parallèle $30$ m ; l'aire maximale vaut $450$ m².",
      "Appelle $x$ la longueur d'un côté perpendiculaire au mur.",
      S("Le côté parallèle au mur mesure $60 - 2x$, avec $0 < x < 30$.", "$A(x) = x(60 - 2x) = -2x^2 + 60x$, maximale en $x = -\\dfrac{60}{2 \\times (-2)} = 15$.",
        "$A(15) = 15 \\times 30 = 450$."),
      checks=("$450$",)),
    E(62504, N5, 3,
      "Une balle est lancée verticalement ; sa hauteur (en m) au bout de $t$ secondes est $h(t) = -5t^2 + 20t + 25$. "
      "a) Quand touche-t-elle le sol ? b) Quelle hauteur maximale atteint-elle ? c) Pendant combien de temps est-elle au-dessus de $40$ m ?",
      "a) Au bout de $5$ s ; b) $45$ m, à $t = 2$ s ; c) pendant $2$ s (de $t = 1$ à $t = 3$).",
      "Factorise $h(t)$ en mettant $-5$ en facteur.",
      S("$h(t) = -5(t^2 - 4t - 5) = -5(t - 5)(t + 1)$ : $h(t) = 0$ pour $t = 5$ ($t = -1$ est exclu).",
        "Maximum en $t = \\dfrac{-20}{2 \\times (-5)} = 2$ : $h(2) = -20 + 40 + 25 = 45$.",
        "$h(t) \\geqslant 40 \\iff -5t^2 + 20t - 15 \\geqslant 0 \\iff t^2 - 4t + 3 \\leqslant 0 \\iff (t - 1)(t - 3) \\leqslant 0 \\iff 1 \\leqslant t \\leqslant 3$."),
      verify=lambda: None if _poly_eq("-5*(x-5)*(x+1)", "-5*x**2+20*x+25") and _poly_eq("(x-1)*(x-3)", "x**2-4*x+3") else "faux"),
    E(62505, N5, 2,
      "Un club fixe le prix $p$ (en euros) d'un abonnement. Il estime vendre $200 - 10p$ abonnements, pour $0 \\leqslant p \\leqslant 20$. "
      "Quel prix maximise la recette ? Quelle est cette recette ?",
      "Un prix de $10$ euros, pour une recette de $1\\,000$ euros.",
      "Recette = prix × nombre d'abonnements vendus.",
      S("$R(p) = p(200 - 10p) = -10p^2 + 200p$.", "Maximum en $p = \\dfrac{-200}{2 \\times (-10)} = 10$.", "$R(10) = 10 \\times 100 = 1\\,000$."),
      checks=("$10$",)),
    E(62506, N5, 3,
      "$ABCD$ est un carré de côté $6$. On place $M \\in [AB]$, $N \\in [BC]$, $P \\in [CD]$, $Q \\in [DA]$ avec $AM = BN = CP = DQ = x$. "
      "On admet que $MNPQ$ est un carré. a) Exprimer son aire en fonction de $x$. b) Pour quelle valeur est-elle minimale ? "
      "c) Pour quelles valeurs vaut-elle $20$ ?",
      "a) $A(x) = 2x^2 - 12x + 36$ ; b) minimale ($18$) pour $x = 3$ ; c) pour $x = 2$ ou $x = 4$.",
      "Le côté $MN$ est l'hypoténuse d'un triangle rectangle de côtés $x$ et $6 - x$.",
      S("Par Pythagore dans $MBN$ : $MN^2 = (6 - x)^2 + x^2 = 2x^2 - 12x + 36$.", "$A(x) = 2(x - 3)^2 + 18$ : minimum $18$ en $x = 3$.",
        "$A(x) = 20 \\iff 2x^2 - 12x + 16 = 0 \\iff x^2 - 6x + 8 = 0 \\iff x = 2$ ou $x = 4$."),
      verify=lambda: None if _poly_eq("(6-x)**2+x**2", "2*(x-3)**2+18") and _same(_sp_roots(1, -6, 8), [2, 4]) else "faux"),
    E(62507, N5, 3,
      "Déterminer les réels non nuls $x$ dont la somme avec leur inverse vaut $\\dfrac{10}{3}$.",
      "$x = 3$ ou $x = \\dfrac{1}{3}$.",
      "Multiplie par $3x$ (non nul) pour obtenir une équation du second degré.",
      S("$x + \\dfrac{1}{x} = \\dfrac{10}{3} \\iff 3x^2 + 3 = 10x \\iff 3x^2 - 10x + 3 = 0$ (pour $x \\neq 0$).",
        "$\\Delta = 100 - 36 = 64$ : $x = \\dfrac{10 \\pm 8}{6}$.", "$x = 3$ ou $x = \\dfrac{1}{3}$ (l'un est l'inverse de l'autre, ce qui était prévisible)."),
      verify=lambda: None if _same(_sp_roots(3, -10, 3), [1 / 3, 3]) else "faux"),
    E(62508, N5, 4,
      "Un jardin rectangulaire de $20$ m sur $12$ m est entouré d'une allée de largeur constante $x$ (à l'extérieur). "
      "L'aire de l'allée vaut $64$ m². Déterminer la valeur exacte de $x$, puis une valeur approchée au centimètre.",
      "$x = -8 + 4\\sqrt{5} \\approx 0{,}94$ m.",
      "Aire de l'allée = aire du grand rectangle − aire du jardin.",
      S("$(20 + 2x)(12 + 2x) - 240 = 64 \\iff 4x^2 + 64x - 64 = 0 \\iff x^2 + 16x - 16 = 0$.",
        "$\\Delta = 256 + 64 = 320 = (8\\sqrt{5})^2$ : $x = \\dfrac{-16 \\pm 8\\sqrt{5}}{2} = -8 \\pm 4\\sqrt{5}$.",
        "Une largeur est positive : $x = -8 + 4\\sqrt{5} \\approx 0{,}94$ m."),
      verify=lambda: None if abs((20 + 2 * (-8 + 4 * 5 ** 0.5)) * (12 + 2 * (-8 + 4 * 5 ** 0.5)) - 240 - 64) < 1e-9 else "faux"),
    E(62509, N5, 4,
      "Un cycliste parcourt $60$ km. S'il roulait $5$ km/h plus vite, il mettrait une heure de moins. Quelle est sa vitesse ?",
      "$15$ km/h.",
      "Écris les deux durées $\\dfrac{60}{v}$ et $\\dfrac{60}{v + 5}$.",
      S("$\\dfrac{60}{v} - \\dfrac{60}{v + 5} = 1$ avec $v > 0$.", "En multipliant par $v(v + 5)$ : $60(v + 5) - 60v = v(v + 5) \\iff v^2 + 5v - 300 = 0$.",
        "$\\Delta = 25 + 1\\,200 = 1\\,225 = 35^2$ : $v = \\dfrac{-5 + 35}{2} = 15$ (l'autre racine, $-20$, est exclue). Contrôle : $4$ h contre $3$ h."),
      verify=lambda: None if _same(_sp_roots(1, 5, -300), [-20, 15]) else "faux"),
    E(62510, N5, 3,
      "Soit $f(x) = 2x^2 - 8x + 6$. Écrire $f$ sous forme canonique et sous forme factorisée, puis utiliser la forme adaptée pour "
      "donner l'extremum de $f$ et le signe de $f(x)$.",
      "$f(x) = 2(x - 2)^2 - 2 = 2(x - 1)(x - 3)$ ; minimum $-2$ en $x = 2$ ; $f(x) < 0$ sur $]1 ; 3[$ et $f(x) > 0$ en dehors de $[1 ; 3]$.",
      "Forme canonique pour l'extremum, forme factorisée pour le signe.",
      S("$f(x) = 2(x^2 - 4x) + 6 = 2\\left((x - 2)^2 - 4\\right) + 6 = 2(x - 2)^2 - 2$.", "$f(x) = 2(x^2 - 4x + 3) = 2(x - 1)(x - 3)$.",
        "Minimum $-2$ en $2$ ; signe de $a = 2$ à l'extérieur de $1$ et $3$, négatif entre."),
      verify=lambda: None if _poly_eq("2*(x-2)**2-2", "2*(x-1)*(x-3)") else "faux"),
    E(62511, N5, 4,
      "Dans un repère orthonormé, $M$ est un point de la parabole d'équation $y = x^2$ et $A(0 ; 2)$. Déterminer la distance minimale $AM$.",
      "La distance minimale vaut $\\dfrac{\\sqrt{7}}{2}$, atteinte pour $x = \\pm\\sqrt{\\dfrac{3}{2}}$.",
      "Minimise $AM^2$ en posant $X = x^2$.",
      S("$AM^2 = x^2 + (x^2 - 2)^2 = x^4 - 3x^2 + 4$.", "Avec $X = x^2 \\geqslant 0$ : $X^2 - 3X + 4 = \\left(X - \\dfrac{3}{2}\\right)^2 + \\dfrac{7}{4}$, minimal pour $X = \\dfrac{3}{2}$.",
        "$AM^2$ minimal vaut $\\dfrac{7}{4}$, donc $AM$ minimal vaut $\\dfrac{\\sqrt{7}}{2}$."),
      verify=lambda: None if _poly_eq("(x-sp.Rational(3,2))**2+sp.Rational(7,4)".replace("sp.", ""), "x**2-3*x+4") else "faux"),
]

EXERCISES = HIST + MANUELS + NOUVEAUX

QUIZ = {
    "fonction-polynome-de-degre-2": (62105, 62109, 62106),
    "equations-du-second-degre": (62201, 62202, 62211),
    "proprietes-d-un-trinome": (62301, 62304, 62302),
    "signe-du-trinome-et-inequations": (62401, 62404, 62403),
    "second-degre-modeliser-et-optimiser": (62501, 62502, 62505),
}

# ── Adaptation au manuel « Première ES/L » (2026-10-26) ─────────────────────
# Voir PREMIERE_SPECIFIQUE_SUIVI.md. Hors manuel, retirés de la banque servie
# (conservés ici, jamais supprimés) : la notion « Modéliser et optimiser » et,
# dans « Racines et factorisation », les exercices fondés sur la somme et le
# produit des racines ou sur un polynôme de degré 3.
_IDS_HORS_PERIMETRE = {
    472, 474, 475, 476, 477, 478, 479, 480, 481, 482, 484, 487, 488, 489, 490, 493, 494, 495, 497, 499, 500, 501,
    502, 503, 504, 505, 508, 509, 512, 513, 514, 516, 517, 518, 519, 520, 522, 524, 525, 526, 527, 528, 529, 530,
    62304, 62307, 62308, 62310, 62311, 62312,
}
EXERCICES_HORS_PERIMETRE = [e for e in EXERCISES if e.notion == N5 or e.id in _IDS_HORS_PERIMETRE]
_hors = {e.id for e in EXERCICES_HORS_PERIMETRE}
EXERCISES = [e for e in EXERCISES if e.id not in _hors]

# « Calcul numérique et algébrique » n'est plus une notion autonome (2026-10-26,
# décision utilisateur) : les rappels utiles sont dans les méthodes du cours.
# Exercices de l'ancien chapitre « Automatismes » (textes inchangés) : ceux qui
# servent directement une notion du chapitre y sont rattachés ; 73202
# (développer) et 73205 (fractions) restent en réserve (reserve/banque_ch13.py).
from dataclasses import replace as _replace  # noqa: E402

from premiere_specifique.reserve.banque_ch13 import EXERCISES as _AUTOMATISMES  # noqa: E402

_RATTACHES = {73201: N2, 73203: N3, 73204: N4}  # produit nul, x² − 25, signe de −2x + 6
EXERCISES += [_replace(e, notion=_RATTACHES[e.id]) for e in _AUTOMATISMES if e.id in _RATTACHES]
NOTIONS = (N1, N2, N3, N4)
NOTION_IDS = (
    "fonction-polynome-de-degre-2",
    "equations-du-second-degre",
    "proprietes-d-un-trinome",
    "signe-du-trinome-et-inequations",
)
QUIZ = {
    "fonction-polynome-de-degre-2": (62105, 62109, 62106),
    "equations-du-second-degre": (62201, 62202, 62211),
    "proprietes-d-un-trinome": (62301, 62303, 62302),
    "signe-du-trinome-et-inequations": (62401, 62404, 62403),
}


# Factorisation selon le signe de Δ (manuel « Première ES/L », Ch. 3 III) :
# exercices créés lors de l'adaptation (bloc 83 300), contrôlés par SymPy.
_x = sp.Symbol("x")


def _factorisation_juste(trinome, facto):
    return lambda: None if sp.expand(trinome - facto) == 0 else "factorisation fausse"


EXERCISES += [
    E(83301, N3, 1,
      "Factoriser $P(x) = 2x^2 - 2x - 12$.",
      "$P(x) = 2(x + 2)(x - 3)$.",
      "Calcule le discriminant, puis les racines.",
      S("$\\Delta = (-2)^2 - 4 \\times 2 \\times (-12) = 4 + 96 = 100 > 0$.", "$x_1 = \\dfrac{2 - 10}{4} = -2$ et $x_2 = \\dfrac{2 + 10}{4} = 3$.",
        "$P(x) = 2(x + 2)(x - 3)$."),
      checks=("2(x + 2)(x - 3)",), verify=_factorisation_juste(2 * _x ** 2 - 2 * _x - 12, 2 * (_x + 2) * (_x - 3))),
    E(83302, N3, 2,
      "Factoriser $Q(x) = 4x^2 - 12x + 9$.",
      "$Q(x) = 4\\left(x - \\dfrac{3}{2}\\right)^2$, soit $(2x - 3)^2$.",
      "Le discriminant est nul.",
      S("$\\Delta = (-12)^2 - 4 \\times 4 \\times 9 = 144 - 144 = 0$ : une racine double.", "$x_0 = -\\dfrac{-12}{2 \\times 4} = \\dfrac{3}{2}$.",
        "$Q(x) = 4\\left(x - \\dfrac{3}{2}\\right)^2 = (2x - 3)^2$."),
      checks=("(2x - 3)^2",), verify=_factorisation_juste(4 * _x ** 2 - 12 * _x + 9, (2 * _x - 3) ** 2)),
    E(83303, N3, 2,
      "Le trinôme $R(x) = 3x^2 - 4x + 2$ peut-il s'écrire comme produit de facteurs du premier degré ? Justifier.",
      "Non : $\\Delta = -8 < 0$, donc $R$ n'a pas de racine réelle et ne se factorise pas.",
      "Calcule le discriminant.",
      S("$\\Delta = (-4)^2 - 4 \\times 3 \\times 2 = 16 - 24 = -8$.", "$\\Delta < 0$ : $R$ n'a aucune racine réelle.",
        "Un facteur $(x - r)$ donnerait la racine $r$ : $R$ ne se factorise pas."),
      checks=("-8",), verify=lambda: None if (-4) ** 2 - 4 * 3 * 2 == -8 else "discriminant faux"),
    E(83304, N3, 3,
      "Factoriser $P(x) = 5x^2 - 10x - 5$.",
      "$P(x) = 5\\left(x - 1 + \\sqrt{2}\\right)\\left(x - 1 - \\sqrt{2}\\right)$.",
      "Calcule $\\Delta$ et simplifie $\\sqrt{\\Delta}$.",
      S("$\\Delta = (-10)^2 - 4 \\times 5 \\times (-5) = 100 + 100 = 200$ et $\\sqrt{200} = 10\\sqrt{2}$.",
        "$x_1 = \\dfrac{10 - 10\\sqrt{2}}{10} = 1 - \\sqrt{2}$ et $x_2 = 1 + \\sqrt{2}$.",
        "$P(x) = 5\\left(x - (1 - \\sqrt{2})\\right)\\left(x - (1 + \\sqrt{2})\\right) = 5\\left(x - 1 + \\sqrt{2}\\right)\\left(x - 1 - \\sqrt{2}\\right)$."),
      checks=("x - 1 + \\sqrt{2}",),
      verify=_factorisation_juste(5 * _x ** 2 - 10 * _x - 5, 5 * (_x - 1 + sp.sqrt(2)) * (_x - 1 - sp.sqrt(2)))),
]
