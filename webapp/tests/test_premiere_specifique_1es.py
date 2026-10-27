# -*- coding: utf-8 -*-
"""Classe « Première spécifique » (`premiere_specifique`), adaptée au manuel
« Première ES/L » (PREMIERE_SPECIFIQUE_SUIVI.md) : 9 chapitres.

- Les JSON servis (cours, banque curée) sont exactement ceux produits par les
  sources tools/premiere_specifique/ (aucune retouche manuelle qui serait écrasée).
- Les contrôles de la banque (valeurs recalculées, quiz, identifiants
  historiques conservés, écritures fautives) passent.
- Les générateurs du programme 2026 sont déterministes et chaque exercice
  échantillonné est revérifié par un contrôle INDÉPENDANT du générateur :
  l'énoncé et la réponse sont relus (texte LaTeX) puis recalculés par SymPy.
"""
import json
import re
import sys
import unittest
from pathlib import Path

import sympy as sp
from sympy.parsing.sympy_parser import (
    convert_xor, implicit_multiplication_application, parse_expr, standard_transformations,
)

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

from exercise_generator_premiere_specifique import derivation_2026, programme_1es, second_degre_formes  # noqa: E402
from exercise_generator_premiere_specifique._tex import parse as _parse_tex  # noqa: E402
from premiere_specifique.banque_commun import build_chapter, check_chapter  # noqa: E402
from premiere_specifique.chapitres import modules  # noqa: E402

import db  # noqa: E402
from tests.premiere_specifique_preview import PreviewHTTPCase  # noqa: E402

COURS_DIR = ROOT / "webapp" / "course_content" / "cours_premiere_specifique"
BANK = ROOT / "exercises_bank_premiere_specifique.json"
GENERATED = ROOT / "exercises_generated_premiere_specifique.json"

X, T, Q, M = sp.symbols("x t q m")
_TR = standard_transformations + (implicit_multiplication_application, convert_xor)


def tex(s):
    """LaTeX simple (polynômes, fractions, racines) -> expression SymPy."""
    return _parse_tex(s, symbols=("x", "t", "q", "m"))


def interval_set(text):
    """« ]-\\infty ; -1] \\cup [3 ; +\\infty[ » -> ensemble SymPy."""
    text = text.replace("\\mathcal{S} = ", "").strip(" $")
    if text == "\\varnothing":
        return sp.S.EmptySet
    if text == "\\mathbb{R}":
        return sp.S.Reals
    out = sp.S.EmptySet
    for part in text.split("\\cup"):
        m_ = re.fullmatch(r"\s*([\[\]])\s*(.+?)\s*;\s*(.+?)\s*([\[\]])\s*", part)
        assert m_, part
        lo = -sp.oo if "infty" in m_.group(2) else tex(m_.group(2))
        hi = sp.oo if "infty" in m_.group(3) else tex(m_.group(3))
        out = out | sp.Interval(lo, hi, m_.group(1) == "]", m_.group(4) == "[")
    return out


def dollars(s):
    return re.findall(r"\$([^$]+)\$", s)


OPS = {"<": sp.Lt, ">": sp.Gt, "\\leqslant": sp.Le, "\\geqslant": sp.Ge}


