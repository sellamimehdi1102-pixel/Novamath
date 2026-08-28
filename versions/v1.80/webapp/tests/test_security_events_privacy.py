"""
Suite SEC-04 : journalisation RGPD — vérifie que la rectification (PUT
/api/auth/me) et la suppression de compte (DELETE /api/auth/me), déjà
existantes avant ce chantier, journalisent désormais explicitement
`gdpr_rectification`/`gdpr_delete_account`, et qu'aucun événement de sécurité
RGPD n'enregistre jamais de donnée sensible (mot de passe, token, secret).
"""
import random
import unittest

import db
import server


def _fake_ip():
    return f"10.{random.randint(0, 254)}.{random.randint(0, 254)}.{random.randint(1, 254)}"


def _register(client):
    email = f"secevt{random.randint(1_000_000, 9_999_999)}@gmail.com"
    username = f"secevt{random.randint(100_000, 999_999)}"
    resp = client.post("/api/auth/register", json={
        "email": email, "username": username, "pseudo": "Test",
        "birth_date": "2000-01-01",
        "password": "MotDePasse123!", "confirm_password": "MotDePasse123!",
        "accept_terms": True, "accept_privacy": True,
    }, headers={"X-Forwarded-For": _fake_ip()})
    user = resp.get_json()["user"]
    csrf = client.get_cookie("nm_csrf").value
    return user, {"X-CSRF-Token": csrf}, email


class SecurityEventsPrivacyTestCase(unittest.TestCase):
    def setUp(self):
        self.client = server.app.test_client()


class TestRectificationLogging(SecurityEventsPrivacyTestCase):
    def test_modification_du_pseudo_journalise_gdpr_rectification(self):
        user, headers, _ = _register(self.client)
        before = db.count_security_events("gdpr_rectification")
        resp = self.client.put("/api/auth/me", json={"pseudo": "NouveauPseudo"}, headers=headers)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(db.count_security_events("gdpr_rectification"), before + 1)

    def test_requete_sans_champ_modifie_ne_journalise_rien(self):
        user, headers, _ = _register(self.client)
        before = db.count_security_events("gdpr_rectification")
        self.client.put("/api/auth/me", json={}, headers=headers)
        self.assertEqual(db.count_security_events("gdpr_rectification"), before)

    def test_changement_email_journalise_aussi_gdpr_rectification(self):
        user, headers, email = _register(self.client)
        before = db.count_security_events("gdpr_rectification")
        new_email = f"newmail{random.randint(1_000_000, 9_999_999)}@gmail.com"
        resp = self.client.put(
            "/api/auth/me",
            json={"email": new_email, "current_password": "MotDePasse123!"},
            headers=headers,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(db.count_security_events("gdpr_rectification"), before + 1)


class TestDeletionLogging(SecurityEventsPrivacyTestCase):
    def test_suppression_journalise_gdpr_delete_account(self):
        user, headers, _ = _register(self.client)
        before = db.count_security_events("gdpr_delete_account")
        resp = self.client.delete(
            "/api/auth/me", json={"confirm": True, "password": "MotDePasse123!"}, headers=headers,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(db.count_security_events("gdpr_delete_account"), before + 1)

    def test_suppression_conserve_les_preuves_de_consentement(self):
        user, headers, _ = _register(self.client)
        records_before = db.list_consent_records(user["id"])
        self.assertEqual(len(records_before), 2)  # terms + privacy_policy
        self.client.delete("/api/auth/me", json={"confirm": True, "password": "MotDePasse123!"}, headers=headers)
        records_after = db.list_consent_records(user["id"])
        self.assertEqual(len(records_after), 2)

    def test_suppression_supprime_bien_le_compte(self):
        user, headers, email = _register(self.client)
        self.client.delete("/api/auth/me", json={"confirm": True, "password": "MotDePasse123!"}, headers=headers)
        self.assertIsNone(db.get_user_by_email(email))


class TestNoSensitiveDataLogged(SecurityEventsPrivacyTestCase):
    def test_les_evenements_de_securite_rgpd_ne_stockent_jamais_de_mot_de_passe(self):
        user, headers, _ = _register(self.client)
        self.client.put("/api/auth/me", json={"pseudo": "Autre"}, headers=headers)
        events = db.list_security_events_for_user(user["id"])
        for event in events:
            self.assertNotIn("MotDePasse123", str(event))

    def test_les_evenements_de_consentement_parental_ne_stockent_jamais_le_token(self):
        import consent_service as cs
        from datetime import date
        today = date.today()
        birth_date = date(today.year - 10, 1, 1).isoformat()
        resp = self.client.post("/api/auth/register", json={
            "email": f"secevtminor{random.randint(1_000_000, 9_999_999)}@gmail.com",
            "username": f"secevtminor{random.randint(100_000, 999_999)}", "pseudo": "Enfant",
            "birth_date": birth_date, "parent_email": "parent@example.com",
            "password": "MotDePasse123!", "confirm_password": "MotDePasse123!",
            "accept_terms": True, "accept_privacy": True,
        }, headers={"X-Forwarded-For": _fake_ip()})
        token = resp.get_json()["dev_consent_link"].rsplit("/", 1)[-1]
        cs.resolve_consent(token, "accepted")
        row = db.get_parental_consent_request(token)
        events = db.list_security_events_for_user(row["user_id"])
        for event in events:
            self.assertNotIn(token, str(event))


if __name__ == "__main__":
    unittest.main()
