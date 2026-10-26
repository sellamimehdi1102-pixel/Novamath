"""Chapitre 9 — Loi de Bernoulli et loi binomiale : banque curée (manuel
« Première ES/L », Ch. 9).

Créée lors de l'adaptation du 2026-10-26 (voir PREMIERE_SPECIFIQUE_SUIVI.md).
Exercices 69401 à 69407 repris de l'ancienne notion « Épreuves indépendantes
et épreuves de Bernoulli » (identifiants conservés) ; 69408 à 69410
(Monte-Carlo, programme Python, marche aléatoire : hors manuel) mis hors
périmètre. Nouveaux exercices : bloc 89 000 ; probabilités binomiales
recalculées exactement (`math.comb`, Fraction).
"""
from dataclasses import replace
from fractions import Fraction as F
from math import comb

from premiere_specifique.banque_commun import E, S
from premiere_specifique.reserve.banque_ch09 import EXERCISES as _ANCIEN_CH9, N4 as _N_BERNOULLI

CHAPTER_NUMBER = 9
N1 = "Expériences indépendantes et loi de Bernoulli"
N2 = "Schéma de Bernoulli et loi binomiale"
N3 = "Échantillonnage et règle de décision"
NOTIONS = (N1, N2, N3)
NOTION_IDS = ("epreuves-independantes-et-epreuves-de-bernoulli", "schema-de-bernoulli-et-loi-binomiale", "echantillonnage-et-regle-de-decision")


def _ok(cond):
    return lambda: None if cond else "valeur fausse"


def _p(n, p, k):
    return comb(n, k) * p ** k * (1 - p) ** (n - k)


def _cumul(n, p, k):
    return sum(_p(n, p, i) for i in range(k + 1))


def _bornes(n, p):
    """(a, b) au sens du manuel : P(X ⩽ a) > 0,025 et P(X ⩽ b) ⩾ 0,975, plus petits entiers."""
    a = next(k for k in range(n + 1) if _cumul(n, p, k) > F(1, 40))
    b = next(k for k in range(n + 1) if _cumul(n, p, k) >= F(39, 40))
    return a, b


