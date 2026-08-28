"""
Service pour le module "Analytics" (/admin/analytics) — vue d'ensemble
filtrable par période (cartes KPI), graphiques (Chart.js, séries journalières
réelles) et classements ("Top X"). Les exports (CSV/Excel/PDF) et un
éventuel système de rapports planifiés restent un chantier ultérieur,
volontairement absents ici.

Architecture stricte, identique au reste du projet :

    server.py  →  admin_analytics_service.py  →  {db, support_service,
                   admin_users_service, ai_provider_service}.py

jamais l'inverse. Ce module NE modifie JAMAIS le chatbot, Stripe, les
abonnements, les quotas ni le routage IA — il ne fait qu'agréger en LECTURE
des compteurs déjà existants (voir db.py) sur une période demandée.

── Anti-duplication (voir les deux explorations préalables) ────────────────
Toutes les requêtes de comptage déjà filtrables par date (count_users_*_since,
count_conversations_since, count_messages_since, count_security_events_since,
users_registered_per_day, conversations_created_per_day,
support_tickets_count_by_day) ont été ÉTENDUES dans db.py avec un paramètre
optionnel `until_iso=None` (comportement inchangé pour tout appelant existant
qui ne le passe pas — Dashboard/Support continuent de fonctionner à
l'identique). Les graphiques "IA par jour" (tokens/coût/appels/latence/
succès/fallbacks) réutilisent UNE SEULE requête mutualisée
(`ai_provider_usage_daily_totals`, sur la table `ai_provider_usage` déjà
alimentée par le chatbot réel) plutôt que six requêtes séparées — voir sa
docstring dans db.py. Seules les requêtes qui n'avaient structurellement
aucun équivalent ont été ajoutées (voir docstrings dans db.py de chacune).

── Politique "aucune donnée inventée" ──────────────────────────────────────
{"available": False, "value": None, "reason": "..."} pour tout ce qui ne
peut pas être calculé sur la période demandée. Certaines valeurs (répartition
Free/Premium/Ultra, tickets ouverts/fermés, catégories/priorités support)
sont des ÉTATS ACTUELS — aucun historique par date n'existe pour elles (voir
docstring de count_users_by_plan()/support_tickets_overview_stats() dans
db.py) : elles sont renvoyées `available: True` avec un champ `note`
expliquant clairement qu'elles ne sont PAS filtrées par la période
sélectionnée, jamais masquées ni fabriquées pour donner l'illusion d'un
filtre qui n'existe pas.

── Chantier de simplification (page Analytics) ─────────────────────────────
La page Analytics est un pur outil de tendances/comparaisons : les cartes
KPI de comptage brut (utilisateurs/chatbot/IA/abonnements/support) et le
camembert de répartition des abonnements ont été retirés du rendu frontend
(doublons du Dashboard/module Support déjà simplifiés) — overview() continue
de les calculer car ils restent utilisés par le tableau de bord personnalisé
("cartes KPI épinglées", voir PINNABLE_KPIS). Le bloc "Pédagogie" (jamais
alimenté, aucune table SQL agrégable — voir l'ancienne constante
_PEDAGOGY_UNAVAILABLE_REASON) et le doublon "temps moyen de
réponse/résolution" (déjà affiché par le module Support) ont été supprimés
de rankings(), qui ne renvoie plus que les classements réels (Top X).

── Fusion de l'ancien groupe "Système" dans "IA" ────────────────────────────
Un groupe KPI/graphique "Système" existait avec 3 champs : availability_pct
(doublon EXACT de ai.success_rate_pct — même calcul, même série, jamais
recalculé séparément, voir git history), errors (compte d'erreurs IA, sans
lien avec l'infrastructure — la page Santé couvre déjà uptime/DB/sauvegardes/
fournisseurs down) et fallbacks (idem, données IA). Le doublon a été
supprimé, errors/fallbacks ont été déplacés dans le groupe "ai" (ils
mesurent tous les deux ai_provider_usage/ai_provider_fallback_events) —
"Système" comme groupe séparé n'avait donc plus de raison d'exister.
"""
import json
from datetime import datetime, timedelta, timezone

import admin_users_service
import ai_provider_service as ai_svc
import backup_service
import db
import support_service

