"""
Suite du mécanisme "Owner/Developer Override" (webapp/owner_service.py) —
chantier 2026-08-23 : accès illimité (Feature + Quota + meilleure chaîne de
modèle IA) UNIQUEMENT pour le compte configuré via NOVAMATH_OWNER_USER_ID,
totalement isolé du système commercial (Plan/QUOTA_MATRIX/FEATURE_MATRIX) et
du système de rôles d'équipe (Role/NOVAMATH_ADMIN_EMAILS/NOVAMATH_SUPER_
ADMIN_EMAILS) — les deux restent orthogonaux à "owner" par construction.

Base SQLite isolée dans un répertoire temporaire, même pattern que
tests/test_quota_service.py — aucune interférence avec data/novamath.db.
"""
import os
import shutil
import tempfile
import unittest
from pathlib import Path

import db
import owner_service
import plan_service
import quota_service
import role_service
from plan_service import Feature, Plan
from quota_service import QuotaType


class OwnerOverrideTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp_dir = tempfile.mkdtemp()
        self._data_dir_backup = db.DATA_DIR
        self._db_path_backup = db.DB_PATH
        db.DATA_DIR = Path(self._tmp_dir)
        db.DB_PATH = db.DATA_DIR / "novamath.db"
        db.init_db()

        self._saved_owner_env = os.environ.get("NOVAMATH_OWNER_USER_ID")
        os.environ.pop("NOVAMATH_OWNER_USER_ID", None)

        self.free_user = self._make_user("free@gmail.com", "free_user", Plan.FREE)
        self.premium_user = self._make_user("premium@gmail.com", "premium_user", Plan.PREMIUM)
        self.ultra_user = self._make_user("ultra@gmail.com", "ultra_user", Plan.ULTRA)
        self.owner_user = self._make_user("owner@gmail.com", "owner_user", Plan.FREE)
        self.other_admin = self._make_user("admin@gmail.com", "admin_user", Plan.FREE)
        db.set_user_role(self.other_admin["id"], role_service.Role.SUPER_ADMIN.value)
        self.other_admin = db.get_user_by_id(self.other_admin["id"])
        self.random_user = self._make_user("random@gmail.com", "random_user", Plan.FREE)

    def tearDown(self):
        db.DATA_DIR = self._data_dir_backup
        db.DB_PATH = self._db_path_backup
        shutil.rmtree(self._tmp_dir, ignore_errors=True)
        if self._saved_owner_env is None:
            os.environ.pop("NOVAMATH_OWNER_USER_ID", None)
        else:
            os.environ["NOVAMATH_OWNER_USER_ID"] = self._saved_owner_env

    def _make_user(self, email, username, plan):
        user_id = db.create_user(email, username, "Élève", "hash")
        if plan is not Plan.FREE:
            db.set_stripe_subscription(user_id, "sub_test", plan.value, "active")
        return db.get_user_by_id(user_id)

    def _activate_owner(self):
        os.environ["NOVAMATH_OWNER_USER_ID"] = str(self.owner_user["id"])


class TestFailClosedParDefaut(OwnerOverrideTestCase):
    """Sans configuration explicite, personne n'a de privilège owner —
    y compris le compte qui deviendra owner une fois la variable posée."""

    def test_variable_absente_aucun_owner(self):
        for user in (self.owner_user, self.free_user, self.premium_user, self.ultra_user, self.other_admin, self.random_user):
            with self.subTest(user=user["email"]):
                self.assertFalse(owner_service.is_owner_account(user))

    def test_variable_non_numerique_aucun_owner(self):
        os.environ["NOVAMATH_OWNER_USER_ID"] = "abc"
        self.assertFalse(owner_service.is_owner_account(self.owner_user))

    def test_variable_vide_aucun_owner(self):
        os.environ["NOVAMATH_OWNER_USER_ID"] = ""
        self.assertFalse(owner_service.is_owner_account(self.owner_user))

    def test_user_none_ou_vide_jamais_owner(self):
        self._activate_owner()
        self.assertFalse(owner_service.is_owner_account(None))
        self.assertFalse(owner_service.is_owner_account({}))


class TestIsolationDesAutresComptes(OwnerOverrideTestCase):
    """TESTS 5 et 6 explicitement demandés : ni un autre admin/super_admin,
    ni un utilisateur quelconque n'obtient les droits owner."""

    def test_autre_super_admin_pas_de_droits_owner(self):
        self._activate_owner()
        self.assertIs(role_service.get_role(self.other_admin), role_service.Role.SUPER_ADMIN)
        self.assertFalse(owner_service.is_owner_account(self.other_admin))
        self.assertFalse(plan_service.has_feature(self.other_admin, Feature.ADVANCED_AI))
        self.assertEqual(quota_service.get_limit(self.other_admin, QuotaType.CHAT_MESSAGES), 15)

    def test_utilisateur_quelconque_pas_de_droits_owner(self):
        self._activate_owner()
        self.assertFalse(owner_service.is_owner_account(self.random_user))
        self.assertFalse(plan_service.has_feature(self.random_user, Feature.ADVANCED_AI))


