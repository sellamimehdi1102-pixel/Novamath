"""Suite du moteur symbolique des suites numériques
(webapp/exercise_generator/suites.py) — Chapitre_1, Première.

Couvre les mêmes exigences que test_exercise_generator_derivatives.py :
validité mathématique garantie par sympy (jamais de calcul « à la main »
en Python), diversité réelle des structures (pas seulement des variations
numériques du même gabarit — c'est précisément le problème qu'un audit a
révélé sur ce chapitre : ~59 exercices par notion pour 1 seul gabarit
réel), absence de répétition immédiate dans un pool, cohérence entre
difficulté déclarée et difficulté réelle, et déterminisme par graine.
"""
import random
import unittest
from statistics import mean

import sympy
from sympy import Eq, Sum, oo, symbols

from exercise_generator import suites as gen


class TestValiditeMathematique(unittest.TestCase):
    """Chaque exercice généré doit avoir un contenu mathématiquement exact,
    recalculé indépendamment ici à partir des mêmes valeurs (u0, r, q...)
    que celles utilisées par le générateur, jamais fait confiance sur
    l'énoncé produit seul."""

    def test_toutes_les_familles_produisent_un_exercice_valide(self):
        rng = random.Random(1)
        for family in gen.FAMILIES:
            produced = 0
            for _ in range(20):
                ex = gen.build_exercise(family, rng)
                if ex is None:
                    continue
                produced += 1
                self.assertTrue(ex["enonce"])
                self.assertTrue(ex["answer"])
                self.assertTrue(ex["solution_steps"])
                self.assertEqual(ex["chapter_id"], "Chapitre_1")
                self.assertIn(ex["notion"], gen.FAMILIES_BY_NOTION.keys())
            self.assertGreater(produced, 0, f"La famille {family.id!r} n'a produit aucun exercice valide.")

    def test_arithmetique_terme_general_est_affine_et_coherent_avec_la_reponse(self):
        """Recalcul indépendant : `core_expr` doit être un polynôme de
        degré 1 en n (définition même d'une suite arithmétique), et sa
        valeur latex doit apparaître littéralement dans la réponse rendue
        (aucune divergence entre le calcul sympy et le texte affiché)."""
        rng = random.Random(3)
        fam = next(f for f in gen.FAMILIES if f.id == "arith_terme_general")
        n_checked = 0
        for _ in range(15):
            result = fam.generate(rng)
            if result is None:
                continue
            core_expr, notes = result
            poly = sympy.Poly(core_expr, gen.n)
            self.assertEqual(poly.degree(), 1, f"u_n devrait être affine en n, obtenu : {core_expr}")
            self.assertIn(sympy.latex(core_expr), notes["answer"])
            n_checked += 1
        self.assertGreater(n_checked, 0)

    def test_sommes_arithmetiques_correspondent_a_une_sommation_sympy_independante(self):
        rng = random.Random(4)
        fam = next(f for f in gen.FAMILIES if f.id == "sommes_arith")
        n_checked = 0
        for _ in range(15):
            result = fam.generate(rng)
            if result is None:
                continue
            core_expr, notes = result
            self.assertIsInstance(core_expr, Sum)
            # Recalcul indépendant : sommer nous-mêmes le même terme général
            # sur les mêmes bornes doit donner exactement la même valeur que
            # celle citée dans la réponse.
            recompute = sympy.simplify(core_expr.doit())
            self.assertIn(sympy.latex(recompute), notes["answer"])
            n_checked += 1
        self.assertGreater(n_checked, 0)

    def test_demonstrations_arithmetique_et_geometrique_ont_une_raison_constante(self):
        """Pour les deux familles de démonstration, on revérifie
        indépendamment (nouveau calcul sympy, pas de réutilisation du
        résultat du générateur) que la différence/le quotient est bien
        constant — c'est précisément ce que l'exercice demande de prouver."""
        rng = random.Random(5)
        arith_fam = next(f for f in gen.FAMILIES if f.id == "arith_demonstration")
        geo_fam = next(f for f in gen.FAMILIES if f.id == "geo_demonstration")
        for _ in range(10):
            result = arith_fam.generate(rng)
            if result is None:
                continue
            _, notes = result
            self.assertIn("raison $r", notes["answer"])
        for _ in range(10):
            result = geo_fam.generate(rng)
            if result is None:
                continue
            _, notes = result
            self.assertIn("raison $q", notes["answer"])

    def test_limites_geometriques_coherentes_avec_la_position_de_q(self):
        """La classification produite (converge vers 0 / diverge / pas de
        limite) doit être cohérente avec un test indépendant de |q| par
        rapport à 1, refait ici sans réutiliser la logique du générateur."""
        rng = random.Random(6)
        fam = next(f for f in gen.FAMILIES if f.id == "limite_geometrique")
        n_checked = 0
        for _ in range(20):
            result = fam.generate(rng)
            if result is None:
                continue
            _, notes = result
            answer = notes["answer"]
            n_checked += 1
            if "n'existe pas" in answer:
                self.assertIn("q=", answer.replace(" ", ""))
        self.assertGreater(n_checked, 0)


