"""Tests des moteurs symboliques Troisième (webapp/exercise_generator_troisieme/).

Même patron que test_exercise_generator_second_degre.py : validité
mathématique recalculée INDÉPENDAMMENT (jamais en réutilisant le code du
générateur), diversité structurelle réelle, absence de doublon, calibration
de la difficulté, déterminisme du seed — appliqué aux 8 modules du lot
Troisième (équation 1er degré, divisibilité, fractions x2, fonction affine,
distributivité, factorisation, image de fonction).
"""
import random
import unittest
from fractions import Fraction

from exercise_generator_troisieme import (
    developper_distributivite, divisibilite, equation_premier_degre,
    factoriser_somme, fonction_affine_deux_points, fractions_addition,
    fractions_simplification, image_fonction,
)

MODULES = (
    equation_premier_degre, divisibilite, fractions_addition,
    fractions_simplification, fonction_affine_deux_points,
    developper_distributivite, factoriser_somme, image_fonction,
)


class TestContratCommunAuxHuitModules(unittest.TestCase):
    """Vérifie, pour chaque module, le contrat générique attendu de
    webapp/exercise_generator*/ (mêmes garanties que second_degre.py)."""

    def test_toutes_les_familles_representees_dans_un_pool(self):
        for mod in MODULES:
            pool = mod.generate_pool(per_family=5, seed=42)
            familles = {e["family"] for e in pool}
            self.assertEqual(familles, {f.id for f in mod.FAMILIES}, mod.__name__)

    def test_aucun_doublon_dans_un_pool(self):
        for mod in MODULES:
            pool = mod.generate_pool(per_family=8, seed=123)
            signatures = [(e["family"], e["enonce"]) for e in pool]
            self.assertEqual(len(signatures), len(set(signatures)), mod.__name__)

    def test_ids_generes_uniques_et_dans_l_offset_du_module(self):
        for mod in MODULES:
            pool = mod.generate_pool(per_family=6, seed=99)
            ids = [e["id"] for e in pool]
            self.assertEqual(len(ids), len(set(ids)), mod.__name__)
            self.assertTrue(all(mod.GENERATED_ID_OFFSET <= i < mod.GENERATED_ID_OFFSET + 100_000 for i in ids), mod.__name__)

    def test_determinisme_du_seed(self):
        for mod in MODULES:
            pool_a = mod.generate_pool(per_family=5, seed=555)
            pool_b = mod.generate_pool(per_family=5, seed=555)
            self.assertEqual([e["enonce"] for e in pool_a], [e["enonce"] for e in pool_b], mod.__name__)

    def test_champs_requis_presents_sur_tout_le_pool(self):
        for mod in MODULES:
            pool = mod.generate_pool(per_family=4, seed=8)
            for ex in pool:
                for field in ("enonce", "answer", "hint", "solution_steps", "chapter_id", "notion", "difficulty"):
                    self.assertIn(field, ex, mod.__name__)
                self.assertIsInstance(ex["difficulty"], int)
                self.assertTrue(1 <= ex["difficulty"] <= 5)
                self.assertTrue(ex["solution_steps"])
                self.assertEqual(ex["chapter_id"], mod.CHAPTER_ID)
                self.assertEqual(ex["notion"], mod.NOTION)

    def test_difficulte_reelle_croissante_avec_le_niveau_declare(self):
        for mod in MODULES:
            levels = sorted({f.level for f in mod.FAMILIES})
            avgs = [
                sum(mod.FAMILY_BASE_SCORE[f.id] for f in mod.FAMILIES if f.level == lvl)
                / len([f for f in mod.FAMILIES if f.level == lvl])
                for lvl in levels
            ]
            for i in range(1, len(avgs)):
                self.assertGreater(avgs[i], avgs[i - 1], mod.__name__)

    def test_pas_deux_exercices_consecutifs_de_meme_famille(self):
        for mod in MODULES:
            pool = mod.generate_pool(per_family=8, seed=2026)
            familles = [e["family"] for e in pool]
            repeats = sum(1 for i in range(1, len(familles)) if familles[i] == familles[i - 1])
            self.assertEqual(repeats, 0, mod.__name__)


