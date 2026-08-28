"""
Analyse des appels LLM — Phase 4, Missions 3 & 4.

Mission 3 : journalise (mémoire process, comme `pipeline_metrics.py`) chaque
décision qui aboutit réellement à un appel LLM — question, intent, moteur
décidé, ET une RAISON classée automatiquement (voir `classify_reason`). Pur
outil d'observabilité : n'influence jamais la réponse envoyée à l'élève,
appelé par `conversation_manager.py` uniquement à l'endroit où l'appel LLM
est déjà décidé (voir ENABLE_LLM_CALL_ANALYTICS).

Mission 4 : pour un enregistrement donné, cherche AUTOMATIQUEMENT s'il existe
une donnée locale proche (notion, exercice, définition) qui aurait pu
répondre — et propose une amélioration textuelle (jamais une modification
automatique des fichiers de cours : voir `suggest_reduction`, qui ne fait que
recommander, en lecture seule, comme `knowledge_audit.py`).
"""
import threading
from collections import OrderedDict, defaultdict

from .. import knowledge_engine
from . import intent_service, response_strategy, search_service

_lock = threading.Lock()
_MAX_RECORDS = 500
_records = OrderedDict()  # insertion order = ordre chronologique, borné

# ── Raisons classées (Mission 3) ─────────────────────────────────────────────
REASON_NOTION_ABSENTE = "notion absente"
REASON_DEMONSTRATION_ABSENTE = "démonstration absente"
REASON_PROPRIETE_ABSENTE = "propriété absente"
REASON_HORS_PROGRAMME = "question hors programme"
REASON_PROBLEME_ROUTAGE = "problème de routage"
REASON_MAUVAISE_DETECTION_INTENTION = "mauvaise détection d'intention"
REASON_CONFIANCE_INSUFFISANTE = "score de confiance insuffisant"
REASON_INTENT_SANS_MOTEUR_LOCAL = "intent reconnu sans moteur local (ex. quiz/correction)"

CONFIDENCE_THRESHOLD = 40
_NO_LOCAL_ENGINE_INTENTS = {
    intent_service.QUIZ, intent_service.CORRECTION, intent_service.FICHE, intent_service.RESTART_BASICS,
}


def classify_reason(strategy, allowed_engines=None):
    """Classe automatiquement la raison d'un appel LLM à partir de la
    `ResponseStrategy` déjà décidée (jamais une nouvelle heuristique de
    correspondance — uniquement une lecture des champs déjà calculés).
    `strategy=None` (Strategy Engine désactivé/en échec) -> "problème de
    routage" (on ne sait littéralement pas pourquoi)."""
    if strategy is None:
        return REASON_PROBLEME_ROUTAGE
    if strategy.intent == intent_service.UNCLEAR:
        return REASON_PROBLEME_ROUTAGE  # ne devrait jamais arriver ici (court-circuité avant), gardé par sûreté
    if strategy.confidence < CONFIDENCE_THRESHOLD:
        return REASON_CONFIANCE_INSUFFISANTE
    if strategy.intent == intent_service.DEMONSTRATION:
        return REASON_DEMONSTRATION_ABSENTE
    if strategy.intent == intent_service.PROPRIETE:
        return REASON_PROPRIETE_ABSENTE
    if strategy.intent in _NO_LOCAL_ENGINE_INTENTS:
        return REASON_INTENT_SANS_MOTEUR_LOCAL
    if not strategy.chapter_id and not strategy.topic_id:
        return REASON_HORS_PROGRAMME
    if strategy.intent == intent_service.NONE_INTENT:
        return REASON_MAUVAISE_DETECTION_INTENTION
    if allowed_engines is not None and strategy.engine in (
        response_strategy.ENGINE_KNOWLEDGE, response_strategy.ENGINE_SEARCH,
        response_strategy.ENGINE_DASHBOARD, response_strategy.ENGINE_EXERCISE,
    ) and strategy.engine not in allowed_engines:
        return REASON_PROBLEME_ROUTAGE  # moteur capable, mais pas encore déployé (voir conversation_manager.py)
    return REASON_NOTION_ABSENTE


def record(user_message, strategy, allowed_engines=None):
    """Journalise un appel LLM réel (Mission 3). Ne lève jamais d'exception —
    un échec de journalisation ne doit jamais faire échouer une réponse."""
    try:
        reason = classify_reason(strategy, allowed_engines)
        with _lock:
            _records[len(_records)] = {
                "message": (user_message or "")[:200],
                "intent": strategy.intent if strategy else None,
                "chapter_id": strategy.chapter_id if strategy else None,
                "topic_id": strategy.topic_id if strategy else None,
                "confidence": strategy.confidence if strategy else None,
                "reason": reason,
            }
            if len(_records) > _MAX_RECORDS:
                _records.popitem(last=False)
    except Exception:
        pass


