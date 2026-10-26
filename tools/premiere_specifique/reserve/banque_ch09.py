"""Chapitre 9 — Probabilités conditionnelles et indépendance : banque curée.

Exercices historiques (banque_ch09_historiques.py, identifiants conservés).
Réponses recalculées : deux erreurs de fond corrigées — 2004 (« 2/13, soit
une personne sur 13 » : c'est environ 1 sur 6,5) et 2005 (valeur 4/23 citée
« d'après l'exercice précédent » qui donnait 40/59 : énoncé rendu autonome) ;
2016 : « 15/23 ≈ 0,529 » corrigé en ≈ 0,652. Écriture : virgule décimale
« 0,154 » rendue {,} en mode maths, « 5.8 % » ; niveaux 5 ramenés à 4.

Nouvelle notion (programme 2026) : « Épreuves indépendantes et épreuves de
Bernoulli » (succession de deux épreuves indépendantes, arbre ou tableau ;
répétition de n ⩽ 4 épreuves de Bernoulli ; Monte-Carlo ; marche aléatoire).
Nouveaux exercices : bloc 69 000, probabilités recalculées en Fraction.
"""
import re
from fractions import Fraction as F

from premiere_specifique.reserve.banque_ch09_historiques import HISTORIQUES
from premiere_specifique.banque_commun import E, S, code

CHAPTER_NUMBER = 9
N1 = "Probabilité conditionnelle"
N2 = "Arbres pondérés"
N3 = "Notion d'indépendance"
N4 = "Épreuves indépendantes et épreuves de Bernoulli"
NOTIONS = (N1, N2, N3, N4)
NOTION_IDS = ("probabilite-conditionnelle", "arbres-ponderes", "notion-d-independance",
              "epreuves-independantes-et-epreuves-de-bernoulli")
LEGACY_IDS = tuple(h[0] for h in HISTORIQUES)

_STEP_PREFIX = re.compile(r"^\s*Étape\s*\d+\s*[:—-]\s*")
_MATH = re.compile(r"\$[^$]*\$")


def _clean(t):
    t = _MATH.sub(lambda m: re.sub(r"(\d),(\d)", r"\1{,}\2", m.group(0)), t)
    return t.replace("5.8\\%", "$5{,}8\\,\\%$")


OVERRIDES = {
    2004: dict(answer="Parmi les personnes testées positives, environ $15{,}4\\,\\%$ ($2$ sur $13$, soit à peu près une sur $6{,}5$) sont réellement malades."),
    2005: dict(enonce="Un contrôle automatique signale certaines pièces (événement $A$) ; on note $D$ l'événement « la pièce est défectueuse ». "
                      "Une étude donne $P_A(D) = \\dfrac{4}{23}$. Expliquer ce que signifie ce résultat pour le responsable de production."),
    2016: dict(steps=("$P(\\overline{S}) = 1 - \\dfrac{1}{25} = \\dfrac{24}{25}$.",
                      "$P(Z) = P(S)\\times P_S(Z) + P(\\overline{S})\\times P_{\\overline{S}}(Z) = \\dfrac{1}{25}\\times\\dfrac{9}{10} + \\dfrac{24}{25}\\times\\dfrac{1}{50} = \\dfrac{69}{1250}$.",
                      "$P(S\\cap Z) = \\dfrac{9}{250}$, donc $P_Z(S) = \\dfrac{9}{250} \\times \\dfrac{1250}{69} = \\dfrac{15}{23}$.",
                      "$P_Z(S) = \\dfrac{15}{23} \\approx 0{,}652$, bien supérieur à $P(S) = 0{,}04$ : un contrat signalé a une probabilité de sinistre beaucoup plus élevée que la moyenne, l'algorithme est utile.")),
}


def _hist(h):
    i, notion, level, enonce, answer, hint, steps = h
    o = dict(enonce=enonce, answer=_clean(answer), hint=_clean(hint), steps=tuple(_clean(_STEP_PREFIX.sub("", s)) for s in steps))
    o.update(OVERRIDES.get(i, {}))
    return E(i, notion, min(level, 4), o["enonce"], o["answer"], o["hint"], S(*o["steps"]))


