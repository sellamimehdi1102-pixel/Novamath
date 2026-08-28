"""
Suite du service de quotas (webapp/quota_service.py) — source unique de
vérité des limitations numériques quotidiennes. Couvre les 3 paliers
(FREE/PREMIUM/ULTRA), les 5 QuotaType, get_limit/get_usage/get_remaining/
can_consume/consume/reset_if_needed/is_unlimited, le dépassement de quota
(QuotaExceededError), le changement de jour, la création automatique de ligne,
et un accès concurrent simulé (threads).

Base SQLite isolée dans un répertoire temporaire (db.DATA_DIR/db.DB_PATH
monkeypatchés), même pattern que tests/test_stripe_webhook_service.py :
aucune interférence avec data/novamath.db.
"""
import shutil
import tempfile
import threading
import unittest
from datetime import datetime, timezone
from pathlib import Path

import db
import quota_service
from plan_service import Plan
from quota_service import QUOTA_MATRIX, QuotaExceededError, QuotaType, UNLIMITED


def _today():
    return datetime.now(timezone.utc).date().isoformat()


class QuotaServiceTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp_dir = tempfile.mkdtemp()
        self._data_dir_backup = db.DATA_DIR
        self._db_path_backup = db.DB_PATH
        db.DATA_DIR = Path(self._tmp_dir)
        db.DB_PATH = db.DATA_DIR / "novamath.db"
        db.init_db()

        self.free_user = self._make_user("free@gmail.com", "free_user", Plan.FREE)
        self.premium_user = self._make_user("premium@gmail.com", "premium_user", Plan.PREMIUM)
        self.ultra_user = self._make_user("ultra@gmail.com", "ultra_user", Plan.ULTRA)

    def tearDown(self):
        db.DATA_DIR = self._data_dir_backup
        db.DB_PATH = self._db_path_backup
        shutil.rmtree(self._tmp_dir, ignore_errors=True)

    def _make_user(self, email, username, plan):
        user_id = db.create_user(email, username, "Élève", "hash")
        if plan is not Plan.FREE:
            db.set_stripe_subscription(user_id, "sub_test", plan.value, "active")
        return db.get_user_by_id(user_id)


class TestQuotaMatrix(unittest.TestCase):
    """La matrice elle-même — pas besoin de DB pour ces assertions."""

    def test_couvre_les_trois_plans(self):
        self.assertEqual(set(QUOTA_MATRIX.keys()), {Plan.FREE, Plan.PREMIUM, Plan.ULTRA})

    def test_couvre_les_cinq_quota_types_par_plan(self):
        for plan in (Plan.FREE, Plan.PREMIUM, Plan.ULTRA):
            with self.subTest(plan=plan):
                self.assertEqual(set(QUOTA_MATRIX[plan].keys()), set(QuotaType))

    def test_valeurs_free(self):
        free = QUOTA_MATRIX[Plan.FREE]
        self.assertEqual(free[QuotaType.CHAT_MESSAGES], 25)
        self.assertEqual(free[QuotaType.PDF_ANALYSIS], 0)
        self.assertEqual(free[QuotaType.AI_GENERATIONS], 20)
        self.assertEqual(free[QuotaType.CUSTOM_EXERCISES], 0)
        self.assertEqual(free[QuotaType.EXPORTS], 0)

    def test_valeurs_premium(self):
        premium = QUOTA_MATRIX[Plan.PREMIUM]
        self.assertEqual(premium[QuotaType.CHAT_MESSAGES], 250)
        self.assertEqual(premium[QuotaType.PDF_ANALYSIS], 25)
        self.assertEqual(premium[QuotaType.AI_GENERATIONS], 500)
        self.assertEqual(premium[QuotaType.CUSTOM_EXERCISES], 100)
        self.assertEqual(premium[QuotaType.EXPORTS], 20)

    def test_valeurs_ultra_illimitees(self):
        ultra = QUOTA_MATRIX[Plan.ULTRA]
        for quota in QuotaType:
            with self.subTest(quota=quota):
                self.assertIs(ultra[quota], UNLIMITED)
                self.assertIsNone(ultra[quota])

    def test_premium_superieur_ou_egal_a_free_partout(self):
        for quota in QuotaType:
            with self.subTest(quota=quota):
                self.assertGreaterEqual(QUOTA_MATRIX[Plan.PREMIUM][quota], QUOTA_MATRIX[Plan.FREE][quota])


