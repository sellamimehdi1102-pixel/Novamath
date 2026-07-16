"""
Suite du service de traitement des webhooks Stripe
(webapp/stripe_webhook_service.py) : couvre les 6 événements gérés
(checkout.session.completed, invoice.paid, invoice.payment_failed,
customer.subscription.{created,updated,deleted}), l'idempotence, et les cas
limites (événement inconnu, customer sans utilisateur NovaMath).

Base SQLite isolée dans un répertoire temporaire (db.DATA_DIR/db.DB_PATH
monkeypatchés) : aucune interférence avec data/novamath.db. Les appels au SDK
Stripe (récupération d'abonnement) sont mockés — aucun appel réseau réel.
"""
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import db
import stripe_webhook_service


def _make_event(event_id, event_type, obj):
    return {"id": event_id, "type": event_type, "data": {"object": obj}}


class StripeWebhookTestCase(unittest.TestCase):
    def setUp(self):
        self._env_backup = dict(os.environ)
        os.environ["STRIPE_PRICE_PREMIUM"] = "price_premium_abc"
        os.environ["STRIPE_PRICE_ULTRA"] = "price_ultra_xyz"

        self._tmp_dir = tempfile.mkdtemp()
        self._data_dir_backup = db.DATA_DIR
        self._db_path_backup = db.DB_PATH
        db.DATA_DIR = Path(self._tmp_dir)
        db.DB_PATH = db.DATA_DIR / "novamath.db"
        db.init_db()

        user_id = db.create_user("eleve@gmail.com", "eleve_test", "Élève", "hash")
        db.set_stripe_customer_id(user_id, "cus_123")
        self.user_id = user_id

    def tearDown(self):
        db.DATA_DIR = self._data_dir_backup
        db.DB_PATH = self._db_path_backup
        shutil.rmtree(self._tmp_dir, ignore_errors=True)
        os.environ.clear()
        os.environ.update(self._env_backup)

    def _user(self):
        return db.get_user_by_id(self.user_id)


class TestCheckoutSessionCompleted(StripeWebhookTestCase):
    @patch("stripe_webhook_service.stripe_service.get_subscription")
    def test_active_subscription_met_a_jour_le_plan(self, mock_get_subscription):
        mock_get_subscription.return_value = {
            "id": "sub_123", "status": "active",
            "items": {"data": [{"price": {"id": "price_premium_abc"}}]},
        }
        event = _make_event(
            "evt_1", "checkout.session.completed",
            {"customer": "cus_123", "subscription": "sub_123"},
        )
        result = stripe_webhook_service.handle_event(event)

        self.assertEqual(result["status"], "processed")
        user = self._user()
        self.assertEqual(user["plan"], "premium")
        self.assertEqual(user["stripe_subscription_id"], "sub_123")
        self.assertEqual(user["stripe_subscription_status"], "active")

    def test_sans_subscription_id_ne_plante_pas(self):
        event = _make_event("evt_2", "checkout.session.completed", {"customer": "cus_123"})
        result = stripe_webhook_service.handle_event(event)
        self.assertEqual(result["status"], "processed")
        self.assertEqual(self._user()["plan"], "free")

    def test_customer_inconnu_ne_plante_pas(self):
        event = _make_event(
            "evt_3", "checkout.session.completed",
            {"customer": "cus_inconnu", "subscription": "sub_999"},
        )
        result = stripe_webhook_service.handle_event(event)
        self.assertEqual(result["status"], "processed")


class TestInvoicePaid(StripeWebhookTestCase):
    @patch("stripe_webhook_service.stripe_service.get_subscription")
    def test_renouvellement_resynchronise_le_plan(self, mock_get_subscription):
        mock_get_subscription.return_value = {
            "id": "sub_123", "status": "active",
            "items": {"data": [{"price": {"id": "price_ultra_xyz"}}]},
        }
        event = _make_event(
            "evt_4", "invoice.paid", {"customer": "cus_123", "subscription": "sub_123"},
        )
        result = stripe_webhook_service.handle_event(event)
        self.assertEqual(result["status"], "processed")
        self.assertEqual(self._user()["plan"], "ultra")

    def test_invoice_sans_abonnement_associe(self):
        event = _make_event("evt_5", "invoice.paid", {"customer": "cus_123"})
        result = stripe_webhook_service.handle_event(event)
        self.assertEqual(result["status"], "processed")
        self.assertEqual(self._user()["plan"], "free")


