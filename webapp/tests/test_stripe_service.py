"""
Suite du service Stripe (webapp/stripe_service.py) : aucun appel réseau réel,
le SDK stripe est entièrement mocké (unittest.mock.patch) — comme les autres
suites du projet, ces tests doivent pouvoir tourner hors ligne et sans clé
Stripe valide.
"""
import os
import unittest
from unittest.mock import patch

import stripe

import stripe_service
from plan_service import Plan


class TestClientConfiguration(unittest.TestCase):
    def setUp(self):
        self._env_backup = dict(os.environ)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env_backup)

    def test_client_leve_si_secret_key_absente(self):
        os.environ.pop("STRIPE_SECRET_KEY", None)
        with self.assertRaises(stripe_service.StripeNotConfigured):
            stripe_service._client()

    def test_client_configure_api_key_depuis_env(self):
        os.environ["STRIPE_SECRET_KEY"] = "sk_test_123"
        client = stripe_service._client()
        self.assertEqual(client.api_key, "sk_test_123")

    def test_client_leve_si_secret_key_est_le_placeholder_env_example(self):
        # Régression : "sk_test_xxx" copié depuis .env.example sans être
        # remplacé par une vraie clé doit être détecté comme "non configuré"
        # (501 explicite côté server.py), jamais laissé passer jusqu'à un
        # appel Stripe réel qui échouerait avec une AuthenticationError opaque.
        os.environ["STRIPE_SECRET_KEY"] = "sk_test_xxx"
        with self.assertRaises(stripe_service.StripeNotConfigured):
            stripe_service._client()


class TestResolvePriceId(unittest.TestCase):
    def setUp(self):
        self._env_backup = dict(os.environ)
        os.environ["STRIPE_PRICE_PREMIUM"] = "price_premium_abc"
        os.environ["STRIPE_PRICE_ULTRA"] = "price_ultra_xyz"

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env_backup)

    def test_plan_connu(self):
        self.assertEqual(stripe_service.resolve_price_id(Plan.PREMIUM), "price_premium_abc")
        self.assertEqual(stripe_service.resolve_price_id(Plan.ULTRA), "price_ultra_xyz")

    def test_plan_inconnu(self):
        with self.assertRaises(stripe_service.StripePlanUnknown):
            stripe_service.resolve_price_id(Plan.FREE)

    def test_price_id_manquant_en_env(self):
        del os.environ["STRIPE_PRICE_PREMIUM"]
        with self.assertRaises(stripe_service.StripeNotConfigured):
            stripe_service.resolve_price_id(Plan.PREMIUM)

    def test_plan_from_price_id(self):
        self.assertIs(stripe_service.plan_from_price_id("price_premium_abc"), Plan.PREMIUM)
        self.assertIs(stripe_service.plan_from_price_id("price_ultra_xyz"), Plan.ULTRA)
        self.assertIs(stripe_service.plan_from_price_id("price_inconnu"), Plan.FREE)


