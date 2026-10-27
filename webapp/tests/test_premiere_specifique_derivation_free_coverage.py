# -*- coding: utf-8 -*-
"""
Classe « Première spécifique » (`premiere_specifique`, non publiée : servie
ici en prévisualisation, voir tests/premiere_specifique_preview.py).
Adaptation au manuel « Première ES/L » : la dérivation est le chapitre 5.

Couverture Free du chapitre 3 de Première (refonte pédagogique, Phase 3,
2026-10-23) : vérifie que chaque règle essentielle des 4 notions a bien un
exemple corrigé Free dédié dans la réponse réellement renvoyée par
filter_notion()/la route HTTP — jamais une simple inspection du JSON source,
qui ne dit rien de ce qu'un élève Free reçoit réellement une fois filtré.

Régression ciblée (trouvée lors de l'audit Phase 3) :
- "Opérations sur les dérivées" a 4 règles essentielles (constante, somme,
  produit, quotient) mais n'avait que 3 exemples Free avant cette phase : la
  règle "multiplier par une constante" n'avait aucun exemple dédié.
- "Fonction dérivée" énonce les règles de référence (1/x)' et (√x)' dans
  reglesImportantes, mais aucun exemple (free ou premium) ne les utilisait
  avant cette phase : seuls des polynômes étaient dérivés.

Ce fichier fige ces corrections pour qu'une future notion ne régresse pas en
silence (ex. un exemple reclassé "premium" par erreur, ou une règle ajoutée
sans exemple).
"""
import unittest

import db
from course_content_service import filter_notion
from curriculum_registry import CURRICULUM_REGISTRY_ALL
from tests.premiere_specifique_preview import PreviewHTTPCase, serve_in_preview
from plan_service import Plan


def _load_derivation():
    registry = CURRICULUM_REGISTRY_ALL["premiere_specifique"]
    path = registry.courses_dir / "chapitre_5.json"
    import json

    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _free_example_ids(notion):
    filtered = filter_notion(notion, Plan.FREE)
    return {ex["id"] for ex in (filtered.get("exemples") or [])}


