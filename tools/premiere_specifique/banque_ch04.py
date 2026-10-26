"""Chapitre 4 — Statistiques : banque curée (manuel « Première ES/L », Ch. 4).

Créée lors de l'adaptation du 2026-10-26 (voir PREMIERE_SPECIFIQUE_SUIVI.md).
Exercice 73401 (moyenne, médiane, étendue) repris de l'ancienne notion
« Statistiques et probabilités » (identifiant conservé). Nouveaux exercices :
bloc 84 000 ; indicateurs recalculés exactement (`verify`, Fraction).
"""
import math
from dataclasses import replace
from fractions import Fraction as F

from premiere_specifique.banque_commun import E, S
from premiere_specifique.reserve.banque_ch13 import EXERCISES as _AUTOMATISMES

CHAPTER_NUMBER = 4
N1 = "Notation Σ et indicateurs de tendance centrale"
N2 = "Quartiles et diagramme en boîte"
N3 = "Variance, écart-type et dispersion"
NOTIONS = (N1, N2, N3)
NOTION_IDS = ("notation-sigma-et-tendance-centrale", "quartiles-et-diagramme-en-boite", "indicateurs-de-dispersion")


def _ok(cond):
    return lambda: None if cond else "valeur fausse"


def _serie(valeurs, effectifs):
    return [v for v, n in zip(valeurs, effectifs) for _ in range(n)]


def _q(data, frac):
    """Quartile au sens du manuel : x_i avec i le plus petit entier >= frac × N."""
    return sorted(data)[math.ceil(frac * len(data)) - 1]


def _moy(data):
    return F(sum(data), len(data))


def _var(data):
    m = _moy(data)
    return sum((F(x) - m) ** 2 for x in data) / len(data)


_NOTES = _serie((6, 8, 9, 10, 11, 12, 14, 15, 17), (1, 2, 3, 4, 3, 2, 2, 2, 1))
_PETITE = [3, 5, 5, 8, 9, 11, 12, 15]

