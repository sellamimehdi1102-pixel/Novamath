"""
Suite de bout en bout du gating Feature Flags sur les routes Flask
(webapp/server.py) : vérifie que @requires_feature(...) est effectivement
branché où il doit l'être, avec le bon comportement pour FREE/PREMIUM/ULTRA,
et que les routes explicitement exclues (login/logout/register/checkout/
webhook) restent accessibles sans aucune vérification de plan.

Le format de refus (403 JSON) et le mécanisme de redirection des pages
protégées (_serve_protected/PAGE_FEATURE_REQUIREMENTS) sont couverts ici en
complément de tests/test_plan_service.py (qui couvre plan_service.py de
façon isolée, indépendamment de server.py).
"""
import random
import unittest

import db
import server
from plan_service import Plan


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


def _set_plan(user_id, plan):
    db.set_stripe_subscription(user_id, "sub_test", plan.value, "active")


class TestFreeTierFeaturesAccessibleToAll(unittest.TestCase):
    """Les features rangées en Free (STATISTICS, COURSES, EXERCISES, GOALS,
    CHATBOT, EXPORT) ne doivent restreindre PERSONNE — @requires_feature y
    est branché pour la cohérence architecturale (une seule source de
    vérité), pas pour bloquer qui que ce soit aujourd'hui."""

    def setUp(self):
        self.client = server.app.test_client()
        self.user, self.headers = _register(self.client)

    def test_api_stats_statistics(self):
        self.assertEqual(self.client.get("/api/stats").status_code, 200)

    def test_api_course_progress_courses(self):
        resp = self.client.get("/api/course-progress")
        self.assertEqual(resp.status_code, 200)

    def test_api_data_summary_export(self):
        self.assertEqual(self.client.get("/api/data/summary").status_code, 200)

    def test_api_goals_daily_goals(self):
        self.assertEqual(self.client.get("/api/goals/daily").status_code, 200)

    def test_api_chatbot_quota_chatbot(self):
        self.assertEqual(self.client.get("/api/chatbot/quota").status_code, 200)

    def test_api_start_exercises(self):
        resp = self.client.post(
            "/api/start", json={"chapters": []}, headers=self.headers,
        )
        self.assertNotEqual(resp.status_code, 403)

    def test_toujours_vrai_pour_premium_et_ultra_aussi(self):
        for plan in (Plan.PREMIUM, Plan.ULTRA):
            _set_plan(self.user["id"], plan)
            with self.subTest(plan=plan):
                self.assertEqual(self.client.get("/api/stats").status_code, 200)
                self.assertEqual(self.client.get("/api/chatbot/quota").status_code, 200)


class TestAdvancedAiIsUltraOnly(unittest.TestCase):
    """Feature.ADVANCED_AI (analyse de PDF joint au chatbot) : seule
    restriction réelle et nouvelle de cette intégration — bloquée pour Free
    ET Premium, débloquée uniquement pour Ultra."""

    ENDPOINT = "/api/chatbot/attachments/pdf"

    def setUp(self):
        self.client = server.app.test_client()
        self.user, self.headers = _register(self.client)

    def _post(self):
        return self.client.post(
            self.ENDPOINT, data={}, content_type="multipart/form-data", headers=self.headers,
        )

    def test_free_est_bloque(self):
        resp = self._post()
        self.assertEqual(resp.status_code, 403)
        body = resp.get_json()
        self.assertEqual(body["error"], "premium_required")
        self.assertEqual(body["feature"], "advanced_ai")
        self.assertEqual(body["required_plan"], "ultra")

    def test_premium_est_aussi_bloque(self):
        _set_plan(self.user["id"], Plan.PREMIUM)
        resp = self._post()
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.get_json()["required_plan"], "ultra")

    def test_ultra_passe_le_gate(self):
        _set_plan(self.user["id"], Plan.ULTRA)
        resp = self._post()
        # Passé le contrôle de plan, la route atteint sa propre validation
        # métier (aucun fichier envoyé) — jamais 403 pour un utilisateur Ultra.
        self.assertNotEqual(resp.status_code, 403)
        self.assertEqual(resp.status_code, 400)

    def test_utilisateur_non_connecte_est_bloque(self):
        anon_client = server.app.test_client()
        resp = anon_client.post(
            self.ENDPOINT, data={}, content_type="multipart/form-data",
        )
        # login_required s'exécute avant requires_feature dans la pile de
        # décorateurs : un anonyme est rejeté par login_required (401),
        # jamais laissé atteindre le contrôle de feature.
        self.assertEqual(resp.status_code, 401)


