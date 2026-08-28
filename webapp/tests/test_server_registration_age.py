"""
Suite SEC-04 : intégration serveur — vérification de l'âge à l'inscription,
seuil des 15 ans, consentement parental obligatoire pour les mineurs, blocage
de connexion tant que le consentement n'est pas obtenu. Complète la suite
isolée tests/test_consent_service.py.
"""
import random
import unittest
from unittest.mock import patch

import db
import server


def _fake_ip():
    return f"10.{random.randint(0, 254)}.{random.randint(0, 254)}.{random.randint(1, 254)}"


def _register_payload(birth_date="2000-01-01", parent_email=None, **overrides):
    payload = {
        "email": f"regage{random.randint(1_000_000, 9_999_999)}@gmail.com",
        "username": f"regage{random.randint(100_000, 999_999)}",
        "pseudo": "Test",
        "birth_date": birth_date,
        "password": "MotDePasse123!",
        "confirm_password": "MotDePasse123!",
        "accept_terms": True,
        "accept_privacy": True,
    }
    if parent_email is not None:
        payload["parent_email"] = parent_email
    payload.update(overrides)
    return payload


class RegistrationAgeTestCase(unittest.TestCase):
    def setUp(self):
        self.client = server.app.test_client()
        # `dev_consent_link` n'apparaît que si aucun SMTP n'est configuré
        # (voir email_service.is_configured) — forcé ici indépendamment du
        # .env réellement chargé dans le process de test.
        patcher = patch("email_service.is_configured", return_value=False)
        patcher.start()
        self.addCleanup(patcher.stop)


class TestBirthDateValidation(RegistrationAgeTestCase):
    def test_absente_renvoie_400(self):
        payload = _register_payload()
        del payload["birth_date"]
        resp = self.client.post("/api/auth/register", json=payload, headers={"X-Forwarded-For": _fake_ip()})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.get_json()["field"], "birth_date")

    def test_vide_renvoie_400(self):
        resp = self.client.post(
            "/api/auth/register", json=_register_payload(birth_date=""), headers={"X-Forwarded-For": _fake_ip()}
        )
        self.assertEqual(resp.status_code, 400)

    def test_format_invalide_renvoie_400(self):
        resp = self.client.post(
            "/api/auth/register", json=_register_payload(birth_date="pas-une-date"),
            headers={"X-Forwarded-For": _fake_ip()},
        )
        self.assertEqual(resp.status_code, 400)

    def test_date_dans_le_futur_renvoie_400(self):
        resp = self.client.post(
            "/api/auth/register", json=_register_payload(birth_date="2999-01-01"),
            headers={"X-Forwarded-For": _fake_ip()},
        )
        self.assertEqual(resp.status_code, 400)

    def test_age_deraisonnable_renvoie_400(self):
        resp = self.client.post(
            "/api/auth/register", json=_register_payload(birth_date="1850-01-01"),
            headers={"X-Forwarded-For": _fake_ip()},
        )
        self.assertEqual(resp.status_code, 400)

    def test_majeur_valide_cree_un_compte_actif_avec_session(self):
        resp = self.client.post(
            "/api/auth/register", json=_register_payload(birth_date="2000-01-01"),
            headers={"X-Forwarded-For": _fake_ip()},
        )
        self.assertEqual(resp.status_code, 201)
        self.assertIn("user", resp.get_json())
        self.assertIsNotNone(self.client.get_cookie("nm_session"))


