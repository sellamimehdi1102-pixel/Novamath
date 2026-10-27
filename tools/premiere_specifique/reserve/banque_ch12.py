"""Chapitre 12 (nouveau, programme 2026) — Algorithmique et programmation :
listes. Banque curée ; l'entraînement en grand nombre vient du générateur
webapp/exercise_generator/listes_python.py (programmes exécutés au tirage).

Chaque programme cité ici est exécuté par `_sortie` au chargement du module :
la sortie annoncée dans la réponse est contrôlée (vérification `verify`).
Nouveaux exercices : bloc 72 000.
"""
import sys
from pathlib import Path

from premiere_specifique.banque_commun import E, S

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "webapp"))  # reserve/ : un niveau de plus
from exercise_generator_premiere_specifique.listes_python import code, prog, run  # noqa: E402

CHAPTER_NUMBER = 12
N1 = "Variables, instructions conditionnelles et boucles"
N2 = "Fonctions et programmation modulaire"
N3 = "Générer une liste"
N4 = "Manipuler et parcourir une liste"
NOTIONS = (N1, N2, N3, N4)
NOTION_IDS = ("variables-instructions-conditionnelles-et-boucles", "fonctions-et-programmation-modulaire",
              "generer-une-liste", "manipuler-et-parcourir-une-liste")


def _out(src, attendu):
    return lambda: None if run(src) == attendu else f"sortie {run(src)!r} ≠ {attendu!r}"


def P(i, notion, level, src, attendu, question, hint, steps, enonce_avant="On considère le programme suivant :"):
    return E(i, notion, level, f"{enonce_avant}{prog(src)}{question}", f"Le programme affiche {code(attendu)}.", hint, S(*steps),
             verify=_out(src, attendu))


_S1 = "a = 3\nb = 5\nc = a\na = b\nb = c\nprint(a, b)"
_S2 = "n = 0\ns = 0\nwhile s < 20:\n    n = n + 1\n    s = s + n\nprint(n, s)"
_S3 = "x = 7\nif x % 2 == 0:\n    print(\"pair\")\nelse:\n    print(\"impair\")"
_S4 = "def carre(x):\n    return x * x\n\ndef somme_carres(n):\n    s = 0\n    for k in range(1, n + 1):\n        s = s + carre(k)\n    return s\n\nprint(somme_carres(4))"
_S5 = "def prix_ttc(ht, taux):\n    return ht * (1 + taux / 100)\n\nprint(prix_ttc(50, 20))"
_S6 = "L = [k * k for k in range(1, 6)]\nprint(L)"
_S7 = "L = [n for n in range(1, 30) if n % 7 == 0]\nprint(L)"
_S8 = "u = [2]\nfor i in range(4):\n    u.append(u[i] * 3)\nprint(u)"
_S9 = "L = [4, 9, 1, 7]\nprint(L[0] + L[-1], len(L))"
_S10 = "L = [5, 3, 8]\nL.append(2)\nL[0] = 10\nprint(L)"
_S11 = "notes = [12, 8, 15, 10, 9]\nc = 0\nfor x in notes:\n    if x >= 10:\n        c = c + 1\nprint(c)"
_S12 = "L = [3, 8, 1, 9, 4]\ni_max = 0\nfor i in range(len(L)):\n    if L[i] > L[i_max]:\n        i_max = i\nprint(i_max, L[i_max])"

