"""
Suite unitaire de rate_limit_service.py — algorithme de fenêtre glissante
(check()), décorateur @rate_limit, nettoyage (cleanup()), et les fonctions
db.py dédiées (record_rate_limit_event/get_rate_limit_usage/
cleanup_rate_limit_events), le tout isolé de server.py.

Base SQLite isolée dans un répertoire temporaire (db.DATA_DIR/db.DB_PATH
monkeypatchés), même pattern que tests/test_quota_service.py : aucune
interférence avec data/novamath.db. Complète tests/test_server_rate_limits.py
(qui couvre le branchement réel sur les routes Flask) et
tests/test_rate_limit_migration.py (schéma/index).
"""
import shutil
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import db
import rate_limit_service
import server
from rate_limit_service import RateLimitState, check, cleanup, rate_limit


class RateLimitServiceTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp_dir = tempfile.mkdtemp()
        self._data_dir_backup = db.DATA_DIR
        self._db_path_backup = db.DB_PATH
        db.DATA_DIR = Path(self._tmp_dir)
        db.DB_PATH = db.DATA_DIR / "novamath.db"
        db.init_db()

    def tearDown(self):
        db.DATA_DIR = self._data_dir_backup
        db.DB_PATH = self._db_path_backup
        shutil.rmtree(self._tmp_dir, ignore_errors=True)


class TestCheckAutorisationDeBase(RateLimitServiceTestCase):
    def test_autorise_sous_la_limite(self):
        state = check("ip:1.1.1.1", "ep", requests=5, per_seconds=60)
        self.assertTrue(state.allowed)

    def test_refuse_au_dela_de_la_limite(self):
        for _ in range(5):
            check("ip:1.1.1.1", "ep", requests=5, per_seconds=60)
        state = check("ip:1.1.1.1", "ep", requests=5, per_seconds=60)
        self.assertFalse(state.allowed)

    def test_remaining_decroit_a_chaque_appel(self):
        remainings = [check("ip:1.1.1.1", "ep", requests=5, per_seconds=60).remaining for _ in range(5)]
        self.assertEqual(remainings, [4, 3, 2, 1, 0])

    def test_remaining_jamais_negatif(self):
        for _ in range(5):
            check("ip:1.1.1.1", "ep", requests=5, per_seconds=60)
        state = check("ip:1.1.1.1", "ep", requests=5, per_seconds=60)
        self.assertEqual(state.remaining, 0)

    def test_limit_reflete_toujours_la_valeur_demandee(self):
        state = check("ip:1.1.1.1", "ep", requests=7, per_seconds=60)
        self.assertEqual(state.limit, 7)

    def test_requete_refusee_nest_jamais_comptee(self):
        """Une tentative refusée ne doit pas s'ajouter au compteur stocké —
        même philosophie que quota_service.consume() (rien n'est facturé au
        refus). Vérifié en relâchant la limite après coup : le total
        effectivement stocké doit rester égal à `requests`, jamais plus."""
        for _ in range(10):
            check("ip:1.1.1.1", "ep", requests=5, per_seconds=60)
        total, _ = db.get_rate_limit_usage("ip:1.1.1.1", "ep", 0)
        self.assertEqual(total, 5)


