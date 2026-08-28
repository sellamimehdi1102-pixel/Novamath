"""
Agrège l'objectif quotidien de l'élève côté backend — même logique que
webapp/static/js/dashboard.js::renderDailyGoal et webapp/static/js/store.js
::computeStreak, portée en Python pour que le chatbot (et toute future route)
puisse s'appuyer sur une seule source de vérité au lieu de recalculer côté
frontend uniquement. Aucune nouvelle donnée : lit exactement ce que
lisent déjà read_user_settings/read_user_stats.
"""
from datetime import date, datetime

from auth import read_user_settings, read_user_stats


def _today_str():
    return date.today().isoformat()


def _compute_streak(history):
    """Nombre de jours consécutifs (aujourd'hui ou hier inclus) avec au moins
    un exercice fait — même règle que store.js::computeStreak."""
    days = sorted({h.get("date") for h in history if h.get("date")}, reverse=True)
    if not days:
        return 0
    streak = 0
    cursor = date.today()
    for day_str in days:
        try:
            day = datetime.strptime(day_str, "%Y-%m-%d").date()
        except ValueError:
            continue
        diff = (cursor - day).days
        if diff in (0, 1):
            streak += 1
            cursor = day
        else:
            break
    return streak


def get_daily_goals_summary(user):
    stats = read_user_stats(user["id"])
    settings = read_user_settings(user["id"])
    history = stats.get("history", [])

    target_exercises = max(1, int((settings.get("learning") or {}).get("dailyGoalExercises") or 10))
    today = _today_str()
    done_exercises = sum(1 for h in history if h.get("date") == today)
    progress_pct = min(100, round((done_exercises / target_exercises) * 100))

    return {
        "target_exercises": target_exercises,
        "done_exercises": done_exercises,
        "remaining_exercises": max(0, target_exercises - done_exercises),
        "progress_pct": progress_pct,
        "reached": done_exercises >= target_exercises,
        "streak_days": _compute_streak(history),
    }
