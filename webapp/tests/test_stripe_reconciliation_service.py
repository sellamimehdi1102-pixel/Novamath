"""
Suite de stripe_reconciliation_service.py (audit admin 2026-10-20, point 2) —
aucun appel réseau réel, stripe_service.get_subscription est mocké comme le
reste des tests Stripe du projet (voir test_stripe_service.py).

Isolation : la base SQLite de test est PARTAGÉE pour toute la session pytest
(voir tests/conftest.py, jamais recréée par test ni par fichier) — d'autres
fichiers de tests laissent déjà des comptes avec un stripe_subscription_id
non nul. reconcile() opère sur TOUTE la base (par conception, pas de filtre
par utilisateur) : chaque test fixe donc son propre `offset` sur le total
déjà présent AVANT de créer ses comptes de contrôle, pour n'observer QUE ses
propres lignes, ajoutées en dernier (ORDER BY id ASC, voir
db.list_users_with_stripe_subscription) — jamais une hypothèse de base vide.
"""
import os
import random
import unittest
from unittest.mock import patch

import admin_subscriptions_service
import db
import server
import stripe_reconciliation_service
from role_service import Role


def _register(client):
    import uuid

    unique = uuid.uuid4().hex
    email = f"stripereco{unique}@gmail.com"
    username = f"stripereco{unique[:15]}"
    resp = client.post("/api/auth/register", json={
        "email": email, "username": username, "pseudo": "Test",
        "birth_date": "2000-01-01",
        "password": "MotDePasse123!", "confirm_password": "MotDePasse123!",
        "accept_terms": True, "accept_privacy": True,
    })
    user = resp.get_json()["user"]
    csrf = client.get_cookie("nm_csrf").value
    return user, {"X-CSRF-Token": csrf}


def _register_admin(client):
    user, headers = _register(client)
    db.set_user_role(user["id"], Role.ADMIN.value)
    return user, headers


class TestReconcilePageAuDelaDuTotalExistant(unittest.TestCase):
    """Équivalent robuste d'une "base vide" dans une base de test partagée :
    une page dont l'offset dépasse le total existant ne doit jamais rien
    trouver, quel que soit ce que d'autres fichiers de tests ont laissé."""

    def setUp(self):
        self._env_backup = dict(os.environ)
        os.environ["STRIPE_SECRET_KEY"] = "sk_test_123"

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env_backup)

    def test_offset_au_dela_du_total_ne_trouve_rien(self):
        total = db.count_users_with_stripe_subscription()
        report = stripe_reconciliation_service.reconcile(limit=50, offset=total)
        self.assertEqual(report["checked"], 0)
        self.assertEqual(report["divergences"], [])
        self.assertEqual(report["errors"], [])
        self.assertFalse(report["has_more"])
        self.assertEqual(report["total"], total)


