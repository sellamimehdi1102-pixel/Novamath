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

from google.genai import errors, types

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

    @patch("chatbot.providers.gemini_provider.time.sleep")
    def test_rate_limit_transitoire_reessaie_3_fois_puis_mis_en_cache_court(self, mock_sleep):
        """429 SANS "limit: 0" et sans détail QuotaFailure exploitable
        (surcharge générique du backend, voir _classify_error) : backoff
        exponentiel (2s/4s/8s) — 4 tentatives au total (1 initiale + 3
        retries) avant d'abandonner. Audit du 2026-07-26 (classification
        fine des 429) : contrairement à un simple échec non mis en cache,
        les 3 tentatives épuisées SANS avoir rien transmis à l'élève sont
        maintenant mises en cache pour une COURTE durée (5 min, pas 15 min)
        — pour ne pas rejouer inutilement le même cycle de 14s à chaque
        message suivant tant que la rafale se poursuit, sans pour autant
        bloquer Gemini aussi longtemps qu'un quota journalier réellement
        épuisé (voir test_quota_journalier_... ci-dessous)."""
        provider = self._provider_avec_stream_qui_leve(
            errors.ClientError(429, {"error": {"message": "too many"}})
        )
        with self.assertRaises(GeminiConnectionError) as ctx:
            list(provider.stream_chat(messages=[], system="s"))
        self.assertTrue(ctx.exception.durable)
        self.assertEqual(ctx.exception.ttl_seconds, 5 * 60)
        self.assertEqual(provider._client.models.generate_content_stream.call_count, 4)
        self.assertEqual(mock_sleep.call_args_list, [((2,),), ((4,),), ((8,),)])

    @patch("chatbot.providers.gemini_provider.time.sleep")
    def test_rate_limit_transitoire_reussit_a_la_deuxieme_tentative(self, mock_sleep):
        """Le 429 ne se reproduit qu'une fois : la 2e tentative (après 2s de
        backoff) doit réussir normalement, sans jamais lever d'exception ni
        retomber sur FakeProvider (voir provider_manager/llm_fallback_service)."""
        provider = GeminiProvider.__new__(GeminiProvider)
        provider._model = "gemini-3-flash-preview"
        provider._api_key = "fake-key"
        chunk = MagicMock()
        chunk.usage_metadata = None
        chunk.text = "Bonjour"
        client = MagicMock()
        client.models.generate_content_stream.side_effect = [
            errors.ClientError(429, {"error": {"message": "too many"}}),
            [chunk],
        ]
        provider._client = client
        result = list(provider.stream_chat(messages=[], system="s"))
        self.assertEqual(result, ["Bonjour"])
        self.assertEqual(client.models.generate_content_stream.call_count, 2)
        mock_sleep.assert_called_once_with(2)

    def test_quota_zero_reste_durable_sans_aucun_retry(self):
        """Un 429 avec "limit: 0" (quota Free Tier figé, facturation non
        activée) reste durable=True et ne doit JAMAIS être retenté ici —
        mis en cache 24h (voir _TTL_QUOTA_ZERO_SECONDS), pas un backoff
        local qui ne ferait que retarder inutilement une panne qui ne se
        résout jamais toute seule."""
        provider = self._provider_avec_stream_qui_leve(
            errors.ClientError(429, {"error": {"message": "limit: 0 requests"}})
        )
        with self.assertRaises(GeminiConnectionError) as ctx:
            list(provider.stream_chat(messages=[], system="s"))
        self.assertTrue(ctx.exception.durable)
        self.assertEqual(ctx.exception.ttl_seconds, 24 * 60 * 60)
        self.assertEqual(provider._client.models.generate_content_stream.call_count, 1)

    def test_quota_journalier_reel_reste_durable_sans_aucun_retry(self):
        """Reproduit EXACTEMENT le corps d'erreur réel observé lors de
        l'audit du 2026-07-26 (quota Free Tier journalier de
        gemini-3-flash-preview réellement épuisé, capturé par un appel
        direct à l'API Google — voir full_audit_trace.py) : `quotaId`
        contient "PerDay" et `limit` vaut 20 (pas 0), donc l'ancienne
        détection (_is_zero_quota_error seule) le classait à tort comme
        transitoire. Doit maintenant échouer IMMÉDIATEMENT (aucun backoff,
        inutile pour un quota qui ne se réinitialise pas avant des heures)
        et être mis en cache pour 12h."""
        body = {
            "error": {
                "code": 429,
                "message": (
                    "You exceeded your current quota, please check your plan "
                    "and billing details. Quota exceeded for metric: "
                    "generativelanguage.googleapis.com/generate_content_free_tier_requests, "
                    "limit: 20, model: gemini-3-flash\nPlease retry in 34.27s."
                ),
                "status": "RESOURCE_EXHAUSTED",
                "details": [
                    {"@type": "type.googleapis.com/google.rpc.QuotaFailure", "violations": [
                        {
                            "quotaMetric": "generativelanguage.googleapis.com/generate_content_free_tier_requests",
                            "quotaId": "GenerateRequestsPerDayPerProjectPerModel-FreeTier",
                            "quotaDimensions": {"location": "global", "model": "gemini-3-flash"},
                            "quotaValue": "20",
                        },
                    ]},
                    {"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "34s"},
                ],
            },
        }
        provider = self._provider_avec_stream_qui_leve(errors.ClientError(429, body))
        with self.assertRaises(GeminiConnectionError) as ctx:
            list(provider.stream_chat(messages=[], system="s"))
        self.assertTrue(ctx.exception.durable)
        self.assertEqual(ctx.exception.ttl_seconds, 12 * 60 * 60)
        self.assertEqual(provider._client.models.generate_content_stream.call_count, 1)
        self.assertIn("journalier", str(ctx.exception))

    @patch("chatbot.providers.gemini_provider.time.sleep")
    def test_quota_rpm_avec_quota_id_garde_le_backoff(self, mock_sleep):
        """Un 429 dont le `quotaId` contient "PerMinute" (RPM/TPM, se résorbe
        en quelques secondes) doit garder le backoff exponentiel existant —
        contrairement à un quota journalier (PerDay), qui échoue
        immédiatement (voir test ci-dessus)."""
        body = {
            "error": {
                "message": "Quota exceeded, limit: 60, model: gemini-3-flash",
                "details": [
                    {"@type": "type.googleapis.com/google.rpc.QuotaFailure", "violations": [
                        {
                            "quotaMetric": "generativelanguage.googleapis.com/generate_requests_per_minute",
                            "quotaId": "GenerateRequestsPerMinutePerProjectPerModel-FreeTier",
                            "quotaValue": "60",
                        },
                    ]},
                ],
            },
        }
        provider = self._provider_avec_stream_qui_leve(errors.ClientError(429, body))
        with self.assertRaises(GeminiConnectionError) as ctx:
            list(provider.stream_chat(messages=[], system="s"))
        self.assertTrue(ctx.exception.durable)
        self.assertEqual(ctx.exception.ttl_seconds, 5 * 60)
        self.assertEqual(provider._client.models.generate_content_stream.call_count, 4)
        self.assertEqual(mock_sleep.call_args_list, [((2,),), ((4,),), ((8,),)])

    def test_quota_projet_reste_durable_sans_aucun_retry(self):
        """Un `quotaId` contenant "PerProject" (sans "PerDay" ni "PerMinute")
        — quota du projet Google Cloud dépassé — échoue immédiatement,
        mis en cache 6h."""
        body = {
            "error": {
                "message": "Quota exceeded, limit: 1000",
                "details": [
                    {"@type": "type.googleapis.com/google.rpc.QuotaFailure", "violations": [
                        {"quotaMetric": "generativelanguage.googleapis.com/requests",
                         "quotaId": "RequestsPerProjectPerModel-FreeTier", "quotaValue": "1000"},
                    ]},
                ],
            },
        }
        provider = self._provider_avec_stream_qui_leve(errors.ClientError(429, body))
        with self.assertRaises(GeminiConnectionError) as ctx:
            list(provider.stream_chat(messages=[], system="s"))
        self.assertTrue(ctx.exception.durable)
        self.assertEqual(provider._client.models.generate_content_stream.call_count, 1)

    def test_modele_introuvable_404_devient_durable_sans_retry(self):
        """Un 404 (modèle supprimé/déprécié côté Google — voir DEFAULT_MODEL)
        échoue immédiatement, sans backoff, mis en cache 24h."""
        provider = self._provider_avec_stream_qui_leve(
            errors.ClientError(404, {"error": {"message": "model not found", "code": 404}})
        )
        with self.assertRaises(GeminiConnectionError) as ctx:
            list(provider.stream_chat(messages=[], system="s"))
        self.assertTrue(ctx.exception.durable)
        self.assertEqual(ctx.exception.ttl_seconds, 24 * 60 * 60)
        self.assertEqual(provider._client.models.generate_content_stream.call_count, 1)

    @patch("chatbot.providers.gemini_provider.time.sleep")
    def test_aucun_retry_si_un_fragment_a_deja_ete_transmis(self, mock_sleep):
        """Un 429 survenant APRÈS qu'un premier fragment ait déjà été transmis
        à l'appelant ne doit jamais être retenté (rejouer depuis le début
        dupliquerait la réponse déjà partiellement affichée à l'élève) —
        l'exception remonte immédiatement, comportement inchangé."""
        chunk = MagicMock()
        chunk.usage_metadata = None
        chunk.text = "Début de réponse"

        def premiere_tentative_partielle():
            yield chunk
            raise errors.ClientError(429, {"error": {"message": "too many"}})

        provider = GeminiProvider.__new__(GeminiProvider)
        provider._model = "gemini-3-flash-preview"
        provider._api_key = "fake-key"
        client = MagicMock()
        client.models.generate_content_stream.side_effect = [premiere_tentative_partielle()]
        provider._client = client

        gen = provider.stream_chat(messages=[], system="s")
        self.assertEqual(next(gen), "Début de réponse")
        with self.assertRaises(GeminiConnectionError):
            next(gen)
        mock_sleep.assert_not_called()
        self.assertEqual(client.models.generate_content_stream.call_count, 1)

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


class TestFinishReasonEtThinkingConfig(unittest.TestCase):
    """Chantier 6 (bug 'réponses parfois coupées') : finish_reason doit être
    capturé (pour distinguer une fin normale d'une troncature), et
    thinking_config doit systématiquement être transmis pour éviter que le
    raisonnement interne des modèles Gemini 3 consomme la quasi-totalité du
    budget max_output_tokens (vérifié par appel réel, voir commentaire dans
    gemini_provider.py::stream_chat)."""

    def test_thinking_level_low_toujours_transmis(self):
        provider = GeminiProvider.__new__(GeminiProvider)
        provider._model = "gemini-3-flash-preview"
        provider._api_key = "fake-key"
        client = MagicMock()
        chunk = MagicMock()
        chunk.usage_metadata = None
        chunk.candidates = None
        chunk.text = "Bonjour !"
        client.models.generate_content_stream.return_value = [chunk]
        provider._client = client

        list(provider.stream_chat(messages=[], system="s", max_tokens=1536))

        _, kwargs = client.models.generate_content_stream.call_args
        self.assertEqual(kwargs["config"].thinking_config.thinking_level, types.ThinkingLevel.LOW)
        self.assertEqual(kwargs["config"].max_output_tokens, 1536)

    def test_finish_reason_stop_capture_sur_fin_normale(self):
        provider = GeminiProvider.__new__(GeminiProvider)
        provider._model = "gemini-3-flash-preview"
        provider._api_key = "fake-key"
        chunk = MagicMock()
        chunk.usage_metadata = None
        chunk.text = "Réponse complète."
        chunk.candidates = [MagicMock(finish_reason="FinishReason.STOP")]
        client = MagicMock()
        client.models.generate_content_stream.return_value = [chunk]
        provider._client = client

        list(provider.stream_chat(messages=[], system="s"))
        self.assertEqual(provider.last_finish_reason, "FinishReason.STOP")

    def test_finish_reason_max_tokens_capture_sur_troncature(self):
        """Reproduit le cas réel observé lors de l'audit (2026-08-25) : le
        modèle s'arrête parce que max_output_tokens est atteint, PAS parce
        que la réponse est terminée — avant ce chantier, ce cas n'était
        distingué nulle part dans le pipeline (voir llm_fallback_service qui
        journalise désormais ce finish_reason)."""
        provider = GeminiProvider.__new__(GeminiProvider)
        provider._model = "gemini-3-flash-preview"
        provider._api_key = "fake-key"
        chunk = MagicMock()
        chunk.usage_metadata = None
        chunk.text = "Réponse tronquée en co"
        chunk.candidates = [MagicMock(finish_reason="FinishReason.MAX_TOKENS")]
        client = MagicMock()
        client.models.generate_content_stream.return_value = [chunk]
        provider._client = client

        list(provider.stream_chat(messages=[], system="s"))
        self.assertEqual(provider.last_finish_reason, "FinishReason.MAX_TOKENS")


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


class TestTimeoutExplicite(unittest.TestCase):
    """Durcissement production : sans timeout explicite, le SDK google-genai
    n'en applique aucun par défaut (voir gemini_provider.DEFAULT_TIMEOUT_MS)."""

    @patch("chatbot.providers.gemini_provider.genai.Client")
    def test_timeout_par_defaut_transmis_au_client(self, mock_client_cls):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "AIzaSy" + "x" * 33}, clear=False):
            GeminiProvider()
        _, kwargs = mock_client_cls.call_args
        self.assertEqual(kwargs["http_options"].timeout, 45_000)

    @patch("chatbot.providers.gemini_provider.genai.Client")
    def test_timeout_configurable_via_variable_environnement(self, mock_client_cls):
        with patch.dict(
            os.environ, {"GEMINI_API_KEY": "AIzaSy" + "x" * 33, "GEMINI_TIMEOUT_MS": "12000"}, clear=False,
        ):
            GeminiProvider()
        _, kwargs = mock_client_cls.call_args
        self.assertEqual(kwargs["http_options"].timeout, 12_000)


if __name__ == "__main__":
    unittest.main()
