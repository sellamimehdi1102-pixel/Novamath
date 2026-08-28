"""
Suite fonctionnelle du registre central des programmes scolaires
(curriculum_registry.py) : présence des deux profils actuels (Seconde,
Première), exactitude des chemins déclarés vers des fichiers déjà existants
dans le projet, représentation explicite des ressources encore absentes pour
Première, unicité garantie des identifiants, et indépendance totale du
module vis-à-vis du reste du projet.

Aucun de ces tests n'importe ni ne modifie server.py, auth.py, db.py,
canonical_ids.py ou le chatbot : ce module est encore inutilisé par le
pipeline existant, donc ces tests ne peuvent pas provoquer de régression.
"""
import unittest
from pathlib import Path

import curriculum_registry
from curriculum_registry import (
    CURRICULUM_REGISTRY,
    CurriculumIntegrityError,
    CurriculumProfile,
    build_registry,
    validate_registry,
)


class TestRegistryContent(unittest.TestCase):
    def test_deux_profils_presents(self):
        self.assertEqual(set(CURRICULUM_REGISTRY.keys()), {"seconde", "premiere", "troisieme"})

    def test_labels_affichage(self):
        self.assertEqual(CURRICULUM_REGISTRY["seconde"].label, "Seconde")
        self.assertEqual(CURRICULUM_REGISTRY["premiere"].label, "Première spécialité Mathématiques")
        self.assertEqual(CURRICULUM_REGISTRY["troisieme"].label, "Troisième")

    def test_registre_immuable(self):
        with self.assertRaises(TypeError):
            CURRICULUM_REGISTRY["terminale"] = None  # type: ignore[index]


class TestCheminsSeconde(unittest.TestCase):
    """Seconde est le programme déjà en production : chaque chemin déclaré
    doit pointer vers un fichier/dossier réellement présent, sans qu'aucun
    de ces fichiers n'ait été créé ni modifié par cette étape."""

    def setUp(self):
        self.profile = CURRICULUM_REGISTRY["seconde"]

    def test_courses_dir_existe(self):
        self.assertTrue(self.profile.courses_dir.is_dir())
        self.assertTrue((self.profile.courses_dir / "chapitre_1.json").is_file())

    def test_exercise_bank_existe(self):
        self.assertTrue(self.profile.exercise_bank.is_file())
        self.assertEqual(self.profile.exercise_bank.name, "exercises_bank.json")

    def test_natural_bank_existe(self):
        self.assertTrue(self.profile.natural_bank.is_file())
        self.assertEqual(self.profile.natural_bank.name, "exercises_bank_natural.json")

    def test_program_file_existe(self):
        self.assertTrue(self.profile.program_file.is_file())
        self.assertEqual(self.profile.program_file.name, "Programme AI.json")

    def test_models_dir_existe(self):
        self.assertTrue(self.profile.models_dir.is_dir())
        self.assertTrue((self.profile.models_dir / "level_predictor.pkl").is_file())

    def test_metadata_dir_existe(self):
        self.assertTrue(self.profile.metadata_dir.is_dir())
        self.assertTrue((self.profile.metadata_dir / "topic_crosswalk.json").is_file())


class TestCheminsPremiere(unittest.TestCase):
    """Première : les banques d'exercices déjà présentes dans le projet
    doivent être déclarées telles quelles (jamais recréées ni modifiées) ;
    les ressources qui n'existent pas encore doivent être explicitement
    None, pas un chemin inventé."""

    def setUp(self):
        self.profile = CURRICULUM_REGISTRY["premiere"]

    def test_exercise_bank_existe_et_non_modifiee(self):
        self.assertTrue(self.profile.exercise_bank.is_file())
        self.assertEqual(self.profile.exercise_bank.name, "exercises_bank_premiere.json")

    def test_natural_bank_existe_et_non_modifiee(self):
        self.assertTrue(self.profile.natural_bank.is_file())
        self.assertEqual(self.profile.natural_bank.name, "exercises_bank_premiere_natural.json")

    def test_courses_dir_genere_depuis_la_banque_existe(self):
        """Généré par generate_cours_from_bank.py à partir de exercise_bank
        (jamais recopié de Seconde) — même schéma, dossier distinct."""
        self.assertTrue(self.profile.courses_dir.is_dir())
        self.assertNotEqual(self.profile.courses_dir, CURRICULUM_REGISTRY["seconde"].courses_dir)
        self.assertTrue((self.profile.courses_dir / "chapitre_1.json").is_file())

    def test_ressources_absentes_sont_explicitement_none(self):
        self.assertIsNone(self.profile.program_file)
        self.assertIsNone(self.profile.models_dir)
        self.assertIsNone(self.profile.metadata_dir)
        self.assertIsNone(self.profile.assets_dir)


class TestCheminsTroisieme(unittest.TestCase):
    """Troisième : mêmes garanties que Première — banques existantes
    déclarées telles quelles, ressources absentes explicitement None."""

    def setUp(self):
        self.profile = CURRICULUM_REGISTRY["troisieme"]

    def test_exercise_bank_existe_et_non_modifiee(self):
        self.assertTrue(self.profile.exercise_bank.is_file())
        self.assertEqual(self.profile.exercise_bank.name, "exercises_bank_troisieme.json")

    def test_natural_bank_existe_et_non_modifiee(self):
        self.assertTrue(self.profile.natural_bank.is_file())
        self.assertEqual(self.profile.natural_bank.name, "exercises_bank_troisieme_natural.json")

    def test_courses_dir_genere_depuis_la_banque_existe(self):
        """Généré par generate_cours_from_bank.py à partir de exercise_bank
        (jamais recopié de Seconde/Première) — même schéma, dossier distinct."""
        self.assertTrue(self.profile.courses_dir.is_dir())
        self.assertNotEqual(self.profile.courses_dir, CURRICULUM_REGISTRY["seconde"].courses_dir)
        self.assertNotEqual(self.profile.courses_dir, CURRICULUM_REGISTRY["premiere"].courses_dir)
        self.assertTrue((self.profile.courses_dir / "chapitre_1.json").is_file())

    def test_ressources_absentes_sont_explicitement_none(self):
        self.assertIsNone(self.profile.program_file)
        self.assertIsNone(self.profile.models_dir)
        self.assertIsNone(self.profile.metadata_dir)
        self.assertIsNone(self.profile.assets_dir)


