"""
Suite SEC-04 : validation unitaire côté auth.py (validate_birth_date,
validate_parent_email) et decorateur consent_service.requires_active_account,
non couverts par les suites d'intégration serveur (test_server_registration_
age.py, test_server_parental_consent.py).
"""
import unittest
from datetime import date, timedelta

import auth
import consent_service as cs
import server


class TestValidateBirthDate(unittest.TestCase):
    def test_date_valide_est_normalisee_en_iso(self):
        value, err = auth.validate_birth_date("2000-01-01")
        self.assertIsNone(err)
        self.assertEqual(value, "2000-01-01")

    def test_absente(self):
        value, err = auth.validate_birth_date(None)
        self.assertIsNotNone(err)

    def test_chaine_vide(self):
        value, err = auth.validate_birth_date("   ")
        self.assertIsNotNone(err)

    def test_format_us_invalide(self):
        value, err = auth.validate_birth_date("01/01/2000")
        self.assertIsNotNone(err)

    def test_jour_hors_limites(self):
        value, err = auth.validate_birth_date("2000-02-31")
        self.assertIsNotNone(err)

    def test_date_de_demain_refusee(self):
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        value, err = auth.validate_birth_date(tomorrow)
        self.assertIsNotNone(err)

    def test_aujourd_hui_accepte(self):
        today = date.today().isoformat()
        value, err = auth.validate_birth_date(today)
        self.assertIsNone(err)

    def test_age_121_ans_refuse(self):
        too_old = date(date.today().year - 121, 1, 1).isoformat()
        value, err = auth.validate_birth_date(too_old)
        self.assertIsNotNone(err)

    def test_age_119_ans_accepte(self):
        old = date(date.today().year - 119, 1, 1).isoformat()
        value, err = auth.validate_birth_date(old)
        self.assertIsNone(err)


class TestValidateParentEmail(unittest.TestCase):
    def test_email_standard_valide(self):
        value, err = auth.validate_parent_email("parent@example.com")
        self.assertIsNone(err)
        self.assertEqual(value, "parent@example.com")

    def test_domaine_non_gmail_accepte(self):
        """Contrairement à validate_email (comptes NovaMath, Gmail
        uniquement), l'email d'un parent n'est jamais restreint à un
        fournisseur particulier."""
        value, err = auth.validate_parent_email("parent@outlook.fr")
        self.assertIsNone(err)

    def test_absent(self):
        value, err = auth.validate_parent_email(None)
        self.assertIsNotNone(err)

    def test_sans_arobase(self):
        value, err = auth.validate_parent_email("pas-un-email")
        self.assertIsNotNone(err)

    def test_sans_domaine(self):
        value, err = auth.validate_parent_email("parent@")
        self.assertIsNotNone(err)

    def test_normalise_en_minuscules(self):
        value, err = auth.validate_parent_email("Parent@Example.COM")
        self.assertEqual(value, "parent@example.com")


class TestRequiresActiveAccountDecorator(unittest.TestCase):
    def setUp(self):
        self.client = server.app.test_client()

    def test_me_reste_joignable_pour_un_compte_pending(self):
        """/api/auth/me n'est jamais protégée par requires_active_account
        (voir sa docstring) : un compte en attente doit pouvoir connaître son
        propre statut, mais ne reçoit par ailleurs aucune session tant que le
        consentement n'est pas résolu (voir test_server_registration_age.py) —
        ce test documente juste l'absence de session, pas un accès élargi."""
        import random
        from datetime import date
        today = date.today()
        birth_date = date(today.year - 10, 1, 1).isoformat()
        resp = self.client.post("/api/auth/register", json={
            "email": f"reqactive{random.randint(1_000_000, 9_999_999)}@gmail.com",
            "username": f"reqactive{random.randint(100_000, 999_999)}", "pseudo": "Test",
            "birth_date": birth_date, "parent_email": "parent@example.com",
            "password": "MotDePasse123!", "confirm_password": "MotDePasse123!",
            "accept_terms": True, "accept_privacy": True,
        })
        self.assertEqual(resp.status_code, 202)
        me_resp = self.client.get("/api/auth/me")
        self.assertEqual(me_resp.status_code, 401)


class TestParentConsentPage(unittest.TestCase):
    def setUp(self):
        self.client = server.app.test_client()

    def test_page_publique_accessible_sans_session(self):
        resp = self.client.get("/parent/consent/un-token-quelconque")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"NovaMath", resp.data)

    def test_page_ne_leve_jamais_meme_avec_un_token_farfelu(self):
        resp = self.client.get("/parent/consent/../../etc/passwd")
        self.assertIn(resp.status_code, (200, 404))


if __name__ == "__main__":
    unittest.main()