class TestCompteOwnerIllimite(OwnerOverrideTestCase):
    """TEST 1 explicitement demandé : mon compte -> illimité (toutes
    features, tous quotas, quel que soit son plan Stripe réel — FREE ici,
    jamais réécrit en base)."""

    def test_owner_a_toutes_les_features(self):
        self._activate_owner()
        for feature in Feature:
            with self.subTest(feature=feature):
                self.assertTrue(plan_service.has_feature(self.owner_user, feature))

    def test_owner_tous_quotas_illimites(self):
        self._activate_owner()
        for quota in QuotaType:
            with self.subTest(quota=quota):
                self.assertTrue(quota_service.is_unlimited(self.owner_user, quota))
                self.assertIsNone(quota_service.get_limit(self.owner_user, quota))

    def test_owner_peut_consommer_sans_limite(self):
        self._activate_owner()
        for _ in range(1000):
            quota_service.consume(self.owner_user, QuotaType.CHAT_MESSAGES)
        # Toujours illimité après 1000 consommations — aucune QuotaExceededError levée.
        self.assertTrue(quota_service.can_consume(self.owner_user, QuotaType.CHAT_MESSAGES, amount=10_000))

    def test_owner_plan_reel_en_base_reste_free_jamais_reecrit(self):
        # L'override ne modifie jamais users.plan : conforme à la contrainte
        # explicite "ne transforme pas réellement mon compte en Ultra".
        self._activate_owner()
        self.assertIs(plan_service.get_plan(self.owner_user), Plan.FREE)
        stored = db.get_user_by_id(self.owner_user["id"])
        self.assertEqual(stored["plan"], "free")


class TestAutresUtilisateursInchanges(OwnerOverrideTestCase):
    """TESTS 2, 3, 4 explicitement demandés : Free/Premium/Ultra normaux
    inchangés, override actif ou non."""

    def test_free_normal_quota_inchange(self):
        self._activate_owner()
        self.assertFalse(quota_service.is_unlimited(self.free_user, QuotaType.CHAT_MESSAGES))
        self.assertEqual(quota_service.get_limit(self.free_user, QuotaType.CHAT_MESSAGES), 15)
        self.assertFalse(plan_service.has_feature(self.free_user, Feature.ADVANCED_AI))

    def test_premium_normal_quota_inchange(self):
        self._activate_owner()
        self.assertEqual(quota_service.get_limit(self.premium_user, QuotaType.CHAT_MESSAGES), 25)
        self.assertTrue(plan_service.has_feature(self.premium_user, Feature.CHATBOT_UNLIMITED))
        self.assertFalse(plan_service.has_feature(self.premium_user, Feature.ADVANCED_AI))

    def test_ultra_normal_quota_inchange(self):
        self._activate_owner()
        # CHAT_MESSAGES Ultra = 40/j depuis le Chantier 6 (plus illimité) —
        # PDF_ANALYSIS reste, lui, illimité pour Ultra.
        self.assertEqual(quota_service.get_limit(self.ultra_user, QuotaType.CHAT_MESSAGES), 40)
        self.assertTrue(quota_service.is_unlimited(self.ultra_user, QuotaType.PDF_ANALYSIS))
        self.assertTrue(plan_service.has_feature(self.ultra_user, Feature.ADVANCED_AI))

    def test_free_atteint_bien_sa_limite_quotidienne(self):
        self._activate_owner()
        for _ in range(15):
            quota_service.consume(self.free_user, QuotaType.CHAT_MESSAGES)
        with self.assertRaises(quota_service.QuotaExceededError):
            quota_service.consume(self.free_user, QuotaType.CHAT_MESSAGES)


class TestFrontendNePeutJamaisActiverLoverride(OwnerOverrideTestCase):
    """L'override est déterminé uniquement par user["id"] (chargé côté
    serveur depuis la session) — jamais par une donnée envoyée par le
    client. Un dict falsifié imitant l'id owner sans être réellement chargé
    depuis la session ne peut pas exister dans le pipeline réel (server.py
    ne construit jamais `request.current_user` depuis le corps JSON), mais
    on vérifie ici que la fonction elle-même ne consulte aucun champ
    « déclaratif » (ex: un champ `is_owner`/`role` envoyé dans le dict) —
    seul `id` compte."""

    def test_champ_is_owner_declare_dans_le_dict_est_ignore(self):
        self._activate_owner()
        faux_dict = {"id": self.random_user["id"], "is_owner": True, "role": "super_admin", "plan": "ultra"}
        self.assertFalse(owner_service.is_owner_account(faux_dict))

    def test_seul_lid_reel_du_compte_owner_declenche_loverride(self):
        self._activate_owner()
        vrai_dict = {"id": self.owner_user["id"]}
        self.assertTrue(owner_service.is_owner_account(vrai_dict))


class TestProviderManagerChaineUltraPourOwner(OwnerOverrideTestCase):
    """L'override s'étend à la sélection du meilleur modèle IA (chaîne
    Ultra) sans jamais modifier plan_service.get_plan()/users.plan."""

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

    def test_owner_recoit_la_chaine_ultra(self):
        from chatbot import provider_manager

        self._activate_owner()
        provider_name, model = provider_manager.select_llm_for_user(self.owner_user)
        self.assertEqual((provider_name, model), ("anthropic", "claude-sonnet-5"))

    def test_free_normal_recoit_toujours_la_chaine_free(self):
        from chatbot import provider_manager

        self._activate_owner()
        provider_name, model = provider_manager.select_llm_for_user(self.free_user)
        self.assertEqual((provider_name, model), ("gemini", "gemini-3-flash-preview"))


if __name__ == "__main__":
    unittest.main()
