"""Gratuité des fonctionnalités pédagogiques (config.PEDAGOGY_FREE).

Vérifie : accès aux cours complets, exercices illimités, statistiques et
exercices sur mesure pour tous les paliers (y compris d'anciens Premium/
Ultra) ; chatbot IA inchangé (quota, routage) ; Owner inchangé ; achat de
nouveaux abonnements fermé ; retour à l'ancien comportement avec le drapeau
désactivé (réversibilité).
"""
import random
import unittest
from unittest import mock

import config
import course_content_service
import owner_service
import owner_test_plan_service
import plan_service
import quota_service
import server
from chatbot import provider_manager
from plan_service import Feature, Plan
from quota_service import QuotaType, UNLIMITED

PEDAGOGY_FEATURES = [
    Feature.COURSES, Feature.EXERCISES, Feature.STATISTICS, Feature.HISTORY, Feature.GOALS, Feature.EXPORT,
    Feature.ADVANCED_EXPLANATIONS, Feature.PROFILE_ANALYTICS, Feature.CUSTOM_EXERCISES,
]
CHATBOT_AI_FEATURES = [
    Feature.CHATBOT_UNLIMITED, Feature.ADVANCED_AI, Feature.LONG_RESPONSES, Feature.PRIORITY_QUEUE,
    Feature.PRIORITY_SUPPORT,
]


def _user(plan):
    return {"id": 987654, "plan": plan}


def _register(client):
    resp = client.post("/api/auth/register", json={
        "email": f"free{random.randint(1_000_000, 9_999_999)}@gmail.com",
        "username": f"freeuser{random.randint(100_000, 999_999)}", "pseudo": "Test",
        "birth_date": "2000-01-01",
        "password": "MotDePasse123!", "confirm_password": "MotDePasse123!",
        "accept_terms": True, "accept_privacy": True,
    })
    assert resp.status_code == 201, resp.get_data(as_text=True)
    return {"X-CSRF-Token": client.get_cookie("nm_csrf").value}


