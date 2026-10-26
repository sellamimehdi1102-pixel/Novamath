"""Chapitre 8 (ancien chapitre 10) — Variables aléatoires : banque curée.

Exercices historiques (banque_ch10_historiques.py, identifiants conservés).
Toutes les réponses ont été recalculées (justes). Défauts d'écriture corrigés
par _clean : « -1^2 × … » (lu −1, écrit (−1)²), « 2X -3 », « 3X +0 »,
« 1X +4 », « × - », virgules décimales en mode maths, « \\% » hors formule,
« 2.20 euros », « 50.0 euros » ; écarts-types √(204/25) et √(171/25)
simplifiés ; niveaux 5 ramenés à 4.

Nouvelle notion (section « Expérimentations » du programme 2026) :
« Simulation et échantillonnage » (moyenne observée sur un échantillon et
espérance, algorithmes d'espérance, de variance et de fréquences).
Nouveaux exercices : bloc 70 000, valeurs recalculées en fractions exactes.
"""
import re
from fractions import Fraction as F

from premiere_specifique.banque_ch08_historiques import HISTORIQUES
from premiere_specifique.banque_commun import E, S, code

CHAPTER_NUMBER = 8  # ancien chapitre 10 (adaptation au manuel « Première ES/L », 2026-10-26)
N1 = "Variables aléatoires réelles"
N2 = "Espérance – Variance – Écart-type"
N3 = "Loi des grands nombres et simulation"
NOTIONS = (N1, N2, N3)
NOTION_IDS = ("variables-aleatoires-reelles", "esperance-–-variance-–-ecart-type", "simulation-et-echantillonnage")
LEGACY_IDS = tuple(h[0] for h in HISTORIQUES)

_STEP_PREFIX = re.compile(r"^\s*Étape\s*\d+\s*[:—-]\s*")
_SPLIT = re.compile(r"(\$[^$]*\$)")


def _affine(m):
    a, s, b = m.group(1), m.group(2), int(m.group(3))
    lead = "X" if a in ("", "1") else (f"-X" if a == "-1" else f"{a}X")
    return lead if b == 0 else f"{lead} {s} {b}"


def _math(t):
    t = re.sub(r"(\d+)\.00(?!\d)", r"\1", t)
    t = re.sub(r"(\d),(\d)", r"\1{,}\2", t)
    t = re.sub(r"(?<![\w)}])-(\d+)\^2", r"(-\1)^2", t)
    t = re.sub(r"\\times\s*-\s*(\d+)", r"\\times (-\1)", t)
    t = re.sub(r"\\times\s*-\s*\\dfrac\{(\d+)\}\{(\d+)\}", r"\\times \\left(-\\dfrac{\1}{\2}\\right)", t)
    t = re.sub(r"\s*\+\s*0(?![\d{,.])", "", t)
    t = re.sub(r"\+\s*-\s*(\d)", r"- \1", t)
    t = re.sub(r"(-?\d*)X\s*([+-])\s*(\d+)(?![\d}])", _affine, t)
    return t


def _texte(t):
    t = re.sub(r"(\d+(?:[.,]\d+)?)\s*\\%", lambda m: f"${m.group(1).replace('.', '{,}').replace(',', '{,}')}\\,\\%$", t)
    t = re.sub(r"(\d+)\.00 euros", r"\1 euros", t)
    t = re.sub(r"(\d+)\.0 euros", r"\1 euros", t)
    t = re.sub(r"(\d+)\.(\d+) euros", r"$\1{,}\2$ euros", t)
    return t


def _clean(t):
    return "".join(_math(p) if p.startswith("$") else _texte(p) for p in _SPLIT.split(t))


OVERRIDES = {
    1942: dict(answer="$V(X) = \\dfrac{204}{25}$ et $\\sigma(X) = \\dfrac{2\\sqrt{51}}{5}$"),
    2077: dict(answer="$E(X) = \\dfrac{12}{5}$, $V(X) = \\dfrac{171}{25}$ et $\\sigma(X) = \\dfrac{3\\sqrt{19}}{5}$"),
}


