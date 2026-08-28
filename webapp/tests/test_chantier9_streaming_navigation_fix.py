"""
Suite dédiée au Chantier 9 "bug streaming chatbot + mauvais chapitre
Entraînement, malgré le premier correctif du Chantier 6" (2026-08-25).

Diagnostic (voir rapport final) : le Chantier 6 avait déjà relevé
_DEFAULT_MAX_TOKENS de 1024 à 1536 et réduit le budget de réflexion Gemini
(thinking_level="low"), mais la troncature réapparaissait — reproduite ICI
par appel réel à l'API (hors suite automatisée, voir le rapport) sur DEUX
questions pédagogiques réalistes et SIMPLES : gemini-3.1-pro-preview et
claude-sonnet-5 coupaient encore leur réponse à 1536 tokens. Relevé à 2500,
revérifié par le même appel réel : réponse complète sur les 3 fournisseurs.

Volets couverts ici (ceux qui ne sont PAS déjà couverts par
test_chantier6_streaming_fix.py / test_chantier2_routing_fallback.py /
test_gemini_provider.py / test_anthropic_provider.py, jamais dupliqués) :

- TestNouveauPlafondMaxTokens : _DEFAULT_MAX_TOKENS vaut bien 2500 et cette
  valeur est réellement transmise au provider (pas seulement définie).
- TestReponseMultiParagrapheEtMultiChunks : une réponse livrée en PLUSIEURS
  fragments SSE (multi-chunks), avec plusieurs paragraphes et une conclusion
  après le dernier paragraphe, est reconstituée et persistée intégralement en
  base — jamais tronquée par l'agrégation elle-même.
- TestBasculeProVersFlashPreserveLaReponse : un échec du premier candidat
  (fallback) ne doit jamais amputer la réponse finale du candidat de repli.
- TestSyncPlafondAffiche : le plafond affiché à l'admin (settings_service)
  reste synchronisé avec la valeur réellement utilisée par le pipeline.
"""
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import db
import settings_service
from chatbot import cache as llm_cache
from chatbot import conversation_manager as cm
from chatbot import provider_manager
from chatbot.providers.base import ChatProvider, ProviderUnavailableError
from chatbot.services import llm_fallback_service
from plan_service import Plan


class _IsolatedDbTestCase(unittest.TestCase):
    """Même pattern que test_chantier6_streaming_fix.py — base SQLite
    temporaire, jamais data/novamath.db."""

    def setUp(self):
        llm_cache.clear()
        provider_manager._unavailability_cache.clear()
        self._tmp_dir = tempfile.mkdtemp()
        self._data_dir_backup = db.DATA_DIR
        self._db_path_backup = db.DB_PATH
        db.DATA_DIR = Path(self._tmp_dir)
        db.DB_PATH = db.DATA_DIR / "novamath.db"
        db.init_db()

        self._saved_owner_env = os.environ.get("NOVAMATH_OWNER_USER_ID")
        os.environ.pop("NOVAMATH_OWNER_USER_ID", None)
        self._saved_gemini_key = os.environ.get("GEMINI_API_KEY")
        self._saved_anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
        os.environ["GEMINI_API_KEY"] = "test-key"
        os.environ["ANTHROPIC_API_KEY"] = "test-key"

    def tearDown(self):
        llm_cache.clear()
        provider_manager._unavailability_cache.clear()
        db.DATA_DIR = self._data_dir_backup
        db.DB_PATH = self._db_path_backup
        shutil.rmtree(self._tmp_dir, ignore_errors=True)
        for key, saved in (
            ("NOVAMATH_OWNER_USER_ID", self._saved_owner_env),
            ("GEMINI_API_KEY", self._saved_gemini_key),
            ("ANTHROPIC_API_KEY", self._saved_anthropic_key),
        ):
            if saved is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = saved

    def _make_user(self, email, username, plan=Plan.FREE):
        user_id = db.create_user(email, username, "Élève", "hash")
        if plan is not Plan.FREE:
            db.set_stripe_subscription(user_id, "sub_test", plan.value, "active")
        return db.get_user_by_id(user_id)


