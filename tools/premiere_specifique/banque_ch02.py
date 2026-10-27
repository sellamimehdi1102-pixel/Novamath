"""Chapitre 2 — Fonctions numériques : banque curée (manuel « Première ES/L », Ch. 2).

Créée lors de l'adaptation du 2026-10-26 (voir PREMIERE_SPECIFIQUE_SUIVI.md).
« Rappels sur les fonctions » : exercices 73301, 73303 et 73304 repris de
l'ancienne notion « Fonctions et représentations » (identifiants conservés) ;
73302 (équation de droite, hors manuel) est mis hors périmètre.
Nouveaux exercices : bloc 82 000, valeurs recalculées (`verify`).
"""
import math
from dataclasses import replace
from fractions import Fraction as F

from premiere_specifique.banque_commun import E, S
from premiere_specifique.reserve.banque_ch13 import EXERCISES as _AUTOMATISMES, N3 as _N_ANCIEN

CHAPTER_NUMBER = 2
N1 = "Rappels sur les fonctions"
N2 = "Fonction racine carrée"
N3 = "Fonction cube"
NOTIONS = (N1, N2, N3)
NOTION_IDS = ("fonctions-et-representations", "fonction-racine-carree", "fonction-cube")


def _ok(cond):
    return lambda: None if cond else "valeur fausse"


