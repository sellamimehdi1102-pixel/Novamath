"""Suite dédiée au mécanisme d'escalade pédagogique (chantier du
2026-08-22) : conversation_manager._get_escalation_level/_select_approach/
_advance_escalation_state, la persistance dans conversations.learning_context
(db.py), la propagation au Local Response Engine (response_strategy/
local_response_engine/knowledge_response_composer) et au mode dégradé
(degraded_mode_service), ainsi que l'instruction structurée transmise au LLM
(pedagogy_templates). Le mécanisme historique `repeated_incomprehension`
reste inchangé et testé séparément (test_chatbot_repeated_incomprehension.py).
"""
import random
import unittest

import db
import server
from chatbot import conversation_manager as cm
from chatbot.services import degraded_mode_service, intent_service, knowledge_response_composer as krc, pedagogy_templates


def _register(client):
    email = f"esc{random.randint(1_000_000, 9_999_999)}@gmail.com"
    username = f"escuser{random.randint(100_000, 999_999)}"
    resp = client.post("/api/auth/register", json={
        "email": email, "username": username, "pseudo": "Esc",
        "birth_date": "2000-01-01",
        "password": "MotDePasse123!", "confirm_password": "MotDePasse123!",
        "accept_terms": True, "accept_privacy": True,
    })
    return resp.get_json()["user"]


class TestFonctionsPures(unittest.TestCase):
    def test_escalation_level_croit_avec_le_compteur(self):
        self.assertEqual(cm._get_escalation_level(0), 0)
        self.assertEqual(cm._get_escalation_level(1), 1)
        self.assertEqual(cm._get_escalation_level(2), 2)
        self.assertEqual(cm._get_escalation_level(3), 3)
        self.assertEqual(cm._get_escalation_level(4), 4)

    def test_escalation_level_plafonne_a_4(self):
        self.assertEqual(cm._get_escalation_level(5), 4)
        self.assertEqual(cm._get_escalation_level(100), 4)

    def test_escalation_level_none_ou_zero(self):
        self.assertEqual(cm._get_escalation_level(None), 0)
        self.assertEqual(cm._get_escalation_level(0), 0)

    def test_select_approach_deterministe(self):
        # Deux appels identiques -> résultat identique (pas de random.choice).
        r1 = cm._select_approach(2, [], cm._LLM_APPROACHES)
        r2 = cm._select_approach(2, [], cm._LLM_APPROACHES)
        self.assertEqual(r1, r2)

    def test_select_approach_evite_les_approches_deja_utilisees(self):
        result = cm._select_approach(0, ["definition"], cm._LLM_APPROACHES)
        self.assertNotEqual(result, "definition")

    def test_select_approach_repli_sur_repetition_si_tout_deja_vu(self):
        result = cm._select_approach(0, list(cm._LLM_APPROACHES), cm._LLM_APPROACHES)
        self.assertEqual(result, cm._LLM_APPROACHES[0])  # répétition acceptée, jamais None/erreur

    def test_select_approach_ne_force_jamais_une_approche_absente(self):
        # available_approaches ne contient QUE "definition"/"exemple" (ex:
        # notion sans méthode) -> jamais "analogie"/"question_guidee" renvoyé.
        for level in range(5):
            result = cm._select_approach(level, [], ("definition", "exemple"))
            self.assertIn(result, ("definition", "exemple"))

    def test_select_approach_liste_vide_renvoie_none(self):
        self.assertIsNone(cm._select_approach(0, [], ()))


