"""
Régression : /api/auth/forgot-password doit réellement tenter d'envoyer
l'email de réinitialisation via email_service, et ne JAMAIS renvoyer le lien
de réinitialisation (`dev_reset_link`) dans la réponse JSON quand cet envoi a
réussi — un token de réinitialisation exposé dans une réponse API accessible
à quiconque connaît l'email de la victime permettrait une prise de contrôle
de compte sans jamais toucher à sa boîte mail (voir auth.py::forgot_password).

Patch de auth.email_service.send_email (comme tests/test_billing_service.py
patche stripe_service) : aucun appel SMTP réel, on vérifie uniquement le
câblage forgot_password <-> email_service.
"""
import random
import unittest
from unittest.mock import patch

import server


def _random_email():
    return f"fpwd{random.randint(1_000_000, 9_999_999)}@gmail.com"


class ForgotPasswordRouteTestCase(unittest.TestCase):
    def setUp(self):
        self.client = server.app.test_client()
        self.email = _random_email()
        resp = self.client.post("/api/auth/register", json={
            "email": self.email, "username": f"fpwd{random.randint(100_000, 999_999)}", "pseudo": "Eleve",
            "birth_date": "2000-01-01",
            "password": "MotDePasse123!", "confirm_password": "MotDePasse123!",
            "accept_terms": True, "accept_privacy": True,
        })
        self.assertEqual(resp.status_code, 201)


class TestEnvoiEchoueOuNonConfigure(ForgotPasswordRouteTestCase):
    @patch("auth.email_service.is_configured", return_value=False)
    @patch("auth.email_service.send_email", return_value=False)
    def test_renvoie_le_lien_en_secours_si_non_configure(self, mock_send, mock_configured):
        resp = self.client.post("/api/auth/forgot-password", json={"email": self.email})
        body = resp.get_json()
        self.assertTrue(body["ok"])
        self.assertIn("dev_reset_link", body)
        mock_send.assert_called_once()


class TestEnvoiReussi(ForgotPasswordRouteTestCase):
    """SMTP configuré (is_configured() = True) : le lien ne doit jamais fuiter
    dans la réponse, que l'envoi réussisse ou échoue de façon transitoire (voir
    auth.py::forgot_password — seul l'état de configuration, jamais le
    résultat de l'envoi, ne doit décider du filet de secours dev_reset_link)."""

    @patch("auth.email_service.is_configured", return_value=True)
    @patch("auth.email_service.send_email", return_value=True)
    def test_najamais_le_lien_dans_la_reponse_si_lenvoi_reussit(self, mock_send, mock_configured):
        resp = self.client.post("/api/auth/forgot-password", json={"email": self.email})
        body = resp.get_json()
        self.assertTrue(body["ok"])
        self.assertNotIn("dev_reset_link", body)

    @patch("auth.email_service.is_configured", return_value=True)
    @patch("auth.email_service.send_email", return_value=False)
    def test_najamais_le_lien_dans_la_reponse_si_lenvoi_echoue_transitoirement(self, mock_send, mock_configured):
        resp = self.client.post("/api/auth/forgot-password", json={"email": self.email})
        body = resp.get_json()
        self.assertTrue(body["ok"])
        self.assertNotIn("dev_reset_link", body)

    @patch("auth.email_service.is_configured", return_value=True)
    @patch("auth.email_service.send_email", return_value=True)
    def test_envoie_au_bon_destinataire_avec_un_lien_de_reinitialisation(self, mock_send, mock_configured):
        self.client.post("/api/auth/forgot-password", json={"email": self.email})
        mock_send.assert_called_once()
        to, subject, html, text = mock_send.call_args[0]
        self.assertEqual(to, self.email)
        self.assertIn("réinitialisation", subject.lower())
        self.assertIn("reset-password.html?token=", html)
        self.assertIn("reset-password.html?token=", text)

    @patch("auth.email_service.is_configured", return_value=True)
    @patch("auth.email_service.send_email", return_value=True)
    def test_le_token_envoye_par_email_reste_utilisable_pour_reinitialiser(self, mock_send, mock_configured):
        """L'envoi par email ne doit jamais empêcher /api/auth/reset-password
        de fonctionner avec le token réellement créé en base."""
        self.client.post("/api/auth/forgot-password", json={"email": self.email})
        text_body = mock_send.call_args[0][3]
        token = text_body.split("token=")[1].split()[0]

        resp = self.client.post("/api/auth/reset-password", json={
            "token": token, "password": "NouveauMotDePasse123!", "confirm_password": "NouveauMotDePasse123!",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.get_json()["ok"])

        # Le nouveau mot de passe doit réellement fonctionner pour se connecter.
        login_resp = self.client.post("/api/auth/login", json={
            "email": self.email, "password": "NouveauMotDePasse123!",
        })
        self.assertEqual(login_resp.status_code, 200)


if __name__ == "__main__":
    unittest.main()
