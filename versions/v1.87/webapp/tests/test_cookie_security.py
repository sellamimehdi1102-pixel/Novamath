"""
Suite Phase 0 (SEC-01) : les cookies posés par auth.py (nm_session, nm_csrf)
et le cookie de session Flask doivent respecter les flags Secure/HttpOnly/
SameSite dérivés de config.py, sans rien coder en dur.
"""
import importlib
import os
import unittest

import auth
import config
import server
from flask import Response


def _reload_config():
    return importlib.reload(config)


class _EnvIsolatedTestCase(unittest.TestCase):
    ENV_VARS = ("FLASK_ENV", "SESSION_COOKIE_SECURE", "REMEMBER_COOKIE_SECURE", "CSRF_COOKIE_SECURE")

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


class TestCookiesEnDeveloppement(_EnvIsolatedTestCase):
    """Comportement actuel (non-régression) : aucun FLASK_ENV positionné."""

    def test_nm_session_pas_secure_mais_httponly_en_dev(self):
        _reload_config()
        resp = Response()
        auth._set_session_cookie(resp, "tok", 30)
        header = resp.headers.get("Set-Cookie", "").lower()
        self.assertNotIn("secure", header)
        self.assertIn("httponly", header)
        self.assertIn("samesite=lax", header)

    def test_nm_csrf_pas_secure_et_pas_httponly_en_dev(self):
        _reload_config()
        resp = Response()
        auth._set_csrf_cookie(resp)
        header = resp.headers.get("Set-Cookie", "").lower()
        self.assertNotIn("secure", header)
        self.assertNotIn("httponly", header)

    def test_endpoint_invite_reel_pose_des_cookies_non_secure(self):
        client = server.app.test_client()
        resp = client.post("/api/auth/guest")
        self.assertEqual(resp.status_code, 201)
        cookies = "\n".join(resp.headers.get_all("Set-Cookie")).lower()
        self.assertIn("nm_session", cookies)
        self.assertIn("nm_csrf", cookies)
        self.assertNotIn("secure", cookies)


class TestCookiesEnProduction(_EnvIsolatedTestCase):
    def test_nm_session_et_nm_csrf_secure_en_production(self):
        os.environ["FLASK_ENV"] = "production"
        _reload_config()
        try:
            resp = Response()
            auth._set_session_cookie(resp, "tok", 30)
            header = resp.headers.get("Set-Cookie", "").lower()
            self.assertIn("secure", header)
            self.assertIn("httponly", header)

            resp2 = Response()
            auth._set_csrf_cookie(resp2)
            header2 = resp2.headers.get("Set-Cookie", "").lower()
            self.assertIn("secure", header2)
        finally:
            _reload_config()


class TestFlaskAppConfig(_EnvIsolatedTestCase):
    def test_app_config_dev_par_defaut_inchange(self):
        self.assertFalse(server.app.config["SESSION_COOKIE_SECURE"])
        self.assertTrue(server.app.config["SESSION_COOKIE_HTTPONLY"])
        self.assertEqual(server.app.config["SESSION_COOKIE_SAMESITE"], "Lax")
        self.assertTrue(server.app.config["DEBUG"])


if __name__ == "__main__":
    unittest.main()
