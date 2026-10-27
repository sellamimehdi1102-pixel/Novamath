"""Chapitre 7 (ancien chapitre 1) — Suites numériques, modèles discrets : banque curée.

Exercices historiques (identifiants conservés, banque_ch01_historiques.py) :
textes réécrits (français corrigé : plus de « le nombre de individus » ni de
« nouveaux/nouvelles »), réponses complètes (tous les termes demandés), sens
de variation précisé (rang à partir duquel la suite est monotone), tableaux
de valeurs de limites recalculés à partir de vraies suites (les anciens
tableaux ne correspondaient à aucune suite). Valeurs recalculées par
Fraction / SymPy.

Nouveaux exercices : bloc 61 000 (voir banque_commun.ID_BASE).
"""
from fractions import Fraction as F

import sympy as sp

from premiere_specifique.banque_ch07_historiques import HISTORIQUES
from premiere_specifique.banque_commun import E, S, code, fr, par, poly_tex, pw

CHAPTER_NUMBER = 7  # ancien chapitre 1 (adaptation au manuel « Première ES/L », 2026-10-26)
N1 = "Généralités sur les suites"
N2 = "Sens de variation d'une suite"
N3 = "Suite arithmétique"
N4 = "Suite géométrique"
N5 = "Calcul de sommes"
N6 = "Notion de limite d'une suite"
NOTIONS = (N1, N2, N3, N4, N5, N6)
NOTION_IDS = (
    "generalites-sur-les-suites",
    "sens-de-variation-d-une-suite",
    "suite-arithmetique",
    "suite-geometrique",
    "calcul-de-sommes",
    "notion-de-limite-d-une-suite",
)

n_ = sp.symbols("n", integer=True, nonnegative=True)


def dec(q) -> str:
    """Rationnel décimal écrit à la française (« 481{,}22 »), sinon fraction."""
    q = F(q)
    d = q.denominator
    while d % 2 == 0:
        d //= 2
    while d % 5 == 0:
        d //= 5
    if d != 1:
        return fr(q)
    s = f"{float(q):.10f}".rstrip("0").rstrip(".")
    return s.replace(".", "{,}")


def approx(x: float) -> str:
    """Valeur approchée à 4 chiffres significatifs, écriture française,
    notation scientifique a × 10^k pour les très grands ou très petits nombres."""
    if x == 0:
        return "0"
    mant, exp = f"{x:.3e}".split("e")
    exp = int(exp)
    if -3 <= exp <= 6:
        s = f"{x:.{max(0, 3 - exp)}f}".rstrip("0").rstrip(".") if "." in f"{x:.{max(0, 3 - exp)}f}" else f"{x:.0f}"
        ent, _, frac_ = s.partition(".")
        neg = ent.startswith("-")
        ent = ent.lstrip("-")
        groups = []
        while len(ent) > 3:
            groups.insert(0, ent[-3:])
            ent = ent[:-3]
        ent = "\\,".join([ent] + groups)
        return ("-" if neg else "") + ent + ("{,}" + frac_ if frac_ else "")
    return f"{mant.rstrip('0').rstrip('.').replace('.', '{,}')} \\times 10^{{{exp}}}"


def _sym(expr_tex):
    return sp.sympify(expr_tex.replace("^", "**").replace("n", "*n").lstrip("*").replace("(*n", "(n")
                      .replace("+*n", "+n").replace("-*n", "-n").replace(" *n", " n"), locals={"n": n_})


def _expr(expr_tex):
    """« -4n^2 + 3n », « n + 6 » -> expression SymPy en n."""
    s = expr_tex.replace(" ", "").replace("^", "**")
    s = sp.parsing.sympy_parser.parse_expr(
        s, local_dict={"n": n_},
        transformations=sp.parsing.sympy_parser.standard_transformations
        + (sp.parsing.sympy_parser.implicit_multiplication_application,))
    return s


# ── Familles historiques ─────────────────────────────────────────────────────


def _recurrence_affine(i, u0, a, b, k):
    terms = [F(u0)]
    for _ in range(k):
        terms.append(a * terms[-1] + b)
    rel = (f"u_n {'+' if b > 0 else '-'} {abs(b)}" if a == 1 else
           f"{'-' if a == -1 else a}u_n {'+' if b > 0 else '-'} {abs(b)}")
    lines = [f"$u_{{{j + 1}}} = {'' if a == 1 else ('-' if a == -1 else str(a) + ' \\times ')}{pw(terms[j])} {'+' if b > 0 else '-'} {abs(b)} = {dec(terms[j + 1])}$"
             for j in range(k)]
    asked = sorted({1, 2, k})
    ans = ", ".join(f"$u_{{{j}}} = {dec(terms[j])}$" for j in asked)
    return E(i, N1, 1 if a == 1 else 2,
             f"Soit $(u_n)$ la suite définie par $u_0 = {u0}$ et, pour tout entier naturel $n$, $u_{{n+1}} = {rel}$. "
             f"Calculer {', '.join(f'$u_{{{j}}}$' for j in asked[:-1])} et $u_{{{asked[-1]}}}$.",
             ans + ".",
             "Chaque terme se calcule à partir du précédent : remplace $u_n$ par la valeur que tu viens de trouver.",
             S(*lines),
             checks=tuple(dec(terms[j]) for j in asked))


def _explicite(i, expr, k):
    e = _expr(expr)
    v = e.subs(n_, k)
    subst = expr.replace("n", f"\\times {k}" if False else f"{k}")
    return E(i, N1, 1 if sp.degree(e, n_) <= 1 else 2,
             f"On considère la suite $(u_n)$ définie pour tout entier naturel $n$ par $u_n = {expr}$. Calculer $u_{{{k}}}$ et $u_{{{k + 1}}}$.",
             f"$u_{{{k}}} = {v}$ et $u_{{{k + 1}}} = {e.subs(n_, k + 1)}$.",
             "Remplace $n$ par l'indice demandé dans la formule explicite.",
             S(f"$u_n$ est donné en fonction de $n$ : on remplace directement $n$ par ${k}$, puis par ${k + 1}$.",
               f"$u_{{{k}}} = {v}$.",
               f"$u_{{{k + 1}}} = {e.subs(n_, k + 1)}$ (aucun besoin de connaître $u_{{{k}}}$ pour calculer $u_{{{k + 1}}}$ : c'est l'avantage d'une formule explicite)."),
             checks=(f"u_{{{k}}} = {v}",))


_MODELES = {
    17: ("une population de poissons compte $373$ individus", "le nombre de poissons", "le nombre de poissons augmente de $14\\,\\%$, puis $56$ poissons sont ajoutés par un alevinage", "poissons", True),
    23: ("une colonie de bactéries compte $211$ milliers d'individus", "le nombre de bactéries, en milliers", "$14\\,\\%$ des bactéries disparaissent, puis $58$ milliers de nouvelles bactéries apparaissent", "milliers de bactéries", True),
    25: ("un capital de $530$ euros est placé", "le capital, en euros", "le capital augmente de $20\\,\\%$ (intérêts), puis $57$ euros sont versés", "euros", False),
    28: ("une entreprise compte $713$ salariés", "le nombre de salariés", "$28\\,\\%$ des salariés partent, puis $48$ personnes sont embauchées", "salariés", True),
    29: ("un forum en ligne compte $611$ membres", "le nombre de membres", "$18\\,\\%$ des membres quittent le forum, puis $53$ nouveaux membres s'inscrivent", "membres", True),
    37: ("une colonie de bactéries compte $456$ milliers d'individus", "le nombre de bactéries, en milliers", "le nombre de bactéries augmente de $21\\,\\%$, puis $48$ milliers de bactéries s'ajoutent", "milliers de bactéries", True),
    41: ("une entreprise compte $369$ salariés", "le nombre de salariés", "le nombre de salariés augmente de $15\\,\\%$, puis $37$ personnes supplémentaires sont embauchées", "salariés", True),
    55: ("une chaîne vidéo compte $900$ abonnés", "le nombre d'abonnés", "$13\\,\\%$ des abonnés se désabonnent, puis $34$ nouveaux abonnés s'inscrivent", "abonnés", True),
}


