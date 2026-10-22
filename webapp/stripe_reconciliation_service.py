"""
Réconciliation Stripe <-> base Mathadap, en LECTURE SEULE — audit admin
(2026-10-20), point 2.

Ce module ne modifie JAMAIS la base ni Stripe : il compare, pour chaque
compte ayant un `stripe_subscription_id`, le `stripe_subscription_status`
stocké localement (mis à jour UNIQUEMENT par un webhook déjà reçu, voir
stripe_webhook_service.py) au statut RÉEL renvoyé par Stripe
(stripe_service.get_subscription -> Subscription.retrieve, un appel de
LECTURE côté API Stripe). Une divergence signifie qu'un webhook a été
manqué, retardé, ou que l'abonnement a été modifié directement dans le
Dashboard Stripe sans jamais déclencher de webhook reçu par Mathadap.

Déclenchement : EXCLUSIVEMENT manuel (route POST dédiée, voir server.py),
jamais une tâche planifiée/un cron — décision volontaire de ce chantier,
l'activation automatique d'un job périodique nécessiterait une validation
produit séparée (fréquence, alerting, volumétrie réelle en production).

Séparation test/production : une clé sk_test_... ne peut de toute façon
renvoyer que des objets Stripe du bac à sable (garantie du SDK Stripe
lui-même), donc une réconciliation lancée avec une clé de test ne touche
jamais d'abonnements réels — aucune protection supplémentaire nécessaire
dans ce cas. Le mode courant (stripe_service.operating_mode()) est reporté
dans le résultat pour que l'admin sache sur quel environnement le rapport
porte.

Garde-fou PRODUCTION (ajouté le 2026-10-20, suite à un incident réel) :
une vérification manuelle de ce module, depuis un poste de développement
local dont le `.env` contenait par erreur une vraie clé `sk_live_...`, a
déclenché 50 appels réels (lecture seule, mais réels) vers l'API Stripe de
PRODUCTION. Aucune donnée n'a été modifiée (ce module ne fait que des
`Subscription.retrieve`), mais rien n'empêchait ce scénario avant cette
correction. Deux niveaux de protection, tous deux appliqués ICI (jamais
seulement côté interface — un appel direct à la route HTTP doit être
bloqué de la même façon, voir tests/test_stripe_reconciliation_service.py) :

1. Blocage DUR, non contournable, si Stripe est en mode "production" (clé
   sk_live_...) alors que ce serveur tourne en environnement non-production
   (`config.IS_PRODUCTION` est False, c-à-d FLASK_ENV != "production") : un
   serveur de développement local n'a AUCUNE raison légitime d'appeler
   Stripe production. Aucun paramètre ne permet de contourner ce cas.
2. Confirmation EXPLICITE obligatoire (`confirmed=True`) si Stripe est en
   mode "production" ET que ce serveur tourne bien en production — pour
   qu'une réconciliation touchant de vrais abonnements reste un geste
   volontaire, jamais le comportement par défaut d'un bouton.

Le mode "test" et le mode "etat_inconnu" ne déclenchent aucune de ces deux
protections (voir point 1 ci-dessus pour "test" ; "etat_inconnu" est déjà
signalé ailleurs dans l'admin comme un état à corriger, mais ne peut par
construction pas être une clé sk_live_ valide).
"""
import logging

import config
import db
import stripe_service

logger = logging.getLogger("stripe_reconciliation_service")

# Nombre d'appels Stripe par exécution manuelle — pagination volontaire
# plutôt qu'un lot unique illimité, pour rester sous les limites de fréquence
# Stripe (100 req/s en production, nettement moins en mode test) même sur une
# base de plusieurs milliers d'abonnés, et pour qu'un échec réseau n'oblige
# jamais à tout relancer depuis le début (voir `offset`).
DEFAULT_BATCH_SIZE = 50


