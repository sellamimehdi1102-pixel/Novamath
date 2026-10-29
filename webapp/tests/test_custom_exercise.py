"""Exercice sur mesure : couverture des cinq classes, tirage depuis la banque
pour les notions sans générateur, type « varié », anti-répétition, titres de
chapitres lisibles (jamais « Chapitre_N » comme libellé élève)."""
import random
import re
import unittest
from unittest import mock

import config
import curriculum_registry
import server


def _client():
    client = server.app.test_client()
    resp = client.post("/api/auth/register", json={
        "email": f"custom{random.randint(1_000_000, 9_999_999)}@gmail.com",
        "username": f"custom{random.randint(100_000, 999_999)}", "pseudo": "Test",
        "birth_date": "2000-01-01",
        "password": "MotDePasse123!", "confirm_password": "MotDePasse123!",
        "accept_terms": True, "accept_privacy": True,
    })
    assert resp.status_code == 201
    return client, {"X-CSRF-Token": client.get_cookie("nm_csrf").value}


class TestCustomExercise(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.object(config, "PEDAGOGY_FREE", True)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.client, self.headers = _client()
        self.notions = self.client.get("/api/practice/generate/options").get_json()["notions"]

    def _generate(self, notion, family_id, exclude=None):
        resp = self.client.post("/api/practice/generate", headers=self.headers, json={
            "class_level": notion["class_level"], "chapter_id": notion["chapter_id"], "notion": notion["notion"],
            "family_id": family_id, "exclude": exclude or [],
        })
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True)[:200])
        return resp.get_json()["exercise"]

    def test_toutes_les_notions_des_banques_sont_proposees_pour_les_cinq_classes(self):
        offered = {(n["class_level"], n["chapter_id"], n["notion"]) for n in self.notions}
        for level in curriculum_registry.CURRICULUM_REGISTRY:
            with self.subTest(class_level=level):
                bank = server._class_bank(level)["bank"]
                wanted = {(level, e["chapter_id"], e["notion"]) for e in bank if e.get("chapter_id") and e.get("notion")}
                self.assertEqual(wanted - offered, set())

    def test_chaque_notion_a_un_titre_de_chapitre_lisible_et_des_types(self):
        for n in self.notions:
            self.assertFalse(re.match(r"^Chapitre[_ ]\d+$", n["chapter_title"]), n)
            self.assertGreater(len(n["families"]), 0)

    def test_notion_sans_generateur_servie_depuis_la_banque_sur_le_bon_sujet(self):
        bank_only = [n for n in self.notions if n["source"] == "banque"]
        self.assertGreater(len(bank_only), 80)
        for level in ("troisieme", "seconde", "premiere", "premiere_specifique"):
            notion = next(n for n in bank_only if n["class_level"] == level)
            for family in notion["families"]:
                with self.subTest(level=level, family=family["family_id"]):
                    ex = self._generate(notion, family["family_id"])
                    self.assertEqual((ex["chapter_id"], ex["notion"]), (notion["chapter_id"], notion["notion"]))
                    self.assertEqual(ex["source"], "banque")
                    self.assertTrue(ex["enonce"] and ex["answer"])
                    if family["level"] is not None:
                        self.assertEqual(ex["difficulty"], family["level"])

    def test_anti_repetition_sur_une_notion_de_banque(self):
        notion = next(n for n in self.notions if n["source"] == "banque" and n["class_level"] == "troisieme")
        family = notion["families"][0]["family_id"]
        seen = []
        for _ in range(12):
            ex = self._generate(notion, family, exclude=seen)
            self.assertNotIn(ex["dedupe_key"], seen)
            seen.append(ex["dedupe_key"])

    def test_famille_variee_melange_les_types_et_evite_les_repetitions(self):
        notion = next(n for n in self.notions if n["source"] == "generateur" and n["families"][0]["family_id"] == "any")
        seen, families = [], set()
        for _ in range(10):
            ex = self._generate(notion, "any", exclude=seen)
            seen.append(ex["dedupe_key"])
            families.add(ex["family"])
        self.assertGreater(len(families), 1)
        self.assertGreaterEqual(len(set(seen)), 9)

    def test_generateur_existant_inchange(self):
        notion = next(n for n in self.notions if n["class_level"] == "quatrieme" and n["source"] == "generateur")
        ex = self._generate(notion, notion["families"][-1]["family_id"])
        self.assertEqual(ex["source"], "generated")
        self.assertEqual(ex["chapter_title"], notion["chapter_title"])

    def test_requetes_invalides(self):
        notion = self.notions[0]
        bad = self.client.post("/api/practice/generate", headers=self.headers, json={
            "class_level": notion["class_level"], "chapter_id": notion["chapter_id"], "notion": "inconnue",
            "family_id": "bank:any",
        })
        self.assertEqual(bad.status_code, 404)
        bad = self.client.post("/api/practice/generate", headers=self.headers, json={
            "class_level": "terminale", "chapter_id": "Chapitre_1", "notion": "x", "family_id": "any",
        })
        self.assertEqual(bad.status_code, 404)


if __name__ == "__main__":
    unittest.main()