class TestChapitre3CouvertureRegleParRegleFree(unittest.TestCase):
    """Une règle essentielle sans exemple Free dédié est une notion que
    l'élève Free ne peut pas réellement appliquer, même s'il en connaît
    l'énoncé — voir l'exigence "ne jamais réserver à Premium une application
    indispensable à la compréhension d'une règle fondamentale"."""

    def setUp(self):
        self.chapitre = _load_derivation()
        self.notions = {n["id"]: n for n in self.chapitre["notions"]}

    def test_operations_les_quatre_regles_ont_chacune_un_exemple_free(self):
        notion = self.notions["operations-et-derivation"]
        free_ids = _free_example_ids(notion)
        # Un exemple par règle essentielle, voir leur rôle respectif dans le
        # contenu : exemple-639 = constante, exemple-661 = somme,
        # exemple-673 = produit, exemple-649 = quotient.
        for regle, exemple_id in {
            "constante": "exemple-639",
            "somme": "exemple-661",
            "produit": "exemple-673",
            "quotient": "exemple-649",
        }.items():
            with self.subTest(regle=regle):
                self.assertIn(exemple_id, free_ids, f"règle '{regle}' sans exemple Free dédié")

    def test_operations_tableau_comparatif_visible_en_free(self):
        notion = self.notions["operations-et-derivation"]
        filtered = filter_notion(notion, Plan.FREE)
        self.assertIn("tableauComparatif", filtered)
        lignes = filtered["tableauComparatif"]["lignes"]
        self.assertEqual(len(lignes), 4)

    def test_fonction_derivee_regles_usuelles_ont_un_exemple_free(self):
        notion = self.notions["fonction-derivee"]
        free_ids = _free_example_ids(notion)
        self.assertIn(
            "exemple-608",
            free_ids,
            "les règles de référence (1/x)' et (√x)' n'ont aucun exemple Free",
        )

    def test_nombre_derive_tangente_regle_et_equation_ont_chacune_un_exemple_free(self):
        notion = self.notions["nombre-derive.-tangente"]
        free_ids = _free_example_ids(notion)
        self.assertIn("exemple-531", free_ids)  # nombre dérivé / taux de variation
        self.assertIn("exemple-555", free_ids)  # équation de la tangente

    # Programme 2026 (BO n° 14 du 2 avril 2026) : la dérivée de x ↦ g(ax + b)
    # n'est plus au programme de Première ; la notion « Composition de
    # fonctions et dérivation » a été retirée du cours (ses exercices ont été
    # réécrits avec la règle du produit et la règle de l'inverse, voir
    # tools/premiere_specifique/banque_ch03.py). Les deux tests ci-dessous remplacent
    # l'ancien test de couverture de cette notion.
    def test_inverse_a_un_exemple_free(self):
        self.assertIn("exemple-inverse", _free_example_ids(self.notions["operations-et-derivation"]))

    def test_notion_hors_programme_retiree(self):
        from exercise_generator import registry
        serve_in_preview(self)
        self.assertNotIn("composition-de-fonctions-et-derivation", self.notions)
        self.assertNotIn("approximation-affine-et-derivabilite", self.notions)  # hors manuel « Première ES/L »
        served = {k[2] for k in registry.available_notions("premiere_specifique") if k[1] == "Chapitre_5"}
        self.assertNotIn("Composition de fonctions et dérivation", served)
        self.assertNotIn("Approximation affine et dérivabilité", served)

    def test_aucun_exemple_premium_ou_ultra_ne_fuite_en_free(self):
        for notion in self.notions.values():
            filtered = filter_notion(notion, Plan.FREE)
            free_ids = {ex["id"] for ex in (filtered.get("exemples") or [])}
            premium_or_ultra_ids = {
                ex["id"] for ex in (notion.get("exemples") or []) if ex.get("niveauAcces") in ("premium", "ultra")
            }
            self.assertFalse(free_ids & premium_or_ultra_ids)

    def test_chaque_notion_garde_au_moins_une_regle_et_une_methode_en_free(self):
        for notion_id, notion in self.notions.items():
            with self.subTest(notion=notion_id):
                filtered = filter_notion(notion, Plan.FREE)
                self.assertTrue(filtered.get("reglesImportantes"), f"{notion_id}: aucune règle en Free")
                if notion.get("methode", {}).get("etapes"):
                    self.assertTrue(filtered.get("methode", {}).get("etapes"), f"{notion_id}: méthode vide en Free")


class TestChapitre3RouteHttpReelle(PreviewHTTPCase):
    """Même vérification que ci-dessus, mais via la vraie route HTTP
    (server.app.test_client()) plutôt que filter_notion() en isolation —
    pour couvrir aussi le câblage curriculum_registry/get_chapter_content."""


    def _get_derivation(self):
        resp = self.client.get("/api/course-content/premiere_specifique/Chapitre_5", headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        return {n["id"]: n for n in resp.get_json()["notions"]}

    def test_free_recoit_un_exemple_par_regle_essentielle_operations(self):
        notions = self._get_derivation()
        free_ids = {ex["id"] for ex in notions["operations-et-derivation"]["exemples"]}
        self.assertTrue({"exemple-639", "exemple-661", "exemple-673", "exemple-649"}.issubset(free_ids))

    def test_free_recoit_le_tableau_comparatif_operations(self):
        notions = self._get_derivation()
        self.assertIn("tableauComparatif", notions["operations-et-derivation"])

    def test_premium_recoit_en_plus_le_cinquieme_exemple_operations(self):
        db.set_stripe_subscription(self.user["id"], "sub_test", "premium", "active")
        notions = self._get_derivation()
        free_ids = {ex["id"] for ex in notions["operations-et-derivation"]["exemples"]}
        self.assertIn("exemple-685", free_ids)

    def test_ultra_recoit_les_quatre_demonstrations(self):
        db.set_stripe_subscription(self.user["id"], "sub_test", "ultra", "active")
        notions = self._get_derivation()
        for notion_id in notions:
            with self.subTest(notion=notion_id):
                self.assertIn("demonstration", notions[notion_id])
                self.assertFalse(notions[notion_id]["locked_content"]["ultra"])


if __name__ == "__main__":
    unittest.main()