class TestRetryAfterEtReset(RateLimitServiceTestCase):
    def test_retry_after_nul_quand_autorise(self):
        state = check("ip:2.2.2.2", "ep", requests=5, per_seconds=60)
        self.assertEqual(state.retry_after, 0)

    def test_retry_after_positif_quand_refuse(self):
        for _ in range(5):
            check("ip:2.2.2.2", "ep", requests=5, per_seconds=60)
        state = check("ip:2.2.2.2", "ep", requests=5, per_seconds=60)
        self.assertGreater(state.retry_after, 0)
        self.assertLessEqual(state.retry_after, 60)

    def test_reset_coherent_avec_retry_after_quand_refuse(self):
        now = int(time.time())
        for _ in range(5):
            check("ip:2.2.2.2", "ep", requests=5, per_seconds=60)
        state = check("ip:2.2.2.2", "ep", requests=5, per_seconds=60)
        self.assertAlmostEqual(state.reset, now + state.retry_after, delta=1)

    def test_precision_retry_after_a_la_seconde_pres(self):
        """La toute première requête fixe le début de fenêtre à `now` ; 10
        secondes plus tard (simulées), il doit rester ~50s avant que cette
        fenêtre de 60s ne se libère — pas un arrondi grossier à la minute."""
        base = 1_000_000
        with patch("rate_limit_service.time.time", return_value=float(base)):
            for _ in range(5):
                check("ip:3.3.3.3", "ep", requests=5, per_seconds=60)
        with patch("rate_limit_service.time.time", return_value=float(base + 10)):
            state = check("ip:3.3.3.3", "ep", requests=5, per_seconds=60)
        self.assertEqual(state.retry_after, 50)


class TestFenetreGlissante(RateLimitServiceTestCase):
    def test_pas_un_reset_calendaire(self):
        """5 requêtes juste avant la limite, puis (à la seconde près) une
        sixième qui doit rester refusée même une fois franchie une frontière
        de minute — la fenêtre glisse en continu, elle ne se remet jamais à
        zéro parce qu'on a changé de minute calendaire."""
        base = 1_000_000  # arbitraire, pas aligné sur une frontière de minute
        with patch("rate_limit_service.time.time", return_value=float(base)):
            for _ in range(5):
                check("ip:4.4.4.4", "ep", requests=5, per_seconds=60)
        with patch("rate_limit_service.time.time", return_value=float(base + 1)):
            state = check("ip:4.4.4.4", "ep", requests=5, per_seconds=60)
        self.assertFalse(state.allowed)

    def test_ancienne_fenetre_sort_naturellement_du_calcul(self):
        base = 2_000_000
        with patch("rate_limit_service.time.time", return_value=float(base)):
            for _ in range(5):
                check("ip:5.5.5.5", "ep", requests=5, per_seconds=60)
        with patch("rate_limit_service.time.time", return_value=float(base + 61)):
            state = check("ip:5.5.5.5", "ep", requests=5, per_seconds=60)
        self.assertTrue(state.allowed)
        self.assertEqual(state.remaining, 4)

    def test_fenetre_glisse_progressivement_pas_tout_ou_rien(self):
        """3 requêtes à t=0, 2 requêtes à t=30 (fenêtre 60s, limite 5) :
        à t=61, seules les 2 de t=30 comptent encore -> 3 places libres,
        jamais 5 (ce que donnerait un reset complet) ni 0."""
        base = 3_000_000
        with patch("rate_limit_service.time.time", return_value=float(base)):
            for _ in range(3):
                check("ip:6.6.6.6", "ep", requests=5, per_seconds=60)
        with patch("rate_limit_service.time.time", return_value=float(base + 30)):
            for _ in range(2):
                check("ip:6.6.6.6", "ep", requests=5, per_seconds=60)
        with patch("rate_limit_service.time.time", return_value=float(base + 61)):
            state = check("ip:6.6.6.6", "ep", requests=5, per_seconds=60)
        self.assertTrue(state.allowed)
        self.assertEqual(state.remaining, 2)


class TestIsolationClesEtEndpoints(RateLimitServiceTestCase):
    def test_deux_endpoints_differents_nont_pas_le_meme_compteur(self):
        for _ in range(5):
            check("ip:7.7.7.7", "endpoint_a", requests=5, per_seconds=60)
        state = check("ip:7.7.7.7", "endpoint_b", requests=5, per_seconds=60)
        self.assertTrue(state.allowed)

    def test_deux_cles_differentes_nont_pas_le_meme_compteur(self):
        for _ in range(5):
            check("ip:8.8.8.8", "ep", requests=5, per_seconds=60)
        state = check("ip:9.9.9.9", "ep", requests=5, per_seconds=60)
        self.assertTrue(state.allowed)

    def test_user_et_ip_ne_collisionnent_jamais_meme_valeur_brute(self):
        for _ in range(5):
            check("user:42", "ep", requests=5, per_seconds=60)
        state = check("ip:42", "ep", requests=5, per_seconds=60)
        self.assertTrue(state.allowed)


