# -*- coding: utf-8 -*-
"""
Couverture Free des chapitres 1, 4, 5 et 8 de Première (audit final, Phase 4,
2026-10-23) : vérifie que chaque règle essentielle identifiée comme manquante
lors de l'audit a désormais un exemple corrigé Free dédié dans la réponse
réellement renvoyée par filter_notion() — jamais une simple inspection du
JSON source.

Régressions ciblées (trouvées lors de l'audit Phase 4) :
- "Suite géométrique" : la règle "retrouver la raison à partir de deux termes"
  n'avait aucun exemple Free (seulement en Premium).
- "Calcul de sommes" : aucun exemple (Free ou Premium) ne testait le piège
  classique du nombre de termes quand la somme ne part pas de l'indice 0
  (q-p+1, pas q-p).
- "Nombre dérivé et extremums locaux" : le piège explicitement décrit dans
  l'intuition et les erreurs fréquentes (f'(x0)=0 sans extremum, ex. x^3)
  n'avait aucun exemple Free illustrant ce cas.
- "Courbe représentative" : la règle "un point (a;b) appartient à la courbe
  si b=f(a)" n'avait aucun exemple, Free ou Premium.
- "Propriétés algébriques" (exponentielle) : la règle de la puissance
  (e^a)^n=e^{na} n'avait aucun exemple Free.
- "Propriétés analytiques" (exponentielle) : la règle d'égalité e^u=e^v⟺u=v
  n'avait aucun exemple Free (seulement les inégalités étaient illustrées).
- "Équation d'un cercle" : le piège "membre de droite négatif ⟹ pas un
  cercle" n'avait aucun exemple, Free ou Premium.

Ce fichier fige ces corrections pour qu'une future notion ne régresse pas en
silence (ex. un exemple reclassé "premium" par erreur, ou une règle ajoutée
sans exemple).
"""
import json
import unittest

from course_content_service import filter_notion
from curriculum_registry import CURRICULUM_REGISTRY
from plan_service import Plan


def _load_chapitre(numero):
    registry = CURRICULUM_REGISTRY["premiere"]
    path = registry.courses_dir / f"chapitre_{numero}.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _free_example_ids(notion):
    filtered = filter_notion(notion, Plan.FREE)
    return {ex["id"] for ex in (filtered.get("exemples") or [])}


class TestChapitre1CouvertureFree(unittest.TestCase):
    def setUp(self):
        self.notions = {n["id"]: n for n in _load_chapitre(1)["notions"]}

    def test_suite_geometrique_raison_a_partir_de_deux_termes_est_free(self):
        notion = self.notions["suite-geometrique"]
        free_ids = _free_example_ids(notion)
        self.assertIn("exemple-154", free_ids, "règle 'retrouver la raison' sans exemple Free dédié")

    def test_calcul_de_sommes_piege_indice_non_nul_est_free(self):
        notion = self.notions["calcul-de-sommes"]
        free_ids = _free_example_ids(notion)
        filtered = filter_notion(notion, Plan.FREE)
        exemple = next(e for e in filtered["exemples"] if e["id"] == "exemple-177")
        self.assertIn("exemple-177", free_ids)
        self.assertIn("u_3", exemple["enonce"].replace(" ", ""))
        self.assertIn("17-3+1", "".join(c["texte"] for c in exemple["calcul"]))


class TestChapitre4CouvertureFree(unittest.TestCase):
    def setUp(self):
        self.notions = {n["id"]: n for n in _load_chapitre(4)["notions"]}

    def test_extremum_sans_changement_de_signe_est_free(self):
        notion = self.notions["nombre-derive-et-extremums-locaux"]
        free_ids = _free_example_ids(notion)
        filtered = filter_notion(notion, Plan.FREE)
        exemple = next(e for e in filtered["exemples"] if e["id"] == "exemple-838")
        self.assertIn("exemple-838", free_ids)
        self.assertIn("pas", exemple["reponse"].lower())


class TestChapitre5CouvertureFree(unittest.TestCase):
    def setUp(self):
        self.notions = {n["id"]: n for n in _load_chapitre(5)["notions"]}

    def test_point_appartient_a_la_courbe_est_free(self):
        notion = self.notions["courbe-representative"]
        free_ids = _free_example_ids(notion)
        self.assertIn("exemple-1216", free_ids, "règle 'point sur la courbe' sans exemple Free dédié")

    def test_regle_puissance_exponentielle_est_free(self):
        notion = self.notions["proprietes-algebriques"]
        free_ids = _free_example_ids(notion)
        self.assertIn("exemple-980", free_ids, "règle de la puissance (e^a)^n sans exemple Free dédié")

    def test_cas_egalite_est_free(self):
        notion = self.notions["proprietes-analytiques"]
        free_ids = _free_example_ids(notion)
        filtered = filter_notion(notion, Plan.FREE)
        exemple = next(e for e in filtered["exemples"] if e["id"] == "exemple-1133")
        self.assertIn("exemple-1133", free_ids)
        self.assertIn("=", exemple["enonce"])
        self.assertNotIn(">", exemple["enonce"])
        self.assertNotIn("<", exemple["enonce"])


class TestChapitre8CouvertureFree(unittest.TestCase):
    def setUp(self):
        self.notions = {n["id"]: n for n in _load_chapitre(8)["notions"]}

    def test_cas_pas_un_cercle_est_free(self):
        notion = self.notions["equation-d-un-cercle"]
        free_ids = _free_example_ids(notion)
        filtered = filter_notion(notion, Plan.FREE)
        exemple = next(e for e in filtered["exemples"] if e["id"] == "exemple-1664")
        self.assertIn("exemple-1664", free_ids, "piège 'membre négatif' sans exemple Free dédié")
        self.assertIn("pas", exemple["reponse"].lower())


class TestApercusUltraAnnoncentLesDemonstrationsReelles(unittest.TestCase):
    """Un aperçu Ultra doit toujours correspondre à un contenu Ultra qui
    existe réellement (ici : la démonstration de la notion)."""

    def setUp(self):
        self.notions = {n["id"]: n for n in _load_chapitre(7)["notions"]}

    def test_produit_scalaire_demonstration_annoncee(self):
        notion = self.notions["produit-scalaire,-colinearite-et-orthogonalite-de-vecteurs"]
        self.assertTrue(notion.get("demonstration"))
        niveaux = [a.get("niveau") for a in notion.get("apercus", [])]
        self.assertIn("ultra", niveaux)

    def test_etude_ensemble_de_points_demonstration_annoncee(self):
        notion = self.notions["etude-d-un-ensemble-de-points"]
        self.assertTrue(notion.get("demonstration"))
        niveaux = [a.get("niveau") for a in notion.get("apercus", [])]
        self.assertIn("ultra", niveaux)


if __name__ == "__main__":
    unittest.main()
