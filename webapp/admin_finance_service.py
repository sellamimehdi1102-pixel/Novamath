"""
Service du module "Finance" (/admin/finance) — Phase 2A de l'audit admin
(2026-10-21). Deux familles de données, de fiabilité très différente,
JAMAIS mélangées dans une même fonction :

1. Abonnements/MRR : calculés UNIQUEMENT depuis la base locale (db.py),
   AUCUN appel réseau Stripe — instantané, toujours disponible, mais MRR
   reste une ESTIMATION (voir get_subscriptions_overview ci-dessous pour
   l'hypothèse exacte posée).
2. Revenus/paiements : nécessitent un appel réel à Stripe (voir
   stripe_financial_service.py) — protégés par stripe_access_guard à
   CHAQUE appel, journalisés (admin_ai_log_service) comme la réconciliation
   Stripe de la Phase 1, puisqu'il s'agit à chaque fois d'un appel réseau
   sortant réel et auditable.

Politique "aucune donnée inventée" : identique au reste du projet — toute
valeur non calculable renvoie {"available": False, "value": None, "reason":
"..."}, jamais un 0/texte fabriqué (voir _ok/_na).

Architecture stricte : server.py → admin_finance_service.py →
stripe_financial_service.py / db.py / admin_ai_log_service.py, jamais
l'inverse. Ce module ne modifie JAMAIS Stripe ni la base (lecture seule de
bout en bout, y compris ses propres appels Stripe).
"""
import config
import admin_ai_log_service
import db
import stripe_access_guard
import stripe_financial_service
import stripe_service
from plan_service import Plan

STATS_WINDOW_DAYS = 30

# Tarifs catalogue RÉELS attendus côté Stripe (mêmes constantes que
# stripe_service.validate_stripe_prices(), jamais le champ catalogue
# éditable par l'admin — subscription_plan_service.py documente déjà que ce
# champ est un simple affichage, non garanti identique au prix Stripe
# réel : le MRR ne doit jamais hériter de cette même incertitude s'il peut
# l'éviter).
_PLAN_PRICE_CENTS = stripe_service.STRIPE_EXPECTED_AMOUNTS_CENTS


def _ok(value, note=None):
    out = {"available": True, "value": value}
    if note:
        out["note"] = note
    return out


def _na(reason):
    return {"available": False, "value": None, "reason": reason}


def _since(days):
    from datetime import datetime, timedelta, timezone
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


def stripe_environment():
    """Même bannière que admin_subscriptions_service._stripe_environment()
    (Phase 1), recalculée ici indépendamment plutôt qu'importée : ce module
    ne doit dépendre d'aucun autre module de page admin, uniquement de
    services de données (db/stripe_service/config), pour rester
    réutilisable si la page Finance évolue sans toucher aux Abonnements."""
    mode = stripe_service.operating_mode()
    return {
        "mode": mode,
        "app_environment": "production" if config.IS_PRODUCTION else "developpement",
        "reconciliation_blocked": mode == "production" and not config.IS_PRODUCTION,
        "reconciliation_requires_confirmation": mode == "production" and config.IS_PRODUCTION,
    }


def get_subscriptions_overview():
    """Abonnements actifs/en retard/résiliés + MRR estimé — AUCUN appel
    réseau, uniquement db.py. Toujours disponible, y compris quand Stripe
    n'est pas configuré ou que l'accès est bloqué (cette fonction n'appelle
    jamais stripe_access_guard, elle n'a rien à protéger)."""
    active_by_plan = db.count_active_subscriptions_by_plan()
    past_due = db.count_users_with_failed_payment()
    canceled = db.count_users_with_canceled_subscription()
    since = _since(STATS_WINDOW_DAYS)
    new_subscriptions = db.count_security_events_since("stripe_subscription_created", since)
    cancellations = db.count_security_events_since("stripe_subscription_deleted", since)

    active_premium = active_by_plan.get(Plan.PREMIUM.value, 0)
    active_ultra = active_by_plan.get(Plan.ULTRA.value, 0)
    mrr_cents = active_premium * _PLAN_PRICE_CENTS[Plan.PREMIUM] + active_ultra * _PLAN_PRICE_CENTS[Plan.ULTRA]

    return {
        "window_days": STATS_WINDOW_DAYS,
        "active_subscriptions_by_plan": _ok(
            active_by_plan,
            note="Comptes dont le dernier statut Stripe connu (webhook) est 'active' ou 'trialing'.",
        ),
        "past_due_or_unpaid": _ok(
            past_due,
            note="Abonnements payants en échec de paiement (relance Stripe en cours ou tentatives épuisées) — "
            "toujours comptés séparément des abonnements actifs.",
        ),
        "canceled": _ok(
            canceled,
            note="Comptes dont le dernier statut Stripe connu est 'canceled' — un état courant, jamais un "
            "nombre de résiliations SURVENUES sur une période (voir 'cancellations' ci-dessous pour cela).",
        ),
        "new_subscriptions": _ok(
            new_subscriptions,
            note=f"Nouveaux abonnements Stripe créés sur les {STATS_WINDOW_DAYS} derniers jours (événement, pas un état).",
        ),
        "cancellations": _ok(
            cancellations,
            note=f"Résiliations survenues sur les {STATS_WINDOW_DAYS} derniers jours (événement, pas un état).",
        ),
        "mrr_cents": _ok(
            mrr_cents,
            note="ESTIMATION : (abonnements Premium actifs x tarif catalogue Premium) + (abonnements Ultra actifs "
            "x tarif catalogue Ultra). Suppose que chaque abonnement actif paie exactement le tarif catalogue en "
            "vigueur — ignore toute remise/coupon Stripe appliqué individuellement, qu'aucune donnée locale ne "
            "permet de détecter sans interroger les Subscription Items réels sur Stripe.",
        ),
    }


