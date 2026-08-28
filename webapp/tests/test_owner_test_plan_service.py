"""
Suite du "Mode test Owner" (webapp/owner_test_plan_service.py) — chantier
2026-08-23, complément de tests/test_owner_override.py.

Deux volets :
- OwnerTestPlanServiceTestCase : owner_test_plan_service.py en isolation
  (base SQLite temporaire, même pattern que test_owner_override.py — aucune
  interférence avec data/novamath.db).
- OwnerTestPlanRoutesTestCase : preuve réelle via server.app.test_client()
  que GET/PATCH /api/owner/test-plan produisent l'effet attendu de bout en
  bout (registre HTTP réel, cookies de session/CSRF réels), y compris sur
  users.plan/Stripe qui ne doivent JAMAIS changer, et sur l'isolation
  stricte des autres comptes (autre super_admin, utilisateur normal -> 404).
"""
import os
import random
import shutil
import tempfile
import unittest
from pathlib import Path

import auth
import db
import owner_service
import owner_test_plan_service
import plan_service
import quota_service
import role_service
import server
from plan_service import Feature, Plan
from quota_service import QuotaType


class _IsolatedDbTestCase(unittest.TestCase):
    """Base commune : redirige db.DATA_DIR/DB_PATH vers un répertoire
    temporaire (voir database_service.py — jamais mis en cache, un test qui
    monkeypatch le chemin est le pattern attendu par le projet), pour ne
    JAMAIS écrire dans data/novamath.db, même via server.app.test_client()."""

    def setUp(self):
        self._tmp_dir = tempfile.mkdtemp()
        self._data_dir_backup = db.DATA_DIR
        self._db_path_backup = db.DB_PATH
        db.DATA_DIR = Path(self._tmp_dir)
        db.DB_PATH = db.DATA_DIR / "novamath.db"
        db.init_db()

        self._saved_owner_env = os.environ.get("NOVAMATH_OWNER_USER_ID")
        os.environ.pop("NOVAMATH_OWNER_USER_ID", None)

    def tearDown(self):
        db.DATA_DIR = self._data_dir_backup
        db.DB_PATH = self._db_path_backup
        shutil.rmtree(self._tmp_dir, ignore_errors=True)
        if self._saved_owner_env is None:
            os.environ.pop("NOVAMATH_OWNER_USER_ID", None)
        else:
            os.environ["NOVAMATH_OWNER_USER_ID"] = self._saved_owner_env

    def _make_user(self, email, username, plan=Plan.FREE):
        user_id = db.create_user(email, username, "Élève", "hash")
        if plan is not Plan.FREE:
            db.set_stripe_subscription(user_id, "sub_test", plan.value, "active")
        return db.get_user_by_id(user_id)


# ── Volet 1 : owner_test_plan_service.py en isolation ───────────────────────
class OwnerTestPlanServiceTestCase(_IsolatedDbTestCase):
    def setUp(self):
        super().setUp()
        self.owner_user = self._make_user("owner@gmail.com", "owner_user", Plan.FREE)
        self.other_admin = self._make_user("admin@gmail.com", "admin_user", Plan.FREE)
        db.set_user_role(self.other_admin["id"], role_service.Role.SUPER_ADMIN.value)
        self.other_admin = db.get_user_by_id(self.other_admin["id"])
        self.random_user = self._make_user("random@gmail.com", "random_user", Plan.FREE)

    def _activate_owner(self):
        os.environ["NOVAMATH_OWNER_USER_ID"] = str(self.owner_user["id"])


class TestFailClosedSansConfiguration(OwnerTestPlanServiceTestCase):
    """Test explicite demandé : absence de NOVAMATH_OWNER_USER_ID -> mode
    test totalement inactif, y compris si une valeur traîne déjà en base
    (ex: variable retirée après un test précédent)."""

    def test_get_test_plan_none_sans_variable(self):
        self.assertIsNone(owner_test_plan_service.get_test_plan(self.owner_user))

    def test_set_test_plan_refuse_sans_variable(self):
        ok, error = owner_test_plan_service.set_test_plan(self.owner_user, "premium")
        self.assertFalse(ok)
        self.assertIsNotNone(error)

    def test_valeur_residuelle_en_base_ignoree_sans_variable(self):
        self._activate_owner()
        owner_test_plan_service.set_test_plan(self.owner_user, "ultra")
        os.environ.pop("NOVAMATH_OWNER_USER_ID", None)
        # La ligne system_settings existe toujours, mais is_owner_account
        # renvoie False sans la variable -> aucune lecture, aucun effet.
        self.assertIsNone(owner_test_plan_service.get_test_plan(self.owner_user))
        self.assertIs(owner_test_plan_service.effective_plan(self.owner_user), Plan.FREE)

    def test_effective_plan_utilisateur_normal_inchange(self):
        self.assertIs(owner_test_plan_service.effective_plan(self.random_user), Plan.FREE)


