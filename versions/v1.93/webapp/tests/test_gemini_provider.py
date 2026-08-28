"""
Suite dédiée à chatbot/providers/gemini_provider.py — même structure que
test_anthropic_provider.py. Le SDK `google.genai.Client` est mocké pour les
scénarios d'erreur (aucune clé API réelle n'est disponible dans cet
environnement) ; un test de connectivité réel et non destructif (health()
avec une clé au format syntaxiquement plausible mais volontairement fausse)
confirme que l'API Gemini est bien joignable et répond avec une vraie erreur
HTTP d'authentification — jamais une simulation.
"""
import os
import unittest
from unittest.mock import patch, MagicMock

from google.genai import errors

from chatbot.providers.gemini_provider import GeminiProvider, GeminiConnectionError


class TestSansCleConfiguree(unittest.TestCase):
    def test_health_sans_cle_renvoie_ok_false_sans_appel_reseau(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("GEMINI_API_KEY", None)
            result = GeminiProvider().health()
        self.assertFalse(result["ok"])
        self.assertIn("n'est pas configurée", result["detail"])

    def test_stream_chat_sans_cle_leve_gemini_connection_error(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("GEMINI_API_KEY", None)
            with self.assertRaises(GeminiConnectionError):
                list(GeminiProvider().stream_chat(messages=[], system="s"))


class TestGestionDErreursHealth(unittest.TestCase):
    def _provider_avec_client_mocke(self):
        provider = GeminiProvider.__new__(GeminiProvider)
        provider._model = "gemini-3-flash-preview"
        provider._api_key = "fake-key"
        provider._client = MagicMock()
        return provider

    def test_cle_invalide_client_error_401(self):
        provider = self._provider_avec_client_mocke()
        provider._client.models.list.side_effect = errors.ClientError(
            401, {"error": {"message": "invalid API key"}},
        )
        result = provider.health()
        self.assertFalse(result["ok"])
        self.assertIn("invalide ou expirée", result["detail"])

    def test_cle_refusee_client_error_403(self):
        provider = self._provider_avec_client_mocke()
        provider._client.models.list.side_effect = errors.ClientError(
            403, {"error": {"message": "forbidden"}},
        )
        result = provider.health()
        self.assertFalse(result["ok"])
        self.assertIn("invalide ou expirée", result["detail"])

    def test_autre_client_error_najamais_confondue_avec_une_cle_invalide(self):
        provider = self._provider_avec_client_mocke()
        provider._client.models.list.side_effect = errors.ClientError(
            400, {"error": {"message": "bad request"}},
        )
        result = provider.health()
        self.assertFalse(result["ok"])
        self.assertIn("refusé la requête", result["detail"])

    def test_cle_invalide_400_api_key_not_valid(self):
        """Comportement réel observé de l'API Gemini (voir
        TestConnectiviteReelleSansVraieCle ci-dessous) : une clé invalide
        renvoie un ClientError 400 générique, PAS 401/403 — jamais confondu
        avec un autre 400 générique grâce au message "API key not valid"."""
        provider = self._provider_avec_client_mocke()
        provider._client.models.list.side_effect = errors.ClientError(
            400, {"error": {"code": 400, "message": "API key not valid. Please pass a valid API key.", "status": "INVALID_ARGUMENT"}},
        )
        result = provider.health()
        self.assertFalse(result["ok"])
        self.assertIn("invalide ou expirée", result["detail"])

    def test_reseau_injoignable_server_error(self):
        provider = self._provider_avec_client_mocke()
        provider._client.models.list.side_effect = errors.ServerError(
            503, {"error": {"message": "unavailable"}},
        )
        result = provider.health()
        self.assertFalse(result["ok"])
        self.assertIn("Impossible de joindre", result["detail"])

    def test_erreur_api_generique(self):
        provider = self._provider_avec_client_mocke()
        provider._client.models.list.side_effect = errors.APIError(
            500, {"error": {"message": "boom"}},
        )
        result = provider.health()
        self.assertFalse(result["ok"])
        self.assertIn("répondu avec une erreur", result["detail"])

    def test_cle_valide_renvoie_ok(self):
        provider = self._provider_avec_client_mocke()
        provider._client.models.list.return_value = MagicMock()
        result = provider.health()
        self.assertEqual(result, {"ok": True, "detail": ""})


class TestGestionDErreursStreamChat(unittest.TestCase):
    def _provider_avec_stream_qui_leve(self, exc):
        provider = GeminiProvider.__new__(GeminiProvider)
        provider._model = "gemini-3-flash-preview"
        provider._api_key = "fake-key"
        client = MagicMock()
        client.models.generate_content_stream.side_effect = exc
        provider._client = client
        return provider

    def test_cle_invalide_devient_gemini_connection_error(self):
        provider = self._provider_avec_stream_qui_leve(
            errors.ClientError(401, {"error": {"message": "invalid"}})
        )
        with self.assertRaises(GeminiConnectionError):
            list(provider.stream_chat(messages=[], system="s"))

    def test_rate_limit_devient_gemini_connection_error(self):
        provider = self._provider_avec_stream_qui_leve(
            errors.ClientError(429, {"error": {"message": "too many"}})
        )
        with self.assertRaises(GeminiConnectionError):
            list(provider.stream_chat(messages=[], system="s"))

    def test_server_error_devient_gemini_connection_error(self):
        provider = self._provider_avec_stream_qui_leve(
            errors.ServerError(503, {"error": {"message": "unavailable"}})
        )
        with self.assertRaises(GeminiConnectionError):
            list(provider.stream_chat(messages=[], system="s"))


class TestTraductionDesMessages(unittest.TestCase):
    """Gemini utilise le rôle "model" là où le format interne NovaMath (voir
    conversation_manager.py) utilise "assistant" — jamais "assistant" envoyé
    tel quel à l'API Gemini."""

    def test_assistant_devient_model_et_le_texte_est_yielde(self):
        provider = GeminiProvider.__new__(GeminiProvider)
        provider._model = "gemini-3-flash-preview"
        provider._api_key = "fake-key"
        client = MagicMock()
        chunk = MagicMock()
        chunk.text = "Bonjour !"
        client.models.generate_content_stream.return_value = [chunk]
        provider._client = client

        result = list(provider.stream_chat(
            messages=[{"role": "user", "content": "Salut"}, {"role": "assistant", "content": "Coucou"}],
            system="s",
        ))

        self.assertEqual(result, ["Bonjour !"])
        _, kwargs = client.models.generate_content_stream.call_args
        roles = [c["role"] for c in kwargs["contents"]]
        self.assertEqual(roles, ["user", "model"])


def _gemini_api_reellement_joignable():
    try:
        import httpx
        httpx.get("https://generativelanguage.googleapis.com", timeout=3)
        return True
    except Exception:
        return False


@unittest.skipUnless(_gemini_api_reellement_joignable(), "generativelanguage.googleapis.com injoignable depuis cet environnement.")
class TestConnectiviteReelleSansVraieCle(unittest.TestCase):
    """Aucune clé Gemini valide n'est configurée dans cet environnement (voir
    .env) — ce test appelle réellement l'API Gemini avec une clé au format
    plausible mais fausse, et vérifie qu'elle répond une vraie erreur
    d'authentification (jamais simulée) : preuve que le endpoint et le SDK
    fonctionnent, sans exposer ni nécessiter de crédit réel."""

    def test_cle_au_format_plausible_mais_fausse_recoit_une_vraie_erreur_auth(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "AIzaSy" + "x" * 33}):
            result = GeminiProvider().health()
        self.assertFalse(result["ok"])
        self.assertIn("invalide ou expirée", result["detail"])


if __name__ == "__main__":
    unittest.main()
