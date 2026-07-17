"""
Suite fonctionnelle de curriculum_stats.py : comptages réels contre les
banques présentes dans le projet (aucune valeur codée en dur dans les
assertions non plus — on recharge la banque nous-mêmes pour comparer),
dégradation propre pour une classe sans banque, mise en cache, et isolation
totale vis-à-vis de BANK/MODEL/chatbot (server.py n'est pas importé ici).
"""
import json
import unittest
from pathlib import Path

import curriculum_stats
from curriculum_registry import CURRICULUM_REGISTRY, CurriculumProfile


def _reference_counts(bank_path):
    bank = json.loads(bank_path.read_text(encoding="utf-8"))
    return {
        "totalExercises": len(bank),
        "chapters": len({e["chapter_id"] for e in bank if e.get("chapter_id")}),
        "notions": len({e["notion"] for e in bank if e.get("notion")}),
        "difficultyLevels": len({e["difficulty"] for e in bank if e.get("difficulty") is not None}),
        "exercisesWithSolution": sum(1 for e in bank if e.get("solution_steps")),
    }


class TestStatsSeconde(unittest.TestCase):
    """Seconde a une vraie banque déjà chargée en production — les compteurs
    doivent correspondre exactement à un recomptage indépendant du fichier."""

    def setUp(self):
        curriculum_stats.clear_cache()

    def test_compte_exactement_comme_un_recomptage_independant(self):
        profile = CURRICULUM_REGISTRY["seconde"]
        expected = _reference_counts(profile.exercise_bank)
        stats = curriculum_stats.compute_stats("seconde")
        for key, value in expected.items():
            with self.subTest(key=key):
                self.assertEqual(stats[key], value)

    def test_label_et_class_level_presents(self):
        stats = curriculum_stats.compute_stats("seconde")
        self.assertEqual(stats["classLevel"], "seconde")
        self.assertEqual(stats["label"], "Seconde")


class TestStatsPremiere(unittest.TestCase):
    """La banque Première existe déjà dans le projet (racine du dépôt) —
    utilisée telle quelle, jamais recréée ni modifiée par ce module."""

    def setUp(self):
        curriculum_stats.clear_cache()

    def test_compte_exactement_comme_un_recomptage_independant(self):
        profile = CURRICULUM_REGISTRY["premiere"]
        expected = _reference_counts(profile.exercise_bank)
        stats = curriculum_stats.compute_stats("premiere")
        for key, value in expected.items():
            with self.subTest(key=key):
                self.assertEqual(stats[key], value)
        # Preuve que ce n'est pas un test qui passerait trivialement avec des
        # banques vides : la banque Première contient bien des exercices.
        self.assertGreater(stats["totalExercises"], 0)


class TestListCurricula(unittest.TestCase):
    def setUp(self):
        curriculum_stats.clear_cache()

    def test_une_entree_par_profil_du_registre(self):
        curricula = curriculum_stats.list_curricula()
        self.assertEqual({c["classLevel"] for c in curricula}, set(CURRICULUM_REGISTRY.keys()))

    def test_extensible_sans_modification_du_module(self):
        """Ajouter un profil au registre (simulé ici, sans toucher au vrai
        registre) doit automatiquement apparaître dans list_curricula() sans
        qu'aucune ligne de curriculum_stats.py n'ait besoin de changer."""
        fake_bank = Path(__file__).resolve().parent / "_fixture_fake_bank.json"
        fake_bank.write_text(json.dumps([
            {"chapter_id": "Chapitre_1", "notion": "Alpha", "difficulty": 1, "solution_steps": ["a"]},
            {"chapter_id": "Chapitre_1", "notion": "Beta", "difficulty": 2, "solution_steps": ["a"]},
        ]), encoding="utf-8")
        try:
            fake_profile = CurriculumProfile(
                id="test_terminale", label="Terminale (test)", courses_dir=None,
                exercise_bank=fake_bank, natural_bank=fake_bank,
                program_file=None, models_dir=None, metadata_dir=None, assets_dir=None,
            )
            registry = dict(CURRICULUM_REGISTRY)
            registry["test_terminale"] = fake_profile
            import unittest.mock as mock
            with mock.patch("curriculum_stats.CURRICULUM_REGISTRY", registry):
                curriculum_stats.clear_cache()
                curricula = curriculum_stats.list_curricula()
            ids = {c["classLevel"] for c in curricula}
            self.assertIn("test_terminale", ids)
            fake_stats = next(c for c in curricula if c["classLevel"] == "test_terminale")
            self.assertEqual(fake_stats["totalExercises"], 2)
            self.assertEqual(fake_stats["chapters"], 1)
            self.assertEqual(fake_stats["notions"], 2)
        finally:
            fake_bank.unlink(missing_ok=True)
            curriculum_stats.clear_cache()


class TestDegradationPropre(unittest.TestCase):
    """Une classe déclarée sans banque disponible ne doit jamais lever
    d'exception — compteurs à zéro, comme le reste du projet (voir
    canonical_ids.py, même principe pour Première tant que son crosswalk
    n'existe pas)."""

    def setUp(self):
        curriculum_stats.clear_cache()

    def test_classe_sans_fichier_de_banque_renvoie_des_zeros(self):
        fake_profile = CurriculumProfile(
            id="test_vide", label="Classe vide (test)", courses_dir=None,
            exercise_bank=Path("chemin/qui/nexiste/pas.json"), natural_bank=Path("chemin/qui/nexiste/pas.json"),
            program_file=None, models_dir=None, metadata_dir=None, assets_dir=None,
        )
        registry = dict(CURRICULUM_REGISTRY)
        registry["test_vide"] = fake_profile
        import unittest.mock as mock
        with mock.patch("curriculum_stats.CURRICULUM_REGISTRY", registry):
            stats = curriculum_stats.compute_stats("test_vide")
        self.assertEqual(stats["totalExercises"], 0)
        self.assertEqual(stats["chapters"], 0)
        self.assertEqual(stats["notions"], 0)
        self.assertEqual(stats["difficultyLevels"], 0)
        self.assertEqual(stats["exercisesWithSolution"], 0)


class TestCache(unittest.TestCase):
    def setUp(self):
        curriculum_stats.clear_cache()

    def test_deuxieme_appel_ne_relit_pas_le_fichier(self):
        calls = []
        original = curriculum_stats._load_bank

        def spy(path):
            calls.append(path)
            return original(path)

        curriculum_stats._load_bank = spy
        try:
            curriculum_stats.compute_stats("seconde")
            curriculum_stats.compute_stats("seconde")
        finally:
            curriculum_stats._load_bank = original
        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
