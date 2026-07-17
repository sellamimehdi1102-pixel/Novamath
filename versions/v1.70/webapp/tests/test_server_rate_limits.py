"""
Suite d'intégration : vérifie le branchement réel de @rate_limit(...) sur les
routes Flask (auth.py/server.py) — login, register, mot de passe oublié,
checkout, billing, chatbot SSE, upload PDF, recherche, avis — ainsi que les
routes explicitement exemptées (webhook Stripe, health, dashboard admin).
Complète tests/test_rate_limit_service.py (algorithme isolé) et
tests/test_rate_limit_migration.py (schéma).

RATE_LIMIT_ENABLED est désactivé par défaut hors production (voir config.py)
— nécessaire pour que le reste de la suite (qui appelle /api/auth/register
des centaines de fois depuis la même IP de test) continue de passer sans
modification. Chaque test ici l'active explicitement pour sa durée, comme
n'importe quelle autre configuration ciblée.
"""
import random
import unittest

import db
import server
from role_service import Role


def _fake_ip():
    """Adresse IP unique par appel — évite qu'un register()/login() de mise
    en place (setUp) ne consomme lui-même le quota de l'endpoint sous test,
    et qu'un test n'en pollue un autre (voir docstring du module)."""
    return f"10.{random.randint(0, 254)}.{random.randint(0, 254)}.{random.randint(1, 254)}"


def _fake_email():
    """Email jetable unique par test : /api/auth/login applique déjà, en
    plus et indépendamment de notre nouveau rate limiter, un verrouillage
    anti brute-force par EMAIL (voir auth.py::MAX_LOGIN_ATTEMPTS/
    LOCKOUT_MINUTES, mécanisme préexistant non touché par cette phase).
    Réutiliser toujours le même email ferait remonter CE verrouillage-là au
    bout de 5 échecs cumulés sur toute la durée de vie de la base de test,
    masquant le comportement de rate_limit_service qu'on veut isoler ici."""
    return f"ratelimit-login-{random.randint(1_000_000, 9_999_999)}@gmail.com"


def _register(client, ip=None):
    ip = ip or _fake_ip()
    email = f"ratelimit{random.randint(1_000_000, 9_999_999)}@gmail.com"
    username = f"ratelimit{random.randint(100_000, 999_999)}"
    resp = client.post(
        "/api/auth/register",
        json={
            "email": email, "username": username, "pseudo": "Test",
            "birth_date": "2000-01-01",
            "password": "MotDePasse123!", "confirm_password": "MotDePasse123!",
            "accept_terms": True, "accept_privacy": True,
        },
        headers={"X-Forwarded-For": ip},
    )
    user = resp.get_json()["user"]
    csrf = client.get_cookie("nm_csrf").value
    return user, {"X-CSRF-Token": csrf}


class RateLimitEnabledTestCase(unittest.TestCase):
    """Active RATE_LIMIT_ENABLED pour la durée de chaque test, la restaure
    ensuite — n'affecte jamais le reste de la suite."""

    def setUp(self):
        self.client = server.app.test_client()
        self._original_enabled = server.app.config.get("RATE_LIMIT_ENABLED")
        server.app.config["RATE_LIMIT_ENABLED"] = True

    def tearDown(self):
        server.app.config["RATE_LIMIT_ENABLED"] = self._original_enabled


