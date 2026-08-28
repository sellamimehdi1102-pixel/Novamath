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


class TestTimeoutExplicite(unittest.TestCase):
    """Durcissement production : sans timeout explicite, le SDK Anthropic
    peut bloquer un thread worker jusqu'à 10 minutes sur un fournisseur
    silencieux (voir anthropic_provider.DEFAULT_TIMEOUT_SECONDS)."""

    @patch("chatbot.providers.anthropic_provider.anthropic.Anthropic")
    def test_timeout_par_defaut_transmis_au_client(self, mock_anthropic_cls):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test"}, clear=False):
            AnthropicProvider()
        _, kwargs = mock_anthropic_cls.call_args
        self.assertEqual(kwargs.get("timeout"), 45.0)

    @patch("chatbot.providers.anthropic_provider.anthropic.Anthropic")
    def test_timeout_configurable_via_variable_environnement(self, mock_anthropic_cls):
        with patch.dict(
            os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test", "ANTHROPIC_TIMEOUT": "12"}, clear=False,
        ):
            AnthropicProvider()
        _, kwargs = mock_anthropic_cls.call_args
        self.assertEqual(kwargs.get("timeout"), 12.0)


class TestTemperatureJamaisTransmiseAuSDK(unittest.TestCase):
    """claude-sonnet-5 rejette le paramètre `temperature` avec un 400 explicite
    ("`temperature` is deprecated for this model") quelle que soit sa valeur —
    confirmé par un appel réel (audit 2026-08-24). `temperature` reste un
    paramètre accepté par stream_chat() (contrat ChatProvider commun à tous
    les providers, réglable par élève/admin), mais ne doit plus jamais
    atteindre client.messages.stream()."""

    def _provider_avec_stream_mocke(self):
        provider = AnthropicProvider.__new__(AnthropicProvider)
        provider._model = "claude-sonnet-5"
        provider._api_key = "fake-key"
        client = MagicMock()
        stream_cm = MagicMock()
        stream_cm.__enter__.return_value.text_stream = iter(["ok"])
        final_message = MagicMock()
        final_message.usage.input_tokens = 1
        final_message.usage.output_tokens = 1
        stream_cm.__enter__.return_value.get_final_message.return_value = final_message
        client.messages.stream.return_value = stream_cm
        provider._client = client
        return provider, client

    def test_temperature_absente_des_kwargs_envoyes_au_sdk(self):
        provider, client = self._provider_avec_stream_mocke()
        list(provider.stream_chat(messages=[], system="s", temperature=0.9, max_tokens=64))
        _, kwargs = client.messages.stream.call_args
        self.assertNotIn("temperature", kwargs)

    def test_temperature_par_defaut_egalement_absente(self):
        provider, client = self._provider_avec_stream_mocke()
        list(provider.stream_chat(messages=[], system="s"))
        _, kwargs = client.messages.stream.call_args
        self.assertNotIn("temperature", kwargs)


class TestFinishReasonCapture(unittest.TestCase):
    """Chantier 6 (bug 'réponses parfois coupées') : stop_reason du message
    final doit être capturé (last_finish_reason), pour que
    llm_fallback_service puisse distinguer une fin normale ("end_turn") d'une
    troncature par max_tokens ("max_tokens") — jamais fait avant ce chantier."""

    def _provider_avec_stop_reason(self, stop_reason):
        provider = AnthropicProvider.__new__(AnthropicProvider)
        provider._model = "claude-sonnet-5"
        provider._api_key = "fake-key"
        client = MagicMock()
        stream_cm = MagicMock()
        stream_cm.__enter__.return_value.text_stream = iter(["ok"])
        final_message = MagicMock()
        final_message.usage.input_tokens = 1
        final_message.usage.output_tokens = 1
        final_message.stop_reason = stop_reason
        stream_cm.__enter__.return_value.get_final_message.return_value = final_message
        client.messages.stream.return_value = stream_cm
        provider._client = client
        return provider

    def test_fin_normale_capture_end_turn(self):
        provider = self._provider_avec_stop_reason("end_turn")
        list(provider.stream_chat(messages=[], system="s"))
        self.assertEqual(provider.last_finish_reason, "end_turn")

    def test_troncature_capture_max_tokens(self):
        provider = self._provider_avec_stop_reason("max_tokens")
        list(provider.stream_chat(messages=[], system="s"))
        self.assertEqual(provider.last_finish_reason, "max_tokens")


if __name__ == "__main__":
    unittest.main()
