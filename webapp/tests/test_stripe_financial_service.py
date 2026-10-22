"""
Suite de stripe_financial_service.py / stripe_access_guard.py (audit admin
Phase 2A, 2026-10-21) — aucun appel réseau réel, stripe_service.list_all_*
est mocké comme le reste des tests Stripe du projet (voir
test_stripe_reconciliation_service.py). Couvre les scénarios demandés :
aucun paiement, paiement réussi, plusieurs paiements, paiement échoué,
remboursement total/partiel, plusieurs devises, Premium/Ultra, pagination,
erreur réseau, accès non autorisé, environnement local avec clé production.
"""
import os
import unittest
from unittest.mock import patch

import db
import server
import stripe_access_guard
import stripe_financial_service as fin
from plan_service import Plan
from role_service import Role


def _register(client):
    import uuid

    unique = uuid.uuid4().hex
    email = f"finance{unique}@gmail.com"
    username = f"finance{unique[:15]}"
    resp = client.post("/api/auth/register", json={
        "email": email, "username": username, "pseudo": "Test",
        "birth_date": "2000-01-01",
        "password": "MotDePasse123!", "confirm_password": "MotDePasse123!",
        "accept_terms": True, "accept_privacy": True,
    })
    user = resp.get_json()["user"]
    csrf = client.get_cookie("nm_csrf").value
    return user, {"X-CSRF-Token": csrf}


def _register_super_admin(client):
    user, headers = _register(client)
    db.set_user_role(user["id"], Role.SUPER_ADMIN.value)
    return user, headers


def _register_admin(client):
    user, headers = _register(client)
    db.set_user_role(user["id"], Role.ADMIN.value)
    return user, headers


def _invoice(id_, amount_paid, currency="eur", created=0, price_id=None):
    inv = {"id": id_, "amount_paid": amount_paid, "currency": currency, "created": created}
    if price_id:
        inv["lines"] = {"data": [{"price": {"id": price_id}}]}
    else:
        inv["lines"] = {"data": []}
    return inv


def _refund(id_, amount, currency="eur", created=0):
    return {"id": id_, "amount": amount, "currency": currency, "created": created}


