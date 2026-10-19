"""
Chantier "routage réel" (2026-10-17) — suite à l'audit confirmant (par
exécution directe + vrais logs ai_request_logs) que des moteurs locaux
interceptaient certaines demandes avant le LLM, avec un gabarit incapable
d'en respecter la contrainte explicite :

  Test A (révision + contrainte de temps) : ENGINE_SEARCH répondait avec un
    gabarit "étape par étape" fixe (knowledge_response_composer.py), sans
    aucune notion de synthèse priorisée ni de contrainte de temps.
  Test B (indice) : ENGINE_SEARCH effectuait sa PROPRE recherche
    indépendante (response_strategy._probe_search_service), pouvant
    sélectionner un chapitre totalement hors sujet (ex: "tableau de signes"
    pour une équation du second degré) sans jamais consulter la notion déjà
    résolue par intent_service.
  Test C (résolution détaillée) : Math Engine répond localement, SANS JAMAIS
    passer par un prompt — son gabarit (math_engine._solve_equation) est une
    ligne de méthode fixe + le résultat, incapable de "toutes les étapes".
  Test D (cartes dupliquées) : deux cartes "notion_series" sur des notions
    différentes affichaient un texte strictement identique ("Commencer un
    entraînement"), car t() n'interpole jamais le `fallback` (i18n.js).

Corrections (toutes minimales, aucune nouvelle recherche/corroboration) :
  - response_strategy.py : Knowledge/Search Engine jamais choisis pour
    REVISION/INDICE (_NO_LOCAL_COMPOSER_INTENTS) ; Math Engine jamais choisi
    quand intent_result["wants_detail"] est vrai (intent_service.DETAIL_RE).
  - conversation_manager._try_internal_answer : même garde-fou wants_detail
    pour le chemin d'exécution RÉEL de Math Engine (_try_local_response_engine
    ne l'exécute jamais, voir LOCAL_RESPONSE_ENGINE_ALLOWED_ENGINES).
  - conversation_manager.attach_action_cards : intent_chapter_id n'est plus
    réservé à l'intent EXERCICE — filtre les cartes "exercices" dès qu'un
    chapitre est résolu, quelle que soit l'intention.
  - action_cards_service._notion_series_card : expose `title` (déjà `notion`,
    même donnée, même clé que _course_card).
  - chatbot.js::actionCardLabel : compose "<libellé> — <title>" côté
    frontend (i18n.js inchangé).
"""
import unittest

from chatbot import conversation_manager as cm
from chatbot.services import action_cards_service as acs
from chatbot.services import intent_service as ins
from chatbot.services import response_strategy as rs
from chatbot.services import search_service as ss


class _StrategyTestCase(unittest.TestCase):
    FAKE_USER = {"id": 1}

    def decide(self, message, class_level="seconde"):
        student_context = {
            "class_level": class_level, "chapitre_courant": None, "topic_courant": None,
            "dashboard": {}, "parametres": {},
        }
        return rs.decide_strategy(
            message, self.FAKE_USER, chatbot_settings={}, student_context=student_context,
            use_cache=False, class_level=class_level,
        )


class TestARevisionNePasInterceptéeLocalement(_StrategyTestCase):
    def test_revision_avec_contrainte_de_temps_route_vers_le_llm(self):
        strategy = self.decide(
            "J'ai 20 minutes pour réviser les probabilités. Organise-moi une révision efficace."
        )
        self.assertEqual(strategy.intent, ins.REVISION)
        self.assertEqual(strategy.engine, rs.ENGINE_LLM)

    def test_revision_sans_contrainte_route_aussi_vers_le_llm(self):
        """Généralisation voulue : le gabarit local n'a aucune notion de
        synthèse priorisée, contrainte ou pas — toute REVISION va au LLM."""
        strategy = self.decide("Je dois réviser les probabilités pour mon contrôle.")
        self.assertEqual(strategy.intent, ins.REVISION)
        self.assertEqual(strategy.engine, rs.ENGINE_LLM)


class TestBIndiceNePasInterceptéeLocalement(_StrategyTestCase):
    def test_indice_sur_equation_ne_route_jamais_vers_knowledge_ou_search(self):
        strategy = self.decide("Aide-moi à résoudre x² - 5x + 6 = 0 sans me donner la réponse.")
        self.assertEqual(strategy.intent, ins.INDICE)
        self.assertEqual(strategy.engine, rs.ENGINE_LLM)

    def test_indice_formulation_differente(self):
        """Généralisation : une autre formulation d'indice, sur un autre
        chapitre, doit aussi éviter tout gabarit local potentiellement hors
        sujet."""
        strategy = self.decide("Donne-moi un petit indice pour factoriser x² - 4, pas la solution complète.")
        self.assertEqual(strategy.intent, ins.INDICE)
        self.assertEqual(strategy.engine, rs.ENGINE_LLM)


