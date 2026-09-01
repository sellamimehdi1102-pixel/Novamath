"""
Registre des générateurs symboliques réellement disponibles pour
POST /api/practice/generate (Chantier "Différenciateurs Premium/Ultra",
2026-08-27).

Cartographie EXACTE de ce qui existe — vérifiée en lisant chaque module
avant d'écrire ce fichier, jamais supposée. Trois packages, un par classe
(curriculum_registry.CURRICULUM_REGISTRY : "troisieme"/"seconde"/"premiere") :
    - exercise_generator_troisieme/ : 8 modules, un par notion
      (developper_distributivite, divisibilite, equation_premier_degre,
      factoriser_somme, fonction_affine_deux_points, fractions_addition,
      fractions_simplification, image_fonction) ;
    - exercise_generator_seconde/ : 2 modules (droites, signes) ;
    - exercise_generator/ (Première) : 6 modules (derivatives, exponentielle,
      second_degre, suites, tangente, variations).

Les 16 modules suivent tous le même contrat :
    - `FAMILIES` : liste de Family(id, level, label, ...) ;
    - `CHAPTER_ID` : chapitre couvert par le module ;
    - `generate_one(family_id, seed=None) -> dict` avec les clés enonce/
      answer/hint/solution_steps/chapter_id/notion/difficulty/
      difficulty_label/difficulty_emoji/family/family_label/declared_level/
      complexity_score/source — déjà compatibles avec le format attendu par
      server.py::public_exercise() (mêmes noms de champs).

Différence réelle entre modules (vérifiée avant écriture, pas supposée) :
la notion peut être portée soit par un champ `Family.notion` (une famille =
potentiellement plusieurs notions dans le même module, ex. derivatives.py),
soit par une constante `NOTION` au niveau du module (un module = une seule
notion, ex. divisibilite.py) — _notion_of() gère les deux cas.

IMPORTANT — collision d'identifiants de famille (découverte à l'audit,
vérifiée par script avant d'écrire ce fichier) : `family_id` n'est PAS
unique globalement, ni même au sein d'une seule classe (ex. "calcul_direct"
existe dans 3 modules différents de Troisième). Résoudre une génération à
partir du seul `family_id` serait donc silencieusement ambigu. `generate()`
exige donc TOUJOURS (class_level, chapter_id, notion, family_id) — exactement
le tuple déjà renvoyé par available_notions(), que le frontend doit
reproduire tel quel plutôt que d'envoyer family_id seul.
"""
from exercise_generator import (
    derivatives, exponentielle, geometrie_reperee, probabilites_conditionnelles,
    produit_scalaire, second_degre, suites, tangente, trigonometrie, variables_aleatoires,
    variations,
)
from exercise_generator_seconde import droites, signes
from exercise_generator_troisieme import (
    developper_distributivite, divisibilite, equation_premier_degre, factoriser_somme,
    fonction_affine_deux_points, fractions_addition, fractions_simplification, image_fonction,
)

_MODULES_BY_CLASS_LEVEL = {
    "troisieme": (
        developper_distributivite, divisibilite, equation_premier_degre, factoriser_somme,
        fonction_affine_deux_points, fractions_addition, fractions_simplification, image_fonction,
    ),
    "seconde": (droites, signes),
    # Chapitre_6 à Chapitre_10 (trigonometrie/produit_scalaire/geometrie_reperee/
    # probabilites_conditionnelles/variables_aleatoires) : nouveaux générateurs
    # créés par la mission "rééquilibrage additif" (2026-09-01) — voir
    # tools/generate_derivative_exercises.py pour le contexte complet.
    "premiere": (
        derivatives, exponentielle, second_degre, suites, tangente, variations,
        trigonometrie, produit_scalaire, geometrie_reperee, probabilites_conditionnelles,
        variables_aleatoires,
    ),
}


def _notion_of(module, family):
    """Voir docstring du module : notion portée par Family.notion si présent,
    sinon par la constante NOTION du module."""
    return getattr(family, "notion", None) or module.NOTION


def available_notions(class_level=None):
    """{(class_level, chapter_id, notion): [{"family_id", "label", "level"}, ...]}
    — tout ce qui peut réellement être généré à la demande aujourd'hui.
    `class_level=None` renvoie les 3 classes ; sinon limité à celle demandée
    (renvoie {} pour une classe qui n'a aucun générateur, jamais une
    exception). Construit à chaque appel à partir de FAMILIES (léger,
    aucune E/S, uniquement des attributs déjà en mémoire)."""
    out = {}
    levels = (class_level,) if class_level else tuple(_MODULES_BY_CLASS_LEVEL)
    for level in levels:
        for module in _MODULES_BY_CLASS_LEVEL.get(level, ()):
            for family in module.FAMILIES:
                key = (level, module.CHAPTER_ID, _notion_of(module, family))
                out.setdefault(key, []).append({
                    "family_id": family.id,
                    "label": family.label,
                    "level": family.level,
                })
    return out


def _find_module(class_level, chapter_id, notion, family_id):
    """Résout SANS AMBIGUÏTÉ le module propriétaire d'une famille, à partir
    du tuple complet (voir docstring du module ci-dessus — family_id seul ne
    suffit pas). None si aucune correspondance exacte."""
    for module in _MODULES_BY_CLASS_LEVEL.get(class_level, ()):
        if module.CHAPTER_ID != chapter_id:
            continue
        for family in module.FAMILIES:
            if family.id == family_id and _notion_of(module, family) == notion:
                return module
    return None


def generate(class_level, chapter_id, notion, family_id, seed=None):
    """Génère un exercice via le module propriétaire de
    (class_level, chapter_id, notion, family_id), ou None si ce tuple ne
    correspond à rien de connu (à l'appelant de répondre 404/400 — ce
    module ne connaît pas Flask)."""
    module = _find_module(class_level, chapter_id, notion, family_id)
    if module is None:
        return None
    return module.generate_one(family_id, seed=seed)