def _modele(i, _ctx, u0, unit, pct, ajout):
    debut, grandeur, regle, unite, entier = _MODELES[i]
    coef = 1 + F(pct, 100)
    u1 = coef * u0 + ajout
    approx = entier and u1.denominator != 1
    tail = f", soit environ ${round(u1)}$ {unite}" if approx else ""
    return E(i, N1, 2,
             f"En 2024, {debut}. On note $u_n$ {grandeur} l'année $2024 + n$, donc $u_0 = {u0}$. Chaque année, {regle}. "
             f"1) Exprimer $u_{{n+1}}$ en fonction de $u_n$. 2) Calculer $u_1$.",
             f"$u_{{n+1}} = {dec(coef)}\\,u_n {'+' if ajout > 0 else '-'} {abs(ajout)}$ et $u_1 = {dec(u1)}${tail}.",
             f"{'Augmenter' if pct > 0 else 'Diminuer'} de $p\\,\\%$ revient à multiplier par $1 {'+' if pct > 0 else '-'} \\dfrac{{p}}{{100}}$.",
             S(f"{'Une hausse' if pct > 0 else 'Une baisse'} de ${abs(pct)}\\,\\%$ multiplie la valeur par ${dec(coef)}$ ; on ajoute ensuite ${ajout}$.",
               f"Donc $u_{{n+1}} = {dec(coef)}\\,u_n + {ajout}$ pour tout entier naturel $n$.",
               f"$u_1 = {dec(coef)} \\times {u0} + {ajout} = {dec(u1)}$." + (f" Comme on compte des {unite}, on arrondit : environ ${round(u1)}$." if approx else "")),
             checks=(dec(u1),))


def _arith_terme(i, u0, r, k):
    v = u0 + k * r
    return E(i, N3, 1,
             f"Soit $(u_n)$ une suite arithmétique de premier terme $u_0 = {u0}$ et de raison $r = {r}$. Donner l'expression de $u_n$ "
             f"en fonction de $n$, puis calculer $u_{{{k}}}$.",
             f"$u_n = {poly_tex([r, u0], 'n')}$ et $u_{{{k}}} = {v}$.",
             "Terme général d'une suite arithmétique : $u_n = u_0 + nr$.",
             S(f"$u_n = u_0 + nr = {u0} + {par(r)}n = {poly_tex([r, u0], 'n')}$.", f"$u_{{{k}}} = {u0} + {k} \\times {par(r)} = {v}$."),
             checks=(f"u_{{{k}}} = {v}",))


def _arith_test(i, expr):
    e = _expr(expr)
    d = sp.simplify(e.subs(n_, n_ + 1) - e)
    is_ar = d.free_symbols == set()
    diff_tex = sp.latex(sp.expand(d)).replace("n", "n")
    return E(i, N3, 1 if is_ar else 2,
             f"La suite $(v_n)$ définie pour tout entier naturel $n$ par $v_n = {expr}$ est-elle arithmétique ? Justifier.",
             (f"Oui : $v_{{n+1}} - v_n = {d}$ pour tout $n$, donc $(v_n)$ est arithmétique de raison ${d}$." if is_ar else
              f"Non : $v_{{n+1}} - v_n = {diff_tex}$ dépend de $n$ (par exemple $v_1 - v_0 = {e.subs(n_, 1) - e.subs(n_, 0)}$ et $v_2 - v_1 = {e.subs(n_, 2) - e.subs(n_, 1)}$)."),
             "Calcule $v_{n+1} - v_n$ : la suite est arithmétique si cette différence est une constante.",
             S(f"$v_{{n+1}} - v_n = {sp.latex(sp.expand(e.subs(n_, n_ + 1)))} - ({expr}) = {diff_tex}$.",
               ("La différence ne dépend pas de $n$ : la suite est arithmétique." if is_ar else
                "La différence dépend de $n$ : deux écarts successifs ne sont pas égaux, la suite n'est pas arithmétique.")))


def _geo_terme(i, u0, q, k):
    q = F(q)
    v = u0 * q ** k
    qt = fr(q) if q.denominator == 1 and q > 0 else f"\\left({fr(q)}\\right)"
    return E(i, N4, 1 if q.denominator == 1 else 2,
             f"Soit $(u_n)$ une suite géométrique de premier terme $u_0 = {u0}$ et de raison $q = {fr(q)}$. Donner l'expression de $u_n$ "
             f"en fonction de $n$, puis calculer $u_{{{k}}}$.",
             f"$u_n = {u0} \\times {qt}^n$ et $u_{{{k}}} = {fr(v)}$.",
             "Terme général d'une suite géométrique : $u_n = u_0 \\times q^n$.",
             S(f"$u_n = u_0 \\times q^n = {u0} \\times {qt}^n$.", f"$u_{{{k}}} = {u0} \\times {qt}^{{{k}}} = {u0} \\times {fr(q ** k)} = {fr(v)}$."),
             checks=(f"u_{{{k}}} = {fr(v)}",))


def _geo_raison(i, u0, u3):
    u3 = F(u3)
    q = F(round(float(u3 / u0) ** (1 / 3) * 1000), 1000)
    q = min((F(a, b) for a in range(1, 10) for b in range(1, 10) if F(a, b) ** 3 == u3 / u0), key=lambda z: z)
    return E(i, N4, 2,
             f"Une suite géométrique $(u_n)$ à termes strictement positifs vérifie $u_0 = {u0}$ et $u_3 = {fr(u3)}$. Déterminer sa raison $q$, "
             f"puis $u_5$.",
             f"$q = {fr(q)}$ et $u_5 = {fr(u0 * q ** 5)}$.",
             "Écris $u_3 = u_0 \\times q^3$ et cherche le nombre positif dont le cube convient.",
             S(f"$u_3 = u_0 q^3$ donc $q^3 = \\dfrac{{u_3}}{{u_0}} = {fr(u3 / u0)}$.",
               f"Les termes étant positifs, $q > 0$ et $q = {fr(q)}$ (car ${pw(q)}^3 = {fr(q ** 3)}$).",
               f"$u_5 = {u0} \\times {pw(q)}^5 = {fr(u0 * q ** 5)}$."),
             checks=(f"q = {fr(q)}",))


def _geo_test(i, v0, rec):
    is_geo = "v_n +" not in rec and "v_n -" not in rec
    q = rec.replace("v_n", "").strip() if is_geo else None
    terms = [v0]
    for _ in range(3):
        terms.append(-2 * terms[-1] if is_geo else terms[-1] + 1)
    return E(i, N4, 1,
             f"La suite $(v_n)$ définie par $v_0 = {v0}$ et, pour tout entier naturel $n$, $v_{{n+1}} = {rec}$ est-elle géométrique ? Justifier.",
             (f"Oui : on passe d'un terme au suivant en multipliant toujours par ${q}$ ; $(v_n)$ est géométrique de raison ${q}$." if is_geo else
              f"Non : $\\dfrac{{v_1}}{{v_0}} = \\dfrac{{{terms[1]}}}{{{terms[0]}}}$ et $\\dfrac{{v_2}}{{v_1}} = \\dfrac{{{terms[2]}}}{{{terms[1]}}}$ sont différents."),
             "Une suite est géométrique si l'on passe de chaque terme au suivant en multipliant par un même nombre.",
             S(f"Premiers termes : ${terms[0]}$, ${terms[1]}$, ${terms[2]}$, ${terms[3]}$.",
               ("La relation $v_{n+1} = q\\,v_n$ est vérifiée avec un $q$ constant." if is_geo else
                "La relation ajoute $1$ au lieu de multiplier : elle est arithmétique, et les quotients successifs ne sont pas constants.")))


def _somme_arith(i, u0, r, k):
    first, last = u0, u0 + k * r
    s = F((k + 1) * (first + last), 2)
    assert s == sum(u0 + j * r for j in range(k + 1)), i
    s = fr(s)
    return E(i, N5, 2,
             f"Soit $(u_n)$ une suite arithmétique de premier terme $u_0 = {u0}$ et de raison $r = {r}$. Calculer $S = u_0 + u_1 + \\cdots + u_{{{k}}}$.",
             f"$S = {s}$.",
             "Somme de termes consécutifs d'une suite arithmétique : nombre de termes × (premier + dernier) ÷ 2.",
             S(f"Il y a ${k} - 0 + 1 = {k + 1}$ termes.", f"$u_{{{k}}} = {u0} + {k} \\times {par(r)} = {last}$.",
               f"$S = {k + 1} \\times \\dfrac{{{first} + {par(last)}}}{{2}} = {s}$."),
             checks=(f"S = {s}",))


