"""
Suite fonctionnelle du routage chatbot : pour chaque catégorie de demande
demandée (cours/définition/méthode/exemple/exercice/plusieurs exercices/quiz/
@Cours/@Exercices/@Dashboard), vérifie que le MÉCANISME RÉEL qui la traite
aujourd'hui produit le bon résultat.

Important — honnêteté du périmètre : certaines catégories demandées ne
correspondent PAS (encore) à une intention dédiée dans le pipeline actuel
("méthode", "plusieurs exercices"). Chaque test documente explicitement quel
mécanisme réel est exercé, plutôt que de fabriquer une assertion sur une
fonctionnalité qui n'existe pas encore (ces écarts sont repris dans le
rapport final, pas cachés ici).
"""
import unittest
from unittest.mock import patch

from chatbot import knowledge_engine
from chatbot.services import intent_service, local_knowledge_service, mentions_service, search_service


class TestDemandeDeCoursEtDefinition(unittest.TestCase):
    """"Demande de cours"/"demande de définition" : traitées AVANT même la
    classification d'intention, par knowledge_engine.try_answer_definition
    (voir conversation_manager.py::_try_internal_answer) — TF-IDF sur les
    notions de cours, indépendant de canonical_ids/topic_crosswalk (les
    cours ont déjà leur propre slug stable)."""

    def test_definition_directe(self):
        answer = knowledge_engine.try_answer_definition("C'est quoi une puissance ?")
        self.assertIsNotNone(answer)
        self.assertIn("Les puissances", answer)

    def test_definition_insensible_a_la_casse(self):
        answer = knowledge_engine.try_answer_definition("DÉFINITION DE LA PUISSANCE")
        self.assertIsNotNone(answer)

    def test_limite_connue_declencheur_sensible_aux_accents(self):
        """Limitation pré-existante découverte par cette suite (indépendante
        de canonical_ids) : DEFINITION_RE (knowledge_engine.py) est
        insensible à la casse (re.IGNORECASE) mais PAS aux accents — "
        "Definition" (sans accent) ne déclenche pas la détection, contrairement
        à la recherche de notion elle-même (TfidfVectorizer, strip_accents).
        Documenté ici comme piste d'amélioration, pas corrigé dans ce chantier
        (hors périmètre : ceci concerne le déclencheur de définition, pas
        l'identification canonique de chapitre/notion)."""
        self.assertIsNone(knowledge_engine.try_answer_definition("Definition de la puissance"))

    def test_limite_connue_aucune_tolerance_aux_fautes_de_frappe(self):
        """Limitation pré-existante : try_answer_definition n'a AUCUN repli
        flou (contrairement à canonical_ids.resolve_topic_id) — un token qui
        ne matche pas exactement (après accents/pluriel) ne remonte aucune
        notion, même proche. Recommandation pour un futur chantier : faire
        retomber ce point d'entrée sur canonical_ids en cas d'échec TF-IDF."""
        self.assertIsNone(knowledge_engine.try_answer_definition("définition de la puissace"))

    def test_contexte_rag_pour_demande_de_cours_ouverte(self):
        block = knowledge_engine.context_block("puissance")
        self.assertIn("Les puissances", block)


class TestDemandeDeMethode(unittest.TestCase):
    """Comblé par l'Intent Engine v2 (Response Engine v2, Phase 1) : METHODE
    est désormais une intention dédiée — "Comment résoudre..."/"Quelle est
    la méthode..." classifiaient NONE_INTENT avant cette phase (voir
    l'ancienne version de ce test, chantier KE v2)."""

    def test_intent_methode_reconnu(self):
        for phrase in ["Comment résoudre une puissance ?", "Quelle est la méthode pour simplifier une puissance ?"]:
            with self.subTest(phrase=phrase):
                result = intent_service.classify(phrase)
                self.assertEqual(result["intent"], intent_service.METHODE)
                self.assertEqual(result["chapter_id"], "Chapitre_1")

    def test_accesseur_methode_fonctionne(self):
        notion = knowledge_engine.get_notion("Chapitre_1", "puissances-entieres-relatives")
        etapes = knowledge_engine.get_methode_etapes(notion, niveau="debutant")
        self.assertEqual(len(etapes), 4)


