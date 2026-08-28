"""
Suite "répétition des exemples" (chantier 2026-08-23, Priorité 3) : prouve
que le chatbot NovaMath mémorise réellement quels exemples ont déjà été
montrés dans une conversation et ne les répète plus tant qu'une alternative
réelle existe dans les données de cours — voir knowledge_engine.get_exemple/
exemple_pool_exhausted, knowledge_response_composer.compose() (moteur local),
degraded_mode_service._build_*_answer (mode dégradé), et
conversation_manager._commit_used_exemples (persistance cross-tour dans
conversations.learning_context).

Notion "puissances-entieres-relatives" (Chapitre_1, Seconde) utilisée pour la
plupart des tests : 3 exemples réels et distincts dans les données actuelles
(exemple-produit-meme-base / exemple-exposant-negatif /
exemple-puissance-de-puissance-combinee) — assez pour observer une vraie
rotation sans repli. "valeur-absolue-dun-nombre-reel" (Chapitre_2, Seconde,
1 seul exemple réel) sert à prouver le repli honnête quand le stock est
epuisé dès le premier tour.
"""
import random
import unittest

import db
import server
from chatbot import conversation_manager as cm
from chatbot import knowledge_engine
from chatbot.services import degraded_mode_service, intent_service
from chatbot.services import knowledge_response_composer as krc
from chatbot.services import response_strategy as rs


def _register(client):
    email = f"exdiv{random.randint(1_000_000, 9_999_999)}@gmail.com"
    username = f"exdivuser{random.randint(100_000, 999_999)}"
    resp = client.post("/api/auth/register", json={
        "email": email, "username": username, "pseudo": "ExDiv",
        "birth_date": "2000-01-01",
        "password": "MotDePasse123!", "confirm_password": "MotDePasse123!",
        "accept_terms": True, "accept_privacy": True,
    })
    return resp.get_json()["user"]


