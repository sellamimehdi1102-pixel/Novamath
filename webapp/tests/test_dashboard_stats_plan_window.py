"""
Suite du chantier "Répartition des options du dashboard par plan" (2026-08-26) :
GET /api/stats limite désormais `series[]` (utilisée par le graphique et la
table "dernières séries" du dashboard) selon le plan effectif de
l'utilisateur — Free = 20 dernières séries, Premium = 50, Ultra = complet.

`history[]` — dont dépendent seuls streak/XP/mastery/badges/accuracy côté
client (store.js) — n'est JAMAIS tronqué : la vérification technique
préalable (voir server.py::_STATS_SERIES_WINDOW et son commentaire) a
confirmé qu'aucune de ces fonctions n'utilise `series` (store.js::BADGE_DEFS
teste uniquement `s.history`), donc réduire `series[]` seul est sûr pour ces
fonctionnalités essentielles du Free.

Même mécanisme générique que course_content_service.py et quota_service.py
(owner_test_plan_service.effective_plan) — aucun nouveau système de plan.
"""
import os
import random
import unittest

import db
import owner_test_plan_service
import server


def _register(client):
    email = f"dashstats{random.randint(1_000_000, 9_999_999)}@gmail.com"
    username = f"dashstats{random.randint(100_000, 999_999)}"
    resp = client.post("/api/auth/register", json={
        "email": email, "username": username, "pseudo": "Test",
        "birth_date": "2000-01-01",
        "password": "MotDePasse123!", "confirm_password": "MotDePasse123!",
        "accept_terms": True, "accept_privacy": True,
    })
    user = resp.get_json()["user"]
    csrf = client.get_cookie("nm_csrf").value
    return user, {"X-CSRF-Token": csrf}


def _set_plan(user_id, plan_value):
    db.set_stripe_subscription(user_id, "sub_test", plan_value, "active")


def _history_entry(ts):
    return {
        "id": f"ex_{ts}", "date": "2026-01-01", "ts": ts, "chapter": "ch1",
        "notion": "n1", "difficulty": 1, "correct": ts % 2 == 0, "mode": "revisions",
        "duration_s": 10, "xp": 5, "class_level": "seconde",
    }


def _series_entry(started_at):
    return {
        "id": f"s_{started_at}", "startedAt": started_at, "endedAt": started_at + 100,
        "mode": "revisions", "chapterId": "Chapitre_1", "notion": "n1", "questions": [],
        "score": 8, "total": 10, "accuracy": 80, "durationTotal_s": 100,
        "class_level": "seconde",
    }


class DashboardStatsTestCase(unittest.TestCase):
    def setUp(self):
        self.client = server.app.test_client()
        self.user, self.headers = _register(self.client)

    def _seed(self, n_history=25, n_series=25):
        history = [_history_entry(i) for i in range(1, n_history + 1)]
        series = [_series_entry(i) for i in range(1, n_series + 1)]
        self.client.post("/api/stats", json={
            "xp": 0, "history": history, "badges": [], "series": series,
        }, headers=self.headers)
        return history, series


class TestFreeSeriesWindow(DashboardStatsTestCase):
    def test_series_limitee_a_20_dernieres(self):
        self._seed(n_history=25, n_series=25)
        body = self.client.get("/api/stats", headers=self.headers).get_json()
        self.assertEqual(len(body["series"]), 20)
        # Les 20 CONSERVÉES doivent être les plus récentes (startedAt 6..25),
        # dans l'ordre chronologique déjà utilisé par le dashboard.
        self.assertEqual([s["startedAt"] for s in body["series"]], list(range(6, 26)))

    def test_history_reste_complet(self):
        self._seed(n_history=25, n_series=25)
        body = self.client.get("/api/stats", headers=self.headers).get_json()
        self.assertEqual(len(body["history"]), 25)

    def test_moins_de_20_series_nest_pas_tronque(self):
        self._seed(n_history=5, n_series=5)
        body = self.client.get("/api/stats", headers=self.headers).get_json()
        self.assertEqual(len(body["series"]), 5)


