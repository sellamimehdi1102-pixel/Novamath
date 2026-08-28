"""Chantier Administrateur "Utilisateurs" (Phase 2) : filtre account_status à
3 valeurs réelles (remplace l'ancien bucket "suspended"), filtre paiement en
échec (stripe_subscription_status), onglet Support de la fiche utilisateur,
enrichissement de l'onglet Informations (auth_provider/2FA/email vérifié).

Isolation vis-à-vis de la base partagée par toute la suite pytest : chaque
test filtre systématiquement par `search=<email unique généré>` pour ne
jamais dépendre du nombre total de comptes déjà présents en base."""
import random
import unittest

import admin_user_profile_service
import admin_users_service
import db
import server
from role_service import Role


def _register(client, role=Role.SUPPORT.value):
    email = f"tusers{random.randint(1_000_000, 9_999_999)}@gmail.com"
    username = f"tusers{random.randint(100_000, 999_999)}"
    resp = client.post("/api/auth/register", json={
        "email": email, "username": username, "pseudo": "Test",
        "birth_date": "2000-01-01",
        "password": "MotDePasse123!", "confirm_password": "MotDePasse123!",
        "accept_terms": True, "accept_privacy": True,
    })
    user = resp.get_json()["user"]
    db.set_user_role(user["id"], role)
    csrf = client.get_cookie("nm_csrf").value
    return user, {"X-CSRF-Token": csrf}


class TestFiltreAccountStatus(unittest.TestCase):
    def setUp(self):
        self.client = server.app.test_client()

    def _make_user(self, account_status):
        user, _ = _register(self.client)
        db.set_account_status(user["id"], account_status)
        return user

    def test_active_isole(self):
        u = self._make_user("active")
        result = admin_users_service.list_users(search=u["email"], account_status="active")
        self.assertEqual([x["id"] for x in result["items"]], [u["id"]])

    def test_pending_parental_consent_isole(self):
        u = self._make_user("pending_parental_consent")
        result = admin_users_service.list_users(search=u["email"], account_status="pending_parental_consent")
        self.assertEqual([x["id"] for x in result["items"]], [u["id"]])

    def test_parental_consent_refused_isole(self):
        u = self._make_user("parental_consent_refused")
        result = admin_users_service.list_users(search=u["email"], account_status="parental_consent_refused")
        self.assertEqual([x["id"] for x in result["items"]], [u["id"]])

    def test_pending_et_refused_ne_sont_jamais_melanges(self):
        refused = self._make_user("parental_consent_refused")
        # Un compte "refusé" ne doit JAMAIS apparaître sous le filtre "en attente" :
        # avant ce chantier, les deux étaient confondus sous un même bucket "suspended".
        result_pending = admin_users_service.list_users(search=refused["email"], account_status="pending_parental_consent")
        self.assertEqual(result_pending["items"], [])
        result_refused = admin_users_service.list_users(search=refused["email"], account_status="parental_consent_refused")
        self.assertEqual([x["id"] for x in result_refused["items"]], [refused["id"]])

    def test_serialize_user_renvoie_la_valeur_reelle_jamais_reconstruite(self):
        u = self._make_user("pending_parental_consent")
        result = admin_users_service.list_users(search=u["email"])
        self.assertEqual(result["items"][0]["account_status"], "pending_parental_consent")


