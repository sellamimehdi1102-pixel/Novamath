"""
Suite du filtrage de contenu pédagogique par plan (Chantier "Répartition du
contenu des cours par plan", 2026-08-26) : webapp/course_content_service.py
(filtrage pur) et webapp/server.py::api_course_content (câblage HTTP réel).

Deux niveaux, comme le reste du projet (voir test_quota_service.py +
test_chatbot_quota_integration.py) :
- TestFilterNotion* : filter_notion() en isolation, sans DB ni HTTP.
- TestApiCourseContent* : la vraie route, server.app.test_client(), pour
  vérifier le câblage (401/404, format JSON réel, Owner, non-régression du
  chatbot/quotas/prix — hors de portée de ce fichier mais confirmée ne pas
  avoir bougé par les suites dédiées).
"""
import os
import random
import unittest

import curriculum_registry
import db
import owner_test_plan_service
import server
from course_content_service import filter_notion
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


def _set_plan(user_id, plan_value):
    db.set_stripe_subscription(user_id, "sub_test", plan_value, "active")


_RICH_NOTION = {
    "id": "notion-riche",
    "title": "Notion riche",
    "intro": "Intro",
    "objectif": "Objectif",
    "definition": "Définition",
    "reglesImportantes": ["Règle 1", "Règle 2"],
    "formules": [{"expression": "F1"}, {"expression": "F2"}, {"expression": "F3"}],
    "methode": {
        "etapes": [{"texte": "Étape normale"}],
        "etapesParNiveau": {
            "debutant": [{"texte": "Étape débutant"}],
            "normal": [{"texte": "Étape normale"}],
            "rapide": [{"texte": "Étape rapide"}],
        },
    },
    "exemples": [{"enonce": "Exemple 1"}, {"enonce": "Exemple 2"}, {"enonce": "Exemple 3"}],
    "erreursFrequentes": ["Erreur 1"],
    "erreursFrequentesDetail": [{"pourquoi": "..."}],
    "astuce": "Astuce",
    "explicationSimple": "Explication simple",
    "intuition": "Intuition",
    "exemplesConcrets": ["Concret 1"],
    "aRetenir": ["Point 1", "Point 2"],
    "demonstration": {"titre": "Pourquoi ?", "etapes": [{"texte": "..."}], "conclusion": "..."},
    "figure": {"kind": "geom", "viewBox": [0, 0, 1, 1]},
    "quizExerciseIds": [1, 2],
}

_MINIMAL_NOTION = {
    "id": "notion-minimale",
    "title": "Notion minimale",
    "intro": "Intro",
    "definition": "Définition",
    "reglesImportantes": ["Règle unique"],
    "exemples": [{"enonce": "Seul exemple"}],
    "quizExerciseIds": [1],
    # Pas de formules, pas de methode, pas de figure, pas de demonstration,
    # pas de champs Premium+ — représente une notion "pauvre" comme
    # racine-carree avant l'audit.
}


class TestFilterNotionFree(unittest.TestCase):
    def setUp(self):
        self.result = filter_notion(_RICH_NOTION, Plan.FREE)

    def test_recoit_le_contenu_essentiel(self):
        for field in ("intro", "objectif", "definition", "reglesImportantes", "astuce", "figure", "quizExerciseIds"):
            with self.subTest(field=field):
                self.assertEqual(self.result[field], _RICH_NOTION[field])

    def test_recoit_exactement_le_premier_exemple(self):
        self.assertEqual(self.result["exemples"], [_RICH_NOTION["exemples"][0]])

    def test_recoit_exactement_la_premiere_formule(self):
        self.assertEqual(self.result["formules"], [_RICH_NOTION["formules"][0]])

    def test_recoit_le_profil_methode_normal(self):
        self.assertEqual(self.result["methode"]["etapesParNiveau"]["normal"], _RICH_NOTION["methode"]["etapesParNiveau"]["normal"])

    def test_ne_recoit_aucun_contenu_premium(self):
        self.assertNotIn("explicationSimple", self.result)
        self.assertNotIn("intuition", self.result)
        self.assertNotIn("exemplesConcrets", self.result)
        self.assertNotIn("erreursFrequentesDetail", self.result)
        self.assertNotIn("aRetenir", self.result)
        self.assertEqual(self.result["methode"]["etapesParNiveau"]["debutant"], [])
        self.assertEqual(self.result["methode"]["etapesParNiveau"]["rapide"], [])

    def test_ne_recoit_aucun_contenu_ultra(self):
        self.assertNotIn("demonstration", self.result)

    def test_locked_content_signale_premium_et_ultra(self):
        locked = self.result["locked_content"]
        self.assertTrue(locked["premium"])
        self.assertEqual(locked["premium_extra_examples"], 2)
        self.assertEqual(locked["premium_extra_formulas"], 2)
        self.assertTrue(locked["ultra"])


