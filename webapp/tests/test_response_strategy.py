"""
Suite de tests du Response Strategy Engine (Phase 3A, Niveau 1) —
`chatbot/services/response_strategy.py`. Ce module n'est PAS branché au
pipeline principal (voir consigne explicite) : tous les tests l'exercent en
isolation, via `decide_strategy(..., student_context=<dict fabriqué>)` pour
la plupart des cas (le Student Context Resolver v2 a déjà sa propre suite,
`test_student_context_resolver.py` — inutile de la re-tester ici), et via de
vrais appels bout en bout (`student_context=None`, résolu réellement) pour
les tests de cache/performance qui doivent refléter un usage réel.
"""
import dataclasses
import time
import unittest
import unittest.mock

from chatbot.services import intent_service, response_strategy as rs
from chatbot.validate_student_context import validate_student_context

REAL_USER = {"id": 1, "pseudo": "Testeur", "level": 1}


def student_context(**overrides):
    """StudentContext minimal mais toujours valide (vérifié par
    validate_student_context) — les tests ne surchargent que ce qui compte
    pour le scénario testé."""
    base = {
        "user_id": 1, "pseudo": "Testeur", "niveau": "Débutant", "niveau_brut": 1,
        "chapitre_courant": None, "topic_courant": None,
        "notions_maitrisees": [], "notions_faibles": [],
        "topics_maitrises": [], "topics_faibles": [],
        "statistiques": {
            "accuracy": 0, "total_exercices": 0,
            "temps_total": "0 h", "temps_jour": "0 h", "temps_semaine": "0 h",
        },
        "dashboard": {
            "objectif_du_jour": None, "chapitres_en_cours": [],
            "meilleur_chapitre": None, "chapitre_le_plus_faible": None,
        },
        "progression": {},
        "preferences": {"langue": "fr", "niveau_explication": "auto", "favoris": []},
        "parametres": {
            "longueur": "normal", "niveau_explication": "auto", "mode": None,
            "memoire_activee": True, "historique_active": True, "provider": None,
            "modele": None, "temperature": 0.6,
        },
        "mentions": [], "historique_conversation": [],
    }
    base.update(overrides)
    return base


class ResponseStrategyTestCase(unittest.TestCase):
    def setUp(self):
        rs.clear_cache()

    def tearDown(self):
        rs.clear_cache()

    def decide(self, message, ctx=None, **kwargs):
        return rs.decide_strategy(
            message, REAL_USER, student_context=ctx if ctx is not None else student_context(),
            use_cache=False, **kwargs,
        )

    def assert_valid_context(self, ctx):
        self.assertEqual(validate_student_context(ctx), [])


class TestStructureImmuable(ResponseStrategyTestCase):
    def test_frozen_leve_une_erreur_a_la_mutation(self):
        strategy = self.decide("Salut")
        with self.assertRaises(dataclasses.FrozenInstanceError):
            strategy.engine = "autre_chose"

    def test_champs_attendus_presents(self):
        strategy = self.decide("Salut")
        for field in (
            "source", "engine", "confidence", "intent", "chapter_id", "topic_id",
            "quantity", "difficulty", "mode", "should_use_llm", "fallback", "explanation",
        ):
            self.assertTrue(hasattr(strategy, field), f"champ manquant : {field}")

    def test_should_use_llm_coherent_avec_engine(self):
        for message in ["Salut", "Resous 2x + 4 = 10", "C'est quoi une puissance ?", "Question totalement inedite sur un sujet hors programme"]:
            with self.subTest(message=message):
                strategy = self.decide(message)
                self.assertEqual(strategy.should_use_llm, strategy.engine == rs.ENGINE_LLM)

    def test_fallback_coherent_avec_engine(self):
        strategy_local = self.decide("Salut")
        self.assertEqual(strategy_local.fallback, rs.ENGINE_LLM)
        strategy_llm = self.decide("Raconte-moi une blague sur les licornes qui font du velo")
        self.assertIsNone(strategy_llm.fallback)


