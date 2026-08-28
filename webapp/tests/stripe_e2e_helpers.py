"""
Infrastructure partagée par la suite E2E Stripe (test_stripe_e2e.py).

JAMAIS un service applicatif : vit dans tests/, jamais importé par le code
de production (webapp/stripe_service.py, stripe_webhook_service.py,
billing_service.py restent inchangés — voir leurs suites de tests existantes
pour la couverture par mocks, complémentaire, jamais dupliquée ici).

Toutes les clés proviennent de `config.py` (webapp/config.py), jamais codées
en dur, jamais lues une seconde fois depuis os.environ ici.

Garde-fou de sécurité : cette suite REFUSE de s'exécuter contre autre chose
qu'une clé Stripe Test Mode (`sk_test_...`) — jamais `sk_live_`, quelle que
soit la configuration de l'environnement où elle tourne. Se désactive
proprement (skip, jamais une erreur) si aucune clé Stripe Test Mode valide
et réellement joignable n'est configurée.

Moyens de paiement de test officiels Stripe (https://docs.stripe.com/testing)
utilisés ici — jamais un numéro de carte réel, jamais une carte inventée :
`pm_card_visa` (paiement toujours accepté), `pm_card_chargeDeclined`/
`pm_card_chargeDeclinedInsufficientFunds`/`pm_card_chargeDeclinedExpiredCard`
(refus réel, déclenché côté serveur Stripe Test Mode — jamais simulé
localement). La page Checkout hébergée (webapp/stripe_service.py::
create_checkout_session) n'est volontairement pas pilotée par un navigateur
automatisé ici (Stripe documente explicitement que Checkout n'est pas conçu
pour être scripté) : un abonnement créé directement via l'API avec un de ces
moyens de paiement de test produit exactement le même graphe d'objets réels
(Subscription + Invoice + PaymentIntent) qu'un Checkout complété avec
succès — c'est cet objet réel qui est testé, jamais un objet inventé.
"""
import time
import unittest

import stripe

import config
import stripe_service

REASON = "indisponible"


def _looks_like_test_key(key):
    return bool(key) and key.startswith("sk_test_")


def _detect_e2e_availability():
    global REASON
    if not _looks_like_test_key(config.STRIPE_SECRET_KEY):
        REASON = (
            "STRIPE_SECRET_KEY absente ou n'est pas une clé Stripe Test Mode "
            "(doit commencer par sk_test_) — voir DEPLOYMENT.md, section Tests E2E Stripe."
        )
        return False
    if not config.STRIPE_PRICE_PREMIUM or not config.STRIPE_PRICE_ULTRA:
        REASON = "STRIPE_PRICE_PREMIUM/STRIPE_PRICE_ULTRA absentes (Price ID Test Mode requis)."
        return False
    if not config.STRIPE_WEBHOOK_SECRET or config.STRIPE_WEBHOOK_SECRET == "whsec_xxx":
        REASON = "STRIPE_WEBHOOK_SECRET absente ou valeur placeholder (voir `stripe listen`, DEPLOYMENT.md)."
        return False
    try:
        stripe.api_key = config.STRIPE_SECRET_KEY
        # Appel réel, minimal : confirme une clé valide et le réseau Stripe
        # joignable, sans créer la moindre ressource.
        stripe.Balance.retrieve()
    except Exception as exc:  # jamais un test qui plante : un skip explicite
        REASON = f"Serveur Stripe Test Mode injoignable ou clé invalide : {exc}"
        return False
    return True


E2E_AVAILABLE = _detect_e2e_availability()

skip_unless_e2e = unittest.skipUnless(E2E_AVAILABLE, REASON)

# ── Moyens de paiement de test officiels Stripe (jamais une carte réelle) ──
CARD_VISA_SUCCESS = "pm_card_visa"

# pm_card_chargeDeclined / pm_card_chargeDeclinedInsufficientFunds /
# pm_card_chargeDeclinedExpiredCard existent bien côté Stripe mais NE
# PEUVENT PAS être attachées à un Customer (vérifié par un appel réel :
# PaymentMethod.attach lève CardError "Your card was declined." immédiatement,
# avant même la création de l'abonnement) — Stripe documente explicitement
# "You can't attach cards that simulate issuer declines to a Customer
# object." (https://docs.stripe.com/testing). Seule pm_card_chargeCustomerFail
# est conçue pour ce scénario précis : l'attach réussit, mais toute tentative
# de facturation échoue ensuite — c'est le seul moyen officiellement supporté
# de tester un abonnement (qui exige un moyen de paiement déjà attaché) dont
# le paiement échoue. Stripe n'offrant qu'un seul token "attach puis échec"
# (pas de distinction insuffisant/expiré au niveau attach), les trois
# constantes ci-dessous partagent volontairement la même valeur réelle — leurs
# noms distincts documentent l'intention du scénario testé côté NovaMath,
# jamais un comportement Stripe différent.
CARD_DECLINED = "pm_card_chargeCustomerFail"
CARD_DECLINED_INSUFFICIENT_FUNDS = "pm_card_chargeCustomerFail"
CARD_DECLINED_EXPIRED = "pm_card_chargeCustomerFail"


