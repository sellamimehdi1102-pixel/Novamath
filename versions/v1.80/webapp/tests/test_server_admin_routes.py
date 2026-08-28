"""
Suite Phase 0 (SEC-05) : /api/dev/dashboard doit être réservée aux comptes
ADMIN/SUPER_ADMIN — vérifie le branchement réel de @requires_role(Role.ADMIN)
sur cette route (server.py), pour chaque catégorie d'appelant possible :
anonyme, invité, utilisateur normal, administrateur. Complète
tests/test_role_service.py (qui couvre role_service.py de façon isolée).
"""
import random
import unittest

import db
import server
from role_service import Role


def _register(client):
    email = f"admintest{random.randint(1_000_000, 9_999_999)}@gmail.com"
    username = f"admintest{random.randint(100_000, 999_999)}"
    resp = client.post("/api/auth/register", json={
        "email": email, "username": username, "pseudo": "Test",
        "birth_date": "2000-01-01",
        "password": "MotDePasse123!", "confirm_password": "MotDePasse123!",
        "accept_terms": True, "accept_privacy": True,
    })
    user = resp.get_json()["user"]
    csrf = client.get_cookie("nm_csrf").value
    return user, {"X-CSRF-Token": csrf}


class TestDevDashboardReserveeAuxAdmins(unittest.TestCase):
    ENDPOINT = "/api/dev/dashboard"

    def setUp(self):
        self.client = server.app.test_client()

    def test_anonyme_non_connecte_recoit_401(self):
        # login_required s'exécute avant requires_role dans la pile de
        # décorateurs : un anonyme est rejeté avant même le contrôle de rôle.
        resp = self.client.get(self.ENDPOINT)
        self.assertEqual(resp.status_code, 401)

    def test_invite_recoit_403(self):
        resp = self.client.post("/api/auth/guest")
        self.assertEqual(resp.status_code, 201)
        resp = self.client.get(self.ENDPOINT)
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.get_json(), {"error": "Réservé à l'administrateur."})

    def test_utilisateur_normal_recoit_403_jamais_les_donnees(self):
        _register(self.client)
        resp = self.client.get(self.ENDPOINT)
        self.assertEqual(resp.status_code, 403)
        body = resp.get_json()
        self.assertEqual(body, {"error": "Réservé à l'administrateur."})
        # Aucune fuite de données internes dans la réponse de refus.
        self.assertNotIn("snapshot", str(body).lower())

    def test_administrateur_accede_au_tableau_de_bord(self):
        user, _ = _register(self.client)
        db.set_user_role(user["id"], Role.ADMIN.value)
        resp = self.client.get(self.ENDPOINT)
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.get_json(), dict)

    def test_super_admin_accede_aussi(self):
        user, _ = _register(self.client)
        db.set_user_role(user["id"], Role.SUPER_ADMIN.value)
        resp = self.client.get(self.ENDPOINT)
        self.assertEqual(resp.status_code, 200)

    def test_moderateur_reste_bloque_role_insuffisant(self):
        user, _ = _register(self.client)
        db.set_user_role(user["id"], Role.MODERATOR.value)
        resp = self.client.get(self.ENDPOINT)
        self.assertEqual(resp.status_code, 403)

    def test_flag_enable_dev_dashboard_toujours_respecte_pour_un_admin(self):
        user, _ = _register(self.client)
        db.set_user_role(user["id"], Role.ADMIN.value)
        original = server.ENABLE_DEV_DASHBOARD
        server.ENABLE_DEV_DASHBOARD = False
        try:
            resp = self.client.get(self.ENDPOINT)
            self.assertEqual(resp.status_code, 404)
        finally:
            server.ENABLE_DEV_DASHBOARD = original


class TestRoleExposeDansLeProfilPublic(unittest.TestCase):
    """Le rôle doit être lisible par le frontend (toute UI admin future) via
    les mêmes routes déjà utilisées pour le plan — jamais de route dédiée
    supplémentaire, jamais de duplication de _public_user."""

    def setUp(self):
        self.client = server.app.test_client()

    def test_role_present_a_linscription(self):
        user, _ = _register(self.client)
        self.assertEqual(user["role"], "user")

    def test_role_present_sur_me(self):
        _register(self.client)
        resp = self.client.get("/api/auth/me")
        self.assertEqual(resp.get_json()["user"]["role"], "user")

    def test_role_reflete_une_promotion_admin_sur_me(self):
        user, _ = _register(self.client)
        db.set_user_role(user["id"], Role.ADMIN.value)
        resp = self.client.get("/api/auth/me")
        self.assertEqual(resp.get_json()["user"]["role"], "admin")


if __name__ == "__main__":
    unittest.main()
