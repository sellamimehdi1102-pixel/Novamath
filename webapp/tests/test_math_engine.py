"""
Suite de tests dédiée à chatbot/math_engine.py — jusqu'ici absente du
projet alors que c'est le seul module qui calcule réellement (sympy) avant
tout recours au LLM (voir audit "pertinence contextuelle", 2026-10-17).

Chantier "respect des contraintes explicites" (test B, 2026-10-17) : bug
confirmé et corrigé — SOLVE_RE/EXPAND_RE/FACTOR_RE/CALCULATE_RE capturent
jusqu'à la fin de la phrase (pas de limite fiable entre l'équation/
l'expression et une consigne qui la précède ou la suit dans le même
message), et la multiplication implicite de SymPy interprétait silencieusement
un mot français comme un produit de symboles à une lettre (ex: "complètement"
-> c*e²*l*m²*n*o*p*t²), sans jamais lever d'exception — produisant une
"solution" inventée avec un degré d'équation faux. Corrigé par _trim_to_math
(isolation de l'expression aux deux extrémités du texte capturé) et une
double vérification dans _to_sympy_expr (avant ET après l'interprétation
SymPy, voir ses docstrings).
"""
import unittest

from chatbot import math_engine as me


class TestEquationsSeules(unittest.TestCase):
    def test_premier_degre(self):
        r = me.try_solve("Résous 2x + 4 = 10")
        self.assertIn("premier degré", r)
        self.assertIn("x = 3", r)

    def test_second_degre(self):
        r = me.try_solve("Résous x² - 5x + 6 = 0")
        self.assertIn("second degré", r)
        self.assertIn("x = 2", r)
        self.assertIn("x = 3", r)

    def test_second_degre_discriminant_negatif(self):
        """x² + 1 = 0 : comportement préexistant, non modifié par ce
        chantier — sympy renvoie les racines complexes plutôt qu'un message
        "pas de solution réelle" (ce message ne sert que si solve() renvoie
        une liste vide, ce qui n'est pas le cas ici)."""
        r = me.try_solve("Résous x² + 1 = 0")
        self.assertIn("second degré", r)
        self.assertIn("i", r)


class TestEquationsSuiviesDinstructions(unittest.TestCase):
    """Le bug confirmé du test B : une consigne en français collée à
    l'équation, dans la MÊME phrase, ne doit plus jamais être interprétée
    comme des symboles mathématiques — l'équation doit rester préservée et
    correctement résolue."""

    def test_equation_suivie_dune_consigne_explique_les_etapes(self):
        r = me.try_solve("Résous complètement x² - 5x + 6 = 0 et explique toutes les étapes.")
        self.assertIn("second degré", r)
        self.assertIn("x = 2", r)
        self.assertIn("x = 3", r)
        # Aucun symbole étranger (issu d'un mot français mal interprété) ne
        # doit apparaître dans la réponse.
        for lettre_parasite in ("c e", "l m", "n o", "o p"):
            self.assertNotIn(lettre_parasite, r)

    def test_equation_precedee_dun_adverbe(self):
        r = me.try_solve("Résous rapidement 2x + 4 = 10")
        self.assertIn("x = 3", r)

    def test_equation_suivie_de_politesse(self):
        r = me.try_solve("Résous x² - 5x + 6 = 0, merci beaucoup")
        self.assertIn("x = 2", r)
        self.assertIn("x = 3", r)
        self.assertNotIn("0.0", r, "la ponctuation collée ne doit pas se transformer en séparateur décimal")

    def test_developpe_suivi_dune_consigne(self):
        r = me.try_solve("Développe maintenant (x+1)(x-2) et donne le résultat simplifié")
        self.assertIn("x^{2}", r)

    def test_factorise_suivi_dune_consigne(self):
        r = me.try_solve("Factorise x² - 4 puis explique la méthode utilisée")
        self.assertIn("x - 2", r)
        self.assertIn("x + 2", r)

    def test_calcule_suivi_dune_question(self):
        r = me.try_solve("Calcule 12 * 3 + 5 et dis-moi si c'est juste")
        self.assertIn("41", r)