class TestPremiumSeriesWindow(DashboardStatsTestCase):
    def test_series_limitee_a_50_dernieres(self):
        _set_plan(self.user["id"], "premium")
        self._seed(n_history=60, n_series=60)
        body = self.client.get("/api/stats", headers=self.headers).get_json()
        self.assertEqual(len(body["series"]), 50)
        self.assertEqual([s["startedAt"] for s in body["series"]], list(range(11, 61)))

    def test_history_reste_complet(self):
        _set_plan(self.user["id"], "premium")
        self._seed(n_history=60, n_series=60)
        body = self.client.get("/api/stats", headers=self.headers).get_json()
        self.assertEqual(len(body["history"]), 60)


class TestUltraSeriesWindow(DashboardStatsTestCase):
    def test_series_complet(self):
        _set_plan(self.user["id"], "ultra")
        self._seed(n_history=80, n_series=80)
        body = self.client.get("/api/stats", headers=self.headers).get_json()
        self.assertEqual(len(body["series"]), 80)

    def test_history_reste_complet(self):
        _set_plan(self.user["id"], "ultra")
        self._seed(n_history=80, n_series=80)
        body = self.client.get("/api/stats", headers=self.headers).get_json()
        self.assertEqual(len(body["history"]), 80)


class TestApiStatsAuth(unittest.TestCase):
    def test_non_connecte_401(self):
        anon = server.app.test_client()
        resp = anon.get("/api/stats")
        self.assertEqual(resp.status_code, 401)


class TestStatistiquesEssentiellesNonAffectees(DashboardStatsTestCase):
    """La troncature de series[] ne doit JAMAIS changer streak/XP/mastery/
    badges/accuracy calculés côté client à partir de history[] — on ne peut
    pas exécuter store.js ici, mais on peut prouver que history[] (leur seule
    source) est bit-à-bit identique à ce qui a été posté, quel que soit le
    plan, ce qui garantit la stabilité de ces calculs en aval."""

    def test_free_history_identique_a_lenvoye(self):
        history, _ = self._seed(n_history=30, n_series=30)
        body = self.client.get("/api/stats", headers=self.headers).get_json()
        self.assertEqual(sorted(h["ts"] for h in body["history"]), sorted(h["ts"] for h in history))
        self.assertEqual(body["xp"], sum(h["xp"] for h in history))

    def test_premium_history_identique_a_lenvoye(self):
        _set_plan(self.user["id"], "premium")
        history, _ = self._seed(n_history=30, n_series=30)
        body = self.client.get("/api/stats", headers=self.headers).get_json()
        self.assertEqual(sorted(h["ts"] for h in body["history"]), sorted(h["ts"] for h in history))

    def test_ultra_history_identique_a_lenvoye(self):
        _set_plan(self.user["id"], "ultra")
        history, _ = self._seed(n_history=30, n_series=30)
        body = self.client.get("/api/stats", headers=self.headers).get_json()
        self.assertEqual(sorted(h["ts"] for h in body["history"]), sorted(h["ts"] for h in history))


class TestSuggestionsLimitByPlan(DashboardStatsTestCase):
    """Chantier "Différenciation des abonnements — suggestions du Dashboard"
    (2026-08-27) : GET /api/stats expose désormais suggestions_limit
    (Free=3/Premium=5/Ultra=8, voir server.py::_SUGGESTIONS_LIMIT_BY_PLAN) —
    un plafond d'AFFICHAGE, jamais un recalcul des suggestions elles-mêmes
    (toujours calculées côté client à partir de history[], inchangé)."""

    def test_free_suggestions_limit_egale_3(self):
        self._seed(n_history=5, n_series=5)
        body = self.client.get("/api/stats", headers=self.headers).get_json()
        self.assertEqual(body["suggestions_limit"], 3)

    def test_premium_suggestions_limit_egale_5(self):
        _set_plan(self.user["id"], "premium")
        self._seed(n_history=5, n_series=5)
        body = self.client.get("/api/stats", headers=self.headers).get_json()
        self.assertEqual(body["suggestions_limit"], 5)

    def test_ultra_suggestions_limit_egale_8(self):
        _set_plan(self.user["id"], "ultra")
        self._seed(n_history=5, n_series=5)
        body = self.client.get("/api/stats", headers=self.headers).get_json()
        self.assertEqual(body["suggestions_limit"], 8)

    def test_suggestions_limit_naffecte_pas_history(self):
        history, _ = self._seed(n_history=30, n_series=30)
        body = self.client.get("/api/stats", headers=self.headers).get_json()
        self.assertEqual(len(body["history"]), 30)
        self.assertIn("suggestions_limit", body)

    def test_suggestions_limit_naffecte_pas_series(self):
        _set_plan(self.user["id"], "premium")
        self._seed(n_history=60, n_series=60)
        body = self.client.get("/api/stats", headers=self.headers).get_json()
        self.assertEqual(len(body["series"]), 50)  # fenêtre Premium inchangée
        self.assertEqual(body["suggestions_limit"], 5)


