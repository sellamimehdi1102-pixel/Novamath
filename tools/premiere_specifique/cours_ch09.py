"""Chapitre 9 — Loi de Bernoulli et loi binomiale (Première spécifique, manuel
« Première ES/L », Ch. 9 : expériences indépendantes, répétition ; loi de
Bernoulli ; schéma de Bernoulli, coefficients binomiaux, loi binomiale ;
représentation graphique ; intervalle de fluctuation et règle de décision).

Créé lors de l'adaptation du 2026-10-26 (voir PREMIERE_SPECIFIQUE_SUIVI.md) :
« Expériences indépendantes et loi de Bernoulli » reprend l'identifiant et des
exemples de l'ancienne notion « Épreuves indépendantes et épreuves de
Bernoulli » (sans Monte-Carlo ni marche aléatoire, hors manuel) ; l'arbre de
trois épreuves de cette notion illustre la loi binomiale ; les deux autres
notions sont créées. Probabilités binomiales calculées par `math.comb`.
"""
from math import comb

from premiere_specifique.cours_commun import calc, chapter, code, demonstration, ex, explication, figure_geom, formule, notion, pt, step, text
from premiere_specifique.reserve.cours_ch09 import FIG4 as _ARBRE_TROIS_EPREUVES

N1, N2, N3 = "Expériences indépendantes et loi de Bernoulli", "Schéma de Bernoulli et loi binomiale", "Échantillonnage et règle de décision"
ID1, ID2, ID3 = "epreuves-independantes-et-epreuves-de-bernoulli", "schema-de-bernoulli-et-loi-binomiale", "echantillonnage-et-regle-de-decision"


def _s(a, b, **kw):
    s = {"from": {"x": a[0], "y": a[1]}, "to": {"x": b[0], "y": b[1]}}
    s.update({k: v for k, v in kw.items() if v is not None})
    return s


def _binom(n, p, k):
    return comb(n, k) * p ** k * (1 - p) ** (n - k)


# Figure 1 : une épreuve de Bernoulli et sa variable aléatoire.
FIG1 = figure_geom(
    view=[-0.6, -3.4, 11.2, 6.8], axes=False,
    points=[pt(0, 0, ""), pt(4, 2, "S"), pt(4, -2, "\\overline{S}")],
    segments=[_s((0, 0), (4, 2)), _s((0, 0), (4, -2))],
    texts=[text((1.6, 1.6), "p"), text((1.6, -1.6), "1 − p"), text((6.2, 2.0), "X = 1", reveal=2), text((6.2, -2.0), "X = 0", reveal=2),
           text((8.6, 0.6), "E(X) = p", reveal=3), text((8.6, -0.6), "V(X) = p(1 − p)", reveal=3)],
    steps=["Une épreuve à deux issues : succès S, échec S̄", "X vaut 1 en cas de succès, 0 sinon", "Espérance p, variance p(1 − p)"],
    relation="$P(X = 1) = p$ ; $P(X = 0) = 1 - p$",
    alt="Arbre d'une épreuve de Bernoulli : branche succès S de probabilité p (X = 1), branche échec S̄ de probabilité 1 − p (X = 0) ; E(X) = p et V(X) = p(1 − p).",
    explication=explication(
        resume="Une épreuve de Bernoulli n'a que deux issues, succès et échec. La variable aléatoire qui vaut $1$ en cas de succès et $0$ sinon suit la loi de Bernoulli de paramètre $p$.",
        lecture=["La branche du haut : succès, probabilité $p$.", "La branche du bas : échec, probabilité $1 - p$."],
        observations=["$E(X) = 0 \\times (1 - p) + 1 \\times p = p$.", "$E(X^2) = p$, donc $V(X) = p - p^2 = p(1 - p)$.", "Avec $p = 0{,}02$ : $\\sigma(X) = \\sqrt{0{,}0196} = 0{,}14$."],
        pieges=["Oublier que les deux probabilités ont pour somme $1$."],
        a_retenir=["Bernoulli de paramètre $p$ : $E(X) = p$, $V(X) = p(1 - p)$."],
    ),
)

# Figure 2 : arbre de trois épreuves (repris de l'ancienne notion), explication adaptée à la loi binomiale.
FIG2 = dict(_ARBRE_TROIS_EPREUVES)
FIG2["explication"] = explication(
    resume="Dans un schéma de Bernoulli, chaque chemin à $k$ succès a pour probabilité $p^k(1 - p)^{n - k}$. Le nombre de ces chemins est le coefficient binomial $\\binom{n}{k}$.",
    lecture=["Chaque nœud se divise en succès $S$ (probabilité $p$) et échec $\\overline{S}$ (probabilité $1 - p$).", "Trois niveaux : $2^3 = 8$ chemins."],
    observations=["Chemins à $2$ succès : $SS\\overline{S}$, $S\\overline{S}S$, $\\overline{S}SS$ : $\\binom{3}{2} = 3$.",
                  "Avec $p = \\dfrac{1}{4}$ : $P(X = 2) = 3 \\times \\dfrac{1}{16} \\times \\dfrac{3}{4} = \\dfrac{9}{64}$.",
                  "$X$, nombre de succès, suit la loi binomiale $\\mathcal{B}(3 ; p)$."],
    pieges=["Oublier des chemins, ou compter $p^2$ sans le facteur $1 - p$."],
    a_retenir=["$P(X = k) = \\binom{n}{k} p^k (1 - p)^{n - k}$."],
)