def check_generated(ex):
    """Contrôle indépendant d'un exercice généré (second_degre_formes) :
    renvoie un message d'erreur, ou None."""
    fam, en, ans = ex["family"], ex["enonce"], ex["answer"]
    if fam in ("canonique_completion", "canonique_general"):
        f = tex(re.search(r"f\(x\) = ([^$]+)\$", en).group(1))
        g = tex(re.search(r"f\(x\) = ([^$]+)\$", ans).group(1))
        if sp.expand(f - g) != 0:
            return "forme canonique fausse"
        al = sp.solve(sp.diff(f, X), X)[0]
        if fam == "canonique_general":
            sx, sy = re.search(r"S\\left\((.+) ; (.+)\\right\)", ans).groups()
            return None if (tex(sx), tex(sy)) == (al, f.subs(X, al)) else "sommet faux"
        extr = re.search(r"égal à \$([^$]+)\$, atteint en \$x = ([^$]+)\$", ans).groups()
        return None if (tex(extr[0]), tex(extr[1])) == (f.subs(X, al), al) else "extremum faux"
    if fam == "canonique_lecture":
        f = tex(re.search(r"f\(x\) = ([^$]+)\$", en).group(1))
        al = sp.solve(sp.diff(f, X), X)[0]
        sx, sy = re.search(r"S\(([^;]+) ; ([^)]+)\)", ans).groups()
        return None if (tex(sx), tex(sy)) == (al, f.subs(X, al)) else "sommet faux"
    if fam == "sommet_et_point":
        sx, sy = re.search(r"S\(([^;]+) ; ([^)]+)\)", en).groups()
        ax, ay = re.search(r"A\(([^;]+) ; ([^)]+)\)", en).groups()
        forms = re.search(r"f\(x\) = ([^=]+) = ([^$]+)\$", ans).groups()
        f, g = tex(forms[0]), tex(forms[1])
        al = tex(sx)
        ok = (sp.expand(f - g) == 0 and sp.diff(f, X).subs(X, al) == 0 and f.subs(X, al) == tex(sy)
              and f.subs(X, tex(ax)) == tex(ay))
        return None if ok else "fonction retrouvée fausse"
    if fam == "comparer_images":
        f = tex(re.search(r"f\(x\) = ([^$]+)\$", en).group(1))
        u, v = re.findall(r"f\((-?\d+)\)", en)[:2]
        want = "<" if f.subs(X, tex(u)) < f.subs(X, tex(v)) else ">"
        return None if ans == f"$f({u}) {want} f({v})$." else "comparaison fausse"
    if fam == "autre_racine":
        f = tex(re.search(r"f\(x\) = ([^$]+)\$", en).group(1))
        g = tex(re.search(r"f\(x\) = ([^$]+)\$", ans).group(1))
        r = tex(re.search(r"Vérifier que \$([^$]+)\$", en).group(1))
        other = tex(re.search(r"L'autre racine est \$([^$]+)\$", ans).group(1))
        ok = sp.expand(f - g) == 0 and f.subs(X, r) == 0 and set(sp.solve(f, X)) == {r, other}
        return None if ok else "factorisation ou seconde racine fausse"
    if fam == "deux_nombres":
        s, p = (tex(v) for v in dollars(en)[:2])
        u, v = (tex(w) for w in dollars(ans)[:2])
        return None if (u + v, u * v) == (s, p) else "nombres faux"
    if fam == "signe_racines":
        f = tex(re.search(r"f\(x\) = ([^$]+)\$", en).group(1))
        rs = [r for r in sp.solve(f, X) if r.is_real]
        if len(rs) != 2:
            return "pas deux racines"
        want = ("contraires" if rs[0] * rs[1] < 0 else ("positives" if rs[0] > 0 else "négatives"))
        return None if want in ans else "signe des racines faux"
    if fam == "expression_symetrique":
        f = tex(re.search(r"racines de \$([^$]+)\$", en).group(1))
        r1, r2 = sp.solve(f, X)
        v1, v2 = (tex(v.split("=")[-1]) for v in dollars(ans)[:2])
        ok = sp.simplify(r1**2 + r2**2 - v1) == 0 and sp.simplify(1 / r1 + 1 / r2 - v2) == 0
        return None if ok else "expressions symétriques fausses"
    if fam.startswith("inequation_") and fam != "inequation_parametre":
        body = re.search(r"inéquation \$([^$]+)\$", en).group(1)
        op = next(o for o in OPS if o in body)
        left, right = body.split(op)
        sol = sp.solve_univariate_inequality(OPS[op](tex(left) - tex(right), 0), X, relational=False)
        return None if sol == interval_set(ans) else "ensemble de solutions faux"
    if fam == "inequation_parametre":
        k = int(re.search(r"mx \+ (\d+)", en).group(1))
        sol = sp.solve_univariate_inequality(M**2 - 4 * k < 0, M, relational=False)
        return None if sol == interval_set(ans.replace("m \\in ", "")) else "intervalle faux"
    if fam == "position_relative":
        f = tex(re.search(r"y = ([^$]+)\$ et de la droite", en).group(1))
        g = tex(re.search(r"droite \$\\mathcal\{D\}\$ d'équation \$y = ([^$]+)\$", en).group(1))
        above = sp.solve_univariate_inequality(f - g > 0, X, relational=False)
        claimed = interval_set(re.search(r"au-dessus de \$\\mathcal\{D\}\$ sur \$([^$]+)\$", ans).group(1))
        return None if above == claimed else "position relative fausse"
    if fam == "enclos":
        L = int(re.search(r"Avec \$(\d+)\$ m", en).group(1))
        a = X * (L - 2 * X)
        best = sp.solve(sp.diff(a, X), X)[0]
        vals = [tex(v) for v in dollars(ans)[:3]]
        return None if vals == [best, L - 2 * best, a.subs(X, best)] else "dimensions ou aire fausses"
    if fam == "recette":
        n, k = (int(v) for v in re.search(r"\$\((\d+) - (\d+)p\)\$", en).groups())
        r = X * (n - k * X)
        best = sp.solve(sp.diff(r, X), X)[0]
        vals = [tex(v) for v in dollars(ans)[:2]]
        return None if vals == [best, r.subs(X, best)] else "prix ou recette faux"
    if fam == "projectile":
        h = tex(re.search(r"h\(t\) = ([^$]+)\$", en).group(1))
        ground = max(r for r in sp.solve(h, T) if r.is_real)
        top = sp.maximum(h, T, sp.Interval(0, ground))
        vals = [tex(v.replace("t = ", "")) for v in dollars(ans)[:3]]
        t_top = sp.solve(sp.diff(h, T), T)[0]
        return None if vals == [ground, top, t_top] else "trajectoire fausse"
    if fam == "rentabilite":
        b = tex(re.search(r"B\(q\) = ([^$]+)\$", en).group(1))
        zone = sp.solve_univariate_inequality(b >= 0, Q, relational=False)
        claimed = interval_set(re.search(r"q \\in ([^$]+)\$", ans).group(1))
        best = sp.maximum(b, Q, zone)
        return None if zone == claimed and tex(dollars(ans)[1]) == best else "rentabilité fausse"
    return f"famille sans vérificateur : {fam}"