class _CapturingProvider(ChatProvider):
    """N'échoue jamais — capture les kwargs réellement transmis par
    llm_fallback_service, pour prouver que le nouveau plafond n'est pas
    seulement défini mais réellement propagé jusqu'à l'appel provider."""

    def __init__(self, chunks, model="gemini-3-flash-preview"):
        self._chunks = chunks
        self._model = model
        self.received_kwargs = None

    def stream_chat(self, messages, system, temperature=0.7, max_tokens=1024):
        self.received_kwargs = {"temperature": temperature, "max_tokens": max_tokens}
        self.last_usage = {"prompt_tokens": 50, "completion_tokens": 200, "total_tokens": 250}
        self.last_finish_reason = "STOP"
        yield from self._chunks

    def current_model(self):
        return self._model


class TestNouveauPlafondMaxTokens(_IsolatedDbTestCase):
    def test_default_max_tokens_vaut_2500(self):
        self.assertEqual(llm_fallback_service._DEFAULT_MAX_TOKENS, 2500)
        self.assertEqual(llm_fallback_service._ai_default_max_tokens(), 2500)

    def test_2500_est_reellement_transmis_au_provider(self):
        user = self._make_user("eleve_max@gmail.com", "eleve_max", Plan.ULTRA)
        conv = cm.create_conversation(user["id"], "Test Chantier 9")
        provider = _CapturingProvider(["Réponse complète."])
        with patch.object(provider_manager, "get_provider", return_value=provider):
            "".join(cm.stream_reply(user, conv["id"], "Explique-moi un théorème avancé de topologie algébrique."))
        self.assertEqual(provider.received_kwargs["max_tokens"], 2500)

    def test_admin_peut_toujours_configurer_une_valeur_differente(self):
        # Le plafond reste réellement configurable (voir settings_service) —
        # ce chantier ne fige jamais la valeur en dur au-delà de la constante
        # de repli, contrairement à un chiffre codé en dur non ajustable.
        user = self._make_user("eleve_cfg@gmail.com", "eleve_cfg", Plan.ULTRA)
        conv = cm.create_conversation(user["id"], "Test Chantier 9")
        db.set_system_setting("ai_max_response_tokens_default", "3000")
        provider = _CapturingProvider(["Réponse."])
        with patch.object(provider_manager, "get_provider", return_value=provider):
            "".join(cm.stream_reply(user, conv["id"], "Explique-moi un théorème avancé de topologie algébrique."))
        self.assertEqual(provider.received_kwargs["max_tokens"], 3000)


class TestReponseMultiParagrapheEtMultiChunks(_IsolatedDbTestCase):
    """Reproduit la forme réelle observée lors du test API direct (Chantier 9,
    voir rapport) : plusieurs paragraphes, livrés en plusieurs fragments SSE
    successifs, avec une phrase de conclusion APRÈS le dernier paragraphe."""

    def test_plusieurs_chunks_multi_paragraphes_avec_conclusion_sont_reconstitues(self):
        user = self._make_user("eleve_multi@gmail.com", "eleve_multi", Plan.PREMIUM)
        conv = cm.create_conversation(user["id"], "Test Chantier 9")
        chunks = [
            "## Méthode\n\nPour étudier les variations, ",
            "on calcule d'abord la dérivée f'(x).\n\n",
            "## Exemple\n\nSoit f(x) = x² - 4x + 3, alors f'(x) = 2x - 4.\n\n",
            "## Conclusion\n\nOn retient : signe de f' -> sens de variation de f.",
        ]
        provider = _CapturingProvider(chunks)
        with patch.object(provider_manager, "get_provider", return_value=provider):
            full_text = "".join(
                cm.stream_reply(user, conv["id"], "Explique-moi un théorème avancé de topologie algébrique, avec sa démonstration complète.")
            )
        expected = "".join(chunks)
        self.assertEqual(full_text, expected)
        self.assertIn("Conclusion", full_text)
        self.assertTrue(full_text.strip().endswith("sens de variation de f."))

        # Persistée intégralement en base — jamais tronquée par l'agrégation
        # des chunks (voir conversation_manager._generate_assistant_reply,
        # full_reply.append(chunk) puis "".join(full_reply)).
        messages = db.list_messages(conv["id"])
        assistant_msg = next(m for m in messages if m["role"] == "assistant")
        self.assertEqual(assistant_msg["content"], expected)

    def test_reponse_courte_simple_non_affectee(self):
        user = self._make_user("eleve_court@gmail.com", "eleve_court", Plan.PREMIUM)
        conv = cm.create_conversation(user["id"], "Test Chantier 9")
        provider = _CapturingProvider(["3x + 2 = 8 donc x = 2."])
        with patch.object(provider_manager, "get_provider", return_value=provider):
            full_text = "".join(cm.stream_reply(user, conv["id"], "Explique-moi un théorème avancé de topologie algébrique en une phrase."))
        self.assertEqual(full_text, "3x + 2 = 8 donc x = 2.")


