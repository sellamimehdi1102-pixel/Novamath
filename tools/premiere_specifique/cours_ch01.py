"""Chapitre 1 — Pourcentages (Première spécifique, manuel « Première ES/L », Ch. 1 :
proportions ; taux d'évolution, coefficient multiplicateur ; taux réciproque ;
indices base 100 ; évolutions successives).

Créé lors de l'adaptation au manuel (2026-10-26, voir PREMIERE_SPECIFIQUE_SUIVI.md) :
« Évolutions et taux » est reprise de l'ancien chapitre « Automatismes »
(identifiant, exemples, figure et mini-quiz conservés) ; « Proportions et
pourcentages » et « Indices base 100 » sont créées.
"""
from premiere_specifique.cours_commun import calc, chapter, demonstration, ex, explication, figure_geom, formule, notion, step, text
from premiere_specifique.reserve.cours_ch13 import NOTION_1 as _EVOLUTIONS

N1, N2, N3 = "Proportions et pourcentages", "Évolutions et taux", "Indices base 100"
ID1, ID2, ID3 = "proportions-et-pourcentages", "evolutions-et-taux", "indices-base-100"


def _s(a, b, **kw):
    s = {"from": {"x": a[0], "y": a[1]}, "to": {"x": b[0], "y": b[1]}}
    s.update({k: v for k, v in kw.items() if v is not None})
    return s


# Figure 1 : une population de 480 personnes, dont 216 dans la partie étudiée (45 %).
FIG1 = figure_geom(
    view=[-0.6, -1.4, 11.2, 5.2], axes=False, points=[],
    segments=[_s((0, 0), (10, 0)), _s((10, 0), (10, 2)), _s((10, 2), (0, 2)), _s((0, 2), (0, 0)),
              _s((4.5, 0), (4.5, 2), reveal=2)],
    texts=[text((5.0, 2.7), "480 adhérents"), text((2.25, 1.0), "216 filles", reveal=2), text((7.25, 1.0), "264 garçons", reveal=2),
           text((2.25, -0.6), "45 %", reveal=3), text((7.25, -0.6), "55 %", reveal=3)],
    steps=["L'ensemble de référence : 480 adhérents", "La partie étudiée : 216 filles", "Proportion : 216 / 480 = 0,45, soit 45 %"],
    relation="$p = \\dfrac{\\text{effectif de la partie}}{\\text{effectif total}}$",
    alt="Rectangle représentant 480 adhérents d'un club, partagé en 216 filles (45 %) et 264 garçons (55 %).",
    explication=explication(
        resume="Une proportion compare l'effectif d'une partie à l'effectif total : c'est un nombre entre $0$ et $1$, souvent écrit en pourcentage.",
        lecture=["Le rectangle entier représente l'ensemble de référence.", "La partie colorée en premier représente les filles."],
        observations=["$\\dfrac{216}{480} = 0{,}45 = 45\\,\\%$.", "La proportion de garçons est $1 - 0{,}45 = 0{,}55$.", "Les deux proportions ont pour somme $1$."],
        pieges=["Diviser par l'effectif de l'autre partie ($\\dfrac{216}{264}$) au lieu de l'effectif total."],
        a_retenir=["Une proportion se calcule toujours par rapport à l'ensemble de référence."],
    ),
)

