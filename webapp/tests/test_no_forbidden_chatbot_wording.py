"""
Garde-fou anti-régression (audit "le chatbot ne doit jamais donner
l'impression d'abandonner", 2026-07-26, épisode 2) : scanne le code SOURCE
réel de `chatbot/` (pas les tests, pas les commentaires internes qui
documentent légitimement l'architecture — voir provider_manager.py/
llm_fallback_service.py, qui doivent pouvoir dire "fournisseur IA"/"Gemini"
dans leurs docstrings d'ingénierie) pour repérer toute chaîne littérale
INTERDITE qui serait réintroduite dans un texte affiché à l'élève.

Contrairement à test_fake_provider.py (qui vérifie le comportement de
FakeProvider en l'exécutant), ce test est volontairement statique et
grossier : il doit échouer bruyamment si quiconque recolle un jour la
formulation bannie dans N'IMPORTE QUEL fichier de `chatbot/`, même un
nouveau module pas encore couvert par un test dédié.
"""
import re
import unittest
from pathlib import Path

CHATBOT_DIR = Path(__file__).resolve().parent.parent / "chatbot"

# Chaînes qui ne doivent plus JAMAIS apparaître dans le code source de
# chatbot/ — voir cahier des charges explicite du 2026-07-26.
FORBIDDEN_LITERALS = [
    "Je n'ai pas trouvé d'information assez précise",
    "Je n'ai pas trouvé de notion de cours correspondant précisément",
    "Active Claude",
    "Active Ollama",
    "active Claude",
    "active Ollama",
]


def _iter_source_files():
    return sorted(CHATBOT_DIR.rglob("*.py"))


class TestAucuneFormulationInterditeDansLeCodeSource(unittest.TestCase):
    def test_aucune_chaine_interdite_nest_presente(self):
        offenders = []
        for path in _iter_source_files():
            text = path.read_text(encoding="utf-8")
            for literal in FORBIDDEN_LITERALS:
                if literal in text:
                    offenders.append((str(path.relative_to(CHATBOT_DIR.parent)), literal))
        self.assertEqual(offenders, [], msg=f"Formulation(s) interdite(s) trouvée(s) : {offenders}")

    def test_aucun_fichier_ne_contient_de_reference_technique_visible(self):
        """Contrairement à FORBIDDEN_LITERALS (phrases exactes), ce test
        cherche des références technique DANS UN CONTEXTE DE TEXTE AFFICHÉ —
        repéré ici par la présence du mot dans une chaîne littérale Python
        (entre guillemets) plutôt que dans un commentaire (#) ou une
        docstring d'architecture. Heuristique volontairement simple : les
        vrais textes affichés à l'élève vivent dans des tuples/constantes de
        messages (NO_MATCH_ANSWERS, CLARIFICATION_MESSAGE, _INTROUVABLE_
        VARIANTS...), jamais dans un commentaire de conception."""
        suspect_patterns = [
            re.compile(r'"[^"\n]*\b(Gemini|Claude|Ollama|FakeProvider)\b[^"\n]*"'),
        ]
        # Fichiers dont les commentaires/docstrings mentionnent légitimement
        # ces noms pour documenter l'architecture (jamais dans un texte
        # affiché) — exclus de cette heuristique volontairement grossière,
        # qui ne sait pas distinguer une chaîne de log serveur d'un texte élève.
        excluded_files = {
            "provider_manager.py", "llm_fallback_service.py", "gemini_provider.py",
            "anthropic_provider.py", "ollama_provider.py", "base.py", "__init__.py",
        }
        offenders = []
        for path in _iter_source_files():
            if path.name in excluded_files:
                continue
            text = path.read_text(encoding="utf-8")
            for pattern in suspect_patterns:
                for match in pattern.finditer(text):
                    offenders.append((str(path.relative_to(CHATBOT_DIR.parent)), match.group(0)))
        self.assertEqual(offenders, [], msg=f"Référence technique visible suspectée : {offenders}")


if __name__ == "__main__":
    unittest.main()