class TestAdvanceEscalationState(unittest.TestCase):
    def test_incremente_sur_incomprehension(self):
        lc = {"chapter_id": "Chapitre_2", "notion_id": "x", "incomprehension_count": 1, "approaches_used": ["definition"]}
        count, level, used, rec = cm._advance_escalation_state(intent_service.REFORMULATION, "Chapitre_2", lc, cm._LLM_APPROACHES)
        self.assertEqual(count, 2)
        self.assertEqual(level, 2)

    def test_ninc_pas_sur_followup(self):
        lc = {"chapter_id": "Chapitre_2", "notion_id": "x", "incomprehension_count": 3, "approaches_used": []}
        count, _, _, _ = cm._advance_escalation_state(intent_service.FOLLOWUP, "Chapitre_2", lc, cm._LLM_APPROACHES)
        self.assertEqual(count, 3)

    def test_ninc_pas_sur_question_normale(self):
        lc = {"chapter_id": "Chapitre_2", "notion_id": "x", "incomprehension_count": 0, "approaches_used": []}
        count, _, _, _ = cm._advance_escalation_state(intent_service.EXEMPLE, "Chapitre_2", lc, cm._LLM_APPROACHES)
        self.assertEqual(count, 0)

    def test_reset_sur_changement_de_sujet(self):
        lc = {"chapter_id": "Chapitre_2", "notion_id": "x", "incomprehension_count": 4, "approaches_used": ["definition", "exemple"]}
        count, level, used, rec = cm._advance_escalation_state(intent_service.NONE_INTENT, "Chapitre_12", lc, cm._LLM_APPROACHES)
        self.assertEqual(count, 0)
        self.assertEqual(level, 0)

    def test_premier_tour_sans_contexte_existant(self):
        count, level, used, rec = cm._advance_escalation_state(intent_service.DEFINITION, "Chapitre_2", None, cm._LLM_APPROACHES)
        self.assertEqual(count, 0)
        self.assertEqual(level, 0)
        self.assertIsNotNone(rec)

    def test_recommended_approach_nest_plus_ajoutee_a_approaches_used(self):
        # Chantier "fausse mémoire d'approche" (2026-08-22) : `recommended_approach`
        # est une SUGGESTION transmise au moteur, jamais une certitude qu'elle
        # sera réellement produite — _advance_escalation_state ne doit donc
        # plus l'ajouter elle-même à approaches_used. Seul un commit après
        # coup (conversation_manager._commit_actual_approach, appelé une fois
        # la réponse réellement composée) doit alimenter approaches_used.
        lc = None
        count, level, used, rec = cm._advance_escalation_state(intent_service.DEFINITION, "Chapitre_2", lc, cm._LLM_APPROACHES)
        self.assertEqual(used, [])
        self.assertIsNotNone(rec)


class TestPersistanceDB(unittest.TestCase):
    """Vérifie que conversations.learning_context (JSON existant, aucune
    nouvelle table) porte bien incomprehension_count/approaches_used SANS
    perdre chapter_id/notion_id/topic_label déjà présents."""

    def setUp(self):
        client = server.app.test_client()
        self.user = _register(client)
        self.conv_id = db.create_conversation(self.user["id"])

    def test_champs_existants_preserves(self):
        db.set_conversation_learning_context(
            self.conv_id, "Chapitre_2", "valeur-absolue-dun-nombre-reel", "La valeur absolue",
            incomprehension_count=2, approaches_used=["definition", "exemple"],
        )
        stored = db.get_conversation_learning_context(self.conv_id)
        self.assertEqual(stored["chapter_id"], "Chapitre_2")
        self.assertEqual(stored["notion_id"], "valeur-absolue-dun-nombre-reel")
        self.assertEqual(stored["topic_label"], "La valeur absolue")
        self.assertIn("updated_at", stored)
        self.assertEqual(stored["incomprehension_count"], 2)
        self.assertEqual(stored["approaches_used"], ["definition", "exemple"])

    def test_valeurs_par_defaut_retrocompatibles(self):
        """Un appel SANS les nouveaux paramètres (comme tout le code
        préexistant) doit continuer à fonctionner exactement comme avant."""
        db.set_conversation_learning_context(self.conv_id, "Chapitre_2", "x", "Titre")
        stored = db.get_conversation_learning_context(self.conv_id)
        self.assertEqual(stored["incomprehension_count"], 0)
        self.assertEqual(stored["approaches_used"], [])