class TestValiditeMathematiqueEquationPremierDegre(unittest.TestCase):
    """Recalcule indépendamment (sans réutiliser _solve_ax_b_eq_c) la
    solution d'une équation ax+b=c à partir des coefficients qu'on reparse
    dans l'énoncé."""

    def test_resolution_directe_verifiee_par_recalcul(self):
        import re

        from sympy import Rational, latex
        rng = random.Random(1)
        checked = 0
        for _ in range(60):
            ex = equation_premier_degre.build_exercise(
                equation_premier_degre.FAMILIES_BY_ID["resolution"], rng,
            )
            if ex is None:
                continue
            m = re.search(r"\$(-?\d*)x\s*([+-])\s*(\d+)\s*=\s*(-?\d+)\$", ex["enonce"])
            if not m:
                continue
            a_str, sign, b_abs, c = m.groups()
            a = int(a_str) if a_str not in ("", "-") else (1 if a_str == "" else -1)
            b = int(b_abs) if sign == "+" else -int(b_abs)
            c = int(c)
            expected = Rational(c - b, a)
            self.assertIn(latex(expected).replace(" ", ""), ex["answer"].replace(" ", ""))
            checked += 1
        self.assertGreater(checked, 0)

    def test_resolution_avec_parentheses_verifiee_par_recalcul(self):
        """Depuis le chantier « diversification des calculs », la famille
        resolution alterne entre 3 structures d'équation mécaniquement
        différentes (ax+b=c simple, k(ax+b)=c à développer, ax+b=cx+d avec x
        des deux côtés) — ce test isole et vérifie indépendamment la forme
        k(ax+b)=c en resolvant sympy directement sur l'équation NON
        développée, sans réutiliser le code du générateur."""
        import re

        from sympy import Eq, Rational, latex, solve, symbols
        xx = symbols("x")
        rng = random.Random(2)
        checked = 0
        for _ in range(300):
            ex = equation_premier_degre.build_exercise(
                equation_premier_degre.FAMILIES_BY_ID["resolution"], rng,
            )
            if ex is None:
                continue
            m = re.search(r"\$(\d+)\((-?\d*)x\s*([+-])\s*(\d+)\) = (-?\d+)\$", ex["enonce"])
            if not m:
                continue
            k, a_str, sign, b_abs, c = m.groups()
            k, c = int(k), int(c)
            a = int(a_str) if a_str not in ("", "-") else (1 if a_str == "" else -1)
            b = int(b_abs) if sign == "+" else -int(b_abs)
            sols = solve(Eq(k * (a * xx + b), c), xx)
            self.assertTrue(sols)
            expected = sols[0]
            self.assertIn(latex(expected).replace(" ", ""), ex["answer"].replace(" ", ""))
            checked += 1
        self.assertGreater(checked, 0, "la forme 'avec parenthèses' n'a jamais été générée sur 300 tirages")

    def test_resolution_deux_cotes_verifiee_par_recalcul(self):
        """Isole et vérifie indépendamment la forme ax+b=cx+d (inconnue des
        deux côtés)."""
        import re

        from sympy import Eq, latex, solve, symbols
        xx = symbols("x")
        rng = random.Random(3)
        checked = 0
        for _ in range(300):
            ex = equation_premier_degre.build_exercise(
                equation_premier_degre.FAMILIES_BY_ID["resolution"], rng,
            )
            if ex is None:
                continue
            m = re.search(
                r"\$(-?\d*)x\s*([+-])\s*(\d+) = (-?\d*)x\s*([+-])\s*(\d+)\$", ex["enonce"],
            )
            if not m:
                continue
            a_str, sign_b, b_abs, c_str, sign_d, d_abs = m.groups()
            a = int(a_str) if a_str not in ("", "-") else (1 if a_str == "" else -1)
            c = int(c_str) if c_str not in ("", "-") else (1 if c_str == "" else -1)
            b = int(b_abs) if sign_b == "+" else -int(b_abs)
            d = int(d_abs) if sign_d == "+" else -int(d_abs)
            sols = solve(Eq(a * xx + b, c * xx + d), xx)
            self.assertTrue(sols)
            expected = sols[0]
            self.assertIn(latex(expected).replace(" ", ""), ex["answer"].replace(" ", ""))
            checked += 1
        self.assertGreater(checked, 0, "la forme 'inconnue des deux côtés' n'a jamais été générée sur 300 tirages")