_ANCIENS = [e for e in _ANCIEN_CH9 if e.notion == _N_BERNOULLI]
EXERCICES_HORS_PERIMETRE = [e for e in _ANCIENS if e.id in (69408, 69409, 69410)]
EXERCISES = ([replace(e, notion=N1) for e in _ANCIENS if e.id in (69401, 69402, 69407)]
             + [replace(e, notion=N2) for e in _ANCIENS if e.id in (69403, 69404, 69405, 69406)]) + [
    # Expériences indépendantes et loi de Bernoulli.
    E(89101, N1, 1,
      "Une pièce truquée donne « face » avec la probabilité $0{,}7$. On la lance $4$ fois de suite. Quelle est la probabilité d'obtenir $4$ fois « face » ?",
      "La probabilité est $0{,}2401$.",
      "Les lancers sont indépendants : on multiplie.",
      S("Les $4$ lancers sont des expériences indépendantes.", "$P(F_1 \\cap F_2 \\cap F_3 \\cap F_4) = 0{,}7^4 = 0{,}2401$."),
      checks=("0{,}2401",), verify=_ok(F(7, 10) ** 4 == F(2401, 10000))),
    E(89102, N1, 2,
      "Dans une usine, un article est défectueux avec la probabilité $0{,}02$. $X$ vaut $1$ si l'article est défectueux et $0$ sinon. Donner la loi de $X$, puis $E(X)$, $V(X)$ et $\\sigma(X)$.",
      "$P(X = 1) = 0{,}02$, $P(X = 0) = 0{,}98$ ; $E(X) = 0{,}02$, $V(X) = 0{,}0196$ et $\\sigma(X) = 0{,}14$.",
      "$X$ suit une loi de Bernoulli.",
      S("$X$ suit la loi de Bernoulli de paramètre $p = 0{,}02$.", "$E(X) = p = 0{,}02$ ; $V(X) = p(1 - p) = 0{,}02 \\times 0{,}98 = 0{,}0196$.", "$\\sigma(X) = \\sqrt{0{,}0196} = 0{,}14$."),
      checks=("0{,}0196", "0{,}14"), verify=_ok(F(2, 100) * F(98, 100) == F(196, 10000) and F(14, 100) ** 2 == F(196, 10000))),
    E(89103, N1, 2,
      "Une urne contient $3$ boules rouges et $2$ boules vertes. On tire successivement deux boules. Les deux tirages sont-ils indépendants si l'on remet la première boule ? si on ne la remet pas ?",
      "Avec remise, les tirages sont indépendants ; sans remise, ils ne le sont pas.",
      "Regarde si la composition de l'urne change.",
      S("Avec remise, l'urne est identique au second tirage : $P(R_2) = \\dfrac{3}{5}$ quel que soit le premier tirage.",
        "Sans remise, $P(R_2)$ vaut $\\dfrac{2}{4}$ si la première boule est rouge, $\\dfrac{3}{4}$ si elle est verte : le premier tirage influe sur le second."),
      checks=("Avec remise",)),
    E(89104, N1, 3,
      "Un QCM comporte $5$ questions indépendantes, chacune avec $3$ réponses dont une seule juste. Un élève répond au hasard. Quelle est la probabilité qu'il réponde juste à toutes les questions ? à aucune ?",
      "Toutes justes : $\\dfrac{1}{243}$ ; aucune juste : $\\dfrac{32}{243}$.",
      "Pour chaque question, le succès a la probabilité $\\dfrac{1}{3}$.",
      S("Les réponses sont des expériences indépendantes de probabilité de succès $\\dfrac{1}{3}$.", "Toutes justes : $\\left(\\dfrac{1}{3}\\right)^5 = \\dfrac{1}{243}$.",
        "Aucune juste : $\\left(\\dfrac{2}{3}\\right)^5 = \\dfrac{32}{243}$."),
      checks=("\\dfrac{1}{243}", "\\dfrac{32}{243}"), verify=_ok(F(1, 3) ** 5 == F(1, 243) and F(2, 3) ** 5 == F(32, 243))),
    E(89105, N1, 4,
      "Démontrer qu'une variable aléatoire $X$ de loi de Bernoulli de paramètre $p$ vérifie $E(X) = p$ et $V(X) = p(1 - p)$, puis déterminer la valeur de $p$ pour laquelle $V(X)$ est maximale.",
      "$E(X) = p$, $V(X) = p - p^2 = p(1 - p)$ ; la variance est maximale pour $p = \\dfrac{1}{2}$ (elle vaut alors $\\dfrac{1}{4}$).",
      "Utilise $V(X) = E(X^2) - E(X)^2$, puis étudie le trinôme $-p^2 + p$.",
      S("$E(X) = 0 \\times (1 - p) + 1 \\times p = p$.", "$X^2 = X$, donc $E(X^2) = p$ et $V(X) = p - p^2 = p(1 - p)$.",
        "$-p^2 + p$ est un trinôme de coefficient $-1 < 0$, maximal en $p = \\dfrac{1}{2}$, où il vaut $\\dfrac{1}{4}$."),
      checks=("p = \\dfrac{1}{2}",), verify=_ok(max((F(k, 100) * (1 - F(k, 100)), F(k, 100)) for k in range(101))[1] == F(1, 2))),
    # Schéma de Bernoulli et loi binomiale.
    E(89201, N2, 1,
      "On joue $7$ fois à un jeu ; à chaque partie, on gagne avec la probabilité $0{,}4$, indépendamment des autres parties. $X$ est le nombre de victoires. Quelle est la loi de $X$ ? Calculer $E(X)$.",
      "$X$ suit la loi binomiale $\\mathcal{B}(7 ; 0{,}4)$ et $E(X) = 2{,}8$.",
      "Repère le nombre de répétitions et la probabilité de succès.",
      S("On répète $7$ fois, de façon indépendante, la même épreuve de Bernoulli de succès « gagner », de paramètre $0{,}4$.",
        "$X$ compte les succès : $X \\sim \\mathcal{B}(7 ; 0{,}4)$.", "$E(X) = 7 \\times 0{,}4 = 2{,}8$."),
      checks=("\\mathcal{B}(7 ; 0{,}4)", "2{,}8"), verify=_ok(7 * F(4, 10) == F(28, 10))),
    E(89202, N2, 2,
      "$X$ suit la loi binomiale $\\mathcal{B}(5 ; 0{,}2)$. Calculer $P(X = 2)$.",
      "$P(X = 2) = 0{,}2048$.",
      "$P(X = k) = \\binom{n}{k} p^k (1 - p)^{n - k}$.",
      S("$\\binom{5}{2} = 10$.", "$P(X = 2) = 10 \\times 0{,}2^2 \\times 0{,}8^3 = 10 \\times 0{,}04 \\times 0{,}512 = 0{,}2048$."),
      checks=("0{,}2048",), verify=_ok(_p(5, F(1, 5), 2) == F(2048, 10000))),
    E(89203, N2, 2,
      "$X$ suit la loi binomiale $\\mathcal{B}(20 ; 0{,}3)$. Calculer $E(X)$, $V(X)$ et donner $\\sigma(X)$ à $0{,}01$ près.",
      "$E(X) = 6$, $V(X) = 4{,}2$ et $\\sigma(X) \\approx 2{,}05$.",
      "$E(X) = np$ et $V(X) = np(1 - p)$.",
      S("$E(X) = 20 \\times 0{,}3 = 6$.", "$V(X) = 20 \\times 0{,}3 \\times 0{,}7 = 4{,}2$.", "$\\sigma(X) = \\sqrt{4{,}2} \\approx 2{,}05$."),
      checks=("E(X) = 6", "4{,}2", "2{,}05"), verify=_ok(20 * F(3, 10) == 6 and 20 * F(3, 10) * F(7, 10) == F(42, 10) and abs(4.2 ** 0.5 - 2.05) < 0.005)),
    E(89204, N2, 3,
      "$X$ suit la loi binomiale $\\mathcal{B}(5 ; 0{,}2)$. Calculer $P(X \\geqslant 1)$.",
      "$P(X \\geqslant 1) = 0{,}67232$.",
      "Passe par l'événement contraire $X = 0$.",
      S("$P(X = 0) = 0{,}8^5 = 0{,}32768$.", "$P(X \\geqslant 1) = 1 - 0{,}32768 = 0{,}67232$."),
      checks=("0{,}67232",), verify=_ok(1 - F(4, 5) ** 5 == F(67232, 100000))),
    E(89205, N2, 4,
      "Dans un lot de $10$ pièces, chaque pièce est défectueuse avec la probabilité $0{,}1$, indépendamment des autres. Calculer la probabilité qu'il y ait au plus une pièce défectueuse (à $0{,}001$ près).",
      "$P(X \\leqslant 1) \\approx 0{,}736$.",
      "$X \\sim \\mathcal{B}(10 ; 0{,}1)$ ; additionne $P(X = 0)$ et $P(X = 1)$.",
      S("Le nombre $X$ de pièces défectueuses suit $\\mathcal{B}(10 ; 0{,}1)$.", "$P(X = 0) = 0{,}9^{10} \\approx 0{,}3487$ et $P(X = 1) = 10 \\times 0{,}1 \\times 0{,}9^9 \\approx 0{,}3874$.",
        "$P(X \\leqslant 1) \\approx 0{,}3487 + 0{,}3874 \\approx 0{,}736$."),
      checks=("0{,}736",), verify=_ok(abs(float(_cumul(10, F(1, 10), 1)) - 0.736) < 0.0005)),
    # Échantillonnage et règle de décision.
    E(89301, N3, 1,
      "Sous l'hypothèse $p = 0{,}3$, pour un échantillon de taille $50$, l'intervalle de fluctuation à $95\\,\\%$ est $[0{,}18 ; 0{,}44]$. On observe $18$ succès sur $50$. Que décider ?",
      "$f = 0{,}36 \\in [0{,}18 ; 0{,}44]$ : on accepte l'hypothèse $p = 0{,}3$.",
      "Calcule la fréquence observée et compare-la à l'intervalle.",
      S("$f = \\dfrac{18}{50} = 0{,}36$.", "$0{,}36$ appartient à $[0{,}18 ; 0{,}44]$.", "L'hypothèse n'est pas remise en question : on l'accepte."),
      checks=("0{,}36",), verify=_ok(_bornes(50, F(3, 10)) == (9, 22) and F(18, 50) == F(36, 100))),
    E(89302, N3, 1,
      "Même situation : intervalle de fluctuation $[0{,}18 ; 0{,}44]$ pour $p = 0{,}3$ et $n = 50$. On observe $25$ succès sur $50$. Que décider ?",
      "$f = 0{,}5 \\notin [0{,}18 ; 0{,}44]$ : on rejette l'hypothèse $p = 0{,}3$.",
      "Calcule la fréquence observée.",
      S("$f = \\dfrac{25}{50} = 0{,}5$.", "$0{,}5$ n'appartient pas à $[0{,}18 ; 0{,}44]$.", "On rejette l'hypothèse, avec un risque d'erreur d'environ $5\\,\\%$."),
      checks=("0{,}5",), verify=_ok(F(25, 50) > F(22, 50))),
    E(89303, N3, 2,
      "$X \\sim \\mathcal{B}(50 ; 0{,}3)$. On donne $P(X \\leqslant 8) \\approx 0{,}018$, $P(X \\leqslant 9) \\approx 0{,}040$, $P(X \\leqslant 21) \\approx 0{,}9749$ et $P(X \\leqslant 22) \\approx 0{,}9877$. Déterminer l'intervalle de fluctuation à $95\\,\\%$ de la fréquence.",
      "$a = 9$, $b = 22$ : l'intervalle est $[0{,}18 ; 0{,}44]$.",
      "$a$ : premier entier avec $P(X \\leqslant a) > 0{,}025$ ; $b$ : premier entier avec $P(X \\leqslant b) \\geqslant 0{,}975$.",
      S("$P(X \\leqslant 8) \\leqslant 0{,}025 < P(X \\leqslant 9)$ : $a = 9$.", "$P(X \\leqslant 21) < 0{,}975 \\leqslant P(X \\leqslant 22)$ : $b = 22$.",
        "$\\left[\\dfrac{9}{50} ; \\dfrac{22}{50}\\right] = [0{,}18 ; 0{,}44]$."),
      checks=("[0{,}18 ; 0{,}44]",), verify=_ok(_bornes(50, F(3, 10)) == (9, 22))),
    E(89304, N3, 3,
      "On lance $40$ fois un dé et on compte les $6$. Sous l'hypothèse « dé équilibré », $X \\sim \\mathcal{B}\\left(40 ; \\dfrac{1}{6}\\right)$ et l'on trouve $a = 2$ et $b = 12$. On observe $14$ fois le $6$. Que décider ?",
      "$f = 0{,}35 \\notin [0{,}05 ; 0{,}3]$ : on rejette l'hypothèse, le dé semble truqué.",
      "Divise $a$, $b$ et le nombre de $6$ observés par $40$.",
      S("Intervalle de fluctuation : $\\left[\\dfrac{2}{40} ; \\dfrac{12}{40}\\right] = [0{,}05 ; 0{,}3]$.", "$f = \\dfrac{14}{40} = 0{,}35$.",
        "$0{,}35 > 0{,}3$ : on rejette l'hypothèse « dé équilibré »."),
      checks=("0{,}35",), verify=_ok(_bornes(40, F(1, 6)) == (2, 12))),
    E(89305, N3, 3,
      "Un fabricant annonce $5\\,\\%$ de pièces défectueuses. Sur $100$ pièces, $X \\sim \\mathcal{B}(100 ; 0{,}05)$ et l'intervalle de fluctuation à $95\\,\\%$ est $[0{,}01 ; 0{,}10]$. On trouve $9$ pièces défectueuses. Que conclure ? Et avec $12$ ?",
      "Avec $9$ : $f = 0{,}09$, on accepte l'annonce. Avec $12$ : $f = 0{,}12$, on la rejette.",
      "Compare chaque fréquence observée à l'intervalle.",
      S("$f = \\dfrac{9}{100} = 0{,}09 \\in [0{,}01 ; 0{,}10]$ : on accepte l'annonce.", "$f = \\dfrac{12}{100} = 0{,}12 \\notin [0{,}01 ; 0{,}10]$ : on la rejette."),
      checks=("0{,}09", "0{,}12"), verify=_ok(_bornes(100, F(1, 20)) == (1, 10))),
    E(89306, N3, 4,
      "Soit $X \\sim \\mathcal{B}(n ; p)$ et $a$, $b$ les bornes définissant l'intervalle de fluctuation à $95\\,\\%$. Démontrer que $P(a \\leqslant X \\leqslant b) \\geqslant 0{,}95$.",
      "$P(a \\leqslant X \\leqslant b) = P(X \\leqslant b) - P(X \\leqslant a - 1) \\geqslant 0{,}975 - 0{,}025 = 0{,}95$.",
      "Utilise la minimalité de $a$ pour majorer $P(X \\leqslant a - 1)$.",
      S("$P(a \\leqslant X \\leqslant b) = P(X \\leqslant b) - P(X \\leqslant a - 1)$.", "Par définition, $P(X \\leqslant b) \\geqslant 0{,}975$.",
        "$a$ est le plus petit entier tel que $P(X \\leqslant a) > 0{,}025$, donc $P(X \\leqslant a - 1) \\leqslant 0{,}025$.",
        "D'où $P(a \\leqslant X \\leqslant b) \\geqslant 0{,}975 - 0{,}025 = 0{,}95$."),
      checks=("0{,}95",)),
]

QUIZ = {
    "epreuves-independantes-et-epreuves-de-bernoulli": (69401, 69402, 89101),
    "schema-de-bernoulli-et-loi-binomiale": (69403, 89201, 89202),
    "echantillonnage-et-regle-de-decision": (89301, 89302, 89303),
}