def _hist(h):
    i, notion, level, enonce, answer, hint, steps = h
    o = dict(enonce=_clean(enonce), answer=_clean(answer), hint=_clean(hint),
             steps=tuple(_clean(_STEP_PREFIX.sub("", s)) for s in steps))
    o.update(OVERRIDES.get(i, {}))
    return E(i, notion, min(level, 4), o["enonce"], o["answer"], o["hint"], S(*o["steps"]))


HIST = [_hist(h) for h in HISTORIQUES]


def _chk(cond_fn):
    return lambda: None if cond_fn() else "valeur fausse"


def _E(loi):
    return sum(F(x) * p for x, p in loi)


def _V(loi):
    return sum(F(x) ** 2 * p for x, p in loi) - _E(loi) ** 2


_DE = [(k, F(1, 6)) for k in range(1, 7)]

NOUVEAUX = [
    # N1
    E(70101, N1, 1,
      "On lance deux pièces équilibrées et on note $X$ le nombre de « pile ». Donner les valeurs possibles de $X$ et sa loi de probabilité.",
      "$X$ prend les valeurs $0$, $1$, $2$ avec $P(X = 0) = \\dfrac{1}{4}$, $P(X = 1) = \\dfrac{1}{2}$, $P(X = 2) = \\dfrac{1}{4}$.",
      "L'univers est $\\{PP, PF, FP, FF\\}$, quatre issues équiprobables.",
      S("Univers : $PP$, $PF$, $FP$, $FF$, chacune de probabilité $\\dfrac{1}{4}$.", "$X(PP) = 2$, $X(PF) = X(FP) = 1$, $X(FF) = 0$.",
        "$P(X = 1) = \\dfrac{2}{4} = \\dfrac{1}{2}$ ; la somme vaut bien $1$."),
      checks=("P(X = 1) = \\dfrac{1}{2}",)),
    E(70102, N1, 2,
      "On lance un dé équilibré. On note $X$ le gain : $5$ euros si le résultat est $6$, $1$ euro s'il est $4$ ou $5$, et $-2$ euros sinon. Traduire en langage naturel l'événement $\\{X \\leqslant 1\\}$ et calculer sa probabilité.",
      "$\\{X \\leqslant 1\\}$ : « le joueur gagne au plus $1$ euro », c'est-à-dire le dé n'affiche pas $6$ ; $P(X \\leqslant 1) = \\dfrac{5}{6}$.",
      "$\\{X \\leqslant 1\\} = \\{X = -2\\} \\cup \\{X = 1\\}$.",
      S("$P(X = -2) = \\dfrac{3}{6}$ et $P(X = 1) = \\dfrac{2}{6}$.", "$P(X \\leqslant 1) = \\dfrac{5}{6}$ : c'est le contraire de « obtenir $6$ »."),
      checks=("\\dfrac{5}{6}",), verify=_chk(lambda: F(3, 6) + F(2, 6) == F(5, 6))),
    E(70103, N1, 3,
      "Une urne contient $3$ boules numérotées $1$, $2$, $3$. On tire successivement deux boules avec remise et on note $X$ la somme des numéros. Déterminer la loi de $X$.",
      "$P(X = 2) = \\dfrac{1}{9}$, $P(X = 3) = \\dfrac{2}{9}$, $P(X = 4) = \\dfrac{3}{9}$, $P(X = 5) = \\dfrac{2}{9}$, $P(X = 6) = \\dfrac{1}{9}$.",
      "Fais un tableau à double entrée des $9$ tirages équiprobables.",
      S("$9$ couples équiprobables (tableau $3 \\times 3$).", "Sommes : $2$ (1 fois), $3$ (2 fois), $4$ (3 fois), $5$ (2 fois), $6$ (1 fois).", "Somme des probabilités : $\\dfrac{9}{9} = 1$."),
      checks=("P(X = 4) = \\dfrac{3}{9}",)),

    # N2
    E(70201, N2, 1,
      "On lance un dé équilibré à $6$ faces ; $X$ est le résultat. Calculer $E(X)$.",
      "$E(X) = \\dfrac{7}{2}$.",
      "$E(X) = \\sum x_i\\,P(X = x_i)$.",
      S("$E(X) = \\dfrac{1 + 2 + 3 + 4 + 5 + 6}{6} = \\dfrac{21}{6}$.", "$E(X) = \\dfrac{7}{2} = 3{,}5$."),
      checks=("\\dfrac{7}{2}",), verify=_chk(lambda: _E(_DE) == F(7, 2))),
    E(70202, N2, 2,
      "Avec le dé équilibré précédent, calculer $V(X)$ à l'aide de la formule de König-Huygens $V(X) = E(X^2) - E(X)^2$.",
      "$V(X) = \\dfrac{35}{12}$.",
      "$E(X^2) = \\dfrac{1 + 4 + 9 + 16 + 25 + 36}{6}$.",
      S("$E(X^2) = \\dfrac{91}{6}$.", "$V(X) = \\dfrac{91}{6} - \\dfrac{49}{4} = \\dfrac{182 - 147}{12} = \\dfrac{35}{12}$."),
      checks=("\\dfrac{35}{12}",), verify=_chk(lambda: _V(_DE) == F(35, 12))),
    E(70203, N2, 2,
      "Un forfait coûte $15$ euros plus $2$ euros par séance ; le nombre $X$ de séances vérifie $E(X) = 8$ et $V(X) = 9$. On note $Y = 2X + 15$ le coût. Calculer $E(Y)$ et $\\sigma(Y)$.",
      "$E(Y) = 31$ euros et $\\sigma(Y) = 6$ euros.",
      "Linéarité de l'espérance ; $V(aX + b) = a^2V(X)$.",
      S("$E(Y) = 2 \\times 8 + 15 = 31$.", "$V(Y) = 4 \\times 9 = 36$, donc $\\sigma(Y) = 6$."),
      checks=("\\sigma(Y) = 6",)),
    E(70204, N2, 3,
      "On donne $P(X = 0) = 0{,}5$, $P(X = 2) = 0{,}3$ et $P(X = a) = 0{,}2$ avec $a > 2$. Déterminer $a$ pour que $E(X) = 2$.",
      "$a = 7$.",
      "Écris $E(X)$ en fonction de $a$.",
      S("$E(X) = 0 + 0{,}6 + 0{,}2a$.", "$0{,}6 + 0{,}2a = 2 \\iff 0{,}2a = 1{,}4 \\iff a = 7$."),
      checks=("a = 7",), verify=_chk(lambda: F(6, 10) + F(2, 10) * 7 == 2)),
    E(70205, N2, 4,
      "Approfondissement. Soit $X$ une variable aléatoire et $f(x) = E\\left((X - x)^2\\right)$. Montrer que $f(x) = x^2 - 2E(X)x + E(X^2)$ et en déduire que $f$ est minimale en $x = E(X)$, de minimum $V(X)$.",
      "Par linéarité, $f(x) = E(X^2) - 2xE(X) + x^2$ : trinôme de sommet $x = E(X)$, de minimum $E(X^2) - E(X)^2 = V(X)$.",
      "Développe $(X - x)^2$ et utilise la linéarité de l'espérance.",
      S("$(X - x)^2 = X^2 - 2xX + x^2$, donc $f(x) = E(X^2) - 2xE(X) + x^2$.", "C'est un trinôme en $x$, de coefficient $1 > 0$ : minimum en $x = \\dfrac{2E(X)}{2} = E(X)$.",
        "$f(E(X)) = E(X^2) - 2E(X)^2 + E(X)^2 = V(X)$."),
      checks=("V(X)",)),

    # N3
    E(70301, N3, 1,
      "On lance $1\\,000$ fois un dé équilibré et on calcule la moyenne des résultats obtenus. Autour de quelle valeur s'attend-on à trouver cette moyenne ?",
      "Autour de $E(X) = 3{,}5$.",
      "La moyenne observée sur un grand échantillon est proche de l'espérance.",
      S("$X$ : résultat d'un lancer, $E(X) = 3{,}5$.", "Sur un grand échantillon, la moyenne observée fluctue autour de $3{,}5$."),
      checks=("3{,}5",)),
    E(70302, N3, 2,
      "Que renvoie la fonction Python " + code("def esperance(valeurs, probas): return sum(x * p for x, p in zip(valeurs, probas))") + " pour " + code("esperance([0, 10, 50], [0.7, 0.25, 0.05])") + " ?",
      "Elle renvoie $0 \\times 0{,}7 + 10 \\times 0{,}25 + 50 \\times 0{,}05 = 5$ : l'espérance de la loi.",
      "La fonction calcule $\\sum x_i\\,p_i$.",
      S(code("zip") + " associe chaque valeur à sa probabilité.", "Somme des produits : $0 + 2{,}5 + 2{,}5 = 5$."),
      checks=("= 5",), verify=_chk(lambda: 0 * F(7, 10) + 10 * F(25, 100) + 50 * F(5, 100) == 5)),
    E(70303, N3, 3,
      "Compléter la fonction " + code("def variance(valeurs, probas):") + " qui renvoie $V(X)$ par la formule de König-Huygens, en réutilisant " + code("esperance") + ".",
      code("m = esperance(valeurs, probas)") + " puis " + code("return esperance([x**2 for x in valeurs], probas) - m**2"),
      "$V(X) = E(X^2) - E(X)^2$.",
      S("On calcule $m = E(X)$.", "$E(X^2)$ est l'espérance de la liste des carrés, avec les mêmes probabilités.", "On renvoie $E(X^2) - m^2$."),
      checks=("m&#42;&#42;2",)),
    E(70304, N3, 3,
      "On simule $100$ échantillons de $50$ lancers d'un dé et on calcule la moyenne de chaque échantillon. Comment varie la dispersion des moyennes si l'on passe à des échantillons de $500$ lancers ?",
      "Elle diminue : les moyennes d'échantillons plus grands sont plus concentrées autour de $E(X) = 3{,}5$.",
      "Plus l'échantillon est grand, plus la moyenne observée est fiable.",
      S("Chaque moyenne d'échantillon estime $E(X) = 3{,}5$.", "Avec $500$ lancers au lieu de $50$, les fluctuations d'échantillonnage sont plus faibles : l'écart-type des moyennes diminue."),
      checks=("diminue",)),
    E(70306, N3, 4,
      "On simule $N = 200$ échantillons de $n = 100$ lancers d'un dé équilibré ($E(X) = 3{,}5$, $\\sigma(X) = \\sqrt{\\dfrac{35}{12}}$). "
      "a) Calculer $\\dfrac{2\\sigma}{\\sqrt{n}}$ au centième. b) Écrire un programme qui compte la proportion d'échantillons dont la moyenne $m$ vérifie $|m - 3{,}5| \\leqslant \\dfrac{2\\sigma}{\\sqrt{n}}$. "
      "c) Quelle proportion observe-t-on en général ?",
      "a) $\\dfrac{2\\sigma}{\\sqrt{n}} \\approx 0{,}34$. b) " + code("from random import randint") + " " + code("ok = 0") + " " + code("for k in range(200):") + " "
      + code("m = sum(randint(1, 6) for i in range(100)) / 100") + " " + code("if abs(m - 3.5) <= 0.34: ok = ok + 1") + " " + code("print(ok / 200)")
      + ". c) Environ $95\\,\\%$ des échantillons.",
      "$\\sigma = \\sqrt{\\dfrac{35}{12}} \\approx 1{,}708$.",
      S("$\\dfrac{2\\sigma}{\\sqrt{100}} = \\dfrac{2 \\times 1{,}708}{10} \\approx 0{,}34$.",
        "Pour chaque échantillon, on calcule la moyenne de $100$ lancers et on teste l'écart à $3{,}5$.",
        "On observe en général environ $95\\,\\%$ d'échantillons dans cet intervalle : les moyennes se concentrent autour de l'espérance."),
      checks=("0{,}34",), verify=_chk(lambda: round(2 * (35 / 12) ** 0.5 / 10, 2) == 0.34)),
    E(70305, N3, 2,
      "Écrire une fonction Python " + code("frequence(texte, lettre)") + " qui renvoie la fréquence d'apparition d'une lettre dans un texte.",
      code("def frequence(texte, lettre): return texte.count(lettre) / len(texte)"),
      "Compte les apparitions et divise par la longueur du texte.",
      S(code("texte.count(lettre)") + " donne le nombre d'apparitions.", "On divise par " + code("len(texte)") + " pour obtenir une fréquence."),
      checks=("texte.count(lettre)",)),
]

