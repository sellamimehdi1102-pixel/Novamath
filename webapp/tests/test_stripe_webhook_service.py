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
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import stripe

import config
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

    @patch("stripe_webhook_service.stripe_service.get_subscription")
    def test_format_basil_sans_champ_subscription_racine(self, mock_get_subscription):
        """Depuis l'API Stripe "Basil" (2025-03-31, vérifié par un appel réel),
        invoice.subscription est toujours absent/None : l'ID vit sous
        invoice.parent.subscription_details.subscription — jamais un objet
        inventé, ce format a été observé sur une vraie Invoice Stripe."""
        mock_get_subscription.return_value = {
            "id": "sub_123", "status": "active",
            "items": {"data": [{"price": {"id": "price_ultra_xyz"}}]},
        }
        event = _make_event(
            "evt_basil", "invoice.paid",
            {
                "customer": "cus_123",
                "subscription": None,
                "parent": {"subscription_details": {"subscription": "sub_123"}},
            },
        )
        result = stripe_webhook_service.handle_event(event)
        self.assertEqual(result["status"], "processed")
        self.assertEqual(self._user()["plan"], "ultra")


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

    # ── Chantier "Robustesse Stripe" (2026-08-27) — voir l'audit : sync_
    # subscription() rétrogradait à tort vers Free dès qu'un webhook
    # customer.subscription.updated arrivait avec status="past_due", ce qui
    # contredisait _handle_invoice_payment_failed (qui conserve toujours le
    # plan pour ce même scénario). Les tests ci-dessous couvrent explicitement
    # chaque statut concerné, en vérifiant le comportement métier FINAL de
    # users.plan (pas seulement qu'une fonction a été appelée).
    def test_status_active_synchronise_normalement_le_plan(self):
        db.set_stripe_subscription(self.user_id, "sub_123", "free", "canceled")
        obj = {
            "id": "sub_123", "customer": "cus_123", "status": "active",
            "items": {"data": [{"price": {"id": "price_premium_abc"}}]},
        }
        event = _make_event("evt_status_active", "customer.subscription.updated", obj)
        result = stripe_webhook_service.handle_event(event)
        self.assertEqual(result["status"], "processed")
        user = self._user()
        self.assertEqual(user["plan"], "premium")
        self.assertEqual(user["stripe_subscription_status"], "active")

    def test_status_trialing_synchronise_normalement_le_plan(self):
        db.set_stripe_subscription(self.user_id, "sub_123", "free", "canceled")
        obj = {
            "id": "sub_123", "customer": "cus_123", "status": "trialing",
            "items": {"data": [{"price": {"id": "price_ultra_xyz"}}]},
        }
        event = _make_event("evt_status_trialing", "customer.subscription.updated", obj)
        result = stripe_webhook_service.handle_event(event)
        self.assertEqual(result["status"], "processed")
        user = self._user()
        self.assertEqual(user["plan"], "ultra")
        self.assertEqual(user["stripe_subscription_status"], "trialing")

    def test_status_past_due_conserve_le_plan_premium_existant(self):
        db.set_stripe_subscription(self.user_id, "sub_123", "premium", "active")
        obj = {
            # price_id pointe volontairement vers Ultra : si le plan était
            # (à tort) recalculé depuis price_id pour ce statut, ce test
            # échouerait en observant "ultra" au lieu de "premium" conservé.
            "id": "sub_123", "customer": "cus_123", "status": "past_due",
            "items": {"data": [{"price": {"id": "price_ultra_xyz"}}]},
        }
        event = _make_event("evt_status_past_due", "customer.subscription.updated", obj)
        result = stripe_webhook_service.handle_event(event)
        self.assertEqual(result["status"], "processed")
        user = self._user()
        self.assertEqual(user["plan"], "premium", "le plan payant doit être conservé pendant la relance (past_due)")
        self.assertEqual(user["stripe_subscription_status"], "past_due")

    def test_status_past_due_conserve_le_plan_ultra_existant(self):
        db.set_stripe_subscription(self.user_id, "sub_123", "ultra", "active")
        obj = {
            "id": "sub_123", "customer": "cus_123", "status": "past_due",
            "items": {"data": [{"price": {"id": "price_ultra_xyz"}}]},
        }
        event = _make_event("evt_status_past_due_ultra", "customer.subscription.updated", obj)
        stripe_webhook_service.handle_event(event)
        self.assertEqual(self._user()["plan"], "ultra")

    def test_status_unpaid_retrograde_vers_free(self):
        # Comportement voulu par l'architecture actuelle (documenté dans
        # _GRACE_STATUSES, stripe_webhook_service.py) : "unpaid" signifie que
        # les relances Stripe sont épuisées, contrairement à "past_due" —
        # traité comme les autres statuts non actifs (downgrade), jamais
        # inclus dans la fenêtre de grâce.
        db.set_stripe_subscription(self.user_id, "sub_123", "premium", "active")
        obj = {
            "id": "sub_123", "customer": "cus_123", "status": "unpaid",
            "items": {"data": [{"price": {"id": "price_premium_abc"}}]},
        }
        event = _make_event("evt_status_unpaid", "customer.subscription.updated", obj)
        result = stripe_webhook_service.handle_event(event)
        self.assertEqual(result["status"], "processed")
        user = self._user()
        self.assertEqual(user["plan"], "free")
        self.assertEqual(user["stripe_subscription_status"], "unpaid")


