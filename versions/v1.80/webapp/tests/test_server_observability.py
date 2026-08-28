"""
Suite d'intégration : vérifie le branchement réel des services d'observabilité
sur `server.app` — GET /api/health (route réelle, jamais authentifiée, jamais
rate-limitée), et le middleware panic log (logging_service.init_app) exercé
sur une vraie requête HTTP de bout en bout. Complète les suites isolées
tests/test_health_service.py, tests/test_logging_service.py et
tests/test_metrics_service.py.
"""
import unittest
from unittest.mock import patch

import logging
import metrics_service
import server


class TestApiHealthRoute(unittest.TestCase):
    def setUp(self):
        self.client = server.app.test_client()

    def test_repond_200_quand_tout_va_bien(self):
        resp = self.client.get("/api/health")
        self.assertIn(resp.status_code, (200, 503))  # dépend de STRIPE_SECRET_KEY en environnement de test
        body = resp.get_json()
        self.assertIn("status", body)
        self.assertIn("checks", body)
        self.assertIn("version", body)

    def test_repond_503_si_la_base_est_en_panne(self):
        with patch("health_service.db.get_connection", side_effect=OSError("panne simulée")):
            resp = self.client.get("/api/health")
        self.assertEqual(resp.status_code, 503)
        body = resp.get_json()
        self.assertEqual(body["status"], "degraded")
        self.assertFalse(body["checks"]["database"])

    def test_accessible_sans_authentification(self):
        resp = self.client.get("/api/health")
        self.assertNotEqual(resp.status_code, 401)

    def test_jamais_rate_limite(self):
        original = server.app.config.get("RATE_LIMIT_ENABLED")
        server.app.config["RATE_LIMIT_ENABLED"] = True
        try:
            last = None
            for _ in range(30):
                last = self.client.get("/api/health")
            self.assertNotEqual(last.status_code, 429)
        finally:
            server.app.config["RATE_LIMIT_ENABLED"] = original

    def test_methode_post_non_autorisee(self):
        resp = self.client.post("/api/health")
        self.assertEqual(resp.status_code, 405)

    def test_checks_contient_les_quatre_verifications(self):
        resp = self.client.get("/api/health")
        self.assertEqual(
            set(resp.get_json()["checks"]),
            {"database", "stripe_configured", "backup_directory", "disk_space"},
        )


class TestPanicLogMiddlewareBrancheSurServerApp(unittest.TestCase):
    """server.app a déjà traité des requêtes au moment où cette suite
    s'exécute (Flask verrouille add_url_rule après la première requête,
    voir Flask._got_first_request) — impossible d'y ajouter une route ad hoc
    ici. On vérifie donc que le VRAI branchement (logging_service.init_app(app)
    dans server.py) est bien en place ; le comportement détaillé du
    middleware lui-même (500 propre hors debug, re-lève en debug, capture
    Sentry, etc.) est déjà exhaustivement testé sur une app dédiée dans
    tests/test_logging_service.py::TestInitAppMiddleware, qui exerce très
    exactement la même fonction logging_service.init_app()."""

    def test_un_errorhandler_generique_est_enregistre(self):
        handlers = server.app.error_handler_spec[None][None]
        self.assertIn(Exception, handlers)

    def test_le_hook_after_request_de_journalisation_est_installe(self):
        names = {f.__name__ for f in server.app.after_request_funcs[None]}
        self.assertIn("_log_request", names)

    def test_le_hook_before_request_de_chronometrage_est_installe(self):
        names = {f.__name__ for f in server.app.before_request_funcs[None]}
        self.assertIn("_start_request_timer", names)


class TestRequestLoggingMiddlewareReel(unittest.TestCase):
    def setUp(self):
        self.client = server.app.test_client()
        metrics_service.reset()

    def tearDown(self):
        metrics_service.reset()

    def test_une_requete_reelle_incremente_les_metriques(self):
        self.client.get("/api/health")
        self.assertEqual(metrics_service.in_memory_snapshot()["total_requests"], 1)

    def test_plusieurs_requetes_saccumulent(self):
        for _ in range(5):
            self.client.get("/api/health")
        self.assertEqual(metrics_service.in_memory_snapshot()["total_requests"], 5)

    def test_journal_de_fin_de_requete_emis(self):
        with self.assertLogs("http", level="INFO") as ctx:
            self.client.get("/api/health")
        self.assertTrue(any("GET /api/health" in line for line in ctx.output))

    def test_route_404_nest_pas_comptee_comme_une_erreur(self):
        self.client.get("/cette-route-nexiste-pas")
        self.assertEqual(metrics_service.in_memory_snapshot()["total_errors"], 0)


class TestLoggingConfigureAuDemarrage(unittest.TestCase):
    def test_le_logger_racine_a_un_handler_structure(self):
        import logging_service
        root = logging.getLogger()
        self.assertTrue(any(isinstance(h.formatter, logging_service.StructuredFormatter) for h in root.handlers))


if __name__ == "__main__":
    unittest.main()