class TestPrioriteDesMoteurs(ResponseStrategyTestCase):
    """Ordre exact demandé : Math > Rule > Knowledge > Dashboard > Search >
    Exercise > Composer > Quiz > Recommendation > LLM."""

    def test_math_engine_priorite_sur_tout_le_reste(self):
        strategy = self.decide("Resous 2x + 4 = 10")
        self.assertEqual(strategy.engine, rs.ENGINE_MATH)

    def test_rule_engine_priorite_sur_knowledge_et_llm(self):
        strategy = self.decide("Salut")
        self.assertEqual(strategy.engine, rs.ENGINE_RULE)

    def test_knowledge_engine_pour_une_definition(self):
        strategy = self.decide("C'est quoi une puissance ?")
        self.assertEqual(strategy.engine, rs.ENGINE_KNOWLEDGE)

    def test_dashboard_pour_intent_donnee_locale(self):
        strategy = self.decide("Quelle est ma progression ?")
        self.assertEqual(strategy.engine, rs.ENGINE_DASHBOARD)

    def test_search_service_grounding_generique(self):
        """"Les puissances" ne déclenche ni définition (pas de "c'est quoi"),
        ni aucun intent dédié, mais un match TF-IDF net existe (score 0.51 >>
        seuil 0.12) — Search Service doit trancher avant le LLM."""
        strategy = self.decide("Les puissances")
        self.assertEqual(strategy.engine, rs.ENGINE_SEARCH)
        self.assertEqual(strategy.chapter_id, "Chapitre_1")
        self.assertEqual(strategy.topic_id, "puissances-entieres-relatives")

    def test_exercise_engine_reserve_capacite_sondee_via_search_service(self):
        strategy = self.decide("Donne-moi un exercice sur les puissances")
        self.assertEqual(strategy.engine, rs.ENGINE_EXERCISE)
        self.assertEqual(strategy.chapter_id, "Chapitre_1")

    def test_llm_en_dernier_recours(self):
        strategy = self.decide("Raconte-moi une blague sur les licornes qui font du velo")
        self.assertEqual(strategy.engine, rs.ENGINE_LLM)
        self.assertEqual(strategy.source, rs.SOURCE_LLM)

    def test_priorite_verifiee_par_injection_de_sondes(self):
        """Vérifie l'ORDRE lui-même (pas seulement un cas réel) en simulant
        artificiellement la disponibilité de plusieurs moteurs à la fois."""
        with unittest.mock.patch.object(rs, "_probe_math_engine", return_value=True), \
             unittest.mock.patch.object(rs, "_probe_rule_engine", return_value=True), \
             unittest.mock.patch.object(rs, "_probe_knowledge_engine", return_value=True):
            strategy = self.decide("peu importe le message")
            self.assertEqual(strategy.engine, rs.ENGINE_MATH, "Math Engine doit gagner même si Rule/Knowledge sont aussi disponibles")

        with unittest.mock.patch.object(rs, "_probe_math_engine", return_value=False), \
             unittest.mock.patch.object(rs, "_probe_rule_engine", return_value=True), \
             unittest.mock.patch.object(rs, "_probe_knowledge_engine", return_value=True):
            strategy = self.decide("peu importe le message")
            self.assertEqual(strategy.engine, rs.ENGINE_RULE, "Rule Engine doit gagner sur Knowledge Engine si Math est indisponible")


class TestClarification(ResponseStrategyTestCase):
    def test_message_incomprehensible_prime_sur_tout(self):
        for message in ["......", "aaaa", ""]:
            with self.subTest(message=message):
                strategy = self.decide(message)
                self.assertEqual(strategy.engine, rs.ENGINE_CLARIFICATION)
                self.assertFalse(strategy.should_use_llm)
                self.assertIsNone(strategy.fallback)
                self.assertEqual(strategy.confidence, 100)


