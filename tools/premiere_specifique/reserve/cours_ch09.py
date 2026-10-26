"""Chapitre 9 — Probabilités conditionnelles et indépendance.

Programme 2026 : indépendance de deux évènements ; partition de l'univers,
formule des probabilités totales ; succession de deux épreuves indépendantes,
arbre ou tableau ; pour n ⩽ 4, répétition de n épreuves de Bernoulli
indépendantes et identiques. Les probabilités conditionnelles (tableau croisé,
arbre pondéré, distinction P(A ∩ B), P_A(B), P_B(A)) sont rappelées (elles
figurent dans les automatismes). Algorithme : Monte-Carlo. Approfondissements :
plusieurs épreuves indépendantes, marches aléatoires.

Les trois notions historiques gardent identifiants et titres ; une notion
ajoutée : « Épreuves indépendantes et épreuves de Bernoulli ».
"""
from premiere_specifique.cours_commun import calc, chapter, code, demonstration, ex, explication, figure_geom, formule, notion, pt, step, text

N1, N2, N3, N4 = ("Probabilité conditionnelle", "Arbres pondérés", "Notion d'indépendance",
                  "Épreuves indépendantes et épreuves de Bernoulli")
ID1, ID2, ID3, ID4 = ("probabilite-conditionnelle", "arbres-ponderes", "notion-d-independance",
                      "epreuves-independantes-et-epreuves-de-bernoulli")


def _s(a, b, **kw):
    s = {"from": {"x": a[0], "y": a[1]}, "to": {"x": b[0], "y": b[1]}}
    s.update({k: v for k, v in kw.items() if v is not None})
    return s


def _tree2(pa, pab, pnab, labels=("A", "\\overline{A}", "B", "\\overline{B}"), reveal_paths=None):
    """Arbre pondéré à deux niveaux (coordonnées et textes)."""
    R = (0, 0)
    A, NA = (3, 1.6), (3, -1.6)
    leaves = [(6, 2.4), (6, 0.8), (6, -0.8), (6, -2.4)]
    pts = [pt(*R, ""), pt(*A, labels[0]), pt(*NA, labels[1])] + [pt(*q, lab) for q, lab in zip(leaves, (labels[2], labels[3], labels[2], labels[3]))]
    segs = [_s(R, A), _s(R, NA), _s(A, leaves[0]), _s(A, leaves[1]), _s(NA, leaves[2]), _s(NA, leaves[3])]
    texts = [text((1.2, 1.25), pa), text((1.2, -1.25), _cpl(pa)),
             text((4.4, 2.35), pab), text((4.4, 0.85), _cpl(pab)), text((4.4, -0.85), pnab), text((4.4, -2.35), _cpl(pnab))]
    return pts, segs, texts


def _cpl(p):
    from fractions import Fraction
    q = 1 - Fraction(p.replace(",", "."))
    return f"{float(q):g}".replace(".", ",")


_P, _S, _T = _tree2("0,3", "0,5", "0,2")
FIG2 = figure_geom(
    view=[-0.6, -3.0, 9.6, 6.0], axes=False,
    points=_P, segments=_S + [_s((0, 0), (3, 1.6), reveal=2), _s((3, 1.6), (6, 2.4), reveal=2),
                              _s((0, 0), (3, -1.6), reveal=3), _s((3, -1.6), (6, -0.8), reveal=3)],
    texts=_T + [text((7.9, 2.4), "0,3 × 0,5 = 0,15", reveal=2), text((7.9, -0.8), "0,7 × 0,2 = 0,14", reveal=3),
                text((7.3, -2.7), "P(B) = 0,15 + 0,14 = 0,29", reveal=3)],
    steps=["Arbre pondéré : P(A) puis probabilités sachant A ou Ā", "Chemin A puis B : on multiplie", "Probabilités totales : on additionne les chemins menant à B"],
    relation="$P(B) = P(A)P_A(B) + P(\\overline{A})P_{\\overline{A}}(B)$",
    alt="Arbre pondéré : P(A) = 0,3 et P(Ā) = 0,7 ; P_A(B) = 0,5, P_Ā(B) = 0,2. Les chemins menant à B ont pour probabilités 0,15 et 0,14, donc P(B) = 0,29.",
    explication=explication(
        resume="Sur un arbre pondéré, la probabilité d'un chemin est le produit des probabilités des branches ; la probabilité d'un événement est la somme des probabilités des chemins qui y mènent (formule des probabilités totales).",
        lecture=["Premier niveau : $A$ et $\\overline{A}$ (une partition de l'univers).", "Second niveau : probabilités conditionnelles."],
        observations=["$P(A \\cap B) = 0{,}3 \\times 0{,}5 = 0{,}15$.", "$P(\\overline{A} \\cap B) = 0{,}7 \\times 0{,}2 = 0{,}14$.", "$P(B) = 0{,}29$."],
        pieges=["Additionner le long d'un chemin au lieu de multiplier."],
        a_retenir=["On multiplie le long d'un chemin, on additionne les chemins."],
    ),
)

FIG1 = figure_geom(
    view=[-3.4, -2.6, 6.8, 5.2], axes=False,
    points=[],
    circles=[{"center": {"x": -0.7, "y": 0}, "radius": 1.6}, {"center": {"x": 0.9, "y": 0}, "radius": 1.6}],
    texts=[text((-1.9, 1.85), "A"), text((2.1, 1.85), "B"), text((0.1, 0), "A ∩ B", reveal=2),
           text((-1.4, -0.3), "A seul"), text((0.1, -2.25), "P_A(B) = P(A ∩ B) / P(A)", reveal=3)],
    steps=["Deux événements A et B", "Leur intersection A ∩ B", "Sachant A : on se restreint à A"],
    relation="$P_A(B) = \\dfrac{P(A \\cap B)}{P(A)}$ (avec $P(A) \\neq 0$)",
    alt="Deux disques A et B qui se chevauchent ; la zone commune représente A ∩ B. Sachant A, on ne regarde que le disque A : P_A(B) est la part de A occupée par A ∩ B.",
    explication=explication(
        resume="Savoir que $A$ est réalisé réduit l'univers à $A$ : la probabilité de $B$ sachant $A$ est la proportion de $A$ occupée par $A \\cap B$.",
        lecture=["Le disque de gauche représente $A$, celui de droite $B$.", "La zone commune est $A \\cap B$."],
        observations=["$P_A(B)$ et $P_B(A)$ ont le même numérateur $P(A \\cap B)$ mais des dénominateurs différents.",
                      "$P(A \\cap B) = P(A) \\times P_A(B)$.", "Dans un tableau croisé, on divise par le total de la ligne ou de la colonne concernée."],
        pieges=["Confondre $P_A(B)$, $P_B(A)$ et $P(A \\cap B)$."],
        a_retenir=["« Sachant $A$ » : on divise par $P(A)$."],
    ),
)

