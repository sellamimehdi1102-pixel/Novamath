"""
Suite du service de Feature Flags (webapp/plan_service.py) — source unique de
vérité des droits utilisateur. Couvre les 3 plans (FREE/PREMIUM/ULTRA), toutes
les features de la matrice, get_plan()/has_feature()/list_features(),
minimal_plan_for_feature(), et le décorateur requires_feature testé de façon
isolée sur une mini-app Flask ad-hoc (indépendante de server.py).

Le branchement réel de @requires_feature sur les routes de server.py — et le
comportement 403/redirection qui en découle pour FREE/PREMIUM/ULTRA — est
couvert par tests/test_server_feature_gating.py, en complément de ce fichier.
"""
import unittest

from flask import Flask

from plan_service import (
    FEATURE_MATRIX, Feature, Plan, get_plan, has_feature, is_free, is_premium,
    is_ultra, list_features, minimal_plan_for_feature, requires_feature,
)


def _user(plan_value):
    return {"id": 1, "plan": plan_value}


class TestPlanEnum(unittest.TestCase):
    def test_valeurs_brutes(self):
        self.assertEqual(Plan.FREE.value, "free")
        self.assertEqual(Plan.PREMIUM.value, "premium")
        self.assertEqual(Plan.ULTRA.value, "ultra")

    def test_from_value_reconnait_les_trois_plans(self):
        self.assertIs(Plan.from_value("free"), Plan.FREE)
        self.assertIs(Plan.from_value("premium"), Plan.PREMIUM)
        self.assertIs(Plan.from_value("ultra"), Plan.ULTRA)

    def test_from_value_degrade_vers_free_sur_valeur_inconnue(self):
        self.assertIs(Plan.from_value("gold"), Plan.FREE)
        self.assertIs(Plan.from_value(None), Plan.FREE)
        self.assertIs(Plan.from_value(""), Plan.FREE)

    def test_parse_est_strict(self):
        self.assertIs(Plan.parse("premium"), Plan.PREMIUM)
        self.assertIsNone(Plan.parse("gold"))
        self.assertIsNone(Plan.parse(None))
        self.assertIsNone(Plan.parse(""))


class TestGetPlan(unittest.TestCase):
    def test_lit_le_plan_de_lutilisateur(self):
        self.assertIs(get_plan(_user("free")), Plan.FREE)
        self.assertIs(get_plan(_user("premium")), Plan.PREMIUM)
        self.assertIs(get_plan(_user("ultra")), Plan.ULTRA)

    def test_utilisateur_none_est_free(self):
        self.assertIs(get_plan(None), Plan.FREE)

    def test_utilisateur_sans_champ_plan_est_free(self):
        self.assertIs(get_plan({"id": 1}), Plan.FREE)

    def test_valeur_corrompue_degrade_vers_free(self):
        self.assertIs(get_plan(_user("not_a_real_plan")), Plan.FREE)


class TestIsPlanHelpers(unittest.TestCase):
    def test_is_free(self):
        self.assertTrue(is_free(_user("free")))
        self.assertFalse(is_free(_user("premium")))
        self.assertFalse(is_free(_user("ultra")))

    def test_is_premium(self):
        self.assertFalse(is_premium(_user("free")))
        self.assertTrue(is_premium(_user("premium")))
        self.assertFalse(is_premium(_user("ultra")))

    def test_is_ultra(self):
        self.assertFalse(is_ultra(_user("free")))
        self.assertFalse(is_ultra(_user("premium")))
        self.assertTrue(is_ultra(_user("ultra")))


class TestListFeatures(unittest.TestCase):
    def test_free_features(self):
        features = list_features(Plan.FREE)
        for expected in (Feature.COURSES, Feature.EXERCISES, Feature.STATISTICS,
                          Feature.HISTORY, Feature.GOALS, Feature.CHATBOT, Feature.EXPORT):
            self.assertIn(expected, features)
        for forbidden in (Feature.CHATBOT_UNLIMITED, Feature.ADVANCED_AI,
                           Feature.ADVANCED_EXPLANATIONS, Feature.PROFILE_ANALYTICS,
                           Feature.EARLY_ACCESS, Feature.PRIORITY_QUEUE,
                           Feature.PRIORITY_SUPPORT, Feature.LONG_RESPONSES,
                           Feature.CUSTOM_EXERCISES):
            self.assertNotIn(forbidden, features)

    def test_premium_inclut_tout_free_plus_ses_propres_features(self):
        free_features = list_features(Plan.FREE)
        premium_features = list_features(Plan.PREMIUM)
        self.assertTrue(free_features.issubset(premium_features))
        for expected in (Feature.CHATBOT_UNLIMITED, Feature.ADVANCED_EXPLANATIONS,
                          Feature.PROFILE_ANALYTICS, Feature.PRIORITY_SUPPORT):
            self.assertIn(expected, premium_features)
        for forbidden in (Feature.ADVANCED_AI, Feature.EARLY_ACCESS,
                           Feature.PRIORITY_QUEUE, Feature.LONG_RESPONSES,
                           Feature.CUSTOM_EXERCISES):
            self.assertNotIn(forbidden, premium_features)

    def test_ultra_inclut_tout_premium_plus_ses_propres_features(self):
        premium_features = list_features(Plan.PREMIUM)
        ultra_features = list_features(Plan.ULTRA)
        self.assertTrue(premium_features.issubset(ultra_features))
        for expected in (Feature.ADVANCED_AI, Feature.CUSTOM_EXERCISES,
                          Feature.EARLY_ACCESS, Feature.PRIORITY_QUEUE, Feature.LONG_RESPONSES):
            self.assertIn(expected, ultra_features)

    def test_ultra_a_toutes_les_features_du_projet(self):
        all_features = set(Feature)
        self.assertEqual(list_features(Plan.ULTRA), all_features)

    def test_feature_matrix_couvre_les_trois_plans(self):
        self.assertEqual(set(FEATURE_MATRIX.keys()), {Plan.FREE, Plan.PREMIUM, Plan.ULTRA})


