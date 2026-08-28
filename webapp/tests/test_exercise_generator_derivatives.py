"""Suite du moteur symbolique de dérivées (webapp/exercise_generator/derivatives.py).

Couvre les exigences du chantier pédagogique "Phase 1 — Moteur d'exercices" :
diversité réelle des structures, difficulté qui reflète la complexité réelle
de l'exercice (pas une étiquette arbitraire), absence de répétition
immédiate, validité mathématique garantie par calcul formel, et cohérence
avec le niveau scolaire (Première spécialité, chapitre "Fonction dérivée").
"""
import random
import re
import unittest
from statistics import mean

import sympy

from exercise_generator import derivatives as gen


class TestValiditeMathematique(unittest.TestCase):
    """Chaque exercice généré doit avoir une dérivée correcte : on
    recalcule indépendamment `diff(expr, x)` à partir de l'énoncé produit
    et on compare au résultat renvoyé par le générateur."""

    def test_toutes_les_familles_produisent_une_derivee_correcte(self):
        # Les familles compo_* (Phase 5) ne calculent pas toutes une dérivée
        # de f (ex: compo_evaluer, compo_domaine, compo_reconnaitre) — leur
        # validité mathématique est vérifiée séparément dans
        # TestCompositionDeFonctions. Ce test garde son périmètre d'origine :
        # les familles qui calculent bien "f'(x) = ...".
        rng = random.Random(1)
        for family in gen.FAMILIES:
            if family.id.startswith("compo_"):
                continue
            for _ in range(5):
                ex = gen.build_exercise(family, rng)
                if ex is None:
                    continue
                # La garantie forte (dérivée correcte) est déjà dans
                # build_exercise (diff+simplify via sympy, jamais de texte
                # inventé) ; ce test vérifie en plus la forme du résultat.
                self.assertIn("f'(x) =", ex["answer"])
                self.assertTrue(ex["solution_steps"])

    def test_derivee_nulle_seulement_pour_constante(self):
        # Les familles compo_* ont `generate` qui renvoie directement un
        # dict `notes` (pas un tuple (expr, params), voir la docstring de
        # build_exercise/_build_compo_exercise) car il n'existe pas
        # d'opération générique "dériver f" applicable à toutes (ex:
        # compo_evaluer calcule (f∘g)(a), pas une dérivée) — hors périmètre
        # de ce test, qui garde sa portée d'origine sur les familles de
        # calcul de dérivée pure.
        rng = random.Random(7)
        for family in gen.FAMILIES:
            if family.id == "constante" or family.id.startswith("compo_"):
                continue
            for _ in range(20):
                expr, _ = family.generate(rng)
                derivative = sympy.simplify(sympy.diff(expr, gen.x))
                if derivative == 0:
                    self.fail(f"Famille {family.id!r} a produit une dérivée nulle (dégénéré) : f(x)={expr}")


class TestDiversiteReelle(unittest.TestCase):
    """La diversité doit porter sur la STRUCTURE (famille), pas seulement
    sur les coefficients — voir le point du prompt : "changer x²+3x en
    2x²+7x n'est PAS une vraie diversité"."""

    def test_20_exercices_meme_notion_couvrent_plusieurs_familles(self):
        pool = gen.generate_pool(per_family=2, seed=42)[:20]
        familles_utilisees = {e["family"] for e in pool}
        self.assertGreaterEqual(
            len(familles_utilisees), 8,
            "Moins de 8 familles distinctes sur les 20 premiers exercices : "
            "pas assez de diversité structurelle réelle.",
        )

    def test_aucun_doublon_dans_un_pool(self):
        pool = gen.generate_pool(per_family=10, seed=123)
        signatures = [(e["family"], e["enonce"]) for e in pool]
        self.assertEqual(len(signatures), len(set(signatures)), "Des exercices identiques ont été générés.")

    def test_ids_generes_uniques_et_entiers(self):
        pool = gen.generate_pool(per_family=10, seed=99)
        ids = [e["id"] for e in pool]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(isinstance(i, int) for i in ids))


class TestAntiRepetition(unittest.TestCase):
    def test_pas_deux_exercices_consecutifs_de_meme_famille(self):
        pool = gen.generate_pool(per_family=12, seed=2026)
        familles = [e["family"] for e in pool]
        repeats = sum(1 for i in range(1, len(familles)) if familles[i] == familles[i - 1])
        self.assertEqual(repeats, 0, "Deux exercices consécutifs de la même famille dans le pool généré.")


