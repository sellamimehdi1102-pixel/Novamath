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
from plan_service import Plan, get_plan

logger = logging.getLogger("stripe_webhook_service")

# Statuts Stripe pour lesquels l'abonnement est considéré actif côté NovaMath.
_ACTIVE_STATUSES = ("active", "trialing")

# Chantier "Robustesse Stripe" (2026-08-27) : statuts de RELANCE (dunning) —
# Stripe retente encore automatiquement le paiement, l'abonnement n'est PAS
# résilié. Le plan payant DOIT être conservé pendant cette fenêtre (voir
# _handle_invoice_payment_failed ci-dessous, qui a toujours eu ce
# comportement pour ce même scénario) — avant ce chantier, sync_subscription()
# le contredisait en rétrogradant vers Free dès qu'un customer.subscription.
# updated arrivait avec ce statut (Stripe envoie ce webhook en même temps
# qu'invoice.payment_failed lors d'un échec de renouvellement).
#
# "unpaid" est volontairement EXCLU de cet ensemble : contrairement à
# past_due (relance en cours), unpaid signifie que les relances Stripe sont
# épuisées sans résiliation formelle — un état plus définitif, plus proche
# d'un abonnement à considérer comme non honoré. Rien dans l'architecture
# existante ne justifiait de l'inclure dans la fenêtre de grâce ; le
# comportement de rétrogradation existant est donc conservé pour ce statut,
# documenté explicitement ici plutôt que supposé.
_GRACE_STATUSES = ("past_due",)


def _user_for_customer(customer_id):
    if not customer_id:
        logger.warning("Webhook Stripe : événement sans customer_id, ignoré.")
        return None
    user = db.get_user_by_stripe_customer_id(customer_id)
    if user is None:
        # error (pas warning) : depuis l'ajout des idempotency keys sur
        # Customer.create (voir stripe_service.py::create_customer), un
        # customer_id introuvable ne devrait plus jamais se produire pour un
        # checkout créé par NovaMath — s'il apparaît malgré tout, c'est un
        # vrai incident à investiguer (compte supprimé manuellement, customer
        # créé hors de ce flux...), pas un cas attendu à absorber en silence.
        # customer_id est la clé de corrélation utilisable dans le Dashboard
        # Stripe pour retrouver l'événement exact.
        logger.error(
            "Webhook Stripe : aucun utilisateur NovaMath pour le customer %s — "
            "événement définitivement perdu (Stripe ne redélivre pas un event déjà marqué traité).",
            customer_id,
        )
    return user


def sync_subscription(user, subscription_obj):
    """Aligne stripe_subscription_id/plan/status sur l'état réel de l'objet
    Subscription Stripe reçu (source de vérité). N'écrit qu'un Plan.value en
    base : ce module se contente d'enregistrer le fait Stripe, il ne décide
    d'aucun accès (voir plan_service.py, qui lira cette même colonne).

    Statut de relance (_GRACE_STATUSES, ex: past_due) : le plan n'est jamais
    recalculé depuis price_id ni forcé à Free — celui déjà en base pour cet
    utilisateur (plan_service.get_plan, lu AVANT cette écriture) est
    conservé tel quel, seul `status` change. Mêmes intention et garantie que
    _handle_invoice_payment_failed ci-dessous pour ce même scénario."""
    subscription_id = subscription_obj.get("id")
    status = subscription_obj.get("status", "active")
    price_id = subscription_obj["items"]["data"][0]["price"]["id"]
    if status in _ACTIVE_STATUSES:
        plan = stripe_service.plan_from_price_id(price_id)
    elif status in _GRACE_STATUSES:
        plan = get_plan(user)
    else:
        plan = Plan.FREE
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
    deleted_subscription_id = obj.get("id")
    current_subscription_id = user.get("stripe_subscription_id")
    # Stripe ne garantit pas l'ordre de livraison des webhooks (retries,
    # redélivraison manuelle depuis le Dashboard). Si l'utilisateur a déjà un
    # AUTRE abonnement actif en base (ex: il s'est ré-abonné entre l'annulation
    # de l'ancien et la livraison tardive de cet événement "deleted"), ce
    # webhook concerne un abonnement obsolète : l'ignorer plutôt que de
    # rétrograder à tort un abonné qui paie actuellement.
    if (
        current_subscription_id
        and deleted_subscription_id
        and current_subscription_id != deleted_subscription_id
    ):
        logger.info(
            "Webhook Stripe subscription.deleted (%s) ignoré pour l'utilisateur %s : "
            "un abonnement plus récent (%s) est actif en base.",
            deleted_subscription_id, user["id"], current_subscription_id,
        )
        db.log_security_event("stripe_subscription_deleted_stale_ignored", user_id=user["id"])
        return
    db.set_stripe_subscription(user["id"], None, Plan.FREE.value, "canceled")
    logger.info("Abonnement supprimé pour l'utilisateur %s, retour au plan free.", user["id"])
    db.log_security_event("stripe_subscription_deleted", user_id=user["id"])


