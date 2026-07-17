"""
Audit multi-classe du module Cours (progression de lecture) : les mêmes
chapter_id ("Chapitre_1"...) existent dans plusieurs classes
(curriculum_registry.py) — sans isolation par classe, la progression de
Première pourrait apparaître comme celle de Seconde et inversement (bug
rapporté). Vérifie : isolation totale entre classes, données historiques
("seconde", format à plat) lues sans migration destructive, aucune perte de
données lors de la première écriture après cette évolution.
"""
import json
import shutil
import unittest
from pathlib import Path

import auth

TEST_USER_ID = "course-progress-class-level-test-user"


class _TmpCourseDirMixin:
    def setUp(self):
        self._orig_dir = auth.USER_COURSE_DIR
        self._tmp_dir = Path(auth.USER_COURSE_DIR).parent / "_test_user_course_progress"
        if self._tmp_dir.exists():
            shutil.rmtree(self._tmp_dir)
        self._tmp_dir.mkdir(parents=True)
        auth.USER_COURSE_DIR = self._tmp_dir

    def tearDown(self):
        auth.USER_COURSE_DIR = self._orig_dir
        if self._tmp_dir.exists():
            shutil.rmtree(self._tmp_dir)

    def _path(self):
        return self._tmp_dir / f"{TEST_USER_ID}.json"


class TestIsolationEntreClasses(_TmpCourseDirMixin, unittest.TestCase):
    def test_ecriture_seconde_invisible_depuis_premiere(self):
        auth.write_user_course_progress(TEST_USER_ID, "Chapitre_1", "n1", {"status": "in_progress"}, class_level="seconde")
        self.assertEqual(auth.read_user_course_progress(TEST_USER_ID, class_level="premiere"), {})

    def test_ecriture_premiere_invisible_depuis_seconde(self):
        auth.write_user_course_progress(TEST_USER_ID, "Chapitre_1", "n1", {"status": "in_progress"}, class_level="premiere")
        self.assertEqual(auth.read_user_course_progress(TEST_USER_ID, class_level="seconde"), {})

    def test_meme_chapter_id_deux_classes_progressions_distinctes(self):
        auth.write_user_course_progress(TEST_USER_ID, "Chapitre_1", "n1", {"status": "done"}, class_level="seconde")
        auth.write_user_course_progress(TEST_USER_ID, "Chapitre_1", "n1", {"status": "in_progress"}, class_level="premiere")
        seconde = auth.read_user_course_progress(TEST_USER_ID, class_level="seconde")
        premiere = auth.read_user_course_progress(TEST_USER_ID, class_level="premiere")
        self.assertEqual(seconde["Chapitre_1"]["n1"]["status"], "done")
        self.assertEqual(premiere["Chapitre_1"]["n1"]["status"], "in_progress")


class TestCompatibiliteAscendante(_TmpCourseDirMixin, unittest.TestCase):
    """Fichiers écrits AVANT cette évolution (format à plat, non namespacé)."""

    def _write_legacy_file(self, data):
        self._tmp_dir.mkdir(parents=True, exist_ok=True)
        self._path().write_text(json.dumps(data), encoding="utf-8")

    def test_donnees_historiques_lues_comme_seconde_sans_parametre(self):
        self._write_legacy_file({"Chapitre_3": {"n2": {"status": "done", "updatedAt": 123}}})
        self.assertEqual(
            auth.read_user_course_progress(TEST_USER_ID),
            {"Chapitre_3": {"n2": {"status": "done", "updatedAt": 123}}},
        )

    def test_donnees_historiques_lues_comme_seconde_explicite(self):
        self._write_legacy_file({"Chapitre_3": {"n2": {"status": "done", "updatedAt": 123}}})
        self.assertEqual(
            auth.read_user_course_progress(TEST_USER_ID, class_level="seconde")["Chapitre_3"]["n2"]["status"],
            "done",
        )

    def test_donnees_historiques_invisibles_pour_une_autre_classe(self):
        self._write_legacy_file({"Chapitre_3": {"n2": {"status": "done"}}})
        self.assertEqual(auth.read_user_course_progress(TEST_USER_ID, class_level="premiere"), {})

    def test_fichier_absent_ne_plante_pas(self):
        self.assertEqual(auth.read_user_course_progress(TEST_USER_ID, class_level="premiere"), {})
        self.assertEqual(auth.read_user_course_progress(TEST_USER_ID), {})

    def test_premiere_ecriture_apres_migration_conserve_les_donnees_seconde(self):
        """Écrire une progression Première ne doit jamais faire disparaître
        la progression Seconde déjà présente au format historique."""
        self._write_legacy_file({"Chapitre_5": {"n9": {"status": "done", "updatedAt": 999}}})
        auth.write_user_course_progress(TEST_USER_ID, "Chapitre_1", "n1", {"status": "in_progress"}, class_level="premiere")

        seconde = auth.read_user_course_progress(TEST_USER_ID, class_level="seconde")
        premiere = auth.read_user_course_progress(TEST_USER_ID, class_level="premiere")
        self.assertEqual(seconde["Chapitre_5"]["n9"]["status"], "done")
        self.assertEqual(premiere["Chapitre_1"]["n1"]["status"], "in_progress")

        # Le fichier sur disque est bien passé au format namespacé (une seule
        # écriture, jamais une copie parallèle des anciennes données).
        on_disk = json.loads(self._path().read_text(encoding="utf-8"))
        self.assertIn("seconde", on_disk)
        self.assertIn("premiere", on_disk)

    def test_ecriture_seconde_sans_parametre_reste_compatible(self):
        """Un appelant qui n'a pas encore été mis à jour pour transmettre
        class_level (comportement par défaut) continue de fonctionner
        exactement comme avant cette évolution."""
        updated = auth.write_user_course_progress(TEST_USER_ID, "Chapitre_2", "n4", {"status": "done"})
        self.assertEqual(updated["Chapitre_2"]["n4"]["status"], "done")
        self.assertEqual(auth.read_user_course_progress(TEST_USER_ID)["Chapitre_2"]["n4"]["status"], "done")


class TestFormatNamespaceParClasse(_TmpCourseDirMixin, unittest.TestCase):
    def test_fusion_partielle_ne_supprime_pas_les_autres_notions(self):
        auth.write_user_course_progress(TEST_USER_ID, "Chapitre_1", "n1", {"status": "done"}, class_level="premiere")
        auth.write_user_course_progress(TEST_USER_ID, "Chapitre_1", "n2", {"status": "in_progress"}, class_level="premiere")
        progress = auth.read_user_course_progress(TEST_USER_ID, class_level="premiere")
        self.assertEqual(progress["Chapitre_1"]["n1"]["status"], "done")
        self.assertEqual(progress["Chapitre_1"]["n2"]["status"], "in_progress")

    def test_write_renvoie_uniquement_la_progression_de_la_classe_ecrite(self):
        auth.write_user_course_progress(TEST_USER_ID, "Chapitre_1", "n1", {"status": "done"}, class_level="seconde")
        updated = auth.write_user_course_progress(TEST_USER_ID, "Chapitre_1", "n1", {"status": "done"}, class_level="premiere")
        self.assertNotIn("seconde", updated)
        self.assertIn("Chapitre_1", updated)


if __name__ == "__main__":
    unittest.main()
