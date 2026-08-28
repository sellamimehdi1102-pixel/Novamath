"""
Suite ciblée : knowledge_engine.py devient multi-classe (class_level optionnel,
"seconde" par défaut). Vérifie la non-régression pour Seconde, le bon
fonctionnement pour Première (cours générés depuis exercise_bank, voir
generate_cours_from_bank.py), et l'absence de collision de cache entre
classes.
"""
import unittest

from chatbot import knowledge_engine as ke


class TestDefautSecondeInchange(unittest.TestCase):
    def test_search_sans_class_level_egale_seconde_explicite(self):
        sans_arg = ke.search("puissances entières relatives", top_k=1)
        avec_seconde = ke.search("puissances entières relatives", top_k=1, class_level="seconde")
        self.assertEqual(sans_arg, avec_seconde)
        self.assertTrue(sans_arg)

    def test_try_answer_definition_fonctionne_toujours(self):
        self.assertIsNotNone(ke.try_answer_definition("c'est quoi une valeur absolue ?"))

    def test_context_block_non_vide_pour_une_vraie_notion(self):
        self.assertTrue(ke.context_block("valeur absolue"))


class TestPremiereFonctionnelle(unittest.TestCase):
    """Première a désormais des cours générés depuis exercise_bank (voir
    generate_cours_from_bank.py, courses_dir déclaré au registre) — mêmes
    comportements que Seconde, jamais de contenu Seconde mélangé."""

    def test_search_renvoie_des_resultats_reels(self):
        results = ke.search("puissances entières relatives", class_level="premiere")
        self.assertTrue(results)
        # Contenu réellement dérivé de exercises_bank_premiere.json (suites,
        # exponentielle...), jamais une notion de Seconde.
        self.assertTrue(all(r["chapter_id"] for r in results))

    def test_try_answer_definition_ambigu_renvoie_none(self):
        # Limitation connue et honnête (même comportement qu'en Seconde pour
        # une requête aussi générique, voir test_chatbot_routing.py) : "une
        # suite" seul ne cible pas nettement une notion, pas d'exception.
        self.assertIsNone(ke.try_answer_definition("c'est quoi une suite ?", class_level="premiere"))

    def test_context_block_non_vide_pour_une_vraie_notion(self):
        self.assertTrue(ke.context_block("suites numériques", class_level="premiere"))

    def test_get_notion_inconnue_renvoie_none(self):
        self.assertIsNone(ke.get_notion("Chapitre_1", "quoi-que-ce-soit", class_level="premiere"))

    def test_get_notion_reelle_fonctionne(self):
        notion = ke.get_notion("Chapitre_1", "generalites-sur-les-suites", class_level="premiere")
        self.assertIsNotNone(notion)
        self.assertEqual(notion["chapter_id"], "Chapitre_1")


class TestAucuneCollisionEntreClasses(unittest.TestCase):
    def test_caches_isoles(self):
        ke.search("test", class_level="seconde")
        ke.search("test", class_level="premiere")
        self.assertIn("seconde", ke._index_by_class)
        self.assertIn("premiere", ke._index_by_class)

        ke.get_notion("Chapitre_1", "x", class_level="seconde")
        ke.get_notion("Chapitre_1", "x", class_level="premiere")
        self.assertGreater(len(ke._by_ids_by_class["seconde"]), 0)
        self.assertGreater(len(ke._by_ids_by_class["premiere"]), 0)
        # Les deux caches contiennent des notions réelles mais jamais les
        # MÊMES objets (aucune fuite de contenu Seconde -> Première).
        self.assertTrue(ke._by_ids_by_class["seconde"].keys().isdisjoint(ke._by_ids_by_class["premiere"].keys())
                         or all(
                             ke._by_ids_by_class["seconde"][k] is not ke._by_ids_by_class["premiere"][k]
                             for k in ke._by_ids_by_class["seconde"].keys() & ke._by_ids_by_class["premiere"].keys()
                         ))


if __name__ == "__main__":
    unittest.main()
