"""Chapitre 8 — Géométrie repérée : banque curée.

Exercices historiques (banque_ch08_historiques.py, identifiants conservés) :
toutes les réponses ont été recalculées (justes) ; les défauts étaient
d'écriture (« 3x -1y +7 = 0 », « +0y », « (x-(3))^2 », « (3-(0))^2 »,
« \\sqrt{9} », un niveau 5) : textes nettoyés par _clean (équations de droite
et de cercle réécrites terme à terme), quelques corrections au cas par cas.

Nouvelles notions (programme 2026) : « Projeté orthogonal d'un point sur une
droite » (capacité attendue) et « Configurations dans un repère » (médiatrice,
utilisation d'un repère, approfondissements : points équidistants d'une droite
et d'un point, intersections avec une droite parallèle à un axe).
Nouveaux exercices : bloc 68 000, valeurs vérifiées par SymPy.
"""
import re

import sympy as sp

from premiere_specifique.reserve.banque_ch08_historiques import HISTORIQUES
from premiere_specifique.banque_commun import E, S

CHAPTER_NUMBER = 8
N1 = "Vecteur normal à une droite"
N2 = "Projeté orthogonal d'un point sur une droite"
N3 = "Équation d'un cercle"
N4 = "Configurations dans un repère"
NOTIONS = (N1, N2, N3, N4)
NOTION_IDS = (
    "vecteur-normal-a-une-droite",
    "projete-orthogonal-d-un-point-sur-une-droite",
    "equation-d-un-cercle",
    "configurations-dans-un-repere",
)
LEGACY_IDS = tuple(h[0] for h in HISTORIQUES)
x, y = sp.symbols("x y")


# ── Nettoyage des écritures historiques ──────────────────────────────────────

def _terms(seq):
    return [(s, int(c) if c else 1, v) for s, c, v in re.findall(r"([+-])\s*(\d*)\s*([xy]?)", seq) if c or v]


def _join(terms, lead=""):
    out = lead
    for s, c, v in terms:
        if c == 0:
            continue
        body = (str(c) if (c != 1 or not v) else "") + v
        out += (f"{'-' if s == '-' else ''}{body}" if not out else f" {s} {body}")
    return out


_LINE = re.compile(r"(-?\d*)x\s*([+-])\s*(\d*)y\s*([+-])\s*(\d+)\s*=\s*0")
_CIRCLE = re.compile(r"x\^2\s*\+\s*y\^2((?:\s*[+-]\s*\d*\s*[xy]?)+?)\s*=\s*0")


def _line(m):
    a = m.group(1)
    sign_a = "-" if a.startswith("-") else "+"
    ca = int(a.lstrip("-")) if a.lstrip("-") else 1
    terms = [(sign_a, ca, "x"), (m.group(2), int(m.group(3)) if m.group(3) else 1, "y"), (m.group(4), int(m.group(5)), "")]
    return _join(terms) + " = 0"


def _circle(m):
    return _join(_terms(m.group(1)), "x^2 + y^2") + " = 0"


def _var(m):
    v, q = m.group(1), int(m.group(2))
    return v if q == 0 else (f"({v} - {q})" if q > 0 else f"({v} + {-q})")


def _num(m):
    p, q = int(m.group(1)), int(m.group(2))
    return f"({p} - {q})" if q >= 0 else f"({p} + {-q})"


def _clean(t):
    t = re.sub(r"\(([xy])\s*-\s*\((-?\d+)\)\)", _var, t)
    t = re.sub(r"\(([xy])\s*-\s*(0)\)", _var, t)
    t = re.sub(r"\((-?\d+)\s*-\s*\((-?\d+)\)\)", _num, t)
    t = _CIRCLE.sub(_circle, t)
    t = _LINE.sub(_line, t)
    t = re.sub(r"\\times\s*-\s*(\d+)", r"\\times (-\1)", t)
    t = re.sub(r"\+\s*-\s*(\d)", r"- \1", t)
    t = re.sub(r"\s*-\s*\(0\)", " - 0", t)
    t = re.sub(r"([+-])\s*1\(", r" \1 (", t)
    # espaces autour des signes dans les sommes (« x^2 -6x +30 » → « x^2 - 6x + 30 »)
    t = re.sub(r"(?<=[\dxy)])\s*([+-])(?=\d)", r" \1 ", t)
    t = re.sub(r"(?<=[\dxy)])\s+([+-])\s*(?=[xy(])", r" \1 ", t)
    return t