class TestGetLimitAndIsUnlimited(QuotaServiceTestCase):
    def test_get_limit_free(self):
        self.assertEqual(quota_service.get_limit(self.free_user, QuotaType.CHAT_MESSAGES), 25)
        self.assertEqual(quota_service.get_limit(self.free_user, QuotaType.PDF_ANALYSIS), 0)

    def test_get_limit_premium(self):
        self.assertEqual(quota_service.get_limit(self.premium_user, QuotaType.CHAT_MESSAGES), 250)

    def test_get_limit_ultra_est_none(self):
        for quota in QuotaType:
            with self.subTest(quota=quota):
                self.assertIsNone(quota_service.get_limit(self.ultra_user, quota))

    def test_is_unlimited(self):
        self.assertFalse(quota_service.is_unlimited(self.free_user, QuotaType.CHAT_MESSAGES))
        self.assertFalse(quota_service.is_unlimited(self.premium_user, QuotaType.CHAT_MESSAGES))
        self.assertTrue(quota_service.is_unlimited(self.ultra_user, QuotaType.CHAT_MESSAGES))


class TestGetUsageAndRemaining(QuotaServiceTestCase):
    def test_usage_initiale_est_zero(self):
        self.assertEqual(quota_service.get_usage(self.free_user, QuotaType.CHAT_MESSAGES), 0)

    def test_remaining_initial_egale_la_limite(self):
        self.assertEqual(quota_service.get_remaining(self.free_user, QuotaType.CHAT_MESSAGES), 25)

    def test_remaining_diminue_apres_consommation(self):
        quota_service.consume(self.free_user, QuotaType.CHAT_MESSAGES, amount=3)
        self.assertEqual(quota_service.get_usage(self.free_user, QuotaType.CHAT_MESSAGES), 3)
        self.assertEqual(quota_service.get_remaining(self.free_user, QuotaType.CHAT_MESSAGES), 22)

    def test_remaining_ne_descend_jamais_sous_zero(self):
        # Consommation directe en base au-delà de la limite (simule un vieux
        # palier supérieur rétrogradé) : get_remaining doit rester >= 0.
        db.increment_daily_usage(self.free_user["id"], QuotaType.CHAT_MESSAGES.value, _today(), 999)
        self.assertEqual(quota_service.get_remaining(self.free_user, QuotaType.CHAT_MESSAGES), 0)

    def test_remaining_none_si_illimite(self):
        quota_service.consume(self.ultra_user, QuotaType.CHAT_MESSAGES, amount=10_000)
        self.assertIsNone(quota_service.get_remaining(self.ultra_user, QuotaType.CHAT_MESSAGES))

    def test_usage_isolee_par_quota_type(self):
        quota_service.consume(self.free_user, QuotaType.CHAT_MESSAGES, amount=5)
        self.assertEqual(quota_service.get_usage(self.free_user, QuotaType.AI_GENERATIONS), 0)

    def test_usage_isolee_par_utilisateur(self):
        quota_service.consume(self.premium_user, QuotaType.CHAT_MESSAGES, amount=5)
        self.assertEqual(quota_service.get_usage(self.free_user, QuotaType.CHAT_MESSAGES), 0)


class TestCanConsume(QuotaServiceTestCase):
    def test_peut_consommer_dans_la_limite(self):
        self.assertTrue(quota_service.can_consume(self.free_user, QuotaType.CHAT_MESSAGES, amount=25))

    def test_ne_peut_pas_depasser_la_limite(self):
        self.assertFalse(quota_service.can_consume(self.free_user, QuotaType.CHAT_MESSAGES, amount=26))

    def test_quota_a_zero_ne_permet_rien(self):
        self.assertFalse(quota_service.can_consume(self.free_user, QuotaType.PDF_ANALYSIS, amount=1))

    def test_illimite_permet_toujours(self):
        self.assertTrue(quota_service.can_consume(self.ultra_user, QuotaType.CHAT_MESSAGES, amount=1_000_000))

    def test_tient_compte_de_lusage_deja_consomme(self):
        quota_service.consume(self.free_user, QuotaType.CHAT_MESSAGES, amount=20)
        self.assertTrue(quota_service.can_consume(self.free_user, QuotaType.CHAT_MESSAGES, amount=5))
        self.assertFalse(quota_service.can_consume(self.free_user, QuotaType.CHAT_MESSAGES, amount=6))


