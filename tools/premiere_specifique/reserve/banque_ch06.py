"""Chapitre 6 — Trigonométrie : banque curée.

Programme 2026 : cercle trigonométrique, longueur d'arc, radian ;
enroulement, image d'un réel ; cosinus et sinus d'un réel, lien avec le
triangle rectangle, valeurs remarquables ; lecture du cercle pour les angles
associés. Les FONCTIONS cosinus et sinus (parité, périodicité, variations,
courbes) ne sont plus au programme de Première : la notion « Fonctions
cosinus et sinus » est retirée (cours_ch06.NOTIONS_RETIREES) et ses
exercices sont rattachés à « Angles associés et lecture du cercle », avec
des justifications par les symétries du cercle et les tours complets.

Exercices historiques (banque_ch06_historiques.py, identifiants conservés) :
textes repris, niveaux 5 ramenés à 4, numérotation des étapes harmonisée ;
réécriture des justifications « fonction paire / impaire / périodique /
décroissante » (OVERRIDES). Contrôle SymPy de CHAQUE égalité numérique
« cos(…) = … » ou « sin(…) = … » écrite dans la réponse et la correction,
et de chaque ensemble de solutions d'équation (_verifier).

Nouveaux exercices : bloc 66 000.
"""
import dataclasses
import math
import re
import sys
from pathlib import Path

import sympy as sp

from premiere_specifique.reserve.banque_ch06_historiques import HISTORIQUES
from premiere_specifique.banque_commun import E, S, code

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "webapp"))  # reserve/ : un niveau de plus
from exercise_generator_premiere_specifique import _tex  # noqa: E402

CHAPTER_NUMBER = 6
N1 = "Repérage sur le cercle trigonométrique"
N2 = "Coordonnées d'un point du cercle trigonométrique"
N3 = "Angles associés et lecture du cercle"
NOTIONS = (N1, N2, N3)
NOTION_IDS = (
    "reperage-sur-le-cercle-trigonometrique",
    "coordonnees-d-un-point-du-cercle-trigonometrique",
    "angles-associes-et-lecture-du-cercle",
)
_RETIREE = "Fonctions cosinus et sinus"
LEGACY_IDS = tuple(h[0] for h in HISTORIQUES)


# ── Vérification SymPy des valeurs écrites ───────────────────────────────────

_MATH = re.compile(r"\$([^$]+)\$")
_SKIP = ("\\iff", "\\text", "\\in", "\\{", "<", ">", "\\leqslant", "\\geqslant", "\\approx", "k", "\\pm", "\\Rightarrow")


def _num(part):
    try:
        v = _tex.parse(part.strip(), symbols=())
    except Exception:
        return None
    return v if v.is_number else None


def _egalites(texts):
    """Vérifie chaque égalité numérique d'un segment mathématique dont un
    membre contient cos ou sin. Renvoie (nombre vérifié, message d'erreur)."""
    checked = 0
    for t in texts:
        for seg in _MATH.findall(t):
            if "=" not in seg or not ("\\cos" in seg or "\\sin" in seg) or any(s in seg for s in _SKIP):
                continue
            parts = [p for p in seg.split("=")]
            vals = [_num(p) for p in parts]
            nums = [v for v in vals if v is not None]
            if len(nums) < 2:
                continue
            for v in nums[1:]:
                if sp.simplify(v - nums[0]) != 0:
                    return checked, f"égalité fausse : {seg}"
            checked += 1
    return checked, None


_EQ = re.compile(r"l'équation \$(\\cos|\\sin)\(x\) = ([^$]+)\$")
_INTERVAL = re.compile(r"dans \$(\]|\[)\s*(-?[^;$]+?)\s*;\s*([^$\]\[]+?)\s*(\]|\[)\$")
_SET = re.compile(r"\\mathcal\{S\} = \\left\\\{(.+?)\\right\\\}")


def _equation(enonce, answer):
    m, mi, ms = _EQ.search(enonce), _INTERVAL.search(enonce.replace("\\,", "")), _SET.search(answer)
    if not (m and mi and ms):
        return None
    f = sp.cos if m.group(1) == "\\cos" else sp.sin
    x = sp.Symbol("x", real=True)
    rhs = _tex.parse(m.group(2), symbols=())
    lo, hi = _tex.parse(mi.group(2), symbols=()), _tex.parse(mi.group(3), symbols=())
    interval = sp.Interval(lo, hi, left_open=mi.group(1) == "]", right_open=mi.group(4) == "[")
    expected = sp.solveset(sp.Eq(f(x), rhs), x, interval)
    given = sp.FiniteSet(*[_tex.parse(s, symbols=()) for s in ms.group(1).split(";")])
    return None if sp.simplify(sp.Complement(expected, given)) == sp.S.EmptySet and len(given) == len(expected) else "solutions fausses"


def _verifier(e):
    def run():
        msg = _equation(e.enonce, e.answer)
        if msg:
            return msg
        return _egalites([e.answer, *e.steps])[1]
    return run


