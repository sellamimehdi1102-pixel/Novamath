"""Référencement naturel : pages publiques par classe (/maths-<classe>),
robots.txt, sitemap.xml, page de choix de classe en noindex et fermeture de
debug-runtime.html hors mode debug.

Vérifie aussi que ces pages n'ouvrent aucun accès : les pages personnelles
restent redirigées vers la connexion sans session.
"""
import json
import random
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

EXPECTED_SLUGS = {
    "quatrieme": "maths-quatrieme",
    "troisieme": "maths-troisieme",
    "seconde": "maths-seconde",
    "premiere": "maths-premiere-specialite",
    "premiere_specifique": "maths-premiere-specifique",
}


def _register(client):
    email = f"seo{random.randint(1_000_000, 9_999_999)}@gmail.com"
    client.post("/api/auth/register", json={
        "email": email, "username": f"seouser{random.randint(100_000, 999_999)}", "pseudo": "Test",
        "birth_date": "2000-01-01",
        "password": "MotDePasse123!", "confirm_password": "MotDePasse123!",
        "accept_terms": True, "accept_privacy": True,
    })


def _ld_json_blocks(html):
    return [json.loads(b) for b in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)]


class TestPagesDeClasse(unittest.TestCase):
    def setUp(self):
        self.client = server.app.test_client()

    def test_une_page_par_classe_publiee_et_identifiants_inchanges(self):
        self.assertEqual({lvl: p["slug"] for lvl, p in seo_pages.CLASS_PAGES.items()}, EXPECTED_SLUGS)
        self.assertEqual(set(EXPECTED_SLUGS), set(curriculum_registry.CURRICULUM_REGISTRY))

    def test_200_sans_session_et_balises_seo(self):
        titles, descriptions = set(), set()
        for level, slug in EXPECTED_SLUGS.items():
            with self.subTest(slug=slug):
                resp = self.client.get(f"/{slug}")
                self.assertEqual(resp.status_code, 200)
                self.assertIn("text/html", resp.content_type)
                html = resp.get_data(as_text=True)
                self.assertNotIn("<!--SEO:", html)
                self.assertNotIn('name="robots"', html)
                self.assertEqual(html.count("<h1>"), 1)
                self.assertIn(f'<link rel="canonical" href="https://mathadap.com/{slug}" />', html)
                self.assertIn(f'<meta property="og:url" content="https://mathadap.com/{slug}" />', html)
                title = re.search(r"<title>(.*?)</title>", html).group(1)
                desc = re.search(r'<meta name="description" content="([^"]+)"', html).group(1)
                self.assertLessEqual(len(desc), 160)
                titles.add(title)
                descriptions.add(desc)
                ld = _ld_json_blocks(html)
                self.assertEqual(len(ld), 1)
                types = {node["@type"] for node in ld[0]["@graph"]}
                self.assertEqual(types, {"WebPage", "BreadcrumbList"})
        # Aucun texte de métadonnées dupliqué entre les cinq pages.
        self.assertEqual(len(titles), 5)
        self.assertEqual(len(descriptions), 5)

    def test_chapitres_avec_vrais_titres(self):
        for level, slug in EXPECTED_SLUGS.items():
            with self.subTest(slug=slug):
                html = self.client.get(f"/{slug}").get_data(as_text=True)
                chapters = re.findall(r'<span class="seo-chapter-num">\d+</span> (.*?)</h3>', html)
                self.assertGreater(len(chapters), 0)
                for title in chapters:
                    self.assertIsNone(re.match(r"^Chapitre\s+\d+$", title), title)

    def test_premiere_specialite_titres_deduits_des_notions(self):
        # Les cours de Première portent un titre générique « Chapitre N » ;
        # la page affiche le titre que l'application montre déjà aux élèves.
        html = self.client.get("/maths-premiere-specialite").get_data(as_text=True)
        chapters = re.findall(r'<span class="seo-chapter-num">\d+</span> (.*?)</h3>', html)
        self.assertEqual(chapters[0], "Suites numériques")
        self.assertIn("Produit scalaire", chapters)
        self.assertIn("Fonction exponentielle", chapters)

    def test_premiere_specifique_transparente_sur_son_origine(self):
        html = self.client.get("/maths-premiere-specifique").get_data(as_text=True)
        self.assertIn("ancienne Première ES/L", html)
        self.assertIn("ne correspond pas au programme officiel actuellement en vigueur", html)

    def test_liens_vers_accueil_et_autres_classes(self):
        for slug in EXPECTED_SLUGS.values():
            with self.subTest(slug=slug):
                html = self.client.get(f"/{slug}").get_data(as_text=True)
                self.assertIn('href="/"', html)
                for other in EXPECTED_SLUGS.values():
                    self.assertIn(f'href="/{other}"', html)

    def test_aucun_lien_interne_casse(self):
        seen = set()
        for slug in EXPECTED_SLUGS.values():
            html = self.client.get(f"/{slug}").get_data(as_text=True)
            seen.update(re.findall(r'href="(/[^"#]*)', html))
        for href in sorted(seen):
            with self.subTest(href=href):
                status = self.client.get(href).status_code
                # Pages personnelles : redirection vers la connexion, jamais 404.
                self.assertIn(status, (200, 302), href)

    def test_inscription_presente_et_classe_preselectionnee(self):
        html = self.client.get("/maths-quatrieme").get_data(as_text=True)
        self.assertIn('js-open-signup" type="button" data-set-class="quatrieme"', html)
        self.assertIn("js-open-login", html)

    def test_compte_connecte_voit_continuer(self):
        _register(self.client)
        html = self.client.get("/maths-seconde").get_data(as_text=True)
        self.assertIn('href="/chapitres.html" data-set-class="seconde"', html)
        self.assertNotIn("js-open-signup", html)

    def test_gabarit_brut_jamais_servi(self):
        self.assertEqual(self.client.get("/maths-classe.html").status_code, 404)

    def test_classe_inconnue_404(self):
        self.assertEqual(self.client.get("/maths-terminale").status_code, 404)

    def test_contenu_echappe(self):
        body = seo_pages.render_body(
            "seconde", [{"title": "<script>x</script>", "notions": ["a & b"]}],
            {"totalExercises": 10, "notions": 1, "difficultyLevels": 1}, False,
        )
        self.assertNotIn("<script>x</script>", body)
        self.assertIn("&lt;script&gt;", body)
        self.assertIn("a &amp; b", body)


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
        # Chaque entrée du module JS est reprise, aucune n'est perdue.
        self.assertEqual(len(table), len(re.findall(r'^\s*"[^"]+"\s*:', block, re.M)))


