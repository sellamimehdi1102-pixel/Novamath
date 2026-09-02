"""Cohérence exercices/chatbot pour le pool généré Troisième (chantier de
diversification, lot 2026-08, étendu par les missions "rééquilibrage global
de toutes les classes" et "équilibrage définitif de toutes les classes"
2026-09-01 — pendant de test_search_service_generated_exercises.py pour
Première) : le pool produit par webapp/exercise_generator_troisieme/
(fusionné dans server.py::_class_bank pour le mode Exercices du site, via
curriculum_registry.CurriculumProfile "troisieme".generated_exercise_bank)
doit aussi être visible par chatbot/services/search_service.py.

14 modules déclarés (equation_premier_degre/divisibilite/fractions_addition/
fractions_simplification/fonction_affine_deux_points/
developper_distributivite/factoriser_somme/image_fonction/nombres_relatifs/
proportionnalite/statistiques/probabilites_troisieme/thales/volumes_espace —
voir tools/generate_troisieme_exercises.py), chacun avec son propre
GENERATED_ID_OFFSET (100_000 à 230_000), couvrant Chapitre_1 à Chapitre_10,
Chapitre_14 et Chapitre_15.
"""
import unittest

from chatbot.services import search_service

GENERATED_ID_OFFSET = 100_000
GENERATED_ID_CEILING = 240_000  # borne haute exclusive : distincte des offsets Première (900_000+)


class TestExercicesGeneresTroisiemeVisiblesParLeChatbot(unittest.TestCase):
    def test_load_exercise_documents_inclut_le_pool_genere(self):
        docs = search_service._load_exercise_documents("troisieme")
        generated = [d for d in docs if GENERATED_ID_OFFSET <= d["exercise_id"] < GENERATED_ID_CEILING]
        self.assertTrue(generated, "Aucun exercice généré Troisième trouvé dans l'index de recherche du chatbot.")
        chapters = {d["chapter_id"] for d in generated}
        self.assertEqual(chapters, {
            "Chapitre_1", "Chapitre_2", "Chapitre_3", "Chapitre_4", "Chapitre_5",
            "Chapitre_6", "Chapitre_7", "Chapitre_8", "Chapitre_9", "Chapitre_10",
            "Chapitre_14", "Chapitre_15",
        })

    def test_search_exercises_in_chapter_peut_renvoyer_un_exercice_genere(self):
        matched = search_service.search_exercises_in_chapter(
            "Chapitre_5", query="équation", limit=50, class_level="troisieme",
        )
        self.assertTrue(
            any(GENERATED_ID_OFFSET <= m["exercise_id"] < GENERATED_ID_CEILING for m in matched),
            "search_exercises_in_chapter ne renvoie jamais d'exercice généré Troisième.",
        )

    def test_resolve_fonctionne_pour_un_exercice_genere(self):
        resolved = search_service.resolve(
            search_service.SCOPE_EXERCICES, exercise_id=GENERATED_ID_OFFSET, class_level="troisieme",
        )
        self.assertIsNotNone(resolved)

    def test_seconde_reste_inchangee_sans_pool_genere_troisieme(self):
        """Seconde n'a toujours pas de generated_exercise_bank déclaré :
        régression si le pool Troisième "fuit" vers un autre niveau."""
        docs = search_service._load_exercise_documents("seconde")
        self.assertFalse(any(GENERATED_ID_OFFSET <= d["exercise_id"] < GENERATED_ID_CEILING for d in docs))

    def test_premiere_reste_inchangee_sans_collision_avec_le_pool_troisieme(self):
        """Le pool généré Première (offsets 900_000+) ne doit jamais se
        mélanger avec celui de Troisième (100_000-170_000)."""
        docs = search_service._load_exercise_documents("premiere")
        self.assertFalse(any(GENERATED_ID_OFFSET <= d["exercise_id"] < GENERATED_ID_CEILING for d in docs))


if __name__ == "__main__":
    unittest.main()
