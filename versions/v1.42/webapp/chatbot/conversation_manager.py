"""
Orchestre le chatbot : CRUD conversations/messages (SQLite via webapp/db.py),
puis pipeline hybride AVANT tout appel LLM — Rule Engine (salutations/
identité) -> Math Engine (calcul déterministe via sympy) -> Knowledge Engine
(définitions/propriétés retrouvées dans les cours, réponse directe si la
correspondance est claire) -> sinon Prompt Builder (avec contexte RAG) +
Provider Manager en streaming. Point d'entrée unique utilisé par les routes
Flask (webapp/server.py) — aucune route n'accède directement à db.py ni aux
providers.
"""
from datetime import date

import db
from auth import read_user_settings

from . import rule_engine, math_engine, knowledge_engine, cache
from .prompt_builder import build_system_prompt, build_messages
from .provider_manager import get_provider

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
def stream_reply(user, conversation_id, user_message, chapters_summary=None):
    """Générateur de fragments texte. Persiste le message utilisateur avant de
    commencer, puis le message assistant complet à la fin du flux — pour que
    l'historique reste cohérent même si le client interrompt le stream."""
    conv = db.get_conversation(conversation_id, user["id"])
    if conv is None:
        raise ValueError("Conversation introuvable.")

    check_and_increment_quota(user["id"])
    db.add_message(conversation_id, "user", user_message)

    # Titre auto : première question de la conversation, tronquée.
    if conv["title"] == "Nouvelle conversation":
        auto_title = user_message.strip()[:60] or "Nouvelle conversation"
        db.update_conversation(conversation_id, user["id"], title=auto_title)

    settings = read_user_settings(user["id"])
    chatbot_settings = settings.get("chatbot", {})

    internal_answer = _try_internal_answer(user_message)
    if internal_answer is not None:
        db.add_message(conversation_id, "assistant", internal_answer)
        db.touch_conversation(conversation_id)
        yield internal_answer
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
    system_prompt = build_system_prompt(user, chatbot_settings, chapters_summary, rag_context)
    messages = build_messages(history_rows)
    provider = get_provider(provider=provider_name, model=model_name)

    full_reply = []
    try:
        for chunk in provider.stream_chat(
            messages,
            system_prompt,
            temperature=float(chatbot_settings.get("temperature", 0.6)),
        ):
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
    rag_context = knowledge_engine.context_block(last_user["content"])
    system_prompt = build_system_prompt(user, chatbot_settings, chapters_summary, rag_context)
    messages = build_messages(db.list_messages(conversation_id))
    provider = get_provider(provider=provider_name, model=model_name)

    full_reply = []
    try:
        for chunk in provider.stream_chat(
            messages, system_prompt, temperature=float(chatbot_settings.get("temperature", 0.6))
        ):
            full_reply.append(chunk)
            yield chunk
    finally:
        if full_reply:
            reply_text = "".join(full_reply)
            db.add_message(conversation_id, "assistant", reply_text)
            db.touch_conversation(conversation_id)
            cache_key = cache.make_key(user["id"], provider_name, model_name, last_user["content"])
            cache.set(cache_key, reply_text)


def set_feedback(user_id, message_id, liked):
    message = db.get_message(message_id)
    if message is None:
        raise ValueError("Message introuvable.")
    conv = db.get_conversation(message["conversation_id"], user_id)
    if conv is None:
        raise ValueError("Message introuvable.")
    db.set_message_feedback(message_id, liked)
