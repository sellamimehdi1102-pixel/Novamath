"""
Chantier "fiabilité mathématique — Phase B" (2026-10-17) : Knowledge/Search
Engine ne composent qu'une notion de cours déjà écrite (knowledge_response_
composer.py) — jamais un calcul, jamais une vérification d'une instance
concrète. L'audit a confirmé, par exécution réelle, que des demandes de
dérivée/limite/probabilité concrète/vérification de raisonnement/géométrie
appliquée étaient interceptées par ce gabarit, parfois même sur un chapitre
au score fort et "corroboré" (ex: "limite de 1/x en 0" matchait avec
confiance sur "Notion de limite d'une SUITE" — un score élevé ne garantit
pas la pertinence, voir intent_service.py/response_strategy.py).

Correction (deux mécanismes, tous deux réutilisant l'existant, aucune liste
de phrases par exemple) :
  - intent_service.CORRECTION_RE élargie (formulations naturelles de
    vérification : "est-ce juste/correct/bon/vrai", "ai-je bien fait...").
  - response_strategy._requires_real_computation : NONE_INTENT combiné à un
    verbe d'opération mathématique (même vocabulaire que math_engine.py,
    plus dérivée/limite/probabilité, jamais implémentées localement) ou à
    une formulation de vérification sur une donnée numérique concrète →
    jamais répondu par Knowledge/Search, quel que soit le score. Toute
    intention théorique déjà reconnue (DEFINITION/COURS/FICHE/EXEMPLE/
    METHODE/PROPRIETE/REFORMULATION/RESUME/DEMONSTRATION...) n'est JAMAIS
    concernée — seul NONE_INTENT l'est.
"""
import unittest

from chatbot.services import intent_service as ins
from chatbot.services import response_strategy as rs


def _student_context(class_level):
    return {
        "class_level": class_level, "chapitre_courant": None, "topic_courant": None,
        "dashboard": {}, "parametres": {},
    }


class _StrategyTestCase(unittest.TestCase):
    FAKE_USER = {"id": 1}

    def decide(self, message, class_level="seconde"):
        return rs.decide_strategy(
            message, self.FAKE_USER, chatbot_settings={}, student_context=_student_context(class_level),
            use_cache=False, class_level=class_level,
        )


class TestVerificationDuneReponse(_StrategyTestCase):
    """Vérifier une réponse d'élève à une équation — plusieurs formulations
    inédites, pas seulement celle de l'audit initial."""

    def test_formulation_1(self):
        strategy = self.decide("J'ai trouvé x = 7 pour 2x + 4 = 10, est-ce juste ?")
        self.assertEqual(strategy.intent, ins.CORRECTION)
        self.assertEqual(strategy.engine, rs.ENGINE_LLM)

    def test_formulation_2(self):
        strategy = self.decide("Pour résoudre x² - 9 = 0, j'ai trouvé x = 3 uniquement. C'est correct ?")
        self.assertEqual(strategy.intent, ins.CORRECTION)
        self.assertEqual(strategy.engine, rs.ENGINE_LLM)

    def test_formulation_3(self):
        strategy = self.decide("Ai-je bien fait de diviser les deux côtés par 2 dans 2x = 10 ?")
        self.assertEqual(strategy.intent, ins.CORRECTION)
        self.assertEqual(strategy.engine, rs.ENGINE_LLM)


class TestCalculDeDerivee(_StrategyTestCase):
    """Calculer une dérivée — plusieurs formulations, plusieurs classes."""

    def test_formulation_verbe_derive(self):
        strategy = self.decide("Dérive f(x) = x² + 3x.", class_level="premiere")
        self.assertEqual(strategy.engine, rs.ENGINE_LLM)

    def test_formulation_avec_fonction(self):
        strategy = self.decide("Dérive la fonction f(x) = x² + 3x", class_level="premiere")
        self.assertEqual(strategy.engine, rs.ENGINE_LLM)

    def test_formulation_question_verification(self):
        strategy = self.decide("La dérivée de x² est 2, est-ce correct ?", class_level="seconde")
        self.assertEqual(strategy.intent, ins.CORRECTION)
        self.assertEqual(strategy.engine, rs.ENGINE_LLM)


class TestLimiteFonctionVsSuite(_StrategyTestCase):
    """Étudier une limite — en distinguant fonction et suite, sans avoir
    besoin de regex spécifique à cette distinction : le verbe "limite" seul
    suffit à écarter Knowledge/Search, qui ne peut composer que sa SEULE
    notion indexée ("limite d'une suite", non pertinente pour une fonction)."""

    def test_limite_de_fonction(self):
        strategy = self.decide("Quelle est la limite de 1/x quand x tend vers 0 ?", class_level="premiere")
        self.assertEqual(strategy.engine, rs.ENGINE_LLM)

    def test_limite_de_suite_reste_aussi_envoyee_au_llm(self):
        """Non couvert localement non plus (aucune formule de limite dans
        math_engine) — cohérent : math_engine ne calcule aucune limite,
        suite ou fonction, et Knowledge/Search ne doit plus répondre par une
        simple définition à une demande de calcul."""
        strategy = self.decide("Quelle est la limite de la suite u_n = 1/n ?", class_level="premiere")
        self.assertEqual(strategy.engine, rs.ENGINE_LLM)


