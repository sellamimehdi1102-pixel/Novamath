"""
Chantier "priorité intention vs mode pédagogique" (test C, 2026-10-17) :
aucune clause n'arbitrait un conflit entre l'instruction d'intention
(pedagogy_templates._INTENT_INSTRUCTIONS, ce que l'élève demande dans le
message) et l'instruction de mode (pedagogy_templates._MODE_INSTRUCTIONS,
une préférence générale enregistrée) quand elles se contredisent. Exemple
confirmé par l'audit : "J'ai 20 minutes pour réviser les probabilités.
Organise-moi une révision efficace." (intention REVISION) + mode
"professeur" (par défaut pour tout compte, voir auth.py DEFAULT_USER_SETTINGS)
produisait un cours détaillé imposé plutôt qu'une synthèse priorisée.

Correction : prompt_builder._EXPLICIT_REQUEST_PRIORITY_INSTRUCTION, injectée
uniquement quand une instruction d'intention ET une instruction de mode
coexistent, et que ce mode n'a pas déjà sa propre clause de précédence
(voir pedagogy_templates.MODES_WITH_OWN_PRECEDENCE_CLAUSE = {"rapide",
"examen"}, qui priment déjà, délibérément, dans l'autre sens — ne jamais
les contredire).
"""
import unittest

from chatbot import prompt_builder
from chatbot.services import intent_service, pedagogy_templates


def _prompt_for(intent, mode=None, class_level="seconde"):
    settings = {"mode": mode} if mode else {}
    return prompt_builder.build_system_prompt(
        user={"id": 1}, chatbot_settings=settings, chapters_summary=None, rag_context=None,
        mentions_block=None, intent_result={"intent": intent}, class_level=class_level,
    )


class TestRegleDePrioriteInjecteeQuandNecessaire(unittest.TestCase):
    """Conflits explicitement cités par l'audit du test C."""

    def test_revision_et_professeur_recoit_la_regle_de_priorite(self):
        prompt = _prompt_for(intent_service.REVISION, mode="professeur")
        self.assertIn("RÈGLE DE PRIORITÉ", prompt)
        # Les deux instructions restent présentes : la règle arbitre, elle
        # ne supprime aucune des deux.
        self.assertIn("synthèse de révision priorisée".lower(), prompt.lower())
        self.assertIn("mode professeur".lower(), prompt.lower())

    def test_indice_et_professeur_recoit_la_regle_de_priorite(self):
        prompt = _prompt_for(intent_service.INDICE, mode="professeur")
        self.assertIn("RÈGLE DE PRIORITÉ", prompt)
        self.assertIn("ne donne jamais le résultat final".lower(), prompt.lower())

    def test_correction_et_pas_a_pas_recoit_la_regle_de_priorite(self):
        prompt = _prompt_for(intent_service.CORRECTION, mode="pas_a_pas")
        self.assertIn("RÈGLE DE PRIORITÉ", prompt)

    def test_exemple_et_visuel_recoit_la_regle_de_priorite(self):
        prompt = _prompt_for(intent_service.EXEMPLE, mode="visuel")
        self.assertIn("RÈGLE DE PRIORITÉ", prompt)


class TestRegleAbsenteQuandNonPertinente(unittest.TestCase):
    """La règle ne doit jamais apparaître quand il n'y a rien à arbitrer, ni
    contredire les modes qui ont déjà leur propre clause de précédence."""

    def test_sans_mode_pas_de_regle(self):
        prompt = _prompt_for(intent_service.REVISION, mode=None)
        self.assertNotIn("RÈGLE DE PRIORITÉ", prompt)

    def test_sans_intention_specifique_pas_de_regle(self):
        prompt = _prompt_for(intent_service.NONE_INTENT, mode="professeur")
        self.assertNotIn("RÈGLE DE PRIORITÉ", prompt)

    def test_mode_rapide_garde_sa_propre_clause_sans_regle_generique(self):
        """Non-régression : "rapide" prime déjà, dans l'autre sens
        (délibérément), sur la méthode en plusieurs étapes — la règle
        générique ne doit pas s'y ajouter et créer une contradiction."""
        prompt = _prompt_for(intent_service.EXERCICE, mode="rapide")
        self.assertNotIn("RÈGLE DE PRIORITÉ", prompt)
        self.assertIn("ce mode prime sur toute consigne de méthode".lower(), prompt.lower())

    def test_mode_examen_garde_sa_propre_clause_sans_regle_generique(self):
        """Non-régression : "examen" doit continuer à bloquer toute solution/
        indice même si l'intention EXERCICE en suggère un — la règle
        générique (intention > mode) irait dans le sens opposé et casserait
        ce comportement déjà correct."""
        prompt = _prompt_for(intent_service.EXERCICE, mode="examen")
        self.assertNotIn("RÈGLE DE PRIORITÉ", prompt)
        self.assertIn("ne donne jamais la réponse ni le moindre indice".lower(), prompt.lower())


class TestModeHasOwnPrecedenceClause(unittest.TestCase):
    def test_rapide_et_examen_ont_leur_propre_clause(self):
        self.assertTrue(pedagogy_templates.mode_has_own_precedence_clause("rapide"))
        self.assertTrue(pedagogy_templates.mode_has_own_precedence_clause("examen"))

    def test_professeur_pas_a_pas_visuel_nen_ont_pas(self):
        self.assertFalse(pedagogy_templates.mode_has_own_precedence_clause("professeur"))
        self.assertFalse(pedagogy_templates.mode_has_own_precedence_clause("pas_a_pas"))
        self.assertFalse(pedagogy_templates.mode_has_own_precedence_clause("visuel"))
        self.assertFalse(pedagogy_templates.mode_has_own_precedence_clause(None))


if __name__ == "__main__":
    unittest.main()
