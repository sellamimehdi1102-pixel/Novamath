"""Non-régression du calibrage pédagogique des difficultés (chantier 2).

Défauts démontrés et corrigés :
- banques générées : la difficulté servie venait d'un score de complexité de
  l'expression (longueur du calcul) ; elle est désormais le niveau
  pédagogique de la famille (tools/calibrage_pedagogique.py) ;
- Première historique (exercises_bank_premiere.json) : des gabarits
  identiques étaient répartis artificiellement sur les niveaux 1 à 5
  (tools/recalibrer_premiere_historique.py).
"""
import json
import re
import sys
import unittest
from pathlib import Path

import server

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

import calibrage_pedagogique as cp  # noqa: E402
import recalibrer_premiere_historique as rph  # noqa: E402

CLASSES_GENEREES = ("quatrieme", "troisieme", "seconde", "premiere", "premiere_specifique")


def _generated(class_level):
    return json.loads((ROOT / f"exercises_generated_{class_level}.json").read_text(encoding="utf-8"))


class TestBanquesGenerees(unittest.TestCase):
    def test_niveau_servi_egal_au_niveau_pedagogique(self):
        for class_level in CLASSES_GENEREES:
            for e in _generated(class_level):
                with self.subTest(classe=class_level, id=e["id"]):
                    self.assertEqual(e["difficulty"], cp.niveau(class_level, e))
                    if "difficulty_label" in e:
                        self.assertEqual((e["difficulty_emoji"], e["difficulty_label"]), cp.LIBELLES[e["difficulty"]])

    def test_niveau_independant_des_nombres_tires(self):
        # Une même famille ne doit plus s'étaler sur plusieurs niveaux selon les coefficients.
        for class_level in CLASSES_GENEREES:
            niveaux = {}
            for e in _generated(class_level):
                # Une famille est propre à une notion (des noms comme « contexte » se répètent d'une notion à l'autre).
                niveaux.setdefault((e["notion"], e["family"]), set()).add(e["difficulty"])
            with self.subTest(classe=class_level):
                self.assertEqual({f: n for f, n in niveaux.items() if len(n) > 1}, {})

    def test_familles_mal_calibrees(self):
        attendus = {
            "premiere": {"arith_demonstration": 2, "trouver_coordonnee_orthogonale": 2, "courbe_tangente": 2,
                         "equation_sin": 2, "polynome_simple": 1, "fn_derivee_simple": 1, "fn_derivee_composee": 2,
                         "variations_racine": 2, "compo_domaine": 1},
            "troisieme": {"retrouver_taux": 2, "ecriture_scientifique": 1, "puissance": 1, "mult_div": 1},
            "seconde": {"signe_tableau": 3, "ineq_erreur": 2},
        }
        for class_level, familles in attendus.items():
            servis = {}
            for e in _generated(class_level):
                servis.setdefault(e["family"], set()).add(e["difficulty"])
            for famille, lvl in familles.items():
                with self.subTest(classe=class_level, famille=famille):
                    self.assertEqual(servis[famille], {lvl})

    def test_defi_reserve_aux_problemes(self):
        defi = {e["family"] for e in _generated("premiere") if e["difficulty"] == 5}
        self.assertLessEqual(defi, {"optimisation", "optimisation_quotient"})

    def test_premiere_specifique_echelle_1_a_4(self):
        # Optimisation guidée (fonction fournie) reclassée Difficile : plus aucun Défi servi.
        gen = _generated("premiere_specifique")
        self.assertEqual({e["difficulty"] for e in gen if e["family"] in ("optimisation", "optimisation_quotient")}, {4})
        self.assertTrue(all(e["difficulty"] <= 4 for e in gen))
        self.assertTrue(all(e["difficulty"] <= 4 for e in server._class_bank("premiere_specifique")["bank"]))

    def test_scripts_de_generation_calibres(self):
        for script in ("generate_derivative_exercises", "generate_premiere_specifique_exercises",
                       "generate_troisieme_exercises", "generate_seconde_exercises"):
            with self.subTest(script=script):
                self.assertIn("calibrer(combined", (ROOT / "tools" / f"{script}.py").read_text(encoding="utf-8"))


