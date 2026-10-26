"""Chapitre 2 — Fonctions numériques (Première spécifique, manuel « Première ES/L »,
Ch. 2 : notion de fonction, sens de variation, représentation graphique ;
fonction racine carrée ; fonction cube).

Créé lors de l'adaptation du 2026-10-26 (voir PREMIERE_SPECIFIQUE_SUIVI.md) :
« Rappels sur les fonctions » reprend l'identifiant et des exemples de
l'ancienne notion « Fonctions et représentations » (chapitre « Automatismes »),
sans l'équation de droite (hors manuel) et avec les définitions du sens de
variation ; « Fonction racine carrée » et « Fonction cube » sont créées (la
symétrie de la courbe du cube reprend l'idée de l'ancienne notion de parité).
"""
import math

from premiere_specifique.cours_commun import calc, chapter, curve, demonstration, ex, explication, figure_geom, formule, notion, pt, step, text

N1, N2, N3 = "Rappels sur les fonctions", "Fonction racine carrée", "Fonction cube"
ID1, ID2, ID3 = "fonctions-et-representations", "fonction-racine-carree", "fonction-cube"


def _s(a, b, **kw):
    s = {"from": {"x": a[0], "y": a[1]}, "to": {"x": b[0], "y": b[1]}}
    s.update({k: v for k, v in kw.items() if v is not None})
    return s


def _f1(x):
    return x * x - 2 * x - 1


_V1 = [-3.6, -2.8, 8.0, 12.0]
FIG1 = figure_geom(
    view=_V1, axes=True,
    points=[pt(3, _f1(3), "A(3 ; 2)", reveal=2), pt(4, 7, "B(4 ; 7)", reveal=3)],
    curves=curve(_f1, -3.0, 3.0, _V1, tooltip="Courbe de f(x) = x² − 2x − 1 sur [−3 ; 3]"),
    segments=[_s((3, 0), (3, 2), dashed=True, reveal=2), _s((0, 2), (3, 2), dashed=True, reveal=2)],
    texts=[text((-2.0, 8.6), "f définie sur [−3 ; 3]"), text((4.0, 8.0), "4 ∉ [−3 ; 3]", reveal=3)],
    steps=["La courbe de f sur son ensemble de définition", "A(3 ; 2) : f(3) = 2, A est sur la courbe", "B(4 ; 7) : 4 n'est pas dans [−3 ; 3], B n'est pas sur la courbe"],
    relation="$M(x ; y) \\in \\mathcal{C}_f \\iff x \\in D$ et $y = f(x)$",
    alt="Courbe de f(x) = x² − 2x − 1 tracée sur [−3 ; 3] ; le point A(3 ; 2) est sur la courbe car f(3) = 2 ; le point B(4 ; 7) n'y est pas car 4 n'appartient pas à l'ensemble de définition, bien que 4² − 2 × 4 − 1 = 7.",
    explication=explication(
        resume="La courbe représentative d'une fonction $f$ définie sur $D$ est l'ensemble des points $M(x ; y)$ tels que $x \\in D$ et $y = f(x)$ : il faut vérifier les deux conditions.",
        lecture=["La courbe n'est tracée que sur l'ensemble de définition $[-3 ; 3]$.", "Les pointillés indiquent la lecture de l'image de $3$."],
        observations=["$f(3) = 9 - 6 - 1 = 2$ : $A$ est sur la courbe.", "$4^2 - 2 \\times 4 - 1 = 7$, mais $4 \\notin [-3 ; 3]$ : $B$ n'est pas sur la courbe.",
                      "Chaque abscisse de $D$ a une seule image : un seul point de la courbe par abscisse."],
        pieges=["Oublier de vérifier que l'abscisse appartient à l'ensemble de définition."],
        a_retenir=["Un point est sur la courbe si son abscisse est dans $D$ et si $y = f(x)$."],
    ),
)

_V2 = [-0.8, -0.8, 8.6, 8.0]
FIG2 = figure_geom(
    view=_V2, axes=True,
    points=[pt(0, 0, "O"), pt(1, 1, "", reveal=2), pt(4, 2, "(4 ; 2)", reveal=2), pt(2, 4, "(2 ; 4)", reveal=3)],
    curves=(curve(math.sqrt, 0.0, 7.6, _V2, tooltip="y = √x")
            + curve(lambda x: x * x, 0.0, 2.7, _V2, variant="b", reveal=3, tooltip="y = x²")
            + curve(lambda x: x, 0.0, 7.0, _V2, dashed=True, reveal=3, tooltip="droite y = x")),
    texts=[text((6.4, 2.2), "y = √x"), text((2.2, 6.6), "y = x²", reveal=3), text((6.6, 6.0), "y = x", reveal=3)],
    steps=["La courbe de la racine carrée sur [0 ; +∞[", "Elle monte toujours : la fonction est strictement croissante", "Symétrique de la parabole y = x² (x ⩾ 0) par rapport à la droite y = x"],
    relation="$\\sqrt{4} = 2$ et $2^2 = 4$ : $(4 ; 2)$ et $(2 ; 4)$ sont symétriques par rapport à $y = x$",
    alt="Courbe de la fonction racine carrée, partant de l'origine et croissante ; elle passe par (1 ; 1) et (4 ; 2). La parabole y = x² pour x ⩾ 0 et la droite y = x sont tracées : les deux courbes sont symétriques par rapport à cette droite.",
    explication=explication(
        resume="La fonction racine carrée est définie sur $[0 ; +\\infty[$ et strictement croissante. Sa courbe est la symétrique, par rapport à la droite $y = x$, de la demi-parabole $y = x^2$ ($x \\geqslant 0$).",
        lecture=["La courbe commence à l'origine : $\\sqrt{0} = 0$.", "Elle monte de moins en moins vite."],
        observations=["$\\sqrt{1} = 1$, $\\sqrt{4} = 2$ : les valeurs restent positives.", "Le point $(4 ; 2)$ de la courbe de $\\sqrt{x}$ correspond au point $(2 ; 4)$ de la parabole.",
                      "Pour $x$ entre $0$ et $1$, $\\sqrt{x} \\geqslant x$ ; pour $x \\geqslant 1$, $\\sqrt{x} \\leqslant x$."],
        pieges=["Chercher la racine carrée d'un nombre négatif : elle n'existe pas dans $\\mathbb{R}$."],
        a_retenir=["$\\sqrt{x}$ : définie et positive sur $[0 ; +\\infty[$, strictement croissante."],
    ),
)


