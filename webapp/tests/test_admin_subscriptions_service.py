"""
Suite de admin_subscriptions_service.py — audit admin (2026-10-22) :

1. `get_overview()` n'inclut plus de compteurs "Nouveaux abonnements (30j)"/
   "Résiliations (30j)" (fonction `_global_stats`, retirée) : ces deux
   compteurs dupliquaient EXACTEMENT ceux déjà affichés par le module
   Finance (voir test_admin_finance_service.py et
   admin_finance_service.get_subscriptions_overview), devenu la seule
   référence pour les indicateurs d'abonnement agrégés.
2. Permissions des routes /api/admin/subscriptions/* vs /api/admin/finance/*
   (ADMIN pour Abonnements, SUPER_ADMIN pour Finance, voir
   admin_nav_service.py) — non-régression : un ADMIN garde l'accès au
   catalogue mais PAS à Finance ; un SUPER_ADMIN accède aux deux.

Aucun appel réseau Stripe : STRIPE_SECRET_KEY reste absent (comportement par
défaut du processus pytest, voir conftest.py) sauf quand un test le définit
explicitement pour la bannière d'environnement.
"""
import os
import random
import unittest

import admin_subscriptions_service
import db
import server
from role_service import Role


def _register(client):
    email = f"subsaudit{random.randint(1_000_000, 9_999_999)}@gmail.com"
    username = f"subsaudit{random.randint(100_000, 999_999)}"
    resp = client.post("/api/auth/register", json={
        "email": email, "username": username, "pseudo": "Test",
        "birth_date": "2000-01-01",
        "password": "MotDePasse123!", "confirm_password": "MotDePasse123!",
        "accept_terms": True, "accept_privacy": True,
    })
    return resp.get_json()["user"]


class TestGetOverviewSansCompteursDupliques(unittest.TestCase):
    """`get_overview()` reste la vue catalogue (plans + bannière Stripe),
    plus aucune statistique agrégée temporelle (voir admin_finance_service
    pour la même donnée)."""

    def setUp(self):
        self._env_backup = dict(os.environ)
        os.environ["STRIPE_SECRET_KEY"] = "sk_test_123"

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env_backup)

    def test_overview_ne_contient_plus_la_cle_stats(self):
        overview = admin_subscriptions_service.get_overview()
        self.assertNotIn("stats", overview)

    def test_overview_garde_le_catalogue_et_la_banniere_stripe(self):
        overview = admin_subscriptions_service.get_overview()
        self.assertIn("plans", overview)
        self.assertIn("stripe_environment", overview)

    def test_le_module_nexpose_plus_de_fonction_global_stats(self):
        # `_global_stats` a été supprimée avec les 2 compteurs qu'elle
        # calculait — jamais simplement vidée/désactivée (code mort).
        self.assertFalse(hasattr(admin_subscriptions_service, "_global_stats"))


class TestPermissionsAbonnementsVsFinance(unittest.TestCase):
    """Non-régression explicitement demandée par l'audit : la suppression
    des 2 compteurs d'Abonnements ne doit JAMAIS avoir été compensée par un
    changement de permission (ADMIN/SUPER_ADMIN restent inchangés, voir
    admin_nav_service.py, lu en lecture seule par ce test)."""

    def setUp(self):
        self.client = server.app.test_client()

    def test_admin_garde_acces_au_catalogue_abonnements(self):
        user = _register(self.client)
        db.set_user_role(user["id"], Role.ADMIN.value)
        resp = self.client.get("/api/admin/subscriptions")
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn("stats", resp.get_json())

    def test_admin_seul_ne_peut_pas_acceder_a_finance(self):
        # Conséquence directe et SIGNALÉE de la suppression des compteurs :
        # un ADMIN (non SUPER_ADMIN) ne peut pas se rabattre sur Finance
        # pour retrouver "Nouveaux abonnements"/"Résiliations" — voir le
        # rapport de ce chantier pour cette limite, non résolue
        # unilatéralement ici (aucune permission n'a été changée).
        user = _register(self.client)
        db.set_user_role(user["id"], Role.ADMIN.value)
        resp = self.client.get("/api/admin/finance/overview")
        self.assertEqual(resp.status_code, 403)

    def test_super_admin_accede_aux_deux_modules(self):
        user = _register(self.client)
        db.set_user_role(user["id"], Role.SUPER_ADMIN.value)
        resp_subs = self.client.get("/api/admin/subscriptions")
        resp_finance = self.client.get("/api/admin/finance/overview")
        self.assertEqual(resp_subs.status_code, 200)
        self.assertEqual(resp_finance.status_code, 200)


if __name__ == "__main__":
    unittest.main()
