"""Calibrage pédagogique des exercices GÉNÉRÉS (chantier 2, 2026-11-01).

Défaut corrigé : les moteurs de webapp/exercise_generator*/ fixaient la
difficulté servie à partir d'un score de complexité de l'EXPRESSION
(`real_difficulty_score` : nombre d'opérations, racines, puissances…). Ce
score mesure la longueur du calcul, pas le raisonnement : la dérivée de
$-4x^2 - 2x - 4$ sortait au niveau 3, celle de $e^{-2x-6}$ au niveau 5,
tandis que « démontrer qu'une suite est arithmétique » retombait au niveau 2
ou 3 selon les coefficients tirés.

Règle appliquée : la difficulté servie est le niveau PÉDAGOGIQUE de la famille
(`declared_level`, fixé à la conception d'après la compétence visée),
indépendant des nombres tirés, sauf pour les familles dont ce niveau déclaré
a été jugé faux à la relecture (tables ci-dessous). Chaque correction a été
décidée en lisant des énoncés réels de la famille, d'après les connaissances
mobilisées, le nombre et la nature des étapes et l'autonomie demandée — pas
d'après une heuristique automatique.

Aucun énoncé, aucune réponse ni aucun identifiant n'est modifié : seuls
`difficulty`, `difficulty_label` et `difficulty_emoji` le sont. Le
`complexity_score` est conservé (information, plus utilisé pour le niveau).

Utilisé par les scripts tools/generate_*_exercises.py (avant écriture) et par
tools/recalibrer_banques_generees.py (banques déjà servies).
"""

LIBELLES = {
    1: ("🟢", "Niveau 1 — Fondamental"),
    2: ("🟡", "Niveau 2 — Intermédiaire"),
    3: ("🟠", "Niveau 3 — Avancé"),
    4: ("🔴", "Niveau 4 — Difficile"),
    5: ("🟣", "Niveau 5 — Défi"),
}

# Familles communes aux moteurs de Première (spécialité et spécifique, mêmes
# modules d'origine) dont le niveau déclaré est corrigé.
_PREMIERE_COMMUNES = {
    # Déclarées 5 : applications ou démonstrations directes.
    "arith_demonstration": 2,          # montrer que u_n = an + b est arithmétique
    "geo_demonstration": 3,            # calculer u_{n+1}/u_n pour une forme explicite
    "variance_comparaison": 4,
    "combinee": 4,
    "simplification_prealable": 4,
    "compo_synthese": 3,
    "defi_tangente_parallele": 4,
    "bayes_trois_branches": 4,
    "parametre": 3,                    # Δ > 0 pour x² - 5x + m
    # Déclarées 4 : méthode unique appliquée directement.
    "variation_parametre": 2,          # u_n = an + 2 croissante ⇔ a > 0
    "limite_geometrique": 3,
    "variance": 3,
    "jeu_trois_issues": 3,
    "jeu_equite": 3,
    "corriger_erreur": 3,
    "resolution_irrationnelle": 3,
    "verifier_resolution_irrationnelle": 3,
    "quotient_complexe": 3,
    "compo_erreur": 3,
    "parametre_retrouver": 3,
    "erreur_calcul": 3,
    "extremum_inverse": 3,             # f'(x0) = 0 donne p directement
    "fn_derivee_polynome_expo": 3,
    "fn_derivee_composee": 2,          # dérivée de e^{ax+b} : application directe
    "courbe_tangente": 2,              # tangente à exp en un point donné
    "suite_contexte_population": 3,
    "suite_contexte_radioactif": 3,
    "suite_contexte_capitalisation": 3,
    "equation_sin": 2,                 # sin x = 1/2 sur ]-π ; π]
    "formule_duplication": 2,
    "trouver_coordonnee_orthogonale": 2,  # u·v = 0 : équation du premier degré
    "angle_inverse": 3,
    "centre_rayon_developpee": 3,
    "droite_parallele_par_point": 2,
    "bayes_simple": 3,
    "probabilites_totales_trois_branches": 3,
    # Déclarées 3 : valeurs ou propriétés à appliquer directement.
    "alg_valeur_connue": 2,
    "ana_limite_composee": 2,
    "combinaison_lineaire": 2,         # valeurs remarquables de cos et sin
    "combinaison_deux_angles": 2,
    "expression_carre": 2,
    "equation_cos": 2,
    "centre_rayon_irrationnel": 2,
    "ensemble_points_distance": 2,     # AM = r : cercle de centre A
    "equation_depuis_normal": 2,
    "not_equation_double": 2,
    "ana_inequation": 2,
    "suite_sens_variation": 2,
    "test_independance": 2,
    "probabilites_totales": 2,
    "alignement_points": 2,
    "compo_domaine": 1,                # domaine de 1/(ax + b)
    # Déclarées 1 : méthode à plusieurs étapes.
    "tangente": 2,
    "resolution": 2,                   # résolution par le discriminant
    "taux_variation": 2,
}