def _cube(x):
    return x ** 3


_V3 = [-2.6, -4.2, 5.2, 8.4]
FIG3 = figure_geom(
    view=_V3, axes=True,
    points=[pt(0, 0, "O"), pt(1.5, _cube(1.5), "M(1,5 ; 3,375)", reveal=2), pt(-1.5, _cube(-1.5), "M'(−1,5 ; −3,375)", reveal=3)],
    curves=curve(_cube, -1.65, 1.65, _V3, tooltip="y = x³"),
    segments=[_s((-1.5, _cube(-1.5)), (1.5, _cube(1.5)), dashed=True, reveal=3, tooltip="O est le milieu de [MM']")],
    texts=[text((1.2, 1.0), "y = x³")],
    steps=["La courbe de la fonction cube", "Un point M de la courbe", "Son symétrique par rapport à O est aussi sur la courbe : (−x)³ = −x³"],
    relation="$(-x)^3 = -x^3$ : la courbe est symétrique par rapport à l'origine",
    alt="Courbe de la fonction cube, strictement croissante, passant par l'origine ; le point M(1,5 ; 3,375) et son symétrique M'(−1,5 ; −3,375) par rapport à l'origine sont tous deux sur la courbe.",
    explication=explication(
        resume="La fonction cube est strictement croissante sur $\\mathbb{R}$ ; $x^3$ a le signe de $x$. Deux nombres opposés ont des cubes opposés : la courbe est symétrique par rapport à l'origine.",
        lecture=["La courbe passe par l'origine et monte sur tout $\\mathbb{R}$.", "Elle est très « plate » près de $0$."],
        observations=["$1{,}5^3 = 3{,}375$ et $(-1{,}5)^3 = -3{,}375$.", "$O$ est le milieu de $[MM']$.", "$x^3 < 0$ pour $x < 0$, $x^3 > 0$ pour $x > 0$."],
        pieges=["Croire que $x^3$ est toujours positif, comme $x^2$."],
        a_retenir=["$x^3$ a le même signe que $x$ ; courbe symétrique par rapport à $O$."],
    ),
)


