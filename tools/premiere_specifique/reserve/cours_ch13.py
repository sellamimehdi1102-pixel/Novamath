"""Chapitre 13 (nouveau, programme 2026) — Automatismes.

Programme 2026 : les automatismes ne constituent pas un chapitre
d'enseignement ; ce sont des savoir-faire (proportions, évolutions, calcul
numérique et algébrique, fonctions et représentations, statistiques et
probabilités) entretenus tout au long de l'année par des questions flash et
évalués dans la partie automatismes de l'épreuve anticipée. Ce « chapitre »
est un espace d'entraînement transversal : chaque notion rappelle les
méthodes et renvoie aux chapitres où elles sont utilisées.
"""
from premiere_specifique.cours_commun import (
    P, calc, chapter, curve, demonstration, ex, explication, figure_geom, formule, notion, pt, seg, signe, step, tableau, text,
)

N1, N2, N3, N4 = ("Évolutions et taux", "Calcul numérique et algébrique", "Fonctions et représentations", "Statistiques et probabilités")
ID1, ID2, ID3, ID4 = ("evolutions-et-taux", "calcul-numerique-et-algebrique", "fonctions-et-representations", "statistiques-et-probabilites")


def _arrow(a, b, **kw):
    s = {"from": {"x": a[0], "y": a[1]}, "to": {"x": b[0], "y": b[1]}}
    s.update({k: v for k, v in kw.items() if v is not None})
    return s


FIG1 = figure_geom(
    view=[-0.4, -0.8, 11.2, 4.6], axes=False,
    points=[pt(0.8, 2, "100"), pt(5, 2, "110", reveal=2), pt(9.2, 2, "99", reveal=3)],
    segments=[_arrow((1.4, 2), (4.4, 2), reveal=2), _arrow((5.6, 2), (8.6, 2), reveal=3)],
    texts=[text((2.9, 2.8), "× 1,1", reveal=2), text((7.1, 2.8), "× 0,9", reveal=3), text((5.0, 0.4), "100 × 1,1 × 0,9 = 99", reveal=3)],
    steps=["Une valeur de départ : 100", "Hausse de 10 % : on multiplie par 1,1", "Baisse de 10 % : on multiplie par 0,9 ; bilan −1 %"],
    relation="Évolutions successives : les coefficients multiplicateurs se multiplient",
    alt="Schéma : 100 devient 110 après une hausse de 10 % (× 1,1), puis 99 après une baisse de 10 % (× 0,9). Le taux global est −1 %.",
    explication=explication(
        resume="Augmenter de $t\\,\\%$, c'est multiplier par $1 + \\dfrac{t}{100}$ ; diminuer de $t\\,\\%$, c'est multiplier par $1 - \\dfrac{t}{100}$. Des évolutions successives se composent en multipliant les coefficients.",
        lecture=["Chaque flèche est une évolution ; son coefficient est écrit au-dessus.", "Le bilan se lit en comparant la valeur finale à la valeur de départ."],
        observations=["$1{,}1 \\times 0{,}9 = 0{,}99$ : baisse globale de $1\\,\\%$.", "Une hausse puis une baisse de même taux ne se compensent pas.",
                      "Pour revenir à $100$ depuis $110$, il faut multiplier par $\\dfrac{1}{1{,}1}$."],
        pieges=["Additionner les taux : $+10\\,\\% - 10\\,\\% \\neq 0\\,\\%$."],
        a_retenir=["Coefficient multiplicateur $c = 1 + t$ ; taux $t = c - 1$."],
    ),
)

_INF = None
FIG2 = tableau(
    ["-\\infty", "-4", "3", "+\\infty"],
    [signe("2x - 6", lambda x: 2 * x - 6, [_INF, -4, 3, _INF], ["", "", "0", ""]),
     signe("x + 4", lambda x: x + 4, [_INF, -4, 3, _INF], ["", "0", "", ""]),
     signe("produit", lambda x: (2 * x - 6) * (x + 4), [_INF, -4, 3, _INF], ["", "0", "0", ""])],
    steps=["Signe de 2x − 6", "Signe de x + 4", "Signe du produit"],
    relation="$(2x - 6)(x + 4)$ s'annule en $-4$ et en $3$",
    alt="Tableau de signes du produit (2x − 6)(x + 4) : 2x − 6 est négatif avant 3 et positif après ; x + 4 est négatif avant −4 et positif après ; le produit est positif sur ]−∞ ; −4[, négatif sur ]−4 ; 3[, positif sur ]3 ; +∞[.",
    explication=explication(
        resume="Une expression du premier degré $ax + b$ change de signe en $-\\dfrac{b}{a}$ : elle a le signe de $a$ à droite de cette valeur. Le signe d'un produit s'obtient par la règle des signes.",
        lecture=["Une ligne par facteur, la dernière pour le produit.", "Les « 0 » marquent les valeurs qui annulent chaque facteur."],
        observations=["$2x - 6 = 0$ pour $x = 3$ ; $x + 4 = 0$ pour $x = -4$.", "Entre $-4$ et $3$, un seul facteur est négatif : le produit est négatif.",
                      "Les solutions de $(2x - 6)(x + 4) = 0$ sont $-4$ et $3$ (équation produit nul)."],
        pieges=["Oublier que le signe de $ax + b$ dépend du signe de $a$."],
        a_retenir=["Signe de $ax + b$ : signe de $a$ à droite de $-\\dfrac{b}{a}$."],
    ),
)


def _d(x):
    return 2 * x + 1


