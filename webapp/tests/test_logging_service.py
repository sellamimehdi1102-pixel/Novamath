"""
Suite de logging_service.py : formatage structuré (StructuredFormatter),
enrichissement contextuel (_ContextFilter), configuration (configure_logging/
configure_sentry), capture d'exception (capture_exception), et le middleware
Flask (init_app) — durée de requête, journal de fin de requête, panic log
(Partie 6), passthrough des HTTPException.

Utilise une mini-application Flask autonome (jamais `server.app`, trop lourde
et déjà couverte par tests/test_server_observability.py) — même technique que
tests/test_role_service.py::TestRequiresRoleDecorator et
tests/test_rate_limit_service.py::TestDecorateur.
"""
import json
import logging
import os
import unittest
from unittest.mock import MagicMock, patch

from flask import Flask, abort, jsonify

import logging_service
import metrics_service
from logging_service import StructuredFormatter, _ContextFilter


def _make_record(msg="hello", level=logging.INFO):
    return logging.LogRecord(
        name="test.module", level=level, pathname=__file__, lineno=1,
        msg=msg, args=(), exc_info=None,
    )


class TestStructuredFormatterDev(unittest.TestCase):
    def setUp(self):
        self.formatter = StructuredFormatter(json_output=False)

    def test_ligne_lisible_contient_le_message(self):
        line = self.formatter.format(_make_record("un message clair"))
        self.assertIn("un message clair", line)

    def test_ligne_contient_le_niveau(self):
        line = self.formatter.format(_make_record(level=logging.WARNING))
        self.assertIn("WARNING", line)

    def test_ligne_contient_le_module(self):
        line = self.formatter.format(_make_record())
        self.assertIn("test.module", line)

    def test_valeurs_par_defaut_absentes_du_contexte(self):
        line = self.formatter.format(_make_record())
        self.assertIn("user=-", line)
        self.assertIn("ip=-", line)
        self.assertIn("request=-", line)
        self.assertIn("duration_ms=-", line)

    def test_champs_enrichis_apparaissent(self):
        record = _make_record()
        record.user = 42
        record.ip = "203.0.113.4"
        record.request = "GET /api/x"
        record.duration_ms = 12.5
        line = self.formatter.format(record)
        self.assertIn("user=42", line)
        self.assertIn("ip=203.0.113.4", line)
        self.assertIn("request=GET /api/x", line)
        self.assertIn("duration_ms=12.5", line)

    def test_exception_incluse_si_presente(self):
        try:
            raise ValueError("boom")
        except ValueError:
            import sys
            record = logging.LogRecord(
                name="test.module", level=logging.ERROR, pathname=__file__, lineno=1,
                msg="erreur", args=(), exc_info=sys.exc_info(),
            )
        line = self.formatter.format(record)
        self.assertIn("ValueError: boom", line)


class TestStructuredFormatterJson(unittest.TestCase):
    def setUp(self):
        self.formatter = StructuredFormatter(json_output=True)

    def test_sortie_est_un_json_valide(self):
        line = self.formatter.format(_make_record("message json"))
        payload = json.loads(line)
        self.assertEqual(payload["message"], "message json")

    def test_contient_tous_les_champs_minimaux(self):
        record = _make_record()
        record.user = 7
        record.ip = "1.2.3.4"
        record.request = "POST /api/y"
        record.duration_ms = 3.1
        payload = json.loads(self.formatter.format(record))
        for field in ("timestamp", "level", "module", "user", "ip", "request", "duration_ms", "message"):
            self.assertIn(field, payload)

    def test_timestamp_est_iso8601(self):
        payload = json.loads(self.formatter.format(_make_record()))
        # Ne doit pas lever : preuve que c'est un ISO 8601 valide.
        from datetime import datetime
        datetime.fromisoformat(payload["timestamp"])