class TestSuggestionsLimitOwnerTestPlan(DashboardStatsTestCase):
    def setUp(self):
        super().setUp()
        self._saved_owner_env = os.environ.get("NOVAMATH_OWNER_USER_ID")
        os.environ["NOVAMATH_OWNER_USER_ID"] = str(self.user["id"])

    def tearDown(self):
        owner_test_plan_service.set_test_plan(self.user, None)
        owner_test_plan_service.set_unlimited_quotas(self.user, True)
        if self._saved_owner_env is None:
            os.environ.pop("NOVAMATH_OWNER_USER_ID", None)
        else:
            os.environ["NOVAMATH_OWNER_USER_ID"] = self._saved_owner_env

    def test_owner_test_free_suggestions_limit_3(self):
        owner_test_plan_service.set_test_plan(self.user, "free")
        self._seed(n_history=5, n_series=5)
        body = self.client.get("/api/stats", headers=self.headers).get_json()
        self.assertEqual(body["suggestions_limit"], 3)

    def test_owner_test_premium_suggestions_limit_5(self):
        owner_test_plan_service.set_test_plan(self.user, "premium")
        self._seed(n_history=5, n_series=5)
        body = self.client.get("/api/stats", headers=self.headers).get_json()
        self.assertEqual(body["suggestions_limit"], 5)

    def test_owner_test_ultra_suggestions_limit_8(self):
        owner_test_plan_service.set_test_plan(self.user, "ultra")
        self._seed(n_history=5, n_series=5)
        body = self.client.get("/api/stats", headers=self.headers).get_json()
        self.assertEqual(body["suggestions_limit"], 8)

    def test_owner_sans_test_actif_recoit_le_defaut_ultra(self):
        """Owner sans plan de test actif = effective_plan Ultra par défaut
        (owner_test_plan_service.effective_plan), même comportement que pour
        series[]/quotas ailleurs dans le projet — jamais un cas spécial ici."""
        self._seed(n_history=5, n_series=5)
        body = self.client.get("/api/stats", headers=self.headers).get_json()
        self.assertEqual(body["suggestions_limit"], 8)


class TestOwnerTestPlanRespecte(DashboardStatsTestCase):
    def setUp(self):
        super().setUp()
        self._saved_owner_env = os.environ.get("NOVAMATH_OWNER_USER_ID")
        os.environ["NOVAMATH_OWNER_USER_ID"] = str(self.user["id"])

    def tearDown(self):
        # Nettoyage impératif (system_settings est une table GLOBALE, pas de
        # DB isolée dans cette suite — voir server.app.test_client() ci-dessus) :
        # sans cela, un plan de test laissé actif pollue les tests suivants
        # touchant un compte owner, y compris dans d'autres fichiers exécutés
        # dans la même session pytest. Effectué AVANT de restaurer la
        # variable d'environnement, tant que self.user est encore reconnu
        # comme owner.
        owner_test_plan_service.set_test_plan(self.user, None)
        owner_test_plan_service.set_unlimited_quotas(self.user, True)
        if self._saved_owner_env is None:
            os.environ.pop("NOVAMATH_OWNER_USER_ID", None)
        else:
            os.environ["NOVAMATH_OWNER_USER_ID"] = self._saved_owner_env

    def test_owner_test_free_limite_bien_a_20(self):
        owner_test_plan_service.set_test_plan(self.user, "free")
        self._seed(n_history=25, n_series=25)
        body = self.client.get("/api/stats", headers=self.headers).get_json()
        self.assertEqual(len(body["series"]), 20)

    def test_owner_test_ultra_recoit_tout(self):
        owner_test_plan_service.set_test_plan(self.user, "ultra")
        self._seed(n_history=25, n_series=25)
        body = self.client.get("/api/stats", headers=self.headers).get_json()
        self.assertEqual(len(body["series"]), 25)


