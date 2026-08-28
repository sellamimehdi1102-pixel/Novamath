"""
Suite SEC-04 : privacy_service.py — export RGPD (agrégation base uniquement ;
les fichiers JSON par utilisateur sont fusionnés par server.py, voir
test_server_privacy_routes.py) et historique des consentements.
"""
import random
import unittest

import consent_service as cs
import db
import privacy_service as ps


def _mk_user(prefix="priv"):
    n = random.randint(1_000_000, 999_999_999)
    email = f"{prefix}{n}@gmail.com"
    username = f"{prefix}{n}"[:25]
    user_id = db.create_user(email, username, "Test", "hash")
    return db.get_user_by_id(user_id)


class TestExportAccountData(unittest.TestCase):
    def test_contient_le_profil_sans_secrets(self):
        user = _mk_user()
        export = ps.export_account_data(user)
        self.assertEqual(export["account"]["id"], user["id"])
        self.assertNotIn("password_hash", export["account"])
        self.assertNotIn("two_factor_secret", export["account"])
        self.assertNotIn("two_factor_last_counter", export["account"])

    def test_contient_l_historique_de_consentement(self):
        user = _mk_user()
        cs.record_initial_policy_acceptance(user["id"])
        export = ps.export_account_data(user)
        self.assertEqual(len(export["consent_history"]), 2)

    def test_contient_les_demandes_de_consentement_parental_sans_email_du_parent(self):
        user = _mk_user()
        cs.create_consent_request(user, "parent-export@example.com")
        export = ps.export_account_data(user)
        self.assertEqual(len(export["parental_consent_requests"]), 1)
        self.assertNotIn("parent_email", export["parental_consent_requests"][0])

    def test_contient_les_preferences_cookies(self):
        user = _mk_user()
        cs.set_cookie_consent(user["id"], True, False)
        export = ps.export_account_data(user)
        self.assertTrue(export["cookie_consent"]["statistics"])

    def test_contient_le_journal_de_securite(self):
        user = _mk_user()
        db.log_security_event("login_success", user_id=user["id"], ip="127.0.0.1")
        export = ps.export_account_data(user)
        event_types = [e["event_type"] for e in export["security_events"]]
        self.assertIn("login_success", event_types)

    def test_journalise_l_export(self):
        user = _mk_user()
        before = db.count_security_events("gdpr_export")
        ps.export_account_data(user)
        self.assertEqual(db.count_security_events("gdpr_export"), before + 1)

    def test_export_sans_aucun_consentement_reste_coherent(self):
        user = _mk_user()
        export = ps.export_account_data(user)
        self.assertEqual(export["consent_history"], [])
        self.assertEqual(export["parental_consent_requests"], [])
        self.assertFalse(export["cookie_consent"]["statistics"])


class TestGetConsentHistory(unittest.TestCase):
    def test_vide_par_defaut(self):
        user = _mk_user()
        self.assertEqual(ps.get_consent_history(user["id"]), [])

    def test_reflete_les_decisions_prises(self):
        user = _mk_user()
        cs.record_initial_policy_acceptance(user["id"])
        history = ps.get_consent_history(user["id"])
        types = {h["consent_type"] for h in history}
        self.assertEqual(types, {"terms", "privacy_policy"})


if __name__ == "__main__":
    unittest.main()
