"""
Validation ciblée du chantier "sécurisation des tests contre les appels API
réels" (2026-10-17) — voir conftest.py (sections "Neutralisation des clés
réelles" et "Garde-fou réseau"). Démontre que :
- un appel direct Anthropic/Gemini/Stripe est bloqué avant d'atteindre le
  réseau (jamais une vraie requête, même avec une vraie clé dans .env) ;
- les clés réelles ne sont jamais exposées dans un message d'exception ;
- FakeProvider et les mocks existants continuent de fonctionner normalement.
"""
import os
import sys
import unittest

import httpx
import requests

import config
from chatbot.providers.anthropic_provider import AnthropicProvider, AnthropicConnectionError
from chatbot.providers.fake_provider import FakeProvider
from chatbot.providers.gemini_provider import GeminiProvider, GeminiConnectionError


def _conftest_module():
    """conftest.py n'est pas importé par pytest sous un nom d'import stable
    (ni `conftest`, ni forcément `tests.conftest` selon le mode de collecte)
    — recherché directement dans sys.modules par son chemin de fichier."""
    for mod in sys.modules.values():
        if getattr(mod, "__file__", "") and mod.__file__.replace("\\", "/").endswith("tests/conftest.py"):
            return mod
    raise RuntimeError("conftest.py introuvable dans sys.modules — pytest l'a-t-il bien chargé ?")


conftest = _conftest_module()


class TestClesReellesNeutralisees(unittest.TestCase):
    """Les clés restent PRÉSENTES (placeholder non vide, voir conftest.py)
    — vider la clé cassait la chaîne de sélection des fournisseurs pour des
    tests préexistants (voir TestSelectionDeFournisseurPreservee ci-dessous).
    Ce qui compte : la valeur n'est jamais la vraie clé de .env."""

    def test_anthropic_api_key_neutralisee(self):
        key = os.environ.get("ANTHROPIC_API_KEY")
        self.assertTrue(key)
        self.assertIn("neutralized", key)

    def test_gemini_api_key_neutralisee(self):
        key = os.environ.get("GEMINI_API_KEY")
        self.assertTrue(key)
        self.assertIn("neutralized", key)

    def test_stripe_secret_key_neutralisee(self):
        self.assertTrue(config.STRIPE_SECRET_KEY)
        self.assertIn("neutralized", config.STRIPE_SECRET_KEY)
        self.assertFalse(config.STRIPE_SECRET_KEY.startswith("sk_live_"))
        self.assertFalse(config.STRIPE_SECRET_KEY.startswith("sk_test_"))

class TestSelectionDeFournisseurPreservee(unittest.TestCase):
    """Preuve que la chaîne de sélection réelle des fournisseurs
    (provider_manager.select_llm_for_user) n'est PAS altérée par la
    neutralisation des clés — seule leur VALEUR change, jamais leur
    présence. Un plan ULTRA doit toujours tenter "anthropic" en premier
    candidat (has_credentials() reste True avec le placeholder), jamais
    basculer directement sur "fake" (qui casserait, entre autres,
    test_chantier9_streaming_navigation_fix.py/test_chantier6_streaming_
    fix.py — voir leur analyse dans ce chantier)."""

    def test_has_credentials_reste_vrai_avec_le_placeholder(self):
        from chatbot.providers.anthropic_provider import AnthropicProvider
        from chatbot.providers.gemini_provider import GeminiProvider

        self.assertTrue(AnthropicProvider().has_credentials())
        self.assertTrue(GeminiProvider().has_credentials())


class TestAppelAnthropicDirectBloque(unittest.TestCase):
    def test_cle_vraiment_absente_echec_local_propre(self):
        """`api_key=""` seul ne suffit pas à simuler l'absence : le
        constructeur retombe sur `os.environ.get("ANTHROPIC_API_KEY")`
        (toujours présent, voir placeholder de conftest.py) — il faut
        aussi vider temporairement la variable elle-même pour exercer ce
        chemin (mécanisme toujours disponible à un test qui en a besoin,
        sans être le défaut global de tout le processus pytest)."""
        saved = os.environ.pop("ANTHROPIC_API_KEY", None)
        try:
            provider = AnthropicProvider(api_key="")
            self.assertFalse(provider.has_credentials())
            with self.assertRaises(AnthropicConnectionError):
                list(provider.stream_chat([{"role": "user", "content": "test"}], system="test"))
        finally:
            if saved is not None:
                os.environ["ANTHROPIC_API_KEY"] = saved

    def test_avec_le_placeholder_par_defaut_le_reseau_reste_bloque(self):
        """Le placeholder d'environnement (voir conftest.py) rend
        has_credentials() vrai (comportement de sélection préservé), mais
        toute tentative réelle d'appel est bloquée par le garde-fou réseau
        — jamais un vrai appel, même avec cette clé "présente"."""
        before = len(conftest.NETWORK_CALLS_PASSED_THROUGH)
        provider = AnthropicProvider()
        self.assertTrue(provider.has_credentials())
        with self.assertRaises(Exception):
            list(provider.stream_chat([{"role": "user", "content": "test"}], system="test"))
        self.assertEqual(len(conftest.NETWORK_CALLS_PASSED_THROUGH), before, "aucun appel réel ne doit avoir atteint le réseau")

    def test_avec_cle_explicite_le_reseau_reste_bloque(self):
        """Même si un test contourne le routage habituel en fournissant une
        clé explicitement (jamais lue depuis l'environnement neutralisé),
        le garde-fou réseau (httpx.Client.send patché) empêche tout appel
        réel — preuve que la protection ne dépend pas uniquement de la
        neutralisation des variables d'environnement.

        Le SDK Anthropic intercepte lui-même les erreurs de transport
        génériques, retente 2 fois, puis les enveloppe dans son propre
        message ("Impossible de joindre l'API Anthropic...") — le texte
        "ISOLATION PYTEST" n'y survit donc pas forcément. La preuve robuste
        est `NETWORK_CALLS_PASSED_THROUGH` (voir conftest.py) : si notre
        garde-fou a bloqué CHAQUE tentative (initiale + 2 retries), cette
        liste reste vide quel que soit ce que le SDK a fait du message."""
        before = len(conftest.NETWORK_CALLS_PASSED_THROUGH)
        provider = AnthropicProvider(api_key="sk-ant-test-jamais-reelle-00000000")
        self.assertTrue(provider.has_credentials())
        with self.assertRaises(Exception) as ctx:
            list(provider.stream_chat([{"role": "user", "content": "test"}], system="test"))
        self.assertEqual(len(conftest.NETWORK_CALLS_PASSED_THROUGH), before, "aucun appel réel ne doit avoir atteint le réseau")
        self.assertNotIn("sk-ant-test-jamais-reelle-00000000", str(ctx.exception))


