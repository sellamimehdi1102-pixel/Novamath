"""
Suite dédiée au Chantier 5 (protection de la marge, quotas LLM réels et
anti-abus, 2026-08-24) — complète (sans le dupliquer) :

- tests/test_quota_service.py (moteur générique, concurrence sur
  QuotaType.CHAT_MESSAGES) ;
- tests/test_chatbot_quota_integration.py (câblage HTTP de CHAT_MESSAGES) ;
- tests/test_chantier2_routing_fallback.py (ordre exact de la chaîne de
  repli, jamais réévalué ici — ce chantier n'a pas touché provider_manager.py) ;
- tests/test_chantier3_cost_accounting.py (comptabilité des tokens/coûts,
  jamais réévaluée ici — ce chantier n'a pas touché ai_provider_service.py).

Ce fichier vérifie UNIQUEMENT ce que le Chantier 5 a ajouté :
1. QuotaType.LLM_CALLS, strictement indépendant de CHAT_MESSAGES ;
2. le point d'incrémentation (llm_fallback_service.generate()) : un
   incrément par tentative réseau RÉELLE, jamais pour "fake" ;
3. la dégradation silencieuse (jamais de blocage/redirection) quand le
   budget LLM_CALLS est épuisé ;
4. la compatibilité avec le mécanisme Owner existant, les paliers Free/
   Premium/Ultra, et la concurrence ;
5. la limite de longueur de message (MAX_CHATBOT_MESSAGE_CHARS) et la
   non-régression du rate limit HTTP existant (30/min).

Deux styles de test, comme le reste du projet :
- base SQLite temporaire (jamais data/novamath.db) pour la mécanique interne
  du budget (mêmes patterns que test_chantier2_routing_fallback.py) ;
- server.app.test_client() contre la vraie base (même convention que
  test_chatbot_quota_integration.py) pour les tests HTTP de bout en bout.
"""
import os
import random
import shutil
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

import db
import server
import quota_service
from chatbot import cache as llm_cache
from chatbot import conversation_manager as cm
from chatbot import provider_manager
from chatbot.providers.base import ChatProvider, ProviderUnavailableError
from chatbot.providers.fake_provider import FakeProvider
from plan_service import Plan
from quota_service import QuotaType


# ── Volet 1 : mécanique interne du budget (base isolée) ─────────────────────

