"""Générateurs créés pour l'adaptation de la Première spécifique au manuel
« Première ES/L » (2026-10-26) : pourcentages_1es, fonctions_reference_1es,
statistiques_1es, evenements_1es, loi_binomiale_1es.

- Contrat : pool déterministe, identifiants dans le bloc du module, niveaux
  cohérents, notions présentes dans le cours du chapitre.
- Vérification INDÉPENDANTE : pour les familles calculatoires, l'énoncé et la
  réponse sont relus (texte) et la réponse est recalculée autrement que dans
  le générateur (statistics, sympy.binomial, sommes SymPy…).
- Pool servi : chaque exercice de ces modules présent dans
  exercises_generated_premiere_specifique.json est identique à un tirage du module.
"""
import json
import math
import re
import statistics
import unittest
from fractions import Fraction as F
from pathlib import Path

import sympy as sp

from exercise_generator_premiere_specifique import (
    evenements_1es, fonctions_reference_1es, loi_binomiale_1es, pourcentages_1es, statistiques_1es,
)

ROOT = Path(__file__).resolve().parents[2]
COURS = ROOT / "webapp" / "course_content" / "cours_premiere_specifique"
GENERATED = ROOT / "exercises_generated_premiere_specifique.json"
MODULES = ((pourcentages_1es, 20261101), (fonctions_reference_1es, 20261102), (statistiques_1es, 20261103),
           (evenements_1es, 20261104), (loi_binomiale_1es, 20261105))


def nombres(texte):
    """Nombres écrits dans les formules : « 1\\,240 », « 0{,}35 », « -3 »."""
    t = texte.replace("\\,", "").replace("{,}", ".")
    return [F(x) for x in re.findall(r"-?\d+(?:\.\d+)?", t)]


def maths(texte):
    return re.findall(r"\$([^$]*)\$", texte)


def verifier(ex):
    fam, en, ans = ex["family"], ex["enonce"], ex["answer"]
    if fam == "proportion":
        n, a = nombres(maths(en)[0])[0], nombres(maths(en)[1])[0]
        return F(a, 1) / n * 100 == nombres(maths(ans)[1])[0]
    if fam == "pourcentage_de":
        p, q = nombres(maths(en)[0])[0], nombres(maths(en)[1])[0]
        return q * p / 100 == nombres(maths(ans)[2])[0]
    if fam == "effectif_total":
        a, p = nombres(maths(en)[0])[0], nombres(maths(en)[1])[0]
        return a * 100 / p == nombres(maths(ans)[0])[0]
    if fam == "indice_calcul":
        y1, y2 = nombres(maths(en)[0])[0], nombres(maths(en)[1])[0]
        return 100 * y2 / y1 == nombres(maths(ans)[0])[0]
    if fam == "indice_valeur":
        y1, i = nombres(maths(en)[0])[0], nombres(maths(en)[2])[0]
        return y1 * i / 100 == nombres(maths(ans)[0])[0]
    if fam == "equation_racine":
        k = nombres(maths(en)[1])[0]
        return ("pas de solution" in ans) if k < 0 else nombres(maths(ans)[0])[0] == k * k
    if fam == "equation_cube":
        k3 = nombres(maths(en)[1])[-1]  # « x^3 = k » : le dernier nombre, pas l'exposant
        x = nombres(maths(ans)[0])[0]
        return x ** 3 == k3
    if fam == "comparer_racines":
        a, b = nombres(maths(en)[0])[0], nombres(maths(en)[1])[0]
        return ("<" in maths(ans)[0]) == (math.sqrt(a) < math.sqrt(b))
    if fam == "somme_sigma":
        n = int(re.search(r"\^\{(\d+)\}", en).group(1))
        a, signe, b = re.search(r"\((\d*)i(?: ([+-]) (\d+))?\)\$", en).groups()
        a, b = int(a or 1), (int(b) if b else 0) * (-1 if signe == "-" else 1)
        return a * n * (n + 1) // 2 + b * n == nombres(maths(ans)[0].rsplit("=", 1)[1])[0]
    if fam == "mediane_serie":
        data = [nombres(m)[0] for m in maths(en)]
        return F(statistics.median(data)) == nombres(maths(ans)[0])[0]
    if fam == "quartiles_serie":
        data = sorted(nombres(m)[0] for m in maths(en))
        n = len(data)
        q1 = next(x for i, x in enumerate(data, 1) if 4 * i >= n)
        q3 = next(x for i, x in enumerate(data, 1) if 4 * i >= 3 * n)
        return nombres(maths(ans)[0])[-1] == q1 and nombres(maths(ans)[1])[-1] == q3
    if fam == "reunion_formule":
        pa, pb, pab = (nombres(m)[-1] for m in maths(en)[:3])
        return pa + pb - pab == nombres(maths(ans)[0])[-1]
    if fam == "proba_binomiale":
        n, p = nombres(maths(en)[1])  # maths(en)[0] est « X »
        k = nombres(maths(en)[2])[0]
        attendu = sp.binomial(int(n), int(k)) * sp.Rational(str(p)) ** int(k) * (1 - sp.Rational(str(p))) ** int(n - k)
        return sp.Rational(str(nombres(maths(ans)[0])[-1])) == attendu
    if fam == "bornes":
        n, p = (int(nombres(maths(en)[0])[0]), sp.Rational(str(nombres(maths(en)[0])[1])))
        cumul = [sum(sp.binomial(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k + 1)) for k in range(n + 1)]
        a = next(k for k in range(n + 1) if cumul[k] > sp.Rational(1, 40))
        b = next(k for k in range(n + 1) if cumul[k] >= sp.Rational(39, 40))
        return nombres(maths(ans)[0])[0] == a and nombres(maths(ans)[1])[0] == b
    return None  # famille sans vérificateur indépendant (contrat seul)


