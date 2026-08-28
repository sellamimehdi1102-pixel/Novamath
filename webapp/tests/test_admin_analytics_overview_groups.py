"""Chantier Administrateur (P2) : admin_analytics_service.overview() ne
calcule plus systématiquement les 5 groupes de KPI (users/chatbot/ai/support/
subscriptions) — seulement ceux réellement demandés via `groups`, puisque ces
KPI n'alimentent plus que le tableau de bord personnalisé ("cartes KPI
épinglées", voir admin-analytics.js) depuis un chantier de simplification
antérieur. `groups=None` (défaut) garde le comportement historique intact
(tout calculer) — non-régression pour tout appelant qui ignore ce paramètre."""
import random
import unittest

import admin_analytics_service
import db
import server
from role_service import Role


def _register_admin(client):
    email = f"tanalytics{random.randint(1_000_000, 9_999_999)}@gmail.com"
    username = f"tanalytics{random.randint(100_000, 999_999)}"
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


class TestOverviewGroupsFiltrage(unittest.TestCase):
    def test_groups_none_calcule_tout_comportement_historique(self):
        payload, error = admin_analytics_service.overview("30j", None, None, groups=None)
        self.assertIsNone(error)
        for group in ("users", "chatbot", "ai", "support", "subscriptions"):
            self.assertIn(group, payload)

    def test_groups_vide_ne_calcule_que_window(self):
        payload, error = admin_analytics_service.overview("30j", None, None, groups=[])
        self.assertIsNone(error)
        self.assertIn("window", payload)
        for group in ("users", "chatbot", "ai", "support", "subscriptions"):
            self.assertNotIn(group, payload)

    def test_groups_partiel_ne_calcule_que_les_groupes_demandes(self):
        payload, error = admin_analytics_service.overview("30j", None, None, groups=["ai", "support"])
        self.assertIsNone(error)
        self.assertIn("window", payload)
        self.assertIn("ai", payload)
        self.assertIn("support", payload)
        self.assertNotIn("users", payload)
        self.assertNotIn("chatbot", payload)
        self.assertNotIn("subscriptions", payload)

    def test_groupe_inconnu_ignore_silencieusement_jamais_une_exception(self):
        payload, error = admin_analytics_service.overview("30j", None, None, groups=["ai", "n_importe_quoi"])
        self.assertIsNone(error)
        self.assertIn("ai", payload)
        self.assertNotIn("n_importe_quoi", payload)

    def test_resultat_dun_groupe_demande_identique_avec_ou_sans_filtrage(self):
        # Le calcul lui-même n'est jamais modifié par ce chantier — seule la
        # décision de le déclencher ou non change.
        full_payload, _ = admin_analytics_service.overview("30j", None, None, groups=None)
        filtered_payload, _ = admin_analytics_service.overview("30j", None, None, groups=["ai"])
        self.assertEqual(full_payload["ai"], filtered_payload["ai"])


class TestEndpointHttpGroupsParam(unittest.TestCase):
    def setUp(self):
        self.client = server.app.test_client()

    def test_sans_parametre_groups_renvoie_tout(self):
        _, headers = _register_admin(self.client)
        resp = self.client.get("/api/admin/analytics/overview", headers=headers)
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        for group in ("users", "chatbot", "ai", "support", "subscriptions"):
            self.assertIn(group, body)

    def test_groups_vide_ne_renvoie_que_window(self):
        _, headers = _register_admin(self.client)
        resp = self.client.get("/api/admin/analytics/overview?groups=", headers=headers)
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertIn("window", body)
        for group in ("users", "chatbot", "ai", "support", "subscriptions"):
            self.assertNotIn(group, body)

    def test_groups_ai_ne_renvoie_que_ai_et_window(self):
        _, headers = _register_admin(self.client)
        resp = self.client.get("/api/admin/analytics/overview?groups=ai", headers=headers)
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertIn("window", body)
        self.assertIn("ai", body)
        self.assertNotIn("users", body)


if __name__ == "__main__":
    unittest.main()
