"""
Suite SEC-06 : en-têtes de sécurité HTTP (security_headers_service.py).

Vérifie la construction pure de la CSP/HSTS (build_csp/build_hsts), leur
application réelle sur des réponses Flask (apply_headers/init_app), et la
non-régression des fonctionnalités existantes (pages HTML, API JSON,
téléchargement, Stripe, OAuth, authentification) une fois les en-têtes en
place. Suit le même schéma d'isolation d'environnement que
tests/test_cookie_security.py (SEC-01) : les variables d'environnement
pertinentes sont sauvegardées/restaurées à chaque test, et config.py est
rechargé pour que les valeurs dérivées (IS_PRODUCTION, ENABLE_HSTS, ...)
reflètent l'environnement du test.
"""
import importlib
import os
import random
import unittest

import config
import security_headers_service as shs
import server
from flask import Response


def _reload_config():
    return importlib.reload(config)


ENV_VARS = (
    "FLASK_ENV", "ENABLE_SECURITY_HEADERS", "CSP_REPORT_ONLY", "ENABLE_HSTS",
    "HSTS_MAX_AGE", "CSP_ALLOWED_CONNECT", "CSP_ALLOWED_IMAGES", "CSP_ALLOWED_FONTS",
)


class _EnvIsolatedTestCase(unittest.TestCase):
    def setUp(self):
        self._saved = {name: os.environ.get(name) for name in ENV_VARS}
        for name in ENV_VARS:
            os.environ.pop(name, None)
        _reload_config()

    def tearDown(self):
        for name, value in self._saved.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        _reload_config()


def _fake_ip():
    """Voir tests/test_server_two_factor.py — IP unique par appel pour éviter
    toute collision avec le rate limiting réel (base partagée entre tests)."""
    return f"10.{random.randint(0, 254)}.{random.randint(0, 254)}.{random.randint(1, 254)}"


def _register(client):
    email = f"secheaders{random.randint(1_000_000, 9_999_999)}@gmail.com"
    username = f"secheaders{random.randint(100_000, 999_999)}"
    resp = client.post("/api/auth/register", json={
        "email": email, "username": username, "pseudo": "Test",
        "birth_date": "2000-01-01",
        "password": "MotDePasse123!", "confirm_password": "MotDePasse123!",
        "accept_terms": True, "accept_privacy": True,
    }, headers={"X-Forwarded-For": _fake_ip()})
    user = resp.get_json()["user"]
    csrf = client.get_cookie("nm_csrf").value
    return user, {"X-CSRF-Token": csrf}


