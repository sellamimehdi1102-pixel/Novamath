"""Prérequis entre notions (webapp/static/data/notion_prerequisites.json).

Le fichier est lu par exercice.js et transmis à adaptiveDifficulty.js::transferPrior
(`relations`) : il doit correspondre exactement aux notions servies, rester propre
à chaque classe, sans cycle, et ne contenir aucune relation pour la Quatrième et la
Troisième (non encore renseignées).
"""
import json
import unittest
from pathlib import Path

import server

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "static" / "data" / "notion_prerequisites.json"
DIST = ROOT / "static-dist" / "data" / "notion_prerequisites.json"


def _relations():
    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    return {k: v for k, v in data.items() if not k.startswith("_")}


class TestPrerequis(unittest.TestCase):
    def test_classes_renseignees(self):
        self.assertEqual(set(_relations()), {"seconde", "premiere", "premiere_specifique"})

    def test_nombre_de_relations(self):
        # 56 notions ayant au moins un prérequis, 59 liens au total.
        self.assertEqual(sum(len(rel) for rel in _relations().values()), 56)
        self.assertEqual(sum(len(v) for rel in _relations().values() for v in rel.values()), 59)

    def test_notions_servies_dans_la_meme_classe(self):
        for class_level, rel in _relations().items():
            served = {f"{e['chapter_id']}|{e['notion']}" for e in server._class_bank(class_level)["bank"]}
            for notion, prereqs in rel.items():
                with self.subTest(classe=class_level, notion=notion):
                    self.assertIn(notion, served)
                    self.assertTrue(prereqs)
                    for p in prereqs:
                        self.assertIn(p, served)
                        self.assertNotEqual(p, notion)

    def test_sans_cycle(self):
        # Un prérequis ne peut pas dépendre, même indirectement, de la notion qu'il prépare.
        for class_level, rel in _relations().items():
            def atteint(depart, cible, vus):
                for p in rel.get(depart, []):
                    if p == cible or (p not in vus and atteint(p, cible, vus | {p})):
                        return True
                return False

            for notion in rel:
                with self.subTest(classe=class_level, notion=notion):
                    self.assertFalse(atteint(notion, notion, set()))

    # static-dist/ est produit par `npm run build` et ignoré par git : absent du job
    # backend de la CI (le job frontend valide le build). Contrôlé dès qu'il existe.
    @unittest.skipUnless(DIST.parent.parent.is_dir(), "static-dist absent (build frontend non exécuté)")
    def test_copie_servie_identique(self):
        # static-dist/ est servi en priorité par le serveur : il doit contenir la même version.
        self.assertEqual(json.loads(DIST.read_text(encoding="utf-8")), json.loads(SOURCE.read_text(encoding="utf-8")))

    def test_fichier_servi_par_le_serveur(self):
        client = server.app.test_client()
        response = client.get("/data/notion_prerequisites.json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), json.loads(SOURCE.read_text(encoding="utf-8")))

    @unittest.skipUnless(DIST.parent.parent.is_dir(), "static-dist absent (build frontend non exécuté)")
    def test_bundle_servi_charge_les_prerequis(self):
        # Le serveur sert static-dist : le bundle de exercice.html doit contenir le branchement.
        import re

        client = server.app.test_client()
        self.assertEqual(Path(server.app.static_folder).name, "static-dist")
        # exercice.html exige une session (redirection vers la connexion) : on lit la page
        # construite, puis on télécharge son bundle via le serveur (assets publics).
        html = (ROOT / "static-dist" / "exercice.html").read_text(encoding="utf-8")
        scripts = re.findall(r'src="/?(assets/exercice[^"]+\.js)"', html)
        self.assertTrue(scripts, "script exercice introuvable dans exercice.html")
        response = client.get("/" + scripts[0])
        self.assertEqual(response.status_code, 200)
        bundle = response.get_data(as_text=True)
        self.assertIn("/data/notion_prerequisites.json", bundle)


if __name__ == "__main__":
    unittest.main()
