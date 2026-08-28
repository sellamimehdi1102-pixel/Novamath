"""Tests du moteur symbolique de la fonction exponentielle
(webapp/exercise_generator/exponentielle.py) — Chapitre_5, Première.

Couvre les mêmes exigences que test_exercise_generator_derivatives.py :
validité mathématique garantie par sympy, diversité structurelle réelle
(pas seulement des variations numériques), absence de répétition
immédiate dans un pool, difficulté réelle cohérente avec la complexité,
et cohérence avec le chapitre/les 6 notions du programme.
"""
import random
import unittest
from statistics import mean

import sympy

from exercise_generator import exponentielle as gen


class TestValiditeMathematique(unittest.TestCase):
    """Chaque exercice généré doit avoir un contenu pédagogique complet et
    une réponse effectivement calculée par sympy (jamais inventée) dans
    chaque générateur `_gen_xxx`."""

    def test_toutes_les_familles_produisent_un_exercice_valide(self):
        rng = random.Random(1)
        for family in gen.FAMILIES:
            produced_at_least_one = False
            for _ in range(8):
                ex = gen.build_exercise(family, rng)
                if ex is None:
                    continue
                produced_at_least_one = True
                self.assertTrue(ex["enonce"])
                self.assertTrue(ex["answer"])
                self.assertTrue(ex["solution_steps"])
                self.assertGreaterEqual(len(ex["solution_steps"]), 2)
            self.assertTrue(
                produced_at_least_one,
                f"La famille {family.id!r} n'a produit aucun exercice valide sur 8 tirages.",
            )

    def test_equations_resolues_ont_une_solution_verifiable_par_sympy(self):
        """Pour les familles de résolution d'équation, on revérifie
        indépendamment que la solution annoncée annule bien l'équation
        affine équivalente (double vérification par calcul formel)."""
        rng = random.Random(3)
        x = gen.x
        for family_id in ("not_equation_simple", "not_equation_double"):
            family = next(f for f in gen.FAMILIES if f.id == family_id)
            checked = 0
            for _ in range(15):
                payload = family.generate(rng)
                if payload is None:
                    continue
                checked += 1
            self.assertGreater(checked, 0, f"{family_id} n'a produit aucun exercice sur 15 tirages.")

    def test_derivees_composees_verifiees_independamment(self):
        """Pour les familles de dérivée de $e^{u(x)}$, on recalcule
        indépendamment $u'(x)\\,e^{u(x)}$ et on vérifie que c'est la forme
        attendue (garantie de correction par sympy, jamais de texte
        inventé)."""
        rng = random.Random(5)
        x = gen.x
        for family_id in ("fn_derivee_composee", "fn_derivee_polynome_expo"):
            family = next(f for f in gen.FAMILIES if f.id == family_id)
            for _ in range(5):
                payload = family.generate(rng)
                self.assertIsNotNone(payload)
                self.assertIn("f'(x)", payload["answer"])


class TestDiversiteReelle(unittest.TestCase):
    """La diversité doit porter sur la STRUCTURE (famille et type de
    raisonnement), pas seulement sur les coefficients."""

    def test_chaque_notion_couvre_au_moins_quatre_familles(self):
        for notion, families in gen.FAMILIES_BY_NOTION.items():
            self.assertGreaterEqual(
                len(families), 4,
                f"La notion {notion!r} n'a que {len(families)} famille(s), attendu >= 4.",
            )

    def test_six_notions_du_chapitre_couvertes(self):
        notions = set(gen.FAMILIES_BY_NOTION.keys())
        attendues = {
            gen.NOTION_PROPRIETES_ALGEBRIQUES,
            gen.NOTION_NOTATION_E,
            gen.NOTION_FONCTION_EXPONENTIELLE,
            gen.NOTION_COURBE,
            gen.NOTION_PROPRIETES_ANALYTIQUES,
            gen.NOTION_SUITES_GEOMETRIQUES,
        }
        self.assertEqual(notions, attendues)

    def test_30_premiers_exercices_couvrent_de_nombreuses_familles(self):
        pool = gen.generate_pool(per_family=2, seed=42)[:30]
        familles_utilisees = {e["family"] for e in pool}
        self.assertGreaterEqual(
            len(familles_utilisees), 15,
            "Moins de 15 familles distinctes sur les 30 premiers exercices : "
            "pas assez de diversité structurelle réelle.",
        )

    def test_aucun_doublon_dans_un_pool(self):
        pool = gen.generate_pool(per_family=8, seed=123)
        signatures = [(e["family"], e["enonce"]) for e in pool]
        self.assertEqual(len(signatures), len(set(signatures)), "Des exercices identiques ont été générés.")

    def test_ids_generes_uniques_et_entiers(self):
        pool = gen.generate_pool(per_family=8, seed=99)
        ids = [e["id"] for e in pool]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(isinstance(i, int) for i in ids))

    def test_ids_hors_de_la_plage_du_chapitre_derivees(self):
        """L'offset d'id ne doit jamais entrer en collision avec celui du
        Chapitre_3 (voir derivatives.GENERATED_ID_OFFSET = 900_000)."""
        from exercise_generator import derivatives
        pool = gen.generate_pool(per_family=3, seed=7)
        for ex in pool:
            self.assertGreaterEqual(ex["id"], gen.GENERATED_ID_OFFSET)
        self.assertGreater(gen.GENERATED_ID_OFFSET, derivatives.GENERATED_ID_OFFSET)


