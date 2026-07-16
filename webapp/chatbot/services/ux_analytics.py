"""
Expérience utilisateur — Phase 4, Mission 7.

IMPORTANT (honnêteté du périmètre, voir rapport de phase) : plusieurs
mesures demandées par le cahier des charges nécessitent une instrumentation
qui N'EXISTE PAS aujourd'hui côté serveur ni côté client (temps de session
réel, clics, réponses abandonnées, fonctionnalités inutilisées) — ce module
ne les invente pas. Il expose UNIQUEMENT ce qui est réellement mesurable à
partir des données déjà collectées (`pipeline_metrics.py`,
`llm_call_analytics.py`) et documente explicitement le reste comme un manque
d'instrumentation, pas un chiffre à zéro qui laisserait croire à une mesure.
"""
from . import llm_call_analytics, pipeline_metrics

# Mesures demandées mais non instrumentées aujourd'hui — voir docstring.
NOT_YET_MEASURABLE = (
    "temps_moyen_session", "nombre_de_clics", "reponses_abandonnees", "fonctionnalites_inutilisees",
)


def messages_incompris():
    """Proportion de tours ayant déclenché la clarification (charabia détecté,
    voir intent_service._is_gibberish) — seule mesure fiable de "message
    incompris" avec les données actuellement collectées."""
    stats = pipeline_metrics.snapshot()
    total = stats["total_requests"] or 1
    count = stats["by_engine"].get("clarification", 0)
    return {"count": count, "pct_of_total": round(100 * count / total, 1)}


def chapitres_evoques_par_les_appels_llm():
    """Chapitres associés aux questions qui ont fini par appeler le LLM
    (`llm_call_analytics`) — un signal partiel mais réel : un chapitre qui
    revient souvent ici est soit très demandé, soit mal couvert localement
    (voir `knowledge_audit.py`/`llm_call_analytics.suggest_reduction`)."""
    records = llm_call_analytics.snapshot()["recent"]
    counts = {}
    for rec in records:
        chapter_id = rec.get("chapter_id")
        if chapter_id:
            counts[chapter_id] = counts.get(chapter_id, 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: kv[1], reverse=True))


def report():
    """Rapport Mission 7 — mesurable aujourd'hui + rappel explicite de ce qui
    ne l'est pas, pour ne jamais laisser croire à une mesure inexistante."""
    return {
        "messages_incompris": messages_incompris(),
        "chapitres_evoques_par_les_appels_llm": chapitres_evoques_par_les_appels_llm(),
        "non_mesurable_avec_les_donnees_actuelles": list(NOT_YET_MEASURABLE),
        "recommandation": (
            "Ajouter une instrumentation front-end (événements de clic, durée de "
            "session, détection d'abandon) pour couvrir les mesures listées dans "
            "non_mesurable_avec_les_donnees_actuelles — hors périmètre de cette phase "
            "(aucune modification du frontend n'a été demandée)."
        ),
    }