class TestIsolationAutresComptes(OwnerTestPlanServiceTestCase):
    """Tests explicites demandés : autre super_admin et utilisateur normal
    ne peuvent jamais lire/activer le mode test, même une fois le owner
    configuré."""

    def test_autre_super_admin_get_test_plan_none(self):
        self._activate_owner()
        self.assertIs(role_service.get_role(self.other_admin), role_service.Role.SUPER_ADMIN)
        self.assertIsNone(owner_test_plan_service.get_test_plan(self.other_admin))

    def test_autre_super_admin_set_test_plan_refuse(self):
        self._activate_owner()
        ok, error = owner_test_plan_service.set_test_plan(self.other_admin, "ultra")
        self.assertFalse(ok)
        self.assertIsNotNone(error)
        # Confirme qu'aucune écriture n'a eu lieu (le owner réel n'est pas affecté).
        self.assertIsNone(owner_test_plan_service.get_test_plan(self.owner_user))

    def test_utilisateur_normal_set_test_plan_refuse(self):
        self._activate_owner()
        ok, error = owner_test_plan_service.set_test_plan(self.random_user, "premium")
        self.assertFalse(ok)
        self.assertIsNotNone(error)

    def test_autres_comptes_effective_plan_toujours_reel(self):
        self._activate_owner()
        owner_test_plan_service.set_test_plan(self.owner_user, "ultra")
        self.assertIs(owner_test_plan_service.effective_plan(self.other_admin), Plan.FREE)
        self.assertIs(owner_test_plan_service.effective_plan(self.random_user), Plan.FREE)


class TestComportementOwnerSansEtAvecOverride(OwnerTestPlanServiceTestCase):
    """Cas E->K explicitement demandés."""

    def test_owner_sans_override_effective_plan_ultra(self):
        self._activate_owner()
        self.assertIsNone(owner_test_plan_service.get_test_plan(self.owner_user))
        self.assertIs(owner_test_plan_service.effective_plan(self.owner_user), Plan.ULTRA)

    def test_owner_free_effective_plan_free(self):
        self._activate_owner()
        ok, error = owner_test_plan_service.set_test_plan(self.owner_user, "free")
        self.assertTrue(ok)
        self.assertIsNone(error)
        self.assertIs(owner_test_plan_service.effective_plan(self.owner_user), Plan.FREE)

    def test_owner_premium_effective_plan_premium(self):
        self._activate_owner()
        owner_test_plan_service.set_test_plan(self.owner_user, "premium")
        self.assertIs(owner_test_plan_service.effective_plan(self.owner_user), Plan.PREMIUM)

    def test_owner_ultra_effective_plan_ultra(self):
        self._activate_owner()
        owner_test_plan_service.set_test_plan(self.owner_user, "ultra")
        self.assertIs(owner_test_plan_service.effective_plan(self.owner_user), Plan.ULTRA)

    def test_reset_revient_a_ultra(self):
        self._activate_owner()
        owner_test_plan_service.set_test_plan(self.owner_user, "free")
        self.assertIs(owner_test_plan_service.effective_plan(self.owner_user), Plan.FREE)
        ok, error = owner_test_plan_service.set_test_plan(self.owner_user, None)
        self.assertTrue(ok)
        self.assertIsNone(error)
        self.assertIsNone(owner_test_plan_service.get_test_plan(self.owner_user))
        self.assertIs(owner_test_plan_service.effective_plan(self.owner_user), Plan.ULTRA)

    def test_plan_invalide_refuse(self):
        self._activate_owner()
        ok, error = owner_test_plan_service.set_test_plan(self.owner_user, "gold")
        self.assertFalse(ok)
        self.assertIsNotNone(error)
        self.assertIsNone(owner_test_plan_service.get_test_plan(self.owner_user))

    def test_users_plan_jamais_modifie(self):
        self._activate_owner()
        for value in ("free", "premium", "ultra", None):
            owner_test_plan_service.set_test_plan(self.owner_user, value)
            stored = db.get_user_by_id(self.owner_user["id"])
            self.assertEqual(stored["plan"], "free")

    def test_aucune_donnee_stripe_modifiee(self):
        self._activate_owner()
        before = db.get_user_by_id(self.owner_user["id"])
        for value in ("free", "premium", "ultra", None):
            owner_test_plan_service.set_test_plan(self.owner_user, value)
        after = db.get_user_by_id(self.owner_user["id"])
        self.assertEqual(before["stripe_customer_id"], after["stripe_customer_id"])
        self.assertEqual(before["stripe_subscription_id"], after["stripe_subscription_id"])
        self.assertEqual(before["stripe_subscription_status"], after["stripe_subscription_status"])


