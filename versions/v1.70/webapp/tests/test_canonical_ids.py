"""
Suite fonctionnelle du système d'identifiants canoniques (canonical_ids.py) :
fautes de frappe, synonymes, formulations, pluriels/singuliers, accents
absents, casse différente, espaces inutiles, noms incomplets, et le cas
ambigu multi-chapitres ("Condition de colinéarité", Chapitre_4 vs Chapitre_5).

Chaque cas a été vérifié manuellement (exploration interactive) avant d'être
figé ici en assertion — aucun résultat attendu n'est inventé.

TestMultiClasse* (fin de fichier) : suite dédiée à l'étape 3 (branchement de
canonical_ids.py sur curriculum_registry.py) — isolation des caches par
class_level, comportement par défaut inchangé, dégradation propre pour une
classe sans données. Tous les tests ci-dessus restent inchangés et continuent
de passer sans class_level, preuve de non-régression de la Seconde réelle.
"""
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import canonical_ids
from curriculum_registry import CurriculumProfile


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


class TestMultiClasseDefautInchange(unittest.TestCase):
    """Preuve explicite de non-régression : ne pas fournir class_level, le
    fournir à None, ou le fournir explicitement à "seconde" doivent toujours
    produire exactement le même résultat que le comportement historique."""

    def test_omission_none_et_seconde_explicite_sont_equivalents(self):
        sans_arg = canonical_ids.resolve_topic_id("Puissances entières relatives", chapter_id="Chapitre_1")
        avec_none = canonical_ids.resolve_topic_id(
            "Puissances entières relatives", chapter_id="Chapitre_1", class_level=None,
        )
        avec_seconde = canonical_ids.resolve_topic_id(
            "Puissances entières relatives", chapter_id="Chapitre_1", class_level="seconde",
        )
        self.assertEqual(sans_arg, "puissances-entieres-relatives")
        self.assertEqual(sans_arg, avec_none)
        self.assertEqual(sans_arg, avec_seconde)

    def test_resolve_chapter_id_ignore_class_level_sans_planter(self):
        self.assertEqual(canonical_ids.resolve_chapter_id("Chapitre_1", class_level="seconde"), "Chapitre_1")
        self.assertEqual(canonical_ids.resolve_chapter_id("Chapitre_1", class_level="premiere"), "Chapitre_1")
        self.assertEqual(
            canonical_ids.resolve_chapter_id("Chapitre_1"),
            canonical_ids.resolve_chapter_id("Chapitre_1", class_level="seconde"),
        )

    def test_get_topic_title_et_synonyms_identiques_avec_ou_sans_class_level(self):
        titre_defaut = canonical_ids.get_topic_title("Chapitre_1", "puissances-entieres-relatives")
        titre_seconde = canonical_ids.get_topic_title("Chapitre_1", "puissances-entieres-relatives", class_level="seconde")
        self.assertEqual(titre_defaut, titre_seconde)

        syn_defaut = canonical_ids.synonyms_for_topic("Chapitre_1", "puissances-entieres-relatives")
        syn_seconde = canonical_ids.synonyms_for_topic("Chapitre_1", "puissances-entieres-relatives", class_level="seconde")
        self.assertEqual(syn_defaut, syn_seconde)
        self.assertTrue(len(syn_defaut) > 0)


class TestPremiereDegradationPropre(unittest.TestCase):
    """Première est un class_level déjà déclaré dans curriculum_registry.
    courses_dir est désormais généré depuis exercise_bank (voir
    generate_cours_from_bank.py) — resolve_topic_id() y trouve donc un repli
    flou (_load_topics_by_chapter lit courses_dir directement). metadata_dir
    (topic_crosswalk.json) reste None : le lookup EXACT/synonymes doit donc
    toujours dégrader silencieusement vers "rien trouvé", jamais lever
    d'exception."""

    def test_resolve_topic_id_trouve_un_repli_flou_depuis_les_cours_generes(self):
        self.assertEqual(
            canonical_ids.resolve_topic_id("Généralités sur les suites", chapter_id="Chapitre_1", class_level="premiere"),
            "generalites-sur-les-suites",
        )

    def test_resolve_topic_id_texte_hors_sujet_renvoie_none(self):
        self.assertIsNone(
            canonical_ids.resolve_topic_id("xyzzyfoobarqux", chapter_id="Chapitre_1", class_level="premiere"),
        )

    def test_get_topic_title_renvoie_none(self):
        self.assertIsNone(canonical_ids.get_topic_title("Chapitre_1", "quoi-que-ce-soit", class_level="premiere"))

    def test_synonyms_renvoie_liste_vide(self):
        self.assertEqual(canonical_ids.synonyms_for_topic("Chapitre_1", "quoi-que-ce-soit", class_level="premiere"), [])

    def test_classe_totalement_inconnue_leve_key_error(self):
        """Différent d'une classe connue sans données : un identifiant de
        classe qui n'existe même pas dans le registre est une erreur de
        programmation, volontairement non avalée (voir docstring de
        _profile_for)."""
        with self.assertRaises(KeyError):
            canonical_ids.resolve_topic_id("texte", chapter_id="Chapitre_1", class_level="terminale")


