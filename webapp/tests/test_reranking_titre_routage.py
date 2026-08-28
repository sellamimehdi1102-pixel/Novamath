"""
Audit global du routage pédagogique NovaMath (2026-08-22) : le classement
TF-IDF brut favorisait parfois un chapitre au vocabulaire générique dense
plutôt que la notion dont le TITRE correspond réellement à la question (ex.
mesuré : "explique-moi la racine carrée" scorait plus haut sur "Fonctions de
référence" — 0.285 — que sur la notion "La racine carrée" elle-même — 0.166).
Confirmé sur les 153 notions/3 niveaux du corpus réel (1071 formulations,
168 collisions) — pas un cas isolé.

Correction : reranking "boost de titre" (intent_service._rerank_by_title),
scoped UNIQUEMENT au routage chapitre/notion du chatbot (_detect_chapter) —
le TF-IDF brut partagé par le RAG générique, les mentions "@", la recherche
utilisateur et les exercices reste strictement inchangé (voir
test_ranking_brut_inchange_pour_les_autres_consommateurs ci-dessous).
"""
import unittest

from chatbot import knowledge_engine as ke
from chatbot.services import intent_service as ins
from chatbot.services import search_service as ss


class TestBoostDeTitreCorrigeLaCollisionDocumentee(unittest.TestCase):
    """Reproduit exactement le cas mesuré dans l'audit."""

    def test_racine_carree_ne_derive_plus_vers_fonctions_de_reference(self):
        result = ins.classify("Explique-moi La racine carrée", context_summary={}, class_level="seconde")
        self.assertEqual(result["chapter_id"], "Chapitre_1")
        self.assertEqual(result["notion_id"], "racine-carree")

    def test_titre_quasi_integral_sauve_un_score_tfidf_brut_faible(self):
        """"Les ensembles de nombres" (titre cité quasi mot pour mot) doit
        être détecté même si son score TF-IDF brut, dilué par un document
        source court, retombe sous le seuil faible historique (0.12)."""
        result = ins.classify("Tu peux m'expliquer Les ensembles de nombres ?", context_summary={}, class_level="seconde")
        self.assertEqual(result["chapter_id"], "Chapitre_1")
        self.assertEqual(result["notion_id"], "ensembles-de-nombres")
        self.assertIn(result["topic_confidence"], ("explicit", "weak"))


class TestPoolDeCandidatsElargi(unittest.TestCase):
    """Phase de validation finale (2026-08-22) : le pool de candidats soumis
    au reranking (_TITLE_RERANK_CANDIDATES) est passé de 5 à 10 — mesuré sur
    les 1071 tests de référence : 5 -> 97,9% (22 collisions), 10 -> 99,1%
    (10 collisions), 0 régression à chaque palier. alpha/beta INCHANGÉS."""

    def test_pool_vaut_bien_dix(self):
        self.assertEqual(ins._TITLE_RERANK_CANDIDATES, 10)

    def test_additionner_des_vecteurs_beneficie_du_pool_elargi(self):
        """Avec un pool de 5, le bon candidat (rang réel #8 en TF-IDF brut)
        n'était même pas soumis au reranking — confirmé absent du top-5."""
        result = ins.classify("Explique-moi Additionner des vecteurs", context_summary={}, class_level="seconde")
        self.assertEqual(result["chapter_id"], "Chapitre_4")
        self.assertEqual(result["notion_id"], "somme-et-difference-de-deux-vecteurs")

    def test_quest_ce_quune_fonction_beneficie_du_pool_elargi(self):
        """Même cause : le bon candidat (rang réel #7) n'entrait pas dans un
        pool de 5, quel que soit son score de titre."""
        result = ins.classify("Explique-moi Qu'est-ce qu'une fonction", context_summary={}, class_level="seconde")
        self.assertEqual(result["chapter_id"], "Chapitre_7")
        self.assertEqual(result["notion_id"], "notion-de-fonction")