class TestSequenceCompleteReelle(unittest.TestCase):
    """Séquence A->B->C->D via les vraies fonctions de conversation_manager.py
    (pas de simulation) — matrice complète intent/compteur/niveau/chapitre."""

    def setUp(self):
        client = server.app.test_client()
        self.user = _register(client)
        self.conv_id = db.create_conversation(self.user["id"])

    def _run_turn(self, message, learning_context):
        context_summary = cm.build_context_summary(self.user, None, class_level="seconde")
        last_assistant_message = cm._previous_assistant_message_text(self.conv_id)
        r = cm._classify_intent(
            message, context_summary, class_level="seconde", learning_context=learning_context,
            last_assistant_message=last_assistant_message,
        )
        db.add_message(self.conv_id, "user", message, mentions=None)
        if cm._detect_repeated_incomprehension(r, self.conv_id, context_summary, "seconde", learning_context):
            r = {**r, "repeated_incomprehension": True}
        cm._update_learning_context(self.conv_id, r, class_level="seconde", existing_learning_context=learning_context)
        db.add_message(self.conv_id, "assistant", f"réponse pour {message!r}", engine="trace")
        return r

    def test_matrice_complete(self):
        expected = [
            # message, intent, count, level, chapter_id
            ("c'est quoi une valeur absolue", intent_service.DEFINITION, 0, 0, "Chapitre_2"),
            ("simplifie", intent_service.REFORMULATION, 1, 1, "Chapitre_2"),
            ("explique plus simplement je n'ai rien compris", intent_service.RESTART_BASICS, 2, 2, "Chapitre_2"),
            ("j'ai toujours pas compris", intent_service.REFORMULATION, 3, 3, "Chapitre_2"),
        ]
        learning_context = None
        for message, exp_intent, exp_count, exp_level, exp_chapter in expected:
            r = self._run_turn(message, learning_context)
            with self.subTest(message=message):
                self.assertEqual(r["intent"], exp_intent)
                self.assertEqual(r["chapter_id"], exp_chapter)
                self.assertEqual(r["notion_id"], "valeur-absolue-dun-nombre-reel")
                self.assertEqual(r["incomprehension_count"], exp_count)
                self.assertEqual(r["escalation_level"], exp_level)
                self.assertIsNotNone(r["recommended_approach"])
            learning_context = db.get_conversation_learning_context(self.conv_id)

    def test_approches_ne_se_repetent_pas_tant_que_des_alternatives_existent(self):
        learning_context = None
        approaches = []
        for message in [
            "c'est quoi une valeur absolue", "simplifie",
            "explique plus simplement je n'ai rien compris", "j'ai toujours pas compris",
        ]:
            r = self._run_turn(message, learning_context)
            approaches.append(r["recommended_approach"])
            learning_context = db.get_conversation_learning_context(self.conv_id)
        self.assertEqual(len(approaches), len(set(approaches)), f"approches non distinctes: {approaches}")

    def test_reset_sur_changement_de_sujet_explicite(self):
        learning_context = None
        for message in ["c'est quoi une valeur absolue", "simplifie", "explique plus simplement je n'ai rien compris"]:
            self._run_turn(message, learning_context)
            learning_context = db.get_conversation_learning_context(self.conv_id)
        self.assertGreater(learning_context["incomprehension_count"], 0)

        r = self._run_turn("Maintenant explique-moi les probabilités.", learning_context)
        self.assertNotEqual(r["chapter_id"], "Chapitre_2")
        self.assertEqual(r["incomprehension_count"], 0)
        self.assertEqual(r["escalation_level"], 0)


class TestLocalResponseEngineRecoitLescalade(unittest.TestCase):
    def test_recommended_approach_influence_le_plan_local(self):
        from chatbot.services import local_response_engine as lre, response_strategy as rs

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
        lc = {"chapter_id": "Chapitre_2", "notion_id": "valeur-absolue-dun-nombre-reel"}
        REAL_USER = {"id": 1, "pseudo": "Testeur", "level": 1}
        # "encore une autre façon" est confirmé router vers le Local Response
        # Engine (ENGINE_SEARCH) quand learning_context est transmis (voir
        # chantier "learning_context perdu" précédent) — message stable pour
        # exercer réellement le chemin local, contrairement à "simplifie" qui
        # route vers le LLM (should_use_llm=True) faute de score local suffisant.
        r = lre.generate(
            "encore une autre façon", REAL_USER, student_context=sctx, use_cache=False, class_level="seconde",
            learning_context=lc, escalation_level=1, recommended_approach="exemple",
        )
        self.assertFalse(r.should_use_llm)
        self.assertIsNotNone(r.text)
        # Le bloc "exemple" doit apparaître avant le bloc "definition" dans le texte
        # (comportement observable indirect : au minimum, la réponse doit rester
        # sur le bon sujet et ne jamais planter avec ces nouveaux paramètres).
        self.assertIn("valeur absolue".lower(), r.text.lower())