class TestServiceCalls(unittest.TestCase):
    def setUp(self):
        self._env_backup = dict(os.environ)
        os.environ["STRIPE_SECRET_KEY"] = "sk_test_123"
        os.environ["STRIPE_PRICE_PREMIUM"] = "price_premium_abc"
        os.environ["STRIPE_PRICE_ULTRA"] = "price_ultra_xyz"

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env_backup)

    @patch("stripe_service.stripe")
    def test_create_customer(self, mock_stripe):
        mock_stripe.Customer.create.return_value = {"id": "cus_123"}
        result = stripe_service.create_customer("eleve@gmail.com", name="Eleve")
        mock_stripe.Customer.create.assert_called_once_with(email="eleve@gmail.com", name="Eleve")
        self.assertEqual(result["id"], "cus_123")

    @patch("stripe_service.stripe")
    def test_create_customer_avec_idempotency_key(self, mock_stripe):
        """Durcissement production : la clé, quand fournie, est transmise
        telle quelle au SDK Stripe — c'est elle qui permet à Stripe de
        dédupliquer deux Customer.create concurrents pour le même
        utilisateur (voir test_stripe_checkout_concurrency.py)."""
        mock_stripe.Customer.create.return_value = {"id": "cus_123"}
        stripe_service.create_customer("eleve@gmail.com", name="Eleve", idempotency_key="novamath-customer-42")
        mock_stripe.Customer.create.assert_called_once_with(
            email="eleve@gmail.com", name="Eleve", idempotency_key="novamath-customer-42",
        )

    @patch("stripe_service.stripe")
    def test_get_customer(self, mock_stripe):
        mock_stripe.Customer.retrieve.return_value = {"id": "cus_123"}
        result = stripe_service.get_customer("cus_123")
        mock_stripe.Customer.retrieve.assert_called_once_with("cus_123")
        self.assertEqual(result["id"], "cus_123")

    @patch("stripe_service.stripe")
    def test_create_checkout_session(self, mock_stripe):
        mock_stripe.checkout.Session.create.return_value = {"id": "cs_123", "url": "https://checkout.stripe.com/x"}
        result = stripe_service.create_checkout_session(
            customer_id="cus_123", plan=Plan.PREMIUM,
            success_url="https://app/success", cancel_url="https://app/cancel",
        )
        mock_stripe.checkout.Session.create.assert_called_once_with(
            customer="cus_123",
            mode="subscription",
            payment_method_types=["card"],
            line_items=[{"price": "price_premium_abc", "quantity": 1}],
            success_url="https://app/success",
            cancel_url="https://app/cancel",
        )
        self.assertEqual(result["url"], "https://checkout.stripe.com/x")

    @patch("stripe_service.stripe")
    def test_create_checkout_session_avec_idempotency_key(self, mock_stripe):
        mock_stripe.checkout.Session.create.return_value = {"id": "cs_123", "url": "https://checkout.stripe.com/x"}
        stripe_service.create_checkout_session(
            customer_id="cus_123", plan=Plan.PREMIUM,
            success_url="https://app/success", cancel_url="https://app/cancel",
            idempotency_key="novamath-checkout-42-premium-1000",
        )
        mock_stripe.checkout.Session.create.assert_called_once_with(
            customer="cus_123",
            mode="subscription",
            payment_method_types=["card"],
            line_items=[{"price": "price_premium_abc", "quantity": 1}],
            success_url="https://app/success",
            cancel_url="https://app/cancel",
            idempotency_key="novamath-checkout-42-premium-1000",
        )

    @patch("stripe_service.stripe")
    def test_create_checkout_session_plan_inconnu(self, mock_stripe):
        with self.assertRaises(stripe_service.StripePlanUnknown):
            stripe_service.create_checkout_session(
                customer_id="cus_123", plan=Plan.FREE,
                success_url="https://app/success", cancel_url="https://app/cancel",
            )
        mock_stripe.checkout.Session.create.assert_not_called()

    @patch("stripe_service.stripe")
    def test_get_subscription(self, mock_stripe):
        mock_stripe.Subscription.retrieve.return_value = {"id": "sub_123"}
        result = stripe_service.get_subscription("sub_123")
        mock_stripe.Subscription.retrieve.assert_called_once_with("sub_123")
        self.assertEqual(result["id"], "sub_123")

    @patch("stripe_service.stripe")
    def test_get_payment(self, mock_stripe):
        mock_stripe.PaymentIntent.retrieve.return_value = {"id": "pi_123"}
        result = stripe_service.get_payment("pi_123")
        mock_stripe.PaymentIntent.retrieve.assert_called_once_with("pi_123")
        self.assertEqual(result["id"], "pi_123")

    @patch("stripe_service.stripe")
    def test_cancel_subscription(self, mock_stripe):
        mock_stripe.Subscription.cancel.return_value = {"id": "sub_123", "status": "canceled"}
        result = stripe_service.cancel_subscription("sub_123")
        mock_stripe.Subscription.cancel.assert_called_once_with("sub_123")
        self.assertEqual(result["status"], "canceled")

    @patch("stripe_service.stripe")
    def test_change_plan(self, mock_stripe):
        mock_stripe.Subscription.retrieve.return_value = {
            "items": {"data": [{"id": "si_123", "price": {"id": "price_premium_abc"}}]}
        }
        mock_stripe.Subscription.modify.return_value = {"id": "sub_123"}
        result = stripe_service.change_plan("sub_123", Plan.ULTRA)
        mock_stripe.Subscription.modify.assert_called_once_with(
            "sub_123",
            items=[{"id": "si_123", "price": "price_ultra_xyz"}],
            proration_behavior="create_prorations",
        )
        self.assertEqual(result["id"], "sub_123")

    @patch("stripe_service.stripe")
    def test_get_checkout_session(self, mock_stripe):
        mock_stripe.checkout.Session.retrieve.return_value = {"id": "cs_123"}
        result = stripe_service.get_checkout_session("cs_123")
        mock_stripe.checkout.Session.retrieve.assert_called_once_with("cs_123")
        self.assertEqual(result["id"], "cs_123")

    @patch("stripe_service.stripe")
    def test_create_billing_portal_session(self, mock_stripe):
        mock_stripe.billing_portal.Session.create.return_value = {"url": "https://billing.stripe.com/x"}
        result = stripe_service.create_billing_portal_session("cus_123", "https://app/abonnement.html")
        mock_stripe.billing_portal.Session.create.assert_called_once_with(
            customer="cus_123", return_url="https://app/abonnement.html",
        )
        self.assertEqual(result["url"], "https://billing.stripe.com/x")

    @patch("stripe_service.stripe")
    def test_list_payment_methods(self, mock_stripe):
        mock_stripe.PaymentMethod.list.return_value = {"data": [{"id": "pm_123"}]}
        result = stripe_service.list_payment_methods("cus_123")
        mock_stripe.PaymentMethod.list.assert_called_once_with(customer="cus_123", type="card")
        self.assertEqual(result["data"][0]["id"], "pm_123")

    @patch("stripe_service.stripe")
    def test_list_invoices(self, mock_stripe):
        mock_stripe.Invoice.list.return_value = {"data": [{"id": "in_123"}]}
        result = stripe_service.list_invoices("cus_123", limit=5)
        mock_stripe.Invoice.list.assert_called_once_with(customer="cus_123", limit=5)
        self.assertEqual(result["data"][0]["id"], "in_123")

    @patch("stripe_service.stripe")
    def test_schedule_downgrade(self, mock_stripe):
        mock_stripe.SubscriptionSchedule.create.return_value = {
            "id": "sub_sched_123",
            "phases": [{"items": [{"price": "price_ultra_xyz"}], "start_date": 100, "end_date": 200}],
        }
        mock_stripe.SubscriptionSchedule.modify.return_value = {"id": "sub_sched_123"}
        result = stripe_service.schedule_downgrade("sub_123", Plan.PREMIUM)
        mock_stripe.SubscriptionSchedule.create.assert_called_once_with(from_subscription="sub_123")
        mock_stripe.SubscriptionSchedule.modify.assert_called_once_with(
            "sub_sched_123",
            phases=[
                {"items": [{"price": "price_ultra_xyz"}], "start_date": 100, "end_date": 200},
                {"items": [{"price": "price_premium_abc", "quantity": 1}]},
            ],
        )
        self.assertEqual(result["id"], "sub_sched_123")

    @patch("stripe_service.stripe")
    def test_schedule_downgrade_plan_inconnu(self, mock_stripe):
        with self.assertRaises(stripe_service.StripePlanUnknown):
            stripe_service.schedule_downgrade("sub_123", Plan.FREE)
        mock_stripe.SubscriptionSchedule.create.assert_not_called()