class TestHasFeatureSuitLeffectivePlan(OwnerTestPlanServiceTestCase):
    def test_owner_sans_override_toutes_features(self):
        self._activate_owner()
        for feature in Feature:
            with self.subTest(feature=feature):
                self.assertTrue(plan_service.has_feature(self.owner_user, feature))

    def test_owner_free_features_limitees(self):
        self._activate_owner()
        owner_test_plan_service.set_test_plan(self.owner_user, "free")
        self.assertTrue(plan_service.has_feature(self.owner_user, Feature.CHATBOT))
        self.assertFalse(plan_service.has_feature(self.owner_user, Feature.CHATBOT_UNLIMITED))
        self.assertFalse(plan_service.has_feature(self.owner_user, Feature.ADVANCED_AI))

    def test_owner_premium_features_intermediaires(self):
        self._activate_owner()
        owner_test_plan_service.set_test_plan(self.owner_user, "premium")
        self.assertTrue(plan_service.has_feature(self.owner_user, Feature.CHATBOT_UNLIMITED))
        self.assertFalse(plan_service.has_feature(self.owner_user, Feature.ADVANCED_AI))

    def test_owner_ultra_toutes_features(self):
        self._activate_owner()
        owner_test_plan_service.set_test_plan(self.owner_user, "ultra")
        for feature in Feature:
            with self.subTest(feature=feature):
                self.assertTrue(plan_service.has_feature(self.owner_user, feature))

    def test_utilisateurs_normaux_inchanges_pendant_le_test_owner(self):
        self._activate_owner()
        owner_test_plan_service.set_test_plan(self.owner_user, "ultra")
        free_user = self._make_user("free2@gmail.com", "free_user2", Plan.FREE)
        self.assertFalse(plan_service.has_feature(free_user, Feature.ADVANCED_AI))
        self.assertFalse(plan_service.has_feature(free_user, Feature.CHATBOT_UNLIMITED))