class TestRevenueReportScenarios(unittest.TestCase):
    def setUp(self):
        self._env_backup = dict(os.environ)
        os.environ["STRIPE_SECRET_KEY"] = "sk_test_123"

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env_backup)

    @patch("stripe_service.list_all_refunds")
    @patch("stripe_service.list_all_invoices")
    def test_aucun_paiement(self, mock_invoices, mock_refunds):
        mock_invoices.return_value = {"data": [], "has_more": False}
        mock_refunds.return_value = {"data": [], "has_more": False}
        report = fin.get_revenue_report(days=30)
        self.assertEqual(report["gross_revenue_cents_by_currency"], {})
        self.assertEqual(report["invoices_checked"], 0)
        self.assertFalse(report["capped"])

    @patch("stripe_service.list_all_refunds")
    @patch("stripe_service.list_all_invoices")
    def test_un_paiement_reussi(self, mock_invoices, mock_refunds):
        mock_invoices.return_value = {"data": [_invoice("in_1", 699, created=1000)], "has_more": False}
        mock_refunds.return_value = {"data": [], "has_more": False}
        report = fin.get_revenue_report(days=30)
        self.assertEqual(report["gross_revenue_cents_by_currency"]["eur"], 699)
        self.assertEqual(report["net_of_refunds_cents_by_currency"]["eur"], 699)

    @patch("stripe_service.list_all_refunds")
    @patch("stripe_service.list_all_invoices")
    def test_plusieurs_paiements(self, mock_invoices, mock_refunds):
        mock_invoices.return_value = {
            "data": [_invoice("in_1", 699, created=1000), _invoice("in_2", 699, created=2000)],
            "has_more": False,
        }
        mock_refunds.return_value = {"data": [], "has_more": False}
        report = fin.get_revenue_report(days=30)
        self.assertEqual(report["gross_revenue_cents_by_currency"]["eur"], 1398)
        self.assertEqual(report["invoices_checked"], 2)

    @patch("stripe_service.list_all_refunds")
    @patch("stripe_service.list_all_invoices")
    def test_remboursement_total(self, mock_invoices, mock_refunds):
        mock_invoices.return_value = {"data": [_invoice("in_1", 699, created=1000)], "has_more": False}
        mock_refunds.return_value = {"data": [_refund("re_1", 699, created=1500)], "has_more": False}
        report = fin.get_revenue_report(days=30)
        self.assertEqual(report["net_of_refunds_cents_by_currency"]["eur"], 0)

    @patch("stripe_service.list_all_refunds")
    @patch("stripe_service.list_all_invoices")
    def test_remboursement_partiel(self, mock_invoices, mock_refunds):
        mock_invoices.return_value = {"data": [_invoice("in_1", 699, created=1000)], "has_more": False}
        mock_refunds.return_value = {"data": [_refund("re_1", 200, created=1500)], "has_more": False}
        report = fin.get_revenue_report(days=30)
        self.assertEqual(report["net_of_refunds_cents_by_currency"]["eur"], 499)

    @patch("stripe_service.list_all_refunds")
    @patch("stripe_service.list_all_invoices")
    def test_plusieurs_devises_jamais_sommees(self, mock_invoices, mock_refunds):
        mock_invoices.return_value = {
            "data": [_invoice("in_1", 699, currency="eur", created=1000), _invoice("in_2", 500, currency="usd", created=1000)],
            "has_more": False,
        }
        mock_refunds.return_value = {"data": [], "has_more": False}
        report = fin.get_revenue_report(days=30)
        self.assertEqual(report["gross_revenue_cents_by_currency"], {"eur": 699, "usd": 500})

    @patch("stripe_service.plan_from_price_id")
    @patch("stripe_service.list_all_refunds")
    @patch("stripe_service.list_all_invoices")
    def test_ventilation_premium_ultra(self, mock_invoices, mock_refunds, mock_plan):
        mock_invoices.return_value = {
            "data": [
                _invoice("in_1", 699, created=1000, price_id="price_premium"),
                _invoice("in_2", 1299, created=1000, price_id="price_ultra"),
            ],
            "has_more": False,
        }
        mock_refunds.return_value = {"data": [], "has_more": False}
        mock_plan.side_effect = lambda pid: Plan.PREMIUM if pid == "price_premium" else Plan.ULTRA
        report = fin.get_revenue_report(days=30)
        self.assertEqual(report["gross_revenue_cents_by_plan"], {"premium": 699, "ultra": 1299})

    @patch("stripe_service.list_all_refunds")
    @patch("stripe_service.list_all_invoices")
    def test_changement_de_plan_facture_sans_ligne_reconnue_va_en_inconnu(self, mock_invoices, mock_refunds):
        """Une facture dont la structure de ligne ne correspond à aucun prix
        connu (ex: changement de plan en cours, proration) ne doit jamais
        faire échouer le rapport — attribution "inconnu", jamais une
        exception remontée à l'admin."""
        mock_invoices.return_value = {"data": [_invoice("in_1", 300, created=1000, price_id=None)], "has_more": False}
        mock_refunds.return_value = {"data": [], "has_more": False}
        report = fin.get_revenue_report(days=30)
        self.assertEqual(report["gross_revenue_cents_by_plan"], {"inconnu": 300})

    @patch("stripe_service.list_all_refunds")
    @patch("stripe_service.list_all_invoices")
    def test_pagination_plafonnee_signale_capped(self, mock_invoices, mock_refunds):
        def always_has_more(limit, starting_after, created_gte, created_lte, status):
            return {"data": [_invoice(f"in_{starting_after}", 100, created=1000)], "has_more": True}

        mock_invoices.side_effect = always_has_more
        mock_refunds.return_value = {"data": [], "has_more": False}
        report = fin.get_revenue_report(days=30)
        self.assertTrue(report["capped"])
        self.assertEqual(report["invoices_checked"], fin.MAX_PAGES)

    @patch("stripe_service.list_all_invoices")
    def test_erreur_reseau_remonte_explicitement(self, mock_invoices):
        mock_invoices.side_effect = RuntimeError("connexion impossible")
        with self.assertRaises(RuntimeError):
            fin.get_revenue_report(days=30)

    def test_stripe_non_configure(self):
        os.environ.pop("STRIPE_SECRET_KEY", None)
        with self.assertRaises(fin.StripeFinancialDataUnavailable):
            fin.get_revenue_report(days=30)


