"""
Suite E2E Stripe — API RÉELLE Stripe Test Mode, JAMAIS de mocks.

Complète (ne duplique jamais) les suites existantes basées sur des mocks
(tests/test_stripe_service.py, test_stripe_webhook_service.py,
test_billing_service.py, test_server_billing.py) qui valident la logique
pure de webapp/stripe_service.py / stripe_webhook_service.py /
billing_service.py hors ligne. Cette suite-ci valide que ce même code
fonctionne réellement contre les serveurs Stripe (Test Mode) : Checkout,
Customer Portal, abonnements, upgrade/downgrade, résiliation, factures,
paiements refusés, renouvellement/expiration via Test Clocks, webhooks
signés avec le véritable algorithme Stripe, et la synchronisation locale
qui en résulte (plan_service/quota_service/billing_service).

Se désactive PROPREMENT (skip, jamais une erreur ni un mock de repli) si
aucune clé Stripe Test Mode réellement joignable n'est configurée — voir
webapp/tests/stripe_e2e_helpers.py::E2E_AVAILABLE. Toute la configuration
(clés, Price ID, secret webhook) vient de webapp/config.py, jamais codée en
dur ici. Sécurité : refuse catégoriquement une clé sk_live_ (voir
stripe_e2e_helpers._detect_e2e_availability).

Parcours Checkout : la page hébergée par Stripe n'est pas pilotée par un
navigateur automatisé dans cette suite (Stripe ne conçoit pas Checkout pour
être scripté) — stripe_service.create_checkout_session()/get_checkout_session()
sont testées contre l'API réelle (création + lecture d'une vraie session),
et le reste du cycle de vie de l'abonnement (paiement, upgrade, downgrade,
résiliation, factures, échecs, renouvellement) est testé en créant
directement, via l'API et un moyen de paiement de test officiel Stripe, le
même graphe d'objets réels (Subscription + Invoice + PaymentIntent) qu'un
Checkout complété avec succès produit — voir stripe_e2e_helpers.py pour le
détail et la justification complète de ce choix.

Suite lente par nature (appels réseau réels vers Stripe Test Mode) :
plusieurs dizaines de secondes à quelques minutes selon la latence réseau et
les scénarios à base de Test Clock (qui attendent la resynchronisation
Stripe). Normal, attendu, jamais un signe de test cassé.
"""
import shutil
import tempfile
import time
import unittest
from pathlib import Path

import stripe

import billing_service
import config
import db
import plan_service
import quota_service
import stripe_service
import stripe_webhook_service
from plan_service import Plan

from tests import stripe_e2e_helpers as h


class _NovaMathUserFixture(unittest.TestCase):
    """Utilisateur NovaMath local (base SQLite temporaire, jamais la base
    réelle — même stratégie que tests/test_two_factor_migration.py) lié à un
    VRAI client Stripe Test Mode, prêt pour les scénarios qui doivent
    résoudre `db.get_user_by_stripe_customer_id` (webhooks) ou lire/écrire
    `users.plan`/`stripe_subscription_id` (plan_service/quota_service)."""

    @classmethod
    def setUpClass(cls):
        cls._tmp_dir = tempfile.mkdtemp()
        cls._data_dir_backup = db.DATA_DIR
        cls._db_path_backup = db.DB_PATH
        db.DATA_DIR = Path(cls._tmp_dir)
        db.DB_PATH = db.DATA_DIR / "novamath.db"
        db.init_db()

        cls.customer = h.create_test_customer()
        cls.user_id = db.create_user(cls.customer["email"], f"e2euser{int(time.time()*1000)}", "E2E Tester", "hash")
        db.set_stripe_customer_id(cls.user_id, cls.customer["id"])

    @classmethod
    def tearDownClass(cls):
        h.cleanup_customer(cls.customer["id"])
        db.DATA_DIR = cls._data_dir_backup
        db.DB_PATH = cls._db_path_backup
        shutil.rmtree(cls._tmp_dir, ignore_errors=True)

    def _user(self):
        return db.get_user_by_id(self.user_id)