class TestQuotasOwnerUnlimitedFlagSepare(OwnerTestPlanServiceTestCase):
    """Cas demandés : unlimited_quotas=true -> None (illimité) ;
    unlimited_quotas=false + plan de test -> vraie limite du plan."""

    def test_defaut_illimite_sans_configuration(self):
        self._activate_owner()
        self.assertTrue(owner_test_plan_service.get_unlimited_quotas(self.owner_user))
        self.assertIsNone(quota_service.get_limit(self.owner_user, QuotaType.CHAT_MESSAGES))

    def test_illimite_reste_vrai_meme_avec_plan_de_test_free(self):
        self._activate_owner()
        owner_test_plan_service.set_test_plan(self.owner_user, "free")
        self.assertIsNone(quota_service.get_limit(self.owner_user, QuotaType.CHAT_MESSAGES))

    def test_desactivation_expose_la_vraie_limite_free(self):
        self._activate_owner()
        owner_test_plan_service.set_test_plan(self.owner_user, "free")
        ok, error = owner_test_plan_service.set_unlimited_quotas(self.owner_user, False)
        self.assertTrue(ok)
        self.assertIsNone(error)
        self.assertEqual(quota_service.get_limit(self.owner_user, QuotaType.CHAT_MESSAGES), 15)

    def test_desactivation_expose_la_vraie_limite_premium(self):
        self._activate_owner()
        owner_test_plan_service.set_test_plan(self.owner_user, "premium")
        owner_test_plan_service.set_unlimited_quotas(self.owner_user, False)
        self.assertEqual(quota_service.get_limit(self.owner_user, QuotaType.CHAT_MESSAGES), 25)
        self.assertEqual(quota_service.get_limit(self.owner_user, QuotaType.LLM_CALLS), 20)

    def test_desactivation_expose_la_vraie_limite_ultra(self):
        self._activate_owner()
        owner_test_plan_service.set_test_plan(self.owner_user, "ultra")
        owner_test_plan_service.set_unlimited_quotas(self.owner_user, False)
        # CHAT_MESSAGES/LLM_CALLS Ultra sont désormais des limites finies
        # (40/j chacune, Chantier 6) même directement dans QUOTA_MATRIX —
        # PDF_ANALYSIS, lui, reste structurellement illimité pour Ultra.
        self.assertEqual(quota_service.get_limit(self.owner_user, QuotaType.CHAT_MESSAGES), 40)
        self.assertEqual(quota_service.get_limit(self.owner_user, QuotaType.LLM_CALLS), 40)
        self.assertIsNone(quota_service.get_limit(self.owner_user, QuotaType.PDF_ANALYSIS))

    def test_free_normal_toujours_sa_vraie_limite(self):
        self._activate_owner()
        owner_test_plan_service.set_test_plan(self.owner_user, "ultra")
        free_user = self._make_user("free3@gmail.com", "free_user3", Plan.FREE)
        self.assertEqual(quota_service.get_limit(free_user, QuotaType.CHAT_MESSAGES), 15)

    def test_set_unlimited_quotas_refuse_pour_non_owner(self):
        self._activate_owner()
        ok, error = owner_test_plan_service.set_unlimited_quotas(self.random_user, False)
        self.assertFalse(ok)
        self.assertIsNotNone(error)

    # ── Chantier "Limitation des exercices par abonnement" (2026-08-26) ─────
    # QuotaType.EXERCISES_DAILY suit exactement le même mécanisme générique
    # que CHAT_MESSAGES ci-dessus (get_limit() ne connaît aucun QuotaType en
    # particulier) — pas de branche spéciale Owner ajoutée pour les
    # exercices, ces tests le prouvent explicitement.
    def test_owner_test_free_exercises_daily_egale_20(self):
        self._activate_owner()
        owner_test_plan_service.set_test_plan(self.owner_user, "free")
        owner_test_plan_service.set_unlimited_quotas(self.owner_user, False)
        self.assertEqual(quota_service.get_limit(self.owner_user, QuotaType.EXERCISES_DAILY), 20)

    def test_owner_test_premium_exercises_daily_egale_60(self):
        self._activate_owner()
        owner_test_plan_service.set_test_plan(self.owner_user, "premium")
        owner_test_plan_service.set_unlimited_quotas(self.owner_user, False)
        self.assertEqual(quota_service.get_limit(self.owner_user, QuotaType.EXERCISES_DAILY), 60)

    def test_owner_test_ultra_exercises_daily_illimite(self):
        self._activate_owner()
        owner_test_plan_service.set_test_plan(self.owner_user, "ultra")
        owner_test_plan_service.set_unlimited_quotas(self.owner_user, False)
        self.assertIsNone(quota_service.get_limit(self.owner_user, QuotaType.EXERCISES_DAILY))

    def test_owner_sans_plan_de_test_exercises_daily_illimite(self):
        self._activate_owner()
        self.assertIsNone(quota_service.get_limit(self.owner_user, QuotaType.EXERCISES_DAILY))