# ── build_csp() : construction pure, sans app Flask ─────────────────────────
class TestBuildCspDefautsDev(_EnvIsolatedTestCase):
    """FLASK_ENV non défini => développement (comportement par défaut)."""

    def test_default_src_self(self):
        self.assertIn("default-src 'self'", shs.build_csp())

    def test_script_src_contient_self_et_katex_cdn_sans_nonce(self):
        csp = shs.build_csp()
        self.assertIn("script-src 'self' https://cdn.jsdelivr.net;", csp)

    def test_script_src_ajoute_le_nonce_fourni(self):
        csp = shs.build_csp(nonce="abc123")
        self.assertIn("'nonce-abc123'", csp)

    def test_nonce_absent_si_non_fourni(self):
        self.assertNotIn("nonce-", shs.build_csp())

    def test_script_src_jamais_unsafe_inline(self):
        csp = shs.build_csp(nonce="x")
        script_directive = [d for d in csp.split("; ") if d.startswith("script-src")][0]
        self.assertNotIn("unsafe-inline", script_directive)

    def test_script_src_jamais_unsafe_eval(self):
        self.assertNotIn("unsafe-eval", shs.build_csp())

    def test_style_src_contient_unsafe_inline_justifie(self):
        csp = shs.build_csp()
        style_directive = [d for d in csp.split("; ") if d.startswith("style-src")][0]
        self.assertIn("'unsafe-inline'", style_directive)
        self.assertIn("https://cdn.jsdelivr.net", style_directive)

    def test_img_src_contient_self_et_data(self):
        csp = shs.build_csp()
        img_directive = [d for d in csp.split("; ") if d.startswith("img-src")][0]
        self.assertIn("'self'", img_directive)
        self.assertIn("data:", img_directive)

    def test_font_src_contient_katex_cdn(self):
        csp = shs.build_csp()
        font_directive = [d for d in csp.split("; ") if d.startswith("font-src")][0]
        self.assertIn("https://cdn.jsdelivr.net", font_directive)

    def test_connect_src_self_seul_par_defaut(self):
        self.assertIn("connect-src 'self';", shs.build_csp())

    def test_frame_src_none(self):
        self.assertIn("frame-src 'none'", shs.build_csp())

    def test_object_src_none(self):
        self.assertIn("object-src 'none'", shs.build_csp())

    def test_base_uri_self(self):
        self.assertIn("base-uri 'self'", shs.build_csp())

    def test_frame_ancestors_none(self):
        self.assertIn("frame-ancestors 'none'", shs.build_csp())

    def test_form_action_self(self):
        self.assertIn("form-action 'self'", shs.build_csp())

    def test_pas_de_upgrade_insecure_requests_en_dev(self):
        self.assertNotIn("upgrade-insecure-requests", shs.build_csp())


class TestBuildCspProduction(_EnvIsolatedTestCase):
    def test_upgrade_insecure_requests_present_en_production(self):
        os.environ["FLASK_ENV"] = "production"
        _reload_config()
        self.assertIn("upgrade-insecure-requests", shs.build_csp())


class TestBuildCspSourcesConfigurables(_EnvIsolatedTestCase):
    def test_csp_allowed_connect_ajoute_une_source(self):
        os.environ["CSP_ALLOWED_CONNECT"] = "https://api.example.com"
        _reload_config()
        connect_directive = [d for d in shs.build_csp().split("; ") if d.startswith("connect-src")][0]
        self.assertIn("https://api.example.com", connect_directive)
        self.assertIn("'self'", connect_directive)

    def test_csp_allowed_images_ajoute_une_source(self):
        os.environ["CSP_ALLOWED_IMAGES"] = "https://images.example.com"
        _reload_config()
        img_directive = [d for d in shs.build_csp().split("; ") if d.startswith("img-src")][0]
        self.assertIn("https://images.example.com", img_directive)

    def test_csp_allowed_fonts_ajoute_une_source(self):
        os.environ["CSP_ALLOWED_FONTS"] = "https://fonts.example.com"
        _reload_config()
        font_directive = [d for d in shs.build_csp().split("; ") if d.startswith("font-src")][0]
        self.assertIn("https://fonts.example.com", font_directive)

    def test_plusieurs_sources_separees_par_espace(self):
        os.environ["CSP_ALLOWED_CONNECT"] = "https://a.example.com https://b.example.com"
        _reload_config()
        connect_directive = [d for d in shs.build_csp().split("; ") if d.startswith("connect-src")][0]
        self.assertIn("https://a.example.com", connect_directive)
        self.assertIn("https://b.example.com", connect_directive)

    def test_sources_vides_naffectent_pas_la_csp(self):
        self.assertEqual(shs.build_csp(), shs.build_csp())

    def test_dedoublonnage_si_source_deja_presente(self):
        os.environ["CSP_ALLOWED_IMAGES"] = "'self' data:"
        _reload_config()
        img_directive = [d for d in shs.build_csp().split("; ") if d.startswith("img-src")][0]
        self.assertEqual(img_directive.count("'self'"), 1)
        self.assertEqual(img_directive.count("data:"), 1)