_V3 = [-1.4, -1.6, 6.4, 10.2]
FIG3 = figure_geom(
    view=_V3, axes=True,
    points=[pt(1, 3, "A(1 ; 3)"), pt(3, 7, "B(3 ; 7)"), pt(0, 1, "(0 ; 1)", reveal=3)],
    curves=curve(_d, -1.2, 4.2, _V3, tooltip="Droite y = 2x + 1"),
    segments=[seg(P(1, 3), P(3, 3), variant="hypotenuse", reveal=2), seg(P(3, 3), P(3, 7), variant="hypotenuse", reveal=2)],
    texts=[text((2, 2.4), "+2", reveal=2), text((3.6, 5), "+4", reveal=2)],
    steps=["Deux points de la droite", "Coefficient directeur : 4 / 2 = 2", "Ordonnée à l'origine : 1"],
    relation="$m = \\dfrac{7 - 3}{3 - 1} = 2$ ; $y = 2x + 1$",
    alt="Droite passant par A(1 ; 3) et B(3 ; 7) : quand x augmente de 2, y augmente de 4 ; le coefficient directeur est 2 et la droite coupe l'axe des ordonnées en (0 ; 1). Équation y = 2x + 1.",
    explication=explication(
        resume="L'équation réduite d'une droite non verticale s'écrit $y = mx + p$ : $m$ est le coefficient directeur (accroissement de $y$ quand $x$ augmente de $1$), $p$ l'ordonnée à l'origine.",
        lecture=["Les pointillés montrent le déplacement horizontal ($+2$) et vertical ($+4$).", "Le point $(0 ; 1)$ donne $p$."],
        observations=["$m = \\dfrac{\\Delta y}{\\Delta x} = \\dfrac{4}{2} = 2$.", "On vérifie : $2 \\times 1 + 1 = 3$ et $2 \\times 3 + 1 = 7$.",
                      "C'est la représentation d'une fonction affine."],
        pieges=["Inverser $\\Delta x$ et $\\Delta y$."],
        a_retenir=["$m = \\dfrac{y_B - y_A}{x_B - x_A}$."],
    ),
)

_BARS = [(1, 4), (2, 7), (3, 7), (4, 9), (5, 13)]
FIG4 = figure_geom(
    view=[-0.6, -1.2, 7.4, 15.4], axes=True, points=[],
    segments=[seg(P(x, 0), P(x, h), variant="hypotenuse" if k == 2 else None, reveal=1) for k, (x, h) in enumerate(_BARS)]
             + [seg(P(0.4, 8), P(5.6, 8), reveal=2, tooltip="Moyenne 8"), seg(P(5.9, 4), P(5.9, 13), reveal=3, tooltip="Étendue 9")],
    texts=[text((6.4, 8.6), "moyenne 8", reveal=2), text((3, 14), "médiane 7", reveal=2), text((6.4, 3.4), "étendue 9", reveal=3)],
    steps=["La série 4 ; 7 ; 7 ; 9 ; 13", "Moyenne et médiane", "Étendue : 13 − 4"],
    relation="Moyenne $8$, médiane $7$, étendue $9$",
    alt="Diagramme en bâtons de la série 4, 7, 7, 9, 13 rangée dans l'ordre croissant ; une ligne horizontale marque la moyenne 8 ; la valeur centrale 7 est la médiane ; l'étendue est 13 − 4 = 9.",
    explication=explication(
        resume="La moyenne et la médiane résument la position d'une série ; l'étendue mesure sa dispersion. La médiane partage la série rangée en deux groupes de même effectif.",
        lecture=["Chaque bâton est une valeur de la série, rangée dans l'ordre croissant.", "Le bâton central (le 3e sur 5) donne la médiane."],
        observations=["Moyenne : $\\dfrac{40}{5} = 8$.", "La moyenne est sensible à la valeur $13$ ; la médiane non.", "Étendue : $13 - 4 = 9$."],
        pieges=["Calculer la médiane sans ranger la série."],
        a_retenir=["Médiane : valeur centrale de la série rangée."],
    ),
)