HIST = [_hist(h) for h in HISTORIQUES]


def _chk(cond_fn):
    return lambda: None if cond_fn() else "valeur fausse"


def _binom(n, k, p):
    from math import comb
    return comb(n, k) * p ** k * (1 - p) ** (n - k)


NOUVEAUX = [
    # N1
    E(69101, N1, 1,
      "Dans un tableau croisé de $200$ élèves, $80$ sont internes, et $30$ internes font du théâtre. On choisit un élève interne au hasard : quelle est la probabilité qu'il fasse du théâtre ?",
      "$P_I(T) = \\dfrac{30}{80} = \\dfrac{3}{8}$.",
      "« Sachant interne » : on se restreint aux $80$ internes.",
      S("La population de référence est celle des internes : $80$ élèves.", "$P_I(T) = \\dfrac{30}{80} = \\dfrac{3}{8}$."),
      checks=("\\dfrac{3}{8}",), verify=_chk(lambda: F(30, 80) == F(3, 8))),
    E(69102, N1, 2,
      "On donne $P(A) = 0{,}4$, $P(B) = 0{,}5$ et $P(A \\cap B) = 0{,}1$. Calculer $P_A(B)$ et $P_B(A)$. Sont-elles égales ?",
      "$P_A(B) = 0{,}25$ et $P_B(A) = 0{,}2$ : elles sont différentes.",
      "On ne divise pas par la même probabilité.",
      S("$P_A(B) = \\dfrac{0{,}1}{0{,}4} = 0{,}25$.", "$P_B(A) = \\dfrac{0{,}1}{0{,}5} = 0{,}2$.", "En général, $P_A(B) \\neq P_B(A)$."),
      checks=("0{,}25",), verify=_chk(lambda: F(1, 10) / F(4, 10) == F(1, 4) and F(1, 10) / F(1, 2) == F(1, 5))),

    # N2
    E(69201, N2, 2,
      "Un magasin a trois fournisseurs : $A_1$ ($50\\,\\%$ des articles), $A_2$ ($30\\,\\%$), $A_3$ ($20\\,\\%$). Les taux de défaut sont $2\\,\\%$, $3\\,\\%$ et $5\\,\\%$. Calculer la probabilité qu'un article soit défectueux.",
      "$P(D) = 0{,}029$.",
      "$A_1$, $A_2$, $A_3$ forment une partition : formule des probabilités totales.",
      S("$P(D) = P(A_1)P_{A_1}(D) + P(A_2)P_{A_2}(D) + P(A_3)P_{A_3}(D)$.", "$= 0{,}5 \\times 0{,}02 + 0{,}3 \\times 0{,}03 + 0{,}2 \\times 0{,}05 = 0{,}01 + 0{,}009 + 0{,}01 = 0{,}029$."),
      checks=("0{,}029",), verify=_chk(lambda: F(5, 10) * F(2, 100) + F(3, 10) * F(3, 100) + F(2, 10) * F(5, 100) == F(29, 1000))),
    E(69202, N2, 3,
      "Avec les données précédentes (fournisseurs $A_1$, $A_2$, $A_3$ : $50\\,\\%$, $30\\,\\%$, $20\\,\\%$ ; défauts $2\\,\\%$, $3\\,\\%$, $5\\,\\%$), un article est défectueux. Quelle est la probabilité qu'il vienne de $A_3$ ?",
      "$P_D(A_3) = \\dfrac{0{,}01}{0{,}029} = \\dfrac{10}{29} \\approx 0{,}345$.",
      "$P_D(A_3) = \\dfrac{P(A_3 \\cap D)}{P(D)}$.",
      S("$P(A_3 \\cap D) = 0{,}2 \\times 0{,}05 = 0{,}01$ et $P(D) = 0{,}029$.", "$P_D(A_3) = \\dfrac{0{,}01}{0{,}029} = \\dfrac{10}{29} \\approx 0{,}345$."),
      checks=("\\dfrac{10}{29}",), verify=_chk(lambda: F(1, 100) / F(29, 1000) == F(10, 29))),

    # N3
    E(69301, N3, 2,
      "On lance un dé équilibré. $A$ : « le résultat est pair », $B$ : « le résultat est inférieur ou égal à $2$ ». $A$ et $B$ sont-ils indépendants ?",
      "Oui : $P(A \\cap B) = \\dfrac{1}{6} = P(A) \\times P(B) = \\dfrac{1}{2} \\times \\dfrac{1}{3}$.",
      "$A \\cap B = \\{2\\}$.",
      S("$P(A) = \\dfrac{1}{2}$, $P(B) = \\dfrac{1}{3}$.", "$A \\cap B = \\{2\\}$, $P(A \\cap B) = \\dfrac{1}{6}$.", "$\\dfrac{1}{2} \\times \\dfrac{1}{3} = \\dfrac{1}{6}$ : indépendants."),
      checks=("Oui",), verify=_chk(lambda: F(1, 2) * F(1, 3) == F(1, 6))),
    E(69302, N3, 3,
      "$A$ et $B$ sont indépendants avec $P(A) = 0{,}3$ et $P(B) = 0{,}6$. Calculer $P(A \\cap \\overline{B})$ et vérifier que $A$ et $\\overline{B}$ sont indépendants.",
      "$P(A \\cap \\overline{B}) = 0{,}12 = P(A) \\times P(\\overline{B})$.",
      "$P(A \\cap \\overline{B}) = P(A) - P(A \\cap B)$.",
      S("$P(A \\cap B) = 0{,}18$.", "$P(A \\cap \\overline{B}) = 0{,}3 - 0{,}18 = 0{,}12$.", "$P(A) \\times P(\\overline{B}) = 0{,}3 \\times 0{,}4 = 0{,}12$ : indépendants."),
      checks=("0{,}12",), verify=_chk(lambda: F(3, 10) - F(3, 10) * F(6, 10) == F(3, 10) * F(4, 10))),

    # N4 — épreuves indépendantes, Bernoulli, Monte-Carlo
    E(69401, N4, 1,
      "On lance une pièce équilibrée puis un dé équilibré, de façon indépendante. Quelle est la probabilité d'obtenir « pile » et un $6$ ?",
      "$P = \\dfrac{1}{2} \\times \\dfrac{1}{6} = \\dfrac{1}{12}$.",
      "Épreuves indépendantes : on multiplie.",
      S("Les deux épreuves sont indépendantes.", "$P(\\text{pile et } 6) = \\dfrac{1}{2} \\times \\dfrac{1}{6} = \\dfrac{1}{12}$."),
      checks=("\\dfrac{1}{12}",)),
    E(69402, N4, 1,
      "Un tireur atteint sa cible avec la probabilité $0{,}7$. Il tire deux fois, de façon indépendante. Représenter la situation par un arbre et calculer la probabilité qu'il atteigne la cible exactement une fois.",
      "$P = 2 \\times 0{,}7 \\times 0{,}3 = 0{,}42$.",
      "Deux chemins de l'arbre correspondent à « exactement une fois ».",
      S("Arbre à deux niveaux, branches $S$ ($0{,}7$) et $\\overline{S}$ ($0{,}3$) à chaque niveau.",
        "Chemins $(S, \\overline{S})$ et $(\\overline{S}, S)$ : chacun de probabilité $0{,}7 \\times 0{,}3 = 0{,}21$.", "$P = 0{,}21 + 0{,}21 = 0{,}42$."),
      checks=("0{,}42",), verify=_chk(lambda: _binom(2, 1, F(7, 10)) == F(42, 100))),
    E(69403, N4, 2,
      "On répète $3$ fois, de façon indépendante, une épreuve de Bernoulli de paramètre $p = 0{,}4$. Calculer la probabilité d'obtenir $3$ succès, puis $0$ succès.",
      "$P(3 \\text{ succès}) = 0{,}064$ et $P(0 \\text{ succès}) = 0{,}216$.",
      "Un seul chemin pour chaque cas.",
      S("$3$ succès : $0{,}4^3 = 0{,}064$.", "$0$ succès : $0{,}6^3 = 0{,}216$."),
      checks=("0{,}216",), verify=_chk(lambda: F(4, 10) ** 3 == F(64, 1000) and F(6, 10) ** 3 == F(216, 1000))),
    E(69404, N4, 3,
      "On répète $3$ fois une épreuve de Bernoulli de paramètre $p = \\dfrac{1}{4}$. À l'aide de l'arbre, calculer la probabilité d'obtenir exactement $2$ succès.",
      "$3 \\times \\left(\\dfrac{1}{4}\\right)^2 \\times \\dfrac{3}{4} = \\dfrac{9}{64}$.",
      "Combien de chemins comportent exactement $2$ succès ?",
      S("Chemins avec $2$ succès : $SS\\overline{S}$, $S\\overline{S}S$, $\\overline{S}SS$ ; il y en a $3$.", "Chacun a pour probabilité $\\dfrac{1}{4} \\times \\dfrac{1}{4} \\times \\dfrac{3}{4} = \\dfrac{3}{64}$.",
        "$P = 3 \\times \\dfrac{3}{64} = \\dfrac{9}{64}$."),
      checks=("\\dfrac{9}{64}",), verify=_chk(lambda: _binom(3, 2, F(1, 4)) == F(9, 64))),
    E(69405, N4, 3,
      "Un QCM comporte $4$ questions indépendantes à $4$ réponses dont une seule juste. Un élève répond au hasard. Quelle est la probabilité d'avoir au moins une bonne réponse ?",
      "$1 - \\left(\\dfrac{3}{4}\\right)^4 = \\dfrac{175}{256} \\approx 0{,}684$.",
      "Passe par l'événement contraire « aucune bonne réponse ».",
      S("« Aucune bonne réponse » : un seul chemin, de probabilité $\\left(\\dfrac{3}{4}\\right)^4 = \\dfrac{81}{256}$.", "$P(\\text{au moins une}) = 1 - \\dfrac{81}{256} = \\dfrac{175}{256} \\approx 0{,}684$."),
      checks=("\\dfrac{175}{256}",), verify=_chk(lambda: 1 - F(3, 4) ** 4 == F(175, 256))),
    E(69406, N4, 4,
      "On répète $4$ fois une épreuve de Bernoulli de paramètre $p = \\dfrac{1}{2}$. Calculer la probabilité d'obtenir exactement $2$ succès, en dénombrant les chemins de l'arbre.",
      "$6 \\times \\dfrac{1}{16} = \\dfrac{3}{8}$.",
      "Choisis les positions des deux succès parmi les quatre épreuves.",
      S("Chaque chemin a pour probabilité $\\left(\\dfrac{1}{2}\\right)^4 = \\dfrac{1}{16}$.",
        "Chemins à $2$ succès : $SS\\overline{SS}$, $S\\overline{S}S\\overline{S}$, $S\\overline{SS}S$, $\\overline{S}SS\\overline{S}$, $\\overline{S}S\\overline{S}S$, $\\overline{SS}SS$ : $6$ chemins.",
        "$P = \\dfrac{6}{16} = \\dfrac{3}{8}$."),
      checks=("\\dfrac{3}{8}",), verify=_chk(lambda: _binom(4, 2, F(1, 2)) == F(3, 8))),
    E(69407, N4, 2,
      "Deux épreuves indépendantes : on tire une boule dans une urne contenant $2$ rouges et $3$ bleues, puis on lance un dé équilibré. Dresser le tableau des issues (couleur, « $6$ » ou « pas $6$ ») et donner la probabilité de « rouge et pas $6$ ».",
      "$P = \\dfrac{2}{5} \\times \\dfrac{5}{6} = \\dfrac{1}{3}$.",
      "Dans un tableau à double entrée, chaque case a pour probabilité le produit des probabilités de sa ligne et de sa colonne.",
      S("Lignes : rouge ($\\dfrac{2}{5}$), bleue ($\\dfrac{3}{5}$) ; colonnes : $6$ ($\\dfrac{1}{6}$), pas $6$ ($\\dfrac{5}{6}$).", "Case « rouge, pas $6$ » : $\\dfrac{2}{5} \\times \\dfrac{5}{6} = \\dfrac{1}{3}$."),
      checks=("\\dfrac{1}{3}",), verify=_chk(lambda: F(2, 5) * F(5, 6) == F(1, 3))),
    E(69408, N4, 3,
      "Méthode de Monte-Carlo. On tire au hasard $N$ points $(x ; y)$ dans le carré $[0 ; 1] \\times [0 ; 1]$ et on compte ceux qui vérifient $x^2 + y^2 \\leqslant 1$. Expliquer pourquoi la fréquence observée, multipliée par $4$, approche $\\pi$.",
      "Les points vérifiant $x^2 + y^2 \\leqslant 1$ forment un quart de disque d'aire $\\dfrac{\\pi}{4}$ ; la fréquence approche cette aire, donc $4 \\times$ fréquence approche $\\pi$.",
      "Quelle est l'aire du quart de disque de rayon $1$ ?",
      S("Le carré a pour aire $1$ ; le quart de disque de rayon $1$ a pour aire $\\dfrac{\\pi}{4}$.",
        "La probabilité qu'un point tiré au hasard tombe dans le quart de disque est $\\dfrac{\\pi}{4}$ ; la fréquence observée s'en approche pour $N$ grand.",
        "Donc $4 \\times$ fréquence $\\approx \\pi$."),
      checks=("\\dfrac{\\pi}{4}",)),
    E(69409, N4, 4,
      "Écrire une fonction Python " + code("monte_carlo(N)") + " qui estime $\\pi$ par la méthode précédente, à l'aide de " + code("random()") + " du module " + code("random") + ".",
      code("from random import random") + " " + code("def monte_carlo(N):") + " " + code("k = 0") + " " + code("for i in range(N):") + " "
      + code("x, y = random(), random()") + " " + code("if x*x + y*y <= 1: k = k + 1") + " " + code("return 4 * k / N"),
      "Compte les points dans le quart de disque, puis multiplie la fréquence par $4$.",
      S("Chaque tour de boucle tire un point au hasard dans le carré.", "Le compteur " + code("k") + " compte les points du quart de disque.",
        "On renvoie $4 \\times \\dfrac{k}{N}$ ; avec $N = 100\\,000$, on obtient en général $\\pi$ à environ $10^{-2}$ près."),
      checks=("4 &#42; k &#47; N",)),
    E(69410, N4, 3,
      "Marche aléatoire (approfondissement). Un pion part de $0$ et, à chaque étape, avance de $+1$ ou de $-1$ avec la même probabilité, indépendamment. Quelle est la probabilité qu'il soit en $0$ après $4$ étapes ?",
      "$\\dfrac{6}{16} = \\dfrac{3}{8}$.",
      "Pour revenir en $0$, il faut autant de $+1$ que de $-1$.",
      S("Il faut exactement $2$ pas $+1$ et $2$ pas $-1$ parmi $4$.", "C'est « $2$ succès en $4$ épreuves de Bernoulli de paramètre $\\dfrac{1}{2}$ » : $6$ chemins de probabilité $\\dfrac{1}{16}$.",
        "$P = \\dfrac{3}{8}$."),
      checks=("\\dfrac{3}{8}",), verify=_chk(lambda: _binom(4, 2, F(1, 2)) == F(3, 8))),
]

EXERCISES = HIST + NOUVEAUX

QUIZ = {
    "probabilite-conditionnelle": (1710, 1712, 2000),
    "arbres-ponderes": (1768, 1769, 2038),
    "notion-d-independance": (1826, 1829, 2033),
    "epreuves-independantes-et-epreuves-de-bernoulli": (69401, 69402, 69403),
}