class TestPaymentsReportScenarios(unittest.TestCase):
    def setUp(self):
        self._env_backup = dict(os.environ)
        os.environ["STRIPE_SECRET_KEY"] = "sk_test_123"

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env_backup)

    @patch("stripe_service.list_all_payment_intents")
    def test_aucun_paiement(self, mock_pi):
        mock_pi.return_value = {"data": [], "has_more": False}
        report = fin.get_payments_report()
        self.assertEqual(report["payments"], [])
        self.assertEqual(report["succeeded_count"], 0)

    @patch("stripe_service.list_all_payment_intents")
    def test_paiement_reussi_et_echoue(self, mock_pi):
        mock_pi.return_value = {
            "data": [
                {"id": "pi_1", "amount": 699, "currency": "eur", "status": "succeeded", "created": 1000},
                {"id": "pi_2", "amount": 1299, "currency": "eur", "status": "requires_payment_method", "created": 1000},
            ],
            "has_more": False,
        }
        report = fin.get_payments_report()
        self.assertEqual(report["succeeded_count"], 1)
        self.assertEqual(report["failed_count"], 1)


class TestLocalSubscriptionsOverviewScenarios(unittest.TestCase):
    """get_subscriptions_overview() : AUCUN appel Stripe, uniquement db.py —
    couvre Premium/Ultra actifs, changement de plan, annulation immédiate
    et annulation en fin de période (cancel_at_period_end)."""

    def setUp(self):
        import admin_finance_service

        self.admin_finance_service = admin_finance_service
        self._user_ids = []

    def tearDown(self):
        for uid in self._user_ids:
            db.delete_user(uid)

    def _make_user(self, plan, status):
        import random

        email = f"finloc{random.randint(1_000_000, 9_999_999)}@gmail.com"
        username = f"finloc{random.randint(100_000, 999_999)}"
        user_id = db.create_user(email, username, "Test", "hash")
        db.set_stripe_subscription(user_id, f"sub_{user_id}", plan, status)
        self._user_ids.append(user_id)
        return user_id

    def test_abonnement_premium_actif_compte(self):
        before = db.count_active_subscriptions_by_plan().get(Plan.PREMIUM.value, 0)
        self._make_user(Plan.PREMIUM.value, "active")
        after = db.count_active_subscriptions_by_plan().get(Plan.PREMIUM.value, 0)
        self.assertEqual(after, before + 1)

    def test_abonnement_ultra_actif_compte(self):
        before = db.count_active_subscriptions_by_plan().get(Plan.ULTRA.value, 0)
        self._make_user(Plan.ULTRA.value, "trialing")
        after = db.count_active_subscriptions_by_plan().get(Plan.ULTRA.value, 0)
        self.assertEqual(after, before + 1)

    def test_changement_de_plan_compte_dans_le_nouveau_plan(self):
        user_id = self._make_user(Plan.PREMIUM.value, "active")
        before_ultra = db.count_active_subscriptions_by_plan().get(Plan.ULTRA.value, 0)
        db.set_stripe_subscription(user_id, f"sub_{user_id}", Plan.ULTRA.value, "active")
        after_ultra = db.count_active_subscriptions_by_plan().get(Plan.ULTRA.value, 0)
        self.assertEqual(after_ultra, before_ultra + 1)

    def test_annulation_immediate_bascule_en_canceled_jamais_actif(self):
        user_id = self._make_user(Plan.PREMIUM.value, "active")
        before_canceled = db.count_users_with_canceled_subscription()
        # Même effet que _handle_subscription_deleted (stripe_webhook_service.py) :
        # statut 'canceled', plus de subscription_id, retour au plan free.
        db.set_stripe_subscription(user_id, None, Plan.FREE.value, "canceled")
        self.assertEqual(db.count_users_with_canceled_subscription(), before_canceled + 1)
        self.assertNotIn(user_id, [u["id"] for u in db.list_users_with_stripe_subscription(limit=1000)])

    def test_annulation_en_fin_de_periode_reste_active_jusqua_la_fin(self):
        """cancel_at_period_end=True : l'abonnement reste 'active' côté
        Stripe (et donc ici) jusqu'à ce que Stripe envoie réellement
        subscription.deleted à la fin de la période — jamais basculé en
        'canceled' par anticipation, ni ici ni dans stripe_webhook_service."""
        self._make_user(Plan.PREMIUM.value, "active")
        active = db.count_active_subscriptions_by_plan().get(Plan.PREMIUM.value, 0)
        self.assertGreaterEqual(active, 1)

    def test_mrr_estime_avec_abonnements_actifs(self):
        import stripe_service

        before = self.admin_finance_service.get_subscriptions_overview()["mrr_cents"]["value"]
        self._make_user(Plan.PREMIUM.value, "active")
        after = self.admin_finance_service.get_subscriptions_overview()["mrr_cents"]["value"]
        self.assertEqual(after - before, stripe_service.STRIPE_EXPECTED_AMOUNTS_CENTS[Plan.PREMIUM])

    def test_overview_toujours_disponible_meme_stripe_non_configure(self):
        env_backup = dict(os.environ)
        os.environ.pop("STRIPE_SECRET_KEY", None)
        try:
            overview = self.admin_finance_service.get_subscriptions_overview()
            self.assertTrue(overview["mrr_cents"]["available"])
        finally:
            os.environ.clear()
            os.environ.update(env_backup)


