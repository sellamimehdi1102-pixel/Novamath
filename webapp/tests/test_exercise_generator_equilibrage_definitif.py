"""Tests des 3 nouveaux moteurs symboliques créés par la mission
"équilibrage définitif de toutes les classes" (2026-09-01) :
- webapp/exercise_generator_troisieme/volumes_espace.py (Chapitre_15) ;
- webapp/exercise_generator_seconde/vecteurs_seconde.py (Chapitre_5) ;
- webapp/exercise_generator_seconde/pourcentages_evolutions.py (Chapitre_10).

Même patron que test_exercise_generator_troisieme.py, adapté à leur
convention "notion portée par Family" (comme derivatives.py) plutôt que
"NOTION unique au niveau du module" (comme equation_premier_degre.py) — voir
webapp/exercise_generator/registry.py::_notion_of() pour cette distinction
déjà connue de l'architecture.
"""
import unittest

from exercise_generator_seconde import pourcentages_evolutions, vecteurs_seconde
from exercise_generator_troisieme import volumes_espace

MODULES = (volumes_espace, vecteurs_seconde, pourcentages_evolutions)


class TestContratCommunAuxTroisNouveauxModules(unittest.TestCase):
    def test_toutes_les_familles_representees_dans_un_pool(self):
        for mod in MODULES:
            pool = mod.generate_pool(per_family=10, seed=42)
            familles = {e["family"] for e in pool}
            self.assertEqual(familles, {f.id for f in mod.FAMILIES}, mod.__name__)

    def test_aucun_doublon_dans_un_pool(self):
        for mod in MODULES:
            pool = mod.generate_pool(per_family=12, seed=123)
            signatures = [(e["family"], e["enonce"]) for e in pool]
            self.assertEqual(len(signatures), len(set(signatures)), mod.__name__)

    def test_ids_generes_uniques_et_dans_l_offset_du_module(self):
        for mod in MODULES:
            pool = mod.generate_pool(per_family=10, seed=99)
            ids = [e["id"] for e in pool]
            self.assertEqual(len(ids), len(set(ids)), mod.__name__)
            self.assertTrue(
                all(mod.GENERATED_ID_OFFSET <= i < mod.GENERATED_ID_OFFSET + 10_000 for i in ids),
                mod.__name__,
            )

    def test_determinisme_du_seed(self):
        for mod in MODULES:
            pool_a = mod.generate_pool(per_family=8, seed=555)
            pool_b = mod.generate_pool(per_family=8, seed=555)
            self.assertEqual([e["enonce"] for e in pool_a], [e["enonce"] for e in pool_b], mod.__name__)

    def test_champs_requis_presents_et_chapter_id_fixe(self):
        for mod in MODULES:
            pool = mod.generate_pool(per_family=8, seed=8)
            self.assertTrue(pool, mod.__name__)
            for ex in pool:
                for field in ("enonce", "answer", "hint", "solution_steps", "chapter_id", "notion", "difficulty"):
                    self.assertIn(field, ex, mod.__name__)
                self.assertIsInstance(ex["difficulty"], int)
                self.assertTrue(1 <= ex["difficulty"] <= 5)
                self.assertTrue(ex["solution_steps"])
                self.assertEqual(ex["chapter_id"], mod.CHAPTER_ID)
                self.assertIn(ex["notion"], {f.notion for f in mod.FAMILIES})

    def test_difficulte_reelle_croissante_avec_le_niveau_declare(self):
        """Recalculé sur un pool réellement généré (pas seulement sur
        FAMILY_BASE_SCORE) pour détecter aussi une régression de calibrage
        introduite par _difficulty_bucket_from_score."""
        for mod in MODULES:
            pool = mod.generate_pool(per_family=15, seed=2026)
            by_level = {}
            for ex in pool:
                by_level.setdefault(ex["declared_level"], []).append(ex["difficulty"])
            levels = sorted(by_level)
            avgs = [sum(by_level[lvl]) / len(by_level[lvl]) for lvl in levels]
            for i in range(1, len(avgs)):
                self.assertGreaterEqual(avgs[i], avgs[i - 1], mod.__name__)

    def test_pas_deux_exercices_consecutifs_de_meme_famille(self):
        for mod in MODULES:
            pool = mod.generate_pool(per_family=8, seed=2026)
            familles = [e["family"] for e in pool]
            repeats = sum(1 for i in range(1, len(familles)) if familles[i] == familles[i - 1])
            self.assertEqual(repeats, 0, mod.__name__)

    def test_generate_one_fonctionne_pour_chaque_famille(self):
        for mod in MODULES:
            for family in mod.FAMILIES:
                ex = mod.generate_one(family.id, seed=1)
                self.assertEqual(ex["family"], family.id, mod.__name__)
                self.assertEqual(ex["chapter_id"], mod.CHAPTER_ID, mod.__name__)


if __name__ == "__main__":
    unittest.main()
