"""
Suite dédiée au Chantier 6 (implémentation finale : prix, limites, marge et
mode test Owner, 2026-08-24) — complète (sans le dupliquer) :

- tests/test_quota_service.py (nouvelles valeurs QUOTA_MATRIX : Premium
  CHAT_MESSAGES=25/LLM_CALLS=20, Ultra CHAT_MESSAGES=40/LLM_CALLS=40, déjà
  adaptées avec les tests génériques existants) ;
- tests/test_chantier5_llm_budget.py (mécanique générale du budget LLM_CALLS,
  déjà compatible car ses tests lisent QUOTA_MATRIX dynamiquement — jamais de
  valeur numérique codée en dur pour Premium/Ultra) ;
- tests/test_owner_test_plan_service.py (cycle Free/Premium/Ultra/reset déjà
  couvert de bout en bout, y compris users.plan/Stripe inchangés).

Ce fichier vérifie UNIQUEMENT ce que le Chantier 6 ajoute par-dessus :
1. Le changement de plan Owner via /api/owner/test-plan NE DÉCLENCHE JAMAIS
   le moindre appel à stripe_service (pas seulement "les colonnes n'ont pas
   changé" déjà prouvé ailleurs, mais "la fonction Stripe n'a même pas été
   appelée" — garantie mécanique plus forte) ;
2. La concurrence sur LLM_CALLS avec les VALEURS COMMERCIALES RÉELLES (20
   Premium / 40 Ultra), pas une valeur de test réduite ;
3. Qu'une combinaison de fallbacks (2 tentatives réseau par message) ne
   permet jamais de dépasser le budget LLM_CALLS réel, même répétée sur
   plusieurs messages consécutifs.
"""
import os
import shutil
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

import db
import owner_service
import owner_test_plan_service
import quota_service
import server
import stripe_service
from chatbot import cache as llm_cache
from chatbot import conversation_manager as cm
from chatbot import provider_manager
from chatbot.providers.base import ChatProvider, ProviderUnavailableError
from chatbot.providers.fake_provider import FakeProvider
from plan_service import Plan
from quota_service import QuotaType


class _IsolatedDbTestCase(unittest.TestCase):
    """Même pattern que tests/test_chantier5_llm_budget.py::_IsolatedDbTestCase
    — base SQLite temporaire, jamais data/novamath.db."""

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
        self._saved_chatbot_provider = os.environ.get("CHATBOT_PROVIDER")
        os.environ["GEMINI_API_KEY"] = "test-key"
        os.environ["ANTHROPIC_API_KEY"] = "test-key"
        os.environ.pop("CHATBOT_PROVIDER", None)

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
            ("CHATBOT_PROVIDER", self._saved_chatbot_provider),
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


