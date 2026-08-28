"""
Suite de bout en bout des routes Billing (webapp/server.py) : GET
/api/billing/status, POST /api/billing/customer-portal, POST
/api/billing/change-plan. Vérifie le login_required/csrf_protect, la
traduction des exceptions billing_service en réponses HTTP, et qu'aucune de
ces routes n'écrit jamais en base (le webhook reste l'unique source de
vérité, voir tests/test_stripe_webhook_service.py).
"""
import random
import unittest
from unittest.mock import patch

import db
import server
from plan_service import Plan


def _register(client):
    email = f"test{random.randint(1_000_000, 9_999_999)}@gmail.com"
    username = f"testuser{random.randint(100_000, 999_999)}"
    resp = client.post("/api/auth/register", json={
        "email": email, "username": username, "pseudo": "Test",
        "birth_date": "2000-01-01",
        "password": "MotDePasse123!", "confirm_password": "MotDePasse123!",
        "accept_terms": True, "accept_privacy": True,
    })
    user = resp.get_json()["user"]
    csrf = client.get_cookie("nm_csrf").value
    return user, {"X-CSRF-Token": csrf}


def _set_plan(user_id, plan, customer_id="cus_123", subscription_id="sub_123", status="active"):
    db.set_stripe_customer_id(user_id, customer_id)
    db.set_stripe_subscription(user_id, subscription_id, plan.value, status)


class TestBillingStatusRoute(unittest.TestCase):
    def setUp(self):
        self.client = server.app.test_client()
        self.user, self.headers = _register(self.client)

    def test_anonyme_est_rejete(self):
        anon = server.app.test_client()
        resp = anon.get("/api/billing/status")
        self.assertEqual(resp.status_code, 401)

    def test_compte_gratuit_sans_customer_stripe(self):
        resp = self.client.get("/api/billing/status")
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertEqual(body["plan"], "free")
        self.assertFalse(body["customer_portal_available"])
        self.assertEqual(body["invoices"], [])

    @patch("billing_service.stripe_service.list_invoices", return_value={"data": []})
    @patch("billing_service.stripe_service.list_payment_methods", return_value={"data": []})
    @patch("billing_service.stripe_service.get_subscription")
    @patch("billing_service.stripe_service.get_customer")
    def test_compte_premium_avec_customer_stripe(
        self, mock_get_customer, mock_get_subscription, mock_list_pm, mock_list_invoices,
    ):
        mock_get_customer.return_value = {"id": "cus_123", "email": "eleve@gmail.com"}
        mock_get_subscription.return_value = {
            "id": "sub_123", "current_period_end": 1_700_000_000, "cancel_at_period_end": False,
        }
        _set_plan(self.user["id"], Plan.PREMIUM)

        resp = self.client.get("/api/billing/status")
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertEqual(body["plan"], "premium")
        self.assertTrue(body["customer_portal_available"])
        self.assertEqual(body["billing_email"], "eleve@gmail.com")
        self.assertEqual(body["renew_at"], 1_700_000_000)


class TestCustomerPortalRoute(unittest.TestCase):
    def setUp(self):
        self.client = server.app.test_client()
        self.user, self.headers = _register(self.client)

    def test_anonyme_est_rejete(self):
        anon = server.app.test_client()
        resp = anon.post("/api/billing/customer-portal")
        self.assertEqual(resp.status_code, 401)

    def test_sans_csrf_est_rejete(self):
        resp = self.client.post("/api/billing/customer-portal")
        self.assertEqual(resp.status_code, 403)

    def test_sans_customer_stripe(self):
        resp = self.client.post("/api/billing/customer-portal", headers=self.headers)
        self.assertEqual(resp.status_code, 400)
        self.assertNotEqual(resp.get_json().get("error"), "premium_required")

    @patch("billing_service.stripe_service.create_billing_portal_session")
    def test_avec_customer_stripe_renvoie_portal_url(self, mock_create_session):
        mock_create_session.return_value = {"url": "https://billing.stripe.com/x"}
        _set_plan(self.user["id"], Plan.PREMIUM)

        resp = self.client.post("/api/billing/customer-portal", headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["portal_url"], "https://billing.stripe.com/x")
        mock_create_session.assert_called_once()
        self.assertEqual(mock_create_session.call_args[0][0], "cus_123")


class TestChangePlanRoute(unittest.TestCase):
    def setUp(self):
        self.client = server.app.test_client()
        self.user, self.headers = _register(self.client)

    def test_anonyme_est_rejete(self):
        anon = server.app.test_client()
        resp = anon.post("/api/billing/change-plan", json={"plan": "ultra"})
        self.assertEqual(resp.status_code, 401)

    def test_sans_csrf_est_rejete(self):
        resp = self.client.post("/api/billing/change-plan", json={"plan": "ultra"})
        self.assertEqual(resp.status_code, 403)

    def test_plan_invalide(self):
        resp = self.client.post("/api/billing/change-plan", json={"plan": "bad"}, headers=self.headers)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.get_json()["field"], "plan")

    def test_sans_abonnement_actif(self):
        resp = self.client.post("/api/billing/change-plan", json={"plan": "premium"}, headers=self.headers)
        self.assertEqual(resp.status_code, 400)

    @patch("billing_service.stripe_service.change_plan")
    def test_upgrade_premium_vers_ultra(self, mock_change_plan):
        mock_change_plan.return_value = {"id": "sub_123"}
        _set_plan(self.user["id"], Plan.PREMIUM)

        resp = self.client.post("/api/billing/change-plan", json={"plan": "ultra"}, headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        mock_change_plan.assert_called_once_with("sub_123", Plan.ULTRA)
        # N'écrit jamais en base : le plan reste inchangé tant que le webhook
        # n'a pas confirmé le changement côté Stripe.
        self.assertEqual(db.get_user_by_id(self.user["id"])["plan"], "premium")

    @patch("billing_service.stripe_service.schedule_downgrade")
    def test_downgrade_ultra_vers_premium(self, mock_schedule_downgrade):
        mock_schedule_downgrade.return_value = {"id": "sub_sched_123"}
        _set_plan(self.user["id"], Plan.ULTRA)

        resp = self.client.post("/api/billing/change-plan", json={"plan": "premium"}, headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        mock_schedule_downgrade.assert_called_once_with("sub_123", Plan.PREMIUM)
        self.assertEqual(db.get_user_by_id(self.user["id"])["plan"], "ultra")

    def test_meme_plan_est_rejete(self):
        _set_plan(self.user["id"], Plan.PREMIUM)
        resp = self.client.post("/api/billing/change-plan", json={"plan": "premium"}, headers=self.headers)
        self.assertEqual(resp.status_code, 400)


if __name__ == "__main__":
    unittest.main()