class TestToutesLesIntentions(ResponseStrategyTestCase):
    """Chaque intent reconnu par l'Intent Engine v2 doit produire une
    décision sans exception, avec `intent` correctement reporté."""

    MESSAGES_PAR_INTENT = {
        intent_service.EXERCICE: "Donne-moi un exercice sur les puissances",
        intent_service.EXEMPLE: "Donne-moi un exemple sur les puissances",
        intent_service.EXPLICATION: "Explique-moi les puissances",
        intent_service.QUIZ: "Interroge-moi sur les puissances",
        intent_service.FICHE: "Fais-moi une fiche de synthèse sur les puissances",
        intent_service.CORRECTION: "Corrige mon exercice sur les puissances",
        intent_service.RESTART_BASICS: "Je n'ai rien compris, reprenons depuis le début",
        intent_service.FORMULE: "Quelle est la formule de la puissance ?",
        intent_service.PROGRESSION: "Quelle est ma progression ?",
        intent_service.STATISTIQUE: "Quelles sont mes statistiques ?",
        intent_service.DASHBOARD: "Montre-moi le tableau de bord",
        intent_service.PROFIL: "C'est quoi mon profil ?",
        intent_service.PARAMETRES: "Quels sont mes paramètres actifs ?",
        intent_service.SERIE: "Quelle est ma série en cours ?",
        intent_service.DEFINITION: "Que veut dire puissance ?",
        intent_service.COURS: "Montre-moi le cours sur les puissances",
        intent_service.RESUME: "Fais-moi un résumé sur les puissances",
        intent_service.METHODE: "Quelle est la méthode pour résoudre une puissance ?",
        intent_service.PROPRIETE: "Quelle est la propriété de la puissance ?",
        intent_service.DEMONSTRATION: "Démontre que la puissance est correcte",
        intent_service.INDICE: "Donne-moi un indice sur les puissances",
        intent_service.RAPPEL: "Rappelle-moi la puissance",
        intent_service.REVISION: "Je veux réviser les puissances",
        intent_service.REFORMULATION: "Explique autrement les puissances",
    }

    def test_toutes_les_intentions_produisent_une_decision_sans_exception(self):
        for intent, message in self.MESSAGES_PAR_INTENT.items():
            with self.subTest(intent=intent, message=message):
                strategy = self.decide(message)
                self.assertIsInstance(strategy, rs.ResponseStrategy)
                self.assertIn(strategy.engine, rs.PRIORITY_ORDER + [rs.ENGINE_CLARIFICATION])

    def test_none_intent_ne_plante_pas(self):
        strategy = self.decide("Bonjour comment ça va aujourd'hui")
        self.assertIsInstance(strategy, rs.ResponseStrategy)


class TestMentions(ResponseStrategyTestCase):
    def test_mention_donnee_seule_devient_intent_dashboard(self):
        mentions = [{"type": "data", "data_key": "dashboard", "label": "Dashboard"}]
        strategy = self.decide("@Dashboard", mentions=mentions)
        self.assertEqual(strategy.intent, intent_service.DASHBOARD)
        self.assertEqual(strategy.engine, rs.ENGINE_DASHBOARD)

    def test_mention_progression_seule(self):
        mentions = [{"type": "data", "data_key": "progression", "label": "Progression"}]
        strategy = self.decide("@Progression", mentions=mentions)
        self.assertEqual(strategy.intent, intent_service.PROGRESSION)
        self.assertEqual(strategy.engine, rs.ENGINE_DASHBOARD)

    def test_mention_statistiques_seule(self):
        mentions = [{"type": "data", "data_key": "statistiques", "label": "Statistiques"}]
        strategy = self.decide("@Statistiques", mentions=mentions)
        self.assertEqual(strategy.intent, intent_service.STATISTIQUE)

    def test_mention_profil_seule(self):
        mentions = [{"type": "data", "data_key": "profil", "label": "Profil"}]
        strategy = self.decide("@Profil", mentions=mentions)
        self.assertEqual(strategy.intent, intent_service.PROFIL)

    def test_mention_parametres_seule(self):
        mentions = [{"type": "data", "data_key": "parametres", "label": "Paramètres"}]
        strategy = self.decide("@Paramètres", mentions=mentions)
        self.assertEqual(strategy.intent, intent_service.PARAMETRES)

    def test_mention_series_seule(self):
        mentions = [{"type": "data", "data_key": "series", "label": "Séries"}]
        strategy = self.decide("@Séries", mentions=mentions)
        self.assertEqual(strategy.intent, intent_service.SERIE)

    def test_mention_ressource_cours_nest_pas_une_mention_donnee_seule(self):
        """Une mention "cours"/"exercices" (type search, pas data) ne
        déclenche pas single_data_mention_intent — la classification
        normale du texte s'applique."""
        mentions = [{"type": "cours", "chapter_id": "Chapitre_1", "notion_id": "puissances-entieres-relatives"}]
        strategy = self.decide("@Cours", mentions=mentions)
        self.assertNotIn(strategy.intent, (intent_service.DASHBOARD, intent_service.PROGRESSION))

    def test_mention_absente_comportement_inchange(self):
        strategy_sans = self.decide("Salut")
        strategy_avec_mentions_vides = self.decide("Salut", mentions=[])
        self.assertEqual(strategy_sans.engine, strategy_avec_mentions_vides.engine)


