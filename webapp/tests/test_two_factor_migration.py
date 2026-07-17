"""
Suite de migration/schéma pour la 2FA (SEC-03) — colonnes ajoutées à `users`
(ALTER TABLE idempotent) et nouvelles tables two_factor_challenges/
two_factor_recovery_codes (CREATE TABLE IF NOT EXISTS). Complète
tests/test_two_factor_service.py.
"""
import shutil
import tempfile
import unittest
from pathlib import Path

import db


class TwoFactorMigrationTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp_dir = tempfile.mkdtemp()
        self._data_dir_backup = db.DATA_DIR
        self._db_path_backup = db.DB_PATH
        db.DATA_DIR = Path(self._tmp_dir)
        db.DB_PATH = db.DATA_DIR / "novamath.db"

    def tearDown(self):
        db.DATA_DIR = self._data_dir_backup
        db.DB_PATH = self._db_path_backup
        shutil.rmtree(self._tmp_dir, ignore_errors=True)


class TestColonnesUsers(TwoFactorMigrationTestCase):
    def test_reexecuter_init_db_est_sans_effet(self):
        db.init_db()
        db.init_db()
        db.init_db()

    def test_colonnes_2fa_presentes_sur_users(self):
        db.init_db()
        conn = db.get_connection()
        try:
            cols = {row["name"] for row in conn.execute("PRAGMA table_info(users)")}
        finally:
            conn.close()
        self.assertTrue({"two_factor_enabled", "two_factor_secret", "two_factor_enabled_at", "two_factor_last_counter"}.issubset(cols))

    def test_two_factor_enabled_defaut_zero_pour_nouveau_compte(self):
        db.init_db()
        user_id = db.create_user("mig2fa@gmail.com", "mig2fa", "Test", "hash")
        user = db.get_user_by_id(user_id)
        self.assertEqual(user["two_factor_enabled"], 0)
        self.assertIsNone(user["two_factor_secret"])
        self.assertIsNone(user["two_factor_enabled_at"])
        self.assertIsNone(user["two_factor_last_counter"])

    def test_compte_existant_conserve_ses_donnees_apres_migration(self):
        """Simule une base créée AVANT l'ajout des colonnes 2FA (schéma de
        base seul, sans les migrations) : un compte déjà présent ne doit
        perdre aucune donnée une fois les colonnes 2FA ajoutées."""
        conn = db.get_connection()
        try:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE NOT NULL,
                    username TEXT UNIQUE NOT NULL,
                    pseudo TEXT NOT NULL,
                    password_hash TEXT,
                    avatar TEXT,
                    auth_provider TEXT NOT NULL DEFAULT 'local',
                    created_at TEXT NOT NULL,
                    last_login_at TEXT,
                    xp INTEGER NOT NULL DEFAULT 0,
                    level INTEGER NOT NULL DEFAULT 1,
                    accuracy REAL NOT NULL DEFAULT 0,
                    progression REAL NOT NULL DEFAULT 0,
                    total_time_s INTEGER NOT NULL DEFAULT 0
                );
                """
            )
            conn.execute(
                "INSERT INTO users (email, username, pseudo, auth_provider, created_at, xp) "
                "VALUES ('preexistant@gmail.com', 'preexistant', 'Ancien', 'local', '2020-01-01T00:00:00', 42)"
            )
            conn.commit()
        finally:
            conn.close()

        db.init_db()  # applique les migrations, comme au démarrage réel du serveur

        user = db.get_user_by_email("preexistant@gmail.com")
        self.assertEqual(user["xp"], 42)
        self.assertEqual(user["pseudo"], "Ancien")
        self.assertEqual(user["two_factor_enabled"], 0)
        self.assertIsNone(user["two_factor_secret"])


class TestTableChallenges(TwoFactorMigrationTestCase):
    def test_table_existe(self):
        db.init_db()
        conn = db.get_connection()
        try:
            row = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='two_factor_challenges'"
            ).fetchone()
        finally:
            conn.close()
        self.assertIsNotNone(row)

    def test_colonnes_attendues(self):
        db.init_db()
        conn = db.get_connection()
        try:
            cols = {row["name"] for row in conn.execute("PRAGMA table_info(two_factor_challenges)")}
        finally:
            conn.close()
        self.assertEqual(cols, {"token", "user_id", "remember", "created_at", "expires_at"})

    def test_token_est_cle_primaire(self):
        db.init_db()
        conn = db.get_connection()
        try:
            pk = [row["name"] for row in conn.execute("PRAGMA table_info(two_factor_challenges)") if row["pk"]]
        finally:
            conn.close()
        self.assertEqual(pk, ["token"])

    def test_cascade_suppression_utilisateur(self):
        db.init_db()
        user_id = db.create_user("cascade2fa@gmail.com", "cascade2fa", "Test", "hash")
        db.create_two_factor_challenge(user_id, remember=False)
        db.delete_user(user_id)
        conn = db.get_connection()
        try:
            n = conn.execute("SELECT COUNT(*) AS n FROM two_factor_challenges WHERE user_id = ?", (user_id,)).fetchone()["n"]
        finally:
            conn.close()
        self.assertEqual(n, 0)


class TestTableRecoveryCodes(TwoFactorMigrationTestCase):
    def test_table_existe(self):
        db.init_db()
        conn = db.get_connection()
        try:
            row = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='two_factor_recovery_codes'"
            ).fetchone()
        finally:
            conn.close()
        self.assertIsNotNone(row)

    def test_colonnes_attendues(self):
        db.init_db()
        conn = db.get_connection()
        try:
            cols = {row["name"] for row in conn.execute("PRAGMA table_info(two_factor_recovery_codes)")}
        finally:
            conn.close()
        self.assertEqual(cols, {"id", "user_id", "code_hash", "created_at"})

    def test_index_user_id_existe(self):
        db.init_db()
        conn = db.get_connection()
        try:
            row = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_two_factor_recovery_codes_user'"
            ).fetchone()
        finally:
            conn.close()
        self.assertIsNotNone(row)

    def test_cascade_suppression_utilisateur(self):
        db.init_db()
        user_id = db.create_user("cascade2fb@gmail.com", "cascade2fb", "Test", "hash")
        db.replace_recovery_codes(user_id, ["hash1", "hash2"])
        db.delete_user(user_id)
        self.assertEqual(db.count_recovery_codes(user_id), 0)


class TestAccesseursDb(TwoFactorMigrationTestCase):
    def setUp(self):
        super().setUp()
        db.init_db()
        self.user_id = db.create_user("accessdb2fa@gmail.com", "accessdb2fa", "Test", "hash")

    def test_set_and_read_two_factor_secret(self):
        db.set_two_factor_secret(self.user_id, "cipher-text")
        self.assertEqual(db.get_user_by_id(self.user_id)["two_factor_secret"], "cipher-text")

    def test_enable_two_factor_fixe_enabled_et_enabled_at(self):
        db.enable_two_factor(self.user_id)
        user = db.get_user_by_id(self.user_id)
        self.assertEqual(user["two_factor_enabled"], 1)
        self.assertIsNotNone(user["two_factor_enabled_at"])

    def test_disable_two_factor_efface_tout(self):
        db.set_two_factor_secret(self.user_id, "cipher-text")
        db.enable_two_factor(self.user_id)
        db.set_two_factor_last_counter(self.user_id, 12345)
        db.disable_two_factor(self.user_id)
        user = db.get_user_by_id(self.user_id)
        self.assertEqual(user["two_factor_enabled"], 0)
        self.assertIsNone(user["two_factor_secret"])
        self.assertIsNone(user["two_factor_enabled_at"])
        self.assertIsNone(user["two_factor_last_counter"])

    def test_set_two_factor_secret_reinitialise_le_compteur_de_rejeu(self):
        db.set_two_factor_last_counter(self.user_id, 999)
        db.set_two_factor_secret(self.user_id, "nouveau-secret-chiffre")
        self.assertIsNone(db.get_user_by_id(self.user_id)["two_factor_last_counter"])

    def test_replace_recovery_codes_remplace_integralement(self):
        db.replace_recovery_codes(self.user_id, ["h1", "h2", "h3"])
        self.assertEqual(db.count_recovery_codes(self.user_id), 3)
        db.replace_recovery_codes(self.user_id, ["h4"])
        self.assertEqual(db.count_recovery_codes(self.user_id), 1)
        hashes = {c["code_hash"] for c in db.get_recovery_codes(self.user_id)}
        self.assertEqual(hashes, {"h4"})

    def test_consume_recovery_code_supprime_et_renvoie_true(self):
        db.replace_recovery_codes(self.user_id, ["h1", "h2"])
        self.assertTrue(db.consume_recovery_code(self.user_id, "h1"))
        self.assertEqual(db.count_recovery_codes(self.user_id), 1)

    def test_consume_recovery_code_renvoie_false_si_absent(self):
        db.replace_recovery_codes(self.user_id, ["h1"])
        self.assertFalse(db.consume_recovery_code(self.user_id, "h-inconnu"))
        self.assertEqual(db.count_recovery_codes(self.user_id), 1)

    def test_consume_recovery_code_ne_supprime_pas_deux_fois(self):
        db.replace_recovery_codes(self.user_id, ["h1"])
        self.assertTrue(db.consume_recovery_code(self.user_id, "h1"))
        self.assertFalse(db.consume_recovery_code(self.user_id, "h1"))

    def test_create_get_delete_challenge(self):
        token = db.create_two_factor_challenge(self.user_id, remember=True)
        self.assertIsNotNone(db.get_two_factor_challenge(token))
        db.delete_two_factor_challenge(token)
        self.assertIsNone(db.get_two_factor_challenge(token))

    def test_get_two_factor_challenge_expire_renvoie_none(self):
        token = db.create_two_factor_challenge(self.user_id, remember=False, minutes=-1)
        self.assertIsNone(db.get_two_factor_challenge(token))

    def test_count_recent_two_factor_failures_zero_sans_evenement(self):
        self.assertEqual(db.count_recent_two_factor_failures(self.user_id), 0)

    def test_count_recent_two_factor_failures_compte_les_bons_evenements(self):
        db.log_security_event("two_factor_verify_failed", user_id=self.user_id)
        db.log_security_event("two_factor_recovery_failed", user_id=self.user_id)
        db.log_security_event("two_factor_enabled", user_id=self.user_id)  # ne se termine pas par _failed
        self.assertEqual(db.count_recent_two_factor_failures(self.user_id), 2)


if __name__ == "__main__":
    unittest.main()
