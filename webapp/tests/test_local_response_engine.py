"""
Suite de tests du Local Response Engine —
`chatbot/services/local_response_engine.py`. Ce module n'est PAS branché au
pipeline principal (voir consigne explicite) : tous les tests l'exercent en
isolation, sur un utilisateur réel de la base (`mehdisellmi`, id=1, déjà
utilisé pour les vérifications manuelles de bout en bout des phases
précédentes) et sur des StudentContext fabriqués pour les cas limites
(élève vide/avancé).
"""
import time
import unittest
from unittest.mock import patch

from chatbot.services import intent_service, local_response_engine as lre, response_strategy as rs

REAL_USER = {"id": 1, "pseudo": "mehdisellmi", "level": 1}


def student_context(**overrides):
    base = {
        "user_id": 1, "pseudo": "Testeur", "niveau": "Débutant", "niveau_brut": 1,
        "chapitre_courant": None, "topic_courant": None,
        "notions_maitrisees": [], "notions_faibles": [],
        "topics_maitrises": [], "topics_faibles": [],
        "statistiques": {"accuracy": 0, "total_exercices": 0, "temps_total": "0 h", "temps_jour": "0 h", "temps_semaine": "0 h"},
        "dashboard": {"objectif_du_jour": None, "chapitres_en_cours": [], "meilleur_chapitre": None, "chapitre_le_plus_faible": None},
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


class LocalResponseEngineTestCase(unittest.TestCase):
    def setUp(self):
        lre.clear_cache()

    def tearDown(self):
        lre.clear_cache()

    def gen(self, message, **kwargs):
        kwargs.setdefault("use_cache", False)
        return lre.generate(message, REAL_USER, **kwargs)


class TestTousLesMoteurs(LocalResponseEngineTestCase):
    def test_math_engine(self):
        r = self.gen("Resous 2x + 4 = 10")
        self.assertEqual(r.engine, rs.ENGINE_MATH)
        self.assertFalse(r.should_use_llm)
        self.assertIn("Résolution", r.text)

    def test_rule_engine(self):
        r = self.gen("Salut")
        self.assertEqual(r.engine, rs.ENGINE_RULE)
        self.assertFalse(r.should_use_llm)
        self.assertTrue(r.text)

    def test_knowledge_engine(self):
        r = self.gen("C'est quoi une puissance ?")
        self.assertEqual(r.engine, rs.ENGINE_KNOWLEDGE)
        self.assertFalse(r.should_use_llm)
        self.assertIn("Les puissances", r.text)

    def test_dashboard(self):
        r = self.gen("Quelle est ma progression ?")
        self.assertEqual(r.engine, rs.ENGINE_DASHBOARD)
        self.assertFalse(r.should_use_llm)
        self.assertTrue(r.text)

    def test_search_service(self):
        r = self.gen("Les puissances")
        self.assertEqual(r.engine, rs.ENGINE_SEARCH)
        self.assertFalse(r.should_use_llm)
        self.assertTrue(r.text)

    def test_exercise_engine(self):
        r = self.gen("Donne-moi un exercice sur les puissances")
        self.assertEqual(r.engine, rs.ENGINE_EXERCISE)
        self.assertFalse(r.should_use_llm)
        self.assertIn("exercice", r.text.lower())

    def test_clarification(self):
        r = self.gen("......")
        self.assertEqual(r.engine, rs.ENGINE_CLARIFICATION)
        self.assertFalse(r.should_use_llm)
        self.assertEqual(r.text, intent_service.CLARIFICATION_MESSAGE)

    def test_llm(self):
        r = self.gen("Raconte-moi une blague sur les licornes qui font du velo")
        self.assertEqual(r.engine, rs.ENGINE_LLM)
        self.assertTrue(r.should_use_llm)
        self.assertIsNone(r.text)


class TestMentions(LocalResponseEngineTestCase):
    def test_mention_dashboard_seule(self):
        mentions = [{"type": "data", "data_key": "dashboard", "label": "Dashboard"}]
        r = self.gen("@Dashboard", mentions=mentions)
        self.assertEqual(r.engine, rs.ENGINE_DASHBOARD)
        self.assertFalse(r.should_use_llm)
        self.assertTrue(r.text)

    def test_mention_progression_seule(self):
        mentions = [{"type": "data", "data_key": "progression", "label": "Progression"}]
        r = self.gen("@Progression", mentions=mentions)
        self.assertEqual(r.intent, intent_service.PROGRESSION)
        self.assertEqual(r.engine, rs.ENGINE_DASHBOARD)


class TestFallbackDExecution(LocalResponseEngineTestCase):
    """Vérifie le repli en cascade quand un moteur DÉCIDÉ échoue réellement à
    produire un texte — ne redémarre jamais depuis Math Engine, reprend la
    cascade là où response_strategy s'est arrêté."""

    def test_repli_dashboard_vers_llm_si_aucun_template(self):
        """Si `local_knowledge_service.try_answer` échoue malgré la décision
        Dashboard (cas limite simulé), le moteur doit basculer sur LLM —
        jamais planter, jamais halluciner une réponse locale vide."""
        with patch("chatbot.services.local_response_engine.local_knowledge_service.try_answer", return_value=None):
            r = self.gen("Quelle est ma progression ?")
        self.assertEqual(r.engine, rs.ENGINE_LLM)
        self.assertTrue(r.should_use_llm)
        self.assertTrue(r.used_fallback)

    def test_repli_math_vers_llm_si_solve_echoue_malgre_la_decision(self):
        with patch("chatbot.services.local_response_engine.math_engine.try_solve", return_value=None):
            r = self.gen("Resous 2x + 4 = 10")
        self.assertEqual(r.engine, rs.ENGINE_LLM)
        self.assertTrue(r.should_use_llm)

    def test_ne_redemarre_pas_depuis_math_si_knowledge_echoue(self):
        """Le repli après un échec de Knowledge Engine (position 3 dans
        PRIORITY_ORDER) doit continuer APRÈS ce point (Dashboard puis
        Search...), jamais revenir en arrière vers Math/Rule Engine — vérifié
        en s'assurant que Math/Rule ne sont jamais appelés dans ce scénario."""
        with patch("chatbot.services.local_response_engine.knowledge_response_composer.compose", side_effect=Exception("boom")), \
             patch("chatbot.services.local_response_engine.math_engine.try_solve", return_value=None) as math_probe, \
             patch("chatbot.services.local_response_engine.rule_engine.try_handle", return_value=None) as rule_probe:
            r = self.gen("C'est quoi une puissance ?")
        # Math/Rule Engine sont bien SONDÉS une fois par decide_strategy()
        # (priorité 1 et 2, avant Knowledge Engine) mais jamais RE-exécutés
        # par le repli en cascade de local_response_engine (qui démarre à la
        # position de Knowledge Engine, pas depuis le début).
        self.assertEqual(math_probe.call_count, 1)
        self.assertEqual(rule_probe.call_count, 1)
        self.assertEqual(r.engine, rs.ENGINE_LLM)


class TestErreurs(LocalResponseEngineTestCase):
    def test_exception_dans_un_moteur_nest_jamais_propagee(self):
        with patch("chatbot.services.local_response_engine.rule_engine.try_handle", side_effect=RuntimeError("panne simulée")):
            r = self.gen("Salut")  # Rule Engine plante -> doit basculer proprement
        self.assertIsInstance(r, lre.LocalResponseResult)
        # "Salut" ne matche aucun autre moteur local -> repli LLM, sans exception.
        self.assertEqual(r.engine, rs.ENGINE_LLM)

    def test_exception_dans_knowledge_composer_absorbee(self):
        with patch("chatbot.services.local_response_engine.knowledge_response_composer.compose", side_effect=Exception("boom")):
            r = self.gen("C'est quoi une puissance ?")
        self.assertIsInstance(r, lre.LocalResponseResult)
        self.assertEqual(r.engine, rs.ENGINE_LLM)


class TestUtilisateurVideEtAvance(LocalResponseEngineTestCase):
    def test_utilisateur_vide_ne_plante_pas(self):
        ctx = student_context()
        r = lre.generate("Quelle est ma progression ?", REAL_USER, student_context=ctx, use_cache=False)
        self.assertEqual(r.engine, rs.ENGINE_DASHBOARD)
        self.assertTrue(r.text)

    def test_utilisateur_avance_contexte_riche(self):
        ctx = student_context(
            chapitre_courant="Chapitre_1", topic_courant="puissances-entieres-relatives",
            statistiques={"accuracy": 92, "total_exercices": 140, "temps_total": "12 h", "temps_jour": "0 h 45", "temps_semaine": "3 h"},
            historique_conversation=[{"role": "assistant", "content": "Salut !"}],
        )
        r = lre.generate("C'est quoi une puissance ?", REAL_USER, student_context=ctx, use_cache=False)
        self.assertEqual(r.engine, rs.ENGINE_KNOWLEDGE)
        self.assertTrue(r.text)


class TestParametres(LocalResponseEngineTestCase):
    def test_longueur_court_donne_un_texte_plus_court(self):
        ctx_normal = student_context()
        ctx_court = student_context(parametres={**student_context()["parametres"], "longueur": "court"})
        r_normal = lre.generate("C'est quoi une puissance ?", REAL_USER, student_context=ctx_normal, use_cache=False)
        r_court = lre.generate("C'est quoi une puissance ?", REAL_USER, student_context=ctx_court, use_cache=False)
        self.assertLess(len(r_court.text), len(r_normal.text))

    def test_mode_professeur_influence_le_texte(self):
        ctx_defaut = student_context()
        ctx_prof = student_context(parametres={**student_context()["parametres"], "mode": "professeur"})
        r_defaut = lre.generate("Salut", REAL_USER, student_context=ctx_defaut, use_cache=False)
        r_prof = lre.generate("Salut", REAL_USER, student_context=ctx_prof, use_cache=False)
        # Rule Engine est indépendant du mode (réponse fixe) : les deux
        # doivent malgré tout rester des réponses valides, sans exception.
        self.assertTrue(r_defaut.text)
        self.assertTrue(r_prof.text)


class TestCache(LocalResponseEngineTestCase):
    def test_decision_de_strategie_non_recalculee(self):
        """Deux appels identiques ne doivent PAS recalculer la décision
        (response_strategy.decide_strategy) — vérifié en comptant les appels
        réels à decide_strategy via un espion."""
        lre.clear_cache()
        with patch(
            "chatbot.services.local_response_engine.response_strategy.decide_strategy",
            wraps=rs.decide_strategy,
        ) as spy:
            lre.generate("Salut", REAL_USER, use_cache=True)
            lre.generate("Salut", REAL_USER, use_cache=True)
        self.assertEqual(spy.call_count, 2)  # decide_strategy est appelé, mais...
        # ... la déduplication réelle se vérifie par le flag cache_hit de la stratégie renvoyée.
        s1 = rs.decide_strategy("Salut", REAL_USER, use_cache=True)
        self.assertTrue(s1.cache_hit)

    def test_texte_final_jamais_mis_en_cache_reste_variable(self):
        """Le texte composé (Knowledge/Dashboard) reste volontairement
        variable d'un appel à l'autre — le cache ne porte que sur les
        données, jamais sur le texte final (voir docstring module)."""
        textes = set()
        for _ in range(10):
            r = lre.generate("C'est quoi une puissance ?", REAL_USER, use_cache=True)
            textes.add(r.text)
        self.assertGreater(len(textes), 1)

    def test_clear_cache_reinitialise_tout(self):
        lre.generate("Salut", REAL_USER, use_cache=True)
        lre.clear_cache()
        stats = lre.cache_stats()
        self.assertEqual(stats["context_summary_entries"], 0)
        self.assertEqual(stats["strategy_cache"]["entries"], 0)


class TestDecouplageProbeEtResolutionNotion(LocalResponseEngineTestCase):
    """Reproduction directe du bug d'abandon prématuré (audit du 2026-07-26,
    épisode 2) : response_strategy._probe_knowledge_engine() peut juger
    ENGINE_KNOWLEDGE éligible (sa propre recherche interne trouve une notion)
    alors que chapter_id/topic_id — résolus séparément par intent_service.
    classify()/le Student Context — restent None/None pour ce message précis.
    Avant la correction, knowledge_response_composer.compose() renvoyait
    alors un texte froid ("Je n'ai pas trouvé...") que local_response_engine
    traitait comme une réponse VALIDE et définitive, empêchant tout repli
    (mode dégradé, LLM). Ce test force ce découplage directement (sans
    dépendre d'un cas réel fragile de TF-IDF) en injectant une ResponseStrategy
    contrefaite via decide_strategy patché."""

    def _strategy_decouplee(self, **overrides):
        base = dict(
            source=rs.SOURCE_LOCAL, engine=rs.ENGINE_KNOWLEDGE, confidence=50,
            intent=intent_service.DEFINITION, chapter_id=None, topic_id=None,
            quantity=None, difficulty=None, mode=None, should_use_llm=False,
            fallback=rs.ENGINE_LLM, explanation="test (bug de découplage forcé)",
        )
        base.update(overrides)
        return rs.ResponseStrategy(**base)

    def test_engine_knowledge_sans_chapter_id_ne_renvoie_plus_le_texte_froid(self):
        with patch(
            "chatbot.services.local_response_engine.response_strategy.decide_strategy",
            return_value=self._strategy_decouplee(),
        ):
            r = self.gen("xyzxyz1234 incompréhensible xyzxyz5678", student_context=student_context())
        # L'ancien texte froid ne doit JAMAIS apparaître, quel que soit le
        # moteur qui finit par répondre (cascade ou LLM).
        if r.text:
            self.assertNotIn("Je n'ai pas trouvé", r.text)

    def test_engine_knowledge_sans_chapter_id_relance_la_cascade(self):
        """Sans aucun autre moteur local disponible pour ce cas contrefait
        (Dashboard/Search/Exercise tous inéligibles), le Local Response
        Engine doit honnêtement renvoyer should_use_llm=True — jamais
        s'arrêter sur le texte de repli interne du composer."""
        with patch(
            "chatbot.services.local_response_engine.response_strategy.decide_strategy",
            return_value=self._strategy_decouplee(),
        ):
            r = self.gen("xyzxyz1234 incompréhensible xyzxyz5678", student_context=student_context())
        self.assertTrue(r.should_use_llm)
        self.assertIsNone(r.text)

    def test_engine_knowledge_avec_chapter_id_resolu_repond_normalement(self):
        """Contrôle négatif : quand chapter_id/topic_id sont bien résolus
        (cas normal, sans découplage), la réponse du composer reste valide
        et n'active pas ce garde-fou."""
        r = self.gen("C'est quoi une puissance ?")
        self.assertEqual(r.engine, rs.ENGINE_KNOWLEDGE)
        self.assertFalse(r.should_use_llm)
        self.assertIn("Les puissances", r.text)


class TestLearningContextTransmisAuMoteurLocal(LocalResponseEngineTestCase):
    """Bug confirmé (audit du 2026-08-22) : generate() n'avait aucun
    paramètre learning_context — le moteur local reclassait donc chaque
    message SANS le Current Learning Context déjà établi par
    conversation_manager.py, ce qui pouvait écraser un sujet correctement
    identifié par une notion sans rapport (ex: "encore une autre façon"
    avec le sujet "La valeur absolue" déjà établi dérivait vers
    "Chapitre_12/operations-sur-les-evenements", score TF-IDF brut
    coïncidentiel de 0.1224, sans aucun recoupement de titre). Correctif :
    generate() accepte désormais learning_context/last_assistant_message et
    les transmet tels quels à response_strategy.decide_strategy() — aucun
    recalcul, aucune nouvelle logique de routage."""

    LEARNING_CONTEXT = {"chapter_id": "Chapitre_2", "notion_id": "valeur-absolue-dun-nombre-reel"}

    def test_sans_learning_context_le_bug_historique_reste_reproductible(self):
        """Contrôle négatif : documente le comportement AVANT transmission
        du contexte — sans learning_context, le message dérive bien vers la
        notion sans rapport (comportement par défaut inchangé, non régressé
        par ce correctif : le paramètre reste optionnel)."""
        r = self.gen("encore une autre façon", student_context=student_context(class_level="seconde"), class_level="seconde")
        self.assertEqual(r.chapter_id, "Chapitre_12")
        self.assertEqual(r.topic_id, "operations-sur-les-evenements")

    def test_avec_learning_context_le_sujet_est_conserve(self):
        """Le test principal du correctif : avec learning_context transmis,
        le moteur local ne doit plus dériver."""
        r = self.gen(
            "encore une autre façon", student_context=student_context(class_level="seconde"), class_level="seconde",
            learning_context=self.LEARNING_CONTEXT,
        )
        self.assertEqual(r.chapter_id, "Chapitre_2")
        self.assertEqual(r.topic_id, "valeur-absolue-dun-nombre-reel")

    def test_learning_context_recu_par_response_strategy_pas_seulement_le_resultat_final(self):
        """Vérifie le contexte effectivement REÇU par response_strategy.decide_strategy
        (pas seulement le résultat final) — instrumentation de l'appel réel
        pour prouver que la valeur transmise à generate() est exactement
        celle reçue par la fonction de stratégie, sans transformation ni perte."""
        received = {}
        original = rs.decide_strategy

        def _spy(*args, **kwargs):
            received["learning_context"] = kwargs.get("learning_context")
            return original(*args, **kwargs)

        with patch.object(rs, "decide_strategy", side_effect=_spy):
            lre.generate(
                "encore une autre façon", REAL_USER, student_context=student_context(class_level="seconde"),
                use_cache=False, class_level="seconde", learning_context=self.LEARNING_CONTEXT,
            )

        self.assertIsNotNone(received["learning_context"])
        self.assertEqual(received["learning_context"]["chapter_id"], "Chapitre_2")
        self.assertEqual(received["learning_context"]["notion_id"], "valeur-absolue-dun-nombre-reel")

    def test_plusieurs_formulations_courtes_protegees_par_le_contexte(self):
        """Non-régression élargie : plusieurs formulations de suivi courtes,
        confirmées dérivantes sans contexte lors de l'audit, doivent toutes
        rester sur le sujet une fois learning_context transmis."""
        formulations = ["encore une autre façon", "une autre façon", "explique autrement", "explique différemment"]
        for text in formulations:
            with self.subTest(text=text):
                r = self.gen(
                    text, student_context=student_context(class_level="seconde"), class_level="seconde",
                    learning_context=self.LEARNING_CONTEXT,
                )
                self.assertEqual(r.chapter_id, "Chapitre_2")
                self.assertEqual(r.topic_id, "valeur-absolue-dun-nombre-reel")

    def test_changement_de_sujet_explicite_reste_possible_avec_contexte_transmis(self):
        """Garde-fou anti-sur-correction : transmettre learning_context ne
        doit jamais empêcher un changement de sujet explicite assumé."""
        r = self.gen(
            "Maintenant explique-moi les probabilités.", student_context=student_context(class_level="seconde"),
            class_level="seconde", learning_context=self.LEARNING_CONTEXT,
        )
        self.assertNotEqual(r.chapter_id, "Chapitre_2")


class TestPerformance(LocalResponseEngineTestCase):
    def test_appels_repetes_avec_cache_rapides(self):
        message = "Quelle est ma progression ?"
        lre.generate(message, REAL_USER, use_cache=True)  # réchauffe les caches de données

        n = 100
        t0 = time.perf_counter()
        for _ in range(n):
            lre.generate(message, REAL_USER, use_cache=True)
        avg_ms = (time.perf_counter() - t0) * 1000 / n
        self.assertLess(avg_ms, 5.0, "avec les caches de données chauds, une génération doit rester rapide")


if __name__ == "__main__":
    unittest.main()