class TestInvoicePaidApresPaymentFailed(StripeWebhookTestCase):
    """Scénario complet : échec de paiement (plan conservé, status past_due)
    PUIS paiement recouvré (invoice.paid) — l'abonnement doit resynchroniser
    correctement le plan, sans dépendre d'un état intermédiaire particulier."""

    @patch("stripe_webhook_service.stripe_service.get_subscription")
    def test_invoice_paid_resynchronise_apres_un_echec_precedent(self, mock_get_subscription):
        db.set_stripe_subscription(self.user_id, "sub_123", "premium", "active")
        failed_event = _make_event(
            "evt_failed", "invoice.payment_failed", {"customer": "cus_123", "id": "in_123"},
        )
        stripe_webhook_service.handle_event(failed_event)
        self.assertEqual(self._user()["plan"], "premium")
        self.assertEqual(self._user()["stripe_subscription_status"], "past_due")

        mock_get_subscription.return_value = {
            "id": "sub_123", "status": "active",
            "items": {"data": [{"price": {"id": "price_premium_abc"}}]},
        }
        paid_event = _make_event(
            "evt_paid_after_failed", "invoice.paid", {"customer": "cus_123", "subscription": "sub_123"},
        )
        result = stripe_webhook_service.handle_event(paid_event)
        self.assertEqual(result["status"], "processed")
        user = self._user()
        self.assertEqual(user["plan"], "premium")
        self.assertEqual(user["stripe_subscription_status"], "active")


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

    def test_evenement_dun_ancien_abonnement_necrase_pas_le_nouveau(self):
        """Cœur du correctif Release Candidate : l'utilisateur a annulé sub_ancien
        puis s'est immédiatement ré-abonné (sub_nouveau, déjà actif en base).
        Le webhook "deleted" de sub_ancien, livré en retard/hors-ordre, ne doit
        JAMAIS écraser l'abonnement actif de l'utilisateur."""
        db.set_stripe_subscription(self.user_id, "sub_nouveau", "ultra", "active")
        event = _make_event(
            "evt_stale", "customer.subscription.deleted",
            {"id": "sub_ancien", "customer": "cus_123"},
        )
        result = stripe_webhook_service.handle_event(event)
        self.assertEqual(result["status"], "processed")
        user = self._user()
        self.assertEqual(user["plan"], "ultra")
        self.assertEqual(user["stripe_subscription_id"], "sub_nouveau")
        self.assertEqual(user["stripe_subscription_status"], "active")

    def test_evenement_de_labonnement_courant_annule_normalement(self):
        """Cas nominal (pas de ré-abonnement) : l'ID reçu correspond à l'ID
        actuellement enregistré, l'annulation doit s'appliquer normalement."""
        db.set_stripe_subscription(self.user_id, "sub_courant", "premium", "active")
        event = _make_event(
            "evt_current", "customer.subscription.deleted",
            {"id": "sub_courant", "customer": "cus_123"},
        )
        result = stripe_webhook_service.handle_event(event)
        self.assertEqual(result["status"], "processed")
        user = self._user()
        self.assertEqual(user["plan"], "free")
        self.assertIsNone(user["stripe_subscription_id"])
        self.assertEqual(user["stripe_subscription_status"], "canceled")

    def test_retries_stripe_du_meme_evenement_hors_ordre_restent_sans_effet(self):
        """Un retry réseau Stripe qui redélivre le MÊME event_id (déjà marqué
        traité par idempotence) reste ignoré — même dans le cas hors-ordre."""
        db.set_stripe_subscription(self.user_id, "sub_nouveau", "ultra", "active")
        event = _make_event(
            "evt_stale_retry", "customer.subscription.deleted",
            {"id": "sub_ancien", "customer": "cus_123"},
        )
        first = stripe_webhook_service.handle_event(event)
        second = stripe_webhook_service.handle_event(event)

        self.assertEqual(first["status"], "processed")
        self.assertEqual(second["status"], "duplicate_ignored")
        user = self._user()
        self.assertEqual(user["plan"], "ultra")
        self.assertEqual(user["stripe_subscription_id"], "sub_nouveau")

    def test_double_livraison_avec_event_id_different_mais_meme_ancien_abonnement(self):
        """Double livraison "logique" (deux event_id Stripe distincts mais
        portant sur le même ancien abonnement obsolète, ex: événement original
        + redélivraison manuelle depuis le Dashboard avec un nouvel event_id) :
        aucun des deux ne doit écraser l'abonnement actif."""
        db.set_stripe_subscription(self.user_id, "sub_nouveau", "ultra", "active")
        event_a = _make_event(
            "evt_dup_a", "customer.subscription.deleted",
            {"id": "sub_ancien", "customer": "cus_123"},
        )
        event_b = _make_event(
            "evt_dup_b", "customer.subscription.deleted",
            {"id": "sub_ancien", "customer": "cus_123"},
        )
        result_a = stripe_webhook_service.handle_event(event_a)
        result_b = stripe_webhook_service.handle_event(event_b)

        self.assertEqual(result_a["status"], "processed")
        self.assertEqual(result_b["status"], "processed")
        user = self._user()
        self.assertEqual(user["plan"], "ultra")
        self.assertEqual(user["stripe_subscription_id"], "sub_nouveau")

    def test_sans_abonnement_actif_en_base_applique_lannulation(self):
        """Si l'utilisateur n'a aucun abonnement en base (déjà free), le
        webhook "deleted" reste appliqué sans erreur (idempotent) — pas de
        régression sur le comportement existant pour un compte déjà free."""
        event = _make_event(
            "evt_already_free", "customer.subscription.deleted",
            {"id": "sub_quelconque", "customer": "cus_123"},
        )
        result = stripe_webhook_service.handle_event(event)
        self.assertEqual(result["status"], "processed")
        user = self._user()
        self.assertEqual(user["plan"], "free")
        self.assertIsNone(user["stripe_subscription_id"])


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