NOTION_1 = notion(
    id=ID1, title=N1,
    intro="On reprend les notions de base sur les fonctions vues en Seconde : image, antécédents, sens de variation et courbe représentative. Elles servent dans tous les chapitres d'analyse de l'année.",
    pourquoi="Lire une courbe, comparer des images grâce au sens de variation ou vérifier qu'un point est sur une courbe sont des gestes que l'on utilise constamment, de l'étude du second degré à la dérivation.",
    objectif="À la fin de ce cours, tu sauras calculer une image, chercher des antécédents, utiliser les définitions de fonction croissante ou décroissante pour comparer des images, et décider si un point appartient à une courbe.",
    definition="Une fonction $f$ définie sur une partie $D$ de $\\mathbb{R}$ associe à tout réel $x$ de $D$ un unique réel $f(x)$, appelé image de $x$ ; un antécédent d'un réel $y$ est un réel $x$ de $D$ tel que $f(x) = y$. Soit $I$ un intervalle inclus dans $D$ : $f$ est croissante sur $I$ si pour tous $a < b$ de $I$, $f(a) \\leqslant f(b)$ ; strictement croissante si $f(a) < f(b)$ ; décroissante si $f(a) \\geqslant f(b)$ ; strictement décroissante si $f(a) > f(b)$. Une fonction croissante ou décroissante sur $I$ est dite monotone sur $I$. La courbe représentative de $f$ est l'ensemble des points $M(x ; y)$ tels que $x \\in D$ et $y = f(x)$.",
    explication_simple="Pour $f(x) = x^2 - 3x$ : l'image de $-2$ est $f(-2) = 4 + 6 = 10$. Si $f$ est strictement croissante sur $[0 ; 5]$, alors $f(1) < f(4)$ sans aucun calcul.",
    intuition="Une fonction croissante « conserve l'ordre » : si $a < b$, alors $f(a) \\leqslant f(b)$ ; une fonction décroissante « renverse l'ordre ».",
    regles=[
        "Image : chaque $x$ de $D$ a une seule image $f(x)$ ; un réel peut avoir zéro, un ou plusieurs antécédents.",
        "Strictement croissante sur $I$ : pour tous $a < b$ de $I$, $f(a) < f(b)$ (l'ordre est conservé).",
        "Strictement décroissante sur $I$ : pour tous $a < b$ de $I$, $f(a) > f(b)$ (l'ordre est renversé).",
        "Un point $M(x ; y)$ est sur la courbe de $f$ si et seulement si $x \\in D$ et $y = f(x)$.",
        "Sur un intervalle où $f$ est strictement monotone, une valeur est atteinte au plus une fois.",
    ],
    formules=[
        formule("formule-croissante", "Croissante", "$a < b \\Rightarrow f(a) \\leqslant f(b)$", "Pour comparer des images.", "Oublier que c'est sur un intervalle.", "L'ordre des images suit l'ordre des antécédents."),
        formule("formule-courbe", "Point de la courbe", "$M(x ; y) \\in \\mathcal{C}_f \\iff x \\in D \\text{ et } y = f(x)$", "Pour tester l'appartenance d'un point.", "Oublier la condition $x \\in D$.", "Deux conditions à vérifier."),
    ],
    methode_titre="Méthode — Utiliser une fonction et sa courbe",
    etapes=[
        step("search", "blue", "Je repère l'ensemble de définition $D$ et l'expression (ou la courbe) de $f$."),
        step("layers", "purple", "Image : je remplace $x$ ; antécédents : je résous $f(x) = y$."),
        step("target", "orange", "Comparaison : j'utilise le sens de variation sur l'intervalle concerné."),
        step("check", "green", "Point de la courbe : je vérifie $x \\in D$ et $y = f(x)$."),
    ],
    debutant=[
        step("search", "blue", "Je regarde sur quel ensemble $f$ est définie."),
        step("layers", "purple", "Je remplace $x$ par la valeur, avec des parenthèses."),
        step("target", "orange", "Pour comparer, je regarde si la fonction monte ou descend."),
        step("check", "green", "Je vérifie mon résultat sur la courbe."),
    ],
    rapide=[step("layers", "purple", "Image, antécédents, sens de variation."), step("check", "green", "$x \\in D$ et $y = f(x)$.")],
    exemples=[
        ex("exemple-auto-image", "Exemple 1 — Image",
           "$f(x) = x^2 - 3x$. Calculer l'image de $-2$.", [calc("f(-2) = (-2)^2 - 3 \\times (-2) = 4 + 6")], "$f(-2) = 10$.", "facile", "free",
           conclusion="Parenthèses autour des nombres négatifs."),
        ex("exemple-auto-antecedents", "Exemple 2 — Antécédents",
           "Quels sont les antécédents de $4$ par la fonction carré ?", [calc("$x^2 = 4$ équivaut à $x = 2$ ou $x = -2$.")], "$-2$ et $2$.", "facile", "free",
           conclusion="Un réel peut avoir plusieurs antécédents."),
        ex("exemple-point-courbe", "Exemple 3 — Un point est-il sur la courbe ?",
           "$f$ est définie sur $[-3 ; 3]$ par $f(x) = x^2 - 2x - 1$. Les points $A(3 ; 2)$ et $B(4 ; 7)$ sont-ils sur sa courbe ?",
           [calc("$3 \\in [-3 ; 3]$ et $f(3) = 9 - 6 - 1 = 2$ : $A$ est sur la courbe."), calc("$4 \\notin [-3 ; 3]$ : $B$ n'est pas sur la courbe.")],
           "$A$ est sur la courbe, $B$ non.", "moyen", "premium", conclusion="C'est la figure du cours : la condition $x \\in D$ compte."),
        ex("exemple-comparer-images", "Exemple 4 — Comparer des images",
           "$f$ est strictement décroissante sur $[0 ; 5]$. Comparer $f(1{,}3)$ et $f(2{,}7)$.",
           [calc("$1{,}3 < 2{,}7$, et ces deux nombres sont dans $[0 ; 5]$."), calc("$f$ renverse l'ordre : $f(1{,}3) > f(2{,}7)$.")],
           "$f(1{,}3) > f(2{,}7)$.", "moyen", "premium", conclusion="Le sens de variation suffit, sans connaître $f$."),
        ex("exemple-auto-variations", "Exemple 5 — Nombre de solutions",
           "$f$ croît de $-3$ à $5$ sur $[-2 ; 1]$ puis décroît jusqu'à $0$ sur $[1 ; 4]$. Combien de solutions l'équation $f(x) = 2$ a-t-elle ?",
           [calc("$2$ est atteint une fois sur $[-2 ; 1]$ (entre $-3$ et $5$) et une fois sur $[1 ; 4]$ (entre $5$ et $0$).")],
           "$2$ solutions.", "moyen", "premium", conclusion="On compte intervalle par intervalle."),
        ex("exemple-prouver-decroissance", "Exemple 6 — Démontrer un sens de variation",
           "Démontrer que $g(x) = -2x + 3$ est strictement décroissante sur $\\mathbb{R}$.",
           [calc("Soient $a < b$. $g(a) - g(b) = -2a + 3 + 2b - 3 = 2(b - a)$."), calc("$b - a > 0$, donc $g(a) - g(b) > 0$, soit $g(a) > g(b)$.")],
           "$g$ est strictement décroissante sur $\\mathbb{R}$.", "difficile", "ultra",
           conclusion="On étudie le signe de $g(a) - g(b)$ : c'est la définition qui sert de preuve."),
    ],
    erreurs=[
        ("Écrire $-2^2 = 4$.", "Priorité du carré.", "Le signe moins est-il dans la parenthèse ?", "$(-2)^2 = 4$ mais $-2^2 = -4$."),
        ("Confondre image et antécédent.", "Sens de lecture.", "Te donne-t-on $x$ ou $y$ ?", "Image : $f(x)$ ; antécédent : $x$."),
        ("Comparer des images avec le sens de variation hors de l'intervalle.", "On oublie l'intervalle.", "Les deux nombres sont-ils dans le même intervalle de monotonie ?", "Le sens de variation ne vaut que sur l'intervalle."),
        ("Oublier l'ensemble de définition pour un point de la courbe.", "On ne vérifie que $y = f(x)$.", "L'abscisse est-elle dans $D$ ?", "Deux conditions."),
    ],
    astuce="Pour comparer deux images, demande-toi d'abord : les deux nombres sont-ils dans un même intervalle où $f$ est monotone ? Si oui, le sens de variation suffit.",
    a_retenir=["Rappels sur les fonctions : image unique, antécédents éventuellement multiples.", "Croissante : conserve l'ordre ; décroissante : le renverse.",
               "Point de la courbe : $x \\in D$ et $y = f(x)$."],
    exemples_concrets=["Lire un graphique de températures.", "Comparer deux tarifs sans tout calculer.", "Vérifier une valeur sur un relevé."],
    figure=FIG1,
    quiz=(73301, 73303, 82101),
    prerequis=["Fonctions (Seconde)"],
    notions_liees=[ID2, ID3],
    objectifs=["Calculer images et antécédents.", "Utiliser le sens de variation pour comparer.", "Tester l'appartenance d'un point à une courbe."],
    vocabulaire=["fonction", "image", "antécédent", "croissante", "décroissante", "monotone", "courbe représentative"],
    synonymes=["image d'un nombre", "antécédent", "fonction croissante", "fonction décroissante", "courbe représentative", "point sur une courbe"],
    proprietes=["Chaque nombre de l'ensemble de définition a une seule image."],
    tags=["fonctions"],
    difficulte="facile",
    apercu_premium=("Point de la courbe, comparaison d'images, nombre de solutions",
                    "Trois exemples rédigés : appartenance d'un point à une courbe, comparaison d'images par le sens de variation, nombre de solutions."),
    apercu_ultra=("Démontrer un sens de variation, démonstration",
                  "Prouver la décroissance d'une fonction affine par la définition, et la décroissance de la fonction carré sur $]-\\infty ; 0]$."),
    questions_eclair=[("figure", "Le point $(0 ; -1)$ est-il sur la courbe de la figure ?", "Oui : $f(0) = -1$ et $0 \\in [-3 ; 3]$."),
                      ("methode", "$f$ croissante, $a < b$ : comparer $f(a)$ et $f(b)$.", "$f(a) \\leqslant f(b)$.")],
    demonstration=demonstration(
        "La fonction carré est strictement décroissante sur $]-\\infty ; 0]$",
        [("Choix", "Soient $a < b \\leqslant 0$."),
         ("Factorisation", "$a^2 - b^2 = (a - b)(a + b)$."),
         ("Signes", "$a - b < 0$ et $a + b < 0$ (deux nombres négatifs, dont au moins un non nul) : le produit est strictement positif."),
         ("Conclusion", "$a^2 > b^2$ : la fonction carré renverse l'ordre sur $]-\\infty ; 0]$.")],
        "La définition du sens de variation se démontre en étudiant le signe d'une différence.",
    ),
)

