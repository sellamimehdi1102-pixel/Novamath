"""
Régression — illustration du Hero (page d'accueil, index.html) mal
proportionnée sur petit écran (webapp/static/css/landing.css).

L'ancien mockup de Dashboard (.hero-mockup-body, hauteur minimale fixe) a été
remplacé par le « cockpit Mathadap » : composition HTML/CSS/SVG dont les
proportions suivent la largeur réelle du cockpit (container queries), sans
aucune hauteur fixe. Ces tests figent les garanties qui évitaient le symptôme
« illustration très grande / mal proportionnée » repéré en audit :
- aucune hauteur fixe sur les cartes du cockpit ;
- une réorganisation dédiée aux cockpits étroits (téléphone) ;
- un cockpit plus étroit sous 960px (colonne unique).
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent


def _read(relative_path):
    return (ROOT / relative_path).read_text(encoding="utf-8")


def _strip_comments(css):
    return re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)


class TestCockpitProportionneSurMobile(unittest.TestCase):
    def setUp(self):
        self.css = _strip_comments(_read("webapp/static/css/landing.css"))

    def test_aucune_hauteur_fixe_sur_les_cartes_du_cockpit(self):
        for selector in (".cockpit", ".ck-grid", ".ck-card", ".ck-train", ".ck-tile"):
            match = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", self.css)
            self.assertIsNotNone(match, f"règle {selector} introuvable")
            self.assertNotRegex(match.group(1), r"(?<![-\w])height\s*:", selector)

    def test_cockpit_etroit_empile_l_entrainement(self):
        blocks = re.findall(r"@container \(max-width:\s*(\d+)px\)\s*\{(.*?)\n\}", self.css, re.DOTALL)
        self.assertTrue(blocks, "aucune container query sur le cockpit")
        stacked = [int(width) for width, body in blocks if '"train train"' in body]
        self.assertTrue(stacked, "aucune disposition empilée pour un cockpit étroit")
        # Seuil compatible avec un téléphone de 390px (cockpit ≈ 330px de large).
        self.assertGreaterEqual(stacked[0], 360)

    def test_cockpit_reduit_sous_960px(self):
        blocks = re.findall(r"@media \(max-width:\s*960px\)\s*\{(.*?)\n\}", self.css, re.DOTALL)
        body = next((b for b in blocks if ".hero-illustration-wrap" in b), None)
        self.assertIsNotNone(body, ".hero-illustration-wrap non redéfini sous 960px")
        width = re.search(r"\.hero-illustration-wrap\s*\{[^}]*max-width:\s*(\d+)px", body)
        self.assertIsNotNone(width)
        self.assertLessEqual(int(width.group(1)), 600)


if __name__ == "__main__":
    unittest.main()