class TestIdentityKey(RateLimitServiceTestCase):
    def setUp(self):
        super().setUp()
        self.app = server.app

    def test_utilisateur_connecte_utilise_user_id(self):
        from flask import request as flask_request
        with self.app.test_request_context("/fake"):
            flask_request.current_user = {"id": 77}
            self.assertEqual(rate_limit_service._identity_key(), "user:77")

    def test_anonyme_utilise_lip(self):
        from flask import request as flask_request
        with self.app.test_request_context("/fake", environ_overrides={"REMOTE_ADDR": "203.0.113.9"}):
            self.assertEqual(rate_limit_service._identity_key(), "ip:203.0.113.9")

    def test_x_forwarded_for_prioritaire_sur_remote_addr(self):
        from flask import request as flask_request
        with self.app.test_request_context(
            "/fake",
            headers={"X-Forwarded-For": "198.51.100.7"},
            environ_overrides={"REMOTE_ADDR": "203.0.113.9"},
        ):
            self.assertEqual(rate_limit_service._identity_key(), "ip:198.51.100.7")


class TestDecorateur(RateLimitServiceTestCase):
    def setUp(self):
        super().setUp()
        self.app = server.app
        self._original_enabled = self.app.config.get("RATE_LIMIT_ENABLED")
        self.app.config["RATE_LIMIT_ENABLED"] = True

    def tearDown(self):
        self.app.config["RATE_LIMIT_ENABLED"] = self._original_enabled
        super().tearDown()

    def _decorated(self, requests=3, per_seconds=60, methods=None):
        @rate_limit(requests=requests, per_seconds=per_seconds, methods=methods)
        def view():
            return {"ok": True}, 200
        return view

    def test_laisse_passer_sous_la_limite(self):
        view = self._decorated()
        with self.app.test_request_context("/fake-decorated"):
            resp = view()
        self.assertEqual(resp.status_code, 200)

    def test_renvoie_429_au_dela_de_la_limite(self):
        view = self._decorated(requests=1)
        with self.app.test_request_context("/fake-decorated"):
            view()
            resp = view()
        self.assertEqual(resp.status_code, 429)

    def test_corps_429_au_format_attendu(self):
        view = self._decorated(requests=1)
        with self.app.test_request_context("/fake-decorated"):
            view()
            resp = view()
        body = resp.get_json()
        self.assertEqual(body["error"], "rate_limited")
        self.assertIsInstance(body["retry_after"], int)
        self.assertGreater(body["retry_after"], 0)

    def test_headers_x_ratelimit_limit(self):
        view = self._decorated(requests=3)
        with self.app.test_request_context("/fake-decorated"):
            resp = view()
        self.assertEqual(resp.headers["X-RateLimit-Limit"], "3")

    def test_headers_x_ratelimit_remaining(self):
        view = self._decorated(requests=3)
        with self.app.test_request_context("/fake-decorated"):
            resp = view()
        self.assertEqual(resp.headers["X-RateLimit-Remaining"], "2")

    def test_headers_x_ratelimit_reset_present(self):
        view = self._decorated(requests=3)
        with self.app.test_request_context("/fake-decorated"):
            resp = view()
        self.assertIn("X-RateLimit-Reset", resp.headers)

    def test_header_retry_after_present_si_refuse(self):
        view = self._decorated(requests=1)
        with self.app.test_request_context("/fake-decorated"):
            view()
            resp = view()
        self.assertIn("Retry-After", resp.headers)

    def test_header_retry_after_absent_si_autorise(self):
        view = self._decorated(requests=3)
        with self.app.test_request_context("/fake-decorated"):
            resp = view()
        self.assertNotIn("Retry-After", resp.headers)

    def test_methods_filtre_ignore_les_methodes_non_listees(self):
        view = self._decorated(requests=1, methods={"POST"})
        with self.app.test_request_context("/fake-decorated", method="GET"):
            resp1 = view()
            resp2 = view()
            resp3 = view()
        # GET n'est jamais compté ni bloqué : aucun en-tête de rate limit posé.
        self.assertNotIn("X-RateLimit-Limit", resp1.headers)
        self.assertEqual(resp3.status_code, 200)

    def test_methods_filtre_limite_bien_la_methode_listee(self):
        view = self._decorated(requests=1, methods={"POST"})
        with self.app.test_request_context("/fake-decorated", method="POST"):
            view()
            resp = view()
        self.assertEqual(resp.status_code, 429)

    def test_sans_methods_limite_toutes_les_methodes(self):
        view = self._decorated(requests=1)
        with self.app.test_request_context("/fake-decorated", method="POST"):
            view()
        with self.app.test_request_context("/fake-decorated", method="POST"):
            # Même endpoint (même vue), donc même compteur malgré une requête
            # GET/POST différente au niveau HTTP.
            resp = view()
        self.assertEqual(resp.status_code, 429)

    def test_desactive_par_config_laisse_toujours_passer(self):
        self.app.config["RATE_LIMIT_ENABLED"] = False
        view = self._decorated(requests=1)
        with self.app.test_request_context("/fake-decorated"):
            view()
            resp = view()
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn("X-RateLimit-Limit", resp.headers)

    def test_preserve_le_corps_json_de_la_vue(self):
        view = self._decorated()
        with self.app.test_request_context("/fake-decorated"):
            resp = view()
        self.assertEqual(resp.get_json(), {"ok": True})

    def test_preserve_les_cookies_poses_par_la_vue(self):
        from flask import jsonify

        @rate_limit(requests=3, per_seconds=60)
        def view_with_cookie():
            resp = jsonify({"ok": True})
            resp.set_cookie("test_cookie", "value")
            return resp

        with self.app.test_request_context("/fake-decorated"):
            resp = view_with_cookie()
        self.assertIn("test_cookie=value", resp.headers.get("Set-Cookie", ""))