NOTION_1 = notion(
    id=ID1, title=N1,
    intro="Les automatismes sont des savoir-faire à maîtriser sans hésitation, évalués par des questions flash. Premier domaine : proportions, pourcentages et évolutions.",
    pourquoi="Les évolutions en pourcentage sont partout (prix, populations, placements) et préparent les suites géométriques et l'exponentielle.",
    objectif="À la fin de ce cours, tu sauras appliquer un taux d'évolution, calculer un taux, retrouver une valeur initiale, composer des évolutions successives et calculer un taux réciproque.",
    definition="Quand une grandeur passe d'une valeur de départ $V_D$ à une valeur d'arrivée $V_A$, le taux d'évolution est $t = \\dfrac{V_A - V_D}{V_D}$ et le coefficient multiplicateur est $c = \\dfrac{V_A}{V_D} = 1 + t$. Augmenter de $t\\,\\%$, c'est multiplier par $1 + \\dfrac{t}{100}$ ; diminuer de $t\\,\\%$, c'est multiplier par $1 - \\dfrac{t}{100}$. Des évolutions successives correspondent au produit des coefficients multiplicateurs ; l'évolution réciproque a pour coefficient $\\dfrac{1}{c}$. Une proportion d'une proportion se calcule par un produit.",
    explication_simple="Une hausse de $15\\,\\%$ sur $80$ € : $80 \\times 1{,}15 = 92$ €. Une baisse de $20\\,\\%$ : on multiplie par $0{,}8$.",
    intuition="On raisonne toujours en coefficients multiplicateurs : ils se multiplient, alors que les taux ne s'additionnent pas.",
    regles=[
        "Taux d'évolution : $t = \\dfrac{V_A - V_D}{V_D}$ ; coefficient multiplicateur $c = 1 + t$.",
        "Hausse de $t\\,\\%$ : $\\times \\left(1 + \\dfrac{t}{100}\\right)$ ; baisse : $\\times \\left(1 - \\dfrac{t}{100}\\right)$.",
        "Valeur initiale : $V_D = \\dfrac{V_A}{c}$.",
        "Évolutions successives : on multiplie les coefficients multiplicateurs.",
        "Taux réciproque : coefficient $\\dfrac{1}{c}$ ; proportion de proportion : produit.",
    ],
    formules=[
        formule("formule-taux", "Taux", "$t = \\dfrac{V_A - V_D}{V_D}$", "Pour calculer un taux d'évolution.", "Diviser par $V_A$.", "On divise toujours par la valeur de départ."),
        formule("formule-coef", "Coefficient", "$c = 1 + t$", "Pour appliquer ou composer des évolutions.", "Additionner les taux.", "Les coefficients se multiplient."),
    ],
    methode_titre="Méthode — Traiter une évolution",
    etapes=[
        step("search", "blue", "J'identifie la valeur de départ, la valeur d'arrivée et le taux éventuel."),
        step("layers", "purple", "Je traduis le taux en coefficient multiplicateur."),
        step("target", "orange", "Je multiplie (évolution), je divise (valeur initiale) ou je compose (évolutions successives)."),
        step("check", "green", "Je reviens à un taux et je vérifie l'ordre de grandeur."),
    ],
    debutant=[
        step("search", "blue", "Je repère le départ et l'arrivée."),
        step("layers", "purple", "J'écris le coefficient : $1 + t$ ou $1 - t$."),
        step("target", "orange", "Je calcule."),
        step("check", "green", "Hausse : résultat plus grand ; baisse : plus petit."),
    ],
    rapide=[step("layers", "purple", "Taux → coefficient."), step("check", "green", "Les coefficients se multiplient.")],
    exemples=[
        ex("exemple-auto-appliquer", "Exemple 1 — Appliquer un taux",
           "Un article à $80$ € augmente de $15\\,\\%$. Nouveau prix ?", [calc("$80 \\times 1{,}15 = 92$.")], "$92$ €.", "facile", "free", conclusion="Coefficient $1{,}15$."),
        ex("exemple-auto-taux", "Exemple 2 — Calculer un taux",
           "Une population passe de $250$ à $200$. Taux d'évolution ?", [calc("$\\dfrac{200 - 250}{250} = -0{,}2$.")], "$-20\\,\\%$.", "facile", "free",
           conclusion="On divise par la valeur de départ."),
        ex("exemple-auto-initiale", "Exemple 3 — Retrouver une valeur initiale",
           "Après une hausse de $25\\,\\%$, un prix vaut $150$ €. Quel était le prix initial ?", [calc("$\\dfrac{150}{1{,}25} = 120$.")], "$120$ €.", "moyen", "premium",
           conclusion="On divise par le coefficient."),
        ex("exemple-auto-successives", "Exemple 4 — Évolutions successives",
           "Hausse de $10\\,\\%$ puis baisse de $10\\,\\%$ : taux global ?", [calc("$1{,}1 \\times 0{,}9 = 0{,}99$.")], "$-1\\,\\%$.", "moyen", "premium",
           conclusion="Les taux ne s'additionnent pas."),
        ex("exemple-auto-proportion", "Exemple 5 — Proportion de proportion",
           "$40\\,\\%$ des élèves sont internes, et $25\\,\\%$ des internes font du sport en club. Proportion d'internes sportifs ?",
           [calc("$0{,}4 \\times 0{,}25 = 0{,}1$.")], "$10\\,\\%$ des élèves.", "moyen", "premium", conclusion="On multiplie les proportions."),
        ex("exemple-auto-reciproque", "Exemple 6 — Taux réciproque",
           "Après une hausse de $25\\,\\%$, quelle baisse ramène à la valeur initiale ?", [calc("$\\dfrac{1}{1{,}25} = 0{,}8$.")], "Une baisse de $20\\,\\%$.", "difficile", "ultra",
           conclusion="Le taux réciproque n'est pas l'opposé du taux."),
    ],
    erreurs=[
        ("Additionner des taux successifs.", "Confusion addition / multiplication.", "Les évolutions s'appliquent-elles à la même valeur ?", "Multiplie les coefficients."),
        ("Diviser par la valeur d'arrivée.", "Mauvaise référence.", "Quelle est la valeur de départ ?", "$t = \\dfrac{V_A - V_D}{V_D}$."),
        ("Croire qu'une baisse de 25 % annule une hausse de 25 %.", "Taux réciproque.", "Que vaut $1{,}25 \\times 0{,}75$ ?", "$0{,}9375$ : il manque $6{,}25\\,\\%$."),
        ("Écrire 1,5 pour une hausse de 5 %.", "Conversion du pourcentage.", "Combien vaut $5\\,\\%$ en décimal ?", "$1 + 0{,}05 = 1{,}05$."),
    ],
    astuce="Retiens quelques coefficients par cœur : $+50\\,\\% \\to 1{,}5$ ; $-50\\,\\% \\to 0{,}5$ ; $+100\\,\\% \\to 2$ ; $-20\\,\\% \\to 0{,}8$.",
    a_retenir=["Évolutions et taux : coefficient multiplicateur $c = 1 + t$.", "Évolutions successives : produit des coefficients.", "Taux réciproque : coefficient $\\dfrac{1}{c}$."],
    exemples_concrets=["Soldes et augmentations de prix.", "Évolution d'une population.", "Placement à intérêts composés."],
    figure=FIG1,
    quiz=(73101, 73102, 73103),
    prerequis=["Pourcentages (Seconde)"],
    notions_liees=[ID2, ID4],
    objectifs=["Appliquer et calculer un taux.", "Composer des évolutions.", "Calculer un taux réciproque."],
    vocabulaire=["taux d'évolution", "coefficient multiplicateur", "pourcentage", "évolution réciproque"],
    synonymes=["pourcentage d'évolution", "coefficient multiplicateur", "hausse en pourcentage", "baisse en pourcentage", "évolutions successives", "taux réciproque"],
    proprietes=["Une hausse puis une baisse de même taux donnent une baisse globale."],
    tags=["automatismes", "pourcentages", "évolutions"],
    difficulte="facile",
    apercu_premium=("Valeur initiale, évolutions successives, proportions",
                    "Trois exemples rédigés : retrouver une valeur initiale, composer deux évolutions, proportion de proportion."),
    apercu_ultra=("Taux réciproque, démonstration",
                  "Le taux réciproque d'une hausse et la démonstration de la règle des évolutions successives."),
    questions_eclair=[("figure", "Quel est le taux global sur la figure ?", "$-1\\,\\%$."),
                      ("methode", "Coefficient d'une baisse de 30 % ?", "$0{,}7$.")],
    demonstration=demonstration(
        "Le taux global de deux évolutions successives vaut $t_1 + t_2 + t_1t_2$",
        [("Première évolution", "$V_1 = V_0(1 + t_1)$."),
         ("Seconde évolution", "$V_2 = V_1(1 + t_2) = V_0(1 + t_1)(1 + t_2)$."),
         ("Développement", "$(1 + t_1)(1 + t_2) = 1 + t_1 + t_2 + t_1t_2$."),
         ("Conclusion", "Le taux global est $t_1 + t_2 + t_1t_2$ : ce n'est la somme des taux que si $t_1t_2 = 0$.")],
        "C'est pourquoi on multiplie les coefficients au lieu d'additionner les taux.",
    ),
)