class TestFilterNotionPremium(unittest.TestCase):
    def setUp(self):
        self.result = filter_notion(_RICH_NOTION, Plan.PREMIUM)

    def test_recoit_le_contenu_free(self):
        self.assertEqual(self.result["definition"], _RICH_NOTION["definition"])
        self.assertEqual(self.result["reglesImportantes"], _RICH_NOTION["reglesImportantes"])

    def test_recoit_le_contenu_premium(self):
        self.assertEqual(self.result["exemples"], _RICH_NOTION["exemples"])
        self.assertEqual(self.result["formules"], _RICH_NOTION["formules"])
        self.assertEqual(self.result["explicationSimple"], _RICH_NOTION["explicationSimple"])
        self.assertEqual(self.result["intuition"], _RICH_NOTION["intuition"])
        self.assertEqual(self.result["exemplesConcrets"], _RICH_NOTION["exemplesConcrets"])
        self.assertEqual(self.result["erreursFrequentesDetail"], _RICH_NOTION["erreursFrequentesDetail"])
        self.assertEqual(self.result["aRetenir"], _RICH_NOTION["aRetenir"])
        self.assertEqual(self.result["methode"]["etapesParNiveau"]["debutant"], _RICH_NOTION["methode"]["etapesParNiveau"]["debutant"])
        self.assertEqual(self.result["methode"]["etapesParNiveau"]["rapide"], _RICH_NOTION["methode"]["etapesParNiveau"]["rapide"])

    def test_ne_recoit_aucun_contenu_ultra(self):
        self.assertNotIn("demonstration", self.result)

    def test_locked_content_signale_uniquement_ultra(self):
        locked = self.result["locked_content"]
        self.assertFalse(locked["premium"])
        self.assertEqual(locked["premium_extra_examples"], 0)
        self.assertTrue(locked["ultra"])


class TestFilterNotionUltra(unittest.TestCase):
    def setUp(self):
        self.result = filter_notion(_RICH_NOTION, Plan.ULTRA)

    def test_recoit_absolument_tout(self):
        for field in ("exemples", "formules", "explicationSimple", "intuition", "exemplesConcrets", "erreursFrequentesDetail", "aRetenir", "demonstration"):
            with self.subTest(field=field):
                self.assertEqual(self.result[field], _RICH_NOTION[field])

    def test_locked_content_ne_signale_rien(self):
        locked = self.result["locked_content"]
        self.assertFalse(locked["premium"])
        self.assertFalse(locked["ultra"])


class TestFilterNotionContenuManquant(unittest.TestCase):
    """§5 du chantier : un champ absent ne doit provoquer aucune erreur, et le
    comportement doit rester identique à aujourd'hui (rien à retirer =
    aucune trace de filtrage)."""

    def test_notion_sans_demonstration_fonctionne(self):
        result = filter_notion(_MINIMAL_NOTION, Plan.FREE)
        self.assertNotIn("demonstration", result)
        self.assertFalse(result["locked_content"]["ultra"])  # rien à débloquer, pas de fausse promesse

    def test_notion_sans_exemples_supplementaires_fonctionne(self):
        result = filter_notion(_MINIMAL_NOTION, Plan.FREE)
        self.assertEqual(result["exemples"], _MINIMAL_NOTION["exemples"])
        self.assertEqual(result["locked_content"]["premium_extra_examples"], 0)
        self.assertFalse(result["locked_content"]["premium"])

    def test_figure_absente_ne_plante_pas(self):
        result = filter_notion(_MINIMAL_NOTION, Plan.FREE)
        self.assertNotIn("figure", result)

    def test_methode_absente_ne_plante_pas(self):
        result = filter_notion(_MINIMAL_NOTION, Plan.PREMIUM)
        self.assertNotIn("methode", result)


class TestFilterNotionFigureResteFree(unittest.TestCase):
    def test_figure_toujours_presente_meme_en_free(self):
        result = filter_notion(_RICH_NOTION, Plan.FREE)
        self.assertEqual(result["figure"], _RICH_NOTION["figure"])


class ApiCourseContentTestCase(unittest.TestCase):
    def setUp(self):
        self.client = server.app.test_client()
        self.user, self.headers = _register(self.client)


class TestApiCourseContentAuth(ApiCourseContentTestCase):
    def test_non_connecte_ne_recoit_rien(self):
        anon = server.app.test_client()
        resp = anon.get("/api/course-content/seconde/Chapitre_1")
        self.assertEqual(resp.status_code, 401)
        self.assertNotIn("notions", resp.get_json() or {})

    def test_chapitre_inconnu_404(self):
        resp = self.client.get("/api/course-content/seconde/Chapitre_9999", headers=self.headers)
        self.assertEqual(resp.status_code, 404)

    def test_classe_inconnue_404(self):
        resp = self.client.get("/api/course-content/inconnue/Chapitre_1", headers=self.headers)
        self.assertEqual(resp.status_code, 404)

    def test_tentative_de_traversee_de_chemin_404(self):
        resp = self.client.get("/api/course-content/seconde/..%2f..%2fnovamath", headers=self.headers)
        self.assertIn(resp.status_code, (404, 400))


