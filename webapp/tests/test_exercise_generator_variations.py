"""Suite du moteur symbolique "Variations d'une fonction" / "Nombre dérivé
et extremums locaux" (webapp/exercise_generator/variations.py).

Suit le même patron que test_exercise_generator_derivatives.py : diversité
réelle des structures (pas seulement les coefficients), difficulté qui
reflète la complexité réelle, absence de répétition immédiate, validité
mathématique garantie par calcul formel, et cohérence avec les deux notions
exactes du Chapitre_4 audités comme redondantes.
"""
import random
import unittest
from statistics import mean

import sympy

from exercise_generator import variations as gen


class TestValiditeMathematique(unittest.TestCase):
    """Chaque exercice généré doit contenir une réponse et des étapes de
    résolution non vides ; les calculs eux-mêmes (dérivée, signe, racines)
    sont faits par sympy dans build_exercise, jamais par un texte inventé."""

    def test_toutes_les_familles_produisent_un_exercice_valide(self):
        rng = random.Random(1)
        for family in gen.FAMILIES:
            produced = 0
            for _ in range(30):
                ex = gen.build_exercise(family, rng)
                if ex is None:
                    continue
                produced += 1
                self.assertTrue(ex["enonce"])
                self.assertTrue(ex["answer"])
                self.assertTrue(ex["solution_steps"])
                self.assertEqual(ex["chapter_id"], "Chapitre_4")
                self.assertIn(ex["notion"], (gen.NOTION_VARIATIONS, gen.NOTION_EXTREMUMS))
            self.assertGreater(produced, 0, f"La famille {family.id!r} n'a jamais produit d'exercice valide.")

    def test_extremum_inverse_verifie_bien_fprime_nulle(self):
        """Vérification indépendante : pour la famille inversée, on
        recalcule f'(x0) avec la valeur de p renvoyée et on vérifie qu'elle
        s'annule bien (garantie mathématique forte, pas juste textuelle)."""
        rng = random.Random(3)
        fam = gen.FAMILIES_BY_ID["extremum_inverse"]
        checked = 0
        for _ in range(30):
            ex = gen.build_exercise(fam, rng)
            if ex is None:
                continue
            checked += 1
            p_value = sympy.sympify(ex["answer"].split("=", 1)[1].strip().rstrip("$"))
            # On relit x0 depuis l'énoncé : "en $x = {x0}$."
            import re
            m = re.search(r"x = (-?\d+)\$", ex["enonce"])
            self.assertIsNotNone(m)
            x0 = int(m.group(1))
            p_sym = sympy.symbols("p")
            f_expr = gen.x**3 + p_sym * gen.x
            fprime = sympy.diff(f_expr, gen.x).subs(p_sym, p_value)
            self.assertEqual(sympy.simplify(fprime.subs(gen.x, x0)), 0)
        self.assertGreater(checked, 0)

    def test_variations_homographique_signe_f_prime_verifie_independamment(self):
        """Audit calcul-diversité Première : nouvelle famille couvrant une
        fonction homographique (ax+b)/(cx+d). On reparse numérateur et
        dénominateur depuis l'énoncé, on recalcule f'(x) INDÉPENDAMMENT par
        la règle du quotient (pas via build_exercise), et on vérifie que son
        signe en un point hors domaine interdit correspond bien au sens de
        variation annoncé."""
        import re

        from sympy.parsing.sympy_parser import (
            implicit_multiplication_application, parse_expr, standard_transformations,
        )
        transformations = standard_transformations + (implicit_multiplication_application,)

        rng = random.Random(11)
        fam = gen.FAMILIES_BY_ID["variations_homographique"]
        checked = 0
        for _ in range(60):
            ex = gen.build_exercise(fam, rng)
            if ex is None:
                continue
            m = re.search(r"f\(x\) = \\dfrac\{([^{}]*)\}\{([^{}]*)\}", ex["enonce"])
            self.assertIsNotNone(m, ex["enonce"])
            numer_text, denom_text = m.groups()
            numer_expr = parse_expr(numer_text, local_dict={"x": gen.x}, transformations=transformations)
            denom_expr = parse_expr(denom_text, local_dict={"x": gen.x}, transformations=transformations)
            f_expr = numer_expr / denom_expr
            fprime = sympy.simplify(sympy.diff(f_expr, gen.x))
            pole = sympy.solve(sympy.Eq(denom_expr, 0), gen.x)[0]
            val = sympy.simplify(fprime.subs(gen.x, pole + 1))
            self.assertNotEqual(val, 0)
            expected_sens = "croissante" if val > 0 else "décroissante"
            self.assertIn(f"est {expected_sens}", ex["answer"])
            checked += 1
        self.assertGreater(checked, 0)

    def test_variations_racine_domaine_et_sens_coherents(self):
        """Nouvelle famille couvrant f(x)=sqrt(ax+b) : le sens de variation
        annoncé doit correspondre au signe de a (racine composée avec une
        expression affine, croissante ssi a>0), recalculé indépendamment
        depuis l'expression reparsée sous la racine."""
        import re

        from sympy.parsing.sympy_parser import (
            implicit_multiplication_application, parse_expr, standard_transformations,
        )
        transformations = standard_transformations + (implicit_multiplication_application,)

        rng = random.Random(12)
        fam = gen.FAMILIES_BY_ID["variations_racine"]
        checked = 0
        for _ in range(60):
            ex = gen.build_exercise(fam, rng)
            if ex is None:
                continue
            m = re.search(r"f\(x\) = \\sqrt\{([^{}]*)\}", ex["enonce"])
            self.assertIsNotNone(m, ex["enonce"])
            inner_expr = parse_expr(m.group(1), local_dict={"x": gen.x}, transformations=transformations)
            a = inner_expr.coeff(gen.x, 1)
            self.assertNotEqual(a, 0)
            expected_sens = "croissante" if a > 0 else "décroissante"
            self.assertIn(f"est {expected_sens}", ex["answer"])
            checked += 1
        self.assertGreater(checked, 0)

    def test_optimisation_quotient_x0_minimise_bien_le_cout_moyen(self):
        """Nouvelle famille d'optimisation à quotient (coût moyen a·x+b/x) :
        on reparse x0 annoncé depuis la réponse et on vérifie
        INDÉPENDAMMENT, via sympy, que C'(x0)=0 et que C'(x) change bien de
        signe de négatif à positif en x0 (condition suffisante de minimum),
        pas seulement que le texte "a l'air correct"."""
        import re

        rng = random.Random(13)
        fam = gen.FAMILIES_BY_ID["optimisation_quotient"]
        checked = 0
        for _ in range(30):
            ex = gen.build_exercise(fam, rng)
            if ex is None:
                continue
            m_ab = re.search(r"C\(x\) = (\d*) ?x \+ \\frac\{(\d+)\}\{x\}", ex["enonce"])
            self.assertIsNotNone(m_ab, ex["enonce"])
            a = int(m_ab.group(1)) if m_ab.group(1) else 1
            b = int(m_ab.group(2))
            m_x0 = re.search(r"x = (\d+)", ex["answer"])
            self.assertIsNotNone(m_x0, ex["answer"])
            x0 = int(m_x0.group(1))

            C_expr = a * gen.x + sympy.Rational(b, 1) / gen.x
            Cprime = sympy.diff(C_expr, gen.x)
            self.assertEqual(sympy.simplify(Cprime.subs(gen.x, x0)), 0)
            self.assertLess(sympy.simplify(Cprime.subs(gen.x, x0 - sympy.Rational(1, 2))), 0)
            self.assertGreater(sympy.simplify(Cprime.subs(gen.x, x0 + sympy.Rational(1, 2))), 0)
            checked += 1
        self.assertGreater(checked, 0)