class TestReconcileDonneesControlees(unittest.TestCase):
    def setUp(self):
        self._env_backup = dict(os.environ)
        os.environ["STRIPE_SECRET_KEY"] = "sk_test_123"
        self._user_ids = []
        # Fixe le point de départ AVANT de créer les comptes de ce test —
        # isole des comptes à stripe_subscription_id déjà laissés par
        # d'autres fichiers de tests dans cette même base partagée.
        self._offset_before = db.count_users_with_stripe_subscription()

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env_backup)
        for uid in self._user_ids:
            db.delete_user(uid)

    def _make_user(self, subscription_id, local_status):
        email = f"reco{random.randint(1_000_000, 9_999_999)}@gmail.com"
        username = f"reco{random.randint(100_000, 999_999)}"
        user_id = db.create_user(email, username, "Test", "hash")
        db.set_stripe_subscription(user_id, subscription_id, "premium", local_status)
        self._user_ids.append(user_id)
        return user_id

    @patch("stripe_reconciliation_service.stripe_service.get_subscription")
    def test_statuts_identiques_aucune_divergence(self, mock_get_subscription):
        self._make_user("sub_match_1", "active")
        mock_get_subscription.return_value = {"status": "active"}
        report = stripe_reconciliation_service.reconcile(limit=50, offset=self._offset_before)
        self.assertEqual(report["checked"], 1)
        self.assertEqual(report["divergences"], [])
        self.assertEqual(report["errors"], [])

    @patch("stripe_reconciliation_service.stripe_service.get_subscription")
    def test_statut_divergent_signale(self, mock_get_subscription):
        user_id = self._make_user("sub_diverge_1", "active")
        # La DB locale dit "active" (dernier webhook reçu), Stripe dit
        # réellement "canceled" (annulé directement dans le Dashboard
        # Stripe, sans qu'aucun webhook n'ait jamais été reçu par Mathadap).
        mock_get_subscription.return_value = {"status": "canceled"}
        report = stripe_reconciliation_service.reconcile(limit=50, offset=self._offset_before)
        self.assertEqual(report["checked"], 1)
        self.assertEqual(len(report["divergences"]), 1)
        divergence = report["divergences"][0]
        self.assertEqual(divergence["user_id"], user_id)
        self.assertEqual(divergence["local_status"], "active")
        self.assertEqual(divergence["stripe_status"], "canceled")
        self.assertEqual(report["errors"], [])

    @patch("stripe_reconciliation_service.stripe_service.get_subscription")
    def test_erreur_reseau_sur_un_compte_najamais_interrompt_le_lot(self, mock_get_subscription):
        self._make_user("sub_ok_1", "active")
        self._make_user("sub_erreur_1", "active")

        def side_effect(subscription_id):
            if subscription_id == "sub_erreur_1":
                raise RuntimeError("connexion impossible")
            return {"status": "active"}

        mock_get_subscription.side_effect = side_effect
        report = stripe_reconciliation_service.reconcile(limit=50, offset=self._offset_before)
        self.assertEqual(report["checked"], 2)
        self.assertEqual(len(report["errors"]), 1)
        self.assertEqual(report["errors"][0]["stripe_subscription_id"], "sub_erreur_1")
        # Le compte en erreur n'apparaît jamais comme une fausse divergence.
        self.assertEqual(report["divergences"], [])

    @patch("stripe_reconciliation_service.stripe_service.get_subscription")
    def test_pagination_has_more(self, mock_get_subscription):
        for i in range(3):
            self._make_user(f"sub_page_{i}", "active")
        mock_get_subscription.return_value = {"status": "active"}
        report = stripe_reconciliation_service.reconcile(limit=2, offset=self._offset_before)
        self.assertEqual(report["checked"], 2)
        self.assertTrue(report["has_more"])
        report2 = stripe_reconciliation_service.reconcile(limit=2, offset=self._offset_before + 2)
        self.assertEqual(report2["checked"], 1)
        self.assertFalse(report2["has_more"])

    @patch("stripe_reconciliation_service.stripe_service.get_subscription")
    def test_mode_reporte_dans_le_resultat(self, mock_get_subscription):
        self._make_user("sub_mode_1", "active")
        mock_get_subscription.return_value = {"status": "active"}
        report = stripe_reconciliation_service.reconcile(limit=50, offset=self._offset_before)
        self.assertEqual(report["mode"], "test")