def _invoice_subscription_id(obj):
    """ID de l'abonnement associé à une Invoice. Depuis l'API Stripe "Basil"
    (2025-03-31, support de plusieurs paiements partiels sur une facture,
    vérifié par un appel réel), `invoice.subscription` est toujours None :
    l'ID vit désormais sous `invoice.parent.subscription_details.subscription`.
    Repli sur l'ancien champ racine pour rester compatible avec un compte
    Stripe encore épinglé sur une version d'API antérieure à Basil (aucune
    version n'est épinglée explicitement dans ce projet, voir stripe_service.py)."""
    legacy = obj.get("subscription")
    if legacy:
        return legacy
    parent = obj.get("parent") or {}
    return (parent.get("subscription_details") or {}).get("subscription")


def _handle_invoice_paid(obj):
    user = _user_for_customer(obj.get("customer"))
    if not user:
        return
    subscription_id = _invoice_subscription_id(obj)
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


# ── Événements du cycle de vie complémentaires ────────────────────────────────
# Aucun de ces événements ne modifie plan/stripe_subscription_id/status : ils
# ne font que journaliser un fait Stripe (facture, moyen de paiement, essai,
# session expirée) déjà consultable en direct depuis Stripe via
# billing_service.get_billing_status — pas de duplication de cet état en
# base. invoice.payment_succeeded est l'exception : Stripe l'envoie en plus
# (ou à la place, selon la configuration du compte) d'invoice.paid pour un
# paiement réussi, donc il resynchronise le plan de la même façon.
def _handle_invoice_finalized(obj):
    user = _user_for_customer(obj.get("customer"))
    if not user:
        return
    logger.info("Facture finalisée pour l'utilisateur %s (invoice %s).", user["id"], obj.get("id"))
    db.log_security_event("stripe_invoice_finalized", user_id=user["id"])


def _handle_invoice_upcoming(obj):
    user = _user_for_customer(obj.get("customer"))
    if not user:
        return
    logger.info("Facture à venir pour l'utilisateur %s.", user["id"])
    db.log_security_event("stripe_invoice_upcoming", user_id=user["id"])


def _handle_subscription_trial_will_end(obj):
    user = _user_for_customer(obj.get("customer"))
    if not user:
        return
    logger.info("Fin d'essai imminente pour l'utilisateur %s.", user["id"])
    db.log_security_event("stripe_trial_will_end", user_id=user["id"])


def _handle_checkout_session_expired(obj):
    user = _user_for_customer(obj.get("customer"))
    if not user:
        return
    logger.info("Session de paiement expirée pour l'utilisateur %s.", user["id"])
    db.log_security_event("stripe_checkout_expired", user_id=user["id"])


def _handle_payment_method_attached(obj):
    user = _user_for_customer(obj.get("customer"))
    if not user:
        return
    logger.info("Moyen de paiement ajouté pour l'utilisateur %s.", user["id"])
    db.log_security_event("stripe_payment_method_attached", user_id=user["id"])


def _handle_payment_method_updated(obj):
    user = _user_for_customer(obj.get("customer"))
    if not user:
        return
    logger.info("Moyen de paiement mis à jour pour l'utilisateur %s.", user["id"])
    db.log_security_event("stripe_payment_method_updated", user_id=user["id"])


def _handle_payment_method_detached(obj):
    # Un PaymentMethod détaché n'a plus de customer associé (c'est justement
    # ce que "detached" signifie côté Stripe) : aucun utilisateur NovaMath
    # fiable à résoudre ici, on se limite à journaliser l'événement lui-même.
    logger.info("Moyen de paiement détaché (payment_method=%s).", obj.get("id"))