# Figure 3 : loi B(50 ; 0,3) et intervalle de fluctuation [9 ; 22] (échelle verticale × 40).
_N3, _P3, _A, _B = 50, 0.3, 9, 22
FIG3 = figure_geom(
    view=[3.0, -1.6, 22.0, 7.4], axes=False, points=[],
    segments=[_s((4, 0), (24, 0))]
             + [_s((k - 1, 0), (k - 1, round(40 * _binom(_N3, _P3, k), 3)),
                   tooltip=f"P(X = {k}) ≈ {str(round(_binom(_N3, _P3, k), 4)).replace('.', ',')}") for k in range(5, 26)]
             + [_s((14, 0), (14, 5.4), dashed=True, reveal=2, tooltip="E(X) = 15"),
                _s((_A - 1, -0.6), (_B - 1, -0.6), reveal=3, tooltip="au moins 95 % des valeurs"),
                _s((_A - 1, -0.9), (_A - 1, -0.3), reveal=3), _s((_B - 1, -0.9), (_B - 1, -0.3), reveal=3)],
    texts=[text((k - 1, -1.3), str(k)) for k in (5, 9, 15, 22, 25)] + [text((19.5, 5.8), "B(50 ; 0,3)"), text((14.0, 5.9), "E(X) = 15", reveal=2),
                                                                      text((15.5, -0.15), "de 9 à 22", reveal=3)],
    steps=["La loi binomiale B(50 ; 0,3) : diagramme en bâtons", "Les valeurs les plus probables sont autour de E(X) = 15", "De a = 9 à b = 22 : au moins 95 % de la probabilité"],
    relation="Intervalle de fluctuation à $95\\,\\%$ de la fréquence : $\\left[\\dfrac{9}{50} ; \\dfrac{22}{50}\\right] = [0{,}18 ; 0{,}44]$",
    alt="Diagramme en bâtons de la loi binomiale de paramètres 50 et 0,3, centré autour de 15 ; les bâtons de 9 à 22 sont mis en évidence : ils regroupent au moins 95 % de la probabilité.",
    explication=explication(
        resume="Les valeurs d'une loi binomiale se concentrent autour de l'espérance $np$. L'intervalle de fluctuation à $95\\,\\%$ regroupe les valeurs centrales, de probabilité totale au moins $0{,}95$.",
        lecture=["En abscisse : le nombre de succès $k$ ; en hauteur : $P(X = k)$ (échelle $\\times 40$).", "Les bâtons hors de $[9 ; 22]$ sont très petits."],
        observations=["$E(X) = 50 \\times 0{,}3 = 15$.", "$P(X \\leqslant 8) \\approx 0{,}018$ et $P(X \\leqslant 9) \\approx 0{,}040$ : $a = 9$.",
                      "$P(X \\leqslant 21) \\approx 0{,}975$ (un peu moins) et $P(X \\leqslant 22) \\approx 0{,}988$ : $b = 22$."],
        pieges=["Confondre l'intervalle pour le nombre de succès $[a ; b]$ et celui pour la fréquence $\\left[\\dfrac{a}{n} ; \\dfrac{b}{n}\\right]$."],
        a_retenir=["$a$ : plus petit entier tel que $P(X \\leqslant a) > 0{,}025$ ; $b$ : plus petit entier tel que $P(X \\leqslant b) \\geqslant 0{,}975$."],
    ),
)


