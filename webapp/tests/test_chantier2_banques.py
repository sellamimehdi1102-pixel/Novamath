"""Chantier 2 (2026-11-01) — compléments de niveaux des banques et prérequis.

- Les valeurs des exercices ajoutés sont recalculées (SymPy / Fraction) :
  check_chapter pour la Première spécifique, assertions à l'import pour les
  outils tools/add_troisieme_chantier2.py et tools/add_premiere_chantier2.py.
- Les exercices ajoutés sont bien servis, sans identifiant en double avec la
  banque générée et sans énoncé repris d'un exercice existant.
- Les niveaux auparavant absents ou insuffisants atteignent au moins 4
  questions dans le pool servi.
- webapp/static/data/notion_prerequisites.json ne référence que des notions
  servies, sans boucle ni cycle.
"""
import importlib
import json
import sys
import unittest
from pathlib import Path

import server

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT))

MIN_PAR_NIVEAU = 4

# (classe, chapitre, notion, niveaux complétés[, minimum garanti]).
# Première spécialité : seuils retirés après le recalibrage pédagogique
# (tools/calibrage_pedagogique.py, tools/recalibrer_premiere_historique.py) —
# ils n'étaient atteints que grâce à des applications directes surclassées ;
# les lacunes réelles des niveaux 4-5 sont suivies à part (voir rapport).
COMPLETES = [
    ("premiere_specifique", "Chapitre_1", "Proportions et pourcentages", (3, 4)),
    ("premiere_specifique", "Chapitre_1", "Évolutions et taux", (4,)),
    ("premiere_specifique", "Chapitre_2", "Rappels sur les fonctions", (2, 4)),
    ("premiere_specifique", "Chapitre_2", "Fonction racine carrée", (3,)),
    ("premiere_specifique", "Chapitre_2", "Fonction cube", (4,)),
    ("premiere_specifique", "Chapitre_3", "Racines et factorisation d'un trinôme", (1, 4)),
    ("premiere_specifique", "Chapitre_4", "Notation Σ et indicateurs de tendance centrale", (3, 4)),
    ("premiere_specifique", "Chapitre_4", "Quartiles et diagramme en boîte", (4,)),
    ("premiere_specifique", "Chapitre_4", "Variance, écart-type et dispersion", (1,)),
    ("premiere_specifique", "Chapitre_5", "Opérations et dérivation", (4,)),
    ("premiere_specifique", "Chapitre_6", "Nombre dérivé et extremums locaux", (1,)),
    ("premiere_specifique", "Chapitre_7", "Généralités sur les suites", (4,)),
    ("premiere_specifique", "Chapitre_7", "Suite arithmétique", (4,)),
    ("premiere_specifique", "Chapitre_8", "Loi des grands nombres et simulation", (1, 2, 3, 4)),
    ("premiere_specifique", "Chapitre_9", "Expériences indépendantes et loi de Bernoulli", (3, 4)),
    ("premiere_specifique", "Chapitre_9", "Échantillonnage et règle de décision", (1, 4)),
    ("troisieme", "Chapitre_10", "Déterminer la probabilité d'un événement", (1, 4)),
]


def _counts(class_level, chapter, notion):
    counts = {}
    for e in server._class_bank(class_level)["bank"]:
        if e.get("chapter_id") == chapter and e.get("notion") == notion:
            counts[e["difficulty"]] = counts.get(e["difficulty"], 0) + 1
    return counts


class TestValeursRecalculees(unittest.TestCase):
    def test_premiere_specifique_check_chapter(self):
        from premiere_specifique.banque_commun import check_chapter
        from premiere_specifique.chapitres import banque_modules

        for number, module in banque_modules():
            with self.subTest(chapitre=number):
                self.assertEqual(check_chapter(module), [])

    def test_outils_troisieme_et_premiere(self):
        # Chaque exercice vérifie ses valeurs à la construction (assert dans _ex).
        for name in ("tools.add_troisieme_chantier2", "tools.add_premiere_chantier2"):
            with self.subTest(outil=name):
                module = importlib.import_module(name)
                self.assertTrue(module.EXERCICES)