class TestDemandeDExemple(unittest.TestCase):
    def test_intent_et_chapitre_corrects(self):
        result = intent_service.classify("Donne-moi un exemple sur les puissances")
        self.assertEqual(result["intent"], intent_service.EXEMPLE)
        self.assertEqual(result["chapter_id"], "Chapitre_1")

    def test_accesseur_exemple_par_difficulte(self):
        notion = knowledge_engine.get_notion("Chapitre_1", "puissances-entieres-relatives")
        exemple = knowledge_engine.get_exemple(notion, difficulte="difficile")
        self.assertEqual(exemple["titre"], "Exemple 3")


class TestDemandeDExercice(unittest.TestCase):
    def test_intent_et_reponse_locale(self):
        result = intent_service.classify("Donne-moi un exercice sur les puissances")
        self.assertEqual(result["intent"], intent_service.EXERCICE)
        self.assertEqual(result["chapter_id"], "Chapitre_1")
        answer = local_knowledge_service.try_answer(
            result, user={"id": "no-such-user"}, context_summary={}, chatbot_settings={},
            user_message="Donne-moi un exercice sur les puissances",
        )
        self.assertIsNotNone(answer)
        self.assertIn("exercice", answer.lower())

    def test_recherche_scopee_par_topic_id_exact(self):
        """Chemin canonique (search_service.exercises_by_topic) — remplace la
        recherche floue quand le topic_id est déjà connu."""
        results = search_service.exercises_by_topic("Chapitre_1", "puissances-entieres-relatives", limit=5)
        self.assertGreater(len(results), 0)
        for r in results:
            self.assertEqual(r["chapter_id"], "Chapitre_1")
            self.assertEqual(r["topic_id"], "puissances-entieres-relatives")


class TestDemandeDePlusieursExercices(unittest.TestCase):
    """Comblé par l'Intent Engine v2 (Response Engine v2, Phase 1) :
    EXERCICE_RE reconnaît maintenant "3 exercices"/"plusieurs exercices", et
    `classify()` expose un champ `quantity` dédié. L'exécution réelle de
    "plusieurs exercices" (Exercise Engine) reste un chantier futur — seule
    l'INTENTION est du ressort de cette phase."""

    def test_intent_et_quantite_reconnus(self):
        result = intent_service.classify("Donne-moi 3 exercices sur les puissances")
        self.assertEqual(result["intent"], intent_service.EXERCICE)
        self.assertEqual(result["quantity"], 3)

    def test_quantite_plusieurs(self):
        result = intent_service.classify("Donne-moi plusieurs exemples sur les puissances")
        self.assertEqual(result["intent"], intent_service.EXEMPLE)
        self.assertEqual(result["quantity"], 3)

    def test_quantite_absente_par_defaut(self):
        result = intent_service.classify("Donne-moi un exercice sur les puissances")
        self.assertIsNone(result["quantity"])

    def test_capacite_sous_jacente_existe_au_niveau_service(self):
        results = search_service.search_exercises_in_chapter("Chapitre_1", limit=3)
        self.assertEqual(len(results), 3)
        exercise_ids = {r["exercise_id"] for r in results}
        self.assertEqual(len(exercise_ids), 3, "les 3 exercices doivent être distincts")


class TestDemandeDeQuiz(unittest.TestCase):
    """Le quiz est intentionnellement répondu par le LLM (pose une question à
    la fois, cf. pedagogy_templates.py), jamais par le moteur local — on
    vérifie que la classification est correcte ET que local_knowledge_service
    laisse bien la main au LLM (design volontaire, pas un bug)."""

    def test_intent_quiz_correctement_classifie(self):
        result = intent_service.classify("Interroge-moi sur les puissances")
        self.assertEqual(result["intent"], intent_service.QUIZ)
        self.assertEqual(result["chapter_id"], "Chapitre_1")

    def test_local_knowledge_service_ne_repond_pas_au_quiz(self):
        result = intent_service.classify("Interroge-moi sur les puissances")
        answer = local_knowledge_service.try_answer(result, user={"id": "no-such-user"}, context_summary={}, chatbot_settings={})
        self.assertIsNone(answer)


