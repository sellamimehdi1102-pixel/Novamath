"""
Suite de health_service.py — chaque vérification individuelle
(check_database/check_stripe_configured/check_backup_directory/
check_disk_space/app_version) et l'agrégation snapshot(), y compris les cas
de panne (base indisponible, dossier de sauvegarde absent/inaccessible,
espace disque insuffisant) : aucune vérification ne doit jamais lever.
"""
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import backup_service
import config
import db
import health_service


class HealthServiceTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp_dir = tempfile.mkdtemp()
        self._data_dir_backup = db.DATA_DIR
        self._db_path_backup = db.DB_PATH
        self._backup_directory_backup = config.BACKUP_DIRECTORY

        db.DATA_DIR = Path(self._tmp_dir) / "data"
        db.DB_PATH = db.DATA_DIR / "novamath.db"
        config.BACKUP_DIRECTORY = str(Path(self._tmp_dir) / "backups")
        db.init_db()

    def tearDown(self):
        db.DATA_DIR = self._data_dir_backup
        db.DB_PATH = self._db_path_backup
        config.BACKUP_DIRECTORY = self._backup_directory_backup
        shutil.rmtree(self._tmp_dir, ignore_errors=True)


class TestCheckDatabase(HealthServiceTestCase):
    def test_true_si_la_base_repond(self):
        self.assertTrue(health_service.check_database())

    def test_false_si_la_base_est_indisponible(self):
        with patch("health_service.db.get_connection", side_effect=OSError("disque hors service")):
            self.assertFalse(health_service.check_database())

    def test_ne_leve_jamais(self):
        with patch("health_service.db.get_connection", side_effect=RuntimeError("boum")):
            try:
                health_service.check_database()
            except Exception as e:  # pragma: no cover - preuve d'échec du test
                self.fail(f"check_database() a levé {e!r}")


class TestCheckStripeConfigured(HealthServiceTestCase):
    def test_true_si_stripe_secret_key_definie(self):
        with patch.dict(os.environ, {"STRIPE_SECRET_KEY": "sk_test_reelle_123"}):
            self.assertTrue(health_service.check_stripe_configured())

    def test_false_si_absente(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("STRIPE_SECRET_KEY", None)
            self.assertFalse(health_service.check_stripe_configured())

    def test_false_si_valeur_placeholder(self):
        with patch.dict(os.environ, {"STRIPE_SECRET_KEY": "sk_test_xxx"}):
            self.assertFalse(health_service.check_stripe_configured())

    def test_naccede_jamais_au_reseau(self):
        """Vérification de configuration uniquement (Partie 4) : aucun appel
        au SDK Stripe ne doit être effectué — la fonction ne fait qu'inspecter
        une variable d'environnement."""
        with patch("stripe.Customer.list", side_effect=AssertionError("appel réseau interdit ici")):
            with patch.dict(os.environ, {"STRIPE_SECRET_KEY": "sk_test_reelle_123"}):
                self.assertTrue(health_service.check_stripe_configured())


class TestCheckBackupDirectory(HealthServiceTestCase):
    def test_true_et_cree_le_dossier_sil_est_absent(self):
        target = Path(config.BACKUP_DIRECTORY)
        self.assertFalse(target.exists())
        self.assertTrue(health_service.check_backup_directory())
        self.assertTrue(target.is_dir())

    def test_true_si_deja_present(self):
        backup_service.backup_dir()
        self.assertTrue(health_service.check_backup_directory())

    def test_false_si_creation_impossible(self):
        with patch("health_service.backup_service.backup_dir", side_effect=OSError("permission refusée")):
            self.assertFalse(health_service.check_backup_directory())

    def test_false_si_dossier_non_inscriptible(self):
        with patch("health_service.backup_service.backup_dir", return_value=Path(self._tmp_dir)), \
             patch("health_service.os.access", return_value=False):
            self.assertFalse(health_service.check_backup_directory())


class TestCheckDiskSpace(HealthServiceTestCase):
    def test_true_avec_un_seuil_minime(self):
        self.assertTrue(health_service.check_disk_space(min_free_mb=1))

    def test_false_avec_un_seuil_irrealiste(self):
        self.assertFalse(health_service.check_disk_space(min_free_mb=10**9))

    def test_false_si_lecture_impossible(self):
        with patch("health_service.shutil.disk_usage", side_effect=OSError("volume introuvable")):
            self.assertFalse(health_service.check_disk_space())


class TestAppVersion(HealthServiceTestCase):
    def test_lit_le_fichier_version_reel(self):
        version = health_service.app_version()
        self.assertIsInstance(version, str)
        self.assertNotEqual(version, "")

    def test_unknown_si_fichier_absent(self):
        with patch("health_service.VERSION_FILE", Path(self._tmp_dir) / "VERSION_INEXISTANT"):
            self.assertEqual(health_service.app_version(), "unknown")


class TestSnapshot(HealthServiceTestCase):
    def test_status_ok_si_tout_va_bien(self):
        with patch.dict(os.environ, {"STRIPE_SECRET_KEY": "sk_test_reelle_123"}):
            result = health_service.snapshot()
        self.assertEqual(result["status"], "ok")

    def test_status_degraded_si_un_check_echoue(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("STRIPE_SECRET_KEY", None)
            result = health_service.snapshot()
        self.assertEqual(result["status"], "degraded")

    def test_contient_les_quatre_verifications_attendues(self):
        result = health_service.snapshot()
        self.assertEqual(
            set(result["checks"]),
            {"database", "stripe_configured", "backup_directory", "disk_space"},
        )

    def test_contient_la_version(self):
        result = health_service.snapshot()
        self.assertIn("version", result)

    def test_ne_leve_jamais_meme_avec_tout_en_panne(self):
        with patch("health_service.check_database", return_value=False), \
             patch("health_service.check_stripe_configured", return_value=False), \
             patch("health_service.check_backup_directory", return_value=False), \
             patch("health_service.check_disk_space", return_value=False):
            result = health_service.snapshot()  # ne doit pas lever
        self.assertEqual(result["status"], "degraded")
        self.assertFalse(all(result["checks"].values()))


if __name__ == "__main__":
    unittest.main()
