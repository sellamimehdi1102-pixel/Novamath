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
import logging
import time

import db
import quota_service
from auth import read_user_settings
from quota_service import QuotaType

from . import rule_engine, math_engine, knowledge_engine, cache, student_context_resolver
from .context_builder import build_context_summary
from .prompt_builder import build_system_prompt, build_messages
from .services import (
    action_cards_service, intent_service, llm_call_analytics, llm_fallback_service, local_knowledge_service,
    local_response_engine, mentions_service, pipeline_metrics, response_strategy, search_service,
    variable_resolver,
)

logger = logging.getLogger("chatbot.conversation_manager")

# ── Feature flags (Phase 3B, intégration progressive) ───────────────────────
# Chaque brique est indépendante et réversible INSTANTANÉMENT (remettre à
# False) sans toucher au code — c'est la garantie demandée pour un
# déploiement progressif, mesurable, jamais brutal.
#
# ENABLE_INTENT_ENGINE_V2 : intent_service.py EST déjà l'Intent Engine v2
# (portage Phase 1) — ce flag ne restaure pas un ancien fichier disparu, il
# restreint la classification aux intents "historiques" (ceux qui existaient
# avant le portage) si désactivé, pour un retour de comportement fidèle sans
# dépendre d'un second fichier à maintenir.
ENABLE_INTENT_ENGINE_V2 = True

# ENABLE_STUDENT_CONTEXT : remplace STUDENT_CONTEXT_RESOLVER_ENABLED (Phase
# 1+2) — même rôle, nom aligné sur les flags de cette phase. L'ancien nom
# reste disponible ci-dessous (alias) pour compatibilité ascendante.
ENABLE_STUDENT_CONTEXT = True
STUDENT_CONTEXT_RESOLVER_ENABLED = ENABLE_STUDENT_CONTEXT

# ENABLE_RESPONSE_STRATEGY (Étape 1) : calcule la décision du Strategy Engine
# à chaque tour réel, EN APARTÉ — comparée au moteur qui répond réellement
# (voir pipeline_metrics.log_comparison), mais NE MODIFIE JAMAIS la réponse
# envoyée à l'élève à elle seule (voir ENABLE_LOCAL_RESPONSE_ENGINE).
ENABLE_RESPONSE_STRATEGY = True

# ENABLE_LOCAL_RESPONSE_ENGINE (Étapes 2+3) : quand True ET que la décision du
# Strategy Engine tombe sur un moteur listé dans
# LOCAL_RESPONSE_ENGINE_ALLOWED_ENGINES, la réponse du Local Response Engine
# REMPLACE réellement l'appel à l'ancien pipeline pour ce tour. Sinon (moteur
# hors périmètre, ou flag à False), l'ancien pipeline s'exécute EXACTEMENT
# comme avant, sans aucune modification.
ENABLE_LOCAL_RESPONSE_ENGINE = True

# Périmètre actuel du déploiement progressif :
#   Étape 2 : salutations/remerciements (Rule Engine) + Dashboard (données
#             locales : progression/statistiques/dashboard/profil/paramètres/
#             série)
#   Étape 3 : Knowledge Response Composer (définition/cours/résumé/méthode/
#             propriété/exemple), couvert par ENGINE_KNOWLEDGE et
#             ENGINE_SEARCH (grounding générique, même composeur — voir
#             knowledge_response_composer.py)
#   Étape 4 (extension à Exercise Engine et au-delà) : PAS encore incluse ici,
#             volontairement — Math Engine reste géré par l'ancien
#             `_try_internal_answer` (déjà local, aucun gain à migrer).
LOCAL_RESPONSE_ENGINE_ALLOWED_ENGINES = {
    response_strategy.ENGINE_RULE,
    response_strategy.ENGINE_DASHBOARD,
    response_strategy.ENGINE_KNOWLEDGE,
    response_strategy.ENGINE_SEARCH,
}