NOTION_1 = notion(
    id=ID1, title=N1,
    intro="Beaucoup d'expériences enchaînent des épreuves qui ne s'influencent pas : lancers successifs, tirages avec remise. Quand une épreuve n'a que deux issues, succès ou échec, on parle d'épreuve de Bernoulli : c'est la brique de base de la loi binomiale.",
    pourquoi="Contrôler des pièces, répondre au hasard à un QCM, jouer plusieurs fois au même jeu : ces situations se modélisent par des épreuves de Bernoulli indépendantes.",
    objectif="À la fin de ce cours, tu sauras reconnaître des expériences indépendantes, calculer la probabilité d'une succession d'issues par un produit, et donner la loi, l'espérance, la variance et l'écart-type d'une variable de Bernoulli.",
    definition="Deux expériences aléatoires sont indépendantes lorsque les résultats de l'une n'influent pas sur les probabilités des issues de l'autre ; répéter une même expérience dans les mêmes conditions initiales donne des expériences indépendantes. Si l'on répète $n$ fois une expérience dans les mêmes conditions et si $A_i$ est un événement de la $i$-ème expérience, alors $P(A_1 \\cap A_2 \\cap \\dots \\cap A_n) = P(A_1) \\times P(A_2) \\times \\dots \\times P(A_n)$. Une épreuve de Bernoulli de paramètre $p \\in [0 ; 1]$ est une expérience à deux issues : succès $S$ (probabilité $p$) et échec $\\overline{S}$ (probabilité $1 - p$). La variable aléatoire $X$ qui vaut $1$ si $S$ est réalisé et $0$ sinon suit la loi de Bernoulli de paramètre $p$ : $P(X = 1) = p$, $P(X = 0) = 1 - p$ ; alors $E(X) = p$, $V(X) = p(1 - p)$ et $\\sigma(X) = \\sqrt{p(1 - p)}$.",
    explication_simple="Une pièce truquée donne « face » avec la probabilité $0{,}7$ ; quatre lancers indépendants : $P(\\text{4 fois face}) = 0{,}7^4 = 0{,}2401$.",
    intuition="Indépendance : on multiplie les probabilités le long d'un chemin. Bernoulli : on ne regarde qu'une question, « succès ou pas ? ».",
    regles=[
        "Tirages avec remise, lancers successifs : expériences indépendantes ; tirages sans remise : en général non.",
        "Répétition dans les mêmes conditions : $P(A_1 \\cap \\dots \\cap A_n) = P(A_1) \\times \\dots \\times P(A_n)$.",
        "Épreuve de Bernoulli : deux issues, succès ($p$) et échec ($1 - p$).",
        "Loi de Bernoulli : $P(X = 1) = p$, $P(X = 0) = 1 - p$.",
        "$E(X) = p$ ; $V(X) = p(1 - p)$ ; $\\sigma(X) = \\sqrt{p(1 - p)}$.",
    ],
    formules=[
        formule("formule-produit-independance", "Répétition", "$P(A_1 \\cap \\dots \\cap A_n) = P(A_1) \\times \\dots \\times P(A_n)$", "Pour des expériences indépendantes.", "L'appliquer à des tirages sans remise.", "Vérifie d'abord l'indépendance."),
        formule("formule-bernoulli", "Loi de Bernoulli", "$E(X) = p$ ; $V(X) = p(1 - p)$", "Pour une variable qui vaut $0$ ou $1$.", "Écrire $V(X) = p^2$.", "$V(X) = E(X^2) - E(X)^2 = p - p^2$."),
    ],
    methode_titre="Méthode — Modéliser par des épreuves indépendantes",
    etapes=[
        step("search", "blue", "Je vérifie que les épreuves se répètent dans les mêmes conditions (avec remise, lancers successifs…)."),
        step("layers", "purple", "J'identifie le succès et son paramètre $p$."),
        step("target", "orange", "Je calcule la probabilité d'une succession d'issues par un produit."),
        step("check", "green", "Je contrôle avec l'événement contraire quand c'est plus simple."),
    ],
    debutant=[
        step("search", "blue", "Je me demande si un résultat change les probabilités du suivant."),
        step("layers", "purple", "Je note ce qu'est un succès et sa probabilité."),
        step("target", "orange", "Je multiplie les probabilités sur le chemin."),
        step("check", "green", "Le résultat est entre $0$ et $1$."),
    ],
    rapide=[step("layers", "purple", "Indépendance : produit."), step("check", "green", "Bernoulli : $E = p$, $V = p(1 - p)$.")],
    exemples=[
        ex("exemple-epreuves-tableau", "Exemple 1 — Deux expériences indépendantes",
           "On lance une pièce équilibrée puis un dé équilibré. Probabilité d'obtenir « face » et un nombre pair ?",
           [calc("Les deux expériences sont indépendantes."), calc("P = \\dfrac{1}{2} \\times \\dfrac{1}{2} = \\dfrac{1}{4}")],
           "$\\dfrac{1}{4}$.", "facile", "free", conclusion="Expériences indépendantes : on multiplie."),
        ex("exemple-quatre-lancers", "Exemple 2 — Répéter une même expérience",
           "Une pièce truquée donne « face » avec la probabilité $0{,}7$. On la lance $4$ fois. Probabilité d'obtenir $4$ fois « face » ?",
           [calc("Les lancers sont indépendants."), calc("P(F_1 \\cap F_2 \\cap F_3 \\cap F_4) = 0{,}7^4 = 0{,}2401")],
           "$0{,}2401$.", "facile", "free", conclusion="C'est le chemin supérieur de l'arbre."),
        ex("exemple-loi-bernoulli", "Exemple 3 — Une variable de Bernoulli",
           "Dans une usine, un article présente un défaut avec la probabilité $0{,}02$. $X$ vaut $1$ si l'article est défectueux, $0$ sinon. Donner la loi de $X$, $E(X)$, $V(X)$ et $\\sigma(X)$.",
           [calc("$P(X = 1) = 0{,}02$ et $P(X = 0) = 0{,}98$."), calc("E(X) = 0{,}02 \\quad V(X) = 0{,}02 \\times 0{,}98 = 0{,}0196"), calc("\\sigma(X) = \\sqrt{0{,}0196} = 0{,}14")],
           "$E(X) = 0{,}02$, $V(X) = 0{,}0196$, $\\sigma(X) = 0{,}14$.", "moyen", "premium", conclusion="Loi de Bernoulli de paramètre $0{,}02$."),
        ex("exemple-deux-tirs", "Exemple 4 — Exactement une réussite",
           "Un tireur atteint sa cible avec la probabilité $0{,}7$. Il tire deux fois, de façon indépendante. Probabilité d'exactement une réussite ?",
           [calc("Chemins $S\\overline{S}$ et $\\overline{S}S$ : $0{,}7 \\times 0{,}3 + 0{,}3 \\times 0{,}7 = 0{,}42$.")],
           "$0{,}42$.", "moyen", "premium", conclusion="Deux chemins de même probabilité."),
        ex("exemple-avec-sans-remise", "Exemple 5 — Avec ou sans remise",
           "Une urne contient $3$ boules rouges et $2$ vertes. On tire deux boules. Les deux tirages sont-ils indépendants avec remise ? sans remise ?",
           [calc("Avec remise : l'urne est la même au second tirage, $P(R_2) = \\dfrac{3}{5}$ quel que soit le premier tirage."),
            calc("Sans remise : si la première est rouge, $P(R_2) = \\dfrac{2}{4}$ ; si elle est verte, $\\dfrac{3}{4}$.")],
           "Indépendants avec remise, pas sans remise.", "moyen", "premium", conclusion="Le protocole décide de l'indépendance."),
        ex("exemple-variance-max", "Exemple 6 — Quand la variance est-elle maximale ?",
           "Pour quelle valeur de $p$ la variance $p(1 - p)$ d'une loi de Bernoulli est-elle maximale ?",
           [calc("$p(1 - p) = -p^2 + p$ : trinôme de coefficient $a = -1 < 0$, maximal en $\\alpha = -\\dfrac{1}{2 \\times (-1)} = \\dfrac{1}{2}$."),
            calc("Maximum : $\\dfrac{1}{2} \\times \\dfrac{1}{2} = \\dfrac{1}{4}$.")],
           "Pour $p = \\dfrac{1}{2}$ ; la variance vaut alors $\\dfrac{1}{4}$.", "difficile", "ultra",
           conclusion="L'incertitude est la plus grande quand succès et échec sont également probables."),
    ],
    erreurs=[
        ("Supposer l'indépendance pour des tirages sans remise.", "On ne regarde pas le protocole.", "La composition de l'urne change-t-elle ?", "Sans remise : pas indépendants."),
        ("Additionner les probabilités le long d'un chemin.", "Confusion entre « et » et « ou ».", "Les issues se succèdent-elles ?", "Le long d'un chemin, on multiplie."),
        ("Écrire $V(X) = p^2$ pour une loi de Bernoulli.", "On élève $E(X)$ au carré.", "As-tu soustrait $E(X)^2$ de $E(X^2)$ ?", "$V(X) = p - p^2 = p(1 - p)$."),
        ("Oublier que l'échec a la probabilité $1 - p$.", "On ne garde que $p$.", "La somme des probabilités vaut-elle $1$ ?", "$P(X = 0) = 1 - p$."),
    ],
    astuce="Pour « au moins un succès » sur $n$ épreuves indépendantes, calcule plutôt le contraire : $1 - (1 - p)^n$.",
    a_retenir=["Expériences indépendantes et loi de Bernoulli : on multiplie le long d'un chemin.", "Bernoulli : $P(X = 1) = p$, $P(X = 0) = 1 - p$.", "$E(X) = p$, $V(X) = p(1 - p)$."],
    exemples_concrets=["Lancers successifs d'une pièce.", "Contrôle d'un article (défectueux ou non).", "Tirages avec remise."],
    figure=FIG1,
    quiz=(69401, 69402, 89101),
    prerequis=["Variables aléatoires", "Rappels de probabilités : événements"],
    notions_liees=[ID2],
    objectifs=["Reconnaître des expériences indépendantes.", "Calculer la probabilité d'une succession d'issues.", "Utiliser la loi de Bernoulli."],
    vocabulaire=["expériences indépendantes", "épreuve de Bernoulli", "succès", "échec", "loi de Bernoulli"],
    synonymes=["épreuve de Bernoulli", "loi de Bernoulli", "expériences indépendantes", "succès et échec", "tirage avec remise"],
    proprietes=["Loi de Bernoulli : $E(X) = p$ et $V(X) = p(1 - p)$."],
    tags=["probabilités", "Bernoulli"],
    difficulte="facile",
    apercu_premium=("Variable de Bernoulli, exactement une réussite, avec ou sans remise",
                    "Trois exemples rédigés : loi, espérance et variance d'une variable de Bernoulli, deux tirs, indépendance selon le protocole."),
    apercu_ultra=("Variance maximale, démonstration",
                  "La valeur de $p$ qui rend la variance maximale, et la démonstration de $E(X) = p$ et $V(X) = p(1 - p)$."),
    questions_eclair=[("figure", "Que vaut $V(X)$ si $p = 0{,}5$ ?", "$0{,}25$."),
                      ("methode", "$3$ lancers d'une pièce équilibrée : probabilité de « 3 piles » ?", "$0{,}125$.")],
    demonstration=demonstration(
        "Espérance et variance d'une loi de Bernoulli",
        [("Loi", "$P(X = 0) = 1 - p$ et $P(X = 1) = p$."),
         ("Espérance", "$E(X) = 0 \\times (1 - p) + 1 \\times p = p$."),
         ("Carré", "$X^2 = X$ (car $0^2 = 0$ et $1^2 = 1$), donc $E(X^2) = p$."),
         ("Variance", "$V(X) = E(X^2) - E(X)^2 = p - p^2 = p(1 - p)$, et $\\sigma(X) = \\sqrt{p(1 - p)}$.")],
        "La formule de König-Huygens (chapitre 8) donne directement la variance.",
    ),
)