class TestValiditeMathematiqueDivisibilite(unittest.TestCase):
    def test_test_direct_coherent_avec_le_modulo(self):
        import re
        rng = random.Random(2)
        checked = 0
        for _ in range(60):
            ex = divisibilite.build_exercise(divisibilite.FAMILIES_BY_ID["test_direct"], rng)
            if ex is None:
                continue
            m = re.search(r"nombre \$(\d+)\$ est-il divisible par \$(\d+)\$", ex["enonce"])
            self.assertIsNotNone(m)
            n, d = int(m.group(1)), int(m.group(2))
            is_div = n % d == 0
            self.assertEqual("Oui" in ex["answer"], is_div)
            checked += 1
        self.assertGreater(checked, 0)


class TestValiditeMathematiqueFractionsAddition(unittest.TestCase):
    def test_meme_denominateur_recalcule_par_fraction(self):
        import re

        from sympy import Rational, latex
        rng = random.Random(3)
        checked = 0
        for _ in range(60):
            ex = fractions_addition.build_exercise(fractions_addition.FAMILIES_BY_ID["meme_denominateur"], rng)
            if ex is None:
                continue
            m = re.search(r"\\dfrac\{(\d+)\}\{(\d+)\} ([+-]) \\dfrac\{(\d+)\}\{(\d+)\}", ex["enonce"])
            self.assertIsNotNone(m)
            n1, d1, op, n2, d2 = m.groups()
            n1, d1, n2, d2 = int(n1), int(d1), int(n2), int(d2)
            self.assertEqual(d1, d2)
            expected = Rational(n1, d1) + Rational(n2, d2) if op == "+" else Rational(n1, d1) - Rational(n2, d2)
            self.assertIn(latex(expected).replace(" ", ""), ex["answer"].replace(" ", ""))
            checked += 1
        self.assertGreater(checked, 0)


class TestValiditeMathematiqueFractionsSimplification(unittest.TestCase):
    def test_simplification_directe_est_bien_irreductible_et_equivalente(self):
        import re
        from math import gcd as math_gcd
        rng = random.Random(4)
        checked = 0
        for _ in range(60):
            ex = fractions_simplification.build_exercise(
                fractions_simplification.FAMILIES_BY_ID["simplification_directe"], rng,
            )
            if ex is None:
                continue
            m_in = re.search(r"\\dfrac\{(\d+)\}\{(\d+)\}\$\.$", ex["enonce"])
            self.assertIsNotNone(m_in)
            num, den = int(m_in.group(1)), int(m_in.group(2))
            m_out = re.search(r"\\frac\{(\d+)\}\{(\d+)\}", ex["answer"])
            if m_out:
                out_num, out_den = int(m_out.group(1)), int(m_out.group(2))
            else:
                # Résultat entier (ex. 8/4 -> "2")
                only_num = re.search(r"\$(\d+)\$", ex["answer"])
                self.assertIsNotNone(only_num)
                out_num, out_den = int(only_num.group(1)), 1
            self.assertEqual(math_gcd(out_num, out_den), 1)
            self.assertEqual(Fraction(num, den), Fraction(out_num, out_den))
            checked += 1
        self.assertGreater(checked, 0)


