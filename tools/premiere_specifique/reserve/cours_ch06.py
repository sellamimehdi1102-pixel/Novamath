"""Chapitre 6 — Trigonométrie.

Programme 2026 : cercle trigonométrique, longueur d'arc, radian ;
enroulement de la droite sur le cercle, image d'un réel ; cosinus et sinus
d'un réel, lien avec le triangle rectangle, valeurs remarquables. Capacités :
placer un point ; par lecture du cercle, déterminer les cosinus et sinus
d'angles associés à x. Démonstration : cos et sin de π/4 et π/3. Algorithme :
approximation de π par la méthode d'Archimède.

Les FONCTIONS cosinus et sinus (parité, périodicité, courbes) ne sont plus au
programme de Première : la notion « Fonctions cosinus et sinus » est retirée
(NOTIONS_RETIREES) ; ses exercices sont rattachés à la nouvelle notion
« Angles associés et lecture du cercle » (banque_ch06.py) et les familles du
générateur aux notions au programme (trigonometrie.py).
"""
import math

from premiere_specifique.cours_commun import (
    calc, chapter, code, demonstration, ex, explication, figure_geom, formule, notion, pt, step, text,
)

NOTIONS_RETIREES = {
    "fonctions-cosinus-et-sinus":
        "Programme 2026 : les fonctions cosinus et sinus (parité, périodicité, courbes) ne sont plus au programme de Première ; "
        "les valeurs et la lecture du cercle restent (notions « Coordonnées… » et « Angles associés et lecture du cercle »).",
}

N1, N2, N3 = ("Repérage sur le cercle trigonométrique", "Coordonnées d'un point du cercle trigonométrique",
              "Angles associés et lecture du cercle")
ID1, ID2, ID3 = ("reperage-sur-le-cercle-trigonometrique", "coordonnees-d-un-point-du-cercle-trigonometrique",
                 "angles-associes-et-lecture-du-cercle")

R3 = math.sqrt(3) / 2
R2 = math.sqrt(2) / 2
_V = [-1.55, -1.45, 3.1, 2.9]
_CERCLE = [{"center": {"x": 0, "y": 0}, "radius": 1}]


def _p(deg, label, **kw):
    t = math.radians(deg)
    return pt(round(math.cos(t), 4), round(math.sin(t), 4), label, **kw)


def _seg(a, b, **kw):
    s = {"from": {"x": a[0], "y": a[1]}, "to": {"x": b[0], "y": b[1]}}
    s.update({k: v for k, v in kw.items() if v is not None})
    return s


FIG1 = figure_geom(
    view=_V, axes=True, circles=_CERCLE,
    points=[pt(1, 0, "I(1 ; 0)"), _p(90, "π/2", reveal=2), _p(180, "π", reveal=2), _p(270, "−π/2 et 3π/2", reveal=2),
            _p(60, "π/3 et 7π/3", reveal=3)],
    arcs=[{"center": {"x": 0, "y": 0}, "radius": 0.3, "startDeg": 0, "endDeg": 60, "label": "π/3", "reveal": 3}],
    segments=[_seg((0, 0), (0.5, R3), reveal=3, tooltip="rayon 1")],
    steps=["Le cercle trigonométrique : rayon 1, origine I", "Quarts de tour : π/2, π, 3π/2", "Un tour de plus (2π) : même point"],
    relation="Le réel $x$ a pour image le point $M$ tel que l'arc $\\overset{\\frown}{IM}$ mesure $|x|$ (sens direct si $x > 0$)",
    alt="Cercle trigonométrique de centre O et de rayon 1, avec le point I(1 ; 0), les points images de π/2, π et −π/2 (qui est aussi celle de 3π/2), et le point image de π/3, qui est aussi celle de 7π/3.",
    explication=explication(
        resume="On enroule la droite des réels sur le cercle de rayon $1$, en partant de $I$ : chaque réel $x$ a un point image. Un tour complet mesure $2\\pi$, donc $x$ et $x + 2\\pi$ ont la même image.",
        lecture=["Le sens direct (inverse des aiguilles d'une montre) correspond aux réels positifs.", "Un quart de tour mesure $\\dfrac{\\pi}{2}$, un demi-tour $\\pi$."],
        observations=["$-\\dfrac{\\pi}{2}$ et $\\dfrac{3\\pi}{2}$ diffèrent de $2\\pi$ : même point.", "$\\dfrac{7\\pi}{3} = \\dfrac{\\pi}{3} + 2\\pi$ : même point que $\\dfrac{\\pi}{3}$.",
                      "Sur ce cercle, la longueur d'un arc est égale à la mesure de l'angle en radians."],
        pieges=["Croire qu'un point correspond à un seul réel : il en a une infinité ($x + 2k\\pi$)."],
        a_retenir=["$x$ et $x + 2k\\pi$ ($k$ entier) ont le même point image."],
    ),
)

FIG2 = figure_geom(
    view=_V, axes=True, circles=_CERCLE,
    points=[pt(0, 0, "O"), _p(60, "M", tooltip="M(cos(π/3) ; sin(π/3))"), pt(0.5, 0, "H", reveal=2), pt(0, R3, "K", reveal=2)],
    arcs=[{"center": {"x": 0, "y": 0}, "radius": 0.3, "startDeg": 0, "endDeg": 60, "label": "x"}],
    segments=[_seg((0, 0), (0.5, R3), tooltip="OM = 1"), _seg((0.5, R3), (0.5, 0), reveal=2, tooltip="sin x = HM"),
              _seg((0.5, R3), (0, R3), reveal=2, tooltip="cos x = KM"), _seg((0, 0), (0.5, 0), reveal=3, tooltip="OH = cos x")],
    texts=[text((0.25, -0.18), "cos x", reveal=2), text((0.78, 0.43), "sin x", reveal=2), text((0.95, -1.15), "cos²x + sin²x = 1", reveal=3)],
    steps=["Le point M image de x", "Ses coordonnées : (cos x ; sin x)", "Triangle rectangle OHM : Pythagore"],
    relation="$M(\\cos x ; \\sin x)$ et $\\cos^2 x + \\sin^2 x = 1$",
    alt="Point M du cercle trigonométrique image de x = π/3, projeté en H sur l'axe des abscisses et en K sur l'axe des ordonnées : OH = cos x et HM = sin x ; le triangle OHM est rectangle en H avec OM = 1.",
    explication=explication(
        resume="Le cosinus et le sinus d'un réel $x$ sont l'abscisse et l'ordonnée de son point image $M$. Dans le triangle rectangle $OHM$ d'hypoténuse $1$, on retrouve les définitions du collège.",
        lecture=["$H$ est le projeté de $M$ sur l'axe des abscisses.", "$OH = \\cos x$ et $HM = \\sin x$ (pour $x$ entre $0$ et $\\dfrac{\\pi}{2}$)."],
        observations=["Pythagore dans $OHM$ : $\\cos^2 x + \\sin^2 x = OM^2 = 1$.", "Les coordonnées sont entre $-1$ et $1$.",
                      "Pour $x = \\dfrac{\\pi}{3}$ : $M\\left(\\dfrac{1}{2} ; \\dfrac{\\sqrt{3}}{2}\\right)$."],
        pieges=["Inverser cosinus (abscisse) et sinus (ordonnée)."],
        a_retenir=["$\\cos x$ = abscisse, $\\sin x$ = ordonnée du point image."],
    ),
)