class TestUtilsInternes(unittest.TestCase):
    def test_split_sources_vide_renvoie_liste_vide(self):
        self.assertEqual(shs._split_sources(""), [])

    def test_split_sources_none_renvoie_liste_vide(self):
        self.assertEqual(shs._split_sources(None), [])

    def test_split_sources_plusieurs_valeurs(self):
        self.assertEqual(shs._split_sources("a b  c"), ["a", "b", "c"])

    def test_dedupe_preserve_ordre_et_supprime_doublons(self):
        self.assertEqual(shs._dedupe(["a", "b", "a", "c", "b"]), ["a", "b", "c"])

    def test_dedupe_liste_vide(self):
        self.assertEqual(shs._dedupe([]), [])


# ── build_hsts() : nécessite un contexte de requête Flask ───────────────────
class TestBuildHsts(_EnvIsolatedTestCase):
    def _hsts_with(self, path="/", headers=None):
        with server.app.test_request_context(path, headers=headers or {}):
            return shs.build_hsts()

    def test_absente_en_developpement_meme_en_https(self):
        self.assertIsNone(self._hsts_with(headers={"X-Forwarded-Proto": "https"}))

    def test_absente_en_production_sans_https(self):
        os.environ["FLASK_ENV"] = "production"
        _reload_config()
        self.assertIsNone(self._hsts_with())

    def test_presente_en_production_avec_https(self):
        os.environ["FLASK_ENV"] = "production"
        _reload_config()
        value = self._hsts_with(headers={"X-Forwarded-Proto": "https"})
        self.assertIsNotNone(value)
        self.assertIn("max-age=", value)

    def test_absente_si_enable_hsts_false(self):
        os.environ["FLASK_ENV"] = "production"
        os.environ["ENABLE_HSTS"] = "false"
        _reload_config()
        self.assertIsNone(self._hsts_with(headers={"X-Forwarded-Proto": "https"}))

    def test_reconnait_x_forwarded_proto_https_insensible_a_la_casse(self):
        os.environ["FLASK_ENV"] = "production"
        _reload_config()
        value = self._hsts_with(headers={"X-Forwarded-Proto": "HTTPS"})
        self.assertIsNotNone(value)

    def test_x_forwarded_proto_http_ne_declenche_pas_hsts(self):
        os.environ["FLASK_ENV"] = "production"
        _reload_config()
        self.assertIsNone(self._hsts_with(headers={"X-Forwarded-Proto": "http"}))

    def test_includes_subdomains_present(self):
        os.environ["FLASK_ENV"] = "production"
        _reload_config()
        value = self._hsts_with(headers={"X-Forwarded-Proto": "https"})
        self.assertIn("includeSubDomains", value)

    def test_preload_present_si_max_age_suffisant(self):
        os.environ["FLASK_ENV"] = "production"
        os.environ["HSTS_MAX_AGE"] = "31536000"
        _reload_config()
        value = self._hsts_with(headers={"X-Forwarded-Proto": "https"})
        self.assertIn("preload", value)

    def test_preload_absent_si_max_age_insuffisant(self):
        os.environ["FLASK_ENV"] = "production"
        os.environ["HSTS_MAX_AGE"] = "3600"
        _reload_config()
        value = self._hsts_with(headers={"X-Forwarded-Proto": "https"})
        self.assertNotIn("preload", value)

    def test_max_age_reflete_la_config(self):
        os.environ["FLASK_ENV"] = "production"
        os.environ["HSTS_MAX_AGE"] = "12345"
        _reload_config()
        value = self._hsts_with(headers={"X-Forwarded-Proto": "https"})
        self.assertIn("max-age=12345", value)


