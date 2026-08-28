"""
Vérifications réelles (test_client, jamais de mock du contrat HTTP) du
chantier "Paramètres réellement complets" : chaque réglage éditable doit
être persisté ET réellement lu par le code qui le consomme, chaque bouton
doit avoir un effet réel — voir settings_service.py et
chatbot/services/llm_fallback_service.py pour le détail de ce qui est
désormais réellement branché (température/tokens/fallback IA)."""
import random
import unittest

import db
import server
from chatbot.services import llm_fallback_service
from role_service import Role


def _register(client):
    email = f"tsettings{random.randint(1_000_000, 9_999_999)}@gmail.com"
    username = f"tsettings{random.randint(100_000, 999_999)}"
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
    # /admin/settings exige SUPER_ADMIN (voir admin_nav_service.py — module le
    # plus sensible du panneau), contrairement à /admin/ia qui n'exige que
    # ADMIN.
    user, headers = _register(client)
    db.set_user_role(user["id"], Role.SUPER_ADMIN.value)
    return user, headers


class TestParametresIAReellementAppliques(unittest.TestCase):
    """Preuve que temperature/max_tokens/fallback ne sont pas juste affichés :
    llm_fallback_service (le pipeline chatbot réel) les relit directement."""

    def setUp(self):
        self.client = server.app.test_client()
        self.addCleanup(self._reset_ai_settings)

    def _reset_ai_settings(self):
        # Pas de delete_system_setting() dans db.py (voir sa docstring) : on
        # réécrit explicitement les valeurs par défaut documentées plutôt que
        # de stocker NULL (qui ferait planter float(None)/int(None) au
        # prochain appel réel du pipeline).
        db.set_system_setting("ai_temperature_default", "0.6")
        db.set_system_setting("ai_max_response_tokens_default", "1024")
        db.set_system_setting("ai_fallback_enabled", "1")

    def test_temperature_et_max_tokens_persistes_et_relus_par_le_pipeline(self):
        _, headers = _register_admin(self.client)
        resp = self.client.patch("/api/admin/settings/ai", json={
            "ai_temperature_default": 0.2,
            "ai_max_response_tokens_default": 512,
            "ai_fallback_enabled": True,
        }, headers=headers)
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertEqual(body["ai_temperature_default"]["value"], 0.2)
        self.assertEqual(body["ai_max_response_tokens_default"]["value"], 512)

        # Lecture directe par le pipeline (pas seulement l'API d'admin) :
        self.assertAlmostEqual(llm_fallback_service._ai_default_temperature(), 0.2)
        self.assertEqual(llm_fallback_service._ai_default_max_tokens(), 512)
        self.assertTrue(llm_fallback_service._ai_fallback_enabled())

    def test_temperature_hors_bornes_rejetee(self):
        _, headers = _register_admin(self.client)
        resp = self.client.patch("/api/admin/settings/ai", json={"ai_temperature_default": 5.0}, headers=headers)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("ai_temperature_default", resp.get_json()["fields"])

    def test_defaut_reste_060_et_2500_si_admin_na_rien_configure(self):
        # Simule l'absence totale de ligne en base (déploiement jamais
        # configuré) : le pipeline doit retomber EXACTEMENT sur les
        # constantes codées en dur — non-régression garantie pour les
        # déploiements existants qui n'ouvriront jamais cette section.
        # 1024 -> 1536 : Chantier 6 (bug "réponses parfois coupées",
        # 2026-08-25) ; 1536 -> 2500 : Chantier 9 (même bug remonté malgré ce
        # premier correctif, reproduit par appel réel à l'API), voir
        # llm_fallback_service._DEFAULT_MAX_TOKENS.
        conn = db.get_connection()
        try:
            conn.execute(
                "DELETE FROM system_settings WHERE key IN "
                "('ai_temperature_default', 'ai_max_response_tokens_default', 'ai_fallback_enabled')"
            )
            conn.commit()
        finally:
            conn.close()
        self.assertEqual(llm_fallback_service._ai_default_temperature(), 0.6)
        self.assertEqual(llm_fallback_service._ai_default_max_tokens(), 2500)
        self.assertTrue(llm_fallback_service._ai_fallback_enabled())

    def test_fallback_desactive_bloque_bascule_vers_autre_fournisseur(self):
        db.set_system_setting("ai_fallback_enabled", "0")

        class _FailingProvider:
            last_usage = None

            def current_model(self):
                return "modele-test"

            def stream_chat(self, messages, system, temperature=0.6, max_tokens=1024):
                raise RuntimeError("panne non durable de test")
                yield  # pragma: no cover

        from chatbot import provider_manager
        original_select = provider_manager.select_llm_for_user
        original_get_provider = provider_manager.get_provider
        provider_manager.select_llm_for_user = lambda user, exclude=None: ("gemini", "gemini-3-flash-preview")
        provider_manager.get_provider = lambda provider=None, model=None, api_key=None: _FailingProvider()
        try:
            with self.assertRaises(RuntimeError):
                list(llm_fallback_service.generate([{"role": "user", "content": "salut"}], "system", {}))
        finally:
            provider_manager.select_llm_for_user = original_select
            provider_manager.get_provider = original_get_provider

    def test_fallback_active_par_defaut_bascule_normalement(self):
        # Non-régression : réglage absent (comportement historique) doit
        # toujours basculer vers "fake" en dernier recours plutôt que lever.
        class _FailingProvider:
            last_usage = None

            def current_model(self):
                return "modele-test"

            def stream_chat(self, messages, system, temperature=0.6, max_tokens=1024):
                raise RuntimeError("panne non durable de test")
                yield  # pragma: no cover

        from chatbot import provider_manager
        original_select = provider_manager.select_llm_for_user
        original_get_provider = provider_manager.get_provider
        calls = {"n": 0}

        def fake_select(user, exclude=None):
            calls["n"] += 1
            if calls["n"] == 1:
                return ("gemini", "gemini-3-flash-preview")
            return ("fake", None)

        provider_manager.select_llm_for_user = fake_select
        provider_manager.get_provider = lambda provider=None, model=None, api_key=None: _FailingProvider()
        try:
            # Les deux candidats ("gemini" puis "fake") échouent aussi : le
            # point vérifié ici n'est pas le succès final, mais qu'une
            # bascule vers un SECOND candidat a bien été tentée (calls["n"]
            # > 1) avant d'abandonner — contrairement au test précédent où
            # fallback_enabled=False arrête tout dès le premier échec.
            with self.assertRaises(RuntimeError):
                list(llm_fallback_service.generate([{"role": "user", "content": "salut"}], "system", {}))
            self.assertGreater(calls["n"], 1)
        finally:
            provider_manager.select_llm_for_user = original_select
            provider_manager.get_provider = original_get_provider


