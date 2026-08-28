"""Chantier Administrateur (P1) : carte "Erreurs serveur" du Dashboard —
réutilise metrics_service.in_memory_snapshot() (déjà incrémenté à chaque
requête HTTP par logging_service.init_app()), aucune nouvelle collecte,
jamais une valeur fabriquée.

Chantier Administrateur "Tri des informations" (Phase 2) : comparaison
"hier" de la carte Utilisateurs actifs + les deux nouvelles alertes
ponctuelles (paiements en échec / consentements parentaux en attente)."""
import random
import unittest
from unittest.mock import patch

import admin_dashboard_service
import db
import metrics_service
import server
from role_service import Role


def _register_admin(client):
    email = f"tdash{random.randint(1_000_000, 9_999_999)}@gmail.com"
    username = f"tdash{random.randint(100_000, 999_999)}"
    resp = client.post("/api/auth/register", json={
        "email": email, "username": username, "pseudo": "Test",
        "birth_date": "2000-01-01",
        "password": "MotDePasse123!", "confirm_password": "MotDePasse123!",
        "accept_terms": True, "accept_privacy": True,
    })
    user = resp.get_json()["user"]
    db.set_user_role(user["id"], Role.SUPPORT.value)
    csrf = client.get_cookie("nm_csrf").value
    return user, {"X-CSRF-Token": csrf}


class TestCarteErreursServeurDashboard(unittest.TestCase):
    def setUp(self):
        self.client = server.app.test_client()
        self.addCleanup(metrics_service.reset)

    def test_server_errors_toujours_disponible_jamais_dexception(self):
        snapshot = admin_dashboard_service.get_dashboard_snapshot()
        self.assertIn("server_errors", snapshot["cards"])
        card = snapshot["cards"]["server_errors"]
        self.assertTrue(card["available"])
        self.assertIn("total_requests", card["value"])
        self.assertIn("total_errors", card["value"])

    def test_reflete_reellement_les_compteurs_en_memoire_jamais_fabrique(self):
        metrics_service.reset()
        metrics_service.record_request(12.5)
        metrics_service.record_request(8.0)
        metrics_service.record_error()

        card = admin_dashboard_service.get_dashboard_snapshot()["cards"]["server_errors"]
        self.assertEqual(card["value"]["total_requests"], 2)
        self.assertEqual(card["value"]["total_errors"], 1)

    def test_endpoint_http_expose_la_carte(self):
        _, headers = _register_admin(self.client)
        resp = self.client.get("/api/admin/dashboard", headers=headers)
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))
        body = resp.get_json()
        self.assertIn("server_errors", body["cards"])
        self.assertTrue(body["cards"]["server_errors"]["available"])


class TestCarteUtilisateursActifsComparaisonHier(unittest.TestCase):
    """Isolée de la DB partagée (voir patch de db.count_users_active_since) :
    la suite pytest entière partage une seule base SQLite, un compte réel
    "actif aujourd'hui" créé par un autre test en parallèle fausserait des
    assertions sur des valeurs absolues."""

    def test_delta_positif(self):
        with patch("admin_dashboard_service.db.count_users_active_since", side_effect=[12, 5]):
            card = admin_dashboard_service._card_active_users_today()
        self.assertTrue(card["available"])
        self.assertEqual(card["value"], {"today": 12, "yesterday": 5, "delta": 7})

    def test_delta_negatif(self):
        with patch("admin_dashboard_service.db.count_users_active_since", side_effect=[3, 11]):
            card = admin_dashboard_service._card_active_users_today()
        self.assertEqual(card["value"], {"today": 3, "yesterday": 11, "delta": -8})

    def test_aucun_actif_hier_reste_calculable(self):
        with patch("admin_dashboard_service.db.count_users_active_since", side_effect=[6, 0]):
            card = admin_dashboard_service._card_active_users_today()
        self.assertTrue(card["available"])
        self.assertEqual(card["value"], {"today": 6, "yesterday": 0, "delta": 6})

    def test_appelle_count_users_active_since_avec_les_bonnes_fenetres(self):
        with patch("admin_dashboard_service.db.count_users_active_since", side_effect=[1, 1]) as mocked:
            admin_dashboard_service._card_active_users_today()
        self.assertEqual(mocked.call_count, 2)
        today_call, yesterday_call = mocked.call_args_list
        # "aujourd'hui" : une seule borne (depuis minuit, comme avant ce chantier).
        self.assertEqual(len(today_call.args), 1)
        # "hier" : bornée des deux côtés, et la borne haute est exactement la
        # borne basse d'aujourd'hui (aucun chevauchement, aucun trou entre les
        # deux fenêtres).
        self.assertEqual(len(yesterday_call.args), 2)
        self.assertEqual(yesterday_call.args[1], today_call.args[0])

    def test_endpoint_http_expose_le_delta(self):
        client = server.app.test_client()
        _, headers = _register_admin(client)
        resp = client.get("/api/admin/dashboard", headers=headers)
        self.assertEqual(resp.status_code, 200)
        card = resp.get_json()["cards"]["active_users_today"]
        self.assertTrue(card["available"])
        for key in ("today", "yesterday", "delta"):
            self.assertIn(key, card["value"])
        self.assertEqual(card["value"]["delta"], card["value"]["today"] - card["value"]["yesterday"])


