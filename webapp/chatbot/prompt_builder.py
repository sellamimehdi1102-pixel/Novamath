"""
Assemble le prompt système envoyé au fournisseur IA : méthode pédagogique,
règles de notation mathématique, contexte NovaMath compact (context_builder.py),
contexte RAG (knowledge_engine.py — quelques notions de cours pertinentes,
jamais les cours entiers) et préférences utilisateur (longueur de réponse,
niveau d'explication). Le Rule Engine et le Math Engine court-circuitent déjà
l'appel LLM en amont (conversation_manager.py) quand ils suffisent seuls.
"""
from .context_builder import build_context_summary, summary_to_text
from .services import intent_service, pedagogy_templates

BASE_SYSTEM_PROMPT = """Tu es l'assistant pédagogique NovaMath, spécialisé en mathématiques pour des élèves du secondaire (collège/lycée).

RÈGLES DE NOTATION (obligatoires, jamais d'exception) :
- Utilise toujours les symboles mathématiques standards : ² ³ × ÷ √ π ∑ et les fractions écrites clairement (ex: 3/4 ou en LaTeX).
- N'écris jamais "au carré", "fois", "divisé par" en toutes lettres si le symbole existe.
- Utilise LaTeX entre $...$ (inline) ou $$...$$ (bloc) pour toute expression un peu complexe (équations, fractions, racines) : le frontend rend ce LaTeX avec KaTeX.

Adapte le vocabulaire, la longueur et le niveau de détail au profil de l'élève ci-dessous. Sois bienveillant, encourageant, jamais condescendant."""

# MÉTHODE PÉDAGOGIQUE (chantier continuité conversationnelle, 2026-08-22) :
# avant cette correction, une seule et même consigne ("progresse en 6 étapes,
# arrête-toi après chacune") s'appliquait à TOUTE question, y compris une
# simple définition ou un "pourquoi ?" — le LLM devait deviner lui-même si la
# question était "purement factuelle/hors exercice" (clause d'exception déjà
# présente, mais peu fiable : cause racine confirmée des réponses transformées
# à tort en parcours guidé, voir audit du 2026-08-22). Désormais choisie par
# le CODE à partir de l'intention déjà classifiée (intent_service.classify),
# jamais laissée à l'appréciation du modèle.
_GUIDED_METHOD_INSTRUCTION = """MÉTHODE PÉDAGOGIQUE (obligatoire) :
Tu n'es jamais un simple générateur de réponse finale. Face à cet exercice ou cette méthode à dérouler, progresse dans cet ordre, et ARRÊTE-toi après chaque étape pour laisser l'élève réagir (sauf s'il demande explicitement la solution complète) :
1. Une question qui aide l'élève à identifier ce qu'il doit chercher.
2. Un premier indice (sans donner la méthode).
3. Un second indice plus précis, ou le nom de la méthode/propriété à utiliser.
4. Une explication de la méthode, avec un exemple similaire si utile.
5. La solution détaillée, étape par étape.
6. Un conseil pour éviter l'erreur la prochaine fois."""

_DIRECT_METHOD_INSTRUCTION = """MÉTHODE PÉDAGOGIQUE (obligatoire) :
L'élève pose une question directe (définition, explication, "pourquoi ?", propriété, méthode générale, reformulation...). Réponds-y clairement et directement — ne transforme PAS cette question en exercice guidé et n'impose aucune étape artificielle ni pause d'attente si l'élève n'en a pas demandé une. Tu peux structurer ta réponse (courte explication puis exemple si utile), mais réponds réellement à ce qui est demandé."""

_DEFAULT_METHOD_INSTRUCTION = """MÉTHODE PÉDAGOGIQUE (obligatoire) :
Si la question est purement factuelle ou hors exercice, réponds directement et clairement. Si l'élève travaille sur un exercice ou une méthode à dérouler, progresse pas à pas (une question, un indice, la méthode, la solution, un conseil), en t'arrêtant après chaque étape sauf demande explicite de la solution complète."""