# ── Historiques ──────────────────────────────────────────────────────────────

_HINT_FONCTIONS = "Utiliser la parité (cosinus pair, sinus impair) et la périodicité ($2\\pi$) des fonctions trigonométriques."
_HINT_CERCLE = "Utilise les symétries du cercle trigonométrique et le fait qu'un tour complet ($2\\pi$) ramène au même point."

OVERRIDES = {
    1357: dict(steps=("Les points images de $a$ et de $-a$ sont symétriques par rapport à l'axe des abscisses : leurs ordonnées sont opposées, $\\sin(-a) = -\\sin(a)$.",
                      "Donc $\\sin(-a) + \\sin(a) = -\\sin(a) + \\sin(a) = 0$.")),
    1367: dict(steps=("Ajouter $2\\pi$ revient à faire un tour complet du cercle : le point image ne change pas.",
                      "$a + 5 \\times 2\\pi$ correspond à $5$ tours de plus : même point image que $a$, donc $\\cos(a + 5 \\times 2\\pi) = \\cos(a)$.")),
    1372: dict(steps=("Retrancher $2\\pi$ revient à faire un tour complet dans le sens indirect : le point image ne change pas.",
                      "$\\sin(a - 5 \\times 2\\pi) = \\sin(a)$.")),
    1385: dict(steps=("Les points images de $a$ et de $-a$ sont symétriques par rapport à l'axe des abscisses : ils ont la même abscisse, $\\cos(-a) = \\cos(a)$.",
                      "Donc $\\cos(-a) + \\cos(a) = 2\\cos(a)$.")),
    2227: dict(steps=("$\\dfrac{11\\pi}{6} = -\\dfrac{\\pi}{6} + 2\\pi$ : un tour complet de plus, même point image que $-\\dfrac{\\pi}{6}$.",
                      "Les points images de $\\dfrac{\\pi}{6}$ et $-\\dfrac{\\pi}{6}$ sont symétriques par rapport à l'axe des abscisses : ordonnées opposées.",
                      "$\\sin\\left(\\dfrac{11\\pi}{6}\\right) = -\\sin\\left(\\dfrac{\\pi}{6}\\right) = -\\dfrac{1}{2}$.")),
    2228: dict(steps=("$\\dfrac{13\\pi}{3} = \\dfrac{\\pi}{3} + 2 \\times 2\\pi$ : deux tours complets de plus.",
                      "Le point image est celui de $\\dfrac{\\pi}{3}$.", "$\\cos\\left(\\dfrac{13\\pi}{3}\\right) = \\cos\\left(\\dfrac{\\pi}{3}\\right) = \\dfrac{1}{2}$.")),
    2229: dict(hint="Le point image de $-a$ est le symétrique de celui de $a$ par rapport à l'axe des abscisses.",
               steps=("Symétrie par rapport à l'axe des abscisses : $\\sin\\left(-\\dfrac{7\\pi}{6}\\right) = -\\sin\\left(\\dfrac{7\\pi}{6}\\right)$.",
                      "$\\dfrac{7\\pi}{6} = \\pi + \\dfrac{\\pi}{6}$ (point diamétralement opposé) : $\\sin\\left(\\dfrac{7\\pi}{6}\\right) = -\\sin\\left(\\dfrac{\\pi}{6}\\right) = -\\dfrac{1}{2}$.",
                      "Ainsi $\\sin\\left(-\\dfrac{7\\pi}{6}\\right) = -\\left(-\\dfrac{1}{2}\\right) = \\dfrac{1}{2}$.")),
    2232: dict(hint="Combien de tours complets représente $2026 \\times 2\\pi$ ?",
               steps=("$2026 \\times 2\\pi$ correspond à $2\\,026$ tours complets : le point image ne change pas.",
                      "$\\cos\\left(\\dfrac{\\pi}{2} + 2026 \\times 2\\pi\\right) = \\cos\\left(\\dfrac{\\pi}{2}\\right) = 0$.",
                      "L'affirmation est vraie, quel que soit le nombre entier de tours.")),
    2235: dict(hint="Les points images de $x$ et $-x$ sont symétriques par rapport à l'axe des abscisses.",
               steps=("L'élève confond le cosinus et le sinus.",
                      "Les points images de $x$ et $-x$ sont symétriques par rapport à l'axe des abscisses : même abscisse, ordonnées opposées.",
                      "Donc $\\cos(-x) = \\cos(x)$ (et c'est le sinus qui change de signe : $\\sin(-x) = -\\sin(x)$) : l'affirmation est fausse.")),
    2237: dict(hint="Les tours complets s'ajoutent à l'angle, pas au cosinus.",
               steps=("L'élève a ajouté $6\\pi$ en dehors du cosinus : c'est une erreur de manipulation.",
                      "$a + 3 \\times 2\\pi$ correspond à $3$ tours complets de plus que $a$ : même point image, donc même cosinus.",
                      "La simplification correcte est $\\cos(a + 3 \\times 2\\pi) = \\cos(a)$.")),
    2240: dict(hint="Sur le cercle, quand l'angle augmente de $0$ à $\\pi$, le point se déplace vers la gauche.",
               steps=("Les points images de $\\dfrac{\\pi}{5}$ et $\\dfrac{\\pi}{3}$ sont sur le demi-cercle supérieur, parcouru de $A(1 ; 0)$ vers $(-1 ; 0)$ quand l'angle va de $0$ à $\\pi$.",
                      "Sur ce demi-cercle, plus l'angle est grand, plus le point est à gauche : son abscisse est plus petite.",
                      "$\\dfrac{\\pi}{5} < \\dfrac{\\pi}{3}$, donc $\\cos\\left(\\dfrac{\\pi}{5}\\right) > \\cos\\left(\\dfrac{\\pi}{3}\\right)$.")),
}