# Figure 3 : une grandeur et son indice base 100.
_VAL = [(2015, "1,20 €", 100), (2018, "1,29 €", 107.5), (2020, "1,38 €", 115)]
FIG3 = figure_geom(
    view=[-0.6, -1.6, 11.6, 5.6], axes=False, points=[],
    segments=[_s((0.5, 1.5), (10.5, 1.5))] + [_s((1 + 4.25 * i, 1.2), (1 + 4.25 * i, 1.8)) for i in range(3)],
    texts=[text((1 + 4.25 * i, 0.6), str(a)) for i, (a, _v, _i) in enumerate(_VAL)]
          + [text((1 + 4.25 * i, 2.5), v, reveal=1 if i == 0 else 2) for i, (_a, v, _i) in enumerate(_VAL)]
          + [text((1 + 4.25 * i, 3.4), f"indice {str(ind).replace('.', ',')}", reveal=2 if i == 0 else 3) for i, (_a, _v, ind) in enumerate(_VAL)]
          + [text((5.5, -1.0), "indice = 100 × valeur / valeur de référence", reveal=3)],
    steps=["Une grandeur suivie dans le temps", "On associe l'indice 100 à l'année de référence", "Les autres indices se calculent par proportionnalité"],
    relation="$I_2 = 100 \\times \\dfrac{y_2}{y_1}$",
    alt="Frise chronologique : prix de 1,20 € en 2015 (indice 100), 1,29 € en 2018 (indice 107,5) et 1,38 € en 2020 (indice 115).",
    explication=explication(
        resume="Un indice base 100 transforme une grandeur en un nombre « sur 100 » par rapport à une date de référence : l'écart à 100 se lit directement comme un pourcentage d'évolution.",
        lecture=["L'année 2015 est l'année de référence : indice $100$.", "Les indices des autres années sont proportionnels aux prix."],
        observations=["$100 \\times \\dfrac{1{,}29}{1{,}20} = 107{,}5$ : hausse de $7{,}5\\,\\%$ depuis 2015.", "$100 \\times \\dfrac{1{,}38}{1{,}20} = 115$ : hausse de $15\\,\\%$.",
                      "Un indice n'a pas d'unité."],
        pieges=["Lire l'écart entre deux indices quelconques comme un pourcentage : seul l'écart à l'indice $100$ de référence se lit ainsi."],
        a_retenir=["Indice $I$ : évolution de $(I - 100)\\,\\%$ depuis la date de référence."],
    ),
)


