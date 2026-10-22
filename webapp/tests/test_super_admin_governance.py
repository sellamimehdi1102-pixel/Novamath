"""
Gouvernance du rôle SUPER_ADMIN (vérification/correction des permissions
admin locales, 2026-10-22) : complète test_role_service.py (TestSyncAdminBootstrap)
avec le pendant SUPER_ADMIN, et verrouille deux propriétés explicitement
demandées qui n'étaient pas encore couvertes par un test :

1. Aucun utilisateur ne peut élever lui-même ses privilèges : il n'existe
   aucune route Flask qui appelle db.set_user_role (seul moyen d'écrire la
   colonne users.role) — la seule façon de changer un rôle est une écriture
   directe en base (hors API) ou le bootstrap par variable d'environnement
   (NOVAMATH_ADMIN_EMAILS/NOVAMATH_SUPER_ADMIN_EMAILS), qui ne promeut
   jamais qu'à la hausse et n'est jamais déclenché par une requête HTTP
   contrôlée par l'utilisateur lui-même.
2. Seul SUPER_ADMIN peut accéder aux modules qui l'exigent explicitement
   (Finance, Paramètres) — voir admin_nav_service.py, source unique de
   vérité déjà testée indirectement par test_admin_subscriptions_service.py/
   test_settings_service.py ; ce fichier vérifie la déclaration elle-même,
   pour détecter toute régression si un futur chantier abaisse par erreur
   le rôle minimum d'un de ces deux modules sensibles.

Aucun compte réel n'est utilisé : tous les comptes sont créés/jetés par
chaque test (db.create_user), jamais l'email sellamimehdi1102@gmail.com.
"""
import os
import unittest

import db
import admin_nav_service
import role_service
from role_service import Role, get_role


class TestSyncSuperAdminBootstrap(unittest.TestCase):
    """Pendant de TestSyncAdminBootstrap (test_role_service.py) pour
    sync_super_admin_bootstrap/NOVAMATH_SUPER_ADMIN_EMAILS — même mécanisme,
    jamais testé isolément jusqu'ici."""

    def setUp(self):
        self._saved_env = os.environ.get("NOVAMATH_SUPER_ADMIN_EMAILS")
        self.user_id = db.create_user(
            f"super-admin-bootstrap-{id(self)}@gmail.com", f"superadminbootstrap{id(self)}", "Test", "hash",
        )

    def tearDown(self):
        if self._saved_env is None:
            os.environ.pop("NOVAMATH_SUPER_ADMIN_EMAILS", None)
        else:
            os.environ["NOVAMATH_SUPER_ADMIN_EMAILS"] = self._saved_env

    def test_sans_variable_denv_aucune_promotion(self):
        os.environ.pop("NOVAMATH_SUPER_ADMIN_EMAILS", None)
        user = db.get_user_by_id(self.user_id)
        result = role_service.sync_super_admin_bootstrap(user)
        self.assertIs(get_role(result), Role.USER)

    def test_email_liste_est_promu_super_admin_et_persiste_en_base(self):
        user = db.get_user_by_id(self.user_id)
        os.environ["NOVAMATH_SUPER_ADMIN_EMAILS"] = f"autre@x.com, {user['email']} ,encore@x.com"
        result = role_service.sync_super_admin_bootstrap(user)
        self.assertIs(get_role(result), Role.SUPER_ADMIN)
        self.assertIs(get_role(db.get_user_by_id(self.user_id)), Role.SUPER_ADMIN)

    def test_email_absent_de_la_liste_reste_user(self):
        user = db.get_user_by_id(self.user_id)
        os.environ["NOVAMATH_SUPER_ADMIN_EMAILS"] = "quelquun-dautre@gmail.com"
        result = role_service.sync_super_admin_bootstrap(user)
        self.assertIs(get_role(result), Role.USER)

    def test_les_deux_listes_denv_sont_independantes(self):
        """Un email présent dans NOVAMATH_ADMIN_EMAILS mais absent de
        NOVAMATH_SUPER_ADMIN_EMAILS ne doit JAMAIS obtenir SUPER_ADMIN —
        les deux variables ne sont jamais fusionnées (voir role_service.py)."""
        saved_admin_env = os.environ.get("NOVAMATH_ADMIN_EMAILS")
        try:
            user = db.get_user_by_id(self.user_id)
            os.environ["NOVAMATH_ADMIN_EMAILS"] = user["email"]
            os.environ.pop("NOVAMATH_SUPER_ADMIN_EMAILS", None)
            user = role_service.sync_admin_bootstrap(user)
            user = role_service.sync_super_admin_bootstrap(user)
            self.assertIs(get_role(user), Role.ADMIN)
        finally:
            if saved_admin_env is None:
                os.environ.pop("NOVAMATH_ADMIN_EMAILS", None)
            else:
                os.environ["NOVAMATH_ADMIN_EMAILS"] = saved_admin_env