_P3, _S3, _T3 = _tree2("0,4", "0,25", "0,25")
FIG3 = figure_geom(
    view=[-0.6, -3.0, 9.6, 6.0], axes=False,
    points=_P3, segments=_S3,
    texts=_T3 + [text((7.6, 1.6), "P_A(B) = P_Ā(B) = 0,25", reveal=2), text((7.6, -1.6), "donc P(B) = 0,25 = P_A(B)", reveal=3)],
    steps=["Un arbre pondéré", "Les branches vers B ont la même probabilité", "B ne dépend pas de A : indépendance"],
    relation="$A$ et $B$ indépendants $\\iff P(A \\cap B) = P(A)P(B) \\iff P_A(B) = P(B)$ (si $P(A) \\neq 0$)",
    alt="Arbre pondéré où P(A) = 0,4 et où P_A(B) = P_Ā(B) = 0,25 : la réalisation de A ne change pas la probabilité de B, les événements sont indépendants.",
    explication=explication(
        resume="Deux événements sont indépendants si la réalisation de l'un ne modifie pas la probabilité de l'autre. Sur un arbre, les branches menant à $B$ portent alors la même probabilité.",
        lecture=["$P_A(B) = P_{\\overline{A}}(B) = 0{,}25$.", "La probabilité de $B$ ne dépend pas du premier niveau."],
        observations=["$P(B) = 0{,}4 \\times 0{,}25 + 0{,}6 \\times 0{,}25 = 0{,}25$.", "$P(A \\cap B) = 0{,}1 = P(A) \\times P(B)$.", "Indépendant n'est pas incompatible."],
        pieges=["Confondre indépendants ($P(A \\cap B) = P(A)P(B)$) et incompatibles ($P(A \\cap B) = 0$)."],
        a_retenir=["Indépendance : $P(A \\cap B) = P(A) \\times P(B)$."],
    ),
)

# Arbre de 3 épreuves de Bernoulli, chemins à 2 succès mis en évidence.
_N = {"": (0, 0)}
_coords = {}
for d, ys in ((1, (2.4, -2.4)), (2, (3.6, 1.2, -1.2, -3.6)), (3, (4.2, 3.0, 1.8, 0.6, -0.6, -1.8, -3.0, -4.2))):
    words = [w for w in ("SSS SSE SES SEE ESS ESE EES EEE".split())]
    prefixes = sorted({w[:d] for w in words}, key=lambda w: [c != "S" for c in w])
    for p, yv in zip(prefixes, ys):
        _N[p] = (2.4 * d, yv)
_segs4 = []
for p, q in _N.items():
    if p:
        _segs4.append(_s(_N[p[:-1]], q))
_two = [w for w in _N if len(w) == 3 and w.count("S") == 2]
_hi = []
for w in _two:
    for k in range(1, 4):
        _hi.append(_s(_N[w[:k - 1]], _N[w[:k]], reveal=2))
FIG4 = figure_geom(
    view=[-0.6, -4.8, 10.4, 9.6], axes=False,
    points=[pt(*q, (p[-1].replace("E", "\\overline{S}") if p else "")) for p, q in _N.items()],
    segments=_segs4 + _hi,
    texts=[text((9.3, _N[w][1]), w.replace("E", "\\overline{S}"), reveal=2) for w in _two] + [text((5.0, -4.6), "P(2 succès) = 3 × p² × (1 − p)", reveal=3)],
    steps=["3 épreuves de Bernoulli : 8 chemins", "3 chemins comportent exactement 2 succès", "Chaque chemin vaut p²(1 − p)"],
    relation="$P(\\text{2 succès sur 3}) = 3p^2(1 - p)$",
    alt="Arbre de trois épreuves de Bernoulli successives (S succès, Ē échec) ; les trois chemins SSĒ, SĒS, ĒSS comportent exactement deux succès, chacun de probabilité p²(1 − p).",
    explication=explication(
        resume="Quand on répète des épreuves de Bernoulli indépendantes et identiques, chaque chemin a pour probabilité $p^k(1 - p)^{n - k}$ ($k$ succès) : il suffit de compter les chemins.",
        lecture=["Chaque nœud se divise en succès $S$ (probabilité $p$) et échec $\\overline{S}$ (probabilité $1 - p$).", "Trois niveaux : $2^3 = 8$ chemins."],
        observations=["Chemins à $2$ succès : $SS\\overline{S}$, $S\\overline{S}S$, $\\overline{S}SS$.", "Avec $p = \\dfrac{1}{4}$ : $3 \\times \\dfrac{1}{16} \\times \\dfrac{3}{4} = \\dfrac{9}{64}$.",
                      "On s'arrête à $n \\leqslant 4$ en Première ($16$ chemins au plus)."],
        pieges=["Oublier des chemins, ou compter $p^2$ sans le facteur $1 - p$."],
        a_retenir=["$k$ succès sur $n$ : (nombre de chemins) $\\times p^k(1 - p)^{n - k}$."],
    ),
)