_STEP_PREFIX = re.compile(r"^\s*Étape\s*\d+\s*[:—-]\s*")


def _hist(h):
    i, notion, level, enonce, answer, hint, steps = h
    o = OVERRIDES.get(i, {})
    notion = N3 if notion == _RETIREE else notion
    hint = o.get("hint", _HINT_CERCLE if hint == _HINT_FONCTIONS else hint)
    steps = o.get("steps", tuple(_STEP_PREFIX.sub("", s) for s in steps))
    e = E(i, notion, min(level, 4), o.get("enonce", enonce), o.get("answer", answer), hint, S(*steps))
    return dataclasses.replace(e, verify=_verifier(e))


HIST = [_hist(h) for h in HISTORIQUES]


# ── Nouveaux exercices ───────────────────────────────────────────────────────

def _chk(cond_fn):
    return lambda: None if cond_fn() else "valeur fausse"


def _new(*args, **kw):
    e = E(*args, **kw)
    return e if e.verify is not None else dataclasses.replace(e, verify=_verifier(e))


def _archimede(n_doublements):
    """Demi-périmètre du polygone régulier inscrit dans le cercle de rayon 1,
    en partant de l'hexagone (côté 1) et en doublant le nombre de côtés."""
    c, n = 1.0, 6
    for _ in range(n_doublements):
        c, n = math.sqrt(2 - math.sqrt(4 - c * c)), 2 * n
    return n * c / 2