class TestInvoicePaymentFailed(StripeWebhookTestCase):
    def test_marque_past_due_sans_toucher_au_plan(self):
        db.set_stripe_subscription(self.user_id, "sub_123", "premium", "active")
        event = _make_event(
            "evt_6", "invoice.payment_failed", {"customer": "cus_123", "id": "in_123"},
        )
        result = stripe_webhook_service.handle_event(event)
        self.assertEqual(result["status"], "processed")
        user = self._user()
        self.assertEqual(user["plan"], "premium")
        self.assertEqual(user["stripe_subscription_id"], "sub_123")
        self.assertEqual(user["stripe_subscription_status"], "past_due")


class TestSubscriptionCreated(StripeWebhookTestCase):
    def test_synchronise_directement_depuis_lobjet(self):
        obj = {
            "id": "sub_123", "customer": "cus_123", "status": "trialing",
            "items": {"data": [{"price": {"id": "price_premium_abc"}}]},
        }
        event = _make_event("evt_7", "customer.subscription.created", obj)
        result = stripe_webhook_service.handle_event(event)
        self.assertEqual(result["status"], "processed")
        user = self._user()
        self.assertEqual(user["plan"], "premium")
        self.assertEqual(user["stripe_subscription_status"], "trialing")


class TestSubscriptionUpdated(StripeWebhookTestCase):
    def test_passage_actif_vers_annule(self):
        db.set_stripe_subscription(self.user_id, "sub_123", "ultra", "active")
        obj = {
            "id": "sub_123", "customer": "cus_123", "status": "canceled",
            "items": {"data": [{"price": {"id": "price_ultra_xyz"}}]},
        }
        event = _make_event("evt_8", "customer.subscription.updated", obj)
        result = stripe_webhook_service.handle_event(event)
        self.assertEqual(result["status"], "processed")
        self.assertEqual(self._user()["plan"], "free")

    def test_changement_de_plan(self):
        db.set_stripe_subscription(self.user_id, "sub_123", "premium", "active")
        obj = {
            "id": "sub_123", "customer": "cus_123", "status": "active",
            "items": {"data": [{"price": {"id": "price_ultra_xyz"}}]},
        }
        event = _make_event("evt_9", "customer.subscription.updated", obj)
        stripe_webhook_service.handle_event(event)
        self.assertEqual(self._user()["plan"], "ultra")


class TestSubscriptionDeleted(StripeWebhookTestCase):
    def test_retour_au_plan_free(self):
        db.set_stripe_subscription(self.user_id, "sub_123", "ultra", "active")
        event = _make_event(
            "evt_10", "customer.subscription.deleted", {"id": "sub_123", "customer": "cus_123"},
        )
        result = stripe_webhook_service.handle_event(event)
        self.assertEqual(result["status"], "processed")
        user = self._user()
        self.assertEqual(user["plan"], "free")
        self.assertIsNone(user["stripe_subscription_id"])
        self.assertEqual(user["stripe_subscription_status"], "canceled")


class TestIdempotence(StripeWebhookTestCase):
    @patch("stripe_webhook_service.stripe_service.get_subscription")
    def test_meme_event_id_traite_une_seule_fois(self, mock_get_subscription):
        mock_get_subscription.return_value = {
            "id": "sub_123", "status": "active",
            "items": {"data": [{"price": {"id": "price_premium_abc"}}]},
        }
        event = _make_event(
            "evt_dup", "checkout.session.completed",
            {"customer": "cus_123", "subscription": "sub_123"},
        )
        first = stripe_webhook_service.handle_event(event)
        second = stripe_webhook_service.handle_event(event)

        self.assertEqual(first["status"], "processed")
        self.assertEqual(second["status"], "duplicate_ignored")
        mock_get_subscription.assert_called_once()


class TestEvenementNonGere(StripeWebhookTestCase):
    def test_type_inconnu_est_ignore_et_marque_traite(self):
        event = _make_event("evt_11", "payment_intent.succeeded", {"customer": "cus_123"})
        result = stripe_webhook_service.handle_event(event)
        self.assertEqual(result["status"], "ignored")
        self.assertTrue(db.has_processed_stripe_event("evt_11"))


if __name__ == "__main__":
    unittest.main()