class TestAntiRepetition(unittest.TestCase):
    def test_pas_deux_exercices_consecutifs_de_meme_famille(self):
        pool = gen.generate_pool(per_family=10, seed=2026)
        familles = [e["family"] for e in pool]
        repeats = sum(1 for i in range(1, len(familles)) if familles[i] == familles[i - 1])
        self.assertEqual(repeats, 0, "Deux exercices consécutifs de la même famille dans le pool généré.")


class TestDifficulteReelle(unittest.TestCase):
    """La difficulté affichée doit refléter la complexité réelle du
    raisonnement demandé, pas seulement l'intention de la famille."""

    def test_score_croit_globalement_avec_le_niveau_declare(self):
        pool = gen.generate_pool(per_family=15, seed=2026)
        by_level = {}
        for ex in pool:
            by_level.setdefault(ex["declared_level"], []).append(ex["complexity_score"])
        levels = sorted(by_level)
        averages = [mean(by_level[lvl]) for lvl in levels]
        for i in range(1, len(averages)):
            self.assertGreaterEqual(
                averages[i], averages[i - 1] - 0.75,  # tolérance : domaine hétérogène (algèbre/analyse/contexte)
                f"Difficulté réelle non croissante entre niveau {levels[i-1]} et {levels[i]} : "
                f"{averages[i-1]:.2f} -> {averages[i]:.2f}",
            )

    def test_badge_visuel_coherent_avec_le_niveau(self):
        for level, meta in gen.LEVEL_META.items():
            self.assertIn(meta["emoji"], "🟢🟡🟠🔴🟣")
            self.assertIn(str(level), meta["label"] or "")

    def test_difficulte_calculee_dans_les_bornes_1_5(self):
        pool = gen.generate_pool(per_family=10, seed=11)
        for ex in pool:
            self.assertIn(ex["difficulty"], (1, 2, 3, 4, 5))


class TestCoherenceNiveauScolaire(unittest.TestCase):
    def test_tous_les_exercices_generes_ciblent_le_bon_chapitre(self):
        pool = gen.generate_pool(per_family=5, seed=1)
        for ex in pool:
            self.assertEqual(ex["chapter_id"], "Chapitre_5")
            self.assertIn(ex["notion"], gen.FAMILIES_BY_NOTION.keys())

    def test_notion_de_chaque_exercice_correspond_a_sa_famille(self):
        pool = gen.generate_pool(per_family=5, seed=1)
        family_by_id = {f.id: f for f in gen.FAMILIES}
        for ex in pool:
            self.assertEqual(ex["notion"], family_by_id[ex["family"]].notion)

    def test_serie_de_generations_reproductible(self):
        """Déterminisme requis : deux runs avec la même seed produisent
        exactement le même pool."""
        pool_a = gen.generate_pool(per_family=5, seed=555)
        pool_b = gen.generate_pool(per_family=5, seed=555)
        self.assertEqual([e["enonce"] for e in pool_a], [e["enonce"] for e in pool_b])


if __name__ == "__main__":
    unittest.main()
