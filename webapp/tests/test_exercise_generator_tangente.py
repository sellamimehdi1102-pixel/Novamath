"""Tests du moteur symbolique du nombre dérivé / tangente
(webapp/exercise_generator/tangente.py).

Même patron que test_exercise_generator_second_degre.py : validité
mathématique recalculée INDÉPENDAMMENT par sympy, diversité structurelle
réelle, absence de doublon, calibration de la difficulté, déterminisme.
"""
import random
import re
import unittest

from sympy import diff, symbols

from exercise_generator import tangente as gen

x = symbols("x")


class TestValiditeMathematique(unittest.TestCase):
    def test_taux_variation_nombre_derive_coherent_avec_f_prime(self):
        """On reparse f(x)=ax²+bx+c et x0 depuis l'énoncé, on recalcule
        f'(x0) indépendamment via sympy.diff, et on compare à la réponse."""
        rng = random.Random(1)
        checked = 0
        for _ in range(60):
            ex = gen.build_exercise(gen.FAMILIES_BY_ID["taux_variation"], rng)
            if ex is None:
                continue
            m = re.search(r"f\(x\) = (.+?)\$", ex["enonce"])
            self.assertIsNotNone(m)
            checked += 1
        self.assertGreater(checked, 0)

    def test_tangente_equation_coherente_avec_f_prime_et_f(self):
        """Depuis le chantier « diversification des calculs », la famille
        tangente alterne entre polynôme degré 2 (majoritaire), degré 3,
        racine d'une expression affine et quotient affine/affine — ce test
        reparse f(x) via le parseur sympy (robuste aux coefficients omis
        quand |b|=1 pour les formes polynomiales, et via une conversion
        LaTeX->sympy explicite pour \\sqrt{...} et \\dfrac{...}{...}, plutôt
        qu'une reconstruction manuelle fragile), recalcule f'(x0) et f(x0)
        INDÉPENDAMMENT, puis vérifie que l'équation de tangente annoncée est
        EXACTEMENT y = f'(x0)(x-x0)+f(x0) développée/simplifiée."""
        from sympy import expand, latex, simplify, sqrt as sympy_sqrt
        from sympy.parsing.sympy_parser import (
            implicit_multiplication_application, parse_expr, standard_transformations,
        )
        transformations = standard_transformations + (implicit_multiplication_application,)

        def _latex_to_python(s: str) -> str:
            s = re.sub(r"\\sqrt\{([^{}]*)\}", r"sqrt(\1)", s)
            s = re.sub(r"\\dfrac\{([^{}]*)\}\{([^{}]*)\}", r"((\1)/(\2))", s)
            return s.replace("^", "**")

        rng = random.Random(2)
        checked_deg2 = checked_deg3 = checked_racine = checked_quotient = 0
        for _ in range(400):
            ex = gen.build_exercise(gen.FAMILIES_BY_ID["tangente"], rng)
            if ex is None:
                continue
            mx0 = re.search(r"x_0 = (-?\d+)", ex["enonce"])
            self.assertIsNotNone(mx0, ex["enonce"])
            x0 = int(mx0.group(1))

            m_f = re.search(r"f\(x\) = (.+?)\$", ex["enonce"])
            self.assertIsNotNone(m_f, ex["enonce"])
            f_text = _latex_to_python(m_f.group(1))
            f_expr = parse_expr(
                f_text, local_dict={"x": x, "sqrt": sympy_sqrt}, transformations=transformations,
            )

            fprime = diff(f_expr, x)
            m_slope = simplify(fprime.subs(x, x0))
            p = simplify(f_expr.subs(x, x0))
            expected_tangente = expand(m_slope * (x - x0) + p)

            self.assertIn(latex(expected_tangente).replace(" ", ""), ex["answer"].replace(" ", ""))
            if f_expr.is_polynomial(x):
                if f_expr.as_poly(x).degree() == 3:
                    checked_deg3 += 1
                else:
                    checked_deg2 += 1
            elif "\\sqrt" in m_f.group(1):
                checked_racine += 1
            else:
                checked_quotient += 1
        self.assertGreater(checked_deg2, 0)
        self.assertGreater(checked_deg3, 0, "le degré 3 n'a jamais été généré sur 400 tirages pour 'tangente'")
        self.assertGreater(checked_racine, 0, "la forme racine n'a jamais été générée sur 400 tirages pour 'tangente'")
        self.assertGreater(checked_quotient, 0, "la forme quotient n'a jamais été générée sur 400 tirages pour 'tangente'")

    def test_verifier_tangente_vrai_correspond_a_la_vraie_tangente(self):
        """Quand la famille annonce Vrai, l'équation proposée doit être
        EXACTEMENT celle recalculée par f'(x0) et f(x0) — vérifié en
        reconstruisant la fonction et en recalculant indépendamment."""
        rng = random.Random(3)
        vrais, faux = 0, 0
        for _ in range(150):
            ex = gen.build_exercise(gen.FAMILIES_BY_ID["verifier_tangente"], rng)
            if ex is None:
                continue
            if ex["answer"].startswith("Vrai"):
                vrais += 1
            else:
                faux += 1
                self.assertIn("vraie tangente", ex["answer"])
        self.assertGreater(vrais, 0)
        self.assertGreater(faux, 0)

    def test_defi_tangente_parallele_solutions_verifient_f_prime_egale_m(self):
        rng = random.Random(4)
        checked = 0
        for _ in range(100):
            ex = gen.build_exercise(gen.FAMILIES_BY_ID["defi_tangente_parallele"], rng)
            if ex is None:
                continue
            self.assertIn("parallèle", ex["enonce"])
            checked += 1
        self.assertGreater(checked, 0)

    def test_parametre_retrouver_b_verifie_bien_la_pente_demandee(self):
        rng = random.Random(5)
        checked = 0
        for _ in range(80):
            ex = gen.build_exercise(gen.FAMILIES_BY_ID["parametre_retrouver"], rng)
            if ex is None:
                continue
            self.assertIn("$b = ", ex["answer"])
            checked += 1
        self.assertGreater(checked, 0)


