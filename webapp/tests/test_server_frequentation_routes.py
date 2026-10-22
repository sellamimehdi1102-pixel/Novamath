"""
Suite Phase 2 Cloudflare (audit admin, 2026-10-21) — /api/admin/frequentation/*
doit être réservée aux comptes ADMIN/SUPER_ADMIN (décision validée
explicitement pour ce module, contrairement à "Analytics" qui reste ouvert à
SUPPORT) — vérifie le branchement réel de
@requires_role(admin_nav_service.module_by_path("/admin/frequentation").
minimum_role) sur ces routes (server.py), pour chaque catégorie d'appelant
possible. Même structure que test_server_admin_routes.py.

Aucun appel réseau réel vers Cloudflare : CLOUDFLARE_API_TOKEN/
CLOUDFLARE_ACCOUNT_TAG/CLOUDFLARE_SITE_TAG restent absents (comportement par
défaut du processus pytest, voir conftest.py) — les routes renvoient donc
toujours des métriques {"available": false, ...}, jamais une exception.
"""
import random
import unittest

import db
import server
from role_service import Role


def _register(client):
    email = f"freqtest{random.randint(1_000_000, 9_999_999)}@gmail.com"
    username = f"freqtest{random.randint(100_000, 999_999)}"
    resp = client.post("/api/auth/register", json={
        "email": email, "username": username, "pseudo": "Test",
        "birth_date": "2000-01-01",
        "password": "MotDePasse123!", "confirm_password": "MotDePasse123!",
        "accept_terms": True, "accept_privacy": True,
    })
    return resp.get_json()["user"]


class TestFrequentationReserveeAuxAdmins(unittest.TestCase):
    ENDPOINTS = (
        "/api/admin/frequentation/filters",
        "/api/admin/frequentation/overview",
        "/api/admin/frequentation/charts",
        "/api/admin/frequentation/rankings",
    )

    def setUp(self):
        self.client = server.app.test_client()

    def test_anonyme_non_connecte_recoit_401_sur_chaque_route(self):
        for endpoint in self.ENDPOINTS:
            resp = self.client.get(endpoint)
            self.assertEqual(resp.status_code, 401, endpoint)

    def test_invite_recoit_403(self):
        resp = self.client.post("/api/auth/guest")
        self.assertEqual(resp.status_code, 201)
        resp = self.client.get("/api/admin/frequentation/overview")
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.get_json(), {"error": "Réservé à l'administrateur."})

    def test_utilisateur_normal_recoit_403(self):
        _register(self.client)
        resp = self.client.get("/api/admin/frequentation/overview")
        self.assertEqual(resp.status_code, 403)

    def test_support_insuffisant_pour_ce_module(self):
        # Contrairement au module "Analytics" interne (ouvert à SUPPORT), la
        # décision validée pour "Fréquentation" est ADMIN minimum — un rôle
        # SUPPORT reste donc bloqué ici.
        user = _register(self.client)
        db.set_user_role(user["id"], Role.SUPPORT.value)
        resp = self.client.get("/api/admin/frequentation/overview")
        self.assertEqual(resp.status_code, 403)

    def test_moderateur_insuffisant(self):
        user = _register(self.client)
        db.set_user_role(user["id"], Role.MODERATOR.value)
        resp = self.client.get("/api/admin/frequentation/overview")
        self.assertEqual(resp.status_code, 403)

    def test_admin_accede_a_toutes_les_routes(self):
        user = _register(self.client)
        db.set_user_role(user["id"], Role.ADMIN.value)
        for endpoint in self.ENDPOINTS:
            resp = self.client.get(endpoint)
            self.assertEqual(resp.status_code, 200, endpoint)
            self.assertIsInstance(resp.get_json(), dict)

    def test_super_admin_accede_aussi(self):
        user = _register(self.client)
        db.set_user_role(user["id"], Role.SUPER_ADMIN.value)
        resp = self.client.get("/api/admin/frequentation/overview")
        self.assertEqual(resp.status_code, 200)

    def test_overview_sans_configuration_renvoie_donnees_non_disponibles_jamais_une_erreur(self):
        user = _register(self.client)
        db.set_user_role(user["id"], Role.ADMIN.value)
        resp = self.client.get("/api/admin/frequentation/overview")
        self.assertEqual(resp.status_code, 200)
        payload = resp.get_json()
        self.assertFalse(payload["pageviews"]["available"])
        self.assertFalse(payload["visits"]["available"])

    def test_module_frequentation_visible_dans_le_menu_pour_un_admin_seulement(self):
        user = _register(self.client)
        # /api/admin/nav exige déjà SUPPORT minimum (ADMIN_MINIMUM_ROLE,
        # voir server.py) — un simple compte SUPPORT voit le menu mais pas le
        # module "Fréquentation" (ADMIN minimum, décision validée pour ce
        # module précis).
        db.set_user_role(user["id"], Role.SUPPORT.value)
        resp = self.client.get("/api/admin/nav")
        self.assertEqual(resp.status_code, 200)
        module_ids = [m["id"] for m in resp.get_json()["modules"]]
        self.assertNotIn("frequentation", module_ids)

        db.set_user_role(user["id"], Role.ADMIN.value)
        resp = self.client.get("/api/admin/nav")
        module_ids = [m["id"] for m in resp.get_json()["modules"]]
        self.assertIn("frequentation", module_ids)


if __name__ == "__main__":
    unittest.main()
