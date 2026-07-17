"""
Suite du service Stripe (webapp/stripe_service.py) : aucun appel réseau réel,
le SDK stripe est entièrement mocké (unittest.mock.patch) — comme les autres
suites du projet, ces tests doivent pouvoir tourner hors ligne et sans clé
Stripe valide.
"""
import os
import unittest
from unittest.mock import MagicMock, patch

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

    @patch("stripe_service.stripe")
    def test_construct_webhook_event(self, mock_stripe):
        os.environ["STRIPE_WEBHOOK_SECRET"] = "whsec_123"
        mock_stripe.Webhook.construct_event.return_value = {"type": "checkout.session.completed"}
        event = stripe_service.construct_webhook_event(b"{}", "sig_header")
        mock_stripe.Webhook.construct_event.assert_called_once_with(b"{}", "sig_header", "whsec_123")
        self.assertEqual(event["type"], "checkout.session.completed")


if __name__ == "__main__":
    unittest.main()