# ENABLE_LLM_FALLBACK : coupe-circuit ultime — si False, plus aucun appel réel
# au fournisseur IA n'est effectué ; un message fixe est renvoyé à la place.
# Sert de garde-fou opérationnel (incident fournisseur, maîtrise des coûts),
# pas un usage courant.
ENABLE_LLM_FALLBACK = True
LLM_DISABLED_MESSAGE = (
    "Le mode intelligence artificielle est temporairement désactivé. "
    "Je ne peux répondre qu'aux questions couvertes par les données du cours pour l'instant."
)

# ENABLE_LLM_CALL_ANALYTICS (Phase 4, Mission 3) : journalise, en aparté, la
# raison classée automatiquement de chaque appel LLM réel — pure
# observabilité (voir llm_call_analytics.py), ne modifie jamais la réponse.
ENABLE_LLM_CALL_ANALYTICS = True

# Intents "historiques" (existaient avant l'Intent Engine v2, Phase 1) —
# utilisés uniquement quand ENABLE_INTENT_ENGINE_V2=False pour restreindre la
# classification à un comportement fidèle à l'avant-portage.
_LEGACY_INTENTS = {
    intent_service.EXERCICE, intent_service.EXEMPLE, intent_service.EXPLICATION, intent_service.QUIZ,
    intent_service.FICHE, intent_service.CORRECTION, intent_service.RESTART_BASICS, intent_service.FORMULE,
    intent_service.PROGRESSION, intent_service.STATISTIQUE, intent_service.DASHBOARD, intent_service.PROFIL,
    intent_service.PARAMETRES, intent_service.SERIE, intent_service.NONE_INTENT, intent_service.UNCLEAR,
}


def _classify_intent(user_message, context_summary, class_level=None):
    """Classification d'intention, respectant ENABLE_INTENT_ENGINE_V2. Le
    module `intent_service.py` est déjà l'Intent Engine v2 (aucun ancien
    fichier à restaurer) — désactiver le flag retombe sur NONE_INTENT pour
    tout intent introduit par le portage (DEFINITION/COURS/RESUME/METHODE/
    PROPRIETE/DEMONSTRATION/INDICE/RAPPEL/REVISION/REFORMULATION), sans
    jamais toucher à UNCLEAR (la détection de charabia reste active dans les
    deux cas — elle existait déjà avant le portage)."""
    result = intent_service.classify(user_message, context_summary, class_level=class_level)
    if not ENABLE_INTENT_ENGINE_V2 and result["intent"] not in _LEGACY_INTENTS:
        result = {**result, "intent": intent_service.NONE_INTENT}
    return result


def _resolve_student_context(user, chapters_summary, chatbot_settings, mentions, history_rows, class_level=None):
    """Calcule le StudentContext v2 sans jamais impacter la réponse envoyée à
    l'élève : une erreur ici est journalisée et avalée, jamais propagée."""
    if not ENABLE_STUDENT_CONTEXT:
        return None
    try:
        return student_context_resolver.resolve(
            user, chapters_summary=chapters_summary, chatbot_settings=chatbot_settings,
            mentions=mentions, history_rows=history_rows, class_level=class_level,
        )
    except Exception:
        return None


def _decide_strategy_shadow(user_message, user, chapters_summary, chatbot_settings, mentions, student_context, debug, class_level=None):
    """Étape 1 : calcule la décision du Strategy Engine sans jamais impacter
    la réponse — une erreur ici est journalisée et avalée."""
    if not ENABLE_RESPONSE_STRATEGY:
        return None
    try:
        return response_strategy.decide_strategy(
            user_message, user, chapters_summary=chapters_summary, chatbot_settings=chatbot_settings,
            mentions=mentions, student_context=student_context, use_cache=True, debug=debug,
            class_level=class_level,
        )
    except Exception:
        logger.exception("Échec du Response Strategy Engine (aparté) — ignoré.")
        return None


