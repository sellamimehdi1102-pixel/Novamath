"""
Suite de backup_service.py — backup_database()/list_backups()/restore_backup(),
rotation (BACKUP_RETENTION_DAYS + filet MAX_BACKUPS), compatibilité SQLite
(exercée pour de vrai) et PostgreSQL (exercée via subprocess mocké — voir
_detect_backend, aucune connexion Postgres réelle n'existe dans ce projet).

Base SQLite ET dossier de sauvegarde isolés dans un répertoire temporaire
(db.DATA_DIR/db.DB_PATH et config.BACKUP_DIRECTORY monkeypatchés), même
pattern que tests/test_quota_service.py : aucune interférence avec
data/novamath.db ni backups/.
"""
import shutil
import subprocess
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import backup_service
import config
import db


class BackupServiceTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp_dir = tempfile.mkdtemp()
        self._data_dir_backup = db.DATA_DIR
        self._db_path_backup = db.DB_PATH
        self._backup_directory_backup = config.BACKUP_DIRECTORY
        self._retention_backup = config.BACKUP_RETENTION_DAYS

        db.DATA_DIR = Path(self._tmp_dir) / "data"
        db.DB_PATH = db.DATA_DIR / "novamath.db"
        config.BACKUP_DIRECTORY = str(Path(self._tmp_dir) / "backups")
        db.init_db()

    def tearDown(self):
        db.DATA_DIR = self._data_dir_backup
        db.DB_PATH = self._db_path_backup
        config.BACKUP_DIRECTORY = self._backup_directory_backup
        config.BACKUP_RETENTION_DAYS = self._retention_backup
        shutil.rmtree(self._tmp_dir, ignore_errors=True)

    def _touch_backup(self, when, prefix=backup_service._FILENAME_PREFIX, suffix=backup_service._SQLITE_SUFFIX):
        """`when` : soit une date au format "YYYYMMDD" (convertie en
        timestamp valide, minuit UTC ce jour-là), soit un datetime déjà
        construit — toujours reformaté avec le format réellement utilisé par
        backup_service (_TIMESTAMP_FORMAT), pour que _parse_timestamp()
        reconnaisse le fichier comme n'importe quelle vraie sauvegarde."""
        if isinstance(when, str):
            when = datetime.strptime(when, "%Y%m%d").replace(tzinfo=timezone.utc)
        stamp = when.strftime(backup_service._TIMESTAMP_FORMAT)
        path = backup_service.backup_dir() / f"{prefix}{stamp}{suffix}"
        path.write_text("contenu factice")
        return path


class TestBackupDir(BackupServiceTestCase):
    def test_cree_automatiquement_le_dossier_absent(self):
        target = Path(config.BACKUP_DIRECTORY)
        self.assertFalse(target.exists())
        result = backup_service.backup_dir()
        self.assertTrue(result.is_dir())

    def test_idempotent_si_deja_present(self):
        backup_service.backup_dir()
        result = backup_service.backup_dir()  # ne doit pas lever
        self.assertTrue(result.is_dir())


class TestDetectBackend(BackupServiceTestCase):
    def test_sqlite_par_defaut(self):
        with patch.dict("os.environ", {}, clear=False):
            import os
            os.environ.pop("DATABASE_URL", None)
            self.assertEqual(backup_service._detect_backend(), "sqlite")

    def test_postgresql_si_database_url_postgres(self):
        with patch.dict("os.environ", {"DATABASE_URL": "postgresql://user:pw@host/db"}):
            self.assertEqual(backup_service._detect_backend(), "postgresql")

    def test_postgresql_si_schema_postgres_court(self):
        with patch.dict("os.environ", {"DATABASE_URL": "postgres://user:pw@host/db"}):
            self.assertEqual(backup_service._detect_backend(), "postgresql")


class TestBackupDatabaseSqlite(BackupServiceTestCase):
    def test_cree_un_fichier_horodate(self):
        path = backup_service.backup_database()
        self.assertTrue(path.exists())
        self.assertTrue(path.name.startswith(backup_service._FILENAME_PREFIX))
        self.assertTrue(path.name.endswith(backup_service._SQLITE_SUFFIX))

    def test_fichier_non_vide(self):
        path = backup_service.backup_database()
        self.assertGreater(path.stat().st_size, 0)

    def test_contenu_restaurable_round_trip(self):
        user_id = db.create_user("roundtrip@gmail.com", "roundtrip", "Test", "hash")
        backup_path = backup_service.backup_database()

        # "Perte de données" simulée : le compte disparaît de la base réelle.
        conn = db.get_connection()
        try:
            conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
            conn.commit()
        finally:
            conn.close()
        self.assertIsNone(db.get_user_by_id(user_id))

        backup_service.restore_backup(backup_path.name)
        restored = db.get_user_by_id(user_id)
        self.assertIsNotNone(restored)
        self.assertEqual(restored["email"], "roundtrip@gmail.com")


