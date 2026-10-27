"""Générateurs de la classe « Première spécifique » (`premiere_specifique`, non
publiée) mis en réserve ou partiellement repris lors de l'adaptation au manuel
« Première ES/L » (2026-10-26) : logique_ensembles et listes_python (anciens
chapitres 11 et 12, hors manuel), automatismes (ancien chapitre 13, familles
redistribuées dans les chapitres 1, 2, 3, 4 et 8).

Garanties conservées sur leur code (il reste réutilisable) : pool déterministe,
identifiants dans le bloc du module, niveaux cohérents, et pour les programmes
Python, sortie annoncée égale à la sortie réelle. Garantie ajoutée : leurs
familles hors manuel ne sont plus exposées par la génération à la demande.
"""
import html
import re
import unittest

from exercise_generator import registry
from exercise_generator_premiere_specifique import automatismes, listes_python, logique_ensembles, programme_1es
from tests.premiere_specifique_preview import serve_in_preview

MODULES = (
    (logique_ensembles, 20261028, "Chapitre_11"),
    (listes_python, 20261027, "Chapitre_12"),
    (automatismes, 20261029, "Chapitre_13"),
)


class TestPoolsDeterministes(unittest.TestCase):
    def test_pools(self):
        for module, seed, chapter in MODULES:
            with self.subTest(module=module.__name__):
                pool = module.generate_pool(32, seed)
                self.assertEqual(pool, module.generate_pool(32, seed))
                self.assertEqual(len(pool), 32 * len(module.FAMILIES))
                ids = [e["id"] for e in pool]
                self.assertEqual(len(ids), len(set(ids)))
                self.assertTrue(all(module.GENERATED_ID_OFFSET <= i < module.GENERATED_ID_OFFSET + 1000 * len(module.FAMILIES) for i in ids))
                self.assertEqual({e["chapter_id"] for e in pool}, {chapter})
                self.assertEqual(len({e["enonce"] for e in pool}), len(pool))
                for e in pool:
                    self.assertIn(e["difficulty"], (1, 2, 3, 4))
                    self.assertTrue(e["answer"] and e["hint"] and e["solution_steps"])
                    self.assertNotIn(e["hint"], e["answer"])


class TestListesPythonExecutes(unittest.TestCase):
    """Le programme affiché (après décodage HTML) produit la sortie annoncée."""

    def test_sortie_annoncee(self):
        for e in listes_python.generate_pool(32, 20261027):
            codes = re.findall(r"<code>(.*?)</code>", e["enonce"], flags=re.S)
            src = "\n".join(html.unescape(c).replace("\xa0", " ") for c in codes)
            sortie = html.unescape(" ".join(re.findall(r"<code>(.*?)</code>", e["answer"], flags=re.S))).replace("\xa0", " ")
            with self.subTest(id=e["id"]):
                self.assertEqual(listes_python.run(src), sortie)


class TestExpositionApresAdaptation(unittest.TestCase):
    def setUp(self):
        serve_in_preview(self)

    def test_logique_et_listes_non_exposees(self):
        notions = registry.available_notions("premiere_specifique")
        exposees = {f["family_id"] for fams in notions.values() for f in fams}
        chapitres = {k[1] for k in notions}
        self.assertTrue(chapitres <= {f"Chapitre_{n}" for n in range(1, 10)}, chapitres)
        for module in (logique_ensembles, listes_python):
            for family in module.FAMILIES:
                self.assertIsNone(registry.generate("premiere_specifique", "Chapitre_11", family.notion, family.id, seed=7))
                self.assertIsNone(registry.generate("premiere_specifique", "Chapitre_12", family.notion, family.id, seed=7))
        self.assertNotIn("droite", exposees)

    def test_automatismes_redistribues(self):
        for fid, (chapitre, notion) in programme_1es.ADAPTATION[automatismes].items():
            with self.subTest(famille=fid):
                ex = registry.generate("premiere_specifique", chapitre, notion, fid, seed=7)
                self.assertIsNotNone(ex)
                self.assertEqual((ex["chapter_id"], ex["notion"]), (chapitre, notion))


class TestNonPublieeHorsPrevisualisation(unittest.TestCase):
    def test_generation_refusee_quand_la_classe_n_est_pas_servie(self):
        self.assertEqual(registry.available_notions("premiere_specifique"), {})
        fid, (chapitre, notion) = next(iter(programme_1es.ADAPTATION[automatismes].items()))
        self.assertIsNone(registry.generate("premiere_specifique", chapitre, notion, fid, seed=7))


if __name__ == "__main__":
    unittest.main()
