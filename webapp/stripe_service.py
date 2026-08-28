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


class StripePriceMismatch(Exception):
    """Levée par validate_stripe_prices() quand le montant réel d'un Price
    Stripe configuré ne correspond pas au montant attendu par NovaMath."""


# Montants attendus (centimes) — mêmes valeurs que celles affichées côté
# marketing (abonnement.html/index.html, voir tests/test_marketing_coherence.py)
# et que 6,99€/12,99€, jamais recalculées ailleurs. Aucune constante Python
# existante ne portait ces montants avant ce chantier (voir l'audit Stripe/
# SMTP, 2026-08-27, §4 : "aucune vérification que le montant Stripe
# correspond à 6,99€/12,99€") — celle-ci est la première et unique source
# pour validate_stripe_prices() ci-dessous, jamais dupliquée.
STRIPE_EXPECTED_AMOUNTS_CENTS = {
    Plan.PREMIUM: 699,
    Plan.ULTRA: 1299,
}


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


def _to_plain(obj):
    """Convertit un objet du SDK Stripe (StripeObject/ListObject/Event) en
    dict Python natif, récursivement (imbrique déjà `data.object`, `data`
    d'une liste paginée, etc. en dicts/listes natifs).

    Nécessaire car StripeObject (SDK stripe>=8) n'hérite PAS de dict et ne
    définit AUCUNE méthode `.get()` : tout `obj.get("x")` sur un objet RÉEL
    renvoyé par le SDK lève AttributeError (vérifié par un appel réel à
    l'API — voir tests/test_stripe_e2e.py). Seul l'accès par attribut
    (`obj.x`) ou par crochets (`obj["x"]`) fonctionne nativement sur ces
    objets, jamais `.get(...)` avec valeur par défaut.

    billing_service.py et stripe_webhook_service.py utilisent `.get()`
    partout (même convention que les mocks des tests unitaires, qui sont de
    simples dicts) : convertir ici, au point d'entrée unique du SDK brut,
    évite de dupliquer ce garde-fou dans chaque appelant. Aucun objet
    StripeObject brut ne doit jamais quitter ce module."""
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    return obj


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


def create_customer(email, name=None, idempotency_key=None):
    """idempotency_key doit être stable pour un même utilisateur (voir
    server.py::api_checkout_create_session, clé dérivée de user["id"]) :
    deux requêtes concurrentes (double onglet, retry réseau) envoyées avec la
    même clé sont sérialisées par Stripe lui-même, qui renvoie le MÊME
    Customer aux deux appelants au lieu d'en créer deux distincts — c'est ce
    mécanisme, pas un verrou applicatif, qui empêche les customers orphelins
    (voir audit production : race condition sur le tout premier abonnement)."""
    client = _client()
    logger.info("Création d'un client Stripe pour %s", email)
    kwargs = {"email": email, "name": name}
    if idempotency_key:
        kwargs["idempotency_key"] = idempotency_key
    return _to_plain(client.Customer.create(**kwargs))


def get_customer(customer_id):
    client = _client()
    return _to_plain(client.Customer.retrieve(customer_id))


def create_checkout_session(customer_id, plan, success_url, cancel_url, idempotency_key=None):
    """idempotency_key : voir create_customer ci-dessus pour le mécanisme.
    Contrairement à celle du customer (stable indéfiniment), la clé passée
    ici par server.py inclut une fenêtre de temps courte (quelques dizaines
    de secondes) : elle absorbe un double-clic/double-onglet/retry sans
    empêcher un utilisateur légitime de relancer un paiement plus tard."""
    client = _client()
    price_id = resolve_price_id(plan)
    logger.info("Création d'une Checkout Session (plan=%s, customer=%s)", plan.value, customer_id)
    kwargs = dict(
        customer=customer_id,
        mode="subscription",
        payment_method_types=["card"],
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=success_url,
        cancel_url=cancel_url,
    )
    if idempotency_key:
        kwargs["idempotency_key"] = idempotency_key
    return _to_plain(client.checkout.Session.create(**kwargs))


def get_checkout_session(session_id):
    client = _client()
    return _to_plain(client.checkout.Session.retrieve(session_id))


def get_subscription(subscription_id):
    client = _client()
    return _to_plain(client.Subscription.retrieve(subscription_id))


def get_payment(payment_intent_id):
    client = _client()
    return _to_plain(client.PaymentIntent.retrieve(payment_intent_id))


def cancel_subscription(subscription_id):
    client = _client()
    logger.info("Annulation de l'abonnement %s", subscription_id)
    return _to_plain(client.Subscription.cancel(subscription_id))


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
    return _to_plain(client.Subscription.modify(
        subscription_id,
        items=[{"id": item_id, "price": new_price_id}],
        proration_behavior="create_prorations",
    ))


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
    return _to_plain(client.SubscriptionSchedule.modify(
        schedule["id"],
        phases=[
            {
                "items": current_phase["items"],
                "start_date": current_phase["start_date"],
                "end_date": current_phase["end_date"],
            },
            {"items": [{"price": new_price_id, "quantity": 1}]},
        ],
    ))