class TestErreurHandlerLibereLaReservation(StripeWebhookTestCase):
    """Si le handler échoue (ex: appel Stripe indisponible pendant
    get_subscription), l'event_id ne doit jamais rester marqué "traité" :
    Stripe redélivrera cet événement plus tard et il doit être retraité pour
    de vrai, pas ignoré comme un doublon fantôme."""

    @patch("stripe_webhook_service.stripe_service.get_subscription")
    def test_exception_retire_la_reservation(self, mock_get_subscription):
        mock_get_subscription.side_effect = stripe.error.StripeError("indisponible")
        event = _make_event(
            "evt_fail", "checkout.session.completed",
            {"customer": "cus_123", "subscription": "sub_123"},
        )

        with self.assertRaises(stripe.error.StripeError):
            stripe_webhook_service.handle_event(event)

        self.assertFalse(db.has_processed_stripe_event("evt_fail"))

    @patch("stripe_webhook_service.stripe_service.get_subscription")
    def test_redelivrance_apres_echec_traite_reellement_levenement(self, mock_get_subscription):
        mock_get_subscription.side_effect = [
            stripe.error.StripeError("indisponible"),
            {
                "id": "sub_123", "status": "active",
                "items": {"data": [{"price": {"id": "price_premium_abc"}}]},
            },
        ]
        event = _make_event(
            "evt_retry", "checkout.session.completed",
            {"customer": "cus_123", "subscription": "sub_123"},
        )

        with self.assertRaises(stripe.error.StripeError):
            stripe_webhook_service.handle_event(event)

        retry = stripe_webhook_service.handle_event(event)

        self.assertEqual(retry["status"], "processed")
        self.assertEqual(self._user()["plan"], "premium")
        self.assertEqual(mock_get_subscription.call_count, 2)


