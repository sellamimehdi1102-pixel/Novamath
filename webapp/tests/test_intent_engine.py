"""
Suite fonctionnelle de l'Intent Engine v2 (Response Engine v2, Phase 1) :
les 10 nouvelles intentions, la détection de quantité ("3 exercices",
"plusieurs exemples"), et le repli flou (formulations jamais vues, politesse,
fautes de frappe, conjugaisons différentes) — chaque cas a été vérifié
empiriquement (exploration interactive) avant d'être figé ici, y compris les
échecs découverts et corrigés en cours de route (mots vides faussant la
couverture, accents non repliés, conjugaisons non couvertes).
"""
import unittest

from chatbot.services import intent_service as ins


class TestNouvellesIntentionsRegex(unittest.TestCase):
    """Formulations directes, déclenchées par une regex de _INTENT_PATTERNS."""

    CASES = [
        ("C'est quoi une puissance ?", ins.DEFINITION),
        ("Qu'est-ce qu'une puissance ?", ins.DEFINITION),  # élision "qu'une" (pas "que une")
        ("Définition de la puissance", ins.DEFINITION),
        ("Que veut dire puissance ?", ins.DEFINITION),
        ("Donne-moi le cours sur les puissances", ins.COURS),
        ("Montre-moi le cours sur les puissances", ins.COURS),
        ("Résume-moi les puissances", ins.RESUME),
        ("Fais-moi un résumé sur les puissances", ins.RESUME),
        ("Quelle est la méthode pour les puissances", ins.METHODE),
        ("Comment résoudre une puissance", ins.METHODE),
        ("Quelles sont les étapes pour simplifier une puissance", ins.METHODE),
        ("Quelle est la propriété des puissances", ins.PROPRIETE),
        ("Propriétés des puissances", ins.PROPRIETE),
        ("Démontre que a^0 = 1", ins.DEMONSTRATION),
        ("Prouve que a^0 = 1", ins.DEMONSTRATION),
        ("Donne-moi un indice sur les puissances", ins.INDICE),
        ("Un petit indice sur les puissances stp", ins.INDICE),
        ("Rappelle-moi les puissances", ins.RAPPEL),
        ("Petit rappel sur les puissances", ins.RAPPEL),
        ("Je veux réviser les puissances", ins.REVISION),
        ("Prépare-moi pour le contrôle sur les puissances", ins.REVISION),
        ("Explique-moi autrement les puissances", ins.REFORMULATION),
        ("Reformule ça", ins.REFORMULATION),
        ("Explique moi autrement", ins.REFORMULATION),  # espace, pas tiret — bug de regex corrigé
    ]

    def test_toutes_les_formulations_directes(self):
        for text, expected in self.CASES:
            with self.subTest(text=text):
                self.assertEqual(ins.classify(text)["intent"], expected)


class TestQuantite(unittest.TestCase):
    def test_nombre_explicite(self):
        result = ins.classify("Donne-moi 3 exercices sur les puissances")
        self.assertEqual(result["intent"], ins.EXERCICE)
        self.assertEqual(result["quantity"], 3)

    def test_plusieurs(self):
        result = ins.classify("Donne-moi plusieurs exemples sur les puissances")
        self.assertEqual(result["intent"], ins.EXEMPLE)
        self.assertEqual(result["quantity"], 3)

    def test_absente_par_defaut(self):
        result = ins.classify("Donne-moi un exercice sur les puissances")
        self.assertIsNone(result["quantity"])

    def test_borne_raisonnable(self):
        """Une quantité absurde ("500 exercices") est plafonnée, pas prise
        telle quelle — évite qu'un futur Exercise Engine tente de générer
        500 exercices d'un coup sur une simple faute de frappe utilisateur."""
        result = ins.classify("Donne-moi 500 exercices sur les puissances")
        self.assertLessEqual(result["quantity"], 10)