EXERCISES = HIST + NOUVEAUX

QUIZ = {
    "variables-aleatoires-reelles": (1884, 1889, 2056),
    "esperance-–-variance-–-ecart-type": (1944, 1945, 2074),
    "simulation-et-echantillonnage": (70301, 70302, 70305),
}

# ── Adaptation au manuel « Première ES/L » (2026-10-26) ─────────────────────
# Voir PREMIERE_SPECIFIQUE_SUIVI.md. Hors manuel, retirés de la banque servie
# (conservés ici) : variables Y = aX + b (linéarité), approfondissement
# x ↦ E((X − x)²), programmes Python et intervalle 2σ/√n.
_IDS_HORS_PERIMETRE = {1944, 1946, 1947, 1949, 1966, 2085, 70203, 70205, 70302, 70303, 70304, 70305, 70306}
EXERCICES_HORS_PERIMETRE = [e for e in EXERCISES if e.id in _IDS_HORS_PERIMETRE]
EXERCISES = [e for e in EXERCISES if e.id not in _IDS_HORS_PERIMETRE]

N_EVT = "Rappels de probabilités : événements"
NOTIONS = (N_EVT, N1, N2, N3)
NOTION_IDS = ("rappels-de-probabilites-evenements", "variables-aleatoires-reelles",
              "esperance-–-variance-–-ecart-type", "simulation-et-echantillonnage")