class TestReconcileGardeFouProduction(unittest.TestCase):
    """Garde-fou ajouté le 2026-10-20 suite à l'incident réel (clé sk_live_
    présente dans un .env local, 50 appels réels déclenchés par un simple
    clic de vérification) — voir stripe_reconciliation_service.py pour le
    détail des 2 protections. Ces tests appellent reconcile() directement
    (jamais la route HTTP) pour prouver que la protection vit dans le
    SERVICE, pas seulement dans server.py/l'interface."""

    def setUp(self):
        self._env_backup = dict(os.environ)
        os.environ["STRIPE_SECRET_KEY"] = "sk_live_123"

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env_backup)

    @patch("stripe_reconciliation_service.config.IS_PRODUCTION", False)
    def test_bloque_production_depuis_serveur_non_production(self):
        with self.assertRaises(stripe_reconciliation_service.StripeReconciliationBlocked):
            stripe_reconciliation_service.reconcile()

    @patch("stripe_reconciliation_service.config.IS_PRODUCTION", False)
    def test_blocage_non_contournable_meme_avec_confirmed_true(self):
        """`confirmed=True` ne doit JAMAIS lever ce blocage — seul le cas
        production+production peut être débloqué par une confirmation."""
        with self.assertRaises(stripe_reconciliation_service.StripeReconciliationBlocked):
            stripe_reconciliation_service.reconcile(confirmed=True)

    @patch("stripe_reconciliation_service.config.IS_PRODUCTION", True)
    def test_confirmation_requise_en_production_sans_confirmed(self):
        with self.assertRaises(stripe_reconciliation_service.StripeReconciliationConfirmationRequired):
            stripe_reconciliation_service.reconcile()

    @patch("stripe_reconciliation_service.stripe_service.get_subscription")
    @patch("stripe_reconciliation_service.config.IS_PRODUCTION", True)
    def test_production_confirmee_sexecute(self, mock_get_subscription):
        mock_get_subscription.return_value = {"status": "active"}
        total = db.count_users_with_stripe_subscription()
        report = stripe_reconciliation_service.reconcile(offset=total, confirmed=True)
        self.assertEqual(report["mode"], "production")
        self.assertEqual(report["checked"], 0)

    def test_mode_test_jamais_bloque_quel_que_soit_lenvironnement(self):
        os.environ["STRIPE_SECRET_KEY"] = "sk_test_123"
        total = db.count_users_with_stripe_subscription()
        with patch("stripe_reconciliation_service.config.IS_PRODUCTION", False):
            report = stripe_reconciliation_service.reconcile(offset=total)
        self.assertEqual(report["mode"], "test")


class TestStripeEnvironmentBanner(unittest.TestCase):
    """_stripe_environment() alimente le bandeau affiché au-dessus du bouton
    de réconciliation (admin-subscriptions.js::renderStripeEnvironment) —
    doit refléter EXACTEMENT la même condition que le blocage dur côté
    service, jamais une approximation qui pourrait rassurer à tort."""

    def setUp(self):
        self._env_backup = dict(os.environ)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env_backup)

    @patch("admin_subscriptions_service.config.IS_PRODUCTION", False)
    def test_production_depuis_dev_signale_bloque(self):
        os.environ["STRIPE_SECRET_KEY"] = "sk_live_123"
        env = admin_subscriptions_service._stripe_environment()
        self.assertEqual(env["mode"], "production")
        self.assertEqual(env["app_environment"], "developpement")
        self.assertTrue(env["reconciliation_blocked"])
        self.assertFalse(env["reconciliation_requires_confirmation"])

    @patch("admin_subscriptions_service.config.IS_PRODUCTION", True)
    def test_production_depuis_production_signale_confirmation(self):
        os.environ["STRIPE_SECRET_KEY"] = "sk_live_123"
        env = admin_subscriptions_service._stripe_environment()
        self.assertEqual(env["app_environment"], "production")
        self.assertFalse(env["reconciliation_blocked"])
        self.assertTrue(env["reconciliation_requires_confirmation"])

    @patch("admin_subscriptions_service.config.IS_PRODUCTION", False)
    def test_mode_test_jamais_bloque_ni_confirmation(self):
        os.environ["STRIPE_SECRET_KEY"] = "sk_test_123"
        env = admin_subscriptions_service._stripe_environment()
        self.assertFalse(env["reconciliation_blocked"])
        self.assertFalse(env["reconciliation_requires_confirmation"])

    def test_get_overview_inclut_le_bandeau(self):
        os.environ["STRIPE_SECRET_KEY"] = "sk_test_123"
        overview = admin_subscriptions_service.get_overview()
        self.assertIn("stripe_environment", overview)


class TestReconcileStripeNonConfigure(unittest.TestCase):
    def setUp(self):
        self._env_backup = dict(os.environ)
        os.environ.pop("STRIPE_SECRET_KEY", None)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env_backup)

    def test_leve_une_exception_explicite_jamais_un_rapport_vide_trompeur(self):
        with self.assertRaises(stripe_reconciliation_service.StripeReconciliationUnavailable):
            stripe_reconciliation_service.reconcile()


