"""
Moteur de décision automatique de figures pédagogiques : à partir de la
catégorie d'une notion (voir `pedagogy_templates.detect_category`), décide
s'il faut une illustration, quel type produire, et avec quelles valeurs.

Les figures utilisent toujours des valeurs pédagogiques canoniques (petits
nombres simples, choisis pour la clarté), jamais les valeurs d'un exercice
précis de la banque — ce qui rend le moteur totalement indépendant du
contenu de la banque d'exercices et reproductible à l'identique pour
n'importe quelle notion de la même catégorie.

Le schéma de sortie (`spec`) est consommé par `static/js/geomSvg.js`
(`renderFigure`). Voir ce fichier pour le détail des types de figures
(`kind`) disponibles.

Retourne `None` quand aucune représentation visuelle fiable n'existe encore
pour la catégorie (mieux vaut aucune figure qu'une figure trompeuse ou sans
valeur pédagogique réelle — ex. calcul littéral abstrait sans modèle d'aire).
"""
import re


def _racines(notion_id, notion_label):
    return {
        "kind": "geom",
        "viewBox": [-1, -1, 6, 6],
        "grid": False,
        "axes": False,
        "polygons": [{"points": ["A", "B", "C", "D"]}],
        "points": [
            {"x": 0, "y": 0, "label": "A"},
            {"x": 3, "y": 0, "label": "B"},
            {"x": 3, "y": 3, "label": "C"},
            {"x": 0, "y": 3, "label": "D"},
        ],
        "texts": [{"x": 1.5, "y": 1.5, "label": "Aire = 9"}],
        "segments": [{"from": "A", "to": "B"}],
        "alt": "Un carré d'aire 9 a un côté de longueur √9 = 3.",
    }


def _arithmetique(notion_id, notion_label):
    marks = [{"value": v, "label": str(v), "filled": v % 3 == 0} for v in range(0, 13)]
    return {
        "kind": "numberline",
        "min": 0, "max": 12,
        "marks": marks,
        "alt": "Les points pleins marquent les multiples de 3 entre 0 et 12.",
    }


def _ensembles_nombres(notion_id, notion_label):
    return {
        "kind": "nested-sets",
        "labels": ["N", "Z", "D", "Q", "R"],
        "alt": "Les ensembles de nombres sont emboîtés : N ⊂ Z ⊂ D ⊂ Q ⊂ R.",
    }


def _intervalles(notion_id, notion_label):
    if "valeur-absolue" in notion_id:
        return {
            "kind": "numberline",
            "min": -5, "max": 5,
            "marks": [{"value": -3, "label": "-3"}, {"value": 0, "label": "0"}, {"value": 3, "label": "3"}],
            "highlight": {"from": -3, "to": 3},
            "alt": "|−3| et |3| représentent la même distance à 0.",
        }
    return {
        "kind": "numberline",
        "min": -5, "max": 5,
        "marks": [
            {"value": -2, "label": "-2", "filled": False},
            {"value": 4, "label": "4"},
        ],
        "highlight": {"from": -2, "to": 4},
        "alt": "L'intervalle ]−2 ; 4] : borne de gauche exclue, borne de droite incluse.",
    }


def _calcul_litteral(notion_id, notion_label):
    if "distributivite" not in notion_id:
        return None
    # Modèle d'aire : a(b + c) = ab + ac, deux rectangles accolés.
    return {
        "kind": "geom",
        "viewBox": [-0.5, -0.5, 8, 4],
        "polygons": [
            {"points": [{"x": 0, "y": 0}, {"x": 3, "y": 0}, {"x": 3, "y": 2}, {"x": 0, "y": 2}]},
            {"points": [{"x": 3, "y": 0}, {"x": 6, "y": 0}, {"x": 6, "y": 2}, {"x": 3, "y": 2}]},
        ],
        "segments": [{"from": {"x": 3, "y": 0}, "to": {"x": 3, "y": 2}, "dashed": True}],
        "texts": [
            {"x": 1.5, "y": 1, "label": "a × b"},
            {"x": 4.5, "y": 1, "label": "a × c"},
            {"x": 0, "y": -0.3, "label": "b"},
            {"x": 3, "y": -0.3, "label": "c"},
            {"x": -0.4, "y": 1, "label": "a"},
        ],
        "alt": "Le rectangle de largeur (b + c) se découpe en deux rectangles d'aires a×b et a×c.",
    }


def _vecteurs(notion_id, notion_label):
    return {
        "kind": "geom",
        "viewBox": [-1, -1, 7, 6],
        "grid": True, "axes": True,
        "points": [{"x": 1, "y": 1, "label": "A"}, {"x": 4, "y": 3, "label": "B"}],
        "vectors": [{"from": "A", "to": "B", "label": "u"}],
        "alt": "Le vecteur u va du point A au point B.",
    }