def _try_local_response_engine(
    strategy, user_message, user, chapters_summary, chatbot_settings, mentions, student_context, debug, class_level=None,
):
    """Étapes 2+3 : n'exécute (et ne peut donc REMPLACER la réponse) que si la
    décision du Strategy Engine tombe sur un moteur déjà couvert par le
    périmètre actuel du déploiement (LOCAL_RESPONSE_ENGINE_ALLOWED_ENGINES).
    Renvoie `None` si hors périmètre, désactivé, ou en échec — l'appelant
    retombe alors sur l'ancien pipeline, inchangé."""
    if not ENABLE_LOCAL_RESPONSE_ENGINE or strategy is None or strategy.engine not in LOCAL_RESPONSE_ENGINE_ALLOWED_ENGINES:
        return None
    try:
        result = local_response_engine.generate(
            user_message, user, chapters_summary=chapters_summary, chatbot_settings=chatbot_settings,
            mentions=mentions, student_context=student_context, use_cache=True, debug=debug,
            class_level=class_level,
        )
    except Exception:
        logger.exception("Échec du Local Response Engine — repli sur l'ancien pipeline.")
        return None
    if result.should_use_llm or not result.text:
        return None
    return result


def _record_llm_call(user_message, strategy):
    """Journalisation Mission 3 (Phase 4) : pur aparté, une panne ici ne doit
    jamais empêcher la réponse déjà décidée d'être envoyée à l'élève."""
    if not ENABLE_LLM_CALL_ANALYTICS:
        return
    try:
        llm_call_analytics.record(user_message, strategy, LOCAL_RESPONSE_ENGINE_ALLOWED_ENGINES)
    except Exception:
        logger.exception("Échec de la journalisation llm_call_analytics — ignoré.")


# ── Quota de messages IA ─────────────────────────────────────────────────────
# Source de vérité unique : quota_service.py (Feature Flags + Quotas). Cette
# fonction reste le seul point du chatbot qui consomme le quota — appelée une
# fois par tour réel (stream_reply/regenerate_last), jamais par retry_last
# (un hoquet réseau ne coûte pas de message, voir sa docstring).
def check_and_increment_quota(user):
    """Consomme un message IA du quota quotidien de `user` (QuotaType.CHAT_MESSAGES)
    et renvoie le nouveau total consommé aujourd'hui. Lève
    quota_service.QuotaExceededError si la limite du palier actuel est
    dépassée — propagée telle quelle jusqu'à la route Flask
    (webapp/server.py), qui la traduit en réponse HTTP 429."""
    return quota_service.consume(user, QuotaType.CHAT_MESSAGES)


def quota_status(user):
    """Statut du quota de messages IA de `user`, au format historique
    {"used": int, "limit": int|None} consommé par GET /api/chatbot/quota
    (voir server.py). Le format détaillé (remaining/unlimited) vit dans
    quota_service.usage_snapshot(), exposé par le nouveau GET /api/quota."""
    snapshot = quota_service.usage_snapshot(user, QuotaType.CHAT_MESSAGES)
    return {"used": snapshot["used"], "limit": snapshot["limit"]}


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
def _try_internal_answer(user_message, class_level=None):
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
    return knowledge_engine.try_answer_definition(user_message, class_level=class_level)


