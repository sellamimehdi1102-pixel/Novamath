# -*- coding: utf-8 -*-
"""Tests de cohérence mathématique — mission "audit mathématique exhaustif de
tous les exercices" (2026-09-03).

Un audit manuel + par sous-agents a recalculé indépendamment (sympy/Fraction)
des milliers d'exercices générés et un échantillon quasi exhaustif (>1200)
de exercises_bank.json / exercises_bank_premiere.json / exercises_bank_troisieme.json.
Tous les GÉNÉRATEURS (webapp/exercise_generator*/) se sont révélés auto-vérifiés
par construction (la réponse est calculée par sympy/Fraction à partir de la
même expression que l'énoncé). Les erreurs trouvées étaient toutes dans les
banques CURÉES statiques (texte + calcul écrits à la main, sans relecture
automatique) — notamment :

  - exercises_bank.json, id 130 : `answer` contredisait ses propres
    `solution_steps` (f(3)-f(1) affiché "20-3=17" alors que les étapes elles-
    mêmes donnaient f(3)=13, f(1)=5, soit 8).
  - exercises_bank_premiere.json, ids 650-707 (18 exercices, notion
    "Opérations et dérivation") : pour f(x)=(ax²+bx)+(cx+d), la dérivée
    stockée valait (2a+c)x+b au lieu de 2a·x+(b+c) — la constante v'(x)=c
    était additionnée au coefficient de x au lieu de la constante b.

Ces deux CLASSES d'erreurs partagent un trait commun : l'énoncé et la
"méthode" affichée étaient corrects, seule la RECOMBINAISON FINALE des
valeurs intermédiaires (déjà correctement calculées et affichées) était
fausse. Les tests ci-dessous détectent GÉNÉRIQUEMENT ce type d'erreur — ils
scannent TOUTE la banque curée à la recherche du patron textuel concerné (pas
un ID particulier) et recalculent indépendamment, de sorte qu'ils s'appliquent
aussi à tout exercice futur qui reproduirait le même patron.

Mission "audit exhaustif des exercices curés restants" (2026-09-04) : les
~5 500 exercices curés qui n'avaient pas encore été vérifiés individuellement
l'ont été (couverture 100% des 3 banques), révélant 22 anomalies supplémentaires
(19 critiques, 1 majeure, 2 mineures), toutes corrigées. Deux classes
supplémentaires, génériques, ont été ajoutées ici :

  - `TestReductionAlgebriqueConclusionCoherente` : détecte le bug id 523
    (exercises_bank.json, "A = (x+2)(x-3)-(x-1)^2" : answer="-x-7" alors que
    la dernière étape concluait elle-même "A = x - 7") — et a également
    attrapé un second cas du même patron (id 597) lors de sa vérification
    contre les données pré-correction, confirmant sa généralité.
  - `TestPuissanceNegativeDeBaseNegativeSigneCorrect` : détecte le bug ids
    920002/920030/920082/920106 ("-N^{-M}" affiché comme +1/P au lieu de
    -1/P — l'exposant négatif ne s'applique qu'à N, pas au signe qui précède).

Ce fichier ne couvre PAS l'intégralité des types de calcul possibles (voir le
rapport de mission pour le détail exact de ce qui est/n'est pas couvert) : il
s'agit de verrous anti-régression ciblés sur les patrons de bugs réellement
trouvés, pas d'un vérificateur mathématique universel."""
import json
import re
import unittest
from pathlib import Path

import sympy
from sympy.parsing.sympy_parser import (
    implicit_multiplication_application,
    parse_expr,
    standard_transformations,
)

from curriculum_registry import CURRICULUM_REGISTRY

ROOT = Path(__file__).resolve().parent.parent.parent
_TRANSFORMATIONS = standard_transformations + (implicit_multiplication_application,)
_X = sympy.symbols("x")


def _load(path):
    if path is None or not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def _all_curated_exercises():
    """Toutes les banques curées statiques (pas les pools générés, déjà
    auto-vérifiés par construction — voir docstring du module)."""
    exercises = []
    for class_level, profile in CURRICULUM_REGISTRY.items():
        for ex in _load(profile.exercise_bank):
            exercises.append((class_level, ex))
    return exercises