NOTION_2 = notion(
    id=ID2, title=N2,
    intro="Deuxième domaine des automatismes : calcul sur les fractions et les puissances, développement, factorisation, équations et inéquations du premier degré, signe d'une expression.",
    pourquoi="Ces calculs interviennent dans tous les chapitres : second degré, dérivation, suites, probabilités. Les rendre automatiques libère l'esprit pour le raisonnement.",
    objectif="À la fin de ce cours, tu sauras calculer avec des fractions, développer et factoriser avec les identités remarquables, résoudre une équation produit nul et étudier le signe d'une expression du premier degré.",
    definition="Les identités remarquables sont $(a + b)^2 = a^2 + 2ab + b^2$, $(a - b)^2 = a^2 - 2ab + b^2$ et $(a - b)(a + b) = a^2 - b^2$ ; lues de gauche à droite elles développent, de droite à gauche elles factorisent. Un produit de facteurs est nul si et seulement si l'un au moins de ses facteurs est nul. L'expression du premier degré $ax + b$ (avec $a \\neq 0$) s'annule en $-\\dfrac{b}{a}$ et a le signe de $a$ à droite de cette valeur, le signe contraire à gauche. Pour additionner des fractions, on les met au même dénominateur.",
    explication_simple="$(3x - 2)^2 = 9x^2 - 12x + 4$ ; $x^2 - 25 = (x - 5)(x + 5)$ ; $(2x - 6)(x + 4) = 0$ a pour solutions $3$ et $-4$.",
    intuition="Développer transforme un produit en somme ; factoriser fait l'inverse. La forme factorisée est la meilleure pour résoudre une équation ou étudier un signe.",
    regles=[
        "Identités remarquables : développer de gauche à droite, factoriser de droite à gauche.",
        "Équation produit nul : $AB = 0 \\iff A = 0$ ou $B = 0$.",
        "Signe de $ax + b$ : signe de $a$ à droite de $-\\dfrac{b}{a}$.",
        "Fractions : même dénominateur pour additionner ; numérateurs et dénominateurs multipliés entre eux pour multiplier.",
        "Puissances : $a^m \\times a^n = a^{m + n}$ ; $(a^m)^n = a^{mn}$.",
    ],
    formules=[
        formule("formule-ir", "Identités", "$(a - b)(a + b) = a^2 - b^2$", "Pour factoriser une différence de carrés.", "Écrire $(a - b)^2$.", "Repère deux carrés séparés par un signe moins."),
        formule("formule-produit-nul", "Produit nul", "$AB = 0 \\iff A = 0$ ou $B = 0$", "Pour résoudre une équation factorisée.", "Développer d'abord.", "Garde la forme factorisée."),
    ],
    methode_titre="Méthode — Choisir la bonne forme",
    etapes=[
        step("search", "blue", "Je lis la question : résoudre, étudier un signe, comparer, calculer une valeur ?"),
        step("layers", "purple", "Je choisis la forme adaptée : factorisée pour résoudre $= 0$ ou étudier un signe, développée pour calculer."),
        step("target", "orange", "Je transforme l'expression avec les identités remarquables ou la distributivité."),
        step("check", "green", "Je vérifie en remplaçant $x$ par une valeur simple."),
    ],
    debutant=[
        step("search", "blue", "Je repère la structure : somme ou produit ?"),
        step("layers", "purple", "Je cherche une identité remarquable."),
        step("target", "orange", "Je calcule pas à pas."),
        step("check", "green", "Je teste avec $x = 0$ ou $x = 1$."),
    ],
    rapide=[step("layers", "purple", "Forme factorisée ou développée."), step("check", "green", "Test numérique.")],
    exemples=[
        ex("exemple-auto-fractions", "Exemple 1 — Fractions",
           "Calculer $\\dfrac{2}{3} + \\dfrac{5}{6}$.", [calc("$\\dfrac{4}{6} + \\dfrac{5}{6} = \\dfrac{9}{6}$.")], "$\\dfrac{3}{2}$.", "facile", "free", conclusion="On simplifie à la fin."),
        ex("exemple-auto-produit-nul", "Exemple 2 — Produit nul",
           "Résoudre $(2x - 6)(x + 4) = 0$.", [calc("$2x - 6 = 0$ ou $x + 4 = 0$.")], "$\\mathcal{S} = \\{-4 ; 3\\}$.", "facile", "free", conclusion="Un facteur nul suffit."),
        ex("exemple-auto-developper", "Exemple 3 — Développer",
           "Développer $(3x - 2)^2$.", [calc("$(3x)^2 - 2 \\times 3x \\times 2 + 2^2$.")], "$9x^2 - 12x + 4$.", "moyen", "premium", conclusion="Identité $(a - b)^2$."),
        ex("exemple-auto-factoriser", "Exemple 4 — Factoriser",
           "Factoriser $x^2 - 25$ puis $(x + 1)^2 - 9$.", [calc("$x^2 - 5^2 = (x - 5)(x + 5)$."), calc("$(x + 1)^2 - 3^2 = (x - 2)(x + 4)$.")],
           "$(x - 5)(x + 5)$ et $(x - 2)(x + 4)$.", "moyen", "premium", conclusion="Différence de deux carrés."),
        ex("exemple-auto-signe", "Exemple 5 — Signe",
           "Étudier le signe de $-2x + 6$.", [calc("$-2x + 6 = 0$ pour $x = 3$ ; $a = -2 < 0$.")], "Positif pour $x < 3$, négatif pour $x > 3$.", "moyen", "premium",
           conclusion="Signe de $a$ à droite de la racine."),
        ex("exemple-auto-inequation", "Exemple 6 — Inéquation produit",
           "Résoudre $(2x - 6)(x + 4) < 0$.", [calc("Tableau de signes (figure) : le produit est négatif entre les racines.")], "$\\mathcal{S} = ]-4 ; 3[$.", "difficile", "ultra",
           conclusion="Le tableau de signes répond à l'inéquation."),
    ],
    erreurs=[
        ("Écrire $(a - b)^2 = a^2 - b^2$.", "Double produit oublié.", "Que donne le test $a = 3$, $b = 1$ ?", "$(a - b)^2 = a^2 - 2ab + b^2$."),
        ("Additionner numérateurs et dénominateurs.", "Fausse règle.", "Que vaut $\\dfrac{1}{2} + \\dfrac{1}{2}$ ?", "Même dénominateur d'abord."),
        ("Diviser par $x$ pour résoudre $x^2 = 3x$.", "Solution perdue.", "Que devient la solution $0$ ?", "Factorise : $x(x - 3) = 0$."),
        ("Oublier de changer le sens d'une inégalité en divisant par un négatif.", "Règle des inégalités.", "Divises-tu par un nombre négatif ?", "Le sens change."),
    ],
    astuce="Teste toujours ton développement ou ta factorisation en remplaçant $x$ par $1$ : les deux expressions doivent donner le même nombre.",
    a_retenir=["Calcul numérique et algébrique : identités remarquables, produit nul, signe de $ax + b$.", "Forme factorisée pour résoudre et étudier un signe.", "Test numérique pour vérifier."],
    exemples_concrets=["Résoudre une équation du second degré factorisée.", "Étudier le signe d'une dérivée.", "Calculer une probabilité avec des fractions."],
    figure=FIG2,
    quiz=(73201, 73202, 73205),
    prerequis=["Calcul littéral (Seconde)"],
    notions_liees=[ID1, ID3],
    objectifs=["Développer et factoriser.", "Résoudre une équation produit nul.", "Étudier un signe."],
    vocabulaire=["développer", "factoriser", "identité remarquable", "produit nul", "signe"],
    synonymes=["identités remarquables", "équation produit nul", "développer réduire", "factoriser une expression", "signe d'une expression affine", "calcul fractionnaire"],
    proprietes=["Un produit est nul si et seulement si l'un de ses facteurs est nul."],
    tags=["automatismes", "calcul littéral"],
    difficulte="facile",
    apercu_premium=("Développer, factoriser, signe",
                    "Trois exemples rédigés : identité remarquable, différence de deux carrés, signe d'une expression affine."),
    apercu_ultra=("Inéquation produit, démonstration",
                  "La résolution d'une inéquation produit par tableau de signes et la démonstration de la règle du produit nul."),
    questions_eclair=[("figure", "Signe du produit entre −4 et 3 ?", "Négatif."),
                      ("methode", "Factoriser $x^2 - 49$.", "$(x - 7)(x + 7)$.")],
    demonstration=demonstration(
        "Un produit de deux réels est nul si et seulement si l'un d'eux est nul",
        [("Sens direct", "Si $A = 0$ ou $B = 0$, alors $AB = 0$."),
         ("Réciproque", "Supposons $AB = 0$ et $A \\neq 0$."),
         ("Division", "On peut diviser par $A$ : $B = \\dfrac{AB}{A} = \\dfrac{0}{A} = 0$."),
         ("Conclusion", "Donc $AB = 0$ implique $A = 0$ ou $B = 0$.")],
        "La réciproque utilise une disjonction des cas ($A = 0$ ou $A \\neq 0$).",
    ),
)