def _ok(cond):
    return lambda: None if cond else "valeur fausse"


# Réutilisés de l'ancien chapitre « Automatismes » (tableau croisé, dé).
from dataclasses import replace as _replace  # noqa: E402

from premiere_specifique.reserve.banque_ch13 import EXERCISES as _AUTOMATISMES  # noqa: E402

EXERCISES += [_replace(e, notion=N_EVT) for e in _AUTOMATISMES if e.id in (73402, 73403)]

EXERCISES += [
    # Rappels de probabilités : événements (bloc 88 100).
    E(88101, N_EVT, 1,
      "On lance un dé équilibré à six faces. $A$ : « obtenir un nombre pair », $B$ : « obtenir au moins $5$ ». Décrire $A \\cap B$ et $A \\cup B$, puis calculer $P(A \\cup B)$.",
      "$A \\cap B = \\{6\\}$, $A \\cup B = \\{2 ; 4 ; 5 ; 6\\}$ et $P(A \\cup B) = \\dfrac{2}{3}$.",
      "Écris d'abord les issues de $A$ et de $B$.",
      S("$A = \\{2 ; 4 ; 6\\}$ et $B = \\{5 ; 6\\}$.", "$A \\cap B = \\{6\\}$ ; $A \\cup B = \\{2 ; 4 ; 5 ; 6\\}$.",
        "$P(A \\cup B) = \\dfrac{4}{6} = \\dfrac{2}{3}$."),
      checks=("\\dfrac{2}{3}",), verify=_ok(F(4, 6) == F(3, 6) + F(2, 6) - F(1, 6))),
    E(88102, N_EVT, 1,
      "La probabilité qu'un candidat réussisse un examen est $0{,}35$. Quelle est la probabilité qu'il échoue ?",
      "La probabilité d'échouer est $0{,}65$.",
      "Échouer est l'événement contraire de réussir.",
      S("Notons $R$ : « réussir » ; échouer est $\\overline{R}$.", "$P(\\overline{R}) = 1 - P(R) = 1 - 0{,}35 = 0{,}65$."),
      checks=("0{,}65",), verify=_ok(1 - F(35, 100) == F(65, 100))),
    E(88103, N_EVT, 2,
      "On donne $P(A) = 0{,}5$, $P(B) = 0{,}4$ et $P(A \\cap B) = 0{,}15$. Calculer $P(A \\cup B)$.",
      "$P(A \\cup B) = 0{,}75$.",
      "Utilise la formule de la réunion.",
      S("$P(A \\cup B) = P(A) + P(B) - P(A \\cap B)$.", "$P(A \\cup B) = 0{,}5 + 0{,}4 - 0{,}15 = 0{,}75$."),
      checks=("0{,}75",), verify=_ok(F(1, 2) + F(2, 5) - F(15, 100) == F(3, 4))),
    E(88104, N_EVT, 2,
      "$A$ et $B$ sont deux événements incompatibles avec $P(A) = 0{,}3$ et $P(B) = 0{,}45$. Calculer $P(A \\cap B)$ et $P(A \\cup B)$.",
      "$P(A \\cap B) = 0$ et $P(A \\cup B) = 0{,}75$.",
      "Incompatibles : $A \\cap B = \\varnothing$.",
      S("$A \\cap B = \\varnothing$, donc $P(A \\cap B) = 0$.", "$P(A \\cup B) = 0{,}3 + 0{,}45$, soit $0{,}75$."),
      checks=("0{,}75",), verify=_ok(F(3, 10) + F(45, 100) == F(3, 4))),
    E(88105, N_EVT, 3,
      "On donne $P(A) = 0{,}4$, $P(B) = 0{,}5$ et $P(A \\cup B) = 0{,}7$. Calculer $P(A \\cap B)$, puis la probabilité qu'aucun des deux événements ne soit réalisé.",
      "$P(A \\cap B) = 0{,}2$ et $P(\\overline{A} \\cap \\overline{B}) = 0{,}3$.",
      "« Aucun des deux » : $\\overline{A} \\cap \\overline{B} = \\overline{A \\cup B}$.",
      S("$P(A \\cap B) = P(A) + P(B) - P(A \\cup B) = 0{,}4 + 0{,}5 - 0{,}7 = 0{,}2$.",
        "D'après les lois de De Morgan, $\\overline{A} \\cap \\overline{B} = \\overline{A \\cup B}$.",
        "$P(\\overline{A \\cup B}) = 1 - 0{,}7 = 0{,}3$."),
      checks=("0{,}2", "0{,}3"), verify=_ok(F(2, 5) + F(1, 2) - F(7, 10) == F(1, 5))),
    E(88106, N_EVT, 3,
      "On tire une carte d'un jeu de $32$ cartes. $A$ : « la carte est un cœur », $B$ : « la carte est une figure » (valet, dame ou roi). Calculer $P(A)$, $P(B)$, $P(A \\cap B)$ et $P(A \\cup B)$.",
      "$P(A) = \\dfrac{1}{4}$, $P(B) = \\dfrac{3}{8}$, $P(A \\cap B) = \\dfrac{3}{32}$ et $P(A \\cup B) = \\dfrac{17}{32}$.",
      "Il y a $8$ cœurs, $12$ figures, dont $3$ figures de cœur.",
      S("$P(A) = \\dfrac{8}{32} = \\dfrac{1}{4}$ ; $P(B) = \\dfrac{12}{32} = \\dfrac{3}{8}$ ; $P(A \\cap B) = \\dfrac{3}{32}$.",
        "$P(A \\cup B) = \\dfrac{8 + 12 - 3}{32} = \\dfrac{17}{32}$."),
      checks=("\\dfrac{17}{32}",), verify=_ok(F(8, 32) + F(12, 32) - F(3, 32) == F(17, 32))),
    # Loi des grands nombres et simulation (bloc 88 400).
    E(88401, N3, 1,
      "On lance $10\\,000$ fois une pièce de monnaie équilibrée. Autour de quelle valeur la fréquence d'apparition de « pile » devrait-elle se trouver ?",
      "Autour de $0{,}5$, la probabilité d'obtenir pile.",
      "Pense à la loi des grands nombres.",
      S("La probabilité d'obtenir pile est $0{,}5$.", "Pour un grand nombre de lancers, la fréquence observée se rapproche de la probabilité."),
      checks=("0{,}5",)),
    E(88402, N3, 1,
      "Une punaise lancée $2\\,000$ fois est tombée $1\\,240$ fois sur la pointe. Donner une estimation de la probabilité qu'elle tombe sur la pointe.",
      "Environ $0{,}62$.",
      "Une fréquence sur un grand nombre d'essais estime une probabilité.",
      S("$f = \\dfrac{1\\,240}{2\\,000} = 0{,}62$.", "D'après la loi des grands nombres, la probabilité est proche de $0{,}62$."),
      checks=("0{,}62",), verify=_ok(F(1240, 2000) == F(62, 100))),
    E(88403, N3, 2,
      "$X$ est le nombre de « pile » obtenus en deux lancers d'une pièce équilibrée. On simule $500$ fois l'expérience. Autour de quelle valeur la moyenne des valeurs observées de $X$ devrait-elle se trouver ?",
      "Autour de $E(X) = 1$.",
      "Calcule l'espérance de $X$.",
      S("Loi de $X$ : $P(X = 0) = \\dfrac{1}{4}$, $P(X = 1) = \\dfrac{1}{2}$, $P(X = 2) = \\dfrac{1}{4}$.",
        "$E(X) = 0 \\times \\dfrac{1}{4} + 1 \\times \\dfrac{1}{2} + 2 \\times \\dfrac{1}{4} = 1$.",
        "Pour un grand nombre de simulations, la moyenne observée se rapproche de $E(X)$."),
      checks=("E(X) = 1",), verify=_ok(F(1, 2) + 2 * F(1, 4) == 1)),
    E(88404, N3, 3,
      "Sur $1\\,000$ lancers d'un dé, la face $6$ est sortie $248$ fois. Le dé semble-t-il équilibré ? Justifier.",
      "Non : la fréquence $0{,}248$ est très éloignée de $\\dfrac{1}{6} \\approx 0{,}167$ pour un aussi grand nombre de lancers ; le dé semble truqué.",
      "Compare la fréquence observée à la probabilité d'un dé équilibré.",
      S("Fréquence observée : $\\dfrac{248}{1\\,000} = 0{,}248$.", "Si le dé était équilibré, la probabilité serait $\\dfrac{1}{6} \\approx 0{,}167$.",
        "Sur $1\\,000$ lancers, la loi des grands nombres prévoit une fréquence proche de $0{,}167$ : l'écart est trop grand."),
      checks=("0{,}248",), verify=_ok(F(248, 1000) > F(1, 6) + F(5, 100))),
    E(88405, N3, 3,
      "Un jeu coûte $2$ euros ; on reçoit $5$ euros avec la probabilité $\\dfrac{1}{4}$, rien sinon. Le gain algébrique est noté $X$. On simule $10\\,000$ parties : quel gain moyen par partie peut-on attendre ?",
      "Un gain moyen proche de $E(X) = -0{,}75$ euro : on perd environ $0{,}75$ euro par partie.",
      "Écris la loi de $X$ : gain $3$ ou perte de $2$.",
      S("$X = 5 - 2 = 3$ avec la probabilité $\\dfrac{1}{4}$, $X = -2$ avec la probabilité $\\dfrac{3}{4}$.",
        "$E(X) = 3 \\times \\dfrac{1}{4} - 2 \\times \\dfrac{3}{4} = -\\dfrac{3}{4}$.",
        "Sur $10\\,000$ parties, le gain moyen observé est proche de $-0{,}75$ euro."),
      checks=("-0{,}75",), verify=_ok(3 * F(1, 4) - 2 * F(3, 4) == F(-3, 4))),
]
QUIZ = {
    "rappels-de-probabilites-evenements": (88101, 88102, 73403),
    "variables-aleatoires-reelles": (1884, 1889, 2056),
    "esperance-–-variance-–-ecart-type": (70201, 1945, 2074),
    "simulation-et-echantillonnage": (70301, 88401, 88402),
}
