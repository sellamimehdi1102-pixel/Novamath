"""Chapitre 7 — Produit scalaire : banque curée.

Exercices historiques (banque_ch07_historiques.py, identifiants conservés).
Toutes les réponses historiques ont été recalculées (justes) ; les défauts
étaient d'écriture : « \\left(\\dfrac{45}{2}\\right)\\sqrt{3} », rayon
« \\sqrt{\\dfrac{81}{4}} », équations « 5x +1y +10 = 0 », « -1\\times-6 + 4\\times-5 »,
« 3(x-(2))+-1(y-q) », un niveau 5. Les huit gabarits paramétrés (produit en
coordonnées, valeur de k, normes et angle, identités remarquables, droite
AM·u = 0, cercle MA·MB = 0) sont reconstruits à partir de leurs paramètres,
lus dans l'énoncé historique : énoncé inchangé, réponse et correction
recalculées par SymPy. Les autres gardent leur texte, nettoyé (_clean).

Nouvelle notion : « Formule d'Al-Kashi et calculs dans le triangle »
(démonstration exigée par le programme 2026).
Nouveaux exercices : bloc 67 000.
"""
import dataclasses
import math
import re

import sympy as sp

from premiere_specifique.reserve.banque_ch07_historiques import HISTORIQUES
from premiere_specifique.banque_commun import E, S

CHAPTER_NUMBER = 7
N1 = "Produit scalaire, colinéarité et orthogonalité de vecteurs"
N2 = "Autres définitions et propriétés"
N3 = "Formule d'Al-Kashi et calculs dans le triangle"
N4 = "Étude d'un ensemble de points"
NOTIONS = (N1, N2, N3, N4)
NOTION_IDS = (
    "produit-scalaire,-colinearite-et-orthogonalite-de-vecteurs",
    "autres-definitions-et-proprietes",
    "formule-d-al-kashi-et-calculs-dans-le-triangle",
    "etude-d-un-ensemble-de-points",
)
LEGACY_IDS = tuple(h[0] for h in HISTORIQUES)

V = "\\vec{u}\\cdot\\vec{v}"
NU, NV = "\\|\\vec{u}\\|", "\\|\\vec{v}\\|"


# ── Écriture ─────────────────────────────────────────────────────────────────

def T(v):
    if isinstance(v, str):
        return v
    return sp.latex(sp.nsimplify(v)).replace("\\frac", "\\dfrac")


def P(v):
    t = T(v)
    return f"\\left({t}\\right)" if t.startswith("-") else t


def prod(a, b):
    return f"{P(a)} \\times {P(b)}"


def plus(*terms):
    out = T(terms[0])
    for t in terms[1:]:
        s = T(t)
        out += f" - {s[1:]}" if s.startswith("-") else f" + {s}"
    return out


def lin(a, b, c):
    """Équation « ax + by + c = 0 » sans « 1x », « + -», « + 0 »."""
    out = ""
    for coef, mono in ((a, "x"), (b, "y"), (c, "")):
        if coef == 0:
            continue
        mag = abs(coef)
        body = (str(mag) if (mono == "" or mag != 1) else "") + mono
        if not out:
            out = ("-" if coef < 0 else "") + body
        else:
            out += f" {'-' if coef < 0 else '+'} {body}"
    return f"{out} = 0"


_EQ = re.compile(r"(-?\d*)x\s*([+-])\s*(\d*)y\s*([+-])\s*(\d+)\s*=\s*0")


def _eq_fmt(m):
    a = int(m.group(1)) if m.group(1) not in ("", "-") else (-1 if m.group(1) == "-" else 1)
    b = (int(m.group(3)) if m.group(3) else 1) * (1 if m.group(2) == "+" else -1)
    c = int(m.group(5)) * (1 if m.group(4) == "+" else -1)
    return lin(a, b, c)


def _clean(t):
    t = re.sub(r"\\times\s*-\s*(\d+)", r"\\times (-\1)", t)
    t = re.sub(r"(?<=[\s$=])-(\d+)\\times", r"(-\1) \\times", t)
    t = re.sub(r"\+\s*-\s*(\d)", r"- \1", t)
    t = re.sub(r"(\d) - -\s*(\d)", r"\1 + \2", t)
    t = _EQ.sub(_eq_fmt, t)
    return t


# ── Lecture des paramètres historiques ───────────────────────────────────────

_VEC = re.compile(r"\\vec\{(\w+)\}\((-?\d+|k|p) ; (-?\d+|k|p)\)")
_PT = re.compile(r"\$([A-Z])\((-?\d+) ; (-?\d+)\)\$")
_NORMS = re.compile(r"\\\|\\vec\{u\}\\\| = (\d+)\$, \$\\\|\\vec\{v\}\\\| = (\d+)\$ et \$\\left\(\\vec\{u\} ; \\vec\{v\}\\right\) = ([^$]+)\$")
_SQ = re.compile(r"\\\|\\vec\{(u|v)\}\\\|\^2 = (\d+)")
_DOT = re.compile(r"\\vec\{u\}\\cdot\\vec\{v\} = (-?\d+)")


def _angle(tex):
    t = tex.replace("\\dfrac", "").replace("\\pi", "pi")
    m = re.fullmatch(r"\{(\d*)pi\}\{(\d+)\}", t)
    if m:
        return sp.Rational(int(m.group(1) or 1), int(m.group(2))) * sp.pi
    return sp.Integer(0) if t == "0" else sp.sympify(t)