NOUVEAUX = [
    # N1 — repérage, radian, longueur d'arc, enroulement, Archimède
    _new(66101, N1, 1,
         "Sur un cercle de rayon $3$ cm, quelle est la longueur de l'arc intercepté par un angle de $2$ radians ?",
         "La longueur de l'arc est $6$ cm.",
         "Longueur d'arc $=$ rayon $\\times$ angle (en radians).",
         S("Sur un cercle de rayon $r$, un angle de $\\theta$ radians intercepte un arc de longueur $r\\theta$.", "$3 \\times 2 = 6$ cm."),
         checks=("$6$ cm",)),
    _new(66102, N1, 1,
         "Sur le cercle trigonométrique (rayon $1$), quelle est la longueur de l'arc correspondant à un angle de $\\dfrac{\\pi}{3}$ radian ? En donner une valeur approchée au centième.",
         "La longueur est $\\dfrac{\\pi}{3} \\approx 1{,}05$.",
         "Sur un cercle de rayon $1$, la longueur de l'arc est égale à la mesure en radians.",
         S("Rayon $1$ : longueur $= 1 \\times \\dfrac{\\pi}{3}$.", "$\\dfrac{\\pi}{3} \\approx 1{,}047$, soit $1{,}05$."),
         checks=("1{,}05",), verify=_chk(lambda: f"{math.pi / 3:.2f}" == "1.05")),
    _new(66103, N1, 2,
         "Une roue de rayon $30$ cm tourne d'un angle de $\\dfrac{5\\pi}{6}$ radian. Quelle distance parcourt un point de sa circonférence (au millimètre près) ?",
         "$30 \\times \\dfrac{5\\pi}{6} = 25\\pi \\approx 78{,}5$ cm.",
         "Longueur d'arc $= r\\theta$.",
         S("$L = r\\theta = 30 \\times \\dfrac{5\\pi}{6} = 25\\pi$.", "$25\\pi \\approx 78{,}54$, soit $78{,}5$ cm."),
         checks=("78{,}5",), verify=_chk(lambda: f"{25 * math.pi:.1f}" == "78.5")),
    _new(66104, N1, 2,
         "Quel est le point image du réel $\\dfrac{2026\\pi}{3}$ sur le cercle trigonométrique ? Donner une mesure de l'angle dans $]-\\pi ; \\pi]$.",
         "$\\dfrac{2026\\pi}{3} = -\\dfrac{2\\pi}{3} + 338 \\times 2\\pi$ : c'est le point image de $-\\dfrac{2\\pi}{3}$.",
         "Retire le plus grand nombre possible de tours complets.",
         S("$\\dfrac{2026\\pi}{3} \\div 2\\pi = \\dfrac{2026}{6} \\approx 337{,}7$.", "$\\dfrac{2026\\pi}{3} - 338 \\times 2\\pi = \\dfrac{2026\\pi - 2028\\pi}{3} = -\\dfrac{2\\pi}{3}$.",
           "$-\\dfrac{2\\pi}{3} \\in ]-\\pi ; \\pi]$ : c'est la mesure cherchée."),
         checks=("-\\dfrac{2\\pi}{3}",), verify=_chk(lambda: sp.Rational(2026, 3) - 338 * 2 == sp.Rational(-2, 3))),
    _new(66105, N1, 1,
         "Combien mesure, en radians, un angle de $1$ degré ? Et combien mesure, en degrés, un angle de $1$ radian (au dixième) ?",
         "$1° = \\dfrac{\\pi}{180}$ rad et $1$ rad $= \\dfrac{180}{\\pi}° \\approx 57{,}3°$.",
         "$180° \\leftrightarrow \\pi$ rad.",
         S("Proportionnalité : $\\pi$ rad correspond à $180°$.", "$1° = \\dfrac{\\pi}{180}$ rad ; $1$ rad $= \\dfrac{180}{\\pi}° \\approx 57{,}3°$."),
         checks=("57{,}3",), verify=_chk(lambda: f"{180 / math.pi:.1f}" == "57.3")),
    _new(66106, N1, 3,
         "Méthode d'Archimède. On inscrit dans le cercle de rayon $1$ un hexagone régulier (côté $c_6 = 1$). On admet que le côté du polygone à $2n$ côtés vérifie $c_{2n} = \\sqrt{2 - \\sqrt{4 - c_n^2}}$. "
         "Calculer $c_{12}$, puis le demi-périmètre $6c_{12}$ du dodécagone (au millième). Que représente ce nombre ?",
         "$c_{12} = \\sqrt{2 - \\sqrt{3}} \\approx 0{,}518$ et $6c_{12} \\approx 3{,}106$ : une valeur approchée par défaut de $\\pi$.",
         "Le demi-périmètre d'un polygone inscrit est un peu plus petit que le demi-périmètre du cercle, $\\pi$.",
         S("$c_{12} = \\sqrt{2 - \\sqrt{4 - 1}} = \\sqrt{2 - \\sqrt{3}} \\approx 0{,}5176$.", "Demi-périmètre : $\\dfrac{12 \\times c_{12}}{2} = 6c_{12} \\approx 3{,}106$.",
           "Le polygone est inscrit dans le cercle de périmètre $2\\pi$ : son demi-périmètre approche $\\pi$ par défaut."),
         checks=("3{,}106",), verify=_chk(lambda: f"{_archimede(1):.3f}" == "3.106")),
    _new(66107, N1, 4,
         "Programmer la méthode d'Archimède : " + code("from math import sqrt") + " " + code("c, n = 1, 6") + " "
         + code("for k in range(4): c, n = sqrt(2 - sqrt(4 - c*c)), 2*n") + " " + code("print(n, n*c/2)")
         + ". Quel couple affiche ce programme (demi-périmètre au dix-millième) ? Combien de décimales de $\\pi$ sont exactes ?",
         "Il affiche $96$ et environ $3{,}1410$ : le polygone à $96$ côtés donne $\\pi \\approx 3{,}141$, avec $2$ décimales exactes ($\\pi \\approx 3{,}1416$).",
         "Chaque passage dans la boucle double le nombre de côtés : $6 \\to 12 \\to 24 \\to 48 \\to 96$.",
         S("Quatre doublements : $n = 6 \\times 2^4 = 96$.", "Le demi-périmètre vaut environ $3{,}1410$.",
           "C'est le polygone d'Archimède (IIIe siècle av. J.-C.) ; $\\pi \\approx 3{,}14159$ : $3{,}14$ est exact, la décimale suivante ne l'est pas encore."),
         checks=("3{,}1410",), verify=_chk(lambda: f"{_archimede(4):.4f}" == "3.1410")),
    _new(66108, N1, 2,
         "Placer sur le cercle trigonométrique les points images de $\\dfrac{\\pi}{2}$, $\\pi$, $-\\dfrac{\\pi}{2}$ et $\\dfrac{3\\pi}{2}$. Que remarque-t-on ?",
         "$\\dfrac{\\pi}{2}$ donne $(0 ; 1)$, $\\pi$ donne $(-1 ; 0)$, $-\\dfrac{\\pi}{2}$ et $\\dfrac{3\\pi}{2}$ donnent le même point $(0 ; -1)$.",
         "Deux réels qui diffèrent de $2\\pi$ ont le même point image.",
         S("Un quart de tour ($\\dfrac{\\pi}{2}$) mène en haut ; un demi-tour ($\\pi$) à gauche.", "$-\\dfrac{\\pi}{2}$ : un quart de tour dans le sens indirect, en bas.",
           "$\\dfrac{3\\pi}{2} = -\\dfrac{\\pi}{2} + 2\\pi$ : même point $(0 ; -1)$."),
         checks=("(0 ; -1)",)),

    # N2 — coordonnées, valeurs remarquables, triangle rectangle, cos² + sin² = 1
    _new(66201, N2, 1,
         "Donner les coordonnées du point image de $\\dfrac{\\pi}{4}$ sur le cercle trigonométrique.",
         "$\\left(\\dfrac{\\sqrt{2}}{2} ; \\dfrac{\\sqrt{2}}{2}\\right)$.",
         "Les coordonnées sont $(\\cos x ; \\sin x)$.",
         S("Le point image de $x$ a pour coordonnées $(\\cos x ; \\sin x)$.", "$\\cos\\left(\\dfrac{\\pi}{4}\\right) = \\sin\\left(\\dfrac{\\pi}{4}\\right) = \\dfrac{\\sqrt{2}}{2}$."),
         checks=("\\dfrac{\\sqrt{2}}{2}",)),
    _new(66202, N2, 2,
         "Démontrer que $\\cos\\left(\\dfrac{\\pi}{4}\\right) = \\dfrac{\\sqrt{2}}{2}$ en utilisant un carré de côté $1$ et sa diagonale.",
         "La diagonale mesure $\\sqrt{2}$ et forme un angle de $\\dfrac{\\pi}{4}$ avec un côté : $\\cos\\left(\\dfrac{\\pi}{4}\\right) = \\dfrac{1}{\\sqrt{2}} = \\dfrac{\\sqrt{2}}{2}$.",
         "Pythagore dans le triangle rectangle isocèle formé par deux côtés et la diagonale.",
         S("La diagonale $d$ vérifie $d^2 = 1^2 + 1^2 = 2$, donc $d = \\sqrt{2}$.", "Le triangle est rectangle isocèle : ses angles aigus mesurent $45° = \\dfrac{\\pi}{4}$.",
           "$\\cos\\left(\\dfrac{\\pi}{4}\\right) = \\dfrac{\\text{adjacent}}{\\text{hypoténuse}} = \\dfrac{1}{\\sqrt{2}} = \\dfrac{\\sqrt{2}}{2}$."),
         checks=("\\dfrac{\\sqrt{2}}{2}",)),
    _new(66203, N2, 3,
         "Démontrer que $\\cos\\left(\\dfrac{\\pi}{3}\\right) = \\dfrac{1}{2}$ et $\\sin\\left(\\dfrac{\\pi}{3}\\right) = \\dfrac{\\sqrt{3}}{2}$ en utilisant un triangle équilatéral de côté $1$.",
         "La hauteur coupe la base en son milieu : $\\cos\\left(\\dfrac{\\pi}{3}\\right) = \\dfrac{1}{2}$ ; par Pythagore, la hauteur vaut $\\dfrac{\\sqrt{3}}{2}$, d'où $\\sin\\left(\\dfrac{\\pi}{3}\\right) = \\dfrac{\\sqrt{3}}{2}$.",
         "Trace une hauteur : elle est aussi médiane.",
         S("Les angles d'un triangle équilatéral mesurent $60° = \\dfrac{\\pi}{3}$.", "La hauteur issue d'un sommet coupe le côté opposé en son milieu : côté adjacent $\\dfrac{1}{2}$, hypoténuse $1$.",
           "$\\cos\\left(\\dfrac{\\pi}{3}\\right) = \\dfrac{1}{2}$ ; hauteur $h$ : $h^2 = 1 - \\dfrac{1}{4} = \\dfrac{3}{4}$, $h = \\dfrac{\\sqrt{3}}{2}$, et $\\sin\\left(\\dfrac{\\pi}{3}\\right) = \\dfrac{\\sqrt{3}}{2}$."),
         checks=("\\dfrac{1}{2}",)),
    _new(66204, N2, 2,
         "Soit $x \\in \\left]0 ; \\dfrac{\\pi}{2}\\right[$ tel que $\\cos(x) = \\dfrac{3}{5}$. Calculer $\\sin(x)$.",
         "$\\sin(x) = \\dfrac{4}{5}$.",
         "$\\cos^2 x + \\sin^2 x = 1$, puis le signe.",
         S("$\\sin^2 x = 1 - \\dfrac{9}{25} = \\dfrac{16}{25}$.", "Sur $\\left]0 ; \\dfrac{\\pi}{2}\\right[$, $\\sin x > 0$ : $\\sin(x) = \\dfrac{4}{5}$."),
         checks=("\\dfrac{4}{5}",), verify=_chk(lambda: sp.sqrt(1 - sp.Rational(9, 25)) == sp.Rational(4, 5))),
    _new(66205, N2, 3,
         "Soit $x \\in \\left]-\\pi ; -\\dfrac{\\pi}{2}\\right[$ tel que $\\sin(x) = -\\dfrac{5}{13}$. Calculer $\\cos(x)$.",
         "$\\cos(x) = -\\dfrac{12}{13}$.",
         "Dans quel quadrant est le point image ? Quel est le signe de l'abscisse ?",
         S("$\\cos^2 x = 1 - \\dfrac{25}{169} = \\dfrac{144}{169}$.", "$x \\in \\left]-\\pi ; -\\dfrac{\\pi}{2}\\right[$ : point dans le quart inférieur gauche, abscisse négative.",
           "$\\cos(x) = -\\dfrac{12}{13}$."),
         checks=("-\\dfrac{12}{13}",), verify=_chk(lambda: sp.sqrt(1 - sp.Rational(25, 169)) == sp.Rational(12, 13))),
    _new(66206, N2, 2,
         "Dans un triangle $ABC$ rectangle en $A$, on a $AB = 4$, $AC = 3$ et $BC = 5$. Calculer $\\cos(\\widehat{B})$ et $\\sin(\\widehat{B})$, puis vérifier que $\\cos^2(\\widehat{B}) + \\sin^2(\\widehat{B}) = 1$.",
         "$\\cos(\\widehat{B}) = \\dfrac{4}{5}$, $\\sin(\\widehat{B}) = \\dfrac{3}{5}$ et $\\dfrac{16}{25} + \\dfrac{9}{25} = 1$.",
         "Côté adjacent à $\\widehat{B}$ : $AB$ ; côté opposé : $AC$.",
         S("$\\cos(\\widehat{B}) = \\dfrac{AB}{BC} = \\dfrac{4}{5}$ et $\\sin(\\widehat{B}) = \\dfrac{AC}{BC} = \\dfrac{3}{5}$.",
           "$\\dfrac{16}{25} + \\dfrac{9}{25} = 1$ : c'est le théorème de Pythagore divisé par $BC^2$."),
         checks=("\\dfrac{4}{5}",), verify=_chk(lambda: sp.Rational(16, 25) + sp.Rational(9, 25) == 1)),
    _new(66207, N2, 1,
         "Peut-il exister un réel $x$ tel que $\\cos(x) = 1{,}2$ ? Justifier.",
         "Non : pour tout réel $x$, $-1 \\leqslant \\cos(x) \\leqslant 1$.",
         "Le cosinus est l'abscisse d'un point du cercle de rayon $1$.",
         S("Le point image est sur le cercle de rayon $1$ : son abscisse est comprise entre $-1$ et $1$.", "$1{,}2 > 1$ : impossible."),
         checks=("Non",)),
    _new(66208, N2, 2,
         "Calculer la valeur exacte de $A = \\cos^2\\left(\\dfrac{\\pi}{6}\\right) + \\cos\\left(\\dfrac{\\pi}{3}\\right) - \\sin\\left(\\dfrac{\\pi}{2}\\right)$.",
         "$A = \\dfrac{1}{4}$.",
         "Remplace chaque terme par sa valeur remarquable.",
         S("$\\cos^2\\left(\\dfrac{\\pi}{6}\\right) = \\left(\\dfrac{\\sqrt{3}}{2}\\right)^2 = \\dfrac{3}{4}$.", "$A = \\dfrac{3}{4} + \\dfrac{1}{2} - 1 = \\dfrac{1}{4}$."),
         checks=("\\dfrac{1}{4}",), verify=_chk(lambda: sp.cos(sp.pi / 6) ** 2 + sp.cos(sp.pi / 3) - sp.sin(sp.pi / 2) == sp.Rational(1, 4))),
    _new(66209, N2, 3,
         "Une échelle de $5$ m est appuyée contre un mur ; elle forme avec le sol un angle de $\\dfrac{\\pi}{3}$. À quelle hauteur touche-t-elle le mur ? À quelle distance du mur est son pied ?",
         "Hauteur $\\dfrac{5\\sqrt{3}}{2} \\approx 4{,}33$ m ; distance au mur $2{,}5$ m.",
         "Hauteur : côté opposé à l'angle ; distance : côté adjacent.",
         S("Hauteur : $5\\sin\\left(\\dfrac{\\pi}{3}\\right) = \\dfrac{5\\sqrt{3}}{2} \\approx 4{,}33$ m.", "Distance : $5\\cos\\left(\\dfrac{\\pi}{3}\\right) = \\dfrac{5}{2} = 2{,}5$ m."),
         checks=("4{,}33",), verify=_chk(lambda: f"{5 * math.sqrt(3) / 2:.2f}" == "4.33")),

    # N3 — angles associés, lecture du cercle
    _new(66301, N3, 1,
         "Sans calculatrice, donner $\\cos\\left(\\dfrac{2\\pi}{3}\\right)$ et $\\sin\\left(\\dfrac{2\\pi}{3}\\right)$.",
         "$\\cos\\left(\\dfrac{2\\pi}{3}\\right) = -\\dfrac{1}{2}$ et $\\sin\\left(\\dfrac{2\\pi}{3}\\right) = \\dfrac{\\sqrt{3}}{2}$.",
         "$\\dfrac{2\\pi}{3} = \\pi - \\dfrac{\\pi}{3}$ : symétrie par rapport à l'axe des ordonnées.",
         S("Les points images de $\\dfrac{\\pi}{3}$ et $\\pi - \\dfrac{\\pi}{3}$ sont symétriques par rapport à l'axe des ordonnées.",
           "Même ordonnée, abscisses opposées : $\\cos\\left(\\dfrac{2\\pi}{3}\\right) = -\\dfrac{1}{2}$ et $\\sin\\left(\\dfrac{2\\pi}{3}\\right) = \\dfrac{\\sqrt{3}}{2}$.")),
    _new(66302, N3, 1,
         "Sans calculatrice, donner $\\cos\\left(-\\dfrac{\\pi}{4}\\right)$ et $\\sin\\left(-\\dfrac{\\pi}{4}\\right)$.",
         "$\\cos\\left(-\\dfrac{\\pi}{4}\\right) = \\dfrac{\\sqrt{2}}{2}$ et $\\sin\\left(-\\dfrac{\\pi}{4}\\right) = -\\dfrac{\\sqrt{2}}{2}$.",
         "$x$ et $-x$ : symétrie par rapport à l'axe des abscisses.",
         S("Les points images de $\\dfrac{\\pi}{4}$ et $-\\dfrac{\\pi}{4}$ sont symétriques par rapport à l'axe des abscisses.",
           "Même abscisse, ordonnées opposées : $\\cos\\left(-\\dfrac{\\pi}{4}\\right) = \\dfrac{\\sqrt{2}}{2}$, $\\sin\\left(-\\dfrac{\\pi}{4}\\right) = -\\dfrac{\\sqrt{2}}{2}$.")),
    _new(66303, N3, 2,
         "Sans calculatrice, donner $\\cos\\left(\\dfrac{7\\pi}{6}\\right)$ et $\\sin\\left(\\dfrac{7\\pi}{6}\\right)$.",
         "$\\cos\\left(\\dfrac{7\\pi}{6}\\right) = -\\dfrac{\\sqrt{3}}{2}$ et $\\sin\\left(\\dfrac{7\\pi}{6}\\right) = -\\dfrac{1}{2}$.",
         "$\\dfrac{7\\pi}{6} = \\pi + \\dfrac{\\pi}{6}$ : point diamétralement opposé.",
         S("$\\dfrac{7\\pi}{6} = \\pi + \\dfrac{\\pi}{6}$ : les points images sont symétriques par rapport à l'origine.",
           "Coordonnées opposées : $\\cos\\left(\\dfrac{7\\pi}{6}\\right) = -\\dfrac{\\sqrt{3}}{2}$, $\\sin\\left(\\dfrac{7\\pi}{6}\\right) = -\\dfrac{1}{2}$.")),
    _new(66304, N3, 2,
         "Montrer, à l'aide du cercle, que pour tout réel $x$ : $\\cos\\left(\\dfrac{\\pi}{2} - x\\right) = \\sin(x)$ et $\\sin\\left(\\dfrac{\\pi}{2} - x\\right) = \\cos(x)$. Vérifier avec $x = \\dfrac{\\pi}{6}$.",
         "Les points images de $x$ et $\\dfrac{\\pi}{2} - x$ sont symétriques par rapport à la droite $y = x$, qui échange abscisse et ordonnée ; avec $x = \\dfrac{\\pi}{6}$ : $\\cos\\left(\\dfrac{\\pi}{3}\\right) = \\sin\\left(\\dfrac{\\pi}{6}\\right) = \\dfrac{1}{2}$.",
         "Quelle symétrie échange les coordonnées d'un point ?",
         S("La symétrie d'axe $y = x$ transforme $(a ; b)$ en $(b ; a)$ et le point image de $x$ en celui de $\\dfrac{\\pi}{2} - x$.",
           "Donc $\\cos\\left(\\dfrac{\\pi}{2} - x\\right) = \\sin(x)$ et $\\sin\\left(\\dfrac{\\pi}{2} - x\\right) = \\cos(x)$.",
           "Vérification : $\\cos\\left(\\dfrac{\\pi}{2} - \\dfrac{\\pi}{6}\\right) = \\cos\\left(\\dfrac{\\pi}{3}\\right) = \\dfrac{1}{2} = \\sin\\left(\\dfrac{\\pi}{6}\\right)$.")),
    _new(66305, N3, 2,
         "Résoudre dans $]-\\pi ; \\pi]$ l'équation $\\cos(x) = -\\dfrac{1}{2}$ par lecture du cercle.",
         "$\\mathcal{S} = \\left\\{-\\dfrac{2\\pi}{3} ; \\dfrac{2\\pi}{3}\\right\\}$.",
         "Trace la droite verticale d'abscisse $-\\dfrac{1}{2}$ : elle coupe le cercle en deux points.",
         S("$\\cos\\left(\\dfrac{2\\pi}{3}\\right) = -\\dfrac{1}{2}$.", "La droite $x = -\\dfrac{1}{2}$ coupe le cercle en deux points symétriques par rapport à l'axe des abscisses.",
           "Ils correspondent à $\\dfrac{2\\pi}{3}$ et $-\\dfrac{2\\pi}{3}$, tous deux dans $]-\\pi ; \\pi]$.")),
    _new(66306, N3, 3,
         "Résoudre dans $]-\\pi ; \\pi]$ l'équation $\\sin(x) = -\\dfrac{\\sqrt{3}}{2}$ par lecture du cercle.",
         "$\\mathcal{S} = \\left\\{-\\dfrac{2\\pi}{3} ; -\\dfrac{\\pi}{3}\\right\\}$.",
         "Trace la droite horizontale d'ordonnée $-\\dfrac{\\sqrt{3}}{2}$.",
         S("$\\sin\\left(-\\dfrac{\\pi}{3}\\right) = -\\dfrac{\\sqrt{3}}{2}$.", "La droite $y = -\\dfrac{\\sqrt{3}}{2}$ coupe le cercle en deux points symétriques par rapport à l'axe des ordonnées.",
           "Le second correspond à $-\\pi + \\dfrac{\\pi}{3} = -\\dfrac{2\\pi}{3}$."),
         ),
    _new(66307, N3, 3,
         "Simplifier, pour tout réel $x$ : $A = \\cos(\\pi - x) + \\cos(\\pi + x) + 2\\cos(-x)$.",
         "$A = 0$.",
         "Écris chaque terme en fonction de $\\cos(x)$.",
         S("$\\cos(\\pi - x) = -\\cos(x)$ (symétrie d'axe des ordonnées).", "$\\cos(\\pi + x) = -\\cos(x)$ (symétrie de centre $O$) et $\\cos(-x) = \\cos(x)$.",
           "$A = -\\cos(x) - \\cos(x) + 2\\cos(x) = 0$."),
         checks=("A = 0",), verify=_chk(lambda: sp.simplify(sp.cos(sp.pi - sp.Symbol("x")) + sp.cos(sp.pi + sp.Symbol("x")) + 2 * sp.cos(-sp.Symbol("x"))) == 0)),
    _new(66308, N3, 4,
         "Sans calculatrice, calculer $B = \\sin\\left(\\dfrac{\\pi}{7}\\right) + \\sin\\left(\\dfrac{6\\pi}{7}\\right) + \\sin\\left(\\dfrac{8\\pi}{7}\\right) + \\sin\\left(\\dfrac{13\\pi}{7}\\right)$.",
         "$B = 0$.",
         "Regroupe les angles par symétries : $\\dfrac{6\\pi}{7} = \\pi - \\dfrac{\\pi}{7}$, $\\dfrac{8\\pi}{7} = \\pi + \\dfrac{\\pi}{7}$, $\\dfrac{13\\pi}{7} = 2\\pi - \\dfrac{\\pi}{7}$.",
         S("$\\sin\\left(\\dfrac{6\\pi}{7}\\right) = \\sin\\left(\\dfrac{\\pi}{7}\\right)$ ; $\\sin\\left(\\dfrac{8\\pi}{7}\\right) = -\\sin\\left(\\dfrac{\\pi}{7}\\right)$.",
           "$\\dfrac{13\\pi}{7}$ a le même point image que $-\\dfrac{\\pi}{7}$ : $\\sin\\left(\\dfrac{13\\pi}{7}\\right) = -\\sin\\left(\\dfrac{\\pi}{7}\\right)$.",
           "$B = s + s - s - s = 0$ avec $s = \\sin\\left(\\dfrac{\\pi}{7}\\right)$."),
         checks=("B = 0",), verify=_chk(lambda: abs(sum(math.sin(k * math.pi / 7) for k in (1, 6, 8, 13))) < 1e-12)),
    _new(66309, N3, 2,
         "Une grande roue de rayon $1$ (unité : $10$ m) tourne dans le sens direct ; une nacelle part du point $A(1 ; 0)$. Où est-elle après avoir tourné de $\\dfrac{3\\pi}{4}$ ? Donner ses coordonnées exactes.",
         "Au point $\\left(-\\dfrac{\\sqrt{2}}{2} ; \\dfrac{\\sqrt{2}}{2}\\right)$.",
         "$\\dfrac{3\\pi}{4} = \\pi - \\dfrac{\\pi}{4}$.",
         S("Les coordonnées sont $\\left(\\cos\\left(\\dfrac{3\\pi}{4}\\right) ; \\sin\\left(\\dfrac{3\\pi}{4}\\right)\\right)$.",
           "Symétrique du point image de $\\dfrac{\\pi}{4}$ par rapport à l'axe des ordonnées : $\\cos\\left(\\dfrac{3\\pi}{4}\\right) = -\\dfrac{\\sqrt{2}}{2}$, $\\sin\\left(\\dfrac{3\\pi}{4}\\right) = \\dfrac{\\sqrt{2}}{2}$."),
         checks=("-\\dfrac{\\sqrt{2}}{2}",)),
]

EXERCISES = HIST + NOUVEAUX

QUIZ = {
    "reperage-sur-le-cercle-trigonometrique": (1239, 66101, 66105),
    "coordonnees-d-un-point-du-cercle-trigonometrique": (1298, 1299, 66201),
    "angles-associes-et-lecture-du-cercle": (1357, 66301, 66302),
}
