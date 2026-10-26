"""Chapitre 4 — Statistiques (Première spécifique, manuel « Première ES/L », Ch. 4 :
notation Σ ; mode, moyenne, médiane ; quartiles et diagramme en boîte ;
variance, écart-type, écart interquartile, étendue ; résumer une série).

Créé lors de l'adaptation du 2026-10-26 (voir PREMIERE_SPECIFIQUE_SUIVI.md) :
reprend les exemples de moyenne et de médiane de l'ancienne notion
« Statistiques et probabilités » (chapitre « Automatismes ») ; tout le reste
est créé. Série d'exemple : 20 notes (valeurs et effectifs ci-dessous), dont
les indicateurs ont été recalculés en fractions exactes.
"""
from premiere_specifique.cours_commun import calc, chapter, demonstration, ex, explication, figure_geom, formule, notion, pt, step, text

N1, N2, N3 = "Notation Σ et indicateurs de tendance centrale", "Quartiles et diagramme en boîte", "Variance, écart-type et dispersion"
ID1, ID2, ID3 = "notation-sigma-et-tendance-centrale", "quartiles-et-diagramme-en-boite", "indicateurs-de-dispersion"

# Série d'exemple : notes de 20 élèves.
_VALEURS = (6, 8, 9, 10, 11, 12, 14, 15, 17)
_EFFECTIFS = (1, 2, 3, 4, 3, 2, 2, 2, 1)
_N = sum(_EFFECTIFS)
_MOY = sum(v * n for v, n in zip(_VALEURS, _EFFECTIFS)) / _N          # 11,05
assert _N == 20 and abs(_MOY - 11.05) < 1e-9


def _s(a, b, **kw):
    s = {"from": {"x": a[0], "y": a[1]}, "to": {"x": b[0], "y": b[1]}}
    s.update({k: v for k, v in kw.items() if v is not None})
    return s


# Figure 1 : diagramme en bâtons, mode, moyenne et médiane (abscisse : note − 5).
FIG1 = figure_geom(
    view=[-0.8, -1.4, 14.4, 7.0], axes=False,
    points=[pt(v - 5, n, "") for v, n in zip(_VALEURS, _EFFECTIFS)],
    segments=[_s((0, 0), (13, 0))] + [_s((v - 5, 0), (v - 5, n), tooltip=f"note {v} : effectif {n}") for v, n in zip(_VALEURS, _EFFECTIFS)]
             + [_s((_MOY - 5, 0), (_MOY - 5, 5.2), dashed=True, reveal=2, tooltip="moyenne 11,05"),
                _s((5.5, 0), (5.5, 4.6), reveal=3, tooltip="médiane 10,5")],
    texts=[text((v - 5, -0.6), str(v)) for v in _VALEURS]
          + [text((5.0, 4.6), "mode 10", reveal=1), text((7.4, 5.6), "moyenne 11,05", reveal=2), text((3.6, 5.2), "médiane 10,5", reveal=3)],
    steps=["La série : 20 notes et leurs effectifs (le mode est 10)", "La moyenne 11,05", "La médiane 10,5 partage la série en deux moitiés"],
    relation="$\\overline{x} = \\dfrac{\\sum n_i x_i}{N} = \\dfrac{221}{20} = 11{,}05$",
    alt="Diagramme en bâtons des notes de 20 élèves : 6 (1), 8 (2), 9 (3), 10 (4), 11 (3), 12 (2), 14 (2), 15 (2), 17 (1). Mode 10, moyenne 11,05, médiane 10,5.",
    explication=explication(
        resume="Le mode, la moyenne et la médiane résument la position d'une série. Avec des effectifs, la moyenne se calcule en pondérant chaque valeur par son effectif.",
        lecture=["Chaque bâton : une note, sa hauteur est l'effectif.", "Effectif total : $N = 20$."],
        observations=["$\\sum n_i x_i = 6 + 16 + 27 + 40 + 33 + 24 + 28 + 30 + 17 = 221$.", "Médiane : moyenne des $10^{e}$ et $11^{e}$ valeurs, $\\dfrac{10 + 11}{2} = 10{,}5$.",
                      "Le mode $10$ est la valeur de plus grand effectif."],
        pieges=["Faire la moyenne des valeurs sans tenir compte des effectifs."],
        a_retenir=["Moyenne : $\\dfrac{\\sum n_i x_i}{N}$ ; médiane : valeur centrale de la série rangée."],
    ),
)

# Figure 2 : diagramme en boîte de la même série.
_MIN, _Q1, _ME, _Q3, _MAX = 6, 9, 10.5, 12, 17
FIG2 = figure_geom(
    view=[3.6, -1.6, 15.2, 5.6], axes=False, points=[],
    segments=[_s((5, 0), (18, 0))] + [_s((x, -0.15), (x, 0.15)) for x in range(5, 19)]
             + [_s((_Q1, 1), (_Q3, 1), reveal=2), _s((_Q3, 1), (_Q3, 3), reveal=2), _s((_Q3, 3), (_Q1, 3), reveal=2), _s((_Q1, 3), (_Q1, 1), reveal=2),
                _s((_ME, 1), (_ME, 3), reveal=2, tooltip="médiane 10,5"),
                _s((_MIN, 2), (_Q1, 2), reveal=3), _s((_Q3, 2), (_MAX, 2), reveal=3), _s((_MIN, 1.5), (_MIN, 2.5), reveal=3), _s((_MAX, 1.5), (_MAX, 2.5), reveal=3)],
    texts=[text((x, -0.6), str(x)) for x in (6, 9, 12, 17)] + [text((_ME, 3.5), "Me", reveal=2), text((_Q1, 3.5), "Q₁", reveal=2), text((_Q3, 3.5), "Q₃", reveal=2),
                                                                text((_MIN, 3.0), "min", reveal=3), text((_MAX, 3.0), "max", reveal=3)],
    steps=["Un axe gradué", "La boîte : de Q₁ à Q₃, coupée par la médiane", "Les moustaches vont jusqu'aux valeurs extrêmes"],
    relation="Min $6$ ; $Q_1 = 9$ ; $Me = 10{,}5$ ; $Q_3 = 12$ ; max $17$",
    alt="Diagramme en boîte des notes : moustache de 6 à 9, boîte de Q1 = 9 à Q3 = 12 coupée par la médiane 10,5, moustache de 12 à 17.",
    explication=explication(
        resume="Le diagramme en boîte résume une série par cinq nombres : minimum, premier quartile, médiane, troisième quartile, maximum. La longueur de la boîte est l'écart interquartile.",
        lecture=["La boîte contient environ la moitié centrale des valeurs.", "Chaque moustache contient environ un quart des valeurs."],
        observations=["$\\dfrac{N}{4} = 5$ : $Q_1$ est la $5^{e}$ valeur, $9$.", "$\\dfrac{3N}{4} = 15$ : $Q_3$ est la $15^{e}$ valeur, $12$.", "Écart interquartile : $12 - 9 = 3$."],
        pieges=["Croire que la médiane est toujours au milieu de la boîte."],
        a_retenir=["Boîte : de $Q_1$ à $Q_3$ ; moustaches : jusqu'au minimum et au maximum."],
    ),
)