NOTION_1 = notion(
    id=ID1, title=N1,
    intro="Avant de parler d'évolutions, il faut savoir comparer une partie à un tout. Une proportion, souvent exprimée en pourcentage, mesure la part d'une sous-population dans une population.",
    pourquoi="Les proportions sont partout : résultats d'élections, parts de marché, composition d'un groupe. Elles permettent de comparer des groupes de tailles différentes.",
    objectif="À la fin de ce cours, tu sauras calculer une proportion et l'écrire en pourcentage, calculer $p\\,\\%$ d'une quantité, retrouver un effectif total et calculer la proportion d'une proportion.",
    definition="La proportion (ou part) d'une partie $A$ dans un ensemble $E$ est le quotient $p = \\dfrac{n_A}{n_E}$ de l'effectif de $A$ par l'effectif total de $E$. Une proportion est toujours comprise entre $0$ (soit $0\\,\\%$) et $1$ (soit $100\\,\\%$). Calculer $p\\,\\%$ d'une quantité, c'est la multiplier par $\\dfrac{p}{100}$. Si $A$ est une partie de $B$, elle-même partie de $E$, la proportion de $A$ dans $E$ est le produit de la proportion de $A$ dans $B$ par la proportion de $B$ dans $E$.",
    explication_simple="Un club compte $480$ adhérents, dont $216$ filles : la proportion de filles est $\\dfrac{216}{480} = 0{,}45$, soit $45\\,\\%$.",
    intuition="Une proportion répond à la question « combien sur $100$ ? » : $45\\,\\%$, c'est $45$ sur $100$.",
    regles=[
        "Proportion : $p = \\dfrac{\\text{effectif de la partie}}{\\text{effectif total}}$, avec $0 \\leqslant p \\leqslant 1$.",
        "Pourcentage : $p = 0{,}45$ s'écrit $45\\,\\%$.",
        "$p\\,\\%$ d'une quantité $Q$ : $Q \\times \\dfrac{p}{100}$.",
        "Effectif total : si une partie d'effectif $n_A$ représente une proportion $p$, alors $n_E = \\dfrac{n_A}{p}$.",
        "Proportion d'une proportion : on multiplie les proportions.",
    ],
    formules=[
        formule("formule-proportion", "Proportion", "$p = \\dfrac{n_A}{n_E}$", "Pour comparer une partie au tout.", "Diviser par l'effectif d'une autre partie.", "Le dénominateur est toujours l'effectif total."),
        formule("formule-pourcentage-de", "$p\\,\\%$ d'une quantité", "$Q \\times \\dfrac{p}{100}$", "Pour calculer une part.", "Diviser par $p$ au lieu de multiplier.", "$15\\,\\%$ de $340$ : $340 \\times 0{,}15$."),
    ],
    methode_titre="Méthode — Calculer et utiliser une proportion",
    etapes=[
        step("search", "blue", "J'identifie l'ensemble de référence (le tout) et la partie étudiée."),
        step("layers", "purple", "Je divise l'effectif de la partie par l'effectif total."),
        step("target", "orange", "J'écris le résultat en décimal puis en pourcentage."),
        step("check", "green", "Je vérifie que le résultat est entre $0$ et $1$."),
    ],
    debutant=[
        step("search", "blue", "Je repère « parmi qui » : c'est le tout."),
        step("layers", "purple", "Je fais partie ÷ tout."),
        step("target", "orange", "Je multiplie par $100$ pour le pourcentage."),
        step("check", "green", "Le pourcentage est entre $0$ et $100$."),
    ],
    rapide=[step("layers", "purple", "Partie ÷ tout."), step("check", "green", "Entre $0$ et $1$.")],
    exemples=[
        ex("exemple-proportion-club", "Exemple 1 — Calculer une proportion",
           "Un club compte $480$ adhérents, dont $216$ filles. Quelle est la proportion de filles ? de garçons ?",
           [calc("p = \\dfrac{216}{480} = 0{,}45"), calc("Garçons : $1 - 0{,}45 = 0{,}55$.")],
           "$45\\,\\%$ de filles et $55\\,\\%$ de garçons.", "facile", "free", conclusion="C'est la figure du cours."),
        ex("exemple-pourcentage-de", "Exemple 2 — Calculer $p\\,\\%$ d'une quantité",
           "Calculer $15\\,\\%$ de $340$ €.",
           [calc("340 \\times \\dfrac{15}{100} = 340 \\times 0{,}15 = 51")],
           "$51$ €.", "facile", "free", conclusion="On multiplie par $\\dfrac{p}{100}$."),
        ex("exemple-effectif-total", "Exemple 3 — Retrouver un effectif total",
           "Dans une classe, $18$ élèves représentent $40\\,\\%$ de l'effectif. Combien d'élèves compte la classe ?",
           [calc("$18 = n_E \\times 0{,}4$, donc $n_E = \\dfrac{18}{0{,}4} = 45$.")],
           "$45$ élèves.", "moyen", "premium", conclusion="On divise la partie par la proportion."),
        ex("exemple-proportion-de-proportion", "Exemple 4 — Proportion d'une proportion",
           "Dans une entreprise, $60\\,\\%$ des salariés sont des femmes, et $25\\,\\%$ d'entre elles sont cadres. Quelle proportion des salariés sont des femmes cadres ?",
           [calc("0{,}6 \\times 0{,}25 = 0{,}15")],
           "$15\\,\\%$ des salariés.", "moyen", "premium", conclusion="« $25\\,\\%$ d'entre elles » : proportion dans les femmes, pas dans l'entreprise."),
        ex("exemple-comparer-proportions", "Exemple 5 — Comparer des groupes de tailles différentes",
           "Classe A : $12$ élèves sur $25$ pratiquent un sport. Classe B : $14$ sur $30$. Quelle classe est la plus sportive ?",
           [calc("A : $\\dfrac{12}{25} = 0{,}48$ ; B : $\\dfrac{14}{30} \\approx 0{,}467$.")],
           "La classe A ($48\\,\\%$ contre environ $46{,}7\\,\\%$).", "moyen", "premium", conclusion="On compare des proportions, pas des effectifs."),
        ex("exemple-fusion-groupes", "Exemple 6 — Réunir deux groupes",
           "Un groupe de $200$ personnes compte $30\\,\\%$ de fumeurs ; un autre de $300$ personnes en compte $50\\,\\%$. Quelle est la proportion de fumeurs dans les deux groupes réunis ?",
           [calc("Fumeurs : $200 \\times 0{,}3 + 300 \\times 0{,}5 = 60 + 150 = 210$."), calc("p = \\dfrac{210}{500} = 0{,}42")],
           "$42\\,\\%$ (et non $40\\,\\%$, moyenne des deux pourcentages).", "difficile", "ultra",
           analyse="Les deux groupes n'ont pas le même effectif.", conclusion="On revient aux effectifs avant de calculer la nouvelle proportion."),
    ],
    erreurs=[
        ("Diviser par l'effectif d'une autre partie.", "On compare filles et garçons au lieu de filles et total.", "Quel est l'ensemble de référence ?", "Le dénominateur est l'effectif total."),
        ("Faire la moyenne de deux pourcentages de groupes différents.", "On oublie les effectifs.", "Les groupes ont-ils la même taille ?", "Reviens aux effectifs."),
        ("Additionner des proportions emboîtées.", "« $25\\,\\%$ des $60\\,\\%$ » lu comme $85\\,\\%$.", "La deuxième proportion porte-t-elle sur le tout ?", "On multiplie : $0{,}6 \\times 0{,}25$."),
        ("Trouver une proportion supérieure à $1$.", "Numérateur et dénominateur inversés.", "La partie est-elle plus petite que le tout ?", "Partie ÷ tout."),
    ],
    astuce="Repère le mot « parmi » ou « d'entre eux » : il désigne l'ensemble de référence, donc le dénominateur.",
    a_retenir=["Proportions et pourcentages : $p = \\dfrac{n_A}{n_E}$, entre $0$ et $1$.", "$p\\,\\%$ de $Q$ : $Q \\times \\dfrac{p}{100}$.", "Proportion d'une proportion : produit."],
    exemples_concrets=["Part des votes d'un candidat.", "Proportion de pièces défectueuses.", "Composition d'une population."],
    figure=FIG1,
    quiz=(81101, 81102, 81103),
    prerequis=["Fractions et pourcentages (collège)"],
    notions_liees=[ID2, ID3],
    objectifs=["Calculer une proportion.", "Calculer $p\\,\\%$ d'une quantité.", "Calculer une proportion de proportion."],
    vocabulaire=["proportion", "part", "pourcentage", "effectif", "ensemble de référence"],
    synonymes=["proportion", "pourcentage d'une quantité", "part d'une population", "proportion de proportion", "calculer un pourcentage"],
    proprietes=["Une proportion est comprise entre $0$ et $1$."],
    tags=["pourcentages", "proportions"],
    difficulte="facile",
    apercu_premium=("Effectif total, proportion de proportion, comparaison",
                    "Trois exemples rédigés : retrouver un effectif total, proportion d'une proportion, comparer deux groupes."),
    apercu_ultra=("Réunir deux groupes, démonstration",
                  "La proportion dans deux groupes réunis et la démonstration de la règle des proportions emboîtées."),
    questions_eclair=[("figure", "Quelle est la proportion de garçons sur la figure ?", "$55\\,\\%$."),
                      ("methode", "$20\\,\\%$ de $150$ ?", "$30$.")],
    demonstration=demonstration(
        "La proportion d'une proportion est le produit des proportions",
        [("Données", "$A \\subset B \\subset E$, d'effectifs $n_A$, $n_B$, $n_E$ ; $p_1 = \\dfrac{n_A}{n_B}$ et $p_2 = \\dfrac{n_B}{n_E}$."),
         ("Produit", "$p_1 \\times p_2 = \\dfrac{n_A}{n_B} \\times \\dfrac{n_B}{n_E}$."),
         ("Simplification", "On simplifie par $n_B \\neq 0$ : $p_1 \\times p_2 = \\dfrac{n_A}{n_E}$."),
         ("Conclusion", "$\\dfrac{n_A}{n_E}$ est la proportion de $A$ dans $E$.")],
        "C'est pourquoi « $25\\,\\%$ de $60\\,\\%$ » se calcule par un produit.",
    ),
)