# Seuil minimal d'échantillon avant d'afficher un taux de disponibilité/succès
# — même politique que system_health_service.py (éviter un "100%"/"0%"
# trompeur calculé sur une poignée d'appels).
_MIN_SAMPLES_FOR_RATE = 5

WINDOW_CHOICES = ("aujourd_hui", "hier", "7j", "30j", "90j", "cette_annee", "tout", "personnalise")
WINDOW_LABELS = {
    "aujourd_hui": "Aujourd'hui", "hier": "Hier", "7j": "7 jours", "30j": "30 jours",
    "90j": "90 jours", "cette_annee": "Cette année", "tout": "Tout", "personnalise": "Personnalisé",
}
_EPOCH_ISO = "1970-01-01T00:00:00+00:00"


def _na(reason):
    return {"available": False, "value": None, "reason": reason}


def _ok(value, note=None):
    result = {"available": True, "value": value}
    if note:
        result["note"] = note
    return result


def _now():
    return datetime.now(timezone.utc)


def _day_start(dt):
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)


def _parse_custom_bound(value, end_of_day=False):
    """`value` : "YYYY-MM-DD" (voir <input type="date">) — même convention
    que admin_ai_log_service._clean_filters pour date_to (borne haute
    incluse jusqu'à 23:59:59). None si absent/invalide."""
    if not value:
        return None
    try:
        dt = datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return None
    return dt.replace(hour=23, minute=59, second=59, microsecond=999999) if end_of_day else dt


def resolve_window(window, date_from=None, date_to=None):
    """(window, since_iso, until_iso, error) — `window` normalisé (retombe
    sur "30j" si la valeur reçue est inconnue), `until_iso` reste None quand
    la fenêtre n'a pas de borne haute (toutes sauf "hier"/"personnalisé").
    `error` non-None uniquement pour "personnalisé" avec des dates
    manquantes/invalides (rejeté par la route en 400, jamais silencieusement
    retombé sur une autre fenêtre)."""
    now = _now()
    if window not in WINDOW_CHOICES:
        window = "30j"

    if window == "aujourd_hui":
        return window, _day_start(now).isoformat(), None, None
    if window == "hier":
        start_today = _day_start(now)
        return window, (start_today - timedelta(days=1)).isoformat(), start_today.isoformat(), None
    if window == "7j":
        return window, (now - timedelta(days=7)).isoformat(), None, None
    if window == "30j":
        return window, (now - timedelta(days=30)).isoformat(), None, None
    if window == "90j":
        return window, (now - timedelta(days=90)).isoformat(), None, None
    if window == "cette_annee":
        return window, now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0).isoformat(), None, None
    if window == "tout":
        return window, _EPOCH_ISO, None, None
    # "personnalise"
    since_dt = _parse_custom_bound(date_from)
    until_dt = _parse_custom_bound(date_to, end_of_day=True)
    if since_dt is None or until_dt is None:
        return window, None, None, "Filtre personnalisé : date_from et date_to (YYYY-MM-DD) sont obligatoires."
    if since_dt > until_dt:
        return window, None, None, "Filtre personnalisé : date_from doit être antérieure à date_to."
    return window, since_dt.isoformat(), until_dt.isoformat(), None


def list_filters():
    """GET /api/admin/analytics/filters — options réellement proposées,
    jamais devinées côté frontend (même politique que admin_nav_service.py
    pour le menu : le frontend affiche ce qui lui est transmis, rien de plus)."""
    return {
        "windows": [{"value": key, "label": WINDOW_LABELS[key]} for key in WINDOW_CHOICES],
        "default": "30j",
    }


# ── KPI Utilisateurs ─────────────────────────────────────────────────────────
def _users_kpis(since_iso, until_iso):
    return {
        "total_registered": _ok(db.count_users(), note="Total actuel, tous comptes confondus (non filtré par la période)."),
        "new_users": _ok(db.count_users_created_since(since_iso, until_iso)),
        "active_users": _ok(db.count_users_active_since(since_iso, until_iso)),
        "logins": _ok(db.count_security_events_since("login_success", since_iso, until_iso)),
    }