_PREMIERE_SPECIFIQUE_SEULE = {
    "comparer_images": 3,
    "indice_evolutions": 2,
    "racine_et_cube": 3,
    "resume_serie": 3,
    "tableau_reunion": 2,
    "cumul": 3,
    "taux_reciproque": 2,
    "lecture_variations": 2,
    "inequation_cube": 2,
    "comparer_dispersion": 2,
    "au_moins_un": 2,
    # Optimisation guidée (fonction fournie : boîte V(x), coût ax + b/x) : niveau
    # Difficile ; l'échelle de Première spécifique va de 1 à 4.
    "optimisation": 4,
    "optimisation_quotient": 4,
}

_TROISIEME = {
    "retrouver_taux": 2,               # 100 € → 90 € : taux d'évolution
    "moyenne_ponderee": 2,
    "arbre_deux_epreuves": 3,
    "reciproque": 3,
    "effet_volume": 2,
    "ecriture_scientifique_produit": 2,
    "comparer_taux": 3,
    "cylindre_retrouver_rayon": 3,
    "moyenne_ponderee_inverse": 3,
    "puissance": 1,                    # (-3)^3
    "ecriture_scientifique": 1,        # écriture décimale de 4,4 × 10^-1
    "antecedent": 2,
    "carre_existence": 2,
    "avec_terme_supplementaire": 2,
    "trois_fractions": 2,
    "volume_cylindre": 2,
    "effet_aire": 2,
    "puissance_produit": 2,
    "calcul_direct_fractionnaire": 2,
    "comparaison": 2,
    "mult_div": 1,                     # 4 × 10
    "calcul_direct": 2,                # fonction affine passant par deux points
}

_SECONDE = {
    "eq_cart_choix_methode": 3,
    "signe_tableau": 3,                # tableau de signes d'un produit de deux facteurs affines
    "vecteur_erreur_normal": 3,
    "eq_reduite_erreur": 3,
    "eq_reduite_inverse": 3,
    "positions_erreur": 3,
    "eq_cart_erreur": 3,
    "eq_cart_inverse": 3,
    "ineq_erreur": 2,
    "ineq_inverse": 3,
    "signe_erreur": 2,
}

CORRECTIONS = {
    "premiere": dict(_PREMIERE_COMMUNES),
    "premiere_specifique": {**_PREMIERE_COMMUNES, **_PREMIERE_SPECIFIQUE_SEULE},
    "troisieme": _TROISIEME,
    "seconde": _SECONDE,
    # Quatrième : la difficulté servie est déjà le niveau déclaré (échelle 1-4).
    "quatrieme": {},
}


def niveau(class_level: str, exercice: dict) -> int:
    """Niveau pédagogique d'un exercice généré."""
    corrige = CORRECTIONS.get(class_level, {}).get(exercice.get("family"))
    if corrige is not None:
        return corrige
    declare = exercice.get("declared_level")
    return declare if declare in LIBELLES else exercice["difficulty"]


def calibrer(pool: list, class_level: str) -> int:
    """Fixe difficulty/difficulty_label/difficulty_emoji de chaque exercice
    (en place) ; renvoie le nombre d'exercices dont le niveau a changé."""
    changes = 0
    for ex in pool:
        lvl = niveau(class_level, ex)
        if lvl != ex.get("difficulty"):
            changes += 1
        ex["difficulty"] = lvl
        if "difficulty_label" in ex or "difficulty_emoji" in ex:
            ex["difficulty_emoji"], ex["difficulty_label"] = LIBELLES[lvl]
    return changes