_REPRIS = [replace(e, notion=N1) for e in _AUTOMATISMES if e.notion == _N_ANCIEN]
EXERCICES_HORS_PERIMETRE = [e for e in _REPRIS if e.id == 73302]
EXERCISES = [e for e in _REPRIS if e.id != 73302] + [
    # Rappels sur les fonctions.
    E(82101, N1, 1,
      "La fonction $f$ est définie sur $[-3 ; 3]$ par $f(x) = x^2 - 2x - 1$. Le point $A(3 ; 2)$ est-il sur sa courbe ? Et le point $B(4 ; 7)$ ?",
      "$A$ est sur la courbe ; $B$ n'y est pas, car $4$ n'appartient pas à $[-3 ; 3]$.",
      "Vérifie que l'abscisse est dans l'ensemble de définition, puis calcule son image.",
      S("$3 \\in [-3 ; 3]$ et $f(3) = 9 - 6 - 1 = 2$ : $A$ est sur la courbe.", "$4 \\notin [-3 ; 3]$ : $B$ n'est pas sur la courbe, même si $4^2 - 2 \\times 4 - 1 = 7$."),
      checks=("$A$ est sur la courbe",), verify=_ok(3 ** 2 - 2 * 3 - 1 == 2)),
    E(82102, N1, 2,
      "La fonction $f$ est strictement décroissante sur $[0 ; 5]$. Comparer $f(1{,}3)$ et $f(2{,}7)$, puis $f(0)$ et $f(5)$.",
      "$f(1{,}3) > f(2{,}7)$ et $f(0) > f(5)$.",
      "Une fonction strictement décroissante renverse l'ordre.",
      S("$1{,}3 < 2{,}7$, deux nombres de $[0 ; 5]$ : $f(1{,}3) > f(2{,}7)$.", "$0 < 5$ : $f(0) > f(5)$."),
      checks=("f(1{,}3) > f(2{,}7)",)),
    E(82103, N1, 3,
      "Démontrer que la fonction $g$ définie sur $\\mathbb{R}$ par $g(x) = -2x + 3$ est strictement décroissante.",
      "Pour tous réels $a < b$, $g(a) - g(b) = 2(b - a) > 0$, donc $g(a) > g(b)$ : $g$ est strictement décroissante.",
      "Étudie le signe de $g(a) - g(b)$ pour $a < b$.",
      S("Soient $a < b$ deux réels.", "$g(a) - g(b) = (-2a + 3) - (-2b + 3) = 2b - 2a = 2(b - a)$.", "$b - a > 0$, donc $g(a) > g(b)$ : $g$ renverse l'ordre."),
      checks=("2(b - a)",)),
    E(82104, N1, 4,
      "Démontrer que la fonction carré est strictement décroissante sur $]-\\infty ; 0]$.",
      "Pour $a < b \\leqslant 0$ : $a^2 - b^2 = (a - b)(a + b) > 0$ (produit de deux nombres strictement négatifs), donc $a^2 > b^2$.",
      "Factorise $a^2 - b^2$ et étudie le signe de chaque facteur.",
      S("Soient $a < b \\leqslant 0$.", "$a^2 - b^2 = (a - b)(a + b)$.", "$a - b < 0$ ; $a + b < 0$ car $a < 0$ et $b \\leqslant 0$.",
        "Le produit est strictement positif : $a^2 > b^2$, la fonction carré est strictement décroissante sur $]-\\infty ; 0]$."),
      checks=("(a - b)(a + b)",)),
    # Fonction racine carrée.
    E(82201, N2, 1,
      "Sans calculatrice, comparer $\\sqrt{7}$ et $\\sqrt{11}$, puis calculer $\\sqrt{0{,}49}$.",
      "$\\sqrt{7} < \\sqrt{11}$ et $\\sqrt{0{,}49} = 0{,}7$.",
      "La fonction racine carrée est strictement croissante sur $[0 ; +\\infty[$.",
      S("$7 < 11$ et la racine carrée est strictement croissante : $\\sqrt{7} < \\sqrt{11}$.", "$0{,}7 \\geqslant 0$ et $0{,}7^2 = 0{,}49$ : $\\sqrt{0{,}49} = 0{,}7$."),
      checks=("\\sqrt{0{,}49} = 0{,}7",), verify=_ok(F(7, 10) ** 2 == F(49, 100))),
    E(82202, N2, 1,
      "Résoudre dans $[0 ; +\\infty[$ les équations $\\sqrt{x} = 3$ et $\\sqrt{x} = -2$.",
      "$\\sqrt{x} = 3 \\iff x = 9$ ; l'équation $\\sqrt{x} = -2$ n'a pas de solution.",
      "Une racine carrée est toujours positive ou nulle.",
      S("$3 \\geqslant 0$ : $\\sqrt{x} = 3 \\iff x = 3^2 = 9$.", "$-2 < 0$ et une racine carrée est positive : aucune solution."),
      checks=("x = 9",), verify=_ok(math.isqrt(9) == 3)),
    E(82203, N2, 2,
      "Résoudre l'inéquation $\\sqrt{x} \\leqslant 2$.",
      "$\\mathcal{S} = [0 ; 4]$.",
      "Écris $2$ comme une racine carrée et utilise le sens de variation.",
      S("$\\sqrt{x}$ existe pour $x \\geqslant 0$.", "$2 = \\sqrt{4}$ ; la fonction est strictement croissante : $\\sqrt{x} \\leqslant \\sqrt{4} \\iff x \\leqslant 4$.",
        "$\\mathcal{S} = [0 ; 4]$."),
      checks=("[0 ; 4]",)),
    E(82204, N2, 2,
      "Sachant que $2 \\leqslant x \\leqslant 9$, donner un encadrement de $\\sqrt{x}$.",
      "$\\sqrt{2} \\leqslant \\sqrt{x} \\leqslant 3$.",
      "Une fonction croissante conserve les inégalités.",
      S("La fonction racine carrée est croissante sur $[0 ; +\\infty[$.", "$\\sqrt{2} \\leqslant \\sqrt{x} \\leqslant \\sqrt{9}$, soit $\\sqrt{2} \\leqslant \\sqrt{x} \\leqslant 3$."),
      checks=("\\leqslant 3",)),
    E(82205, N2, 3,
      "Ranger dans l'ordre croissant $0{,}36$, $0{,}36^2$ et $\\sqrt{0{,}36}$. Que peut-on conjecturer pour un nombre $x$ compris entre $0$ et $1$ ?",
      "$0{,}1296 < 0{,}36 < 0{,}6$ : pour $0 < x < 1$, on conjecture $x^2 < x < \\sqrt{x}$.",
      "Calcule $0{,}36^2$ et $\\sqrt{0{,}36}$.",
      S("$0{,}36^2 = 0{,}1296$ et $\\sqrt{0{,}36} = 0{,}6$.", "Donc $0{,}36^2 < 0{,}36 < \\sqrt{0{,}36}$.",
        "Sur la figure du cours, entre $0$ et $1$, la parabole est sous la droite $y = x$, elle-même sous la courbe de $\\sqrt{x}$."),
      checks=("0{,}1296",), verify=_ok(F(36, 100) ** 2 == F(1296, 10000) and F(6, 10) ** 2 == F(36, 100))),
    E(82206, N2, 4,
      "Démontrer que la fonction racine carrée est strictement croissante sur $[0 ; +\\infty[$.",
      "Pour $0 \\leqslant a < b$ : $\\sqrt{b} - \\sqrt{a} = \\dfrac{b - a}{\\sqrt{b} + \\sqrt{a}} > 0$, donc $\\sqrt{a} < \\sqrt{b}$.",
      "Multiplie et divise $\\sqrt{b} - \\sqrt{a}$ par $\\sqrt{b} + \\sqrt{a}$.",
      S("Soient $0 \\leqslant a < b$ ; $\\sqrt{b} > 0$, donc $\\sqrt{b} + \\sqrt{a} > 0$.",
        "$\\sqrt{b} - \\sqrt{a} = \\dfrac{(\\sqrt{b} - \\sqrt{a})(\\sqrt{b} + \\sqrt{a})}{\\sqrt{b} + \\sqrt{a}} = \\dfrac{b - a}{\\sqrt{b} + \\sqrt{a}}$.",
        "$b - a > 0$ : le quotient est strictement positif, donc $\\sqrt{a} < \\sqrt{b}$."),
      checks=("\\dfrac{b - a}{\\sqrt{b} + \\sqrt{a}}",)),
    # Fonction cube.
    E(82301, N3, 1,
      "Calculer $(-2)^3$, $0{,}5^3$ et $(-0{,}1)^3$.",
      "$(-2)^3 = -8$ ; $0{,}5^3 = 0{,}125$ ; $(-0{,}1)^3 = -0{,}001$.",
      "Le cube d'un nombre négatif est négatif.",
      S("$(-2)^3 = (-2) \\times (-2) \\times (-2) = -8$.", "$0{,}5^3 = 0{,}125$ et $(-0{,}1)^3 = -0{,}001$."),
      checks=("-8", "0{,}125", "-0{,}001"), verify=_ok(F(-2) ** 3 == -8 and F(1, 2) ** 3 == F(125, 1000) and F(-1, 10) ** 3 == F(-1, 1000))),
    E(82302, N3, 1,
      "Sans calcul, comparer $(-1{,}5)^3$ et $(-1{,}4)^3$.",
      "$(-1{,}5)^3 < (-1{,}4)^3$.",
      "La fonction cube est strictement croissante sur $\\mathbb{R}$.",
      S("$-1{,}5 < -1{,}4$.", "La fonction cube conserve l'ordre : $(-1{,}5)^3 < (-1{,}4)^3$."),
      checks=("(-1{,}5)^3 < (-1{,}4)^3",), verify=_ok(F(-15, 10) ** 3 < F(-14, 10) ** 3)),
    E(82303, N3, 2,
      "Résoudre dans $\\mathbb{R}$ l'équation $x^3 = -8$.",
      "$\\mathcal{S} = \\{-2\\}$.",
      "Écris $-8$ comme un cube.",
      S("$-8 = (-2)^3$.", "La fonction cube est strictement croissante : l'équation a une unique solution, $x = -2$."),
      checks=("\\{-2\\}",), verify=_ok(F(-2) ** 3 == -8)),
    E(82304, N3, 2,
      "Résoudre dans $\\mathbb{R}$ l'inéquation $x^3 > 27$.",
      "$\\mathcal{S} = ]3 ; +\\infty[$.",
      "$27$ est le cube d'un entier.",
      S("$27 = 3^3$.", "La fonction cube est strictement croissante : $x^3 > 3^3 \\iff x > 3$."),
      checks=("]3 ; +\\infty[",), verify=_ok(3 ** 3 == 27)),
    E(82305, N3, 3,
      "Dresser le tableau de signes de $(x - 1)^3$ sur $\\mathbb{R}$, puis résoudre $(x - 1)^3 \\leqslant 0$.",
      "$(x - 1)^3 < 0$ pour $x < 1$, nul en $1$, $> 0$ pour $x > 1$ ; $\\mathcal{S} = ]-\\infty ; 1]$.",
      "Un cube a le même signe que le nombre qu'on élève au cube.",
      S("$(x - 1)^3$ a le signe de $x - 1$.", "$x - 1 < 0$ pour $x < 1$ et $x - 1 > 0$ pour $x > 1$.", "$(x - 1)^3 \\leqslant 0 \\iff x \\leqslant 1$."),
      checks=("]-\\infty ; 1]",)),
    E(82306, N3, 4,
      "Montrer que, pour tous réels $a$ et $b$, $b^3 - a^3 = (b - a)(a^2 + ab + b^2)$, puis en déduire que la fonction cube est strictement croissante sur $\\mathbb{R}$.",
      "En développant, $(b - a)(a^2 + ab + b^2) = b^3 - a^3$. Si $a < b$, $a^2 + ab + b^2 = \\left(a + \\dfrac{b}{2}\\right)^2 + \\dfrac{3b^2}{4} > 0$, donc $b^3 - a^3 > 0$.",
      "Pour le signe du second facteur, écris-le comme une somme de carrés.",
      S("$(b - a)(a^2 + ab + b^2) = a^2b + ab^2 + b^3 - a^3 - a^2b - ab^2 = b^3 - a^3$.",
        "$a^2 + ab + b^2 = \\left(a + \\dfrac{b}{2}\\right)^2 + \\dfrac{3b^2}{4}$, somme de deux carrés, nulle seulement si $a = b = 0$.",
        "Si $a < b$, alors $b - a > 0$ et $a^2 + ab + b^2 > 0$ : $b^3 - a^3 > 0$, donc $a^3 < b^3$."),
      checks=("b^3 - a^3",)),
]

QUIZ = {
    "fonctions-et-representations": (73301, 73303, 82101),
    "fonction-racine-carree": (82201, 82202, 82203),
    "fonction-cube": (82301, 82302, 82303),
}
