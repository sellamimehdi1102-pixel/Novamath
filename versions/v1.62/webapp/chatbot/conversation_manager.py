"""
Orchestre le chatbot : CRUD conversations/messages (SQLite via webapp/db.py),
puis pipeline local-first AVANT tout appel LLM (v2.12 : le LLM devient un
filet de sécurité, jamais le premier réflexe) — Rule Engine (salutations/
identité) -> Math Engine (calcul déterministe via sympy) -> Knowledge Engine
(définitions/propriétés retrouvées dans les cours) -> Local Knowledge Service
(progression/statistiques/dashboard/profil/exercices scopés par chapitre,
données réelles de l'élève, jamais d'appel IA) -> sinon Prompt Builder (avec
contexte RAG) + LLM Fallback Service en streaming. Point d'entrée unique
utilisé par les routes Flask (webapp/server.py) — aucune route n'accède
directement à db.py ni aux providers.
"""
from datetime import date

import db
from auth import read_user_settings

from . import rule_engine, math_engine, knowledge_engine, cache
from .context_builder import build_context_summary
from .prompt_builder import build_system_prompt, build_messages
from .services import (
    action_cards_service, intent_service, llm_fallback_service, local_knowledge_service,
    mentions_service, search_service, variable_resolver,
)

DAILY_QUOTA = 200


class QuotaExceeded(Exception):
    pass


def _today():
    return date.today().isoformat()


def check_and_increment_quota(user_id):
    count = db.increment_chatbot_quota(user_id, _today())
    if count > DAILY_QUOTA:
        raise QuotaExceeded(f"Limite quotidienne de {DAILY_QUOTA} messages atteinte. Réessaie demain.")
    return count


def quota_status(user_id):
    used = db.get_chatbot_quota(user_id, _today())
    return {"used": used, "limit": DAILY_QUOTA}


# ── Conversations ────────────────────────────────────────────────────────────
def create_conversation(user_id, title="Nouvelle conversation"):
    conv_id = db.create_conversation(user_id, title)
    return db.get_conversation(conv_id, user_id)


def list_conversations(user_id, search=None):
    return db.list_conversations(user_id, search)


def rename_conversation(user_id, conversation_id, title):
    return db.update_conversation(conversation_id, user_id, title=title)


def pin_conversation(user_id, conversation_id, pinned):
    return db.update_conversation(conversation_id, user_id, pinned=pinned)


def delete_conversation(user_id, conversation_id):
    db.delete_conversation(conversation_id, user_id)


def get_messages(user_id, conversation_id):
    conv = db.get_conversation(conversation_id, user_id)
    if conv is None:
        return None
    return db.list_messages(conversation_id)


# ── Pipeline hybride (court-circuite le LLM quand la logique interne suffit) ─
def _try_internal_answer(user_message):
    """Rule Engine (salutations/identité) -> Math Engine (calcul déterministe)
    -> Knowledge Engine (définition retrouvée avec une correspondance nette
    dans les cours). Renvoie une réponse toute faite, ou None si seul le LLM
    peut répondre (question ouverte, méthode à expliquer pas à pas...)."""
    answer = rule_engine.try_handle(user_message)
    if answer is not None:
        return answer
    answer = math_engine.try_solve(user_message)
    if answer is not None:
        return answer
    return knowledge_engine.try_answer_definition(user_message)


