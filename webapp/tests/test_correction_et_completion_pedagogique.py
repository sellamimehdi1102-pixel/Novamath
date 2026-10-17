"""
Chantier "correction finale des consignes pédagogiques" (2026-10-17) :
diagnostic confirmé sur 2 cas réels (tests manuels) —

1. "J'ai trouvé x = 7 pour 2x + 4 = 10, est-ce correct ?" : l'ancienne
   instruction de l'intention CORRECTION ("corrige pas à pas... sans donner
   d'emblée la solution complète s'il n'a pas encore réessayé") était écrite
   pour un seul cas (l'élève ne sait pas s'il a une erreur) et s'appliquait
   à tort à une vérification explicite d'une réponse déjà trouvée — le
   chatbot disait que c'était faux sans jamais donner la bonne réponse.

2. "Un triangle de côtés 3/4/6 cm est-il rectangle ? Justifie." (NONE_INTENT) :
   aucune instruction n'imposait d'aller jusqu'à la conclusion — le chatbot
   s'arrêtait en cours de calcul pour demander l'autorisation de continuer,
   sans qu'aucune règle ne l'en empêche ni ne l'y oblige.

Correction : instruction CORRECTION réécrite en une seule instruction
générale couvrant les 3 situations réelles (vérification d'une réponse
proposée / correction complète sans réponse propre / indice ou réessai
respecté) — voir pedagogy_templates.py. Et clause positive
_COMPLETION_CLAUSE ajoutée à _DIRECT_METHOD_INSTRUCTION (prompt_builder.py),
exclue pour INDICE (voir _NO_COMPLETION_INTENTS) qui demande explicitement
de ne pas recevoir la solution complète.

Ces tests vérifient le CONTENU réel des instructions assemblées, pas
seulement la classification des intentions (déjà couverte par
test_intent_engine.py).
"""
import unittest

from chatbot import prompt_builder
from chatbot.services import intent_service as ins
from chatbot.services import pedagogy_templates as pt


def _built(text, class_level="seconde"):
    intent_result = ins.classify(text)
    method_instruction = prompt_builder._method_instruction(intent_result)
    intent_instruction = pt.build_intent_instruction(intent_result)
    return intent_result, method_instruction, intent_instruction


class TestVerificationDuneReponseDejaProposee(unittest.TestCase):
    def test_verification_explicite_demande_de_verifier_et_corriger(self):
        intent_result, _, intent_instruction = _built(
            "J'ai trouvé x = 7 pour 2x + 4 = 10, est-ce correct ?"
        )
        self.assertEqual(intent_result["intent"], ins.CORRECTION)
        self.assertIn("vérifie-la explicitement", intent_instruction)
        self.assertIn("donne la correction nécessaire", intent_instruction)

    def test_formulation_differente_meme_instruction(self):
        intent_result, _, intent_instruction = _built(
            "Pour résoudre x² - 9 = 0, j'ai trouvé x = 3 uniquement. C'est correct ?"
        )
        self.assertEqual(intent_result["intent"], ins.CORRECTION)
        self.assertIn("vérifie-la explicitement", intent_instruction)


class TestCorrectionSansReponsePersonnelle(unittest.TestCase):
    def test_correction_dune_equation_sans_reponse_propre(self):
        intent_result, _, intent_instruction = _built("Corrige mon équation 2x + 4 = 10.")
        self.assertEqual(intent_result["intent"], ins.CORRECTION)
        # La même instruction couvre ce cas (pas de duplication de
        # classification) : elle mentionne aussi la correction complète
        # directe, sans dépendre de la présence de chiffres dans le message
        # pour trancher.
        self.assertIn("fournis-la directement avec les explications utiles", intent_instruction)


class TestDemandeDeCorrectionComplete(unittest.TestCase):
    def test_correction_complete_avec_explications(self):
        intent_result, _, intent_instruction = _built(
            "Corrige cet exercice entièrement avec les explications."
        )
        self.assertEqual(intent_result["intent"], ins.CORRECTION)
        self.assertIn("fournis-la directement avec les explications utiles", intent_instruction)


class TestDemandeDindiceUniquement(unittest.TestCase):
    def test_indice_ne_recoit_jamais_la_clause_de_completion(self):
        intent_result, method_instruction, intent_instruction = _built(
            "Aide-moi à résoudre x² - 5x + 6 = 0 sans me donner la réponse."
        )
        self.assertEqual(intent_result["intent"], ins.INDICE)
        self.assertNotIn(prompt_builder._COMPLETION_CLAUSE, method_instruction)
        self.assertIn("Ne donne JAMAIS le résultat final", intent_instruction)

    def test_indice_reste_la_methode_directe_sans_parcours_en_6_etapes(self):
        _, method_instruction, _ = _built("Donne-moi un indice sur les puissances")
        self.assertEqual(method_instruction, prompt_builder._DIRECT_METHOD_INSTRUCTION)


class TestJustificationGeometriqueComplete(unittest.TestCase):
    def test_triangle_rectangle_recoit_la_clause_de_completion(self):
        intent_result, method_instruction, _ = _built(
            "Un triangle dont les côtés mesurent 3 cm, 4 cm et 6 cm est-il rectangle ? Justifie."
        )
        self.assertEqual(intent_result["intent"], ins.NONE_INTENT)
        self.assertIn(prompt_builder._COMPLETION_CLAUSE, method_instruction)
        self.assertIn("N'interromps jamais spontanément une résolution en cours", method_instruction)


class TestResolutionDirecteDuneEquation(unittest.TestCase):
    def test_resous_recoit_la_clause_de_completion(self):
        _, method_instruction, _ = _built("Résous x² - 5x + 6 = 0 et explique ta méthode.")
        self.assertIn(prompt_builder._COMPLETION_CLAUSE, method_instruction)


class TestExplicationTheoriqueSansCalcul(unittest.TestCase):
    """Non-régression : une question de cours ne doit jamais recevoir le
    parcours guidé en 6 étapes — la clause de complétion (qui ne concerne
    que les demandes de résolution/calcul/vérification/justification/
    explication d'un résultat) n'introduit aucune contradiction ici, elle
    est simplement sans objet."""

    def test_definition_reste_directe(self):
        intent_result, method_instruction, _ = _built("Qu'est-ce qu'une fonction affine ?")
        self.assertEqual(intent_result["intent"], ins.DEFINITION)
        self.assertNotEqual(method_instruction, prompt_builder._GUIDED_METHOD_INSTRUCTION)

    def test_pourquoi_formule_reste_direct_sans_parcours_guide(self):
        _, method_instruction, _ = _built("Pourquoi (a+b)² = a² + 2ab + b² ?")
        self.assertNotEqual(method_instruction, prompt_builder._GUIDED_METHOD_INSTRUCTION)


class TestNonRegressionInstructionsExistantes(unittest.TestCase):
    """Les intentions déjà bien gérées ne doivent pas changer de comportement."""

    def test_exercice_garde_le_parcours_guide_en_6_etapes(self):
        _, method_instruction, _ = _built("Donne-moi un exercice sur les puissances")
        self.assertEqual(method_instruction, prompt_builder._GUIDED_METHOD_INSTRUCTION)

    def test_revision_garde_son_instruction_de_synthese_priorisee(self):
        intent_result, _, intent_instruction = _built(
            "J'ai 20 minutes pour réviser les probabilités. Organise-moi une révision efficace."
        )
        self.assertEqual(intent_result["intent"], ins.REVISION)
        self.assertIn("synthèse de révision PRIORISÉE", intent_instruction)


if __name__ == "__main__":
    unittest.main()
