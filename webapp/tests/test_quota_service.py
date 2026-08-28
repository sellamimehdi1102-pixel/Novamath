"""
Suite du service de quotas (webapp/quota_service.py) — source unique de
vérité des limitations numériques quotidiennes. Couvre les 3 paliers
(FREE/PREMIUM/ULTRA), les 7 QuotaType, get_limit/get_usage/get_remaining/
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
        self.assertEqual(free[QuotaType.CHAT_MESSAGES], 15)
        self.assertEqual(free[QuotaType.PDF_ANALYSIS], 0)
        self.assertEqual(free[QuotaType.AI_GENERATIONS], 20)
        self.assertEqual(free[QuotaType.CUSTOM_EXERCISES], 0)
        self.assertEqual(free[QuotaType.EXPORTS], 0)
        self.assertEqual(free[QuotaType.EXERCISES_DAILY], 20)

    def test_valeurs_premium(self):
        premium = QUOTA_MATRIX[Plan.PREMIUM]
        self.assertEqual(premium[QuotaType.CHAT_MESSAGES], 25)
        self.assertEqual(premium[QuotaType.PDF_ANALYSIS], 25)
        self.assertEqual(premium[QuotaType.AI_GENERATIONS], 500)
        self.assertEqual(premium[QuotaType.CUSTOM_EXERCISES], 100)
        self.assertEqual(premium[QuotaType.EXPORTS], 20)
        self.assertEqual(premium[QuotaType.LLM_CALLS], 20)
        self.assertEqual(premium[QuotaType.EXERCISES_DAILY], 60)

    def test_valeurs_exercises_daily_distinctes_de_ai_generations_et_custom_exercises(self):
        # Garde-fou explicite demandé par le chantier "Limitation des
        # exercices par abonnement" : EXERCISES_DAILY ne doit JAMAIS être
        # confondu (même valeur par coïncidence acceptée, mais jamais la
        # MÊME clé) avec AI_GENERATIONS/CUSTOM_EXERCISES, qui restent réservés
        # à une future vraie fonctionnalité IA/personnalisée non implémentée.
        self.assertNotEqual(QuotaType.EXERCISES_DAILY, QuotaType.AI_GENERATIONS)
        self.assertNotEqual(QuotaType.EXERCISES_DAILY, QuotaType.CUSTOM_EXERCISES)
        for plan in (Plan.FREE, Plan.PREMIUM, Plan.ULTRA):
            with self.subTest(plan=plan):
                # AI_GENERATIONS/CUSTOM_EXERCISES restent EXACTEMENT ce
                # qu'ils étaient avant ce chantier (valeurs mortes, jamais
                # consommées) — ce chantier ne les a pas touchés.
                self.assertEqual(QUOTA_MATRIX[plan][QuotaType.AI_GENERATIONS],
                                  {Plan.FREE: 20, Plan.PREMIUM: 500, Plan.ULTRA: UNLIMITED}[plan])
                self.assertEqual(QUOTA_MATRIX[plan][QuotaType.CUSTOM_EXERCISES],
                                  {Plan.FREE: 0, Plan.PREMIUM: 100, Plan.ULTRA: UNLIMITED}[plan])

    def test_valeurs_ultra(self):
        # CHAT_MESSAGES et LLM_CALLS (Chantier 6) sont volontairement exclus
        # de l'illimité : CHAT_MESSAGES est désormais une limite commerciale
        # de volume (40/j) et LLM_CALLS un budget de PROTECTION FINANCIÈRE
        # (appels réseau réels vers un fournisseur LLM payant) — les deux
        # sont délibérément finis pour Ultra (voir quota_service.py::
        # QUOTA_MATRIX), contrairement aux autres QuotaType qui restent
        # illimités pour ce palier.
        ultra = QUOTA_MATRIX[Plan.ULTRA]
        self.assertEqual(ultra[QuotaType.CHAT_MESSAGES], 40)
        self.assertEqual(ultra[QuotaType.LLM_CALLS], 40)
        for quota in QuotaType:
            if quota in (QuotaType.CHAT_MESSAGES, QuotaType.LLM_CALLS):
                continue
            with self.subTest(quota=quota):
                self.assertIs(ultra[quota], UNLIMITED)
                self.assertIsNone(ultra[quota])

    def test_premium_superieur_ou_egal_a_free_partout(self):
        # LLM_CALLS exclu : Free y est illimité (aucun second palier distinct,
        # sa chaîne n'a qu'un seul candidat réel, voir
        # provider_manager.MODEL_CHAIN_BY_PLAN) alors que Premium y a une
        # limite finie de protection (20) — l'ordre inverse est ici
        # intentionnel, jamais une régression. CHAT_MESSAGES Free (15) <
        # Premium (25) depuis le chantier "Réduction quota Free"
        # (2026-08-25) : >= reste trivialement vrai, conservé dans la boucle
        # générique, pas besoin d'exclusion pour celui-ci.
        for quota in QuotaType:
            if quota is QuotaType.LLM_CALLS:
                continue
            with self.subTest(quota=quota):
                self.assertGreaterEqual(QUOTA_MATRIX[Plan.PREMIUM][quota], QUOTA_MATRIX[Plan.FREE][quota])


class TestGetLimitAndIsUnlimited(QuotaServiceTestCase):
    def test_get_limit_free(self):
        self.assertEqual(quota_service.get_limit(self.free_user, QuotaType.CHAT_MESSAGES), 15)
        self.assertEqual(quota_service.get_limit(self.free_user, QuotaType.PDF_ANALYSIS), 0)

    def test_get_limit_premium(self):
        self.assertEqual(quota_service.get_limit(self.premium_user, QuotaType.CHAT_MESSAGES), 25)

    def test_get_limit_ultra(self):
        # CHAT_MESSAGES/LLM_CALLS exclus : voir TestQuotaMatrix.test_valeurs_ultra.
        self.assertEqual(quota_service.get_limit(self.ultra_user, QuotaType.CHAT_MESSAGES), 40)
        self.assertEqual(quota_service.get_limit(self.ultra_user, QuotaType.LLM_CALLS), 40)
        for quota in QuotaType:
            if quota in (QuotaType.CHAT_MESSAGES, QuotaType.LLM_CALLS):
                continue
            with self.subTest(quota=quota):
                self.assertIsNone(quota_service.get_limit(self.ultra_user, quota))

    def test_is_unlimited(self):
        self.assertFalse(quota_service.is_unlimited(self.free_user, QuotaType.CHAT_MESSAGES))
        self.assertFalse(quota_service.is_unlimited(self.premium_user, QuotaType.CHAT_MESSAGES))
        self.assertFalse(quota_service.is_unlimited(self.ultra_user, QuotaType.CHAT_MESSAGES))
        self.assertTrue(quota_service.is_unlimited(self.ultra_user, QuotaType.PDF_ANALYSIS))


class TestGetUsageAndRemaining(QuotaServiceTestCase):
    def test_usage_initiale_est_zero(self):
        self.assertEqual(quota_service.get_usage(self.free_user, QuotaType.CHAT_MESSAGES), 0)

    def test_remaining_initial_egale_la_limite(self):
        self.assertEqual(quota_service.get_remaining(self.free_user, QuotaType.CHAT_MESSAGES), 15)

    def test_remaining_diminue_apres_consommation(self):
        quota_service.consume(self.free_user, QuotaType.CHAT_MESSAGES, amount=3)
        self.assertEqual(quota_service.get_usage(self.free_user, QuotaType.CHAT_MESSAGES), 3)
        self.assertEqual(quota_service.get_remaining(self.free_user, QuotaType.CHAT_MESSAGES), 12)

    def test_remaining_ne_descend_jamais_sous_zero(self):
        # Consommation directe en base au-delà de la limite (simule un vieux
        # palier supérieur rétrogradé) : get_remaining doit rester >= 0.
        db.increment_daily_usage(self.free_user["id"], QuotaType.CHAT_MESSAGES.value, _today(), 999)
        self.assertEqual(quota_service.get_remaining(self.free_user, QuotaType.CHAT_MESSAGES), 0)

    def test_remaining_none_si_illimite(self):
        # PDF_ANALYSIS reste illimité pour Ultra (contrairement à CHAT_MESSAGES/
        # LLM_CALLS depuis le Chantier 6 — voir quota_service.py::QUOTA_MATRIX).
        quota_service.consume(self.ultra_user, QuotaType.PDF_ANALYSIS, amount=10_000)
        self.assertIsNone(quota_service.get_remaining(self.ultra_user, QuotaType.PDF_ANALYSIS))

    def test_usage_isolee_par_quota_type(self):
        quota_service.consume(self.free_user, QuotaType.CHAT_MESSAGES, amount=5)
        self.assertEqual(quota_service.get_usage(self.free_user, QuotaType.AI_GENERATIONS), 0)

    def test_usage_isolee_par_utilisateur(self):
        quota_service.consume(self.premium_user, QuotaType.CHAT_MESSAGES, amount=5)
        self.assertEqual(quota_service.get_usage(self.free_user, QuotaType.CHAT_MESSAGES), 0)


class TestCanConsume(QuotaServiceTestCase):
    def test_peut_consommer_dans_la_limite(self):
        self.assertTrue(quota_service.can_consume(self.free_user, QuotaType.CHAT_MESSAGES, amount=15))

    def test_ne_peut_pas_depasser_la_limite(self):
        self.assertFalse(quota_service.can_consume(self.free_user, QuotaType.CHAT_MESSAGES, amount=16))

    def test_quota_a_zero_ne_permet_rien(self):
        self.assertFalse(quota_service.can_consume(self.free_user, QuotaType.PDF_ANALYSIS, amount=1))

    def test_illimite_permet_toujours(self):
        self.assertTrue(quota_service.can_consume(self.ultra_user, QuotaType.PDF_ANALYSIS, amount=1_000_000))

    def test_tient_compte_de_lusage_deja_consomme(self):
        quota_service.consume(self.free_user, QuotaType.CHAT_MESSAGES, amount=10)
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
        total = quota_service.consume(self.free_user, QuotaType.CHAT_MESSAGES, amount=15)
        self.assertEqual(total, 15)

    def test_depassement_leve_quota_exceeded_error(self):
        quota_service.consume(self.free_user, QuotaType.CHAT_MESSAGES, amount=15)
        with self.assertRaises(QuotaExceededError) as ctx:
            quota_service.consume(self.free_user, QuotaType.CHAT_MESSAGES, amount=1)
        err = ctx.exception
        self.assertEqual(err.quota, QuotaType.CHAT_MESSAGES)
        self.assertEqual(err.remaining, 0)
        self.assertEqual(err.limit, 15)
        # Depuis le chantier "Réduction quota Free" (2026-08-25), Free (15)
        # est strictement inférieur à Premium (25) sur CHAT_MESSAGES :
        # _next_plan_with_more() propose donc à nouveau Premium en premier
        # palier offrant réellement plus sur ce quota précis (ce n'était plus
        # le cas quand Free==Premium==25, entre le Chantier 6 et ce chantier).
        self.assertEqual(err.required_plan, Plan.PREMIUM)

    def test_depassement_ne_facture_rien(self):
        """Le compteur ne doit JAMAIS dépasser la limite après un refus —
        preuve que la compensation (décrément) fonctionne."""
        quota_service.consume(self.free_user, QuotaType.CHAT_MESSAGES, amount=15)
        with self.assertRaises(QuotaExceededError):
            quota_service.consume(self.free_user, QuotaType.CHAT_MESSAGES, amount=1)
        self.assertEqual(quota_service.get_usage(self.free_user, QuotaType.CHAT_MESSAGES), 15)

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

    def test_ultra_ne_leve_jamais_sur_un_quota_illimite(self):
        # PDF_ANALYSIS reste illimité pour Ultra (CHAT_MESSAGES/LLM_CALLS ont
        # désormais une vraie limite depuis le Chantier 6 — testé séparément
        # dans TestConsommationLimiteesUltraChantier6 ci-dessous).
        try:
            quota_service.consume(self.ultra_user, QuotaType.PDF_ANALYSIS, amount=100_000)
        except QuotaExceededError:
            self.fail("Ultra ne doit jamais lever QuotaExceededError sur un quota illimité.")

    def test_consommation_dun_gros_lot_qui_depasse_dun_coup(self):
        with self.assertRaises(QuotaExceededError):
            quota_service.consume(self.free_user, QuotaType.CHAT_MESSAGES, amount=26)
        # Aucun incrément partiel ne doit rester : tout ou rien.
        self.assertEqual(quota_service.get_usage(self.free_user, QuotaType.CHAT_MESSAGES), 0)


class TestConsommationLimiteesUltraChantier6(QuotaServiceTestCase):
    """Ultra n'est plus illimité sur CHAT_MESSAGES (40/j) ni LLM_CALLS (40/j)
    depuis le Chantier 6 — ces deux quotas doivent désormais lever
    QuotaExceededError comme n'importe quel autre palier limité."""

    def test_ultra_chat_messages_leve_au_dela_de_40(self):
        quota_service.consume(self.ultra_user, QuotaType.CHAT_MESSAGES, amount=40)
        with self.assertRaises(QuotaExceededError) as ctx:
            quota_service.consume(self.ultra_user, QuotaType.CHAT_MESSAGES, amount=1)
        self.assertEqual(ctx.exception.limit, 40)

    def test_ultra_llm_calls_leve_au_dela_de_40(self):
        quota_service.consume(self.ultra_user, QuotaType.LLM_CALLS, amount=40)
        with self.assertRaises(QuotaExceededError) as ctx:
            quota_service.consume(self.ultra_user, QuotaType.LLM_CALLS, amount=1)
        self.assertEqual(ctx.exception.limit, 40)

    def test_premium_llm_calls_leve_au_dela_de_20(self):
        quota_service.consume(self.premium_user, QuotaType.LLM_CALLS, amount=20)
        with self.assertRaises(QuotaExceededError) as ctx:
            quota_service.consume(self.premium_user, QuotaType.LLM_CALLS, amount=1)
        self.assertEqual(ctx.exception.limit, 20)


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
        quota_service.consume(self.free_user, QuotaType.CHAT_MESSAGES, amount=15)
        self.assertEqual(quota_service.get_usage(self.free_user, QuotaType.CHAT_MESSAGES), 15)

        # Un autre jour = compteur à 0, aucune tâche de reset à appeler.
        self.assertEqual(
            quota_service.get_usage(self.free_user, QuotaType.CHAT_MESSAGES, day="2020-01-01"), 0
        )

    def test_nouveau_jour_permet_de_nouveau_consume(self):
        quota_service.consume(self.free_user, QuotaType.CHAT_MESSAGES, amount=15)
        with self.assertRaises(QuotaExceededError):
            quota_service.consume(self.free_user, QuotaType.CHAT_MESSAGES, amount=1)

        # Simule le lendemain en insérant directement sur une autre date : le
        # service ne connaît que _today(), donc on vérifie via db.py que la
        # ligne d'hier reste intacte et n'affecte pas un autre jour.
        db.increment_daily_usage(self.free_user["id"], QuotaType.CHAT_MESSAGES.value, "2099-01-01", 1)
        self.assertEqual(
            db.get_daily_usage(self.free_user["id"], QuotaType.CHAT_MESSAGES.value, "2099-01-01"), 1
        )
        self.assertEqual(quota_service.get_usage(self.free_user, QuotaType.CHAT_MESSAGES), 15)


