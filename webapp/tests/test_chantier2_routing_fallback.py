"""
Suite dédiée au Chantier 2 (audit routage IA + fallback, 2026-08-24) —
complète volontairement les suites existantes (test_owner_test_plan_service.py
couvre déjà le routage principal par plan ; test_gemini_provider.py/
test_anthropic_provider.py couvrent déjà la classification fine des erreurs
provider) sans les dupliquer. Deux volets :

- TestTraverseeDeLaChaine* : select_llm_for_user() avec `exclude` progressif,
  pour prouver l'ORDRE exact de la chaîne de repli par plan (jamais testé
  directement ailleurs) — aucun appel réseau, aucune modification de
  users.plan/Stripe (compte Owner, mode test).
- TestFallbackReelViaGenerate/TestFallbackFreeNescaladeJamais : boucle réelle
  de webapp/chatbot/services/llm_fallback_service.generate() (et, pour les
  Tests A/B, le pipeline complet conversation_manager.stream_reply()), avec
  SEULEMENT l'appel réseau du provider mocké (jamais provider_manager.
  select_llm_for_user ni generate() eux-mêmes) — sur une base SQLite
  temporaire, jamais data/novamath.db, jamais une vraie clé API.
"""
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import db
import owner_service
import owner_test_plan_service
import quota_service
from chatbot import cache as llm_cache
from chatbot import conversation_manager as cm
from chatbot import provider_manager
from chatbot.providers.base import ChatProvider, ProviderUnavailableError
from chatbot.providers.fake_provider import FakeProvider
from chatbot.services import llm_fallback_service
from plan_service import Plan
from quota_service import QuotaType


class _IsolatedDbTestCase(unittest.TestCase):
    """Même pattern que test_owner_test_plan_service.py::_IsolatedDbTestCase —
    base SQLite temporaire, jamais data/novamath.db."""

    def setUp(self):
        llm_cache.clear()  # cache LLM en mémoire process-global : jamais de résidu d'un autre test
        provider_manager._unavailability_cache.clear()  # idem pour le cache d'indisponibilité provider/modèle
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


# ── Volet 1 : ordre exact de la chaîne de repli par plan ────────────────────
class TestTraverseeDeLaChaine(_IsolatedDbTestCase):
    """select_llm_for_user(user, exclude=...) reproduit exactement
    l'exclusion progressive que llm_fallback_service.generate() effectue
    RÉELLEMENT candidat après candidat — sans mock, sans appel réseau :
    ceci est la fonction de décision elle-même, jamais réimplémentée ici."""

    def setUp(self):
        super().setUp()
        self.owner_user = self._make_user("owner@gmail.com", "owner_user", Plan.FREE)
        os.environ["NOVAMATH_OWNER_USER_ID"] = str(self.owner_user["id"])

    def test_free_un_seul_candidat_puis_fake(self):
        owner_test_plan_service.set_test_plan(self.owner_user, "free")
        self.assertEqual(
            provider_manager.select_llm_for_user(self.owner_user, exclude=set()),
            ("gemini", "gemini-3-flash-preview"),
        )
        # Free épuisé : jamais un candidat Premium/Ultra, directement "fake".
        self.assertEqual(
            provider_manager.select_llm_for_user(
                self.owner_user, exclude={("gemini", "gemini-3-flash-preview")},
            ),
            ("fake", None),
        )

    def test_premium_pro_puis_flash_puis_fake(self):
        owner_test_plan_service.set_test_plan(self.owner_user, "premium")
        chain_start = provider_manager.select_llm_for_user(self.owner_user, exclude=set())
        self.assertEqual(chain_start, ("gemini", "gemini-3.1-pro-preview"))

        after_pro = provider_manager.select_llm_for_user(
            self.owner_user, exclude={chain_start},
        )
        self.assertEqual(after_pro, ("gemini", "gemini-3-flash-preview"))

        after_flash = provider_manager.select_llm_for_user(
            self.owner_user, exclude={chain_start, after_pro},
        )
        self.assertEqual(after_flash, ("fake", None))

    def test_ultra_claude_puis_pro_puis_flash_puis_fake(self):
        owner_test_plan_service.set_test_plan(self.owner_user, "ultra")
        step1 = provider_manager.select_llm_for_user(self.owner_user, exclude=set())
        self.assertEqual(step1, ("anthropic", "claude-sonnet-5"))

        step2 = provider_manager.select_llm_for_user(self.owner_user, exclude={step1})
        self.assertEqual(step2, ("gemini", "gemini-3.1-pro-preview"))

        step3 = provider_manager.select_llm_for_user(self.owner_user, exclude={step1, step2})
        self.assertEqual(step3, ("gemini", "gemini-3-flash-preview"))

        step4 = provider_manager.select_llm_for_user(self.owner_user, exclude={step1, step2, step3})
        self.assertEqual(step4, ("fake", None))

    def test_users_plan_et_stripe_jamais_modifies_par_ces_tests(self):
        owner_test_plan_service.set_test_plan(self.owner_user, "ultra")
        provider_manager.select_llm_for_user(self.owner_user, exclude=set())
        owner_test_plan_service.set_test_plan(self.owner_user, None)
        fresh = db.get_user_by_id(self.owner_user["id"])
        self.assertEqual(fresh["plan"], "free")
        self.assertIsNone(fresh["stripe_customer_id"])
        self.assertIsNone(fresh["stripe_subscription_id"])