class TestAppelGeminiDirectBloque(unittest.TestCase):
    def test_cle_vraiment_absente_echec_local_propre(self):
        saved = os.environ.pop("GEMINI_API_KEY", None)
        try:
            provider = GeminiProvider(api_key="")
            self.assertFalse(provider.has_credentials())
            with self.assertRaises(GeminiConnectionError):
                list(provider.stream_chat([{"role": "user", "content": "test"}], system="test"))
        finally:
            if saved is not None:
                os.environ["GEMINI_API_KEY"] = saved

    def test_avec_cle_explicite_le_reseau_reste_bloque(self):
        provider = GeminiProvider(api_key="AIzaFakeTestKeyJamaisReelle00000")
        self.assertTrue(provider.has_credentials())
        with self.assertRaises(Exception) as ctx:
            list(provider.stream_chat([{"role": "user", "content": "test"}], system="test"))
        self.assertIn("ISOLATION PYTEST", str(ctx.exception))
        self.assertNotIn("AIzaFakeTestKeyJamaisReelle00000", str(ctx.exception))


class TestAppelStripeDirectBloque(unittest.TestCase):
    def test_appel_stripe_reel_bloque(self):
        import stripe

        stripe.api_key = "sk_live_jamais_une_vraie_cle_xxxxxxxxxxxx"
        with self.assertRaises(Exception) as ctx:
            stripe.Balance.retrieve()
        message = str(ctx.exception)
        self.assertIn("ISOLATION PYTEST", message)
        self.assertNotIn("sk_live_jamais_une_vraie_cle_xxxxxxxxxxxx", message)


class TestHoteLocalResteAutorise(unittest.TestCase):
    """Ollama (serveur local, jamais une API payante) ne doit pas être
    bloqué par le garde-fou réseau — seule l'absence de serveur réellement
    démarré doit faire échouer la connexion (ConnectionError), jamais notre
    RuntimeError d'isolation."""

    def test_httpx_vers_127_0_0_1_nest_pas_bloque_par_lisolation(self):
        # Pas de serveur Ollama réel en écoute ici : la connexion échoue
        # (refus ou timeout selon l'environnement) — ce qui compte est que
        # ce ne soit JAMAIS notre RuntimeError "ISOLATION PYTEST".
        with self.assertRaises(httpx.TransportError) as ctx:
            with httpx.Client(timeout=1) as client:
                client.get("http://127.0.0.1:11434/api/tags")
        self.assertNotIsInstance(ctx.exception, RuntimeError)

    def test_requests_vers_127_0_0_1_nest_pas_bloque_par_lisolation(self):
        with self.assertRaises(requests.exceptions.RequestException) as ctx:
            requests.get("http://127.0.0.1:11434/api/tags", timeout=1)
        self.assertNotIn("ISOLATION PYTEST", str(ctx.exception))


class TestFakeProviderFonctionneToujours(unittest.TestCase):
    def test_fake_provider_repond_sans_reseau(self):
        provider = FakeProvider(model="moteur-novamath")
        chunks = list(provider.stream_chat([{"role": "user", "content": "Qu'est-ce qu'une fonction affine ?"}], system="système"))
        self.assertTrue(chunks)


class TestMocksExistantsPreserves(unittest.TestCase):
    """Un mock explicite (même pattern que test_stripe_service.py/
    test_server_oauth_google.py) continue de fonctionner normalement : le
    mock remplace l'appel avant d'atteindre la couche transport patchée."""

    def test_mock_stripe_fonctionne_sans_toucher_au_garde_fou(self):
        from unittest.mock import patch

        import stripe_service

        with patch("stripe_service.stripe") as mock_stripe:
            mock_stripe.Customer.create.return_value = {"id": "cus_test_123"}
            customer = stripe_service.stripe.Customer.create(email="eleve@gmail.com")
        self.assertEqual(customer["id"], "cus_test_123")

    def test_mock_requests_post_fonctionne_sans_toucher_au_garde_fou(self):
        from unittest.mock import patch

        with patch("requests.post") as mock_post:
            mock_post.return_value.json.return_value = {"access_token": "fake"}
            resp = requests.post("https://oauth2.googleapis.com/token", data={})
        self.assertEqual(resp.json()["access_token"], "fake")


if __name__ == "__main__":
    unittest.main()