class TestMinorRegistration(RegistrationAgeTestCase):
    def _minor_birth_date(self):
        from datetime import date
        today = date.today()
        return date(today.year - 10, 1, 1).isoformat()

    def test_mineur_sans_email_parent_renvoie_400(self):
        resp = self.client.post(
            "/api/auth/register", json=_register_payload(birth_date=self._minor_birth_date()),
            headers={"X-Forwarded-For": _fake_ip()},
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.get_json()["field"], "parent_email")

    def test_mineur_avec_email_parent_invalide_renvoie_400(self):
        resp = self.client.post(
            "/api/auth/register",
            json=_register_payload(birth_date=self._minor_birth_date(), parent_email="pas-un-email"),
            headers={"X-Forwarded-For": _fake_ip()},
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.get_json()["field"], "parent_email")

    def test_mineur_valide_recoit_202_et_statut_pending(self):
        resp = self.client.post(
            "/api/auth/register",
            json=_register_payload(birth_date=self._minor_birth_date(), parent_email="parent@example.com"),
            headers={"X-Forwarded-For": _fake_ip()},
        )
        self.assertEqual(resp.status_code, 202)
        self.assertEqual(resp.get_json()["account_status"], "pending_parental_consent")

    def test_mineur_ne_recoit_aucune_session(self):
        resp = self.client.post(
            "/api/auth/register",
            json=_register_payload(birth_date=self._minor_birth_date(), parent_email="parent@example.com"),
            headers={"X-Forwarded-For": _fake_ip()},
        )
        self.assertEqual(resp.status_code, 202)
        self.assertIsNone(self.client.get_cookie("nm_session"))

    def test_mode_dev_sans_smtp_renvoie_un_lien_de_consentement_en_clair(self):
        resp = self.client.post(
            "/api/auth/register",
            json=_register_payload(birth_date=self._minor_birth_date(), parent_email="parent@example.com"),
            headers={"X-Forwarded-For": _fake_ip()},
        )
        body = resp.get_json()
        self.assertIn("dev_consent_link", body)
        self.assertTrue(body["dev_consent_link"].startswith("/parent/consent/"))

    def test_le_compte_existe_bien_en_base_avec_le_bon_statut(self):
        email = f"regageminor{random.randint(1_000_000, 9_999_999)}@gmail.com"
        payload = _register_payload(birth_date=self._minor_birth_date(), parent_email="parent@example.com")
        payload["email"] = email
        self.client.post("/api/auth/register", json=payload, headers={"X-Forwarded-For": _fake_ip()})
        user = db.get_user_by_email(email)
        self.assertEqual(user["account_status"], "pending_parental_consent")


class TestLoginBlockedForPendingAccount(RegistrationAgeTestCase):
    def _register_minor(self):
        from datetime import date
        today = date.today()
        birth_date = date(today.year - 10, 1, 1).isoformat()
        email = f"regagelogin{random.randint(1_000_000, 9_999_999)}@gmail.com"
        payload = _register_payload(birth_date=birth_date, parent_email="parent@example.com")
        payload["email"] = email
        resp = self.client.post("/api/auth/register", json=payload, headers={"X-Forwarded-For": _fake_ip()})
        return email, resp

    def test_connexion_refusee_tant_que_non_resolu(self):
        email, _ = self._register_minor()
        resp = self.client.post(
            "/api/auth/login", json={"email": email, "password": "MotDePasse123!"},
            headers={"X-Forwarded-For": _fake_ip()},
        )
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.get_json()["account_status"], "pending_parental_consent")

    def test_connexion_reussit_apres_acceptation_du_parent(self):
        import consent_service as cs
        email, resp = self._register_minor()
        link = resp.get_json()["dev_consent_link"]
        token = link.rsplit("/", 1)[-1]
        cs.resolve_consent(token, "accepted")
        login_resp = self.client.post(
            "/api/auth/login", json={"email": email, "password": "MotDePasse123!"},
            headers={"X-Forwarded-For": _fake_ip()},
        )
        self.assertEqual(login_resp.status_code, 200)

    def test_connexion_refusee_apres_refus_du_parent(self):
        import consent_service as cs
        email, resp = self._register_minor()
        link = resp.get_json()["dev_consent_link"]
        token = link.rsplit("/", 1)[-1]
        cs.resolve_consent(token, "refused")
        login_resp = self.client.post(
            "/api/auth/login", json={"email": email, "password": "MotDePasse123!"},
            headers={"X-Forwarded-For": _fake_ip()},
        )
        self.assertEqual(login_resp.status_code, 403)
        self.assertEqual(login_resp.get_json()["account_status"], "parental_consent_refused")


class TestPolicyAcceptanceRecorded(RegistrationAgeTestCase):
    def test_inscription_enregistre_deux_preuves_de_consentement(self):
        email = f"regagepolicy{random.randint(1_000_000, 9_999_999)}@gmail.com"
        payload = _register_payload()
        payload["email"] = email
        self.client.post("/api/auth/register", json=payload, headers={"X-Forwarded-For": _fake_ip()})
        user = db.get_user_by_email(email)
        records = db.list_consent_records(user["id"])
        self.assertEqual({r["consent_type"] for r in records}, {"terms", "privacy_policy"})


if __name__ == "__main__":
    unittest.main()
