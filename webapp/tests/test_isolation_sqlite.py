"""
Validation minimale du chantier "isolation SQLite" (2026-10-17) :
démontre que conftest.py a bien redirigé db.py/auth.py/server.py vers un
répertoire temporaire, que le schéma y est initialisé, et que les vrais
chemins ne sont jamais utilisés par ces modules pendant pytest.
"""
import sqlite3
import unittest
from pathlib import Path

import auth
import config
import db
import server


class TestCheminsRedirigesVersLeRepertoireTemporaire(unittest.TestCase):
    def test_db_path_est_hors_du_projet_reel(self):
        real_db = (Path(__file__).resolve().parent.parent.parent / "data" / "novamath.db")
        self.assertNotEqual(Path(db.DB_PATH).resolve(), real_db.resolve())
        self.assertIn("mathadap_pytest_", str(db.DB_PATH))

    def test_auth_dirs_pointent_vers_le_meme_repertoire_temporaire_que_db(self):
        self.assertEqual(Path(auth.DATA_DIR).resolve(), Path(db.DATA_DIR).resolve())
        for p in (auth.USER_STATS_DIR, auth.USER_SETTINGS_DIR, auth.USER_COURSE_DIR):
            self.assertTrue(str(p).startswith(str(db.DATA_DIR)))

    def test_server_data_dir_redirige(self):
        self.assertEqual(Path(server.DATA_DIR).resolve(), Path(db.DATA_DIR).resolve())

    def test_database_url_neutralisee(self):
        self.assertIsNone(config.DATABASE_URL)


class TestSchemaInitialiseDansLeRepertoireTemporaire(unittest.TestCase):
    def test_base_temporaire_existe_et_contient_les_tables_attendues(self):
        self.assertTrue(Path(db.DB_PATH).exists())
        conn = db.get_connection()
        try:
            tables = {
                row[0]
                for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            }
        finally:
            conn.close()
        for expected in ("users", "sessions", "conversations", "chatbot_messages"):
            self.assertIn(expected, tables)

    def test_ecrire_un_utilisateur_de_test_ne_touche_pas_la_vraie_base(self):
        real_db = Path(__file__).resolve().parent.parent.parent / "data" / "novamath.db"
        size_before = real_db.stat().st_size

        client = server.app.test_client()
        resp = client.post(
            "/api/auth/register",
            json={
                "email": "isolation_test@gmail.com", "username": "isolation_test",
                "pseudo": "Isolation Test", "birth_date": "2000-01-01",
                "password": "TestPassword123!", "confirm_password": "TestPassword123!",
                "accept_terms": True, "accept_privacy": True,
            },
        )
        self.assertIn(resp.status_code, (200, 201), resp.get_json())

        conn = db.get_connection()
        try:
            row = conn.execute(
                "SELECT id FROM users WHERE email = ?", ("isolation_test@gmail.com",)
            ).fetchone()
        finally:
            conn.close()
        self.assertIsNotNone(row, "L'utilisateur de test doit exister dans la base TEMPORAIRE")

        self.assertEqual(real_db.stat().st_size, size_before)
        real_conn = sqlite3.connect(":memory:")  # neutre, juste pour garder l'import utilisé
        real_conn.close()


class TestGardeFouSqliteConnect(unittest.TestCase):
    def test_connexion_vers_un_chemin_hors_repertoire_temporaire_est_refusee(self):
        real_db = Path(__file__).resolve().parent.parent.parent / "data" / "novamath.db"
        with self.assertRaises(RuntimeError) as ctx:
            sqlite3.connect(str(real_db))
        self.assertIn("ISOLATION PYTEST", str(ctx.exception))

    def test_connexion_en_memoire_reste_autorisee(self):
        conn = sqlite3.connect(":memory:")
        conn.close()


if __name__ == "__main__":
    unittest.main()