class TestConsume(QuotaServiceTestCase):
    def test_consomme_et_renvoie_le_nouveau_total(self):
        self.assertEqual(quota_service.consume(self.free_user, QuotaType.CHAT_MESSAGES), 1)
        self.assertEqual(quota_service.consume(self.free_user, QuotaType.CHAT_MESSAGES), 2)

    def test_consomme_par_lot(self):
        total = quota_service.consume(self.free_user, QuotaType.AI_GENERATIONS, amount=7)
        self.assertEqual(total, 7)
        self.assertEqual(quota_service.get_usage(self.free_user, QuotaType.AI_GENERATIONS), 7)

    def test_consommation_jusqua_la_limite_exacte_reussit(self):
        total = quota_service.consume(self.free_user, QuotaType.CHAT_MESSAGES, amount=25)
        self.assertEqual(total, 25)

    def test_depassement_leve_quota_exceeded_error(self):
        quota_service.consume(self.free_user, QuotaType.CHAT_MESSAGES, amount=25)
        with self.assertRaises(QuotaExceededError) as ctx:
            quota_service.consume(self.free_user, QuotaType.CHAT_MESSAGES, amount=1)
        err = ctx.exception
        self.assertEqual(err.quota, QuotaType.CHAT_MESSAGES)
        self.assertEqual(err.remaining, 0)
        self.assertEqual(err.limit, 25)
        self.assertEqual(err.required_plan, Plan.PREMIUM)

    def test_depassement_ne_facture_rien(self):
        """Le compteur ne doit JAMAIS dépasser la limite après un refus —
        preuve que la compensation (décrément) fonctionne."""
        quota_service.consume(self.free_user, QuotaType.CHAT_MESSAGES, amount=25)
        with self.assertRaises(QuotaExceededError):
            quota_service.consume(self.free_user, QuotaType.CHAT_MESSAGES, amount=1)
        self.assertEqual(quota_service.get_usage(self.free_user, QuotaType.CHAT_MESSAGES), 25)

    def test_quota_a_zero_leve_immediatement(self):
        with self.assertRaises(QuotaExceededError) as ctx:
            quota_service.consume(self.free_user, QuotaType.PDF_ANALYSIS)
        self.assertEqual(ctx.exception.limit, 0)
        self.assertEqual(quota_service.get_usage(self.free_user, QuotaType.PDF_ANALYSIS), 0)

    def test_required_plan_propose_ultra_depuis_premium(self):
        quota_service.consume(self.premium_user, QuotaType.EXPORTS, amount=20)
        with self.assertRaises(QuotaExceededError) as ctx:
            quota_service.consume(self.premium_user, QuotaType.EXPORTS, amount=1)
        self.assertEqual(ctx.exception.required_plan, Plan.ULTRA)

    def test_ultra_ne_leve_jamais(self):
        try:
            quota_service.consume(self.ultra_user, QuotaType.CHAT_MESSAGES, amount=100_000)
        except QuotaExceededError:
            self.fail("Ultra ne doit jamais lever QuotaExceededError (illimité).")

    def test_consommation_dun_gros_lot_qui_depasse_dun_coup(self):
        with self.assertRaises(QuotaExceededError):
            quota_service.consume(self.free_user, QuotaType.CHAT_MESSAGES, amount=26)
        # Aucun incrément partiel ne doit rester : tout ou rien.
        self.assertEqual(quota_service.get_usage(self.free_user, QuotaType.CHAT_MESSAGES), 0)


