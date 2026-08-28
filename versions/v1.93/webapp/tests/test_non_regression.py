"""
Non-régression : vérifie que les fonctionnalités historiques (antérieures au
chantier Knowledge Engine v2 / canonical_ids) continuent de fonctionner à
l'identique après le câblage de canonical_ids dans search_service.py,
context_builder.py, variable_resolver.py, action_cards_service.py et
mentions_service.py.
"""
import unittest

from chatbot import knowledge_engine, math_engine, rule_engine
from chatbot.services import search_service
from chatbot.validate_cours_schema import validate_all as validate_cours
from validate_topic_crosswalk import validate as validate_crosswalk


class TestValidateursDeSchema(unittest.TestCase):
    """Les deux validateurs (chantiers précédents) doivent rester à 0 erreur
    après le câblage de canonical_ids — sinon une régression de contenu
    serait passée inaperçue."""

    def test_validate_cours_schema(self):
        errors, stats = validate_cours()
        self.assertEqual(errors, [])
        self.assertEqual(stats["chapters"], 12)
        self.assertEqual(stats["notions"], 52)
        self.assertEqual(stats["schema_v2_notions"], 52, "généralisation KE v2 : les 52 notions doivent être en schemaVersion 2")

    def test_validate_topic_crosswalk(self):
        errors, warnings, stats = validate_crosswalk()
        self.assertEqual(errors, [])
        self.assertEqual(stats["entries"], 52)


class TestRuleEngineEtMathEngineInchanges(unittest.TestCase):
    """Rule Engine (salutations/identité) et Math Engine (sympy) ne dépendent
    pas de canonical_ids — vérifie qu'ils n'ont pas été affectés par les
    imports ajoutés dans les modules voisins."""

    def test_salutation(self):
        self.assertIsNotNone(rule_engine.try_handle("Bonjour"))

    def test_identite(self):
        self.assertIsNotNone(rule_engine.try_handle("Qui es-tu ?"))

    def test_message_hors_perimetre_ne_declenche_rien(self):
        self.assertIsNone(rule_engine.try_handle("Explique-moi les puissances"))

    def test_calcul_deterministe(self):
        answer = math_engine.try_solve("Résous 2x + 4 = 10")
        self.assertIsNotNone(answer)
        self.assertIn("3", answer)


class TestKnowledgeEngineV2AccesseursNonRegresses(unittest.TestCase):
    """Les accesseurs KE v2 doivent continuer à retomber proprement sur le
    format historique après migrate_ke_v2.py (généralisation aux 12
    chapitres) : les champs scaffoldés automatiquement (structure présente,
    contenu pédagogique réel non rédigé) doivent retomber correctement sur le
    comportement historique — mise à jour depuis la généralisation, où
    "racine-carree" est passée de "non enrichie" à "scaffoldée mais vide sur
    les niveaux non dérivables automatiquement"."""

    def test_repli_definition_niveau_non_redige(self):
        """definitions.college a été scaffoldée à "" (pas de contenu collège
        réellement rédigé pour cette notion) — doit retomber sur la
        définition historique, jamais renvoyer une chaîne vide."""
        notion = knowledge_engine.get_notion("Chapitre_1", "racine-carree")
        self.assertIsNotNone(notion)
        self.assertEqual(knowledge_engine.get_definition(notion, level="college"), notion["definition"])

    def test_formules_scaffoldees_depuis_reglesimportantes(self):
        """Après migration, les formules ne sont plus vides : elles ont été
        automatiquement scaffoldées depuis reglesImportantes (contenu réel,
        pas fabriqué) — seul le champ "expression" est rempli, le reste
        ("nom", "quand_utiliser"...) reste vide, à charge d'un professeur."""
        notion = knowledge_engine.get_notion("Chapitre_1", "racine-carree")
        formules = knowledge_engine.get_formules(notion)
        # notion["regles"] : nom du champ dans le document indexé par
        # knowledge_engine._load_notions() (traduit depuis "reglesImportantes"
        # du JSON brut).
        self.assertEqual(len(formules), len(notion["regles"]))
        for f in formules:
            self.assertTrue(f["expression"])
            self.assertEqual(f["nom"], "")

    def test_repli_methode_niveau_non_redige(self):
        """etapesParNiveau.debutant a été scaffoldée à [] (aucune version
        "débutant" réellement rédigée pour cette notion) — doit retomber sur
        les étapes historiques, jamais renvoyer une liste vide."""
        notion = knowledge_engine.get_notion("Chapitre_1", "racine-carree")
        etapes = knowledge_engine.get_methode_etapes(notion, niveau="debutant")
        self.assertEqual(etapes, notion["methode"]["etapes"])


class TestSearchServiceExercicesInchange(unittest.TestCase):
    """search_exercises_in_chapter (pré-existant) doit continuer à ne jamais
    sortir du chapitre demandé, avec ou sans le nouveau champ topic_id."""

    def test_scope_strictement_le_chapitre(self):
        results = search_service.search_exercises_in_chapter("Chapitre_2", limit=5)
        for r in results:
            self.assertEqual(r["chapter_id"], "Chapitre_2")

    def test_chapitre_inexistant_renvoie_liste_vide(self):
        self.assertEqual(search_service.search_exercises_in_chapter("Chapitre_99", limit=5), [])

    def test_filtre_difficulte_traduit_les_vocabulaires(self):
        """Bug corrigé lors de l'audit de généralisation KE v2 : le filtre
        difficulty ("easy"/"hard", intent_service) ne matchait jamais
        d["difficulty"] (entier 1-5, exercises_bank.json) — comparaison
        directe entre deux vocabulaires incompatibles, toujours fausse.
        Vérifie que le filtre restreint désormais réellement les résultats."""
        docs_by_id = {d["exercise_id"]: d for d in search_service._load_exercise_documents()}
        easy = search_service.search_exercises_in_chapter("Chapitre_1", difficulty="easy", limit=50)
        self.assertGreater(len(easy), 0)
        for r in easy:
            label = knowledge_engine.EXERCISES_BANK_SCALE_TO_LABEL.get(docs_by_id[r["exercise_id"]]["difficulty"])
            self.assertEqual(label, "facile")

    def test_resultat_exercice_porte_toujours_les_champs_historiques(self):
        results = search_service.search_exercises_in_chapter("Chapitre_1", limit=1)
        self.assertEqual(len(results), 1)
        for champ in ("type", "chapter_id", "notion", "exercise_id", "title", "snippet", "score", "url"):
            self.assertIn(champ, results[0])


if __name__ == "__main__":
    unittest.main()
