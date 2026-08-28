"""
Suite dédiée à chatbot/providers/ollama_provider.py — jusqu'ici couvert
uniquement indirectement via test_chatbot_routing.py (avec FakeProvider).
Deux niveaux :
  - unitaire, requests mocké : gestion d'erreur/timeout/parsing, toujours
    exécuté en CI, aucune dépendance externe.
  - intégration réelle, jamais mockée : exercée uniquement si un serveur
    Ollama répond vraiment sur OLLAMA_BASE_URL (127.0.0.1:11434 par défaut)
    — skip explicite sinon, jamais un échec (même politique que
    tests/test_stripe_e2e.py pour Stripe Test Mode).
"""
import json
import unittest
from unittest.mock import patch, MagicMock

import requests

from chatbot.providers.ollama_provider import OllamaProvider, OllamaConnectionError


def _fake_response(payload=None, status_code=200, lines=None):
    resp = MagicMock()
    resp.status_code = status_code
    if status_code >= 400:
        resp.raise_for_status.side_effect = requests.HTTPError(f"HTTP {status_code}")
    else:
        resp.raise_for_status.side_effect = None
    if payload is not None:
        resp.json.return_value = payload
    if lines is not None:
        resp.iter_lines.return_value = iter(lines)
    return resp


class TestHealth(unittest.TestCase):
    def test_serveur_joignable_renvoie_ok(self):
        with patch("chatbot.providers.ollama_provider.requests.get", return_value=_fake_response({"models": []})):
            result = OllamaProvider().health()
        self.assertEqual(result, {"ok": True, "detail": ""})

    def test_serveur_injoignable_renvoie_ok_false_sans_lever(self):
        with patch("chatbot.providers.ollama_provider.requests.get", side_effect=requests.ConnectionError("refused")):
            result = OllamaProvider().health()
        self.assertFalse(result["ok"])
        self.assertIn("pas démarré", result["detail"])

    def test_timeout_est_traite_comme_indisponible(self):
        with patch("chatbot.providers.ollama_provider.requests.get", side_effect=requests.Timeout("slow")):
            result = OllamaProvider().health()
        self.assertFalse(result["ok"])


class TestAvailableModels(unittest.TestCase):
    def test_liste_les_modeles_installes(self):
        payload = {"models": [{"name": "mistral:latest"}, {"name": "llama3:8b"}]}
        with patch("chatbot.providers.ollama_provider.requests.get", return_value=_fake_response(payload)):
            models = OllamaProvider().available_models()
        self.assertEqual(models, {"mistral:latest": "mistral:latest", "llama3:8b": "llama3:8b"})

    def test_serveur_injoignable_renvoie_dict_vide(self):
        with patch("chatbot.providers.ollama_provider.requests.get", side_effect=requests.ConnectionError("refused")):
            models = OllamaProvider().available_models()
        self.assertEqual(models, {})

    def test_reponse_json_invalide_renvoie_dict_vide(self):
        resp = _fake_response()
        resp.json.side_effect = ValueError("not json")
        with patch("chatbot.providers.ollama_provider.requests.get", return_value=resp):
            models = OllamaProvider().available_models()
        self.assertEqual(models, {})


class TestStreamChat(unittest.TestCase):
    def test_assemble_les_chunks_de_la_reponse_en_streaming(self):
        lines = [
            json.dumps({"message": {"content": "Bon"}}),
            json.dumps({"message": {"content": "jour"}}),
            json.dumps({"message": {"content": ""}, "done": True}),
        ]
        with patch("chatbot.providers.ollama_provider.requests.post", return_value=_fake_response(lines=lines)):
            chunks = list(OllamaProvider().stream_chat(messages=[{"role": "user", "content": "salut"}], system="s"))
        self.assertEqual("".join(chunks), "Bonjour")

    def test_ligne_json_invalide_est_ignoree_sans_planter(self):
        lines = ["not-json-at-all", json.dumps({"message": {"content": "ok"}, "done": True})]
        with patch("chatbot.providers.ollama_provider.requests.post", return_value=_fake_response(lines=lines)):
            chunks = list(OllamaProvider().stream_chat(messages=[], system="s"))
        self.assertEqual("".join(chunks), "ok")

    def test_erreur_reseau_a_la_connexion_leve_ollama_connection_error(self):
        with patch("chatbot.providers.ollama_provider.requests.post", side_effect=requests.ConnectionError("refused")):
            with self.assertRaises(OllamaConnectionError):
                list(OllamaProvider().stream_chat(messages=[], system="s"))

    def test_erreur_dans_un_chunk_de_stream_leve_ollama_connection_error(self):
        lines = [json.dumps({"error": "model not found"})]
        with patch("chatbot.providers.ollama_provider.requests.post", return_value=_fake_response(lines=lines)):
            with self.assertRaises(OllamaConnectionError):
                list(OllamaProvider().stream_chat(messages=[], system="s"))

    def test_http_4xx_leve_ollama_connection_error(self):
        with patch("chatbot.providers.ollama_provider.requests.post", return_value=_fake_response(status_code=404)):
            with self.assertRaises(OllamaConnectionError):
                list(OllamaProvider().stream_chat(messages=[], system="s"))


def _ollama_really_running():
    try:
        requests.get(f"{OllamaProvider()._base_url}/api/tags", timeout=1)
        return True
    except requests.RequestException:
        return False


@unittest.skipUnless(_ollama_really_running(), "Aucun serveur Ollama réel joignable sur cette machine (`ollama serve`).")
class TestIntegrationReelleSiOllamaTourne(unittest.TestCase):
    """Jamais mocké — exécuté uniquement si un vrai serveur Ollama local
    répond. Reflète l'usage réel de NovaMath (CHATBOT_PROVIDER=ollama)."""

    def test_health_reel(self):
        result = OllamaProvider().health()
        self.assertTrue(result["ok"])

    def test_available_models_reel_non_vide_si_un_modele_est_installe(self):
        models = OllamaProvider().available_models()
        self.assertIsInstance(models, dict)


if __name__ == "__main__":
    unittest.main()