class TestValidateStripePrices(unittest.TestCase):
    """Chantier "Robustesse Stripe" (2026-08-27) : validate_stripe_prices()
    vérifie, via un appel réel à Price.retrieve (mocké ici), que
    STRIPE_PRICE_PREMIUM/STRIPE_PRICE_ULTRA valent bien 699/1299 centimes
    (voir stripe_service.STRIPE_EXPECTED_AMOUNTS_CENTS). Jamais câblée au
    démarrage ni à un health check — fonction explicite uniquement."""

    def setUp(self):
        self._env_backup = dict(os.environ)
        os.environ["STRIPE_SECRET_KEY"] = "sk_test_123"
        os.environ["STRIPE_PRICE_PREMIUM"] = "price_premium_abc"
        os.environ["STRIPE_PRICE_ULTRA"] = "price_ultra_xyz"

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env_backup)

    @patch("stripe_service.stripe")
    def test_montants_corrects_ne_levent_rien(self, mock_stripe):
        mock_stripe.Price.retrieve.side_effect = lambda price_id: (
            {"id": "price_premium_abc", "unit_amount": 699}
            if price_id == "price_premium_abc"
            else {"id": "price_ultra_xyz", "unit_amount": 1299}
        )
        stripe_service.validate_stripe_prices()  # ne doit lever aucune exception

    @patch("stripe_service.stripe")
    def test_premium_montant_incorrect_leve_stripe_price_mismatch(self, mock_stripe):
        mock_stripe.Price.retrieve.side_effect = lambda price_id: (
            {"id": "price_premium_abc", "unit_amount": 500}
            if price_id == "price_premium_abc"
            else {"id": "price_ultra_xyz", "unit_amount": 1299}
        )
        with self.assertRaises(stripe_service.StripePriceMismatch) as ctx:
            stripe_service.validate_stripe_prices()
        self.assertIn("price_premium_abc", str(ctx.exception))
        self.assertIn("699", str(ctx.exception))

    @patch("stripe_service.stripe")
    def test_ultra_montant_incorrect_leve_stripe_price_mismatch(self, mock_stripe):
        mock_stripe.Price.retrieve.side_effect = lambda price_id: (
            {"id": "price_premium_abc", "unit_amount": 699}
            if price_id == "price_premium_abc"
            else {"id": "price_ultra_xyz", "unit_amount": 999}
        )
        with self.assertRaises(stripe_service.StripePriceMismatch) as ctx:
            stripe_service.validate_stripe_prices()
        self.assertIn("price_ultra_xyz", str(ctx.exception))
        self.assertIn("1299", str(ctx.exception))

    @patch("stripe_service.stripe")
    def test_price_inexistant_leve_une_erreur_stripe_propre(self, mock_stripe):
        mock_stripe.Price.retrieve.side_effect = stripe.error.InvalidRequestError(
            "No such price: 'price_premium_abc'", param="id",
        )
        with self.assertRaises(stripe.error.StripeError):
            stripe_service.validate_stripe_prices()

    def test_stripe_non_configure_ne_leve_rien(self):
        os.environ.pop("STRIPE_SECRET_KEY", None)
        stripe_service.validate_stripe_prices()  # silencieux, comportement existant conservé

    @patch("stripe_service.stripe")
    def test_aucun_secret_dans_le_message_derreur(self, mock_stripe):
        mock_stripe.Price.retrieve.side_effect = lambda price_id: (
            {"id": "price_premium_abc", "unit_amount": 1}
            if price_id == "price_premium_abc"
            else {"id": "price_ultra_xyz", "unit_amount": 1299}
        )
        with self.assertRaises(stripe_service.StripePriceMismatch) as ctx:
            stripe_service.validate_stripe_prices()
        message = str(ctx.exception)
        self.assertNotIn("sk_test_123", message)
        self.assertNotIn(os.environ["STRIPE_SECRET_KEY"], message)


