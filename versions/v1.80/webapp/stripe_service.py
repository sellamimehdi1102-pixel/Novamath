"""
Couche Stripe Billing pour NovaMath : création/lecture de client, Checkout
Session, abonnement, paiement, annulation, changement de plan.

Même séparation que db.py : ce module ne contient aucune route Flask, aucune
logique de session HTTP — uniquement les appels au SDK Stripe. Les routes et
la logique métier (association user <-> customer, redirections) vivent dans
webapp/server.py.

Clés et Price ID toujours lus depuis des variables d'environnement (jamais en
dur dans le code), sur le même modèle que OAUTH_PROVIDERS dans auth.py :
STRIPE_SECRET_KEY, STRIPE_PUBLIC_KEY, STRIPE_PRICE_PREMIUM, STRIPE_PRICE_ULTRA.

Le vocabulaire de plan (Plan.PREMIUM/Plan.ULTRA) vient de plan_service.py,
seule source de vérité des plans NovaMath — ce module ne fait qu'utiliser ce
type partagé pour parler à l'API Stripe, il ne décide jamais des droits
utilisateur (voir plan_service.py pour cette responsabilité).
"""
import logging
import os

import stripe

from plan_service import Plan

logger = logging.getLogger("stripe_service")

STRIPE_PRICES = {
    Plan.PREMIUM: "STRIPE_PRICE_PREMIUM",
    Plan.ULTRA: "STRIPE_PRICE_ULTRA",
}


class StripeNotConfigured(Exception):
    """Levée quand STRIPE_SECRET_KEY n'est pas définie côté serveur."""


class StripePlanUnknown(Exception):
    """Levée quand le plan demandé ne correspond à aucun Price ID configuré."""


# Valeurs placeholder de .env.example, copiées telles quelles dans .env par
# erreur au lieu d'être remplacées par de vraies clés Stripe : sans ce
# garde-fou, la clé n'échoue qu'au moment de l'appel Stripe réel, avec une
# StripeError peu explicite (AuthenticationError) au lieu du diagnostic clair
# attendu ici (StripeNotConfigured -> 501 explicite côté server.py, jamais un
# 500 générique). Comparaison à une liste explicite plutôt qu'une heuristique
# de longueur : les tests du projet utilisent des valeurs factices courtes
# (ex: "sk_test_123") qui doivent rester acceptées comme "configurées".
_PLACEHOLDER_VALUES = {"sk_test_xxx", "pk_test_xxx", "whsec_xxx"}


def _looks_unconfigured(value):
    return not value or value in _PLACEHOLDER_VALUES


def _client():
    """Renvoie le module stripe configuré avec la clé secrète courante, lue à
    chaque appel (jamais mise en cache) pour rester cohérent avec
    _get_or_create_secret côté auth.py : la variable d'environnement reste la
    source de vérité, y compris si elle change entre deux requêtes en tests."""
    api_key = os.environ.get("STRIPE_SECRET_KEY")
    if _looks_unconfigured(api_key):
        raise StripeNotConfigured(
            "STRIPE_SECRET_KEY n'est pas configurée sur ce serveur "
            "(absente ou valeur placeholder de .env.example non remplacée)."
        )
    stripe.api_key = api_key
    return stripe


def is_configured():
    """True si STRIPE_SECRET_KEY est définie et n'est pas une valeur
    placeholder — vérification de CONFIGURATION uniquement, jamais d'appel
    réseau (voir _looks_unconfigured ci-dessus, même règle que _client()).
    Utilisé par health_service.py (GET /api/health) : un health check ne
    doit jamais dépendre de la disponibilité d'un service tiers."""
    return not _looks_unconfigured(os.environ.get("STRIPE_SECRET_KEY"))


def resolve_price_id(plan):
    """Traduit un Plan (Premium/Ultra) en Price ID Stripe via les variables
    d'environnement STRIPE_PRICE_*. Ne renvoie jamais un Price ID codé en dur."""
    env_name = STRIPE_PRICES.get(plan)
    if not env_name:
        raise StripePlanUnknown(f"Plan inconnu : {plan!r}")
    price_id = os.environ.get(env_name)
    if not price_id:
        raise StripeNotConfigured(f"{env_name} n'est pas configurée sur ce serveur.")
    return price_id


def create_customer(email, name=None):
    client = _client()
    logger.info("Création d'un client Stripe pour %s", email)
    return client.Customer.create(email=email, name=name)


def get_customer(customer_id):
    client = _client()
    return client.Customer.retrieve(customer_id)