class TestAlertesPonctuelles(unittest.TestCase):
    """`_alerts()` isolé des 5 alertes de tendance existantes (mockées à une
    liste vide) — seules les 2 nouvelles règles ponctuelles sont sous test
    ici, sans dépendre de données business réelles pouvant déclencher les
    autres alertes en parallèle."""

    def _alerts_with(self, failed_payments, pending_consent):
        with patch("admin_dashboard_service.admin_analytics_service.list_alerts", return_value=({"alerts": []}, None)), \
             patch("admin_dashboard_service.db.count_users_with_failed_payment", return_value=failed_payments), \
             patch("admin_dashboard_service.db.count_users_pending_parental_consent", return_value=pending_consent):
            return admin_dashboard_service._alerts()

    def test_aucune_alerte_si_les_deux_compteurs_sont_a_zero(self):
        alerts = self._alerts_with(0, 0)
        self.assertTrue(alerts["available"])
        self.assertEqual(alerts["value"], [])

    def test_alerte_paiements_en_echec_si_positif(self):
        alerts = self._alerts_with(3, 0)
        self.assertEqual(len(alerts["value"]), 1)
        alert = alerts["value"][0]
        self.assertEqual(alert["level"], "warning")
        self.assertEqual(alert["code"], "paiements_en_echec")
        self.assertIn("3", alert["message"])
        self.assertEqual(alert["link"], {"path": "/admin/subscriptions", "label": "Voir les abonnements"})

    def test_alerte_consentement_parental_si_positif(self):
        alerts = self._alerts_with(0, 4)
        self.assertEqual(len(alerts["value"]), 1)
        alert = alerts["value"][0]
        self.assertEqual(alert["level"], "warning")
        self.assertEqual(alert["code"], "consentement_parental_attente")
        self.assertIn("4", alert["message"])
        self.assertEqual(alert["link"], {"path": "/admin/users", "label": "Voir les utilisateurs"})

    def test_les_deux_alertes_peuvent_coexister(self):
        alerts = self._alerts_with(2, 1)
        codes = {a["code"] for a in alerts["value"]}
        self.assertEqual(codes, {"paiements_en_echec", "consentement_parental_attente"})

    def test_alertes_de_tendance_existantes_toujours_incluses(self):
        existing = {"level": "critical", "code": "hausse_erreurs", "message": "test"}
        with patch("admin_dashboard_service.admin_analytics_service.list_alerts", return_value=({"alerts": [existing]}, None)), \
             patch("admin_dashboard_service.db.count_users_with_failed_payment", return_value=0), \
             patch("admin_dashboard_service.db.count_users_pending_parental_consent", return_value=0):
            alerts = admin_dashboard_service._alerts()
        self.assertEqual(alerts["value"], [existing])


class TestAgregatsDbPaiementsEtConsentement(unittest.TestCase):
    """Valide directement les deux fonctions ajoutées à db.py — en
    particulier qu'elles ne comptent PAS les mêmes utilisateurs qu'une
    réutilisation naïve de admin_users_service.count_users_admin() (voir la
    contradiction signalée avant implémentation : "suspended" y regroupe
    TOUTE valeur différente de 'active', 'parental_consent_refused' inclus).
    Delta avant/après (jamais une valeur absolue) : la base est partagée par
    toute la suite pytest."""

    def setUp(self):
        self.client = server.app.test_client()

    def test_ne_compte_que_past_due_et_unpaid(self):
        before = db.count_users_with_failed_payment()
        active, _ = _register_admin(self.client)
        past_due, _ = _register_admin(self.client)
        unpaid, _ = _register_admin(self.client)
        canceled, _ = _register_admin(self.client)
        db.set_stripe_subscription_status(active["id"], "active")
        db.set_stripe_subscription_status(past_due["id"], "past_due")
        db.set_stripe_subscription_status(unpaid["id"], "unpaid")
        db.set_stripe_subscription_status(canceled["id"], "canceled")
        after = db.count_users_with_failed_payment()
        self.assertEqual(after - before, 2)

    def test_ne_compte_pas_parental_consent_refused_ni_active(self):
        before = db.count_users_pending_parental_consent()
        pending, _ = _register_admin(self.client)
        refused, _ = _register_admin(self.client)
        active, _ = _register_admin(self.client)
        db.set_account_status(pending["id"], "pending_parental_consent")
        db.set_account_status(refused["id"], "parental_consent_refused")
        db.set_account_status(active["id"], "active")
        after = db.count_users_pending_parental_consent()
        self.assertEqual(after - before, 1)


if __name__ == "__main__":
    unittest.main()