class TestProviderSelectionSuitLeffectivePlan(OwnerTestPlanServiceTestCase):
    """Cas L explicitement demandé : select_llm_for_user() suit bien
    effective_plan(), pas plan_service.get_plan()."""

    def setUp(self):
        super().setUp()
        self._saved_gemini_key = os.environ.get("GEMINI_API_KEY")
        self._saved_anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
        self._saved_chatbot_provider = os.environ.get("CHATBOT_PROVIDER")
        os.environ["GEMINI_API_KEY"] = "test-key"
        os.environ["ANTHROPIC_API_KEY"] = "test-key"
        os.environ.pop("CHATBOT_PROVIDER", None)

    def tearDown(self):
        for key, saved in (
            ("GEMINI_API_KEY", self._saved_gemini_key),
            ("ANTHROPIC_API_KEY", self._saved_anthropic_key),
            ("CHATBOT_PROVIDER", self._saved_chatbot_provider),
        ):
            if saved is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = saved
        super().tearDown()

    def test_owner_sans_override_chaine_ultra(self):
        from chatbot import provider_manager
        self._activate_owner()
        provider_name, model = provider_manager.select_llm_for_user(self.owner_user)
        self.assertEqual((provider_name, model), ("anthropic", "claude-sonnet-5"))

    def test_owner_test_plan_free_chaine_free(self):
        from chatbot import provider_manager
        self._activate_owner()
        owner_test_plan_service.set_test_plan(self.owner_user, "free")
        provider_name, model = provider_manager.select_llm_for_user(self.owner_user)
        self.assertEqual((provider_name, model), ("gemini", "gemini-3-flash-preview"))

    def test_owner_test_plan_premium_chaine_premium(self):
        from chatbot import provider_manager
        self._activate_owner()
        owner_test_plan_service.set_test_plan(self.owner_user, "premium")
        provider_name, model = provider_manager.select_llm_for_user(self.owner_user)
        self.assertEqual((provider_name, model), ("gemini", "gemini-3.1-pro-preview"))

    def test_owner_test_plan_ultra_chaine_ultra(self):
        from chatbot import provider_manager
        self._activate_owner()
        owner_test_plan_service.set_test_plan(self.owner_user, "ultra")
        provider_name, model = provider_manager.select_llm_for_user(self.owner_user)
        self.assertEqual((provider_name, model), ("anthropic", "claude-sonnet-5"))

    def test_free_normal_toujours_chaine_free(self):
        from chatbot import provider_manager
        self._activate_owner()
        owner_test_plan_service.set_test_plan(self.owner_user, "ultra")
        provider_name, model = provider_manager.select_llm_for_user(self.random_user)
        self.assertEqual((provider_name, model), ("gemini", "gemini-3-flash-preview"))


# ── Volet 2 : preuve réelle via server.app.test_client() ───────────────────
def _register(client, email=None, username=None):
    email = email or f"test{random.randint(1_000_000, 9_999_999)}@gmail.com"
    username = username or f"testuser{random.randint(100_000, 999_999)}"
    resp = client.post("/api/auth/register", json={
        "email": email, "username": username, "pseudo": "Test",
        "birth_date": "2000-01-01",
        "password": "MotDePasse123!", "confirm_password": "MotDePasse123!",
        "accept_terms": True, "accept_privacy": True,
    })
    user = resp.get_json()["user"]
    csrf = client.get_cookie("nm_csrf").value
    return user, {"X-CSRF-Token": csrf}


class OwnerTestPlanRoutesTestCase(_IsolatedDbTestCase):
    def setUp(self):
        super().setUp()
        self.client = server.app.test_client()
        self.owner_user, self.owner_headers = _register(self.client)

    def _activate_owner(self):
        os.environ["NOVAMATH_OWNER_USER_ID"] = str(self.owner_user["id"])


class TestRoutesFailClosedEtIsolation(OwnerTestPlanRoutesTestCase):
    def test_get_404_sans_novamath_owner_user_id(self):
        resp = self.client.get("/api/owner/test-plan")
        self.assertEqual(resp.status_code, 404)

    def test_get_404_pour_autre_super_admin(self):
        self._activate_owner()
        admin_client = server.app.test_client()
        admin_user, admin_headers = _register(admin_client)
        db.set_user_role(admin_user["id"], role_service.Role.SUPER_ADMIN.value)
        resp = admin_client.get("/api/owner/test-plan")
        self.assertEqual(resp.status_code, 404)

    def test_patch_404_pour_autre_super_admin(self):
        self._activate_owner()
        admin_client = server.app.test_client()
        admin_user, admin_headers = _register(admin_client)
        db.set_user_role(admin_user["id"], role_service.Role.SUPER_ADMIN.value)
        resp = admin_client.patch("/api/owner/test-plan", json={"plan": "ultra"}, headers=admin_headers)
        self.assertEqual(resp.status_code, 404)
        # Le compte owner réel n'est jamais affecté par cette tentative refusée.
        self.assertIsNone(owner_test_plan_service.get_test_plan(self.owner_user))

    def test_get_404_pour_utilisateur_normal(self):
        self._activate_owner()
        other_client = server.app.test_client()
        _register(other_client)
        resp = other_client.get("/api/owner/test-plan")
        self.assertEqual(resp.status_code, 404)

    def test_patch_404_pour_utilisateur_normal(self):
        self._activate_owner()
        other_client = server.app.test_client()
        _, other_headers = _register(other_client)
        resp = other_client.patch("/api/owner/test-plan", json={"plan": "ultra"}, headers=other_headers)
        self.assertEqual(resp.status_code, 404)


