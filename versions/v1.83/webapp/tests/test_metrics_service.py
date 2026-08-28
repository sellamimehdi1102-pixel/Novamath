"""
Suite de metrics_service.py — compteurs en mémoire (record_request/
record_error/in_memory_snapshot/reset) et compteurs persistés dérivés de
tables déjà existantes (snapshot()). Base SQLite isolée dans un répertoire
temporaire (db.DATA_DIR/db.DB_PATH monkeypatchés), même pattern que
tests/test_quota_service.py : aucune interférence avec data/novamath.db.
"""
import shutil
import tempfile
import unittest
from pathlib import Path

import db
import metrics_service


class TestInMemoryCounters(unittest.TestCase):
    def setUp(self):
        metrics_service.reset()

    def tearDown(self):
        metrics_service.reset()

    def test_snapshot_initial_est_a_zero(self):
        snap = metrics_service.in_memory_snapshot()
        self.assertEqual(snap, {"total_requests": 0, "total_errors": 0, "avg_request_duration_ms": 0.0})

    def test_record_request_incremente_le_total(self):
        metrics_service.record_request(10.0)
        metrics_service.record_request(20.0)
        self.assertEqual(metrics_service.in_memory_snapshot()["total_requests"], 2)

    def test_record_request_calcule_la_moyenne(self):
        metrics_service.record_request(10.0)
        metrics_service.record_request(30.0)
        self.assertEqual(metrics_service.in_memory_snapshot()["avg_request_duration_ms"], 20.0)

    def test_record_error_incremente_les_erreurs_sans_toucher_aux_requetes(self):
        metrics_service.record_error()
        metrics_service.record_error()
        snap = metrics_service.in_memory_snapshot()
        self.assertEqual(snap["total_errors"], 2)
        self.assertEqual(snap["total_requests"], 0)

    def test_reset_remet_tout_a_zero(self):
        metrics_service.record_request(5.0)
        metrics_service.record_error()
        metrics_service.reset()
        self.assertEqual(
            metrics_service.in_memory_snapshot(),
            {"total_requests": 0, "total_errors": 0, "avg_request_duration_ms": 0.0},
        )

    def test_concurrence_ne_perd_aucun_increment(self):
        import threading
        threads = [threading.Thread(target=metrics_service.record_request, args=(1.0,)) for _ in range(200)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(metrics_service.in_memory_snapshot()["total_requests"], 200)


class MetricsServiceDbTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp_dir = tempfile.mkdtemp()
        self._data_dir_backup = db.DATA_DIR
        self._db_path_backup = db.DB_PATH
        db.DATA_DIR = Path(self._tmp_dir)
        db.DB_PATH = db.DATA_DIR / "novamath.db"
        db.init_db()
        metrics_service.reset()

    def tearDown(self):
        db.DATA_DIR = self._data_dir_backup
        db.DB_PATH = self._db_path_backup
        shutil.rmtree(self._tmp_dir, ignore_errors=True)
        metrics_service.reset()

    def _create_user(self, email):
        return db.create_user(email, email.split("@")[0], "Test", "hash")


class TestSnapshotPersiste(MetricsServiceDbTestCase):
    def test_snapshot_sur_base_vierge_ne_leve_pas(self):
        snap = metrics_service.snapshot()
        self.assertEqual(snap["users"], 0)
        self.assertEqual(snap["conversations"], 0)
        self.assertEqual(snap["logins"], 0)
        self.assertEqual(snap["registrations"], 0)
        self.assertEqual(snap["payments"], 0)

    def test_compte_les_utilisateurs(self):
        self._create_user("a@gmail.com")
        self._create_user("b@gmail.com")
        self.assertEqual(metrics_service.snapshot()["users"], 2)

    def test_compte_les_conversations(self):
        user_id = self._create_user("c@gmail.com")
        db.create_conversation(user_id)
        db.create_conversation(user_id)
        db.create_conversation(user_id)
        self.assertEqual(metrics_service.snapshot()["conversations"], 3)

    def test_compte_les_connexions_via_security_events(self):
        db.log_security_event("login_success", user_id=1)
        db.log_security_event("login_success", user_id=1)
        db.log_security_event("login_failed", user_id=1)  # ne doit pas être compté
        self.assertEqual(metrics_service.snapshot()["logins"], 2)

    def test_compte_les_inscriptions(self):
        db.log_security_event("account_created", user_id=1)
        self.assertEqual(metrics_service.snapshot()["registrations"], 1)

    def test_compte_les_paiements_deux_types_devenements(self):
        db.log_security_event("stripe_checkout_completed", user_id=1)
        db.log_security_event("stripe_invoice_paid", user_id=1)
        db.log_security_event("stripe_invoice_paid", user_id=1)
        self.assertEqual(metrics_service.snapshot()["payments"], 3)

    def test_snapshot_combine_persiste_et_memoire(self):
        self._create_user("d@gmail.com")
        metrics_service.record_request(15.0)
        snap = metrics_service.snapshot()
        self.assertEqual(snap["users"], 1)
        self.assertEqual(snap["total_requests"], 1)

    def test_snapshot_ne_ralentit_jamais_une_requete_normale(self):
        """record_request()/record_error() (appelés à CHAQUE requête par
        logging_service) ne touchent jamais la base de données — seul
        snapshot() (appelé à la demande, jamais sur le chemin d'une requête
        normale) fait des lectures SQL. Preuve : record_request() seul ne
        crée aucune connexion (pas d'exception si la base est inaccessible)."""
        db.DB_PATH = db.DATA_DIR / "chemin_qui_nexiste_pas" / "novamath.db"
        metrics_service.record_request(1.0)
        metrics_service.record_error()
        self.assertEqual(metrics_service.in_memory_snapshot()["total_requests"], 1)


if __name__ == "__main__":
    unittest.main()
