"""Chapitre 1 — Pourcentages : banque curée (manuel « Première ES/L », Ch. 1).

Créée lors de l'adaptation du 2026-10-26 (voir PREMIERE_SPECIFIQUE_SUIVI.md).
« Évolutions et taux » : exercices 73101 à 73104 repris tels quels de
l'ancien chapitre « Automatismes » (identifiants conservés), complétés.
Nouveaux exercices : bloc 81 000 (banque_commun.ID_BASE), chaque valeur
recalculée en fractions exactes (`verify`).
"""
from fractions import Fraction as F

from premiere_specifique.banque_commun import E, S
from premiere_specifique.reserve.banque_ch13 import EXERCISES as _AUTOMATISMES

CHAPTER_NUMBER = 1
N1 = "Proportions et pourcentages"
N2 = "Évolutions et taux"
N3 = "Indices base 100"
NOTIONS = (N1, N2, N3)
NOTION_IDS = ("proportions-et-pourcentages", "evolutions-et-taux", "indices-base-100")


def _ok(cond):
    return lambda: None if cond else "valeur fausse"


EXERCISES = [e for e in _AUTOMATISMES if e.notion == N2] + [
    # Proportions et pourcentages.
    E(81101, N1, 1,
      "Un club compte $480$ adhérents, dont $216$ filles. Calculer la proportion de filles, puis celle de garçons, en pourcentage.",
      "$45\\,\\%$ de filles et $55\\,\\%$ de garçons.",
      "Divise l'effectif des filles par l'effectif total.",
      S("$p = \\dfrac{216}{480} = 0{,}45$, soit $45\\,\\%$.", "Garçons : $1 - 0{,}45 = 0{,}55$, soit $55\\,\\%$."),
      checks=("45\\,\\%", "55\\,\\%"), verify=_ok(F(216, 480) == F(45, 100))),
    E(81102, N1, 1,
      "Calculer $15\\,\\%$ de $340$ €.",
      "$51$ €.",
      "Multiplie par $\\dfrac{15}{100}$.",
      S("$340 \\times \\dfrac{15}{100} = 340 \\times 0{,}15$.", "$340 \\times 0{,}15 = 51$."),
      checks=("$51$",), verify=_ok(340 * F(15, 100) == 51)),
    E(81103, N1, 2,
      "Dans une classe, $18$ élèves représentent $40\\,\\%$ de l'effectif. Combien d'élèves compte la classe ?",
      "La classe compte $45$ élèves.",
      "L'effectif total multiplié par $0{,}4$ donne $18$.",
      S("$n \\times 0{,}4 = 18$.", "$n = \\dfrac{18}{0{,}4} = 45$."),
      checks=("$45$",), verify=_ok(F(18) / F(2, 5) == 45)),
    E(81104, N1, 2,
      "Dans une entreprise, $60\\,\\%$ des salariés sont des femmes et $25\\,\\%$ d'entre elles sont cadres. Quelle proportion des salariés sont des femmes cadres ?",
      "$15\\,\\%$ des salariés.",
      "« $25\\,\\%$ d'entre elles » : une proportion dans la proportion.",
      S("On multiplie les proportions : $0{,}6 \\times 0{,}25$.", "$0{,}6 \\times 0{,}25 = 0{,}15$, soit $15\\,\\%$."),
      checks=("15\\,\\%",), verify=_ok(F(3, 5) * F(1, 4) == F(15, 100))),
    E(81105, N1, 3,
      "Un groupe de $200$ personnes compte $30\\,\\%$ de fumeurs ; un autre groupe de $300$ personnes en compte $50\\,\\%$. Quelle est la proportion de fumeurs dans les deux groupes réunis ?",
      "$42\\,\\%$.",
      "Reviens aux effectifs de fumeurs dans chaque groupe.",
      S("Fumeurs : $200 \\times 0{,}3 + 300 \\times 0{,}5 = 60 + 150 = 210$.", "Proportion : $\\dfrac{210}{500} = 0{,}42$, soit $42\\,\\%$.",
        "Ce n'est pas la moyenne $40\\,\\%$ des deux pourcentages : les groupes n'ont pas le même effectif."),
      checks=("42\\,\\%",), verify=_ok(F(200 * 30 + 300 * 50, 100 * 500) == F(42, 100))),
    E(81106, N1, 3,
      "Classe A : $12$ élèves sur $25$ pratiquent un sport en club. Classe B : $14$ élèves sur $30$. Quelle classe a la plus grande proportion de sportifs ?",
      "La classe A : $48\\,\\%$ contre environ $46{,}7\\,\\%$.",
      "Compare des proportions, pas des effectifs.",
      S("A : $\\dfrac{12}{25} = 0{,}48$.", "B : $\\dfrac{14}{30} \\approx 0{,}467$.", "$0{,}48 > 0{,}467$ : la classe A."),
      checks=("48\\,\\%",), verify=_ok(F(12, 25) > F(14, 30))),
    # Évolutions et taux (compléments).
    E(81201, N2, 2,
      "Le nombre d'abonnés d'une chaîne passe de $40\\,000$ à $98\\,000$. Calculer le taux d'évolution.",
      "Le taux d'évolution est $+145\\,\\%$.",
      "Un taux d'évolution peut dépasser $100\\,\\%$.",
      S("$t = \\dfrac{98\\,000 - 40\\,000}{40\\,000} = \\dfrac{58\\,000}{40\\,000} = 1{,}45$.", "Le nombre d'abonnés a augmenté de $145\\,\\%$."),
      checks=("145\\,\\%",), verify=_ok(F(98000 - 40000, 40000) == F(145, 100))),
    E(81202, N2, 3,
      "Un prix augmente de $5\\,\\%$, puis de nouveau de $5\\,\\%$, puis baisse de $10\\,\\%$. Quel est le taux d'évolution global ?",
      "Le taux global est $-0{,}775\\,\\%$ : le prix a légèrement baissé.",
      "Multiplie les coefficients multiplicateurs.",
      S("Coefficients : $1{,}05$, $1{,}05$ et $0{,}9$.", "$1{,}05 \\times 1{,}05 \\times 0{,}9 = 0{,}99225$.", "$T = 0{,}99225 - 1 = -0{,}00775$, soit $-0{,}775\\,\\%$."),
      checks=("-0{,}775\\,\\%",), verify=_ok(F(105, 100) ** 2 * F(9, 10) - 1 == F(-775, 100000))),
    E(81203, N2, 3,
      "Pendant les soldes, un prix baisse de $30\\,\\%$. Quelle évolution, arrondie à $0{,}01\\,\\%$ près, faut-il appliquer ensuite pour revenir au prix initial ?",
      "Une hausse d'environ $42{,}86\\,\\%$.",
      "Le coefficient réciproque de $0{,}7$ est $\\dfrac{1}{0{,}7}$.",
      S("Coefficient de la baisse : $0{,}7$.", "Coefficient réciproque : $\\dfrac{1}{0{,}7} = \\dfrac{10}{7} \\approx 1{,}4286$.",
        "$t' = \\dfrac{1}{0{,}7} - 1 \\approx 0{,}4286$, soit une hausse d'environ $42{,}86\\,\\%$."),
      checks=("42{,}86\\,\\%",), verify=_ok(abs(float(F(10, 7) - 1) - 0.4286) < 0.00005)),
    # Indices base 100.
    E(81301, N3, 1,
      "Un prix vaut $1{,}20$ € en 2015 et $1{,}38$ € en 2020. Calculer l'indice du prix en 2020, base $100$ en 2015, et interpréter.",
      "L'indice vaut $115$ : le prix a augmenté de $15\\,\\%$.",
      "$I = 100 \\times \\dfrac{\\text{nouvelle valeur}}{\\text{valeur de référence}}$.",
      S("$I = 100 \\times \\dfrac{1{,}38}{1{,}20} = 115$.", "$115 - 100 = 15$ : hausse de $15\\,\\%$ depuis 2015."),
      checks=("$115$",), verify=_ok(100 * F(138, 120) == 115)),
    E(81302, N3, 1,
      "L'indice d'une production vaut $87$ en 2023 (base $100$ en 2019). Interpréter cet indice.",
      "La production a baissé de $13\\,\\%$ entre 2019 et 2023.",
      "Compare l'indice à $100$.",
      S("$t = \\dfrac{87 - 100}{100} = -0{,}13$.", "Baisse de $13\\,\\%$ depuis 2019."),
      checks=("13\\,\\%",), verify=_ok(F(87 - 100, 100) == F(-13, 100))),
    E(81303, N3, 2,
      "Une ville comptait $2\\,400$ habitants en 2010 (indice $100$). En 2020, l'indice vaut $108{,}5$. Combien d'habitants compte-t-elle en 2020 ?",
      "La ville compte $2\\,604$ habitants.",
      "Valeur $= $ valeur de référence $\\times \\dfrac{I}{100}$.",
      S("$y = 2\\,400 \\times \\dfrac{108{,}5}{100}$.", "$y = 2\\,400 \\times 1{,}085 = 2\\,604$."),
      checks=("2\\,604",), verify=_ok(2400 * F(1085, 1000) == 2604)),
    E(81304, N3, 2,
      "Le loyer A passe de $500$ € à $620$ € ; le loyer B de $750$ € à $900$ €. Calculer les indices (base $100$ au départ) et comparer les évolutions.",
      "Indice $124$ pour A, $120$ pour B : le loyer A a davantage augmenté.",
      "Calcule un indice pour chaque loyer.",
      S("A : $100 \\times \\dfrac{620}{500} = 124$.", "B : $100 \\times \\dfrac{900}{750} = 120$.", "$+24\\,\\%$ contre $+20\\,\\%$ : le loyer A a le plus augmenté."),
      checks=("$124$", "$120$"), verify=_ok(100 * F(620, 500) == 124 and 100 * F(900, 750) == 120)),
    E(81305, N3, 3,
      "Base $100$ en 2018, un indice vaut $110$ en 2020 et $121$ en 2022. Calculer l'indice de 2022 en prenant 2020 comme référence, puis l'évolution entre 2020 et 2022.",
      "Indice $110$ : hausse de $10\\,\\%$ entre 2020 et 2022.",
      "Les indices sont proportionnels aux valeurs.",
      S("$I = 100 \\times \\dfrac{121}{110} = 110$.", "Entre 2020 et 2022, la grandeur a augmenté de $10\\,\\%$ (et non de $11\\,\\%$)."),
      checks=("$110$",), verify=_ok(100 * F(121, 110) == 110)),
    E(81306, N3, 3,
      "Base $100$ en 2020, une grandeur augmente de $20\\,\\%$ en 2021 puis baisse de $10\\,\\%$ en 2022. Calculer ses indices en 2021 et 2022 et l'évolution globale.",
      "Indices $120$ puis $108$ : hausse globale de $8\\,\\%$.",
      "Applique les coefficients multiplicateurs aux indices.",
      S("2021 : $100 \\times 1{,}2 = 120$.", "2022 : $120 \\times 0{,}9 = 108$.", "Indice $108$ : hausse de $8\\,\\%$ depuis 2020."),
      checks=("$108$",), verify=_ok(100 * F(6, 5) * F(9, 10) == 108)),
]

QUIZ = {
    "proportions-et-pourcentages": (81101, 81102, 81103),
    "evolutions-et-taux": (73101, 73102, 73103),
    "indices-base-100": (81301, 81302, 81303),
}