NOTION_1 = notion(
    id=ID1, title=N1,
    intro="Une information change les probabilités : sachant qu'un test est positif, la probabilité d'être malade n'est plus la même. La probabilité conditionnelle mesure cette mise à jour.",
    pourquoi="Dépistages médicaux, contrôles qualité, sondages : mal interpréter une probabilité conditionnelle conduit à de fausses conclusions (confondre « malade sachant positif » et « positif sachant malade »).",
    objectif="À la fin de ce cours, tu sauras calculer une probabilité conditionnelle à partir d'un tableau croisé ou de probabilités données, et distinguer $P(A \\cap B)$, $P_A(B)$ et $P_B(A)$.",
    definition="Soit $A$ un événement de probabilité non nulle. La probabilité de $B$ sachant $A$ est $P_A(B) = \\dfrac{P(A \\cap B)}{P(A)}$. On en déduit $P(A \\cap B) = P(A) \\times P_A(B)$. Dans un tableau croisé d'effectifs, $P_A(B)$ est l'effectif de $A \\cap B$ divisé par l'effectif de $A$. En général $P_A(B) \\neq P_B(A)$ : ces deux nombres ont le même numérateur $P(A \\cap B)$ mais pas le même dénominateur. On a $P_A(B) + P_A(\\overline{B}) = 1$.",
    explication_simple="Sur $200$ élèves, $80$ internes dont $30$ font du théâtre : $P_I(T) = \\dfrac{30}{80} = \\dfrac{3}{8}$. Si $110$ élèves font du théâtre, $P_T(I) = \\dfrac{30}{110} = \\dfrac{3}{11}$.",
    intuition="« Sachant $A$ » : on oublie tout ce qui n'est pas dans $A$, et on regarde la part de $B$ dans $A$.",
    regles=[
        "$P_A(B) = \\dfrac{P(A \\cap B)}{P(A)}$ avec $P(A) \\neq 0$.",
        "$P(A \\cap B) = P(A) \\times P_A(B) = P(B) \\times P_B(A)$.",
        "Tableau croisé : $P_A(B) = \\dfrac{\\text{effectif de } A \\cap B}{\\text{effectif de } A}$.",
        "$P_A(B)$ et $P_B(A)$ sont en général différentes.",
        "$P_A(\\overline{B}) = 1 - P_A(B)$.",
    ],
    formules=[
        formule("formule-proba-conditionnelle", "Probabilité conditionnelle", "$P_A(B) = \\dfrac{P(A \\cap B)}{P(A)}$", "Quand on sait que $A$ est réalisé.", "Diviser par $P(B)$.", "On divise par la probabilité de ce qu'on SAIT."),
        formule("formule-intersection", "Intersection", "$P(A \\cap B) = P(A) \\times P_A(B)$", "Pour un chemin d'arbre.", "Additionner au lieu de multiplier.", "C'est la formule de la définition, retournée."),
    ],
    methode_titre="Méthode — Calculer une probabilité conditionnelle",
    etapes=[
        step("search", "blue", "J'identifie l'événement connu (après « sachant ») et l'événement cherché."),
        step("layers", "purple", "Je calcule $P(A \\cap B)$ (ou l'effectif de $A \\cap B$)."),
        step("target", "orange", "Je divise par $P(A)$ (ou par l'effectif de $A$)."),
        step("check", "green", "Je vérifie que le résultat est entre $0$ et $1$ et je l'interprète."),
    ],
    debutant=[
        step("search", "blue", "Je repère ce que je SAIS (« sachant… »)."),
        step("layers", "purple", "Je regarde seulement cette partie de la population."),
        step("target", "orange", "Je calcule la proportion de ce que je cherche dedans."),
        step("check", "green", "Je réponds par une phrase."),
    ],
    rapide=[step("layers", "purple", "$P_A(B) = P(A \\cap B) / P(A)$."), step("check", "green", "Bon dénominateur.")],
    exemples=[
        ex("exemple-1710", "Exemple 1 — Avec la formule",
           "On donne $P(A) = \\dfrac{9}{20}$ et $P(A \\cap B) = \\dfrac{1}{4}$. Calculer $P_A(B)$.",
           [calc("P_A(B) = \\dfrac{1}{4} \\times \\dfrac{20}{9} = \\dfrac{5}{9}")],
           "$P_A(B) = \\dfrac{5}{9}$.", "facile", "free", conclusion="On divise par $P(A)$."),
        ex("exemple-1746", "Exemple 2 — Tableau croisé",
           "Sur $200$ élèves, $80$ sont internes, dont $30$ font du théâtre. Calculer la probabilité qu'un élève interne choisi au hasard fasse du théâtre.",
           [calc("On se restreint aux $80$ internes : $P_I(T) = \\dfrac{30}{80}$.")],
           "$P_I(T) = \\dfrac{3}{8}$.", "facile", "free", conclusion="Le dénominateur est l'effectif de la condition."),
        ex("exemple-1722", "Exemple 3 — $P_A(B)$ ou $P_B(A)$ ?",
           "On donne $P(A) = 0{,}4$, $P(B) = 0{,}5$, $P(A \\cap B) = 0{,}1$. Calculer $P_A(B)$ et $P_B(A)$.",
           [calc("$P_A(B) = \\dfrac{0{,}1}{0{,}4} = 0{,}25$ ; $P_B(A) = \\dfrac{0{,}1}{0{,}5} = 0{,}2$.")],
           "$P_A(B) = 0{,}25$ et $P_B(A) = 0{,}2$.", "moyen", "premium", conclusion="Même numérateur, dénominateurs différents."),
        ex("exemple-1734", "Exemple 4 — Dépistage",
           "Sur $1\\,000$ personnes, $20$ sont malades ; $18$ malades et $49$ non-malades ont un test positif. Calculer la probabilité d'être malade sachant que le test est positif.",
           [calc("Positifs : $18 + 49 = 67$ ; malades parmi eux : $18$.")],
           "$P_T(M) = \\dfrac{18}{67} \\approx 0{,}27$.", "moyen", "premium", conclusion="Un test positif ne signifie pas « malade à coup sûr »."),
        ex("exemple-proba-intersection", "Exemple 5 — Retrouver une intersection",
           "On donne $P(A) = 0{,}63$ et $P_A(B) = 0{,}77$. Calculer $P(A \\cap B)$ et $P(A \\cap \\overline{B})$.",
           [calc("$P(A \\cap B) = 0{,}63 \\times 0{,}77 = 0{,}4851$."), calc("$P(A \\cap \\overline{B}) = 0{,}63 \\times 0{,}23 = 0{,}1449$.")],
           "$0{,}4851$ et $0{,}1449$.", "moyen", "premium", conclusion="Leur somme vaut $P(A)$."),
        ex("exemple-inversion", "Exemple 6 — Inverser une condition",
           "$P(M) = 0{,}01$, $P_M(T) = 0{,}9$, $P_{\\overline{M}}(T) = 0{,}05$. Calculer $P_T(M)$.",
           [calc("$P(T) = 0{,}01 \\times 0{,}9 + 0{,}99 \\times 0{,}05 = 0{,}0585$."), calc("$P_T(M) = \\dfrac{0{,}009}{0{,}0585} = \\dfrac{2}{13} \\approx 0{,}154$.")],
           "$P_T(M) = \\dfrac{2}{13} \\approx 15{,}4\\,\\%$.", "difficile", "ultra",
           conclusion="Une maladie rare produit beaucoup de faux positifs, même avec un bon test."),
    ],
    erreurs=[
        ("Diviser par $P(B)$ pour calculer $P_A(B)$.", "On confond les deux conditions.", "Que SAIS-tu ?", "On divise par la probabilité de la condition."),
        ("Confondre $P_A(B)$ et $P(A \\cap B)$.", "On oublie la restriction à $A$.", "Te restreins-tu à $A$ ?", "$P(A \\cap B) = P(A) \\times P_A(B)$."),
        ("Croire que $P_A(B) = P_B(A)$.", "Symétrie apparente.", "Les dénominateurs sont-ils les mêmes ?", "En général, non."),
        ("Utiliser l'effectif total dans un tableau.", "On divise par $200$ au lieu de $80$.", "Quelle est la population de référence ?", "L'effectif de la condition."),
    ],
    astuce="Avant de calculer, reformule en français : « parmi les … (condition), quelle proportion … ? ». Le « parmi » donne le dénominateur.",
    a_retenir=["Probabilité conditionnelle : $P_A(B) = \\dfrac{P(A \\cap B)}{P(A)}$.", "$P(A \\cap B) = P(A) \\times P_A(B)$.", "$P_A(B) \\neq P_B(A)$ en général."],
    exemples_concrets=["Fiabilité d'un test de dépistage.", "Taux de réussite selon la filière.", "Contrôle qualité en usine."],
    figure=FIG1,
    quiz=(1710, 1712, 2000),
    prerequis=["Probabilités (Seconde)", "Fractions et pourcentages"],
    notions_liees=[ID2, ID3],
    objectifs=["Calculer une probabilité conditionnelle.", "Utiliser un tableau croisé.", "Distinguer $P(A \\cap B)$, $P_A(B)$, $P_B(A)$."],
    vocabulaire=["probabilité conditionnelle", "sachant", "intersection", "tableau croisé", "événement"],
    synonymes=["probabilité conditionnelle", "probabilité sachant", "P_A(B)", "tableau croisé d'effectifs"],
    proprietes=["$P(A \\cap B) = P(A) \\times P_A(B)$."],
    tags=["probabilités", "probabilité conditionnelle"],
    difficulte="facile",
    apercu_premium=("Deux conditions, dépistage, intersections",
                    "Trois exemples rédigés : $P_A(B)$ et $P_B(A)$, un tableau de dépistage, intersection et contraire."),
    apercu_ultra=("Inverser une condition, démonstration",
                  "Le calcul de $P_T(M)$ à partir de $P_M(T)$ et la démonstration de $P_A(B) + P_A(\\overline{B}) = 1$."),
    questions_eclair=[("figure", "Que représente la zone commune des deux disques ?", "$A \\cap B$."),
                      ("methode", "$P(A) = 0{,}5$, $P(A \\cap B) = 0{,}2$ : $P_A(B)$ ?", "$0{,}4$.")],
    demonstration=demonstration(
        "Probabilité sachant $A$ : $P_A(B) + P_A(\\overline{B}) = 1$",
        [("Partition", "$A \\cap B$ et $A \\cap \\overline{B}$ sont incompatibles et leur réunion est $A$."),
         ("Somme", "$P(A \\cap B) + P(A \\cap \\overline{B}) = P(A)$."),
         ("Division", "En divisant par $P(A) \\neq 0$ : $P_A(B) + P_A(\\overline{B}) = 1$."),
         ("Conclusion", "Les branches issues d'un même nœud d'un arbre pondéré ont une somme égale à $1$.")],
        "C'est la règle des nœuds des arbres pondérés.",
    ),
)