_X = 35
FIG3 = figure_geom(
    view=_V, axes=True, circles=_CERCLE,
    points=[_p(_X, "M (x)"), _p(-_X, "M₁ (−x)", reveal=2), _p(180 - _X, "M₂ (π − x)", reveal=3), _p(180 + _X, "M₃ (π + x)", reveal=3)],
    segments=[_seg((math.cos(math.radians(_X)), math.sin(math.radians(_X))), (math.cos(math.radians(_X)), -math.sin(math.radians(_X))), reveal=2,
                   tooltip="symétrie d'axe (Ox)"),
              _seg((math.cos(math.radians(_X)), math.sin(math.radians(_X))), (-math.cos(math.radians(_X)), math.sin(math.radians(_X))), reveal=3,
                   tooltip="symétrie d'axe (Oy)"),
              _seg((math.cos(math.radians(_X)), math.sin(math.radians(_X))), (-math.cos(math.radians(_X)), -math.sin(math.radians(_X))), reveal=3,
                   tooltip="symétrie de centre O")],
    steps=["Le point M image de x", "−x : symétrique par rapport à l'axe des abscisses", "π − x et π + x : axe des ordonnées et centre O"],
    relation="$\\cos(-x) = \\cos x$, $\\sin(-x) = -\\sin x$ ; $\\cos(\\pi - x) = -\\cos x$, $\\sin(\\pi - x) = \\sin x$ ; $\\cos(\\pi + x) = -\\cos x$, $\\sin(\\pi + x) = -\\sin x$",
    alt="Point M image de x et ses trois symétriques sur le cercle : M₁ image de −x (symétrie par rapport à l'axe des abscisses), M₂ image de π − x (symétrie par rapport à l'axe des ordonnées), M₃ image de π + x (symétrie de centre O).",
    explication=explication(
        resume="Les points images de $-x$, $\\pi - x$ et $\\pi + x$ sont les symétriques de celui de $x$ : on lit leurs coordonnées sans calcul.",
        lecture=["$M_1$ : même abscisse, ordonnée opposée.", "$M_2$ : même ordonnée, abscisse opposée ; $M_3$ : coordonnées opposées."],
        observations=["$\\cos(-x) = \\cos x$ et $\\sin(-x) = -\\sin x$.", "$\\cos(\\pi - x) = -\\cos x$ et $\\sin(\\pi - x) = \\sin x$.",
                      "$\\cos(\\pi + x) = -\\cos x$ et $\\sin(\\pi + x) = -\\sin x$."],
        pieges=["Apprendre ces formules par cœur sans le dessin : il suffit de visualiser la symétrie."],
        a_retenir=["Angles associés : on dessine, on lit les signes, on garde les valeurs absolues."],
    ),
)


