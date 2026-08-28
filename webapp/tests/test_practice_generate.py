"""
Suite du chantier "Différenciateurs Premium/Ultra — Génération d'exercices
sur mesure" (2026-08-27) : POST /api/practice/generate et
GET /api/practice/generate/options réutilisent le moteur symbolique
existant (exercise_generator/, voir registry.py) — aucun appel LLM, aucune
écriture dans la banque commune (_class_bank), Feature.CUSTOM_EXERCISES
(déjà Ultra-only dans FEATURE_MATRIX) réutilisée telle quelle, aucune
nouvelle Feature.

QuotaType.CUSTOM_EXERCISES volontairement PAS consommé (décision validée
explicitement, voir server.py::api_practice_generate) — un test ci-dessous
le vérifie noir sur blanc plutôt que de le supposer.
"""
import os
import random
import unittest

import db
import owner_test_plan_service
import server


def _register(client):
    email = f"gen{random.randint(1_000_000, 9_999_999)}@gmail.com"
    username = f"gen{random.randint(100_000, 999_999)}"
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


VALID_BODY = {
    "class_level": "premiere",
    "chapter_id": "Chapitre_2",
    "notion": "Équations du second degré",
    "family_id": "resolution",
}


class PracticeGenerateTestCase(unittest.TestCase):
    def setUp(self):
        self.client = server.app.test_client()
        self.user, self.headers = _register(self.client)


class TestFeatureGatingParPlan(PracticeGenerateTestCase):
    def test_free_recoit_403(self):
        resp = self.client.post("/api/practice/generate", json=VALID_BODY, headers=self.headers)
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.get_json()["error"], "premium_required")

    def test_free_options_recoit_403(self):
        resp = self.client.get("/api/practice/generate/options", headers=self.headers)
        self.assertEqual(resp.status_code, 403)

    def test_premium_recoit_403(self):
        _set_plan(self.user["id"], "premium")
        resp = self.client.post("/api/practice/generate", json=VALID_BODY, headers=self.headers)
        self.assertEqual(resp.status_code, 403)

    def test_ultra_recoit_200(self):
        _set_plan(self.user["id"], "ultra")
        resp = self.client.post("/api/practice/generate", json=VALID_BODY, headers=self.headers)
        self.assertEqual(resp.status_code, 200)

    def test_403_indique_required_plan_ultra(self):
        resp = self.client.post("/api/practice/generate", json=VALID_BODY, headers=self.headers)
        self.assertEqual(resp.get_json()["required_plan"], "ultra")


class TestOwnerTestPlan(PracticeGenerateTestCase):
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

    def test_owner_test_free_recoit_403(self):
        owner_test_plan_service.set_test_plan(self.user, "free")
        resp = self.client.post("/api/practice/generate", json=VALID_BODY, headers=self.headers)
        self.assertEqual(resp.status_code, 403)

    def test_owner_test_premium_recoit_403(self):
        owner_test_plan_service.set_test_plan(self.user, "premium")
        resp = self.client.post("/api/practice/generate", json=VALID_BODY, headers=self.headers)
        self.assertEqual(resp.status_code, 403)

    def test_owner_test_ultra_recoit_200(self):
        owner_test_plan_service.set_test_plan(self.user, "ultra")
        resp = self.client.post("/api/practice/generate", json=VALID_BODY, headers=self.headers)
        self.assertEqual(resp.status_code, 200)


class TestFormatExercice(PracticeGenerateTestCase):
    def setUp(self):
        super().setUp()
        _set_plan(self.user["id"], "ultra")

    def test_champs_compatibles_avec_public_exercise(self):
        resp = self.client.post("/api/practice/generate", json=VALID_BODY, headers=self.headers)
        ex = resp.get_json()["exercise"]
        for field in ("id", "chapter_id", "notion", "difficulty", "enonce", "hint", "answer", "solution_steps"):
            self.assertIn(field, ex)

    def test_source_vaut_generated(self):
        resp = self.client.post("/api/practice/generate", json=VALID_BODY, headers=self.headers)
        self.assertEqual(resp.get_json()["exercise"]["source"], "generated")

    def test_chapter_id_et_notion_correspondent_a_la_demande(self):
        resp = self.client.post("/api/practice/generate", json=VALID_BODY, headers=self.headers)
        ex = resp.get_json()["exercise"]
        self.assertEqual(ex["chapter_id"], VALID_BODY["chapter_id"])
        self.assertEqual(ex["notion"], VALID_BODY["notion"])

    def test_id_est_distinct_de_la_banque_classique(self):
        resp = self.client.post("/api/practice/generate", json=VALID_BODY, headers=self.headers)
        ex = resp.get_json()["exercise"]
        self.assertTrue(str(ex["id"]).startswith("generated:"))

    def test_deux_appels_successifs_donnent_des_ids_distincts(self):
        r1 = self.client.post("/api/practice/generate", json=VALID_BODY, headers=self.headers).get_json()
        r2 = self.client.post("/api/practice/generate", json=VALID_BODY, headers=self.headers).get_json()
        self.assertNotEqual(r1["exercise"]["id"], r2["exercise"]["id"])


