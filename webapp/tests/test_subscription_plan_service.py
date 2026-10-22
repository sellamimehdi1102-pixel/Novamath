"""
Suite de subscription_plan_service.py — audit admin (2026-10-20), point 3 :
corrige la confusion entre la fenêtre d'affichage du graphique "Résultats au
fil des séries" (server.py::_STATS_SERIES_WINDOW) et une rétention réelle
des données. Couvre spécifiquement migrate_stale_series_window_wording()
(idempotente, non destructive) et seed_default_plans() (non régressé).
"""
import unittest

import db
import subscription_plan_service as catalog


class TestSeedDefaultPlansTexteCorrige(unittest.TestCase):
    def setUp(self):
        catalog.seed_default_plans()

    def test_premium_mentionne_lhistorique_du_graphique_jamais_une_retention(self):
        plan = catalog.get_plan("premium")
        self.assertIn("Historique du graphique : 15 dernières séries", plan["advantages"])
        self.assertNotIn("conservées", " ".join(plan["advantages"]))

    def test_ultra_mentionne_lhistorique_du_graphique_jamais_une_retention(self):
        plan = catalog.get_plan("ultra")
        self.assertIn("Historique du graphique : toutes les séries", plan["advantages"])
        self.assertNotIn("conservées", " ".join(plan["advantages"]))


class TestMigrationStaleSeriesWording(unittest.TestCase):
    def setUp(self):
        catalog.seed_default_plans()

    def _force_stale_text(self):
        """Simule une base seedée AVANT ce chantier (ancien texte exact),
        sans passer par seed_default_plans() qui n'écrit déjà plus que le
        texte corrigé — reproduit fidèlement l'état réel d'une base
        existante jamais retouchée."""
        row = db.get_subscription_plan("premium")
        advantages = catalog._decode_list(row["advantages"])
        advantages = [
            "Dashboard élargi : 50 séries d'entraînement conservées" if "Historique du graphique" in a else a
            for a in advantages
        ]
        db.update_subscription_plan(
            "premium", row["name"], row["description"], row["price_amount_cents"], row["currency"],
            row["duration_label"], catalog._encode_list(advantages), row["limits"], row["quota_daily"],
            row["quota_monthly"], row["quota_chatbot"], row["display_order"], row["active"],
        )

    def test_corrige_le_texte_obsolete_sans_toucher_au_reste(self):
        self._force_stale_text()
        before = db.get_subscription_plan("premium")
        corrected = catalog.migrate_stale_series_window_wording()
        self.assertEqual(corrected, ["premium"])
        after = catalog.get_plan("premium")
        self.assertIn("Historique du graphique : 15 dernières séries", after["advantages"])
        # Rien d'autre n'a changé : prix, quotas, display_order inchangés.
        self.assertEqual(after["price_amount_cents"], before["price_amount_cents"])
        self.assertEqual(after["quota_daily"], before["quota_daily"])
        self.assertEqual(after["quota_chatbot"], before["quota_chatbot"])
        self.assertEqual(after["display_order"], before["display_order"])

    def test_idempotente_deuxieme_appel_ne_corrige_plus_rien(self):
        self._force_stale_text()
        first = catalog.migrate_stale_series_window_wording()
        self.assertEqual(first, ["premium"])
        second = catalog.migrate_stale_series_window_wording()
        self.assertEqual(second, [])

    def test_aucune_correction_si_le_texte_est_deja_a_jour(self):
        # seed_default_plans() écrit déjà le bon texte : rien à corriger.
        corrected = catalog.migrate_stale_series_window_wording()
        self.assertEqual(corrected, [])

    def test_ne_touche_pas_free_qui_na_jamais_mentionne_de_nombre_de_series(self):
        self._force_stale_text()
        before_free = catalog.get_plan("free")
        catalog.migrate_stale_series_window_wording()
        after_free = catalog.get_plan("free")
        self.assertEqual(before_free, after_free)


if __name__ == "__main__":
    unittest.main()