class TestAccesConcurrentSimule(QuotaServiceTestCase):
    def test_consume_concurrent_ne_depasse_jamais_la_limite(self):
        """40 threads tentent chacun de consommer 1 unité d'un quota limité à
        15/jour, simultanément. Le compteur final ne doit jamais dépasser 15,
        et exactement 15 threads doivent réussir (les autres lèvent
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

        self.assertEqual(len(successes), 15)
        self.assertEqual(len(failures), 25)
        self.assertEqual(quota_service.get_usage(self.free_user, QuotaType.CHAT_MESSAGES), 15)

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


class TestExercisesDailyQuota(QuotaServiceTestCase):
    """Chantier "Limitation des exercices par abonnement" (2026-08-26) :
    Free=20/Premium=60/Ultra=illimité sur QuotaType.EXERCISES_DAILY. Ces
    tests couvrent le service pur (câblage réel sur /api/practice/load, voir
    tests/test_exercises_quota_integration.py)."""

    def test_free_peut_consommer_exactement_20(self):
        total = quota_service.consume(self.free_user, QuotaType.EXERCISES_DAILY, amount=20)
        self.assertEqual(total, 20)

    def test_free_21e_leve_quota_exceeded(self):
        quota_service.consume(self.free_user, QuotaType.EXERCISES_DAILY, amount=20)
        with self.assertRaises(QuotaExceededError) as ctx:
            quota_service.consume(self.free_user, QuotaType.EXERCISES_DAILY, amount=1)
        self.assertEqual(ctx.exception.limit, 20)
        self.assertEqual(ctx.exception.required_plan, Plan.PREMIUM)

    def test_free_compteur_reste_a_20_apres_refus(self):
        quota_service.consume(self.free_user, QuotaType.EXERCISES_DAILY, amount=20)
        with self.assertRaises(QuotaExceededError):
            quota_service.consume(self.free_user, QuotaType.EXERCISES_DAILY, amount=1)
        self.assertEqual(quota_service.get_usage(self.free_user, QuotaType.EXERCISES_DAILY), 20)

    def test_premium_peut_consommer_exactement_60(self):
        total = quota_service.consume(self.premium_user, QuotaType.EXERCISES_DAILY, amount=60)
        self.assertEqual(total, 60)

    def test_premium_61e_leve_quota_exceeded(self):
        quota_service.consume(self.premium_user, QuotaType.EXERCISES_DAILY, amount=60)
        with self.assertRaises(QuotaExceededError) as ctx:
            quota_service.consume(self.premium_user, QuotaType.EXERCISES_DAILY, amount=1)
        self.assertEqual(ctx.exception.limit, 60)
        self.assertEqual(ctx.exception.required_plan, Plan.ULTRA)

    def test_ultra_peut_consommer_plus_de_60(self):
        total = quota_service.consume(self.ultra_user, QuotaType.EXERCISES_DAILY, amount=200)
        self.assertEqual(total, 200)

    def test_ultra_est_illimite(self):
        self.assertTrue(quota_service.is_unlimited(self.ultra_user, QuotaType.EXERCISES_DAILY))
        self.assertIsNone(quota_service.get_limit(self.ultra_user, QuotaType.EXERCISES_DAILY))

    def test_nouveau_jour_remet_le_compteur_a_zero(self):
        quota_service.consume(self.free_user, QuotaType.EXERCISES_DAILY, amount=20)
        self.assertEqual(quota_service.get_usage(self.free_user, QuotaType.EXERCISES_DAILY), 20)
        self.assertEqual(
            quota_service.get_usage(self.free_user, QuotaType.EXERCISES_DAILY, day="2020-01-01"), 0
        )

    def test_requete_concurrente_ne_depasse_jamais_la_limite(self):
        successes, failures = [], []
        lock = threading.Lock()

        def worker():
            try:
                quota_service.consume(self.free_user, QuotaType.EXERCISES_DAILY, amount=1)
                with lock:
                    successes.append(1)
            except QuotaExceededError:
                with lock:
                    failures.append(1)

        threads = [threading.Thread(target=worker) for _ in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(successes), 20)
        self.assertEqual(len(failures), 30)
        self.assertEqual(quota_service.get_usage(self.free_user, QuotaType.EXERCISES_DAILY), 20)


class TestAbonnementHtmlNeDivergeJamaisDeQuotaMatrix(unittest.TestCase):
    """Chantier Quotas/IA (audit prioritaire) : webapp/static/abonnement.html
    affiche les limites CHAT_MESSAGES/LLM_CALLS en dur (texte marketing, pas
    lu dynamiquement — voir son propre audit). Garde-fou anti-dérive
    silencieuse : si QUOTA_MATRIX change un jour sans que ce fichier HTML ne
    soit mis à jour, ce test doit casser plutôt que laisser l'utilisateur
    voir une limite fausse."""

    HTML_PATH = Path(__file__).resolve().parent.parent / "static" / "abonnement.html"

    def test_free_chat_messages_affiche_correspond_a_quota_matrix(self):
        html = self.HTML_PATH.read_text(encoding="utf-8")
        limit = QUOTA_MATRIX[Plan.FREE][QuotaType.CHAT_MESSAGES]
        self.assertIn(f"{limit} messages/jour", html)

    def test_premium_chat_messages_affiche_correspond(self):
        # LLM_CALLS (appels IA/jour) n'est plus affiché sur la page client
        # depuis le chantier "Simplification affichage chatbot" (2026-08-27) :
        # seul le nombre de messages chatbot/jour reste visible. QUOTA_MATRIX
        # reste inchangé côté backend (voir test_appels_ia_jour_absent_de_
        # laffichage_client dans test_marketing_coherence.py pour la garantie
        # d'absence).
        html = self.HTML_PATH.read_text(encoding="utf-8")
        chat_limit = QUOTA_MATRIX[Plan.PREMIUM][QuotaType.CHAT_MESSAGES]
        self.assertIn(f"{chat_limit} messages/jour", html)

    def test_ultra_chat_messages_affiche_correspond(self):
        html = self.HTML_PATH.read_text(encoding="utf-8")
        chat_limit = QUOTA_MATRIX[Plan.ULTRA][QuotaType.CHAT_MESSAGES]
        self.assertIn(f"{chat_limit} messages/jour", html)

    def test_free_exercises_daily_affiche_correspond_a_quota_matrix(self):
        html = self.HTML_PATH.read_text(encoding="utf-8")
        limit = QUOTA_MATRIX[Plan.FREE][QuotaType.EXERCISES_DAILY]
        self.assertIn(f"{limit} exercices/jour", html)

    def test_premium_exercises_daily_affiche_correspond_a_quota_matrix(self):
        html = self.HTML_PATH.read_text(encoding="utf-8")
        limit = QUOTA_MATRIX[Plan.PREMIUM][QuotaType.EXERCISES_DAILY]
        self.assertIn(f"{limit} exercices/jour", html)

    def test_ultra_exercises_daily_illimite_affiche(self):
        html = self.HTML_PATH.read_text(encoding="utf-8")
        self.assertIsNone(QUOTA_MATRIX[Plan.ULTRA][QuotaType.EXERCISES_DAILY])
        self.assertIn("Exercices illimités", html)


if __name__ == "__main__":
    unittest.main()