def _map_financial_error(exc):
    """Traduit une exception du garde-fou/service financier en {"_": message,
    "code": ...} — même convention que admin_subscriptions_service.
    reconcile_stripe_logged (Phase 1), pour que server.py mappe le `code`
    vers le même jeu de statuts HTTP (403/409/501) sans dupliquer la
    logique de correspondance."""
    if isinstance(exc, stripe_access_guard.StripeAccessBlocked):
        return {"_": str(exc), "code": "blocked_local_production"}
    if isinstance(exc, stripe_access_guard.StripeAccessConfirmationRequired):
        return {"_": str(exc), "code": "confirmation_required"}
    if isinstance(exc, stripe_financial_service.StripeFinancialDataUnavailable):
        return {"_": str(exc), "code": "not_configured"}
    raise exc


def get_revenue_report_logged(actor, days=30, confirmed=False):
    """Rapport de revenu sur `days` jours — appel Stripe réel protégé +
    journalisé (voir docstring module). Renvoie (ok, result_or_errors)."""
    try:
        report = stripe_financial_service.get_revenue_report(days=days, confirmed=confirmed)
    except (
        stripe_access_guard.StripeAccessBlocked,
        stripe_access_guard.StripeAccessConfirmationRequired,
        stripe_financial_service.StripeFinancialDataUnavailable,
    ) as exc:
        result = _map_financial_error(exc)
        if result["code"] != "confirmation_required":
            admin_ai_log_service.record(
                actor, action="view_finance_revenue", provider_id=None, provider_name="Stripe (revenus)",
                old_values=None, new_values=None, result="error", error_message=str(exc),
            )
        return False, result

    admin_ai_log_service.record(
        actor, action="view_finance_revenue", provider_id=None, provider_name="Stripe (revenus)",
        old_values=None,
        new_values={"mode": report["mode"], "window_days": report["window_days"], "invoices_checked": report["invoices_checked"]},
        result="success", error_message=None,
    )
    return True, report


def get_revenue_series_logged(actor, months=6, confirmed=False):
    try:
        report = stripe_financial_service.get_revenue_series(months=months, confirmed=confirmed)
    except (
        stripe_access_guard.StripeAccessBlocked,
        stripe_access_guard.StripeAccessConfirmationRequired,
        stripe_financial_service.StripeFinancialDataUnavailable,
    ) as exc:
        result = _map_financial_error(exc)
        if result["code"] != "confirmation_required":
            admin_ai_log_service.record(
                actor, action="view_finance_revenue", provider_id=None, provider_name="Stripe (évolution revenus)",
                old_values=None, new_values=None, result="error", error_message=str(exc),
            )
        return False, result

    admin_ai_log_service.record(
        actor, action="view_finance_revenue", provider_id=None, provider_name="Stripe (évolution revenus)",
        old_values=None, new_values={"mode": report["mode"], "months_requested": report["months_requested"]},
        result="success", error_message=None,
    )
    return True, report


def get_payments_report_logged(actor, limit=20, confirmed=False):
    try:
        report = stripe_financial_service.get_payments_report(limit=limit, confirmed=confirmed)
    except (
        stripe_access_guard.StripeAccessBlocked,
        stripe_access_guard.StripeAccessConfirmationRequired,
        stripe_financial_service.StripeFinancialDataUnavailable,
    ) as exc:
        result = _map_financial_error(exc)
        if result["code"] != "confirmation_required":
            admin_ai_log_service.record(
                actor, action="view_finance_payments", provider_id=None, provider_name="Stripe (paiements)",
                old_values=None, new_values=None, result="error", error_message=str(exc),
            )
        return False, result

    admin_ai_log_service.record(
        actor, action="view_finance_payments", provider_id=None, provider_name="Stripe (paiements)",
        old_values=None,
        new_values={"mode": report["mode"], "succeeded_count": report["succeeded_count"], "failed_count": report["failed_count"]},
        result="success", error_message=None,
    )
    return True, report