# ── Stub provider contrôlé (pas de mock du contrat ChatProvider lui-même) ──
class _ScriptedProvider(ChatProvider):
    """Provider de test : échoue ou réussit selon un script fourni, sans
    jamais toucher au réseau. Une instance par (provider, modèle) demandé —
    voir _patched_get_provider ci-dessous."""

    def __init__(self, outcome):
        self._outcome = outcome  # "fail" ou "succeed"
        self._model = None

    def stream_chat(self, messages, system, temperature=0.7, max_tokens=1024):
        if self._outcome == "fail":
            raise ProviderUnavailableError("panne simulée de test", durable=True, ttl_seconds=5)
        self.last_usage = {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
        yield f"Réponse réelle de {self._model}."


def _patched_get_provider(script):
    """Remplace provider_manager.get_provider : renvoie un _ScriptedProvider
    configuré selon `script` ({(provider, modele): "fail"|"succeed"}) —
    seul point mocké de toute la chaîne, jamais select_llm_for_user() ni
    llm_fallback_service.generate(). "fake" (dernier maillon, model=None)
    délègue au VRAI FakeProvider — jamais mocké, il ne fait aucun appel
    réseau et son comportement réel (model par défaut "moteur-novamath",
    jamais None) doit être exercé tel quel, pas réinventé par le stub."""
    def _get(provider=None, model=None, api_key=None):
        if provider == "fake":
            return FakeProvider(model=model)
        outcome = script.get((provider, model), "fail")
        instance = _ScriptedProvider(outcome)
        instance._model = model
        return instance
    return _get


class TestFallbackReelViaGenerate(_IsolatedDbTestCase):
    """TEST A et TEST B demandés — bascule réelle à travers
    conversation_manager.stream_reply() -> llm_fallback_service.generate() ->
    provider_manager.select_llm_for_user(), avec uniquement l'appel réseau du
    provider mocké. Vérifie provider/modèle final, nombre de tentatives,
    fallback enregistré, quota consommé UNE SEULE FOIS, réponse unique."""

    def _run_llm_turn(self, plan, script, message="Explique-moi un théorème avancé de topologie algébrique."):
        user = self._make_user(f"eleve_{plan.value}@gmail.com", f"eleve_{plan.value}", plan)
        conv = cm.create_conversation(user["id"], "Test Chantier 2")
        quota_before = quota_service.usage_snapshot(user, QuotaType.CHAT_MESSAGES)["used"]
        with patch.object(provider_manager, "get_provider", side_effect=_patched_get_provider(script)):
            text = "".join(cm.stream_reply(user, conv["id"], message))
        quota_after = quota_service.usage_snapshot(user, QuotaType.CHAT_MESSAGES)["used"]
        return user, conv, text, quota_before, quota_after

    def test_A_premium_pro_echoue_puis_flash_repond(self):
        script = {
            ("gemini", "gemini-3.1-pro-preview"): "fail",
            ("gemini", "gemini-3-flash-preview"): "succeed",
        }
        user, conv, text, quota_before, quota_after = self._run_llm_turn(Plan.PREMIUM, script)

        self.assertEqual(text, "Réponse réelle de gemini-3-flash-preview.")

        # Quota consommé UNE SEULE fois, malgré 2 candidats tentés.
        self.assertEqual(quota_after, quota_before + 1)

        # Chantier Quotas/IA : CHAT_MESSAGES != LLM_CALLS — 2 tentatives
        # réseau RÉELLES (Pro échoué + Flash réussi) doivent consommer
        # exactement 2 unités LLM_CALLS, jamais 1 (pas de sous-comptage du
        # candidat échoué) ni 3 (pas de double-comptage du candidat réussi).
        llm_calls_used = quota_service.usage_snapshot(user, QuotaType.LLM_CALLS)["used"]
        self.assertEqual(llm_calls_used, 2)

        # Un seul message assistant persisté (pas de doublon).
        rows = db.list_messages(conv["id"])
        assistant_rows = [r for r in rows if r["role"] == "assistant"]
        self.assertEqual(len(assistant_rows), 1)
        self.assertEqual(assistant_rows[0]["provider"], "gemini")

        # ai_request_logs : une seule ligne pour ce tour, provider/modèle
        # RÉELLEMENT utilisé, marquée fallback=1.
        logs = db.list_ai_request_logs_for_user(user["id"], limit=5)
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0]["provider"], "gemini")
        self.assertEqual(logs[0]["model"], "gemini-3-flash-preview")
        self.assertEqual(logs[0]["fallback"], 1)
        self.assertEqual(logs[0]["success"], 1)

        # ai_provider_fallback_events : un seul événement, Pro -> Flash.
        events = db.list_ai_provider_fallback_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["provider_initial"], "gemini")
        self.assertEqual(events[0]["model_initial"], "gemini-3.1-pro-preview")
        self.assertEqual(events[0]["provider_final"], "gemini")
        self.assertEqual(events[0]["model_final"], "gemini-3-flash-preview")

    def test_B_ultra_claude_et_pro_echouent_puis_flash_repond(self):
        script = {
            ("anthropic", "claude-sonnet-5"): "fail",
            ("gemini", "gemini-3.1-pro-preview"): "fail",
            ("gemini", "gemini-3-flash-preview"): "succeed",
        }
        user, conv, text, quota_before, quota_after = self._run_llm_turn(Plan.ULTRA, script)

        self.assertEqual(text, "Réponse réelle de gemini-3-flash-preview.")
        self.assertEqual(quota_after, quota_before + 1)

        # 3 tentatives réseau réelles (Claude échoué, Pro échoué, Flash
        # réussi) = 3 unités LLM_CALLS, indépendamment du 1 seul CHAT_MESSAGES.
        self.assertEqual(quota_service.usage_snapshot(user, QuotaType.LLM_CALLS)["used"], 3)

        rows = db.list_messages(conv["id"])
        assistant_rows = [r for r in rows if r["role"] == "assistant"]
        self.assertEqual(len(assistant_rows), 1)

        logs = db.list_ai_request_logs_for_user(user["id"], limit=5)
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0]["model"], "gemini-3-flash-preview")
        self.assertEqual(logs[0]["fallback"], 1)

        # fallback_from = LE PREMIER candidat tenté (Claude), pas le pénultième.
        events = db.list_ai_provider_fallback_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["provider_initial"], "anthropic")
        self.assertEqual(events[0]["model_initial"], "claude-sonnet-5")
        self.assertEqual(events[0]["provider_final"], "gemini")
        self.assertEqual(events[0]["model_final"], "gemini-3-flash-preview")

    def test_ultra_tous_les_candidats_llm_echouent_bascule_sur_local(self):
        """Si Claude, Pro ET Flash échouent tous, le tour ne plante jamais —
        le moteur local (FakeProvider/mode dégradé) répond toujours."""
        script = {
            ("anthropic", "claude-sonnet-5"): "fail",
            ("gemini", "gemini-3.1-pro-preview"): "fail",
            ("gemini", "gemini-3-flash-preview"): "fail",
        }
        user, conv, text, quota_before, quota_after = self._run_llm_turn(Plan.ULTRA, script)

        self.assertTrue(text)  # une réponse a bien été produite, jamais un plantage
        self.assertEqual(quota_after, quota_before + 1)
        logs = db.list_ai_request_logs_for_user(user["id"], limit=5)
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0]["provider"], "fake")

        # 3 tentatives réseau réelles échouées (Claude, Pro, Flash) = 3
        # LLM_CALLS ; le repli final sur "fake" (moteur local) n'en consomme
        # aucune (pas de réseau) — jamais 4.
        self.assertEqual(quota_service.usage_snapshot(user, QuotaType.LLM_CALLS)["used"], 3)


