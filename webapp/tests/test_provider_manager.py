"""
Suite dédiée au cache d'indisponibilité de provider_manager.py — audit du
2026-07-26 (classification fine des pannes Gemini) : le TTL de ce cache
n'est plus figé à 15 minutes pour toute panne durable, un fournisseur peut
préciser un TTL adapté à la famille de panne détectée via
ProviderUnavailableError.ttl_seconds (voir gemini_provider.py::_classify_error
et llm_fallback_service.py, qui transmet ce TTL à mark_unavailable())."""
import time
import unittest

from chatbot import provider_manager
from chatbot.providers.base import ProviderUnavailableError
from chatbot.services import llm_fallback_service


class TestTTLDuCacheDIndisponibilite(unittest.TestCase):
    def tearDown(self):
        provider_manager.clear_unavailable("gemini", "gemini-3-flash-preview")

    def test_ttl_par_defaut_si_non_precise(self):
        provider_manager.mark_unavailable("gemini", "gemini-3-flash-preview", reason="test")
        entry = provider_manager._unavailability_cache[("gemini", "gemini-3-flash-preview")]
        self.assertAlmostEqual(
            entry["expires_at"] - entry["marked_at"],
            provider_manager.UNAVAILABILITY_TTL_SECONDS,
            delta=1,
        )

    def test_ttl_personnalise_est_bien_applique(self):
        provider_manager.mark_unavailable(
            "gemini", "gemini-3-flash-preview", reason="quota journalier", ttl_seconds=12 * 3600,
        )
        entry = provider_manager._unavailability_cache[("gemini", "gemini-3-flash-preview")]
        self.assertAlmostEqual(entry["expires_at"] - entry["marked_at"], 12 * 3600, delta=1)

    def test_format_ttl_human_minutes_et_heures(self):
        self.assertEqual(provider_manager._format_ttl_human(300), "5 min")
        self.assertEqual(provider_manager._format_ttl_human(3600), "1h")
        self.assertEqual(provider_manager._format_ttl_human(12 * 3600), "12h")
        self.assertEqual(provider_manager._format_ttl_human(5400), "1.5h")


class TestLlmFallbackServiceTransmetLeTTL(unittest.TestCase):
    """llm_fallback_service.generate() doit transmettre le ttl_seconds de
    l'exception à mark_unavailable() quand il est précisé, et laisser le
    défaut de provider_manager s'appliquer sinon."""

    def tearDown(self):
        provider_manager.clear_unavailable("fake", None)

    def test_ttl_seconds_de_lexception_est_transmis_a_mark_unavailable(self):
        # provider_name="fake" : dernier maillon de la chaîne (voir
        # llm_fallback_service.generate(), `if yielded_any or provider_name
        # == "fake": raise`) — évite une boucle infinie de repli, sans
        # affecter ce qui est testé ici (la transmission du ttl_seconds à
        # mark_unavailable(), qui a lieu AVANT ce test de sortie de boucle).
        class _FailingProvider:
            last_usage = None

            def current_model(self):
                return None

            def stream_chat(self, messages, system, temperature=0.6, max_tokens=1024):
                raise ProviderUnavailableError("panne durable de test", durable=True, ttl_seconds=999)
                yield  # pragma: no cover - rend la fonction générateur

        original_select = provider_manager.select_llm_for_user
        original_get_provider = provider_manager.get_provider
        provider_manager.select_llm_for_user = lambda user, exclude=None: ("fake", None)
        provider_manager.get_provider = lambda provider=None, model=None, api_key=None: _FailingProvider()
        try:
            with self.assertRaises(ProviderUnavailableError):
                list(llm_fallback_service.generate([], "system", {}))
        finally:
            provider_manager.select_llm_for_user = original_select
            provider_manager.get_provider = original_get_provider

        entry = provider_manager._unavailability_cache[("fake", None)]
        self.assertAlmostEqual(entry["expires_at"] - entry["marked_at"], 999, delta=1)


class TestLlmFallbackServiceModeDegrade(unittest.TestCase):
    """Audit du mode dégradé (2026-07-26) : llm_fallback_service.generate()
    doit tenter degraded_mode_service.try_answer() AVANT d'appeler
    provider.stream_chat() quand le candidat résolu est "fake" — voir
    _stream_chunks(). Un stub FakeProvider qui lève s'il est appelé prouve
    que le mode dégradé a bien répondu à sa place quand intent_result
    contient une notion connue."""

    def tearDown(self):
        provider_manager.clear_unavailable("fake", None)

    def test_mode_degrade_repond_avant_dappeler_fakeprovider(self):
        class _FakeProviderQuiNeDoitJamaisEtreAppele:
            last_usage = None

            def current_model(self):
                return "moteur-novamath"

            def stream_chat(self, messages, system, temperature=0.6, max_tokens=1024):
                raise AssertionError(
                    "FakeProvider.stream_chat() n'aurait jamais dû être appelé : "
                    "le mode dégradé avait de quoi répondre (notion connue)."
                )
                yield  # pragma: no cover

        original_select = provider_manager.select_llm_for_user
        original_get_provider = provider_manager.get_provider
        provider_manager.select_llm_for_user = lambda user, exclude=None: ("fake", None)
        provider_manager.get_provider = lambda provider=None, model=None, api_key=None: _FakeProviderQuiNeDoitJamaisEtreAppele()
        try:
            intent_result = {
                "chapter_id": "Chapitre_13", "notion_id": "theoreme-de-pythagore", "topic_inherited": True,
            }
            messages = [{"role": "user", "content": "je n'ai toujours pas compris"}]
            chunks = list(llm_fallback_service.generate(
                messages, "system", {}, intent_result=intent_result, class_level="troisieme",
            ))
        finally:
            provider_manager.select_llm_for_user = original_select
            provider_manager.get_provider = original_get_provider

        full_reply = "".join(chunks)
        self.assertIn("Pythagore", full_reply)

    def test_sans_rien_a_exploiter_fakeprovider_repond_normalement(self):
        """Aucun intent_result/class_level fourni (comme un appelant qui ne
        les transmettrait pas) : le mode dégradé ne trouve rien, FakeProvider
        reprend son rôle habituel de dernier recours."""
        from chatbot.providers.fake_provider import NO_MATCH_ANSWERS

        original_select = provider_manager.select_llm_for_user
        provider_manager.select_llm_for_user = lambda user, exclude=None: ("fake", None)
        try:
            messages = [{"role": "user", "content": "xyzxyz1234 incompréhensible xyzxyz5678"}]
            chunks = list(llm_fallback_service.generate(messages, "", {}))
        finally:
            provider_manager.select_llm_for_user = original_select

        self.assertIn("".join(chunks), NO_MATCH_ANSWERS)


if __name__ == "__main__":
    unittest.main()