# ── Envoi d'un message (génère la réponse en streaming) ─────────────────────
def stream_reply(user, conversation_id, user_message, chapters_summary=None, mentions=None, debug=False, class_level=None):
    """Générateur de fragments texte. Persiste le message utilisateur avant de
    commencer, puis le message assistant complet à la fin du flux — pour que
    l'historique reste cohérent même si le client interrompt le stream.
    `mentions` : ressources "@" résolues côté frontend (chapter_id/notion_id
    ou exercise_id) — injectées telles quelles dans le prompt système, jamais
    devinées par le LLM (voir mentions_service.build_grounding_block).
    `debug=True` : journalise (logger DEBUG) un bloc détaillé Intent/Strategy/
    Moteur/Temps/Fallback pour ce tour (Phase 3B).
    `class_level` (optionnel, "seconde" par défaut) : classe active de
    l'élève (curriculum_registry.py) — transportée jusqu'au bout du pipeline
    (StudentContext, Knowledge/Search Engine, grounding des mentions "@")
    afin qu'aucune donnée d'une autre classe ne soit jamais utilisée."""
    conv = db.get_conversation(conversation_id, user["id"])
    if conv is None:
        raise ValueError("Conversation introuvable.")

    check_and_increment_quota(user)
    db.add_message(conversation_id, "user", user_message, mentions=mentions)

    # Titre auto : première question de la conversation, tronquée.
    if conv["title"] == "Nouvelle conversation":
        auto_title = user_message.strip()[:60] or "Nouvelle conversation"
        db.update_conversation(conversation_id, user["id"], title=auto_title)

    yield from _generate_assistant_reply(user, conversation_id, user_message, chapters_summary, mentions, debug, class_level)


def retry_last(user, conversation_id, chapters_summary=None, debug=False, class_level=None):
    """Réessaie la génération de réponse pour le dernier message utilisateur,
    SANS le dupliquer en base — pour le cas où une tentative précédente
    (stream_reply ou regenerate_last) a échoué avant qu'aucun message
    assistant n'ait pu être persisté (panne réseau/fournisseur pendant le
    tout premier essai, cf. robustesse chatbot). Ne consomme pas de quota
    supplémentaire : un hoquet réseau ne doit jamais coûter un message à
    l'élève. Si une réponse assistant a déjà été persistée pour ce tour,
    c'est `regenerate_last` qu'il faut utiliser à la place — celui-ci lève
    une erreur explicite sinon (aucun risque de double génération)."""
    conv = db.get_conversation(conversation_id, user["id"])
    if conv is None:
        raise ValueError("Conversation introuvable.")
    rows = db.list_messages(conversation_id)
    if not rows or rows[-1]["role"] != "user":
        raise ValueError("Rien à réessayer.")
    last_user = rows[-1]
    yield from _generate_assistant_reply(
        user, conversation_id, last_user["content"], chapters_summary, last_user.get("mentions"), debug, class_level,
    )