class _IsolatedDbTestCase(unittest.TestCase):
    """Même pattern que test_chantier2_routing_fallback.py::_IsolatedDbTestCase
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
    """Identique à test_chantier2_routing_fallback.py::_ScriptedProvider —
    échoue ou réussit selon un script, sans jamais toucher au réseau."""

    def __init__(self, outcome):
        self._outcome = outcome
        self._model = None

    def stream_chat(self, messages, system, temperature=0.7, max_tokens=1024):
        if self._outcome == "fail":
            raise ProviderUnavailableError("panne simulée de test", durable=True, ttl_seconds=5)
        self.last_usage = {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
        yield f"Réponse réelle de {self._model}."


def _patched_get_provider(script, appelés=None):
    """Comme test_chantier2_routing_fallback.py::_patched_get_provider, avec
    en plus la trace optionnelle (`appelés`) de chaque (provider, modèle)
    réellement instancié — utile pour prouver qu'AUCUN appel n'a été fait
    vers un candidat donné (ex: budget épuisé, ou hors du plan de l'élève)."""
    def _get(provider=None, model=None, api_key=None):
        if appelés is not None:
            appelés.append((provider, model))
        if provider == "fake":
            return FakeProvider(model=model)
        outcome = script.get((provider, model), "fail")
        instance = _ScriptedProvider(outcome)
        instance._model = model
        return instance
    return _get


class TestIndependanceChatMessagesEtLlmCalls(_IsolatedDbTestCase):
    """Point 1 : les deux compteurs ne se touchent jamais."""

    def test_consommer_llm_calls_ne_touche_pas_chat_messages(self):
        user = self._make_user("indep1@gmail.com", "indep1", Plan.PREMIUM)
        quota_service.consume(user, QuotaType.LLM_CALLS)
        self.assertEqual(quota_service.get_usage(user, QuotaType.LLM_CALLS), 1)
        self.assertEqual(quota_service.get_usage(user, QuotaType.CHAT_MESSAGES), 0)

    def test_consommer_chat_messages_ne_touche_pas_llm_calls(self):
        user = self._make_user("indep2@gmail.com", "indep2", Plan.PREMIUM)
        quota_service.consume(user, QuotaType.CHAT_MESSAGES)
        self.assertEqual(quota_service.get_usage(user, QuotaType.CHAT_MESSAGES), 1)
        self.assertEqual(quota_service.get_usage(user, QuotaType.LLM_CALLS), 0)


class TestComptageParTourReel(_IsolatedDbTestCase):
    """Points 2/3/4/9/10/11 : exemples exacts fournis par la demande."""

    def _run(self, plan, script, message="Question test."):
        user = self._make_user(f"tour_{plan.value}@gmail.com", f"tour_{plan.value}", plan)
        conv = cm.create_conversation(user["id"], "Test Chantier 5")
        with patch.object(provider_manager, "get_provider", side_effect=_patched_get_provider(script)):
            text = "".join(cm.stream_reply(user, conv["id"], message))
        return user, text

    def test_message_reussi_du_premier_coup_plus1_chat_plus1_llm(self):
        user, text = self._run(Plan.PREMIUM, {("gemini", "gemini-3.1-pro-preview"): "succeed"})
        self.assertTrue(text)
        self.assertEqual(quota_service.get_usage(user, QuotaType.CHAT_MESSAGES), 1)
        self.assertEqual(quota_service.get_usage(user, QuotaType.LLM_CALLS), 1)

    def test_premium_pro_echoue_flash_reussit_plus1_chat_plus2_llm(self):
        script = {
            ("gemini", "gemini-3.1-pro-preview"): "fail",
            ("gemini", "gemini-3-flash-preview"): "succeed",
        }
        user, text = self._run(Plan.PREMIUM, script)
        self.assertEqual(text, "Réponse réelle de gemini-3-flash-preview.")
        self.assertEqual(quota_service.get_usage(user, QuotaType.CHAT_MESSAGES), 1)
        self.assertEqual(quota_service.get_usage(user, QuotaType.LLM_CALLS), 2)

    def test_ultra_claude_et_pro_echouent_flash_reussit_plus1_chat_plus3_llm(self):
        script = {
            ("anthropic", "claude-sonnet-5"): "fail",
            ("gemini", "gemini-3.1-pro-preview"): "fail",
            ("gemini", "gemini-3-flash-preview"): "succeed",
        }
        user, text = self._run(Plan.ULTRA, script)
        self.assertEqual(text, "Réponse réelle de gemini-3-flash-preview.")
        self.assertEqual(quota_service.get_usage(user, QuotaType.CHAT_MESSAGES), 1)
        self.assertEqual(quota_service.get_usage(user, QuotaType.LLM_CALLS), 3)

    def test_toutes_les_tentatives_reseau_echouent_sont_comptees_fake_non_compte(self):
        """3 tentatives réseau réelles (Claude, Pro, Flash), toutes échouent,
        repli final sur "fake" (mode local/dégradé) : +1 CHAT_MESSAGES,
        +3 LLM_CALLS (pas +4 — "fake" n'est jamais un appel réseau réel)."""
        script = {
            ("anthropic", "claude-sonnet-5"): "fail",
            ("gemini", "gemini-3.1-pro-preview"): "fail",
            ("gemini", "gemini-3-flash-preview"): "fail",
        }
        user, text = self._run(Plan.ULTRA, script)
        self.assertTrue(text)
        self.assertEqual(quota_service.get_usage(user, QuotaType.CHAT_MESSAGES), 1)
        self.assertEqual(quota_service.get_usage(user, QuotaType.LLM_CALLS), 3)

        logs = db.list_ai_request_logs_for_user(user["id"], limit=5)
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0]["provider"], "fake")
        self.assertEqual(logs[0]["estimated_cost"], 0)  # point 21/23 : aucun coût fictif


