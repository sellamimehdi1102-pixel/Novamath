"""
Suite SEC-04 : email_service.py — envoi SMTP mocké (aucun appel réseau réel),
filet de secours si non configuré, contenu des templates. Même stratégie de
patch que tests/test_stripe_service.py (config.* directement, pas os.environ,
puisque config.py lit l'environnement une seule fois à l'import).
"""
import unittest
from unittest.mock import MagicMock, patch

import config
import email_service


class ConfiguredEmailTestCase(unittest.TestCase):
    """Bascule config.EMAIL_* vers une configuration SMTP complète pour la
    durée du test, puis restaure l'état précédent (jamais un test qui laisse
    une configuration polluer le suivant)."""

    def setUp(self):
        self._backup = {
            "EMAIL_SMTP_HOST": config.EMAIL_SMTP_HOST,
            "EMAIL_SMTP_PORT": config.EMAIL_SMTP_PORT,
            "EMAIL_SMTP_USERNAME": config.EMAIL_SMTP_USERNAME,
            "EMAIL_SMTP_PASSWORD": config.EMAIL_SMTP_PASSWORD,
            "EMAIL_SMTP_USE_TLS": config.EMAIL_SMTP_USE_TLS,
            "EMAIL_FROM_ADDRESS": config.EMAIL_FROM_ADDRESS,
            "EMAIL_FROM_NAME": config.EMAIL_FROM_NAME,
        }
        config.EMAIL_SMTP_HOST = "smtp.example.com"
        config.EMAIL_SMTP_PORT = 587
        config.EMAIL_SMTP_USERNAME = "user"
        config.EMAIL_SMTP_PASSWORD = "secret"
        config.EMAIL_SMTP_USE_TLS = True
        config.EMAIL_FROM_ADDRESS = "no-reply@novamath.fr"
        config.EMAIL_FROM_NAME = "NovaMath"

    def tearDown(self):
        for key, value in self._backup.items():
            setattr(config, key, value)


class UnconfiguredEmailTestCase(unittest.TestCase):
    def setUp(self):
        self._backup_host = config.EMAIL_SMTP_HOST
        self._backup_from = config.EMAIL_FROM_ADDRESS
        config.EMAIL_SMTP_HOST = None
        config.EMAIL_FROM_ADDRESS = None

    def tearDown(self):
        config.EMAIL_SMTP_HOST = self._backup_host
        config.EMAIL_FROM_ADDRESS = self._backup_from


class TestIsConfigured(unittest.TestCase):
    def test_absent_par_defaut_dans_lenvironnement_de_test(self):
        # Ne dépend d'aucun état préalable : vérifie juste la cohérence de
        # is_configured() avec les deux champs requis.
        self.assertEqual(email_service.is_configured(), bool(config.EMAIL_SMTP_HOST and config.EMAIL_FROM_ADDRESS))


class TestSendEmailNonConfigure(UnconfiguredEmailTestCase):
    def test_renvoie_false_sans_lever(self):
        sent = email_service.send_email("parent@example.com", "Sujet", "<p>html</p>", "texte")
        self.assertFalse(sent)

    def test_leve_email_not_configured_si_required(self):
        with self.assertRaises(email_service.EmailNotConfigured):
            email_service.send_email("parent@example.com", "Sujet", "<p>html</p>", "texte", required=True)


class TestSendEmailConfigure(ConfiguredEmailTestCase):
    @patch("email_service.smtplib.SMTP")
    def test_envoie_via_smtp_et_renvoie_true(self, mock_smtp_cls):
        mock_smtp = MagicMock()
        mock_smtp_cls.return_value.__enter__.return_value = mock_smtp
        sent = email_service.send_email("parent@example.com", "Sujet", "<p>html</p>", "texte")
        self.assertTrue(sent)
        mock_smtp.sendmail.assert_called_once()

    @patch("email_service.smtplib.SMTP")
    def test_appelle_starttls_si_use_tls(self, mock_smtp_cls):
        mock_smtp = MagicMock()
        mock_smtp_cls.return_value.__enter__.return_value = mock_smtp
        email_service.send_email("parent@example.com", "Sujet", "<p>html</p>", "texte")
        mock_smtp.starttls.assert_called_once()

    @patch("email_service.smtplib.SMTP")
    def test_appelle_login_si_identifiants_fournis(self, mock_smtp_cls):
        mock_smtp = MagicMock()
        mock_smtp_cls.return_value.__enter__.return_value = mock_smtp
        email_service.send_email("parent@example.com", "Sujet", "<p>html</p>", "texte")
        mock_smtp.login.assert_called_once_with("user", "secret")

    @patch("email_service.smtplib.SMTP")
    def test_echec_smtp_renvoie_false_sans_lever(self, mock_smtp_cls):
        import smtplib
        mock_smtp_cls.side_effect = smtplib.SMTPException("boom")
        sent = email_service.send_email("parent@example.com", "Sujet", "<p>html</p>", "texte")
        self.assertFalse(sent)

    @patch("email_service.smtplib.SMTP")
    def test_erreur_reseau_renvoie_false_sans_lever(self, mock_smtp_cls):
        mock_smtp_cls.side_effect = OSError("connexion refusée")
        sent = email_service.send_email("parent@example.com", "Sujet", "<p>html</p>", "texte")
        self.assertFalse(sent)

    @patch("email_service.smtplib.SMTP")
    def test_ne_journalise_jamais_le_contenu_du_message(self, mock_smtp_cls):
        """Un lien de consentement parental est un secret au même titre qu'un
        token de réinitialisation de mot de passe — jamais dans les logs."""
        mock_smtp = MagicMock()
        mock_smtp_cls.return_value.__enter__.return_value = mock_smtp
        with self.assertLogs("email_service", level="INFO") as logs:
            email_service.send_email("parent@example.com", "Sujet secret", "<p>lien-secret</p>", "lien-secret")
        for line in logs.output:
            self.assertNotIn("lien-secret", line)
            self.assertNotIn("parent@example.com", line)


class TestEmailTemplates(unittest.TestCase):
    def test_build_parental_consent_request_email_contient_le_lien(self):
        subject, html, text = email_service.build_parental_consent_request_email(
            "Eleve", "https://novamath.fr/parent/consent/abc123", "2026-12-31T00:00:00+00:00"
        )
        self.assertIn("Eleve", subject)
        self.assertIn("https://novamath.fr/parent/consent/abc123", html)
        self.assertIn("https://novamath.fr/parent/consent/abc123", text)

    def test_build_parental_consent_confirmed_email_mentionne_le_pseudo(self):
        subject, html, text = email_service.build_parental_consent_confirmed_email("Eleve")
        self.assertIn("Eleve", html)
        self.assertIn("Eleve", text)

    def test_build_parental_consent_refused_email_mentionne_le_pseudo(self):
        subject, html, text = email_service.build_parental_consent_refused_email("Eleve")
        self.assertIn("Eleve", html)

    def test_build_policy_updated_email_mentionne_le_pseudo(self):
        subject, html, text = email_service.build_policy_updated_email("Eleve")
        self.assertIn("Eleve", html)

    def test_templates_ne_contiennent_jamais_de_script(self):
        _, html, _ = email_service.build_parental_consent_request_email(
            "Eleve", "https://novamath.fr/parent/consent/abc123", "2026-12-31"
        )
        self.assertNotIn("<script", html.lower())


if __name__ == "__main__":
    unittest.main()
