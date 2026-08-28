"""
Suite d'intégration SEC-03 : vérifie le branchement réel des routes 2FA sur
`server.app`/`auth.py` — /2fa/setup, /2fa/enable, /2fa/disable, /2fa/verify,
/2fa/recovery, et le flux de connexion complet (login() renvoie un défi au
lieu d'une session quand la 2FA est active). Complète les suites isolées
tests/test_two_factor_service.py et tests/test_two_factor_migration.py.
"""
import random
import unittest

import pyotp
from cryptography.fernet import Fernet

import config
import db
import server
import two_factor_service as tfs


def _fake_ip():
    """IP unique par appel — voir tests/test_server_rate_limits.py (même
    convention) : évite qu'un /api/auth/register appelé pendant que
    RATE_LIMIT_ENABLED=True (voir TestRateLimiting) ne collisionne, via la
    même IP 127.0.0.1 par défaut du client de test, avec des appels
    register() faits par d'autres classes de ce fichier ou d'autres fichiers
    de la suite — le compteur register (3/heure) vit dans la base réelle,
    partagée entre tous les tests non isolés."""
    return f"10.{random.randint(0, 254)}.{random.randint(0, 254)}.{random.randint(1, 254)}"


def _register(client, ip=None):
    email = f"tf2fa{random.randint(1_000_000, 9_999_999)}@gmail.com"
    username = f"tf2fa{random.randint(100_000, 999_999)}"
    resp = client.post("/api/auth/register", json={
        "email": email, "username": username, "pseudo": "Test",
        "birth_date": "2000-01-01",
        "password": "MotDePasse123!", "confirm_password": "MotDePasse123!",
        "accept_terms": True, "accept_privacy": True,
    }, headers={"X-Forwarded-For": ip or _fake_ip()})
    user = resp.get_json()["user"]
    csrf = client.get_cookie("nm_csrf").value
    return user, {"X-CSRF-Token": csrf}, email


class TwoFactorServerTestCase(unittest.TestCase):
    def setUp(self):
        self.client = server.app.test_client()
        self._key_backup = config.TWO_FACTOR_SECRET_KEY
        config.TWO_FACTOR_SECRET_KEY = Fernet.generate_key().decode()

    def tearDown(self):
        config.TWO_FACTOR_SECRET_KEY = self._key_backup

    def _setup_and_enable(self, client, headers):
        setup = client.post("/api/auth/2fa/setup", headers=headers).get_json()
        totp = pyotp.TOTP(setup["secret"])
        resp = client.post("/api/auth/2fa/enable", json={"code": totp.now()}, headers=headers)
        return setup["secret"], resp.get_json()["recovery_codes"]

    def _future_code(self, secret, offset=1):
        totp = pyotp.TOTP(secret)
        now_counter = tfs._totp_counter_now()
        return totp.at((now_counter + offset) * tfs.TOTP_STEP_SECONDS)


class TestSetupRoute(TwoFactorServerTestCase):
    def test_anonyme_refuse(self):
        resp = self.client.post("/api/auth/2fa/setup")
        self.assertEqual(resp.status_code, 401)

    def test_utilisateur_connecte_recoit_secret_uri_qr(self):
        _, headers, _ = _register(self.client)
        resp = self.client.post("/api/auth/2fa/setup", headers=headers)
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertIn("secret", body)
        self.assertIn("otpauth_uri", body)
        self.assertTrue(body["qr_code"].startswith("data:image/png;base64,"))

    def test_ne_leve_pas_secret_en_clair_dans_la_reponse_finale_de_2fa_status(self):
        """Le secret n'est renvoyé que par /setup elle-même — jamais par
        /api/auth/me ni ailleurs (voir _public_user, qui n'expose que le
        booléen two_factor_enabled)."""
        _, headers, _ = _register(self.client)
        self.client.post("/api/auth/2fa/setup", headers=headers)
        resp = self.client.get("/api/auth/me")
        self.assertNotIn("two_factor_secret", resp.get_json()["user"])

    def test_invite_refuse(self):
        resp = self.client.post("/api/auth/guest")
        headers = {"X-CSRF-Token": self.client.get_cookie("nm_csrf").value}
        resp = self.client.post("/api/auth/2fa/setup", headers=headers)
        self.assertEqual(resp.status_code, 403)
        self.assertTrue(resp.get_json().get("guest_restricted"))

    def test_501_si_cle_de_chiffrement_absente(self):
        config.TWO_FACTOR_SECRET_KEY = None
        _, headers, _ = _register(self.client)
        resp = self.client.post("/api/auth/2fa/setup", headers=headers)
        self.assertEqual(resp.status_code, 501)

    def test_400_si_deja_active(self):
        _, headers, _ = _register(self.client)
        self._setup_and_enable(self.client, headers)
        resp = self.client.post("/api/auth/2fa/setup", headers=headers)
        self.assertEqual(resp.status_code, 400)

    def test_csrf_requis(self):
        _register(self.client)
        resp = self.client.post("/api/auth/2fa/setup")
        self.assertIn(resp.status_code, (401, 403))