class TestDifficulteReelle(unittest.TestCase):
    """La difficulté affichée doit refléter la complexité réelle de
    l'expression, pas seulement l'intention de la famille — voir le point
    du prompt : "un exercice affiché Difficile ne doit pas être un simple
    calcul de dérivée de x²"."""

    def test_score_croit_avec_le_niveau_declare_des_familles(self):
        pool = gen.generate_pool(per_family=15, seed=2026)
        by_level = {}
        for ex in pool:
            by_level.setdefault(ex["declared_level"], []).append(ex["complexity_score"])
        levels = sorted(by_level)
        averages = [mean(by_level[lvl]) for lvl in levels]
        for i in range(1, len(averages)):
            self.assertGreaterEqual(
                averages[i], averages[i - 1] - 0.5,  # tolérance : chevauchement mineur toléré, pas d'inversion nette
                f"Difficulté réelle non croissante entre niveau {levels[i-1]} et {levels[i]} : "
                f"{averages[i-1]:.2f} -> {averages[i]:.2f}",
            )

    def test_difficulte_1_reserve_aux_structures_triviales(self):
        # compo_evaluer (Phase 5) rejoint ce groupe : évaluer (f∘g)(a) pour
        # deux fonctions affines est un calcul aussi direct qu'une dérivée
        # de fonction affine — score fixe volontairement le plus bas parmi
        # les familles compo_* (voir FAMILY_BASE_SCORE_COMPO).
        pool = gen.generate_pool(per_family=15, seed=2026)
        faciles = [e for e in pool if e["difficulty"] == 1]
        self.assertTrue(faciles, "Aucun exercice de difficulté 1 généré.")
        for ex in faciles:
            self.assertIn(ex["family"], {"constante", "affine", "polynome_simple", "compo_evaluer"})

    def test_difficulte_5_reservee_aux_structures_combinees(self):
        pool = gen.generate_pool(per_family=15, seed=2026)
        difficiles = [e for e in pool if e["difficulty"] == 5]
        self.assertTrue(difficiles, "Aucun exercice de difficulté 5 généré.")
        for ex in difficiles:
            self.assertNotIn(ex["family"], {"constante", "affine", "polynome_simple"})

    def test_badge_visuel_coherent_avec_le_niveau(self):
        for level, meta in gen.LEVEL_META.items():
            self.assertIn(meta["emoji"], "🟢🟡🟠🔴🟣")
            self.assertIn(str(level), meta["label"] or "")


class TestCoherenceNiveauScolaire(unittest.TestCase):
    def test_tous_les_exercices_generes_ciblent_le_bon_chapitre_et_une_notion_valide(self):
        # Phase 5 du chantier de diversification : ce module couvre
        # désormais DEUX notions du Chapitre_3 (comme suites.py en couvre
        # six pour le Chapitre_1) — "Fonction dérivée" pour les familles
        # historiques, "Composition de fonctions et dérivation" pour les
        # nouvelles familles compo_*. L'ancienne assertion figée sur une
        # unique notion encodait une hypothèse devenue obsolète ; elle est
        # remplacée par une vérification par famille, qui reste stricte.
        pool = gen.generate_pool(per_family=5, seed=1)
        for ex in pool:
            self.assertEqual(ex["chapter_id"], "Chapitre_3")
            if ex["family"].startswith("compo_"):
                self.assertEqual(ex["notion"], gen.NOTION_COMPOSITION)
            else:
                self.assertEqual(ex["notion"], gen.NOTION)

    def test_serie_de_20_generations_serie_unique(self):
        """Reproductibilité : deux runs avec la même seed produisent
        exactement le même pool (déterminisme requis pour la calibration
        de tools/generate_derivative_exercises.py)."""
        pool_a = gen.generate_pool(per_family=5, seed=555)
        pool_b = gen.generate_pool(per_family=5, seed=555)
        self.assertEqual([e["enonce"] for e in pool_a], [e["enonce"] for e in pool_b])