class TestMentionArobase(unittest.TestCase):
    def test_categorie_cours(self):
        result = mentions_service.search_mentions("cours")
        keys = [item.get("key") for item in result["items"] if item.get("item_kind") == "category"]
        self.assertIn("cours", keys)

    def test_categorie_exercices(self):
        result = mentions_service.search_mentions("exercices")
        keys = [item.get("key") for item in result["items"] if item.get("item_kind") == "category"]
        self.assertIn("exercices", keys)

    def test_recherche_de_ressource_exercice_porte_topic_id(self):
        """search_mentions renvoie plusieurs ressources apparentées classées
        par score (comportement normal, pas une recherche exacte) — seul le
        MEILLEUR résultat doit correspondre exactement au sujet demandé."""
        result = mentions_service.search_mentions("puissances entières relatives")
        exercise_items = [
            item for item in result["items"]
            if item.get("item_kind") == "resource" and item.get("type") == search_service.SCOPE_EXERCICES
        ]
        self.assertGreater(len(exercise_items), 0)
        best = max(exercise_items, key=lambda item: item["score"])
        self.assertEqual(best["topic_id"], "puissances-entieres-relatives")

    def test_dashboard_mention_seule_donne_intent_local(self):
        mentions = [{"type": "data", "data_key": "dashboard", "label": "Dashboard"}]
        intent = mentions_service.single_data_mention_intent("@Dashboard", mentions)
        self.assertEqual(intent, intent_service.DASHBOARD)

    @patch("chatbot.services.variable_resolver.read_user_stats")
    @patch("chatbot.services.variable_resolver.read_user_settings")
    @patch("chatbot.context_builder.read_user_stats")
    @patch("chatbot.context_builder.read_user_settings")
    def test_dashboard_repond_localement_avec_donnees_reelles(
        self, mock_cb_settings, mock_cb_stats, mock_vr_settings, mock_vr_stats,
    ):
        """Bout en bout : @Dashboard -> intent DASHBOARD -> réponse composée
        localement (jamais le LLM) avec les vraies données (mockées ici pour
        ne toucher aucun fichier réel de data/user_stats/).

        Note (trouvée en construisant Student Context Resolver v2, Phase 2) :
        `@patch("auth.read_user_stats")` ne mockait PAS réellement ce test —
        context_builder.py et variable_resolver.py font chacun `from auth
        import read_user_stats`, une référence liée à l'import qu'un patch
        sur `auth.read_user_stats` ne modifie pas rétroactivement. Ce test
        passait "par chance" (l'assertion sur "objectif du jour" est vraie
        même avec les données réelles/vides de l'utilisateur fictif). Corrigé
        en patchant les deux modules consommateurs à leur véritable point
        d'import."""
        history = {
            "xp": 0, "badges": [], "series": [],
            "history": [
                {"chapter": "Chapitre_1", "notion": "Puissances entières relatives", "correct": True, "duration_s": 60},
                {"chapter": "Chapitre_1", "notion": "Puissances entières relatives", "correct": True, "duration_s": 60},
            ],
        }
        settings = {"chatbot": {}, "favorites": [], "language": "fr"}
        mock_cb_stats.return_value = history
        mock_vr_stats.return_value = history
        mock_cb_settings.return_value = settings
        mock_vr_settings.return_value = settings
        from chatbot import context_builder
        user = {"id": "fake-test-user", "pseudo": "Testeur", "level": 2}
        context_summary = context_builder.build_context_summary(user)
        intent_result = {"intent": intent_service.DASHBOARD, "chapter_id": None, "notion_id": None, "difficulty": None, "simplify": False}
        answer = local_knowledge_service.try_answer(intent_result, user, context_summary, {})
        self.assertIsNotNone(answer)
        # "objectif du jour" est le seul segment commun aux 3 variantes de
        # template DASHBOARD (template_library.py) — {niveau}/{prenom} ne
        # figurent chacun que dans 2 des 3, une assertion dessus serait non
        # déterministe (response_composer.compose tire une variante au hasard).
        self.assertIn("objectif du jour", answer)


if __name__ == "__main__":
    unittest.main()
