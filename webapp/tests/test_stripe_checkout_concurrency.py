"""
Durcissement production — race condition "customer Stripe orphelin" (voir
audit production : deux requêtes concurrentes sur le tout premier abonnement
d'un utilisateur pouvaient chacune créer un Customer Stripe distinct, un seul
étant retenu en base, l'autre restant orphelin si un paiement lui était
rattaché).

Correction : stripe_service.create_customer/create_checkout_session acceptent
désormais un idempotency_key ; server.py::api_checkout_create_session envoie
une clé STABLE par utilisateur pour la création du customer. Stripe lui-même
sérialise les requêtes concurrentes portant la même clé et renvoie le même
objet à tous les appelants — c'est ce que ce test simule via un faux SDK
Stripe en mémoire (dédoublonnage par idempotency_key, comme documenté par
Stripe), pour prouver qu'aucun customer dupliqué n'est jamais créé même sous
concurrence réelle (threads).
"""
import random
import threading
import unittest
from unittest.mock import patch

import db
import server


def _register(client):
    email = f"test{random.randint(1_000_000, 9_999_999)}@gmail.com"
    username = f"testuser{random.randint(100_000, 999_999)}"
    resp = client.post("/api/auth/register", json={
        "email": email, "username": username, "pseudo": "Test",
        "birth_date": "2000-01-01",
        "password": "MotDePasse123!", "confirm_password": "MotDePasse123!",
        "accept_terms": True, "accept_privacy": True,
    })
    user = resp.get_json()["user"]
    csrf = client.get_cookie("nm_csrf").value
    return user, {"X-CSRF-Token": csrf}


class _FakeStripeCustomerStore:
    """Reproduit le comportement RÉEL de l'API Stripe pour des requêtes
    concurrentes partageant la même idempotency_key : la première gagne la
    course et crée l'objet, toute requête concurrente/ultérieure avec la même
    clé reçoit le MÊME objet au lieu d'en créer un second. Voir la doc Stripe
    sur les idempotency keys."""

    def __init__(self):
        self._lock = threading.Lock()
        self._by_key = {}
        self.created_count = 0

    def create(self, email, name=None, idempotency_key=None):
        assert idempotency_key, "create_customer doit toujours recevoir une idempotency_key ici"
        with self._lock:
            if idempotency_key in self._by_key:
                return self._by_key[idempotency_key]
            self.created_count += 1
            customer = {"id": f"cus_fake_{self.created_count}"}
            self._by_key[idempotency_key] = customer
            return customer


class TestPasDeCustomerOrphelinSousConcurrence(unittest.TestCase):
    def setUp(self):
        self.client = server.app.test_client()
        self.user, self.headers = _register(self.client)
        self.store = _FakeStripeCustomerStore()

    @patch("server.stripe_service.create_checkout_session")
    @patch("server.stripe_service.create_customer")
    def test_deux_requetes_concurrentes_ne_creent_quun_seul_customer(
        self, mock_create_customer, mock_create_checkout_session,
    ):
        mock_create_customer.side_effect = self.store.create
        mock_create_checkout_session.return_value = {"url": "https://checkout.stripe.com/x"}

        results = []
        lock = threading.Lock()

        def worker():
            resp = self.client.post(
                "/api/checkout/create-session", json={"plan": "premium"}, headers=self.headers,
            )
            with lock:
                results.append(resp.status_code)

        threads = [threading.Thread(target=worker) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertTrue(all(code == 200 for code in results), results)
        # Le point central du test : peu importe le nombre de requêtes
        # concurrentes, un seul Customer Stripe a réellement été créé (la
        # clé d'idempotence est stable par utilisateur).
        self.assertEqual(self.store.created_count, 1)

        # Toutes les requêtes concurrentes doivent avoir été passées avec
        # exactement la même idempotency_key (stable, dérivée de user["id"]).
        keys_used = {call.kwargs["idempotency_key"] for call in mock_create_customer.call_args_list}
        self.assertEqual(keys_used, {f"novamath-customer-{self.user['id']}"})

        # La base ne retient qu'un seul customer_id, cohérent avec celui créé.
        stored_user = db.get_user_by_id(self.user["id"])
        self.assertEqual(stored_user["stripe_customer_id"], "cus_fake_1")

    @patch("server.stripe_service.create_checkout_session")
    @patch("server.stripe_service.create_customer")
    def test_double_clic_meme_thread_reutilise_le_customer_existant(
        self, mock_create_customer, mock_create_checkout_session,
    ):
        """Une fois le customer_id persisté (premier appel), les appels
        suivants ne recréent jamais de customer — comportement déjà correct
        avant durcissement, non régressé ici."""
        mock_create_customer.side_effect = self.store.create
        mock_create_checkout_session.return_value = {"url": "https://checkout.stripe.com/x"}

        for _ in range(3):
            resp = self.client.post(
                "/api/checkout/create-session", json={"plan": "premium"}, headers=self.headers,
            )
            self.assertEqual(resp.status_code, 200)

        self.assertEqual(self.store.created_count, 1)
        self.assertEqual(mock_create_customer.call_count, 1)

    @patch("server.stripe_service.create_checkout_session")
    @patch("server.stripe_service.create_customer")
    def test_checkout_session_recoit_une_idempotency_key(
        self, mock_create_customer, mock_create_checkout_session,
    ):
        mock_create_customer.side_effect = self.store.create
        mock_create_checkout_session.return_value = {"url": "https://checkout.stripe.com/x"}

        resp = self.client.post(
            "/api/checkout/create-session", json={"plan": "premium"}, headers=self.headers,
        )
        self.assertEqual(resp.status_code, 200)
        _, kwargs = mock_create_checkout_session.call_args
        self.assertTrue(kwargs.get("idempotency_key"))
        self.assertIn(f"novamath-checkout-{self.user['id']}-premium-", kwargs["idempotency_key"])


if __name__ == "__main__":
    unittest.main()
