"""
Tableau de bord développeur — Phase 4, Mission 8.

Agrège en UNE lecture toutes les métriques déjà collectées par les modules
d'observabilité de ce chantier — n'ajoute aucune nouvelle collecte, ne
modifie aucune donnée, ne fait aucun calcul dupliqué (chaque nombre vient
d'un seul module responsable). Conçu pour être exposé par une route Flask
réservée au développement (voir `server.py`, `ENABLE_DEV_DASHBOARD`), mais
utilisable aussi en ligne de commande/notebook sans serveur.
"""
import random

from . import diversity_audit, knowledge_audit, llm_call_analytics, pipeline_metrics, response_quality, ux_analytics


def snapshot(quality_sample_size=20):
    """Snapshot complet. `quality_sample_size` : nombre de compositions
    simulées pour estimer une qualité moyenne (Mission 5) — voir
    `_sample_quality_score`, jamais calculé sur des réponses réellement
    envoyées à un élève (ce module ne lit aucune conversation)."""
    pipeline = pipeline_metrics.snapshot()
    llm_analytics = llm_call_analytics.snapshot()
    knowledge = knowledge_audit.audit_all()
    diversity = diversity_audit.simulate_usage(n=100)
    ux = ux_analytics.report()
    quality = _sample_quality_score(quality_sample_size)

    return {
        "pipeline": pipeline,
        "llm_call_reasons": llm_analytics["by_reason"],
        "knowledge_coverage": {
            "project_score_global": knowledge["project_score_global"],
            "total_chapters": knowledge["total_chapters"],
            "total_notions": knowledge["total_notions"],
        },
        "diversity_pools_below_threshold": [
            name for name, stats in diversity.items() if stats["diversity_ratio"] < 0.5
        ],
        "response_quality_estimate": quality,
        "ux": ux,
    }


def _sample_quality_score(n):
    """Estime une qualité moyenne (Mission 5) en composant `n` réponses sur
    une notion réelle connue (Chapitre_1/puissances-entieres-relatives, déjà
    utilisée par les suites de tests du projet) avec des intents variés —
    un échantillon représentatif, pas une mesure sur du trafic réel (ce
    module n'a pas accès aux réponses effectivement envoyées)."""
    from .. import knowledge_engine
    from . import intent_service, knowledge_response_composer, response_strategy

    sample_intents = [
        intent_service.DEFINITION, intent_service.METHODE, intent_service.EXEMPLE,
        intent_service.FORMULE, intent_service.COURS,
    ]
    rng = random.Random(7)
    scores = []
    for intent in sample_intents:
        strategy = response_strategy._build_strategy(  # noqa: SLF001 (module interne, usage diagnostique)
            response_strategy.ENGINE_KNOWLEDGE, intent, "Chapitre_1", "puissances-entieres-relatives",
            None, None, None, {}, {},
        )
        draft = knowledge_response_composer.compose(strategy, student_context={}, rng=rng)
        scores.append(response_quality.score_draft(draft)["score_global"])
    return {
        "sample_size": len(scores),
        "avg_score": round(sum(scores) / len(scores), 1) if scores else 0.0,
        "min_score": min(scores) if scores else 0.0,
        "max_score": max(scores) if scores else 0.0,
    }


def format_report(quality_sample_size=20):
    data = snapshot(quality_sample_size)
    p = data["pipeline"]
    lines = [
        "=== Tableau de bord développeur NovaMath ===",
        f"Requêtes totales        : {p['total_requests']}",
        f"Réponses locales        : {p['local_responses']} ({p['local_response_rate_pct']}%)",
        f"Appels LLM              : {p['llm_calls']} ({p['llm_call_rate_pct']}%)",
        f"Temps moyen             : {p['avg_response_time_ms']} ms",
        f"Fallbacks               : {p['fallbacks']} | Erreurs : {p['errors']}",
        f"Moteur utilisé (compte) : {p['by_engine']}",
        "",
        f"Raisons des appels LLM  : {data['llm_call_reasons']}",
        "",
        f"Couverture Knowledge Engine : {data['knowledge_coverage']['project_score_global']}% "
        f"({data['knowledge_coverage']['total_notions']} notions, {data['knowledge_coverage']['total_chapters']} chapitres)",
        f"Pools de formulation à enrichir : {data['diversity_pools_below_threshold']}",
        f"Qualité moyenne estimée : {data['response_quality_estimate']['avg_score']}/100 "
        f"(échantillon de {data['response_quality_estimate']['sample_size']})",
        "",
        f"Messages incompris : {data['ux']['messages_incompris']}",
    ]
    return "\n".join(lines)