NOTION_1 = notion(
    id=ID1, title=N1,
    intro="Pour parler d'angles de plus d'un tour, ou d'angles « négatifs », on enroule la droite des réels autour d'un cercle de rayon $1$. Chaque réel devient alors un point du cercle : c'est le cercle trigonométrique, et l'unité naturelle d'angle est le radian.",
    pourquoi="Le radian relie directement angle et longueur : sur le cercle de rayon $1$, l'angle EST la longueur de l'arc. C'est l'unité utilisée en analyse, en physique et par les calculatrices scientifiques.",
    objectif="À la fin de ce cours, tu sauras définir le radian, calculer une longueur d'arc, placer sur le cercle le point image d'un réel, trouver une mesure dans $]-\\pi ; \\pi]$ ou $[0 ; 2\\pi[$, et approcher $\\pi$ par la méthode d'Archimède.",
    definition="Le cercle trigonométrique est le cercle de centre $O$ et de rayon $1$, orienté dans le sens direct (inverse des aiguilles d'une montre), avec pour origine $I(1 ; 0)$. En enroulant la droite des réels autour de ce cercle à partir de $I$, on associe à tout réel $x$ un unique point $M$, appelé image de $x$ ; $x$ est une mesure en radians de l'angle $\\widehat{IOM}$. Un angle de $1$ radian intercepte un arc de longueur égale au rayon ; sur un cercle de rayon $r$, un angle de $\\theta$ radians intercepte un arc de longueur $r\\theta$. Un tour complet mesure $2\\pi$ radians ($360°$), donc $x$ et $x + 2k\\pi$ ($k \\in \\mathbb{Z}$) ont la même image.",
    explication_simple="$\\dfrac{\\pi}{2}$ est un quart de tour : son image est $J(0 ; 1)$. $\\dfrac{9\\pi}{4} = \\dfrac{\\pi}{4} + 2\\pi$ : même image que $\\dfrac{\\pi}{4}$. Sur un cercle de rayon $5$ cm, un angle de $2$ rad intercepte un arc de $10$ cm.",
    intuition="Imagine un fil gradué enroulé autour d'une roue de rayon $1$ : chaque graduation tombe sur un point de la roue, et après $2\\pi \\approx 6{,}28$ unités, on recommence un tour.",
    regles=[
        "Radian : un angle de $1$ rad intercepte un arc de longueur égale au rayon ; $\\pi$ rad $= 180°$.",
        "Longueur d'arc sur un cercle de rayon $r$ : $L = r\\theta$ ($\\theta$ en radians).",
        "Tout réel $x$ a un unique point image ; $x$ et $x + 2k\\pi$ ($k$ entier) ont la même image.",
        "Pour placer l'image d'un réel, on retire (ou ajoute) des tours complets pour se ramener à $]-\\pi ; \\pi]$ ou à $[0 ; 2\\pi[$.",
        "Méthode d'Archimède : les demi-périmètres des polygones réguliers inscrits dans le cercle de rayon $1$ approchent $\\pi$.",
    ],
    formules=[
        formule("formule-degres-radians", "Conversion", "$\\pi$ rad $= 180°$", "Pour passer des degrés aux radians.", "Oublier que la calculatrice doit être en mode radian.", "$x$ rad $= \\dfrac{180x}{\\pi}$ degrés."),
        formule("formule-longueur-arc", "Longueur d'arc", "$L = r\\theta$", "Pour une roue, une piste, un arc.", "Utiliser $\\theta$ en degrés.", "Sur le cercle trigonométrique, $L = \\theta$."),
    ],
    methode_titre="Méthode — Placer l'image d'un réel sur le cercle",
    etapes=[
        step("search", "blue", "J'écris le réel sous la forme $\\dfrac{p\\pi}{q}$ et je calcule combien de tours complets ($2\\pi$) il contient."),
        step("layers", "purple", "Je retire ces tours pour obtenir une mesure dans $]-\\pi ; \\pi]$ (ou $[0 ; 2\\pi[$)."),
        step("target", "orange", "Je place le point en partant de $I$, dans le sens direct si la mesure est positive."),
        step("check", "green", "Je vérifie que la différence entre le réel de départ et la mesure obtenue est un multiple de $2\\pi$."),
    ],
    debutant=[
        step("search", "blue", "Je repère les quarts de tour : $\\dfrac{\\pi}{2}$, $\\pi$, $\\dfrac{3\\pi}{2}$."),
        step("layers", "purple", "J'enlève les tours complets (multiples de $2\\pi$)."),
        step("target", "orange", "Je tourne à partir de $I$ : sens inverse des aiguilles si positif."),
        step("check", "green", "Je contrôle avec la calculatrice en mode radian."),
    ],
    rapide=[step("layers", "purple", "Retirer les multiples de $2\\pi$."), step("check", "green", "Placer à partir de $I$.")],
    exemples=[
        ex("exemple-1239", "Exemple 1 — Une mesure dans $[0 ; 2\\pi[$",
           "Un angle a pour mesure $\\dfrac{5\\pi}{2}$ radians. Déterminer sa mesure dans $[0 ; 2\\pi[$ et placer son image.",
           [calc("$\\dfrac{5\\pi}{2} = \\dfrac{\\pi}{2} + 2\\pi$ : un tour complet de plus que $\\dfrac{\\pi}{2}$.")],
           "$\\dfrac{\\pi}{2}$ : l'image est le point $J(0 ; 1)$.", "facile", "free", conclusion="Ajouter un tour ne change pas le point."),
        ex("exemple-1251", "Exemple 2 — Longueur d'arc",
           "Une roue de rayon $40$ cm tourne de $\\dfrac{3\\pi}{4}$ radian. Quelle distance parcourt un point de la jante ?",
           [calc("$L = r\\theta = 40 \\times \\dfrac{3\\pi}{4} = 30\\pi$.")],
           "$30\\pi \\approx 94{,}2$ cm.", "facile", "free", conclusion="L'angle doit être en radians."),
        ex("exemple-1263", "Exemple 3 — Une mesure dans $]-\\pi ; \\pi]$",
           "Déterminer la mesure dans $]-\\pi ; \\pi]$ de l'angle $\\dfrac{17\\pi}{6}$.",
           [calc("$\\dfrac{17\\pi}{6} - 2\\pi = \\dfrac{17\\pi - 12\\pi}{6} = \\dfrac{5\\pi}{6}$, qui est dans $]-\\pi ; \\pi]$.")],
           "$\\dfrac{5\\pi}{6}$.", "moyen", "premium", conclusion="On retire un tour, et on vérifie l'intervalle."),
        ex("exemple-1275", "Exemple 4 — Beaucoup de tours",
           "Quelle est l'image de $-\\dfrac{35\\pi}{4}$ ? Donner une mesure dans $]-\\pi ; \\pi]$.",
           [calc("$-\\dfrac{35\\pi}{4} \\div 2\\pi = -\\dfrac{35}{8} \\approx -4{,}4$ : on ajoute $4$ tours."),
            calc("$-\\dfrac{35\\pi}{4} + 8\\pi = -\\dfrac{35\\pi}{4} + \\dfrac{32\\pi}{4} = -\\dfrac{3\\pi}{4}$.")],
           "$-\\dfrac{3\\pi}{4}$.", "moyen", "premium", conclusion="On ajoute un nombre entier de tours $2\\pi$."),
        ex("exemple-archimede", "Exemple 5 — Méthode d'Archimède",
           "Un hexagone régulier inscrit dans le cercle de rayon $1$ a des côtés de longueur $1$. En déduire un encadrement grossier de $\\pi$ par le bas.",
           [calc("Périmètre de l'hexagone : $6$ ; il est plus court que le cercle, de périmètre $2\\pi$."),
            calc("$6 < 2\\pi$, donc $\\pi > 3$. En doublant le nombre de côtés ($12$, $24$, $48$, $96$), Archimède obtient $\\pi \\approx 3{,}14$.")],
           "$\\pi > 3$ ; avec $96$ côtés, $\\pi \\approx 3{,}14$.", "moyen", "premium",
           conclusion="Programme : " + code("c = sqrt(2 - sqrt(4 - c*c))") + " fait passer du côté du polygone à $n$ côtés à celui à $2n$ côtés."),
        ex("exemple-radian-definition", "Exemple 6 — Pourquoi $\\pi$ rad $= 180°$",
           "Justifier que $\\pi$ radians correspondent à $180°$ et que $1$ rad $\\approx 57{,}3°$.",
           [calc("Le demi-cercle de rayon $1$ a pour longueur $\\pi$ : l'angle plat ($180°$) mesure $\\pi$ rad."),
            calc("Proportionnalité : $1$ rad $= \\dfrac{180}{\\pi}° \\approx 57{,}3°$.")],
           "$\\pi$ rad $= 180°$ et $1$ rad $\\approx 57{,}3°$.", "difficile", "ultra",
           conclusion="Le radian est défini par la longueur d'arc ; le degré, par un partage du tour en $360$."),
    ],
    erreurs=[
        ("Confondre degrés et radians.", "On calcule avec une calculatrice en mode degré.", "Ton angle est-il en radians ?", "$\\pi$ rad $= 180°$."),
        ("Croire qu'un réel négatif n'a pas d'image.", "On oublie le sens indirect.", "Dans quel sens tourne-t-on pour $x < 0$ ?", "Sens des aiguilles d'une montre."),
        ("Retirer $\\pi$ au lieu de $2\\pi$ pour « faire un tour ».", "On confond demi-tour et tour.", "Combien mesure un tour complet ?", "Un tour : $2\\pi$."),
        ("Appliquer $L = r\\theta$ avec $\\theta$ en degrés.", "On oublie la condition d'unité.", "En quelle unité est ton angle ?", "Convertis d'abord en radians."),
    ],
    astuce="Pour ramener $\\dfrac{p\\pi}{q}$ dans $]-\\pi ; \\pi]$, écris $2\\pi = \\dfrac{2q\\pi}{q}$ et retire ce nombre autant de fois que nécessaire : tout se fait sur les numérateurs.",
    a_retenir=["Repérage sur le cercle trigonométrique : rayon $1$, origine $I$, sens direct.",
               "Radian : $\\pi$ rad $= 180°$ ; longueur d'arc $L = r\\theta$.", "$x$ et $x + 2k\\pi$ ont la même image.",
               "Méthode d'Archimède : approcher pi par les polygones réguliers inscrits."],
    exemples_concrets=["Distance parcourue par une roue de vélo.", "Position d'une nacelle de grande roue.", "Histoire de $\\pi$ : Archimède et ses polygones."],
    figure=FIG1,
    quiz=(1239, 66101, 66105),
    prerequis=["Cercle et angles (collège)", "Proportionnalité"],
    notions_liees=[ID2, ID3],
    objectifs=["Définir le radian.", "Calculer une longueur d'arc.", "Placer l'image d'un réel.", "Approcher $\\pi$ (Archimède)."],
    vocabulaire=["cercle trigonométrique", "radian", "longueur d'arc", "enroulement", "point image"],
    synonymes=["cercle trigonométrique", "radian", "longueur d'arc", "mesure principale", "enroulement de la droite", "méthode d'Archimède"],
    proprietes=["Les réels $x$ et $x + 2k\\pi$ ($k$ entier) ont le même point image."],
    tags=["trigonométrie", "radian", "cercle"],
    difficulte="facile",
    apercu_premium=("Mesure dans ]−π ; π], beaucoup de tours, Archimède",
                    "Trois exemples rédigés : ramener un angle dans $]-\\pi ; \\pi]$, un angle de plusieurs tours, la méthode d'Archimède."),
    apercu_ultra=("Radian et degré, démonstration de la longueur d'arc",
                  "Pourquoi $\\pi$ rad $= 180°$, et la démonstration de la formule $L = r\\theta$."),
    questions_eclair=[("figure", "Quels réels de la figure ont la même image que $\\dfrac{\\pi}{3}$ ?", "$\\dfrac{7\\pi}{3}$ (et tous les $\\dfrac{\\pi}{3} + 2k\\pi$)."),
                      ("methode", "Combien mesure en degrés un angle de $\\dfrac{\\pi}{6}$ rad ?", "$30°$.")],
    demonstration=demonstration(
        "Longueur d'un arc : $L = r\\theta$",
        [("Proportionnalité", "Sur un cercle donné, la longueur d'un arc est proportionnelle à l'angle au centre qui l'intercepte."),
         ("Tour complet", "Pour un tour complet, l'angle mesure $2\\pi$ rad et l'arc est le cercle entier, de longueur $2\\pi r$."),
         ("Coefficient", "Le coefficient de proportionnalité est $\\dfrac{2\\pi r}{2\\pi} = r$."),
         ("Conclusion", "Un angle de $\\theta$ radians intercepte un arc de longueur $L = r\\theta$ ; si $r = 1$, $L = \\theta$ : sur le cercle trigonométrique, la mesure en radians EST une longueur.")],
        "C'est ce qui fait du radian l'unité « naturelle » des angles.",
    ),
)