def _vecs(enonce):
    return {n: (x, y) for n, x, y in _VEC.findall(enonce)}


# ── Gabarits reconstruits ────────────────────────────────────────────────────

def _t1(h):
    """Produit scalaire en coordonnées."""
    (a, b), (c, d) = [tuple(map(int, v)) for v in _vecs(h[3]).values()]
    val = a * c + b * d
    return dict(answer=f"${V} = {val}$", hint="En repère orthonormé, $\\vec{u}\\cdot\\vec{v} = xx' + yy'$.",
                steps=(f"En repère orthonormé : ${V} = xx' + yy'$.", f"${V} = {prod(a, c)} + {prod(b, d)} = {plus(a * c, b * d)} = {val}$."))


def _k(b):
    return "k" if b == 1 else ("-k" if b == -1 else f"{b}k")


def _t2(h):
    """Valeur de k pour l'orthogonalité ou la colinéarité."""
    vs = _vecs(h[3])
    a, b = map(int, vs["u"])
    c = int(vs["v"][0])
    k = sp.Symbol("k")
    if "orthogonaux" in h[3]:
        sol = sp.solve(a * c + b * k, k)[0]
        steps = ("$\\vec{u}$ et $\\vec{v}$ sont orthogonaux si et seulement si $\\vec{u}\\cdot\\vec{v} = 0$.",
                 f"${V} = {prod(a, c)} + {P(b)}k = {plus(a * c, f'{b}k')}$.", f"${plus(a * c, f'{b}k')} = 0 \\iff k = {T(sol)}$.")
        hint = "Orthogonaux : produit scalaire nul."
    else:
        sol = sp.solve(a * k - b * c, k)[0]
        steps = ("$\\vec{u}$ et $\\vec{v}$ sont colinéaires si et seulement si $xy' - x'y = 0$.",
                 f"${P(a)}k - {prod(c, b)} = 0$, soit ${_k(a)} = {b * c}$.", f"$k = {T(sol)}$.")
        hint = "Colinéaires : $xy' - x'y = 0$."
    return dict(answer=f"$k = {T(sol)}$", hint=hint, steps=steps)


def _t3(h):
    """Produit scalaire à partir des normes et de l'angle."""
    n1, n2, ang = _NORMS.search(h[3]).groups()
    theta = _angle(ang)
    val = sp.nsimplify(int(n1) * int(n2) * sp.cos(theta))
    return dict(answer=f"${V} = {T(val)}$", hint="$\\vec{u}\\cdot\\vec{v} = \\|\\vec{u}\\|\\,\\|\\vec{v}\\|\\cos(\\vec{u} ; \\vec{v})$.",
                steps=(f"${V} = {NU}\\times{NV}\\times\\cos\\left(\\vec{{u}} ; \\vec{{v}}\\right)$.",
                       f"${V} = {n1} \\times {n2} \\times \\cos\\left({ang}\\right) = {int(n1) * int(n2)} \\times {P(sp.cos(theta))}$.",
                       f"${V} = {T(val)}$."))


def _t4(h):
    """(u + v)·(u + v) = ‖u‖² + 2u·v + ‖v‖²."""
    sq = dict(_SQ.findall(h[3]))
    d = int(_DOT.search(h[3]).group(1))
    u2, v2 = int(sq["u"]), int(sq["v"])
    val = u2 + 2 * d + v2
    return dict(answer=f"$(\\vec{{u}}+\\vec{{v}})\\cdot(\\vec{{u}}+\\vec{{v}}) = {val}$",
                hint="Développe comme une identité remarquable : $\\|\\vec{u}\\|^2 + 2\\vec{u}\\cdot\\vec{v} + \\|\\vec{v}\\|^2$.",
                steps=("Par bilinéarité : $(\\vec{u}+\\vec{v})\\cdot(\\vec{u}+\\vec{v}) = \\|\\vec{u}\\|^2 + 2\\vec{u}\\cdot\\vec{v} + \\|\\vec{v}\\|^2$.",
                       f"$= {plus(u2, 2 * d, v2)} = {val}$."))


def _t5(h):
    """(u + v)·(u − v) = ‖u‖² − ‖v‖²."""
    sq = dict(_SQ.findall(h[3]))
    u2, v2 = int(sq["u"]), int(sq["v"])
    return dict(answer=f"$(\\vec{{u}}+\\vec{{v}})\\cdot(\\vec{{u}}-\\vec{{v}}) = {u2 - v2}$",
                hint="Les termes $\\vec{u}\\cdot\\vec{v}$ et $\\vec{v}\\cdot\\vec{u}$ se compensent.",
                steps=("Par bilinéarité : $(\\vec{u}+\\vec{v})\\cdot(\\vec{u}-\\vec{v}) = \\|\\vec{u}\\|^2 - \\vec{u}\\cdot\\vec{v} + \\vec{v}\\cdot\\vec{u} - \\|\\vec{v}\\|^2 = \\|\\vec{u}\\|^2 - \\|\\vec{v}\\|^2$.",
                       f"$= {u2} - {v2} = {u2 - v2}$."))