class TestKillBrutalDuProcess(StripeWebhookTestCase):
    """Release Candidate : contrairement à une exception Python normale (déjà
    couverte par TestErreurHandlerLibereLaReservation, qui libère la
    réservation via le `except`), un SIGKILL/restart Fly.io en plein
    traitement n'exécute NI le `except` NI le mark_stripe_event_completed —
    la réservation reste "en cours" indéfiniment sans ce correctif. On
    simule ce cas en reculant artificiellement processed_at (comme si le
    process était mort il y a longtemps), sans jamais appeler unmark ni
    completed nous-mêmes."""

    @patch("stripe_webhook_service.stripe_service.get_subscription")
    def test_redelivrance_tardive_apres_kill_retraite_reellement_levenement(self, mock_get_subscription):
        mock_get_subscription.return_value = {
            "id": "sub_123", "status": "active",
            "items": {"data": [{"price": {"id": "price_premium_abc"}}]},
        }
        event = _make_event(
            "evt_killed", "checkout.session.completed",
            {"customer": "cus_123", "subscription": "sub_123"},
        )

        # Réserve l'event (comme le début réel de handle_event) puis simule
        # le kill : le process meurt ici, avant tout appel handler/completed.
        db.mark_stripe_event_processed("evt_killed", "checkout.session.completed")
        stale_ts = (
            datetime.now(timezone.utc) - timedelta(seconds=config.STRIPE_WEBHOOK_CLAIM_TIMEOUT_SECONDS + 60)
        ).isoformat()
        conn = db.get_connection()
        try:
            conn.execute(
                "UPDATE stripe_webhook_events SET processed_at = ? WHERE event_id = ?",
                (stale_ts, "evt_killed"),
            )
            conn.commit()
        finally:
            conn.close()

        # Stripe redélivre l'event (retry standard) : doit être RÉELLEMENT
        # retraité, pas ignoré comme un doublon fantôme.
        result = stripe_webhook_service.handle_event(event)

        self.assertEqual(result["status"], "processed")
        self.assertEqual(self._user()["plan"], "premium")
        mock_get_subscription.assert_called_once()

    @patch("stripe_webhook_service.stripe_service.get_subscription")
    def test_redelivrance_rapide_apres_kill_reste_bloquee_dans_la_fenetre_de_grace(self, mock_get_subscription):
        """Sans attente suffisante (process potentiellement encore vivant,
        juste lent), la redélivrance doit rester ignorée — jamais de double
        exécution prématurée du handler."""
        mock_get_subscription.return_value = {
            "id": "sub_123", "status": "active",
            "items": {"data": [{"price": {"id": "price_premium_abc"}}]},
        }
        event = _make_event(
            "evt_slow", "checkout.session.completed",
            {"customer": "cus_123", "subscription": "sub_123"},
        )
        db.mark_stripe_event_processed("evt_slow", "checkout.session.completed")

        result = stripe_webhook_service.handle_event(event)

        self.assertEqual(result["status"], "duplicate_ignored")
        mock_get_subscription.assert_not_called()

    @patch("stripe_webhook_service.stripe_service.get_subscription")
    def test_evenement_reellement_complete_reste_protege_meme_tres_longtemps_apres(self, mock_get_subscription):
        """Garantie d'idempotence historique préservée : un event correctement
        traité de bout en bout ne doit JAMAIS être rejoué, quel que soit le
        temps écoulé — le mécanisme de reprise sur kill ne s'applique qu'aux
        réservations jamais complétées."""
        mock_get_subscription.return_value = {
            "id": "sub_123", "status": "active",
            "items": {"data": [{"price": {"id": "price_premium_abc"}}]},
        }
        event = _make_event(
            "evt_finished", "checkout.session.completed",
            {"customer": "cus_123", "subscription": "sub_123"},
        )
        first = stripe_webhook_service.handle_event(event)
        self.assertEqual(first["status"], "processed")

        very_old_ts = (datetime.now(timezone.utc) - timedelta(days=365)).isoformat()
        conn = db.get_connection()
        try:
            conn.execute(
                "UPDATE stripe_webhook_events SET processed_at = ? WHERE event_id = ?",
                (very_old_ts, "evt_finished"),
            )
            conn.commit()
        finally:
            conn.close()

        second = stripe_webhook_service.handle_event(event)
        self.assertEqual(second["status"], "duplicate_ignored")
        mock_get_subscription.assert_called_once()

    def test_evenement_ignore_type_inconnu_est_aussi_marque_complete(self):
        """Un event dont le type n'est géré par aucun handler est marqué
        complété (pas seulement réservé) : une redélivrance tardive de ce
        même event, même après expiration du délai, ne doit jamais déclencher
        de nouveau traitement (il n'y a rien à re-traiter)."""
        event = _make_event("evt_unhandled", "payment_intent.succeeded", {"customer": "cus_123"})
        first = stripe_webhook_service.handle_event(event)
        self.assertEqual(first["status"], "ignored")

        stale_ts = (
            datetime.now(timezone.utc) - timedelta(seconds=config.STRIPE_WEBHOOK_CLAIM_TIMEOUT_SECONDS + 60)
        ).isoformat()
        conn = db.get_connection()
        try:
            conn.execute(
                "UPDATE stripe_webhook_events SET processed_at = ? WHERE event_id = ?",
                (stale_ts, "evt_unhandled"),
            )
            conn.commit()
        finally:
            conn.close()

        second = stripe_webhook_service.handle_event(event)
        self.assertEqual(second["status"], "duplicate_ignored")