NOTION_3 = notion(
    id=ID3, title=N3,
    intro="Troisième domaine des automatismes : lire et utiliser les représentations d'une fonction — expression, courbe, tableau de valeurs, tableau de variations — et les équations de droites.",
    pourquoi="Lire un graphique ou un tableau est indispensable pour conjecturer, vérifier un calcul, et répondre aux questions flash.",
    objectif="À la fin de ce cours, tu sauras calculer une image, trouver des antécédents, déterminer l'équation réduite d'une droite et lire un tableau de variations pour dénombrer des solutions.",
    definition="Une fonction $f$ associe à chaque nombre $x$ de son ensemble de définition un unique nombre $f(x)$, son image ; un antécédent de $y$ est un nombre $x$ tel que $f(x) = y$. Sa courbe représentative est l'ensemble des points de coordonnées $(x ; f(x))$. Une droite non parallèle à l'axe des ordonnées a une équation réduite $y = mx + p$, où $m = \\dfrac{y_B - y_A}{x_B - x_A}$ est le coefficient directeur et $p$ l'ordonnée à l'origine. Sur un intervalle où $f$ est strictement monotone et continue, chaque valeur comprise entre les valeurs extrêmes est atteinte exactement une fois.",
    explication_simple="Pour $f(x) = x^2 - 3x$ : $f(-2) = 4 + 6 = 10$. La droite passant par $A(1 ; 3)$ et $B(3 ; 7)$ a pour équation $y = 2x + 1$.",
    intuition="Image : on part de $x$ et on monte jusqu'à la courbe. Antécédent : on part de $y$ et on cherche horizontalement les points de la courbe.",
    regles=[
        "Image : remplacer $x$ par la valeur, avec des parenthèses pour un nombre négatif.",
        "Antécédents de $y$ : résoudre $f(x) = y$ ; il peut y en avoir zéro, un ou plusieurs.",
        "Droite par deux points : $m = \\dfrac{y_B - y_A}{x_B - x_A}$, puis $p$ avec un point.",
        "Tableau de variations : sur chaque intervalle de monotonie, une valeur est atteinte au plus une fois.",
        "Un point appartient à la courbe si ses coordonnées vérifient $y = f(x)$.",
    ],
    formules=[
        formule("formule-coef-dir", "Coefficient directeur", "$m = \\dfrac{y_B - y_A}{x_B - x_A}$", "Pour une droite par deux points.", "Inverser les différences.", "Δy sur Δx."),
        formule("formule-image", "Image", "$f(a)$", "Pour calculer une image.", "Oublier les parenthèses.", "$(-2)^2 = 4$."),
    ],
    methode_titre="Méthode — Exploiter une représentation",
    etapes=[
        step("search", "blue", "J'identifie la représentation : expression, courbe, tableau de valeurs ou de variations."),
        step("layers", "purple", "Je traduis la question : image, antécédent, équation, nombre de solutions."),
        step("target", "orange", "Je calcule avec l'expression ou je lis sur la représentation."),
        step("check", "green", "Je contrôle la cohérence entre calcul et lecture graphique."),
    ],
    debutant=[
        step("search", "blue", "Je repère ce qu'on me donne : x ou y ?"),
        step("layers", "purple", "Donné x : image. Donné y : antécédents."),
        step("target", "orange", "Je calcule ou je lis."),
        step("check", "green", "Je vérifie sur la courbe."),
    ],
    rapide=[step("layers", "purple", "Image ou antécédent ?"), step("check", "green", "Cohérence calcul / lecture.")],
    exemples=[
        ex("exemple-auto-image", "Exemple 1 — Image",
           "$f(x) = x^2 - 3x$. Calculer $f(-2)$.", [calc("$(-2)^2 - 3 \\times (-2) = 4 + 6$.")], "$f(-2) = 10$.", "facile", "free", conclusion="Parenthèses autour des négatifs."),
        ex("exemple-auto-antecedents", "Exemple 2 — Antécédents",
           "Antécédents de $4$ par la fonction carré ?", [calc("$x^2 = 4$.")], "$-2$ et $2$.", "facile", "free", conclusion="Deux antécédents."),
        ex("exemple-auto-droite", "Exemple 3 — Équation de droite",
           "Droite passant par $A(1 ; 3)$ et $B(3 ; 7)$ ?", [calc("$m = \\dfrac{4}{2} = 2$ ; $3 = 2 + p$.")], "$y = 2x + 1$.", "moyen", "premium", conclusion="C'est la figure."),
        ex("exemple-auto-appartenance", "Exemple 4 — Point sur une courbe",
           "Le point $C(3 ; 0)$ est-il sur la courbe de $f(x) = x^2 - 3x$ ?", [calc("$f(3) = 9 - 9 = 0$.")], "Oui.", "moyen", "premium", conclusion="On vérifie $y_C = f(x_C)$."),
        ex("exemple-auto-variations", "Exemple 5 — Nombre de solutions",
           "$f$ croît de $-3$ à $5$ sur $[-2 ; 1]$ puis décroît jusqu'à $0$ sur $[1 ; 4]$. Combien de solutions pour $f(x) = 2$ ?",
           [calc("$2$ est atteint une fois sur chaque intervalle.")], "$2$ solutions.", "moyen", "premium", conclusion="On compte intervalle par intervalle."),
        ex("exemple-auto-intersection", "Exemple 6 — Intersection de droites",
           "Point d'intersection des droites $y = 2x + 1$ et $y = -x + 7$ ?", [calc("$2x + 1 = -x + 7$ donne $x = 2$, puis $y = 5$.")], "$(2 ; 5)$.", "difficile", "ultra",
           conclusion="On résout l'égalité des ordonnées."),
    ],
    erreurs=[
        ("Écrire $-2^2 = 4$.", "Priorité du carré.", "Le signe moins est-il dans la parenthèse ?", "$(-2)^2 = 4$ mais $-2^2 = -4$."),
        ("Confondre image et antécédent.", "Sens de lecture.", "Te donne-t-on x ou y ?", "Image : $f(x)$ ; antécédent : $x$."),
        ("Calculer $m = \\dfrac{x_B - x_A}{y_B - y_A}$.", "Différences inversées.", "Le numérateur est-il vertical ?", "Δy sur Δx."),
        ("Croire qu'un nombre a toujours un seul antécédent.", "Image unique, antécédents multiples.", "Combien de points à cette hauteur ?", "Zéro, un ou plusieurs."),
    ],
    astuce="Pour une question flash sur une courbe, trace mentalement la droite horizontale $y = k$ : le nombre de points d'intersection est le nombre d'antécédents de $k$.",
    a_retenir=["Fonctions et représentations : image unique, antécédents éventuellement multiples.", "Droite : $y = mx + p$ avec $m = \\dfrac{\\Delta y}{\\Delta x}$.", "Tableau de variations : compter les solutions intervalle par intervalle."],
    exemples_concrets=["Lire un graphique de températures.", "Tarif affine d'un abonnement.", "Seuil de rentabilité."],
    figure=FIG3,
    quiz=(73301, 73302, 73303),
    prerequis=["Fonctions (Seconde)"],
    notions_liees=[ID2, ID4],
    objectifs=["Calculer une image et des antécédents.", "Trouver une équation de droite.", "Lire un tableau de variations."],
    vocabulaire=["image", "antécédent", "courbe", "coefficient directeur", "ordonnée à l'origine"],
    synonymes=["image d'un nombre", "antécédent", "équation réduite de droite", "lecture graphique", "coefficient directeur", "nombre de solutions"],
    proprietes=["Chaque nombre a au plus une image."],
    tags=["automatismes", "fonctions"],
    difficulte="facile",
    apercu_premium=("Droite, appartenance, nombre de solutions",
                    "Trois exemples rédigés : équation de droite, point sur une courbe, lecture d'un tableau de variations."),
    apercu_ultra=("Intersection de droites, démonstration",
                  "Le point d'intersection de deux droites et la démonstration de la formule du coefficient directeur."),
    questions_eclair=[("figure", "Coefficient directeur de la droite ?", "$2$."),
                      ("methode", "Image de $0$ par $x \\mapsto 3x - 5$ ?", "$-5$.")],
    demonstration=demonstration(
        "Si $A$ et $B$ sont sur la droite $y = mx + p$, alors $m = \\dfrac{y_B - y_A}{x_B - x_A}$",
        [("Hypothèse", "$y_A = mx_A + p$ et $y_B = mx_B + p$, avec $x_A \\neq x_B$."),
         ("Soustraction", "$y_B - y_A = m(x_B - x_A)$ : $p$ disparaît."),
         ("Division", "$x_B - x_A \\neq 0$, on peut diviser."),
         ("Conclusion", "$m = \\dfrac{y_B - y_A}{x_B - x_A}$.")],
        "Le coefficient directeur ne dépend pas des deux points choisis sur la droite.",
    ),
)

