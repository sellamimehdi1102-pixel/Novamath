"""
Construit un résumé compact (jamais les données brutes) de la situation
NovaMath de l'élève : niveau, précision, notions faibles, chapitre en cours...
Ce résumé est ce qui est injecté dans le prompt système (voir
prompt_builder.py) — pas l'historique complet ni la banque d'exercices
entière, pour rester proche de l'esprit RAG (contexte minimal) même si le
Phase 1 n'a pas encore de retrieval documentaire.
"""
from auth import read_user_stats, read_user_settings, read_user_course_progress

LEVEL_LABELS = {1: "Débutant", 2: "Intermédiaire", 3: "Avancé"}


def _weak_notions(history, limit=5):
    """Notions avec le plus d'erreurs récentes (100 dernières réponses)."""
    recent = history[-100:]
    stats_by_notion = {}
    for h in recent:
        notion = h.get("notion")
        if not notion:
            continue
        s = stats_by_notion.setdefault(notion, {"correct": 0, "total": 0})
        s["total"] += 1
        if h.get("correct"):
            s["correct"] += 1
    weak = [
        (notion, s["correct"] / s["total"])
        for notion, s in stats_by_notion.items()
        if s["total"] >= 2 and s["correct"] / s["total"] < 0.6
    ]
    weak.sort(key=lambda x: x[1])
    return [n for n, _ in weak[:limit]]


def _mastered_notions(history, limit=5):
    recent = history[-100:]
    stats_by_notion = {}
    for h in recent:
        notion = h.get("notion")
        if not notion:
            continue
        s = stats_by_notion.setdefault(notion, {"correct": 0, "total": 0})
        s["total"] += 1
        if h.get("correct"):
            s["correct"] += 1
    mastered = [
        notion for notion, s in stats_by_notion.items()
        if s["total"] >= 2 and s["correct"] / s["total"] >= 0.85
    ]
    return mastered[:limit]


def build_context_summary(user, chapters_summary=None):
    """Retourne un dict compact, sérialisable en quelques lignes de texte pour
    le prompt système. `chapters_summary` (optionnel) : liste de dicts
    {id, title} déjà calculée par server.py depuis la banque d'exercices —
    évite de recharger exercises_bank.json ici."""
    stats = read_user_stats(user["id"])
    settings = read_user_settings(user["id"])
    course_progress = read_user_course_progress(user["id"])
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
        "level_label": LEVEL_LABELS.get(user.get("level"), "Intermédiaire"),
        "accuracy_pct": accuracy,
        "total_exercises": total,
        "weak_notions": _weak_notions(history),
        "mastered_notions": _mastered_notions(history),
        "chapters_in_progress": sorted(set(in_progress_chapters))[:5],
        "language": settings.get("language", "fr"),
        "explanation_level": (settings.get("chatbot") or {}).get("explanationLevel", "auto"),
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
    return "\n".join(lines) if lines else "- Aucune donnée de progression disponible pour le moment."
