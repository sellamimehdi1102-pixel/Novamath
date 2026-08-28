"""
Suite dédiée au Chantier 6 "bug streaming chatbot + mauvais chapitre
Entraînement" (2026-08-25) — complète les suites existantes
(test_gemini_provider.py/test_anthropic_provider.py couvrent déjà la capture
de finish_reason par provider ; test_chantier2_routing_fallback.py couvre
déjà la traversée de la chaîne de fallback) sans les dupliquer. Deux volets :

- TestJournalisationTroncatureMaxTokens : llm_fallback_service.generate()
  journalise (log WARNING) une réponse tronquée par max_tokens, jamais avant
  ce chantier — vérifié via le seul point mocké (provider_manager.get_provider),
  jamais la boucle de fallback elle-même.
- TestPrixEtQuotasInchanges : garde-fou explicite demandé par ce chantier —
  prix commerciaux et limites CHAT_MESSAGES/LLM_CALLS doivent rester
  strictement identiques à avant (aucune régression de politique tarifaire).
"""
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import db
import quota_service
import stripe_service
from chatbot import cache as llm_cache
from chatbot import conversation_manager as cm
from chatbot import provider_manager
from chatbot.providers.base import ChatProvider
from plan_service import Plan
from quota_service import QuotaType


class _IsolatedDbTestCase(unittest.TestCase):
    """Même pattern que test_chantier2_routing_fallback.py — base SQLite
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


class _TruncatedProvider(ChatProvider):
    """Simule un provider qui répond normalement mais dont le finish_reason
    indique une troncature par max_tokens — reproduit exactement le cas prouvé
    par appel réel (audit 2026-08-25, voir gemini_provider.py::stream_chat)."""

    def __init__(self, finish_reason):
        self._finish_reason = finish_reason
        self._model = "gemini-3-flash-preview"

    def stream_chat(self, messages, system, temperature=0.7, max_tokens=1024):
        self.last_usage = {"prompt_tokens": 100, "completion_tokens": 40, "total_tokens": 1024}
        self.last_finish_reason = self._finish_reason
        yield "Réponse tronquée en co"

    def current_model(self):
        return self._model


class TestJournalisationTroncatureMaxTokens(_IsolatedDbTestCase):
    def test_finish_reason_max_tokens_est_journalise_en_warning(self):
        user = self._make_user("eleve_trunc@gmail.com", "eleve_trunc", Plan.PREMIUM)
        conv = cm.create_conversation(user["id"], "Test Chantier 6")
        provider = _TruncatedProvider("FinishReason.MAX_TOKENS")
        with patch.object(provider_manager, "get_provider", return_value=provider):
            with self.assertLogs("chatbot.llm_fallback_service", level="WARNING") as ctx:
                text = "".join(cm.stream_reply(user, conv["id"], "Explique-moi un théorème avancé de topologie algébrique."))
        self.assertEqual(text, "Réponse tronquée en co")
        self.assertTrue(any("tronqu" in msg for msg in ctx.output))

    def test_finish_reason_stop_ne_declenche_aucun_warning(self):
        user = self._make_user("eleve_ok@gmail.com", "eleve_ok", Plan.PREMIUM)
        conv = cm.create_conversation(user["id"], "Test Chantier 6")
        provider = _TruncatedProvider("FinishReason.STOP")
        with patch.object(provider_manager, "get_provider", return_value=provider):
            # assertNoLogs n'existe qu'à partir de Python 3.10 — vérifie
            # directement qu'aucun record WARNING ne mentionne "tronqu".
            import logging
            records = []
            handler = logging.Handler()
            handler.emit = lambda record: records.append(record)
            logger = logging.getLogger("chatbot.llm_fallback_service")
            logger.addHandler(handler)
            try:
                "".join(cm.stream_reply(user, conv["id"], "Explique-moi un théorème avancé de topologie algébrique."))
            finally:
                logger.removeHandler(handler)
        self.assertFalse(any("tronqu" in r.getMessage() for r in records if r.levelno >= logging.WARNING))


class TestPrixEtQuotasInchanges(unittest.TestCase):
    """Garde-fou explicite du Chantier 6 (bug streaming/entraînement) : ce
    chantier ne doit modifier NI les prix commerciaux NI les limites — vérifié
    ici en négatif, pour qu'une régression future soit détectée immédiatement.

    Free CHAT_MESSAGES est passé à 15 lors du chantier "Réduction quota Free"
    (2026-08-25, postérieur au Chantier 6 que cette classe protège) — mise à
    jour délibérée, pas une régression : voir quota_service.py::QUOTA_MATRIX."""

    def test_quota_matrix_inchangee(self):
        self.assertEqual(quota_service.QUOTA_MATRIX[Plan.FREE][QuotaType.CHAT_MESSAGES], 15)
        self.assertEqual(quota_service.QUOTA_MATRIX[Plan.PREMIUM][QuotaType.CHAT_MESSAGES], 25)
        self.assertEqual(quota_service.QUOTA_MATRIX[Plan.PREMIUM][QuotaType.LLM_CALLS], 20)
        self.assertEqual(quota_service.QUOTA_MATRIX[Plan.ULTRA][QuotaType.CHAT_MESSAGES], 40)
        self.assertEqual(quota_service.QUOTA_MATRIX[Plan.ULTRA][QuotaType.LLM_CALLS], 40)
        self.assertEqual(quota_service.QUOTA_MATRIX[Plan.FREE][QuotaType.LLM_CALLS], quota_service.UNLIMITED)

    @unittest.skipUnless(
        os.environ.get("STRIPE_SECRET_KEY") and os.environ.get("STRIPE_PRICE_PREMIUM") and os.environ.get("STRIPE_PRICE_ULTRA"),
        "Nécessite une vraie clé Stripe (lecture seule) — sauté si absente de l'environnement de test.",
    )
    def test_prix_stripe_inchanges(self):
        premium_id = stripe_service.resolve_price_id(Plan.PREMIUM)
        ultra_id = stripe_service.resolve_price_id(Plan.ULTRA)
        import stripe
        stripe.api_key = os.environ["STRIPE_SECRET_KEY"]
        premium = stripe.Price.retrieve(premium_id)
        ultra = stripe.Price.retrieve(ultra_id)
        self.assertEqual(premium["unit_amount"], 699)
        self.assertEqual(premium["currency"], "eur")
        self.assertEqual(ultra["unit_amount"], 1299)
        self.assertEqual(ultra["currency"], "eur")


if __name__ == "__main__":
    unittest.main()