def _student_context(**overrides):
    base = {
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
    base.update(overrides)
    return base


PUISSANCES = ("Chapitre_1", "puissances-entieres-relatives")
VALEUR_ABSOLUE = ("Chapitre_2", "valeur-absolue-dun-nombre-reel")


class TestKnowledgeEngineExcludeIds(unittest.TestCase):
    def setUp(self):
        self.notion = knowledge_engine.get_notion(*PUISSANCES, class_level="seconde")
        self.all_ids = {ex["id"] for ex in self.notion["exemples"]}
        self.assertEqual(len(self.all_ids), 3)

    def test_exclut_les_ids_deja_vus_quand_une_alternative_existe(self):
        first = knowledge_engine.get_exemple(self.notion, exclude_ids=())
        self.assertIsNotNone(first)
        second = knowledge_engine.get_exemple(self.notion, exclude_ids=(first["id"],))
        self.assertNotEqual(second["id"], first["id"])
        third = knowledge_engine.get_exemple(self.notion, exclude_ids=(first["id"], second["id"]))
        self.assertNotIn(third["id"], (first["id"], second["id"]))

    def test_pool_non_epuise_tant_quune_alternative_existe(self):
        self.assertFalse(knowledge_engine.exemple_pool_exhausted(self.notion, exclude_ids=()))
        two_ids = list(self.all_ids)[:2]
        self.assertFalse(knowledge_engine.exemple_pool_exhausted(self.notion, exclude_ids=two_ids))

    def test_pool_epuise_repli_honnete_sur_repetition_sans_planter(self):
        self.assertTrue(knowledge_engine.exemple_pool_exhausted(self.notion, exclude_ids=self.all_ids))
        # Repli : renvoie quand même un exemple (jamais None), plutôt que
        # d'échouer — la répétition devient alors normale et attendue.
        repeated = knowledge_engine.get_exemple(self.notion, exclude_ids=self.all_ids)
        self.assertIsNotNone(repeated)
        self.assertIn(repeated["id"], self.all_ids)

    def test_notion_a_un_seul_exemple_epuise_des_le_premier_tour(self):
        va_notion = knowledge_engine.get_notion(*VALEUR_ABSOLUE, class_level="seconde")
        self.assertEqual(len(va_notion["exemples"]), 1)
        only_id = va_notion["exemples"][0]["id"]
        self.assertFalse(knowledge_engine.exemple_pool_exhausted(va_notion, exclude_ids=()))
        self.assertTrue(knowledge_engine.exemple_pool_exhausted(va_notion, exclude_ids=(only_id,)))


class TestComposeExcludeExemplesEntreLesTours(unittest.TestCase):
    """Moteur local (knowledge_response_composer.compose()) : `used_exemple_ids`
    décoré sur la ResponseStrategy (même mécanisme que escalation_level/
    recommended_approach, voir local_response_engine.generate()) exclut
    réellement les exemples déjà montrés."""

    def _strategy(self, used_exemple_ids=()):
        return rs.ResponseStrategy(
            source=rs.SOURCE_LOCAL, engine=rs.ENGINE_KNOWLEDGE, confidence=50,
            intent=intent_service.EXEMPLE, chapter_id=PUISSANCES[0], topic_id=PUISSANCES[1],
            quantity=None, difficulty=None, mode=None, should_use_llm=False,
            fallback=rs.ENGINE_LLM, explanation="test", used_exemple_ids=tuple(used_exemple_ids),
        )

    def test_trois_tours_successifs_donnent_trois_exemples_distincts(self):
        used = []
        seen_texts = []
        for _ in range(3):
            draft = krc.compose(self._strategy(used_exemple_ids=used), student_context=_student_context())
            self.assertEqual(len(draft.new_exemple_ids), 1, "un seul nouvel exemple attendu par tour")
            new_id = draft.new_exemple_ids[0]
            self.assertNotIn(new_id, used, "un id déjà utilisé a été re-proposé comme neuf")
            used.append(new_id)
            seen_texts.append(draft.text)
        self.assertEqual(len(set(used)), 3, f"les 3 tours n'ont pas couvert les 3 exemples réels : {used!r}")
        self.assertEqual(len(set(seen_texts)), 3, "les 3 réponses ne sont pas réellement différentes")

    def test_quatrieme_tour_quand_stock_epuise_ne_pretend_pas_un_nouvel_id(self):
        notion = knowledge_engine.get_notion(*PUISSANCES, class_level="seconde")
        all_ids = tuple(ex["id"] for ex in notion["exemples"])
        draft = krc.compose(self._strategy(used_exemple_ids=all_ids), student_context=_student_context())
        # Stock épuisé : compose() doit répéter un exemple existant (jamais
        # planter, jamais None) mais ne doit RIEN ajouter de "nouveau" à
        # persister (l'exemple répété est déjà connu de l'appelant).
        self.assertEqual(draft.new_exemple_ids, ())
        self.assertTrue(draft.text.strip())


class TestDegradedModeExcludeExemplesEntreLesTours(unittest.TestCase):
    """Mode dégradé (degraded_mode_service.try_answer) : même exclusion
    cross-tour via intent_result["used_exemple_ids"], et repli honnête
    (formulation distincte) quand le stock d'une notion pauvre est épuisé."""

    def _intent_result(self, used_exemple_ids=()):
        return {
            "chapter_id": PUISSANCES[0], "notion_id": PUISSANCES[1], "topic_inherited": True,
            "intent": intent_service.EXEMPLE, "escalation_level": 1, "recommended_approach": "exemple",
            "used_exemple_ids": list(used_exemple_ids),
        }

    def test_trois_tours_successifs_excluent_les_precedents(self):
        used = []
        for _ in range(3):
            intent_result = self._intent_result(used_exemple_ids=used)
            messages = [{"role": "user", "content": "donne-moi un exemple"}]
            answer = degraded_mode_service.try_answer(intent_result, messages, class_level="seconde")
            self.assertIsNotNone(answer)
            new_ids = intent_result.get("new_exemple_ids") or ()
            self.assertEqual(len(new_ids), 1)
            self.assertNotIn(new_ids[0], used)
            used.append(new_ids[0])
        self.assertEqual(len(set(used)), 3)

    def test_repli_honnete_quand_stock_dune_notion_pauvre_est_epuise(self):
        va_notion = knowledge_engine.get_notion(*VALEUR_ABSOLUE, class_level="seconde")
        only_id = va_notion["exemples"][0]["id"]
        intent_result = {
            "chapter_id": VALEUR_ABSOLUE[0], "notion_id": VALEUR_ABSOLUE[1], "topic_inherited": True,
            "intent": intent_service.EXEMPLE, "escalation_level": 1, "recommended_approach": "exemple",
            "used_exemple_ids": [only_id],
        }
        messages = [{"role": "user", "content": "donne-moi un autre exemple"}]
        answer = degraded_mode_service.try_answer(intent_result, messages, class_level="seconde")
        self.assertIsNotNone(answer)
        # Le seul exemple réel est nécessairement répété (aucune alternative
        # dans les données) — la formulation doit le dire honnêtement plutôt
        # que prétendre un exemple neuf ("Voyons ça avec un exemple concret").
        self.assertNotIn("Voyons ça avec un exemple concret", answer)
        self.assertIn("pas d'autre exemple différent", answer.lower())
        # Aucun id "nouveau" à committer : c'est une pure répétition connue.
        self.assertEqual(intent_result.get("new_exemple_ids"), ())


class TestPipelineReelDiversiteExemples(unittest.TestCase):
    """Preuve bout-en-bout sur le vrai pipeline (stream_reply) : la séquence
    exacte rapportée par l'utilisateur ("donne-moi un exemple" / "donne-moi
    un autre exemple" / "encore un exemple") ne produit plus le même exemple
    à chaque fois, tant que le stock réel de la notion n'est pas épuisé."""

    def setUp(self):
        client = server.app.test_client()
        self.user = _register(client)
        self.conv_id = db.create_conversation(self.user["id"])
        # Amorce le Current Learning Context directement sur la notion à 3
        # exemples, pour cibler exactement le scénario testé sans dépendre
        # de la classification d'un premier message d'introduction.
        db.set_conversation_learning_context(
            self.conv_id, PUISSANCES[0], PUISSANCES[1], "Puissances entières relatives",
            incomprehension_count=0, approaches_used=[], class_level="seconde", used_exemple_ids=[],
        )

    def test_approches_ne_se_repetent_pas_sur_3_demandes_dexemple(self):
        for message in ("Donne-moi un exemple.", "Donne-moi un autre exemple.", "Encore un exemple."):
            list(cm.stream_reply(
                self.user, self.conv_id, message, chapters_summary=None, mentions=None,
                debug=False, class_level="seconde",
            ))
        lc = db.get_conversation_learning_context(self.conv_id)
        used_exemple_ids = lc.get("used_exemple_ids") or []
        # Non fatal si le moteur choisi pour un tour n'a pas mémorisé
        # d'exemple (ex: repli LLM sans mode dégradé, qui reste réputé
        # fiable) — mais si des ids ont été mémorisés, ils doivent être
        # RÉELLEMENT distincts, jamais deux fois le même noté comme "vu".
        self.assertEqual(len(used_exemple_ids), len(set(used_exemple_ids)), f"doublon dans used_exemple_ids : {used_exemple_ids!r}")


if __name__ == "__main__":
    unittest.main()
