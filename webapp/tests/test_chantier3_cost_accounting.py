"""
Suite dédiée au Chantier 3 (audit comptabilité IA/tokens/coûts, 2026-08-24) —
corrige le sous-comptage des thinking tokens Gemini dans
ai_provider_service.estimate_llm_cost(), confirmé par appels réels aux 3
providers (Gemini Flash, Gemini Pro, Claude Sonnet 5) et par la documentation
officielle des deux fournisseurs :
- Gemini : thoughts_token_count est un champ SÉPARÉ de candidates_token_count
  (total_token_count = prompt + candidates + thoughts, vérifié par appel réel),
  facturé par Google au tarif OUTPUT ("Output price, including thinking
  tokens" — ai.google.dev/gemini-api/docs/pricing).
- Anthropic : aucun champ séparé, usage.output_tokens inclut DÉJÀ le
  raisonnement (platform.claude.com/docs/en/build-with-claude/
  extended-thinking : "usage.output_tokens_details.thinking_tokens ... how
  many of the BILLED OUTPUT TOKENS were internal reasoning") — comportement
  inchangé pour Anthropic, volontairement.

Deux volets :
- TestEstimateLlmCost : la fonction pure, avec les VRAIES valeurs de tokens
  observées lors de l'audit (appels réels documentés dans le rapport).
- TestEnregistrementCoutEnBase : ai_request_log_service.record() et
  ai_provider_service.record_llm_usage(), sur une base SQLite temporaire.
"""
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import ai_provider_service
import ai_request_log_service
import db
from chatbot import cache as llm_cache
from chatbot import conversation_manager as cm
from chatbot import provider_manager
from chatbot.providers.base import ChatProvider, ProviderUnavailableError
from chatbot.providers.fake_provider import FakeProvider
from plan_service import Plan


