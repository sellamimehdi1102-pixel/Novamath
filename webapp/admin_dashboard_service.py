"""
Service en lecture seule pour le Dashboard Administrateur (Vue d'ensemble de
/admin) — aucune écriture, aucune action destructive, aucune donnée inventée.

Architecture :

    server.py  →  admin_dashboard_service.py  →  {db, support_service,
                   system_health_service, admin_analytics_service}.py

jamais l'inverse. Ce module ne dépend ni de Flask ni de rôles/permissions
(déjà tranchés par role_service.py au niveau de la route, jamais recontrôlés
ici) — voir server.py::api_admin_dashboard.

── Politique "aucune donnée inventée" ──────────────────────────────────────
Chaque métrique renvoie la forme uniforme {"available": bool, "value": ...}
(+ "reason" si available=False). `available=False` couvre le cas où la
source de données existe mais n'a structurellement aucune mesure à ce jour.
Dans tous les cas, la valeur est None, JAMAIS 0 : un 0 fabriqué laisserait
croire à une mesure réelle alors qu'il s'agit d'une absence de mesure.

── Refonte UX (audit round 2) ──────────────────────────────────────────────
Le Dashboard est la page la plus consultée du panneau : chaque carte doit
permettre une décision en moins de 30 secondes, sinon elle n'a rien à y
faire. Sortent : le total d'utilisateurs (vanity, aucune décision), les
nouveaux inscrits 24h (déjà couvert par l'alerte "forte création de
comptes"), la répartition par plan (déjà sur /admin/subscriptions, aucune
décision quotidienne) et le flux d'activité brute (login/compte créé —
aucune décision, juste du bruit forensique). Entrent : un statut Santé et un
statut Support réellement alimentés (avant : pures cartes de navigation
vides) et les alertes métier (avant : uniquement sur /admin/analytics, page
de deep-dive périodique — alors qu'"est-ce qui a besoin de mon attention
aujourd'hui" est exactement le rôle du Dashboard). Résultat : 4 cartes +
1 liste d'alertes, chacune réellement décisionnelle, zéro doublon (le détail
complet reste exclusivement dans sa page dédiée).

── Audit "tri des informations" (Phase 2) ──────────────────────────────────
Toujours 4 cartes, aucune carte permanente ajoutée. La carte "Utilisateurs
actifs" gagne une comparaison avec hier (delta simple, pas un pourcentage —
voir _card_active_users_today). La liste d'alertes gagne deux règles
ponctuelles ("paiements en échec", "consentements parentaux en attente"),
chacune sur une donnée déjà réelle en base (users.stripe_subscription_status/
users.account_status) via une agrégation minimale ajoutée à db.py
(count_users_with_failed_payment/count_users_pending_parental_consent) —
aucune des deux fonctions de comptage existantes (count_users_admin côté
admin_users_service.py) ne convenait telle quelle, voir leurs docstrings.
"""
from datetime import datetime, timedelta, timezone

import admin_analytics_service
import db
import metrics_service
import support_service
import system_health_service


def _now():
    return datetime.now(timezone.utc)


def _today_start():
    return _now().replace(hour=0, minute=0, second=0, microsecond=0)


def _today_start_iso():
    return _today_start().isoformat()


def _yesterday_start_iso():
    return (_today_start() - timedelta(days=1)).isoformat()


def _available(value, reason=None):
    if value is None:
        return {"available": False, "value": None, "reason": reason}
    return {"available": True, "value": value}


# ── Cartes ───────────────────────────────────────────────────────────────────
def _card_active_users_today():
    """Utilisateurs actifs (dernière connexion) depuis minuit (heure serveur)
    vs la même fenêtre hier — un delta simple (`aujourd'hui - hier`), jamais
    un pourcentage : reste calculable même si personne n'était actif hier
    (delta = aujourd'hui - 0), voir admin-dashboard.js::activeUsersCard pour
    l'affichage exact ("+N vs hier"/"−N vs hier"). `db.count_users_active_
    since` renvoie toujours un entier réel (COUNT SQL, jamais NULL) : cette
    carte est donc toujours `available`, comme avant ce chantier."""
    today_start = _today_start_iso()
    today = db.count_users_active_since(today_start)
    yesterday = db.count_users_active_since(_yesterday_start_iso(), today_start)
    return _available({"today": today, "yesterday": yesterday, "delta": today - yesterday})


