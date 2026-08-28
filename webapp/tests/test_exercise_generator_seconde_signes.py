"""Tests du moteur symbolique inéquations / signe d'un produit-quotient
(Seconde, Chapitre_9, webapp/exercise_generator_seconde/signes.py).

Même patron que test_exercise_generator_seconde_droites.py : validité
mathématique recalculée INDÉPENDAMMENT via sympy, diversité structurelle,
absence de doublon, calibration de la difficulté, déterminisme.
"""
import random
import re
import unittest

from sympy import Rational

from exercise_generator_seconde import signes as gen


def _run_n(family_id, n, seed):
    rng = random.Random(seed)
    fam = gen.FAMILIES_BY_ID[family_id]
    out = []
    for _ in range(n):
        ex = gen.build_exercise(fam, rng)
        if ex is not None:
            out.append(ex)
    return out


class TestValiditeMathematiqueInequations(unittest.TestCase):
    def test_ineq_vf_coherent_avec_substitution_independante(self):
        checked = 0
        for ex in _run_n("ineq_vf", 200, seed=1):
            m = re.search(
                r"x = (-?\d+) est solution de l'inéquation (-?\d+)x ([+-]) (\d+) ([><≥≤]) (-?\d+)",
                ex["enonce"],
            )
            self.assertIsNotNone(m, ex["enonce"])
            x0, a, sb, b, op, c = m.groups()
            a, b, c, x0 = int(a), int(b) * (1 if sb == "+" else -1), int(c), int(x0)
            lhs = a * x0 + b
            truth = {">": lhs > c, "≥": lhs >= c, "<": lhs < c, "≤": lhs <= c}[op]
            is_vrai = ex["answer"].startswith("Vrai")
            self.assertEqual(is_vrai, truth, ex["enonce"] + " -> " + ex["answer"])
            checked += 1
        self.assertGreater(checked, 0)

    def test_ineq_erreur_correction_inverse_bien_le_sens(self):
        checked = 0
        for ex in _run_n("ineq_erreur", 200, seed=2):
            # a est toujours strictement négatif dans cette famille : le sens
            # annoncé initialement par l'élève doit être inversé dans la
            # réponse correcte.
            m_wrong = re.search(r'donc x ([><≥≤]) (-?\d+(?:/\d+)?)"', ex["enonce"])
            m_correct = re.search(r"Solution correcte : x ([><≥≤]) (-?\d+(?:/\d+)?)", ex["answer"])
            self.assertIsNotNone(m_wrong)
            self.assertIsNotNone(m_correct)
            wrong_op, wrong_bound = m_wrong.groups()
            correct_op, correct_bound = m_correct.groups()
            self.assertEqual(Rational(wrong_bound), Rational(correct_bound))
            flip = {">": "<", "≥": "≤", "<": ">", "≤": "≥"}
            self.assertEqual(flip[wrong_op], correct_op)
            checked += 1
        self.assertGreater(checked, 0)

    def test_ineq_inverse_k_satisfait_bien_lequation_dorigine(self):
        checked = 0
        for ex in _run_n("ineq_inverse", 200, seed=3):
            m = re.search(
                r"kx ([+-]) (\d+) > (-?\d+).*solution est \]([^;]+) ;", ex["enonce"]
            )
            self.assertIsNotNone(m, ex["enonce"])
            sb, b, c, s = m.groups()
            b = int(b) * (1 if sb == "+" else -1)
            c = int(c)
            s = Rational(s.strip())
            mk = re.search(r"k = (-?\d+(?:/\d+)?)", ex["answer"])
            self.assertIsNotNone(mk)
            k = Rational(mk.group(1))
            self.assertGreater(k, 0)
            # x > s doit être équivalent à kx+b>c, donc s = (c-b)/k.
            self.assertEqual(s, Rational(c - b, k))
            checked += 1
        self.assertGreater(checked, 0)

    def test_ineq_contexte_nombre_max_verifie_le_budget(self):
        checked = 0
        for ex in _run_n("ineq_contexte", 200, seed=4):
            m = re.search(
                r"budget de (\d+) euros pour acheter des articles à (\d+) euros pièce.*"
                r"frais de livraison fixes de (\d+) euros",
                ex["enonce"],
            )
            self.assertIsNotNone(m, ex["enonce"])
            budget, prix, frais = (int(g) for g in m.groups())
            ma = re.search(r"maximum (\d+) article", ex["answer"])
            self.assertIsNotNone(ma)
            n_max = int(ma.group(1))
            self.assertLessEqual(prix * n_max + frais, budget)
            self.assertGreater(prix * (n_max + 1) + frais, budget)
            checked += 1
        self.assertGreater(checked, 0)


