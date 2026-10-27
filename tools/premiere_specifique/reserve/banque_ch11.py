"""Chapitre 11 (nouveau, programme 2026) — Vocabulaire ensembliste et logique :
banque curée. Les exercices d'entraînement en grand nombre viennent du
générateur webapp/exercise_generator/logique_ensembles.py.

Nouveaux exercices : bloc 71 000.
"""
from premiere_specifique.banque_commun import E, S

CHAPTER_NUMBER = 11
N1 = "Ensembles et notations"
N2 = "Propositions, connecteurs et quantificateurs"
N3 = "Implication, réciproque et contraposée"
N4 = "Types de raisonnement"
NOTIONS = (N1, N2, N3, N4)
NOTION_IDS = ("ensembles-et-notations", "propositions-connecteurs-et-quantificateurs",
              "implication-reciproque-et-contraposee", "types-de-raisonnement")


def _chk(cond_fn):
    return lambda: None if cond_fn() else "valeur fausse"


A, B = {2, 4, 6, 8, 10}, {3, 6, 9}

EXERCISES = [
    E(71101, N1, 1,
      "On donne $A = \\{2 ; 4 ; 6 ; 8 ; 10\\}$ et $B = \\{3 ; 6 ; 9\\}$. Déterminer $A \\cap B$ et $A \\cup B$.",
      "$A \\cap B = \\{6\\}$ et $A \\cup B = \\{2 ; 3 ; 4 ; 6 ; 8 ; 9 ; 10\\}$.",
      "Intersection : « et » ; réunion : « ou ».",
      S("Seul $6$ est dans les deux ensembles.", "La réunion rassemble tous les éléments, sans répétition."),
      checks=("\\{6\\}",), verify=_chk(lambda: A & B == {6} and len(A | B) == 7)),
    E(71102, N1, 1,
      "Compléter avec $\\in$, $\\notin$ ou $\\subset$ : $\\sqrt{2} \\ldots \\mathbb{Q}$ ; $\\{1 ; 2\\} \\ldots \\mathbb{N}$ ; $-3 \\ldots \\mathbb{N}$.",
      "$\\sqrt{2} \\notin \\mathbb{Q}$ ; $\\{1 ; 2\\} \\subset \\mathbb{N}$ ; $-3 \\notin \\mathbb{N}$.",
      "Un élément appartient ($\\in$) ; un ensemble est inclus ($\\subset$).",
      S("$\\sqrt{2}$ n'est pas rationnel.", "$\\{1 ; 2\\}$ est un ensemble dont les éléments sont des entiers naturels : inclusion.", "$-3$ est négatif : il n'est pas dans $\\mathbb{N}$."),
      checks=("\\subset \\mathbb{N}",)),
    E(71103, N1, 2,
      "Dans une classe de $30$ élèves, $18$ font du sport, $12$ de la musique et $5$ les deux. Combien ne font ni l'un ni l'autre ?",
      "$5$ élèves.",
      "$\\operatorname{Card}(S \\cup M) = \\operatorname{Card}(S) + \\operatorname{Card}(M) - \\operatorname{Card}(S \\cap M)$.",
      S("$\\operatorname{Card}(S \\cup M) = 18 + 12 - 5 = 25$.", "Ni l'un ni l'autre : $30 - 25 = 5$."),
      checks=("$5$",), verify=_chk(lambda: 30 - (18 + 12 - 5) == 5)),
    E(71104, N1, 2,
      "On lance un dé puis une pièce. Décrire l'univers comme un produit cartésien et donner son cardinal.",
      "$\\Omega = \\{1 ; 2 ; 3 ; 4 ; 5 ; 6\\} \\times \\{P ; F\\}$, de cardinal $12$.",
      "Un résultat est un couple (résultat du dé ; résultat de la pièce).",
      S("Chaque issue est un couple, par exemple $(3 ; P)$.", "$\\operatorname{Card}(\\Omega) = 6 \\times 2 = 12$."),
      checks=("$12$",)),
    E(71105, N1, 3,
      "Déterminer $[-2 ; 5[ \\cap ]1 ; 7]$ et $[-2 ; 5[ \\cup ]1 ; 7]$, puis le complémentaire de $[-2 ; 5[$ dans $\\mathbb{R}$.",
      "$]1 ; 5[$ ; $[-2 ; 7]$ ; $]-\\infty ; -2[ \\cup [5 ; +\\infty[$.",
      "Représente les intervalles sur une droite graduée.",
      S("Partie commune : de $1$ (exclu) à $5$ (exclu).", "Réunion : de $-2$ (inclus) à $7$ (inclus).", "Complémentaire : tout ce qui est hors de $[-2 ; 5[$."),
      checks=("]1 ; 5[",)),

    E(71201, N2, 1,
      "La proposition « $12$ est pair ou $12$ est un multiple de $5$ » est-elle vraie ? Et « $12$ est pair et $12$ est un multiple de $5$ » ?",
      "La première est vraie, la seconde est fausse.",
      "« ou » : au moins une ; « et » : les deux.",
      S("« $12$ est pair » est vraie, « $12$ est multiple de $5$ » est fausse.", "« ou » : vraie ; « et » : fausse."),
      checks=("seconde est fausse",)),
    E(71202, N2, 2,
      "Écrire la négation de : « Tous les élèves de la classe ont plus de $15$ ans. »",
      "« Au moins un élève de la classe a $15$ ans ou moins. »",
      "La négation de « tous » est « au moins un… ne… pas ».",
      S("On remplace « pour tout » par « il existe ».", "On nie « a plus de $15$ ans » : « a $15$ ans ou moins »."),
      checks=("Au moins un",)),
    E(71203, N2, 2,
      "Montrer que la proposition « pour tout réel $x$, $x^2 \\geqslant x$ » est fausse.",
      "Contre-exemple : $x = \\dfrac{1}{2}$, car $\\dfrac{1}{4} < \\dfrac{1}{2}$.",
      "Cherche entre $0$ et $1$.",
      S("Un seul contre-exemple suffit.", "Pour $x = \\dfrac{1}{2}$ : $x^2 = \\dfrac{1}{4} < x$."),
      checks=("\\dfrac{1}{2}",)),
    E(71204, N2, 3,
      "Dans « $f(x) = ax + 3$ ; déterminer $a$ pour que $f(2) = 7$ », préciser le statut des lettres $x$, $a$ et de l'égalité $f(2) = 7$.",
      "$x$ est une variable, $a$ un paramètre (inconnue du problème), $f(2) = 7$ est une équation d'inconnue $a$ ; solution $a = 2$.",
      "Une variable parcourt un ensemble ; une inconnue est cherchée.",
      S("$x$ désigne n'importe quel réel : variable.", "$a$ est fixé mais inconnu : on le cherche.", "$2a + 3 = 7 \\iff a = 2$."),
      checks=("a = 2",), verify=_chk(lambda: 2 * 2 + 3 == 7)),
    E(71205, N2, 3,
      "Écrire la négation de : « Il existe un entier $n$ tel que $n^2 = 2$ et $n > 0$. » Laquelle des deux propositions est vraie ?",
      "Négation : « Pour tout entier $n$, $n^2 \\neq 2$ ou $n \\leqslant 0$ ». C'est la négation qui est vraie.",
      "La négation de « P et Q » est « non P ou non Q ».",
      S("« il existe » devient « pour tout ».", "« $n^2 = 2$ et $n > 0$ » devient « $n^2 \\neq 2$ ou $n \\leqslant 0$ ».", "Aucun entier n'a pour carré $2$ : la négation est vraie."),
      checks=("n \\leqslant 0",)),

    E(71301, N3, 1,
      "Énoncer la réciproque de « si un quadrilatère est un carré, alors c'est un rectangle ». Est-elle vraie ?",
      "Réciproque : « si un quadrilatère est un rectangle, alors c'est un carré » ; elle est fausse.",
      "On échange hypothèse et conclusion.",
      S("Réciproque : on échange les deux parties.", "Un rectangle de côtés $2$ et $3$ n'est pas un carré : contre-exemple."),
      checks=("fausse",)),
    E(71302, N3, 2,
      "Énoncer la contraposée de « si $n^2$ est pair, alors $n$ est pair ».",
      "« Si $n$ est impair, alors $n^2$ est impair. »",
      "Contraposée de « si P alors Q » : « si non Q alors non P ».",
      S("Non Q : « $n$ est impair » ; non P : « $n^2$ est impair ».", "Contraposée : « si $n$ est impair, alors $n^2$ est impair »."),
      checks=("n^2$ est impair",)),
    E(71303, N3, 2,
      "Compléter par « nécessaire » ou « suffisante » : pour qu'un réel $x$ vérifie $x^2 = 9$, il est … que $x = 3$ ; il est … que $x \\geqslant -3$.",
      "« $x = 3$ » est une condition suffisante ; « $x \\geqslant -3$ » est une condition nécessaire.",
      "Suffisante : elle entraîne le résultat ; nécessaire : le résultat l'entraîne.",
      S("$x = 3 \\Rightarrow x^2 = 9$ : suffisante (pas nécessaire : $x = -3$).", "$x^2 = 9 \\Rightarrow x = \\pm 3 \\Rightarrow x \\geqslant -3$ : nécessaire."),
      checks=("nécessaire",)),
    E(71304, N3, 3,
      "« Pour tous réels $a$ et $b$, $a^2 = b^2 \\iff a = b$ ». Vrai ou faux ? Corriger si nécessaire.",
      "Faux : seule l'implication « $a = b \\Rightarrow a^2 = b^2$ » est vraie ; la bonne équivalence est $a^2 = b^2 \\iff a = b$ ou $a = -b$.",
      "Teste $a = 2$ et $b = -2$.",
      S("$a = 2$, $b = -2$ : $a^2 = b^2$ mais $a \\neq b$.", "$a^2 - b^2 = (a - b)(a + b) = 0 \\iff a = b$ ou $a = -b$."),
      checks=("a = -b",)),

    E(71401, N4, 2,
      "Démontrer par disjonction des cas que, pour tout entier $n$, $n(n + 1)$ est pair.",
      "Si $n$ est pair, le facteur $n$ est pair ; si $n$ est impair, $n + 1$ est pair : le produit est toujours pair.",
      "Distingue n pair et n impair.",
      S("Cas $n$ pair : $n(n + 1)$ a un facteur pair.", "Cas $n$ impair : $n + 1$ est pair.", "Dans tous les cas, le produit est pair."),
      checks=("toujours pair",)),
    E(71402, N4, 3,
      "Démontrer par l'absurde qu'il n'existe pas de plus grand entier naturel.",
      "Si $N$ était le plus grand entier, $N + 1$ serait un entier plus grand : contradiction.",
      "Suppose le contraire et cherche une contradiction.",
      S("Supposons qu'il existe un plus grand entier $N$.", "$N + 1$ est un entier et $N + 1 > N$ : contradiction.", "L'hypothèse est fausse : il n'y a pas de plus grand entier."),
      checks=("contradiction",)),
    E(71403, N4, 4,
      "Démontrer par l'absurde que $\\sqrt{2}$ n'est pas rationnel (on admet que si $n^2$ est pair, alors $n$ est pair).",
      "Si $\\sqrt{2} = \\dfrac{p}{q}$ irréductible, alors $p^2 = 2q^2$, donc $p$ pair, $p = 2k$, puis $q^2 = 2k^2$ et $q$ pair : contradiction avec l'irréductibilité.",
      "Écris $\\sqrt{2} = \\dfrac{p}{q}$ avec une fraction irréductible.",
      S("Supposons $\\sqrt{2} = \\dfrac{p}{q}$, fraction irréductible : $p^2 = 2q^2$.", "$p^2$ est pair, donc $p$ est pair : $p = 2k$, et $4k^2 = 2q^2$, soit $q^2 = 2k^2$.",
        "$q$ est pair aussi : $p$ et $q$ sont tous deux divisibles par $2$, contradiction."),
      checks=("contradiction",)),
    E(71404, N4, 3,
      "Démontrer par contraposée : pour tout entier $n$, si $n^2$ est pair, alors $n$ est pair.",
      "Contraposée : si $n$ est impair, $n = 2k + 1$, alors $n^2 = 2(2k^2 + 2k) + 1$ est impair. Donc l'implication est vraie.",
      "Démontre « si n impair, alors n² impair ».",
      S("Contraposée : « si $n$ est impair, alors $n^2$ est impair ».", "$n = 2k + 1$ : $n^2 = 4k^2 + 4k + 1 = 2(2k^2 + 2k) + 1$, impair.",
        "La contraposée est vraie, donc l'implication aussi."),
      checks=("impair",)),
    E(71405, N4, 1,
      "Pour démontrer par l'absurde qu'une proposition P est vraie, que suppose-t-on au départ, et que cherche-t-on à obtenir ?",
      "On suppose que P est fausse (on suppose « non P »), et on cherche à aboutir à une contradiction.",
      "« Par l'absurde » : on part du contraire de ce qu'on veut montrer.",
      S("Hypothèse de départ : « non P ».", "On raisonne jusqu'à une contradiction (deux affirmations incompatibles).", "Donc « non P » est impossible : P est vraie."),
      checks=("contradiction",)),
    E(71406, N4, 2,
      "Démontrer par disjonction des cas que, pour tout réel $x$, $|x| \\geqslant x$.",
      "Si $x \\geqslant 0$, $|x| = x$ ; si $x < 0$, $|x| = -x > 0 > x$. Dans les deux cas, $|x| \\geqslant x$.",
      "Distingue x positif et x négatif.",
      S("Cas $x \\geqslant 0$ : $|x| = x$, donc $|x| \\geqslant x$.", "Cas $x < 0$ : $|x| = -x$ est positif, donc supérieur à $x$ qui est négatif.", "La propriété est vraie dans tous les cas."),
      checks=("|x| \\geqslant x",)),
]

QUIZ = {
    "ensembles-et-notations": (71101, 71102, 71103),
    "propositions-connecteurs-et-quantificateurs": (71201, 71202, 71203),
    "implication-reciproque-et-contraposee": (71301, 71302, 71303),
    "types-de-raisonnement": (71401, 71405, 71406),
}
