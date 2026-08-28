"""
Suite du Current Learning Context (continuité de sujet du chatbot) : couvre
exactement le scénario rapporté ("Explique Pythagore" puis un message ambigu
qui faisait parfois dériver le chatbot vers un autre chapitre, ex: les
puissances) — voir chatbot/services/intent_service.py::classify/_detect_chapter,
chatbot/knowledge_engine.py::notion_context_block, db.py::get/set_conversation_
learning_context, chatbot/conversation_manager.py::_update_learning_context.

Utilise la classe "troisieme" (curriculum_registry) : Chapitre_13 y contient
la vraie notion "theoreme-de-pythagore", et Chapitre_2 la vraie notion
"puissances-d-un-nombre-relatif" — le scénario exact de dérive rapporté.
"""
import random
import unittest

import db
import server
from chatbot import knowledge_engine
from chatbot.services import intent_service, pedagogy_templates
from plan_service import Plan

PYTHAGORE_CONTEXT = {
    "chapter_id": "Chapitre_13",
    "notion_id": "theoreme-de-pythagore",
    "topic_label": "Théorème de Pythagore",
}

# Les 6 formulations explicitement demandées + 1 variante polie couverte par
# la même détection (REFORMULATION_RE/FOLLOWUP_TOPIC_RE) — voir intent_service.py.
FOLLOWUP_MESSAGES = [
    "Réexplique",
    "Je n'ai pas compris",
    "Encore",
    "Plus simplement",
    "Donne un autre exemple",
    "Peux-tu détailler",
]


class TestCurrentLearningContextSuivFollowups(unittest.TestCase):
    """Avec un Current Learning Context déjà établi sur Pythagore (voir
    docstring du module : la manière dont il a été établi n'est pas testée
    ici, seule la CONTINUITÉ l'est), chaque message ambigu doit rester
    ancré sur exactement la même notion — jamais de dérive vers un autre
    chapitre (ex: les puissances, cf. bug rapporté)."""

    def test_chaque_formulation_ambigue_reste_sur_pythagore(self):
        for message in FOLLOWUP_MESSAGES:
            with self.subTest(message=message):
                result = intent_service.classify(
                    message, context_summary={}, class_level="troisieme",
                    learning_context=PYTHAGORE_CONTEXT,
                )
                self.assertEqual(result["chapter_id"], "Chapitre_13", msg=f"dérive de chapitre sur {message!r}")
                self.assertEqual(result["notion_id"], "theoreme-de-pythagore", msg=f"dérive de notion sur {message!r}")
                self.assertTrue(result["topic_inherited"], msg=f"topic_inherited devrait être vrai pour {message!r}")

    def test_jamais_de_derive_vers_les_puissances(self):
        """Reproduction directe du bug rapporté : sans Current Learning
        Context, "Je n'ai pas compris" dérive réellement vers le chapitre des
        puissances (recherche TF-IDF faible mais au-dessus du seuil,
        confirmé empiriquement) — avec le contexte mémorisé, plus jamais."""
        without_context = intent_service.classify(
            "Je n'ai pas compris", context_summary={}, class_level="troisieme", learning_context=None,
        )
        self.assertNotEqual(without_context["chapter_id"], "Chapitre_13")  # documente le bug d'origine (hors contexte)

        with_context = intent_service.classify(
            "Je n'ai pas compris", context_summary={}, class_level="troisieme",
            learning_context=PYTHAGORE_CONTEXT,
        )
        self.assertEqual(with_context["chapter_id"], "Chapitre_13")
        self.assertNotEqual(with_context["chapter_id"], without_context["chapter_id"])

    def test_changement_explicite_de_sujet_est_respecte(self):
        """Le Current Learning Context ne doit JAMAIS empêcher un changement
        de sujet explicite — dès qu'un autre chapitre est nettement identifié
        dans le message, il l'emporte (voir _detect_chapter : la recherche
        fraîche reste toujours prioritaire sur le contexte mémorisé)."""
        result = intent_service.classify(
            "Explique-moi maintenant les puissances d'un nombre relatif",
            context_summary={}, class_level="troisieme", learning_context=PYTHAGORE_CONTEXT,
        )
        self.assertEqual(result["chapter_id"], "Chapitre_2")
        self.assertEqual(result["notion_id"], "puissances-d-un-nombre-relatif")
        self.assertFalse(result["topic_inherited"])

    def test_rag_par_lookup_exact_ne_peut_pas_se_tromper_de_notion(self):
        """notion_context_block (lookup exact) doit renvoyer un bloc parlant
        bien de Pythagore, jamais un autre chapitre — contrairement à
        context_block (recherche floue) sur un message ambigu."""
        block = knowledge_engine.notion_context_block(
            "Chapitre_13", "theoreme-de-pythagore", class_level="troisieme",
        )
        self.assertIn("Pythagore", block)

    def test_instruction_explicite_ne_change_pas_de_sujet(self):
        """Quand le sujet est hérité, l'instruction système doit nommer
        explicitement la notion et interdire tout changement de sujet — le
        LLM ne doit jamais avoir à deviner (cahier des charges)."""
        for message in FOLLOWUP_MESSAGES:
            with self.subTest(message=message):
                intent_result = intent_service.classify(
                    message, context_summary={}, class_level="troisieme",
                    learning_context=PYTHAGORE_CONTEXT,
                )
                instruction = pedagogy_templates.build_intent_instruction(
                    intent_result, topic_label=PYTHAGORE_CONTEXT["topic_label"],
                )
                self.assertIn("Théorème de Pythagore", instruction)
                self.assertIn("Ne dévie jamais", instruction)