class TestRobotsEtSitemap(unittest.TestCase):
    def test_robots_sitemap_absolu_et_api_non_bloquee(self):
        robots = (STATIC / "robots.txt").read_text(encoding="utf-8")
        self.assertIn("Sitemap: https://mathadap.com/sitemap.xml", robots)
        self.assertNotRegex(robots, r"(?m)^Disallow:\s*/api")
        self.assertNotRegex(robots, r"(?m)^Disallow:\s*/maths-")
        self.assertNotRegex(robots, r"(?m)^Disallow:\s*/choisir-classe")

    def test_sitemap_uniquement_urls_publiques_indexables(self):
        client = server.app.test_client()
        doc = xml.dom.minidom.parse(str(STATIC / "sitemap.xml"))
        locs = [e.firstChild.data for e in doc.getElementsByTagName("loc")]
        for slug in EXPECTED_SLUGS.values():
            self.assertIn(f"https://mathadap.com/{slug}", locs)
        for loc in locs:
            with self.subTest(loc=loc):
                self.assertTrue(loc.startswith("https://mathadap.com/"))
                path = loc[len("https://mathadap.com"):]
                resp = client.get(path)
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

    def test_plus_de_mentions_seconde_seule_ou_lyceens_seuls(self):
        self.assertNotIn("Fait avec soin pour les lycéens.", self.html)
        self.assertNotIn("faq-class-label", self.html)
        self.assertNotIn("tout le programme officiel", self.html)

    def test_open_graph_harmonise(self):
        title = re.search(r"<title>(.*?)</title>", self.html).group(1)
        self.assertIn(f'<meta property="og:title" content="{title}" />', self.html)
        self.assertIn('<meta property="og:url" content="https://mathadap.com/" />', self.html)

    def test_liens_vers_les_cinq_pages(self):
        for slug in EXPECTED_SLUGS.values():
            self.assertIn(f'href="/{slug}"', self.html)


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