NOTION_2 = notion(
    id=ID2, title=N2,
    intro="Un arbre pondéré représente une expérience en plusieurs étapes. La formule des probabilités totales permet d'y calculer la probabilité d'un événement atteint par plusieurs chemins.",
    pourquoi="C'est l'outil standard pour les situations en deux temps : un premier tri (fournisseur, population, maladie), puis un résultat (défaut, réponse, test).",
    objectif="À la fin de ce cours, tu sauras construire et compléter un arbre pondéré, calculer la probabilité d'un chemin, et utiliser une partition de l'univers et la formule des probabilités totales.",
    definition="Des événements $A_1, \\dots, A_n$ de probabilités non nulles forment une partition de l'univers (système complet d'événements) s'ils sont deux à deux incompatibles et si leur réunion est l'univers ; c'est le cas de $A$ et $\\overline{A}$. Formule des probabilités totales : $P(B) = P(A_1)P_{A_1}(B) + \\dots + P(A_n)P_{A_n}(B)$ ; en particulier $P(B) = P(A)P_A(B) + P(\\overline{A})P_{\\overline{A}}(B)$. Sur un arbre pondéré : la somme des probabilités issues d'un même nœud vaut $1$ ; la probabilité d'un chemin est le produit des probabilités de ses branches ; la probabilité d'un événement est la somme des probabilités des chemins qui y mènent.",
    explication_simple="$P(A) = 0{,}3$, $P_A(B) = 0{,}5$, $P_{\\overline{A}}(B) = 0{,}2$ : $P(B) = 0{,}3 \\times 0{,}5 + 0{,}7 \\times 0{,}2 = 0{,}29$.",
    intuition="Pour aller à $B$, il y a plusieurs routes ; on calcule la probabilité de chaque route (en multipliant) puis on les additionne.",
    regles=[
        "Somme des branches issues d'un nœud : $1$.",
        "Probabilité d'un chemin : produit des probabilités des branches.",
        "Partition $A_1, \\dots, A_n$ : incompatibles deux à deux, de réunion l'univers.",
        "Probabilités totales : $P(B) = \\sum P(A_i)P_{A_i}(B)$.",
        "Inverser une condition : $P_B(A) = \\dfrac{P(A)P_A(B)}{P(B)}$.",
    ],
    formules=[
        formule("formule-probabilites-totales", "Probabilités totales", "$P(B) = P(A)P_A(B) + P(\\overline{A})P_{\\overline{A}}(B)$", "Quand $B$ est atteint par plusieurs chemins.", "Oublier un chemin.", "Un terme par chemin menant à $B$."),
        formule("formule-chemin", "Chemin", "$P(A \\cap B) = P(A) \\times P_A(B)$", "Pour un chemin de l'arbre.", "Additionner.", "On multiplie le long du chemin."),
    ],
    methode_titre="Méthode — Utiliser un arbre pondéré",
    etapes=[
        step("search", "blue", "Je repère la partition du premier niveau et les probabilités conditionnelles du second."),
        step("layers", "purple", "Je construis l'arbre et je complète les branches (somme $1$ par nœud)."),
        step("target", "orange", "Je multiplie le long des chemins utiles, puis j'additionne."),
        step("check", "green", "Je vérifie que la somme de tous les chemins vaut $1$."),
    ],
    debutant=[
        step("search", "blue", "Je dessine les premières branches."),
        step("layers", "purple", "Je complète pour que chaque nœud fasse $1$."),
        step("target", "orange", "Je multiplie sur un chemin, j'additionne les chemins."),
        step("check", "green", "Résultat entre $0$ et $1$."),
    ],
    rapide=[step("layers", "purple", "Multiplier sur un chemin, additionner les chemins."), step("check", "green", "Somme totale $1$.")],
    exemples=[
        ex("exemple-1768", "Exemple 1 — Probabilités totales",
           "$P(A) = \\dfrac{1}{2}$, $P_A(B) = \\dfrac{1}{4}$, $P_{\\overline{A}}(B) = \\dfrac{11}{20}$. Calculer $P(B)$.",
           [calc("P(B) = \\dfrac{1}{2} \\times \\dfrac{1}{4} + \\dfrac{1}{2} \\times \\dfrac{11}{20} = \\dfrac{1}{8} + \\dfrac{11}{40}")],
           "$P(B) = \\dfrac{2}{5}$.", "facile", "free", conclusion="Deux chemins mènent à $B$."),
        ex("exemple-1780", "Exemple 2 — Compléter un arbre",
           "$P(A) = 0{,}6$, $P_A(B) = 0{,}3$, $P_{\\overline{A}}(B) = 0{,}5$. Compléter l'arbre et calculer $P(\\overline{A} \\cap \\overline{B})$.",
           [calc("$P(\\overline{A}) = 0{,}4$ et $P_{\\overline{A}}(\\overline{B}) = 0{,}5$."), calc("$P(\\overline{A} \\cap \\overline{B}) = 0{,}4 \\times 0{,}5 = 0{,}2$.")],
           "$P(\\overline{A} \\cap \\overline{B}) = 0{,}2$.", "facile", "free", conclusion="On complète chaque nœud à $1$."),
        ex("exemple-1792", "Exemple 3 — Trois fournisseurs",
           "Fournisseurs $A_1$ ($50\\,\\%$), $A_2$ ($30\\,\\%$), $A_3$ ($20\\,\\%$) ; défauts $2\\,\\%$, $3\\,\\%$, $5\\,\\%$. Calculer $P(D)$.",
           [calc("$P(D) = 0{,}5 \\times 0{,}02 + 0{,}3 \\times 0{,}03 + 0{,}2 \\times 0{,}05$.")],
           "$P(D) = 0{,}029$.", "moyen", "premium", conclusion="Partition en trois événements."),
        ex("exemple-1804", "Exemple 4 — Tirage sans remise",
           "Une urne contient $5$ boules rouges et $3$ vertes ; on tire deux boules sans remise. Calculer la probabilité que la seconde soit rouge.",
           [calc("$P(R_2) = \\dfrac{5}{8} \\times \\dfrac{4}{7} + \\dfrac{3}{8} \\times \\dfrac{5}{7} = \\dfrac{20 + 15}{56}$.")],
           "$P(R_2) = \\dfrac{5}{8}$.", "moyen", "premium", conclusion="Même probabilité qu'au premier tirage : c'est une symétrie."),
        ex("exemple-arbre-inversion", "Exemple 5 — Remonter l'arbre",
           "Avec les trois fournisseurs précédents, sachant qu'un article est défectueux, quelle est la probabilité qu'il vienne de $A_3$ ?",
           [calc("$P_D(A_3) = \\dfrac{0{,}2 \\times 0{,}05}{0{,}029} = \\dfrac{10}{29}$.")],
           "$P_D(A_3) = \\dfrac{10}{29} \\approx 0{,}345$.", "moyen", "premium", conclusion="On divise un chemin par la probabilité totale."),
        ex("exemple-arbre-jeune", "Exemple 6 — Assurance",
           "$25\\,\\%$ d'assurés jeunes ; sinistre : $0{,}3$ pour un jeune, $0{,}1$ sinon. Calculer $P(S)$ puis $P_S(J)$, et conclure.",
           [calc("$P(S) = 0{,}075 + 0{,}075 = 0{,}15$."), calc("$P_S(J) = \\dfrac{0{,}075}{0{,}15} = 0{,}5$.")],
           "Les jeunes, $25\\,\\%$ des assurés, représentent $50\\,\\%$ des sinistrés.", "difficile", "ultra", conclusion="Comparer $P_S(J)$ et $P(J)$ mesure une surreprésentation."),
    ],
    erreurs=[
        ("Additionner le long d'un chemin.", "On confond « et » et « ou ».", "Est-ce une succession (et) ?", "Multiplier sur un chemin."),
        ("Oublier un chemin dans les probabilités totales.", "On ne regarde qu'une branche.", "Tous les chemins menant à $B$ sont-ils comptés ?", "Un terme par chemin."),
        ("Nœud dont les branches ne somment pas à $1$.", "Mauvaise lecture de l'énoncé.", "As-tu complété chaque nœud ?", "$P_A(\\overline{B}) = 1 - P_A(B)$."),
        ("Mettre $P(B)$ sur une branche du second niveau.", "On confond probabilité simple et conditionnelle.", "Cette branche part-elle de $A$ ?", "Au second niveau : probabilités conditionnelles."),
    ],
    astuce="Vérifie toujours ton arbre : la somme des probabilités de tous les chemins doit valoir $1$.",
    a_retenir=["Arbres pondérés : multiplier le long d'un chemin, additionner les chemins.", "Formule des probabilités totales sur une partition.", "Branches d'un nœud : somme $1$."],
    exemples_concrets=["Contrôle qualité chez plusieurs fournisseurs.", "Retards de livraison selon le canal.", "Tirages successifs dans une urne."],
    figure=FIG2,
    quiz=(1768, 1769, 2038),
    prerequis=["Probabilité conditionnelle"],
    notions_liees=[ID1, ID3, ID4],
    objectifs=["Construire un arbre pondéré.", "Utiliser une partition.", "Appliquer la formule des probabilités totales."],
    vocabulaire=["arbre pondéré", "chemin", "partition", "probabilités totales", "système complet"],
    synonymes=["arbre pondéré", "formule des probabilités totales", "partition de l'univers", "système complet d'événements"],
    proprietes=["La probabilité d'un événement est la somme des probabilités des chemins qui y mènent."],
    tags=["probabilités", "arbres", "probabilités totales"],
    difficulte="moyen",
    apercu_premium=("Trois fournisseurs, sans remise, remonter l'arbre",
                    "Trois exemples rédigés : partition en trois, tirage sans remise, inversion de la condition."),
    apercu_ultra=("Assurance, démonstration des probabilités totales",
                  "Un exemple de surreprésentation et la démonstration de la formule des probabilités totales."),
    questions_eclair=[("figure", "Que vaut $P(B)$ sur la figure ?", "$0{,}29$."),
                      ("methode", "$P(A) = 0{,}2$ : que vaut la branche $\\overline{A}$ ?", "$0{,}8$.")],
    demonstration=demonstration(
        "Formule des probabilités totales",
        [("Partition", "$A_1, \\dots, A_n$ sont deux à deux incompatibles et de réunion l'univers."),
         ("Découpage", "Les événements $B \\cap A_1, \\dots, B \\cap A_n$ sont deux à deux incompatibles et leur réunion est $B$."),
         ("Somme", "$P(B) = P(B \\cap A_1) + \\dots + P(B \\cap A_n)$."),
         ("Conclusion", "Avec $P(B \\cap A_i) = P(A_i)P_{A_i}(B)$ : $P(B) = \\sum P(A_i)P_{A_i}(B)$.")],
        "On découpe $B$ selon la partition, puis on additionne.",
    ),
)