def create_checkout_session(customer_id, plan, success_url, cancel_url):
    client = _client()
    price_id = resolve_price_id(plan)
    logger.info("Création d'une Checkout Session (plan=%s, customer=%s)", plan.value, customer_id)
    return client.checkout.Session.create(
        customer=customer_id,
        mode="subscription",
        payment_method_types=["card"],
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=success_url,
        cancel_url=cancel_url,
    )


def get_checkout_session(session_id):
    client = _client()
    return client.checkout.Session.retrieve(session_id)


def get_subscription(subscription_id):
    client = _client()
    return client.Subscription.retrieve(subscription_id)


def get_payment(payment_intent_id):
    client = _client()
    return client.PaymentIntent.retrieve(payment_intent_id)


def cancel_subscription(subscription_id):
    client = _client()
    logger.info("Annulation de l'abonnement %s", subscription_id)
    return client.Subscription.cancel(subscription_id)


def change_plan(subscription_id, new_plan):
    """Change de plan immédiatement, avec proration — réservé aux upgrades
    (Premium -> Ultra). Pour un downgrade (effectif à la prochaine période de
    facturation, jamais immédiat), voir schedule_downgrade() ci-dessous."""
    client = _client()
    new_price_id = resolve_price_id(new_plan)
    subscription = client.Subscription.retrieve(subscription_id)
    item_id = subscription["items"]["data"][0]["id"]
    logger.info(
        "Changement de plan pour l'abonnement %s -> %s", subscription_id, new_plan.value
    )
    return client.Subscription.modify(
        subscription_id,
        items=[{"id": item_id, "price": new_price_id}],
        proration_behavior="create_prorations",
    )


def schedule_downgrade(subscription_id, new_plan):
    """Planifie un changement vers new_plan à la fin de la période de
    facturation en cours (jamais immédiat, contrairement à change_plan
    ci-dessus) via un Subscription Schedule Stripe : la phase courante est
    conservée telle quelle jusqu'à son terme, une seconde phase applique le
    nouveau prix ensuite. users.plan n'est mis à jour qu'au moment où Stripe
    applique réellement cette seconde phase (webhook
    customer.subscription.updated), jamais ici."""
    client = _client()
    new_price_id = resolve_price_id(new_plan)
    schedule = client.SubscriptionSchedule.create(from_subscription=subscription_id)
    current_phase = schedule["phases"][0]
    logger.info(
        "Planification d'un downgrade pour l'abonnement %s -> %s (fin de période).",
        subscription_id, new_plan.value,
    )
    return client.SubscriptionSchedule.modify(
        schedule["id"],
        phases=[
            {
                "items": current_phase["items"],
                "start_date": current_phase["start_date"],
                "end_date": current_phase["end_date"],
            },
            {"items": [{"price": new_price_id, "quantity": 1}]},
        ],
    )


def create_billing_portal_session(customer_id, return_url):
    """Crée une session du Portail client Stripe Billing pour un customer
    existant. Ne crée jamais de Customer (voir stripe_customer_id, seule
    source acceptée) : appelée uniquement pour un utilisateur qui en a
    déjà un (voir billing_service.create_portal_session)."""
    client = _client()
    logger.info("Création d'une Billing Portal Session (customer=%s)", customer_id)
    return client.billing_portal.Session.create(customer=customer_id, return_url=return_url)


def list_payment_methods(customer_id, type="card"):
    client = _client()
    return client.PaymentMethod.list(customer=customer_id, type=type)


def list_invoices(customer_id, limit=10):
    client = _client()
    return client.Invoice.list(customer=customer_id, limit=limit)


def plan_from_price_id(price_id):
    """Traduit un Price ID Stripe en Plan interne, via les mêmes variables
    d'environnement que resolve_price_id — sens inverse, utilisé pour
    interpréter les webhooks. Renvoie Plan.FREE si le Price ID ne correspond
    à aucun plan payant configuré."""
    for plan, env_name in STRIPE_PRICES.items():
        if os.environ.get(env_name) == price_id:
            return plan
    return Plan.FREE


def construct_webhook_event(payload, sig_header):
    """Vérifie la signature d'un webhook Stripe et renvoie l'événement décodé.
    Lève stripe.error.SignatureVerificationError si la signature est invalide
    (jamais de traitement d'un payload non vérifié)."""
    client = _client()
    webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET")
    if _looks_unconfigured(webhook_secret):
        raise StripeNotConfigured(
            "STRIPE_WEBHOOK_SECRET n'est pas configurée sur ce serveur "
            "(absente ou valeur placeholder de .env.example non remplacée)."
        )
    return client.Webhook.construct_event(payload, sig_header, webhook_secret)
