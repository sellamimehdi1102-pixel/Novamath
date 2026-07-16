"""
Traitement des événements webhook Stripe : toute la logique métier (quel
événement met à jour quoi en base, idempotence, journalisation) vit ici.

Séparation des responsabilités :
- webapp/stripe_service.py    : appels au SDK Stripe (création de client,
  Checkout Session, vérification de signature...), aucune logique métier.
- webapp/stripe_webhook_service.py (ce module) : que faire d'un événement une
  fois reçu et sa signature vérifiée — aucun appel HTTP entrant/sortant côté
  Flask, aucune notion de requête/réponse.
- webapp/server.py            : la route /api/checkout/webhook se limite à
  vérifier la signature (via stripe_service) puis délègue entièrement à
  handle_event() ci-dessous. Aucune logique métier n'y reste.

Idempotence : chaque event.id Stripe n'est traité qu'une seule fois (table
stripe_webhook_events, voir db.py) — Stripe redélivre parfois le même
événement (retry réseau, redélivraison manuelle depuis le Dashboard), et le
traiter deux fois ne doit jamais dupliquer un effet de bord.
"""
import logging

import db
import stripe_service
from plan_service import Plan

logger = logging.getLogger("stripe_webhook_service")

# Statuts Stripe pour lesquels l'abonnement est considéré actif côté NovaMath.
_ACTIVE_STATUSES = ("active", "trialing")


def _user_for_customer(customer_id):
    if not customer_id:
        logger.warning("Webhook Stripe : événement sans customer_id, ignoré.")
        return None
    user = db.get_user_by_stripe_customer_id(customer_id)
    if user is None:
        logger.warning("Webhook Stripe : aucun utilisateur NovaMath pour le customer %s.", customer_id)
    return user


def sync_subscription(user, subscription_obj):
    """Aligne stripe_subscription_id/plan/status sur l'état réel de l'objet
    Subscription Stripe reçu (source de vérité). N'écrit qu'un Plan.value en
    base : ce module se contente d'enregistrer le fait Stripe, il ne décide
    d'aucun accès (voir plan_service.py, qui lira cette même colonne)."""
    subscription_id = subscription_obj.get("id")
    status = subscription_obj.get("status", "active")
    price_id = subscription_obj["items"]["data"][0]["price"]["id"]
    plan = stripe_service.plan_from_price_id(price_id) if status in _ACTIVE_STATUSES else Plan.FREE
    db.set_stripe_subscription(user["id"], subscription_id, plan.value, status)
    logger.info(
        "Abonnement synchronisé pour l'utilisateur %s : plan=%s status=%s", user["id"], plan.value, status
    )


def _handle_checkout_session_completed(obj):
    user = _user_for_customer(obj.get("customer"))
    subscription_id = obj.get("subscription")
    if not user or not subscription_id:
        return
    subscription = stripe_service.get_subscription(subscription_id)
    sync_subscription(user, subscription)
    db.log_security_event("stripe_checkout_completed", user_id=user["id"])


def _handle_subscription_created(obj):
    user = _user_for_customer(obj.get("customer"))
    if not user:
        return
    sync_subscription(user, obj)
    db.log_security_event("stripe_subscription_created", user_id=user["id"])


def _handle_subscription_updated(obj):
    user = _user_for_customer(obj.get("customer"))
    if not user:
        return
    sync_subscription(user, obj)
    db.log_security_event("stripe_subscription_updated", user_id=user["id"])


def _handle_subscription_deleted(obj):
    user = _user_for_customer(obj.get("customer"))
    if not user:
        return
    db.set_stripe_subscription(user["id"], None, Plan.FREE.value, "canceled")
    logger.info("Abonnement supprimé pour l'utilisateur %s, retour au plan free.", user["id"])
    db.log_security_event("stripe_subscription_deleted", user_id=user["id"])


def _handle_invoice_paid(obj):
    user = _user_for_customer(obj.get("customer"))
    if not user:
        return
    subscription_id = obj.get("subscription")
    if subscription_id:
        subscription = stripe_service.get_subscription(subscription_id)
        sync_subscription(user, subscription)
    db.log_security_event("stripe_invoice_paid", user_id=user["id"])


def _handle_invoice_payment_failed(obj):
    user = _user_for_customer(obj.get("customer"))
    if not user:
        return
    # Ne touche pas à plan/stripe_subscription_id : Stripe retente
    # automatiquement le paiement avant d'annuler réellement l'abonnement
    # (ce qui déclenchera customer.subscription.deleted/updated séparément).
    db.set_stripe_subscription_status(user["id"], "past_due")
    logger.warning(
        "Paiement en échec pour l'utilisateur %s (invoice %s).", user["id"], obj.get("id")
    )
    db.log_security_event("stripe_invoice_payment_failed", user_id=user["id"])


# Un seul point de vérité pour la liste des événements gérés — ajouter un
# événement Stripe supplémentaire se limite à ajouter une entrée ici et une
# fonction _handle_xxx(obj), sans toucher au reste (idempotence, logs, route).
EVENT_HANDLERS = {
    "checkout.session.completed": _handle_checkout_session_completed,
    "invoice.paid": _handle_invoice_paid,
    "invoice.payment_failed": _handle_invoice_payment_failed,
    "customer.subscription.created": _handle_subscription_created,
    "customer.subscription.updated": _handle_subscription_updated,
    "customer.subscription.deleted": _handle_subscription_deleted,
}


def handle_event(event):
    """Point d'entrée unique appelé par la route webhook une fois la signature
    vérifiée. Idempotent : un event.id déjà traité est ignoré sans relancer la
    logique métier. Les erreurs de traitement (ex: appel Stripe API en échec)
    ne sont pas absorbées ici : elles remontent à l'appelant, qui doit
    répondre par un code d'erreur pour que Stripe redélivre l'événement plus
    tard (l'événement n'est marqué "traité" qu'après un handler réussi)."""
    event_id = event.get("id")
    event_type = event.get("type")

    if event_id and db.has_processed_stripe_event(event_id):
        logger.info("Webhook Stripe %s (%s) déjà traité, ignoré (idempotence).", event_id, event_type)
        return {"received": True, "status": "duplicate_ignored"}

    handler = EVENT_HANDLERS.get(event_type)
    if handler is None:
        logger.info("Webhook Stripe %s : type %s non géré, ignoré.", event_id, event_type)
        status = "ignored"
    else:
        logger.info("Traitement du webhook Stripe %s (%s).", event_id, event_type)
        obj = event.get("data", {}).get("object", {})
        handler(obj)
        status = "processed"

    if event_id:
        db.mark_stripe_event_processed(event_id, event_type)

    return {"received": True, "status": status}
