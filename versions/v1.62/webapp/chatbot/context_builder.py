"""
Construit un résumé compact (jamais les données brutes) de la situation
NovaMath de l'élève : niveau, précision, notions faibles, chapitre en cours...
Ce résumé est ce qui est injecté dans le prompt système (voir
prompt_builder.py) — pas l'historique complet ni la banque d'exercices
entière, pour rester proche de l'esprit RAG (contexte minimal) même si le
Phase 1 n'a pas encore de retrieval documentaire.
"""
import canonical_ids
from auth import read_user_stats, read_user_settings, read_user_course_progress

from .services import goals_service, progress_service

LEVEL_LABELS = {1: "Débutant", 2: "Intermédiaire", 3: "Avancé"}


def _stats_by_chapter_notion(history):
    """Regroupe par (chapter, notion) — jamais par notion seule : un même
    texte libre de notion peut désigner deux notions différentes selon le
    chapitre (ex. "Condition de colinéarité" existe identique en Chapitre_4
    ET Chapitre_5, voir static/data/topic_crosswalk.json). Grouper par notion
    seule conflaterait silencieusement leurs statistiques."""
    recent = history[-100:]
    stats = {}
    for h in recent:
        notion = h.get("notion")
        if not notion:
            continue
        key = (h.get("chapter"), notion)
        s = stats.setdefault(key, {"correct": 0, "total": 0})
        s["total"] += 1
        if h.get("correct"):
            s["correct"] += 1
    return stats


def _weak_notions(history, limit=5):
    """Notions avec le plus d'erreurs récentes (100 dernières réponses)."""
    stats = _stats_by_chapter_notion(history)
    weak = [
        (notion, s["correct"] / s["total"])
        for (_chapter, notion), s in stats.items()
        if s["total"] >= 2 and s["correct"] / s["total"] < 0.6
    ]
    weak.sort(key=lambda x: x[1])
    return [n for n, _ in weak[:limit]]


def _weak_topics(history, limit=5):
    """Version canonique de `_weak_notions` : chaque entrée est résolue en
    topic_id exact (canonical_ids.py), scopé par chapitre — consommable
    directement par knowledge_engine.get_notion()/search_service.exercises_by_topic()
    sans repasser par une recherche floue. Une notion dont le texte ne
    résout à aucun topic connu est simplement omise (jamais de topic_id
    inventé)."""
    stats = _stats_by_chapter_notion(history)
    weak = [
        (chapter, notion, s["correct"] / s["total"])
        for (chapter, notion), s in stats.items()
        if s["total"] >= 2 and s["correct"] / s["total"] < 0.6
    ]
    weak.sort(key=lambda x: x[2])
    topics = []
    for chapter, notion, _ratio in weak:
        topic_id = canonical_ids.resolve_topic_id(notion, chapter_id=chapter)
        if topic_id:
            topics.append({"chapter_id": chapter, "topic_id": topic_id, "label": notion})
        if len(topics) >= limit:
            break
    return topics


def _mastered_notions(history, limit=5):
    stats = _stats_by_chapter_notion(history)
    # Règle métier unique (Phase N, progress_service.py) : même seuil que
    # store.js::getChapterStatus — le chatbot ne doit jamais annoncer une
    # notion "maîtrisée" avec un seuil différent du reste du site.
    mastered = [
        notion for (_chapter, notion), s in stats.items()
        if progress_service.is_mastered(s["correct"], s["total"])
    ]
    return mastered[:limit]


def _mastered_topics(history, limit=5):
    """Version canonique de `_mastered_notions` — même principe que
    `_weak_topics` (Student Context Resolver v2, Phase 2) : chaque notion
    maîtrisée résolue en topic_id exact, scopée par chapitre. Absente
    jusqu'ici (asymétrie avec `_weak_topics`), ajoutée pour que le Response
    Engine v2 puisse citer une notion déjà maîtrisée par son topic_id, pas
    seulement par son texte libre."""
    stats = _stats_by_chapter_notion(history)
    topics = []
    for (chapter, notion), s in stats.items():
        if not progress_service.is_mastered(s["correct"], s["total"]):
            continue
        topic_id = canonical_ids.resolve_topic_id(notion, chapter_id=chapter)
        if topic_id:
            topics.append({"chapter_id": chapter, "topic_id": topic_id, "label": notion})
        if len(topics) >= limit:
            break
    return topics