class TestCDetailDesEtapes(_StrategyTestCase):
    def test_demande_explicite_de_detail_route_vers_le_llm(self):
        strategy = self.decide("Résous complètement x² - 5x + 6 = 0 et explique toutes les étapes.")
        self.assertEqual(strategy.engine, rs.ENGINE_LLM)

    def test_formulation_differente_du_detail(self):
        strategy = self.decide("Résous 3x - 1 = 8 et montre-moi le détail du calcul.")
        self.assertEqual(strategy.engine, rs.ENGINE_LLM)

    def test_resolution_simple_reste_locale(self):
        """Non-régression centrale : sans demande explicite de détail, Math
        Engine répond toujours localement (rapide, gratuit, déterministe)."""
        strategy = self.decide("Résous x² - 5x + 6 = 0")
        self.assertEqual(strategy.engine, rs.ENGINE_MATH)

    def test_try_internal_answer_respecte_wants_detail(self):
        """Le chemin d'exécution RÉEL de Math Engine (confirmé par les logs
        de production, engine="legacy_internal") doit aussi respecter le
        flag — pas seulement la décision "en aparté" de response_strategy."""
        self.assertIsNone(cm._try_internal_answer(
            "Résous complètement x² - 5x + 6 = 0 et explique toutes les étapes.",
            wants_detail=True,
        ))
        answer = cm._try_internal_answer("Résous x² - 5x + 6 = 0", wants_detail=False)
        self.assertIn("x = 2", answer)
        self.assertIn("x = 3", answer)


class TestNonRegressionAutresIntents(_StrategyTestCase):
    """Les corrections ci-dessus ne doivent couvrir QUE REVISION/INDICE/
    wants_detail — tout le reste continue de profiter des moteurs locaux
    quand ils savent répondre."""

    def test_definition_simple_reste_locale(self):
        strategy = self.decide("Qu'est-ce qu'une fonction affine ?")
        self.assertIn(strategy.engine, (rs.ENGINE_KNOWLEDGE, rs.ENGINE_SEARCH))

    def test_calcul_direct_reste_local(self):
        strategy = self.decide("Calcule 12 * 3 + 5")
        self.assertEqual(strategy.engine, rs.ENGINE_MATH)

    def test_correction_de_raisonnement_non_bloquee(self):
        """CORRECTION n'est pas dans _NO_LOCAL_COMPOSER_INTENTS — doit
        pouvoir rester locale si un moteur sait répondre."""
        self.assertNotIn(ins.CORRECTION, rs._NO_LOCAL_COMPOSER_INTENTS)