NOTION_2 = notion(
    id=ID2, title=N2,
    intro="La fonction racine carrée associe à tout nombre positif le nombre positif dont il est le carré. C'est une nouvelle fonction de référence, liée à la fonction carré.",
    pourquoi="La racine carrée apparaît dans les longueurs (Pythagore), les formules du second degré ($\\sqrt{\\Delta}$) et les dérivées ($\\dfrac{1}{2\\sqrt{x}}$). Connaître sa courbe et son sens de variation permet de comparer et de résoudre sans calculatrice.",
    objectif="À la fin de ce cours, tu connaîtras l'ensemble de définition, le sens de variation et la courbe de la fonction racine carrée, et tu sauras comparer des racines carrées et résoudre des équations ou inéquations simples.",
    definition="La fonction racine carrée est la fonction $f$ définie sur $[0 ; +\\infty[$ par $f(x) = \\sqrt{x}$, où $\\sqrt{x}$ est l'unique nombre positif dont le carré vaut $x$. Elle n'est définie que pour $x \\geqslant 0$, et $\\sqrt{x} \\geqslant 0$. Elle est strictement croissante sur $[0 ; +\\infty[$. Dans un repère orthonormé, sa courbe est symétrique de la courbe de $x \\mapsto x^2$ sur $[0 ; +\\infty[$ par rapport à la droite d'équation $y = x$ (les fonctions carré et racine carrée sont réciproques l'une de l'autre sur $[0 ; +\\infty[$).",
    explication_simple="$\\sqrt{9} = 3$ car $3 \\geqslant 0$ et $3^2 = 9$. Comme la fonction est croissante, $\\sqrt{2} < \\sqrt{3}$.",
    intuition="La racine carrée « défait » le carré pour les nombres positifs : $\\sqrt{x^2} = x$ si $x \\geqslant 0$.",
    regles=[
        "Ensemble de définition : $[0 ; +\\infty[$ ; une racine carrée est toujours positive ou nulle.",
        "Pour $x \\geqslant 0$ : $(\\sqrt{x})^2 = x$ et $\\sqrt{x^2} = x$.",
        "Strictement croissante : pour $0 \\leqslant a < b$, $\\sqrt{a} < \\sqrt{b}$.",
        "Pour $a \\geqslant 0$ : $\\sqrt{x} = a \\iff x = a^2$.",
        "Courbe : symétrique de la demi-parabole $y = x^2$ ($x \\geqslant 0$) par rapport à la droite $y = x$.",
    ],
    formules=[
        formule("formule-racine", "Racine carrée", "$\\sqrt{x} \\geqslant 0$ et $(\\sqrt{x})^2 = x$ ($x \\geqslant 0$)", "Pour calculer et simplifier.", "Écrire $\\sqrt{x}$ pour $x < 0$.", "Pas de racine carrée d'un nombre négatif."),
        formule("formule-racine-croissante", "Sens de variation", "$0 \\leqslant a < b \\Rightarrow \\sqrt{a} < \\sqrt{b}$", "Pour comparer des racines.", "Renverser l'ordre.", "La racine conserve l'ordre."),
    ],
    methode_titre="Méthode — Comparer ou résoudre avec la racine carrée",
    etapes=[
        step("search", "blue", "Je vérifie que les nombres sous la racine sont positifs."),
        step("layers", "purple", "Pour comparer, je compare les nombres sous la racine (la fonction est croissante)."),
        step("target", "orange", "Pour résoudre $\\sqrt{x} = a$ ($a \\geqslant 0$), j'élève au carré : $x = a^2$."),
        step("check", "green", "Je contrôle que la solution est dans $[0 ; +\\infty[$."),
    ],
    debutant=[
        step("search", "blue", "Sous la racine, le nombre doit être positif."),
        step("layers", "purple", "Plus le nombre est grand, plus sa racine est grande."),
        step("target", "orange", "$\\sqrt{x} = 3$ : $x = 9$."),
        step("check", "green", "Je vérifie en recalculant la racine."),
    ],
    rapide=[step("layers", "purple", "Croissante sur $[0 ; +\\infty[$."), step("check", "green", "$\\sqrt{x} = a \\iff x = a^2$ ($a \\geqslant 0$).")],
    exemples=[
        ex("exemple-racine-comparer", "Exemple 1 — Comparer sans calculatrice",
           "Comparer $\\sqrt{7}$ et $\\sqrt{11}$, puis $\\sqrt{0{,}49}$ et $0{,}7$.",
           [calc("$7 < 11$ et la fonction racine est croissante : $\\sqrt{7} < \\sqrt{11}$."), calc("$0{,}7^2 = 0{,}49$ et $0{,}7 \\geqslant 0$ : $\\sqrt{0{,}49} = 0{,}7$.")],
           "$\\sqrt{7} < \\sqrt{11}$ ; $\\sqrt{0{,}49} = 0{,}7$.", "facile", "free", conclusion="On compare les nombres sous la racine."),
        ex("exemple-racine-equation", "Exemple 2 — Résoudre $\\sqrt{x} = 3$",
           "Résoudre dans $[0 ; +\\infty[$ l'équation $\\sqrt{x} = 3$, puis l'équation $\\sqrt{x} = -2$.",
           [calc("$3 \\geqslant 0$ : $\\sqrt{x} = 3 \\iff x = 9$."), calc("Une racine carrée est positive : $\\sqrt{x} = -2$ n'a pas de solution.")],
           "$x = 9$ ; pas de solution pour $\\sqrt{x} = -2$.", "facile", "free", conclusion="Penser au signe avant d'élever au carré."),
        ex("exemple-racine-inequation", "Exemple 3 — Une inéquation",
           "Résoudre $\\sqrt{x} \\leqslant 2$.",
           [calc("$x$ doit être dans $[0 ; +\\infty[$."), calc("$2 = \\sqrt{4}$ et la fonction est strictement croissante : $\\sqrt{x} \\leqslant \\sqrt{4} \\iff x \\leqslant 4$.")],
           "$\\mathcal{S} = [0 ; 4]$.", "moyen", "premium", conclusion="Ne pas oublier la condition $x \\geqslant 0$."),
        ex("exemple-racine-ordre", "Exemple 4 — Ranger $x$, $x^2$ et $\\sqrt{x}$",
           "Ranger $0{,}25$, $0{,}25^2$ et $\\sqrt{0{,}25}$ dans l'ordre croissant, puis faire de même pour $4$.",
           [calc("$0{,}25^2 = 0{,}0625$ et $\\sqrt{0{,}25} = 0{,}5$ : $0{,}0625 < 0{,}25 < 0{,}5$."), calc("$\\sqrt{4} = 2$ et $4^2 = 16$ : $2 < 4 < 16$.")],
           "Entre $0$ et $1$ : $x^2 < x < \\sqrt{x}$ ; au-delà de $1$ : $\\sqrt{x} < x < x^2$.", "moyen", "premium", conclusion="On le voit sur la figure : les courbes se croisent en $(1 ; 1)$."),
        ex("exemple-racine-tableau", "Exemple 5 — Encadrer une racine",
           "Sachant que $2 \\leqslant x \\leqslant 9$, encadrer $\\sqrt{x}$.",
           [calc("La fonction racine est croissante : $\\sqrt{2} \\leqslant \\sqrt{x} \\leqslant \\sqrt{9}$.")],
           "$\\sqrt{2} \\leqslant \\sqrt{x} \\leqslant 3$ (soit environ $1{,}41 \\leqslant \\sqrt{x} \\leqslant 3$).", "moyen", "premium",
           conclusion="Une fonction croissante conserve les encadrements."),
        ex("exemple-racine-symetrie", "Exemple 6 — Pourquoi la symétrie ?",
           "Montrer que si le point $M(a ; b)$ est sur la courbe de la racine carrée, alors $M'(b ; a)$ est sur la parabole $y = x^2$, avec $b \\geqslant 0$.",
           [calc("$M$ sur la courbe : $a \\geqslant 0$ et $b = \\sqrt{a}$, donc $b \\geqslant 0$ et $b^2 = a$."),
            calc("Le point $M'(b ; a)$ vérifie donc $a = b^2$ : il est sur la parabole $y = x^2$, avec une abscisse positive.")],
           "$M'$ est sur la demi-parabole ; $M$ et $M'$ sont symétriques par rapport à la droite $y = x$.", "difficile", "ultra",
           conclusion="Échanger abscisse et ordonnée, c'est appliquer la symétrie par rapport à $y = x$."),
    ],
    erreurs=[
        ("Calculer la racine carrée d'un nombre négatif.", "On oublie l'ensemble de définition.", "Le nombre sous la racine est-il positif ?", "$\\sqrt{x}$ n'existe que pour $x \\geqslant 0$."),
        ("Écrire $\\sqrt{x^2} = x$ pour tout $x$.", "On oublie le signe.", "Que vaut $\\sqrt{(-3)^2}$ ?", "$\\sqrt{9} = 3$ : l'égalité $\\sqrt{x^2} = x$ n'est vraie que pour $x \\geqslant 0$."),
        ("Écrire $\\sqrt{a + b} = \\sqrt{a} + \\sqrt{b}$.", "Fausse règle de calcul.", "Teste avec $a = 9$ et $b = 16$.", "$\\sqrt{25} = 5$ mais $3 + 4 = 7$."),
        ("Résoudre $\\sqrt{x} = -2$ par $x = 4$.", "On élève au carré sans réfléchir.", "Une racine carrée peut-elle être négative ?", "Pas de solution."),
    ],
    astuce="Pour vérifier $\\sqrt{x} = a$, contrôle deux choses : $a \\geqslant 0$ et $a^2 = x$.",
    a_retenir=["Fonction racine carrée : définie sur $[0 ; +\\infty[$, positive, strictement croissante.", "Courbe symétrique de $y = x^2$ ($x \\geqslant 0$) par rapport à $y = x$.",
               "$\\sqrt{x} = a \\iff x = a^2$ si $a \\geqslant 0$."],
    exemples_concrets=["Côté d'un carré d'aire donnée.", "Distance de freinage et vitesse.", "Diagonale d'un écran."],
    figure=FIG2,
    quiz=(82201, 82202, 82203),
    prerequis=["Rappels sur les fonctions", "Fonction carré (Seconde)"],
    notions_liees=[ID1, ID3],
    objectifs=["Connaître la courbe et les variations de la racine carrée.", "Comparer des racines carrées.", "Résoudre $\\sqrt{x} = a$ et $\\sqrt{x} \\leqslant a$."],
    vocabulaire=["racine carrée", "ensemble de définition", "strictement croissante", "symétrie"],
    synonymes=["fonction racine carrée", "racine carrée", "courbe de racine de x", "racine carrée croissante"],
    proprietes=["La fonction racine carrée est strictement croissante sur $[0 ; +\\infty[$."],
    tags=["fonctions de référence", "racine carrée"],
    difficulte="facile",
    apercu_premium=("Inéquation, ordre de $x$, $x^2$, $\\sqrt{x}$, encadrement",
                    "Trois exemples rédigés : résoudre $\\sqrt{x} \\leqslant 2$, ranger $x$, $x^2$ et $\\sqrt{x}$, encadrer une racine carrée."),
    apercu_ultra=("Symétrie des courbes, démonstration",
                  "Pourquoi la courbe de la racine est symétrique de la parabole, et la démonstration de la croissance de la racine carrée."),
    questions_eclair=[("figure", "Par quel point passent les trois courbes de la figure, à part l'origine ?", "$(1 ; 1)$."),
                      ("methode", "Résoudre $\\sqrt{x} = 5$.", "$x = 25$.")],
    demonstration=demonstration(
        "La fonction racine carrée est strictement croissante sur $[0 ; +\\infty[$",
        [("Choix", "Soient $0 \\leqslant a < b$ ; alors $\\sqrt{a} + \\sqrt{b} > 0$ (car $\\sqrt{b} > 0$)."),
         ("Quantité conjuguée", "$\\sqrt{b} - \\sqrt{a} = \\dfrac{(\\sqrt{b} - \\sqrt{a})(\\sqrt{b} + \\sqrt{a})}{\\sqrt{b} + \\sqrt{a}} = \\dfrac{b - a}{\\sqrt{b} + \\sqrt{a}}$."),
         ("Signe", "$b - a > 0$ et $\\sqrt{b} + \\sqrt{a} > 0$, donc $\\sqrt{b} - \\sqrt{a} > 0$."),
         ("Conclusion", "$\\sqrt{a} < \\sqrt{b}$ : la fonction conserve l'ordre.")],
        "Multiplier par la quantité conjuguée fait apparaître $b - a$, dont on connaît le signe.",
    ),
)

