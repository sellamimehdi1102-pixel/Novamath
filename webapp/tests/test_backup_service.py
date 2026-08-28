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
import importlib
import os
import shutil
import sqlite3
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


class TestEcritureAtomiqueSauvegarde(BackupServiceTestCase):
    """Release Candidate : une sauvegarde tuée en cours d'écriture (SIGKILL,
    redéploiement Fly.io) ne doit jamais apparaître comme une sauvegarde
    valide — voir _backup_sqlite (écriture via .tmp + os.replace)."""

    def test_le_fichier_final_napparait_quapres_ecriture_complete(self):
        """Simule un kill en cours d'écriture (Connection.backup() échoue
        avant la fin, comme le ferait un SIGKILL en plein transfert de pages)
        -> le fichier .tmp existe, mais jamais le nom final. sqlite3.Connection
        étant un type C immuable, on ne peut pas patcher sa méthode `backup`
        directement : on intercepte sqlite3.connect() pour renvoyer, pour la
        connexion SOURCE uniquement, un petit proxy dont `.backup()` échoue,
        tout en laissant la connexion DESTINATION (le futur .tmp) bien réelle
        — exactement le point de défaillance visé (l'écriture des pages)."""
        class _FailingSource:
            def __init__(self, real_conn):
                self._real = real_conn

            def backup(self, dest):
                raise sqlite3.OperationalError("kill simulé")

            def close(self):
                self._real.close()

        real_connect = sqlite3.connect

        def fake_connect(path, *args, **kwargs):
            real_conn = real_connect(path, *args, **kwargs)
            if str(path) == str(db.DB_PATH):
                return _FailingSource(real_conn)
            return real_conn

        with patch("backup_service.sqlite3.connect", side_effect=fake_connect):
            with self.assertRaises(sqlite3.OperationalError):
                backup_service._backup_sqlite()
        self.assertEqual(backup_service.list_backups(), [])
        tmp_files = [p for p in backup_service.backup_dir().iterdir() if p.name.endswith(".tmp")]
        self.assertEqual(len(tmp_files), 1)

    def test_aucun_fichier_tmp_ne_subsiste_apres_une_ecriture_reussie(self):
        backup_service.backup_database()
        tmp_files = [p for p in backup_service.backup_dir().iterdir() if p.name.endswith(".tmp")]
        self.assertEqual(tmp_files, [])


class TestCopiePreRestoreWalAware(BackupServiceTestCase):
    """La copie de sécurité pre_restore_* utilise désormais Connection.backup()
    (comme une sauvegarde normale) au lieu de shutil.copy2 — même garantie
    d'écriture atomique, et surtout cohérente même en mode WAL sous charge."""

    def test_copie_pre_restore_est_une_base_sqlite_valide_et_complete(self):
        user_id = db.create_user("preval@gmail.com", "preval", "Test", "hash")
        backup_path = backup_service.backup_database()
        backup_service.restore_backup(backup_path.name)

        pre_restore_files = [
            p for p in backup_service.backup_dir().iterdir()
            if p.name.startswith(backup_service._PRE_RESTORE_PREFIX)
        ]
        self.assertEqual(len(pre_restore_files), 1)
        # La copie de sécurité contient bien l'état d'AVANT la restauration
        # (l'utilisateur créé juste avant le backup), preuve qu'il ne s'agit
        # pas d'un fichier tronqué/vide.
        conn = sqlite3.connect(pre_restore_files[0])
        try:
            row = conn.execute("SELECT id FROM users WHERE id = ?", (user_id,)).fetchone()
        finally:
            conn.close()
        self.assertIsNotNone(row)

    def test_aucun_fichier_tmp_ne_subsiste_apres_une_restauration(self):
        backup_path = backup_service.backup_database()
        backup_service.restore_backup(backup_path.name)
        tmp_files = [p for p in backup_service.backup_dir().iterdir() if ".tmp" in p.name]
        self.assertEqual(tmp_files, [])