class TestPremiereHistorique(unittest.TestCase):
    def setUp(self):
        self.bank = json.loads((ROOT / "exercises_bank_premiere.json").read_text(encoding="utf-8"))
        self.by_id = {e["id"]: e for e in self.bank}

    def test_exemple_demontre(self):
        self.assertEqual(self.by_id[49]["difficulty"], 1)  # u_n = n + 6, calculer u_4

    def test_recalibrage_applique_et_idempotent(self):
        for e in self.bank:
            if e["id"] < rph.LIMITE_HISTORIQUE:
                with self.subTest(id=e["id"]):
                    self.assertEqual(e["difficulty"], rph.niveau(e))

    def test_applications_directes_jamais_difficiles(self):
        motifs = [
            r"définie pour tout entier naturel \$n\$ par \$u_n = .*Calculer \$u_",
            r"Donner les coefficients",
            r"^Rappeler",
            r"^Calculer la dérivée de la fonction \$f\$ définie sur \$\\mathbb\{R\}\$ par \$f\(x\) = [-+ x\d^]*\$\.$",
            r"En utilisant les symétries du cercle trigonométrique",
        ]
        for e in self.bank:
            if e["id"] >= rph.LIMITE_HISTORIQUE:
                continue
            for motif in motifs:
                if re.search(motif, e["enonce"]):
                    with self.subTest(id=e["id"], motif=motif):
                        self.assertLessEqual(e["difficulty"], 2)

    def test_gabarits_non_etales(self):
        # Un gabarit de calcul direct ne s'étale plus sur 1 à 5.
        derivees = [e for e in self.bank if e["id"] < rph.LIMITE_HISTORIQUE and e["notion"] == "Fonction dérivée"
                    and e["enonce"].startswith("Calculer la dérivée de la fonction $f$ définie sur")]
        self.assertTrue(derivees)
        self.assertLessEqual({e["difficulty"] for e in derivees}, {1, 2})

    def test_niveau_5_historique_limite_aux_demonstrations(self):
        defi = {e["id"] for e in self.bank if e["id"] < rph.LIMITE_HISTORIQUE and e["difficulty"] == 5}
        self.assertEqual(defi, {2180, 2196})


class TestServis(unittest.TestCase):
    def test_banques_servies_coherentes(self):
        for class_level in CLASSES_GENEREES:
            bank = server._class_bank(class_level)["bank"]
            ids = [e["id"] for e in bank]
            with self.subTest(classe=class_level):
                self.assertEqual(len(ids), len(set(ids)))
                self.assertTrue(all(e["difficulty"] in (1, 2, 3, 4, 5) for e in bank))
                if class_level == "quatrieme":
                    self.assertTrue(all(e["difficulty"] <= 4 for e in bank))
                # Aucun caractère de contrôle (ex. « \t » issu d'un « \times » mal échappé).
                for e in bank:
                    texte = e["enonce"] + e["answer"] + "".join(e.get("solution_steps") or [])
                    self.assertFalse(re.search(r"[\x00-\x08\x0b-\x1f]", texte), e["id"])

    def test_couverture_complete_des_cinq_classes(self):
        # Finalisation du chantier 2 : au moins 4 questions à chaque niveau de l'échelle
        # de la classe (1-4 en Quatrième et en Première spécifique curée, 1-5 ailleurs).
        echelles = {"quatrieme": 4, "troisieme": 5, "seconde": 5, "premiere": 5, "premiere_specifique": 4}
        for class_level, niveau_max in echelles.items():
            compte = {}
            for e in server._class_bank(class_level)["bank"]:
                compte[(e["chapter_id"], e["notion"], e["difficulty"])] = compte.get((e["chapter_id"], e["notion"], e["difficulty"]), 0) + 1
            notions = {(ch, n) for ch, n, _ in compte}
            manquants = {(ch, n, d): compte.get((ch, n, d), 0) for ch, n in notions for d in range(1, niveau_max + 1) if compte.get((ch, n, d), 0) < 4}
            with self.subTest(classe=class_level):
                self.assertEqual(manquants, {})

    def test_ajouts_premiere_sans_toucher_aux_identifiants_existants(self):
        import add_premiere_niveaux_eleves as ajout
        bank = {e["id"]: e for e in json.loads((ROOT / "exercises_bank_premiere.json").read_text(encoding="utf-8"))}
        self.assertEqual(ajout.FIRST_ID, 2386)
        servis = []
        for i, ex in enumerate(ajout.EXERCICES):
            ex_id = ajout.FIRST_ID + i
            attendu = {**ex, "id": ex_id, "difficulty": ajout.RECALIBRAGE.get(ex_id, ex["difficulty"])}
            servis.append(attendu)
            with self.subTest(id=ex_id):
                self.assertEqual(bank[ex_id], attendu)
        # Relecture : les Défi reclassés (technique classique, stratégie indiquée) ne sont plus au niveau 5.
        self.assertTrue(all(bank[i]["difficulty"] <= 4 for i in ajout.RECALIBRAGE))
        self.assertNotIn("deux à deux", bank[2606]["enonce"])  # indépendance mutuelle : hors programme
        # Les questions Défi ajoutées sont des démonstrations, synthèses ou problèmes à plusieurs étapes.
        defi = [e for e in servis if e["difficulty"] == 5]
        self.assertGreaterEqual(len(defi), 120)
        self.assertTrue(all(len(e["solution_steps"]) >= 2 for e in defi))

    def test_quatrieme_petites_lacunes_comblees(self):
        compte = {}
        for e in server._class_bank("quatrieme")["bank"]:
            compte[(e["notion"], e["difficulty"])] = compte.get((e["notion"], e["difficulty"]), 0) + 1
        self.assertGreaterEqual(compte[("Nommer les côtés d'un triangle rectangle", 3)], 4)
        self.assertGreaterEqual(compte[("Utiliser les nombres premiers : fractions et problèmes", 1)], 4)


if __name__ == "__main__":
    unittest.main()