class TestFallbackFreeNescaladeJamais(_IsolatedDbTestCase):
    """TEST C demandé — Free dont l'unique candidat échoue ne doit JAMAIS
    obtenir un candidat Premium/Ultra : la chaîne Free ne contient que
    Gemini Flash (voir MODEL_CHAIN_BY_PLAN), donc select_llm_for_user()
    renvoie directement ("fake", None) sans jamais consulter Pro/Claude.
    Vérifié directement via llm_fallback_service.generate() (pas besoin du
    pipeline complet : la chaîne Free est triviale, un seul candidat)."""

    def test_free_echoue_bascule_sur_fake_jamais_sur_pro_ou_claude(self):
        user = self._make_user("free_user@gmail.com", "free_user", Plan.FREE)
        appelés = []

        def _get(provider=None, model=None, api_key=None):
            appelés.append((provider, model))
            if provider == "fake":
                return FakeProvider(model=model)
            outcome = "fail" if (provider, model) == ("gemini", "gemini-3-flash-preview") else "succeed"
            instance = _ScriptedProvider(outcome)
            instance._model = model
            return instance

        call_info = {}
        with patch.object(provider_manager, "get_provider", side_effect=_get):
            text = "".join(llm_fallback_service.generate(
                [{"role": "user", "content": "Question."}], "system", {}, user, call_info,
            ))

        self.assertTrue(text)
        self.assertEqual(call_info["provider"], "fake")
        # Aucun candidat Premium/Ultra n'a jamais été instancié.
        self.assertNotIn(("gemini", "gemini-3.1-pro-preview"), appelés)
        self.assertNotIn(("anthropic", "claude-sonnet-5"), appelés)