class TestHasFeature(unittest.TestCase):
    def test_free_na_pas_les_features_premium(self):
        user = _user("free")
        self.assertTrue(has_feature(user, Feature.CHATBOT))
        self.assertFalse(has_feature(user, Feature.CHATBOT_UNLIMITED))
        self.assertFalse(has_feature(user, Feature.ADVANCED_AI))

    def test_premium_a_ses_features_mais_pas_ultra(self):
        user = _user("premium")
        self.assertTrue(has_feature(user, Feature.CHATBOT_UNLIMITED))
        self.assertTrue(has_feature(user, Feature.PROFILE_ANALYTICS))
        self.assertFalse(has_feature(user, Feature.ADVANCED_AI))
        self.assertFalse(has_feature(user, Feature.EARLY_ACCESS))

    def test_ultra_a_absolument_tout(self):
        user = _user("ultra")
        for feature in Feature:
            self.assertTrue(has_feature(user, feature))

    def test_utilisateur_none_na_aucune_feature_premium(self):
        self.assertFalse(has_feature(None, Feature.CHATBOT_UNLIMITED))
        self.assertTrue(has_feature(None, Feature.CHATBOT))


class TestMinimalPlanForFeature(unittest.TestCase):
    def test_feature_free_renvoie_free(self):
        self.assertIs(minimal_plan_for_feature(Feature.CHATBOT), Plan.FREE)
        self.assertIs(minimal_plan_for_feature(Feature.STATISTICS), Plan.FREE)

    def test_feature_premium_renvoie_premium(self):
        self.assertIs(minimal_plan_for_feature(Feature.CHATBOT_UNLIMITED), Plan.PREMIUM)
        self.assertIs(minimal_plan_for_feature(Feature.PROFILE_ANALYTICS), Plan.PREMIUM)

    def test_feature_ultra_renvoie_ultra(self):
        self.assertIs(minimal_plan_for_feature(Feature.ADVANCED_AI), Plan.ULTRA)
        self.assertIs(minimal_plan_for_feature(Feature.EARLY_ACCESS), Plan.ULTRA)

    def test_coherent_avec_has_feature_pour_toutes_les_features(self):
        """Le plan minimal renvoyé doit toujours réellement débloquer la
        feature, et le palier juste en dessous ne jamais la débloquer."""
        order = [Plan.FREE, Plan.PREMIUM, Plan.ULTRA]
        for feature in Feature:
            with self.subTest(feature=feature):
                minimal = minimal_plan_for_feature(feature)
                self.assertIn(feature, FEATURE_MATRIX[minimal])
                idx = order.index(minimal)
                if idx > 0:
                    self.assertNotIn(feature, FEATURE_MATRIX[order[idx - 1]])


class TestRequiresFeature(unittest.TestCase):
    """Branché réellement sur les routes de server.py (voir
    tests/test_server_feature_gating.py) — vérifié ici de façon isolée sur une
    mini-app Flask ad-hoc, indépendante du serveur réel."""

    def setUp(self):
        app = Flask(__name__)

        @app.route("/only-premium")
        @requires_feature(Feature.CHATBOT_UNLIMITED)
        def only_premium():
            return {"ok": True}

        self.client = app.test_client()
        self.app = app

    def _call_as(self, plan_value):
        with self.app.test_request_context("/only-premium"):
            from flask import request
            request.current_user = _user(plan_value) if plan_value else None
            view = self.app.view_functions["only_premium"]
            return view()

    def test_bloque_free(self):
        result = self._call_as("free")
        body, status = result
        self.assertEqual(status, 403)
        payload = body.get_json()
        self.assertEqual(payload, {
            "error": "premium_required",
            "feature": "chatbot_unlimited",
            "required_plan": "premium",
        })

    def test_autorise_premium(self):
        result = self._call_as("premium")
        self.assertEqual(result, {"ok": True})

    def test_autorise_ultra(self):
        result = self._call_as("ultra")
        self.assertEqual(result, {"ok": True})

    def test_bloque_utilisateur_non_connecte(self):
        result = self._call_as(None)
        body, status = result
        self.assertEqual(status, 403)


if __name__ == "__main__":
    unittest.main()