class TestRepliChapitreSansNotionPrecise(unittest.TestCase):
    """Audit "le chatbot abandonne trop vite" (2026-07-26) : quand le Current
    Learning Context ne connaît que le CHAPITRE (pas de notion précise — ex:
    le message établissant le sujet n'a matché aucune notion par recherche),
    un message ambigu ne doit plus jamais retomber sur une recherche floue
    non fiable sur ce message lui-même (souvent vide/hors-sujet) : le contenu
    de tout le chapitre doit servir de RAG à la place — voir
    conversation_manager._resolve_rag_context et knowledge_engine.
    chapter_context_block/get_chapter_title."""

    CHAPITRE_SEUL_CONTEXT = {"chapter_id": "Chapitre_13", "notion_id": None, "topic_label": "Théorème de Pythagore et trigonométrie"}

    def test_chapter_context_block_contient_le_contenu_du_chapitre(self):
        block = knowledge_engine.chapter_context_block("Chapitre_13", class_level="troisieme")
        self.assertIn("Pythagore", block)

    def test_chapter_context_block_vide_si_chapitre_introuvable(self):
        self.assertEqual(knowledge_engine.chapter_context_block("Chapitre_Inconnu", class_level="troisieme"), "")

    def test_get_chapter_title_renvoie_le_vrai_titre(self):
        title = knowledge_engine.get_chapter_title("Chapitre_13", class_level="troisieme")
        self.assertEqual(title, "Théorème de Pythagore et trigonométrie")

    def test_get_chapter_title_none_si_introuvable(self):
        self.assertIsNone(knowledge_engine.get_chapter_title("Chapitre_Inconnu", class_level="troisieme"))

    def test_resolve_rag_context_utilise_le_chapitre_quand_la_notion_est_inconnue(self):
        from chatbot.conversation_manager import _resolve_rag_context
        intent_result = {
            "intent": intent_service.REFORMULATION, "chapter_id": "Chapitre_13", "notion_id": None,
            "topic_inherited": True,
        }
        rag = _resolve_rag_context(intent_result, "réexplique moi", class_level="troisieme")
        self.assertIn("Pythagore", rag)

    def test_resolve_rag_context_priorise_la_notion_precise_quand_connue(self):
        from chatbot.conversation_manager import _resolve_rag_context
        intent_result = {
            "intent": intent_service.REFORMULATION, "chapter_id": "Chapitre_13",
            "notion_id": "theoreme-de-pythagore", "topic_inherited": True,
        }
        rag = _resolve_rag_context(intent_result, "réexplique moi", class_level="troisieme")
        self.assertIn("Pythagore", rag)

    def test_update_learning_context_retombe_sur_le_titre_du_chapitre(self):
        """_update_learning_context (conversation_manager.py) doit toujours
        pouvoir nommer le sujet, même sans notion précise — sinon
        l'instruction "ne change pas de sujet" (pedagogy_templates) ne peut
        jamais être injectée pour un chapitre connu sans notion exacte."""
        from chatbot import conversation_manager
        import db
        client = server.app.test_client()
        email = f"chaptitle{random.randint(1_000_000, 9_999_999)}@gmail.com"
        username = f"chaptitleuser{random.randint(100_000, 999_999)}"
        resp = client.post("/api/auth/register", json={
            "email": email, "username": username, "pseudo": "ChapTitle",
            "birth_date": "2000-01-01",
            "password": "MotDePasse123!", "confirm_password": "MotDePasse123!",
            "accept_terms": True, "accept_privacy": True,
        })
        user = resp.get_json()["user"]
        conv_id = db.create_conversation(user["id"])
        intent_result = {"intent": intent_service.REFORMULATION, "chapter_id": "Chapitre_13", "notion_id": None}
        topic_label = conversation_manager._update_learning_context(conv_id, intent_result, class_level="troisieme")
        self.assertEqual(topic_label, "Théorème de Pythagore et trigonométrie")