class TestListBackups(BackupServiceTestCase):
    def test_vide_sur_dossier_neuf(self):
        self.assertEqual(backup_service.list_backups(), [])

    def test_liste_les_sauvegardes_creees(self):
        backup_service.backup_database()
        backup_service.backup_database()
        self.assertEqual(len(backup_service.list_backups()), 2)

    def test_tri_du_plus_recent_au_plus_ancien(self):
        old = self._touch_backup("20200101")
        new = self._touch_backup("20250101")
        result = backup_service.list_backups()
        self.assertEqual([b["filename"] for b in result], [new.name, old.name])

    def test_ignore_les_fichiers_etrangers_au_dossier(self):
        (backup_service.backup_dir() / ".gitkeep").write_text("")
        (backup_service.backup_dir() / "notes.txt").write_text("pas une sauvegarde")
        self.assertEqual(backup_service.list_backups(), [])

    def test_ignore_les_copies_de_securite_pre_restore(self):
        self._touch_backup("20240101", prefix=backup_service._PRE_RESTORE_PREFIX)
        self.assertEqual(backup_service.list_backups(), [])

    def test_chaque_entree_a_les_champs_attendus(self):
        backup_service.backup_database()
        entry = backup_service.list_backups()[0]
        self.assertEqual(set(entry), {"filename", "path", "size_bytes", "created_at"})


class TestRestoreBackup(BackupServiceTestCase):
    def test_leve_backup_not_found_si_absent(self):
        with self.assertRaises(backup_service.BackupNotFound):
            backup_service.restore_backup("novamath_backup_20200101_000000.sqlite3")

    def test_leve_backup_not_found_pour_un_nom_hors_convention(self):
        """Aucun fichier arbitraire du disque ne doit pouvoir être "restauré"
        — seuls les fichiers au format de nom attendu sont acceptés, même
        s'ils existent physiquement dans le dossier de sauvegarde."""
        (backup_service.backup_dir() / "etc_passwd").write_text("contenu arbitraire")
        with self.assertRaises(backup_service.BackupNotFound):
            backup_service.restore_backup("etc_passwd")

    def test_cree_une_copie_de_securite_avant_ecrasement(self):
        backup_path = backup_service.backup_database()
        before = len([p for p in backup_service.backup_dir().iterdir()])
        backup_service.restore_backup(backup_path.name)
        after_files = list(backup_service.backup_dir().iterdir())
        pre_restore_files = [p for p in after_files if p.name.startswith(backup_service._PRE_RESTORE_PREFIX)]
        self.assertEqual(len(pre_restore_files), 1)


class TestRotationParDate(BackupServiceTestCase):
    def test_supprime_les_sauvegardes_plus_vieilles_que_la_retention(self):
        config.BACKUP_RETENTION_DAYS = 30
        very_old = (datetime.now(timezone.utc) - timedelta(days=45))
        recent = (datetime.now(timezone.utc) - timedelta(days=1))
        old_path = self._touch_backup(very_old)
        recent_path = self._touch_backup(recent)

        backup_service._apply_retention()

        self.assertFalse(old_path.exists())
        self.assertTrue(recent_path.exists())

    def test_conserve_tout_si_rien_nest_expire(self):
        config.BACKUP_RETENTION_DAYS = 30
        for days_ago in (1, 2, 3):
            ts = (datetime.now(timezone.utc) - timedelta(days=days_ago))
            self._touch_backup(ts)
        backup_service._apply_retention()
        self.assertEqual(len(backup_service.list_backups()), 3)

    def test_retention_configurable_plus_courte(self):
        config.BACKUP_RETENTION_DAYS = 2
        ts_3_days = (datetime.now(timezone.utc) - timedelta(days=3))
        path = self._touch_backup(ts_3_days)
        backup_service._apply_retention()
        self.assertFalse(path.exists())