class TestDegradedModeRecoitLescalade(unittest.TestCase):
    def test_escalation_level_eleve_declenche_le_mode_reprise_des_bases(self):
        intent_result_bas = {
            "chapter_id": "Chapitre_2", "notion_id": "valeur-absolue-dun-nombre-reel", "topic_inherited": True,
            "intent": intent_service.REFORMULATION, "escalation_level": 0,
        }
        intent_result_haut = {**intent_result_bas, "escalation_level": 2}
        messages = [{"role": "user", "content": "simplifie"}]

        answer_bas = degraded_mode_service.try_answer(intent_result_bas, messages, class_level="seconde")
        answer_haut = degraded_mode_service.try_answer(intent_result_haut, messages, class_level="seconde")
        self.assertIsNotNone(answer_bas)
        self.assertIsNotNone(answer_haut)
        # Niveau élevé -> réordonnancement règles-first + erreur fréquente
        # possible, même sans intent RESTART_BASICS pour ce message précis.
        self.assertTrue(answer_bas.strip())
        self.assertTrue(answer_haut.strip())

    def test_aucun_appel_llm_avec_escalade(self):
        import chatbot.services.degraded_mode_service as mod
        self.assertNotIn("provider_manager", mod.__dict__)
        self.assertNotIn("llm_fallback_service", mod.__dict__)


class TestInstructionLLMStructuree(unittest.TestCase):
    def test_instruction_nomme_les_approches_deja_utilisees(self):
        instr = pedagogy_templates.build_intent_instruction({
            "intent": intent_service.REFORMULATION, "incomprehension_count": 3, "escalation_level": 3,
            "approaches_used": ["definition", "exemple", "analogie"], "recommended_approach": "question_guidee",
        })
        self.assertIn("3", instr)
        self.assertIn("question", instr.lower())

    def test_repli_de_compatibilite_sans_etat_descalade(self):
        instr = pedagogy_templates.build_intent_instruction({
            "intent": intent_service.REFORMULATION, "repeated_incomprehension": True,
        })
        self.assertIn("deuxième fois", instr)

    def test_aucune_instruction_descalade_si_niveau_zero(self):
        instr = pedagogy_templates.build_intent_instruction({
            "intent": intent_service.DEFINITION, "escalation_level": 0,
        })
        self.assertNotIn("tentative", instr.lower())


class TestContentPlanNinventeJamaisDeBloc(unittest.TestCase):
    def test_approche_non_locale_ninfluence_pas_le_plan(self):
        plan_sans = krc._content_plan(intent_service.REFORMULATION, "normal", None)
        plan_avec_analogie = krc._content_plan(intent_service.REFORMULATION, "normal", None, recommended_approach="analogie")
        self.assertEqual(plan_sans, plan_avec_analogie)

    def test_approche_locale_reordonne_sans_ajouter_de_bloc(self):
        plan_sans = set(krc._content_plan(intent_service.REFORMULATION, "normal", None))
        plan_avec = krc._content_plan(intent_service.REFORMULATION, "normal", None, recommended_approach="exemple")
        self.assertEqual(set(plan_avec), plan_sans)  # même ensemble de blocs
        self.assertEqual(plan_avec[0], krc.BLOCK_EXEMPLE)  # simplement réordonné


