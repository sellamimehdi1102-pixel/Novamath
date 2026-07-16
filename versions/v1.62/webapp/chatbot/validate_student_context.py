"""
Validateur de forme du StudentContext (student_context_resolver.py, Response
Engine v2 Phase 2) — vérifie que la structure renvoyée par `resolve()` a
exactement les champs attendus, du bon type, et que `chapitre_courant`/
`topic_courant` (quand renseignés) sont bien des identifiants canoniques
réels (canonical_ids.py) — jamais une valeur inventée ou périmée.

Utilisé par tests/test_student_context_resolver.py ; peut aussi servir à
tout futur appelant (Response Strategy Engine, Composer...) pour vérifier
défensivement ce qu'il reçoit avant de s'en servir.
"""
import canonical_ids
from chatbot import knowledge_engine

REQUIRED_TOP_LEVEL_LIST_FIELDS = (
    "notions_maitrisees", "notions_faibles", "topics_maitrises", "topics_faibles",
    "mentions", "historique_conversation",
)
REQUIRED_TOP_LEVEL_DICT_FIELDS = ("parametres", "statistiques", "dashboard", "preferences", "progression")
REQUIRED_TOP_LEVEL_SCALAR_FIELDS = ("user_id", "pseudo", "niveau", "niveau_brut", "chapitre_courant", "topic_courant")

REQUIRED_PARAMETRES_FIELDS = (
    "longueur", "niveau_explication", "mode", "memoire_activee",
    "historique_active", "provider", "modele", "temperature",
)
REQUIRED_STATISTIQUES_FIELDS = ("accuracy", "total_exercices", "temps_total", "temps_jour", "temps_semaine")
REQUIRED_DASHBOARD_FIELDS = ("objectif_du_jour", "chapitres_en_cours", "meilleur_chapitre", "chapitre_le_plus_faible")
REQUIRED_PREFERENCES_FIELDS = ("langue", "niveau_explication", "favoris")


def validate_student_context(context):
    """Renvoie la liste des erreurs (vide si tout est correct). Ne lève
    jamais d'exception — un appelant défensif peut inspecter la liste."""
    errors = []

    for field in REQUIRED_TOP_LEVEL_SCALAR_FIELDS:
        if field not in context:
            errors.append(f"champ racine manquant : {field}")

    for field in REQUIRED_TOP_LEVEL_LIST_FIELDS:
        if field not in context:
            errors.append(f"champ racine manquant : {field}")
        elif not isinstance(context[field], list):
            errors.append(f"{field} doit être une liste, reçu {type(context.get(field)).__name__}")

    for field in REQUIRED_TOP_LEVEL_DICT_FIELDS:
        if field not in context:
            errors.append(f"champ racine manquant : {field}")
        elif not isinstance(context[field], dict):
            errors.append(f"{field} doit être un dict, reçu {type(context.get(field)).__name__}")

    if "parametres" in context:
        for field in REQUIRED_PARAMETRES_FIELDS:
            if field not in context["parametres"]:
                errors.append(f"parametres.{field} manquant")

    if "statistiques" in context:
        for field in REQUIRED_STATISTIQUES_FIELDS:
            if field not in context["statistiques"]:
                errors.append(f"statistiques.{field} manquant")

    if "dashboard" in context:
        for field in REQUIRED_DASHBOARD_FIELDS:
            if field not in context["dashboard"]:
                errors.append(f"dashboard.{field} manquant")

    if "preferences" in context:
        for field in REQUIRED_PREFERENCES_FIELDS:
            if field not in context["preferences"]:
                errors.append(f"preferences.{field} manquant")

    # chapitre_courant/topic_courant : jamais une valeur inventée — doivent
    # être None ou correspondre à un chapitre/notion RÉEL du Knowledge Engine.
    chapter_id = context.get("chapitre_courant")
    if chapter_id is not None:
        if canonical_ids.resolve_chapter_id(chapter_id) != chapter_id:
            errors.append(f"chapitre_courant={chapter_id!r} n'est pas sous forme canonique")
        topic_id = context.get("topic_courant")
        if topic_id is not None and knowledge_engine.get_notion(chapter_id, topic_id) is None:
            errors.append(f"topic_courant={topic_id!r} n'existe pas dans {chapter_id} (topic_id invalide)")

    # topics_faibles/topics_maitrises : chaque entrée doit pointer vers une
    # vraie notion (jamais un topic_id orphelin).
    for field in ("topics_faibles", "topics_maitrises"):
        for entry in context.get(field) or []:
            if knowledge_engine.get_notion(entry.get("chapter_id"), entry.get("topic_id")) is None:
                errors.append(f"{field} contient un topic_id invalide : {entry}")

    return errors