# ── KPI Chatbot ───────────────────────────────────────────────────────────────
def _chatbot_kpis(since_iso, until_iso):
    return {
        "conversations": _ok(db.count_conversations_since(since_iso, until_iso)),
        "user_messages": _ok(db.count_messages_by_role_since("user", since_iso, until_iso)),
        "assistant_messages": _ok(db.count_messages_by_role_since("assistant", since_iso, until_iso)),
    }


# ── KPI IA ────────────────────────────────────────────────────────────────────
_NO_AI_CALLS_REASON = "Aucun appel IA réel enregistré sur cette période (table ai_request_logs)."


def _ai_kpis(since_iso, until_iso):
    stats = db.ai_request_logs_stats_since(since_iso, until_iso)
    fallback_count = db.count_ai_provider_fallback_events_since(since_iso, until_iso)
    if stats is None:
        return {
            "calls": _na(_NO_AI_CALLS_REASON), "tokens": _na(_NO_AI_CALLS_REASON),
            "cost_usd": _na(_NO_AI_CALLS_REASON), "avg_latency_ms": _na(_NO_AI_CALLS_REASON),
            "success_rate_pct": _na(_NO_AI_CALLS_REASON), "errors": _na(_NO_AI_CALLS_REASON),
            "fallbacks": _ok(fallback_count),
        }, stats
    requests = stats["requests"]
    success_rate = (
        _ok(round(stats["success_count"] / requests * 100, 1))
        if requests >= _MIN_SAMPLES_FOR_RATE else
        _na(f"Échantillon trop faible ({requests} appel(s), {_MIN_SAMPLES_FOR_RATE} minimum) pour un taux fiable.")
    )
    return {
        "calls": _ok(requests, note=f"dont {stats['real_requests']} réel(s) / {stats['estimated_requests']} estimé(s)."),
        "tokens": _ok(stats["total_tokens"] or 0),
        "cost_usd": _ok(round(stats["estimated_cost"] or 0, 4), note="Coût réel Gemini/Claude uniquement — le moteur local/cache reste à 0 (aucune dépense externe)."),
        "avg_latency_ms": _ok(round(stats["avg_response_time_ms"])) if stats["avg_response_time_ms"] is not None else _na(_NO_AI_CALLS_REASON),
        "success_rate_pct": success_rate,
        "errors": _ok(stats["error_count"]),
        "fallbacks": _ok(fallback_count),
    }, stats


# ── KPI Support ────────────────────────────────────────────────────────────────
def _support_kpis(since_iso, until_iso):
    overview = support_service.overview_stats()
    tickets_in_period = db.count_support_tickets_created_since(since_iso, until_iso)
    return {
        "tickets_created": _ok(tickets_in_period),
        "open": _ok(overview["open_count"], note="État actuel (non filtré par la période sélectionnée)."),
        "closed": _ok(overview["closed_count"], note="État actuel (non filtré par la période sélectionnée)."),
    }


# ── KPI Abonnements ────────────────────────────────────────────────────────────
def _subscriptions_kpis():
    by_plan = db.count_users_by_plan()
    note = "État actuel des comptes (non filtré par la période sélectionnée) — aucun historique des changements de plan n'est stocké au-delà des événements Stripe déjà exploités par le module Abonnements."
    return {
        "free": _ok(by_plan.get("free", 0), note=note),
        "premium": _ok(by_plan.get("premium", 0), note=note),
        "ultra": _ok(by_plan.get("ultra", 0), note=note),
    }


def _window_payload(window, since_iso, until_iso):
    """Bloc "window" commun aux trois routes (overview/charts/rankings) —
    une seule fonction, jamais un dict recopié trois fois."""
    return {"value": window, "label": WINDOW_LABELS[window], "since": since_iso, "until": until_iso}


_OVERVIEW_GROUPS = ("users", "chatbot", "ai", "support", "subscriptions")