class TestRouteReconcileStripeDroitsAdmin(unittest.TestCase):
    """Vérifie les droits d'accès réels de la route HTTP — un utilisateur
    ordinaire ne doit jamais pouvoir déclencher d'appels Stripe."""

    def setUp(self):
        self.client = server.app.test_client()
        self._env_backup = dict(os.environ)
        os.environ["STRIPE_SECRET_KEY"] = "sk_test_123"

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env_backup)

    def test_sans_session_401(self):
        resp = self.client.post("/api/admin/subscriptions/reconcile-stripe")
        self.assertEqual(resp.status_code, 401)

    def test_utilisateur_ordinaire_403(self):
        _, headers = _register(self.client)
        resp = self.client.post("/api/admin/subscriptions/reconcile-stripe", headers=headers)
        self.assertEqual(resp.status_code, 403)

    @patch("stripe_reconciliation_service.stripe_service.get_subscription")
    def test_admin_recoit_un_rapport(self, mock_get_subscription):
        mock_get_subscription.return_value = {"status": "active"}
        _, headers = _register_admin(self.client)
        resp = self.client.post("/api/admin/subscriptions/reconcile-stripe", headers=headers)
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertIn("divergences", body)
        self.assertIn("errors", body)
        self.assertIn("mode", body)

    def test_stripe_non_configure_501(self):
        os.environ.pop("STRIPE_SECRET_KEY", None)
        _, headers = _register_admin(self.client)
        resp = self.client.post("/api/admin/subscriptions/reconcile-stripe", headers=headers)
        self.assertEqual(resp.status_code, 501)


class TestRouteReconcileStripeGardeFouProduction(unittest.TestCase):
    """Prouve que le garde-fou production ne peut pas être contourné par un
    appel direct à la route HTTP (ex: via curl/Postman, sans passer par le
    bouton admin) — seule la réponse HTTP (code + statut) compte ici, pas le
    comportement de l'interface."""

    def setUp(self):
        self.client = server.app.test_client()
        self._env_backup = dict(os.environ)
        os.environ["STRIPE_SECRET_KEY"] = "sk_live_123"

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env_backup)

    @patch("stripe_reconciliation_service.config.IS_PRODUCTION", False)
    def test_appel_direct_production_depuis_dev_est_refuse_403(self):
        _, headers = _register_admin(self.client)
        resp = self.client.post("/api/admin/subscriptions/reconcile-stripe", headers=headers)
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.get_json().get("code"), "blocked_local_production")

    @patch("stripe_reconciliation_service.config.IS_PRODUCTION", False)
    def test_appel_direct_avec_confirmed_true_reste_refuse_403(self):
        """Le paramètre `confirmed` envoyé directement dans le corps de la
        requête ne doit JAMAIS suffire à débloquer ce cas — c'est exactement
        le scénario d'un appel API direct qui tenterait de contourner la
        protection d'interface."""
        _, headers = _register_admin(self.client)
        resp = self.client.post(
            "/api/admin/subscriptions/reconcile-stripe", headers=headers, json={"confirmed": True}
        )
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.get_json().get("code"), "blocked_local_production")

    @patch("stripe_reconciliation_service.config.IS_PRODUCTION", True)
    def test_appel_direct_production_sans_confirmation_409(self):
        _, headers = _register_admin(self.client)
        resp = self.client.post("/api/admin/subscriptions/reconcile-stripe", headers=headers)
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.get_json().get("code"), "confirmation_required")

    @patch("stripe_reconciliation_service.stripe_service.get_subscription")
    @patch("stripe_reconciliation_service.config.IS_PRODUCTION", True)
    def test_appel_direct_production_avec_confirmation_200(self, mock_get_subscription):
        mock_get_subscription.return_value = {"status": "active"}
        _, headers = _register_admin(self.client)
        resp = self.client.post(
            "/api/admin/subscriptions/reconcile-stripe", headers=headers, json={"confirmed": True}
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json().get("mode"), "production")


if __name__ == "__main__":
    unittest.main()
