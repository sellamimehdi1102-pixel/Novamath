"""
Régression — pied de page cohérent sur les pages légales (mission
"stabilisation UI/UX Mathadap"). Les 3 pages légales n'avaient qu'un simple
lien de retour, sans pied de page reprenant l'identité Mathadap (logo, liens
légaux, mention de copyright) — incohérent avec le reste du site. Ne charge
pas landing.css (pas de section marketing sur ces pages) : le pied réutilise
un style dédié et léger défini dans legal.css.
"""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
STATIC = ROOT / "webapp" / "static"

PAGES = ["mentions-legales.html", "confidentialite.html", "cgu.html"]


class TestPiedDePageCoherent(unittest.TestCase):
    def setUp(self):
        self.contents = {page: (STATIC / page).read_text(encoding="utf-8") for page in PAGES}

    def test_chaque_page_a_un_footer_legal(self):
        for page, html in self.contents.items():
            with self.subTest(page=page):
                self.assertIn('<footer class="legal-footer">', html)

    def test_le_footer_pointe_vers_les_trois_pages_legales(self):
        for page, html in self.contents.items():
            with self.subTest(page=page):
                for target in PAGES:
                    self.assertIn(f'href="{target}"', html)

    def test_le_footer_est_place_apres_le_lien_retour(self):
        for page, html in self.contents.items():
            with self.subTest(page=page):
                back_link_pos = html.index("legal-back-link")
                footer_pos = html.index('<footer class="legal-footer">')
                self.assertGreater(footer_pos, back_link_pos)

    def test_legal_css_definit_le_style_du_footer(self):
        css = (STATIC / "css" / "legal.css").read_text(encoding="utf-8")
        self.assertIn(".legal-footer {", css)
        self.assertIn(".legal-footer-links", css)


if __name__ == "__main__":
    unittest.main()