class TestDifficultes(ResponseStrategyTestCase):
    def test_difficulte_facile_propagee(self):
        strategy = self.decide("Donne-moi un exercice facile sur les puissances")
        self.assertEqual(strategy.difficulty, "easy")

    def test_difficulte_difficile_propagee(self):
        strategy = self.decide("Donne-moi un exercice difficile sur les puissances")
        self.assertEqual(strategy.difficulty, "hard")

    def test_difficulte_absente_par_defaut(self):
        strategy = self.decide("Donne-moi un exercice sur les puissances")
        self.assertIsNone(strategy.difficulty)


class TestModes(ResponseStrategyTestCase):
    def test_mode_source_depuis_student_context(self):
        ctx = student_context(parametres={**student_context()["parametres"], "mode": "professeur"})
        self.assert_valid_context(ctx)
        strategy = self.decide("Salut", ctx=ctx)
        self.assertEqual(strategy.mode, "professeur")

    def test_mode_source_depuis_chatbot_settings_si_absent_du_contexte(self):
        strategy = self.decide("Salut", chatbot_settings={"mode": "rapide"})
        self.assertEqual(strategy.mode, "rapide")

    def test_mode_contexte_prioritaire_sur_chatbot_settings(self):
        ctx = student_context(parametres={**student_context()["parametres"], "mode": "pas_a_pas"})
        self.assert_valid_context(ctx)
        strategy = self.decide("Salut", ctx=ctx, chatbot_settings={"mode": "rapide"})
        self.assertEqual(strategy.mode, "pas_a_pas")

    def test_mode_absent_partout(self):
        strategy = self.decide("Salut")
        self.assertIsNone(strategy.mode)


class TestQuantites(ResponseStrategyTestCase):
    def test_quantite_chiffree(self):
        strategy = self.decide("Donne-moi 3 exercices sur les puissances")
        self.assertEqual(strategy.quantity, 3)

    def test_quantite_plusieurs(self):
        strategy = self.decide("Donne-moi plusieurs exemples sur les puissances")
        self.assertEqual(strategy.quantity, 3)

    def test_quantite_absente_par_defaut(self):
        strategy = self.decide("Donne-moi un exercice sur les puissances")
        self.assertIsNone(strategy.quantity)

    def test_quantite_bornee(self):
        strategy = self.decide("Donne-moi 500 exercices sur les puissances")
        self.assertLessEqual(strategy.quantity, 10)