class TestContrat(unittest.TestCase):
    def test_pool_deterministe_identifiants_niveaux_notions(self):
        for module, seed in MODULES:
            titres = {n["title"] for n in json.loads((COURS / f"chapitre_{module.CHAPTER_ID.split('_')[1]}.json").read_text(encoding="utf-8"))["notions"]}
            with self.subTest(module=module.__name__):
                pool = module.generate_pool(per_family=8, seed=seed)
                self.assertEqual(pool, module.generate_pool(per_family=8, seed=seed))
                ids = [e["id"] for e in pool]
                self.assertEqual(len(ids), len(set(ids)))
                self.assertTrue(all(module.GENERATED_ID_OFFSET <= i < module.GENERATED_ID_OFFSET + 1000 * len(module.FAMILIES) for i in ids))
                self.assertEqual({e["difficulty"] for e in pool} - {1, 2, 3, 4}, set())
                for fam in module.FAMILIES:
                    self.assertIn(fam.notion, titres)
                for e in pool:
                    self.assertEqual(e["chapter_id"], module.CHAPTER_ID)
                    self.assertTrue(e["answer"] and e["hint"] and e["solution_steps"])
                    self.assertNotIn(e["hint"], e["answer"])
                    self.assertEqual(e["enonce"].count("$") % 2, 0)

    def test_quatre_niveaux_par_chapitre(self):
        for module, _seed in MODULES:
            with self.subTest(module=module.__name__):
                self.assertEqual({f.level for f in module.FAMILIES}, {1, 2, 3, 4})


class TestVerificationIndependante(unittest.TestCase):
    def test_reponses_recalculees(self):
        verifiees = set()
        for module, _seed in MODULES:
            for fam in module.FAMILIES:
                for seed in range(30):
                    ex = module.generate_one(fam.id, seed=seed)
                    ok = verifier(ex)
                    if ok is None:
                        break
                    verifiees.add(fam.id)
                    with self.subTest(famille=fam.id, seed=seed):
                        self.assertTrue(ok, ex["enonce"] + " || " + ex["answer"])
        self.assertGreaterEqual(len(verifiees), 14)


class TestPoolServi(unittest.TestCase):
    def test_pool_servi_identique_aux_tirages(self):
        servi = [e for e in json.loads(GENERATED.read_text(encoding="utf-8")) if e["id"] >= 1_200_000]
        self.assertGreater(len(servi), 800)
        frais = {}
        for module, seed in MODULES:
            frais.update({e["id"]: e for e in module.generate_pool(per_family=24, seed=seed)})
        for e in servi:
            with self.subTest(id=e["id"]):
                self.assertEqual(e, frais[e["id"]])


if __name__ == "__main__":
    unittest.main()