def unique_email(prefix="e2e"):
    return f"{prefix}-{int(time.time() * 1_000_000)}@example.com"


def create_test_customer(email=None, test_clock=None):
    """Client Stripe réel (Test Mode) — jamais un objet simulé. `test_clock`
    (optionnel) attache le client à une horloge de test (voir
    create_test_clock ci-dessous) pour les scénarios de renouvellement/
    expiration qui nécessitent de faire avancer le temps Stripe. Passe par
    stripe_service.create_customer() (jamais un appel Stripe dupliqué) pour
    le cas simple ; `test_clock` nécessite un paramètre que cette fonction
    ne supporte pas, d'où l'appel direct au SDK dans ce seul cas."""
    stripe.api_key = config.STRIPE_SECRET_KEY
    email = email or unique_email()
    if test_clock:
        # Appel SDK direct (stripe_service.create_customer ne supporte pas
        # test_clock) : converti en dict comme stripe_service._to_plain
        # (voir sa docstring) pour que .get() se comporte comme sur le
        # retour du cas simple ci-dessous, exactement comme un appelant
        # passant par stripe_service.py en recevrait un.
        return stripe_service._to_plain(stripe.Customer.create(email=email, name="NovaMath E2E", test_clock=test_clock))
    return stripe_service.create_customer(email, name="NovaMath E2E")


def attach_payment_method(customer_id, payment_method=CARD_VISA_SUCCESS):
    """Attache un moyen de paiement de test réel au client et le définit
    comme moyen de paiement par défaut pour les factures futures — reproduit
    exactement ce qu'une Checkout Session complétée avec succès fait pour
    l'utilisateur (voir stripe_service.create_checkout_session).

    Renvoie l'ID RÉEL de la PaymentMethod attachée (ex: "pm_1Tvf..."), jamais
    le jeton magique d'entrée (`pm_card_visa` etc.) : vérifié en conditions
    réelles, Stripe crée une PaymentMethod RÉELLE DIFFÉRENTE à chaque
    utilisation de ce jeton (deux appels avec "pm_card_visa" sur le même
    client produisent deux pm_... distincts) — réutiliser le jeton magique
    tel quel dans un appel ultérieur (ex: Subscription.create(
    default_payment_method=...)) référence alors une PaymentMethod jamais
    attachée au client et échoue avec "The payment method must be attached
    to the customer.". Seul l'ID réellement retourné par cet attach() est
    stable et attaché."""
    attached = stripe.PaymentMethod.attach(payment_method, customer=customer_id)
    stripe.Customer.modify(customer_id, invoice_settings={"default_payment_method": attached.id})
    return attached.id


def create_real_subscription(customer_id, price_id, payment_method=CARD_VISA_SUCCESS):
    """Abonnement Stripe RÉEL (Test Mode), avec Invoice/PaymentIntent réels
    — voir la docstring du module pour pourquoi ceci remplace un parcours
    Checkout piloté par navigateur dans cette suite automatisée.

    Retour converti via stripe_service._to_plain (voir sa docstring) : un
    appel SDK direct comme celui-ci renvoie un StripeObject réel, qui ne
    définit AUCUNE méthode `.get()` (vérifié en conditions réelles) — cette
    conversion est nécessaire pour que stripe_webhook_service.sync_subscription
    (appelé directement par plusieurs tests avec cet objet, pas seulement via
    un webhook) fonctionne exactement comme avec les données réellement
    reçues en production, qui transitent TOUJOURS par stripe_service.py
    (donc déjà converties) avant d'atteindre ce code métier."""
    real_payment_method_id = attach_payment_method(customer_id, payment_method)
    return stripe_service._to_plain(stripe.Subscription.create(
        customer=customer_id,
        items=[{"price": price_id}],
        default_payment_method=real_payment_method_id,
        expand=["latest_invoice.payments"],
    ))


def latest_payment_intent(subscription):
    """Recupere le PaymentIntent REEL de la facture la plus recente d'un
    abonnement cree par create_real_subscription() -- necessaire depuis la
    suppression de invoice.payment_intent par Stripe (API "Basil",
    2025-03-31, support des paiements partiels multiples sur une facture,
    vecu en conditions reelles via un KeyError explicite renvoye par le SDK
    pointant vers ce changelog) : seul l'ID est desormais present sur la
    facture (invoice["payments"]["data"][0]["payment"]["payment_intent"]),
    l'objet complet necessite un appel separe."""
    payment_intent_id = subscription["latest_invoice"]["payments"]["data"][0]["payment"]["payment_intent"]
    return stripe_service._to_plain(stripe.PaymentIntent.retrieve(payment_intent_id))