class TestValidationEntree(PracticeGenerateTestCase):
    def setUp(self):
        super().setUp()
        _set_plan(self.user["id"], "ultra")

    def test_champ_manquant_400(self):
        resp = self.client.post("/api/practice/generate", json={"family_id": "resolution"}, headers=self.headers)
        self.assertEqual(resp.status_code, 400)

    def test_family_id_inconnu_404(self):
        body = {**VALID_BODY, "family_id": "famille_qui_nexiste_pas"}
        resp = self.client.post("/api/practice/generate", json=body, headers=self.headers)
        self.assertEqual(resp.status_code, 404)

    def test_family_id_reel_mais_mauvaise_notion_404(self):
        # "resolution" existe bien, mais pas sous cette notion/chapitre —
        # vérifie que la résolution est bien scoping-stricte (voir
        # exercise_generator/registry.py, family_id seul est ambigu :
        # "resolution" existe aussi dans equation_premier_degre, Troisième).
        body = {**VALID_BODY, "notion": "Notion inexistante"}
        resp = self.client.post("/api/practice/generate", json=body, headers=self.headers)
        self.assertEqual(resp.status_code, 404)

    def test_class_level_inconnue_404(self):
        body = {**VALID_BODY, "class_level": "terminale"}
        resp = self.client.post("/api/practice/generate", json=body, headers=self.headers)
        self.assertEqual(resp.status_code, 404)


class TestOptionsListeReelle(PracticeGenerateTestCase):
    def setUp(self):
        super().setUp()
        _set_plan(self.user["id"], "ultra")

    def test_contient_au_moins_les_3_classes_avec_generateur(self):
        resp = self.client.get("/api/practice/generate/options", headers=self.headers)
        levels = {n["class_level"] for n in resp.get_json()["notions"]}
        self.assertEqual(levels, {"troisieme", "seconde", "premiere"})

    def test_chaque_notion_a_au_moins_une_famille(self):
        resp = self.client.get("/api/practice/generate/options", headers=self.headers)
        for n in resp.get_json()["notions"]:
            self.assertGreater(len(n["families"]), 0)

    def test_une_notion_de_la_liste_est_generable_via_generate(self):
        resp = self.client.get("/api/practice/generate/options", headers=self.headers)
        notion_entry = next(n for n in resp.get_json()["notions"] if n["class_level"] == "premiere")
        body = {
            "class_level": notion_entry["class_level"],
            "chapter_id": notion_entry["chapter_id"],
            "notion": notion_entry["notion"],
            "family_id": notion_entry["families"][0]["family_id"],
        }
        resp2 = self.client.post("/api/practice/generate", json=body, headers=self.headers)
        self.assertEqual(resp2.status_code, 200)


class TestQuotaCustomExercisesNonConsomme(PracticeGenerateTestCase):
    """Décision produit validée explicitement (2026-08-27) : Feature.
    CUSTOM_EXERCISES bloque déjà Free/Premium avant tout quota, et
    QUOTA_MATRIX[ULTRA][CUSTOM_EXERCISES] est illimité — consommer n'aurait
    aucun effet pratique. Ce test vérifie que ce choix est bien respecté par
    le code, pas seulement documenté en commentaire."""

    def test_usage_custom_exercises_reste_a_zero_apres_generation(self):
        _set_plan(self.user["id"], "ultra")
        for _ in range(3):
            self.client.post("/api/practice/generate", json=VALID_BODY, headers=self.headers)
        quota = self.client.get("/api/quota", headers=self.headers).get_json()
        self.assertEqual(quota["custom_exercises"]["used"], 0)


if __name__ == "__main__":
    unittest.main()