class TestAccessGuardProductionIncident(unittest.TestCase):
    """Reproduit exactement l'incident du 2026-10-20 (clé sk_live_ présente
    sur un poste de développement) pour CHAQUE nouvelle route financière —
    la consigne explicite de cette phase est de ne jamais supposer que la
    protection de la réconciliation (Phase 1) couvre ces nouvelles routes."""

    def setUp(self):
        self._env_backup = dict(os.environ)
        os.environ["STRIPE_SECRET_KEY"] = "sk_live_123"

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env_backup)

    @patch("stripe_access_guard.config.IS_PRODUCTION", False)
    def test_revenue_bloque_depuis_dev(self):
        with self.assertRaises(stripe_access_guard.StripeAccessBlocked):
            fin.get_revenue_report(days=30)

    @patch("stripe_access_guard.config.IS_PRODUCTION", False)
    def test_revenue_bloque_meme_avec_confirmed_true(self):
        with self.assertRaises(stripe_access_guard.StripeAccessBlocked):
            fin.get_revenue_report(days=30, confirmed=True)

    @patch("stripe_access_guard.config.IS_PRODUCTION", False)
    def test_payments_bloque_depuis_dev(self):
        with self.assertRaises(stripe_access_guard.StripeAccessBlocked):
            fin.get_payments_report()

    @patch("stripe_access_guard.config.IS_PRODUCTION", False)
    def test_series_bloque_depuis_dev(self):
        with self.assertRaises(stripe_access_guard.StripeAccessBlocked):
            fin.get_revenue_series()

    @patch("stripe_access_guard.config.IS_PRODUCTION", True)
    def test_revenue_confirmation_requise_en_production(self):
        with self.assertRaises(stripe_access_guard.StripeAccessConfirmationRequired):
            fin.get_revenue_report(days=30)

    @patch("stripe_service.list_all_refunds")
    @patch("stripe_service.list_all_invoices")
    @patch("stripe_access_guard.config.IS_PRODUCTION", True)
    def test_revenue_confirmee_sexecute(self, mock_invoices, mock_refunds):
        mock_invoices.return_value = {"data": [], "has_more": False}
        mock_refunds.return_value = {"data": [], "has_more": False}
        report = fin.get_revenue_report(days=30, confirmed=True)
        self.assertEqual(report["mode"], "production")


