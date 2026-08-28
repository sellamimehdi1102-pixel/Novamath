"""Suite de la détection de répétition d'incompréhension (chantier
pédagogique Phase 3 — chatbot) : voir chatbot/conversation_manager.py::
_detect_repeated_incomprehension et chatbot/services/pedagogy_templates.py.

Avant ce chantier, rien ne détectait qu'un élève exprime une incompréhension
("je ne comprends pas") deux tours de suite (voir audit Phase 0) — le LLM
pouvait alors répéter presque la même explication. Cette suite vérifie que
le signal est détecté au bon moment (jamais au premier message, toujours au
second consécutif) et qu'il se traduit en une instruction concrète de
changement d'approche dans le prompt système.
"""
import random
import unittest

import db
import server
from chatbot import conversation_manager
from chatbot.services import intent_service, pedagogy_templates


def _register(client):
    email = f"repet{random.randint(1_000_000, 9_999_999)}@gmail.com"
    username = f"repetuser{random.randint(100_000, 999_999)}"
    resp = client.post("/api/auth/register", json={
        "email": email, "username": username, "pseudo": "Repet",
        "birth_date": "2000-01-01",
        "password": "MotDePasse123!", "confirm_password": "MotDePasse123!",
        "accept_terms": True, "accept_privacy": True,
    })
    return resp.get_json()["user"]


class TestDetectionRepetitionIncomprehension(unittest.TestCase):
    def setUp(self):
        client = server.app.test_client()
        self.user = _register(client)
        self.conv_id = db.create_conversation(self.user["id"])

    def test_pas_de_repetition_au_premier_message(self):
        db.add_message(self.conv_id, "user", "Je ne comprends pas", mentions=None)
        intent_result = {"intent": intent_service.REFORMULATION}
        detected = conversation_manager._detect_repeated_incomprehension(
            intent_result, self.conv_id, context_summary={}, class_level=None, learning_context=None,
        )
        self.assertFalse(detected, "Un seul message d'incompréhension ne doit jamais déclencher l'escalade.")

    def test_repetition_detectee_au_deuxieme_message_consecutif(self):
        db.add_message(self.conv_id, "user", "Je ne comprends pas", mentions=None)
        db.add_message(self.conv_id, "assistant", "Reprenons calmement.", engine="test")
        db.add_message(self.conv_id, "user", "Je ne comprends toujours pas", mentions=None)
        intent_result = {"intent": intent_service.REFORMULATION}
        detected = conversation_manager._detect_repeated_incomprehension(
            intent_result, self.conv_id, context_summary={}, class_level=None, learning_context=None,
        )
        self.assertTrue(detected, "Deux messages d'incompréhension consécutifs doivent déclencher l'escalade.")

    def test_pas_de_repetition_si_le_message_precedent_etait_different(self):
        db.add_message(self.conv_id, "user", "Peux-tu me donner un exercice ?", mentions=None)
        db.add_message(self.conv_id, "assistant", "Voici un exercice.", engine="test")
        db.add_message(self.conv_id, "user", "Je ne comprends pas", mentions=None)
        intent_result = {"intent": intent_service.REFORMULATION}
        detected = conversation_manager._detect_repeated_incomprehension(
            intent_result, self.conv_id, context_summary={}, class_level=None, learning_context=None,
        )
        self.assertFalse(detected, "Le message précédent n'exprimait pas d'incompréhension : pas d'escalade.")

    def test_pas_de_repetition_hors_intentions_concernees(self):
        db.add_message(self.conv_id, "user", "Je ne comprends pas", mentions=None)
        db.add_message(self.conv_id, "assistant", "Reprenons calmement.", engine="test")
        db.add_message(self.conv_id, "user", "Merci !", mentions=None)
        intent_result = {"intent": intent_service.NONE_INTENT}
        detected = conversation_manager._detect_repeated_incomprehension(
            intent_result, self.conv_id, context_summary={}, class_level=None, learning_context=None,
        )
        self.assertFalse(detected, "Un remerciement n'est pas une incompréhension : pas d'escalade.")


class TestInstructionDeChangementDApproche(unittest.TestCase):
    def test_instruction_absente_par_defaut(self):
        instr = pedagogy_templates.build_intent_instruction({"intent": intent_service.REFORMULATION})
        self.assertNotIn("deuxième fois", instr)

    def test_instruction_presente_quand_repetition_detectee(self):
        instr = pedagogy_templates.build_intent_instruction({
            "intent": intent_service.REFORMULATION, "repeated_incomprehension": True,
        })
        self.assertIn("deuxième fois", instr)
        self.assertIn("change réellement d'approche", instr)