NOTION_2 = dict(
    _EVOLUTIONS,
    intro="Quand une grandeur change de valeur (prix, population, salaire), on mesure son évolution en pourcentage. Le coefficient multiplicateur relie la valeur de départ à la valeur d'arrivée et permet d'enchaîner les évolutions.",
    pourquoi="Les évolutions en pourcentage sont partout (prix, populations, placements) et préparent l'étude des suites géométriques (chapitre 7).",
    notions_liees=[ID1, ID3],
    prerequis=["Proportions et pourcentages"],
    tags=["pourcentages", "évolutions"],
)

NOTION_3 = notion(
    id=ID3, title=N3,
    intro="Pour suivre l'évolution d'une grandeur dans le temps, on la compare souvent à une valeur de référence à laquelle on attribue l'indice $100$ : les autres valeurs deviennent des indices, faciles à comparer.",
    pourquoi="Les indices sont utilisés par la statistique publique (prix à la consommation, production industrielle) : ils permettent de lire immédiatement une évolution en pourcentage depuis une date de référence.",
    objectif="À la fin de ce cours, tu sauras calculer un indice base $100$, en déduire un taux d'évolution, retrouver une valeur à partir de son indice et comparer des évolutions grâce aux indices.",
    definition="Soient $y_1$ et $y_2$ deux valeurs d'une même grandeur. Définir l'indice base $100$ correspondant à $y_1$, c'est associer à $y_1$ l'indice $I_1 = 100$ ; l'indice $I_2$ associé à $y_2$ est alors obtenu par proportionnalité : $\\dfrac{I_2}{I_1} = \\dfrac{y_2}{y_1}$, donc $I_2 = 100 \\times \\dfrac{y_2}{y_1}$. Le taux d'évolution de $y_1$ à $y_2$ est $t = \\dfrac{I_2 - 100}{100}$.",
    explication_simple="Un prix passe de $1{,}20$ € à $1{,}38$ €. Avec $1{,}20$ € comme référence (indice $100$) : $I = 100 \\times \\dfrac{1{,}38}{1{,}20} = 115$ ; le prix a augmenté de $15\\,\\%$.",
    intuition="Un indice, c'est la valeur ramenée « sur $100$ » : $115$ veut dire « $115$ pour $100$ au départ ».",
    regles=[
        "Indice de référence : $I_1 = 100$ pour la valeur $y_1$.",
        "Indice d'une autre valeur : $I_2 = 100 \\times \\dfrac{y_2}{y_1}$.",
        "Taux d'évolution depuis la référence : $t = \\dfrac{I_2 - 100}{100}$ ; indice $115$ : $+15\\,\\%$, indice $87$ : $-13\\,\\%$.",
        "Valeur à partir de l'indice : $y_2 = y_1 \\times \\dfrac{I_2}{100}$.",
        "Un indice n'a pas d'unité ; deux indices de même base se comparent directement.",
    ],
    formules=[
        formule("formule-indice", "Indice base 100", "$I_2 = 100 \\times \\dfrac{y_2}{y_1}$", "Pour transformer une valeur en indice.", "Inverser $y_1$ et $y_2$.", "La valeur de référence est au dénominateur."),
        formule("formule-indice-taux", "Indice et taux", "$t = \\dfrac{I - 100}{100}$", "Pour lire une évolution depuis la référence.", "Lire l'écart entre deux indices quelconques comme un pourcentage.", "L'écart se lit par rapport à $100$."),
    ],
    methode_titre="Méthode — Calculer et interpréter un indice",
    etapes=[
        step("search", "blue", "Je repère la valeur de référence $y_1$ (indice $100$)."),
        step("layers", "purple", "Je calcule $I_2 = 100 \\times \\dfrac{y_2}{y_1}$."),
        step("target", "orange", "J'interprète : $I_2 - 100$ est l'évolution en pourcentage depuis la référence."),
        step("check", "green", "Je contrôle : indice supérieur à $100$ pour une hausse, inférieur pour une baisse."),
    ],
    debutant=[
        step("search", "blue", "Je trouve l'année (ou la valeur) qui vaut $100$."),
        step("layers", "purple", "Je divise la nouvelle valeur par la valeur de référence."),
        step("target", "orange", "Je multiplie par $100$."),
        step("check", "green", "Plus de $100$ : hausse ; moins de $100$ : baisse."),
    ],
    rapide=[step("layers", "purple", "$100 \\times \\dfrac{y_2}{y_1}$."), step("check", "green", "Écart à $100$ = évolution en %.")],
    exemples=[
        ex("exemple-calcul-indice", "Exemple 1 — Calculer un indice",
           "Un prix vaut $1{,}20$ € en 2015 et $1{,}38$ € en 2020. Calculer l'indice du prix en 2020, base $100$ en 2015, et interpréter.",
           [calc("I = 100 \\times \\dfrac{1{,}38}{1{,}20} = 115")],
           "Indice $115$ : le prix a augmenté de $15\\,\\%$ entre 2015 et 2020.", "facile", "free", conclusion="C'est la figure du cours."),
        ex("exemple-indice-baisse", "Exemple 2 — Un indice inférieur à 100",
           "L'indice d'une production vaut $87$ (base $100$ en 2019). Interpréter.",
           [calc("t = \\dfrac{87 - 100}{100} = -0{,}13")],
           "La production a baissé de $13\\,\\%$ depuis 2019.", "facile", "free", conclusion="Un indice inférieur à $100$ traduit une baisse."),
        ex("exemple-valeur-depuis-indice", "Exemple 3 — Retrouver une valeur",
           "Une ville comptait $2\\,400$ habitants en 2010 (indice $100$). En 2020, l'indice vaut $108{,}5$. Combien d'habitants en 2020 ?",
           [calc("y_2 = 2\\,400 \\times \\dfrac{108{,}5}{100} = 2\\,604")],
           "$2\\,604$ habitants.", "moyen", "premium", conclusion="On multiplie la valeur de référence par $\\dfrac{I}{100}$."),
        ex("exemple-comparer-indices", "Exemple 4 — Comparer deux évolutions",
           "Le loyer A passe de $500$ € à $620$ € ; le loyer B de $750$ € à $900$ €. Comparer leurs évolutions grâce aux indices (base $100$ au départ).",
           [calc("A : $100 \\times \\dfrac{620}{500} = 124$ ; B : $100 \\times \\dfrac{900}{750} = 120$.")],
           "Le loyer A a davantage augmenté ($+24\\,\\%$ contre $+20\\,\\%$).", "moyen", "premium", conclusion="Les indices effacent la différence de niveau de départ."),
        ex("exemple-changer-base", "Exemple 5 — Changer d'année de référence",
           "Base $100$ en 2018, un indice vaut $110$ en 2020 et $121$ en 2022. Quel est l'indice de 2022 en prenant 2020 comme base $100$ ?",
           [calc("I = 100 \\times \\dfrac{121}{110} = 110")],
           "Indice $110$ : $+10\\,\\%$ entre 2020 et 2022.", "moyen", "premium", conclusion="Les indices sont proportionnels aux valeurs : on peut changer de base."),
        ex("exemple-indice-evolutions", "Exemple 6 — Indice et évolutions successives",
           "Base $100$ en 2020. Une grandeur augmente de $20\\,\\%$ en 2021 puis baisse de $10\\,\\%$ en 2022. Quel est son indice en 2022 ? Quelle est l'évolution globale ?",
           [calc("Indice 2021 : $100 \\times 1{,}2 = 120$ ; indice 2022 : $120 \\times 0{,}9 = 108$.")],
           "Indice $108$ : hausse globale de $8\\,\\%$, et non de $10\\,\\%$.", "difficile", "ultra",
           conclusion="L'indice applique les coefficients multiplicateurs successifs."),
    ],
    erreurs=[
        ("Lire l'écart entre deux indices quelconques comme un pourcentage.", "Indices $110$ et $121$ : « $+11\\,\\%$ ».", "Le premier indice vaut-il $100$ ?", "Calcule $100 \\times \\dfrac{121}{110}$."),
        ("Inverser valeur de référence et nouvelle valeur.", "On divise par la mauvaise valeur.", "Quelle valeur correspond à l'indice $100$ ?", "La référence est au dénominateur."),
        ("Donner une unité à un indice.", "On recopie l'unité de la grandeur.", "Un indice est-il un prix ?", "Un indice est un nombre sans unité."),
        ("Additionner des évolutions au lieu de les enchaîner.", "« $+20\\,\\%$ puis $-10\\,\\%$ » lu comme $+10\\,\\%$.", "Les coefficients se multiplient-ils ?", "$1{,}2 \\times 0{,}9 = 1{,}08$."),
    ],
    astuce="Pour lire un indice, retire $100$ : indice $123$, hausse de $23\\,\\%$ ; indice $94$, baisse de $6\\,\\%$ — toujours depuis la date de référence.",
    a_retenir=["Indices base 100 : $I_2 = 100 \\times \\dfrac{y_2}{y_1}$.", "Indice $I$ : évolution de $(I - 100)\\,\\%$ depuis la référence.", "Valeur : $y_2 = y_1 \\times \\dfrac{I_2}{100}$."],
    exemples_concrets=["Indice des prix à la consommation.", "Évolution d'une population depuis un recensement.", "Comparaison de loyers."],
    figure=FIG3,
    quiz=(81301, 81302, 81303),
    prerequis=["Évolutions et taux"],
    notions_liees=[ID1, ID2],
    objectifs=["Calculer un indice base 100.", "En déduire un taux d'évolution.", "Retrouver une valeur à partir de son indice."],
    vocabulaire=["indice", "base 100", "valeur de référence", "taux d'évolution"],
    synonymes=["indice base 100", "indice", "année de référence", "calculer un indice", "indice des prix"],
    proprietes=["Les indices sont proportionnels aux valeurs de la grandeur."],
    tags=["pourcentages", "indices"],
    difficulte="facile",
    apercu_premium=("Valeur depuis un indice, comparaison, changement de base",
                    "Trois exemples rédigés : retrouver une valeur, comparer deux évolutions, changer d'année de référence."),
    apercu_ultra=("Indice et évolutions successives, démonstration",
                  "Un indice obtenu par évolutions successives et la démonstration du lien entre indice et taux d'évolution."),
    questions_eclair=[("figure", "Quelle est la hausse du prix entre 2015 et 2018 ?", "$7{,}5\\,\\%$."),
                      ("methode", "Indice $92$ : évolution depuis la référence ?", "Baisse de $8\\,\\%$.")],
    demonstration=demonstration(
        "Le taux d'évolution depuis la référence vaut $\\dfrac{I_2 - 100}{100}$",
        [("Taux", "Le taux d'évolution de $y_1$ à $y_2$ est $t = \\dfrac{y_2 - y_1}{y_1} = \\dfrac{y_2}{y_1} - 1$."),
         ("Indice", "Par définition, $\\dfrac{y_2}{y_1} = \\dfrac{I_2}{100}$."),
         ("Substitution", "$t = \\dfrac{I_2}{100} - 1 = \\dfrac{I_2 - 100}{100}$."),
         ("Conclusion", "L'écart de l'indice à $100$ donne directement le taux d'évolution en pourcentage.")],
        "C'est tout l'intérêt de la base $100$.",
    ),
)

CHAPTER = chapter(1, "Pourcentages", "layers", [NOTION_1, NOTION_2, NOTION_3])
