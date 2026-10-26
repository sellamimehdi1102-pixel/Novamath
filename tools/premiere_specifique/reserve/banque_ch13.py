"""Chapitre 13 (nouveau, programme 2026) — Automatismes : banque curée.

Les automatismes ne forment pas un chapitre d'enseignement : ce sont des
savoir-faire travaillés tout au long de l'année (questions flash, calcul
mental, épreuve anticipée). L'entraînement en grand nombre vient du
générateur webapp/exercise_generator/automatismes.py. Chaque résultat
numérique est recalculé exactement (`Fraction`) au chargement.

Nouveaux exercices : bloc 73 000.
"""
from fractions import Fraction as F

from premiere_specifique.banque_commun import E, S

CHAPTER_NUMBER = 13
N1 = "Évolutions et taux"
N2 = "Calcul numérique et algébrique"
N3 = "Fonctions et représentations"
N4 = "Statistiques et probabilités"
NOTIONS = (N1, N2, N3, N4)
NOTION_IDS = ("evolutions-et-taux", "calcul-numerique-et-algebrique", "fonctions-et-representations", "statistiques-et-probabilites")


def _chk(cond_fn):
    return lambda: None if cond_fn() else "valeur fausse"


def _f(x):
    return x * x - 3 * x


EXERCISES = [
    E(73101, N1, 1,
      "Un article coûte $80$ €. Son prix augmente de $15\\,\\%$. Quel est son nouveau prix ?",
      "$92$ €.",
      "Augmenter de $15\\,\\%$, c'est multiplier par $1{,}15$.",
      S("Coefficient multiplicateur : $1 + 0{,}15 = 1{,}15$.", "$80 \\times 1{,}15 = 92$."),
      checks=("$92$",), verify=_chk(lambda: 80 * F(115, 100) == 92)),
    E(73102, N1, 1,
      "Le nombre d'abonnés d'un club passe de $250$ à $200$. Quel est le taux d'évolution ?",
      "Le taux d'évolution est $-20\\,\\%$ (baisse de $20\\,\\%$).",
      "Taux $= \\dfrac{V_A - V_D}{V_D}$.",
      S("$\\dfrac{200 - 250}{250} = \\dfrac{-50}{250} = -0{,}2$.", "Le taux est $-20\\,\\%$."),
      checks=("$-20\\,\\%$",), verify=_chk(lambda: F(200 - 250, 250) == F(-1, 5))),
    E(73103, N1, 2,
      "Un prix augmente de $10\\,\\%$ puis baisse de $10\\,\\%$. Quel est le taux d'évolution global ?",
      "Le taux global est $-1\\,\\%$ : le prix final est inférieur au prix initial.",
      "Les coefficients multiplicateurs se multiplient ; les taux ne s'additionnent pas.",
      S("Coefficients : $1{,}1$ puis $0{,}9$.", "$1{,}1 \\times 0{,}9 = 0{,}99$.", "$0{,}99 = 1 - 0{,}01$ : baisse de $1\\,\\%$."),
      checks=("$-1\\,\\%$",), verify=_chk(lambda: F(11, 10) * F(9, 10) == F(99, 100))),
    E(73104, N1, 3,
      "Après une hausse de $25\\,\\%$, quelle baisse en pourcentage permet de revenir à la valeur initiale ?",
      "Une baisse de $20\\,\\%$.",
      "Le coefficient réciproque est l'inverse du coefficient multiplicateur.",
      S("Coefficient de la hausse : $1{,}25$.", "Coefficient réciproque : $\\dfrac{1}{1{,}25} = 0{,}8$.", "$0{,}8 = 1 - 0{,}2$ : baisse de $20\\,\\%$, et non de $25\\,\\%$."),
      checks=("$20\\,\\%$",), verify=_chk(lambda: 1 / F(5, 4) == F(4, 5))),

    E(73201, N2, 1,
      "Résoudre dans $\\mathbb{R}$ l'équation $(2x - 6)(x + 4) = 0$.",
      "Les solutions sont $3$ et $-4$.",
      "Un produit est nul si et seulement si l'un de ses facteurs est nul.",
      S("$2x - 6 = 0$ donne $x = 3$.", "$x + 4 = 0$ donne $x = -4$.", "$\\mathcal{S} = \\{-4 ; 3\\}$."),
      checks=("$3$", "$-4$"), verify=_chk(lambda: (2 * 3 - 6) * (3 + 4) == 0 and (2 * -4 - 6) * (-4 + 4) == 0)),
    E(73202, N2, 2,
      "Développer et réduire $(3x - 2)^2$.",
      "$(3x - 2)^2 = 9x^2 - 12x + 4$.",
      "Identité remarquable $(a - b)^2 = a^2 - 2ab + b^2$.",
      S("$a = 3x$ et $b = 2$.", "$(3x)^2 - 2 \\times 3x \\times 2 + 2^2 = 9x^2 - 12x + 4$."),
      checks=("9x^2 - 12x + 4",), verify=_chk(lambda: all((3 * x - 2) ** 2 == 9 * x * x - 12 * x + 4 for x in range(-3, 4)))),
    E(73203, N2, 2,
      "Factoriser $x^2 - 25$.",
      "$x^2 - 25 = (x - 5)(x + 5)$.",
      "Identité remarquable $a^2 - b^2 = (a - b)(a + b)$.",
      S("$25 = 5^2$.", "$x^2 - 5^2 = (x - 5)(x + 5)$."),
      checks=("(x - 5)(x + 5)",), verify=_chk(lambda: all(x * x - 25 == (x - 5) * (x + 5) for x in range(-3, 4)))),
    E(73204, N2, 3,
      "Étudier le signe de $-2x + 6$ selon les valeurs de $x$.",
      "$-2x + 6 > 0$ pour $x < 3$, $-2x + 6 = 0$ pour $x = 3$ et $-2x + 6 < 0$ pour $x > 3$.",
      "Une expression $ax + b$ avec $a < 0$ est positive puis négative.",
      S("$-2x + 6 = 0$ pour $x = 3$.", "Le coefficient de $x$ est $-2 < 0$ : l'expression est décroissante.", "Elle est donc positive avant $3$ et négative après."),
      checks=("$x < 3$",), verify=_chk(lambda: -2 * 0 + 6 > 0 and -2 * 4 + 6 < 0)),
    E(73205, N2, 1,
      "Calculer $\\dfrac{2}{3} + \\dfrac{5}{6}$ et donner le résultat sous forme irréductible.",
      "$\\dfrac{2}{3} + \\dfrac{5}{6} = \\dfrac{3}{2}$.",
      "On met les fractions au même dénominateur.",
      S("$\\dfrac{2}{3} = \\dfrac{4}{6}$.", "$\\dfrac{4}{6} + \\dfrac{5}{6} = \\dfrac{9}{6} = \\dfrac{3}{2}$."),
      checks=("\\dfrac{3}{2}",), verify=_chk(lambda: F(2, 3) + F(5, 6) == F(3, 2))),

    E(73301, N3, 1,
      "On considère la fonction $f$ définie sur $\\mathbb{R}$ par $f(x) = x^2 - 3x$. Calculer l'image de $-2$.",
      "$f(-2) = 10$.",
      "On remplace $x$ par $(-2)$, avec des parenthèses.",
      S("$f(-2) = (-2)^2 - 3 \\times (-2)$.", "$= 4 + 6 = 10$."),
      checks=("$f(-2) = 10$",), verify=_chk(lambda: _f(-2) == 10)),
    E(73302, N3, 2,
      "Déterminer l'équation réduite de la droite passant par $A(1 ; 3)$ et $B(3 ; 7)$.",
      "$y = 2x + 1$.",
      "Coefficient directeur $m = \\dfrac{y_B - y_A}{x_B - x_A}$.",
      S("$m = \\dfrac{7 - 3}{3 - 1} = 2$.", "$3 = 2 \\times 1 + p$ donne $p = 1$.", "Équation réduite : $y = 2x + 1$."),
      checks=("y = 2x + 1",), verify=_chk(lambda: 2 * 1 + 1 == 3 and 2 * 3 + 1 == 7)),
    E(73303, N3, 2,
      "Déterminer les antécédents de $4$ par la fonction carré.",
      "Les antécédents de $4$ sont $-2$ et $2$.",
      "On résout $x^2 = 4$.",
      S("$x^2 = 4$ équivaut à $x = 2$ ou $x = -2$.", "$4$ a deux antécédents : $-2$ et $2$."),
      checks=("$-2$", "$2$"), verify=_chk(lambda: (-2) ** 2 == 4 and 2 ** 2 == 4)),
    E(73304, N3, 3,
      "Une fonction $f$ définie sur $[-2 ; 4]$ est strictement croissante sur $[-2 ; 1]$, de $f(-2) = -3$ à $f(1) = 5$, puis strictement décroissante sur $[1 ; 4]$, jusqu'à $f(4) = 0$. Combien l'équation $f(x) = 2$ a-t-elle de solutions ? Et $f(x) = -1$ ?",
      "$f(x) = 2$ a $2$ solutions ; $f(x) = -1$ a $1$ solution.",
      "On lit le tableau de variations : sur chaque intervalle de monotonie, la valeur est atteinte au plus une fois.",
      S("Sur $[-2 ; 1]$, $f$ prend toutes les valeurs de $-3$ à $5$ une seule fois : $2$ et $-1$ sont atteints une fois.",
        "Sur $[1 ; 4]$, $f$ prend les valeurs de $5$ à $0$ : $2$ est atteint une fois, $-1$ jamais.",
        "Bilan : deux solutions pour $f(x) = 2$, une seule pour $f(x) = -1$."),
      checks=("$2$ solutions", "$1$ solution")),

    E(73401, N4, 1,
      "On considère la série $4$ ; $7$ ; $7$ ; $9$ ; $13$. Calculer la moyenne, la médiane et l'étendue.",
      "Moyenne $8$, médiane $7$, étendue $9$.",
      "La série est déjà rangée dans l'ordre croissant.",
      S("Moyenne : $\\dfrac{4 + 7 + 7 + 9 + 13}{5} = \\dfrac{40}{5} = 8$.", "Médiane : valeur centrale (3e sur 5) : $7$.", "Étendue : $13 - 4 = 9$."),
      checks=("Moyenne $8$", "médiane $7$", "étendue $9$"), verify=_chk(lambda: F(4 + 7 + 7 + 9 + 13, 5) == 8)),
    E(73402, N4, 2,
      "Un lycée compte $120$ élèves de Première : $70$ filles, dont $42$ externes, et $50$ garçons, dont $20$ externes. On choisit un élève au hasard. Quelle est la probabilité que ce soit une fille externe ? un élève externe ?",
      "$P(\\text{fille externe}) = 0{,}35$ et $P(\\text{externe}) = \\dfrac{31}{60}$.",
      "Un tableau croisé d'effectifs aide à lire les effectifs.",
      S("Filles externes : $42$, donc $\\dfrac{42}{120} = \\dfrac{7}{20} = 0{,}35$.", "Externes : $42 + 20 = 62$.", "$\\dfrac{62}{120} = \\dfrac{31}{60}$."),
      checks=("0{,}35", "\\dfrac{31}{60}"), verify=_chk(lambda: F(42, 120) == F(35, 100) and F(62, 120) == F(31, 60))),
    E(73403, N4, 1,
      "On lance un dé équilibré à six faces. Quelle est la probabilité d'obtenir un multiple de $3$ ?",
      "La probabilité est $\\dfrac{1}{3}$.",
      "Équiprobabilité : nombre d'issues favorables sur nombre d'issues.",
      S("Multiples de $3$ parmi $1$ à $6$ : $3$ et $6$.", "$\\dfrac{2}{6} = \\dfrac{1}{3}$."),
      checks=("\\dfrac{1}{3}",), verify=_chk(lambda: F(len([k for k in range(1, 7) if k % 3 == 0]), 6) == F(1, 3))),
    E(73404, N4, 3,
      "Dans un lycée, $40\\,\\%$ des élèves sont internes et $25\\,\\%$ des internes pratiquent un sport en club. Quelle proportion de l'ensemble des élèves est interne et pratique un sport en club ?",
      "$10\\,\\%$ des élèves.",
      "Une proportion d'une proportion : on multiplie.",
      S("Proportion des internes sportifs : $0{,}25 \\times 0{,}4$.", "$0{,}25 \\times 0{,}4 = 0{,}1$, soit $10\\,\\%$."),
      checks=("$10\\,\\%$",), verify=_chk(lambda: F(1, 4) * F(2, 5) == F(1, 10))),
]

QUIZ = {
    "evolutions-et-taux": (73101, 73102, 73103),
    "calcul-numerique-et-algebrique": (73201, 73202, 73205),
    "fonctions-et-representations": (73301, 73302, 73303),
    "statistiques-et-probabilites": (73401, 73402, 73403),
}