def overview(window="30j", date_from=None, date_to=None, groups=None):
    """GET /api/admin/analytics/overview — point d'entrée UNIQUE. Renvoie
    (payload, error) : error non-None seulement pour un filtre personnalisé
    invalide (400 côté route), jamais une exception.

    `groups` (optionnel) restreint les 5 agrégations réellement calculées à
    ce sous-ensemble — `None` (défaut) calcule tout, comportement historique
    inchangé pour tout appelant qui ne connaît pas ce paramètre. Ajouté pour
    admin-analytics.js : ces KPI ne sont plus affichés directement sur la
    page (retirés lors d'un chantier de simplification antérieur), ils
    n'alimentent plus que le tableau de bord personnalisé ("cartes KPI
    épinglées") — recalculer les 5 groupes à chaque chargement de page alors
    qu'aucun KPI n'est épinglé (le cas le plus courant) était un coût réel
    pour une donnée jamais consommée. `window` reste TOUJOURS calculé (coût
    négligeable, aucune requête DB) : le frontend en a besoin pour son
    libellé de période même sans aucun KPI épinglé."""
    window, since_iso, until_iso, error = resolve_window(window, date_from, date_to)
    if error:
        return None, error

    wanted = set(_OVERVIEW_GROUPS) if groups is None else (set(groups) & set(_OVERVIEW_GROUPS))
    payload = {"window": _window_payload(window, since_iso, until_iso)}
    if "ai" in wanted:
        ai_kpis, _ai_stats = _ai_kpis(since_iso, until_iso)
        payload["ai"] = ai_kpis
    if "users" in wanted:
        payload["users"] = _users_kpis(since_iso, until_iso)
    if "chatbot" in wanted:
        payload["chatbot"] = _chatbot_kpis(since_iso, until_iso)
    if "support" in wanted:
        payload["support"] = _support_kpis(since_iso, until_iso)
    if "subscriptions" in wanted:
        payload["subscriptions"] = _subscriptions_kpis()
    return payload, None


# ── Graphiques (Chart.js côté frontend) ──────────────────────────────────────
_NO_USERS_REASON = "Aucune inscription sur cette période."
_NO_CONVERSATIONS_REASON = "Aucune conversation créée sur cette période."
_NO_MESSAGES_REASON = "Aucun message échangé sur cette période."
_NO_AI_USAGE_REASON = "Aucune consommation IA enregistrée (ai_provider_usage) sur cette période."
_NO_TICKETS_REASON = "Aucun ticket sur cette période."
_NO_TICKETS_AT_ALL_REASON = "Aucun ticket n'existe dans la base."
_TICKETS_NOT_PERIOD_SCOPED_NOTE = (
    "Répartition sur l'ensemble des tickets existants (support_tickets_count_by_category/_priority ne sont pas "
    "filtrables par date) — non filtrée par la période sélectionnée."
)


def _series_wrap(series, reason):
    return _ok(series) if series else _na(reason)


def _normalize_count_series(rows):
    """db.py renvoie historiquement {"date", "count"} pour les séries
    "par jour/mois/année" (voir users_registered_per_day et consorts) —
    normalisé ici en {"date", "value"} pour que le frontend Analytics
    consomme TOUJOURS la même forme, quelle que soit la requête d'origine
    (jamais un JSON reconstruit différemment par graphique)."""
    return [{"date": r["date"], "value": r["count"]} for r in rows]