class TestProbabiliteConcrete(_StrategyTestCase):
    def test_probabilite_de_faces(self):
        strategy = self.decide("Probabilité d'obtenir 7 avec un dé à six faces ?")
        self.assertEqual(strategy.engine, rs.ENGINE_LLM)

    def test_probabilite_formulation_differente(self):
        strategy = self.decide("Quelle est la probabilité de tirer un as dans un jeu de 32 cartes ?")
        self.assertEqual(strategy.engine, rs.ENGINE_LLM)


class TestGeometrieAppliquee(_StrategyTestCase):
    def test_triangle_rectangle(self):
        strategy = self.decide("Triangle de côtés 3, 4 et 6 : est-il rectangle ?")
        self.assertEqual(strategy.engine, rs.ENGINE_LLM)

    def test_triangle_rectangle_formulation_differente(self):
        strategy = self.decide("Un triangle a des côtés de 5, 12 et 13 cm, est-ce un triangle rectangle ?")
        self.assertEqual(strategy.engine, rs.ENGINE_LLM)


class TestNonRegressionQuestionsTheoriques(_StrategyTestCase):
    """Ne jamais bloquer une question de cours/définition, même si elle
    contient une formule ou un exemple numérique — exigence explicite."""

    def test_explication_de_formule_sans_calcul_reste_locale(self):
        strategy = self.decide("Pourquoi (a+b)² = a² + 2ab + b² ?")
        self.assertIn(strategy.engine, (rs.ENGINE_KNOWLEDGE, rs.ENGINE_SEARCH))

    def test_definition_simple_reste_locale(self):
        strategy = self.decide("Qu'est-ce qu'une probabilité ?")
        self.assertEqual(strategy.intent, ins.DEFINITION)
        self.assertIn(strategy.engine, (rs.ENGINE_KNOWLEDGE, rs.ENGINE_SEARCH))

    def test_definition_fonction_affine_reste_locale(self):
        strategy = self.decide("Qu'est-ce qu'une fonction affine ?")
        self.assertIn(strategy.engine, (rs.ENGINE_KNOWLEDGE, rs.ENGINE_SEARCH))

    def test_propriete_avec_nombres_dans_lenonce_reste_locale(self):
        """Une propriété générale, même illustrée de nombres/symboles dans
        l'énoncé, n'est pas une demande de calcul."""
        strategy = self.decide("Donne-moi un exemple de fonction affine avec a=2 et b=3")
        self.assertIn(strategy.engine, (rs.ENGINE_KNOWLEDGE, rs.ENGINE_SEARCH))

    def test_formule_rappelee_sans_calcul_reste_locale(self):
        strategy = self.decide("Rappelle-moi la formule de la probabilité d'un événement")
        self.assertIn(strategy.engine, (rs.ENGINE_KNOWLEDGE, rs.ENGINE_SEARCH))

    def test_explication_discriminant_reste_locale(self):
        strategy = self.decide("Explique-moi la formule du discriminant", class_level="premiere")
        self.assertIn(strategy.engine, (rs.ENGINE_KNOWLEDGE, rs.ENGINE_SEARCH))


class TestNonRegressionIntentionsEtMoteursDejaCorriges(_StrategyTestCase):
    """Les corrections précédentes (INDICE/REVISION exclus de Knowledge/
    Search, Math Engine jamais pour INDICE ni pour une demande de détail,
    trigonométrie/division par zéro) restent intactes."""

    def test_revision_toujours_envoyee_au_llm(self):
        strategy = self.decide("J'ai 20 minutes pour réviser les probabilités. Organise-moi une révision efficace.")
        self.assertEqual(strategy.engine, rs.ENGINE_LLM)

    def test_indice_toujours_envoye_au_llm(self):
        strategy = self.decide("Aide-moi à résoudre x² - 5x + 6 = 0 sans me donner la réponse.")
        self.assertEqual(strategy.engine, rs.ENGINE_LLM)

    def test_resolution_simple_reste_locale_math_engine(self):
        strategy = self.decide("Résous x² - 5x + 6 = 0")
        self.assertEqual(strategy.engine, rs.ENGINE_MATH)

    def test_calcul_direct_reste_local(self):
        strategy = self.decide("Calcule 12 * 3 + 5")
        self.assertEqual(strategy.engine, rs.ENGINE_MATH)


if __name__ == "__main__":
    unittest.main()