OVERRIDES = {
    1664: dict(steps=("On regroupe : $x^2 - 6x + y^2 = 7$.", "On complète le carré : $(x - 3)^2 - 9 + y^2 = 7$.",
                      "D'où $(x - 3)^2 + y^2 = 16$.", "C'est l'équation du cercle de centre $\\Omega(3 ; 0)$ et de rayon $4$.")),
    2178: dict(answer="$\\mathcal{C}$ a pour centre $\\Omega(3 ; 2)$ et pour rayon $3$ ; $P$ appartient à $\\mathcal{C}$"),
}

_STEP_PREFIX = re.compile(r"^\s*Étape\s*\d+\s*[:—-]\s*")


def _hist(h):
    i, notion, level, enonce, answer, hint, steps = h
    o = dict(enonce=_clean(enonce), answer=_clean(answer), hint=_clean(hint),
             steps=tuple(_clean(_STEP_PREFIX.sub("", s)) for s in steps))
    o.update(OVERRIDES.get(i, {}))
    return E(i, notion, min(level, 4), o["enonce"], o["answer"], o["hint"], S(*o["steps"]))


HIST = [_hist(h) for h in HISTORIQUES]


# ── Nouveaux exercices ───────────────────────────────────────────────────────

def _chk(cond_fn):
    return lambda: None if cond_fn() else "valeur fausse"


def _projete(a, b, c, px, py):
    """Projeté orthogonal de P(px ; py) sur ax + by + c = 0."""
    t = sp.Rational(-(a * px + b * py + c), a * a + b * b)
    return (px + a * t, py + b * t)


