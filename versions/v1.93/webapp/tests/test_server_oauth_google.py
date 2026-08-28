"""
Suite OAuth Google — échange code -> token -> userinfo (webapp/auth.py::
oauth_start/oauth_callback/oauth_complete_signup). Aucune clé Google réelle
n'est nécessaire : les appels sortants (token_url/userinfo_url) sont mockés
(requests.post/get), seul GOOGLE_CLIENT_ID/SECRET sont simulés via
os.environ pour activer le fournisseur (_provider_configured). Complète
tests/test_server_registration_age.py (même contrainte RGPD de consentement
parental, ici déclenchée via oauth_complete_signup plutôt que register()).
"""
import random
import unittest
from datetime import date
from unittest.mock import patch
from urllib.parse import urlparse, parse_qs

import auth
import db
import server


def _fake_ip():
    return f"10.{random.randint(0, 254)}.{random.randint(0, 254)}.{random.randint(1, 254)}"


def _fake_google_env():
    return patch.dict("os.environ", {"GOOGLE_CLIENT_ID": "test-client-id", "GOOGLE_CLIENT_SECRET": "test-client-secret"})


class _FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            import requests
            raise requests.HTTPError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


def _mock_google_exchange(profile, token_status=200, userinfo_status=200):
    """Patch requests.post (token_url) et requests.get (userinfo_url) tels
    qu'utilisés par auth.oauth_callback."""
    token_patch = patch.object(
        auth.requests, "post",
        return_value=_FakeResponse({"access_token": "fake-access-token"}, token_status),
    )
    userinfo_patch = patch.object(
        auth.requests, "get",
        return_value=_FakeResponse(profile, userinfo_status),
    )
    return token_patch, userinfo_patch


def _google_profile(email, sub=None, email_verified=True, name="Ada"):
    # sub unique par défaut : deux tests indépendants ne doivent jamais
    # partager le même identifiant Google (sinon get_user_by_oauth() les
    # confond), comme les emails/usernames aléatoires déjà utilisés partout
    # ailleurs dans cette suite.
    if sub is None:
        sub = f"sub-{random.randint(10_000_000, 99_999_999)}"
    return {"sub": sub, "email": email, "email_verified": email_verified, "name": name}


class OAuthGoogleTestCase(unittest.TestCase):
    def setUp(self):
        self.client = server.app.test_client()

    def _start_and_get_state(self):
        resp = self.client.get("/api/auth/google/start")
        self.assertEqual(resp.status_code, 302)
        location = resp.headers["Location"]
        qs = parse_qs(urlparse(location).query)
        self.assertTrue(location.startswith("https://accounts.google.com/"))
        return qs["state"][0]


class TestProviderNonConfigure(OAuthGoogleTestCase):
    def test_start_sans_cles_renvoie_501(self):
        with patch.dict("os.environ", {}, clear=False):
            for key in ("GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET"):
                import os
                os.environ.pop(key, None)
            resp = self.client.get("/api/auth/google/start")
            self.assertEqual(resp.status_code, 501)

    def test_callback_sans_cles_renvoie_501(self):
        with patch.dict("os.environ", {}, clear=False):
            import os
            for key in ("GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET"):
                os.environ.pop(key, None)
            resp = self.client.get("/api/auth/google/callback?code=x&state=y")
            self.assertEqual(resp.status_code, 501)

    def test_provider_inconnu_renvoie_404(self):
        with _fake_google_env():
            resp = self.client.get("/api/auth/microsoft/start")
            self.assertEqual(resp.status_code, 404)


class TestOAuthStart(OAuthGoogleTestCase):
    def test_redirige_vers_google_avec_un_state_et_scope_encode(self):
        with _fake_google_env():
            resp = self.client.get("/api/auth/google/start")
            self.assertEqual(resp.status_code, 302)
            location = resp.headers["Location"]
            self.assertTrue(location.startswith("https://accounts.google.com/o/oauth2/v2/auth?"))
            qs = parse_qs(urlparse(location).query)
            self.assertEqual(qs["scope"][0], "openid email profile")
            self.assertTrue(len(qs["state"][0]) > 20)

    def test_deux_appels_generent_des_state_differents(self):
        with _fake_google_env():
            state1 = self._start_and_get_state()
            state2 = self._start_and_get_state()
            self.assertNotEqual(state1, state2)