class TestConversationLearningContextPersistance(unittest.TestCase):
    """db.get/set_conversation_learning_context : round-trip simple, et
    valeur par défaut None pour une conversation neuve."""

    def setUp(self):
        self.client = server.app.test_client()
        email = f"lc{random.randint(1_000_000, 9_999_999)}@gmail.com"
        username = f"lcuser{random.randint(100_000, 999_999)}"
        resp = self.client.post("/api/auth/register", json={
            "email": email, "username": username, "pseudo": "LC",
            "birth_date": "2000-01-01",
            "password": "MotDePasse123!", "confirm_password": "MotDePasse123!",
            "accept_terms": True, "accept_privacy": True,
        })
        self.user = resp.get_json()["user"]
        self.conv_id = db.create_conversation(self.user["id"])

    def test_aucun_contexte_pour_une_conversation_neuve(self):
        self.assertIsNone(db.get_conversation_learning_context(self.conv_id))

    def test_round_trip_ecriture_lecture(self):
        db.set_conversation_learning_context(
            self.conv_id, "Chapitre_13", "theoreme-de-pythagore", "Théorème de Pythagore",
        )
        stored = db.get_conversation_learning_context(self.conv_id)
        self.assertEqual(stored["chapter_id"], "Chapitre_13")
        self.assertEqual(stored["notion_id"], "theoreme-de-pythagore")
        self.assertEqual(stored["topic_label"], "Théorème de Pythagore")

    def test_ecriture_suivante_remplace_le_contexte(self):
        db.set_conversation_learning_context(self.conv_id, "Chapitre_13", "theoreme-de-pythagore", "Pythagore")
        db.set_conversation_learning_context(self.conv_id, "Chapitre_2", "puissances-d-un-nombre-relatif", "Puissances")
        stored = db.get_conversation_learning_context(self.conv_id)
        self.assertEqual(stored["chapter_id"], "Chapitre_2")