class TestEstimateLlmCost(unittest.TestCase):
    """Fonction pure — aucune base de données, aucun mock : les tarifs
    (PRICING_USD_PER_MILLION_TOKENS) et la formule sont exercés tels quels."""

    # Lit toujours PRICING_USD_PER_MILLION_TOKENS au lieu de coder les tarifs
    # en dur ici — ces tests vérifient la FORMULE (inclusion du thinking),
    # jamais une valeur de tarif figée qui deviendrait fausse au prochain
    # ajustement de la grille (voir Chantier 4, correction du 2026-08-24).
    FLASH = ai_provider_service.PRICING_USD_PER_MILLION_TOKENS[("gemini", "gemini-3-flash-preview")]
    PRO = ai_provider_service.PRICING_USD_PER_MILLION_TOKENS[("gemini", "gemini-3.1-pro-preview")]
    CLAUDE = ai_provider_service.PRICING_USD_PER_MILLION_TOKENS[("anthropic", "claude-sonnet-5")]

    def test_gemini_flash_sans_thinking_total_egal_input_plus_output(self):
        # total_tokens == input+output (aucun delta) : comportement identique
        # à avant la correction, formule simple input*prix_in + output*prix_out.
        cost = ai_provider_service.estimate_llm_cost(
            "gemini", "gemini-3-flash-preview", input_tokens=100, output_tokens=50, total_tokens=150,
        )
        attendu = 100 * self.FLASH["input"] / 1_000_000 + 50 * self.FLASH["output"] / 1_000_000
        self.assertAlmostEqual(cost, attendu)

    def test_gemini_flash_avec_thinking_reel_observe(self):
        """Valeurs RÉELLES observées lors de l'audit (appel réel Gemini Flash,
        2026-08-24) : input=29, completion=34, thoughts=166, total=229."""
        cost = ai_provider_service.estimate_llm_cost(
            "gemini", "gemini-3-flash-preview", input_tokens=29, output_tokens=34, total_tokens=229,
        )
        # 166 thinking tokens doivent être ajoutés à l'output facturé.
        attendu = 29 * self.FLASH["input"] / 1_000_000 + (34 + 166) * self.FLASH["output"] / 1_000_000
        self.assertAlmostEqual(cost, attendu)
        # Le coût AVANT correction (sans total_tokens) sous-évaluait bien ~5x.
        cost_sans_correction = ai_provider_service.estimate_llm_cost(
            "gemini", "gemini-3-flash-preview", input_tokens=29, output_tokens=34,
        )
        self.assertGreater(cost, cost_sans_correction * 4)

    def test_gemini_pro_avec_thinking_reel_observe(self):
        """Valeurs RÉELLES (audit 2026-08-24) : input=29, completion=10,
        thoughts=286, total=325 — cas extrême où le raisonnement domine
        largement la réponse visible."""
        cost = ai_provider_service.estimate_llm_cost(
            "gemini", "gemini-3.1-pro-preview", input_tokens=29, output_tokens=10, total_tokens=325,
        )
        attendu = 29 * self.PRO["input"] / 1_000_000 + (10 + 286) * self.PRO["output"] / 1_000_000
        self.assertAlmostEqual(cost, attendu)

    def test_anthropic_thinking_deja_inclus_dans_output_aucun_changement(self):
        """Valeurs RÉELLES (audit 2026-08-24, question à raisonnement
        visible) : input=47, output=68, total=115=47+68 — Claude ne renvoie
        jamais un troisième nombre, output_tokens facture déjà le
        raisonnement. Passer ou non total_tokens ne doit RIEN changer."""
        sans_total = ai_provider_service.estimate_llm_cost(
            "anthropic", "claude-sonnet-5", input_tokens=47, output_tokens=68,
        )
        avec_total = ai_provider_service.estimate_llm_cost(
            "anthropic", "claude-sonnet-5", input_tokens=47, output_tokens=68, total_tokens=115,
        )
        self.assertEqual(sans_total, avec_total)
        attendu = 47 * self.CLAUDE["input"] / 1_000_000 + 68 * self.CLAUDE["output"] / 1_000_000
        self.assertAlmostEqual(avec_total, attendu)

    def test_total_tokens_incoherent_ne_produit_jamais_un_cout_negatif(self):
        """Si total_tokens < input+output (donnée incohérente/absente d'un
        futur provider), le delta thinking est ignoré (clamp à 0) plutôt que
        de soustraire un coût négatif absurde."""
        cost = ai_provider_service.estimate_llm_cost(
            "gemini", "gemini-3-flash-preview", input_tokens=100, output_tokens=50, total_tokens=10,
        )
        attendu = 100 * self.FLASH["input"] / 1_000_000 + 50 * self.FLASH["output"] / 1_000_000
        self.assertAlmostEqual(cost, attendu)

    def test_modele_non_repertorie_renvoie_toujours_zero(self):
        self.assertEqual(
            ai_provider_service.estimate_llm_cost("gemini", "modele-inconnu", 1000, 1000, 5000), 0.0,
        )


class _IsolatedDbTestCase(unittest.TestCase):
    def setUp(self):
        llm_cache.clear()
        provider_manager._unavailability_cache.clear()
        self._tmp_dir = tempfile.mkdtemp()
        self._data_dir_backup = db.DATA_DIR
        self._db_path_backup = db.DB_PATH
        db.DATA_DIR = Path(self._tmp_dir)
        db.DB_PATH = db.DATA_DIR / "novamath.db"
        db.init_db()
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
            ("GEMINI_API_KEY", self._saved_gemini_key), ("ANTHROPIC_API_KEY", self._saved_anthropic_key),
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