class TestBudgetLlmCallsEpuise(_IsolatedDbTestCase):
    """Points 5/6/7/8 : comportement à l'épuisement du budget LLM_CALLS —
    jamais de blocage, jamais de redirection, dégradation silencieuse."""

    def _epuiser_budget(self, user):
        limit = quota_service.QUOTA_MATRIX[Plan.PREMIUM][QuotaType.LLM_CALLS]
        db.increment_daily_usage(user["id"], QuotaType.LLM_CALLS.value, quota_service._today(), limit)
        return limit

    def test_budget_atteint_aucun_appel_reseau_supplementaire(self):
        user = self._make_user("budget1@gmail.com", "budget1", Plan.PREMIUM)
        self._epuiser_budget(user)
        conv = cm.create_conversation(user["id"], "Test")
        appelés = []
        script = {
            ("gemini", "gemini-3.1-pro-preview"): "succeed",
            ("gemini", "gemini-3-flash-preview"): "succeed",
        }
        with patch.object(provider_manager, "get_provider", side_effect=_patched_get_provider(script, appelés)):
            text = "".join(cm.stream_reply(user, conv["id"], "Question."))

        self.assertTrue(text)  # jamais un plantage
        self.assertNotIn(("gemini", "gemini-3.1-pro-preview"), appelés)
        self.assertNotIn(("gemini", "gemini-3-flash-preview"), appelés)
        self.assertIn(("fake", None), appelés)

    def test_budget_atteint_message_utilisateur_non_bloque_chat_messages_normal(self):
        user = self._make_user("budget2@gmail.com", "budget2", Plan.PREMIUM)
        limit = self._epuiser_budget(user)
        conv = cm.create_conversation(user["id"], "Test")
        script = {("gemini", "gemini-3.1-pro-preview"): "succeed"}
        with patch.object(provider_manager, "get_provider", side_effect=_patched_get_provider(script)):
            text = "".join(cm.stream_reply(user, conv["id"], "Question."))

        self.assertTrue(text)
        # CHAT_MESSAGES continue de fonctionner exactement comme avant.
        self.assertEqual(quota_service.get_usage(user, QuotaType.CHAT_MESSAGES), 1)
        # Le budget LLM_CALLS ne dépasse jamais sa limite.
        self.assertEqual(quota_service.get_usage(user, QuotaType.LLM_CALLS), limit)

    def test_budget_atteint_utilise_moteur_local_ou_degrade(self):
        user = self._make_user("budget3@gmail.com", "budget3", Plan.ULTRA)
        db.increment_daily_usage(
            user["id"], QuotaType.LLM_CALLS.value, quota_service._today(),
            quota_service.QUOTA_MATRIX[Plan.ULTRA][QuotaType.LLM_CALLS],
        )
        from chatbot.services import llm_fallback_service
        call_info = {}
        script = {("anthropic", "claude-sonnet-5"): "succeed"}
        with patch.object(provider_manager, "get_provider", side_effect=_patched_get_provider(script)):
            text = "".join(llm_fallback_service.generate(
                [{"role": "user", "content": "Question."}], "system", {},
                user, call_info,
            ))
        self.assertTrue(text)
        self.assertEqual(call_info["provider"], "fake")

    def test_budget_epuise_ne_depasse_jamais_meme_apres_plusieurs_tours(self):
        """Point 8/10 : consume() qui échoue ne laisse jamais un résidu — le
        compteur reste strictement égal à la limite, quel que soit le nombre
        de tours suivants tentés."""
        user = self._make_user("budget4@gmail.com", "budget4", Plan.PREMIUM)
        limit = self._epuiser_budget(user)
        script = {("gemini", "gemini-3.1-pro-preview"): "succeed"}
        for i in range(3):
            conv = cm.create_conversation(user["id"], f"Test {i}")
            with patch.object(provider_manager, "get_provider", side_effect=_patched_get_provider(script)):
                "".join(cm.stream_reply(user, conv["id"], f"Question {i}."))
        self.assertEqual(quota_service.get_usage(user, QuotaType.LLM_CALLS), limit)

    def test_budget_non_atteint_appelle_normalement_le_reseau(self):
        """Non-régression : tant que le budget n'est pas épuisé, le
        comportement de routage reste identique à avant ce chantier."""
        user = self._make_user("budget5@gmail.com", "budget5", Plan.PREMIUM)
        conv = cm.create_conversation(user["id"], "Test")
        appelés = []
        script = {("gemini", "gemini-3.1-pro-preview"): "succeed"}
        with patch.object(provider_manager, "get_provider", side_effect=_patched_get_provider(script, appelés)):
            text = "".join(cm.stream_reply(user, conv["id"], "Question."))
        self.assertEqual(text, "Réponse réelle de gemini-3.1-pro-preview.")
        self.assertIn(("gemini", "gemini-3.1-pro-preview"), appelés)