NOTION_2 = notion(
    id=ID2, title=N2,
    intro="Le point image d'un réel $x$ a deux coordonnées : on les appelle cosinus et sinus de $x$. Pour un angle aigu, on retrouve exactement le cosinus et le sinus du triangle rectangle vus au collège.",
    pourquoi="Cosinus et sinus décrivent tout mouvement circulaire (roues, rotations, ondes) et permettent de calculer des longueurs et des hauteurs sans les mesurer.",
    objectif="À la fin de ce cours, tu sauras définir $\\cos x$ et $\\sin x$, connaître les valeurs remarquables, utiliser $\\cos^2 x + \\sin^2 x = 1$ et le signe selon la position du point, et faire le lien avec le triangle rectangle.",
    definition="Soit $x$ un réel et $M$ son point image sur le cercle trigonométrique. Le cosinus de $x$, noté $\\cos x$, est l'abscisse de $M$ ; le sinus de $x$, noté $\\sin x$, est son ordonnée : $M(\\cos x ; \\sin x)$. Pour tout réel $x$ : $-1 \\leqslant \\cos x \\leqslant 1$, $-1 \\leqslant \\sin x \\leqslant 1$ et $\\cos^2 x + \\sin^2 x = 1$. Pour $x \\in \\left]0 ; \\dfrac{\\pi}{2}\\right[$, dans le triangle $OHM$ rectangle en $H$ (hypoténuse $OM = 1$), $\\cos x = \\dfrac{OH}{OM}$ et $\\sin x = \\dfrac{HM}{OM}$ : ce sont les rapports du collège. Valeurs remarquables : $\\cos 0 = 1$, $\\sin 0 = 0$ ; $\\cos\\dfrac{\\pi}{6} = \\dfrac{\\sqrt{3}}{2}$, $\\sin\\dfrac{\\pi}{6} = \\dfrac{1}{2}$ ; $\\cos\\dfrac{\\pi}{4} = \\sin\\dfrac{\\pi}{4} = \\dfrac{\\sqrt{2}}{2}$ ; $\\cos\\dfrac{\\pi}{3} = \\dfrac{1}{2}$, $\\sin\\dfrac{\\pi}{3} = \\dfrac{\\sqrt{3}}{2}$ ; $\\cos\\dfrac{\\pi}{2} = 0$, $\\sin\\dfrac{\\pi}{2} = 1$.",
    explication_simple="L'image de $\\dfrac{\\pi}{3}$ est $M\\left(\\dfrac{1}{2} ; \\dfrac{\\sqrt{3}}{2}\\right)$, donc $\\cos\\dfrac{\\pi}{3} = \\dfrac{1}{2}$ et $\\sin\\dfrac{\\pi}{3} = \\dfrac{\\sqrt{3}}{2}$. L'image de $\\pi$ est $(-1 ; 0)$ : $\\cos\\pi = -1$, $\\sin\\pi = 0$.",
    intuition="Le cosinus dit « de combien le point est à droite », le sinus « de combien il est en haut ».",
    regles=[
        "$\\cos x$ = abscisse et $\\sin x$ = ordonnée du point image de $x$.",
        "$-1 \\leqslant \\cos x \\leqslant 1$ et $-1 \\leqslant \\sin x \\leqslant 1$.",
        "$\\cos^2 x + \\sin^2 x = 1$ (Pythagore) ; si on connaît l'un, on trouve l'autre au signe près, et le signe se lit sur le cercle.",
        "Signes : à droite de l'axe des ordonnées, $\\cos x > 0$ ; au-dessus de l'axe des abscisses, $\\sin x > 0$.",
        "Valeurs remarquables en $0$, $\\dfrac{\\pi}{6}$, $\\dfrac{\\pi}{4}$, $\\dfrac{\\pi}{3}$, $\\dfrac{\\pi}{2}$ : à connaître (tableau du cours).",
    ],
    formules=[
        formule("formule-cos2-sin2", "Relation fondamentale", "$\\cos^2 x + \\sin^2 x = 1$", "Pour trouver $\\sin x$ connaissant $\\cos x$.", "Oublier le choix du signe.", "Le signe se lit sur le cercle."),
        formule("formule-valeurs-remarquables", "Valeurs remarquables", "$\\cos\\dfrac{\\pi}{3} = \\dfrac{1}{2}$, $\\sin\\dfrac{\\pi}{3} = \\dfrac{\\sqrt{3}}{2}$, $\\cos\\dfrac{\\pi}{4} = \\dfrac{\\sqrt{2}}{2}$",
                "Pour tout calcul exact.", "Échanger $\\dfrac{\\pi}{6}$ et $\\dfrac{\\pi}{3}$.", "Plus l'angle est grand (jusqu'à $\\dfrac{\\pi}{2}$), plus le cosinus est petit."),
    ],
    methode_titre="Méthode — Trouver $\\sin x$ connaissant $\\cos x$",
    etapes=[
        step("search", "blue", "J'écris $\\sin^2 x = 1 - \\cos^2 x$ et je calcule."),
        step("layers", "purple", "J'obtiens deux valeurs possibles, opposées."),
        step("target", "orange", "Je place l'intervalle de $x$ sur le cercle pour connaître le signe de $\\sin x$."),
        step("check", "green", "Je vérifie que la valeur est entre $-1$ et $1$."),
    ],
    debutant=[
        step("search", "blue", "Je me rappelle : $\\cos^2 + \\sin^2 = 1$."),
        step("layers", "purple", "Je calcule le carré qui manque."),
        step("target", "orange", "Je regarde si le point est en haut ou en bas pour le signe."),
        step("check", "green", "Je contrôle à la calculatrice."),
    ],
    rapide=[step("layers", "purple", "$\\sin x = \\pm\\sqrt{1 - \\cos^2 x}$."), step("check", "green", "Signe lu sur le cercle.")],
    exemples=[
        ex("exemple-1298", "Exemple 1 — Coordonnées d'un point image",
           "Donner les coordonnées du point image de $\\dfrac{\\pi}{6}$.",
           [calc("$\\cos\\dfrac{\\pi}{6} = \\dfrac{\\sqrt{3}}{2}$ et $\\sin\\dfrac{\\pi}{6} = \\dfrac{1}{2}$.")],
           "$\\left(\\dfrac{\\sqrt{3}}{2} ; \\dfrac{1}{2}\\right)$.", "facile", "free", conclusion="Abscisse = cosinus, ordonnée = sinus."),
        ex("exemple-1310", "Exemple 2 — Relation fondamentale",
           "Soit $x \\in \\left]0 ; \\dfrac{\\pi}{2}\\right[$ avec $\\cos x = \\dfrac{1}{3}$. Calculer $\\sin x$.",
           [calc("$\\sin^2 x = 1 - \\dfrac{1}{9} = \\dfrac{8}{9}$."), calc("$\\sin x > 0$ (point au-dessus de l'axe) : $\\sin x = \\dfrac{\\sqrt{8}}{3} = \\dfrac{2\\sqrt{2}}{3}$.")],
           "$\\sin x = \\dfrac{2\\sqrt{2}}{3}$.", "facile", "free", conclusion="Le signe se lit sur le cercle."),
        ex("exemple-1322", "Exemple 3 — Un signe négatif",
           "Soit $x \\in \\left]\\dfrac{\\pi}{2} ; \\pi\\right[$ avec $\\sin x = \\dfrac{3}{5}$. Calculer $\\cos x$.",
           [calc("$\\cos^2 x = 1 - \\dfrac{9}{25} = \\dfrac{16}{25}$."), calc("Point à gauche de l'axe des ordonnées : $\\cos x < 0$.")],
           "$\\cos x = -\\dfrac{4}{5}$.", "moyen", "premium", conclusion="Deuxième quart du cercle : cosinus négatif, sinus positif."),
        ex("exemple-1334", "Exemple 4 — Triangle rectangle",
           "Un toboggan de $6$ m fait un angle de $\\dfrac{\\pi}{6}$ avec le sol. Quelle est sa hauteur ?",
           [calc("Hauteur $= 6\\sin\\dfrac{\\pi}{6} = 6 \\times \\dfrac{1}{2}$.")],
           "$3$ m.", "moyen", "premium", conclusion="Côté opposé $=$ hypoténuse $\\times$ sinus."),
        ex("exemple-valeurs-calcul", "Exemple 5 — Calcul exact",
           "Calculer $A = 2\\cos\\dfrac{\\pi}{4} \\times \\sin\\dfrac{\\pi}{4} + \\cos^2\\dfrac{\\pi}{3}$.",
           [calc("$2 \\times \\dfrac{\\sqrt{2}}{2} \\times \\dfrac{\\sqrt{2}}{2} = 2 \\times \\dfrac{2}{4} = 1$."), calc("$\\cos^2\\dfrac{\\pi}{3} = \\dfrac{1}{4}$.")],
           "$A = \\dfrac{5}{4}$.", "moyen", "premium", conclusion="On remplace, puis on calcule exactement."),
        ex("exemple-sin-pi-6-triangle", "Exemple 6 — Retrouver les valeurs de $\\dfrac{\\pi}{6}$",
           "Dans un triangle équilatéral de côté $1$, la hauteur coupe un angle de $\\dfrac{\\pi}{3}$ en deux. En déduire $\\cos\\dfrac{\\pi}{6}$ et $\\sin\\dfrac{\\pi}{6}$.",
           [calc("Le demi-triangle est rectangle, d'hypoténuse $1$, de petit côté $\\dfrac{1}{2}$ et de hauteur $\\dfrac{\\sqrt{3}}{2}$."),
            calc("L'angle au sommet mesure $\\dfrac{\\pi}{6}$ : côté adjacent $\\dfrac{\\sqrt{3}}{2}$, côté opposé $\\dfrac{1}{2}$.")],
           "$\\cos\\dfrac{\\pi}{6} = \\dfrac{\\sqrt{3}}{2}$ et $\\sin\\dfrac{\\pi}{6} = \\dfrac{1}{2}$.", "difficile", "ultra",
           conclusion="Les valeurs de $\\dfrac{\\pi}{6}$ et $\\dfrac{\\pi}{3}$ s'échangent : elles viennent du même triangle."),
    ],
    erreurs=[
        ("Inverser cosinus et sinus.", "On ne se souvient plus de l'axe.", "Le cosinus est-il sur l'axe horizontal ?", "$\\cos$ : abscisse ; $\\sin$ : ordonnée."),
        ("Oublier le signe après $\\cos^2 x + \\sin^2 x = 1$.", "On prend toujours la racine positive.", "Où est le point sur le cercle ?", "Lis le signe sur le cercle."),
        ("Écrire $\\cos x = 1{,}5$.", "On oublie que le cercle a pour rayon $1$.", "Une coordonnée peut-elle dépasser $1$ ?", "$-1 \\leqslant \\cos x \\leqslant 1$."),
        ("Échanger les valeurs de $\\dfrac{\\pi}{6}$ et $\\dfrac{\\pi}{3}$.", "On mélange les deux angles.", "$\\dfrac{\\pi}{3}$ est-il proche de la verticale ?", "Angle plus grand : abscisse plus petite."),
    ],
    astuce="Pour retenir les valeurs : $\\sin 0, \\sin\\dfrac{\\pi}{6}, \\sin\\dfrac{\\pi}{4}, \\sin\\dfrac{\\pi}{3}, \\sin\\dfrac{\\pi}{2}$ valent $\\dfrac{\\sqrt{0}}{2}, \\dfrac{\\sqrt{1}}{2}, \\dfrac{\\sqrt{2}}{2}, \\dfrac{\\sqrt{3}}{2}, \\dfrac{\\sqrt{4}}{2}$ ; les cosinus sont dans l'ordre inverse.",
    a_retenir=["Coordonnées d'un point du cercle trigonométrique : $M(\\cos x ; \\sin x)$.",
               "Relation cos² + sin² = 1 : $\\cos^2 x + \\sin^2 x = 1$ ; valeurs entre $-1$ et $1$.",
               "Valeurs remarquables du cosinus et du sinus : $0$, $\\dfrac{\\pi}{6}$, $\\dfrac{\\pi}{4}$, $\\dfrac{\\pi}{3}$, $\\dfrac{\\pi}{2}$."],
    exemples_concrets=["Hauteur d'une échelle contre un mur.", "Position d'un point sur une roue.", "Ombre et hauteur du Soleil."],
    figure=FIG2,
    quiz=(1298, 1299, 66201),
    prerequis=["Repérage sur le cercle trigonométrique", "Trigonométrie du triangle rectangle (collège)", "Théorème de Pythagore"],
    notions_liees=[ID1, ID3],
    objectifs=["Définir cosinus et sinus d'un réel.", "Connaître les valeurs remarquables.", "Utiliser $\\cos^2 + \\sin^2 = 1$.", "Faire le lien avec le triangle rectangle."],
    vocabulaire=["cosinus", "sinus", "abscisse", "ordonnée", "valeurs remarquables"],
    synonymes=["cosinus et sinus d'un réel", "valeurs remarquables", "cos² + sin² = 1", "coordonnées sur le cercle"],
    proprietes=["Pour tout réel $x$, $\\cos^2 x + \\sin^2 x = 1$."],
    tags=["trigonométrie", "cosinus", "sinus"],
    difficulte="moyen",
    apercu_premium=("Signe négatif, triangle rectangle, calcul exact",
                    "Trois exemples rédigés : cosinus négatif via $\\cos^2 + \\sin^2 = 1$, hauteur d'un toboggan, calcul exact avec valeurs remarquables."),
    apercu_ultra=("Valeurs de π/6, démonstration pour π/4 et π/3",
                  "Les valeurs de $\\dfrac{\\pi}{6}$ retrouvées par un triangle et la démonstration des valeurs de $\\dfrac{\\pi}{4}$ et $\\dfrac{\\pi}{3}$."),
    questions_eclair=[("figure", "Que vaut $OH$ sur la figure ?", "$\\cos\\dfrac{\\pi}{3} = \\dfrac{1}{2}$."),
                      ("methode", "Quel est le signe de $\\cos x$ si $x \\in \\left]\\dfrac{\\pi}{2} ; \\pi\\right[$ ?", "Négatif.")],
    demonstration=demonstration(
        "Calcul de $\\cos\\dfrac{\\pi}{4}$, $\\sin\\dfrac{\\pi}{4}$, $\\cos\\dfrac{\\pi}{3}$, $\\sin\\dfrac{\\pi}{3}$",
        [("$\\dfrac{\\pi}{4}$", "Le point image $M$ est sur la bissectrice $y = x$ : $\\cos\\dfrac{\\pi}{4} = \\sin\\dfrac{\\pi}{4} = a > 0$. Avec $a^2 + a^2 = 1$ : $a = \\dfrac{1}{\\sqrt{2}} = \\dfrac{\\sqrt{2}}{2}$."),
         ("$\\dfrac{\\pi}{3}$ : triangle", "Soit $M$ l'image de $\\dfrac{\\pi}{3}$ : $OI = OM = 1$ et $\\widehat{IOM} = 60°$, donc $OIM$ est équilatéral."),
         ("$\\cos\\dfrac{\\pi}{3}$", "La hauteur issue de $M$ est aussi médiane : son pied $H$ est le milieu de $[OI]$, donc $\\cos\\dfrac{\\pi}{3} = OH = \\dfrac{1}{2}$."),
         ("$\\sin\\dfrac{\\pi}{3}$", "$\\sin^2\\dfrac{\\pi}{3} = 1 - \\dfrac{1}{4} = \\dfrac{3}{4}$ et $\\sin\\dfrac{\\pi}{3} > 0$ : $\\sin\\dfrac{\\pi}{3} = \\dfrac{\\sqrt{3}}{2}$.")],
        "Deux figures simples (carré, triangle équilatéral) donnent toutes les valeurs remarquables.",
    ),
)