EXERCISES = [
    P(72101, N1, 1, _S1, "5 3", "Qu'affiche ce programme ? Quel est le rôle de la variable c ?", "Suis les valeurs de a, b et c ligne par ligne.",
      ("c garde une copie de la valeur initiale de a : $3$.", "a prend la valeur de b : $5$ ; puis b prend la valeur de c : $3$.", "Les valeurs de a et b ont été échangées ; affichage 5 3.")),
    P(72102, N1, 2, _S2, "6 21", "Qu'affiche ce programme ?", "s cumule 1 + 2 + … + n tant que s < 20.",
      ("Valeurs de s : $1$, $3$, $6$, $10$, $15$, $21$.", "La boucle s'arrête dès que $s \\geqslant 20$, avec $n = 6$.", "Affichage : 6 21.")),
    P(72103, N1, 1, _S3, "impair", "Qu'affiche ce programme ?", "x % 2 est le reste de la division de x par 2.",
      ("$7 = 2 \\times 3 + 1$ : le reste vaut $1$.", "La condition x % 2 == 0 est fausse : on exécute le bloc else.", "Affichage : impair.")),
    E(72104, N1, 3,
      "Écrire en langage naturel, avec le symbole « ← », un algorithme qui calcule le plus petit entier $n$ tel que $1{,}05^n > 2$, puis donner ce nombre.",
      "$n \\leftarrow 0$ ; $u \\leftarrow 1$ ; tant que $u \\leqslant 2$ : $u \\leftarrow 1{,}05 \\times u$ et $n \\leftarrow n + 1$. On obtient $n = 15$.",
      "Boucle « tant que » : on multiplie par 1,05 tant que le seuil n'est pas dépassé.",
      S("$u$ contient $1{,}05^n$ ; on l'initialise à $1$.", "Tant que $u \\leqslant 2$, on multiplie par $1{,}05$ et on compte.", "$1{,}05^{14} \\approx 1{,}98$ et $1{,}05^{15} \\approx 2{,}08$ : $n = 15$."),
      checks=("n = 15",), verify=lambda: None if (1.05 ** 14 <= 2 < 1.05 ** 15) else "seuil faux"),

    P(72201, N2, 2, _S4, "30", "Qu'affiche ce programme ?", "somme_carres appelle carre pour chaque k.",
      ("somme_carres(4) calcule $1^2 + 2^2 + 3^2 + 4^2$.", "$1 + 4 + 9 + 16 = 30$.", "La tâche est découpée en deux fonctions : programmation modulaire.")),
    P(72202, N2, 1, _S5, "60.0", "Qu'affiche ce programme ?", "Le prix TTC est le prix HT multiplié par 1 + taux/100.",
      ("prix_ttc(50, 20) $= 50 \\times 1{,}2 = 60$.", "Le calcul utilise une division : Python affiche un nombre décimal, 60.0.")),
    E(72203, N2, 3,
      "Écrire une fonction " + code("est_premier(n)") + " qui renvoie " + code("True") + " si l'entier $n \\geqslant 2$ est premier, puis une fonction " + code("premiers(N)") + " qui renvoie la liste des nombres premiers inférieurs à $N$.",
      prog("def est_premier(n):\n    for d in range(2, n):\n        if n % d == 0:\n            return False\n    return True\n\ndef premiers(N):\n    return [n for n in range(2, N) if est_premier(n)]").strip(),
      "La seconde fonction réutilise la première dans une liste en compréhension.",
      S("est_premier teste tous les diviseurs possibles de $2$ à $n - 1$.", "premiers construit la liste en compréhension avec la condition est_premier(n).",
        "Exemple : premiers(20) renvoie [2, 3, 5, 7, 11, 13, 17, 19]."),
      checks=("est_premier(n)",),
      verify=lambda: None if run("def est_premier(n):\n    for d in range(2, n):\n        if n % d == 0:\n            return False\n    return True\nprint([n for n in range(2, 20) if est_premier(n)])") == "[2, 3, 5, 7, 11, 13, 17, 19]" else "liste fausse"),

    P(72301, N3, 1, _S6, "[1, 4, 9, 16, 25]", "Quelle liste est affichée ?", "k va de 1 à 5.",
      ("Liste en compréhension : un carré pour chaque k de $1$ à $5$.", "Affichage : [1, 4, 9, 16, 25].")),
    P(72302, N3, 2, _S7, "[7, 14, 21, 28]", "Quelle liste est affichée ? À quel ensemble correspond-elle ?", "On garde les n divisibles par 7.",
      ("Condition n % 7 == 0 : multiples de $7$.", "Entre $1$ et $29$ : $7$, $14$, $21$, $28$.", "C'est l'ensemble des multiples de $7$ compris entre $1$ et $29$.")),
    P(72303, N3, 2, _S8, "[2, 6, 18, 54, 162]", "Qu'affiche ce programme ? Quelle suite reconnaît-on ?", "u[i] est le dernier terme avant l'ajout.",
      ("On part de $2$ et on multiplie par $3$ à chaque ajout.", "Termes : $2$, $6$, $18$, $54$, $162$.", "Ce sont les premiers termes de la suite géométrique de premier terme $2$ et de raison $3$.")),
    E(72304, N3, 3,
      "Écrire trois façons de générer en Python la liste " + code("[0, 2, 4, 6, 8]") + " : en extension, par ajouts successifs, en compréhension.",
      "En extension : " + code("L = [0, 2, 4, 6, 8]") + " ; par ajouts : " + code("L = []") + " puis " + code("for k in range(5): L.append(2 * k)")
      + " ; en compréhension : " + code("L = [2 * k for k in range(5)]") + ".",
      "Une liste peut être écrite directement, construite pas à pas ou décrite par une règle.",
      S("Extension : on écrit tous les éléments.", "Ajouts successifs : on part d'une liste vide et on utilise append.", "Compréhension : on décrit l'élément général $2k$."),
      checks=("range(5)",), verify=lambda: None if run("print([2 * k for k in range(5)])") == "[0, 2, 4, 6, 8]" else "liste fausse"),

    P(72401, N4, 1, _S9, "11 4", "Qu'affiche ce programme ?", "L[0] est le premier élément, L[-1] le dernier.",
      ("L[0] = 4 et L[-1] = 7 : $4 + 7 = 11$.", "La liste a $4$ éléments.", "Affichage : 11 4.")),
    P(72402, N4, 1, _S10, "[10, 3, 8, 2]", "Qu'affiche ce programme ?", "append ajoute à la fin ; L[0] = 10 remplace le premier élément.",
      ("Après append(2) : [5, 3, 8, 2].", "Après L[0] = 10 : [10, 3, 8, 2].")),
    P(72403, N4, 2, _S11, "3", "Qu'affiche ce programme ? Que calcule-t-il ?", "On parcourt les notes une à une.",
      ("On compte les notes supérieures ou égales à $10$.", "$12$, $15$ et $10$ conviennent.", "Affichage : 3 (nombre de notes au moins égales à $10$).")),
    P(72404, N4, 3, _S12, "3 9", "Qu'affiche ce programme ? Que fait-il ?", "i_max mémorise l'indice du plus grand élément rencontré.",
      ("On parcourt les indices $0$ à $4$.", "Le plus grand élément est $9$, d'indice $3$.", "Le programme affiche l'indice et la valeur du maximum : 3 9.")),
]

QUIZ = {
    "variables-instructions-conditionnelles-et-boucles": (72101, 72102, 72103),
    "fonctions-et-programmation-modulaire": (72201, 72202, 72205),
    "generer-une-liste": (72301, 72302, 72303),
    "manipuler-et-parcourir-une-liste": (72401, 72402, 72403),
}

_S13 = "def f(x):\n    return 2 * x - 1\n\nprint(f(f(3)))"
EXERCISES.append(P(72205, N2, 1, _S13, "9", "Qu'affiche ce programme ?", "Calcule d'abord f(3), puis f de ce résultat.",
                   ("f(3) = $2 \\times 3 - 1 = 5$.", "f(5) = $2 \\times 5 - 1 = 9$.", "Affichage : 9.")))