def _generate_assistant_reply(user, conversation_id, user_message, chapters_summary, mentions, debug, class_level=None):
    """Cœur de sélection/génération de réponse (Intent → Strategy Engine/
    Local Response Engine → moteurs legacy → LLM en dernier recours), extrait
    de stream_reply pour être partagé avec retry_last sans jamais dupliquer
    le message utilisateur (déjà persisté par l'appelant)."""
    t0 = time.perf_counter()
    pipeline_metrics.record_request()

    settings = read_user_settings(user["id"])
    chatbot_settings = settings.get("chatbot", {})

    # Classification d'intention (Phase G) : détecte les demandes
    # incompréhensibles AVANT tout appel LLM — jamais laisser le fournisseur
    # IA inventer une réponse à "aaaa" ou "......".
    context_summary = build_context_summary(user, chapters_summary, class_level=class_level)
    intent_result = _classify_intent(user_message, context_summary, class_level=class_level)
    if intent_result["intent"] == intent_service.UNCLEAR:
        db.add_message(conversation_id, "assistant", intent_service.CLARIFICATION_MESSAGE)
        db.touch_conversation(conversation_id)
        pipeline_metrics.record_response("clarification", local=True, elapsed_ms=(time.perf_counter() - t0) * 1000)
        yield intent_service.CLARIFICATION_MESSAGE
        return

    # Une mention "@" seule ("@Progression", sans question ouverte autour,
    # Phase R) est une intention directe tout aussi locale qu'une phrase
    # tapée — mêmes données réelles, même moteur, jamais le LLM.
    mention_intent = mentions_service.single_data_mention_intent(user_message, mentions)
    if mention_intent:
        intent_result = {**intent_result, "intent": mention_intent}

    # Student Context Resolver v2 (portage Phase 2) : calculé à chaque tour
    # réel — consommé par le Strategy/Local Response Engine ci-dessous quand
    # ils sont activés, sinon un aparté sans effet (comme avant Phase 3B).
    student_context = _resolve_student_context(
        user, chapters_summary, chatbot_settings, mentions, history_rows=None, class_level=class_level,
    )

    # Étape 1 (Phase 3B) : décision du Strategy Engine en aparté, comparée au
    # moteur qui répond réellement plus bas — ne change jamais la réponse à
    # elle seule.
    strategy = _decide_strategy_shadow(
        user_message, user, chapters_summary, chatbot_settings, mentions, student_context, debug,
        class_level=class_level,
    )

    # Étapes 2+3 (Phase 3B) : le Local Response Engine ne remplace la réponse
    # que si la décision tombe dans le périmètre déployé aujourd'hui
    # (LOCAL_RESPONSE_ENGINE_ALLOWED_ENGINES) — sinon `None`, et l'ancien
    # pipeline s'exécute juste en dessous, à l'identique d'avant cette phase.
    local_result = _try_local_response_engine(
        strategy, user_message, user, chapters_summary, chatbot_settings, mentions, student_context, debug,
        class_level=class_level,
    )
    if local_result is not None:
        db.add_message(conversation_id, "assistant", local_result.text)
        db.touch_conversation(conversation_id)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        pipeline_metrics.record_response(local_result.engine, local=True, elapsed_ms=elapsed_ms, fallback=local_result.used_fallback)
        pipeline_metrics.log_comparison(strategy, local_result.engine)
        if debug:
            logger.debug(pipeline_metrics.format_debug_trace(strategy, local_result.engine, elapsed_ms, local_result.used_fallback))
        yield local_result.text
        return

    internal_answer = _try_internal_answer(user_message, class_level=(student_context or {}).get("class_level"))
    if internal_answer is not None:
        db.add_message(conversation_id, "assistant", internal_answer)
        db.touch_conversation(conversation_id)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        pipeline_metrics.record_response("legacy_internal", local=True, elapsed_ms=elapsed_ms)
        pipeline_metrics.log_comparison(strategy, "legacy_internal")
        if debug:
            logger.debug(pipeline_metrics.format_debug_trace(strategy, "legacy_internal", elapsed_ms))
        yield internal_answer
        return

    # Moteur de réponses locales (Phase Q, v2.12) : le LLM ne doit être qu'un
    # filet de sécurité, jamais le premier réflexe. Toute intention couverte
    # localement (données réelles de l'élève, exercice scopé par chapitre —
    # jamais un autre chapitre, jamais halluciné) est répondue ici, sans
    # jamais appeler le fournisseur IA.
    local_answer = local_knowledge_service.try_answer(
        intent_result, user, context_summary, chatbot_settings, user_message=user_message,
        student_context=student_context,
    )
    if local_answer is not None:
        db.add_message(conversation_id, "assistant", local_answer)
        db.touch_conversation(conversation_id)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        pipeline_metrics.record_response("legacy_local_knowledge", local=True, elapsed_ms=elapsed_ms)
        pipeline_metrics.log_comparison(strategy, "legacy_local_knowledge")
        if debug:
            logger.debug(pipeline_metrics.format_debug_trace(strategy, "legacy_local_knowledge", elapsed_ms))
        yield local_answer
        return

    history_enabled = chatbot_settings.get("historyEnabled", True)
    history_rows = db.list_messages(conversation_id) if history_enabled else [
        {"role": "user", "content": user_message}
    ]

    provider_name = chatbot_settings.get("provider")
    model_name = chatbot_settings.get("model")
    cache_key = cache.make_key(
        user["id"], provider_name, model_name, user_message, class_level=(student_context or {}).get("class_level"),
    )
    cached_answer = cache.get(cache_key)
    if cached_answer is not None:
        db.add_message(conversation_id, "assistant", cached_answer)
        db.touch_conversation(conversation_id)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        pipeline_metrics.record_response("cache", local=True, elapsed_ms=elapsed_ms)
        pipeline_metrics.log_comparison(strategy, "cache")
        if debug:
            logger.debug(pipeline_metrics.format_debug_trace(strategy, "cache", elapsed_ms))
        yield cached_answer
        return

    if not ENABLE_LLM_FALLBACK:
        db.add_message(conversation_id, "assistant", LLM_DISABLED_MESSAGE)
        db.touch_conversation(conversation_id)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        pipeline_metrics.record_response("llm_disabled", local=True, elapsed_ms=elapsed_ms)
        if debug:
            logger.debug(pipeline_metrics.format_debug_trace(strategy, "llm_disabled", elapsed_ms))
        yield LLM_DISABLED_MESSAGE
        return

    rag_context = knowledge_engine.context_block(user_message, class_level=(student_context or {}).get("class_level"))
    mentions_block = mentions_service.build_grounding_block(
        mentions, user=user, chapters_summary=chapters_summary, class_level=(student_context or {}).get("class_level"),
    )
    system_prompt = build_system_prompt(
        user, chatbot_settings, chapters_summary, rag_context, mentions_block, intent_result=intent_result,
        class_level=(student_context or {}).get("class_level"),
    )
    messages = build_messages(history_rows)

    pipeline_metrics.log_comparison(strategy, response_strategy.ENGINE_LLM)
    _record_llm_call(user_message, strategy)
    if debug:
        logger.debug(pipeline_metrics.format_debug_trace(strategy, response_strategy.ENGINE_LLM, (time.perf_counter() - t0) * 1000))

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
            pipeline_metrics.record_response(response_strategy.ENGINE_LLM, local=False, elapsed_ms=(time.perf_counter() - t0) * 1000)