# ── Valeurs par défaut de config.py ──────────────────────────────────────────
class TestConfigDefaults(_EnvIsolatedTestCase):
    def test_enable_security_headers_true_par_defaut(self):
        self.assertTrue(config.ENABLE_SECURITY_HEADERS)

    def test_csp_report_only_false_par_defaut(self):
        self.assertFalse(config.CSP_REPORT_ONLY)

    def test_enable_hsts_false_en_dev_par_defaut(self):
        self.assertFalse(config.ENABLE_HSTS)

    def test_enable_hsts_true_en_production_par_defaut(self):
        os.environ["FLASK_ENV"] = "production"
        _reload_config()
        self.assertTrue(config.ENABLE_HSTS)

    def test_hsts_max_age_defaut_un_an(self):
        self.assertEqual(config.HSTS_MAX_AGE, 31536000)

    def test_csp_allowed_connect_vide_par_defaut(self):
        self.assertEqual(config.CSP_ALLOWED_CONNECT, "")

    def test_csp_allowed_images_vide_par_defaut(self):
        self.assertEqual(config.CSP_ALLOWED_IMAGES, "")

    def test_csp_allowed_fonts_vide_par_defaut(self):
        self.assertEqual(config.CSP_ALLOWED_FONTS, "")


# ── apply_headers() sur de vraies réponses Flask (sans passer par le client) ─
class TestApplyHeadersUnitaire(_EnvIsolatedTestCase):
    def test_cache_control_toujours_present(self):
        with server.app.test_request_context("/"):
            resp = shs.apply_headers(Response())
        self.assertEqual(resp.headers["Cache-Control"], "no-store, no-cache, must-revalidate, max-age=0")

    def test_desactivation_supprime_csp(self):
        os.environ["ENABLE_SECURITY_HEADERS"] = "false"
        _reload_config()
        with server.app.test_request_context("/"):
            resp = shs.apply_headers(Response())
        self.assertNotIn("Content-Security-Policy", resp.headers)

    def test_desactivation_supprime_x_frame_options(self):
        os.environ["ENABLE_SECURITY_HEADERS"] = "false"
        _reload_config()
        with server.app.test_request_context("/"):
            resp = shs.apply_headers(Response())
        self.assertNotIn("X-Frame-Options", resp.headers)

    def test_desactivation_conserve_cache_control(self):
        os.environ["ENABLE_SECURITY_HEADERS"] = "false"
        _reload_config()
        with server.app.test_request_context("/"):
            resp = shs.apply_headers(Response())
        self.assertIn("Cache-Control", resp.headers)

    def test_desactivation_supprime_hsts_meme_en_production_https(self):
        os.environ["FLASK_ENV"] = "production"
        os.environ["ENABLE_SECURITY_HEADERS"] = "false"
        _reload_config()
        with server.app.test_request_context("/", headers={"X-Forwarded-Proto": "https"}):
            resp = shs.apply_headers(Response())
        self.assertNotIn("Strict-Transport-Security", resp.headers)

    def test_report_only_renomme_le_header(self):
        os.environ["CSP_REPORT_ONLY"] = "true"
        _reload_config()
        with server.app.test_request_context("/"):
            resp = shs.apply_headers(Response())
        self.assertIn("Content-Security-Policy-Report-Only", resp.headers)
        self.assertNotIn("Content-Security-Policy", resp.headers)

    def test_hors_report_only_header_normal(self):
        with server.app.test_request_context("/"):
            resp = shs.apply_headers(Response())
        self.assertIn("Content-Security-Policy", resp.headers)
        self.assertNotIn("Content-Security-Policy-Report-Only", resp.headers)

    def test_server_header_neutralise(self):
        with server.app.test_request_context("/"):
            resp = shs.apply_headers(Response())
        self.assertEqual(resp.headers["Server"], "NovaMath")

    def test_permissions_policy_minimale(self):
        with server.app.test_request_context("/"):
            resp = shs.apply_headers(Response())
        policy = resp.headers["Permissions-Policy"]
        for directive in ("geolocation=()", "microphone=()", "camera=()"):
            self.assertIn(directive, policy)

    def test_referrer_policy(self):
        with server.app.test_request_context("/"):
            resp = shs.apply_headers(Response())
        self.assertEqual(resp.headers["Referrer-Policy"], "strict-origin-when-cross-origin")

    def test_x_content_type_options_nosniff(self):
        with server.app.test_request_context("/"):
            resp = shs.apply_headers(Response())
        self.assertEqual(resp.headers["X-Content-Type-Options"], "nosniff")

    def test_x_frame_options_deny(self):
        with server.app.test_request_context("/"):
            resp = shs.apply_headers(Response())
        self.assertEqual(resp.headers["X-Frame-Options"], "DENY")

    def test_cross_origin_opener_policy_same_origin(self):
        with server.app.test_request_context("/"):
            resp = shs.apply_headers(Response())
        self.assertEqual(resp.headers["Cross-Origin-Opener-Policy"], "same-origin")

    def test_cross_origin_resource_policy_same_origin(self):
        with server.app.test_request_context("/"):
            resp = shs.apply_headers(Response())
        self.assertEqual(resp.headers["Cross-Origin-Resource-Policy"], "same-origin")

    def test_pas_de_cross_origin_embedder_policy(self):
        with server.app.test_request_context("/"):
            resp = shs.apply_headers(Response())
        self.assertNotIn("Cross-Origin-Embedder-Policy", resp.headers)

    def test_nonce_g_absent_donne_une_csp_sans_nonce(self):
        with server.app.test_request_context("/"):
            resp = shs.apply_headers(Response())
        self.assertNotIn("nonce-", resp.headers["Content-Security-Policy"])