class TestFiltrePaiementEnEchec(unittest.TestCase):
    def setUp(self):
        self.client = server.app.test_client()

    def _make_user(self, stripe_status):
        user, _ = _register(self.client)
        if stripe_status is not None:
            db.set_stripe_subscription_status(user["id"], stripe_status)
        return user

    def test_past_due_inclus(self):
        u = self._make_user("past_due")
        result = admin_users_service.list_users(search=u["email"], payment_status="failed")
        self.assertEqual([x["id"] for x in result["items"]], [u["id"]])

    def test_unpaid_inclus(self):
        u = self._make_user("unpaid")
        result = admin_users_service.list_users(search=u["email"], payment_status="failed")
        self.assertEqual([x["id"] for x in result["items"]], [u["id"]])

    def test_active_exclu(self):
        u = self._make_user("active")
        result = admin_users_service.list_users(search=u["email"], payment_status="failed")
        self.assertEqual(result["items"], [])

    def test_canceled_exclu(self):
        u = self._make_user("canceled")
        result = admin_users_service.list_users(search=u["email"], payment_status="failed")
        self.assertEqual(result["items"], [])

    def test_incomplete_exclu(self):
        u = self._make_user("incomplete")
        result = admin_users_service.list_users(search=u["email"], payment_status="failed")
        self.assertEqual(result["items"], [])

    def test_null_exclu(self):
        u = self._make_user(None)  # jamais d'abonnement Stripe initié
        result = admin_users_service.list_users(search=u["email"], payment_status="failed")
        self.assertEqual(result["items"], [])

    def test_valeur_de_filtre_inconnue_ignoree_jamais_une_exception(self):
        u = self._make_user("past_due")
        result = admin_users_service.list_users(search=u["email"], payment_status="valeur_invalide")
        # payment_status invalide -> filtre ignoré, pas d'exception, le compte reste visible
        self.assertEqual([x["id"] for x in result["items"]], [u["id"]])


class TestCombinaisonsDeFiltres(unittest.TestCase):
    def setUp(self):
        self.client = server.app.test_client()

    def test_plan_et_statut(self):
        user, _ = _register(self.client)
        db.set_account_status(user["id"], "pending_parental_consent")
        db.set_stripe_subscription(user["id"], "sub_x", "premium", "active")
        result = admin_users_service.list_users(search=user["email"], plan="premium", account_status="pending_parental_consent")
        self.assertEqual([x["id"] for x in result["items"]], [user["id"]])
        result_wrong_plan = admin_users_service.list_users(search=user["email"], plan="ultra", account_status="pending_parental_consent")
        self.assertEqual(result_wrong_plan["items"], [])

    def test_plan_et_paiement(self):
        user, _ = _register(self.client)
        db.set_stripe_subscription(user["id"], "sub_x", "premium", "past_due")
        result = admin_users_service.list_users(search=user["email"], plan="premium", payment_status="failed")
        self.assertEqual([x["id"] for x in result["items"]], [user["id"]])
        result_wrong_plan = admin_users_service.list_users(search=user["email"], plan="ultra", payment_status="failed")
        self.assertEqual(result_wrong_plan["items"], [])

    def test_statut_et_paiement(self):
        user, _ = _register(self.client)
        db.set_account_status(user["id"], "active")
        db.set_stripe_subscription_status(user["id"], "unpaid")
        result = admin_users_service.list_users(search=user["email"], account_status="active", payment_status="failed")
        self.assertEqual([x["id"] for x in result["items"]], [user["id"]])

    def test_recherche_et_statut(self):
        user, _ = _register(self.client)
        db.set_account_status(user["id"], "parental_consent_refused")
        result = admin_users_service.list_users(search=user["email"], account_status="parental_consent_refused")
        self.assertEqual([x["id"] for x in result["items"]], [user["id"]])

    def test_recherche_et_paiement(self):
        user, _ = _register(self.client)
        db.set_stripe_subscription_status(user["id"], "past_due")
        result = admin_users_service.list_users(search=user["email"], payment_status="failed")
        self.assertEqual([x["id"] for x in result["items"]], [user["id"]])


