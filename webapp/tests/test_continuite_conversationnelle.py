"""
Chantier "continuité conversationnelle" (2026-08-22, audit puis correction) :
- Phase A : messages courts de pure continuation ("continue", "pourquoi ?",
  "développe", "oui"/"non" nus) rattachés au fil de la conversation plutôt que
  traités comme des questions isolées.
- Phase B/C : un Current Learning Context déjà établi ne doit plus être
  écrasé par une correspondance TF-IDF simplement faible (bug confirmé :
  "équation cartésienne" -> "proportionnalité") ; un changement de sujet
  explicitement assumé par l'élève doit, lui, toujours l'emporter.
- Phase E : le prompt système impose la progression en 6 étapes seulement
  pour les intentions d'exercice/méthode, jamais pour une question directe.

Utilise la classe "troisieme" (mêmes chapitres réels que
test_learning_context_continuity.py : Chapitre_13 = Pythagore, Chapitre_2 =
puissances) pour la cohérence, et deux requêtes calibrées empiriquement sur
le corpus réel (voir docstrings ci-dessous) pour les cas de score faible.
"""
import unittest

from chatbot import conversation_manager, prompt_builder
from chatbot.services import intent_service

PYTHAGORE_CONTEXT = {
    "chapter_id": "Chapitre_13",
    "notion_id": "theoreme-de-pythagore",
    "topic_label": "Théorème de Pythagore",
}


class TestMessagesCourtsDeContinuation(unittest.TestCase):
    """Phase A : "continue", "pourquoi ?", "développe"... doivent être
    reconnus comme une pure continuation (intent FOLLOWUP) et rester ancrés
    sur le Current Learning Context, jamais réévalués par une recherche
    TF-IDF sur ces quelques mots (qui ne veulent rien dire isolément)."""

    FOLLOWUP_MESSAGES = ["continue", "Continue.", "développe", "développe ça", "pourquoi ?", "pourquoi", "comment ça ?"]

    def test_chaque_message_court_est_classe_followup_et_reste_sur_le_sujet(self):
        for message in self.FOLLOWUP_MESSAGES:
            with self.subTest(message=message):
                result = intent_service.classify(
                    message, context_summary={}, class_level="troisieme", learning_context=PYTHAGORE_CONTEXT,
                )
                self.assertEqual(result["intent"], intent_service.FOLLOWUP, msg=f"intent inattendu pour {message!r}")
                self.assertEqual(result["chapter_id"], "Chapitre_13", msg=f"dérive de sujet pour {message!r}")
                self.assertTrue(result["topic_inherited"])

    def test_continue_sans_aucun_contexte_ne_devient_pas_followup_hasardeux(self):
        """Sans Current Learning Context du tout (première question de la
        conversation), "continue" reste FOLLOWUP mais ne peut naturellement
        rattacher à aucun sujet — aucun chapitre ne doit être inventé."""
        result = intent_service.classify("continue", context_summary={}, class_level="troisieme", learning_context=None)
        self.assertEqual(result["intent"], intent_service.FOLLOWUP)
        self.assertIsNone(result["chapter_id"])

    def test_continue_ton_exercice_sur_les_fractions_nest_pas_un_message_nu(self):
        """Un message qui CONTIENT "continue" mais porte aussi un vrai sujet
        ne doit pas être traité comme une pure continuation nue (le sujet
        explicite doit être détectable normalement)."""
        result = intent_service.classify(
            "continue ton explication sur les puissances d'un nombre relatif",
            context_summary={}, class_level="troisieme", learning_context=PYTHAGORE_CONTEXT,
        )
        self.assertNotEqual(result["intent"], intent_service.FOLLOWUP)


class TestConfirmationOuiNonAmbigue(unittest.TestCase):
    """Phase A : "oui"/"non" nus ne doivent être traités comme une
    continuation QUE s'ils répondent à une question posée par l'assistant."""

    def test_oui_apres_une_question_de_lassistant_est_une_continuation(self):
        result = intent_service.classify(
            "oui", context_summary={}, class_level="troisieme", learning_context=PYTHAGORE_CONTEXT,
            last_assistant_message="Est-ce que tu veux un exemple ?",
        )
        self.assertEqual(result["intent"], intent_service.FOLLOWUP)
        self.assertEqual(result["chapter_id"], "Chapitre_13")
        self.assertTrue(result["topic_inherited"])

    def test_oui_sans_question_prealable_nest_pas_force(self):
        result = intent_service.classify(
            "oui", context_summary={}, class_level="troisieme", learning_context=PYTHAGORE_CONTEXT,
            last_assistant_message="Voici la formule du théorème de Pythagore.",
        )
        self.assertNotEqual(result["intent"], intent_service.FOLLOWUP)

    def test_non_avec_du_texte_reste_un_changement_de_sujet_normal(self):
        """"non, je parle des puissances" ne matche pas le "non" nu — le
        sujet ("puissances d'un nombre relatif") doit être détecté comme
        d'habitude, changement de sujet explicite inclus."""
        result = intent_service.classify(
            "non, je veux parler des puissances d'un nombre relatif",
            context_summary={}, class_level="troisieme", learning_context=PYTHAGORE_CONTEXT,
            last_assistant_message="Est-ce que tu veux un exemple sur Pythagore ?",
        )
        self.assertEqual(result["chapter_id"], "Chapitre_2")
        self.assertFalse(result["topic_inherited"])