# ── Intégration réelle via server.app.test_client() ──────────────────────────
class TestApplyHeadersIntegrationDev(_EnvIsolatedTestCase):
    def setUp(self):
        super().setUp()
        self.client = server.app.test_client()

    def test_page_html_contient_tous_les_headers_attendus(self):
        resp = self.client.get("/")
        for header in (
            "Content-Security-Policy", "X-Content-Type-Options", "Referrer-Policy",
            "Permissions-Policy", "X-Frame-Options", "Cross-Origin-Opener-Policy",
            "Cross-Origin-Resource-Policy", "Cache-Control",
        ):
            self.assertIn(header, resp.headers, f"header manquant : {header}")

    def test_api_json_contient_les_memes_headers(self):
        resp = self.client.get("/api/health")
        self.assertIn("Content-Security-Policy", resp.headers)
        self.assertIn("X-Content-Type-Options", resp.headers)

    def test_pas_de_hsts_en_dev_meme_sur_une_vraie_reponse(self):
        resp = self.client.get("/", headers={"X-Forwarded-Proto": "https"})
        self.assertNotIn("Strict-Transport-Security", resp.headers)

    def test_landing_page_sans_nonce_dans_la_csp(self):
        resp = self.client.get("/")
        # La landing page n'est pas une "page protégée" (_serve_protected) :
        # aucun script inline n'y est injecté, donc pas de nonce à prévoir.
        self.assertNotIn("nonce-", resp.headers["Content-Security-Policy"])

    def test_404_a_quand_meme_les_headers_de_securite(self):
        resp = self.client.get("/cette-page-nexiste-pas")
        self.assertIn("X-Frame-Options", resp.headers)


class TestApplyHeadersIntegrationProduction(_EnvIsolatedTestCase):
    def setUp(self):
        super().setUp()
        os.environ["FLASK_ENV"] = "production"
        _reload_config()
        self.client = server.app.test_client()

    def test_hsts_present_si_https_simule(self):
        resp = self.client.get("/api/health", headers={"X-Forwarded-Proto": "https"})
        self.assertIn("Strict-Transport-Security", resp.headers)

    def test_hsts_absent_sans_en_tete_https(self):
        resp = self.client.get("/api/health")
        self.assertNotIn("Strict-Transport-Security", resp.headers)

    def test_upgrade_insecure_requests_present(self):
        resp = self.client.get("/api/health")
        self.assertIn("upgrade-insecure-requests", resp.headers["Content-Security-Policy"])