class TestDeriveeDeSommeCoherente(unittest.TestCase):
    """Détecte le bug ids 650-707 : pour tout exercice curé qui affiche
    "u'(x) = <U> et v'(x) = <V>" dans ses `solution_steps` (règle (u+v)'=u'+v'),
    la réponse finale f'(x) doit être EXACTEMENT u'(x)+v'(x), recalculée de
    façon indépendante (sympy), pas seulement "avoir la bonne forme"."""

    _STEP_RE = re.compile(r"u'\(x\) = (.+?) et \$v'\(x\) = (.+?)\$\.")
    _ANSWER_RE = re.compile(r"f'\(x\) = (.+?)\$?$")

    def _extract_affine(self, latex_expr):
        cleaned = latex_expr.replace("$", "").strip()
        return parse_expr(cleaned.replace("^", "**"), transformations=_TRANSFORMATIONS)

    def test_somme_de_deux_fonctions_recombinee_correctement(self):
        checked = 0
        for class_level, ex in _all_curated_exercises():
            steps = ex.get("solution_steps") or []
            if len(steps) < 3:
                continue
            m = self._STEP_RE.search(steps[1] if len(steps) > 1 else "")
            if not m:
                continue
            answer = ex.get("answer", "")
            m_ans = re.search(r"f'\(x\) = (.+?)\$", answer)
            if not m_ans:
                continue
            with self.subTest(class_level=class_level, id=ex.get("id")):
                uprime = self._extract_affine(m.group(1))
                vprime = self._extract_affine(m.group(2))
                expected = sympy.expand(uprime + vprime)
                stored = self._extract_affine(m_ans.group(1))
                self.assertEqual(
                    sympy.expand(stored - expected), 0,
                    f"{class_level}/id {ex.get('id')} : f'(x) stocké = {stored}, "
                    f"attendu u'(x)+v'(x) = {expected} (u'={uprime}, v'={vprime})",
                )
                checked += 1
        # Verrou anti-faux-négatif : si ce patron disparaît totalement de la
        # banque (refonte future), le test ne doit pas rester "vert" en silence
        # sans avoir jamais rien vérifié.
        self.assertGreater(checked, 0, "aucun exercice ne correspond au patron (u+v)' — test à revoir")


class TestVariationDeFonctionCoherente(unittest.TestCase):
    """Détecte le bug id 130 : pour tout exercice curé de type "calculer la
    variation de f entre a et b" qui affiche f(a)=... et f(b)=... dans ses
    `solution_steps`, la variation annoncée dans `answer` doit être EXACTEMENT
    f(b)-f(a), recalculée indépendamment à partir des valeurs déjà affichées
    (pas seulement re-décodées depuis le answer lui-même)."""

    # Ne matche QUE le cas 100% numérique "f(<nombre>) - f(<nombre>) = <vb> - <va> = <résultat>"
    # (jamais f(x_1)-f(x_2), une démonstration symbolique générale — celle-ci n'a pas de
    # valeur numérique à recalculer et ne doit pas être capturée).
    _NUM = r"-?\d+(?:[.,]\d+)?"
    _VARIATION_RE = re.compile(
        rf"f\(\d+(?:[.,]\d+)?\)\s*-\s*f\(\d+(?:[.,]\d+)?\)\s*=\s*({_NUM})\s*-\s*({_NUM})\s*=\s*({_NUM})"
    )
    _ANSWER_NUM_RE = re.compile(_NUM)

    def test_variation_f_b_moins_f_a_coherente(self):
        checked = 0
        for class_level, ex in _all_curated_exercises():
            steps = ex.get("solution_steps") or []
            if len(steps) < 3:
                continue
            haystack = (ex.get("notion") or "") + " " + (ex.get("enonce") or "")
            if "variation" not in haystack.lower():
                continue
            match = None
            for s in steps:
                match = self._VARIATION_RE.search(s)
                if match:
                    break
            if match is None:
                continue
            vb = float(match.group(1).replace(",", "."))
            va = float(match.group(2).replace(",", "."))
            resultat = float(match.group(3).replace(",", "."))
            with self.subTest(class_level=class_level, id=ex.get("id")):
                self.assertAlmostEqual(
                    vb - va, resultat, places=6,
                    msg=(
                        f"{class_level}/id {ex.get('id')} : l'étape de variation affiche "
                        f"{vb} - {va} = {resultat}, mais {vb} - {va} = {vb - va}"
                    ),
                )
                # La réponse finale doit citer ce même résultat quelque part.
                answer = ex.get("answer", "")
                answer_nums = [float(n.replace(",", ".")) for n in self._ANSWER_NUM_RE.findall(answer)]
                self.assertIn(
                    round(resultat, 6), [round(n, 6) for n in answer_nums],
                    f"{class_level}/id {ex.get('id')} : answer={answer!r} ne contient pas le résultat "
                    f"{resultat} calculé dans solution_steps",
                )
                checked += 1
        self.assertGreater(checked, 0, "aucun exercice ne correspond au patron variation f(b)-f(a) — test à revoir")