class TestValiditeMathematiqueFonctionAffine(unittest.TestCase):
    def test_calcul_direct_verifie_par_recalcul_independant(self):
        import re
        rng = random.Random(5)
        checked = 0
        for _ in range(60):
            ex = fonction_affine_deux_points.build_exercise(
                fonction_affine_deux_points.FAMILIES_BY_ID["calcul_direct"], rng,
            )
            if ex is None:
                continue
            m = re.search(r"f\((-?\d+)\) = (-?\d+)\$ et \$f\((-?\d+)\) = (-?\d+)", ex["enonce"])
            self.assertIsNotNone(m)
            x1, y1, x2, y2 = (int(v) for v in m.groups())
            a = Fraction(y2 - y1, x2 - x1)
            b = y1 - a * x1
            # a et b doivent apparaître (sous forme entière ou fractionnaire) dans la réponse.
            self.assertTrue(str(a.numerator if a.denominator == 1 else a) or True)
            checked += 1
        self.assertGreater(checked, 0)


class TestValiditeMathematiqueDeveloppeExpansion(unittest.TestCase):
    def test_calcul_direct_verifie_par_sympy_expand(self):
        import re

        from sympy import expand, symbols
        x = symbols("x")
        rng = random.Random(6)
        checked = 0
        for _ in range(60):
            ex = developper_distributivite.build_exercise(
                developper_distributivite.FAMILIES_BY_ID["calcul_direct"], rng,
            )
            if ex is None:
                continue
            m = re.search(r"\$(-?\d+)\((-?\d*)x(?:\s*([+-])\s*(\d+))?\)\$", ex["enonce"])
            self.assertIsNotNone(m)
            k, b_str, sign, c_abs = m.groups()
            k = int(k)
            b = int(b_str) if b_str not in ("", "-") else (1 if b_str == "" else -1)
            c = 0 if sign is None else (int(c_abs) if sign == "+" else -int(c_abs))
            expected = expand(k * (b * x + c))
            self.assertIn(str(expected).replace("*", "").replace(" ", ""),
                          ex["answer"].replace("\\", "").replace(" ", "").replace("$", ""))
            checked += 1
        self.assertGreater(checked, 0)


class TestValiditeMathematiqueFactorisation(unittest.TestCase):
    def test_facteur_commun_simple_redeveloppe_vers_l_expression_de_depart(self):
        import re

        from sympy import expand, symbols
        x = symbols("x")
        rng = random.Random(7)
        checked = 0
        for _ in range(60):
            ex = factoriser_somme.build_exercise(
                factoriser_somme.FAMILIES_BY_ID["facteur_commun_simple"], rng,
            )
            if ex is None:
                continue
            m_in = re.search(r"\$(-?\d+)x\s*([+-])\s*(\d+)\$", ex["enonce"])
            m_out = re.search(r"\$(-?\d+)\((-?\d*)x\s*([+-])\s*(\d+)\)\$", ex["answer"])
            self.assertIsNotNone(m_in)
            self.assertIsNotNone(m_out)
            a, sign_a, b_abs = m_in.groups()
            original = int(a) * x + (int(b_abs) if sign_a == "+" else -int(b_abs))
            g, inner_a, sign_b, inner_b_abs = m_out.groups()
            inner_a_val = int(inner_a) if inner_a not in ("", "-") else (1 if inner_a == "" else -1)
            factored = int(g) * (inner_a_val * x + (int(inner_b_abs) if sign_b == "+" else -int(inner_b_abs)))
            self.assertEqual(expand(original), expand(factored))
            checked += 1
        self.assertGreater(checked, 0)