class TestNonEcrasementDuContextePourUnScoreFaible(unittest.TestCase):
    """Phase B/C : correction directe du bug "équation cartésienne" ->
    "proportionnalité" — un score TF-IDF simplement faible (au-dessus de
    l'ancien seuil unique 0.12, mais sous le nouveau seuil "fort" 0.20) ne
    doit plus écraser un Current Learning Context déjà établi.

    "et la formule" scorе empiriquement 0.169 sur Chapitre_8 (classe
    troisieme) — un score faible, RÉEL, pour un chapitre différent de
    Pythagore (Chapitre_13) : exactement le scénario du bug rapporté."""

    WEAK_QUERY = "et la formule"

    def test_score_faible_ne_derive_pas_le_sujet(self):
        result = intent_service.classify(
            self.WEAK_QUERY, context_summary={}, class_level="troisieme", learning_context=PYTHAGORE_CONTEXT,
        )
        self.assertEqual(result["chapter_id"], "Chapitre_13", "un score faible a écrasé le contexte à tort")
        self.assertEqual(result["topic_confidence"], "inherited")

    def test_score_faible_sans_aucun_contexte_reste_utilise_faute_de_mieux(self):
        """Sans Current Learning Context du tout, le score faible reste le
        seul signal disponible — il doit toujours être utilisé (sinon le
        chatbot "abandonnerait" une vraie première question)."""
        result = intent_service.classify(
            self.WEAK_QUERY, context_summary={}, class_level="troisieme", learning_context=None,
        )
        self.assertEqual(result["chapter_id"], "Chapitre_8")
        self.assertEqual(result["topic_confidence"], "weak")

    def test_changement_de_sujet_explicitement_assume_lemporte_meme_a_score_faible(self):
        """"je veux parler de la formule" scorе le même 0.169 sur Chapitre_8,
        mais porte un marqueur de changement de sujet explicite
        (EXPLICIT_TOPIC_CHANGE_RE) : il doit l'emporter sur Pythagore, sans
        exiger le score fort habituel."""
        result = intent_service.classify(
            "je veux parler de la formule", context_summary={}, class_level="troisieme",
            learning_context=PYTHAGORE_CONTEXT,
        )
        self.assertEqual(result["chapter_id"], "Chapitre_8")
        self.assertEqual(result["topic_confidence"], "explicit")
        self.assertFalse(result["topic_inherited"])

    def test_update_learning_context_conserve_lancien_sujet_sur_signal_faible(self):
        """Bout-en-bout conversation_manager._update_learning_context : un
        intent_result de confiance "weak"/"global" pointant vers un AUTRE
        chapitre ne doit pas réécrire le Current Learning Context existant."""
        intent_result = {"intent": intent_service.NONE_INTENT, "chapter_id": "Chapitre_8", "notion_id": None, "topic_confidence": "weak"}
        topic_label = conversation_manager._update_learning_context(
            "conv-id-inutilise", intent_result, class_level="troisieme",
            existing_learning_context=PYTHAGORE_CONTEXT,
        )
        self.assertEqual(topic_label, "Théorème de Pythagore")

    def test_update_learning_context_ecrit_normalement_sur_signal_fort(self):
        """À l'inverse, une confiance "explicit" doit bien mettre à jour le
        contexte — la garde ne doit pas devenir un verrou permanent."""
        intent_result = {"intent": intent_service.NONE_INTENT, "chapter_id": "Chapitre_2", "notion_id": "puissances-d-un-nombre-relatif", "topic_confidence": "explicit"}
        topic_label = conversation_manager._update_learning_context(
            "conv-id-inutilise", intent_result, class_level="troisieme",
            existing_learning_context=PYTHAGORE_CONTEXT,
        )
        self.assertNotEqual(topic_label, "Théorème de Pythagore")


class TestPromptMethodeConditionnelleAlIntention(unittest.TestCase):
    """Phase E : la progression en 6 étapes ("ARRÊTE-toi après chaque
    étape") ne doit plus s'appliquer par défaut à une question directe
    (définition/explication/pourquoi) — seulement à un exercice/une méthode
    à dérouler."""

    def _prompt_for(self, intent):
        return prompt_builder.build_system_prompt(
            user={"id": 1}, chatbot_settings={}, chapters_summary=None, rag_context=None,
            mentions_block=None, intent_result={"intent": intent}, class_level="troisieme",
        )

    def test_definition_ne_force_pas_les_six_etapes(self):
        prompt = self._prompt_for(intent_service.DEFINITION)
        self.assertNotIn("ARRÊTE-toi après chaque étape", prompt)
        self.assertIn("réponds-y clairement et directement".lower(), prompt.lower())

    def test_followup_ne_force_pas_les_six_etapes(self):
        prompt = self._prompt_for(intent_service.FOLLOWUP)
        self.assertNotIn("ARRÊTE-toi après chaque étape", prompt)

    def test_exercice_impose_bien_la_progression_pas_a_pas(self):
        prompt = self._prompt_for(intent_service.EXERCICE)
        self.assertIn("ARRÊTE-toi après chaque étape", prompt)

    def test_methode_impose_bien_la_progression_pas_a_pas(self):
        prompt = self._prompt_for(intent_service.METHODE)
        self.assertIn("ARRÊTE-toi après chaque étape", prompt)

    def test_aucune_intention_connue_garde_le_comportement_par_defaut(self):
        """NONE_INTENT (question libre non classifiée) garde l'ancien
        comportement mixte (le LLM tranche lui-même factuel/exercice) —
        aucune régression pour les cas déjà ambigus avant ce chantier."""
        prompt = self._prompt_for(intent_service.NONE_INTENT)
        self.assertIn("purement factuelle ou hors exercice", prompt)


if __name__ == "__main__":
    unittest.main()