class TestExcludedRoutesNeverGated(unittest.TestCase):
    """login/logout/register/checkout/webhook : jamais de contrôle de plan,
    quel que soit le compte (y compris anonyme)."""

    def setUp(self):
        self.client = server.app.test_client()

    def test_register_accessible_sans_plan(self):
        _, resp_status = self._register_status()
        self.assertNotEqual(resp_status, 403)

    def _register_status(self):
        email = f"test{random.randint(1_000_000, 9_999_999)}@gmail.com"
        resp = self.client.post("/api/auth/register", json={
            "email": email, "username": f"user{random.randint(100000,999999)}", "pseudo": "T",
            "birth_date": "2000-01-01",
            "password": "MotDePasse123!", "confirm_password": "MotDePasse123!",
            "accept_terms": True, "accept_privacy": True,
        })
        return resp, resp.status_code

    def test_login_accessible_sans_plan(self):
        resp = self.client.post("/api/auth/login", json={"email": "x@gmail.com", "password": "wrong"})
        self.assertNotEqual(resp.status_code, 403)

    def test_logout_accessible_sans_plan(self):
        resp = self.client.post("/api/auth/logout")
        self.assertNotEqual(resp.status_code, 403)

    def test_checkout_webhook_accessible_sans_plan(self):
        # Signature absente -> 400 (voir stripe_service), jamais 403 "premium_required".
        resp = self.client.post("/api/checkout/webhook", data=b"{}")
        self.assertNotEqual(resp.status_code, 403)

    def test_checkout_create_session_accessible_a_tout_plan_connecte(self):
        user, headers = _register(self.client)
        # Refusé pour une raison métier (plan cible manquant), jamais parce
        # que le compte lui-même n'aurait pas le droit d'accéder à la route.
        resp = self.client.post("/api/checkout/create-session", json={"plan": "bad"}, headers=headers)
        self.assertEqual(resp.status_code, 400)
        self.assertNotEqual(resp.get_json().get("error"), "premium_required")


class TestProtectedPageFeatureGate(unittest.TestCase):
    """PAGE_FEATURE_REQUIREMENTS est vide aujourd'hui (aucune page n'excède
    Free) : ce test prouve que le mécanisme de redirection fonctionne
    correctement s'il venait à être peuplé, sans dépendre d'une vraie page
    verrouillée en dur dans le produit."""

    def setUp(self):
        self.client = server.app.test_client()
        self.user, _ = _register(self.client)
        self._original = dict(server.PAGE_FEATURE_REQUIREMENTS)

    def tearDown(self):
        server.PAGE_FEATURE_REQUIREMENTS.clear()
        server.PAGE_FEATURE_REQUIREMENTS.update(self._original)

    def test_redirige_vers_abonnement_si_feature_manquante(self):
        server.PAGE_FEATURE_REQUIREMENTS["dashboard.html"] = server.Feature.ADVANCED_AI
        resp = self.client.get("/dashboard.html")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/abonnement.html?required=advanced_ai", resp.headers["Location"])

    def test_laisse_passer_si_lutilisateur_a_la_feature(self):
        server.PAGE_FEATURE_REQUIREMENTS["dashboard.html"] = server.Feature.STATISTICS
        resp = self.client.get("/dashboard.html")
        self.assertEqual(resp.status_code, 200)

    def test_aucune_page_actuelle_nest_verrouillee_par_defaut(self):
        for page in server.PROTECTED_PAGES:
            with self.subTest(page=page):
                self.assertNotIn(page, self._original)


if __name__ == "__main__":
    unittest.main()
