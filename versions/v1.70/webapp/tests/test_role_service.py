"""
Suite Phase 0 (SEC-05) : role_service.py isolé de server.py — Role, hiérarchie
des privilèges, décorateur @requires_role, bootstrap NOVAMATH_ADMIN_EMAILS.
Complément de tests/test_server_admin_routes.py qui couvre le branchement
réel sur /api/dev/dashboard.
"""
import os
import unittest

import db
import role_service
from role_service import Role, get_role, has_role_at_least, is_staff, requires_role


class TestRoleFromValue(unittest.TestCase):
    def test_from_value_degrade_vers_user_pour_toute_valeur_inconnue(self):
        for bad in (None, "", "superadmin", "Admin", 42):
            with self.subTest(bad=bad):
                self.assertIs(Role.from_value(bad), Role.USER)

    def test_from_value_reconnait_les_cinq_roles(self):
        for role in Role:
            self.assertIs(Role.from_value(role.value), role)

    def test_parse_est_strict_renvoie_none_si_inconnu(self):
        self.assertIsNone(Role.parse("superadmin"))
        self.assertIsNone(Role.parse(None))
        self.assertIs(Role.parse("admin"), Role.ADMIN)


class TestGetRole(unittest.TestCase):
    def test_utilisateur_none_egale_user(self):
        self.assertIs(get_role(None), Role.USER)

    def test_sans_colonne_role_egale_user(self):
        self.assertIs(get_role({"id": 1}), Role.USER)

    def test_valeur_corrompue_degrade_vers_user(self):
        self.assertIs(get_role({"role": "n'importe quoi"}), Role.USER)

    def test_lit_le_role_stocke(self):
        self.assertIs(get_role({"role": "admin"}), Role.ADMIN)


class TestHasRoleAtLeast(unittest.TestCase):
    def test_role_egal_satisfait_lexigence(self):
        self.assertTrue(has_role_at_least({"role": "admin"}, Role.ADMIN))

    def test_role_superieur_satisfait_une_exigence_plus_basse(self):
        self.assertTrue(has_role_at_least({"role": "super_admin"}, Role.ADMIN))
        self.assertTrue(has_role_at_least({"role": "admin"}, Role.MODERATOR))

    def test_role_inferieur_ne_satisfait_pas(self):
        self.assertFalse(has_role_at_least({"role": "moderator"}, Role.ADMIN))
        self.assertFalse(has_role_at_least({"role": "user"}, Role.SUPPORT))

    def test_utilisateur_none_ne_satisfait_jamais_plus_que_user(self):
        self.assertTrue(has_role_at_least(None, Role.USER))
        self.assertFalse(has_role_at_least(None, Role.SUPPORT))


class TestIsStaff(unittest.TestCase):
    def test_user_nest_pas_staff(self):
        self.assertFalse(is_staff({"role": "user"}))
        self.assertFalse(is_staff(None))

    def test_tout_role_superieur_est_staff(self):
        for value in ("support", "moderator", "admin", "super_admin"):
            with self.subTest(role=value):
                self.assertTrue(is_staff({"role": value}))


class TestRequiresRoleDecorator(unittest.TestCase):
    """Le décorateur lit request.current_user (posé par login_required en
    amont) — testé ici indépendamment de toute vraie route Flask, en
    simulant exactement ce que login_required fait avant lui."""

    def setUp(self):
        import server
        self.app = server.app

    def _call_wrapped(self, minimum, user):
        from flask import request

        @requires_role(minimum)
        def view():
            return "ok", 200

        with self.app.test_request_context("/fake-admin-route"):
            request.current_user = user
            return view()

    def test_refuse_un_utilisateur_normal(self):
        result = self._call_wrapped(Role.ADMIN, {"role": "user"})
        body, status = result
        self.assertEqual(status, 403)
        self.assertEqual(body.get_json(), {"error": "Réservé à l'administrateur."})

    def test_refuse_labsence_de_current_user(self):
        # Ne devrait jamais arriver derrière @login_required, mais le
        # décorateur ne doit jamais lever d'exception (jamais de 500).
        body, status = self._call_wrapped(Role.ADMIN, None)
        self.assertEqual(status, 403)

    def test_laisse_passer_un_administrateur(self):
        result = self._call_wrapped(Role.ADMIN, {"role": "admin"})
        self.assertEqual(result, ("ok", 200))

    def test_laisse_passer_un_role_superieur(self):
        result = self._call_wrapped(Role.ADMIN, {"role": "super_admin"})
        self.assertEqual(result, ("ok", 200))


class TestSyncAdminBootstrap(unittest.TestCase):
    def setUp(self):
        self._saved_env = os.environ.get("NOVAMATH_ADMIN_EMAILS")
        self.user_id = db.create_user(
            f"role-bootstrap-{id(self)}@gmail.com", f"rolebootstrap{id(self)}", "Test", "hash",
        )

    def tearDown(self):
        if self._saved_env is None:
            os.environ.pop("NOVAMATH_ADMIN_EMAILS", None)
        else:
            os.environ["NOVAMATH_ADMIN_EMAILS"] = self._saved_env

    def test_sans_variable_denv_aucune_promotion(self):
        os.environ.pop("NOVAMATH_ADMIN_EMAILS", None)
        user = db.get_user_by_id(self.user_id)
        result = role_service.sync_admin_bootstrap(user)
        self.assertIs(get_role(result), Role.USER)
        self.assertIs(get_role(db.get_user_by_id(self.user_id)), Role.USER)

    def test_email_liste_est_promu_admin_et_persiste_en_base(self):
        user = db.get_user_by_id(self.user_id)
        os.environ["NOVAMATH_ADMIN_EMAILS"] = f"autre@x.com, {user['email']} ,encore@x.com"
        result = role_service.sync_admin_bootstrap(user)
        self.assertIs(get_role(result), Role.ADMIN)
        self.assertIs(get_role(db.get_user_by_id(self.user_id)), Role.ADMIN)

    def test_email_absent_de_la_liste_reste_user(self):
        user = db.get_user_by_id(self.user_id)
        os.environ["NOVAMATH_ADMIN_EMAILS"] = "quelquun-dautre@gmail.com"
        result = role_service.sync_admin_bootstrap(user)
        self.assertIs(get_role(result), Role.USER)

    def test_ne_retrograde_jamais_un_role_deja_superieur(self):
        db.set_user_role(self.user_id, Role.SUPER_ADMIN.value)
        user = db.get_user_by_id(self.user_id)
        os.environ["NOVAMATH_ADMIN_EMAILS"] = user["email"]
        result = role_service.sync_admin_bootstrap(user)
        self.assertIs(get_role(result), Role.SUPER_ADMIN)

    def test_idempotent(self):
        user = db.get_user_by_id(self.user_id)
        os.environ["NOVAMATH_ADMIN_EMAILS"] = user["email"]
        first = role_service.sync_admin_bootstrap(user)
        second = role_service.sync_admin_bootstrap(first)
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