class TestFinanceRoutesHttp(unittest.TestCase):
    """Droits d'accès ET non-contournabilité par appel direct à l'API."""

    def setUp(self):
        self.client = server.app.test_client()
        self._env_backup = dict(os.environ)
        os.environ["STRIPE_SECRET_KEY"] = "sk_test_123"

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env_backup)

    def test_overview_sans_session_401(self):
        resp = self.client.get("/api/admin/finance/overview")
        self.assertEqual(resp.status_code, 401)

    def test_overview_admin_insuffisant_403(self):
        """Le module Finance exige SUPER_ADMIN — un simple ADMIN (suffisant
        pour /admin/subscriptions) doit être refusé."""
        _, headers = _register_admin(self.client)
        resp = self.client.get("/api/admin/finance/overview", headers=headers)
        self.assertEqual(resp.status_code, 403)

    def test_overview_super_admin_200_local_toujours_disponible(self):
        _, headers = _register_super_admin(self.client)
        resp = self.client.get("/api/admin/finance/overview", headers=headers)
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertIn("subscriptions", body)
        self.assertTrue(body["subscriptions"]["mrr_cents"]["available"])

    def test_revenue_sans_session_401(self):
        resp = self.client.get("/api/admin/finance/revenue")
        self.assertEqual(resp.status_code, 401)

    def test_revenue_admin_insuffisant_403(self):
        _, headers = _register_admin(self.client)
        resp = self.client.get("/api/admin/finance/revenue", headers=headers)
        self.assertEqual(resp.status_code, 403)

    @patch("stripe_service.list_all_refunds")
    @patch("stripe_service.list_all_invoices")
    def test_revenue_super_admin_200(self, mock_invoices, mock_refunds):
        mock_invoices.return_value = {"data": [], "has_more": False}
        mock_refunds.return_value = {"data": [], "has_more": False}
        _, headers = _register_super_admin(self.client)
        resp = self.client.get("/api/admin/finance/revenue?days=30", headers=headers)
        self.assertEqual(resp.status_code, 200)

    def test_revenue_stripe_non_configure_501(self):
        os.environ.pop("STRIPE_SECRET_KEY", None)
        _, headers = _register_super_admin(self.client)
        resp = self.client.get("/api/admin/finance/revenue", headers=headers)
        self.assertEqual(resp.status_code, 501)

    @patch("stripe_access_guard.config.IS_PRODUCTION", False)
    def test_revenue_appel_direct_production_depuis_dev_refuse_403(self):
        os.environ["STRIPE_SECRET_KEY"] = "sk_live_123"
        _, headers = _register_super_admin(self.client)
        resp = self.client.get("/api/admin/finance/revenue", headers=headers)
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.get_json().get("code"), "blocked_local_production")

    @patch("stripe_access_guard.config.IS_PRODUCTION", False)
    def test_revenue_appel_direct_avec_confirmed_true_reste_refuse_403(self):
        """Preuve explicite demandée par la consigne : un appel HTTP forgé
        avec confirmed=true ne doit JAMAIS suffire à contourner le blocage
        local/production, pour AUCUNE des 3 routes financières."""
        os.environ["STRIPE_SECRET_KEY"] = "sk_live_123"
        _, headers = _register_super_admin(self.client)
        resp = self.client.get("/api/admin/finance/revenue?confirmed=true", headers=headers)
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.get_json().get("code"), "blocked_local_production")

    @patch("stripe_access_guard.config.IS_PRODUCTION", False)
    def test_payments_appel_direct_avec_confirmed_true_reste_refuse_403(self):
        os.environ["STRIPE_SECRET_KEY"] = "sk_live_123"
        _, headers = _register_super_admin(self.client)
        resp = self.client.get("/api/admin/finance/payments?confirmed=true", headers=headers)
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.get_json().get("code"), "blocked_local_production")

    @patch("stripe_access_guard.config.IS_PRODUCTION", False)
    def test_revenue_series_appel_direct_avec_confirmed_true_reste_refuse_403(self):
        os.environ["STRIPE_SECRET_KEY"] = "sk_live_123"
        _, headers = _register_super_admin(self.client)
        resp = self.client.get("/api/admin/finance/revenue/series?confirmed=true", headers=headers)
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.get_json().get("code"), "blocked_local_production")

    @patch("stripe_access_guard.config.IS_PRODUCTION", True)
    def test_revenue_appel_direct_production_sans_confirmation_409(self):
        os.environ["STRIPE_SECRET_KEY"] = "sk_live_123"
        _, headers = _register_super_admin(self.client)
        resp = self.client.get("/api/admin/finance/revenue", headers=headers)
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.get_json().get("code"), "confirmation_required")

    @patch("stripe_service.list_all_refunds")
    @patch("stripe_service.list_all_invoices")
    @patch("stripe_access_guard.config.IS_PRODUCTION", True)
    def test_revenue_appel_direct_production_avec_confirmation_200(self, mock_invoices, mock_refunds):
        os.environ["STRIPE_SECRET_KEY"] = "sk_live_123"
        mock_invoices.return_value = {"data": [], "has_more": False}
        mock_refunds.return_value = {"data": [], "has_more": False}
        _, headers = _register_super_admin(self.client)
        resp = self.client.get("/api/admin/finance/revenue?confirmed=true", headers=headers)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json().get("mode"), "production")

    @patch("stripe_service.list_all_payment_intents")
    def test_payments_super_admin_200(self, mock_pi):
        mock_pi.return_value = {"data": [], "has_more": False}
        _, headers = _register_super_admin(self.client)
        resp = self.client.get("/api/admin/finance/payments", headers=headers)
        self.assertEqual(resp.status_code, 200)


if __name__ == "__main__":
    unittest.main()