NOTION_2 = notion(
    id=ID2, title=N2,
    intro="En répétant plusieurs fois, de façon indépendante, la même épreuve de Bernoulli, on obtient un schéma de Bernoulli. Le nombre de succès suit alors une loi binomiale, que l'on calcule en comptant les chemins de l'arbre.",
    pourquoi="La loi binomiale modélise le nombre de pièces défectueuses dans un lot, de bonnes réponses à un QCM, de victoires sur plusieurs parties : c'est la loi de probabilité la plus utilisée en Première.",
    objectif="À la fin de ce cours, tu sauras reconnaître une loi binomiale et ses paramètres, interpréter un coefficient binomial comme un nombre de chemins, calculer $P(X = k)$, et donner l'espérance, la variance et l'écart-type.",
    definition="Un schéma de Bernoulli est la répétition de $n$ épreuves de Bernoulli identiques (même paramètre $p$) et indépendantes ; l'arbre associé possède $2^n$ chemins. Pour $0 \\leqslant k \\leqslant n$, le coefficient binomial $\\binom{n}{k}$ (« $k$ parmi $n$ ») est le nombre de chemins de l'arbre comportant exactement $k$ succès ; $\\binom{n}{0} = \\binom{n}{n} = 1$ et $\\binom{n}{1} = n$. La variable aléatoire $X$ égale au nombre de succès suit la loi binomiale de paramètres $n$ et $p$, notée $\\mathcal{B}(n ; p)$ : pour tout entier $k$ de $0$ à $n$, $P(X = k) = \\binom{n}{k} p^k (1 - p)^{n - k}$. De plus, $E(X) = np$, $V(X) = np(1 - p)$ et $\\sigma(X) = \\sqrt{np(1 - p)}$.",
    explication_simple="On joue $7$ fois à un jeu où l'on gagne avec la probabilité $0{,}4$, de façon indépendante : le nombre de victoires suit $\\mathcal{B}(7 ; 0{,}4)$, d'espérance $7 \\times 0{,}4 = 2{,}8$.",
    intuition="Tous les chemins à $k$ succès ont la même probabilité $p^k(1 - p)^{n - k}$ : il suffit de savoir combien il y en a, c'est $\\binom{n}{k}$.",
    regles=[
        "Reconnaître une loi binomiale : $n$ épreuves identiques, indépendantes, à deux issues ; $X$ compte les succès.",
        "$\\binom{n}{k}$ : nombre de chemins à $k$ succès ; $\\binom{n}{0} = \\binom{n}{n} = 1$, $\\binom{n}{1} = n$.",
        "$P(X = k) = \\binom{n}{k} p^k (1 - p)^{n - k}$.",
        "$E(X) = np$ ; $V(X) = np(1 - p)$ ; $\\sigma(X) = \\sqrt{np(1 - p)}$.",
        "La calculatrice donne les coefficients binomiaux, $P(X = k)$ et $P(X \\leqslant k)$. Texas Instruments : « math », « PRB », « Combinaison » pour $\\binom{n}{k}$ ; « distrib » (« 2nde », « var ») pour " + code("binomFdp(n,p,k)") + " $= P(X = k)$ et " + code("binomFrép(n,p,k)") + " $= P(X \\leqslant k)$. Casio : « OPTN », « PROB », « nCr » pour $\\binom{n}{k}$ ; « OPTN », « STAT », « DIST », « BINM » pour " + code("binomialPD(k,n,p)") + " et " + code("binomialCD(k,n,p)") + ".",
    ],
    formules=[
        formule("formule-binomiale", "Loi binomiale", "$P(X = k) = \\binom{n}{k} p^k (1 - p)^{n - k}$", "Pour $k$ succès exactement.", "Oublier le coefficient binomial.", "Compte les chemins, puis multiplie par la probabilité d'un chemin."),
        formule("formule-esperance-binomiale", "Espérance", "$E(X) = np$", "Pour le nombre moyen de succès.", "Écrire $E(X) = p$.", "En moyenne, $p$ succès par épreuve, donc $np$ sur $n$ épreuves."),
    ],
    methode_titre="Méthode — Utiliser une loi binomiale",
    etapes=[
        step("search", "blue", "Je justifie le schéma de Bernoulli : épreuves identiques, indépendantes, deux issues."),
        step("layers", "purple", "J'identifie $n$ et $p$ et j'écris $X \\sim \\mathcal{B}(n ; p)$."),
        step("target", "orange", "Je calcule $P(X = k)$ par la formule (ou la calculatrice), $P(X \\geqslant 1)$ par le contraire."),
        step("check", "green", "Je contrôle l'ordre de grandeur avec $E(X) = np$."),
    ],
    debutant=[
        step("search", "blue", "Je repère le nombre de répétitions $n$."),
        step("layers", "purple", "Je repère la probabilité de succès $p$."),
        step("target", "orange", "Je compte les chemins à $k$ succès et je multiplie."),
        step("check", "green", "Je compare à $np$."),
    ],
    rapide=[step("layers", "purple", "$\\binom{n}{k} p^k (1 - p)^{n - k}$."), step("check", "green", "$E(X) = np$.")],
    exemples=[
        ex("exemple-compter-chemins", "Exemple 1 — Compter des chemins",
           "Dans l'arbre de $3$ épreuves de Bernoulli, combien de chemins comportent exactement $2$ succès ? En déduire $\\binom{3}{2}$.",
           [calc("Chemins : $SS\\overline{S}$, $S\\overline{S}S$, $\\overline{S}SS$.")], "$3$ chemins : $\\binom{3}{2} = 3$.", "facile", "free",
           conclusion="C'est la figure du cours."),
        ex("exemple-reconnaitre-binomiale", "Exemple 2 — Reconnaître une loi binomiale",
           "On joue $7$ fois à un jeu ; à chaque partie, on gagne avec la probabilité $0{,}4$, indépendamment des autres. $X$ est le nombre de victoires. Quelle est la loi de $X$ ? Son espérance ?",
           [calc("$7$ épreuves identiques et indépendantes, succès « gagner » de probabilité $0{,}4$."), calc("E(X) = 7 \\times 0{,}4 = 2{,}8")],
           "$X \\sim \\mathcal{B}(7 ; 0{,}4)$ et $E(X) = 2{,}8$.", "facile", "free", conclusion="On justifie toujours le schéma de Bernoulli."),
        ex("exemple-calcul-binomiale", "Exemple 3 — Calculer $P(X = k)$",
           "$X \\sim \\mathcal{B}(5 ; 0{,}2)$. Calculer $P(X = 2)$.",
           [calc("$\\binom{5}{2} = 10$ chemins à $2$ succès."), calc("P(X = 2) = 10 \\times 0{,}2^2 \\times 0{,}8^3 = 10 \\times 0{,}04 \\times 0{,}512 = 0{,}2048")],
           "$P(X = 2) = 0{,}2048$.", "moyen", "premium", conclusion="Nombre de chemins $\\times$ probabilité d'un chemin."),
        ex("exemple-esperance-binomiale", "Exemple 4 — Espérance et écart-type",
           "$X \\sim \\mathcal{B}(20 ; 0{,}3)$. Calculer $E(X)$, $V(X)$ et $\\sigma(X)$.",
           [calc("E(X) = 20 \\times 0{,}3 = 6"), calc("V(X) = 20 \\times 0{,}3 \\times 0{,}7 = 4{,}2"), calc("\\sigma(X) = \\sqrt{4{,}2} \\approx 2{,}05")],
           "$E(X) = 6$, $V(X) = 4{,}2$, $\\sigma(X) \\approx 2{,}05$.", "moyen", "premium", conclusion="En moyenne $6$ succès sur $20$ épreuves."),
        ex("exemple-au-moins-un", "Exemple 5 — Au moins un succès",
           "$X \\sim \\mathcal{B}(5 ; 0{,}2)$. Calculer $P(X \\geqslant 1)$.",
           [calc("Contraire : $P(X = 0) = 0{,}8^5 = 0{,}32768$."), calc("P(X \\geqslant 1) = 1 - 0{,}32768 = 0{,}67232")],
           "$P(X \\geqslant 1) = 0{,}67232$.", "moyen", "premium", conclusion="Le contraire évite cinq calculs."),
        ex("exemple-cumul", "Exemple 6 — Probabilité cumulée",
           "Un lot de $10$ pièces ; chaque pièce est défectueuse avec la probabilité $0{,}1$, indépendamment. Probabilité qu'il y ait au plus une pièce défectueuse ?",
           [calc("$X \\sim \\mathcal{B}(10 ; 0{,}1)$."), calc("P(X = 0) = 0{,}9^{10} \\approx 0{,}3487 \\quad P(X = 1) = 10 \\times 0{,}1 \\times 0{,}9^9 \\approx 0{,}3874"),
            calc("P(X \\leqslant 1) \\approx 0{,}3487 + 0{,}3874 = 0{,}7361")],
           "$P(X \\leqslant 1) \\approx 0{,}736$.", "difficile", "ultra", conclusion="La calculatrice donne directement $P(X \\leqslant 1)$."),
    ],
    erreurs=[
        ("Oublier le coefficient binomial.", "On calcule la probabilité d'un seul chemin.", "Combien de chemins comportent $k$ succès ?", "Multiplie par $\\binom{n}{k}$."),
        ("Utiliser la loi binomiale pour des tirages sans remise.", "Épreuves non indépendantes.", "Les épreuves sont-elles indépendantes et identiques ?", "Vérifie le schéma de Bernoulli."),
        ("Inverser les exposants $k$ et $n - k$.", "Confusion succès/échecs.", "Quel exposant pour $p$ ?", "$p$ à la puissance du nombre de succès."),
        ("Écrire $V(X) = np$.", "On recopie l'espérance.", "As-tu le facteur $1 - p$ ?", "$V(X) = np(1 - p)$."),
    ],
    astuce="Avant tout calcul, écris la phrase : « On répète $n$ fois, de façon indépendante, la même épreuve de Bernoulli de paramètre $p$ ; $X$ compte les succès, donc $X \\sim \\mathcal{B}(n ; p)$. »",
    a_retenir=["Schéma de Bernoulli et loi binomiale : $P(X = k) = \\binom{n}{k} p^k (1 - p)^{n - k}$.", "$\\binom{n}{k}$ : nombre de chemins à $k$ succès.",
               "$E(X) = np$, $V(X) = np(1 - p)$, $\\sigma(X) = \\sqrt{np(1 - p)}$."],
    exemples_concrets=["Nombre de pièces défectueuses dans un lot.", "Bonnes réponses au hasard à un QCM.", "Nombre de victoires sur plusieurs parties."],
    figure=FIG2,
    quiz=(69403, 89201, 89202),
    prerequis=["Expériences indépendantes et loi de Bernoulli"],
    notions_liees=[ID1, ID3],
    objectifs=["Reconnaître une loi binomiale.", "Calculer $P(X = k)$ et $P(X \\geqslant 1)$.", "Calculer $E(X)$, $V(X)$, $\\sigma(X)$."],
    vocabulaire=["schéma de Bernoulli", "coefficient binomial", "loi binomiale", "paramètres $n$ et $p$"],
    synonymes=["loi binomiale", "schéma de Bernoulli", "coefficient binomial", "k parmi n", "B(n ; p)", "espérance d'une loi binomiale"],
    proprietes=["$E(X) = np$ et $V(X) = np(1 - p)$."],
    tags=["probabilités", "loi binomiale"],
    difficulte="moyen",
    apercu_premium=("Calcul de $P(X = k)$, espérance, au moins un succès",
                    "Trois exemples rédigés : $P(X = 2)$ pour $\\mathcal{B}(5 ; 0{,}2)$, espérance et écart-type, au moins un succès."),
    apercu_ultra=("Probabilité cumulée, démonstration",
                  "Le calcul de $P(X \\leqslant 1)$ pour un lot de pièces, et la démonstration de la formule de la loi binomiale."),
    questions_eclair=[("figure", "Combien de chemins comportent exactement $1$ succès sur la figure ?", "$3$."),
                      ("methode", "$X \\sim \\mathcal{B}(40 ; 0{,}25)$ : $E(X)$ ?", "$10$.")],
    demonstration=demonstration(
        "Formule de la loi binomiale",
        [("Chemin", "Un chemin à $k$ succès et $n - k$ échecs a pour probabilité $p^k (1 - p)^{n - k}$ (épreuves indépendantes)."),
         ("Même probabilité", "Tous les chemins à $k$ succès ont cette même probabilité, quel que soit l'ordre des succès."),
         ("Comptage", "Par définition, il y a $\\binom{n}{k}$ chemins à $k$ succès."),
         ("Conclusion", "$P(X = k)$ est la somme de leurs probabilités : $\\binom{n}{k} p^k (1 - p)^{n - k}$.")],
        "Dénombrer les chemins suffit : c'est le rôle du coefficient binomial.",
    ),
)