# Figure 3 : dispersion autour de la moyenne (même série).
FIG3 = figure_geom(
    view=[-0.8, -1.4, 14.4, 7.0], axes=False,
    points=[pt(v - 5, n, "") for v, n in zip(_VALEURS, _EFFECTIFS)],
    segments=[_s((0, 0), (13, 0))] + [_s((v - 5, 0), (v - 5, n)) for v, n in zip(_VALEURS, _EFFECTIFS)]
             + [_s((_MOY - 5, 0), (_MOY - 5, 5.2), dashed=True, reveal=1),
                _s((_MOY - 5 - 2.71, 5.0), (_MOY - 5 + 2.71, 5.0), reveal=2, tooltip="de x̄ − σ à x̄ + σ"),
                _s((1, 6.0), (12, 6.0), reveal=3, tooltip="étendue 11")],
    texts=[text((v - 5, -0.6), str(v)) for v in _VALEURS] + [text((6.05, 4.4), "σ ≈ 2,71", reveal=2), text((6.5, 6.5), "étendue = 17 − 6 = 11", reveal=3)],
    steps=["La série et sa moyenne 11,05", "L'écart-type σ ≈ 2,71 mesure l'écart moyen à la moyenne", "L'étendue mesure l'écart entre les valeurs extrêmes"],
    relation="$V = \\dfrac{\\sum n_i x_i^2}{N} - \\overline{x}^2 = 129{,}45 - 122{,}1025 = 7{,}3475$ ; $\\sigma = \\sqrt{V} \\approx 2{,}71$",
    alt="Diagramme en bâtons des notes avec la moyenne 11,05, un segment allant de x̄ − σ à x̄ + σ (σ ≈ 2,71) et l'étendue 11 de 6 à 17.",
    explication=explication(
        resume="La variance est la moyenne des carrés des écarts à la moyenne ; l'écart-type, sa racine carrée, s'exprime dans l'unité de la série. L'étendue et l'écart interquartile sont d'autres mesures de dispersion.",
        lecture=["Le segment horizontal va de $\\overline{x} - \\sigma$ à $\\overline{x} + \\sigma$.", "Beaucoup de valeurs sont dans cet intervalle."],
        observations=["$\\sum n_i x_i^2 = 2\\,589$, donc $\\dfrac{2\\,589}{20} = 129{,}45$.", "$V = 129{,}45 - 11{,}05^2 = 7{,}3475$.", "$\\sigma = \\sqrt{7{,}3475} \\approx 2{,}71$ points."],
        pieges=["Oublier de soustraire $\\overline{x}^2$ dans la seconde formule."],
        a_retenir=["$\\sigma = \\sqrt{V}$, dans l'unité de la série."],
    ),
)