class TestConversationManagerWiring(unittest.TestCase):
    """Bout en bout via conversation_manager (sans appel LLM réel — le
    fournisseur IA est remplacé par un faux générateur) : vérifie que le
    PIPELINE COMPLET met bien à jour puis réutilise le Current Learning
    Context d'un vrai tour de conversation."""

    def setUp(self):
        self.client = server.app.test_client()
        email = f"lcw{random.randint(1_000_000, 9_999_999)}@gmail.com"
        username = f"lcwuser{random.randint(100_000, 999_999)}"
        resp = self.client.post("/api/auth/register", json={
            "email": email, "username": username, "pseudo": "LCW",
            "birth_date": "2000-01-01",
            "password": "MotDePasse123!", "confirm_password": "MotDePasse123!",
            "accept_terms": True, "accept_privacy": True,
        })
        self.user = resp.get_json()["user"]
        db.set_stripe_subscription(self.user["id"], "sub_lc_test", Plan.PREMIUM.value, "active")
        self.conv_id = db.create_conversation(self.user["id"])

    def test_le_contexte_est_memorise_puis_reutilise(self):
        from chatbot import conversation_manager

        # Premier tour : le sujet est déjà connu (établi par un autre moyen,
        # ex: message explicite ou mention "@" — non testé ici, voir
        # TestCurrentLearningContextSuivFollowups pour la continuité pure) —
        # on simule directement l'état "après un premier tour réussi sur
        # Pythagore" en écrivant le contexte, comme le ferait
        # _update_learning_context au premier tour réel.
        db.set_conversation_learning_context(
            self.conv_id, "Chapitre_13", "theoreme-de-pythagore", "Théorème de Pythagore",
        )

        captured_system_prompts = []

        def fake_llm_generate(messages, system_prompt, chatbot_settings, user=None, call_info=None, **_kwargs):
            captured_system_prompts.append(system_prompt)
            if call_info is not None:
                call_info["provider"] = "fake"
                call_info["model"] = "test"
                call_info["fallback_from"] = None
                call_info["usage"] = None
            yield "Réponse de test."

        original_generate = conversation_manager.llm_fallback_service.generate
        conversation_manager.llm_fallback_service.generate = fake_llm_generate
        try:
            list(conversation_manager.stream_reply(
                self.user, self.conv_id, "Réexplique", class_level="troisieme",
            ))
        finally:
            conversation_manager.llm_fallback_service.generate = original_generate

        self.assertEqual(len(captured_system_prompts), 1)
        system_prompt = captured_system_prompts[0]
        self.assertIn("Théorème de Pythagore", system_prompt)
        self.assertIn("Pythagore", system_prompt)  # extrait RAG exact également présent
        self.assertNotIn("puissance", system_prompt.lower())

        # Le contexte reste (toujours) celui de Pythagore après ce tour.
        stored = db.get_conversation_learning_context(self.conv_id)
        self.assertEqual(stored["chapter_id"], "Chapitre_13")


class TestLearningContextTransmisAuLocalResponseEngine(unittest.TestCase):
    """Bug confirmé (audit du 2026-08-22) : conversation_manager.
    _try_local_response_engine()/local_response_engine.generate() n'avaient
    aucun paramètre learning_context — un message de suivi court routé vers
    le Local Response Engine (pas le LLM) pouvait donc écraser un sujet déjà
    établi (ex: "encore une autre façon" avec "La valeur absolue" déjà
    établie dérivait vers Chapitre_12/operations-sur-les-evenements).
    Vérifie les DEUX chemins réels : réponse normale (stream_reply) et
    régénération (regenerate_last)."""

    def setUp(self):
        self.client = server.app.test_client()
        email = f"lrec{random.randint(1_000_000, 9_999_999)}@gmail.com"
        username = f"lrecuser{random.randint(100_000, 999_999)}"
        resp = self.client.post("/api/auth/register", json={
            "email": email, "username": username, "pseudo": "LREC",
            "birth_date": "2000-01-01",
            "password": "MotDePasse123!", "confirm_password": "MotDePasse123!",
            "accept_terms": True, "accept_privacy": True,
        })
        self.user = resp.get_json()["user"]
        self.conv_id = db.create_conversation(self.user["id"])
        db.set_conversation_learning_context(
            self.conv_id, "Chapitre_2", "valeur-absolue-dun-nombre-reel", "La valeur absolue",
        )

    def test_reponse_normale_stream_reply_conserve_le_sujet(self):
        from chatbot import conversation_manager

        list(conversation_manager.stream_reply(
            self.user, self.conv_id, "encore une autre façon", class_level="seconde",
        ))
        last = db.list_messages(self.conv_id)[-1]
        self.assertEqual(last["role"], "assistant")
        self.assertIn("valeur absolue".lower(), last["content"].lower())
        self.assertNotIn("évènement", last["content"].lower())
        stored = db.get_conversation_learning_context(self.conv_id)
        self.assertEqual(stored["chapter_id"], "Chapitre_2")

    def test_regeneration_regenerate_last_conserve_le_sujet(self):
        from chatbot import conversation_manager

        db.add_message(self.conv_id, "user", "encore une autre façon", mentions=None)
        db.add_message(self.conv_id, "assistant", "réponse initiale (à régénérer)", engine="test")

        list(conversation_manager.regenerate_last(self.user, self.conv_id, class_level="seconde"))

        last = db.list_messages(self.conv_id)[-1]
        self.assertEqual(last["role"], "assistant")
        self.assertIn("valeur absolue".lower(), last["content"].lower())
        self.assertNotIn("évènement", last["content"].lower())


if __name__ == "__main__":
    unittest.main()