class TestSourcesFideles(unittest.TestCase):
    def test_cours_json_identiques_aux_sources(self):
        for number, cours, _banque in modules():
            with self.subTest(chapitre=number):
                served = json.loads((COURS_DIR / f"chapitre_{number}.json").read_text(encoding="utf-8"))
                self.assertEqual(served, json.loads(json.dumps(cours.CHAPTER, ensure_ascii=False)))

    def test_banque_json_identique_aux_sources(self):
        bank = json.loads(BANK.read_text(encoding="utf-8"))
        for number, _cours, banque in modules():
            with self.subTest(chapitre=number):
                served = [e for e in bank if e["chapter_id"] == f"Chapitre_{number}"]
                self.assertEqual(sorted(served, key=lambda e: e["id"]), build_chapter(banque))

    def test_controles_de_la_banque(self):
        for number, _cours, banque in modules():
            with self.subTest(chapitre=number):
                self.assertEqual(check_chapter(banque), [])

    def test_quiz_references_dans_le_cours(self):
        for number, cours, banque in modules():
            for n in cours.CHAPTER["notions"]:
                with self.subTest(notion=n["id"]):
                    self.assertEqual(tuple(n["quizExerciseIds"]), tuple(banque.QUIZ[n["id"]]))


def _num(s):
    return sp.nsimplify(tex(s.replace("{,}", ".")), rational=True)


