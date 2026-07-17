"""
Suite SEC-04 : routes RGPD du compte connecté — /api/data/export (étendu),
/api/privacy/consent-history, /api/privacy/cookie-consent,
/api/privacy/policy-status, /api/privacy/policy-accept.
"""
import random
import unittest

import consent_service as cs
import db
import server


def _fake_ip():
    return f"10.{random.randint(0, 254)}.{random.randint(0, 254)}.{random.randint(1, 254)}"


def _register(client):
    email = f"privroute{random.randint(1_000_000, 9_999_999)}@gmail.com"
    username = f"privroute{random.randint(100_000, 999_999)}"
    resp = client.post("/api/auth/register", json={
        "email": email, "username": username, "pseudo": "Test",
        "birth_date": "2000-01-01",
        "password": "MotDePasse123!", "confirm_password": "MotDePasse123!",
        "accept_terms": True, "accept_privacy": True,
    }, headers={"X-Forwarded-For": _fake_ip()})
    user = resp.get_json()["user"]
    csrf = client.get_cookie("nm_csrf").value
    return user, {"X-CSRF-Token": csrf}


class PrivacyRouteTestCase(unittest.TestCase):
    def setUp(self):
        self.client = server.app.test_client()


class TestDataExportRoute(PrivacyRouteTestCase):
    def test_anonyme_refuse(self):
        resp = self.client.get("/api/data/export")
        self.assertEqual(resp.status_code, 401)

    def test_contient_le_profil_les_stats_et_l_historique_de_consentement(self):
        user, _ = _register(self.client)
        resp = self.client.get("/api/data/export")
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertEqual(body["account"]["id"], user["id"])
        self.assertIn("stats", body)
        self.assertIn("settings", body)
        self.assertIn("course_progress", body)
        self.assertIn("consent_history", body)
        self.assertIn("cookie_consent", body)
        self.assertIn("security_events", body)

    def test_ne_contient_jamais_le_hash_du_mot_de_passe(self):
        _register(self.client)
        body = self.client.get("/api/data/export").get_json()
        self.assertNotIn("password_hash", body["account"])

    def test_a_un_en_tete_content_disposition_attachment(self):
        _register(self.client)
        resp = self.client.get("/api/data/export")
        self.assertIn("attachment", resp.headers.get("Content-Disposition", ""))

    def test_journalise_gdpr_export(self):
        user, _ = _register(self.client)
        before = db.count_security_events("gdpr_export")
        self.client.get("/api/data/export")
        self.assertEqual(db.count_security_events("gdpr_export"), before + 1)


class TestConsentHistoryRoute(PrivacyRouteTestCase):
    def test_anonyme_refuse(self):
        resp = self.client.get("/api/privacy/consent-history")
        self.assertEqual(resp.status_code, 401)

    def test_contient_terms_et_privacy_policy_apres_inscription(self):
        _register(self.client)
        resp = self.client.get("/api/privacy/consent-history")
        self.assertEqual(resp.status_code, 200)
        types = {c["consent_type"] for c in resp.get_json()["consent_history"]}
        self.assertEqual(types, {"terms", "privacy_policy"})


class TestCookieConsentRoutes(PrivacyRouteTestCase):
    def test_get_anonyme_refuse(self):
        resp = self.client.get("/api/privacy/cookie-consent")
        self.assertEqual(resp.status_code, 401)

    def test_get_par_defaut_tout_refuse(self):
        _register(self.client)
        resp = self.client.get("/api/privacy/cookie-consent")
        body = resp.get_json()
        self.assertFalse(body["statistics"])
        self.assertFalse(body["marketing"])

    def test_put_anonyme_refuse(self):
        resp = self.client.put("/api/privacy/cookie-consent", json={"statistics": True, "marketing": True})
        self.assertEqual(resp.status_code, 401)

    def test_put_enregistre_et_relu_par_get(self):
        _, headers = _register(self.client)
        put_resp = self.client.put(
            "/api/privacy/cookie-consent", json={"statistics": True, "marketing": False}, headers=headers,
        )
        self.assertEqual(put_resp.status_code, 200)
        get_resp = self.client.get("/api/privacy/cookie-consent")
        body = get_resp.get_json()
        self.assertTrue(body["statistics"])
        self.assertFalse(body["marketing"])

    def test_put_sans_csrf_refuse(self):
        user, _ = _register(self.client)
        resp = self.client.put("/api/privacy/cookie-consent", json={"statistics": True, "marketing": True})
        self.assertEqual(resp.status_code, 403)

    def test_put_journalise_cookie_consent_updated(self):
        user, headers = _register(self.client)
        before = db.count_security_events("cookie_consent_updated")
        self.client.put("/api/privacy/cookie-consent", json={"statistics": True, "marketing": True}, headers=headers)
        self.assertEqual(db.count_security_events("cookie_consent_updated"), before + 1)


class TestPolicyStatusRoutes(PrivacyRouteTestCase):
    def test_get_anonyme_refuse(self):
        resp = self.client.get("/api/privacy/policy-status")
        self.assertEqual(resp.status_code, 401)

    def test_juste_apres_inscription_aucune_reacceptation_necessaire(self):
        _register(self.client)
        resp = self.client.get("/api/privacy/policy-status")
        self.assertFalse(resp.get_json()["needs_reacceptance"])

    def test_apres_bump_de_version_reacceptation_necessaire(self):
        user, headers = _register(self.client)
        db.set_policy_acceptance(user["id"], terms_version="0.0.1", privacy_version="0.0.1")
        resp = self.client.get("/api/privacy/policy-status")
        self.assertTrue(resp.get_json()["needs_reacceptance"])

    def test_accept_sans_csrf_refuse(self):
        _register(self.client)
        resp = self.client.post("/api/privacy/policy-accept")
        self.assertEqual(resp.status_code, 403)

    def test_accept_remet_a_jour_le_statut(self):
        user, headers = _register(self.client)
        db.set_policy_acceptance(user["id"], terms_version="0.0.1", privacy_version="0.0.1")
        resp = self.client.post("/api/privacy/policy-accept", headers=headers)
        self.assertEqual(resp.status_code, 200)
        status_resp = self.client.get("/api/privacy/policy-status")
        self.assertFalse(status_resp.get_json()["needs_reacceptance"])

    def test_accept_journalise_policy_accepted(self):
        user, headers = _register(self.client)
        before = db.count_security_events("policy_accepted")
        self.client.post("/api/privacy/policy-accept", headers=headers)
        self.assertEqual(db.count_security_events("policy_accepted"), before + 1)


if __name__ == "__main__":
    unittest.main()