class TestVariablesQuelconques(unittest.TestCase):
    """Aucune équation ne doit être silencieusement supposée porter sur
    "x" — n'importe quelle lettre inconnue doit être résolue correctement."""

    def test_variable_n(self):
        r = me.try_solve("Résous 3n - 9 = 0")
        self.assertIn("n = 3", r)

    def test_variable_y_second_degre(self):
        r = me.try_solve("Résous y² - 4 = 0")
        self.assertIn("y = -2", r)
        self.assertIn("y = 2", r)

    def test_variable_t(self):
        r = me.try_solve("Résous 5t + 1 = 11")
        self.assertIn("t = 2", r)


class TestFractionsEtAutresSyntaxes(unittest.TestCase):
    def test_simplification_fraction(self):
        r = me.try_solve("Simplifie 8/12")
        self.assertIn("2/3", r)

    def test_pourcentage(self):
        r = me.try_solve("Calcule 20% de 50")
        self.assertIn("10", r)

    def test_racine(self):
        r = me.try_solve("Simplifie √50")
        self.assertIsNotNone(r)


class TestEquationsTrigonometriques(unittest.TestCase):
    """Chantier "fiabilité mathématique" (2026-10-17, audit) : bug confirmé
    et corrigé — solve() sur une équation trigonométrique ne renvoie qu'un
    sous-ensemble FINI de solutions (ex: sin(x)=0 -> seulement x=0 et x=π),
    jamais l'ensemble complet (périodique, infini), présenté pourtant avec
    le même format de confiance qu'une résolution complète. Refus général :
    toute équation contenant sin/cos/tan/cot/sec/csc retombe sur le LLM."""

    def test_sin_egal_zero_refuse_proprement(self):
        self.assertIsNone(me.try_solve("Résous sin(x) = 0"))

    def test_cos_egal_un_refuse_proprement(self):
        self.assertIsNone(me.try_solve("Résous cos(x) = 1"))

    def test_tan_egal_un_refuse_proprement(self):
        self.assertIsNone(me.try_solve("Résous tan(x) = 1"))

    def test_sin_egal_demi_refuse_proprement(self):
        self.assertIsNone(me.try_solve("Résous sin(x) = 1/2"))

    def test_equation_trigonometrique_avec_domaine_explicite_refuse_aussi(self):
        """Même avec un domaine précisé dans le message, Math Engine ne sait
        pas l'exploiter (aucune notion de domaine dans son code) : refus
        général, jamais une solution partielle faussement présentée comme
        complète."""
        self.assertIsNone(me.try_solve("Résous sin(x) = 0 pour x dans [0, 2π]"))

    def test_calcul_trigonometrique_direct_reste_fonctionnel(self):
        """Non-régression : un calcul direct (pas une résolution d'équation,
        _calculate n'appelle jamais solve()) reste correct et inchangé."""
        r = me.try_solve("Calcule sin(pi/2)")
        self.assertIn("1", r)


class TestDivisionParZeroEtFormesIndeterminees(unittest.TestCase):
    """Chantier "fiabilité mathématique" (2026-10-17, audit) : bug confirmé
    et corrigé — parse_expr(evaluate=True) évalue une division par zéro en
    `zoo` (infini complexe) et 0/0 en `nan`, tous deux affichés auparavant
    comme des résultats mathématiques valides ($\\tilde{\\infty}$/$NaN$)."""

    def test_calcule_cinq_sur_zero_ne_montre_jamais_zoo(self):
        r = me.try_solve("Calcule 5/0")
        self.assertIsNotNone(r)
        self.assertNotIn("zoo", r.lower())
        self.assertNotIn("infty", r.lower())
        self.assertIn("division par zéro", r.lower())

    def test_calcule_zero_sur_zero_ne_montre_jamais_nan(self):
        r = me.try_solve("Calcule 0/0")
        self.assertIsNotNone(r)
        self.assertNotIn("nan", r.lower())
        self.assertIn("indéterminée", r.lower())

    def test_resous_x_sur_zero_ne_montre_jamais_zoo(self):
        r = me.try_solve("Résous x/0 = 5")
        self.assertIsNotNone(r)
        self.assertNotIn("zoo", r.lower())
        self.assertNotIn("infty", r.lower())
        self.assertIn("division par zéro", r.lower())