def _repere(notion_id, notion_label):
    if "milieu" in notion_id or "norme" in notion_id:
        return {
            "kind": "geom",
            "viewBox": [-1, -1, 7, 6],
            "grid": True, "axes": True,
            "points": [{"x": 0, "y": 1, "label": "A"}, {"x": 4, "y": 3, "label": "B"}, {"x": 2, "y": 2, "label": "I"}],
            "segments": [{"from": "A", "to": "B"}],
            "alt": "I est le milieu du segment [AB].",
        }
    return {
        "kind": "geom",
        "viewBox": [-1, -1, 7, 6],
        "grid": True, "axes": True,
        "points": [{"x": 3, "y": 2, "label": "M(3 ; 2)"}],
        "alt": "Le point M a pour coordonnées (3 ; 2) dans le repère.",
    }


def _droites(notion_id, notion_label):
    return {
        "kind": "geom",
        "viewBox": [-1, -2, 7, 7],
        "grid": True, "axes": True,
        "points": [{"x": 0, "y": 1, "label": "A"}, {"x": 4, "y": 3, "label": "B"}],
        "segments": [{"from": {"x": -1, "y": 0.5}, "to": {"x": 5, "y": 3.5}}],
        "alt": "La droite (AB) passe par les points A et B.",
    }


def _fonctions_generalites(notion_id, notion_label):
    pts = [[x / 2, -0.3 * (x / 2 - 2) ** 2 + 3] for x in range(0, 13)]
    return {
        "kind": "geom",
        "viewBox": [-1, -1, 8, 6],
        "grid": True, "axes": True,
        "curves": [{"points": pts}],
        "points": [{"x": 2, "y": 3, "label": "M"}],
        "segments": [
            {"from": {"x": 2, "y": 0}, "to": {"x": 2, "y": 3}, "dashed": True},
            {"from": {"x": 0, "y": 3}, "to": {"x": 2, "y": 3}, "dashed": True},
        ],
        "alt": "Le point M(2 ; 3) de la courbe : 3 est l'image de 2, 2 est un antécédent de 3.",
    }


def _variations(notion_id, notion_label):
    pts = [[x / 2, -0.3 * (x / 2 - 3) ** 2 + 4] for x in range(0, 13)]
    return {
        "kind": "geom",
        "viewBox": [-1, -1, 8, 6],
        "grid": True, "axes": True,
        "curves": [{"points": pts}],
        "points": [{"x": 3, "y": 4, "label": "maximum"}],
        "alt": "La fonction croît puis décroît : elle atteint un maximum au sommet de la courbe.",
    }


def _signe(notion_id, notion_label):
    return {
        "kind": "numberline",
        "min": -4, "max": 4,
        "marks": [{"value": -2, "label": "-2"}, {"value": 1, "label": "1"}],
        "highlight": {"from": -2, "to": 1},
        "alt": "Le signe change en chaque valeur qui annule l'expression.",
    }


def _statistiques(notion_id, notion_label):
    return {
        "kind": "boxplot",
        "min": 2, "q1": 8, "median": 12, "q3": 16, "max": 20,
        "alt": "Boîte à moustaches résumant une série de notes (minimum, quartiles, médiane, maximum).",
    }


def _pourcentages(notion_id, notion_label):
    return {
        "kind": "pie",
        "slices": [{"label": "Avant (100 %)", "value": 100}, {"label": "Évolution (+20 %)", "value": 20}],
        "alt": "Une évolution de +20 % ajoutée à une valeur de départ.",
    }


def _suites(notion_id, notion_label):
    return {
        "kind": "geom",
        "viewBox": [-1, -1, 7, 6],
        "grid": True, "axes": True,
        "points": [{"x": n, "y": 1 + 0.6 * n, "label": f"u{n}"} for n in range(0, 6)],
        "alt": "Les termes d'une suite, placés les uns après les autres selon leur rang.",
    }


def _second_degre(notion_id, notion_label):
    pts = [[x / 2, 0.4 * (x / 2 - 2.5) ** 2 - 1.5] for x in range(0, 13)]
    return {
        "kind": "geom",
        "viewBox": [-1, -2, 8, 7],
        "grid": True, "axes": True,
        "curves": [{"points": pts}],
        "points": [{"x": 1.5, "y": 0, "label": "racine"}, {"x": 3.5, "y": 0, "label": "racine"}, {"x": 2.5, "y": -1.5, "label": "sommet"}],
        "alt": "Une parabole coupe l'axe des abscisses en ses racines ; son sommet est son minimum.",
    }


def _derivation(notion_id, notion_label):
    pts = [[x / 2, -0.25 * (x / 2 - 2) ** 2 + 3] for x in range(0, 13)]
    return {
        "kind": "geom",
        "viewBox": [-1, -1, 8, 6],
        "grid": True, "axes": True,
        "curves": [{"points": pts}],
        "points": [{"x": 3, "y": 2.75, "label": "point de contact"}],
        "segments": [{"from": {"x": 1.2, "y": 4.05}, "to": {"x": 4.8, "y": 1.45}}],
        "alt": "La tangente à la courbe au point de contact a pour pente le nombre dérivé en ce point.",
    }


def _exponentielle(notion_id, notion_label):
    pts = [[x / 3, min(0.3 * (1.8 ** (x / 3)), 6)] for x in range(0, 13)]
    return {
        "kind": "geom",
        "viewBox": [-1, -1, 6, 7],
        "grid": True, "axes": True,
        "curves": [{"points": pts}],
        "alt": "La fonction exponentielle croît de plus en plus vite.",
    }


