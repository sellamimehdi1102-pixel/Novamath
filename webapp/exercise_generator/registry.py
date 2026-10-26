"""
Registre des générateurs symboliques réellement disponibles pour
POST /api/practice/generate (Chantier "Différenciateurs Premium/Ultra",
2026-08-27).

Cartographie EXACTE de ce qui existe — vérifiée en lisant chaque module
avant d'écrire ce fichier, jamais supposée. Trois packages, un par classe
(curriculum_registry.CURRICULUM_REGISTRY : "troisieme"/"seconde"/"premiere"),
enrichis au fil des missions "rééquilibrage additif" / "rééquilibrage global
de toutes les classes" / "équilibrage définitif de toutes les classes"
(2026-09-01) :
    - exercise_generator_troisieme/ : 14 modules, un par notion
      (developper_distributivite, divisibilite, equation_premier_degre,
      factoriser_somme, fonction_affine_deux_points, fractions_addition,
      fractions_simplification, image_fonction, nombres_relatifs,
      proportionnalite, statistiques, probabilites_troisieme, thales,
      volumes_espace) ;
    - exercise_generator_seconde/ : 4 modules (droites, signes,
      vecteurs_seconde, pourcentages_evolutions) ;
    - exercise_generator/ (Première) : 11 modules (derivatives,
      exponentielle, second_degre, suites, tangente, variations,
      trigonometrie, produit_scalaire, geometrie_reperee,
      probabilites_conditionnelles, variables_aleatoires).

Les 29 modules suivent tous le même contrat :
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
import curriculum_registry
from exercise_generator import (
    derivatives, exponentielle, geometrie_reperee, probabilites_conditionnelles,
    produit_scalaire, second_degre, suites, tangente, trigonometrie, variables_aleatoires,
    variations,
)
from exercise_generator_premiere_specifique import programme_1es
from exercise_generator_quatrieme import relatifs, fractions_sommes, fractions_produits, arithmetique, puissances, calcul_litteral, equations, pythagore, thales_emboites, cosinus, translations_plan, triangles_egaux, espace_volumes, proportionnalite_grandeurs, notion_fonction, statistiques_quatrieme, probabilites_quatrieme
from exercise_generator_seconde import droites, pourcentages_evolutions, signes, vecteurs_seconde
from exercise_generator_troisieme import (
    developper_distributivite, divisibilite, equation_premier_degre, factoriser_somme,
    fonction_affine_deux_points, fractions_addition, fractions_simplification, image_fonction,
    nombres_relatifs, probabilites_troisieme, proportionnalite, statistiques, thales, volumes_espace,
)

_MODULES_BY_CLASS_LEVEL = {
    # Chantier "Quatrième — chapitre pilote Pythagore" (2026-10-24) : classe
    # NON PUBLIÉE — ces familles ne sont listées ni exécutées que si
    # "quatrieme" est servie (prévisualisation locale), voir _is_served().
    "quatrieme": (relatifs, fractions_sommes, fractions_produits, arithmetique, puissances, calcul_litteral, equations, pythagore, thales_emboites, cosinus, translations_plan, triangles_egaux, espace_volumes, proportionnalite_grandeurs, notion_fonction, statistiques_quatrieme, probabilites_quatrieme),
    # nombres_relatifs/proportionnalite/statistiques/probabilites_troisieme/
    # thales (Chapitre_2/6/9/10/14) : nouveaux générateurs créés par la
    # mission "rééquilibrage global de toutes les classes" (2026-09-01).
    "troisieme": (
        developper_distributivite, divisibilite, equation_premier_degre, factoriser_somme,
        fonction_affine_deux_points, fractions_addition, fractions_simplification, image_fonction,
        nombres_relatifs, proportionnalite, statistiques, probabilites_troisieme, thales,
        volumes_espace,
    ),
    # vecteurs_seconde/pourcentages_evolutions (Chapitre_5/10) : nouveaux
    # générateurs créés par la mission "équilibrage définitif de toutes les
    # classes" (2026-09-01) — leur pool n'est PAS dans
    # exercises_generated_seconde.json (voir tools/
    # generate_seconde_curated_additions.py : Seconde ne fusionne pas de
    # generated_exercise_bank, donc ce contenu est distribué directement
    # dans exercises_bank.json), mais ils suivent le même contrat Family/
    # generate_one que droites/signes et sont donc éligibles à la
    # génération à la demande au même titre.
    "seconde": (droites, signes, vecteurs_seconde, pourcentages_evolutions),
    # Chapitre_6 à Chapitre_10 (trigonometrie/produit_scalaire/geometrie_reperee/
    # probabilites_conditionnelles/variables_aleatoires) : nouveaux générateurs
    # créés par la mission "rééquilibrage additif" (2026-09-01) — voir
    # tools/generate_derivative_exercises.py pour le contexte complet.
    "premiere": (
        derivatives, exponentielle, second_degre, suites, tangente, variations,
        trigonometrie, produit_scalaire, geometrie_reperee, probabilites_conditionnelles,
        variables_aleatoires,
    ),
    # Première spécifique (séparée de "premiere" le 2026-10-26, adaptée au
    # manuel « Première ES/L » le même jour ; NON PUBLIÉE — servie seulement en
    # prévisualisation, voir _is_served) : package indépendant
    # exercise_generator_premiere_specifique/, exposé par les vues de
    # programme_1es.py (familles conservées, rattachées aux 9 chapitres du
    # manuel ; les familles hors manuel ne sont ni listées ni générées).
    "premiere_specifique": programme_1es.VUES,
}

# Notions retirées d'un programme officiel : leurs familles restent dans le
# code (réversible) mais ne sont plus proposées ni générées à la demande.
# Première spécifique, programme 2026 : la dérivée de x ↦ g(ax + b) n'est plus
# au programme ; les FONCTIONS cosinus et sinus non plus. Aucune entrée pour
# la Première historique ("premiere"), servie à l'identique.
NOTIONS_HORS_PROGRAMME = {
    ("premiere_specifique", "Composition de fonctions et dérivation"),
    ("premiere_specifique", "Fonctions cosinus et sinus"),
}


def _retired(class_level, notion):
    return (class_level, notion) in NOTIONS_HORS_PROGRAMME


def _notion_of(module, family):
    """Voir docstring du module : notion portée par Family.notion si présent,
    sinon par la constante NOTION du module."""
    return getattr(family, "notion", None) or module.NOTION


def _is_served(class_level):
    """Publication des classes (chantier "préparation de la Quatrième",
    2026-10-24) : POST /api/practice/generate et /options ne valident pas
    eux-mêmes `class_level` contre curriculum_registry (contrairement aux
    autres routes de server.py) — ce module est donc leur point de contrôle.
    Un générateur déclaré ici pour une classe non publiée (en préparation)
    ne doit jamais être listé ni exécuté. Lu à chaque appel (attribut du
    module, jamais une copie figée à l'import)."""
    return class_level in curriculum_registry.CURRICULUM_REGISTRY


def available_notions(class_level=None):
    """{(class_level, chapter_id, notion): [{"family_id", "label", "level"}, ...]}
    — tout ce qui peut réellement être généré à la demande aujourd'hui.
    `class_level=None` renvoie toutes les classes servies ; sinon limité à
    celle demandée (renvoie {} pour une classe qui n'a aucun générateur ou
    qui n'est pas servie, jamais une exception). Construit à chaque appel à
    partir de FAMILIES (léger, aucune E/S, uniquement des attributs déjà en
    mémoire)."""
    out = {}
    levels = (class_level,) if class_level else tuple(_MODULES_BY_CLASS_LEVEL)
    for level in levels:
        if not _is_served(level):
            continue
        for module in _MODULES_BY_CLASS_LEVEL.get(level, ()):
            for family in module.FAMILIES:
                key = (level, module.CHAPTER_ID, _notion_of(module, family))
                if _retired(level, key[2]):
                    continue
                out.setdefault(key, []).append({
                    "family_id": family.id,
                    "label": family.label,
                    "level": family.level,
                })
    return out


def _find_module(class_level, chapter_id, notion, family_id):
    """Résout SANS AMBIGUÏTÉ le module propriétaire d'une famille, à partir
    du tuple complet (voir docstring du module ci-dessus — family_id seul ne
    suffit pas). None si aucune correspondance exacte ou si la classe n'est
    pas servie (voir _is_served)."""
    if not _is_served(class_level) or _retired(class_level, notion):
        return None
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