class TestEleveVideEtAvance(ResponseStrategyTestCase):
    def test_eleve_vide_ne_plante_pas(self):
        ctx = student_context()  # tout à zéro/vide, cas d'un élève neuf
        self.assert_valid_context(ctx)
        strategy = self.decide("Quelle est ma progression ?", ctx=ctx)
        self.assertEqual(strategy.engine, rs.ENGINE_DASHBOARD)
        # Contexte incomplet (pas de chapitre courant, pas d'historique) :
        # le score ne peut pas atteindre le plafond, mais reste positif.
        self.assertGreater(strategy.confidence, 0)
        self.assertLess(strategy.confidence, 100)

    def test_eleve_avance_score_plus_haut(self):
        ctx_vide = student_context()
        ctx_avance = student_context(
            chapitre_courant="Chapitre_1", topic_courant="puissances-entieres-relatives",
            statistiques={
                "accuracy": 92, "total_exercices": 140,
                "temps_total": "12 h", "temps_jour": "0 h 45", "temps_semaine": "3 h",
            },
            historique_conversation=[{"role": "user", "content": "Salut"}, {"role": "assistant", "content": "Salut !"}],
            topics_maitrises=[{"chapter_id": "Chapitre_1", "topic_id": "puissances-entieres-relatives", "label": "Les puissances"}],
        )
        self.assert_valid_context(ctx_avance)
        strategy_vide = self.decide("Quelle est ma progression ?", ctx=ctx_vide)
        strategy_avance = self.decide("Quelle est ma progression ?", ctx=ctx_avance, chatbot_settings={"mode": "professeur"})
        self.assertGreater(strategy_avance.confidence, strategy_vide.confidence)
        self.assertEqual(strategy_avance.confidence, 100)


class TestPlusieursTopicsEtChapitres(ResponseStrategyTestCase):
    def test_plusieurs_topics_faibles_narrivent_pas_a_confondre_la_decision(self):
        ctx = student_context(
            topics_faibles=[
                {"chapter_id": "Chapitre_1", "topic_id": "puissances-entieres-relatives", "label": "Les puissances"},
                {"chapter_id": "Chapitre_2", "topic_id": "comparaison", "label": "Comparaison"},
            ],
        )
        self.assert_valid_context(ctx)
        strategy = self.decide("Donne-moi un exercice sur les puissances", ctx=ctx)
        self.assertEqual(strategy.engine, rs.ENGINE_EXERCISE)
        self.assertEqual(strategy.chapter_id, "Chapitre_1")

    def test_plusieurs_chapitres_en_cours_repli_sur_le_premier(self):
        ctx = student_context(dashboard={
            **student_context()["dashboard"], "chapitres_en_cours": ["Chapitre_3", "Chapitre_5"],
        })
        self.assert_valid_context(ctx)
        # Message sans sujet identifiable dans le texte -> repli sur le
        # premier chapitre en cours (même règle que intent_service._detect_chapter).
        strategy = self.decide("Donne-moi un exercice", ctx=ctx)
        self.assertEqual(strategy.chapter_id, "Chapitre_3")


class TestAmbiguitesEtMessagesIncomplets(ResponseStrategyTestCase):
    def test_reformulation_prime_sur_explication(self):
        """"Explique autrement" doit être classé REFORMULATION, pas
        EXPLICATION (voir intent_service._INTENT_PATTERNS, ordre volontaire)."""
        strategy = self.decide("Explique autrement les puissances")
        self.assertEqual(strategy.intent, intent_service.REFORMULATION)

    def test_message_vide(self):
        strategy = self.decide("")
        self.assertEqual(strategy.engine, rs.ENGINE_CLARIFICATION)

    def test_message_tres_court_sans_sujet(self):
        strategy = self.decide("Ok")
        self.assertIsInstance(strategy, rs.ResponseStrategy)

    def test_faute_de_frappe_repli_flou_sur_intent(self):
        """"resume moi" (sans trait d'union ni accent) doit encore être
        reconnu via le repli flou de l'Intent Engine v2."""
        strategy = self.decide("resume moi la puissance")
        self.assertEqual(strategy.intent, intent_service.RESUME)

    def test_faute_de_frappe_sur_definition_tombe_sur_search_service(self):
        """Limitation pré-existante et assumée (voir test_chatbot_routing.py) :
        try_answer_definition n'a aucune tolérance aux fautes de frappe. Le
        Strategy Engine ne doit pas planter — il doit retomber plus bas dans
        la chaîne (ici Search Service, qui lui tolère les fautes via TF-IDF)."""
        strategy = self.decide("définition de la puissace")
        self.assertNotEqual(strategy.engine, rs.ENGINE_KNOWLEDGE)
        self.assertIn(strategy.engine, (rs.ENGINE_SEARCH, rs.ENGINE_LLM))