def _somme_geo(i, u0, q, k):
    q = F(q)
    s = u0 * (1 - q ** k) / (1 - q)
    return E(i, N5, 2,
             f"Soit $(u_n)$ une suite géométrique de premier terme $u_0 = {u0}$ et de raison $q = {fr(q)}$. Calculer la somme $S$ des ${k}$ "
             f"premiers termes (de $u_0$ à $u_{{{k - 1}}}$).",
             f"$S = {fr(s)}$.",
             "Utilise $1 + q + \\cdots + q^{n} = \\dfrac{1 - q^{n+1}}{1 - q}$ pour $q \\neq 1$.",
             S(f"$S = u_0(1 + q + \\cdots + q^{{{k - 1}}}) = {u0} \\times \\dfrac{{1 - {pw(q)}^{{{k}}}}}{{1 - {pw(q)}}}$.",
               f"${pw(q)}^{{{k}}} = {fr(q ** k)}$, donc $S = {u0} \\times \\dfrac{{{fr(1 - q ** k)}}}{{{fr(1 - q)}}} = {fr(s)}$."),
             checks=(f"S = {fr(s)}",))


def _somme_entiers(i, k):
    s = k * (k + 1) // 2
    return E(i, N5, 1,
             f"Calculer la somme $S = 1 + 2 + 3 + \\cdots + {k}$.",
             f"$S = {s}$.",
             "Utilise $1 + 2 + \\cdots + n = \\dfrac{n(n+1)}{2}$.",
             S(f"$S = \\dfrac{{{k} \\times {k + 1}}}{{2}} = {s}$.", f"Contrôle : il y a ${k}$ termes, de moyenne $\\dfrac{{1 + {k}}}{{2}}$."),
             checks=(f"S = {s}",))


def _variation_ref(i, kind, raison, u0):
    raison = F(raison)
    if kind == "arith":
        sens = "croissante" if raison > 0 else "décroissante"
        why = f"la raison $r = {fr(raison)}$ est {'positive' if raison > 0 else 'négative'} : $u_{{n+1}} - u_n = r$"
        return E(i, N2, 1,
                 f"Soit $(u_n)$ une suite arithmétique de raison $r = {fr(raison)}$ et de premier terme $u_0 = {u0}$. Quel est son sens de variation ?",
                 f"$(u_n)$ est strictement {sens}.",
                 "Pour une suite arithmétique, regarde le signe de la raison.",
                 S(f"Pour tout $n$, $u_{{n+1}} - u_n = r = {fr(raison)}$.", f"Le signe de $r$ donne le sens : {why} {'> 0' if raison > 0 else '< 0'}."))
    croit = (u0 > 0) == (raison > 1)
    sens = "croissante" if croit else "décroissante"
    return E(i, N2, 2,
             f"Soit $(u_n)$ une suite géométrique de raison $q = {fr(raison)}$ et de premier terme $u_0 = {u0}$. Quel est son sens de variation ?",
             f"$(u_n)$ est strictement {sens}.",
             "Calcule $u_{n+1} - u_n = u_n(q - 1)$ et étudie son signe ; attention au signe de $u_0$.",
             S(f"$u_{{n+1}} - u_n = u_0 q^n (q - 1)$ avec $q^n > 0$.",
               f"$u_0 = {u0}$ est {'positif' if u0 > 0 else 'négatif'} et $q - 1 = {fr(raison - 1)}$ est {'positif' if raison > 1 else 'négatif'}.",
               f"Le produit est {'positif' if croit else 'négatif'} : la suite est strictement {sens}."))


def _variation_geo(i, u0, q):
    q = F(q)
    sens = "croissante" if q > 1 else "décroissante"
    return E(i, N2, 1,
             f"Soit $(u_n)$ la suite définie pour tout entier naturel $n$ par $u_n = {u0} \\times {pw(q)}^n$. Étudier son sens de variation.",
             f"$(u_n)$ est strictement {sens}.",
             "Les termes sont strictement positifs : compare $\\dfrac{u_{n+1}}{u_n}$ à $1$.",
             S("Pour tout $n$, $u_n > 0$.", f"$\\dfrac{{u_{{n+1}}}}{{u_n}} = {fr(q)}$, {'supérieur' if q > 1 else 'inférieur'} à $1$.",
               f"Donc $u_{{n+1}} {'>' if q > 1 else '<'} u_n$ : la suite est strictement {sens}."))


