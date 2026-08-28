"""
Suite Phase 0 (passage en production) : vérifie que FLASK_ENV pilote bien
debug/cookies sans rien coder en dur (SEC-01, ARCH-01) et sans changer le
comportement par défaut (développement).
"""
import importlib
import os
import unittest

import config


def _reload_config():
    return importlib.reload(config)


class _EnvIsolatedTestCase(unittest.TestCase):
    """Sauvegarde/restaure les variables d'environnement touchées par un test
    et recharge `config` après coup pour ne pas polluer les autres tests."""

    ENV_VARS = (
        "FLASK_ENV",
        "FLASK_DEBUG",
        "SESSION_COOKIE_SECURE",
        "REMEMBER_COOKIE_SECURE",
        "CSRF_COOKIE_SECURE",
        "SESSION_COOKIE_HTTPONLY",
        "SESSION_COOKIE_SAMESITE",
    )

    def setUp(self):
        self._saved = {name: os.environ.get(name) for name in self.ENV_VARS}
        for name in self.ENV_VARS:
            os.environ.pop(name, None)

    def tearDown(self):
        for name, value in self._saved.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        _reload_config()


class TestConfigDeveloppementParDefaut(_EnvIsolatedTestCase):
    def test_sans_flask_env_le_comportement_actuel_est_preserve(self):
        mod = _reload_config()
        self.assertEqual(mod.FLASK_ENV, "development")
        self.assertFalse(mod.IS_PRODUCTION)
        self.assertTrue(mod.DEBUG)
        self.assertFalse(mod.SESSION_COOKIE_SECURE)
        self.assertFalse(mod.REMEMBER_COOKIE_SECURE)
        self.assertFalse(mod.CSRF_COOKIE_SECURE)
        self.assertTrue(mod.SESSION_COOKIE_HTTPONLY)
        self.assertEqual(mod.SESSION_COOKIE_SAMESITE, "Lax")


class TestConfigProduction(_EnvIsolatedTestCase):
    def test_flask_env_production_active_debug_false_et_cookies_secure(self):
        os.environ["FLASK_ENV"] = "production"
        mod = _reload_config()
        self.assertTrue(mod.IS_PRODUCTION)
        self.assertFalse(mod.DEBUG)
        self.assertTrue(mod.SESSION_COOKIE_SECURE)
        self.assertTrue(mod.REMEMBER_COOKIE_SECURE)
        self.assertTrue(mod.CSRF_COOKIE_SECURE)

    def test_flask_env_insensible_a_la_casse(self):
        os.environ["FLASK_ENV"] = "Production"
        mod = _reload_config()
        self.assertTrue(mod.IS_PRODUCTION)


class TestSurchargesIndividuelles(_EnvIsolatedTestCase):
    def test_secure_individuel_surcharge_flask_env_development(self):
        os.environ["SESSION_COOKIE_SECURE"] = "true"
        mod = _reload_config()
        self.assertFalse(mod.IS_PRODUCTION)
        self.assertTrue(mod.SESSION_COOKIE_SECURE)
        # Les autres flags restent dérivés du dev par défaut.
        self.assertFalse(mod.REMEMBER_COOKIE_SECURE)
        self.assertFalse(mod.CSRF_COOKIE_SECURE)

    def test_debug_peut_etre_force_off_en_dev(self):
        os.environ["FLASK_DEBUG"] = "false"
        mod = _reload_config()
        self.assertFalse(mod.IS_PRODUCTION)
        self.assertFalse(mod.DEBUG)

    def test_samesite_personnalise(self):
        os.environ["SESSION_COOKIE_SAMESITE"] = "Strict"
        mod = _reload_config()
        self.assertEqual(mod.SESSION_COOKIE_SAMESITE, "Strict")


if __name__ == "__main__":
    unittest.main()