class _ScriptedProvider(ChatProvider):
    def __init__(self, outcome):
        self._outcome = outcome
        self._model = None

    def stream_chat(self, messages, system, temperature=0.7, max_tokens=1024):
        if self._outcome == "fail":
            raise ProviderUnavailableError("panne simulée de test", durable=True, ttl_seconds=5)
        self.last_usage = {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
        yield f"Réponse réelle de {self._model}."


def _patched_get_provider(script):
    def _get(provider=None, model=None, api_key=None):
        if provider == "fake":
            return FakeProvider(model=model)
        outcome = script.get((provider, model), "fail")
        instance = _ScriptedProvider(outcome)
        instance._model = model
        return instance
    return _get


# ── Volet 1 : aucun appel Stripe pendant un cycle de plan de test Owner ─────
def _register(client):
    import random
    email = f"test{random.randint(1_000_000, 9_999_999)}@gmail.com"
    username = f"testuser{random.randint(100_000, 999_999)}"
    resp = client.post("/api/auth/register", json={
        "email": email, "username": username, "pseudo": "Test",
        "birth_date": "2000-01-01",
        "password": "MotDePasse123!", "confirm_password": "MotDePasse123!",
        "accept_terms": True, "accept_privacy": True,
    })
    user = resp.get_json()["user"]
    csrf = client.get_cookie("nm_csrf").value
    return user, {"X-CSRF-Token": csrf}


class TestOwnerAucuneInteractionStripe(_IsolatedDbTestCase):
    """Points 18/19 de la demande : le cycle Free -> Premium -> Ultra -> Free
    via /api/owner/test-plan ne doit JAMAIS appeler la moindre fonction de
    stripe_service — garantie mécanique (spy), pas seulement déduite d'un
    état de base inchangé (déjà prouvé par ailleurs)."""

    def setUp(self):
        super().setUp()
        self.client = server.app.test_client()
        self.owner_user, self.owner_headers = _register(self.client)
        os.environ["NOVAMATH_OWNER_USER_ID"] = str(self.owner_user["id"])

    def test_cycle_complet_sans_aucun_appel_stripe(self):
        with patch.object(stripe_service, "create_customer", side_effect=AssertionError("create_customer appelé")), \
             patch.object(stripe_service, "create_checkout_session", side_effect=AssertionError("create_checkout_session appelé")), \
             patch.object(stripe_service, "change_plan", side_effect=AssertionError("change_plan appelé")), \
             patch.object(stripe_service, "schedule_downgrade", side_effect=AssertionError("schedule_downgrade appelé")), \
             patch.object(stripe_service, "cancel_subscription", side_effect=AssertionError("cancel_subscription appelé")), \
             patch.object(stripe_service, "create_billing_portal_session", side_effect=AssertionError("create_billing_portal_session appelé")):
            for plan in ("premium", "ultra", "free", "premium"):
                resp = self.client.patch(
                    "/api/owner/test-plan", json={"plan": plan}, headers=self.owner_headers,
                )
                self.assertEqual(resp.status_code, 200)
                self.assertEqual(resp.get_json()["effective_plan"], plan)

        before = db.get_user_by_id(self.owner_user["id"])
        self.assertEqual(before["plan"], "free")
        self.assertIsNone(before["stripe_customer_id"])
        self.assertIsNone(before["stripe_subscription_id"])
        self.assertIsNone(before["stripe_subscription_status"])


class TestUtilisateurNormalStripeInchange(_IsolatedDbTestCase):
    """Point 17 : un utilisateur normal ne peut jamais utiliser la route
    Owner, quelle que soit la valeur envoyée."""

    def test_utilisateur_normal_ne_peut_jamais_patch_owner_test_plan(self):
        self.client = server.app.test_client()
        user, headers = _register(self.client)
        os.environ["NOVAMATH_OWNER_USER_ID"] = str(user["id"] + 999_999)  # jamais CET utilisateur
        resp = self.client.patch("/api/owner/test-plan", json={"plan": "ultra"}, headers=headers)
        self.assertEqual(resp.status_code, 404)
        fresh = db.get_user_by_id(user["id"])
        self.assertEqual(fresh["plan"], "free")


# ── Volet 2 : concurrence avec les valeurs commerciales réelles ────────────
class TestConcurrenceLlmCallsValeursReelles(_IsolatedDbTestCase):
    """Point 22 : la concurrence ne doit jamais permettre de dépasser 20
    (Premium) ni 40 (Ultra) — valeurs RÉELLEMENT configurées dans
    QUOTA_MATRIX depuis le Chantier 6, pas une valeur de test réduite."""

    def _concurrence(self, plan, expected_limit):
        user = self._make_user(f"concurrent_{plan.value}@gmail.com", f"concurrent_{plan.value}", plan)
        self.assertEqual(quota_service.QUOTA_MATRIX[plan][QuotaType.LLM_CALLS], expected_limit)

        successes, failures = [], []
        lock = threading.Lock()

        def worker():
            try:
                quota_service.consume(user, QuotaType.LLM_CALLS)
                with lock:
                    successes.append(1)
            except quota_service.QuotaExceededError:
                with lock:
                    failures.append(1)

        threads = [threading.Thread(target=worker) for _ in range(expected_limit * 2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(successes), expected_limit)
        self.assertEqual(len(failures), expected_limit)
        self.assertEqual(quota_service.get_usage(user, QuotaType.LLM_CALLS), expected_limit)

    def test_premium_20_llm_calls_jamais_depasse(self):
        self._concurrence(Plan.PREMIUM, 20)

    def test_ultra_40_llm_calls_jamais_depasse(self):
        self._concurrence(Plan.ULTRA, 40)


# ── Volet 3 : fallback répété sur plusieurs messages, budget réel ──────────
class TestFallbackRepeteNeDepassePasLeBudgetReel(_IsolatedDbTestCase):
    """Un message Premium dont le premier candidat (Pro) échoue toujours et
    le second (Flash) répond consomme 2 LLM_CALLS par message. Avec la
    limite réelle de 20/jour, le budget doit être épuisé après exactement 10
    messages — le 11e ne doit déclencher AUCUN appel réseau supplémentaire,
    tout en continuant à répondre normalement (dégradation silencieuse) et
    en continuant à consommer CHAT_MESSAGES normalement."""

    def test_dixieme_message_epuise_le_budget_onzieme_degrade_silencieusement(self):
        user = self._make_user("fallback_repete@gmail.com", "fallback_repete", Plan.PREMIUM)
        conv = cm.create_conversation(user["id"], "Test Chantier 6")
        script = {
            ("gemini", "gemini-3.1-pro-preview"): "fail",
            ("gemini", "gemini-3-flash-preview"): "succeed",
        }

        with patch.object(provider_manager, "get_provider", side_effect=_patched_get_provider(script)):
            for i in range(10):
                # Sans ce clear, l'échec "durable" de Pro (voir _ScriptedProvider,
                # ProviderUnavailableError(durable=True)) le mettrait en cache
                # d'indisponibilité (voir provider_manager.mark_unavailable) dès
                # le premier message — les messages suivants sauteraient Pro
                # sans même le retenter, donc ne consommeraient plus qu'1
                # LLM_CALL (Flash seul) au lieu de 2. On force ici le scénario
                # demandé (2 tentatives réseau réelles à CHAQUE message) en
                # simulant un fournisseur qui échoue à nouveau à chaque fois,
                # jamais mis en cache entre deux messages.
                provider_manager._unavailability_cache.clear()
                text = "".join(cm.stream_reply(user, conv["id"], f"Question {i}."))
                self.assertEqual(text, "Réponse réelle de gemini-3-flash-preview.")

            self.assertEqual(quota_service.get_usage(user, QuotaType.LLM_CALLS), 20)
            self.assertEqual(quota_service.get_usage(user, QuotaType.CHAT_MESSAGES), 10)

            appelés = []
            real_get_provider = provider_manager.get_provider

            def _tracking_get(provider=None, model=None, api_key=None):
                appelés.append((provider, model))
                return _patched_get_provider(script)(provider=provider, model=model, api_key=api_key)

            with patch.object(provider_manager, "get_provider", side_effect=_tracking_get):
                text = "".join(cm.stream_reply(user, conv["id"], "Question 11 — budget épuisé."))

        self.assertTrue(text)  # une réponse est bien produite (mode local/dégradé)
        self.assertNotIn(("gemini", "gemini-3.1-pro-preview"), appelés)
        self.assertNotIn(("gemini", "gemini-3-flash-preview"), appelés)
        # Budget LLM_CALLS inchangé (aucune tentative réseau supplémentaire).
        self.assertEqual(quota_service.get_usage(user, QuotaType.LLM_CALLS), 20)
        # CHAT_MESSAGES continue de fonctionner normalement.
        self.assertEqual(quota_service.get_usage(user, QuotaType.CHAT_MESSAGES), 11)


if __name__ == "__main__":
    unittest.main()
