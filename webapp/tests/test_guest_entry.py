"""POST /api/auth/guest : une session déjà valide (invité ou compte réel) est
réutilisée, jamais remplacée ; sans session valide, un invité est créé."""
import random
import unittest
from unittest import mock

import auth
import db
import server


def _guest_count():
    conn = db.get_connection()
    try:
        return conn.execute("SELECT COUNT(*) AS n FROM users WHERE auth_provider = 'guest'").fetchone()["n"]
    finally:
        conn.close()


class TestGuestEntry(unittest.TestCase):
    def setUp(self):
        self.client = server.app.test_client()

    def test_sans_session_cree_un_invite(self):
        before = _guest_count()
        resp = self.client.post("/api/auth/guest")
        self.assertEqual(resp.status_code, 201)
        self.assertTrue(resp.get_json()["user"]["is_guest"])
        self.assertEqual(_guest_count(), before + 1)

    def test_session_invitee_valide_reutilisee_sans_nouveau_compte(self):
        first = self.client.post("/api/auth/guest").get_json()["user"]
        before = _guest_count()
        for _ in range(3):
            resp = self.client.post("/api/auth/guest")
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.get_json()["user"]["id"], first["id"])
        self.assertEqual(_guest_count(), before)
        self.assertEqual(self.client.get("/api/auth/me").get_json()["user"]["id"], first["id"])

    def test_session_invitee_expiree_donne_un_nouvel_invite(self):
        first = self.client.post("/api/auth/guest").get_json()["user"]
        with mock.patch.object(db, "is_guest_expired", return_value=True):
            resp = self.client.post("/api/auth/guest")
        self.assertEqual(resp.status_code, 201)
        self.assertNotEqual(resp.get_json()["user"]["id"], first["id"])

    def test_compte_connecte_jamais_remplace_par_un_invite(self):
        reg = self.client.post("/api/auth/register", json={
            "email": f"guest{random.randint(1_000_000, 9_999_999)}@gmail.com",
            "username": f"guestuser{random.randint(100_000, 999_999)}", "pseudo": "Test",
            "birth_date": "2000-01-01", "password": "MotDePasse123!", "confirm_password": "MotDePasse123!",
            "accept_terms": True, "accept_privacy": True,
        })
        self.assertEqual(reg.status_code, 201)
        real_id = reg.get_json()["user"]["id"]
        before = _guest_count()
        resp = self.client.post("/api/auth/guest")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["user"]["id"], real_id)
        self.assertFalse(resp.get_json()["user"].get("is_guest"))
        self.assertEqual(self.client.get("/api/auth/me").get_json()["user"]["id"], real_id)
        self.assertEqual(_guest_count(), before)

    def test_session_inconnue_ou_invalide_donne_un_nouvel_invite(self):
        self.client.set_cookie(auth.SESSION_COOKIE, "jeton-invalide")
        self.assertEqual(self.client.post("/api/auth/guest").status_code, 201)


if __name__ == "__main__":
    unittest.main()