def _trigonometrie(notion_id, notion_label):
    import math
    deg = 40
    rad = math.radians(deg)
    x, y = round(math.cos(rad), 2), round(math.sin(rad), 2)
    return {
        "kind": "geom",
        "viewBox": [-1.3, -1.3, 2.6, 2.6],
        "grid": False, "axes": True,
        "circles": [{"center": {"x": 0, "y": 0}, "radius": 1}],
        "points": [{"x": x, "y": y, "label": "M"}],
        "segments": [
            {"from": {"x": 0, "y": 0}, "to": {"x": x, "y": y}},
            {"from": {"x": x, "y": y}, "to": {"x": x, "y": 0}, "dashed": True},
            {"from": {"x": x, "y": y}, "to": {"x": 0, "y": y}, "dashed": True},
        ],
        "arcs": [{"center": {"x": 0, "y": 0}, "radius": 0.35, "startDeg": 0, "endDeg": deg, "label": "angle"}],
        "alt": "Sur le cercle trigonométrique, l'abscisse de M est cos(angle), son ordonnée est sin(angle).",
    }


def _produit_scalaire(notion_id, notion_label):
    if "cercle" in notion_id:
        return {
            "kind": "geom",
            "viewBox": [-3.5, -3.5, 8, 8],
            "grid": True, "axes": True,
            "points": [{"x": 1, "y": 1, "label": "Ω"}],
            "circles": [{"center": {"x": 1, "y": 1}, "radius": 2.5}],
            "segments": [{"from": {"x": 1, "y": 1}, "to": {"x": 3.5, "y": 1}}],
            "texts": [{"x": 2.25, "y": 0.6, "label": "r"}],
            "alt": "Un cercle est défini par son centre Ω et son rayon r.",
        }
    return {
        "kind": "geom",
        "viewBox": [-1, -1, 7, 6],
        "grid": True, "axes": True,
        "points": [{"x": 0, "y": 0, "label": "O"}, {"x": 4, "y": 1, "label": "A"}, {"x": 2, "y": 3, "label": "B"}],
        "vectors": [{"from": "O", "to": "A", "label": "u"}, {"from": "O", "to": "B", "label": "v"}],
        "arcs": [{"center": "O", "radius": 0.8, "startDeg": 14, "endDeg": 56, "label": "angle"}],
        "alt": "L'angle entre les vecteurs u et v détermine le signe du produit scalaire.",
    }


def _probabilites(notion_id, notion_label):
    return {
        "kind": "tree",
        "branches": [
            {"label": "Boule rouge", "proba": "0,4", "branches": [
                {"label": "Rouge", "proba": "0,4"}, {"label": "Bleue", "proba": "0,6"},
            ]},
            {"label": "Boule bleue", "proba": "0,6", "branches": [
                {"label": "Rouge", "proba": "0,4"}, {"label": "Bleue", "proba": "0,6"},
            ]},
        ],
        "alt": "Arbre pondéré à deux tirages successifs.",
    }


def _variables_aleatoires(notion_id, notion_label):
    return {
        "kind": "bars",
        "bars": [{"label": "-1", "value": 0.3}, {"label": "0", "value": 0.2}, {"label": "2", "value": 0.5}],
        "maxValue": 0.6,
        "alt": "Loi de probabilité d'une variable aléatoire X : chaque valeur possible a sa probabilité.",
    }


_SOLID_KEYWORDS = (
    ("cube", r"\bcube\b"),
    ("pave", r"pave"),
    ("cylindre", r"cylindre"),
    ("cone", r"c[oô]ne"),
    ("sphere", r"sphere"),
    ("pyramide", r"pyramide"),
    ("prisme", r"prisme"),
)


def _solides(notion_id, notion_label):
    haystack = f"{notion_id} {notion_label}".lower()
    shape = "cube"
    for key, pattern in _SOLID_KEYWORDS:
        if re.search(pattern, haystack):
            shape = key
            break
    return {"kind": "solid", "shape": shape}


_BUILDERS = {
    "racines": _racines,
    "arithmetique": _arithmetique,
    "ensembles_nombres": _ensembles_nombres,
    "intervalles": _intervalles,
    "calcul_litteral": _calcul_litteral,
    "vecteurs": _vecteurs,
    "repere": _repere,
    "droites": _droites,
    "fonctions_generalites": _fonctions_generalites,
    "variations": _variations,
    "signe": _signe,
    "statistiques": _statistiques,
    "pourcentages": _pourcentages,
    "suites": _suites,
    "second_degre": _second_degre,
    "derivation": _derivation,
    "exponentielle": _exponentielle,
    "trigonometrie": _trigonometrie,
    "produit_scalaire": _produit_scalaire,
    "probabilites": _probabilites,
    "variables_aleatoires": _variables_aleatoires,
    "solides": _solides,
}


def build_figure(category, notion_id, notion_label):
    builder = _BUILDERS.get(category)
    if builder is None:
        return None
    return builder(notion_id, notion_label)