class TestMultiClasseAucuneCollision(unittest.TestCase):
    """Preuve directe qu'un même chapter_id ("Chapitre_1") et un même texte
    libre ("Alpha") résolvent vers des topic_id complètement différents
    selon la classe, sans jamais se mélanger — exactement le scénario de
    collision identifié dans l'audit (exercises_bank.json et
    exercises_bank_premiere.json partagent la nomenclature "Chapitre_N").
    Utilise deux classes SYNTHÉTIQUES (pas Seconde/Première réelles :
    Première n'a pas encore de cours/crosswalk à ce stade) pour isoler
    précisément ce comportement, sans dépendre de données réelles absentes."""

    @classmethod
    def setUpClass(cls):
        cls.tmp_a = Path(tempfile.mkdtemp())
        cls.tmp_b = Path(tempfile.mkdtemp())
        for tmp, topic_id, title in ((cls.tmp_a, "alpha-id", "Titre A"), (cls.tmp_b, "beta-id", "Titre B")):
            (tmp / "cours").mkdir()
            (tmp / "topic_crosswalk.json").write_text(
                json.dumps({"Chapitre_1": {"Alpha": topic_id}}), encoding="utf-8",
            )
            (tmp / "cours" / "chapitre_1.json").write_text(
                json.dumps({"chapterId": "Chapitre_1", "notions": [{"id": topic_id, "title": title}]}),
                encoding="utf-8",
            )
        cls.profile_a = CurriculumProfile(
            id="test_classe_a", label="Classe A", courses_dir=cls.tmp_a / "cours",
            exercise_bank=cls.tmp_a / "bank.json", natural_bank=cls.tmp_a / "natural.json",
            program_file=None, models_dir=None, metadata_dir=cls.tmp_a, assets_dir=None,
        )
        cls.profile_b = CurriculumProfile(
            id="test_classe_b", label="Classe B", courses_dir=cls.tmp_b / "cours",
            exercise_bank=cls.tmp_b / "bank.json", natural_bank=cls.tmp_b / "natural.json",
            program_file=None, models_dir=None, metadata_dir=cls.tmp_b, assets_dir=None,
        )

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp_a, ignore_errors=True)
        shutil.rmtree(cls.tmp_b, ignore_errors=True)

    def setUp(self):
        profiles = {"test_classe_a": self.profile_a, "test_classe_b": self.profile_b}
        self._patcher = patch("canonical_ids._profile_for", side_effect=lambda cl: profiles[cl])
        self._patcher.start()
        for cache in (canonical_ids._crosswalk_by_class, canonical_ids._crosswalk_raw_by_class,
                      canonical_ids._topics_by_chapter_by_class):
            cache.pop("test_classe_a", None)
            cache.pop("test_classe_b", None)

    def tearDown(self):
        self._patcher.stop()

    def test_meme_texte_meme_chapitre_resout_differemment_selon_la_classe(self):
        topic_a = canonical_ids.resolve_topic_id("Alpha", chapter_id="Chapitre_1", class_level="test_classe_a")
        topic_b = canonical_ids.resolve_topic_id("Alpha", chapter_id="Chapitre_1", class_level="test_classe_b")
        self.assertEqual(topic_a, "alpha-id")
        self.assertEqual(topic_b, "beta-id")
        self.assertNotEqual(topic_a, topic_b)

    def test_titres_ne_se_melangent_pas(self):
        self.assertEqual(canonical_ids.get_topic_title("Chapitre_1", "alpha-id", class_level="test_classe_a"), "Titre A")
        self.assertEqual(canonical_ids.get_topic_title("Chapitre_1", "beta-id", class_level="test_classe_b"), "Titre B")
        self.assertIsNone(canonical_ids.get_topic_title("Chapitre_1", "alpha-id", class_level="test_classe_b"))
        self.assertIsNone(canonical_ids.get_topic_title("Chapitre_1", "beta-id", class_level="test_classe_a"))

    def test_caches_isoles_par_classe(self):
        canonical_ids.resolve_topic_id("Alpha", chapter_id="Chapitre_1", class_level="test_classe_a")
        canonical_ids.resolve_topic_id("Alpha", chapter_id="Chapitre_1", class_level="test_classe_b")
        self.assertIn("test_classe_a", canonical_ids._crosswalk_by_class)
        self.assertIn("test_classe_b", canonical_ids._crosswalk_by_class)
        self.assertNotEqual(
            canonical_ids._crosswalk_by_class["test_classe_a"],
            canonical_ids._crosswalk_by_class["test_classe_b"],
        )


if __name__ == "__main__":
    unittest.main()