NOTION_3 = notion(
    id=ID3, title=N3,
    intro="Une fréquence observée sur un échantillon fluctue autour de la proportion théorique. La loi binomiale permet de déterminer un intervalle dans lequel la fréquence se trouve avec une probabilité d'au moins $95\\,\\%$ : c'est l'intervalle de fluctuation, qui sert à prendre une décision.",
    pourquoi="Un dé est-il truqué ? Une machine produit-elle trop de pièces défectueuses ? On compare une fréquence observée à l'intervalle de fluctuation pour accepter ou rejeter une hypothèse.",
    objectif="À la fin de ce cours, tu sauras déterminer l'intervalle de fluctuation à $95\\,\\%$ d'une fréquence à partir de la loi binomiale, et appliquer la règle de décision pour accepter ou rejeter une hypothèse sur une proportion.",
    definition="Soit $X \\sim \\mathcal{B}(n ; p)$, où $X$ compte les succès dans un échantillon aléatoire de taille $n$ et $p$ est la proportion supposée dans la population. L'intervalle de fluctuation à $95\\,\\%$ de la fréquence $\\dfrac{X}{n}$ est l'intervalle $\\left[\\dfrac{a}{n} ; \\dfrac{b}{n}\\right]$, où $a$ est le plus petit entier tel que $P(X \\leqslant a) > 0{,}025$ et $b$ le plus petit entier tel que $P(X \\leqslant b) \\geqslant 0{,}975$. Règle de décision : si la fréquence observée $f$ appartient à $\\left[\\dfrac{a}{n} ; \\dfrac{b}{n}\\right]$, on ne remet pas en question l'hypothèse « la proportion vaut $p$ » et on l'accepte ; sinon, on la rejette (avec un risque d'erreur d'environ $5\\,\\%$).",
    explication_simple="Pour $n = 50$ et $p = 0{,}3$, on trouve $a = 9$ et $b = 22$ : l'intervalle de fluctuation est $[0{,}18 ; 0{,}44]$. Une fréquence observée de $0{,}36$ est compatible avec $p = 0{,}3$ ; une fréquence de $0{,}5$ ne l'est pas.",
    intuition="On fixe à l'avance une « zone normale » pour la fréquence : en sortir est trop rare (moins de $5\\,\\%$ des cas) pour être attribué au hasard.",
    regles=[
        "$X \\sim \\mathcal{B}(n ; p)$ sous l'hypothèse « la proportion vaut $p$ ».",
        "$a$ : plus petit entier tel que $P(X \\leqslant a) > 0{,}025$.",
        "$b$ : plus petit entier tel que $P(X \\leqslant b) \\geqslant 0{,}975$.",
        "Intervalle de fluctuation à $95\\,\\%$ de la fréquence : $\\left[\\dfrac{a}{n} ; \\dfrac{b}{n}\\right]$.",
        "Règle : $f$ dans l'intervalle, on accepte l'hypothèse ; $f$ hors de l'intervalle, on la rejette.",
    ],
    formules=[
        formule("formule-intervalle-fluctuation", "Intervalle de fluctuation", "$\\left[\\dfrac{a}{n} ; \\dfrac{b}{n}\\right]$", "Pour une fréquence observée sur $n$ essais.", "Oublier de diviser par $n$.", "$a$ et $b$ sont des nombres de succès, l'intervalle porte sur la fréquence."),
        formule("formule-a-b", "Bornes", "$P(X \\leqslant a) > 0{,}025$ ; $P(X \\leqslant b) \\geqslant 0{,}975$", "Pour trouver $a$ et $b$ dans un tableau des probabilités cumulées.", "Prendre le dernier entier sous $0{,}025$.", "On cherche le PREMIER entier qui dépasse le seuil."),
    ],
    methode_titre="Méthode — Prendre une décision par l'intervalle de fluctuation",
    etapes=[
        step("search", "blue", "J'écris l'hypothèse : proportion $p$, échantillon de taille $n$, $X \\sim \\mathcal{B}(n ; p)$."),
        step("layers", "purple", "Avec les probabilités cumulées $P(X \\leqslant k)$, je trouve $a$ et $b$."),
        step("target", "orange", "Je calcule la fréquence observée $f$ et je la compare à $\\left[\\dfrac{a}{n} ; \\dfrac{b}{n}\\right]$."),
        step("check", "green", "Je conclus : accepter ou rejeter l'hypothèse, avec une phrase dans le contexte."),
    ],
    debutant=[
        step("search", "blue", "Je note $n$ et $p$."),
        step("layers", "purple", "Je cherche $a$ et $b$ dans le tableau."),
        step("target", "orange", "Je calcule la fréquence observée."),
        step("check", "green", "Dans l'intervalle : j'accepte ; dehors : je rejette."),
    ],
    rapide=[step("layers", "purple", "$a$, $b$, puis $\\left[\\dfrac{a}{n} ; \\dfrac{b}{n}\\right]$."), step("check", "green", "$f$ dedans : accepter.")],
    exemples=[
        ex("exemple-decision-accepter", "Exemple 1 — Accepter une hypothèse",
           "Sous l'hypothèse $p = 0{,}3$ et pour $n = 50$, l'intervalle de fluctuation à $95\\,\\%$ est $[0{,}18 ; 0{,}44]$. On observe $18$ succès sur $50$. Que décider ?",
           [calc("f = \\dfrac{18}{50} = 0{,}36"), calc("$0{,}36 \\in [0{,}18 ; 0{,}44]$.")],
           "On accepte l'hypothèse $p = 0{,}3$.", "facile", "free", conclusion="L'écart à $0{,}3$ peut s'expliquer par la fluctuation."),
        ex("exemple-decision-rejeter", "Exemple 2 — Rejeter une hypothèse",
           "Même situation, mais on observe $25$ succès sur $50$. Que décider ?",
           [calc("f = \\dfrac{25}{50} = 0{,}5"), calc("$0{,}5 \\notin [0{,}18 ; 0{,}44]$.")],
           "On rejette l'hypothèse $p = 0{,}3$.", "facile", "free", conclusion="Risque de se tromper : environ $5\\,\\%$."),
        ex("exemple-trouver-a-b", "Exemple 3 — Déterminer $a$ et $b$",
           "$X \\sim \\mathcal{B}(50 ; 0{,}3)$ : $P(X \\leqslant 8) \\approx 0{,}018$, $P(X \\leqslant 9) \\approx 0{,}040$, $P(X \\leqslant 21) \\approx 0{,}9749$, $P(X \\leqslant 22) \\approx 0{,}9877$. Déterminer l'intervalle de fluctuation à $95\\,\\%$.",
           [calc("$P(X \\leqslant 8) \\leqslant 0{,}025 < P(X \\leqslant 9)$ : $a = 9$."), calc("$P(X \\leqslant 21) < 0{,}975 \\leqslant P(X \\leqslant 22)$ : $b = 22$."),
            calc("\\left[\\dfrac{9}{50} ; \\dfrac{22}{50}\\right] = [0{,}18 ; 0{,}44]")],
           "$[0{,}18 ; 0{,}44]$.", "moyen", "premium", conclusion="C'est la figure du cours."),
        ex("exemple-de-truque", "Exemple 4 — Un dé est-il truqué ?",
           "On lance $40$ fois un dé et on compte les $6$. Sous l'hypothèse « dé équilibré », $X \\sim \\mathcal{B}\\left(40 ; \\dfrac{1}{6}\\right)$, et l'on obtient $a = 2$, $b = 12$. On observe $14$ fois le $6$. Que décider ?",
           [calc("Intervalle de fluctuation : $\\left[\\dfrac{2}{40} ; \\dfrac{12}{40}\\right] = [0{,}05 ; 0{,}3]$."), calc("f = \\dfrac{14}{40} = 0{,}35 \\notin [0{,}05 ; 0{,}3]")],
           "On rejette l'hypothèse : le dé semble truqué.", "moyen", "premium", conclusion="$E(X) = \\dfrac{40}{6} \\approx 6{,}67$ : $14$ est très au-dessus."),
        ex("exemple-controle-qualite", "Exemple 5 — Contrôle qualité",
           "Un fabricant annonce $5\\,\\%$ de pièces défectueuses. Pour $n = 100$, $X \\sim \\mathcal{B}(100 ; 0{,}05)$ et l'intervalle de fluctuation à $95\\,\\%$ est $[0{,}01 ; 0{,}10]$. Sur $100$ pièces, $9$ sont défectueuses. Que conclure ?",
           [calc("f = \\dfrac{9}{100} = 0{,}09 \\in [0{,}01 ; 0{,}10]")],
           "On accepte l'annonce du fabricant.", "moyen", "premium", conclusion="Une fréquence au-dessus de $5\\,\\%$ n'est pas forcément anormale."),
        ex("exemple-sens-du-95", "Exemple 6 — Que signifie « 95 % » ?",
           "Justifier que, si l'hypothèse est vraie, la probabilité que la fréquence observée soit dans $\\left[\\dfrac{a}{n} ; \\dfrac{b}{n}\\right]$ est au moins $0{,}95$.",
           [calc("$P(a \\leqslant X \\leqslant b) = P(X \\leqslant b) - P(X \\leqslant a - 1)$."),
            calc("$a$ est le plus petit entier tel que $P(X \\leqslant a) > 0{,}025$ : donc $P(X \\leqslant a - 1) \\leqslant 0{,}025$."),
            calc("P(a \\leqslant X \\leqslant b) \\geqslant 0{,}975 - 0{,}025 = 0{,}95")],
           "La fréquence est dans l'intervalle avec une probabilité d'au moins $95\\,\\%$.", "difficile", "ultra",
           conclusion="Rejeter à tort une hypothèse vraie n'arrive donc qu'avec une probabilité d'au plus $5\\,\\%$ environ."),
    ],
    erreurs=[
        ("Comparer le nombre de succès à l'intervalle de la fréquence.", "On oublie de diviser par $n$.", "Compares-tu des fréquences ?", "$f = \\dfrac{X}{n}$."),
        ("Prendre pour $a$ le dernier entier tel que $P(X \\leqslant a) \\leqslant 0{,}025$.", "Mauvaise lecture du tableau.", "Quel est le premier entier qui dépasse $0{,}025$ ?", "$a$ : premier entier tel que $P(X \\leqslant a) > 0{,}025$."),
        ("Conclure qu'une hypothèse acceptée est « prouvée ».", "Interprétation trop forte.", "Les observations démontrent-elles l'hypothèse ?", "On dit seulement qu'elle n'est pas remise en question."),
        ("Oublier les conditions de la loi binomiale.", "On applique l'outil sans justifier.", "L'échantillon est-il aléatoire, les tirages indépendants ?", "Justifie $X \\sim \\mathcal{B}(n ; p)$."),
    ],
    astuce="Dans un tableau de probabilités cumulées, cherche la première ligne qui dépasse $0{,}025$ (pour $a$), puis la première qui atteint $0{,}975$ (pour $b$).",
    a_retenir=["Échantillonnage et règle de décision : intervalle $\\left[\\dfrac{a}{n} ; \\dfrac{b}{n}\\right]$.",
               "$a$ : premier entier avec $P(X \\leqslant a) > 0{,}025$ ; $b$ : premier entier avec $P(X \\leqslant b) \\geqslant 0{,}975$.",
               "$f$ dans l'intervalle : on accepte ; sinon on rejette."],
    exemples_concrets=["Tester un dé.", "Contrôler un taux de pièces défectueuses.", "Vérifier une proportion annoncée."],
    figure=FIG3,
    quiz=(89301, 89302, 89303),
    prerequis=["Schéma de Bernoulli et loi binomiale", "Loi des grands nombres et simulation"],
    notions_liees=[ID2],
    objectifs=["Déterminer un intervalle de fluctuation à $95\\,\\%$.", "Appliquer la règle de décision.", "Interpréter le risque de $5\\,\\%$."],
    vocabulaire=["échantillon", "intervalle de fluctuation", "fréquence observée", "règle de décision", "hypothèse"],
    synonymes=["intervalle de fluctuation", "règle de décision", "échantillonnage", "dé truqué", "accepter ou rejeter une hypothèse"],
    proprietes=["Si l'hypothèse est vraie, $P\\left(\\dfrac{a}{n} \\leqslant \\dfrac{X}{n} \\leqslant \\dfrac{b}{n}\\right) \\geqslant 0{,}95$."],
    tags=["probabilités", "échantillonnage"],
    difficulte="moyen",
    apercu_premium=("Déterminer $a$ et $b$, dé truqué, contrôle qualité",
                    "Trois exemples rédigés : lecture d'un tableau de probabilités cumulées, test d'un dé, contrôle d'un taux de défauts."),
    apercu_ultra=("Le sens du « 95 % », démonstration",
                  "Pourquoi la fréquence est dans l'intervalle avec une probabilité d'au moins $0{,}95$."),
    questions_eclair=[("figure", "Quelles sont les bornes $a$ et $b$ sur la figure ?", "$9$ et $22$."),
                      ("methode", "$n = 50$, $a = 9$, $b = 22$ : $f = 0{,}46$ ?", "Hors de l'intervalle : on rejette.")],
    demonstration=demonstration(
        "La fréquence est dans l'intervalle de fluctuation avec une probabilité d'au moins $95\\,\\%$",
        [("Événement", "$\\dfrac{a}{n} \\leqslant \\dfrac{X}{n} \\leqslant \\dfrac{b}{n} \\iff a \\leqslant X \\leqslant b$."),
         ("Découpage", "$P(a \\leqslant X \\leqslant b) = P(X \\leqslant b) - P(X \\leqslant a - 1)$."),
         ("Bornes", "$P(X \\leqslant b) \\geqslant 0{,}975$ et, $a$ étant le plus petit entier tel que $P(X \\leqslant a) > 0{,}025$, $P(X \\leqslant a - 1) \\leqslant 0{,}025$."),
         ("Conclusion", "$P(a \\leqslant X \\leqslant b) \\geqslant 0{,}975 - 0{,}025 = 0{,}95$.")],
        "C'est ce qui justifie le seuil de décision : une fréquence hors de l'intervalle est rare si l'hypothèse est vraie.",
    ),
)

CHAPTER = chapter(9, "Loi de Bernoulli et loi binomiale", "layers", [NOTION_1, NOTION_2, NOTION_3])