class TestRoutesComportementOwnerReel(OwnerTestPlanRoutesTestCase):
    """Preuve de bout en bout (section 11 de la demande) : A/B/C/D/E pour
    chacun des trois plans, puis le reset — via de vraies requêtes HTTP sur
    server.app.test_client(), jamais un appel direct au service."""

    def setUp(self):
        super().setUp()
        self._activate_owner()
        self._saved_gemini_key = os.environ.get("GEMINI_API_KEY")
        self._saved_anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
        os.environ["GEMINI_API_KEY"] = "test-key"
        os.environ["ANTHROPIC_API_KEY"] = "test-key"

    def tearDown(self):
        for key, saved in (("GEMINI_API_KEY", self._saved_gemini_key), ("ANTHROPIC_API_KEY", self._saved_anthropic_key)):
            if saved is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = saved
        super().tearDown()

    def test_get_sans_override_plan_effectif_ultra(self):
        resp = self.client.get("/api/owner/test-plan")
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertTrue(body["is_owner"])
        self.assertEqual(body["real_plan"], "free")
        self.assertIsNone(body["test_plan"])
        self.assertEqual(body["effective_plan"], "ultra")
        self.assertEqual((body["provider"], body["model"]), ("anthropic", "claude-sonnet-5"))

    def _patch_plan(self, plan):
        return self.client.patch("/api/owner/test-plan", json={"plan": plan}, headers=self.owner_headers)

    def test_cycle_free_premium_ultra_puis_reset(self):
        expected_chain = {
            "free": ("gemini", "gemini-3-flash-preview"),
            "premium": ("gemini", "gemini-3.1-pro-preview"),
            "ultra": ("anthropic", "claude-sonnet-5"),
        }
        for plan in ("free", "premium", "ultra"):
            with self.subTest(plan=plan):
                # A : users.plan = free, quelle que soit l'itération.
                self.assertEqual(db.get_user_by_id(self.owner_user["id"])["plan"], "free")

                # B : plan de test appliqué via une vraie requête PATCH.
                resp = self._patch_plan(plan)
                self.assertEqual(resp.status_code, 200)
                body = resp.get_json()
                self.assertEqual(body["test_plan"], plan)

                # C : plan effectif = plan de test.
                self.assertEqual(body["effective_plan"], plan)

                # D : has_feature() suit bien le plan effectif (ADVANCED_AI = Ultra only).
                fresh_user = db.get_user_by_id(self.owner_user["id"])
                self.assertEqual(
                    plan_service.has_feature(fresh_user, Feature.ADVANCED_AI),
                    plan == "ultra",
                )

                # E : provider_manager sélectionne réellement la config du plan.
                self.assertEqual((body["provider"], body["model"]), expected_chain[plan])

                # users.plan et Stripe n'ont jamais bougé.
                stored = db.get_user_by_id(self.owner_user["id"])
                self.assertEqual(stored["plan"], "free")
                self.assertIsNone(stored["stripe_subscription_id"])

        # Reset : retour au plan effectif Ultra (comportement owner par défaut).
        resp = self.client.patch("/api/owner/test-plan", json={"plan": None}, headers=self.owner_headers)
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertIsNone(body["test_plan"])
        self.assertEqual(body["effective_plan"], "ultra")
        self.assertEqual((body["provider"], body["model"]), ("anthropic", "claude-sonnet-5"))
        self.assertEqual(db.get_user_by_id(self.owner_user["id"])["plan"], "free")

    def test_unlimited_quotas_toggle_via_route(self):
        self._patch_plan("free")
        resp = self.client.get("/api/quota")
        self.assertEqual(resp.get_json()["chat_messages"]["unlimited"], True)

        resp = self.client.patch("/api/owner/test-plan", json={"unlimited_quotas": False}, headers=self.owner_headers)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.get_json()["owner_unlimited_quotas"])
        resp = self.client.get("/api/quota")
        body = resp.get_json()
        self.assertFalse(body["chat_messages"]["unlimited"])
        self.assertEqual(body["chat_messages"]["limit"], 15)

        resp = self.client.patch("/api/owner/test-plan", json={"unlimited_quotas": True}, headers=self.owner_headers)
        self.assertTrue(resp.get_json()["owner_unlimited_quotas"])
        resp = self.client.get("/api/quota")
        self.assertTrue(resp.get_json()["chat_messages"]["unlimited"])

    def test_plan_invalide_rejete_400_sans_effet(self):
        resp = self.client.patch("/api/owner/test-plan", json={"plan": "gold"}, headers=self.owner_headers)
        self.assertEqual(resp.status_code, 400)
        self.assertIsNone(owner_test_plan_service.get_test_plan(self.owner_user))

    def test_csrf_requis_pour_patch(self):
        resp = self.client.patch("/api/owner/test-plan", json={"plan": "ultra"})
        self.assertEqual(resp.status_code, 403)


