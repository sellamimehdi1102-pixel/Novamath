"""Cohérence exercices/chatbot (chantier pédagogique Phase 4, étendu par le
chantier de diversification des exercices) : le pool généré par
webapp/exercise_generator/ (fusionné dans server.py::_class_bank pour le mode
Exercices du site) doit aussi être visible par
chatbot/services/search_service.py — sinon le chatbot ("donne-moi un exercice
sur les dérivées") ne peut jamais proposer un exercice généré que l'élève
voit pourtant déjà dans le mode Exercices, deux sources de vérité qui
divergent silencieusement.

Depuis le chantier de diversification, le pool généré n'est plus limité à
derivatives.py/Chapitre_3 : il combine 4 modules (derivatives, suites,
exponentielle, variations — voir tools/generate_derivative_exercises.py),
couvrant Chapitre_1/3/4/5. Chaque module a son propre GENERATED_ID_OFFSET
(900_000/910_000/920_000/930_000, voir chaque module) — DERIVATIVES_ID_OFFSET
isole ici le sous-ensemble historique pour vérifier que son chapitre n'a pas
changé, sans supposer que TOUS les exercices générés partagent ce chapitre.

Depuis le lot Seconde (droites/inéquations, Chapitre_6/9 — voir
webapp/exercise_generator_seconde/), Seconde a elle aussi un
generated_exercise_bank (exercises_generated_seconde.json, offsets 800_000 et
810_000 — distincts de la plage 900_000+ de Première et non testés ici) :
l'ancien test "Seconde reste inchangée" est devenu un changement DÉLIBÉRÉ,
remplacé ci-dessous par une vérification symétrique à celle de Première."""
import unittest

from chatbot.services import search_service

GENERATED_ID_OFFSET = 900_000
DERIVATIVES_ID_OFFSET = 900_000
DERIVATIVES_ID_CEILING = 910_000  # borne haute exclusive : tout id < 910_000 vient de derivatives.py

SECONDE_GENERATED_ID_OFFSET = 800_000
SECONDE_GENERATED_ID_CEILING = 900_000  # borne haute exclusive : tout id < 900_000 dans ce pool vient de Seconde


class TestExercicesGeneresVisiblesParLeChatbot(unittest.TestCase):
    def test_load_exercise_documents_inclut_le_pool_genere(self):
        docs = search_service._load_exercise_documents("premiere")
        generated = [d for d in docs if d["exercise_id"] >= GENERATED_ID_OFFSET]
        self.assertTrue(generated, "Aucun exercice généré trouvé dans l'index de recherche du chatbot.")

        derivatives_docs = [d for d in generated if d["exercise_id"] < DERIVATIVES_ID_CEILING]
        self.assertTrue(derivatives_docs, "Le pool généré historique (derivatives.py) a disparu.")
        self.assertTrue(all(d["chapter_id"] == "Chapitre_3" for d in derivatives_docs))

        # Depuis la diversification, le pool généré couvre aussi d'autres
        # chapitres (suites/variations/exponentielle) : régression si un
        # nouveau module cesse d'être indexé par le chatbot.
        other_chapters = {d["chapter_id"] for d in generated if d["exercise_id"] >= DERIVATIVES_ID_CEILING}
        self.assertTrue(
            other_chapters - {"Chapitre_3"},
            "Aucun exercice généré hors Chapitre_3/derivatives.py n'est visible par le chatbot "
            "— les modules suites/exponentielle/variations semblent absents de l'index.",
        )

    def test_search_exercises_in_chapter_peut_renvoyer_un_exercice_genere(self):
        matched = search_service.search_exercises_in_chapter(
            "Chapitre_3", query="dérivée", limit=50, class_level="premiere",
        )
        self.assertTrue(
            any(m["exercise_id"] >= GENERATED_ID_OFFSET for m in matched),
            "search_exercises_in_chapter ne renvoie jamais d'exercice généré.",
        )

    def test_resolve_fonctionne_pour_un_exercice_genere(self):
        resolved = search_service.resolve(
            search_service.SCOPE_EXERCICES, exercise_id=GENERATED_ID_OFFSET, class_level="premiere",
        )
        self.assertIsNotNone(resolved)

    def test_seconde_a_maintenant_un_pool_genere_visible_par_le_chatbot(self):
        """Depuis le lot Seconde (droites/inéquations), Seconde a un
        generated_exercise_bank déclaré dans le registre (offsets 800_000 et
        810_000, voir webapp/exercise_generator_seconde/) : le chatbot doit
        pouvoir proposer ces exercices, exactement comme pour Première."""
        docs = search_service._load_exercise_documents("seconde")
        generated = [
            d for d in docs
            if SECONDE_GENERATED_ID_OFFSET <= d["exercise_id"] < SECONDE_GENERATED_ID_CEILING
        ]
        self.assertTrue(generated, "Aucun exercice généré Seconde trouvé dans l'index de recherche du chatbot.")
        self.assertTrue(all(d["chapter_id"] in {"Chapitre_6", "Chapitre_9"} for d in generated))

    def test_search_exercises_in_chapter_peut_renvoyer_un_exercice_genere_seconde(self):
        matched = search_service.search_exercises_in_chapter(
            "Chapitre_6", query="droite", limit=50, class_level="seconde",
        )
        self.assertTrue(
            any(m["exercise_id"] >= SECONDE_GENERATED_ID_OFFSET for m in matched),
            "search_exercises_in_chapter (Seconde) ne renvoie jamais d'exercice généré.",
        )

    def test_resolve_fonctionne_pour_un_exercice_genere_seconde(self):
        resolved = search_service.resolve(
            search_service.SCOPE_EXERCICES, exercise_id=SECONDE_GENERATED_ID_OFFSET, class_level="seconde",
        )
        self.assertIsNotNone(resolved)


if __name__ == "__main__":
    unittest.main()