NOTION_3 = notion(
    id=ID3, title=N3,
    intro="Deux événements sont indépendants quand la réalisation de l'un ne change pas la probabilité de l'autre : savoir que $A$ est arrivé n'apprend rien sur $B$.",
    pourquoi="L'indépendance simplifie les calculs (on multiplie les probabilités) et sert à juger si un facteur a un effet : une publicité, un traitement, un fournisseur.",
    objectif="À la fin de ce cours, tu sauras définir l'indépendance, la vérifier par le calcul, l'utiliser pour calculer $P(A \\cap B)$, et ne pas la confondre avec l'incompatibilité.",
    definition="Deux événements $A$ et $B$ sont indépendants si $P(A \\cap B) = P(A) \\times P(B)$. Si $P(A) \\neq 0$, cela équivaut à $P_A(B) = P(B)$ : la probabilité de $B$ ne dépend pas de la réalisation de $A$. Si $A$ et $B$ sont indépendants, alors $A$ et $\\overline{B}$ le sont aussi. Ne pas confondre avec des événements incompatibles ($P(A \\cap B) = 0$) : deux événements incompatibles de probabilités non nulles ne sont jamais indépendants. L'indépendance fait souvent partie d'un modèle (lancers de dés distincts, tirages avec remise).",
    explication_simple="Dé équilibré : $A$ « pair », $B$ « $\\leqslant 2$ ». $P(A \\cap B) = P(\\{2\\}) = \\dfrac{1}{6} = \\dfrac{1}{2} \\times \\dfrac{1}{3}$ : indépendants.",
    intuition="Indépendant : « l'un ne renseigne pas sur l'autre ». Incompatible : « si l'un arrive, l'autre ne peut pas arriver » — c'est au contraire une information très forte.",
    regles=[
        "$A$ et $B$ indépendants $\\iff P(A \\cap B) = P(A) \\times P(B)$.",
        "Si $P(A) \\neq 0$ : indépendants $\\iff P_A(B) = P(B)$.",
        "Indépendants : on multiplie les probabilités.",
        "Si $A$ et $B$ sont indépendants, $A$ et $\\overline{B}$ aussi.",
        "Incompatibles (de probabilités non nulles) $\\Rightarrow$ non indépendants.",
    ],
    formules=[
        formule("formule-independance", "Indépendance", "$P(A \\cap B) = P(A) \\times P(B)$", "Pour tester ou utiliser l'indépendance.", "L'appliquer sans justification.", "Vérifie l'égalité, ou justifie par le modèle."),
        formule("formule-independance-cond", "Avec la condition", "$P_A(B) = P(B)$", "Quand on connaît $P_A(B)$.", "Comparer $P_A(B)$ à $P(A)$.", "On compare à $P(B)$."),
    ],
    methode_titre="Méthode — Tester l'indépendance",
    etapes=[
        step("search", "blue", "Je calcule $P(A)$, $P(B)$ et $P(A \\cap B)$ (ou $P_A(B)$)."),
        step("layers", "purple", "Je compare $P(A \\cap B)$ et $P(A) \\times P(B)$ (ou $P_A(B)$ et $P(B)$)."),
        step("target", "orange", "Égalité : indépendants ; sinon : dépendants."),
        step("check", "green", "J'interprète dans le contexte."),
    ],
    debutant=[
        step("search", "blue", "Je calcule le produit des deux probabilités."),
        step("layers", "purple", "Je le compare à la probabilité de « les deux à la fois »."),
        step("target", "orange", "Même nombre : indépendants."),
        step("check", "green", "Je fais une phrase de conclusion."),
    ],
    rapide=[step("layers", "purple", "$P(A \\cap B) \\overset{?}{=} P(A)P(B)$."), step("check", "green", "Conclure.")],
    exemples=[
        ex("exemple-1826", "Exemple 1 — Test par le produit",
           "$P(A) = \\dfrac{9}{20}$, $P(B) = \\dfrac{4}{5}$, $P(A \\cap B) = \\dfrac{9}{25}$. $A$ et $B$ sont-ils indépendants ?",
           [calc("$P(A) \\times P(B) = \\dfrac{36}{100} = \\dfrac{9}{25} = P(A \\cap B)$.")],
           "Oui, $A$ et $B$ sont indépendants.", "facile", "free", conclusion="Le produit est égal à l'intersection."),
        ex("exemple-1838", "Exemple 2 — Deux dés",
           "On lance deux dés équilibrés indépendants. Probabilité d'obtenir deux $6$ ?",
           [calc("Les lancers sont indépendants : $\\dfrac{1}{6} \\times \\dfrac{1}{6}$.")],
           "$\\dfrac{1}{36}$.", "facile", "free", conclusion="L'indépendance vient du modèle."),
        ex("exemple-1850", "Exemple 3 — Effet d'une publicité",
           "$P(B) = 0{,}3$ (achat) et $P_A(B) = 0{,}5$ (achat sachant que le client a vu la publicité). La publicité a-t-elle un effet ?",
           [calc("$P_A(B) = 0{,}5 \\neq P(B) = 0{,}3$ : $A$ et $B$ ne sont pas indépendants.")],
           "Oui : la publicité augmente la probabilité d'achat.", "moyen", "premium", conclusion="Comparer $P_A(B)$ et $P(B)$."),
        ex("exemple-1862", "Exemple 4 — Incompatibles ou indépendants ?",
           "$P(A) = \\dfrac{1}{3}$, $P(B) = \\dfrac{1}{4}$ et $A$, $B$ incompatibles. Sont-ils indépendants ?",
           [calc("$P(A \\cap B) = 0$ alors que $P(A) \\times P(B) = \\dfrac{1}{12}$.")],
           "Non : incompatibles ne veut pas dire indépendants.", "moyen", "premium", conclusion="Deux notions différentes."),
        ex("exemple-independance-tableau", "Exemple 5 — Tableau croisé",
           "$240$ clients : $144$ hommes dont $60$ acheteurs, $96$ femmes dont $40$ acheteuses. Les événements « homme » et « acheteur » sont-ils indépendants ?",
           [calc("$P(A) = \\dfrac{100}{240} = \\dfrac{5}{12}$ et $P_H(A) = \\dfrac{60}{144} = \\dfrac{5}{12}$.")],
           "Oui, ils sont indépendants.", "moyen", "premium", conclusion="Même proportion d'acheteurs chez les hommes et dans l'ensemble."),
        ex("exemple-independance-contraire", "Exemple 6 — Indépendance et contraire",
           "Démontrer que si $A$ et $B$ sont indépendants, alors $A$ et $\\overline{B}$ le sont aussi.",
           [calc("$P(A \\cap \\overline{B}) = P(A) - P(A \\cap B) = P(A) - P(A)P(B)$."), calc("$= P(A)(1 - P(B)) = P(A)P(\\overline{B})$.")],
           "$A$ et $\\overline{B}$ sont indépendants.", "difficile", "ultra", conclusion="L'indépendance passe aux contraires."),
    ],
    erreurs=[
        ("Confondre indépendants et incompatibles.", "Les deux mots évoquent « séparés ».", "$P(A \\cap B)$ vaut-il $0$ ou $P(A)P(B)$ ?", "Incompatibles : $0$ ; indépendants : produit."),
        ("Supposer l'indépendance sans justification.", "On multiplie par réflexe.", "L'énoncé ou le modèle l'affirme-t-il ?", "Justifie ou vérifie."),
        ("Additionner les probabilités d'événements indépendants.", "On confond « et » et « ou ».", "Cherches-tu « les deux à la fois » ?", "On multiplie."),
        ("Comparer $P_A(B)$ à $P(A)$.", "Mauvaise comparaison.", "Quelle probabilité ne doit pas changer ?", "Comparer $P_A(B)$ à $P(B)$."),
    ],
    astuce="Sur un arbre, l'indépendance se voit : les branches menant à $B$ portent la même probabilité au second niveau.",
    a_retenir=["Indépendance : $P(A \\cap B) = P(A) \\times P(B)$.", "Équivaut à $P_A(B) = P(B)$ si $P(A) \\neq 0$.", "Indépendant $\\neq$ incompatible."],
    exemples_concrets=["Tirages avec remise.", "Pannes de deux machines indépendantes.", "Effet (ou non) d'un traitement."],
    figure=FIG3,
    quiz=(1826, 1829, 2033),
    prerequis=["Probabilité conditionnelle", "Arbres pondérés"],
    notions_liees=[ID1, ID2, ID4],
    objectifs=["Définir l'indépendance.", "La tester.", "L'utiliser pour calculer.", "La distinguer de l'incompatibilité."],
    vocabulaire=["indépendance", "incompatibles", "produit", "événement contraire", "modèle"],
    synonymes=["événements indépendants", "indépendance de deux événements", "P(A∩B) = P(A)P(B)", "incompatibles"],
    proprietes=["Si $A$ et $B$ sont indépendants, $A$ et $\\overline{B}$ le sont aussi."],
    tags=["probabilités", "indépendance"],
    difficulte="moyen",
    apercu_premium=("Publicité, incompatibles, tableau croisé",
                    "Trois exemples rédigés : effet d'une publicité, incompatibles contre indépendants, indépendance dans un tableau."),
    apercu_ultra=("Indépendance et contraire, démonstration",
                  "La démonstration que l'indépendance passe à l'événement contraire."),
    questions_eclair=[("figure", "Pourquoi $A$ et $B$ sont-ils indépendants sur la figure ?", "$P_A(B) = P_{\\overline{A}}(B) = P(B)$."),
                      ("methode", "$P(A) = 0{,}5$, $P(B) = 0{,}4$, indépendants : $P(A \\cap B)$ ?", "$0{,}2$.")],
    demonstration=demonstration(
        "Indépendance et probabilité conditionnelle",
        [("Hypothèse", "$P(A) \\neq 0$."),
         ("Sens direct", "Si $P(A \\cap B) = P(A)P(B)$, alors $P_A(B) = \\dfrac{P(A)P(B)}{P(A)} = P(B)$."),
         ("Réciproque", "Si $P_A(B) = P(B)$, alors $P(A \\cap B) = P(A)P_A(B) = P(A)P(B)$."),
         ("Conclusion", "Les deux définitions de l'indépendance sont équivalentes.")],
        "Être indépendant, c'est « savoir $A$ ne change rien à $B$ ».",
    ),
)