class TestValidationRegistreGenerique(unittest.TestCase):
    """Régression "troisieme" : un profil ajouté à _PROFILES avec un
    courses_dir déclaré, mais dont le contenu n'a jamais été généré, doit
    être détecté automatiquement — pour CHAQUE programme, présent ou futur,
    sans dupliquer une classe de test par classe scolaire (voir
    TestCheminsSeconde/Premiere/Troisieme ci-dessus, qui restent en plus de
    celle-ci pour les assertions fines par programme)."""

    def test_chaque_profil_avec_courses_dir_a_du_contenu_genere(self):
        for profile in CURRICULUM_REGISTRY.values():
            if profile.courses_dir is None:
                continue
            with self.subTest(profile=profile.id):
                self.assertTrue(
                    profile.courses_dir.is_dir(),
                    f"{profile.id!r} : courses_dir introuvable — {profile.courses_dir}",
                )
                chapitres = sorted(profile.courses_dir.glob("chapitre_*.json"))
                self.assertGreater(
                    len(chapitres), 0,
                    f"{profile.id!r} : courses_dir vide (aucun chapitre_*.json) — {profile.courses_dir}",
                )

    def test_registre_reel_passe_validate_registry(self):
        # Ne doit lever aucune exception : c'est exactement ce que
        # server.py appelle au démarrage et `npm run validate:curricula`
        # au build (voir curriculum_registry.py::validate_registry).
        validate_registry()

    def test_validate_registry_detecte_un_dossier_absent(self):
        casse = build_registry((
            CurriculumProfile(
                id="fantome", label="Fantôme",
                courses_dir=Path("/chemin/qui/n_existe_pas"),
                exercise_bank=Path("dummy_bank.json"), natural_bank=Path("dummy_natural.json"),
                program_file=None, models_dir=None, metadata_dir=None, assets_dir=None,
            ),
        ))
        with self.assertRaises(CurriculumIntegrityError) as ctx:
            validate_registry(casse)
        self.assertIn("fantome", str(ctx.exception))

    def test_validate_registry_detecte_un_dossier_vide(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            casse = build_registry((
                CurriculumProfile(
                    id="vide", label="Vide",
                    courses_dir=Path(tmp),
                    exercise_bank=Path("dummy_bank.json"), natural_bank=Path("dummy_natural.json"),
                    program_file=None, models_dir=None, metadata_dir=None, assets_dir=None,
                ),
            ))
            with self.assertRaises(CurriculumIntegrityError) as ctx:
                validate_registry(casse)
            self.assertIn("vide", str(ctx.exception))

    def test_validate_registry_ignore_courses_dir_none(self):
        # Un profil sans courses_dir (None explicite) n'est pas une erreur —
        # c'est une ressource assumée comme absente, pas un état incohérent.
        casse = build_registry((
            CurriculumProfile(
                id="sans_cours", label="Sans cours",
                courses_dir=None,
                exercise_bank=Path("dummy_bank.json"), natural_bank=Path("dummy_natural.json"),
                program_file=None, models_dir=None, metadata_dir=None, assets_dir=None,
            ),
        ))
        validate_registry(casse)  # ne doit pas lever


class TestUniciteIdentifiants(unittest.TestCase):
    """Point explicitement demandé : deux profils ne peuvent jamais partager
    le même `id`, garanti dès la construction du registre."""

    def _make_profile(self, profile_id):
        return CurriculumProfile(
            id=profile_id,
            label="Profil de test",
            courses_dir=None,
            exercise_bank=Path("dummy_bank.json"),
            natural_bank=Path("dummy_natural.json"),
            program_file=None,
            models_dir=None,
            metadata_dir=None,
            assets_dir=None,
        )

    def test_construction_normale_ok(self):
        registry = build_registry((self._make_profile("a"), self._make_profile("b")))
        self.assertEqual(set(registry.keys()), {"a", "b"})

    def test_doublon_leve_une_erreur(self):
        with self.assertRaises(ValueError):
            build_registry((self._make_profile("seconde"), self._make_profile("seconde")))

    def test_registre_reel_ne_contient_aucun_doublon(self):
        # Reconstruit le registre réel via build_registry pour s'assurer que
        # les profils actuels de _PROFILES ne violent pas la contrainte.
        registry = build_registry(curriculum_registry._PROFILES)
        self.assertEqual(len(registry), len(curriculum_registry._PROFILES))


class TestIndependance(unittest.TestCase):
    """Le module ne doit dépendre d'aucun autre composant du projet."""

    def test_aucun_import_projet(self):
        source = Path(curriculum_registry.__file__).read_text(encoding="utf-8")
        interdits = ["import server", "import auth", "import db", "import canonical_ids", "chatbot"]
        for terme in interdits:
            with self.subTest(terme=terme):
                self.assertNotIn(terme, source)


if __name__ == "__main__":
    unittest.main()