def cleanup_customer(customer_id):
    """Supprime le client de test (cascade : abonnements/moyens de
    paiement/factures associés côté Stripe Test Mode) — jamais laissé
    traîner dans le compte Stripe Test Mode après un test. Best-effort :
    jamais une erreur de nettoyage ne doit faire échouer un test déjà
    terminé (tearDown)."""
    try:
        stripe.Customer.delete(customer_id)
    except Exception:  # pragma: no cover - nettoyage best-effort
        pass


def create_test_clock(frozen_time=None, name=None):
    """Horloge de test Stripe (https://docs.stripe.com/billing/testing/test-clocks)
    — seul moyen officiellement recommandé par Stripe pour tester des
    scénarios temporels (renouvellement, expiration de période) sans
    attendre de vrais jours/mois."""
    return stripe.test_helpers.TestClock.create(
        frozen_time=frozen_time or int(time.time()), name=name or "novamath-e2e",
    )


def advance_test_clock(clock_id, to_timestamp, timeout=60):
    """Avance l'horloge et ATTEND que Stripe ait fini de rejouer tous les
    événements simulés (facturation, webhooks internes...) avant de rendre
    la main — une horloge encore `advancing` donnerait un état incohérent
    aux assertions suivantes."""
    stripe.test_helpers.TestClock.advance(clock_id, frozen_time=to_timestamp)
    deadline = time.time() + timeout
    while time.time() < deadline:
        clock = stripe.test_helpers.TestClock.retrieve(clock_id)
        if clock["status"] == "ready":
            return clock
        time.sleep(2)
    raise TimeoutError(f"Test Clock {clock_id} jamais repassée à 'ready' sous {timeout}s.")


def cleanup_test_clock(clock_id):
    """Supprime l'horloge de test — cascade la suppression de TOUTES les
    ressources (clients, abonnements, factures) qui lui sont attachées,
    plus fiable qu'un nettoyage ressource par ressource pour les scénarios
    à base de Test Clock."""
    try:
        stripe.test_helpers.TestClock.delete(clock_id)
    except Exception:  # pragma: no cover - nettoyage best-effort
        pass


def build_real_signed_webhook_payload(event_type, data_object, api_version=None):
    """Construit un payload webhook Stripe et sa signature RÉELLE (même
    algorithme HMAC-SHA256 que `stripe.WebhookSignature`, utilisé aussi bien
    par Stripe CLI/`stripe listen` que par les serveurs Stripe pour signer un
    envoi — voir stripe.Webhook.construct_event/WebhookSignature.
    verify_header, code source vérifié) à partir d'un objet RÉEL déjà obtenu
    depuis l'API (jamais un objet inventé). Simule l'ENVOI HTTP d'un webhook
    (ce que `stripe listen --forward-to` ferait localement) sans dépendre
    d'un process interactif externe dans la suite automatisée — la
    vérification de signature exercée
    (stripe_service.construct_webhook_event) est le code réellement utilisé
    en production, avec le vrai STRIPE_WEBHOOK_SECRET configuré."""
    import json
    from decimal import Decimal

    def _json_default(obj):
        # Certains champs monétaires (ex: items.data[].plan.amount_decimal)
        # restent des Decimal même après stripe_service._to_plain()/.to_dict()
        # (vérifié en conditions réelles) — json.dumps ne les sérialise pas
        # nativement. Stripe envoie toujours ces montants en entier (cents)
        # dans un vrai payload webhook JSON, jamais en chaîne : conversion
        # fidèle à ce que Stripe transmet réellement.
        if isinstance(obj, Decimal):
            return int(obj) if obj == obj.to_integral_value() else float(obj)
        raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

    payload_str = json.dumps({
        "id": f"evt_e2e_{int(time.time() * 1000)}",
        "object": "event",
        "type": event_type,
        "api_version": api_version,
        "created": int(time.time()),
        "data": {"object": data_object},
    }, default=_json_default)
    timestamp = int(time.time())
    # Même construction que WebhookSignature.verify_header : "%d.%s" % (timestamp, payload)
    signed_payload = f"{timestamp}.{payload_str}"
    signature = stripe.WebhookSignature._compute_signature(signed_payload, config.STRIPE_WEBHOOK_SECRET)
    sig_header = f"t={timestamp},v1={signature}"
    return payload_str.encode("utf-8"), sig_header