def _card_ai_providers_status():
    """Un fournisseur SANS ligne dans ai_provider_health n'a jamais été
    testé : son statut est None (jamais "ok"/"down" deviné). Consommé ici
    uniquement pour afficher UN badge global agrégé sur la carte IA du
    Dashboard (voir admin-dashboard.js) — le détail par fournisseur reste
    exclusivement dans le module IA (admin_ai_service.py)."""
    providers = db.list_ai_providers()
    if not providers:
        return _available(None, "Aucun fournisseur IA configuré.")
    health_by_provider = {h["provider_id"]: h for h in db.list_ai_provider_health()}
    items = []
    for p in providers:
        health = health_by_provider.get(p["id"])
        items.append({
            "name": p["name"],
            "enabled": bool(p["enabled"]),
            "last_success": health["last_success"] if health else None,
            "last_failure": health["last_failure"] if health else None,
        })
    return _available(items)


def _card_health_status():
    """Réutilise system_health_service.overview() (même source que la page
    Santé) : jamais de statut global recalculé séparément. Toujours
    disponible (la supervision elle-même ne peut pas être "indisponible")."""
    return _available(system_health_service.overview())


def _card_support_status():
    """Réutilise support_service.overview_stats() (même source que
    l'ancienne carte "Vue d'ensemble" de la page Support et qu'Analytics) —
    seuls les 2 champs utiles à une décision immédiate sont conservés ici."""
    stats = support_service.overview_stats()
    return _available({"open_count": stats["open_count"], "total_count": stats["total_count"]})


def _card_server_errors():
    """Réutilise metrics_service.in_memory_snapshot() (déjà incrémenté à
    chaque requête par logging_service.init_app(), voir sa docstring) —
    aucune nouvelle collecte, aucun compteur parallèle. Compteurs
    process-local (remis à zéro à chaque redémarrage) : PAS une fenêtre
    glissante de 24h (aucune table ne journalise un timestamp par requête),
    donc jamais présenté comme tel — voir admin-dashboard.js::errorsSubLabel
    pour le libellé exact affiché."""
    m = metrics_service.in_memory_snapshot()
    return _available(m)


CARD_METRICS = {
    "active_users_today": _card_active_users_today,
    "ai_providers_status": _card_ai_providers_status,
    "health_status": _card_health_status,
    "support_status": _card_support_status,
    "server_errors": _card_server_errors,
}


# ── Alertes (déplacées depuis /admin/analytics — audit round 2) ────────────
# Mêmes règles, même seuils, même fonction que list_alerts() de
# admin_analytics_service.py (aucune logique dupliquée) : fenêtre fixe
# "aujourd_hui" (le Dashboard n'a pas de sélecteur de période, contrairement
# à Analytics qui garde list_alerts() pour ses propres besoins d'exploration
# historique). L'ancienne route HTTP /api/admin/analytics/alerts et son
# affichage sur la page Analytics ont été retirés : cette liste n'existe
# plus qu'à un seul endroit désormais.
def _alerts():
    payload, error = admin_analytics_service.list_alerts("aujourd_hui")
    if error:
        return _available(None, error)
    alerts = list(payload["alerts"])

    # Deux règles supplémentaires, propres au Dashboard (pas des tendances
    # période courante/précédente comme list_alerts() ci-dessus, de simples
    # conditions ponctuelles "> 0") — ajoutées ici plutôt que dans
    # admin_analytics_service.py pour ne pas mélanger la logique de
    # comparaison temporelle d'Analytics avec ces deux compteurs instantanés
    # (Chantier Administrateur, Phase 2). Jamais de carte permanente : une
    # alerte uniquement si le compte est > 0, jamais un 0 affiché.
    failed_payments = db.count_users_with_failed_payment()
    if failed_payments:
        alerts.append({
            "level": "warning", "code": "paiements_en_echec",
            "message": f"{failed_payments} abonnement(s) en échec de paiement.",
            "link": {"path": "/admin/subscriptions", "label": "Voir les abonnements"},
        })

    pending_consent = db.count_users_pending_parental_consent()
    if pending_consent:
        alerts.append({
            "level": "warning", "code": "consentement_parental_attente",
            "message": f"{pending_consent} compte(s) en attente de consentement parental.",
            "link": {"path": "/admin/users", "label": "Voir les utilisateurs"},
        })

    return _available(alerts)


# ── Point d'entrée unique ───────────────────────────────────────────────────────
def get_dashboard_snapshot():
    """Snapshot complet consommé par GET /api/admin/dashboard (voir
    server.py) — une seule lecture, jamais recalculée deux fois pour la même
    requête. Itère sur CARD_METRICS : ajouter une métrique future ne touche
    jamais cette fonction."""
    return {
        "cards": {key: fn() for key, fn in CARD_METRICS.items()},
        "alerts": _alerts(),
    }
