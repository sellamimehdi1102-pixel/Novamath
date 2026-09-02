"""Tests des 8 nouveaux générateurs créés par la mission "audit final et
rééquilibrage additif global" (2026-09-02) pour les chapitres qui n'avaient
AUCUN générateur auparavant :

- Troisième : geometrie_transformations (Chapitre_11), geometrie_triangles
  (Chapitre_12), pythagore_trigonometrie (Chapitre_13).
- Seconde : nombres_seconde (Chapitre_1), calcul_litteral_seconde
  (Chapitre_3), vecteurs_sans_repere (Chapitre_4), variations_seconde
  (Chapitre_8), statistiques_seconde (Chapitre_11).

Ces tests sont volontairement DYNAMIQUES (jamais de nombre codé en dur pour
un chapitre donné) : ils vérifient la forme et la cohérence de ce qui est
RÉELLEMENT produit, pas une valeur figée.
"""
import importlib
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
WEBAPP = ROOT / "webapp"
if str(WEBAPP) not in sys.path:
    sys.path.insert(0, str(WEBAPP))

from curriculum_registry import CURRICULUM_REGISTRY  # noqa: E402

_NOUVEAUX_MODULES = [
    ("exercise_generator_troisieme", "geometrie_transformations", "troisieme"),
    ("exercise_generator_troisieme", "geometrie_triangles", "troisieme"),
    ("exercise_generator_troisieme", "pythagore_trigonometrie", "troisieme"),
    ("exercise_generator_seconde", "nombres_seconde", "seconde"),
    ("exercise_generator_seconde", "calcul_litteral_seconde", "seconde"),
    ("exercise_generator_seconde", "vecteurs_sans_repere", "seconde"),
    ("exercise_generator_seconde", "variations_seconde", "seconde"),
    ("exercise_generator_seconde", "statistiques_seconde", "seconde"),
    # Mission "porter à 300 exercices minimum par chapitre + diversité
    # mathématique réelle" (2026-09-02) : Seconde Chapitre_2/7/12 restaient
    # purement curés (aucun générateur) — 3 nouveaux modules.
    ("exercise_generator_seconde", "intervalles_seconde", "seconde"),
    ("exercise_generator_seconde", "fonctions_generalites_seconde", "seconde"),
    ("exercise_generator_seconde", "probabilites_seconde", "seconde"),
]


def _import_module(package: str, name: str):
    return importlib.import_module(f"{package}.{name}")


class TestNouveauxGenerateursProduisentDuContenuValide(unittest.TestCase):
    def test_generate_pool_produit_des_exercices_bien_formes(self):
        for package, name, class_level in _NOUVEAUX_MODULES:
            module = _import_module(package, name)
            with self.subTest(module=name):
                pool = module.generate_pool()
                self.assertTrue(pool, f"{name} : generate_pool() ne produit aucun exercice")
                for ex in pool:
                    self.assertEqual(ex["chapter_id"], module.CHAPTER_ID)
                    self.assertTrue(ex.get("enonce"))
                    self.assertTrue(ex.get("answer"))
                    self.assertTrue(ex.get("hint"))
                    self.assertTrue(ex.get("solution_steps"))
                    self.assertIn(ex.get("difficulty"), (1, 2, 3, 4, 5))
                    self.assertTrue(ex.get("notion"))
                    self.assertEqual(ex.get("source"), "generated")

    def test_aucun_doublon_id_ou_enonce_au_sein_dun_module(self):
        for package, name, _ in _NOUVEAUX_MODULES:
            module = _import_module(package, name)
            pool = module.generate_pool()
            with self.subTest(module=name):
                ids = [e["id"] for e in pool]
                enonces = [e["enonce"] for e in pool]
                self.assertEqual(len(ids), len(set(ids)), f"{name} : doublon d'ID")
                self.assertEqual(len(enonces), len(set(enonces)), f"{name} : doublon d'énoncé")

    def test_determinisme_du_seed(self):
        for package, name, _ in _NOUVEAUX_MODULES:
            module = _import_module(package, name)
            pool_a = module.generate_pool()
            pool_b = module.generate_pool()
            with self.subTest(module=name):
                self.assertEqual([e["enonce"] for e in pool_a], [e["enonce"] for e in pool_b])

    def test_toutes_les_familles_sont_reellement_representees(self):
        """Chaque famille déclarée doit produire AU MOINS un exercice — sinon
        elle serait déclarée mais jamais réellement générée."""
        for package, name, _ in _NOUVEAUX_MODULES:
            module = _import_module(package, name)
            pool = module.generate_pool()
            familles_presentes = {e["family"] for e in pool}
            with self.subTest(module=name):
                self.assertEqual(familles_presentes, set(module.FAMILIES_BY_ID))

    def test_chapter_id_correspond_a_un_chapitre_reellement_declare(self):
        for package, name, class_level in _NOUVEAUX_MODULES:
            module = _import_module(package, name)
            profile = CURRICULUM_REGISTRY[class_level]
            declared_chapters = set()
            if profile.courses_dir is not None and profile.courses_dir.exists():
                for course_path in profile.courses_dir.glob("chapitre_*.json"):
                    import json
                    try:
                        course = json.loads(course_path.read_text(encoding="utf-8"))
                    except (json.JSONDecodeError, OSError):
                        continue
                    if course.get("chapterId"):
                        declared_chapters.add(course["chapterId"])
            with self.subTest(module=name):
                if declared_chapters:
                    self.assertIn(module.CHAPTER_ID, declared_chapters)


class TestFusionTroisiemeReellementServie(unittest.TestCase):
    """Contrairement à Seconde, Troisième fusionne intégralement
    generated_exercise_bank (voir server.py::_class_bank) — les 3 nouveaux
    modules Troisième doivent donc apparaître dans le fichier généré réel."""

    def test_modules_troisieme_presents_dans_le_fichier_genere(self):
        import json
        profile = CURRICULUM_REGISTRY["troisieme"]
        generated = json.loads(profile.generated_exercise_bank.read_text(encoding="utf-8"))
        families_generees = {e["family"] for e in generated}
        for package, name, class_level in _NOUVEAUX_MODULES:
            if class_level != "troisieme":
                continue
            module = _import_module(package, name)
            with self.subTest(module=name):
                self.assertTrue(
                    set(module.FAMILIES_BY_ID) & families_generees,
                    f"{name} : aucune famille trouvée dans le pool généré réellement écrit sur disque",
                )


class TestNouveauxModulesSecondePresentsDansLaBanqueCuree(unittest.TestCase):
    """Seconde n'a pas de fusion generated_exercise_bank générique : les 5
    nouveaux modules Seconde doivent avoir été écrits directement dans
    exercises_bank.json par tools/generate_seconde_curated_additions.py."""

    def test_modules_seconde_presents_dans_exercises_bank(self):
        import json
        profile = CURRICULUM_REGISTRY["seconde"]
        bank = json.loads(profile.exercise_bank.read_text(encoding="utf-8"))
        chapitres_bank = {e.get("chapter_id") for e in bank}
        for package, name, class_level in _NOUVEAUX_MODULES:
            if class_level != "seconde":
                continue
            module = _import_module(package, name)
            with self.subTest(module=name):
                self.assertIn(module.CHAPTER_ID, chapitres_bank)


if __name__ == "__main__":
    unittest.main()
