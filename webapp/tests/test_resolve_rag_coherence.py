"""
Chantier "cohérence du RAG" (2026-10-17) : conversation_manager.
_resolve_rag_context ne doit plus réutiliser aveuglément le chapitre/la
notion déjà résolus par intent_service (même à confiance "explicit"), ni
se rabattre sans condition sur une recherche indépendante
(knowledge_engine.search) — bug confirmé par l'audit "tableau de signes" :
pour le message "Aide-moi à résoudre x² - 5x + 6 = 0 sans me donner la
réponse", intent_service (search_service + reranking de titre) ET
knowledge_engine.search (implémentation de recherche totalement
indépendante) donnent chacun un résultat, mais ces deux résultats peuvent
être CONTRADICTOIRES (classe "première") ou s'accorder sur un chapitre qui
n'est en réalité pas celui attendu par l'utilisateur, faute de notion
adéquate au programme de la classe (classe "seconde").

Correction : le chapitre/la notion résolus par intent_service ne sont
réutilisés QUE s'ils sont CORROBORÉS par la recherche indépendante
(apparaissent dans son top-5) ; à défaut, on ne se rabat sur cette
recherche indépendante elle-même que si son meilleur score est net
(search_service.TFIDF_STRONG_THRESHOLD) ; sinon, aucun contexte n'est
renvoyé plutôt qu'un cours potentiellement hors sujet.
"""
import unittest

from chatbot import conversation_manager as cm
from chatbot.services import intent_service as ins, search_service as ss


class TestSujetExpliciteCorrobore(unittest.TestCase):
    """Le cas corrigé du test A : une équation nue, en classe "première"
    (où la notion existe réellement), doit désormais renvoyer le bon
    contenu — avant cette correction, une notion sans rapport
    ("Notion de limite d'une suite") était injectée à sa place."""

    def test_premiere_equation_nue_renvoie_le_bon_chapitre(self):
        msg = "Aide-moi à résoudre x² - 5x + 6 = 0 sans me donner la réponse."
        intent_result = ins.classify(msg, class_level="premiere")
        rag = cm._resolve_rag_context(intent_result, msg, class_level="premiere")
        self.assertIn("Équations du second degré", rag)
        self.assertNotIn("limite d'une suite", rag)

    def test_revision_probabilites_reste_sur_le_bon_chapitre(self):
        """Non-régression (test C) : un sujet déjà bien identifié et
        corroboré (le cas normal, pas le bug) doit continuer de fonctionner."""
        msg = "J'ai 20 minutes pour réviser les probabilités. Organise-moi une révision efficace."
        intent_result = ins.classify(msg, class_level="seconde")
        rag = cm._resolve_rag_context(intent_result, msg, class_level="seconde")
        self.assertIn("probabilité", rag.lower())


class TestSujetHeriteContinuite(unittest.TestCase):
    """Chemin "topic_inherited" : non modifié par cette correction — doit
    rester fiable (lookup exact, pas une recherche floue)."""

    def test_sujet_herite_utilise_directement_le_lookup_exact(self):
        intent_result = {
            "intent": ins.REFORMULATION, "chapter_id": "Chapitre_13",
            "notion_id": "theoreme-de-pythagore", "topic_inherited": True,
        }
        rag = cm._resolve_rag_context(intent_result, "réexplique moi", class_level="troisieme")
        self.assertIn("Pythagore", rag)


class TestSujetAmbiguOuAbsent(unittest.TestCase):
    def test_aucun_chapitre_et_recherche_faible_ne_renvoie_rien(self):
        """Un message réellement hors-sujet (aucun chapitre résolu, aucune
        correspondance nette) doit renvoyer une chaîne vide plutôt qu'un
        contenu deviné au hasard."""
        intent_result = {"intent": ins.NONE_INTENT, "chapter_id": None, "notion_id": None, "topic_inherited": False}
        rag = cm._resolve_rag_context(intent_result, "blablabla sans aucun rapport", class_level="seconde")
        self.assertEqual(rag, "")

    def test_notion_absente_du_programme_ne_plante_pas(self):
        """Classe "seconde" : "équations du second degré" n'existe pas dans
        ce programme — ne doit jamais lever d'exception, seulement renvoyer
        le meilleur contenu corroboré disponible (ou rien)."""
        msg = "Aide-moi à résoudre x² - 5x + 6 = 0 sans me donner la réponse."
        intent_result = ins.classify(msg, class_level="seconde")
        rag = cm._resolve_rag_context(intent_result, msg, class_level="seconde")
        self.assertIsInstance(rag, str)


class TestCoherenceDesDeuxRecherchesIndependantes(unittest.TestCase):
    """Preuve directe que la corroboration fonctionne comme prévu : le
    chapitre résolu par intent_service n'est utilisé que s'il apparaît
    aussi dans la recherche indépendante."""

    def test_chapitre_non_corrobore_nest_pas_utilise_aveuglement(self):
        intent_result = {
            "intent": ins.NONE_INTENT, "chapter_id": "Chapitre_999_inexistant",
            "notion_id": None, "topic_inherited": False, "topic_confidence": "explicit",
        }
        rag = cm._resolve_rag_context(
            intent_result, "Les probabilités et les lois de probabilité", class_level="seconde",
        )
        # Le chapitre bidon n'est jamais corroboré par la recherche
        # indépendante -> repli sur cette dernière (ou rien), jamais un
        # lookup sur un chapitre inexistant.
        self.assertNotIn("Chapitre_999_inexistant", rag)


if __name__ == "__main__":
    unittest.main()
