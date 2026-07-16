"""
Suite fonctionnelle du système d'identifiants canoniques (canonical_ids.py) :
fautes de frappe, synonymes, formulations, pluriels/singuliers, accents
absents, casse différente, espaces inutiles, noms incomplets, et le cas
ambigu multi-chapitres ("Condition de colinéarité", Chapitre_4 vs Chapitre_5).

Chaque cas a été vérifié manuellement (exploration interactive) avant d'être
figé ici en assertion — aucun résultat attendu n'est inventé.
"""
import unittest

import canonical_ids


class TestResolveChapterId(unittest.TestCase):
    def test_forme_canonique(self):
        self.assertEqual(canonical_ids.resolve_chapter_id("Chapitre_1"), "Chapitre_1")

    def test_variantes_de_saisie(self):
        cases = ["chapitre 1", "Chapitre_01", "CHAPITRE 1", " Chapitre_2 ", 3, "4"]
        expected = ["Chapitre_1", "Chapitre_1", "Chapitre_1", "Chapitre_2", "Chapitre_3", "Chapitre_4"]
        for raw, exp in zip(cases, expected):
            with self.subTest(raw=raw):
                self.assertEqual(canonical_ids.resolve_chapter_id(raw), exp)

    def test_valeurs_non_reconnaissables(self):
        for raw in [None, "", "chap_5", "xyz"]:
            with self.subTest(raw=raw):
                self.assertIsNone(canonical_ids.resolve_chapter_id(raw))


class TestResolveTopicIdExact(unittest.TestCase):
    """Lookup exact (crosswalk) — doit être fiable à 100% sur un texte connu."""

    def test_texte_exact(self):
        self.assertEqual(
            canonical_ids.resolve_topic_id("Puissances entières relatives", chapter_id="Chapitre_1"),
            "puissances-entieres-relatives",
        )

    def test_casse_differente(self):
        self.assertEqual(
            canonical_ids.resolve_topic_id("PUISSANCES ENTIÈRES RELATIVES", chapter_id="Chapitre_1"),
            "puissances-entieres-relatives",
        )

    def test_accents_absents(self):
        self.assertEqual(
            canonical_ids.resolve_topic_id("Puissances entieres relatives", chapter_id="Chapitre_1"),
            "puissances-entieres-relatives",
        )

    def test_espaces_inutiles(self):
        self.assertEqual(
            canonical_ids.resolve_topic_id("  Puissances   entières   relatives  ", chapter_id="Chapitre_1"),
            "puissances-entieres-relatives",
        )


class TestResolveTopicIdFuzzy(unittest.TestCase):
    """Repli flou (difflib) — texte jamais répertorié tel quel dans la
    crosswalk : synonymes, fautes de frappe, formulations d'élève, noms
    incomplets, singulier/pluriel."""

    def test_faute_de_frappe(self):
        self.assertEqual(
            canonical_ids.resolve_topic_id("puissance entiere relatve", chapter_id="Chapitre_1"),
            "puissances-entieres-relatives",
        )

    def test_singulier_pluriel(self):
        self.assertEqual(
            canonical_ids.resolve_topic_id("puissance entière relative", chapter_id="Chapitre_1"),
            "puissances-entieres-relatives",
        )
        self.assertEqual(
            canonical_ids.resolve_topic_id("ensembles de nombre", chapter_id="Chapitre_1"),
            "ensembles-de-nombres",
        )

    def test_nom_incomplet(self):
        self.assertEqual(
            canonical_ids.resolve_topic_id("puissances", chapter_id="Chapitre_1"),
            "puissances-entieres-relatives",
        )
        self.assertEqual(
            canonical_ids.resolve_topic_id("racine carree", chapter_id="Chapitre_1"),
            "racine-carree",
        )

    def test_formulation_naturelle_avec_article(self):
        self.assertEqual(
            canonical_ids.resolve_topic_id("les puissances", chapter_id="Chapitre_1"),
            "puissances-entieres-relatives",
        )

    def test_exemples_explicites_du_cahier_des_charges(self):
        """"Les valeurs absolues" / "Valeur absolue" / "les valeurs absolues" /
        "Chapitre Valeurs Absolues" doivent tous pointer vers le même topic_id."""
        variantes = [
            "Les valeurs absolues",
            "Valeur absolue",
            "Valeurs absolues",
            "les valeurs absolues",
            "Chapitre Valeurs Absolues",
        ]
        for texte in variantes:
            with self.subTest(texte=texte):
                self.assertEqual(
                    canonical_ids.resolve_topic_id(texte, chapter_id="Chapitre_2"),
                    "valeur-absolue-dun-nombre-reel",
                )

    def test_texte_hors_sujet_ne_matche_rien(self):
        """Un texte sans rapport ne doit jamais halluciner un topic_id."""
        self.assertIsNone(canonical_ids.resolve_topic_id("xyz totalement hors sujet", chapter_id="Chapitre_1"))


class TestAmbiguiteInterChapitre(unittest.TestCase):
    """"Condition de colinéarité" existe, texte identique, en Chapitre_4 ET
    Chapitre_5 (deux notions réellement différentes). Avec chapter_id
    (toujours disponible dans notre câblage réel — historique, mentions,
    recherche scopée), la résolution est garantie correcte."""

    def test_scope_chapitre_4(self):
        self.assertEqual(
            canonical_ids.resolve_topic_id("Condition de colinéarité", chapter_id="Chapitre_4"),
            "condition-de-colinearite",
        )

    def test_scope_chapitre_5(self):
        self.assertEqual(
            canonical_ids.resolve_topic_id("Condition de colinéarité", chapter_id="Chapitre_5"),
            "condition-de-colinearite-repere",
        )

    def test_sans_scope_comportement_documente(self):
        """Limitation connue et attendue : SANS chapter_id, un texte ambigu
        entre deux chapitres n'a aucun signal pour trancher — le résolveur
        renvoie de façon déterministe la première correspondance trouvée
        (ordre d'insertion de topic_crosswalk.json, donc Chapitre_4 avant
        Chapitre_5). Ce n'est PAS un défaut à corriger : aucun algorithme ne
        peut deviner le bon chapitre sans indice supplémentaire. C'est
        pourquoi chaque appelant réel (context_builder, mentions_service,
        search_service) passe TOUJOURS un chapter_id quand il en a un."""
        result = canonical_ids.resolve_topic_id("condition de colinéarité")
        self.assertEqual(result, "condition-de-colinearite")


if __name__ == "__main__":
    unittest.main()