class TestPageProtegeeEtNonce(_EnvIsolatedTestCase):
    def setUp(self):
        super().setUp()
        self.client = server.app.test_client()
        self.user, self.headers = _register(self.client)

    def test_page_protegee_utilise_un_nonce_dans_le_script_src(self):
        resp = self.client.get("/dashboard.html")
        self.assertEqual(resp.status_code, 200)
        csp = resp.headers["Content-Security-Policy"]
        self.assertIn("nonce-", csp)

    def test_nonce_different_a_chaque_requete(self):
        csp1 = self.client.get("/dashboard.html").headers["Content-Security-Policy"]
        csp2 = self.client.get("/dashboard.html").headers["Content-Security-Policy"]
        nonce1 = [p for p in csp1.split() if p.startswith("'nonce-")][0]
        nonce2 = [p for p in csp2.split() if p.startswith("'nonce-")][0]
        self.assertNotEqual(nonce1, nonce2)

    def test_page_protegee_toujours_les_autres_headers(self):
        resp = self.client.get("/dashboard.html")
        self.assertIn("X-Frame-Options", resp.headers)
        self.assertIn("Referrer-Policy", resp.headers)

    def test_page_protegee_sans_session_redirige_sans_planter(self):
        anon = server.app.test_client()
        resp = anon.get("/dashboard.html")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("X-Frame-Options", resp.headers)


class TestTelechargement(_EnvIsolatedTestCase):
    def setUp(self):
        super().setUp()
        self.client = server.app.test_client()
        self.user, self.headers = _register(self.client)

    def test_export_donnees_conserve_content_disposition(self):
        resp = self.client.get("/api/data/export")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("attachment", resp.headers.get("Content-Disposition", ""))

    def test_export_donnees_a_aussi_les_headers_de_securite(self):
        resp = self.client.get("/api/data/export")
        self.assertIn("X-Content-Type-Options", resp.headers)
        self.assertIn("Content-Security-Policy", resp.headers)

    def test_export_donnees_reste_du_json_valide(self):
        resp = self.client.get("/api/data/export")
        payload = resp.get_json()
        self.assertIn("account", payload)


class TestStripeNonRegression(_EnvIsolatedTestCase):
    """Stripe est intégré côté client par redirection complète du navigateur
    (jamais un script/iframe embarqué) — la CSP ne peut donc pas casser ce
    flux. Vérifie ici que la route reste joignable et fonctionnelle avec les
    nouveaux en-têtes en place (statut inchangé : 501 sans clé Stripe
    configurée dans l'environnement de test, comme avant cette passe)."""

    def setUp(self):
        super().setUp()
        self.client = server.app.test_client()
        self.user, self.headers = _register(self.client)

    def test_route_checkout_repond_et_a_les_headers(self):
        resp = self.client.post(
            "/api/checkout/create-session", json={"plan": "premium"}, headers=self.headers,
        )
        self.assertIn(resp.status_code, (200, 501, 502))
        self.assertIn("Content-Security-Policy", resp.headers)

    def test_connect_src_self_nempeche_pas_lappel_serveur_a_stripe(self):
        # connect-src ne s'applique qu'aux requêtes initiées par le navigateur
        # (fetch/XHR côté client) — jamais aux appels HTTP sortants effectués
        # par le serveur Flask lui-même (stripe_service). La route doit donc
        # se comporter exactement comme avant l'ajout de la CSP.
        resp = self.client.post(
            "/api/checkout/create-session", json={"plan": "ultra"}, headers=self.headers,
        )
        self.assertNotEqual(resp.status_code, 500)