class TestDiversiteReelle(unittest.TestCase):
    """La diversité doit porter sur la STRUCTURE (famille), pas seulement
    sur les coefficients."""

    def test_16_exercices_couvrent_au_moins_6_familles(self):
        pool = gen.generate_pool(per_family=2, seed=42)[:16]
        familles_utilisees = {e["family"] for e in pool}
        self.assertGreaterEqual(
            len(familles_utilisees), 6,
            "Moins de 6 familles distinctes sur les 16 premiers exercices : "
            "pas assez de diversité structurelle réelle.",
        )

    def test_les_deux_notions_sont_couvertes(self):
        pool = gen.generate_pool(per_family=5, seed=42)
        notions = {e["notion"] for e in pool}
        self.assertEqual(notions, {gen.NOTION_VARIATIONS, gen.NOTION_EXTREMUMS})

    def test_aucun_doublon_dans_un_pool(self):
        pool = gen.generate_pool(per_family=8, seed=123)
        signatures = [(e["family"], e["enonce"]) for e in pool]
        self.assertEqual(len(signatures), len(set(signatures)), "Des exercices identiques ont été générés.")

    def test_ids_generes_uniques_et_entiers(self):
        pool = gen.generate_pool(per_family=8, seed=99)
        ids = [e["id"] for e in pool]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(isinstance(i, int) for i in ids))
        self.assertTrue(all(i >= gen.GENERATED_ID_OFFSET for i in ids))

    def test_offset_distinct_du_moteur_derivees(self):
        from exercise_generator import derivatives
        self.assertNotEqual(gen.GENERATED_ID_OFFSET, derivatives.GENERATED_ID_OFFSET)


class TestAntiRepetition(unittest.TestCase):
    def test_pas_deux_exercices_consecutifs_de_meme_famille(self):
        pool = gen.generate_pool(per_family=8, seed=2026)
        familles = [e["family"] for e in pool]
        repeats = sum(1 for i in range(1, len(familles)) if familles[i] == familles[i - 1])
        self.assertEqual(repeats, 0, "Deux exercices consécutifs de la même famille dans le pool généré.")


class TestDifficulteReelle(unittest.TestCase):
    def test_score_croit_globalement_avec_le_niveau_declare(self):
        pool = gen.generate_pool(per_family=10, seed=2026)
        by_level = {}
        for ex in pool:
            by_level.setdefault(ex["declared_level"], []).append(ex["complexity_score"])
        levels = sorted(by_level)
        averages = [mean(by_level[lvl]) for lvl in levels]
        for i in range(1, len(averages)):
            self.assertGreaterEqual(
                averages[i], averages[i - 1] - 0.5,
                f"Difficulté réelle non croissante entre niveau {levels[i-1]} et {levels[i]} : "
                f"{averages[i-1]:.2f} -> {averages[i]:.2f}",
            )

    def test_badge_visuel_coherent_avec_le_niveau(self):
        for level, meta in gen.LEVEL_META.items():
            self.assertIn(meta["emoji"], "🟢🟡🟠🔴🟣")
            self.assertIn(str(level), meta["label"] or "")


class TestCoherenceNiveauScolaire(unittest.TestCase):
    def test_tous_les_exercices_generes_ciblent_le_bon_chapitre(self):
        pool = gen.generate_pool(per_family=5, seed=1)
        for ex in pool:
            self.assertEqual(ex["chapter_id"], "Chapitre_4")

    def test_serie_de_generations_reproductible(self):
        pool_a = gen.generate_pool(per_family=5, seed=555)
        pool_b = gen.generate_pool(per_family=5, seed=555)
        self.assertEqual([e["enonce"] for e in pool_a], [e["enonce"] for e in pool_b])


if __name__ == "__main__":
    unittest.main()