class TestNotionBreakdownEnabled(DashboardStatsTestCase):
    """Chantier "Différenciateurs Premium/Ultra" (2026-08-27) : GET /api/stats
    expose désormais notion_breakdown_enabled, réutilisant Feature.
    ADVANCED_EXPLANATIONS (déjà Premium+ dans FEATURE_MATRIX) — jamais une
    nouvelle Feature. Le calcul du bilan lui-même reste entièrement côté
    client (dashboard.js/store.js::notionBreakdown), ce champ n'est qu'une
    autorisation d'affichage."""

    def test_free_notion_breakdown_desactive(self):
        self._seed(n_history=5, n_series=5)
        body = self.client.get("/api/stats", headers=self.headers).get_json()
        self.assertFalse(body["notion_breakdown_enabled"])

    def test_premium_notion_breakdown_active(self):
        _set_plan(self.user["id"], "premium")
        self._seed(n_history=5, n_series=5)
        body = self.client.get("/api/stats", headers=self.headers).get_json()
        self.assertTrue(body["notion_breakdown_enabled"])

    def test_ultra_notion_breakdown_active(self):
        _set_plan(self.user["id"], "ultra")
        self._seed(n_history=5, n_series=5)
        body = self.client.get("/api/stats", headers=self.headers).get_json()
        self.assertTrue(body["notion_breakdown_enabled"])

    def test_notion_breakdown_naffecte_pas_history(self):
        history, _ = self._seed(n_history=30, n_series=30)
        body = self.client.get("/api/stats", headers=self.headers).get_json()
        self.assertEqual(sorted(h["ts"] for h in body["history"]), sorted(h["ts"] for h in history))
        self.assertEqual(len(body["history"]), 30)


class TestNotionBreakdownEnabledOwnerTestPlan(DashboardStatsTestCase):
    def setUp(self):
        super().setUp()
        self._saved_owner_env = os.environ.get("NOVAMATH_OWNER_USER_ID")
        os.environ["NOVAMATH_OWNER_USER_ID"] = str(self.user["id"])

    def tearDown(self):
        owner_test_plan_service.set_test_plan(self.user, None)
        owner_test_plan_service.set_unlimited_quotas(self.user, True)
        if self._saved_owner_env is None:
            os.environ.pop("NOVAMATH_OWNER_USER_ID", None)
        else:
            os.environ["NOVAMATH_OWNER_USER_ID"] = self._saved_owner_env

    def test_owner_test_free_desactive(self):
        owner_test_plan_service.set_test_plan(self.user, "free")
        self._seed(n_history=5, n_series=5)
        body = self.client.get("/api/stats", headers=self.headers).get_json()
        self.assertFalse(body["notion_breakdown_enabled"])

    def test_owner_test_premium_active(self):
        owner_test_plan_service.set_test_plan(self.user, "premium")
        self._seed(n_history=5, n_series=5)
        body = self.client.get("/api/stats", headers=self.headers).get_json()
        self.assertTrue(body["notion_breakdown_enabled"])

    def test_owner_test_ultra_active(self):
        owner_test_plan_service.set_test_plan(self.user, "ultra")
        self._seed(n_history=5, n_series=5)
        body = self.client.get("/api/stats", headers=self.headers).get_json()
        self.assertTrue(body["notion_breakdown_enabled"])


if __name__ == "__main__":
    unittest.main()