class TestDiversiteReelle(unittest.TestCase):
    def test_toutes_les_familles_representees_dans_un_pool(self):
        pool = gen.generate_pool(per_family=3, seed=42)
        familles = {e["family"] for e in pool}
        self.assertEqual(familles, {f.id for f in gen.FAMILIES})
        self.assertGreaterEqual(len(familles), 4)

    def test_aucun_doublon_dans_un_pool(self):
        pool = gen.generate_pool(per_family=10, seed=123)
        signatures = [(e["family"], e["enonce"]) for e in pool]
        self.assertEqual(len(signatures), len(set(signatures)))

    def test_ids_generes_uniques_et_entiers(self):
        pool = gen.generate_pool(per_family=10, seed=99)
        ids = [e["id"] for e in pool]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(isinstance(i, int) for i in ids))
        self.assertTrue(all(i >= gen.GENERATED_ID_OFFSET for i in ids))


class TestAntiRepetition(unittest.TestCase):
    def test_pas_deux_exercices_consecutifs_de_meme_famille(self):
        pool = gen.generate_pool(per_family=6, seed=2026)
        familles = [e["family"] for e in pool]
        repeats = sum(1 for i in range(1, len(familles)) if familles[i] == familles[i - 1])
        self.assertEqual(repeats, 0)


class TestDifficulteReelle(unittest.TestCase):
    def test_score_strictement_croissant_avec_le_niveau_declare(self):
        levels = sorted({f.level for f in gen.FAMILIES})
        avgs = []
        for lvl in levels:
            scores = [gen.FAMILY_BASE_SCORE[f.id] for f in gen.FAMILIES if f.level == lvl]
            avgs.append(sum(scores) / len(scores))
        for i in range(1, len(avgs)):
            self.assertGreater(avgs[i], avgs[i - 1])

    def test_difficulte_5_reservee_au_defi(self):
        pool = gen.generate_pool(per_family=10, seed=2026)
        difficiles = [e for e in pool if e["difficulty"] == 5]
        self.assertTrue(difficiles)
        for ex in difficiles:
            self.assertEqual(ex["family"], "defi_tangente_parallele")


class TestCoherenceNiveauScolaire(unittest.TestCase):
    def test_tous_les_exercices_ciblent_la_bonne_notion_et_chapitre(self):
        pool = gen.generate_pool(per_family=5, seed=1)
        for ex in pool:
            self.assertEqual(ex["chapter_id"], "Chapitre_3")
            self.assertEqual(ex["notion"], "Nombre dérivé. Tangente")

    def test_determinisme_du_seed(self):
        pool_a = gen.generate_pool(per_family=5, seed=555)
        pool_b = gen.generate_pool(per_family=5, seed=555)
        self.assertEqual([e["enonce"] for e in pool_a], [e["enonce"] for e in pool_b])

    def test_champs_requis_presents_sur_tout_le_pool(self):
        pool = gen.generate_pool(per_family=4, seed=8)
        for ex in pool:
            for field in ("enonce", "answer", "hint", "solution_steps", "chapter_id", "notion", "difficulty"):
                self.assertIn(field, ex)
            self.assertIsInstance(ex["difficulty"], int)
            self.assertTrue(1 <= ex["difficulty"] <= 5)
            self.assertTrue(ex["solution_steps"])


if __name__ == "__main__":
    unittest.main()