class TestCache(ResponseStrategyTestCase):
    def test_deux_appels_identiques_renvoient_la_meme_decision(self):
        rs.clear_cache()
        s1 = rs.decide_strategy("Salut", REAL_USER, student_context=student_context(), use_cache=True)
        s2 = rs.decide_strategy("Salut", REAL_USER, student_context=student_context(), use_cache=True)
        self.assertFalse(s1.cache_hit)
        self.assertTrue(s2.cache_hit)
        # Toutes les autres valeurs restent identiques (déterminisme).
        self.assertEqual(s1.engine, s2.engine)
        self.assertEqual(s1.confidence, s2.confidence)
        self.assertEqual(s1.explanation, s2.explanation)

    def test_messages_differents_ne_partagent_pas_le_cache(self):
        rs.clear_cache()
        rs.decide_strategy("Salut", REAL_USER, student_context=student_context(), use_cache=True)
        s2 = rs.decide_strategy("Resous 2x + 4 = 10", REAL_USER, student_context=student_context(), use_cache=True)
        self.assertFalse(s2.cache_hit)

    def test_clear_cache_force_un_recalcul(self):
        rs.clear_cache()
        rs.decide_strategy("Salut", REAL_USER, student_context=student_context(), use_cache=True)
        rs.clear_cache()
        s2 = rs.decide_strategy("Salut", REAL_USER, student_context=student_context(), use_cache=True)
        self.assertFalse(s2.cache_hit)

    def test_mode_different_change_la_cle_de_cache(self):
        rs.clear_cache()
        rs.decide_strategy("Salut", REAL_USER, student_context=student_context(), chatbot_settings={"mode": "rapide"}, use_cache=True)
        s2 = rs.decide_strategy("Salut", REAL_USER, student_context=student_context(), chatbot_settings={"mode": "professeur"}, use_cache=True)
        self.assertFalse(s2.cache_hit)

    def test_cache_stats(self):
        rs.clear_cache()
        rs.decide_strategy("Salut", REAL_USER, student_context=student_context(), use_cache=True)
        stats = rs.cache_stats()
        self.assertEqual(stats["entries"], 1)


class TestPerformance(ResponseStrategyTestCase):
    def test_decision_avec_cache_chaud_nettement_plus_rapide(self):
        rs.clear_cache()
        message = "Quelle est ma progression ?"
        ctx = student_context()
        rs.decide_strategy(message, REAL_USER, student_context=ctx, use_cache=True)  # cache froid

        n = 200
        t0 = time.perf_counter()
        for _ in range(n):
            rs.decide_strategy(message, REAL_USER, student_context=ctx, use_cache=True)
        warm_ms = (time.perf_counter() - t0) * 1000 / n

        rs.clear_cache()
        t0 = time.perf_counter()
        for _ in range(n):
            rs.decide_strategy(message, REAL_USER, student_context=ctx, use_cache=False)
            rs.clear_cache()
        cold_ms = (time.perf_counter() - t0) * 1000 / n

        self.assertLess(warm_ms, cold_ms)
        self.assertLess(warm_ms, 1.0, "une décision en cache doit rester sous la milliseconde")


class TestClassLevelPropagation(ResponseStrategyTestCase):
    """class_level vient du StudentContext déjà résolu, jamais recalculé ni
    deviné ici — voir response_strategy._build_strategy()."""

    def test_absent_du_student_context_reste_none(self):
        strategy = self.decide("Salut", ctx=student_context())
        self.assertIsNone(strategy.class_level)

    def test_transporte_tel_quel_depuis_le_student_context(self):
        strategy = self.decide("Salut", ctx=student_context(class_level="premiere"))
        self.assertEqual(strategy.class_level, "premiere")

    def test_definition_premiere_utilise_les_cours_generes_sans_planter(self):
        """Première a désormais des cours générés depuis exercise_bank (voir
        generate_cours_from_bank.py, courses_dir déclaré au registre) : la
        décision doit pouvoir s'appuyer dessus (Knowledge/Search Engine),
        jamais lever d'exception, jamais mélanger avec le contenu Seconde."""
        strategy = self.decide(
            "c'est quoi une suite ?", ctx=student_context(class_level="premiere"),
        )
        self.assertEqual(strategy.class_level, "premiere")
        self.assertIn(strategy.engine, (rs.ENGINE_LLM, rs.ENGINE_KNOWLEDGE, rs.ENGINE_SEARCH))