class TestApiCourseContentParPlan(ApiCourseContentTestCase):
    def test_free_recoit_le_contenu_essentiel_uniquement(self):
        resp = self.client.get("/api/course-content/seconde/Chapitre_1", headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        notion = resp.get_json()["notions"][0]
        self.assertNotIn("aRetenir", notion)
        self.assertNotIn("demonstration", notion)
        self.assertLessEqual(len(notion["exemples"]), 1)

    def test_premium_recoit_free_plus_premium(self):
        _set_plan(self.user["id"], "premium")
        resp = self.client.get("/api/course-content/seconde/Chapitre_1", headers=self.headers)
        notion = resp.get_json()["notions"][0]
        self.assertIn("aRetenir", notion)
        self.assertNotIn("demonstration", notion)

    def test_ultra_recoit_tout(self):
        _set_plan(self.user["id"], "ultra")
        resp = self.client.get("/api/course-content/premiere/Chapitre_3", headers=self.headers)
        notion = next(n for n in resp.get_json()["notions"] if n["id"] == "fonction-derivee")
        self.assertIn("demonstration", notion)
        self.assertFalse(notion["locked_content"]["premium"])
        self.assertFalse(notion["locked_content"]["ultra"])


class TestApiCourseContentOwner(ApiCourseContentTestCase):
    """Même mécanisme générique que quota_service (owner_test_plan_service.
    effective_plan) — aucune branche spéciale ajoutée pour les cours."""

    def setUp(self):
        super().setUp()
        self._saved_owner_env = os.environ.get("NOVAMATH_OWNER_USER_ID")
        os.environ["NOVAMATH_OWNER_USER_ID"] = str(self.user["id"])

    def tearDown(self):
        # owner_test_plan_service persiste dans system_settings (table
        # GLOBALE, pas de DB isolée dans cette suite — voir server.app.test_client()
        # ci-dessus) : sans ce nettoyage, un plan de test/quotas laissés actifs
        # ici POLLUERAIENT tous les tests suivants qui touchent un compte
        # owner, y compris dans d'autres fichiers exécutés dans la même
        # session pytest. Effectué AVANT de restaurer la variable
        # d'environnement, tant que self.user est encore reconnu comme owner.
        owner_test_plan_service.set_test_plan(self.user, None)
        owner_test_plan_service.set_unlimited_quotas(self.user, True)
        if self._saved_owner_env is None:
            os.environ.pop("NOVAMATH_OWNER_USER_ID", None)
        else:
            os.environ["NOVAMATH_OWNER_USER_ID"] = self._saved_owner_env

    def test_owner_sans_test_actif_recoit_tout(self):
        resp = self.client.get("/api/course-content/premiere/Chapitre_3", headers=self.headers)
        notion = next(n for n in resp.get_json()["notions"] if n["id"] == "fonction-derivee")
        self.assertIn("demonstration", notion)

    def test_owner_test_free_recoit_le_contenu_free(self):
        owner_test_plan_service.set_test_plan(self.user, "free")
        owner_test_plan_service.set_unlimited_quotas(self.user, False)
        resp = self.client.get("/api/course-content/seconde/Chapitre_1", headers=self.headers)
        notion = resp.get_json()["notions"][0]
        self.assertNotIn("aRetenir", notion)

    def test_owner_test_ultra_recoit_tout(self):
        owner_test_plan_service.set_test_plan(self.user, "ultra")
        owner_test_plan_service.set_unlimited_quotas(self.user, False)
        resp = self.client.get("/api/course-content/premiere/Chapitre_3", headers=self.headers)
        notion = next(n for n in resp.get_json()["notions"] if n["id"] == "fonction-derivee")
        self.assertIn("demonstration", notion)


class TestApiCourseContentCompatibilite(ApiCourseContentTestCase):
    def test_37_chapitres_se_chargent_pour_les_trois_plans(self):
        checked = 0
        for plan in (None, "premium", "ultra"):
            if plan:
                _set_plan(self.user["id"], plan)
            for class_level, profile in curriculum_registry.CURRICULUM_REGISTRY.items():
                for path in sorted(profile.courses_dir.glob("chapitre_*.json")):
                    num = path.stem.split("_")[1]
                    resp = self.client.get(f"/api/course-content/{class_level}/Chapitre_{num}", headers=self.headers)
                    self.assertEqual(resp.status_code, 200, f"{class_level}/Chapitre_{num} (plan={plan})")
                    checked += 1
        self.assertEqual(checked, 37 * 3)

    def test_une_figure_reste_accessible_en_free(self):
        """§10 du chantier : les figures restent Free par défaut, jamais
        retirées automatiquement — revérifié en HTTP réel (déjà couvert
        unitairement par TestFilterNotionFigureResteFree)."""
        resp = self.client.get("/api/course-content/seconde/Chapitre_7", headers=self.headers)
        notions = resp.get_json()["notions"]
        has_any_figure = any(n.get("figure") for n in notions)
        self.assertTrue(has_any_figure, "aucune figure trouvée dans Chapitre_7 — le test lui-même serait un faux négatif")


if __name__ == "__main__":
    unittest.main()