NOTION_1 = notion(
    id=ID1, title=N1,
    intro="Une série statistique se résume d'abord par sa position : autour de quelle valeur se situent les données ? Le mode, la moyenne et la médiane répondent à cette question. La notation $\\Sigma$ permet d'écrire les sommes sans pointillés.",
    pourquoi="Comparer des résultats, des salaires, des temps : on a besoin d'un nombre qui résume une série. Selon les données, la moyenne ou la médiane est la plus pertinente.",
    objectif="À la fin de ce cours, tu sauras lire et écrire une somme avec $\\Sigma$, calculer effectif total et fréquences, et déterminer le mode, la moyenne (avec effectifs ou fréquences) et la médiane d'une série.",
    definition="La somme $a_1 + a_2 + \\dots + a_n$ se note $\\sum_{i=1}^{n} a_i$ (« somme pour $i$ allant de $1$ à $n$ des $a_i$ »). Une série prend les valeurs $x_1, \\dots, x_p$ avec les effectifs $n_1, \\dots, n_p$ ; l'effectif total est $N = \\sum_{i=1}^{p} n_i$ et la fréquence de $x_i$ est $f_i = \\dfrac{n_i}{N}$. Le mode est la valeur de plus grand effectif. La moyenne est $\\overline{x} = \\dfrac{\\sum_{i=1}^{p} n_i x_i}{N} = \\sum_{i=1}^{p} f_i x_i$. Les $N$ valeurs étant rangées dans l'ordre croissant (chacune répétée selon son effectif), la médiane $Me$ est la valeur centrale si $N$ est impair (rang $\\dfrac{N + 1}{2}$), la moyenne des valeurs de rangs $\\dfrac{N}{2}$ et $\\dfrac{N}{2} + 1$ si $N$ est pair.",
    explication_simple="Série $4$ ; $7$ ; $7$ ; $9$ ; $13$ : mode $7$, moyenne $\\dfrac{40}{5} = 8$, médiane $7$ (la $3^{e}$ valeur sur $5$).",
    intuition="La moyenne est le « partage équitable » ; la médiane coupe la série en deux moitiés ; le mode est la valeur « la plus à la mode ».",
    regles=[
        "Notation $\\Sigma$ : $\\sum_{i=1}^{n} a_i = a_1 + a_2 + \\dots + a_n$.",
        "Effectif total $N = \\sum n_i$ ; fréquence $f_i = \\dfrac{n_i}{N}$ (les fréquences ont pour somme $1$).",
        "Moyenne : $\\overline{x} = \\dfrac{\\sum n_i x_i}{N} = \\sum f_i x_i$.",
        "Médiane : ranger les valeurs ; $N$ impair : valeur de rang $\\dfrac{N + 1}{2}$ ; $N$ pair : moyenne des valeurs de rangs $\\dfrac{N}{2}$ et $\\dfrac{N}{2} + 1$.",
        "Les effectifs cumulés croissants permettent de trouver la valeur d'un rang donné.",
    ],
    formules=[
        formule("formule-moyenne-ponderee", "Moyenne", "$\\overline{x} = \\dfrac{\\sum n_i x_i}{N}$", "Pour une série avec effectifs.", "Diviser par le nombre de valeurs distinctes.", "On divise par l'effectif total $N$."),
        formule("formule-mediane", "Médiane", "rang $\\dfrac{N + 1}{2}$ ($N$ impair)", "Pour une valeur centrale.", "Oublier de ranger la série.", "Utilise les effectifs cumulés."),
    ],
    methode_titre="Méthode — Calculer moyenne et médiane d'une série avec effectifs",
    etapes=[
        step("search", "blue", "Je calcule l'effectif total $N$ et les effectifs cumulés croissants."),
        step("layers", "purple", "Moyenne : je calcule $\\sum n_i x_i$ puis je divise par $N$."),
        step("target", "orange", "Médiane : je repère le ou les rangs centraux dans les effectifs cumulés."),
        step("check", "green", "Je contrôle que moyenne et médiane sont entre la plus petite et la plus grande valeur."),
    ],
    debutant=[
        step("search", "blue", "J'additionne les effectifs : c'est $N$."),
        step("layers", "purple", "Je multiplie chaque valeur par son effectif, j'additionne, je divise par $N$."),
        step("target", "orange", "Pour la médiane, je cherche la valeur du milieu."),
        step("check", "green", "Le résultat est entre le minimum et le maximum."),
    ],
    rapide=[step("layers", "purple", "$\\overline{x} = \\dfrac{\\sum n_i x_i}{N}$."), step("check", "green", "Médiane par les effectifs cumulés.")],
    exemples=[
        ex("exemple-sigma", "Exemple 1 — La notation $\\Sigma$",
           "Écrire $1 + 2 + \\dots + 20$ avec le symbole $\\Sigma$, puis calculer $\\sum_{i=1}^{4} i^2$.",
           [calc("1 + 2 + \\dots + 20 = \\sum_{i=1}^{20} i"), calc("\\sum_{i=1}^{4} i^2 = 1 + 4 + 9 + 16 = 30")],
           "$\\sum_{i=1}^{20} i$ ; $\\sum_{i=1}^{4} i^2 = 30$.", "facile", "free", conclusion="On remplace $i$ par chaque entier de $1$ à $4$, puis on additionne."),
        ex("exemple-auto-stats", "Exemple 2 — Mode, moyenne, médiane",
           "Série $4$ ; $7$ ; $7$ ; $9$ ; $13$ : déterminer le mode, la moyenne et la médiane.",
           [calc("Mode : $7$ (deux fois)."), calc("\\overline{x} = \\dfrac{4 + 7 + 7 + 9 + 13}{5} = \\dfrac{40}{5} = 8"), calc("Médiane : $3^{e}$ valeur sur $5$, soit $7$.")],
           "Mode $7$, moyenne $8$, médiane $7$.", "facile", "free", conclusion="La série est déjà rangée."),
        ex("exemple-moyenne-effectifs", "Exemple 3 — Moyenne avec effectifs",
           "Notes de $20$ élèves : $6$ (1), $8$ (2), $9$ (3), $10$ (4), $11$ (3), $12$ (2), $14$ (2), $15$ (2), $17$ (1). Calculer la moyenne.",
           [calc("\\sum n_i x_i = 6 + 16 + 27 + 40 + 33 + 24 + 28 + 30 + 17 = 221"), calc("\\overline{x} = \\dfrac{221}{20} = 11{,}05")],
           "$\\overline{x} = 11{,}05$.", "moyen", "premium", conclusion="C'est la figure du cours."),
        ex("exemple-mediane-cumules", "Exemple 4 — Médiane par les effectifs cumulés",
           "Avec la même série ($N = 20$), déterminer la médiane.",
           [calc("Effectifs cumulés : $1$ ; $3$ ; $6$ ; $10$ ; $13$ ; …"), calc("$10^{e}$ valeur : $10$ ; $11^{e}$ valeur : $11$."), calc("Me = \\dfrac{10 + 11}{2} = 10{,}5")],
           "$Me = 10{,}5$.", "moyen", "premium", conclusion="$N$ pair : moyenne des deux valeurs centrales."),
        ex("exemple-moyenne-frequences", "Exemple 5 — Moyenne avec les fréquences",
           "Une série prend les valeurs $1$, $2$, $3$ avec les fréquences $0{,}2$, $0{,}5$, $0{,}3$. Calculer sa moyenne.",
           [calc("\\overline{x} = 0{,}2 \\times 1 + 0{,}5 \\times 2 + 0{,}3 \\times 3 = 0{,}2 + 1 + 0{,}9")],
           "$\\overline{x} = 2{,}1$.", "moyen", "premium", conclusion="Avec les fréquences, on ne divise plus par $N$."),
        ex("exemple-valeur-extreme", "Exemple 6 — Sensibilité aux valeurs extrêmes",
           "Dans la série $4$ ; $7$ ; $7$ ; $9$ ; $13$, on remplace $13$ par $63$. Comment évoluent la moyenne et la médiane ?",
           [calc("Nouvelle moyenne : $\\dfrac{90}{5} = 18$ (au lieu de $8$)."), calc("Médiane : toujours la $3^{e}$ valeur, $7$.")],
           "La moyenne passe de $8$ à $18$ ; la médiane reste $7$.", "difficile", "ultra",
           conclusion="La médiane est peu sensible aux valeurs extrêmes, la moyenne l'est beaucoup."),
    ],
    erreurs=[
        ("Calculer la médiane sans ranger la série.", "Valeur centrale fausse.", "La série est-elle rangée ?", "Range d'abord, ou utilise les effectifs cumulés."),
        ("Diviser par le nombre de valeurs distinctes.", "On oublie les effectifs.", "Combien d'individus en tout ?", "On divise par $N = \\sum n_i$."),
        ("Prendre le rang $\\dfrac{N}{2}$ seul quand $N$ est pair.", "Règle incomplète.", "$N$ est-il pair ou impair ?", "$N$ pair : moyenne des rangs $\\dfrac{N}{2}$ et $\\dfrac{N}{2} + 1$."),
        ("Confondre $\\sum_{i=1}^{4} i^2$ et $\\left(\\sum_{i=1}^{4} i\\right)^2$.", "On élève la somme au carré.", "Le carré porte-t-il sur chaque terme ?", "$30$ et non $100$."),
    ],
    astuce="Avant de calculer, écris la ligne des effectifs cumulés croissants : elle donne $N$ (dernier nombre) et permet de trouver immédiatement la médiane.",
    a_retenir=["Notation Σ et indicateurs de tendance centrale : mode, moyenne, médiane.", "$\\overline{x} = \\dfrac{\\sum n_i x_i}{N} = \\sum f_i x_i$.", "Médiane : valeur centrale de la série rangée."],
    exemples_concrets=["Moyenne d'une classe.", "Salaire médian.", "Pointure la plus vendue (mode)."],
    figure=FIG1,
    quiz=(84101, 84102, 73401),
    prerequis=["Statistiques (Seconde)"],
    notions_liees=[ID2, ID3],
    objectifs=["Utiliser la notation $\\Sigma$.", "Calculer moyenne et médiane d'une série avec effectifs.", "Choisir l'indicateur adapté."],
    vocabulaire=["somme Σ", "effectif", "fréquence", "mode", "moyenne", "médiane", "effectifs cumulés"],
    synonymes=["notation sigma", "moyenne pondérée", "médiane", "mode d'une série", "effectifs cumulés croissants", "moyenne avec fréquences"],
    proprietes=["$\\overline{x} = \\sum f_i x_i$."],
    tags=["statistiques"],
    difficulte="facile",
    apercu_premium=("Moyenne avec effectifs, médiane, fréquences",
                    "Trois exemples rédigés : moyenne d'une série avec effectifs, médiane par les effectifs cumulés, moyenne avec les fréquences."),
    apercu_ultra=("Valeurs extrêmes, démonstration",
                  "La sensibilité de la moyenne aux valeurs extrêmes, et la démonstration de la formule de la moyenne avec les fréquences."),
    questions_eclair=[("figure", "Quel est le mode de la série de la figure ?", "$10$."),
                      ("methode", "$\\sum_{i=1}^{3} 2i$ ?", "$2 + 4 + 6 = 12$.")],
    demonstration=demonstration(
        "La moyenne s'écrit avec les fréquences : $\\overline{x} = \\sum f_i x_i$",
        [("Définition", "$\\overline{x} = \\dfrac{\\sum_{i=1}^{p} n_i x_i}{N}$."),
         ("Distribution", "Diviser la somme par $N$, c'est diviser chaque terme : $\\overline{x} = \\sum_{i=1}^{p} \\dfrac{n_i}{N} x_i$."),
         ("Fréquences", "Par définition, $f_i = \\dfrac{n_i}{N}$."),
         ("Conclusion", "$\\overline{x} = \\sum_{i=1}^{p} f_i x_i$.")],
        "C'est cette écriture qui relie la moyenne d'une série à l'espérance d'une variable aléatoire (chapitre 8).",
    ),
)

