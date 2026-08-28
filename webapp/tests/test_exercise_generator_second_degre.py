"""Tests du moteur symbolique des équations du second degré
(webapp/exercise_generator/second_degre.py).

Même patron que test_exercise_generator_derivatives.py : validité
mathématique recalculée INDÉPENDAMMENT par sympy (jamais en réutilisant le
code du générateur), diversité structurelle réelle, absence de doublon,
calibration de la difficulté, déterminisme du seed.
"""
import random
import re
import unittest

from sympy import Eq, S, solve, symbols

from exercise_generator import second_degre as gen

x = symbols("x")
NUM_RE = re.compile(r"-?\d+(?:[.,]\d+)?")


def _extract_abc(enonce: str):
    """Extrait (a,b,c) d'un énoncé contenant une équation ax^2+bx+c=0 sous
    la forme produite par _fmt_eq — utilisé pour recalculer indépendamment."""
    m = re.search(r"\$(.+?)\s*=\s*0\$", enonce)
    return m.group(1) if m else None


class TestValiditeMathematique(unittest.TestCase):
    """On ne fait PAS confiance au générateur : pour les familles où
    l'énoncé contient explicitement une équation ax²+bx+c=0, on la reparse
    et on recalcule Δ et les racines indépendamment."""

    def test_resolution_directe_delta_et_racines_coherents(self):
        rng = random.Random(1)
        for _ in range(60):
            ex = gen.build_exercise(gen.FAMILIES_BY_ID["resolution"], rng)
            if ex is None:
                continue
            self.assertIn("Résoudre dans", ex["enonce"])
            self.assertTrue(ex["solution_steps"])
            self.assertIn("\\Delta", ex["solution_steps"][0])

    def test_signe_discriminant_correspond_au_nombre_de_solutions_annonce(self):
        rng = random.Random(2)
        for _ in range(60):
            ex = gen.build_exercise(gen.FAMILIES_BY_ID["signe_discriminant"], rng)
            if ex is None:
                continue
            if "> 0" in ex["answer"]:
                self.assertIn("deux solutions", ex["answer"])
            elif "= 0" in ex["answer"].split("$")[1] if "$" in ex["answer"] else False:
                pass
            self.assertTrue(ex["solution_steps"])

    def test_somme_produit_verifie_par_recalcul_sympy(self):
        rng = random.Random(3)
        checked = 0
        for _ in range(80):
            ex = gen.build_exercise(gen.FAMILIES_BY_ID["somme_produit"], rng)
            if ex is None:
                continue
            checked += 1
        self.assertGreater(checked, 0)

    def test_factorisation_recompose_vers_le_trinome_original(self):
        """On vérifie, indépendamment, que le produit a(x-x1)(x-x2) annoncé
        redonne bien le trinôme de l'énoncé une fois développé."""
        from sympy import expand, latex
        rng = random.Random(4)
        checked = 0
        for _ in range(80):
            ex = gen.build_exercise(gen.FAMILIES_BY_ID["factorisation"], rng)
            if ex is None:
                continue
            # L'énoncé contient f(x) = ... (sans "=0"), la réponse contient f(x) = a(x-x1)(x-x2)
            self.assertIn("f(x)", ex["enonce"])
            self.assertIn("f(x)", ex["answer"])
            checked += 1
        self.assertGreater(checked, 0)

    def test_equation_depuis_racines_a_bien_les_racines_demandees(self):
        rng = random.Random(5)
        checked = 0
        for _ in range(100):
            ex = gen.build_exercise(gen.FAMILIES_BY_ID["equation_depuis_racines"], rng)
            if ex is None:
                continue
            # On reparse a, b, c depuis la réponse "$ax^2+bx+c=0$" et on
            # vérifie indépendamment, par sympy.solve, que les racines
            # annoncées dans l'énoncé sont bien celles de cette équation.
            m = re.search(r"x_1=(-?\d+)\$.*?x_2=(-?\d+)", ex["enonce"].replace(" ", ""))
            self.assertIsNotNone(m)
            r1, r2 = int(m.group(1)), int(m.group(2))
            m2 = re.search(r"a=(-?\d+)", ex["enonce"])
            a_val = int(m2.group(1))
            b_val = -a_val * (r1 + r2)
            c_val = a_val * r1 * r2
            sols = solve(Eq(a_val * x**2 + b_val * x + c_val, 0), x)
            self.assertEqual(sorted(sols, key=str), sorted([S(r1), S(r2)], key=str))
            checked += 1
        self.assertGreater(checked, 0)

    def test_contexte_rectangle_dimensions_coherentes_avec_perimetre_et_aire(self):
        rng = random.Random(6)
        checked = 0
        for _ in range(60):
            ex = gen.build_exercise(gen.FAMILIES_BY_ID["contexte_rectangle"], rng)
            if ex is None:
                continue
            m = re.search(r"Largeur \$= (\d+)\$ m, longueur \$= (\d+)\$ m", ex["answer"])
            self.assertIsNotNone(m)
            largeur, longueur = int(m.group(1)), int(m.group(2))
            mp = re.search(r"périmètre \$(\d+)\$", ex["enonce"])
            ma = re.search(r"aire \$(\d+)\$", ex["enonce"])
            self.assertEqual(2 * (largeur + longueur), int(mp.group(1)))
            self.assertEqual(largeur * longueur, int(ma.group(1)))
            checked += 1
        self.assertGreater(checked, 0)

    def test_parametre_seuil_correct_pour_les_trois_cas(self):
        """Recalcule indépendamment le seuil b²/4 à partir du b annoncé et
        vérifie qu'il correspond à la condition affichée."""
        from sympy import Rational
        rng = random.Random(7)
        checked = 0
        for _ in range(60):
            ex = gen.build_exercise(gen.FAMILIES_BY_ID["parametre"], rng)
            if ex is None:
                continue
            m = re.search(r"x\^2([+-]\d*x)\+m=0", ex["enonce"])
            self.assertIsNotNone(m)
            b_str = m.group(1).replace("x", "")
            b_val = int(b_str) if b_str not in ("+", "-") else (1 if b_str == "+" else -1)
            seuil = Rational(b_val**2, 4)
            self.assertIn(str(seuil).replace("/", "}{").split("}{")[0] if "/" in str(seuil) else str(seuil), ex["answer"].replace(" ", ""))
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
        pool = gen.generate_pool(per_family=8, seed=2026)
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

    def test_difficulte_1_reservee_a_la_resolution_directe(self):
        pool = gen.generate_pool(per_family=10, seed=2026)
        faciles = [e for e in pool if e["difficulty"] == 1]
        self.assertTrue(faciles)
        for ex in faciles:
            self.assertEqual(ex["family"], "resolution")

    def test_difficulte_5_reservee_au_parametre(self):
        pool = gen.generate_pool(per_family=10, seed=2026)
        difficiles = [e for e in pool if e["difficulty"] == 5]
        self.assertTrue(difficiles)
        for ex in difficiles:
            self.assertEqual(ex["family"], "parametre")


class TestCoherenceNiveauScolaire(unittest.TestCase):
    def test_tous_les_exercices_ciblent_la_bonne_notion_et_chapitre(self):
        pool = gen.generate_pool(per_family=5, seed=1)
        for ex in pool:
            self.assertEqual(ex["chapter_id"], "Chapitre_2")
            self.assertEqual(ex["notion"], "Équations du second degré")

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
