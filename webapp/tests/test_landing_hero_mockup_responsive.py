"""
Régression — mockup du Hero (page d'accueil, index.html) disproportionné sur
petit écran (webapp/static/css/landing.css).

Cause racine : `.hero-mockup-body` porte une hauteur minimale fixe (460px,
pensée pour la largeur desktop de `.hero-illustration-wrap`, ~640px). Sous
960px, `.hero-illustration-wrap` se limite déjà à max-width:560px, puis
rétrécit encore avec le viewport sur mobile — mais rien ne réduisait la
hauteur minimale du mockup, qui restait à 460px : sur un téléphone étroit, la
miniature de Dashboard devenait une fenêtre haute et étroite au lieu d'une
vignette proportionnée, exactement le symptôme "illustration très grande /
mal proportionnée" repéré en audit.

Correction : une règle mobile (`@media (max-width: 640px)`) réduit
`.hero-mockup-body` à une hauteur minimale plus proche du contenu réel
affiché (sidebar + objectif du jour + stats + graphique) à cette largeur.
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent


def _read(relative_path):
    return (ROOT / relative_path).read_text(encoding="utf-8")


class TestHeroMockupProportionneSurMobile(unittest.TestCase):
    def setUp(self):
        self.css = _read("webapp/static/css/landing.css")

    def test_hauteur_minimale_desktop_reste_460px(self):
        # Ne doit pas régresser côté desktop (le bug n'existait que sous
        # 640px, voir docstring) : la règle de base doit rester intacte.
        match = re.search(r"\.hero-mockup-body\s*\{([^}]*)\}", self.css)
        self.assertIsNotNone(match, "règle .hero-mockup-body introuvable")
        self.assertIn("min-height: 460px", match.group(1))

    def test_une_regle_mobile_reduit_la_hauteur_minimale(self):
        # Plusieurs blocs `@media (max-width: 640px)` coexistent dans le
        # fichier (un par composant concerné) : on cherche celui qui redéfinit
        # .hero-mockup-body, pas nécessairement le premier trouvé.
        media_blocks = re.findall(r"@media \(max-width:\s*640px\)\s*\{(.*?)\n\}", self.css, re.DOTALL)
        self.assertTrue(media_blocks, "aucun media query max-width:640px trouvé")
        mobile_height = None
        for block in media_blocks:
            match = re.search(r"\.hero-mockup-body\s*\{([^}]*)\}", block)
            if match:
                mobile_height = re.search(r"min-height:\s*(\d+)px", match.group(1))
                break
        self.assertIsNotNone(mobile_height, ".hero-mockup-body non redéfini sous 640px")
        self.assertLess(int(mobile_height.group(1)), 460)


if __name__ == "__main__":
    unittest.main()