class TestRepliFlou(unittest.TestCase):
    """Formulations JAMAIS présentes dans _FUZZY_TRIGGER_PHRASES ni dans les
    regex — reconnues uniquement par couverture de mots (voir
    _phrase_coverage). Chaque cas a d'abord échoué en exploration, puis a été
    corrigé (mots vides, accents, verbe conjugué) avant d'être figé ici."""

    CASES = [
        ("Est-ce que tu pourrais m'expliquer autrement ce concept car je ne comprends vraiment pas", ins.REFORMULATION),
        ("Pourrais-tu stp me donner un petit indice sans me donner la reponse direct", ins.INDICE),
        ("Je voudrais un tout petit rappel sur les puissances si possible", ins.RAPPEL),
        ("Est ce que tu peux demontrer que a^0 vaut 1", ins.DEMONSTRATION),
        ("Aide moi a reviser un peu les puissances stp", ins.REVISION),
        ("Peux tu me dire la propriete des puissances", ins.PROPRIETE),
        ("Bonjour, auriez vous la gentillesse de me faire un petit resume sur les puissances", ins.RESUME),
        ("Peux tu me montrer un exemple avec les puissances stp", ins.EXEMPLE),
        ("jaimerai bien un exercice dentrainement sur les puissances", ins.EXERCICE),
    ]

    def test_formulations_jamais_vues(self):
        for text, expected in self.CASES:
            with self.subTest(text=text):
                self.assertEqual(ins.classify(text)["intent"], expected)

    def test_mot_vide_ne_suffit_pas_a_declencher(self):
        """Régression corrigée : "qu'est-ce que" était détecté à 100% de
        couverture dans N'IMPORTE QUELLE phrase contenant juste "que" (mot
        grammatical omniprésent), déclenchant DEFINITION à tort."""
        result = ins.classify("Est-ce que tu peux m'aider avec mon exercice de vecteurs")
        self.assertNotEqual(result["intent"], ins.DEFINITION)

    def test_conversation_libre_reste_none(self):
        """Le repli flou ne doit jamais happer une conversation réellement
        libre (aucune intention pédagogique) vers une intention au hasard."""
        for text in ["Pourquoi le ciel est bleu", "Salut ça va", "Merci beaucoup pour ton aide"]:
            with self.subTest(text=text):
                self.assertEqual(ins.classify(text)["intent"], ins.NONE_INTENT)


class TestExempleNu(unittest.TestCase):
    """Audit global du routage pédagogique (2026-08-22) : "un exemple"/
    "encore un exemple" seuls (sans "donne-moi"/"montre-moi") restaient
    NONE_INTENT — l'instruction pédagogique spécifique EXEMPLE
    (pedagogy_templates) n'était alors jamais injectée."""

    def test_messages_nus_sont_bien_exemple(self):
        for text in ["un exemple", "Un exemple", "exemple", "exemples", "encore un exemple", "un autre exemple", "autre exemple"]:
            with self.subTest(text=text):
                self.assertEqual(ins.classify(text)["intent"], ins.EXEMPLE)

    def test_ne_casse_pas_la_formulation_avec_sujet_deja_couverte(self):
        """Non-régression : une demande d'exemple portant un vrai sujet
        (déjà couverte avant ce correctif) doit rester EXEMPLE."""
        result = ins.classify("Je voudrais un exemple sur les probabilités")
        self.assertEqual(result["intent"], ins.EXEMPLE)


class TestSimplifieNu(unittest.TestCase):
    """Chantier "reformulations successives" (2026-08-22) : "simplifie"/"plus
    simple" seuls restaient NONE_INTENT, cassant la chaîne de
    conversation_manager._detect_repeated_incomprehension (qui exige que le
    tour PRÉCÉDENT soit déjà classé REFORMULATION/RESTART_BASICS pour
    déclencher l'instruction "change réellement d'approche" au tour
    suivant — bug confirmé sur la séquence "simplifie" -> "explique plus
    simplement je n'ai rien compris")."""

    def test_simplifie_nu_est_reconnu_comme_reformulation(self):
        from chatbot import conversation_manager as cm

        for text in ["simplifie", "Simplifie.", "plus simple", "plus simple !"]:
            with self.subTest(text=text):
                self.assertEqual(ins.classify(text)["intent"], ins.REFORMULATION)
                self.assertIn(ins.REFORMULATION, cm._INCOMPREHENSION_INTENTS)

    def test_ne_capture_pas_simple_au_milieu_dune_phrase(self):
        """Garde-fou anti-sur-correction : "simple"/"simplifie" au milieu
        d'une phrase avec un vrai sujet ne doit jamais être reclassé
        REFORMULATION — seul le message NU (ancré ^...$) est concerné."""
        for text in ["j'aimerais un exercice plus simple", "un exemple plus simple stp", "donne-moi une méthode simple"]:
            with self.subTest(text=text):
                self.assertNotEqual(ins.classify(text)["intent"], ins.REFORMULATION)


if __name__ == "__main__":
    unittest.main()
