# -*- coding: utf-8 -*-
"""
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
import server
from course_content_service import filter_notion
from curriculum_registry import CURRICULUM_REGISTRY
from plan_service import Plan


def _load_chapitre_3():
    registry = CURRICULUM_REGISTRY["premiere"]
    path = registry.courses_dir / "chapitre_3.json"
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
        self.chapitre = _load_chapitre_3()
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

    def test_composition_les_trois_regles_ont_chacune_un_exemple_free(self):
        notion = self.notions["composition-de-fonctions-et-derivation"]
        free_ids = _free_example_ids(notion)
        self.assertIn("exemple-708", free_ids)  # puissance
        self.assertIn("exemple-720", free_ids)  # racine
        self.assertIn("exemple-756", free_ids)  # inverse

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


def _register(client):
    import random

    email = f"test{random.randint(1_000_000, 9_999_999)}@gmail.com"
    username = f"testuser{random.randint(100_000, 999_999)}"
    resp = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "username": username,
            "pseudo": "Test",
            "birth_date": "2000-01-01",
            "password": "MotDePasse123!",
            "confirm_password": "MotDePasse123!",
            "accept_terms": True,
            "accept_privacy": True,
        },
    )
    user = resp.get_json()["user"]
    csrf = client.get_cookie("nm_csrf").value
    return user, {"X-CSRF-Token": csrf}


class TestChapitre3RouteHttpReelle(unittest.TestCase):
    """Même vérification que ci-dessus, mais via la vraie route HTTP
    (server.app.test_client()) plutôt que filter_notion() en isolation —
    pour couvrir aussi le câblage curriculum_registry/get_chapter_content."""

    def setUp(self):
        self.client = server.app.test_client()
        self.user, self.headers = _register(self.client)

    def _get_chapitre_3(self):
        resp = self.client.get("/api/course-content/premiere/Chapitre_3", headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        return {n["id"]: n for n in resp.get_json()["notions"]}

    def test_free_recoit_un_exemple_par_regle_essentielle_operations(self):
        notions = self._get_chapitre_3()
        free_ids = {ex["id"] for ex in notions["operations-et-derivation"]["exemples"]}
        self.assertTrue({"exemple-639", "exemple-661", "exemple-673", "exemple-649"}.issubset(free_ids))

    def test_free_recoit_le_tableau_comparatif_operations(self):
        notions = self._get_chapitre_3()
        self.assertIn("tableauComparatif", notions["operations-et-derivation"])

    def test_premium_recoit_en_plus_le_cinquieme_exemple_operations(self):
        db.set_stripe_subscription(self.user["id"], "sub_test", "premium", "active")
        notions = self._get_chapitre_3()
        free_ids = {ex["id"] for ex in notions["operations-et-derivation"]["exemples"]}
        self.assertIn("exemple-685", free_ids)

    def test_ultra_recoit_les_quatre_demonstrations(self):
        db.set_stripe_subscription(self.user["id"], "sub_test", "ultra", "active")
        notions = self._get_chapitre_3()
        for notion_id in notions:
            with self.subTest(notion=notion_id):
                self.assertIn("demonstration", notions[notion_id])
                self.assertFalse(notions[notion_id]["locked_content"]["ultra"])


if __name__ == "__main__":
    unittest.main()
