"""
Suite Phase 0 (SEC-05) : migration de la colonne users.role — idempotente,
comptes existants conservent un rôle cohérent ('user'), aucune perte de
données. Complète tests/test_role_service.py.
"""
import unittest

import db


class TestMigrationColonneRole(unittest.TestCase):
    def test_reexecuter_init_db_est_sans_effet(self):
        # db.init_db() applique le schéma + les migrations idempotentes à
        # chaque démarrage du serveur (voir db.py) — doit rester sans danger
        # à répéter, y compris après l'ajout de la colonne role.
        db.init_db()
        db.init_db()

    def test_nouveau_compte_recoit_le_role_user_par_defaut(self):
        user_id = db.create_user(
            f"role-migration-{id(self)}@gmail.com", f"rolemigration{id(self)}", "Test", "hash",
        )
        user = db.get_user_by_id(user_id)
        self.assertIn("role", user)
        self.assertEqual(user["role"], "user")

    def test_compte_invite_recoit_aussi_le_role_user_par_defaut(self):
        user_id = db.create_guest_user(f"rolemigrationguest{id(self)}")
        user = db.get_user_by_id(user_id)
        self.assertEqual(user["role"], "user")

    def test_set_user_role_ecrit_et_relit(self):
        user_id = db.create_user(
            f"role-migration-set-{id(self)}@gmail.com", f"rolemigrationset{id(self)}", "Test", "hash",
        )
        db.set_user_role(user_id, "admin")
        self.assertEqual(db.get_user_by_id(user_id)["role"], "admin")


if __name__ == "__main__":
    unittest.main()