# Un seul point de vérité pour la liste des événements gérés — ajouter un
# événement Stripe supplémentaire se limite à ajouter une entrée ici et une
# fonction _handle_xxx(obj), sans toucher au reste (idempotence, logs, route).
EVENT_HANDLERS = {
    "checkout.session.completed": _handle_checkout_session_completed,
    "invoice.paid": _handle_invoice_paid,
    "invoice.payment_succeeded": _handle_invoice_paid,
    "invoice.payment_failed": _handle_invoice_payment_failed,
    "invoice.finalized": _handle_invoice_finalized,
    "invoice.upcoming": _handle_invoice_upcoming,
    "customer.subscription.created": _handle_subscription_created,
    "customer.subscription.updated": _handle_subscription_updated,
    "customer.subscription.deleted": _handle_subscription_deleted,
    "customer.subscription.trial_will_end": _handle_subscription_trial_will_end,
    "checkout.session.expired": _handle_checkout_session_expired,
    "payment_method.attached": _handle_payment_method_attached,
    "payment_method.updated": _handle_payment_method_updated,
    "payment_method.detached": _handle_payment_method_detached,
}


def handle_event(event):
    """Point d'entrée unique appelé par la route webhook une fois la signature
    vérifiée. Idempotent : un event.id déjà traité est ignoré sans relancer la
    logique métier. Les erreurs de traitement (ex: appel Stripe API en échec)
    ne sont pas absorbées ici : elles remontent à l'appelant, qui doit
    répondre par un code d'erreur pour que Stripe redélivre l'événement plus
    tard.

    L'event_id est réservé (mark_stripe_event_processed) AVANT l'exécution du
    handler, jamais après : si deux livraisons quasi simultanées du même
    event_id arrivent en parallèle (retry réseau Stripe qui chevauche la
    requête initiale encore en cours de traitement), seule la première à
    committer son INSERT obtient le droit d'exécuter le handler — l'autre le
    voit déjà réservé et s'arrête immédiatement en "duplicate_ignored", sans
    jamais exécuter le handler deux fois. Si le handler lève, la réservation
    est annulée (unmark_stripe_event_processed) pour que la redélivrance
    Stripe suivante retraite réellement l'événement au lieu de le voir comme
    un doublon fantôme.

    La réservation n'est marquée "complétée" (mark_stripe_event_completed)
    qu'une fois le traitement réellement terminé (handler exécuté avec succès,
    ou aucun handler à exécuter). Tant qu'elle ne l'est pas, mark_stripe_event_
    processed() la considère "en cours" : si le process est tué avant d'y
    arriver (SIGKILL, restart Fly.io — donc AUCUNE des deux lignes ci-dessous
    ne s'exécute, ni le except ni le mark_completed), elle reste réservée mais
    jamais complétée. Passé STRIPE_WEBHOOK_CLAIM_TIMEOUT_SECONDS, un retry
    Stripe de ce même event_id est alors autorisé à re-réserver et retraiter
    réellement l'événement, au lieu de rester bloqué en doublon fantôme pour
    toujours (voir db.mark_stripe_event_processed)."""
    event_id = event.get("id")
    event_type = event.get("type")

    if event_id:
        newly_reserved = db.mark_stripe_event_processed(event_id, event_type)
        if not newly_reserved:
            logger.info("Webhook Stripe %s (%s) déjà traité, ignoré (idempotence).", event_id, event_type)
            return {"received": True, "status": "duplicate_ignored"}

    handler = EVENT_HANDLERS.get(event_type)
    if handler is None:
        logger.info("Webhook Stripe %s : type %s non géré, ignoré.", event_id, event_type)
        if event_id:
            db.mark_stripe_event_completed(event_id)
        return {"received": True, "status": "ignored"}

    logger.info("Traitement du webhook Stripe %s (%s).", event_id, event_type)
    obj = event.get("data", {}).get("object", {})
    try:
        handler(obj)
    except Exception:
        if event_id:
            db.unmark_stripe_event_processed(event_id)
        raise

    if event_id:
        db.mark_stripe_event_completed(event_id)
    return {"received": True, "status": "processed"}