class TestClesApiCreationEtTest(unittest.TestCase):
    def setUp(self):
        self.client = server.app.test_client()

    def test_creation_puis_test_de_connexion_puis_suppression(self):
        _, headers = _register_admin(self.client)
        resp = self.client.post("/api/admin/ai/keys", json={
            "provider_key": "gemini", "label": "Clé de test pytest", "priority": 0,
            "api_key": "AIzaTestFakeKeyForPytestOnly",
        }, headers=headers)
        if resp.status_code == 400 and "TWO_FACTOR_SECRET_KEY" in (resp.get_json().get("error") or ""):
            # Chiffrement des clés API IA indisponible dans cet environnement
            # de test (variable d'environnement absente) — limitation de
            # l'environnement, pas une régression du code : le message
            # d'erreur clair renvoyé par la route EST le comportement
            # attendu dans ce cas (voir ai_provider_key_service.py).
            self.skipTest("TWO_FACTOR_SECRET_KEY non configurée dans cet environnement de test.")
        self.assertEqual(resp.status_code, 201, resp.get_json())
        key_id = resp.get_json()["id"]

        # Bouton "Tester la connexion" : un vrai appel réseau est déclenché
        # (clé fabriquée donc l'issue attendue est un échec), on vérifie
        # seulement que la route répond proprement (jamais un 500).
        test_resp = self.client.post(f"/api/admin/ai/keys/{key_id}/test", headers=headers)
        self.assertEqual(test_resp.status_code, 200)
        self.assertIn("ok", test_resp.get_json())

        delete_resp = self.client.delete(f"/api/admin/ai/keys/{key_id}", headers=headers)
        self.assertEqual(delete_resp.status_code, 200)


