"""
Suite dédiée à chatbot/providers/fake_provider.py — le filet de TOUT dernier
recours (voir provider_manager.select_llm_for_user et
llm_fallback_service.generate). Audit du mode dégradé (2026-07-26) : ce
fournisseur ne construit plus de réponse pédagogique à partir du RAG/Current
Learning Context (voir désormais chatbot/services/degraded_mode_service.py,
testé séparément dans test_degraded_mode_service.py) — il ne doit JAMAIS
divulguer l'existence de plusieurs fournisseurs IA, ni de FakeProvider
lui-même, et n'affiche plus qu'une ressource "@" déjà résolue avec certitude
ou, en tout dernier recours, un message de clarification neutre.
"""
import unittest

from chatbot.providers.fake_provider import FakeProvider, NO_MATCH_ANSWERS

FORBIDDEN_WORDS = [
    "claude", "ollama", "gemini", "anthropic", "openai", "fournisseur",
    "intelligence artificielle", "paramètres → chatbot", "fakeprovider",
]


def _contains_forbidden_reference(text):
    lowered = text.lower()
    return [w for w in FORBIDDEN_WORDS if w in lowered]


class TestAucuneReferenceTechnique(unittest.TestCase):
    """Un élève ne doit jamais pouvoir déduire qu'il existe plusieurs
    fournisseurs IA, lequel est actif, ou qu'un filet de sécurité local
    existe — voir le cahier des charges explicite du 2026-07-26."""

    def test_messages_de_clarification_sans_reference_technique(self):
        for message in NO_MATCH_ANSWERS:
            with self.subTest(message=message[:40]):
                self.assertEqual(_contains_forbidden_reference(message), [])

    def test_bloc_rag_seul_ne_construit_plus_de_reponse_ici(self):
        """Le bloc RAG générique (sans grounding "@") n'est plus exploité par
        FakeProvider (voir degraded_mode_service.py, appelé en amont par
        llm_fallback_service.generate() — testé séparément) : ce provider
        retombe honnêtement sur un message de clarification neutre."""
        provider = FakeProvider()
        system = (
            "Contexte."
            "\n\nEXTRAITS DE COURS NOVAMATH PERTINENTS (appuie-toi dessus, ne les recopie pas mot pour mot) :\n"
            "### Théorème de Pythagore (Chapitre 13)\nDans un triangle rectangle..."
        )
        answer = list(provider.stream_chat(messages=[{"role": "user", "content": "explique-moi"}], system=system))[0]
        self.assertEqual(_contains_forbidden_reference(answer), [])
        self.assertIn(answer, NO_MATCH_ANSWERS)

    def test_reponse_grounding_sans_reference_technique(self):
        provider = FakeProvider()
        system = (
            "RESSOURCES MENTIONNÉES PAR L'ÉLÈVE :\n### Théorème de Pythagore (Chapitre 13)\nDéfinition..."
        )
        answer = list(provider.stream_chat(messages=[{"role": "user", "content": "@Pythagore"}], system=system))[0]
        self.assertEqual(_contains_forbidden_reference(answer), [])

    def test_message_par_defaut_sans_aucun_contexte(self):
        provider = FakeProvider()
        answer = list(provider.stream_chat(messages=[{"role": "user", "content": "bla bla bla"}], system=""))[0]
        self.assertIn(answer, NO_MATCH_ANSWERS)
        self.assertEqual(_contains_forbidden_reference(answer), [])


if __name__ == "__main__":
    unittest.main()