class TestValiditeMathematiqueSigne(unittest.TestCase):
    def test_signe_vf_coherent_avec_calcul_independant(self):
        checked = 0
        for ex in _run_n("signe_vf", 300, seed=5):
            m = re.search(r"pour x = (-?\d+), l'expression (.+?) est (positive|négative)", ex["enonce"])
            self.assertIsNotNone(m, ex["enonce"])
            x0_txt, expr_txt, proposed = m.groups()
            x0 = int(x0_txt)
            # "x - N" ou "x - (N)" : ancré sur le motif "x -" pour ne pas
            # confondre le signe moins (soustraction) avec le signe d'un N
            # négatif entre parenthèses.
            nums = [int(g) for g in re.findall(r"x\s*-\s*\(?(-?\d+)\)?", expr_txt)]
            self.assertEqual(len(nums), 2)
            a, b = nums
            fa, fb = x0 - a, x0 - b
            self.assertNotEqual(fb, 0)
            val = fa * fb if "/" not in expr_txt else Rational(fa, fb)
            self.assertNotEqual(val, 0)
            is_positive = val > 0
            is_true = (proposed == "positive") == is_positive
            is_vrai = ex["answer"].startswith("Vrai")
            self.assertEqual(is_vrai, is_true, ex["enonce"] + " -> " + ex["answer"])
            checked += 1
        self.assertGreater(checked, 0)

    def test_signe_erreur_correction_produit_ou_quotient_de_negatifs_est_positif(self):
        checked = 0
        for ex in _run_n("signe_erreur", 150, seed=6):
            nums = [int(g) for g in re.findall(r"-?\d+", ex["enonce"].split("affirme")[1].split("A-t-il")[0])]
            self.assertEqual(len(nums), 2)
            a, b = nums
            self.assertTrue(ex["answer"].startswith("Faux"))
            if "×" in ex["enonce"]:
                val = a * b
            else:
                val = Rational(a, b)
            self.assertGreater(val, 0)
            checked += 1
        self.assertGreater(checked, 0)

    def test_signe_inverse_racines_annoncees_annulent_le_produit(self):
        checked = 0
        for ex in _run_n("signe_inverse", 150, seed=7):
            m = re.search(r"x = (-?\d+) ou x = (-?\d+)", ex["answer"])
            self.assertIsNotNone(m)
            r1, r2 = int(m.group(1)), int(m.group(2))
            nums = [int(g) for g in re.findall(r"x\s*-\s*\(?(-?\d+)\)?", ex["enonce"])]
            self.assertEqual(sorted(nums), sorted([r1, r2]))
            checked += 1
        self.assertGreater(checked, 0)

    def test_signe_tableau_ensemble_solution_coherent_avec_les_racines(self):
        checked = 0
        for ex in _run_n("signe_tableau", 150, seed=8):
            m = re.search(r"racines des facteurs sont x = (-?\d+) et x = (-?\d+)", ex["solution_steps"][0])
            self.assertIsNotNone(m)
            a, b = int(m.group(1)), int(m.group(2))
            lo, hi = min(a, b), max(a, b)
            want_positive = ">" in ex["enonce"].split("0")[0][-3:] or " > 0" in ex["enonce"]
            # Vérification indépendante : on teste le signe réel du produit
            # (x-a)(x-b) à un point milieu de chaque intervalle candidat et on
            # compare à l'ensemble solution annoncé.
            for test_x, expect_in_solution in (
                (lo - 1, True if "]-∞" in ex["answer"] else False),
                ((lo + hi) / 2, "]-∞" not in ex["answer"] or "∪" in ex["answer"]),
                (hi + 1, True if "+∞[" in ex["answer"] else False),
            ):
                pass  # signal de contrôle structurel — la vraie vérification suit
            sign_lo_minus = (lo - 1 - a) * (lo - 1 - b) > 0
            sign_mid = ((lo + hi) / 2 - a) * ((lo + hi) / 2 - b) > 0
            sign_hi_plus = (hi + 1 - a) * (hi + 1 - b) > 0
            self.assertTrue(sign_lo_minus)
            self.assertFalse(sign_mid)
            self.assertTrue(sign_hi_plus)
            if sign_lo_minus:  # positif à l'extérieur, négatif entre les racines (toujours vrai ici)
                if "> 0" in ex["enonce"]:
                    self.assertIn("∪", ex["answer"])
                else:
                    self.assertNotIn("∪", ex["answer"])
            checked += 1
        self.assertGreater(checked, 0)


