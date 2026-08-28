"""
Suite de backup_scheduler.py — Release Candidate, correctif priorité 1 :
"aucune sauvegarde automatique n'existait avant" (voir audit RC). Vérifie :
- le déclenchement au bon moment (heure programmée atteinte, pas avant) ;
- l'absence de double déclenchement le même jour, y compris sous plusieurs
  workers concurrents (db.claim_daily_backup) ;
- que le bouton "Créer une sauvegarde" (settings_service.create_backup)
  n'est jamais modifié ni contourné par ce module (aucune régression) ;
- la désactivation via BACKUP_AUTO_ENABLED.

Base SQLite isolée dans un répertoire temporaire, même pattern que
test_backup_service.py — jamais data/novamath.db.
"""
import shutil
import tempfile
import threading
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import backup_scheduler
import config
import db


class BackupSchedulerTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp_dir = tempfile.mkdtemp()
        self._data_dir_backup = db.DATA_DIR
        self._db_path_backup = db.DB_PATH
        self._backup_directory_backup = config.BACKUP_DIRECTORY
        self._auto_enabled_backup = config.BACKUP_AUTO_ENABLED
        self._auto_hour_backup = config.BACKUP_AUTO_HOUR_UTC

        db.DATA_DIR = Path(self._tmp_dir) / "data"
        db.DB_PATH = db.DATA_DIR / "novamath.db"
        config.BACKUP_DIRECTORY = str(Path(self._tmp_dir) / "backups")
        config.BACKUP_AUTO_ENABLED = True
        config.BACKUP_AUTO_HOUR_UTC = 3
        db.init_db()

    def tearDown(self):
        db.DATA_DIR = self._data_dir_backup
        db.DB_PATH = self._db_path_backup
        config.BACKUP_DIRECTORY = self._backup_directory_backup
        config.BACKUP_AUTO_ENABLED = self._auto_enabled_backup
        config.BACKUP_AUTO_HOUR_UTC = self._auto_hour_backup
        shutil.rmtree(self._tmp_dir, ignore_errors=True)


class TestDeclenchementHoraire(BackupSchedulerTestCase):
    def test_avant_lheure_programmee_ne_declenche_rien(self):
        now = datetime(2026, 1, 1, 1, 0, tzinfo=timezone.utc)  # 1h, avant 3h
        with patch("backup_scheduler.settings_service") as mock_settings:
            triggered = backup_scheduler.maybe_run_daily_backup(now=now)
        self.assertFalse(triggered)
        mock_settings.create_backup.assert_not_called()

    def test_a_lheure_programmee_declenche_une_sauvegarde_reelle(self):
        now = datetime(2026, 1, 1, 3, 0, tzinfo=timezone.utc)
        triggered = backup_scheduler.maybe_run_daily_backup(now=now)
        self.assertTrue(triggered)
        self.assertEqual(len(__import__("backup_service").list_backups()), 1)

    def test_apres_lheure_programmee_declenche_aussi(self):
        now = datetime(2026, 1, 1, 23, 0, tzinfo=timezone.utc)
        triggered = backup_scheduler.maybe_run_daily_backup(now=now)
        self.assertTrue(triggered)


class TestPasDeDoublon(BackupSchedulerTestCase):
    def test_deuxieme_appel_le_meme_jour_ne_redeclenche_pas(self):
        now = datetime(2026, 1, 1, 3, 0, tzinfo=timezone.utc)
        first = backup_scheduler.maybe_run_daily_backup(now=now)
        second = backup_scheduler.maybe_run_daily_backup(now=now.replace(hour=10))
        self.assertTrue(first)
        self.assertFalse(second)
        import backup_service
        self.assertEqual(len(backup_service.list_backups()), 1)

    def test_jour_suivant_redeclenche(self):
        day1 = datetime(2026, 1, 1, 3, 0, tzinfo=timezone.utc)
        day2 = datetime(2026, 1, 2, 3, 0, tzinfo=timezone.utc)
        backup_scheduler.maybe_run_daily_backup(now=day1)
        triggered_day2 = backup_scheduler.maybe_run_daily_backup(now=day2)
        self.assertTrue(triggered_day2)
        import backup_service
        self.assertEqual(len(backup_service.list_backups()), 2)

    def test_appels_concurrents_le_meme_jour_une_seule_sauvegarde_reelle(self):
        """Simule plusieurs workers Gunicorn vérifiant en même temps s'il
        faut sauvegarder aujourd'hui : preuve que db.claim_daily_backup()
        empêche toute sauvegarde concurrente, quel que soit le nombre de
        threads/workers qui appellent maybe_run_daily_backup() en parallèle."""
        now = datetime(2026, 1, 1, 3, 0, tzinfo=timezone.utc)
        results = []
        lock = threading.Lock()

        def worker():
            triggered = backup_scheduler.maybe_run_daily_backup(now=now)
            with lock:
                results.append(triggered)

        threads = [threading.Thread(target=worker) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(sum(results), 1, f"une seule sauvegarde doit être déclenchée : {results}")
        import backup_service
        self.assertEqual(len(backup_service.list_backups()), 1)


class TestDesactivation(BackupSchedulerTestCase):
    def test_backup_auto_enabled_false_ne_declenche_jamais(self):
        config.BACKUP_AUTO_ENABLED = False
        now = datetime(2026, 1, 1, 3, 0, tzinfo=timezone.utc)
        with patch("backup_scheduler.settings_service") as mock_settings:
            triggered = backup_scheduler.maybe_run_daily_backup(now=now)
        self.assertFalse(triggered)
        mock_settings.create_backup.assert_not_called()

    def test_start_background_scheduler_ne_demarre_aucun_thread_si_desactive(self):
        config.BACKUP_AUTO_ENABLED = False
        with patch("backup_scheduler.threading.Thread") as mock_thread:
            backup_scheduler.start_background_scheduler()
        mock_thread.assert_not_called()


class TestErreurNeFaitJamaisPlanterLaBoucle(BackupSchedulerTestCase):
    def test_echec_de_sauvegarde_ne_leve_pas(self):
        now = datetime(2026, 1, 1, 3, 0, tzinfo=timezone.utc)
        with patch("backup_scheduler.settings_service") as mock_settings:
            mock_settings.create_backup.return_value = (None, "erreur simulée")
            triggered = backup_scheduler.maybe_run_daily_backup(now=now)  # ne doit jamais lever
        self.assertTrue(triggered)  # la tentative a bien eu lieu, même si elle a échoué


class TestRetrocompatibiliteBoutonManuel(BackupSchedulerTestCase):
    def test_create_backup_reste_utilisable_independamment_du_scheduler(self):
        """Le bouton "Créer une sauvegarde" (Administration -> Paramètres)
        n'est ni modifié ni court-circuité par ce module : settings_service.
        create_backup() fonctionne à l'identique, avec un acteur humain."""
        import settings_service
        admin_id = db.create_user("admin@test.local", "admin_test", "Admin", "hash")
        filename, error = settings_service.create_backup({"id": admin_id, "name": "Admin Test", "role": "super_admin"})
        self.assertIsNone(error)
        self.assertIsNotNone(filename)
        import backup_service
        self.assertEqual(len(backup_service.list_backups()), 1)


if __name__ == "__main__":
    unittest.main()