def check_derivation(ex):
    """Contrôle indépendant d'un exercice de derivation_2026 (relecture du texte)."""
    fam, en, ans = ex["family"], ex["enonce"], ex["answer"]
    if fam == "tangente_horizontale":
        f = tex(re.search(r"f\(x\) = ([^$]+)\$", en).group(1))
        a = sp.solve(sp.diff(f, X), X)[0]
        px, py = re.search(r"\(([^;]+) ; ([^)]+)\)", ans).groups()
        return None if (tex(px), tex(py)) == (a, f.subs(X, a)) else "point faux"
    if fam == "lire_pente_tangente":
        (x0, y0), (x1, y1) = [tuple(tex(v) for v in m) for m in re.findall(r"\((-?[\d\\{}a-z]+) ; (-?[^)]+)\)", en)[:2]]
        m_ = (y1 - y0) / (x1 - x0)
        line = tex(re.search(r"y = ([^$]+)\$", ans).group(1))
        ok = sp.expand(line - (m_ * (X - x0) + y0)) == 0 and f"f'({x0}) = " in ans
        return None if ok else "tangente fausse"
    if fam == "vitesse_instantanee":
        k = _num(re.search(r"d\(t\) = ([^t]+)t\^2", en).group(1))
        t0 = int(re.search(r"entre \$t = (\d+)\$", en).group(1))
        v = _num(re.search(r"instantanée : \$([^$]+)\$", ans).group(1))
        return None if v == 2 * k * t0 else "vitesse fausse"
    if fam == "tangente_parallele":
        f = tex(re.search(r"f\(x\) = ([^$]+)\$", en).group(1))
        d = tex(re.search(r"droite d'équation \$y = ([^$]+)\$", en).group(1))
        m_ = sp.diff(d, X)
        a = sp.solve(sp.diff(f, X) - m_, X)[0]
        line = tex(re.search(r"tangente : \$y = ([^$]+)\$", ans).group(1))
        return None if sp.expand(line - (m_ * (X - a) + f.subs(X, a))) == 0 else "tangente fausse"
    if fam == "tangentes_par_un_point":
        px, py = (tex(v) for v in re.search(r"P\(([^;]+) ; ([^)]+)\)", en).groups())
        lines = [tex(s) for s in re.findall(r"\$y = ([^$]+)\$", ans)]
        ok = len(lines) == 2 and all(l.subs(X, px) == py and sp.discriminant(sp.Poly(X**2 - l, X)) == 0 for l in lines)
        return None if ok else "tangentes fausses"
    if fam == "approximation_affine":
        f = tex(re.search(r"f\(x\) = ([^$]+)\$", en).group(1))
        a = tex(re.search(r"a = (\d+)", en).group(1))
        xv = _num(re.search(r"de \$f\(([^)]+)\)\$", en).group(1))
        approx = _num(re.search(r"\\approx ([^$ ]+)", ans).group(1))
        exact = f.subs(X, a) + sp.diff(f, X).subs(X, a) * (xv - a)
        return None if abs(approx - exact) <= sp.Rational(1, 20000) else "approximation fausse"
    if fam == "cout_marginal":
        c = tex(re.search(r"C\(q\) = ([^$]+)\$", en).group(1)).subs(Q, X)
        q0 = int(re.search(r"C'\((\d+)\)", en).group(1))
        cm, real = (_num(v) for v in re.findall(r"= ([\d{},]+)\$ €", ans)[:2])
        ok = cm == sp.diff(c, X).subs(X, q0) and real == c.subs(X, q0 + 1) - c.subs(X, q0)
        return None if ok else "coût marginal faux"
    if fam in ("puissance_negative", "regle_inverse", "produit_racine"):
        f = tex(re.search(r"f\(x\) = ([^$]+)\$", en).group(1))
        d = tex(re.search(r"f'\(x\) = ([^$]+)\$", ans).group(1))
        return None if sp.simplify(sp.diff(f, X) - d) == 0 else "dérivée fausse"
    return f"famille sans vérificateur : {fam}"


class TestGenerateurDerivation2026(unittest.TestCase):
    def test_verification_independante(self):
        for fam in derivation_2026.FAMILIES:
            for seed in range(40):
                ex = derivation_2026.generate_one(fam.id, seed=seed)
                with self.subTest(famille=fam.id, seed=seed):
                    self.assertIsNone(check_derivation(ex), ex["enonce"] + " || " + ex["answer"])

    def test_deterministe_et_notions_du_cours(self):
        self.assertEqual(derivation_2026.generate_pool(per_family=3), derivation_2026.generate_pool(per_family=3))
        # Dérivation : chapitre 5 du manuel ; seules les familles servies comptent.
        titles = {n["title"] for n in json.loads((COURS_DIR / "chapitre_5.json").read_text(encoding="utf-8"))["notions"]}
        for fid, (chapitre, notion) in programme_1es.ADAPTATION[derivation_2026].items():
            self.assertEqual(chapitre, "Chapitre_5")
            self.assertIn(notion, titles)


class TestGenerateursProgramme2026(unittest.TestCase):
    def test_deterministe(self):
        self.assertEqual(second_degre_formes.generate_pool(per_family=4, seed=7),
                         second_degre_formes.generate_pool(per_family=4, seed=7))

    def test_pool_servi_reproductible(self):
        served = [e for e in json.loads(GENERATED.read_text(encoding="utf-8"))
                  if e["id"] >= second_degre_formes.GENERATED_ID_OFFSET
                  and e["id"] < second_degre_formes.GENERATED_ID_OFFSET + 20_000]
        # 206 avant l'adaptation au manuel « Première ES/L » ; 9 familles (somme
        # et produit des racines, position relative, modélisation) sont hors
        # manuel : il reste environ la moitié du pool.
        self.assertGreater(len(served), 90)
        fresh = {e["enonce"]: e for e in second_degre_formes.generate_pool(per_family=12, seed=20261025)}
        for e in served:
            self.assertEqual(fresh[e["enonce"]]["answer"], e["answer"])

    def test_verification_independante(self):
        """60 tirages par famille, chacun relu et recalculé par SymPy."""
        for fam in second_degre_formes.FAMILIES:
            for seed in range(60):
                ex = second_degre_formes.generate_one(fam.id, seed=seed)
                with self.subTest(famille=fam.id, seed=seed):
                    self.assertIsNone(check_generated(ex), ex["enonce"] + " || " + ex["answer"])

    def test_notion_existe_dans_le_cours(self):
        # Polynômes du second degré : chapitre 3 du manuel ; familles servies seulement.
        titles = {n["title"] for n in json.loads((COURS_DIR / "chapitre_3.json").read_text(encoding="utf-8"))["notions"]}
        for fid, (chapitre, notion) in programme_1es.ADAPTATION[second_degre_formes].items():
            self.assertEqual(chapitre, "Chapitre_3")
            self.assertIn(notion, titles)