class TestRotationParNombre(BackupServiceTestCase):
    def test_ne_conserve_jamais_plus_de_max_backups(self):
        config.BACKUP_RETENTION_DAYS = 365  # rien n'expire par date ici
        now = datetime.now(timezone.utc)
        for i in range(35):
            ts = (now - timedelta(minutes=i))
            self._touch_backup(ts)
        backup_service._apply_retention()
        self.assertEqual(len(backup_service.list_backups()), backup_service.MAX_BACKUPS)

    def test_conserve_les_plus_recentes_en_cas_de_depassement(self):
        config.BACKUP_RETENTION_DAYS = 365
        now = datetime.now(timezone.utc)
        newest_ts = now
        newest_path = self._touch_backup(newest_ts)
        for i in range(1, 35):
            ts = (now - timedelta(minutes=i))
            self._touch_backup(ts)
        backup_service._apply_retention()
        remaining = {b["filename"] for b in backup_service.list_backups()}
        self.assertIn(newest_path.name, remaining)

    def test_backup_database_declenche_la_rotation_automatiquement(self):
        config.BACKUP_RETENTION_DAYS = 365
        now = datetime.now(timezone.utc)
        for i in range(35):
            ts = (now - timedelta(minutes=i + 1))
            self._touch_backup(ts)
        backup_service.backup_database()  # +1 sauvegarde -> déclenche _apply_retention()
        self.assertLessEqual(len(backup_service.list_backups()), backup_service.MAX_BACKUPS)


class TestPermissions(BackupServiceTestCase):
    def test_echec_de_suppression_ne_fait_pas_planter_la_rotation(self):
        config.BACKUP_RETENTION_DAYS = 1
        very_old = (datetime.now(timezone.utc) - timedelta(days=10))
        self._touch_backup(very_old)
        with patch("pathlib.Path.unlink", side_effect=OSError("permission refusée")):
            backup_service._apply_retention()  # ne doit lever aucune exception

    def test_parse_timestamp_renvoie_none_pour_un_nom_malforme(self):
        self.assertIsNone(backup_service._parse_timestamp("pas_une_sauvegarde.txt"))
        self.assertIsNone(backup_service._parse_timestamp("novamath_backup_pasunedate.sqlite3"))


class TestCompatibilitePostgresql(BackupServiceTestCase):
    def setUp(self):
        super().setUp()
        self._database_url_patch = patch.dict("os.environ", {"DATABASE_URL": "postgresql://u:p@host/db"})
        self._database_url_patch.start()

    def tearDown(self):
        self._database_url_patch.stop()
        super().tearDown()

    def test_backup_database_appelle_pg_dump(self):
        with patch("backup_service.subprocess.run") as mock_run:
            mock_run.return_value = None
            path = backup_service.backup_database()
        self.assertTrue(path.name.endswith(backup_service._POSTGRES_SUFFIX))
        called_cmd = mock_run.call_args.args[0]
        self.assertEqual(called_cmd[0], "pg_dump")

    def test_backup_database_pg_dump_echoue_leve_runtime_error(self):
        with patch(
            "backup_service.subprocess.run",
            side_effect=subprocess.CalledProcessError(1, ["pg_dump"]),
        ):
            with self.assertRaises(RuntimeError):
                backup_service.backup_database()

    def test_backup_database_pg_dump_echoue_nettoie_le_fichier_partiel(self):
        with patch(
            "backup_service.subprocess.run",
            side_effect=subprocess.CalledProcessError(1, ["pg_dump"]),
        ):
            with self.assertRaises(RuntimeError):
                backup_service.backup_database()
        self.assertEqual(backup_service.list_backups(), [])

    def test_restore_backup_appelle_psql(self):
        source = self._touch_backup("20240101", suffix=backup_service._POSTGRES_SUFFIX)
        with patch("backup_service.subprocess.run") as mock_run:
            mock_run.return_value = None
            backup_service.restore_backup(source.name)
        called_cmd = mock_run.call_args.args[0]
        self.assertEqual(called_cmd[0], "psql")

    def test_restore_backup_psql_echoue_leve_runtime_error(self):
        source = self._touch_backup("20240101", suffix=backup_service._POSTGRES_SUFFIX)
        with patch(
            "backup_service.subprocess.run",
            side_effect=subprocess.CalledProcessError(1, ["psql"]),
        ):
            with self.assertRaises(RuntimeError):
                backup_service.restore_backup(source.name)


if __name__ == "__main__":
    unittest.main()
