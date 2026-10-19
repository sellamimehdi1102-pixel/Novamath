"""
Régression — bug d'affichage page Entraînement (exercice.html).

Cause racine : `.question-card` (webapp/static/css/exercice.css) portait un
`overflow: hidden` sans raison fonctionnelle — la barre de progression
(`.question-loading-bar`) a déjà son propre `overflow: hidden` pour clipper
l'animation de son enfant. Cet `overflow: hidden` sur la carte entière
rognait silencieusement tout contenu KaTeX plus large que la carte (fraction,
système d'équations, matrice), sans jamais provoquer d'erreur ni de
scrollbar visible — juste un énoncé tronqué. Ce test empêche sa
réintroduction et vérifie le filet de sécurité (overflow-x: auto) posé sur
les zones où le contenu LaTeX est injecté.
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent


def _read(relative_path):
    return (ROOT / relative_path).read_text(encoding="utf-8")


def _rule_body(css, selector):
    match = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", css)
    assert match, f"Règle {selector} introuvable dans exercice.css"
    return match.group(1)


class TestQuestionCardNeClippePlusLeContenu(unittest.TestCase):
    def setUp(self):
        self.css = _read("webapp/static/css/exercice.css")

    def test_question_card_sans_overflow_hidden(self):
        body = _rule_body(self.css, ".question-card")
        self.assertNotIn("overflow", body)

    def test_question_enonce_defile_horizontalement_si_besoin(self):
        body = _rule_body(self.css, ".question-enonce")
        self.assertIn("overflow-x: auto", body)

    def test_callout_defile_horizontalement_si_besoin(self):
        body = _rule_body(self.css, ".callout")
        self.assertIn("overflow-x: auto", body)


if __name__ == "__main__":
    unittest.main()