NOUVEAUX = [
    # N1 — vecteur normal
    E(68101, N1, 1,
      "Donner un vecteur normal et un vecteur directeur de la droite $d : 2x - 3y + 5 = 0$.",
      "Vecteur normal $\\vec{n}(2 ; -3)$ ; vecteur directeur $\\vec{u}(3 ; 2)$.",
      "Pour $ax + by + c = 0$ : $\\vec{n}(a ; b)$ et $\\vec{u}(-b ; a)$.",
      S("$d : ax + by + c = 0$ avec $a = 2$, $b = -3$ : $\\vec{n}(2 ; -3)$.", "Vecteur directeur $\\vec{u}(-b ; a) = (3 ; 2)$.",
        "Contrôle : $\\vec{n}\\cdot\\vec{u} = 6 - 6 = 0$."),
      checks=("\\vec{u}(3 ; 2)",)),
    E(68102, N1, 2,
      "Déterminer une équation de la droite perpendiculaire à $d : x + 2y - 1 = 0$ passant par $A(3 ; -1)$.",
      "$2x - y - 7 = 0$.",
      "Un vecteur directeur de $d$ est un vecteur normal de la perpendiculaire.",
      S("Un vecteur directeur de $d$ est $\\vec{u}(-2 ; 1)$, ou $(2 ; -1)$.", "La perpendiculaire a pour vecteur normal $(2 ; -1)$ : $2x - y + c = 0$.",
        "$A$ : $6 + 1 + c = 0$, donc $c = -7$."),
      checks=("2x - y - 7 = 0",), verify=_chk(lambda: 2 * 3 - (-1) - 7 == 0 and 1 * 2 + 2 * (-1) == 0)),
    E(68103, N1, 3,
      "Les droites $d_1 : 3x - y + 2 = 0$ et $d_2 : x + 3y - 4 = 0$ sont-elles perpendiculaires ? Calculer les coordonnées de leur point d'intersection.",
      "Oui, $\\vec{n_1}\\cdot\\vec{n_2} = 0$ ; elles se coupent en $\\left(-\\dfrac{1}{5} ; \\dfrac{7}{5}\\right)$.",
      "Deux droites sont perpendiculaires si et seulement si leurs vecteurs normaux sont orthogonaux.",
      S("$\\vec{n_1}(3 ; -1)\\cdot\\vec{n_2}(1 ; 3) = 3 - 3 = 0$ : perpendiculaires.", "De $d_1$ : $y = 3x + 2$ ; dans $d_2$ : $x + 9x + 6 - 4 = 0$, $x = -\\dfrac{1}{5}$.",
        "$y = -\\dfrac{3}{5} + 2 = \\dfrac{7}{5}$."),
      checks=("\\dfrac{7}{5}",), verify=_chk(lambda: sp.solve([3 * x - y + 2, x + 3 * y - 4], [x, y]) == {x: sp.Rational(-1, 5), y: sp.Rational(7, 5)})),

    # N2 — projeté orthogonal
    E(68201, N2, 1,
      "Déterminer le projeté orthogonal du point $A(3 ; 5)$ sur l'axe des abscisses, puis sur la droite d'équation $y = 2$.",
      "Sur l'axe des abscisses : $(3 ; 0)$ ; sur la droite $y = 2$ : $(3 ; 2)$.",
      "On garde l'abscisse et on « descend » verticalement.",
      S("La perpendiculaire à une droite horizontale passant par $A$ est la droite verticale $x = 3$.", "Intersections : $(3 ; 0)$ et $(3 ; 2)$."),
      checks=("(3 ; 2)",)),
    E(68202, N2, 2,
      "Déterminer les coordonnées du projeté orthogonal $H$ du point $A(4 ; 2)$ sur la droite $d : x + y - 2 = 0$.",
      "$H(2 ; 0)$.",
      "La droite $(AH)$ passe par $A$ et est dirigée par le vecteur normal $\\vec{n}(1 ; 1)$ de $d$.",
      S("$(AH)$ : $x = 4 + t$, $y = 2 + t$ ($\\vec{n}(1 ; 1)$ directeur).", "Dans $d$ : $4 + t + 2 + t - 2 = 0$, donc $t = -2$.", "$H(2 ; 0)$."),
      checks=("H(2 ; 0)",), verify=_chk(lambda: _projete(1, 1, -2, 4, 2) == (2, 0))),
    E(68203, N2, 3,
      "Déterminer les coordonnées du projeté orthogonal $H$ de $A(1 ; 6)$ sur $d : 2x - y + 1 = 0$, puis la distance de $A$ à $d$.",
      "$H\\left(\\dfrac{11}{5} ; \\dfrac{27}{5}\\right)$ et $AH = \\dfrac{3\\sqrt{5}}{5}$.",
      "Écris $H = A + t\\,\\vec{n}$ et $H \\in d$.",
      S("$\\vec{n}(2 ; -1)$ ; $H(1 + 2t ; 6 - t)$.", "$2(1 + 2t) - (6 - t) + 1 = 0 \\iff 5t - 3 = 0 \\iff t = \\dfrac{3}{5}$.",
        "$H\\left(\\dfrac{11}{5} ; \\dfrac{27}{5}\\right)$ et $AH = \\dfrac{3}{5}\\|\\vec{n}\\| = \\dfrac{3\\sqrt{5}}{5}$."),
      checks=("\\dfrac{27}{5}",), verify=_chk(lambda: _projete(2, -1, 1, 1, 6) == (sp.Rational(11, 5), sp.Rational(27, 5)))),
    E(68204, N2, 2,
      "Soit $d : x - 2y + 3 = 0$ et $A(4 ; -1)$. Le point $H(1 ; 2)$ est-il le projeté orthogonal de $A$ sur $d$ ? Justifier.",
      "Non : $H \\in d$, mais $\\vec{AH}(-3 ; 3)$ n'est pas colinéaire au vecteur normal $\\vec{n}(1 ; -2)$. Le projeté est $\\left(\\dfrac{11}{5} ; \\dfrac{13}{5}\\right)$.",
      "Le projeté doit être sur $d$ ET $\\vec{AH}$ doit être colinéaire à un vecteur normal de $d$.",
      S("$H \\in d$ : $1 - 4 + 3 = 0$, oui.", "$\\vec{AH}(-3 ; 3)$ et $\\vec{n}(1 ; -2)$ : $(-3) \\times (-2) - 3 \\times 1 = 3 \\neq 0$, pas colinéaires.",
        "Donc $H$ n'est pas le projeté ; avec $A + t\\vec{n}$ : $9 + 5t = 0$, $t = -\\dfrac{9}{5}$, projeté $\\left(\\dfrac{11}{5} ; \\dfrac{13}{5}\\right)$."),
      checks=("Non",), verify=_chk(lambda: _projete(1, -2, 3, 4, -1) == (sp.Rational(11, 5), sp.Rational(13, 5)))),
    E(68205, N2, 3,
      "Déterminer le projeté orthogonal $H$ de l'origine $O$ sur la droite $d : 3x + 4y - 25 = 0$, puis la distance de $O$ à $d$.",
      "$H(3 ; 4)$ et $OH = 5$.",
      "$H = t\\,\\vec{n}$ avec $\\vec{n}(3 ; 4)$.",
      S("$H(3t ; 4t)$ et $H \\in d$ : $9t + 16t - 25 = 0$, $t = 1$.", "$H(3 ; 4)$ ; $OH = \\sqrt{9 + 16} = 5$.",
        "C'est la plus petite distance de $O$ à un point de $d$."),
      checks=("OH = 5",), verify=_chk(lambda: _projete(3, 4, -25, 0, 0) == (3, 4))),
    E(68206, N2, 4,
      "Soit $A(0 ; 0)$, $B(6 ; 2)$ et $C(1 ; 5)$. Déterminer le pied $H$ de la hauteur issue de $C$ dans le triangle $ABC$, puis l'aire du triangle.",
      "$H\\left(\\dfrac{12}{5} ; \\dfrac{4}{5}\\right)$ et aire $= 14$.",
      "$H$ est le projeté orthogonal de $C$ sur $(AB)$, d'équation $x - 3y = 0$.",
      S("$(AB)$ : vecteur directeur $(6 ; 2)$, vecteur normal $(1 ; -3)$ : $x - 3y = 0$.",
        "$H = C + t(1 ; -3)$ : $1 + t - 3(5 - 3t) = 0 \\iff 10t = 14 \\iff t = \\dfrac{7}{5}$, $H\\left(\\dfrac{12}{5} ; \\dfrac{4}{5}\\right)$.",
        "$CH = \\dfrac{7}{5}\\sqrt{10}$, $AB = 2\\sqrt{10}$ : aire $= \\dfrac{1}{2} \\times 2\\sqrt{10} \\times \\dfrac{7\\sqrt{10}}{5} = 14$."),
      checks=("14",), verify=_chk(lambda: _projete(1, -3, 0, 1, 5) == (sp.Rational(12, 5), sp.Rational(4, 5)))),

    # N3 — cercle
    E(68301, N3, 2,
      "Le cercle de centre $\\Omega(2 ; -1)$ passe par le point $A(5 ; 3)$. Déterminer son équation.",
      "$(x - 2)^2 + (y + 1)^2 = 25$.",
      "Le rayon est la distance $\\Omega A$.",
      S("$\\Omega A^2 = 3^2 + 4^2 = 25$.", "Équation : $(x - 2)^2 + (y + 1)^2 = 25$."),
      checks=("= 25",)),
    E(68302, N3, 2,
      "L'équation $x^2 + y^2 - 4x + 2y + 10 = 0$ est-elle celle d'un cercle ?",
      "Non : elle équivaut à $(x - 2)^2 + (y + 1)^2 = -5$, impossible (une somme de carrés est positive).",
      "Complète les carrés et regarde le membre de droite.",
      S("$(x - 2)^2 - 4 + (y + 1)^2 - 1 + 10 = 0$.", "$(x - 2)^2 + (y + 1)^2 = -5 < 0$ : aucun point ne convient."),
      checks=("Non",)),
    E(68303, N3, 3,
      "Déterminer les points d'intersection du cercle $\\mathcal{C} : (x - 1)^2 + (y - 2)^2 = 25$ et de la droite d'équation $x = 4$.",
      "$(4 ; 6)$ et $(4 ; -2)$.",
      "Remplace $x$ par $4$ dans l'équation du cercle.",
      S("$9 + (y - 2)^2 = 25 \\iff (y - 2)^2 = 16$.", "$y - 2 = 4$ ou $y - 2 = -4$ : $y = 6$ ou $y = -2$."),
      checks=("(4 ; -2)",), verify=_chk(lambda: set(sp.solve((4 - 1) ** 2 + (y - 2) ** 2 - 25, y)) == {6, -2})),
    E(68304, N3, 3,
      "Soit $\\mathcal{C}$ le cercle de centre $\\Omega(1 ; 1)$ et de rayon $\\sqrt{5}$, et $A(3 ; 2)$. Vérifier que $A \\in \\mathcal{C}$ et déterminer une équation de la tangente à $\\mathcal{C}$ en $A$.",
      "$\\Omega A^2 = 5$ ; tangente : $2x + y - 8 = 0$.",
      "La tangente en $A$ est perpendiculaire au rayon $[\\Omega A]$ : $\\vec{\\Omega A}$ en est un vecteur normal.",
      S("$\\Omega A^2 = 2^2 + 1^2 = 5$ : $A \\in \\mathcal{C}$.", "$\\vec{\\Omega A}(2 ; 1)$ est normal à la tangente : $2x + y + c = 0$.",
        "$A$ : $6 + 2 + c = 0$, $c = -8$."),
      checks=("2x + y - 8 = 0",)),

    # N4 — configurations
    E(68407, N4, 1,
      "Dans un repère orthonormé, $A(1 ; 2)$ et $B(7 ; 10)$. Calculer la distance $AB$ et les coordonnées du milieu $I$ de $[AB]$.",
      "$AB = 10$ et $I(4 ; 6)$.",
      "$AB = \\sqrt{(x_B - x_A)^2 + (y_B - y_A)^2}$.",
      S("$AB = \\sqrt{6^2 + 8^2} = \\sqrt{100} = 10$.", "$I\\left(\\dfrac{1 + 7}{2} ; \\dfrac{2 + 10}{2}\\right) = (4 ; 6)$."),
      checks=("AB = 10",), verify=_chk(lambda: sp.sqrt(6 ** 2 + 8 ** 2) == 10)),
    E(68401, N4, 2,
      "Déterminer une équation de la médiatrice de $[AB]$ avec $A(1 ; 2)$ et $B(5 ; 4)$, en utilisant le milieu et un vecteur normal.",
      "$2x + y - 9 = 0$.",
      "La médiatrice passe par le milieu $I$ de $[AB]$ et admet $\\vec{AB}$ comme vecteur normal.",
      S("$I(3 ; 3)$ et $\\vec{AB}(4 ; 2)$.", "$4(x - 3) + 2(y - 3) = 0 \\iff 4x + 2y - 18 = 0 \\iff 2x + y - 9 = 0$."),
      checks=("2x + y - 9 = 0",)),
    E(68402, N4, 3,
      "Déterminer le centre du cercle circonscrit au triangle $A(0 ; 0)$, $B(4 ; 0)$, $C(0 ; 6)$, puis son rayon.",
      "Centre $(2 ; 3)$, rayon $\\sqrt{13}$.",
      "Le centre est l'intersection des médiatrices.",
      S("Médiatrice de $[AB]$ : $x = 2$ ; médiatrice de $[AC]$ : $y = 3$.", "Centre $\\Omega(2 ; 3)$ ; $\\Omega A = \\sqrt{4 + 9} = \\sqrt{13}$.",
        "Le triangle est rectangle en $A$ : le centre est le milieu de l'hypoténuse $[BC]$."),
      checks=("\\sqrt{13}",)),
    E(68403, N4, 3,
      "Dans un repère, $A(0 ; 0)$, $B(a ; 0)$, $D(0 ; b)$ et $C(a ; b)$ forment un rectangle. Démontrer que ses diagonales ont la même longueur.",
      "$AC = BD = \\sqrt{a^2 + b^2}$.",
      "Calcule $AC^2$ et $BD^2$ avec les coordonnées.",
      S("$AC^2 = a^2 + b^2$.", "$\\vec{BD}(-a ; b)$, $BD^2 = a^2 + b^2$.", "Donc $AC = BD$."),
      checks=("\\sqrt{a^2 + b^2}",)),
    E(68404, N4, 4,
      "Approfondissement. Déterminer l'ensemble des points $M(x ; y)$ équidistants de l'axe des abscisses et du point $F(0 ; 2)$.",
      "La parabole d'équation $y = \\dfrac{x^2}{4} + 1$.",
      "La distance de $M$ à l'axe des abscisses est $|y|$.",
      S("$MF^2 = x^2 + (y - 2)^2$ et la distance à l'axe vaut $|y|$.", "$x^2 + (y - 2)^2 = y^2 \\iff x^2 - 4y + 4 = 0$.", "$y = \\dfrac{x^2}{4} + 1$ : c'est une parabole."),
      checks=("\\dfrac{x^2}{4} + 1",), verify=_chk(lambda: sp.expand(x ** 2 + (y - 2) ** 2 - y ** 2) == sp.expand(x ** 2 - 4 * y + 4))),
    E(68405, N4, 3,
      "Approfondissement. Déterminer les points d'intersection de la parabole $y = x^2 - 2x - 1$ et de la droite d'équation $y = 2$.",
      "$(-1 ; 2)$ et $(3 ; 2)$.",
      "Résous $x^2 - 2x - 1 = 2$.",
      S("$x^2 - 2x - 3 = 0 \\iff (x + 1)(x - 3) = 0$.", "Les points sont $(-1 ; 2)$ et $(3 ; 2)$."),
      checks=("(3 ; 2)",), verify=_chk(lambda: set(sp.solve(x ** 2 - 2 * x - 3, x)) == {-1, 3})),
    E(68406, N4, 2,
      "Dans un repère orthonormé, $A(-1 ; 0)$, $B(3 ; 2)$ et $C(0 ; 3)$. Montrer que le triangle $ABC$ est isocèle en $C$.",
      "$CA = CB = \\sqrt{10}$.",
      "Compare $CA^2$ et $CB^2$.",
      S("$\\vec{CA}(-1 ; -3)$ : $CA^2 = 1 + 9 = 10$.", "$\\vec{CB}(3 ; -1)$ : $CB^2 = 9 + 1 = 10$.", "$CA = CB$ : le triangle est isocèle en $C$."),
      checks=("\\sqrt{10}",), verify=_chk(lambda: (-1) ** 2 + (-3) ** 2 == 3 ** 2 + (-1) ** 2 == 10)),
]

EXERCISES = HIST + NOUVEAUX

QUIZ = {
    "vecteur-normal-a-une-droite": (1593, 1594, 1595),
    "projete-orthogonal-d-un-point-sur-une-droite": (68201, 68202, 68204),
    "equation-d-un-cercle": (1652, 1659, 2159),
    "configurations-dans-un-repere": (68401, 68406, 68407),
}