def charts(window="30j", date_from=None, date_to=None):
    """GET /api/admin/analytics/charts — séries journalières (ou mensuelles/
    annuelles pour les utilisateurs) RÉELLES, jamais un jour fabriqué : seuls
    les jours ayant au moins une ligne réelle apparaissent (même convention
    que admin_ai_service._build_daily_chart/system_health_service.charts)."""
    window, since_iso, until_iso, error = resolve_window(window, date_from, date_to)
    if error:
        return None, error

    ai_daily = db.ai_provider_usage_daily_totals(since_iso, until_iso)
    tokens_series = [{"date": r["date"], "value": r["total_tokens"] or 0} for r in ai_daily]
    cost_series = [{"date": r["date"], "value": round(r["estimated_cost"] or 0, 4)} for r in ai_daily]
    calls_series = [{"date": r["date"], "value": r["requests"] or 0} for r in ai_daily]
    latency_series = [
        {"date": r["date"], "value": round(r["total_response_time_ms"] / r["requests"]) if r["requests"] else None}
        for r in ai_daily
    ]
    success_series = [
        {"date": r["date"], "value": round(r["success_count"] / r["requests"] * 100, 1) if r["requests"] else None}
        for r in ai_daily
    ]
    errors_series = [{"date": r["date"], "value": r["error_count"] or 0} for r in ai_daily]
    fallback_series = [{"date": r["date"], "value": r["fallback_count"] or 0} for r in ai_daily]

    estimated_per_day = db.ai_request_logs_estimated_per_day(since_iso, until_iso)
    ai_responses_series = [{"date": r["day"], "value": r["real_count"]} for r in estimated_per_day]
    local_responses_series = [{"date": r["day"], "value": r["estimated_count"]} for r in estimated_per_day]

    messages_by_role = db.messages_created_per_day_by_role(since_iso, until_iso)
    user_messages_series = [{"date": r["date"], "value": r["count"]} for r in messages_by_role if r["role"] == "user"]
    assistant_messages_series = [
        {"date": r["date"], "value": r["count"]} for r in messages_by_role if r["role"] == "assistant"
    ]

    by_category = db.support_tickets_count_by_category()
    by_priority = db.support_tickets_count_by_priority()
    support_overview = support_service.overview_stats()
    by_status = {
        "open": support_overview["open_count"], "in_progress": support_overview["in_progress_count"],
        "closed": support_overview["closed_count"],
    }

    return {
        "window": _window_payload(window, since_iso, until_iso),
        "users": {
            "daily": _series_wrap(_normalize_count_series(db.users_registered_per_day(since_iso, until_iso)), _NO_USERS_REASON),
            "monthly": _series_wrap(_normalize_count_series(db.users_registered_per_month(since_iso, until_iso)), _NO_USERS_REASON),
            "yearly": _series_wrap(_normalize_count_series(db.users_registered_per_year(since_iso, until_iso)), _NO_USERS_REASON),
        },
        "chatbot": {
            "conversations_per_day": _series_wrap(
                _normalize_count_series(db.conversations_created_per_day(since_iso, until_iso)), _NO_CONVERSATIONS_REASON
            ),
            "messages_per_day": {
                "user": _series_wrap(user_messages_series, _NO_MESSAGES_REASON),
                "assistant": _series_wrap(assistant_messages_series, _NO_MESSAGES_REASON),
            },
            "ai_vs_local_per_day": {
                "ai": _series_wrap(ai_responses_series, _NO_MESSAGES_REASON),
                "local": _series_wrap(local_responses_series, _NO_MESSAGES_REASON),
            },
        },
        "ai": {
            "tokens_per_day": _series_wrap(tokens_series, _NO_AI_USAGE_REASON),
            "cost_per_day": _series_wrap(cost_series, _NO_AI_USAGE_REASON),
            "calls_per_day": _series_wrap(calls_series, _NO_AI_USAGE_REASON),
            "avg_latency_per_day": _series_wrap(latency_series, _NO_AI_USAGE_REASON),
            "success_rate_per_day": _series_wrap(success_series, _NO_AI_USAGE_REASON),
            "fallbacks_per_day": _series_wrap(fallback_series, _NO_AI_USAGE_REASON),
            "errors_per_day": _series_wrap(errors_series, _NO_AI_USAGE_REASON),
        },
        "support": {
            "tickets_per_day": _series_wrap(db.support_tickets_count_by_day(since_iso, until_iso), _NO_TICKETS_REASON),
            "by_category": _ok(by_category, note=_TICKETS_NOT_PERIOD_SCOPED_NOTE) if by_category else _na(_NO_TICKETS_AT_ALL_REASON),
            "by_priority": _ok(by_priority, note=_TICKETS_NOT_PERIOD_SCOPED_NOTE) if by_priority else _na(_NO_TICKETS_AT_ALL_REASON),
            "by_status": _ok(by_status, note="État actuel (non filtré par la période sélectionnée)."),
        },
    }, None


# ── Classements ("Top X") ─────────────────────────────────────────────────────
def _aggregate_provider_rows_by(rows, key):
    grouped = {}
    for row in rows:
        grouped_key = row[key]
        entry = grouped.setdefault(grouped_key, {key: grouped_key, "requests": 0, "total_tokens": 0, "estimated_cost": 0.0})
        entry["requests"] += row["requests"] or 0
        entry["total_tokens"] += row["total_tokens"] or 0
        entry["estimated_cost"] += row["estimated_cost"] or 0
    return sorted(grouped.values(), key=lambda e: e["total_tokens"], reverse=True)