def regenerate_last(user, conversation_id, chapters_summary=None, debug=False, class_level=None):
    """Supprime le dernier message assistant et redemande une réponse à partir
    du dernier message utilisateur (rejoué, pas dupliqué)."""
    t0 = time.perf_counter()
    pipeline_metrics.record_request()

    rows = db.list_messages(conversation_id)
    if not rows or rows[-1]["role"] != "assistant":
        raise ValueError("Rien à régénérer.")
    last_user = next((m for m in reversed(rows[:-1]) if m["role"] == "user"), None)
    if last_user is None:
        raise ValueError("Aucun message utilisateur précédent.")
    db.delete_message(rows[-1]["id"])

    check_and_increment_quota(user)
    settings = read_user_settings(user["id"])
    chatbot_settings = settings.get("chatbot", {})
    provider_name = chatbot_settings.get("provider")
    model_name = chatbot_settings.get("model")
    context_summary = build_context_summary(user, chapters_summary, class_level=class_level)
    intent_result = _classify_intent(last_user["content"], context_summary, class_level=class_level)
    mention_intent = mentions_service.single_data_mention_intent(last_user["content"], last_user.get("mentions"))
    if mention_intent:
        intent_result = {**intent_result, "intent": mention_intent}

    student_context = _resolve_student_context(
        user, chapters_summary, chatbot_settings, last_user.get("mentions"), history_rows=None, class_level=class_level,
    )
    strategy = _decide_strategy_shadow(
        last_user["content"], user, chapters_summary, chatbot_settings, last_user.get("mentions"), student_context, debug,
        class_level=class_level,
    )
    local_result = _try_local_response_engine(
        strategy, last_user["content"], user, chapters_summary, chatbot_settings,
        last_user.get("mentions"), student_context, debug, class_level=class_level,
    )
    if local_result is not None:
        db.add_message(conversation_id, "assistant", local_result.text)
        db.touch_conversation(conversation_id)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        pipeline_metrics.record_response(local_result.engine, local=True, elapsed_ms=elapsed_ms, fallback=local_result.used_fallback)
        pipeline_metrics.log_comparison(strategy, local_result.engine)
        yield local_result.text
        return

    # Même priorité locale que stream_reply (Phase Q) : régénérer une
    # question de progression/statistiques/exercice ne doit pas non plus
    # appeler le LLM.
    local_answer = local_knowledge_service.try_answer(
        intent_result, user, context_summary, chatbot_settings, user_message=last_user["content"],
        student_context=student_context,
    )
    if local_answer is not None:
        db.add_message(conversation_id, "assistant", local_answer)
        db.touch_conversation(conversation_id)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        pipeline_metrics.record_response("legacy_local_knowledge", local=True, elapsed_ms=elapsed_ms)
        pipeline_metrics.log_comparison(strategy, "legacy_local_knowledge")
        yield local_answer
        return

    if not ENABLE_LLM_FALLBACK:
        db.add_message(conversation_id, "assistant", LLM_DISABLED_MESSAGE)
        db.touch_conversation(conversation_id)
        pipeline_metrics.record_response("llm_disabled", local=True, elapsed_ms=(time.perf_counter() - t0) * 1000)
        yield LLM_DISABLED_MESSAGE
        return

    rag_context = knowledge_engine.context_block(
        last_user["content"], class_level=(student_context or {}).get("class_level"),
    )
    mentions_block = mentions_service.build_grounding_block(
        last_user.get("mentions"), user=user, chapters_summary=chapters_summary,
        class_level=(student_context or {}).get("class_level"),
    )
    system_prompt = build_system_prompt(
        user, chatbot_settings, chapters_summary, rag_context, mentions_block, intent_result=intent_result,
        class_level=(student_context or {}).get("class_level"),
    )
    messages = build_messages(db.list_messages(conversation_id))
    pipeline_metrics.log_comparison(strategy, response_strategy.ENGINE_LLM)
    _record_llm_call(last_user["content"], strategy)

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
            cache_key = cache.make_key(
                user["id"], provider_name, model_name, last_user["content"],
                class_level=(student_context or {}).get("class_level"),
            )
            cache.set(cache_key, reply_text)
            pipeline_metrics.record_response(response_strategy.ENGINE_LLM, local=False, elapsed_ms=(time.perf_counter() - t0) * 1000)


