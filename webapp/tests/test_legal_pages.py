"""
Pages légales publiques (mission "finalisation juridique + Google OAuth") :
mentions-legales.html, confidentialite.html, cgu.html — accessibles sans
authentification via le handler statique par défaut de Flask (server.py::app,
static_url_path=""), jamais via PROTECTED_PAGES. Ne teste aucune logique
métier protégée (Stripe/quotas/plans/chatbot/auth/2FA/consentement parental) :
uniquement l'accessibilité et la structure de ces 3 pages statiques.
"""
import re
import unittest
from pathlib import Path

import server

ROOT = Path(__file__).resolve().parent.parent.parent
STATIC = ROOT / "webapp" / "static"

PAGES = ["mentions-legales.html", "confidentialite.html", "cgu.html"]


class TestPagesLegalesAccessiblesSansAuth(unittest.TestCase):
    def setUp(self):
        self.client = server.app.test_client()

    def test_les_trois_pages_repondent_200_sans_session(self):
        for page in PAGES:
            with self.subTest(page=page):
                resp = self.client.get(f"/{page}")
                self.assertEqual(resp.status_code, 200)

    def test_pas_de_redirection_vers_la_connexion(self):
        # Contrairement aux PROTECTED_PAGES (voir server.py), ces pages ne
        # doivent jamais rediriger un visiteur anonyme.
        for page in PAGES:
            with self.subTest(page=page):
                resp = self.client.get(f"/{page}")
                self.assertNotIn(resp.status_code, (301, 302, 303, 307, 308))

    def test_content_type_html(self):
        for page in PAGES:
            with self.subTest(page=page):
                resp = self.client.get(f"/{page}")
                self.assertIn("text/html", resp.content_type)

    def test_pages_absentes_de_protected_pages(self):
        for page in PAGES:
            self.assertNotIn(page, server.PROTECTED_PAGES)


class TestStructureSeoAccessibilite(unittest.TestCase):
    def setUp(self):
        self.contents = {page: (STATIC / page).read_text(encoding="utf-8") for page in PAGES}

    def test_lang_fr(self):
        for page, html in self.contents.items():
            with self.subTest(page=page):
                self.assertIn('<html lang="fr">', html)

    def test_title_et_description_presents(self):
        for page, html in self.contents.items():
            with self.subTest(page=page):
                self.assertRegex(html, r"<title>[^<]+Mathadap[^<]*</title>")
                self.assertIn('name="description"', html)

    def test_canonical_pointe_vers_le_domaine_de_production(self):
        for page in PAGES:
            with self.subTest(page=page):
                html = self.contents[page]
                self.assertIn(f'<link rel="canonical" href="https://mathadap.com/{page}">', html)

    def test_un_seul_h1_par_page(self):
        for page, html in self.contents.items():
            with self.subTest(page=page):
                self.assertEqual(len(re.findall(r"<h1[ >]", html)), 1)

    def test_lien_retour_vers_mathadap(self):
        for page, html in self.contents.items():
            with self.subTest(page=page):
                self.assertIn('href="index.html"', html)

    def test_reutilise_le_design_system_existant(self):
        # Ne crée pas un nouveau design system (consigne explicite) : chaque
        # page doit charger tokens.css/base.css, jamais un CSS de mise en
        # forme dupliqué depuis zéro.
        for page, html in self.contents.items():
            with self.subTest(page=page):
                self.assertIn('href="css/tokens.css"', html)
                self.assertIn('href="css/base.css"', html)

    def test_aucun_script_inline(self):
        # CSP (security_headers_service.build_csp) : script-src 'self' sans
        # nonce ni unsafe-inline sur les pages statiques (le nonce n'est posé
        # que par server.py::_serve_protected, jamais ici) — un script
        # inline serait silencieusement bloqué par le navigateur en
        # production. Les scripts doivent donc toujours être externes (src=).
        for page, html in self.contents.items():
            with self.subTest(page=page):
                self.assertNotRegex(html, r"<script(?![^>]*\bsrc=)[^>]*>\s*\S")


class TestLiensDepuisLeSite(unittest.TestCase):
    def test_footer_landing_pointe_vers_les_vraies_pages(self):
        index_html = (STATIC / "index.html").read_text(encoding="utf-8")
        for page in PAGES:
            self.assertIn(f'href="{page}"', index_html)
        # L'ancien mécanisme (popups au contenu obsolète/inexact) ne doit
        # plus être référencé dans le footer.
        self.assertNotIn("js-open-legal", index_html)
        self.assertNotIn("js-open-privacy", index_html)

    def test_cases_a_cocher_inscription_pointent_vers_les_vraies_pages(self):
        auth_modals = (STATIC / "js" / "authModalsTemplate.js").read_text(encoding="utf-8")
        self.assertIn('href="cgu.html"', auth_modals)
        self.assertIn('href="confidentialite.html"', auth_modals)
        self.assertNotIn("js-open-legal", auth_modals)
        self.assertNotIn("js-open-privacy", auth_modals)


class TestBuildViteInclutLesPagesLegales(unittest.TestCase):
    def test_les_trois_pages_sont_dans_le_pipeline_de_build(self):
        # vite.config.js::PAGES pilote rollupOptions.input : une page absente
        # de cette liste n'est jamais copiée dans static-dist/ (servi en
        # priorité par server.py dès qu'il existe, voir _STATIC_FOLDER) —
        # elle resterait donc introuvable (404) en production malgré sa
        # présence dans webapp/static/. Bug constaté puis corrigé pendant
        # cette mission : ce test l'empêche de revenir silencieusement.
        vite_config = (ROOT / "vite.config.js").read_text(encoding="utf-8")
        for page in PAGES:
            self.assertIn(f'"{page}"', vite_config)


class TestSitemapEtRobots(unittest.TestCase):
    def test_sitemap_liste_les_pages_legales(self):
        sitemap = (STATIC / "sitemap.xml").read_text(encoding="utf-8")
        for page in PAGES:
            self.assertIn(f"https://mathadap.com/{page}", sitemap)

    def test_robots_ne_bloque_pas_les_pages_legales(self):
        robots = (STATIC / "robots.txt").read_text(encoding="utf-8")
        for page in PAGES:
            self.assertNotIn(f"Disallow: /{page}", robots)


class TestAucunSecretDansLesPagesLegales(unittest.TestCase):
    def test_pas_de_cle_ni_de_secret(self):
        forbidden = ("sk_live", "sk_test", "GOOGLE_CLIENT_SECRET", "STRIPE_SECRET_KEY", "-----BEGIN")
        for page, html in {p: (STATIC / p).read_text(encoding="utf-8") for p in PAGES}.items():
            with self.subTest(page=page):
                for needle in forbidden:
                    self.assertNotIn(needle, html)


if __name__ == "__main__":
    unittest.main()