# ── Envoi d'un message (génère la réponse en streaming) ─────────────────────
def stream_reply(user, conversation_id, user_message, chapters_summary=None, mentions=None):
    """Générateur de fragments texte. Persiste le message utilisateur avant de
    commencer, puis le message assistant complet à la fin du flux — pour que
    l'historique reste cohérent même si le client interrompt le stream.
    `mentions` : ressources "@" résolues côté frontend (chapter_id/notion_id
    ou exercise_id) — injectées telles quelles dans le prompt système, jamais
    devinées par le LLM (voir mentions_service.build_grounding_block)."""
    conv = db.get_conversation(conversation_id, user["id"])
    if conv is None:
        raise ValueError("Conversation introuvable.")

    check_and_increment_quota(user["id"])
    db.add_message(conversation_id, "user", user_message, mentions=mentions)

    # Titre auto : première question de la conversation, tronquée.
    if conv["title"] == "Nouvelle conversation":
        auto_title = user_message.strip()[:60] or "Nouvelle conversation"
        db.update_conversation(conversation_id, user["id"], title=auto_title)

    settings = read_user_settings(user["id"])
    chatbot_settings = settings.get("chatbot", {})

    # Classification d'intention (Phase G) : détecte les demandes
    # incompréhensibles AVANT tout appel LLM — jamais laisser le fournisseur
    # IA inventer une réponse à "aaaa" ou "......".
    context_summary = build_context_summary(user, chapters_summary)
    intent_result = intent_service.classify(user_message, context_summary)
    if intent_result["intent"] == intent_service.UNCLEAR:
        db.add_message(conversation_id, "assistant", intent_service.CLARIFICATION_MESSAGE)
        db.touch_conversation(conversation_id)
        yield intent_service.CLARIFICATION_MESSAGE
        return

    # Une mention "@" seule ("@Progression", sans question ouverte autour,
    # Phase R) est une intention directe tout aussi locale qu'une phrase
    # tapée — mêmes données réelles, même moteur, jamais le LLM.
    mention_intent = mentions_service.single_data_mention_intent(user_message, mentions)
    if mention_intent:
        intent_result = {**intent_result, "intent": mention_intent}

    internal_answer = _try_internal_answer(user_message)
    if internal_answer is not None:
        db.add_message(conversation_id, "assistant", internal_answer)
        db.touch_conversation(conversation_id)
        yield internal_answer
        return

    # Moteur de réponses locales (Phase Q, v2.12) : le LLM ne doit être qu'un
    # filet de sécurité, jamais le premier réflexe. Toute intention couverte
    # localement (données réelles de l'élève, exercice scopé par chapitre —
    # jamais un autre chapitre, jamais halluciné) est répondue ici, sans
    # jamais appeler le fournisseur IA.
    local_answer = local_knowledge_service.try_answer(
        intent_result, user, context_summary, chatbot_settings, user_message=user_message,
    )
    if local_answer is not None:
        db.add_message(conversation_id, "assistant", local_answer)
        db.touch_conversation(conversation_id)
        yield local_answer
        return

    history_enabled = chatbot_settings.get("historyEnabled", True)
    history_rows = db.list_messages(conversation_id) if history_enabled else [
        {"role": "user", "content": user_message}
    ]

    provider_name = chatbot_settings.get("provider")
    model_name = chatbot_settings.get("model")
    cache_key = cache.make_key(user["id"], provider_name, model_name, user_message)
    cached_answer = cache.get(cache_key)
    if cached_answer is not None:
        db.add_message(conversation_id, "assistant", cached_answer)
        db.touch_conversation(conversation_id)
        yield cached_answer
        return

    rag_context = knowledge_engine.context_block(user_message)
    mentions_block = mentions_service.build_grounding_block(mentions, user=user, chapters_summary=chapters_summary)
    system_prompt = build_system_prompt(
        user, chatbot_settings, chapters_summary, rag_context, mentions_block, intent_result=intent_result,
    )
    messages = build_messages(history_rows)

    full_reply = []
    try:
        for chunk in llm_fallback_service.generate(messages, system_prompt, chatbot_settings):
            full_reply.append(chunk)
            yield chunk
    finally:
        if full_reply:
            reply_text = "".join(full_reply)
            db.add_message(conversation_id, "assistant", reply_text)
            db.touch_conversation(conversation_id)
            cache.set(cache_key, reply_text)