def rankings(window="30j", date_from=None, date_to=None, limit=10):
    """GET /api/admin/analytics/rankings."""
    window, since_iso, until_iso, error = resolve_window(window, date_from, date_to)
    if error:
        return None, error

    top_ai_consumers = db.ai_request_logs_top_users_since(since_iso, until_iso, limit)
    top_chatbot_users = db.chatbot_top_users_since(since_iso, until_iso, limit)

    provider_rows = db.ai_provider_usage_by_provider_since(since_iso, until_iso)
    top_providers = _aggregate_provider_rows_by(provider_rows, "provider_key")
    top_models = sorted(provider_rows, key=lambda r: r["total_tokens"] or 0, reverse=True)[:limit]
    top_cost = sorted(provider_rows, key=lambda r: r["estimated_cost"] or 0, reverse=True)[:limit]

    engine_rows = db.ai_request_logs_by_engine_since(since_iso, until_iso)

    by_category = db.support_tickets_count_by_category()
    by_priority = db.support_tickets_count_by_priority()
    top_admins = db.support_tickets_by_assigned_admin_since(since_iso, until_iso)[:limit]

    return {
        "window": _window_payload(window, since_iso, until_iso),
        "users": {
            "top_ai_consumers": _ok(top_ai_consumers) if top_ai_consumers else _na(
                "Aucun appel IA enregistré sur cette période (ai_request_logs)."
            ),
            "top_chatbot_users": _ok(top_chatbot_users) if top_chatbot_users else _na(_NO_CONVERSATIONS_REASON),
            "top_active_reason": (
                "Top utilisateurs actifs / Top temps passé : déjà disponibles dans le module Utilisateurs "
                "(/admin/users, triable par « Dernière connexion »/« Temps total ») — réutilisés tels quels, "
                "aucune donnée dupliquée ici."
            ),
        },
        "ai": {
            "top_providers": _ok(top_providers[:limit]) if top_providers else _na(_NO_AI_USAGE_REASON),
            "top_models": _ok(top_models) if top_models else _na(_NO_AI_USAGE_REASON),
            "top_engines": _ok(engine_rows[:limit]) if engine_rows else _na(
                "Aucun appel IA/moteur local enregistré sur cette période (ai_request_logs)."
            ),
            "top_cost": _ok(top_cost) if top_cost else _na(_NO_AI_USAGE_REASON),
            "top_tokens": _ok(top_models) if top_models else _na(_NO_AI_USAGE_REASON),
        },
        "support": {
            "top_categories": _ok(by_category, note=_TICKETS_NOT_PERIOD_SCOPED_NOTE) if by_category else _na(_NO_TICKETS_AT_ALL_REASON),
            "top_priorities": _ok(by_priority, note=_TICKETS_NOT_PERIOD_SCOPED_NOTE) if by_priority else _na(_NO_TICKETS_AT_ALL_REASON),
            "top_admins": _ok(top_admins) if top_admins else _na("Aucun ticket assigné sur cette période."),
            # Le "temps moyen de première réponse / résolution" n'est plus
            # renvoyé ici : doublon exact de la carte équivalente du module
            # Support (voir support_service.overview_stats()), retiré du
            # rendu Analytics (chantier de simplification).
        },
    }, None


# ── Recherche globale ─────────────────────────────────────────────────────────
def global_search(query, limit=5):
    """GET /api/admin/analytics/search — fédère les recherches déjà
    existantes (utilisateurs/tickets), ajoute une recherche conversations
    (nouvelle, aucun équivalent global n'existait) et un filtrage en mémoire
    sur la petite liste des fournisseurs IA déjà chargée (aucune nouvelle
    requête SQL nécessaire, la liste tient déjà entièrement en mémoire
    ailleurs dans le projet, voir admin_ai_service.py)."""
    query = (query or "").strip()
    if len(query) < 2:
        return {
            "users": [], "conversations": [], "tickets": [], "ai_providers": [],
            "messages": [], "backups": [], "security_events": [],
        }

    users_result = admin_users_service.list_users(search=query, page_size=limit)
    tickets_result = support_service.list_tickets(search=query, page_size=limit)
    conversations = db.search_conversations_global(query, limit=limit)
    messages = db.search_messages_global(query, limit=limit)
    security_events = db.search_security_events_global(query, limit=limit)

    query_lower = query.lower()
    providers = [
        {"id": p["id"], "name": p["name"], "provider_key": p["provider_key"], "model_name": p["model_name"]}
        for p in ai_svc.list_providers()
        if query_lower in p["name"].lower() or query_lower in p["provider_key"].lower()
        or query_lower in p["model_name"].lower()
    ][:limit]
    backups = [b for b in backup_service.list_backups() if query_lower in b["filename"].lower()][:limit]

    return {
        "users": users_result["items"],
        "conversations": conversations,
        "tickets": tickets_result["items"],
        "ai_providers": providers,
        "messages": messages,
        "backups": backups,
        "security_events": security_events,
    }


