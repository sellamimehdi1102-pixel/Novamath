"""
Observabilité du pipeline hybride local/LLM (Phase 3B). Deux responsabilités
uniques et séparées :

1. Compteurs en mémoire process-local (comme `chatbot/cache.py` — aucune
   persistance disque, un redémarrage remet à zéro, sans conséquence) :
   nombre de requêtes, réponses locales vs LLM, moteur utilisé, replis,
   erreurs, temps moyen. Voir `record_request()`/`record_response()`/
   `snapshot()`/`reset()`.
2. Mise en forme du mode debug détaillé (`format_debug_trace()`) et du
   journal de comparaison entre la décision du Strategy Engine et le moteur
   qui a RÉELLEMENT répondu (`format_comparison()`) — utilisé par
   `conversation_manager.py` pour journaliser uniquement les divergences
   (Étape 1 de l'intégration progressive), jamais pour modifier la réponse.
"""
import logging
import threading

logger = logging.getLogger("chatbot.pipeline_metrics")
comparison_logger = logging.getLogger("chatbot.pipeline_comparison")

_lock = threading.Lock()


def _initial_stats():
    return {
        "total_requests": 0,
        "local_responses": 0,
        "llm_calls": 0,
        "errors": 0,
        "fallbacks": 0,
        "by_engine": {},
        "total_elapsed_ms": 0.0,
    }


_stats = _initial_stats()


def reset():
    """Remet tous les compteurs à zéro — utilisé par les tests pour repartir
    d'un état connu, jamais nécessaire en usage normal."""
    with _lock:
        _stats.clear()
        _stats.update(_initial_stats())


def record_request():
    with _lock:
        _stats["total_requests"] += 1


def record_response(engine, local, elapsed_ms=0.0, fallback=False, error=False):
    """`engine` : identifiant du moteur qui a RÉELLEMENT répondu (un des
    `response_strategy.ENGINE_*`, ou "legacy_*"/"cache" pour les chemins de
    l'ancien pipeline non encore migrés). `local=False` signifie un appel LLM
    réel."""
    with _lock:
        if local:
            _stats["local_responses"] += 1
        else:
            _stats["llm_calls"] += 1
        if fallback:
            _stats["fallbacks"] += 1
        if error:
            _stats["errors"] += 1
        _stats["by_engine"][engine] = _stats["by_engine"].get(engine, 0) + 1
        _stats["total_elapsed_ms"] += elapsed_ms


def record_error():
    """Erreur qui n'aboutit PAS à une réponse (ex. exception propagée avant
    même de choisir un moteur) — distinct de `record_response(error=True)`,
    qui compte une erreur absorbée ayant tout de même produit une réponse."""
    with _lock:
        _stats["errors"] += 1


def snapshot():
    """Statistiques agrégées, prêtes pour un tableau de bord ou un log —
    jamais d'exception même si aucune requête n'a encore été enregistrée."""
    with _lock:
        total = _stats["total_requests"]
        answered = _stats["local_responses"] + _stats["llm_calls"]
        return {
            "total_requests": total,
            "local_responses": _stats["local_responses"],
            "llm_calls": _stats["llm_calls"],
            "local_response_rate_pct": round(100 * _stats["local_responses"] / total, 1) if total else 0.0,
            "llm_call_rate_pct": round(100 * _stats["llm_calls"] / total, 1) if total else 0.0,
            "fallbacks": _stats["fallbacks"],
            "errors": _stats["errors"],
            "avg_response_time_ms": round(_stats["total_elapsed_ms"] / answered, 3) if answered else 0.0,
            "by_engine": dict(_stats["by_engine"]),
        }


# ── Mode debug / comparaison ─────────────────────────────────────────────────
def format_debug_trace(strategy, engine_used, elapsed_ms, fallback_used=False):
    """Bloc de debug détaillé pour UNE requête — Intent/Strategy/Engine
    choisi/Temps/Fallback/Score, comme demandé. `strategy` peut être `None`
    (Response Strategy Engine désactivé ou en échec) sans jamais lever
    d'exception."""
    if strategy is None:
        return (
            "── Pipeline hybride (debug) ──\n"
            f"Response Strategy Engine : indisponible (désactivé ou en échec)\n"
            f"Moteur exécuté           : {engine_used}\n"
            f"Temps                    : {elapsed_ms:.3f} ms"
        )
    return (
        "── Pipeline hybride (debug) ──\n"
        f"Intent            : {strategy.intent}\n"
        f"Chapitre / Topic  : {strategy.chapter_id} / {strategy.topic_id}\n"
        f"Strategy engine   : {strategy.engine} (confidence={strategy.confidence}/100)\n"
        f"Moteur exécuté    : {engine_used}\n"
        f"Fallback utilisé  : {fallback_used}\n"
        f"Fallback (filet)  : {strategy.fallback}\n"
        f"Temps             : {elapsed_ms:.3f} ms"
    )


def log_comparison(strategy, actual_engine):
    """Étape 1 de l'intégration progressive : compare la décision du Strategy
    Engine (`strategy.engine`, calculée en aparté) avec le moteur qui a
    RÉELLEMENT répondu dans le pipeline actuel — journalise UNIQUEMENT les
    divergences (jamais un log à chaque requête identique, pour rester
    exploitable). Ne modifie jamais la réponse envoyée à l'élève."""
    if strategy is None:
        return
    if strategy.engine != actual_engine:
        comparison_logger.info(
            "Divergence Strategy Engine vs pipeline actuel : décidé=%s, réellement utilisé=%s (intent=%s)",
            strategy.engine, actual_engine, strategy.intent,
        )