class TestOwnerCompatibilite(_IsolatedDbTestCase):
    """Point 12 : LLM_CALLS respecte automatiquement owner_test_plan_service,
    sans aucun code de contournement supplémentaire."""

    def setUp(self):
        super().setUp()
        self.owner = self._make_user("owner@gmail.com", "owner_user", Plan.FREE)
        os.environ["NOVAMATH_OWNER_USER_ID"] = str(self.owner["id"])

    def test_llm_calls_illimite_par_defaut_pour_owner(self):
        self.assertTrue(quota_service.is_unlimited(self.owner, QuotaType.LLM_CALLS))

    def test_owner_peut_consommer_bien_au_dela_des_limites_commerciales(self):
        for _ in range(1000):
            quota_service.consume(self.owner, QuotaType.LLM_CALLS)  # ne doit jamais lever
        self.assertEqual(quota_service.get_usage(self.owner, QuotaType.LLM_CALLS), 1000)


class TestBudgetNeContourneJamaisLePlan(_IsolatedDbTestCase):
    """Points 13/14/15 : le budget LLM_CALLS ne change rien à QUI a le droit
    d'essayer QUEL modèle — provider_manager.py n'a pas été modifié."""

    def test_premium_natteint_jamais_claude_meme_budget_disponible(self):
        script = {
            ("gemini", "gemini-3.1-pro-preview"): "fail",
            ("gemini", "gemini-3-flash-preview"): "fail",
        }
        user = self._make_user("plan_premium@gmail.com", "plan_premium", Plan.PREMIUM)
        conv = cm.create_conversation(user["id"], "Test")
        appelés = []
        with patch.object(provider_manager, "get_provider", side_effect=_patched_get_provider(script, appelés)):
            "".join(cm.stream_reply(user, conv["id"], "Question."))
        self.assertNotIn(("anthropic", "claude-sonnet-5"), appelés)

    def test_free_natteint_jamais_premium_ou_ultra_meme_budget_illimite(self):
        script = {("gemini", "gemini-3-flash-preview"): "fail"}
        user = self._make_user("plan_free@gmail.com", "plan_free", Plan.FREE)
        conv = cm.create_conversation(user["id"], "Test")
        appelés = []
        with patch.object(provider_manager, "get_provider", side_effect=_patched_get_provider(script, appelés)):
            "".join(cm.stream_reply(user, conv["id"], "Question."))
        self.assertNotIn(("gemini", "gemini-3.1-pro-preview"), appelés)
        self.assertNotIn(("anthropic", "claude-sonnet-5"), appelés)

    def test_ultra_suit_sa_chaine_complete_dans_la_limite_du_budget(self):
        script = {
            ("anthropic", "claude-sonnet-5"): "succeed",
        }
        user = self._make_user("plan_ultra@gmail.com", "plan_ultra", Plan.ULTRA)
        conv = cm.create_conversation(user["id"], "Test")
        with patch.object(provider_manager, "get_provider", side_effect=_patched_get_provider(script)):
            text = "".join(cm.stream_reply(user, conv["id"], "Question."))
        self.assertEqual(text, "Réponse réelle de claude-sonnet-5.")
        self.assertEqual(quota_service.get_usage(user, QuotaType.LLM_CALLS), 1)