def reset():
    with _lock:
        _records.clear()


def snapshot():
    """Statistiques agrégées par raison (Mission 3)."""
    with _lock:
        records = list(_records.values())
    by_reason = defaultdict(int)
    for rec in records:
        by_reason[rec["reason"]] += 1
    return {
        "total_llm_calls_logged": len(records),
        "by_reason": dict(by_reason),
        "recent": records[-20:],
    }


# ── Mission 4 : suggestions automatiques de réduction ───────────────────────
FUZZY_SEARCH_THRESHOLD = 0.05  # nettement sous TFIDF_WEAK_THRESHOLD (0.12) — exploratoire, jamais utilisé pour répondre


def suggest_reduction(rec):
    """Pour UN enregistrement (dict renvoyé par `snapshot()["recent"]` ou
    équivalent), cherche s'il existe une donnée locale proche qui aurait pu
    éviter l'appel LLM. Renvoie une suggestion textuelle, JAMAIS une
    modification automatique d'un fichier de cours — la décision de
    l'appliquer reste humaine."""
    message = rec.get("message") or ""
    reason = rec.get("reason")

    if reason == REASON_HORS_PROGRAMME:
        matches = search_service.search(message, scope=[search_service.SCOPE_COURS], limit=1)
        if matches and matches[0]["score"] >= FUZZY_SEARCH_THRESHOLD:
            m = matches[0]
            return (
                f"Un match faible existe (« {m['title']} », score {m['score']:.2f}, "
                f"sous le seuil de confiance {search_service.TFIDF_WEAK_THRESHOLD}) — "
                "envisager d'ajouter les mots de la question comme synonyme dans "
                "static/data/topic_crosswalk.json plutôt que d'abaisser le seuil global."
            )
        return "Aucune notion proche trouvée — question probablement réellement hors programme."

    if reason in (REASON_DEMONSTRATION_ABSENTE, REASON_PROPRIETE_ABSENTE) and rec.get("chapter_id") and rec.get("topic_id"):
        notion = knowledge_engine.get_notion(rec["chapter_id"], rec["topic_id"])
        if notion:
            champ = "preuve d'une propriété" if reason == REASON_DEMONSTRATION_ABSENTE else "propriété structurée"
            return (
                f"La notion « {notion['title']} » existe mais n'a pas encore de {champ} curée "
                "(knowledge_engine.get_proprietes) — ajouter ce contenu résoudrait cet appel LLM "
                "et tous les suivants sur la même notion."
            )
        return "Chapitre/topic résolus mais notion introuvable — vérifier canonical_ids.py."

    if reason == REASON_NOTION_ABSENTE and rec.get("chapter_id"):
        exercices = search_service.exercises_by_topic(rec["chapter_id"], rec.get("topic_id"), limit=1) if rec.get("topic_id") else []
        if exercices:
            return (
                f"Un exercice existe déjà pour ce chapitre/topic — la question portait probablement "
                "sur un format de réponse non couvert (ex. méthode/propriété manquante, voir Mission 1)."
            )
        return "Chapitre identifié mais contenu insuffisant pour répondre localement — candidat à enrichir en priorité."

    if reason == REASON_MAUVAISE_DETECTION_INTENTION:
        return (
            "Un chapitre/topic a été trouvé mais aucun intent n'a été reconnu — la formulation "
            "n'est proche d'aucune phrase déclencheuse connue (voir intent_service._FUZZY_TRIGGER_PHRASES) : "
            "candidat à ajouter comme nouvelle phrase déclenchrice."
        )

    if reason == REASON_CONFIANCE_INSUFFISANTE:
        return "Décision locale trouvée mais peu fiable (score sous le seuil) — vérifier manuellement avant d'automatiser."

    if reason == REASON_INTENT_SANS_MOTEUR_LOCAL:
        return f"Intent « {rec.get('intent')} » reconnu mais aucun moteur local ne le traite encore (hors périmètre actuel)."

    return "Moteur capable identifié mais pas encore déployé dans LOCAL_RESPONSE_ENGINE_ALLOWED_ENGINES."


def suggest_reductions(limit=20):
    """Mission 4, vue d'ensemble : une suggestion par enregistrement récent."""
    with _lock:
        records = list(_records.values())[-limit:]
    return [{"record": rec, "suggestion": suggest_reduction(rec)} for rec in records]