# ── Chantier 8 : champ "features" de auth.py::_public_user() ────────────────
class TestPublicUserFeaturesField(OwnerTestPlanServiceTestCase):
    """auth._public_user()["features"] doit être calculé via
    plan_service.has_feature() (donc Owner-aware, suit effective_plan) — pas
    FEATURE_MATRIX[get_plan(user)] directement. Vérifie aussi qu'aucune clé
    inconnue n'apparaît et que toutes les Feature sont couvertes."""

    def _features_of(self, user):
        return auth._public_user(user)["features"]

    def test_toutes_les_cles_correspondent_exactement_a_feature_value(self):
        features = self._features_of(self.random_user)
        self.assertEqual(set(features.keys()), {f.value for f in Feature})

    def test_free_features_correctes(self):
        features = self._features_of(self.random_user)  # Plan.FREE par défaut
        for feature in plan_service.FEATURE_MATRIX[Plan.FREE]:
            self.assertTrue(features[feature.value], feature.value)
        for feature in set(Feature) - plan_service.FEATURE_MATRIX[Plan.FREE]:
            self.assertFalse(features[feature.value], feature.value)

    def test_premium_features_correctes(self):
        user = self._make_user("premium_pub@gmail.com", "premium_pub", Plan.PREMIUM)
        features = self._features_of(user)
        for feature in plan_service.FEATURE_MATRIX[Plan.PREMIUM]:
            self.assertTrue(features[feature.value], feature.value)
        for feature in set(Feature) - plan_service.FEATURE_MATRIX[Plan.PREMIUM]:
            self.assertFalse(features[feature.value], feature.value)

    def test_ultra_features_correctes(self):
        user = self._make_user("ultra_pub@gmail.com", "ultra_pub", Plan.ULTRA)
        features = self._features_of(user)
        for feature in Feature:
            self.assertTrue(features[feature.value], feature.value)

    def test_owner_sans_plan_de_test_a_toutes_les_features(self):
        self._activate_owner()
        features = self._features_of(self.owner_user)
        for feature in Feature:
            self.assertTrue(features[feature.value], feature.value)
        # "plan" reste le plan RÉEL (free) — jamais Ultra par défaut, contrairement à "features".
        self.assertEqual(auth._public_user(self.owner_user)["plan"], "free")

    def test_owner_test_free_features_limitees(self):
        self._activate_owner()
        owner_test_plan_service.set_test_plan(self.owner_user, "free")
        features = self._features_of(self.owner_user)
        for feature in plan_service.FEATURE_MATRIX[Plan.FREE]:
            self.assertTrue(features[feature.value], feature.value)
        self.assertFalse(features[Feature.CHATBOT_UNLIMITED.value])
        self.assertFalse(features[Feature.ADVANCED_AI.value])
        # Le plan réel affiché ne suit toujours pas le plan de test.
        self.assertEqual(auth._public_user(self.owner_user)["plan"], "free")

    def test_owner_test_premium_features_intermediaires(self):
        self._activate_owner()
        owner_test_plan_service.set_test_plan(self.owner_user, "premium")
        features = self._features_of(self.owner_user)
        self.assertTrue(features[Feature.CHATBOT_UNLIMITED.value])
        self.assertTrue(features[Feature.PROFILE_ANALYTICS.value])
        self.assertFalse(features[Feature.ADVANCED_AI.value])
        self.assertFalse(features[Feature.EARLY_ACCESS.value])

    def test_owner_test_ultra_toutes_les_features(self):
        self._activate_owner()
        owner_test_plan_service.set_test_plan(self.owner_user, "ultra")
        features = self._features_of(self.owner_user)
        for feature in Feature:
            self.assertTrue(features[feature.value], feature.value)

    def test_utilisateur_normal_inchange_pendant_test_owner(self):
        self._activate_owner()
        owner_test_plan_service.set_test_plan(self.owner_user, "ultra")
        features = self._features_of(self.random_user)
        self.assertFalse(features[Feature.ADVANCED_AI.value])
        self.assertFalse(features[Feature.CHATBOT_UNLIMITED.value])