# Intents qui expriment un exercice/une méthode à dérouler pas à pas — seuls
# ceux-ci déclenchent la progression en 6 étapes par défaut.
_GUIDED_INTENTS = {
    intent_service.EXERCICE, intent_service.METHODE, intent_service.DEMONSTRATION, intent_service.QUIZ,
}
# Intents qui expriment une question directe — réponse franche, sans étapes
# imposées (voir aussi pedagogy_templates._INTENT_INSTRUCTIONS pour la nuance
# fine par intent, ceci ne fixe que le cadre général du prompt de base).
_DIRECT_INTENTS = {
    intent_service.DEFINITION, intent_service.EXPLICATION, intent_service.COURS, intent_service.RESUME,
    intent_service.PROPRIETE, intent_service.FORMULE, intent_service.RAPPEL, intent_service.REVISION,
    intent_service.REFORMULATION, intent_service.FOLLOWUP, intent_service.INDICE, intent_service.CORRECTION,
    intent_service.FICHE, intent_service.RESTART_BASICS,
}


def _method_instruction(intent_result):
    intent = (intent_result or {}).get("intent")
    if intent in _GUIDED_INTENTS:
        return _GUIDED_METHOD_INSTRUCTION
    if intent in _DIRECT_INTENTS:
        return _DIRECT_METHOD_INSTRUCTION
    return _DEFAULT_METHOD_INSTRUCTION


def _length_instruction(response_length):
    return {
        "court": "Réponds de façon très concise (quelques phrases maximum).",
        "normal": "Réponds de façon claire et structurée, sans être trop long.",
        "detaille": "Développe tes réponses en détail, avec des exemples si utile.",
    }.get(response_length, "Réponds de façon claire et structurée.")


def _explanation_instruction(level):
    return {
        "college": "L'élève est au collège : vocabulaire simple, pas de notions avancées.",
        "lycee": "L'élève est au lycée : tu peux utiliser un vocabulaire mathématique plus rigoureux.",
        "expert": "L'élève maîtrise bien les bases : va droit au but, moins de reformulation.",
        "auto": "Adapte automatiquement le niveau de vocabulaire à la progression de l'élève décrite ci-dessous.",
    }.get(level, "Adapte automatiquement le niveau de vocabulaire à la progression de l'élève décrite ci-dessous.")


def build_system_prompt(
    user, chatbot_settings, chapters_summary=None, rag_context=None, mentions_block=None, intent_result=None,
    class_level=None, topic_label=None,
):
    response_length = chatbot_settings.get("responseLength", "normal")
    explanation_level = chatbot_settings.get("explanationLevel", "auto")

    # `memoryEnabled` (paramètres du chatbot) : jusqu'ici ce réglage n'avait
    # aucun effet — le profil élève était toujours injecté. Désormais,
    # désactivé, la conversation n'a plus accès au profil NovaMath réel.
    if chatbot_settings.get("memoryEnabled", True):
        summary = build_context_summary(user, chapters_summary, class_level=class_level)
        context_text = summary_to_text(summary)
        profile_block = f"PROFIL NOVAMATH DE L'ÉLÈVE :\n{context_text}"
    else:
        profile_block = "Mémoire de profil désactivée par l'élève dans les paramètres : ne suppose rien sur son niveau ou son historique."

    rag_block = (
        f"\n\nEXTRAITS DE COURS NOVAMATH PERTINENTS (appuie-toi dessus, ne les recopie pas mot pour mot) :\n{rag_context}"
        if rag_context else ""
    )
    # Priorité sur le RAG générique : une mention "@" est une intention
    # explicite de l'élève, la ressource résolue doit primer.
    mentions_prompt_block = f"\n\n{mentions_block}" if mentions_block else ""

    intent_instruction = pedagogy_templates.build_intent_instruction(intent_result, topic_label=topic_label)
    mode_instruction = pedagogy_templates.build_mode_instruction(chatbot_settings.get("mode"))
    extra_instructions = "\n".join(filter(None, [intent_instruction, mode_instruction]))
    extra_block = f"\n{extra_instructions}" if extra_instructions else ""

    return (
        f"{BASE_SYSTEM_PROMPT}\n\n"
        f"{_method_instruction(intent_result)}\n\n"
        f"{_length_instruction(response_length)}\n"
        f"{_explanation_instruction(explanation_level)}"
        f"{extra_block}\n\n"
        f"{profile_block}"
        f"{mentions_prompt_block}"
        f"{rag_block}"
    )


def build_messages(history_rows, max_turns=20):
    """Convertit l'historique SQLite (webapp/db.py::list_messages) au format
    attendu par les providers ({role, content}), tronqué aux derniers tours —
    mémoire courte de Phase 1, sans compression sémantique (Phase 2)."""
    trimmed = history_rows[-max_turns:]
    return [{"role": m["role"], "content": m["content"]} for m in trimmed]