# ── Favoris ("vues Analytics sauvegardées") ─────────────────────────────────
def list_saved_views(admin_user_id):
    return [
        {"id": row["id"], "name": row["name"], "params": json.loads(row["params_json"]), "created_at": row["created_at"]}
        for row in db.list_analytics_saved_views(admin_user_id)
    ]


def create_saved_view(admin_user_id, name, window, date_from=None, date_to=None):
    name = (name or "").strip()
    if not name:
        return None, "Le nom de la vue est obligatoire."
    if len(name) > 80:
        return None, "Le nom ne doit pas dépasser 80 caractères."
    params = {"window": window, "date_from": date_from, "date_to": date_to}
    view_id = db.create_analytics_saved_view(admin_user_id, name, json.dumps(params, ensure_ascii=False))
    return view_id, None


def delete_saved_view(admin_user_id, view_id):
    return db.delete_analytics_saved_view(admin_user_id, view_id)


# ── Tableau de bord personnalisé ("cartes KPI épinglées") ───────────────────
# Whitelist stricte des clés épinglables — une clé par carte KPI réelle de
# overview() (Partie 3 du chantier fondations), jamais une chaîne libre.
PINNABLE_KPIS = (
    "users.total_registered", "users.new_users", "users.active_users", "users.logins",
    "chatbot.conversations", "chatbot.user_messages", "chatbot.assistant_messages",
    "ai.calls", "ai.tokens", "ai.cost_usd", "ai.avg_latency_ms", "ai.success_rate_pct",
    "ai.errors", "ai.fallbacks",
    "support.tickets_created", "support.open", "support.closed",
    "subscriptions.free", "subscriptions.premium", "subscriptions.ultra",
)


def list_pinned_kpis(admin_user_id):
    return db.list_pinned_kpis(admin_user_id)


def toggle_pinned_kpi(admin_user_id, kpi_key, pinned):
    if kpi_key not in PINNABLE_KPIS:
        return False, f"Carte KPI inconnue : {kpi_key!r}."
    if pinned:
        db.pin_kpi(admin_user_id, kpi_key)
    else:
        db.unpin_kpi(admin_user_id, kpi_key)
    return True, None


# ── Alertes ───────────────────────────────────────────────────────────────────
# Comparaison période courante vs période précédente de même durée, à partir
# des mêmes fonctions déjà utilisées par overview()/charts() — jamais un
# recalcul différent. Seuils explicites (mêmes principes que
# system_health_service.ALERT_*), documentés et affichés tels quels, jamais
# cachés.
ALERT_AI_CALLS_INCREASE_PCT = 50
ALERT_ERROR_RATE_INCREASE_PCT = 20
ALERT_NEW_USERS_INCREASE_PCT = 50
ALERT_TICKETS_INCREASE_PCT = 50


def _pct_change(current, previous):
    if previous in (None, 0):
        return None
    return round((current - previous) / previous * 100, 1)