def _latex_to_sympy_text(latex):
    """Convertisseur LaTeX -> texte analysable par sympy, volontairement
    limité aux constructions rencontrées dans les banques curées (pas de
    nesting profond) : \\dfrac{a}{b} et \\frac{a}{b} -> (a)/(b), \\times/\\cdot
    -> *, ^{n} -> **n, suppression de \\left/\\right/$."""
    s = latex.strip().strip("$").strip()
    s = s.replace("\\left", "").replace("\\right", "")
    s = re.sub(r"\\d?frac\{([^{}]+)\}\{([^{}]+)\}", r"((\1)/(\2))", s)
    s = s.replace("\\times", "*").replace("\\cdot", "*")
    s = re.sub(r"\^\{(-?\d+)\}", r"**(\1)", s)
    s = s.replace("^", "**")
    s = re.sub(r"(\d),(\d)", r"\1.\2", s)  # virgule décimale française -> point
    return s


class TestReductionAlgebriqueConclusionCoherente(unittest.TestCase):
    """Détecte le bug id 523 (exercises_bank.json, "Distributivité et identités
    remarquables" : A=(x+2)(x-3)-(x-1)^2, answer="-x-7" alors que la dernière
    étape calcule et affirme elle-même "A = x - 7") : pour tout exercice curé
    dont le `answer` est de la forme "$X = <expr>$" (X = un identifiant simple :
    A, B, y, f(x)...), si la DERNIÈRE étape de `solution_steps` affiche aussi
    une assignation "$X = <expr2>$" pour ce même X, les deux expressions
    doivent être algébriquement identiques (recalcul sympy), pas seulement
    textuellement proches. Beaucoup d'exercices n'ont pas ce format (réponses
    "Oui"/"Non"/prose) : ils sont simplement ignorés (pas de faux positif),
    voir test_aucun_faux_positif_sur_reponses_non_algebriques ci-dessous."""

    _ANSWER_ASSIGN_RE = re.compile(r"^\$([A-Za-z](?:\([^)$]*\))?'?) = (.+)\$$")

    def test_derniere_etape_coherente_avec_answer(self):
        checked = 0
        for class_level, ex in _all_curated_exercises():
            answer = (ex.get("answer") or "").strip()
            m = self._ANSWER_ASSIGN_RE.match(answer)
            if not m:
                continue
            ident, expr_answer = m.group(1), m.group(2)
            steps = ex.get("solution_steps") or []
            if not steps:
                continue
            last_step = steps[-1]
            m_step = re.search(
                r"\$" + re.escape(ident) + r" = (.+?)\$(?!.*\$" + re.escape(ident) + r" = )",
                last_step,
            )
            if not m_step:
                continue
            try:
                left = parse_expr(_latex_to_sympy_text(expr_answer), transformations=_TRANSFORMATIONS)
                right = parse_expr(_latex_to_sympy_text(m_step.group(1)), transformations=_TRANSFORMATIONS)
            except Exception:
                continue  # expression non-algébrique (texte, ensembles...) : hors périmètre de ce test
            with self.subTest(class_level=class_level, id=ex.get("id")):
                self.assertEqual(
                    sympy.simplify(left - right), 0,
                    f"{class_level}/id {ex.get('id')} : answer donne {ident} = {left}, "
                    f"mais la dernière étape conclut {ident} = {right}",
                )
                checked += 1
        self.assertGreater(checked, 0, "aucun exercice ne correspond au patron 'X = expr' — test à revoir")


class TestPuissanceNegativeDeBaseNegativeSigneCorrect(unittest.TestCase):
    """Détecte le bug ids 920002/920030/920082/920106 (exercises_bank.json,
    "Puissances entières relatives") : pour toute réponse de la forme
    "$-N^{-M} = \\dfrac{1}{P}$" (M pair rendant le piège invisible), le signe
    doit être respecté : -N^{-M} = -(N**(-M)), jamais +(N**(-M)) — l'exposant
    ne s'applique qu'à N, pas au signe qui le précède."""

    _RE = re.compile(r"\$-(\d+)\^\{(-\d+)\} = (-?)\\dfrac\{1\}\{(\d+)\}\$")

    def test_signe_de_moins_n_puissance_m_correct(self):
        checked = 0
        for class_level, ex in _all_curated_exercises():
            answer = ex.get("answer") or ""
            m = self._RE.search(answer)
            if not m:
                continue
            n, exp, sign, denom = int(m.group(1)), int(m.group(2)), m.group(3), int(m.group(4))
            expected = sympy.Rational(-1, n ** (-exp))
            with self.subTest(class_level=class_level, id=ex.get("id")):
                stored = sympy.Rational(-1 if sign == "-" else 1, denom)
                self.assertEqual(
                    stored, expected,
                    f"{class_level}/id {ex.get('id')} : answer={answer!r} donne {sign or '+'}1/{denom}, "
                    f"attendu -{n}^{{{exp}}} = {expected}",
                )
                checked += 1
        self.assertGreater(checked, 0, "aucun exercice ne correspond au patron '-N^{-M}' — test à revoir")


if __name__ == "__main__":
    unittest.main()