class _FlagOn(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.object(config, "PEDAGOGY_FREE", True)
        patcher.start()
        self.addCleanup(patcher.stop)


class TestFonctionnalitesGratuites(_FlagOn):
    def test_tous_les_paliers_ont_les_fonctionnalites_pedagogiques(self):
        for plan in ("free", "premium", "ultra"):
            for feature in PEDAGOGY_FEATURES:
                with self.subTest(plan=plan, feature=feature.value):
                    self.assertTrue(plan_service.has_feature(_user(plan), feature))

    def test_fonctionnalites_ia_non_ouvertes(self):
        for plan in ("free", "premium", "ultra"):
            for feature in CHATBOT_AI_FEATURES:
                with self.subTest(plan=plan, feature=feature.value):
                    self.assertFalse(plan_service.has_feature(_user(plan), feature))

    def test_quotas_pedagogiques_illimites_pour_tous(self):
        for plan in ("free", "premium", "ultra"):
            for quota in (QuotaType.EXERCISES_DAILY, QuotaType.CUSTOM_EXERCISES, QuotaType.EXPORTS):
                with self.subTest(plan=plan, quota=quota.value):
                    self.assertEqual(quota_service.get_limit(_user(plan), quota), UNLIMITED)

    def test_cours_complets_pour_tous(self):
        for plan in ("free", "premium", "ultra"):
            self.assertIs(course_content_service._effective_plan(_user(plan)), Plan.ULTRA)

    def test_statistiques_sans_fenetre_ni_limite_de_suggestions(self):
        plan = plan_service.pedagogy_plan(Plan.FREE)
        self.assertIsNone(server._STATS_SERIES_WINDOW[plan])
        self.assertEqual(server._SUGGESTIONS_LIMIT_BY_PLAN[plan], 8)


class TestChatbotInchange(_FlagOn):
    def test_quota_chatbot_free_pour_tous_les_comptes(self):
        free = {q: quota_service.get_limit(_user("free"), q) for q in QuotaType}
        for plan in ("premium", "ultra"):
            for quota in (QuotaType.CHAT_MESSAGES, QuotaType.LLM_CALLS, QuotaType.PDF_ANALYSIS,
                          QuotaType.AI_GENERATIONS):
                with self.subTest(plan=plan, quota=quota.value):
                    self.assertEqual(quota_service.get_limit(_user(plan), quota), free[quota])
        self.assertEqual(free[QuotaType.CHAT_MESSAGES], quota_service.QUOTA_MATRIX[Plan.FREE][QuotaType.CHAT_MESSAGES])
        self.assertEqual(free[QuotaType.CHAT_MESSAGES], 15)

    def test_routage_ia_free_pour_tous_les_comptes(self):
        for plan in ("premium", "ultra"):
            with self.subTest(plan=plan):
                self.assertIs(owner_test_plan_service.effective_plan(_user(plan)), Plan.FREE)
                self.assertEqual(
                    provider_manager.select_llm_for_user(_user(plan)),
                    provider_manager.select_llm_for_user(_user("free")),
                )

    def test_owner_inchange(self):
        with mock.patch.object(owner_service, "is_owner_account", return_value=True), \
                mock.patch.object(owner_test_plan_service, "get_test_plan", return_value=None):
            self.assertIs(owner_test_plan_service.effective_plan(_user("free")), Plan.ULTRA)
        with mock.patch.object(owner_service, "is_owner_account", return_value=True), \
                mock.patch.object(owner_test_plan_service, "get_test_plan", return_value=Plan.PREMIUM):
            self.assertIs(owner_test_plan_service.effective_plan(_user("free")), Plan.PREMIUM)


class TestAchatFerme(_FlagOn):
    def test_creation_de_session_de_paiement_refusee(self):
        client = server.app.test_client()
        headers = _register(client)
        for plan in ("premium", "ultra"):
            resp = client.post("/api/checkout/create-session", json={"plan": plan}, headers=headers)
            self.assertEqual(resp.status_code, 410)
            self.assertEqual(resp.get_json()["code"], "pedagogy_free")

    def test_gestion_des_abonnements_existants_non_bloquee(self):
        client = server.app.test_client()
        headers = _register(client)
        # Route de gestion : répond par sa propre logique métier (pas de 410).
        resp = client.post("/api/billing/change-plan", json={"plan": "premium"}, headers=headers)
        self.assertNotEqual(resp.status_code, 410)
        self.assertEqual(client.get("/api/billing/status").status_code, 200)


class TestExercicesIllimites(unittest.TestCase):
    def _load_many(self, n):
        client = server.app.test_client()
        headers = _register(client)
        exercise_id = server.BANK[0]["id"]
        return [
            client.post("/api/practice/load", json={"exercise_id": exercise_id, "class_level": "seconde"},
                        headers=headers).status_code
            for _ in range(n)
        ]

    def test_plus_de_limite_quotidienne_avec_la_gratuite(self):
        with mock.patch.object(config, "PEDAGOGY_FREE", True):
            self.assertEqual(set(self._load_many(23)), {200})

    def test_ancienne_limite_rétablie_sans_la_gratuite(self):
        with mock.patch.object(config, "PEDAGOGY_FREE", False):
            codes = self._load_many(22)
        self.assertEqual(codes[:20], [200] * 20)
        self.assertEqual(codes[20], 429)


class TestInterfaceSansOffre(unittest.TestCase):
    def _logged_client(self):
        client = server.app.test_client()
        _register(client)
        return client

    def test_classe_pedagogy_free_posee_sur_les_pages_eleves(self):
        with mock.patch.object(config, "PEDAGOGY_FREE", True):
            client = self._logged_client()
            for page in ("dashboard.html", "profil.html", "chapitres.html", "cours.html", "exercice.html", "chatbot.html"):
                with self.subTest(page=page):
                    html = client.get(f"/{page}").get_data(as_text=True)
                    self.assertIn('classList.add("pedagogy-free")', html)

    def test_page_abonnement_redirigee_vers_le_profil(self):
        with mock.patch.object(config, "PEDAGOGY_FREE", True):
            resp = self._logged_client().get("/abonnement.html")
            self.assertEqual(resp.status_code, 302)
            self.assertTrue(resp.headers["Location"].endswith("/profil.html"))

    def test_sans_la_gratuite_ancienne_interface_intacte(self):
        with mock.patch.object(config, "PEDAGOGY_FREE", False):
            client = self._logged_client()
            self.assertNotIn("pedagogy-free", client.get("/dashboard.html").get_data(as_text=True))
            self.assertEqual(client.get("/abonnement.html").status_code, 200)


class TestReversibilite(unittest.TestCase):
    def test_drapeau_desactive_rend_les_paliers_historiques(self):
        with mock.patch.object(config, "PEDAGOGY_FREE", False):
            self.assertFalse(plan_service.has_feature(_user("free"), Feature.CUSTOM_EXERCISES))
            self.assertTrue(plan_service.has_feature(_user("ultra"), Feature.CUSTOM_EXERCISES))
            self.assertEqual(quota_service.get_limit(_user("free"), QuotaType.EXERCISES_DAILY), 20)
            self.assertEqual(quota_service.get_limit(_user("premium"), QuotaType.CHAT_MESSAGES), 25)
            self.assertIs(owner_test_plan_service.effective_plan(_user("ultra")), Plan.ULTRA)


if __name__ == "__main__":
    unittest.main()