# ── Connectivité / configuration ─────────────────────────────────────────
@h.skip_unless_e2e
class TestConnexionStripeReelle(unittest.TestCase):
    def test_cle_secrete_est_bien_test_mode(self):
        self.assertTrue(config.STRIPE_SECRET_KEY.startswith("sk_test_"))

    def test_stripe_service_is_configured(self):
        self.assertTrue(stripe_service.is_configured())

    def test_appel_reel_balance_retrieve(self):
        stripe.api_key = config.STRIPE_SECRET_KEY
        balance = stripe.Balance.retrieve()
        self.assertEqual(balance["object"], "balance")

    def test_price_premium_existe_reellement(self):
        stripe.api_key = config.STRIPE_SECRET_KEY
        price = stripe.Price.retrieve(config.STRIPE_PRICE_PREMIUM)
        self.assertEqual(price["id"], config.STRIPE_PRICE_PREMIUM)
        self.assertTrue(price["active"])

    def test_price_ultra_existe_reellement(self):
        stripe.api_key = config.STRIPE_SECRET_KEY
        price = stripe.Price.retrieve(config.STRIPE_PRICE_ULTRA)
        self.assertEqual(price["id"], config.STRIPE_PRICE_ULTRA)
        self.assertTrue(price["active"])

    def test_prix_premium_et_ultra_distincts(self):
        self.assertNotEqual(config.STRIPE_PRICE_PREMIUM, config.STRIPE_PRICE_ULTRA)