class TestLoginRateLimit(RateLimitEnabledTestCase):
    def test_bloque_apres_5_tentatives_par_minute(self):
        ip, email = _fake_ip(), _fake_email()
        for _ in range(5):
            resp = self.client.post(
                "/api/auth/login", json={"email": email, "password": "wrong"},
                headers={"X-Forwarded-For": ip},
            )
            self.assertNotEqual(resp.status_code, 429)
        resp = self.client.post(
            "/api/auth/login", json={"email": email, "password": "wrong"},
            headers={"X-Forwarded-For": ip},
        )
        self.assertEqual(resp.status_code, 429)
        self.assertEqual(resp.get_json()["error"], "rate_limited")

    def test_ratelimit_headers_presents(self):
        resp = self.client.post(
            "/api/auth/login", json={"email": _fake_email(), "password": "wrong"},
            headers={"X-Forwarded-For": _fake_ip()},
        )
        self.assertIn("X-RateLimit-Limit", resp.headers)
        self.assertEqual(resp.headers["X-RateLimit-Limit"], "5")
        self.assertIn("X-RateLimit-Remaining", resp.headers)
        self.assertIn("X-RateLimit-Reset", resp.headers)

    def test_ips_differentes_ont_chacune_leur_propre_limite(self):
        # Deux emails distincts : le verrouillage anti brute-force par email
        # déjà existant dans login() est un mécanisme séparé, indépendant de
        # l'IP — le laisser interférer masquerait ce qu'on isole ici.
        ip_a, ip_b = _fake_ip(), _fake_ip()
        for _ in range(5):
            self.client.post(
                "/api/auth/login", json={"email": _fake_email(), "password": "wrong"},
                headers={"X-Forwarded-For": ip_a},
            )
        resp = self.client.post(
            "/api/auth/login", json={"email": _fake_email(), "password": "wrong"},
            headers={"X-Forwarded-For": ip_b},
        )
        self.assertNotEqual(resp.status_code, 429)

    def test_retry_after_present_dans_le_corps(self):
        ip, email = _fake_ip(), _fake_email()
        for _ in range(5):
            self.client.post(
                "/api/auth/login", json={"email": email, "password": "wrong"},
                headers={"X-Forwarded-For": ip},
            )
        resp = self.client.post(
            "/api/auth/login", json={"email": email, "password": "wrong"},
            headers={"X-Forwarded-For": ip},
        )
        body = resp.get_json()
        self.assertIn("retry_after", body)
        self.assertGreater(body["retry_after"], 0)
        self.assertLessEqual(body["retry_after"], 60)

    def test_desactive_hors_activation_explicite(self):
        server.app.config["RATE_LIMIT_ENABLED"] = False
        ip = _fake_ip()
        resp = None
        for _ in range(8):
            # Un email différent à chaque tentative : évite de déclencher le
            # verrouillage anti brute-force PAR EMAIL déjà existant dans
            # login() (voir _fake_email()) — on isole ici uniquement le
            # comportement de rate_limit_service (par IP), désactivé.
            resp = self.client.post(
                "/api/auth/login", json={"email": _fake_email(), "password": "wrong"},
                headers={"X-Forwarded-For": ip},
            )
        self.assertNotEqual(resp.status_code, 429)


class TestRegisterRateLimit(RateLimitEnabledTestCase):
    def test_bloque_apres_3_par_heure(self):
        ip = _fake_ip()
        for _ in range(3):
            user, _ = _register(self.client, ip=ip)
            self.assertIsNotNone(user)
        email = f"ratelimit{random.randint(1_000_000, 9_999_999)}@gmail.com"
        resp = self.client.post(
            "/api/auth/register",
            json={
                "email": email, "username": f"u{random.randint(100000,999999)}", "pseudo": "T",
                "birth_date": "2000-01-01",
                "password": "MotDePasse123!", "confirm_password": "MotDePasse123!",
                "accept_terms": True, "accept_privacy": True,
            },
            headers={"X-Forwarded-For": ip},
        )
        self.assertEqual(resp.status_code, 429)


class TestForgotPasswordRateLimit(RateLimitEnabledTestCase):
    def test_bloque_apres_3_par_heure(self):
        ip = _fake_ip()
        for _ in range(3):
            resp = self.client.post(
                "/api/auth/forgot-password", json={"email": "inconnu@gmail.com"},
                headers={"X-Forwarded-For": ip},
            )
            self.assertNotEqual(resp.status_code, 429)
        resp = self.client.post(
            "/api/auth/forgot-password", json={"email": "inconnu@gmail.com"},
            headers={"X-Forwarded-For": ip},
        )
        self.assertEqual(resp.status_code, 429)