NOTION_2 = notion(
    id=ID2, title=N2,
    intro="La médiane coupe une série en deux moitiés ; les quartiles la coupent en quatre parts. Avec le minimum et le maximum, ils permettent de dessiner un diagramme en boîte, résumé visuel très utilisé pour comparer des séries.",
    pourquoi="Les quartiles décrivent la répartition des données sans être perturbés par quelques valeurs extrêmes : on les utilise pour les salaires, les temps de trajet, les résultats d'examen.",
    objectif="À la fin de ce cours, tu sauras déterminer le premier et le troisième quartile d'une série (avec ou sans effectifs), construire et lire un diagramme en boîte, et comparer deux séries grâce à leurs boîtes.",
    definition="Les $N$ valeurs de la série étant rangées dans l'ordre croissant, $x_1 \\leqslant x_2 \\leqslant \\dots \\leqslant x_N$ (chacune répétée selon son effectif) : le premier quartile $Q_1$ est la valeur $x_i$ dont l'indice $i$ est le plus petit entier supérieur ou égal à $\\dfrac{N}{4}$ ; le troisième quartile $Q_3$ est la valeur $x_i$ dont l'indice $i$ est le plus petit entier supérieur ou égal à $\\dfrac{3N}{4}$. On prend souvent la médiane comme deuxième quartile. Le diagramme en boîte (ou boîte à moustaches) représente, le long d'un axe, une boîte allant de $Q_1$ à $Q_3$, coupée par un trait à la médiane, et deux moustaches allant jusqu'aux valeurs extrêmes.",
    explication_simple="Série de $8$ valeurs $3$ ; $5$ ; $5$ ; $8$ ; $9$ ; $11$ ; $12$ ; $15$ : $\\dfrac{8}{4} = 2$, donc $Q_1 = x_2 = 5$ ; $\\dfrac{3 \\times 8}{4} = 6$, donc $Q_3 = x_6 = 11$.",
    intuition="Au moins un quart des valeurs sont inférieures ou égales à $Q_1$, au moins les trois quarts sont inférieures ou égales à $Q_3$.",
    regles=[
        "$Q_1$ : valeur de rang égal au plus petit entier $\\geqslant \\dfrac{N}{4}$.",
        "$Q_3$ : valeur de rang égal au plus petit entier $\\geqslant \\dfrac{3N}{4}$.",
        "Au moins $25\\,\\%$ des valeurs sont $\\leqslant Q_1$ ; au moins $75\\,\\%$ sont $\\leqslant Q_3$.",
        "Diagramme en boîte : boîte de $Q_1$ à $Q_3$, trait à la médiane, moustaches jusqu'au minimum et au maximum.",
        "Les quartiles sont toujours des valeurs de la série.",
    ],
    formules=[
        formule("formule-q1", "Premier quartile", "rang $\\lceil \\dfrac{N}{4} \\rceil$", "Pour $Q_1$.", "Prendre la moyenne de deux valeurs comme pour la médiane.", "Si $\\dfrac{N}{4}$ n'est pas entier, on prend l'entier juste au-dessus."),
        formule("formule-q3", "Troisième quartile", "rang $\\lceil \\dfrac{3N}{4} \\rceil$", "Pour $Q_3$.", "Arrondir à l'entier inférieur.", "Toujours l'entier supérieur ou égal."),
    ],
    methode_titre="Méthode — Déterminer les quartiles et tracer la boîte",
    etapes=[
        step("search", "blue", "Je range la série (ou j'utilise les effectifs cumulés) et je calcule $N$."),
        step("layers", "purple", "Je calcule $\\dfrac{N}{4}$ et $\\dfrac{3N}{4}$, puis les rangs (entiers supérieurs ou égaux)."),
        step("target", "orange", "Je lis $Q_1$ et $Q_3$, ainsi que la médiane, le minimum et le maximum."),
        step("check", "green", "Je trace la boîte sur un axe gradué et je vérifie $\\min \\leqslant Q_1 \\leqslant Me \\leqslant Q_3 \\leqslant \\max$."),
    ],
    debutant=[
        step("search", "blue", "Je range les valeurs de la plus petite à la plus grande."),
        step("layers", "purple", "Je divise $N$ par $4$ pour trouver le rang de $Q_1$."),
        step("target", "orange", "Je multiplie par $3$ pour le rang de $Q_3$."),
        step("check", "green", "Je dessine la boîte et les moustaches."),
    ],
    rapide=[step("layers", "purple", "Rangs $\\lceil N/4 \\rceil$ et $\\lceil 3N/4 \\rceil$."), step("check", "green", "Boîte de $Q_1$ à $Q_3$.")],
    exemples=[
        ex("exemple-quartiles-simples", "Exemple 1 — Quartiles d'une petite série",
           "Déterminer $Q_1$, la médiane et $Q_3$ de la série $3$ ; $5$ ; $5$ ; $8$ ; $9$ ; $11$ ; $12$ ; $15$.",
           [calc("$N = 8$ ; $\\dfrac{N}{4} = 2$ : $Q_1 = x_2 = 5$."), calc("$\\dfrac{3N}{4} = 6$ : $Q_3 = x_6 = 11$."), calc("Me = \\dfrac{x_4 + x_5}{2} = \\dfrac{8 + 9}{2} = 8{,}5")],
           "$Q_1 = 5$, $Me = 8{,}5$, $Q_3 = 11$.", "facile", "free", conclusion="$Q_1$ et $Q_3$ sont des valeurs de la série."),
        ex("exemple-lire-boite", "Exemple 2 — Lire un diagramme en boîte",
           "Une boîte va de $9$ à $12$, la médiane est $10{,}5$, les moustaches vont de $6$ à $17$. Interpréter.",
           [calc("Au moins un quart des valeurs sont inférieures ou égales à $9$, au moins les trois quarts inférieures ou égales à $12$."),
            calc("Écart interquartile : $12 - 9 = 3$ ; étendue : $17 - 6 = 11$.")],
           "La moitié centrale des valeurs se situe environ entre $9$ et $12$.", "facile", "free", conclusion="C'est la figure du cours."),
        ex("exemple-quartiles-effectifs", "Exemple 3 — Quartiles avec effectifs",
           "Notes de $20$ élèves : $6$ (1), $8$ (2), $9$ (3), $10$ (4), $11$ (3), $12$ (2), $14$ (2), $15$ (2), $17$ (1). Déterminer $Q_1$ et $Q_3$.",
           [calc("Effectifs cumulés : $1$ ; $3$ ; $6$ ; $10$ ; $13$ ; $15$ ; $17$ ; $19$ ; $20$."),
            calc("$\\dfrac{20}{4} = 5$ : la $5^{e}$ valeur est $9$, donc $Q_1 = 9$."), calc("$\\dfrac{3 \\times 20}{4} = 15$ : la $15^{e}$ valeur est $12$, donc $Q_3 = 12$.")],
           "$Q_1 = 9$ et $Q_3 = 12$.", "moyen", "premium", conclusion="Les effectifs cumulés évitent d'écrire les $20$ valeurs."),
        ex("exemple-rang-non-entier", "Exemple 4 — Un rang non entier",
           "Une série rangée compte $N = 30$ valeurs. Quels rangs donnent $Q_1$ et $Q_3$ ?",
           [calc("$\\dfrac{30}{4} = 7{,}5$ : le plus petit entier supérieur ou égal est $8$."), calc("$\\dfrac{3 \\times 30}{4} = 22{,}5$ : on prend le rang $23$.")],
           "$Q_1 = x_8$ et $Q_3 = x_{23}$.", "moyen", "premium", conclusion="Toujours l'entier supérieur ou égal."),
        ex("exemple-comparer-boites", "Exemple 5 — Comparer deux séries",
           "Classe A : min $4$, $Q_1 = 8$, $Me = 11$, $Q_3 = 13$, max $18$. Classe B : min $7$, $Q_1 = 10$, $Me = 11$, $Q_3 = 12$, max $15$. Comparer.",
           [calc("Mêmes médianes : $11$."), calc("Écarts interquartiles : $5$ pour A, $2$ pour B ; étendues : $14$ et $8$.")],
           "Même niveau médian, mais les notes de A sont beaucoup plus dispersées.", "moyen", "premium", conclusion="Deux boîtes côte à côte comparent position et dispersion."),
        ex("exemple-quart-des-valeurs", "Exemple 6 — Que garantit $Q_1$ ?",
           "Dans une série de $N = 22$ valeurs, $Q_1 = 12$. Combien de valeurs, au minimum, sont inférieures ou égales à $12$ ?",
           [calc("$\\dfrac{22}{4} = 5{,}5$ : $Q_1$ est la $6^{e}$ valeur."), calc("Les $6$ premières valeurs sont inférieures ou égales à $12$.")],
           "Au moins $6$ valeurs, soit au moins $\\dfrac{6}{22} \\approx 27\\,\\%$ (plus du quart).", "difficile", "ultra",
           conclusion="La définition garantit qu'au moins un quart des valeurs sont inférieures ou égales à $Q_1$."),
    ],
    erreurs=[
        ("Prendre la moyenne de deux valeurs pour un quartile.", "Confusion avec la médiane.", "La définition des quartiles fait-elle une moyenne ?", "$Q_1$ et $Q_3$ sont des valeurs de la série."),
        ("Arrondir $\\dfrac{N}{4}$ à l'entier inférieur.", "Arrondi habituel.", "Le rang doit-il être supérieur ou égal ?", "On prend l'entier supérieur ou égal."),
        ("Oublier de ranger la série.", "Valeurs dans l'ordre de l'énoncé.", "La série est-elle rangée ?", "Range d'abord."),
        ("Croire que la boîte contient exactement la moitié des valeurs.", "Interprétation trop précise.", "Y a-t-il des valeurs égales aux quartiles ?", "« Environ » la moitié des valeurs."),
    ],
    astuce="Pour une série avec effectifs, calcule les rangs $\\lceil N/4 \\rceil$ et $\\lceil 3N/4 \\rceil$, puis cherche dans les effectifs cumulés le premier qui les atteint.",
    a_retenir=["Quartiles et diagramme en boîte : $Q_1$ et $Q_3$ par les rangs $\\lceil N/4 \\rceil$ et $\\lceil 3N/4 \\rceil$.",
               "Boîte de $Q_1$ à $Q_3$, médiane, moustaches jusqu'aux extrêmes.", "Au moins $25\\,\\%$ des valeurs $\\leqslant Q_1$."],
    exemples_concrets=["Comparer les temps de trajet de deux lignes de bus.", "Salaires d'une entreprise.", "Résultats de deux classes."],
    figure=FIG2,
    quiz=(84201, 84202, 84203),
    prerequis=["Notation Σ et indicateurs de tendance centrale"],
    notions_liees=[ID1, ID3],
    objectifs=["Déterminer $Q_1$ et $Q_3$.", "Construire et lire un diagramme en boîte.", "Comparer deux séries."],
    vocabulaire=["quartile", "premier quartile", "troisième quartile", "diagramme en boîte", "moustache"],
    synonymes=["quartiles", "boîte à moustaches", "diagramme en boîte", "premier quartile", "troisième quartile", "Q1 Q3"],
    proprietes=["Au moins $25\\,\\%$ des valeurs sont inférieures ou égales à $Q_1$."],
    tags=["statistiques", "quartiles"],
    difficulte="facile",
    apercu_premium=("Quartiles avec effectifs, rang non entier, comparaison de boîtes",
                    "Trois exemples rédigés : quartiles par les effectifs cumulés, rang non entier, comparaison de deux séries."),
    apercu_ultra=("Ce que garantit $Q_1$, démonstration",
                  "Le nombre minimal de valeurs inférieures au premier quartile, et sa démonstration."),
    questions_eclair=[("figure", "Que vaut l'écart interquartile sur la figure ?", "$12 - 9 = 3$."),
                      ("methode", "$N = 12$ : rang de $Q_3$ ?", "$9$.")],
    demonstration=demonstration(
        "Au moins un quart des valeurs sont inférieures ou égales à $Q_1$",
        [("Définition", "$Q_1 = x_k$ où $k$ est le plus petit entier tel que $k \\geqslant \\dfrac{N}{4}$."),
         ("Rangement", "La série est rangée : $x_1 \\leqslant x_2 \\leqslant \\dots \\leqslant x_k = Q_1$."),
         ("Comptage", "Les $k$ valeurs $x_1, \\dots, x_k$ sont donc inférieures ou égales à $Q_1$."),
         ("Conclusion", "Leur proportion est $\\dfrac{k}{N} \\geqslant \\dfrac{1}{4}$.")],
        "De même, au moins les trois quarts des valeurs sont inférieures ou égales à $Q_3$.",
    ),
)