# ── Création de client ────────────────────────────────────────────────────
@h.skip_unless_e2e
class TestCreationClient(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.customer = h.create_test_customer()

    @classmethod
    def tearDownClass(cls):
        h.cleanup_customer(cls.customer["id"])

    def test_id_reel_prefixe_cus(self):
        self.assertTrue(self.customer["id"].startswith("cus_"))

    def test_email_persiste(self):
        self.assertIn("@example.com", self.customer["email"])

    def test_objet_est_bien_customer(self):
        self.assertEqual(self.customer["object"], "customer")

    def test_recuperation_reelle_par_id(self):
        fetched = stripe_service.get_customer(self.customer["id"])
        self.assertEqual(fetched["id"], self.customer["id"])

    def test_client_supprime_nest_plus_recuperable_normalement(self):
        temp_customer = h.create_test_customer()
        stripe.Customer.delete(temp_customer["id"])
        fetched = stripe_service.get_customer(temp_customer["id"])
        self.assertTrue(fetched.get("deleted"))


# ── Checkout Session (création + lecture réelles) ─────────────────────────
@h.skip_unless_e2e
class TestCheckoutSession(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.customer = h.create_test_customer()
        cls.session = stripe_service.create_checkout_session(
            customer_id=cls.customer["id"], plan=Plan.PREMIUM,
            success_url="https://example.com/checkout/success", cancel_url="https://example.com/checkout/cancel",
        )

    @classmethod
    def tearDownClass(cls):
        h.cleanup_customer(cls.customer["id"])

    def test_session_id_prefixe_cs(self):
        self.assertTrue(self.session["id"].startswith("cs_"))

    def test_session_a_une_url_hebergee_stripe(self):
        self.assertTrue(self.session["url"].startswith("https://checkout.stripe.com/"))

    def test_mode_subscription(self):
        self.assertEqual(self.session["mode"], "subscription")

    def test_customer_correct(self):
        self.assertEqual(self.session["customer"], self.customer["id"])

    def test_statut_initial_open(self):
        self.assertEqual(self.session["status"], "open")

    def test_recuperation_reelle_de_la_session(self):
        fetched = stripe_service.get_checkout_session(self.session["id"])
        self.assertEqual(fetched["id"], self.session["id"])

    def test_checkout_pour_ultra_utilise_le_bon_price(self):
        session_ultra = stripe_service.create_checkout_session(
            customer_id=self.customer["id"], plan=Plan.ULTRA,
            success_url="https://example.com/s", cancel_url="https://example.com/c",
        )
        line_items = stripe.checkout.Session.list_line_items(session_ultra["id"])
        self.assertEqual(line_items["data"][0]["price"]["id"], config.STRIPE_PRICE_ULTRA)

    def test_checkout_pour_premium_utilise_le_bon_price(self):
        line_items = stripe.checkout.Session.list_line_items(self.session["id"])
        self.assertEqual(line_items["data"][0]["price"]["id"], config.STRIPE_PRICE_PREMIUM)


# ── Abonnement Premium — paiement accepté ─────────────────────────────────
@h.skip_unless_e2e
class TestAbonnementPremiumReussi(_NovaMathUserFixture):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.subscription = h.create_real_subscription(cls.customer["id"], config.STRIPE_PRICE_PREMIUM)

    def test_abonnement_id_prefixe_sub(self):
        self.assertTrue(self.subscription["id"].startswith("sub_"))

    def test_statut_actif(self):
        self.assertEqual(self.subscription["status"], "active")

    def test_price_id_correct(self):
        self.assertEqual(self.subscription["items"]["data"][0]["price"]["id"], config.STRIPE_PRICE_PREMIUM)

    def test_invoice_payee(self):
        invoice = self.subscription["latest_invoice"]
        self.assertEqual(invoice["status"], "paid")

    def test_payment_intent_reussi(self):
        payment_intent = self.subscription["latest_invoice"]["payment_intent"]
        self.assertEqual(payment_intent["status"], "succeeded")

    def test_plan_from_price_id_resout_premium(self):
        self.assertEqual(stripe_service.plan_from_price_id(config.STRIPE_PRICE_PREMIUM), Plan.PREMIUM)

    def test_sync_subscription_ecrit_le_plan_premium_localement(self):
        db.set_stripe_customer_id(self.user_id, self.customer["id"])
        sync_subscription_test_helper = self._user()
        stripe_webhook_service.sync_subscription(sync_subscription_test_helper, self.subscription)
        user = self._user()
        self.assertEqual(user["plan"], "premium")
        self.assertEqual(user["stripe_subscription_status"], "active")

    def test_plan_service_reflete_premium_apres_synchronisation(self):
        stripe_webhook_service.sync_subscription(self._user(), self.subscription)
        user = self._user()
        self.assertTrue(plan_service.is_premium(user))
        self.assertTrue(plan_service.has_feature(user, plan_service.Feature.CHATBOT_UNLIMITED))

    def test_quota_service_reflete_premium_apres_synchronisation(self):
        stripe_webhook_service.sync_subscription(self._user(), self.subscription)
        user = self._user()
        free_user = {"id": 999999, "plan": "free"}
        limit_premium = quota_service.get_limit(user, quota_service.QuotaType.PDF_ANALYSIS)
        limit_free = quota_service.get_limit(free_user, quota_service.QuotaType.PDF_ANALYSIS)
        if limit_premium is not None and limit_free is not None:
            self.assertGreaterEqual(limit_premium, limit_free)


# ── Abonnement Ultra — paiement accepté ───────────────────────────────────
@h.skip_unless_e2e
class TestAbonnementUltraReussi(_NovaMathUserFixture):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.subscription = h.create_real_subscription(cls.customer["id"], config.STRIPE_PRICE_ULTRA)

    def test_statut_actif(self):
        self.assertEqual(self.subscription["status"], "active")

    def test_price_id_correct(self):
        self.assertEqual(self.subscription["items"]["data"][0]["price"]["id"], config.STRIPE_PRICE_ULTRA)

    def test_plan_from_price_id_resout_ultra(self):
        self.assertEqual(stripe_service.plan_from_price_id(config.STRIPE_PRICE_ULTRA), Plan.ULTRA)

    def test_sync_subscription_ecrit_le_plan_ultra_localement(self):
        stripe_webhook_service.sync_subscription(self._user(), self.subscription)
        user = self._user()
        self.assertEqual(user["plan"], "ultra")

    def test_plan_service_reflete_ultra_apres_synchronisation(self):
        stripe_webhook_service.sync_subscription(self._user(), self.subscription)
        user = self._user()
        self.assertTrue(plan_service.is_ultra(user))
        self.assertTrue(plan_service.has_feature(user, plan_service.Feature.ADVANCED_AI))
        self.assertTrue(plan_service.has_feature(user, plan_service.Feature.CUSTOM_EXERCISES))

    def test_invoice_payee(self):
        self.assertEqual(self.subscription["latest_invoice"]["status"], "paid")


# ── Paiement refusé ────────────────────────────────────────────────────────
@h.skip_unless_e2e
class TestPaiementRefuse(_NovaMathUserFixture):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.subscription = h.create_real_subscription(
            cls.customer["id"], config.STRIPE_PRICE_PREMIUM, payment_method=h.CARD_DECLINED,
        )

    def test_abonnement_reste_incomplet(self):
        self.assertEqual(self.subscription["status"], "incomplete")

    def test_invoice_non_payee(self):
        self.assertNotEqual(self.subscription["latest_invoice"]["status"], "paid")

    def test_payment_intent_necessite_un_moyen_de_paiement(self):
        payment_intent = self.subscription["latest_invoice"]["payment_intent"]
        self.assertIn(payment_intent["status"], ("requires_payment_method", "requires_action"))

    def test_sync_subscription_najamais_les_droits_premium(self):
        stripe_webhook_service.sync_subscription(self._user(), self.subscription)
        user = self._user()
        self.assertFalse(plan_service.is_premium(user))
        self.assertEqual(plan_service.get_plan(user), Plan.FREE)

    def test_plan_from_price_id_reste_correct_meme_impaye(self):
        # plan_from_price_id ne regarde que le Price ID, jamais le statut —
        # c'est sync_subscription qui applique la règle "actif seulement".
        self.assertEqual(stripe_service.plan_from_price_id(config.STRIPE_PRICE_PREMIUM), Plan.PREMIUM)


@h.skip_unless_e2e
class TestPaiementFondsInsuffisants(_NovaMathUserFixture):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.subscription = h.create_real_subscription(
            cls.customer["id"], config.STRIPE_PRICE_PREMIUM, payment_method=h.CARD_DECLINED_INSUFFICIENT_FUNDS,
        )

    def test_abonnement_incomplet(self):
        self.assertEqual(self.subscription["status"], "incomplete")

    def test_najamais_synchronise_vers_un_plan_payant(self):
        stripe_webhook_service.sync_subscription(self._user(), self.subscription)
        self.assertEqual(plan_service.get_plan(self._user()), Plan.FREE)


@h.skip_unless_e2e
class TestCarteExpiree(_NovaMathUserFixture):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.subscription = h.create_real_subscription(
            cls.customer["id"], config.STRIPE_PRICE_PREMIUM, payment_method=h.CARD_DECLINED_EXPIRED,
        )

    def test_abonnement_incomplet(self):
        self.assertEqual(self.subscription["status"], "incomplete")

    def test_najamais_synchronise_vers_un_plan_payant(self):
        stripe_webhook_service.sync_subscription(self._user(), self.subscription)
        self.assertEqual(plan_service.get_plan(self._user()), Plan.FREE)

    def test_nouvelle_carte_valide_permet_le_paiement(self):
        """« Nouvelle carte » : remplace le moyen de paiement par défaut par
        une carte de test valide et confirme que la facture en attente peut
        alors être payée — reproduit le parcours "mettre à jour ma carte"
        du Customer Portal."""
        h.attach_payment_method(self.customer["id"], h.CARD_VISA_SUCCESS)
        invoice_id = self.subscription["latest_invoice"]["id"]
        paid_invoice = stripe.Invoice.pay(invoice_id, payment_method=h.CARD_VISA_SUCCESS)
        self.assertEqual(paid_invoice["status"], "paid")


# ── Webhooks (signature RÉELLE, jamais simulée) ───────────────────────────
@h.skip_unless_e2e
class TestWebhookSignature(unittest.TestCase):
    def test_signature_reelle_valide_est_acceptee(self):
        payload, sig_header = h.build_real_signed_webhook_payload(
            "customer.subscription.updated", {"id": "sub_fake_for_signature_test", "customer": "cus_fake"},
        )
        event = stripe_service.construct_webhook_event(payload, sig_header)
        self.assertEqual(event["type"], "customer.subscription.updated")

    def test_signature_falsifiee_est_rejetee(self):
        payload, sig_header = h.build_real_signed_webhook_payload(
            "customer.subscription.updated", {"id": "sub_x", "customer": "cus_x"},
        )
        tampered_header = sig_header.replace("v1=", "v1=0000")
        with self.assertRaises(stripe.error.SignatureVerificationError):
            stripe_service.construct_webhook_event(payload, tampered_header)

    def test_payload_modifie_apres_signature_est_rejete(self):
        payload, sig_header = h.build_real_signed_webhook_payload(
            "customer.subscription.updated", {"id": "sub_y", "customer": "cus_y"},
        )
        tampered_payload = payload.replace(b"sub_y", b"sub_z")
        with self.assertRaises(stripe.error.SignatureVerificationError):
            stripe_service.construct_webhook_event(tampered_payload, sig_header)


@h.skip_unless_e2e
class TestWebhookCheckoutEtAbonnement(_NovaMathUserFixture):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.subscription = h.create_real_subscription(cls.customer["id"], config.STRIPE_PRICE_PREMIUM)

    def test_webhook_subscription_created_synchronise_le_plan(self):
        payload, sig_header = h.build_real_signed_webhook_payload(
            "customer.subscription.created", dict(self.subscription),
        )
        event = stripe_service.construct_webhook_event(payload, sig_header)
        result = stripe_webhook_service.handle_event(event)
        self.assertEqual(result["status"], "processed")
        self.assertEqual(self._user()["plan"], "premium")

    def test_webhook_idempotent_sur_rejeu_du_meme_event_id(self):
        payload, sig_header = h.build_real_signed_webhook_payload(
            "customer.subscription.updated", dict(self.subscription),
        )
        event = stripe_service.construct_webhook_event(payload, sig_header)
        first = stripe_webhook_service.handle_event(event)
        second = stripe_webhook_service.handle_event(event)
        self.assertEqual(first["status"], "processed")
        self.assertEqual(second["status"], "duplicate_ignored")

    def test_webhook_subscription_deleted_repasse_en_free(self):
        stripe_webhook_service.sync_subscription(self._user(), self.subscription)
        self.assertEqual(self._user()["plan"], "premium")
        payload, sig_header = h.build_real_signed_webhook_payload(
            "customer.subscription.deleted", dict(self.subscription),
        )
        event = stripe_service.construct_webhook_event(payload, sig_header)
        stripe_webhook_service.handle_event(event)
        user = self._user()
        self.assertEqual(user["plan"], "free")
        self.assertEqual(user["stripe_subscription_status"], "canceled")

    def test_webhook_type_non_gere_est_ignore_sans_erreur(self):
        payload, sig_header = h.build_real_signed_webhook_payload(
            "customer.updated", {"id": self.customer["id"]},
        )
        event = stripe_service.construct_webhook_event(payload, sig_header)
        result = stripe_webhook_service.handle_event(event)
        self.assertEqual(result["status"], "ignored")

    def test_webhook_customer_inconnu_najamais_erreur(self):
        payload, sig_header = h.build_real_signed_webhook_payload(
            "customer.subscription.updated", {"id": "sub_unknown", "customer": "cus_completely_unknown_xyz", "status": "active", "items": {"data": [{"price": {"id": config.STRIPE_PRICE_PREMIUM}}]}},
        )
        event = stripe_service.construct_webhook_event(payload, sig_header)
        result = stripe_webhook_service.handle_event(event)
        self.assertEqual(result["status"], "processed")


@h.skip_unless_e2e
class TestWebhookInvoices(_NovaMathUserFixture):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.subscription = h.create_real_subscription(cls.customer["id"], config.STRIPE_PRICE_PREMIUM)
        cls.invoice = cls.subscription["latest_invoice"]

    def test_invoice_paid_synchronise_le_plan(self):
        payload, sig_header = h.build_real_signed_webhook_payload("invoice.paid", dict(self.invoice))
        event = stripe_service.construct_webhook_event(payload, sig_header)
        result = stripe_webhook_service.handle_event(event)
        self.assertEqual(result["status"], "processed")
        self.assertEqual(self._user()["plan"], "premium")

    def test_invoice_payment_failed_met_le_statut_past_due(self):
        payload, sig_header = h.build_real_signed_webhook_payload("invoice.payment_failed", dict(self.invoice))
        event = stripe_service.construct_webhook_event(payload, sig_header)
        stripe_webhook_service.handle_event(event)
        self.assertEqual(self._user()["stripe_subscription_status"], "past_due")

    def test_invoice_payment_failed_ne_retire_pas_le_plan(self):
        stripe_webhook_service.sync_subscription(self._user(), self.subscription)
        payload, sig_header = h.build_real_signed_webhook_payload("invoice.payment_failed", dict(self.invoice))
        event = stripe_service.construct_webhook_event(payload, sig_header)
        stripe_webhook_service.handle_event(event)
        # Stripe retente automatiquement avant d'annuler réellement — le plan
        # n'est retiré que par customer.subscription.deleted, jamais ici.
        self.assertEqual(self._user()["plan"], "premium")

    def test_invoice_finalized_journalise_sans_modifier_le_plan(self):
        before = self._user()["plan"]
        payload, sig_header = h.build_real_signed_webhook_payload("invoice.finalized", dict(self.invoice))
        event = stripe_service.construct_webhook_event(payload, sig_header)
        result = stripe_webhook_service.handle_event(event)
        self.assertEqual(result["status"], "processed")
        self.assertEqual(self._user()["plan"], before)

    def test_invoice_upcoming_journalise_sans_erreur(self):
        payload, sig_header = h.build_real_signed_webhook_payload("invoice.upcoming", dict(self.invoice))
        event = stripe_service.construct_webhook_event(payload, sig_header)
        result = stripe_webhook_service.handle_event(event)
        self.assertEqual(result["status"], "processed")

    def test_invoice_payment_succeeded_alias_de_invoice_paid(self):
        payload, sig_header = h.build_real_signed_webhook_payload("invoice.payment_succeeded", dict(self.invoice))
        event = stripe_service.construct_webhook_event(payload, sig_header)
        result = stripe_webhook_service.handle_event(event)
        self.assertEqual(result["status"], "processed")
        self.assertEqual(self._user()["plan"], "premium")


# ── Customer Portal ─────────────────────────────────────────────────────────
@h.skip_unless_e2e
class TestCustomerPortal(_NovaMathUserFixture):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.subscription = h.create_real_subscription(cls.customer["id"], config.STRIPE_PRICE_PREMIUM)
        db.set_stripe_subscription(cls.user_id, cls.subscription["id"], "premium", "active")

    def test_creation_reelle_dune_session_portail(self):
        url = billing_service.create_portal_session(self._user(), "https://example.com/return")
        self.assertTrue(url.startswith("https://billing.stripe.com/"))

    def test_sans_customer_leve_no_stripe_customer(self):
        with self.assertRaises(billing_service.NoStripeCustomer):
            billing_service.create_portal_session({"id": 0, "stripe_customer_id": None}, "https://example.com")

    def test_session_stripe_service_directe(self):
        session = stripe_service.create_billing_portal_session(self.customer["id"], "https://example.com/r")
        self.assertTrue(session["id"].startswith("bps_") or session["object"] == "billing_portal.session")


# ── Upgrade Premium -> Ultra ──────────────────────────────────────────────
@h.skip_unless_e2e
class TestUpgradePremiumVersUltra(_NovaMathUserFixture):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.subscription = h.create_real_subscription(cls.customer["id"], config.STRIPE_PRICE_PREMIUM)
        db.set_stripe_subscription(cls.user_id, cls.subscription["id"], "premium", "active")

    def test_upgrade_change_immediatement_le_price(self):
        updated = billing_service.change_plan(self._user(), Plan.ULTRA)
        self.assertEqual(updated["items"]["data"][0]["price"]["id"], config.STRIPE_PRICE_ULTRA)

    def test_upgrade_meme_plan_leve_same_plan(self):
        with self.assertRaises(billing_service.SamePlan):
            billing_service.change_plan(self._user(), Plan.PREMIUM)

    def test_upgrade_sans_abonnement_leve_no_active_subscription(self):
        with self.assertRaises(billing_service.NoActiveSubscription):
            billing_service.change_plan({"id": 0, "plan": "free", "stripe_subscription_id": None}, Plan.ULTRA)

    def test_apres_upgrade_la_synchronisation_reflete_ultra(self):
        updated = stripe_service.get_subscription(self.subscription["id"])
        stripe_webhook_service.sync_subscription(self._user(), updated)
        self.assertEqual(self._user()["plan"], "ultra")


# ── Downgrade Ultra -> Premium ─────────────────────────────────────────────
@h.skip_unless_e2e
class TestDowngradeUltraVersPremium(_NovaMathUserFixture):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.subscription = h.create_real_subscription(cls.customer["id"], config.STRIPE_PRICE_ULTRA)
        db.set_stripe_subscription(cls.user_id, cls.subscription["id"], "ultra", "active")

    def test_downgrade_cree_un_subscription_schedule_reel(self):
        schedule = billing_service.change_plan(self._user(), Plan.PREMIUM)
        self.assertTrue(schedule["id"].startswith("sub_sched_"))

    def test_downgrade_najamais_immediat(self):
        """Le downgrade ne modifie JAMAIS immédiatement users.plan (seul le
        webhook, quand Stripe applique réellement la seconde phase, le
        fait) — vérifié en relisant l'utilisateur juste après l'appel."""
        billing_service.change_plan(self._user(), Plan.PREMIUM)
        self.assertEqual(self._user()["plan"], "ultra")

    def test_downgrade_conserve_la_phase_courante(self):
        schedule = billing_service.change_plan(self._user(), Plan.PREMIUM)
        self.assertEqual(len(schedule["phases"]), 2)


# ── Résiliation ────────────────────────────────────────────────────────────
@h.skip_unless_e2e
class TestResiliationImmediate(_NovaMathUserFixture):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.subscription = h.create_real_subscription(cls.customer["id"], config.STRIPE_PRICE_PREMIUM)

    def test_annulation_reelle(self):
        canceled = stripe_service.cancel_subscription(self.subscription["id"])
        self.assertEqual(canceled["status"], "canceled")

    def test_webhook_deleted_repasse_lutilisateur_en_free(self):
        canceled = stripe_service.get_subscription(self.subscription["id"])
        payload, sig_header = h.build_real_signed_webhook_payload("customer.subscription.deleted", dict(canceled))
        event = stripe_service.construct_webhook_event(payload, sig_header)
        stripe_webhook_service.handle_event(event)
        self.assertEqual(self._user()["plan"], "free")


@h.skip_unless_e2e
class TestResiliationFinDePeriode(_NovaMathUserFixture):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.subscription = h.create_real_subscription(cls.customer["id"], config.STRIPE_PRICE_PREMIUM)

    def test_cancel_at_period_end_reel(self):
        updated = stripe.Subscription.modify(self.subscription["id"], cancel_at_period_end=True)
        self.assertTrue(updated["cancel_at_period_end"])
        self.assertEqual(updated["status"], "active")

    def test_billing_status_expose_cancel_at(self):
        stripe.Subscription.modify(self.subscription["id"], cancel_at_period_end=True)
        db.set_stripe_subscription(self.user_id, self.subscription["id"], "premium", "active")
        status = billing_service.get_billing_status(self._user())
        self.assertIsNotNone(status["cancel_at"])

    def test_annuler_la_resiliation_programmee(self):
        stripe.Subscription.modify(self.subscription["id"], cancel_at_period_end=True)
        restored = stripe.Subscription.modify(self.subscription["id"], cancel_at_period_end=False)
        self.assertFalse(restored["cancel_at_period_end"])


# ── Facturation ────────────────────────────────────────────────────────────
@h.skip_unless_e2e
class TestFacturation(_NovaMathUserFixture):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.subscription = h.create_real_subscription(cls.customer["id"], config.STRIPE_PRICE_PREMIUM)
        db.set_stripe_subscription(cls.user_id, cls.subscription["id"], "premium", "active")

    def test_get_billing_status_plan_correct(self):
        status = billing_service.get_billing_status(self._user())
        self.assertEqual(status["plan"], "premium")

    def test_get_billing_status_email_facturation(self):
        status = billing_service.get_billing_status(self._user())
        self.assertEqual(status["billing_email"], self.customer["email"])

    def test_get_billing_status_moyen_de_paiement(self):
        status = billing_service.get_billing_status(self._user())
        self.assertIsNotNone(status["payment_method"])
        self.assertEqual(status["payment_method"]["brand"], "visa")

    def test_get_billing_status_factures_non_vides(self):
        status = billing_service.get_billing_status(self._user())
        self.assertGreaterEqual(len(status["invoices"]), 1)

    def test_get_billing_status_renew_at_defini(self):
        status = billing_service.get_billing_status(self._user())
        self.assertIsNotNone(status["renew_at"])

    def test_liste_factures_stripe_service_direct(self):
        invoices = stripe_service.list_invoices(self.customer["id"])
        self.assertGreaterEqual(len(invoices["data"]), 1)

    def test_liste_moyens_de_paiement_stripe_service_direct(self):
        methods = stripe_service.list_payment_methods(self.customer["id"])
        self.assertGreaterEqual(len(methods["data"]), 1)

    def test_facture_contient_le_bon_montant(self):
        status = billing_service.get_billing_status(self._user())
        self.assertGreater(status["invoices"][0]["amount_paid"], 0)


# ── Synchronisation locale (plan / quotas / billing) ──────────────────────
@h.skip_unless_e2e
class TestSynchronisationLocale(_NovaMathUserFixture):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.subscription = h.create_real_subscription(cls.customer["id"], config.STRIPE_PRICE_ULTRA)

    def test_synchronisation_ecrit_stripe_subscription_id(self):
        stripe_webhook_service.sync_subscription(self._user(), self.subscription)
        self.assertEqual(self._user()["stripe_subscription_id"], self.subscription["id"])

    def test_synchronisation_du_plan(self):
        stripe_webhook_service.sync_subscription(self._user(), self.subscription)
        self.assertEqual(plan_service.get_plan(self._user()), Plan.ULTRA)

    def test_synchronisation_des_quotas(self):
        stripe_webhook_service.sync_subscription(self._user(), self.subscription)
        user = self._user()
        limit = quota_service.get_limit(user, quota_service.QuotaType.PDF_ANALYSIS)
        unlimited = quota_service.is_unlimited(user, quota_service.QuotaType.PDF_ANALYSIS)
        self.assertTrue(unlimited or (limit is not None and limit > 0))

    def test_synchronisation_billing_apres_webhook(self):
        stripe_webhook_service.sync_subscription(self._user(), self.subscription)
        status = billing_service.get_billing_status(self._user())
        self.assertEqual(status["plan"], "ultra")

    def test_resynchronisation_ne_duplique_rien(self):
        stripe_webhook_service.sync_subscription(self._user(), self.subscription)
        stripe_webhook_service.sync_subscription(self._user(), self.subscription)
        user = self._user()
        self.assertEqual(user["plan"], "ultra")
        self.assertEqual(user["stripe_subscription_id"], self.subscription["id"])

    def test_quota_consume_fonctionne_apres_synchronisation(self):
        stripe_webhook_service.sync_subscription(self._user(), self.subscription)
        user = self._user()
        try:
            quota_service.consume(user, quota_service.QuotaType.PDF_ANALYSIS)
        except quota_service.QuotaExceededError:
            self.fail("Un utilisateur Ultra fraîchement synchronisé ne devrait jamais être déjà à quota.")


# ── Renouvellement / expiration via Test Clock ────────────────────────────
@h.skip_unless_e2e
class TestRenouvellementAvecTestClock(_NovaMathUserFixture):
    """Seul groupe de tests à utiliser un Test Clock (lent : chaque avance
    d'horloge attend une resynchronisation réelle côté Stripe) — voir
    stripe_e2e_helpers.advance_test_clock. Un seul cycle création + avance
    couvre "renouvellement" ET "expiration de la période en cours"."""

    @classmethod
    def setUpClass(cls):
        cls._tmp_dir = tempfile.mkdtemp()
        cls._data_dir_backup = db.DATA_DIR
        cls._db_path_backup = db.DB_PATH
        db.DATA_DIR = Path(cls._tmp_dir)
        db.DB_PATH = db.DATA_DIR / "novamath.db"
        db.init_db()

        now = int(time.time())
        cls.clock = h.create_test_clock(frozen_time=now)
        cls.customer = h.create_test_customer(test_clock=cls.clock["id"])
        cls.user_id = db.create_user(cls.customer["email"], f"e2eclock{now}", "E2E Clock", "hash")
        db.set_stripe_customer_id(cls.user_id, cls.customer["id"])
        cls.subscription = h.create_real_subscription(cls.customer["id"], config.STRIPE_PRICE_PREMIUM)
        cls.initial_period_end = cls.subscription["current_period_end"]

    @classmethod
    def tearDownClass(cls):
        h.cleanup_test_clock(cls.clock["id"])
        db.DATA_DIR = cls._data_dir_backup
        db.DB_PATH = cls._db_path_backup
        shutil.rmtree(cls._tmp_dir, ignore_errors=True)

    def _user(self):
        return db.get_user_by_id(self.user_id)

    def test_01_abonnement_initial_actif(self):
        self.assertEqual(self.subscription["status"], "active")

    def test_02_avance_du_temps_declenche_le_renouvellement(self):
        h.advance_test_clock(self.clock["id"], self.initial_period_end + 3600)
        renewed = stripe_service.get_subscription(self.subscription["id"])
        self.assertGreater(renewed["current_period_end"], self.initial_period_end)

    def test_03_abonnement_toujours_actif_apres_renouvellement(self):
        renewed = stripe_service.get_subscription(self.subscription["id"])
        self.assertEqual(renewed["status"], "active")

    def test_04_une_nouvelle_facture_de_renouvellement_existe(self):
        invoices = stripe_service.list_invoices(self.customer["id"], limit=10)
        self.assertGreaterEqual(len(invoices["data"]), 2)

    def test_05_synchronisation_apres_renouvellement_reste_premium(self):
        renewed = stripe_service.get_subscription(self.subscription["id"])
        stripe_webhook_service.sync_subscription(self._user(), renewed)
        self.assertEqual(self._user()["plan"], "premium")


# ── Non-régression : tous les services protégés restent inchangés ─────────
# Aucun appel Stripe réel ici — vérifie uniquement que cette suite E2E n'a
# rien cassé dans les modules qu'elle n'a pas le droit de modifier
# (importabilité + un appel représentatif de chacun, cohérent avec les
# suites de non-régression déjà écrites pour SEC-06/ARCH-03/ARCH-05/ARCH-02).
class TestNonRegressionServicesProteges(unittest.TestCase):
    def test_plan_service_intact(self):
        import plan_service as m
        self.assertEqual(m.get_plan(None), m.Plan.FREE)

    def test_quota_service_intact(self):
        import quota_service as m
        self.assertIsNotNone(m.QuotaType)

    def test_billing_service_intact(self):
        import billing_service as m
        self.assertTrue(hasattr(m, "get_billing_status"))

    def test_stripe_service_intact(self):
        import stripe_service as m
        self.assertTrue(hasattr(m, "create_checkout_session"))

    def test_stripe_webhook_service_intact(self):
        import stripe_webhook_service as m
        self.assertIn("checkout.session.completed", m.EVENT_HANDLERS)

    def test_role_service_intact(self):
        import role_service as m
        self.assertTrue(hasattr(m, "Role"))

    def test_rate_limit_service_intact(self):
        import rate_limit_service as m
        self.assertTrue(hasattr(m, "rate_limit"))

    def test_two_factor_service_intact(self):
        import two_factor_service as m
        self.assertTrue(hasattr(m, "begin_setup"))

    def test_logging_service_intact(self):
        import logging_service as m
        self.assertTrue(hasattr(m, "init_app"))

    def test_metrics_service_intact(self):
        import metrics_service as m
        self.assertTrue(hasattr(m, "record_request"))

    def test_backup_service_intact(self):
        import backup_service as m
        self.assertTrue(hasattr(m, "backup_database"))

    def test_health_service_intact(self):
        import health_service as m
        self.assertTrue(hasattr(m, "snapshot"))

    def test_database_service_intact(self):
        import database_service as m
        self.assertTrue(hasattr(m, "get_connection"))

    def test_security_headers_service_intact(self):
        import security_headers_service as m
        self.assertTrue(hasattr(m, "init_app"))

    def test_db_intact(self):
        import db as m
        self.assertTrue(hasattr(m, "get_connection"))
        self.assertTrue(hasattr(m, "set_stripe_subscription"))

    def test_plan_feature_matrix_toujours_complete(self):
        import plan_service as m
        for plan in m.Plan:
            self.assertIn(plan, m.FEATURE_MATRIX)

    def test_stripe_prices_mapping_toujours_present(self):
        import stripe_service as m
        self.assertIn(Plan.PREMIUM, m.STRIPE_PRICES)
        self.assertIn(Plan.ULTRA, m.STRIPE_PRICES)


if __name__ == "__main__":
    unittest.main()