NOTION_4 = notion(
    id=ID4, title=N4,
    intro="Beaucoup d'expériences enchaînent des épreuves qui ne s'influencent pas : lancers successifs, tirages avec remise, questions répondues au hasard. Quand chaque épreuve n'a que deux issues (succès ou échec), on parle d'épreuves de Bernoulli.",
    pourquoi="Ces modèles décrivent les jeux, les contrôles de pièces, les QCM, les marches aléatoires… et préparent la loi binomiale de Terminale.",
    objectif="À la fin de ce cours, tu sauras représenter la succession de deux épreuves indépendantes par un arbre ou un tableau, et, pour $n \\leqslant 4$, représenter l'arbre de $n$ épreuves de Bernoulli indépendantes et identiques pour calculer des probabilités ; tu sauras aussi estimer une probabilité ou une aire par la méthode de Monte-Carlo.",
    definition="Deux épreuves sont indépendantes si les issues de l'une n'influencent pas les probabilités des issues de l'autre ; la probabilité d'un couple d'issues est alors le produit des probabilités, ce que l'on représente par un arbre (mêmes probabilités au second niveau sur toutes les branches) ou par un tableau à double entrée. Une épreuve de Bernoulli de paramètre $p$ est une épreuve à deux issues : succès $S$ (probabilité $p$) et échec $\\overline{S}$ (probabilité $1 - p$). En répétant $n$ fois ($n \\leqslant 4$) de manière indépendante la même épreuve de Bernoulli, chaque chemin de l'arbre comportant $k$ succès a pour probabilité $p^k(1 - p)^{n - k}$ ; la probabilité d'obtenir exactement $k$ succès est le nombre de ces chemins multiplié par $p^k(1 - p)^{n - k}$. Méthode de Monte-Carlo : on estime une probabilité (ou une aire) par la fréquence observée sur un grand nombre de simulations.",
    explication_simple="Un tireur réussit avec $p = 0{,}7$ ; deux tirs indépendants : $P(\\text{exactement une réussite}) = 2 \\times 0{,}7 \\times 0{,}3 = 0{,}42$.",
    intuition="Chaque chemin de l'arbre est un « scénario » ; on calcule la probabilité d'un scénario en multipliant, puis on compte combien de scénarios conviennent.",
    regles=[
        "Épreuves indépendantes : probabilité d'une suite d'issues = produit des probabilités.",
        "Représentation : arbre (mêmes branches à chaque niveau) ou tableau à double entrée.",
        "Bernoulli de paramètre $p$ : succès $p$, échec $1 - p$.",
        "$n \\leqslant 4$ épreuves : un chemin à $k$ succès vaut $p^k(1 - p)^{n - k}$ ; on compte les chemins.",
        "« Au moins un succès » : $1 - (1 - p)^n$ (événement contraire).",
    ],
    formules=[
        formule("formule-chemin-bernoulli", "Chemin", "$p^k(1 - p)^{n - k}$", "Pour un chemin à $k$ succès sur $n$.", "Oublier les échecs.", "Autant de facteurs que d'épreuves."),
        formule("formule-au-moins-un", "Au moins un succès", "$1 - (1 - p)^n$", "Pour « au moins une fois ».", "Additionner les cas un par un.", "Passe par le contraire « aucun succès »."),
    ],
    methode_titre="Méthode — Répétition d'épreuves de Bernoulli",
    etapes=[
        step("search", "blue", "J'identifie le succès, son paramètre $p$ et le nombre $n \\leqslant 4$ de répétitions."),
        step("layers", "purple", "Je dessine l'arbre ($2^n$ chemins) ou je liste les chemins utiles."),
        step("target", "orange", "Je calcule la probabilité d'un chemin, puis je multiplie par le nombre de chemins."),
        step("check", "green", "Je contrôle avec l'événement contraire ou la somme totale."),
    ],
    debutant=[
        step("search", "blue", "Je note ce qu'est un succès et sa probabilité."),
        step("layers", "purple", "Je dessine l'arbre, branche par branche."),
        step("target", "orange", "Je repère les chemins qui conviennent."),
        step("check", "green", "Je multiplie sur chaque chemin et j'additionne."),
    ],
    rapide=[step("layers", "purple", "Compter les chemins, $p^k(1 - p)^{n - k}$."), step("check", "green", "Contraire pour « au moins ».")],
    exemples=[
        ex("exemple-epreuves-tableau", "Exemple 1 — Tableau de deux épreuves",
           "On lance une pièce puis un dé, indépendamment. Probabilité de « face » et d'un nombre pair ?",
           [calc("Tableau : lignes pile/face ($\\dfrac{1}{2}$), colonnes pair/impair ($\\dfrac{1}{2}$)."), calc("$P = \\dfrac{1}{2} \\times \\dfrac{1}{2}$.")],
           "$\\dfrac{1}{4}$.", "facile", "free", conclusion="Chaque case : produit de sa ligne et de sa colonne."),
        ex("exemple-deux-tirs", "Exemple 2 — Deux tirs",
           "Un tireur réussit avec $p = 0{,}7$. Deux tirs indépendants : probabilité d'exactement une réussite ?",
           [calc("Chemins $S\\overline{S}$ et $\\overline{S}S$ : $0{,}7 \\times 0{,}3 + 0{,}3 \\times 0{,}7$.")],
           "$0{,}42$.", "facile", "free", conclusion="Deux chemins de même probabilité."),
        ex("exemple-trois-epreuves", "Exemple 3 — Trois épreuves",
           "$p = \\dfrac{1}{4}$, $3$ répétitions. Probabilité d'exactement $2$ succès ?",
           [calc("$3$ chemins, chacun $\\left(\\dfrac{1}{4}\\right)^2 \\times \\dfrac{3}{4} = \\dfrac{3}{64}$.")],
           "$\\dfrac{9}{64}$.", "moyen", "premium", conclusion="C'est la figure du cours."),
        ex("exemple-qcm", "Exemple 4 — QCM au hasard",
           "QCM de $4$ questions à $4$ réponses (une juste), réponses au hasard. Probabilité d'au moins une bonne réponse ?",
           [calc("Aucune bonne réponse : $\\left(\\dfrac{3}{4}\\right)^4 = \\dfrac{81}{256}$.")],
           "$1 - \\dfrac{81}{256} = \\dfrac{175}{256} \\approx 0{,}68$.", "moyen", "premium", conclusion="Le contraire évite de nombreux cas."),
        ex("exemple-monte-carlo", "Exemple 5 — Monte-Carlo",
           "Comment estimer l'aire sous la parabole $y = x^2$ entre $0$ et $1$ par la méthode de Monte-Carlo ?",
           [calc("On tire $N$ points au hasard dans le carré $[0 ; 1]^2$ et on compte ceux tels que $y \\leqslant x^2$."),
            calc("La fréquence approche l'aire cherchée (car le carré a pour aire $1$). En Python : " + code("if y <= x*x: k = k + 1") + ".")],
           "La fréquence approche l'aire, qui vaut $\\dfrac{1}{3}$.", "moyen", "premium", conclusion="Une probabilité estimée par simulation."),
        ex("exemple-marche-aleatoire", "Exemple 6 — Marche aléatoire",
           "Un pion part de $0$ et fait $4$ pas de $\\pm 1$ équiprobables et indépendants. Probabilité qu'il revienne en $0$ ?",
           [calc("Il faut $2$ pas $+1$ et $2$ pas $-1$ : $6$ chemins de probabilité $\\dfrac{1}{16}$.")],
           "$\\dfrac{6}{16} = \\dfrac{3}{8}$.", "difficile", "ultra", conclusion="Approfondissement : les marches aléatoires sont des répétitions d'épreuves de Bernoulli."),
    ],
    erreurs=[
        ("Oublier des chemins.", "On n'en compte qu'un.", "As-tu listé toutes les positions des succès ?", "Dessine l'arbre ou liste les mots."),
        ("Calculer $p^k$ sans $(1 - p)^{n - k}$.", "On oublie les échecs.", "Combien de facteurs dans ton produit ?", "Autant que d'épreuves."),
        ("Supposer l'indépendance pour des tirages sans remise.", "On ne regarde pas le protocole.", "La composition change-t-elle ?", "Sans remise : pas indépendants."),
        ("Additionner les cas pour « au moins un ».", "Calcul long et erreurs.", "Le contraire est-il plus simple ?", "$1 - P(\\text{aucun})$."),
    ],
    astuce="Pour lister les chemins, écris-les comme des mots de $S$ et $\\overline{S}$ : $SS\\overline{S}$, $S\\overline{S}S$… Le nombre de mots à $k$ lettres $S$ est le nombre de chemins.",
    a_retenir=["Épreuves indépendantes : on multiplie.", "Bernoulli répétée : chemin $p^k(1 - p)^{n - k}$, on compte les chemins.", "Monte-Carlo : fréquence ≈ probabilité."],
    exemples_concrets=["Réponses au hasard à un QCM.", "Contrôle de pièces successives.", "Estimation de $\\pi$ par simulation."],
    figure=FIG4,
    quiz=(69401, 69402, 69403),
    prerequis=["Arbres pondérés", "Notion d'indépendance"],
    notions_liees=[ID2, ID3],
    objectifs=["Représenter deux épreuves indépendantes.", "Utiliser l'arbre de $n \\leqslant 4$ épreuves de Bernoulli.", "Estimer par Monte-Carlo."],
    vocabulaire=["épreuve de Bernoulli", "succès", "échec", "épreuves indépendantes", "Monte-Carlo"],
    synonymes=["épreuve de Bernoulli", "répétition d'épreuves indépendantes", "succès et échec", "méthode de Monte-Carlo", "marche aléatoire"],
    proprietes=["Un chemin à $k$ succès sur $n$ épreuves de Bernoulli de paramètre $p$ a pour probabilité $p^k(1 - p)^{n - k}$."],
    tags=["probabilités", "Bernoulli", "Monte-Carlo"],
    difficulte="moyen",
    apercu_premium=("Trois épreuves, QCM, Monte-Carlo",
                    "Trois exemples rédigés : $2$ succès sur $3$, au moins une bonne réponse, aire sous la parabole par simulation."),
    apercu_ultra=("Marche aléatoire, démonstration",
                  "Le retour à l'origine d'une marche aléatoire et la démonstration de la formule d'un chemin."),
    questions_eclair=[("figure", "Combien de chemins comportent exactement $2$ succès ?", "$3$."),
                      ("methode", "$p = 0{,}5$, $3$ épreuves : probabilité de $3$ succès ?", "$0{,}125$.")],
    demonstration=demonstration(
        "Probabilité d'un chemin de $n$ épreuves de Bernoulli",
        [("Indépendance", "Les épreuves sont indépendantes : la probabilité d'une suite d'issues est le produit des probabilités."),
         ("Facteurs", "Chaque succès apporte un facteur $p$, chaque échec un facteur $1 - p$."),
         ("Chemin", "Un chemin à $k$ succès et $n - k$ échecs a pour probabilité $p^k(1 - p)^{n - k}$, quel que soit l'ordre."),
         ("Conclusion", "$P(\\text{exactement } k \\text{ succès}) = (\\text{nombre de chemins}) \\times p^k(1 - p)^{n - k}$.")],
        "Tous les chemins ayant le même nombre de succès ont la même probabilité : il suffit de les compter.",
    ),
)

CHAPTER = chapter(9, "Probabilités conditionnelles et indépendance", "layers", [NOTION_1, NOTION_2, NOTION_3, NOTION_4])
