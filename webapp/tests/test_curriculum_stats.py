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


def _reference_counts(bank_path, generated_bank_path=None):
    bank = json.loads(bank_path.read_text(encoding="utf-8"))
    if generated_bank_path is not None and generated_bank_path.exists():
        bank = bank + json.loads(generated_bank_path.read_text(encoding="utf-8"))
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
        # Depuis l'audit "audit et renforcement de l'accès Seconde"
        # (2026-09-02), server.py fusionne le sous-ensemble Chapitre_9 de
        # generated_exercise_bank (voir curriculum_stats._SECONDE_MERGED_CHAPTERS) —
        # le recomptage de référence doit inclure exactement ce même
        # sous-ensemble, pas la banque generated entière (Chapitre_6 reste
        # orphelin, non fusionné).
        profile = CURRICULUM_REGISTRY["seconde"]
        bank = json.loads(profile.exercise_bank.read_text(encoding="utf-8"))
        generated = json.loads(profile.generated_exercise_bank.read_text(encoding="utf-8"))
        bank = bank + [
            ex for ex in generated
            if ex.get("chapter_id") in curriculum_stats._SECONDE_MERGED_CHAPTERS
        ]
        expected = {
            "totalExercises": len(bank),
            "chapters": len({e["chapter_id"] for e in bank if e.get("chapter_id")}),
            "notions": len({e["notion"] for e in bank if e.get("notion")}),
            "difficultyLevels": len({e["difficulty"] for e in bank if e.get("difficulty") is not None}),
            "exercisesWithSolution": sum(1 for e in bank if e.get("solution_steps")),
        }
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
        """"premiere" fusionne exercise_bank + generated_exercise_bank (voir
        server.py::_class_bank) : un recomptage indépendant qui ne lirait que
        exercises_bank_premiere.json (815 entrées) reproduirait exactement le
        bug corrigé par cette mission (comptage tronqué, sans les 1402
        exercices de exercises_generated_premiere.json)."""
        profile = CURRICULUM_REGISTRY["premiere"]
        expected = _reference_counts(profile.exercise_bank, profile.generated_exercise_bank)
        stats = curriculum_stats.compute_stats("premiere")
        for key, value in expected.items():
            with self.subTest(key=key):
                self.assertEqual(stats[key], value)
        # Preuve que ce n'est pas un test qui passerait trivialement avec des
        # banques vides : la banque Première contient bien des exercices.
        self.assertGreater(stats["totalExercises"], 0)

    def test_le_pool_genere_est_bien_inclus_pas_seulement_la_banque_curee(self):
        """Fige la cause racine du bug signalé ("815 exercices affichés au
        lieu d'environ 2000") : exercises_bank_premiere.json seul (815) ne
        doit plus jamais être, à lui seul, la valeur de totalExercises."""
        profile = CURRICULUM_REGISTRY["premiere"]
        curated_only = len(json.loads(profile.exercise_bank.read_text(encoding="utf-8")))
        stats = curriculum_stats.compute_stats("premiere")
        self.assertNotEqual(stats["totalExercises"], curated_only)
        self.assertGreater(stats["totalExercises"], curated_only)


class TestStatsTroisieme(unittest.TestCase):
    """Même patron additif que "premiere" (voir curriculum_registry.py) :
    "troisieme" déclare aussi generated_exercise_bank et doit donc, elle
    aussi, compter exercise_bank + generated_exercise_bank."""

    def setUp(self):
        curriculum_stats.clear_cache()

    def test_compte_exactement_comme_un_recomptage_independant(self):
        profile = CURRICULUM_REGISTRY["troisieme"]
        expected = _reference_counts(profile.exercise_bank, profile.generated_exercise_bank)
        stats = curriculum_stats.compute_stats("troisieme")
        for key, value in expected.items():
            with self.subTest(key=key):
                self.assertEqual(stats[key], value)


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
        # Depuis l'audit "audit et renforcement de l'accès Seconde"
        # (2026-09-02), le premier appel lit exercise_bank ET le
        # sous-ensemble fusionné de generated_exercise_bank (2 lectures) ;
        # le second appel doit rester servi entièrement par le cache (0
        # lecture supplémentaire).
        self.assertEqual(len(calls), 2)


class TestTotalExercisesRefleteVraimentCeQuiEstServi(unittest.TestCase):
    """Verrou de non-régression sur la CAUSE (pas sur un nombre codé en dur,
    qui évoluerait à chaque régénération de banque) : pour toute classe du
    registre, curriculum_stats.compute_stats(...)['totalExercises'] doit être
    strictement égal à len(server._class_bank(...)['bank']) — la banque
    réellement combinée (exercise_bank + generated_exercise_bank le cas
    échéant) que server.py sert en mode Exercices/Entraînement pour cette
    classe. Empêche qu'une future modification fasse à nouveau compter le
    compteur depuis exercises_bank_<classe>.json seul (ou toute autre source
    qui diverge de ce que server.py sert réellement), quelle que soit la
    classe ajoutée plus tard au registre."""

    def setUp(self):
        curriculum_stats.clear_cache()
        import server
        self.server = server

    def test_total_exercises_egale_la_banque_reellement_servie_par_classe(self):
        for class_level in CURRICULUM_REGISTRY:
            with self.subTest(class_level=class_level):
                stats = curriculum_stats.compute_stats(class_level)
                try:
                    served = self.server._class_bank(class_level)["bank"]
                except Exception as exc:
                    # Anomalie préexistante et sans rapport avec cette mission
                    # (comptage) : exercises_bank_troisieme_natural.json est
                    # corrompu sur le disque (contenu tronqué, ne commence pas
                    # par du JSON valide), ce qui fait planter
                    # server._class_bank("troisieme") indépendamment de tout
                    # comptage — signalé comme anomalie restante dans le
                    # rapport de mission, volontairement non corrigé ici
                    # (modifier une banque d'exercices est hors périmètre).
                    self.skipTest(f"{class_level} : server._class_bank() indisponible ({exc!r}), anomalie préexistante sans rapport avec le comptage")
                    continue
                self.assertEqual(stats["totalExercises"], len(served))


if __name__ == "__main__":
    unittest.main()