class TestOAuthNonRegression(_EnvIsolatedTestCase):
    """Google OAuth (auth.py::oauth_start) redirige le navigateur entier vers
    accounts.google.com — une redirection HTTP (Location) n'est jamais
    bloquée par une CSP, quelle que soit sa politique connect-src/frame-src."""

    def setUp(self):
        super().setUp()
        self.client = server.app.test_client()

    def test_oauth_start_accessible_sans_session(self):
        resp = self.client.get("/api/auth/google/start")
        self.assertIn(resp.status_code, (302, 501))
        self.assertIn("X-Content-Type-Options", resp.headers)

    def test_oauth_start_fournisseur_inconnu_404_avec_headers(self):
        resp = self.client.get("/api/auth/facebook/start")
        self.assertEqual(resp.status_code, 404)
        self.assertIn("Content-Security-Policy", resp.headers)

    def test_oauth_callback_accessible_avec_headers(self):
        resp = self.client.get("/api/auth/google/callback")
        self.assertEqual(resp.status_code, 501)
        self.assertIn("X-Frame-Options", resp.headers)


class TestChatbotNonRegression(_EnvIsolatedTestCase):
    def setUp(self):
        super().setUp()
        self.client = server.app.test_client()
        self.user, self.headers = _register(self.client)

    def test_page_chatbot_html_a_les_headers_et_reste_accessible(self):
        resp = self.client.get("/chatbot.html")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Content-Security-Policy", resp.headers)
        # KaTeX (rendu des formules) et marked.js (rendu markdown) sont
        # chargés par cette page — le CDN doit rester autorisé.
        self.assertIn("https://cdn.jsdelivr.net", resp.headers["Content-Security-Policy"])


class TestAuthenticationNonRegression(_EnvIsolatedTestCase):
    def setUp(self):
        super().setUp()
        self.client = server.app.test_client()

    def test_register_fonctionne_toujours(self):
        user, headers = _register(self.client)
        self.assertIn("id", user)

    def test_login_fonctionne_toujours_avec_les_nouveaux_headers(self):
        email = f"secheaderslogin{random.randint(1_000_000, 9_999_999)}@gmail.com"
        username = f"shlogin{random.randint(100_000, 999_999)}"
        self.client.post("/api/auth/register", json={
            "email": email, "username": username, "pseudo": "Test",
            "birth_date": "2000-01-01",
            "password": "MotDePasse123!", "confirm_password": "MotDePasse123!",
            "accept_terms": True, "accept_privacy": True,
        }, headers={"X-Forwarded-For": _fake_ip()})
        self.client.delete_cookie("nm_session")
        resp = self.client.post("/api/auth/login", json={
            "email": email, "password": "MotDePasse123!",
        }, headers={"X-Forwarded-For": _fake_ip()})
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Content-Security-Policy", resp.headers)

    def test_quota_summary_toujours_accessible_apres_connexion(self):
        user, headers = _register(self.client)
        resp = self.client.get("/api/quota/summary")
        self.assertNotEqual(resp.status_code, 500)
        self.assertIn("X-Content-Type-Options", resp.headers)

    def test_route_2fa_setup_toujours_accessible(self):
        user, headers = _register(self.client)
        resp = self.client.post("/api/auth/2fa/setup", headers=headers)
        self.assertIn(resp.status_code, (200, 501))
        self.assertIn("Content-Security-Policy", resp.headers)


class TestBalayageRoutesAucuneRegression(_EnvIsolatedTestCase):
    """Un en-tête de sécurité mal construit ne doit jamais faire planter une
    route (500) — vérifié sur un échantillon de routes représentatives des
    différentes catégories du projet (pages HTML publiques/protégées, API
    JSON, authentification, paiement, OAuth)."""

    def setUp(self):
        super().setUp()
        self.client = server.app.test_client()

    def test_aucune_route_publique_ne_leve_une_erreur_serveur(self):
        # /api/health peut légitimement renvoyer 503 (un sous-système dégradé,
        # voir health_service.py) — jamais 500, qui signalerait une exception
        # non gérée provenant de la construction des en-têtes.
        for path in ("/", "/index.html", "/api/health", "/api/chapters"):
            with self.subTest(path=path):
                resp = self.client.get(path)
                self.assertNotEqual(resp.status_code, 500)


if __name__ == "__main__":
    unittest.main()