# ── Chantier 8 : /api/auth/me expose "features", bout en bout HTTP ─────────
class TestApiAuthMeExposeFeatures(OwnerTestPlanRoutesTestCase):
    def test_plan_et_features_corrects_pour_utilisateur_normal(self):
        resp = self.client.get("/api/auth/me")
        user = resp.get_json()["user"]
        self.assertEqual(user["plan"], "free")
        self.assertEqual(user["effective_plan"], "free")  # identique à "plan" pour un compte normal
        self.assertIn("features", user)
        self.assertEqual(set(user["features"].keys()), {f.value for f in Feature})
        self.assertTrue(user["features"][Feature.CHATBOT.value])
        self.assertFalse(user["features"][Feature.CHATBOT_UNLIMITED.value])

    def test_effective_plan_owner_sans_simulation_est_ultra(self):
        self._activate_owner()
        resp = self.client.get("/api/auth/me")
        user = resp.get_json()["user"]
        self.assertEqual(user["plan"], "free")  # plan réel jamais modifié
        self.assertEqual(user["effective_plan"], "ultra")  # accès owner par défaut

    def test_effective_plan_owner_suit_le_plan_de_test_actif(self):
        self._activate_owner()
        self.client.patch("/api/owner/test-plan", json={"plan": "premium"}, headers=self.owner_headers)
        resp = self.client.get("/api/auth/me")
        user = resp.get_json()["user"]
        self.assertEqual(user["plan"], "free")  # plan réel/Stripe toujours inchangé
        self.assertEqual(user["effective_plan"], "premium")

    def test_effective_plan_owner_revient_au_plan_reel_apres_reset(self):
        self._activate_owner()
        self.client.patch("/api/owner/test-plan", json={"plan": "ultra"}, headers=self.owner_headers)
        self.client.patch("/api/owner/test-plan", json={"plan": None}, headers=self.owner_headers)
        resp = self.client.get("/api/auth/me")
        user = resp.get_json()["user"]
        self.assertEqual(user["effective_plan"], "ultra")  # reset = retour au défaut owner (Ultra), pas au plan de test

    def test_changement_de_plan_de_test_owner_met_a_jour_features_immediatement(self):
        self._activate_owner()
        resp = self.client.get("/api/auth/me")
        self.assertTrue(resp.get_json()["user"]["features"][Feature.ADVANCED_AI.value])  # Ultra par défaut

        self.client.patch("/api/owner/test-plan", json={"plan": "free"}, headers=self.owner_headers)
        resp = self.client.get("/api/auth/me")
        user = resp.get_json()["user"]
        self.assertEqual(user["plan"], "free")  # plan réel inchangé
        self.assertFalse(user["features"][Feature.CHATBOT_UNLIMITED.value])
        self.assertFalse(user["features"][Feature.ADVANCED_AI.value])

        self.client.patch("/api/owner/test-plan", json={"plan": "premium"}, headers=self.owner_headers)
        resp = self.client.get("/api/auth/me")
        user = resp.get_json()["user"]
        self.assertTrue(user["features"][Feature.CHATBOT_UNLIMITED.value])
        self.assertFalse(user["features"][Feature.ADVANCED_AI.value])


if __name__ == "__main__":
    unittest.main()
