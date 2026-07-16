"""
Construit le dictionnaire de variables réelles ({username}, {accuracy},
{meilleur_chapitre}...) injectées dans les templates de réponse locale
(template_library.py / response_composer.py) — aucune donnée inventée, tout
vient de sources déjà utilisées ailleurs dans le projet : context_builder.py
(profil déjà agrégé pour le prompt LLM), auth.py (historique/paramètres
bruts), progress_service.py (même seuil de maîtrise que tout le site).
"""
from datetime import datetime

import canonical_ids
from auth import read_user_stats, read_user_settings

from .progress_service import is_mastered

NO_DATA = "pas encore assez de données"


def _chapter_stats(history):
    by_chapter = {}
    for h in history:
        # resolve_chapter_id normalise défensivement une variante malformée
        # ("chapitre 1", 1...) vers "Chapitre_N" — identité sans effet sur la
        # valeur déjà canonique stockée normalement par store.js::recordAnswer.
        chapter = canonical_ids.resolve_chapter_id(h.get("chapter")) or h.get("chapter")
        if not chapter:
            continue
        s = by_chapter.setdefault(chapter, {"correct": 0, "total": 0})
        s["total"] += 1
        if h.get("correct"):
            s["correct"] += 1
    return by_chapter


def _best_worst_chapter(by_chapter):
    rated = [(ch, s["correct"] / s["total"]) for ch, s in by_chapter.items() if s["total"] >= 1]
    if not rated:
        return None, None
    rated.sort(key=lambda x: x[1])
    return rated[-1][0], rated[0][0]


def _mastered_and_in_progress_chapters(by_chapter):
    mastered, in_progress = [], []
    for ch, s in by_chapter.items():
        (mastered if is_mastered(s["correct"], s["total"]) else in_progress).append(ch)
    return mastered, in_progress


def _time_totals(history):
    now = datetime.now()
    today = now.date()
    week_start = today.toordinal() - today.weekday()
    total_s = jour_s = semaine_s = 0
    for h in history:
        duration = h.get("duration_s") or 0
        total_s += duration
        ts = h.get("ts")
        if not ts:
            continue
        entry_date = datetime.fromtimestamp(ts / 1000).date()
        if entry_date == today:
            jour_s += duration
        if entry_date.toordinal() >= week_start:
            semaine_s += duration
    return total_s, jour_s, semaine_s


def _format_duration(seconds):
    minutes = int(seconds or 0) // 60
    if minutes < 60:
        return f"{minutes} min"
    hours, rem = divmod(minutes, 60)
    return f"{hours} h {rem:02d}" if rem else f"{hours} h"


def resolve(user, context_summary, chatbot_settings=None, stats=None, settings=None):
    """Dict de variables réelles, prêt pour `str.format_map` dans un
    template. Toujours calculé sur l'historique réel de l'élève
    (`auth.read_user_stats`) — une valeur manquante devient un texte de
    repli honnête (`NO_DATA`), jamais une donnée inventée.

    `stats`/`settings` (optionnels, Student Context Resolver v2, Phase 2) :
    permettent à un appelant qui les a déjà lus une fois (ex.
    student_context_resolver.py, pour éviter de relire deux fois les mêmes
    fichiers JSON dans un même appel) de les injecter directement — comportement
    inchangé si omis (lecture disque comme avant, tous les appelants existants
    ne passent pas ces arguments)."""
    chatbot_settings = chatbot_settings or {}
    context_summary = context_summary or {}
    stats = stats if stats is not None else read_user_stats(user["id"])
    settings = settings if settings is not None else read_user_settings(user["id"])
    history = stats.get("history", [])

    by_chapter = _chapter_stats(history)
    best_chapter, worst_chapter = _best_worst_chapter(by_chapter)
    mastered_chapters, in_progress_chapters = _mastered_and_in_progress_chapters(by_chapter)
    total_s, jour_s, semaine_s = _time_totals(history)
    favorites = settings.get("favorites") or []
    daily_goals = context_summary.get("daily_goals") or {}
    chapters_in_progress = context_summary.get("chapters_in_progress") or []
    accuracy = context_summary.get("accuracy_pct")
    total_touched = len(mastered_chapters) + len(in_progress_chapters)

    return {
        "username": user.get("pseudo") or "l'élève",
        "prenom": user.get("pseudo") or "l'élève",
        "niveau": context_summary.get("level_label", "Intermédiaire"),
        "classe": context_summary.get("level_label", "Intermédiaire"),
        "accuracy": accuracy if accuracy is not None else 0,
        "precision": accuracy if accuracy is not None else 0,
        "chapitres_maitrises": ", ".join(mastered_chapters) if mastered_chapters else "aucun pour l'instant",
        "chapitres_non_maitrises": ", ".join(in_progress_chapters) if in_progress_chapters else "aucun",
        "chapitres_en_cours": ", ".join(chapters_in_progress) if chapters_in_progress else "aucun",
        "favoris": ", ".join(favorites) if favorites else "aucun",
        "temps_total": _format_duration(total_s),
        "temps_jour": _format_duration(jour_s),
        "temps_semaine": _format_duration(semaine_s),
        "serie_actuelle": ", ".join(chapters_in_progress) if chapters_in_progress else "aucune série en cours",
        "dernier_chapitre": chapters_in_progress[0] if chapters_in_progress else "aucun",
        "meilleur_chapitre": best_chapter or NO_DATA,
        "chapitre_le_plus_faible": worst_chapter or NO_DATA,
        "nombre_exercices": context_summary.get("total_exercises", 0),
        "nombre_quiz": len(stats.get("series") or []),
        "score": accuracy if accuracy is not None else 0,
        "progression": round(100 * len(mastered_chapters) / total_touched) if total_touched else 0,
        "objectif": f"{daily_goals.get('done_exercises', 0)}/{daily_goals.get('target_exercises', 0)} exercices",
        "date": datetime.now().strftime("%d/%m/%Y"),
        "heure": datetime.now().strftime("%H:%M"),
        "difficulty": chatbot_settings.get("mode", "professeur"),
        "response_length": chatbot_settings.get("responseLength", "normal"),
        "learning_mode": chatbot_settings.get("mode", "professeur"),
    }
