"""
Suite du service d'agrégation Stripe Billing (webapp/billing_service.py) :
statut de facturation complet, création de session du Portail client,
changement de plan (upgrade immédiat / downgrade programmé). Aucun appel
réseau réel : stripe_service est entièrement mocké, comme les autres suites
Stripe du projet.
"""
import os
import unittest
from unittest.mock import patch

import billing_service
import stripe
from plan_service import Plan


def _user(**overrides):
    base = {
        "id": 1, "plan": "free",
        "stripe_customer_id": None, "stripe_subscription_id": None,
        "stripe_subscription_status": None,
    }
    base.update(overrides)
    return base


class TestGetBillingStatus(unittest.TestCase):
    def test_sans_customer_stripe(self):
        status = billing_service.get_billing_status(_user())
        self.assertEqual(status["plan"], "free")
        self.assertFalse(status["customer_portal_available"])
        self.assertIsNone(status["renew_at"])
        self.assertIsNone(status["cancel_at"])
        self.assertIsNone(status["payment_method"])
        self.assertEqual(status["invoices"], [])

    @patch("billing_service.stripe_service.list_invoices")
    @patch("billing_service.stripe_service.list_payment_methods")
    @patch("billing_service.stripe_service.get_subscription")
    @patch("billing_service.stripe_service.get_customer")
    def test_avec_customer_et_abonnement_actif(
        self, mock_get_customer, mock_get_subscription, mock_list_pm, mock_list_invoices,
    ):
        mock_get_customer.return_value = {"id": "cus_123", "email": "eleve@gmail.com"}
        mock_get_subscription.return_value = {
            "id": "sub_123", "current_period_end": 1_700_000_000, "cancel_at_period_end": False,
        }
        mock_list_pm.return_value = {"data": [{"card": {"brand": "visa", "last4": "4242", "exp_month": 8, "exp_year": 2027}}]}
        mock_list_invoices.return_value = {"data": [{
            "id": "in_1", "amount_paid": 699, "currency": "eur", "status": "paid",
            "created": 1_690_000_000, "invoice_pdf": "https://pdf", "hosted_invoice_url": "https://hosted",
        }]}

        user = _user(plan="premium", stripe_customer_id="cus_123", stripe_subscription_id="sub_123", stripe_subscription_status="active")
        status = billing_service.get_billing_status(user)

        self.assertEqual(status["plan"], "premium")
        self.assertEqual(status["subscription_status"], "active")
        self.assertTrue(status["customer_portal_available"])
        self.assertEqual(status["billing_email"], "eleve@gmail.com")
        self.assertEqual(status["renew_at"], 1_700_000_000)
        self.assertIsNone(status["cancel_at"])
        self.assertEqual(status["payment_method"]["brand"], "visa")
        self.assertEqual(status["payment_method"]["last4"], "4242")
        self.assertEqual(len(status["invoices"]), 1)
        self.assertEqual(status["invoices"][0]["amount_paid"], 699)

    @patch("billing_service.stripe_service.get_subscription")
    @patch("billing_service.stripe_service.get_customer")
    def test_annulation_programmee_expose_cancel_at(self, mock_get_customer, mock_get_subscription):
        mock_get_customer.return_value = {"id": "cus_123", "email": "eleve@gmail.com"}
        mock_get_subscription.return_value = {
            "id": "sub_123", "current_period_end": 1_700_000_000,
            "cancel_at_period_end": True, "cancel_at": 1_700_000_000,
        }
        with patch("billing_service.stripe_service.list_payment_methods", return_value={"data": []}), \
             patch("billing_service.stripe_service.list_invoices", return_value={"data": []}):
            user = _user(plan="ultra", stripe_customer_id="cus_123", stripe_subscription_id="sub_123", stripe_subscription_status="active")
            status = billing_service.get_billing_status(user)

        self.assertEqual(status["cancel_at"], 1_700_000_000)

    @patch("billing_service.stripe_service.get_customer")
    def test_erreur_stripe_degrade_sans_planter(self, mock_get_customer):
        mock_get_customer.side_effect = stripe.error.StripeError("indisponible")
        user = _user(plan="premium", stripe_customer_id="cus_123", stripe_subscription_status="active")
        status = billing_service.get_billing_status(user)
        # Best-effort : le plan connu en base reste affiché malgré l'échec Stripe.
        self.assertEqual(status["plan"], "premium")
        self.assertTrue(status["customer_portal_available"])
        self.assertIsNone(status["billing_email"])


class TestCreatePortalSession(unittest.TestCase):
    def test_sans_customer_leve_no_stripe_customer(self):
        with self.assertRaises(billing_service.NoStripeCustomer):
            billing_service.create_portal_session(_user(), "https://app/abonnement.html")

    @patch("billing_service.stripe_service.create_billing_portal_session")
    def test_avec_customer_renvoie_lurl(self, mock_create_session):
        mock_create_session.return_value = {"url": "https://billing.stripe.com/x"}
        user = _user(stripe_customer_id="cus_123")
        url = billing_service.create_portal_session(user, "https://app/abonnement.html")
        mock_create_session.assert_called_once_with("cus_123", "https://app/abonnement.html")
        self.assertEqual(url, "https://billing.stripe.com/x")


class TestChangePlan(unittest.TestCase):
    def test_sans_abonnement_actif_leve_no_active_subscription(self):
        with self.assertRaises(billing_service.NoActiveSubscription):
            billing_service.change_plan(_user(plan="free"), Plan.PREMIUM)

    def test_meme_plan_leve_same_plan(self):
        user = _user(plan="premium", stripe_subscription_id="sub_123")
        with self.assertRaises(billing_service.SamePlan):
            billing_service.change_plan(user, Plan.PREMIUM)

    @patch("billing_service.stripe_service.change_plan")
    def test_upgrade_est_immediat(self, mock_change_plan):
        user = _user(plan="premium", stripe_subscription_id="sub_123")
        billing_service.change_plan(user, Plan.ULTRA)
        mock_change_plan.assert_called_once_with("sub_123", Plan.ULTRA)

    @patch("billing_service.stripe_service.schedule_downgrade")
    def test_downgrade_est_programme(self, mock_schedule_downgrade):
        user = _user(plan="ultra", stripe_subscription_id="sub_123")
        billing_service.change_plan(user, Plan.PREMIUM)
        mock_schedule_downgrade.assert_called_once_with("sub_123", Plan.PREMIUM)


if __name__ == "__main__":
    unittest.main()
