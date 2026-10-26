"""
Suite de admin_finance_service.py — audit admin (2026-10-22) :

1. `get_subscriptions_overview()` reste la RÉFÉRENCE UNIQUE pour les
   indicateurs d'abonnement agrégés ("Nouveaux abonnements"/"Résiliations"
   sur une fenêtre glissante) après leur suppression du module Abonnements
   (voir test_admin_subscriptions_service.py) — vérifie que Finance les
   affiche toujours correctement, donc sans perte de donnée pour qui a
   accès à ce module (SUPER_ADMIN).
2. MRR estimé : formule `(Premium actifs x 699) + (Ultra actifs x 1299)`
   (STRIPE_EXPECTED_AMOUNTS_CENTS, voir stripe_service.py) — toujours
   accompagnée d'une note documentant explicitement la limite (suppose
   qu'aucune remise/coupon Stripe n'est appliqué, non détectable sans appel
   réseau réel). Pas de régression sur cette documentation.
3. Permissions : /api/admin/finance/* exige SUPER_ADMIN (voir
   admin_nav_service.py, Role.SUPER_ADMIN) — un ADMIN simple reste bloqué.

Aucun appel réseau Stripe dans ce fichier : seules des fonctions purement
locales (db.py) sont exercées (get_subscriptions_overview ne touche jamais
stripe_access_guard/stripe_financial_service).
"""
import random
import unittest

import admin_finance_service
import db
import server
from plan_service import Plan
from role_service import Role


def _register(client):
    email = f"financeaudit{random.randint(1_000_000, 9_999_999)}@gmail.com"
    username = f"financeaudit{random.randint(100_000, 999_999)}"
    resp = client.post("/api/auth/register", json={
        "email": email, "username": username, "pseudo": "Test",
        "birth_date": "2000-01-01",
        "password": "MotDePasse123!", "confirm_password": "MotDePasse123!",
        "accept_terms": True, "accept_privacy": True,
    })
    return resp.get_json()["user"]


class TestSubscriptionsOverviewReferenceUnique(unittest.TestCase):
    def test_contient_toujours_new_subscriptions_et_cancellations(self):
        overview = admin_finance_service.get_subscriptions_overview()
        self.assertIn("new_subscriptions", overview)
        self.assertIn("cancellations", overview)
        self.assertTrue(overview["new_subscriptions"]["available"])
        self.assertTrue(overview["cancellations"]["available"])
        self.assertIsInstance(overview["new_subscriptions"]["value"], int)
        self.assertIsInstance(overview["cancellations"]["value"], int)

    def test_fenetre_temporelle_documentee_dans_les_notes(self):
        overview = admin_finance_service.get_subscriptions_overview()
        self.assertIn(str(overview["window_days"]), overview["new_subscriptions"]["note"])
        self.assertIn(str(overview["window_days"]), overview["cancellations"]["note"])


class TestMrrEstimeEtSesLimites(unittest.TestCase):
    def _user(self, plan, stripe_status):
        email = f"mrr{random.randint(1_000_000, 9_999_999)}@gmail.com"
        username = f"mrr{random.randint(100_000, 999_999)}"
        user_id = db.create_user(email, username, "Test", "hash")
        # set_stripe_subscription écrit à la fois plan/stripe_subscription_id/
        # stripe_subscription_status (voir db.py) — aucun appel séparé requis.
        db.set_stripe_subscription(user_id, f"sub_{user_id}", plan, stripe_status)
        return user_id

    def setUp(self):
        self._user_ids = []

    def tearDown(self):
        for uid in self._user_ids:
            db.delete_user(uid)

    def test_mrr_suit_exactement_la_formule_documentee(self):
        before = admin_finance_service.get_subscriptions_overview()
        premium_before = before["active_subscriptions_by_plan"]["value"].get(Plan.PREMIUM.value, 0)
        ultra_before = before["active_subscriptions_by_plan"]["value"].get(Plan.ULTRA.value, 0)

        self._user_ids.append(self._user(Plan.PREMIUM.value, "active"))
        self._user_ids.append(self._user(Plan.ULTRA.value, "trialing"))

        after = admin_finance_service.get_subscriptions_overview()
        premium_after = after["active_subscriptions_by_plan"]["value"].get(Plan.PREMIUM.value, 0)
        ultra_after = after["active_subscriptions_by_plan"]["value"].get(Plan.ULTRA.value, 0)
        self.assertEqual(premium_after, premium_before + 1)
        self.assertEqual(ultra_after, ultra_before + 1)

        expected_delta_cents = 699 + 1299
        self.assertEqual(
            after["mrr_cents"]["value"] - before["mrr_cents"]["value"],
            expected_delta_cents,
        )

    def test_mrr_documente_explicitement_sa_limite_estimation(self):
        overview = admin_finance_service.get_subscriptions_overview()
        note = overview["mrr_cents"]["note"].lower()
        self.assertIn("estimation", note)
        self.assertIn("remise", note)


class TestPermissionsFinanceReserveesAuSuperAdmin(unittest.TestCase):
    def setUp(self):
        self.client = server.app.test_client()

    def test_admin_simple_recoit_403_sur_finance(self):
        user = _register(self.client)
        db.set_user_role(user["id"], Role.ADMIN.value)
        resp = self.client.get("/api/admin/finance/overview")
        self.assertEqual(resp.status_code, 403)

    def test_super_admin_recoit_200_sur_finance(self):
        user = _register(self.client)
        db.set_user_role(user["id"], Role.SUPER_ADMIN.value)
        resp = self.client.get("/api/admin/finance/overview")
        self.assertEqual(resp.status_code, 200)
        payload = resp.get_json()
        self.assertIn("subscriptions", payload)
        self.assertIn("stripe_environment", payload)


if __name__ == "__main__":
    unittest.main()