class TestEnableRoute(TwoFactorServerTestCase):
    def test_sans_setup_prealable_400(self):
        _, headers, _ = _register(self.client)
        resp = self.client.post("/api/auth/2fa/enable", json={"code": "123456"}, headers=headers)
        self.assertEqual(resp.status_code, 400)

    def test_code_invalide_400_et_najamais_active(self):
        _, headers, _ = _register(self.client)
        self.client.post("/api/auth/2fa/setup", headers=headers)
        resp = self.client.post("/api/auth/2fa/enable", json={"code": "000000"}, headers=headers)
        self.assertEqual(resp.status_code, 400)
        me = self.client.get("/api/auth/me").get_json()["user"]
        self.assertFalse(me["two_factor_enabled"])

    def test_code_valide_active_et_renvoie_dix_recovery_codes(self):
        _, headers, _ = _register(self.client)
        setup = self.client.post("/api/auth/2fa/setup", headers=headers).get_json()
        totp = pyotp.TOTP(setup["secret"])
        resp = self.client.post("/api/auth/2fa/enable", json={"code": totp.now()}, headers=headers)
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(len(resp.get_json()["recovery_codes"]), 10)
        me = self.client.get("/api/auth/me").get_json()["user"]
        self.assertTrue(me["two_factor_enabled"])

    def test_invite_refuse(self):
        self.client.post("/api/auth/guest")
        headers = {"X-CSRF-Token": self.client.get_cookie("nm_csrf").value}
        resp = self.client.post("/api/auth/2fa/enable", json={"code": "123456"}, headers=headers)
        self.assertEqual(resp.status_code, 403)