class TestOngletSupport(unittest.TestCase):
    def setUp(self):
        self.client = server.app.test_client()

    def test_utilisateur_avec_tickets(self):
        import support_service
        user, _ = _register(self.client)
        support_service.create_ticket(user["id"], "Le chatbot ne répond plus", "bug", "Corps du message.")

        data = admin_user_profile_service.get_support(user["id"])
        self.assertIsNotNone(data["tickets"])
        self.assertEqual(len(data["tickets"]), 1)
        ticket = data["tickets"][0]
        self.assertEqual(ticket["subject"], "Le chatbot ne répond plus")
        self.assertEqual(ticket["category_label"], "Bug")
        self.assertEqual(ticket["status_label"], "Ouvert")
        self.assertIsNone(data["tickets_reason"])

    def test_utilisateur_sans_ticket(self):
        user, _ = _register(self.client)
        data = admin_user_profile_service.get_support(user["id"])
        self.assertIsNone(data["tickets"])
        self.assertEqual(data["tickets_reason"], admin_user_profile_service.NO_TICKETS_REASON)

    def test_utilisateur_inexistant(self):
        data = admin_user_profile_service.get_support(999_999_999)
        self.assertIsNone(data)

    def test_permission_role_support_suffit(self):
        target, _ = _register(self.client)
        _, headers = _register(self.client, role=Role.SUPPORT.value)
        resp = self.client.get(f"/api/admin/users/{target['id']}/support", headers=headers)
        self.assertEqual(resp.status_code, 200)

    def test_permission_role_user_refusee(self):
        target, _ = _register(self.client)
        _, headers = _register(self.client, role=Role.USER.value)
        resp = self.client.get(f"/api/admin/users/{target['id']}/support", headers=headers)
        self.assertEqual(resp.status_code, 403)

    def test_route_http_utilisateur_inexistant_404(self):
        _, headers = _register(self.client)
        resp = self.client.get("/api/admin/users/999999999/support", headers=headers)
        self.assertEqual(resp.status_code, 404)


class TestInformationsEnrichies(unittest.TestCase):
    def setUp(self):
        self.client = server.app.test_client()

    def test_auth_provider_local_par_defaut(self):
        user, _ = _register(self.client)
        data = admin_user_profile_service.get_profile(user["id"])
        self.assertTrue(data["auth_provider"]["available"])
        self.assertEqual(data["auth_provider"]["value"], "local")

    def test_two_factor_desactivee_par_defaut(self):
        user, _ = _register(self.client)
        data = admin_user_profile_service.get_profile(user["id"])
        self.assertTrue(data["two_factor_enabled"]["available"])
        self.assertFalse(data["two_factor_enabled"]["value"])

    def test_two_factor_activee_reflete_la_colonne_reelle(self):
        user, _ = _register(self.client)
        db.enable_two_factor(user["id"])
        data = admin_user_profile_service.get_profile(user["id"])
        self.assertTrue(data["two_factor_enabled"]["value"])

    def test_email_non_verifie_pour_compte_local(self):
        user, _ = _register(self.client)
        data = admin_user_profile_service.get_profile(user["id"])
        self.assertFalse(data["email_verified"]["value"])

    def test_email_verifie_pour_compte_oauth(self):
        user, _ = _register(self.client)
        conn = db.get_connection()
        try:
            conn.execute("UPDATE users SET auth_provider = 'google' WHERE id = ?", (user["id"],))
            conn.commit()
        finally:
            conn.close()

        data = admin_user_profile_service.get_profile(user["id"])
        self.assertEqual(data["auth_provider"]["value"], "google")
        self.assertTrue(data["email_verified"]["value"])

    def test_meme_regle_que_public_user_pour_email_verified(self):
        """Ne recrée jamais un second calcul divergent de auth.py::_public_user
        (voir la docstring de get_profile) — prouvé en comparant directement
        aux deux sources pour le même compte."""
        user, headers = _register(self.client)
        resp = self.client.get("/api/auth/me", headers=headers)
        public_email_verified = resp.get_json()["user"]["email_verified"]

        data = admin_user_profile_service.get_profile(user["id"])
        self.assertEqual(data["email_verified"]["value"], public_email_verified)


if __name__ == "__main__":
    unittest.main()
