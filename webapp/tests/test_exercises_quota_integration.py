"""
Suite d'intégration du branchement quota_service.py sur la vraie route
d'entraînement (webapp/server.py::api_practice_load) — QuotaType.
EXERCISES_DAILY (Chantier "Limitation des exercices par abonnement",
2026-08-26) : Free=20/Premium=60/Ultra=illimité exercices classiques/jour.

Complète (sans le dupliquer) tests/test_quota_service.py, qui couvre déjà
exhaustivement consume()/can_consume()/concurrence au niveau du service pur —
ici on vérifie le CÂBLAGE : le format HTTP 429 exact, GET /api/quota, qu'un
exercice réellement chargé consomme exactement 1, qu'un exercice inconnu ou
une classe inconnue ne consomme rien, et que /api/exercise/<id> (route
publique, hors système d'entraînement) reste totalement inchangée.

Même convention que tests/test_chatbot_quota_integration.py : pas d'isolation
de base (server.app.test_client() contre la vraie data/novamath.db,
utilisateurs de test à email/username aléatoires).
"""
import random
import unittest
from datetime import datetime, timezone

import db
import server
from plan_service import Plan
from quota_service import QuotaType


def _today():
    return datetime.now(timezone.utc).date().isoformat()


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


def _used(client):
    return client.get("/api/quota").get_json()["exercises_daily"]["used"]


# Ids réels de la banque "seconde" (server.BANK_BY_ID), jamais inventés —
# suffisamment nombreux pour couvrir même la limite Premium (60) sans jamais
# recharger deux fois le même exercice dans un même test.
_REAL_IDS = list(server.BANK_BY_ID.keys())


class ExercisesQuotaTestCase(unittest.TestCase):
    def setUp(self):
        self.client = server.app.test_client()
        self.user, self.headers = _register(self.client)

    def _load(self, ex_id):
        return self.client.post(
            "/api/practice/load",
            json={"exercise_id": ex_id, "class_level": "seconde"},
            headers=self.headers,
        )


class TestChargementConsommeLeQuota(ExercisesQuotaTestCase):
    def test_un_exercice_reellement_charge_consomme_exactement_une_unite(self):
        resp = self._load(_REAL_IDS[0])
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(_used(self.client), 1)

    def test_deux_exercices_consomment_exactement_deux_unites(self):
        self._load(_REAL_IDS[0])
        self._load(_REAL_IDS[1])
        self.assertEqual(_used(self.client), 2)

    def test_exercice_inconnu_ne_consomme_rien(self):
        resp = self._load(-999999)
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(_used(self.client), 0)

    def test_classe_inconnue_ne_consomme_rien(self):
        resp = self.client.post(
            "/api/practice/load",
            json={"exercise_id": _REAL_IDS[0], "class_level": "inconnue"},
            headers=self.headers,
        )
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(_used(self.client), 0)


class TestFreeLimiteA20(ExercisesQuotaTestCase):
    def test_free_peut_charger_exactement_20_exercices(self):
        for ex_id in _REAL_IDS[:20]:
            resp = self._load(ex_id)
            self.assertEqual(resp.status_code, 200)
        self.assertEqual(_used(self.client), 20)

    def test_le_21e_est_refuse_avec_un_429(self):
        for ex_id in _REAL_IDS[:20]:
            self._load(ex_id)
        resp = self._load(_REAL_IDS[20])
        self.assertEqual(resp.status_code, 429)
        payload = resp.get_json()
        self.assertEqual(payload["error"], "quota_exceeded")
        self.assertEqual(payload["quota"], "exercises_daily")
        self.assertEqual(payload["limit"], 20)
        self.assertEqual(payload["required_plan"], "premium")

    def test_le_compteur_reste_a_20_apres_le_refus(self):
        for ex_id in _REAL_IDS[:20]:
            self._load(ex_id)
        self._load(_REAL_IDS[20])
        self.assertEqual(_used(self.client), 20)

    def test_le_21e_refuse_ne_renvoie_aucun_exercice(self):
        for ex_id in _REAL_IDS[:20]:
            self._load(ex_id)
        resp = self._load(_REAL_IDS[20])
        self.assertNotIn("exercise", resp.get_json())