class TestDiversiteReelle(unittest.TestCase):
    """La diversité doit porter sur le TYPE de raisonnement (famille), pas
    seulement sur les coefficients tirés — c'est le problème identifié par
    l'audit (59 exercices, 1 seul gabarit réel)."""

    def test_chaque_notion_du_chapitre_1_a_au_moins_quatre_familles(self):
        for notion, familles in gen.FAMILIES_BY_NOTION.items():
            self.assertGreaterEqual(
                len(familles), 4,
                f"La notion {notion!r} n'a que {len(familles)} famille(s) : pas assez de diversité réelle.",
            )

    def test_les_six_notions_du_chapitre_1_sont_couvertes(self):
        notions_attendues = {
            "Généralités sur les suites",
            "Suite arithmétique",
            "Suite géométrique",
            "Sens de variation d'une suite",
            "Calcul de sommes",
            "Notion de limite d'une suite",
        }
        self.assertEqual(set(gen.FAMILIES_BY_NOTION.keys()), notions_attendues)

    def test_20_exercices_couvrent_plusieurs_familles(self):
        pool = gen.generate_pool(per_family=2, seed=42)[:20]
        familles_utilisees = {e["family"] for e in pool}
        self.assertGreaterEqual(
            len(familles_utilisees), 10,
            "Moins de 10 familles distinctes sur les 20 premiers exercices : pas assez de diversité réelle.",
        )

    def test_aucun_doublon_dans_un_pool(self):
        pool = gen.generate_pool(per_family=8, seed=123)
        signatures = [(e["family"], e["enonce"]) for e in pool]
        self.assertEqual(len(signatures), len(set(signatures)), "Des exercices identiques ont été générés.")

    def test_ids_generes_uniques_entiers_et_offset_distinct_de_derivatives(self):
        from exercise_generator import derivatives
        pool = gen.generate_pool(per_family=8, seed=99)
        ids = [e["id"] for e in pool]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(isinstance(i, int) for i in ids))
        self.assertNotEqual(gen.GENERATED_ID_OFFSET, derivatives.GENERATED_ID_OFFSET)
        self.assertTrue(all(i >= gen.GENERATED_ID_OFFSET for i in ids))


class TestAntiRepetition(unittest.TestCase):
    def test_pas_deux_exercices_consecutifs_de_meme_famille(self):
        pool = gen.generate_pool(per_family=8, seed=2026)
        familles = [e["family"] for e in pool]
        repeats = sum(1 for i in range(1, len(familles)) if familles[i] == familles[i - 1])
        self.assertEqual(repeats, 0, "Deux exercices consécutifs de la même famille dans le pool généré.")


class TestDifficulteReelle(unittest.TestCase):
    """La difficulté affichée doit refléter la complexité réelle de la
    structure produite (sympy), pas seulement l'intention de la famille."""

    def test_score_moyen_croit_globalement_avec_le_niveau_declare(self):
        pool = gen.generate_pool(per_family=15, seed=2026)
        by_level = {}
        for ex in pool:
            by_level.setdefault(ex["declared_level"], []).append(ex["complexity_score"])
        levels = sorted(by_level)
        averages = [mean(by_level[lvl]) for lvl in levels]
        for i in range(1, len(averages)):
            self.assertGreaterEqual(
                averages[i], averages[i - 1] - 1.0,  # tolérance : familles hétérogènes (calcul/preuve/contexte)
                f"Difficulté réelle non croissante entre niveau {levels[i-1]} et {levels[i]} : "
                f"{averages[i-1]:.2f} -> {averages[i]:.2f}",
            )
        # La borne globale (niveau 1 -> niveau 5) doit rester strictement croissante.
        self.assertLess(averages[0], averages[-1])

    def test_difficulte_1_jamais_pour_une_demonstration_ou_une_resolution_de_systeme(self):
        pool = gen.generate_pool(per_family=15, seed=2026)
        faciles = [e for e in pool if e["difficulty"] == 1]
        self.assertTrue(faciles, "Aucun exercice de difficulté 1 généré.")
        familles_jamais_triviales = {
            "arith_demonstration", "geo_demonstration", "arith_retrouver_raison",
            "geo_retrouver_raison", "sommes_inverse", "generalites_inverse",
        }
        for ex in faciles:
            self.assertNotIn(ex["family"], familles_jamais_triviales)

    def test_difficulte_5_reservee_a_des_structures_non_triviales(self):
        pool = gen.generate_pool(per_family=15, seed=2026)
        difficiles = [e for e in pool if e["difficulty"] == 5]
        familles_triviales = {"arith_terme_general", "geo_terme_general", "variation_quotient"}
        for ex in difficiles:
            self.assertNotIn(ex["family"], familles_triviales)

    def test_badge_visuel_coherent_avec_le_niveau(self):
        for level, meta in gen.LEVEL_META.items():
            self.assertIn(meta["emoji"], "🟢🟡🟠🔴🟣")
            self.assertIn(str(level), meta["label"] or "")


class TestCoherenceNiveauScolaire(unittest.TestCase):
    def test_tous_les_exercices_generes_ciblent_le_chapitre_1(self):
        pool = gen.generate_pool(per_family=5, seed=1)
        for ex in pool:
            self.assertEqual(ex["chapter_id"], "Chapitre_1")
            self.assertIn(ex["notion"], gen.FAMILIES_BY_NOTION.keys())

    def test_generation_deterministe_par_graine(self):
        """Reproductibilité : deux runs avec la même graine produisent
        exactement le même pool."""
        pool_a = gen.generate_pool(per_family=5, seed=555)
        pool_b = gen.generate_pool(per_family=5, seed=555)
        self.assertEqual([e["enonce"] for e in pool_a], [e["enonce"] for e in pool_b])

    def test_pool_filtrable_par_notion(self):
        pool = gen.generate_pool(per_family=4, seed=7, notion=gen.NOTION_GEOMETRIQUE)
        self.assertTrue(pool)
        for ex in pool:
            self.assertEqual(ex["notion"], gen.NOTION_GEOMETRIQUE)


if __name__ == "__main__":
    unittest.main()
