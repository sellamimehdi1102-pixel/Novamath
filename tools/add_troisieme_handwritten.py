"""Ajoute les exercices rédigés à la main pour les deux notions du lot
Troisième où aucune génération symbolique n'a de sens :

- Chapitre_7 :: "Lire graphiquement une image ou un antécédent" — le site
  n'a aucun support d'affichage de courbe ; toute lecture graphique est
  donc décrite textuellement (liste de points), comme le pilote Première
  l'a fait pour la lecture graphique de tangente.
- Chapitre_10 :: "Construire et utiliser un arbre de probabilités" — la
  structure d'un arbre (contexte, nombre de branches, remise ou non) varie
  trop pour un moteur générique ; contenu rédigé et vérifié à la main
  (toutes les probabilités recalculées avec `fractions.Fraction` avant
  écriture, jamais tapées "en dur" sans contrôle).

Usage : python -m tools.add_troisieme_handwritten
"""
import json
from fractions import Fraction as F
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BANK_PATH = ROOT / "exercises_bank_troisieme.json"

NEXT_ID = 2010


def _f(x: F) -> str:
    if x.denominator == 1:
        return str(x.numerator)
    return f"\\dfrac{{{x.numerator}}}{{{x.denominator}}}"


LECTURE_GRAPHIQUE = [
    {
        "enonce": (
            "La courbe représentative d'une fonction $f$ passe par les points "
            "$A(-2\\,;\\,4)$, $B(-1\\,;\\,1)$, $C(0\\,;\\,0)$, $D(1\\,;\\,1)$, $E(2\\,;\\,4)$. "
            "Un élève affirme : \"$f(-1) = -1$\". A-t-il raison ? Justifier en lisant le tableau de points."
        ),
        "answer": "Faux : d'après le point $B(-1\\,;\\,1)$, $f(-1) = 1$, pas $-1$.",
        "hint": "Repérer le point dont l'abscisse est -1 et lire son ordonnée avant de juger l'affirmation.",
        "solution_steps": [
            "Étape 1 — Le point d'abscisse $-1$ est $B(-1\\,;\\,1)$.",
            "Étape 2 — On lit donc $f(-1) = 1$, ce qui contredit l'affirmation de l'élève : elle est fausse.",
        ],
        "difficulty": 2,
    },
    {
        "enonce": (
            "La courbe représentative d'une fonction $g$ passe par les points "
            "$A(-3\\,;\\,-5)$, $B(-1\\,;\\,-1)$, $C(1\\,;\\,3)$, $D(3\\,;\\,7)$. "
            "Un élève écrit : \"l'antécédent de $3$ par $g$ est $3$\" en confondant image et antécédent. "
            "Identifier son erreur et donner la bonne réponse."
        ),
        "answer": "Erreur : il a lu l'image de 3 (qui vaut 7, point D) au lieu de chercher l'antécédent de 3. L'antécédent de $3$ par $g$ est $1$ (point $C$).",
        "hint": "Un antécédent se cherche en ordonnée (on lit l'abscisse du point), une image se cherche en abscisse (on lit l'ordonnée) — ne pas confondre les deux sens de lecture.",
        "solution_steps": [
            "Étape 1 — Chercher l'antécédent de 3 signifie trouver le point dont l'ORDONNÉE vaut 3, pas l'abscisse.",
            "Étape 2 — Le point $C(1\\,;\\,3)$ a pour ordonnée $3$, donc l'antécédent de $3$ par $g$ est $1$.",
            "Étape 3 — L'élève a confondu avec l'image de $3$, qui vaut $7$ (point $D$) : ce n'est pas ce qui était demandé.",
        ],
        "difficulty": 3,
    },
    {
        "enonce": (
            "La courbe représentative d'une fonction $h$ passe par les points "
            "$A(-2\\,;\\,6)$, $B(-1\\,;\\,2)$, $C(0\\,;\\,-1)$, $D(1\\,;\\,-3)$, $E(2\\,;\\,-4)$. "
            "Comparer $h(-2)$ et $h(2)$ : lequel des deux est le plus grand ?"
        ),
        "answer": "$h(-2) = 6$ est plus grand que $h(2) = -4$.",
        "hint": "Lire les deux images séparément avant de les comparer, plutôt que de deviner d'après la position des points.",
        "solution_steps": [
            "Étape 1 — Le point $A(-2\\,;\\,6)$ donne $h(-2) = 6$.",
            "Étape 2 — Le point $E(2\\,;\\,-4)$ donne $h(2) = -4$.",
            "Étape 3 — $6 > -4$, donc $h(-2)$ est le plus grand des deux.",
        ],
        "difficulty": 2,
    },
    {
        "enonce": (
            "La courbe représentative d'une fonction $f$ passe par les points "
            "$A(-2\\,;\\,-3)$, $B(-1\\,;\\,-1)$, $C(0\\,;\\,2)$, $D(1\\,;\\,4)$. "
            "Sans connaître l'expression de $f$, peut-on affirmer que l'équation $f(x) = 0$ admet une solution "
            "entre $-1$ et $0$ ? Justifier."
        ),
        "answer": "Oui, on peut le supposer : $f(-1) = -1$ est négatif et $f(0) = 2$ est positif, donc la courbe change de signe (et donc croise l'axe des abscisses) entre ces deux points.",
        "hint": "Si l'image passe d'une valeur négative à une valeur positive entre deux abscisses connues, la courbe traverse nécessairement l'axe des abscisses entre elles.",
        "solution_steps": [
            "Étape 1 — $f(-1) = -1$ (point $B$) est négatif ; $f(0) = 2$ (point $C$) est positif.",
            "Étape 2 — Comme $f$ passe d'une valeur négative à une valeur positive entre $x=-1$ et $x=0$, elle s'annule nécessairement quelque part entre les deux (en admettant que la courbe ne présente pas de saut).",
            "Étape 3 — On ne peut pas donner la valeur exacte de cette solution sans l'expression de $f$, seulement encadrer son existence.",
        ],
        "difficulty": 4,
    },
    {
        "enonce": (
            "La courbe représentative d'une fonction $g$ passe par les points "
            "$A(-4\\,;\\,1)$, $B(-2\\,;\\,3)$, $C(0\\,;\\,5)$, $D(2\\,;\\,7)$, $E(4\\,;\\,9)$. "
            "Lire graphiquement l'image de $-2$ par $g$, puis l'antécédent de $9$ par $g$."
        ),
        "answer": "$g(-2) = 3$ et l'antécédent de $9$ par $g$ est $4$.",
        "hint": "Traiter les deux questions séparément : image = lire l'ordonnée à partir de l'abscisse donnée ; antécédent = lire l'abscisse à partir de l'ordonnée donnée.",
        "solution_steps": [
            "Étape 1 — Le point $B(-2\\,;\\,3)$ donne $g(-2) = 3$.",
            "Étape 2 — Le point $E(4\\,;\\,9)$ a pour ordonnée $9$, donc l'antécédent de $9$ par $g$ est $4$.",
        ],
        "difficulty": 2,
    },
    {
        "enonce": (
            "La courbe représentative d'une fonction $f$ passe par les points "
            "$A(-3\\,;\\,7)$, $B(-1\\,;\\,3)$, $C(1\\,;\\,-1)$, $D(3\\,;\\,-5)$. "
            "Un élève affirme : \"$f$ est strictement croissante sur cet intervalle, car les ordonnées augmentent "
            "de gauche à droite\". A-t-il raison ? Justifier en observant les ordonnées."
        ),
        "answer": "Faux : les ordonnées données ($7$, $3$, $-1$, $-5$) diminuent quand l'abscisse augmente ; $f$ semble donc décroissante sur cet intervalle, pas croissante.",
        "hint": "Comparer les ordonnées successives dans l'ordre des abscisses croissantes : si elles diminuent, la fonction est décroissante, pas croissante.",
        "solution_steps": [
            "Étape 1 — Les abscisses des points, dans l'ordre croissant, sont $-3, -1, 1, 3$.",
            "Étape 2 — Les ordonnées correspondantes sont $7, 3, -1, -5$ : elles diminuent à chaque fois.",
            "Étape 3 — Une fonction dont les images diminuent quand $x$ augmente est décroissante, pas croissante : l'élève s'est trompé de sens.",
        ],
        "difficulty": 3,
    },
]

