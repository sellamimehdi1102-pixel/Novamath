"""Audit admin (2026-10-20) : nettoyage des calculs morts de
admin_analytics_service.rankings()/charts() — vérifiés exhaustivement par
grep (aucun export CSV/Excel/PDF, aucun test, aucun autre consommateur
Python ou JS ne référençait ces clés) avant suppression :

- rankings()["ai"]["top_tokens"] : doublon EXACT de "top_models" (même
  liste), jamais une donnée distincte, jamais lu par admin-analytics.js
  (seul "top_models" l'est).
- rankings()["support"]["top_categories"]/["top_priorities"] : calculés
  mais jamais lus par admin-analytics.js (seul "top_admins" l'est, pour le
  groupe "support" de rankings()).
- charts()["support"]["by_priority"] : calculé mais jamais lu par
  admin-analytics.js::renderSupportCharts (seuls "by_category"/"by_status"
  le sont).

Les fonctions db.py sous-jacentes (support_tickets_count_by_category/
_priority) ne sont PAS supprimées : count_by_category reste utilisée par
charts()["support"]["by_category"], et count_by_priority peut encore servir
ailleurs à l'avenir — seule la clé de sortie inutilisée disparaît."""
import unittest

import admin_analytics_service


class TestRankingsCalculsMortsRetires(unittest.TestCase):
    def test_top_tokens_nest_plus_renvoye(self):
        payload, error = admin_analytics_service.rankings("30j")
        self.assertIsNone(error)
        self.assertNotIn("top_tokens", payload["ai"])

    def test_top_categories_et_top_priorities_ne_sont_plus_renvoyes(self):
        payload, error = admin_analytics_service.rankings("30j")
        self.assertIsNone(error)
        self.assertNotIn("top_categories", payload["support"])
        self.assertNotIn("top_priorities", payload["support"])

    def test_les_classements_reellement_consommes_restent_intacts(self):
        """Aucune régression sur les classements réellement affichés côté
        JS (admin-analytics.js) : top_ai_consumers/top_chatbot_users/
        top_providers/top_models/top_engines/top_cost/top_admins."""
        payload, error = admin_analytics_service.rankings("30j")
        self.assertIsNone(error)
        for key in ("top_ai_consumers", "top_chatbot_users", "top_active_reason"):
            self.assertIn(key, payload["users"])
        for key in ("top_providers", "top_models", "top_engines", "top_cost"):
            self.assertIn(key, payload["ai"])
        self.assertIn("top_admins", payload["support"])


class TestChartsByPriorityRetire(unittest.TestCase):
    def test_by_priority_nest_plus_renvoye(self):
        payload, error = admin_analytics_service.charts("30j")
        self.assertIsNone(error)
        self.assertNotIn("by_priority", payload["support"])

    def test_by_category_et_by_status_restent_intacts(self):
        """Seuls by_category/by_status sont réellement rendus par
        admin-analytics.js::renderSupportCharts — aucune régression."""
        payload, error = admin_analytics_service.charts("30j")
        self.assertIsNone(error)
        self.assertIn("by_category", payload["support"])
        self.assertIn("by_status", payload["support"])
        self.assertIn("tickets_per_day", payload["support"])


if __name__ == "__main__":
    unittest.main()