NOTION_3 = notion(
    id=ID3, title=N3,
    intro="Deux séries peuvent avoir la même moyenne et être très différentes : l'une très regroupée, l'autre très étalée. Les indicateurs de dispersion — variance, écart-type, écart interquartile, étendue — mesurent cet étalement.",
    pourquoi="La dispersion mesure la régularité : régularité d'une production, homogénéité d'une classe, risque d'un placement. Résumer une série, c'est donner un indicateur de position ET un indicateur de dispersion.",
    objectif="À la fin de ce cours, tu sauras calculer la variance (par les deux formules), l'écart-type, l'écart interquartile et l'étendue, et choisir le couple d'indicateurs adapté pour résumer une série.",
    definition="La variance d'une série de moyenne $\\overline{x}$ est $V = \\dfrac{\\sum_{i=1}^{p} n_i (x_i - \\overline{x})^2}{N}$, la moyenne des carrés des écarts à la moyenne ; on a aussi $V = \\dfrac{\\sum_{i=1}^{p} n_i x_i^2}{N} - \\overline{x}^2$. L'écart-type est $\\sigma = \\sqrt{V}$ ; il s'exprime dans l'unité de la série. L'écart interquartile est $E_i = Q_3 - Q_1$ et l'étendue est la différence entre la plus grande et la plus petite valeur. Pour résumer une série, on associe la médiane à l'écart interquartile (peu sensibles aux valeurs extrêmes), ou la moyenne à l'écart-type (sensibles aux valeurs extrêmes).",
    explication_simple="Série $2$ ; $4$ ; $6$ : moyenne $4$, écarts $-2$ ; $0$ ; $2$, variance $\\dfrac{4 + 0 + 4}{3} = \\dfrac{8}{3}$, écart-type $\\sqrt{\\dfrac{8}{3}} \\approx 1{,}63$.",
    intuition="L'écart-type est une sorte d'« écart moyen » à la moyenne : petit si les valeurs sont regroupées, grand si elles sont étalées.",
    regles=[
        "Variance : $V = \\dfrac{\\sum n_i (x_i - \\overline{x})^2}{N}$, toujours positive ou nulle.",
        "Seconde formule : $V = \\dfrac{\\sum n_i x_i^2}{N} - \\overline{x}^2$.",
        "Écart-type : $\\sigma = \\sqrt{V}$, dans l'unité de la série.",
        "Écart interquartile $E_i = Q_3 - Q_1$ ; étendue $= \\max - \\min$.",
        "Résumer : (médiane, écart interquartile), peu sensibles aux valeurs extrêmes ; (moyenne, écart-type), sensibles aux valeurs extrêmes.",
    ],
    formules=[
        formule("formule-variance", "Variance", "$V = \\dfrac{\\sum n_i x_i^2}{N} - \\overline{x}^2$", "Pour calculer rapidement une variance.", "Oublier de soustraire $\\overline{x}^2$.", "Une variance négative signale une erreur."),
        formule("formule-ecart-type", "Écart-type", "$\\sigma = \\sqrt{V}$", "Pour mesurer la dispersion dans l'unité de la série.", "Confondre $V$ et $\\sigma$.", "$\\sigma$ a la même unité que les valeurs."),
    ],
    methode_titre="Méthode — Calculer variance et écart-type",
    etapes=[
        step("search", "blue", "Je calcule la moyenne $\\overline{x}$."),
        step("layers", "purple", "Je calcule $\\sum n_i x_i^2$ (ou les carrés des écarts $(x_i - \\overline{x})^2$)."),
        step("target", "orange", "$V = \\dfrac{\\sum n_i x_i^2}{N} - \\overline{x}^2$ (ou la moyenne des carrés des écarts)."),
        step("check", "green", "Je vérifie $V \\geqslant 0$, puis $\\sigma = \\sqrt{V}$ avec l'unité."),
    ],
    debutant=[
        step("search", "blue", "Je calcule la moyenne."),
        step("layers", "purple", "J'élève chaque valeur au carré et je fais la moyenne de ces carrés."),
        step("target", "orange", "Je retire le carré de la moyenne : c'est la variance."),
        step("check", "green", "La racine carrée donne l'écart-type."),
    ],
    rapide=[step("layers", "purple", "$V = \\overline{x^2} - \\overline{x}^2$."), step("check", "green", "$\\sigma = \\sqrt{V}$.")],
    exemples=[
        ex("exemple-etendue-ei", "Exemple 1 — Étendue et écart interquartile",
           "Une série a pour minimum $6$, $Q_1 = 9$, $Q_3 = 12$ et pour maximum $17$. Calculer l'étendue et l'écart interquartile.",
           [calc("Étendue : $17 - 6 = 11$."), calc("E_i = Q_3 - Q_1 = 12 - 9 = 3")],
           "Étendue $11$ ; écart interquartile $3$.", "facile", "free", conclusion="Deux mesures simples de dispersion."),
        ex("exemple-variance-definition-serie", "Exemple 2 — Variance par la définition",
           "Calculer la variance et l'écart-type de la série $2$ ; $4$ ; $6$.",
           [calc("\\overline{x} = \\dfrac{2 + 4 + 6}{3} = 4"), calc("V = \\dfrac{(2 - 4)^2 + (4 - 4)^2 + (6 - 4)^2}{3} = \\dfrac{8}{3}")],
           "$V = \\dfrac{8}{3}$ et $\\sigma = \\sqrt{\\dfrac{8}{3}} \\approx 1{,}63$.", "facile", "free", conclusion="Moyenne des carrés des écarts."),
        ex("exemple-variance-effectifs", "Exemple 3 — Variance avec effectifs",
           "Pour les $20$ notes de la figure ($\\overline{x} = 11{,}05$), on a $\\sum n_i x_i^2 = 2\\,589$. Calculer la variance et l'écart-type.",
           [calc("\\dfrac{2\\,589}{20} = 129{,}45"), calc("V = 129{,}45 - 11{,}05^2 = 129{,}45 - 122{,}1025 = 7{,}3475"), calc("\\sigma = \\sqrt{7{,}3475} \\approx 2{,}71")],
           "$V = 7{,}3475$ et $\\sigma \\approx 2{,}71$ points.", "moyen", "premium", conclusion="C'est la figure du cours."),
        ex("exemple-meme-moyenne", "Exemple 4 — Même moyenne, dispersions différentes",
           "Série A : $9$ ; $10$ ; $11$. Série B : $0$ ; $10$ ; $20$. Comparer moyennes et écarts-types.",
           [calc("Moyennes : $10$ et $10$."), calc("A : $V = \\dfrac{1 + 0 + 1}{3} = \\dfrac{2}{3}$ ; B : $V = \\dfrac{100 + 0 + 100}{3} = \\dfrac{200}{3}$.")],
           "Même moyenne ; $\\sigma_A \\approx 0{,}82$ et $\\sigma_B \\approx 8{,}16$ : B est beaucoup plus dispersée.", "moyen", "premium",
           conclusion="La moyenne seule ne suffit pas à résumer une série."),
        ex("exemple-choisir-resume", "Exemple 5 — Choisir un résumé",
           "Les salaires d'une petite entreprise : $1\\,500$, $1\\,600$, $1\\,600$, $1\\,700$, $1\\,800$, $9\\,000$ euros. Quel couple d'indicateurs choisir pour résumer cette série ?",
           [calc("La valeur $9\\,000$ est extrême : elle tire fortement la moyenne ($\\approx 2\\,867$ €) vers le haut."),
            calc("La médiane ($1\\,650$ €) et l'écart interquartile n'en dépendent presque pas.")],
           "Le couple (médiane, écart interquartile).", "moyen", "premium", conclusion="Avec des valeurs extrêmes, on préfère les indicateurs robustes."),
        ex("exemple-preuve-variance", "Exemple 6 — Les deux formules de la variance",
           "Vérifier sur la série $2$ ; $4$ ; $6$ que les deux formules de la variance donnent le même résultat.",
           [calc("Définition : $V = \\dfrac{8}{3}$ (exemple 2)."), calc("Seconde formule : $\\dfrac{4 + 16 + 36}{3} - 4^2 = \\dfrac{56}{3} - 16 = \\dfrac{8}{3}$.")],
           "Les deux formules donnent $\\dfrac{8}{3}$.", "difficile", "ultra",
           conclusion="La démonstration générale développe $(x_i - \\overline{x})^2$."),
    ],
    erreurs=[
        ("Oublier de soustraire $\\overline{x}^2$.", "Formule incomplète.", "As-tu retiré le carré de la moyenne ?", "$V = \\dfrac{\\sum n_i x_i^2}{N} - \\overline{x}^2$."),
        ("Donner la variance à la place de l'écart-type.", "Confusion des deux indicateurs.", "L'unité est-elle celle de la série ?", "$\\sigma = \\sqrt{V}$."),
        ("Calculer $\\left(\\sum n_i x_i\\right)^2$ au lieu de $\\sum n_i x_i^2$.", "On élève la somme au carré.", "Le carré porte-t-il sur chaque valeur ?", "On élève chaque valeur au carré, puis on pondère."),
        ("Résumer par la moyenne une série avec une valeur extrême.", "On choisit l'indicateur par habitude.", "Une valeur est-elle très éloignée des autres ?", "Préfère médiane et écart interquartile."),
    ],
    astuce="Une variance négative signale toujours une erreur de calcul : contrôle-la avant de prendre la racine carrée.",
    a_retenir=["Variance, écart-type et dispersion : variance, écart-type $\\sigma = \\sqrt{V}$, écart interquartile, étendue.",
               "$V = \\dfrac{\\sum n_i x_i^2}{N} - \\overline{x}^2$.", "Résumer : (médiane, $E_i$) ou (moyenne, $\\sigma$)."],
    exemples_concrets=["Régularité d'une production.", "Homogénéité de deux classes.", "Risque de deux placements."],
    figure=FIG3,
    quiz=(84301, 84302, 84303),
    prerequis=["Notation Σ et indicateurs de tendance centrale", "Quartiles et diagramme en boîte"],
    notions_liees=[ID1, ID2],
    objectifs=["Calculer variance et écart-type.", "Calculer écart interquartile et étendue.", "Choisir un résumé adapté."],
    vocabulaire=["variance", "écart-type", "écart interquartile", "étendue", "dispersion"],
    synonymes=["variance d'une série", "écart-type", "écart interquartile", "étendue", "dispersion", "résumer une série statistique"],
    proprietes=["$V = \\dfrac{\\sum n_i x_i^2}{N} - \\overline{x}^2$."],
    tags=["statistiques", "dispersion"],
    difficulte="moyen",
    apercu_premium=("Variance avec effectifs, même moyenne, choix du résumé",
                    "Trois exemples rédigés : variance d'une série avec effectifs, deux séries de même moyenne, choix d'un résumé adapté."),
    apercu_ultra=("Les deux formules de la variance, démonstration",
                  "La vérification des deux formules sur un exemple et la démonstration générale de la seconde formule."),
    questions_eclair=[("figure", "Que vaut l'étendue de la série de la figure ?", "$11$."),
                      ("methode", "$V = 9$ : écart-type ?", "$3$.")],
    demonstration=demonstration(
        "Seconde formule de la variance : $V = \\dfrac{\\sum n_i x_i^2}{N} - \\overline{x}^2$",
        [("Développement", "$(x_i - \\overline{x})^2 = x_i^2 - 2\\overline{x} x_i + \\overline{x}^2$."),
         ("Somme", "$\\sum n_i (x_i - \\overline{x})^2 = \\sum n_i x_i^2 - 2\\overline{x} \\sum n_i x_i + \\overline{x}^2 \\sum n_i$."),
         ("Simplification", "$\\sum n_i x_i = N\\overline{x}$ et $\\sum n_i = N$ : la somme vaut $\\sum n_i x_i^2 - 2N\\overline{x}^2 + N\\overline{x}^2 = \\sum n_i x_i^2 - N\\overline{x}^2$."),
         ("Conclusion", "En divisant par $N$ : $V = \\dfrac{\\sum n_i x_i^2}{N} - \\overline{x}^2$.")],
        "C'est la même identité que la formule de König-Huygens pour une variable aléatoire (chapitre 8).",
    ),
)

CHAPTER = chapter(4, "Statistiques", "layers", [NOTION_1, NOTION_2, NOTION_3])