def _t6(h):
    """‖u + v‖ à partir des normes et de l'angle."""
    n1, n2, ang = _NORMS.search(h[3]).groups()
    n1, n2, theta = int(n1), int(n2), _angle(ang)
    dot = sp.nsimplify(n1 * n2 * sp.cos(theta))
    carre = sp.nsimplify(n1 ** 2 + 2 * dot + n2 ** 2)
    return dict(answer=f"$\\|\\vec{{u}}+\\vec{{v}}\\| = {T(sp.sqrt(carre))}$", hint="Calcule d'abord $\\|\\vec{u}+\\vec{v}\\|^2$.",
                steps=(f"${V} = {n1} \\times {n2} \\times {P(sp.cos(theta))} = {T(dot)}$.",
                       f"$\\|\\vec{{u}}+\\vec{{v}}\\|^2 = {NU}^2 + 2{V} + {NV}^2 = {plus(n1 ** 2, 2 * dot, n2 ** 2)} = {T(carre)}$.",
                       f"$\\|\\vec{{u}}+\\vec{{v}}\\| = \\sqrt{{{T(carre)}}} {'' if sp.sqrt(carre).is_Pow else ' = ' + T(sp.sqrt(carre))}$."))


def _t7(h):
    """Ensemble des points M tels que AM·u = 0 : une droite."""
    xa, ya = map(int, _PT.search(h[3]).groups()[1:])
    a, b = map(int, _vecs(h[3])["u"])
    eq = lin(a, b, -(a * xa + b * ya))
    return dict(answer=f"La droite passant par $A$ de vecteur normal $\\vec{{u}}$, d'équation ${eq}$.",
                hint="$\\vec{AM}\\cdot\\vec{u} = 0$ : $\\vec{AM}$ est orthogonal à $\\vec{u}$.",
                steps=("$\\vec{AM}\\cdot\\vec{u} = 0$ signifie que $\\vec{AM}$ est orthogonal à $\\vec{u}$ (ou nul) : c'est la droite passant par $A$ de vecteur normal $\\vec{u}$.",
                       f"Avec $M(x ; y)$ : $\\vec{{AM}}(x {'-' if xa >= 0 else '+'} {abs(xa)} ; y {'-' if ya >= 0 else '+'} {abs(ya)})$.",
                       f"${T(a)}(x {'-' if xa >= 0 else '+'} {abs(xa)}) {'-' if b < 0 else '+'} {abs(b) if abs(b) != 1 else ''}(y {'-' if ya >= 0 else '+'} {abs(ya)}) = 0$, soit ${eq}$."))


def _t8(h):
    """Ensemble des points M tels que MA·MB = 0 : cercle de diamètre [AB]."""
    pts = {n: (int(x), int(y)) for n, x, y in _PT.findall(h[3])}
    (xa, ya), (xb, yb) = pts["A"], pts["B"]
    cx, cy = sp.Rational(xa + xb, 2), sp.Rational(ya + yb, 2)
    r = sp.sqrt(sp.Rational((xb - xa) ** 2 + (yb - ya) ** 2, 4))
    return dict(answer=f"Le cercle de diamètre $[AB]$, de centre $\\Omega\\left({T(cx)} ; {T(cy)}\\right)$ et de rayon ${T(r)}$.",
                hint="$\\vec{MA}\\cdot\\vec{MB} = 0$ : l'angle $\\widehat{AMB}$ est droit (ou $M = A$, $M = B$).",
                steps=("$\\vec{MA}\\cdot\\vec{MB} = 0$ caractérise le cercle de diamètre $[AB]$ (cours).",
                       f"Centre : milieu de $[AB]$, $\\Omega\\left({T(cx)} ; {T(cy)}\\right)$.",
                       f"Rayon : $\\dfrac{{AB}}{{2}} = \\dfrac{{\\sqrt{{{(xb - xa) ** 2 + (yb - ya) ** 2}}}}}{{2}} = {T(r)}$."))


GABARITS = {
    **dict.fromkeys((1420, 2116, 2117, 2118), _t1),
    **dict.fromkeys((1416, 1418, 2119, 2120, 2121, 2122), _t2),
    **dict.fromkeys((1475, 1476, 2092, 2093, 2094, 2095), _t3),
    **dict.fromkeys((1479, 2096, 2097, 2098), _t4),
    **dict.fromkeys((1480, 2099, 2100), _t5),
    **dict.fromkeys((2101, 2102, 2103), _t6),
    **dict.fromkeys((1534, 2181, 2182, 2183), _t7),
    **dict.fromkeys((1535, 2184, 2185, 2186), _t8),
}

OVERRIDES = {
    2189: dict(steps=("$\\vec{AM}(x - 2 ; y - q)$ et $\\vec{AM}\\cdot\\vec{u} = 3(x - 2) - (y - q) = 3x - y - 6 + q$.",
                      "L'équation est $3x - y + (q - 6) = 0$ ; par identification avec $3x - y - 2 = 0$ : $q - 6 = -2$.",
                      "Donc $q = 4$.")),
    2190: dict(steps=("$\\vec{AM}(x + 3 ; y - q)$ et $\\vec{AM}\\cdot\\vec{u} = 4(x + 3) + 5(y - q) = 4x + 5y + 12 - 5q$.",
                      "Par identification avec $4x + 5y + 22 = 0$ : $12 - 5q = 22$.", "Donc $q = -2$.")),
    2115: dict(answer="$W = 8000\\sqrt{2}$ J $\\approx 11\\,314$ J"),
    2187: dict(steps=("$\\vec{AM}\\cdot\\vec{u} = 0$ : droite passant par $A$ de vecteur normal $\\vec{u}$.",
                      "$3(x - 1) - 2(y - 2) = 0$, soit $3x - 2y + 1 = 0$.",
                      "Pour $N(4 ; 1)$ : $3 \\times 4 - 2 \\times 1 + 1 = 11 \\neq 0$, donc $N \\notin \\mathcal{E}$.")),
    2188: dict(steps=("$\\vec{AM}\\cdot\\vec{u} = 0$ : droite passant par $A$ de vecteur normal $\\vec{u}$.",
                      "$5(x + 2) + (y - 0) = 0$, soit $5x + y + 10 = 0$.",
                      "Pour $N(-1 ; -5)$ : $5 \\times (-1) + (-5) + 10 = 0$, donc $N \\in \\mathcal{E}$.")),
}