# ── Chantier Quotas/IA (audit prioritaire) ──────────────────────────────────
# Reproduction réelle (pas une simple lecture de code) des deux symptômes
# rapportés : "Free peut envoyer autant de messages que Premium" et "l'API
# répond alors que le quota est indiqué atteint". Complète TestFallbackReelViaGenerate
# ci-dessus (qui prouve déjà CHAT_MESSAGES=+1/LLM_CALLS=+2 ou +3 selon le
# nombre de tentatives réseau réelles) avec les deux scénarios de blocage.
class TestBudgetLlmCallsEpuiseNeBloqueJamaisLeMessage(_IsolatedDbTestCase):
    """Chantier 5 (protection de la marge) : quand LLM_CALLS est épuisé EN
    COURS de repli, aucun appel réseau supplémentaire n'est tenté (voir
    llm_fallback_service.py:175-185) — mais le message utilisateur reçoit
    quand même une réponse (moteur local), jamais bloqué. Reproduit ici avec
    un budget Premium volontairement épuisé à l'avance."""

    def test_budget_llm_calls_deja_epuise_bascule_direct_sur_local_sans_appel_reseau(self):
        user = self._make_user("premium_budget@gmail.com", "premium_budget", Plan.PREMIUM)
        # Épuise le budget LLM_CALLS AVANT tout tour réel (20/20, voir QUOTA_MATRIX).
        quota_service.consume(user, QuotaType.LLM_CALLS, amount=20)
        user = db.get_user_by_id(user["id"])

        appels_reseau = []

        def _get(provider=None, model=None, api_key=None):
            if provider == "fake":
                return FakeProvider(model=model)
            appels_reseau.append((provider, model))
            instance = _ScriptedProvider("succeed")  # aurait réussi si appelé
            instance._model = model
            return instance

        conv = cm.create_conversation(user["id"], "Test budget LLM_CALLS")
        with patch.object(provider_manager, "get_provider", side_effect=_get):
            text = "".join(cm.stream_reply(user, conv["id"], "Explique-moi un théorème avancé de topologie."))

        # Une réponse a bien été produite (moteur local), l'utilisateur n'est
        # JAMAIS bloqué par un budget LLM_CALLS épuisé.
        self.assertTrue(text)
        # AUCUN appel réseau réel n'a été tenté : le budget étant déjà à 0,
        # consume() lève QuotaExceededError avant même d'instancier le
        # provider réseau (voir llm_fallback_service.py:175-186).
        self.assertEqual(appels_reseau, [])
        # CHAT_MESSAGES consommé normalement (le budget LLM_CALLS est
        # indépendant) : le message utilisateur compte bien pour 1.
        self.assertEqual(quota_service.usage_snapshot(user, QuotaType.CHAT_MESSAGES)["used"], 1)
        # LLM_CALLS reste strictement à sa limite, jamais dépassé.
        self.assertEqual(quota_service.usage_snapshot(user, QuotaType.LLM_CALLS)["used"], 20)


