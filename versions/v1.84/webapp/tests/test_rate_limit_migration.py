"""
Suite de migration/schéma pour rate_limit_events (webapp/rate_limit_service.py)
— table entièrement nouvelle (pas un ALTER TABLE sur une table existante),
créée de façon idempotente via CREATE TABLE/INDEX IF NOT EXISTS (voir
db.py::SCHEMA). Complète tests/test_rate_limit_service.py.
"""
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path

import db


class TestMigrationRateLimitEvents(unittest.TestCase):
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

    def test_reexecuter_init_db_est_sans_effet(self):
        db.init_db()
        db.init_db()
        db.init_db()

    def test_table_rate_limit_events_existe(self):
        db.init_db()
        conn = db.get_connection()
        try:
            row = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='rate_limit_events'"
            ).fetchone()
        finally:
            conn.close()
        self.assertIsNotNone(row)

    def test_colonnes_attendues_presentes(self):
        db.init_db()
        conn = db.get_connection()
        try:
            cols = {row["name"] for row in conn.execute("PRAGMA table_info(rate_limit_events)")}
        finally:
            conn.close()
        self.assertEqual(cols, {"id", "key", "endpoint", "window_start", "count"})

    def test_id_est_la_cle_primaire(self):
        db.init_db()
        conn = db.get_connection()
        try:
            pk_cols = [row["name"] for row in conn.execute("PRAGMA table_info(rate_limit_events)") if row["pk"]]
        finally:
            conn.close()
        self.assertEqual(pk_cols, ["id"])

    def test_index_lookup_existe_et_couvre_key_endpoint_window_start(self):
        db.init_db()
        conn = db.get_connection()
        try:
            row = conn.execute(
                "SELECT sql FROM sqlite_master WHERE type='index' AND name='idx_rate_limit_events_lookup'"
            ).fetchone()
        finally:
            conn.close()
        self.assertIsNotNone(row)
        self.assertIn("key", row["sql"])
        self.assertIn("endpoint", row["sql"])
        self.assertIn("window_start", row["sql"])

    def test_index_lookup_est_unique(self):
        db.init_db()
        conn = db.get_connection()
        try:
            indexes = conn.execute("PRAGMA index_list(rate_limit_events)").fetchall()
            lookup = next(i for i in indexes if i["name"] == "idx_rate_limit_events_lookup")
        finally:
            conn.close()
        self.assertEqual(lookup["unique"], 1)

    def test_index_lookup_unique_rejette_un_doublon_exact(self):
        db.init_db()
        conn = db.get_connection()
        try:
            conn.execute(
                "INSERT INTO rate_limit_events (key, endpoint, window_start, count) VALUES ('k', 'ep', 100, 1)"
            )
            conn.commit()
            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute(
                    "INSERT INTO rate_limit_events (key, endpoint, window_start, count) VALUES ('k', 'ep', 100, 1)"
                )
        finally:
            conn.close()

    def test_index_window_start_existe(self):
        db.init_db()
        conn = db.get_connection()
        try:
            row = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_rate_limit_events_window_start'"
            ).fetchone()
        finally:
            conn.close()
        self.assertIsNotNone(row)

    def test_table_vide_apres_init_sur_base_neuve(self):
        db.init_db()
        conn = db.get_connection()
        try:
            n = conn.execute("SELECT COUNT(*) AS n FROM rate_limit_events").fetchone()["n"]
        finally:
            conn.close()
        self.assertEqual(n, 0)

    def test_count_par_defaut_a_zero(self):
        db.init_db()
        conn = db.get_connection()
        try:
            conn.execute("INSERT INTO rate_limit_events (key, endpoint, window_start) VALUES ('k', 'ep', 1)")
            conn.commit()
            row = conn.execute("SELECT count FROM rate_limit_events WHERE key='k'").fetchone()
        finally:
            conn.close()
        self.assertEqual(row["count"], 0)


if __name__ == "__main__":
    unittest.main()