class TestEvenementNonGere(StripeWebhookTestCase):
    def test_type_inconnu_est_ignore_et_marque_traite(self):
        event = _make_event("evt_11", "payment_intent.succeeded", {"customer": "cus_123"})
        result = stripe_webhook_service.handle_event(event)
        self.assertEqual(result["status"], "ignored")
        self.assertTrue(db.has_processed_stripe_event("evt_11"))


class TestInvoicePaymentSucceeded(StripeWebhookTestCase):
    """invoice.payment_succeeded doit resynchroniser le plan exactement comme
    invoice.paid (Stripe envoie l'un ou l'autre selon la configuration du
    compte, jamais les deux traitements ne doivent diverger)."""

    @patch("stripe_webhook_service.stripe_service.get_subscription")
    def test_resynchronise_le_plan_comme_invoice_paid(self, mock_get_subscription):
        mock_get_subscription.return_value = {
            "id": "sub_123", "status": "active",
            "items": {"data": [{"price": {"id": "price_premium_abc"}}]},
        }
        event = _make_event(
            "evt_12", "invoice.payment_succeeded", {"customer": "cus_123", "subscription": "sub_123"},
        )
        result = stripe_webhook_service.handle_event(event)
        self.assertEqual(result["status"], "processed")
        self.assertEqual(self._user()["plan"], "premium")


class TestEvenementsJournalisesUniquement(StripeWebhookTestCase):
    """invoice.finalized, invoice.upcoming, trial_will_end,
    checkout.session.expired, payment_method.{attached,updated,detached} :
    aucun ne touche plan/stripe_subscription_id/status, seulement le journal
    de sécurité (voir db.log_security_event)."""

    def _assert_processed_sans_toucher_au_plan(self, event, plan_avant):
        db.set_stripe_subscription(self.user_id, "sub_123", plan_avant, "active")
        result = stripe_webhook_service.handle_event(event)
        self.assertEqual(result["status"], "processed")
        user = self._user()
        self.assertEqual(user["plan"], plan_avant)
        self.assertEqual(user["stripe_subscription_id"], "sub_123")

    def test_invoice_finalized(self):
        event = _make_event("evt_13", "invoice.finalized", {"customer": "cus_123", "id": "in_1"})
        self._assert_processed_sans_toucher_au_plan(event, "premium")

    def test_invoice_upcoming(self):
        event = _make_event("evt_14", "invoice.upcoming", {"customer": "cus_123"})
        self._assert_processed_sans_toucher_au_plan(event, "premium")

    def test_trial_will_end(self):
        event = _make_event(
            "evt_15", "customer.subscription.trial_will_end", {"customer": "cus_123", "id": "sub_123"},
        )
        self._assert_processed_sans_toucher_au_plan(event, "ultra")

    def test_checkout_session_expired(self):
        event = _make_event("evt_16", "checkout.session.expired", {"customer": "cus_123"})
        self._assert_processed_sans_toucher_au_plan(event, "ultra")

    def test_payment_method_attached(self):
        event = _make_event("evt_17", "payment_method.attached", {"customer": "cus_123", "id": "pm_1"})
        self._assert_processed_sans_toucher_au_plan(event, "premium")

    def test_payment_method_updated(self):
        event = _make_event("evt_18", "payment_method.updated", {"customer": "cus_123", "id": "pm_1"})
        self._assert_processed_sans_toucher_au_plan(event, "premium")

    def test_payment_method_detached_sans_customer(self):
        # payment_method.detached n'a plus de customer : ne doit jamais planter.
        event = _make_event("evt_19", "payment_method.detached", {"id": "pm_1"})
        result = stripe_webhook_service.handle_event(event)
        self.assertEqual(result["status"], "processed")

    def test_evenements_customer_inconnu_ne_plantent_pas(self):
        for event_type in (
            "invoice.finalized", "invoice.upcoming", "customer.subscription.trial_will_end",
            "checkout.session.expired", "payment_method.attached", "payment_method.updated",
        ):
            with self.subTest(event_type=event_type):
                event = _make_event(f"evt_unk_{event_type}", event_type, {"customer": "cus_inconnu"})
                result = stripe_webhook_service.handle_event(event)
                self.assertEqual(result["status"], "processed")


if __name__ == "__main__":
    unittest.main()
