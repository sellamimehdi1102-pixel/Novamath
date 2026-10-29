"""Référencement : anciennes pages /maths-<classe> redirigées vers l'entrée
invité du sélecteur de classe, robots.txt, sitemap.xml, accueil, page de choix
de classe en noindex et fermeture de debug-runtime.html hors mode debug.
Les pages personnelles restent redirigées vers la connexion sans session."""
import re
import unittest
import xml.dom.minidom
from pathlib import Path
from unittest import mock

import config
import curriculum_registry
import seo_pages
import server

STATIC = Path(__file__).resolve().parent.parent / "static"

REDIRECTS = {
    "maths-quatrieme": "quatrieme",
    "maths-troisieme": "troisieme",
    "maths-seconde": "seconde",
    "maths-premiere-specialite": "premiere",
    "maths-premiere-specifique": "premiere_specifique",
}


class TestAnciennesPagesDeClasse(unittest.TestCase):
    def setUp(self):
        self.client = server.app.test_client()

    def test_cinq_redirections_permanentes_vers_la_bonne_classe(self):
        self.assertEqual(seo_pages.SLUG_TO_CLASS_LEVEL, REDIRECTS)
        for slug, level in REDIRECTS.items():
            with self.subTest(slug=slug):
                resp = self.client.get(f"/{slug}")
                self.assertEqual(resp.status_code, 301)
                self.assertEqual(resp.headers["Location"], f"/choisir-classe.html?classe={level}")

    def test_redirection_sans_session_et_cibles_valides(self):
        for level in REDIRECTS.values():
            self.assertIn(level, curriculum_registry.CURRICULUM_REGISTRY)
        target = self.client.get("/choisir-classe.html?classe=seconde")
        self.assertEqual(target.status_code, 200)  # accessible sans compte

    def test_gabarit_et_script_des_anciennes_pages_supprimes(self):
        self.assertFalse((STATIC / "maths-classe.html").exists())
        self.assertFalse((STATIC / "js" / "classePage.js").exists())
        self.assertEqual(self.client.get("/maths-classe.html").status_code, 404)

    def test_classe_inconnue_404(self):
        self.assertEqual(self.client.get("/maths-terminale").status_code, 404)


class TestTitresDeChapitre(unittest.TestCase):
    def test_titre_non_generique_conserve(self):
        self.assertEqual(seo_pages.resolve_chapter_title("Puissances", ["x"]), "Puissances")

    def test_titre_generique_deduit_du_theme_majoritaire(self):
        notions = ["Fonction dérivée", "Nombre dérivé. Tangente", "Variations d'une fonction"]
        self.assertEqual(
            seo_pages.resolve_chapter_title("Chapitre 3", notions),
            "Dérivation : nombre dérivé et fonction dérivée",
        )

    def test_sans_theme_connu_garde_le_titre_brut(self):
        self.assertEqual(seo_pages.resolve_chapter_title("Chapitre 2", ["inconnue"]), "Chapitre 2")

    def test_table_lue_depuis_le_module_js(self):
        table = seo_pages._notion_theme()
        source = (STATIC / "js" / "chapterTitleByNotions.js").read_text(encoding="utf-8")
        block = source[source.index("const NOTION_THEME = {"):source.index("};")]
        self.assertEqual(len(table), len(re.findall(r'^\s*"[^"]+"\s*:', block, re.M)))


class TestRobotsEtSitemap(unittest.TestCase):
    def test_robots_sitemap_absolu_et_api_non_bloquee(self):
        robots = (STATIC / "robots.txt").read_text(encoding="utf-8")
        self.assertIn("Sitemap: https://mathadap.com/sitemap.xml", robots)
        self.assertNotRegex(robots, r"(?m)^Disallow:\s*/api")

    def test_sitemap_sans_les_anciennes_pages_et_uniquement_urls_indexables(self):
        client = server.app.test_client()
        doc = xml.dom.minidom.parse(str(STATIC / "sitemap.xml"))
        locs = [e.firstChild.data for e in doc.getElementsByTagName("loc")]
        self.assertTrue(locs)
        for loc in locs:
            with self.subTest(loc=loc):
                self.assertNotIn("/maths-", loc)
                resp = client.get(loc[len("https://mathadap.com"):])
                self.assertEqual(resp.status_code, 200)
                self.assertNotIn("noindex", resp.get_data(as_text=True))


class TestAccueil(unittest.TestCase):
    def setUp(self):
        self.html = (STATIC / "index.html").read_text(encoding="utf-8")

    def test_titre_et_description_couvrent_les_classes(self):
        title = re.search(r"<title>(.*?)</title>", self.html).group(1)
        self.assertIn("4e", title)
        self.assertIn("1re", title)
        desc = re.search(r'name="description"\s+content="([^"]+)"', self.html).group(1)
        self.assertIn("Quatrième", desc)

    def test_open_graph_harmonise(self):
        title = re.search(r"<title>(.*?)</title>", self.html).group(1)
        self.assertIn(f'<meta property="og:title" content="{title}" />', self.html)
        self.assertIn('<meta property="og:url" content="https://mathadap.com/" />', self.html)

    def test_liens_des_classes_vers_la_nouvelle_entree_sans_ancienne_url(self):
        for level in REDIRECTS.values():
            self.assertIn(f'href="/choisir-classe.html?classe={level}"', self.html)
        self.assertNotIn('href="/maths-', self.html)


class TestPagesNonIndexablesEtProtegees(unittest.TestCase):
    def setUp(self):
        self.client = server.app.test_client()

    def test_choisir_classe_noindex(self):
        html = self.client.get("/choisir-classe.html").get_data(as_text=True)
        self.assertIn('<meta name="robots" content="noindex" />', html)

    def test_pages_personnelles_toujours_protegees(self):
        for page in server.PROTECTED_PAGES:
            with self.subTest(page=page):
                resp = self.client.get(f"/{page}")
                self.assertEqual(resp.status_code, 302)
                self.assertIn("/?next=", resp.headers["Location"])
        self.assertEqual(self.client.get("/api/auth/me").status_code, 401)

    def test_debug_runtime_ferme_hors_debug(self):
        with mock.patch.object(config, "DEBUG", False):
            self.assertEqual(self.client.get("/debug-runtime").status_code, 404)
            self.assertEqual(self.client.get("/debug-runtime.html").status_code, 404)

    def test_debug_runtime_disponible_en_debug(self):
        with mock.patch.object(config, "DEBUG", True):
            self.assertEqual(self.client.get("/debug-runtime").status_code, 200)
            self.assertEqual(self.client.get("/debug-runtime.html").status_code, 200)


if __name__ == "__main__":
    unittest.main()