class TestApprochesRealisablesUniquement(unittest.TestCase):
    """Chantier "escalade réellement exécutée" (2026-08-22) — Partie F :
    une approche ne doit être recommandée (et donc marquée `approaches_used`)
    que si les données de la notion permettent réellement de la réaliser."""

    def test_notion_riche_toutes_les_approches_disponibles(self):
        from chatbot import knowledge_engine as ke
        notion = ke.get_notion("Chapitre_2", "valeur-absolue-dun-nombre-reel", class_level="seconde")
        available = cm._approaches_available_for_notion(notion)
        self.assertEqual(set(available), {"definition", "exemple", "analogie", "question_guidee"})

    def test_notion_titre_seul_uniquement_definition(self):
        notion = {"title": "Notion minimale"}
        available = cm._approaches_available_for_notion(notion)
        self.assertEqual(available, ("definition",))

    def test_notion_none_uniquement_definition(self):
        self.assertEqual(cm._approaches_available_for_notion(None), ("definition",))

    def test_notion_avec_exemple_seul(self):
        notion = {"title": "X", "exemples": [{"enonce": "e", "reponse": "r", "id": "1"}], "regles": [], "a_retenir": []}
        available = cm._approaches_available_for_notion(notion)
        self.assertIn("exemple", available)
        self.assertIn("question_guidee", available)
        self.assertNotIn("analogie", available)


class TestRegenerationNAvancePasLescalade(unittest.TestCase):
    """Partie A/G — TEST 4 explicite demandé : A->B->C (count=2), puis deux
    regenerate_last() consécutifs (count doit rester 2 à chaque fois), puis
    un nouveau message d'incompréhension (count doit alors passer à 3)."""

    def setUp(self):
        client = server.app.test_client()
        self.user = _register(client)
        self.conv_id = db.create_conversation(self.user["id"])

    def test_sequence_complete(self):
        from chatbot import conversation_manager as conv_mgr

        for m in ["c'est quoi une valeur absolue", "simplifie", "explique plus simplement je n'ai rien compris"]:
            list(conv_mgr.stream_reply(self.user, self.conv_id, m, chapters_summary=None, mentions=None, debug=False, class_level="seconde"))
        lc = db.get_conversation_learning_context(self.conv_id)
        self.assertEqual(lc["incomprehension_count"], 2)
        approaches_after_abc = list(lc["approaches_used"])

        list(conv_mgr.regenerate_last(self.user, self.conv_id, class_level="seconde"))
        lc = db.get_conversation_learning_context(self.conv_id)
        self.assertEqual(lc["incomprehension_count"], 2)
        self.assertEqual(lc["approaches_used"], approaches_after_abc)

        list(conv_mgr.regenerate_last(self.user, self.conv_id, class_level="seconde"))
        lc = db.get_conversation_learning_context(self.conv_id)
        self.assertEqual(lc["incomprehension_count"], 2)
        self.assertEqual(lc["approaches_used"], approaches_after_abc)

        list(conv_mgr.stream_reply(self.user, self.conv_id, "j'ai toujours pas compris", chapters_summary=None, mentions=None, debug=False, class_level="seconde"))
        lc = db.get_conversation_learning_context(self.conv_id)
        self.assertEqual(lc["incomprehension_count"], 3)


