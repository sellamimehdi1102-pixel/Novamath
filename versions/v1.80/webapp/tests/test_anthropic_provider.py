"""
Suite dédiée à chatbot/providers/anthropic_provider.py — jusqu'ici couvert
uniquement indirectement via test_chatbot_routing.py (avec FakeProvider).
Le SDK `anthropic.Anthropic` est mocké pour les scénarios d'erreur (aucune clé
API réelle n'est disponible dans cet environnement) ; un test de
connectivité réel et non destructif (health() avec une clé au format valide
mais volontairement fausse) confirme que l'API Anthropic est bien joignable
et répond avec une vraie AuthenticationError HTTP — jamais une simulation.
"""
import os
import unittest
from unittest.mock import patch, MagicMock

import anthropic

from chatbot.providers.anthropic_provider import AnthropicProvider, AnthropicConnectionError


class TestSansCleConfiguree(unittest.TestCase):
    def test_health_sans_cle_renvoie_ok_false_sans_appel_reseau(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("ANTHROPIC_API_KEY", None)
            result = AnthropicProvider().health()
        self.assertFalse(result["ok"])
        self.assertIn("n'est pas configurée", result["detail"])

    def test_stream_chat_sans_cle_leve_anthropic_connection_error(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("ANTHROPIC_API_KEY", None)
            with self.assertRaises(AnthropicConnectionError):
                list(AnthropicProvider().stream_chat(messages=[], system="s"))


def _request_mock():
    # anthropic.APIConnectionError/AuthenticationError exigent un objet
    # `request` (httpx.Request) minimal dans leur constructeur.
    return MagicMock()


class TestGestionDErreursHealth(unittest.TestCase):
    def _provider_avec_client_mocke(self):
        provider = AnthropicProvider.__new__(AnthropicProvider)
        provider._model = "claude-sonnet-5"
        provider._api_key = "fake-key"
        provider._client = MagicMock()
        return provider

    def test_cle_invalide_authentication_error(self):
        provider = self._provider_avec_client_mocke()
        provider._client.models.list.side_effect = anthropic.AuthenticationError(
            "invalid", response=MagicMock(status_code=401), body=None,
        )
        result = provider.health()
        self.assertFalse(result["ok"])
        self.assertIn("invalide ou expirée", result["detail"])

    def test_reseau_injoignable_api_connection_error(self):
        provider = self._provider_avec_client_mocke()
        provider._client.models.list.side_effect = anthropic.APIConnectionError(request=_request_mock())
        result = provider.health()
        self.assertFalse(result["ok"])
        self.assertIn("Impossible de joindre", result["detail"])

    def test_erreur_api_generique(self):
        provider = self._provider_avec_client_mocke()
        provider._client.models.list.side_effect = anthropic.APIError(
            "boom", request=_request_mock(), body=None,
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
        provider = AnthropicProvider.__new__(AnthropicProvider)
        provider._model = "claude-sonnet-5"
        provider._api_key = "fake-key"
        client = MagicMock()
        client.messages.stream.side_effect = exc
        provider._client = client
        return provider

    def test_authentication_error_devient_anthropic_connection_error(self):
        provider = self._provider_avec_stream_qui_leve(
            anthropic.AuthenticationError("invalid", response=MagicMock(status_code=401), body=None)
        )
        with self.assertRaises(AnthropicConnectionError):
            list(provider.stream_chat(messages=[], system="s"))

    def test_rate_limit_error_devient_anthropic_connection_error(self):
        provider = self._provider_avec_stream_qui_leve(
            anthropic.RateLimitError("too many", response=MagicMock(status_code=429), body=None)
        )
        with self.assertRaises(AnthropicConnectionError):
            list(provider.stream_chat(messages=[], system="s"))

    def test_api_connection_error_devient_anthropic_connection_error(self):
        provider = self._provider_avec_stream_qui_leve(anthropic.APIConnectionError(request=_request_mock()))
        with self.assertRaises(AnthropicConnectionError):
            list(provider.stream_chat(messages=[], system="s"))


def _anthropic_api_reellement_joignable():
    try:
        import httpx
        httpx.get("https://api.anthropic.com", timeout=3)
        return True
    except Exception:
        return False


@unittest.skipUnless(_anthropic_api_reellement_joignable(), "api.anthropic.com injoignable depuis cet environnement.")
class TestConnectiviteReelleSansVraieCle(unittest.TestCase):
    """Aucune clé Anthropic valide n'est configurée dans cet environnement
    (voir .env) — ce test appelle réellement l'API Anthropic avec une clé au
    bon format mais fausse, et vérifie qu'elle répond une vraie erreur 401
    d'authentification (jamais simulée) : preuve que le endpoint et le SDK
    fonctionnent, sans exposer ni nécessiter de crédit réel."""

    def test_cle_au_format_valide_mais_fausse_recoit_une_vraie_401(self):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-api03-" + "x" * 95}):
            result = AnthropicProvider().health()
        self.assertFalse(result["ok"])
        self.assertIn("invalide ou expirée", result["detail"])


if __name__ == "__main__":
    unittest.main()