class TestValidationIntegriteAvantRestauration(BackupServiceTestCase):
    """Une sauvegarde corrompue (tronquée par un kill, avant ce correctif, ou
    altérée) ne doit jamais commencer à écraser la base de production."""

    def test_sauvegarde_corrompue_est_refusee_avant_toute_ecriture(self):
        corrupted = self._touch_backup(datetime.now(timezone.utc))
        corrupted.write_bytes(b"ceci n'est pas une base SQLite valide")

        user_id = db.create_user("integrite@gmail.com", "integrite", "Test", "hash")

        with self.assertRaises(backup_service.BackupCorrupted):
            backup_service.restore_backup(corrupted.name)

        # La base de production n'a jamais été touchée : l'utilisateur créé
        # juste avant la tentative de restauration est toujours présent.
        self.assertIsNotNone(db.get_user_by_id(user_id))

    def test_sauvegarde_corrompue_najamais_ecrase_le_fichier_final(self):
        corrupted = self._touch_backup(datetime.now(timezone.utc))
        corrupted.write_bytes(b"contenu invalide")
        with self.assertRaises(backup_service.BackupCorrupted):
            backup_service.restore_backup(corrupted.name)
        self.assertTrue(Path(db.DB_PATH).exists())
        # La base reste une base SQLite saine.
        conn = sqlite3.connect(db.DB_PATH)
        try:
            result = conn.execute("PRAGMA integrity_check").fetchone()
        finally:
            conn.close()
        self.assertEqual(result[0], "ok")

    def test_sauvegarde_valide_passe_la_validation_et_restaure_normalement(self):
        backup_path = backup_service.backup_database()
        backup_service.restore_backup(backup_path.name)  # ne doit lever aucune exception


class TestSuppressionCopiesPreRestore(BackupServiceTestCase):
    """Avant ce correctif, delete_backup() levait BackupNotFound pour tout
    fichier pre_restore_*, même en connaissant son nom exact — aucune
    suppression manuelle possible via ce point d'entrée."""

    def test_delete_backup_accepte_un_nom_pre_restore_valide(self):
        copy_path = self._touch_backup(
            datetime.now(timezone.utc), prefix=backup_service._PRE_RESTORE_PREFIX,
        )
        backup_service.delete_backup(copy_path.name)
        self.assertFalse(copy_path.exists())

    def test_delete_backup_leve_backup_not_found_pour_un_pre_restore_inexistant(self):
        with self.assertRaises(backup_service.BackupNotFound):
            backup_service.delete_backup("pre_restore_20200101_000000_000000.sqlite3")

    def test_apply_retention_purge_les_copies_pre_restore_expirees(self):
        config.BACKUP_RETENTION_DAYS = 30
        very_old = datetime.now(timezone.utc) - timedelta(days=45)
        recent = datetime.now(timezone.utc) - timedelta(days=1)
        old_copy = self._touch_backup(very_old, prefix=backup_service._PRE_RESTORE_PREFIX)
        recent_copy = self._touch_backup(recent, prefix=backup_service._PRE_RESTORE_PREFIX)

        backup_service._apply_retention()

        self.assertFalse(old_copy.exists())
        self.assertTrue(recent_copy.exists())

    def test_list_pre_restore_copies_les_expose_sans_les_melanger_a_list_backups(self):
        copy_path = self._touch_backup(
            datetime.now(timezone.utc), prefix=backup_service._PRE_RESTORE_PREFIX,
        )
        copies = backup_service.list_pre_restore_copies()
        self.assertEqual([c["filename"] for c in copies], [copy_path.name])
        self.assertEqual(backup_service.list_backups(), [])


class TestPlancherRetentionDays(unittest.TestCase):
    """BACKUP_RETENTION_DAYS=0 (ou négatif, erreur de configuration
    plausible via `fly secrets set`) ne doit plus jamais purger TOUTE
    sauvegarde, y compris celle qui vient d'être créée dans le même appel
    (voir backup_service._apply_retention, exécutée juste après
    backup_database()) — un plancher à 1 jour est appliqué au chargement de
    config.py."""

    def setUp(self):
        self._env_backup = os.environ.get("BACKUP_RETENTION_DAYS")

    def tearDown(self):
        if self._env_backup is None:
            os.environ.pop("BACKUP_RETENTION_DAYS", None)
        else:
            os.environ["BACKUP_RETENTION_DAYS"] = self._env_backup
        importlib.reload(config)

    def test_zero_est_remonte_a_un_jour(self):
        os.environ["BACKUP_RETENTION_DAYS"] = "0"
        importlib.reload(config)
        self.assertEqual(config.BACKUP_RETENTION_DAYS, 1)

    def test_valeur_negative_est_remontee_a_un_jour(self):
        os.environ["BACKUP_RETENTION_DAYS"] = "-5"
        importlib.reload(config)
        self.assertEqual(config.BACKUP_RETENTION_DAYS, 1)

    def test_valeur_positive_normale_est_preservee(self):
        os.environ["BACKUP_RETENTION_DAYS"] = "7"
        importlib.reload(config)
        self.assertEqual(config.BACKUP_RETENTION_DAYS, 7)


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