class TestEnregistrementCoutEnBase(_IsolatedDbTestCase):
    """ai_request_log_service.record() (ai_request_logs, PAR utilisateur) et
    ai_provider_service.record_llm_usage() (ai_provider_usage, agrégat
    GLOBAL/admin) — les deux seuls appelants réels de estimate_llm_cost()."""

    def test_record_par_utilisateur_inclut_le_thinking_gemini(self):
        user = self._make_user("eleve1@gmail.com", "eleve1")
        conv_id = db.create_conversation(user["id"], "Test")
        usage = {"prompt_tokens": 29, "completion_tokens": 34, "total_tokens": 229}
        ai_request_log_service.record(user["id"], conv_id, "gemini", "gemini-3-flash-preview", usage)

        rows = db.list_ai_request_logs_for_user(user["id"], limit=5)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["total_tokens"], 229)  # total_tokens toujours le vrai total, inchangé
        flash = ai_provider_service.PRICING_USD_PER_MILLION_TOKENS[("gemini", "gemini-3-flash-preview")]
        attendu = 29 * flash["input"] / 1_000_000 + (34 + 166) * flash["output"] / 1_000_000
        self.assertAlmostEqual(rows[0]["estimated_cost"], attendu)

    def test_record_llm_usage_agrege_admin_meme_formule_que_par_utilisateur(self):
        """Le coût affiché dans l'admin (ai_provider_usage) doit être
        EXACTEMENT le même, appel pour appel, que celui enregistré par
        utilisateur (ai_request_logs) — même fonction, mêmes arguments."""
        ai_provider_service.seed_default_providers()
        user = self._make_user("eleve2@gmail.com", "eleve2")
        conv_id = db.create_conversation(user["id"], "Test")
        usage = {"prompt_tokens": 29, "completion_tokens": 10, "total_tokens": 325}

        ai_request_log_service.record(user["id"], conv_id, "gemini", "gemini-3.1-pro-preview", usage)
        ai_provider_service.record_llm_usage("gemini", "gemini-3.1-pro-preview", usage)

        user_row = db.list_ai_request_logs_for_user(user["id"], limit=5)[0]
        provider_id = ai_provider_service._find_provider_id("gemini", "gemini-3.1-pro-preview")
        from datetime import datetime, timezone
        today = datetime.now(timezone.utc).date().isoformat()
        admin_row = db.get_ai_provider_usage(provider_id, today)
        self.assertIsNotNone(admin_row)
        self.assertAlmostEqual(admin_row["estimated_cost"], user_row["estimated_cost"])

    def test_echec_api_sans_usage_ne_produit_aucun_cout(self):
        """Un échec avant le premier chunk (usage=None) ne doit jamais
        produire un coût fabriqué — vérifie explicitement le point J
        (risque de double comptabilisation / faux coût) de l'audit."""
        user = self._make_user("eleve3@gmail.com", "eleve3")
        conv_id = db.create_conversation(user["id"], "Test")
        ai_request_log_service.record(
            user["id"], conv_id, "gemini", "gemini-3-flash-preview", None, success=False,
        )
        rows = db.list_ai_request_logs_for_user(user["id"], limit=5)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["estimated_cost"], 0.0)
        self.assertEqual(rows[0]["total_tokens"], 0)
        self.assertEqual(rows[0]["success"], 0)


# ── Stub provider contrôlé (même pattern que test_chantier2_routing_fallback.py) ──
class _ScriptedProvider(ChatProvider):
    def __init__(self, outcome, usage=None):
        self._outcome = outcome
        self._model = None
        self._usage = usage

    def stream_chat(self, messages, system, temperature=0.7, max_tokens=1024):
        if self._outcome == "fail":
            raise ProviderUnavailableError("panne simulée de test", durable=True, ttl_seconds=5)
        self.last_usage = self._usage
        yield f"Réponse de {self._model}."


def _patched_get_provider(script):
    def _get(provider=None, model=None, api_key=None):
        if provider == "fake":
            return FakeProvider(model=model)
        outcome, usage = script.get((provider, model), ("fail", None))
        instance = _ScriptedProvider(outcome, usage)
        instance._model = model
        return instance
    return _get


