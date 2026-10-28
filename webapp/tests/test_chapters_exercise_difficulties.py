"""/api/chapters : champ additif `exercise_difficulties`, aligné sur
`exercise_ids`, lu par exercice.js pour les séries adaptatives
(voir webapp/static/js/adaptiveDifficulty.js). Les champs existants ne
changent pas."""
import unittest

import curriculum_registry
import server


class TestExerciseDifficulties(unittest.TestCase):
    def setUp(self):
        self.client = server.app.test_client()

    def test_aligne_sur_exercise_ids_pour_chaque_classe(self):
        for class_level in curriculum_registry.CURRICULUM_REGISTRY:
            with self.subTest(class_level=class_level):
                data = self.client.get(f"/api/chapters?class_level={class_level}").get_json()
                bank_by_id = server._class_bank(class_level)["bank_by_id"]
                checked = 0
                for chapter in data["chapters_meta"]:
                    for notion in chapter["notions_detail"]:
                        ids, diffs = notion["exercise_ids"], notion["exercise_difficulties"]
                        self.assertEqual(len(ids), len(diffs))
                        for ex_id, difficulty in zip(ids, diffs):
                            self.assertEqual(difficulty, bank_by_id[ex_id].get("difficulty"))
                            checked += 1
                self.assertGreater(checked, 0)

    def test_champs_existants_inchanges(self):
        notion = self.client.get("/api/chapters").get_json()["chapters_meta"][0]["notions_detail"][0]
        for key in ("notion", "n_exercises", "difficulty_dominant", "difficulty_counts", "exercise_ids"):
            self.assertIn(key, notion)


if __name__ == "__main__":
    unittest.main()
