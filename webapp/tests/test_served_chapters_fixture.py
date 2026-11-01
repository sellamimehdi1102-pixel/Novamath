"""L'instantané de /api/chapters utilisé par exercice-adaptive-classes.test.js
doit rester identique aux banques réellement servies (sinon : relancer
`python tests/dump_served_chapters.py --write`)."""
import json
import unittest

from tests import dump_served_chapters as dump


class TestInstantaneChapitresServis(unittest.TestCase):
    def test_instantane_identique_a_la_reponse_reelle(self):
        instantane = json.loads(dump.FIXTURE.read_text(encoding="utf-8"))
        reel = dump.served_chapters()
        for class_level in dump.CLASSES:
            with self.subTest(classe=class_level):
                self.assertEqual(instantane[class_level], reel[class_level])
        self.assertEqual(set(instantane), set(dump.CLASSES))


if __name__ == "__main__":
    unittest.main()