def regenerate_last(user, conversation_id, chapters_summary=None):
    """Supprime le dernier message assistant et redemande une réponse à partir
    du dernier message utilisateur (rejoué, pas dupliqué)."""
    rows = db.list_messages(conversation_id)
    if not rows or rows[-1]["role"] != "assistant":
        raise ValueError("Rien à régénérer.")
    last_user = next((m for m in reversed(rows[:-1]) if m["role"] == "user"), None)
    if last_user is None:
        raise ValueError("Aucun message utilisateur précédent.")
    db.delete_message(rows[-1]["id"])

    check_and_increment_quota(user["id"])
    settings = read_user_settings(user["id"])
    chatbot_settings = settings.get("chatbot", {})
    provider_name = chatbot_settings.get("provider")
    model_name = chatbot_settings.get("model")
    context_summary = build_context_summary(user, chapters_summary)
    intent_result = intent_service.classify(last_user["content"], context_summary)
    mention_intent = mentions_service.single_data_mention_intent(last_user["content"], last_user.get("mentions"))
    if mention_intent:
        intent_result = {**intent_result, "intent": mention_intent}

    # Même priorité locale que stream_reply (Phase Q) : régénérer une
    # question de progression/statistiques/exercice ne doit pas non plus
    # appeler le LLM.
    local_answer = local_knowledge_service.try_answer(
        intent_result, user, context_summary, chatbot_settings, user_message=last_user["content"],
    )
    if local_answer is not None:
        db.add_message(conversation_id, "assistant", local_answer)
        db.touch_conversation(conversation_id)
        yield local_answer
        return

    rag_context = knowledge_engine.context_block(last_user["content"])
    mentions_block = mentions_service.build_grounding_block(
        last_user.get("mentions"), user=user, chapters_summary=chapters_summary,
    )
    system_prompt = build_system_prompt(
        user, chatbot_settings, chapters_summary, rag_context, mentions_block, intent_result=intent_result,
    )
    messages = build_messages(db.list_messages(conversation_id))

    full_reply = []
    try:
        for chunk in llm_fallback_service.generate(messages, system_prompt, chatbot_settings):
            full_reply.append(chunk)
            yield chunk
    finally:
        if full_reply:
            reply_text = "".join(full_reply)
            db.add_message(conversation_id, "assistant", reply_text)
            db.touch_conversation(conversation_id)
            cache_key = cache.make_key(user["id"], provider_name, model_name, last_user["content"])
            cache.set(cache_key, reply_text)


# ── Cartes d'action (Phase C) ────────────────────────────────────────────────
def attach_action_cards(user, conversation_id, chapters_summary=None):
    """Appelée par les routes SSE une fois le stream texte terminé (voir
    server.py::api_chatbot_messages/api_chatbot_regenerate) : calcule les
    cartes d'action pertinentes pour le dernier échange et les persiste sur
    le dernier message assistant, pour qu'elles réapparaissent à l'historique.
    Ne modifie jamais le contenu texte déjà streamé/persisté."""
    rows = db.list_messages(conversation_id)
    if not rows or rows[-1]["role"] != "assistant":
        return []
    last_assistant = rows[-1]
    last_user = next((m for m in reversed(rows[:-1]) if m["role"] == "user"), None)
    if last_user is None:
        return []

    context_summary = build_context_summary(user, chapters_summary)
    intent_result = intent_service.classify(last_user["content"], context_summary)
    mention_intent = mentions_service.single_data_mention_intent(last_user["content"], last_user.get("mentions"))
    if mention_intent:
        intent_result = {**intent_result, "intent": mention_intent}
    search_results = search_service.search(last_user["content"], limit=8)
    intent_chapter_id = (
        intent_result["chapter_id"] if intent_result["intent"] == intent_service.EXERCICE else None
    )
    # Phase S : quand la réponse portait sur la progression/les statistiques,
    # propose de revoir le chapitre le plus faible de l'élève (même donnée
    # réelle que celle utilisée pour composer la réponse, variable_resolver.py).
    weak_chapter_id = None
    if intent_result["intent"] in (intent_service.PROGRESSION, intent_service.STATISTIQUE):
        variables = variable_resolver.resolve(user, context_summary, read_user_settings(user["id"]).get("chatbot", {}))
        candidate = variables.get("chapitre_le_plus_faible")
        if candidate and candidate != variable_resolver.NO_DATA:
            weak_chapter_id = candidate
    cards = action_cards_service.build_cards(
        last_user["content"], last_assistant["content"], context_summary, search_results,
        intent_chapter_id=intent_chapter_id, weak_chapter_id=weak_chapter_id,
    )
    if cards:
        db.set_message_cards(last_assistant["id"], cards)
    return cards


def set_feedback(user_id, message_id, liked):
    message = db.get_message(message_id)
    if message is None:
        raise ValueError("Message introuvable.")
    conv = db.get_conversation(message["conversation_id"], user_id)
    if conv is None:
        raise ValueError("Message introuvable.")
    db.set_message_feedback(message_id, liked)