NOTION_3 = notion(
    id=ID3, title=N3,
    intro="Les angles $-x$, $\\pi - x$, $\\pi + x$, $\\dfrac{\\pi}{2} - x$ ont des points images symétriques de celui de $x$. Il suffit donc de connaître les valeurs pour un angle aigu pour lire, sur le cercle, celles de tous les angles « associés ».",
    pourquoi="Avec cinq valeurs remarquables et les symétries du cercle, on obtient sans calculatrice le cosinus et le sinus de dizaines d'angles, et on résout des équations simples comme $\\cos x = \\dfrac{1}{2}$.",
    objectif="À la fin de ce cours, tu sauras déterminer, par lecture du cercle, le cosinus et le sinus des angles associés à un angle remarquable, et résoudre dans $]-\\pi ; \\pi]$ des équations du type $\\cos x = a$ ou $\\sin x = a$ pour des valeurs remarquables.",
    definition="Pour tout réel $x$, les points images de $x$ et de $-x$ sont symétriques par rapport à l'axe des abscisses : $\\cos(-x) = \\cos x$ et $\\sin(-x) = -\\sin x$. Ceux de $x$ et de $\\pi - x$ sont symétriques par rapport à l'axe des ordonnées : $\\cos(\\pi - x) = -\\cos x$ et $\\sin(\\pi - x) = \\sin x$. Ceux de $x$ et de $\\pi + x$ sont symétriques par rapport à l'origine : $\\cos(\\pi + x) = -\\cos x$ et $\\sin(\\pi + x) = -\\sin x$. Ceux de $x$ et de $\\dfrac{\\pi}{2} - x$ sont symétriques par rapport à la droite d'équation $y = x$ : $\\cos\\left(\\dfrac{\\pi}{2} - x\\right) = \\sin x$ et $\\sin\\left(\\dfrac{\\pi}{2} - x\\right) = \\cos x$. Enfin $x + 2k\\pi$ a la même image que $x$. Pour résoudre $\\cos x = a$ (resp. $\\sin x = a$), on trace la droite verticale d'abscisse $a$ (resp. horizontale d'ordonnée $a$) et on lit les points d'intersection avec le cercle.",
    explication_simple="$\\dfrac{5\\pi}{6} = \\pi - \\dfrac{\\pi}{6}$ : $\\cos\\dfrac{5\\pi}{6} = -\\dfrac{\\sqrt{3}}{2}$ et $\\sin\\dfrac{5\\pi}{6} = \\dfrac{1}{2}$. L'équation $\\cos x = \\dfrac{1}{2}$ a deux solutions dans $]-\\pi ; \\pi]$ : $\\dfrac{\\pi}{3}$ et $-\\dfrac{\\pi}{3}$.",
    intuition="Le cercle est très symétrique : quatre points « jumeaux » ont les mêmes coordonnées au signe près. Le dessin donne les signes, la valeur remarquable donne les nombres.",
    regles=[
        "$-x$ : symétrie d'axe $(Ox)$ ; $\\cos(-x) = \\cos x$, $\\sin(-x) = -\\sin x$.",
        "$\\pi - x$ : symétrie d'axe $(Oy)$ ; $\\cos(\\pi - x) = -\\cos x$, $\\sin(\\pi - x) = \\sin x$.",
        "$\\pi + x$ : symétrie de centre $O$ ; $\\cos(\\pi + x) = -\\cos x$, $\\sin(\\pi + x) = -\\sin x$.",
        "$\\dfrac{\\pi}{2} - x$ : symétrie d'axe $y = x$ ; $\\cos\\left(\\dfrac{\\pi}{2} - x\\right) = \\sin x$, $\\sin\\left(\\dfrac{\\pi}{2} - x\\right) = \\cos x$.",
        "Équation $\\cos x = a$ : droite verticale $x = a$ ; $\\sin x = a$ : droite horizontale $y = a$ ; on lit les points d'intersection.",
    ],
    formules=[
        formule("formule-angles-associes", "Angles associés", "$\\cos(\\pi - x) = -\\cos x$, $\\sin(\\pi - x) = \\sin x$", "Pour les angles $\\dfrac{2\\pi}{3}$, $\\dfrac{3\\pi}{4}$, $\\dfrac{5\\pi}{6}$…", "Se tromper de signe.", "Fais le dessin : le signe se voit."),
        formule("formule-lecture-equation", "Lecture d'équation", "$\\cos x = \\cos a \\iff x = a$ ou $x = -a$ (à $2k\\pi$ près)", "Pour $\\cos x = a$ remarquable.", "Oublier la seconde solution.", "Une droite coupe le cercle en deux points (en général)."),
    ],
    methode_titre="Méthode — Cosinus et sinus d'un angle associé",
    etapes=[
        step("search", "blue", "J'écris l'angle sous la forme $\\pi - a$, $\\pi + a$, $-a$ ou $a + 2k\\pi$ avec $a$ remarquable."),
        step("layers", "purple", "Je place les deux points images et je repère la symétrie."),
        step("target", "orange", "Je lis les signes sur le dessin et je reprends les valeurs absolues de $a$."),
        step("check", "green", "Je contrôle avec la calculatrice en mode radian."),
    ],
    debutant=[
        step("search", "blue", "Je cherche l'angle remarquable « caché » ($\\dfrac{\\pi}{6}$, $\\dfrac{\\pi}{4}$, $\\dfrac{\\pi}{3}$)."),
        step("layers", "purple", "Je dessine le point sur le cercle."),
        step("target", "orange", "À gauche : cosinus négatif ; en bas : sinus négatif."),
        step("check", "green", "Les nombres sont ceux de l'angle remarquable."),
    ],
    rapide=[step("layers", "purple", "Dessin + symétrie."), step("check", "green", "Signes lus, valeurs remarquables.")],
    exemples=[
        ex("exemple-1357", "Exemple 1 — Angle opposé",
           "Calculer $\\cos\\left(-\\dfrac{\\pi}{3}\\right)$ et $\\sin\\left(-\\dfrac{\\pi}{3}\\right)$.",
           [calc("Symétrie par rapport à l'axe des abscisses : même abscisse, ordonnée opposée.")],
           "$\\cos\\left(-\\dfrac{\\pi}{3}\\right) = \\dfrac{1}{2}$ et $\\sin\\left(-\\dfrac{\\pi}{3}\\right) = -\\dfrac{\\sqrt{3}}{2}$.", "facile", "free",
           conclusion="Le cosinus ne change pas, le sinus change de signe."),
        ex("exemple-1369", "Exemple 2 — Angle $\\pi - x$",
           "Calculer $\\cos\\dfrac{3\\pi}{4}$ et $\\sin\\dfrac{3\\pi}{4}$.",
           [calc("$\\dfrac{3\\pi}{4} = \\pi - \\dfrac{\\pi}{4}$ : symétrie par rapport à l'axe des ordonnées.")],
           "$\\cos\\dfrac{3\\pi}{4} = -\\dfrac{\\sqrt{2}}{2}$ et $\\sin\\dfrac{3\\pi}{4} = \\dfrac{\\sqrt{2}}{2}$.", "facile", "free",
           conclusion="Le sinus ne change pas, le cosinus change de signe."),
        ex("exemple-1381", "Exemple 3 — Angle $\\pi + x$ et tours",
           "Calculer $\\cos\\dfrac{19\\pi}{6}$.",
           [calc("$\\dfrac{19\\pi}{6} - 2\\pi = \\dfrac{7\\pi}{6} = \\pi + \\dfrac{\\pi}{6}$."), calc("Symétrie de centre $O$ : $\\cos\\dfrac{7\\pi}{6} = -\\cos\\dfrac{\\pi}{6}$.")],
           "$\\cos\\dfrac{19\\pi}{6} = -\\dfrac{\\sqrt{3}}{2}$.", "moyen", "premium", conclusion="D'abord les tours, puis la symétrie."),
        ex("exemple-1393", "Exemple 4 — Une équation",
           "Résoudre dans $]-\\pi ; \\pi]$ l'équation $\\sin x = \\dfrac{\\sqrt{2}}{2}$.",
           [calc("La droite $y = \\dfrac{\\sqrt{2}}{2}$ coupe le cercle en deux points, symétriques par rapport à l'axe des ordonnées."),
            calc("Ce sont les images de $\\dfrac{\\pi}{4}$ et de $\\pi - \\dfrac{\\pi}{4} = \\dfrac{3\\pi}{4}$.")],
           "$\\mathcal{S} = \\left\\{\\dfrac{\\pi}{4} ; \\dfrac{3\\pi}{4}\\right\\}$.", "moyen", "premium", conclusion="Deux solutions dans un tour (en général)."),
        ex("exemple-angle-complementaire", "Exemple 5 — Angle $\\dfrac{\\pi}{2} - x$",
           "Sachant que $\\cos\\dfrac{\\pi}{5} \\approx 0{,}809$, donner une valeur approchée de $\\sin\\dfrac{3\\pi}{10}$.",
           [calc("$\\dfrac{3\\pi}{10} = \\dfrac{\\pi}{2} - \\dfrac{\\pi}{5}$."), calc("$\\sin\\left(\\dfrac{\\pi}{2} - x\\right) = \\cos x$.")],
           "$\\sin\\dfrac{3\\pi}{10} = \\cos\\dfrac{\\pi}{5} \\approx 0{,}809$.", "moyen", "premium",
           conclusion="Angles complémentaires : cosinus et sinus s'échangent."),
        ex("exemple-equation-cos-negatif", "Exemple 6 — Une équation avec un cosinus négatif",
           "Résoudre dans $[0 ; 2\\pi[$ l'équation $\\cos x = -\\dfrac{\\sqrt{3}}{2}$.",
           [calc("$-\\dfrac{\\sqrt{3}}{2} = \\cos\\left(\\pi - \\dfrac{\\pi}{6}\\right) = \\cos\\dfrac{5\\pi}{6}$."),
            calc("Le symétrique par rapport à l'axe des abscisses correspond à $-\\dfrac{5\\pi}{6}$, soit $2\\pi - \\dfrac{5\\pi}{6} = \\dfrac{7\\pi}{6}$ dans $[0 ; 2\\pi[$.")],
           "$\\mathcal{S} = \\left\\{\\dfrac{5\\pi}{6} ; \\dfrac{7\\pi}{6}\\right\\}$.", "difficile", "ultra",
           conclusion="On combine deux symétries et un tour complet."),
    ],
    erreurs=[
        ("Se tromper de signe pour un angle associé.", "On applique une formule mal retenue.", "As-tu fait le dessin ?", "Le signe se lit sur la position du point."),
        ("Oublier une solution d'équation.", "On ne prend que l'angle remarquable.", "Combien de points la droite coupe-t-elle sur le cercle ?", "En général deux solutions par tour."),
        ("Donner une solution hors de l'intervalle demandé.", "On ne ramène pas l'angle.", "Ta solution est-elle dans $]-\\pi ; \\pi]$ ?", "Ajoute ou retire $2\\pi$."),
        ("Confondre $\\pi - x$ et $\\pi + x$.", "On mélange les symétries.", "Axe des ordonnées ou centre $O$ ?", "$\\pi - x$ : axe $(Oy)$ ; $\\pi + x$ : centre $O$."),
    ],
    astuce="Écris toujours l'angle sous la forme « multiple de $\\pi$ $\\pm$ angle remarquable » : $\\dfrac{5\\pi}{6} = \\pi - \\dfrac{\\pi}{6}$, $\\dfrac{4\\pi}{3} = \\pi + \\dfrac{\\pi}{3}$, $\\dfrac{7\\pi}{4} = 2\\pi - \\dfrac{\\pi}{4}$.",
    a_retenir=["Angles associés : symétries du cercle (axe $(Ox)$, axe $(Oy)$, centre $O$, droite $y = x$).",
               "Lecture du cercle : le dessin donne les signes, l'angle remarquable donne les valeurs.",
               "Équations $\\cos x = a$, $\\sin x = a$ : intersections d'une droite et du cercle."],
    exemples_concrets=["Position d'une nacelle après un demi-tour.", "Hauteur d'un point de roue à différents instants.", "Calculer sans calculatrice."],
    figure=FIG3,
    quiz=(1357, 66301, 66302),
    prerequis=["Coordonnées d'un point du cercle trigonométrique", "Symétries (collège)"],
    notions_liees=[ID1, ID2],
    objectifs=["Lire cosinus et sinus d'angles associés.", "Résoudre $\\cos x = a$ et $\\sin x = a$ par lecture du cercle."],
    vocabulaire=["angles associés", "symétrie", "lecture du cercle", "équation trigonométrique", "angle opposé"],
    synonymes=["angles associés", "cos(π − x)", "cos(−x)", "résoudre cos x = a", "lecture du cercle trigonométrique"],
    proprietes=["Les points images de $x$, $-x$, $\\pi - x$ et $\\pi + x$ sont symétriques deux à deux."],
    tags=["trigonométrie", "angles associés", "équations"],
    difficulte="moyen",
    apercu_premium=("Tours et symétrie, équation, angles complémentaires",
                    "Trois exemples rédigés : $\\cos\\dfrac{19\\pi}{6}$, l'équation $\\sin x = \\dfrac{\\sqrt{2}}{2}$, et $\\dfrac{\\pi}{2} - x$."),
    apercu_ultra=("Équation avec cosinus négatif, démonstration des angles associés",
                  "Une équation dans $[0 ; 2\\pi[$ et la démonstration des formules par les symétries du cercle."),
    questions_eclair=[("figure", "Quel point de la figure est l'image de $\\pi + x$ ?", "$M_3$, symétrique de $M$ par rapport à $O$."),
                      ("methode", "$\\sin\\left(\\pi - \\dfrac{\\pi}{6}\\right)$ ?", "$\\dfrac{1}{2}$.")],
    demonstration=demonstration(
        "Formules des angles associés par les symétries du cercle",
        [("Point de départ", "$M(\\cos x ; \\sin x)$ est l'image de $x$ ; l'angle orienté de $\\overrightarrow{OI}$ à $\\overrightarrow{OM}$ mesure $x$."),
         ("$-x$", "La symétrie d'axe $(Ox)$ change le sens de rotation : elle envoie $M$ sur l'image de $-x$, et $(a ; b)$ sur $(a ; -b)$. D'où $\\cos(-x) = \\cos x$, $\\sin(-x) = -\\sin x$."),
         ("$\\pi + x$", "Tourner encore d'un demi-tour envoie $M$ sur son symétrique par rapport à $O$, de coordonnées $(-a ; -b)$ : $\\cos(\\pi + x) = -\\cos x$, $\\sin(\\pi + x) = -\\sin x$."),
         ("$\\pi - x$", "$\\pi - x = \\pi + (-x)$ : on enchaîne les deux symétries précédentes, ce qui donne la symétrie d'axe $(Oy)$ : $\\cos(\\pi - x) = -\\cos x$, $\\sin(\\pi - x) = \\sin x$.")],
        "Toutes les formules se lisent sur le dessin : il est inutile de les apprendre sans lui.",
    ),
)

CHAPTER = chapter(6, "Trigonométrie", "layers", [NOTION_1, NOTION_2, NOTION_3])