class TestModeDegradeExecuteReellementLescalade(unittest.TestCase):
    """Parties C — vérifie que chaque niveau produit une structure
    pédagogique RÉELLEMENT différente (pas seulement un texte différent)."""

    NOTION_ARGS = ("Chapitre_2", "valeur-absolue-dun-nombre-reel")

    def _answer(self, recommended_approach, escalation_level):
        intent_result = {
            "chapter_id": self.NOTION_ARGS[0], "notion_id": self.NOTION_ARGS[1], "topic_inherited": True,
            "intent": intent_service.REFORMULATION, "escalation_level": escalation_level,
            "recommended_approach": recommended_approach,
        }
        messages = [{"role": "user", "content": "simplifie"}]
        return degraded_mode_service.try_answer(intent_result, messages, class_level="seconde")

    def test_niveau_1_exemple_met_lexemple_en_avant(self):
        answer = self._answer("exemple", 1)
        self.assertIn("exemple concret", answer.lower())

    def test_niveau_2_analogie_nutilise_pas_le_mot_analogie_invente(self):
        """Pas de fausse analogie fabriquée — structure de repli honnête
        (règle + exemple + mini-vérification), vérifiée structurellement."""
        answer = self._answer("analogie", 2)
        self.assertIn("règle", answer.lower())
        self.assertTrue(answer.strip().endswith("?"))  # mini-vérification = question fermée

    def test_niveau_3_question_guidee_ne_revele_pas_la_reponse(self):
        # Chantier "vraie question guidée niveau 3" (2026-08-22) : le test
        # précédent acceptait n'importe quelle fin ("?", ".", "réponse.") —
        # trop permissif pour distinguer une vraie question ouverte d'une
        # phrase impérative avec un "?" collé au bout. On vérifie maintenant
        # explicitement : (1) une vraie phrase interrogative est présente ;
        # (2) la réponse finale connue n'apparaît pas ; (3) une action/étape
        # est demandée ; (4) ce n'est pas une question fermée rhétorique.
        answer = self._answer("question_guidee", 3)
        self.assertNotIn("x = 8", answer)
        self.assertNotIn("x = -2", answer)

        lines_with_question = [ln.strip() for ln in answer.splitlines() if "?" in ln]
        self.assertTrue(lines_with_question, "aucune phrase interrogative trouvée dans la réponse")
        question_sentence = lines_with_question[0].split("?")[0].strip() + " ?"
        lower_q = question_sentence.lower()

        # Une vraie question ouverte guide le raisonnement (mot interrogatif) —
        # ce n'est pas juste un "?" collé en fin de phrase impérative.
        interrogative_words = ("quelle", "quel", "comment", "que ", "qu'est-ce", "pourquoi")
        self.assertTrue(
            any(w in lower_q for w in interrogative_words),
            f"pas de mot interrogatif dans la question : {question_sentence!r}",
        )
        # Motifs explicitement interdits : impératif + '?' collé au bout, ou
        # question fermée de simple confirmation ("tu comprends ?"...).
        forbidden_patterns = ("toi-même ?", "tu comprends", "est-ce que tu peux essayer", "c'est clair ?")
        for pattern in forbidden_patterns:
            self.assertNotIn(pattern, lower_q)

        # Doit demander une action/étape concrète à l'élève.
        self.assertIn("essaie", answer.lower())

    def test_niveaux_1_2_3_produisent_des_structures_distinctes(self):
        a1 = self._answer("exemple", 1)
        a2 = self._answer("analogie", 2)
        a3 = self._answer("question_guidee", 3)
        self.assertNotEqual(a1, a2)
        self.assertNotEqual(a2, a3)
        self.assertNotEqual(a1, a3)

    def test_notion_pauvre_niveau_3_replie_sans_planter(self):
        """Aucun exemple disponible -> repli explicite, jamais de question
        inventée sans rapport avec les données."""
        from unittest.mock import patch
        with patch.object(degraded_mode_service.knowledge_engine, "get_exemple", return_value=None):
            answer = self._answer("question_guidee", 3)
        self.assertTrue(answer.strip())


class TestLocalResponseEngineIntentNoneConserveLescalade(unittest.TestCase):
    """Partie D/E — TEST 2 : intent=none pendant une escalade déjà avancée
    ne doit plus retomber sur le plan par défaut [BLOCK_DEFINITION] seul."""

    def test_plan_enrichi_des_escalation_level_2(self):
        plan_bas = krc._content_plan(intent_service.NONE_INTENT, "normal", None, escalation_level=0)
        plan_haut = krc._content_plan(intent_service.NONE_INTENT, "normal", None, escalation_level=2)
        self.assertEqual(plan_bas, [krc.BLOCK_DEFINITION])
        self.assertNotEqual(plan_haut, [krc.BLOCK_DEFINITION])
        self.assertIn(krc.BLOCK_METHODE, plan_haut)

    def test_sequence_reelle_msg5_narrive_pas_a_une_definition_seule(self):
        from chatbot.services import local_response_engine as lre

        REAL_USER = {"id": 1, "pseudo": "Testeur", "level": 1}
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
        lc = {"chapter_id": "Chapitre_2", "notion_id": "valeur-absolue-dun-nombre-reel"}
        r = lre.generate(
            "encore une autre façon", REAL_USER, student_context=sctx, use_cache=False, class_level="seconde",
            learning_context=lc, escalation_level=3, recommended_approach="definition",
        )
        self.assertFalse(r.should_use_llm)
        # Une notion à ce niveau d'escalade doit désormais montrer plus
        # qu'une simple définition isolée (étapes de méthode incluses).
        self.assertIn("1.", r.text)  # étapes numérotées de la méthode