class TestContextFilter(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.filter = _ContextFilter()

    def test_hors_contexte_de_requete_valeurs_par_defaut(self):
        record = _make_record()
        self.filter.filter(record)
        self.assertEqual(record.user, "-")
        self.assertEqual(record.ip, "-")
        self.assertEqual(record.request, "-")

    def test_dans_le_contexte_anonyme_utilise_lip(self):
        with self.app.test_request_context("/x", environ_overrides={"REMOTE_ADDR": "198.51.100.3"}):
            record = _make_record()
            self.filter.filter(record)
            self.assertEqual(record.user, "-")
            self.assertEqual(record.ip, "198.51.100.3")
            self.assertEqual(record.request, "GET /x")

    def test_dans_le_contexte_connecte_utilise_luser_id(self):
        from flask import request as flask_request
        with self.app.test_request_context("/x"):
            flask_request.current_user = {"id": 99}
            record = _make_record()
            self.filter.filter(record)
            self.assertEqual(record.user, 99)

    def test_ne_reecrase_pas_une_duration_ms_deja_fournie(self):
        record = _make_record()
        record.duration_ms = 42.0
        self.filter.filter(record)
        self.assertEqual(record.duration_ms, 42.0)

    def test_filter_ne_leve_jamais(self):
        record = _make_record()
        self.assertTrue(self.filter.filter(record))


class TestConfigureLogging(unittest.TestCase):
    def tearDown(self):
        # Restaure un état propre pour ne pas polluer le reste de la suite
        # (les autres fichiers de tests s'attendent à pouvoir logger sans lever).
        logging_service.configure_logging()

    def test_idempotent_pas_de_handlers_dupliques(self):
        logging_service.configure_logging()
        logging_service.configure_logging()
        logging_service.configure_logging()
        root = logging.getLogger()
        self.assertEqual(len(root.handlers), 1)

    def test_niveau_lu_depuis_log_level(self):
        with patch.dict(os.environ, {"LOG_LEVEL": "WARNING"}):
            import importlib
            import config
            importlib.reload(config)
            importlib.reload(logging_service)
            logging_service.configure_logging()
            self.assertEqual(logging.getLogger().level, logging.WARNING)
        importlib.reload(config)
        importlib.reload(logging_service)

    def test_handler_a_un_formatter_et_un_filtre(self):
        root = logging_service.configure_logging()
        handler = root.handlers[0]
        self.assertIsInstance(handler.formatter, StructuredFormatter)
        self.assertTrue(any(isinstance(f, _ContextFilter) for f in handler.filters))


class TestConfigureSentry(unittest.TestCase):
    def setUp(self):
        self._saved_dsn = os.environ.get("SENTRY_DSN")

    def tearDown(self):
        if self._saved_dsn is None:
            os.environ.pop("SENTRY_DSN", None)
        else:
            os.environ["SENTRY_DSN"] = self._saved_dsn
        self._reload_config()
        logging_service.configure_sentry()

    def _reload_config(self):
        import importlib
        import config
        importlib.reload(config)
        importlib.reload(logging_service)

    def test_sans_sentry_dsn_desactive_et_ne_leve_pas(self):
        os.environ.pop("SENTRY_DSN", None)
        self._reload_config()
        result = logging_service.configure_sentry()
        self.assertFalse(result)
        self.assertFalse(logging_service.sentry_enabled())

    def test_avec_sentry_dsn_et_paquet_installe_active(self):
        os.environ["SENTRY_DSN"] = "https://fake@example.ingest.sentry.io/1"
        self._reload_config()
        with patch("sentry_sdk.init") as mock_init:
            result = logging_service.configure_sentry()
        self.assertTrue(result)
        self.assertTrue(logging_service.sentry_enabled())
        mock_init.assert_called_once()
        self.assertEqual(mock_init.call_args.kwargs["dsn"], "https://fake@example.ingest.sentry.io/1")

    def test_paquet_sentry_absent_desactive_sans_lever(self):
        os.environ["SENTRY_DSN"] = "https://fake@example.ingest.sentry.io/1"
        self._reload_config()
        with patch.dict("sys.modules", {"sentry_sdk": None}):
            result = logging_service.configure_sentry()
        self.assertFalse(result)
        self.assertFalse(logging_service.sentry_enabled())


class TestCaptureException(unittest.TestCase):
    def setUp(self):
        self._saved_dsn = os.environ.get("SENTRY_DSN")
        os.environ.pop("SENTRY_DSN", None)
        import importlib
        import config
        importlib.reload(config)
        importlib.reload(logging_service)

    def tearDown(self):
        if self._saved_dsn is None:
            os.environ.pop("SENTRY_DSN", None)
        else:
            os.environ["SENTRY_DSN"] = self._saved_dsn
        import importlib
        import config
        importlib.reload(config)
        importlib.reload(logging_service)

    def test_journalise_toujours_meme_sans_sentry(self):
        with self.assertLogs("logging_service", level="ERROR") as ctx:
            logging_service.capture_exception(ValueError("panne"))
        self.assertTrue(any("panne" in line for line in ctx.output))

    def test_appelle_sentry_si_actif(self):
        logging_service._sentry_enabled = True
        try:
            with patch("sentry_sdk.capture_exception") as mock_capture:
                logging_service.capture_exception(ValueError("panne sentry"))
            mock_capture.assert_called_once()
        finally:
            logging_service._sentry_enabled = False

    def test_najoute_pas_sentry_si_inactif(self):
        with patch("sentry_sdk.capture_exception") as mock_capture:
            logging_service.capture_exception(ValueError("sans sentry"))
        mock_capture.assert_not_called()


class TestInitAppMiddleware(unittest.TestCase):
    def _build_app(self, debug):
        app = Flask(__name__)
        app.config["DEBUG"] = debug
        app.testing = False

        @app.route("/ok")
        def ok():
            return jsonify({"ok": True})

        @app.route("/boom")
        def boom():
            raise ValueError("kaboom")

        @app.route("/not-found")
        def not_found():
            abort(404)

        logging_service.init_app(app)
        return app

    def setUp(self):
        metrics_service.reset()

    def test_route_normale_repond_200(self):
        app = self._build_app(debug=False)
        resp = app.test_client().get("/ok")
        self.assertEqual(resp.status_code, 200)

    def test_route_normale_incremente_les_metriques(self):
        app = self._build_app(debug=False)
        app.test_client().get("/ok")
        snap = metrics_service.in_memory_snapshot()
        self.assertEqual(snap["total_requests"], 1)
        self.assertEqual(snap["total_errors"], 0)

    def test_httpexception_nest_pas_traitee_comme_une_panique(self):
        app = self._build_app(debug=False)
        resp = app.test_client().get("/not-found")
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(metrics_service.in_memory_snapshot()["total_errors"], 0)

    def test_exception_non_geree_en_debug_est_relevee(self):
        app = self._build_app(debug=True)
        with self.assertRaises(ValueError):
            app.test_client().get("/boom")
        self.assertEqual(metrics_service.in_memory_snapshot()["total_errors"], 1)

    def test_exception_non_geree_hors_debug_renvoie_500_json_propre(self):
        app = self._build_app(debug=False)
        resp = app.test_client().get("/boom")
        self.assertEqual(resp.status_code, 500)
        body = resp.get_json()
        self.assertEqual(body, {"error": "Une erreur interne est survenue."})
        self.assertNotIn("kaboom", resp.get_data(as_text=True))

    def test_exception_non_geree_incremente_les_metriques(self):
        app = self._build_app(debug=False)
        app.test_client().get("/boom")
        self.assertEqual(metrics_service.in_memory_snapshot()["total_errors"], 1)

    def test_exception_non_geree_est_journalisee(self):
        app = self._build_app(debug=False)
        with self.assertLogs("logging_service", level="ERROR") as ctx:
            app.test_client().get("/boom")
        self.assertTrue(any("kaboom" in line for line in ctx.output))

    def test_exception_non_geree_appelle_sentry_si_actif(self):
        app = self._build_app(debug=False)
        logging_service._sentry_enabled = True
        try:
            with patch("sentry_sdk.capture_exception") as mock_capture:
                app.test_client().get("/boom")
            mock_capture.assert_called_once()
        finally:
            logging_service._sentry_enabled = False


if __name__ == "__main__":
    unittest.main()