class TestDCartesDeSuggestion(unittest.TestCase):
    """Backend : intent_chapter_id filtre désormais les cartes "exercices"
    hors sujet dès qu'un chapitre est résolu, quelle que soit l'intention."""

    def test_carte_hors_sujet_disparait_quand_un_chapitre_est_resolu(self):
        msg = "J'ai 20 minutes pour réviser les probabilités. Organise-moi une révision efficace."
        search_results = ss.search(msg, limit=8, class_level="seconde")
        cards = acs.build_cards(
            msg, "réponse", {"weak_topics": [], "weak_notions": []}, search_results,
            intent_chapter_id="Chapitre_12", class_level="seconde",
        )
        for card in cards:
            if card["type"] == "notion_series":
                self.assertEqual(card["chapter_id"], "Chapitre_12")

    def test_notion_series_card_porte_un_title_distinct(self):
        card_a = acs._notion_series_card("Chapitre_12", "Loi de probabilité", ["ex1"])
        card_b = acs._notion_series_card("Chapitre_12", "Notion d'événement", ["ex2"])
        self.assertEqual(card_a["title"], "Loi de probabilité")
        self.assertEqual(card_b["title"], "Notion d'événement")
        self.assertNotEqual(card_a["title"], card_b["title"])

    def test_carte_entrainement_porte_un_vrai_pool_pas_un_seul_exercice(self):
        """Non-régression : la carte "Commencer un entraînement" (label_key
        par défaut de _notion_series_card, construite depuis un résultat de
        recherche "exercices" normal — pas depuis les notions faibles)
        transmettait un unique exercise_id au frontend
        (chatbot.js::navigateToCard -> lumis:pending_series), que
        exercice.js::buildSeriesPool répétait ensuite pour remplir toute la
        série (comportement voulu pour un pool réellement restreint, mais ici
        le pool n'était restreint qu'à cause de ce bug) — chaque "question
        suivante" affichait donc le même exercice du début à la fin. La carte
        doit désormais porter un pool réel (jusqu'à 5 exercices distincts de
        la même notion, voir search_service.exercises_by_notion), exactement
        comme le chemin "Refaire cette série" (notions faibles) le fait déjà."""
        msg = "Comment calculer la probabilité d'un événement ?"
        search_results = ss.search(msg, limit=8, class_level="seconde")
        exercices_results = [r for r in search_results if r["type"] == "exercices"]
        self.assertTrue(exercices_results, "précondition du test : aucun résultat 'exercices' trouvé")

        cards = acs.build_cards(
            msg, "réponse", {"weak_topics": [], "weak_notions": []}, search_results, class_level="seconde",
        )
        practice_cards = [c for c in cards if c["type"] == "notion_series" and c["label_key"] == "chatbot_card_practice"]
        self.assertTrue(practice_cards, "aucune carte 'Commencer un entraînement' générée")
        for card in practice_cards:
            self.assertGreater(
                len(card["exercise_ids"]), 1,
                f"carte {card['notion']!r} ne porte qu'un seul exercice — la série se répétera",
            )
            self.assertEqual(len(card["exercise_ids"]), len(set(card["exercise_ids"])), "exercise_ids doit être dédupliqué")

    def test_scenario_exact_des_captures_distributivite_3x_plus_5(self):
        """Reproduit littéralement le scénario signalé (captures d'écran) :
        la question "Développer l'expression A = 3(x + 5)" (exercice 508,
        Chapitre_3 "Distributivité et identités remarquables") revenait à
        l'identique en question 3 ET 4 d'une série lancée depuis le chatbot.
        Un premier correctif (exercises_by_topic, basé sur canonical_ids.
        resolve_topic_id) n'a PAS fait disparaître ce bug en conditions
        réelles — ce test échoue avec ce premier correctif s'il est
        réintroduit seul (topic_id peut être None ou diverger d'un exercice à
        l'autre selon la résolution floue), et ne passe qu'avec
        exercises_by_notion (correspondance exacte sur le texte de la banque,
        sans dépendre d'aucun topic_id)."""
        msg = "Développer l'expression A = 3(x + 5)"
        search_results = ss.search(msg, limit=8, class_level="seconde")
        exercices_results = [r for r in search_results if r["type"] == "exercices"]
        self.assertTrue(exercices_results, "précondition du test : aucun résultat 'exercices' trouvé")
        self.assertEqual(exercices_results[0]["chapter_id"], "Chapitre_3")

        cards = acs.build_cards(
            msg, "réponse", {"weak_topics": [], "weak_notions": []}, search_results, class_level="seconde",
        )
        practice_cards = [c for c in cards if c["type"] == "notion_series" and c["label_key"] == "chatbot_card_practice"]
        self.assertTrue(practice_cards)
        card = practice_cards[0]
        self.assertGreater(len(card["exercise_ids"]), 1)

        # Vérifie les ÉNONCÉS réellement affichés (pas seulement les ids) :
        # simule les deux premiers appels de exercice.js::loadCurrent() sur ce
        # pool exact, comme le ferait la série lancée depuis le chatbot.
        bank_by_id = {e["id"]: e for e in knowledge_engine_exercises_bank()}
        enonces = [bank_by_id[eid]["enonce"] for eid in card["exercise_ids"]]
        self.assertEqual(len(enonces), len(set(enonces)), "deux questions de la série afficheraient le même énoncé")

    def test_exercises_by_notion_fonctionne_sans_topic_crosswalk(self):
        """La classe "troisieme" n'a pas de topic_crosswalk.json
        (metadata_dir=None, curriculum_registry.py) : canonical_ids.
        resolve_topic_id() peut y renvoyer None selon la notion, auquel cas
        exercises_by_topic(topic_id=None) renvoie toujours [] — jamais de pool
        réel. exercises_by_notion(), qui compare le texte exact de la notion
        plutôt qu'un topic_id, doit fonctionner indépendamment de cette
        absence de crosswalk."""
        pool = ss.exercises_by_notion(
            "Chapitre_4", "Développer un produit avec la simple distributivité",
            limit=5, class_level="troisieme",
        )
        self.assertGreater(len(pool), 1)
        self.assertEqual(len({p["exercise_id"] for p in pool}), len(pool))


def knowledge_engine_exercises_bank():
    import json
    from pathlib import Path

    path = Path(__file__).resolve().parent.parent.parent / "exercises_bank.json"
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