class TestCoutDeFallback(_IsolatedDbTestCase):
    """TEST demandé (§6) : Premium, Pro échoue (aucun coût) → Flash réussit
    (coût correspondant UNIQUEMENT à l'appel réellement effectué, thinking
    inclus) — jamais un coût fabriqué pour la tentative échouée, jamais un
    double comptage entre les deux tentatives."""

    def test_premium_pro_echoue_puis_flash_reussit_cout_uniquement_du_reel(self):
        flash_usage = {"prompt_tokens": 29, "completion_tokens": 34, "total_tokens": 229}
        script = {
            ("gemini", "gemini-3.1-pro-preview"): ("fail", None),
            ("gemini", "gemini-3-flash-preview"): ("succeed", flash_usage),
        }
        user = self._make_user("premium@gmail.com", "premium_user", Plan.PREMIUM)
        conv = cm.create_conversation(user["id"], "Test cout fallback")
        with patch.object(provider_manager, "get_provider", side_effect=_patched_get_provider(script)):
            "".join(cm.stream_reply(user, conv["id"], "Une question difficile."))

        logs = db.list_ai_request_logs_for_user(user["id"], limit=5)
        self.assertEqual(len(logs), 1, "un seul appel réel effectué (Pro a échoué SANS coût) -> une seule ligne")
        self.assertEqual(logs[0]["model"], "gemini-3-flash-preview")
        self.assertEqual(logs[0]["fallback"], 1)
        flash = ai_provider_service.PRICING_USD_PER_MILLION_TOKENS[("gemini", "gemini-3-flash-preview")]
        attendu = 29 * flash["input"] / 1_000_000 + (34 + 166) * flash["output"] / 1_000_000
        self.assertAlmostEqual(logs[0]["estimated_cost"], attendu)

        # Aucune trace de coût pour Pro (jamais tenté avec un vrai coût, il a
        # échoué avant tout usage) : le seul événement de fallback pointe bien
        # Pro -> Flash, sans ligne de coût intermédiaire pour Pro.
        events = db.list_ai_provider_fallback_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["model_initial"], "gemini-3.1-pro-preview")
        self.assertEqual(events[0]["model_final"], "gemini-3-flash-preview")

    def test_ultra_claude_reussit_directement_cout_claude_uniquement(self):
        claude_usage = {"prompt_tokens": 47, "completion_tokens": 68, "total_tokens": 115}
        script = {("anthropic", "claude-sonnet-5"): ("succeed", claude_usage)}
        user = self._make_user("ultra1@gmail.com", "ultra_user1", Plan.ULTRA)
        conv = cm.create_conversation(user["id"], "Test cout ultra direct")
        with patch.object(provider_manager, "get_provider", side_effect=_patched_get_provider(script)):
            "".join(cm.stream_reply(user, conv["id"], "Une question difficile."))

        logs = db.list_ai_request_logs_for_user(user["id"], limit=5)
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0]["provider"], "anthropic")
        self.assertEqual(logs[0]["fallback"], 0)
        claude = ai_provider_service.PRICING_USD_PER_MILLION_TOKENS[("anthropic", "claude-sonnet-5")]
        attendu = 47 * claude["input"] / 1_000_000 + 68 * claude["output"] / 1_000_000
        self.assertAlmostEqual(logs[0]["estimated_cost"], attendu)

    def test_ultra_trois_echecs_bascule_locale_aucun_cout_api(self):
        """§6 dernier cas demandé : les trois candidats LLM échouent, le
        moteur local répond — AUCUN coût API fabriqué (FakeProvider n'a
        aucun tarif dans PRICING_USD_PER_MILLION_TOKENS -> 0.0 garanti)."""
        script = {
            ("anthropic", "claude-sonnet-5"): ("fail", None),
            ("gemini", "gemini-3.1-pro-preview"): ("fail", None),
            ("gemini", "gemini-3-flash-preview"): ("fail", None),
        }
        user = self._make_user("ultra2@gmail.com", "ultra_user2", Plan.ULTRA)
        conv = cm.create_conversation(user["id"], "Test cout ultra local")
        with patch.object(provider_manager, "get_provider", side_effect=_patched_get_provider(script)):
            text = "".join(cm.stream_reply(user, conv["id"], "Une question difficile."))
        self.assertTrue(text)

        logs = db.list_ai_request_logs_for_user(user["id"], limit=5)
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0]["provider"], "fake")
        self.assertEqual(logs[0]["estimated_cost"], 0.0)


if __name__ == "__main__":
    unittest.main()