class TestDisableRoute(TwoFactorServerTestCase):
    def test_necessite_mot_de_passe_et_code(self):
        _, headers, email = _register(self.client)
        secret, _ = self._setup_and_enable(self.client, headers)

        resp = self.client.post(
            "/api/auth/2fa/disable", json={"password": "mauvais-mdp", "code": self._future_code(secret)},
            headers=headers,
        )
        self.assertEqual(resp.status_code, 401)
        self.assertTrue(self.client.get("/api/auth/me").get_json()["user"]["two_factor_enabled"])

    def test_code_invalide_refuse(self):
        _, headers, email = _register(self.client)
        self._setup_and_enable(self.client, headers)
        resp = self.client.post(
            "/api/auth/2fa/disable", json={"password": "MotDePasse123!", "code": "000000"}, headers=headers,
        )
        self.assertEqual(resp.status_code, 400)
        self.assertTrue(self.client.get("/api/auth/me").get_json()["user"]["two_factor_enabled"])

    def test_mot_de_passe_et_code_valides_desactive(self):
        _, headers, email = _register(self.client)
        secret, _ = self._setup_and_enable(self.client, headers)
        resp = self.client.post(
            "/api/auth/2fa/disable",
            json={"password": "MotDePasse123!", "code": self._future_code(secret)},
            headers=headers,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(self.client.get("/api/auth/me").get_json()["user"]["two_factor_enabled"])

    def test_sans_2fa_active_400(self):
        _, headers, _ = _register(self.client)
        resp = self.client.post(
            "/api/auth/2fa/disable", json={"password": "MotDePasse123!", "code": "123456"}, headers=headers,
        )
        self.assertEqual(resp.status_code, 400)


class TestLoginSansDeuxFA(TwoFactorServerTestCase):
    """Non-régression : un compte sans 2FA continue de se connecter
    exactement comme avant (refactor de login()/_finish_login)."""

    def test_login_cree_directement_une_session(self):
        _, headers, email = _register(self.client)
        self.client.post("/api/auth/logout", headers=headers)
        resp = self.client.post("/api/auth/login", json={"email": email, "password": "MotDePasse123!"})
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertIn("user", body)
        self.assertNotIn("two_factor_required", body)

    def test_login_pose_le_cookie_de_session(self):
        _, headers, email = _register(self.client)
        self.client.post("/api/auth/logout", headers=headers)
        self.client.post("/api/auth/login", json={"email": email, "password": "MotDePasse123!"})
        self.assertIsNotNone(self.client.get_cookie("nm_session"))

    def test_login_echoue_toujours_sur_mauvais_mot_de_passe(self):
        _, headers, email = _register(self.client)
        self.client.post("/api/auth/logout", headers=headers)
        resp = self.client.post("/api/auth/login", json={"email": email, "password": "mauvais"})
        self.assertEqual(resp.status_code, 401)


class TestLoginAvecDeuxFA(TwoFactorServerTestCase):
    def test_login_renvoie_un_defi_au_lieu_dune_session(self):
        _, headers, email = _register(self.client)
        self._setup_and_enable(self.client, headers)
        self.client.post("/api/auth/logout", headers=headers)

        resp = self.client.post("/api/auth/login", json={"email": email, "password": "MotDePasse123!"})
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertTrue(body["two_factor_required"])
        self.assertIn("challenge_token", body)
        self.assertNotIn("user", body)

    def test_login_ne_pose_aucun_cookie_de_session(self):
        _, headers, email = _register(self.client)
        self._setup_and_enable(self.client, headers)
        self.client.post("/api/auth/logout", headers=headers)
        self.client.post("/api/auth/login", json={"email": email, "password": "MotDePasse123!"})
        self.assertIsNone(self.client.get_cookie("nm_session"))

    def test_mauvais_mot_de_passe_ne_revele_pas_si_la_2fa_est_active(self):
        _, headers, email = _register(self.client)
        self._setup_and_enable(self.client, headers)
        self.client.post("/api/auth/logout", headers=headers)
        resp = self.client.post("/api/auth/login", json={"email": email, "password": "mauvais"})
        self.assertEqual(resp.status_code, 401)
        self.assertNotIn("two_factor_required", resp.get_json())


class TestVerifyRoute(TwoFactorServerTestCase):
    def _pending_login(self):
        _, headers, email = _register(self.client)
        secret, codes = self._setup_and_enable(self.client, headers)
        self.client.post("/api/auth/logout", headers=headers)
        resp = self.client.post("/api/auth/login", json={"email": email, "password": "MotDePasse123!"})
        return resp.get_json()["challenge_token"], secret, codes

    def test_code_valide_termine_la_connexion(self):
        challenge_token, secret, _ = self._pending_login()
        resp = self.client.post(
            "/api/auth/2fa/verify", json={"challenge_token": challenge_token, "code": self._future_code(secret)},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("user", resp.get_json())
        self.assertIsNotNone(self.client.get_cookie("nm_session"))

    def test_jeton_invalide_400(self):
        resp = self.client.post("/api/auth/2fa/verify", json={"challenge_token": "inexistant", "code": "123456"})
        self.assertEqual(resp.status_code, 400)

    def test_code_invalide_401(self):
        challenge_token, secret, _ = self._pending_login()
        resp = self.client.post(
            "/api/auth/2fa/verify", json={"challenge_token": challenge_token, "code": "000000"},
        )
        self.assertEqual(resp.status_code, 401)
        self.assertIsNone(self.client.get_cookie("nm_session"))

    def test_jeton_consomme_apres_succes(self):
        challenge_token, secret, _ = self._pending_login()
        code = self._future_code(secret)
        self.client.post("/api/auth/2fa/verify", json={"challenge_token": challenge_token, "code": code})
        resp = self.client.post(
            "/api/auth/2fa/verify", json={"challenge_token": challenge_token, "code": self._future_code(secret, offset=2)},
        )
        self.assertEqual(resp.status_code, 400)

    def test_verrouillage_apres_echecs_repetes(self):
        challenge_token, secret, _ = self._pending_login()
        last = None
        for _ in range(tfs.MAX_ATTEMPTS + 1):
            last = self.client.post(
                "/api/auth/2fa/verify", json={"challenge_token": challenge_token, "code": "000000"},
            )
        self.assertEqual(last.status_code, 429)


class TestRecoveryRoute(TwoFactorServerTestCase):
    def _pending_login(self):
        _, headers, email = _register(self.client)
        secret, codes = self._setup_and_enable(self.client, headers)
        self.client.post("/api/auth/logout", headers=headers)
        resp = self.client.post("/api/auth/login", json={"email": email, "password": "MotDePasse123!"})
        return resp.get_json()["challenge_token"], secret, codes

    def test_recovery_code_valide_termine_la_connexion(self):
        challenge_token, _, codes = self._pending_login()
        resp = self.client.post(
            "/api/auth/2fa/recovery", json={"challenge_token": challenge_token, "recovery_code": codes[0]},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIsNotNone(self.client.get_cookie("nm_session"))

    def test_recovery_code_deja_utilise_refuse(self):
        challenge_token, _, codes = self._pending_login()
        self.client.post("/api/auth/2fa/recovery", json={"challenge_token": challenge_token, "recovery_code": codes[0]})

        _, headers2, email2 = _register(self.client)
        # Nouveau défi (le premier a été consommé par le succès ci-dessus).
        self.client.post("/api/auth/logout", headers=headers2)

    def test_recovery_code_invalide_401(self):
        challenge_token, _, _ = self._pending_login()
        resp = self.client.post(
            "/api/auth/2fa/recovery",
            json={"challenge_token": challenge_token, "recovery_code": "0000-0000-0000-0000"},
        )
        self.assertEqual(resp.status_code, 401)


class TestRateLimiting(TwoFactorServerTestCase):
    def setUp(self):
        super().setUp()
        self._rl_backup = server.app.config.get("RATE_LIMIT_ENABLED")
        server.app.config["RATE_LIMIT_ENABLED"] = True

    def tearDown(self):
        server.app.config["RATE_LIMIT_ENABLED"] = self._rl_backup
        super().tearDown()

    def test_verify_route_est_rate_limitee(self):
        ip = f"10.{random.randint(0, 254)}.{random.randint(0, 254)}.{random.randint(1, 254)}"
        last = None
        for _ in range(6):
            last = self.client.post(
                "/api/auth/2fa/verify",
                json={"challenge_token": "inexistant", "code": "123456"},
                headers={"X-Forwarded-For": ip},
            )
        self.assertEqual(last.status_code, 429)

    def test_setup_route_est_rate_limitee(self):
        _, headers, _ = _register(self.client)
        last = None
        for _ in range(11):
            last = self.client.post("/api/auth/2fa/setup", headers=headers)
        self.assertEqual(last.status_code, 429)


class TestJournalisation(TwoFactorServerTestCase):
    def test_activation_journalisee(self):
        _, headers, _ = _register(self.client)
        self._setup_and_enable(self.client, headers)
        self.assertGreater(db.count_security_events("two_factor_enabled"), 0)

    def test_desactivation_journalisee(self):
        _, headers, email = _register(self.client)
        secret, _ = self._setup_and_enable(self.client, headers)
        self.client.post(
            "/api/auth/2fa/disable",
            json={"password": "MotDePasse123!", "code": self._future_code(secret)},
            headers=headers,
        )
        self.assertGreater(db.count_security_events("two_factor_disabled"), 0)

    def test_echec_verify_journalise(self):
        _, headers, email = _register(self.client)
        self._setup_and_enable(self.client, headers)
        self.client.post("/api/auth/logout", headers=headers)
        resp = self.client.post("/api/auth/login", json={"email": email, "password": "MotDePasse123!"})
        challenge_token = resp.get_json()["challenge_token"]
        before = db.count_security_events("two_factor_verify_failed")
        self.client.post("/api/auth/2fa/verify", json={"challenge_token": challenge_token, "code": "000000"})
        self.assertEqual(db.count_security_events("two_factor_verify_failed"), before + 1)

    def test_recovery_code_utilise_journalise(self):
        _, headers, email = _register(self.client)
        secret, codes = self._setup_and_enable(self.client, headers)
        self.client.post("/api/auth/logout", headers=headers)
        resp = self.client.post("/api/auth/login", json={"email": email, "password": "MotDePasse123!"})
        challenge_token = resp.get_json()["challenge_token"]
        before = db.count_security_events("two_factor_recovery_used")
        self.client.post("/api/auth/2fa/recovery", json={"challenge_token": challenge_token, "recovery_code": codes[0]})
        self.assertEqual(db.count_security_events("two_factor_recovery_used"), before + 1)

    def test_aucun_secret_ni_code_dans_les_logs_structures(self):
        _, headers, _ = _register(self.client)
        with self.assertLogs("two_factor_service", level="INFO") as ctx:
            setup = self.client.post("/api/auth/2fa/setup", headers=headers).get_json()
            totp = pyotp.TOTP(setup["secret"])
            self.client.post("/api/auth/2fa/enable", json={"code": totp.now()}, headers=headers)
        joined = "\n".join(ctx.output)
        self.assertNotIn(setup["secret"], joined)


if __name__ == "__main__":
    unittest.main()