class TestSequenceSimplifieCompleteRealiste(unittest.TestCase):
    """Reproduit exactement la séquence réelle du bug "reformulations
    successives identiques" (audit 2026-08-22) : "simplifie" était classé
    NONE_INTENT, cassant la chaîne _detect_repeated_incomprehension pour le
    tour suivant. Vérifie la séquence complète après correctif."""

    def setUp(self):
        client = server.app.test_client()
        self.user = _register(client)
        self.conv_id = db.create_conversation(self.user["id"])

    def test_sequence_complete_valeur_absolue(self):
        messages = [
            "c'est quoi une valeur absolue",
            "simplifie",
            "explique plus simplement je n'ai rien compris",
            "j'ai toujours pas compris",
        ]
        expected_intents = [
            intent_service.DEFINITION, intent_service.REFORMULATION,
            intent_service.RESTART_BASICS, intent_service.REFORMULATION,
        ]
        expected_repeated = [False, False, True, True]

        learning_context = None
        for message, exp_intent, exp_repeated in zip(messages, expected_intents, expected_repeated):
            db.add_message(self.conv_id, "user", message, mentions=None)
            intent_result = intent_service.classify(
                message, context_summary={}, class_level="seconde", learning_context=learning_context,
            )
            with self.subTest(message=message):
                self.assertEqual(intent_result["intent"], exp_intent)
                self.assertEqual(intent_result["chapter_id"], "Chapitre_2")
                self.assertEqual(intent_result["notion_id"], "valeur-absolue-dun-nombre-reel")
                repeated = conversation_manager._detect_repeated_incomprehension(
                    intent_result, self.conv_id, context_summary={}, class_level="seconde",
                    learning_context=learning_context,
                )
                self.assertEqual(repeated, exp_repeated)
            if intent_result["chapter_id"]:
                learning_context = {"chapter_id": intent_result["chapter_id"], "notion_id": intent_result["notion_id"]}
            db.add_message(self.conv_id, "assistant", f"réponse simulée pour {message!r}", engine="test")


class TestRestartBasicsPlanRiche(unittest.TestCase):
    """RESTART_BASICS doit désormais produire le même plan de contenu riche
    que REFORMULATION [BLOCK_METHODE, BLOCK_EXEMPLE, BLOCK_DEFINITION] —
    plus jamais le plan par défaut [BLOCK_DEFINITION] (identique à celui de
    DEFINITION, cause de la répétition)."""

    def test_restart_basics_utilise_methode_et_exemple(self):
        from chatbot.services import knowledge_response_composer as krc, response_strategy as rs

        sctx = {
            "user_id": 1, "pseudo": "Testeur", "niveau": "Débutant", "niveau_brut": 1,
            "class_level": "seconde", "chapitre_courant": None, "topic_courant": None,
            "notions_maitrisees": [], "notions_faibles": [], "topics_maitrises": [], "topics_faibles": [],
            "statistiques": {"accuracy": 0, "total_exercices": 0, "temps_total": "0 h", "temps_jour": "0 h", "temps_semaine": "0 h"},
            "dashboard": {"objectif_du_jour": None, "chapitres_en_cours": [], "meilleur_chapitre": None, "chapitre_le_plus_faible": None},
            "progression": {}, "preferences": {"langue": "fr", "niveau_explication": "auto", "favoris": []},
            "parametres": {
                "longueur": "normal", "niveau_explication": "auto", "mode": None,
                "memoire_activee": True, "historique_active": True, "provider": None,
                "modele": None, "temperature": 0.6,
            },
            "mentions": [], "historique_conversation": [],
        }
        strategy = rs.ResponseStrategy(
            source=rs.SOURCE_LOCAL, engine=rs.ENGINE_KNOWLEDGE, confidence=50,
            intent=intent_service.RESTART_BASICS, chapter_id="Chapitre_1", topic_id="puissances-entieres-relatives",
            quantity=None, difficulty=None, mode=None, should_use_llm=False,
            fallback=rs.ENGINE_LLM, explanation="test",
        )
        draft = krc.compose(strategy, student_context=sctx)
        kinds = [b.kind for b in draft.blocks]
        self.assertIn(krc.BLOCK_METHODE, kinds)
        self.assertIn(krc.BLOCK_EXEMPLE, kinds)
        self.assertIn(krc.BLOCK_DEFINITION, kinds)


class TestReformulationInchangee(unittest.TestCase):
    """Non-régression explicite : REFORMULATION continue d'utiliser
    [BLOCK_METHODE, BLOCK_EXEMPLE, BLOCK_DEFINITION] (correctif précédent,
    non touché par ce chantier)."""

    def test_reformulation_plan_inchange(self):
        from chatbot.services import knowledge_response_composer as krc

        self.assertEqual(
            krc._content_plan(intent_service.REFORMULATION, "normal", None),
            [krc.BLOCK_METHODE, krc.BLOCK_EXEMPLE, krc.BLOCK_DEFINITION],
        )


class TestFollowupEtChangementDeSujetNonAffectes(unittest.TestCase):
    """Le correctif "simplifie" est ancré (^...$) : ne doit toucher ni
    FOLLOWUP ni le changement de sujet explicite."""

    def test_followup_reste_followup(self):
        lc = {"chapter_id": "Chapitre_2", "notion_id": "valeur-absolue-dun-nombre-reel"}
        for text in ["Pourquoi ?", "Continue.", "Encore."]:
            with self.subTest(text=text):
                result = intent_service.classify(text, context_summary={}, class_level="seconde", learning_context=lc)
                self.assertIn(result["intent"], (intent_service.FOLLOWUP, intent_service.REFORMULATION))
                self.assertEqual(result["chapter_id"], "Chapitre_2")
                self.assertEqual(result["notion_id"], "valeur-absolue-dun-nombre-reel")

    def test_changement_de_sujet_explicite_toujours_possible(self):
        lc = {"chapter_id": "Chapitre_2", "notion_id": "valeur-absolue-dun-nombre-reel"}
        result = intent_service.classify(
            "Maintenant explique-moi les probabilités.", context_summary={}, class_level="seconde", learning_context=lc,
        )
        self.assertNotEqual(result["chapter_id"], "Chapitre_2")


if __name__ == "__main__":
    unittest.main()