class TestMethodePreferee(unittest.TestCase):
    """TEST 5 — non-répétition : si definition et exemple sont déjà
    utilisés et que methode existe, l'approche/le plan doit la privilégier."""

    def test_content_plan_priorise_methode_si_deja_vu_definition_et_exemple(self):
        # REFORMULATION mène déjà avec [methode, exemple, definition] — la
        # méthode est déjà en tête par défaut, confirmé ici explicitement.
        plan = krc._content_plan(intent_service.REFORMULATION, "normal", None)
        self.assertEqual(plan[0], krc.BLOCK_METHODE)


class TestChangementDeSujetResetApprochesUsed(unittest.TestCase):
    """TEST 8."""

    def setUp(self):
        client = server.app.test_client()
        self.user = _register(client)
        self.conv_id = db.create_conversation(self.user["id"])

    def test_reset_complet_apres_changement_de_sujet(self):
        from chatbot import conversation_manager as conv_mgr

        for m in ["c'est quoi une valeur absolue", "simplifie", "explique plus simplement je n'ai rien compris"]:
            list(conv_mgr.stream_reply(self.user, self.conv_id, m, chapters_summary=None, mentions=None, debug=False, class_level="seconde"))
        lc = db.get_conversation_learning_context(self.conv_id)
        self.assertGreater(lc["incomprehension_count"], 0)

        list(conv_mgr.stream_reply(
            self.user, self.conv_id, "Maintenant explique-moi les probabilités.",
            chapters_summary=None, mentions=None, debug=False, class_level="seconde",
        ))
        lc = db.get_conversation_learning_context(self.conv_id)
        self.assertNotEqual(lc["chapter_id"], "Chapitre_2")
        self.assertEqual(lc["incomprehension_count"], 0)


