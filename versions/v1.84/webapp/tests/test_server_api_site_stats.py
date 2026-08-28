"""
Suite de non-régression pour /api/site/stats et /api/curricula (server.py) —
créée après incident : `?class_level=<valeur inconnue>` faisait remonter un
KeyError non intercepté jusqu'à Flask (500), reproductible avec n'importe
quelle valeur absente de curriculum_registry.CURRICULUM_REGISTRY (faute de
frappe, cache client périmé, appel direct de l'API). Le correctif valide
`class_level` contre le registre AVANT d'appeler curriculum_stats.py, et
renvoie une erreur 404 explicite plutôt qu'un crash.
"""
import unittest

import server


class TestApiSiteStats(unittest.TestCase):
    def setUp(self):
        self.client = server.app.test_client()

    def test_classe_inconnue_renvoie_404_explicite_jamais_500(self):
        resp = self.client.get("/api/site/stats?class_level=inexistante")
        self.assertEqual(resp.status_code, 404)
        body = resp.get_json()
        self.assertIn("error", body)
        self.assertIn("inexistante", body["error"])

    def test_sans_parametre_egale_seconde_explicite_egale_seconde_vide(self):
        without_param = self.client.get("/api/site/stats").get_json()
        explicit_seconde = self.client.get("/api/site/stats?class_level=seconde").get_json()
        empty_param = self.client.get("/api/site/stats?class_level=").get_json()
        self.assertEqual(without_param, explicit_seconde)
        self.assertEqual(without_param, empty_param)
        self.assertEqual(without_param["totalExercises"], len(server.BANK))

    def test_premiere_renvoie_des_statistiques_reelles(self):
        resp = self.client.get("/api/site/stats?class_level=premiere")
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertEqual(body["classLevel"], "premiere")
        self.assertGreater(body["totalExercises"], 0)


class TestApiCurricula(unittest.TestCase):
    def setUp(self):
        self.client = server.app.test_client()

    def test_liste_les_deux_programmes_actuels(self):
        resp = self.client.get("/api/curricula")
        self.assertEqual(resp.status_code, 200)
        ids = {c["classLevel"] for c in resp.get_json()}
        self.assertEqual(ids, {"seconde", "premiere"})


if __name__ == "__main__":
    unittest.main()
