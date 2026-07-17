"""
Suite SEC-04 : migration des colonnes/tables RGPD (birth_date, account_status,
terms_accepted_version, privacy_accepted_version, parental_consent_requests,
consent_records, cookie_consents) — idempotente, comptes existants conservent
un account_status cohérent ('active'). Complète tests/test_role_migration.py.
"""
import unittest

import db


class TestMigrationColonnesRGPD(unittest.TestCase):
    def test_reexecuter_init_db_est_sans_effet(self):
        db.init_db()
        db.init_db()
        db.init_db()

    def test_nouveau_compte_recoit_account_status_active_par_defaut(self):
        user_id = db.create_user(
            f"privacy-migration-{id(self)}@gmail.com", f"privacymigration{id(self)}"[:25], "Test", "hash",
        )
        user = db.get_user_by_id(user_id)
        self.assertIn("account_status", user)
        self.assertEqual(user["account_status"], "active")

    def test_nouveau_compte_n_a_pas_de_date_de_naissance_par_defaut(self):
        user_id = db.create_user(
            f"privacy-migration-bd-{id(self)}@gmail.com", f"privacymigrationbd{id(self)}"[:25], "Test", "hash",
        )
        user = db.get_user_by_id(user_id)
        self.assertIsNone(user["birth_date"])

    def test_compte_invite_recoit_aussi_account_status_active(self):
        user_id = db.create_guest_user(f"privacymigrationguest{id(self)}")
        user = db.get_user_by_id(user_id)
        self.assertEqual(user["account_status"], "active")

    def test_create_user_accepte_birth_date_et_account_status_explicites(self):
        user_id = db.create_user(
            f"privacy-migration-explicit-{id(self)}@gmail.com", f"pmexplicit{id(self)}"[:25], "Test", "hash",
            birth_date="2015-05-05", account_status="pending_parental_consent",
        )
        user = db.get_user_by_id(user_id)
        self.assertEqual(user["birth_date"], "2015-05-05")
        self.assertEqual(user["account_status"], "pending_parental_consent")

    def test_set_account_status_ecrit_et_relit(self):
        user_id = db.create_user(
            f"privacy-migration-set-{id(self)}@gmail.com", f"pmset{id(self)}"[:25], "Test", "hash",
        )
        db.set_account_status(user_id, "parental_consent_refused")
        self.assertEqual(db.get_user_by_id(user_id)["account_status"], "parental_consent_refused")

    def test_set_policy_acceptance_ecrit_terms_et_privacy_independamment(self):
        user_id = db.create_user(
            f"privacy-migration-policy-{id(self)}@gmail.com", f"pmpolicy{id(self)}"[:25], "Test", "hash",
        )
        db.set_policy_acceptance(user_id, terms_version="1.0")
        user = db.get_user_by_id(user_id)
        self.assertEqual(user["terms_accepted_version"], "1.0")
        self.assertIsNone(user["privacy_accepted_version"])

        db.set_policy_acceptance(user_id, privacy_version="1.0")
        user = db.get_user_by_id(user_id)
        self.assertEqual(user["privacy_accepted_version"], "1.0")

    def test_table_parental_consent_requests_existe_et_est_utilisable(self):
        user_id = db.create_user(
            f"privacy-migration-pcr-{id(self)}@gmail.com", f"pmpcr{id(self)}"[:25], "Test", "hash",
        )
        token = db.create_parental_consent_request(user_id, "parent@example.com")
        self.assertIsNotNone(db.get_parental_consent_request(token))

    def test_table_consent_records_existe_et_est_utilisable(self):
        user_id = db.create_user(
            f"privacy-migration-cr-{id(self)}@gmail.com", f"pmcr{id(self)}"[:25], "Test", "hash",
        )
        db.add_consent_record(user_id, "terms", "accepted", "1.0", "127.0.0.1")
        self.assertEqual(len(db.list_consent_records(user_id)), 1)

    def test_table_cookie_consents_existe_et_est_utilisable(self):
        user_id = db.create_user(
            f"privacy-migration-cc-{id(self)}@gmail.com", f"pmcc{id(self)}"[:25], "Test", "hash",
        )
        db.set_cookie_consent(user_id, True, False)
        self.assertIsNotNone(db.get_cookie_consent(user_id))

    def test_consent_records_survit_a_la_suppression_du_compte(self):
        """Preuve légale : jamais supprimée, même après suppression du compte
        (voir le commentaire dans SCHEMA — pas de ON DELETE CASCADE ici,
        contrairement à parental_consent_requests/cookie_consents)."""
        user_id = db.create_user(
            f"privacy-migration-survie-{id(self)}@gmail.com", f"pmsurvie{id(self)}"[:25], "Test", "hash",
        )
        db.add_consent_record(user_id, "terms", "accepted", "1.0", "127.0.0.1")
        db.delete_user(user_id)
        records = db.list_consent_records(user_id)
        self.assertEqual(len(records), 1)

    def test_parental_consent_requests_supprimee_en_cascade_avec_le_compte(self):
        user_id = db.create_user(
            f"privacy-migration-cascade-{id(self)}@gmail.com", f"pmcascade{id(self)}"[:25], "Test", "hash",
        )
        token = db.create_parental_consent_request(user_id, "parent@example.com")
        db.delete_user(user_id)
        self.assertIsNone(db.get_parental_consent_request(token))


if __name__ == "__main__":
    unittest.main()
