"""
Métriques applicatives NovaMath.

Architecture stricte, identique à plan_service.py/quota_service.py/
rate_limit_service.py :

    server.py / logging_service.py  →  metrics_service.py  →  db.py

jamais l'inverse. Deux sources combinées dans snapshot(), jamais mélangées :

1. Compteurs en mémoire process-local (record_request/record_error),
   incrémentés par le middleware HTTP de logging_service.init_app() à
   CHAQUE requête — même technique que
   chatbot/services/pipeline_metrics.py (dict + threading.Lock, une
   opération O(1) sous verrou, aucun impact mesurable sur la latence :
   jamais d'écriture disque ni de requête réseau ici). Remis à zéro à
   chaque redémarrage du process, sans conséquence (comme pipeline_metrics).

2. Compteurs persistés, dérivés de tables DÉJÀ existantes et déjà tenues à
   jour par d'autres modules pour d'autres raisons (traçabilité) :
   db.count_users() (table users), db.count_conversations() (table
   conversations), db.count_security_events(...) (table security_events,
   déjà alimentée par auth.py::_log_security_event et
   stripe_webhook_service.py pour les connexions/inscriptions/paiements).
   Lus uniquement à la demande (snapshot()), jamais sur le chemin d'une
   requête normale — aucune duplication de compteur, aucune nouvelle
   écriture introduite par ce module.
"""
import threading

import db

_lock = threading.Lock()


def _initial_stats():
    return {"total_requests": 0, "total_errors": 0, "total_duration_ms": 0.0}


_stats = _initial_stats()


def reset():
    """Remet les compteurs en mémoire à zéro — tests uniquement, jamais
    nécessaire en usage normal (même convention que
    chatbot/services/pipeline_metrics.py::reset())."""
    with _lock:
        _stats.clear()
        _stats.update(_initial_stats())


def record_request(duration_ms):
    """Appelée une fois par requête HTTP par logging_service.init_app()."""
    with _lock:
        _stats["total_requests"] += 1
        _stats["total_duration_ms"] += duration_ms


def record_error():
    """Appelée pour toute réponse 5xx ou exception non gérée (voir
    logging_service.init_app()) — distincte des erreurs 4xx (attendues,
    jamais comptées comme une panne du serveur)."""
    with _lock:
        _stats["total_errors"] += 1


def in_memory_snapshot():
    """Uniquement les compteurs process-local (voir docstring du module,
    source 1) — utilisé isolément par les tests, et composé dans snapshot()."""
    with _lock:
        total = _stats["total_requests"]
        return {
            "total_requests": total,
            "total_errors": _stats["total_errors"],
            "avg_request_duration_ms": round(_stats["total_duration_ms"] / total, 2) if total else 0.0,
        }


def snapshot():
    """Instantané complet (compteurs process-local + compteurs persistés) —
    jamais d'exception, y compris sur une base tout juste initialisée (tous
    les compteurs persistés valent alors 0, voir les fonctions db.count_*)."""
    persisted = {
        "users": db.count_users(),
        "conversations": db.count_conversations(),
        "logins": db.count_security_events("login_success"),
        "registrations": db.count_security_events("account_created"),
        # Un paiement réussi peut être journalisé par l'un ou l'autre de ces
        # deux événements Stripe selon le flux (premier paiement via Checkout
        # vs renouvellement d'abonnement via une facture) — voir
        # stripe_webhook_service.py::_handle_checkout_session_completed/
        # _handle_invoice_paid, jamais les deux pour le même paiement.
        "payments": (
            db.count_security_events("stripe_checkout_completed")
            + db.count_security_events("stripe_invoice_paid")
        ),
    }
    return {**persisted, **in_memory_snapshot()}