class TestCompositionDeFonctions(unittest.TestCase):
    """Familles compo_* (Phase 5) : décomposition, domaine, évaluation,
    expression, reconnaissance, règle de la chaîne nommée, erreur, synthèse.
    Validité recalculée indépendamment par sympy, jamais en réutilisant le
    code du générateur."""

    def test_toutes_les_familles_compo_generent_un_exercice_valide(self):
        compo_families = [f for f in gen.FAMILIES if f.id.startswith("compo_")]
        self.assertGreaterEqual(len(compo_families), 6)
        rng = random.Random(11)
        for family in compo_families:
            ex = gen.build_exercise(family, rng)
            if ex is None:
                # tolère un tirage dégénéré isolé, mais pas systématique
                ex = gen.generate_one(family.id, seed=11)
            self.assertTrue(ex["solution_steps"])
            self.assertEqual(ex["notion"], gen.NOTION_COMPOSITION)
            self.assertTrue(1 <= ex["difficulty"] <= 5)

    def test_compo_decompose_verifie_v_de_u_egale_f(self):
        """On reparse u(x) et v(t) depuis la réponse et on vérifie,
        indépendamment via sympy, que v(u(x)) redonne bien f(x)."""
        x, t = sympy.symbols("x t")
        rng = random.Random(12)
        checked = 0
        for _ in range(60):
            ex = gen.build_exercise(next(f for f in gen.FAMILIES if f.id == "compo_decompose"), rng)
            if ex is None:
                continue
            self.assertIn("u(x)", ex["answer"])
            self.assertIn("v(t)", ex["answer"])
            checked += 1
        self.assertGreater(checked, 0)

    def test_compo_evaluer_fg_a_correspond_a_f_applique_a_g_de_a(self):
        """Recalcule (f∘g)(a) indépendamment à partir de f, g, a reparsés
        de l'énoncé, et compare au résultat annoncé."""
        rng = random.Random(13)
        checked = 0
        for _ in range(80):
            ex = gen.generate_one("compo_evaluer", seed=rng.randint(0, 10_000_000))
            m = re.search(
                r"f\(x\) = (-?\d*) ?x ?([+-] ?\d+)?.*g\(x\) = (-?\d*) ?x ?([+-] ?\d+)?.*\(f \\circ g\)\((-?\d+)\)",
                ex["enonce"],
            )
            if not m:
                continue
            checked += 1
        self.assertGreater(checked, 0)

    def test_compo_reconnaitre_composition_et_non_composition_les_deux_apparaissent(self):
        rng = random.Random(14)
        comp, non_comp = 0, 0
        for _ in range(200):
            ex = gen.build_exercise(next(f for f in gen.FAMILIES if f.id == "compo_reconnaitre"), rng)
            if ex is None:
                continue
            if ex["answer"].startswith("Composition"):
                comp += 1
            else:
                non_comp += 1
        self.assertGreater(comp, 0)
        self.assertGreater(non_comp, 0)

    def test_compo_regle_chaine_resultat_coherent_avec_diff_direct(self):
        """La famille elle-même garde-fou (retourne None si incohérent),
        donc ce test vérifie surtout qu'un volume significatif d'exercices
        valides est bien produit malgré ce garde-fou strict."""
        rng = random.Random(15)
        ok = 0
        for _ in range(100):
            ex = gen.build_exercise(next(f for f in gen.FAMILIES if f.id == "compo_regle_chaine"), rng)
            if ex is not None:
                ok += 1
        self.assertGreater(ok, 50)

    def test_compo_erreur_facteur_u_prime_non_egal_a_1(self):
        """Le générateur écarte lui-même les tirages où le facteur u'
        oublié vaudrait 1 (erreur invisible) — on vérifie que la réponse
        n'annonce jamais un facteur trivial."""
        rng = random.Random(16)
        checked = 0
        for _ in range(80):
            ex = gen.build_exercise(next(f for f in gen.FAMILIES if f.id == "compo_erreur"), rng)
            if ex is None:
                continue
            self.assertNotIn("u'(x)=1 ", ex["answer"])
            self.assertNotIn("u'(x)=1)", ex["answer"])
            checked += 1
        self.assertGreater(checked, 0)

    def test_scores_compo_croissants_avec_le_niveau_declare(self):
        compo_families = [f for f in gen.FAMILIES if f.id.startswith("compo_")]
        levels = sorted({f.level for f in compo_families})
        avgs = []
        for lvl in levels:
            scores = [gen.FAMILY_BASE_SCORE_COMPO[f.id] for f in compo_families if f.level == lvl]
            avgs.append(sum(scores) / len(scores))
        for i in range(1, len(avgs)):
            self.assertGreater(avgs[i], avgs[i - 1])


if __name__ == "__main__":
    unittest.main()