class TestConcurrenceLlmCalls(_IsolatedDbTestCase):
    """Point 20 : requêtes concurrentes — même garantie que CHAT_MESSAGES
    (voir test_quota_service.py::TestAccesConcurrentSimule), reportée ici sur
    LLM_CALLS avec une limite réduite pour un test rapide."""

    def test_consume_concurrent_ne_depasse_jamais_le_budget(self):
        user = self._make_user("concurrent@gmail.com", "concurrent_user", Plan.PREMIUM)
        original_matrix = quota_service.QUOTA_MATRIX[Plan.PREMIUM][QuotaType.LLM_CALLS]
        quota_service.QUOTA_MATRIX[Plan.PREMIUM][QuotaType.LLM_CALLS] = 25
        try:
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

            threads = [threading.Thread(target=worker) for _ in range(40)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            self.assertEqual(len(successes), 25)
            self.assertEqual(len(failures), 15)
            self.assertEqual(quota_service.get_usage(user, QuotaType.LLM_CALLS), 25)
        finally:
            quota_service.QUOTA_MATRIX[Plan.PREMIUM][QuotaType.LLM_CALLS] = original_matrix


# ── Volet 2 : bout en bout HTTP (même convention que
#    test_chatbot_quota_integration.py — server.app.test_client() contre la
#    vraie data/novamath.db, utilisateurs de test à email/username aléatoires) ──

def _register(client):
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


def _create_conversation(client, headers):
    resp = client.post("/api/chatbot/conversations", headers=headers)
    return resp.get_json()["conversation"]["id"]


class _ForceFakeProviderTestCase(unittest.TestCase):
    """GEMINI_API_KEY/ANTHROPIC_API_KEY sont des clés RÉELLES dans .env
    (chargées par `server`, voir server.py::load_dotenv) — sans ce
    verrouillage explicite sur "fake", un test HTTP de bout en bout via
    server.app.test_client() déclencherait un VRAI appel réseau à chaque
    message (coût réel, lenteur, non-déterminisme), alors que ces tests ne
    portent que sur la longueur de message / le rate limit, jamais sur le
    choix du fournisseur IA."""

    def setUp(self):
        self._saved_chatbot_provider = os.environ.get("CHATBOT_PROVIDER")
        os.environ["CHATBOT_PROVIDER"] = "fake"

    def tearDown(self):
        if self._saved_chatbot_provider is None:
            os.environ.pop("CHATBOT_PROVIDER", None)
        else:
            os.environ["CHATBOT_PROVIDER"] = self._saved_chatbot_provider


class TestLimiteLongueurMessage(_ForceFakeProviderTestCase):
    """Points 16/17/18 : MAX_CHATBOT_MESSAGE_CHARS."""

    def setUp(self):
        super().setUp()
        self.client = server.app.test_client()
        self.user, self.headers = _register(self.client)
        self.conv_id = _create_conversation(self.client, self.headers)

    def test_message_a_la_limite_exacte_est_accepte(self):
        resp = self.client.post(
            f"/api/chatbot/conversations/{self.conv_id}/messages",
            json={"message": "a" * server.MAX_CHATBOT_MESSAGE_CHARS}, headers=self.headers,
        )
        self.assertEqual(resp.status_code, 200)

    def test_message_un_caractere_au_dessus_est_refuse_proprement(self):
        resp = self.client.post(
            f"/api/chatbot/conversations/{self.conv_id}/messages",
            json={"message": "a" * (server.MAX_CHATBOT_MESSAGE_CHARS + 1)}, headers=self.headers,
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("error", resp.get_json())
        # Jamais un 500, jamais de troncature silencieuse (refus explicite).
        self.assertNotEqual(resp.status_code, 500)

    def test_message_trop_long_ne_consomme_aucun_quota(self):
        self.client.post(
            f"/api/chatbot/conversations/{self.conv_id}/messages",
            json={"message": "a" * (server.MAX_CHATBOT_MESSAGE_CHARS + 1)}, headers=self.headers,
        )
        body = self.client.get("/api/quota").get_json()
        self.assertEqual(body["chat_messages"]["used"], 0)

    def test_message_vide_reste_refuse(self):
        """Non-régression : la validation "message vide" pré-existante n'a
        pas été altérée par l'ajout de la limite de longueur."""
        resp = self.client.post(
            f"/api/chatbot/conversations/{self.conv_id}/messages",
            json={"message": "   "}, headers=self.headers,
        )
        self.assertEqual(resp.status_code, 400)


class TestRateLimitMessagesResteFonctionnel(_ForceFakeProviderTestCase):
    """Point 19 : non-régression — le rate limit HTTP 30/min pré-existant
    sur /messages n'a pas été touché par ce chantier.

    RATE_LIMIT_ENABLED n'est activé qu'APRÈS l'inscription/la création de
    conversation : /api/auth/register est LUI-MÊME rate-limité (3/heure/IP,
    voir server.py) — l'activer trop tôt ferait dépendre ce test d'un
    compteur PERSISTANT partagé avec tests/test_server_rate_limits.py (même
    IP de test 127.0.0.1, même fenêtre d'une heure), au lieu du seul
    comportement réellement visé ici (POST /messages)."""

    def setUp(self):
        super().setUp()
        self.client = server.app.test_client()
        self._original_enabled = server.app.config.get("RATE_LIMIT_ENABLED")
        server.app.config["RATE_LIMIT_ENABLED"] = False
        self.user, self.headers = _register(self.client)
        self.conv_id = _create_conversation(self.client, self.headers)

    def tearDown(self):
        server.app.config["RATE_LIMIT_ENABLED"] = self._original_enabled
        super().tearDown()

    def test_31e_message_en_moins_dune_minute_est_bloque(self):
        server.app.config["RATE_LIMIT_ENABLED"] = True
        last = None
        for i in range(31):
            last = self.client.post(
                f"/api/chatbot/conversations/{self.conv_id}/messages",
                json={"message": f"Message {i}"}, headers=self.headers,
            )
        self.assertEqual(last.status_code, 429)
        self.assertEqual(last.get_json()["error"], "rate_limited")


if __name__ == "__main__":
    unittest.main()