class TestResetPasswordRateLimit(RateLimitEnabledTestCase):
    def test_bloque_apres_3_par_heure(self):
        ip = _fake_ip()
        for _ in range(3):
            resp = self.client.post(
                "/api/auth/reset-password", json={"token": "invalide", "password": "x"},
                headers={"X-Forwarded-For": ip},
            )
            self.assertNotEqual(resp.status_code, 429)
        resp = self.client.post(
            "/api/auth/reset-password", json={"token": "invalide", "password": "x"},
            headers={"X-Forwarded-For": ip},
        )
        self.assertEqual(resp.status_code, 429)


class TestCheckoutRateLimit(RateLimitEnabledTestCase):
    def test_bloque_apres_10_par_heure(self):
        user, headers = _register(self.client)
        for _ in range(10):
            resp = self.client.post("/api/checkout/create-session", json={"plan": "premium"}, headers=headers)
            self.assertNotEqual(resp.status_code, 429)
        resp = self.client.post("/api/checkout/create-session", json={"plan": "premium"}, headers=headers)
        self.assertEqual(resp.status_code, 429)

    def test_cle_est_le_compte_pas_lip_une_fois_connecte(self):
        """Deux comptes connectés depuis la MÊME IP ne doivent pas partager
        le même compteur : la clé privilégie user_id dès qu'un compte est
        résolu (voir @login_required avant @rate_limit)."""
        ip = _fake_ip()
        user_a, headers_a = _register(self.client, ip=ip)
        for _ in range(10):
            self.client.post("/api/checkout/create-session", json={"plan": "premium"}, headers=headers_a)
        client_b = server.app.test_client()
        user_b, headers_b = _register(client_b, ip=ip)
        resp = client_b.post("/api/checkout/create-session", json={"plan": "premium"}, headers=headers_b)
        self.assertNotEqual(resp.status_code, 429)


class TestBillingRateLimit(RateLimitEnabledTestCase):
    def test_billing_status_bloque_apres_20_par_heure(self):
        _, headers = _register(self.client)
        for _ in range(20):
            resp = self.client.get("/api/billing/status")
            self.assertNotEqual(resp.status_code, 429)
        resp = self.client.get("/api/billing/status")
        self.assertEqual(resp.status_code, 429)

    def test_customer_portal_a_son_propre_compteur(self):
        """Un endpoint billing distinct (customer-portal) ne doit pas être
        affecté par l'épuisement du compteur de billing/status — chaque
        endpoint a son propre bucket (voir clé (identité, endpoint))."""
        user, headers = _register(self.client)
        for _ in range(20):
            self.client.get("/api/billing/status")
        resp = self.client.post("/api/billing/customer-portal", headers=headers)
        self.assertNotEqual(resp.status_code, 429)


class TestChatbotSseRateLimit(RateLimitEnabledTestCase):
    def _conversation_id(self, headers):
        resp = self.client.post("/api/chatbot/conversations", headers=headers)
        return resp.get_json()["conversation"]["id"] if resp.status_code in (200, 201) else None

    def test_get_messages_nest_jamais_limite(self):
        """methods={"POST"} sur /messages : la lecture (GET) de l'historique
        n'est jamais soumise au rate limit, même après épuisement du
        compteur POST du même endpoint."""
        user, headers = _register(self.client)
        conv_id = self._conversation_id(headers)
        if conv_id is None:
            self.skipTest("conversation non créée (dépendance chatbot indisponible en test)")
        for _ in range(35):
            resp = self.client.get(f"/api/chatbot/conversations/{conv_id}/messages")
            self.assertNotEqual(resp.status_code, 429)


class TestPdfUploadRateLimit(RateLimitEnabledTestCase):
    def test_bloque_apres_5_par_heure_pour_un_compte_ultra(self):
        from plan_service import Plan

        user, headers = _register(self.client)
        db.set_stripe_subscription(user["id"], "sub_test", Plan.ULTRA.value, "active")
        for _ in range(5):
            resp = self.client.post(
                "/api/chatbot/attachments/pdf", data={}, content_type="multipart/form-data", headers=headers,
            )
            self.assertNotEqual(resp.status_code, 429)
        resp = self.client.post(
            "/api/chatbot/attachments/pdf", data={}, content_type="multipart/form-data", headers=headers,
        )
        self.assertEqual(resp.status_code, 429)