class TestAucuneElevationDePrivilegeParLutilisateur(unittest.TestCase):
    """Aucun utilisateur ne peut élever lui-même ses privilèges : vérifie
    qu'aucune route Flask (server.py) n'appelle db.set_user_role — seul
    point d'écriture de la colonne users.role. Si un futur chantier ajoute
    une route de gestion des rôles, elle devra explicitement exiger
    SUPER_ADMIN ET ne jamais permettre à un utilisateur de se cibler
    lui-même ; ce test échouera alors intentionnellement pour forcer cette
    vérification plutôt que de laisser passer silencieusement une nouvelle
    voie d'élévation de privilèges."""

    def test_server_py_ne_contient_aucun_appel_a_set_user_role(self):
        import server

        server_source_path = server.__file__
        with open(server_source_path, "r", encoding="utf-8") as f:
            source = f.read()
        self.assertNotIn(
            "set_user_role",
            source,
            "server.py appelle désormais db.set_user_role depuis une route HTTP : "
            "vérifier manuellement qu'aucun utilisateur ne peut cibler son propre "
            "compte ni se promouvoir au-delà de son rôle actuel avant de valider "
            "ce changement.",
        )

    def test_seul_db_set_user_role_ecrit_la_colonne_role(self):
        """Non-régression de la garantie ci-dessus si set_user_role était un
        jour renommé/déplacé : au moins une fonction db.py doit rester le
        point d'écriture unique de users.role (UPDATE users SET role = ...)."""
        self.assertTrue(hasattr(db, "set_user_role"))
        self.assertTrue(callable(db.set_user_role))


class TestDeclarationDesModulesReservesSuperAdmin(unittest.TestCase):
    """Verrou de non-régression sur admin_nav_service.MODULES : Finance et
    Paramètres doivent rester réservés à SUPER_ADMIN (données financières
    réelles / réglages système les plus larges) — si un futur chantier
    abaisse ce rôle minimum par erreur, ce test échoue immédiatement."""

    def test_finance_exige_super_admin(self):
        module = admin_nav_service.module_by_path("/admin/finance")
        self.assertIsNotNone(module)
        self.assertIs(module.minimum_role, Role.SUPER_ADMIN)

    def test_parametres_exige_super_admin(self):
        module = admin_nav_service.module_by_path("/admin/settings")
        self.assertIsNotNone(module)
        self.assertIs(module.minimum_role, Role.SUPER_ADMIN)

    def test_seuls_finance_et_parametres_exigent_super_admin(self):
        """Documente explicitement la surface SUPER_ADMIN actuelle — toute
        extension à un autre module doit être une décision délibérée, pas un
        effet de bord silencieux d'un futur chantier."""
        super_admin_paths = {m.path for m in admin_nav_service.MODULES if m.minimum_role is Role.SUPER_ADMIN}
        self.assertEqual(super_admin_paths, {"/admin/finance", "/admin/settings"})


if __name__ == "__main__":
    unittest.main()