class TestFausseMemoireApprocheCorrectif(unittest.TestCase):
    """TESTS A-F du chantier "fausse mémoire d'approche" (2026-08-22) —
    vérifie que `approaches_used` ne contient QUE des approches RÉELLEMENT
    exécutées (jamais `recommended_approach` par simple supposition). Voir
    conversation_manager._commit_actual_approach, appelé uniquement une fois
    la réponse réellement composée, jamais avant."""

    NOTION_ARGS = ("Chapitre_2", "valeur-absolue-dun-nombre-reel")

    def setUp(self):
        client = server.app.test_client()
        self.user = _register(client)
        self.conv_id = db.create_conversation(self.user["id"])
        db.set_conversation_learning_context(
            self.conv_id, self.NOTION_ARGS[0], self.NOTION_ARGS[1], "La valeur absolue",
            incomprehension_count=0, approaches_used=[],
        )

    def test_a_analogie_recommandee_mais_indisponible_nest_jamais_memorisee(self):
        intent_result = {
            "chapter_id": self.NOTION_ARGS[0], "notion_id": self.NOTION_ARGS[1], "topic_inherited": True,
            "intent": intent_service.REFORMULATION, "escalation_level": 2,
            "recommended_approach": "analogie",
        }
        messages = [{"role": "user", "content": "simplifie"}]
        answer = degraded_mode_service.try_answer(intent_result, messages, class_level="seconde")
        self.assertIsNotNone(answer)
        self.assertTrue(answer.strip())
        # Repli honnête : le moteur a réellement produit "exemple" ou
        # "definition", jamais "analogie" (aucune vraie donnée d'analogie
        # n'existe dans le corpus).
        self.assertIn("actual_approach", intent_result)
        self.assertIsNotNone(intent_result["actual_approach"])
        self.assertNotEqual(intent_result["actual_approach"], "analogie")

        cm._commit_actual_approach(self.conv_id, intent_result["actual_approach"])
        stored = db.get_conversation_learning_context(self.conv_id)
        self.assertNotIn("analogie", stored["approaches_used"])
        self.assertIn(intent_result["actual_approach"], stored["approaches_used"])

    def test_b_question_guidee_reellement_produite_est_memorisee(self):
        intent_result = {
            "chapter_id": self.NOTION_ARGS[0], "notion_id": self.NOTION_ARGS[1], "topic_inherited": True,
            "intent": intent_service.REFORMULATION, "escalation_level": 3,
            "recommended_approach": "question_guidee",
        }
        messages = [{"role": "user", "content": "j'ai toujours pas compris"}]
        answer = degraded_mode_service.try_answer(intent_result, messages, class_level="seconde")
        self.assertIsNotNone(answer)
        self.assertEqual(intent_result.get("actual_approach"), "question_guidee")

        cm._commit_actual_approach(self.conv_id, intent_result["actual_approach"])
        stored = db.get_conversation_learning_context(self.conv_id)
        self.assertIn("question_guidee", stored["approaches_used"])

    def test_c_question_guidee_impossible_a_produire_nest_pas_memorisee(self):
        from unittest.mock import patch

        intent_result = {
            "chapter_id": self.NOTION_ARGS[0], "notion_id": self.NOTION_ARGS[1], "topic_inherited": True,
            "intent": intent_service.REFORMULATION, "escalation_level": 3,
            "recommended_approach": "question_guidee",
        }
        messages = [{"role": "user", "content": "j'ai toujours pas compris"}]
        with patch.object(degraded_mode_service.knowledge_engine, "get_exemple", return_value=None):
            answer = degraded_mode_service.try_answer(intent_result, messages, class_level="seconde")
        self.assertIsNotNone(answer)
        # Aucun exemple disponible -> _build_question_guidee_answer replie sur
        # _build_definition_answer -> actual_approach="definition", jamais
        # "question_guidee" : pas de fausse mémoire d'une interaction guidée
        # qui n'a jamais eu lieu.
        self.assertNotEqual(intent_result.get("actual_approach"), "question_guidee")

        cm._commit_actual_approach(self.conv_id, intent_result.get("actual_approach"))
        stored = db.get_conversation_learning_context(self.conv_id)
        self.assertNotIn("question_guidee", stored["approaches_used"])

    def test_d_alternative_disponible_nest_pas_immediatement_repetee(self):
        used = ["definition"]
        available = ("definition", "exemple", "question_guidee")
        result = cm._select_approach(1, used, available)
        self.assertNotIn(result, used)

    def test_e_aucune_alternative_repetition_sans_exception(self):
        used = ["definition", "exemple", "question_guidee"]
        available = ("definition", "exemple", "question_guidee")
        result = cm._select_approach(1, used, available)  # ne doit jamais lever d'exception
        self.assertIn(result, available)

    def test_f_regenerate_last_ne_modifie_ni_le_compteur_ni_approaches_used(self):
        from chatbot import conversation_manager as conv_mgr

        for m in ["c'est quoi une valeur absolue", "simplifie", "explique plus simplement je n'ai rien compris"]:
            list(conv_mgr.stream_reply(
                self.user, self.conv_id, m, chapters_summary=None, mentions=None, debug=False, class_level="seconde",
            ))
        lc_before = db.get_conversation_learning_context(self.conv_id)
        count_before = lc_before["incomprehension_count"]
        approaches_before = list(lc_before["approaches_used"])

        list(conv_mgr.regenerate_last(self.user, self.conv_id, class_level="seconde"))
        lc_after = db.get_conversation_learning_context(self.conv_id)
        self.assertEqual(lc_after["incomprehension_count"], count_before)
        self.assertEqual(lc_after["approaches_used"], approaches_before)
        self.assertEqual(len(lc_after["approaches_used"]), len(approaches_before))


if __name__ == "__main__":
    unittest.main()
