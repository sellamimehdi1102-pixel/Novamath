"""
Suite SEC-04 : routes publiques de consentement parental (GET status,
accept, refuse, resend) — /api/auth/parental-consent/*, ouvertes sans session
(le parent qui clique le lien reçu par email n'a pas de compte NovaMath).
"""
import random
import unittest
from datetime import date
from unittest.mock import patch

import consent_service as cs
import db
import server


def _fake_ip():
    return f"10.{random.randint(0, 254)}.{random.randint(0, 254)}.{random.randint(1, 254)}"


class ParentalConsentRouteTestCase(unittest.TestCase):
    def setUp(self):
        self.client = server.app.test_client()
        # Ces tests capturent le token via `dev_consent_link`, le filet de
        # secours qui ne s'active que si aucun SMTP n'est configuré (voir
        # email_service.is_configured et consent_service.create_consent_
        # request) — forcé ici indépendamment du .env réellement chargé dans
        # le process de test (peut contenir de vrais identifiants SMTP).
        patcher = patch("email_service.is_configured", return_value=False)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _register_minor(self, parent_email="parent@example.com"):
        today = date.today()
        birth_date = date(today.year - 10, 1, 1).isoformat()
        email = f"pcroute{random.randint(1_000_000, 9_999_999)}@gmail.com"
        payload = {
            "email": email, "username": f"pcroute{random.randint(100_000, 999_999)}", "pseudo": "Enfant",
            "birth_date": birth_date, "parent_email": parent_email,
            "password": "MotDePasse123!", "confirm_password": "MotDePasse123!",
            "accept_terms": True, "accept_privacy": True,
        }
        resp = self.client.post("/api/auth/register", json=payload, headers={"X-Forwarded-For": _fake_ip()})
        token = resp.get_json()["dev_consent_link"].rsplit("/", 1)[-1]
        return email, token


class TestGetConsentStatus(ParentalConsentRouteTestCase):
    def test_token_inconnu_renvoie_404(self):
        resp = self.client.get("/api/auth/parental-consent/token-inexistant")
        self.assertEqual(resp.status_code, 404)

    def test_token_valide_renvoie_le_pseudo_et_le_statut_pending(self):
        _, token = self._register_minor()
        resp = self.client.get(f"/api/auth/parental-consent/{token}")
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertEqual(body["status"], "pending")
        self.assertEqual(body["child_pseudo"], "Enfant")
        self.assertFalse(body["expired"])

    def test_ne_renvoie_jamais_l_email_du_parent(self):
        _, token = self._register_minor()
        resp = self.client.get(f"/api/auth/parental-consent/{token}")
        self.assertNotIn("parent_email", resp.get_json())

    def test_apres_acceptation_le_statut_devient_accepted(self):
        _, token = self._register_minor()
        cs.resolve_consent(token, "accepted")
        resp = self.client.get(f"/api/auth/parental-consent/{token}")
        self.assertEqual(resp.get_json()["status"], "accepted")

    def test_apres_refus_le_statut_devient_refused(self):
        _, token = self._register_minor()
        cs.resolve_consent(token, "refused")
        resp = self.client.get(f"/api/auth/parental-consent/{token}")
        self.assertEqual(resp.get_json()["status"], "refused")


class TestAcceptRoute(ParentalConsentRouteTestCase):
    def test_acceptation_reussie(self):
        email, token = self._register_minor()
        resp = self.client.post(f"/api/auth/parental-consent/{token}/accept")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["status"], "accepted")
        self.assertEqual(db.get_user_by_email(email)["account_status"], "active")

    def test_token_inconnu_renvoie_404(self):
        resp = self.client.post("/api/auth/parental-consent/inconnu/accept")
        self.assertEqual(resp.status_code, 404)

    def test_deja_accepte_renvoie_409(self):
        _, token = self._register_minor()
        self.client.post(f"/api/auth/parental-consent/{token}/accept")
        resp = self.client.post(f"/api/auth/parental-consent/{token}/accept")
        self.assertEqual(resp.status_code, 409)

    def test_expire_renvoie_410(self):
        user = db.get_user_by_id(
            db.create_user(f"pcexpire{random.randint(1_000_000, 9_999_999)}@gmail.com",
                            f"pcexpire{random.randint(100_000, 999_999)}", "Test", "hash")
        )
        token = db.create_parental_consent_request(user["id"], "parent@example.com", days=-1)
        resp = self.client.post(f"/api/auth/parental-consent/{token}/accept")
        self.assertEqual(resp.status_code, 410)


class TestRefuseRoute(ParentalConsentRouteTestCase):
    def test_refus_reussi(self):
        email, token = self._register_minor()
        resp = self.client.post(f"/api/auth/parental-consent/{token}/refuse")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["status"], "refused")
        self.assertEqual(db.get_user_by_email(email)["account_status"], "parental_consent_refused")

    def test_deja_refuse_renvoie_409(self):
        _, token = self._register_minor()
        self.client.post(f"/api/auth/parental-consent/{token}/refuse")
        resp = self.client.post(f"/api/auth/parental-consent/{token}/refuse")
        self.assertEqual(resp.status_code, 409)

    def test_accepte_puis_refuse_renvoie_409(self):
        _, token = self._register_minor()
        self.client.post(f"/api/auth/parental-consent/{token}/accept")
        resp = self.client.post(f"/api/auth/parental-consent/{token}/refuse")
        self.assertEqual(resp.status_code, 409)


class TestResendRoute(ParentalConsentRouteTestCase):
    def test_email_ou_mot_de_passe_incorrect_renvoie_401(self):
        email, _ = self._register_minor()
        resp = self.client.post("/api/auth/parental-consent/resend", json={
            "email": email, "password": "mauvais-mot-de-passe",
        })
        self.assertEqual(resp.status_code, 401)

    def test_compte_inexistant_renvoie_401(self):
        resp = self.client.post("/api/auth/parental-consent/resend", json={
            "email": "inexistant@gmail.com", "password": "peu-importe",
        })
        self.assertEqual(resp.status_code, 401)

    def test_compte_deja_actif_renvoie_400(self):
        email = f"pcresendactive{random.randint(1_000_000, 9_999_999)}@gmail.com"
        payload = {
            "email": email, "username": f"pcra{random.randint(100_000, 999_999)}", "pseudo": "Test",
            "birth_date": "2000-01-01",
            "password": "MotDePasse123!", "confirm_password": "MotDePasse123!",
            "accept_terms": True, "accept_privacy": True,
        }
        self.client.post("/api/auth/register", json=payload, headers={"X-Forwarded-For": _fake_ip()})
        resp = self.client.post("/api/auth/parental-consent/resend", json={
            "email": email, "password": "MotDePasse123!",
        })
        self.assertEqual(resp.status_code, 400)

    def test_renvoi_reussi_invalide_l_ancien_token(self):
        email, old_token = self._register_minor()
        resp = self.client.post("/api/auth/parental-consent/resend", json={
            "email": email, "password": "MotDePasse123!",
        })
        self.assertEqual(resp.status_code, 200)
        new_link = resp.get_json()["dev_consent_link"]
        new_token = new_link.rsplit("/", 1)[-1]
        self.assertNotEqual(new_token, old_token)
        old_status_resp = self.client.get(f"/api/auth/parental-consent/{old_token}")
        self.assertEqual(old_status_resp.get_json()["status"], "superseded")


if __name__ == "__main__":
    unittest.main()