class TestPremiumLimiteA60(ExercisesQuotaTestCase):
    def setUp(self):
        super().setUp()
        _set_plan(self.user["id"], Plan.PREMIUM)

    def test_premium_peut_charger_exactement_60_exercices(self):
        for ex_id in _REAL_IDS[:60]:
            resp = self._load(ex_id)
            self.assertEqual(resp.status_code, 200)
        self.assertEqual(_used(self.client), 60)

    def test_le_61e_est_refuse_avec_un_429(self):
        for ex_id in _REAL_IDS[:60]:
            self._load(ex_id)
        resp = self._load(_REAL_IDS[60])
        self.assertEqual(resp.status_code, 429)
        payload = resp.get_json()
        self.assertEqual(payload["limit"], 60)
        self.assertEqual(payload["required_plan"], "ultra")


class TestUltraIllimite(ExercisesQuotaTestCase):
    def setUp(self):
        super().setUp()
        _set_plan(self.user["id"], Plan.ULTRA)

    def test_ultra_peut_charger_plus_de_60_exercices(self):
        for ex_id in _REAL_IDS[:75]:
            resp = self._load(ex_id)
            self.assertEqual(resp.status_code, 200)
        self.assertEqual(_used(self.client), 75)

    def test_ultra_est_illimite_dans_get_quota(self):
        self._load(_REAL_IDS[0])
        snapshot = self.client.get("/api/quota").get_json()["exercises_daily"]
        self.assertTrue(snapshot["unlimited"])
        self.assertIsNone(snapshot["limit"])
        self.assertIsNone(snapshot["remaining"])


class TestGetQuotaExposeExercisesDaily(ExercisesQuotaTestCase):
    def test_quota_initial(self):
        snapshot = self.client.get("/api/quota").get_json()["exercises_daily"]
        self.assertEqual(snapshot, {"used": 0, "remaining": 20, "limit": 20, "unlimited": False})

    def test_quota_apres_consommation(self):
        self._load(_REAL_IDS[0])
        self._load(_REAL_IDS[1])
        self._load(_REAL_IDS[2])
        snapshot = self.client.get("/api/quota").get_json()["exercises_daily"]
        self.assertEqual(snapshot, {"used": 3, "remaining": 17, "limit": 20, "unlimited": False})


class TestNouveauJourReinitialiseLeCompteur(ExercisesQuotaTestCase):
    def test_hier_najoute_pas_a_aujourdhui(self):
        db.increment_daily_usage(self.user["id"], QuotaType.EXERCISES_DAILY.value, "2020-01-01", 20)
        resp = self._load(_REAL_IDS[0])
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(_used(self.client), 1)


class TestExerciceUniqueApiInchangee(ExercisesQuotaTestCase):
    """L'audit a montré que GET /api/exercise/<id> est public, hors système
    d'entraînement — ce chantier ne doit RIEN y changer : ni authentification,
    ni consommation de quota."""

    def test_reste_public_sans_authentification(self):
        anon_client = server.app.test_client()
        resp = anon_client.get(f"/api/exercise/{_REAL_IDS[0]}")
        self.assertEqual(resp.status_code, 200)

    def test_ne_consomme_aucun_quota(self):
        self.client.get(f"/api/exercise/{_REAL_IDS[0]}")
        self.assertEqual(_used(self.client), 0)


class TestQuotasChatbotEtLlmCallsInchanges(ExercisesQuotaTestCase):
    """Le nouveau quota exercices doit être totalement étanche : consommer
    des exercices ne doit jamais toucher CHAT_MESSAGES ni LLM_CALLS, et
    réciproquement (déjà couvert côté chatbot par
    test_chatbot_quota_integration.py, revérifié ici dans l'autre sens)."""

    def test_charger_des_exercices_ne_touche_pas_chat_messages(self):
        for ex_id in _REAL_IDS[:5]:
            self._load(ex_id)
        snapshot = self.client.get("/api/quota").get_json()
        self.assertEqual(snapshot["chat_messages"]["used"], 0)
        self.assertEqual(snapshot["llm_calls"]["used"], 0)

    def test_limites_chatbot_llm_calls_toujours_identiques(self):
        snapshot = self.client.get("/api/quota").get_json()
        self.assertEqual(snapshot["chat_messages"]["limit"], 15)
        self.assertTrue(snapshot["llm_calls"]["unlimited"])
        _set_plan(self.user["id"], Plan.PREMIUM)
        snapshot = self.client.get("/api/quota").get_json()
        self.assertEqual(snapshot["chat_messages"]["limit"], 25)
        self.assertEqual(snapshot["llm_calls"]["limit"], 20)
        _set_plan(self.user["id"], Plan.ULTRA)
        snapshot = self.client.get("/api/quota").get_json()
        self.assertEqual(snapshot["chat_messages"]["limit"], 40)
        self.assertEqual(snapshot["llm_calls"]["limit"], 40)


if __name__ == "__main__":
    unittest.main()