class TestOAuthCallbackErreurs(OAuthGoogleTestCase):
    def test_consentement_refuse_redirige_sans_crash(self):
        with _fake_google_env():
            resp = self.client.get("/api/auth/google/callback?error=access_denied")
            self.assertEqual(resp.status_code, 302)
            self.assertIn("oauth_error=", resp.headers["Location"])

    def test_state_manquant_est_rejete(self):
        with _fake_google_env():
            resp = self.client.get("/api/auth/google/callback?code=abc")
            self.assertEqual(resp.status_code, 302)
            self.assertIn("oauth_error=", resp.headers["Location"])

    def test_state_incorrect_est_rejete(self):
        with _fake_google_env():
            self._start_and_get_state()
            resp = self.client.get("/api/auth/google/callback?code=abc&state=un-autre-state")
            self.assertEqual(resp.status_code, 302)
            self.assertIn("oauth_error=", resp.headers["Location"])

    def test_code_manquant_est_rejete(self):
        with _fake_google_env():
            state = self._start_and_get_state()
            resp = self.client.get(f"/api/auth/google/callback?state={state}")
            self.assertEqual(resp.status_code, 302)
            self.assertIn("oauth_error=", resp.headers["Location"])

    def test_echec_reseau_lors_de_lechange_de_code_ne_plante_pas(self):
        with _fake_google_env():
            state = self._start_and_get_state()
            import requests
            with patch.object(auth.requests, "post", side_effect=requests.ConnectionError("boom")):
                resp = self.client.get(f"/api/auth/google/callback?code=abc&state={state}")
            self.assertEqual(resp.status_code, 302)
            self.assertIn("oauth_error=", resp.headers["Location"])

    def test_email_non_verifie_est_rejete_sans_creer_de_compte(self):
        email = f"oauthnv{random.randint(1_000_000, 9_999_999)}@gmail.com"
        with _fake_google_env():
            state = self._start_and_get_state()
            token_patch, userinfo_patch = _mock_google_exchange(_google_profile(email, email_verified=False))
            with token_patch, userinfo_patch:
                resp = self.client.get(f"/api/auth/google/callback?code=abc&state={state}")
            self.assertEqual(resp.status_code, 302)
            self.assertIn("oauth_error=", resp.headers["Location"])
        self.assertIsNone(db.get_user_by_email(email))


class TestOAuthCallbackNouveauCompte(OAuthGoogleTestCase):
    def test_nouveau_compte_redirige_vers_completion_dinscription(self):
        email = f"oauthnew{random.randint(1_000_000, 9_999_999)}@gmail.com"
        with _fake_google_env():
            state = self._start_and_get_state()
            token_patch, userinfo_patch = _mock_google_exchange(_google_profile(email))
            with token_patch, userinfo_patch:
                resp = self.client.get(f"/api/auth/google/callback?code=abc&state={state}")
            self.assertEqual(resp.status_code, 302)
            self.assertIn("oauth_complete_signup=google", resp.headers["Location"])
        # Aucun compte créé tant que la date de naissance n'a pas été fournie.
        self.assertIsNone(db.get_user_by_email(email))

    def test_complete_signup_sans_profil_en_attente_renvoie_400(self):
        resp = self.client.post("/api/auth/google/complete-signup", json={
            "username": f"nopending{random.randint(100000,999999)}",
            "pseudo": "Test", "birth_date": "2000-01-01",
            "accept_terms": True, "accept_privacy": True,
        })
        self.assertEqual(resp.status_code, 400)

    def _amorcer_profil_en_attente(self, email, sub=None):
        sub = sub or f"sub-{random.randint(10_000_000, 99_999_999)}"
        with _fake_google_env():
            state = self._start_and_get_state()
            token_patch, userinfo_patch = _mock_google_exchange(_google_profile(email, sub=sub))
            with token_patch, userinfo_patch:
                self.client.get(f"/api/auth/google/callback?code=abc&state={state}")
        return sub

    def test_complete_signup_adulte_cree_le_compte_et_connecte(self):
        email = f"oauthadult{random.randint(1_000_000, 9_999_999)}@gmail.com"
        sub = self._amorcer_profil_en_attente(email)
        username = f"oauthadult{random.randint(100000, 999999)}"
        resp = self.client.post("/api/auth/google/complete-signup", json={
            "username": username, "pseudo": "Ada", "birth_date": "1990-01-01",
            "accept_terms": True, "accept_privacy": True,
        }, headers={"X-Forwarded-For": _fake_ip()})
        self.assertEqual(resp.status_code, 201)
        user = db.get_user_by_email(email)
        self.assertIsNotNone(user)
        self.assertEqual(user["auth_provider"], "google")
        self.assertIsNone(user["password_hash"])
        self.assertIsNotNone(db.get_user_by_oauth("google", sub))
        self.assertIn("nm_session", resp.headers.get("Set-Cookie", ""))

    def test_complete_signup_mineur_declenche_le_consentement_parental(self):
        email = f"oauthminor{random.randint(1_000_000, 9_999_999)}@gmail.com"
        self._amorcer_profil_en_attente(email)
        username = f"oauthminor{random.randint(100000, 999999)}"
        young = (date.today().replace(year=date.today().year - 12)).isoformat()
        resp = self.client.post("/api/auth/google/complete-signup", json={
            "username": username, "pseudo": "Ada", "birth_date": young,
            "parent_email": "parent@example.com",
            "accept_terms": True, "accept_privacy": True,
        }, headers={"X-Forwarded-For": _fake_ip()})
        self.assertEqual(resp.status_code, 202)
        self.assertEqual(resp.get_json()["account_status"], "pending_parental_consent")
        user = db.get_user_by_email(email)
        self.assertEqual(user["account_status"], "pending_parental_consent")

    def test_complete_signup_email_prise_entre_temps_renvoie_409(self):
        """Cas de course : le profil OAuth est amorcé sur un email encore
        libre, mais un autre compte prend cet email avant que l'utilisateur
        ne finalise son inscription (register() classique, ou un deuxième
        onglet) — complete-signup doit revalider, pas faire confiance à l'état
        au moment du callback."""
        email = f"oauthrace{random.randint(1_000_000, 9_999_999)}@gmail.com"
        self._amorcer_profil_en_attente(email)
        db.create_user(email, f"racewinner{random.randint(100000,999999)}", "Race", "hash")
        resp = self.client.post("/api/auth/google/complete-signup", json={
            "username": f"newname{random.randint(100000,999999)}", "pseudo": "Ada",
            "birth_date": "1990-01-01", "accept_terms": True, "accept_privacy": True,
        }, headers={"X-Forwarded-For": _fake_ip()})
        self.assertEqual(resp.status_code, 409)