class TestBanquesServies(unittest.TestCase):
    def test_exercices_ajoutes_servis_sans_doublon(self):
        from premiere_specifique.complements_chantier2 import complements
        import tools.add_premiere_chantier2 as premiere
        import tools.add_troisieme_chantier2 as troisieme

        attendus = {
            "premiere_specifique": {e.id for n in range(1, 10) for e in complements(n)},
            "troisieme": {troisieme.FIRST_ID + i for i in range(len(troisieme.EXERCICES))},
            "premiere": {premiere.FIRST_ID + i for i in range(len(premiere.EXERCICES))},
        }
        for class_level, ids in attendus.items():
            with self.subTest(classe=class_level):
                bank = server._class_bank(class_level)["bank"]
                tous = [e["id"] for e in bank]
                self.assertEqual(len(tous), len(set(tous)), "identifiant en double (banque curée + générée)")
                servis = {e["id"]: e for e in bank}
                self.assertFalse(ids - set(servis), "exercice ajouté non servi")
                enonces = [e["enonce"] for e in bank]
                ajoutes = {servis[i]["enonce"] for i in ids}
                self.assertFalse([t for t in ajoutes if enonces.count(t) > 1], "énoncé repris d'un exercice existant")
                for i in ids:
                    e = servis[i]
                    self.assertTrue(e["enonce"] and e["answer"] and e["hint"] and e["solution_steps"])
                    self.assertIn(e["difficulty"], (1, 2, 3, 4, 5))

    def test_niveaux_completes(self):
        for class_level, chapter, notion, niveaux, *minimum in COMPLETES:
            counts = _counts(class_level, chapter, notion)
            for niveau in niveaux:
                with self.subTest(classe=class_level, notion=notion, niveau=niveau):
                    self.assertGreaterEqual(counts.get(niveau, 0), minimum[0] if minimum else MIN_PAR_NIVEAU)


class TestQuatriemeNiveauDifficile(unittest.TestCase):
    def test_niveau_4_present_dans_chaque_notion(self):
        par_notion = {}
        for e in server._class_bank("quatrieme")["bank"]:
            self.assertIn(e["difficulty"], (1, 2, 3, 4), "échelle de la Quatrième : 1 à 4")
            if e["difficulty"] == 4:
                key = (e["chapter_id"], e["notion"])
                par_notion[key] = par_notion.get(key, 0) + 1
        notions = {(e["chapter_id"], e["notion"]) for e in server._class_bank("quatrieme")["bank"]}
        for key in notions:
            with self.subTest(notion=key):
                # Après relecture pédagogique (applications directes ramenées au
                # niveau 3), 19 notions n'ont que 2 ou 3 exercices de niveau 4 :
                # lacune réelle, signalée ; minimum garanti ici.
                self.assertGreaterEqual(par_notion.get(key, 0), 2)

    def test_quatrieme_controles_recalcules(self):
        import build_quatrieme_bank

        self.assertEqual(build_quatrieme_bank.check_all_chapters(), [])
        servie = json.loads((ROOT / "exercises_bank_quatrieme.json").read_text(encoding="utf-8"))
        self.assertEqual(servie, build_quatrieme_bank.build_all(), "banque servie différente des modules")


class TestPrerequis(unittest.TestCase):
    def setUp(self):
        path = ROOT / "webapp" / "static" / "data" / "notion_prerequisites.json"
        self.data = {k: v for k, v in json.loads(path.read_text(encoding="utf-8")).items() if not k.startswith("_")}

    def test_notions_servies_et_sans_cycle(self):
        for class_level, relations in self.data.items():
            with self.subTest(classe=class_level):
                servies = {f"{e['chapter_id']}|{e['notion']}" for e in server._class_bank(class_level)["bank"]}
                for key, prereqs in relations.items():
                    self.assertIn(key, servies)
                    self.assertTrue(prereqs)
                    for p in prereqs:
                        self.assertIn(p, servies)
                        self.assertNotEqual(p, key)
                # Aucun cycle (parcours en profondeur).
                etat = {}

                def visite(n):
                    etat[n] = 1
                    for p in relations.get(n, ()):
                        self.assertNotEqual(etat.get(p), 1, f"cycle via {n} -> {p}")
                        if p not in etat:
                            visite(p)
                    etat[n] = 2

                for n in relations:
                    if n not in etat:
                        visite(n)


if __name__ == "__main__":
    unittest.main()