def _variation_quad(i, expr):
    e = _expr(expr)
    d = sp.expand(e.subs(n_, n_ + 1) - e)
    a1, a0 = sp.Poly(d, n_).all_coeffs() if sp.degree(d, n_) == 1 else (0, d)
    a1, a0 = int(a1), int(a0)
    # d = a1 n + a0 : signe pour n >= 0
    if a1 > 0:
        rank = max(0, -(-(-a0) // a1)) if a0 < 0 else 0
        while a1 * rank + a0 <= 0:
            rank += 1
        sens, symb = "croissante", ">"
    else:
        rank = 0
        while a1 * rank + a0 >= 0:
            rank += 1
        sens, symb = "décroissante", "<"
    if rank == 0:
        ans = f"$(u_n)$ est strictement {sens}."
        concl = f"Pour tout $n \\geqslant 0$, ${sp.latex(d)} {symb} 0$ : la suite est strictement {sens}."
    else:
        ans = f"$(u_n)$ est strictement {sens} à partir du rang ${rank}$ (et pas avant : $u_{{{rank}}} {'>' if sens == 'décroissante' else '<'}\\!= u_{{{rank - 1}}}$ ou l'inverse)."
        ans = f"$(u_n)$ est strictement {sens} à partir du rang $n = {rank}$."
        concl = (f"${sp.latex(d)} {symb} 0 \\iff n \\geqslant {rank}$ (pour $n$ entier) : la suite est strictement {sens} à partir du rang ${rank}$ "
                 f"(contrôle : $u_{{{rank - 1}}} = {e.subs(n_, rank - 1)}$, $u_{{{rank}}} = {e.subs(n_, rank)}$, $u_{{{rank + 1}}} = {e.subs(n_, rank + 1)}$).")
    return E(i, N2, 2 if rank == 0 else 3,
             f"Étudier le sens de variation de la suite $(u_n)$ définie pour tout entier naturel $n$ par $u_n = {expr}$.",
             ans,
             "Calcule $u_{n+1} - u_n$ en développant, puis étudie son signe selon $n$.",
             S(f"$u_{{n+1}} - u_n = {sp.latex(sp.expand(e.subs(n_, n_ + 1)))} - ({expr}) = {sp.latex(d)}$.", concl))


def _limite_geo(i, u0, q):
    q = F(q)
    conv = abs(q) < 1
    return E(i, N6, 1,
             f"Soit $(u_n)$ la suite définie par $u_n = {u0} \\times {pw(q)}^n$. Calculer $u_5$, $u_{{10}}$ et $u_{{20}}$ (valeurs approchées si besoin), "
             f"puis conjecturer le comportement de $(u_n)$ quand $n$ devient grand.",
             (f"Les termes se rapprochent de $0$ : on conjecture que $(u_n)$ converge vers $0$." if conv else
              f"Les termes deviennent aussi grands que l'on veut : on conjecture que $(u_n)$ tend vers $+\\infty$."),
             f"Observe ce que deviennent les puissances de ${fr(q)}$.",
             S(f"$u_5 \\approx {approx(u0 * float(q) ** 5)}$, $u_{{10}} \\approx {approx(u0 * float(q) ** 10)}$, "
               f"$u_{{20}} \\approx {approx(u0 * float(q) ** 20)}$.",
               ("Multiplier sans cesse par un nombre entre $0$ et $1$ fait rapprocher les termes de $0$." if conv else
                "Multiplier sans cesse par un nombre supérieur à $1$ fait grandir les termes sans limite.")))


def _limite_inverse(i, l, k):
    return E(i, N6, 1,
             f"Soit $(u_n)$ la suite définie pour tout entier naturel non nul $n$ par $u_n = {l} {'+' if k > 0 else '-'} \\dfrac{{{abs(k)}}}{{n}}$. "
             f"Calculer $u_{{10}}$, $u_{{100}}$ et $u_{{1\\,000}}$, puis conjecturer la limite de $(u_n)$.",
             f"On conjecture que $(u_n)$ converge vers ${l}$.",
             "Que devient $\\dfrac{1}{n}$ quand $n$ devient très grand ?",
             S(f"$u_{{10}} = {dec(F(l) + F(k, 10))}$, $u_{{100}} = {dec(F(l) + F(k, 100))}$, $u_{{1\\,000}} = {dec(F(l) + F(k, 1000))}$.",
               f"$\\dfrac{{{abs(k)}}}{{n}}$ se rapproche de $0$, donc $u_n$ se rapproche de ${l}$."),
             checks=(f"vers ${l}$",))


_FAMILIES = {"recurrence_affine": _recurrence_affine, "explicite": _explicite, "modele": _modele, "arith_terme": _arith_terme,
             "arith_test": _arith_test, "geo_terme": _geo_terme, "geo_raison": _geo_raison, "geo_test": _geo_test,
             "somme_arith": _somme_arith, "somme_geo": _somme_geo, "somme_entiers": _somme_entiers,
             "variation_ref": _variation_ref, "variation_geo": _variation_geo, "variation_quad": _variation_quad,
             "limite_geo": _limite_geo, "limite_inverse": _limite_inverse}

HIST = [_FAMILIES[fam](i, *params) for i, fam, params in HISTORIQUES if fam != "limite_table"]


def _limite_table(i, expr_tex, f, ns, concl, level=1):
    vals = [f(F(k)) for k in ns]
    return E(i, N6, level,
             f"Pour la suite définie par $u_n = {expr_tex}$, on a calculé quelques termes : "
             + ", ".join(f"$u_{{{k}}} = {dec(v) if abs(v) < 10**7 else sp.latex(sp.Integer(int(v)))}$" for k, v in zip(ns, vals))
             + ". Conjecturer le comportement de $(u_n)$ quand $n$ devient grand.",
             concl,
             "Regarde si les termes se rapprochent d'un nombre, grandissent sans fin ou oscillent.",
             S("On lit l'évolution des termes quand $n$ augmente.", concl.replace("On conjecture", "On peut conjecturer")))


MANUELS = [
    E(71, N3, 2,
      "Une suite arithmétique $(u_n)$ vérifie $u_0 = 0$ et $u_8 = 48$. Déterminer sa raison $r$, puis calculer $u_{20}$.",
      "$r = 6$ et $u_{20} = 120$.",
      "Entre $u_0$ et $u_8$, on ajoute $8$ fois la raison.",
      S("$u_8 = u_0 + 8r$, donc $8r = 48$ et $r = 6$.", "$u_{20} = u_0 + 20r = 120$."),
      checks=("r = 6", "u_{20} = 120")),
    _limite_table(295, "-n^3", lambda k: -k ** 3, (1, 10, 100, 1000), "On conjecture que $(u_n)$ tend vers $-\\infty$."),
    _limite_table(296, "3 + \\dfrac{1}{n}", lambda k: 3 + 1 / k, (1, 10, 100, 1000), "On conjecture que $(u_n)$ converge vers $3$."),
    _limite_table(302, "(-1)^n", lambda k: (-1) ** int(k), (100, 101, 102, 103), "Les termes valent alternativement $1$ et $-1$ : la suite ne semble pas avoir de limite."),
    _limite_table(315, "\\dfrac{1}{2} + \\dfrac{1}{n}", lambda k: F(1, 2) + 1 / k, (1, 10, 100, 1000), "On conjecture que $(u_n)$ converge vers $\\dfrac{1}{2}$.", 2),
    _limite_table(322, "-1 + \\dfrac{1}{n}", lambda k: -1 + 1 / k, (1, 10, 100, 1000), "On conjecture que $(u_n)$ converge vers $-1$.", 2),
]

LEGACY_IDS = tuple(e.id for e in HIST + MANUELS)

# ── Nouveaux exercices ──────────────────────────────────────────────────────

NOUVEAUX = [
    # N1 — modes de génération, notations, motifs, algorithmes
    E(61101, N1, 1,
      "On construit une rangée de carrés avec des allumettes : $1$ carré utilise $4$ allumettes, $2$ carrés côte à côte en utilisent $7$, "
      "$3$ carrés en utilisent $10$. On note $u_n$ le nombre d'allumettes pour $n$ carrés. Exprimer $u_{n+1}$ en fonction de $u_n$, "
      "puis $u_n$ en fonction de $n$.",
      "$u_{n+1} = u_n + 3$ et $u_n = 3n + 1$.",
      "Combien d'allumettes faut-il ajouter pour fermer un carré de plus ?",
      S("Ajouter un carré à droite demande $3$ allumettes (le côté gauche existe déjà) : $u_{n+1} = u_n + 3$.",
        "On part de $u_1 = 4$ et on ajoute $3$ à chaque carré : $u_n = 4 + 3(n - 1) = 3n + 1$.",
        "Contrôle : $u_3 = 10$."),
      checks=("u_n = 3n + 1",)),
    E(61102, N1, 2,
      "Les nombres triangulaires comptent les points d'un triangle : $T_1 = 1$, $T_2 = 3$, $T_3 = 6$, $T_4 = 10$. "
      "a) Exprimer $T_{n+1}$ en fonction de $T_n$. b) Vérifier sur les premiers termes que $T_n = \\dfrac{n(n+1)}{2}$, puis calculer $T_{50}$.",
      "a) $T_{n+1} = T_n + (n + 1)$ ; b) la formule redonne $1$, $3$, $6$, $10$, et $T_{50} = 1\\,275$.",
      "Pour passer d'un triangle au suivant, on ajoute une ligne de points.",
      S("Le triangle suivant a une ligne de plus, de $n + 1$ points : $T_{n+1} = T_n + n + 1$.",
        "$\\dfrac{1 \\times 2}{2} = 1$, $\\dfrac{2 \\times 3}{2} = 3$, $\\dfrac{3 \\times 4}{2} = 6$, $\\dfrac{4 \\times 5}{2} = 10$.",
        "$T_{50} = \\dfrac{50 \\times 51}{2} = 1\\,275$."),
      checks=("1\\,275",)),
    E(61103, N1, 1,
      "On considère le programme Python suivant : " + code("u = 5") + " puis " + code("for k in range(3): u = 2*u - 3") + " puis " + code("print(u)") + ". Qu'affiche-t-il ? "
      "Quelle suite permet-il de calculer ?",
      "Il affiche $19$ ; il calcule $u_3$ pour la suite définie par $u_0 = 5$ et $u_{n+1} = 2u_n - 3$.",
      "Exécute la boucle à la main en notant la valeur de " + code("u") + " après chaque passage.",
      S("Avant la boucle : $u = 5$.", "Passages : $2 \\times 5 - 3 = 7$, puis $2 \\times 7 - 3 = 11$, puis $2 \\times 11 - 3 = 19$.",
        "" + code("range(3)") + " fait exécuter la boucle $3$ fois : la valeur affichée est $u_3 = 19$."),
      checks=("$19$",), verify=lambda: None if (lambda u: [u := 2 * u - 3 for _ in range(3)][-1])(5) == 19 else "faux"),
    E(61104, N1, 2,
      "La suite de Fibonacci est définie par $F_0 = 0$, $F_1 = 1$ et $F_{n+2} = F_{n+1} + F_n$. a) Calculer $F_2$ à $F_{10}$. "
      "b) Compléter le programme Python qui renvoie la liste $[F_0, F_1, \\ldots, F_n]$ : " + code("L = [0, 1]") + " puis " + code("for k in range(2, n + 1): L.append(...)") + ".",
      "a) $1$, $2$, $3$, $5$, $8$, $13$, $21$, $34$, $55$ ; b) " + code("L.append(L[k - 1] + L[k - 2])") + ".",
      "Chaque terme est la somme des deux précédents ; dans la liste, ils ont les indices $k - 1$ et $k - 2$.",
      S("$F_2 = 1$, $F_3 = 2$, $F_4 = 3$, $F_5 = 5$, $F_6 = 8$, $F_7 = 13$, $F_8 = 21$, $F_9 = 34$, $F_{10} = 55$.",
        "Au moment d'ajouter $F_k$, la liste contient déjà $F_0, \\ldots, F_{k-1}$ : " + code("L[k - 1]") + " et " + code("L[k - 2]") + " sont les deux derniers termes.",
        "La relation est une récurrence d'ordre $2$ : il faut DEUX termes initiaux."),
      checks=("55", "L[k - 1] + L[k - 2]")),
    E(61105, N1, 2,
      "Suite de Syracuse : on part d'un entier $u_0 > 0$ ; si $u_n$ est pair, $u_{n+1} = \\dfrac{u_n}{2}$, sinon $u_{n+1} = 3u_n + 1$. "
      "Écrire les termes pour $u_0 = 6$ jusqu'à obtenir $1$. Combien d'étapes faut-il ?",
      "$6, 3, 10, 5, 16, 8, 4, 2, 1$ : il faut $8$ étapes.",
      "Applique la règle terme après terme en regardant la parité.",
      S("$6$ pair donne $3$ ; $3$ impair donne $10$ ; $10$ donne $5$ ; $5$ donne $16$.", "$16 \\to 8 \\to 4 \\to 2 \\to 1$.",
        "On compte les passages d'un terme au suivant : $8$."),
      checks=("$8$",)),
    E(61106, N1, 2,
      "Dans un tournoi, chacun des $n$ joueurs affronte une fois chacun des autres. On note $m_n$ le nombre de matchs. "
      "Calculer $m_2$, $m_3$, $m_4$, justifier que $m_{n+1} = m_n + n$, puis donner $m_{20}$ sachant que $m_n = \\dfrac{n(n-1)}{2}$.",
      "$m_2 = 1$, $m_3 = 3$, $m_4 = 6$ ; $m_{20} = 190$.",
      "Quand un nouveau joueur arrive, contre combien de joueurs doit-il jouer ?",
      S("Avec $2$ joueurs : $1$ match ; avec $3$ : $3$ ; avec $4$ : $6$.",
        "Le $(n+1)$-ième joueur affronte les $n$ joueurs déjà présents : $m_{n+1} = m_n + n$.",
        "$m_{20} = \\dfrac{20 \\times 19}{2} = 190$."),
      checks=("190",)),
    E(61107, N1, 1,
      "Soit $(u_n)$ définie par $u_n = f(n)$ avec $f(x) = \\dfrac{x}{x + 1}$. Calculer $u_0$, $u_1$, $u_9$, puis exprimer $u_{n+1}$ en fonction de $n$.",
      "$u_0 = 0$, $u_1 = \\dfrac{1}{2}$, $u_9 = \\dfrac{9}{10}$ et $u_{n+1} = \\dfrac{n + 1}{n + 2}$.",
      "$u_{n+1}$ s'obtient en remplaçant $n$ par $n + 1$, pas en ajoutant $1$ au résultat.",
      S("$u_0 = \\dfrac{0}{1} = 0$, $u_1 = \\dfrac{1}{2}$, $u_9 = \\dfrac{9}{10}$.", "$u_{n+1} = f(n + 1) = \\dfrac{n + 1}{n + 2}$ (et non $u_n + 1$)."),
      checks=("\\dfrac{n + 1}{n + 2}",)),
    E(61108, N1, 3,
      "Écrire une fonction Python " + code("terme(n)") + " qui renvoie $u_n$ pour la suite définie par $u_0 = 2$ et $u_{n+1} = 0{,}5u_n + 3$, "
      "puis donner la valeur renvoyée par " + code("terme(3)") + ".",
      "" + code("def terme(n):") + " / " + code("u = 2") + " / " + code("for k in range(n): u = 0.5*u + 3") + " / " + code("return u") + " ; " + code("terme(3)") + " renvoie $5{,}5$.",
      "Une boucle qui répète $n$ fois la relation de récurrence à partir de $u_0$.",
      S("La boucle " + code("for k in range(n)") + " applique $n$ fois la relation.", "$u_1 = 4$, $u_2 = 5$, $u_3 = 5{,}5$.",
        "La fonction renvoie la dernière valeur de " + code("u") + ", ici $5{,}5$."),
      checks=("5{,}5",)),
    E(61109, N1, 3,
      "Une suite vérifie $u_0 = 1$ et $u_{n+1} = u_n + 2n + 3$. Calculer $u_1$, $u_2$, $u_3$, $u_4$, conjecturer une formule explicite, "
      "puis la vérifier.",
      "$u_1 = 4$, $u_2 = 9$, $u_3 = 16$, $u_4 = 25$ ; $u_n = (n + 1)^2$.",
      "Les valeurs obtenues sont des nombres bien connus.",
      S("$u_1 = 1 + 3 = 4$, $u_2 = 4 + 5 = 9$, $u_3 = 9 + 7 = 16$, $u_4 = 16 + 9 = 25$.", "Conjecture : $u_n = (n + 1)^2$.",
        "Vérification : $(n + 2)^2 - (n + 1)^2 = 2n + 3$, et $(0 + 1)^2 = 1 = u_0$ : la formule vérifie la même relation et le même premier terme."),
      checks=("(n + 1)^2",)),
    E(61110, N1, 4,
      "Tour de Hanoï : pour déplacer $n$ disques, on déplace les $n - 1$ disques du dessus, puis le grand disque, puis de nouveau les $n - 1$ disques. "
      "On note $h_n$ le nombre minimal de déplacements ($h_1 = 1$). Exprimer $h_{n+1}$ en fonction de $h_n$, montrer que $v_n = h_n + 1$ est "
      "géométrique, puis en déduire $h_n$ et $h_{10}$.",
      "$h_{n+1} = 2h_n + 1$ ; $v_{n+1} = 2v_n$ avec $v_1 = 2$, donc $v_n = 2^n$ et $h_n = 2^n - 1$ ; $h_{10} = 1\\,023$.",
      "Ajoute $1$ aux deux membres de la relation de récurrence.",
      S("Avec $n + 1$ disques : $h_n$ déplacements, puis $1$, puis $h_n$ : $h_{n+1} = 2h_n + 1$.",
        "$v_{n+1} = h_{n+1} + 1 = 2h_n + 2 = 2(h_n + 1) = 2v_n$ : $(v_n)$ est géométrique de raison $2$, avec $v_1 = 2$.",
        "$v_n = 2 \\times 2^{n-1} = 2^n$, donc $h_n = 2^n - 1$ et $h_{10} = 1\\,023$."),
      checks=("1\\,023",)),

    # N2 — sens de variation
    E(61201, N2, 1,
      "Étudier le sens de variation de la suite définie par $u_n = 5 - \\dfrac{2}{n + 1}$ pour $n \\in \\mathbb{N}$.",
      "$(u_n)$ est strictement croissante.",
      "Compare $\\dfrac{2}{n + 2}$ et $\\dfrac{2}{n + 1}$.",
      S("$u_{n+1} - u_n = \\dfrac{2}{n + 1} - \\dfrac{2}{n + 2} = \\dfrac{2}{(n + 1)(n + 2)}$.", "Ce quotient est strictement positif.",
        "Donc $u_{n+1} > u_n$ pour tout $n$ : la suite est strictement croissante."),
      checks=()),
    E(61202, N2, 2,
      "Soit $u_n = \\dfrac{3^n}{n + 1}$ pour $n \\in \\mathbb{N}$. Justifier que $u_n > 0$, calculer $\\dfrac{u_{n+1}}{u_n}$ et en déduire le sens de variation.",
      "$\\dfrac{u_{n+1}}{u_n} = \\dfrac{3(n + 1)}{n + 2} > 1$ : la suite est strictement croissante.",
      "Pour une suite à termes strictement positifs, comparer le quotient $\\dfrac{u_{n+1}}{u_n}$ à $1$ suffit.",
      S("$3^n > 0$ et $n + 1 > 0$, donc $u_n > 0$.", "$\\dfrac{u_{n+1}}{u_n} = \\dfrac{3^{n+1}}{n + 2} \\times \\dfrac{n + 1}{3^n} = \\dfrac{3(n + 1)}{n + 2}$.",
        "$3(n + 1) - (n + 2) = 2n + 1 > 0$, donc le quotient est supérieur à $1$ : $u_{n+1} > u_n$."),
      checks=()),
    E(61203, N2, 2,
      "Soit $f(x) = x^2 - 6x$ et $u_n = f(n)$. a) Étudier les variations de $f$ sur $[3 ; +\\infty[$. b) En déduire le sens de variation de "
      "$(u_n)$ à partir du rang $3$. c) La suite est-elle croissante sur $\\mathbb{N}$ ?",
      "a) $f$ est croissante sur $[3 ; +\\infty[$ ; b) $(u_n)$ est strictement croissante à partir du rang $3$ ; c) non, car $u_0 = 0 > u_1 = -5$.",
      "Si $f$ est croissante sur $[k ; +\\infty[$, alors $u_n = f(n)$ est croissante à partir du rang $k$.",
      S("$f(x) = (x - 3)^2 - 9$ : $f$ est strictement croissante sur $[3 ; +\\infty[$.", "Pour $3 \\leqslant n < n + 1$ : $f(n) < f(n + 1)$, donc $u_n < u_{n+1}$.",
        "$u_0 = 0$ et $u_1 = -5$ : la suite commence par décroître, elle n'est pas croissante sur $\\mathbb{N}$."),
      checks=()),
    E(61204, N2, 1,
      "La suite définie par $u_n = (-1)^n$ est-elle croissante ? décroissante ?",
      "Ni l'une ni l'autre : elle n'est pas monotone.",
      "Compare $u_0$, $u_1$ et $u_2$.",
      S("$u_0 = 1$, $u_1 = -1$, $u_2 = 1$.", "$u_1 < u_0$ empêche la croissance ; $u_2 > u_1$ empêche la décroissance.",
        "Une suite peut n'être ni croissante ni décroissante."),
      checks=()),
    E(61205, N2, 3,
      "Soit $(u_n)$ définie par $u_0 = 1$ et $u_{n+1} = u_n + n^2 - 4$. Étudier le signe de $u_{n+1} - u_n$ et en déduire le sens de variation "
      "de $(u_n)$.",
      "$(u_n)$ décroît de $u_0$ à $u_2$, puis $u_3 = u_2$, puis elle est strictement croissante à partir du rang $3$.",
      "Ici $u_{n+1} - u_n$ est donné directement par la relation.",
      S("$u_{n+1} - u_n = n^2 - 4 = (n - 2)(n + 2)$.", "Pour $n \\in \\mathbb{N}$ : négatif pour $n < 2$, nul pour $n = 2$, positif pour $n > 2$.",
        "$u_0 = 1$, $u_1 = -3$, $u_2 = -6$, $u_3 = -6$, $u_4 = -1$ : décroissante jusqu'au rang $2$, puis strictement croissante à partir du rang $3$."),
      checks=()),
    E(61206, N2, 4,
      "Vrai ou faux : « si $f$ est croissante sur $\\mathbb{R}$ et $u_{n+1} = f(u_n)$, alors la suite $(u_n)$ est croissante ». "
      "Justifier avec $f(x) = 2x$.",
      "Faux : avec $f(x) = 2x$ et $u_0 = -1$, on obtient $u_n = -2^n$, suite strictement décroissante.",
      "Le sens de variation d'une suite définie par récurrence dépend aussi du premier terme.",
      S("$f(x) = 2x$ est croissante sur $\\mathbb{R}$.", "Avec $u_0 = -1$ : $u_1 = -2$, $u_2 = -4$, … ; $u_n = -2^n$.",
        "$u_{n+1} - u_n = -2^n < 0$ : la suite est décroissante. Un seul contre-exemple suffit pour montrer que l'affirmation est fausse."),
      checks=()),
    E(61207, N2, 2,
      "Un capital de $2\\,000$ € diminue de $5\\,\\%$ par an. On note $c_n$ le capital après $n$ années. Quel est le sens de variation de $(c_n)$ ? Justifier.",
      "$(c_n)$ est strictement décroissante.",
      "Écris $c_{n+1}$ en fonction de $c_n$.",
      S("$c_{n+1} = 0{,}95\\,c_n$ : suite géométrique de raison $0{,}95$ et de premier terme $c_0 = 2\\,000 > 0$.",
        "$c_{n+1} - c_n = -0{,}05\\,c_n < 0$ car $c_n > 0$.", "La suite est strictement décroissante."),
      checks=()),

    # N3 — suites arithmétiques
    E(61301, N3, 1,
      "Un abonnement coûte $20$ € à l'inscription puis $3$ € par mois. On note $a_n$ le coût total après $n$ mois. Montrer que $(a_n)$ est arithmétique, "
      "donner $a_n$ en fonction de $n$, puis le coût après deux ans.",
      "$a_n = 20 + 3n$ ; après $24$ mois, le coût est $92$ €.",
      "Le coût augmente chaque mois de la même quantité.",
      S("$a_{n+1} = a_n + 3$ : la suite est arithmétique de raison $3$ et de premier terme $a_0 = 20$.", "$a_n = 20 + 3n$.", "$a_{24} = 20 + 72 = 92$."),
      checks=("$92$",)),
    E(61302, N3, 2,
      "Une suite arithmétique vérifie $u_5 = 17$ et $u_{12} = 45$. Déterminer sa raison, son premier terme $u_0$, puis $u_n$ en fonction de $n$.",
      "$r = 4$, $u_0 = -3$ et $u_n = 4n - 3$.",
      "Entre $u_5$ et $u_{12}$, on ajoute $7$ fois la raison.",
      S("$u_{12} - u_5 = 7r$, donc $7r = 28$ et $r = 4$.", "$u_5 = u_0 + 5r$, donc $u_0 = 17 - 20 = -3$.", "$u_n = -3 + 4n$."),
      checks=("r = 4", "u_0 = -3")),
    E(61303, N3, 2,
      "Une suite arithmétique a pour premier terme $u_1 = 7$ et pour raison $r = -2$. Donner $u_n$ en fonction de $n$, puis $u_{30}$.",
      "$u_n = 7 - 2(n - 1) = 9 - 2n$ ; $u_{30} = -51$.",
      "Le premier terme est $u_1$ : entre $u_1$ et $u_n$, on ajoute $n - 1$ fois la raison.",
      S("$u_n = u_1 + (n - 1)r = 7 - 2(n - 1) = 9 - 2n$.", "$u_{30} = 9 - 60 = -51$.", "Erreur fréquente : écrire $u_n = 7 - 2n$, ce qui donnerait $u_1 = 5$."),
      checks=("u_{30} = -51",)),
    E(61304, N3, 2,
      "Les points de coordonnées $(n ; u_n)$ d'une suite $(u_n)$ sont alignés sur la droite d'équation $y = -1{,}5x + 6$. "
      "Que peut-on dire de la suite ? Donner $u_0$ et la raison.",
      "C'est une suite arithmétique de premier terme $u_0 = 6$ et de raison $-1{,}5$.",
      "Une suite arithmétique est la restriction à $\\mathbb{N}$ d'une fonction affine.",
      S("$u_n = -1{,}5n + 6$ pour tout entier naturel $n$.", "$u_{n+1} - u_n = -1{,}5$ : la suite est arithmétique de raison $-1{,}5$.",
        "$u_0 = 6$ (ordonnée à l'origine) ; la raison est le coefficient directeur."),
      checks=("u_0 = 6",)),
    E(61305, N3, 3,
      "Soit $u_n = 3n - 50$. À partir de quel rang a-t-on $u_n > 1\\,000$ ?",
      "À partir du rang $n = 351$.",
      "Résous l'inéquation $3n - 50 > 1\\,000$ dans les entiers.",
      S("$3n - 50 > 1\\,000 \\iff 3n > 1\\,050 \\iff n > 350$.", "Le plus petit entier qui convient est $351$.",
        "Contrôle : $u_{350} = 1\\,000$ (pas strictement supérieur) et $u_{351} = 1\\,003$."),
      checks=("351",)),
    E(61306, N3, 4,
      "Soit $u_n = (n + 1)^2 - n^2$. Montrer que $(u_n)$ est arithmétique, puis calculer $u_0 + u_1 + \\cdots + u_{99}$ de deux façons.",
      "$u_n = 2n + 1$ est arithmétique de raison $2$ ; la somme vaut $10\\,000$.",
      "Développe $(n + 1)^2$ ; pour la somme, pense aussi aux simplifications en cascade.",
      S("$u_n = n^2 + 2n + 1 - n^2 = 2n + 1$ : $u_{n+1} - u_n = 2$, raison $2$, $u_0 = 1$.",
        "Première méthode : $100 \\times \\dfrac{u_0 + u_{99}}{2} = 100 \\times \\dfrac{1 + 199}{2} = 10\\,000$.",
        "Seconde méthode : $(1^2 - 0^2) + (2^2 - 1^2) + \\cdots + (100^2 - 99^2) = 100^2 = 10\\,000$ (les termes se simplifient deux à deux)."),
      checks=("10\\,000",)),
    E(61307, N3, 3,
      "Le prix d'une course de taxi est $4{,}20$ € de prise en charge, plus $1{,}60$ € par kilomètre. On note $p_n$ le prix pour $n$ km. "
      "Avec $30$ €, quelle distance maximale (en km entiers) peut-on parcourir ?",
      "$16$ km.",
      "Écris $p_n$, puis résous $p_n \\leqslant 30$.",
      S("$p_n = 4{,}2 + 1{,}6n$ : suite arithmétique de raison $1{,}6$.", "$4{,}2 + 1{,}6n \\leqslant 30 \\iff n \\leqslant 16{,}125$.", "On peut parcourir au plus $16$ km ($p_{16} = 29{,}80$ €)."),
      checks=("16",)),

    # N4 — suites géométriques
    E(61401, N4, 1,
      "Une ville compte $25\\,000$ habitants en 2025 ; sa population augmente de $3\\,\\%$ par an. On note $p_n$ la population l'année $2025 + n$. "
      "Exprimer $p_n$ en fonction de $n$ et estimer la population en 2035.",
      "$p_n = 25\\,000 \\times 1{,}03^n$ ; en 2035, environ $33\\,598$ habitants.",
      "Une hausse de $3\\,\\%$ revient à multiplier par $1{,}03$.",
      S("$p_{n+1} = 1{,}03\\,p_n$ : suite géométrique de raison $1{,}03$.", "$p_n = 25\\,000 \\times 1{,}03^n$.", "$p_{10} = 25\\,000 \\times 1{,}03^{10} \\approx 33\\,597{,}9$, soit environ $33\\,598$ habitants."),
      checks=("33\\,598",)),
    E(61402, N4, 2,
      "Un médicament est éliminé à raison de $20\\,\\%$ par heure. La dose initiale est $500$ mg. Au bout de combien d'heures restera-t-il moins de $100$ mg ?",
      "Au bout de $8$ heures.",
      "La quantité est multipliée par $0{,}8$ chaque heure ; calcule les termes successifs.",
      S("$q_n = 500 \\times 0{,}8^n$.", "$q_7 = 500 \\times 0{,}8^7 \\approx 104{,}9$ et $q_8 \\approx 83{,}9$.", "Il reste moins de $100$ mg à partir de $8$ heures."),
      checks=("$8$",)),
    E(61403, N4, 2,
      "Une suite géométrique vérifie $u_2 = 12$ et $u_5 = 96$. Déterminer sa raison et $u_0$.",
      "$q = 2$ et $u_0 = 3$.",
      "Entre $u_2$ et $u_5$, on multiplie trois fois par $q$.",
      S("$u_5 = u_2 \\times q^3$, donc $q^3 = 8$ et $q = 2$.", "$u_2 = u_0 \\times q^2$, donc $u_0 = \\dfrac{12}{4} = 3$.", "Contrôle : $u_5 = 3 \\times 32 = 96$."),
      checks=("q = 2", "u_0 = 3")),
    E(61404, N4, 3,
      "On place $1\\,000$ €. Placement A : intérêts simples de $5\\,\\%$ du capital initial par an. Placement B : intérêts composés de $4\\,\\%$ par an. "
      "Exprimer les capitaux $a_n$ et $b_n$ après $n$ années, puis déterminer à partir de quelle année B devient plus avantageux.",
      "$a_n = 1\\,000 + 50n$ (arithmétique), $b_n = 1\\,000 \\times 1{,}04^n$ (géométrique) ; B devient plus avantageux à partir de la $12$e année.",
      "Compare les deux suites avec un tableau de valeurs (calculatrice ou programme).",
      S("Intérêts simples : on ajoute $50$ € chaque année. Intérêts composés : on multiplie par $1{,}04$.",
        "$a_{11} = 1\\,550$ et $b_{11} \\approx 1\\,539{,}45$ : A est encore devant.",
        "$a_{12} = 1\\,600$ et $b_{12} \\approx 1\\,601{,}03$ : B passe devant et y reste, car une croissance géométrique finit toujours par dépasser une croissance arithmétique."),
      checks=("$12$",), verify=lambda: None if 1000 * 1.04 ** 12 > 1600 and 1000 * 1.04 ** 11 < 1550 else "faux"),
    E(61405, N4, 2,
      "La masse d'un échantillon radioactif est divisée par $2$ tous les $30$ ans. Masse initiale : $80$ g. Exprimer la masse $m_n$ après $n$ périodes "
      "de $30$ ans, puis la masse après $150$ ans.",
      "$m_n = 80 \\times \\left(\\dfrac{1}{2}\\right)^n$ ; après $150$ ans ($n = 5$), il reste $2{,}5$ g.",
      "$150$ ans correspondent à $5$ périodes.",
      S("$m_{n+1} = \\dfrac{1}{2} m_n$ : suite géométrique de raison $\\dfrac{1}{2}$.", "$m_n = 80 \\times \\left(\\dfrac{1}{2}\\right)^n$.", "$m_5 = \\dfrac{80}{32} = 2{,}5$ g."),
      checks=("2{,}5",)),
    E(61406, N4, 4,
      "Soit $u_0 = 10$ et $u_{n+1} = 0{,}5u_n + 3$. On pose $v_n = u_n - 6$. Montrer que $(v_n)$ est géométrique, puis exprimer $u_n$ en fonction de $n$.",
      "$v_{n+1} = 0{,}5v_n$ avec $v_0 = 4$ ; $v_n = 4 \\times 0{,}5^n$ et $u_n = 6 + 4 \\times 0{,}5^n$.",
      "Exprime $v_{n+1}$ en remplaçant $u_{n+1}$ par $0{,}5u_n + 3$, puis $u_n$ par $v_n + 6$.",
      S("$v_{n+1} = u_{n+1} - 6 = 0{,}5u_n - 3 = 0{,}5(v_n + 6) - 3 = 0{,}5v_n$.",
        "$(v_n)$ est géométrique de raison $0{,}5$ et de premier terme $v_0 = 4$ : $v_n = 4 \\times 0{,}5^n$.",
        "$u_n = v_n + 6 = 6 + 4 \\times 0{,}5^n$ (contrôle : $u_1 = 8$)."),
      checks=("6 + 4 \\times 0{,}5^n",)),
    E(61407, N4, 1,
      "Une suite est définie par $u_n = 7 \\times 2^n$. Montrer qu'elle est géométrique et donner sa raison et son premier terme.",
      "$\\dfrac{u_{n+1}}{u_n} = 2$ : géométrique de raison $2$ et de premier terme $u_0 = 7$.",
      "Calcule $u_{n+1}$, puis le quotient $\\dfrac{u_{n+1}}{u_n}$ (les termes ne sont pas nuls).",
      S("$u_{n+1} = 7 \\times 2^{n+1} = 2 \\times 7 \\times 2^n = 2u_n$.", "Raison $2$, premier terme $u_0 = 7$."),
      checks=()),

    # N5 — sommes
    E(61501, N5, 1,
      "Calculer la somme des entiers pairs de $2$ à $100$.",
      "$2\\,550$.",
      "$2 + 4 + \\cdots + 100 = 2(1 + 2 + \\cdots + 50)$.",
      S("$2 + 4 + \\cdots + 100 = 2 \\times (1 + 2 + \\cdots + 50)$.", "$1 + 2 + \\cdots + 50 = \\dfrac{50 \\times 51}{2} = 1\\,275$.", "La somme vaut $2\\,550$."),
      checks=("2\\,550",)),
    E(61502, N5, 2,
      "Calculer $S = 3 + 6 + 12 + \\cdots + 384$, somme de termes consécutifs d'une suite géométrique.",
      "$S = 765$.",
      "Trouve d'abord la raison et le nombre de termes.",
      S("Raison $2$ : $3 \\times 2^7 = 384$, donc les termes vont de $3 \\times 2^0$ à $3 \\times 2^7$ : $8$ termes.",
        "$S = 3(1 + 2 + \\cdots + 2^7) = 3 \\times \\dfrac{2^8 - 1}{2 - 1} = 3 \\times 255$.", "$S = 765$."),
      checks=("S = 765",)),
    E(61503, N5, 2,
      "Soit $(u_n)$ arithmétique avec $u_0 = 4$ et $r = 3$. Calculer $S = u_5 + u_6 + \\cdots + u_{20}$.",
      "$S = 664$.",
      "Compte les termes : de l'indice $5$ à l'indice $20$ inclus.",
      S("Nombre de termes : $20 - 5 + 1 = 16$.", "$u_5 = 19$ et $u_{20} = 64$.", "$S = 16 \\times \\dfrac{19 + 64}{2} = 16 \\times 41{,}5 = 664$."),
      checks=("S = 664",), verify=lambda: None if sum(4 + 3 * k for k in range(5, 21)) == 664 else "faux"),
    E(61504, N5, 3,
      "Démontrer que la somme des $n$ premiers entiers impairs vaut $n^2$ : $1 + 3 + 5 + \\cdots + (2n - 1) = n^2$.",
      "C'est la somme des $n$ premiers termes de la suite arithmétique $u_k = 2k - 1$ ($k$ de $1$ à $n$) : $n \\times \\dfrac{1 + (2n - 1)}{2} = n^2$.",
      "Utilise la formule « nombre de termes × moyenne du premier et du dernier ».",
      S("Les impairs forment une suite arithmétique de raison $2$, de premier terme $1$.", "Il y a $n$ termes, le dernier est $2n - 1$.",
        "Somme $= n \\times \\dfrac{1 + 2n - 1}{2} = n \\times n = n^2$."),
      checks=()),
    E(61505, N5, 3,
      "Léa épargne $50$ € le premier mois, puis $5$ € de plus chaque mois que le mois précédent. Combien aura-t-elle épargné au bout de $2$ ans ?",
      "$2\\,580$ €.",
      "Les versements forment une suite arithmétique ; il y en a $24$.",
      S("Versements : $v_1 = 50$, raison $5$ : $v_{24} = 50 + 23 \\times 5 = 165$.", "Total $= 24 \\times \\dfrac{50 + 165}{2} = 24 \\times 107{,}5$.", "Total : $2\\,580$ €."),
      checks=("2\\,580",)),
    E(61506, N5, 4,
      "Un ballon tombe de $10$ m ; après chaque rebond il remonte aux $\\dfrac{3}{5}$ de la hauteur précédente. Quelle distance totale a-t-il parcourue "
      "lorsqu'il touche le sol pour la $6$e fois ? (valeur arrondie au centimètre)",
      "Environ $37{,}67$ m.",
      "Descente initiale, puis pour chaque rebond une montée et une descente de même hauteur.",
      S("Hauteurs des rebonds : $6$, $3{,}6$, $2{,}16$, $1{,}296$, $0{,}7776$ m (géométrique de raison $0{,}6$).",
        "Somme des $5$ rebonds : $6 \\times \\dfrac{1 - 0{,}6^5}{1 - 0{,}6} = 6 \\times \\dfrac{0{,}92224}{0{,}4} = 13{,}8336$.",
        "Distance : $10 + 2 \\times 13{,}8336 = 37{,}6672 \\approx 37{,}67$ m."),
      checks=("37{,}67",), verify=lambda: None if abs(10 + 2 * sum(10 * 0.6 ** k for k in range(1, 6)) - 37.6672) < 1e-9 else "faux"),
    E(61507, N5, 2,
      "Écrire un programme Python qui calcule $1 + 2 + \\cdots + 1\\,000$ avec une boucle, puis comparer avec la formule.",
      "" + code("s = 0") + " puis " + code("for k in range(1, 1001): s = s + k") + " ; on obtient $500\\,500 = \\dfrac{1\\,000 \\times 1\\,001}{2}$.",
      "Attention : " + code("range(1, 1001)") + " va de $1$ à $1\\,000$.",
      S("On initialise " + code("s = 0") + ", puis on ajoute chaque entier $k$ de $1$ à $1\\,000$.", "La boucle " + code("for k in range(1, 1001)") + " parcourt exactement ces entiers.",
        "Formule : $\\dfrac{1\\,000 \\times 1\\,001}{2} = 500\\,500$."),
      checks=("500\\,500",)),

    # N6 — limite (intuition), seuils
    E(61601, N6, 2,
      "Déterminer le plus petit entier $n$ tel que $0{,}9^n < 0{,}01$, puis écrire un algorithme de seuil qui le trouve.",
      "$n = 44$ ; algorithme : " + code("n = 0") + ", " + code("u = 1") + ", " + code("while u >= 0.01: n = n + 1 ; u = 0.9*u") + ", puis afficher " + code("n") + ".",
      "Calcule des puissances de $0{,}9$ à la calculatrice autour de $n = 40$.",
      S("$0{,}9^{43} \\approx 0{,}0108$ et $0{,}9^{44} \\approx 0{,}0097$.", "Le plus petit entier qui convient est $44$.",
        "La boucle " + code("while") + " s'arrête dès que la condition " + code("u >= 0.01") + " devient fausse."),
      checks=("44",)),
    E(61602, N6, 2,
      "Soit $u_0 = 0$ et $u_{n+1} = 0{,}5u_n + 2$. Calculer $u_1$ à $u_6$ et conjecturer la limite de la suite.",
      "$2$ ; $3$ ; $3{,}5$ ; $3{,}75$ ; $3{,}875$ ; $3{,}9375$ : on conjecture que $(u_n)$ converge vers $4$.",
      "Regarde l'écart entre les termes et $4$.",
      S("$u_1 = 2$, $u_2 = 3$, $u_3 = 3{,}5$, $u_4 = 3{,}75$, $u_5 = 3{,}875$, $u_6 = 3{,}9375$.", "L'écart à $4$ est divisé par $2$ à chaque étape.",
        "Conjecture : la suite converge vers $4$ (point fixe : $\\ell = 0{,}5\\ell + 2 \\iff \\ell = 4$)."),
      checks=()),
    E(61603, N6, 3,
      "Vrai ou faux : « une suite croissante tend vers $+\\infty$ ». Justifier.",
      "Faux : $u_n = 1 - \\dfrac{1}{n + 1}$ est croissante et se rapproche de $1$.",
      "Cherche une suite croissante dont les termes restent bloqués sous un nombre.",
      S("$u_{n+1} - u_n = \\dfrac{1}{n + 1} - \\dfrac{1}{n + 2} > 0$ : la suite est croissante.", "Pourtant $u_n < 1$ pour tout $n$ et $u_n$ se rapproche de $1$.",
        "Un contre-exemple suffit : l'affirmation est fausse."),
      checks=()),
    E(61604, N6, 1,
      "Soit $(u_n)$ arithmétique de raison $r = -0{,}5$ et de premier terme $u_0 = 100$. Conjecturer le comportement de $(u_n)$ quand $n$ devient grand.",
      "$(u_n)$ tend vers $-\\infty$.",
      "On retire $0{,}5$ à chaque étape, indéfiniment.",
      S("$u_n = 100 - 0{,}5n$.", "Par exemple $u_{1\\,000} = -400$ et $u_{10\\,000} = -4\\,900$.", "Les termes deviennent négatifs et aussi grands en valeur absolue que l'on veut."),
      checks=()),
    E(61605, N6, 3,
      "Pour approcher le nombre $e$, on considère $u_n = \\left(1 + \\dfrac{1}{n}\\right)^n$. Calculer $u_1$, $u_{10}$, $u_{100}$, $u_{1\\,000}$ "
      "(valeurs approchées à $10^{-3}$) et conjecturer la limite.",
      "$2$ ; $2{,}594$ ; $2{,}705$ ; $2{,}717$ : la suite semble converger vers un nombre proche de $2{,}718$ (le nombre $e$).",
      "Utilise la calculatrice ou un tableur.",
      S("$u_1 = 2$, $u_{10} \\approx 2{,}594$, $u_{100} \\approx 2{,}705$, $u_{1\\,000} \\approx 2{,}717$.", "Les termes augmentent de moins en moins.",
        "On conjecture une limite voisine de $2{,}718$ : c'est le nombre $e$, étudié avec la fonction exponentielle."),
      checks=()),
]

EXERCISES = HIST + MANUELS + NOUVEAUX

QUIZ = {
    "generalites-sur-les-suites": (61101, 61107, 0),
    "sens-de-variation-d-une-suite": (236, 239, 61201),
    "suite-arithmetique": (59, 61301, 61302),
    "suite-geometrique": (118, 61407, 61401),
    "calcul-de-sommes": (184, 61501, 178),
    "notion-de-limite-d-une-suite": (297, 300, 61604),
}

# ── Adaptation au manuel « Première ES/L » (2026-10-26) ─────────────────────
# Voir PREMIERE_SPECIFIQUE_SUIVI.md. Hors manuel, retirés de la banque servie
# (conservés ici) : calcul de sommes, notion de limite, et la somme
# u_0 + … + u_99 de l'exercice 61306.
_IDS_HORS_PERIMETRE = {61306}
EXERCICES_HORS_PERIMETRE = [e for e in EXERCISES if e.notion in (N5, N6) or e.id in _IDS_HORS_PERIMETRE]
_hors = {e.id for e in EXERCICES_HORS_PERIMETRE}
EXERCISES = [e for e in EXERCISES if e.id not in _hors]
NOTIONS = (N1, N2, N3, N4)
NOTION_IDS = NOTION_IDS[:4]
QUIZ = {k: v for k, v in QUIZ.items() if k in NOTION_IDS}