class _FailingThenCapturingSelector:
    """Force select_llm_for_user à renvoyer d'abord un candidat "pro" qui
    échouera (panne durable simulée), puis un candidat "flash" qui réussit —
    reproduit un vrai scénario de bascule Pro -> Flash (voir Partie 5, item 8
    de la demande) sans dupliquer test_chantier2_routing_fallback.py qui
    couvre déjà la mécanique générique de la boucle de fallback elle-même."""

    def __init__(self, real_select):
        self._real_select = real_select
        self.calls = 0

    def __call__(self, user, exclude=None):
        self.calls += 1
        if self.calls == 1:
            return ("gemini", "gemini-3.1-pro-preview")
        return ("gemini", "gemini-3-flash-preview")


class TestBasculeProVersFlashPreserveLaReponse(_IsolatedDbTestCase):
    def test_echec_pro_puis_succes_flash_ne_perd_aucun_texte(self):
        user = self._make_user("eleve_fallback@gmail.com", "eleve_fallback", Plan.ULTRA)
        conv = cm.create_conversation(user["id"], "Test Chantier 9")

        class _FailingProProvider(ChatProvider):
            def stream_chat(self, messages, system, temperature=0.7, max_tokens=1024):
                raise ProviderUnavailableError("quota Pro épuisé", durable=True, ttl_seconds=60)
                yield  # pragma: no cover

            def current_model(self):
                return "gemini-3.1-pro-preview"

        flash_provider = _CapturingProvider(
            ["Réponse complète du modèle de repli, texte intégral préservé."],
            model="gemini-3-flash-preview",
        )
        providers_by_model = {
            "gemini-3.1-pro-preview": _FailingProProvider(),
            "gemini-3-flash-preview": flash_provider,
        }

        def fake_get_provider(provider, model, api_key=None):
            return providers_by_model[model]

        selector = _FailingThenCapturingSelector(provider_manager.select_llm_for_user)
        with patch.object(provider_manager, "select_llm_for_user", side_effect=selector), \
             patch.object(provider_manager, "get_provider", side_effect=fake_get_provider):
            full_text = "".join(cm.stream_reply(user, conv["id"], "Explique-moi un vrai théorème"))

        self.assertEqual(full_text, "Réponse complète du modèle de repli, texte intégral préservé.")
        messages = db.list_messages(conv["id"])
        assistant_msg = next(m for m in messages if m["role"] == "assistant")
        self.assertEqual(assistant_msg["content"], full_text)
        self.assertEqual(assistant_msg["provider"], "gemini")


class TestSyncPlafondAffiche(unittest.TestCase):
    """Le plafond affiché à l'admin (settings_service, quand aucune valeur
    n'est configurée) doit rester synchronisé avec _DEFAULT_MAX_TOKENS
    réellement utilisé par le pipeline — l'écart entre 1024 (affiché) et 1536
    (réellement utilisé) découvert lors de l'audit de ce chantier était trompeur
    pour l'admin, même s'il n'affectait jamais le comportement réel du chatbot."""

    def test_default_schema_synchronise_avec_le_pipeline(self):
        self.assertEqual(
            settings_service.SETTINGS_SCHEMA["ai_max_response_tokens_default"]["default"],
            llm_fallback_service._DEFAULT_MAX_TOKENS,
        )


if __name__ == "__main__":
    unittest.main()
