"""
Décide si une demande de l'élève peut être répondue entièrement en local
(sans appel au fournisseur IA) — Phase Q du chantier v2.12 : le LLM devient
un filet de sécurité, jamais le premier réflexe. Centralise ici ce qui était
dispersé dans conversation_manager.stream_reply() (Phase H) : un seul point
d'entrée à interroger avant de basculer sur llm_fallback_service.py.

Ordre de priorité, du plus déterministe au plus général :
1. Intents "données locales" (progression/statistique/dashboard/profil/
   paramètres/série, intent_service.LOCAL_DATA_INTENTS) : toujours
   répondables, les variables existent toujours (variable_resolver.py),
   même à zéro pour un compte neuf — jamais besoin du LLM.
2. EXERCICE avec un chapitre résolu : recherche strictement scopée par
   chapitre (search_service.search_exercises_in_chapter, Phase H), jamais de
   repli vers un autre chapitre. Message fixe explicite si le chapitre n'a
   aucun exercice.
3. Sinon : None — aucune réponse locale possible, direction LLM
   (comportement inchangé pour les questions ouvertes/inédites).

(EXPLICATION/FORMULE/définition sont déjà traitées en amont, dans le pipeline
existant `rule_engine -> math_engine -> knowledge_engine.try_answer_definition`
— pas de nouvelle logique ici, ce module ne fait que compléter cette chaîne.)
"""
from . import intent_service, response_composer, search_service, variable_resolver

NO_EXERCISE_MESSAGE = (
    "Je n'ai pas encore d'exercice enregistré pour ce chapitre. "
    "Tu peux essayer un autre chapitre, ou me demander une explication ou un exemple sur cette notion à la place."
)


def _try_exercise_answer(intent_result, chatbot_settings, user_message):
    matched = search_service.search_exercises_in_chapter(
        intent_result["chapter_id"], query=user_message, difficulty=intent_result["difficulty"], limit=1,
    )
    if not matched:
        return NO_EXERCISE_MESSAGE
    resolved = search_service.resolve(search_service.SCOPE_EXERCICES, exercise_id=matched[0]["exercise_id"])
    if not resolved:
        return NO_EXERCISE_MESSAGE
    text = (
        f"Voici un exercice sur **{resolved['title']}** :\n\n"
        f"{resolved['snippet']}\n\n"
        "Prends le temps de chercher, et dis-moi si tu veux un indice ou la correction."
    )
    return response_composer.apply_length(text, chatbot_settings.get("responseLength", "normal"))


def try_answer(intent_result, user, context_summary, chatbot_settings, user_message=None):
    """Renvoie le texte de la réponse locale, ou None si aucune réponse
    locale n'est possible pour cette intention (l'appelant doit alors
    basculer sur llm_fallback_service)."""
    intent = intent_result["intent"]

    if intent in intent_service.LOCAL_DATA_INTENTS:
        variables = variable_resolver.resolve(user, context_summary, chatbot_settings)
        text = response_composer.compose(intent, variables, chatbot_settings)
        if text is not None:
            return text

    if intent == intent_service.EXERCICE and intent_result["chapter_id"]:
        return _try_exercise_answer(intent_result, chatbot_settings, user_message)

    return None