def build_context_summary(user, chapters_summary=None, stats=None, settings=None, course_progress=None):
    """Retourne un dict compact, sérialisable en quelques lignes de texte pour
    le prompt système. `chapters_summary` (optionnel) : liste de dicts
    {id, title} déjà calculée par server.py depuis la banque d'exercices —
    évite de recharger exercises_bank.json ici (paramètre historique,
    actuellement inutilisé dans le corps de cette fonction).

    `stats`/`settings`/`course_progress` (optionnels, Student Context
    Resolver v2, Phase 2) : permettent à un appelant qui les a déjà lus une
    fois (ex. student_context_resolver.py) de les injecter directement —
    comportement inchangé si omis (lecture disque comme avant)."""
    stats = stats if stats is not None else read_user_stats(user["id"])
    settings = settings if settings is not None else read_user_settings(user["id"])
    course_progress = course_progress if course_progress is not None else read_user_course_progress(user["id"])
    history = stats.get("history", [])

    total = len(history)
    correct = sum(1 for h in history if h.get("correct"))
    accuracy = round((correct / total) * 100, 1) if total else None

    in_progress_chapters = []
    for chapter_id, notions in (course_progress or {}).items():
        for notion_id, progress in (notions or {}).items():
            if progress.get("score") is not None:
                in_progress_chapters.append(chapter_id)
                break

    return {
        "pseudo": user.get("pseudo"),
        "level_label": LEVEL_LABELS.get(user.get("level"), "Intermédiaire"),
        "accuracy_pct": accuracy,
        "total_exercises": total,
        "weak_notions": _weak_notions(history),
        "weak_topics": _weak_topics(history),
        "mastered_notions": _mastered_notions(history),
        "mastered_topics": _mastered_topics(history),
        "chapters_in_progress": sorted(set(in_progress_chapters))[:5],
        "language": settings.get("language", "fr"),
        "explanation_level": (settings.get("chatbot") or {}).get("explanationLevel", "auto"),
        # Additif (Phase B) : objectif quotidien, même source que dashboard.js,
        # désormais accessible au prompt système ET à l'accueil personnalisé.
        "daily_goals": goals_service.get_daily_goals_summary(user),
    }


def summary_to_text(summary):
    """Version texte compacte injectée telle quelle dans le prompt système."""
    lines = [
        f"- Niveau estimé : {summary['level_label']}",
    ]
    if summary["accuracy_pct"] is not None:
        lines.append(f"- Précision globale récente : {summary['accuracy_pct']}%")
    if summary["total_exercises"]:
        lines.append(f"- Exercices déjà réalisés : {summary['total_exercises']}")
    if summary["weak_notions"]:
        lines.append(f"- Notions à renforcer en priorité : {', '.join(summary['weak_notions'])}")
    if summary["mastered_notions"]:
        lines.append(f"- Notions déjà maîtrisées : {', '.join(summary['mastered_notions'])}")
    if summary["chapters_in_progress"]:
        lines.append(f"- Chapitres en cours de lecture : {', '.join(summary['chapters_in_progress'])}")
    goals = summary.get("daily_goals")
    if goals:
        lines.append(
            f"- Objectif du jour : {goals['done_exercises']}/{goals['target_exercises']} exercices"
            f"{' (déjà atteint)' if goals['reached'] else ''}"
            + (f" — série de {goals['streak_days']} jour(s) consécutifs" if goals["streak_days"] else "")
        )
    return "\n".join(lines) if lines else "- Aucune donnée de progression disponible pour le moment."