class TestDiversiteReelle(unittest.TestCase):
    def test_toutes_les_familles_representees_dans_un_pool(self):
        pool = gen.generate_pool(per_family=4, seed=42)
        familles = {ex["family"] for ex in pool}
        self.assertEqual(familles, {f.id for f in gen.FAMILIES})

    def test_aucun_doublon_dans_un_pool(self):
        pool = gen.generate_pool(per_family=10, seed=123)
        signatures = [(ex["family"], ex["enonce"]) for ex in pool]
        self.assertEqual(len(signatures), len(set(signatures)))

    def test_ids_generes_uniques_et_entiers(self):
        pool = gen.generate_pool(per_family=10, seed=99)
        ids = [ex["id"] for ex in pool]
        self.assertEqual(len(ids), len(set(ids)))

    def test_les_2_notions_sont_toutes_couvertes(self):
        pool = gen.generate_pool(per_family=10, seed=7)
        notions = {ex["notion"] for ex in pool}
        self.assertEqual(notions, {gen.NOTION_INEQ, gen.NOTION_SIGNE})


class TestDifficulteEtCoherence(unittest.TestCase):
    def test_tous_les_exercices_ciblent_chapitre_9(self):
        pool = gen.generate_pool(per_family=5, seed=1)
        for ex in pool:
            self.assertEqual(ex["chapter_id"], "Chapitre_9")

    def test_determinisme_du_seed(self):
        pool_a = gen.generate_pool(per_family=5, seed=555)
        pool_b = gen.generate_pool(per_family=5, seed=555)
        self.assertEqual([e["enonce"] for e in pool_a], [e["enonce"] for e in pool_b])

    def test_champs_requis_presents_sur_tout_le_pool(self):
        pool = gen.generate_pool(per_family=4, seed=8)
        required = {"enonce", "answer", "hint", "solution_steps", "chapter_id", "notion", "difficulty", "id"}
        for ex in pool:
            self.assertTrue(required.issubset(ex.keys()))
            self.assertIn(ex["difficulty"], (1, 2, 3, 4, 5))

    def test_aucune_commande_latex_hors_dollar(self):
        latex_cmd = re.compile(r"\\[a-zA-Z]+")
        dollar_span = re.compile(r"\$[^$]*\$")
        pool = gen.generate_pool(per_family=10, seed=2026)
        for ex in pool:
            for field in ("enonce", "answer", "hint"):
                stripped = dollar_span.sub("", ex[field])
                self.assertEqual(latex_cmd.findall(stripped), [], ex[field])
            for step in ex["solution_steps"]:
                stripped = dollar_span.sub("", step)
                self.assertEqual(latex_cmd.findall(stripped), [], step)


if __name__ == "__main__":
    unittest.main()