class TestSecondRoutageNecrasePasLeContexteFiable(ResponseStrategyTestCase):
    """Bug réel confirmé (audit du 2026-08-22) : _probe_search_service()
    (étape 5 de decide_strategy) refait sa PROPRE recherche brute sur le
    message, sans reranking de titre ni connaissance du Current Learning
    Context, et écrasait silencieusement un routage déjà correctement
    protégé par intent_service._detect_chapter (confidence "inherited").
    Cas réel : contexte "Fonction dérivée" (Chapitre_3), message "comment
    dérivé une fonction ?" — la recherche brute renvoie "Fonction
    exponentielle" (Chapitre_5, score 0.157, sous le seuil fort) alors que
    intent_service avait déjà tranché "inherited". Correctif : ne plus
    écraser chapter_id/topic_id quand topic_confidence == "inherited"
    (voir response_strategy.py, étape 5)."""

    PREMIERE_LC = {"chapter_id": "Chapitre_3", "notion_id": "fonction-derivee"}

    def test_search_faible_necrase_pas_learning_context_dans_strategy(self):
        strategy = self.decide(
            "comment dérivé une fonction?",
            ctx=student_context(class_level="premiere"),
            learning_context=self.PREMIERE_LC,
        )
        self.assertEqual(strategy.chapter_id, "Chapitre_3")
        self.assertEqual(strategy.topic_id, "fonction-derivee")

    def test_changement_de_sujet_explicite_reste_possible(self):
        """Un changement de sujet assumé doit toujours pouvoir remplacer le
        contexte — le correctif ne doit pas figer indéfiniment le sujet."""
        strategy = self.decide(
            "Maintenant explique-moi les probabilités.",
            ctx=student_context(class_level="premiere"),
            learning_context=self.PREMIERE_LC,
        )
        self.assertNotEqual(strategy.chapter_id, "Chapitre_3")
        self.assertNotEqual(strategy.topic_id, "fonction-derivee")

    def test_followup_conserve_le_sujet(self):
        ctx = student_context(class_level="premiere")
        for message in ["Pourquoi ?", "Continue.", "Encore.", "Explique autrement."]:
            with self.subTest(message=message):
                strategy = self.decide(message, ctx=ctx, learning_context=self.PREMIERE_LC)
                self.assertEqual(strategy.chapter_id, "Chapitre_3")
                self.assertEqual(strategy.topic_id, "fonction-derivee")

    def test_sans_contexte_la_recherche_fonctionne_normalement(self):
        """Sans Current Learning Context fiable, le correctif ne doit rien
        changer au comportement existant du moteur de recherche."""
        strategy = self.decide(
            "comment dérivé une fonction?",
            ctx=student_context(class_level="premiere"),
            learning_context=None,
        )
        self.assertEqual(strategy.engine, rs.ENGINE_SEARCH)
        self.assertEqual(strategy.chapter_id, "Chapitre_5")
        self.assertEqual(strategy.topic_id, "fonction-exponentielle")

    def test_valeur_absolue_seconde_reste_correcte(self):
        """Cas réel supplémentaire signalé — vérifié en Seconde, seul niveau
        où la notion "Valeur absolue" existe réellement dans le corpus."""
        strategy = self.decide(
            "c'est quoi une valeur absolue", ctx=student_context(class_level="seconde"),
        )
        self.assertEqual(strategy.chapter_id, "Chapitre_2")
        self.assertEqual(strategy.topic_id, "valeur-absolue-dun-nombre-reel")


if __name__ == "__main__":
    unittest.main()