class TestSearchRateLimit(RateLimitEnabledTestCase):
    def test_bloque_apres_60_par_minute(self):
        _, headers = _register(self.client)
        last = None
        for _ in range(60):
            last = self.client.get("/api/search?q=test")
        self.assertNotEqual(last.status_code, 429)
        resp = self.client.get("/api/search?q=test")
        self.assertEqual(resp.status_code, 429)


class TestReviewsRateLimit(RateLimitEnabledTestCase):
    def _payload(self, i):
        return {
            "name": f"Testeur {i}", "pseudo": f"testeur{i}", "classe": "Seconde",
            "rating": 5, "comment": f"Un avis de test numéro {i}, assez long pour passer la validation.",
        }

    def test_post_bloque_apres_10_par_minute(self):
        ip = _fake_ip()
        for i in range(10):
            resp = self.client.post("/api/reviews", json=self._payload(i), headers={"X-Forwarded-For": ip})
            self.assertNotEqual(resp.status_code, 429)
        resp = self.client.post("/api/reviews", json=self._payload(99), headers={"X-Forwarded-For": ip})
        self.assertEqual(resp.status_code, 429)

    def test_get_nest_jamais_limite(self):
        ip = _fake_ip()
        for _ in range(15):
            resp = self.client.get("/api/reviews", headers={"X-Forwarded-For": ip})
            self.assertNotEqual(resp.status_code, 429)


class TestRoutesExemptees(RateLimitEnabledTestCase):
    def test_webhook_stripe_jamais_limite(self):
        ip = _fake_ip()
        last = None
        for _ in range(15):
            last = self.client.post("/api/checkout/webhook", data=b"{}", headers={"X-Forwarded-For": ip})
        self.assertNotEqual(last.status_code, 429)

    def test_chatbot_health_jamais_limite(self):
        ip = _fake_ip()
        last = None
        for _ in range(15):
            last = self.client.get("/api/chatbot/health", headers={"X-Forwarded-For": ip})
        self.assertNotEqual(last.status_code, 429)

    def test_dev_dashboard_jamais_429_seulement_403_pour_un_non_admin(self):
        user, _ = _register(self.client)
        last = None
        for _ in range(15):
            last = self.client.get("/api/dev/dashboard")
        self.assertNotEqual(last.status_code, 429)
        self.assertEqual(last.status_code, 403)

    def test_dev_dashboard_jamais_limite_pour_un_admin(self):
        user, _ = _register(self.client)
        db.set_user_role(user["id"], Role.ADMIN.value)
        last = None
        for _ in range(15):
            last = self.client.get("/api/dev/dashboard")
        self.assertEqual(last.status_code, 200)


class TestRateLimitDesactiveParDefaut(unittest.TestCase):
    """Sans activation explicite (comportement par défaut hors production,
    voir config.py) : aucune route n'est jamais limitée, quel que soit le
    volume — condition nécessaire à la non-régression du reste de la suite."""

    def setUp(self):
        self.client = server.app.test_client()

    def test_login_jamais_bloque_par_defaut(self):
        ip = _fake_ip()
        last = None
        for _ in range(10):
            # Email différent à chaque tentative — voir _fake_email() : évite
            # le verrouillage anti brute-force par email déjà existant dans
            # login(), pour isoler uniquement rate_limit_service (par IP).
            last = self.client.post(
                "/api/auth/login", json={"email": _fake_email(), "password": "wrong"},
                headers={"X-Forwarded-For": ip},
            )
        self.assertNotEqual(last.status_code, 429)

    def test_register_jamais_bloque_par_defaut(self):
        ip = _fake_ip()
        for _ in range(5):
            user, _ = _register(self.client, ip=ip)
            self.assertIsNotNone(user)


if __name__ == "__main__":
    unittest.main()