class TestEquationsSansSolutionUniqueOuInfinite(unittest.TestCase):
    """Distinguer "aucune solution" (égalité toujours fausse) de "infinité
    de solutions" (égalité toujours vraie) plutôt qu'un refus silencieux
    identique dans les deux cas — chantier "fiabilité mathématique"."""

    def test_egalite_toujours_fausse_aucune_solution(self):
        r = me.try_solve("Résous 0 * x = 5")
        self.assertIsNotNone(r)
        self.assertIn("aucune solution", r.lower())
        self.assertNotIn("True", r)
        self.assertNotIn("False", r)

    def test_egalite_toujours_vraie_infinite_de_solutions(self):
        r = me.try_solve("Résous 0 * x = 0")
        self.assertIsNotNone(r)
        self.assertIn("infinité de solutions", r.lower())

    def test_equation_a_solution_unique_toujours_correcte(self):
        """Non-régression : le cas normal (une seule solution) n'est pas
        affecté par la distinction ajoutée ci-dessus."""
        r = me.try_solve("Résous 2x + 4 = 10")
        self.assertIn("x = 3", r)


class TestNonRegressionAlgebreEtCalculsDejaFonctionnels(unittest.TestCase):
    """Non-régression explicite (chantier "fiabilité mathématique") : les
    équations algébriques et calculs déjà corrects avant ce chantier ne
    doivent pas être affectés par les refus ajoutés ci-dessus (trigonométrie,
    division par zéro) ni par la distinction aucune/infinité de solutions."""

    def test_premier_degre_plusieurs_variables(self):
        for var, msg, attendu in [
            ("n", "Résous 3n - 9 = 0", "n = 3"),
            ("t", "Résous 5t + 1 = 11", "t = 2"),
            ("m", "Résous 2m - 8 = 0", "m = 4"),
        ]:
            with self.subTest(var=var):
                self.assertIn(attendu, me.try_solve(msg))

    def test_second_degre_plusieurs_variables(self):
        r = me.try_solve("Résous y² - 4 = 0")
        self.assertIn("y = -2", r)
        self.assertIn("y = 2", r)

    def test_developpement_factorisation_inchanges(self):
        self.assertIn("x^{2}", me.try_solve("Développe (x+1)(x-2)"))
        self.assertIn("x - 2", me.try_solve("Factorise x² - 4"))

    def test_calculs_simples_inchanges(self):
        self.assertIn("53", me.try_solve("Calcule 7 * 8 - 3"))
        self.assertIn("10", me.try_solve("Calcule 20% de 50"))
        self.assertIn("2/3", me.try_solve("Simplifie 8/12"))


class TestExpressionsMalformeesRefuseesProprement(unittest.TestCase):
    """Si Math Engine ne peut pas interpréter une expression avec
    suffisamment de fiabilité, il doit renvoyer None (jamais planter, jamais
    inventer une solution) pour laisser le fallback/LLM prendre le relais."""

    def test_aucune_equation_reelle(self):
        self.assertIsNone(me.try_solve("Résous blabla"))

    def test_deux_variables_ambigu(self):
        self.assertIsNone(me.try_solve("Résous x + y = 5"))

    def test_message_sans_trigger(self):
        self.assertIsNone(me.try_solve("Qu'est-ce qu'une équation ?"))

    def test_message_vide(self):
        self.assertIsNone(me.try_solve(""))
        self.assertIsNone(me.try_solve(None))

    def test_indice_avec_equation_laisse_le_fallback_en_amont(self):
        """Non couvert ici (le court-circuit vers le LLM se décide dans
        conversation_manager/response_strategy, pas dans math_engine lui-
        même) — mais try_solve() continue de calculer correctement SI on
        l'appelle directement, pour ne jamais perdre cette capacité aux
        endroits où elle est légitimement utile."""
        r = me.try_solve("Aide-moi à résoudre x² - 5x + 6 = 0 sans me donner la réponse.")
        self.assertIn("x = 2", r)
        self.assertIn("x = 3", r)


if __name__ == "__main__":
    unittest.main()