NOTION_3 = notion(
    id=ID3, title=N3,
    intro="La fonction cube associe à tout réel $x$ son cube $x^3$. Contrairement au carré, un cube peut être négatif : la fonction cube est croissante sur tout $\\mathbb{R}$.",
    pourquoi="Les volumes varient comme le cube des longueurs ; la fonction cube est aussi l'exemple type d'une fonction strictement croissante dont la dérivée s'annule (chapitre 6).",
    objectif="À la fin de ce cours, tu connaîtras le sens de variation, le signe et la courbe de la fonction cube, et tu sauras comparer des cubes et résoudre des équations et inéquations simples.",
    definition="La fonction cube est la fonction $f$ définie sur $\\mathbb{R}$ par $f(x) = x^3$. Elle est strictement croissante sur $\\mathbb{R}$. Son signe : $x^3 < 0 \\iff x < 0$, $x^3 > 0 \\iff x > 0$ et $x^3 = 0 \\iff x = 0$. Pour tout réel $x$, $(-x)^3 = -x^3$ : deux nombres opposés ont des images opposées, donc la courbe de la fonction cube est symétrique par rapport à l'origine du repère.",
    explication_simple="$2^3 = 8$ et $(-2)^3 = -8$ : des cubes opposés. Comme la fonction est croissante, $(-3)^3 < (-2)^3$, c'est-à-dire $-27 < -8$.",
    intuition="Le cube conserve l'ordre ET le signe : plus le nombre est grand, plus son cube est grand, sur tout $\\mathbb{R}$.",
    regles=[
        "Strictement croissante sur $\\mathbb{R}$ : pour tous réels $a < b$, $a^3 < b^3$.",
        "Signe : $x^3$ a le même signe que $x$.",
        "Symétrie : $(-x)^3 = -x^3$ ; la courbe est symétrique par rapport à l'origine.",
        "Équation : pour tout réel $k$, l'équation $x^3 = k$ a une unique solution.",
        "Inéquation : $x^3 < a^3 \\iff x < a$.",
    ],
    formules=[
        formule("formule-cube-oppose", "Cube d'un opposé", "$(-x)^3 = -x^3$", "Pour calculer le cube d'un négatif.", "Croire que $(-x)^3$ est positif.", "Un nombre impair de facteurs négatifs donne un résultat négatif."),
        formule("formule-cube-croissante", "Sens de variation", "$a < b \\iff a^3 < b^3$", "Pour comparer ou résoudre.", "Renverser l'ordre pour les négatifs.", "Le cube conserve l'ordre sur tout $\\mathbb{R}$."),
    ],
    methode_titre="Méthode — Comparer et résoudre avec la fonction cube",
    etapes=[
        step("search", "blue", "Je repère les nombres à comparer, ou j'écris le second membre comme un cube."),
        step("layers", "purple", "J'utilise la croissance stricte : l'ordre des cubes est celui des nombres."),
        step("target", "orange", "Pour $x^3 = a^3$, l'unique solution est $x = a$."),
        step("check", "green", "Je contrôle le signe : $x^3$ et $x$ ont le même signe."),
    ],
    debutant=[
        step("search", "blue", "Je calcule le cube : le nombre multiplié trois fois par lui-même."),
        step("layers", "purple", "Un nombre négatif a un cube négatif."),
        step("target", "orange", "Plus le nombre est grand, plus son cube est grand."),
        step("check", "green", "Je vérifie avec la courbe."),
    ],
    rapide=[step("layers", "purple", "Croissante sur $\\mathbb{R}$, même signe que $x$."), step("check", "green", "$(-x)^3 = -x^3$.")],
    exemples=[
        ex("exemple-cube-calcul", "Exemple 1 — Calculer des cubes",
           "Calculer $(-2)^3$, $0{,}5^3$ et $(-0{,}1)^3$.",
           [calc("(-2)^3 = -8 \\quad 0{,}5^3 = 0{,}125 \\quad (-0{,}1)^3 = -0{,}001")],
           "$-8$ ; $0{,}125$ ; $-0{,}001$.", "facile", "free", conclusion="Le cube d'un négatif est négatif."),
        ex("exemple-cube-comparer", "Exemple 2 — Comparer sans calculer",
           "Comparer $(-1{,}5)^3$ et $(-1{,}4)^3$.",
           [calc("$-1{,}5 < -1{,}4$ et la fonction cube est strictement croissante.")],
           "$(-1{,}5)^3 < (-1{,}4)^3$.", "facile", "free", conclusion="Contrairement au carré, le cube conserve l'ordre même pour les négatifs."),
        ex("exemple-cube-equation", "Exemple 3 — Résoudre $x^3 = -8$",
           "Résoudre dans $\\mathbb{R}$ l'équation $x^3 = -8$.",
           [calc("$-8 = (-2)^3$."), calc("La fonction cube est strictement croissante : la seule solution est $x = -2$.")],
           "$\\mathcal{S} = \\{-2\\}$.", "moyen", "premium", conclusion="Une seule solution, contrairement à $x^2 = 4$."),
        ex("exemple-cube-inequation", "Exemple 4 — Une inéquation",
           "Résoudre $x^3 > 27$.",
           [calc("$27 = 3^3$, et la fonction cube est strictement croissante : $x^3 > 3^3 \\iff x > 3$.")],
           "$\\mathcal{S} = ]3 ; +\\infty[$.", "moyen", "premium", conclusion="On compare les nombres, puisque le cube conserve l'ordre."),
        ex("exemple-cube-signe", "Exemple 5 — Étudier un signe",
           "Dresser le tableau de signes de $x^3$ sur $\\mathbb{R}$, puis donner le signe de $(x - 1)^3$.",
           [calc("$x^3 < 0$ pour $x < 0$, $x^3 = 0$ en $0$, $x^3 > 0$ pour $x > 0$."), calc("$(x - 1)^3$ a le signe de $x - 1$ : négatif pour $x < 1$, positif pour $x > 1$.")],
           "$x^3$ a le signe de $x$ ; $(x - 1)^3$ celui de $x - 1$.", "moyen", "premium", conclusion="Le cube ne change pas le signe."),
        ex("exemple-cube-symetrie", "Exemple 6 — Symétrie de la courbe",
           "Le point $M(1{,}2 ; 1{,}728)$ est sur la courbe de la fonction cube. Justifier que son symétrique par rapport à l'origine y est aussi.",
           [calc("Le symétrique de $M$ par rapport à $O$ est $M'(-1{,}2 ; -1{,}728)$."), calc("$(-1{,}2)^3 = -1{,}2^3 = -1{,}728$ : $M'$ est sur la courbe.")],
           "$M'(-1{,}2 ; -1{,}728)$ est sur la courbe.", "difficile", "ultra",
           conclusion="C'est vrai pour tout point : $(-x)^3 = -x^3$."),
    ],
    erreurs=[
        ("Croire que $x^3$ est toujours positif.", "Confusion avec le carré.", "Que vaut $(-1)^3$ ?", "$x^3$ a le signe de $x$."),
        ("Trouver deux solutions à $x^3 = 8$.", "Confusion avec $x^2 = 4$.", "La fonction cube est-elle strictement croissante ?", "Une seule solution : $2$."),
        ("Écrire $(-2)^3 = -6$.", "On multiplie par $3$ au lieu d'élever au cube.", "Que signifie l'exposant $3$ ?", "$(-2)^3 = (-2) \\times (-2) \\times (-2) = -8$."),
        ("Renverser l'ordre pour les négatifs.", "Réflexe du carré.", "La fonction cube est-elle croissante sur $]-\\infty ; 0]$ ?", "Oui : l'ordre est conservé."),
    ],
    astuce="Pour un négatif, calcule le cube de son opposé puis change le signe : $(-3)^3 = -(3^3) = -27$.",
    a_retenir=["Fonction cube : strictement croissante sur $\\mathbb{R}$.", "$x^3$ a le même signe que $x$.", "Courbe symétrique par rapport à l'origine : $(-x)^3 = -x^3$."],
    exemples_concrets=["Volume d'un cube d'arête $x$.", "Comparer des volumes d'objets semblables.", "Modèles de croissance rapide."],
    figure=FIG3,
    quiz=(82301, 82302, 82303),
    prerequis=["Rappels sur les fonctions", "Puissances"],
    notions_liees=[ID1, ID2],
    objectifs=["Connaître la courbe et les variations de la fonction cube.", "Utiliser le signe de $x^3$.", "Résoudre $x^3 = k$ et $x^3 < a^3$."],
    vocabulaire=["cube", "strictement croissante", "signe", "symétrie par rapport à l'origine"],
    synonymes=["fonction cube", "x au cube", "courbe de x³", "signe de x³"],
    proprietes=["La fonction cube est strictement croissante sur $\\mathbb{R}$.", "$(-x)^3 = -x^3$."],
    tags=["fonctions de référence", "cube"],
    difficulte="facile",
    apercu_premium=("Équation, inéquation, signe",
                    "Trois exemples rédigés : résoudre $x^3 = -8$, résoudre $x^3 > 27$, étudier le signe de $(x - 1)^3$."),
    apercu_ultra=("Symétrie de la courbe, démonstration",
                  "La symétrie de la courbe par rapport à l'origine, et la démonstration de la croissance de la fonction cube."),
    questions_eclair=[("figure", "Quel est le symétrique du point $(1 ; 1)$ sur la courbe ?", "$(-1 ; -1)$."),
                      ("methode", "Signe de $(-0{,}3)^3$ ?", "Négatif.")],
    demonstration=demonstration(
        "La fonction cube est strictement croissante sur $\\mathbb{R}$",
        [("Factorisation", "Pour tous réels $a$ et $b$ : $b^3 - a^3 = (b - a)(a^2 + ab + b^2)$."),
         ("Second facteur", "$a^2 + ab + b^2 = \\left(a + \\dfrac{b}{2}\\right)^2 + \\dfrac{3b^2}{4}$ : c'est une somme de deux carrés, nulle seulement si $a = b = 0$."),
         ("Signe", "Si $a < b$, alors $b - a > 0$ et $a$, $b$ ne sont pas tous deux nuls, donc $a^2 + ab + b^2 > 0$."),
         ("Conclusion", "$b^3 - a^3 > 0$, c'est-à-dire $a^3 < b^3$.")],
        "Une factorisation et une forme canonique suffisent à établir la croissance.",
    ),
)

CHAPTER = chapter(2, "Fonctions numériques", "layers", [NOTION_1, NOTION_2, NOTION_3])