class TestSmtpTest(unittest.TestCase):
    def setUp(self):
        self.client = server.app.test_client()

    def test_bouton_tester_lenvoi_repond_avec_un_resultat_reel(self):
        _, headers = _register_admin(self.client)
        resp = self.client.post("/api/admin/settings/smtp/test", json={}, headers=headers)
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertIn("sent", body)
        if not body["sent"]:
            self.assertIn("error", body)


class TestSauvegardesCycleComplet(unittest.TestCase):
    def setUp(self):
        self.client = server.app.test_client()

    def test_creation_telechargement_restauration_suppression(self):
        _, headers = _register_admin(self.client)

        create_resp = self.client.post("/api/admin/settings/backups", json={}, headers=headers)
        self.assertEqual(create_resp.status_code, 201, create_resp.get_json())
        filename = create_resp.get_json()["filename"]

        download_resp = self.client.get(f"/api/admin/settings/backups/{filename}/download", headers=headers)
        self.assertEqual(download_resp.status_code, 200)
        self.assertGreater(len(download_resp.data), 0)
        # send_file() (Flask/Werkzeug) garde le fichier ouvert tant que la
        # réponse de test n'est pas explicitement fermée — sur Windows, cela
        # verrouille le fichier au niveau OS (WinError 32) pour toute
        # opération suivante dessus (restore/delete), contrairement à un
        # vrai serveur WSGI qui ferme la réponse après l'avoir envoyée.
        # Purement un artefact du test_client, jamais un problème en prod.
        download_resp.close()

        restore_resp = self.client.post(f"/api/admin/settings/backups/{filename}/restore", headers=headers)
        self.assertEqual(restore_resp.status_code, 200)

        delete_resp = self.client.delete(f"/api/admin/settings/backups/{filename}", headers=headers)
        self.assertEqual(delete_resp.status_code, 200, delete_resp.get_json())


class TestApercuParametresSansErreur500(unittest.TestCase):
    """Non-régression : GET /api/admin/settings/overview levait un KeyError
    (500) car settings_service.backups_info() lisait storage["disk_total_bytes"],
    une clé volontairement retirée de system_health_service.storage_info()
    (voir sa docstring). Le correctif représente cette donnée comme
    indisponible via le contrat {available, value, reason} déjà géré par
    admin-settings.js, plutôt que de la recalculer ou de fabriquer une valeur."""

    def setUp(self):
        self.client = server.app.test_client()

    def test_overview_renvoie_200_et_une_structure_conforme(self):
        _, headers = _register_admin(self.client)
        resp = self.client.get("/api/admin/settings/overview", headers=headers)
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))
        body = resp.get_json()
        for section in ("ai", "api_keys", "smtp", "stripe", "backups", "security", "logs"):
            self.assertIn(section, body)

    def test_bloc_sauvegardes_disk_total_bytes_indisponible_sans_valeur_fabriquee(self):
        _, headers = _register_admin(self.client)
        resp = self.client.get("/api/admin/settings/overview", headers=headers)
        backups = resp.get_json()["backups"]
        # disk_used_bytes reste réellement disponible (shutil.disk_usage réel) :
        self.assertTrue(backups["disk_used_bytes"]["available"])
        self.assertIsInstance(backups["disk_used_bytes"]["value"], int)
        # disk_total_bytes n'est plus calculé : indisponible explicitement,
        # jamais 0 ni une valeur devinée.
        self.assertFalse(backups["disk_total_bytes"]["available"])
        self.assertIsNone(backups["disk_total_bytes"]["value"])
        self.assertTrue(backups["disk_total_bytes"]["reason"])

    def test_bloc_sauvegardes_reste_fonctionnel_avec_les_donnees_reellement_disponibles(self):
        _, headers = _register_admin(self.client)
        resp = self.client.get("/api/admin/settings/overview", headers=headers)
        backups = resp.get_json()["backups"]
        self.assertIn("items", backups)
        self.assertIn("total_size_bytes", backups)
        self.assertIn("last_backup", backups)
        self.assertIn("last_backup_successful", backups)


if __name__ == "__main__":
    unittest.main()