class StripeReconciliationUnavailable(Exception):
    """Levée si Stripe n'est pas configuré — jamais un crash silencieux ni
    un rapport vide trompeur (voir server.py pour la réponse HTTP associée,
    501 comme le reste des routes Stripe non configurées)."""


class StripeReconciliationBlocked(Exception):
    """Levée quand Stripe est en mode PRODUCTION alors que ce serveur ne
    tourne pas en environnement de production (`config.IS_PRODUCTION` est
    False) — blocage DUR, sans paramètre de contournement : voir l'incident
    décrit en tête de ce module. server.py répond 403."""


class StripeReconciliationConfirmationRequired(Exception):
    """Levée quand Stripe est en mode PRODUCTION et que ce serveur tourne
    bien en production, mais que l'appelant n'a pas encore passé
    `confirmed=True` — server.py répond 409 (action possible, mais pas
    encore confirmée explicitement)."""


def reconcile(limit=DEFAULT_BATCH_SIZE, offset=0, confirmed=False):
    """Lecture seule, un lot à la fois. Renvoie :
        {
            "mode": "test"|"production"|"etat_inconnu",
            "checked": nombre de comptes réellement interrogés dans ce lot,
            "total": nombre total de comptes à stripe_subscription_id non-nul,
            "has_more": True si un prochain appel avec offset+limit a du sens,
            "divergences": [{"user_id", "email", "stripe_subscription_id",
                              "local_status", "stripe_status"}, ...],
            "errors": [{"user_id", "stripe_subscription_id", "error"}, ...],
        }
    Une erreur réseau/Stripe sur UN compte n'interrompt jamais le reste du
    lot (voir `errors`, jamais une exception qui ferait perdre tout le lot
    pour un seul abonnement introuvable/réseau indisponible)."""
    mode = stripe_service.operating_mode()
    if mode == "non_configure":
        raise StripeReconciliationUnavailable(
            "Stripe n'est pas configuré (STRIPE_SECRET_KEY absente ou valeur "
            "placeholder) — aucune réconciliation possible."
        )

    if mode == "production":
        if not config.IS_PRODUCTION:
            raise StripeReconciliationBlocked(
                "Stripe est configuré en mode PRODUCTION mais ce serveur tourne "
                "en environnement de développement (FLASK_ENV != 'production') — "
                "la réconciliation est bloquée pour éviter tout appel réel vers "
                "Stripe production depuis un poste local. Vérifie STRIPE_SECRET_KEY "
                "dans ce .env si ce n'est pas volontaire."
            )
        if not confirmed:
            raise StripeReconciliationConfirmationRequired(
                "Confirmation explicite requise avant de lancer une réconciliation "
                "contre Stripe en mode PRODUCTION (de vrais abonnements seront lus)."
            )

    total = db.count_users_with_stripe_subscription()
    users = db.list_users_with_stripe_subscription(limit=limit, offset=offset)

    divergences = []
    errors = []
    for user in users:
        sub_id = user["stripe_subscription_id"]
        local_status = user["stripe_subscription_status"]
        try:
            remote = stripe_service.get_subscription(sub_id)
        except Exception as exc:  # StripeError (introuvable, réseau, auth) — jamais fatal pour le lot
            logger.warning(
                "Réconciliation Stripe : échec pour user_id=%s subscription_id=%s (%s)",
                user["id"], sub_id, exc,
            )
            errors.append({
                "user_id": user["id"],
                "stripe_subscription_id": sub_id,
                "error": str(exc),
            })
            continue

        remote_status = remote.get("status")
        if remote_status != local_status:
            divergences.append({
                "user_id": user["id"],
                "email": user["email"],
                "stripe_subscription_id": sub_id,
                "local_status": local_status,
                "stripe_status": remote_status,
            })

    return {
        "mode": mode,
        "checked": len(users),
        "total": total,
        "has_more": offset + len(users) < total,
        "divergences": divergences,
        "errors": errors,
    }