class TestNouveauJourEtCreationAutomatique(QuotaServiceTestCase):
    def test_ligne_creee_automatiquement_au_premier_consume(self):
        conn = db.get_connection()
        try:
            rows = conn.execute("SELECT * FROM user_daily_usage").fetchall()
        finally:
            conn.close()
        self.assertEqual(len(rows), 0)

        quota_service.consume(self.free_user, QuotaType.CHAT_MESSAGES)

        conn = db.get_connection()
        try:
            rows = conn.execute("SELECT * FROM user_daily_usage").fetchall()
        finally:
            conn.close()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["count"], 1)

    def test_reset_if_needed_cree_une_ligne_a_zero(self):
        usage = quota_service.reset_if_needed(self.free_user, QuotaType.CHAT_MESSAGES)
        self.assertEqual(usage, 0)
        self.assertEqual(quota_service.get_usage(self.free_user, QuotaType.CHAT_MESSAGES), 0)

    def test_reset_if_needed_est_idempotent(self):
        quota_service.consume(self.free_user, QuotaType.CHAT_MESSAGES, amount=5)
        usage = quota_service.reset_if_needed(self.free_user, QuotaType.CHAT_MESSAGES)
        # N'écrase pas un usage déjà présent : reset_if_needed ne fait que
        # garantir l'EXISTENCE de la ligne, jamais la remettre à 0 si déjà là.
        self.assertEqual(usage, 5)

    def test_nouveau_jour_reinitialise_lusage(self):
        quota_service.consume(self.free_user, QuotaType.CHAT_MESSAGES, amount=25)
        self.assertEqual(quota_service.get_usage(self.free_user, QuotaType.CHAT_MESSAGES), 25)

        # Un autre jour = compteur à 0, aucune tâche de reset à appeler.
        self.assertEqual(
            quota_service.get_usage(self.free_user, QuotaType.CHAT_MESSAGES, day="2020-01-01"), 0
        )

    def test_nouveau_jour_permet_de_nouveau_consume(self):
        quota_service.consume(self.free_user, QuotaType.CHAT_MESSAGES, amount=25)
        with self.assertRaises(QuotaExceededError):
            quota_service.consume(self.free_user, QuotaType.CHAT_MESSAGES, amount=1)

        # Simule le lendemain en insérant directement sur une autre date : le
        # service ne connaît que _today(), donc on vérifie via db.py que la
        # ligne d'hier reste intacte et n'affecte pas un autre jour.
        db.increment_daily_usage(self.free_user["id"], QuotaType.CHAT_MESSAGES.value, "2099-01-01", 1)
        self.assertEqual(
            db.get_daily_usage(self.free_user["id"], QuotaType.CHAT_MESSAGES.value, "2099-01-01"), 1
        )
        self.assertEqual(quota_service.get_usage(self.free_user, QuotaType.CHAT_MESSAGES), 25)


class TestAccesConcurrentSimule(QuotaServiceTestCase):
    def test_consume_concurrent_ne_depasse_jamais_la_limite(self):
        """40 threads tentent chacun de consommer 1 unité d'un quota limité à
        25/jour, simultanément. Le compteur final ne doit jamais dépasser 25,
        et exactement 25 threads doivent réussir (les autres lèvent
        QuotaExceededError) — preuve que l'UPSERT atomique + compensation
        empêchent toute perte d'écriture ou tout dépassement sous concurrence."""
        successes = []
        failures = []
        lock = threading.Lock()

        def worker():
            try:
                quota_service.consume(self.free_user, QuotaType.CHAT_MESSAGES, amount=1)
                with lock:
                    successes.append(1)
            except QuotaExceededError:
                with lock:
                    failures.append(1)

        threads = [threading.Thread(target=worker) for _ in range(40)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(successes), 25)
        self.assertEqual(len(failures), 15)
        self.assertEqual(quota_service.get_usage(self.free_user, QuotaType.CHAT_MESSAGES), 25)

    def test_consume_concurrent_sur_utilisateurs_differents_ninterfere_pas(self):
        errors = []

        def worker(user):
            try:
                for _ in range(10):
                    quota_service.consume(user, QuotaType.AI_GENERATIONS, amount=1)
            except QuotaExceededError as e:
                errors.append(e)

        threads = [
            threading.Thread(target=worker, args=(self.free_user,)),
            threading.Thread(target=worker, args=(self.premium_user,)),
            threading.Thread(target=worker, args=(self.ultra_user,)),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(errors, [])
        self.assertEqual(quota_service.get_usage(self.free_user, QuotaType.AI_GENERATIONS), 10)
        self.assertEqual(quota_service.get_usage(self.premium_user, QuotaType.AI_GENERATIONS), 10)
        self.assertEqual(quota_service.get_usage(self.ultra_user, QuotaType.AI_GENERATIONS), 10)


class TestQuotaExceededErrorMessage(unittest.TestCase):
    def test_message_lisible(self):
        err = QuotaExceededError(
            quota=QuotaType.CHAT_MESSAGES, remaining=0, limit=25, required_plan=Plan.PREMIUM,
        )
        self.assertIn("chat_messages", str(err))
        self.assertIn("25", str(err))
        self.assertIn("premium", str(err))


if __name__ == "__main__":
    unittest.main()
