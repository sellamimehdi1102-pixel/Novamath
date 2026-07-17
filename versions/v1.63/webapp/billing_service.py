"""
Agrège les informations Stripe Billing nécessaires aux pages Abonnement et
Profil (statut, dates, moyen de paiement, factures) et pilote le Portail
client + le changement de plan.

Séparation des responsabilités, dans la continuité de stripe_service.py /
stripe_webhook_service.py :
- stripe_service.py            : appels SDK Stripe bruts, aucune logique
  métier.
- stripe_webhook_service.py     : que faire d'un événement webhook une fois
  reçu — seule voie qui écrit plan/stripe_subscription_id/status en base.
- billing_service.py (ce module) : lecture seule côté Stripe (jamais de
  webhook, jamais d'écriture en base) — assemble plusieurs appels
  stripe_service en une réponse pour les routes /api/billing/* de
  server.py, et traduit une demande de changement de plan en le bon appel
  Stripe (immédiat ou programmé). Le webhook reste l'unique source de
  vérité qui met à jour la base suite à un changement réel côté Stripe.
"""
import logging

import stripe

from plan_service import Plan, get_plan
import stripe_service

logger = logging.getLogger("billing_service")

_PLAN_ORDER = (Plan.FREE, Plan.PREMIUM, Plan.ULTRA)


class NoStripeCustomer(Exception):
    """Levée quand l'utilisateur n'a jamais eu de client Stripe (jamais passé
    par un Checkout) : aucun Portail à ouvrir, jamais de Customer créé ici."""


class NoActiveSubscription(Exception):
    """Levée quand un changement de plan est demandé sans abonnement actif."""


class SamePlan(Exception):
    """Levée quand le plan demandé est déjà le plan actif de l'abonnement."""


def _payment_method_summary(customer_id):
    methods = stripe_service.list_payment_methods(customer_id)
    data = methods["data"]
    if not data:
        return None
    card = data[0]["card"]
    return {
        "brand": card["brand"],
        "last4": card["last4"],
        "exp_month": card["exp_month"],
        "exp_year": card["exp_year"],
    }


def _invoice_history(customer_id, limit=10):
    invoices = stripe_service.list_invoices(customer_id, limit=limit)
    return [
        {
            "id": inv["id"],
            "amount_paid": inv["amount_paid"],
            "currency": inv["currency"],
            "status": inv["status"],
            "created": inv["created"],
            "invoice_pdf": inv.get("invoice_pdf"),
            "hosted_invoice_url": inv.get("hosted_invoice_url"),
        }
        for inv in invoices["data"]
    ]


def get_billing_status(user):
    """Renvoie l'état d'abonnement complet. Le plan effectif vient de
    plan_service.get_plan (jamais recalculé ici, cohérent avec le reste du
    projet) ; toutes les autres informations (dates, moyen de paiement,
    factures) sont lues en direct depuis Stripe — jamais depuis une colonne
    mise en cache qui pourrait diverger de l'état réel côté Stripe."""
    plan = get_plan(user)
    customer_id = user.get("stripe_customer_id")
    status = {
        "plan": plan.value,
        "subscription_status": user.get("stripe_subscription_status"),
        "renew_at": None,
        "cancel_at": None,
        "customer_portal_available": bool(customer_id),
        "billing_email": None,
        "payment_method": None,
        "invoices": [],
    }
    if not customer_id:
        return status

    try:
        customer = stripe_service.get_customer(customer_id)
        status["billing_email"] = customer.get("email")
        status["payment_method"] = _payment_method_summary(customer_id)
        status["invoices"] = _invoice_history(customer_id)

        subscription_id = user.get("stripe_subscription_id")
        if subscription_id:
            subscription = stripe_service.get_subscription(subscription_id)
            status["renew_at"] = subscription.get("current_period_end")
            if subscription.get("cancel_at_period_end"):
                status["cancel_at"] = subscription.get("cancel_at")
    except stripe.error.StripeError as e:
        # Best-effort : un plan/status déjà connu en base reste affiché même
        # si l'enrichissement Stripe échoue temporairement (indisponibilité
        # de l'API, customer/subscription supprimé côté Stripe...).
        logger.warning("Statut de facturation Stripe incomplet pour %s : %s", customer_id, e)

    return status


def create_portal_session(user, return_url):
    """Crée une Billing Portal Session pour le customer Stripe existant de
    `user`. Ne crée jamais de nouveau Customer : un portail suppose un
    client déjà passé par le Checkout au moins une fois (voir
    stripe_customer_id, seule source acceptée)."""
    customer_id = user.get("stripe_customer_id")
    if not customer_id:
        raise NoStripeCustomer("Aucun client Stripe associé à ce compte.")
    session = stripe_service.create_billing_portal_session(customer_id, return_url)
    return session["url"]


def change_plan(user, new_plan):
    """Change le plan de l'abonnement actif : upgrade immédiat avec proration
    (Premium -> Ultra) ou downgrade programmé à la prochaine période de
    facturation (Ultra -> Premium) — jamais d'écriture en base ici, le
    webhook (customer.subscription.updated) reste l'unique source de vérité
    qui appliquera le changement à users.plan une fois effectif côté
    Stripe."""
    subscription_id = user.get("stripe_subscription_id")
    if not subscription_id:
        raise NoActiveSubscription("Aucun abonnement actif à modifier.")

    current_plan = get_plan(user)
    if new_plan is current_plan:
        raise SamePlan("Ce plan est déjà actif.")

    if _PLAN_ORDER.index(new_plan) > _PLAN_ORDER.index(current_plan):
        return stripe_service.change_plan(subscription_id, new_plan)
    return stripe_service.schedule_downgrade(subscription_id, new_plan)
