"""Audit admin (2026-10-20) :

1. overview() a été simplifié avant ce chantier (plus de total_services/
   ok_count) mais admin-dashboard.js::healthBadge() lisait encore ces deux
   champs disparus, affichant littéralement "undefined/undefined
   opérationnels" dès que global_status valait "ok" — ce test verrouille le
   contrat RÉEL renvoyé par overview() pour qu'une régression JS équivalente
   soit immédiatement visible côté backend si le contrat venait à changer à
   nouveau sans mettre à jour admin-dashboard.js.

2. full_snapshot() déclenchait deux connexions SQLite "SELECT 1" distinctes
   pour la même information (health_service.check_database(), une fois via
   list_services()->_sqlite_service(), une fois via database_info()) dans le
   même cycle de requête — vérifié ici en comptant les appels réels."""
import unittest
from unittest.mock import patch

import system_health_service


class TestOverviewContratReel(unittest.TestCase):
    def test_overview_ne_renvoie_plus_total_services_ni_ok_count(self):
        """Contrat simplifié : seuls global_status/degraded_count/down_count/
        checked_at sont renvoyés — jamais total_services/ok_count/
        untested_count (retirés lors du chantier de simplification de la
        page Santé, avant ce correctif)."""
        result = system_health_service.overview()
        for removed_key in ("total_services", "ok_count", "untested_count"):
            self.assertNotIn(removed_key, result)
        for expected_key in ("global_status", "degraded_count", "down_count", "checked_at"):
            self.assertIn(expected_key, result)

    def test_overview_accepte_des_services_deja_calcules(self):
        """overview(services=...) : ne recalcule pas list_services() si le
        résultat est déjà fourni (voir full_snapshot())."""
        fake_services = [{"state": "degraded"}, {"state": "down"}, {"state": "ok"}]
        result = system_health_service.overview(services=fake_services)
        self.assertEqual(result["degraded_count"], 1)
        self.assertEqual(result["down_count"], 1)
        self.assertEqual(result["global_status"], "down")


class TestFullSnapshotUneSeuleVerificationSqlite(unittest.TestCase):
    def test_une_seule_connexion_sqlite_par_cycle_de_full_snapshot(self):
        """Avant le correctif : health_service.check_database() était appelée
        deux fois (une dans list_services()->_sqlite_service(), une autre
        dans database_info()) pour le même full_snapshot() — désormais une
        seule fois, le résultat étant réutilisé partout."""
        with patch(
            "system_health_service.health_service.check_database", return_value=True
        ) as mocked_check:
            system_health_service.full_snapshot()
        self.assertEqual(mocked_check.call_count, 1)

    def test_services_et_database_restent_coherents_entre_eux(self):
        """Les deux vues (carte "Base SQLite" de Services, et "État" de
        Database) doivent refléter exactement le même constat — puisqu'elles
        partagent désormais le même db_check."""
        snapshot = system_health_service.full_snapshot()
        sqlite_service = next(s for s in snapshot["services"] if s["id"] == "sqlite")
        expected_state = "ok" if snapshot["database"]["state"]["value"] == "ok" else "down"
        self.assertEqual(sqlite_service["state"], expected_state)


if __name__ == "__main__":
    unittest.main()
