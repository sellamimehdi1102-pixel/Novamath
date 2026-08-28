"""
Consommation IA PAR UTILISATEUR (table ai_request_logs) — strictement
distincte de ai_provider_service.py/ai_provider_usage (agrégat GLOBAL par
fournisseur, jamais par utilisateur, jamais modifié par ce module).

Architecture identique au reste du projet :

    webapp/chatbot/conversation_manager.py  →  ai_request_log_service.py  →  db.py

Couche de tracking UNIQUE couvrant TOUT traitement ayant produit une réponse
assistant, pas seulement les vrais appels LLM : record() (Gemini/Claude, vrais
tokens/coût, appelée par conversation_manager.py::_log_llm_call_details, même
call_info que ai_provider_service.record_llm_usage()) et
record_local_response() (moteur local/cache/clarification/LLM désactivé,
tokens ESTIMÉS par heuristique, coût toujours 0 — voir son docstring). Même
tolérance aux pannes des deux côtés : jamais d'exception propagée.

Les statistiques utilisateur (admin_user_profile_service.get_chatbot(), onglet
Chatbot de la fiche utilisateur) sont calculées EXCLUSIVEMENT à partir de
ai_request_logs (voir stats_for_user() ci-dessous) — jamais depuis
ai_provider_usage, qui reste réservée aux statistiques globales
d'administration (Dashboard).
"""
import logging

import ai_provider_service
import db

logger = logging.getLogger("webapp.ai_request_log_service")

# Heuristique standard ~4 caractères = 1 token (approximation communément
# admise pour du texte FR/EN) — utilisée UNIQUEMENT pour les moteurs qui
# n'appellent aucune API réelle (moteur local, cache, clarification...), où
# aucun comptage de tokens n'existe. Chaque ligne produite avec cette
# heuristique est marquée estimated=1 en base, jamais confondue avec un vrai
# comptage fourni par Gemini/Claude (estimated=0).
_CHARS_PER_TOKEN = 4


def estimate_tokens_from_text(text):
    if not text:
        return 0
    return max(1, round(len(text) / _CHARS_PER_TOKEN))


def record(user_id, conversation_id, provider, model, usage, *, success=True, response_time_ms=None,
           is_fallback=False):
    """Enregistre UNE ligne pour CHAQUE appel LLM réel (succès ou échec) —
    même contrat de tolérance que ai_provider_service.record_llm_usage() :
    ne lève JAMAIS d'exception (un échec ici est journalisé et ignoré,
    jamais propagé jusqu'à la réponse déjà envoyée à l'élève).

    `usage` : dict {"prompt_tokens", "completion_tokens", "total_tokens"} ou
    None/vide (échec avant le premier chunk, ou FakeProvider) — les compteurs
    de tokens restent alors à 0, mais la ligne est quand même écrite (une
    requête a bien eu lieu, même sans tokens exploitables). Le coût est
    calculé via ai_provider_service.estimate_llm_cost() — même grille
    tarifaire que pour l'agrégat global, jamais une seconde constante de
    prix dupliquée ici."""
    if not user_id or not provider or not model:
        return
    try:
        usage = usage or {}
        input_tokens = usage.get("prompt_tokens") or 0
        output_tokens = usage.get("completion_tokens") or 0
        total_tokens = usage.get("total_tokens") or (input_tokens + output_tokens)
        cost = ai_provider_service.estimate_llm_cost(provider, model, input_tokens, output_tokens, total_tokens)
        db.create_ai_request_log(
            user_id, conversation_id, provider, model,
            input_tokens=input_tokens, output_tokens=output_tokens, total_tokens=total_tokens,
            estimated_cost=cost, response_time_ms=round(response_time_ms) if response_time_ms else 0,
            success=success, fallback=is_fallback,
            engine="llm", source=provider, estimated=False,
        )
    except Exception:
        logger.exception("ai_request_log_service.record : échec de l'enregistrement — ignoré.")


def record_local_response(user_id, conversation_id, engine, source, model_label, *, user_text="", response_text="",
                           response_time_ms=None, success=True, fallback=False):
    """Enregistre UNE ligne pour CHAQUE réponse assistant qui n'a PAS appelé
    un vrai fournisseur LLM (moteur local, cache, clarification, LLM
    désactivé...) — pour que la Consommation IA reflète TOUT traitement
    ayant servi à répondre à l'élève, pas seulement Gemini/Claude (voir
    conversation_manager.py, appelée au même endroit que db.add_message(...,
    engine=...)). Aucun appel API réel n'ayant eu lieu, aucun vrai comptage
    de tokens n'existe : `input_tokens`/`output_tokens` sont ESTIMÉS depuis
    la longueur du texte (voir estimate_tokens_from_text), et
    `estimated_cost` reste à 0 (aucune dépense externe réelle n'a eu lieu —
    jamais un coût fabriqué). Ligne marquée estimated=1 pour rester
    distinguable des vrais appels LLM. Même tolérance aux pannes que
    record() : n'lève jamais d'exception."""
    if not user_id or not engine:
        return
    try:
        input_tokens = estimate_tokens_from_text(user_text)
        output_tokens = estimate_tokens_from_text(response_text)
        db.create_ai_request_log(
            user_id, conversation_id, source, model_label,
            input_tokens=input_tokens, output_tokens=output_tokens, total_tokens=input_tokens + output_tokens,
            estimated_cost=0, response_time_ms=round(response_time_ms) if response_time_ms else 0,
            success=success, fallback=fallback,
            engine=engine, source=source, estimated=True,
        )
    except Exception:
        logger.exception("ai_request_log_service.record_local_response : échec de l'enregistrement — ignoré.")


def source_breakdown_for_user(user_id):
    return db.ai_request_log_source_breakdown_for_user(user_id)


def list_for_user(user_id, limit=20):
    """Historique des derniers appels IA de `user_id`, du plus récent au
    plus ancien — [] si aucun appel n'a encore été effectué (jamais None,
    pour que l'appelant puisse itérer sans vérification supplémentaire)."""
    return db.list_ai_request_logs_for_user(user_id, limit=limit)


def stats_for_user(user_id):
    """Statistiques agrégées de `user_id`, calculées EXCLUSIVEMENT sur
    ai_request_logs — None si ce compte n'a encore déclenché aucun appel LLM
    réel (jamais un 0 fabriqué : à l'appelant, admin_user_profile_service.py,
    de traduire ce None en {"available": false, ...})."""
    return db.ai_request_log_stats_for_user(user_id)
