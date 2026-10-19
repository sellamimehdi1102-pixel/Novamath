"""
Régression — la popup Paramètres change de position (webapp/static/css/base.css).

Cause racine : `.popup-overlay` centre verticalement (`align-items: center`)
une `.popup-card` dont la hauteur restait intrinsèque (liée au contenu). Les
catégories de Paramètres (settingsPopup.js/settings.js) ont des hauteurs de
contenu très différentes ("Compte" vs "Aide & à propos") : changer de
catégorie changeait la hauteur de la carte, donc sa position verticale
(recentrage à chaque clic) — exactement le symptôme "la page Paramètres
change de position en cliquant entre les sections".

Correction : `.popup-card--xl` (taille utilisée exclusivement par le popup
Paramètres, voir settingsPopup.js) reçoit une hauteur FIXE (pas seulement un
plafond `max-height`), et `.popup-body` devient un enfant flex extensible
(`flex: 1 1 auto`) qui défile en interne — la carte elle-même ne bouge plus.
sm/md/lg (confirmation/prompt/autres popups ponctuels) ne sont volontairement
pas concernés : ils doivent rester compacts, ajustés à leur contenu.
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent


def _read(relative_path):
    return (ROOT / relative_path).read_text(encoding="utf-8")


def _rule_body(css, selector):
    match = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", css)
    assert match, f"Règle {selector} introuvable dans base.css"
    return match.group(1)


class TestPopupXlHauteurStable(unittest.TestCase):
    def setUp(self):
        self.css = _read("webapp/static/css/base.css")

    def test_popup_card_xl_a_une_hauteur_fixe(self):
        body = _rule_body(self.css, ".popup-card--xl")
        self.assertRegex(body, r"(?<!max-)height\s*:")

    def test_popup_body_peut_grandir_pour_remplir_une_hauteur_fixe(self):
        body = _rule_body(self.css, ".popup-body")
        self.assertIn("flex:", body)

    def test_popup_overlay_reste_centre(self):
        # Le centrage lui-même (flex + align-items/justify-content: center)
        # n'est pas le bug — seule une carte à hauteur variable l'était. On
        # vérifie qu'on ne l'a pas supprimé en corrigeant autre chose.
        body = _rule_body(self.css, ".popup-overlay")
        self.assertIn("align-items: center", body)
        self.assertIn("justify-content: center", body)


if __name__ == "__main__":
    unittest.main()