class TestConcurrence(RateLimitServiceTestCase):
    def test_exactement_n_autorisations_sous_charge_concurrente(self):
        """40 threads tentent chacun une requête sur une limite de 25 —
        exactement 25 doivent être autorisées, 15 refusées, jamais plus ni
        moins (preuve que l'incrément atomique + compensation empêchent tout
        dépassement sous concurrence, même principe que
        test_quota_service.py::test_consume_concurrent_...)."""
        allowed = []
        refused = []
        lock = threading.Lock()

        def worker():
            state = check("ip:concurrent", "ep", requests=25, per_seconds=60)
            with lock:
                (allowed if state.allowed else refused).append(1)

        threads = [threading.Thread(target=worker) for _ in range(40)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(allowed), 25)
        self.assertEqual(len(refused), 15)
        total, _ = db.get_rate_limit_usage("ip:concurrent", "ep", 0)
        self.assertEqual(total, 25)

    def test_cles_differentes_ninterferent_pas_sous_concurrence(self):
        errors = []

        def worker(key):
            for _ in range(10):
                state = check(key, "ep", requests=10, per_seconds=60)
                if not state.allowed:
                    errors.append((key, state))

        threads = [
            threading.Thread(target=worker, args=("ip:c1",)),
            threading.Thread(target=worker, args=("ip:c2",)),
            threading.Thread(target=worker, args=("ip:c3",)),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(errors, [])


class TestCleanup(RateLimitServiceTestCase):
    def test_supprime_les_fenetres_expirees(self):
        base = 4_000_000
        with patch("rate_limit_service.time.time", return_value=float(base)):
            check("ip:old", "ep", requests=5, per_seconds=60)
        with patch("rate_limit_service.time.time", return_value=float(base + 7200)):
            deleted = cleanup(older_than_seconds=3600)
        self.assertEqual(deleted, 1)
        total, _ = db.get_rate_limit_usage("ip:old", "ep", 0)
        self.assertEqual(total, 0)

    def test_conserve_les_fenetres_recentes(self):
        base = 5_000_000
        with patch("rate_limit_service.time.time", return_value=float(base)):
            check("ip:recent", "ep", requests=5, per_seconds=60)
        with patch("rate_limit_service.time.time", return_value=float(base + 10)):
            deleted = cleanup(older_than_seconds=3600)
        self.assertEqual(deleted, 0)
        total, _ = db.get_rate_limit_usage("ip:recent", "ep", 0)
        self.assertEqual(total, 1)

    def test_idempotent(self):
        base = 6_000_000
        with patch("rate_limit_service.time.time", return_value=float(base)):
            check("ip:idem", "ep", requests=5, per_seconds=60)
        with patch("rate_limit_service.time.time", return_value=float(base + 7200)):
            first = cleanup(older_than_seconds=3600)
            second = cleanup(older_than_seconds=3600)
        self.assertEqual(first, 1)
        self.assertEqual(second, 0)

    def test_sans_rien_a_supprimer_renvoie_zero(self):
        self.assertEqual(cleanup(older_than_seconds=3600), 0)

    def test_ne_supprime_pas_au_dela_du_necessaire(self):
        """Deux clés distinctes, une seule expirée : cleanup() ne doit
        supprimer que la fenêtre réellement périmée."""
        base = 7_000_000
        with patch("rate_limit_service.time.time", return_value=float(base)):
            check("ip:expired", "ep", requests=5, per_seconds=60)
        with patch("rate_limit_service.time.time", return_value=float(base + 7200)):
            check("ip:fresh", "ep", requests=5, per_seconds=60)
            deleted = cleanup(older_than_seconds=3600)
        self.assertEqual(deleted, 1)
        total_fresh, _ = db.get_rate_limit_usage("ip:fresh", "ep", 0)
        self.assertEqual(total_fresh, 1)


class TestDbLayer(RateLimitServiceTestCase):
    def test_record_rate_limit_event_incremente(self):
        total = db.record_rate_limit_event("k", "ep", 1000, amount=1)
        self.assertEqual(total, 1)
        total = db.record_rate_limit_event("k", "ep", 1000, amount=1)
        self.assertEqual(total, 2)

    def test_record_rate_limit_event_amount_negatif_decremente(self):
        db.record_rate_limit_event("k", "ep", 1000, amount=1)
        total = db.record_rate_limit_event("k", "ep", 1000, amount=-1)
        self.assertEqual(total, 0)

    def test_get_rate_limit_usage_somme_plusieurs_buckets(self):
        db.record_rate_limit_event("k", "ep", 1000, amount=1)
        db.record_rate_limit_event("k", "ep", 1001, amount=1)
        db.record_rate_limit_event("k", "ep", 1002, amount=1)
        total, oldest = db.get_rate_limit_usage("k", "ep", 0)
        self.assertEqual(total, 3)
        self.assertEqual(oldest, 1000)

    def test_get_rate_limit_usage_ignore_les_buckets_hors_fenetre(self):
        db.record_rate_limit_event("k", "ep", 100, amount=1)
        db.record_rate_limit_event("k", "ep", 2000, amount=1)
        total, oldest = db.get_rate_limit_usage("k", "ep", 1000)
        self.assertEqual(total, 1)
        self.assertEqual(oldest, 2000)

    def test_get_rate_limit_usage_vide_renvoie_zero_et_none(self):
        total, oldest = db.get_rate_limit_usage("aucun", "ep", 0)
        self.assertEqual(total, 0)
        self.assertIsNone(oldest)

    def test_cleanup_rate_limit_events_renvoie_le_nombre_supprime(self):
        db.record_rate_limit_event("k1", "ep", 100, amount=1)
        db.record_rate_limit_event("k2", "ep", 200, amount=1)
        db.record_rate_limit_event("k3", "ep", 5000, amount=1)
        deleted = db.cleanup_rate_limit_events(1000)
        self.assertEqual(deleted, 2)


if __name__ == "__main__":
    unittest.main()