ARBRE_PROBABILITES = [
    {
        "enonce": (
            "Une urne contient 3 boules rouges et 2 boules bleues, indiscernables au toucher. On tire une boule, "
            "on la remet, puis on tire une seconde boule. Construire l'arbre de probabilités complet (4 issues) "
            "et vérifier que la somme des probabilités des 4 issues vaut bien $1$."
        ),
        "answer": f"$P(RR)=\\dfrac{{9}}{{25}}$, $P(RB)=\\dfrac{{6}}{{25}}$, $P(BR)=\\dfrac{{6}}{{25}}$, $P(BB)=\\dfrac{{4}}{{25}}$, et leur somme vaut ${_f(F(9,25)+F(6,25)+F(6,25)+F(4,25))}$.",
        "hint": "Calculer les 4 probabilités une par une (produit des probabilités le long de chaque chemin), puis les additionner pour vérifier qu'on retrouve 1.",
        "solution_steps": [
            "Étape 1 — À chaque tirage, $P(\\text{rouge}) = \\dfrac{3}{5}$ et $P(\\text{bleu}) = \\dfrac{2}{5}$ (la boule est remise).",
            "Étape 2 — $P(RR) = \\dfrac{3}{5}\\times\\dfrac{3}{5} = \\dfrac{9}{25}$ ; $P(RB) = \\dfrac{3}{5}\\times\\dfrac{2}{5} = \\dfrac{6}{25}$ ; "
            "$P(BR) = \\dfrac{2}{5}\\times\\dfrac{3}{5} = \\dfrac{6}{25}$ ; $P(BB) = \\dfrac{2}{5}\\times\\dfrac{2}{5} = \\dfrac{4}{25}$.",
            "Étape 3 — La somme des 4 issues couvre TOUS les cas possibles, donc $\\dfrac{9}{25}+\\dfrac{6}{25}+\\dfrac{6}{25}+\\dfrac{4}{25} = \\dfrac{25}{25} = 1$, comme attendu.",
        ],
        "difficulty": 2,
    },
    {
        "enonce": (
            "La même urne (3 boules rouges, 2 boules bleues) est utilisée, mais cette fois SANS remise : on tire "
            "une boule, on ne la remet pas, puis on tire une seconde boule. Construire l'arbre de probabilités et "
            "calculer la probabilité d'obtenir deux boules rouges."
        ),
        "answer": f"$P(RR) = {_f(F(3,5)*F(2,4))}$",
        "hint": "Sans remise, la composition de l'urne change après le premier tirage : les probabilités du second tirage dépendent du résultat du premier.",
        "solution_steps": [
            "Étape 1 — Au premier tirage, $P(\\text{rouge}) = \\dfrac{3}{5}$.",
            "Étape 2 — S'il reste 2 rouges parmi 4 boules pour le second tirage (une rouge a été retirée sans être remise), "
            "$P(\\text{rouge au 2e} \\mid \\text{rouge au 1er}) = \\dfrac{2}{4}$.",
            f"Étape 3 — $P(RR) = \\dfrac{{3}}{{5}}\\times\\dfrac{{2}}{{4}} = {_f(F(3,5)*F(2,4))}$.",
        ],
        "difficulty": 3,
    },
    {
        "enonce": (
            "Un sac contient 5 jetons rouges, 3 jetons verts et 2 jetons jaunes, indiscernables au toucher. On "
            "tire successivement deux jetons SANS remise. Comparer la probabilité d'obtenir \"deux jetons rouges\" "
            "et celle d'obtenir \"un jeton rouge puis un jeton vert\" : laquelle est la plus grande ?"
        ),
        "answer": f"$P(\\text{{rouge, rouge}}) = {_f(F(5,10)*F(4,9))}$ est plus grande que $P(\\text{{rouge, vert}}) = {_f(F(5,10)*F(3,9))}$.",
        "hint": "Calculer les deux probabilités séparément (en tenant compte du tirage sans remise pour le second jeton), puis les comparer.",
        "solution_steps": [
            f"Étape 1 — $P(\\text{{rouge, rouge}}) = \\dfrac{{5}}{{10}}\\times\\dfrac{{4}}{{9}} = {_f(F(5,10)*F(4,9))}$ (il reste 4 rouges parmi 9 jetons après le premier tirage).",
            f"Étape 2 — $P(\\text{{rouge, vert}}) = \\dfrac{{5}}{{10}}\\times\\dfrac{{3}}{{9}} = {_f(F(5,10)*F(3,9))}$ (il reste 3 verts parmi 9 jetons, le nombre de rouges n'a pas changé).",
            f"Étape 3 — ${_f(F(5,10)*F(4,9))} > {_f(F(5,10)*F(3,9))}$, donc \"deux rouges\" est plus probable.",
        ],
        "difficulty": 4,
    },
    {
        "enonce": (
            "Une urne contient 4 boules jaunes et 6 boules noires. On tire une boule, on la remet, puis on tire "
            "une seconde boule. Un élève affirme : \"la probabilité d'obtenir au moins une boule jaune sur les "
            "deux tirages est $\\dfrac{16}{25}$\". Cette affirmation est-elle correcte ? Justifier en utilisant "
            "l'événement contraire."
        ),
        "answer": f"Vrai : $P(\\text{{au moins une jaune}}) = 1 - P(\\text{{aucune jaune}}) = 1 - \\dfrac{{6}}{{10}}\\times\\dfrac{{6}}{{10}} = {_f(1-F(6,10)*F(6,10))}$.",
        "hint": "\"Au moins une jaune\" est l'événement contraire de \"aucune jaune\" (donc noire, noire) : calculer P(aucune jaune) puis faire 1 moins ce résultat.",
        "solution_steps": [
            "Étape 1 — L'événement contraire de \"au moins une jaune\" est \"aucune jaune\", c'est-à-dire \"noire puis noire\".",
            f"Étape 2 — $P(\\text{{noire, noire}}) = \\dfrac{{6}}{{10}}\\times\\dfrac{{6}}{{10}} = \\dfrac{{36}}{{100}} = {_f(F(6,10)*F(6,10))}$.",
            f"Étape 3 — $P(\\text{{au moins une jaune}}) = 1 - {_f(F(6,10)*F(6,10))} = {_f(1-F(6,10)*F(6,10))}$, ce qui confirme l'affirmation de l'élève.",
        ],
        "difficulty": 3,
    },
    {
        "enonce": (
            "Une urne contient 2 boules vertes et 3 boules rouges. On tire deux boules SANS remise. Un élève "
            "calcule ainsi la probabilité d'obtenir deux boules vertes : \"$P(\\text{vert}) = \\dfrac{2}{5}$ à "
            "chaque tirage, donc $P(VV) = \\dfrac{2}{5}\\times\\dfrac{2}{5} = \\dfrac{4}{25}$\". Identifier son "
            "erreur et donner le calcul correct."
        ),
        "answer": f"Erreur : il a oublié que le tirage est SANS remise, la probabilité change au second tirage. Le calcul correct est $P(VV) = \\dfrac{{2}}{{5}}\\times\\dfrac{{1}}{{4}} = {_f(F(2,5)*F(1,4))}$, pas $\\dfrac{{4}}{{25}}$.",
        "hint": "Sans remise, il ne reste plus que 4 boules (dont 1 verte) pour le second tirage si la première boule tirée était verte — la probabilité du second tirage doit être recalculée.",
        "solution_steps": [
            "Étape 1 — Au premier tirage, $P(\\text{vert}) = \\dfrac{2}{5}$, c'est correct.",
            "Étape 2 — Mais SANS remise, s'il y avait 2 vertes sur 5 boules et qu'une verte a été tirée, il ne reste plus qu'1 verte sur 4 boules : $P(\\text{vert au 2e} \\mid \\text{vert au 1er}) = \\dfrac{1}{4}$, pas $\\dfrac{2}{5}$.",
            f"Étape 3 — Le calcul correct est $P(VV) = \\dfrac{{2}}{{5}}\\times\\dfrac{{1}}{{4}} = {_f(F(2,5)*F(1,4))}$.",
        ],
        "difficulty": 4,
    },
    {
        "enonce": (
            "On lance deux fois de suite une pièce de monnaie équilibrée. Calculer la probabilité d'obtenir "
            "\"au moins un pile\" en comparant deux méthodes : le calcul direct (additionner les chemins "
            "favorables) et le calcul par l'événement contraire."
        ),
        "answer": "$P(\\text{au moins un pile}) = \\dfrac{3}{4}$ par les deux méthodes.",
        "hint": "L'événement contraire de \"au moins un pile\" est \"aucun pile\" (donc face, face) : les deux méthodes doivent donner le même résultat.",
        "solution_steps": [
            "Méthode directe — Les chemins favorables sont (pile, pile), (pile, face), (face, pile), chacun de probabilité $\\dfrac{1}{4}$, "
            "soit $P(\\text{au moins un pile}) = \\dfrac{1}{4}+\\dfrac{1}{4}+\\dfrac{1}{4} = \\dfrac{3}{4}$.",
            "Méthode par le contraire — $P(\\text{aucun pile}) = P(\\text{face, face}) = \\dfrac{1}{2}\\times\\dfrac{1}{2} = \\dfrac{1}{4}$, "
            "donc $P(\\text{au moins un pile}) = 1 - \\dfrac{1}{4} = \\dfrac{3}{4}$.",
            "Étape finale — Les deux méthodes donnent bien le même résultat ; l'événement contraire est souvent plus rapide dès qu'on demande \"au moins un\".",
        ],
        "difficulty": 3,
    },
    {
        "enonce": (
            "On lance trois fois de suite une pièce de monnaie équilibrée. En construisant l'arbre à 3 niveaux "
            "(8 chemins), calculer la probabilité d'obtenir exactement deux \"pile\" sur les trois lancers."
        ),
        "answer": f"$P(\\text{{exactement 2 piles}}) = {_f(F(3,8))}$",
        "hint": "Identifier tous les chemins de l'arbre à 3 niveaux contenant exactement deux P et un F (il y en a 3), puis additionner leurs probabilités.",
        "solution_steps": [
            "Étape 1 — Chaque chemin de l'arbre à 3 niveaux a la même probabilité : $\\left(\\dfrac{1}{2}\\right)^3 = \\dfrac{1}{8}$.",
            "Étape 2 — Les chemins contenant exactement deux P sont : (P,P,F), (P,F,P), (F,P,P), soit 3 chemins sur les 8 possibles.",
            f"Étape 3 — $P(\\text{{exactement 2 piles}}) = 3\\times\\dfrac{{1}}{{8}} = {_f(F(3,8))}$.",
        ],
        "difficulty": 5,
    },
    {
        "enonce": (
            "Dans un contrôle qualité, un lot contient 8 pièces conformes et 2 pièces défectueuses. On prélève "
            "deux pièces SANS remise pour vérification. Interpréter : que représente concrètement l'événement "
            "\"les deux pièces prélevées sont conformes\" pour l'entreprise, puis calculer sa probabilité."
        ),
        "answer": f"Cela signifie que le contrôle ne détecte aucun défaut sur cet échantillon (alors qu'il existe des pièces défectueuses dans le lot) ; $P(\\text{{conforme, conforme}}) = {_f(F(8,10)*F(7,9))}$.",
        "hint": "Interpréter d'abord ce que signifie l'événement dans le contexte du contrôle qualité, puis calculer sa probabilité avec un tirage sans remise.",
        "solution_steps": [
            "Étape 1 — Interprétation : si les deux pièces prélevées sont conformes, le contrôle ne révèle aucune anomalie, "
            "même si le lot contient bel et bien des pièces défectueuses non détectées.",
            "Étape 2 — $P(\\text{conforme au 1er}) = \\dfrac{8}{10}$ ; sans remise, $P(\\text{conforme au 2e} \\mid \\text{conforme au 1er}) = \\dfrac{7}{9}$.",
            f"Étape 3 — $P(\\text{{conforme, conforme}}) = \\dfrac{{8}}{{10}}\\times\\dfrac{{7}}{{9}} = {_f(F(8,10)*F(7,9))}$.",
        ],
        "difficulty": 4,
    },
]


def main() -> None:
    data = json.loads(BANK_PATH.read_text(encoding="utf-8"))
    next_id = NEXT_ID

    for ex in LECTURE_GRAPHIQUE:
        ex["chapter_id"] = "Chapitre_7"
        ex["chapter"] = "Fonctions"
        ex["notion"] = "Lire graphiquement une image ou un antécédent"
        ex["id"] = next_id
        next_id += 1
        data.append(ex)

    for ex in ARBRE_PROBABILITES:
        ex["chapter_id"] = "Chapitre_10"
        ex["chapter"] = "Probabilités"
        ex["notion"] = "Construire et utiliser un arbre de probabilités"
        ex["id"] = next_id
        next_id += 1
        data.append(ex)

    BANK_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Ajouté {len(LECTURE_GRAPHIQUE)} exercices de lecture graphique et {len(ARBRE_PROBABILITES)} exercices d'arbres de probabilités.")
    print(f"Total banque : {len(data)} exercices, prochain id libre : {next_id}")


if __name__ == "__main__":
    main()