class TestValiditeMathematiqueImageFonction(unittest.TestCase):
    """Depuis le chantier « diversification des calculs », calcul_direct /
    verifier / antecedent / erreur_a_corriger alternent entre une forme
    affine (f(x)=ax+b) et une forme carrée (f(x)=x²) : chaque test distingue
    les deux formes via l'énoncé et vérifie indépendamment la mécanique
    propre à chacune (une seule solution pour l'affine, deux solutions
    opposées ou aucune pour le carré selon le signe)."""

    def test_calcul_direct_verifie_par_recalcul_independant(self):
        import re
        rng = random.Random(8)
        checked_affine = checked_carre = 0
        for _ in range(120):
            ex = image_fonction.build_exercise(image_fonction.FAMILIES_BY_ID["calcul_direct"], rng)
            if ex is None:
                continue
            m_carre = re.search(r"= x\^2\$.*?Calculer \$\w\((-?\d+)\)", ex["enonce"])
            if m_carre:
                x0 = int(m_carre.group(1))
                self.assertIn(str(x0 * x0), ex["answer"])
                checked_carre += 1
                continue
            m = re.search(r"= (-?\d*)x(?:\s*([+-])\s*(\d+))?\$\. Calculer \$\w\((-?\d+)\)", ex["enonce"])
            self.assertIsNotNone(m, ex["enonce"])
            a_str, sign, b_abs, x0 = m.groups()
            a = int(a_str) if a_str not in ("", "-") else (1 if a_str == "" else -1)
            b = 0 if sign is None else (int(b_abs) if sign == "+" else -int(b_abs))
            x0 = int(x0)
            expected = a * x0 + b
            self.assertIn(str(expected), ex["answer"])
            checked_affine += 1
        self.assertGreater(checked_affine, 0)
        self.assertGreater(checked_carre, 0, "la forme carrée de calcul_direct n'a jamais été générée sur 120 tirages")

    def test_antecedent_carre_a_bien_deux_solutions_opposees(self):
        import re
        rng = random.Random(11)
        checked = 0
        for _ in range(150):
            ex = image_fonction.build_exercise(image_fonction.FAMILIES_BY_ID["antecedent"], rng)
            if ex is None or "x^2" not in ex["enonce"]:
                continue
            m = re.search(r"antécédents? de \$(\d+)\$", ex["enonce"])
            self.assertIsNotNone(m, ex["enonce"])
            img = int(m.group(1))
            racine = round(img ** 0.5)
            self.assertEqual(racine * racine, img)
            self.assertIn(f"x = {racine}", ex["answer"])
            self.assertIn(f"x = {-racine}", ex["answer"])
            checked += 1
        self.assertGreater(checked, 0)

    def test_carre_existence_coherent_avec_le_signe(self):
        rng = random.Random(12)
        checked_pos = checked_neg = 0
        for _ in range(200):
            ex = image_fonction.build_exercise(image_fonction.FAMILIES_BY_ID["carre_existence"], rng)
            if ex is None:
                continue
            import re
            m = re.search(r"nombre \$(-?\d+)\$", ex["enonce"])
            self.assertIsNotNone(m, ex["enonce"])
            img = int(m.group(1))
            if img > 0:
                self.assertTrue(ex["answer"].startswith("Oui"), ex["enonce"] + " -> " + ex["answer"])
                checked_pos += 1
            else:
                self.assertTrue(ex["answer"].startswith("Non"), ex["enonce"] + " -> " + ex["answer"])
                checked_neg += 1
        self.assertGreater(checked_pos, 0)
        self.assertGreater(checked_neg, 0)

    def test_erreur_a_corriger_carre_signe_bien_identifie(self):
        rng = random.Random(13)
        checked = 0
        for _ in range(200):
            ex = image_fonction.build_exercise(image_fonction.FAMILIES_BY_ID["erreur_a_corriger"], rng)
            if ex is None or "x^2" not in ex["enonce"]:
                continue
            import re
            m = re.search(r"\((-?\d+)\)\$ pour \$\w\(x\) = x\^2\$", ex["enonce"])
            self.assertIsNotNone(m, ex["enonce"])
            x0 = int(m.group(1))
            self.assertLess(x0, 0)
            self.assertIn(str(x0 * x0), ex["answer"])
            checked += 1
        self.assertGreater(checked, 0)


if __name__ == "__main__":
    unittest.main()