# ── Cartes d'action (Phase C) ────────────────────────────────────────────────
def attach_action_cards(user, conversation_id, chapters_summary=None, class_level=None):
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

    context_summary = build_context_summary(user, chapters_summary, class_level=class_level)
    intent_result = _classify_intent(last_user["content"], context_summary, class_level=class_level)
    mention_intent = mentions_service.single_data_mention_intent(last_user["content"], last_user.get("mentions"))
    if mention_intent:
        intent_result = {**intent_result, "intent": mention_intent}

    chatbot_settings = read_user_settings(user["id"]).get("chatbot", {})
    _resolve_student_context(
        user, chapters_summary, chatbot_settings, last_user.get("mentions"), history_rows=None, class_level=class_level,
    )

    search_results = search_service.search(last_user["content"], limit=8, class_level=class_level)
    intent_chapter_id = (
        intent_result["chapter_id"] if intent_result["intent"] == intent_service.EXERCICE else None
    )
    # Phase S : quand la réponse portait sur la progression/les statistiques,
    # propose de revoir le chapitre le plus faible de l'élève (même donnée
    # réelle que celle utilisée pour composer la réponse, variable_resolver.py).
    weak_chapter_id = None
    if intent_result["intent"] in (intent_service.PROGRESSION, intent_service.STATISTIQUE):
        variables = variable_resolver.resolve(
            user, context_summary, read_user_settings(user["id"]).get("chatbot", {}), class_level=class_level,
        )
        candidate = variables.get("chapitre_le_plus_faible")
        if candidate and candidate != variable_resolver.NO_DATA:
            weak_chapter_id = candidate
    cards = action_cards_service.build_cards(
        last_user["content"], last_assistant["content"], context_summary, search_results,
        intent_chapter_id=intent_chapter_id, weak_chapter_id=weak_chapter_id, class_level=class_level,
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