class TestOAuthCallbackCompteExistant(OAuthGoogleTestCase):
    def test_compte_local_existant_est_lie_et_connecte_sans_creer_de_doublon(self):
        email = f"oauthlink{random.randint(1_000_000, 9_999_999)}@gmail.com"
        sub = f"sub-{random.randint(10_000_000, 99_999_999)}"
        user_id = db.create_user(email, f"linkuser{random.randint(100000,999999)}", "Link", "hash")
        with _fake_google_env():
            state = self._start_and_get_state()
            token_patch, userinfo_patch = _mock_google_exchange(_google_profile(email, sub=sub))
            with token_patch, userinfo_patch:
                resp = self.client.get(f"/api/auth/google/callback?code=abc&state={state}")
            self.assertEqual(resp.status_code, 302)
            self.assertIn("dashboard.html", resp.headers["Location"])
        linked = db.get_user_by_oauth("google", sub)
        self.assertIsNotNone(linked)
        self.assertEqual(linked["id"], user_id)

    def test_reconnexion_via_compte_google_deja_lie_reutilise_le_meme_compte(self):
        email = f"oauthrelog{random.randint(1_000_000, 9_999_999)}@gmail.com"
        sub = f"sub-{random.randint(10_000_000, 99_999_999)}"
        self._amorcer_et_finaliser(email, sub=sub)
        first_user = db.get_user_by_email(email)
        self.assertIsNotNone(first_user)

        with _fake_google_env():
            state = self._start_and_get_state()
            token_patch, userinfo_patch = _mock_google_exchange(_google_profile(email, sub=sub))
            with token_patch, userinfo_patch:
                resp = self.client.get(f"/api/auth/google/callback?code=abc&state={state}")
            self.assertEqual(resp.status_code, 302)
            self.assertIn("dashboard.html", resp.headers["Location"])
        second_user = db.get_user_by_email(email)
        self.assertEqual(first_user["id"], second_user["id"])

    def _amorcer_et_finaliser(self, email, sub):
        with _fake_google_env():
            state = self._start_and_get_state()
            token_patch, userinfo_patch = _mock_google_exchange(_google_profile(email, sub=sub))
            with token_patch, userinfo_patch:
                self.client.get(f"/api/auth/google/callback?code=abc&state={state}")
        username = f"relog{random.randint(100000, 999999)}"
        self.client.post("/api/auth/google/complete-signup", json={
            "username": username, "pseudo": "Ada", "birth_date": "1990-01-01",
            "accept_terms": True, "accept_privacy": True,
        }, headers={"X-Forwarded-For": _fake_ip()})


if __name__ == "__main__":
    unittest.main()