class TestWebhook(unittest.TestCase):
    def setUp(self):
        self._env_backup = dict(os.environ)
        os.environ["STRIPE_SECRET_KEY"] = "sk_test_123"

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env_backup)

    def test_construct_webhook_event_sans_secret_configure(self):
        os.environ.pop("STRIPE_WEBHOOK_SECRET", None)
        with self.assertRaises(stripe_service.StripeNotConfigured):
            stripe_service.construct_webhook_event(b"{}", "sig")

    def test_construct_webhook_event_avec_placeholder_env_example(self):
        os.environ["STRIPE_WEBHOOK_SECRET"] = "whsec_xxx"
        with self.assertRaises(stripe_service.StripeNotConfigured):
            stripe_service.construct_webhook_event(b"{}", "sig")

    @patch("stripe_service.stripe")
    def test_construct_webhook_event(self, mock_stripe):
        os.environ["STRIPE_WEBHOOK_SECRET"] = "whsec_123"
        mock_stripe.Webhook.construct_event.return_value = {"type": "checkout.session.completed"}
        event = stripe_service.construct_webhook_event(b"{}", "sig_header")
        mock_stripe.Webhook.construct_event.assert_called_once_with(b"{}", "sig_header", "whsec_123")
        self.assertEqual(event["type"], "checkout.session.completed")


if __name__ == "__main__":
    unittest.main()