def list_alerts(window="30j", date_from=None, date_to=None):
    """Réutilise system_health_service (fournisseurs indisponibles, déjà
    calculé là-bas, jamais recalculé ici) et les mêmes fonctions db.py déjà
    utilisées par overview(). Appelée en interne par
    admin_dashboard_service._alerts() (fenêtre fixe "aujourd_hui") : c'est
    désormais le SEUL endroit où ces alertes sont affichées (audit round 2 —
    avant : dupliquées sur /admin/analytics, page de deep-dive périodique où
    "qu'est-ce qui a besoin de mon attention aujourd'hui" n'a pas sa place).
    Aucune route HTTP dédiée ne l'expose plus directement.

    `window`/`date_from`/`date_to` restent des paramètres génériques (audit
    du Chantier Administrateur, 2026-08-25) alors qu'un seul appelant existe
    aujourd'hui, toujours avec "aujourd_hui" : cette fonction calcule un
    delta "période courante vs période précédente équivalente" (voir
    `period_delta` ci-dessous), une logique déjà générique par nature et
    strictement identique à `overview()`/`charts()`/`rankings()` du même
    module — retirer ces paramètres obligerait soit à dupliquer
    `resolve_window()` en dur avec "aujourd_hui", soit à casser la
    cohérence de signature avec le reste du module pour économiser 2
    paramètres jamais coûteux (aucune requête DB tant qu'ils ne sont pas
    utilisés). Simplification jugée plus risquée que bénéfique ici :
    conservée telle quelle."""
    import system_health_service

    window, since_iso, until_iso, error = resolve_window(window, date_from, date_to)
    if error:
        return None, error

    now = _now()
    period_delta = (
        (datetime.fromisoformat(until_iso) if until_iso else now) - datetime.fromisoformat(since_iso)
    )
    previous_since = (datetime.fromisoformat(since_iso) - period_delta).isoformat()
    previous_until = since_iso

    alerts = []

    current_ai = db.ai_provider_usage_daily_totals(since_iso, until_iso)
    previous_ai = db.ai_provider_usage_daily_totals(previous_since, previous_until)
    current_calls = sum(r["requests"] or 0 for r in current_ai)
    previous_calls = sum(r["requests"] or 0 for r in previous_ai)
    calls_change = _pct_change(current_calls, previous_calls)
    if calls_change is not None and calls_change >= ALERT_AI_CALLS_INCREASE_PCT:
        alerts.append({
            "level": "warning", "code": "forte_consommation_ia",
            "message": f"Consommation IA en hausse de {calls_change}% par rapport à la période précédente "
                        f"({previous_calls} → {current_calls} appels, seuil {ALERT_AI_CALLS_INCREASE_PCT}%).",
        })

    current_errors = sum(r["error_count"] or 0 for r in current_ai)
    previous_errors = sum(r["error_count"] or 0 for r in previous_ai)
    errors_change = _pct_change(current_errors, previous_errors)
    if errors_change is not None and errors_change >= ALERT_ERROR_RATE_INCREASE_PCT:
        alerts.append({
            "level": "critical", "code": "hausse_erreurs",
            "message": f"Erreurs IA en hausse de {errors_change}% ({previous_errors} → {current_errors}, "
                        f"seuil {ALERT_ERROR_RATE_INCREASE_PCT}%).",
        })

    for service in system_health_service.list_services():
        if service["state"] == "down":
            alerts.append({
                "level": "critical", "code": "provider_indisponible",
                "message": f"{service['name']} est indisponible.",
            })

    current_users = db.count_users_created_since(since_iso, until_iso)
    previous_users = db.count_users_created_since(previous_since, previous_until)
    users_change = _pct_change(current_users, previous_users)
    if users_change is not None and users_change >= ALERT_NEW_USERS_INCREASE_PCT:
        alerts.append({
            "level": "info", "code": "forte_creation_comptes",
            "message": f"Créations de comptes en hausse de {users_change}% ({previous_users} → {current_users}, "
                        f"seuil {ALERT_NEW_USERS_INCREASE_PCT}%).",
        })

    current_tickets = db.count_support_tickets_created_since(since_iso, until_iso)
    previous_tickets = db.count_support_tickets_created_since(previous_since, previous_until)
    tickets_change = _pct_change(current_tickets, previous_tickets)
    if tickets_change is not None and tickets_change >= ALERT_TICKETS_INCREASE_PCT:
        alerts.append({
            "level": "warning", "code": "augmentation_tickets",
            "message": f"Créations de tickets en hausse de {tickets_change}% ({previous_tickets} → {current_tickets}, "
                        f"seuil {ALERT_TICKETS_INCREASE_PCT}%).",
        })

    return {
        "window": _window_payload(window, since_iso, until_iso),
        "previous_period": {"since": previous_since, "until": previous_until},
        "alerts": alerts,
    }, None