class TestQuotaEpuiseBloqueAvantToutAppelReseau(_IsolatedDbTestCase):
    """Reproduction directe du symptôme 2 rapporté : "l'interface indique une
    limite atteinte mais une réponse IA arrive quand même". Envoie des
    messages jusqu'à épuiser CHAT_MESSAGES, puis vérifie qu'un message
    supplémentaire NE DÉCLENCHE STRICTEMENT AUCUN appel réseau — le blocage
    (check_and_increment_quota, conversation_manager.py:808) a lieu avant
    toute tentative de génération, y compris locale."""

    def test_chat_messages_epuise_aucun_appel_reseau_ni_local_nest_tente(self):
        user = self._make_user("free_exhaust@gmail.com", "free_exhaust", Plan.FREE)
        conv = cm.create_conversation(user["id"], "Test épuisement")
        appels = []

        def _get(provider=None, model=None, api_key=None):
            appels.append((provider, model))
            if provider == "fake":
                return FakeProvider(model=model)
            instance = _ScriptedProvider("succeed")
            instance._model = model
            return instance

        # Épuise CHAT_MESSAGES (Free = 15/j depuis le chantier "Réduction
        # quota Free", 2026-08-25 — voir QUOTA_MATRIX) en une seule écriture
        # directe (inutile de rejouer 15 vrais tours) puis tente UN message
        # supplémentaire, le seul dont ce test vérifie le comportement.
        quota_service.consume(user, QuotaType.CHAT_MESSAGES, amount=15)
        user = db.get_user_by_id(user["id"])

        with patch.object(provider_manager, "get_provider", side_effect=_get):
            with self.assertRaises(quota_service.QuotaExceededError):
                "".join(cm.stream_reply(user, conv["id"], "Un message de trop."))

        # Aucun candidat (réseau OU local) n'a été instancié : le blocage a
        # lieu strictement avant toute génération.
        self.assertEqual(appels, [])
        # Le compteur n'a pas bougé (aucun message facturé pour un tour bloqué).
        self.assertEqual(quota_service.usage_snapshot(user, QuotaType.CHAT_MESSAGES)["used"], 15)
        # Aucun message n'a été persisté pour cette tentative refusée.
        rows = db.list_messages(conv["id"])
        self.assertEqual(len(rows), 0)


class TestFreeVsPremiumReproductionReelle(_IsolatedDbTestCase):
    """Reproduction directe du symptôme 1 initialement rapporté : "Free peut
    envoyer autant de messages que Premium". C'était un FAIT RÉEL jusqu'au
    Chantier 6 inclus (CHAT_MESSAGES identique, 25/25, décision produit
    documentée) — corrigé par le chantier "Réduction quota Free"
    (2026-08-25, voir quota_service.py::QUOTA_MATRIX) : Free passe à 15,
    strictement inférieur à Premium (25). Ce test confirme désormais l'écart
    réel, et que LLM_CALLS (Free illimité formellement mais contraint par sa
    chaîne à 1 seul candidat réel ; Premium plafonné à 20) reste inchangé."""

    def test_free_et_premium_ont_desormais_des_limites_chat_messages_distinctes(self):
        free_user = self._make_user("free_cmp@gmail.com", "free_cmp", Plan.FREE)
        premium_user = self._make_user("premium_cmp@gmail.com", "premium_cmp", Plan.PREMIUM)
        self.assertEqual(quota_service.get_limit(free_user, QuotaType.CHAT_MESSAGES), 15)
        self.assertEqual(quota_service.get_limit(premium_user, QuotaType.CHAT_MESSAGES), 25)
        self.assertLess(
            quota_service.get_limit(free_user, QuotaType.CHAT_MESSAGES),
            quota_service.get_limit(premium_user, QuotaType.CHAT_MESSAGES),
        )

    def test_llm_calls_reste_inchange_par_ce_chantier(self):
        free_user = self._make_user("free_cmp2@gmail.com", "free_cmp2", Plan.FREE)
        premium_user = self._make_user("premium_cmp2@gmail.com", "premium_cmp2", Plan.PREMIUM)
        self.assertIsNone(quota_service.get_limit(free_user, QuotaType.LLM_CALLS))  # illimité formellement
        self.assertEqual(quota_service.get_limit(premium_user, QuotaType.LLM_CALLS), 20)

    def test_free_epuise_reellement_son_seul_candidat_avant_15_messages(self):
        """La protection réelle de Free n'est pas LLM_CALLS (illimité) mais
        le fait que sa chaîne n'ait qu'un seul candidat réseau réel avant
        "fake" — un Free ne peut donc jamais consommer plus de 15 appels
        réseau réels par jour, même si LLM_CALLS ne le limite pas explicitement."""
        user = self._make_user("free_chain@gmail.com", "free_chain", Plan.FREE)
        candidat = provider_manager.select_llm_for_user(user, exclude=set())
        self.assertEqual(candidat, ("gemini", "gemini-3-flash-preview"))
        next_candidat = provider_manager.select_llm_for_user(user, exclude={candidat})
        self.assertEqual(next_candidat, ("fake", None))  # jamais de second candidat réseau


if __name__ == "__main__":
    unittest.main()