_STEP_PREFIX = re.compile(r"^\s*Étape\s*\d+\s*[:—-]\s*")


def _hist(h):
    i, notion, level, enonce, answer, hint, steps = h
    steps = tuple(_STEP_PREFIX.sub("", s) for s in steps)
    o = dict(answer=_clean(answer), hint=_clean(hint), steps=tuple(_clean(s) for s in steps))
    if i in GABARITS:
        o.update(GABARITS[i](h))
    o.update(OVERRIDES.get(i, {}))
    return E(i, notion, min(level, 4), enonce, o["answer"], o["hint"], S(*o["steps"]))


HIST = [_hist(h) for h in HISTORIQUES]


# ── Nouveaux exercices ───────────────────────────────────────────────────────

def _chk(cond_fn):
    return lambda: None if cond_fn() else "valeur fausse"


def _al_kashi(b, c, angle):
    return sp.sqrt(sp.nsimplify(b ** 2 + c ** 2 - 2 * b * c * sp.cos(angle)))


NOUVEAUX = [
    # N1 — définition, projection, orthogonalité
    E(67101, N1, 1,
      "Dans un triangle $ABC$, le projeté orthogonal de $C$ sur $(AB)$ est le point $H$ de $[AB]$ tel que $AH = 2$. On sait que $AB = 6$. Calculer $\\vec{AB}\\cdot\\vec{AC}$.",
      "$\\vec{AB}\\cdot\\vec{AC} = 12$.",
      "$\\vec{AB}\\cdot\\vec{AC} = \\vec{AB}\\cdot\\vec{AH}$.",
      S("Avec le projeté orthogonal : $\\vec{AB}\\cdot\\vec{AC} = \\vec{AB}\\cdot\\vec{AH}$.", "$\\vec{AB}$ et $\\vec{AH}$ sont de même sens : $\\vec{AB}\\cdot\\vec{AH} = AB \\times AH = 6 \\times 2 = 12$."),
      checks=("12",)),
    E(67102, N1, 2,
      "$ABCD$ est un carré de côté $4$. Calculer $\\vec{AB}\\cdot\\vec{AC}$ et $\\vec{AB}\\cdot\\vec{CD}$.",
      "$\\vec{AB}\\cdot\\vec{AC} = 16$ et $\\vec{AB}\\cdot\\vec{CD} = -16$.",
      "Projette $C$ sur $(AB)$ ; $\\vec{CD} = -\\vec{AB}$.",
      S("Le projeté de $C$ sur $(AB)$ est $B$ : $\\vec{AB}\\cdot\\vec{AC} = \\vec{AB}\\cdot\\vec{AB} = AB^2 = 16$.",
        "$\\vec{CD} = -\\vec{AB}$ : $\\vec{AB}\\cdot\\vec{CD} = -AB^2 = -16$."),
      checks=("-16",)),
    E(67103, N1, 2,
      "$ABC$ est un triangle équilatéral de côté $a$. Calculer $\\vec{AB}\\cdot\\vec{AC}$ en fonction de $a$.",
      "$\\vec{AB}\\cdot\\vec{AC} = \\dfrac{a^2}{2}$.",
      "L'angle $\\widehat{BAC}$ mesure $\\dfrac{\\pi}{3}$.",
      S("$\\vec{AB}\\cdot\\vec{AC} = AB \\times AC \\times \\cos\\widehat{BAC} = a \\times a \\times \\cos\\dfrac{\\pi}{3}$.", "$= \\dfrac{a^2}{2}$."),
      checks=("\\dfrac{a^2}{2}",)),
    E(67104, N1, 3,
      "Dans un triangle $ABC$ tel que $AB = 5$, le projeté orthogonal $H$ de $C$ sur la droite $(AB)$ vérifie $AH = 3$ avec $H$ n'appartenant pas à $[AB]$ et $A \\in [HB]$. Calculer $\\vec{AB}\\cdot\\vec{AC}$.",
      "$\\vec{AB}\\cdot\\vec{AC} = -15$.",
      "$\\vec{AB}$ et $\\vec{AH}$ sont de sens contraires.",
      S("$\\vec{AB}\\cdot\\vec{AC} = \\vec{AB}\\cdot\\vec{AH}$.", "$A$ est entre $H$ et $B$ : $\\vec{AH}$ et $\\vec{AB}$ sont de sens contraires.",
        "$\\vec{AB}\\cdot\\vec{AH} = -AB \\times AH = -15$ : l'angle $\\widehat{BAC}$ est obtus."),
      checks=("-15",)),
    E(67105, N1, 3,
      "$ABCD$ est un losange. En posant $\\vec{u} = \\vec{AB}$ et $\\vec{v} = \\vec{AD}$, démontrer que ses diagonales sont perpendiculaires.",
      "$\\vec{AC}\\cdot\\vec{DB} = (\\vec{u} + \\vec{v})\\cdot(\\vec{u} - \\vec{v}) = AB^2 - AD^2 = 0$ : les diagonales sont perpendiculaires.",
      "Exprime $\\vec{AC}$ et $\\vec{DB}$ avec $\\vec{u}$ et $\\vec{v}$.",
      S("$\\vec{AC} = \\vec{u} + \\vec{v}$ (parallélogramme) et $\\vec{DB} = \\vec{u} - \\vec{v}$.",
        "$(\\vec{u} + \\vec{v})\\cdot(\\vec{u} - \\vec{v}) = \\|\\vec{u}\\|^2 - \\|\\vec{v}\\|^2 = AB^2 - AD^2$.",
        "Dans un losange, $AB = AD$ : le produit scalaire est nul, les diagonales sont perpendiculaires."),
      checks=("= 0",)),

    # N2 — bilinéarité, coordonnées, normes
    E(67201, N2, 1,
      "Dans un repère orthonormé, $\\vec{u}(3 ; -4)$. Calculer $\\|\\vec{u}\\|$ en utilisant $\\|\\vec{u}\\|^2 = \\vec{u}\\cdot\\vec{u}$.",
      "$\\|\\vec{u}\\| = 5$.",
      "$\\vec{u}\\cdot\\vec{u} = x^2 + y^2$.",
      S("$\\vec{u}\\cdot\\vec{u} = 3^2 + (-4)^2 = 9 + 16 = 25$.", "$\\|\\vec{u}\\| = \\sqrt{25} = 5$."),
      checks=("5",)),
    E(67202, N2, 2,
      "Dans un repère orthonormé, $\\vec{u}(1 ; 2)$ et $\\vec{v}(3 ; 1)$. Calculer $\\vec{u}\\cdot\\vec{v}$, les normes, puis une mesure de l'angle $(\\vec{u} ; \\vec{v})$.",
      "$\\vec{u}\\cdot\\vec{v} = 5$, $\\|\\vec{u}\\| = \\sqrt{5}$, $\\|\\vec{v}\\| = \\sqrt{10}$, $\\cos(\\vec{u} ; \\vec{v}) = \\dfrac{\\sqrt{2}}{2}$ : l'angle mesure $\\dfrac{\\pi}{4}$.",
      "$\\cos(\\vec{u} ; \\vec{v}) = \\dfrac{\\vec{u}\\cdot\\vec{v}}{\\|\\vec{u}\\|\\,\\|\\vec{v}\\|}$.",
      S("$\\vec{u}\\cdot\\vec{v} = 3 + 2 = 5$ ; $\\|\\vec{u}\\| = \\sqrt{5}$, $\\|\\vec{v}\\| = \\sqrt{10}$.",
        "$\\cos(\\vec{u} ; \\vec{v}) = \\dfrac{5}{\\sqrt{50}} = \\dfrac{5}{5\\sqrt{2}} = \\dfrac{\\sqrt{2}}{2}$.", "L'angle géométrique mesure $\\dfrac{\\pi}{4}$."),
      checks=("\\dfrac{\\pi}{4}",), verify=_chk(lambda: sp.simplify(sp.Rational(5) / sp.sqrt(50) - sp.sqrt(2) / 2) == 0)),
    E(67203, N2, 2,
      "On donne $\\|\\vec{u}\\| = 3$, $\\|\\vec{v}\\| = 2$ et $\\vec{u}\\cdot\\vec{v} = -1$. Calculer $(2\\vec{u} + \\vec{v})\\cdot(\\vec{u} - 3\\vec{v})$.",
      "$(2\\vec{u} + \\vec{v})\\cdot(\\vec{u} - 3\\vec{v}) = 11$.",
      "Développe par bilinéarité, puis remplace.",
      S("$(2\\vec{u} + \\vec{v})\\cdot(\\vec{u} - 3\\vec{v}) = 2\\|\\vec{u}\\|^2 - 6\\vec{u}\\cdot\\vec{v} + \\vec{v}\\cdot\\vec{u} - 3\\|\\vec{v}\\|^2$.",
        "$= 2\\|\\vec{u}\\|^2 - 5\\vec{u}\\cdot\\vec{v} - 3\\|\\vec{v}\\|^2 = 18 + 5 - 12 = 11$."),
      checks=("11",), verify=_chk(lambda: 2 * 9 - 5 * (-1) - 3 * 4 == 11)),
    E(67204, N2, 3,
      "Démontrer que pour tous vecteurs $\\vec{u}$ et $\\vec{v}$ : $\\vec{u}\\cdot\\vec{v} = \\dfrac{1}{2}\\left(\\|\\vec{u} + \\vec{v}\\|^2 - \\|\\vec{u}\\|^2 - \\|\\vec{v}\\|^2\\right)$. Appliquer avec $\\|\\vec{u}\\| = 4$, $\\|\\vec{v}\\| = 5$, $\\|\\vec{u} + \\vec{v}\\| = 7$.",
      "Identité obtenue en développant $\\|\\vec{u} + \\vec{v}\\|^2$ ; application : $\\vec{u}\\cdot\\vec{v} = \\dfrac{49 - 16 - 25}{2} = 4$.",
      "$\\|\\vec{u} + \\vec{v}\\|^2 = (\\vec{u} + \\vec{v})\\cdot(\\vec{u} + \\vec{v})$.",
      S("$\\|\\vec{u} + \\vec{v}\\|^2 = \\|\\vec{u}\\|^2 + 2\\vec{u}\\cdot\\vec{v} + \\|\\vec{v}\\|^2$ (bilinéarité et symétrie).",
        "On isole $\\vec{u}\\cdot\\vec{v}$ : formule demandée.", "$\\vec{u}\\cdot\\vec{v} = \\dfrac{49 - 16 - 25}{2} = 4$."),
      checks=("= 4",)),
    E(67205, N2, 3,
      "Dans une base orthonormée $(\\vec{i}, \\vec{j})$, montrer que l'abscisse d'un vecteur $\\vec{w}(x ; y)$ est $\\vec{w}\\cdot\\vec{i}$. Application : $\\vec{w} = 2\\vec{a} - \\vec{b}$ avec $\\vec{a}\\cdot\\vec{i} = 3$ et $\\vec{b}\\cdot\\vec{i} = -1$ ; donner l'abscisse de $\\vec{w}$.",
      "$\\vec{w}\\cdot\\vec{i} = x\\,\\vec{i}\\cdot\\vec{i} + y\\,\\vec{j}\\cdot\\vec{i} = x$ ; abscisse de $\\vec{w}$ : $2 \\times 3 - (-1) = 7$.",
      "$\\vec{i}\\cdot\\vec{i} = 1$ et $\\vec{j}\\cdot\\vec{i} = 0$.",
      S("$\\vec{w} = x\\vec{i} + y\\vec{j}$, donc $\\vec{w}\\cdot\\vec{i} = x\\|\\vec{i}\\|^2 + y\\,\\vec{j}\\cdot\\vec{i} = x \\times 1 + y \\times 0 = x$.",
        "$\\vec{w}\\cdot\\vec{i} = 2\\vec{a}\\cdot\\vec{i} - \\vec{b}\\cdot\\vec{i} = 6 + 1 = 7$."),
      checks=("7",)),

    # N3 — Al-Kashi
    E(67301, N3, 1,
      "Dans un triangle $ABC$, $AB = 5$, $AC = 8$ et $\\widehat{BAC} = \\dfrac{\\pi}{3}$. Calculer $BC$.",
      "$BC = 7$.",
      "Formule d'Al-Kashi : $BC^2 = AB^2 + AC^2 - 2\\,AB \\times AC \\cos\\widehat{A}$.",
      S("$BC^2 = 25 + 64 - 2 \\times 5 \\times 8 \\times \\dfrac{1}{2} = 89 - 40 = 49$.", "$BC = 7$."),
      checks=("BC = 7",), verify=_chk(lambda: _al_kashi(5, 8, sp.pi / 3) == 7)),
    E(67302, N3, 2,
      "Dans un triangle $ABC$, $AB = 3$, $AC = 5$ et $BC = 7$. Calculer $\\cos\\widehat{BAC}$ et en déduire $\\widehat{BAC}$.",
      "$\\cos\\widehat{BAC} = -\\dfrac{1}{2}$, donc $\\widehat{BAC} = \\dfrac{2\\pi}{3}$.",
      "Isole $\\cos\\widehat{A}$ dans la formule d'Al-Kashi.",
      S("$49 = 9 + 25 - 2 \\times 3 \\times 5 \\cos\\widehat{A}$, donc $30\\cos\\widehat{A} = -15$.", "$\\cos\\widehat{A} = -\\dfrac{1}{2}$ : $\\widehat{A} = \\dfrac{2\\pi}{3}$ ($120°$)."),
      checks=("\\dfrac{2\\pi}{3}",), verify=_chk(lambda: sp.Rational(9 + 25 - 49, 30) == sp.Rational(-1, 2))),
    E(67303, N3, 2,
      "Dans un triangle $ABC$, $AB = 4$, $AC = 6$ et $\\widehat{BAC} = \\dfrac{\\pi}{2}$. Que devient la formule d'Al-Kashi ? Calculer $BC$.",
      "Avec $\\cos\\dfrac{\\pi}{2} = 0$, on retrouve Pythagore : $BC = \\sqrt{52} = 2\\sqrt{13}$.",
      "Que vaut $\\cos\\dfrac{\\pi}{2}$ ?",
      S("$BC^2 = AB^2 + AC^2 - 2\\,AB \\times AC \\times 0 = 16 + 36 = 52$.", "$BC = \\sqrt{52} = 2\\sqrt{13}$ : c'est le théorème de Pythagore."),
      checks=("2\\sqrt{13}",), verify=_chk(lambda: _al_kashi(4, 6, sp.pi / 2) == 2 * sp.sqrt(13))),
    E(67304, N3, 3,
      "Deux bateaux partent du même port $P$. Le premier parcourt $12$ km dans une direction, le second $8$ km dans une direction faisant un angle de $\\dfrac{\\pi}{3}$ avec la première. Quelle distance les sépare ?",
      "$4\\sqrt{7} \\approx 10{,}6$ km.",
      "Al-Kashi dans le triangle formé par le port et les deux bateaux.",
      S("$d^2 = 12^2 + 8^2 - 2 \\times 12 \\times 8 \\times \\cos\\dfrac{\\pi}{3} = 144 + 64 - 96 = 112$.", "$d = \\sqrt{112} = 4\\sqrt{7} \\approx 10{,}58$ km."),
      checks=("4\\sqrt{7}",), verify=_chk(lambda: _al_kashi(12, 8, sp.pi / 3) == 4 * sp.sqrt(7) and f"{4 * math.sqrt(7):.1f}" == "10.6")),
    E(67305, N3, 3,
      "Dans un triangle $ABC$, $AB = 6$, $AC = 4$ et $\\widehat{BAC} = \\dfrac{\\pi}{3}$. Calculer $BC$, puis $\\cos\\widehat{ABC}$.",
      "$BC = 2\\sqrt{7}$ et $\\cos\\widehat{ABC} = \\dfrac{2\\sqrt{7}}{7}$.",
      "Applique deux fois la formule d'Al-Kashi.",
      S("$BC^2 = 36 + 16 - 2 \\times 6 \\times 4 \\times \\dfrac{1}{2} = 28$, $BC = 2\\sqrt{7}$.",
        "$AC^2 = AB^2 + BC^2 - 2\\,AB \\times BC\\cos\\widehat{B}$ : $16 = 36 + 28 - 24\\sqrt{7}\\cos\\widehat{B}$.",
        "$\\cos\\widehat{B} = \\dfrac{48}{24\\sqrt{7}} = \\dfrac{2}{\\sqrt{7}} = \\dfrac{2\\sqrt{7}}{7}$."),
      checks=("\\dfrac{2\\sqrt{7}}{7}",), verify=_chk(lambda: sp.simplify(sp.Rational(48) / (24 * sp.sqrt(7)) - 2 * sp.sqrt(7) / 7) == 0
                                                       and _al_kashi(6, 4, sp.pi / 3) == 2 * sp.sqrt(7))),
    E(67306, N3, 4,
      "Démontrer la formule d'Al-Kashi : dans un triangle $ABC$, $BC^2 = AB^2 + AC^2 - 2\\,AB \\times AC \\times \\cos\\widehat{BAC}$.",
      "$BC^2 = \\|\\vec{AC} - \\vec{AB}\\|^2 = AC^2 - 2\\vec{AB}\\cdot\\vec{AC} + AB^2$, et $\\vec{AB}\\cdot\\vec{AC} = AB \\times AC \\times \\cos\\widehat{BAC}$.",
      "Écris $\\vec{BC} = \\vec{AC} - \\vec{AB}$.",
      S("Relation de Chasles : $\\vec{BC} = \\vec{BA} + \\vec{AC} = \\vec{AC} - \\vec{AB}$.",
        "$BC^2 = \\|\\vec{AC} - \\vec{AB}\\|^2 = AC^2 - 2\\vec{AB}\\cdot\\vec{AC} + AB^2$ (bilinéarité).",
        "Avec $\\vec{AB}\\cdot\\vec{AC} = AB \\times AC \\times \\cos\\widehat{BAC}$, on obtient la formule."),
      checks=("\\cos\\widehat{BAC}",)),
    E(67307, N3, 4,
      "Loi des sinus (approfondissement). Dans un triangle $ABC$, on note $a = BC$, $b = AC$, $c = AB$ et $h$ la hauteur issue de $C$. Montrer que $h = b\\sin\\widehat{A} = a\\sin\\widehat{B}$, puis que $\\dfrac{a}{\\sin\\widehat{A}} = \\dfrac{b}{\\sin\\widehat{B}}$.",
      "Dans les deux triangles rectangles formés par la hauteur, $h = b\\sin\\widehat{A}$ et $h = a\\sin\\widehat{B}$ ; en égalant : $\\dfrac{a}{\\sin\\widehat{A}} = \\dfrac{b}{\\sin\\widehat{B}}$.",
      "La hauteur issue de $C$ découpe deux triangles rectangles.",
      S("Triangle $ACH$ rectangle en $H$ : $\\sin\\widehat{A} = \\dfrac{h}{b}$, donc $h = b\\sin\\widehat{A}$ (cas des angles aigus).",
        "Triangle $BCH$ rectangle en $H$ : $h = a\\sin\\widehat{B}$.", "$b\\sin\\widehat{A} = a\\sin\\widehat{B}$, soit $\\dfrac{a}{\\sin\\widehat{A}} = \\dfrac{b}{\\sin\\widehat{B}}$."),
      checks=("\\dfrac{a}{\\sin\\widehat{A}}",)),

    # N4 — ensembles de points
    E(67401, N4, 2,
      "Soit $I$ le milieu de $[AB]$. Montrer que pour tout point $M$ : $\\vec{MA}\\cdot\\vec{MB} = MI^2 - \\dfrac{AB^2}{4}$.",
      "$\\vec{MA}\\cdot\\vec{MB} = (\\vec{MI} + \\vec{IA})\\cdot(\\vec{MI} - \\vec{IA}) = MI^2 - IA^2 = MI^2 - \\dfrac{AB^2}{4}$.",
      "Introduis $I$ par la relation de Chasles ; $\\vec{IB} = -\\vec{IA}$.",
      S("$\\vec{MA} = \\vec{MI} + \\vec{IA}$ et $\\vec{MB} = \\vec{MI} + \\vec{IB} = \\vec{MI} - \\vec{IA}$.",
        "$\\vec{MA}\\cdot\\vec{MB} = MI^2 - IA^2$ (identité remarquable).", "$IA = \\dfrac{AB}{2}$, donc $IA^2 = \\dfrac{AB^2}{4}$."),
      checks=("\\dfrac{AB^2}{4}",)),
    E(67402, N4, 3,
      "Soit $A$ et $B$ tels que $AB = 6$ et $I$ le milieu de $[AB]$. Déterminer l'ensemble des points $M$ tels que $\\vec{MA}\\cdot\\vec{MB} = 16$.",
      "$MI^2 = 16 + 9 = 25$ : c'est le cercle de centre $I$ et de rayon $5$.",
      "Utilise $\\vec{MA}\\cdot\\vec{MB} = MI^2 - \\dfrac{AB^2}{4}$.",
      S("$\\vec{MA}\\cdot\\vec{MB} = MI^2 - 9$.", "$MI^2 - 9 = 16 \\iff MI^2 = 25 \\iff MI = 5$.", "Ensemble : cercle de centre $I$, de rayon $5$."),
      checks=("rayon $5$",)),
    E(67403, N4, 3,
      "Soit $AB = 4$ et $I$ le milieu de $[AB]$. Pour quelles valeurs de $k$ l'ensemble des points $M$ tels que $\\vec{MA}\\cdot\\vec{MB} = k$ est-il vide ? réduit à un point ?",
      "Vide si $k < -4$ ; réduit au point $I$ si $k = -4$ ; cercle de centre $I$ et de rayon $\\sqrt{k + 4}$ si $k > -4$.",
      "$MI^2 = k + 4$ doit être positif ou nul.",
      S("$\\vec{MA}\\cdot\\vec{MB} = MI^2 - 4$, donc $MI^2 = k + 4$.", "Si $k + 4 < 0$ : aucun point. Si $k + 4 = 0$ : $M = I$.",
        "Si $k + 4 > 0$ : cercle de centre $I$, de rayon $\\sqrt{k + 4}$."),
      checks=("k = -4",)),
    E(67404, N4, 4,
      "Concourance des hauteurs (approfondissement). a) Montrer que pour tous points $H$, $A$, $B$, $C$ : $\\vec{HA}\\cdot\\vec{BC} + \\vec{HB}\\cdot\\vec{CA} + \\vec{HC}\\cdot\\vec{AB} = 0$. "
      "b) En déduire que les trois hauteurs d'un triangle $ABC$ sont concourantes.",
      "a) Avec $\\vec{a} = \\vec{HA}$, $\\vec{b} = \\vec{HB}$, $\\vec{c} = \\vec{HC}$, la somme vaut $\\vec{a}\\cdot(\\vec{c} - \\vec{b}) + \\vec{b}\\cdot(\\vec{a} - \\vec{c}) + \\vec{c}\\cdot(\\vec{b} - \\vec{a}) = 0$. "
      "b) Si $H$ est sur les hauteurs issues de $A$ et $B$, les deux premiers termes sont nuls, donc $\\vec{HC}\\cdot\\vec{AB} = 0$ : les trois hauteurs sont concourantes.",
      "Exprime $\\vec{BC}$, $\\vec{CA}$, $\\vec{AB}$ à l'aide de $\\vec{HA}$, $\\vec{HB}$, $\\vec{HC}$.",
      S("$\\vec{BC} = \\vec{HC} - \\vec{HB}$, $\\vec{CA} = \\vec{HA} - \\vec{HC}$, $\\vec{AB} = \\vec{HB} - \\vec{HA}$.",
        "En développant par bilinéarité : $\\vec{a}\\cdot\\vec{c} - \\vec{a}\\cdot\\vec{b} + \\vec{b}\\cdot\\vec{a} - \\vec{b}\\cdot\\vec{c} + \\vec{c}\\cdot\\vec{b} - \\vec{c}\\cdot\\vec{a} = 0$ (symétrie).",
        "Soit $H$ l'intersection des hauteurs issues de $A$ et de $B$ : $\\vec{HA}\\cdot\\vec{BC} = 0$ et $\\vec{HB}\\cdot\\vec{CA} = 0$.",
        "Donc $\\vec{HC}\\cdot\\vec{AB} = 0$ : $(HC) \\perp (AB)$, $H$ est aussi sur la hauteur issue de $C$."),
      checks=("concourantes",)),
    E(67405, N4, 2,
      "Dans un repère orthonormé, $A(1 ; 0)$, $B(5 ; 4)$ et $C(1 ; 4)$. Le point $C$ appartient-il au cercle de diamètre $[AB]$ ?",
      "Oui : $\\vec{CA}\\cdot\\vec{CB} = 0$.",
      "$M$ est sur le cercle de diamètre $[AB]$ si et seulement si $\\vec{MA}\\cdot\\vec{MB} = 0$.",
      S("$\\vec{CA}(0 ; -4)$ et $\\vec{CB}(4 ; 0)$.", "$\\vec{CA}\\cdot\\vec{CB} = 0 \\times 4 + (-4) \\times 0 = 0$.", "$C$ est sur le cercle de diamètre $[AB]$ (angle droit en $C$)."),
      checks=("Oui",)),
]

EXERCISES = HIST + NOUVEAUX

QUIZ = {
    "produit-scalaire,-colinearite-et-orthogonalite-de-vecteurs": (1416, 1420, 2116),
    "autres-definitions-et-proprietes": (1475, 1476, 1479),
    "formule-d-al-kashi-et-calculs-dans-le-triangle": (67301, 67302, 67303),
    "etude-d-un-ensemble-de-points": (1534, 1535, 2197),
}