def create_billing_portal_session(customer_id, return_url):
    """Crée une session du Portail client Stripe Billing pour un customer
    existant. Ne crée jamais de Customer (voir stripe_customer_id, seule
    source acceptée) : appelée uniquement pour un utilisateur qui en a
    déjà un (voir billing_service.create_portal_session)."""
    client = _client()
    logger.info("Création d'une Billing Portal Session (customer=%s)", customer_id)
    return _to_plain(client.billing_portal.Session.create(customer=customer_id, return_url=return_url))


def list_payment_methods(customer_id, type="card"):
    client = _client()
    return _to_plain(client.PaymentMethod.list(customer=customer_id, type=type))


def list_invoices(customer_id, limit=10):
    client = _client()
    return _to_plain(client.Invoice.list(customer=customer_id, limit=limit))


def plan_from_price_id(price_id):
    """Traduit un Price ID Stripe en Plan interne, via les mêmes variables
    d'environnement que resolve_price_id — sens inverse, utilisé pour
    interpréter les webhooks. Renvoie Plan.FREE si le Price ID ne correspond
    à aucun plan payant configuré."""
    for plan, env_name in STRIPE_PRICES.items():
        if os.environ.get(env_name) == price_id:
            return plan
    return Plan.FREE


def validate_stripe_prices():
    """Vérifie que les Price Stripe réellement configurés (STRIPE_PRICE_PREMIUM/
    STRIPE_PRICE_ULTRA) ont bien le montant attendu (STRIPE_EXPECTED_AMOUNTS_CENTS
    ci-dessus) — appel réel à l'API Stripe (Price.retrieve), jamais un montant
    supposé depuis la configuration locale.

    Vérification EXPLICITE, à invoquer à la demande (script d'exploitation
    avant mise en production, suite E2E) — JAMAIS câblée au démarrage du
    serveur ni à un health check : même principe déjà établi ailleurs dans le
    projet (voir health_service.py::check_stripe_configured/
    check_smtp_configured, dont la docstring exclut explicitement tout appel
    réseau — "un health check ne doit jamais dépendre de la disponibilité
    d'un service tiers"). Cette fonction ne doit donc jamais faire échouer le
    démarrage d'un environnement où Stripe est momentanément injoignable.

    Renvoie silencieusement (None) si Stripe n'est pas configuré — même
    politique que is_configured() ailleurs dans ce module : ne doit jamais
    être la raison pour laquelle un environnement de développement sans
    Stripe configuré échoue.

    Lève StripePriceMismatch si un montant ne correspond pas (message
    d'erreur : Price ID concerné + montants attendu/réel, jamais la clé API
    ni aucun secret — un Price ID est un identifiant public, déjà visible
    dans .env.example et le Dashboard Stripe). Laisse remonter tel quel
    stripe.error.StripeError si le Price ID configuré n'existe pas/est
    invalide côté Stripe (ex: InvalidRequestError) — jamais absorbée ni
    reformulée, cohérent avec le traitement des erreurs Stripe partout
    ailleurs dans ce module (voir server.py, qui catch déjà stripe.error.
    StripeError autour des appels à ce module).

    Ne modifie et ne crée jamais de Price Stripe — lecture seule."""
    if not is_configured():
        return
    client = _client()
    for plan, expected_cents in STRIPE_EXPECTED_AMOUNTS_CENTS.items():
        price_id = resolve_price_id(plan)
        price = _to_plain(client.Price.retrieve(price_id))
        actual_cents = price.get("unit_amount")
        if actual_cents != expected_cents:
            raise StripePriceMismatch(
                f"Price Stripe {price_id!r} (plan {plan.value}) a un montant de "
                f"{actual_cents!r} centimes, attendu {expected_cents} centimes."
            )


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
    event = client.Webhook.construct_event(payload, sig_header, webhook_secret)
    # BUG CRITIQUE corrigé ici (vérifié par un appel réel signé avec le vrai
    # STRIPE_WEBHOOK_SECRET) : l'Event retourné par le SDK est un objet
    # StripeObject réel, PAS un dict — stripe_webhook_service.handle_event
    # (et tous ses handlers _handle_*) appellent event.get(...)/obj.get(...)
    # partout, ce qui lève AttributeError sur un objet StripeObject réel (il
    # n'hérite pas de dict, aucune méthode .get() définie). Sans cette
    # conversion, TOUT webhook Stripe réel reçu en production ferait
    # planter le traitement dès la première ligne de handle_event().
    return _to_plain(event)