class TestNotionsServiesAuProgramme(unittest.TestCase):
    """Tout exercice servi (banque curée et pool généré) est rattaché à une
    notion présente dans le cours de son chapitre : aucune notion retirée
    (hors manuel « Première ES/L ») ne doit apparaître."""

    def _titles(self, chapter_id):
        path = COURS_DIR / f"chapitre_{chapter_id.split('_')[1]}.json"
        return {n["title"] for n in json.loads(path.read_text(encoding="utf-8"))["notions"]}

    def test_banque_et_pool(self):
        # Chapitres repris uniquement (premiere_specifique/chapitres.py) : la liste
        # s'allonge à chaque chapitre terminé.
        repris = {f"Chapitre_{n}" for n, _c, _b in modules()}
        bank = json.loads((ROOT / "exercises_bank_premiere_specifique.json").read_text(encoding="utf-8"))
        generated = json.loads(GENERATED.read_text(encoding="utf-8"))
        cache = {}
        for e in (x for x in bank + generated if x["chapter_id"] in repris):
            titles = cache.setdefault(e["chapter_id"], self._titles(e["chapter_id"]))
            with self.subTest(id=e["id"]):
                self.assertIn(e["notion"], titles)

    def test_structure_du_manuel(self):
        titres = [json.loads((COURS_DIR / f"chapitre_{n}.json").read_text(encoding="utf-8"))["title"] for n in range(1, 10)]
        self.assertEqual(titres, ["Pourcentages", "Fonctions numériques", "Polynômes du second degré", "Statistiques", "Dérivation",
                                  "Dérivation et variations", "Suites numériques", "Variables aléatoires", "Loi de Bernoulli et loi binomiale"])
        self.assertEqual(sorted(p.name for p in COURS_DIR.glob("chapitre_*.json")), sorted(f"chapitre_{n}.json" for n in range(1, 10)))

    def test_aucune_famille_hors_manuel_servie(self):
        servies = {(e["chapter_id"], e["family"]) for e in json.loads(GENERATED.read_text(encoding="utf-8"))}
        autorisees = {(ch, fid) for table in programme_1es.ADAPTATION.values() for fid, (ch, _n) in table.items()}
        self.assertLessEqual(servies, autorisees)
        familles = {f for _ch, f in servies}
        for hors in ("somme_produit", "composition_puissance", "transformation_affine", "sommes_arith", "approximation_affine", "droite"):
            self.assertNotIn(hors, familles)


class TestAccesParAbonnement(PreviewHTTPCase):
    """Les 9 chapitres se chargent pour Free, Premium et Ultra ; chaque formule
    reçoit exactement les exemples de son niveau, et Ultra les démonstrations."""

    PLANS = {"free": ("free",), "premium": ("free", "premium"), "ultra": ("free", "premium", "ultra")}

    def test_trois_formules_sur_les_neuf_chapitres(self):
        sources = {n: json.loads((COURS_DIR / f"chapitre_{n}.json").read_text(encoding="utf-8")) for n in range(1, 10)}
        for plan, niveaux in self.PLANS.items():
            if plan != "free":
                db.set_stripe_subscription(self.user["id"], f"sub_{plan}", plan, "active")
            for n, source in sources.items():
                resp = self.client.get(f"/api/course-content/premiere_specifique/Chapitre_{n}", headers=self.headers)
                with self.subTest(plan=plan, chapitre=n):
                    self.assertEqual(resp.status_code, 200)
                    servies = {x["id"]: x for x in resp.get_json()["notions"]}
                    for notion in source["notions"]:
                        attendus = {e["id"] for e in notion["exemples"] if e["niveauAcces"] in niveaux}
                        recus = {e["id"] for e in servies[notion["id"]]["exemples"]}
                        self.assertEqual(recus, attendus, notion["id"])
                        if plan == "ultra" and notion.get("demonstration"):
                            self.assertIn("demonstration", servies[notion["id"]])


if __name__ == "__main__":
    unittest.main()