EXERCISES = [replace(e, notion=N1) for e in _AUTOMATISMES if e.id == 73401] + [
    # Notation Σ et indicateurs de tendance centrale.
    E(84101, N1, 1,
      "Calculer $\\sum_{i=1}^{4} i^2$ et $\\sum_{i=1}^{5} (2i + 1)$.",
      "$\\sum_{i=1}^{4} i^2 = 30$ et $\\sum_{i=1}^{5} (2i + 1) = 35$.",
      "Remplace $i$ par chaque entier, puis additionne.",
      S("$\\sum_{i=1}^{4} i^2 = 1 + 4 + 9 + 16 = 30$.", "$\\sum_{i=1}^{5} (2i + 1) = 3 + 5 + 7 + 9 + 11 = 35$."),
      checks=("= 30", "= 35"), verify=_ok(sum(i * i for i in range(1, 5)) == 30 and sum(2 * i + 1 for i in range(1, 6)) == 35)),
    E(84102, N1, 1,
      "Une série prend les valeurs $1$, $2$, $3$ avec les fréquences $0{,}2$, $0{,}5$ et $0{,}3$. Calculer sa moyenne.",
      "La moyenne vaut $2{,}1$.",
      "Avec les fréquences : $\\overline{x} = \\sum f_i x_i$.",
      S("$\\overline{x} = 0{,}2 \\times 1 + 0{,}5 \\times 2 + 0{,}3 \\times 3$.", "$\\overline{x} = 0{,}2 + 1 + 0{,}9 = 2{,}1$."),
      checks=("2{,}1",), verify=_ok(F(2, 10) * 1 + F(5, 10) * 2 + F(3, 10) * 3 == F(21, 10))),
    E(84103, N1, 2,
      "Notes de $20$ élèves : $6$ (1), $8$ (2), $9$ (3), $10$ (4), $11$ (3), $12$ (2), $14$ (2), $15$ (2), $17$ (1). Calculer la moyenne et donner le mode.",
      "Moyenne $11{,}05$ ; mode $10$.",
      "Multiplie chaque note par son effectif, additionne, divise par $20$.",
      S("$\\sum n_i x_i = 6 + 16 + 27 + 40 + 33 + 24 + 28 + 30 + 17 = 221$.", "$\\overline{x} = \\dfrac{221}{20} = 11{,}05$.",
        "Le mode est la note de plus grand effectif : $10$ (effectif $4$)."),
      checks=("11{,}05", "mode $10$"), verify=_ok(_moy(_NOTES) == F(1105, 100))),
    E(84104, N1, 2,
      "Avec la série de $20$ notes de l'exercice précédent, déterminer la médiane à l'aide des effectifs cumulés croissants.",
      "La médiane vaut $10{,}5$.",
      "$N = 20$ est pair : moyenne des valeurs de rangs $10$ et $11$.",
      S("Effectifs cumulés : $1$ ; $3$ ; $6$ ; $10$ ; $13$ ; $15$ ; $17$ ; $19$ ; $20$.", "La $10^{e}$ valeur est $10$ et la $11^{e}$ est $11$.",
        "$Me = \\dfrac{10 + 11}{2} = 10{,}5$."),
      checks=("10{,}5",), verify=_ok(F(sorted(_NOTES)[9] + sorted(_NOTES)[10], 2) == F(21, 2))),
    E(84105, N1, 3,
      "Dans la série $4$ ; $7$ ; $7$ ; $9$ ; $13$, on remplace $13$ par $63$. Calculer la nouvelle moyenne et la nouvelle médiane. Que constate-t-on ?",
      "Moyenne $18$ (au lieu de $8$), médiane $7$ (inchangée) : la moyenne est sensible aux valeurs extrêmes, pas la médiane.",
      "La médiane ne dépend que de la valeur centrale.",
      S("Nouvelle moyenne : $\\dfrac{4 + 7 + 7 + 9 + 63}{5} = \\dfrac{90}{5} = 18$.", "La série rangée a toujours $7$ en $3^{e}$ position : la médiane reste $7$.",
        "Une valeur extrême modifie fortement la moyenne, pas la médiane."),
      checks=("$18$", "$7$"), verify=_ok(_moy([4, 7, 7, 9, 63]) == 18)),
    E(84106, N1, 4,
      "Démontrer que, pour une série de valeurs $x_i$ d'effectifs $n_i$ et d'effectif total $N$, la moyenne vérifie $\\overline{x} = \\sum f_i x_i$, où $f_i$ est la fréquence de $x_i$.",
      "$\\overline{x} = \\dfrac{\\sum n_i x_i}{N} = \\sum \\dfrac{n_i}{N} x_i = \\sum f_i x_i$.",
      "Divise chaque terme de la somme par $N$.",
      S("Par définition, $\\overline{x} = \\dfrac{\\sum_{i=1}^{p} n_i x_i}{N}$.", "Diviser une somme par $N$, c'est diviser chacun de ses termes : $\\overline{x} = \\sum_{i=1}^{p} \\dfrac{n_i}{N} x_i$.",
        "Or $\\dfrac{n_i}{N} = f_i$ : $\\overline{x} = \\sum_{i=1}^{p} f_i x_i$."),
      checks=("\\sum f_i x_i",)),
    # Quartiles et diagramme en boîte.
    E(84201, N2, 1,
      "Déterminer le premier quartile, la médiane et le troisième quartile de la série $3$ ; $5$ ; $5$ ; $8$ ; $9$ ; $11$ ; $12$ ; $15$.",
      "$Q_1 = 5$, $Me = 8{,}5$ et $Q_3 = 11$.",
      "$N = 8$ : calcule $\\dfrac{N}{4}$ et $\\dfrac{3N}{4}$.",
      S("$\\dfrac{8}{4} = 2$ : $Q_1 = x_2 = 5$.", "$\\dfrac{3 \\times 8}{4} = 6$ : $Q_3 = x_6 = 11$.", "$Me = \\dfrac{x_4 + x_5}{2} = \\dfrac{8 + 9}{2} = 8{,}5$."),
      checks=("Q_1 = 5", "Q_3 = 11"), verify=_ok(_q(_PETITE, F(1, 4)) == 5 and _q(_PETITE, F(3, 4)) == 11)),
    E(84202, N2, 1,
      "Un diagramme en boîte a pour extrémités $6$ et $17$, une boîte allant de $9$ à $12$ et une médiane égale à $10{,}5$. Calculer l'écart interquartile et l'étendue.",
      "Écart interquartile $3$ ; étendue $11$.",
      "La boîte va de $Q_1$ à $Q_3$ ; les moustaches jusqu'aux valeurs extrêmes.",
      S("$Q_1 = 9$ et $Q_3 = 12$ : $E_i = 12 - 9 = 3$.", "Étendue : $17 - 6 = 11$."),
      checks=("$3$", "$11$"), verify=_ok(12 - 9 == 3 and 17 - 6 == 11)),
    E(84203, N2, 2,
      "Notes de $20$ élèves : $6$ (1), $8$ (2), $9$ (3), $10$ (4), $11$ (3), $12$ (2), $14$ (2), $15$ (2), $17$ (1). Déterminer $Q_1$ et $Q_3$.",
      "$Q_1 = 9$ et $Q_3 = 12$.",
      "Utilise les effectifs cumulés croissants.",
      S("Effectifs cumulés : $1$ ; $3$ ; $6$ ; $10$ ; $13$ ; $15$ ; $17$ ; $19$ ; $20$.", "$\\dfrac{20}{4} = 5$ : la $5^{e}$ valeur est $9$, donc $Q_1 = 9$.",
        "$\\dfrac{3 \\times 20}{4} = 15$ : la $15^{e}$ valeur est $12$, donc $Q_3 = 12$."),
      checks=("Q_1 = 9", "Q_3 = 12"), verify=_ok(_q(_NOTES, F(1, 4)) == 9 and _q(_NOTES, F(3, 4)) == 12)),
    E(84204, N2, 2,
      "Une série rangée compte $N = 30$ valeurs. Quels rangs donnent le premier et le troisième quartile ?",
      "$Q_1$ est la $8^{e}$ valeur et $Q_3$ la $23^{e}$.",
      "On prend le plus petit entier supérieur ou égal.",
      S("$\\dfrac{30}{4} = 7{,}5$ : le plus petit entier supérieur ou égal est $8$.", "$\\dfrac{3 \\times 30}{4} = 22{,}5$ : on prend $23$."),
      checks=("8^{e}", "23^{e}"), verify=_ok(math.ceil(30 / 4) == 8 and math.ceil(90 / 4) == 23)),
    E(84205, N2, 3,
      "Classe A : min $4$, $Q_1 = 8$, $Me = 11$, $Q_3 = 13$, max $18$. Classe B : min $7$, $Q_1 = 10$, $Me = 11$, $Q_3 = 12$, max $15$. Comparer les deux séries.",
      "Même médiane ($11$) ; les notes de A sont plus dispersées : écart interquartile $5$ contre $2$, étendue $14$ contre $8$.",
      "Compare d'abord les médianes, puis les écarts interquartiles et les étendues.",
      S("Médianes : $11$ dans les deux classes.", "Écarts interquartiles : $13 - 8 = 5$ (A) et $12 - 10 = 2$ (B).", "Étendues : $18 - 4 = 14$ (A) et $15 - 7 = 8$ (B)."),
      checks=("$5$", "$2$"), verify=_ok(13 - 8 == 5 and 12 - 10 == 2)),
    E(84206, N2, 3,
      "Dans une série de $N = 22$ valeurs, le premier quartile vaut $12$. Combien de valeurs, au minimum, sont inférieures ou égales à $12$ ? Quelle proportion cela représente-t-il ?",
      "Au moins $6$ valeurs, soit environ $27\\,\\%$ des valeurs.",
      "Calcule le rang de $Q_1$.",
      S("$\\dfrac{22}{4} = 5{,}5$ : $Q_1$ est la $6^{e}$ valeur.", "Les $6$ premières valeurs sont inférieures ou égales à $Q_1 = 12$.",
        "$\\dfrac{6}{22} \\approx 0{,}27$ : plus du quart des valeurs."),
      checks=("$6$",), verify=_ok(math.ceil(22 / 4) == 6)),
    # Indicateurs de dispersion.
    E(84301, N3, 1,
      "Calculer la variance et l'écart-type de la série $2$ ; $4$ ; $6$.",
      "$V = \\dfrac{8}{3}$ et $\\sigma = \\sqrt{\\dfrac{8}{3}} \\approx 1{,}63$.",
      "Calcule d'abord la moyenne, puis la moyenne des carrés des écarts.",
      S("$\\overline{x} = \\dfrac{2 + 4 + 6}{3} = 4$.", "$V = \\dfrac{(-2)^2 + 0^2 + 2^2}{3} = \\dfrac{8}{3}$.", "$\\sigma = \\sqrt{\\dfrac{8}{3}} \\approx 1{,}63$."),
      checks=("\\dfrac{8}{3}",), verify=_ok(_var([2, 4, 6]) == F(8, 3))),
    E(84302, N3, 1,
      "Une série a pour minimum $6$, $Q_1 = 9$, $Q_3 = 12$ et maximum $17$ ; sa variance vaut $9$. Calculer l'étendue, l'écart interquartile et l'écart-type.",
      "Étendue $11$, écart interquartile $3$, écart-type $3$.",
      "L'écart-type est la racine carrée de la variance.",
      S("Étendue : $17 - 6 = 11$.", "$E_i = Q_3 - Q_1 = 12 - 9 = 3$.", "$\\sigma = \\sqrt{9} = 3$."),
      checks=("$11$", "$3$"), verify=_ok(math.isqrt(9) == 3)),
    E(84303, N3, 2,
      "Série A : $9$ ; $10$ ; $11$. Série B : $0$ ; $10$ ; $20$. Calculer les moyennes et les variances. Comparer.",
      "Les deux moyennes valent $10$ ; $V_A = \\dfrac{2}{3}$ et $V_B = \\dfrac{200}{3}$ : la série B est beaucoup plus dispersée.",
      "Même moyenne ne veut pas dire même dispersion.",
      S("Moyennes : $\\dfrac{30}{3} = 10$ dans les deux cas.", "$V_A = \\dfrac{1 + 0 + 1}{3} = \\dfrac{2}{3}$.", "$V_B = \\dfrac{100 + 0 + 100}{3} = \\dfrac{200}{3}$."),
      checks=("\\dfrac{2}{3}", "\\dfrac{200}{3}"), verify=_ok(_var([9, 10, 11]) == F(2, 3) and _var([0, 10, 20]) == F(200, 3))),
    E(84304, N3, 3,
      "Pour les $20$ notes ($\\overline{x} = 11{,}05$), on a $\\sum n_i x_i^2 = 2\\,589$. Calculer la variance avec la seconde formule, puis l'écart-type au centième.",
      "$V = 7{,}3475$ et $\\sigma \\approx 2{,}71$.",
      "$V = \\dfrac{\\sum n_i x_i^2}{N} - \\overline{x}^2$.",
      S("$\\dfrac{2\\,589}{20} = 129{,}45$.", "$V = 129{,}45 - 11{,}05^2 = 129{,}45 - 122{,}1025 = 7{,}3475$.", "$\\sigma = \\sqrt{7{,}3475} \\approx 2{,}71$."),
      checks=("7{,}3475", "2{,}71"), verify=_ok(sum(x * x for x in _NOTES) == 2589 and _var(_NOTES) == F(73475, 10000))),
    E(84305, N3, 3,
      "Salaires d'une petite entreprise (en euros) : $1\\,500$ ; $1\\,600$ ; $1\\,600$ ; $1\\,700$ ; $1\\,800$ ; $9\\,000$. Calculer la moyenne et la médiane, puis choisir un couple d'indicateurs pour résumer cette série.",
      "Moyenne environ $2\\,867$ €, médiane $1\\,650$ € : on choisit le couple (médiane, écart interquartile), peu sensible à la valeur extrême $9\\,000$.",
      "Repère la valeur extrême.",
      S("Moyenne : $\\dfrac{17\\,200}{6} \\approx 2\\,867$ €.", "Médiane : $\\dfrac{1\\,600 + 1\\,700}{2} = 1\\,650$ €.",
        "La valeur $9\\,000$ tire la moyenne vers le haut : on préfère médiane et écart interquartile."),
      checks=("1\\,650",), verify=_ok(sum([1500, 1600, 1600, 1700, 1800, 9000]) == 17200)),
    E(84306, N3, 4,
      "Démontrer que la variance d'une série vérifie $V = \\dfrac{\\sum n_i x_i^2}{N} - \\overline{x}^2$.",
      "En développant $(x_i - \\overline{x})^2$ : $\\sum n_i (x_i - \\overline{x})^2 = \\sum n_i x_i^2 - N\\overline{x}^2$, puis on divise par $N$.",
      "Développe $(x_i - \\overline{x})^2$ avec une identité remarquable.",
      S("$(x_i - \\overline{x})^2 = x_i^2 - 2\\overline{x} x_i + \\overline{x}^2$.",
        "$\\sum n_i (x_i - \\overline{x})^2 = \\sum n_i x_i^2 - 2\\overline{x} \\sum n_i x_i + \\overline{x}^2 \\sum n_i = \\sum n_i x_i^2 - 2N\\overline{x}^2 + N\\overline{x}^2$.",
        "On divise par $N$ : $V = \\dfrac{\\sum n_i x_i^2}{N} - \\overline{x}^2$."),
      checks=("N\\overline{x}^2",)),
]

QUIZ = {
    "notation-sigma-et-tendance-centrale": (84101, 84102, 73401),
    "quartiles-et-diagramme-en-boite": (84201, 84202, 84203),
    "indicateurs-de-dispersion": (84301, 84302, 84303),
}