NOTION_4 = notion(
    id=ID4, title=N4,
    intro="Quatrième domaine des automatismes : indicateurs statistiques (moyenne, médiane, étendue), tableaux croisés et calculs de probabilités élémentaires.",
    pourquoi="Résumer des données et calculer une probabilité simple sont des gestes de base, préparatoires aux probabilités conditionnelles et aux variables aléatoires.",
    objectif="À la fin de ce cours, tu sauras calculer moyenne, médiane et étendue d'une série, lire un tableau croisé d'effectifs et calculer une probabilité en situation d'équiprobabilité.",
    definition="Pour une série de $n$ valeurs, la moyenne est la somme des valeurs divisée par $n$ ; la médiane est une valeur qui partage la série rangée dans l'ordre croissant en deux groupes de même effectif ; l'étendue est la différence entre la plus grande et la plus petite valeur. Un tableau croisé d'effectifs répartit une population selon deux critères. En situation d'équiprobabilité, la probabilité d'un événement $A$ est $P(A) = \\dfrac{\\text{nombre d'issues favorables}}{\\text{nombre total d'issues}}$, et $P(\\overline{A}) = 1 - P(A)$.",
    explication_simple="Série $4$ ; $7$ ; $7$ ; $9$ ; $13$ : moyenne $8$, médiane $7$, étendue $9$. Dé équilibré : $P(\\text{multiple de } 3) = \\dfrac{2}{6} = \\dfrac{1}{3}$.",
    intuition="La moyenne est le « partage équitable » ; la médiane la « valeur du milieu ». Une probabilité est une proportion d'issues.",
    regles=[
        "Moyenne : somme des valeurs divisée par l'effectif total.",
        "Médiane : ranger la série, puis prendre la valeur centrale (ou la moyenne des deux valeurs centrales).",
        "Étendue : valeur maximale moins valeur minimale.",
        "Tableau croisé : effectifs à l'intersection d'une ligne et d'une colonne ; totaux en marge.",
        "Équiprobabilité : issues favorables sur issues possibles ; $P(\\overline{A}) = 1 - P(A)$.",
    ],
    formules=[
        formule("formule-moyenne", "Moyenne", "$\\overline{x} = \\dfrac{x_1 + \\dots + x_n}{n}$", "Pour une série de valeurs.", "Oublier une valeur.", "Contrôle : la moyenne est entre le min et le max."),
        formule("formule-equiprobabilite", "Équiprobabilité", "$P(A) = \\dfrac{\\text{favorables}}{\\text{possibles}}$", "Pour un tirage au hasard.", "Compter deux fois une issue.", "Liste les issues."),
    ],
    methode_titre="Méthode — Lire un tableau croisé",
    etapes=[
        step("search", "blue", "J'identifie les deux critères (lignes et colonnes) et l'effectif total."),
        step("layers", "purple", "Je complète les cases manquantes avec les totaux."),
        step("target", "orange", "Je lis l'effectif voulu : une case (« et ») ou un total de ligne ou de colonne."),
        step("check", "green", "Je divise par l'effectif de référence et je vérifie que la probabilité est entre $0$ et $1$."),
    ],
    debutant=[
        step("search", "blue", "Je repère l'effectif total."),
        step("layers", "purple", "Je cherche la bonne case."),
        step("target", "orange", "Je divise par le total."),
        step("check", "green", "Résultat entre $0$ et $1$."),
    ],
    rapide=[step("layers", "purple", "Case ou total."), step("check", "green", "Bon dénominateur.")],
    exemples=[
        ex("exemple-auto-stats", "Exemple 1 — Indicateurs",
           "Série $4$ ; $7$ ; $7$ ; $9$ ; $13$ : moyenne, médiane, étendue ?", [calc("$\\dfrac{40}{5} = 8$ ; valeur centrale $7$ ; $13 - 4 = 9$.")],
           "Moyenne $8$, médiane $7$, étendue $9$.", "facile", "free", conclusion="C'est la figure."),
        ex("exemple-auto-de", "Exemple 2 — Un dé",
           "Probabilité d'obtenir un multiple de $3$ avec un dé équilibré ?", [calc("Issues favorables : $3$ et $6$.")], "$\\dfrac{1}{3}$.", "facile", "free",
           conclusion="Équiprobabilité."),
        ex("exemple-auto-croise", "Exemple 3 — Tableau croisé",
           "$120$ élèves : $70$ filles dont $42$ externes, $50$ garçons dont $20$ externes. $P(\\text{fille externe})$ ?", [calc("$\\dfrac{42}{120} = 0{,}35$.")],
           "$0{,}35$.", "moyen", "premium", conclusion="Une case du tableau : « et »."),
        ex("exemple-auto-contraire", "Exemple 4 — Événement contraire",
           "Dans le même lycée, probabilité qu'un élève choisi au hasard ne soit pas externe ?", [calc("Externes : $62$ ; $1 - \\dfrac{62}{120} = \\dfrac{58}{120}$.")],
           "$\\dfrac{29}{60}$.", "moyen", "premium", conclusion="$P(\\overline{A}) = 1 - P(A)$."),
        ex("exemple-auto-mediane-paire", "Exemple 5 — Médiane d'une série d'effectif pair",
           "Médiane de $3$ ; $5$ ; $8$ ; $10$ ; $12$ ; $20$ ?", [calc("Valeurs centrales : $8$ et $10$.")], "$9$.", "moyen", "premium",
           conclusion="Moyenne des deux valeurs centrales."),
        ex("exemple-auto-moyenne-ponderee", "Exemple 6 — Moyenne pondérée",
           "Notes $12$ (coefficient $2$), $8$ (coefficient $1$), $15$ (coefficient $3$) : moyenne ?", [calc("$\\dfrac{24 + 8 + 45}{6} = \\dfrac{77}{6}$.")],
           "$\\dfrac{77}{6} \\approx 12{,}8$.", "difficile", "ultra", conclusion="On divise par la somme des coefficients."),
    ],
    erreurs=[
        ("Calculer la médiane sans ranger la série.", "Valeur centrale fausse.", "La série est-elle rangée ?", "Range d'abord."),
        ("Se tromper de dénominateur dans un tableau croisé.", "Mauvaise population de référence.", "Sur quel total te demande-t-on ?", "Total général pour une probabilité simple."),
        ("Diviser par le nombre de notes dans une moyenne pondérée.", "Coefficients oubliés.", "Quelle est la somme des coefficients ?", "Divise par la somme des coefficients."),
        ("Obtenir une probabilité supérieure à 1.", "Erreur de comptage.", "Le résultat est-il entre 0 et 1 ?", "Recompte les issues."),
    ],
    astuce="Dans un tableau croisé, complète toujours les totaux de lignes et de colonnes : ils servent de vérification et de dénominateurs.",
    a_retenir=["Statistiques et probabilités : moyenne, médiane, étendue.", "Tableau croisé : une case = « et ».", "Équiprobabilité : favorables sur possibles."],
    exemples_concrets=["Notes d'une classe.", "Sondage croisé.", "Jeux de dés et de cartes."],
    figure=FIG4,
    quiz=(73401, 73402, 73403),
    prerequis=["Statistiques et probabilités (Seconde)"],
    notions_liees=[ID1, ID3],
    objectifs=["Calculer des indicateurs.", "Lire un tableau croisé.", "Calculer une probabilité."],
    vocabulaire=["moyenne", "médiane", "étendue", "tableau croisé", "équiprobabilité"],
    synonymes=["moyenne médiane étendue", "tableau croisé d'effectifs", "indicateurs statistiques", "probabilité équiprobable", "événement contraire"],
    proprietes=["La médiane est peu sensible aux valeurs extrêmes."],
    tags=["automatismes", "statistiques", "probabilités"],
    difficulte="facile",
    apercu_premium=("Tableau croisé, contraire, médiane paire",
                    "Trois exemples rédigés : lecture d'un tableau croisé, événement contraire, médiane d'une série d'effectif pair."),
    apercu_ultra=("Moyenne pondérée, démonstration",
                  "Une moyenne pondérée et la démonstration de la linéarité de la moyenne."),
    questions_eclair=[("figure", "Médiane de la série de la figure ?", "$7$."),
                      ("methode", "Probabilité de tirer un as dans un jeu de 32 cartes ?", "$\\dfrac{1}{8}$.")],
    demonstration=demonstration(
        "Si on ajoute $b$ à chaque valeur d'une série, la moyenne augmente de $b$",
        [("Nouvelle série", "Valeurs $x_1 + b, \\dots, x_n + b$."),
         ("Somme", "$(x_1 + b) + \\dots + (x_n + b) = (x_1 + \\dots + x_n) + nb$."),
         ("Division", "$\\dfrac{(x_1 + \\dots + x_n) + nb}{n} = \\overline{x} + b$."),
         ("Conclusion", "La moyenne augmente de $b$ ; de même, multiplier chaque valeur par $a$ multiplie la moyenne par $a$.")],
        "C'est la linéarité de la moyenne, qui annonce celle de l'espérance (chapitre 10).",
    ),
)

CHAPTER = chapter(13, "Automatismes", "zap", [NOTION_1, NOTION_2, NOTION_3, NOTION_4])