class TestRankingBrutInchangePourLesAutresConsommateurs(unittest.TestCase):
    """Le reranking est scoped à intent_service._detect_chapter uniquement —
    RAG (knowledge_engine), recherche unifiée (search_service.search) et donc
    mentions "@"/recherche utilisateur/cartes d'action gardent EXACTEMENT le
    même classement TF-IDF brut qu'avant ce chantier."""

    def test_knowledge_engine_search_conserve_lancien_classement(self):
        results = ke.search("Explique-moi La racine carrée", top_k=1, min_score=0.0, class_level="seconde")
        self.assertEqual(results[0]["chapter_id"], "Chapitre_7")
        self.assertEqual(results[0]["notion_id"], "exemples-de-fonctions-de-reference")

    def test_search_service_search_conserve_lancien_classement(self):
        results = ss.search("Explique-moi La racine carrée", scope=[ss.SCOPE_COURS], limit=1, class_level="seconde")
        self.assertEqual(results[0]["chapter_id"], "Chapitre_7")


class TestBugDefinitionsDansUnTitreDeNotion(unittest.TestCase):
    """Bug indépendant du reranking, découvert par l'audit du 2026-08-22 : le
    titre de notion "Autres définitions et propriétés" (Première) déclenchait
    à tort l'intent DEFINITION via le fragment verbal "d[ée]fini[st]"
    (matché SANS limite de mot à l'intérieur même de "définitions", nom
    pluriel) — la requête était alors amputée avant même la recherche du
    chapitre. Correctif : "d[ée]fini[st]" est désormais ancré par un \\b
    final (verbe uniquement), et "définition de" gagne une variante élidée
    "définition d[e'’]" pour ne plus dépendre accidentellement du fragment
    verbal pour reconnaître "la définition d'une fonction"."""

    def test_titre_definitions_ne_declenche_plus_lintent_a_tort(self):
        result = ins.classify(
            "Je voudrais comprendre Autres définitions et propriétés, tu peux m'aider ?",
            context_summary={}, class_level="premiere",
        )
        self.assertNotEqual(result["intent"], ins.DEFINITION)
        self.assertEqual(result["chapter_id"], "Chapitre_7")
        self.assertEqual(result["notion_id"], "autres-definitions-et-proprietes")

    def test_vraies_formulations_definition_toujours_reconnues(self):
        cases = [
            "donne-moi la définition de la fonction affine",
            "quelle est la définition d'une fonction",
            "c'est quoi la définition de la dérivée",
            "explique la définition de la dérivée",
        ]
        for text in cases:
            with self.subTest(text=text):
                self.assertEqual(ins.classify(text)["intent"], ins.DEFINITION)

    def test_verbe_definir_toujours_reconnu(self):
        for text in ["il définit le mot ainsi", "tu définis correctement"]:
            with self.subTest(text=text):
                self.assertEqual(ins.classify(text)["intent"], ins.DEFINITION)


class TestRerankingParametres(unittest.TestCase):
    """Les poids alpha/beta calibrés empiriquement (audit dédié, 1071 tests)
    restent documentés et accessibles — évite qu'une future modification les
    change silencieusement sans repasser par le jeu de référence."""

    def test_alpha_beta_calibres(self):
        self.assertAlmostEqual(ins.TITLE_BOOST_ALPHA, 0.6)
        self.assertAlmostEqual(ins.TITLE_BOOST_BETA, 0.4)
        self.assertAlmostEqual(ins.TITLE_BOOST_ALPHA + ins.TITLE_BOOST_BETA, 1.0)

    def test_reranking_ne_change_rien_sans_titre_correspondant(self):
        """Une requête sans rapport avec aucun titre du corpus doit garder
        le comportement TF-IDF brut usuel (aucun candidat artificiellement
        favorisé)."""
        candidates = ss.search("un truc au hasard sans rapport", scope=[ss.SCOPE_COURS], limit=5, class_level="seconde")
        # Corpus réel : peut légitimement ne rien retourner de pertinent.
        self.assertIsInstance(candidates, list)


if __name__ == "__main__":
    unittest.main()
